#!/usr/bin/env python3
r"""Smoke test — `tools/claim_workspace.py` (9 assertions).

## 왜 이 검사가 필요한가

본 도구는 **네트워크로 쓰기를 수행**하고, 그 push 가 곧 배타 획득이다. 따라서 검사는
"돌아가는가" 가 아니라 **안전 성질**을 본다:

- 여러 에이전트가 동시에 밀면 **정확히 1명만** 성공하는가 (배타성이 실제로 성립하는가)
- 진 쪽이 **남의 브랜치를 덮어쓰지 않는가**
- 진 쪽의 로컬 작업을 **조용히 지우지 않는가** (사용자가 상태를 확인할 수 있어야 한다)
- **`--force` 수단 자체가 없는가** — 도구가 그 수단을 갖고 있으면 언젠가 쓰인다.
  표준 §10.4 는 되돌릴 수 없는 작업을 에이전트 단독 결정에서 배제한다.

case 3(동시 경합)이 핵심이다. 배타성이 깨지면 두 에이전트가 같은 작업을 동시에 하게
되고, 그건 이 워크플로우 전체의 전제가 무너지는 것이다.

9 assertions:
  1) dry-run 은 브랜치도 커밋도 만들지 않는다
  2) 이미 선점된 브랜치는 소유자를 알려주고 아무것도 하지 않는다
  3) **동시 경합에서 정확히 1명만 성공한다**
  4) 승자의 seed 가 원격에 온전히 올라간다
  5) 진 쪽은 lost_race 로 보고하고 선점자를 알려준다
  6) 진 쪽의 로컬 브랜치가 보존된다 (조용히 삭제하지 않는다)
  7) 원격 브랜치가 승자의 것으로 유지된다 (덮어쓰기 없음)
  8) 승자는 곧바로 session-start 로 이어받을 수 있다
  9) **소스에 force push 수단이 없다**

Refs:
  - core/global_workflow_standard.md §10.2 · §10.4
  - core/multi_workspace_orchestration.md §5D.1 (원자성) · §5D.5 (플로우)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
sys.path.insert(0, str(SOURCE_ROOT))

CLAIM = SOURCE_ROOT / "workflow_kit" / "tools" / "claim_workspace.py"
SESSION_START = SOURCE_ROOT / "skills" / "session-start" / "scripts" / "run_session_start.py"
PROFILE = REPO_ROOT / "docs" / "PROJECT_PROFILE.md"

BRANCH = "feat-contested"
TODAY = date.today().isoformat()
ENV = {"PYTHONPATH": str(SOURCE_ROOT), "PATH": "/usr/bin:/bin:/usr/local/bin"}

FAILURES: list[str] = []


def _record(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + ("" if ok else f" — {detail}"))
    if not ok:
        FAILURES.append(name)


def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    env = {**ENV, "HOME": str(cwd),
           "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@t"}
    proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                          text=True, env=env)
    if check:
        assert proc.returncode == 0, f"git {' '.join(args)}: {proc.stderr}"
    return proc


def _claim(repo: Path, *, axis: str, apply: bool, name: str = "agent") -> dict:
    args = [sys.executable, str(CLAIM), "--repo-root", str(repo),
            "--branch", BRANCH, "--axis", axis, "--task-title", axis,
            "--today", TODAY, "--json"]
    args.append("--apply" if apply else "--dry-run")
    proc = subprocess.run(args, capture_output=True, text=True,
                          env={**ENV, "HOME": str(repo),
                               "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": f"{name}@t",
                               "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": f"{name}@t"})
    assert proc.stdout.strip(), f"claim 출력 없음: {proc.stderr}"
    return json.loads(proc.stdout)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bare = root / "o.git"
        bare.mkdir()
        _git(["init", "-q", "--bare", "."], bare)

        seed = root / "seed"
        _git(["clone", "-q", str(bare), str(seed)], root)
        (seed / "docs").mkdir(parents=True)
        (seed / "docs" / "f.md").write_text("base\n", encoding="utf-8")
        _git(["add", "-A"], seed)
        _git(["commit", "-qm", "base"], seed)
        _git(["branch", "-M", "main"], seed)
        _git(["push", "-q", "origin", "main"], seed)

        agents = []
        for i in range(1, 5):
            a = root / f"a{i}"
            _git(["clone", "-q", "-b", "main", str(bare), str(a)], root)
            agents.append(a)

        # --- 1: dry-run 은 아무것도 만들지 않는다 --------------------------
        dry = _claim(agents[0], axis="dry", apply=False)
        branches = _git(["branch", "--list", BRANCH], agents[0]).stdout.strip()
        _record("test_dry_run_creates_nothing",
                dry["mode"] == "dry-run" and not dry["claimed"] and not branches,
                f"claimed={dry['claimed']} local_branch={branches!r}")

        # --- 3: 동시 경합 → 정확히 1명 -------------------------------------
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(
                lambda t: _claim(t[1], axis=f"경합 축 {t[0]}", apply=True,
                                 name=f"agent{t[0]}"),
                [(i + 1, a) for i, a in enumerate(agents)],
            ))
        winners = [r for r in results if r.get("claimed")]
        losers = [r for r in results if r.get("status") in ("lost_race", "already_claimed")]
        _record("test_exactly_one_winner", len(winners) == 1,
                f"winners={len(winners)} statuses={[r['status'] for r in results]}")
        _record("test_others_lose_cleanly", len(losers) == 3,
                f"losers={len(losers)}")

        if len(winners) != 1:
            print("\n=== FAIL: 배타성이 깨졌다 — 이후 검사 생략 ===")
            return 1

        win_idx = results.index(winners[0])
        win_repo = agents[win_idx]
        win_axis = f"경합 축 {win_idx + 1}"

        # --- 5: 진 쪽이 선점자를 알려준다 ----------------------------------
        _record("test_loser_reports_holder",
                all((r.get("holder") or {}).get("owner") for r in losers),
                f"holders={[r.get('holder') for r in losers]}")

        # --- 6: 진 쪽 로컬 브랜치 보존 -------------------------------------
        lose_idx = next(i for i in range(4) if i != win_idx)
        kept = _git(["branch", "--list", BRANCH], agents[lose_idx]).stdout.strip()
        _record("test_loser_local_branch_preserved", bool(kept),
                "진 쪽의 로컬 브랜치가 사라졌다")

        # --- 4 & 7: 원격은 승자의 것 --------------------------------------
        _git(["fetch", "origin", "--prune", "-q"], win_repo)
        show = _git(["show", f"origin/{BRANCH}:ai-workflow/memory/active/"
                     f"{BRANCH}/session_handoff.md"], win_repo, check=False)
        _record("test_winner_seed_on_remote",
                show.returncode == 0 and win_axis in show.stdout,
                f"rc={show.returncode}")
        heads = _git(["ls-remote", "--heads", str(bare)], win_repo).stdout
        _record("test_remote_has_single_claim",
                heads.count(f"refs/heads/{BRANCH}") == 1,
                f"heads={heads!r}")

        # --- 2: 이미 선점된 브랜치 재시도 ----------------------------------
        again = _claim(agents[lose_idx], axis="다시", apply=False)
        _record("test_already_claimed_detected",
                again["status"] == "already_claimed"
                and (again.get("holder") or {}).get("owner"),
                f"status={again['status']}")

        # --- 8: 승자는 바로 이어받는다 -------------------------------------
        started = subprocess.run(
            [sys.executable, str(SESSION_START),
             "--session-handoff-path",
             str(win_repo / "ai-workflow" / "memory" / "active" / BRANCH / "session_handoff.md"),
             "--work-backlog-index-path",
             str(win_repo / "ai-workflow" / "memory" / "active" / BRANCH / "backlog" / f"{TODAY}.md"),
             "--project-profile-path", str(PROFILE)],
            capture_output=True, text=True, env=ENV,
        )
        payload = json.loads(started.stdout)
        _record("test_winner_can_start_session",
                payload.get("status") == "ok" and not payload.get("warnings"),
                f"status={payload.get('status')} warnings={payload.get('warnings')}")

        # --- 9: force push 수단이 없다 -------------------------------------
        # "--force 로 뚫지 않는다" 같은 *안내 문구* 는 정상이므로, git 인자 리스트에
        # force 가 들어가는지만 본다 — `_git([...])` / `["push", ...]` 형태.
        src = CLAIM.read_text(encoding="utf-8")
        git_calls = re.findall(r"_git\(\s*\[(.*?)\]", src, re.S)
        forced = [c for c in git_calls
                  if "--force" in c or "+refs" in c or "-f\"" in c or "'-f'" in c]
        _record("test_no_force_push_capability", not forced,
                f"force 를 쓰는 git 호출: {forced}")

    print()
    if FAILURES:
        print(f"=== FAIL: {len(FAILURES)} case(s) — {FAILURES} ===")
        return 1
    print("=== PASS: claim_workspace smoke (9 assertions) ===")
    return 0


def test_claim_workspace() -> None:
    assert main() == 0, "claim_workspace smoke FAIL"


if __name__ == "__main__":
    raise SystemExit(main())
