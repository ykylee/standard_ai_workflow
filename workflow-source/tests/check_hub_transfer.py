#!/usr/bin/env python3
"""허브 서버 간 프로젝트 이전 (M-039 WBS-39.4, 소유자 2026-11-21) — 묶음 · CLI export/import · 봉인.

정본: ``workflow_kit/hub/transfer.py`` · ``core/hub_spec.md`` §3.5. 실제 허브 프로세스 둘(A · B) 사이에서
관리자 CLI 로 옮기고, **같은 콜사인 토큰**으로 두 허브의 응답을 대조한다.

1. 분류 — DB 의 모든 표가 '프로젝트 표'(project_id) 또는 허브 전역 표. 미분류 0
2. 왕복 — A 에서 봉인 + 묶음 → B 에 들임 → 같은 토큰으로 task · 계획 · 결정 상태 · handoff · 위키 · 지침 ·
   memory_index · 로드맵 진척 · 프로젝트 문서 · 상태 요약이 이전 직전의 A 와 같다. 표별 행 수가 같고 이력은 순서 그대로 + 들임 1
3. 봉인 — A 에서 그 프로젝트의 도구 · 화면 호출이 410 project_moved + 새 주소, 주소 조회는 새 주소를 알리고,
   같은 허브의 다른 프로젝트는 그대로
4. 거절 — 같은 프로젝트(봉인 안 됨) · 묶음 변조 · 더 새로운 DB 판 · 다른 프로젝트가 쓰는 주소 키 → 거절, 대상 변화 0
5. 되옮기기 — B 에서 바뀐 뒤 B → A(봉인된 사본) 로 옮기면 교체되고 A 가 다시 정본 · B 는 봉인
6. 봉인 풀기 — unseal 뒤 다시 쓴다
7. HTTP 경로 (소유자 2026-11-21 — 대상 허브 일회용 초대 코드): 허브가 내려준 클라이언트의 move —
   다른 프로젝트용 · 만료된 코드는 대상이 거절하고 원본 봉인이 풀린다(원래 봉인돼 있던 것은 그대로), 맞는 코드면 옮겨지고
   같은 토큰으로 B 응답이 같고 A 는 봉인 · env 주소가 B 로, 쓴 코드는 다시 못 쓴다
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 300

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/check_hub_core.py",
    "workflow-source/tests/check_roadmap_gates.py",
)

import json
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_roadmap_gates as rg  # noqa: E402
from check_hub_core import Hub, _env  # noqa: E402
from workflow_kit.common import plan_claims, plan_responses  # noqa: E402
from workflow_kit.hub import db as hubdb  # noqa: E402
from workflow_kit.hub.transfer import HUB_SCOPED_TABLES, project_tables  # noqa: E402

_failures: list[str] = []
_passes: list[str] = []

PLAN = ("- Claims: C1 옮겨도 같다\n"
        "- Decisions: D1 [C1] 어디로? | default: a | options: a = 가; b = 나 | state: proposed\n")
CRIT = ["[C1] 같다"]


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


def admin(db: Path, *args: str) -> tuple[int, dict[str, Any]]:
    r = subprocess.run([sys.executable, "-m", "workflow_kit", "hub", "admin", "--db", str(db), "project", *args],
                       capture_output=True, encoding="utf-8", env=_env(), timeout=120)
    try:
        return r.returncode, json.loads(r.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return r.returncode, {"raw": r.stdout[-400:], "err": r.stderr[-400:]}


def counts(db: Path, pid: str) -> dict[str, int]:
    with sqlite3.connect(db) as c:
        c.row_factory = sqlite3.Row
        return {t: c.execute(f'SELECT COUNT(*) FROM "{t}" WHERE project_id = ?', (pid,)).fetchone()[0]
                for t in project_tables(c)}


def fill(hub: Hub, tok: str, name: str) -> str:
    """A 의 프로젝트를 채운다 — 이전 대상이 되는 종류 전부."""
    _, t, _ = hub.call("hub_task_create", {"title": f"{name} task", "plan_md": PLAN, "fields": {"done_criteria": CRIT}}, tok)
    tid = t["task"]["id"]
    hub.call("hub_task_claim", {"id": tid}, tok)
    hub.call("hub_task_progress", {"id": tid, "note": "옮기기 전"}, tok)
    hub.call("hub_task_link_commit", {"id": tid, "sha": "a" * 40, "branch": "main"}, tok)
    plan = plan_claims.parse_plan(PLAN.splitlines() + [f"- Completion criteria: {c}" for c in CRIT])
    body = plan_responses.render_response(task_id=tid, plan=plan, responder="owner-a", received_at="2026-11-21T09:00:00+09:00",
                                          values={"D1": "b"}, opened={"D1": True})
    hub.call("hub_plan_respond", {"task_id": tid, "body": body}, tok)
    hub.call("hub_handoff_put", {"handoff": {"baseline": f"{name} 기준선", "in_progress": [tid], "next": ["옮긴다"]}}, tok)
    hub.call("hub_wiki_ingest", {"summary": "첫", "pages": [{"path": "concepts/a.md", "body": "# A\n\n본문\n", "expected_version": 0}]}, tok)
    hub.call("hub_guide_propose", {"base_version": 0, "body": "# 지침\n\n- 옮겨도 남는다\n"}, tok)
    hub.call("hub_memory_entry_put", {"entry": {
        "id": "MEM-2026-01-01-001", "schema_version": 1, "source_paths": ["ai-workflow/x.md"], "primary_abstraction": "e",
        "cue_anchors": ["x"], "value_digest": "x", "owners": ["o"], "scope": ["s"], "merge_state": "active",
        "mentioned_in": [], "related_ids": [], "created_at": "2026-01-01", "updated_at": "2026-01-01"}, "expected_version": 0}, tok)
    with tempfile.TemporaryDirectory() as d:
        rg._fixture(Path(d))
        for p in sorted((Path(d) / "ai-workflow/memory/active/roadmap").glob("*.md")):
            hub.call("hub_roadmap_put", {"path": p.name, "body": p.read_text(encoding="utf-8")}, tok)
    hub.call("hub_project_doc_put", {"name": "purpose", "body": "# PURPOSE\n\n## 1. Goals\n\n- **G1**: 옮겨도 같다\n"}, tok)
    return tid


def snapshot(hub: Hub, tok: str, tid: str) -> dict[str, Any]:
    def g(name: str, args: dict[str, Any] | None = None) -> Any:
        st, out, _ = hub.call(name, args or {}, tok)
        return st, out

    return {
        "tasks": g("hub_task_list", {"limit": 500}), "task": g("hub_task_get", {"id": tid}),
        "plan": g("hub_plan_status", {"task_id": tid}), "handoff": g("hub_handoff_get"),
        "wiki": g("hub_wiki_list"), "page": g("hub_wiki_get", {"path": "concepts/a.md"}), "guide": g("hub_guide_get"),
        "mem": g("hub_memory_entry_list"), "roadmap": g("hub_roadmap_state"), "doc": g("hub_project_doc_get", {"name": "purpose"}),
        "state": g("hub_state"), "whoami": g("hub_whoami"),
    }


def ops(hub: Hub, tok: str) -> list[str]:
    st, ev, _ = hub.call("hub_events", {"limit": 1000}, tok)
    return [f"{e['op']}:{e['target_kind']}:{e['target_id']}" for e in ev.get("events", [])]


def main() -> int:
    print("check_hub_transfer")
    # 1 분류
    with tempfile.TemporaryDirectory(prefix="hub-xfer-0-") as d:
        p = Path(d) / "x.db"
        hubdb.open_db(p, now=datetime.now(timezone.utc))
        with sqlite3.connect(p) as c:
            names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            proj = set(project_tables(c))
    unclassified = sorted(names - proj - HUB_SCOPED_TABLES)
    _record("case 1 (분류 — 모든 표가 프로젝트 표 또는 허브 전역 표)", not unclassified and "task" in proj and "event" in proj,
            f"미분류={unclassified}")

    with tempfile.TemporaryDirectory(prefix="hub-xfer-") as d:
        tmp = Path(d)
        db_a, db_b, db_c = tmp / "a.db", tmp / "b.db", tmp / "c.db"
        a = Hub(db_a)
        b = Hub(db_b)
        try:
            _, reg, _ = a.call("hub_project_register", {"remote_url": "git@github.com:acme/moving.git", "display_name": "moving",
                                                         "callsign": "owner-a", "kind": "human"})
            pid, tok = reg["project_id"], reg["token"]
            _, other, _ = a.call("hub_project_register", {"remote_url": "git@github.com:acme/staying.git",
                                                           "display_name": "staying", "callsign": "owner-q", "kind": "human"})
            tid = fill(a, tok, "A")
            before = snapshot(a, tok, tid)
            ops_a = ops(a, tok)
            counts_a = counts(db_a, pid)
            bundle = tmp / "moving.bundle.json"
            e_rc, e_out = admin(db_a, "export", "--project", pid, "--out", str(bundle), "--seal-to", b.base,
                                "--public-url", a.base)
            i_rc, i_out = admin(db_b, "import", "--file", str(bundle))
            after = snapshot(b, tok, tid)
            diff = sorted(k for k in before if before[k] != after[k])
            counts_b = counts(db_b, pid)
            ops_b = ops(b, tok)
            ok2 = (e_rc == 0 and i_rc == 0 and e_out.get("sealed", {}).get("sealed") is True and not diff
                   and all(before[k][0] == 200 for k in before)
                   and {k: v for k, v in counts_b.items() if k != "event"} == {k: v for k, v in counts_a.items() if k != "event"}
                   and counts_b["event"] == counts_a["event"] + 2  # 봉인 1(A 에서 · 묶음에 실림) + 들임 1
                   and ops_b[: len(ops_a)] == ops_a and ops_b[-2:] == [f"sealed:project:{pid}", f"project_imported:project:{pid}"]
                   and bundle.stat().st_mode & 0o077 == 0)
            _record("case 2 (왕복 — 같은 토큰으로 B 의 응답이 이전 직전의 A 와 같다 · 표별 행 수 · 이력 순서)", ok2,
                    f"export={e_rc}/{e_out.get('counts')} import={i_rc}/{i_out} diff={diff} "
                    f"counts_a={counts_a} counts_b={counts_b} tail={ops_b[-3:]}")

            # 3 봉인
            s1, moved, _ = a.call("hub_task_list", {}, tok)
            s2, mv_w, _ = a.call("hub_task_create", {"title": "옮긴 뒤 A 에 쓰기"}, tok)
            s3, look, _ = a.call("hub_project_lookup", {"remote_url": "git@github.com:acme/moving.git"})
            s4, stay, _ = a.call("hub_task_list", {}, other["token"])
            s5, cs, _ = a.call("hub_callsign_register", {"project_id": pid, "callsign": "late-b", "kind": "agent"})
            import urllib.error
            import urllib.request
            req = urllib.request.Request(f"{a.base}/api/projects/{pid}/tasks", headers={"authorization": f"Bearer {tok}"})
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    s6 = r.status
            except urllib.error.HTTPError as e:
                s6 = e.code
            counts_a2 = counts(db_a, pid)
            ok3 = (s1 == 410 and moved.get("error_code") == "project_moved" and moved["detail"].get("moved_to") == b.base
                   and s2 == 410 and s3 == 200 and look.get("moved_to") == b.base and s4 == 200 and s5 == 410 and s6 == 410
                   and counts_a2["task"] == counts_a["task"])
            _record("case 3 (봉인 — A 의 도구 · 화면 410 + 새 주소, 조회는 새 주소, 다른 프로젝트 그대로)", ok3,
                    f"{s1}/{moved.get('detail')} {s2} {s3}/{look} {s4} {s5} ui={s6}")

            # 4 거절
            c_b = counts(db_b, pid)
            r_dup, dup = admin(db_b, "import", "--file", str(bundle))
            data = json.loads(bundle.read_text(encoding="utf-8"))
            bad = json.loads(json.dumps(data))
            bad["tables"]["task"]["rows"][0][2] = "변조"
            (tmp / "bad.json").write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
            r_bad, badout = admin(db_c, "import", "--file", str(tmp / "bad.json"))
            newer = json.loads(json.dumps(data))
            newer["source"]["db_version"] = hubdb.latest_version() + 1
            (tmp / "newer.json").write_text(json.dumps(newer, ensure_ascii=False), encoding="utf-8")
            r_new, newout = admin(db_c, "import", "--file", str(tmp / "newer.json"))
            cc = Hub(db_c)
            try:
                cc.call("hub_project_register", {"remote_url": "git@github.com:acme/moving.git", "display_name": "squatter",
                                                  "callsign": "own-c", "kind": "human"})
            finally:
                cc.stop()
            r_key, keyout = admin(db_c, "import", "--file", str(bundle))
            with sqlite3.connect(db_c) as c:
                c_tasks = c.execute("SELECT COUNT(*) FROM task").fetchone()[0]
            ok4 = (r_dup != 0 and "project_exists" in json.dumps(dup) and counts(db_b, pid) == c_b
                   and r_bad != 0 and "bundle_digest_mismatch" in json.dumps(badout)
                   and r_new != 0 and "bundle_newer_than_hub" in json.dumps(newout)
                   and r_key != 0 and "alias_taken" in json.dumps(keyout) and c_tasks == 0)
            _record("case 4 (거절 — 같은 프로젝트 · 변조 · 더 새로운 판 · 남의 주소 키, 대상 변화 0)", ok4,
                    f"dup={r_dup}/{dup} bad={r_bad}/{badout} newer={r_new}/{newout} key={r_key}/{keyout} c_tasks={c_tasks}")

            # 5 되옮기기 — B 에서 바뀐 뒤 B → A
            # 로드맵이 함께 옮겨져 B 에서도 WBS 게이트가 산다 — 로드맵 밖 작업으로 선언한다
            s_nt, nt, _ = b.call("hub_task_create", {"title": "B 에서 만든 task", "wbs": "exempt",
                                                      "wbs_exempt_reason": "이전 검사"}, tok)
            back = tmp / "back.json"
            rb, bout = admin(db_b, "export", "--project", pid, "--out", str(back), "--seal-to", a.base)
            ra, aout = admin(db_a, "import", "--file", str(back))
            s7, a_list, _ = a.call("hub_task_list", {"limit": 500}, tok)
            s8, b_moved, _ = b.call("hub_task_list", {}, tok)
            s9, a_write, _ = a.call("hub_task_progress", {"id": tid, "note": "돌아왔다"}, tok)
            ok5 = (s_nt == 200 and rb == 0 and ra == 0 and aout.get("replaced_sealed_copy") is True and s7 == 200
                   and nt.get("task", {}).get("id") in [t["id"] for t in a_list.get("tasks", [])]
                   and s8 == 410 and b_moved["detail"].get("moved_to") == a.base and s9 == 200)
            _record("case 5 (되옮기기 — 봉인된 A 사본을 교체, A 정본 · B 봉인)", ok5,
                    f"{rb} {ra}/{aout} list={s7} b={s8}/{b_moved.get('detail')} write={s9}")

            # 6 봉인 풀기
            ru, _ = admin(db_b, "unseal", "--project", pid)
            s10, _, _ = b.call("hub_task_list", {}, tok)
            _record("case 6 (봉인 풀기 — 다시 쓴다)", ru == 0 and s10 == 200, f"{ru} {s10}")

            # 7 HTTP 경로 — 새 프로젝트 R (A 에서 B 로)
            import os
            import urllib.request
            _, reg_r, _ = a.call("hub_project_register", {"remote_url": "git@github.com:acme/http-move.git",
                                                           "display_name": "http-move", "callsign": "owner-r", "kind": "human"})
            pid_r, tok_r = reg_r["project_id"], reg_r["token"]
            tid_r = fill(a, tok_r, "R")
            before_r = snapshot(a, tok_r, tid_r)
            work = tmp / "env-r"
            (work / ".workflow-hub").mkdir(parents=True)
            (work / ".workflow-hub" / "env").write_text(f"WORKFLOW_HUB_URL={a.base}\nWORKFLOW_HUB_TOKEN={tok_r}\n", encoding="utf-8")
            with urllib.request.urlopen(a.base + "/v1/bootstrap/hub_client.py", timeout=20) as r:
                (work / ".workflow-hub" / "hub_client.py").write_bytes(r.read())
            clean = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "WORKFLOW_HUB_URL", "WORKFLOW_HUB_TOKEN")}

            def client(*args: str) -> tuple[int, dict[str, Any]]:
                r = subprocess.run([sys.executable, "-I", ".workflow-hub/hub_client.py", *args], cwd=work, capture_output=True,
                                   text=True, env=clean, timeout=300)
                try:
                    return r.returncode, json.loads(r.stdout)
                except json.JSONDecodeError:
                    return r.returncode, {"raw": r.stdout[-300:], "err": r.stderr[-300:]}

            def invite(project: str, hours: str = "24") -> str:
                r = subprocess.run([sys.executable, "-m", "workflow_kit", "hub", "admin", "--db", str(db_b), "project", "invite",
                                    "--project", project, "--hours", hours], capture_output=True, encoding="utf-8", env=_env(), timeout=60)
                return str(json.loads(r.stdout.strip().splitlines()[-1]).get("code", ""))

            env_text = lambda: (work / ".workflow-hub" / "env").read_text(encoding="utf-8")  # noqa: E731
            m1, wrong = client("move", b.base, invite("P-nope"))
            a_after_wrong, _, _ = a.call("hub_task_list", {}, tok_r)
            m2, expired = client("move", b.base, invite(pid_r, "0"))
            a_after_exp, _, _ = a.call("hub_task_list", {}, tok_r)
            # 원래 봉인돼 있던 프로젝트는 실패해도 그대로 (정본 둘 방지)
            admin(db_a, "seal", "--project", pid_r, "--to", "http://elsewhere.invalid")
            m3, pre_sealed = client("move", b.base, invite("P-nope"))
            still, _, _ = a.call("hub_task_list", {}, tok_r)
            admin(db_a, "unseal", "--project", pid_r)
            code = invite(pid_r)
            m4, moved = client("move", b.base, code)
            after_r = snapshot(b, tok_r, tid_r)
            diff_r = sorted(k for k in before_r if before_r[k] != after_r[k])
            a_sealed, a_body, _ = a.call("hub_task_list", {}, tok_r)
            c_ok, via_env = client("call", "hub_task_list", "{}")
            bundle_again = json.loads(json.dumps({"invite": code, "bundle": {"format": "x"}}))
            reuse, reuse_out, _ = b.call("hub_project_import", bundle_again)
            ok7 = (m1 == 1 and wrong.get("target", {}).get("error_code") == "invite_wrong_project" and wrong.get("source_unsealed") is True
                   and a_after_wrong == 200 and m2 == 1 and expired.get("target", {}).get("error_code") == "invite_expired"
                   and a_after_exp == 200 and m3 == 1 and still == 410
                   and m4 == 0 and moved.get("status") == "moved" and not diff_r and a_sealed == 410
                   and a_body.get("detail", {}).get("moved_to") == b.base and f"WORKFLOW_HUB_URL={b.base}" in env_text()
                   and c_ok == 0 and via_env.get("http") == 200 and reuse == 403 and reuse_out.get("error_code") == "invite_used")
            _record("case 7 (HTTP 경로 — 초대 코드 · 실패 복구 · 옮겨진 뒤 같은 토큰 · 봉인 · env 주소 · 코드 1회)", ok7,
                    f"wrong={m1}/{wrong} a={a_after_wrong} exp={m2}/{expired.get('target')} a={a_after_exp} presealed={m3}/{still} "
                    f"move={m4}/{moved.get('status')} diff={diff_r} a_sealed={a_sealed} via_env={c_ok}/{via_env.get('http')} reuse={reuse}/{reuse_out}")
        finally:
            a.stop()
            b.stop()
    print(f"PASS {len(_passes)} · FAIL {len(_failures)}")
    for f in _failures:
        print(f"  FAIL {f}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
