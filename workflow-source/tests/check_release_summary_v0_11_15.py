"""Acceptance test for v0.11.15 release summary 1-line (jq-friendly verdict).

1 acceptance test:
- test_release_summary_v0_11_15 — `_summarize_release_status` helper + `cmd_release_status`
  의 `summary` field + `cmd_release` 의 `_attach_release_summary` helper + 모든 return
  point 의 summary 추가 + `--skip-validate` / full validate 시나리오별 summary verify
  + jq-friendly (1-line grep / pipe)

`ci_mypy=<verdict>` 머리는 mypy-strict CI 폐지(main-022) 후 늘 `skipped` 인 칸이라
TASK-2026-09-24-main-001 에서 걷었다. 되살아나면 red 가 나도록 **부재를 단언**한다.
"""
from __future__ import annotations

import io
import json
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
    # 5-field format: local_mypy / ready / next / unreleased / auto_bump
    for field in ("local_mypy=", "ready=", "next=", "unreleased=", "auto_bump="):
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
    for token in ("local_mypy=", "ready=", "next=", "unreleased="):
        assert token in summary, f"summary 에 {token!r} 부재: {summary!r}"
    assert "ci_mypy" not in summary and "ci_mypy" not in result, (
        f"은퇴한 ci_mypy 가 release-status 에 남았다: {summary!r}"
    )
    # 1-line verify (no newline)
    assert "\n" not in summary, f"summary 가 multi-line: {summary!r}"
    print(f"  case 2 (cmd_release_status summary field + 1-line + 5-field): PASS")

    # case 3: `_attach_release_summary` helper 존재 + 모든 cmd_release return point wrap
    rp_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "tools" / "release_pipeline.py"
    rp_text = rp_path.read_text(encoding="utf-8")
    assert "def _attach_release_summary" in rp_text, (
        "release_pipeline._attach_release_summary helper 부재"
    )
    # 모든 return point 가 `_attach_release_summary(...)` 를 돌려주는가 — AST 로 잰다.
    # 예전에는 들여쓰기별 "return " 문자열 수와 호출 수를 비교했는데, 깊은 들여쓰기의
    # return 은 세지 않고 중첩 함수의 return 은 세어 두 수가 서로 다른 것을 셌다.
    # 그 사이로 wrap 안 된 return 2개(원격 tag 충돌 · dry-run 정상 종료)가 숨어
    # 있었다 (TASK-2026-09-24-main-001 에서 발견·수리).
    import ast
    fn = next(n for n in ast.parse(rp_text).body
              if isinstance(n, ast.FunctionDef) and n.name == "cmd_release")

    def _own_nodes(node: ast.AST):  # type: ignore[no-untyped-def]
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue  # 중첩 함수의 return 은 cmd_release 의 return point 가 아니다
            yield child
            yield from _own_nodes(child)

    returns = [n for n in _own_nodes(fn) if isinstance(n, ast.Return)]
    unwrapped = [
        f"L{r.lineno}: {ast.unparse(r)[:60]}"
        for r in returns
        if not (isinstance(r.value, ast.Call)
                and getattr(r.value.func, "id", None) == "_attach_release_summary")
    ]
    assert returns, "cmd_release 에서 return 을 하나도 못 찾았다 — 판정이 아무것도 안 잰다"
    assert not unwrapped, f"summary 없이 돌아가는 return point: {unwrapped}"
    print(f"  case 3 (cmd_release 의 return point {len(returns)}개 전부 _attach_release_summary): PASS")

    # case 4: cmd_release_create dispatcher 호출 — summary field verify (--skip-validate)
    sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
    from workflow_kit.workflow_kit_cli import cmd_release_create
    argv = ["--version=0.11.15", "--skip-validate", "--json"]
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cmd_release_create(argv)
    parsed = json.loads(buf.getvalue())
    assert "summary" in parsed, "cmd_release_create --json 결과에 'summary' field 부재"
    # --skip-validate 인 경우: local_mypy 가 pre_check 에 없음 → summary 의 local_mypy 는 "skipped"
    s = parsed["summary"]
    assert "local_mypy=skipped" in s, (
        f"--skip-validate summary 의 local_mypy != 'skipped': {s!r}"
    )
    assert "ci_mypy" not in s and "ci_mypy" not in parsed, (
        f"은퇴한 ci_mypy 가 release 결과에 남았다: {s!r}"
    )
    assert "ready=false" in s, f"summary ready != false: {s!r}"
    assert "error=" in s, f"summary 에 error field 부재: {s!r}"
    print(f"  case 4 (cmd_release_create --skip-validate --json summary): PASS")

    # case 4b: ready 매핑을 **주입으로** 검증한다 — 환경이 아니라 매핑을 본다.
    # ready=true 는 error 부재 + local mypy ok 일 때뿐이다.
    ok_mypy = {"mypy": {"ok": True, "skipped": False, "error_count": 0}}
    cases = (
        ({"pre_check": ok_mypy}, "local_mypy=ok", "ready=true"),
        ({"pre_check": ok_mypy, "error": "boom"}, "local_mypy=ok", "ready=false"),
        ({"pre_check": {"mypy": {"ok": False, "error_count": 3}}}, "local_mypy=FAIL", "ready=false"),
        ({"pre_check": {"mypy": {"ok": True, "skipped": True}}}, "local_mypy=skipped", "ready=false"),
        ({"pre_check": {}}, "local_mypy=skipped", "ready=false"),
    )
    for results, want_local, want_ready in cases:
        got = _attach_release_summary_via_helper(dict(results))
        assert want_local in got and want_ready in got, (
            f"{results!r} → {want_local}/{want_ready} 여야 한다: {got!r}"
        )
    print(f"  case 4b (ready 매핑 {len(cases)}행 주입 검증): PASS")

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
    # format: "local_mypy=Y, ready=Z, next=W, unreleased=N, auto_bump=S"
    parts = dict(pair.split("=", 1) for pair in s.split(", "))
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
    # cmd_release summary format: local_mypy / ready / next / error (unreleased 없음)
    for token in ("local_mypy=", "ready=", "next=", "error="):
        assert token in s_full, f"cmd_release summary {token!r} 부재: {s_full!r}"
    assert "unreleased=" not in s_full, (
        f"cmd_release summary 에는 'unreleased' field 부재 (cmd_release_status 만): {s_full!r}"
    )
    assert "ci_mypy" not in s_full and "ci_mypy" not in parsed_full, (
        f"은퇴한 ci_mypy 가 full validate 결과에 남았다: {s_full!r}"
    )
    # `local_mypy` 는 값을 고정하지 않는다. 이 값은 **이 test 를 실행한
    # 인터프리터에 mypy 가 설치돼 있는가** 에 달려 있다. dev 의존성이 없는 해석기
    # (예: 해석기 매트릭스의 격리 venv)에서는 `FAIL` 이 되고, 그러면 구조적으로
    # 통과할 수 없는 단언이 된다. mypy 가 실제로 깨끗한지는
    # `check_mypy_strict_*` 계열이 본다 — 여기서 볼 것은 summary 의 계약이다.
    known_local = ("ok", "FAIL", "skipped")
    local_value = dict(p.split("=", 1) for p in s_full.split(", ") if "=" in p).get("local_mypy", "")
    assert local_value in known_local, (
        f"알 수 없는 local_mypy 값: {local_value!r} (알려진 값: {known_local}): {s_full!r}"
    )
    print(f"  case 7 (cmd_release full validate summary 4-field + known local_mypy): PASS")

    # case 8: helper 가 dict 를 mutate 하고 같은 dict 를 반환한다
    fake_results = {"pre_check": {"mypy": {"ok": True, "skipped": False, "error_count": 0}}}
    _attach_release_summary_via_helper(fake_results)
    assert "summary" in fake_results, "_attach_release_summary 가 dict 에 summary 추가 안 함"
    print("  case 8 (_attach_release_summary dict mutate): PASS")


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
