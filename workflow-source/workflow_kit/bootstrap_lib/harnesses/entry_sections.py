"""하네스 진입점(CLAUDE.md · AGENTS.md · GROK.md …)이 공유하는 절의 **정본**.

TASK-2026-10-06-main-003 (진입점 다이어트 2). 진입점은 세션마다 통째로 컨텍스트에 실린다.
같은 절("Read these first" · 언어 원칙)이 렌더러 8곳에 손으로 복제돼 있었고, 줄이려면 8곳을
따로 고쳐야 했다 — 그래서 한 곳으로 모으고 같이 줄였다. 2026-10-06 신규 bootstrap 실측:
CLAUDE.md 7,758B · AGENTS.md 7,044B · GROK.md 10,532B (그중 정본 규칙 블록 3.6KB).

하네스 고유 사실(Codex notes · Grok MCP 등록 · subagent 구성 등)은 각 렌더러에 남는다.
생성 진입점의 분량 상한은 :data:`ENTRY_BUDGET_BYTES` 이고 `check_entry_budget` 이 전 하네스를 잰다.
"""

from __future__ import annotations

from collections.abc import Sequence

#: 신규 bootstrap 이 생성하는 하네스 진입점 한 파일의 분량 상한 (바이트).
#:
#: 근거: AI-native SDLC 플레이북은 CLAUDE.md 를 "under a page" 로 두라고 한다 — 세션 시작에
#: 전부 읽히므로 낡거나 겹친 줄은 컨텍스트만 차지한다. 정본 규칙 블록(약 2.7KB)이 모든 진입점에
#: 들어가고, 하네스 고유 절이 가장 큰 GROK.md 가 다이어트 후 상한 안에 들어오는 값이다.
#: 올리려면 왜 그 하네스에 그만큼이 필요한지를 여기에 적는다.
ENTRY_BUDGET_BYTES = 8 * 1024

#: "Read these first" 의 정본 문안. 경로 목록을 나열하는 대신 그것을 읽는 명령을 가리킨다 —
#: 목록은 session-start 가 아는 것이고, 진입점에 사본을 두면 갈라진다.
READ_FIRST_LINES: tuple[str, ...] = (
    "- Restore the session with `python -m workflow_kit session-start` — it reads "
    "`ai-workflow/memory/active/<branch>/` (`state.json`, handoff, backlog), "
    "`docs/PROJECT_PROFILE.md`, and `PURPOSE.md` (`<branch>` = current git branch).",
    "- `ai-workflow/` is the workflow meta layer — keep it out of code and document searches; "
    "open it only to restore or update workflow state.",
)

_LANGUAGE_LINES: tuple[str, ...] = (
    "- Write user-facing reports, summaries, and document updates in Korean; keep code, commands, "
    "paths, and product names verbatim.",
    "- Give the user the conclusion and the next action — skip long intermediate reasoning and "
    "repeated summaries.",
    "- Keep only the facts the next session needs in the handoff and backlog.",
)


def read_first_section(extra: Sequence[str] = ()) -> str:
    """`## Read these first` 절. ``extra`` 는 하네스 고유 bullet (``- `` 없이 본문만)."""
    lines = ["## Read these first", "", *READ_FIRST_LINES, *(f"- {item}" for item in extra)]
    return "\n".join(lines)


def language_section() -> str:
    """`## Language and context principles` 절."""
    return "\n".join(["## Language and context principles", "", *_LANGUAGE_LINES])


__all__ = ["ENTRY_BUDGET_BYTES", "READ_FIRST_LINES", "language_section", "read_first_section"]
