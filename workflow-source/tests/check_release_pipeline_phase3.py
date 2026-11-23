"""tools/release_pipeline.py Phase 3 subcommand (dist) smoke test.

v0.7.11: dist subcommand (`python3 -m build` wheel + sdist 자동 빌드).
8 test PASS 기준.

Test list:
1. test_dist_dry_run_no_build_module: build module 부재 시 graceful error + exit 1
2. test_dist_dry_run_with_build_module: build module 가용 시 command plan 출력
3. test_dist_apply_with_build_module: build module 가용 + apply → wheel + sdist glob
4. test_dist_skip_existing: --skip-existing + 기존 dist 파일 존재 시 mode=skip
5. test_build_command_sdist_wheel_only: --sdist-only / --wheel-only flag 반영
6. test_expected_dist_pattern_pep440: PEP 440 normalize (0.7.10-beta → 0.7.10)
7. test_dist_subcommand_help: main --help + 7 subcommand 노출
8. test_dist_skip_existing_argparse: --skip-existing argparse error 없음
"""

from __future__ import annotations

#: 의도적 전역 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES_ALL_REASON = (
    "dist 서브커맨드가 빌드 전 저장소 정합을 훑는다 — meta-watch 실측 (2026-08-29) 접근 2076건 · "
    "최상위 30개 항목 전부: diff 로 좁혀지지 않는다"
)

import importlib.util
import argparse
import json
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _repo_sandbox import repo_sandbox  # noqa: E402

# v1.1.7(TASK-019): 아래 경로들은 `main()` 이 **저장소 사본** 으로 갈아끼운다.
# `dist --apply` 는 실제 빌드라, 원본에서 돌리면 `standard_ai_workflow-<ver>/`
# 빌드 디렉터리와 `dist/` 산출물이 저장소 안에 생긴다.
SOURCE_ROOT = Path(__file__).resolve().parents[1]
TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline.py"

def _import_tool():
    """release_pipeline.py 를 importlib 로 로드."""
    spec = importlib.util.spec_from_file_location("release_pipeline", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _has_build_module() -> bool:
    """`build` module 가용 여부."""
    try:
        import build  # type: ignore[import-not-found]  # noqa: F401

        return True
    except ImportError:
        return False


# --- Test 1: dist --dry-run (build module 부재 시 graceful error) ---


def test_dist_dry_run_no_build_module() -> None:
    """dist --dry-run — build module 부재 시 graceful error + exit 1.

    이 환경 (system python, build module 부재) 에서 실행 시 exit 1 + error + hint 검증.
    build module 가용 환경에서는 skip (test 2 가 검증).
    """
    if _has_build_module():
        return

    proc = subprocess.run(
        [sys.executable, str(TOOL), "dist", "--dry-run", "--json"],
        capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace"
    )
    assert proc.returncode == 1, f"expected exit 1, got {proc.returncode}: {proc.stderr}"
    out = json.loads(proc.stdout)
    assert "error" in out
    assert "build module not installed" in out["error"]
    assert out["build_module"]["available"] is False
    assert "pip install build" in out["build_module"]["hint"]


# --- Test 2: dist --dry-run (build module 가용 시 command plan) ---


def test_dist_dry_run_with_build_module() -> None:
    """dist --dry-run — build module 가용 시 command + version + expected_pattern 출력.

    build module 부재 환경에서는 skip (이 환경 test 1 이 graceful error 검증).
    """
    if not _has_build_module():
        return

    proc = subprocess.run(
        [sys.executable, str(TOOL), "dist", "--dry-run", "--json"],
        capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace"
    )
    assert proc.returncode == 0, f"expected exit 0, got {proc.returncode}: {proc.stderr}"
    out = json.loads(proc.stdout)
    assert out["mode"] == "dry-run"
    assert out["build_module"]["available"] is True
    assert "version" in out
    assert "command" in out
    assert "expected_pattern" in out
    assert out["expected_pattern"].startswith("standard_ai_workflow-")


# --- Test 3: dist --apply (build module 가용 시 wheel + sdist glob) ---


def test_dist_apply_with_build_module() -> None:
    """dist --apply — build module 가용 + apply → wheel + sdist glob 결과 report.

    build module 부재 시 skip (apply 불가). 가용 시에만 dist/ 의 wheel + sdist 검증.
    """
    if not _has_build_module():
        return

    proc = subprocess.run(
        [sys.executable, str(TOOL), "dist", "--apply", "--timeout=120", "--json"],
        capture_output=True, text=True, timeout=180,
        cwd=str(SOURCE_ROOT), encoding="utf-8", errors="replace"
    )
    assert proc.returncode == 0, f"expected exit 0, got {proc.returncode}: {proc.stderr}"
    out = json.loads(proc.stdout)
    assert out["mode"] == "apply"
    assert out["ok"] is True
    assert "built" in out
    built = out["built"]
    assert any(f.endswith(".whl") for f in built), f"no .whl in built: {built}"
    assert any(f.endswith(".tar.gz") for f in built), f"no .tar.gz in built: {built}"


# --- Test 4: dist --skip-existing (build module 가용 시 기존 파일 skip) ---


def test_dist_skip_existing() -> None:
    """dist --skip-existing + dist/ 의 current-version 파일 존재 시 mode=skip.

    build module 부재 시 skip. 가용 시 mode=skip 또는 mode=dry-run (기존 파일 없으면).
    """
    if not _has_build_module():
        return

    proc = subprocess.run(
        [sys.executable, str(TOOL), "dist", "--skip-existing", "--dry-run", "--json"],
        capture_output=True, text=True, timeout=30,
        cwd=str(SOURCE_ROOT), encoding="utf-8", errors="replace"
    )
    assert proc.returncode == 0
    out = json.loads(proc.stdout)
    # mode 는 skip 또는 dry-run (기존 파일이 있는 경우 skip, 없으면 dry-run)
    assert out["mode"] in ("skip", "dry-run")
    if out["mode"] == "skip":
        assert out["skipped"] is True
        assert "existing" in out
        assert all(f.startswith("standard_ai_workflow-") for f in out["existing"])


# --- Test 5: _build_command (sdist-only / wheel-only) ---


def test_build_command_sdist_wheel_only() -> None:
    """_build_command 가 --sdist-only / --wheel-only flag 반영."""
    mod = _import_tool()
    out_dir = Path("/tmp/dist_test")

    cmd_default = mod._build_command(out_dir)
    assert "--sdist" not in cmd_default
    assert "--wheel" not in cmd_default
    assert "--outdir" in cmd_default
    assert str(out_dir) in cmd_default

    cmd_sdist = mod._build_command(out_dir, sdist_only=True)
    assert "--sdist" in cmd_sdist
    assert "--wheel" not in cmd_sdist

    cmd_wheel = mod._build_command(out_dir, wheel_only=True)
    assert "--wheel" in cmd_wheel
    assert "--sdist" not in cmd_wheel


# --- Test 6: _expected_dist_pattern (PEP 440 normalize) ---


def test_expected_dist_pattern_pep440() -> None:
    """_expected_dist_pattern 가 PEP 440 suffix 처리.

    '0.7.10' / '0.7.10-beta' 모두 '0.7.10' (split('-')[0]) 으로 normalize.
    """
    mod = _import_tool()
    assert mod._expected_dist_pattern("0.7.10") == "0.7.10"
    assert mod._expected_dist_pattern("0.7.10-beta") == "0.7.10"
    assert mod._expected_dist_pattern("1.0.0-rc1") == "1.0.0"


# --- Test 7: main --help (dist subcommand 노출) ---


def test_dist_subcommand_help() -> None:
    """main --help + 7 subcommand (validate / version-bump / note-draft / release / verify / rollback / dist) 노출."""
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--help"],
        capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace"
    )
    assert proc.returncode == 0, f"expected exit 0, got {proc.returncode}: {proc.stderr}"
    for cmd in ("validate", "version-bump", "note-draft", "release", "verify", "rollback", "dist"):
        assert cmd in proc.stdout, f"missing subcommand {cmd!r} in help"


# --- Test 8: dist --skip-existing argparse 검증 ---


def test_dist_skip_existing_argparse() -> None:
    """dist --skip-existing 가 argparse error 없이 받아들여짐."""
    proc = subprocess.run(
        [sys.executable, str(TOOL), "dist", "--skip-existing", "--dry-run", "--json"],
        capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace"
    )
    # build module 부재 시 exit 1 이지만 argparse error 는 없어야 함
    assert "unrecognized arguments" not in proc.stderr
    assert "unrecognized arguments" not in proc.stdout
    # 정상 실행 결과 (성공 또는 build module 부재 error)
    out = json.loads(proc.stdout)
    assert "mode" in out


def test_go_release_asset_scope_and_missing_gate() -> None:
    mod = _import_tool()
    with tempfile.TemporaryDirectory() as temp_dir:
        go_dir = Path(temp_dir)
        assert mod.planned_go_release_assets(go_dir, "2.1.0") == []
        planned = mod.planned_go_release_assets(go_dir, "3.0.0")
        assert len(planned) == 7
        assert planned[-1].name == "SHA256SUMS"
        try:
            mod.go_release_assets(go_dir, "3.0.0")
        except FileNotFoundError as exc:
            assert "release-pipeline dist --apply" in str(exc)
        else:
            raise AssertionError("3.x release must reject missing Go assets")


def test_dist_3x_dry_run_includes_go_asset_plan() -> None:
    from unittest.mock import patch

    mod = _import_tool()
    args = argparse.Namespace(
        dry_run=True, timeout=10, sdist_only=False, wheel_only=False, skip_existing=False,
    )
    with patch.object(mod, "read_version", return_value="3.0.0"), patch.object(
        mod, "_check_build_module", return_value={"available": True, "version": "test"}
    ):
        result = mod.cmd_dist(args)
    assert result["ok"] is True
    assert len(result["planned_go_assets"]) == 7
    assert result["go_assets"] == result["planned_go_assets"]


def test_go_release_asset_build_writes_sums() -> None:
    """Go build helper emits six versioned files and checksums; use fake go process."""
    from unittest.mock import patch

    mod = _import_tool()
    spec = importlib.util.spec_from_file_location(
        "release_pipeline_go", SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline_go.py"
    )
    assert spec and spec.loader
    go_helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(go_helper)

    with tempfile.TemporaryDirectory() as temp_dir:
        out_dir = Path(temp_dir)

        def fake_run(command, **_kwargs):
            output = Path(command[command.index("-o") + 1])
            output.write_bytes(b"test binary:" + output.name.encode("utf-8"))
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch.object(go_helper.subprocess, "run", side_effect=fake_run):
            built = go_helper.build_go_release_assets(out_dir, "3.0.0")
        assets = go_helper.go_release_assets(out_dir, "3.0.0")
        assert len(built["built"]) == 6
        assert len(assets) == 7
        rows = (out_dir / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
        assert len(rows) == 6
        for row, binary in zip(rows, assets[:-1]):
            digest, name = row.split("  ", 1)
            assert name == binary.name
            assert digest == hashlib.sha256(binary.read_bytes()).hexdigest()
        (out_dir / rows[0].split("  ", 1)[1]).write_bytes(b"tampered")
        try:
            go_helper.go_release_assets(out_dir, "3.0.0")
        except ValueError as exc:
            assert "SHA256SUMS" in str(exc)
        else:
            raise AssertionError("mismatched Go checksum must be rejected")


# --- 메인 실행 ---


def main() -> int:
    """저장소 **사본** 에서 돌린다 — 실제 빌드 산출물이 원본에 남지 않게 (TASK-019)."""
    global SOURCE_ROOT, TOOL
    origin = SOURCE_ROOT
    with repo_sandbox(origin.parent) as sandbox:
        SOURCE_ROOT = sandbox / "workflow-source"
        TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline.py"
        rc = _run_cases()

    leaked = sorted(q.name for q in origin.glob("standard_ai_workflow-*") if q.is_dir())
    assert not leaked, f"원본에 빌드 디렉터리가 남았다: {leaked}"
    return rc


def _run_cases() -> int:
    test_funcs = [
        test_dist_dry_run_no_build_module,
        test_dist_dry_run_with_build_module,
        test_dist_apply_with_build_module,
        test_dist_skip_existing,
        test_build_command_sdist_wheel_only,
        test_expected_dist_pattern_pep440,
        test_dist_subcommand_help,
        test_dist_skip_existing_argparse,
        test_go_release_asset_scope_and_missing_gate,
        test_dist_3x_dry_run_includes_go_asset_plan,
        test_go_release_asset_build_writes_sums,
    ]

    failed: list[str] = []
    for fn in test_funcs:
        name = fn.__name__
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed.append(name)

    total = len(test_funcs)
    passed = total - len(failed)
    print(f"\n{passed}/{total} tests passed.")
    if failed:
        print(f"\n{len(failed)} tests failed:")
        for name in failed:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
