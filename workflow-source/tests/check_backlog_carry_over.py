#!/usr/bin/env python3
"""날짜가 바뀌어도 진행 중인 task 의 갱신이 사라지지 않는다 (TASK-2026-08-16-main-001).

daily index 는 *그날 손댄 task* 의 목록이고, SSOT 는 `backlog/tasks/<id>.md` 다.
그런데 update 경로가 "오늘 index 에 없으면 `cannot_determine`" 으로 끝나 버려서,
**날짜가 바뀐 순간부터 진행 중 task 의 갱신이 통째로 무시**됐다. 그러고도 최상위
`status` 는 `ok` 였다 — 호출자는 갱신됐다고 읽는다.

2회 연속 세션에서 밟았다. 두 번째에는 조용히 끝나지도 않았다: linter 가
`task_status_mismatch` 를 냈고 `check_self_application` 이 red 가 되어 **커밋
게이트를 세웠다**. 그 결함을 task 파일에 기록하려던 호출 자신도 같은 이유로
스킵됐다.

여기서 고정하는 것은 둘이다:

1. task SSOT 가 있으면 그것은 미지의 ID 가 아니라 **이월**이다 — 오늘 index 에
   항목을 만들고 갱신을 반영한다 (본문·상태는 보존).
2. 정말로 대상이 없으면 `cannot_determine` 이되, **최상위 `status` 를 `ok` 로
   두지 않는다.** 아무것도 안 썼으면 그렇게 말해야 한다.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
SCRIPT_PATH = SOURCE_ROOT / "skills" / "backlog-update" / "scripts" / "run_backlog_update.py"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.paths import get_current_branch  # noqa: E402

FAILURES: list[str] = []

TASK_ID = "TASK-2026-08-16-carry-001"

#: 이월돼도 살아 있어야 하는 본문. 이월이 "새로 만들기" 로 구현되면 이게 사라진다.
SSOT_BODY = f"""---
id: {TASK_ID}
status: in_progress
created_at: 2026-08-16
source_anchor: generic-task-2026-08-16-carry-001
source_path: backlog/2026-08-16.md
kind: generic
---

# {TASK_ID} — 이월 대상 task

## 📝 Description

- 상태: in_progress
- 우선순위: high
- 요청일: 2026-08-16
- 담당:
- 호스트명:
- 호스트 IP:
- 영향 문서:
  -

- 작업 내용: 어제 등록된 진행 중 작업.
- 완료 기준:
  - PRESERVED-CRITERION-A
  - PRESERVED-CRITERION-B

## 🛠️ Implementation / Content

- 진행 현황: 어제까지의 기록.
- 다음 세션 시작 포인트:
- 남은 리스크:

## ✅ Outcome

- 작업 결과:
- 후속 작업:
"""

YESTERDAY_INDEX = f"""# Backlog Index — 2026-08-16

- 문서 목적: 해당 날짜의 작업 항목(task) SSOT link 모음.
- 범위: 해당 일자(task 단위)의 모든 task.
- 대상 독자: AI agent (session-start / backlog-update), maintainer.
- 상태: stable (v0.14.0 append-only layout).
- 최종 수정일: 2026-08-16
- 관련 문서: [./tasks/](./tasks/) (per-task SSOT)

## Tasks

- **{TASK_ID}** [generic] 이월 대상 task
  - path: [`./tasks/{TASK_ID}.md`](./tasks/{TASK_ID}.md)
  - status: in_progress
"""

TODAY_INDEX = """# Backlog Index — 2026-08-17

- 문서 목적: 해당 날짜의 작업 항목(task) SSOT link 모음.
- 범위: 해당 일자(task 단위)의 모든 task.
- 대상 독자: AI agent (session-start / backlog-update), maintainer.
- 상태: stable (v0.14.0 append-only layout).
- 최종 수정일: 2026-08-17
- 관련 문서: [./tasks/](./tasks/) (per-task SSOT)

## Tasks

- **TASK-2026-08-17-other-001** [generic] 오늘 이미 등록된 다른 task
  - path: [`./tasks/TASK-2026-08-17-other-001.md`](./tasks/TASK-2026-08-17-other-001.md)
  - status: planned
"""


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case}{(' — ' + detail) if detail else ''}")
        FAILURES.append(case)


def _run(args: list[str]) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"backlog-update 실패 rc={completed.returncode}: {completed.stderr[-400:]}")
    return json.loads(completed.stdout)


class Fixture:
    """어제 index 에만 있는 진행 중 task + 오늘 index (다른 task 로 이미 존재)."""

    def __init__(self, tmp: Path, *, with_ssot: bool = True) -> None:
        example_root = SOURCE_ROOT / "examples" / "acme_delivery_platform"
        self.project_root = (tmp / "project").resolve()
        branch_root = (self.project_root / get_current_branch()).resolve()
        branch_root.mkdir(parents=True)
        for rel in ("PROJECT_PROFILE.md", "work_backlog.md"):
            (self.project_root / rel).write_text(
                (example_root / rel).read_text(encoding="utf-8"), encoding="utf-8"
            )
        (branch_root / "session_handoff.md").write_text(
            (example_root / "session_handoff.md").read_text(encoding="utf-8"), encoding="utf-8"
        )
        backlog_dir = branch_root / "backlog"
        (backlog_dir / "tasks").mkdir(parents=True)
        (backlog_dir / "2026-08-16.md").write_text(YESTERDAY_INDEX, encoding="utf-8")
        self.today = backlog_dir / "2026-08-17.md"
        self.today.write_text(TODAY_INDEX, encoding="utf-8")
        self.ssot = backlog_dir / "tasks" / f"{TASK_ID}.md"
        if with_ssot:
            self.ssot.write_text(SSOT_BODY, encoding="utf-8")

    @property
    def base_args(self) -> list[str]:
        return [
            "--project-profile-path", str(self.project_root / "PROJECT_PROFILE.md"),
            "--daily-backlog-path", str(self.today),
        ]


# --- Case 1 ----------------------------------------------------------------


def test_carry_over_into_new_daily_index() -> None:
    """어제 index 에만 있는 task 를 오늘 갱신하면 오늘 index 로 이월된다."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fx = Fixture(Path(tmpdir))
        payload = _run([
            *fx.base_args,
            "--task-id", TASK_ID,
            "--mode", "update",
            "--task-name", "이월 대상 task",
            "--task-brief", "날짜가 바뀐 뒤의 갱신.",
            "--apply",
        ])
        today_text = fx.today.read_text(encoding="utf-8")
        ssot_text = fx.ssot.read_text(encoding="utf-8")

    problems: list[str] = []
    if payload["operation_type"] != "carry_over_entry":
        problems.append(f"operation_type={payload['operation_type']!r} (carry_over_entry 기대)")
    if payload["apply_status"] != "applied":
        problems.append(f"apply_status={payload['apply_status']!r} — 이월인데 아무것도 안 썼다")
    if f"- **{TASK_ID}**" not in today_text:
        problems.append("오늘 index 에 이월 항목이 없다")
    if "TASK-2026-08-17-other-001" not in today_text:
        problems.append("오늘 index 의 기존 항목이 사라졌다 (append-only 위반)")
    _record("test_carry_over_into_new_daily_index", not problems, "; ".join(problems))

    # 이월이 "새로 만들기" 로 구현되면 본문이 날아간다 — 별 case 로 분리해 지목한다.
    lost = [
        marker
        for marker in ("PRESERVED-CRITERION-A", "PRESERVED-CRITERION-B", "# " + TASK_ID)
        if marker not in ssot_text
    ]
    _record(
        "test_carry_over_preserves_task_body",
        not lost,
        f"이월이 SSOT 본문을 잃었다: {lost}",
    )


# --- Case 3 ----------------------------------------------------------------


def test_carry_over_preserves_status_when_unspecified() -> None:
    """`--status` 미지정은 '바꾸지 말라' 다 — 이월에서도 같다."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fx = Fixture(Path(tmpdir))
        _run([
            *fx.base_args,
            "--task-id", TASK_ID,
            "--mode", "update",
            "--task-name", "이월 대상 task",
            "--task-brief", "상태 미지정 이월.",
            "--apply",
        ])
        today_text = fx.today.read_text(encoding="utf-8")
    block = today_text.split(f"- **{TASK_ID}**", 1)[-1]
    _record(
        "test_carry_over_preserves_status_when_unspecified",
        "- status: in_progress" in block,
        f"이월 항목의 status 가 보존되지 않았다: {block.strip()[:120]!r}",
    )


# --- Case 4 ----------------------------------------------------------------


def test_missing_ssot_is_not_ok() -> None:
    """SSOT 도 없으면 `cannot_determine` 이고, 최상위 status 가 `ok` 여선 안 된다."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fx = Fixture(Path(tmpdir), with_ssot=False)
        payload = _run([
            *fx.base_args,
            "--task-id", TASK_ID,
            "--mode", "update",
            "--task-name", "존재하지 않는 대상",
            "--task-brief", "갱신할 대상이 없다.",
            "--apply",
        ])
        today_text = fx.today.read_text(encoding="utf-8")

    problems: list[str] = []
    if payload["operation_type"] != "cannot_determine":
        problems.append(f"operation_type={payload['operation_type']!r} (cannot_determine 기대)")
    if payload["status"] == "ok":
        problems.append("아무것도 안 썼는데 최상위 status 가 ok 다 — 조용한 미반영 회귀")
    if payload["apply_status"] != "skipped":
        problems.append(f"apply_status={payload['apply_status']!r} — 대상이 없는데 썼다")
    if TASK_ID in today_text:
        problems.append("대상이 없는데 오늘 index 에 항목을 만들었다")
    _record("test_missing_ssot_is_not_ok", not problems, "; ".join(problems))


# --- Case 5 ----------------------------------------------------------------


def test_same_day_update_still_update_entry() -> None:
    """반대 방향으로 넓히지 않았는가 — 오늘 index 에 있는 task 는 그냥 update 다.

    이월 분기가 정상 경로까지 삼키면 `operation_type` 이 갈리고, 그걸 보고
    판단하는 호출자가 조용히 어긋난다.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        fx = Fixture(Path(tmpdir))
        # 먼저 이월시켜 오늘 index 에 올린 뒤, 같은 날 두 번째 갱신을 본다.
        _run([
            *fx.base_args, "--task-id", TASK_ID, "--mode", "update",
            "--task-name", "이월 대상 task", "--task-brief", "1회차.", "--apply",
        ])
        payload = _run([
            *fx.base_args, "--task-id", TASK_ID, "--mode", "update",
            "--task-name", "이월 대상 task", "--task-brief", "2회차.", "--apply",
        ])
    _record(
        "test_same_day_update_still_update_entry",
        payload["operation_type"] == "update_entry" and payload["apply_status"] == "applied",
        f"operation_type={payload['operation_type']!r} apply_status={payload['apply_status']!r}",
    )


def main() -> int:
    test_carry_over_into_new_daily_index()
    test_carry_over_preserves_status_when_unspecified()
    test_missing_ssot_is_not_ok()
    test_same_day_update_still_update_entry()
    total = 5
    print(f"\n{total - len(FAILURES)}/{total} passed")
    if FAILURES:
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
