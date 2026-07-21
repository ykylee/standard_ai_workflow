#!/usr/bin/env python3
"""
v0.7.29: TASK-V0727-001 (post-step 2-phase + amend 통합) smoke test

Test cases:
1. test_2_phase_sync_calls — sync_release_hash + git add + git commit --amend 모두 호출
2. test_amend_integration — amend 후의 final_hash 가 rev-parse 결과와 정합
3. test_no_tbd_skip — TBD 부재 시 sync 가 *변경 0* (idempotent skip)
4. test_sync_failure_graceful — sync_release_hash fail 시 amend 호출 안 함, ok=False
5. test_amend_failure_graceful — git commit --amend fail 시 ok=False

v1.0.0 amend guard (release-pipeline-auto-amend-hazard):
6. test_dirty_tree_aborts — pre-flight dirty tree → mode=aborted, sync 호출 0
7. test_allow_dirty_override — --allow-dirty 시 dirty 여도 진행
8. test_pushed_head_refuses_amend — HEAD 가 upstream ancestor → amend 거부
9. test_add_is_scoped — `git add -A` 가 아니라 dirty path 명시 add

mock 은 *호출 순서*가 아니라 *명령 내용*으로 dispatch 한다 (call-count 취약성 제거 —
v0.7.26 의 2-step rev-parse 도입 때 이 파일이 StopIteration 으로 red 였던 원인).
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TOOL = REPO_ROOT / "workflow-source" / "tools" / "release_pipeline.py"
SOURCE_ROOT = REPO_ROOT / "workflow-source"
PYTHON = sys.executable

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

# In-process module load
import importlib.util
_spec = importlib.util.spec_from_file_location("release_pipeline", str(TOOL))
_rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rp)
cmd_version_bump = _rp.cmd_version_bump
_run_post_step_sync_hash = _rp._run_post_step_sync_hash
parse_version = _rp.parse_version


def _run_inproc(args: list[str], repo_root: Path) -> dict:
    """In-process invocation of cmd_version_bump (mock-friendly)."""
    import argparse
    # Strip "version-bump" subcommand
    if args and args[0] == "version-bump":
        args = args[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch", action="store_true")
    parser.add_argument("--minor", action="store_true")
    parser.add_argument("--major", action="store_true")
    parser.add_argument("--to", default=None)
    parser.add_argument("--no-init", action="store_true", dest="no_init")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    parser.add_argument("--apply", dest="apply", action="store_true", default=True)
    parser.add_argument("--skip-sync-hash", action="store_true", dest="skip_sync_hash")
    parser.add_argument("--allow-dirty", action="store_true", dest="allow_dirty")
    parser.add_argument("--allow-pushed-amend", action="store_true", dest="allow_pushed_amend")
    parser.add_argument("--json", action="store_true")

    import unittest.mock
    with unittest.mock.patch.object(_rp, "REPO_ROOT", repo_root):
        with unittest.mock.patch.object(_rp, "read_version", return_value="0.7.0"):
            with unittest.mock.patch.object(_rp, "read_workflow_kit_version", return_value="v0.7.0-beta"):
                with unittest.mock.patch.object(_rp, "write_version"):
                    with unittest.mock.patch.object(_rp, "write_workflow_kit_version", return_value="v0.7.0-beta"):
                        ns = parser.parse_args(args)
                        if not ns.dry_run and not ns.apply:
                            ns.apply = True
                        try:
                            return cmd_version_bump(ns)
                        except SystemExit as e:
                            return {"error": f"SystemExit: {e}"}


def _make_fake_proc(returncode: int = 0, stdout: str = "", stderr: str = ""):
    """Create a mock subprocess.CompletedProcess."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


DIRTY = " M pyproject.toml\n M workflow_kit/__init__.py\n"


def _make_router(
    *,
    sync: tuple[int, str, str] = (0, "sync ok\n", ""),
    add: tuple[int, str, str] = (0, "", ""),
    amend: tuple[int, str, str] = (0, "[main abc1234] amend\n", ""),
    preflight_status: str = "",
    staging_status: str = DIRTY,
    upstream: str | None = None,
    head_pushed: bool = False,
):
    """subprocess.run 을 *명령 내용*으로 dispatch 하는 side_effect + 호출 기록.

    Returns:
        (side_effect, calls) — calls 는 실행된 argv list 의 기록.
    """
    calls: list[list[str]] = []
    status_seen = [0]

    def _side_effect(cmd, *a, **kw):
        calls.append(list(cmd))
        joined = " ".join(str(c) for c in cmd)
        if "sync_release_hash" in joined:
            return _make_fake_proc(*sync)
        if cmd[:3] == ["git", "status", "--porcelain"]:
            status_seen[0] += 1
            out = preflight_status if status_seen[0] == 1 else staging_status
            return _make_fake_proc(0, out)
        if "--symbolic-full-name" in cmd:
            if upstream is None:
                return _make_fake_proc(128, "", "no upstream\n")
            return _make_fake_proc(0, f"{upstream}\n")
        if cmd[:2] == ["git", "merge-base"]:
            return _make_fake_proc(0 if head_pushed else 1, "", "")
        if cmd[:2] == ["git", "add"]:
            return _make_fake_proc(*add)
        if "--amend" in cmd:
            return _make_fake_proc(*amend)
        if "--short=7" in joined:
            return _make_fake_proc(0, "abc1234\n")
        if cmd[:2] == ["git", "rev-parse"]:
            return _make_fake_proc(0, "abc1234def5678901234567890123456789012ab\n")
        raise AssertionError(f"unrouted subprocess call: {cmd}")

    return _side_effect, calls


def _fake_repo(tmp: str) -> Path:
    """git init 된 최소 repo (pyproject + workflow_kit)."""
    repo_root = Path(tmp) / "fake_repo"
    (repo_root / "workflow_kit").mkdir(parents=True, exist_ok=True)
    (repo_root / "pyproject.toml").write_text(
        '[project]\nname = "test"\nversion = "0.0.0"\n', encoding="utf-8")
    (repo_root / "workflow_kit" / "__init__.py").write_text(
        '__version__ = "v0.0.0-beta"\n', encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=str(repo_root), check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(repo_root), check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(repo_root), check=True)
    subprocess.run(["git", "add", "-A"], cwd=str(repo_root), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=str(repo_root), check=True)
    return repo_root


def _ran(calls: list[list[str]], needle: str) -> bool:
    return any(needle in " ".join(str(c) for c in call) for call in calls)


# === Test 1: 2-phase sync calls ===
def test_2_phase_sync_calls() -> bool:
    """sync_release_hash + git add + git commit --amend 모두 호출."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _fake_repo(tmp)
        side_effect, calls = _make_router()
        with patch("subprocess.run", side_effect=side_effect):
            result = _run_inproc(["version-bump", "--to=0.7.29", "--apply"], repo_root=repo_root)
        if result.get("error"):
            print(f"  FAIL: tool error: {result['error']}")
            return False
        for needle in ("sync_release_hash", "git add", "--amend"):
            if not _ran(calls, needle):
                print(f"  FAIL: {needle!r} not called. Calls: {calls}")
                return False
        sync_hash_result = result.get("sync_hash_result", {})
        if not sync_hash_result.get("ok"):
            print(f"  FAIL: sync_hash_result.ok=False. Got: {sync_hash_result}")
            return False
        if sync_hash_result.get("final_hash") != "abc1234":
            print(f"  FAIL: final_hash != 'abc1234'. Got: {sync_hash_result.get('final_hash')}")
            return False
        print("  PASS: 2-phase sync (sync + add + amend + rev-parse) all called")
        return True


# === Test 2: amend integration ===
def test_amend_integration() -> bool:
    """amend 후의 final_hash 가 rev-parse (2-step full → short=7) 결과와 정합."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _fake_repo(tmp)
        side_effect, calls = _make_router()
        with patch("subprocess.run", side_effect=side_effect):
            result = _run_inproc(["version-bump", "--to=0.7.29", "--apply"], repo_root=repo_root)
        if result.get("error"):
            print(f"  FAIL: tool error: {result['error']}")
            return False
        sync_hash_result = result.get("sync_hash_result", {})
        if sync_hash_result.get("final_hash") != "abc1234":
            print(f"  FAIL: final_hash != 'abc1234'. Got: {sync_hash_result.get('final_hash')}")
            return False
        if not _ran(calls, "--short=7"):
            print(f"  FAIL: 2-step rev-parse (--short=7) not used. Calls: {calls}")
            return False
        print("  PASS: amend integration (final_hash='abc1234' via 2-step rev-parse)")
        return True


# === Test 3: no TBD skip ===
def test_no_tbd_skip() -> bool:
    """TBD 부재 (sync 변경 0) → staging 대상 0 → amend 호출 없이 ok=True."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _fake_repo(tmp)
        side_effect, calls = _make_router(
            sync=(0, "state_updated: False\nbacklog_updated: False\n", ""),
            staging_status="",  # sync 가 아무것도 안 바꿈
        )
        with patch("subprocess.run", side_effect=side_effect):
            result = _run_inproc(["version-bump", "--to=0.7.29", "--apply"], repo_root=repo_root)
        if result.get("error"):
            print(f"  FAIL: tool error: {result['error']}")
            return False
        sync_hash_result = result.get("sync_hash_result", {})
        if not sync_hash_result.get("ok"):
            print(f"  FAIL: sync_hash_result.ok=False despite no-op. Got: {sync_hash_result}")
            return False
        if _ran(calls, "--amend"):
            print(f"  FAIL: amend called despite 0 change. Calls: {calls}")
            return False
        if sync_hash_result.get("skipped") != "no changes to amend":
            print(f"  FAIL: expected skipped marker. Got: {sync_hash_result}")
            return False
        print("  PASS: no TBD → staging 0 → amend skipped (no empty-commit amend)")
        return True


# === Test 4: sync failure graceful ===
def test_sync_failure_graceful() -> bool:
    """sync_release_hash fail (returncode 1) 시 amend 호출 안 함, ok=False."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _fake_repo(tmp)
        side_effect, calls = _make_router(sync=(1, "", "sync_release_hash failed\n"))
        with patch("subprocess.run", side_effect=side_effect):
            result = _run_inproc(["version-bump", "--to=0.7.29", "--apply"], repo_root=repo_root)
        if result.get("mode") != "applied":
            print(f"  FAIL: expected mode='applied', got {result.get('mode')!r}")
            return False
        sync_hash_result = result.get("sync_hash_result", {})
        if sync_hash_result.get("ok") is not False:
            print(f"  FAIL: sync_hash_result.ok should be False. Got: {sync_hash_result}")
            return False
        if _ran(calls, "--amend") or _ran(calls, "git add"):
            print(f"  FAIL: add/amend called despite sync failure. Calls: {calls}")
            return False
        if "sync_release_hash failed" not in sync_hash_result.get("error", ""):
            print(f"  FAIL: error message missing. Got: {sync_hash_result.get('error')!r}")
            return False
        print("  PASS: sync failure → no add/amend, ok=False, graceful")
        return True


# === Test 5: amend failure graceful ===
def test_amend_failure_graceful() -> bool:
    """git commit --amend fail (returncode 1) 시 ok=False, final_hash=None."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _fake_repo(tmp)
        side_effect, calls = _make_router(amend=(1, "", "amend failed\n"))
        with patch("subprocess.run", side_effect=side_effect):
            result = _run_inproc(["version-bump", "--to=0.7.29", "--apply"], repo_root=repo_root)
        if result.get("mode") != "applied":
            print(f"  FAIL: expected mode='applied', got {result.get('mode')!r}")
            return False
        sync_hash_result = result.get("sync_hash_result", {})
        if sync_hash_result.get("ok") is not False:
            print(f"  FAIL: sync_hash_result.ok should be False. Got: {sync_hash_result}")
            return False
        if sync_hash_result.get("final_hash") is not None:
            print(f"  FAIL: final_hash should be None. Got: {sync_hash_result.get('final_hash')}")
            return False
        if "amend failed" not in sync_hash_result.get("error", ""):
            print(f"  FAIL: error message missing. Got: {sync_hash_result.get('error')!r}")
            return False
        print("  PASS: amend failure → ok=False, final_hash=None, graceful")
        return True


# === Test 6 (v1.0.0 guard): dirty tree aborts ===
def test_dirty_tree_aborts() -> bool:
    """pre-flight 에서 dirty tree 감지 → mode=aborted, sync/amend 호출 0."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _fake_repo(tmp)
        side_effect, calls = _make_router(preflight_status="?? unrelated_work.py\n")
        with patch("subprocess.run", side_effect=side_effect):
            result = _run_inproc(["version-bump", "--to=0.7.29", "--apply"], repo_root=repo_root)
        if result.get("mode") != "aborted":
            print(f"  FAIL: expected mode='aborted', got {result.get('mode')!r}")
            return False
        if "unrelated_work.py" not in result.get("dirty_paths", []):
            print(f"  FAIL: dirty_paths missing offender. Got: {result.get('dirty_paths')}")
            return False
        if _ran(calls, "sync_release_hash") or _ran(calls, "--amend"):
            print(f"  FAIL: sync/amend ran despite dirty tree. Calls: {calls}")
            return False
        print("  PASS: dirty tree → aborted before any write (amend hazard blocked)")
        return True


# === Test 7 (v1.0.0 guard): --allow-dirty override ===
def test_allow_dirty_override() -> bool:
    """--allow-dirty 시 dirty tree 여도 기존 flow 진행."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _fake_repo(tmp)
        side_effect, calls = _make_router(preflight_status="?? unrelated_work.py\n")
        with patch("subprocess.run", side_effect=side_effect):
            result = _run_inproc(
                ["version-bump", "--to=0.7.29", "--apply", "--allow-dirty"], repo_root=repo_root)
        if result.get("mode") != "applied":
            print(f"  FAIL: expected mode='applied', got {result.get('mode')!r}")
            return False
        if not _ran(calls, "--amend"):
            print(f"  FAIL: amend not called under --allow-dirty. Calls: {calls}")
            return False
        print("  PASS: --allow-dirty overrides the pre-flight guard")
        return True


# === Test 8 (v1.0.0 guard): pushed HEAD refuses amend ===
def test_pushed_head_refuses_amend() -> bool:
    """HEAD 가 upstream 의 ancestor (= 이미 push) → amend 거부, ok=False."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _fake_repo(tmp)
        side_effect, calls = _make_router(upstream="origin/main", head_pushed=True)
        with patch("subprocess.run", side_effect=side_effect):
            result = _run_inproc(["version-bump", "--to=0.7.29", "--apply"], repo_root=repo_root)
        sync_hash_result = result.get("sync_hash_result", {})
        if sync_hash_result.get("ok") is not False:
            print(f"  FAIL: ok should be False for pushed HEAD. Got: {sync_hash_result}")
            return False
        if _ran(calls, "--amend"):
            print(f"  FAIL: amend ran on a pushed HEAD. Calls: {calls}")
            return False
        if "already pushed" not in sync_hash_result.get("error", ""):
            print(f"  FAIL: error message missing. Got: {sync_hash_result.get('error')!r}")
            return False
        # override 로는 통과해야 함
        side_effect2, calls2 = _make_router(upstream="origin/main", head_pushed=True)
        with patch("subprocess.run", side_effect=side_effect2):
            result2 = _run_inproc(
                ["version-bump", "--to=0.7.29", "--apply", "--allow-pushed-amend"], repo_root=repo_root)
        if not result2.get("sync_hash_result", {}).get("ok"):
            print(f"  FAIL: --allow-pushed-amend should proceed. Got: {result2.get('sync_hash_result')}")
            return False
        print("  PASS: pushed HEAD → amend refused (--allow-pushed-amend overrides)")
        return True


# === Test 9 (v1.0.0 guard): scoped add ===
def test_add_is_scoped() -> bool:
    """`git add -A` 대신 dirty path 를 명시 add 하고 staged_paths 로 기록."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _fake_repo(tmp)
        side_effect, calls = _make_router()
        with patch("subprocess.run", side_effect=side_effect):
            result = _run_inproc(["version-bump", "--to=0.7.29", "--apply"], repo_root=repo_root)
        add_calls = [c for c in calls if c[:2] == ["git", "add"]]
        if not add_calls:
            print(f"  FAIL: no git add call. Calls: {calls}")
            return False
        add_cmd = add_calls[0]
        if "-A" in add_cmd:
            print(f"  FAIL: `git add -A` still used (amend hazard). Got: {add_cmd}")
            return False
        if "--" not in add_cmd or "pyproject.toml" not in add_cmd:
            print(f"  FAIL: add is not path-scoped. Got: {add_cmd}")
            return False
        staged = result.get("sync_hash_result", {}).get("staged_paths")
        if staged != ["pyproject.toml", "workflow_kit/__init__.py"]:
            print(f"  FAIL: staged_paths not recorded correctly. Got: {staged}")
            return False
        print("  PASS: git add is path-scoped + staged_paths recorded")
        return True


# === Main ===
def main() -> int:
    print("=" * 60)
    print("TASK-V0727-001 (2-phase post-step + amend) smoke test (v0.7.29 / v1.0.0 guard)")
    print("=" * 60)

    tests = [
        test_2_phase_sync_calls,
        test_amend_integration,
        test_no_tbd_skip,
        test_sync_failure_graceful,
        test_amend_failure_graceful,
        test_dirty_tree_aborts,
        test_allow_dirty_override,
        test_pushed_head_refuses_amend,
        test_add_is_scoped,
    ]
    passed = 0
    for test in tests:
        print(f"\n{test.__name__}:")
        if test():
            passed += 1

    print()
    print("=" * 60)
    print(f"Result: {passed}/{len(tests)} PASS")
    print("=" * 60)
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
