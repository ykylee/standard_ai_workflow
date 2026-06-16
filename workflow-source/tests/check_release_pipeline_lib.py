"""tools.release_pipeline_lib in-process wrapper test (v0.7.55+).

Verifies that `tools.release_pipeline_lib.cmd_validate` correctly loads the
underlying `tools/release_pipeline.py` script and returns a 4-key dict.

This test imports `release_pipeline_lib` from `workflow-source/tools/`,
which is *sibling* of `workflow_kit/`. Path resolution matches the
dispatcher's release-doctor handler.

Test list:
1. test_cmd_validate_returns_4_keys: returns dict with packaging/doctor/state/git
2. test_cmd_validate_all_skipped_returns_all_ok: all 4 sources skipped → all ok=True
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Add workflow-source/tools/ to sys.path so release_pipeline_lib import works.
TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


def _import_lib():
    spec = importlib.util.spec_from_file_location(
        "release_pipeline_lib", str(TOOLS_DIR / "release_pipeline_lib.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["release_pipeline_lib"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_cmd_validate_returns_4_keys_v0_7_55() -> None:
    """cmd_validate() returns dict with 4 expected keys."""
    lib = _import_lib()
    result = lib.cmd_validate()
    assert isinstance(result, dict), f"expected dict, got {type(result)}"
    for key in ("packaging", "doctor", "state", "git"):
        assert key in result, f"missing key: {key}"


def test_cmd_validate_all_skipped_returns_all_ok_v0_7_55() -> None:
    """cmd_validate with all 4 sources skipped returns all ok=True."""
    lib = _import_lib()
    result = lib.cmd_validate(
        skip_packaging=True, skip_doctor=True,
        skip_state=True, skip_git=True,
    )
    for key in ("packaging", "doctor", "state", "git"):
        assert result[key].get("ok") is True, f"{key} not ok: {result[key]}"
        assert result[key].get("skipped") is True, f"{key} not marked skipped: {result[key]}"


def main() -> int:
    test_funcs = [
        test_cmd_validate_returns_4_keys_v0_7_55,
        test_cmd_validate_all_skipped_returns_all_ok_v0_7_55,
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
