"""Acceptance test for v0.11.14 release-status dispatcher subcommand.

1 acceptance test:
- test_release_status_v0_11_14 — `release_status.py` 신규 module + dispatcher
  `release-status` subcommand + __init__.py 의 release_status import/export +
  cumulative strict clean 35 → 36 (v0.11.14) + schema verify (current_version /
  last_release_tag / unreleased_commits / ci_mypy / local_mypy / next_version /
  ready_to_release / ready_reason) + mypy strict clean 107 source files verify
  + cmd_release_status dispatcher text/JSON mode
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# 병렬 전량(--jobs auto)에서 55s 실측 (2026-08-11) — 기본 60s 상한과 여유가
# 없어 부하 편차만으로 TIMEOUT flake 가 난다. 행(hang) 검출은 150s 로도 충분하다.
CHECK_TIMEOUT_S = 150

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
)
"""릴리스 상태는 workflow_kit 전체(mypy 대상) + 버전 파일의 함수다."""


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_status_v0_11_14() -> None:
    """v0.11.14 release-status dispatcher subcommand verify."""
    # case 1: workflow_kit/release_status.py 신규 module 존재
    rs_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "release_status.py"
    assert rs_path.exists(), f"workflow_kit/release_status.py 부재: {rs_path}"
    # cmd_release_status 함수 + 5 helper (_read_pyproject_version / _last_release_tag /
    # _unreleased_commits / _suggest_next_version / _check_local_mypy / _check_ci_mypy)
    rs_text = rs_path.read_text(encoding="utf-8")
    assert "def cmd_release_status" in rs_text, "release_status.cmd_release_status 함수 부재"
    for helper in ("_read_pyproject_version", "_last_release_tag", "_unreleased_commits",
                   "_suggest_next_version", "_check_local_mypy", "_check_ci_mypy"):
        assert f"def {helper}" in rs_text, f"release_status.{helper} helper 부재"
    print("  case 1 (release_status.py 신규 + 6 helper + cmd_release_status): PASS")

    # case 2: __init__.py 의 release_status import + __all__ + cumulative count 36
    init_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "__init__.py"
    init_text = init_path.read_text(encoding="utf-8")
    assert "    release_status," in init_text, "__init__.py 의 release_status import 부재"
    assert '"release_status",' in init_text, "__init__.py 의 __all__ 에 release_status 부재"
    # cumulative count 36 갱신
    count_match = re.search(
        r"v0\.11\.14\s*누적:\s*(\d+)\s*file\s*strict\s*clean",
        init_text,
    )
    assert count_match, "__init__.py 의 v0.11.14 누적 count 주석 부재"
    new_count = int(count_match.group(1))
    assert new_count >= 36, f"v0.11.14 cumulative count {new_count} < 36 (v0.11.10 baseline 35 + v0.11.14 release_status.py)"
    print(f"  case 2 (__init__.py import + __all__ + cumulative count {new_count} >= 36): PASS")

    # case 3: dispatcher `release-status` subcommand + @register
    cli_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "workflow_kit_cli.py"
    cli_text = cli_path.read_text(encoding="utf-8")
    assert '@register("release-status")' in cli_text, "dispatcher @register('release-status') 부재"
    assert "def cmd_release_status" in cli_text, "dispatcher cmd_release_status 함수 부재"
    # docstring 갱신: @register 라인부터 docstring 끝까지
    rs_section = re.search(
        r'@register\("release-status"\).*?"""(.*?)"""',
        cli_text,
        re.DOTALL,
    )
    assert rs_section, "release-status subcommand dispatcher + docstring 부재"
    docstring = rs_section.group(1)
    assert "v0.11.14" in docstring, f"dispatcher docstring 의 v0.11.14 명시 부재: {docstring[:200]}"
    assert "read-only" in docstring, f"dispatcher docstring 의 read-only 명시 부재: {docstring[:200]}"
    print("  case 3 (dispatcher @register('release-status') + docstring v0.11.14/read-only): PASS")

    # case 4: dispatcher args --json (text/JSON mode)
    rs_body = re.search(
        r'def cmd_release_status\(argv:.*?return 2',
        cli_text,
        re.DOTALL,
    )
    assert rs_body, "release-status dispatcher body 부재"
    rs_body_text = rs_body.group(0)
    assert "_has_flag(argv, \"--json\")" in rs_body_text, "--json flag 처리 부재"
    assert "json.dumps" in rs_body_text, "JSON output 부재"
    assert "current_version:" in rs_body_text, "text mode output (current_version) 부재"
    print("  case 4 (dispatcher --json + json.dumps + text mode): PASS")

    # case 5: cmd_release_status 직접 실행 — schema verify
    sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
    from workflow_kit.release_status import cmd_release_status as _impl
    import argparse
    args = argparse.Namespace()
    result = _impl(args)
    # schema 8 key verify
    for key in ("current_version", "last_release_tag", "unreleased_commits",
                "ci_mypy", "local_mypy", "next_version", "ready_to_release", "ready_reason"):
        assert key in result, f"cmd_release_status 결과에 {key!r} key 부재"
    # current_version format = X.Y.Z
    assert re.match(r"^\d+\.\d+\.\d+$", str(result.get("current_version", ""))), (
        f"current_version != X.Y.Z format: {result.get('current_version')!r}"
    )
    # ci_mypy schema (v0.11.13+ cross-verify)
    ci = result["ci_mypy"]
    for k in ("verdict", "head_sha_match", "ci_run", "message"):
        assert k in ci, f"ci_mypy 에 {k!r} 부재"
    # local_mypy schema
    lm = result["local_mypy"]
    for k in ("ok", "exit_code", "error_count", "first_error"):
        assert k in lm, f"local_mypy 에 {k!r} 부재"
    # next_version schema
    nv = result["next_version"]
    for k in ("next", "current", "bumped"):
        assert k in nv, f"next_version 에 {k!r} 부재"
    # ready_to_release + ready_reason (boolean + string)
    assert isinstance(result["ready_to_release"], bool), (
        f"ready_to_release != bool: {type(result['ready_to_release'])}"
    )
    assert isinstance(result["ready_reason"], str), (
        f"ready_reason != str: {type(result['ready_reason'])}"
    )
    print("  case 5 (cmd_release_status schema 8 key + nested schema verify): PASS")

    # case 6: mypy strict clean verify (CI scope, 107 source files)
    mypy_proc = subprocess.run(
        [sys.executable, "-m", "mypy", "--no-incremental",
             # v1.0.2: config 명시. cwd(REPO_ROOT)에는 [tool.mypy] 가 없어
             # 암묵적 탐색은 `Config File: Default` 로 떨어진다 — strict 미적용.
             "--config-file", "workflow-source/pyproject.toml",
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
    # 107 source files (was 106 + release_status.py = 107)
    success_match = re.search(r"no issues found in (\d+) source files", mypy_proc.stdout)
    assert success_match, f"mypy strict success message 부재: {mypy_proc.stdout[:200]}"
    file_count = int(success_match.group(1))
    assert file_count >= 107, f"mypy strict file count {file_count} < 107 (expected v0.11.10 106 + release_status.py)"
    print(f"  case 6 (mypy strict clean {file_count} source files): PASS")

    # case 7: dispatcher 호출 — text mode + JSON mode 둘 다
    #
    # **Layer 2(mypy) 는 case 5 가 실제로 얻은 판정을 재사용한다.** 이 case 가 재는 것은
    # *dispatcher 가 두 모드로 rc=0 과 필수 field 를 내는가* 이지 mypy 판정이 아닌데,
    # `cmd_release_status` 는 호출마다 `mypy --no-incremental` 을 새로 돌린다 (~5.1s).
    # 여기서만 2회 더 돌아 이 검사 22.9s 중 mypy 3회가 15.4s 였다 (2026-08-14 cProfile).
    # 가짜 값이 아니라 case 5 의 실측 그대로다. 실제 mypy 판정은 바로 위 case 6 이
    # 자기 subprocess 로 따로 재고 있고, 실행 계약(`--no-incremental`)은 손대지 않는다.
    from workflow_kit import release_status as _rs
    from workflow_kit.workflow_kit_cli import cmd_release_status as _dispatch
    from unittest import mock
    # text mode
    import io
    import contextlib
    with mock.patch.object(_rs, "_check_local_mypy", lambda: dict(result["local_mypy"] or {})):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_text = _dispatch([])
        text_output = buf.getvalue()
        assert "current_version:" in text_output, "text mode output 부재"
        assert "ready_to_release:" in text_output, "text mode ready_to_release 부재"
        assert rc_text == 0, f"text mode rc != 0: {rc_text}"
        # JSON mode
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            rc_json = _dispatch(["--json"])
        json_output = buf2.getvalue()
    parsed = json.loads(json_output)
    assert "current_version" in parsed, "JSON mode parsed 부재"
    assert "ready_to_release" in parsed, "JSON mode ready_to_release 부재"
    assert rc_json == 0, f"JSON mode rc != 0: {rc_json}"
    print("  case 7 (dispatcher text + JSON mode 둘 다 rc=0): PASS")

    # case 8: ready_to_release verdict logic — current_version == last_release_tag → ready=False
    # v0.11.14 original assertion: "방금 v0.11.13 release 후이므로 본 commit 시점의 current_version 은 0.11.13,
    # last_release_tag 는 v0.11.13-beta, → ready=False + reason='current_version already at last_release_tag'"
    # v0.11.16 robust fix: 시간 의존적 assertion 제거. current == last_tag 일 때만 ready=False 검증
    # (방금 release 직후 시나리오 + 다음 release 진행 중 시나리오 둘 다 handle).
    last_tag_norm = (result["last_release_tag"] or "").lstrip("v").rstrip("-beta")
    current_ver = str(result["current_version"])
    if last_tag_norm and last_tag_norm == current_ver:
        # 방금 release 직후 시나리오 (current == last_tag): ready=False 정합
        assert result["ready_to_release"] is False, (
            f"방금 release 직후 (current==last_tag={current_ver}) → ready_to_release=True (expected False): {result['ready_to_release']}"
        )
        assert "last_release_tag" in result["ready_reason"] or "release_tag" in result["ready_reason"], (
            f"ready_reason 이 last_release_tag mismatch 설명 안 함: {result['ready_reason']!r}"
        )
        print(f"  case 8 (방금 release 직후: ready=False + last_release_tag reason, current==last_tag={current_ver}): PASS")
    else:
        # 다음 release 진행 중 시나리오 (current != last_tag): 다른 조건으로 ready 결정
        # verdict logic 의 핵심 분기 (current==last_tag → ready=False) 는 위의 if 분기에서 검증됨
        # 본 분기는 current != last_tag 일 때의 정상 동작 확인 (어떤 ready verdict 든 acceptable)
        assert isinstance(result["ready_to_release"], bool), (
            f"current != last_tag 시나리오의 ready_to_release != bool: {type(result['ready_to_release'])}"
        )
        print(f"  case 8 (다음 release 진행 중: current={current_ver} != last_tag={result['last_release_tag']!r}, ready_to_release={result['ready_to_release']} by 다른 분기): PASS")


def test_next_version_is_derived_from_commits_v1_2_2() -> None:
    """`next_version` 이 **미발행 커밋 유형에서 파생**된다 (TASK-2026-08-20-main-006).

    이전 구현은 `current + 0.0.1` 고정이었고 커밋을 아예 읽지 않았다. 그런데 그
    값은 같은 summary 줄에서 `unreleased=<N>` 옆에 찍힌다 — **개수는 세면서 판정은
    안 세니** 파생값처럼 보이는 상수였다. 실측(2026-08-20): feat 18 · fix 24 ·
    breaking 1 인 사이클에 `1.2.1`(patch)을 권했다.
    """
    import importlib

    mod = importlib.import_module("workflow_kit.release_status")
    importlib.reload(mod)

    def commits(*subjects: str) -> list[dict[str, str]]:
        return [{"sha": f"{i:07d}", "subject": s} for i, s in enumerate(subjects)]

    problems: list[str] = []

    # breaking → major, 그리고 **숫자만 내밀지 않는다**
    br = mod._suggest_next_version("1.2.0", commits=commits("feat(okf)!: v0.2 이행", "fix: x"))
    if br["next"] != "2.0.0" or br.get("level") != "major":
        problems.append(f"breaking → {br['next']} / {br.get('level')}")
    if not br.get("requires_decision"):
        problems.append("major 를 사람 결정 없이 확정했다")
    if not br["basis"]["breaking"]:
        problems.append("근거(breaking 제목)가 비었다")

    # feat → minor
    ft = mod._suggest_next_version("1.2.0", commits=commits("feat: a", "docs: b"))
    if ft["next"] != "1.3.0" or ft.get("level") != "minor":
        problems.append(f"feat → {ft['next']} / {ft.get('level')}")
    if ft.get("requires_decision"):
        problems.append("minor 에 결정 요구가 붙었다")

    # 그 외 → patch
    px = mod._suggest_next_version("1.2.0", commits=commits("fix: a", "chore: b"))
    if px["next"] != "1.2.1" or px.get("level") != "patch":
        problems.append(f"fix/chore → {px['next']} / {px.get('level')}")

    # 근거 없음 → patch 이되 **근거 없음을 밝힌다**
    none = mod._suggest_next_version("1.2.0")
    if none["next"] != "1.2.1":
        problems.append(f"근거 없음 → {none['next']}")
    if none["basis"]["total"] != 0:
        problems.append(f"근거 없음인데 total={none['basis']['total']}")

    # scope 가 붙은 breaking 표기도 잡는다
    scoped = mod._suggest_next_version("1.2.0", commits=commits("refactor(core)!: drop shim"))
    if scoped.get("level") != "major":
        problems.append(f"scoped breaking 미탐지: {scoped.get('level')}")

    assert not problems, "; ".join(problems)


def main() -> int:
    """1 acceptance test. 1 fail = exit 1."""
    print("=== v0.11.14 release-status dispatcher subcommand acceptance test ===")
    print("=== v0.11.13 의 '다음' §1 follow-up (신규 workflow_kit/<module>.py mypy strict clean) ===")
    tests = [
        ("test_release_status_v0_11_14", test_release_status_v0_11_14),
        ("test_next_version_is_derived_from_commits_v1_2_2", test_next_version_is_derived_from_commits_v1_2_2),
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
