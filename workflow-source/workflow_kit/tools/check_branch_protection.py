#!/usr/bin/env python3
"""branch protection check CLI — 3-layer defense 의 3rd layer (v1.1.2+, TASK-023).

TASK-019 가 1st (`claim_workspace.py` 가 `--force` 를 제공하지 않음) 와 2nd
(pre-push hook) 를 닫았다. 3rd (server-side branch protection) 는 *가이드* 로만
남았는데, 가이드는 지켜졌는지 아무도 확인하지 않는다 — 실질적으로 layer 가 둘뿐인
것과 같았다. 본 CLI 가 그 3rd layer 가 실제로 켜져 있는지 `gh api` 로 읽어서
판정한다.

## 무엇을 하지 않는가

- **보호를 켜지 않는다.** branch protection 변경은 저장소 소유자의 결정이고,
  도구가 조용히 바꿀 종류의 설정이 아니다 (§5D.4).
- **push 를 막지 않는다.** advisory 가 기본. CI 에서 게이트로 쓰려면
  `--exit-on-unprotected` 를 명시한다.
- `gh` 가 없거나 로그인이 안 돼 있으면 **graceful skip** (rc 0, `skipped: true`).
  보호 상태를 *모르는 것* 과 보호가 *없는 것* 은 다르다. CI 에서 그 구분이 필요하면
  `--require-gh` 로 없을 때 실패시킨다.

## 사용법

```bash
# 현재 저장소의 main (advisory)
wk check-branch-protection

# 다른 저장소 / 브랜치 + JSON
wk check-branch-protection \
    --repo ykylee/standard_ai_workflow --branch main --json

# CI 게이트
wk check-branch-protection --exit-on-unprotected
```

Cross-ref: `core/multi_workspace_orchestration.md` §5D.4 (b) (TASK-019 / TASK-023).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.branch_protection import evaluate_protection  # noqa: E402

GH_TIMEOUT_SECONDS = 20


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _gh_available() -> tuple[bool, str]:
    """`gh` 가 있고 인증돼 있는가. (available, reason)."""
    try:
        proc = subprocess.run(
            ["gh", "auth", "status"], capture_output=True, text=True, timeout=GH_TIMEOUT_SECONDS
        )
    except FileNotFoundError:
        return False, "gh CLI not found on PATH"
    except subprocess.TimeoutExpired:
        return False, "gh auth status timed out"
    if proc.returncode != 0:
        return False, "gh is not authenticated (`gh auth login`)"
    return True, ""


def _detect_repo() -> str | None:
    """현재 디렉터리의 GitHub repo (`owner/name`). 못 찾으면 None."""
    try:
        proc = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            capture_output=True, text=True, timeout=GH_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    name = proc.stdout.strip()
    return name if proc.returncode == 0 and name else None


def _fetch_protection(repo: str, branch: str) -> tuple[dict[str, Any] | None, bool, str]:
    """protection JSON 을 가져온다. (payload, not_found, error)."""
    try:
        proc = subprocess.run(
            ["gh", "api", f"repos/{repo}/branches/{branch}/protection"],
            capture_output=True, text=True, timeout=GH_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return None, False, "gh CLI not found on PATH"
    except subprocess.TimeoutExpired:
        return None, False, "gh api timed out"

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        # 보호 미설정이면 404. 이건 오류가 아니라 *판정 결과* 다.
        if "404" in stderr or "Branch not protected" in stderr:
            return None, True, ""
        return None, False, stderr or f"gh api exited {proc.returncode}"

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return None, False, f"JSONDecodeError: {e}"
    return (payload if isinstance(payload, dict) else None), False, ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_branch_protection",
        description="Check server-side branch protection (3-layer defense, 3rd layer).",
    )
    parser.add_argument("--repo", default=None, help="owner/name (default: 현재 저장소 자동 감지)")
    parser.add_argument("--branch", default="main", help="branch name (default: main)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "--exit-on-unprotected",
        action="store_true",
        help="보호가 불충분하면 non-zero (기본: advisory, 항상 0)",
    )
    parser.add_argument(
        "--require-gh",
        action="store_true",
        help="gh 부재/미인증을 skip 이 아니라 실패로 취급",
    )
    args = parser.parse_args(argv)

    available, reason = _gh_available()
    if not available:
        skip_payload: dict[str, Any] = {
            "ok": False,
            "skipped": True,
            "reason": reason,
            "hint": "보호 상태를 *모르는 것* 이지 보호가 *없는 것* 이 아니다.",
        }
        if args.json:
            _print_json(skip_payload)
        else:
            print(f"SKIP: {reason}")
            print("      보호 상태를 확인하지 못했다 (보호가 없다는 뜻이 아니다).")
        return 1 if args.require_gh else 0

    repo = args.repo or _detect_repo()
    if not repo:
        msg = "저장소를 감지하지 못했다 — --repo owner/name 으로 지정한다."
        if args.json:
            _print_json({"ok": False, "skipped": True, "reason": msg})
        else:
            print(f"SKIP: {msg}")
        return 1 if args.require_gh else 0

    payload, not_found, error = _fetch_protection(repo, args.branch)
    if error:
        out: dict[str, Any] = {
            "ok": False, "skipped": True, "repo": repo,
            "branch": args.branch, "reason": error,
        }
        if args.json:
            _print_json(out)
        else:
            print(f"SKIP: {error}")
        return 1 if args.require_gh else 0

    verdict = evaluate_protection(payload, not_found=not_found)
    result = {"repo": repo, "branch": args.branch, **verdict.to_dict()}

    if args.json:
        _print_json(result)
    else:
        status = "OK" if verdict.ok else "UNPROTECTED"
        print(f"{status}: {repo}@{args.branch}")
        print(f"  protected          : {verdict.protected}")
        print(f"  force_push_blocked : {verdict.force_push_blocked}")
        print(f"  deletion_blocked   : {verdict.deletion_blocked}")
        for finding in verdict.findings:
            print(f"  - {finding}")
        if verdict.advisory:
            print(f"  advisory: {verdict.advisory}")
        if not verdict.ok:
            print()
            print("  3rd layer 를 켜려면 (저장소 소유자가 직접 판단):")
            print(f"    gh api -X PUT repos/{repo}/branches/{args.branch}/protection \\")
            print("      -F allow_force_pushes=false -F allow_deletions=false ...")

    if args.exit_on_unprotected and not verdict.ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
