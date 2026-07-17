#!/usr/bin/env python3
"""Smoke test — v0.15.4+ 3rd deprecation cycle 부재 검증 (ADR-007 close-out).

ADR-007 placeholder 의 정공법 ("3rd cycle 영향 후보 부재 시 accepted (no-op) 전환")
을 v0.15.3+ 시점 codebase re-scan 으로 verify. v0.11.24 와 v0.15.3 codebase 가
많이 달라졌으므로, 다음 3 case 를 verify:

  1) `DeprecationWarning` literal 을 *emit* 하는 call site 가 infrastructure
     (workflow_kit.common.decorators:v0_7_4_deprecated) 안에만 존재. 다른 module
     (workflow_kit 그 외, skills/, mcp_servers/, harness 등) 에서는 *직접* emit
     하지 않음.
  2) `__deprecated__ = True` marker 가 decorators.py 안에서만 설정됨. 다른
     module 에서는 marker 0개.
  3) `v0_7_4_deprecated` decorator 의 *실제 사용처* = 0개. decorator 자체는
     정의돼 있으나 apply 된 symbol 이 0개 → 3rd cycle 영향 symbol 부재.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_SOURCE = REPO_ROOT / "workflow-source"


# infrastructure 가 정의된 module (allowed_to_emit)
ALLOWED_DEPRECATION_INFRASTRUCTURE = {
    "workflow_kit/common/decorators.py",  # v0_7_4_deprecated decorator 본체
    "workflow_kit/__init__.py",            # docstring only (Deprecation policy 설명)
}

# test/docstring/comments 안에 mention 되는 것은 emit 이 아니므로 제외
# 본 smoke 는 "실제 call site" 만 detect.
# 즉, `warnings.warn(..., DeprecationWarning)` pattern 의 active call.

DEPRECATION_WARN_CALL_RE = re.compile(
    r"warnings\.warn\s*\([^)]*DeprecationWarning"
)


def _is_in_docstring_or_comment(file_path: Path, line_number: int) -> bool:
    # 주어진 (file, line) 이 docstring 또는 comment 안에 있는지 확인.
    # heuristic: 위쪽 line 들을 scan 하면서 triple-quote marker 의 짝/홀 판정.
    # 짝수가 나오면 docstring 이 *닫혔거나* 시작도 안 했음 (즉, 코드 영역).
    # 홀수가 나오면 docstring 이 *열려있는 상태* (즉, docstring 안).
    # 단순 context 기반 heuristic 으로, module-level docstring (line 1~10) 도 cover.
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError:
        return False
    lines = content.splitlines()
    if line_number - 1 >= len(lines):
        return False
    line = lines[line_number - 1].lstrip()
    if line.startswith("#"):
        return True
    # file 전체 처음부터 line_number 까지 scan
    context = "\n".join(lines[:line_number])
    DDD = '"""'
    SSS = '\x27\x27\x27'  # ''' avoid escape issue
    triple_double = context.count(DDD)
    triple_single = context.count(SSS)
    # 짝수 = 닫힘 (즉, 코드 영역), 홀수 = 열림 (docstring 안)
    if triple_double % 2 == 1 or triple_single % 2 == 1:
        return True
    return False


def _scan_python_files_for_deprecation_warns(exclude_paths: set[Path]) -> list[tuple[Path, int, str]]:
    """workflow-source 의 모든 .py file 에서 DeprecationWarning emit call site 검색.

    docstring/comment 안의 mention 은 제외.

    Returns:
        list of (file_path, line_number, matched_line)
    """
    matches: list[tuple[Path, int, str]] = []
    for py in WORKFLOW_SOURCE.rglob("*.py"):
        # exclude paths
        rel = py.relative_to(REPO_ROOT)
        if any(str(rel).startswith(str(ex)) for ex in exclude_paths):
            continue
        # smoke self-reference 제외
        if py.name == "check_deprecation_3rd_cycle_v0_15_4.py":
            continue
        try:
            content = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for ln, line in enumerate(content.splitlines(), start=1):
            if DEPRECATION_WARN_CALL_RE.search(line):
                if _is_in_docstring_or_comment(py, ln):
                    continue
                matches.append((py, ln, line.strip()))
    return matches


def _scan_python_files_for_deprecated_markers() -> list[tuple[Path, int, str]]:
    """__deprecated__ marker 설정 call site 검색.

    docstring/comment 안의 mention 은 제외. 함수/클래스 attribute 로 *설정*되는
    패턴만 detect.
    """
    matches: list[tuple[Path, int, str]] = []
    deprecated_attr_re = re.compile(r"__deprecated__\s*=\s*True")
    for py in WORKFLOW_SOURCE.rglob("*.py"):
        rel = py.relative_to(REPO_ROOT)
        if any(str(rel).startswith(str(ex)) for ex in {Path("build"), Path(".venv")}):
            continue
        if py.name == "check_deprecation_3rd_cycle_v0_15_4.py":
            continue
        try:
            content = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for ln, line in enumerate(content.splitlines(), start=1):
            if deprecated_attr_re.search(line):
                if _is_in_docstring_or_comment(py, ln):
                    continue
                matches.append((py, ln, line.strip()))
    return matches


def _scan_v0_7_4_deprecated_uses() -> list[tuple[Path, int, str]]:
    """@v0_7_4_deprecated decorator 의 실제 사용처 검색.

    docstring (사용 예시) 의 mention 은 제외하고, 실제 decorator apply 만 detect.
    Pattern: line 시작 또는 whitespace 후 `@v0_7_4_deprecated(` 로 시작.
    """
    matches: list[tuple[Path, int, str]] = []
    apply_re = re.compile(r"^\s*@v0_7_4_deprecated\s*\(")
    for py in WORKFLOW_SOURCE.rglob("*.py"):
        rel = py.relative_to(REPO_ROOT)
        if any(str(rel).startswith(str(ex)) for ex in {Path("build"), Path(".venv")}):
            continue
        if py.name == "check_deprecation_3rd_cycle_v0_15_4.py":
            continue
        try:
            content = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for ln, line in enumerate(content.splitlines(), start=1):
            if apply_re.search(line):
                if _is_in_docstring_or_comment(py, ln):
                    continue
                matches.append((py, ln, line.strip()))
    return matches


def case_1_deprecation_warning_emit_infrastructure_only() -> bool:
    """1) DeprecationWarning emit call site 가 infrastructure (decorators.py) 안에만 존재."""
    exclude = {Path("build"), Path(".venv"), Path("tests")}
    matches = _scan_python_files_for_deprecation_warns(exclude_paths=exclude)
    # 각 match 의 file 이 ALLOWED 에 속하는지 확인
    non_infrastructure: list[tuple[Path, int, str]] = []
    for fpath, ln, line in matches:
        rel = fpath.relative_to(REPO_ROOT)
        rel_str = str(rel)
        if any(rel_str == allowed or rel_str.endswith(allowed) for allowed in ALLOWED_DEPRECATION_INFRASTRUCTURE):
            continue
        # decorators.py 자체는 infrastructure
        if "decorators.py" in rel_str:
            continue
        non_infrastructure.append((fpath, ln, line))
    if non_infrastructure:
        print(f"  FAIL: non-infrastructure DeprecationWarning emit 발견 ({len(non_infrastructure)}건):")
        for f, l, line in non_infrastructure[:5]:
            print(f"    {f.relative_to(REPO_ROOT)}:{l}: {line[:80]}")
        return False
    # infrastructure 자체는 있어야 함 (없으면 decorator 가 정의 안 된 상태)
    infra_hits = [m for m in matches if "decorators.py" in str(m[0])]
    if not infra_hits:
        print(f"  FAIL: infrastructure 자체도 emit 0건 (decorator 정의 부재)")
        return False
    print(f"  [info] infrastructure emit: {len(infra_hits)}건 (decorators.py)")
    return True


def case_2_deprecated_marker_infrastructure_only() -> bool:
    """2) __deprecated__ = True marker 가 infrastructure (decorators.py) 안에서만 설정."""
    matches = _scan_python_files_for_deprecated_markers()
    non_infrastructure: list[tuple[Path, int, str]] = []
    for fpath, ln, line in matches:
        rel = fpath.relative_to(REPO_ROOT)
        rel_str = str(rel)
        if "decorators.py" in rel_str:
            continue
        non_infrastructure.append((fpath, ln, line))
    if non_infrastructure:
        print(f"  FAIL: non-infrastructure __deprecated__ marker 발견 ({len(non_infrastructure)}건):")
        for f, l, line in non_infrastructure[:5]:
            print(f"    {f.relative_to(REPO_ROOT)}:{l}: {line[:80]}")
        return False
    infra_hits = [m for m in matches if "decorators.py" in str(m[0])]
    if not infra_hits:
        print(f"  FAIL: infrastructure marker 0건 (decorator 정의 부재)")
        return False
    print(f"  [info] infrastructure marker: {len(infra_hits)}건 (decorators.py)")
    return True


def case_3_v0_7_4_deprecated_no_actual_use() -> bool:
    """3) v0_7_4_deprecated decorator 의 실제 사용처 = 0개."""
    matches = _scan_v0_7_4_deprecated_uses()
    # docstring 의 usage example 은 제외되어야 함 (정규식 precision)
    # 실제 apply 만 detect
    non_docstring: list[tuple[Path, int, str]] = []
    for fpath, ln, line in matches:
        rel = fpath.relative_to(REPO_ROOT)
        rel_str = str(rel)
        # decorators.py 안의 docstring 예시는 제외 (line 자체에 @ 표시가 있어 hit 가능)
        # 정밀도: line 의 이전/다음 line 이 docstring marker 라면 제외
        try:
            content = fpath.read_text(encoding="utf-8")
        except OSError:
            continue
        lines = content.splitlines()
        # 위 5 line context 확인
        start = max(0, ln - 5)
        context = "\n".join(lines[start:ln + 1])
        if '"""' in context or "'''" in context:
            # docstring 안이면 제외
            continue
        non_docstring.append((fpath, ln, line))
    if non_docstring:
        print(f"  FAIL: v0_7_4_deprecated 실제 사용처 발견 ({len(non_docstring)}건):")
        for f, l, line in non_docstring[:5]:
            print(f"    {f.relative_to(REPO_ROOT)}:{l}: {line[:80]}")
        return False
    return True


def main() -> int:
    cases = [
        ("case_1_deprecation_warning_emit_infrastructure_only", case_1_deprecation_warning_emit_infrastructure_only),
        ("case_2_deprecated_marker_infrastructure_only", case_2_deprecated_marker_infrastructure_only),
        ("case_3_v0_7_4_deprecated_no_actual_use", case_3_v0_7_4_deprecated_no_actual_use),
    ]
    results: list[tuple[str, bool]] = []
    for name, fn in cases:
        results.append((name, fn()))
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {name}")
    print(f"\n=== {passed}/{len(cases)} PASS ===")
    if passed != len(cases):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
