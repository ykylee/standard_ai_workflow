"""기존 진입점 다이어트 — 과거 kit 가 생성한 그대로인 절만 현행 템플릿으로 바꾸거나 걷는다.

TASK-2026-10-06-main-004 (진입점 다이어트 3). 신규 bootstrap 템플릿은 다이어트됐지만(main-003),
이미 채택한 프로젝트의 진입점(CLAUDE.md · AGENTS.md · GROK.md …)은 옛 템플릿의 상용구와 옛 규칙
블록을 그대로 들고 있다. 진입점은 세션마다 통째로 실리므로 그 분량이 매 세션 비용이다.

**판정은 절(`## `) 단위다.** 파일 전체를 "손댔나" 로 판정하면 한 줄만 고친 파일도 통째로 못 고친다.

- 절의 (제목, 정규화 본문)이 과거 kit 버전 중 어느 하나가 **생성한 그대로**면 kit 소유 절이다
  (:data:`KNOWN_GENERATED` — 발행 태그별 bootstrap 출력에서 채취한 해시).
  - 현행 템플릿에 같은 제목의 절이 있으면 **교체** (`replace`).
  - 없으면 **제거** (`remove`) — 현행 템플릿이 걷은 상용구다.
- 본문이 다르면 사용자가 고친 절이거나 프로젝트 값이 든 절이다 → **그대로** (`keep`). 걷힌 제목인데
  본문이 다르면 `edited` 로 보고해 사람이 판단하게 한다.
- 포크를 선언한 파일은 계산만 하고 쓰지 않는다 (호출자 몫, `ensure-entrypoints --diet`).

정규화는 공백 묶음을 한 칸으로 줄이는 것뿐이다 — 줄바꿈 위치만 다른 옛 변형(렌더러마다 줄 폭이
달랐다)을 같은 문안으로 본다. 그 밖의 차이는 전부 "다르다" 다.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field

from workflow_kit.common._entry_known_sections import KNOWN_GENERATED

#: 한국어 시절(2026-08-14 이전) 제목 → 현행 제목. 현행 템플릿에서 교체 대상을 찾을 때 쓴다.
HEADING_ALIASES: Mapping[str, str] = {
    "항상 먼저 읽을 문서": "Read these first",
    "진입 slash command (additive)": "Entry slash commands (additive)",
    "언어와 컨텍스트 원칙": "Language and context principles",
    "작업 원칙": "Working Principles",
    "세션 종료 순서": "Session Close Order",
    "메모리 갱신 경로": "Memory Update Paths",
    "프로젝트 실행 기본값": "Project run defaults",
    "문서 관례": "Documentation conventions",
}


def normalize(body: str) -> str:
    return " ".join(body.split())


def body_hash(body: str) -> str:
    return hashlib.sha256(normalize(body).encode("utf-8")).hexdigest()[:16]


def split_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    """(첫 `## ` 앞의 머리, [(제목, 본문)]) — 본문은 제목 줄 다음부터 다음 `## ` 앞까지."""
    lines = text.split("\n")
    head: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    for line in lines:
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif sections:
            sections[-1][1].append(line)
        else:
            head.append(line)
    return "\n".join(head), [(title, "\n".join(body)) for title, body in sections]


def is_known_generated(title: str, body: str) -> bool:
    return body_hash(body) in KNOWN_GENERATED.get(title, frozenset())


@dataclass
class SectionAction:
    title: str
    action: str  # replace | remove | keep | edited
    bytes_before: int
    bytes_after: int


@dataclass
class DietPlan:
    bytes_before: int
    bytes_after: int
    budget: int
    actions: list[SectionAction] = field(default_factory=list)
    new_text: str = ""

    @property
    def changed(self) -> bool:
        return self.bytes_before != self.bytes_after or any(a.action in ("replace", "remove") for a in self.actions)

    def counts(self) -> dict[str, int]:
        out = {"replace": 0, "remove": 0, "keep": 0, "edited": 0}
        for a in self.actions:
            out[a.action] += 1
        return out


def plan_diet(text: str, current_template: str, budget: int) -> DietPlan:
    """``text`` (기존 진입점)를 ``current_template`` (같은 파일의 현행 생성물) 기준으로 줄이는 계획."""
    head, sections = split_sections(text)
    _, current_sections = split_sections(current_template)
    current = {title: body for title, body in current_sections}
    # 걷힌 제목 = 과거 생성물에 있었고 현행 템플릿에 (별칭으로도) 대응 절이 없는 제목.
    retired_titles = {t for t in KNOWN_GENERATED if HEADING_ALIASES.get(t, t) not in current}
    out_parts = [head]
    actions: list[SectionAction] = []
    for title, body in sections:
        block = f"## {title}\n{body}"
        canonical = HEADING_ALIASES.get(title, title)
        if is_known_generated(title, body):
            if canonical == title and canonical in current and normalize(current[canonical]) == normalize(body):
                # 이미 현행과 같다 — 교체할 것이 없다 (교체로 세면 보고가 부풀어 오른다).
                out_parts.append(block)
                actions.append(SectionAction(title, "keep", len(block.encode()), len(block.encode())))
                continue
            if canonical in current:
                new_block = f"## {canonical}\n{current[canonical]}"
                out_parts.append(new_block)
                actions.append(SectionAction(title, "replace", len(block.encode()), len(new_block.encode())))
            else:
                actions.append(SectionAction(title, "remove", len(block.encode()), 0))
            continue
        out_parts.append(block)
        action = "edited" if title in retired_titles else "keep"
        actions.append(SectionAction(title, action, len(block.encode()), len(block.encode())))
    new_text = "\n".join(out_parts)
    return DietPlan(
        bytes_before=len(text.encode()),
        bytes_after=len(new_text.encode()),
        budget=budget,
        actions=actions,
        new_text=new_text,
    )


__all__ = [
    "DietPlan",
    "HEADING_ALIASES",
    "SectionAction",
    "body_hash",
    "is_known_generated",
    "normalize",
    "plan_diet",
    "split_sections",
]
