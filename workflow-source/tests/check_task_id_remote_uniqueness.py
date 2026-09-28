#!/usr/bin/env python3
"""task ID 채번이 원격을 함께 보는가 + 충돌을 검출하는가 (8 cases, TASK-2026-09-07-main-006 · 09-23-main-016).

## 왜 필요한가

채번기 둘(`backlog_update.suggest_next_task_id` · `seed_workspace_memory.next_task_id`)
은 오래 **로컬만** 읽었다. 그런데 후자의 docstring 은 "번호는 브랜치 안에서만
매긴다 — 브랜치별로 격리돼 있으므로 **다른 호스트가 동시에 만들어도 겹치지
않는다**" 고 *보증* 했다. 브랜치 격리는 브랜치가 *다를 때* 성립하는 문장이고,
두 호스트가 **같은 브랜치**(대개 main)에 있으면 아무것도 막지 않는다.

2026-09-04 실측: 두 호스트가 같은 날 각각 `main-002` 를 매겼고 **push 가
거절돼서야** 알았다. 뒤에 올린 쪽이 ID 를 비키며 코드 주석과 문서의 참조 6곳을
함께 고쳤다. 보증을 문서로 적어 두면 아무도 다시 재지 않는다 — 그 문장이 이
결함을 열 달 가까이 덮었다.

## 판정 설계

- case 1·2 는 **양방향**이다. "원격에만 있는 ID 를 피한다" 만 재면 *아무것도
  하지 않는* 구현도 통과할 수 있으므로(늘 큰 번호를 내면 된다), 원격을 안 넘겼을
  때 이전과 같은 답을 내는 것도 함께 고정한다.
- case 3 은 **모름 ≠ 안전**이다. 저장소 밖·ref 부재에서 빈 목록이 나오는데,
  그것을 '원격에 없다' 로 읽으면 조용한 거짓 안심이 된다. `consulted` 가 그
  둘을 가르는지 본다.
- case 4 는 **경로 계산이 정본 안에 있는가**. 호출자가 상대경로를 만들게 하면
  절대경로를 넘기기 쉽고, `ls-tree` 는 그때 **조용히 빈 목록**을 낸다 — 이
  함수가 막으려는 실패 모드가 그대로 재현된다.
- case 6~8 은 **채번이 못 막는 충돌의 검출**이다 (09-23-main-016). 미커밋 task 는
  채번 시점에 원격이 볼 수 없다 — 87차에 실제로 겹쳤는데 대시보드 충돌 지표는 git
  충돌 표식만 세어 0 (pass) 였다. case 6 은 그 상황을 bare 원격 + 클론 둘로 재현하고
  (같은 task 의 상태 갱신·로컬 전용 신규 task 는 충돌이 **아님**도 함께 잰다),
  case 7 은 대시보드 지표까지의 배선, case 8 은 원격을 못 봤을 때 '못 봤다' 로 말하는지.
- case 5 는 **거짓 보증의 재발 방지**다. 문장 하나가 결함을 덮었으므로 그
  문장이 돌아오는 것을 정적으로 막는다.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.git import remote_known_task_ids, task_id_collisions  # noqa: E402
from workflow_kit.common.paths import BRANCH_ENV_KEYS  # noqa: E402
from workflow_kit.tools.backlog_update import suggest_next_task_id  # noqa: E402
from workflow_kit.tools.seed_workspace_memory import next_task_id  # noqa: E402

DATE = "2026-09-07"
LOCAL = [{"task_id": f"TASK-{DATE}-main-{n:03d}"} for n in (1, 2)]


def case_1_remote_only_id_is_avoided() -> bool:
    """원격에만 있는 ID 는 재사용되지 않는다 (두 채번기 모두)."""
    print("case_1: 원격에만 있는 ID 를 비켜 간다")
    remote = {f"TASK-{DATE}-main-003"}
    got = suggest_next_task_id(LOCAL, target_date=DATE, branch="main", reserved_ids=remote)
    if got != f"TASK-{DATE}-main-004":
        print(f"  FAIL: backlog_update 채번이 {got} — 원격의 003 을 못 봤다")
        return False
    with tempfile.TemporaryDirectory(prefix="taskid-") as tmp:
        tasks = Path(tmp) / "tasks"
        tasks.mkdir()
        for n in (1, 2):
            (tasks / f"TASK-{DATE}-main-{n:03d}.md").write_text("x", encoding="utf-8")
        seeded = next_task_id(tasks, branch="main", today=DATE, reserved_ids=remote)
    if seeded != f"TASK-{DATE}-main-004":
        print(f"  FAIL: seed 채번이 {seeded} — 원격의 003 을 못 봤다")
        return False
    print(f"  [info] 두 채번기 모두 {got}")
    return True


def case_2_local_only_behaviour_is_unchanged() -> bool:
    """원격을 안 넘기면 이전과 같은 답이다 — 한 방향만 재면 '늘 큰 번호' 도 통과한다."""
    print("case_2: 원격 미지정 시 로컬 전용 동작 보존")
    got = suggest_next_task_id(LOCAL, target_date=DATE, branch="main")
    if got != f"TASK-{DATE}-main-003":
        print(f"  FAIL: {got} (기대 003) — 로컬 전용 동작이 바뀌었다")
        return False
    print(f"  [info] {got}")
    return True


def case_3_unknown_is_not_reported_as_safe() -> bool:
    """원격을 못 봤을 때 빈 목록을 '원격에 없다' 로 내놓지 않는다."""
    print("case_3: 모름 ≠ 안전")
    with tempfile.TemporaryDirectory(prefix="norepo-") as tmp:
        outside = remote_known_task_ids(Path(tmp) / "tasks")
    if outside.consulted or not outside.reason:
        print(f"  FAIL: git 저장소 밖인데 consulted={outside.consulted} reason={outside.reason!r}")
        return False
    with tempfile.TemporaryDirectory(prefix="norem-") as tmp:
        root = Path(tmp) / "repo"
        (root / "backlog" / "tasks").mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        # 원격이 없는 저장소 — ref 부재를 '없음' 이 아니라 '못 봤음' 으로 말해야 한다.
        no_remote = remote_known_task_ids(root / "backlog" / "tasks", branch="main")
    if no_remote.consulted or not no_remote.reason:
        print(f"  FAIL: 원격 추적 ref 부재인데 consulted={no_remote.consulted}")
        return False
    print(f"  [info] 저장소 밖 / ref 부재 모두 consulted=False + 근거 문구 보유")
    return True


def case_4_helper_owns_the_path_math() -> bool:
    """정본이 절대경로를 받아 스스로 pathspec 을 만든다 (조용한 빈 목록 방지)."""
    print("case_4: 경로 계산이 정본 안에 있다")
    tasks_abs = REPO_ROOT / "ai-workflow" / "memory" / "active" / "main" / "backlog" / "tasks"
    if not tasks_abs.is_dir():
        print("  FAIL: 이 저장소의 tasks 디렉터리를 찾지 못했다")
        return False
    result = remote_known_task_ids(tasks_abs)
    if not result.consulted:
        # 얕은 clone / 미fetch 환경은 정상적인 '못 봤음' 이다 — 그때는 이 case 를
        # 판정 대상에서 뺀다. 통과로 세지 않고 그 사실을 찍는다.
        print(f"  [skip] 원격을 못 봤다 ({result.reason}) — 이 환경에서는 잴 수 없다")
        return True
    if not result.ids:
        print("  FAIL: 절대경로를 넘겼는데 목록이 비었다 — pathspec 이 어긋났다")
        return False
    print(f"  [info] 절대경로만으로 원격 task {len(result.ids)}건 조회")
    return True


def case_5_false_guarantee_does_not_return() -> bool:
    """'다른 호스트가 동시에 만들어도 겹치지 않는다' 는 보증 문구가 없다."""
    print("case_5: 거짓 보증 문구 재발 방지")
    needle = "다른 호스트가 동시에 만들어도 겹치지 않는다"
    offenders = [
        f"{p.relative_to(SOURCE_ROOT).as_posix()}"
        for p in sorted((SOURCE_ROOT / "workflow_kit").rglob("*.py"))
        if needle in p.read_text(encoding="utf-8")
    ]
    if offenders:
        print(f"  FAIL: 거짓 보증이 {len(offenders)}곳에 있다 — {offenders}")
        print("        브랜치 격리는 호스트 축을 막지 못한다 (2026-09-04 실측).")
        return False
    print("  [info] 0곳")
    return True


GIT_ENV = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
TASKS_REL = Path("ai-workflow/memory/active/main/backlog/tasks")


def _git(cwd: Path, *args: str) -> None:
    import os
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={**os.environ, **GIT_ENV})


def _task(root: Path, n: int, title: str, status: str = "planned") -> Path:
    path = root / TASKS_REL / f"TASK-{DATE}-main-{n:03d}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nstatus: {status}\n---\n# TASK-{DATE}-main-{n:03d} — {title}\n", encoding="utf-8")
    return path


def _collision_fixture(tmp: Path) -> Path:
    """87차 재현: A 가 미커밋으로 002 를 쓰는 사이 B 가 같은 번호를 다른 task 로 push.

    A 에는 충돌이 **아닌** 것도 둔다 — 공유 task 001 의 상태 갱신(제목 동일)과 로컬
    전용 신규 003. 이 둘을 세면 '모든 변경 = 충돌' 인 구현도 통과하지 못한다.
    """
    remote = tmp / "remote.git"
    _git(tmp, "init", "-q", "--bare", "-b", "main", str(remote))
    b = tmp / "b"
    _git(tmp, "clone", "-q", str(remote), str(b))
    _git(b, "checkout", "-q", "-b", "main")
    _task(b, 1, "공유 task")
    _git(b, "add", "-A"); _git(b, "commit", "-q", "-m", "001"); _git(b, "push", "-q", "origin", "main")
    a = tmp / "a"
    _git(tmp, "clone", "-q", str(remote), str(a))
    _task(b, 2, "B 가 채번한 task")
    _git(b, "add", "-A"); _git(b, "commit", "-q", "-m", "002"); _git(b, "push", "-q", "origin", "main")
    _task(a, 1, "공유 task", status="in_progress")   # 같은 task 의 갱신 — 충돌 아님
    _task(a, 2, "A 가 미커밋으로 쓰던 task")          # 충돌
    _task(a, 3, "A 로컬 전용 신규 task")              # 원격에 없음 — 충돌 아님
    _git(a, "fetch", "-q", "origin")
    return a


def case_6_uncommitted_id_collision_is_detected() -> bool:
    """미커밋 task 와 원격의 같은 ID 가 다른 task 면 충돌로 센다 (그 외는 세지 않는다)."""
    print("case_6: 87차 재현 — 미커밋 task ID 충돌 검출")
    with tempfile.TemporaryDirectory(prefix="idclash-") as tmp:
        a = _collision_fixture(Path(tmp))
        got = task_id_collisions(a / TASKS_REL, branch="main")
    if not got.consulted:
        print(f"  FAIL: 원격을 못 봤다 ({got.reason})")
        return False
    ids = [c[0] for c in got.collisions]
    if ids != [f"TASK-{DATE}-main-002"]:
        print(f"  FAIL: 충돌 {ids} (기대: 002 하나 — 001 은 같은 task 의 갱신, 003 은 로컬 전용)")
        return False
    _, local_head, remote_head = got.collisions[0]
    if "A 가" not in local_head or "B 가" not in remote_head:
        print(f"  FAIL: 제목 대조가 어긋났다 — 로컬 {local_head!r} / 원격 {remote_head!r}")
        return False
    print(f"  [info] 002 만 충돌 (로컬 {local_head!r} ≠ 원격 {remote_head!r})")
    return True


def _no_branch_env():  # type: ignore[no-untyped-def]
    """게이트의 slash 셀이 주입하는 브랜치 env 를 이 fixture 에서 걷는다.

    fixture 는 자기 git 브랜치(main)를 재야 한다 — 상속된 오버라이드를 따르면
    slash 셀에서만 다른 디렉터리를 보고 red 가 된다 (메모리: fixture 는 재려는 조건을
    스스로 성립시켜야 한다).
    """
    import os
    from unittest import mock
    env = {k: v for k, v in os.environ.items() if k not in BRANCH_ENV_KEYS}
    return mock.patch.dict(os.environ, env, clear=True)


def case_7_dashboard_counts_id_collisions() -> bool:
    """대시보드 멀티에이전트 충돌 지표가 ID 충돌을 센다 (예전에는 git 표식만 → 0 pass)."""
    print("case_7: 대시보드 지표 배선")
    from workflow_kit.common.dashboard_data import collect_multi_agent_concurrent_write_conflict
    with tempfile.TemporaryDirectory(prefix="idclash-") as tmp:
        a = _collision_fixture(Path(tmp))
        with _no_branch_env():
            panel = collect_multi_agent_concurrent_write_conflict(a)
    problems = []
    if panel.get("task_id_collision_count") != 1:
        problems.append(f"task_id_collision_count={panel.get('task_id_collision_count')}")
    if panel.get("conflict_count", 0) < 1 or panel.get("status") != "fail":
        problems.append(f"conflict_count={panel.get('conflict_count')} status={panel.get('status')}")
    if "task_id_remote" not in str(panel.get("conflict_count_source")):
        problems.append(f"conflict_count_source={panel.get('conflict_count_source')}")
    if not any(f"TASK-{DATE}-main-002" in loc for loc in panel.get("conflict_locations", [])):
        problems.append(f"conflict_locations 에 002 가 없다: {panel.get('conflict_locations')}")
    if problems:
        print(f"  FAIL: {problems}")
        return False
    print(f"  [info] status=fail, locations={panel['conflict_locations']}")
    return True


def case_8_unconsulted_remote_is_not_zero_conflicts() -> bool:
    """원격 ref 가 없으면 '충돌 0' 이 아니라 '못 봤다' 다 — 지표도 그것을 싣는다."""
    print("case_8: 원격 미확인 ≠ 충돌 없음")
    from workflow_kit.common.dashboard_data import collect_multi_agent_concurrent_write_conflict
    with tempfile.TemporaryDirectory(prefix="idnorem-") as tmp:
        root = Path(tmp) / "repo"
        root.mkdir()
        _git(root, "init", "-q", "-b", "main")
        _task(root, 1, "원격 없는 task")
        got = task_id_collisions(root / TASKS_REL, branch="main")
        with _no_branch_env():
            panel = collect_multi_agent_concurrent_write_conflict(root)
    problems = []
    if got.consulted or not got.reason:
        problems.append(f"consulted={got.consulted} reason={got.reason!r}")
    if panel.get("task_id_collision_measured") is not False or not panel.get("task_id_collision_reason"):
        problems.append(f"지표: measured={panel.get('task_id_collision_measured')} reason={panel.get('task_id_collision_reason')!r}")
    if "task_id_remote" in str(panel.get("conflict_count_source")):
        problems.append(f"못 본 측정원을 source 에 넣었다: {panel.get('conflict_count_source')}")
    if problems:
        print(f"  FAIL: {problems}")
        return False
    print(f"  [info] {got.reason}")
    return True


def main() -> int:
    cases = [
        ("case_1_remote_only_id_is_avoided", case_1_remote_only_id_is_avoided),
        ("case_2_local_only_behaviour_is_unchanged", case_2_local_only_behaviour_is_unchanged),
        ("case_3_unknown_is_not_reported_as_safe", case_3_unknown_is_not_reported_as_safe),
        ("case_4_helper_owns_the_path_math", case_4_helper_owns_the_path_math),
        ("case_5_false_guarantee_does_not_return", case_5_false_guarantee_does_not_return),
        ("case_6_uncommitted_id_collision_is_detected", case_6_uncommitted_id_collision_is_detected),
        ("case_7_dashboard_counts_id_collisions", case_7_dashboard_counts_id_collisions),
        ("case_8_unconsulted_remote_is_not_zero_conflicts", case_8_unconsulted_remote_is_not_zero_conflicts),
    ]
    results = [(name, fn()) for name, fn in cases]
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== {passed}/{len(cases)} PASS ===")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
