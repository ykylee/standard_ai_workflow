"""tools.release_pipeline_lib — in-process wrapper for release_pipeline.py (v0.7.55+).

기존 `tools/release_pipeline.py` (1478 line) 는 *script* (`if __name__ == "__main__": main()`)
라 `import` 가 안 됨. 본 wrapper 는 *in-process* 호출을 위해:

1. `tools/` 를 sys.path 에 임시로 insert (relative import 회피)
2. `release_pipeline` module spec load via importlib
3. `cmd_validate` / `cmd_version_bump` / `cmd_note_draft` / `cmd_release` /
   `cmd_verify` / `cmd_rollback` / `cmd_dist` / `cmd_changelog_gen` 등 노출

Design note: `tools/release_pipeline.py` 의 REPO_ROOT = parents[1] (workflow-source/).
본 wrapper 도 같은 위치에 있으므로 REPO_ROOT 정합 — 추가 조정 불필요.

Cross-ref: memory rule 12 (cleanup 정공법 — inline vs dispatcher), release_pipeline.py
의 module-level const (REPO_ROOT / PYPROJECT / WORKFLOW_KIT_INIT) 가 *load time* 에
계산되므로 wrapper module 위치 변경 시 REPO_ROOT drift 위험.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


_TOOLS_DIR = Path(__file__).resolve().parent
_RELEASE_PIPELINE_PATH = _TOOLS_DIR / "release_pipeline.py"


def _load_release_pipeline() -> ModuleType:
    """Load tools/release_pipeline.py as a module (script → module).

    Uses importlib.util.spec_from_file_location to bypass sys.path / package
    boundary. The module is cached in sys.modules under a stable name so
    subsequent imports return the same instance (avoids REPO_ROOT drift).
    """
    if "tools_release_pipeline" in sys.modules:
        return sys.modules["tools_release_pipeline"]
    spec = importlib.util.spec_from_file_location(
        "tools_release_pipeline", str(_RELEASE_PIPELINE_PATH),
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {_RELEASE_PIPELINE_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tools_release_pipeline"] = mod
    spec.loader.exec_module(mod)
    return mod


def cmd_validate(skip_packaging: bool = False, skip_doctor: bool = False,
                 skip_state: bool = False, skip_git: bool = False) -> dict:
    """Run cmd_validate from tools/release_pipeline.py in-process.

    Returns the dict shape produced by cmd_validate (4 keys: packaging / doctor /
    state / git, each with `ok` boolean + details).
    """
    mod = _load_release_pipeline()

    class _Args:
        pass
    args = _Args()
    args.skip_packaging = skip_packaging
    args.skip_doctor = skip_doctor
    args.skip_state = skip_state
    args.skip_git = skip_git
    return mod.cmd_validate(args)
