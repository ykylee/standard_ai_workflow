#!/usr/bin/env python3
"""체크인된 예제 `state.json` 과 생성기 계약을 고정한다 (4 cases).

## 왜 필요한가 (TASK-2026-09-07-main-003)

`workflow-source/examples/acme_delivery_platform/state.json` 은 저장소에 체크인된
**생성 산출물**인데, 어느 검사도 그것을 생성기 출력과 대조하지 않았다. 기존 두
검사는 같은 입력으로 **tmpdir 에 새로 생성**해 느슨한 속성만 봤다:

  - `check_generate_workflow_state` — status/schema_version/generated_at 보존,
    current_focus 와 next_documents 가 비지 않았는가
  - `check_workflow_state_generator` — 경로가 상대경로인가

둘 다 체크인본을 **읽지 않는다**. 그래서 산출물이 생성기와 갈라져도 조용했고,
2026-09-07 실측에서 최상위 key 3개(`source_of_truth` / `session` /
`next_documents`)가 어긋나 있었다.

그 침묵이 실제로 살려 둔 결함 두 개가 이 검사의 case 2·3·4 다:

  - **main-001** — handoff 경로에만 legacy fallback 이 없었다. 디렉터리는 전부
    `_branch_scoped_dir` 를 지나는데 handoff 만 인라인 조립이었다. 평평한 layout
    (예제가 바로 그 모양) 에서 handoff 를 **있는데도** 못 찾아 state.json 의
    `current_baseline` / `current_axis` / `recent_done_items` 가 통째로 비었다.
    경고는 없다 — 없으면 그냥 빈 값이라 정상으로 보인다.
  - **main-002** — `cast(list[str], handoff.get("constraints"))` 가 실제로는
    `str` 인 값을 목록이라 **선언만** 했다. 문자열을 iterate 해
    `environment_constraints` 가 한 글자씩 쪼개졌고, `cast` 가 mypy strict 를
    통과시켜 타입 축도 이것을 볼 수 없었다.

이 저장소에서 main-002 가 안 보인 이유가 중요하다: main 의 handoff 에는
`주요 제약` 줄이 없어 값이 늘 `[]` 였다. **그 줄을 가진 유일한 코퍼스가 예제**
였고, 예제 산출물을 보는 검사가 없었다. 결함이 어려웠던 게 아니라 재는 자리가
없었다.

## 판정 설계

- case 1 은 **산출물 대조**다. `generated_at` 은 제외한다 — 날짜만 다른 것은
  내용 drift 가 아니고, 포함하면 이 검사가 매일 red 가 된다
  (`wk refresh-state --check` 와 같은 규약).
- case 2·4 는 **결함의 모양**을 직접 잰다. 산출물 대조만 두면 예제를 손대는
  순간 그 근거가 사라지므로, 합성 fixture 로 규칙 자체를 고정한다.
- case 3 은 **정적 판정**이다. 인라인 조립이 8곳까지 번진 것이 main-001 의
  뿌리라, 새 인라인이 늘어나는 것을 막는다. 허용 목록은 *만드는 쪽*뿐이다 —
  신규 생성은 항상 branch-scoped 라는 규약(`_branch_scoped_dir` docstring)이
  그대로 성립한다.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/examples/acme_delivery_platform/*",
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.normalize import normalize_constraint_values  # noqa: E402
from workflow_kit.common.paths import (  # noqa: E402
    HANDOFF_FILENAME,
    branch_for_workspace,
    workflow_handoff_path,
)
from workflow_kit.common.state.cache import refresh_workflow_state_cache  # noqa: E402

EXAMPLE_ROOT = SOURCE_ROOT / "examples" / "acme_delivery_platform"

#: `session_handoff.md` 경로를 **직접 조립해도 되는** 자리와 그 근거.
#: 전부 *만드는 쪽* 이거나 파일명 정본 자신이다. 읽는 쪽은 예외 없이
#: `workflow_handoff_path` / `path_in_active` 를 지나야 한다 — 그 둘만이
#: branch-scoped→legacy fallback 을 들고 있다.
INLINE_ALLOWED: dict[str, str] = {
    "workflow_kit/common/paths.py": "정본 — fallback 규칙과 파일명이 여기 산다",
    "workflow_kit/tools/seed_workspace_memory.py": "신규 생성 (writer) — 만들 자리는 항상 branch-scoped",
    "workflow_kit/bootstrap_lib/paths.py": "신규 생성 (writer) — bootstrap 이 emit 할 경로를 정한다",
    "workflow_kit/common/ingest.py": "선언된 legacy 경로 세트 API — 한 호출 안에서 규약을 섞지 않는다",
}

#: 경로 조립으로 볼 토큰. 리터럴과 정본 상수 양쪽을 본다 — 상수로 바꿔 적는 것도
#: fallback 을 잃는 점에서는 인라인과 같다.
_JOIN_TOKENS = (f'/ "{HANDOFF_FILENAME}"', "/ HANDOFF_FILENAME", "/ HANDOFF_NAME")


def _seed_flat_workspace(root: Path) -> Path:
    """평평한(미마이그레이션) layout 의 최소 workspace 를 만든다.

    handoff 를 `<root>/session_handoff.md` 에 둔다 — branch-scoped
    (`<root>/<branch>/session_handoff.md`) 가 **아니다**. main-001 이 놓치던
    바로 그 배치다.
    """
    (root / "backlog").mkdir(parents=True, exist_ok=True)
    (root / "PROJECT_PROFILE.md").write_text(
        "# Project Profile\n\n- 프로젝트명: Flat Fixture\n", encoding="utf-8"
    )
    (root / "session_handoff.md").write_text(
        "# Session Handoff\n\n"
        "- 현재 기준선: 평평한 layout 의 기준선 한 줄\n"
        "- 현재 주 작업 축: 평평한 layout 의 작업 축\n"
        "- 주요 제약: VPN 없이는 접근 불가\n",
        encoding="utf-8",
    )
    (root / "backlog" / "2026-04-18.md").write_text("# Backlog Index\n\n## Tasks\n", encoding="utf-8")
    return root / "PROJECT_PROFILE.md"


def case_1_checked_in_artifact_matches_generator() -> bool:
    """체크인된 예제 산출물이 현재 생성기 출력과 같은가 (`generated_at` 제외)."""
    print("case_1: 체크인된 예제 state.json vs 생성기 출력")
    state_path = EXAMPLE_ROOT / "state.json"
    if not state_path.is_file():
        print(f"  FAIL: 예제 산출물이 없다: {state_path}")
        return False
    current = json.loads(state_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="example-state-") as tmp:
        out = Path(tmp) / "state.json"
        result = refresh_workflow_state_cache(
            project_profile_path=EXAMPLE_ROOT / "PROJECT_PROFILE.md",
            output_path=out,
            # 날짜만 다른 것은 drift 가 아니다 — 현재 파일의 값으로 재생성한다.
            generated_at=str(current.get("generated_at", "")),
        )
        if result["status"] != "refreshed":
            print(f"  FAIL: 생성기가 재생성하지 못했다 (status={result['status']})")
            return False
        regenerated = json.loads(out.read_text(encoding="utf-8"))
    drifted = sorted(
        k for k in set(current) | set(regenerated) if current.get(k) != regenerated.get(k)
    )
    if drifted:
        print(f"  FAIL: 어긋난 최상위 key {len(drifted)}개 — {drifted}")
        print("        예제 state.json 은 생성물이다. 손으로 고치지 말고 재생성하라:")
        print("        wk refresh-state --project-profile-path "
              "workflow-source/examples/acme_delivery_platform/PROJECT_PROFILE.md")
        return False
    print(f"  [info] 최상위 key {len(regenerated)}개 전부 일치")
    return True


def case_2_flat_layout_handoff_is_found() -> bool:
    """평평한 layout 의 handoff 를 정본이 찾고, 그 내용이 state 에 실리는가."""
    print("case_2: 평평한 layout 의 handoff legacy fallback")
    with tempfile.TemporaryDirectory(prefix="flat-ws-") as tmp:
        root = Path(tmp) / "ws"
        profile = _seed_flat_workspace(root)
        # `resolve()` 로 맞춘다 — macOS 의 `/var` → `/private/var` symlink 때문에
        # 조립한 경로와 정본의 반환이 문자열로는 다르다.
        resolved = workflow_handoff_path(profile).resolve()
        if resolved != (root / HANDOFF_FILENAME).resolve():
            print(f"  FAIL: 정본이 평평한 handoff 를 가리키지 않는다 — {resolved}")
            return False
        out = Path(tmp) / "state.json"
        refresh_workflow_state_cache(
            project_profile_path=profile, output_path=out, generated_at="2026-09-07"
        )
        state = json.loads(out.read_text(encoding="utf-8"))
        session = state["session"]
        if not session.get("current_baseline") or not session.get("current_axis"):
            print("  FAIL: handoff 유래 필드가 비었다 — 파일은 있는데 생성기가 못 읽었다 "
                  f"(current_baseline={session.get('current_baseline')!r})")
            return False
        if state["source_of_truth"].get("session_handoff_path") is None:
            print("  FAIL: source_of_truth.session_handoff_path 가 null 이다")
            return False
    print("  [info] 평평한 handoff 를 찾고 current_baseline / current_axis 가 실렸다")
    return True


def case_3_no_inline_handoff_path_assembly() -> bool:
    """읽는 쪽이 handoff 경로를 직접 조립하지 않는가 (정적)."""
    print("case_3: handoff 경로 인라인 조립 금지")
    offenders: list[str] = []
    for path in sorted((SOURCE_ROOT / "workflow_kit").rglob("*.py")):
        rel = path.relative_to(SOURCE_ROOT).as_posix()
        if rel in INLINE_ALLOWED:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(token in line for token in _JOIN_TOKENS):
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    if offenders:
        print(f"  FAIL: 정본을 지나지 않는 handoff 경로 조립 {len(offenders)}건")
        for entry in offenders:
            print(f"        {entry}")
        print("        읽는 쪽은 `workflow_handoff_path(profile)` 또는")
        print("        `path_in_active(active_dir, HANDOFF_FILENAME, branch)` 를 쓴다 —")
        print("        인라인 조립에는 미마이그레이션 저장소용 legacy fallback 이 없다.")
        return False
    print(f"  [info] 인라인 0건 (허용 {len(INLINE_ALLOWED)}곳은 전부 만드는 쪽/정본)")
    return True


def case_4_constraints_are_not_split_into_characters() -> bool:
    """문자열 제약이 한 항목으로 남는가 — 문자 단위 분해 회귀 방지."""
    print("case_4: 제약 문자열이 한 글자씩 쪼개지지 않는다")
    sentence = "VPN 미연결 상태에서는 staging API 및 운영 콘솔 접근 불가"
    got = normalize_constraint_values(sentence)
    if got != [sentence]:
        print(f"  FAIL: 문자열 하나가 {len(got)}개 항목이 됐다 — {got[:6]}...")
        return False
    # 목록 입력은 펼치고, None 과 플레이스홀더는 버린다.
    if normalize_constraint_values([sentence, "TODO: 미정"], None, "  ") != [sentence]:
        print("  FAIL: 목록/None/플레이스홀더 처리가 계약과 다르다")
        return False
    # 실제 산출물에도 회귀가 없어야 한다 — 단위만 재면 배선이 빠져도 통과한다.
    state = json.loads((EXAMPLE_ROOT / "state.json").read_text(encoding="utf-8"))
    for item in state["session"]["environment_constraints"]:
        if len(item) <= 1:
            print(f"  FAIL: 예제 산출물에 한 글자 제약이 남아 있다 — {item!r}")
            return False
    print("  [info] 단위 계약과 예제 산출물 양쪽에서 문장이 온전하다")
    return True


def case_5_artifact_does_not_embed_the_repo_branch() -> bool:
    """체크인된 산출물에 **저장소의 현재 브랜치 이름**이 박히지 않았는가.

    ## 왜 별도 case 인가 (2축 게이트 실측)

    case 1 은 `native` 축에서 통과하고 `slash` 축에서만 red 였다. 예제에
    `sessions/` 가 없으면 `_branch_scoped_dir` 이 legacy 로 못 떨어지고
    branch-scoped 를 반환하는데, 그 branch 는 **예제의 것이 아니라 이 저장소를
    체크아웃한 브랜치**다. 그래서 `sessions_dir` 이 `main` 에서는
    `main/sessions`, `feature/x` 에서는 `feature/x/sessions` 가 된다 —
    체크인된 샘플 산출물이 체크아웃한 브랜치에 따라 달라지므로 **어떤 값으로
    커밋해도 다른 축에서 red** 다.

    `main` 에서만 재면 이 차이가 0이라 안 보인다. CLAUDE.md 가 브랜치 매트릭스를
    push 전에 로컬에서 돌리라고 적은 이유가 이것이고, 실제로 2026-08-10 에
    같은 모양으로 **15연속 CI red 인 동안 로컬은 계속 green** 이었다.

    case 1 이 이미 red 를 내지만 그것은 *그 축에서 돌려야* 보인다. 이 case 는
    축과 무관하게 잡는다 — 산출물에 브랜치 이름이 있으면 그 자체가 결함이다.
    """
    print("case_5: 산출물에 저장소 브랜치 이름이 박히지 않았는가")
    branch = branch_for_workspace(REPO_ROOT)
    raw = (EXAMPLE_ROOT / "state.json").read_text(encoding="utf-8")
    # 브랜치 이름이 흔한 단어일 수 있으므로 **경로 segment** 로만 본다.
    needles = [f"{branch}/", f"/{branch}"]
    hits = [n for n in needles if n in raw]
    if hits:
        print(f"  FAIL: 산출물이 저장소 브랜치 {branch!r} 를 경로에 담고 있다 — {hits}")
        print("        예제 workspace 에 그 leaf 디렉터리(예: `sessions/`)가 실재하면")
        print("        경로 해석이 legacy 로 떨어져 브랜치와 무관해진다.")
        return False
    print(f"  [info] 저장소 브랜치 {branch!r} 가 산출물 경로에 없다")
    return True


def main() -> int:
    cases = [
        ("case_1_checked_in_artifact_matches_generator", case_1_checked_in_artifact_matches_generator),
        ("case_2_flat_layout_handoff_is_found", case_2_flat_layout_handoff_is_found),
        ("case_3_no_inline_handoff_path_assembly", case_3_no_inline_handoff_path_assembly),
        ("case_4_constraints_are_not_split_into_characters", case_4_constraints_are_not_split_into_characters),
        ("case_5_artifact_does_not_embed_the_repo_branch", case_5_artifact_does_not_embed_the_repo_branch),
    ]
    results = [(name, fn()) for name, fn in cases]
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== {passed}/{len(cases)} PASS ===")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
