<!-- standard-ai-workflow-kit: v1.0.0-beta -->

# CLAUDE.md (Claude Code 진입점)

- 문서 목적: 표준 AI 워크플로우 의 *directional intent* + Claude Code 가 매 세션 알아야 할 진입 규칙
- 범위: 세션 복원, workflow state docs 참조 순서, 작업 원칙, 세션 종료 순서
- 대상 독자: Claude Code, 저장소 관리자, workflow 설계자
- 상태: beta
- 최종 수정일: 2026-07-27
- 관련 문서: `ai-workflow/memory/active/<branch>/state.json`, `docs/PROJECT_PROFILE.md`

> **이 저장소만의 차이**: 상태 문서가 브랜치별(`ai-workflow/memory/active/<branch>/`)로
> 나뉜다. bootstrap 산출물의 기본값은 평평한 `active/` 라, 상태 문서 경로만 실제에 맞춰
> 조정했다. 규칙 블록(`## 작업 원칙` / `## 세션 종료 순서`)은 손대지 않는다 —
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

## 작업 원칙

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 — 이 블록은 직접 고치지 않는다. 표준 문서를 고치고 다시 생성한다. -->

- 새 세션은 항상 현재 상태 요약 문서부터 읽는다.
- 작업은 시작 전에 목적, 범위, 예상 산출물, 영향 문서를 짧게 브리핑한다.
- 작업은 상태 문서에 기록하고, 진행 상태는 `planned`, `in_progress`, `blocked`, `done` 중 하나로 관리한다.
- 검증하지 않은 결과는 완료로 확정하지 않는다.
- 세션 종료 전에는 다음 세션이 바로 이어받을 수 있게 현재 상태를 요약한다.
- 공통 표준은 얇게 유지하고, 프로젝트별 차이는 프로젝트 프로파일에 둔다.

## 세션 종료 순서

세션 종료는 **memory 갱신 → commit → push** 순서로 진행한다. memory 갱신을 commit 이후 별도 turn 에 분리하지 않는다 (push 시 memory 갱신 내용이 동일 commit 에 포함되도록 협업 정합 보장).

- 종료 전 갱신 대상: `state.json`, `session_handoff.md`, 최신 backlog

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

- **install**: TODO: 설치 명령 입력
- **run**: TODO: 로컬 실행 명령 입력
- **quick test**: TODO: 빠른 테스트 명령 입력
- **isolated test**: TODO: 격리 테스트 명령 입력
- **smoke check**: TODO: 실행 확인 명령 입력

위 명령은 추정값이다. 실제 프로젝트 명령으로 보정 후 commit.

## 다음에 읽을 문서

- `ai-workflow/README.md` (kit 개요)
- `docs/PROJECT_PROFILE.md` (프로젝트 메타)
- `ai-workflow/memory/active/<branch>/sessions` (현재 세션 인계)
- `harnesses/claude-code/apply_guide.md` (Claude Code 적용 절차)
