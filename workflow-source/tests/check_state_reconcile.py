#!/usr/bin/env python3
"""handoff ↔ backlog 상태 정합 비교의 계약을 고정한다 (TASK-2026-09-02-main-002, 7 cases).

## 왜 필요한가

이 비교는 **한 번도 검사에 덮인 적이 없었고**, 그래서 세 겹으로 틀린 채로 돌았다:

1. **분모** — `session-start` 가 handoff 의 열린 작업 전체를 *오늘자 daily
   backlog 하나* 와 비교했다. append-only 레이아웃에서 in_progress task 는
   **등록된 날짜의 파일**에 있으므로, 하루 안에 끝나지 않은 작업이 하나만 있어도
   날이 바뀌는 순간부터 매 세션 시작마다 거짓 경고가 났다.
2. **키** — 문자열 집합 비교라 handoff 의 `TASK-… <제목>` 과 corpus 의 `TASK-…`
   가 서로 다른 원소였다. 같은 저장소의 `dedupe_work_items` 는 이미 ID 를 키로
   쓴다(정본은 ID 로 볼 줄 알았고 경고 경로만 몰랐다).
3. **설명** — "다를 수 있으므로 수동 재확인이 필요하다" 만 냈다. 차집합은 도구가
   이미 들고 있는데 사람이 매번 두 문서를 손으로 대조했다.

순효과는 늑대 소년이다. 거의 항상 거짓인 경고가 `recommended_next_action` 까지
점거해, 진짜 불일치가 났을 때 구분이 안 된다.

## 되주입 방향

case 2(오탐이 사라졌다)만 재면 **아무것도 안 잡는** 구현이 통과한다. 그래서
case 3·4 를 같이 둔다 — 진짜 불일치는 양방향(handoff 에만 / backlog 에만) 모두
여전히 red 여야 하고, 문안이 **어느 항목인지** 짚어야 한다.

Refs:
  - workflow_kit/common/reconcile.py — 비교 정본
  - workflow_kit/common/state/builder.py — `collect_task_corpus_status` (분모 정본)
  - workflow_kit/tools/session_start.py · skills/merge-doc-reconcile — 소비자
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.reconcile import (  # noqa: E402
    STATE_CONFLICT_MARKER,
    compare_state_lists,
    diff_state_lists,
)
from workflow_kit.common.state.builder import collect_task_corpus_status  # noqa: E402

#: 의도적 전역 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES_ALL_REASON = (
    "case 7 이 이 저장소 자신에게 session-start 를 통째로 돌린다 — 판정 대상이 저장소의 "
    "살아있는 memory 트리(task corpus 365개 + handoff)라 표면이 곧 저장소다. meta-watch "
    "실측 (2026-09-02) 접근 457건"
)

# case 7 이 저장소의 살아있는 memory 문서를 관찰한다.
REQUIRES_QUIET_REPO = True

TOOL_PATH = SOURCE_ROOT / "workflow_kit" / "tools" / "session_start.py"
BRANCH = "main"

# 어제 등록되어 오늘로 넘어온 작업 / 오늘 등록된 작업.
CARRIED = "TASK-2026-01-01-main-001"
TODAY = "TASK-2026-01-02-main-002"


def _run_session_start(profile: Path) -> tuple[int, dict]:
    env = dict(os.environ)
    env["CODEX_WORKFLOW_BRANCH"] = BRANCH
    proc = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--project-profile-path", str(profile)],
        capture_output=True, text=True, timeout=180, env=env,
    )
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        raise AssertionError(f"tool 출력이 JSON 이 아니다:\n{proc.stdout}\n{proc.stderr}")
    return proc.returncode, payload


def _conflict_warnings(payload: dict) -> list[str]:
    return [w for w in payload.get("warnings", []) if STATE_CONFLICT_MARKER in w]


def _task_file(tasks_dir: Path, task_id: str, status: str, title: str) -> None:
    date = task_id.split("-")[1:4]
    (tasks_dir / f"{task_id}.md").write_text(
        f"---\nid: {task_id}\nstatus: {status}\ncreated_at: {'-'.join(date)}\n"
        f"source_anchor: generic-{task_id.lower()}\nsource_path: backlog/{'-'.join(date)}.md\n"
        f"kind: generic\n---\n\n# {task_id} — {title}\n",
        encoding="utf-8",
    )


def _write_handoff(branch_dir: Path, in_progress: list[str], blocked: list[str]) -> None:
    def block(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items) if items else "-"

    (branch_dir / "session_handoff.md").write_text(
        "# Session Handoff\n\n"
        "## 1. 현재 작업 요약\n\n- 현재 기준선: fixture baseline\n\n"
        f"## 2. 진행 중 작업\n\n- 현재 `in_progress` 작업:\n{block(in_progress)}\n\n"
        f"## 3. 차단 작업\n\n- 현재 `blocked` 작업:\n{block(blocked)}\n\n"
        "## 4. 최근 완료 작업\n\n- 최근 완료 작업 목록:\n-\n",
        encoding="utf-8",
    )


def _build_fixture(root: Path) -> Path:
    """어제 시작한 in_progress 작업 + 오늘 끝난 작업. 실제 세션의 정상 상태다."""
    (root / "docs").mkdir(parents=True)
    profile = root / "docs" / "PROJECT_PROFILE.md"
    profile.write_text("# profile\n", encoding="utf-8")
    branch_dir = root / "ai-workflow" / "memory" / "active" / BRANCH
    tasks_dir = branch_dir / "backlog" / "tasks"
    tasks_dir.mkdir(parents=True)
    (branch_dir / "sessions").mkdir(parents=True)

    # handoff 는 제목을 달고 적는다 — corpus 는 ID 만 낸다 (case 1 의 키 비교).
    _write_handoff(branch_dir, [f"{CARRIED} 어제 시작해 오늘로 넘어온 작업"], [])

    _task_file(tasks_dir, CARRIED, "in_progress", "어제 시작해 오늘로 넘어온 작업")
    _task_file(tasks_dir, TODAY, "done", "오늘 등록하고 오늘 끝낸 작업")

    backlog_dir = branch_dir / "backlog"
    (backlog_dir / "2026-01-01.md").write_text(
        "# Daily Backlog — 2026-01-01\n\n"
        f"- **{CARRIED}** [generic] 어제 시작해 오늘로 넘어온 작업\n"
        f"  - path: [`./tasks/{CARRIED}.md`](./tasks/{CARRIED}.md)\n"
        "  - status: in_progress\n",
        encoding="utf-8",
    )
    # **최신 daily backlog 에는 in_progress 가 하나도 없다** — 결함의 재현 조건이다.
    (backlog_dir / "2026-01-02.md").write_text(
        "# Daily Backlog — 2026-01-02\n\n"
        f"- **{TODAY}** [generic] 오늘 등록하고 오늘 끝낸 작업\n"
        f"  - path: [`./tasks/{TODAY}.md`](./tasks/{TODAY}.md)\n"
        "  - status: done\n",
        encoding="utf-8",
    )
    return profile


def case_1_id_is_the_key() -> None:
    """handoff 의 `ID 제목` 과 corpus 의 `ID` 는 같은 항목이다."""
    assert compare_state_lists([f"{CARRIED} 어제 시작한 작업"], [CARRIED], "in_progress") == [], (
        "제목이 붙었다고 다른 항목으로 봤다 — 문자열 집합 비교로 되돌아갔다"
    )
    # backtick 표기도 같은 항목이다 (handoff 산문에서 흔하다).
    assert compare_state_lists([f"`{CARRIED}` 어제 시작한 작업"], [CARRIED], "in_progress") == []


def case_2_denominator_is_the_corpus(profile: Path) -> None:
    """어제 등록된 in_progress 가 있어도 경고가 없다 — 이 검사의 핵심 회귀 가드."""
    rc, payload = _run_session_start(profile)
    assert rc == 0, f"session-start 실패: {payload}"
    conflicts = _conflict_warnings(payload)
    assert not conflicts, (
        "handoff 와 task corpus 가 일치하는데 불일치 경고가 났다 — 비교 분모가 다시 "
        f"하루치 backlog 로 돌아갔다: {conflicts}"
    )
    assert payload.get("in_progress_items"), "기준선 자체가 비었다 (fixture 가 깨졌다)"


def case_3_reinjection_only_in_handoff(root: Path, profile: Path) -> None:
    """corpus 에 없는 항목이 handoff 에 있으면 red — 그리고 어느 항목인지 짚는다."""
    branch_dir = root / "ai-workflow" / "memory" / "active" / BRANCH
    ghost = "TASK-2026-01-01-main-999"
    _write_handoff(
        branch_dir,
        [f"{CARRIED} 어제 시작해 오늘로 넘어온 작업", f"{ghost} corpus 에 없는 유령 항목"],
        [],
    )
    try:
        _rc, payload = _run_session_start(profile)
        conflicts = _conflict_warnings(payload)
        assert conflicts, "가짜를 심었는데 통과했다 — 검사가 죽었다"
        assert any(ghost in w and "handoff 에만" in w for w in conflicts), (
            f"어느 항목이 어느 쪽에만 있는지 문안이 짚지 않는다: {conflicts}"
        )
        assert not any(CARRIED in w for w in conflicts), (
            f"정합인 항목까지 충돌로 실었다: {conflicts}"
        )
    finally:
        _write_handoff(branch_dir, [f"{CARRIED} 어제 시작해 오늘로 넘어온 작업"], [])


def case_4_reinjection_only_in_backlog(root: Path, profile: Path) -> None:
    """handoff 가 빈 채 corpus 에 in_progress 가 있으면 red (반대 방향)."""
    branch_dir = root / "ai-workflow" / "memory" / "active" / BRANCH
    _write_handoff(branch_dir, [], [])
    try:
        _rc, payload = _run_session_start(profile)
        conflicts = _conflict_warnings(payload)
        assert conflicts, "handoff 가 corpus 의 열린 작업을 통째로 빠뜨렸는데 통과했다"
        assert any(CARRIED in w and "backlog 에만" in w for w in conflicts), (
            f"backlog 쪽 누락을 문안이 짚지 않는다: {conflicts}"
        )
    finally:
        _write_handoff(branch_dir, [f"{CARRIED} 어제 시작해 오늘로 넘어온 작업"], [])


def case_5_blocked_axis_is_labelled() -> None:
    """blocked 도 같은 규율을 타고, 라벨이 섞이지 않는다."""
    warnings = compare_state_lists(["TASK-2026-01-01-main-003 막힌 작업"], [], "blocked")
    assert len(warnings) == 1 and warnings[0].startswith("blocked "), f"라벨 오염: {warnings}"
    only_handoff, only_backlog = diff_state_lists([], ["TASK-2026-01-01-main-003"])
    assert only_handoff == [] and only_backlog == ["TASK-2026-01-01-main-003"], (
        f"차집합 방향이 뒤집혔다: {only_handoff} / {only_backlog}"
    )


def case_6_missing_corpus_is_not_empty_corpus(root: Path) -> None:
    """corpus 부재는 '비었다' 가 아니다 — legacy 프로젝트를 뒤집지 않는다."""
    assert collect_task_corpus_status(None) is None
    empty = root / "no-such-backlog-dir"
    assert collect_task_corpus_status(empty) is None, (
        "corpus 가 없는데 빈 집계를 냈다 — legacy handoff 전체가 '분모에 없음' 으로 뒤집힌다"
    )
    present = collect_task_corpus_status(
        root / "ai-workflow" / "memory" / "active" / BRANCH / "backlog"
    )
    assert present is not None and present["in_progress_items"] == [CARRIED], (
        f"corpus 집계가 SSOT 와 다르다: {present}"
    )


def case_7_self_application() -> None:
    """이 저장소의 handoff 와 task corpus 가 실제로 정합이다."""
    profile = REPO_ROOT / "docs" / "PROJECT_PROFILE.md"
    if not profile.is_file():
        raise AssertionError("자기 적용 대상 문서가 없다 (PROJECT_PROFILE.md 부재)")
    _rc, payload = _run_session_start(profile)
    conflicts = _conflict_warnings(payload)
    assert not conflicts, (
        "이 저장소의 handoff 가 backlog SSOT 와 갈라졌다. task 상태는 "
        f"`wk backlog-update` 로 갱신한다 (handoff 를 손으로 고치지 않는다): {conflicts}"
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="check-state-reconcile-") as tmp:
        root = Path(tmp).resolve()  # macOS /private symlink (TASK-017)
        profile = _build_fixture(root)
        case_1_id_is_the_key()
        case_2_denominator_is_the_corpus(profile)
        case_3_reinjection_only_in_handoff(root, profile)
        case_4_reinjection_only_in_backlog(root, profile)
        case_5_blocked_axis_is_labelled()
        case_6_missing_corpus_is_not_empty_corpus(root)
    case_7_self_application()
    print("handoff/backlog state reconcile check passed (7 cases)")
    return 0


def test_case_1() -> None:
    case_1_id_is_the_key()


def test_case_5() -> None:
    case_5_blocked_axis_is_labelled()


if __name__ == "__main__":
    raise SystemExit(main())
