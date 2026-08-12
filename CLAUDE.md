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
> 조정했다. 규칙 블록(`## 작업 원칙` / `## 세션 종료 순서` / `## 메모리 갱신 경로`)은
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

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 · §11 — 이 블록은 직접 고치지 않는다. 표준 문서를 고치고 다시 생성한다. -->

- 새 세션은 항상 현재 상태 요약 문서부터 읽는다.
- 작업은 시작 전에 목적, 범위, 예상 산출물, 영향 문서를 짧게 브리핑한다.
- 작업은 상태 문서에 기록하고, 진행 상태는 `planned`, `in_progress`, `blocked`, `done` 중 하나로 관리한다.
- 검증하지 않은 결과는 완료로 확정하지 않는다.
- 세션 종료 전에는 다음 세션이 바로 이어받을 수 있게 현재 상태를 요약한다.
- 여러 에이전트가 함께 일할 수 있으므로, 작업 시작 전에 원격을 동기화해 다른 에이전트의 진행 상황을 확인하고 겹치지 않는 작업을 선택한다.
- 다른 에이전트의 작업을 지우거나 덮어쓰는 등 되돌릴 수 없는 작업은 단독으로 결정하지 않고 사용자에게 확인한다.
- 공통 표준은 얇게 유지하고, 프로젝트별 차이는 프로젝트 프로파일에 둔다.

## 세션 종료 순서

세션 종료는 **memory 갱신 → commit → push** 순서로 진행한다. memory 갱신을 commit 이후 별도 turn 에 분리하지 않는다 (push 시 memory 갱신 내용이 동일 commit 에 포함되도록 협업 정합 보장).

- 종료 전 갱신 대상: `state.json`, `session_handoff.md`, 최신 backlog

## 메모리 갱신 경로

- 세션 시작 baseline 복원: `wk session-start`
- task 등록 / 갱신: `wk backlog-update`
- 영향 문서 동기화 (advisory): `wk doc-sync`
- 세션 종료 시 state.json 재생성: `wk refresh-state`

- handoff 의 `in_progress` / `blocked` 목록이 비면 **빈 bullet `-`** 로 둔다. 산문을 쓰면 작업 항목으로 파싱된다.
- handoff 의 최근 완료 목록 항목은 `TASK-` 로 시작하고, 10건을 넘지 않는다.
- backlog task 의 `status` 는 `planned` / `in_progress` / `blocked` / `done` 중 하나다.
- `state.json` 은 **생성물**이다 — 손으로 고치지 않는다. SSOT 는 `backlog/tasks/` 와 `session_handoff.md` 이고, 세션 종료 시 `wk refresh-state` 로 재생성한다.
- `session_handoff.md` 와 backlog 는 **state.json 생성기의 입력**이다 — 형식을 벗어나 쓰면 state.json 이 조용히 오염된다.

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

- **install**: `python3 -m pip install -r requirements.txt -r requirements-dev.txt && python3 -m pip install -e "./workflow-source[dev,release,mcp-sdk]"`
- **run**: `PYTHONPATH=workflow-source python3 -m workflow_kit.workflow_kit_cli --command=dashboard --format=json`
- **quick test**: `python3 workflow-source/tests/run_all_checks.py --filter=<이름조각> --tmp-dir=<실디스크경로>`
- **isolated test**: `python3 workflow-source/tests/run_all_checks.py --tmp-dir=<실디스크경로>` (격리 venv 에서 전량)

> 전량 검사는 **기본이 병렬**이다 (v1.1.7, `--jobs auto`). 345s → 85s 로 줄었다.
> 재현이 필요하거나 실패를 분리해 보고 싶을 때만 `--jobs 1` 로 순차 실행한다.
> 저장소 전역 상태를 관찰하는 check (`REQUIRES_QUIET_REPO = True` 를 선언한 것들)
> 는 병렬 구간이 끝난 뒤 **정숙 구간**에서 직렬로 돈다 — 새로 그런 check 를 만들면
> 그 선언을 파일 안에 넣어야 한다. 안 넣으면 병렬에서 오탐이 난다.
> 단독 실행이 ~25s 를 넘는 무거운 check 는 `CHECK_TIMEOUT_S = 150` 을 파일 안에
> 선언한다 (v1.1.7+) — 기본 60s 상한은 병렬 부하에서 2배로 늘어진 실행을 죽인다.
> 선언은 CLI `--timeout` 과 max 로 합쳐져 상한을 **늘릴 수만** 있다.
> 전량 runner 는 **워킹 트리 배타 락**을 잡는다 (v1.1.7+, `.git/run_all_checks.lock`).
> 다른 runner 가 돌고 있으면 보유자 정보를 찍고 즉시 실패한다 — 동시 실행된 전량의
> 결과는 PASS 도 FAIL 도 근거가 못 된다. 같은 워킹 트리에서 두 에이전트가 전량을
> 돌려야 하면 락을 우회(`--no-lock`)하지 말고 **worktree 를 분리**한다.
- **smoke check**: `python3 workflow-source/tests/check_self_application.py`

### SDK 매트릭스는 push 전에 로컬에서 돌린다

```bash
PYTHONPATH=workflow-source python3 -m workflow_kit.common.sdk_matrix --run-local
```

`mcp` SDK 를 쓰는 코드를 건드렸으면 **반드시** 이걸 먼저 돌린다. 개발 venv 는
`requirements-dev.txt` 가 깐 하한(1.27.0) 하나뿐이라, 2.x 에서만 갈라지는 코드가
**로컬에서는 통과하고 CI 의 `mcp-sdk-matrix` 에서만 red** 가 된다. 실제로 2026-08-05
에 `CallToolResult.isError`(1.x 이름, 2.0.0 은 `is_error`) 때문에 그렇게 됐고,
저장소가 이미 알고 있던 함정이었는데 로컬에 재현 수단이 없었다.

버전 목록은 `workflow_kit/common/sdk_matrix.py` 의 `PINNED_VERSIONS` 가 정본이고
CI yml 도 거기서 읽는다. venv 는 `.venv-sdk-matrix/` 에 캐시되므로 두 번째부터 빠르다.

### 브랜치 매트릭스도 push 전에 로컬에서 돌린다

```bash
python3 workflow-source/tests/run_all_checks.py --branch-context=all --tmp-dir=<실디스크경로>
```

CI 의 `smoke` 는 전량을 **두 브랜치 컨텍스트**로 돌린다 (`native` / `slash`).
`ai-workflow/memory/active/<branch>/` 는 브랜치 이름으로 경로가 갈리고, 슬래시가 든
브랜치는 중첩 디렉터리가 되며 **그 브랜치의 `state.json` 은 존재하지 않는다** —
main 에서 재면 그 차이가 전부 0이다.

무인자 `run_all_checks.py` 는 `native` 하나만 밟으므로, 위 SDK 매트릭스와 **똑같이**
로컬 green + CI red 가 성립한다. 실제로 2026-08-10 에 그렇게 됐다: 검사 하나가
브랜치의 `state.json` 존재를 전제해 `slash` 셀에서만 red 였고, **15연속 red 인
동안 로컬은 계속 green 이었으며 handoff 는 내내 "전량 검사 green" 을 기록했다.**
열흘 가까이 걸린 이유는 결함이 어려워서가 아니라 로컬에 그 축이 없어서였다.

컨텍스트 목록은 `workflow_kit/common/branch_matrix.py` 의 `BRANCH_CONTEXTS` 가
정본이고 `smoke.yml` 의 prepare job 도 거기서 읽는다
(`check_branch_context_matrix.py` 가 복제를 검출한다). 한 축만 볼 때는
`--branch-context=slash` 로 줄인다.

> `--tmp-dir` 를 실디스크 경로로 주는 이유: `TMPDIR` 가 tmpfs(RAM) 이면 temp 누수가
> 곧 OOM 이 된다.

## 다음에 읽을 문서

- `ai-workflow/README.md` (kit 개요)
- `docs/PROJECT_PROFILE.md` (프로젝트 메타)
- `ai-workflow/memory/active/<branch>/sessions` (현재 세션 인계)
- `harnesses/claude-code/apply_guide.md` (Claude Code 적용 절차)
