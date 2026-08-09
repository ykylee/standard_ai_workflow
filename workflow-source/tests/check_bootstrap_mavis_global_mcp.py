#!/usr/bin/env python3
"""Smoke — bootstrap `--harness mavis --enable-mcp` 의 글로벌 mcp.json merge (v0.15.20+).

## 왜 이 검사가 필요한가

`check_bootstrap_mavis_global_mcp.py` 는 mavis 데스크탑 런타임의 *유일한 등록
표면* 인 `~/.minimax/mcp/mcp.json` 에 `standardAiWorkflowReadOnly` 가 *atomic
merge* 되는지 확인한다. 정본 §6.5.2 는

- 명령 args 에 절대 경로 env (STANDARD_AI_WORKFLOW_ROOT / PYTHONPATH) 가 들어가야
  한다 (mavis 가 띄울 때 cwd 가 데스크탑 런타임 자리이므로 상대 경로면
  `ModuleNotFoundError` 로 *조용히* 죽는다).
- builtin 5종 (`matrix` / `playwright` / `cu` / `trash` / `github`) 보존.
- backup (atomic write 전 `<path>.bak.<UTC-iso>`).
- 동일 alias 가 이미 있으면 keep (사용자 deterministic).

6 cases:
  1) fresh 파일 생성 시 backup 0 + 새 entry 1 추가.
  2) 5 builtin 보존 + 1 standardAiWorkflowReadOnly 추가.
  3) env 두 개 모두 `Path(...).resolve()` 가 절대.
  4) 동일 alias 재실행 (force=False) → skip.
  5) 동일 alias 재실행 (force=True) → overwrite.
  6) argparse 가 `--harness mavis` 를 받아내고 `--mavis-global-mcp-path` 옵션
     으로 격리 경로 override.

Refs:
  - workflow-source/core/mcp_installation_by_harness.md §6.5.2
  - workflow-source/scripts/bootstrap_lib/mcp.py
"""

from __future__ import annotations

import argparse
import json
import sys
import atexit
import shutil
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
SCRIPTS_DIR = SOURCE_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from bootstrap_lib.harnesses import (  # noqa: E402
    HARNESS_SPECS,
    SUPPORTED_HARNESSES,
    HARNESS_FILE_BUILDERS,
)
from bootstrap_lib.mcp import (  # noqa: E402
    DEFAULT_MAVIS_GLOBAL_MCP_PATH,
    MCP_CONFIG_RENDERERS,
    MCP_SERVER_ALIAS,
    atomic_merge_mavis_global,
    render_mavis_global_mcp_config,
)
from bootstrap_lib.__main__ import HARNESS_DEFINITIONS  # noqa: E402


#: mkdtemp + 프로세스 종료 시 정리 (v1.1.2, `check_tempdir_leak_guard` case 7).
#:
#: `mkdtemp` 은 `TemporaryDirectory` 와 달리 자동 정리가 **전혀** 없어서 성공한
#: 실행마다 temp dir 이 하나씩 쌓인다. 컨텍스트 매니저가 정석이지만 이 파일의
#: 테스트들은 함수 전체가 한 덩어리라 감싸려면 전부 재들여쓰기해야 한다. 정리
#: 보장은 `atexit` 으로 같게 두고 변경면을 줄인다 — assert 가 중간에 터져도 정리된다.
def _tmpdir(prefix: str) -> Path:
    path = Path(tempfile.mkdtemp(prefix=prefix))
    atexit.register(shutil.rmtree, path, ignore_errors=True)
    return path


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _args(target_root: str) -> argparse.Namespace:
    return argparse.Namespace(
        target_root=target_root,
        mcp_bridge="jsonrpc-bridge",
    )


def test_dispatch_consistency() -> None:
    """case 0: 5 dispatch 자료 / mavis 진입."""
    _assert("mavis" in HARNESS_SPECS, "mavis missing from HARNESS_SPECS")
    _assert("mavis" in SUPPORTED_HARNESSES, "mavis missing from SUPPORTED_HARNESSES")
    _assert(
        "mavis" in HARNESS_FILE_BUILDERS,
        "mavis missing from HARNESS_FILE_BUILDERS (no-op builder required)",
    )
    _assert("mavis" in HARNESS_DEFINITIONS, "mavis missing from HARNESS_DEFINITIONS")
    # mavis 는 글로벌 mcp.json merge 만 — MCP_CONFIG_RENDERERS 에는 *없어야* 함.
    _assert(
        "mavis" not in MCP_CONFIG_RENDERERS,
        "mavis should not be in MCP_CONFIG_RENDERERS (project-local 0)",
    )
    # DEFAULT_MAVIS_GLOBAL_MCP_PATH 가 의도된 경로인지.
    _assert(
        DEFAULT_MAVIS_GLOBAL_MCP_PATH == Path.home() / ".minimax" / "mcp" / "mcp.json",
        f"DEFAULT_MAVIS_GLOBAL_MCP_PATH drift: {DEFAULT_MAVIS_GLOBAL_MCP_PATH}",
    )


def test_fresh_create_no_backup() -> None:
    """case 1: 파일 부재 시 backup 0, 새 entry 1 추가."""
    tmp = _tmpdir("mavis-fresh-")
    target = tmp / "mcp.json"
    out = atomic_merge_mavis_global(target, render_mavis_global_mcp_config(_args(str(REPO_ROOT))))
    _assert(out["wrote"], "fresh create should write")
    _assert(out["backup"] is None, "fresh create should have no backup")
    data = json.loads(target.read_text(encoding="utf-8"))
    _assert(MCP_SERVER_ALIAS in data["mcpServers"], "alias missing in fresh create")
    _assert(len(data["mcpServers"]) == 1, f"unexpected keys: {data['mcpServers']}")


def test_existing_5_builtin_preserved_plus_alias() -> None:
    """case 2: 5 builtin 보존 + alias 1 추가."""
    tmp = _tmpdir("mavis-existing-")
    target = tmp / "mcp.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    seed = {
        "mcpServers": {
            "matrix": {"command": "X", "args": []},
            "playwright": {"command": "X", "args": []},
            "cu": {"type": "streamable-http", "url": "http://x"},
            "trash": {"type": "streamable-http", "url": "http://x"},
            "github": {"command": "X", "args": []},
        }
    }
    target.write_text(json.dumps(seed), encoding="utf-8")
    out = atomic_merge_mavis_global(target, render_mavis_global_mcp_config(_args(str(REPO_ROOT))))
    _assert(out["wrote"], "merge should write")
    _assert(out["backup"] is not None and out["backup"].is_file(), "backup not created")
    data = json.loads(target.read_text(encoding="utf-8"))
    keys = set(data["mcpServers"])
    expected = {"matrix", "playwright", "cu", "trash", "github", MCP_SERVER_ALIAS}
    _assert(keys == expected, f"key drift: {keys} vs {expected}")


def test_absolute_env_paths() -> None:
    """case 3: env 두 개 모두 abs."""
    tmp = _tmpdir("mavis-abs-")
    target = tmp / "mcp.json"
    atomic_merge_mavis_global(target, render_mavis_global_mcp_config(_args(str(REPO_ROOT))))
    data = json.loads(target.read_text(encoding="utf-8"))
    entry = data["mcpServers"][MCP_SERVER_ALIAS]
    env = entry["env"]
    _assert("STANDARD_AI_WORKFLOW_ROOT" in env, "STANDARD_AI_WORKFLOW_ROOT 누락")
    _assert("PYTHONPATH" in env, "PYTHONPATH 누락")
    _assert(
        Path(env["STANDARD_AI_WORKFLOW_ROOT"]).is_absolute(),
        f"STANDARD_AI_WORKFLOW_ROOT not absolute: {env['STANDARD_AI_WORKFLOW_ROOT']}",
    )
    _assert(
        Path(env["PYTHONPATH"]).is_absolute(),
        f"PYTHONPATH not absolute: {env['PYTHONPATH']}",
    )
    _assert(entry["command"] == "python3", f"command must be python3, got {entry['command']}")
    _assert(
        entry["args"] == ["-m", "workflow_kit.server.read_only_jsonrpc", "--stdio-lines"],
        f"args drift: {entry['args']}",
    )


def test_resame_alias_skip_without_force() -> None:
    """case 4: 동일 alias 재실행 (force=False) → skip."""
    tmp = _tmpdir("mavis-skip-")
    target = tmp / "mcp.json"
    block = render_mavis_global_mcp_config(_args(str(REPO_ROOT)))
    atomic_merge_mavis_global(target, block)
    out2 = atomic_merge_mavis_global(target, block)
    _assert(out2["skipped"], "rerun should skip without force")
    _assert(not out2["wrote"], "rerun should not write without force")


def test_resame_alias_overwrite_with_force() -> None:
    """case 5: 동일 alias 재실행 (force=True) → overwrite."""
    tmp = _tmpdir("mavis-force-")
    target = tmp / "mcp.json"
    block = render_mavis_global_mcp_config(_args(str(REPO_ROOT)))
    atomic_merge_mavis_global(target, block)
    out2 = atomic_merge_mavis_global(target, block, force=True)
    _assert(out2["wrote"], "force rerun should write")
    _assert(not out2["skipped"], "force rerun should not skip")


def test_argparse_accepts_mavis_with_overrides() -> None:
    """case 6: argparse 가 --harness mavis + --mavis-global-mcp-path 수용."""
    from bootstrap_lib import __main__ as _bm

    tmp = _tmpdir("mavis-arg-")
    target = tmp / "mcp.json"
    saved = sys.argv
    try:
        sys.argv = [
            "bootstrap.py",
            "--project-slug", "demo",
            "--project-name", "D",
            "--target-root", str(REPO_ROOT),
            "--harness", "mavis",
            "--no-interactive",
            "--enable-mcp",
            "--mavis-global-mcp-path", str(target),
        ]
        ns = _bm.parse_args()
    finally:
        sys.argv = saved
    _assert("mavis" in ns.harnesses, f"mavis not in harnesses: {ns.harnesses}")
    _assert(
        getattr(ns, "mavis_global_mcp_path", None) == str(target),
        f"override not picked: {getattr(ns, 'mavis_global_mcp_path', None)}",
    )
    _assert(ns.enable_mcp, "enable-mcp not set")


def main() -> int:
    tests = [
        test_dispatch_consistency,
        test_fresh_create_no_backup,
        test_existing_5_builtin_preserved_plus_alias,
        test_absolute_env_paths,
        test_resame_alias_skip_without_force,
        test_resame_alias_overwrite_with_force,
        test_argparse_accepts_mavis_with_overrides,
    ]
    passed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"FAIL  {t.__name__}: {e}")
            return 1
        except Exception as e:  # pragma: no cover
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
            return 2
        print(f"PASS  {t.__name__}")
        passed += 1
    print(f"\n{passed}/{len(tests)} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
