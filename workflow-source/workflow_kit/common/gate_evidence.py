"""push 전 게이트 통과 기록 — CI 를 대신하는 발행 게이트의 근거 (TASK-2026-09-23-main-022).

## 왜 필요한가

GitHub Actions 테스트 workflow 를 폐지하고(2026-09-23 소유자 결정) 각 개발환경의
push 전 게이트가 동등 검사를 맡게 됐다. 그런데 발행 게이트(`release --apply`)는
"이 커밋에서 전량이 green 이었다" 는 사실을 CI 에게 물어 왔다 — v1.8.0 이 smoke
10 커밋 연속 red 위에서 발행된 뒤(v1.9.0) 넣은 차단이다. CI 가 없어지면 그 사실을
어디에도 물을 수 없고, 게이트를 비우면 같은 사고가 다시 난다.

그래서 runner 가 **게이트 조건을 만족한 실행**을 커밋 sha 로 기록하고, 발행 게이트가
그 기록을 읽는다. "모름은 통과가 아니다" 는 그대로다 — 기록이 없으면 막는다.

## 기록 조건 (전부 참이어야 한다)

- 필터 없는 전량 (`--filter` / `--changed` 없음) 이고 `--branch-context=all`
- 종료 코드 0
- 시작 시점 워킹 트리가 깨끗했고 (untracked 포함), 끝났을 때 HEAD 가 그대로다
  — 커밋되지 않은 변경 위에서 잰 green 은 그 sha 의 green 이 아니다.

## 저장 위치

`<git common dir>/gate_evidence/<sha>.json`. common dir 이라 같은 저장소의 worktree
끼리 공유된다. 호스트 밖으로는 나가지 않는다 — 발행하는 호스트가 게이트를 돌린
호스트여야 한다.
"""

from __future__ import annotations

import datetime
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

EVIDENCE_DIRNAME = "gate_evidence"
EVIDENCE_SCHEMA = 1


def _git(repo_root: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", str(repo_root), *args],
                              capture_output=True, text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def head_sha(repo_root: Path) -> str | None:
    return _git(repo_root, "rev-parse", "HEAD") or None


def tree_is_clean(repo_root: Path) -> bool | None:
    """untracked 포함 깨끗한가. git 을 못 부르면 None (모름 — 깨끗함이 아니다)."""
    out = _git(repo_root, "status", "--porcelain")
    if out is None:
        return None
    return out == ""


def evidence_dir(repo_root: Path) -> Path | None:
    common = _git(repo_root, "rev-parse", "--git-common-dir")
    if not common:
        return None
    path = Path(common)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    return path / EVIDENCE_DIRNAME


def record(repo_root: Path, sha: str, *, contexts: list[str], total: int) -> Path | None:
    """게이트 통과를 기록한다. 조건 판정은 호출자(runner) 몫이다."""
    directory = evidence_dir(repo_root)
    if directory is None:
        return None
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": EVIDENCE_SCHEMA,
        "sha": sha,
        "contexts": contexts,
        "checks_per_context": total,
        "python": platform.python_version(),
        "executable": sys.executable,
        "host": platform.node(),
        "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    path = directory / f"{sha}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def lookup(repo_root: Path, sha: str) -> dict[str, Any] | None:
    directory = evidence_dir(repo_root)
    if directory is None:
        return None
    path = directory / f"{sha}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("sha") != sha:
        return None
    return data
