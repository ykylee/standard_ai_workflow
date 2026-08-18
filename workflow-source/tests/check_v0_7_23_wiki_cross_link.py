#!/usr/bin/env python3
"""v0.7.23+: wiki 운영 cross-link 1-command wrapper smoke test.

`tools/wiki_emit.py` 가 `refresh_wiki_memory.py` + `emit_wiki_l2_body.py` 의
3-step cycle 을 1-command 로 묶음. 운영 시 *3번의 별도 invoke* 부담 zero.

Test 구성 (5 test):
1. test_wiki_emit_dry_run_full_cycle: 3-step 전체 (default) dry-run + 3 step planned
2. test_wiki_emit_refresh_wiki_only: --refresh-wiki 시 1단계만 (2/3 skipped)
3. test_wiki_emit_emit_l2_only: --emit-l2 시 2단계만
4. test_wiki_emit_reemit_stubs_only: --reemit-stubs 시 3단계만
5. test_wiki_emit_skip_combinations: --skip-1 / --skip-2 / --skip-3 의 조합 검증

Reference:
- workflow-source/workflow_kit/tools/wiki_emit.py (v0.7.23 본 release)
- workflow-source/workflow_kit/tools/refresh_wiki_memory.py (3-step 의 1+3)
- workflow-source/workflow_kit/tools/emit_wiki_l2_body.py (3-step 의 2)
- v0.7.23 release note (wiki 운영 cross-link 1-command wrapper)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "wiki_emit.py"


def _run(args: list[str], *, timeout: int = 60) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(TOOL)] + args,
        capture_output=True, text=True, timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


# --- Test 1: dry-run full cycle (3-step) ---


def test_wiki_emit_dry_run_full_cycle() -> None:
    """dry-run 시 3-step 전체 cycle 의 command list + skipped_steps=[]."""
    rc, out, err = _run(["--dry-run", "--json"], timeout=30)
    assert rc == 0, f"unexpected rc={rc}, stderr={err}"
    data = json.loads(out)
    assert data["mode"] == "dry-run"
    # 3 step 모두 planned
    assert len(data["steps"]) == 3
    step_names = [s["name"] for s in data["steps"]]
    assert "1_refresh_raw" in step_names
    assert "2_emit_l2_dense" in step_names
    assert "3_reemit_stubs" in step_names
    # skipped 없음
    assert data["skipped_steps"] == []
    # 하위 단계는 **모듈로** 부른다 (`-m <module>`), 파일 경로가 아니다.
    #
    # 2026-08-18 (TASK-2026-08-18-main-003): 원래 이 단언은 `"…​.py" in cmd[1]` 로
    # **파일 경로 계약을 고정**하고 있었다. 그런데 그 경로(`workflow-source/tools/…`)는
    # v1.2.0 shim drop 이후 존재하지 않았고, dry-run 은 subprocess 를 띄우지 않으므로
    # 검사는 계속 green 이었다 — 즉 이 단언이 **죽은 경로를 지키고 있었다**. 이제
    # 모듈 이름을 고정한다: 설치본이든 체크아웃이든 import 규칙 하나로 풀린다.
    # 1단계 — refresh_wiki_memory + --refresh-raw
    step_1_cmd = data["steps"][0]["command"]
    assert step_1_cmd[1] == "-m", f"파일 경로로 부른다: {step_1_cmd[:3]}"
    assert step_1_cmd[2] == "workflow_kit.tools.refresh_wiki_memory", step_1_cmd[2]
    assert "--refresh-raw" in step_1_cmd
    # 2단계 — emit_wiki_l2_body + --max-chars
    step_2_cmd = data["steps"][1]["command"]
    assert step_2_cmd[1] == "-m", f"파일 경로로 부른다: {step_2_cmd[:3]}"
    assert step_2_cmd[2] == "workflow_kit.tools.emit_wiki_l2_body", step_2_cmd[2]
    assert "--max-chars" in step_2_cmd
    # 3단계 — refresh_wiki_memory + --emit-l2
    step_3_cmd = data["steps"][2]["command"]
    assert step_3_cmd[1] == "-m", f"파일 경로로 부른다: {step_3_cmd[:3]}"
    assert step_3_cmd[2] == "workflow_kit.tools.refresh_wiki_memory", step_3_cmd[2]
    assert "--emit-l2" in step_3_cmd


# --- Test 2: --refresh-wiki 만 (1단계만) ---


def test_wiki_emit_refresh_wiki_only() -> None:
    """--refresh-wiki 시 1단계만 (2/3 skipped)."""
    rc, out, err = _run(["--refresh-wiki", "--dry-run", "--json"], timeout=30)
    assert rc == 0, f"unexpected rc={rc}, stderr={err}"
    data = json.loads(out)
    assert len(data["steps"]) == 1
    assert data["steps"][0]["name"] == "1_refresh_raw"
    assert set(data["skipped_steps"]) == {"2_emit_l2_dense", "3_reemit_stubs"}


# --- Test 3: --emit-l2 만 (2단계만) ---


def test_wiki_emit_emit_l2_only() -> None:
    """--emit-l2 시 2단계만 (1/3 skipped)."""
    rc, out, err = _run(["--emit-l2", "--dry-run", "--json"], timeout=30)
    assert rc == 0, f"unexpected rc={rc}, stderr={err}"
    data = json.loads(out)
    assert len(data["steps"]) == 1
    assert data["steps"][0]["name"] == "2_emit_l2_dense"
    assert set(data["skipped_steps"]) == {"1_refresh_raw", "3_reemit_stubs"}


# --- Test 4: --reemit-stubs 만 (3단계만) ---


def test_wiki_emit_reemit_stubs_only() -> None:
    """--reemit-stubs 시 3단계만 (1/2 skipped)."""
    rc, out, err = _run(["--reemit-stubs", "--dry-run", "--json"], timeout=30)
    assert rc == 0, f"unexpected rc={rc}, stderr={err}"
    data = json.loads(out)
    assert len(data["steps"]) == 1
    assert data["steps"][0]["name"] == "3_reemit_stubs"
    assert set(data["skipped_steps"]) == {"1_refresh_raw", "2_emit_l2_dense"}


# --- Test 5: --skip-N 조합 ---


def test_wiki_emit_skip_combinations() -> None:
    """--skip-1/2/3 의 조합 검증."""
    # --skip-1 → 2+3 만
    rc, out, _ = _run(["--skip-1", "--dry-run", "--json"], timeout=30)
    assert rc == 0
    data = json.loads(out)
    assert len(data["steps"]) == 2
    assert data["skipped_steps"] == ["1_refresh_raw"]
    # --skip-2 → 1+3 만
    rc, out, _ = _run(["--skip-2", "--dry-run", "--json"], timeout=30)
    assert rc == 0
    data = json.loads(out)
    assert len(data["steps"]) == 2
    assert data["skipped_steps"] == ["2_emit_l2_dense"]
    # --skip-3 → 1+2 만
    rc, out, _ = _run(["--skip-3", "--dry-run", "--json"], timeout=30)
    assert rc == 0
    data = json.loads(out)
    assert len(data["steps"]) == 2
    assert data["skipped_steps"] == ["3_reemit_stubs"]


# --- 메인 실행 ---


def main() -> int:
    test_funcs = [
        test_wiki_emit_dry_run_full_cycle,
        test_wiki_emit_refresh_wiki_only,
        test_wiki_emit_emit_l2_only,
        test_wiki_emit_reemit_stubs_only,
        test_wiki_emit_skip_combinations,
    ]
    passed = 0
    failed = 0
    for func in test_funcs:
        try:
            func()
            print(f"  PASS  {func.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {func.__name__}: {e}")
            failed += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {func.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print()
    print(f"{passed} pass, {failed} fail")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
