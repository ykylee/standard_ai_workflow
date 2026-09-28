"""세션 시작 컨텍스트 예산 — 정본 (ADR-029, `core/session_context_budget_spec.md`).

세션을 열 때 읽는 문서의 **섹션별 바이트 상한**과, 넘쳤을 때의 **출구**를 한 곳에 둔다.
문서·검사·도구는 값을 다시 적지 않고 여기서 import 한다 — 사본은 갈라진다.

왜 바이트이고 왜 출구인가 (concept `docs/planning/session-context-budget-review-2026-09.md`):

- 필독 문서가 195KB 였고 절반 이상이 handoff §5 와 `state.json.memory_entries` 였다.
  둘 다 **줄어드는 경로가 없었다**. 줄 수 상한만 있던 §1 은 한 줄이 18KB 까지 컸다.
- 8/08 에 손으로 99KB → 6KB 로 줄인 handoff 는 7주 만에 82KB 로 돌아왔다 — 예산이 없었다.
  반대로 출구 없이 예산만 걸면 같은 손 압축이 반복된다. 그래서 예산마다 **출구 명령**이
  붙고, 초과 메시지는 그 명령을 그대로 싣는다.

개수 상한(`RECENT_DONE_ITEMS_CAP` · `BASELINE_ITEMS_CAP`)은 `common.project_docs` 에 있다.
두 부류는 서로를 대체하지 않는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from workflow_kit.common.project_docs import BASELINE_LABELS

Severity = Literal["red", "warn"]


@dataclass(frozen=True)
class Budget:
    """예산 한 건 — 무엇을, 얼마까지, 넘치면 얼마나 세게, 어디로 빼는가."""

    key: str
    target: str
    limit_bytes: int
    severity: Severity
    exit: str


#: 예산 정본 (requirements sign-off Q2, 2026-09-28 — 구현 후 실측으로 한 번 재조정한다).
BUDGETS: tuple[Budget, ...] = (
    Budget(
        key="handoff_s5_accumulated",
        target="session_handoff.md §5 누적형 절의 합",
        limit_bytes=8 * 1024,
        severity="red",
        exit="wk rollover-handoff-notes --apply",
    ),
    Budget(
        key="handoff_baseline_line",
        target="session_handoff.md §1 기준선 줄 하나",
        limit_bytes=3 * 1024,
        severity="warn",
        exit="상세를 task 파일·세션 기록으로 옮기고 기준선 줄을 요약한다 (판단 — 자동 이관 없음)",
    ),
    Budget(
        key="state_json",
        target="브랜치 state.json 전체",
        limit_bytes=30 * 1024,
        severity="red",
        exit="생성기 입력을 줄인다 — handoff §1 기준선 줄 · memory_index entry 수 (state.json 은 손으로 고치지 않는다)",
    ),
    Budget(
        key="claude_md",
        target="저장소 루트 CLAUDE.md",
        limit_bytes=12 * 1024,
        severity="red",
        exit="운영 산문을 docs/LOCAL_GATE.md 로 옮기고 CLAUDE.md 에는 명령·규칙·링크만 남긴다",
    ),
)

BUDGETS_BY_KEY: dict[str, Budget] = {b.key: b for b in BUDGETS}

#: handoff §5 의 **현재형** 절 — 이름 접두로 선언한다 (ADR-029 결정 2). 목록 밖의 `###` 절은
#: 누적형이라 예산을 넘으면 `wk rollover-handoff-notes` 가 옮긴다. 새 절을 현재형으로 두려면
#: 여기에 올린다 — 휴리스틱으로 고르면 현재형을 옮기는 오판이 난다.
HANDOFF_S5_CURRENT_SECTIONS: tuple[str, ...] = (
    "▶ 지금 할 일",
    "작업 후보",
    "소유자 결정 대기",
    "환경 상태",
    "관찰 축",
)


@dataclass(frozen=True)
class S5Block:
    """handoff §5 의 `###` 절 하나 (그 아래 `####` 포함)."""

    title: str
    text: str
    current: bool

    @property
    def size(self) -> int:
        return len(self.text.encode("utf-8"))


def _section(text: str, number: int) -> str:
    """`## <number>.` 절 본문 (제목 줄 포함). 없으면 빈 문자열."""
    m = re.search(rf"(?m)^## {number}\.", text)
    if not m:
        return ""
    nxt = re.search(r"(?m)^## ", text[m.end():])
    return text[m.start(): m.end() + nxt.start()] if nxt else text[m.start():]


def is_current_section(title: str) -> bool:
    """`###` 절 제목(`### ` 뒤)이 현재형 목록의 접두로 시작하는가."""
    return title.strip().startswith(HANDOFF_S5_CURRENT_SECTIONS)


def split_s5_blocks(handoff_text: str) -> list[S5Block]:
    """§5 를 `###` 절 단위로 나눈다. `###` 앞의 서두는 현재형으로 친다."""
    s5 = _section(handoff_text, 5)
    if not s5:
        return []
    parts = re.split(r"(?m)^(?=### )", s5)
    blocks: list[S5Block] = []
    head = parts[0]
    if head.strip():
        blocks.append(S5Block(title="(서두)", text=head, current=True))
    for part in parts[1:]:
        title = part.splitlines()[0][4:]
        blocks.append(S5Block(title=title, text=part, current=is_current_section(title)))
    return blocks


def baseline_lines(handoff_text: str) -> list[str]:
    """§1 의 기준선 줄 (`- 현재 기준선:` · `- 직전 기준선:` · `- 그 이전 기준선:`)."""
    s1 = _section(handoff_text, 1)
    prefixes = tuple(f"- {label}:" for label in BASELINE_LABELS)
    return [line for line in s1.splitlines() if line.startswith(prefixes)]


@dataclass(frozen=True)
class Measurement:
    """예산 하나의 측정 결과. `measured=False` 면 `size` 는 판단 근거가 아니다."""

    budget: Budget
    measured: bool
    size: int
    detail: str = ""

    @property
    def over(self) -> bool:
        return self.measured and self.size > self.budget.limit_bytes

    def message(self) -> str:
        b = self.budget
        return (
            f"컨텍스트 예산 초과 [{b.severity}] {b.key}: {b.target} {self.size:,}B > {b.limit_bytes:,}B"
            f"{' (' + self.detail + ')' if self.detail else ''} — 출구: {b.exit}"
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.budget.key,
            "measured": self.measured,
            "size": self.size,
            "limit": self.budget.limit_bytes,
            "severity": self.budget.severity,
            "over": self.over,
            "exit": self.budget.exit,
            "detail": self.detail,
        }


def _file_size(path: Path | None) -> tuple[bool, int]:
    if path is None or not path.is_file():
        return False, 0
    return True, path.stat().st_size


def measure(
    *,
    handoff_path: Path | None,
    state_path: Path | None,
    claude_md_path: Path | None,
) -> list[Measurement]:
    """`BUDGETS` 전부를 잰다. 파일이 없으면 그 예산은 `measured=False` (모름 ≠ 통과)."""
    handoff_text = ""
    if handoff_path is not None and handoff_path.is_file():
        handoff_text = handoff_path.read_text(encoding="utf-8")
    out: list[Measurement] = []
    for b in BUDGETS:
        if b.key == "handoff_s5_accumulated":
            if not handoff_text:
                out.append(Measurement(b, False, 0, "handoff 없음"))
                continue
            acc = [blk for blk in split_s5_blocks(handoff_text) if not blk.current]
            out.append(Measurement(b, True, sum(blk.size for blk in acc), f"누적형 {len(acc)}절"))
        elif b.key == "handoff_baseline_line":
            if not handoff_text:
                out.append(Measurement(b, False, 0, "handoff 없음"))
                continue
            sizes = [len(line.encode("utf-8")) for line in baseline_lines(handoff_text)]
            worst = max(sizes, default=0)
            n_over = sum(1 for s in sizes if s > b.limit_bytes)
            out.append(Measurement(b, bool(sizes), worst, f"가장 긴 줄 · {n_over}/{len(sizes)}줄 초과"))
        elif b.key == "state_json":
            ok, size = _file_size(state_path)
            out.append(Measurement(b, ok, size, "" if ok else "state.json 없음"))
        elif b.key == "claude_md":
            ok, size = _file_size(claude_md_path)
            out.append(Measurement(b, ok, size, "" if ok else "CLAUDE.md 없음"))
        else:  # pragma: no cover — 새 예산을 추가하고 측정을 빠뜨린 경우
            raise ValueError(f"측정이 정의되지 않은 예산: {b.key}")
    return out
