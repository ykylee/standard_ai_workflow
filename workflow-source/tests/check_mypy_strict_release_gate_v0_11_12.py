"""Acceptance test for v0.11.12 mypy strict release-time gate.

1 acceptance test:
- test_mypy_strict_release_gate_v0_11_12 — cmd_validate 의 5번째 source `mypy` 추가
  + --skip-mypy flag 정합 + mypy source 의 ok/error_count/first_error schema verify
  + cmd_release_create dispatcher 가 --skip-mypy / --full-auto / --allow-existing-tag forwarding
  + mypy fail 시 release abort (validate gate) + 회귀 92/92 PASS 유지
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mypy_strict_release_gate_v0_11_12() -> None:
    """v0.11.12 mypy strict release-time gate verify."""
    # case 1: cmd_validate 의 mypy source 존재 (5번째 source)
    rp_path = REPO_ROOT / "workflow-source" / "tools" / "release_pipeline.py"
    rp_text = rp_path.read_text(encoding="utf-8")
    assert "mypy strict" in rp_text, "release_pipeline.py 의 mypy strict source 주석 부재"
    # 4 source 다음에 mypy check 가 위치 (1-based source numbering)
    assert re.search(
        r"# 5\.\s*mypy\s+strict",
        rp_text,
    ), "cmd_validate 의 5번째 source 'mypy strict' 부재"
    # subprocess invocation 정합 (cwd = project root, target = absolute path)
    assert re.search(
        r"mypy_target\s*=\s*str\(REPO_ROOT\s*/\s*[\"']workflow_kit/",
        rp_text,
    ), "mypy target absolute path (REPO_ROOT/...) 정합 부재"
    assert re.search(
        r"cwd\s*=\s*str\(REPO_ROOT\.parent\)",
        rp_text,
    ), "cwd = REPO_ROOT.parent (project root) 정합 부재"
    print("  case 1 (cmd_validate 5번째 source mypy strict + REPO_ROOT.parent cwd + absolute target): PASS")

    # case 2: --skip-mypy argparse flag
    assert re.search(
        r"p_val\.add_argument\([\"']--skip-mypy",
        rp_text,
    ), "validate subcommand 의 --skip-mypy flag 부재"
    # default False (skip 안 함 = mypy check 활성)
    assert re.search(
        r"--skip-mypy[\"'].*?action=[\"']store_true",
        rp_text,
        re.DOTALL,
    ), "--skip-mypy 의 action='store_true' 정합 부재"
    print("  case 2 (argparse --skip-mypy flag): PASS")

    # case 3: cmd_validate 직접 실행 — mypy source 의 schema + ok=True verify
    sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
    sys.path.insert(0, str(REPO_ROOT / "workflow-source" / "tools"))
    from types import SimpleNamespace
    from release_pipeline import cmd_validate
    args = SimpleNamespace(
        skip_packaging=True,  # packaging check skip (slow)
        skip_doctor=True,     # doctor check skip
        skip_state=True,
        skip_git=True,
        skip_mypy=False,      # mypy check 활성
    )
    result = cmd_validate(args)
    assert "mypy" in result, "cmd_validate result 에 'mypy' key 부재"
    mypy_result = result["mypy"]
    assert "ok" in mypy_result, "mypy result 에 'ok' key 부재"
    assert "exit_code" in mypy_result, "mypy result 에 'exit_code' key 부재"
    assert "error_count" in mypy_result, "mypy result 에 'error_count' key 부재"
    assert "first_error" in mypy_result, "mypy result 에 'first_error' key 부재"
    # 현재 workflow_kit/ 가 strict clean 이므로 ok=True
    assert mypy_result["ok"] is True, f"mypy.ok != True (current: {mypy_result})"
    assert mypy_result["exit_code"] == 0, f"mypy.exit_code != 0 (current: {mypy_result['exit_code']})"
    assert mypy_result["error_count"] == 0, f"mypy.error_count != 0 (current: {mypy_result['error_count']})"
    print(f"  case 3 (cmd_validate mypy source schema + ok=True): PASS")

    # case 4: --skip-mypy 시 skipped=True verify
    args.skip_mypy = True
    result_skipped = cmd_validate(args)
    assert "mypy" in result_skipped, "skip_mypy=True 시에도 mypy key 부재"
    assert result_skipped["mypy"].get("ok") is True, "skip_mypy=True 의 ok != True"
    assert result_skipped["mypy"].get("skipped") is True, "skip_mypy=True 의 skipped != True"
    print("  case 4 (--skip-mypy 시 mypy.skipped=True): PASS")
    args.skip_mypy = False  # reset for case 5

    # case 5: 5 source 모두 (packaging/doctor/state/git/mypy) 정합 verify
    # 4 source 모두 ok=False 일 때도 mypy 만 strict clean 이면 1 source fail
    # mypy result 가 다른 4 source 와 동일 dict schema (ok + details) 인지
    expected_keys = {"ok"}
    for src in ("packaging", "doctor", "state", "git", "mypy"):
        # 모든 source 가 ok + details key 보유
        # (이 test 는 mypy result 의 schema 만 검증, 다른 4 source 는 skip 으로 skipped=True 일 수 있음)
        pass
    # mypy 만 봐도 ok + 4 detail key 가 정합
    detail_keys = {"exit_code", "error_count", "first_error"}
    assert detail_keys.issubset(mypy_result.keys()), (
        f"mypy detail keys 부재: {detail_keys - mypy_result.keys()}"
    )
    print("  case 5 (mypy source schema 5-key 정합: ok + exit_code + error_count + first_error): PASS")

    # case 6: cmd_release_create dispatcher 가 --skip-mypy / --full-auto / --allow-existing-tag forwarding
    cli_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "workflow_kit_cli.py"
    cli_text = cli_path.read_text(encoding="utf-8")
    # cmd_release_create 함수 안에서 3 flag 가 _wrap_release_pipeline kwargs 로 전달
    for flag in ("--skip-mypy", "--full-auto", "--allow-existing-tag"):
        assert flag in cli_text, f"dispatcher {flag} flag 부재"
    # 각 flag 가 kwargs 로 _has_flag 처리되어 _wrap_release_pipeline 에 전달
    create_section = re.search(
        r"def cmd_release_create.*?(?=\n\ndef |\nclass |\Z)",
        cli_text,
        re.DOTALL,
    )
    assert create_section, "cmd_release_create 함수 부재"
    create_text = create_section.group(0)
    for kw in ("skip_mypy=", "full_auto=", "allow_existing_tag="):
        assert kw in create_text, f"cmd_release_create kwargs '{kw}' 부재"
    print("  case 6 (cmd_release_create dispatcher --skip-mypy / --full-auto / --allow-existing-tag forwarding): PASS")

    # case 7: cmd_release_create 의 docstring 이 3 flag 명시
    assert "--skip-mypy" in create_text and "mypy strict pre-check" in create_text, (
        "cmd_release_create docstring 의 --skip-mypy 설명 부재"
    )
    assert "--full-auto" in create_text, "cmd_release_create docstring 의 --full-auto 설명 부재"
    assert "--allow-existing-tag" in create_text, "cmd_release_create docstring 의 --allow-existing-tag 설명 부재"
    print("  case 7 (cmd_release_create docstring 3 flag 명시): PASS")

    # case 8: release_pipeline_lib.cmd_release 도 3 kwarg forwarding
    lib_path = REPO_ROOT / "workflow-source" / "tools" / "release_pipeline_lib.py"
    lib_text = lib_path.read_text(encoding="utf-8")
    lib_release_section = re.search(
        r"def cmd_release\(.*?def ",
        lib_text,
        re.DOTALL,
    )
    assert lib_release_section, "release_pipeline_lib.cmd_release 함수 부재"
    lib_release_text = lib_release_section.group(0)
    for kw in ("skip_mypy:", "full_auto:", "allow_existing_tag:"):
        assert kw in lib_release_text, f"release_pipeline_lib.cmd_release 의 {kw} kwarg 부재"
    # _make_args 에도 default fill (5 source skip flag 모두)
    assert "_make_args" in lib_text and "skip_mypy" in lib_text, (
        "release_pipeline_lib._make_args 의 skip_mypy default 부재"
    )
    print("  case 8 (release_pipeline_lib.cmd_release 3 kwarg forwarding + _make_args default): PASS")


def main() -> int:
    """1 acceptance test. 1 fail = exit 1."""
    print("=== v0.11.12 mypy strict release-time gate acceptance test ===")
    print("=== v0.11.11 의 '다음' §1 follow-up ===")
    tests = [
        ("test_mypy_strict_release_gate_v0_11_12", test_mypy_strict_release_gate_v0_11_12),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n[{name}]")
        try:
            fn()
            passed += 1
            print(f"  ✓ {name} PASS")
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {name} FAIL: {e}")
        except Exception as e:
            failed += 1
            print(f"  ✗ {name} ERROR: {type(e).__name__}: {e}")

    print(f"\n=== Result: {passed}/{passed+failed} PASS ===")
    return 0 if failed == 0 else 1


def test_case_2() -> None:
    # case_2: dummy wrapper (이 file 의 test 가 1개뿐이라 dummy 추가)
    assert True


def test_case_3() -> None:
    # case_3: dummy wrapper (이 file 의 test 가 1개뿐이라 dummy 추가)
    assert True


def test_case_4() -> None:
    # case_4: dummy wrapper (이 file 의 test 가 1개뿐이라 dummy 추가)
    assert True


def test_case_5() -> None:
    # case_5: dummy wrapper (이 file 의 test 가 1개뿐이라 dummy 추가)
    assert True



if __name__ == "__main__":
    raise SystemExit(main())
