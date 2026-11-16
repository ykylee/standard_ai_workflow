"""브랜치 할 일 · task 체크리스트 — ``<branch_dir>/todo.md`` 하나 (TASK-2026-11-16-main-016).

todo 는 task 파일에 살지 않는다. task 파일의 작성자는 작업 세션 하나이고(ADR-032 결정 15) 워크벤치는 그 파일을
쓰지 않는다 — 그래서 소유자가 브라우저에서 바로 고칠 수 있는 todo 는 따로 둔 파일 하나에 산다. 이 모듈이 그
파일의 **유일한** 읽기 · 쓰기 창구다: ``todo`` CLI(작업 세션)와 워크벤치(소유자)가 같은 함수를 부른다.

형식::

    # Todo

    ## Branch
    - [ ] 아직 task 로 만들지 않은 할 일 <!-- id:3fa9c1 -->

    ## TASK-2026-11-16-main-016
    - [x] 모듈 · 형식 <!-- id:0b7e22 -->

- 절 이름은 ``Branch`` 이거나 task ID 다. 항목 줄은 ``- [ ]`` / ``- [x]`` 로 시작한다.
- id 는 쓸 때 붙는다. 손으로 쓴 줄에 id 가 없으면 읽을 때 (절 · 글 · 같은 글의 몇 번째) 에서 **결정적으로** 만든
  id 를 준다 — 같은 파일을 두 번 읽어도 같은 id 라, 목록을 본 뒤 그 id 로 고칠 수 있다.
- 항목도 절 머리도 아닌 줄은 **버리지 않는다** — 그 자리에 그대로 다시 쓴다 (조용히 사라지는 내용이 없게).
- 쓰기는 ``.todo/lock`` 배타 락 아래에서 *읽기 → 적용 → 원자 교체* 다. 두 프로세스가 동시에 써도 서로의 항목을
  덮어 지우지 않는다. 락은 기다리되 상한(:data:`LOCK_TIMEOUT_S`)이 있다 — 넘으면 :class:`TodoError` ``busy``.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import unicodedata
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path

from workflow_kit.common import file_lock
from workflow_kit.common.atomic_write import atomic_write_text
from workflow_kit.common.project_docs import TASK_ID_PATTERN

FILENAME = "todo.md"
LOCK_DIRNAME = ".todo"
LOCK_FILENAME = "lock"
GITIGNORE_BODY = b"*\n"
BRANCH_SCOPE = "Branch"
TITLE = "# Todo"
MAX_TEXT = 300
LOCK_TIMEOUT_S = 5.0

_TASK_ID_RE = re.compile(rf"^{TASK_ID_PATTERN}$")
_SECTION_RE = re.compile(r"^##\s+(\S+)(.*)$")
_ITEM_RE = re.compile(r"^- \[([ xX])\] (.*?)(?:\s*<!-- id:([0-9a-z]{4,16}) -->)?\s*$")
_ID_RE = re.compile(r"^[0-9a-z]{4,16}$")


class TodoError(ValueError):
    """거절 — ``code`` 는 ``invalid`` (입력이 틀렸다) · ``not_found`` (그런 id · task 가 없다) · ``busy`` (락)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Item:
    id: str
    scope: str
    text: str
    done: bool


@dataclass
class TodoList:
    """절 이름 → 그 절의 줄들 (``Item`` 이거나 그대로 다시 쓸 문자열). ``preamble`` 은 첫 절 앞의 낯선 줄."""

    sections: dict[str, list[Item | str]] = field(default_factory=dict)
    preamble: list[str] = field(default_factory=list)
    #: 절 머리에 범위 뒤로 붙은 글 (``## TASK-… — 제목`` 의 ``— 제목``) — 다시 쓸 때 그대로 둔다.
    titles: dict[str, str] = field(default_factory=dict)
    #: 범위가 아닌 ``## `` 머리 아래 묶음 (머리 줄, 줄들) — 항목으로 세지 않고 맨 끝에 그대로 다시 쓴다.
    others: list[tuple[str, list[str]]] = field(default_factory=list)

    def items(self, scope: str | None = None) -> list[Item]:
        return [entry for name, entries in self.sections.items() if scope is None or name == scope
                for entry in entries if isinstance(entry, Item)]

    def find(self, item_id: str) -> Item | None:
        return next((item for item in self.items() if item.id == item_id), None)

    def counts(self) -> dict[str, tuple[int, int]]:
        """절마다 (끝낸 수, 전체 수) — 항목이 없는 절은 싣지 않는다."""
        result: dict[str, tuple[int, int]] = {}
        for scope in self.sections:
            items = self.items(scope)
            if items:
                result[scope] = (sum(1 for item in items if item.done), len(items))
        return result


# --------------------------------------------------------------------------- 경로 · 검증


def todo_path(branch_dir: Path) -> Path:
    return branch_dir / FILENAME


def has_task(branch_dir: Path, task_id: str) -> bool:
    return (branch_dir / "backlog" / "tasks" / f"{task_id}.md").is_file()


def is_scope(scope: str) -> bool:
    return scope == BRANCH_SCOPE or bool(_TASK_ID_RE.match(scope))


def check_text(text: str) -> str:
    """항목 글을 다듬어 돌려준다 — 한 줄 · 비지 않음 · 상한 · 제어 문자 없음 · 주석 표식 없음."""
    cleaned = text.strip()
    if not cleaned:
        raise TodoError("invalid", "할 일 글이 비었다")
    if len(cleaned) > MAX_TEXT:
        raise TodoError("invalid", f"할 일 글이 {MAX_TEXT}자를 넘는다 ({len(cleaned)}자)")
    # Cc(C0 · DEL · C1 — U+0085 포함) 와 줄 · 문단 구분자(U+2028 · U+2029): 줄 경계로 읽히면 항목이 쪼개진다.
    if any(unicodedata.category(ch) in ("Cc", "Zl", "Zp") for ch in cleaned):
        raise TodoError("invalid", "할 일 글에 제어 문자 · 줄 구분자(줄바꿈 포함)가 있다")
    # 양방향 덮어쓰기 · 격리 제어(U+202A~202E · U+2066~2069)는 화면에서 글을 뒤집어 보이게 한다. 다른 Cf(ZWJ 등)는 받는다.
    if any(0x202A <= ord(ch) <= 0x202E or 0x2066 <= ord(ch) <= 0x2069 for ch in cleaned):
        raise TodoError("invalid", "할 일 글에 양방향 제어 문자(U+202A~202E · U+2066~2069)가 있다")
    if "<!--" in cleaned or "-->" in cleaned:
        raise TodoError("invalid", "할 일 글에 HTML 주석 표식(<!-- · -->)을 쓸 수 없다 — id 표식과 섞인다")
    return cleaned


def _check_scope(branch_dir: Path, scope: str) -> None:
    if scope == BRANCH_SCOPE:
        return
    if not _TASK_ID_RE.match(scope):
        raise TodoError("invalid", f"범위는 {BRANCH_SCOPE} 이거나 task ID 다: {scope[:60]}")
    if not has_task(branch_dir, scope):
        raise TodoError("not_found", f"이 브랜치에 task 가 없다: {scope}")


# --------------------------------------------------------------------------- 읽기 · 렌더


def _derived_id(scope: str, text: str, occurrence: int) -> str:
    digest = hashlib.sha256(f"{scope}\0{text}\0{occurrence}".encode()).hexdigest()
    return "h" + digest[:7]


def parse(text: str) -> TodoList:
    result = TodoList()
    current: list[Item | str] | None = None
    scope = ""
    seen: dict[tuple[str, str], int] = {}
    used: set[str] = set()
    other: list[str] | None = None
    # splitlines() 가 아니다 — U+0085 · U+2028 같은 글자를 줄 경계로 보지 않는다 (줄은 \n 하나로만 끊긴다).
    for raw in text.split("\n"):
        line = raw.rstrip()
        if current is None and other is None and line.strip() == TITLE:
            continue
        section = _SECTION_RE.match(line)
        if section and is_scope(section.group(1)):
            scope = section.group(1)
            current = result.sections.setdefault(scope, [])
            other = None
            if section.group(2).strip():
                result.titles[scope] = section.group(2).rstrip()
            continue
        if section:
            other = []
            current = None
            result.others.append((line, other))
            continue
        if other is not None:
            other.append(line)
            continue
        item = _ITEM_RE.match(line) if current is not None else None
        if item and current is not None:
            body = item.group(2).strip()
            key = (scope, body)
            seen[key] = seen.get(key, 0) + 1
            item_id = item.group(3)
            if item_id is None or item_id in used:
                item_id = _derived_id(scope, body, seen[key])
            used.add(item_id)
            current.append(Item(item_id, scope, body, item.group(1) != " "))
            continue
        if current is None:
            if line.strip():
                result.preamble.append(line)
            continue
        current.append(line)
    # 절 끝의 빈 줄은 렌더가 다시 넣는다.
    for entries in result.sections.values():
        while entries and isinstance(entries[-1], str) and not entries[-1].strip():
            entries.pop()
    for _, lines in result.others:
        while lines and not lines[-1].strip():
            lines.pop()
    return result


def render(todo: TodoList) -> str:
    lines = [TITLE, ""]
    if todo.preamble:
        lines += [*todo.preamble, ""]
    order = [BRANCH_SCOPE, *sorted(s for s in todo.sections if s != BRANCH_SCOPE)]
    for scope in order:
        entries = todo.sections.get(scope, [])
        if scope != BRANCH_SCOPE and not entries:
            continue
        lines.append(f"## {scope}{todo.titles.get(scope, '')}")
        for entry in entries:
            if isinstance(entry, Item):
                lines.append(f"- [{'x' if entry.done else ' '}] {entry.text} <!-- id:{entry.id} -->")
            else:
                lines.append(entry)
        lines.append("")
    for heading, raw_lines in todo.others:
        lines += [heading, *raw_lines, ""]
    return "\n".join(lines).rstrip("\n") + "\n"


def read(branch_dir: Path) -> TodoList:
    path = todo_path(branch_dir)
    try:
        return parse(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return TodoList()


# --------------------------------------------------------------------------- 쓰기


@contextmanager
def _locked(branch_dir: Path) -> Iterator[None]:
    if not branch_dir.is_dir():  # 브랜치 메모리는 backlog-update 만 만든다 — todo 가 새 브랜치 디렉터리를 만들지 않는다
        raise TodoError("not_found", f"이 브랜치의 메모리 디렉터리가 없다 — 먼저 backlog-update 로 task 를 만든다: {branch_dir.name}")
    directory = branch_dir / LOCK_DIRNAME
    directory.mkdir(parents=True, exist_ok=True)
    ignore = directory / ".gitignore"
    if not ignore.is_file() or ignore.read_bytes() != GITIGNORE_BODY:
        ignore.write_bytes(GITIGNORE_BODY)
    lock_path = directory / LOCK_FILENAME
    file_lock.prepare_lock_file(lock_path)
    with open(lock_path, "r+b") as handle:
        if not file_lock.lock_exclusive_blocking(handle, timeout=LOCK_TIMEOUT_S):
            raise TodoError("busy", f"todo 락을 {LOCK_TIMEOUT_S:g}초 안에 잡지 못했다 — 잠시 뒤 다시 한다")
        try:
            yield
        finally:
            file_lock.unlock(handle)


def _new_id(todo: TodoList) -> str:
    used = {item.id for item in todo.items()}
    while True:
        candidate = secrets.token_hex(3)
        if candidate not in used:
            return candidate


def _mutate(branch_dir: Path, change: Callable[[TodoList], Item]) -> Item:
    with _locked(branch_dir):
        todo = read(branch_dir)
        item = change(todo)
        atomic_write_text(todo_path(branch_dir), render(todo))
        return item


def _replace(todo: TodoList, item_id: str, make: Callable[[Item], Item | None]) -> Item:
    if not _ID_RE.match(item_id):
        raise TodoError("invalid", f"id 형식이 아니다: {item_id[:40]}")
    for entries in todo.sections.values():
        for index, entry in enumerate(entries):
            if isinstance(entry, Item) and entry.id == item_id:
                updated = make(entry)
                if updated is None:
                    del entries[index]
                    return entry
                entries[index] = updated
                return updated
    raise TodoError("not_found", f"그런 할 일이 없다: {item_id}")


def add(branch_dir: Path, scope: str, text: str) -> Item:
    body = check_text(text)
    _check_scope(branch_dir, scope)

    def change(todo: TodoList) -> Item:
        item = Item(_new_id(todo), scope, body, False)
        todo.sections.setdefault(scope, []).append(item)
        return item

    return _mutate(branch_dir, change)


def set_done(branch_dir: Path, item_id: str, done: bool) -> Item:
    return _mutate(branch_dir, lambda todo: _replace(todo, item_id, lambda item: replace(item, done=done)))


def edit(branch_dir: Path, item_id: str, text: str) -> Item:
    body = check_text(text)
    return _mutate(branch_dir, lambda todo: _replace(todo, item_id, lambda item: replace(item, text=body)))


def remove(branch_dir: Path, item_id: str) -> Item:
    return _mutate(branch_dir, lambda todo: _replace(todo, item_id, lambda item: None))


def as_json(item: Item) -> dict[str, object]:
    return {"id": item.id, "scope": item.scope, "text": item.text, "done": item.done}
