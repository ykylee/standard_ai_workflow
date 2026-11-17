"""진행 기록 상기 — 작업 중인 task 의 Progress 가 오래 그대로면 작업 세션 hook 이 한 번 알린다.

TASK-2026-11-17-claude-remote-sync-check-234c32-003 (소유자 지시 2026-11-17: "작업 중에 지속적으로 워크벤치를
업데이트하도록 지침이 들어가야 한다" · 결정 D1=hook, D2=15분). 워크벤치의 '지금 하는 일' 은 task 파일의
``Progress`` 한 줄이고, 그 줄은 작업하는 에이전트가 단계마다 ``backlog-update --progress-note`` 로 바꾼다
(TASK-2026-11-16-main-009). 규칙만으로는 잊힌다 — 이 명령이 하네스 hook 에서 그것을 상기시킨다.

판정 (``core/plan_workbench_spec.md`` §4.6):

- 대상은 현재 브랜치의 ``in_progress`` task 중 Progress 시각이 **최근 ACTIVE_WINDOW 안** 인 것 — '작업 중' 인 task.
  모 브랜치에서 물려받아 오래 손대지 않은 in_progress task 는 대상이 아니다 (매번 상기하면 잡음이다).
- 대상 중 가장 새 Progress 가 STALE_AFTER 넘게 그대로면 hook JSON(additionalContext) 한 덩어리를 낸다.
  아니면 아무것도 출력하지 않는다.
- 부를 때마다 ``.workbench/progress.checked`` 를 새로 쓴다 — hook 셸이 그 mtime 으로 STALE_AFTER 안의 재호출을
  Python 없이 거른다. 그래서 상기는 낡은 동안 STALE_AFTER 마다 많아야 한 번이다.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from workflow_kit.common import plan_tasks
from workflow_kit.common.paths import discover_project_profile_path, project_workspace_root, workflow_branch_dir
from workflow_kit.common.stdio import force_utf8_stdio
from workflow_kit.workbench import inbox_signal, state_view

#: 진행 기록이 이만큼 그대로면 상기한다 (결정 D2 = 15분).
STALE_AFTER = dt.timedelta(minutes=15)
#: Progress 가 이 안에 있어야 '작업 중' task 로 본다 — 물려받은 낡은 in_progress 를 거른다.
ACTIVE_WINDOW = dt.timedelta(hours=12)
CHECKED = "progress.checked"
#: kit 하위 명령 이름 — ``common/tool_dispatch.py`` 의 키와 같다 (hook 셸이 이것으로 부른다).
COMMAND = "progress-nudge"
STAMP_FORMAT = "%Y-%m-%d %H:%M"  # backlog-update --progress-note 가 붙이는 시각 (로컬 시각)


def active_tasks(tasks_dir: Path, now: dt.datetime) -> list[tuple[str, dt.datetime]]:
    """(task id, Progress 시각) — in_progress 이고 Progress 시각이 ACTIVE_WINDOW 안인 것, 새 것부터."""
    found: list[tuple[str, dt.datetime]] = []
    # iter_task_plans 는 주장 · 결정이 있는 task 만 준다 — 계획 없는 task 도 진행 기록은 남긴다, 전부 읽는다.
    paths = sorted(tasks_dir.glob("TASK-*.md")) if tasks_dir.is_dir() else []
    for task in filter(None, (plan_tasks.read_task_plan(path) for path in paths)):
        if task.status != "in_progress":
            continue
        progress = state_view.task_progress(list(task.lines))
        if not progress or not progress.get("at"):
            continue
        try:
            at = dt.datetime.strptime(progress["at"], STAMP_FORMAT)
        except ValueError:
            continue
        if now - at <= ACTIVE_WINDOW:
            found.append((task.task_id, at))
    found.sort(key=lambda item: item[1], reverse=True)
    return found


def nudge_message(active: list[tuple[str, dt.datetime]], now: dt.datetime) -> str | None:
    if not active:
        return None
    newest = active[0][1]
    if now - newest < STALE_AFTER:
        return None
    minutes = int((now - newest).total_seconds() // 60)
    ids = ", ".join(task_id for task_id, _ in active[:3])
    return (f"[진행 기록] 작업 중인 task 의 진행 기록이 {minutes}분째 그대로다 ({ids}). 지금 단계(계획 → 구현 → 검사 → "
            "verifier → 커밋 · push)를 남겨라 — `python -m workflow_kit backlog-update --mode update --task-id <ID> "
            "--task-name \"<제목>\" --progress-note \"<지금 하는 일>\"`. 워크벤치의 '지금 하는 일' 이 이 줄이다. "
            "끝난 task 면 닫고, 멈춘 task 면 blocked 로 바꾼다.")


def run_hook(profile: Path, event: str, *, now: dt.datetime | None = None) -> int:
    current = now or dt.datetime.now()
    workspace = project_workspace_root(profile)
    message = nudge_message(active_tasks(workflow_branch_dir(profile) / "backlog" / "tasks", current), current)
    try:
        (inbox_signal._ensure_dir(workspace) / CHECKED).write_text(current.strftime(STAMP_FORMAT) + "\n",
                                                                   encoding="utf-8")
    except OSError:
        pass  # 표식을 못 쓰면 다음 hook 이 다시 부를 뿐이다
    if message:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": message}},
                         ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="progress-nudge",
        description="작업 중인 task 의 진행 기록(Progress)이 15분 넘게 그대로면 hook JSON 으로 상기한다 (작업 세션 hook 용).")
    parser.add_argument("--hook", required=True, metavar="EVENT", help="hook 이벤트 이름 (예: PostToolUse) — 출력 JSON 에 실린다")
    parser.add_argument("--project-profile-path", default=None, help="미지정 시 cwd 상위에서 자동 탐색")
    return parser


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    args = build_parser().parse_args(argv)
    found = Path(args.project_profile_path).resolve() if args.project_profile_path else discover_project_profile_path()
    if found is None or not Path(found).is_file():
        return 0  # 프로필 없는 디렉터리의 hook — 조용히 지나간다
    return run_hook(Path(found).resolve(), args.hook)


if __name__ == "__main__":
    sys.exit(main())
