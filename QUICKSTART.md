# QUICKSTART.md

- 문서 목적: 표준 AI 워크플로우를 신규 또는 기존 프로젝트에 5분 내로 도입하는 핵심 절차를 안내한다.
- 범위: bootstrap 실행, 하네스 연결, 첫 세션 시작 방법
- 대상 독자: 프로젝트 관리자, AI 에이전트 사용자, 워크플로우 설계자
- 상태: beta
- 최종 수정일: 2026-04-26

## 1. 개요

표준 AI 워크플로우는 AI 에이전트와 사람이 협업할 때 **상태(State), 인계(Handoff), 백로그(Backlog)**를 일관되게 관리하기 위한 문서 체계와 도구 모음입니다.

## 2. 빠른 도입 방법 (Bootstrap)

저장소 루트에서 아래 명령을 실행하여 워크플로우 환경을 구축합니다.

### A. 신규 프로젝트인 경우
```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root . \
  --project-slug my-project \
  --project-name "My New Project" \
  --adoption-mode new \
  --harness gemini-cli \
  --copy-core-docs
```

### B. 기존 프로젝트인 경우
```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root . \
  --project-slug my-existing-project \
  --project-name "My Existing Project" \
  --adoption-mode existing \
  --harness gemini-cli \
  --copy-core-docs
```

*참고: `--harness` 옵션에 `codex`, `opencode`, `gemini-cli` 중 사용하는 도구를 지정할 수 있습니다.*

## 3. 도입 후 핵심 파일

도입이 완료되면 다음 파일들이 생성됩니다:

- `GEMINI.md` (또는 `AGENTS.md`, `opencode.json`): AI 에이전트의 진입점 및 시스템 지침 오버레이.
- `ai-workflow/project/`: 프로젝트별 상태 관리 문서들.
  - `state.json`: 워크플로우 전체 상태의 단일 진실 공급원(Source of Truth).
  - `session_handoff.md`: 세션 간 작업 맥락 인계 문서.
  - `work_backlog.md`: 전체 작업 목록 및 일자별 백로그 인덱스.
  - `project_workflow_profile.md`: 프로젝트 전용 명령(설치, 실행, 테스트) 정의.

## 4. 첫 세션 시작하기

1. AI 에이전트에게 `GEMINI.md` (또는 `AGENTS.md`)를 먼저 읽도록 지시합니다.
2. 에이전트가 `ai-workflow/project/session_handoff.md`를 통해 현재 상태를 파악하게 합니다.
3. `ai-workflow/project/project_workflow_profile.md`의 TODO 항목들을 실제 프로젝트 환경에 맞게 수정합니다. (특히 설치/실행/테스트 명령)
4. 오늘 날짜의 백로그 문서(`ai-workflow/project/backlog/YYYY-MM-DD.md`)에 첫 번째 작업을 등록하고 시작합니다.

## 5. 주요 워크플로우 스킬 (Beta)

에이전트는 다음 스킬들을 사용하여 작업을 보조할 수 있습니다:

- `session-start`: 새 세션 시작 시 상태 복원 및 브리핑.
- `backlog-update`: 작업 진행 상태 반영 및 백로그 갱신.
- `doc-sync`: 워크플로우 문서 간 데이터 동기화.
- `validation-plan`: 변경 사항 검증을 위한 테스트 계획 수립 및 뼈대 생성.
- `code-index-update`: 코드 변경 사항을 프로젝트 색인에 반영.

## 6. 더 알아보기

- 상세 가이드: `ai-workflow/README.md`
- 스킬 카탈로그: `ai-workflow/core/workflow_skill_catalog.md`
- 하네스별 적용 안내: `harnesses/README.md`

---
*표준 AI 워크플로우 Beta v1 릴리즈를 환영합니다!*
