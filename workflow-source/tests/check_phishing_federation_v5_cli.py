"""workflow_kit.phishing_federation_v5_cli test (v0.7.51+).

Test list:
1. test_run_federation_v5_cli_no_flag_returns_1_v0_7_51: missing --federate-v5 returns 1
2. test_run_federation_v5_cli_no_phishtank_key_runs_v0_7_51: runs without key (OpenPhish only)
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path
import io

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


_v5 = _import_module("phishing_federation_v5", WORKFLOW_KIT_DIR / "phishing_federation_v5.py")
_cli = _import_module("phishing_federation_v5_cli", WORKFLOW_KIT_DIR / "phishing_federation_v5_cli.py")


def test_run_federation_v5_cli_no_flag_returns_1_v0_7_51() -> None:
    """run_federation_v5_cli returns 1 when --federate-v5 is missing."""
    code = _cli.run_federation_v5_cli([])
    assert code == 1, f"expected exit 1, got {code}"


def test_run_federation_v5_cli_no_phishtank_key_runs_v0_7_51() -> None:
    """run_federation_v5_cli without --phishtank-key runs (OpenPhish only, may fail)."""
    # Without API key + without network, the federation will likely error.
    # We're just verifying the CLI is wired correctly. Expect exit 0 or 1.
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = _cli.run_federation_v5_cli(["--federate-v5"])
    # Either it works (no PhishTank, OpenPhish might fail in test env) or fails gracefully
    assert code in (0, 1), f"expected exit 0 or 1, got {code}"


def main() -> int:
    test_funcs = [
        test_run_federation_v5_cli_no_flag_returns_1_v0_7_51,
        test_run_federation_v5_cli_no_phishtank_key_runs_v0_7_51,
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
