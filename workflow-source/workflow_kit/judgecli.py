"""언어 중립 판정 CLI 입구 — ``python -m workflow_kit.judgecli <op> [--batch]`` (``hub_go_spec.md`` §3 · §4).

``hub-go`` 의 ``workflow-hub judge <op>`` 과 같은 입력·출력·오류 형식(``judge/1``)을 쓴다.
여기의 함수들은 DB · 시계 · 작업 트리를 읽지 않는 순수 판정 함수만 부른다.
"""

from __future__ import annotations

import base64
import binascii
import json
import sys
from typing import Any, Callable, Iterable

from workflow_kit.common import plan_claims, plan_responses, planning

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


_OPS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "plan.lint": _op_plan_lint,
    "plan.states": _op_plan_states,
    "task.status": _op_task_status,
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
