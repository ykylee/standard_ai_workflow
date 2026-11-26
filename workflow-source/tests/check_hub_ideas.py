#!/usr/bin/env python3
"""아이디어 박스 (TASK-2026-11-25-claude-plex-010) — Python · Go 실프로세스에서 같은 요청으로 잰다.

1. 적기 — 로그인한 승인된 사람만, 원문 그대로, 멱등, 길이 · NUL · 비밀 거절
2. 집기 · 회신 — 하나만 맡는다, 2시간 뒤 풀린다, 읽은 판에서만, 근거나 미확인 필수
3. 세션 시작 — 사람이 적거나 되물은 것만 최대 2건, worker 와 두 번째 호출에는 없다
4. 처리 — 사람만 · 더 묻기 · 보관 · 닫기 · task 등록(WBS 게이트, 한 트랜잭션)
5. 이관 — DB 18 → 19, 프로젝트 묶음에 실린다
6. 화면 — 실제 브라우저로 적기 · 거절 때 글 보존 · 더 묻기 · 등록 · 휴대폰 폭 (브라우저가 없으면 미측정)
7. 두 구현이 같은 모양의 답을 낸다 (시각 · 프로젝트 id 빼고)
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 300

WATCHES = (
    "workflow-source/workflow_kit/*",
    "hub-go/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/check_hub_core.py",
    "workflow-source/tests/check_hub_screens.py",
    "workflow-source/tests/check_hub_ui.py",
)

import html
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_hub_screens as scr  # noqa: E402
from check_hub_core import Hub, _env, _resolve_go_hub  # noqa: E402

RAW = "  생각\u200b 하나\n둘째 줄\u202e  "
_failures: list[str] = []
_count = 0


def _record(case: str, ok: bool, detail: str = "") -> None:
    global _count
    _count += 1
    if not ok:
        _failures.append(f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail[:1500]) if detail and not ok else ''}")


def http(base: str, path: str, body: Any = None, *, token: str = "", cookie: str = "", origin: str = "", raw: bytes | None = None) -> tuple[int, Any, Any]:
    h = {"content-type": "application/json", "origin": origin or base, **({"authorization": f"Bearer {token}"} if token else {}), **({"cookie": cookie} if cookie else {})}
    data = raw if raw is not None else json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(urllib.request.Request(base + path, data=data, headers=h), timeout=30) as r:
            return r.status, json.loads(r.read()), r.headers
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read()), e.headers


def scrub(v: Any) -> Any:
    if isinstance(v, dict):
        out = {k: scrub(x) for k, x in v.items()}
        if isinstance(out.get("ideas"), list):  # 같은 초에 든 변경끼리의 순서는 실행 속도에 달린다
            out["ideas"] = sorted(out["ideas"], key=lambda i: str(i["id"]))
        return out
    if isinstance(v, list):
        return [scrub(x) for x in v]
    return re.sub(r"P-\d{8}-[0-9a-f]+", "P-*", re.sub(r"\d{4}-\d\d-\d\dT[\d:.]+(?:Z|\+00:00)", "<time>", re.sub(r"TASK-\d{4}-\d\d-\d\d", "TASK-*", v))) if isinstance(v, str) else v


def scenario(impl: str, cmd: list[str] | None, tmp: Path) -> list[Any]:
    log: list[Any] = []
    db = tmp / f"{impl}.db"
    hub = Hub(db, cmd_prefix=cmd)
    exe = scr.browser()
    srv = None

    def keep(r: tuple[int, Any, Any]) -> tuple[int, Any]:
        log.append((r[0], scrub(r[1])))
        return r[0], r[1]

    def tool(name: str, args: dict[str, Any], tok: str) -> tuple[int, Any]:
        return keep(hub.call(name, args, tok))

    try:
        st, reg, _ = hub.call("hub_project_register", {"remote_url": "git@github.com:acme/ideas.git", "display_name": "ideas-demo", "callsign": "owner-a", "kind": "human"})
        pid, owner = reg["project_id"], reg["token"]
        bot, bot2 = (hub.call("hub_callsign_register", {"project_id": pid, "callsign": n, "kind": "agent"})[1]["token"] for n in ("bot-a", "bot-b"))
        _, _, head = http(hub.base, "/api/account/enroll", {"username": f"ia-{impl}", "display_name": "O", "password": "long-test-password-123"}, token=owner)
        cookie = head.get("set-cookie", "").split(";", 1)[0]
        _, _, head = http(hub.base, "/api/account/enroll", {"username": f"ib-{impl}", "display_name": "J", "password": "long-test-password-123"})
        joiner = head.get("set-cookie", "").split(";", 1)[0]
        assert http(hub.base, "/api/account/join", {"project": pid, "callsign": "joiner-a"}, cookie=joiner)[0] == 200
        ideas = f"/api/projects/{pid}/ideas"

        def post(path: str, body: Any, **kw: Any) -> tuple[int, Any]:
            return keep(http(hub.base, path, body, **{"cookie": cookie, **kw}))

        def act(idea: str, action: str, version: Any, **kw: Any) -> tuple[int, Any]:
            return post(f"{ideas}/{idea}", {"action": action, "expected_version": version, **kw})

        # 1
        one = post(ideas, {"body": RAW, "request_id": "k1"})
        again = post(ideas, {"body": RAW, "request_id": "k1"})
        who = {"none": post(ideas, {"body": "x"}, cookie="")[0], "owner token": post(ideas, {"body": "x"}, cookie="", token=owner)[0], "bot": post(ideas, {"body": "x"}, cookie="", token=bot)[0],
               "unapproved": post(ideas, {"body": "x"}, cookie=joiner)[0], "cross origin": post(ideas, {"body": "x"}, origin="https://evil.example")[0]}
        bad = {"missing": {}, "blank": {"body": " \n\u3000"}, "long": {"body": "가" * 4001}, "nul": {"body": "a\0b"}, "type": {"body": ["x"]}, "hidden": {"body": "\u200b\x0b\u202e"}, "replaced": {"body": "a\ufffd"}, "key": {"body": "x", "request_id": 3}, "secret": {"body": "wfh_" + "a" * 30}}
        codes = {k: post(ideas, b)[0] for k, b in bad.items()}
        edge = post(ideas, {"body": "가" * 4000})
        lone = http(hub.base, ideas, raw=b'{"body":"a\\ud800"}', cookie=cookie)[0]
        bytes_ = http(hub.base, ideas, raw=b'{"body":"a\xff"}', cookie=cookie)[0]
        n = len(hub.call("hub_idea_list", {}, bot)[1]["ideas"])
        _record(f"case 1 (적기 — 사람 로그인만 · 원문 그대로 · 멱등 · 거절) [{impl}]",
                one[0] == 200 and one[1]["idea"]["entries"][0]["body"] == RAW and again[1].get("replayed") is True and again[1]["idea"]["id"] == "IDEA-0001"
                and who == {"none": 401, "owner token": 403, "bot": 403, "unapproved": 403, "cross origin": 403} and set(codes.values()) == {400} and edge[0] == 200 and lone == 400 and bytes_ == 400 and n == 2,
                f"{one} {again} {who} {codes} {edge[0]} {lone} {n}")
        # 2
        good = {"id": "IDEA-0001", "expected_version": 2, "verdict": "do", "understood": "이해", "reason": "이유", "refs": ["docs/a.md"], "draft": {"title": "할 일", "wbs": "", "done_criteria": ["된다"]}}
        early = tool("hub_idea_reply", good, bot)
        c1, same, c2, c3 = tool("hub_idea_claim", {"id": "IDEA-0001"}, bot), tool("hub_idea_claim", {"id": "IDEA-0001"}, bot), tool("hub_idea_claim", {"id": "IDEA-0001"}, bot2), tool("hub_idea_claim", {"id": "IDEA-9"}, bot)
        other = tool("hub_idea_reply", good, bot2)
        rej = {k: tool("hub_idea_reply", {**good, **v}, bot)[0] for k, v in {
            "verdict": {"verdict": "yes"}, "no evidence": {"refs": [], "unverified": " "}, "hidden evidence": {"refs": [], "unverified": "\u200b\x0b"}, "hidden ref": {"refs": ["\u200b"]}, "refs": {"refs": [1]}, "many": {"refs": ["x"] * 21}, "draft key": {"draft": {"title": "t", "run": "rm"}},
            "draft title": {"draft": {}}, "reason": {"reason": ""}, "long": {"scope": "가" * 1001}, "stale": {"expected_version": 1},
            # 사유 없는 로드맵 밖 초안은 사람이 그대로 등록할 수 없다 (2026-11-26 운영 422) — 회신 때 거절한다
            "exempt draft": {"draft": {"title": "t", "wbs": "exempt"}}, "exempt blank": {"draft": {"title": "t", "wbs": "exempt", "wbs_exempt_reason": " \u3000"}},
            "exempt reason type": {"draft": {"title": "t", "wbs": "exempt", "wbs_exempt_reason": 3}}}.items()}
        asked = act("IDEA-0001", "ask", 2, body="하나 더")
        stale = tool("hub_idea_reply", good, bot)
        done = tool("hub_idea_reply", {**good, "expected_version": 3}, bot)
        twice = tool("hub_idea_reply", {**good, "expected_version": 4}, bot)
        not_waiting = tool("hub_idea_claim", {"id": "IDEA-0001"}, bot2)
        _record(f"case 2 (집기 · 회신 — 맡은 이 · 읽은 판 · 근거) [{impl}]",
                early[0] == 409 and c1[0] == 200 and same[0] == 409 and c2[0] == 409 and c2[1]["error_code"] == "idea_claimed" and c3[0] == 404 and other[0] == 409
                and {k: v for k, v in rej.items() if k != "stale"} == dict.fromkeys([k for k in rej if k != "stale"], 400) and rej["stale"] == 409
                and asked[0] == 200 and asked[1]["idea"]["status"] == "reviewing" and stale[0] == 409 and done[0] == 200 and done[1]["idea"]["status"] == "replied"
                and [e["kind"] for e in done[1]["idea"]["entries"]] == ["idea", "ask", "reply"] and done[1]["idea"]["entries"][0]["body"] == RAW
                and twice[0] == 409 and not_waiting[0] == 409, f"{early} {c1[0]} {c2} {c3[0]} {other} {rej} {asked} {stale} {done} {twice} {not_waiting}")
        tool("hub_idea_claim", {"id": "IDEA-0002"}, bot)
        with sqlite3.connect(db) as c:
            c.execute("UPDATE idea SET claim_until='2026-01-01T00:00:00+00:00' WHERE id='IDEA-0002'")
        freed = tool("hub_idea_list", {"status": "new"}, bot)
        lapsed = tool("hub_idea_reply", {**good, "id": "IDEA-0002", "expected_version": 2}, bot)
        takeover = tool("hub_idea_claim", {"id": "IDEA-0002"}, bot2)
        late = tool("hub_idea_reply", {**good, "id": "IDEA-0002", "expected_version": 3}, bot)
        with sqlite3.connect(db) as c:
            until = datetime.fromisoformat(c.execute("SELECT claim_until FROM idea WHERE id='IDEA-0002'").fetchone()[0])
            c.execute("UPDATE idea SET status='new', claimed_by=NULL, claim_until=NULL WHERE id='IDEA-0002'")
        left = (until - datetime.now(timezone.utc)).total_seconds()
        _record(f"case 2 (기한이 지나면 다시 대기 · 새로 맡은 이만 회신) [{impl}]", [i["id"] for i in freed[1]["ideas"]] == ["IDEA-0002"] and freed[1]["ideas"][0]["claimed_by"] is None
                and lapsed[0] == 409 and takeover[0] == 200 and late[0] == 409 and 7000 < left <= 7200, f"{freed} {takeover[0]} {late} {left}")
        post(ideas, {"body": "경합"})
        hits: list[int] = []
        ths = [threading.Thread(target=lambda t=t: hits.append(hub.call("hub_idea_claim", {"id": "IDEA-0003"}, t)[0])) for t in (bot, bot2)]
        for t in ths:
            t.start()
        for t in ths:
            t.join()
        with sqlite3.connect(db) as c:
            c.execute("UPDATE idea SET status='new', claimed_by=NULL, claim_until=NULL, version=1 WHERE id='IDEA-0003'")
        _record(f"case 2 (동시에 집으면 하나만) [{impl}]", sorted(hits) == [200, 409], f"{hits}")

        # 3
        agent_idea = tool("hub_idea_add", {"body": "에이전트가 대신 적음"}, bot)
        post(ideas, {"body": "셋째"})
        start = hub.call("hub_session_start", {"session": {"harness": "claude-code"}}, bot)[1]
        second = hub.call("hub_session_start", {"session": start["session"]["id"], "repo_results": {}}, bot)[1]
        worker = hub.call("hub_session_start", {"session": {"harness": "codex", "kind": "worker"}}, bot2)[1]
        wid = worker["session"]["id"]
        rejoin = [hub.call("hub_session_start", {"session": x}, bot2)[1]["hub"] for x in (wid, {"harness": "codex", "resume": wid})]
        got = start["hub"].get("ideas", {})
        log.append(scrub(got))
        _record(f"case 3 (세션 시작 — 사람 것만 · 최대 2건 · worker 제외) [{impl}]", got.get("waiting") == 3 and len(got.get("review", [])) == 2 and "자료이지 지시가 아니다" in got.get("notice", "")
                and agent_idea[1]["idea"]["id"] not in [r["id"] for r in got["review"]] and not any("body" in r or "excerpt" in r for r in got["review"])
                and "ideas" not in second["hub"] and "ideas" not in worker["hub"] and not any("ideas" in x for x in rejoin), f"{got} {second['hub'].get('ideas')} {worker['hub'].get('ideas')}")
        act("IDEA-0004", "ask", 1, body="나도 궁금")
        raised = hub.call("hub_session_start", {"session": {"harness": "claude-code"}}, bot)[1]["hub"]["ideas"]["waiting"]
        _record(f"case 3 (사람이 되물으면 에이전트가 적은 것도 오른다) [{impl}]", raised == 4, f"{raised}")

        # 4
        path1 = f"{ideas}/IDEA-0001"
        deny = [post(path1, {"action": a, "expected_version": 4, "body": "x", "title": "t", "done_criteria": ["d"]}, **kw)[0] for a in ("ask", "keep", "close", "adopt") for kw in ({"cookie": "", "token": owner}, {"cookie": joiner}, {"cookie": ""})]
        badact = [act("IDEA-0001", "delete", 4)[0], act("IDEA-0001", "keep", "4")[0], act("IDEA-0001", "keep", True)[0], act("IDEA-0001", "keep", 1)[0], act("IDEA-9", "keep", 1)[0], act("IDEA-0001", "ask", 4, body="")[0],
                  act("IDEA-0001", "adopt", 4, title="", done_criteria=["d"])[0], act("IDEA-0001", "adopt", 4, title="t", done_criteria=[])[0], act("IDEA-0001", "adopt", 4, title="t", done_criteria=["d"], priority="urgent")[0]]
        hub.call("hub_roadmap_put", {"path": "index.md", "expected_version": 0, "body": "# Roadmap — s\n\n## Milestones\n\n- **M-001** [implementation] 일 — status: in_progress\n  - path: [`./M-001-x.md`](./M-001-x.md)\n"}, owner)
        hub.call("hub_roadmap_put", {"path": "M-001-x.md", "expected_version": 0, "body": "---\nid: M-001\ntitle: 일\nsdlc_phase: implementation\nstatus: in_progress\norder: 1\nparallel_allowed: []\ndeliverables: []\n---\n\n# M-001\n\n## WBS\n\n- **WBS-1.1** 작업\n"}, owner)
        before = hub.call("hub_task_list", {}, owner)[1]["tasks"]
        gate = act("IDEA-0001", "adopt", 4, title="할 일", done_criteria=["된다"], wbs="M-009/WBS-9.9")
        held = hub.call("hub_idea_get", {"id": "IDEA-0001"}, bot)[1]["idea"]
        stale_adopt = act("IDEA-0001", "adopt", 3, title="할 일", done_criteria=["된다"], wbs="M-001/WBS-1.1")[0]
        mid = hub.call("hub_task_list", {}, owner)[1]["tasks"]
        ok = act("IDEA-0001", "adopt", 4, title="할 일", done_criteria=["된다"], wbs="M-001/WBS-1.1")
        task = hub.call("hub_task_get", {"id": ok[1]["task"]["id"]}, owner)[1]["task"] if ok[0] == 200 else {}
        after = [act("IDEA-0001", "adopt", 5, title="t", done_criteria=["d"], wbs="M-001/WBS-1.1")[0], act("IDEA-0001", "ask", 5, body="x")[0], act("IDEA-0001", "close", 5)[0]]
        noreason = act("IDEA-0003", "adopt", 1, title="밖", done_criteria=["d"], wbs="exempt")
        exempt = act("IDEA-0003", "adopt", 1, title="밖", done_criteria=["d"], wbs="exempt", wbs_exempt_reason="로드맵 밖")
        _record(f"case 4 (처리 — 사람만 · 게이트 거절이면 그대로 · task 등록은 한 번) [{impl}]", deny == [403, 403, 401] * 4 and badact == [400, 400, 400, 409, 404, 400, 400, 400, 400] and gate[0] == 422 and held["status"] == "replied"
                and held["version"] == 4 and stale_adopt == 409 and mid == before and ok[0] == 200 and ok[1]["idea"]["status"] == "adopted" and ok[1]["idea"]["task_id"] == task.get("id")
                and task.get("description") == "아이디어 IDEA-0001\n\n" + RAW and task.get("fields", {}).get("done_criteria") == ["된다"] and task.get("wbs") == "M-001/WBS-1.1" and task.get("created_by") == "owner-a" and task.get("status") == "planned"
                and after == [409, 409, 409] and exempt[0] == 200
                and noreason[0] == 422 and noreason[1].get("detail", {}).get("warnings") == ["exempt_reason_required"],
                f"{deny} {badact} {gate} {held['status']} {stale_adopt} {ok} {task} {after} {exempt} {noreason}")
        k = [act("IDEA-0002", "keep", 3), act("IDEA-0002", "ask", 4, body="다시"), act("IDEA-0002", "close", 5)]
        tool("hub_idea_list", {}, bot)
        tool("hub_idea_list", {"status": "nope"}, bot)
        keep(http(hub.base, ideas, cookie=cookie))
        keep(http(hub.base, f"{ideas}?status=", cookie=cookie))
        keep(http(hub.base, f"{ideas}/IDEA-0002", token=bot))
        keep(http(hub.base, f"{ideas}/IDEA-9", token=bot))
        ops = [e["op"] for e in hub.call("hub_events", {"target_kind": "idea", "target_id": "IDEA-0002"}, owner)[1]["events"]]
        log.append(ops)
        _record(f"case 4 (보관 · 다시 묻기 · 닫기 · 이력) [{impl}]", [x[1].get("idea", {}).get("status") for x in k] == ["kept", "new", "closed"] and ops == ["add", "claim", "claim", "keep", "ask", "close"], f"{k} {ops}")
        rv = hub.call("hub_idea_claim", {"id": "IDEA-0004"}, bot)
        out_pid = hub.call("hub_project_register", {"remote_url": "git@github.com:acme/other.git", "display_name": "o", "callsign": "owner-z", "kind": "human"})[1]
        far = [hub.call("hub_idea_get", {"id": "IDEA-0001"}, out_pid["token"])[0], http(hub.base, ideas, token=out_pid["token"])[0]]
        _record(f"case 4 (다른 프로젝트에는 없다) [{impl}]", rv[0] == 200 and far == [404, 403], f"{far}")

        # 5
        bundle = tmp / f"{impl}.bundle.json"
        r = subprocess.run([*(cmd or [sys.executable, "-m", "workflow_kit", "hub"]), "admin", "--db", str(db), "project", "export", "--project", pid, "--out", str(bundle), "--public-url", hub.base],
                           capture_output=True, encoding="utf-8", env=_env(), timeout=60)
        tables = json.loads(bundle.read_text(encoding="utf-8"))["tables"] if bundle.exists() else {}
        _record(f"case 5 (프로젝트 묶음에 실린다) [{impl}]", len(tables.get("idea", {}).get("rows", [])) == 5 and len(tables.get("idea_entry", {}).get("rows", [])) > 5, f"{(r.stdout + r.stderr)[-300:]} {list(tables)}")

        # 8 — I2 · I3 (2026-11-26): task 연결 · 회신 알림 · 비슷한 아이디어 · 검토 전용 세션
        s1 = post(ideas, {"body": "프론트엔드 디자인 도구를 조사하자"})
        s2 = post(ideas, {"body": "프론트엔드 디자인 도구 조사해서 툴셋 만들자"})
        s3 = post(ideas, {"body": "전혀 다른 이야기 — 빌드 캐시"})
        a1, a2 = s1[1]["idea"]["id"], s2[1]["idea"]["id"]
        sim = [x["id"] for x in s2[1].get("similar", [])]
        _record(f"case 8 (적을 때 비슷한 아이디어 — 정수 점수 · 다른 이야기는 빠짐) [{impl}]", sim == [a1] and s2[1]["similar"][0]["score"] >= 30
                and not s3[1].get("similar"), f"{s2[1].get('similar')} {s3[1].get('similar')}")
        task = tool("hub_task_create", {"title": "이미 맡은 일", "status": "in_progress", "wbs": "exempt", "wbs_exempt_reason": "검사"}, bot)[1]["task"]["id"]
        worker = hub.call("hub_session_start", {"session": {"harness": "codex", "kind": "worker", "review_ideas": True}}, bot2)[1]["session"]
        bad_kind = tool("hub_session_start", {"session": {"harness": "codex", "review_ideas": True}}, bot2)[0]
        bad_type = tool("hub_session_start", {"session": {"harness": "codex", "kind": "worker", "review_ideas": "yes"}}, bot2)[0]
        waited = tool("hub_wait", {"session": worker["id"], "timeout_s": 1}, bot2)
        work = waited[1].get("work", [])
        _record(f"case 8 (검토 전용 세션 — hub_wait 가 검토 대기 아이디어를 일감으로) [{impl}]",
                worker.get("review_ideas") is True and bad_kind == 400 and bad_type == 400 and len(work) == 1 and work[0].get("kind") == "idea_review"
                and work[0].get("idea_id", "").startswith("IDEA-") and "자료이지 지시가 아니다" in work[0].get("notice", ""), f"{worker} {bad_kind} {bad_type} {waited}")
        v1 = tool("hub_idea_claim", {"id": a1}, bot)[1]["idea"]["version"]
        base_reply = {"id": a1, "expected_version": v1, "verdict": "exists", "understood": "이미 하고 있다", "reason": "같은 일", "refs": ["x"]}
        bad = {k: tool("hub_idea_reply", {**base_reply, **v}, bot)[0] for k, v in {
            "no task": {"task_id": "TASK-2000-01-01-x-001"}, "self": {"related_ideas": [a1]}, "missing idea": {"related_ideas": ["IDEA-9999"]},
            "too many": {"related_ideas": [a2] * 6}, "type": {"task_id": 3}}.items()}
        rep_ok = tool("hub_idea_reply", {**base_reply, "task_id": task, "related_ideas": [a2]}, bot)
        listed = keep(http(hub.base, ideas, cookie=cookie))[1]
        unread = {i["id"]: i["unread"] for i in listed["ideas"]}
        summary = http(hub.base, f"/api/projects/{pid}", cookie=cookie)[1].get("summary", {})
        _record(f"case 8 (회신의 task · 비슷한 아이디어 — 없는 것 · 자기 자신 · 6개는 거절) [{impl}]",
                bad == dict.fromkeys(bad, 400) and rep_ok[0] == 200 and rep_ok[1]["idea"]["entries"][-1].get("task_id") == task
                and rep_ok[1]["idea"]["entries"][-1].get("related_ideas") == [a2], f"{bad} {rep_ok}")
        seen = act(a1, "seen", None)
        after_seen = keep(http(hub.base, ideas, cookie=cookie))[1]
        summary2 = http(hub.base, f"/api/projects/{pid}", cookie=cookie)[1].get("summary", {})
        _record(f"case 8 (새 회신 — 목록 · 프로젝트 요약에 수, 열면 읽음 · 판은 그대로) [{impl}]",
                unread.get(a1) == 1 and listed.get("unread_total", 0) >= 1 and summary.get("ideas_unread") == listed.get("unread_total")
                and seen[0] == 200 and seen[1]["idea"]["unread"] == 0 and seen[1]["idea"]["version"] == rep_ok[1]["idea"]["version"]
                and after_seen["unread_total"] == listed["unread_total"] - 1 and summary2.get("ideas_unread") == after_seen["unread_total"]
                and http(hub.base, f"{ideas}/{a1}", {"action": "seen"}, cookie=joiner)[0] == 403, f"{unread} {listed.get('unread_total')} {summary} {seen} {summary2}")
        ver = seen[1]["idea"]["version"]
        links = [act(a1, "link", ver, task_id="TASK-2000-01-01-x-001")[0], act(a1, "link", ver)[0], act(a1, "link", ver - 1, task_id=task)[0]]
        linked = act(a1, "link", ver, task_id=task)
        again = act(a1, "link", ver + 1, task_id=task)[0]
        before_n = len(hub.call("hub_task_list", {}, owner)[1]["tasks"])
        _record(f"case 8 (이 task 로 처리 — 새 task 없이 adopted · 없는 task 404 · 두 번은 409) [{impl}]",
                links == [404, 400, 409] and linked[0] == 200 and linked[1]["idea"]["status"] == "adopted" and linked[1]["idea"]["task_id"] == task
                and again == 409 and len(hub.call("hub_task_list", {}, owner)[1]["tasks"]) == before_n, f"{links} {linked} {again}")
        detail = keep(http(hub.base, f"{ideas}/{a2}", cookie=cookie))[1]
        _record(f"case 8 (상세의 비슷한 아이디어) [{impl}]", [x["id"] for x in detail.get("similar", [])] == [a1], f"{detail.get('similar')}")

        # 6
        if exe is None:
            print("    [unmeasured] 화면 미측정: Chrome · Chromium 이 없다")
            return log
        srv = scr.proxy(hub, cookie)
        port = srv.server_address[1]
        dom = scr.draw(exe, tmp, port, f"p/{pid}/ideas", "~아이디어=화면에서 적음|적어 두기", 8000)
        with sqlite3.connect(db) as c:
            row = c.execute("SELECT i.id,i.added_via,e.body_json FROM idea i JOIN idea_entry e ON e.idea_id=i.id AND e.seq=1 ORDER BY i.id DESC LIMIT 1").fetchone()
        _record(f"case 6 (화면에서 적는다) [{impl}]", row[1] == "web" and json.loads(row[2])["body"] == "화면에서 적음" and "적어 두었다" in dom and "화면에서 적음" in dom, f"{row}")
        dom = scr.draw(exe, tmp, port, f"p/{pid}/ideas", "!아이디어=갱신 중에 쓴 글", 16000)
        _record(f"case 6 (자동 갱신이 오가는 동안 쓴 글이 남는다) [{impl}]", 'data-kept="9"' in dom and "자동 새로고침을 잠시 멈췄다" in dom, dom[-400:])
        secret = "wfh_" + "b" * 30
        dom = scr.draw(exe, tmp, port, f"p/{pid}/ideas", f"~아이디어=앞 {secret} 뒤|적어 두기", 8000)
        _record(f"case 6 (거절돼도 폼이 다시 그려지지 않는다) [{impl}]", "secret_in_payload" in dom and "적어 두었다" not in dom and f'data-kept="{len(secret) + 4}"' in dom, dom[-600:])
        nid = row[0]
        hub.call("hub_idea_claim", {"id": nid}, bot)
        hub.call("hub_idea_reply", {**good, "id": nid, "expected_version": 2, "reason": "이\u200b유", "draft": {"title": "초\u202e안", "wbs": "M-001/WBS-1.1", "done_criteria": ["가", "나"]}}, bot)
        dom = scr.draw(exe, tmp, port, f"p/{pid}/ideas/{nid}")
        shown = not scr.problems(dom, "회신") and dom.count(">U+200B</mark>") == 1 and dom.count(">U+202E</mark>") == 1 and "등록할 내용에 보이지 않는 문자 1개" in dom and 'data-exact="bidi-override/pre-wrap"' in dom
        _record(f"case 6 (회신 · 보이지 않는 문자) [{impl}]", shown, f"{scr.problems(dom, '회신')}")
        dom1 = scr.draw(exe, tmp, port, f"p/{pid}/ideas/IDEA-0001")
        _record(f"case 6 (원문의 보이지 않는 문자 · 등록된 것은 처리 단추 없음) [{impl}]", dom1.count(">U+200B</mark>") == 1 and dom1.count(">U+202E</mark>") == 1 and "task 로 등록" not in dom1)
        dom = scr.draw(exe, tmp, port, f"p/{pid}/ideas/{nid}", "~task 제목=고친 제목|task 로 등록", 12000)
        made = hub.call("hub_idea_get", {"id": nid}, bot)[1]["idea"]
        t = hub.call("hub_task_get", {"id": made["task_id"] or "x"}, owner)[1].get("task", {})
        _record(f"case 6 (초안을 고쳐 등록) [{impl}]", t.get("title") == "고친 제목" and t.get("fields", {}).get("done_criteria") == ["가", "나"], f"{made} {t}")
        post(ideas, {"body": "로드맵 밖 일"})
        oid = hub.call("hub_idea_list", {}, bot)[1]["ideas"]
        oid = max(i["id"] for i in oid)
        v = hub.call("hub_idea_claim", {"id": oid}, bot)[1]["idea"]["version"]
        hub.call("hub_idea_reply", {**good, "id": oid, "expected_version": v, "draft": {"title": "밖의 일", "wbs": "exempt", "wbs_exempt_reason": "초안의 사유", "done_criteria": ["끝"]}}, bot)
        dom = scr.draw(exe, tmp, port, f"p/{pid}/ideas/{oid}", "~WBS 면제 사유=|task 로 등록", 9000)
        held_o = hub.call("hub_idea_get", {"id": oid}, bot)[1]["idea"]
        _record(f"case 6 (사유 없는 exempt 는 보내지 않고 사유 칸을 가리킨다) [{impl}]", held_o["status"] == "replied" and held_o["version"] == v + 1
                and "칸을 채운다 — 아직 보내지 않았다" in html.unescape(dom), dom[-500:])
        dom = scr.draw(exe, tmp, port, f"p/{pid}/ideas/{oid}", "~WBS=|~WBS 면제 사유=|task 로 등록", 9000)
        _record(f"case 6 (게이트 거절을 화면의 칸 이름으로 말한다) [{impl}]", "'WBS' 칸에 M-NNN/WBS-N.N 을 적거나" in html.unescape(dom)
                and "--wbs" not in html.unescape(dom), dom[-500:])
        dom = scr.draw(exe, tmp, port, f"p/{pid}/ideas/{oid}", "task 로 등록", 9000)
        made_o = hub.call("hub_idea_get", {"id": oid}, bot)[1]["idea"]
        t_o = hub.call("hub_task_get", {"id": made_o["task_id"] or "x"}, owner)[1].get("task", {})
        _record(f"case 6 (초안의 면제 사유가 칸에 채워져 그대로 등록된다) [{impl}]", made_o["status"] == "adopted" and t_o.get("wbs") == "exempt"
                and t_o.get("wbs_exempt_reason") == "초안의 사유", f"{made_o['status']} {t_o.get('wbs')} {t_o.get('wbs_exempt_reason')}")
        # I2a · 연결 — 새 회신 알림(개요 · 목록), 열면 읽음, '이 task 로 처리'
        post(ideas, {"body": "화면에서 묶을 일"})
        lid = max(i["id"] for i in hub.call("hub_idea_list", {}, bot)[1]["ideas"])
        lv = hub.call("hub_idea_claim", {"id": lid}, bot)[1]["idea"]["version"]
        hub.call("hub_idea_reply", {**good, "id": lid, "expected_version": lv, "draft": None, "task_id": task}, bot)
        over = html.unescape(scr.draw(exe, tmp, port, f"p/{pid}"))
        lst = html.unescape(scr.draw(exe, tmp, port, f"p/{pid}/ideas"))
        _record(f"case 6 (새 회신 — 개요 알림 · 목록 칩) [{impl}]", "아이디어에 새 회신" in over and "새 회신 1" in lst and "아직 안 본 회신" in lst, over[-300:])
        scr.draw(exe, tmp, port, f"p/{pid}/ideas/{lid}")
        seen_now = hub.call("hub_idea_get", {"id": lid}, bot)[1]["idea"]["unread"]
        _record(f"case 6 (열어 보면 읽음) [{impl}]", seen_now == 0, f"{seen_now}")
        dom = scr.draw(exe, tmp, port, f"p/{pid}/ideas/{lid}", "이 task 로 처리", 9000)
        lk = hub.call("hub_idea_get", {"id": lid}, bot)[1]["idea"]
        _record(f"case 6 (이 task 로 처리 — 단추) [{impl}]", lk["status"] == "adopted" and lk["task_id"] == task,
                f"{lk['status']} {lk['task_id']}")
        dom = scr.draw(exe, tmp, port, f"p/{pid}/ideas/IDEA-0005", "~task 제목=남을 초안|~더 묻기=한 번 더|더 묻기", 8000)
        _record(f"case 6 (더 묻기 · 다른 칸의 글은 남는다) [{impl}]", [e["kind"] for e in hub.call("hub_idea_get", {"id": "IDEA-0005"}, bot)[1]["idea"]["entries"]] == ["idea", "ask"] and 'data-title="남을 초안"' in dom, dom[-400:])
        for route in (f"p/{pid}/ideas", f"p/{pid}/ideas/{nid}", f"p/{pid}/ideas/IDEA-0005"):
            dom = scr.draw(exe, tmp, port, route, narrow=True)
            w = re.search(r'data-w="(\d+)/(\d+)"', dom)
            _record(f"case 6 (휴대폰 폭에서 옆으로 넘치지 않는다 · {route.rsplit('/', 1)[1]}) [{impl}]", bool(w) and int(w[1]) <= int(w[2]) and "아이디어" in html.unescape(dom), f"{w and w[0]}")
    finally:
        if srv:
            srv.shutdown()
            srv.server_close()
        hub.stop()
    return log


def case_5_migration(tmp: Path) -> None:
    from workflow_kit.hub import db as hubdb

    path, now = tmp / "old.db", datetime(2026, 11, 25, tzinfo=timezone.utc)
    full = hubdb.MIGRATIONS
    try:
        hubdb.MIGRATIONS = full[:18]
        hubdb.open_db(path, now=now)
    finally:
        hubdb.MIGRATIONS = full
    hubdb.open_db(path, now=now)
    conn = hubdb.connect(path)
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        _record("case 5 (DB 18 → 19)", hubdb.schema_version(conn) == len(full) >= 19 and {"idea", "idea_entry"} <= tables)
    finally:
        conn.close()


def main() -> int:
    print("check_hub_ideas")
    missed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="hub-ideas-", ignore_cleanup_errors=True) as d:
        tmp = Path(d)
        case_5_migration(tmp)
        py = scenario("python", None, tmp)
        go_cmd, why = _resolve_go_hub(tmp)
        if go_cmd is None:
            print(f"    [unmeasured] Go 허브 미측정: {why}")
            missed.append("Go 허브")
        else:
            go = scenario("go", go_cmd, tmp)
            diff = [(i, a, b) for i, (a, b) in enumerate(zip(py, go)) if a != b]
            _record("case 7 (두 구현이 같은 답)", not diff and len(py) == len(go), f"{len(diff)}건 {len(py)}/{len(go)} {diff[:2]}")
    if scr.browser() is None:
        missed.append("브라우저")
    print(f"PASS {_count - len(_failures)} · FAIL {len(_failures)} · 미측정 {len(missed)}{' (' + ', '.join(missed) + ')' if missed else ''}")
    for f in _failures:
        print("  -", f[:400])
    return 1 if _failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
