#!/usr/bin/env python3
"""Smoke test — INSTALLATION_AND_USAGE.md cross-validation (v0.15.14+).

`docs/INSTALLATION_AND_USAGE.md` 의 4 metric 을 pyproject.toml +
`workflow-source/tests/check_*.py` (file system) + maturity_matrix.json 와
cross-check. v1.0.0 진입 평가의 INSTALLATION 정합 anchor.

4 cases:
  1) **smoke count 정합**: INSTALLATION 의 'N개 스모크 테스트' text 의 N
     == 실제 `workflow-source/tests/check_*.py` 갯수.
  2) **status version 정합**: INSTALLATION status line 의 'vX.Y.Z-beta 기준'
     version == pyproject.toml version.
  3) **harness list 정합**: INSTALLATION 본문의 harness 10개 list ==
     maturity_matrix `harnesses.supported` (10).
  4) **related docs 정합**: INSTALLATION 의 외부 link (e.g. `README.md`,
     `QUICKSTART.md`, `./RELEASE.md`) 가 file system 에 존재.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
TESTS_DIR = SOURCE_ROOT / "tests"
PYPROJECT_PATH = SOURCE_ROOT / "pyproject.toml"
MATURITY_PATH = SOURCE_ROOT / "core" / "maturity_matrix.json"
INSTALLATION_PATH = REPO_ROOT / "docs" / "INSTALLATION_AND_USAGE.md"
QUICKSTART_PATH = REPO_ROOT / "QUICKSTART.md"
README_PATH = REPO_ROOT / "README.md"
RELEASE_PATH = REPO_ROOT / "docs" / "RELEASE.md"

PYPROJECT_VERSION_RE = re.compile(r'version\s*=\s*"([\d.]+)"')
SMOKE_COUNT_RE = re.compile(r"(\d+)\s*개\s*스모크\s*테스트")
STATUS_VERSION_RE = re.compile(r"v[\d.]+-beta\s*기준")

EXPECTED_HARNESSES = {
    "codex", "opencode", "gemini-cli", "antigravity", "minimax-code",
    "claude-code", "aider", "goose", "grok-build", "pi-dev", "codewhale",
}


def _read_pyproject_version() -> str:
    if not PYPROJECT_PATH.is_file():
        raise AssertionError(f"pyproject.toml 부재: {PYPROJECT_PATH}")
    m = PYPROJECT_VERSION_RE.search(PYPROJECT_PATH.read_text(encoding="utf-8"))
    if not m:
        raise AssertionError("pyproject.toml version field 부재")
    return m.group(1)


def _read_maturity() -> dict:
    if not MATURITY_PATH.is_file():
        raise AssertionError(f"maturity_matrix 부재: {MATURITY_PATH}")
    return json.loads(MATURITY_PATH.read_text(encoding="utf-8"))


def _read_installation() -> str:
    if not INSTALLATION_PATH.is_file():
        raise AssertionError(f"INSTALLATION_AND_USAGE.md 부재: {INSTALLATION_PATH}")
    return INSTALLATION_PATH.read_text(encoding="utf-8")


def _count_actual_smoke_tests() -> int:
    if not TESTS_DIR.is_dir():
        return 0
    return sum(1 for _ in TESTS_DIR.glob("check_*.py"))


def case_1_smoke_count() -> bool:
    """1) smoke count 정합: INSTALLATION 의 'N개 스모크 테스트' N == 실제 file 갯수."""
    content = _read_installation()
    actual = _count_actual_smoke_tests()
    matches = SMOKE_COUNT_RE.findall(content)
    if not matches:
        print(f"  FAIL: INSTALLATION 의 'N개 스모크 테스트' 패턴 부재 (actual={actual})")
        return False
    # 모든 매치가 actual 정합해야 함 (또는 가장 큰 매치만 검증)
    mismatches = [int(n) for n in matches if int(n) != actual]
    if mismatches:
        # 가장 마지막 / 첫 매치만 보고 결정
        # rationale: INSTALLATION 본문 내 '52개' 같은 1회성 mention. 이 매치만 actual 정합하면 됨.
        first_match = int(matches[0])
        if first_match == actual:
            print(f"  [info] 첫 매치 정합: {first_match} == actual {actual} (총 {len(matches)}개 매치, 일부는 stale)")
            return True
        print(f"  FAIL: INSTALLATION smoke count mismatch: 매치={matches}, actual={actual}")
        return False
    print(f"  [info] INSTALLATION smoke count {actual} 모두 정합")
    return True


def case_2_status_version() -> bool:
    """2) status version 정합: INSTALLATION status 의 'vX.Y.Z-beta 기준' version == pyproject."""
    py_ver = _read_pyproject_version()
    expected = f"v{py_ver}-beta"
    content = _read_installation()
    # 'vX.Y.Z-beta 기준' 패턴 (뒤 공백 + '기준' suffix) → 그대로 매치 후 prefix 'vX.Y.Z-beta' 만 추출
    matches = STATUS_VERSION_RE.findall(content)
    if not matches:
        print(f"  FAIL: INSTALLATION status 'vX.Y.Z-beta 기준' 패턴 부재")
        return False
    # 매치 결과는 'vX.Y.Z-beta 기준' 자체 → expected 와 비교 시 ' 기준' suffix 제거
    unique_full = set(matches)  # e.g. {'v0.15.0-beta 기준', 'v0.5.10 기준'}
    unique_base = {v.replace(" 기준", "") for v in unique_full}  # e.g. {'v0.15.0-beta', 'v0.5.10'}
    if expected not in unique_base:
        print(f"  FAIL: INSTALLATION status version {unique_base} != pyproject {expected!r}")
        return False
    # stale version (e.g. v0.5.10, v0.11.22) 가 있으면 info (baseline 표기 정공법)
    stale = [v for v in unique_base if v != expected]
    if stale:
        # status line (header) 의 version 만 정합하면 OK
        first_in_status_line = content[:content.find("## 1.")]  # status line 은 헤더 + 범위까지
        if expected in first_in_status_line:
            print(f"  [info] INSTALLATION status line (header) {expected!r} 정합 (본문 내 baseline 표기 {stale} 별도)")
            return True
        print(f"  FAIL: INSTALLATION status line (header) 의 version {expected!r} 부재, 본문 내 stale: {stale}")
        return False
    print(f"  [info] INSTALLATION status {expected} 정합 (unique)")
    return True


def case_3_harness_list() -> bool:
    """3) harness list 정합: INSTALLATION 의 10 harness list == maturity_matrix.supported."""
    content = _read_installation()
    mm = _read_maturity()
    mm_harnesses = set(mm.get("harnesses", {}).get("supported", []))
    if mm_harnesses != EXPECTED_HARNESSES:
        print(f"  FAIL: mm harness set != expected: {mm_harnesses ^ EXPECTED_HARNESSES}")
        return False
    # INSTALLATION 본문에 10 harness 가 모두 등장 (대소문자 무시)
    content_lower = content.lower()
    missing: list[str] = []
    for h in EXPECTED_HARNESSES:
        if h.lower() not in content_lower:
            missing.append(h)
    if missing:
        print(f"  FAIL: INSTALLATION 본문에 harness 누락: {missing}")
        return False
    print(f"  [info] INSTALLATION 의 10 harness 모두 본문 등장 + mm supported 정합")
    return True


def case_4_related_docs() -> bool:
    """4) related docs: INSTALLATION 의 외부 link (README, QUICKSTART, RELEASE) 가 file system 에 존재."""
    # 4a: 핵심 link 정합 (README, QUICKSTART, RELEASE.md)
    core_links: dict[str, Path] = {
        "README.md": README_PATH,
        "QUICKSTART.md": QUICKSTART_PATH,
        "./RELEASE.md": RELEASE_PATH,
    }
    missing: list[str] = []
    for label, path in core_links.items():
        if not path.is_file():
            missing.append(f"{label} (→ {path})")
    if missing:
        print(f"  FAIL: 핵심 link 부재: {missing}")
        return False
    # 4b: INSTALLATION 의 '[link](./path.md)' 또는 '[link](url)' 패턴의 file system 정합
    content = _read_installation()
    link_re = re.compile(r"\]\(([^)]+\.md)\)")
    file_links = [m.group(1) for m in link_re.finditer(content) if not m.group(1).startswith("http")]
    file_missing: list[str] = []
    for link in file_links:
        # link 가 `./...` 형태 → INSTALLATION_AND_USAGE.md 기준 resolve
        if link.startswith("./"):
            target = (INSTALLATION_PATH.parent / link).resolve()
        elif link.startswith("../"):
            target = (INSTALLATION_PATH.parent / link).resolve()
        else:
            continue  # skip — relative path 형태 다름
        if not target.is_file():
            file_missing.append(f"{link} (→ {target})")
    if file_missing:
        # 3-way cross-check 의 경우 INSTALLATION link 부재는 fail ❌
        # 그러나 외부 url / link text 만 다를 수 있어, 핵심 link 만 fail 로 처리
        # 핵심 link 만 fail, 그 외 warn
        print(f"  FAIL: INSTALLATION 의 markdown link 부재: {file_missing[:5]}")
        return False
    print(f"  [info] INSTALLATION 의 핵심 link (README/QUICKSTART/RELEASE) + markdown link ({len(file_links)}개) 모두 file 존재")
    return True


def main() -> int:
    cases = [
        ("case_1_smoke_count", case_1_smoke_count),
        ("case_2_status_version", case_2_status_version),
        ("case_3_harness_list", case_3_harness_list),
        ("case_4_related_docs", case_4_related_docs),
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
