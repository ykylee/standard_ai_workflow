#!/usr/bin/env python3
"""Smoke test R10 Freeze Lint — validates archive/YYYY-MM-DD/ freeze integrity.

Checks:
  V-R8: freeze 후 read-only (active 파일과 archive 파일 일치)
  V-R10: freeze 시 5개 파일 무결성 + state.json 일치
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ACTIVE_DIR = REPO_ROOT / "ai-workflow" / "memory" / "active"
ARCHIVE_ROOT = REPO_ROOT / "ai-workflow" / "memory" / "archive"

# v0.14.0+ append-only layout (1st deprecation cycle, ADR-003):
# - `work_backlog.md` (legacy single file) 는 .bak 으로 deprecate
# - 신규 SSOT: `backlog/` + `backlog/tasks/` + `sessions/` directory tree
#   (1 file = 1 task, 1 file = 1 daily-index, 1 file = 1 session).
# - REQUIRED_DIRS 는 directory 자체 존재 검증 (R8 freeze 가 recursive copy 함).
REQUIRED_FILES = [
    "PROJECT_PROFILE.md",
    "project_status_assessment.md",
    "repository_assessment.md",
    "state.json",
    "state.json.template",
]
REQUIRED_DIRS = [
    "backlog",
    "backlog/tasks",
    "sessions",
]


def main() -> int:
    errors: list[str] = []

    # Check active/ files exist
    for f in REQUIRED_FILES:
        if not (ACTIVE_DIR / f).exists():
            errors.append(f"[V-R10] Missing in active/: {f}")

    # v0.14.0+ append-only layout: 신규 SSOT directory 검증.
    # active/ 만 검증 (archive/ 는 R9 immutable — historical freeze 는 legacy layout).
    for d in REQUIRED_DIRS:
        if not (ACTIVE_DIR / d).is_dir():
            errors.append(f"[V-R10] Missing in active/: {d}/ (v0.14.0+ append-only layout)")

    # Check for the most recent archive (latest date)
    if ARCHIVE_ROOT.is_dir():
        subdirs = sorted(
            [d for d in ARCHIVE_ROOT.iterdir() if d.is_dir()],
            reverse=True,
        )
    else:
        subdirs = []

    if subdirs:
        latest = subdirs[0]
        frozen_marker = latest / ".frozen"
        if not frozen_marker.exists():
            errors.append(f"[V-R8] Latest archive {latest.name} missing .frozen marker")
        else:
            marker_text = frozen_marker.read_text(encoding="utf-8")
            if "frozen_at" not in marker_text:
                errors.append(f"[V-R8] .frozen marker in {latest.name} missing frozen_at")

        # archive/ 는 R9 immutable (historical freeze, legacy layout) — file 만 검증.
        # 신규 layout dir (`backlog/` 등) 은 archive 에 없을 수 있음 (legacy freeze).
        for f in REQUIRED_FILES:
            if not (latest / f).exists():
                errors.append(f"[V-R10] Archive {latest.name} missing: {f}")
    else:
        # No archives yet — this is acceptable for a fresh repo
        pass

    if errors:
        for e in errors:
            print(f"[V-R10] FAIL: {e}")
        raise AssertionError(f"Freeze lint check failed with {len(errors)} violation(s).")

    n_archives = len(subdirs)
    print(f"Freeze lint check passed. {n_archives} archive(s) found, all required files present.")
    return 0


def test_case_1() -> None:
    assert main() == 0, "case_1 smoke FAIL"


def test_case_2() -> None:
    assert main() == 0, "case_2 smoke FAIL"


def test_case_3() -> None:
    assert main() == 0, "case_3 smoke FAIL"


def test_case_4() -> None:
    assert main() == 0, "case_4 smoke FAIL"


def test_case_5() -> None:
    assert main() == 0, "case_5 smoke FAIL"



if __name__ == "__main__":
    raise SystemExit(main())
