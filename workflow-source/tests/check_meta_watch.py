#!/usr/bin/env python3
"""meta-watch (WATCHES 선언 메타 검증, ADR-028) 의 계약을 고정한다 (8 cases).

## 왜 필요한가

`--changed` 의 유일한 위험 실패 모드는 **좁은 선언** — 선언 밖 경로를 읽는
검사가 조용히 skip 되는 것이다. meta-watch 가 그것을 잡는데, 그 그물 자신이
좁아지면(채취 누락·판정 완화) 다시 침묵이 된다. 그래서 세 층을 못 박는다:

1. **채취**: sitecustomize 주입이 저장소 안 접근을 기록하고, 자식 python
   프로세스에도 전파되며, pyc 접근이 소스 .py 로 역매핑된다.
2. **판정**: 선언 밖 접근 → uncovered (red 근거), 접근 0 glob → unused (warn).
   실재하는 일반 파일만 판정 대상 — import 기계의 부재 stat 은 잡음이다.
3. **어휘**: `WATCHES_ALL_REASON` 은 근거 문자열 필수, `WATCHES` 와 동시
   선언은 모순으로 red.

## 되주입 방향

case 3(좁은 선언을 잡는다)과 case 4(맞는 선언은 통과)를 같이 둔다 — 한
방향만 재면 "아무것도 안 잡는" 구현이 통과한다 (check_changed_selection 의
설계와 같은 이유).

Refs:
  - workflow_kit/common/meta_watch.py — 채취/판정 정본
  - tests/run_all_checks.py — meta_watch_verdict / ALL_REASON_MARKER
  - core/test_impact_tiering_spec.md §4 · ADR-028
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = TESTS_DIR.parent
for p in (str(TESTS_DIR), str(SOURCE_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import run_all_checks as R  # noqa: E402
from workflow_kit.common import meta_watch as MW  # noqa: E402

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/run_all_checks.py",
    "workflow-source/pyproject.toml",
)

FAILURES: list[str] = []


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def case_1_capture_records_repo_access(root: Path) -> None:
    """주입된 프로세스의 저장소 안 파일 접근이 기록된다 (저장소 밖은 아니다)."""
    _write(root / "data" / "in_repo.txt", "x")
    outside = Path(tempfile.mkstemp(prefix="mw-outside-")[1])
    site_dir = root / "site"
    MW.write_sitecustomize(site_dir)
    out = root / "acc.txt"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(site_dir)
    env[MW.OUT_ENV] = str(out)
    env[MW.REPO_ENV] = str(root)
    code = (f"open({str(root / 'data' / 'in_repo.txt')!r}).read(); "
            f"open({str(outside)!r}).read()")
    subprocess.run([sys.executable, "-c", code], env=env, check=True,
                   cwd=str(root), capture_output=True)
    accessed = MW.load_accesses(out)
    assert "data/in_repo.txt" in accessed, f"저장소 안 접근이 기록되지 않았다: {accessed}"
    assert not any("mw-outside" in a for a in accessed), "저장소 밖 접근을 기록했다"
    outside.unlink(missing_ok=True)


def case_2_capture_propagates_to_python_child(root: Path) -> None:
    """자식 python 프로세스의 접근도 같은 훅으로 기록된다 (env 전파)."""
    _write(root / "data" / "child_read.txt", "x")
    site_dir = root / "site"
    MW.write_sitecustomize(site_dir)
    out = root / "acc.txt"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(site_dir)
    env[MW.OUT_ENV] = str(out)
    env[MW.REPO_ENV] = str(root)
    inner = f"open({str(root / 'data' / 'child_read.txt')!r}).read()"
    code = f"import subprocess, sys; subprocess.run([sys.executable, '-c', {inner!r}], check=True)"
    subprocess.run([sys.executable, "-c", code], env=env, check=True,
                   cwd=str(root), capture_output=True)
    assert "data/child_read.txt" in MW.load_accesses(out), \
        "자식 python 의 접근이 기록되지 않았다 — 전파가 끊겼다"


def case_3_judge_catches_narrow_declaration(root: Path) -> None:
    """선언 밖 실접근 → uncovered. **이쪽이 진짜 위험한 실패다.**"""
    _write(root / "declared" / "a.md", "x")
    _write(root / "undeclared" / "b.md", "x")
    uncovered, _ = MW.judge(
        {"declared/a.md", "undeclared/b.md"}, ("declared/*",), "tests/check_x.py", root)
    assert uncovered == ["undeclared/b.md"], f"좁은 선언을 못 잡았다: {uncovered}"


def case_4_judge_passes_covering_declaration(root: Path) -> None:
    """선언이 접근을 덮으면 uncovered 0 — 자기 파일은 선언 없이도 허용."""
    _write(root / "declared" / "a.md", "x")
    _write(root / "tests" / "check_x.py", "x")
    uncovered, unused = MW.judge(
        {"declared/a.md", "tests/check_x.py"}, ("declared/*",), "tests/check_x.py", root)
    assert uncovered == [], f"맞는 선언을 red 로 판정했다: {uncovered}"
    assert unused == [], f"접근이 있는 glob 을 unused 로 판정했다: {unused}"


def case_5_judge_ignores_nonexistent_and_dirs(root: Path) -> None:
    """부재 경로(import 기계의 후보 stat)와 디렉터리는 판정 대상이 아니다."""
    (root / "somedir").mkdir(parents=True)
    uncovered, _ = MW.judge(
        {"somedir", "ghost/never_existed.py"}, ("declared/*",), "", root)
    assert uncovered == [], f"부재/디렉터리를 접근으로 판정했다: {uncovered}"


def case_6_unused_glob_is_warn_not_red(root: Path) -> None:
    """접근 0 인 glob 은 unused (warn) — 넓은 선언은 안전한 오차다."""
    _write(root / "declared" / "a.md", "x")
    uncovered, unused = MW.judge(
        {"declared/a.md"}, ("declared/*", "nowhere/*"), "", root)
    assert uncovered == [], uncovered
    assert unused == ["nowhere/*"], f"unused 판정이 틀렸다: {unused}"


def case_7_all_reason_vocabulary(root: Path) -> None:
    """WATCHES_ALL_REASON 파싱: 근거 문자열만 선언, 동시 선언은 모순으로 red."""
    ok = root / "tests" / "check_all.py"
    _write(ok, '"""f."""\nWATCHES_ALL_REASON = "전역 관찰 — 근거"\nprint("ok")\n')
    assert R.watches_all_reason(ok) == "전역 관찰 — 근거", "근거 문자열이 안 읽힌다"
    empty = root / "tests" / "check_empty_reason.py"
    _write(empty, '"""f."""\nWATCHES_ALL_REASON = "  "\n')
    assert R.watches_all_reason(empty) == "", "빈 근거를 선언으로 취급했다"
    both = root / "tests" / "check_both.py"
    _write(both, '"""f."""\nWATCHES = ("a/*",)\nWATCHES_ALL_REASON = "x"\n')
    violations, _, _ = R.meta_watch_verdict([both], root, root)
    assert violations and "동시 선언" in violations[0], \
        f"동시 선언 모순을 못 잡았다: {violations}"


def case_8_pyc_access_maps_to_source(root: Path) -> None:
    """__pycache__/<m>.cpython-*.pyc 접근이 <m>.py 로 역매핑된다 (import 표면)."""
    pkg = root / "pkg"
    _write(pkg / "mod.py", "VALUE = 1\n")
    site_dir = root / "site"
    MW.write_sitecustomize(site_dir)
    out = root / "acc.txt"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(site_dir), str(root)])
    env[MW.OUT_ENV] = str(out)
    env[MW.REPO_ENV] = str(root)
    # 1회차가 pyc 를 굽고, 2회차가 pyc 를 읽는다 — 역매핑은 2회차에서 재진다.
    for _ in range(2):
        subprocess.run([sys.executable, "-c", "import pkg.mod"], env=env,
                       check=True, cwd=str(root), capture_output=True)
    accessed = MW.load_accesses(out)
    assert "pkg/mod.py" in accessed, f"pyc→py 역매핑이 안 됐다: {sorted(accessed)}"
    assert not any(".pyc" in a for a in accessed), f"pyc 경로가 그대로 남았다: {sorted(accessed)}"


def _run(fn) -> None:
    try:
        with tempfile.TemporaryDirectory(prefix="check-meta-watch-") as tmp:
            fn(Path(tmp).resolve())
        print(f"  PASS  {fn.__name__}")
    except AssertionError as e:
        FAILURES.append(fn.__name__)
        print(f"  FAIL  {fn.__name__} — {e}")


def main() -> int:
    print("=== meta-watch 계약 (ADR-028) ===")
    for fn in (case_1_capture_records_repo_access,
               case_2_capture_propagates_to_python_child,
               case_3_judge_catches_narrow_declaration,
               case_4_judge_passes_covering_declaration,
               case_5_judge_ignores_nonexistent_and_dirs,
               case_6_unused_glob_is_warn_not_red,
               case_7_all_reason_vocabulary,
               case_8_pyc_access_maps_to_source):
        _run(fn)
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    print("\n8/8 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
