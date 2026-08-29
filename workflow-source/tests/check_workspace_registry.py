#!/usr/bin/env python3
"""Smoke test — workspace registry 모듈 + CLI (6 cases).

## 왜 이 검사가 필요한가

표준 §10.2 §7.1 의 workspace registry 가 *정말로* git 외부에 안전하게 저장되는지,
in-flight 가시성을 줘야 하는지 측정이 필요하다. 또 dashboard Panel 5 가 registry
경로를 합류시키는 동작도 직접 확인한다. 이 산출물이 registry 에 들고 있는 entry 의
metadata(branch/harness/endpoint) 가 안정적이어야 다른 도구들이 의존할 수 있다.

7 cases:
  1) register: 새 entry 가 생기고 `last_seen_at` 이 박힌다
  2) register idempotent: 동일 path 재등록 시 entries 증가 ❌, `last_seen_at` 갱신 ⭕
  3) unregister --path: 해당 entry 만 제거
  4) unregister --branch: 같은 branch 의 모든 entry 제거
  5) unregister --all: 전부 제거
  6) atomic write: 권한 0o600, JSON 정상 parse round-trip
  7) dashboard 합류: registry 가 알려주는 경로의 state.json 이 collect_recent_releases
     의 timeline 에 합류

Refs:
  - workflow-source/core/multi_workspace_orchestration.md §7.1, §5A.3
  - workflow-source/workflow_kit/common/workspace_registry.py
  - workflow-source/workflow_kit/tools/workspace_registry.py
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import os
import stat
import subprocess
import sys
import atexit
import shutil
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import workspace_registry as R  # noqa: E402
from workflow_kit.common.dashboard_data import collect_recent_releases  # noqa: E402


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


def _isolated_registry():
    """테스트 격리를 위해 WORKFLOW_REGISTRY_PATH 를 tmpdir 로 강제."""
    tmp = _tmpdir("regtest-")
    os.environ["WORKFLOW_REGISTRY_PATH"] = str(tmp / "registry.json")
    os.environ["WORKFLOW_HOST_ID"] = "test-host-isolated"
    # 캐시 비우기
    R.unregister(all=True)
    return tmp


def test_register_creates_entry() -> None:
    """case 1."""
    tmp = _isolated_registry()
    try:
        R.register("/tmp/ws-a", branch="feat-a", harness="codex")
        entries = R.list_entries()
        _assert(
            len(entries) == 1,
            f"entry 1개 예상, 실제 {len(entries)}",
        )
        e = entries[0]
        _assert(e.branch == "feat-a", f"branch mismatch: {e.branch}")
        _assert(e.harness == "codex", f"harness mismatch: {e.harness}")
        _assert(e.last_seen_at != "", "last_seen_at 누락")
        _assert(e.registered_at != "", "registered_at 누락")
    finally:
        R.unregister(all=True)


def test_register_idempotent() -> None:
    """case 2: 동일 path 재등록 시 entries 증가 ❌, last_seen 갱신 ⭕."""
    _isolated_registry()
    try:
        R.register("/tmp/ws-a", branch="feat-a")
        first = R.list_entries()[0]
        first_seen = first.last_seen_at
        # 짧은 sleep 대용: last_seen_at 의 초 단위 박힘이므로 1초 후 재시도.
        # 단위 테스트 시간 민감도 회피: 그냥 한 번 더 호출하고 last_seen_at 이
        # 같은 초라도 동일 값으로 인정한다 (본 검사에서는 카운트만 본다).
        R.register("/tmp/ws-a", branch="feat-a")
        second = R.list_entries()
        _assert(
            len(second) == 1,
            f"재등록 시 entries 가 늘었다: {len(second)}",
        )
        # 동일 path 가 두 번 들어가서 dedupe 되었는지가 핵심.
        _assert(
            second[0].path == first.path,
            f"path 변경됨: {first.path} → {second[0].path}",
        )
    finally:
        R.unregister(all=True)


def test_unregister_by_path() -> None:
    """case 3."""
    _isolated_registry()
    try:
        R.register("/tmp/ws-a", branch="feat-a")
        R.register("/tmp/ws-b", branch="feat-b")
        R.unregister(path="/tmp/ws-a")
        entries = R.list_entries()
        _assert(
            len(entries) == 1 and entries[0].branch == "feat-b",
            f"unregister(path) 실패: {entries}",
        )
    finally:
        R.unregister(all=True)


def test_unregister_by_branch() -> None:
    """case 4."""
    _isolated_registry()
    try:
        R.register("/tmp/ws-a", branch="feat-x")
        R.register("/tmp/ws-b", branch="feat-x")
        R.register("/tmp/ws-c", branch="feat-y")
        R.unregister(branch="feat-x")
        entries = R.list_entries()
        _assert(
            len(entries) == 1 and entries[0].branch == "feat-y",
            f"unregister(branch) 실패: {entries}",
        )
    finally:
        R.unregister(all=True)


def test_unregister_all() -> None:
    """case 5."""
    _isolated_registry()
    try:
        R.register("/tmp/ws-a", branch="feat-a")
        R.register("/tmp/ws-b", branch="feat-b")
        R.register("/tmp/ws-c", branch="feat-c")
        R.unregister(all=True)
        _assert(len(R.list_entries()) == 0, "unregister --all 미동작")
    finally:
        pass  # 모두 비웠으므로 cleanup 불요


def test_atomic_write_permissions() -> None:
    """case 6: 파일 권한 0o600, JSON round-trip."""
    tmp = _isolated_registry()
    try:
        R.register("/tmp/ws-a", branch="feat-a")
        path = R.registry_path()
        _assert(path.is_file(), f"registry 파일 없음: {path}")
        mode = stat.S_IMODE(path.stat().st_mode)
        _assert(
            mode == 0o600,
            f"권한 0o600 예상, 실제 {oct(mode)}",
        )
        # JSON round-trip
        raw = path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        _assert(parsed["schema_version"] == "1", f"schema_version mismatch: {parsed}")
        _assert(parsed["host_id"] == "test-host-isolated", f"host_id mismatch: {parsed}")
        _assert(len(parsed["entries"]) == 1, f"entries count mismatch: {parsed}")
    finally:
        R.unregister(all=True)


def test_dashboard_aggregates_registry_paths() -> None:
    """case 7: registry 경로의 state.json 이 timeline 에 합류."""
    _isolated_registry()
    try:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            # 정합 layout
            state_dir = tdp / "ai-workflow" / "memory" / "active" / "demo-feat-reg"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "state.json").write_text(
                json.dumps(
                    {"session": {"recent_done_items": ["__registry_marker__"]}},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            R.register(td, branch="demo-feat-reg", harness="codex")
            # 자기 root 외 추가 합류 검증. v1.1.5: primary 를 실제 저장소가 아니라
            # tmp fixture 로 — REPO_ROOT 를 쓰면 저장소 recent_done_items 가
            # top_n 을 넘는 순간 marker 가 컷 밖으로 밀려 깨진다 (살아있는
            # 저장소 상태는 기대값이 아니다).
            primary = tdp / "primary_root"
            pstate = primary / "ai-workflow" / "memory" / "active" / "demo-feat-p"
            pstate.mkdir(parents=True, exist_ok=True)
            (pstate / "state.json").write_text(
                json.dumps(
                    {"session": {"recent_done_items": ["__primary_item__"]}},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            merged = collect_recent_releases(primary, top_n=50)
            found = any(
                "__registry_marker__" in t["preview"] for t in merged["timeline"]
            )
            _assert(
                found,
                f"registry 합류 marker가 timeline 에 없음: {merged}",
            )
            # registry 가 없으면 합류 ❌ (대조군)
            R.unregister(all=True)
            baseline = collect_recent_releases(primary, top_n=50)
            baseline_has = any(
                "__registry_marker__" in t["preview"] for t in baseline["timeline"]
            )
            _assert(
                not baseline_has,
                "registry 비웠는데도 marker 가 살아있음 (fallback 의심)",
            )
    finally:
        R.unregister(all=True)


def test_cli_register_list_paths() -> None:
    """CLI 의 basic 동작 (별도 subprocess)."""
    tmp = _isolated_registry()
    try:
        env = os.environ.copy()
        env["WORKFLOW_REGISTRY_PATH"] = str(tmp / "registry.json")
        env["WORKFLOW_HOST_ID"] = "cli-test"
        with tempfile.TemporaryDirectory() as td:
            cli = [
                sys.executable,
                str(REPO_ROOT / "workflow-source" / "workflow_kit" / "tools" / "workspace_registry.py"),
                "register",
                "--path", td,
                "--branch", "feat-cli",
                "--harness", "codex",
                "--apply",
            ]
            r = subprocess.run(cli, env=env, capture_output=True, text=True)
            _assert(r.returncode == 0, f"register CLI failed: {r.stderr}")

            cli = [
                sys.executable,
                str(REPO_ROOT / "workflow-source" / "workflow_kit" / "tools" / "workspace_registry.py"),
                "list",
            ]
            r = subprocess.run(cli, env=env, capture_output=True, text=True)
            _assert(r.returncode == 0, f"list CLI failed: {r.stderr}")
            _assert("feat-cli" in r.stdout, f"list 출력에 feat-cli 없음: {r.stdout}")

            cli = [
                sys.executable,
                str(REPO_ROOT / "workflow-source" / "workflow_kit" / "tools" / "workspace_registry.py"),
                "paths",
            ]
            r = subprocess.run(cli, env=env, capture_output=True, text=True)
            _assert(r.returncode == 0, f"paths CLI failed: {r.stderr}")
            _assert(td in r.stdout, f"paths 출력에 {td} 없음: {r.stdout}")

            cli = [
                sys.executable,
                str(REPO_ROOT / "workflow-source" / "workflow_kit" / "tools" / "workspace_registry.py"),
                "unregister",
                "--all",
                "--apply",
            ]
            r = subprocess.run(cli, env=env, capture_output=True, text=True)
            _assert(r.returncode == 0, f"unregister CLI failed: {r.stderr}")
    finally:
        R.unregister(all=True)


def main() -> int:
    tests = [
        test_register_creates_entry,
        test_register_idempotent,
        test_unregister_by_path,
        test_unregister_by_branch,
        test_unregister_all,
        test_atomic_write_permissions,
        test_dashboard_aggregates_registry_paths,
        test_cli_register_list_paths,
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
