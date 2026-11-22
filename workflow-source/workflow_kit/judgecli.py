"""언어 중립 판정 CLI 입구 — ``python -m workflow_kit.judgecli <op> [--batch]`` (``hub_go_spec.md`` §3 · §4).

``hub-go`` 의 ``workflow-hub judge <op>`` 과 같은 입력·출력·오류 형식(``judge/1``)을 쓴다.
여기의 함수들은 DB · 시계 · 작업 트리를 읽지 않는 순수 판정 함수만 부른다.
"""

from __future__ import annotations

import base64
import binascii
import json
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, cast

from workflow_kit.common import plan_claims, plan_responses, planning, project_docs
from workflow_kit.common.markdown import iter_markdown_link_targets
from workflow_kit.common.paths import (
    HANDOFF_FILENAME,
    path_in_active,
    workflow_memory_dir,
)
from workflow_kit.common.schemas.roadmap import RoadmapIssue, TaskWbsLink
from workflow_kit.common.state import roadmap as rm
from workflow_kit.common.state.builder import build_workflow_state_payload
from workflow_kit.common.state.memory_index import (
    entry_pointers,
    load_memory_index_at,
    memory_index_root,
)

PROTOCOL = "judge/1"


class JudgeCLIError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _require_str(obj: dict[str, Any], key: str) -> str:
    val = obj.get(key)
    if not isinstance(val, str):
        raise JudgeCLIError("invalid_input", f"{key} 는 문자열이어야 한다")
    return val


def _optional_str(obj: dict[str, Any], key: str) -> str | None:
    if key not in obj or obj[key] is None:
        return None
    val = obj[key]
    if not isinstance(val, str):
        raise JudgeCLIError("invalid_input", f"{key} 는 문자열 또는 null 이어야 한다")
    return val


def _check_allowed_keys(obj: dict[str, Any], allowed: Iterable[str], where: str) -> None:
    allowed_set = set(allowed)
    extra = sorted(set(obj) - allowed_set)
    if extra:
        raise JudgeCLIError("unknown_field", f"{where} 에 모르는 필드: {', '.join(extra)}")


def _optional_bool(obj: dict[str, Any], key: str) -> bool | None:
    if key not in obj or obj[key] is None:
        return None
    val = obj[key]
    if not isinstance(val, bool):
        raise JudgeCLIError("invalid_input", f"{key} 는 불리언 또는 null 이어야 한다")
    return val


def _require_str_map(obj: dict[str, Any], key: str) -> dict[str, str]:
    raw = obj.get(key)
    if not isinstance(raw, dict):
        raise JudgeCLIError("invalid_input", f"{key} 는 문자열 맵이어야 한다")
    out: dict[str, str] = {}
    for k, v in raw.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise JudgeCLIError("invalid_input", f"{key} 의 키와 값은 모두 문자열이어야 한다")
        out[k] = v
    return out


def _op_plan_lint(inp: dict[str, Any]) -> dict[str, Any]:
    _check_allowed_keys(inp, ("plan_md", "criteria", "line_counts"), "input")
    plan_md = _require_str(inp, "plan_md")
    raw_criteria = inp.get("criteria")
    if raw_criteria is None:
        criteria: list[str] = []
    elif isinstance(raw_criteria, list) and all(isinstance(x, str) for x in raw_criteria):
        criteria = list(raw_criteria)
    else:
        raise JudgeCLIError("invalid_input", "criteria 는 문자열 목록이어야 한다")

    raw_counts = inp.get("line_counts")
    line_counts: dict[str, int | None] | None
    if raw_counts is None:
        line_counts = None
    elif isinstance(raw_counts, dict):
        parsed_counts: dict[str, int | None] = {}
        for k, v in raw_counts.items():
            if not isinstance(k, str):
                raise JudgeCLIError("invalid_input", "line_counts 키는 문자열이어야 한다")
            if v is None:
                parsed_counts[k] = None
            elif isinstance(v, int) and not isinstance(v, bool):
                parsed_counts[k] = v
            else:
                raise JudgeCLIError("invalid_input", f"line_counts[{k!r}] 는 정수 또는 null 이어야 한다")
        line_counts = parsed_counts
    else:
        raise JudgeCLIError("invalid_input", "line_counts 는 객체 또는 null 이어야 한다")

    plan = plan_claims.parse_plan(plan_md.splitlines())
    counter = (lambda path: line_counts.get(path)) if line_counts is not None else None
    issues = plan_claims.lint_plan(plan, criteria=criteria, file_line_count=counter)
    return {
        "digest": plan_claims.plan_digest(plan),
        "has_error": plan_claims.has_error_rules(plan),
        "issues": [
            {"message": i.message, "ref": i.ref, "rule": i.rule, "severity": i.severity}
            for i in issues
        ],
        "open_column_ids": plan_claims.column_open_decision_ids(plan),
    }


def _op_plan_states(inp: dict[str, Any]) -> dict[str, Any]:
    _check_allowed_keys(inp, ("plan_md", "task_id", "responses"), "input")
    plan_md = _require_str(inp, "plan_md")
    task_id = _require_str(inp, "task_id")
    raw_resps = inp.get("responses")
    if raw_resps is None:
        raw_resps = []
    elif not isinstance(raw_resps, list):
        raise JudgeCLIError("invalid_input", "responses 는 목록이어야 한다")

    plan = plan_claims.parse_plan(plan_md.splitlines())
    has_error = plan_claims.has_error_rules(plan)
    verdicts: list[dict[str, Any]] = []
    qualified: list[plan_claims.Response] = []

    for idx, item in enumerate(raw_resps):
        if not isinstance(item, dict):
            raise JudgeCLIError("invalid_input", f"responses[{idx}] 는 객체여야 한다")
        _check_allowed_keys(item, ("name", "bytes_b64"), f"responses[{idx}]")
        name = _require_str(item, "name") if "name" in item and item["name"] is not None else ""
        b64 = _require_str(item, "bytes_b64")
        try:
            data = base64.b64decode(b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise JudgeCLIError("invalid_input", f"responses[{idx}].bytes_b64 base64 오류: {exc}") from exc
        if has_error:
            verdicts.append({
                "eligible": False,
                "name": name,
                "reason": "task 계획이 오류 규칙(L2 · L6 · L9)을 어긴 상태다",
                "stage": 0,
            })
            continue
        parsed = plan_responses.parse_response(data, name=name)
        v = plan_responses.qualify(parsed, plan, task_id)
        verdicts.append({
            "eligible": v.eligible,
            "name": name,
            "reason": v.reason,
            "stage": v.stage,
        })
        if v.eligible:
            qualified.append(plan_responses.as_response(parsed))

    state_res = plan_claims.compute_states(plan, qualified)
    return {
        "digest": plan_claims.plan_digest(plan),
        "disputed_responses": list(state_res.disputed_responses),
        "has_error": has_error,
        "open": plan_claims.open_decision_ids(plan, qualified),
        "states": state_res.states,
        "superseded_responses": list(state_res.superseded_responses),
        "verdicts": verdicts,
    }


def _op_task_status(inp: dict[str, Any]) -> dict[str, Any]:
    _check_allowed_keys(
        inp,
        ("requested_status", "validation_result", "operation_type", "current_status", "recorded_validation"),
        "input",
    )
    op_type = _require_str(inp, "operation_type")
    requested = _optional_str(inp, "requested_status")
    val_res = _optional_str(inp, "validation_result")
    cur_status = _optional_str(inp, "current_status")
    rec_val = _optional_str(inp, "recorded_validation")
    status, warnings = planning.determine_conservative_task_status(
        requested, val_res, op_type, cur_status, recorded_validation=rec_val,
    )
    return {"status": status, "warnings": list(warnings)}


def _op_wbs_gate(inp: dict[str, Any]) -> dict[str, Any]:
    _check_allowed_keys(inp, ("roadmap_docs", "is_draft", "wbs", "exempt_reason"), "input")
    raw_docs = inp.get("roadmap_docs")
    roadmap_docs = None if raw_docs is None else _require_str_map(inp, "roadmap_docs")
    is_draft = _optional_bool(inp, "is_draft")
    wbs = _optional_str(inp, "wbs")
    exempt_reason = _optional_str(inp, "exempt_reason")

    if roadmap_docs is None or rm.INDEX_FILE not in roadmap_docs:
        roadmap = None
        index_draft = False
    else:
        texts = {k: v for k, v in roadmap_docs.items() if k != rm.INDEX_FILE}
        roadmap, _ = rm.assemble_roadmap(roadmap_docs[rm.INDEX_FILE], texts)
        index_draft = rm.index_text_is_draft(roadmap_docs[rm.INDEX_FILE])

    effective_draft = bool(is_draft) or index_draft
    verdict = rm.judge_wbs(
        roadmap,
        is_draft=effective_draft,
        wbs=wbs or None,
        exempt_reason=exempt_reason,
    )
    return verdict.model_dump(mode="json")


def _op_roadmap_derive(inp: dict[str, Any]) -> dict[str, Any]:
    _check_allowed_keys(inp, ("roadmap_docs", "links", "deliverables", "generated_at"), "input")
    roadmap_docs = _require_str_map(inp, "roadmap_docs")
    if rm.INDEX_FILE not in roadmap_docs:
        raise JudgeCLIError("invalid_input", "roadmap_docs 에 index.md 가 필요하다")

    raw_links = inp.get("links")
    if raw_links is None:
        raw_links = []
    elif not isinstance(raw_links, list):
        raise JudgeCLIError("invalid_input", "links 는 목록이어야 한다")

    task_links: list[TaskWbsLink] = []
    for idx, item in enumerate(raw_links):
        if not isinstance(item, dict):
            raise JudgeCLIError("invalid_input", f"links[{idx}] 는 객체여야 한다")
        _check_allowed_keys(
            item,
            ("task_id", "task_status", "wbs_ref", "exempt_reason", "source_path"),
            f"links[{idx}]",
        )
        task_links.append(TaskWbsLink(
            task_id=_require_str(item, "task_id"),
            task_status=_require_str(item, "task_status"),
            wbs_ref=_require_str(item, "wbs_ref"),
            exempt_reason=_optional_str(item, "exempt_reason") or "",
            source_path=_optional_str(item, "source_path") or "",
        ))

    raw_deliv = inp.get("deliverables")
    deliverables: dict[str, bool] | None
    if raw_deliv is None:
        deliverables = None
    elif isinstance(raw_deliv, dict):
        parsed_deliv: dict[str, bool] = {}
        for k, v in raw_deliv.items():
            if not isinstance(k, str) or not isinstance(v, bool):
                raise JudgeCLIError("invalid_input", f"deliverables[{k!r}] 는 불리언이어야 한다")
            parsed_deliv[k] = v
        deliverables = parsed_deliv
    else:
        raise JudgeCLIError("invalid_input", "deliverables 는 객체 또는 null 이어야 한다")

    generated_at = _require_str(inp, "generated_at")
    if not generated_at.strip():
        raise JudgeCLIError("invalid_input", "generated_at 는 비어 있지 않은 문자열이어야 한다")

    texts = {k: v for k, v in roadmap_docs.items() if k != rm.INDEX_FILE}
    roadmap, issues = rm.assemble_roadmap(roadmap_docs[rm.INDEX_FILE], texts)

    if deliverables is None:
        declared = sorted({d for m in roadmap.milestones for d in m.deliverables})
        if declared:
            issues.append(RoadmapIssue(
                code="deliverables_unmeasured",
                detail=f"허브는 저장소를 보지 않아 산출물 {len(declared)}개의 존재를 재지 않았다 — 미측정",
                where=rm.INDEX_FILE,
            ))
        exists_fn = lambda _d: True  # noqa: E731
    else:
        exists_fn = lambda d: bool(deliverables.get(d, False))  # noqa: E731

    state = rm.derive_state(
        roadmap,
        task_links,
        Path("/nonexistent-hub-workspace"),
        issues,
        deliverable_exists=exists_fn,
        generated_at=generated_at,
    )
    return state.model_dump(mode="json")


def _op_handoff_parse(inp: dict[str, Any]) -> dict[str, Any]:
    _check_allowed_keys(inp, ("text",), "input")
    text = _require_str(inp, "text")
    with tempfile.TemporaryDirectory(prefix="judge-handoff-") as tmp:
        path = path_in_active(Path(tmp), HANDOFF_FILENAME, "handoff")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="")
        parsed = dict(project_docs.parse_handoff(path))
    parsed["next_documents"] = [
        PurePosixPath(t).as_posix() for t in iter_markdown_link_targets(text)
    ]
    return parsed


def _op_state_build(inp: dict[str, Any]) -> dict[str, Any]:
    _check_allowed_keys(inp, ("files", "generated_at"), "input")
    files = _require_str_map(inp, "files")
    generated_at = _require_str(inp, "generated_at")
    if not generated_at.strip():
        raise JudgeCLIError("invalid_input", "generated_at 는 비어 있지 않은 문자열이어야 한다")

    for rel in files:
        if not rel or rel.startswith("/") or "\\" in rel:
            raise JudgeCLIError("invalid_input", f"files 경로가 올바르지 않다: {rel!r}")
        parts = PurePosixPath(rel).parts
        if any(part in ("", ".", "..") for part in parts):
            raise JudgeCLIError("invalid_input", f"files 경로가 올바르지 않다: {rel!r}")

    if "docs/PROJECT_PROFILE.md" in files:
        profile_rel = "docs/PROJECT_PROFILE.md"
    elif "ai-workflow/memory/active/PROJECT_PROFILE.md" in files:
        profile_rel = "ai-workflow/memory/active/PROJECT_PROFILE.md"
    else:
        raise JudgeCLIError("invalid_input", "files 에 docs/PROJECT_PROFILE.md 가 필요하다")

    branch = "main"
    active_prefix = "ai-workflow/memory/active/"
    skip_segs = {"roadmap", "memory_index", "environments", "archived", "backlog", "sessions"}
    for rel in sorted(files):
        if rel.startswith(active_prefix):
            rest = rel[len(active_prefix):]
            if "/" in rest:
                seg = rest.split("/", 1)[0]
                if seg not in skip_segs:
                    branch = seg
                    break

    with tempfile.TemporaryDirectory(prefix="judge-state-") as tmp:
        root = Path(tmp).resolve()
        for rel, content in files.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="")

        profile_path = root / profile_rel
        memory_dir = workflow_memory_dir(profile_path)
        handoff_cand = path_in_active(memory_dir, HANDOFF_FILENAME, branch)
        handoff_path = handoff_cand if handoff_cand.is_file() else None
        wb_cand = memory_dir / "work_backlog.md"
        work_backlog_index_path = wb_cand if wb_cand.is_file() else None
        daily_backlog_dir = path_in_active(memory_dir, "backlog", branch)
        tasks_dir = daily_backlog_dir / "tasks"
        sessions_dir = path_in_active(memory_dir, "sessions", branch)
        repo_assess_cand = memory_dir / "repository_assessment.md"
        repository_assessment_path = repo_assess_cand if repo_assess_cand.is_file() else None

        idx_dir = memory_index_root(root)
        loaded_entries = load_memory_index_at(idx_dir)
        mem_payload = [dict(p) for p in entry_pointers(loaded_entries, idx_dir, root)]

        payload = build_workflow_state_payload(
            project_profile_path=profile_path,
            session_handoff_path=handoff_path,
            work_backlog_index_path=work_backlog_index_path,
            daily_backlog_dir=daily_backlog_dir,
            tasks_dir=tasks_dir,
            sessions_dir=sessions_dir,
            latest_backlog_path=None,
            repository_assessment_path=repository_assessment_path,
            generated_at=generated_at,
            workspace_root=root,
            memory_entries=mem_payload,
        )
        return cast(
            "dict[str, Any]",
            json.loads(json.dumps(payload, ensure_ascii=False, default=str).replace(str(root), "<hub>")),
        )


_OPS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "plan.lint": _op_plan_lint,
    "plan.states": _op_plan_states,
    "task.status": _op_task_status,
    "wbs.gate": _op_wbs_gate,
    "roadmap.derive": _op_roadmap_derive,
    "handoff.parse": _op_handoff_parse,
    "state.build": _op_state_build,
}


def evaluate(op: str, raw_payload: str) -> dict[str, Any]:
    handler = _OPS.get(op)
    if handler is None:
        raise JudgeCLIError("unknown_op", f"모르는 op: {op}")
    try:
        envelope = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise JudgeCLIError("invalid_json", f"입력이 JSON 이 아니다: {exc}") from exc
    if not isinstance(envelope, dict):
        raise JudgeCLIError("invalid_input", "최상위 입력은 JSON 객체여야 한다")
    _check_allowed_keys(envelope, ("protocol", "input"), "요청")
    if envelope.get("protocol") != PROTOCOL:
        raise JudgeCLIError("protocol_mismatch", f"protocol 은 {PROTOCOL} 이어야 한다")
    inp = envelope.get("input")
    if not isinstance(inp, dict):
        raise JudgeCLIError("invalid_input", "input 은 JSON 객체여야 한다")
    return {"op": op, "protocol": PROTOCOL, "result": handler(inp)}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    batch = False
    pos: list[str] = []
    for arg in args:
        if arg == "--batch":
            batch = True
        elif arg.startswith("-"):
            print(_canonical_json({"error_code": "invalid_args", "message": f"알 수 없는 옵션: {arg}", "protocol": PROTOCOL}))
            return 2
        else:
            pos.append(arg)
    if len(pos) != 1:
        print(_canonical_json({"error_code": "invalid_args", "message": "사용법: workflow_kit.judgecli <op> [--batch]", "protocol": PROTOCOL}))
        return 2
    op = pos[0]
    if op not in _OPS:
        print(_canonical_json({"error_code": "unknown_op", "message": f"모르는 op: {op}", "protocol": PROTOCOL}))
        return 2

    if not batch:
        raw = sys.stdin.read()
        try:
            out = evaluate(op, raw)
        except JudgeCLIError as exc:
            print(_canonical_json({"error_code": exc.code, "message": exc.message, "protocol": PROTOCOL}))
            return 2
        print(_canonical_json(out))
        return 0

    for line in sys.stdin:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            out = evaluate(op, stripped)
        except JudgeCLIError as exc:
            print(_canonical_json({"error_code": exc.code, "message": exc.message, "protocol": PROTOCOL}))
            return 2
        print(_canonical_json(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
