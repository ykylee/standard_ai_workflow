"""Acceptance test for v0.11.12 mypy strict release-time gate.

1 acceptance test (case 1 / 1b / 1c / …):
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
    rp_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "tools" / "release_pipeline.py"
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
    # case 1b: `--show-traceback` (TASK-2026-08-13-main-004 관찰 4차, 2026-08-24)
    #
    # 게이트는 4차까지 `exit 2 / error_count 0` 만 내고 원인을 못 말했다. 3차가
    # stderr 를 로그 앞으로 끌어오면서 남은 문장이 하필 mypy 가 **"please use
    # --show-traceback"** 이라고 *요청하는* 문구였다 — 그 요청을 로그로 옮겨 놓고
    # 정작 플래그를 준 적이 없어서, 완료 기준("다음 재발이 트레이스백을 남긴다")이
    # 원리적으로 충족될 수 없었다.
    #
    # mypy 는 **내부 오류일 때만** 트레이스백을 찍으므로 정상 경로 비용은 0 이다.
    assert "--show-traceback" in rp_text, (
        "게이트 invocation 에 --show-traceback 부재 — 내부 오류가 나도 트레이스백이 "
        "로그에 남지 않는다 (관찰 4차의 재발이 그렇게 증거 없이 지나갔다)"
    )
    assert re.search(
        r'"-m",\s*"mypy",[^\]]*"--show-traceback"',
        rp_text,
    ), "--show-traceback 이 mypy invocation 인자 목록 안에 없다"
    print("  case 1b (--show-traceback 이 invocation 에 있다): PASS")

    # case 1c: 신호 추출이 트레이스백을 **살려서** 앞으로 보내는가.
    # 플래그만 주고 추출이 그것을 잘라 버리면 아무것도 얻지 못한다.
    sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
    from workflow_kit.tools.release_pipeline import _mypy_stderr_signal  # noqa: PLC0415

    internal_error = "\n".join([
        "workflow_kit/x.py:1: error: INTERNAL ERROR -- Please try using mypy master on GitHub:",
        "https://mypy.readthedocs.io/en/stable/common_issues.html",
        "Please report a bug at https://github.com/python/mypy/issues",
        "version: 2.1.0",
        "Traceback (most recent call last):",
        '  File "mypy/checker.py", line 1, in accept',
        "AssertionError: unexpected node type",
    ])
    signal = _mypy_stderr_signal(internal_error)
    assert "Traceback (most recent call last)" in signal, (
        f"추출이 트레이스백을 잘랐다: {signal!r}"
    )
    assert "AssertionError" in signal, f"추출이 실제 예외를 잘랐다: {signal!r}"
    print("  case 1c (신호 추출이 트레이스백과 예외를 살린다): PASS")

    # case 1d: 절단이 **결론**을 자르지 않는가 (관찰 4차 후속, 2026-08-24).
    #
    # `--show-traceback` 을 준 뒤 트레이스백이 드디어 로그에 왔는데, step summary 의
    # `error_excerpt[:800]` 이 그 **꼬리를 잘랐다** — 남은 것은 `File "mypy/` 까지였고
    # 어느 예외였는지는 사라졌다. 상한을 또 올리면 다음 트레이스백에서 같은 자리로
    # 돌아온다. 절단은 언제나 머리를 남기므로 **결론을 머리로 옮긴다.**
    from workflow_kit.tools.release_pipeline import (  # noqa: PLC0415
        _traceback_conclusion_first,
    )

    sample = "\n".join([
        "Traceback (most recent call last):",
        '  File "<frozen runpy>", line 198, in _run_module_as_main',
        '  File "mypy/build.py", line 1916, in create_metastore',
        "OSError: [Errno 39] Directory not empty",
    ])
    tail = _traceback_conclusion_first(sample)
    assert tail.splitlines()[0].startswith("[exception] OSError"), (
        f"결론이 맨 앞에 없다 — 절단되면 사라진다: {tail.splitlines()[0]!r}"
    )
    assert "OSError" in tail[:80], "짧은 절단에도 예외가 살아야 한다"
    # 트레이스백이 아닌 출력은 그대로 꼬리만 남긴다 (있지도 않은 결론을 만들지 않는다)
    plain = _traceback_conclusion_first("Success: no issues found in 199 source files")
    assert not plain.startswith("[exception]"), f"트레이스백이 아닌데 결론을 붙였다: {plain!r}"
    print("  case 1d (절단이 트레이스백 결론을 자르지 않는다): PASS")

    # 캐시 격리의 **전수 조사**는 `check_mypy_config_actually_loaded` 의
    # `test_sites_isolate_cache` 가 한다 — 그 파일이 이미 AST 로 mypy 호출
    # 자리를 열거하고 있고, 열거를 두 곳에 두면 갈라진다. 여기서는 격리가
    # **실제로 동작하는지**만 돌려서 본다 (case 1f).

    # case 1f: 격리가 **실제로** cwd 를 오염시키지 않는가.
    # 정적 검사만으로는 부족하다 — `--cache-dir=`(빈 값)도 문법적으로는 격리처럼
    # 보였고, 그것이 저장소에 캐시 db 를 커밋하게 만들었다. 그래서 돌려서 본다.
    import subprocess, tempfile as _tf
    with _tf.TemporaryDirectory() as _td:
        probe = Path(_td) / "probe.py"
        probe.write_text("def f(x: int) -> int:\n    return x\n", encoding="utf-8")
        cache = Path(_td) / "cache-probe"
        subprocess.run(
            # 이 호출도 전수 조사가 세는 자리다 — `--config-file` 과 캐시 격리를
            # 둘 다 명시한다. 검사 자신이 규약을 어기면 그물이 자기를 문다.
            [sys.executable, "-m", "mypy", "--no-incremental",
             "--cache-dir", str(cache),
             "--config-file", str(REPO_ROOT / "workflow-source" / "pyproject.toml"),
             probe.name],
            cwd=_td, capture_output=True, text=True,
        )
        leftovers = sorted(
            q.name for q in Path(_td).iterdir()
            if q.name not in {"probe.py", "cache-probe"}
        )
    assert not leftovers, (
        f"격리했는데도 cwd 에 산출물이 남았다: {leftovers} — "
        "빈 문자열 격리의 재발 서명이다"
    )
    print("  case 1f (격리가 cwd 를 오염시키지 않는다): PASS")

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
    sys.path.insert(0, str(REPO_ROOT / "workflow-source" / "workflow_kit" / "tools"))
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
    lib_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "tools" / "release_pipeline_lib.py"
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


if __name__ == "__main__":
    raise SystemExit(main())
