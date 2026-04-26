# Prototype V4 Pre-release

- 날짜: 2026-04-25
- 버전: `prototype-v4`
- 주요 변경 사항: 템플릿 최적화, OpenCode 통합, Bootstrap 로직 개선

## 1. 주요 개선 사항

### 템플릿 컨텍스트 최적화
- `templates/` 내의 모든 템플릿에서 불필요한 메타데이터와 예시 텍스트를 제거.
- LLM 에이전트가 매 세션 읽어야 하는 고정 컨텍스트 비용을 약 40-50% 절감.
- 기계 가독성을 높이기 위해 구조적 명확성 확보 및 자리표시자(<Placeholder>) 도입.

### Bootstrap 스크립트 고도화
- `scripts/bootstrap_workflow_kit.py`가 하드코딩된 문자열 대신 `templates/`의 최신 파일을 사용하도록 수정.
- 템플릿 수정 사항이 `bootstrap` 결과물에 즉시 반영되는 구조로 개선.

### 하네스 지원 확장
- **OpenCode 공식 지원:** `opencode.json` 및 `.opencode/agents/` 설정을 통한 멀티 에이전트(Orchestrator-Worker) 워크플로우 지원 통합.
- **Gemini CLI 안정화:** `GEMINI.md` 지침 준수 및 self-dogfooding 설정 강화.

### 워크플로우 품질 기준 수립
- `core/skill_beta_criteria.md` 추가: 스킬들을 프로토타입에서 베타 수준으로 올리기 위한 기술적/문서적 기준 정의.

## 2. 포함된 패키지

- `standard-ai-workflow-codex-prototype-v4.zip`
- `standard-ai-workflow-gemini-cli-prototype-v4.zip`
- `standard-ai-workflow-opencode-prototype-v4.zip`

## 3. 다음 단계

- `session-start`, `backlog-update` 스킬에 대한 자동화된 smoke test 추가.
- 실제 신규 프로젝트(빈 저장소) 대상 bootstrap 시나리오 반복 검증.
- `core/` 표준 문서들을 바탕으로 실제 에이전트 연동 프로토타입 구체화.
