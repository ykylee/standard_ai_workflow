#!/usr/bin/env python3
"""Smoke test — refresh-maturity dispatcher subcommand (Task 3 follow-up, v0.14.6+) 4 case PASS.

v0.14.0+ 의 Task 3 follow-up 정합성 검증. `cmd_refresh_maturity` 가 helper
`refresh_maturity_last_updated` 와 정합 동작 + idempotent + CLI 시그너처 정상.

4 cases:
  1) default = apply (--apply default True): maturity_last_updated 가 오늘 날짜로 갱신
  2) --dry-run: 실제 갱신 없이 plan 만 emit, before field 정합
  3) idempotency: 오늘 날짜로 갱신된 직후 다시 호출 시 refreshed=False (no-op)
  4) --today 명시 override: 임의 날짜 (e.g., '2027-01-01') 로 갱신 가능 + helper 와 정합
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "workflow-source" / "tools" / "release_pipeline.py"
MATURITY_PATH = REPO_ROOT / "workflow-source" / "core" / "maturity_matrix.json"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--json"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30,
    )


def case_1_default_apply() -> bool:
    """1) default = apply — maturity_last_updated 가 오늘 날짜로 갱신."""
    proc = _run("refresh-maturity")
    if proc.returncode != 0:
        print(f"  FAIL: default returncode={proc.returncode}, stderr={proc.stderr[:200]}")
        return False
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        print(f"  FAIL: JSON parse: {exc}")
        return False
    if payload.get("mode") != "apply":
        print(f"  FAIL: mode={payload.get('mode')!r}")
        return False
    if "refreshed" not in payload:
        print(f"  FAIL: refreshed field missing")
        return False
    # 실제 file 갱신 검증
    mm = json.loads(MATURITY_PATH.read_text(encoding="utf-8"))
    from datetime import date
    today = date.today().isoformat()
    if mm.get("last_updated") != today:
        print(f"  FAIL: maturity last_updated={mm.get('last_updated')!r} (expected {today!r})")
        return False
    return True


def case_2_dry_run() -> bool:
    """2) --dry-run — 실제 갱신 안 함 + plan 만 emit."""
    proc = _run("refresh-maturity", "--dry-run")
    if proc.returncode != 0:
        print(f"  FAIL: dry-run returncode={proc.returncode}")
        return False
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        print(f"  FAIL: JSON parse: {exc}")
        return False
    if payload.get("mode") != "dry-run":
        print(f"  FAIL: mode={payload.get('mode')!r}")
        return False
    # dry-run 은 refreshed=False + dry_run_note 명시
    if payload.get("refreshed") is not False:
        print(f"  FAIL: refreshed={payload.get('refreshed')!r} (expected False in dry-run)")
        return False
    if "dry_run_note" not in payload:
        print(f"  FAIL: dry_run_note missing")
        return False
    return True


def case_3_idempotency() -> bool:
    """3) idempotency — 이미 today 면 refreshed=False (no-op)."""
    proc = _run("refresh-maturity")
    if proc.returncode != 0:
        print(f"  FAIL: idempotency returncode={proc.returncode}")
        return False
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        print(f"  FAIL: JSON parse: {exc}")
        return False
    # 이미 today 면 refreshed=False
    if payload.get("refreshed") is not False:
        print(f"  FAIL: idempotency refreshed={payload.get('refreshed')!r} (expected False)")
        return False
    if payload.get("before") != payload.get("after"):
        print(f"  FAIL: idempotency before={payload.get('before')!r} != after={payload.get('after')!r}")
        return False
    return True


def case_4_today_override() -> bool:
    """4) --today 명시 — 임의 미래 날짜로 갱신 (helper 와 정합성 검증)."""
    proc = _run("refresh-maturity", "--today", "2027-01-01")
    if proc.returncode != 0:
        print(f"  FAIL: override returncode={proc.returncode}")
        return False
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        print(f"  FAIL: JSON parse: {exc}")
        return False
    if payload.get("today") != "2027-01-01":
        print(f"  FAIL: today={payload.get('today')!r}")
        return False
    if payload.get("after") != "2027-01-01":
        print(f"  FAIL: after={payload.get('after')!r}")
        return False
    if payload.get("refreshed") is not True:
        print(f"  FAIL: refreshed={payload.get('refreshed')!r} (expected True after override)")
        return False
    # 실제 file 도 2027-01-01 인지 확인
    mm = json.loads(MATURITY_PATH.read_text(encoding="utf-8"))
    if mm.get("last_updated") != "2027-01-01":
        print(f"  FAIL: file last_updated={mm.get('last_updated')!r}")
        return False
    # 원복 (오늘 날짜로 reset)
    from datetime import date
    _run("refresh-maturity")
    return True


def main() -> int:
    cases = [
        ("case_1_default_apply", case_1_default_apply),
        ("case_2_dry_run", case_2_dry_run),
        ("case_3_idempotency", case_3_idempotency),
        ("case_4_today_override", case_4_today_override),
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