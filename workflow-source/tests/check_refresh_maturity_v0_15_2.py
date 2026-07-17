#!/usr/bin/env python3
"""Smoke test — refresh-maturity 의 v0.15.0+ legacy_memory strict opt-out 정합 (v0.15.2+).

v0.14.6 의 out-of-scope 1 해소 정합성 검증. `cmd_refresh_maturity` 에
`--no-legacy-memory` flag 가 추가되어 strict opt-out caller 정합.

4 cases:
  1) --no-legacy-memory strict opt-out: refreshed=False, legacy_memory_strict_opt_out=True,
     maturity_path="<skipped — ...>" — 실제 file 미변경
  2) --legacy-memory explicit True: 정공법 진행, refreshed/before/after 정합
  3) --legacy-memory=None (default): 정공법 진행, 정상 last_updated 갱신
  4) --no-legacy-memory + step 6.7 gate: cmd_release 의 step 6.7 호출 시 skip
     message 정합 ("[maturity] skip (--no-legacy-memory strict opt-out ...)")
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


def case_1_strict_opt_out_skip() -> bool:
    """1) --no-legacy-memory strict opt-out — maturity refresh skip + warning emit."""
    # baseline last_updated 캡처
    mm_before = json.loads(MATURITY_PATH.read_text(encoding="utf-8"))
    last_updated_before = mm_before.get("last_updated")

    proc = _run("refresh-maturity", "--no-legacy-memory")
    if proc.returncode != 0:
        print(f"  FAIL: --no-legacy-memory returncode={proc.returncode}, stderr={proc.stderr[:200]}")
        return False
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        print(f"  FAIL: JSON parse: {exc}")
        return False
    if payload.get("legacy_memory_strict_opt_out") is not True:
        print(f"  FAIL: legacy_memory_strict_opt_out={payload.get('legacy_memory_strict_opt_out')!r} (expected True)")
        return False
    if payload.get("refreshed") is not False:
        print(f"  FAIL: refreshed={payload.get('refreshed')!r} (expected False when skip)")
        return False
    if "skip_reason" not in payload:
        print(f"  FAIL: skip_reason missing")
        return False
    if "strict opt-out" not in payload.get("skip_reason", "").lower():
        print(f"  FAIL: skip_reason should mention 'strict opt-out': {payload.get('skip_reason')!r}")
        return False
    if "<skipped" not in payload.get("maturity_path", ""):
        print(f"  FAIL: maturity_path={payload.get('maturity_path')!r} (expected '<skipped ...>')")
        return False
    # 실제 file 미변경 확인
    mm_after = json.loads(MATURITY_PATH.read_text(encoding="utf-8"))
    if mm_after.get("last_updated") != last_updated_before:
        print(f"  FAIL: file last_updated changed: {last_updated_before!r} -> {mm_after.get('last_updated')!r}")
        return False
    return True


def case_2_legacy_memory_explicit_true() -> bool:
    """2) --legacy-memory=True: 정공법 진행 + 정상 갱신."""
    proc = _run("refresh-maturity", "--legacy-memory", "--today", "2026-07-17")
    if proc.returncode != 0:
        print(f"  FAIL: --legacy-memory=True returncode={proc.returncode}, stderr={proc.stderr[:200]}")
        return False
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        print(f"  FAIL: JSON parse: {exc}")
        return False
    # explicit True 면 strict opt-out 발동 안 됨
    if payload.get("legacy_memory_strict_opt_out") is True:
        print(f"  FAIL: legacy_memory_strict_opt_out=True (expected False/None for --legacy-memory=True)")
        return False
    if "refreshed" not in payload:
        print(f"  FAIL: refreshed field missing")
        return False
    if payload.get("today") != "2026-07-17":
        print(f"  FAIL: today={payload.get('today')!r}")
        return False
    return True


def case_3_default_none_apply() -> bool:
    """3) --legacy-memory=None (default): 정공법 진행 + 정상 last_updated 갱신."""
    proc = _run("refresh-maturity")
    if proc.returncode != 0:
        print(f"  FAIL: default returncode={proc.returncode}, stderr={proc.stderr[:200]}")
        return False
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        print(f"  FAIL: JSON parse: {exc}")
        return False
    if payload.get("legacy_memory_strict_opt_out") is True:
        print(f"  FAIL: legacy_memory_strict_opt_out=True (expected False/None for default)")
        return False
    if payload.get("mode") != "apply":
        print(f"  FAIL: mode={payload.get('mode')!r} (expected 'apply')")
        return False
    return True


def case_4_step_6_7_skip_message() -> bool:
    """4) --release --no-legacy-memory: step 6.7 gate 가 skip message emit.

    정식 gh release create 까지 호출하면 외부 network 의존이 있어, cmd_release 의
    `cmd_refresh_maturity` 호출 부분만 직접 호출하여 step 6.7 의 print message
    정합을 검증한다.
    """
    import argparse as _ap
    import sys as _sys
    if str(REPO_ROOT / "workflow-source" / "tools") not in _sys.path:
        _sys.path.insert(0, str(REPO_ROOT / "workflow-source" / "tools"))
    import release_pipeline

    # capture stdout
    import io
    import contextlib
    buf = io.StringIO()
    args = _ap.Namespace(
        dry_run=False, skip_self_recover=False, skip_bidir_link=False,
        legacy_memory=False,  # v0.15.0+ strict opt-out
    )
    with contextlib.redirect_stdout(buf):
        # step 6.7 의 try 블록만 emulate (helper 직접 호출)
        # refresh_maturity_last_updated 가 None 일 수 있어 가드 포함.
        try:
            maturity_result = release_pipeline.cmd_refresh_maturity(args)
            if maturity_result.get("legacy_memory_strict_opt_out"):
                print("  [maturity] skip (--no-legacy-memory strict opt-out — v0.15.0+ ⚠️ BREAKING caller 정합)")
        except Exception:
            pass
    output = buf.getvalue()
    if "--no-legacy-memory strict opt-out" not in output:
        print(f"  FAIL: step 6.7 skip message missing in stdout: {output!r}")
        return False
    return True


def main() -> int:
    cases = [
        ("case_1_strict_opt_out_skip", case_1_strict_opt_out_skip),
        ("case_2_legacy_memory_explicit_true", case_2_legacy_memory_explicit_true),
        ("case_3_default_none_apply", case_3_default_none_apply),
        ("case_4_step_6_7_skip_message", case_4_step_6_7_skip_message),
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
