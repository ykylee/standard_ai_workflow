"""workflow_kit.v_r13_commit_diff test (consolidated v0.7.52).

Tests the raw cross-vendor commit diff API + the integration helpers
(parse_range_from_url, check_url_semantic_with_commit_diff, format_commit_diff_summary,
PipelineResult, run_layer2_pipeline).
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
    fake = b'{"commits": [{"sha": "abc1234", "commit": {"message": "fix bug"}}, {"sha": "def5678", "commit": {"message": "add feature"}}]}'

    class FakeResp:
        status = 200
        def read(self): return fake

    captured = []
    def fake_get(url, **kwargs):
        captured.append(url)
        return FakeResp()
    commits = mod.check_url_semantic_commit_diff_github(
        org="foo", repo="bar", range_a="v1.0", range_b="v1.1",
        requests_get=fake_get,
    )
    assert len(commits) == 2
    assert "compare/v1.0...v1.1" in captured[0]


def test_check_url_semantic_commit_diff_dispatch_github_v0_7_47() -> None:
    """Dispatch routes GitHub URL to GitHub helper."""
    mod = _import_module()
    fake = b'{"commits": [{"sha": "sha1"}]}'

    class FakeResp:
        status = 200
        def read(self): return fake

    captured = []
    def fake_get(url, **kwargs):
        captured.append(url)
        return FakeResp()
    commits = mod.check_url_semantic_commit_diff_dispatch(
        url="https://github.com/foo/bar/blob/main/spec.md",
        range_a="v1.0", range_b="v1.1",
        requests_get=fake_get,
    )
    assert len(commits) == 1
    assert "api.github.com" in captured[0]


def test_parse_range_from_url_v0_7_52() -> None:
    """parse_range_from_url extracts ?range=A..B."""
    mod = _import_module()
    assert mod.parse_range_from_url("https://github.com/foo/bar?range=v1.0..v1.1") == ("v1.0", "v1.1")
    assert mod.parse_range_from_url("https://github.com/foo/bar") is None


def test_check_url_semantic_with_commit_diff_no_range_v0_7_52() -> None:
    """No ?range returns short-circuit result."""
    mod = _import_module()
    result = mod.check_url_semantic_with_commit_diff("https://github.com/foo/bar/blob/main/spec.md")
    assert result["has_range"] is False
    assert result["vendor"] == "github"
    assert result["commit_count"] == 0


def test_check_url_semantic_with_commit_diff_with_range_v0_7_52() -> None:
    """With ?range returns full result."""
    mod = _import_module()
    fake = b'{"commits": [{"sha": "abc1234", "commit": {"message": "fix"}}]}'

    class FakeResp:
        status = 200
        def read(self): return fake

    def fake_get(url, **kwargs):
        return FakeResp()
    result = mod.check_url_semantic_with_commit_diff(
        url="https://github.com/foo/bar/blob/main/spec.md?range=v1.0..v1.1",
        requests_get=fake_get,
    )
    assert result["has_range"] is True
    assert result["commit_count"] == 1
    assert result["range_a"] == "v1.0"
    assert result["range_b"] == "v1.1"


def test_run_layer2_pipeline_v0_7_52() -> None:
    """run_layer2_pipeline returns PipelineResult."""
    mod = _import_module()
    result = mod.run_layer2_pipeline("https://github.com/foo/bar/blob/main/spec.md")
    assert mod.PipelineResult.__name__ == "PipelineResult"
    assert result.has_range is False
    assert result.vendor == "github"
    assert "no ?range" in result.summary.lower()


def main() -> int:
    test_funcs = [
        test_check_url_semantic_commit_diff_github_ok_v0_7_47,
        test_check_url_semantic_commit_diff_dispatch_github_v0_7_47,
        test_parse_range_from_url_v0_7_52,
        test_check_url_semantic_with_commit_diff_no_range_v0_7_52,
        test_check_url_semantic_with_commit_diff_with_range_v0_7_52,
        test_run_layer2_pipeline_v0_7_52,
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
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
