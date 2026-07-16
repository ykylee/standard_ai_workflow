#!/usr/bin/env python3
"""Migrate the legacy single `work_backlog.md` into the v0.14.0 append-only layout.

입력: `ai-workflow/memory/active/backlog` (legacy)
출력:
  - `ai-workflow/memory/active/backlog/<YYYY-MM-DD>.md`  (per-day index, link-only)
  - `ai-workflow/memory/active/backlog/tasks/TASK-<YYYY-MM-DD>-<NNN>.md`  (per-task SSOT)
  - `ai-workflow/memory/active/sessions/<YYYY-MM-DD>-<topic>.md`  (per-session)

본 script 는 **idempotent** — 동일 입력으로 두 번 실행해도 같은 결과. Dry-run 이 default
(`--apply` flag 가 있어야 실제 write). 본 release (v0.14.0) 의 1st deprecation cycle 의
fallback 으로 work_backlog.md 가 deprecated 위치에 보존됨 (rename to .bak 후 drop).
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ACTIVE_DIR = REPO_ROOT / "ai-workflow" / "memory" / "active"
LEGACY_FILE = ACTIVE_DIR / "work_backlog.md"
BACKLOG_DIR = ACTIVE_DIR / "backlog"
TASKS_DIR = BACKLOG_DIR / "tasks"
SESSIONS_DIR = ACTIVE_DIR / "sessions"

ENTRY_RE = re.compile(r"^###\s+\[\[(?P<path>[^\]]+)\]\]\s+\{#(?P<anchor>[^}]+)\}\s*$")
DATE_BULLET_RE = re.compile(r"^-\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<summary>.*)$")
H2_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$")


@dataclass
class Entry:
    """One `### [[path]] {#anchor}` block from legacy work_backlog.md."""

    raw_path: str
    anchor: str
    date: str
    summary: str
    body_lines: list[str] = field(default_factory=list)
    kind: str = "generic"  # 'release' | 'session' | 'generic'
    task_id: str = ""
    output_path: Path | None = None


def parse_entries(text: str) -> tuple[list[str], list[Entry], list[str]]:
    """Parse work_backlog.md into (header_lines, entries, footer_lines).

    `## 최근 작업 백로그` section 안의 `###` block 만 Entry 로 변환.
    다른 `##` section 은 그대로 유지 (footer 처리 — index rules, 다음에 읽을 문서 등).
    """
    lines = text.splitlines()
    header_lines: list[str] = []
    entries: list[Entry] = []
    footer_lines: list[str] = []
    current_entry: Entry | None = None
    current_section: str = ""  # '' | 'header' | 'recent' | 'footer'

    for line in lines:
        h2_match = H2_RE.match(line)
        if h2_match:
            title = h2_match.group("title")
            if title.startswith("인덱스 규칙"):
                current_section = "header"
                header_lines.append(line)
                continue
            if title.startswith("최근 작업 백로그"):
                current_section = "recent"
                continue
            # 그 외 ## (다음에 읽을 문서, v0.7.25 in-flight housekeeping 등)
            current_section = "footer"
            footer_lines.append(line)
            continue

        if current_section == "header":
            header_lines.append(line)
            continue

        if current_section == "footer":
            footer_lines.append(line)
            continue

        # current_section == 'recent'
        m = ENTRY_RE.match(line)
        if m:
            if current_entry is not None:
                entries.append(current_entry)
            current_entry = Entry(
                raw_path=m.group("path"),
                anchor=m.group("anchor"),
                date="",
                summary="",
                body_lines=[],
            )
            continue

        if current_entry is not None:
            current_entry.body_lines.append(line)
            if not current_entry.date:
                dm = DATE_BULLET_RE.match(line.strip())
                if dm:
                    current_entry.date = dm.group("date")
                    current_entry.summary = dm.group("summary").strip()
            continue

        # `## 최근 작업 백로그` 직후 또는 entry 사이 빈 줄 등
        # — 무시 (preserving canonical layout)

    if current_entry is not None:
        entries.append(current_entry)
    return header_lines, entries, footer_lines


DATE_IN_PATH_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _infer_date_from_path(raw_path: str) -> str:
    """path stem 에서 YYYY-MM-DD 추출. 부재 시 ''."""
    m = DATE_IN_PATH_RE.search(raw_path)
    return m.group(1) if m else ""


def classify(entry: Entry) -> None:
    """Classify entry.kind + assign task_id (TASK-YYYY-MM-DD-NNN) / session id."""
    p = entry.raw_path
    if p.startswith("release/"):
        entry.kind = "release"
    elif p.startswith("active/session_analysis_") or p.startswith("active/audit_"):
        entry.kind = "session"
    elif p.startswith("main/"):
        entry.kind = "generic"
    else:
        entry.kind = "generic"
    # date 부재 시 path stem 에서 추출 (body 빈 entry 대비)
    if not entry.date:
        entry.date = _infer_date_from_path(p)


def make_task_id(date: str, n: int) -> str:
    return f"TASK-{date}-{n:03d}"


def build_daily_index(date: str, entries: list[Entry]) -> str:
    """Generate backlog/<date>.md — link-only index."""
    lines = [
        f"# Backlog Index — {date}",
        "",
        "- 문서 목적: 해당 날짜의 작업 항목(task) SSOT link 모음.",
        "- 범위: 해당 일자(task 단위)의 모든 task.",
        "- 대상 독자: AI agent (session-start / backlog-update), maintainer.",
        "- 상태: stable (v0.14.0 신규 layout).",
        f"- 최종 수정일: {date}",
        "- 관련 문서: [./tasks/TASK-XXX.md](./tasks/TASK-XXX.md) (per-task SSOT)",
        "",
        "## Tasks",
        "",
    ]
    for e in sorted(entries, key=lambda x: x.task_id):
        rel = e.output_path.relative_to(BACKLOG_DIR.parent) if e.output_path else ""
        title = e.summary or e.anchor
        kind_marker = "🔧 release" if e.kind == "release" else (
            "📝 session" if e.kind == "session" else "• generic"
        )
        lines.append(f"- **{e.task_id}** [{kind_marker}] {title}")
        lines.append(f"  - path: `{rel}`")
        lines.append(f"  - source: `[[{e.raw_path}]] {{#{e.anchor}}}`")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"_본 daily index 는 work_backlog.md (legacy) 의 `### [[path]]` section 들을")
    lines.append(f"분할하여 자동 생성됨. Migration tool: `workflow-source/tools/migrate_active_to_appendonly.py`._")
    return "\n".join(lines)


def build_task_file(entry: Entry) -> str:
    """Generate backlog/tasks/TASK-XXX.md per-task SSOT."""
    title = entry.summary or entry.anchor
    fm = [
        "---",
        f"id: {entry.task_id}",
        f"status: {'done' if entry.kind == 'release' else 'recorded'}",
        f"created_at: {entry.date}",
        f"source_anchor: {entry.anchor}",
        f"source_path: {entry.raw_path}",
        f"kind: {entry.kind}",
        "---",
        "",
        f"# {entry.task_id} — {title}",
        "",
        "## 📝 Description",
        "",
        f"- 출처: `[[{entry.raw_path}]] {{#{entry.anchor}}}` (legacy work_backlog.md inline section)",
        f"- 분류: `{entry.kind}`",
        f"- 작성일: {entry.date}",
        "",
        "## 🛠️ Implementation / Content",
        "",
    ]
    body = "\n".join(line for line in entry.body_lines if line.strip())
    if not body:
        body = "_(legacy inline 본문 없음 — 요약만 보존)_"
    fm.append(body)
    fm.append("")
    fm.append("## ✅ Outcome")
    fm.append("")
    fm.append(f"- v0.14.0 migration 으로 per-task SSOT 로 분리됨. 원본은 `work_backlog.md.bak` 에 보존.")
    fm.append("")
    return "\n".join(fm)


def build_session_file(entry: Entry) -> str:
    """Generate sessions/<stem>.md per-session — file name 은 raw_path stem 그대로 사용
    (예: `session_analysis_2026-07-09`, `audit_follow_up_2026-07-09`) → 같은 session 안의
    두 entry 가 같은 파일 이름으로 overwrite 되는 사고 방지."""
    stem = Path(entry.raw_path).stem  # 'session_analysis_2026-07-09' / 'audit_follow_up_2026-07-09'
    topic = stem  # 표기용 (raw stem 그대로 사용)

    lines = [
        f"# Session — {entry.date} / {topic}",
        "",
        "- 문서 목적: 특정 세션의 작업 단기 메모리 (영구 보존 대상 아님 — 단, 본문은 wiki/topics/ 와 함께 보존).",
        f"- 날짜: {entry.date}",
        f"- 주제: `{topic}`",
        f"- 출처: `[[{entry.raw_path}]] {{#{entry.anchor}}}`",
        "- 상태: stable",
        "",
        "## 📋 Session Summary",
        "",
        entry.summary or "_(summary 없음)_",
        "",
        "## 🛠️ Detail",
        "",
    ]
    body = "\n".join(line for line in entry.body_lines if line.strip())
    lines.append(body or "_(detail 없음)_")
    lines.append("")
    lines.append("## ✅ Outcome")
    lines.append("")
    lines.append(f"- v0.14.0 migration 으로 per-session 파일로 분리됨. 원본은 `work_backlog.md.bak` 에 보존.")
    lines.append("")
    return "\n".join(lines)


def assign_task_ids(entries: list[Entry]) -> None:
    """Assign TASK-YYYY-MM-DD-NNN id per (date, order)."""
    by_date: dict[str, list[Entry]] = defaultdict(list)
    for e in entries:
        by_date[e.date].append(e)
    for date, items in by_date.items():
        for n, e in enumerate(items, start=1):
            e.task_id = make_task_id(date, n)


def resolve_output_paths(entries: list[Entry]) -> None:
    """Resolve each entry.output_path based on its kind."""
    for e in entries:
        if e.kind == "session":
            # raw_path stem 그대로 사용 → 같은 entry 의 두 본문이 overwrite 되지 않음
            stem = Path(e.raw_path).stem
            e.output_path = SESSIONS_DIR / f"{stem}.md"
        else:
            e.output_path = TASKS_DIR / f"{e.task_id}.md"


def group_by_date(entries: list[Entry]) -> dict[str, list[Entry]]:
    out: dict[str, list[Entry]] = defaultdict(list)
    for e in entries:
        out[e.date].append(e)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate legacy single work_backlog.md → v0.14.0 append-only layout",
    )
    parser.add_argument("--apply", action="store_true", help="실제 write (default: dry-run)")
    parser.add_argument(
        "--legacy-backup",
        action="store_true",
        help="`work_backlog.md` → `work_backlog.md.bak` 으로 rename (--apply 와 함께 사용)",
    )
    parser.add_argument(
        "--active-dir",
        type=Path,
        default=ACTIVE_DIR,
        help="active/ 루트 경로 (default: <repo>/ai-workflow/memory/active)",
    )
    args = parser.parse_args()

    active_dir: Path = args.active_dir
    legacy_file = active_dir / "work_backlog.md"
    backlog_dir = active_dir / "backlog"
    tasks_dir = backlog_dir / "tasks"
    sessions_dir = active_dir / "sessions"

    if not legacy_file.exists():
        print(f"[skip] {legacy_file} 부재 — 신규 layout 만 사용 중. exit 0", file=sys.stderr)
        return 0

    text = legacy_file.read_text(encoding="utf-8")
    _, entries, footer = parse_entries(text)

    for e in entries:
        classify(e)
    # date 부재 entry → "unknown-date" 로 fallback
    for e in entries:
        if not e.date:
            e.date = "1970-01-01"
            e.kind = "generic"
    assign_task_ids(entries)
    resolve_output_paths(entries)

    # daily index group
    by_date = group_by_date(entries)

    # summary
    print(f"[plan] entries={len(entries)} dates={len(by_date)} kinds=", end="")
    kinds: dict[str, int] = defaultdict(int)
    for e in entries:
        kinds[e.kind] += 1
    print(", ".join(f"{k}={v}" for k, v in sorted(kinds.items())))

    if not args.apply:
        print("[dry-run] --apply flag 없이 실행됨. 실제 write ❌. 위 plan 만 emit.")
        print()
        print("Sample (top 5):")
        for e in entries[:5]:
            print(f"  {e.kind:8s} {e.task_id}  {e.date}  → {e.output_path.relative_to(active_dir)}")
        print()
        print("Daily indexes:")
        for date, items in sorted(by_date.items()):
            print(f"  backlog/{date}.md  ({len(items)} tasks)")
        return 0

    # ---- apply ----
    tasks_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # 1) write per-task + per-session files
    for e in entries:
        assert e.output_path is not None
        if e.kind == "session":
            content = build_session_file(e)
        else:
            content = build_task_file(e)
        e.output_path.write_text(content, encoding="utf-8")

    # 2) write daily indexes
    for date, items in sorted(by_date.items()):
        idx_path = backlog_dir / f"{date}.md"
        idx_path.write_text(build_daily_index(date, items), encoding="utf-8")

    # 3) optional legacy backup
    if args.legacy_backup:
        backup = legacy_file.with_suffix(".md.bak")
        if not backup.exists():
            shutil.copy2(legacy_file, backup)
        legacy_file.unlink()
        print(f"[backup] {legacy_file} → {backup.name}")
    else:
        print(f"[keep]   {legacy_file} 그대로 보존 (v0.14.0 1st cycle fallback)")

    print()
    print(f"[done] {len(entries)} entries migrated to append-only layout.")
    print(f"  - tasks:      {len([e for e in entries if e.kind != 'session'])} files in backlog/tasks/")
    print(f"  - sessions:   {len([e for e in entries if e.kind == 'session'])} files in sessions/")
    print(f"  - daily idx:  {len(by_date)} files in backlog/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())