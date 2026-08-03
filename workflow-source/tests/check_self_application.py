#!/usr/bin/env python3
"""이 저장소가 **자기 워크플로우를 스스로 따르는가** (v1.0.2+).

## 왜 필요한가

이 저장소는 11개 하네스용 진입점과 상태 문서 규약을 만들어 배포한다. 그런데
2026-07-27 조사에서 드러난 것은:

- 루트에 `CLAUDE.md` 도 `AGENTS.md` 도 **없었다**. 진입점을 배포하는 저장소가 자기
  진입점을 한 번도 만든 적이 없다.
- `session_handoff.md` 가 없어 `session-start` 가 `missing_required_document` 로
  **실행조차 되지 않았다**. 그런데 린터는 같은 시각 `status: ok` 였다.
- 배포본 `ai-workflow/core/` 21개 문서가 전부 정본과 갈라져 있었다.

배포하는 것을 우리가 쓰지 않으면 그것이 동작하는지 알 방법이 없다. 그래서 자기 적용을
**문서의 다짐이 아니라 검사**로 둔다 (`core/workflow_design_principles.md` §5).

## 판정 규칙

1. **원리 ↔ 검사 매핑이 실재한다** — 설계 원칙 문서 §5.1 표가 가리키는 검사 파일이
   전부 존재해야 한다. 없는 검사를 가리키는 표는 지켜지는 것처럼 보이는 장식이다.
2. **자기 진입점을 가진다** — 루트 진입점이 존재하고, 정본에서 생성된 규칙(§1 · §8)을
   담고 있어야 한다.
3. **자기 상태를 자기 규약대로 둔다** — 브랜치 메모리에 state / handoff / backlog 가
   모두 있어야 한다.
4. **자기 린터가 자기 저장소에서 통과한다** — issue 0.
5. **자기 session-start 가 자기 저장소에서 돈다** — `status: ok`.

**한계 (과장하지 않는다)**: 2번은 파일 내용만 본다. 실제 에이전트 세션이 그 파일을
로드하는지까지는 확인하지 못한다. 4·5번은 이 저장소의 현재 상태에 의존하므로, 소비자
프로젝트에서는 의미가 없다 — 그래서 이 검사는 배포 대상이 아니라 우리 tests/ 에만 둔다.

Test list (5 case):
1. test_principle_check_mapping_exists
2. test_repo_has_own_entrypoints
3. test_repo_has_own_state_documents
4. test_own_linter_passes_on_own_repo
5. test_own_session_start_runs_on_own_repo

Cross-ref: `core/workflow_design_principles.md` §5, `core/global_workflow_standard.md` §8.4.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.paths import (  # noqa: E402
    memory_active_dir,
    state_path_for_workspace,
)
from workflow_kit.common.standard_rules import load_standard_rules  # noqa: E402

PRINCIPLES_DOC = SOURCE_ROOT / "core" / "workflow_design_principles.md"

#: 반드시 있어야 하는 진입점. `.gitignore` 의 "Workflow layer (selective tracking)" 이
#: `/AGENTS.md` · `/GEMINI.md` · `/ANTIGRAVITY.md` 를 의도적으로 제외하므로, 그것들을
#: 요구하면 **깨끗한 clone 과 CI 에서 반드시 실패한다**. 추적되는 진입점만 요구한다.
REQUIRED_ENTRYPOINTS = ("CLAUDE.md",)
#: 있으면 내용까지 검증하되, 없다고 실패시키지는 않는 진입점 (로컬 전용 산출물).
OPTIONAL_ENTRYPOINTS = ("AGENTS.md", "GEMINI.md", "ANTIGRAVITY.md")
LINTER = SOURCE_ROOT / "skills" / "workflow-linter" / "scripts" / "run_workflow_linter.py"
SESSION_START = SOURCE_ROOT / "skills" / "session-start" / "scripts" / "run_session_start.py"
PROFILE = REPO_ROOT / "docs" / "PROJECT_PROFILE.md"

FAILURES: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case}{(' — ' + detail) if detail else ''}")
        FAILURES.append(case)


def _branch_dir() -> Path:
    """이 저장소의 현재 브랜치 메모리 디렉터리."""
    return state_path_for_workspace(REPO_ROOT).parent


def _self_application_target() -> tuple[Path, str]:
    """자기 적용을 **어느 브랜치 메모리로** 검증할지 + 그 근거.

    이 검사가 묻는 것은 "이 *저장소* 가 자기 kit 을 쓰는가" 이지 "이 *브랜치* 에서
    세션을 시작한 적이 있는가" 가 아니다. 그런데 현재 브랜치 디렉터리만 보다 보니,
    **session-start 를 아직 안 돌린 새 브랜치에서는 무조건 3건이 FAIL** 했다.
    smoke 는 `branches: ["**"]` 로 모든 브랜치·PR 에서 도므로, 브랜치를 하나 따는
    순간 자기 변경과 무관하게 CI 가 red 가 된다 — 위양성을 내는 검사는 무시당하고,
    그러면 같은 검사가 잡아 줄 진짜 결함도 함께 무시된다(§2.48).

    브랜치 메모리 부재는 **결함이 아니라 선언된 상태**다(CLAUDE.md self-bootstrap:
    state.json 이 없으면 session-start 는 graceful skip 하고 scaffold 를 제안한다).
    그래서 없으면 기존 브랜치 메모리로 검증하되, **바꿔치기한 사실을 반드시 밝힌다** —
    조용히 대체하면 "이 브랜치가 자기 적용된다" 는 거짓을 말하게 된다.
    """
    current = _branch_dir()
    if (current / "state.json").is_file():
        return current, "current-branch"

    active = memory_active_dir(REPO_ROOT)
    fallbacks = sorted(
        (p.parent for p in active.rglob("state.json") if p.parent != current),
        key=lambda p: (p.name != "main", p.as_posix()),
    )
    if not fallbacks:
        return current, "none"
    chosen = fallbacks[0]
    return chosen, f"fallback:{chosen.relative_to(active).as_posix()}"


def _run_json(argv: list[str]) -> dict:
    completed = subprocess.run(argv, cwd=REPO_ROOT, capture_output=True, text=True)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"status": "error", "_stdout": completed.stdout[-400:], "_stderr": completed.stderr[-400:]}


# --- Case 1 ----------------------------------------------------------------


def test_principle_check_mapping_exists() -> None:
    if not PRINCIPLES_DOC.exists():
        _record("test_principle_check_mapping_exists", False, f"설계 원칙 문서가 없다: {PRINCIPLES_DOC}")
        return
    text = PRINCIPLES_DOC.read_text(encoding="utf-8")
    referenced = sorted(set(re.findall(r"`(tests/check_[a-z0-9_]+\.py)`", text)))
    missing = [rel for rel in referenced if not (SOURCE_ROOT / rel).exists()]
    _record(
        "test_principle_check_mapping_exists",
        bool(referenced) and not missing,
        f"참조 {len(referenced)}건 중 부재 {missing}" if missing else "매핑 표에 검사 참조가 없다",
    )


# --- Case 2 ----------------------------------------------------------------


def test_repo_has_own_entrypoints() -> None:
    rules = load_standard_rules(SOURCE_ROOT)
    verify = next((p for p in rules.principles if "검증" in p), rules.principles[0])
    problems: list[str] = []
    for name in (*REQUIRED_ENTRYPOINTS, *OPTIONAL_ENTRYPOINTS):
        path = REPO_ROOT / name
        if not path.exists():
            if name in REQUIRED_ENTRYPOINTS:
                problems.append(f"{name} 없음")
            continue
        text = path.read_text(encoding="utf-8")
        if verify not in text:
            problems.append(f"{name}: §1 원칙 누락")
        if rules.close_order not in text:
            problems.append(f"{name}: §8 종료 순서 누락")
    _record("test_repo_has_own_entrypoints", not problems, "; ".join(problems))


# --- Case 3 ----------------------------------------------------------------


def test_repo_has_own_state_documents() -> None:
    branch_dir, provenance = _self_application_target()
    if provenance == "none":
        _record("test_repo_has_own_state_documents", False,
                f"어느 브랜치에도 상태 문서가 없다 ({memory_active_dir(REPO_ROOT)})")
        return
    if provenance != "current-branch":
        print(f"  [info] 현재 브랜치({_branch_dir().name})에 상태 문서가 없어 "
              f"{provenance} 로 검증한다 — session-start 미실행 상태다")
    required = {
        "state.json": branch_dir / "state.json",
        "session_handoff.md": branch_dir / "session_handoff.md",
        "backlog/": branch_dir / "backlog",
    }
    missing = [f"{name} ({path})" for name, path in required.items() if not path.exists()]
    shared = memory_active_dir(REPO_ROOT)
    if not shared.is_dir():
        missing.append(f"active/ ({shared})")
    _record("test_repo_has_own_state_documents", not missing, "; ".join(missing))


# --- Case 4 ----------------------------------------------------------------


def test_own_linter_passes_on_own_repo() -> None:
    branch_dir, provenance = _self_application_target()
    # 경로를 **전부 명시**한다. state.json 만 넘기면 린터는 handoff/backlog 를 profile
    # 에서 *현재 브랜치* 기준으로 다시 해석하므로, fallback 대상과 갈라져
    # `missing_required_document` 가 난다 — 인자 하나만 바꾸면 나머지가 딴 데를 본다.
    backlogs = sorted((branch_dir / "backlog").glob("*.md"), reverse=True)
    argv = [
        sys.executable, str(LINTER),
        "--project-profile-path", str(PROFILE),
        "--state-json-path", str(branch_dir / "state.json"),
        "--session-handoff-path", str(branch_dir / "session_handoff.md"),
    ]
    if backlogs:
        argv += ["--latest-backlog-path", str(backlogs[0])]
    if provenance != "current-branch":
        print(f"  [info] 린터를 {provenance} 의 문서로 실행한다")
    result = _run_json(argv)
    issues = result.get("issues", [])
    _record(
        "test_own_linter_passes_on_own_repo",
        result.get("status") in ("ok", "success") and not issues,
        f"status={result.get('status')} issues={[i.get('code') for i in issues][:3]}",
    )


# --- Case 5 ----------------------------------------------------------------


def test_own_session_start_runs_on_own_repo() -> None:
    branch_dir, _ = _self_application_target()
    backlogs = sorted((branch_dir / "backlog").glob("*.md"), reverse=True)
    if not backlogs:
        _record("test_own_session_start_runs_on_own_repo", False, "backlog 문서가 없어 실행할 수 없다")
        return
    result = _run_json([
        sys.executable, str(SESSION_START),
        "--session-handoff-path", str(branch_dir / "session_handoff.md"),
        "--work-backlog-index-path", str(backlogs[0]),
        "--project-profile-path", str(PROFILE),
    ])
    _record(
        "test_own_session_start_runs_on_own_repo",
        result.get("status") in ("ok", "success"),
        f"status={result.get('status')} error={result.get('error_code') or result.get('error')}",
    )


def main() -> int:
    test_principle_check_mapping_exists()
    test_repo_has_own_entrypoints()
    test_repo_has_own_state_documents()
    test_own_linter_passes_on_own_repo()
    test_own_session_start_runs_on_own_repo()
    total = 5
    print(f"\n{total - len(FAILURES)}/{total} passed")
    if FAILURES:
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
