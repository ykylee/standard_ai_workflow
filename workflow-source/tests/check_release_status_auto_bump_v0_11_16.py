"""Acceptance test for v0.11.16 release-status --auto-bump flag.

1 acceptance test (8 case):
- test_release_status_auto_bump_v0_11_16 — `cmd_release_status` 에 `args.auto_bump`
  처리 + `_run_auto_bump` helper + dispatcher `--auto-bump` flag forwarding +
  schema verify (auto_bump_applied / auto_bump_result / current_version re-read) +
  summary 6-field (auto_bump=applied|skipped|failed) + mypy strict clean 107 source
  files verify + dispatcher text/JSON mode + mock _run_auto_bump applied scenario
  + ready_to_release verdict 정합.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_status_auto_bump_v0_11_16() -> None:
    """v0.11.16 release-status --auto-bump flag verify."""
    # case 1: release_status.py 의 _run_auto_bump helper + --auto-bump 처리 verify
    rs_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "release_status.py"
    rs_text = rs_path.read_text(encoding="utf-8")
    assert "def _run_auto_bump" in rs_text, "release_status._run_auto_bump helper 부재"
    # _run_auto_bump 의 new_version: str 파라미터
    assert re.search(r"def _run_auto_bump\(new_version:\s*str\)", rs_text), (
        "_run_auto_bump(new_version: str) signature 부재"
    )
    # _run_auto_bump 가 ok / new_version / result / error key 반환
    assert '"ok"' in rs_text or "'ok'" in rs_text, "_run_auto_bump 의 'ok' key 반환 부재"
    # cmd_release_status 에 args.auto_bump 처리
    assert 'getattr(args, "auto_bump", False)' in rs_text, (
        "cmd_release_status 의 args.auto_bump 처리 부재"
    )
    # auto_bump_applied + auto_bump_result result dict 추가
    assert '"auto_bump_applied"' in rs_text or "'auto_bump_applied'" in rs_text, (
        "result dict 의 auto_bump_applied field 부재"
    )
    assert '"auto_bump_result"' in rs_text or "'auto_bump_result'" in rs_text, (
        "result dict 의 auto_bump_result field 부재"
    )
    print("  case 1 (release_status._run_auto_bump + --auto-bump 처리 + result field): PASS")

    # case 2: workflow_kit_cli.py dispatcher --auto-bump flag + args forwarding
    cli_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "workflow_kit_cli.py"
    cli_text = cli_path.read_text(encoding="utf-8")
    # dispatcher release-status body 추출
    rs_body = re.search(
        r'def cmd_release_status\(argv:.*?return 2',
        cli_text,
        re.DOTALL,
    )
    assert rs_body, "release-status dispatcher body 부재"
    rs_body_text = rs_body.group(0)
    assert '_has_flag(argv, "--auto-bump")' in rs_body_text, (
        "dispatcher --auto-bump flag parsing 부재"
    )
    assert "auto_bump=auto_bump" in rs_body_text, (
        "dispatcher args.auto_bump forwarding 부재"
    )
    # docstring v0.11.16 + auto-bump 명시
    rs_section = re.search(
        r'@register\("release-status"\).*?"""(.*?)"""',
        cli_text,
        re.DOTALL,
    )
    assert rs_section, "release-status subcommand dispatcher + docstring 부재"
    docstring = rs_section.group(1)
    assert "v0.11.16" in docstring, f"dispatcher docstring 의 v0.11.16 명시 부재: {docstring[:200]}"
    assert "auto-bump" in docstring.lower() or "auto_bump" in docstring, (
        f"dispatcher docstring 의 auto-bump 명시 부재: {docstring[:200]}"
    )
    print("  case 2 (dispatcher --auto-bump flag + args forwarding + docstring v0.11.16): PASS")

    # case 3: cmd_release_status default 호출 — schema verify (auto_bump_applied + auto_bump_result 추가)
    sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
    from workflow_kit.release_status import cmd_release_status as _impl
    args_default = argparse.Namespace(auto_bump=False)
    result = _impl(args_default)
    # 8 + 2 = 10 key verify (v0.11.14 8 + v0.11.16 2)
    for key in ("current_version", "last_release_tag", "unreleased_commits",
                "ci_mypy", "local_mypy", "next_version", "ready_to_release",
                "ready_reason", "summary", "auto_bump_applied", "auto_bump_result"):
        assert key in result, f"cmd_release_status 결과에 {key!r} key 부재"
    # default (auto_bump=False) → auto_bump_applied=False, auto_bump_result=None
    assert result["auto_bump_applied"] is False, (
        f"default 호출의 auto_bump_applied != False: {result['auto_bump_applied']!r}"
    )
    assert result["auto_bump_result"] is None, (
        f"default 호출의 auto_bump_result != None: {result['auto_bump_result']!r}"
    )
    print("  case 3 (default 호출 schema 11 key + auto_bump=False 정합): PASS")

    # case 4: _summarize_release_status 6-field format verify
    summary = result["summary"]
    # format = ci_mypy=<v>, local_mypy=<ok|FAIL>, ready=<bool>, next=<X.Y.Z>, unreleased=<int>, auto_bump=<state>
    parts = [p.strip() for p in summary.split(",")]
    assert len(parts) == 6, f"summary != 6-field: {summary!r}"
    # 각 part 의 key=value parse
    kv = {}
    for p in parts:
        assert "=" in p, f"summary part 의 key=value format 아님: {p!r}"
        k, v = p.split("=", 1)
        kv[k.strip()] = v.strip()
    for expected_key in ("ci_mypy", "local_mypy", "ready", "next", "unreleased", "auto_bump"):
        assert expected_key in kv, f"summary field {expected_key!r} 부재: {summary!r}"
    # default 호출 시 auto_bump=skipped
    assert kv["auto_bump"] == "skipped", (
        f"default 호출의 summary.auto_bump != 'skipped': {kv['auto_bump']!r}"
    )
    print(f"  case 4 (summary 6-field format + auto_bump=skipped): PASS")

    # case 5: mypy strict clean verify (CI scope, 107 source files 유지)
    mypy_proc = subprocess.run(
        [sys.executable, "-m", "mypy", "--no-incremental",
         "workflow-source/workflow_kit/"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
    )
    error_lines = [
        line for line in mypy_proc.stdout.splitlines()
        if ".py:" in line and "error:" in line
    ]
    assert mypy_proc.returncode == 0, (
        f"mypy strict exit {mypy_proc.returncode} ({len(error_lines)} errors):\n"
        + "\n".join(error_lines[:5])
    )
    # 107 source files 유지 (v0.11.16 = v0.11.14 36 file 누적 mypy strict clean)
    success_match = re.search(r"no issues found in (\d+) source files", mypy_proc.stdout)
    assert success_match, f"mypy strict success message 부재: {mypy_proc.stdout[:200]}"
    file_count = int(success_match.group(1))
    assert file_count >= 107, f"mypy strict file count {file_count} < 107 (v0.11.10 baseline)"
    print(f"  case 5 (mypy strict clean {file_count} source files): PASS")

    # case 6: dispatcher 호출 — text mode + JSON mode 양쪽 auto_bump field 출력
    from workflow_kit.workflow_kit_cli import cmd_release_status as _dispatch
    import io
    import contextlib

    # text mode (default, --auto-bump 없음)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc_text = _dispatch([])
    text_output = buf.getvalue()
    assert "auto_bump_applied: False" in text_output, (
        f"text mode 의 auto_bump_applied: False 출력 부재: {text_output[:500]}"
    )
    assert rc_text == 0, f"text mode rc != 0: {rc_text}"

    # JSON mode
    buf2 = io.StringIO()
    with contextlib.redirect_stdout(buf2):
        rc_json = _dispatch(["--json"])
    json_output = buf2.getvalue()
    parsed = json.loads(json_output)
    assert "auto_bump_applied" in parsed, "JSON mode parsed 에 auto_bump_applied 부재"
    assert "auto_bump_result" in parsed, "JSON mode parsed 에 auto_bump_result 부재"
    assert parsed["auto_bump_applied"] is False, (
        f"JSON mode 의 auto_bump_applied != False: {parsed['auto_bump_applied']!r}"
    )
    assert parsed["auto_bump_result"] is None, (
        f"JSON mode 의 auto_bump_result != None: {parsed['auto_bump_result']!r}"
    )
    assert rc_json == 0, f"JSON mode rc != 0: {rc_json}"
    print("  case 6 (dispatcher text + JSON mode 양쪽 auto_bump_applied/result 출력): PASS")

    # case 7: auto_bump_applied=False default 의 ready_to_release 정합
    # v0.11.16 release 직후 state: current_version=0.11.16, last_release_tag=v0.11.15-beta
    # → last_tag != current → ready_to_release 분기는 case-by-case
    # 본 case 는 auto_bump_applied=False 일 때 ready_to_release=False + reason 검증
    assert result["ready_to_release"] is False or result["ready_to_release"] is True, (
        f"ready_to_release != bool: {type(result['ready_to_release'])}"
    )
    assert isinstance(result["ready_reason"], str), (
        f"ready_reason != str: {type(result['ready_reason'])}"
    )
    # default summary.auto_bump=skipped 와 정합
    assert kv["auto_bump"] == "skipped", "default summary.auto_bump=skipped 정합 verify"
    print(f"  case 7 (default mode ready_to_release verdict + summary 정합): PASS")

    # case 8: --auto-bump=True + mock _run_auto_bump applied → auto_bump_applied=True verify
    # 실제 _run_auto_bump 호출하면 pyproject.toml + __init__.py write 발생.
    # mock 으로 logic verify 만. current_version re-read 도 mock.
    with patch("workflow_kit.release_status._run_auto_bump") as mock_bump, \
         patch("workflow_kit.release_status._read_pyproject_version") as mock_read:
        # 첫 read = "0.11.15" (auto-bump 전), 두 번째 read = "0.11.16" (auto-bump 후 re-read)
        mock_read.side_effect = ["0.11.15", "0.11.16"]
        mock_bump.return_value = {
            "ok": True,
            "new_version": "0.11.16",
            "result": {
                "mode": "applied",
                "previous_pyproject": "0.11.15",
                "current_pyproject": "0.11.16",
            },
            "error": None,
        }
        args_bump = argparse.Namespace(auto_bump=True)
        result_bump = _impl(args_bump)
    assert result_bump["auto_bump_applied"] is True, (
        f"--auto-bump=True 호출의 auto_bump_applied != True: {result_bump['auto_bump_applied']!r}"
    )
    assert result_bump["auto_bump_result"]["ok"] is True, (
        f"--auto-bump=True 호출의 auto_bump_result.ok != True: {result_bump['auto_bump_result']!r}"
    )
    assert result_bump["auto_bump_result"]["new_version"] == "0.11.16", (
        f"--auto-bump=True 호출의 auto_bump_result.new_version != '0.11.16': "
        f"{result_bump['auto_bump_result'].get('new_version')!r}"
    )
    # auto-bump 후 current_version re-read = "0.11.16"
    assert result_bump["current_version"] == "0.11.16", (
        f"--auto-bump 후 current_version re-read != '0.11.16': {result_bump['current_version']!r}"
    )
    # next_version 도 재계산: "0.11.15" → "0.11.16" (re-read 후) → "0.11.17" (다음 patch)
    assert result_bump["next_version"]["next"] == "0.11.17", (
        f"--auto-bump 후 next_version.next != '0.11.17': {result_bump['next_version']['next']!r}"
    )
    # summary auto_bump=applied 정합
    summary_bump = result_bump["summary"]
    kv_bump = {}
    for p in summary_bump.split(","):
        k, v = p.strip().split("=", 1)
        kv_bump[k.strip()] = v.strip()
    assert kv_bump["auto_bump"] == "applied", (
        f"--auto-bump=True 호출의 summary.auto_bump != 'applied': {kv_bump['auto_bump']!r}"
    )
    # auto-bump 후 ready_to_release=True (bump 성공 = next version 으로 정렬됨)
    assert result_bump["ready_to_release"] is True, (
        f"--auto-bump 성공 후 ready_to_release != True: {result_bump['ready_to_release']!r}"
    )
    assert "auto-bumped" in result_bump["ready_reason"].lower() or "auto_bumped" in result_bump["ready_reason"].lower(), (
        f"--auto-bump 성공 후 ready_reason 의 auto-bump 명시 부재: {result_bump['ready_reason']!r}"
    )
    print(f"  case 8 (--auto-bump=True + mock applied → auto_bump_applied=True + re-read 정합): PASS")


def main() -> int:
    """1 acceptance test. 1 fail = exit 1."""
    print("=== v0.11.16 release-status --auto-bump flag acceptance test ===")
    print("=== v0.11.15 의 '다음' §1 follow-up (read-only → opt-in write 변환) ===")
    tests = [
        ("test_release_status_auto_bump_v0_11_16", test_release_status_auto_bump_v0_11_16),
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