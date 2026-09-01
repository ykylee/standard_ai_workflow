#!/usr/bin/env python3
"""`done` 강등이 **이미 기록된 완료를 취소**하지 않는지 고정한다 (8 cases).

## 계보 (TASK-2026-09-01-main-003)

`determine_conservative_task_status` 의 docstring 은 원래부터 이렇게 **선언**하고 있었다:

    done 강등 규칙은 명시 요청에만 적용한다 … 기존 done 의 보존은 강등하지 않는다 —
    그 done 은 이미 검증과 함께 기록된 상태다.

그런데 코드는 그 원칙을 `--status` 를 **생략했을 때만** 지켰다. `--status done` 을
명시하면 파일에 이미 기록된 검증 결과를 **보지 않고** 무조건 낮췄다. 선언과 구현이
갈라진 자리였고, 갈라진 쪽이 기록을 지웠다.

2026-09-01(72차) 실측: 이미 close 한 task 에 진행 메모만 덧붙이려고
`--status done --progress-note` 로 재호출했는데 `--validation-result` 를 안 실어서,
도구가 done → in_progress 로 낮추고 **handoff §4(최근 완료)의 항목을 §2(진행 중)로
되돌렸다.** 최상위 `status` 는 `ok` 였고 근거는 warnings 한 줄뿐이라 그대로 커밋·push
됐다 (`12b9f311`).

## 이 검사가 지키는 두 갈래

성격이 다른 두 경우라 판정도 둘이다:

- **기록이 있으면 보존** — 검증은 이미 파일에 있고, 그 호출은 *새로운* 미검증 done 을
  주장하는 것이 아니다. 막을 것이 없다.
- **어디에도 없으면 강등 유지** — 규칙 자체는 옳다. 다만 그것이 *이미 기록된* done 을
  취소하는 경우라면 `DEMOTION_REVERTS_DONE` 표식이 붙고, 호출자는 최상위 status 를
  `ok` 가 아니게 만든다. 조용한 취소를 금지하는 것이지 강등을 없애는 게 아니다.

8 cases:
  1) 기록된 검증이 있으면 `--status done` 을 보존한다
  2) 그때 경고는 남긴다 (조용히 통과시키지 않는다)
  3) 기록도 인자도 없고 **이미 done** 이면 → 강등 + `DEMOTION_REVERTS_DONE` 표식
  4) 기록도 인자도 없고 done 이 **아니었으면** → 강등하되 표식은 없다 (취소한 게 없다)
  5) 인자로 검증을 주면 그대로 done
  6) `--status` 미지정이면 기존 상태 보존 (v1.1.8 규약 회귀 방지)
  7) `read_task_ssot_state` 가 status 와 기록된 검증을 함께 읽는다 (별칭 포함)
  8) 호출자가 그 표식을 최상위 `status` 로 올린다 (소스 계약)
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.planning import (  # noqa: E402
    DEMOTION_REVERTS_DONE,
    determine_conservative_task_status,
)
from workflow_kit.common.project_docs import task_label  # noqa: E402
from workflow_kit.tools.backlog_update import read_task_ssot_state  # noqa: E402

BACKLOG_SRC = SOURCE_ROOT / "workflow_kit" / "tools" / "backlog_update.py"

FAILURES: list[str] = []


def _record(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  PASS  {name}")
        return
    FAILURES.append(name)
    print(f"  FAIL  {name} — {detail}")


def _decide(**kw):
    base = dict(requested_status="done", validation_result=None,
                operation_type="update_entry", current_status="done")
    base.update(kw)
    recorded = base.pop("recorded_validation", None)
    return determine_conservative_task_status(
        base["requested_status"], base["validation_result"],
        base["operation_type"], current_status=base["current_status"],
        recorded_validation=recorded,
    )


def case_1_recorded_validation_preserves_done() -> None:
    status, _ = _decide(recorded_validation="전량 2축 278/278 PASS")
    _record(
        "case_1_recorded_validation_preserves_done", status == "done",
        f"status={status!r} — 파일에 검증이 있는데 강등하면 이미 기록된 완료가 취소된다",
    )


def case_2_preservation_still_warns() -> None:
    _, warnings = _decide(recorded_validation="전량 2축 278/278 PASS")
    ok = bool(warnings) and any("이미 기록" in w for w in warnings)
    _record("case_2_preservation_still_warns", ok,
            f"보존도 조용하면 안 된다 (새 검증이 안 남았다는 사실은 알려야 한다): {warnings}")


def case_3_reverting_recorded_done_is_flagged() -> None:
    status, warnings = _decide(recorded_validation=None, current_status="done")
    ok = status == "in_progress" and any(DEMOTION_REVERTS_DONE in w for w in warnings)
    _record("case_3_reverting_recorded_done_is_flagged", ok,
            f"status={status!r} warnings={warnings} — 표식이 없으면 호출자가 "
            "최상위 status 를 올릴 근거를 잃는다")


def case_4_plain_demotion_is_not_flagged() -> None:
    """done 이 아니던 task 의 강등은 취소한 것이 없다 — 표식을 붙이면 늑대 소년이 된다."""
    status, warnings = _decide(recorded_validation=None, current_status="in_progress")
    ok = status == "in_progress" and not any(DEMOTION_REVERTS_DONE in w for w in warnings)
    _record("case_4_plain_demotion_is_not_flagged", ok,
            f"status={status!r} warnings={warnings}")


def case_5_explicit_validation_keeps_done() -> None:
    status, _ = _decide(validation_result="전량 PASS", current_status="in_progress")
    _record("case_5_explicit_validation_keeps_done", status == "done", f"status={status!r}")


def case_6_unspecified_status_preserves() -> None:
    """v1.1.8 규약: 미지정은 '바꾸지 말라' 다 (회귀 방지)."""
    status, _ = _decide(requested_status=None, current_status="done")
    _record("case_6_unspecified_status_preserves", status == "done", f"status={status!r}")


def case_7_ssot_reader_returns_both() -> None:
    label = task_label("validation")
    body = (
        "---\nid: TASK-X\nstatus: done\n---\n\n"
        "## 📝 Description\n\n- Status: done\n"
        f"- {label}: 전량 2축 278/278 PASS\n"
    )
    with tempfile.TemporaryDirectory(prefix="ssot-") as tmp:
        f = Path(tmp) / "TASK-X.md"
        f.write_text(body, encoding="utf-8")
        status, recorded = read_task_ssot_state(f)
        empty = Path(tmp) / "TASK-Y.md"
        empty.write_text("---\nstatus: planned\n---\n", encoding="utf-8")
        status2, recorded2 = read_task_ssot_state(empty)
    problems = []
    if status != "done":
        problems.append(f"status 오독: {status!r}")
    if recorded != "전량 2축 278/278 PASS":
        problems.append(f"기록된 검증 오독: {recorded!r}")
    if (status2, recorded2) != ("planned", None):
        problems.append(f"검증 없는 파일 오독: {(status2, recorded2)!r}")
    _record("case_7_ssot_reader_returns_both", not problems, "; ".join(problems))


def case_8_caller_raises_top_level_status() -> None:
    """표식이 최상위 `status` 로 올라가는가 — warnings 에만 남으면 놓친다."""
    src = BACKLOG_SRC.read_text(encoding="utf-8")
    problems = []
    if "read_task_ssot_state(" not in src:
        problems.append("호출자가 SSOT reader 를 안 쓴다")
    if "recorded_validation=recorded_validation" not in src:
        problems.append("기록된 검증을 판정에 안 넘긴다")
    if "demotion_reverted_done" not in src:
        problems.append("표식을 안 읽는다")
    if 'or demotion_reverted_done' not in src:
        problems.append("최상위 status 에 반영하지 않는다 — warnings 에만 남으면 조용한 취소로 되돌아간다")
    _record("case_8_caller_raises_top_level_status", not problems, "; ".join(problems))


def main() -> int:
    print("=== done 강등이 기록된 완료를 취소하지 않는가 ===")
    for fn in (
        case_1_recorded_validation_preserves_done,
        case_2_preservation_still_warns,
        case_3_reverting_recorded_done_is_flagged,
        case_4_plain_demotion_is_not_flagged,
        case_5_explicit_validation_keeps_done,
        case_6_unspecified_status_preserves,
        case_7_ssot_reader_returns_both,
        case_8_caller_raises_top_level_status,
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
