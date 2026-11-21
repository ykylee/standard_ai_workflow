"""세션 시작 확인 — 허브와 저장소를 함께 (hub_spec §6.2, 요구 R10 · Q5).

원격 MCP 는 저장소를 볼 수 없다. 그래서 두 번 부른다:

1. ``repo_results`` 없이 → 허브 쪽 결과 + 에이전트가 **그대로** 돌릴 명령 목록
2. ``repo_results`` 와 함께 → 저장소 판정 · 교차 대조 · 확인/미확인 목록

판정 (``verdict``):
    ``stop_and_ask``             — 미커밋 변경 · 갈라짐 (1.x 원칙 '먼저 원격과 동기화')
    ``fast_forward_then_start``  — 뒤처짐만
    ``start``                    — 맞음
    ``unconfirmed``              — 저장소 결과가 없거나 읽을 수 없음 (확인한 척하지 않는다)
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from workflow_kit.hub import render
from workflow_kit.hub.errors import invalid_field
from workflow_kit.hub.setup import CHECK_IGNORE, Setup, check_ignore_ok
from workflow_kit.hub.store import Ctx, Principal

_AB = re.compile(r"^# branch\.ab \+(\d+) -(\d+)$")


def _commands(entry_paths: list[str], shas: list[str]) -> dict[str, list[str]]:
    cmds: dict[str, list[str]] = {
        "fetch": ["git", "fetch", "--prune"],
        "status": ["git", "status", "--porcelain=v2", "--branch"],
        "default_branch": ["git", "rev-parse", "--abbrev-ref", "origin/HEAD"],
        "check_ignore": list(CHECK_IGNORE),
    }
    for path in entry_paths:
        cmds[f"entry_head:{path}"] = ["git", "grep", "--no-index", "-h", "-e", "workflow-hub:begin", "--", path]
    for sha in shas:
        cmds[f"commit:{sha}"] = ["git", "cat-file", "-e", f"{sha}^{{commit}}"]
    return cmds


class SessionStart:
    def __init__(self, setup: Setup) -> None:
        self.setup = setup
        self.store = setup.store

    def _hub_part(self, conn: sqlite3.Connection, p: Principal) -> dict[str, Any]:
        _, _, guide_ver = self.setup.project_guide(conn, p.project_id or "")
        current = render.guide_version(guide_ver)
        cs = conn.execute("SELECT guide_version_seen, setup_complete FROM callsign WHERE project_id = ? AND id = ?",
                          (p.project_id, p.callsign)).fetchone()
        mine = [dict(r) for r in conn.execute(
            "SELECT id, title, status, version, progress_note, progress_at FROM task "
            "WHERE project_id = ? AND assignee = ? AND status != 'done' ORDER BY created_at", (p.project_id, p.callsign))]
        free = [dict(r) for r in conn.execute(
            "SELECT id, title, status FROM task WHERE project_id = ? AND assignee IS NULL AND status != 'done' "
            "ORDER BY created_at LIMIT 50", (p.project_id,))]
        commits: dict[str, list[str]] = {}
        for r in conn.execute(
            "SELECT c.task_id, c.sha FROM task_commit c JOIN task t ON t.project_id = c.project_id AND t.id = c.task_id "
            "WHERE c.project_id = ? AND t.assignee = ? AND t.status != 'done'", (p.project_id, p.callsign)):
            commits.setdefault(r["sha"], []).append(r["task_id"])
        entries = [r["path"] for r in conn.execute(
            "SELECT path FROM setup_step WHERE project_id = ? AND callsign = ? AND kind = 'entry'", (p.project_id, p.callsign))]
        seen = cs["guide_version_seen"] if cs else None
        return {
            "guide": {"current": current, "seen": seen, "changed": seen != current},
            "setup_complete": bool(cs["setup_complete"]) if cs else False,
            "my_tasks": mine,
            "unassigned_open_tasks": free,
            # M-035 · M-036 이 채운다 — 그 전에는 미측정으로 보고한다 (확인한 척하지 않는다)
            "handoff": {"status": "unmeasured", "reason": "handoff 저장은 M-035"},
            "plan_responses": {"status": "unmeasured", "reason": "결정 응답은 M-035"},
            "_entries": sorted(set(entries)),
            "_commits": commits,
        }

    def run(self, ctx: Ctx, repo_results: dict[str, Any] | None) -> dict[str, Any]:
        p = ctx.principal
        assert p is not None and p.project_id is not None
        with self.store.read() as conn:
            hub = self._hub_part(conn, p)
        entries: list[str] = hub.pop("_entries")
        commits: dict[str, list[str]] = hub.pop("_commits")
        commands = _commands(entries, sorted(commits))
        confirmed = ["hub: 닿음", "hub: 지침 판", "hub: 내 task", "hub: 맡은 이 없는 열린 task"]
        unconfirmed = ["hub: handoff (M-035)", "hub: 결정 응답 (M-035)"]
        if hub["guide"]["changed"]:
            hub["guide"]["notice"] = "[바뀜] 지침이 바뀌었다 — hub_guide_render 로 진입 파일을 다시 쓰고 먼저 읽는다"
        if repo_results is None:
            return {
                "phase": 1,
                "hub": hub,
                "repo_check": {
                    "commands": commands,
                    "rules": [
                        "각 명령을 저장소 뿌리에서 그대로 돌리고 {name: {rc, output}} 로 repo_results 에 싣는다",
                        "명령을 고치거나 건너뛰지 않는다 — 못 돌린 명령은 싣지 않는다 (미확인으로 남는다)",
                    ],
                },
                "verdict": "unconfirmed",
                "confirmed": confirmed,
                "unconfirmed": unconfirmed + [f"repo: {name}" for name in commands],
                "next": "hub_session_start(repo_results=…)",
            }
        if not isinstance(repo_results, dict):
            raise invalid_field("repo_results", "{name: {rc, output}} 객체")
        unknown = set(repo_results) - set(commands)
        if unknown:
            raise invalid_field("repo_results", f"요청하지 않은 명령 결과: {', '.join(sorted(unknown))}")
        findings: list[str] = []
        verdict = "start"

        def result(name: str) -> tuple[int, str] | None:
            r = repo_results.get(name)
            if not isinstance(r, dict) or "rc" not in r:
                return None
            return int(r["rc"]), str(r.get("output", ""))

        fetch = result("fetch")
        if fetch is None or fetch[0] != 0:
            unconfirmed.append("repo: 원격 (fetch 결과 없음 또는 실패 — 아래 차이는 마지막 fetch 기준)")
        else:
            confirmed.append("repo: fetch")
        status = result("status")
        if status is None or status[0] != 0:
            unconfirmed.append("repo: 브랜치 · 변경 (status 결과 없음)")
            verdict = "unconfirmed"
        else:
            lines = status[1].splitlines()
            ab = next((m for m in (_AB.match(ln.strip()) for ln in lines) if m), None)
            dirty = [ln for ln in lines if ln.strip() and not ln.startswith("#")]
            has_upstream = any(ln.startswith("# branch.upstream ") for ln in lines)
            confirmed.append("repo: 브랜치 · 변경")
            if dirty:
                verdict = "stop_and_ask"
                findings.append(f"커밋 안 된 변경 {len(dirty)}건 — 멈추고 묻는다")
            if not has_upstream or ab is None:
                unconfirmed.append("repo: 원격 추적 브랜치 없음 — 뒤처짐 · 앞섬을 잴 수 없다")
                if verdict == "start":
                    verdict = "unconfirmed"
            else:
                ahead, behind = int(ab.group(1)), int(ab.group(2))
                if ahead and behind:
                    verdict = "stop_and_ask"
                    findings.append(f"갈라짐 (앞섬 {ahead} · 뒤처짐 {behind}) — 멈추고 묻는다")
                elif behind and verdict == "start":
                    verdict = "fast_forward_then_start"
                    findings.append(f"뒤처짐 {behind} — fast-forward 뒤 시작")
                elif ahead:
                    findings.append(f"앞섬 {ahead} — push 전 커밋이 있다")
        ci = result("check_ignore")
        if ci is None:
            unconfirmed.append("repo: .gitignore 규칙")
        else:
            ok, why = check_ignore_ok(*ci)
            (confirmed if ok else findings).append("repo: .gitignore 규칙" if ok else f".gitignore 규칙이 듣지 않는다 — {why}")
        for path in entries:
            r = result(f"entry_head:{path}")
            if r is None:
                unconfirmed.append(f"repo: {path} 지침 판")
                continue
            m = render.BEGIN_RE.search(r[1] + "\n")
            got = m.group("guide") if m else None
            confirmed.append(f"repo: {path} 지침 판")
            if got != hub["guide"]["current"]:
                findings.append(f"[바뀜] {path} 의 지침 판 {got} ≠ 허브 {hub['guide']['current']} — hub_guide_render")
        for sha, tasks in commits.items():
            r = result(f"commit:{sha}")
            if r is None:
                unconfirmed.append(f"repo: 커밋 {sha[:12]}")
            elif r[0] != 0:
                findings.append(f"task {', '.join(tasks)} 에 묶인 커밋 {sha[:12]} 이 이 저장소에 없다 (push 전 · 다른 원격)")
            else:
                confirmed.append(f"repo: 커밋 {sha[:12]}")
        return {"phase": 2, "hub": hub, "verdict": verdict, "findings": findings,
                "confirmed": confirmed, "unconfirmed": unconfirmed}
