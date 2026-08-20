"""정본 규칙의 **생성된 스냅샷** — 직접 고치지 않는다.

생성: ``python3 -m workflow_kit.common.standard_rules --apply``
정본: ``core/global_workflow_standard.md`` §1 · §3 · §8 · §11
검증: ``tests/check_standard_single_source.py``

wheel 설치처럼 ``core/`` 가 함께 배포되지 않는 환경에서 진입점 렌더링이 규칙을
잃지 않도록 두는 사본이다. 정본과의 일치는 검사로 강제된다.
"""

from __future__ import annotations


PRINCIPLES: tuple[str, ...] = (
    'Start every session by reading the current state summary documents first.',
    'Before starting work, briefly state its purpose, scope, expected deliverables, and affected documents.',
    'Record work in the state documents; track progress as exactly one of `planned`, `in_progress`, `blocked`, `done`.',
    'Never mark an unverified result as done.',
    'Before ending a session, summarize the current state so the next session can pick it up directly.',
    'Multiple agents may work together: sync with the remote before starting, check what other agents are doing, and pick work that does not overlap.',
    "Never decide irreversible actions alone — deleting or overwriting another agent's work requires confirmation from the user.",
    'Keep the shared standard thin; put project-specific differences in the project profile.',
)

TASK_STATES: tuple[str, ...] = (
    'planned',
    'in_progress',
    'blocked',
    'done',
)

CLOSE_ORDER: str = 'Close a session in the order **update memory → commit → push**. Do not split the memory update into a separate turn after the commit, so that pushed commits always carry the memory update with them (collaboration consistency).'

MEMORY_COMMANDS: tuple[tuple[str, str], ...] = (
    ('Restore session-start baseline', 'wk session-start'),
    ('Register / update a task', 'wk backlog-update'),
    ('Sync affected documents (advisory)', 'wk doc-sync'),
    ('Regenerate state.json at session close', 'wk refresh-state'),
    ('Roll off handoff §1 baselines when over cap', 'wk rollover-baselines'),
    ('Propose memory_index promotion candidates at close (advisory, no write)', 'wk suggest-memory-entries'),
)

PARSE_CONTRACT: tuple[str, ...] = (
    "When the handoff's `in_progress` / `blocked` lists are empty, leave an **empty bullet `-`**. Prose there is parsed as a work item.",
    "Entries in the handoff's recently-completed list start with `TASK-` and never exceed 10.",
    "A backlog task's `status` is one of `planned` / `in_progress` / `blocked` / `done`.",
    '`state.json` is a **generated artifact** — never hand-edit it. The SSOT is `backlog/tasks/` plus `session_handoff.md`; regenerate with `wk refresh-state` at session close.',
    'Handoff §1 baseline lines have a cap. When it is exceeded, **move** the excess with `wk rollover-baselines` — never delete them by hand. That prose exists nowhere else, unlike the recently-done list whose SSOT is `backlog/tasks/`.',
    '`session_handoff.md` and the backlog are **inputs to the state.json generator** — writing outside the format silently corrupts state.json.',
)
