# Document Index

- 문서 목적: 프로젝트의 영구 지식 자산(Knowledge Base)을 체계적으로 정리하여 개발자와 AI 에이전트의 온보딩 및 분석을 돕는다.
- 범위: 프로젝트 설계, 개발 및 표준, 분석 및 계획
- 대상 독자: 개발자, AI 에이전트, 프로젝트 온보딩 담당자
- 상태: stable
- 최종 수정일: 2026-07-18
- 관련 문서: [Documentation Governance](./index.md) (저장소 governance 의 진입점), [README.md](https://github.com/ykylee/standard_ai_workflow/blob/main/README.md)

이 인덱스는 프로젝트의 영구 지식 자산(Knowledge Base)을 체계적으로 정리하여 개발자와 AI 에이전트의 온보딩 및 분석을 돕습니다.

> [!NOTE]
> 세션 상태, 백로그 등 워크플로우 운영 문서는 `ai-workflow/` 폴더를 참조하십시오. 이 인덱스는 프로젝트 자체의 설계와 개발 지침만을 포함합니다.

## 1. 프로젝트 설계 (Architecture)
*시스템 구조 및 핵심 설계 원칙을 다룹니다.*

- **[Project Profile](./PROJECT_PROFILE.md)**: 프로젝트 개요, 목적, 설치/실행 가이드 및 워크플로우 기본 규칙.
- **[Architecture docs](https://github.com/ykylee/standard_ai_workflow/tree/main/docs/architecture/)**: 프로젝트 아키텍처 개요 및 ADR.
- **[Planning docs](https://github.com/ykylee/standard_ai_workflow/tree/main/docs/planning/)**: 마일스톤 및 상위 로드맵.

## 2. 개발 및 표준 (Development)
*코드 작성 및 문서 관리 표준을 다룹니다.*

- **[Documentation Governance](./index.md)**: 문서 분류 체계 (`ai-workflow/memory/` 상태 vs `docs/` 지식) 및 PR 리뷰 프로세스.
- **[Code Index](./CODE_INDEX.md)**: 코드베이스 구조 (`workflow-source/`, `workflow_kit/`, `contract_v1/`, `bootstrap_lib/`, `tools/`) 및 핵심 컴포넌트 안내.
- **[Installation & Usage Guide](./INSTALLATION_AND_USAGE.md)** (v0.5.10+ 도입, v0.15.15 기준 cross-check): 소스에서 설치해 개발/검증 환경으로 쓰는 절차. editable install, 스모크 테스트 실행, `workflow_kit` / `bootstrap_lib` 임포트, 부트스트랩, MCP 서버 (jsonrpc-bridge / stdio-sdk), 자주 만나는 문제 안내.
- **[Release Procedure](./RELEASE.md)** (v0.5.7+ 도입, v0.15.15 까지 회귀 표 확장): GitHub Releases only, PyPI 폐기. wheel 빌드/스모크/릴리스 절차 + 회귀 표.

## 3. 분석 및 계획 (Analysis & Planning)
*요구사항 분석 및 상위 수준의 로드맵을 다룹니다.*

- **[Microsoft Memora Evaluation](./architecture/MICROSOFT_MEMORA_EVALUATION.md)**: Microsoft Research `Memora` 조사와 `standard_ai_workflow` 적용 가능성 검토.
- **[ADR-005: Memora-inspired Memory Index](./architecture/ADR-005-memora-inspired-memory-index.md)** (v0.11.22 Phase 1~3d 완료): 평가 문서 결론을 정식 결정으로 — `ai-workflow/memory/active/memory_index/` 메타데이터 레이어 위에 retrieval flow 3-tuple (anchor exact → embedding/BM25 → linked expansion) 을 얹는다. canonical merge 는 기본 advisory, opt-in 으로 `merged` 활성화. 3-layer (source/state/knowledge) 분리 정합 유지. 후속: [ADR-006 retrospective](./architecture/ADR-006-memory-index-retrospective.md) (회고 본문은 v0.11.23+ 또는 30일 후 작성).
- 상위 로드맵은 [workflow-source/core/workflow_kit_roadmap.md](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/workflow_kit_roadmap.md) (12단계 + Phase 12 in_progress) 참고.

## 4. 보존 (Archive)
*오래된 단계의 결정 기록과 폐기 후보.*

- **[archive/AGENTS.md](https://github.com/ykylee/standard_ai_workflow/blob/main/docs/archive/AGENTS.md)**: Phase 6/codex 시점 결정 기록. (deprecated)
- **[archive/split_checklist.md](https://github.com/ykylee/standard_ai_workflow/blob/main/docs/archive/split_checklist.md)**: source/runtime 분리 작업 체크리스트. (deprecated)

---
*모든 신규 문서는 `docs/` 하위의 적절한 카테고리에 생성되어야 하며, PR 리뷰를 통해 승인되어야 합니다.*
