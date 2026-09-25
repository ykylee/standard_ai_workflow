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

## 읽는 곳 (둘)

- 발행: `release --apply` 가 HEAD 의 기록을 요구한다 (`release_pipeline.verify_gate_evidence`).
- push: `.githooks/pre-push` 가 push 하는 각 ref 의 sha 기록을 요구한다
  (:func:`check_push`, TASK-2026-09-23-main-009). 86차 `f4504818` 은 게이트를 돈 **뒤**
  CLAUDE.md 를 고쳐 게이트 없이 push 됐고, 스탬프 위반이 CI 에서만 드러났다 — 로컬
  green 은 다른 sha 의 green 이었다. CI 가 없는 지금은 그 커밋을 아무도 안 잰다.
  우회는 `git push --no-verify` (쓰면 그 push 는 게이트 근거가 없다).
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


def missing_contexts(evidence: dict[str, Any]) -> list[str]:
    """기록에 빠진 브랜치 컨텍스트. 정본은 `branch_matrix.BRANCH_CONTEXTS` — 발행과 push 가 같이 쓴다."""
    from workflow_kit.common.branch_matrix import labels

    have = evidence.get("contexts") or []
    return [c for c in labels() if c not in have]


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


_ZERO = frozenset("0")


def _is_zero_sha(sha: str) -> bool:
    return bool(sha) and set(sha) <= _ZERO


def check_push(repo_root: Path, lines: list[str]) -> list[str]:
    """pre-push 표준입력(`<local ref> <local sha> <remote ref> <remote sha>`)을 판정한다.

    반환은 막을 사유 목록 — 비면 통과. ref 마다 **tip sha** 하나를 본다 (게이트는
    push 직전 HEAD 에서 돈다). 삭제 push(local sha 가 0)는 올리는 것이 없으니 통과.
    태그는 가리키는 커밋으로 벗긴다. **모름은 통과가 아니다** — sha 를 못 벗기면 막는다.
    """
    problems: list[str] = []
    for raw in lines:
        parts = raw.split()
        if len(parts) != 4:
            continue
        local_ref, local_sha, remote_ref, _remote_sha = parts
        if _is_zero_sha(local_sha):
            continue
        commit = _git(repo_root, "rev-parse", "--verify", "--quiet", f"{local_sha}^{{commit}}")
        if not commit:
            problems.append(f"{local_ref} → {remote_ref}: {local_sha[:8]} 를 커밋으로 읽지 못했다")
            continue
        evidence = lookup(repo_root, commit)
        if evidence is None:
            problems.append(
                f"{local_ref} → {remote_ref}: {commit[:8]} 에 게이트 통과 기록이 없다")
            continue
        missing = missing_contexts(evidence)
        if missing:
            problems.append(
                f"{local_ref} → {remote_ref}: {commit[:8]} 의 게이트 기록에 컨텍스트가 빠졌다 {missing}")
    return problems


def main(argv: list[str] | None = None) -> int:
    """`python -m workflow_kit.common.gate_evidence pre-push <repo_root>` — hook 진입점."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2 or args[0] != "pre-push":
        print("usage: python -m workflow_kit.common.gate_evidence pre-push <repo_root>",
              file=sys.stderr)
        return 2
    problems = check_push(Path(args[1]), sys.stdin.read().splitlines())
    if not problems:
        return 0
    print("[pre-push] 게이트를 돌지 않은 커밋은 push 하지 않는다 (TASK-2026-09-23-main-009):",
          file=sys.stderr)
    for item in problems:
        print(f"  - {item}", file=sys.stderr)
    print("  커밋 후 깨끗한 트리에서 `run_all_checks.py --branch-context=all` 을 돌린다. "
          "정말 넘겨야 하면 `git push --no-verify`.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
