#!/usr/bin/env python3
"""`run_all_checks --changed` 의 선택 계약을 고정한다 (9 cases).

## 왜 필요한가

선택 실행의 실패 양식은 **느려지는 것이 아니라 조용히 안 도는 것**이다. 선언이
코드와 갈라지거나 매칭이 좁아지면, 러너는 여전히 green 을 찍고 사람은 "전부 돌았다"
로 읽는다. 그래서 계약을 세 방향으로 못 박는다:

1. **미선언 = 항상 실행** — 선언을 깜빡한 check 는 느려질 뿐 놓치지 않는다.
2. **자기 파일이 바뀌면 무조건 실행** — 선언 자체를 고친 경우를 포함한다.
3. **건너뛴 것은 이름과 사유가 출력된다** — 조용한 축소를 금지한다.

## 되주입 방향

case 4 는 "무관한 변경이면 건너뛴다" 를, case 3 은 "관련 변경이면 잡는다" 를 잰다.
**둘을 같이 두는 이유**: 한 방향만 재면 "아무것도 안 잡는" 구현이 통과한다
(2026-08-14 `check_archive_history_integrity` case 14 와 같은 부류 — 자기 적용
case 는 corpus 가 깨끗하면 무력화돼도 green 이다).

Refs:
  - workflow-source/tests/run_all_checks.py — WATCHES_MARKER / select_by_change
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/tests/*",
    "workflow-source/workflow_kit/*",
)

import sys
import tempfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import run_all_checks as R  # noqa: E402

REPO_ROOT = TESTS_DIR.resolve().parents[1]

FAILURES: list[str] = []


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fixture(root: Path, name: str, watches: str | None) -> Path:
    decl = f"WATCHES = ({watches})\n" if watches is not None else ""
    p = root / "tests" / f"{name}.py"
    _write(p, f'"""fixture."""\n{decl}\nprint("ok")\n')
    return p


def case_1_undeclared_always_runs(root: Path) -> None:
    c = _fixture(root, "check_nodecl", None)
    run, skipped = R.select_by_change([c], ["some/other/file.py"], root)
    assert run == [c], "미선언 check 를 건너뛰었다 — 사각지대다"
    assert skipped == [], skipped


def case_2_own_file_changed_runs(root: Path) -> None:
    c = _fixture(root, "check_own", '"nowhere/*",')
    rel = c.resolve().relative_to(root.resolve()).as_posix()
    run, skipped = R.select_by_change([c], [rel], root)
    assert run == [c], "자기 파일이 바뀌었는데 건너뛰었다 (선언 변경을 못 본다)"


def case_3_glob_match_runs(root: Path) -> None:
    c = _fixture(root, "check_match", '"src/lib/*.py",')
    run, _ = R.select_by_change([c], ["src/lib/deep/mod.py"], root)
    assert run == [c], "선언한 범위의 변경을 못 잡았다 — 이쪽이 진짜 위험한 실패다"


def case_4_unrelated_change_skips(root: Path) -> None:
    c = _fixture(root, "check_skip", '"src/lib/*.py",')
    run, skipped = R.select_by_change([c], ["docs/readme.md"], root)
    assert run == [], "무관한 변경인데 실행했다 (선택이 작동하지 않는다)"
    assert len(skipped) == 1 and "WATCHES" in skipped[0][1], (
        f"건너뛴 사유가 비어 있다: {skipped}"
    )


def case_5_non_literal_watches_is_undeclared(root: Path) -> None:
    """리터럴이 아닌 원소가 섞이면 **미선언으로 본다** — 반쯤 읽은 선언은 사각지대다."""
    p = root / "tests" / "check_dyn.py"
    _write(p, '"""fixture."""\nP = "x"\nWATCHES = ("src/*", P)\n')
    assert R.watched_globs(p) == (), "리터럴 아닌 선언을 부분 해석했다"
    run, _ = R.select_by_change([p], ["totally/unrelated.md"], root)
    assert run == [p], "반쯤 읽은 선언으로 건너뛰었다"


def case_6_empty_tuple_is_undeclared(root: Path) -> None:
    c = _fixture(root, "check_empty", "")
    assert R.watched_globs(c) == (), "빈 튜플을 선언으로 취급했다"
    run, _ = R.select_by_change([c], ["anything.md"], root)
    assert run == [c], "빈 선언인데 건너뛰었다"


def case_7_unparsable_file_runs(root: Path) -> None:
    p = root / "tests" / "check_broken.py"
    _write(p, "def (:\n")
    run, _ = R.select_by_change([p], ["x.md"], root)
    assert run == [p], "parse 실패 파일을 건너뛰었다 — 실행해서 실패하게 둬야 한다"


def case_8_report_names_every_skip(root: Path) -> None:
    """건너뛴 것은 **개수가 아니라 이름과 사유**로 출력된다 (조용한 축소 금지)."""
    import io
    from contextlib import redirect_stdout
    cs = [_fixture(root, f"check_s{i}", '"nowhere/*",') for i in range(3)]
    run, skipped = R.select_by_change(cs, ["docs/a.md"], root)
    buf = io.StringIO()
    with redirect_stdout(buf):
        R.report_change_selection(["docs/a.md"], "테스트", run, skipped)
    out = buf.getvalue()
    for c in cs:
        assert c.stem in out, f"건너뛴 {c.stem} 이 출력에 없다"
    assert "게이트가 아니다" in out, "게이트 아님 경고가 출력에 없다"


def case_9_self_declarations_parse() -> None:
    """자기 적용 — 이 저장소의 `WATCHES` 선언이 실제로 읽히는가.

    선언을 붙였는데 문법이 어긋나 `()` 로 읽히면 그냥 '항상 실행' 이 되어
    **조용히 효과가 0** 이다. 그 침묵을 여기서 깬다.
    """
    declared = [p for p in sorted(TESTS_DIR.glob("check_*.py")) if R.watched_globs(p)]
    assert declared, "저장소에 WATCHES 선언이 하나도 읽히지 않는다"
    for p in declared:
        for g in R.watched_globs(p):
            assert g and not g.startswith("/"), f"{p.stem}: 이상한 glob {g!r}"


def _run(fn, needs_root: bool = True) -> None:
    try:
        if needs_root:
            with tempfile.TemporaryDirectory(prefix="check-changed-sel-") as tmp:
                fn(Path(tmp).resolve())
        else:
            fn()
        print(f"  PASS  {fn.__name__}")
    except AssertionError as e:
        FAILURES.append(fn.__name__)
        print(f"  FAIL  {fn.__name__} — {e}")


def main() -> int:
    print("=== changed-selection 계약 ===")
    for fn in (case_1_undeclared_always_runs, case_2_own_file_changed_runs,
               case_3_glob_match_runs, case_4_unrelated_change_skips,
               case_5_non_literal_watches_is_undeclared,
               case_6_empty_tuple_is_undeclared, case_7_unparsable_file_runs,
               case_8_report_names_every_skip):
        _run(fn)
    _run(case_9_self_declarations_parse, needs_root=False)
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    print("\n9/9 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
