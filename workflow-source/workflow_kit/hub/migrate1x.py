"""1.x 전환 — 감지 · 전환 계획 · 들여오기 (hub_spec §6.6, 요구 R14.1 ~ R14.5 · R14.9 · Q1 · Q2 · I1).

허브는 저장소를 읽지 않는다 (원격 MCP). 감지는 **에이전트가 돌린 명령의 결과**를 허브가 판정하는 것이고
(:data:`COMMANDS`), 들여오기는 계획이 고른 파일을 에이전트가 읽어 묶음으로 싣는 것이다. 원본 파일은
건드리지 않는다 — 허브는 쓰기 지시도 내지 않는다 ('허브로 옮김' 표식은 WBS-38.2).

판정은 1.x 함수 그대로다: task 칸은 ``read_task_list_field`` · ``read_task_affected_documents`` ·
``plan_claims`` 의 라벨, handoff 는 ``HandoffParser``, 진입 파일의 kit 생성 절은 ``entry_diet`` 의
'알려진 생성물' 해시. 허브가 자기 사본을 들면 1.x 와 갈라진다.
"""

from __future__ import annotations

import json
import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from workflow_kit.common.entry_diet import is_known_generated, split_sections
from workflow_kit.common.hub_marker import MARKER_REL
from workflow_kit.common.paths import HANDOFF_FILENAME
from workflow_kit.common.project_docs import HandoffParser, task_label, task_label_aliases
from workflow_kit.common.workflow_writes import read_task_affected_documents, read_task_list_field
from workflow_kit.hub.errors import HubError, forbidden, invalid_field, not_found
from workflow_kit.hub import render
from workflow_kit.hub.guide import Guides
from workflow_kit.hub.judge import Judge
from workflow_kit.hub.memory import Memory
from workflow_kit.hub.store import STATUSES, Ctx, Principal, Store, _iso, _json, scan_secrets
from workflow_kit.hub.wiki import Wiki

ACTIVE = "ai-workflow/memory/active/"
WIKI_ROOT = "ai-workflow/wiki/"
ENTRY_FILES = ("CLAUDE.md", "AGENTS.md", "MiniMax.md", "ANTIGRAVITY.md", "GEMINI.md")
#: 하네스 설정 흔적 → 하네스. 지원 4종 밖은 '2.0 지원 대상 아님' (R14.9).
HARNESS_TRACES: dict[str, str] = {
    ".claude-plugin/": "claude-code", ".claude/": "claude-code", ".mcp.json": "claude-code",
    ".codex/": "codex", ".minimax/": "minimax-code", ".agents/": "antigravity",
    ".grok/": "grok-build", ".opencode/": "opencode", "opencode.json": "opencode", ".pi/": "pi-dev",
}
SUPPORTED = ("claude-code", "codex", "minimax-code", "antigravity")
KINDS = ("tasks", "archive", "handoff", "roadmap", "wiki", "memory_index", "checkpoint", "guide_draft")
_TRACE_PATHS = sorted({p.rstrip("/") for p in HARNESS_TRACES})

#: 에이전트가 저장소 뿌리에서 돌리는 명령 (읽기만). 결과는 ``{이름: {rc, output}}``.
COMMANDS: dict[str, list[str]] = {
    "branch": ["git", "rev-parse", "--abbrev-ref", "HEAD"],
    "default": ["git", "rev-parse", "--abbrev-ref", "origin/HEAD"],
    "head": ["git", "rev-parse", "HEAD"],
    "ls_tracked": ["git", "ls-files", "--", "ai-workflow", *ENTRY_FILES, *_TRACE_PATHS],
    "ls_ignored": ["git", "ls-files", "--others", "--ignored", "--exclude-standard", "--", "ai-workflow/memory/active"],
    "times": ["git", "log", "--format=@%ct %H", "--name-only", "--", "ai-workflow/memory/active"],
    "kit_marker": ["git", "grep", "-n", "-e", "standard-ai-workflow-kit:", "--", *ENTRY_FILES],
    # 커밋 안 된 · 추적 안 된 파일 — 감지는 추적 파일만 보므로 이것들은 계획에 없다 (경고로 알린다).
    "dirty": ["git", "status", "--porcelain", "--untracked-files=all", "--", "ai-workflow", *ENTRY_FILES],
}

#: 계획이 들이지 않고 저장소에 남기는 파일의 사유 (R14.2 '무엇을 남기는지'). 위에서부터 첫 일치.
LEFT_REASONS: tuple[tuple[str, str], ...] = (
    (r"(^|/)state\.json(\.template)?$|/roadmap_state\.json$", "생성물 — 허브가 다시 만든다"),
    (r"^ai-workflow/memory/archived/", "아카이브된 브랜치 기록 — 이 전환은 활성 네임스페이스만 들인다"),
    (r"^ai-workflow/memory/active/.+/backlog/\d{4}-\d{2}-\d{2}\.md$", "날짜별 backlog — task 파일이 정본이고 이것은 파생 목록"),
    (r"/baselines\.md$", "기준선 이관 기록 — 이 전환이 다루지 않는다"),
    (r"/plan_responses/", "결정 응답 보관 — 이 전환이 다루지 않는다 (결정 상태는 task 계획 줄에 있다)"),
    (r"(^|/)\.gitkeep$|(^|/)\.frozen$|\.bak$", "자리 표시 · 백업 파일"),
    (r"^ai-workflow/memory/active/(PURPOSE|PROJECT_PROFILE)\.md$", "프로젝트 문서 — 허브에 자리가 없다 (저장소에 남는다)"),
    (r"^ai-workflow/memory/(archive|release|plans)/|^ai-workflow/memory/log\.md$", "옛 스냅숏 · 발행 기록 — 저장소에 남는다"),
    (r"^ai-workflow/wiki/", "위키의 페이지가 아닌 파일"),
    (r"^ai-workflow/memory/active/memory_index/", "memory_index 의 entry 가 아닌 파일"),
)

_KIT_MARKER = re.compile(r"standard-ai-workflow-kit:\s*v?([0-9][0-9A-Za-z.+-]*)")
#: task 파일 이름의 ID 는 정규식으로 거르지 않는다 — 옛 ID(``TASK-021``)도 감지에서 빠지면 안 된다. 판정은 파서가 한다.
_TASK_FILE = re.compile(r"^(?P<ns>.+?)/backlog/tasks/(?P<id>[^/]+)\.md$")  # 이름이 TASK- 로 시작하는지는 아래에서
_ARCHIVE_FILE = re.compile(rf"^(?P<ns>.+?)/(?:{re.escape(HANDOFF_FILENAME)}|lessons\.md|sessions/.+\.md)$")
_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_HEADER = re.compile(r"^#\s+(\S+)\s+[—-]\s+(.+)$", re.M)  # ID 는 frontmatter 의 것과 같은지로만 본다
_SPECIAL_TOP = ("roadmap/", "memory_index/")


def _out(results: dict[str, Any], name: str) -> tuple[int, str] | None:
    r = results.get(name)
    if not isinstance(r, dict) or "rc" not in r:
        return None
    return int(r["rc"]), str(r.get("output", ""))


def _lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def parse_times(output: str) -> dict[str, tuple[int, str]]:
    """``git log --format=@%ct %H --name-only`` → 경로별 **마지막** 커밋 (시각, sha). 첫 등장이 최신이다."""
    out: dict[str, tuple[int, str]] = {}
    current: tuple[int, str] | None = None
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("@"):
            ct, _, sha = line[1:].partition(" ")
            current = (int(ct), sha) if ct.isdigit() else None
        elif current is not None and line not in out:
            out[line] = current
    return out


# --------------------------------------------------------------------------- task 파일 (1.x 형식)


def _first(lines: list[str], key: str) -> str:
    vals = read_task_list_field(lines, task_label(key))
    return vals[0] if vals else ""


def _section(text: str, marker: str) -> str:
    """``## <marker…>`` 절의 원문 (제목 줄 빼고, 앞뒤 빈 줄 걷음)."""
    m = re.search(rf"^## [^\n]*{re.escape(marker)}[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1).strip("\n") + "\n" if m and m.group(1).strip() else ""


def parse_task_file(text: str) -> dict[str, Any]:
    """1.x task 파일 → 허브 task 칸. 못 읽으면 ``invalid_field`` (미분류로 보고한다 — 조용히 버리지 않는다)."""
    fm = _FRONTMATTER.match(text)
    if not fm:
        raise invalid_field("task", "frontmatter 가 없다")
    meta = dict(re.findall(r"^(\w+):\s*(.*?)\s*$", fm.group(1), re.M))
    task_id = meta.get("id", "")
    if not task_id.startswith("TASK-"):
        raise invalid_field("task", "frontmatter 에 id 가 없다")
    lines = text.splitlines()
    header = next((m for m in _HEADER.finditer(text) if m.group(1) == task_id), None)
    title = header.group(2).strip() if header else task_id
    status = meta.get("status") or _first(lines, "status")
    if status not in STATUSES:
        raise invalid_field("status", f"1.x 상태가 네 값 밖이다: {status!r}")
    priority = _first(lines, "priority") or "medium"
    plan_md = _section(text, "🧭 Plan") or _section(text, "Plan")
    fields: dict[str, Any] = {
        "affected_documents": read_task_affected_documents(lines),
        "done_criteria": read_task_list_field(lines, task_label("done_criteria")),
        "risks": read_task_list_field(lines, task_label("risks")),
        "follow_up": read_task_list_field(lines, task_label("follow_up")),
    }
    for key, label in (("result", "result"), ("validation_result", "validation"), ("next_step", "next_step")):
        vals = read_task_list_field(lines, task_label(label))
        if vals:
            fields[key] = "\n".join(vals)
    progress = read_task_list_field(lines, task_label("progress"))
    return {
        "id": task_id, "title": title[:200], "status": status,
        "priority": priority if priority in ("high", "medium", "low") else "medium",
        "wbs": meta.get("wbs", ""), "wbs_exempt_reason": meta.get("wbs_exempt_reason", ""),
        "description": "\n".join(read_task_list_field(lines, task_label("summary"))),
        "plan_md": plan_md, "fields": {k: v for k, v in fields.items() if v},
        "progress_note": progress[-1] if progress else "",
        "created_at": meta.get("created_at", ""),
    }


# --------------------------------------------------------------------------- handoff · 진입 파일


_NEXT_HEADS = ("다음 세션 시작 포인트", "Next session")
_RISK_HEADS = ("남은 리스크", "Remaining risks")


def _bullets(text: str, heads: tuple[str, ...]) -> list[str]:
    for head in heads:
        body = _section(text, head)
        if body:
            return [ln.strip()[2:].strip() for ln in body.splitlines()
                    if ln.strip().startswith("- ") and ln.strip()[2:].strip() not in ("", "-")]
    return []


def parse_handoff(text: str) -> tuple[dict[str, Any], list[str]]:
    """1.x handoff → 허브 handoff 칸 (R14.4). (칸, 버린 줄) — 진행 · 막힘 · 최근 완료는 ``TASK-`` 줄만 (R6.2)."""
    # 저장소 경로가 아니라 파서에 넘길 임시 사본이다 — 이름은 아무래도 좋다 (HandoffParser 가 파일을 받는다).
    with tempfile.TemporaryDirectory() as td:
        copy = Path(td) / "handoff-copy.md"
        copy.write_text(text, encoding="utf-8")
        data = HandoffParser(copy).parse()
    dropped: list[str] = []

    def tasks(key: str) -> list[str]:
        out = []
        raw = data.get(key)
        for item in raw if isinstance(raw, list) else []:
            s = str(item).strip()
            if s.startswith("TASK-"):
                out.append(s)
            elif s not in ("", "-"):
                dropped.append(s)
        return out

    return {
        "baseline": str(data.get("current_baseline") or ""),
        "focus": str(data.get("current_axis") or ""),
        "in_progress": tasks("in_progress_items"),
        "blocked": tasks("blocked_items"),
        "recent_done": tasks("recent_done_items"),
        "next": _bullets(text, _NEXT_HEADS),
        "risks": _bullets(text, _RISK_HEADS),
    }, dropped


_KIT_LINE = re.compile(r"^<!-- (?:standard-ai-workflow-kit[^>]*|generated-from:[^>]*) -->$")
_HUB_REGION = re.compile(r"<!-- workflow-hub:begin .*?<!-- workflow-hub:end -->\n?", re.S)


def hand_written(text: str) -> tuple[str, list[str]]:
    """진입 파일에서 kit 생성 절을 걷고 손 문단만 (R14.5). (손 문단, 걷은 절 제목)."""
    text = _HUB_REGION.sub("", text)
    head, sections = split_sections(text)
    dropped: list[str] = []
    kept: list[str] = []
    head_lines = [ln for ln in head.split("\n") if not _KIT_LINE.match(ln.strip())]
    head_text = "\n".join(ln for ln in head_lines if not ln.startswith("# ")).strip()
    if head_text and not head_text.startswith("- 문서 목적"):
        kept.append(head_text)
    for title, body in sections:
        if is_known_generated(title, body) or "<!-- generated-from:" in body:
            dropped.append(title)
            continue
        clean = "\n".join(ln for ln in body.split("\n") if not _KIT_LINE.match(ln.strip())).strip()
        if clean:
            kept.append(f"## {title}\n\n{clean}")
    return ("\n\n".join(kept) + "\n") if kept else "", dropped


# --------------------------------------------------------------------------- 계획 · 들여오기


class Migrator:
    def __init__(self, store: Store) -> None:
        self.store = store

    @staticmethod
    def _owner(ctx: Ctx) -> Principal:
        p = ctx.principal
        if p is None or p.kind != "callsign" or p.role != "owner" or p.callsign_kind != "human" or not p.human_approved:
            raise forbidden("1.x 전환은 프로젝트 소유자(승인된 human)가 한다 (R14.2 — 등록자가 확인한 것만 들인다)")
        return p

    def plan(self, ctx: Ctx, scan: dict[str, Any] | None) -> dict[str, Any]:
        """인자 없이 → 돌릴 명령. ``scan`` 을 실어 → 감지 보고 · 전환 계획 (계획은 ``MIG-NNNN`` 으로 남는다)."""
        p = self._owner(ctx)
        if scan is None:
            return {"phase": 1, "commands": COMMANDS,
                    "rules": ["저장소 뿌리에서 그대로 돌리고 {name: {rc, output}} 로 scan 에 싣는다",
                              "명령을 고치거나 건너뛰지 않는다 — 못 돌린 명령은 싣지 않는다 (미확인으로 남는다)"],
                    "next": "hub_migrate_plan(scan=…)"}
        if not isinstance(scan, dict):
            raise invalid_field("scan", "{name: {rc, output}}")
        unknown = set(scan) - set(COMMANDS)
        if unknown:
            raise invalid_field("scan", f"요청하지 않은 명령 결과: {', '.join(sorted(unknown))}")
        unmeasured = [n for n in COMMANDS if _out(scan, n) is None]
        ls = _out(scan, "ls_tracked")
        if ls is None or ls[0] != 0:
            raise invalid_field("scan.ls_tracked", "git ls-files 결과가 필요하다 (rc 0)")
        tracked = _lines(ls[1])
        ignored = _lines((_out(scan, "ls_ignored") or (1, ""))[1])
        times = parse_times((_out(scan, "times") or (1, ""))[1])
        branch = (_out(scan, "branch") or (1, ""))[1].strip()
        default = (_out(scan, "default") or (1, ""))[1].strip().removeprefix("origin/")
        head = (_out(scan, "head") or (1, ""))[1].strip()
        kit_versions = sorted({m.group(1) for m in _KIT_MARKER.finditer((_out(scan, "kit_marker") or (1, ""))[1])})

        tasks: dict[str, list[dict[str, Any]]] = {}
        archive: list[dict[str, Any]] = []
        namespaces: set[str] = set()
        roadmap, wiki, memidx, entries, traces = [], [], [], [], []
        for path in tracked:
            if path.startswith(ACTIVE):
                rest = path[len(ACTIVE):]
                if rest.startswith("roadmap/") and rest.endswith(".md") and rest.count("/") == 1:
                    roadmap.append(path)
                    continue
                if rest.startswith("memory_index/entries/") and rest.endswith(".json"):
                    memidx.append(path)
                    continue
                if rest.startswith(_SPECIAL_TOP):
                    continue
                m = _TASK_FILE.match(rest)
                if m and m.group("id").startswith("TASK-"):
                    namespaces.add(m.group("ns"))
                    ct, sha = times.get(path, (0, ""))
                    tasks.setdefault(m.group("id"), []).append(
                        {"namespace": m.group("ns"), "path": path, "committed_at": ct, "commit": sha})
                    continue
                m = _ARCHIVE_FILE.match(rest)
                if m:
                    namespaces.add(m.group("ns"))
                    ct, sha = times.get(path, (0, ""))
                    archive.append({"namespace": m.group("ns"), "path": path, "commit": sha, "committed_at": ct})
            elif path.startswith(WIKI_ROOT) and path.endswith(".md"):
                wiki.append(path)
            elif path in ENTRY_FILES:
                entries.append(path)
            else:
                for prefix, harness in HARNESS_TRACES.items():
                    if path == prefix or path.startswith(prefix):
                        traces.append({"path": path, "harness": harness})
                        break
        covered_now = set(sorted(c["path"] for cands in tasks.values() for c in cands)) | {a["path"] for a in archive} \
            | set(roadmap) | set(wiki) | set(memidx) | set(entries)
        left: dict[str, list[str]] = {}
        for path in tracked:
            if path in covered_now or not path.startswith("ai-workflow/"):
                continue
            if path.endswith("/session_handoff.md") or path.endswith(".compact/checkpoint.json"):
                continue
            reason = next((why for pat, why in LEFT_REASONS if re.search(pat, path)), "이 전환이 다루지 않는다 — 저장소에 남는다")
            left.setdefault(reason, []).append(path)
        dirty = [ln[3:].strip() for ln in (_out(scan, "dirty") or (1, ""))[1].splitlines() if len(ln) > 3]
        current_ns = branch if branch in namespaces else (default if default in namespaces else "")
        checkpoint = f"{ACTIVE}{current_ns}/.compact/checkpoint.json" if current_ns else ""
        if checkpoint not in ignored and checkpoint not in tracked:
            checkpoint = ""

        canonical: dict[str, dict[str, Any]] = {}
        conflicts = []
        for task_id, cands in sorted(tasks.items()):
            ranked = sorted(cands, key=lambda c: (-c["committed_at"], c["namespace"] != default, c["namespace"]))
            win = ranked[0]
            if len(cands) > 1:
                second = ranked[1]
                if win["committed_at"] > second["committed_at"]:
                    reason = "마지막 커밋 시각이 가장 늦다"
                elif win["namespace"] == default:
                    reason = "커밋 시각이 같아 기본 브랜치"
                else:
                    reason = "커밋 시각이 같고 기본 브랜치가 없어 이름순"
                win_with_reason: dict[str, Any] = {**win, "reason": reason}
                conflicts.append({"task_id": task_id, "canonical": win_with_reason,
                                  "variants": ranked[1:]})
            canonical[task_id] = win
        harnesses = sorted({t["harness"] for t in traces} | {
            {"CLAUDE.md": "claude-code", "AGENTS.md": "codex", "MiniMax.md": "minimax-code",
             "ANTIGRAVITY.md": "antigravity", "GEMINI.md": "antigravity"}[e] for e in entries})
        files: dict[str, list[str]] = {
            "tasks": sorted(c["path"] for cands in tasks.values() for c in cands),
            "archive": sorted(a["path"] for a in archive),
            "handoff": [f"{ACTIVE}{current_ns}/{HANDOFF_FILENAME}"]
            if current_ns and f"{ACTIVE}{current_ns}/{HANDOFF_FILENAME}" in tracked else [],
            "roadmap": sorted(roadmap), "wiki": sorted(wiki), "memory_index": sorted(memidx),
            "checkpoint": [checkpoint] if checkpoint else [], "guide_draft": sorted(entries),
        }
        detected: dict[str, Any] = {
            "namespaces": sorted(namespaces), "current_namespace": current_ns, "branch": branch,
            "default_branch": default, "head": head, "kit_versions": kit_versions,
            "counts": {k: len(v) for k, v in files.items()}, "task_ids": len(tasks),
            "entry_files": sorted(entries), "harness_traces": traces,
            "unsupported_harnesses": [h for h in harnesses if h not in SUPPORTED],
            "unmeasured": unmeasured,
            "left_in_repo": {why: {"files": len(paths), "sample": paths[:3]} for why, paths in sorted(left.items())},
            "left_in_repo_total": sum(len(v) for v in left.values()),
            "uncommitted": dirty,
        }
        guidance = ([f"커밋 안 된 파일 {len(dirty)}개는 계획에 없다 — 커밋한 뒤 계획을 다시 낸다: {', '.join(dirty[:5])}"]
                    if dirty else []) + [
            f"{h}: 2.0 지원 대상 아님 — 1.x 줄에 남거나 원격 MCP 를 손으로 등록한다 (R14.9)"
            for h in detected["unsupported_harnesses"]
        ] + [
            f"{t['path']}: kit 플러그인 · hook · stdio MCP 설정 — 허브 MCP 로 바꾼 뒤 지운다. 지우는 것은 소유자 확인 뒤 (I4)"
            for t in traces if t["harness"] in SUPPORTED
        ]
        plan = {"detected": detected, "files": files, "conflicts": conflicts,
                "canonical": {k: v["path"] for k, v in canonical.items()},
                "times": {p: list(v) for p, v in times.items() if p in set(files["tasks"]) | set(files["archive"])},
                "guidance": guidance}
        scan_secrets(plan, "plan")
        with self.store.write() as conn:
            n = conn.execute("SELECT COUNT(*) AS n FROM migration_1x WHERE project_id = ?", (p.project_id,)).fetchone()["n"] + 1
            mig = f"MIG-{n:04d}"
            conn.execute("INSERT INTO migration_1x (project_id, id, at, callsign, status, plan_json) VALUES (?, ?, ?, ?, 'planned', ?)",
                         (p.project_id, mig, _iso(ctx.now), p.callsign, _json(plan)))
            self.store._event(conn, ctx, p.project_id, "migration_1x", mig, "plan", None, detected["counts"])
        return {"phase": 2, "migration_id": mig, **plan,
                "table": [{"kind": k, "files": len(v), "default": True} for k, v in files.items()],
                "next": "고를 종류(kinds)를 소유자에게 확인한 뒤 hub_migrate_import(migration_id, kinds, files=[{path, content}]) — "
                        "요청 상한(256KB) 안으로 나눠 보내고 마지막에 final=true. 원본 파일은 지우지 않는다"}

    def _load(self, conn: sqlite3.Connection, pid: str, mig: str) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM migration_1x WHERE project_id = ? AND id = ?", (pid, mig)).fetchone()
        if row is None:
            raise not_found(f"전환 계획이 없다: {mig}")
        found: sqlite3.Row = row
        return found

    def report(self, ctx: Ctx, mig: str) -> dict[str, Any]:
        p = self.store._need_reader(ctx)
        with self.store.read() as conn:
            row = self._load(conn, p.project_id or "", mig)
        return {"migration_id": mig, "status": row["status"], "at": row["at"], "callsign": row["callsign"],
                "plan": json.loads(row["plan_json"]), "report": json.loads(row["report_json"])}

    def import_batch(self, ctx: Ctx, mig: str, kinds: list[str], files: list[Any], final: bool = False) -> dict[str, Any]:
        """고른 종류의 파일 묶음을 들인다 (R14.2). 계획에 없는 경로 · 고르지 않은 종류의 파일은 거절."""
        p = self._owner(ctx)
        pid = p.project_id or ""
        bad = [k for k in kinds if k not in KINDS]
        if not kinds or bad:
            raise invalid_field("kinds", f"{' · '.join(KINDS)} 가운데 하나 이상 — 모르는 값: {bad}")
        with self.store.read() as conn:
            row = self._load(conn, pid, mig)
        if row["status"] == "done":
            raise HubError(409, "already_done", f"{mig} 는 이미 끝난 전환이다")
        plan = json.loads(row["plan_json"])
        report: dict[str, Any] = json.loads(row["report_json"]) or {}
        # 한 파일이 여러 종류에 속할 수 있다 — 현재 브랜치 handoff 는 보관(원문)이자 콜사인 handoff 의 출처다.
        kinds_of: dict[str, set[str]] = {}
        for kind, paths in plan["files"].items():
            for path in paths:
                kinds_of.setdefault(path, set()).add(kind)
        by_kind: dict[str, list[tuple[str, str]]] = {}
        for i, f in enumerate(files or []):
            if not isinstance(f, dict) or not isinstance(f.get("path"), str) or not isinstance(f.get("content"), str):
                raise invalid_field(f"files[{i}]", "{path, content}")
            owners = kinds_of.get(f["path"])
            if owners is None:
                raise invalid_field(f"files[{i}].path", f"전환 계획에 없는 경로: {f['path']}")
            chosen = owners & set(kinds)
            if not chosen:
                raise invalid_field(f"files[{i}].path", f"고르지 않은 종류({', '.join(sorted(owners))})의 파일")
            for kind in chosen:
                by_kind.setdefault(kind, []).append((f["path"], f["content"]))

        batch: dict[str, dict[str, list[Any]]] = {}

        def add(kind: str, key: str, item: Any) -> None:
            batch.setdefault(kind, {}).setdefault(key, []).append(item)

        for kind in KINDS:
            if kind == "wiki" and by_kind.get(kind):
                try:
                    self._import_wiki_batch(ctx, p, by_kind[kind], add)
                except HubError as e:
                    for path, _ in by_kind[kind]:
                        add(kind, "failed", {"path": path, "error_code": e.code, "message": e.message})
                continue
            for path, content in by_kind.get(kind, []):
                try:
                    getattr(self, f"_import_{kind}")(ctx, p, plan, path, content, add)
                except HubError as e:
                    add(kind, "failed", {"path": path, "error_code": e.code, "message": e.message})
        for kind, groups in batch.items():  # 누적 기록 — 응답은 이번 묶음만 센다
            for key, items in groups.items():
                report.setdefault(kind, {}).setdefault(key, []).extend(items)
        report["kinds"] = sorted(set(report.get("kinds", [])) | set(kinds))
        if final:
            report["done_at"] = _iso(ctx.now)
        status = "done" if final else "importing"
        with self.store.write() as conn:
            conn.execute("UPDATE migration_1x SET status = ?, report_json = ? WHERE project_id = ? AND id = ?",
                         (status, _json(report), pid, mig))
            if final:
                self.store._event(conn, ctx, pid, "migration_1x", mig, "done", None,
                                  {k: {kk: len(vv) for kk, vv in v.items()} for k, v in report.items() if isinstance(v, dict)})
        summary = {k: {kk: len(vv) for kk, vv in v.items()} for k, v in batch.items()}
        total = {k: {kk: len(vv) for kk, vv in v.items()} for k, v in report.items() if isinstance(v, dict)}
        return {"migration_id": mig, "status": status, "summary": summary, "total": total,
                "next": "끝났다 — 원본은 그대로다. hub_migrate_marker(migration_id, action='issue') 로 '허브로 옮김' 표식을 남긴다" if final
                else "남은 파일을 이어 보내고 마지막에 final=true"}

    # --- '허브로 옮김' 표식 (R14.6 · R14.7 · DS9) ---------------------------------------------

    def marker(self, ctx: Ctx, mig: str, action: str, sha256: str | None = None,
               check: dict[str, Any] | None = None) -> dict[str, Any]:
        """표식 쓰기 지시 · 확인 · 되돌리기. 허브는 저장소에 쓰지 않는다 — 지시를 내고 결과를 대조한다."""
        p = self._owner(ctx)
        pid = p.project_id or ""
        if action not in MARKER_ACTIONS:
            raise invalid_field("action", " · ".join(MARKER_ACTIONS))
        with self.store.read() as conn:
            row = self._load(conn, pid, mig)
        if row["status"] != "done":
            raise HubError(409, "migration_not_done", f"{mig} 가 아직 끝나지 않았다 — 마지막 묶음을 final=true 로 보낸 뒤에 표식을 남긴다")
        plan, report = json.loads(row["plan_json"]), json.loads(row["report_json"])
        state: dict[str, Any] = report.get("marker") or {}
        content = marker_content(ctx.public_url, pid, mig, report.get("done_at") or row["at"],
                                 plan["detected"].get("kit_versions", []))
        expected = render.sha256(content)
        out: dict[str, Any] = {"migration_id": mig, "action": action, "path": MARKER_PATH}
        if action == "issue":
            state = {**state, "issued_at": state.get("issued_at") or _iso(ctx.now), "sha256": expected}
            out.update({"steps": [
                {"id": "marker", "op": "write", "path": MARKER_PATH, "content": content, "sha256_after": expected},
                {"id": "commit", "op": "run", "run": ["git", "add", "--", MARKER_PATH],
                 "then": ["git", "commit", "-m", f"chore: 워크플로우 허브로 옮김 ({mig})", "--", MARKER_PATH]},
            ], "next": "파일을 쓰고 커밋한 뒤 hub_migrate_marker(action='confirm', sha256=<쓴 파일의 sha256>)"})
        elif action == "confirm":
            if not isinstance(sha256, str) or not sha256:
                raise invalid_field("sha256", "쓴 파일의 sha256")
            ok = sha256 == expected
            if ok:
                state = {**state, "confirmed_at": _iso(ctx.now), "reverted_at": None}
            out.update({"confirmed": ok, "reason": "" if ok else f"sha256 이 지시와 다르다 (지시 {expected[:12]}…, 받음 {sha256[:12]}…)"})
        elif action == "revert":
            state = {**state, "revert_issued_at": _iso(ctx.now)}
            out.update({"steps": [
                {"id": "marker", "op": "delete", "path": MARKER_PATH},
                {"id": "check", "op": "run_and_report", "run": ["git", "ls-files", "--", MARKER_PATH], "expect": "empty"},
            ], "warning": REVERT_WARNING,
                "next": "파일을 지우고 커밋한 뒤 확인 명령의 결과를 hub_migrate_marker(action='confirm_revert', check={rc, output})"})
        else:  # confirm_revert
            if not isinstance(check, dict) or "rc" not in check:
                raise invalid_field("check", "{rc, output} — git ls-files 결과")
            ok = int(check["rc"]) == 0 and not str(check.get("output", "")).strip()
            if ok:
                state = {**state, "reverted_at": _iso(ctx.now), "confirmed_at": None}
            out.update({"reverted": ok, "warning": REVERT_WARNING,
                        "reason": "" if ok else "표식이 아직 추적된다 (지우고 커밋했는지 본다)"})
        report["marker"] = state
        with self.store.write() as conn:
            conn.execute("UPDATE migration_1x SET report_json = ? WHERE project_id = ? AND id = ?", (_json(report), pid, mig))
            self.store._event(conn, ctx, pid, "migration_1x", mig, f"marker_{action}", None,
                              {k: v for k, v in out.items() if k in ("confirmed", "reverted", "reason")})
        out["marker"] = state
        return out

    # --- 종류별 ---------------------------------------------------------------------

    def _import_tasks(self, ctx: Ctx, p: Principal, plan: dict[str, Any], path: str, content: str, add: Any) -> None:
        t = parse_task_file(content)
        scan_secrets(t, "task")
        pid = p.project_id or ""
        ns = path[len(ACTIVE):].split("/backlog/tasks/")[0]
        ct, sha = plan["times"].get(path, [0, ""])
        if plan["canonical"].get(t["id"]) != path:
            with self.store.write() as conn:
                seen = conn.execute(
                    "SELECT 1 FROM event WHERE project_id = ? AND target_kind = 'task' AND target_id = ? "
                    "AND op = 'imported_variant' AND json_extract(after_json, '$.path') = ?", (pid, t["id"], path)).fetchone()
                if seen:  # 다시 보내도 이력은 한 번 (멱등)
                    add("tasks", "skipped_exists", {"id": t["id"], "path": path, "variant": True})
                    return
                self.store._event(conn, ctx, pid, "task", t["id"], "imported_variant", None,
                                  {"namespace": ns, "path": path, "commit": sha, "committed_at": ct,
                                   "title": t["title"], "status": t["status"], "canonical": plan["canonical"].get(t["id"])})
            add("tasks", "variants", {"id": t["id"], "path": path})
            return
        with self.store.write() as conn:
            if conn.execute("SELECT 1 FROM task WHERE project_id = ? AND id = ?", (pid, t["id"])).fetchone():
                add("tasks", "skipped_exists", {"id": t["id"], "path": path})
                return
            created = f"{t['created_at']}T00:00:00+00:00" if re.match(r"^\d{4}-\d{2}-\d{2}$", t["created_at"]) else _iso(ctx.now)
            conn.execute(
                "INSERT INTO task (project_id, id, title, status, priority, branch, wbs, wbs_exempt_reason, description, "
                "plan_md, fields_json, progress_note, created_by, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (pid, t["id"], t["title"], t["status"], t["priority"], ns, t["wbs"], t["wbs_exempt_reason"],
                 t["description"], t["plan_md"], _json(t["fields"]), t["progress_note"], p.callsign, created, _iso(ctx.now)))
            self.store._event(conn, ctx, pid, "task", t["id"], "import_1x", None,
                              {"namespace": ns, "path": path, "commit": sha, "committed_at": ct})
        add("tasks", "imported", {"id": t["id"], "path": path})

    def _import_archive(self, ctx: Ctx, p: Principal, plan: dict[str, Any], path: str, content: str, add: Any) -> None:
        pid = p.project_id or ""
        rest = path[len(ACTIVE):]
        ns = next(a["namespace"] for a in _archive_rows(plan) if a["path"] == path)
        ct, sha = plan["times"].get(path, [0, ""])
        with self.store.write() as conn:
            dup = conn.execute("SELECT 1 FROM memory_note WHERE project_id = ? AND kind = 'archive_1x' AND title = ?",
                               (pid, path)).fetchone()
            if dup:
                add("archive", "skipped_exists", path)
                return
            conn.execute("INSERT INTO memory_note (project_id, callsign, kind, title, body_md, meta_json, created_at) "
                         "VALUES (?, ?, 'archive_1x', ?, ?, ?, ?)",
                         (pid, p.callsign, path, content,
                          _json({"branch": ns, "path": path, "rel": rest, "commit": sha, "committed_at": ct,
                                 "imported_at": _iso(ctx.now)}), _iso(ctx.now)))
        add("archive", "imported", path)

    def _import_handoff(self, ctx: Ctx, p: Principal, plan: dict[str, Any], path: str, content: str, add: Any) -> None:
        sections, dropped = parse_handoff(content)
        mem = Memory(self.store)
        current = mem.handoff_get(ctx, p.callsign)
        if current["version"]:
            add("handoff", "skipped_exists", {"callsign": p.callsign, "path": path})
            return
        mem.handoff_put(ctx, 0, sections)
        add("handoff", "imported", {"callsign": p.callsign, "path": path, "dropped_lines": dropped})

    def _import_roadmap(self, ctx: Ctx, p: Principal, plan: dict[str, Any], path: str, content: str, add: Any) -> None:
        name = path.rsplit("/", 1)[-1]
        judge = Judge(self.store)
        have = {d["path"] for d in judge.roadmap_get(ctx).get("docs", [])}
        if name in have:
            add("roadmap", "skipped_exists", name)
            return
        judge.roadmap_put(ctx, name, 0, content)
        add("roadmap", "imported", name)

    def _import_wiki_batch(self, ctx: Ctx, p: Principal, items: list[tuple[str, str]], add: Any) -> None:
        """한 묶음 = ingest 하나 (``hub_wiki_import_dir`` 와 같은 함수). 이미 있는 페이지는 건너뛴다 — 다시 보내도 같다."""
        w = Wiki(self.store)
        have = {pg["path"] for pg in w.list_pages(ctx).get("pages", [])}
        send = []
        for path, content in items:
            rel = path[len(WIKI_ROOT):]
            if rel in have:
                add("wiki", "skipped_exists", rel)
            else:
                send.append({"path": rel, "content": content})
        if not send:
            return
        out = w.import_dir(ctx, send, "1.x 전환 — 위키 들여오기")
        for page in out.get("pages", []):
            add("wiki", "imported", page.get("path") if isinstance(page, dict) else page)
        for item in out.get("archived_1x", []):
            add("wiki", "archived_1x", item)

    def _import_memory_index(self, ctx: Ctx, p: Principal, plan: dict[str, Any], path: str, content: str, add: Any) -> None:
        try:
            entry = json.loads(content)
        except json.JSONDecodeError as exc:
            raise invalid_field("memory_index", f"JSON 이 아니다: {exc}") from exc
        w = Wiki(self.store)
        have = {e["id"] for e in w.memory_list(ctx).get("entries", [])}
        if isinstance(entry, dict) and entry.get("id") in have:
            add("memory_index", "skipped_exists", entry.get("id"))
            return
        w.memory_put(ctx, entry, 0)
        add("memory_index", "imported", entry.get("id") if isinstance(entry, dict) else path)

    def _import_checkpoint(self, ctx: Ctx, p: Principal, plan: dict[str, Any], path: str, content: str, add: Any) -> None:
        try:
            body = json.loads(content)
        except json.JSONDecodeError as exc:
            raise invalid_field("checkpoint", f"JSON 이 아니다: {exc}") from exc
        allowed = {"next", "unverified", "verified", "rejected", "tasks", "branch"}
        if not isinstance(body, dict):
            raise invalid_field("checkpoint", "객체")
        Memory(self.store).checkpoint_put(ctx, {k: v for k, v in body.items() if k in allowed})
        add("checkpoint", "imported", {"path": path, "dropped_keys": sorted(set(body) - allowed)})

    def _import_guide_draft(self, ctx: Ctx, p: Principal, plan: dict[str, Any], path: str, content: str, add: Any) -> None:
        """손 문단만 지침 제안 **초안**(open)으로 — 승인된 human 이 올려도 판은 오르지 않는다 (R14.5 · D11)."""
        body, dropped = hand_written(content)
        if not body.strip():
            add("guide_draft", "empty", {"path": path, "dropped_sections": dropped})
            return
        pid = p.project_id or ""
        scan_secrets(body, "guide_draft")
        with self.store.write() as conn:
            current = Guides._current(conn, pid)[0]
            n = conn.execute("SELECT COUNT(*) AS n FROM guide_proposal WHERE project_id = ?", (pid,)).fetchone()["n"] + 1
            prop = f"GP-{n:04d}"
            conn.execute(
                "INSERT INTO guide_proposal (project_id, id, base_version, body_md, note, proposed_by, proposed_at, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'open')",
                (pid, prop, current, body, f"1.x 전환 초안 — {path} 의 손 문단", p.callsign, _iso(ctx.now)))
            self.store._event(conn, ctx, pid, "guide_proposal", prop, "propose", None,
                              {"base_version": current, "source": path, "draft_1x": True})
        add("guide_draft", "proposed", {"path": path, "proposal_id": prop, "dropped_sections": dropped})


MARKER_PATH = MARKER_REL  # 정본은 1.x 쪽 판정 모듈 — 두 쪽이 같은 경로를 본다
MARKER_FORMAT = "workflow-hub-migrated/1"
MARKER_ACTIONS = ("issue", "confirm", "revert", "confirm_revert")
REVERT_WARNING = ("허브 쪽 기록(task · handoff · 위키 …)은 지우지 않는다 — 되돌림에 데이터 이동은 없다 (R14.7). 되돌린 뒤 1.x 에서 "
                  "바뀐 것은 다시 전환해도 '이미 있음' 으로 건너뛴다 — 다시 전환하기 전에 허브 쪽 기록을 어떻게 할지 정한다.")


def marker_content(public_url: str, project_id: str, mig: str, migrated_at: str, from_kit: list[str]) -> str:
    """표식 본문 — 같은 전환이면 언제 내도 같은 바이트 (멱등 · sha256 대조)."""
    from workflow_kit import __version__ as kit

    body = {"format": MARKER_FORMAT, "hub": public_url, "project_id": project_id, "migration_id": mig,
            "migrated_at": migrated_at, "kit_version": kit, "from_kit_versions": from_kit,
            "note": "이 저장소의 워크플로우 정본은 허브다 — 1.x kit 의 쓰기 도구는 이 파일을 보면 거절한다. "
                    "1.x 로 되돌리려면 이 파일만 지운다 (허브 쪽 데이터는 옮기지 않는다)."}
    return json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _archive_rows(plan: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for path in plan["files"].get("archive", []):
        m = _ARCHIVE_FILE.match(path[len(ACTIVE):])
        if m:
            out.append({"path": path, "namespace": m.group("ns")})
    return out


__all__ = ["COMMANDS", "KINDS", "Migrator", "hand_written", "parse_handoff", "parse_task_file", "parse_times",
           "task_label_aliases"]
