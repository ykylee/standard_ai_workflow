#!/usr/bin/env python3
"""pre-push 게이트 — 게이트 통과 기록 없는 커밋의 push 를 막는다 (TASK-2026-09-23-main-009).

86차 `f4504818` 은 게이트를 돈 **뒤** CLAUDE.md 를 고쳐 게이트 없이 push 됐고, 스탬프
위반이 CI 에서만 드러났다. 등록 당시 진단('미커밋 유예가 축을 가렸다')은 틀렸다 —
미커밋 변경의 스탬프는 유예 0 으로 로컬에서도 red 다. 로컬 green 은 **다른 sha 의**
green 이었다. CI 가 폐지된 지금은 그런 커밋을 아무도 안 잰다.

이 검사가 고정하는 것 (임시 저장소에서 — 실 저장소의 기록·설정을 건드리지 않는다):

- 기록 있음 → 통과 · 기록 없음 → 막음 · 컨텍스트 빠진 기록 → 막음
- 삭제 push 는 통과 · 태그는 가리키는 커밋으로 벗긴다 · 못 읽는 sha 는 막는다 (모름 ≠ 통과)
- 저장소의 `.githooks/pre-push` 가 실행 가능하고, 실제로 그 판정을 exit code 로 낸다
- hooksPath 로 꺼지는 `.git/hooks/pre-push` 를 같은 인자·입력으로 이어 부른다
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    ".githooks/*",
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "workflow-source"))

from workflow_kit.common import gate_evidence  # noqa: E402
from workflow_kit.common.branch_matrix import labels  # noqa: E402

HOOK = REPO_ROOT / ".githooks" / "pre-push"
ZERO = "0" * 40
FAILURES: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}: {case}{'' if ok else ' — ' + detail}")
    if not ok:
        FAILURES.append(case)


def _git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True, env=env).stdout.strip()


def _repo(tmp: Path) -> tuple[Path, str, str]:
    repo = tmp / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "a.txt").write_text("1\n", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "one")
    gated = _git(repo, "rev-parse", "HEAD")
    (repo / "a.txt").write_text("2\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "two")
    ungated = _git(repo, "rev-parse", "HEAD")
    gate_evidence.record(repo, gated, contexts=list(labels()), total=1)
    return repo, gated, ungated


def _line(sha: str, ref: str = "refs/heads/main") -> str:
    return f"{ref} {sha} {ref} {ZERO}"


def test_check_push_verdicts() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="pre-push-") as tmpdir:
        repo, gated, ungated = _repo(Path(tmpdir))
        if gate_evidence.check_push(repo, [_line(gated)]):
            problems.append("기록 있는 sha 를 막았다")
        out = gate_evidence.check_push(repo, [_line(ungated)])
        if not out or ungated[:8] not in out[0]:
            problems.append(f"기록 없는 sha 를 통과시켰다: {out}")
        # ref 여럿 중 하나라도 없으면 막는다
        if not gate_evidence.check_push(repo, [_line(gated), _line(ungated, "refs/heads/b")]):
            problems.append("여러 ref 중 기록 없는 것을 놓쳤다")
        # 컨텍스트가 빠진 기록
        partial = list(labels())[:-1]
        gate_evidence.record(repo, ungated, contexts=partial, total=1)
        out = gate_evidence.check_push(repo, [_line(ungated)])
        if not out or "컨텍스트" not in out[0]:
            problems.append(f"컨텍스트 빠진 기록을 통과시켰다: {out}")
        # 삭제 push · 태그 벗기기 · 못 읽는 sha
        if gate_evidence.check_push(repo, [f"(delete) {ZERO} refs/heads/x {gated}"]):
            problems.append("삭제 push 를 막았다")
        _git(repo, "tag", "-a", "v1", gated, "-m", "t")
        tag_obj = _git(repo, "rev-parse", "v1")
        if tag_obj == gated or gate_evidence.check_push(repo, [_line(tag_obj, "refs/tags/v1")]):
            problems.append("주석 태그를 커밋으로 벗기지 않았다")
        out = gate_evidence.check_push(repo, [_line("f" * 40)])
        if not out or "읽지 못했다" not in out[0]:
            problems.append(f"못 읽는 sha 를 통과시켰다: {out}")
    _record("test_check_push_verdicts", not problems, "; ".join(problems))


def test_hook_script_enforces_verdict() -> None:
    """저장소의 hook 이 실행 가능하고, 그 판정을 exit code 로 낸다 (소비 지점까지)."""
    problems: list[str] = []
    if not HOOK.is_file():
        _record("test_hook_script_enforces_verdict", False, f"hook 이 없다: {HOOK}")
        return
    if os.name != "nt" and not os.access(HOOK, os.X_OK):
        problems.append("hook 에 실행 권한이 없다 — git 은 조용히 건너뛴다")
    with tempfile.TemporaryDirectory(prefix="pre-push-hook-") as tmpdir:
        repo, gated, ungated = _repo(Path(tmpdir))
        for sha, want in ((gated, 0), (ungated, 1)):
            proc = subprocess.run(["sh", str(HOOK)], cwd=repo, input=_line(sha) + "\n",
                                  capture_output=True, text=True, timeout=60)
            if proc.returncode != want:
                problems.append(f"{sha[:8]}: exit {proc.returncode} (기대 {want}) {proc.stderr[-300:]!r}")
            if want == 1 and "--no-verify" not in proc.stderr:
                problems.append("막을 때 우회 방법을 말하지 않는다")
        # hooksPath 로 꺼지는 `.git/hooks/pre-push` 를 이어 부르는가 — 같은 인자·입력으로
        legacy = repo / ".git" / "hooks" / "pre-push"
        seen = repo / "legacy-saw.txt"
        legacy.write_text(f'#!/bin/sh\necho "$1 $(cat)" > "{seen}"\nexit 1\n', encoding="utf-8")
        legacy.chmod(0o755)
        proc = subprocess.run(["sh", str(HOOK), "origin", "url"], cwd=repo,
                              input=_line(gated) + "\n", capture_output=True, text=True, timeout=60)
        if proc.returncode != 1:
            problems.append(f"기존 .git/hooks/pre-push 의 거절을 삼켰다: exit {proc.returncode}")
        saw = seen.read_text(encoding="utf-8") if seen.is_file() else ""
        if not saw.startswith("origin") or gated not in saw:
            problems.append(f"기존 hook 에 인자·입력을 넘기지 않았다: {saw!r}")
    _record("test_hook_script_enforces_verdict", not problems, "; ".join(problems))


def main() -> int:
    cases = [test_check_push_verdicts, test_hook_script_enforces_verdict]
    for case in cases:
        case()
    print(f"\n{len(cases) - len(FAILURES)}/{len(cases)} passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
