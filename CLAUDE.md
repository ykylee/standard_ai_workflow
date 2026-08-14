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

- When the handoff's `in_progress` / `blocked` lists are empty, leave an **empty bullet `-`**. Prose there is parsed as a work item.
- Entries in the handoff's recently-completed list start with `TASK-` and never exceed 10.
- A backlog task's `status` is one of `planned` / `in_progress` / `blocked` / `done`.
- `state.json` is a **generated artifact** — never hand-edit it. The SSOT is `backlog/tasks/` plus `session_handoff.md`; regenerate with `wk refresh-state` at session close.
- Handoff §1 baseline lines have a cap. When it is exceeded, **move** the excess with
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

**개발 환경은 저장소 `.venv` 다.** 시스템 python3(homebrew)는 PEP 668
(`externally-managed-environment`)로 pip install 을 거부하고, 설치가 됐더라도 dev
의존성(mypy/jsonschema/mcp)이 없어 **전량 검사가 의존성 부재로 무더기 오탐**을 낸다
(2026-08-14 실측: homebrew python3 로 전량 2축을 돌려 9건 red — 전부 미설치였고 코드
결함은 0건). 아래 명령은 활성화 없이 그대로 복사해 실행 가능한 형태다.
기존 `.venv` 가 uv 로 만들어져 pip 이 없으면(`No module named pip`)
`.venv/bin/python3 -m ensurepip --upgrade` 한 번으로 채운다 (2026-08-14 이 호스트 실측).

- **install**: `python3 -m venv .venv && .venv/bin/python3 -m pip install -r requirements.txt -r requirements-dev.txt && .venv/bin/python3 -m pip install -e "./workflow-source[dev,release,mcp-sdk]"`
- **run**: `PYTHONPATH=workflow-source .venv/bin/python3 -m workflow_kit.workflow_kit_cli --command=dashboard --format=json`
- **quick test**: `.venv/bin/python3 workflow-source/tests/run_all_checks.py --filter=<이름조각> --tmp-dir=<실디스크경로>`
- **isolated test**: `.venv/bin/python3 workflow-source/tests/run_all_checks.py --tmp-dir=<실디스크경로>` (격리 venv 에서 전량)

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
- **smoke check**: `.venv/bin/python3 workflow-source/tests/check_self_application.py`

### 전량은 게이트지 확인 수단이 아니다 (2026-08-14 실측)

**편집할 때마다 전량을 돌리지 않는다.** 축당 벽시계 ~195s 이고 2축이면 ~6.5분이라,
반복 편집 중에 돌리면 그것만으로 세션이 간다 (2026-08-14 세션: 전량 2축 5회 =
약 33분 중 게이트로서 의미 있던 것은 push 직전 1회뿐).

| 단계 | 명령 | 언제 |
|---|---|---|
| 편집 중 | `run_all_checks.py --filter=<이름조각>` | 방금 건드린 것과 그 이웃만. 초 단위로 끝난다 |
| 커밋 전 | 관련 검사 + `check_self_application.py` | 메모리/문서를 건드렸으면 이것부터 (`task_status_mismatch` 류를 여기서 잡는다) |
| **push 직전 1회** | `run_all_checks.py --branch-context=all` | **이것이 게이트다.** 여기만 2축 전량 |

**시간을 쓰는 것은 개수가 아니라 8개다** (1축 실측: CPU 819s / 255 checks, 벽시계
196s, 160개는 1초 미만): `wiki_score` 68s(병렬 구간 임계경로) · `release_summary` 62s ·
`release_status_auto_bump` 57s · `release_status` 48s · `release_pipeline_lib` 44s ·
`mypy_config_actually_loaded` 41s · `no_repo_write` 39s(정숙 구간 61s 의 64%) ·
`branch_context_matrix` 32s. `--filter` 로 좁힐 때 이 이름들을 피하면 대개 즉시 끝난다.


### SDK 매트릭스는 push 전에 로컬에서 돌린다

```bash
PYTHONPATH=workflow-source .venv/bin/python3 -m workflow_kit.common.sdk_matrix --run-local
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
.venv/bin/python3 workflow-source/tests/run_all_checks.py --branch-context=all --tmp-dir=<실디스크경로>
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
