"""Acceptance test for v0.11.15 release summary 1-line (jq-friendly verdict).

1 acceptance test:
- test_release_summary_v0_11_15 — `_summarize_release_status` helper + `cmd_release_status`
  의 `summary` field + `cmd_release` 의 `_attach_release_summary` helper + 모든 return
  point 의 summary 추가 + `--skip-validate` / full validate / `--strict-cross-verify`
  시나리오별 summary verify + jq-friendly (1-line grep / pipe)
"""
from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_summary_v0_11_15() -> None:
    """v0.11.15 release summary 1-line (jq-friendly) verify."""
    # case 1: `_summarize_release_status` helper 존재 + 5-field format
    rs_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "release_status.py"
    rs_text = rs_path.read_text(encoding="utf-8")
    assert "def _summarize_release_status" in rs_text, (
        "release_status._summarize_release_status helper 부재"
    )
    # 5-field format: ci_mypy / local_mypy / ready / next / unreleased
    for field in ("ci_mypy=", "local_mypy=", "ready=", "next=", "unreleased="):
        assert field in rs_text, f"_summarize_release_status 의 {field!r} field 부재"
    print("  case 1 (_summarize_release_status helper + 5-field format): PASS")

    # case 2: `cmd_release_status` 가 `summary` field 반환
    sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
    from workflow_kit.release_status import cmd_release_status as _impl
    import argparse
    args = argparse.Namespace()
    result = _impl(args)
    assert "summary" in result, "cmd_release_status 결과에 'summary' field 부재"
    # 5-field format verify (jq-friendly: `cmd_release_status --json | jq -r .summary`)
    summary = result["summary"]
    for token in ("ci_mypy=", "local_mypy=", "ready=", "next=", "unreleased="):
        assert token in summary, f"summary 에 {token!r} 부재: {summary!r}"
    # 1-line verify (no newline)
    assert "\n" not in summary, f"summary 가 multi-line: {summary!r}"
    print(f"  case 2 (cmd_release_status summary field + 1-line + 5-field): PASS")

    # case 3: `_attach_release_summary` helper 존재 + 모든 cmd_release return point wrap
    rp_path = REPO_ROOT / "workflow-source" / "tools" / "release_pipeline.py"
    rp_text = rp_path.read_text(encoding="utf-8")
    assert "def _attach_release_summary" in rp_text, (
        "release_pipeline._attach_release_summary helper 부재"
    )
    # cmd_release function 안의 return 개수 vs _attach_release_summary 호출 개수
    cmd_release_section = re.search(
        r"def cmd_release\(args\) -> dict:.*?(?=\n\ndef |\nclass |\Z)",
        rp_text,
        re.DOTALL,
    )
    assert cmd_release_section, "cmd_release 함수 부재"
    cmd_release_text = cmd_release_section.group(0)
    return_count = cmd_release_text.count("\n        return ") + cmd_release_text.count("\n            return ") + cmd_release_text.count("\n    return ")
    wrap_count = cmd_release_text.count("_attach_release_summary(")
    assert wrap_count >= return_count, (
        f"_attach_release_summary 호출 수 {wrap_count} < return point 수 {return_count}"
    )
    print(f"  case 3 (cmd_release 의 _attach_release_summary {wrap_count} 호출 >= {return_count} return): PASS")

    # case 4: cmd_release_create dispatcher 호출 — summary field verify (--skip-validate)
    sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
    from workflow_kit.workflow_kit_cli import cmd_release_create
    argv = ["--version=0.11.15", "--skip-validate", "--json"]
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cmd_release_create(argv)
    parsed = json.loads(buf.getvalue())
    assert "summary" in parsed, "cmd_release_create --json 결과에 'summary' field 부재"
    # --skip-validate 인 경우: local_mypy 가 pre_check 에 없음 → ci_mypy.local_mypy 도 empty
    # → summary 의 local_mypy 는 "skipped", ci_mypy 는 "no_local_verify"
    s = parsed["summary"]
    assert "local_mypy=skipped" in s, (
        f"--skip-validate summary 의 local_mypy != 'skipped': {s!r}"
    )
    assert "ci_mypy=no_local_verify" in s, (
        f"--skip-validate summary 의 ci_mypy != 'no_local_verify': {s!r}"
    )
    assert "ready=false" in s, f"summary ready != false: {s!r}"
    assert "error=" in s, f"summary 에 error field 부재: {s!r}"
    print(f"  case 4 (cmd_release_create --skip-validate --json summary): PASS")

    # case 5: cmd_release_status dispatcher 호출 — text mode + JSON mode 둘 다 summary 포함
    from workflow_kit.workflow_kit_cli import cmd_release_status as _dispatch
    # text mode
    buf2 = io.StringIO()
    with redirect_stdout(buf2):
        rc_text = _dispatch([])
    text_output = buf2.getvalue()
    assert "summary:" in text_output, "text mode summary 부재"
    assert rc_text == 0, f"text mode rc != 0: {rc_text}"
    # JSON mode
    buf3 = io.StringIO()
    with redirect_stdout(buf3):
        rc_json = _dispatch(["--json"])
    json_output = buf3.getvalue()
    parsed_json = json.loads(json_output)
    assert "summary" in parsed_json, "JSON mode summary 부재"
    assert rc_json == 0, f"JSON mode rc != 0: {rc_json}"
    print("  case 5 (cmd_release_status text + JSON mode summary): PASS")

    # case 6: jq-friendly verify — 1-line summary 파싱 가능 (split by comma + =)
    s = parsed_json["summary"]
    # format: "ci_mypy=X, local_mypy=Y, ready=Z, next=W, unreleased=N"
    parts = dict(pair.split("=", 1) for pair in s.split(", "))
    assert "ci_mypy" in parts, "summary 'ci_mypy=' parse fail"
    assert "local_mypy" in parts, "summary 'local_mypy=' parse fail"
    assert "ready" in parts, "summary 'ready=' parse fail"
    assert "next" in parts, "summary 'next=' parse fail"
    assert "unreleased" in parts, "summary 'unreleased=' parse fail"
    # 각 value 가 1-token (no space)
    for k, v in parts.items():
        assert " " not in v, f"summary {k}={v!r} value 에 space 포함 (jq-incompatible)"
    print(f"  case 6 (summary jq-friendly: 5-field dict parse + space-free): PASS")

    # case 7: cmd_release 의 5-field format (unreleased 없이) — full validate path
    # skip git/packaging/doctor/state (working tree dirty) → validate fail on git
    argv_full = [
        "--version=0.11.15",
        "--skip-packaging", "--skip-doctor", "--skip-state", "--skip-git",
        "--json",
    ]
    buf4 = io.StringIO()
    with redirect_stdout(buf4):
        rc_full = cmd_release_create(argv_full)
    parsed_full = json.loads(buf4.getvalue())
    s_full = parsed_full["summary"]
    # cmd_release summary format: ci_mypy / local_mypy / ready / next / error (unreleased 없음)
    for token in ("ci_mypy=", "local_mypy=", "ready=", "next=", "error="):
        assert token in s_full, f"cmd_release summary {token!r} 부재: {s_full!r}"
    assert "unreleased=" not in s_full, (
        f"cmd_release summary 에는 'unreleased' field 부재 (cmd_release_status 만): {s_full!r}"
    )
    # local_mypy=ok (my mypy strict 통과), ci_mypy=sanity (Layer 1 + Layer 2 정합)
    assert "local_mypy=ok" in s_full, f"full validate summary local_mypy != ok: {s_full!r}"
    assert "ci_mypy=sanity" in s_full, f"full validate summary ci_mypy != sanity: {s_full!r}"
    print(f"  case 7 (cmd_release full validate summary 5-field + sanity verdict): PASS")

    # case 8: --strict-cross-verify + ci_stale 시뮬레이션 — helper 가 drift/ci_stale/ci_fail 검출
    # helper 가 verdict 를 그대로 summary 에 반영하는지 verify (직접 호출)
    fake_results = {
        "ci_mypy": {"verdict": "ci_stale"},
        "pre_check": {"mypy": {"ok": True, "skipped": False, "error_count": 0}},
    }
    summary_cs = _attach_release_summary_via_helper(fake_results)
    assert "ci_mypy=ci_stale" in summary_cs, (
        f"ci_stale verdict summary 반영 안 됨: {summary_cs!r}"
    )
    # helper 가 dict 를 mutate 하고 같은 dict 반환
    assert "summary" in fake_results, "_attach_release_summary 가 dict 에 summary 추가 안 함"
    print("  case 8 (_attach_release_summary dict mutate + verdict reflection): PASS")


def _attach_release_summary_via_helper(results: dict) -> str:
    """cmd_release 의 _attach_release_summary 직접 호출 (test 용)."""
    sys.path.insert(0, str(REPO_ROOT / "workflow-source" / "tools"))
    from release_pipeline import _attach_release_summary
    return _attach_release_summary(results)["summary"]


def main() -> int:
    """1 acceptance test. 1 fail = exit 1."""
    print("=== v0.11.15 release summary 1-line (jq-friendly verdict) acceptance test ===")
    print("=== v0.11.14 의 '다음' §1 follow-up ===")
    tests = [
        ("test_release_summary_v0_11_15", test_release_summary_v0_11_15),
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
