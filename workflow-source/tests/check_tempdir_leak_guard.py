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
5. 게이트 runner(`run_all_checks.py`)의 per-check timeout 이 **기본으로** 켜져 있다.
   (2026-09-23 CI workflow 폐지(main-022) 전에는 smoke.yml 의 호출을 쟀다 — 게이트가
   로컬 runner 로 옮겨 가 보장의 자리도 runner 기본값으로 옮겼다.)
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
GATE_RUNNER = TESTS_DIR / "run_all_checks.py"

# 복사 staging 에서 반드시 제외되어야 하는 무거운 트리
REQUIRED_EXCLUDES = (".venv", ".git", "node_modules", "__pycache__")


def _cleanup_roots() -> list[Path]:
    """정리 도구(`cleanup_leaked_tempdirs`) 가 **실제로 훑는** temp root 목록.

    정본은 `export_harness_package.leaked_tempdir_roots()` 다 — 후보는 플랫폼마다
    다르다 (POSIX: /tmp · /var/tmp / Windows: %TEMP% · D:\\tmp). 정본을 못 읽으면
    (import 실패) 플랫폼 기본값으로 물러난다 — 측정 대상이 사라지진 않는다.
    """
    fallback = [Path(tempfile.gettempdir()), Path("/var/tmp")]
    try:
        sys.path.insert(0, str(EXPORT_TOOL.parent))
        import importlib

        mod = importlib.import_module("export_harness_package")
        roots = [Path(p) for p in mod.leaked_tempdir_roots()]
    except Exception as exc:  # pragma: no cover - import 실패 시 기본값으로
        print(f"  [warn] 정본 후보 목록을 못 읽었다 ({exc}) — 기본 root 로 잰다")
        return fallback
    return roots or fallback


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
    """3) cleanup_leaked_tempdirs 가 /var/tmp 를 포함해 훑는다 (원래 버그의 회귀 가드).

    2026-10-31 Windows 실측: 이 case 가 POSIX 전용 경로를 **그대로 요구**해 Windows 에서
    늘 red 였다 — `Path("/var/tmp")` 는 `D:\\var\\tmp` 로落到, 그 디렉터리는 Windows 에
    없다. 그래서 `leaked_tempdir_roots()` 는 그 루트를 후보로 돌려줄 수 없다
    (존재하지 않는 디렉터리는 후보가 아니다 — 구현이 옳고 **요구**가 플랫폼 사실에
    묶여 있었다).

    계약의 본질은 "누수가 쌓이는 temp root 를 **여러 개** 훑는다" 다. 그래서 판정을
    그 플랫폼에서 성립하는 형태로 바꾼다:

    - **정적** (양쪽 공통): 구현이 `/var/tmp` 를 후보로 **mentions** 해야 하고,
      후보가 하나뿐인 구 impl 로 되돌아가지 않아야 한다.
    - **런타임**: POSIX 는 `/var/tmp` 가 실제 후보에 들어 있어야 한다 (원래 버그의
      회귀 가드 — 그대로). Windows 는 그 플랫폼의 temp root (`%TEMP%`) 가 실제
      후보에 들어 있어야 한다 (단일 root impl 로의 회귀를 막는다).
    """
    src = EXPORT_TOOL.read_text(encoding="utf-8")
    if "/var/tmp" not in src:
        print("  FAIL: export_harness_package.py 가 /var/tmp 를 훑지 않음")
        return False
    if 'os.environ.get("TMPDIR", "/tmp")' in src and "leaked_tempdir_roots" not in src:
        print("  FAIL: TMPDIR 단일 root 만 보는 구 impl (누수 위치 /var/tmp 를 놓침)")
        return False
    # 후보가 **여러 개** 라는 계약 — 정적으로 못 박는다. 런타임 후보 수는 그 호스트에
    # 어떤 temp root 가 존재하느냐에 달려 있어 플랫폼마다 달라진다 (Windows: %TEMP% ·
    # D:\tmp / POSIX: /tmp · /var/tmp). 그래서 "구 후보가 몇 개인가" 대신 "구 impl 이
    # 후보를 어디서 모으는가" 를 본다 — 단일 root impl(원래 버그)이면 `gettempdir()`
    # 가 후보 목록에 없다.
    if "tempfile.gettempdir()" not in src:
        print("  FAIL: 후보 root 목록이 tempfile.gettempdir() 를 넣지 않는다 — "
              "단일 root impl (원래 버그) 위험")
        return False
    # 실제 함수가 그 플랫폼의 temp root 를 후보로 반환하는지 런타임 확인
    sys.path.insert(0, str(EXPORT_TOOL.parent))
    try:
        import importlib

        mod = importlib.import_module("export_harness_package")
        roots = [str(p) for p in mod.leaked_tempdir_roots()]
    except Exception as exc:  # pragma: no cover - import 실패 시 정적 검사로 충분
        print(f"  [warn] import 실패, 정적 검사만 수행: {exc}")
        return True
    # v1.1.2: 문자열 `"/var/tmp"` 를 그대로 찾으면 **macOS 에서 늘 red** 다.
    # `leaked_tempdir_roots()` 는 후보를 `resolve()` 해서 돌려주는데, macOS 는
    # `/var` 가 `/private/var` 심볼릭이라 결과가 `/private/var/tmp` 가 된다.
    # 구현은 정상이고 검사가 플랫폼을 못 넘긴 것이었다 — resolve 된 형태로 비교한다.
    # Windows 에서는 `/var/tmp` 자체가 없으므로 **그 플랫폼의** temp root 를 요구한다
    # (경로 표기는 저장소 규약상 POSIX 다 — 판정 대상만 그 플랫폼에서 성립하게 한다).
    if os.name == "nt":
        expected = str(Path(tempfile.gettempdir()).resolve())
    else:
        expected = str(Path("/var/tmp").resolve())
    if expected not in roots:
        print(f"  FAIL: leaked_tempdir_roots() 에 {expected} 없음 (got {roots})")
        return False
    print(f"  [info] leaked_tempdir_roots() = {roots} (expected root {expected})")
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


def case_5_runner_has_default_timeout() -> bool:
    """5) 게이트 runner 가 per-check timeout 을 **기본으로** 보장한다.

    CI 폐지(TASK-2026-09-23-main-022) 후 게이트는 로컬 `run_all_checks.py` 다. 인자
    없이 돌려도 per-check timeout 이 걸려야 hang 이 무한 대기가 되지 않는다 (runner 는
    timeout 에 더해 전용 TMPDIR 삭제 + 프로세스 그룹 회수까지 수행). 기본값이 사라지거나
    0 이 되면 사람이 `--timeout` 을 잊는 순간 보장이 없어진다.
    """
    import re

    if not GATE_RUNNER.is_file():
        print(f"  FAIL: {GATE_RUNNER} 부재")
        return False
    src = GATE_RUNNER.read_text(encoding="utf-8")
    match = re.search(r'add_argument\(\s*"--timeout"\s*,[^)]*?default\s*=\s*(\d+)', src)
    if match is None:
        print("  FAIL: runner 의 --timeout 기본값을 찾지 못했다 (per-check 보장 없음)")
        return False
    default = int(match.group(1))
    if default <= 0:
        print(f"  FAIL: runner 의 --timeout 기본값이 {default} 다 — per-check 보장 없음")
        return False
    if '"--tmp-dir"' not in src:
        print("  FAIL: runner 에 --tmp-dir 이 없다 (tmpfs 누수 회피 수단 부재)")
        return False
    print(f"  [info] runner 기본 per-check timeout {default}s + --tmp-dir 지원")
    return True


def case_6_scaffold_leaves_no_orphan() -> bool:
    """6) 실측: check_scaffold_harness 1회 실행이 temp root 에 orphan 을 남기지 않는다.

    재는 root 는 **정리 도구가 실제로 훑는 root** 와 같아야 한다 — 2026-10-31
    Windows 실측: 이 case 가 `gettempdir()` + `/var/tmp` 만 봤다. Windows 에선
    `/var/tmp` 가 `D:\\var\\tmp` 로 존재하지 않는 경로라 빈 집합이 되고, 정리 도구가
    **훑는** `D:\\tmp` 는 보지 않았다 — 즉 누수가 쌓일 수 있는 그 루트를 못 보는
    모양이었다. 그래서 후보 목록은 정본(`leaked_tempdir_roots()`)에서 가져온다.
    """

    def snapshot(root: Path) -> set[str]:
        try:
            return {p.name for p in root.iterdir() if p.is_dir() and p.name.startswith("tmp")}
        except OSError:
            return set()

    roots = _cleanup_roots()
    before = {r: snapshot(r) for r in roots}

    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT / "workflow-source"))
    proc = subprocess.run(
        [sys.executable, str(SCAFFOLD_SMOKE)],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=180, encoding="utf-8", errors="replace"
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
    print(f"  [info] 실행 후 orphan temp dir 0건 (재 본 root: "
          f"{', '.join(str(r) for r in roots)})")
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
        REPO_ROOT / "workflow-source" / "workflow_kit" / "tools",
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
    ("case_5_runner_has_default_timeout", case_5_runner_has_default_timeout),
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


def test_case_5_runner_has_default_timeout() -> None:
    assert case_5_runner_has_default_timeout()


def test_case_6_scaffold_leaves_no_orphan() -> None:
    assert case_6_scaffold_leaves_no_orphan()


def test_case_7_no_unmanaged_mkdtemp() -> None:
    assert case_7_no_unmanaged_mkdtemp()


if __name__ == "__main__":
    sys.exit(main())
