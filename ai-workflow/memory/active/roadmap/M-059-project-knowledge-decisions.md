---
id: M-059
title: 프로젝트 지식·결정 공유 시스템
sdlc_phase: implementation
status: in_progress
order: 59
parallel_allowed:
  - M-007
  - M-028
  - M-039
  - M-057
deliverables:
  - docs/planning/project-knowledge-decisions-concept-2026-11.md
  - docs/planning/project-knowledge-decisions-requirements-2026-11.md
  - workflow-source/core/hub_knowledge_decisions_spec.md
  - ai-workflow/wiki/decisions/
goals: [G1, G2, G4]
---

# M-059 — 프로젝트 지식·결정 공유 시스템

## 목적 및 완료 기준

프로젝트 설계 문서·위키·기술 지식과 DCR·ADR 같은 결정 기록을 허브 세션들이 찾고, 출처와 상태를 보존하며, 승인 경계를 지켜 공유하는 구조를 정의하고 구현한다. 기존 Git 문서와 ADR-001/004/033의 정본·권한 원칙을 유지한다.

## WBS

- **WBS-59.1** 기존 지식·결정 데이터와 공유 경로 조사, 개념·요구 정리 — 산출물: source-of-truth 표와 검증 가능한 요구
- **WBS-59.2** 데이터 모델·권한·동기화·DCR→ADR 수명주기 설계 및 ADR 합의 — 산출물: accepted ADR과 normatively approved Hub contract
- **WBS-59.3** Python·Go 허브의 프로젝트 지식 카탈로그, provenance 검색, DCR→ADR workflow, MCP/API/UI 구현 — 산출물: 공통 migration·API와 감사 가능한 승인 흐름
- **WBS-59.4** Python/Go parity, 권한·충돌·복구 검증과 홈랩 pilot — 산출물: 필수 회귀 게이트·운영 안내·실환경 MCP/UI 확인
