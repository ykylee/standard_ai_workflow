---
purpose_version: 2
last_purpose_review: 2026-11-21
---

# Purpose — Wiki의 Why

- 문서 목적: 이 프로젝트/저장소가 *왜* 존재하는지, 어디로 가는지 (directional intent) 를 정의한다. LLM 이 매 ingest/query 시 read 하여 source 분류 + cross-reference 방향성 결정에 사용.
- 범위: 4-element (Goals / Key Questions / Research Scope / Evolving Thesis)
- 대상 독자: AI agent (session-start / backlog-update / doc-sync), 저장소 maintainer
- 상태: draft — **2.0판** (`purpose_version: 2`, 2026-11-21 ADR-033 Accepted 때 적용 — 소유자 Q9). 개정 근거 `docs/planning/workflow-hub-requirements-2026-11.md` §17.1. 1.x 분기 브랜치는 v1 그대로 (v0.9.2 chapter 6 — purpose.md concept 흡수, 1차 출처 = llm_wiki Karpathy 패턴)
- 최종 수정일: 2026-11-21
- 관련 문서: [PROJECT_PROFILE.md](./PROJECT_PROFILE.md) (프로젝트 메타), [PURPOSE 운영 spec](../../workflow-source/core/llm_wiki_concept_purpose_spec.md)
- 1차 출처: Karpathy `llm-wiki.md` + llm_wiki (nashsu) README §"Purpose.md — The Wiki's Soul"

## 1. Goals

이 프로젝트가 도달하려는 목표. 정량적/질적 모두 OK. LLM 이 매 ingest/query 시 read 하여 source-page 분류 + cross-reference 의 *방향성* 결정에 사용.

- **G1**: 여러 프로젝트에서 공통으로 사용할 수 있는 표준 AI 협업 워크플로우를 **허브**로 제공한다 — 작업 환경은 kit 을 깔지 않고 허브 주소 하나로 참여하고, kit 은 허브 서버 안에서 돈다 (H2 · H4). 독립 패키지 형태는 1.x 줄로 유지보수한다
- **G2**: skill / MCP / agent 구현 기준을 *프로젝트별 차이* 와 *공통 표준* 으로 분리하여 *재현 가능* 한 운영 보장
- **G3**: 1.x 공개 API(stable_guarantee 25 항목)는 2.0 에서도 지움 없이 이어지고 (R0.2), **1.x 줄은 2028-07-20 까지 결함 수리**로 보장 기간을 지킨다 (R16.3). 2.0 의 새 계약(허브 API · MCP 도구 · 생성물 형식)의 보장 기간은 2.0 stable 선언 때 정한다
- **G4**: deprecation / breaking change 가 *운영 중인 consumer* 에게 *예측 가능* 하게 전달되는 운영 약속 (1 release DeprecationWarning → 1 release removal). 같은 약속을 **허브 API · MCP 도구 이름 · 인자**에도 적용한다 — 허브가 경고를 응답에 싣고 다음 판에서 지운다. 흐름 전환(1.x → 2.0)은 1.x 마지막 minor 의 안내(R16.4)가 경고 판이다
- **G5**: 프로젝트 작업을 *로드맵 · 마일스톤 · WBS* 로 추적하고, 새 작업 축은 *SDLC 순서* (concept → requirements → design → implementation) 로 온보딩한다 (ADR-027, 2026-08-25 주 작업 축으로 확정)

## 2. Key Questions

이 저장소/프로젝트가 답하려는 핵심 질문:

- **Q1**: 어떻게 하면 *여러 프로젝트* 가 같은 워크플로우를 *각자 다른 환경* 에서 *재현 가능* 하게 적용할 수 있는가?
- **Q2**: 어떻게 하면 *AI agent* 가 *세션 단위* 로 작업을 복원하고, *handoff* 를 안정적으로 이어갈 수 있는가? — **허브와 콜사인 단위**로, 허브가 닿지 않을 때 · 컨텍스트 압축 직후에도 (R10 · R11 · R12)
- **Q3**: 어떻게 하면 *deprecation / breaking change* 가 *운영 중인 consumer* 에게 *예측 가능* 하게 전달되는가?
- **Q4**: 어떻게 하면 *skill / MCP / agent* 구현이 *공통 계약* 아래 *프로젝트별 최적화* 될 수 있는가?

## 3. Research Scope

### 포함 영역

- 공통 표준 문서 (core/global_workflow_standard 등)
- **허브 상태** (task · handoff · 이력 · 로드맵 · 공유 지침 · 위키 · memory_index) + 그 git 내보내기 (D6)
- skill / MCP / agent 설계 카탈로그 + 프로토타입
- **허브 원격 MCP + 진입 지침** — 지원 하네스 4종 Claude Code · Codex · MiniMax Code · Antigravity (R2.8). 플러그인 채널은 1.x 줄
- 허브 서버 (Python · SQLite) 와 그 운영 가이드 — 배치 자동화는 여전히 제외 (IaC)
- 1.x 유지보수 줄 (R16)
- 로드맵 · 마일스톤 · WBS 진척 관리 + SDLC 온보딩 (ADR-027)
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
- **세션 복원의 정본은 허브다** — task · handoff · 이력 · 로드맵 · 공유 지침 · 위키의 정본이 허브에 있고, git 은 그 내보내기다 (D6 · D9 · E1). `state.json` 형식의 상태 요약은 허브가 1.x 와 같은 판정 함수로 만드는 생성물이다 (R0.7 · R6.3). 1.x 줄에서는 옛 명제(workflow state docs `ai-workflow/memory/active/<branch>/` 가 세션 복원의 SSOT, 정본은 `backlog/tasks/` + `session_handoff.md`, `state.json` 은 생성물)가 그대로다
- deprecation policy 의 *1 release DeprecationWarning → 1 release removal* 은 *stable API* 의 *운영 약속* 이며, *contract test* 가 그 약속의 *자동 verify*. 허브 API · MCP 도구 계약에도 같다
- 외부 reference (Karpathy / llm_wiki / OpenCode / Aider 등) 의 *concept* 은 *우리 spec/code* 로 *재구현* (코드 차용 ❌) 이 표준 패턴
- wiki 운영 R-1~R9 cycle 의 *lifecycle 운영* (Issue 발견 → Rule 보강 → SSOT 추출 → 영향 page 식별 → Lint cycle → Memory 갱신) 은 cross-project SSOT
- 4-element purpose.md (Goals / Key Questions / Research Scope / Evolving Thesis) 는 LLM 의 *directional intent* 의 SSOT — schema (구조) 와 분리
