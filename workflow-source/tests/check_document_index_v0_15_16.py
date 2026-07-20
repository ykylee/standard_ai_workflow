#!/usr/bin/env python3
"""Smoke test — DOCUMENT_INDEX.md cross-validation (v0.15.16+).

`docs/DOCUMENT_INDEX.md` 가 영구 지식 자산의 SSOT 인덱스 역할을 유지하는지
검증한다. 4 cases:

  1) **상대 링크 정합**: 본문의 `./...` 링크 (PROJECT_PROFILE, CODE_INDEX,
     RELEASE, INSTALLATION_AND_USAGE, index, architecture/...) 가 file
     system 에 모두 존재.
  2) **외부 GitHub 링크 정합**: 본문의 `github.com/.../blob/main/docs/...`
     경로가 저장소 `docs/` 트리에 실제로 존재 (5 file sample).
  3) **frontmatter 정합**: `- 최종 수정일: 2026-07-18` stamp 가 v0.15.15
     release day 와 정합.
  4) **4 카테고리 섹션 헤더**: `## 1. 프로젝트 설계`, `## 2. 개발 및 표준`,
     `## 3. 분석 및 계획`, `## 4. 보존` 모두 존재.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
DOCUMENT_INDEX_PATH = DOCS_DIR / "DOCUMENT_INDEX.md"

# v0.15.15 release day (cross-check stamp)
EXPECTED_LAST_UPDATED = "2026-07-18"
EXPECTED_VERSION_STAMP = "v0.15.15"

REQUIRED_SECTIONS = [
    "## 1. 프로젝트 설계",
    "## 2. 개발 및 표준",
    "## 3. 분석 및 계획",
    "## 4. 보존",
]


def _load_document_index() -> str:
    if not DOCUMENT_INDEX_PATH.is_file():
        raise AssertionError(f"DOCUMENT_INDEX.md 부재: {DOCUMENT_INDEX_PATH}")
    return DOCUMENT_INDEX_PATH.read_text(encoding="utf-8")


def case_1_relative_links() -> bool:
    """1) 본문의 `./...` 상대 링크가 모두 file system 에 존재."""
    content = _load_document_index()
    # extract ./foo/bar.md 형태의 path
    rel_paths = re.findall(r"\(\./[\w/\-_.]+\.md\)", content)
    rel_paths = sorted({p[3:-1] for p in rel_paths})  # drop "(./" prefix and ")" suffix, dedup
    # dedup
    rel_paths = sorted(set(rel_paths))
    missing: list[str] = []
    for p in rel_paths:
        full = DOCS_DIR / p
        if not full.is_file():
            missing.append(p)
    if missing:
        print(f"  FAIL: 상대 링크 부재 ({len(missing)}): {missing}")
        return False
    print(f"  [info] {len(rel_paths)} relative links 모두 file system 정합")
    return True


def case_2_github_links() -> bool:
    """2) 본문의 GitHub 외부 링크 path 가 `docs/` 트리에 실제 존재 (5 file sample)."""
    content = _load_document_index()
    # extract /blob/main/docs/... or /tree/main/docs/...
    gh_paths = re.findall(
        r"github\.com/ykylee/standard_ai_workflow/(?:blob|tree)/main/docs/([\w/\-_.]+\.?(?:md)?)",
        content,
    )
    gh_paths = sorted(set(gh_paths))
    missing: list[str] = []
    for p in gh_paths:
        # strip trailing slash if any
        cleaned = p.rstrip("/")
        if not cleaned:
            continue
        full = DOCS_DIR / cleaned
        if not full.is_file() and not full.is_dir():
            missing.append(cleaned)
    if missing:
        print(f"  FAIL: GitHub 링크 부재 ({len(missing)}): {missing}")
        return False
    print(f"  [info] {len(gh_paths)} GitHub docs paths 모두 file system 정합")
    return True


def case_3_frontmatter_stamp() -> bool:
    """3) frontmatter `- 최종 수정일: 2026-07-18` stamp 가 v0.15.15 release day 와 정합."""
    content = _load_document_index()
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


def case_4_required_sections() -> bool:
    """4) 4개 카테고리 섹션 헤더가 모두 존재."""
    content = _load_document_index()
    missing: list[str] = []
    for sec in REQUIRED_SECTIONS:
        if sec not in content:
            missing.append(sec)
    if missing:
        print(f"  FAIL: 필수 섹션 부재: {missing}")
        return False
    # 본문에 v0.15.15 stamp 등장 확인
    if EXPECTED_VERSION_STAMP not in content:
        print(f"  FAIL: 본문에 '{EXPECTED_VERSION_STAMP}' stamp 부재")
        return False
    print(f"  [info] 4개 카테고리 섹션 헤더 정합 + {EXPECTED_VERSION_STAMP} stamp 등장")
    return True


def main() -> int:
    cases = [
        ("case_1_relative_links", case_1_relative_links),
        ("case_2_github_links", case_2_github_links),
        ("case_3_frontmatter_stamp", case_3_frontmatter_stamp),
        ("case_4_required_sections", case_4_required_sections),
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


# v0.15.16+: pytest-friendly wrappers (TST-WF-01 정합 — def test_ 패턴 추가).
# 기존 `def case_*` 와 `def main()` 정합 유지. pytest collection 에서도 4 case 모두 검증.
def test_case_1_relative_links() -> None:
    assert case_1_relative_links(), "case_1_relative_links FAIL"


def test_case_2_github_links() -> None:
    assert case_2_github_links(), "case_2_github_links FAIL"


def test_case_3_frontmatter_stamp() -> None:
    assert case_3_frontmatter_stamp(), "case_3_frontmatter_stamp FAIL"


def test_case_4_required_sections() -> None:
    assert case_4_required_sections(), "case_4_required_sections FAIL"


if __name__ == "__main__":
    raise SystemExit(main())
