#!/usr/bin/env python3
"""task 본문 라벨의 **정본 단일화**를 고정한다 (11 cases).

## 계보 — 라벨은 곧 파싱 계약이다

`- 상태:` 같은 본문 라벨은 장식이 아니라 **파싱 계약**이다. `project_docs.STATUS_RE`
가 그 문자열로 상태를 읽고, writer 넷이 같은 문자열을 emit 한다. 그런데 리터럴이
`backlog_update` / `workflow_writes` / `read_only_bundle` 에 흩어져 있었다 —
2026-08-14 조사에서 12개 라벨이 46곳. 흩어진 채로는 **바꿀 수가 없다.** 한 곳만
고치면 나머지가 조용히 갈라지고, 그 갈라짐은 "필드가 사라진 문서" 로 나타난다.

## 두 단계로 나눈 이유

라벨 영어화는 **쓰는 쪽을 먼저 바꾸면 안 된다.** 소비자 저장소의 리더가 아직 옛
표기만 알기 때문이다. 순서는:

1. (이번) **리더가 두 표기를 모두 받는다** + 리터럴을 정본 한 곳으로
2. (다음 release) 정본 라벨을 영어로 바꾼다 — 그때는 상수 한 줄이다

이 검사는 1단계가 **실제로 성립하는지**를 잰다. 특히 case 6 — 정본을 바꾸면
산출물이 따라 바뀌는가 — 가 "정본이 하나" 라는 주장의 유일한 증거다.

11 cases:
  1) 정본 표와 별칭 표의 key 집합이 같다
  2) 별칭의 첫 항목은 항상 정본이다
  3) 읽는 쪽이 **옛 표기**로 적힌 줄을 찾는다
  4) 읽는 쪽이 **영어 표기**로 적힌 줄을 찾는다
  5) 쓸 때는 **정본 표기**로 쓴다 (찾기는 넓게, 쓰기는 좁게)
  6) **정본을 바꾸면 산출물이 따라 바뀐다** — 정본이 하나라는 증거
  7) `STATUS_RE` 가 두 표기를 받고, 잘못된 상태값은 여전히 거부한다
  8) 산출물 렌더 경로 **전부**에 라벨 리터럴이 남아 있지 않다
  9) 본문 조립부가 **정본 표에 없는 라벨**을 쓰지 않는다 (8 의 역방향)
 10) **되주입 실증** — 정본을 영어로 뒤집어도 옛 표기 문서가 그대로 읽힌다
 11) `검증 결과` 주입 앵커가 두 표기 모두에서 걸린다 (done 근거가 안 사라진다)
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = TESTS_DIR.parent
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import project_docs as PD  # noqa: E402
from workflow_kit.common.workflow_writes import (  # noqa: E402
    _set_inline_field,
    _set_list_field,
    merge_task_file,
)

FAILURES: list[str] = []


def case_1_key_sets_match() -> None:
    a, b = set(PD.TASK_FIELD_LABELS), set(PD.TASK_FIELD_ALIASES)
    assert a == b, f"정본과 별칭의 key 가 어긋난다: only_labels={a - b} only_aliases={b - a}"


def case_2_canonical_is_first() -> None:
    for key in PD.TASK_FIELD_LABELS:
        got = PD.task_label_aliases(key)
        assert got[0] == PD.TASK_FIELD_LABELS[key], f"{key}: 별칭 첫 항목이 정본이 아니다 ({got})"


def case_3_reader_finds_legacy_spelling() -> None:
    lines = ["# TASK-X — t", "- 상태: planned", "- 완료 기준: 옛 표기"]
    out, found = _set_inline_field(lines, PD.task_label("done_criteria"), "새 값")
    assert found, "옛 표기로 적힌 줄을 못 찾았다"
    assert "- 완료 기준: 새 값" in out


def case_4_reader_finds_english_spelling() -> None:
    lines = ["# TASK-X — t", "- Completion criteria: english form"]
    out, found = _set_inline_field(lines, PD.task_label("done_criteria"), "새 값")
    assert found, "영어 표기로 적힌 줄을 못 찾았다 — 전환 후 옛 리더가 못 읽는다"
    assert "- 완료 기준: 새 값" in out, f"쓸 때 정본 표기를 안 썼다: {out}"


def case_5_writes_canonical_only() -> None:
    lines = ["- Completion criteria: a", "- Completion criteria: b"]
    out, found = _set_list_field(lines, PD.task_label("done_criteria"), ["x", "y"])
    assert found
    assert out == ["- 완료 기준: x", "- 완료 기준: y"], f"찾기는 넓게 쓰기는 좁게가 아니다: {out}"


def case_6_changing_canonical_changes_output() -> None:
    """**정본이 하나라는 유일한 증거.** 표를 바꾸면 산출물이 따라 바뀐다."""
    original = PD.TASK_FIELD_LABELS["done_criteria"]
    try:
        PD.TASK_FIELD_LABELS["done_criteria"] = "Completion criteria"
        lines = ["- 완료 기준: 옛 표기"]
        out, found = _set_list_field(lines, PD.task_label("done_criteria"), ["v"])
        assert found, "정본을 바꾸자 옛 표기 줄을 못 찾는다 — 별칭이 안 걸렸다"
        assert out == ["- Completion criteria: v"], f"산출물이 정본을 안 따랐다: {out}"
    finally:
        PD.TASK_FIELD_LABELS["done_criteria"] = original


def case_7_status_regex_accepts_both() -> None:
    assert PD.STATUS_RE.match("- 상태: done"), "옛 표기를 거부한다"
    assert PD.STATUS_RE.match("- Status: done"), "영어 표기를 거부한다"
    assert not PD.STATUS_RE.match("- 상태: bogus"), "잘못된 상태값을 받아들인다"


#: task **본문**을 렌더하거나 갱신하는 함수 전부. case 8 · 9 가 이 범위를 훑는다.
#:
#: **파일이 아니라 함수 단위**인 이유: `- 상태:` / `- 호스트명:` 은 문서 메타데이터
#: 헤더(`- 문서 목적:` / `- 범위:` / `- 상태:` …)와 환경 기록에도 쓰인다. 그쪽은
#: `check_doc_metadata` 가 지키는 **다른 계약**이고, 4단계에서 영어로 바뀌지 않는다.
#: 파일 전체를 훑으면 그 셋이 오탐으로 걸린다.
#:
#: 한 파일만 훑던 때가 있었다 (`backlog_update.py` 하나). 그래서 `read_only_bundle`
#: 의 라벨 13개가 3단계의 "46곳을 모았다" 를 통과하고도 리터럴로 남았다 — **검사의
#: 범위가 곧 주장의 범위다.** 새 writer 를 만들면 여기에 등록한다.
TASK_BODY_BUILDERS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("workflow_kit", "tools", "backlog_update.py"), "build_draft_entry"),
    (("workflow_kit", "tools", "seed_workspace_memory.py"), "task_body"),
    (("workflow_kit", "common", "read_only_bundle.py"), "create_backlog_entry_payload"),
    (("workflow_kit", "common", "workflow_writes.py"), "render_task_file"),
    (("workflow_kit", "common", "workflow_writes.py"), "merge_task_file"),
)


def _body_builder_nodes() -> list[tuple[str, ast.AST]]:
    """등록된 본문 조립 함수들을 (표시이름, AST) 로 돌려준다."""
    out: list[tuple[str, ast.AST]] = []
    for parts, func_name in TASK_BODY_BUILDERS:
        target = SOURCE_ROOT.joinpath(*parts)
        assert target.exists(), f"본문 조립 경로 목록이 실제 파일과 어긋난다: {target}"
        tree = ast.parse(target.read_text(encoding="utf-8"))
        func = next((n for n in ast.walk(tree)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and n.name == func_name), None)
        assert func is not None, f"본문 조립 함수를 못 찾았다: {target.name}::{func_name}"
        out.append((f"{target.name}::{func_name}", func))
    return out


def _string_constants(func: ast.AST):
    """함수 안의 문자열 리터럴. docstring 은 설명이므로 제외한다."""
    docstrings: set[int] = set()
    for node in ast.walk(func):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(
                    node.body[0].value, ast.Constant):
                docstrings.add(id(node.body[0].value))
    for node in ast.walk(func):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            yield node


def case_8_no_literals_left_in_render_path() -> None:
    """본문 조립/갱신 경로 **전부**에 라벨 리터럴이 남아 있지 않다.

    남아 있으면 정본을 바꿔도 그 자리만 옛 표기를 쓴다 — 갈라짐의 씨앗이다.
    """
    labels = set(PD.TASK_FIELD_LABELS.values())
    bad: list[str] = []
    for where, func in _body_builder_nodes():
        for node in _string_constants(func):
            for label in labels:
                if re.search(rf"(^|[^가-힣A-Za-z]){re.escape(label)}:", node.value):
                    bad.append(f"{where} L{node.lineno}: {node.value[:50]!r}")
                    break
    assert not bad, ("본문 조립 경로에 라벨 리터럴이 남았다 (정본 조회로 바꿀 것):\n  "
                     + "\n  ".join(bad[:10]))


_BODY_LABEL_RE = re.compile(r"^- ([^:\n]{1,30}):")


def case_9_unregistered_label_cannot_enter_body() -> None:
    """본문 조립부가 **정본 표에 없는 라벨**을 쓰지 않는다.

    case 8 은 "표에 있는 라벨이 리터럴로 남았나" 를 본다. 표에 *없는* 라벨은 그
    그물에 안 걸린다 — `요청일` / `완료일` / `범위 밖` 이 정확히 그렇게 3단계의
    "46곳을 모았다" 를 통과했다. 표에 없으면 전환 때 그 줄만 한국어로 남아
    **섞인 문서**가 된다. 그래서 방향을 뒤집어 한 번 더 잰다.
    """
    known = set(PD.TASK_FIELD_LABELS.values())
    bad: list[str] = []
    for where, func in _body_builder_nodes():
        for node in _string_constants(func):
            m = _BODY_LABEL_RE.match(node.value)
            if m and m.group(1) not in known:
                bad.append(f"{where} L{node.lineno}: {m.group(1)!r}")
    assert not bad, ("본문에 정본 표에 없는 라벨이 들어간다 (표에 등록할 것):\n  "
                     + "\n  ".join(bad[:10]))


def case_10_legacy_document_survives_the_flip() -> None:
    """**되주입 실증** — 정본을 영어로 바꿔도 옛 표기로 적힌 기존 문서가 그대로 읽힌다.

    4단계(영어 전환)의 완료 기준을 전환 *전에* 미리 실증한다. 표 전체를 영어로
    뒤집은 상태에서, 실제 task 파일 모양의 한국어 본문을 읽고 갱신해 본다.
    한 필드라도 못 찾으면 그 필드는 전환 후 **조용히 사라진다**.
    """
    legacy_body = [
        "# TASK-2026-08-14-main-009 — t",
        "",
        "## 📝 Description",
        "",
        "- 상태: in_progress",
        "- 우선순위: medium",
        "- 요청일: 2026-08-14",
        "- 담당: AI Agent",
        "- 작업 내용: 옛 표기로 적힌 기존 문서",
        "- 완료 기준: 전환 후에도 읽힌다",
        "- 진행 현황: 진행 중",
        "- 작업 결과: 아직",
        "- 후속 작업: 없음",
    ]
    original = dict(PD.TASK_FIELD_LABELS)
    try:
        PD.TASK_FIELD_LABELS.update(
            {k: v[-1] for k, v in PD.TASK_FIELD_ALIASES.items()})
        assert PD.TASK_FIELD_LABELS["status"] == "Status", "전환 시뮬레이션이 성립하지 않았다"
        for key in ("status", "priority", "request_date", "owner", "summary",
                    "done_criteria", "progress", "result", "follow_up"):
            _, found = _set_inline_field(legacy_body, PD.task_label(key), "새 값")
            assert found, (f"전환 후 옛 표기 줄 '{original[key]}' 을 못 찾는다 — "
                           f"이 필드는 기존 문서에서 조용히 사라진다")
        # 상태 줄은 정규식으로도 읽힌다 (frontmatter 가 없는 legacy 문서의 fallback).
        assert PD.STATUS_RE.match("- 상태: in_progress"), "전환 후 STATUS_RE 가 옛 표기를 거부한다"
    finally:
        PD.TASK_FIELD_LABELS.clear()
        PD.TASK_FIELD_LABELS.update(original)


def case_11_validation_injection_survives_both_spellings() -> None:
    """`검증 결과` 주입 앵커가 **두 표기 모두**에서 걸린다.

    이 분기는 원문에 줄이 없을 때 `작업 결과` 바로 뒤에 넣는다. 앵커를 리터럴로
    보던 때는 영어 표기 문서에서 비교가 항상 거짓이라, done 판정의 근거인 검증
    결과가 `missing` 으로 조용히 버려졌다 (2026-08-14 실측).
    """
    for label, body in (
        ("옛 표기", ["# T", "- 상태: in_progress", "- 작업 결과: 기존"]),
        ("영어 표기", ["# T", "- Status: in_progress", "- Result: existing"]),
    ):
        lines, missing = merge_task_file(
            body, status="done",
            scalar_updates={PD.task_label("validation"): "전량 green"},
            affected_documents=None)
        assert any("전량 green" in ln for ln in lines), (
            f"{label} 문서에 검증 결과가 주입되지 않았다 — done 근거가 사라진다")
        assert not missing, f"{label} 문서에서 필드를 놓쳤다: {missing}"


def _run(fn) -> None:
    try:
        fn()
        print(f"  PASS  {fn.__name__}")
    except AssertionError as e:
        FAILURES.append(fn.__name__)
        print(f"  FAIL  {fn.__name__} — {e}")
    except Exception as e:  # noqa: BLE001
        FAILURES.append(fn.__name__)
        print(f"  FAIL  {fn.__name__} — 예외 {type(e).__name__}: {e}")


def main() -> int:
    print("=== task 라벨 정본 단일화 ===")
    cases = (case_1_key_sets_match, case_2_canonical_is_first,
             case_3_reader_finds_legacy_spelling, case_4_reader_finds_english_spelling,
             case_5_writes_canonical_only, case_6_changing_canonical_changes_output,
             case_7_status_regex_accepts_both, case_8_no_literals_left_in_render_path,
             case_9_unregistered_label_cannot_enter_body,
             case_10_legacy_document_survives_the_flip,
             case_11_validation_injection_survives_both_spellings)
    for fn in cases:
        _run(fn)
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    print(f"\n{len(cases)}/{len(cases)} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
