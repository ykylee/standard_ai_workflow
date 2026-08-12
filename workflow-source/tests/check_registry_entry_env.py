#!/usr/bin/env python3
"""Smoke — RegistryEntry.env 필드 + sync_mavis env 합성 (v0.15.21+).

## 왜 이 검사가 필요한가

TASK-2026-08-08-main-010. sync_mavis 의 export 가 *이전* registry entries 의
env 가 비어 있어 의미 있는 alias 가 안 나가는 모티프를 닫는다. RegistryEntry
에 env 필드 추가, register() 에 env kwarg, seed 가
STANDARD_AI_WORKFLOW_ROOT / PYTHONPATH 자동 주입, sync_mavis 가 그 env 를
mavis alias env 로 emit. 기존 entries (env field 누락) 는 *빈 dict* 로 load
— 하위 호환.

6 cases:
  1) RegistryEntry.env default = {} (empty tuple).
  2) register(env=...) 가 env 보존 + last_seen 갱신.
  3) JSON round-trip env 정상.
  4) legacy registry.json (env field 없음) load → env = {}.
  5) sync_mavis(apply_export=True) 가 entries.env 를 mavis alias env 로 emit.
  6) sync_mavis(apply_export=False) 시 mavis mcp.json 변경 0 (env preview 만).

Refs:
  - workflow-source/workflow_kit/common/workspace_registry.py
  - workflow-source/workflow_kit/tools/seed_workspace_memory.py
"""

from __future__ import annotations

import json
import os
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

from workflow_kit.common import workspace_registry as R  # noqa: E402


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


def _isolated() -> tuple[Path, Path]:
    reg_dir = _tmpdir("reg-env-")
    reg_path = reg_dir / "registry.json"
    mavis_dir = _tmpdir("mavis-env-")
    mavis_path = mavis_dir / "mcp.json"
    os.environ["WORKFLOW_REGISTRY_PATH"] = str(reg_path)
    os.environ["WORKFLOW_MAVIS_GLOBAL_PATH"] = str(mavis_path)
    os.environ["WORKFLOW_HOST_ID"] = "test-host"
    return reg_path, mavis_path


def test_default_env_is_empty() -> None:
    """case 1."""
    _, _ = _isolated()
    try:
        R.register("/abs/ws", branch="feat-a")
        e = R.list_entries()[0]
        _assert(e.env == (), f"default env should be empty tuple, got {e.env!r}")
        _assert(e.env_dict() == {}, f"env_dict should be empty: {e.env_dict()}")
    finally:
        R.unregister(all=True)


def test_register_preserves_env() -> None:
    """case 2."""
    reg_path, _ = _isolated()
    try:
        env = {
            "STANDARD_AI_WORKFLOW_ROOT": "/abs/ws",
            "PYTHONPATH": "/abs/ws/workflow-source",
        }
        R.register("/abs/ws", branch="feat-b", env=env)
        e = R.list_entries()[0]
        _assert(
            e.env_dict() == env,
            f"env mismatch: {e.env_dict()} vs {env}",
        )
        # 재등록 시 env 는 명시했으므로 *덮어쓰기*
        new_env = {"X": "1"}
        R.register("/abs/ws", branch="feat-b", env=new_env)
        e2 = R.list_entries()[0]
        _assert(
            e2.env_dict() == new_env,
            f"env not overwritten: {e2.env_dict()}",
        )
    finally:
        R.unregister(all=True)


def test_json_roundtrip_env() -> None:
    """case 3."""
    reg_path, _ = _isolated()
    try:
        R.register(
            "/abs/ws",
            branch="feat-c",
            env={"A": "1", "B": "2"},
        )
        data = json.loads(reg_path.read_text(encoding="utf-8"))
        env_dump = data["entries"][0]["env"]
        _assert(env_dump == {"A": "1", "B": "2"}, f"env dump: {env_dump}")
        # reload
        loaded = R.load()
        _assert(
            loaded.entries[0].env_dict() == {"A": "1", "B": "2"},
            f"reload env: {loaded.entries[0].env_dict()}",
        )
    finally:
        R.unregister(all=True)


def test_legacy_registry_loads_with_empty_env() -> None:
    """case 4: env field 없는 기존 entries → 빈 dict (하위 호환)."""
    reg_path, _ = _isolated()
    try:
        legacy = {
            "schema_version": "1",
            "host_id": "x",
            "updated_at": "",
            "entries": [
                {
                    "path": "/legacy",
                    "branch": "old",
                    "harness": None,
                    "endpoint": None,
                    "registered_at": "2026-01-01T00:00:00Z",
                    "last_seen_at": "2026-01-01T00:00:00Z",
                }
            ],
        }
        reg_path.write_text(json.dumps(legacy), encoding="utf-8")
        loaded = R.load()
        _assert(len(loaded.entries) == 1, f"entries count: {len(loaded.entries)}")
        e = loaded.entries[0]
        _assert(e.env_dict() == {}, f"legacy env should be empty: {e.env_dict()}")
    finally:
        R.unregister(all=True)


def test_sync_mavis_emits_env() -> None:
    """case 5: sync_mavis(apply=True) 가 entries.env 를 mavis alias env 로 emit."""
    _, mavis_path = _isolated()
    try:
        env = {
            "STANDARD_AI_WORKFLOW_ROOT": "/abs/ws3",
            "PYTHONPATH": "/abs/ws3/workflow-source",
        }
        R.register("/abs/ws3", branch="feat-sync", env=env)
        out = R.sync_mavis(apply_export=True)
        _assert(out["export_applied"] is True, f"export_applied: {out}")
        data = json.loads(mavis_path.read_text(encoding="utf-8"))
        alias = data["mcpServers"].get("mavis:feat-sync")
        _assert(alias is not None, f"mavis:feat-sync missing: {list(data['mcpServers'])}")
        _assert(
            alias.get("env") == env,
            f"mavis alias env mismatch: {alias.get('env')}",
        )
    finally:
        R.unregister(all=True)


def test_sync_mavis_dry_run_no_write() -> None:
    """case 6: apply=False → mavis mcp.json 변경 0."""
    _, mavis_path = _isolated()
    try:
        R.register(
            "/abs/ws4",
            branch="feat-dry",
            env={"X": "1"},
        )
        out = R.sync_mavis(apply_export=False)
        _assert(out["export_applied"] is False, f"export_applied: {out}")
        # mavis 파일이 *없어야* 한다.
        _assert(
            not mavis_path.is_file(),
            f"dry-run created mavis file: {mavis_path}",
        )
    finally:
        R.unregister(all=True)


def main() -> int:
    tests = [
        test_default_env_is_empty,
        test_register_preserves_env,
        test_json_roundtrip_env,
        test_legacy_registry_loads_with_empty_env,
        test_sync_mavis_emits_env,
        test_sync_mavis_dry_run_no_write,
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
