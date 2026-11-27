"""허브 판정 — 1.x 와 **같은 함수**를 데이터로 부른다 (hub_spec §1-6 · §2.2, 요구 R0.7 · R5.5 · R5.6 · R5.8 · R9).

부르는 1.x 함수:
    계획      ``plan_claims.parse_plan`` · ``lint_plan`` · ``lint_errors`` · ``compute_states`` · ``open_decision_ids``
    응답      ``plan_responses.parse_response`` · ``qualify`` · ``as_response`` — 순서 ``has_error_rules`` → ``qualify`` → ``compute_states``
    게이트    ``backlog_update.enforce_plan_contract`` (응답 공급 · 대기 수 · 줄 수 콜백 입구) ·
              ``planning.determine_conservative_task_status``
    로드맵    ``state.roadmap.assemble_roadmap`` · ``index_text_is_draft`` · ``judge_wbs`` · ``derive_state``

허브에는 작업 트리가 없다: L5(줄 수) 는 공급하지 않고 결과에 '미측정' 으로 싣는다 · 산출물 존재는
재지 않고 issue ``deliverables_unmeasured`` 로 싣는다 — 통과로 세지 않는다 (hub_spec §1-9).
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Callable

from workflow_kit.common import plan_claims, plan_responses
from workflow_kit.common.planning import determine_conservative_task_status
from workflow_kit.common.project_docs import task_label
from workflow_kit.common.schemas.roadmap import Roadmap, RoadmapIssue, TaskWbsLink
from workflow_kit.common.state import roadmap as rm
from workflow_kit.hub.errors import HubError, forbidden, invalid_field
from workflow_kit.hub.store import Ctx, Store, _iso, _json, scan_secrets

#: 작업 트리가 없다는 표식 — enforce_plan_contract 의 workspace_root 자리 (파일을 열지 않는다).
_NO_TREE = Path("/nonexistent-hub-workspace")
INDEX = "index.md"
_MILESTONE_NAME = re.compile(r"^M-\d{3}-[a-z0-9][a-z0-9-]*\.md$")
L5_UNMEASURED = "L5 (계획 파일의 줄 수) 는 허브에 작업 트리가 없어 재지 않았다 — 미측정"


def _gate(code: str, message: str, warnings: list[str] | None = None) -> HubError:
    return HubError(422, "gate_denied", message, {"kit_error_code": code, "warnings": warnings or []})


def task_lines(plan_md: str, fields: dict[str, Any]) -> tuple[list[str], int]:
    """1.x task 파일 꼴의 줄 — Plan 절 원문 + 완료 기준. (줄 목록, 덧붙인 꼬리 줄 수)."""
    lines = plan_md.splitlines()
    tail = [f"- {task_label('done_criteria')}: {c}" for c in fields.get("done_criteria") or []]
    return lines + tail, len(tail)


class Judge:
    def __init__(self, store: Store) -> None:
        self.store = store

    # --- 결정 응답 -----------------------------------------------------------------

    @staticmethod
    def _responses(conn: sqlite3.Connection, project_id: str, task_id: str) -> Callable[[plan_claims.Plan], tuple[plan_claims.Response, ...]]:
        rows = [r["body"] for r in conn.execute(
            "SELECT body FROM plan_response WHERE project_id = ? AND task_id = ? ORDER BY received_at, rowid",
            (project_id, task_id))]

        def provider(target: plan_claims.Plan) -> tuple[plan_claims.Response, ...]:
            out = []
            for body in rows:
                parsed = plan_responses.parse_response(body.encode("utf-8"))
                if plan_responses.qualify(parsed, target, task_id).eligible:
                    out.append(plan_responses.as_response(parsed))
            return tuple(out)

        return provider

    def enforce(self, conn: sqlite3.Connection, project_id: str, task_id: str, *, new_plan_md: str,
                previous_plan_md: str | None, fields: dict[str, Any], requested_status: str | None,
                status: str, current_status: str | None, decision_states: list[str], removal_note: str | None,
                creating: bool) -> tuple[str, list[str]]:
        """계획 계약 — 린트 · 결정 상태 재계산 · 상태 전이 게이트. (고친 plan_md, 경고)."""
        from workflow_kit.tools.backlog_update import enforce_plan_contract

        lines, tail = task_lines(new_plan_md, fields)
        previous = task_lines(previous_plan_md, fields)[0] if previous_plan_md is not None else None
        plan_changed = previous_plan_md is None or previous_plan_md != new_plan_md
        if plan_changed and new_plan_md.strip():
            # 계획을 바꾸는 쓰기는 오류 규칙이면 거부 (1.x 의 --plan-claim · --plan-decision 과 같은 판정)
            issues = plan_claims.lint_plan(plan_claims.parse_plan(lines), criteria=list(fields.get("done_criteria") or []),
                                           file_line_count=None)
            errors = plan_claims.lint_errors(issues)
            if errors:
                rendered = [i.render() for i in errors]
                raise _gate("plan_lint_error", f"주장 · 결정이 오류 규칙을 어긴다 ({len(errors)}건) — " + " / ".join(rendered),
                            rendered)
        verdict = enforce_plan_contract(
            lines, previous_lines=previous, plan_claim_args=[], plan_decision_args=[],
            decision_state_args=decision_states, replace_fields=set(), requested_status=requested_status,
            status=status, current_status=current_status, removal_note=removal_note, workspace_root=_NO_TREE,
            creating=creating, task_id=task_id, responses_provider=self._responses(conn, project_id, task_id),
            pending_count=0, line_counter=None,
        )
        if verdict.error_code:
            raise _gate(verdict.error_code, verdict.error or verdict.error_code, verdict.warnings)
        out = verdict.lines[: len(verdict.lines) - tail] if tail else verdict.lines
        warnings = list(verdict.warnings)
        if plan_claims.parse_plan(lines).claims:
            warnings.append(L5_UNMEASURED)
        return "\n".join(out) + ("\n" if new_plan_md.endswith("\n") else ""), warnings

    # --- WBS 게이트 · 로드맵 --------------------------------------------------------

    @staticmethod
    def roadmap(conn: sqlite3.Connection, project_id: str) -> tuple[Roadmap | None, bool, list[RoadmapIssue]]:
        docs = {r["path"]: r["body_md"] for r in conn.execute(
            "SELECT path, body_md FROM roadmap_doc WHERE project_id = ?", (project_id,))}
        if INDEX not in docs:
            return None, False, []
        texts = {k: v for k, v in docs.items() if k != INDEX}
        roadmap, issues = rm.assemble_roadmap(docs[INDEX], texts)
        return roadmap, rm.index_text_is_draft(docs[INDEX]), issues

    def wbs_gate(self, conn: sqlite3.Connection, project_id: str, wbs: str | None, exempt_reason: str | None) -> str:
        roadmap, draft, _ = self.roadmap(conn, project_id)
        verdict = rm.judge_wbs(roadmap, is_draft=draft, wbs=wbs or None, exempt_reason=exempt_reason)
        if not verdict.allowed:
            # 1.x 판정 문구는 CLI 플래그(--wbs)로 말한다 — 허브 도구 인자로도 말한다 (테스트베드 실측: 사유만 주고 거절됨)
            hint = ' 허브 도구에서는 wbs="M-NNN/WBS-N.N", 로드맵 밖이면 wbs="exempt" 와 wbs_exempt_reason 을 함께 준다.'
            if exempt_reason and not wbs:
                hint += " (wbs_exempt_reason 만 왔다 — wbs=\"exempt\" 가 함께 있어야 로드맵 밖 선언이다)"
            raise _gate("wbs_gate_denied", f"WBS 게이트 거부 ({verdict.code}): {verdict.detail}{hint}", [verdict.code])
        return verdict.code

    def roadmap_state(self, ctx: Ctx) -> dict[str, Any]:
        p = self.store._need_callsign(ctx)
        with self.store.read() as conn:
            roadmap, _, issues = self.roadmap(conn, p.project_id or "")
            if roadmap is None:
                return {"roadmap": None, "reason": "로드맵이 없다 (index.md 없음)"}
            links = [TaskWbsLink(task_id=r["id"], task_status=r["status"], wbs_ref=r["wbs"],
                                 exempt_reason=r["wbs_exempt_reason"], source_path=r["id"])
                     for r in conn.execute("SELECT id, status, wbs, wbs_exempt_reason FROM task WHERE project_id = ? AND wbs != ''",
                                           (p.project_id,))]
        declared = sorted({d for m in roadmap.milestones for d in m.deliverables})
        if declared:
            issues.append(RoadmapIssue(code="deliverables_unmeasured",
                                       detail=f"허브는 저장소를 보지 않아 산출물 {len(declared)}개의 존재를 재지 않았다 — 미측정",
                                       where=INDEX))
        state = rm.derive_state(roadmap, links, _NO_TREE, issues, deliverable_exists=lambda _d: True,
                                generated_at=ctx.now.strftime("%Y-%m-%d"))
        return {"roadmap_state": state.model_dump(mode="json")}

    def roadmap_put(self, ctx: Ctx, path: str, expected_version: int | None, body: str) -> dict[str, Any]:
        p = self.store._need_callsign(ctx)
        scan_secrets(body, "body")
        if path != INDEX and not _MILESTONE_NAME.match(path):
            raise invalid_field("path", "index.md 또는 M-NNN-<slug>.md")
        if path == INDEX:
            _, issues = rm.parse_index_text(body)
        else:
            milestone, issues = rm.parse_milestone_text(body, path)
            if milestone is None:
                detail = [f"{i.code}: {i.detail}" for i in issues]
                raise HubError(400, "invalid_field", "마일스톤을 읽을 수 없어요 — " + " / ".join(detail),
                               {"field": "body", "issues": detail})
        with self.store.write() as conn:
            row = conn.execute("SELECT body_md, version FROM roadmap_doc WHERE project_id = ? AND path = ?",
                               (p.project_id, path)).fetchone()
            current = row["version"] if row else 0
            if expected_version is not None and expected_version != current:
                raise HubError(409, "version_conflict", f"version 이 달라요 — 지금 {current}",
                               {"current_version": current, "current": {"path": path, "body": row["body_md"] if row else None}})
            conn.execute(
                "INSERT INTO roadmap_doc (project_id, path, body_md, version, updated_by, updated_at) VALUES (?, ?, ?, 1, ?, ?) "
                "ON CONFLICT(project_id, path) DO UPDATE SET body_md = excluded.body_md, version = roadmap_doc.version + 1, "
                "updated_by = excluded.updated_by, updated_at = excluded.updated_at",
                (p.project_id, path, body, p.callsign, _iso(ctx.now)))
            self.store._event(conn, ctx, p.project_id, "roadmap", path, "put",
                              {"version": current}, {"version": current + 1})
        return {"path": path, "version": current + 1, "issues": [f"{i.code}: {i.detail}" for i in issues]}

    def roadmap_get(self, ctx: Ctx) -> dict[str, Any]:
        p = self.store._need_callsign(ctx)
        with self.store.read() as conn:
            docs = [dict(r) for r in conn.execute(
                "SELECT path, body_md, version, updated_by, updated_at FROM roadmap_doc WHERE project_id = ? ORDER BY path",
                (p.project_id,))]
        return {"docs": docs}

    # --- task 쓰기 경로 ------------------------------------------------------------

    def prepare_create(self, conn: sqlite3.Connection, project_id: str, task_id: str,
                       values: dict[str, Any]) -> dict[str, Any]:
        """task 생성 직전 (같은 트랜잭션) — WBS 게이트 · 계획 계약 (R5.5 · R5.6)."""
        self.wbs_gate(conn, project_id, values.get("wbs"), values.get("wbs_exempt_reason"))
        out = dict(values)
        plan_md = values.get("plan_md", "")
        if plan_md.strip():
            status = values.get("status", "planned")
            out["plan_md"], _ = self.enforce(conn, project_id, task_id, new_plan_md=plan_md, previous_plan_md=None,
                                             fields=values.get("fields") or {}, requested_status=status, status=status,
                                             current_status=None, decision_states=[], removal_note=None, creating=True)
        return out

    def prepare_update(self, conn: sqlite3.Connection, project_id: str, before: dict[str, Any], values: dict[str, Any],
                       decision_states: dict[str, str], note: str | None) -> dict[str, Any]:
        """task 갱신 직전 (같은 트랜잭션)."""
        out = dict(values)
        if "wbs" in values or "wbs_exempt_reason" in values:
            self.wbs_gate(conn, project_id, values.get("wbs", before["wbs"]),
                          values.get("wbs_exempt_reason", before["wbs_exempt_reason"]))
        new_plan = values.get("plan_md", before["plan_md"])
        status_change = "status" in values and values["status"] != before["status"]
        if (new_plan.strip() or before["plan_md"].strip()) and ("plan_md" in values or decision_states or status_change):
            fields = {**before["fields"], **(values.get("fields") or {})}
            out["plan_md"], _ = self.enforce(
                conn, project_id, before["id"], new_plan_md=new_plan, previous_plan_md=before["plan_md"], fields=fields,
                requested_status=values.get("status"), status=values.get("status", before["status"]),
                current_status=before["status"], decision_states=[f"{k}={v}" for k, v in decision_states.items()],
                removal_note=note, creating=False)
        return out

    def task_close(self, ctx: Ctx, task_id: str, expected_version: int, validation_result: str,
                   request_id: str | None = None) -> dict[str, Any]:
        p = self.store._need_callsign(ctx)
        pid = p.project_id or ""
        scan_secrets(validation_result, "validation_result")

        def do(conn: sqlite3.Connection) -> dict[str, Any]:
            before = self.store._get_task(conn, pid, task_id)
            if before["version"] != expected_version:
                raise HubError(409, "version_conflict", f"version 이 달라요 — 지금 {before['version']}",
                               {"current_version": before["version"], "current": before})
            status, warns = determine_conservative_task_status("done", validation_result, "update", before["status"],
                                                               recorded_validation=None)
            if status != "done":
                raise _gate("validation_result_required", "done 은 검증 결과가 있어야 닫힌다 — 검증하지 않은 결과를 done 으로 두지 않는다",
                            warns)
            tests = before["fields"].get("tests", [])
            pending = [test.get("id", "?") for test in tests if test.get("required") and
                       (not test.get("runs") or test["runs"][-1].get("status") != "passed")]
            if pending:
                raise _gate("required_tests_not_passed", "필수 테스트의 최신 실행 결과가 passed 여야 닫힌다",
                            [f"미통과 필수 테스트: {', '.join(pending)}"])
            fields = dict(before["fields"])
            fields["validation_result"] = validation_result
            new_plan, warnings = self.enforce(conn, pid, task_id, new_plan_md=before["plan_md"],
                                              previous_plan_md=before["plan_md"], fields=fields, requested_status="done",
                                              status="done", current_status=before["status"], decision_states=[],
                                              removal_note=None, creating=False)
            conn.execute(
                "UPDATE task SET status = 'done', plan_md = ?, fields_json = ?, version = version + 1, updated_at = ? "
                "WHERE project_id = ? AND id = ? AND version = ?",
                (new_plan, _json(fields), _iso(ctx.now), pid, task_id, before["version"]))
            after = self.store._get_task(conn, pid, task_id)
            self.store._event(conn, ctx, pid, "task", task_id, "close", {"status": before["status"]},
                              {"status": "done", "validation_result": validation_result})
            return {"task": after, "warnings": warnings}

        return self.store.idempotent(ctx, request_id, do)

    # --- 결정 응답 수신 (R5.8) --------------------------------------------------------

    def plan_respond(self, ctx: Ctx, task_id: str, body: str) -> dict[str, Any]:
        p = self.store._need_callsign(ctx)
        pid = p.project_id or ""
        # 결정에 답하는 것은 승인된 사람 콜사인이고, 응답자는 그 콜사인이다 (소유자 2026-11-21 · 요구 R4.6) —
        # 에이전트가 자기 계획의 결정을 닫거나 남의 이름으로 답하지 못하게.
        if p.callsign_kind != "human" or not p.human_approved:
            raise forbidden("결정 응답은 승인된 human 콜사인만 보내요")
        data = body.encode("utf-8")
        parsed = plan_responses.parse_response(data)
        if parsed.responder != p.callsign:
            raise HubError(403, "forbidden", f"responder 가 이 콜사인({p.callsign})이 아니에요: {parsed.responder!r}",
                           {"field": "responder"})
        with self.store.write() as conn:
            task = self.store._get_task(conn, pid, task_id)
            plan = plan_claims.parse_plan(task_lines(task["plan_md"], task["fields"])[0])
            dup = conn.execute("SELECT 1 FROM plan_response WHERE project_id = ? AND body_sha256 = ?",
                               (pid, parsed.content_sha256)).fetchone()
            if dup:
                return {"task_id": task_id, "accepted": True, "duplicate": True}
            if plan_claims.has_error_rules(plan):
                raise _gate("plan_lint_error", "task 계획이 오류 규칙을 어긴 상태라 응답을 받을 수 없다 (자격 0 단계)")
            verdict = plan_responses.qualify(parsed, plan, task_id)
            if not verdict.eligible:
                raise HubError(422, "response_ineligible", f"자격 {verdict.stage} 단계에서 거부: {verdict.reason}",
                               {"stage": verdict.stage, "reason": verdict.reason})
            conn.execute(
                "INSERT INTO plan_response (project_id, task_id, body, body_sha256, received_at, responder) VALUES (?, ?, ?, ?, ?, ?)",
                (pid, task_id, body, parsed.content_sha256, parsed.received_at, parsed.responder))
            new_plan, warnings = self.enforce(conn, pid, task_id, new_plan_md=task["plan_md"], previous_plan_md=task["plan_md"],
                                              fields=task["fields"], requested_status=None, status=task["status"],
                                              current_status=task["status"], decision_states=[], removal_note=None,
                                              creating=False)
            if new_plan != task["plan_md"]:
                conn.execute("UPDATE task SET plan_md = ?, version = version + 1, updated_at = ? WHERE project_id = ? AND id = ?",
                             (new_plan, _iso(ctx.now), pid, task_id))
            self.store._event(conn, ctx, pid, "task", task_id, "plan_response", None,
                              {"responder": parsed.responder, "sha256": parsed.content_sha256})
            after = self.store._get_task(conn, pid, task_id)
        return {"task_id": task_id, "accepted": True, "duplicate": False, "task": after, "warnings": warnings}

    def plan_status(self, ctx: Ctx, task_id: str) -> dict[str, Any]:
        p = self.store._need_reader(ctx)
        pid = p.project_id or ""
        with self.store.read() as conn:
            task = self.store._get_task(conn, pid, task_id)
            plan = plan_claims.parse_plan(task_lines(task["plan_md"], task["fields"])[0])
            responses = self._responses(conn, pid, task_id)(plan)
        result = plan_claims.compute_states(plan, responses)
        return {"task_id": task_id, "plan_digest": plan_claims.plan_digest(plan), "states": result.states,
                "open_decisions": plan_claims.open_decision_ids(plan, responses), "responses": len(responses)}

