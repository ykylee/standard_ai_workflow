#!/usr/bin/env python3
"""catch-all 오류 결과가 예외 이름만 싣지 않고 원인을 싣는지 잰다.

TASK-2026-11-20-claude-workflow-hub-concept-007. ``backlog-update`` 가 로드맵 WBS 제목
200자 초과(pydantic ``WbsNode.title`` 상한)를 ``exception_type: ValidationError`` 하나로
보고해 원인이 숨었다. 정본은 ``workflow_kit/common/errors.py`` 의
:func:`exception_context` · :func:`describe_exception` 이다.

1~3. :func:`exception_context` 가 메시지를 싣고, pydantic 검증 오류는 필드 위치 · 메시지를 싣는다(JSON 직렬화 가능).
4~5. :func:`describe_exception` 가 검증 오류의 모델 · 필드 · 제약을 한 줄로, 일반 예외는 첫 줄만 낸다.
6. kit 안에서 ``"exception_type": type(x).__name__`` 을 싣는 dict 리터럴은 같은 dict 에 메시지 키
   (``exception_message`` 또는 ``exception``)를 같이 둔다 — 이름만 싣는 새 자리를 막는다.
7. ``backlog-update`` 의 catch-all 이 실제로 원인을 오류 결과(``error`` 문안 · ``source_context``)에 싣는다.
8. 원인을 싣는 family(session_start · backlog_update · doc_sync)의 오류 계약이 새 키를 선언한다.
"""
from __future__ import annotations

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
)

import ast
import contextlib
import io
import json
import sys
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from pydantic import ValidationError  # noqa: E402

from workflow_kit.common.errors import describe_exception, exception_context  # noqa: E402
from workflow_kit.common.schemas.roadmap import WbsNode  # noqa: E402

KIT_ROOT = SOURCE_ROOT / "workflow_kit"
MESSAGE_KEYS = frozenset({"exception_message", "exception"})

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail else ''}")


def _long_title_error() -> ValidationError:
    try:
        WbsNode(id="WBS-31.1", title="가" * 230)
    except ValidationError as exc:
        return exc
    raise AssertionError("WbsNode 가 230자 제목을 받아들였다 — fixture 가 조건을 성립시키지 못한다")


def case_1_context_carries_cause() -> None:
    plain = exception_context(RuntimeError("디스크가 가득 찼다"))
    ok_plain = (plain.get("exception_type") == "RuntimeError"
                and plain.get("exception_message") == "디스크가 가득 찼다"
                and "exception_errors" not in plain)
    _record("case 1 (일반 예외에 메시지)", ok_plain, "" if ok_plain else str(plain))

    ctx = exception_context(_long_title_error())
    errors = ctx.get("exception_errors") or []
    ok_val = (ctx.get("exception_type") == "ValidationError"
              and "200" in str(ctx.get("exception_message", ""))
              and len(errors) == 1 and errors[0].get("loc") == "title"
              and "200" in errors[0].get("msg", ""))
    _record("case 2 (검증 오류에 필드 위치 · 메시지)", ok_val, "" if ok_val else str(ctx))

    ok_json = True
    try:
        json.dumps(ctx, ensure_ascii=False)
    except TypeError as exc:
        ok_json = False
        ok_detail = str(exc)
    _record("case 3 (JSON 직렬화 가능)", ok_json, "" if ok_json else ok_detail)


def case_2_describe_one_line() -> None:
    line = describe_exception(_long_title_error())
    ok = line.startswith("ValidationError(WbsNode) — title:") and "200" in line and "\n" not in line
    _record("case 4 (검증 오류 한 줄 — 모델 · 필드 · 제약)", ok, line)
    line = describe_exception(ValueError("첫 줄\n둘째 줄"))
    _record("case 5 (일반 예외는 첫 줄만)", line == "ValueError: 첫 줄", line)


def _dict_keys(node: ast.Dict) -> set[str]:
    return {k.value for k in node.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}


def _is_runtime_payload(node: ast.Dict) -> bool:
    """``"exception_type": type(x).__name__`` 값을 가진 dict — 계약 선언(shape)은 제외한다."""
    for key, value in zip(node.keys, node.values):
        if (isinstance(key, ast.Constant) and key.value == "exception_type"
                and isinstance(value, ast.Attribute) and value.attr == "__name__"):
            return True
    return False


def case_3_no_name_only_dict() -> None:
    offenders: list[str] = []
    scanned = 0
    for path in sorted(KIT_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict) and _is_runtime_payload(node):
                keys = _dict_keys(node)
                if "exception_type" in keys:
                    scanned += 1
                    if not keys & MESSAGE_KEYS:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")
    # 정본 헬퍼 1곳 + MCP 진입점 1곳은 반드시 보여야 한다 — 0 이면 스캔이 아무것도 못 본 것이다.
    ok = not offenders and scanned >= 2
    _record("case 6 (exception_type 만 싣는 dict 리터럴 없음)", ok,
            f"훑은 dict {scanned}개" + (f", 이름만: {offenders}" if offenders else ""))


def case_4_backlog_update_surfaces_cause() -> None:
    from workflow_kit.tools import backlog_update

    argv = ["backlog-update", "--project-profile-path", "docs/PROJECT_PROFILE.md",
            "--task-name", "repro", "--task-brief", "repro", "--mode", "create"]
    out = io.StringIO()
    with mock.patch.object(sys, "argv", argv), \
         mock.patch.object(backlog_update, "parse_project_profile_backlog",
                           side_effect=_long_title_error()), \
         mock.patch.object(backlog_update, "resolve_existing_path", side_effect=lambda p: Path(p)), \
         contextlib.redirect_stdout(out):
        rc = backlog_update.main()
    try:
        result = json.loads(out.getvalue())
    except json.JSONDecodeError:
        _record("case 7 (backlog-update catch-all 이 원인을 싣는다)", False, f"JSON 아님: {out.getvalue()[:200]}")
        return
    ctx = result.get("source_context", {})
    ok = (rc == 1 and result.get("error_code") == "backlog_update_runtime_error"
          and "title:" in result.get("error", "")
          and (ctx.get("exception_errors") or [{}])[0].get("loc") == "title")
    _record("case 7 (backlog-update catch-all 이 원인을 싣는다)", ok,
            "" if ok else json.dumps({"rc": rc, "error": result.get("error"), "ctx": ctx}, ensure_ascii=False)[:400])


def case_5_contracts_declare_new_keys() -> None:
    from workflow_kit.common.contracts.errors import ERROR_FIELD_SHAPES

    missing: list[str] = []
    for family in ("session_start", "backlog_update", "doc_sync"):
        props = ERROR_FIELD_SHAPES[family]["source_context"].properties
        for key in ("exception_type", "exception_message", "exception_errors"):
            if key not in props:
                missing.append(f"{family}.{key}")
    _record("case 8 (catch-all family 계약이 원인 키를 선언)", not missing, ", ".join(missing))


def main() -> int:
    print("=== catch-all 오류 결과에 예외 원인 (TASK-2026-11-20-claude-workflow-hub-concept-007) ===")
    for fn in (case_1_context_carries_cause,
               case_2_describe_one_line,
               case_3_no_name_only_dict,
               case_4_backlog_update_surfaces_cause,
               case_5_contracts_declare_new_keys):
        fn()
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
