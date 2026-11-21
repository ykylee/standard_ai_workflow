#!/usr/bin/env python3
"""허브 판정 (M-035 WBS-35.2 · 35.3) — 1.x 와 **같은 판정**을 내는지 대조한다.

정본: ``core/hub_spec.md`` §1-6 · §2.2 (요구 R0.7 · R5.5 · R5.6 · R5.8 · R9). 1.x 쪽은 같은 입력을
1.x 함수(``enforce_plan_contract`` · ``evaluate_wbs_gate`` · ``derive_state``)에 저장소 파일로 넣고,
허브 쪽은 실제 허브 프로세스에 HTTP 로 넣는다. 로드맵 fixture 는 ``check_roadmap_gates`` 의 것을 그대로 쓴다.

1. WBS 게이트 대조 — 1.x 매트릭스(거부 6 · 허용 2 · done 역행 · parallel_allowed · draft)와 같은 허용 · 코드
2. 로드맵 쓰기 — 스키마 오류는 필드 · 제약(200자)과 함께 거절 · 낡은 version 409
3. 진척 파생 대조 — 같은 로드맵 · 같은 task 링크에서 1.x derive_state 와 마일스톤별 진척 · 파생 상태가 같다 · 산출물은 미측정 issue
4. done 게이트 대조 — 열린 결정 · 검증 결과 없음은 1.x 와 같이 거부, 답한 뒤 닫힘 (kit error_code 일치)
5. 계획 린트 — 오류 규칙 계획은 1.x 와 같은 plan_lint_error 로 생성 거부
6. 결정 응답 — 자격 있는 응답만 반영(answered) · 다른 task · 옛 계획 응답은 단계와 함께 거부 · 같은 응답 두 번은 한 번 반영
7. 열린 결정을 사유 없이 걷으면 1.x 와 같이 거부 (decision_removal_needs_note)
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 300

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/check_hub_core.py",
    "workflow-source/tests/check_roadmap_gates.py",
)

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_roadmap_gates as rg  # noqa: E402
from check_hub_core import Hub  # noqa: E402
from workflow_kit.common import plan_claims, plan_responses  # noqa: E402
from workflow_kit.common.planning import determine_conservative_task_status  # noqa: E402
from workflow_kit.common.schemas.roadmap import TaskWbsLink  # noqa: E402
from workflow_kit.common.state import roadmap as rm  # noqa: E402
from workflow_kit.tools.backlog_update import enforce_plan_contract  # noqa: E402

_failures: list[str] = []
_passes: list[str] = []

PLAN_OPEN = (
    "- Claims: C1 허브는 1.x 와 같은 판정을 낸다\n"
    "- Decisions: D1 [C1] 어느 저장소를 쓰는가? | default: sqlite | options: sqlite = 파일 하나; pg = 서버 | state: proposed\n"
)
PLAN_BAD = "- Claims: C1 주장\n- Decisions: D1 [C9] 없는 주장을 가리킨다 | default: a | options: a = 가; b = 나 | state: proposed\n"
CRITERIA = ["판정이 같다"]


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


def _roadmap_docs(root: Path) -> dict[str, str]:
    d = root / "ai-workflow" / "memory" / "active" / "roadmap"
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(d.glob("*.md"))}


def _hub_project(hub: Hub, name: str) -> str:
    st, reg, _ = hub.call("hub_project_register", {"remote_url": f"git@github.com:acme/{name}.git", "display_name": name,
                                                     "callsign": "agent-a", "kind": "human"})
    assert st == 200, reg
    return str(reg["token"])


def _put_roadmap(hub: Hub, tok: str, docs: dict[str, str]) -> None:
    for path in sorted(docs, key=lambda n: (n != "index.md", n)):
        st, out, _ = hub.call("hub_roadmap_put", {"path": path, "body": docs[path]}, tok)
        assert st == 200, (path, out)


def _hub_gate(hub: Hub, tok: str, wbs: str | None, reason: str | None) -> tuple[bool, str]:
    args: dict[str, Any] = {"title": "게이트 대조"}
    if wbs is not None:
        args["wbs"] = wbs
    if reason is not None:
        args["wbs_exempt_reason"] = reason
    st, out, _ = hub.call("hub_task_create", args, tok)
    if st == 200:
        roadmap_state = hub.call("hub_roadmap_state", {}, tok)[1]
        return True, "linked_or_allowed" if roadmap_state is not None else "?"
    return False, (out.get("detail", {}).get("warnings") or ["?"])[0]


def case_1_wbs_parity(hub: Hub, tmp: Path) -> None:
    problems = []
    scenarios: list[tuple[str, dict[str, Any], list[tuple[str | None, str | None]]]] = [
        ("기본", {}, [(None, None), ("exempt", None), ("banana", None), ("M-001/WBS-1.9", None), ("M-001/WBS-1.1", None),
                     ("M-002/WBS-2.1", None), ("M-001/WBS-1.2", None), ("exempt", "로드맵 밖 긴급 수리")]),
        ("done 역행", {"m1_status": "done"}, [("M-001/WBS-1.2", None), ("M-002/WBS-2.1", None)]),
        ("병행 허용", {"m2_parallel": "M-001"}, [("M-002/WBS-2.1", None)]),
        ("draft", {"draft": True}, [(None, None)]),
    ]
    for i, (label, opts, probes) in enumerate(scenarios):
        root = tmp / f"wbs-{i}"
        draft = opts.pop("draft", False)
        rg._fixture(root, **opts)
        if draft:
            idx = root / "ai-workflow" / "memory" / "active" / "roadmap" / "index.md"
            idx.write_text(idx.read_text(encoding="utf-8").replace("# Roadmap — fixture\n", "# Roadmap — fixture\n\n- 상태: draft\n", 1),
                           encoding="utf-8")
        tok = _hub_project(hub, f"wbs-{i}")
        _put_roadmap(hub, tok, _roadmap_docs(root))
        for wbs, reason in probes:
            v1 = rm.evaluate_wbs_gate(root, wbs=wbs, exempt_reason=reason)
            allowed, code = _hub_gate(hub, tok, wbs, reason)
            if allowed != v1.allowed or (not allowed and code != v1.code):
                problems.append(f"{label} {wbs!r}: 1.x {v1.allowed}/{v1.code} ≠ 허브 {allowed}/{code}")
    _record("case 1 (WBS 게이트 — 1.x 매트릭스와 같은 판정)", not problems, "; ".join(problems))


def case_2_roadmap_write(hub: Hub, tmp: Path) -> None:
    root = tmp / "rm-write"
    rg._fixture(root)
    docs = _roadmap_docs(root)
    tok = _hub_project(hub, "rm-write")
    _put_roadmap(hub, tok, docs)
    name = next(n for n in docs if n.startswith("M-001"))
    long_title = docs[name].replace("title: 컨셉", "title: " + "가" * 201)
    st1, bad, _ = hub.call("hub_roadmap_put", {"path": name, "body": long_title, "expected_version": 1}, tok)
    st2, stale, _ = hub.call("hub_roadmap_put", {"path": name, "body": docs[name], "expected_version": 7}, tok)
    st3, okv, _ = hub.call("hub_roadmap_put", {"path": name, "body": docs[name], "expected_version": 1}, tok)
    st4, badname, _ = hub.call("hub_roadmap_put", {"path": "../x.md", "body": "x"}, tok)
    ok = (st1 == 400 and bad.get("error_code") == "invalid_field" and "200" in bad.get("message", "")
          and st2 == 409 and stale["detail"]["current_version"] == 1 and st3 == 200 and okv.get("version") == 2
          and st4 == 400)
    _record("case 2 (로드맵 쓰기 — 스키마 원인 · 409 · 경로)", ok,
            f"{st1}/{bad.get('message', '')[:80]} {st2} {st3}/{okv.get('version')} {st4}")


def case_3_derive_parity(hub: Hub, tmp: Path) -> None:
    root = tmp / "derive"
    rg._fixture(root, m2_parallel="M-001")
    tok = _hub_project(hub, "derive")
    docs = _roadmap_docs(root)
    _put_roadmap(hub, tok, docs)
    created = []
    for wbs in ("M-001/WBS-1.2", "M-001/WBS-1.1.1", "M-002/WBS-2.1"):
        st, out, _ = hub.call("hub_task_create", {"title": f"t {wbs}", "wbs": wbs}, tok)
        created.append((out["task"]["id"], wbs))
    tid0 = created[0][0]
    hub.call("hub_task_close", {"id": tid0, "expected_version": 1, "validation_result": "검사 green"}, tok)
    hub_state = hub.call("hub_roadmap_state", {}, tok)[1]["roadmap_state"]
    roadmap, issues = rm.load_roadmap(root)
    assert roadmap is not None
    links = [TaskWbsLink(task_id=t, task_status="done" if t == tid0 else "planned", wbs_ref=w, source_path=t) for t, w in created]
    v1 = rm.derive_state(roadmap, links, root, issues).model_dump(mode="json")
    pick = lambda s: [(m["id"], m["derived_status"], m["progress"], m["total_leaves"], m["done_leaves"]) for m in s["milestones"]]  # noqa: E731
    same = pick(v1) == pick(hub_state)
    # 산출물을 선언하면 허브는 미측정 issue 를 싣는다
    name = next(n for n in docs if n.startswith("M-002"))
    hub.call("hub_roadmap_put", {"path": name, "body": docs[name].replace("deliverables: []", "deliverables: [docs/x.md]"),
                                  "expected_version": 1}, tok)
    after = hub.call("hub_roadmap_state", {}, tok)[1]["roadmap_state"]
    unmeasured = any(i["code"] == "deliverables_unmeasured" for i in after["issues"])
    _record("case 3 (진척 파생 — 1.x derive_state 와 같은 값 · 산출물 미측정)", same and unmeasured and after.get("schema_version") == 1,
            f"1.x={pick(v1)} hub={pick(hub_state)} unmeasured={unmeasured}")


def _v1_done(plan_md: str, criteria: list[str], validation: str | None, decision_states: list[str]) -> str | None:
    status, _ = determine_conservative_task_status("done", validation, "update", "in_progress")
    if status != "done":
        return "validation_result_required"
    lines = plan_md.splitlines() + [f"- Completion criteria: {c}" for c in criteria]
    v = enforce_plan_contract(lines, previous_lines=lines, plan_claim_args=[], plan_decision_args=[],
                              decision_state_args=decision_states, replace_fields=set(), requested_status="done",
                              status="done", current_status="in_progress", removal_note=None,
                              workspace_root=Path("/nonexistent"), creating=False, task_id="T", pending_count=0,
                              line_counter=None)
    return v.error_code


def _hub_task(hub: Hub, tok: str, plan: str) -> tuple[str, int]:
    st, out, _ = hub.call("hub_task_create", {"title": "계획 task", "plan_md": plan, "status": "in_progress",
                                                "fields": {"done_criteria": CRITERIA}}, tok)
    assert st == 200, out
    return out["task"]["id"], out["task"]["version"]


def case_4_done_parity(hub: Hub) -> None:
    tok = _hub_project(hub, "done")
    tid, ver = _hub_task(hub, tok, PLAN_OPEN)
    st1, open_, _ = hub.call("hub_task_close", {"id": tid, "expected_version": ver, "validation_result": "green"}, tok)
    st2, novalid, _ = hub.call("hub_task_close", {"id": tid, "expected_version": ver, "validation_result": ""}, tok)
    st3, upd, _ = hub.call("hub_task_update", {"id": tid, "expected_version": ver, "decision_states": {"D1": "answered:pg"}}, tok)
    ver2 = upd.get("task", {}).get("version", ver)
    st4, closed, _ = hub.call("hub_task_close", {"id": tid, "expected_version": ver2, "validation_result": "green"}, tok)
    v1_open = _v1_done(PLAN_OPEN, CRITERIA, "green", [])
    v1_novalid = _v1_done(PLAN_OPEN, CRITERIA, None, [])
    v1_answered = _v1_done(PLAN_OPEN, CRITERIA, "green", ["D1=answered:pg"])
    hub_open = open_.get("detail", {}).get("kit_error_code")
    hub_novalid = novalid.get("detail", {}).get("kit_error_code")
    ok = (st1 == 422 and hub_open == v1_open == "open_decisions"
          and st2 == 422 and hub_novalid == v1_novalid == "validation_result_required"
          and st3 == 200 and "state: answered:pg" in upd["task"]["plan_md"]
          and st4 == 200 and closed["task"]["status"] == "done" and v1_answered is None
          and any("미측정" in w for w in closed.get("warnings", [])))
    _record("case 4 (done 게이트 — 1.x 와 같은 kit error_code)", ok,
            f"open {hub_open}/{v1_open} novalid {hub_novalid}/{v1_novalid} answer {st3} close {st4}/{v1_answered} warn={closed.get('warnings')}")


def case_5_lint(hub: Hub) -> None:
    tok = _hub_project(hub, "lint")
    st, out, _ = hub.call("hub_task_create", {"title": "나쁜 계획", "plan_md": PLAN_BAD, "fields": {"done_criteria": CRITERIA}}, tok)
    lines = PLAN_BAD.splitlines() + [f"- Completion criteria: {c}" for c in CRITERIA]
    v1 = enforce_plan_contract(lines, previous_lines=None, plan_claim_args=["x"], plan_decision_args=["x"],
                               decision_state_args=[], replace_fields=set(), requested_status="planned", status="planned",
                               current_status=None, removal_note=None, workspace_root=Path("/nonexistent"),
                               creating=True, task_id="T", pending_count=0, line_counter=None)
    _, listing, _ = hub.call("hub_task_list", {}, tok)
    ok = st == 422 and out["detail"]["kit_error_code"] == v1.error_code == "plan_lint_error" and listing["tasks"] == []
    _record("case 5 (계획 린트 — 오류 규칙 계획 생성 거부)", ok, f"{st} {out.get('detail')} 1.x={v1.error_code} tasks={len(listing['tasks'])}")


def case_6_responses(hub: Hub) -> None:
    tok = _hub_project(hub, "resp")
    tid, ver = _hub_task(hub, tok, PLAN_OPEN)
    other, _ = _hub_task(hub, tok, PLAN_OPEN)
    plan = plan_claims.parse_plan((PLAN_OPEN.splitlines() + [f"- Completion criteria: {c}" for c in CRITERIA]))
    body = plan_responses.render_response(task_id=tid, plan=plan, responder="owner", received_at="2026-11-21T09:00:00+09:00",
                                          values={"D1": "pg"}, opened={"D1": True})
    wrong_task = plan_responses.render_response(task_id=other + "-x", plan=plan, responder="owner",
                                                received_at="2026-11-21T09:00:00+09:00", values={"D1": "pg"})
    s1, wrong, _ = hub.call("hub_plan_respond", {"task_id": tid, "body": wrong_task}, tok)
    s2, ok_resp, _ = hub.call("hub_plan_respond", {"task_id": tid, "body": body}, tok)
    s3, dup, _ = hub.call("hub_plan_respond", {"task_id": tid, "body": body}, tok)
    _, status, _ = hub.call("hub_plan_status", {"task_id": tid}, tok)
    _, events, _ = hub.call("hub_events", {"target_kind": "task", "target_id": tid}, tok)
    n_resp = sum(1 for e in events["events"] if e["op"] == "plan_response")
    # 옛 계획 응답: 계획을 바꾼 뒤 같은 body 를 다른 task 에 — 대신 계획을 바꾼 task 에 옛 응답
    cur = hub.call("hub_task_get", {"id": other}, tok)[1]["task"]
    hub.call("hub_task_update", {"id": other, "expected_version": cur["version"],
                                  "values": {"plan_md": PLAN_OPEN.replace("1.x 와 같은 판정을 낸다", "같은 판정을 낸다 (고침)")}}, tok)
    old = plan_responses.render_response(task_id=other, plan=plan, responder="owner", received_at="2026-11-21T09:00:00+09:00",
                                         values={"D1": "pg"})
    s4, stale, _ = hub.call("hub_plan_respond", {"task_id": other, "body": old}, tok)
    ok = (s1 == 422 and wrong["detail"]["stage"] == 3 and s2 == 200 and ok_resp.get("duplicate") is False
          and s3 == 200 and dup.get("duplicate") is True and n_resp == 1
          and status["open_decisions"] == [] and status["states"].get("D1", "").startswith("changed")
          and "state: changed" in ok_resp["task"]["plan_md"]
          and s4 == 422 and stale["detail"]["stage"] == 4)
    _record("case 6 (결정 응답 — 자격 판정 뒤 반영 · 단계별 거부 · 중복 한 번)", ok,
            f"wrong={s1}/{wrong.get('detail')} ok={s2} dup={s3}/{dup.get('duplicate')} n={n_resp} status={status} stale={s4}/{stale.get('detail')}")


def case_7_removal(hub: Hub) -> None:
    tok = _hub_project(hub, "removal")
    tid, ver = _hub_task(hub, tok, PLAN_OPEN)
    no_decisions = "- Claims: C1 허브는 1.x 와 같은 판정을 낸다\n"
    s1, denied, _ = hub.call("hub_task_update", {"id": tid, "expected_version": ver, "values": {"plan_md": no_decisions}}, tok)
    s2, allowed, _ = hub.call("hub_task_update", {"id": tid, "expected_version": ver, "values": {"plan_md": no_decisions},
                                                   "note": "소유자와 대화로 확인 — 결정 불필요"}, tok)
    ok = (s1 == 422 and denied["detail"]["kit_error_code"] == "decision_removal_needs_note" and s2 == 200
          and "Decisions" not in allowed["task"]["plan_md"])
    _record("case 7 (열린 결정을 사유 없이 걷으면 거부)", ok, f"{s1}/{denied.get('detail')} {s2}")


def main() -> int:
    print("=== 허브 판정 — 1.x 대조 (M-035) ===")
    with tempfile.TemporaryDirectory(prefix="hubjudge-") as d:
        tmp = Path(d)
        hub = Hub(tmp / "hub.db")
        try:
            for fn, args in ((case_1_wbs_parity, (hub, tmp)), (case_2_roadmap_write, (hub, tmp)),
                             (case_3_derive_parity, (hub, tmp)), (case_4_done_parity, (hub,)), (case_5_lint, (hub,)),
                             (case_6_responses, (hub,)), (case_7_removal, (hub,))):
                try:
                    fn(*args)  # type: ignore[operator]
                except Exception as exc:  # noqa: BLE001 — 예외도 case 판정으로 남긴다
                    _record(f"{fn.__name__} (예외)", False, repr(exc))
        finally:
            err = hub.stop()
            if _failures:
                print("  --- 허브 stderr ---\n" + err[-2000:])
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    raise SystemExit(main())
