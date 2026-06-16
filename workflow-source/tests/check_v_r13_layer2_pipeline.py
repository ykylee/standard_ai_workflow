"""workflow_kit.v_r13_layer2_pipeline test (v0.7.49+).

Test list:
1. test_run_layer2_pipeline_no_range_v0_7_49: URL without ?range returns short-circuit result
2. test_run_layer2_pipeline_with_range_v0_7_49: URL with ?range runs full pipeline
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


# Pre-import dependencies
_diff_integration = _import_module("v_r13_commit_diff_integration", WORKFLOW_KIT_DIR / "v_r13_commit_diff_integration.py")
_pipeline = _import_module("v_r13_layer2_pipeline", WORKFLOW_KIT_DIR / "v_r13_layer2_pipeline.py")


def test_run_layer2_pipeline_no_range_v0_7_49() -> None:
    """run_layer2_pipeline with no ?range returns short-circuit result."""
    result = _pipeline.run_layer2_pipeline("https://github.com/foo/bar/blob/main/spec.md")
    assert result.has_range is False
    assert result.commit_count == 0
    assert result.vendor == "github"
    assert "no ?range=A..B" in result.summary or "no ?range" in result.summary.lower()


def test_run_layer2_pipeline_with_range_v0_7_49() -> None:
    """run_layer2_pipeline with ?range runs full pipeline."""
    fake_data = b'{"commits": [{"sha": "abc1234", "commit": {"message": "fix bug"}}, {"sha": "def5678", "commit": {"message": "add feature"}}]}'
    class FakeResp:
        def __init__(self):
            self.status = 200
        def read(self):
            return fake_data
    def fake_get(url, **kwargs):
        return FakeResp()
    result = _pipeline.run_layer2_pipeline(
        url="https://github.com/foo/bar/blob/main/spec.md?range=v1.0..v1.1",
        requests_get=fake_get,
    )
    assert result.has_range is True
    assert result.range_a == "v1.0"
    assert result.range_b == "v1.1"
    assert result.commit_count == 2
    assert result.vendor == "github"
    assert "v1.0..v1.1" in result.summary
    assert "2 commits" in result.summary


def main() -> int:
    test_funcs = [
        test_run_layer2_pipeline_no_range_v0_7_49,
        test_run_layer2_pipeline_with_range_v0_7_49,
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
