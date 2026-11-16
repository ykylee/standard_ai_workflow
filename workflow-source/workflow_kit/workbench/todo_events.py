"""소유자가 워크벤치에서 바꾼 todo 의 기록 — 작업 세션 hook 이 다음 차례에 문장으로 받는다 (TASK-2026-11-16-main-017).

- 서버는 todo 를 바꾼 뒤 checkout 루트의 ``.workbench/todo-events.jsonl`` 에 한 줄(누가 · 무엇을 · 어느 항목)을 더하고
  응답과 같은 도착 신호(:func:`inbox_signal.touch_stamp`)를 남긴다.
- hook(``plan-import --hook``)은 :func:`drain` 으로 쌓인 줄을 **읽고 비운다** — 같은 락 아래라 그 사이에 더해진 줄은
  잃지 않고, 이미 알린 변경은 다시 싣지 않는다. 파일은 비워지므로 자라지 않는다.
- 작업 세션 자신의 ``todo`` CLI 변경은 기록하지 않는다 — 알릴 대상은 소유자의 변경이다.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from workflow_kit.common import file_lock, todo_list
from workflow_kit.workbench import inbox_signal

EVENTS = "todo-events.jsonl"
LOCK = "todo-events.lock"
LOCK_TIMEOUT_S = 5.0
#: 한 번에 hook 에 싣는 줄의 상한 — 넘으면 "외 N건" 으로 접는다.
MAX_LINES = 20
ACTIONS = {"add": "추가", "done": "끝냄", "undo": "되돌림", "edit": "고침", "remove": "삭제"}


@contextmanager
def _locked(workspace: Path) -> Iterator[Path]:
    directory = inbox_signal._ensure_dir(workspace)
    lock_path = directory / LOCK
    file_lock.prepare_lock_file(lock_path)
    with open(lock_path, "r+b") as handle:
        if not file_lock.lock_exclusive_blocking(handle, timeout=LOCK_TIMEOUT_S):
            raise TimeoutError("todo 기록 락을 잡지 못했다")
        try:
            yield directory / EVENTS
        finally:
            file_lock.unlock(handle)


def record(workspace: Path, *, actor: str, action: str, item: todo_list.Item) -> None:
    entry = {"at": time.strftime("%Y-%m-%d %H:%M"), "actor": actor, "action": action, **todo_list.as_json(item)}
    with _locked(workspace) as path:
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def drain(workspace: Path) -> list[dict[str, Any]]:
    """쌓인 기록을 읽고 비운다. 기록이 없거나 디렉터리가 없으면 빈 목록 — 디렉터리를 새로 만들지 않는다."""
    if not (inbox_signal.signal_dir(workspace) / EVENTS).is_file():
        return []
    with _locked(workspace) as path:
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        path.write_text("", encoding="utf-8")
    events: list[dict[str, Any]] = []
    for line in text.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            events.append({"broken": line[:120]})
            continue
        if isinstance(value, dict):
            events.append(value)
    return events


def hook_lines(events: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for event in events[:MAX_LINES]:
        if "broken" in event:
            lines.append(f"- (읽지 못한 기록 줄: {event['broken']})")
            continue
        scope = event.get("scope", "?")
        where = "브랜치 할 일" if scope == todo_list.BRANCH_SCOPE else f"{scope} 체크리스트"
        lines.append(f"- {event.get('at', '?')} {event.get('actor', '?')} · {ACTIONS.get(event.get('action', ''), event.get('action'))}"
                     f" · {where}: {event.get('text', '')} ({event.get('id', '?')})")
    if len(events) > MAX_LINES:
        lines.append(f"- 외 {len(events) - MAX_LINES}건 — `python -m workflow_kit todo` 로 현재 목록을 본다")
    return lines
