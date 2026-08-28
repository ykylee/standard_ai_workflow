#!/usr/bin/env python3
"""워크스페이스를 선점한다 — 표준 §10.2 의 4~5단계 (브랜치 + seed + 1회 push).

**push 가 곧 배타 획득이다.** git 의 ref 생성은 원자적이라, 여러 호스트가 같은 브랜치명을
동시에 밀면 **정확히 1명만 성공**한다 (2026-08-07 실측: 5-way 경합 → 1 성공 / 4 거부).
별도 lease 파일도 registry 도 필요 없다 — 원격 저장소가 단일 판정자다.

## rejected 는 장애가 아니라 신호다

push 가 거부됐다는 것은 **다른 에이전트가 이미 그 작업을 가져갔다**는 뜻이다. 뚫어야 할
문제가 아니므로 본 도구는:

- **재시도하지 않는다.**
- **`--force` 를 제공하지 않는다.** 배타성이 규약일 뿐 강제가 아니어서(§5D.4b 실측:
  `--force` 는 남의 브랜치를 덮어쓴다), 도구가 그 수단을 갖고 있으면 언젠가 쓰인다.
  강제로 밀어야 한다면 사람이 직접, 확인을 거쳐서 한다.
- 대신 **누가 가져갔는지**(owner / 축)를 보여 주고 다른 작업을 고르라고 안내한다.

## 어디까지 자동으로 하는가

`--apply` 없이는 아무것도 하지 않는다. `--apply` 를 줘도 **로컬 작업(브랜치·seed·commit)
까지만** 하고, 네트워크로 나가는 push 는 마지막 한 번뿐이다. 실패하면 로컬 브랜치는
남으므로 사용자가 상태를 확인할 수 있다 — 조용히 되돌려 흔적을 지우지 않는다.

Usage:
    wk claim-workspace --branch feat-login \\
        --axis "로그인 세션 만료 처리" --task-title "세션 만료 시 재인증" --dry-run
    wk claim-workspace --branch feat-login \\
        --axis "..." --task-title "..." --apply

Cross-ref: `core/global_workflow_standard.md` §10.2 · §10.4,
`core/multi_workspace_orchestration.md` §5D.1 (원자성) · §5D.5 (플로우).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.child_process import child_env, module_command  # noqa: E402
from workflow_kit.common.paths import (  # noqa: E402
    memory_dir_for_workspace,
    resolve_workspace_root,
)

#: seed 도구는 **모듈로** 부른다 — 설치본에는 `workflow-source/` 디렉터리가 없다.
SEED_MODULE = "workflow_kit.tools.seed_workspace_memory"


def _git(args: list[str], *, repo_root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(repo_root),
                          capture_output=True, text=True)


def remote_branch_exists(branch: str, *, repo_root: Path, remote: str) -> bool:
    proc = _git(["ls-remote", "--heads", remote, f"refs/heads/{branch}"],
                repo_root=repo_root)
    return proc.returncode == 0 and bool(proc.stdout.strip())


def holder_of(branch: str, *, repo_root: Path, remote: str) -> dict:
    """이미 선점된 브랜치의 소유자 정보 (있으면)."""
    _git(["fetch", remote, branch, "--quiet"], repo_root=repo_root)
    proc = _git(["log", "-1", "--format=%an%x00%s", "FETCH_HEAD"], repo_root=repo_root)
    if proc.returncode != 0 or not proc.stdout.strip():
        return {}
    owner, _, subject = proc.stdout.strip().partition("\x00")
    return {"owner": owner, "last_commit_subject": subject}


def claim(*, repo_root: Path, remote: str, branch: str, axis: str,
          task_title: str, out_of_scope: str | None, base: str,
          today: str, apply: bool,
          harness: str | None = None,
          endpoint: str | None = None,
          no_register: bool = False) -> dict:
    result: dict = {
        "status": "ok",
        "mode": "apply" if apply else "dry-run",
        "branch": branch,
        "remote": remote,
        "claimed": False,
        "steps": [],
        "warnings": [],
    }

    # --- 사전 확인: 이미 선점됐는가 (힌트일 뿐, 판정은 push 가 한다) --------
    if remote_branch_exists(branch, repo_root=repo_root, remote=remote):
        result["status"] = "already_claimed"
        result["holder"] = holder_of(branch, repo_root=repo_root, remote=remote)
        result["next_action"] = (
            "다른 에이전트가 이미 이 작업을 가져갔다. 다른 작업을 고른다 "
            "(survey_remote_workspaces.py 로 현황 재확인). --force 로 뚫지 않는다."
        )
        return result

    plan = [
        f"git checkout -b {branch} ({base} 기준)",
        f"seed_workspace_memory.py --branch {branch} --apply",
        "git add -A && git commit (작업 예정 내역)",
        f"git push {remote} {branch}   ← 이 push 가 배타 획득",
    ]
    result["steps"] = plan
    if not apply:
        result["next_action"] = "실제 선점: --apply"
        return result

    # --- 1) 브랜치 생성 ---------------------------------------------------
    proc = _git(["checkout", "-b", branch, base], repo_root=repo_root)
    if proc.returncode != 0:
        result["status"] = "error"
        result["error"] = f"브랜치 생성 실패: {proc.stderr.strip()}"
        return result

    # --- 2) 메모리 seed ---------------------------------------------------
    # seed 가 성공하면 자기 자신을 workspace registry 에 self-register 한다
    # (TASK-2026-08-08-main-008, §5A.3 정합). WORKFLOW_HARNESS / WORKFLOW_ENDPOINT
    # env 가 있으면 seed 가 그대로 채워 넣는다. claim 측에서도 명시적
    # --harness / --endpoint forwarding 허용.
    # 환경은 **좁힌 채로** 시작하고(base), PYTHONPATH 만 helper 가 얹는다.
    forwarded = {
        # 보안: 호출자 작업 디렉터리 컨텍스트 registry 가 그대로 쓰도록
        # WORKFLOW_REGISTRY_PATH / WORKFLOW_HOST_ID 는 *덮어쓰지 않는다*.
        k: os.environ[k]
        for k in ("WORKFLOW_REGISTRY_PATH", "WORKFLOW_HOST_ID",
                  "WORKFLOW_HARNESS", "WORKFLOW_ENDPOINT")
        if k in os.environ
    }
    seed_env = child_env(
        {"PATH": "/usr/bin:/bin:/usr/local/bin", **forwarded}, base={},
    )
    seed_args = module_command(
        SEED_MODULE,
        "--memory-root", str(memory_dir_for_workspace(repo_root)),
        "--branch", branch, "--axis", axis, "--task-title", task_title,
        "--today", today, "--apply", "--json",
    )
    if out_of_scope:
        seed_args += ["--out-of-scope", out_of_scope]
    if harness:
        seed_args += ["--harness", harness]
    if endpoint:
        seed_args += ["--endpoint", endpoint]
    if no_register:
        seed_args += ["--no-register"]
    seed_proc = subprocess.run(seed_args, capture_output=True, text=True,
                               env=seed_env)
    if seed_proc.returncode != 0:
        result["status"] = "error"
        result["error"] = f"seed 실패: {seed_proc.stderr.strip()}"
        return result
    try:
        result["task_id"] = json.loads(seed_proc.stdout).get("task_id")
    except json.JSONDecodeError:
        result["warnings"].append("seed 출력에서 task_id 를 읽지 못했다")

    # --- 3) commit --------------------------------------------------------
    _git(["add", "-A"], repo_root=repo_root)
    msg = f"chore(workspace): {branch} 선점 — {axis}"
    proc = _git(["commit", "-m", msg], repo_root=repo_root)
    if proc.returncode != 0:
        result["status"] = "error"
        result["error"] = f"commit 실패: {proc.stdout.strip() or proc.stderr.strip()}"
        return result

    # --- 4) push = 배타 획득 ----------------------------------------------
    proc = _git(["push", remote, branch], repo_root=repo_root)
    if proc.returncode != 0:
        # 여기서 지는 것이 정상 경로다. 되돌리지 않고 사실만 보고한다.
        result["status"] = "lost_race"
        result["holder"] = holder_of(branch, repo_root=repo_root, remote=remote)
        result["next_action"] = (
            "push 가 거부됐다 — 그 사이 다른 에이전트가 선점했다. 다른 작업을 고른다. "
            f"로컬 브랜치 `{branch}` 는 남겨 두었으니 확인 후 정리한다. "
            "--force 로 뚫지 않는다 (표준 §10.4 — 사용자 확인 필요)."
        )
        result["push_stderr"] = proc.stderr.strip()[:400]
        return result

    result["claimed"] = True
    result["next_action"] = (
        "선점 완료. state.json 을 생성한 뒤 작업을 시작한다: "
        "generate_workflow_state.py --project-profile-path docs/PROJECT_PROFILE.md "
        f"--output-path ai-workflow/memory/active/{branch}/state.json"
    )
    return result


def _render(r: dict) -> None:
    if r["status"] == "already_claimed":
        h = r.get("holder") or {}
        print(f"=== 이미 선점됨: {r['branch']} ===")
        if h:
            print(f"  owner: {h.get('owner')}")
            print(f"  마지막: {h.get('last_commit_subject')}")
        print(f"\n  → {r['next_action']}")
        return
    if r["status"] == "lost_race":
        h = r.get("holder") or {}
        print(f"=== 경합에서 졌다: {r['branch']} ===")
        if h:
            print(f"  선점자: {h.get('owner')} — {h.get('last_commit_subject')}")
        print(f"\n  → {r['next_action']}")
        return
    if r["status"] == "error":
        print(f"[error] {r.get('error')}")
        return

    print(f"=== 워크스페이스 선점 ({r['mode']}) — {r['branch']} ===")
    for i, step in enumerate(r["steps"], 1):
        print(f"  {i}. {step}")
    if r["claimed"]:
        print(f"\n  선점 완료 (task: {r.get('task_id')})")
    print(f"\n  → {r['next_action']}")


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo-root", default=None,
                   help="대상 저장소 (default: cwd 에서 해석)")
    p.add_argument("--remote", default="origin")
    p.add_argument("--branch", required=True)
    p.add_argument("--axis", required=True, help="주 작업 축 — 이게 곧 업무 지시다")
    p.add_argument("--task-title", required=True)
    p.add_argument("--out-of-scope", default=None)
    p.add_argument("--base", default="HEAD", help="브랜치를 딸 기준 (default: HEAD)")
    p.add_argument("--today", default=date.today().isoformat())
    p.add_argument("--apply", action="store_true", help="실제 선점 (default: dry-run)")
    p.add_argument("--dry-run", action="store_true", dest="dry_run")
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--no-register",
        action="store_true",
        help=(
            "seed 가 성공해도 workspace_registry 에 self-register 하지 않는다. "
            "CI / 격리 / 회사 정책 등. 기본은 register."
        ),
    )
    p.add_argument(
        "--harness",
        default=None,
        help="registry entry 의 harness 필드 (env WORKFLOW_HARNESS 도 가능).",
    )
    p.add_argument(
        "--endpoint",
        default=None,
        help="registry entry 의 endpoint 필드 (env WORKFLOW_ENDPOINT 도 가능).",
    )
    args = p.parse_args()
    if args.dry_run:
        args.apply = False

    # 무인자 기본값은 **cwd 의 작업 저장소**에서 해석한다 — 모듈 위치가 아니라
    # (TASK-2026-08-28-main-013, `resolve_workspace_root` docstring 의 결함족).
    repo_root, path_source = (
        (Path(args.repo_root).resolve(), "explicit") if args.repo_root
        else resolve_workspace_root()
    )

    result = claim(
        repo_root=repo_root, remote=args.remote,
        harness=args.harness, endpoint=args.endpoint,
        no_register=args.no_register,
        branch=args.branch, axis=args.axis, task_title=args.task_title,
        out_of_scope=args.out_of_scope, base=args.base, today=args.today,
        apply=args.apply,
    )
    # 무엇을 대상으로 골랐는지 결과에 남긴다 — 폴백은 조용히 하지 않는다.
    result["repo_root"] = str(repo_root)
    result["path_source"] = path_source
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _render(result)
    # 경합에서 지는 것은 정상 경로이므로 0. 진짜 오류만 1.
    return 1 if result["status"] == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
