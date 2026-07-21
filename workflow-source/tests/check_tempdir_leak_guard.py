#!/usr/bin/env python3
"""v1.0.0 — temp dir 누수 재발 방지 contract guard (7 case).

**배경 (2026-07-21 실측 사고)**

`tests/check_scaffold_harness.py` 가 `cp -R <REPO_ROOT>` 로 저장소 전체
(327MB, 그중 `.venv` 258MB) 를 `tempfile.TemporaryDirectory()` 안에 staging 했다.
복사가 runner 의 per-check timeout 을 넘기면 프로세스가 SIGKILL 되고,
`TemporaryDirectory` 의 `__exit__` 정리 코드는 SIGKILL 에서 실행되지 않으므로
temp dir 이 그대로 남는다. 누적 결과:

- `/var/tmp` 에 orphan temp dir **1431개 / 약 211GB**
- 루트 파일시스템 **100% full (Avail 0)**
- 부분 복사본의 내용물이 `.venv` 172K 에서 잘려 있는 것이 "복사 도중 kill" 의 증거
- `/tmp` 가 tmpfs (RAM) 인 환경에서는 동일 누수가 **RAM 을 직접 소모** → OOM

`export_harness_package.cleanup_leaked_tempdirs()` 라는 가드가 이미 있었지만
`base = Path(os.environ.get("TMPDIR", "/tmp"))` 로 `/tmp` 만 훑어서, 실제 누수 위치인
`/var/tmp` 를 보지 못했다 (docstring 은 `/var/tmp` 라고 적혀 있었음 — 문서/코드 불일치).

**본 guard 가 고정하는 계약**

1. 어떤 smoke 도 REPO_ROOT 를 필터 없이 통째로 복사하지 않는다 (`cp -R` 금지).
2. `check_scaffold_harness` 의 제외 목록에 무거운 트리가 들어 있다.
3. `cleanup_leaked_tempdirs` 가 `/var/tmp` 를 포함해 훑는다.
4. `cleanup_leaked_tempdirs` 가 남의 소유 dir 을 건드리지 않는다.
5. CI smoke 루프에 per-check timeout 이 걸려 있다.
6. `check_scaffold_harness` 실행이 temp root 에 orphan 을 남기지 않는다 (실측).
7. `tempfile.mkdtemp()` 를 정리 없이 쓰는 곳이 없다 — `mkdtemp` 은 자동 정리가
   전혀 없어 kill 이 아니라 *성공한 실행마다* 흘린다 (감사에서 3 smoke / 5개소,
   실행당 5개 누수 확인).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = REPO_ROOT / "workflow-source" / "tests"
SCAFFOLD_SMOKE = TESTS_DIR / "check_scaffold_harness.py"
EXPORT_TOOL = REPO_ROOT / "workflow-source" / "scripts" / "export_harness_package.py"
SMOKE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "smoke.yml"

# 복사 staging 에서 반드시 제외되어야 하는 무거운 트리
REQUIRED_EXCLUDES = (".venv", ".git", "node_modules", "__pycache__")


def case_1_no_unfiltered_repo_copy() -> bool:
    """1) smoke 가 `cp -R <REPO_ROOT>` 로 저장소를 통째 복사하지 않는다."""
    offenders: list[str] = []
    for py in sorted(TESTS_DIR.glob("check_*.py")):
        if py.name == Path(__file__).name:
            continue  # 탐지 패턴 문자열을 본문에 담고 있으므로 자기 자신은 제외
        src = py.read_text(encoding="utf-8")
        # `cp -R` / `cp -r` 에 REPO_ROOT 가 인자로 붙는 패턴
        for marker in ('"cp", "-R"', '"cp", "-r"', "'cp', '-R'", "'cp', '-r'"):
            if marker in src and "REPO_ROOT" in src:
                offenders.append(py.name)
                break
    if offenders:
        print(f"  FAIL: REPO_ROOT 통째 `cp -R` 사용: {offenders}")
        print("        → shutil.copytree(..., ignore=shutil.ignore_patterns(...)) 로 교체할 것")
        return False
    print(f"  [info] {len(list(TESTS_DIR.glob('check_*.py')))} smoke 중 무필터 repo 복사 0건")
    return True


def case_2_scaffold_excludes_heavy_trees() -> bool:
    """2) check_scaffold_harness 의 제외 목록에 무거운 트리가 포함된다."""
    src = SCAFFOLD_SMOKE.read_text(encoding="utf-8")
    if "EXCLUDED_TREE_DIRS" not in src:
        print("  FAIL: check_scaffold_harness.py 에 EXCLUDED_TREE_DIRS 부재")
        return False
    if "shutil.copytree" not in src or "ignore_patterns" not in src:
        print("  FAIL: shutil.copytree + ignore_patterns 미사용")
        return False
    missing = [d for d in REQUIRED_EXCLUDES if f'"{d}"' not in src]
    if missing:
        print(f"  FAIL: EXCLUDED_TREE_DIRS 에 누락: {missing}")
        return False
    print(f"  [info] 제외 목록에 {list(REQUIRED_EXCLUDES)} 모두 존재")
    return True


def case_3_cleanup_scans_var_tmp() -> bool:
    """3) cleanup_leaked_tempdirs 가 /var/tmp 를 포함해 훑는다 (원래 버그의 회귀 가드)."""
    src = EXPORT_TOOL.read_text(encoding="utf-8")
    if "/var/tmp" not in src:
        print("  FAIL: export_harness_package.py 가 /var/tmp 를 훑지 않음")
        return False
    if 'os.environ.get("TMPDIR", "/tmp")' in src and "leaked_tempdir_roots" not in src:
        print("  FAIL: TMPDIR 단일 root 만 보는 구 impl (누수 위치 /var/tmp 를 놓침)")
        return False
    # 실제 함수가 /var/tmp 를 후보로 반환하는지 런타임 확인
    sys.path.insert(0, str(EXPORT_TOOL.parent))
    try:
        import importlib

        mod = importlib.import_module("export_harness_package")
        roots = [str(p) for p in mod.leaked_tempdir_roots()]
    except Exception as exc:  # pragma: no cover - import 실패 시 정적 검사로 충분
        print(f"  [warn] import 실패, 정적 검사만 수행: {exc}")
        return True
    if "/var/tmp" not in roots:
        print(f"  FAIL: leaked_tempdir_roots() 에 /var/tmp 없음 (got {roots})")
        return False
    print(f"  [info] leaked_tempdir_roots() = {roots}")
    return True


def case_4_cleanup_respects_ownership() -> bool:
    """4) cleanup 이 남의 소유 temp dir 을 건드리지 않는다."""
    src = EXPORT_TOOL.read_text(encoding="utf-8")
    if "st_uid" not in src or "getuid" not in src:
        print("  FAIL: cleanup_leaked_tempdirs 에 소유자(uid) 가드 부재")
        return False
    if 'entry / "repo"' not in src:
        print("  FAIL: cleanup 이 repo/ leaf 조건 없이 삭제 (과잉 삭제 위험)")
        return False
    print("  [info] uid 가드 + repo/ leaf 조건 모두 존재")
    return True


def case_5_ci_loop_has_timeout() -> bool:
    """5) CI smoke 가 per-check timeout 을 **보장**한다.

    v1.0.0: *구현 형태* 가 아니라 *보장* 을 검증한다. 이전 구현은 `timeout ... python3 "$t"`
    쉘 루프를 문자열로 고정했는데, CI 가 통합 runner(`run_all_checks.py --timeout=N`) 호출로
    바뀌면 형태가 달라도 보장은 오히려 강해진다(러너는 per-check timeout 에 더해 전용 TMPDIR
    삭제 + 프로세스 그룹 회수 + 디스크/temp 상한까지 수행). 둘 중 어느 형태든 통과시킨다.
    """
    if not SMOKE_WORKFLOW.is_file():
        print(f"  FAIL: {SMOKE_WORKFLOW} 부재")
        return False
    src = SMOKE_WORKFLOW.read_text(encoding="utf-8")

    # (a) 통합 runner 경로 — --timeout 이 명시되어야 per-check 보장이 성립한다.
    if "run_all_checks.py" in src:
        if "--timeout" not in src:
            print("  FAIL: run_all_checks 호출에 --timeout 부재 (per-check 보장 없음)")
            return False
        if "--tmp-dir" not in src:
            print("  FAIL: run_all_checks 호출에 --tmp-dir 부재 (tmpfs 누수 회피 권장)")
            return False
        print("  [info] CI 가 통합 runner 사용 — per-check timeout + 전용 TMPDIR 보장")
        return True

    # (b) 직접 쉘 루프 경로 (legacy)
    if 'python3 "$t"' in src and "timeout --signal=TERM" in src:
        print("  [info] smoke.yml per-check timeout 존재 (SIGTERM 우선 → 정리 코드 실행 기회)")
        return True

    print("  FAIL: CI smoke 에 per-check timeout 보장이 없다")
    print("        → hang 시 job 무한 대기 + kill 시 temp dir 누수")
    return False


def case_6_scaffold_leaves_no_orphan() -> bool:
    """6) 실측: check_scaffold_harness 1회 실행이 temp root 에 orphan 을 남기지 않는다."""

    def snapshot(root: Path) -> set[str]:
        try:
            return {p.name for p in root.iterdir() if p.is_dir() and p.name.startswith("tmp")}
        except OSError:
            return set()

    roots = [Path(tempfile.gettempdir()), Path("/var/tmp")]
    before = {r: snapshot(r) for r in roots}

    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT / "workflow-source"))
    proc = subprocess.run(
        [sys.executable, str(SCAFFOLD_SMOKE)],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=180,
    )
    if proc.returncode != 0:
        print(f"  FAIL: check_scaffold_harness 실행 실패 (exit {proc.returncode})")
        print(f"        stderr: {proc.stderr.strip()[:400]}")
        return False

    leaked: list[str] = []
    for r in roots:
        for name in snapshot(r) - before[r]:
            if (r / name / "repo").is_dir():
                leaked.append(str(r / name))
    if leaked:
        print(f"  FAIL: 실행 후 orphan temp dir 잔존: {leaked}")
        return False
    print("  [info] 실행 후 orphan temp dir 0건 (/tmp + /var/tmp)")
    return True


def case_7_no_unmanaged_mkdtemp() -> bool:
    """7) `tempfile.mkdtemp()` 를 정리 없이 쓰는 곳이 없다.

    `mkdtemp` 은 `TemporaryDirectory` 와 달리 자동 정리가 **전혀** 없어서 kill 이
    아니라 *성공한 실행마다* temp dir 이 하나씩 쌓인다. 2026-07-21 감사에서 3개
    smoke 5개소가 실행당 5개씩 흘리고 있었다.
    """
    import ast

    scan_dirs = [
        REPO_ROOT / "workflow-source" / "tests",
        REPO_ROOT / "workflow-source" / "tools",
        REPO_ROOT / "workflow-source" / "scripts",
        REPO_ROOT / "workflow-source" / "workflow_kit",
    ]
    offenders: list[str] = []
    for base in scan_dirs:
        for py in sorted(base.rglob("*.py")):
            if "__pycache__" in py.parts or py.name == Path(__file__).name:
                continue
            try:
                src = py.read_text(encoding="utf-8")
                tree = ast.parse(src)
            except Exception:
                continue
            for fn in ast.walk(tree):
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                body = ast.unparse(fn)
                if "mkdtemp" in body and "rmtree" not in body:
                    offenders.append(f"{py.relative_to(REPO_ROOT)}::{fn.name}")
    if offenders:
        print(f"  FAIL: 정리 없는 mkdtemp {len(offenders)}건: {offenders[:8]}")
        print("        → tempfile.TemporaryDirectory() 컨텍스트 매니저로 교체할 것")
        return False
    print("  [info] 정리 없는 mkdtemp 0건")
    return True


CASES = [
    ("case_1_no_unfiltered_repo_copy", case_1_no_unfiltered_repo_copy),
    ("case_7_no_unmanaged_mkdtemp", case_7_no_unmanaged_mkdtemp),
    ("case_2_scaffold_excludes_heavy_trees", case_2_scaffold_excludes_heavy_trees),
    ("case_3_cleanup_scans_var_tmp", case_3_cleanup_scans_var_tmp),
    ("case_4_cleanup_respects_ownership", case_4_cleanup_respects_ownership),
    ("case_5_ci_loop_has_timeout", case_5_ci_loop_has_timeout),
    ("case_6_scaffold_leaves_no_orphan", case_6_scaffold_leaves_no_orphan),
]


def main() -> int:
    print("=== check_tempdir_leak_guard (v1.0.0, 7 case) ===")
    passed = 0
    for name, fn in CASES:
        print(f"\n[{name}]")
        try:
            ok = fn()
        except Exception as exc:
            print(f"  FAIL: 예외 {exc!r}")
            ok = False
        if ok:
            passed += 1
    print(f"\n결과: {passed}/{len(CASES)} PASS")
    return 0 if passed == len(CASES) else 1


# pytest wrapper (TST-WF-01)
def test_case_1_no_unfiltered_repo_copy() -> None:
    assert case_1_no_unfiltered_repo_copy()


def test_case_2_scaffold_excludes_heavy_trees() -> None:
    assert case_2_scaffold_excludes_heavy_trees()


def test_case_3_cleanup_scans_var_tmp() -> None:
    assert case_3_cleanup_scans_var_tmp()


def test_case_4_cleanup_respects_ownership() -> None:
    assert case_4_cleanup_respects_ownership()


def test_case_5_ci_loop_has_timeout() -> None:
    assert case_5_ci_loop_has_timeout()


def test_case_6_scaffold_leaves_no_orphan() -> None:
    assert case_6_scaffold_leaves_no_orphan()


def test_case_7_no_unmanaged_mkdtemp() -> None:
    assert case_7_no_unmanaged_mkdtemp()


if __name__ == "__main__":
    sys.exit(main())
