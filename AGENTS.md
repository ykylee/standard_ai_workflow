# oh-my-codex - Intelligent Multi-Agent Orchestration

- Purpose: Codex 진입점. oh-my-codex(OMX) 운영 계약을 master 로 두고, 이 저장소의 표준 AI 워크플로우 규칙을 additive rule 로 더한다.
- Scope: OMX orchestration contract (본문) + 표준 워크플로우 규칙 블록 (문서 끝)
- Audience: Codex CLI (및 AGENTS.md 를 공유하는 opencode / pi-dev / grok-build), 저장소 관리자
- Status: active
- Updated: 2026-08-18 (워크플로우 규칙 블록 합류 — TASK-2026-08-18-main-001)
- Related docs: `CLAUDE.md` (같은 규칙의 Claude Code 판), `ai-workflow/memory/active/<branch>/state.json`, `docs/PROJECT_PROFILE.md`, `workflow-source/core/workflow_deployment_idempotency.md` §4

You are running with oh-my-codex (OMX), a coordination layer for Codex CLI.
This AGENTS.md is the top-level operating contract for the workspace.
Role prompts under `prompts/*.md` are narrower execution surfaces. They must follow this file, not override it.

> **이 파일은 두 주인을 가진다.** 본문은 OMX 템플릿이고, 문서 끝의
> "Standard AI Workflow" 절은 이 저장소의 워크플로우 규칙이다 (컨셉 §4.2 —
> 공유 진입점은 master 를 참조하고 하네스 고유분만 더한다). **`omx setup` 이
> 이 파일을 재생성하면 그 절이 사라질 수 있다** — 사라지면
> `check_self_application` 이 즉시 red 로 지목하므로, 조용히 없어지지는 않는다.
> 복구는 `python3 -m workflow_kit.common.standard_rules` 가 내는 블록을 다시
> 붙이면 된다 (정본: `workflow-source/core/global_workflow_standard.md`).

<guidance_schema_contract>
Canonical guidance schema for this template is defined in `docs/guidance-schema.md`.

Required schema sections and this template's mapping:
- **Role & Intent**: title + opening paragraphs.
- **Operating Principles**: `<operating_principles>`.
- **Execution Protocol**: delegation/model routing/agent catalog/skills/team pipeline sections.
- **Constraints & Safety**: keyword detection, cancellation, and state-management rules.
- **Verification & Completion**: `<verification>` + continuation checks in `<execution_protocols>`.
- **Recovery & Lifecycle Overlays**: runtime/team overlays are appended by marker-bounded runtime hooks.

Keep runtime marker contracts stable and non-destructive when overlays are applied:
- `<!-- OMX:RUNTIME:START --> ... <!-- OMX:RUNTIME:END -->`
- `<!-- OMX:TEAM:WORKER:START --> ... <!-- OMX:TEAM:WORKER:END -->`
</guidance_schema_contract>

<operating_principles>
- Solve the task directly when you can do so safely and well.
- Delegate only when it materially improves quality, speed, or correctness.
- Keep progress short, concrete, and useful.
- Prefer evidence over assumption; verify before claiming completion.
- Use the lightest path that preserves quality: direct action, MCP, then delegation.
- Check official documentation before implementing with unfamiliar SDKs, frameworks, or APIs.
<!-- OMX:GUIDANCE:OPERATING:START -->
- Default to compact, information-dense responses; expand only when risk, ambiguity, or the user explicitly calls for detail.
- Proceed automatically on clear, low-risk, reversible next steps; ask only for irreversible, side-effectful, or materially branching actions.
- Treat newer user task updates as local overrides for the active task while preserving earlier non-conflicting instructions.
- Persist with tool use when correctness depends on retrieval, inspection, execution, or verification; do not skip prerequisites just because the likely answer seems obvious.
<!-- OMX:GUIDANCE:OPERATING:END -->
</operating_principles>

## Working agreements
- Write a cleanup plan before modifying code for cleanup/refactor/deslop work.
- Lock existing behavior with regression tests before cleanup edits when behavior is not already protected.
- Prefer deletion over addition.
- Reuse existing utils and patterns before introducing new abstractions.
- No new dependencies without explicit request.
- Keep diffs small, reviewable, and reversible.
- Run lint, typecheck, tests, and static analysis after changes.
- Final reports must include changed files, simplifications made, and remaining risks.

---

<delegation_rules>
Default posture: work directly. Delegate only when the task is multi-file, specialist-heavy, highly parallel, or materially safer with a dedicated role.

Use delegation for:
- deep analysis, broad planning, focused review, specialist research, or large parallel work
- non-trivial SDK/API/framework usage that benefits from `dependency-expert`
- substantive implementation work that clearly benefits from `executor`

Do not delegate trivial work or use delegation as a substitute for reading the code.
For substantive code changes, `executor` is the default implementation role.
Outside active `team`/`swarm` mode, use `executor` (or another standard role prompt) for implementation work; do not invoke `worker` or spawn Worker-labeled helpers in non-team mode.
Reserve `worker` strictly for active `team`/`swarm` sessions and team-runtime bootstrap flows.
</delegation_rules>

<child_agent_protocol>
When delegating:
1. Choose the right role.
2. Read `./.codex/prompts/{role}.md` first.
3. Spawn the child with that prompt plus the concrete task.
4. Keep the task bounded and verifiable.

Rules:
- Max 6 concurrent child agents.
- Child prompts stay under AGENTS.md authority.
- `worker` is a team-runtime surface, not a general-purpose child role.
- Child agents should report recommended handoffs upward.
- Child agents should finish their assigned role, not recursively orchestrate unless explicitly told to do so.
</child_agent_protocol>

<invocation_conventions>
- `/prompts:name` — invoke a role prompt
- `$name` — invoke a workflow skill
- `/skills` — browse available skills
</invocation_conventions>

<model_routing>
Match role to task shape:
- Low complexity: `explore`, `style-reviewer`, `writer`
- Standard: `executor`, `debugger`, `test-engineer`
- High complexity: `architect`, `executor`, `critic`
</model_routing>

---

<agent_catalog>
Key roles:
- `explore` — fast codebase search and mapping
- `planner` — work plans and sequencing
- `architect` — read-only analysis, diagnosis, tradeoffs
- `debugger` — root-cause analysis
- `executor` — implementation and refactoring
- `verifier` — completion evidence and validation

Specialists remain available through `/prompts:*` when the task clearly benefits from them.
</agent_catalog>

---

<keyword_detection>
When the user message contains a mapped keyword, activate the corresponding skill immediately.
Do not ask for confirmation.

Supported workflow triggers include: `ralph`, `autopilot`, `ultrawork`, `ultraqa`, `cleanup`/`refactor`/`deslop`, `analyze`, `plan this`, `deep interview`, `ouroboros`, `ralplan`, `team`/`swarm`, `ecomode`, `cancel`, `tdd`, `fix build`, `code review`, `security review`, and `web-clone`.
The `deep-interview` skill is the Socratic deep interview workflow and includes the ouroboros trigger family.

| Keyword(s) | Skill | Action |
|-------------|-------|--------|
| "ralph", "don't stop", "must complete", "keep going" | `$ralph` | Read `./.agents/skills/ralph/SKILL.md`, execute persistence loop |
| "autopilot", "build me", "I want a" | `$autopilot` | Read `./.agents/skills/autopilot/SKILL.md`, execute autonomous pipeline |
| "ultrawork", "ulw", "parallel" | `$ultrawork` | Read `./.agents/skills/ultrawork/SKILL.md`, execute parallel agents |
| "ultraqa" | `$ultraqa` | Read `./.agents/skills/ultraqa/SKILL.md`, run QA cycling workflow |
| "analyze", "investigate" | `$analyze` | Read `./.agents/skills/analyze/SKILL.md`, run deep analysis |
| "plan this", "plan the", "let's plan" | `$plan` | Read `./.agents/skills/plan/SKILL.md`, start planning workflow |
| "interview", "deep interview", "gather requirements", "interview me", "don't assume", "ouroboros" | `$deep-interview` | Read `./.agents/skills/deep-interview/SKILL.md`, run Ouroboros-inspired Socratic ambiguity-gated interview workflow |
| "ralplan", "consensus plan" | `$ralplan` | Read `./.agents/skills/ralplan/SKILL.md`, start consensus planning with RALPLAN-DR structured deliberation (short by default, `--deliberate` for high-risk) |
| "team", "swarm", "coordinated team", "coordinated swarm" | `$team` | Read `./.agents/skills/team/SKILL.md`, start team orchestration (swarm compatibility alias) |
| "ecomode", "eco", "budget" | `$ecomode` | Read `./.agents/skills/ecomode/SKILL.md`, enable token-efficient mode |
| "cancel", "stop", "abort" | `$cancel` | Read `./.agents/skills/cancel/SKILL.md`, cancel active modes |
| "tdd", "test first" | `$tdd` | Read `./.agents/skills/tdd/SKILL.md`, start test-driven workflow |
| "fix build", "type errors" | `$build-fix` | Read `./.agents/skills/build-fix/SKILL.md`, fix build errors |
| "review code", "code review", "code-review" | `$code-review` | Read `./.agents/skills/code-review/SKILL.md`, run code review |
| "security review" | `$security-review` | Read `./.agents/skills/security-review/SKILL.md`, run security audit |
| "web-clone", "clone site", "clone website", "copy webpage" | `$web-clone` | Read `./.agents/skills/web-clone/SKILL.md`, start website cloning pipeline |

Detection rules:
- Keywords are case-insensitive and match anywhere in the user message.
- Explicit `$name` invocations run left-to-right and override non-explicit keyword resolution.
- If multiple non-explicit keywords match, use the most specific match.
- If the user explicitly invokes `/prompts:<name>`, do not auto-activate keyword skills unless explicit `$name` tokens are also present.
- The rest of the user message becomes the task description.

Ralph / Ralplan execution gate:
- Enforce **ralplan-first** when ralph is active and planning is not complete.
- Planning is complete only after both `.omx/plans/prd-*.md` and `.omx/plans/test-spec-*.md` exist.
- Until complete, do not begin implementation or execute implementation-focused tools.
</keyword_detection>

---

<skills>
Skills are workflow commands.
Core workflows include `autopilot`, `ralph`, `ultrawork`, `visual-verdict`, `web-clone`, `ecomode`, `team`, `swarm`, `ultraqa`, `plan`, `deep-interview` (Socratic deep interview, Ouroboros-inspired), and `ralplan`.
Utilities include `cancel`, `note`, `doctor`, `help`, and `trace`.
</skills>

---

<team_compositions>
Common team compositions remain available when explicit team orchestration is warranted, for example feature development, bug investigation, code review, and UX audit.
</team_compositions>

---

<team_pipeline>
Team mode is the structured multi-agent surface.
Canonical pipeline:
`team-plan -> team-prd -> team-exec -> team-verify -> team-fix (loop)`

Use it when durable staged coordination is worth the overhead. Otherwise, stay direct.
Terminal states: `complete`, `failed`, `cancelled`.
</team_pipeline>

---

<team_model_resolution>
Team/Swarm workers currently share one `agentType` and one launch-arg set.
Model precedence:
1. Explicit model in `OMX_TEAM_WORKER_LAUNCH_ARGS`
2. Inherited leader `--model`
3. Low-complexity default model from `OMX_SPARK_MODEL` (currently `gpt-5.3-codex-spark`)

Normalize model flags to one canonical `--model <value>` entry.
</team_model_resolution>

---

<verification>
Verify before claiming completion.

Sizing guidance:
- Small changes: lightweight verification
- Standard changes: standard verification
- Large or security/architectural changes: thorough verification

<!-- OMX:GUIDANCE:VERIFYSEQ:START -->
Verification loop: identify what proves the claim, run the verification, read the output, then report with evidence. If verification fails, continue iterating rather than reporting incomplete work. Default to concise evidence summaries in the final response, but never omit the proof needed to justify completion.

- Run dependent tasks sequentially; verify prerequisites before starting downstream actions.
- If a task update changes only the current branch of work, apply it locally and continue without reinterpreting unrelated standing instructions.
- When correctness depends on retrieval, diagnostics, tests, or other tools, continue using them until the task is grounded and verified.
<!-- OMX:GUIDANCE:VERIFYSEQ:END -->
</verification>

<execution_protocols>
Broad Request Detection:
A request is broad when it uses vague verbs without targets, names no specific file or function, touches 3+ areas, or is a single sentence without a clear deliverable. For broad work: explore first, then plan if needed.

Parallelization:
- Run independent tasks in parallel.
- Run dependent tasks sequentially.
- Use background execution for builds and tests when helpful.
- Prefer Team mode only when its coordination value outweighs its overhead.
- If correctness depends on retrieval, diagnostics, tests, or other tools, continue using them until the task is grounded and verified.

Anti-slop workflow:
- Cleanup/refactor/deslop requests route through `$ai-slop-cleaner` unless the user explicitly requests otherwise.
- Lock behavior with tests first, then make one smell-focused pass at a time.
- Prefer deletion, reuse, and boundary repair over new layers.
- Keep writer/reviewer pass separation for cleanup plans and approvals.

Visual iteration gate:
- For visual tasks, run `$visual-verdict` every iteration before the next edit.
- Persist verdict JSON in `.omx/state/{scope}/ralph-progress.json`.

Continuation:
Before concluding, confirm: no pending work, features working, tests passing, zero known errors, verification evidence collected. If not, continue.

Ralph planning gate:
If ralph is active, verify PRD + test spec artifacts exist before implementation work.
</execution_protocols>

<cancellation>
Use the `cancel` skill to end execution modes.
Cancel when work is done and verified, when the user says stop, or when a hard blocker prevents meaningful progress.
Do not cancel while recoverable work remains.
</cancellation>

---

<state_management>
OMX persists runtime state under `.omx/`:
- `.omx/state/` — mode state
- `.omx/notepad.md` — session notes
- `.omx/project-memory.json` — cross-session memory
- `.omx/plans/` — plans
- `.omx/logs/` — logs

Available MCP groups include state/memory tools, code-intel tools, and trace tools.

Mode lifecycle requirements:
- Write state on start.
- Update state on phase or iteration change.
- Mark inactive with `completed_at` on completion.
- Clear state on cancel/abort cleanup.
</state_management>

---

## Setup

Run `omx setup` to install all components. Run `omx doctor` to verify installation.

---

# Standard AI Workflow (additive rule)

이 절은 **OMX 계약 아래에서 더해지는 규칙**이다. 충돌하면 위의 OMX 운영 계약이
우선하고, 이 절은 세션 경계(시작·종료)와 상태 문서 취급만 규정한다. 같은 규칙의
Claude Code 판은 `CLAUDE.md` 에 있으며 **둘은 같은 정본에서 파생**된다
(`workflow-source/core/global_workflow_standard.md` §1 · §3 · §8 · §11).

## 항상 먼저 읽을 문서

- `ai-workflow/memory/active/<branch>/state.json` (생성물 — 손으로 고치지 않는다)
- `ai-workflow/memory/active/<branch>/session_handoff.md`
- `ai-workflow/memory/active/<branch>/backlog/`
- `docs/PROJECT_PROFILE.md`

`ai-workflow/` 는 세션 복원용 메타 레이어다. 프로젝트 코드를 탐색할 때는 기본
탐색 범위에 넣지 않는다.

## 실행 기본값

개발 환경은 저장소 `.venv` 다. 명령과 게이트 규칙(편집 중 `--filter` / 커밋 전
관련 검사 / **push 직전 1회만 2축 전량**)은 `CLAUDE.md` 의 "프로젝트 실행
기본값" 절이 정본이다 — 여기 복제하지 않는다.

## Working Principles

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 · §11 — do not edit this block directly; edit the standard document and regenerate. -->

- Start every session by reading the current state summary documents first.
- Before starting work, briefly state its purpose, scope, expected deliverables, and affected documents.
- Record work in the state documents; track progress as exactly one of `planned`, `in_progress`, `blocked`, `done`.
- Never mark an unverified result as done.
- Before ending a session, summarize the current state so the next session can pick it up directly.
- Multiple agents may work together: sync with the remote before starting, check what other agents are doing, and pick work that does not overlap.
- Never decide irreversible actions alone — deleting or overwriting another agent's work requires confirmation from the user.
- Keep the shared standard thin; put project-specific differences in the project profile.

## Session Close Order

Close a session in the order **update memory → commit → push**. Do not split the memory update into a separate turn after the commit, so that pushed commits always carry the memory update with them (collaboration consistency).

- Update before closing: `state.json`, `session_handoff.md`, the latest backlog

## Memory Update Paths

- Restore session-start baseline: `wk session-start`
- Register / update a task: `wk backlog-update`
- Sync affected documents (advisory): `wk doc-sync`
- Regenerate state.json at session close: `wk refresh-state`
- Roll off handoff §1 baselines when over cap: `wk rollover-baselines`
- Propose memory_index promotion candidates at close (advisory, no write): `wk suggest-memory-entries`

- When the handoff's `in_progress` / `blocked` lists are empty, leave an **empty bullet `-`**. Prose there is parsed as a work item.
- Entries in the handoff's recently-completed list start with `TASK-` and never exceed 10.
- A backlog task's `status` is one of `planned` / `in_progress` / `blocked` / `done`.
- `state.json` is a **generated artifact** — never hand-edit it. The SSOT is `backlog/tasks/` plus `session_handoff.md`; regenerate with `wk refresh-state` at session close.
- Handoff §1 baseline lines have a cap. When it is exceeded, **move** the excess with `wk rollover-baselines` — never delete them by hand. That prose exists nowhere else, unlike the recently-done list whose SSOT is `backlog/tasks/`.
- `session_handoff.md` and the backlog are **inputs to the state.json generator** — writing outside the format silently corrupts state.json.
