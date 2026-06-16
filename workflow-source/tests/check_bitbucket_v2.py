"""workflow_kit.bitbucket_v2 test (v0.7.46+).

Test list:
1. test_fetch_bitbucket_commit_history_ok_v0_7_46: 200 response returns commits
2. test_fetch_bitbucket_commit_history_error_returns_empty_v0_7_46: 404 returns []
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
BITBUCKET_V2 = SOURCE_ROOT / "workflow_kit" / "bitbucket_v2.py"


def _import_bitbucket_v2():
    spec = importlib.util.spec_from_file_location("bitbucket_v2", str(BITBUCKET_V2))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bitbucket_v2"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_fetch_bitbucket_commit_history_ok_v0_7_46() -> None:
    """fetch_bitbucket_commit_history returns commits on 200 (mocked responses)."""
    mod = _import_bitbucket_v2()
    fake_data = b'{"values": [{"hash": "abc1234", "message": "fix bug"}, {"hash": "def5678", "message": "add feature"}]}'
    class FakeResp:
        def __init__(self):
            self.status = 200
        def read(self):
            return fake_data
    captured_url = []
    def fake_get_capture(url, **kwargs):
        captured_url.append(url)
        return FakeResp()
    commits = mod.fetch_bitbucket_commit_history(
        workspace="myworkspace", repo="myrepo", requests_get=fake_get_capture
    )
    assert len(commits) == 2, f"expected 2 commits, got {len(commits)}: {commits}"
    assert commits[0]["hash"] == "abc1234", f"unexpected first commit: {commits[0]}"
    assert "pagelen=50" in captured_url[0], f"limit param should be in URL: {captured_url[0]}"


def test_fetch_bitbucket_commit_history_error_returns_empty_v0_7_46() -> None:
    """fetch_bitbucket_commit_history returns [] on 404 (silent fallback)."""
    mod = _import_bitbucket_v2()
    class FakeResp:
        def __init__(self):
            self.status = 404
    def fake_get(url, **kwargs):
        return FakeResp()
    commits = mod.fetch_bitbucket_commit_history(
        workspace="myworkspace", repo="myrepo", requests_get=fake_get
    )
    assert commits == [], f"expected [] on 404, got: {commits}"


def main() -> int:
    test_funcs = [
        test_fetch_bitbucket_commit_history_ok_v0_7_46,
        test_fetch_bitbucket_commit_history_error_returns_empty_v0_7_46,
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
