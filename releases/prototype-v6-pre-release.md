# Prototype V6 Pre-release

- 날짜: 2026-04-28
- 버전: `v3.0.2-beta` (Prototype V6)
- 주요 변경 사항: 빈 프로젝트 오판 버그 수정, Phase 6 진입 및 공유용 소개자료 추가

## 1. 주요 개선 사항

### 기존 저장소 분석 로직 안정화 (중요)
- **빈 프로젝트 오판 방지:** 기존 저장소 모드(`--adoption-mode existing`)로 도입 시, 대상 디렉토리가 비어 있으면 `ai-workflow` 키트 내부 파일을 프로젝트 코드로 오해하던 로직을 수정했습니다.
- **필터링 강화:** `iter_repo_files` 및 `analyze_repo_structure` 함수에 `ignore_dirs` 파라미터를 추가하여 분석 시 키트 디렉토리를 명시적으로 제외하도록 보정했습니다.

### Phase 6 진입 및 지능형 도구 최적화
- **정밀 편집 및 읽기:** `robust-patcher`(정밀 패치 엔진)와 `smart-context-reader`(AST 기반 소스 코드 분석기)가 `core/maturity_matrix.json`에 추가되었습니다.
- **상태 동기화:** 로드맵과 마일스톤 상태를 2026-04-28 기준으로 최신화하여 팀 내 전파 준비를 마쳤습니다.

### 팀 협업 지원 강화
- **소개 자료 추가:** 팀원들이 워크플로우의 가치를 한눈에 파악할 수 있는 `ai-workflow/docs/INTRODUCTION_DECK.md`를 포함했습니다.
- **도입 가이드 업데이트:** `core/workflow_adoption_entrypoints.md`에 기술적 안정성 개선 사례를 반영했습니다.

## 2. 포함된 패키지

- `standard-ai-workflow-codex-v3.0.2-beta.zip`
- `standard-ai-workflow-gemini-cli-v3.0.2-beta.zip`
- `standard-ai-workflow-opencode-v3.0.2-beta.zip`
- `standard-ai-workflow-pi-dev-v3.0.2-beta.zip`

## 3. 적용 방법

1.  `scripts/bootstrap_workflow_kit.py`를 실행하여 최신 키트를 배포합니다.
2.  `ai-workflow/docs/INTRODUCTION_DECK.md`를 통해 팀원들에게 핵심 가치를 공유합니다.
3.  기존 프로젝트라면 생성된 `repository_assessment.md`를 통해 분석 결과의 정확도를 확인합니다.

---
**주의:** 이전 릴리스에서 발견된 마크다운 문법 오류를 점검 완료했습니다. 모든 문서의 링크와 코드 블록은 표준 규격을 따릅니다.
