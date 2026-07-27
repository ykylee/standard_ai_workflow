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

Test list (5 case):
1. test_snapshot_matches_standard
2. test_renderers_have_no_rule_literals
3. test_generated_entrypoints_carry_rules
4. test_distributed_core_matches_canonical
5. test_detector_catches_injected_copy

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

RENDERERS = SOURCE_ROOT / "scripts" / "bootstrap_lib" / "harnesses" / "renderers.py"
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
    "opencode": ".opencode/skills/standard-ai-workflow/SKILL.md",
}

#: 규칙 문서를 만들지 않는 하네스 — 이유를 남긴다 (조용히 빠져나가는 경로를 두지 않는다).
EXEMPT_HARNESSES: dict[str, str] = {
    "goose": "config-only overlay — 산문 진입점 없이 .goose/config.yaml 의 read_files 로 상태 문서를 지정한다",
    "custom": "사용자가 채우는 빈 템플릿 — 규칙을 미리 박으면 템플릿 목적에 어긋난다",
    "codex": "AGENTS.md 를 pi-dev 와 공유한다 — 파일 소유가 겹쳐 단독 판정이 불가 (별도 이슈)",
    "pi-dev": "번호 장 구조라 §1 을 자체 문장으로 서술 — §8 만 정본에서 주입한다",
    "codewhale": "보조 SKILL.md — §8 만 정본에서 주입한다",
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
    return [s for s in (*rules.principles, rules.close_order) if len(s) >= 20]


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
    _record(
        "test_detector_catches_injected_copy",
        bool(_detect_copies(injected)),
        "주입한 사본을 탐지기가 잡지 못했다 — 탐지기가 죽어 있다",
    )


def main() -> int:
    test_snapshot_matches_standard()
    test_renderers_have_no_rule_literals()
    test_generated_entrypoints_carry_rules()
    test_distributed_core_matches_canonical()
    test_detector_catches_injected_copy()
    total = 5
    print(f"\n{total - len(FAILURES)}/{total} passed")
    if FAILURES:
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
