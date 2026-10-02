#!/usr/bin/env python3
r"""브랜치 네임스페이스가 없는 worktree 에서 session-start 가 스스로 seed 한다 (13 cases).

## 왜 이 검사가 필요한가 (TASK-2026-09-30-claude-session-start-e6eb83-002)

`active/<branch>/` 는 브랜치를 만든다고 생기지 않는다 (orchestration §5A.2). 중앙이
배정하는 워크스페이스는 `seed-workspace-memory` 를 먼저 돌리지만, **하네스가 스스로
만드는 worktree** 는 그 단계를 거치지 않는다. 110차 macOS 실측:

- Claude Code 데스크톱 worktree(`claude/<name>`) — `wk session-start` 가
  `missing_required_document` 로 멈췄고, 이어진 `backlog-update` 는 state.json 만
  `active/claude/<name>/` 에 만들어 브랜치 메모리가 절반짜리로 갈렸다.
- Codex 데스크톱 worktree(detached HEAD) — slug 가 short sha 라 `active/6545f13/` 이
  생겼다. sha 는 커밋마다 바뀌므로 커밋 한 번에 네임스페이스가 고아가 된다.

소유자 결정(2026-09-30): 브랜치 dir 이 없으면 **자동 seed**, CI 밖 detached HEAD 는
**기본 브랜치**. 이 검사는 파일이 생겼는지가 아니라 **session-start 가 도는지** 를 본다.

판정이 호스트 저장소 상태에 달리지 않게, 매 case 가 임시 git 저장소(origin + clone)를
만들고 브랜치·CI env 를 비운 좁은 환경에서 모듈을 띄운다.

7 cases:
  1) 새 브랜치 → session-start status=ok + seed warning + 한 벌(handoff·backlog·task·
     sessions·state.json) — 되주입: seed 를 끄면 missing_required_document
  2) 재실행은 다시 seed 하지 않는다 (task 가 늘지 않고 seed warning 이 없다)
  3) 기본 브랜치 자신에서는 seed 하지 않는다
  4) `--session-handoff-path` 를 명시하면 seed 하지 않는다 (호출자가 자리를 골랐다)
  5) env override 로 얻은 브랜치는 seed 하지 않는다 (이 workspace 를 보고 얻은 답이 아니다)
  6) 기본 브랜치 네임스페이스가 없는 저장소는 seed 하지 않는다 (bootstrap 이 할 일)
  7) CI 밖 detached HEAD 는 기본 브랜치 네임스페이스로 바로 시작한다 — sha dir 이 생기지 않는다
  8) 로드맵 선언 수집이 슬래시 브랜치(`active/claude/<name>/`)의 task 도 센다 — 한 단계
     glob 이던 때는 자동 seed task 의 `wbs: exempt` 가 안 보여 '선언 사슬이 끊긴 완료
     항목' 경고가 매 세션 났다. 형제 공유 디렉터리(roadmap · memory_index · environments)의
     task 모양 파일은 링크로 오인하지 않는다 (main-012 완료 기준 4)

이어받기 (TASK-2026-10-02-main-001 — seed 가 모 브랜치 **내용을 옮겨 적고** 원류를 남긴다):
  9) 새 브랜치의 session-start 가 모 브랜치의 차단 task · 기준선을 보고하고, handoff 에 `원류: main@<sha>`
     (sha = 체크아웃 HEAD) · §5 앞머리 bullet 이 실린다. 열린 task(차단·계획)는 같은 ID 로 옮겨지고
     원류 두 줄을 걷으면 원문과 바이트가 같다. done task 는 옮기지 않는다. 모 브랜치 파일은 바이트 불변.
     옮긴 상대 링크는 새 위치에서 풀린다
 10) 이어받은 task 를 worktree 에서 `backlog-update` 로 갱신할 수 있고(원류 줄 유지), 다음 시작에 정합
     경고가 없으며, 모 브랜치 원본은 그대로다
 11) 로드맵 수집은 같은 ID 를 한 번만 센다 — 안 고친 사본은 원본의 그림자, 고친 사본이 원본을 대신한다
 12) 합류 아카이브가 고친 사본을 원류 줄 없이 원본 자리에 되돌려 적고, 안 고친 사본은 건드리지 않으며,
     이어받은 열린 task 가 아카이브를 막지 않는다
 13) 원본이 그 사이 바뀌었으면 되돌려 적지 않고 막는다 — 원본 불변, 브랜치 네임스페이스는 active 에 남는다
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.state.memory_index import TELEMETRY_SKIP_ROOT_ENV  # noqa: E402
from workflow_kit.common.branch_inheritance import strip_inherited  # noqa: E402
from workflow_kit.common.reconcile import STATE_CONFLICT_MARKER  # noqa: E402
from workflow_kit.common.state.roadmap import collect_task_wbs_links, resolve_task_goals  # noqa: E402

SEED_MARK = "네임스페이스를 seed 했다"
FAILURES: list[str] = []


def _record(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + ("" if ok else f" — {detail}"))
    if not ok:
        FAILURES.append(name)


def _env(extra: dict[str, str] | None = None) -> dict[str, str]:
    # 브랜치 env · CI env 를 물려받지 않는다 — 답이 러너에 달리면 호스트마다 갈린다.
    env = {"PYTHONPATH": str(SOURCE_ROOT), "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
           "HOME": os.environ.get("HOME", "/tmp"),
           "GIT_CONFIG_NOSYSTEM": "1"}
    if TELEMETRY_SKIP_ROOT_ENV in os.environ:
        env[TELEMETRY_SKIP_ROOT_ENV] = os.environ[TELEMETRY_SKIP_ROOT_ENV]
    env.update(extra or {})
    return env


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   cwd=cwd, check=True, capture_output=True, text=True, env=_env())


def _make_repo(tmp: Path, *, with_base_memory: bool = True) -> Path:
    """origin(main, 브랜치별 메모리) 을 만들고 clone 을 돌려준다."""
    origin = tmp / "origin"
    (origin / "docs").mkdir(parents=True)
    _git(tmp, "init", "-q", "-b", "main", str(origin))
    (origin / "docs" / "PROJECT_PROFILE.md").write_text(
        "# Project Profile\n\n- 프로젝트명: auto-seed probe\n", encoding="utf-8")
    if with_base_memory:
        base = origin / "ai-workflow" / "memory" / "active" / "main"
        (base / "backlog" / "tasks").mkdir(parents=True)
        (base / "sessions").mkdir()
        (base / "sessions" / "seed.md").write_text("# s\n", encoding="utf-8")
        (base / "backlog" / "tasks" / ".gitkeep").write_text("", encoding="utf-8")
        (base / "session_handoff.md").write_text(
            "# Session Handoff\n\n## 1. 현재 작업 요약\n\n- 현재 기준선: base\n"
            "- 현재 주 작업 축: base 축\n\n## 2. 진행 중 작업\n\n- 현재 `in_progress` 작업:\n-\n",
            encoding="utf-8")
    else:
        (origin / "ai-workflow" / "memory" / "active").mkdir(parents=True)
        (origin / "ai-workflow" / "memory" / "active" / ".gitkeep").write_text("", encoding="utf-8")
    _git(origin, "add", "-A")
    _git(origin, "commit", "-qm", "init")
    clone = tmp / "clone"
    _git(tmp, "clone", "-q", str(origin), str(clone))
    return clone


def _session_start(cwd: Path, *args: str, env: dict[str, str] | None = None) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "workflow_kit.tools.session_start", *args],
        cwd=cwd, capture_output=True, text=True, env=_env(env), timeout=120,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"status": "unparsable", "stdout": proc.stdout[-500:], "stderr": proc.stderr[-500:]}


def _seeded(result: dict) -> bool:
    return any(SEED_MARK in w for w in result.get("warnings", []))


def _active(clone: Path) -> Path:
    return clone / "ai-workflow" / "memory" / "active"


PARENT_TASKS = {
    # id: (status, wbs)
    "TASK-2026-09-30-main-001": ("blocked", "M-001/WBS-1.1"),
    "TASK-2026-09-30-main-002": ("planned", "M-001/WBS-1.2"),
    "TASK-2026-09-30-main-003": ("done", "M-001/WBS-1.3"),
}


def _parent_task_text(task_id: str, status: str, wbs: str) -> str:
    return (f"---\nid: {task_id}\nstatus: {status}\ncreated_at: 2026-09-30\n"
            f"source_anchor: generic-{task_id.lower()}\nsource_path: backlog/2026-09-30.md\n"
            f"kind: generic\nwbs: {wbs}\n---\n\n# {task_id} — 모 브랜치 {status} task\n\n"
            f"## 📝 Description\n\n- 상태: {status}\n\n## 🛠️ Implementation / Content\n\n- 진행 현황: 원문\n")


def _make_inherit_repo(tmp: Path) -> Path:
    """모 브랜치(main)에 열린 task · §5 · 상대 링크를 가진 handoff 를 둔 저장소."""
    clone = _make_repo(tmp)
    base = _active(clone) / "main"
    (clone / "docs" / "SPEC.md").write_text("# spec\n", encoding="utf-8")
    (base / "session_handoff.md").write_text(
        "# Session Handoff\n\n## 1. 현재 작업 요약\n\n- 현재 기준선: 모 브랜치 기준선 X\n"
        "- 현재 주 작업 축: 모 축 — [spec](../../../../docs/SPEC.md)\n\n"
        "## 2. 진행 중 작업\n\n- 현재 `in_progress` 작업:\n-\n\n"
        "## 3. 차단 작업\n\n- 현재 `blocked` 작업:\n- TASK-2026-09-30-main-001 모 브랜치 blocked task\n\n"
        "## 5. 다음 세션 시작 포인트\n\n- 모 브랜치 다음 걸음 A\n- 모 브랜치 다음 걸음 B\n\n"
        "### 누적 소절\n\n- 옮기지 않을 줄\n", encoding="utf-8")
    index = ["# Backlog Index — 2026-09-30", "", "## Tasks", ""]
    for task_id, (status, wbs) in PARENT_TASKS.items():
        (base / "backlog" / "tasks" / f"{task_id}.md").write_text(
            _parent_task_text(task_id, status, wbs), encoding="utf-8")
        index += [f"- **{task_id}** [generic] 모 브랜치 {status} task",
                  f"  - path: [`./tasks/{task_id}.md`](./tasks/{task_id}.md)", f"  - status: {status}"]
    (base / "backlog" / "2026-09-30.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-qm", "parent memory")
    return clone


def _snapshot(directory: Path) -> dict[str, bytes]:
    return {p.relative_to(directory).as_posix(): p.read_bytes() for p in sorted(directory.rglob("*")) if p.is_file()}


def _archive(clone: Path, branch: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "workflow_kit.tools.archive_branch_memory", "--branch", branch, "--apply", "--json"],
        cwd=clone, capture_output=True, text=True, env=_env(), timeout=120,
    )


def _inheritance_cases(tmp: Path) -> None:
    import re  # noqa: PLC0415

    # --- case 9: 옮겨 적기 + 원류 -------------------------------------------
    clone = _make_inherit_repo(tmp / "c9")
    parent = _active(clone) / "main"
    before = _snapshot(parent)
    _git(clone, "checkout", "-q", "-b", "claude/heir")
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=clone, capture_output=True,
                         text=True, env=_env()).stdout.strip()
    result = _session_start(clone)
    heir = _active(clone) / "claude" / "heir"
    handoff = (heir / "session_handoff.md").read_text(encoding="utf-8") if (heir / "session_handoff.md").exists() else ""
    problems = []
    if "TASK-2026-09-30-main-001" not in " ".join(result.get("blocked_items") or []):
        problems.append(f"blocked_items={result.get('blocked_items')}")
    if "모 브랜치 기준선 X" not in " ".join(result.get("summary") or []):
        problems.append("기준선 미보고")
    if f"원류: `main@{sha}`" not in handoff:
        problems.append(f"원류 줄 없음 (sha={sha})")
    if "모 브랜치 다음 걸음 B" not in handoff or "옮기지 않을 줄" in handoff:
        problems.append("§5 앞머리 bullet 만 옮겨야 한다")
    for task_id, (status, wbs) in PARENT_TASKS.items():
        copy = heir / "backlog" / "tasks" / f"{task_id}.md"
        if status == "done":
            if copy.exists():
                problems.append(f"done task 를 옮겼다: {task_id}")
            continue
        text = copy.read_text(encoding="utf-8") if copy.exists() else ""
        if f"inherited_from: main@{sha}" not in text:
            problems.append(f"{task_id} 원류 frontmatter 없음")
        elif strip_inherited(text) != _parent_task_text(task_id, status, wbs):
            problems.append(f"{task_id} 원류 줄을 걷어도 원문과 다르다")
    for link in re.findall(r"\]\(([^)#]+)\)", handoff):
        if not link.startswith(("./", "http")) and not (heir / link).resolve().exists():
            problems.append(f"깨진 링크 {link}")
    if _snapshot(parent) != before:
        problems.append("모 브랜치 파일이 바뀌었다")
    _record("test_seed_inherits_parent_content_with_origin", result.get("status") == "ok" and not problems,
            "; ".join(problems))

    # --- case 10: 이어받은 task 갱신 -----------------------------------------
    upd = subprocess.run(
        [sys.executable, "-m", "workflow_kit.tools.backlog_update", "--project-profile-path", "docs/PROJECT_PROFILE.md",
         "--apply", "--task-id", "TASK-2026-09-30-main-002", "--mode", "update", "--task-name", "x",
         "--progress-note", "worktree 에서 이어서 진행"],
        cwd=clone, capture_output=True, text=True, env=_env(), timeout=120)
    copy = heir / "backlog" / "tasks" / "TASK-2026-09-30-main-002.md"
    # 사본이 없으면(이어받기 실패) 판정으로 떨어뜨린다 — 예외로 죽으면 뒤 case 가 안 돈다.
    copy_text = copy.read_text(encoding="utf-8") if copy.is_file() else ""
    again = _session_start(clone)
    # 정합 경고(handoff ↔ backlog)만 본다 — fixture 에 PURPOSE.md 가 없어 나는 경고는 이 판정과 무관하다.
    conflicts = [w for w in again.get("warnings", []) if STATE_CONFLICT_MARKER in w]
    origin_kept = copy_text.startswith("---\ninherited_from: main@")
    ok10 = (upd.returncode == 0 and "worktree 에서 이어서 진행" in copy_text
            and origin_kept and not conflicts
            and again.get("status") == "ok" and _snapshot(parent) == before)
    _record("test_inherited_task_is_updatable_in_branch", ok10,
            f"rc={upd.returncode} updated={'worktree 에서 이어서 진행' in copy_text} "
            f"origin_kept={origin_kept} conflicts={conflicts} "
            f"parent_same={_snapshot(parent) == before}")

    # --- case 11: 로드맵은 같은 ID 를 한 번 센다 --------------------------------
    links = [(link.task_id, link.task_status, link.source_path) for link in collect_task_wbs_links(clone)]
    ids = [tid for tid, _, _ in links]
    by_id = {tid: (st, src) for tid, st, src in links}
    ok11 = (len(ids) == len(set(ids))
            and "/active/main/" in "/" + by_id.get("TASK-2026-09-30-main-001", ("", ""))[1]
            and "/claude/heir/" in by_id.get("TASK-2026-09-30-main-002", ("", ""))[1])
    _record("test_roadmap_counts_inherited_task_once", ok11, f"links={links}")

    # --- case 12: 합류 아카이브가 되돌려 적는다 ----------------------------------
    proc = _archive(clone, "claude/heir")
    origin_002 = (parent / "backlog" / "tasks" / "TASK-2026-09-30-main-002.md").read_text(encoding="utf-8")
    origin_001 = (parent / "backlog" / "tasks" / "TASK-2026-09-30-main-001.md").read_text(encoding="utf-8")
    ok12 = (proc.returncode == 0 and origin_002 == strip_inherited(copy_text)
            and origin_001 == _parent_task_text("TASK-2026-09-30-main-001", "blocked", "M-001/WBS-1.1")
            and not heir.exists())
    _record("test_archive_writes_back_modified_inherited_task", ok12,
            f"rc={proc.returncode} written={origin_002 == strip_inherited(copy_text)} "
            f"untouched_001={'inherited_from' not in origin_001} heir_left={heir.exists()} {proc.stdout[-300:]}")

    # --- case 13: 원본이 바뀌었으면 막는다 --------------------------------------
    clone = _make_inherit_repo(tmp / "c13")
    parent = _active(clone) / "main"
    _git(clone, "checkout", "-q", "-b", "claude/heir")
    _session_start(clone)
    heir = _active(clone) / "claude" / "heir"
    subprocess.run(
        [sys.executable, "-m", "workflow_kit.tools.backlog_update", "--project-profile-path", "docs/PROJECT_PROFILE.md",
         "--apply", "--task-id", "TASK-2026-09-30-main-002", "--mode", "update", "--task-name", "x",
         "--progress-note", "worktree 쪽 변경"],
        cwd=clone, capture_output=True, text=True, env=_env(), timeout=120)
    origin = parent / "backlog" / "tasks" / "TASK-2026-09-30-main-002.md"
    origin.write_text(origin.read_text(encoding="utf-8") + "- 모 브랜치 쪽 변경\n", encoding="utf-8")
    origin_before = origin.read_bytes()
    proc = _archive(clone, "claude/heir")
    ok13 = proc.returncode != 0 and origin.read_bytes() == origin_before and heir.exists() and "conflict" in proc.stdout
    _record("test_archive_blocks_on_parent_conflict", ok13,
            f"rc={proc.returncode} origin_same={origin.read_bytes() == origin_before} heir_kept={heir.exists()}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="auto-seed-") as raw:
        tmp = Path(raw)

        # --- case 1 · 2: 새 브랜치 → seed, 재실행은 멱등 -------------------
        clone = _make_repo(tmp / "c1")
        _git(clone, "checkout", "-q", "-b", "claude/probe")
        first = _session_start(clone)
        branch_dir = _active(clone) / "claude" / "probe"
        expected = ["session_handoff.md", "state.json", "backlog/tasks", "sessions"]
        missing = [p for p in expected if not (branch_dir / p).exists()]
        _record("test_new_branch_is_seeded_and_starts",
                first.get("status") == "ok" and _seeded(first) and not missing,
                f"status={first.get('status')} error={first.get('error_code')} "
                f"seeded={_seeded(first)} missing={missing}")

        tasks_before = sorted((branch_dir / "backlog" / "tasks").glob("*.md"))
        second = _session_start(clone)
        tasks_after = sorted((branch_dir / "backlog" / "tasks").glob("*.md"))
        _record("test_rerun_does_not_seed_again",
                second.get("status") == "ok" and not _seeded(second) and tasks_before == tasks_after,
                f"status={second.get('status')} seeded={_seeded(second)} "
                f"tasks {len(tasks_before)}→{len(tasks_after)}")

        # --- case 3: 기본 브랜치 자신 --------------------------------------
        clone = _make_repo(tmp / "c3")
        result = _session_start(clone)
        extra_dirs = sorted(p.name for p in _active(clone).iterdir() if p.is_dir() and p.name != "main")
        _record("test_base_branch_is_not_seeded",
                result.get("status") == "ok" and not _seeded(result) and not extra_dirs,
                f"status={result.get('status')} seeded={_seeded(result)} extra={extra_dirs}")

        # --- case 4: handoff 명시 ------------------------------------------
        clone = _make_repo(tmp / "c4")
        _git(clone, "checkout", "-q", "-b", "feat/explicit")
        result = _session_start(
            clone, "--session-handoff-path",
            str(_active(clone) / "main" / "session_handoff.md"))
        _record("test_explicit_handoff_skips_seed",
                not _seeded(result) and not (_active(clone) / "feat").exists(),
                f"seeded={_seeded(result)} feat_dir={(_active(clone) / 'feat').exists()}")

        # --- case 5: env override ------------------------------------------
        clone = _make_repo(tmp / "c5")
        _git(clone, "checkout", "-q", "-b", "feat/env")
        result = _session_start(clone, env={"CODEX_WORKFLOW_BRANCH": "feat/other"})
        _record("test_env_override_skips_seed",
                not _seeded(result) and not (_active(clone) / "feat").exists(),
                f"seeded={_seeded(result)} status={result.get('status')}")

        # --- case 6: 기본 브랜치 메모리 없는 저장소 --------------------------
        clone = _make_repo(tmp / "c6", with_base_memory=False)
        _git(clone, "checkout", "-q", "-b", "feat/fresh")
        result = _session_start(clone)
        _record("test_no_base_memory_skips_seed",
                result.get("status") == "error" and not _seeded(result)
                and not (_active(clone) / "feat").exists(),
                f"status={result.get('status')} seeded={_seeded(result)}")

        # --- case 7: CI 밖 detached HEAD ------------------------------------
        clone = _make_repo(tmp / "c7")
        _git(clone, "checkout", "-q", "--detach")
        result = _session_start(clone)
        stray = sorted(p.name for p in _active(clone).iterdir() if p.is_dir() and p.name != "main")
        _record("test_local_detached_head_uses_base_namespace",
                result.get("status") == "ok" and not _seeded(result) and not stray,
                f"status={result.get('status')} seeded={_seeded(result)} stray_dirs={stray} "
                "(sha dir 이면 커밋마다 네임스페이스가 바뀐다)")

        # --- case 8: 슬래시 브랜치 task 수집 --------------------------------
        ws = tmp / "c8"
        for branch, task_id, wbs in (("main", "TASK-2026-09-30-main-001", "M-001/WBS-1.1"),
                                     ("claude/probe", "TASK-2026-09-30-claude-probe-001", "exempt")):
            tasks = ws / "ai-workflow" / "memory" / "active" / branch / "backlog" / "tasks"
            tasks.mkdir(parents=True)
            (tasks / f"{task_id}.md").write_text(
                f"---\nid: {task_id}\nstatus: done\nwbs: {wbs}\n"
                + ("wbs_exempt_reason: probe\n" if wbs == "exempt" else "")
                + f"---\n\n# {task_id} — probe\n", encoding="utf-8")
        # 형제 공유 디렉터리(roadmap / memory_index / environments)에 task 모양 파일이
        # 있어도 링크로 오인하지 않는다 — `**` 는 `backlog/tasks/` 바로 아래만 잡는다.
        active = ws / "ai-workflow" / "memory" / "active"
        decoys = {
            "roadmap": "TASK-2026-09-30-decoy-001",
            "memory_index/entries": "TASK-2026-09-30-decoy-002",
            "environments": "TASK-2026-09-30-decoy-003",
        }
        for rel, decoy_id in decoys.items():
            (active / rel).mkdir(parents=True, exist_ok=True)
            (active / rel / f"{decoy_id}.md").write_text(
                f"---\nid: {decoy_id}\nstatus: done\nwbs: M-001/WBS-1.1\n---\n", encoding="utf-8")
        resolution = resolve_task_goals(ws)
        linked = {link.task_id for link in collect_task_wbs_links(ws)}
        _record("test_slash_branch_tasks_are_collected",
                "TASK-2026-09-30-claude-probe-001" in resolution.exempt_tasks
                and {"TASK-2026-09-30-main-001", "TASK-2026-09-30-claude-probe-001"} <= linked
                and not linked & set(decoys.values()),
                f"exempt={resolution.exempt_tasks} linked={sorted(linked)}")

        _inheritance_cases(tmp)

    print()
    if FAILURES:
        print(f"=== FAIL: {len(FAILURES)} case(s) — {FAILURES} ===")
        return 1
    print("=== PASS: branch memory auto-seed (13 cases) ===")
    return 0


def test_branch_memory_auto_seed() -> None:
    assert main() == 0, "branch memory auto-seed FAIL"


if __name__ == "__main__":
    raise SystemExit(main())
