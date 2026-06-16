"""workflow_kit.v_r13_commit_diff_integration test (v0.7.48+).

Test list:
1. test_parse_range_from_url_v0_7_48: parse ?range=A..B from V-R13 URL
2. test_check_url_semantic_with_commit_diff_github_v0_7_48: integrate V-R13 parse + commit diff
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_KIT_DIR = SOURCE_ROOT / "workflow_kit"

workflow_kit_pkg = types.ModuleType("workflow_kit")
workflow_kit_pkg.__path__ = [str(WORKFLOW_KIT_DIR)]
sys.modules["workflow_kit"] = workflow_kit_pkg


def _import_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(f"workflow_kit.{name}", str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"workflow_kit.{name}"] = mod
    spec.loader.exec_module(mod)
    return mod


_commit_diff = _import_module("v_r13_commit_diff", WORKFLOW_KIT_DIR / "v_r13_commit_diff.py")
_integration = _import_module(
    "v_r13_commit_diff_integration", WORKFLOW_KIT_DIR / "v_r13_commit_diff_integration.py"
)


def test_parse_range_from_url_v0_7_48() -> None:
    """parse_range_from_url returns (range_a, range_b) or None."""
    # With range
    result = _integration.parse_range_from_url(
        "https://github.com/foo/bar/blob/main/spec.md?range=v1.0..v1.1"
    )
    assert result == ("v1.0", "v1.1"), f"unexpected: {result}"
    # Without range
    result2 = _integration.parse_range_from_url("https://github.com/foo/bar/blob/main/spec.md")
    assert result2 is None, f"expected None, got: {result2}"


def test_check_url_semantic_with_commit_diff_github_v0_7_48() -> None:
    """check_url_semantic_with_commit_diff returns commit diff for GitHub URL."""
    fake_data = b'{"commits": [{"sha": "abc1234", "commit": {"message": "fix bug"}}, {"sha": "def5678", "commit": {"message": "add feature"}}]}'
    class FakeResp:
        def __init__(self):
            self.status = 200
        def read(self):
            return fake_data
    def fake_get(url, **kwargs):
        return FakeResp()
    result = _integration.check_url_semantic_with_commit_diff(
        url="https://github.com/foo/bar/blob/main/spec.md?range=v1.0..v1.1",
        requests_get=fake_get,
    )
    assert result["has_range"] is True
    assert result["range_a"] == "v1.0"
    assert result["range_b"] == "v1.1"
    assert result["commit_count"] == 2, f"expected 2 commits, got: {result}"
    assert result["vendor"] == "github"


def main() -> int:
    test_funcs = [
        test_parse_range_from_url_v0_7_48,
        test_check_url_semantic_with_commit_diff_github_v0_7_48,
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
