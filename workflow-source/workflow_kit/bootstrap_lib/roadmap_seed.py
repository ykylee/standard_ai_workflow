"""ADR-027 M-005 — bootstrap 이 심는 SDLC 로드맵 씨앗.

온보딩 기본 흐름(스펙 §4): 신규 프로젝트는 **컨셉 정리부터** 시작한다 —
concept → requirements → design → implementation 4 마일스톤을 심고
M-001(concept)을 `in_progress` 로 연다.

기존 프로젝트(adoption-mode existing)는 **추정을 확정으로 적지 않는다** —
전 마일스톤 planned + "현재 단계는 소유자가 선언한다" draft 표기다. 어느
단계를 in_progress 로 지어내면 그 거짓이 게이트 판정(§6)까지 흘러간다.

씨앗의 형식 정본은 `workflow_kit.common.state.roadmap` 파서다 — 씨앗이 자기
파서를 통과하는지는 `check_roadmap_bootstrap_seed` 가 고정한다 (56차 규칙:
심는 것이 읽히는지 확인하지 않으면 소비자는 첫날부터 파싱 안 되는 상태를
받는다).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from workflow_kit.common.schemas.roadmap import RoadmapItemStatus, SdlcPhase


@dataclass(frozen=True)
class _SeedMilestone:
    number: int
    slug: str
    title: str
    phase: SdlcPhase
    body: str
    wbs_lines: tuple[str, ...]
    deliverables: tuple[str, ...]

    @property
    def id(self) -> str:
        return f"M-{self.number:03d}"

    @property
    def filename(self) -> str:
        return f"{self.id}-{self.slug}.md"


def _seed_milestones(kit_dir: str) -> tuple[_SeedMilestone, ...]:
    """SDLC 기본 4 마일스톤. deliverables 는 §4 표의 기본 산출물 경로다.

    implementation 의 deliverables 는 비워 둔다 — 동작 산출물은 프로젝트마다
    다르고, 모르는 정체를 지어내면 그 거짓이 done 판정에 실린다.
    """
    purpose_rel = f"{kit_dir.rstrip('/')}/memory/active/PURPOSE.md"
    return (
        _SeedMilestone(
            number=1, slug="concept", title="컨셉 정리", phase=SdlcPhase.CONCEPT,
            body=(
                "프로젝트가 *왜* 존재하고 어디로 가는지부터 정리한다 — PURPOSE.md 의\n"
                "4-element (Goals / Key Questions / Research Scope / Evolving Thesis)를\n"
                "placeholder 없이 채우는 것이 이 마일스톤의 완료다."
            ),
            wbs_lines=(
                "- **WBS-1.1** PURPOSE.md 4-element 채움 — 산출물: placeholder 소거",
                "- **WBS-1.2** 컨셉 노트 — 핵심 개념·용어·경계",
            ),
            deliverables=(purpose_rel,),
        ),
        _SeedMilestone(
            number=2, slug="requirements", title="요구사항 정리", phase=SdlcPhase.REQUIREMENTS,
            body="컨셉에서 요구를 끌어낸다 — 기능/비기능을 나누고 우선순위를 매긴다.",
            wbs_lines=(
                "- **WBS-2.1** 요구사항 문서 작성 — 산출물: docs/REQUIREMENTS.md",
            ),
            deliverables=("docs/REQUIREMENTS.md",),
        ),
        _SeedMilestone(
            number=3, slug="design", title="설계", phase=SdlcPhase.DESIGN,
            body="요구를 구조로 옮긴다 — 설계 문서 또는 ADR 로 결정을 기록한다.",
            wbs_lines=(
                "- **WBS-3.1** 설계 문서 / ADR 작성 — 산출물: docs/architecture/",
            ),
            deliverables=("docs/architecture",),
        ),
        _SeedMilestone(
            number=4, slug="implementation", title="구현", phase=SdlcPhase.IMPLEMENTATION,
            body=(
                "설계를 동작으로 옮긴다. WBS 는 설계가 끝나면 프로젝트가 스스로\n"
                "분해한다 — 씨앗이 미리 지어내지 않는다."
            ),
            wbs_lines=(
                "- **WBS-4.1** 구현 (설계 확정 후 leaf 로 분해한다)",
            ),
            deliverables=(),
        ),
    )


def _milestone_status(m: _SeedMilestone, *, draft: bool) -> RoadmapItemStatus:
    if not draft and m.number == 1:
        return RoadmapItemStatus.IN_PROGRESS
    return RoadmapItemStatus.PLANNED


def render_roadmap_seed(args: argparse.Namespace, *, draft: bool) -> dict[str, str]:
    """{상대경로(roadmap/ 기준): 내용} 을 반환한다.

    ``draft=False`` (신규): M-001 concept 가 in_progress — 컨셉부터가 기본이다.
    ``draft=True`` (기존): 전부 planned + 소유자 선언 대기 표기.
    """
    kit_dir = str(getattr(args, "kit_dir", "ai-workflow"))
    project_name = str(getattr(args, "project_name", "") or "project")
    today = str(getattr(args, "today", ""))
    milestones = _seed_milestones(kit_dir)

    index_lines = [
        f"# Roadmap — {project_name}",
        "",
        "- 문서 목적: 로드맵 층의 SSOT index — 마일스톤 목록과 SDLC 순서를 선언한다 (ADR-027).",
        "- 범위: 마일스톤 선언 · SDLC 순서 · WBS (각 마일스톤 파일)",
        "- 대상 독자: AI agent (session-start / backlog-update), 저장소 관리자",
        f"- 상태: {'draft — 기존 프로젝트 온보딩 초안' if draft else 'active'}",
        f"- 최종 수정일: {today}",
        "- 관련 문서: [`roadmap_state.json`](./roadmap_state.json)",
        "",
        "> 이 목록의 **순서가 곧 SDLC 순서 선언**이다. status 는 선언이고, 파생",
        "> 진척과의 불일치는 `roadmap_state.json` 의 issues 가 지목한다.",
        "> `roadmap_state.json` 은 생성물이다 — 손으로 고치지 않는다.",
    ]
    if draft:
        index_lines += [
            ">",
            "> **draft** — 기존 프로젝트라 현재 단계를 추정하지 않았다. 추정을",
            "> 확정으로 적으면 그 거짓이 게이트 판정까지 흘러간다. **소유자가**",
            "> 현재 단계의 마일스톤을 in_progress 로 선언하는 것이 온보딩의 다음",
            "> 한 수다 (repository_assessment.md 가 있으면 판단 재료로 쓴다).",
        ]
    index_lines += ["", "## Milestones", ""]
    for m in milestones:
        status = _milestone_status(m, draft=draft)
        index_lines.append(f"- **{m.id}** [{m.phase.value}] {m.title} — status: {status.value}")
        index_lines.append(f"  - path: [`./{m.filename}`](./{m.filename})")
    files: dict[str, str] = {"index.md": "\n".join(index_lines) + "\n"}

    for m in milestones:
        status = _milestone_status(m, draft=draft)
        deliverable_lines = (
            ["deliverables:"] + [f"  - {d}" for d in m.deliverables]
            if m.deliverables else ["deliverables: []"]
        )
        files[m.filename] = "\n".join([
            "---",
            f"id: {m.id}",
            f"title: {m.title}",
            f"sdlc_phase: {m.phase.value}",
            f"status: {status.value}",
            f"order: {m.number}",
            "parallel_allowed: []",
            *deliverable_lines,
            "---",
            "",
            f"# {m.id} — {m.title}",
            "",
            m.body,
            "",
            "## WBS",
            "",
            *m.wbs_lines,
        ]) + "\n"
    return files
