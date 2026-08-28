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
from unittest import mock
from pathlib import Path

WATCHES_ALL_REASON = (
    "release summary 는 kit 코드만 아니라 memory·문서·루트 매니페스트의 파생 "
    "정합까지 읽는다 — meta-watch 실측 (2026-08-28) 선언 밖 접근 1185건: 입력 "
    "표면이 사실상 저장소 전체다. 좁힌 선언은 사각지대였다 (ADR-028)"
)

# 병렬 전량(--jobs auto)에서 53s 실측 (2026-08-11) — 기본 60s 상한과 여유가
# 없어 부하 편차만으로 TIMEOUT flake 가 난다. 행(hang) 검출은 150s 로도 충분하다.
CHECK_TIMEOUT_S = 150


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
    # 이 호출이 **이 검사에서 유일한 실제 Layer 2 실행**이다 (아래 case 5 가 재사용).
    _real_local_mypy = result.get("local_mypy")
    # 5-field format verify (jq-friendly: `cmd_release_status --json | jq -r .summary`)
    summary = result["summary"]
    for token in ("ci_mypy=", "local_mypy=", "ready=", "next=", "unreleased="):
        assert token in summary, f"summary 에 {token!r} 부재: {summary!r}"
    # 1-line verify (no newline)
    assert "\n" not in summary, f"summary 가 multi-line: {summary!r}"
    print(f"  case 2 (cmd_release_status summary field + 1-line + 5-field): PASS")

    # case 3: `_attach_release_summary` helper 존재 + 모든 cmd_release return point wrap
    rp_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "tools" / "release_pipeline.py"
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
    # v1.0.2: `no_local_verify` 로 값을 고정하던 것이 (4)/(6) 과 같은 **자기참조**였다.
    # 이 값은 `_resolve_cross_verify_verdict` 매트릭스의 `ci_sanity` 행에서만 나온다.
    # HEAD 에 아직 mypy-strict run 이 없으면 CI verdict 는 `ci_stale` 이고, 그것이
    # *커밋 직후 push 직전* — 이 게이트가 정작 필요한 순간 — 의 정상 상태다.
    # 값은 알려진 집합에 드는지만 보고, 매트릭스 행 자체는 case 4b 에서 주입으로 본다.
    known_ci_skip = ("no_local_verify", "ci_stale", "ci_fail", "absent", "skipped")
    ci_skip_value = dict(p.split("=", 1) for p in s.split(", ") if "=" in p).get("ci_mypy", "")
    assert ci_skip_value in known_ci_skip, (
        f"--skip-validate summary 의 알 수 없는 ci_mypy: {ci_skip_value!r} "
        f"(알려진 값: {known_ci_skip}): {s!r}"
    )
    assert "ready=false" in s, f"summary ready != false: {s!r}"
    assert "error=" in s, f"summary 에 error field 부재: {s!r}"
    print(f"  case 4 (cmd_release_create --skip-validate --json summary): PASS")

    # case 4b: `no_local_verify` 행을 **주입으로** 검증한다 — 환경이 아니라 매핑을 본다.
    # (CI verdict = ci_sanity) x (local mypy 없음/skipped) → no_local_verify.
    sys.path.insert(0, str(REPO_ROOT / "workflow-source" / "workflow_kit" / "tools"))
    from release_pipeline import _resolve_cross_verify_verdict
    for local in ({}, {"skipped": True}):
        v = _resolve_cross_verify_verdict({"verdict": "ci_sanity"}, local)
        assert v == "no_local_verify", (
            f"ci_sanity + local={local!r} 는 no_local_verify 여야 한다: {v!r}"
        )
    # 매트릭스의 나머지 행도 함께 — CI verdict 가 sanity 가 아니면 그대로 통과시킨다.
    for ci_v in ("ci_stale", "ci_fail", "absent", "skipped"):
        v = _resolve_cross_verify_verdict({"verdict": ci_v}, {"ok": True})
        assert v == ci_v, f"CI verdict {ci_v!r} 는 그대로 나와야 한다: {v!r}"
    assert _resolve_cross_verify_verdict(
        {"verdict": "ci_sanity"}, {"ok": True}) == "sanity"
    assert _resolve_cross_verify_verdict(
        {"verdict": "ci_sanity"}, {"ok": False}) == "drift_warning"
    print("  case 4b (_resolve_cross_verify_verdict 매트릭스 7행 주입 검증): PASS")

    # case 5: cmd_release_status dispatcher 호출 — text mode + JSON mode 둘 다 summary 포함
    #
    # **Layer 2(mypy) 는 case 2 가 실제로 돌린 결과를 재사용한다.** 이 case 가 재는 것은
    # *dispatcher 출력에 summary 가 실리는가* 이지 mypy 판정이 아닌데, `cmd_release_status`
    # 는 호출마다 `mypy --no-incremental` 을 새로 돌린다 (1회 ~5.1s). 여기서만 2회 더
    # 돌아 이 검사의 32s 중 15.3s 가 mypy 3회였다 (2026-08-14 cProfile 실측).
    #
    # **가짜 값을 넣는 것이 아니다** — case 2 가 방금 실제로 얻은 그 판정을 그대로 준다.
    # 실행 계약(`--no-incremental`)은 손대지 않는다: 그건 CI·release gate·v1.0.0 Gate 3 이
    # 같은 invocation 을 쓰도록 `check_yaml_surfaces` / `check_mypy_strict_ci_v0_11_11` 이
    # 고정하고 있는 값이라, 여기서 바꾸면 게이트 간 동일성이 깨진다.
    from workflow_kit import release_status as _rs
    from workflow_kit.workflow_kit_cli import cmd_release_status as _dispatch
    with mock.patch.object(_rs, "_check_local_mypy", lambda: dict(_real_local_mypy or {})):
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
    # v1.0.2 — 여기서 `ci_mypy=sanity` 를 요구하던 것이 **자기참조**였다.
    #
    # `sanity` 는 "GH Actions 의 최신 mypy-strict run 이 success 이고 그 headSha 가 HEAD 와
    # 같다" 는 뜻이다. 그런데 이 test 는 smoke 의 일부로 **바로 그 commit 의 CI 안에서**
    # 돈다. 그 시점에는 같은 SHA 의 run 이 아직 없거나 진행 중이라 `ci_stale` 이 되고,
    # 결국 *구조적으로 통과할 수 없는* 단언이었다. 로컬에서도 push 하고 CI 가 끝나야만
    # green 이라, 이 검사 하나가 main 을 상시 red 로 만들고 있었다.
    #
    # 검사의 본래 목적은 "cmd_release 가 verdict 를 summary 에 제대로 싣는가" 라는
    # **계약**이다. 그 계약은 아래에서 verdict 를 주입해 검증한다 (case 7b / case 8).
    # 여기서는 환경에 의존하지 않는 것만 본다 — 값이 *알려진 verdict 집합에 드는가*.
    known_ci = ("sanity", "ci_sanity", "ci_stale", "ci_fail", "drift_warning",
                "absent", "skipped", "no_local_verify")
    ci_value = dict(p.split("=", 1) for p in s_full.split(", ") if "=" in p).get("ci_mypy", "")
    assert ci_value in known_ci, (
        f"알 수 없는 ci_mypy verdict: {ci_value!r} (알려진 값: {known_ci}) — "
        f"verdict 를 늘렸다면 이 목록도 함께 늘린다: {s_full!r}"
    )
    # `local_mypy` 도 같은 이유로 값을 고정하지 않는다. 이 값은 **이 test 를 실행한
    # 인터프리터에 mypy 가 설치돼 있는가** 에 달려 있다. smoke workflow 는 mypy 를
    # 설치하지 않으므로(그건 mypy-strict workflow 의 몫이다) CI 에서는 `FAIL` 이 되고,
    # 그러면 또 구조적으로 통과할 수 없는 단언이 된다. mypy 가 실제로 깨끗한지는
    # `check_mypy_strict_*` 계열이 본다 — 여기서 볼 것은 summary 의 계약이다.
    known_local = ("ok", "FAIL", "skipped")
    local_value = dict(p.split("=", 1) for p in s_full.split(", ") if "=" in p).get("local_mypy", "")
    assert local_value in known_local, (
        f"알 수 없는 local_mypy 값: {local_value!r} (알려진 값: {known_local}): {s_full!r}"
    )
    print(f"  case 7 (cmd_release full validate summary 5-field + known verdict): PASS")

    # case 7b: verdict 주입 — 환경이 아니라 **매핑**을 검증한다.
    summary_sanity = _attach_release_summary_via_helper({
        "ci_mypy": {"verdict": "sanity"},
        "pre_check": {"mypy": {"ok": True, "skipped": False, "error_count": 0}},
    })
    assert "ci_mypy=sanity" in summary_sanity, (
        f"sanity verdict 가 summary 에 반영되지 않았다: {summary_sanity!r}"
    )
    assert "local_mypy=ok" in summary_sanity, (
        f"local mypy ok 가 summary 에 반영되지 않았다: {summary_sanity!r}"
    )
    print("  case 7b (sanity + local ok 주입 → summary 반영): PASS")

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
    sys.path.insert(0, str(REPO_ROOT / "workflow-source" / "workflow_kit" / "tools"))
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
