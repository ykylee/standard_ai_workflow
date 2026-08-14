#!/usr/bin/env python3
"""task 본문 라벨의 **정본 단일화**를 고정한다 (8 cases).

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

8 cases:
  1) 정본 표와 별칭 표의 key 집합이 같다
  2) 별칭의 첫 항목은 항상 정본이다
  3) 읽는 쪽이 **옛 표기**로 적힌 줄을 찾는다
  4) 읽는 쪽이 **영어 표기**로 적힌 줄을 찾는다
  5) 쓸 때는 **정본 표기**로 쓴다 (찾기는 넓게, 쓰기는 좁게)
  6) **정본을 바꾸면 산출물이 따라 바뀐다** — 정본이 하나라는 증거
  7) `STATUS_RE` 가 두 표기를 받고, 잘못된 상태값은 여전히 거부한다
  8) 산출물 렌더 경로에 라벨 **리터럴이 남아 있지 않다**
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
from workflow_kit.common.workflow_writes import _set_inline_field, _set_list_field  # noqa: E402

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


def case_8_no_literals_left_in_render_path() -> None:
    """렌더/갱신 경로에 라벨 리터럴이 남아 있지 않다.

    남아 있으면 정본을 바꿔도 그 자리만 옛 표기를 쓴다 — 갈라짐의 씨앗이다.
    docstring 과 주석은 설명이므로 제외한다 (AST 로 **문자열 리터럴만** 본다).
    """
    target = SOURCE_ROOT / "workflow_kit" / "tools" / "backlog_update.py"
    tree = ast.parse(target.read_text(encoding="utf-8"))
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(
                    node.body[0].value, ast.Constant):
                docstrings.add(id(node.body[0].value))
    labels = set(PD.TASK_FIELD_LABELS.values())
    bad: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            for label in labels:
                if re.search(rf"(^|[^가-힣A-Za-z]){re.escape(label)}:", node.value):
                    bad.append(f"L{node.lineno}: {node.value[:50]!r}")
                    break
    assert not bad, ("렌더 경로에 라벨 리터럴이 남았다 (정본 조회로 바꿀 것):\n  "
                     + "\n  ".join(bad[:10]))


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
    for fn in (case_1_key_sets_match, case_2_canonical_is_first,
               case_3_reader_finds_legacy_spelling, case_4_reader_finds_english_spelling,
               case_5_writes_canonical_only, case_6_changing_canonical_changes_output,
               case_7_status_regex_accepts_both, case_8_no_literals_left_in_render_path):
        _run(fn)
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    print("\n8/8 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
