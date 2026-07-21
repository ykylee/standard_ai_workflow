#!/usr/bin/env python3
"""Smoke test — CODE_INDEX.md cross-validation (v0.15.17+).

`docs/CODE_INDEX.md` 가 코드베이스 카운트와 정합을 유지하는지 검증한다.
코드 구조와 카운트가 drift 하면 index 의 신뢰성이 떨어지므로, 핵심 정합
항목을 자동 검증한다. 5 cases:

  1) **smoke 파일 수**: CODE_INDEX.md 가 "192개 check_*.py 스모크" 라고
     적었을 때 실제 `workflow-source/tests/check_*.py` 파일 수가 일치.
  2) **harness 디렉터리 수**: "10개 지원 하네스" 와 실제
     `workflow-source/harnesses/` 디렉터리 수 (10 + `_template`) 가 일치.
  3) **skill 디렉터리 수**: "11 + task-modes (12 total)" 와 실제
     `workflow-source/skills/` 디렉터리 수 (12 + `__pycache__` 등 제외) 가 일치.
  4) **version stamp 정합**: 본문의 "version 0.15.15" 와
     `workflow-source/pyproject.toml` 의 version 이 일치.
  5) **frontmatter stamp**: `- 최종 수정일: 2026-07-18` 이 v0.15.15
     release day 와 정합.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
CODE_INDEX_PATH = REPO_ROOT / "docs" / "CODE_INDEX.md"
PYPROJECT_PATH = SOURCE_ROOT / "pyproject.toml"
TESTS_DIR = SOURCE_ROOT / "tests"
HARNESSES_DIR = SOURCE_ROOT / "harnesses"
SKILLS_DIR = SOURCE_ROOT / "skills"

EXPECTED_LAST_UPDATED = "2026-07-21"


def _load_code_index() -> str:
    if not CODE_INDEX_PATH.is_file():
        raise AssertionError(f"CODE_INDEX.md 부재: {CODE_INDEX_PATH}")
    return CODE_INDEX_PATH.read_text(encoding="utf-8")


def _load_pyproject() -> str:
    if not PYPROJECT_PATH.is_file():
        raise AssertionError(f"pyproject.toml 부재: {PYPROJECT_PATH}")
    return PYPROJECT_PATH.read_text(encoding="utf-8")


def _count_py_files(d: Path) -> int:
    if not d.is_dir():
        return 0
    return len([p for p in d.glob("check_*.py") if p.is_file()])


def _count_harness_dirs() -> tuple[int, list[str]]:
    if not HARNESSES_DIR.is_dir():
        return 0, []
    names = sorted([e.name for e in HARNESSES_DIR.iterdir() if e.is_dir()])
    return len(names), names


def _count_skill_dirs() -> tuple[int, list[str]]:
    """skill 디렉터리 수. `__pycache__`, `__init__` 같은 non-skill entry 제외."""
    if not SKILLS_DIR.is_dir():
        return 0, []
    skip = {"__pycache__"}
    names = sorted([e.name for e in SKILLS_DIR.iterdir() if e.is_dir() and e.name not in skip])
    return len(names), names


def _extract_count_from_text(content: str, pattern: str, group: int = 1) -> int | None:
    """CODE_INDEX 본문에서 `pattern` 의 NNN 추출. 실패 시 None."""
    m = re.search(pattern, content)
    if not m:
        return None
    try:
        return int(m.group(group))
    except (ValueError, IndexError):
        return None


def case_1_smoke_count() -> bool:
    """1) 실제 check_*.py 파일 수가 CODE_INDEX 의 'NNN개 check_*.py' 와 일치."""
    actual = _count_py_files(TESTS_DIR)
    content = _load_code_index()
    claim = _extract_count_from_text(content, r"(\d+)개\s+check_\*\.py")
    if claim is None:
        print(f"  FAIL: CODE_INDEX 본문에서 smoke 카운트 stamp 추출 실패 (actual={actual})")
        return False
    if actual != claim:
        print(f"  FAIL: smoke 파일 수 불일치 — actual={actual}, CODE_INDEX claim={claim}")
        return False
    print(f"  [info] {actual} check_*.py files = CODE_INDEX '{claim}개 check_*.py' 정합")
    return True


def case_2_harness_count() -> bool:
    """2) 실제 harness 디렉터리 수가 CODE_INDEX 의 'NNN개 지원 하네스' 와 정합.
    
    `_template` (신규 하네스 추가용 템플릿) + `custom` (caller 가 wire-up 하는 neutral adapter,
    check_harness_v0_15_9 의 EXCLUDED 정공법과 정합) 제외.
    """
    _, names = _count_harness_dirs()
    actual_harness = [n for n in names if n not in {"_template", "custom"}]
    content = _load_code_index()
    claim = _extract_count_from_text(content, r"(\d+)개\s+지원\s+하네스")
    if claim is None:
        print(f"  FAIL: CODE_INDEX 본문에서 harness 카운트 stamp 추출 실패")
        return False
    if len(actual_harness) != claim:
        print(f"  FAIL: harness 수 불일치 — actual={len(actual_harness)} ({actual_harness}), claim={claim}")
        return False
    print(f"  [info] {len(actual_harness)} harness (excluding _template + custom) = CODE_INDEX '{claim}개 지원 하네스' 정합")
    return True


def case_3_skill_count() -> bool:
    """3) 실제 skill 디렉터리 수가 CODE_INDEX 의 'NNN dirs' 와 정합.

    CODE_INDEX 본문이 '— NNN + ... (NN dirs)' 형식이므로 두 자리 모두 추출
    해서 비교. 안정 형식: '— N + ... (N dirs)' 또는 '— NN + ... (NN dirs)'."""
    count, names = _count_skill_dirs()
    content = _load_code_index()
    # 패턴: `— NNN + something (NN dirs)` 또는 `— N + something (N dirs)`
    m = re.search(r"—\s+(\d+)\s*\+[^()]*\((\d+)\s+dirs\)", content)
    if not m:
        print(f"  FAIL: CODE_INDEX 본문에서 skill 카운트 stamp 추출 실패 (actual={count})")
        return False
    claim = int(m.group(2))  # 'NN dirs' 의 NN
    if count != claim:
        print(f"  FAIL: skill 수 불일치 — actual={count} ({names}), CODE_INDEX claim={claim}")
        return False
    print(f"  [info] {count} skills = CODE_INDEX '{claim} dirs' 정합")
    return True


def case_4_version_stamp() -> bool:
    """4) CODE_INDEX 본문의 'version 0.15.15' 와 pyproject.toml 의 version 이 일치."""
    pyproject = _load_pyproject()
    m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    if not m:
        print("  FAIL: pyproject.toml 에서 version 추출 실패")
        return False
    actual = m.group(1)
    content = _load_code_index()
    if f"version {actual}" not in content:
        print(f"  FAIL: CODE_INDEX 본문에 'version {actual}' stamp 부재")
        return False
    print(f"  [info] pyproject version={actual} = CODE_INDEX 'version {actual}' 정합")
    return True


def case_5_frontmatter_stamp() -> bool:
    """5) frontmatter `- 최종 수정일: 2026-07-18` 이 v0.15.15 release day 와 정합."""
    content = _load_code_index()
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


def main() -> int:
    cases = [
        ("case_1_smoke_count", case_1_smoke_count),
        ("case_2_harness_count", case_2_harness_count),
        ("case_3_skill_count", case_3_skill_count),
        ("case_4_version_stamp", case_4_version_stamp),
        ("case_5_frontmatter_stamp", case_5_frontmatter_stamp),
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


# v0.15.17+: pytest-friendly wrappers (TST-WF-01 정합 — def test_ 패턴 추가).
# 기존 `def case_*` 와 `def main()` 정합 유지. pytest collection 에서도 5 case 모두 검증.
def test_case_1_smoke_count() -> None:
    assert case_1_smoke_count(), "case_1_smoke_count FAIL"


def test_case_2_harness_count() -> None:
    assert case_2_harness_count(), "case_2_harness_count FAIL"


def test_case_3_skill_count() -> None:
    assert case_3_skill_count(), "case_3_skill_count FAIL"


def test_case_4_version_stamp() -> None:
    assert case_4_version_stamp(), "case_4_version_stamp FAIL"


def test_case_5_frontmatter_stamp() -> None:
    assert case_5_frontmatter_stamp(), "case_5_frontmatter_stamp FAIL"


if __name__ == "__main__":
    raise SystemExit(main())
