#!/usr/bin/env python3
"""작업 브랜치의 메모리가 *자기 네임스페이스*에 기록되는지 직접 지목한다 (8 cases).

## 계보 — PR #23 세션 기록 §7 "남은 구멍"

`ai-workflow/memory/active/<branch>/` 는 **자동으로 생기지 않는다.** PR #23 의 작업
브랜치는 그것을 만들지 않고 `active/main/` 의 daily index·handoff·state.json 을
**직접 편집**했고, 결과가 둘이었다:

1. 브랜치 디렉터리가 끝내 안 생겨 `check_branch_context_matrix` /
   `check_claim_workspace` / `check_seed_workspace_memory` 가 push 마다 red —
   **간접 증상**이라 원인을 지목하는 데 오래 걸렸다.
2. task 번호를 main 네임스페이스에서 뽑아 ID 가 충돌했다. 병합 시 daily index 는
   conflict 없이 auto-merge 되므로 **조용히** 오염된다.

2번의 *사후* 흔적은 `check_appendonly_memory_layout` case 7 이 닫았다. 이 검사는
그 앞 단계 — **브랜치에서 일하는 동안** 원인 자체를 지목한다.

## 안내는 `seed-workspace-memory` 를 가리킨다 (실측으로 고침)

PR #23 의 §4 는 "만드는 자리는 `wk backlog-update` 하나" 라고 적었는데, **그대로
따르면 여전히 red 다**. `backlog-update` 는 `tasks_dir.mkdir()` 의 부수효과로
`backlog/` 만 만들 뿐이라 `sessions/` 와 `session_handoff.md` 가 없는 절반짜리
네임스페이스가 되고, `check_appendonly_memory_layout` / `check_memory_freeze_lint` /
`check_self_application` 이 red 가 된다 (이 검사를 만들며 그 순서로 밟아 실측했다).
한 벌로 만드는 정본 창구는 `wk seed-workspace-memory` 다. 도구를 옳게 썼는데도
red 가 나면 다음 사람은 다시 손 편집으로 도망가므로, 이 검사의 안내 문구는
**따라 하면 실제로 green 이 되는 명령**을 가리켜야 한다.

## 판정이 호스트 환경에 달리지 않게 한 것들

같은 세션에서 "로컬 green / CI red" 가 세 번 나왔고 셋 다 *판정이 호스트 환경의
무언가에 달려 있는데 로컬에는 그 축이 없다* 였다 (세션 기록 §5·§6). 그래서:

- 네임스페이스 매핑은 **경로 내용만으로** 한다 (`backlog`/`sessions`/`state.json`/
  `session_handoff.md` marker 앞까지가 slug). 슬래시 든 브랜치명이 그대로 산다.
- CI 환경변수를 보지 않는다. 기본 브랜치는 `path_resolver._detect_default_branch`
  (origin 이 있으면 현재 브랜치로 내려가지 않는다 — 4번째 비대칭의 수리) 를 쓴다.
- detached HEAD (CI 의 PR checkout) 는 **조용한 PASS 가 아니라 사유를 찍고 SKIP**.
  브랜치가 없으면 "브랜치 네임스페이스" 라는 질문 자체가 성립하지 않는다.

## 삭제를 잡지 않는 이유

`archive_branch_memory.py` 는 **작업 브랜치에서 실행해 그 PR 에 실어 보내는 것이
정본 절차**다 (MEMORY_GOVERNANCE.md — protected main 과 호환되게 하는 piggyback).
그 도구는 남의 브랜치 경로(`active/<X>/`)를 지운다. 삭제까지 잡으면 정본 절차가
red 가 된다. 그래서 **추가/수정(A/M)만** 본다.

8 cases:
  1) 경로 → 네임스페이스 매핑 (슬래시 브랜치, 공유 파일, legacy flat)
  2) 다른 브랜치 네임스페이스에 추가/수정 → 검출 (A)
  3) 삭제·rename 원본은 검출하지 않는다 (archive piggyback 오탐 방지)
  4) **되주입** — PR #23 의 모양(작업 브랜치가 `active/main/` 에 task 추가)을
     실제 git 저장소로 재현하면 FAIL 하고 그 경로를 지목한다
  5) 브랜치 메모리 디렉터리 부재 → 검출 (B)
  6) `wk backlog-update` 를 쓴 정상 브랜치는 통과한다 (공허하지 않음의 반대 방향)
  7) detached HEAD 는 사유를 밝히고 SKIP 한다 (조용한 PASS 금지)
  8) **자기 적용** — 이 저장소의 현재 브랜치

Refs:
  - workflow-source/MEMORY_GOVERNANCE.md — Branch-scoped layout (v1.0.0+)
  - ai-workflow/memory/archived/feat/plugin-harness-distribution/sessions/
    plugin_harness_distribution_pr23_2026-08-13.md §4 · §7
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.paths import memory_active_dir  # noqa: E402
from workflow_kit.path_resolver import _detect_default_branch  # noqa: E402

REQUIRES_QUIET_REPO = True
"""case 8 이 저장소의 살아있는 git 상태와 `memory/active/` 를 관찰한다.

다른 check 가 그 찰나에 memory 파일을 재생성 중이면 워킹 트리 diff 가 오염된다."""

MARKER_SEGMENTS = frozenset({
    "backlog", "sessions", "state.json", "session_handoff.md",
})
"""브랜치 디렉터리의 *바로 아래* 에 오는 이름들. 이 앞까지가 브랜치 slug 다.

`active/` 직속의 공유 파일(`PROJECT_PROFILE.md` / `PURPOSE.md` / `memory_index/` /
`environments/` / `*_assessment.md` / `state.json.template`)에는 이 marker 가 없어
자연히 네임스페이스 밖으로 떨어진다 — 목록을 따로 들고 있지 않는 이유다."""


def active_relpath(repo_root: Path) -> str:
    """`memory/active` 의 저장소 상대 경로. 규칙을 여기에 복사하지 않고 resolver 를 쓴다."""
    return memory_active_dir(repo_root).relative_to(repo_root).as_posix()


def namespace_of(rel_path: str, *, active_rel: str) -> str | None:
    """저장소 상대 경로 → 그 파일이 속한 브랜치 네임스페이스.

    브랜치 네임스페이스가 아니면 (공유 파일 / active 밖 / legacy flat layout) None.
    """
    prefix = active_rel + "/"
    if not rel_path.startswith(prefix):
        return None
    segments = rel_path[len(prefix):].split("/")
    for idx, seg in enumerate(segments):
        if seg in MARKER_SEGMENTS:
            # idx == 0 은 legacy flat layout (`active/backlog/…`) — 브랜치 축이 없다.
            return "/".join(segments[:idx]) if idx else None
    return None


def foreign_namespace_writes(
    changes: list[tuple[str, str]], *, branch: str, active_rel: str,
) -> list[str]:
    """`branch` 가 *다른* 브랜치 네임스페이스에 추가/수정한 경로.

    `changes` 는 `(status, path)` — git 의 name-status 그대로. 삭제(D)는 보지
    않는다 (모듈 docstring "삭제를 잡지 않는 이유").
    """
    offenders = []
    for status, path in changes:
        if status not in ("A", "M"):
            continue
        ns = namespace_of(path, active_rel=active_rel)
        if ns is not None and ns != branch:
            offenders.append(path)
    return sorted(set(offenders))


# ---------------------------------------------------------------------------
# git 관측 (판정이 아니라 입력 수집)
# ---------------------------------------------------------------------------
def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, timeout=30,
    )


def current_branch(repo: Path) -> str | None:
    """체크아웃한 브랜치. detached HEAD 면 None (env 를 보지 않는다)."""
    result = _git(repo, "symbolic-ref", "--quiet", "--short", "HEAD")
    return result.stdout.strip() or None if result.returncode == 0 else None


def _merge_base(repo: Path, default_branch: str) -> str | None:
    for ref in (f"origin/{default_branch}", default_branch):
        if _git(repo, "rev-parse", "--verify", "--quiet", ref).returncode != 0:
            continue
        result = _git(repo, "merge-base", ref, "HEAD")
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    return None


def collect_changes(repo: Path, base: str) -> list[tuple[str, str]]:
    """`base`..HEAD 커밋 + 워킹 트리(미커밋·untracked) 를 합친 (status, path).

    커밋 전에도 지적하려면 워킹 트리를 함께 봐야 한다 — 커밋된 뒤에 알려주는
    가드는 이미 늦다.
    """
    changes: list[tuple[str, str]] = []

    diff = _git(repo, "diff", "--name-status", base, "HEAD")
    for line in diff.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        code = parts[0]
        if code.startswith("R"):
            # rename: 원본은 삭제, 목적지는 추가로 본다.
            changes.append(("D", parts[1]))
            changes.append(("A", parts[2]))
        else:
            changes.append((code[0], parts[1]))

    porcelain = _git(repo, "status", "--porcelain", "--untracked-files=all")
    for line in porcelain.stdout.splitlines():
        if len(line) < 4:
            continue
        code, path = line[:2], line[3:].strip()
        if code == "??":
            changes.append(("A", path))
        elif "D" in code:
            changes.append(("D", path))
        else:
            changes.append(("M", path))
    return changes


class Verdict:
    """판정 결과. `skipped` 는 통과가 아니라 *질문이 성립하지 않았다* 는 뜻이다."""

    def __init__(self, errors: list[str], skipped: str | None = None) -> None:
        self.errors = errors
        self.skipped = skipped


def audit_repo(repo: Path) -> Verdict:
    """저장소 하나를 판정한다. 호스트 환경이 아니라 저장소 자신만 본다."""
    branch = current_branch(repo)
    if branch is None:
        return Verdict([], skipped="detached HEAD — 브랜치 네임스페이스 질문이 성립하지 않는다")

    default_branch = _detect_default_branch(repo)
    if branch == default_branch:
        return Verdict([], skipped=f"기본 브랜치({default_branch}) — 자기 네임스페이스에 쓰는 것이 정상")

    base = _merge_base(repo, default_branch)
    if base is None:
        return Verdict([], skipped=f"기준 ref 부재 ({default_branch}) — diverged 범위를 못 만든다")

    changes = collect_changes(repo, base)
    if not changes:
        return Verdict([], skipped="기본 브랜치와 갈라진 변경이 없다")

    active_rel = active_relpath(repo)
    errors: list[str] = []

    # (A) 남의 네임스페이스에 쓰기 — PR #23 의 직접 원인
    offenders = foreign_namespace_writes(changes, branch=branch, active_rel=active_rel)
    if offenders:
        errors.append(
            f"작업 브랜치 '{branch}' 가 다른 브랜치 네임스페이스에 추가/수정했다:\n"
            + "".join(f"    {p}\n" for p in offenders)
            + f"  → 브랜치 메모리는 `{active_rel}/{branch}/` 에 쓴다. "
            "손으로 편집하지 말고 `wk backlog-update` 를 쓰면 경로와 task ID 가 "
            "브랜치 네임스페이스로 잡힌다 (main 번호를 뽑으면 병합 시 ID 가 충돌하고, "
            "daily index 는 conflict 없이 auto-merge 되어 조용히 오염된다). "
            "네임스페이스가 아직 없으면 `wk seed-workspace-memory` 를 먼저 돌린다."
        )

    # (B) 자기 디렉터리 부재 — 3개 검사가 간접 증상으로만 알려주던 것
    if (repo / active_rel / "backlog").is_dir():
        return Verdict(errors)  # legacy flat layout — 브랜치 축이 없다
    branch_dir = repo / active_rel / branch
    if not branch_dir.is_dir():
        errors.append(
            f"작업 브랜치 '{branch}' 에 메모리 디렉터리가 없다: {active_rel}/{branch}/\n"
            "  → 이 디렉터리는 자동으로 생기지 않는다. `wk seed-workspace-memory "
            f"--branch {branch} --axis <작업 축> --task-title <제목> --apply` 로 "
            "handoff + backlog + sessions 를 **한 벌로** 만든 뒤 `wk refresh-state` 를 "
            "돌린다 (session-start / refresh-state 는 부재를 warning 으로만 알린다).\n"
            "  → `wk backlog-update` 만 쓰면 backlog/ 만 생겨 sessions/ 와 "
            "session_handoff.md 가 빠진 절반짜리가 된다 — 그 상태에서는 "
            "check_appendonly_memory_layout / check_memory_freeze_lint / "
            "check_self_application 이 red 다."
        )

    return Verdict(errors)


# ---------------------------------------------------------------------------
# fixture
# ---------------------------------------------------------------------------
ACTIVE_REL = "ai-workflow/memory/active"


def _init_repo(root: Path, *, default_branch: str = "main") -> None:
    """origin 을 **가진** 저장소를 만든다 — 그게 실제 형상이고, 판정이 달라진다.

    `_detect_default_branch` 는 origin 이 없으면 *현재 브랜치*를 기본 브랜치로
    돌려준다 (로컬 전용 저장소에서는 그게 맞다). origin 없는 fixture 로 재면 작업
    브랜치가 곧 기본 브랜치가 되어 이 검사가 통째로 skip 된다 — 실제 저장소에서는
    절대 일어나지 않는 형상으로 green 을 얻는 것이다.

    `refs/remotes/origin/HEAD` 는 일부러 만들지 않는다. `actions/checkout` 이
    단일 ref 만 가져와 그것을 만들지 않으므로, CI 형상과 같은 축으로 잰다.
    """
    bare = root.parent / f"{root.name}.origin.git"
    subprocess.run(
        ["git", "init", "--quiet", "--bare", f"--initial-branch={default_branch}", str(bare)],
        capture_output=True, text=True, timeout=30, check=True,
    )
    _git(root, "init", "--quiet", f"--initial-branch={default_branch}")
    _git(root, "config", "user.email", "fixture@example.com")
    _git(root, "config", "user.name", "fixture")
    _git(root, "remote", "add", "origin", str(bare))
    _write(root / "README.md", "# fixture\n")
    _git(root, "add", "-A")
    _git(root, "commit", "--quiet", "-m", "init")
    _git(root, "push", "--quiet", "origin", default_branch)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_branch_memory(root: Path, branch: str) -> None:
    """`wk backlog-update` 가 만드는 최소 형태."""
    _write(root / ACTIVE_REL / branch / "backlog" / "2026-01-01.md", "# index\n")
    _write(
        root / ACTIVE_REL / branch / "backlog" / "tasks" / "TASK-2026-01-01-x-001.md",
        "# task\n",
    )


# ---------------------------------------------------------------------------
# cases
# ---------------------------------------------------------------------------
def case_1_namespace_mapping() -> None:
    table = {
        f"{ACTIVE_REL}/main/backlog/tasks/TASK-1.md": "main",
        f"{ACTIVE_REL}/main/session_handoff.md": "main",
        f"{ACTIVE_REL}/main/state.json": "main",
        # 슬래시 든 브랜치명이 한 segment 로 잘리면 안 된다 (4번째 비대칭의 교훈)
        f"{ACTIVE_REL}/feat/plugin-harness-distribution/backlog/2026-08-13.md":
            "feat/plugin-harness-distribution",
        f"{ACTIVE_REL}/feat/plugin-harness-distribution/sessions/s.md":
            "feat/plugin-harness-distribution",
        # 공유 파일 — 브랜치 축이 없다
        f"{ACTIVE_REL}/PROJECT_PROFILE.md": None,
        f"{ACTIVE_REL}/PURPOSE.md": None,
        f"{ACTIVE_REL}/memory_index/index.json": None,
        f"{ACTIVE_REL}/environments/plex.md": None,
        f"{ACTIVE_REL}/state.json.template": None,
        # legacy flat layout — 브랜치 축 이전
        f"{ACTIVE_REL}/backlog/2026-01-01.md": None,
        # active 밖
        "docs/PROJECT_PROFILE.md": None,
        "ai-workflow/memory/archived/feat/x/sessions/s.md": None,
    }
    for path, expected in table.items():
        actual = namespace_of(path, active_rel=ACTIVE_REL)
        assert actual == expected, f"{path} → {actual!r} (기대 {expected!r})"


def case_2_foreign_writes_detected() -> None:
    changes = [
        ("A", f"{ACTIVE_REL}/main/backlog/tasks/TASK-2026-08-13-main-008.md"),
        ("M", f"{ACTIVE_REL}/main/session_handoff.md"),
        ("M", f"{ACTIVE_REL}/feat/mine/backlog/2026-08-13.md"),
        ("M", f"{ACTIVE_REL}/PROJECT_PROFILE.md"),
        ("M", "workflow-source/workflow_kit/tools/doc_sync.py"),
    ]
    offenders = foreign_namespace_writes(changes, branch="feat/mine", active_rel=ACTIVE_REL)
    assert offenders == [
        f"{ACTIVE_REL}/main/backlog/tasks/TASK-2026-08-13-main-008.md",
        f"{ACTIVE_REL}/main/session_handoff.md",
    ], f"검출 결과가 다르다: {offenders}"


def case_3_deletions_are_not_flagged() -> None:
    """archive_branch_memory 는 작업 브랜치에서 남의 경로를 지운다 — 정본 절차다."""
    changes = [
        ("D", f"{ACTIVE_REL}/feat/other/backlog/2026-08-13.md"),
        ("D", f"{ACTIVE_REL}/feat/other/session_handoff.md"),
        ("A", "ai-workflow/memory/archived/feat/other/session_handoff.md"),
    ]
    offenders = foreign_namespace_writes(changes, branch="feat/mine", active_rel=ACTIVE_REL)
    assert offenders == [], f"삭제/아카이브를 오탐했다: {offenders}"


def case_4_reinjection_real_repo(root: Path) -> None:
    """PR #23 의 모양을 실제 git 저장소로 재현한다."""
    repo = root / "reinjection"
    repo.mkdir(parents=True)
    _init_repo(repo)
    _seed_branch_memory(repo, "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "main memory")
    # main 의 기록은 **갈라지기 전** 에 origin 에 올려 둔다. 안 그러면 merge-base 가
    # init 커밋으로 내려가 main 의 정상 커밋까지 브랜치의 변경으로 잡힌다.
    _git(repo, "push", "--quiet", "origin", "main")

    _git(repo, "checkout", "--quiet", "-b", "feat/plugin-harness-distribution")
    _seed_branch_memory(repo, "feat/plugin-harness-distribution")
    # ← 여기가 결함: 브랜치 작업을 main 네임스페이스에 적었다
    _write(
        repo / ACTIVE_REL / "main" / "backlog" / "tasks" / "TASK-2026-08-13-main-008.md",
        "# 브랜치 작업인데 main 번호를 뽑았다\n",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "work")

    verdict = audit_repo(repo)
    assert verdict.skipped is None, f"판정을 건너뛰었다: {verdict.skipped}"
    assert len(verdict.errors) == 1, f"오류 수가 다르다: {verdict.errors}"
    assert "TASK-2026-08-13-main-008.md" in verdict.errors[0], (
        f"오염 경로를 지목하지 못했다:\n{verdict.errors[0]}"
    )
    assert "wk backlog-update" in verdict.errors[0], "처방을 안내하지 않는다"


def case_5_missing_branch_dir(root: Path) -> None:
    repo = root / "missing-dir"
    repo.mkdir(parents=True)
    _init_repo(repo)
    _seed_branch_memory(repo, "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "main memory")
    # main 의 기록은 **갈라지기 전** 에 origin 에 올려 둔다. 안 그러면 merge-base 가
    # init 커밋으로 내려가 main 의 정상 커밋까지 브랜치의 변경으로 잡힌다.
    _git(repo, "push", "--quiet", "origin", "main")

    _git(repo, "checkout", "--quiet", "-b", "fix/no-memory")
    _write(repo / "workflow-source" / "tools" / "thing.py", "x = 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "code only")

    verdict = audit_repo(repo)
    assert verdict.skipped is None, f"판정을 건너뛰었다: {verdict.skipped}"
    assert len(verdict.errors) == 1, f"오류 수가 다르다: {verdict.errors}"
    assert f"{ACTIVE_REL}/fix/no-memory/" in verdict.errors[0], (
        f"부재 경로를 지목하지 못했다:\n{verdict.errors[0]}"
    )


def case_6_healthy_branch_passes(root: Path) -> None:
    """공허하지 않음의 반대 방향 — 정상 브랜치를 red 로 만들면 그 검사는 못 쓴다."""
    repo = root / "healthy"
    repo.mkdir(parents=True)
    _init_repo(repo)
    _seed_branch_memory(repo, "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "main memory")
    # main 의 기록은 **갈라지기 전** 에 origin 에 올려 둔다. 안 그러면 merge-base 가
    # init 커밋으로 내려가 main 의 정상 커밋까지 브랜치의 변경으로 잡힌다.
    _git(repo, "push", "--quiet", "origin", "main")

    _git(repo, "checkout", "--quiet", "-b", "feat/proper")
    _seed_branch_memory(repo, "feat/proper")
    _write(repo / "workflow-source" / "tools" / "thing.py", "x = 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "work with branch memory")

    verdict = audit_repo(repo)
    assert verdict.skipped is None, f"판정을 건너뛰었다: {verdict.skipped}"
    assert verdict.errors == [], f"정상 브랜치를 오탐했다: {verdict.errors}"


def case_7_detached_head_is_loud(root: Path) -> None:
    repo = root / "detached"
    repo.mkdir(parents=True)
    _init_repo(repo)
    _seed_branch_memory(repo, "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "main memory")
    # main 의 기록은 **갈라지기 전** 에 origin 에 올려 둔다. 안 그러면 merge-base 가
    # init 커밋으로 내려가 main 의 정상 커밋까지 브랜치의 변경으로 잡힌다.
    _git(repo, "push", "--quiet", "origin", "main")
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "checkout", "--quiet", head)

    assert current_branch(repo) is None, "detached HEAD 를 브랜치로 봤다"
    verdict = audit_repo(repo)
    assert verdict.skipped is not None, "detached HEAD 를 조용히 통과시켰다"
    assert "detached" in verdict.skipped, f"사유가 불명확하다: {verdict.skipped}"
    assert verdict.errors == [], f"skip 인데 오류를 냈다: {verdict.errors}"


def case_8_self_application() -> str:
    verdict = audit_repo(REPO_ROOT)
    assert verdict.errors == [], (
        "이 저장소가 자기 규칙을 어겼다:\n" + "\n".join(verdict.errors)
    )
    return verdict.skipped or "판정함"


def main() -> int:
    case_1_namespace_mapping()
    case_2_foreign_writes_detected()
    case_3_deletions_are_not_flagged()
    with tempfile.TemporaryDirectory(prefix="check-branch-memory-ns-") as tmp:
        root = Path(tmp).resolve()  # macOS /private symlink
        case_4_reinjection_real_repo(root)
        case_5_missing_branch_dir(root)
        case_6_healthy_branch_passes(root)
        case_7_detached_head_is_loud(root)
    self_note = case_8_self_application()
    print(f"case 8 (자기 적용): {self_note}")
    print("branch memory namespace check passed (8 cases)")
    return 0


def test_case_1() -> None:
    case_1_namespace_mapping()


def test_case_2() -> None:
    case_2_foreign_writes_detected()


def test_case_3() -> None:
    case_3_deletions_are_not_flagged()


def test_case_4() -> None:
    with tempfile.TemporaryDirectory(prefix="check-branch-memory-ns-") as tmp:
        case_4_reinjection_real_repo(Path(tmp).resolve())


def test_case_5() -> None:
    with tempfile.TemporaryDirectory(prefix="check-branch-memory-ns-") as tmp:
        case_5_missing_branch_dir(Path(tmp).resolve())


def test_case_6() -> None:
    with tempfile.TemporaryDirectory(prefix="check-branch-memory-ns-") as tmp:
        case_6_healthy_branch_passes(Path(tmp).resolve())


def test_case_7() -> None:
    with tempfile.TemporaryDirectory(prefix="check-branch-memory-ns-") as tmp:
        case_7_detached_head_is_loud(Path(tmp).resolve())


def test_case_8() -> None:
    case_8_self_application()


if __name__ == "__main__":
    raise SystemExit(main())
