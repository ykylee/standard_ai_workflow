#!/usr/bin/env python3
"""Smoke test — MEMORY_GOVERNANCE ↔ global_workflow_standard 정합 검증 (v0.15.19+).

두 문서가 AI 에이전트 운영 표준의 SSOT 역할을 유지하기 위해, 핵심 정합
항목을 자동 검증한다. 5 cases:

  1) **frontmatter stamp 정합**: MEMORY_GOVERNANCE.md 의 `- 최종 수정일:`
     이 v0.15.15 release day 와 정합 (또는 더 최신).
  2) **status 값 정합**: 두 문서가 모두 `planned` / `in_progress` /
     `blocked` / `done` 4 status 를 정의 — 누락 없이 모두 등장.
  3) **status 순서 정합**: MEMORY_GOVERNANCE.md 의 status 템플릿 (45줄)
     의 순서가 global_workflow_standard.md §3 표의 순서와 일치
     (`planned|in_progress|blocked|done`).
  4) **cross-reference 양방향**: MEMORY_GOVERNANCE.md §3 에서
     `global_workflow_standard.md §8` 을 명시적으로 참조하는지 확인.
  5) **memory → commit → push 순서 정합**: global_workflow_standard.md §8
     의 핵심 문구 `memory 갱신 → commit → push` 가 MEMORY_GOVERNANCE.md §3
     에서도 인용되는지 확인.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
MEMORY_GOVERNANCE_PATH = SOURCE_ROOT / "MEMORY_GOVERNANCE.md"
GLOBAL_STANDARD_PATH = SOURCE_ROOT / "core" / "global_workflow_standard.md"

EXPECTED_MIN_LAST_UPDATED = "2026-07-18"  # v0.15.15 release day (이전이면 stale)

# §3 표의 정공법 status 순서
EXPECTED_STATUS_ORDER = ["planned", "in_progress", "blocked", "done"]


def _load(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"부재: {path}")
    return path.read_text(encoding="utf-8")


def case_1_frontmatter_stamp() -> bool:
    """1) MEMORY_GOVERNANCE.md 의 최종 수정일이 v0.15.15 release day 이상."""
    mg = _load(MEMORY_GOVERNANCE_PATH)
    m = re.search(r"^-\s+최종\s*수정일\s*:\s*(\S+)", mg, re.MULTILINE)
    if not m:
        print("  FAIL: MEMORY_GOVERNANCE.md '최종 수정일' line 부재")
        return False
    actual = m.group(1).strip()
    if actual < EXPECTED_MIN_LAST_UPDATED:
        print(f"  FAIL: MEMORY_GOVERNANCE.md stamp stale — actual={actual}, "
              f"min={EXPECTED_MIN_LAST_UPDATED}")
        return False
    print(f"  [info] MEMORY_GOVERNANCE.md stamp = {actual} (≥ {EXPECTED_MIN_LAST_UPDATED})")
    return True


def case_2_status_values_complete() -> bool:
    """2) 두 문서 모두 4 status (planned/in_progress/blocked/done) 모두 등장."""
    mg = _load(MEMORY_GOVERNANCE_PATH)
    gs = _load(GLOBAL_STANDARD_PATH)
    required = {"planned", "in_progress", "blocked", "done"}
    mg_missing = required - set(re.findall(r"\b(planned|in_progress|blocked|done)\b", mg))
    gs_missing = required - set(re.findall(r"\b(planned|in_progress|blocked|done)\b", gs))
    if mg_missing or gs_missing:
        print(f"  FAIL: status 누락 — mg_missing={sorted(mg_missing)}, "
              f"gs_missing={sorted(gs_missing)}")
        return False
    print(f"  [info] 두 문서 모두 4 status 정합 (planned/in_progress/blocked/done)")
    return True


def case_3_status_order() -> bool:
    """3) MEMORY_GOVERNANCE.md 45줄 status 템플릿의 순서가 §3 표와 정합."""
    mg = _load(MEMORY_GOVERNANCE_PATH)
    # 45줄 근처의 status: [planned|in_progress|done|blocked] 템플릿
    m = re.search(r"status:\s*\[([^\]]+)\]", mg)
    if not m:
        print("  FAIL: MEMORY_GOVERNANCE.md 'status: [...]' 템플릿 line 부재")
        return False
    parts = [s.strip() for s in m.group(1).split("|")]
    if parts != EXPECTED_STATUS_ORDER:
        print(f"  FAIL: status 순서 불일치 — actual={parts}, expected={EXPECTED_STATUS_ORDER}")
        return False
    print(f"  [info] status 순서 정합: {' → '.join(parts)}")
    return True


def case_4_cross_reference() -> bool:
    """4) MEMORY_GOVERNANCE.md §3 에서 global_workflow_standard.md §8 을 명시 참조."""
    mg = _load(MEMORY_GOVERNANCE_PATH)
    # 'global_workflow_standard' 와 '§8' 이 같은 단락 안에 등장
    patterns = [
        r"global_workflow_standard\.md.*§\s*8",
        r"§\s*8.*global_workflow_standard\.md",
        r"global_workflow_standard.*세션\s*종료",
    ]
    if not any(re.search(p, mg, re.DOTALL) for p in patterns):
        print("  FAIL: MEMORY_GOVERNANCE.md 에서 global_workflow_standard.md §8 cross-ref 부재")
        return False
    # link path 가 실제 file 로 resolve 되는지
    m = re.search(r"\[.*?\]\((\./core/global_workflow_standard\.md)\)", mg)
    if m:
        link_target = MEMORY_GOVERNANCE_PATH.parent / m.group(1)
        if not link_target.is_file():
            print(f"  FAIL: cross-ref link 부재 — {link_target}")
            return False
    print(f"  [info] MEMORY_GOVERNANCE.md §3 → global_workflow_standard.md §8 cross-ref 정합")
    return True


def case_5_memory_commit_push_order() -> bool:
    """5) 'memory 갱신 → commit → push' 순서가 두 문서 모두에 등장."""
    mg = _load(MEMORY_GOVERNANCE_PATH)
    gs = _load(GLOBAL_STANDARD_PATH)
    # 핵심 문구: 'memory 갱신 → commit → push' 또는 'memory → commit → push'
    pattern = r"memory\s*(갱신\s*)?[→\->]+\s*commit\s*[→\->]+\s*push"
    if not re.search(pattern, gs):
        print("  FAIL: global_workflow_standard.md 에 'memory → commit → push' 순서 부재")
        return False
    if not re.search(pattern, mg):
        print("  FAIL: MEMORY_GOVERNANCE.md 에 'memory → commit → push' 순서 부재")
        return False
    print(f"  [info] 두 문서 모두 'memory → commit → push' 순서 정합")
    return True


def main() -> int:
    cases = [
        ("case_1_frontmatter_stamp", case_1_frontmatter_stamp),
        ("case_2_status_values_complete", case_2_status_values_complete),
        ("case_3_status_order", case_3_status_order),
        ("case_4_cross_reference", case_4_cross_reference),
        ("case_5_memory_commit_push_order", case_5_memory_commit_push_order),
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
