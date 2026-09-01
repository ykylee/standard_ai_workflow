#!/usr/bin/env python3
"""발행 게이트가 **필수 CI 워크플로 전부**를 보고, 기본이 차단인지 고정한다 (8 cases).

## 계보 (TASK-2026-09-01-main-005)

이전 게이트는 `gh run list --workflow mypy-strict.yml --limit 1` **하나**였고 그마저
advisory 였다. 결과:

- `smoke` 가 2026-08-30 `6d9ad763` 부터 **10 커밋 연속 red** 인 동안 게이트는 내내
  green 을 봤다 — `mypy-strict` 는 그 10 커밋 전부에서 success 였다.
- **v1.8.0 이 그 위에서 발행됐다.** 발행 커밋 `6c495e61` 실측:
  smoke=failure · mypy-strict=success · os-matrix=success · mcp-sdk-matrix=success.
- 릴리스 노트는 같은 시점에 `누적 smoke 276/276 PASS` 라고 적고 있었다. 그 줄은
  설계상 **사람의 주장**이고(`verify_release_note_smoke_count` 주석), 그 주장을 CI 와
  대조하는 자리가 없었다.

곁가지 결함도 둘 있었다 — 질의에 `--branch` 가 없어 다른 브랜치 run 이 섞일 수 있었고,
`--limit 1` 이라 HEAD 의 run 이 아직 없으면 **이전 커밋의 run** 을 봤다.

이 검사는 그 셋을 전부 고정한다. **판정은 주입한 run 으로 잰다** — 네트워크에 기대면
검사가 환경에 따라 흔들리고, 정작 판정 로직의 회귀는 못 잡는다.

8 cases:
  1) `REQUIRED_CI_WORKFLOWS` 가 선언돼 있고 `smoke` 를 포함한다
  2) 목록의 모든 이름이 `.github/workflows/` 에 실재한다 (오타·이름 변경 검출)
  3) 전부 success → 통과
  4) 하나라도 failure → 차단
  5) run 이 없으면(missing) 차단 — 모름은 통과가 아니다
  6) 아직 도는 중(pending)이면 차단
  7) gh 를 못 부르면 차단 (fetch_error)
  8) 질의가 sha 를 직접 지정한다 (`--commit`), `--limit 1` 최신-집기가 아니다
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: `.github/workflows/*` 는 case 2 가 **파일 이름**에 의존하는 자리다 (내용을 열지
#: 않으므로 meta-watch 는 '접근 0' 으로 본다 — 그 warn 은 감수한다). 워크플로 파일이
#: 이름을 바꾸면 이 검사가 반드시 돌아야 한다.
WATCHES = (
    ".github/workflows/*",
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.tools.release_pipeline import (  # noqa: E402
    REQUIRED_CI_WORKFLOWS,
    verify_required_ci,
)

PIPELINE_SRC = SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline.py"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

FAILURES: list[str] = []


def _record(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  PASS  {name}")
        return
    FAILURES.append(name)
    print(f"  FAIL  {name} — {detail}")


def _run(name: str, *, status: str = "completed", conclusion: str = "success") -> dict:
    return {"name": name, "status": status, "conclusion": conclusion, "databaseId": 1}


def _all_green() -> list[dict]:
    return [_run(n) for n in REQUIRED_CI_WORKFLOWS]


def case_1_required_list_declared() -> None:
    ok = bool(REQUIRED_CI_WORKFLOWS) and "smoke" in REQUIRED_CI_WORKFLOWS
    _record(
        "case_1_required_list_declared", ok,
        f"REQUIRED_CI_WORKFLOWS={REQUIRED_CI_WORKFLOWS!r} — 전량 검사(smoke)가 빠지면 "
        "이 게이트는 v1.8.0 을 막지 못한 그 게이트로 되돌아간다",
    )


def case_2_every_required_workflow_exists() -> None:
    names = set()
    for f in WORKFLOWS_DIR.glob("*.yml"):
        names.add(f.stem)
    missing = [n for n in REQUIRED_CI_WORKFLOWS if n not in names]
    _record(
        "case_2_every_required_workflow_exists", not missing,
        f"`.github/workflows/` 에 없는 이름: {missing} — 이름이 바뀌면 그 축은 "
        "조용히 'missing' 이 되어 발행이 영구 차단되거나(그나마 낫다) 오해를 부른다",
    )


def case_3_all_success_passes() -> None:
    r = verify_required_ci(head_sha="deadbeef", runs=_all_green())
    _record("case_3_all_success_passes", r["ok"] is True, f"{r['workflows']} / {r['error']}")


def case_4_one_failure_blocks() -> None:
    runs = [_run(n) for n in REQUIRED_CI_WORKFLOWS if n != "smoke"]
    runs.append(_run("smoke", conclusion="failure"))
    r = verify_required_ci(head_sha="deadbeef", runs=runs)
    ok = r["ok"] is False and "smoke" in r["blocking"]
    _record("case_4_one_failure_blocks", ok, f"{r['workflows']} / blocking={r['blocking']}")


def case_5_missing_run_blocks() -> None:
    """이 sha 에 run 이 없으면 막는다 — v1.8.0 을 통과시킨 것이 정확히 이 자리다."""
    runs = [_run(n) for n in REQUIRED_CI_WORKFLOWS if n != "smoke"]
    r = verify_required_ci(head_sha="deadbeef", runs=runs)
    ok = r["ok"] is False and r["workflows"].get("smoke") == "missing"
    _record("case_5_missing_run_blocks", ok, f"{r['workflows']} / blocking={r['blocking']}")


def case_6_pending_run_blocks() -> None:
    runs = [_run(n) for n in REQUIRED_CI_WORKFLOWS if n != "smoke"]
    runs.append(_run("smoke", status="in_progress", conclusion=""))
    r = verify_required_ci(head_sha="deadbeef", runs=runs)
    ok = r["ok"] is False and r["workflows"].get("smoke") == "pending"
    _record("case_6_pending_run_blocks", ok, f"{r['workflows']} / blocking={r['blocking']}")


def case_7_fetch_error_blocks() -> None:
    r = verify_required_ci(head_sha="deadbeef", fetch_error="gh CLI not found")
    ok = r["ok"] is False and r["blocking"] == list(REQUIRED_CI_WORKFLOWS)
    _record("case_7_fetch_error_blocks", ok,
            f"못 읽은 것을 통과로 세면 안 된다 (모름 ≠ 안전): {r}")


def case_8_query_targets_head_sha() -> None:
    """질의가 sha 를 직접 지정하는가 — '최신 run 집기' 로 되돌아가지 않았는가."""
    src = PIPELINE_SRC.read_text(encoding="utf-8")
    fetch = src.split("def _fetch_ci_runs_for_sha", 1)
    problems = []
    if len(fetch) != 2:
        problems.append("_fetch_ci_runs_for_sha 가 없다")
    else:
        body = fetch[1].split("\ndef ", 1)[0]
        if '"--commit"' not in body:
            problems.append("`--commit` 으로 sha 를 지정하지 않는다")
    if "def verify_required_ci" not in src:
        problems.append("verify_required_ci 가 없다")
    # 게이트가 cmd_release 에서 **차단**으로 쓰이는가
    rel = src.split("def cmd_release", 1)
    if len(rel) != 2:
        problems.append("cmd_release 가 없다")
    else:
        body = rel[1]
        if "verify_required_ci()" not in body:
            problems.append("cmd_release 가 verify_required_ci 를 부르지 않는다")
        if 'required_ci["ok"]' not in body or "not args.dry_run" not in body:
            problems.append("apply 경로에서 차단하지 않는다 — advisory 로 되돌아갔다")
    _record("case_8_query_targets_head_sha", not problems, "; ".join(problems))


def main() -> int:
    print("=== 발행 게이트 ↔ 필수 CI 워크플로 ===")
    for fn in (
        case_1_required_list_declared,
        case_2_every_required_workflow_exists,
        case_3_all_success_passes,
        case_4_one_failure_blocks,
        case_5_missing_run_blocks,
        case_6_pending_run_blocks,
        case_7_fetch_error_blocks,
        case_8_query_targets_head_sha,
    ):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            FAILURES.append(fn.__name__)
            print(f"  FAIL  {fn.__name__} — 예외 {type(exc).__name__}: {exc}")
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    print("\n8/8 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
