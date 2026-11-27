#!/usr/bin/env python3
"""허브 콜사인별 기억 (M-035 WBS-35.1) — handoff · 세션 끝 · compact · state.json v1 · 보관을 잰다.

정본: ``core/hub_spec.md`` §3.3 · §6.3 · §6.4 (요구 R4.5 · R4.6 · R4.7 · R6 · R11 · G1~G3).

1. handoff — 콜사인 하나에 하나 · 다른 콜사인은 읽기 · 낡은 version 409 · TASK- 아닌 항목 거절 · 10건 넘치면 옮김(삭제 0) (R6.1 · R6.2 · G1 · G3)
2. state.json v1 — 같은 데이터를 **이 검사가 손으로 쓴 1.x 배치**에 넣어 1.x 생성기로 만든 값과 같다 (R6.3 · R0.7)
3. 세션 끝 — handoff 와 진행 한 줄이 한 트랜잭션 (중간 실패면 아무것도 안 쓰임) (R6.4)
4. compact — 요약에서 빠진 식별자 · 그 사이 다른 콜사인의 변경 · 요약 없으면 대조 불가 (R11)
5. 거두기 뒤 — 기록은 읽기 전용으로 남는다 (archived) · 세션 시작이 내 handoff 를 돌려준다 (G2 · R10)
6. 문서 본문 해석 — 승인 요청 action 의 expected_version 4.0 은 400 · 홀로 선 서로게이트는 U+FFFD (HTTP · MCP) · U+001C–001F 만인 본문은 빈 본문 (Python · Go 같은 응답)
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 240

WATCHES = (
    "workflow-source/workflow_kit/*",
    "hub-go/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/check_hub_core.py",
)

import hashlib
import json
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_hub_core import Hub, _env, _resolve_go_hub  # noqa: E402
from workflow_kit.common.state.builder import build_workflow_state_payload  # noqa: E402

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


def _native_state(root: Path, branch: str, tasks: list[tuple[str, str, str]], handoff: dict[str, Any]) -> dict[str, Any]:
    """1.x 배치를 손으로 쓴다 — check_state_json_generated 의 최소 fixture 와 같은 꼴 (허브 펼침 코드와 독립)."""
    (root / "docs").mkdir(parents=True)
    profile = root / "docs" / "PROJECT_PROFILE.md"
    profile.write_text("# native\n", encoding="utf-8")
    bd = root / "ai-workflow" / "memory" / "active" / branch
    (bd / "backlog" / "tasks").mkdir(parents=True)
    (bd / "sessions").mkdir(parents=True)
    title = {tid: t for tid, _s, t in tasks}

    def lst(ids: list[str]) -> str:
        return "".join(f"- {i} — {title[i]}\n" for i in ids) or "-\n"

    (bd / "session_handoff.md").write_text(
        "# Session Handoff\n\n"
        f"## 1. 현재 작업 요약\n\n- 현재 기준선: {handoff['baseline']}\n- 현재 주 작업 축: {handoff.get('focus') or '-'}\n\n"
        f"## 2. 진행 중 작업\n\n- 현재 `in_progress` 작업:\n{lst(handoff['in_progress'])}\n"
        f"## 3. 차단 작업\n\n- 현재 `blocked` 작업:\n{lst(handoff.get('blocked', []))}\n"
        f"## 4. 최근 완료 작업\n\n- 최근 완료 작업 목록:\n{lst(handoff.get('recent_done', []))}\n",
        encoding="utf-8")
    date = tasks[0][0].split("-")[1:4]
    day = "-".join(date)
    lines = [f"# Daily Backlog — {day}\n\n"]
    for tid, status, t in tasks:
        lines.append(f"- **{tid}** [generic] {t}\n  - path: [`./tasks/{tid}.md`](./tasks/{tid}.md)\n  - status: {status}\n")
        (bd / "backlog" / "tasks" / f"{tid}.md").write_text(
            f"---\nid: {tid}\nstatus: {status}\ncreated_at: {day}\nsource_anchor: generic-{tid.lower()}\n"
            f"source_path: backlog/{day}.md\nkind: generic\n---\n\n# {tid} — {t}\n", encoding="utf-8")
    (bd / "backlog" / f"{day}.md").write_text("".join(lines), encoding="utf-8")
    return build_workflow_state_payload(
        project_profile_path=profile, session_handoff_path=bd / "session_handoff.md", daily_backlog_dir=bd / "backlog",
        tasks_dir=bd / "backlog" / "tasks", sessions_dir=bd / "sessions", latest_backlog_path=bd / "backlog" / f"{day}.md",
        generated_at="2026-01-01", workspace_root=root)


def run(hub: Hub, db: Path, tmp: Path) -> None:
    st, reg, _ = hub.call("hub_project_register", {"remote_url": "git@github.com:acme/mem.git", "display_name": "Mem",
                                                     "callsign": "agent-a", "kind": "agent"})
    tok_a, pid = reg["token"], reg["project_id"]
    tok_b = hub.call("hub_callsign_register", {"project_id": pid, "callsign": "agent-b", "kind": "agent"})[1]["token"]
    ids = []
    for title, status in (("첫째", "in_progress"), ("둘째", "blocked"), ("셋째", "planned")):
        ids.append(hub.call("hub_task_create", {"title": title, "status": status}, tok_a)[1]["task"]["id"])

    # 1 handoff
    h = {"baseline": "기준선 A", "focus": "허브", "in_progress": [ids[0]], "blocked": [ids[1]], "recent_done": [],
         "next": ["M-036"], "risks": []}
    s1, put1, _ = hub.call("hub_handoff_put", {"handoff": h}, tok_a)
    s2, read_b, _ = hub.call("hub_handoff_get", {"callsign": "agent-a"}, tok_b)
    s3, stale, _ = hub.call("hub_handoff_put", {"handoff": h, "expected_version": 0}, tok_a)
    s4, bad, _ = hub.call("hub_handoff_put", {"handoff": {**h, "recent_done": ["완료 메모"]}}, tok_a)
    many = [f"TASK-2026-01-01-x-{i:03d} 완료" for i in range(12)]
    s5, roll, _ = hub.call("hub_handoff_put", {"handoff": {**h, "recent_done": many}, "expected_version": 1}, tok_a)
    kept = hub.call("hub_handoff_get", {}, tok_a)[1]
    b_own = hub.call("hub_handoff_get", {}, tok_b)[1]
    ok1 = (s1 == 200 and put1["version"] == 1 and s2 == 200 and read_b["handoff"]["baseline"] == "기준선 A"
           and s3 == 409 and s4 == 400 and bad["error_code"] == "invalid_field"
           and s5 == 200 and len(roll["rolled_over"]) == 2 and len(kept["handoff"]["recent_done"]) == 10
           and kept["handoff"]["recent_done"][0] == many[0] and b_own["handoff"] is None)
    rows = subprocess.run([sys.executable, "-c", f"import sqlite3;c=sqlite3.connect({str(db)!r});"
                           "print(c.execute(\"SELECT COUNT(*) FROM memory_note WHERE kind='handoff_rollover'\").fetchone()[0])"],
                          capture_output=True, encoding="utf-8").stdout.strip()
    _record("case 1 (handoff — 콜사인별 · 읽기 공개 · 409 · TASK- 규칙 · 넘침은 옮김)", ok1 and rows == "2",
            f"{s1} {s2} {s3} {s4}/{bad.get('error_code')} {s5}/{roll.get('rolled_over')} kept={len(kept['handoff']['recent_done'])} moved={rows}")

    # 2 state.json v1 — 1.x 손 배치와 대조
    hub.call("hub_handoff_put", {"handoff": {**h, "recent_done": []}, "expected_version": 2}, tok_a)
    hub_state = hub.call("hub_state", {}, tok_a)[1]["state"]
    tasks = [(ids[0], "in_progress", "첫째"), (ids[1], "blocked", "둘째"), (ids[2], "planned", "셋째")]
    native = _native_state(tmp / "native", "agent-a", tasks, {**h, "recent_done": []})

    def norm(s: dict[str, Any]) -> dict[str, Any]:
        out = json.loads(json.dumps({k: s[k] for k in ("schema_version", "backlog", "session")}, ensure_ascii=False, default=str))
        out["backlog"].pop("latest_backlog_path", None)
        return out

    same = norm(hub_state) == norm(native)
    _record("case 2 (state.json v1 — 1.x 손 배치의 생성기 출력과 같다)", same and hub_state["backlog"]["task_count"] == 3,
            f"hub={norm(hub_state)} native={norm(native)}")

    # 3 세션 끝 — 원자성
    before = hub.call("hub_handoff_get", {}, tok_a)[1]["version"]
    s6, fail, _ = hub.call("hub_session_end", {"handoff": {**h, "baseline": "끝 시도"}, "progress": [
        {"task_id": ids[0], "note": "마무리"}, {"task_id": "TASK-2026-01-01-none-001", "note": "없는 task"}]}, tok_a)
    after_fail = hub.call("hub_handoff_get", {}, tok_a)[1]
    t0 = hub.call("hub_task_get", {"id": ids[0]}, tok_a)[1]["task"]
    s7, end, _ = hub.call("hub_session_end", {"handoff": {**h, "baseline": "끝"}, "expected_version": before,
                                               "progress": [{"task_id": ids[0], "note": "마무리"}]}, tok_a)
    t0b = hub.call("hub_task_get", {"id": ids[0]}, tok_a)[1]["task"]
    ok3 = (s6 == 404 and after_fail["version"] == before and after_fail["handoff"]["baseline"] == "기준선 A"
           and "마무리" not in t0["progress_note"] and s7 == 200 and end["progress_written"] == 1
           and t0b["progress_note"].endswith("마무리") and "push" in end["next"])
    _record("case 3 (세션 끝 — 한 트랜잭션)", ok3, f"fail={s6} ver={after_fail['version']}/{before} end={s7}")

    # 4 compact
    hub.call("hub_task_claim", {"id": ids[0]}, tok_a)
    hub.call("hub_checkpoint_put", {"body": {"next": [f"{ids[0]} 검사", "`hub_state` 대조"], "unverified": ["S3 재실측"],
                                             "verified": [], "rejected": [], "branch": "main"}}, tok_a)
    hub.call("hub_task_progress", {"id": ids[0], "note": "B 가 손댐"}, tok_b)
    s8, res, _ = hub.call("hub_compact_resume", {"summary_ids": [ids[0]]}, tok_a)
    s9, nosum, _ = hub.call("hub_compact_resume", {}, tok_a)
    ok4 = (s8 == 200 and res["missing_from_summary"] == ["hub_state"]
           and any(e["callsign"] == "agent-b" and e["target_id"] == ids[0] for e in res["changed_by_others"])
           and res["checkpoint"]["unverified"] == ["S3 재실측"]
           and s9 == 200 and nosum["missing_from_summary"] is None and "대조 불가" in nosum["compare"])
    _record("case 4 (compact — 빠진 식별자 · 다른 콜사인 변경 · 대조 불가)", ok4,
            f"missing={res.get('missing_from_summary')} others={res.get('changed_by_others')} nosum={nosum.get('compare')}")

    # 5 거두기 뒤 · 세션 시작
    start = hub.call("hub_session_start", {}, tok_a)[1]
    rv = subprocess.run([sys.executable, "-m", "workflow_kit", "hub", "admin", "--db", str(db), "callsign", "revoke",
                         "--project", pid, "--callsign", "agent-a"], capture_output=True, encoding="utf-8", env=_env(), timeout=60)
    s10, arch, _ = hub.call("hub_handoff_get", {"callsign": "agent-a"}, tok_b)
    s11, _, _ = hub.call("hub_handoff_put", {"handoff": h}, tok_a)
    ok5 = (start["hub"]["handoff"]["handoff"]["baseline"] == "끝" and rv.returncode == 0
           and s10 == 200 and arch["archived"] is True and arch["handoff"]["baseline"] == "끝" and s11 == 401)
    _record("case 5 (거두기 뒤 읽기 전용 보관 · 세션 시작의 handoff)", ok5, f"start={start['hub'].get('handoff')} {s10}/{arch} {s11}")

    # 6 문서 본문 해석 — Python · Go 가 같은 응답 (TASK-2026-11-24-claude-plex-003)
    sid_b = hub.call("hub_session_start", {"session": {"harness": "check"}}, tok_b)[1]["session"]["id"]

    def ask(body: str, version: Any) -> tuple[int, dict[str, Any]]:
        st, out, _ = hub.call("hub_approval_request", {"session": sid_b, "title": "문서", "question": "쓸까요?", "action": {
            "type": "project_doc_put", "name": "purpose", "body": body, "expected_version": version}}, tok_b)
        return st, out

    s_f, float_v = ask("# P\n", 4.0)  # 4.0 은 정수가 아니다 — 409 로 판을 대조하지 않고 400
    s_sur, sur = ask("a\ud800b", 0)  # 홀로 선 서로게이트 — U+FFFD 로 읽는다 (Go encoding/json 과 같음)
    want_sha = hashlib.sha256("a\ufffdb".encode("utf-8")).hexdigest()
    blank = {repr(b): ask(b, 0) for b in ("\x1c", "\x1f\n", " \x1d\t")}  # str.strip() 이 지우는 U+001C–001F
    s_put, put_blank, _ = hub.call("hub_project_doc_put", {"name": "profile", "body": "\x1e", "expected_version": 0}, tok_b)
    s_mcp, mcp_sha = _mcp_approval_sha(hub, tok_b, sid_b, "a\\ud800b")
    ok6 = (s_f == 400 and float_v.get("detail", {}).get("field") == "action.expected_version"
           and s_sur == 200 and sur.get("request", {}).get("action", {}).get("sha256") == want_sha
           and all(st == 400 and out.get("detail", {}).get("field") == "body" for st, out in blank.values())
           and s_put == 400 and put_blank.get("detail", {}).get("field") == "body"
           and s_mcp == 200 and mcp_sha == want_sha)
    _record("case 6 (문서 본문 해석 — 4.0 · 서로게이트(HTTP · MCP) · U+001C–001F 공백)", ok6,
            f"float={s_f}/{float_v.get('detail')} sur={s_sur}/{sur.get('request', {}).get('action')} "
            f"blank={ {k: (st, out.get('detail')) for k, (st, out) in blank.items()} } put={s_put} mcp={s_mcp}/{mcp_sha}")


def _mcp_approval_sha(hub: Hub, token: str, session: str, body_json: str) -> tuple[int, str | None]:
    """/mcp 에 날 JSON-RPC 를 보낸다 — SDK 클라이언트는 홀로 선 서로게이트를 보내기 전에 막아 이 경로를 못 잰다."""
    def post(raw: bytes, sid: str | None) -> tuple[int, str, str | None]:
        headers = {"authorization": f"Bearer {token}", "content-type": "application/json",
                   "accept": "application/json, text/event-stream", **({"mcp-session-id": sid} if sid else {})}
        req = urllib.request.Request(hub.base + "/mcp", data=raw, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, r.read().decode("utf-8"), r.headers.get("mcp-session-id")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8"), None

    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "check", "version": "0"}}}
    _, _, mcp_sid = post(json.dumps(init).encode("utf-8"), None)
    post(b'{"jsonrpc":"2.0","method":"notifications/initialized"}', mcp_sid)
    raw = ('{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"hub_approval_request","arguments":'
           '{"session":"%s","title":"t","question":"q","action":{"type":"project_doc_put","name":"purpose",'
           '"body":"%s","expected_version":0}}}}' % (session, body_json)).encode("utf-8")
    status, text, _ = post(raw, mcp_sid)
    data = next((line[5:] for line in text.splitlines() if line.startswith("data:")), text)  # SSE 이면 data 줄
    try:
        result = json.loads(data).get("result") or {}
        out = result.get("structuredContent") or json.loads(result["content"][0]["text"])
        return status, out.get("request", {}).get("action", {}).get("sha256")
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        return status, None


def _measure(impl: str, cmd: list[str] | None) -> None:
    print(f"  --- [{impl}] ---")
    before = len(_failures)
    with tempfile.TemporaryDirectory(prefix="hubmem-") as d:
        tmp = Path(d)
        db = tmp / "hub.db"
        hub = Hub(db, cmd_prefix=cmd)
        try:
            try:
                run(hub, db, tmp)
            except Exception as exc:  # noqa: BLE001 — 예외도 판정으로
                _record("run (예외)", False, repr(exc))
        finally:
            err = hub.stop()
            if len(_failures) > before:
                print("  --- 허브 stderr ---\n" + err[-2000:])


def main() -> int:
    print("=== 허브 콜사인별 기억 (M-035 WBS-35.1) ===")
    _measure("python", None)
    with tempfile.TemporaryDirectory(prefix="hubmem-go-") as d:
        go_cmd, reason = _resolve_go_hub(Path(d))
        if go_cmd is None:
            print(f"    [unmeasured] go 허브 미측정: {reason}")
        else:
            _measure("go", go_cmd)
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
