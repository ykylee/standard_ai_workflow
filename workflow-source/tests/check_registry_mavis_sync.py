#!/usr/bin/env python3
"""Smoke — registry ↔ mavis 글로벌 양방향 동기 (v0.15.20+).

## 왜 이 검사가 필요한가

TASK-2026-08-08-main-009. 같은 호스트의 registry 와 mavis 글로벌 mcp.json 이 서로
모른 채로 살아있다. registry 가 알려주는 workspace 가 mavis attach 후보로 자동
반영되지 않고, mavis 글로벌의 *사용자 alias* 들이 dashboard 가 *진행 중* 으로
인식되지 않는다. 본 검사는 양방향 동기 흐름의 안전 규칙 (builtin 5종 보존, 보호
alias skip, idempotency, dry-run default) 을 확인한다.

6 cases:
  1) mavis 글로벌 부재 시 import = dry-run no-op.
  2) import: builtin 5종 + 표준 alias 보호, 그 외 alias 만 entry 환원.
  3) import idempotent: 동일 alias 재실행 시 skip.
  4) export dry-run (apply_export=False) → mavis mcp.json 변경 0, preview 만.
  5) export apply → mavis mcpServers 에 mavis:<branch> alias 추가, builtin 보존.
  6) sync_mavis(apply_export=False) → import 결과 + export preview 0.

Refs:
  - workflow-source/workflow_kit/common/workspace_registry.py
  - workflow-source/tools/workspace_registry.py
  - core/multi_workspace_orchestration.md §6.5.2, §7.1
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
    """registry tmp + mavis tmp."""
    reg_dir = _tmpdir("reg-mvsync-")
    reg_path = reg_dir / "registry.json"
    mavis_dir = _tmpdir("mavis-mvsync-")
    mavis_path = mavis_dir / "mcp.json"
    os.environ["WORKFLOW_REGISTRY_PATH"] = str(reg_path)
    os.environ["WORKFLOW_MAVIS_GLOBAL_PATH"] = str(mavis_path)
    os.environ["WORKFLOW_HOST_ID"] = "test-host"
    return reg_path, mavis_path


def _seed_mavis(mavis_path: Path, extras: list[str] | None = None) -> None:
    mavis_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "mcpServers": {
            "matrix": {"command": "X", "args": []},
            "playwright": {"command": "X", "args": []},
            "cu": {"type": "streamable-http", "url": "http://127.0.0.1:15321/mavis/mcp/cu"},
            "trash": {"type": "streamable-http", "url": "http://127.0.0.1:15321/mavis/mcp/trash"},
            "github": {"command": "npx", "args": ["-y", "@mcp/github"]},
            "standardAiWorkflowReadOnly": {"command": "python3", "args": ["-m", "x"]},
        }
    }
    for i, name in enumerate(extras or [], start=1):
        data["mcpServers"][name] = {
            "command": f"/abs/tool-{i}",
            "args": ["run"],
        }
    mavis_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_import_no_mavis_file_is_noop() -> None:
    """case 1: mavis mcp.json 부재 시 no-op."""
    reg_path, mavis_path = _isolated()
    try:
        # mavis_path 가 부재.
        _assert(not mavis_path.is_file(), "mavis_path should not exist yet")
        out = R.import_mavis_aliases()
        _assert(out["wrote"] is False, f"wrote should be False: {out}")
        _assert(out.get("skipped") is True, f"skipped flag missing: {out}")
        _assert(R.list_entries() == [], f"registry should be empty: {R.list_entries()}")
    finally:
        R.unregister(all=True)


def test_import_protects_builtin_and_standard() -> None:
    """case 2: builtin 5종 + 표준 alias 보호, 사용자 alias 만 환원."""
    _, mavis_path = _isolated()
    try:
        _seed_mavis(mavis_path, extras=["my-extra-1", "my-extra-2"])
        out = R.import_mavis_aliases()
        _assert(set(out["imported"]) == {"my-extra-1", "my-extra-2"},
                f"imported mismatch: {out['imported']}")
        protected = set(out["skipped_protected"])
        expected = {"matrix", "playwright", "cu", "trash", "github", "standardAiWorkflowReadOnly"}
        _assert(protected == expected, f"protected mismatch: {protected}")
        # registry entries 도 같은 path prefix 로만
        paths = {e.path for e in R.list_entries()}
        _assert(
            paths == {"__mavis__/my-extra-1", "__mavis__/my-extra-2"},
            f"registry path mismatch: {paths}",
        )
        # branch / harness / endpoint 검증
        e1 = next(e for e in R.list_entries() if e.branch == "my-extra-1")
        _assert(e1.harness == "mavis-bridge", f"harness mismatch: {e1.harness}")
        _assert(e1.endpoint == "cmd:/abs/tool-1", f"endpoint mismatch: {e1.endpoint}")
    finally:
        R.unregister(all=True)


def test_import_idempotent() -> None:
    """case 3: 동일 alias 재실행 시 skip."""
    _, mavis_path = _isolated()
    try:
        _seed_mavis(mavis_path, extras=["my-extra-1"])
        R.import_mavis_aliases()
        first = len(R.list_entries())
        out2 = R.import_mavis_aliases()
        _assert(
            out2["imported"] == [],
            f"second import should not re-import: {out2}",
        )
        _assert(
            out2["skipped_existing"] == ["my-extra-1"],
            f"skipped_existing mismatch: {out2['skipped_existing']}",
        )
        _assert(len(R.list_entries()) == first, f"entries grew: {first} -> {len(R.list_entries())}")
    finally:
        R.unregister(all=True)


def test_export_dry_run_no_write() -> None:
    """case 4: apply=False → write 0."""
    _, mavis_path = _isolated()
    try:
        out = R.sync_mavis(apply_export=False)
        _assert(out["export_applied"] is False, f"export_applied: {out}")
        _assert(out["export_preview"] == [], f"preview should be empty (no entries): {out}")
        # mavis 파일 부재 유지
        _assert(not mavis_path.is_file(), "dry-run should not create mavis file")
    finally:
        R.unregister(all=True)


def test_export_apply_adds_alias_and_preserves_builtin() -> None:
    """case 5: apply=True → builtin 보존 + mavis:<branch> 추가."""
    _, mavis_path = _isolated()
    try:
        _seed_mavis(mavis_path, extras=["my-extra-1"])
        # 1) import 먼저 (registry 채우기)
        imp = R.import_mavis_aliases()
        # 2) export apply — entries 를 그대로 emit (sync_mavis 가 list_entries() 사용)
        out = R.sync_mavis(apply_export=True)
        # entries 의 branch=my-extra-1 + mavis:feat-x 가 아닌 list_entries branch
        # my-extra-1 만 mavis:my-extra-1 로 emit 되어야 함.
        # sync_mavis 의 new_aliases 는 *모든* entries 를 emit. builtin 5종은
        # registry entries 가 아니므로 안 emit. 그 외는 emit.
        _assert(out["export_applied"] is True, f"export_applied: {out}")
        # mavis mcp.json 파싱
        data = json.loads(mavis_path.read_text(encoding="utf-8"))
        keys = set(data["mcpServers"])
        # builtin 5종 + 표준 + 사용자 1개 + registry export (mavis:my-extra-1) — 보존
        _assert({"matrix", "playwright", "cu", "trash", "github",
                 "standardAiWorkflowReadOnly", "my-extra-1", "mavis:my-extra-1"} <= keys,
                f"missing keys: {keys}")
    finally:
        R.unregister(all=True)


def test_sync_mavis_no_apply_writes_nothing() -> None:
    """case 6: sync_mavis(apply=False) → import 는 적용, export 는 preview 0."""
    _, mavis_path = _isolated()
    try:
        _seed_mavis(mavis_path, extras=["my-extra-1"])
        out = R.sync_mavis(apply_export=False)
        _assert(
            "my-extra-1" in out["imported"],
            f"imported should include my-extra-1: {out}",
        )
        _assert(out["export_applied"] is False, f"export_applied should be False: {out}")
        # mavis mcp.json 의 mavis:* alias 가 *없어야* 함.
        data = json.loads(mavis_path.read_text(encoding="utf-8"))
        alias_keys = [k for k in data["mcpServers"] if k.startswith("mavis:")]
        _assert(
            alias_keys == [],
            f"apply=False 이지만 mavis:* alias 가 박혔다: {alias_keys}",
        )
    finally:
        R.unregister(all=True)


def main() -> int:
    tests = [
        test_import_no_mavis_file_is_noop,
        test_import_protects_builtin_and_standard,
        test_import_idempotent,
        test_export_dry_run_no_write,
        test_export_apply_adds_alias_and_preserves_builtin,
        test_sync_mavis_no_apply_writes_nothing,
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
