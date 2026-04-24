"""Workflow markdown write helpers for safe, narrow document updates."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from workflow_kit.common.markdown import rel_link_from_doc
from workflow_kit.common.project_docs import TASK_HEADER_RE


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _replace_scalar_value(lines: list[str], label: str, value: str) -> list[str]:
    prefix = f"- {label}:"
    for idx, line in enumerate(lines):
        if line.strip() == prefix and idx + 1 < len(lines):
            updated = list(lines)
            updated[idx + 1] = f"- {value}"
            return updated
    return lines


def _replace_list_after_label(lines: list[str], label: str, items: list[str]) -> list[str]:
    prefix = f"- {label}:"
    for idx, line in enumerate(lines):
        if line.strip() != prefix:
            continue
        start = idx + 1
        end = start
        while end < len(lines):
            stripped = lines[end].strip()
            if stripped.startswith("## "):
                break
            if stripped.startswith("- "):
                end += 1
                continue
            if stripped == "":
                end += 1
                continue
            break
        replacement = [f"- {item}" for item in items] if items else ["- "]
        return lines[:start] + replacement + lines[end:]
    return lines


def _ensure_related_doc_links(lines: list[str], *, backlog_path: Path) -> list[str]:
    related = [
        f"`{rel_link_from_doc(backlog_path, backlog_path.parent.parent / 'work_backlog.md')}`",
        f"`{rel_link_from_doc(backlog_path, backlog_path.parent.parent / 'session_handoff.md')}`",
        f"`{rel_link_from_doc(backlog_path, backlog_path.parent.parent / 'project_workflow_profile.md')}`",
    ]
    return _replace_list_after_label(lines, "관련 문서", related)


def render_daily_backlog_header(*, backlog_path: Path) -> list[str]:
    backlog_date = backlog_path.stem
    lines = [
        f"# {backlog_date} 작업 백로그",
        "",
        f"- 문서 목적: {backlog_date}에 수행한 작업의 계획, 진행 현황, 완료 내역을 기록한다.",
        f"- 범위: {backlog_date} 작업 이력",
        "- 대상 독자: 프로젝트 참여자, 문서 작성자, 개발자, 운영자",
        "- 상태: draft",
        f"- 최종 수정일: {date.today().isoformat()}",
        "- 관련 문서:",
        "",
    ]
    return _ensure_related_doc_links(lines, backlog_path=backlog_path)


def upsert_backlog_entry(*, backlog_path: Path, task_id: str, entry_lines: list[str]) -> str:
    lines = _read_lines(backlog_path)
    if not lines:
        lines = render_daily_backlog_header(backlog_path=backlog_path)

    lines = _replace_scalar_value(lines, "최종 수정일", date.today().isoformat())
    lines = _ensure_related_doc_links(lines, backlog_path=backlog_path)

    header_prefix = f"## {task_id} "
    start: int | None = None
    end: int | None = None
    for idx, line in enumerate(lines):
        if line.startswith(header_prefix):
            start = idx
            end = idx + 1
            while end < len(lines) and not lines[end].startswith("## "):
                end += 1
            break

    updated = list(lines)
    if start is None:
        if updated and updated[-1] != "":
            updated.append("")
        updated.extend(entry_lines)
        action = "created"
    else:
        updated = updated[:start] + entry_lines + updated[end:]
        action = "updated"

    _write_lines(backlog_path, updated)
    return action


def ensure_backlog_index_entry(*, work_backlog_index_path: Path, daily_backlog_path: Path) -> bool:
    lines = _read_lines(work_backlog_index_path)
    if not lines:
        return False

    lines = _replace_scalar_value(lines, "최종 수정일", date.today().isoformat())
    link_target = rel_link_from_doc(work_backlog_index_path, daily_backlog_path)
    link_line = f"- [{daily_backlog_path.stem} 작업 백로그]({link_target})"
    if any(line.strip() == link_line for line in lines):
        _write_lines(work_backlog_index_path, lines)
        return False

    insert_at = None
    for idx, line in enumerate(lines):
        if line.strip() == "## 날짜별 백로그 문서":
            insert_at = idx + 1
            while insert_at < len(lines) and (
                lines[insert_at].strip() == "" or lines[insert_at].strip().startswith("- ")
            ):
                insert_at += 1
            break
    if insert_at is None:
        lines.extend(["", "## 날짜별 백로그 문서", link_line])
    else:
        lines = lines[:insert_at] + [link_line] + lines[insert_at:]
    _write_lines(work_backlog_index_path, lines)
    return True


def sync_handoff_status(*, handoff_path: Path, task_label: str, status: str) -> None:
    lines = _read_lines(handoff_path)
    if not lines:
        return

    label_map = {
        "in_progress": "현재 `in_progress` 작업",
        "blocked": "현재 `blocked` 작업",
        "done": "최근 완료 작업 목록",
    }
    target_label = label_map.get(status)
    if target_label is None:
        return

    current_lists = {
        "현재 `in_progress` 작업": [],
        "현재 `blocked` 작업": [],
        "최근 완료 작업 목록": [],
    }
    for section_label in current_lists:
        for idx, line in enumerate(lines):
            if line.strip() == f"- {section_label}:":
                items: list[str] = []
                pointer = idx + 1
                while pointer < len(lines):
                    stripped = lines[pointer].strip()
                    if stripped.startswith("## "):
                        break
                    if stripped.startswith("- "):
                        value = stripped[2:].strip().strip("`")
                        if value:
                            items.append(value)
                        pointer += 1
                        continue
                    if stripped == "":
                        pointer += 1
                        continue
                    break
                current_lists[section_label] = items
                break

    for section_label, items in current_lists.items():
        current_lists[section_label] = [item for item in items if item != task_label]
    current_lists[target_label].append(task_label)

    lines = _replace_scalar_value(lines, "최종 수정일", date.today().isoformat())
    for section_label, items in current_lists.items():
        lines = _replace_list_after_label(lines, section_label, items)
    _write_lines(handoff_path, lines)


def append_unique_bullets_under_heading(*, doc_path: Path, heading: str, bullets: list[str]) -> bool:
    lines = _read_lines(doc_path)
    if not lines or not bullets:
        return False

    heading_line = f"## {heading}"
    start: int | None = None
    end: int | None = None
    for idx, line in enumerate(lines):
        if line.strip() == heading_line:
            start = idx + 1
            end = start
            while end < len(lines) and not lines[end].startswith("## "):
                end += 1
            break
    if start is None or end is None:
        return False

    existing = {
        line.strip()[2:].strip()
        for line in lines[start:end]
        if line.strip().startswith("- ") and line.strip()[2:].strip()
    }
    additions = [bullet for bullet in bullets if bullet not in existing]
    if not additions:
        return False

    updated = list(lines)
    insertion = [f"- {bullet}" for bullet in additions]
    updated = updated[:end] + insertion + updated[end:]
    updated = _replace_scalar_value(updated, "최종 수정일", date.today().isoformat())
    _write_lines(doc_path, updated)
    return True
