#!/usr/bin/env python3
"""handoff §5 의 **작업 후보**가 열린 task 를 가리키는가 (TASK-2026-08-22-main-001).

## 왜 필요한가

§5 "다음 세션 시작 포인트" 는 다음 세션이 **가장 먼저 읽는 자리**다. 그런데 그
목록은 판정 기준이 서로 다른 네 부류를 한 덩어리로 섞어 두고 있었다:

1. 사용자 행동 (`wk doctor` 의 `runtime_load` 가 **이미 잰다**)
2. 진짜 작업 후보 (SSOT 없음)
3. 소유자 결정 대기 (task 가 아니다)
4. 이미 열린 task (`state.json` 이 **이미 싣는다**)

넷 중 **둘은 기계가 읽는 자리를 가진 채 산문이 그것을 복제**하고 있었고, 복제는
갈라진다. 2026-08-20 하루에 잔재 두 건이 확인됐다 — `TASK-2026-08-14-main-018` 은
정본이 이미 해소를 선언한 gap 3 이었고(6일간 후보로 떠 있었다), "OKF v0.2 이행
ADR 후속" 은 `main-003` 이 닫은 일이었다(`OKF_SPEC_VERSION` 은 이미 0.2).

**목록이 낡았다는 것을 아무것도 말해 주지 않는 것이 결함이다.** 그래서 부류를
갈라 각자의 SSOT 로 보내고, 그중 기계가 판정할 수 있는 한 부류 — 작업 후보 — 에
대해 이 검사가 대조한다.

## 판정 규칙

`#### 작업 후보` 소절의 각 최상위 불릿은

1. `TASK-<YYYY-MM-DD>-<slug>-<NNN>` 형식의 ID 를 **하나 이상** 인용해야 한다.
2. 그 task 파일이 `backlog/tasks/` 에 실재해야 한다.
3. 그 task 의 frontmatter `status` 가 `planned` 또는 `in_progress` 여야 한다.
   `done` / `blocked` 은 "지금 할 일" 이 아니다.

**ID 는 markdown 링크가 아니라 평문으로 인용한다.** `parse_handoff` 의
`next_documents` 가 파일 **전체**의 markdown 링크를 긁어가므로, 링크로 적으면
후보를 하나 더할 때마다 state.json 의 "다음에 읽을 문서" 가 같이 부푼다.

## 한계 (과장하지 않는다)

나머지 세 부류(결정 대기 · 환경 상태 · 관찰 축)는 **기계가 낡음을 판정할 수 없다** —
결정은 사람이 내리고, 환경은 `wk doctor` 가 그때그때 재며, 관찰은 신호를 기다린다.
이 검사는 그것들을 보지 않는다. 재지 못하는 것을 재는 척하지 않는다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.paths import (  # noqa: E402
    memory_active_dir,
    state_path_for_workspace,
)
from workflow_kit.common.project_docs import TASK_STATUSES  # noqa: E402

#: "지금 할 일" 로 인정하는 status. 어휘는 `TASK_STATUSES` 가 정본이고 여기서는
#: 그중 **열린 것**만 고른다 — 목록을 따로 적으면 어휘가 늘 때 갈라진다.
OPEN_STATUSES = tuple(s for s in TASK_STATUSES if s in {"planned", "in_progress"})

CANDIDATE_HEADING = "#### 작업 후보"
TASK_ID_RE = re.compile(r"TASK-\d{4}-\d{2}-\d{2}-[A-Za-z0-9_.-]+-\d{3}")
STATUS_RE = re.compile(r"^status:\s*(\S+)\s*$", re.M)

#: 이 검사가 관찰하는 저장소 경로. `--changed` 가 이 선언을 보고 건너뛸지 정한다.
#: 목록을 runner 안에 두지 않는 이유는 정본과 같다 — 파일에서 멀어지면 드리프트한다.
WATCHES = (
    "ai-workflow/memory/active/*/session_handoff.md",
    "ai-workflow/memory/active/*/backlog/tasks/*.md",
)

FAILURES: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case}{(' — ' + detail) if detail else ''}")
        FAILURES.append(case)


def _handoff_target() -> tuple[Path, str]:
    """**어느 브랜치 메모리의** handoff 를 볼지 + 그 근거.

    이 검사가 묻는 것은 "이 *저장소* 의 §5 계약이 지켜지는가" 이지 "이 *브랜치* 에서
    세션을 시작한 적이 있는가" 가 아니다. `ai-workflow/memory/active/<branch>/` 는
    브랜치 이름으로 갈리므로, session-start 를 아직 안 돌린 브랜치에는 handoff 가
    **없다** — 그것은 결함이 아니라 CLAUDE.md self-bootstrap 이 선언한 상태다.

    처음 판이 그 자리를 FAIL 로 처리해 `slash` 브랜치 컨텍스트에서 red 였다.
    smoke 는 모든 브랜치에서 도므로, 브랜치를 하나 따는 순간 자기 변경과 무관하게
    CI 가 red 가 된다 — **위양성을 내는 검사는 무시당하고, 그러면 같은 검사가
    잡아 줄 진짜 결함도 함께 무시된다.** `check_self_application` 이 같은 함정을
    이미 겪고 남긴 처방을 그대로 따른다: 없으면 기존 브랜치 메모리로 검증하되
    **바꿔치기한 사실을 반드시 밝힌다.**
    """
    current = state_path_for_workspace(REPO_ROOT).parent
    if (current / "session_handoff.md").is_file():
        return current, "current-branch"

    active = memory_active_dir(REPO_ROOT)
    fallbacks = sorted(
        (q.parent for q in active.rglob("session_handoff.md") if q.parent != current),
        key=lambda q: (q.name != "main", q.as_posix()),
    )
    if not fallbacks:
        return current, "none"
    chosen = fallbacks[0]
    return chosen, f"fallback:{chosen.relative_to(active).as_posix()}"


def _candidate_bullets(text: str) -> list[str] | None:
    """`#### 작업 후보` 소절의 최상위 불릿들. 소절이 없으면 None."""
    if CANDIDATE_HEADING not in text:
        return None
    body = text.split(CANDIDATE_HEADING, 1)[1]
    # 다음 `#### ` 또는 `### ` 가 소절의 끝이다.
    for terminator in ("\n#### ", "\n### ", "\n## "):
        if terminator in body:
            body = body.split(terminator, 1)[0]
    bullets: list[str] = []
    for line in body.splitlines():
        if line.startswith("- "):
            bullets.append(line[2:].strip())
        elif bullets and line.startswith("  "):
            # 이어지는 들여쓰기 줄은 같은 불릿의 일부다.
            bullets[-1] += " " + line.strip()
    return bullets


def test_candidates_cite_open_tasks() -> None:
    branch_dir, provenance = _handoff_target()
    handoff = branch_dir / "session_handoff.md"
    if provenance == "none":
        _record(
            "test_candidates_cite_open_tasks",
            False,
            f"어느 브랜치에도 handoff 가 없다 ({memory_active_dir(REPO_ROOT)})",
        )
        return
    if provenance != "current-branch":
        print(f"  [info] 현재 브랜치에 handoff 가 없어 {provenance} 로 검증한다 "
              "— session-start 미실행 상태다")
    text = handoff.read_text(encoding="utf-8")
    bullets = _candidate_bullets(text)
    if bullets is None:
        _record(
            "test_candidates_cite_open_tasks",
            False,
            f"`{CANDIDATE_HEADING}` 소절이 없다 — §5 의 부류 분리 계약이 깨졌는가",
        )
        return

    tasks_dir = branch_dir / "backlog" / "tasks"
    problems: list[str] = []
    for bullet in bullets:
        ids = TASK_ID_RE.findall(bullet)
        if not ids:
            problems.append(
                f"task ID 를 인용하지 않은 후보: {bullet[:60]!r} — 작업 후보가 "
                "아니면 '결정 대기' / '관찰 축' 소절로 옮길 것"
            )
            continue
        for task_id in ids:
            path = tasks_dir / f"{task_id}.md"
            if not path.is_file():
                problems.append(f"{task_id}: task 파일이 없다 ({path})")
                continue
            match = STATUS_RE.search(path.read_text(encoding="utf-8"))
            if match is None:
                problems.append(f"{task_id}: frontmatter 에 status 가 없다")
                continue
            status = match.group(1)
            if status not in OPEN_STATUSES:
                problems.append(
                    f"{task_id}: status={status} — 열린 것이 아니다. "
                    f"§5 의 작업 후보는 {list(OPEN_STATUSES)} 만 인용한다"
                )
    _record("test_candidates_cite_open_tasks", not problems, "; ".join(problems))


def test_candidates_do_not_use_markdown_links() -> None:
    """후보의 task 인용이 **평문**인가.

    `parse_handoff` 의 `next_documents` 는 handoff **파일 전체**의 markdown 링크를
    긁어간다. 후보를 링크로 적으면 후보를 하나 더할 때마다 state.json 의 "다음에
    읽을 문서" 가 같이 부푼다 — 그 목록은 *문서* 를 위한 자리지 *작업* 을 위한
    자리가 아니다.
    """
    branch_dir, provenance = _handoff_target()
    if provenance == "none":
        _record("test_candidates_do_not_use_markdown_links", False,
                "어느 브랜치에도 handoff 가 없다")
        return
    handoff = branch_dir / "session_handoff.md"
    bullets = _candidate_bullets(handoff.read_text(encoding="utf-8")) or []
    linked = [b[:60] for b in bullets if re.search(r"\[[^\]]*TASK-[^\]]*\]\(", b)]
    _record(
        "test_candidates_do_not_use_markdown_links",
        not linked,
        f"task 를 markdown 링크로 인용한 후보: {linked} — 평문 ID 로 적을 것",
    )


def main() -> int:
    cases = [
        test_candidates_cite_open_tasks,
        test_candidates_do_not_use_markdown_links,
    ]
    for case in cases:
        case()
    total = len(cases)
    print(f"\n{total - len(FAILURES)}/{total} passed")
    if FAILURES:
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
