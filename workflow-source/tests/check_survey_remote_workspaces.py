#!/usr/bin/env python3
r"""Smoke test — `tools/survey_remote_workspaces.py` (8 assertions).

## 왜 이 검사가 필요한가

본 도구의 출력은 **사용자에게 "이 브랜치 지울까요?" 를 묻는 근거**가 된다. 근거가
틀리면 살아있는 작업을 지우자고 제안하게 된다. 그래서 검사는 "돌아가는가" 가 아니라
**"판정이 맞는가"** 를 본다.

특히 stale 오판은 2026-08-07 에 실측으로 확인된 실패 경로다 — 다른 호스트가 브랜치를
되살렸는데 로컬 remote-tracking ref 가 낡아 있으면 여전히 오래된 것으로 보인다.
case 4~5 가 이 경로를 정면으로 재현한다 (bare remote + 두 번째 클론).

또 하나: `for-each-ref` 는 심볼릭 ref(`origin` → `origin/main`)도 함께 내놓는다.
이걸 거르지 않으면 `origin` 자체가 브랜치로 잡혀 매번 경고가 뜬다 (초안에서 실제로
발생). case 2 가 이를 고정한다.

8 assertions:
  1) 워크스페이스 브랜치만 나온다 (main/HEAD/심볼릭 ref 제외)
  2) 심볼릭 ref 때문에 경고가 생기지 않는다
  3) idle 시간으로 active / stale 이 갈린다 (임계 경계)
  4) --stale-hours 로 임계를 조정할 수 있다
  5) **fetch 없이는 되살아난 브랜치를 stale 로 오판한다** (실패 재현 + 경고 존재)
  6) **fetch 하면 오판이 교정된다**
  7) 체크아웃 없이 작업 예정 내역(축)을 읽는다
  8) stale 이 있어도 삭제하지 않고 사용자 확인을 요구한다 (표준 §10.4)

Refs:
  - core/global_workflow_standard.md §10.2 · §10.4
  - core/multi_workspace_orchestration.md §5D.3 · §5D.4a
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
sys.path.insert(0, str(SOURCE_ROOT))

SURVEY = SOURCE_ROOT / "workflow_kit" / "tools" / "survey_remote_workspaces.py"
SEED = SOURCE_ROOT / "workflow_kit" / "tools" / "seed_workspace_memory.py"

FAILURES: list[str] = []


def _record(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + ("" if ok else f" — {detail}"))
    if not ok:
        FAILURES.append(name)


def _git(args: list[str], cwd: Path, **env_extra: str) -> None:
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(cwd),
        "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@t",
        **env_extra,
    }
    proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                          text=True, env=env)
    assert proc.returncode == 0, f"git {' '.join(args)} 실패: {proc.stderr}"


def _survey(repo: Path, *, no_fetch: bool = False, stale_hours: int | None = None) -> dict:
    args = [sys.executable, str(SURVEY), "--repo-root", str(repo), "--json"]
    if no_fetch:
        args.append("--no-fetch")
    if stale_hours is not None:
        args += ["--stale-hours", str(stale_hours)]
    proc = subprocess.run(args, capture_output=True, text=True,
                          env={"PYTHONPATH": str(SOURCE_ROOT),
                               "PATH": "/usr/bin:/bin:/usr/local/bin"})
    assert proc.returncode == 0, f"survey 실패: {proc.stderr}"
    return json.loads(proc.stdout)


def _names(items: list[dict]) -> set[str]:
    return {b["branch"] for b in items}


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bare = root / "o.git"
        work = root / "w"
        bare.mkdir()
        _git(["init", "-q", "--bare", "."], bare)
        _git(["clone", "-q", str(bare), str(work)], root)
        (work / "docs").mkdir(parents=True)
        (work / "docs" / "f.md").write_text("base\n", encoding="utf-8")
        _git(["add", "-A"], work)
        _git(["commit", "-qm", "base"], work)
        _git(["branch", "-M", "main"], work)
        _git(["push", "-q", "origin", "main"], work)

        now = int(time.time())
        # (branch, hours_ago, owner, axis)
        specs = [
            ("feat-alpha", 0, "Alice", "로그인 세션 만료"),
            ("feat-beta", 12, "Bob", "결제 재시도"),
            ("feat-dead", 100, "Carol", "오래된 리팩터링"),
        ]
        for branch, hours, owner, axis in specs:
            _git(["checkout", "-q", "main"], work)
            _git(["checkout", "-qb", branch], work)
            subprocess.run(
                [sys.executable, str(SEED), "--memory-root",
                 str(work / "ai-workflow" / "memory"), "--branch", branch,
                 "--axis", axis, "--task-title", axis, "--apply"],
                capture_output=True, text=True,
                env={"PYTHONPATH": str(SOURCE_ROOT), "PATH": "/usr/bin:/bin:/usr/local/bin"},
                check=True,
            )
            stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now - hours * 3600))
            _git(["add", "-A"], work)
            _git(["commit", "-qm", f"{owner}: {axis}"], work,
                 GIT_AUTHOR_NAME=owner, GIT_COMMITTER_NAME=owner,
                 GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
            _git(["push", "-q", "origin", branch], work)
        _git(["checkout", "-q", "main"], work)

        # --- 1~2: 워크스페이스 브랜치만, 잡음 없음 ------------------------
        r = _survey(work)
        seen = _names(r["active"]) | _names(r["stale"])
        _record("test_only_workspace_branches", seen == {"feat-alpha", "feat-beta", "feat-dead"},
                f"branches={seen}")
        _record("test_no_symref_noise", not r["warnings"], f"warnings={r['warnings']}")

        # --- 3: 임계로 active / stale 이 갈린다 ---------------------------
        _record("test_active_stale_split",
                _names(r["active"]) == {"feat-alpha", "feat-beta"}
                and _names(r["stale"]) == {"feat-dead"},
                f"active={_names(r['active'])} stale={_names(r['stale'])}")

        # --- 4: 임계 조정 --------------------------------------------------
        wide = _survey(work, stale_hours=200)
        _record("test_stale_hours_configurable", not wide["stale"],
                f"stale={_names(wide['stale'])}")

        # --- 7: 체크아웃 없이 축을 읽는다 ----------------------------------
        alpha = next(b for b in r["active"] if b["branch"] == "feat-alpha")
        _record("test_reads_plan_without_checkout", alpha.get("plan") == "로그인 세션 만료",
                f"plan={alpha.get('plan')!r}")

        # --- 8: stale 은 삭제가 아니라 질문 --------------------------------
        _record("test_stale_requires_user_confirmation",
                bool(r["action_required"]) and "사용자" in r["action_required"],
                f"action_required={r['action_required']!r}")

        # --- 5~6: 되살아난 브랜치 오판 재현 / 교정 -------------------------
        other = root / "other"
        _git(["clone", "-q", "-b", "main", str(bare), str(other)], root)
        _git(["checkout", "-q", "-b", "feat-dead", "origin/feat-dead"], other)
        (other / "docs" / "f.md").write_text("revived\n", encoding="utf-8")
        _git(["commit", "-qam", "Carol: 작업 재개"], other,
             GIT_AUTHOR_NAME="Carol", GIT_COMMITTER_NAME="Carol")
        _git(["push", "-q", "origin", "feat-dead"], other)

        stale_view = _survey(work, no_fetch=True)
        _record("test_no_fetch_misjudges_but_warns",
                "feat-dead" in _names(stale_view["stale"])
                and any("낡" in w for w in stale_view["warnings"]),
                f"stale={_names(stale_view['stale'])} warnings={stale_view['warnings']}")

        fresh_view = _survey(work)
        _record("test_fetch_corrects_misjudgment",
                "feat-dead" in _names(fresh_view["active"]) and not fresh_view["stale"],
                f"active={_names(fresh_view['active'])} stale={_names(fresh_view['stale'])}")

    print()
    if FAILURES:
        print(f"=== FAIL: {len(FAILURES)} case(s) — {FAILURES} ===")
        return 1
    print("=== PASS: survey_remote_workspaces smoke (8 assertions) ===")
    return 0


def test_survey_remote_workspaces() -> None:
    assert main() == 0, "survey_remote_workspaces smoke FAIL"


if __name__ == "__main__":
    raise SystemExit(main())
