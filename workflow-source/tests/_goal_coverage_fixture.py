"""goal coverage 판정의 **실물을 닮은** fixture (TASK-2026-09-21-main-001).

옛 fixture 는 goal 문자열을 deliverable 안에 통째로 넣어 두고 coverage 100 을
받았다 (`G1: 표준 워크플로우` ↔ `표준 워크플로우 패키지의 배포 경로를 정리했다`).
실물에서는 **정확히 0** 이었다 — Goals 는 전략 산문이고 완료 항목은 결함수리
제목이라 낱말을 공유할 이유가 없다. fixture 가 100 을 찍고 실물이 0 을 찍는
동안 둘을 대조하는 자리가 없었다.

그래서 이 fixture 는 두 성질을 **동시에** 갖도록 만든다:

1. goal 산문과 완료 항목 제목의 어휘 겹침이 0 이다 (실물을 닮았다).
2. 그런데도 선언 사슬(`task.wbs → milestone.wbs_goals/goals → PURPOSE §1`)로는
   닿는다 — 즉 판정이 어휘가 아니라 선언을 읽고 있음을 fixture 자신이 증명한다.

`assert_fixture_resembles_reality` 가 1번을 매 사용처에서 다시 잰다. 어휘가
겹치게 fixture 가 흘러가면 그 자리에서 red 가 된다.
"""
from __future__ import annotations

import json
from pathlib import Path

#: goal 산문 — 실물처럼 전략 어휘로 쓴다 (12~15 토큰).
GOALS: dict[str, str] = {
    "G1": "여러 프로젝트에서 공통으로 사용할 수 있는 표준 협업 워크플로우를 독립 패키지 형태로 제공",
    "G2": "구현 기준을 프로젝트별 차이와 공통 규약으로 분리하여 재현 가능한 운영 보장",
    "G3": "외부 소비자가 안정된 라이브러리처럼 신뢰하도록 버전 약속을 지켜 운영",
}

#: 완료 항목 — 실물처럼 결함수리 제목으로 쓴다. 위 산문과 낱말이 겹치지 않는다.
DONE_ITEMS: list[tuple[str, str, str]] = [
    # (task_id, 제목, wbs 선언)
    ("TASK-2026-01-01-main-001", "탐침이 읽히지 않는 사본을 재고 있었다 — 소스 유형을 읽는다", "M-100/WBS-100.2"),
    ("TASK-2026-01-01-main-002", "한 호스트 채널이 다섯 주 낡아 있었다 — 재적용", "M-100/WBS-100.1"),
    ("TASK-2026-01-01-main-003", "형제 생성물이 갱신을 안 따라간다 — 쓰는 층에 흡수", "M-100/WBS-100.2"),
    ("TASK-2026-01-02-main-004", "배포 꾸러미 발행 사이클 한 바퀴", "M-101/WBS-101.1"),
]

MILESTONES: list[dict[str, object]] = [
    {
        "id": "M-100",
        "slug": "standing-operations",
        "title": "운영 축 (상설)",
        "phase": "stabilization",
        "status": "in_progress",
        "order": 1,
        "goals": [],
        "wbs_goals": {"WBS-100.1": ["G1"], "WBS-100.2": ["G2"]},
        "wbs": [("WBS-100.1", "결함 수리 — 플랫폼"), ("WBS-100.2", "결함 수리 — 탐침·도구")],
    },
    {
        "id": "M-101",
        "slug": "release-cycle",
        "title": "릴리스 사이클",
        "phase": "release",
        "status": "in_progress",
        "order": 2,
        "goals": ["G3"],
        "wbs_goals": {},
        "wbs": [("WBS-101.1", "발행 + 채널 재적용")],
    },
]


def _purpose_text() -> str:
    goal_lines = "\n".join(f"- **{gid}**: {text}" for gid, text in GOALS.items())
    return (
        "---\npurpose_version: 1\nlast_purpose_review: 2026-01-01\n---\n\n"
        f"## 1. Goals\n\n{goal_lines}\n\n"
        "## 2. Key Questions\n\n- **Q1**: 어떻게 재현하는가?\n\n"
        "## 3. Research Scope\n\n### 포함\n- 공통 표준 문서\n\n"
        "### 제외\n- 도메인 로직\n- 학습 파이프라인\n\n"
        "## 4. Evolving Thesis\n\n선언이 추측을 이긴다.\n"
    )


def build_workspace(ws: Path, *, branch: str = "main", omit_goals: bool = False) -> Path:
    """실물을 닮은 workspace 를 만든다.

    Args:
        ws: workspace root.
        branch: task 파일이 놓일 브랜치 네임스페이스.
        omit_goals: True 면 마일스톤의 goals/wbs_goals 선언을 **비운다** —
            '선언을 안 하면 못 잰다' 를 재는 되주입 case 용이다.
    """
    active = ws / "ai-workflow" / "memory" / "active"
    active.mkdir(parents=True, exist_ok=True)
    (active / "PURPOSE.md").write_text(_purpose_text(), encoding="utf-8")

    # cross-ref 부재 warning 방지 (다른 판정과 같은 관행)
    concepts = ws / "ai-workflow" / "wiki" / "concepts"
    concepts.mkdir(parents=True, exist_ok=True)
    (concepts / "dummy.md").write_text("# d\n", encoding="utf-8")

    (active / "state.json").write_text(
        json.dumps(
            {"session": {"recent_done_items": [f"{tid} — {title}" for tid, title, _ in DONE_ITEMS]}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    roadmap = active / "roadmap"
    roadmap.mkdir(parents=True, exist_ok=True)
    index_lines = ["# Roadmap Index", "", "- 상태: active", "", "## Milestones", ""]
    for m in MILESTONES:
        path_name = f"{m['id']}-{m['slug']}.md"
        index_lines.append(f"- **{m['id']}** [{m['phase']}] {m['title']} — status: {m['status']}")
        index_lines.append(f"  - path: [`./{path_name}`](./{path_name})")
        goals = [] if omit_goals else m["goals"]
        wbs_goals = {} if omit_goals else m["wbs_goals"]
        front = [
            "---",
            f"id: {m['id']}",
            f"title: {m['title']}",
            f"sdlc_phase: {m['phase']}",
            f"status: {m['status']}",
            f"order: {m['order']}",
            "parallel_allowed: []",
            "deliverables: []",
            f"goals: [{', '.join(goals)}]" if goals else "goals: []",
        ]
        if wbs_goals:
            front.append("wbs_goals:")
            front.extend(f"  - {k} -> {', '.join(v)}" for k, v in wbs_goals.items())
        front.append("---")
        body = [f"\n# {m['id']} — {m['title']}\n", "## WBS", ""]
        body.extend(f"- **{nid}** {title}" for nid, title in m["wbs"])
        (roadmap / path_name).write_text("\n".join(front + body) + "\n", encoding="utf-8")
    (roadmap / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    tasks = active / branch / "backlog" / "tasks"
    tasks.mkdir(parents=True, exist_ok=True)
    for tid, title, wbs in DONE_ITEMS:
        (tasks / f"{tid}.md").write_text(
            f"---\nid: {tid}\nstatus: done\nkind: generic\nwbs: {wbs}\n---\n\n# {tid} — {title}\n",
            encoding="utf-8",
        )
    return ws


def assert_fixture_resembles_reality() -> tuple[int, int]:
    """fixture 의 goal↔완료항목 **어휘 겹침이 0** 임을 다시 잰다.

    이 함수가 지키는 성질이 깨지면 fixture 는 다시 항등함수를 재게 된다.
    문자열 완전일치만 보던 옛 가드는 부분문자열 복사를 통과시켰으므로,
    여기서는 **겹침 비율 자체**를 잰다.

    Returns:
        (검사한 goal 수, 검사한 완료 항목 수)
    """
    from workflow_kit.common.purpose_graph import _tokenize

    done_tokens: set[str] = set()
    for _, title, _ in DONE_ITEMS:
        done_tokens |= set(_tokenize(title))

    for gid, text in GOALS.items():
        goal_tokens = set(_tokenize(text))
        overlap = goal_tokens & done_tokens
        assert not overlap, (
            f"fixture 가 실물을 안 닮았다 — {gid} 와 완료 항목이 어휘 {sorted(overlap)} 를 "
            f"공유한다. 겹치면 어휘 판정으로도 통과해 버려 선언 경로를 증명하지 못한다"
        )
    return len(GOALS), len(DONE_ITEMS)
