---
purpose_version: 1
last_purpose_review: 2026-06-19
---

# Purpose — Wiki의 Why

- 문서 목적: 이 프로젝트/저장소가 *왜* 존재하는지, 어디로 가는지 (directional intent) 를 정의한다. LLM 이 매 ingest/query 시 read 하여 source 분류 + cross-reference 방향성 결정에 사용.
- 범위: 4-element (Goals / Key Questions / Research Scope / Evolving Thesis)
- 대상 독자: AI agent (session-start / backlog-update / doc-sync), 저장소 maintainer
- 상태: draft (v0.9.2 chapter 6 — purpose.md concept 흡수, 1차 출처 = llm_wiki Karpathy 패턴)
- 최종 수정일: 2026-06-19
- 관련 문서: [PROJECT_PROFILE.md](./PROJECT_PROFILE.md) (프로젝트 메타), [PURPOSE 운영 spec](../../workflow-source/core/llm_wiki_concept_purpose_spec.md)
- 1차 출처: Karpathy `llm-wiki.md` + llm_wiki (nashsu) README §"Purpose.md — The Wiki's Soul"

## 1. Goals

이 프로젝트가 도달하려는 목표. 정량적/질적 모두 OK. LLM 이 매 ingest/query 시 read 하여 source-page 분류 + cross-reference 의 *방향성* 결정에 사용.

- **G1**: 여러 프로젝트에서 공통으로 사용할 수 있는 표준 AI 협업 워크플로우를 *독립 패키지 형태* 로 제공
- **G2**: skill / MCP / agent 구현 기준을 *프로젝트별 차이* 와 *공통 표준* 으로 분리하여 *재현 가능* 한 운영 보장
- **G3**: 외부 consumer 가 stable library 처럼 *신뢰* 가능하도록 SemVer 2-year guarantee (v0.8.0 → 2.0.0) 운영
- **G4**: deprecation / breaking change 가 *운영 중인 consumer* 에게 *예측 가능* 하게 전달되는 운영 약속 (1 release DeprecationWarning → 1 release removal)

## 2. Key Questions

이 저장소/프로젝트가 답하려는 핵심 질문:

- **Q1**: 어떻게 하면 *여러 프로젝트* 가 같은 워크플로우를 *각자 다른 환경* 에서 *재현 가능* 하게 적용할 수 있는가?
- **Q2**: 어떻게 하면 *AI agent* 가 *세션 단위* 로 작업을 복원하고, *handoff* 를 안정적으로 이어갈 수 있는가?
- **Q3**: 어떻게 하면 *deprecation / breaking change* 가 *운영 중인 consumer* 에게 *예측 가능* 하게 전달되는가?
- **Q4**: 어떻게 하면 *skill / MCP / agent* 구현이 *공통 계약* 아래 *프로젝트별 최적화* 될 수 있는가?

## 3. Research Scope

### 포함 영역

- 공통 표준 문서 (core/global_workflow_standard 등)
- workflow state docs (session_handoff / work_backlog / state.json)
- skill / MCP / agent 설계 카탈로그 + 프로토타입
- 하네스 배포 가이드 (Codex / OpenCode / Gemini CLI / Antigravity / MiniMax Code / pi-dev)
- deprecation policy 운영 spec
- release pipeline + state cache 운영
- 외부 reference (Karpathy / llm_wiki / OpenCode / Aider 등) 의 *concept 흡수 정공법* (코드 차용 ❌)

### 제외 영역

- 특정 도메인 (e.g. 결제 / 의료 / 금융) 의 도메인 로직
- LLM model fine-tuning / training pipeline
- 인프라 IaC (Terraform / CDK) 자동화 — 운영은 별도 가이드
- non-Python 기반 runtime (TypeScript / Rust tool) — Python 외 runtime 의 정공법은 별도 spec
- 외부 reference 의 *코드 직접 차용* — GPLv3 / 라이센스 영향 회피, concept 만 흡수

## 4. Evolving Thesis

*현재까지의 working hypothesis* (시간에 따라 변할 수 있음):

- 표준 워크플로우는 *문서 + 프로토타입 + 운영 spec* 의 3-tuple 로 표현 가능하며, *프로젝트별 차이* 는 *프로젝트 프로파일* 로 흡수
- workflow state docs (`ai-workflow/memory/active/`) 는 *세션 복원의 SSOT* 이며, `state.json` 의 *in-process cache* 가 *라이브 운영 상태* 의 mirror
- deprecation policy 의 *1 release DeprecationWarning → 1 release removal* 은 *stable API* 의 *운영 약속* 이며, *contract test* 가 그 약속의 *자동 verify*
- 외부 reference (Karpathy / llm_wiki / OpenCode / Aider 등) 의 *concept* 은 *우리 spec/code* 로 *재구현* (코드 차용 ❌) 이 표준 패턴
- wiki 운영 R-1~R9 cycle 의 *lifecycle 운영* (Issue 발견 → Rule 보강 → SSOT 추출 → 영향 page 식별 → Lint cycle → Memory 갱신) 은 cross-project SSOT
- 4-element purpose.md (Goals / Key Questions / Research Scope / Evolving Thesis) 는 LLM 의 *directional intent* 의 SSOT — schema (구조) 와 분리
