"""정본 규칙의 **생성된 스냅샷** — 직접 고치지 않는다.

생성: ``python3 -m workflow_kit.common.standard_rules --apply``
정본: ``core/global_workflow_standard.md`` §1 · §3 · §8 · §11
검증: ``tests/check_standard_single_source.py``

wheel 설치처럼 ``core/`` 가 함께 배포되지 않는 환경에서 진입점 렌더링이 규칙을
잃지 않도록 두는 사본이다. 정본과의 일치는 검사로 강제된다.
"""

from __future__ import annotations


PRINCIPLES: tuple[str, ...] = (
    'Read the state summary documents first, every session.',
    'Before starting work, state its purpose, scope, deliverables, and affected documents, and record the plan in the task file (files, order of work, risks, proof).',
    'Track work in the state documents with exactly one status: `planned`, `in_progress`, `blocked`, `done`.',
    'Never mark an unverified result as done.',
    'Before ending a session, leave a state summary the next session can resume from.',
    'With multiple agents: sync with the remote first, check what the others are doing, and pick work that does not overlap.',
    "Never decide irreversible actions alone — deleting or overwriting another agent's work needs the user's confirmation.",
    'Keep the shared standard thin; project-specific differences go in the project profile.',
)

TASK_STATES: tuple[str, ...] = (
    'planned',
    'in_progress',
    'blocked',
    'done',
)

CLOSE_ORDER: str = 'Close a session in the order **update memory → commit → push** — the memory update rides in the pushed commit, never in a later turn.'

MEMORY_COMMANDS: tuple[tuple[str, str], ...] = (
    ('Restore session-start baseline', 'python -m workflow_kit session-start'),
    ('Register / update a task', 'python -m workflow_kit backlog-update'),
    ('Sync affected documents (advisory)', 'python -m workflow_kit doc-sync'),
    ('Regenerate state.json at session close', 'python -m workflow_kit refresh-state'),
    ('Roll off handoff §1 baselines over cap', 'python -m workflow_kit rollover-baselines'),
    ('Roll off handoff §5 notes over budget', 'python -m workflow_kit rollover-handoff-notes'),
    ('Propose memory_index entries at close (advisory)', 'python -m workflow_kit suggest-memory-entries'),
    ('Relay working state across compaction', 'python -m workflow_kit compact-checkpoint'),
)

PARSE_CONTRACT: tuple[str, ...] = (
    'Run them with the Python that has `workflow_kit` installed (`python` on Windows, usually `python3` elsewhere) — not a `wk` executable, which Windows antivirus blocks.',
    'Empty handoff `in_progress` / `blocked` lists hold an **empty bullet `-`** — prose there is parsed as a work item.',
    'Handoff recently-completed entries start with `TASK-`, at most 10.',
    '`state.json` is a **generated artifact** — never hand-edit it; regenerate with `refresh-state` (sources: `backlog/tasks/` + `session_handoff.md`).',
    'Over the handoff §1 baseline cap, **move** lines with `rollover-baselines` — never delete them.',
    'Over the handoff §5 notes budget, **move** the oldest with `rollover-handoff-notes` (rules → `lessons.md`, notes → `sessions/`).',
    'Write the handoff and backlog only in their format — they feed the state.json generator.',
)
