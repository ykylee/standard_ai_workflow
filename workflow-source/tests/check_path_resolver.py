"""workflow_kit.path_resolver test (v0.7.60, 5 module audit 4차).

ADR-008 (in-repo path → canonical GitHub URL) + ADR-018 (commit/ref pinned URL)
coverage.

Test list (12):
1-2.  Path safety: safe/unsafe path
3-4.  Origin URL normalize: SSH / HTTPS form
5-6.  detect_origin: CI env / git config
7-8.  detect_default_branch: symbolic-ref / fallback
9-10. resolve: URL pass-through / path resolve
11-12. resolve_pinned: commit / ref
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
PATH_RESOLVER = SOURCE_ROOT / "workflow_kit" / "path_resolver.py"


def _import_path_resolver():
    spec = importlib.util.spec_from_file_location(
        "workflow_kit.path_resolver", str(PATH_RESOLVER)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["workflow_kit.path_resolver"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Test 1-2: Path safety
# ---------------------------------------------------------------------------
def test_path_safe_accepts_v0_7_60() -> None:
    """_is_path_safe accepts valid in-repo path (v0.7.60+)."""
    mod = _import_path_resolver()
    assert mod._is_path_safe("workflow-source/workflow_kit/README.md") is True
    assert mod._is_path_safe("README.md") is True
    assert mod._is_path_safe("a/b/c.md") is True


def test_path_safe_rejects_unsafe_v0_7_60() -> None:
    """_is_path_safe rejects path traversal / absolute paths (v0.7.60+)."""
    mod = _import_path_resolver()
    assert mod._is_path_safe("../etc/passwd") is False
    assert mod._is_path_safe("/etc/passwd") is False
    assert mod._is_path_safe("a/../b.md") is False
    assert mod._is_path_safe("") is False


# ---------------------------------------------------------------------------
# Test 3-4: Origin URL normalize
# ---------------------------------------------------------------------------
def test_normalize_origin_ssh_to_https_v0_7_60() -> None:
    """_normalize_origin_url converts git@github.com:foo/bar.git → https://github.com/foo/bar (v0.7.60+)."""
    mod = _import_path_resolver()
    assert mod._normalize_origin_url("git@github.com:owner/repo.git") == "https://github.com/owner/repo"
    assert mod._normalize_origin_url("git@github.com:owner/repo") == "https://github.com/owner/repo"


def test_normalize_origin_https_passthrough_v0_7_60() -> None:
    """_normalize_origin_url strips .git suffix from HTTPS form (v0.7.60+)."""
    mod = _import_path_resolver()
    assert mod._normalize_origin_url("https://github.com/owner/repo.git") == "https://github.com/owner/repo"
    assert mod._normalize_origin_url("https://github.com/owner/repo") == "https://github.com/owner/repo"
    assert mod._normalize_origin_url("") is None
    assert mod._normalize_origin_url("not-a-url") is None


# ---------------------------------------------------------------------------
# Test 5-6: detect_origin_url
# ---------------------------------------------------------------------------
def test_detect_origin_ci_env_v0_7_60() -> None:
    """_detect_origin_url prefers GITHUB_SERVER_URL + GITHUB_REPOSITORY (v0.7.60+)."""
    mod = _import_path_resolver()
    old_server = os.environ.get("GITHUB_SERVER_URL")
    old_repo = os.environ.get("GITHUB_REPOSITORY")
    try:
        os.environ["GITHUB_SERVER_URL"] = "https://github.com"
        os.environ["GITHUB_REPOSITORY"] = "owner/repo"
        assert mod._detect_origin_url(Path("/tmp")) == "https://github.com/owner/repo"
    finally:
        if old_server is None:
            os.environ.pop("GITHUB_SERVER_URL", None)
        else:
            os.environ["GITHUB_SERVER_URL"] = old_server
        if old_repo is None:
            os.environ.pop("GITHUB_REPOSITORY", None)
        else:
            os.environ["GITHUB_REPOSITORY"] = old_repo


def test_detect_origin_git_config_v0_7_60() -> None:
    """_detect_origin_url falls back to `git config --get remote.origin.url` (v0.7.60+)."""
    mod = _import_path_resolver()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # init git + set origin
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/owner/repo.git"],
            cwd=tmp_path, check=True,
        )
        # clear CI env
        old_server = os.environ.pop("GITHUB_SERVER_URL", None)
        old_repo = os.environ.pop("GITHUB_REPOSITORY", None)
        try:
            result = mod._detect_origin_url(tmp_path)
            assert result == "https://github.com/owner/repo"
        finally:
            if old_server:
                os.environ["GITHUB_SERVER_URL"] = old_server
            if old_repo:
                os.environ["GITHUB_REPOSITORY"] = old_repo


# ---------------------------------------------------------------------------
# Test 7-8: detect_default_branch
# ---------------------------------------------------------------------------
def test_detect_branch_local_fallback_v0_7_60() -> None:
    """_detect_default_branch returns current branch via `git branch --show-current` when no symbolic-ref (v0.7.60+)."""
    mod = _import_path_resolver()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "checkout", "-q", "-b", "feature-x"], cwd=tmp_path, check=True)
        # Symbolic-ref will fail (no fetch), so falls back to --show-current
        result = mod._detect_default_branch(tmp_path)
        assert result == "feature-x"


def test_detect_branch_fallback_main_v0_7_60() -> None:
    """_detect_default_branch returns 'main' as deepest fallback (v0.7.60+)."""
    mod = _import_path_resolver()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # No git init — all 3 layer fallback fail
        result = mod._detect_default_branch(tmp_path)
        assert result == "main"


# ---------------------------------------------------------------------------
# Test 9-10: resolve_in_repo_path_to_url
# ---------------------------------------------------------------------------
def test_resolve_url_passthrough_v0_7_60() -> None:
    """resolve_in_repo_path_to_url returns URL form unchanged (v0.7.60+)."""
    mod = _import_path_resolver()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        result = mod.resolve_in_repo_path_to_url(
            "https://github.com/owner/repo/blob/main/README.md", tmp_path
        )
        assert result == "https://github.com/owner/repo/blob/main/README.md"


def test_resolve_in_repo_path_v0_7_60() -> None:
    """resolve_in_repo_path_to_url builds canonical GitHub blob URL (v0.7.60+)."""
    mod = _import_path_resolver()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "git@github.com:owner/repo.git"],
            cwd=tmp_path, check=True,
        )
        actual_branch = mod._detect_default_branch(tmp_path)
        result = mod.resolve_in_repo_path_to_url(
            "workflow-source/workflow_kit/README.md", tmp_path
        )
        expected = f"https://github.com/owner/repo/blob/{actual_branch}/workflow-source/workflow_kit/README.md"
        assert result == expected, f"expected {expected}, got {result}"


def test_resolve_pinned_commit_v0_7_60() -> None:
    """resolve_in_repo_path_to_url_pinned uses commit SHA (immutable) (v0.7.60+, ADR-018)."""
    mod = _import_path_resolver()

def test_resolve_pinned_ref_v0_7_60() -> None:
    """resolve_in_repo_path_to_url_pinned uses ref (branch/tag) (v0.7.60+, ADR-018)."""
    mod = _import_path_resolver()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/owner/repo.git"],
            cwd=tmp_path, check=True,
        )
        result = mod.resolve_in_repo_path_to_url_pinned(
            "README.md", tmp_path, ref="v0.7.60"
        )
        assert result == "https://github.com/owner/repo/blob/v0.7.60/README.md"
        # Bad SHA format returns None
        bad = mod.resolve_in_repo_path_to_url_pinned(
            "README.md", tmp_path, commit_sha="not-hex!!"
        )
        assert bad is None


def main() -> int:
    test_funcs = [
        test_path_safe_accepts_v0_7_60,
        test_path_safe_rejects_unsafe_v0_7_60,
        test_normalize_origin_ssh_to_https_v0_7_60,
        test_normalize_origin_https_passthrough_v0_7_60,
        test_detect_origin_ci_env_v0_7_60,
        test_detect_origin_git_config_v0_7_60,
        test_detect_branch_local_fallback_v0_7_60,
        test_detect_branch_fallback_main_v0_7_60,
        test_resolve_url_passthrough_v0_7_60,
        test_resolve_in_repo_path_v0_7_60,
        test_resolve_pinned_commit_v0_7_60,
        test_resolve_pinned_ref_v0_7_60,
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
    print(f"\n{len(test_funcs) - len(failed)}/{len(test_funcs)} tests passed.")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
