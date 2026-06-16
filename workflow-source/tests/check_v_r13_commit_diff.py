"""workflow_kit.v_r13_commit_diff test (v0.7.47+).

Test list:
1. test_check_url_semantic_commit_diff_github_ok_v0_7_47: GitHub compare API returns commits
2. test_check_url_semantic_commit_diff_dispatch_github_v0_7_47: dispatch routes GitHub URL to github helper
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
COMMIT_DIFF = SOURCE_ROOT / "workflow_kit" / "v_r13_commit_diff.py"


def _import_module():
    spec = importlib.util.spec_from_file_location("v_r13_commit_diff", str(COMMIT_DIFF))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["v_r13_commit_diff"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_check_url_semantic_commit_diff_github_ok_v0_7_47() -> None:
    """GitHub compare API returns commit list (mocked)."""
    mod = _import_module()
    fake_data = b'{"commits": [{"sha": "abc1234", "commit": {"message": "fix bug"}}, {"sha": "def5678", "commit": {"message": "add feature"}}]}'
    class FakeResp:
        def __init__(self):
            self.status = 200
        def read(self):
            return fake_data
    captured_url = []
    def fake_get_capture(url, **kwargs):
        captured_url.append(url)
        return FakeResp()
    commits = mod.check_url_semantic_commit_diff_github(
        org="foo", repo="bar", range_a="v1.0", range_b="v1.1",
        requests_get=fake_get_capture,
    )
    assert len(commits) == 2, f"expected 2 commits, got {len(commits)}: {commits}"
    assert "compare/v1.0...v1.1" in captured_url[0], f"compare URL pattern expected: {captured_url[0]}"


def test_check_url_semantic_commit_diff_dispatch_github_v0_7_47() -> None:
    """Dispatch routes GitHub URL to GitHub helper (mocked)."""
    mod = _import_module()
    fake_data = b'{"commits": [{"sha": "sha1"}]}'
    class FakeResp:
        def __init__(self):
            self.status = 200
        def read(self):
            return fake_data
    captured_url = []
    def fake_get_capture(url, **kwargs):
        captured_url.append(url)
        return FakeResp()
    commits = mod.check_url_semantic_commit_diff_dispatch(
        url="https://github.com/foo/bar/blob/main/spec.md",
        range_a="v1.0", range_b="v1.1",
        requests_get=fake_get_capture,
    )
    assert len(commits) == 1, f"expected 1 commit, got {len(commits)}: {commits}"
    assert "api.github.com" in captured_url[0], f"expected GitHub API URL: {captured_url[0]}"


def main() -> int:
    test_funcs = [
        test_check_url_semantic_commit_diff_github_ok_v0_7_47,
        test_check_url_semantic_commit_diff_dispatch_github_v0_7_47,
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
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
