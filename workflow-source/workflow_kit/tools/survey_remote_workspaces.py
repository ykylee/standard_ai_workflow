#!/usr/bin/env python3
"""원격 워크스페이스 현황을 조회한다 — 표준 §10.2 의 1~3단계.

**무엇을 푸는가**: 표준 §10.2 는 세션 시작 시 (1) 원격 동기화 (2) 다른 에이전트의 진행
상황 확인 (3) 겹치지 않는 작업 선택 을 요구한다. 지금까지 이 셋은 손으로 했다. 본 도구가
1~2 를 자동화하고 3 의 판단 근거를 모아 준다.

**활성 브랜치 = 진행 중인 작업 목록**. 브랜치 선점(`git push`)이 곧 배타 획득이므로
(§5D.1 — ref 생성이 원자적), 원격 브랜치를 훑으면 누가 무엇을 잡고 있는지 알 수 있다.
별도 registry 없이 원격 저장소 자체가 현황판 역할을 한다.

## fetch 를 먼저 하는 이유 (선택 사항이 아니다)

로컬 remote-tracking ref 가 낡아 있으면 다른 호스트가 *되살린* 브랜치도 여전히 오래된
것으로 보인다 (2026-08-07 실측: fetch 전 idle=72h → fetch 후 0h). 그 상태로 stale 을
판정하면 **살아있는 작업을 지우자고 사용자에게 제안하게 된다.** 그래서 기본값으로
`git fetch --prune` 를 먼저 돌리고, 생략하려면 `--no-fetch` 를 명시해야 한다.

## stale 은 판정이 아니라 질문이다

git 은 "이 브랜치가 살아있는 작업인지" 를 모르고 **마지막 커밋 시각만** 안다. 따라서
`--stale-hours`(기본 24) 초과는 *사실* 이 아니라 *heuristic* 이다. 본 도구는 **보고만
하고 아무것도 삭제하지 않는다** — 표준 §10.4 의 "되돌릴 수 없는 작업은 에이전트가 단독
으로 결정하지 않는다". 그래서 stale 항목에는 사용자가 판단할 근거(owner / idle / 마지막
커밋 메시지 / 작업 예정 내역)를 함께 싣는다.

지표는 `%ct`(commit date)를 쓴다. `%at`(author date)는 rebase/cherry-pick 시 원본 시각을
유지하므로 *활동성* 지표로 부적합하다.

Usage:
    python3 tools/survey_remote_workspaces.py
    python3 tools/survey_remote_workspaces.py --json
    python3 tools/survey_remote_workspaces.py --no-fetch --stale-hours 48

Cross-ref: `core/global_workflow_standard.md` §10.2 · §10.4,
`core/multi_workspace_orchestration.md` §5D.3 (조회) · §5D.4a (stale 임계).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.paths import branch_slug_for  # noqa: E402

DEFAULT_STALE_HOURS = 24
# 워크스페이스 브랜치가 아닌 것 (통합 브랜치 / 심볼릭 ref)
NON_WORKSPACE = {"HEAD", "main", "master"}
# 작업 예정 내역을 찾을 후보 경로 (seed 도구가 만드는 자리)
PLAN_GLOB = "ai-workflow/memory/active/{branch}/session_handoff.md"


def _git(args: list[str], *, repo_root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(repo_root),
                          capture_output=True, text=True)


def fetch_remote(*, repo_root: Path, remote: str) -> str | None:
    """`git fetch --prune`. 실패 시 에러 문자열 반환 (조회는 계속하되 경고)."""
    proc = _git(["fetch", remote, "--prune"], repo_root=repo_root)
    if proc.returncode != 0:
        return proc.stderr.strip() or f"git fetch {remote} 실패"
    return None


def remote_branches(*, repo_root: Path, remote: str) -> list[str]:
    """워크스페이스 브랜치 이름 목록.

    `%(symref)` 가 비어 있지 않은 항목은 심볼릭 ref (`origin` → `origin/main`) 이므로
    제외한다. 이걸 걸러내지 않으면 `origin` 자체가 브랜치로 잡혀 "커밋 정보를 읽지
    못했다" 경고가 매번 뜬다 (실측).
    """
    proc = _git(["for-each-ref", "--format=%(refname:short)%09%(symref)",
                 f"refs/remotes/{remote}"], repo_root=repo_root)
    if proc.returncode != 0:
        return []
    names = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        short, _, symref = line.partition("\t")
        if symref.strip():
            continue
        short = short.strip()
        name = short[len(remote) + 1:] if short.startswith(f"{remote}/") else short
        if not name or name in NON_WORKSPACE:
            continue
        names.append(name)
    return sorted(names)


def branch_info(name: str, *, repo_root: Path, remote: str) -> dict:
    ref = f"{remote}/{name}"
    proc = _git(["log", "-1", "--format=%ct%x00%an%x00%s", ref], repo_root=repo_root)
    if proc.returncode != 0 or not proc.stdout.strip():
        return {"branch": name, "error": "커밋 정보를 읽지 못했다"}
    ts_raw, author, subject = proc.stdout.strip().split("\x00", 2)
    return {
        "branch": name,
        "owner": author,
        "last_commit_at": int(ts_raw),
        "last_commit_subject": subject,
    }


def read_plan(name: str, *, repo_root: Path, remote: str) -> str | None:
    """체크아웃 없이 원격 브랜치의 작업 예정 내역(handoff 의 축)을 읽는다."""
    path = PLAN_GLOB.format(branch=name)
    proc = _git(["show", f"{remote}/{name}:{path}"], repo_root=repo_root)
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("- 현재 주 작업 축:"):
            return stripped.split(":", 1)[1].strip()
    return None


def survey(*, repo_root: Path, remote: str, stale_hours: int, do_fetch: bool,
           now: int | None = None) -> dict:
    warnings: list[str] = []
    fetched = False
    if do_fetch:
        err = fetch_remote(repo_root=repo_root, remote=remote)
        if err:
            warnings.append(f"fetch 실패 — 낡은 정보로 판단할 수 있다: {err}")
        else:
            fetched = True
    else:
        warnings.append(
            "--no-fetch: 원격 정보가 낡았을 수 있다. 되살아난 브랜치를 stale 로 오판할 수 있으므로 "
            "stale 항목을 근거로 삭제를 제안하지 않는다."
        )

    now = int(time.time()) if now is None else now
    threshold = stale_hours * 3600
    # `get_current_branch()` 가 아니다 — 그건 *이 모듈이 속한* 저장소를 본다.
    # `--repo-root` 로 다른 저장소를 지목한 호출에서 `is_current` / `current_branch`
    # 가 엉뚱한 브랜치를 가리키던 자리 (audit_root_anchors R3).
    current = branch_slug_for(repo_root)

    active: list[dict] = []
    stale: list[dict] = []
    for name in remote_branches(repo_root=repo_root, remote=remote):
        info = branch_info(name, repo_root=repo_root, remote=remote)
        if "error" in info:
            warnings.append(f"{name}: {info['error']}")
            continue
        idle = max(0, now - info["last_commit_at"])
        info["idle_hours"] = idle // 3600
        info["is_current"] = name == current
        info["plan"] = read_plan(name, repo_root=repo_root, remote=remote)
        info.pop("last_commit_at", None)
        (stale if idle > threshold else active).append(info)

    return {
        "status": "ok",
        "remote": remote,
        "fetched": fetched,
        "current_branch": current,
        "stale_hours": stale_hours,
        "active": active,
        "stale": stale,
        "warnings": warnings,
        # stale 은 삭제 대상이 아니라 사용자에게 물어볼 목록이다 (표준 §10.4).
        "action_required": (
            f"{len(stale)}건은 {stale_hours}시간 이상 활동이 없다. 삭제·선점 전에 사용자에게 확인한다."
            if stale else None
        ),
    }


def _render(result: dict) -> None:
    print(f"=== 원격 워크스페이스 현황 ({result['remote']}) — 현재 브랜치: {result['current_branch']} ===")
    if not result["fetched"]:
        print("  [warn] fetch 하지 않았다 — 아래 정보는 낡았을 수 있다")
    print()
    print(f"  진행 중 ({len(result['active'])}건):")
    if not result["active"]:
        print("    (없음)")
    for b in result["active"]:
        mark = " *" if b["is_current"] else "  "
        print(f"   {mark} {b['branch']:<24} owner={b['owner']:<12} idle={b['idle_hours']:>3}h")
        if b.get("plan"):
            print(f"        축: {b['plan']}")
    if result["stale"]:
        print()
        print(f"  활동 없음 {result['stale_hours']}h+ ({len(result['stale'])}건) — 삭제하지 않는다, 사용자 확인 대상:")
        for b in result["stale"]:
            print(f"      {b['branch']:<24} owner={b['owner']:<12} idle={b['idle_hours']:>3}h")
            print(f"        마지막: {b['last_commit_subject']}")
            if b.get("plan"):
                print(f"        축: {b['plan']}")
    for w in result["warnings"]:
        print(f"\n  [warn] {w}")
    if result["action_required"]:
        print(f"\n  → {result['action_required']}")


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo-root", default=str(REPO_ROOT))
    p.add_argument("--remote", default="origin")
    p.add_argument("--stale-hours", type=int, default=DEFAULT_STALE_HOURS,
                   help=f"이 시간을 넘게 활동이 없으면 사용자 확인 대상 (default: {DEFAULT_STALE_HOURS})")
    p.add_argument("--no-fetch", action="store_true",
                   help="fetch 를 건너뛴다 (낡은 정보로 판단할 위험이 있다)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    result = survey(
        repo_root=Path(args.repo_root).resolve(), remote=args.remote,
        stale_hours=args.stale_hours, do_fetch=not args.no_fetch,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _render(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
