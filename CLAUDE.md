<!-- standard-ai-workflow-kit: v1.0.0-beta -->
<!-- standard-ai-workflow-kit-fork: 이 저장소가 소유한다 — 아래 '프로젝트 실행 기본값' 이하가 실측으로 얻은 고유 운영 규칙이다. 재적용하면 placeholder 로 되돌아간다. kit 변경 반영은 생성물과 diff 해 손으로 병합한다 (마지막 병합: v1.9.4 / 2026-09-18, 채택 0 · 기각 3 재확인 — TASK-2026-09-18-main-003) -->
<!-- standard-ai-workflow-kit-overlay: plugin-only — 워크플로우 스킬은 플러그인 채널(marketplace standard-ai-workflow)로만 소비한다. .claude/commands·skills 의 프로젝트 overlay 사본은 두지 않는다 (소유자 결정 2026-08-25, TASK-2026-08-25-main-010 — 두 채널이 같은 스킬을 이중 노출해 정리) -->

# CLAUDE.md (Claude Code 진입점)

- 문서 목적: 표준 AI 워크플로우 의 *directional intent* + Claude Code 가 매 세션 알아야 할 진입 규칙
- 범위: 세션 복원, workflow state docs 참조 순서, 작업 원칙, 세션 종료 순서
- 대상 독자: Claude Code, 저장소 관리자, workflow 설계자
- 상태: beta
- 최종 수정일: 2026-10-02
- 관련 문서: `ai-workflow/memory/active/<branch>/state.json`, `docs/PROJECT_PROFILE.md`

> **이 저장소만의 차이**: 상태 문서가 브랜치별(`ai-workflow/memory/active/<branch>/`)로
> 나뉜다. bootstrap 산출물의 기본값은 평평한 `active/` 라, 상태 문서 경로만 실제에 맞춰
> 조정했다. 규칙 블록(`## Working Principles` / `## Session Close Order` / `## Memory Update Paths`)은
> 손대지 않는다 —
> `core/global_workflow_standard.md` 에서 생성되며 `check_standard_single_source.py`
> 가 정본과의 일치를 강제한다.


## 이 파일의 역할

- **역할**: Claude Code 가 이 저장소에서 *세션 시작 시 자동 read* 하는 진입점 문서.
- **위치**: `./CLAUDE.md` (또는 `./.claude/CLAUDE.md`) — 둘 다 자동 read.
- **AGENTS.md 와의 관계**: Claude Code 는 `AGENTS.md` 를 *직접* read 안 함. 본 프로젝트에
  `AGENTS.md` 가 이미 있으면 본 `CLAUDE.md` 의 `@AGENTS.md` import 또는 symlink 으로 통합 가능:

  ```bash
  # import 방식 (CLAUDE.md 안에 @AGENTS.md 한 줄 추가)
  @AGENTS.md

  # 또는 symlink 방식 (cross-platform 의 경우 import 권장)
  ln -s AGENTS.md CLAUDE.md
  ```

## 항상 먼저 읽을 문서

> `<branch>` 는 현재 git 브랜치 이름이다 (git 저장소가 아니면 `main`). 브랜치별로
> 나누면 동시에 도는 작업이 서로를 덮어쓰지 않는다.

- `ai-workflow/memory/active/<branch>/state.json`
- `ai-workflow/memory/active/<branch>/sessions`
- `ai-workflow/memory/active/<branch>/backlog`
- `docs/PROJECT_PROFILE.md`
- `ai-workflow/wiki/index.md` — R4 anchor 기반, AI agent query 시 먼저 로드
- (있으면) `ai-workflow/memory/active/PURPOSE.md` — directional intent 1-line + body excerpt

`ai-workflow/` 는 세션 복원과 workflow 상태 관리용 메타 레이어다. 프로젝트 코드나
프로젝트 문서를 탐색할 때는 이 경로를 기본 탐색 범위에 넣지 말고, workflow 문서 자체를
갱신하거나 현재 세션 상태를 복원할 때만 예외적으로 참조한다.

## 진입 slash command (additive)

- `/workflow-session-start` — `state.json` + `session_handoff.md` + `work_backlog.md` baseline 복원
- `/workflow-backlog-update` — task 등록/갱신 + scope creep warning
- `/workflow-doc-sync` — 영향 문서 동기화 (advisory)
- `/workflow-session-end` — handoff + backlog 갱신 후 `state.json` 재생성 (세션 종료)

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

## 언어와 컨텍스트 원칙

- 사용자에게 직접 보이는 작업 보고, 상태 요약, 문서 갱신 문안은 기본적으로 한국어로 작성한다.
- 코드, 명령어, 파일 경로, 설정 key, 외부 시스템 고유 명칭은 필요할 때 원문 그대로 유지한다.
- 내부 사고 과정과 임시 분류는 모델이 가장 효율적인 방식으로 처리하되, 사용자에게는 필요한
  결론과 다음 행동만 짧게 전달한다.
- 장문의 중간 reasoning, 중복 요약, 불필요한 자기 설명을 피한다.
- handoff 와 backlog 에는 다음 세션에 필요한 핵심 사실만 남겨 불필요한 컨텍스트 누적을 줄인다.

## self-bootstrap (PURPOSE.md / state.json 부재 시)

`state.json` 이나 `PURPOSE.md` 가 없으면 session-start skill 이 *graceful skip* 으로
동작. 사용자가 직접 `/workflow-session-start` 호출 시 (또는 자동 read 시) baseline 복원을
*최소 effort* 로 시도:

1. `ai-workflow/memory/active/<branch>/state.json` 부재 → 사용자에게 scaffold 제안
2. `PURPOSE.md` 부재 → 4-element placeholder + `init` light 호출 권장
3. `work_backlog.md` 부재 → 빈 인덱스 + 첫 task 등록 안내

## 프로젝트 실행 기본값

**개발 환경은 저장소 `.venv` 다.** 시스템 python3 는 PEP 668 로 pip install 을 거부하고, dev
의존성이 없어 전량 검사가 무더기 오탐을 낸다. uv 로 만든 `.venv` 에 pip 이 없으면
`.venv/bin/python3 -m ensurepip --upgrade`. 아래 명령은 활성화 없이 그대로 실행된다.

- **install**: `python3 -m venv .venv && .venv/bin/python3 -m pip install -r requirements.txt -r requirements-dev.txt && .venv/bin/python3 -m pip install -e "./workflow-source[dev,release,mcp-sdk]"`
- **run**: `PYTHONPATH=workflow-source .venv/bin/python3 -m workflow_kit.workflow_kit_cli --command=dashboard --format=json`
- **quick test**: `.venv/bin/python3 workflow-source/tests/run_all_checks.py --filter=<이름조각> --tmp-dir=<실디스크경로>`
- **isolated test**: `.venv/bin/python3 workflow-source/tests/run_all_checks.py --tmp-dir=<실디스크경로>` (격리 venv 에서 전량)
- **smoke check**: `.venv/bin/python3 workflow-source/tests/check_self_application.py`

| 단계 | 명령 | 언제 |
|---|---|---|
| 편집 중 | `run_all_checks.py --filter=<이름조각>` | 방금 건드린 것과 그 이웃만 |
| 커밋 전 | `run_all_checks.py --changed` + `check_self_application.py` | 검사의 `WATCHES` 선언이 관련 검사를 고른다 |
| **push 직전 1회** | 커밋 후 깨끗한 트리에서 `.venv/bin/python3 workflow-source/tests/run_all_checks.py --branch-context=all --tmp-dir=<실디스크경로>` | **이것이 게이트다.** 통과하면 HEAD sha 의 게이트 통과 기록이 남고 pre-push hook 과 `release --apply` 가 요구한다 |
| 발행 전 · 해당 코드를 건드렸을 때 | `PYTHONPATH=workflow-source .venv/bin/python3 -m workflow_kit.common.interpreter_matrix --run-local` · `PYTHONPATH=workflow-source .venv/bin/python3 -m workflow_kit.common.sdk_matrix --run-local` | CI 가 없어 로컬 말고는 아무도 안 돈다. `mcp` SDK 를 쓰는 코드를 건드렸으면 sdk 매트릭스는 **반드시** |

- **기록 없는 커밋은 push 되지 않는다** — 새 클론·호스트는 `git config core.hooksPath .githooks` 를 한 번 켠다. 게이트를 돈 **뒤** 편집하면 다시 돈다 (`--no-verify` push 는 게이트 근거가 없다).
- **GitHub Actions 테스트 workflow 는 없다** (2026-09-23). Windows/macOS 소비자 설치 · MCP Inspector · 외부 URL 검증은 지금 아무도 재지 않는다.
- 전량은 병렬이 기본이고 워킹 트리 배타 락을 잡는다 — 두 에이전트가 전량을 돌려야 하면 `--no-lock` 말고 **worktree 를 나눈다**.
- 저장소 전역 상태를 보는 검사는 `REQUIRES_QUIET_REPO = True`, 단독 ~25s 를 넘는 검사는 `CHECK_TIMEOUT_S = 150` 을 파일 안에 선언한다.
- 게이트는 두 브랜치 컨텍스트(`native` · `slash`)를 돈다. 조건부 1축 생략은 기각됐다 — 한 축만 볼 때는 `--branch-context=slash` 를 명시한다.
- 저장소 코드가 낸 Python 경고는 게이트 red 다. 의도한 deprecation 호출은 `check_warnings.call_deprecated` 로 감싼다.
- `--tmp-dir` 는 실디스크 경로로 준다 — `TMPDIR` 가 tmpfs 면 temp 누수가 곧 OOM 이다.

근거·실측·축별 상세는 [`docs/LOCAL_GATE.md`](docs/LOCAL_GATE.md) 에 있다.

## 다음에 읽을 문서

- `ai-workflow/README.md` (kit 개요)
- `docs/PROJECT_PROFILE.md` (프로젝트 메타)
- `ai-workflow/memory/active/<branch>/sessions` (현재 세션 인계)
- `harnesses/claude-code/apply_guide.md` (Claude Code 적용 절차)
