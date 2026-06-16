"""workflow_kit.v_r13_layer2_cli test (v0.7.50+).

Test list:
1. test_run_layer2_cli_no_flag_returns_1_v0_7_50: missing --layer2 flag returns 1
2. test_run_layer2_cli_with_flag_runs_v0_7_50: with --layer2 URL, exits 0 and prints JSON
"""

from __future__ import annotations

import importlib.util
import json
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


# Pre-import pipeline dependency
_pipeline = _import_module("v_r13_layer2_pipeline", WORKFLOW_KIT_DIR / "v_r13_layer2_pipeline.py")
_cli = _import_module("v_r13_layer2_cli", WORKFLOW_KIT_DIR / "v_r13_layer2_cli.py")


def test_run_layer2_cli_no_flag_returns_1_v0_7_50() -> None:
    """run_layer2_cli returns 1 when --layer2 flag is missing."""
    code = _cli.run_layer2_cli([])
    assert code == 1, f"expected exit 1, got {code}"


def test_run_layer2_cli_with_flag_runs_v0_7_50(capsys=None) -> None:
    """run_layer2_cli with --layer2 URL exits 0 and prints JSON."""
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = _cli.run_layer2_cli([
            "--layer2", "https://github.com/foo/bar/blob/main/spec.md",
        ])
    assert code == 0, f"expected exit 0, got {code}"
    output = buf.getvalue()
    # Output should be valid JSON
    parsed = json.loads(output)
    assert "url" in parsed
    assert "has_range" in parsed
    assert parsed["has_range"] is False


def main() -> int:
    test_funcs = [
        test_run_layer2_cli_no_flag_returns_1_v0_7_50,
        test_run_layer2_cli_with_flag_runs_v0_7_50,
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
