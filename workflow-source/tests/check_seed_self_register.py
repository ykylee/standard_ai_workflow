#!/usr/bin/env python3
"""Smoke — `seed_workspace_memory.py --apply` 가 self-register 호출 (v0.15.20+).

## 왜 이 검사가 필요한가

표준 §10.2 §0.4 의 세션 시작 플로우에서 *자기 workspace 가 진행 중* 이라는
사실을 registry 가 *암묵적으로* 받아야 dashboard 가 in-flight 워크스페이스를
볼 수 있다 (§5A.3). 본 검사는 seed_workspace_memory.py 가 --apply 성공 시
workspace_registry.register() 를 부르고, --no-register 로 비활성되며, idempotent
하게 동작하는지 확인한다.

5 cases:
  1) seed --apply 성공 시 registry 1건 적재.
  2) --no-register 시 registry 변동 0.
  3) 재시드 (idempotent) 시 entries 1건 유지, last_seen_at 갱신.
  4) --harness / --endpoint 명시 → registry 정확히 보존.
  5) env 기반 (WORKFLOW_HARNESS / WORKFLOW_ENDPOINT) → 등록 시 자동 사용.

Refs:
  - workflow-source/tools/seed_workspace_memory.py
  - workflow-source/workflow_kit/common/workspace_registry.py
  - core/multi_workspace_orchestration.md §5A.3
"""

from __future__ import annotations

import json
import os
import subprocess
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


def _isolated_env(extra: dict[str, str] | None = None) -> tuple[Path, dict[str, str], Path]:
    """테스트 격리: registry tmp, host_id 결정, proj 디렉터리 준비."""
    reg_dir = _tmpdir("seed-selfreg-")
    reg_path = reg_dir / "registry.json"
    proj = _tmpdir("proj-")
    (proj / "ai-workflow" / "memory" / "active").mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["WORKFLOW_REGISTRY_PATH"] = str(reg_path)
    env["WORKFLOW_HOST_ID"] = "test-host"
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    if extra:
        env.update(extra)
    return reg_path, env, proj


def _run_seed(env: dict, proj: Path, *args: str) -> subprocess.CompletedProcess:
    # 격리: --memory-root 를 명시적으로 proj 의 active/ 위로 강제.
    # seed 의 default 가 REPO_ROOT/ai-workflow/memory 라서 명시 안 하면
    # *실 저장소 active/* 에 박히는 결함을 막는다.
    proj_memory_root = proj / "ai-workflow" / "memory"
    return subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "workflow-source" / "tools" / "seed_workspace_memory.py"),
            "--memory-root", str(proj_memory_root),
            *args,
        ],
        capture_output=True,
        text=True,
        cwd=str(proj),
        env=env,
    )


def _read_journal(reg_path: Path) -> dict:
    return json.loads(reg_path.read_text(encoding="utf-8"))


def test_apply_registers_one_entry() -> None:
    """case 1."""
    reg_path, env, proj = _isolated_env()
    try:
        r = _run_seed(
            env,
            proj,
            "--branch", "feat-a",
            "--axis", "axis a",
            "--task-title", "task a",
            "--apply",
        )
        _assert(r.returncode == 0, f"seed failed: rc={r.returncode} stderr={r.stderr}")
        _assert("self-register OK" in r.stdout, f"self-register 메시지 없음: {r.stdout}")
        data = _read_journal(reg_path)
        _assert(len(data["entries"]) == 1, f"entry 1개 예상, {len(data['entries'])}")
        e = data["entries"][0]
        _assert(e["branch"] == "feat-a", f"branch mismatch: {e['branch']}")
        _assert(e["path"], "path 누락")
    finally:
        R.unregister(all=True)


def test_no_register_skips() -> None:
    """case 2."""
    reg_path, env, proj = _isolated_env()
    try:
        r = _run_seed(
            env,
            proj,
            "--branch", "feat-b",
            "--axis", "axis b",
            "--task-title", "task b",
            "--apply",
            "--no-register",
        )
        _assert(r.returncode == 0, f"seed failed: {r.stderr}")
        _assert("--no-register" in r.stdout, f"--no-register hint 없음: {r.stdout}")
        _assert(not reg_path.is_file(), f"registry file created unexpectedly: {reg_path}")
    finally:
        R.unregister(all=True)


def test_rerun_idempotent_updates_last_seen() -> None:
    """case 3: seed 재시드 시 entries 1건 유지, last_seen_at 갱신."""
    _, env, proj = _isolated_env()
    try:
        _run_seed(
            env,
            proj,
            "--branch", "feat-c",
            "--axis", "axis c",
            "--task-title", "task c",
            "--apply",
        )
        first = _read_journal(Path(env["WORKFLOW_REGISTRY_PATH"]))["entries"][0]
        first_seen = first["last_seen_at"]
        _run_seed(
            env,
            proj,
            "--branch", "feat-c",
            "--axis", "axis c",
            "--task-title", "task c",
            "--apply",
        )
        second = _read_journal(Path(env["WORKFLOW_REGISTRY_PATH"]))["entries"]
        _assert(len(second) == 1, f"entries 가 늘었다: {len(second)}")
        # last_seen_at 이 같은 초 박힘일 수 있으니 비교는 *같거나 큰* 정도.
        _assert(second[0]["last_seen_at"] >= first_seen, "last_seen_at 갱신 안 됨")
    finally:
        R.unregister(all=True)


def test_explicit_harness_and_endpoint() -> None:
    """case 4: --harness / --endpoint 명시."""
    reg_path, env, proj = _isolated_env()
    try:
        _run_seed(
            env,
            proj,
            "--branch", "feat-d",
            "--axis", "axis d",
            "--task-title", "task d",
            "--apply",
            "--harness", "codex",
            "--endpoint", "local:test-d",
        )
        data = _read_journal(reg_path)
        e = data["entries"][0]
        _assert(e["harness"] == "codex", f"harness mismatch: {e['harness']}")
        _assert(e["endpoint"] == "local:test-d", f"endpoint mismatch: {e['endpoint']}")
    finally:
        R.unregister(all=True)


def test_env_fallback_harness_endpoint() -> None:
    """case 5: env WORKFLOW_HARNESS / WORKFLOW_ENDPOINT 자동 사용."""
    reg_path, env, proj = _isolated_env(
        {
            "WORKFLOW_HARNESS": "antigravity",
            "WORKFLOW_ENDPOINT": "remote:env-feed",
        }
    )
    try:
        _run_seed(
            env,
            proj,
            "--branch", "feat-e",
            "--axis", "axis e",
            "--task-title", "task e",
            "--apply",
            # --harness / --endpoint 미명시
        )
        data = _read_journal(reg_path)
        e = data["entries"][0]
        _assert(e["harness"] == "antigravity", f"env harness not picked: {e['harness']}")
        _assert(e["endpoint"] == "remote:env-feed", f"env endpoint not picked: {e['endpoint']}")
    finally:
        R.unregister(all=True)


def main() -> int:
    tests = [
        test_apply_registers_one_entry,
        test_no_register_skips,
        test_rerun_idempotent_updates_last_seen,
        test_explicit_harness_and_endpoint,
        test_env_fallback_harness_endpoint,
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
