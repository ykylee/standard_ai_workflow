"""모 브랜치 메모리 이어받기 — worktree 브랜치가 seed 때 모 브랜치의 내용을 **자기 네임스페이스에 옮겨 적는** 규칙.

## 왜 필요한가 (TASK-2026-10-02-main-001)

자동 seed(TASK-2026-09-30-claude-session-start-e6eb83-002)는 worktree 가 *시작은* 하게 했지만
빈 골격 handoff 에 "분기 시점 기준선은 `active/main/session_handoff.md`" 라는 산문 포인터만 남겼다.
2026-10-01 실측: `claude/probe-inherit` 의 session-start 는 "아직 작업 전" · `blocked=[]` (main 의
blocked task 미노출) · 계획 task 0 · §5 미노출 — 모 브랜치 맥락이 통째로 빠졌다.

## 규칙

- **모 브랜치에는 쓰지 않는다** (seed 시점). 기준선 · 주 작업 축 · §5 · 열린 task 를 새 네임스페이스로 옮겨 적는다.
- **원류를 남긴다.** handoff 에는 `원류: <branch>@<sha>` 줄, 옮겨 온 task 에는 frontmatter
  ``inherited_from: <branch>@<sha>`` · ``inherited_hash: sha256:<원문 해시>`` 를 **여는 `---` 바로 뒤에** 넣는다.
  :func:`strip_inherited` 가 그 두 줄을 걷으면 원문과 바이트가 같다 — 사본이 고쳐졌는지는 그 비교로 안다.
- **같은 ID 의 두 파일 중 하나만 센다** (:func:`effective_task_files`). 안 고친 사본은 원본의 그림자라 버리고,
  고친 사본은 원본보다 새것이라 원본을 버린다. 로드맵처럼 네임스페이스 전체를 훑는 집계가 이중으로 세지 않는다.
- **합류(아카이브) 때 고친 사본을 원본 자리로 되돌려 적는다** (:func:`plan_write_back`). 원본이 그 사이
  바뀌었으면(해시 불일치) 덮지 않고 충돌로 보고한다 — 아카이브는 그 브랜치를 막는다.
"""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

INHERITED_FROM_KEY = "inherited_from"
INHERITED_HASH_KEY = "inherited_hash"
#: 옮겨 오는 task 상태 — 닫힌 task 는 모 브랜치의 이력이지 이어받을 일이 아니다.
INHERITABLE_STATES: tuple[str, ...] = ("in_progress", "blocked", "planned")

WRITE_BACK = "write_back"
UNCHANGED = "unchanged"
CONFLICT = "conflict"
ORIGIN_MISSING = "origin_missing"


def content_hash(text: str) -> str:
    """끝 공백은 정규화한다 — task 작성기(`_write_lines`)가 `rstrip() + "\\n"` 으로 쓰므로, 그 차이를 '수정' 으로 읽지 않는다."""
    return "sha256:" + hashlib.sha256((text.rstrip() + "\n").encode("utf-8")).hexdigest()


def origin_label(branch: str, sha: str | None) -> str:
    return f"{branch}@{sha}" if sha else branch


def parse_origin(label: str) -> tuple[str, str | None]:
    branch, _, sha = label.partition("@")
    return branch, (sha or None)


def mark_inherited(text: str, *, origin: str) -> str:
    """원문 task 에 원류 두 줄을 넣는다. frontmatter 가 없으면 원류를 적을 자리가 없다 — 거절한다."""
    head, sep, rest = text.partition("\n")
    if head.strip() != "---" or not sep:
        raise ValueError("frontmatter 가 없는 task 는 이어받을 수 없다 (원류를 적을 자리가 없다)")
    return f"{head}\n{INHERITED_FROM_KEY}: {origin}\n{INHERITED_HASH_KEY}: {content_hash(text)}\n{rest}"


def _inheritance_lines(text: str) -> tuple[str, str] | None:
    lines = text.split("\n", 3)
    if len(lines) < 4 or lines[0].strip() != "---":
        return None
    a, b = lines[1], lines[2]
    if a.startswith(f"{INHERITED_FROM_KEY}: ") and b.startswith(f"{INHERITED_HASH_KEY}: "):
        return a.split(": ", 1)[1].strip(), b.split(": ", 1)[1].strip()
    return None


def strip_inherited(text: str) -> str:
    """:func:`mark_inherited` 의 정확한 역. 원류 줄이 없으면 그대로."""
    if _inheritance_lines(text) is None:
        return text
    first, _a, _b, rest = text.split("\n", 3)
    return f"{first}\n{rest}"


@dataclass(frozen=True)
class Inheritance:
    origin_branch: str
    origin_sha: str | None
    original_hash: str
    modified: bool


def inheritance_of(text: str) -> Inheritance | None:
    found = _inheritance_lines(text)
    if found is None:
        return None
    origin, original_hash = found
    branch, sha = parse_origin(origin)
    return Inheritance(branch, sha, original_hash, content_hash(strip_inherited(text)) != original_hash)


def effective_task_files(paths: Iterable[Path]) -> list[Path]:
    """같은 task ID 가 여러 네임스페이스에 있을 때 **하나만** 남긴다 (모듈 docstring 규칙)."""
    by_id: dict[str, list[tuple[Path, Inheritance | None]]] = {}
    for path in paths:
        by_id.setdefault(path.stem, []).append((path, inheritance_of(path.read_text(encoding="utf-8"))))
    out: list[Path] = []
    for entries in by_id.values():
        modified = [p for p, inh in entries if inh is not None and inh.modified]
        if modified:
            out.extend(modified)
            continue
        plain = [p for p, inh in entries if inh is None]
        # 원본이 이 체크아웃에 없으면(아카이브됨 등) 안 고친 사본이라도 유일한 기록이다.
        out.extend(plain or [p for p, _ in entries])
    return sorted(out)


@dataclass(frozen=True)
class WriteBackItem:
    task_id: str
    origin_branch: str
    copy_path: Path
    origin_path: Path
    action: str


def plan_write_back(branch_dir: Path, active_dir: Path) -> list[WriteBackItem]:
    """합류하는 브랜치 네임스페이스의 이어받은 task 를 모 브랜치 원본과 대조한다."""
    tasks_dir = branch_dir / "backlog" / "tasks"
    items: list[WriteBackItem] = []
    if not tasks_dir.is_dir():
        return items
    for copy_path in sorted(tasks_dir.glob("TASK-*.md")):
        inh = inheritance_of(copy_path.read_text(encoding="utf-8"))
        if inh is None:
            continue
        origin_path = active_dir / inh.origin_branch / "backlog" / "tasks" / copy_path.name
        if not inh.modified:
            action = UNCHANGED
        elif not origin_path.is_file():
            action = ORIGIN_MISSING
        elif content_hash(origin_path.read_text(encoding="utf-8")) != inh.original_hash:
            action = CONFLICT
        else:
            action = WRITE_BACK
        items.append(WriteBackItem(copy_path.stem, inh.origin_branch, copy_path, origin_path, action))
    return items


def _frontmatter_value(text: str, key: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    return ""


def handoff_line(text: str, label: str) -> str:
    """handoff 의 `- <label>: 값` 한 줄의 값. 없으면 빈 문자열."""
    prefix = f"- {label}:"
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return ""


def insert_frontmatter_line(text: str, key: str, value: str) -> str:
    """여는 `---` 바로 뒤에 `key: value` 한 줄. 이미 있으면 그대로."""
    head, sep, rest = text.partition("\n")
    if head.strip() != "---" or not sep or _frontmatter_value(text, key):
        return text
    return f"{head}\n{key}: {value}\n{rest}"


def task_title(text: str, task_id: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"# {task_id}"):
            return line[len(f"# {task_id}"):].lstrip(" —-").strip() or task_id
    return task_id


def apply_write_back(item: WriteBackItem) -> None:
    """고친 사본을 원류 표시 없이 원본 자리에 쓰고, 원본 쪽 daily index 의 status 를 맞춘다."""
    from workflow_kit.common.workflow_writes import upsert_backlog_entry  # noqa: PLC0415 — 순환 회피

    restored = strip_inherited(item.copy_path.read_text(encoding="utf-8"))
    origin_dir = item.origin_path.parent.parent.parent  # <active>/<branch>/backlog/tasks/<id>.md
    source_path = _frontmatter_value(restored, "source_path") or ""
    backlog_path = origin_dir / source_path if source_path.startswith("backlog/") else None
    if backlog_path is None or not backlog_path.is_file():
        item.origin_path.write_text(restored, encoding="utf-8")
        return
    upsert_backlog_entry(
        backlog_path=backlog_path,
        task_id=item.task_id,
        entry_lines=restored.rstrip("\n").split("\n"),
        title=task_title(restored, item.task_id),
        kind=_frontmatter_value(restored, "kind") or "generic",
        status=_frontmatter_value(restored, "status") or "planned",
        preserve_index_block=True,
    )


_LINK_RE = re.compile(r"\]\(([^)\s]+)\)")


def relocate_markdown_links(text: str, *, from_dir: Path, to_dir: Path) -> str:
    """옮겨 적는 handoff 줄의 상대 링크를 새 위치 기준으로 다시 잡는다.

    모 브랜치 `active/main/` 의 `../../../../x` 는 슬래시 브랜치 `active/claude/<name>/` 에서 한 단계 모자라
    깨진다 (2026-10-02 실측). task 파일은 원문 그대로 두므로(합류 때 되돌려 적는다) 여기서 고치지 않는다.
    """
    def repl(m: re.Match[str]) -> str:
        target = m.group(1)
        if "://" in target or target.startswith(("#", "/", "mailto:")):
            return m.group(0)
        path, sep, anchor = target.partition("#")
        moved = os.path.relpath(os.path.normpath(from_dir / path), to_dir)
        return f"]({Path(moved).as_posix()}{sep}{anchor})"

    return _LINK_RE.sub(repl, text)
