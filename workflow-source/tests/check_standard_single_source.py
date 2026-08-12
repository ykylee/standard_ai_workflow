#!/usr/bin/env python3
"""진입점 규칙이 **표준 문서 한 곳에서만** 나오는가 (v1.0.2+).

## 왜 필요한가

하네스 진입점 파일은 에이전트가 세션을 열 때 처음 읽는 문서다. 거기 적힌 규칙이
그 세션의 규칙인데, 그 문장들이 `bootstrap_lib/harnesses/renderers.py` 의 하네스별
f-string 에 손으로 복제돼 있었다. 정본 `core/global_workflow_standard.md` 는 아무도
읽지 않았고, 복제본은 예상대로 갈라졌다 (2026-07-27 조사):

| 규칙 | 도입 전 | 도입 후 |
|---|---|---|
| §1 검증하지 않은 결과는 완료로 확정하지 않는다 | 12개 중 6개 | 주요 진입점 전부 |
| §8 memory 갱신 → commit → push | **12개 중 2개** | 주요 진입점 전부 |

§8 은 표준이 안티패턴까지 적어 둔 규칙인데, 정작 그 규칙을 지켜야 할 에이전트
대부분이 규칙을 받지 못하고 있었다.

## 판정 규칙

1. **스냅샷 == 정본** — wheel 설치용 스냅샷(`_standard_rules_snapshot.py`)은 정본에서
   생성된 것이어야 한다. 손으로 고친 순간 두 개의 진실이 생긴다.
2. **렌더러에 규칙 리터럴이 없다** — 진입점 규칙 문장을 렌더러가 직접 들고 있으면
   그건 사본이다. 반드시 `render_entrypoint_rules()` 를 거쳐야 한다.
3. **주요 진입점이 규칙을 담는다** — 실제 bootstrap 을 temp 에 돌려 산출물을 본다.
   렌더러를 직접 호출하지 않고 end-to-end 로 보는 이유는, 렌더러가 옳아도 배선이
   빠지면 파일에는 안 실리기 때문이다 (조립 단계에서 새는 것이 실제 사고였다).
4. **배포본 == 정본** — 이 저장소의 `ai-workflow/core/` 사본이 정본과 같아야 한다.
   진입점이 "표준 문서" 로 가리키는 것이 이 사본이라, 이게 낡으면 에이전트는 낡은
   규칙을 읽는다. 실제로 §8 이 통째로 빠진 채 2개월 방치돼 있었다.
5. **탐지기 자체가 동작한다** — 사본을 주입하면 2번이 실패해야 한다.

**한계 (과장하지 않는다)**: 2번은 *문장 리터럴* 만 본다. 렌더러가 규칙을 의역해서
새로 쓰면 잡지 못한다. 의역까지 잡으려면 의미 비교가 필요한데 그건 위양성을 낳고,
위양성을 내는 검사는 무시당한다. 대신 3번이 "정본 문장이 산출물에 그대로 있는가" 를
보므로, 의역본만 남기면 3번에서 걸린다.

Test list (7 case):
1. test_snapshot_matches_standard
2. test_renderers_have_no_rule_literals
3. test_generated_entrypoints_carry_rules
4. test_distributed_core_matches_canonical
5. test_detector_catches_injected_copy
6. test_shared_entrypoint_merges_instead_of_overwriting  ← 같은 파일을 쓰는 두 하네스
7. test_entrypoint_paths_match_generated_layout        ← 문서가 가리키는 곳에 파일이 있는가

Cross-ref: `workflow_kit/common/standard_rules.py`, `core/global_workflow_standard.md` §1 §3 §8.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.standard_rules import (  # noqa: E402
    STANDARD_RELPATH,
    load_standard_rules,
    parse_standard,
    render_snapshot_module,
)

RENDERERS = SOURCE_ROOT / "workflow_kit" / "bootstrap_lib" / "harnesses" / "renderers.py"
SNAPSHOT = SOURCE_ROOT / "workflow_kit" / "common" / "_standard_rules_snapshot.py"
BOOTSTRAP_SCRIPT = SOURCE_ROOT / "scripts" / "bootstrap_workflow_kit.py"
DISTRIBUTED_CORE = REPO_ROOT / "ai-workflow" / "core"

#: 규칙을 담아야 하는 하네스별 *주요* 진입점 (bootstrap 산출물 기준 상대 경로).
PRIMARY_ENTRYPOINTS: dict[str, str] = {
    "claude-code": "CLAUDE.md",
    "gemini-cli": "GEMINI.md",
    "antigravity": "ANTIGRAVITY.md",
    "minimax-code": "MiniMax.md",
    "grok-build": "GROK.md",
    "aider": "CONVENTIONS.md",
    # v1.0.2: pi-dev 와의 파일 소유 충돌이 해소돼(합치기) 단독 판정이 가능해졌다.
    "codex": "AGENTS.md",
    "opencode": ".opencode/skills/standard-ai-workflow/SKILL.md",
}

#: 규칙 문서를 만들지 않는 하네스 — 이유를 남긴다 (조용히 빠져나가는 경로를 두지 않는다).
EXEMPT_HARNESSES: dict[str, str] = {
    "goose": "config-only overlay — 산문 진입점 없이 .goose/config.yaml 의 read_files 로 상태 문서를 지정한다",
    "custom": "사용자가 채우는 빈 템플릿 — 규칙을 미리 박으면 템플릿 목적에 어긋난다",
    "pi-dev": "codex 와 root AGENTS.md 를 공유한다 (덮어쓰지 않고 합쳐서 emit) — codex 항목으로 함께 판정된다",
    "codewhale": "보조 SKILL.md — §8 만 정본에서 주입한다",
    # v1.1.7 (TASK-2026-08-11-main-026): 등록만 되고 어느 목록에도 없던 하네스.
    # case 8 이 PRIMARY ∪ EXEMPT == SUPPORTED_HARNESSES 를 단언하므로, 새 하네스는
    # 여기든 PRIMARY 든 반드시 분류해야 한다 — 미분류는 조용히 빠져나가는 경로다.
    "mavis": "project-local 산출물 0 — 글로벌 mcp.json merge 만 emit 하므로 규칙 문서 자체가 없다",
}

FAILURES: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case}{(' — ' + detail) if detail else ''}")
        FAILURES.append(case)


def _strip_marker(text: str) -> str:
    """`<!-- standard-ai-workflow-kit: vX -->` 버전 마커를 제거한다."""
    return re.sub(r"^<!--\s*standard-ai-workflow-kit:[^>]*-->\n\n?", "", text)


# --- Case 1 ----------------------------------------------------------------


def test_snapshot_matches_standard() -> None:
    standard = SOURCE_ROOT / STANDARD_RELPATH
    rules = parse_standard(standard.read_text(encoding="utf-8"))
    expected = render_snapshot_module(rules)
    actual = SNAPSHOT.read_text(encoding="utf-8") if SNAPSHOT.exists() else ""
    _record(
        "test_snapshot_matches_standard",
        expected == actual,
        "python3 -m workflow_kit.common.standard_rules --apply 로 재생성한다",
    )


# --- Case 2 ----------------------------------------------------------------


def _rule_literals() -> list[str]:
    rules = load_standard_rules(SOURCE_ROOT)
    # 짧은 문장은 다른 맥락에서도 자연스럽게 나올 수 있어 판정에서 뺀다 (위양성 방지).
    sentence_literals = [
        s for s in (*rules.principles, rules.close_order, *rules.parse_contract) if len(s) >= 20
    ]
    # v1.1.7 (TASK-2026-08-11-main-026): §11.1 명령 문자열도 판정 대상이다.
    # `wk session-start --help` 같은 손 사본 7곳이 이 검사의 사각지대였다 —
    # §11.1 개명 시 정본과 주입 렌더러만 움직이고 사본은 낡는다. 명령은 짧지만
    # `wk ` 접두가 충분히 특이해 위양성이 없다 (렌더러는 `find_memory_command` 로
    # 꺼내 쓰므로 리터럴이 남아 있으면 그 자체가 사본이다).
    command_literals = [cmd for _purpose, cmd in rules.memory_commands]
    return sentence_literals + command_literals


def _detect_copies(text: str) -> list[str]:
    return [lit for lit in _rule_literals() if lit in text]


def test_renderers_have_no_rule_literals() -> None:
    found = _detect_copies(RENDERERS.read_text(encoding="utf-8"))
    _record(
        "test_renderers_have_no_rule_literals",
        not found,
        f"{len(found)}개 문장이 렌더러에 직접 박혀 있다: {found[:2]}",
    )


# --- Case 3 ----------------------------------------------------------------


def test_generated_entrypoints_carry_rules() -> None:
    rules = load_standard_rules(SOURCE_ROOT)
    verify = next((p for p in rules.principles if "검증" in p), rules.principles[0])
    close = rules.close_order
    # §11 은 표(명령)와 bullet(계약) 두 축이라 각각 한 개씩 대표를 뽑아 본다.
    memory_cmd = rules.memory_commands[0][1]
    contract_probe = rules.parse_contract[0]

    harnesses = sorted(set(PRIMARY_ENTRYPOINTS) | set(EXEMPT_HARNESSES))
    args: list[str] = []
    for name in harnesses:
        args += ["--harness", name]

    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "target"
        target.mkdir(parents=True)
        completed = subprocess.run(
            [
                sys.executable, str(BOOTSTRAP_SCRIPT),
                "--target-root", str(target),
                "--project-slug", "rule_probe",
                "--project-name", "Rule Probe",
                "--adoption-mode", "existing",
                "--no-interactive",
                *args,
            ],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        if completed.returncode != 0:
            _record("test_generated_entrypoints_carry_rules", False,
                    f"bootstrap 실패: {completed.stderr[-300:]}")
            return

        missing: list[str] = []
        for harness, relpath in sorted(PRIMARY_ENTRYPOINTS.items()):
            path = target / relpath
            if not path.exists():
                missing.append(f"{harness}: {relpath} 미생성")
                continue
            text = path.read_text(encoding="utf-8")
            if verify not in text:
                missing.append(f"{harness}: §1 원칙 누락")
            if close not in text:
                missing.append(f"{harness}: §8 종료 순서 누락")
            # v1.1.7+ (TASK-2026-08-11-main-022): §11 메모리 갱신 경로.
            # 진입점이 "메모리 문서를 갱신하라" 고 지시하면서 **방법을 안 알려주면**
            # 에이전트는 손으로 쓰고, 그 순간 §11.2 파싱 계약이 조용히 깨진다
            # (실측: 렌더러 32개 중 26개가 그 상태였다 — TASK-020 전수검사).
            if memory_cmd not in text:
                missing.append(f"{harness}: §11 메모리 갱신 경로 누락")
            if contract_probe not in text:
                missing.append(f"{harness}: §11.2 파싱 계약 누락")

    _record("test_generated_entrypoints_carry_rules", not missing, "; ".join(missing[:4]))


# --- Case 4 ----------------------------------------------------------------


def test_distributed_core_matches_canonical() -> None:
    if not DISTRIBUTED_CORE.is_dir():
        _record("test_distributed_core_matches_canonical", True, "배포본 없음 (skip)")
        return
    drifted: list[str] = []
    for copy_path in sorted(DISTRIBUTED_CORE.glob("*.md")):
        canonical = SOURCE_ROOT / "core" / copy_path.name
        if not canonical.exists():
            continue
        if _strip_marker(copy_path.read_text(encoding="utf-8")) != canonical.read_text(encoding="utf-8"):
            drifted.append(copy_path.name)
    _record(
        "test_distributed_core_matches_canonical",
        not drifted,
        f"{len(drifted)}개 사본이 정본과 다르다: {drifted[:3]}",
    )


# --- Case 5 ----------------------------------------------------------------


def test_detector_catches_injected_copy() -> None:
    rules = load_standard_rules(SOURCE_ROOT)
    injected = f'    text = "{rules.close_order}"\n'
    # v1.1.7: §11.1 명령 사본과 §11.2 계약 bullet 사본도 잡아야 한다 (되주입 3종).
    injected_cmd = f'    command = "{rules.memory_commands[0][1]} --help"\n'
    injected_contract = f'    rule = "{rules.parse_contract[0]}"\n'
    _record(
        "test_detector_catches_injected_copy",
        bool(_detect_copies(injected))
        and bool(_detect_copies(injected_cmd))
        and bool(_detect_copies(injected_contract)),
        "주입한 사본을 탐지기가 잡지 못했다 — 탐지기가 죽어 있다",
    )



# --- Case 6 ----------------------------------------------------------------


def test_shared_entrypoint_merges_instead_of_overwriting() -> None:
    """같은 파일을 쓰는 두 하네스를 함께 고르면 **덮어쓰지 않고 합쳐진다** (v1.0.2).

    codex/opencode 와 pi-dev 는 둘 다 root `AGENTS.md` 를 읽는다. 이전에는 나중에
    도는 pi-dev 가 codex 판을 조용히 덮어써서 한쪽 지침이 통째로 사라졌고, manifest 는
    두 key 로 *두 파일이 생긴 것처럼* 보고했다. 파일이 하나뿐이면 답은 합치기다.

    동시에, 합친 결과에 **생성 블록이 두 번 들어가면 안 된다** — 한 파일 안의 사본도
    사본이고, 나중에 한쪽만 고쳐지면 갈라진다.
    """
    rules = load_standard_rules(SOURCE_ROOT)
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "target"
        target.mkdir(parents=True)
        completed = subprocess.run(
            [
                sys.executable, str(BOOTSTRAP_SCRIPT),
                "--target-root", str(target),
                "--project-slug", "shared_entry",
                "--project-name", "Shared Entry",
                "--adoption-mode", "existing",
                "--no-interactive",
                "--harness", "codex", "--harness", "pi-dev",
            ],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        if completed.returncode != 0:
            _record("test_shared_entrypoint_merges_instead_of_overwriting", False,
                    f"bootstrap 실패: {completed.stderr[-300:]}")
            return
        agents = target / "AGENTS.md"
        if not agents.exists():
            _record("test_shared_entrypoint_merges_instead_of_overwriting", False, "AGENTS.md 미생성")
            return
        text = agents.read_text(encoding="utf-8")

    problems: list[str] = []
    if "Codex" not in text:
        problems.append("codex 지침이 사라졌다 (덮어쓰기 회귀)")
    if "Pi Coding Agent" not in text:
        problems.append("pi-dev 지침이 사라졌다")
    if text.count(rules.close_order) != 1:
        problems.append(f"§8 종료 순서가 {text.count(rules.close_order)}회 (정확히 1회여야 한다)")

    _record("test_shared_entrypoint_merges_instead_of_overwriting", not problems, "; ".join(problems))



# --- Case 7 ----------------------------------------------------------------


def test_entrypoint_paths_match_generated_layout() -> None:
    """진입점이 가리키는 상태 문서 경로가 **실제로 생성된 것과 일치한다** (v1.0.2).

    bootstrap 은 평평한 `active/` 를 만드는데 진입점은 그 경로를 적고, 런타임은
    branch-scoped 를 먼저 보는 — 세 층이 서로 다른 곳을 가리키고 있었다. 문서가
    가리키는 곳에 파일이 없으면 에이전트는 첫 단계에서 길을 잃는다.

    `<branch>` 는 문서용 placeholder 이므로 실제 branch slug 로 치환해서 확인한다.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "target"
        target.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(target)], capture_output=True, check=False)
        completed = subprocess.run(
            [
                sys.executable, str(BOOTSTRAP_SCRIPT),
                "--target-root", str(target),
                "--project-slug", "layout_probe",
                "--project-name", "Layout Probe",
                "--adoption-mode", "existing",
                "--no-interactive",
                "--harness", "claude-code",
            ],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        if completed.returncode != 0:
            _record("test_entrypoint_paths_match_generated_layout", False,
                    f"bootstrap 실패: {completed.stderr[-300:]}")
            return

        entry = target / "CLAUDE.md"
        text = entry.read_text(encoding="utf-8")
        # 문서에 적힌 memory 경로를 모아 실제 존재를 확인한다.
        # `(있으면)` 으로 표기된 줄은 **선택** 경로다 — 부재가 정상이므로 제외한다.
        lines = [ln for ln in text.splitlines() if "(있으면)" not in ln]
        referenced = sorted(set(re.findall(
            r"ai-workflow/memory/active/[A-Za-z0-9_<>./-]+", "\n".join(lines))))
        missing: list[str] = []
        for ref in referenced:
            concrete = ref.replace("<branch>", "main").rstrip("/.")
            if not (target / concrete).exists():
                missing.append(ref)

    _record(
        "test_entrypoint_paths_match_generated_layout",
        bool(referenced) and not missing,
        f"진입점이 가리키는데 생성되지 않은 경로: {missing}" if missing else "진입점에 memory 경로 참조가 없다",
    )


# --- Case 8 ----------------------------------------------------------------


def test_harness_registry_fully_classified() -> None:
    """PRIMARY ∪ EXEMPT == SUPPORTED_HARNESSES — 미분류 하네스는 없다 (v1.1.7).

    이 검사의 순회는 두 dict 의 합집합이라, 레지스트리에만 등록된 하네스는 **아무
    판정도 받지 않고 조용히 빠져나갔다** (실측: `mavis` 가 그 상태였다 —
    TASK-2026-08-11-main-026). "새 하네스가 §11 을 안 실으면 검사가 잡는다" 는
    보장은 이 단언이 있어야 성립한다. 겹치는 분류(양쪽 모두 등재)도 오류다.
    """
    scripts_dir = SOURCE_ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from workflow_kit.bootstrap_lib.harnesses import SUPPORTED_HARNESSES  # noqa: E402

    classified = set(PRIMARY_ENTRYPOINTS) | set(EXEMPT_HARNESSES)
    registered = set(SUPPORTED_HARNESSES)
    overlap = set(PRIMARY_ENTRYPOINTS) & set(EXEMPT_HARNESSES)
    problems: list[str] = []
    if registered - classified:
        problems.append(f"미분류 하네스 (PRIMARY 나 EXEMPT 에 넣어라): {sorted(registered - classified)}")
    if classified - registered:
        problems.append(f"레지스트리에 없는 유령 분류: {sorted(classified - registered)}")
    if overlap:
        problems.append(f"양쪽에 모두 등재: {sorted(overlap)}")
    _record("test_harness_registry_fully_classified", not problems, "; ".join(problems))


# --- Case 9 ----------------------------------------------------------------

#: §11 을 실어야 하는 보조 렌더러 (TASK-2026-08-11-main-028 — TASK-020 1순위).
#: 주요 진입점(case 3)과 달리 bootstrap 산출물이 아니라 렌더러 출력을 직접 판정한다.
SECONDARY_INJECTED_RENDERERS: tuple[str, ...] = (
    "render_minimax_orchestrator",
    "render_opencode_agent",
    "render_pi_dev_agents",
    "render_grok_build_skill",
    "render_codewhale_skill",
    "render_custom_skill_template",
)

#: §11 미주입 잔여 렌더러 **원장** — 이유와 함께 명시한다 (조용한 사각지대 금지).
#: 여기 든 렌더러가 §11 을 싣게 되면 이 원장에서 빼야 검사가 통과한다 (양방향).
SECONDARY_UNINJECTED_RENDERERS: dict[str, str] = {
    "render_minimax_config_example": "설정 예시 — 규칙 산문을 싣는 문서가 아니다",
    "render_minimax_doc_worker": "worker 페르소나 — 메모리 갱신은 orchestrator 의 책임 (분리 유지)",
    "render_opencode_config": "설정 파일 — 규칙 산문을 싣는 문서가 아니다",
    "render_opencode_worker_agent": "worker 페르소나 — 메모리 갱신은 orchestrator 의 책임",
    "render_opencode_doc_worker_agent": "worker 페르소나 — 메모리 갱신은 orchestrator 의 책임",
    "render_opencode_code_worker_agent": "worker 페르소나 — 메모리 갱신은 orchestrator 의 책임",
    "render_opencode_validation_worker_agent": "worker 페르소나 — 메모리 갱신은 orchestrator 의 책임",
    "render_aider_config_example": "설정 예시 — 규칙 산문을 싣는 문서가 아니다",
}


def test_secondary_renderers_carry_or_declare() -> None:
    """보조 렌더러의 §11 상태를 **전수 판정**한다 (v1.1.7, TASK-028).

    TASK-020 전수검사에서 26개 렌더러가 메모리 갱신을 지시하며 방법을 안 알려줬다.
    주요 진입점 8개는 case 3 이, 직접 주입 4개는 case 2 의 리터럴 검출이 덮는다 —
    남은 보조 렌더러는 여기서: 주입 목록은 §11 을 실어야 하고, 미주입 원장은
    이유와 함께 §11 이 **없어야** 한다 (원장이 낡으면 그 자체가 red).
    """
    import argparse
    import collections
    import inspect

    scripts_dir = SOURCE_ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from workflow_kit.bootstrap_lib.harnesses import renderers as renderer_module  # noqa: E402
    from workflow_kit.bootstrap_lib.paths import Paths  # noqa: E402

    rules = load_standard_rules(SOURCE_ROOT)
    memory_cmd = rules.memory_commands[0][1]
    contract_probe = rules.parse_contract[0]
    dummy_args = argparse.Namespace(today="2026-01-01", adoption_mode="existing", force=True)
    dummy_context: dict[str, object] = collections.defaultdict(lambda: "probe")
    dummy_paths = Paths(*[Path("/nonexistent/probe")] * 13)
    by_param = {"args": dummy_args, "context": dummy_context, "paths": dummy_paths}

    def _render(name: str) -> str:
        fn = getattr(renderer_module, name)
        # 렌더러 시그니처가 (args, context) / (args, paths) / () 로 갈린다 —
        # 파라미터 이름으로 dummy 를 맞춘다.
        kwargs = {p: by_param[p] for p in inspect.signature(fn).parameters if p in by_param}
        return str(fn(**kwargs))

    problems: list[str] = []
    for name in SECONDARY_INJECTED_RENDERERS:
        out = _render(name)
        if memory_cmd not in out:
            problems.append(f"{name}: §11 갱신 명령 누락")
        if contract_probe not in out:
            problems.append(f"{name}: §11.2 파싱 계약 누락")
    for name in SECONDARY_UNINJECTED_RENDERERS:
        out = _render(name)
        if memory_cmd in out:
            problems.append(f"{name}: §11 이 실렸는데 미주입 원장에 남아 있다 — 원장을 갱신하라")
    overlap = set(SECONDARY_INJECTED_RENDERERS) & set(SECONDARY_UNINJECTED_RENDERERS)
    if overlap:
        problems.append(f"양쪽에 모두 등재: {sorted(overlap)}")
    _record("test_secondary_renderers_carry_or_declare", not problems, "; ".join(problems[:4]))


def main() -> int:
    test_snapshot_matches_standard()
    test_renderers_have_no_rule_literals()
    test_generated_entrypoints_carry_rules()
    test_distributed_core_matches_canonical()
    test_detector_catches_injected_copy()
    test_shared_entrypoint_merges_instead_of_overwriting()
    test_entrypoint_paths_match_generated_layout()
    test_harness_registry_fully_classified()
    test_secondary_renderers_carry_or_declare()
    total = 9
    print(f"\n{total - len(FAILURES)}/{total} passed")
    if FAILURES:
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
