<!-- standard-ai-workflow-kit: v1.0.0-beta -->
<!-- standard-ai-workflow-kit-fork: 이 저장소가 소유한다 — 재적용하면 placeholder 로 되돌아간다. kit 변경은 생성물과 diff 해 손으로 병합한다 (마지막 병합 v1.9.4, TASK-2026-09-18-main-003) -->
<!-- standard-ai-workflow-kit-overlay: plugin-only — 스킬은 플러그인 채널로만 소비한다 (TASK-2026-08-25-main-010) -->

# CLAUDE.md (Claude Code 진입점)

- 문서 목적: Claude Code 가 이 저장소에서 매 세션 알아야 할 진입 규칙
- 범위: 세션 복원, 작업 원칙, 세션 종료 순서, 실행 · 검증 명령
- 대상 독자: Claude Code, 저장소 관리자
- 상태: beta
- 최종 수정일: 2026-10-06
- 관련 문서: `docs/PROJECT_PROFILE.md`, `docs/LOCAL_GATE.md`, `ai-workflow/memory/active/<branch>/session_handoff.md`

> 아래 `## Working Principles` · `## Session Close Order` · `## Memory Update Paths` 는
> `core/global_workflow_standard.md` 의 생성물이다 — 여기서 고치지 말고 정본을 고친다.

## 세션 시작

- `python -m workflow_kit session-start` (플러그인 스킬 `/standard-ai-workflow:session-start`) 가
  `ai-workflow/memory/active/<branch>/` 의 `state.json` · handoff · backlog, `docs/PROJECT_PROFILE.md`,
  `PURPOSE.md` 를 복원한다. `<branch>` 는 현재 git 브랜치다.
- `ai-workflow/` 는 세션 상태용 메타 레이어다 — 코드 · 문서 탐색 범위에서 빼고, 상태를 갱신할 때만 본다.
- task 를 `done` 으로 닫기 전: `verifier` subagent (`.claude/agents/verifier.md`) — 완료 기준을 새 컨텍스트에서 다시 잰다

## Working Principles

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 · §11 — do not edit this block directly; edit the standard document and regenerate. -->

- Start every session by reading the current state summary documents first.
- Before starting work, briefly state its purpose, scope, expected deliverables, and affected documents — and record the plan in the task file (files that change, order of work, risks, proof) so it outlives the conversation.
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

- Restore session-start baseline: `python -m workflow_kit session-start`
- Register / update a task: `python -m workflow_kit backlog-update`
- Sync affected documents (advisory): `python -m workflow_kit doc-sync`
- Regenerate state.json at session close: `python -m workflow_kit refresh-state`
- Roll off handoff §1 baselines when over cap: `python -m workflow_kit rollover-baselines`
- Roll off handoff §5 accumulated notes when over budget: `python -m workflow_kit rollover-handoff-notes`
- Propose memory_index promotion candidates at close (advisory, no write): `python -m workflow_kit suggest-memory-entries`
- Relay working state across a context compaction (skill + hooks): `python -m workflow_kit compact-checkpoint`

- Run these with the Python interpreter that has `workflow_kit` installed — `python` on Windows, usually `python3` on macOS / Linux. Do not call a `wk` executable instead: on Windows it is an unsigned per-install launcher that reputation-based antivirus blocks.
- When the handoff's `in_progress` / `blocked` lists are empty, leave an **empty bullet `-`**. Prose there is parsed as a work item.
- Entries in the handoff's recently-completed list start with `TASK-` and never exceed 10.
- A backlog task's `status` is one of `planned` / `in_progress` / `blocked` / `done`.
- `state.json` is a **generated artifact** — never hand-edit it. The SSOT is `backlog/tasks/` plus `session_handoff.md`; regenerate with `python -m workflow_kit refresh-state` at session close.
- Handoff §1 baseline lines have a cap. When it is exceeded, **move** the excess with `python -m workflow_kit rollover-baselines` — never delete them by hand. That prose exists nowhere else, unlike the recently-done list whose SSOT is `backlog/tasks/`.
- Handoff §5 accumulated sections (everything outside the declared current-section list) have a byte budget. When it is exceeded, **move** the oldest with `python -m workflow_kit rollover-handoff-notes` — rules go to `lessons.md`, other notes to `sessions/`.
- `session_handoff.md` and the backlog are **inputs to the state.json generator** — writing outside the format silently corrupts state.json.

## 언어

- 사용자에게 보이는 보고 · 요약 · 문서 문안은 한국어로 쓴다. 코드 · 명령 · 경로 · 고유 명칭은 원문 그대로.
- 결론과 다음 행동만 짧게 — 중간 reasoning · 중복 요약 · 자기 설명은 뺀다.
- handoff 와 backlog 에는 다음 세션에 필요한 사실만 남긴다.

## 프로젝트 실행 기본값

개발 환경은 저장소 `.venv` 다 (시스템 python3 는 PEP 668 · dev 의존성 부재로 오탐을 낸다). 활성화 없이 그대로 실행된다.

- **install**: `python3 -m venv .venv && .venv/bin/python3 -m pip install -r requirements.txt -r requirements-dev.txt && .venv/bin/python3 -m pip install -e "./workflow-source[dev,release,mcp-sdk]"`
- **run**: `PYTHONPATH=workflow-source .venv/bin/python3 -m workflow_kit.workflow_kit_cli --command=dashboard --format=json`
- **quick test**: `.venv/bin/python3 workflow-source/tests/run_all_checks.py --filter=<이름조각> --tmp-dir=<실디스크경로>`
- **isolated test**: `.venv/bin/python3 workflow-source/tests/run_all_checks.py --tmp-dir=<실디스크경로>` (격리 venv 에서 전량)
- **smoke check**: `.venv/bin/python3 workflow-source/tests/check_self_application.py`

| 단계 | 명령 |
|---|---|
| 커밋 전 | `run_all_checks.py --changed` + smoke check |
| **push 직전 (게이트)** | 커밋 후 깨끗한 트리에서 `.venv/bin/python3 workflow-source/tests/run_all_checks.py --branch-context=all --tmp-dir=<실디스크경로>` — 통과 기록이 없으면 pre-push hook 과 `release --apply` 가 막는다 |
| 발행 전 · 해당 코드를 건드렸을 때 | `PYTHONPATH=workflow-source .venv/bin/python3 -m workflow_kit.common.interpreter_matrix --run-local` · `PYTHONPATH=workflow-source .venv/bin/python3 -m workflow_kit.common.sdk_matrix --run-local` (`mcp` SDK 코드를 건드렸으면 **반드시**) |

- 새 클론 · 호스트는 `git config core.hooksPath .githooks` 를 한 번 켠다. 게이트 **뒤** 편집하면 다시 돈다.
- 두 에이전트가 전량을 돌려야 하면 `--no-lock` 말고 worktree 를 나눈다. `--tmp-dir` 는 실디스크 경로 (tmpfs 는 OOM).
- 게이트 명령 출력은 파일로 받고 종료 코드를 따로 읽는다 (파이프 뒤 exit 0 에 속지 않는다).

CI 는 없다 — 근거 · 축별 상세 · 검사 작성 규약(`REQUIRES_QUIET_REPO` · `CHECK_TIMEOUT_S` · 경고 red)은 [`docs/LOCAL_GATE.md`](docs/LOCAL_GATE.md).
