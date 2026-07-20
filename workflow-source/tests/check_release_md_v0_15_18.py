#!/usr/bin/env python3
"""Smoke test — RELEASE.md cross-validation (v0.15.18+).

`docs/RELEASE.md` 가 릴리스 절차·회귀 표·버전 정보를 정확히 유지하는지
검증한다. 5 cases:

  1) **회귀 표 v0.15.1~v0.15.15 status**: 본 회귀 표의 마지막 행
     `v0.15.1~v0.15.15-beta` 의 release page 상태가 v0.15.15 정식 release
     완료 후 stale 하지 않은지 확인 (✅ 또는 명시적 in-release 표기).
  2) **pyproject version 정합**: 본문에 등장하는 `version 0.15.15` 와
     `workflow-source/pyproject.toml` 의 version 이 일치.
  3) **회귀 표 v0.5.7 행**: wheel packaging 도입 행의 wheel/sdist 가
     `GitHub Release + wheel/sdist` 인지 확인.
  4) **frontmatter stamp**: `- 최종 수정일: 2026-07-18` 이 v0.15.15
     release day 와 정합.
  5) **회귀 표의 모든 vN.N.N 가 Beta-v*.md 파일 존재**: 본문에 등장하는
     주요 release version 들이 `workflow-source/releases/Beta-v*.md` 로
     존재 (드리프트 검출).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
RELEASE_MD_PATH = REPO_ROOT / "docs" / "RELEASE.md"
PYPROJECT_PATH = SOURCE_ROOT / "pyproject.toml"
RELEASES_DIR = SOURCE_ROOT / "releases"

EXPECTED_LAST_UPDATED = "2026-07-18"

# 회귀 표에 등장하는 주요 vN.N.N 패턴 (cross-check anchor)
# 본문에 등장하면 Beta-v<pattern>.md 가 존재해야 함
ANCHOR_VERSIONS = [
    "v0.5.0", "v0.5.7", "v0.5.10", "v0.5.11", "v0.6.0.1",
    "v0.8.0", "v0.9.0", "v0.9.1", "v0.10.0", "v0.10.2",
    "v0.10.4", "v0.11.0", "v0.11.18", "v0.11.21", "v0.11.22",
    "v0.15.0", "v0.15.15",
]


def _load_release_md() -> str:
    if not RELEASE_MD_PATH.is_file():
        raise AssertionError(f"RELEASE.md 부재: {RELEASE_MD_PATH}")
    return RELEASE_MD_PATH.read_text(encoding="utf-8")


def _load_pyproject() -> str:
    if not PYPROJECT_PATH.is_file():
        raise AssertionError(f"pyproject.toml 부재: {PYPROJECT_PATH}")
    return PYPROJECT_PATH.read_text(encoding="utf-8")


def _list_release_notes() -> set[str]:
    """Beta-v*.md 파일들의 version stem 반환. 예: {'v0.5.0', 'v0.15.15'}"""
    if not RELEASES_DIR.is_dir():
        return set()
    notes: set[str] = set()
    for p in RELEASES_DIR.glob("Beta-v*.md"):
        # Beta-v0.15.15.md -> v0.15.15
        stem = p.stem  # 'Beta-v0.15.15'
        if stem.startswith("Beta-"):
            notes.add(stem[len("Beta-"):])
    return notes


def case_1_regression_last_row_stale() -> bool:
    """1) 회귀 표 마지막 행 (v0.15.1~v0.15.15) 의 release page 상태 검증.

    v0.15.15 정식 release 가 완료된 상태이므로, 마지막 행은 ✅ 여야 함.
    `**in release**` 표기는 release 직전 단계 표기이므로 stale."""
    content = _load_release_md()
    # 마지막 행 (v0.15.1~v0.15.15-beta) 의 release page 컬럼 추출
    m = re.search(
        r"v0\.15\.1~v0\.15\.15-beta\s*\|[^\n]*\|\s*\*?\*?(in release|pending|✅)[^\n]*\|",
        content,
    )
    if not m:
        print("  FAIL: 회귀 표의 'v0.15.1~v0.15.15-beta' 행을 찾지 못함")
        return False
    cell = m.group(0)
    if "**in release**" in cell or "pending" in cell:
        print(f"  FAIL: 마지막 행 status 가 stale — '{cell.split('|')[-2].strip()}' "
              f"(v0.15.15 정식 release 완료 후 ✅ 여야 함)")
        return False
    if "✅" not in cell:
        print(f"  FAIL: 마지막 행 status 가 ✅ 가 아님 — '{cell[:100]}'")
        return False
    print(f"  [info] v0.15.1~v0.15.15 행 release page = ✅ 정합")
    return True


def case_2_pyproject_version() -> bool:
    """2) 본문에 pyproject.toml version 이 등장 (어떤 표현이든).

    허용 패턴: 'version: 0.15.15', 'version 0.15.15', 'version=0.15.15',
    'v0.15.15' 등. 정확한 일치가 아니라 '본문에 version X 가 명시'만 검증."""
    pyproject = _load_pyproject()
    m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    if not m:
        print("  FAIL: pyproject.toml 에서 version 추출 실패")
        return False
    actual = m.group(1)
    content = _load_release_md()
    # 5가지 표현 중 하나라도 등장하면 PASS
    patterns = [
        f"version {actual}",        # "version 0.15.15"
        f"version: {actual}",       # "version: 0.15.15"
        f"version={actual}",        # "version=0.15.15"
        f"v{actual}",               # "v0.15.15"
        f"v{actual}-beta",          # "v0.15.15-beta"
    ]
    if not any(p in content for p in patterns):
        print(f"  FAIL: RELEASE.md 본문에 '{actual}' version stamp 부재 (5 pattern 시도)")
        return False
    matched = next(p for p in patterns if p in content)
    print(f"  [info] pyproject version={actual} = RELEASE.md '{matched}' 정합")
    return True


def case_3_wheel_packaging_row() -> bool:
    """3) 회귀 표의 v0.5.7 행 wheel/sdist 컬럼이 'GitHub Release + wheel/sdist' 인지."""
    content = _load_release_md()
    m = re.search(
        r"v0\.5\.7-beta\s*\|\s*\*?\*?GitHub Release \+ wheel/sdist\*?\*?",
        content,
    )
    if not m:
        print("  FAIL: v0.5.7 행의 wheel/sdist 컬럼이 'GitHub Release + wheel/sdist' 가 아님")
        return False
    print(f"  [info] v0.5.7 행 wheel/sdist = 'GitHub Release + wheel/sdist' 정합")
    return True


def case_4_frontmatter_stamp() -> bool:
    """4) frontmatter `- 최종 수정일: 2026-07-18` 정합."""
    content = _load_release_md()
    m = re.search(r"^-\s+최종\s*수정일\s*:\s*(\S+)", content, re.MULTILINE)
    if not m:
        print("  FAIL: frontmatter '최종 수정일' line 부재")
        return False
    actual = m.group(1).strip()
    if actual != EXPECTED_LAST_UPDATED:
        print(f"  FAIL: frontmatter stamp 불일치 — actual={actual} expected={EXPECTED_LAST_UPDATED}")
        return False
    print(f"  [info] frontmatter stamp 정합: {actual}")
    return True


def case_5_release_notes_exist() -> bool:
    """5) 회귀 표의 주요 version 들이 Beta-v*.md 로 존재."""
    content = _load_release_md()
    notes = _list_release_notes()
    missing: list[str] = []
    for ver in ANCHOR_VERSIONS:
        # 본문에 등장 (v0.5.7, v0.5.7-beta 등 다양한 표기 흡수)
        pattern = re.escape(ver)
        if not re.search(pattern, content):
            # 본문에도 없으면 skip (anchor list 자체 drift)
            continue
        if ver not in notes:
            missing.append(ver)
    if missing:
        print(f"  FAIL: RELEASE.md 에 등장하지만 Beta-v*.md 부재: {missing}")
        return False
    found = sum(1 for v in ANCHOR_VERSIONS if v in notes)
    print(f"  [info] {found}/{len(ANCHOR_VERSIONS)} anchor versions 모두 Beta-v*.md 존재 ({len(notes)} total)")
    return True


def main() -> int:
    cases = [
        ("case_1_regression_last_row_stale", case_1_regression_last_row_stale),
        ("case_2_pyproject_version", case_2_pyproject_version),
        ("case_3_wheel_packaging_row", case_3_wheel_packaging_row),
        ("case_4_frontmatter_stamp", case_4_frontmatter_stamp),
        ("case_5_release_notes_exist", case_5_release_notes_exist),
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


# v0.15.18+: pytest-friendly wrappers (TST-WF-01 정합 — def test_ 패턴 추가).
# 기존 `def case_*` 와 `def main()` 정합 유지. pytest collection 에서도 5 case 모두 검증.
def test_case_1_regression_last_row_stale() -> None:
    assert case_1_regression_last_row_stale(), "case_1_regression_last_row_stale FAIL"


def test_case_2_pyproject_version() -> None:
    assert case_2_pyproject_version(), "case_2_pyproject_version FAIL"


def test_case_3_wheel_packaging_row() -> None:
    assert case_3_wheel_packaging_row(), "case_3_wheel_packaging_row FAIL"


def test_case_4_frontmatter_stamp() -> None:
    assert case_4_frontmatter_stamp(), "case_4_frontmatter_stamp FAIL"


def test_case_5_release_notes_exist() -> None:
    assert case_5_release_notes_exist(), "case_5_release_notes_exist FAIL"


if __name__ == "__main__":
    raise SystemExit(main())
