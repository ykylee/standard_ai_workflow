#!/usr/bin/env python3
"""in-repo wiki L2 stub 4종을 **현재 memory SSOT 에서 파생**한다.

L2 는 1차 출처가 아니라 *파생 뷰* 다. `ai-workflow/wiki/sources/` 의 4개
stub 은 각각 정해진 L1 SSOT 를 하나씩 갖고, 본 tool 은 그 L1 을 읽어 압축
본문을 emit 하고 `last_touched` 를 **실제 emit 일자**로 적는다.

| L2 stub | L1 SSOT |
|---|---|
| `active-state` | `memory/active/<branch>/state.json` |
| `active-work-backlog` | `memory/active/<branch>/backlog/<최신>.md` |
| `active-session-handoff` | `memory/active/<branch>/session_handoff.md` |
| `wiki-log` | `ai-workflow/wiki/log.md` |

**`--refresh-raw` 는 은퇴했다 (TASK-2026-08-18-main-004).** 그 단계는 L1 을
*쓰는* 경로였고, 쓰려던 4개 대상이 전부 무너져 있었다:

- `state.json` — 정본 §11.2 가 **생성 산출물**로 확정했고 `wk refresh-state`
  가 유일한 생성기다. 이 tool 이 `recent_done_items` 를 직접 쓰면 **두 번째
  writer** 가 되어 SSOT(backlog/tasks + session_handoff)와 갈라진다.
- `work_backlog.md` — v0.14.0 append-only layout 에서 사라졌다
  (`backlog/<날짜>.md` 로 대체). apply 는 `FileNotFoundError` 였다.
- `memory/log.md` — entry 문자열을 만들고 **쓰지 않는** 죽은 코드였다.
- `wiki/log.md` — 날짜(`2026-06-13`)와 릴리스(`v0.7.0~v0.7.4`)가 하드코딩이라
  실행할수록 2026-06 스냅샷으로 되돌렸다.

같은 이유로 이전 `--emit-l2` 도 위험했다: `rc=0` 인 채 본문을 2026-06-14
스냅샷으로 재생성하고 `last_touched` 를 그 날짜로 **뒷걸음질**시켰다. 그 결과
`score_wiki_maintainability` 의 `lifecycle`(30일 신선도)이 무너지는데도
종료 코드는 성공이었다.

Usage:
    # 어떤 stub 이 무엇에서 파생되는지 미리 보기
    python3 -m workflow_kit.tools.refresh_wiki_memory --emit-l2 --dry-run

    # 실제 emit
    python3 -m workflow_kit.tools.refresh_wiki_memory --emit-l2 --apply

    # JSON 출력 (CI 통합)
    python3 -m workflow_kit.tools.refresh_wiki_memory --emit-l2 --apply --json

REPO_ROOT 결정 (v0.7.12+ auto-detect):
    1. `--repo-root=<path>` CLI flag (명시적)
    2. `STANDARD_AI_WF_REPO` env var (CI integration)
    3. `git rev-parse --show-toplevel` subprocess
    4. legacy fallback: `~/repos/standard_ai_workflow_minimax` (deprecation 경고)

Reference:
- workflow_kit/tools/emit_wiki_l2_body.py (L1 wiki page → L2 파생 뷰, 다른 축)
- workflow_kit/tools/score_wiki_maintainability.py (lifecycle = last_touched 신선도)
- workflow_kit/tools/wiki_emit.py (본 tool 을 포함한 파이프라인 wrapper)
- ai-workflow/wiki/SCHEMA.md (status 어휘 = active|draft|deprecated)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# v0.7.15+ atomic_write (POSIX os.replace guarantee)
try:
    from workflow_kit.common.atomic_write import atomic_write_text
except ImportError:
    # standalone script (no workflow_kit on sys.path) — fall back to direct write.
    # atomic guarantee 없이 (file truncation possible mid-write).
    atomic_write_text = None  # type: ignore[assignment]

# v1.0.0 branch-scoped memory: 작업 상태 파일은 `memory/active/` 바로 아래가 아니라
# `memory/active/<branch>/` 에 있다. 규칙을 여기에 복사하지 않고 정식 resolver 를 쓴다.
try:
    from workflow_kit.common.paths import path_in_active
except ImportError:
    path_in_active = None  # type: ignore[assignment]

_LEGACY_REPO_ROOT = Path.home() / "repos" / "standard_ai_workflow_minimax"
_DEPRECATION_WARNED = False


def get_repo_root(cli_value: str | os.PathLike[str] | None = None, *, _suppress_warning: bool = False) -> Path:
    """REPO_ROOT 결정 (priority: CLI flag > env var > git rev-parse > legacy fallback).

    Args:
        cli_value: `--repo-root` 로 넘어온 경로. None 이면 다음 우선순위로.
        _suppress_warning: legacy fallback 의 deprecation 경고 억제 (test 용).
    """
    global _DEPRECATION_WARNED

    # 1. CLI flag
    if cli_value:
        return Path(cli_value).expanduser().resolve()

    # 2. env var
    env_value = os.environ.get("STANDARD_AI_WF_REPO")
    if env_value:
        return Path(env_value).expanduser().resolve()

    # 3. git rev-parse --show-toplevel
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return Path(proc.stdout.strip()).resolve()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # 4. legacy fallback (deprecation warning 1회)
    if not _DEPRECATION_WARNED and not _suppress_warning:
        _DEPRECATION_WARNED = True
        print(
            f"[DEPRECATION] refresh_wiki_memory.py: REPO_ROOT auto-detect 실패 — legacy fallback 사용 ({_LEGACY_REPO_ROOT}). "
            "v0.7.12+ 부터 --repo-root=<path> 또는 STANDARD_AI_WF_REPO env var 사용 권장.",
            file=sys.stderr,
        )
    return _LEGACY_REPO_ROOT


REPO_ROOT = get_repo_root()  # eager init for backward compat (module-level read)

# v0.7.17+ in-repo storage: 외부 vault (~/wiki/) 연결 완전 제거. 모든 path 가
# REPO_ROOT 안쪽. PROJECT_SLUG 는 *legacy* field (multi-project metadata) 로 유지.
PROJECT_SLUG = "standard-ai-workflow"
# 1차 출처 (L1) — in-repo wiki + memory/active
L1_BASE = REPO_ROOT / "ai-workflow"
# 2차 출처 (L2 파생 뷰) — in-repo wiki/sources
L2_BASE = L1_BASE / "wiki" / "sources"

ACTIVE_BASE = L1_BASE / "memory" / "active"

#: L2 본문 기본 상한 (자). `--max-chars` 로 조정.
DEFAULT_MAX_CHARS = 2000

#: `wiki/sources/` 의 frontmatter `status` 는 SCHEMA §1.1 의 어휘만 쓴다
#: (`active|draft|deprecated`). L2 stub 은 **매 사이클 재생성되는 생성물**이라
#: "사람이 검토함" 상태가 구조적으로 붙지 않으므로 `draft` 로 고정한다.
#: (이전 emit 경로가 쓰던 `reviewed` 는 SCHEMA 어디에도 정의된 적이 없다 —
#: `score_wiki_maintainability.score_lifecycle` 의 docstring 이 같은 지적을 한다.)
GENERATED_STATUS = "draft"


def _active_path(leaf: str) -> Path:
    """`memory/active/` 하위 작업 상태 파일의 branch-scoped 경로."""
    if path_in_active is not None:
        return path_in_active(ACTIVE_BASE, leaf)
    # standalone script fallback — branch 해석 불가 시 legacy 경로.
    return ACTIVE_BASE / leaf


# L2 stub 4 file (파생 뷰 대상, in-repo)
L2_STUBS = {
    "active-state": L2_BASE / "active-state.md",
    "active-work-backlog": L2_BASE / "active-work-backlog.md",
    "active-session-handoff": L2_BASE / "active-session-handoff.md",
    "wiki-log": L2_BASE / "wiki-log.md",
}


# ---------------------------------------------------------------------------
# L1 SSOT 해석
# ---------------------------------------------------------------------------


def latest_backlog_path() -> Path | None:
    """`backlog/` 의 가장 최근 일자 index (`YYYY-MM-DD.md`).

    v0.14.0 append-only layout. 파일명이 날짜라 사전순 = 시간순이다.
    """
    backlog_dir = _active_path("backlog")
    if not backlog_dir.is_dir():
        return None
    dated = sorted(
        p for p in backlog_dir.glob("*.md")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)
    )
    return dated[-1] if dated else None


def l1_sources() -> dict[str, Path | None]:
    """L2 stub 이름 → 그 stub 이 파생되는 L1 SSOT 경로.

    값이 None 이면 **그 L1 이 이 저장소에 없다** — emit 은 그 stub 을 건너뛰고
    `missing_l1` 로 보고한다. 없는 것을 있는 것처럼 채우지 않는다.
    """
    state_json = _active_path("state.json")
    handoff = _active_path("session_handoff.md")
    backlog = latest_backlog_path()
    wiki_log = L1_BASE / "wiki" / "log.md"
    return {
        "active-state": state_json if state_json.exists() else None,
        "active-work-backlog": backlog if backlog and backlog.exists() else None,
        "active-session-handoff": handoff if handoff.exists() else None,
        "wiki-log": wiki_log if wiki_log.exists() else None,
    }


def _rel_to_repo(p: Path) -> str:
    """REPO_ROOT 상대 경로 문자열. 밖이면 절대 경로 그대로."""
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def _line_count(p: Path) -> int:
    with p.open(encoding="utf-8", errors="ignore") as fh:
        return sum(1 for _ in fh)


def _truncate(body: str, max_chars: int) -> str:
    """본문 상한. 줄 경계에서 자르고 잘렸음을 본문에 남긴다."""
    if len(body) <= max_chars:
        return body
    return body[:max_chars].rsplit("\n", 1)[0] + "\n\n... (이후 본문은 L1 SSOT 참조)"


# ---------------------------------------------------------------------------
# stub 별 본문 파생
# ---------------------------------------------------------------------------


def _derive_active_state(p: Path) -> str:
    """`state.json` 에서 현재 축 / 초점 / 진행·차단·완료 목록을 뽑는다."""
    data = json.loads(p.read_text(encoding="utf-8"))
    session = data.get("session", {}) or {}
    backlog = data.get("backlog", {}) or {}
    sot = data.get("source_of_truth", {}) or {}

    def _bullets(items, empty: str = "- (없음)") -> str:
        items = [str(i).strip() for i in (items or []) if str(i).strip()]
        return "\n".join(f"- {i}" for i in items) if items else empty

    rows = [
        ("`purpose_digest`", data.get("purpose_digest", "")),
        ("`session.current_focus`", session.get("current_focus", "")),
        ("`backlog.task_count`", backlog.get("task_count", "")),
        ("`source_of_truth.latest_backlog_path`", sot.get("latest_backlog_path", "")),
    ]
    def _cell(value) -> str:
        # 표 셀 안의 `|` 는 markdown 표를 깨뜨리므로 escape 한다.
        return str(value).replace("|", "\\|") or "-"

    table = "\n".join(f"| {k} | {_cell(v)} |" for k, v in rows)

    parts = [
        "## SSOT 요약",
        "",
        "| 필드 | 값 |",
        "|---|---|",
        table,
        "",
        "## 진행 중",
        "",
        _bullets(session.get("in_progress_items")),
        "",
        "## 차단",
        "",
        _bullets(session.get("blocked_items")),
        "",
        "## 최근 완료",
        "",
        _bullets(session.get("recent_done_items")),
    ]
    return "\n".join(parts)


def _derive_active_work_backlog(p: Path) -> str:
    """일자별 backlog index 에서 task 목록(id + 제목 + status)을 뽑는다."""
    text = p.read_text(encoding="utf-8")
    entries: list[str] = []
    current: str | None = None
    for line in text.splitlines():
        m = re.match(r"^-\s+\*\*(TASK-[\w.-]+)\*\*\s*(?:\[[^\]]*\])?\s*(.*)$", line)
        if m:
            current = f"- **{m.group(1)}** {m.group(2).strip()}".rstrip()
            entries.append(current)
            continue
        m = re.match(r"^\s+-\s+status:\s*(\S+)", line)
        if m and entries:
            entries[-1] += f" — `{m.group(1)}`"
    body = "\n".join(entries) if entries else "- (등록된 task 없음)"
    return "\n".join([f"## Task 목록 ({p.stem})", "", body])


#: handoff §2/§3 의 lead-in 라벨 줄 (`- 현재 \`in_progress\` 작업:`) — 항목이 아니라
#: 목록의 제목이다. 본문 없이 `:` 로 끝나는 bullet 을 항목으로 세면 "진행 중 1건"
#: 이 실제로는 0건인데도 세어진다.
_IS_LEAD_IN = re.compile(r"^-\s*\S.*:\s*$")


def _derive_active_session_handoff(p: Path) -> str:
    """handoff 의 §1 현재 기준선 + §2 진행 중 + §3 차단 을 뽑는다."""
    text = p.read_text(encoding="utf-8")

    baseline = ""
    m = re.search(r"^-\s*현재 기준선:\s*(.+)$", text, re.MULTILINE)
    if m:
        baseline = m.group(1).strip()

    def _section(num: int) -> str:
        m2 = re.search(
            rf"^##\s*{num}\..*?$\n(.*?)(?=^##\s|\Z)", text, re.MULTILINE | re.DOTALL
        )
        if not m2:
            return ""
        lines = []
        for ln in m2.group(1).splitlines():
            stripped = ln.strip()
            # 빈 줄 · 빈 bullet(`-`) · lead-in 라벨(`- 현재 ... 작업:`) 은 항목이 아니다.
            if not stripped or stripped == "-" or _IS_LEAD_IN.match(stripped):
                continue
            lines.append(ln.rstrip())
        return "\n".join(lines)

    in_progress = _section(2) or "- (없음)"
    blocked = _section(3) or "- (없음)"

    parts = ["## 현재 기준선", ""]
    parts.append(baseline if baseline else "- (기록 없음)")
    parts.extend(["", "## 진행 중", "", in_progress, "", "## 차단", "", blocked])
    return "\n".join(parts)


def _derive_wiki_log(p: Path, keep: int = 5) -> str:
    """wiki/log.md 의 최신 entry N개를 뽑는다 (`## [YYYY-MM-DD] ...` 단위)."""
    text = p.read_text(encoding="utf-8")
    blocks = re.findall(
        r"^##\s*\[\d{4}-\d{2}-\d{2}\].*?(?=^##\s*\[|\Z)", text, re.MULTILINE | re.DOTALL
    )
    if not blocks:
        return "## 최근 ingest/query entry\n\n- (entry 없음)"
    recent = [b.strip() for b in blocks[-keep:]][::-1]
    return "\n\n".join([f"## 최근 entry {len(recent)}건 (최신 우선)", *recent])


#: stub 이름 → 파생 함수. L1 경로 하나를 받아 markdown 본문(헤딩 이하)을 반환.
DERIVERS = {
    "active-state": _derive_active_state,
    "active-work-backlog": _derive_active_work_backlog,
    "active-session-handoff": _derive_active_session_handoff,
    "wiki-log": _derive_wiki_log,
}

#: stub 이름 → 사람이 읽을 제목.
STUB_TITLES = {
    "active-state": "Active State",
    "active-work-backlog": "Active Work Backlog",
    "active-session-handoff": "Active Session Handoff",
    "wiki-log": "Wiki Log",
}


def build_stub_body(name: str, l1_path: Path, today: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """L2 stub 1개의 전체 본문 (frontmatter 제외) 을 만든다."""
    derived = DERIVERS[name](l1_path)
    header = [
        f"# {STUB_TITLES[name]} (Derived View, {today})",
        "",
        f"> L1 SSOT: `{_rel_to_repo(l1_path)}` ({_line_count(l1_path)} lines)",
        "> 본 L2 파생 뷰는 in-repo retrieval 용 압축 요약이다. 정본은 L1 SSOT 를 본다.",
        f"> 생성: `{today}` by `workflow_kit.tools.refresh_wiki_memory --emit-l2`",
        "",
    ]
    return "\n".join(header) + "\n" + _truncate(derived.strip(), max_chars) + "\n"


def _frontmatter(name: str, today: str, existing: str | None) -> str:
    """기존 frontmatter 를 보존하되 `last_touched` 를 today 로 갱신.

    없으면 bootstrap. `status` 는 SCHEMA 어휘로 고정한다 (GENERATED_STATUS).
    """
    if existing is None:
        return (
            "---\n"
            "type: meta\n"
            f"status: {GENERATED_STATUS}\n"
            "r9_skip: true\n"
            f"title: {name}\n"
            f"created: {today}\n"
            f"last_touched: {today}\n"
            "---\n"
        )
    lines = []
    seen_touched = False
    for line in existing.splitlines():
        if line.startswith("last_touched:"):
            lines.append(f"last_touched: {today}")
            seen_touched = True
        elif line.startswith("status:"):
            lines.append(f"status: {GENERATED_STATUS}")
        else:
            lines.append(line)
    if not seen_touched:
        lines.append(f"last_touched: {today}")
    return "---\n" + "\n".join(lines) + "\n---\n"


def _split_frontmatter(text: str) -> str | None:
    """`---\\n...\\n---\\n` 의 안쪽만 반환. 형식이 아니면 None."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    return text[4:end]


def emit_stub(
    name: str,
    l1_path: Path,
    today: str,
    *,
    dry: bool = True,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> dict:
    """L2 stub 1개 emit.

    Returns:
        {"stub", "l1", "bytes", "action"} — action 은
        `dry-run` / `written` / `unchanged` / `created`.

    `unchanged` 는 **결과 바이트가 완전히 같을 때만** 난다. 같은 날 두 번
    돌려도 write 가 없다 — 진단 실행이 저장소를 바꾸지 않게 하는 최소 보장이다.
    """
    p = L2_STUBS[name]
    body = build_stub_body(name, l1_path, today, max_chars=max_chars)
    existing_text = p.read_text(encoding="utf-8") if p.exists() else None
    existing_fm = _split_frontmatter(existing_text) if existing_text is not None else None
    new_text = _frontmatter(name, today, existing_fm) + "\n" + body

    result = {"stub": name, "l1": _rel_to_repo(l1_path), "bytes": len(body)}
    if dry:
        result["action"] = "dry-run"
        return result
    if existing_text == new_text:
        result["action"] = "unchanged"
        return result
    p.parent.mkdir(parents=True, exist_ok=True)
    if atomic_write_text is not None:
        atomic_write_text(p, new_text)
    else:
        p.write_text(new_text, encoding="utf-8")
    result["action"] = "created" if existing_text is None else "written"
    return result


def emit_l2_stubs(
    *, dry: bool = True, max_chars: int = DEFAULT_MAX_CHARS, today: str | None = None
) -> dict:
    """L2 stub 4종 전부 emit. L1 이 없는 stub 은 건너뛰고 밝힌다."""
    today = today or datetime.now().strftime("%Y-%m-%d")
    sources = l1_sources()
    emitted: list[dict] = []
    missing: list[str] = []
    for name in L2_STUBS:
        l1 = sources.get(name)
        if l1 is None:
            missing.append(name)
            continue
        emitted.append(emit_stub(name, l1, today, dry=dry, max_chars=max_chars))
    return {
        "mode": "dry-run" if dry else "applied",
        "today": today,
        "emitted": emitted,
        "missing_l1": missing,
    }


# ---------------------------------------------------------------------------
# CLI main
# ---------------------------------------------------------------------------

#: `--refresh-raw` 은퇴 사유. rc 는 0 이지만 **아무것도 쓰지 않는다** — 왜
#: 안 쓰는지 stderr 로 말한다 (조용한 no-op 은 이 저장소가 금지한다).
REFRESH_RAW_RETIRED_MESSAGE = (
    "[RETIRED] --refresh-raw 는 아무것도 쓰지 않는다 (TASK-2026-08-18-main-004).\n"
    "  · state.json  — 정본 §11.2 의 **생성 산출물**. 생성기는 `wk refresh-state` 하나다.\n"
    "  · work_backlog.md — v0.14.0 append-only layout 에서 제거됨 (backlog/<날짜>.md 로 대체).\n"
    "  · memory/log.md — 이전 구현이 entry 를 만들고 쓰지 않던 죽은 경로.\n"
    "  · wiki/log.md — 이전 구현이 2026-06 스냅샷을 하드코딩해 실행할수록 되돌렸다.\n"
    "  L1 갱신은 `wk refresh-state` 와 backlog/handoff 도구가 담당한다. "
    "본 tool 은 L2 파생 뷰(--emit-l2)만 만든다."
)


def cmd_refresh_raw(args) -> dict:
    """은퇴한 raw mirror 갱신 단계. write 0, 사유를 stderr 로 보고."""
    print(REFRESH_RAW_RETIRED_MESSAGE, file=sys.stderr)
    return {
        "mode": "retired",
        "writes": 0,
        "reason": "L1 raw mirror write 경로 은퇴 — state.json 은 wk refresh-state 가 유일한 생성기",
    }


def cmd_emit_l2(args) -> dict:
    """L2 stub 4종을 현재 memory SSOT 에서 파생 (subcommand --emit-l2)."""
    return emit_l2_stubs(dry=args.dry_run, max_chars=args.max_chars)


def main() -> int:
    p = argparse.ArgumentParser(
        description="in-repo wiki L2 파생 뷰 emit tool (v1.2.2+)",
    )
    p.add_argument("--refresh-raw", action="store_true",
                   help="[은퇴] L1 raw mirror 갱신 — write 0, 사유만 보고한다")
    p.add_argument("--emit-l2", action="store_true",
                   help="L2 stub 4종을 현재 memory SSOT 에서 파생 "
                        "(active-state / active-work-backlog / active-session-handoff / wiki-log)")
    p.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS,
                   help=f"L2 본문 상한 (default: {DEFAULT_MAX_CHARS})")
    p.add_argument("--since", default=None,
                   help="[은퇴] git log 기준일 — 파생이 git log 를 쓰지 않으므로 무시된다")
    p.add_argument("--repo-root", default=None,
                   help="git repo 경로 (default: auto-detect via $STANDARD_AI_WF_REPO or `git rev-parse --show-toplevel`)")
    p.add_argument("--dry-run", action="store_true",
                   help="갱신 없이 plan 만 출력 (default: --apply)")
    p.add_argument("--apply", dest="apply", action="store_true", default=True,
                   help="갱신 적용 (default)")
    p.add_argument("--json", action="store_true",
                   help="JSON 출력 (CI 통합)")
    args = p.parse_args()

    if not (args.refresh_raw or args.emit_l2):
        p.error("--refresh-raw 또는 --emit-l2 중 1개 이상 지정")

    if args.dry_run:
        args.apply = False

    if args.since is not None:
        print(
            "[IGNORED] --since 는 무시된다 — L2 파생은 git log 가 아니라 "
            "memory SSOT 파일에서 나온다.",
            file=sys.stderr,
        )

    # REPO_ROOT 결정 (CLI flag > env var > git rev-parse > legacy fallback)
    resolved_repo_root = get_repo_root(args.repo_root)
    args.repo_root = resolved_repo_root

    result: dict = {
        "dry_run": args.dry_run,
        "repo_root": str(resolved_repo_root),
    }
    if args.refresh_raw:
        result["refresh_raw"] = cmd_refresh_raw(args)
    if args.emit_l2:
        result["emit_l2"] = cmd_emit_l2(args)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"=== {'DRY-RUN' if args.dry_run else 'APPLY'} mode ===")
        print(f"repo_root: {resolved_repo_root}")
        emit = result.get("emit_l2")
        if emit:
            for row in emit["emitted"]:
                print(f"  [{row['action']}] {row['stub']:<24} ← {row['l1']} ({row['bytes']}B)")
            for name in emit["missing_l1"]:
                print(f"  [skip] {name:<24} ← L1 SSOT 부재")
    return 0


if __name__ == "__main__":
    sys.exit(main())
