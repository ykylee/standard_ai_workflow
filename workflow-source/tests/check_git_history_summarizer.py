#!/usr/bin/env python3
"""Smoke test — git-history-summarizer MCP (v0.14.0+ 1st batch stable) 5 case PASS.

skill_beta_criteria §3.1 의 6 condition 중 smoke_test_5_cases 정공법 적용.
본 smoke 는 git-history-summarizer 의 stable 정합성 검증.

5 cases:
  1) Markdown output format (`Git 작업 요약` substring)
  2) JSON output format (`status=ok` + `entries` field, length ≥ 1)
  3) CLI 도움말 (`--help`): argparse exit 0 + description 포함
  4) Pydantic schema validate (GitHistorySummarizerOutput model_validate)
  5) categories 6 종 모두 type=int (>= 0)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{REPO_ROOT / 'workflow-source'}"
        + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
    )
    return subprocess.run(
        [sys.executable, str(
            REPO_ROOT / "workflow-source/mcp_servers/git-history-summarizer/scripts/run_git_history_summarizer.py"
        ), *args],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=30,
    )


def case_1_markdown() -> bool:
    """1) Markdown output format."""
    proc = _run("--range", "HEAD~1..HEAD")
    if proc.returncode != 0:
        print(f"  FAIL: markdown returncode={proc.returncode}, stderr={proc.stderr[:200]}")
        return False
    if "Git 작업 요약" not in proc.stdout:
        print(f"  FAIL: markdown missing 'Git 작업 요약' marker")
        return False
    return True


def case_2_json() -> bool:
    """2) JSON output format."""
    proc = _run("--range", "HEAD~1..HEAD", "--json")
    if proc.returncode != 0:
        print(f"  FAIL: json returncode={proc.returncode}, stderr={proc.stderr[:200]}")
        return False
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        print(f"  FAIL: JSON parse: {exc}")
        return False
    if data.get("status") != "ok":
        print(f"  FAIL: status={data.get('status')!r}")
        return False
    if "entries" not in data or len(data["entries"]) < 1:
        print(f"  FAIL: entries={data.get('entries')!r}")
        return False
    return True


def case_3_help() -> bool:
    """3) CLI 도움말 정상 동작."""
    proc = _run("--help")
    if proc.returncode != 0:
        print(f"  FAIL: --help returncode={proc.returncode}")
        return False
    if "git" not in proc.stdout.lower():
        print(f"  FAIL: --help missing description")
        return False
    return True


def case_4_pydantic() -> bool:
    """4) Pydantic schema (GitHistorySummarizerOutput) validate."""
    try:
        sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
        from workflow_kit.common.schemas.git_history_summarizer import (
            GitHistorySummarizerOutput,
            GitHistorySummarizerCategories,
        )
    except ImportError as exc:
        print(f"  FAIL: schema import: {exc}")
        return False
    sample = {
        "status": "ok",
        "tool_version": "v0.14.0-beta",
        "warnings": [],
        "summary": "test summary",
        "commit_count": 1,
        "categories": GitHistorySummarizerCategories(feature=1, bug_fix=0, docs=0,
                                                  refactor=0, test=0, chore=0, unknown=0).model_dump(),
        "raw_log": ["feat: sample | abc1234 | author | 2026-07-16"],
    }
    try:
        out = GitHistorySummarizerOutput.model_validate(sample)
    except Exception as exc:
        print(f"  FAIL: Pydantic validate: {exc}")
        return False
    if out.summary != "test summary" or out.commit_count != 1 or len(out.raw_log) != 1:
        print(f"  FAIL: field mismatch")
        return False
    return True


def case_5_categories_int() -> bool:
    """5) categories 6 종 모두 type=int (>= 0)."""
    try:
        sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
        from workflow_kit.common.schemas.git_history_summarizer import GitHistorySummarizerCategories
    except ImportError as exc:
        print(f"  FAIL: schema import: {exc}")
        return False
    cats = GitHistorySummarizerCategories()
    for field_name in ("feature", "bug_fix", "docs", "refactor", "test", "chore", "unknown"):
        val = getattr(cats, field_name)
        if not isinstance(val, int) or val < 0:
            print(f"  FAIL: category {field_name}={val} not int >= 0")
            return False
    return True


def main() -> int:
    cases = [
        ("case_1_markdown", case_1_markdown),
        ("case_2_json", case_2_json),
        ("case_3_help", case_3_help),
        ("case_4_pydantic", case_4_pydantic),
        ("case_5_categories_int", case_5_categories_int),
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