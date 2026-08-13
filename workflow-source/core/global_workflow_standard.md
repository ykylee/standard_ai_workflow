# Global Workflow Standard

- 문서 목적: 모든 저장소에서 공통으로 적용되는 AI 에이전트 협업 표준을 정의한다.
- 범위: 문서 구조, 세션 핸드오프, 작업 분류 및 모드(Task Modes) 기준
- 상태: stable
- 최종 수정일: 2026-08-13
- 관련 문서: `../templates/project_workflow_profile_template.md`, `../templates/session_handoff_template.md`, `../templates/work_backlog_template.md`, **외부 contract: [`./orchestrator_subagent_contract_v1.md`](./orchestrator_subagent_contract_v1.md)**, [`./workflow_agent_topology.md`](./workflow_agent_topology.md)

## 1. 공통 원칙

- 새 세션은 항상 현재 상태 요약 문서부터 읽는다.
- 작업은 시작 전에 목적, 범위, 예상 산출물, 영향 문서를 짧게 브리핑한다.
- 작업은 상태 문서에 기록하고, 진행 상태는 `planned`, `in_progress`, `blocked`, `done` 중 하나로 관리한다.
- 검증하지 않은 결과는 완료로 확정하지 않는다.
- 세션 종료 전에는 다음 세션이 바로 이어받을 수 있게 현재 상태를 요약한다.
- 여러 에이전트가 함께 일할 수 있으므로, 작업 시작 전에 원격을 동기화해 다른 에이전트의 진행 상황을 확인하고 겹치지 않는 작업을 선택한다.
- 다른 에이전트의 작업을 지우거나 덮어쓰는 등 되돌릴 수 없는 작업은 단독으로 결정하지 않고 사용자에게 확인한다.
- 공통 표준은 얇게 유지하고, 프로젝트별 차이는 프로젝트 프로파일에 둔다.

## 1.1 언어와 보고 원칙

- 사용자에게 직접 보여지는 작업 보고, 상태 요약, 문서 초안, handoff, backlog 갱신 문안은 기본적으로 한국어로 작성한다.
- 저장소 표준 문서와 템플릿도 별도 예외가 없으면 한국어를 기본 언어로 유지한다.
- 코드, 명령어, 파일 경로, 설정 key, 외부 시스템 고유 명칭은 필요할 때 원문 그대로 유지할 수 있다.
- 프로젝트 특성상 영어 산출물이 꼭 필요한 경우에는 프로젝트 프로파일에 예외를 명시한다.

## 1.2 컨텍스트 절약 원칙

- 사용자에게 보이지 않는 내부 처리, 중간 분류, 임시 사고 과정은 모델이 가장 효율적인 형태로 수행한다.
- 중간 reasoning 을 장문으로 반복 출력하지 않는다.
- 이미 확인한 사실을 매 단계 길게 재서술하지 않고, 필요한 결론과 다음 행동만 짧게 남긴다.
- 작업 중 누적되는 컨텍스트는 현재 의사결정과 다음 행동에 필요한 정보 중심으로 유지한다.
- 긴 원문 인용, 중복 요약, 불필요한 체크리스트 복제를 피한다.
- 세션 문서에는 최종 결정, 검증 결과, 다음 세션에 필요한 사실만 남기고 내부 탐색 흔적은 최소화한다.
- orchestrator 와 worker 를 나눠 운영할 수 있는 하네스에서는 메인 orchestrator 가 직접 도구 호출을 떠안기보다 task delegation 과 결과 통합에 집중하는 구성을 기본값으로 둔다.
- 실제 탐색, 수정, 검증은 bounded scope worker 에 맡기고, ask 는 genuinely blocking decision 이나 위험한 외부 작업으로만 좁히는 편을 기본 원칙으로 둔다.
- `ai-workflow/` 는 세션 복원과 workflow 상태 관리용 메타 레이어로 보고, 프로젝트 코드/문서 탐색 범위에는 기본적으로 포함하지 않는다.
- 메인 orchestrator 와 sub-agent 간 위임은 [`./orchestrator_subagent_contract_v1.md`](./orchestrator_subagent_contract_v1.md) 의 외부 contract v1 을 따른다 (v0.5.4 부터 적용, v0.5.3 이하 시스템은 점진 적용 권장).
## 1.3 작업 모드 (Task Modes)

작업의 성격에 따라 최적화된 워크플로우를 제공하기 위해 아래 모드를 지원한다. 세부 정의는 `workflow_task_modes.md`를 따른다.

- **Analysis**: 구조 분석 및 탐색 중심.
- **Requirements**: 니즈 수집 및 명세화 중심.
- **Design**: 아키텍처 및 상세 설계 중심.
- **Planning**: 태스크 분해 및 일정 계획 중심.
- **Implementation**: 코드 작성 및 단위 검증 중심.
- **Refactoring**: 코드 개선 및 회귀 테스트 중심.

운영 원칙:
- 세션 오케스트레이터는 현재 작업의 성격을 판단하여 모드를 전환하고, 해당 모드에 최적화된 에이전트 토폴로지를 구성한다.

## 2. 세션 시작 순서

1. 세션 상태 요약 문서를 읽는다.
2. 작업 백로그 인덱스와 최신 날짜 백로그를 읽는다.
3. 진행 중 또는 차단 작업이 있는지 확인한다.
4. 현재 프로젝트 프로파일을 읽고 저장소별 명령과 문서 구조를 확인한다.

## 3. 작업 상태값

| 상태 | 의미 |
| --- | --- |
| `planned` | 시작 준비는 됐지만 본격 수행 전 |
| `in_progress` | 현재 세션 또는 다음 세션에서 이어서 처리 중 |
| `blocked` | 외부 의존성 또는 결정 대기 때문에 진행 불가 |
| `done` | 완료 기준과 검증 근거를 갖춘 상태 |

## 4. 작업 기록 최소 필드

각 작업 항목은 최소한 아래 필드를 가져야 한다.

- 작업명
- 상태
- 우선순위
- 요청일
- 완료일
- 담당
- 호스트명
- 호스트 IP
- 영향 문서
- 작업 내용
- 진행 현황
- 완료 기준
- 작업 결과
- 다음 세션 시작 포인트
- 남은 리스크
- 후속 작업

## 5. 검증 수준

검증은 아래 4단계 중 필요한 수준까지 수행한다.

1. 빠른 로컬 검증
2. 격리 검증
3. 실행 확인
4. 결과 기록

문서 변경만 있어도 최소한 정적 무결성 점검은 권장한다.

## 6. 결과 기록 최소 기준

검증을 수행했다면 아래 중 해당되는 결과를 상태 문서에 남겨야 한다.

- 통과한 명령
- 실패한 명령과 원인
- 미실행 항목과 사유
- 실행 확인 요약
- 남은 리스크

## 7. 상태 동기화 및 가버넌스 가이드라인 (v0.5.10-beta 기준)

문서 파편화와 로드맵 뒤처짐을 방지하기 위해 아래의 동기화 규칙을 준수한다.

### 7.1 단일 진실 공급원 (SSOT)
- 모든 스킬, MCP, 마일스톤의 공식 상태는 `core/maturity_matrix.json`에서 관리한다.
- 로드맵(`workflow_kit_roadmap.md`), 스킬 카탈로그(`workflow_skill_catalog.md`), MCP 카탈로그(`workflow_mcp_candidate_catalog.md`) 등은 이 JSON 데이터를 바탕으로 기술되어야 한다.
- 하네스 진입점(`CLAUDE.md`, `AGENTS.md`, `GEMINI.md` 등)에 실리는 규칙 문장은 **본 문서의 §1 · §3 · §8 에서 생성**한다. 진입점 파일에도, 렌더러 코드에도 규칙을 직접 적지 않는다. 추출기는 `workflow_kit/common/standard_rules.py`, 강제 검사는 `tests/check_standard_single_source.py` 다.

### 7.2 동기화 루틴
- **스킬 승급 시**: 코드 구현 완료 후 `maturity_matrix.json`의 `stage`를 변경하고, 즉시 관련 카탈로그 문서를 갱신한다.
- **TASK 완료 시**: 세션 종료 전, 완료된 TASK가 로드맵의 마일스톤이나 스킬 상태에 영향을 주는지 확인하고 일괄 반영한다.

### 7.3 자동 검증 (Workflow Linter)
- `workflow-linter`는 `maturity_matrix.json`을 참조하여 아래 사항을 검사한다.
    - 선언된 `test_path` 파일의 실제 존재 여부.
    - 구현 완료(`stable`/`beta`)로 선언된 항목의 실제 코드/스크립트 존재 여부.
    - 로드맵 문서의 단계와 JSON의 마일스톤 단계 일치 여부.

## 8. 세션 종료 원칙 및 절차

세션 종료는 **memory 갱신 → commit → push** 순서로 진행한다. memory 갱신을 commit 이후 별도 turn 에 분리하지 않는다 (push 시 memory 갱신 내용이 동일 commit 에 포함되도록 협업 정합 보장).

**8.1 종료 절차 (memory → commit → push)**
1. **memory 갱신** (commit 직전): 오늘 작업 결과를 상태 문서에 반영한다.
   - `state.json`, `session_handoff.md`, `work_backlog.md` 등 active memory 갱신
   - 미검증 항목과 남은 리스크를 명시한다
   - **문서 정합성 동기화**: `maturity_matrix.json`을 업데이트하고 관련 계획 문서(Roadmap/Catalog)를 최신화한다
2. **최종 검증**: `workflow-linter`를 실행하여 문서 간 불일치가 없는지 확인한다.
3. **다음 세션 시작 포인트** + **종료 요약** 을 handoff 에 짧게 적는다 (다음 세션이 바로 이어받는 데 필요한 핵심 사실만 간결하게).
4. **commit + push**: memory 갱신이 *모두 포함된 상태* 로 단일 commit 작성 + push. (협업자가 push 시점에 memory 갱신까지 함께 본다)

**8.2 commit 이후 추가 memory 작업 (예외, 의도적 허용)**
- `summarize_git_history` 로 commit hash 를 handoff 에 반영하는 작업은 commit 이후에 의미가 있다. 이는 *예외*로 허용하되 그 자체가 별도 commit 의 대상은 아니다 (다음 작업의 memory 갱신 cycle 에 흡수).
- 별도 turn "memory 에 적어줘" 호출은 deprecated. memory 갱신은 결과 commit 직전 같은 turn 에 묶어서 처리한다.

**8.3 잘못된 순서 (안티패턴)**
- ❌ commit → push → 별도 turn memory 갱신 → 또 commit → push (memory 갱신 누락 / 추가 commit 유발 → 협업 결함)
- ❌ memory 갱신 누락 후 commit → push (협업자가 memory 변경을 push 시점에 못 봄)

## 8.4 자기 적용 (self-application)

이 워크플로우는 **스스로에게 먼저 적용된다.** 배포하는 것을 우리가 쓰지 않으면 그것이
실제로 동작하는지 알 방법이 없다. 구체적으로:

- 이 저장소는 자기 진입점 파일을 **자기 렌더러로 생성해서** 가진다.
- 이 저장소는 자기 상태를 자기 규약대로 둔다 (`ai-workflow/memory/active/<branch>/`).
- 이 저장소의 린터와 session-start 는 **이 저장소에서 통과해야 한다.**
- 새 규칙을 이 문서에 추가할 때는 **그 규칙을 검사할 방법을 함께 제안한다.** 검사할
  방법이 없으면 규칙이 아니라 가이드로 분류한다.

설계 원리와 원리별 강제 검사 매핑은 [`./workflow_design_principles.md`](./workflow_design_principles.md) 에 있고,
자기 적용 여부는 `tests/check_self_application.py` 가 확인한다.

## 9. 프로젝트 프로파일과의 관계

이 문서는 공통 코어만 정의한다. 아래 항목은 프로젝트 프로파일로 분리한다.

- 기본 빌드/테스트/실행 명령
- 문서 디렉터리 구조
- 환경 기록 경로
- 프로젝트 특화 검증 포인트
- 병합/승인 예외 규칙

## 10. 다중 작업과 협업 (multi-agent teamwork)

여러 에이전트가 같은 저장소에서 동시에 일할 때의 공통 규칙이다. 혼자 쓰는 저장소에서도
같은 절차를 따른다 — 나중에 다른 에이전트가 합류할 때 규칙이 달라지지 않아야 하고,
"지금은 나뿐" 이라는 가정은 원격을 확인하기 전에는 사실이 아니기 때문이다.

설계 근거와 실측 기록: [`./multi_workspace_orchestration.md`](./multi_workspace_orchestration.md) §0 (정본 요약).

### 10.1 작업 단위와 격리

- **워크스페이스 1개 = 작업 1개 = 브랜치 1개 = 에이전트 1명.**
- 작업 상태(`state.json` / backlog / sessions)는 브랜치별로 분리해 보관한다.
- 격리 키는 **git 이 존재를 검증할 수 있는 브랜치명** 이어야 한다. 도구명·하네스명처럼
  git 이 모르는 이름으로 상태 디렉터리를 만들지 않는다.

### 10.2 세션 시작 — 확인하고 선점한다

1. **원격을 먼저 동기화한다** (`git fetch --prune`). 이 단계를 건너뛰면 다른 에이전트의
   최신 활동이 보이지 않아, 남이 진행 중인 작업을 죽은 것으로 오판한다.
2. 원격의 활성 브랜치로 **다른 에이전트의 진행 상황을 확인**한다. 브랜치 목록이 곧
   진행 중인 작업 목록이다.
3. 겹치지 않는 작업을 고른다.
4. 브랜치를 만들고 **작업 상태 문서를 먼저 생성한 뒤**, 작업 예정 내역을 담아
   **1회 push 한다.** 이 push 가 곧 작업 선점이며, 다른 에이전트에게 예정 내역을
   공유하는 수단이다.

push 가 거부되면 **다른 에이전트가 이미 그 작업을 가져갔다는 신호** 다. 뚫어야 할
장애가 아니므로, 1로 돌아가 다른 작업을 고른다.

### 10.3 공유 파일 취급

- 상태 문서는 **도구를 통해 갱신한다.** 파일을 통째로 다시 쓰면 다른 에이전트가 추가한
  항목이 충돌 없이 사라질 수 있다.
- 공유 append 파일에 남기는 줄에는 **시각과 작성 주체를 포함한다.** 동일한 줄은 병합
  과정에서 하나로 합쳐질 수 있다.
- 파생 파일(예: `state.json`)은 충돌 시 손으로 합치지 않고 **재생성한다.**

### 10.4 사용자 확인이 필요한 작업

에이전트가 단독으로 결정하지 않고 **반드시 사용자에게 확인**한다.

- 다른 에이전트의 브랜치를 삭제하거나 덮어쓰는 일 (`--force` 계열 포함).
- 마지막 활동 이후 **1일이 지난** 브랜치의 처리. 활동이 없다는 것과 작업이 끝났다는
  것은 다르므로, 도구는 보고만 하고 판단은 사람이 한다.

원칙: **되돌릴 수 없는 작업은 에이전트가 단독으로 결정하지 않는다.**

## 11. 메모리 갱신 경로와 파싱 계약

메모리 문서(`state.json` / `session_handoff.md` / backlog)는 **도구를 거쳐 갱신한다.**
도구가 그 문서들의 형식 계약을 알고 있고, 손으로 쓰면 그 계약이 조용히 깨진다.
실측(2026-08-11): handoff 의 빈 목록에 산문 "(없음 …)" 을 써 두었더니 `state.json` 이
그것을 **작업 항목 하나로** 읽었고, 아무 검사도 그것을 오류로 보지 않았다.

**11.1 갱신 명령**

| 목적 | 명령 |
|---|---|
| 세션 시작 baseline 복원 | `wk session-start` |
| task 등록 / 갱신 | `wk backlog-update` |
| 영향 문서 동기화 (advisory) | `wk doc-sync` |
| 세션 종료 시 state.json 재생성 | `wk refresh-state` |

**11.2 파싱 계약** — 도구를 쓰지 않고 손으로 쓸 때도 지켜야 한다

- handoff 의 `in_progress` / `blocked` 목록이 비면 **빈 bullet `-`** 로 둔다. 산문을 쓰면 작업 항목으로 파싱된다.
- handoff 의 최근 완료 목록 항목은 `TASK-` 로 시작하고, 10건을 넘지 않는다.
- backlog task 의 `status` 는 `planned` / `in_progress` / `blocked` / `done` 중 하나다.
- `state.json` 은 **생성물**이다 — 손으로 고치지 않는다. SSOT 는 `backlog/tasks/` 와 `session_handoff.md` 이고, 세션 종료 시 `wk refresh-state` 로 재생성한다.
- `session_handoff.md` 와 backlog 는 **state.json 생성기의 입력**이다 — 형식을 벗어나 쓰면 state.json 이 조용히 오염된다.

## 다음에 읽을 문서

- 프로젝트 프로파일 템플릿: [../templates/project_workflow_profile_template.md](../templates/project_workflow_profile_template.md)
- 세션 인계 템플릿: [../templates/session_handoff_template.md](../templates/session_handoff_template.md)
