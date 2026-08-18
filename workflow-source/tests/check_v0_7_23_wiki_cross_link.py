#!/usr/bin/env python3
"""v0.7.23+: wiki 운영 cross-link 1-command wrapper smoke test.

`tools/wiki_emit.py` 가 `refresh_wiki_memory.py` + `emit_wiki_l2_body.py` 의
3-step cycle 을 1-command 로 묶음. 운영 시 *3번의 별도 invoke* 부담 zero.

Test 구성 (5 test):
1. test_wiki_emit_dry_run_full_cycle: 기본 dry-run 이 살아 있는 2단계만 계획 (1단계 은퇴)
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
    """dry-run 기본은 **살아 있는 2단계**만 계획하고 은퇴한 1단계는 뺀다.

    TASK-2026-08-18-main-004 이전에는 3-step 이 기본이었다. 1단계는
    `state.json` 을 쓰는 **두 번째 writer** 였고 (정본 §11.2 의 생성 산출물,
    생성기는 `wk refresh-state` 하나다) 나머지 대상도 전부 무너져 있어
    은퇴했다. write 0 인 단계를 기본에 두면 로그만 늘고, 그 자리에 뭔가
    갱신되고 있다는 인상을 준다.
    """
    rc, out, err = _run(["--dry-run", "--json"], timeout=30)
    assert rc == 0, f"unexpected rc={rc}, stderr={err}"
    data = json.loads(out)
    assert data["mode"] == "dry-run"
    step_names = [s["name"] for s in data["steps"]]
    assert step_names == ["2_emit_l2_dense", "3_reemit_stubs"], step_names
    assert data["skipped_steps"] == ["1_refresh_raw"], data["skipped_steps"]
    # 하위 단계는 **모듈로** 부른다 (`-m <module>`), 파일 경로가 아니다.
    #
    # 2026-08-18 (TASK-2026-08-18-main-003): 원래 이 단언은 `"…​.py" in cmd[1]` 로
    # **파일 경로 계약을 고정**하고 있었다. 그런데 그 경로(`workflow-source/tools/…`)는
    # v1.2.0 shim drop 이후 존재하지 않았고, dry-run 은 subprocess 를 띄우지 않으므로
    # 검사는 계속 green 이었다 — 즉 이 단언이 **죽은 경로를 지키고 있었다**. 이제
    # 모듈 이름을 고정한다: 설치본이든 체크아웃이든 import 규칙 하나로 풀린다.
    # 은퇴한 1단계도 **명시 호출** 시에는 모듈로 불린다 (계약 자체는 유지)
    rc1, out1, _ = _run(["--refresh-wiki", "--dry-run", "--json"], timeout=30)
    assert rc1 == 0
    step_1_cmd = json.loads(out1)["steps"][0]["command"]
    assert step_1_cmd[1] == "-m", f"파일 경로로 부른다: {step_1_cmd[:3]}"
    assert step_1_cmd[2] == "workflow_kit.tools.refresh_wiki_memory", step_1_cmd[2]
    assert "--refresh-raw" in step_1_cmd
    # 2단계 — emit_wiki_l2_body + --max-chars (기본 실행의 첫 단계)
    step_2_cmd = data["steps"][0]["command"]
    assert step_2_cmd[1] == "-m", f"파일 경로로 부른다: {step_2_cmd[:3]}"
    assert step_2_cmd[2] == "workflow_kit.tools.emit_wiki_l2_body", step_2_cmd[2]
    assert "--max-chars" in step_2_cmd
    # 3단계 — refresh_wiki_memory + --emit-l2
    step_3_cmd = data["steps"][1]["command"]
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
    """--skip-N 이 기본 2단계에서 그 단계를 뺀다 (1단계는 이미 기본에서 빠져 있다)."""
    # --skip-1 → 기본과 같다 (1단계는 원래 안 돈다)
    rc, out, _ = _run(["--skip-1", "--dry-run", "--json"], timeout=30)
    assert rc == 0
    data = json.loads(out)
    assert [s["name"] for s in data["steps"]] == ["2_emit_l2_dense", "3_reemit_stubs"]
    assert data["skipped_steps"] == ["1_refresh_raw"]
    # --skip-2 → 3단계만
    rc, out, _ = _run(["--skip-2", "--dry-run", "--json"], timeout=30)
    assert rc == 0
    data = json.loads(out)
    assert [s["name"] for s in data["steps"]] == ["3_reemit_stubs"]
    assert data["skipped_steps"] == ["1_refresh_raw", "2_emit_l2_dense"]
    # --skip-3 → 2단계만
    rc, out, _ = _run(["--skip-3", "--dry-run", "--json"], timeout=30)
    assert rc == 0
    data = json.loads(out)
    assert [s["name"] for s in data["steps"]] == ["2_emit_l2_dense"]
    assert data["skipped_steps"] == ["1_refresh_raw", "3_reemit_stubs"]


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
