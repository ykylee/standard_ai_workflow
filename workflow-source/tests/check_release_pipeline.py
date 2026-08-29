"""tools/release_pipeline.py smoke test (v0.7.9+).

3 subcommand 의 release pipeline 정합성 검증.
- validate: 4 source (packaging, doctor, state, git) 의 release-readiness
- version-bump: pyproject.toml version patch (--patch / --minor / --major / --to)
- note-draft: git log <from>..HEAD → release note skeleton 자동 생성

Test 구성 (8 test):
1. validate --json output: 4 source 결과 dict
2. version-bump --patch dry-run: current 0.7.8 → next 0.7.9
3. version-bump --to=0.8.0 dry-run: 명시 버전 적용
4. version-bump apply: 저장소 사본(sandbox)에서 실제 갱신 검증 — 원본 무접촉
5. note-draft dry-run: output_path + commits count
6. parse_version: 'X.Y.Z' / 'X.Y.Z-suffix' 정합
7. bump_version: major / minor / patch / to 분기
8. main CLI: --dry-run / --apply / subcommand help

Reference:
- tools/release_pipeline.py 본체
- tools/check_packaging.py (validate 의 packaging source)
- workflow_kit.cli.doctor (v0.7.8, validate 의 doctor source)
- tools/refresh_wiki_memory.py (v0.7.5, note-draft 의 git log 패턴)
- memory #5 standard-ai-workflow.md (release 채널 정책)
"""

from __future__ import annotations

#: 의도적 전역 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES_ALL_REASON = (
    "release pipeline 의 validate/version-bump/dist 가 "
    "packaging·doctor·state·git 네 source 의 release-readiness 를 훑는다 — "
    "meta-watch 실측 (2026-08-29) 접근 2076건 · 최상위 30개 항목 전부: 입력 표면이 사실상 저장소 "
    "전체다"
)

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline.py"
PYPROJECT = SOURCE_ROOT / "pyproject.toml"


def _import_tool():
    """release_pipeline.py 를 importlib 로 로드."""
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location("release_pipeline", str(TOOL))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["release_pipeline"] = mod  # 3.14 dataclass 호환
    spec.loader.exec_module(mod)
    return mod


# --- Test 1: validate --json output ---


def test_validate_json_output() -> None:
    """validate --json output 이 4 source 결과 dict 반환."""
    proc = subprocess.run(
        [sys.executable, str(TOOL), "validate",
         "--skip-packaging", "--skip-doctor",
         "--json"],
        capture_output=True, text=True, timeout=60,
    )
    # exit 0 또는 1 (git.status untracked 있을 수 있음) — JSON parse 가능 검증
    out = json.loads(proc.stdout)
    assert "packaging" in out
    assert "doctor" in out
    assert "state" in out
    assert "git" in out


# --- Test 2: version-bump --patch dry-run ---


def test_version_bump_patch_dry_run() -> None:
    """version-bump --patch dry-run: current 0.7.x → next 0.7.x+1."""
    mod = _import_tool()
    current = mod.read_version()
    result = mod.cmd_version_bump(type("Args", (), {"patch": True, "minor": False, "major": False, "to": None, "dry_run": True, "apply": False, "no_init": False})())
    assert result["mode"] == "dry-run"
    major, minor, patch = mod.parse_version(current)
    expected = f"{major}.{minor}.{patch + 1}"
    assert result["next_pyproject"] == expected


# --- Test 3: version-bump --to=... dry-run ---


def test_version_bump_to_explicit() -> None:
    """--to=0.8.0 명시 시 그대로 사용."""
    mod = _import_tool()
    result = mod.cmd_version_bump(type("Args", (), {"patch": False, "minor": False, "major": False, "to": "0.8.0", "dry_run": True, "apply": False, "no_init": False})())
    assert result["next_pyproject"] == "0.8.0"


# --- Test 4: version-bump apply (sandbox — 원본 무접촉) ---


def test_version_bump_apply_in_sandbox() -> None:
    """--apply 는 저장소 **사본**에서 검증한다 (TASK-2026-08-13-main-001).

    이전 형태는 원본 pyproject 를 bump 했다가 finally 로 되돌렸다. **되돌리는 것은
    안 건드리는 것이 아니다**: 왕복 86ms 동안 병렬 검사와 다른 에이전트는 틀린
    버전을 읽고 (mypy 는 시작 시 pyproject 를 config 로 읽는다 — CI native 셀
    exit 2 flake 의 유력 원인, TASK-2026-08-13-main-004), 프로세스가 죽으면
    복원되지 않는다. watch_transient_writer 실측으로 이 test 가 전량 중 유일한
    원본 pyproject writer 였음을 확인하고 sandbox 로 옮겼다.

    skip-sync-hash: post-step 을 켜면 git amend 가 필요한데 sandbox 는 `.git` 없이
    복사된다 (본 test 의 검증 대상은 pyproject/__init__ 갱신뿐이다).
    """
    from _repo_sandbox import repo_sandbox

    origin_before = PYPROJECT.read_bytes()
    version_re = re.compile(r'^version\s*=\s*"([^"]+)"', re.M)
    with repo_sandbox(SOURCE_ROOT.parent) as sandbox:
        src = sandbox / "workflow-source"
        before = version_re.search((src / "pyproject.toml").read_text(encoding="utf-8")).group(1)
        proc = subprocess.run(
            [sys.executable, str(src / "workflow_kit" / "tools" / "release_pipeline.py"),
             "version-bump", "--patch", "--apply", "--skip-sync-hash", "--json"],
            capture_output=True, text=True, timeout=60, cwd=str(sandbox),
        )
        assert proc.returncode == 0, f"exit {proc.returncode}: {proc.stderr}"
        result = json.loads(proc.stdout)
        assert result["mode"] == "applied"
        assert result["previous_pyproject"] == before
        assert result["current_pyproject"] != before
        # 사본 파일 갱신 검증
        after = version_re.search((src / "pyproject.toml").read_text(encoding="utf-8")).group(1)
        assert after == result["current_pyproject"]
        # __init__.py auto-sync 검증
        assert "current_workflow_kit" in result
        init_text = (src / "workflow_kit" / "__init__.py").read_text(encoding="utf-8")
        assert result["current_workflow_kit"] in init_text
    # 원본은 내내 그대로여야 한다 — 이 단언이 깨지면 sandbox 이관이 무력화된 것이다.
    assert PYPROJECT.read_bytes() == origin_before, "원본 pyproject 가 변경됐다"


def test_doc_headers_update_syncs_distributed_core() -> None:
    """doc-headers-update 가 `ai-workflow/core/` 배포 사본까지 맞추는가 (v1.2.0).

    v1.2.0 발행 직후 전량이 잡은 드리프트의 근본 자리다: 갱신기가 정본
    (`workflow-source/core/*.md`) 의 '최종 수정일' 만 고치고 사본을 몰라
    `check_standard_single_source` case 4 가 23개 드리프트로 red 를 냈다.
    검출기는 이미 있었고, 없던 것은 **만드는 층의 규약 인지**였다.

    사본에 낡은 날짜를 되주입한 sandbox 에서 갱신기를 돌려, 사본이 정본과
    byte 동일(선두 kit 마커 제외)로 수렴하는지 본다. 갱신기가 사본을 다시
    모르게 되면 이 test 가 먼저 실패한다.
    """
    from _repo_sandbox import repo_sandbox

    marker_re = re.compile(r"^(<!--\s*standard-ai-workflow-kit:[^>]*-->\n\n?)")
    with repo_sandbox(SOURCE_ROOT.parent) as sandbox:
        src = sandbox / "workflow-source"
        mirror = sandbox / "ai-workflow" / "core" / "global_workflow_standard.md"
        canonical = src / "core" / "global_workflow_standard.md"
        assert mirror.exists() and canonical.exists(), "배포 사본/정본 fixture 부재"

        # 되주입: 사본의 '최종 수정일' 을 낡은 값으로 되돌린다.
        drifted = re.sub(
            r"(^-\s+최종\s*수정일\s*:\s*)(\S+)",
            r"\g<1>1999-01-01",
            mirror.read_text(encoding="utf-8"),
            count=1,
            flags=re.M,
        )
        mirror.write_text(drifted, encoding="utf-8")
        assert "1999-01-01" in mirror.read_text(encoding="utf-8"), "되주입이 적용되지 않았다"

        proc = subprocess.run(
            [sys.executable, str(src / "workflow_kit" / "tools" / "release_pipeline.py"),
             "doc-headers-update", "--scope=core", "--apply", "--json"],
            capture_output=True, text=True, timeout=60, cwd=str(sandbox),
        )
        assert proc.returncode == 0, f"exit {proc.returncode}: {proc.stderr}"

        after = mirror.read_text(encoding="utf-8")
        assert "1999-01-01" not in after, "배포 사본이 갱신되지 않았다 (갱신기가 사본을 모른다)"
        stripped = marker_re.sub("", after)
        assert stripped == canonical.read_text(encoding="utf-8"), (
            "배포 사본이 정본과 byte 동일이 아니다"
        )


def test_note_draft_dry_run() -> None:
    """note-draft dry-run: output_path + commits count."""
    proc = subprocess.run(
        [sys.executable, str(TOOL), "note-draft",
         "--from=v0.7.4-beta", "--to=0.7.9", "--dry-run"],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, f"exit {proc.returncode}: {proc.stderr}"
    out = re.search(r"output_path:\s*([^\s]+)", proc.stdout)
    assert out is not None
    assert out.group(1) == "releases/Beta-v0.7.9.md"
    commits_m = re.search(r"commits:\s*(\d+)", proc.stdout)
    assert commits_m is not None
    assert int(commits_m.group(1)) > 0


# --- Test 6: parse_version ---


def test_parse_version_formats() -> None:
    """parse_version 이 'X.Y.Z' / 'X.Y.Z-suffix' 모두 정합."""
    mod = _import_tool()
    assert mod.parse_version("0.7.8") == (0, 7, 8)
    assert mod.parse_version("0.7.8-beta") == (0, 7, 8)
    assert mod.parse_version("1.0.0") == (1, 0, 0)
    # invalid format
    try:
        mod.parse_version("invalid")
        assert False, "should have raised"
    except ValueError:
        pass


# --- Test 7: bump_version logic ---


def test_bump_version_logic() -> None:
    """bump_version 의 major / minor / patch / to 분기."""
    mod = _import_tool()
    assert mod.bump_version("0.7.8", patch=True) == "0.7.9"
    assert mod.bump_version("0.7.8", minor=True) == "0.8.0"
    assert mod.bump_version("0.7.8", major=True) == "1.0.0"
    assert mod.bump_version("0.7.8", to="2.0.0") == "2.0.0"
    # default = patch
    assert mod.bump_version("0.7.8") == "0.7.9"


# --- Test 8: main CLI subcommand help ---


def test_cli_subcommand_help() -> None:
    """main --help + 각 subcommand --help 정상."""
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 0
    assert "validate" in proc.stdout
    assert "version-bump" in proc.stdout
    assert "note-draft" in proc.stdout


# --- 메인 실행 ---


def main() -> int:
    test_funcs = [
        test_validate_json_output,
        test_version_bump_patch_dry_run,
        test_version_bump_to_explicit,
        test_version_bump_apply_in_sandbox,
        test_doc_headers_update_syncs_distributed_core,
        test_note_draft_dry_run,
        test_parse_version_formats,
        test_bump_version_logic,
        test_cli_subcommand_help,
    ]

    passed = 0
    failed = 0
    failures: list[tuple[str, str]] = []
    for func in test_funcs:
        try:
            func()
            print(f"  PASS  {func.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {func.__name__}: {e}")
            failed += 1
            failures.append((func.__name__, str(e)))
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {func.__name__}: {type(e).__name__}: {e}")
            failed += 1
            failures.append((func.__name__, f"{type(e).__name__}: {e}"))

    print()
    if failed == 0:
        print(f"All {passed} tests passed.")
        return 0
    print(f"{failed}/{passed + failed} tests failed:")
    for name, err in failures:
        print(f"  - {name}: {err}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
