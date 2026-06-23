# llm_wiki Concept — Purpose.md 흡수 Spec (v0.9.2)

- 문서 목적: Karpathy `llm-wiki.md` 패턴 + llm_wiki (nashsu) 의 *Purpose.md — The Wiki's Soul* concept 을 우리 standard_ai_workflow 의 workflow state docs layer 에 흡수하는 정공법을 정의한다.
- 범위: 1차 출처 추출, 4-element concept 정형화, 우리 흡수 위치 (PURPOSE.md 분리), LLM context read pattern, suggest-update trigger
- 대상 독자: workflow_kit consumer, 저장소 maintainer, AI workflow 설계자
- 상태: draft (cycle 7 / v0.9.2 chapter 6, v0.9.4 chapter 8 part 1, v0.9.5 chapter 9 part 2)
- 최종 수정일: 2026-06-23
- 관련 문서: [`./v0_9_0_deprecation_policy_spec.md`](./v0_9_0_deprecation_policy_spec.md), [`./workflow_kit_roadmap.md`](./workflow_kit_roadmap.md), [`./global_workflow_standard.md`](./global_workflow_standard.md), [`./v0_8_0_stable_api_spec.md`](./v0_8_0_stable_api_spec.md)
- 1차 출처:
  - Karpathy `llm-wiki.md`: <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>
  - llm_wiki (nashsu/llm_wiki) README §"Purpose.md — The Wiki's Soul"
  - llm_wiki repo: <https://github.com/nashsu/llm_wiki>

## 1. 목적

v0.9.0 spec §3 (deprecation policy) 와 v0.9.1 spec §4 (Phase 12) 의 *외부 consumer 정합* 위에서, v0.9.2 는 *내부 운영 품질* 의 *workflow state layer* 심화 — 외부 reference concept 의 흡수를 통한 directional intent 정형화.

본 spec 은 다음을 *실제 운영* 으로 가져가는지를 정의한다:

- **purpose.md concept 의 첫 흡수**: Karpathy 원본엔 없는 *llm_wiki 추가 concept* 을 우리 `ai-workflow/memory/active/` 의 workflow state layer 에 정형화
- **4-element 구조**: Goals / Key Questions / Research Scope / Evolving Thesis
- **LLM context read pattern**: session-start / backlog-update / doc-sync skill 이 PURPOSE.md 자동 read
- **Suggest-update trigger**: usage pattern 기반 LLM suggest, wiki 운영 R-1~R9 cycle 에 통합 (R-A Purpose Refresh)

## 2. 1차 출처

### 2.1 Karpathy `llm-wiki.md` (원본)

3-layer architecture (Raw → Wiki → Schema) + 3 operations (Ingest / Query / Lint). `index.md` + `log.md` + `[[wikilink]]` + Obsidian compatibility. **purpose.md 명시 ❌**. 1차 출처의 *baseline*.

### 2.2 llm_wiki README §"Purpose.md — The Wiki's Soul"

원본에 없는 *llm_wiki 추가* concept:

> "The original has Schema (how the wiki works) but no formal place for **why** the wiki exists. We added `purpose.md`: Defines goals, key questions, research scope, evolving thesis. LLM reads it during every ingest and query for context. LLM can suggest updates based on usage patterns. Different from schema — schema is structural rules, purpose is directional intent."

4-element 구조: **goals / key questions / research scope / evolving thesis**. LLM read + suggest update 두 가지 운영 메커니즘.

### 2.3 llm_wiki docs (concept 명세 보강)

`purpose.md` 와 `schema.md` 의 역할 분리:
- `schema.md` = *structural rules* (wiki 구조, page type, 운영 규칙)
- `purpose.md` = *directional intent* (왜 이 wiki 가 존재하는지, 어디로 가는지)

LLM 의 *매 ingest/query 시 context load* 와 *usage pattern 기반 suggest update* 가 두 운영 메커니즘.

## 3. Concept 정의 (4-element)

### 3.1 Goals

이 프로젝트/저장소가 도달하려는 목표. 정량적/질적 모두 OK. LLM 이 *매 ingest/query* 시 read 하여 source-page 분류 + cross-reference 의 *방향성* 결정에 사용.

### 3.2 Key Questions

이 wiki 가 답하려는 핵심 질문 3-5개. LLM 이 query 시 *answer framing* + *gaps detection* 에 사용.

### 3.3 Research Scope

- 포함 영역: wiki 가 다룰 topic 범위
- 제외 영역: 의도적으로 다루지 않을 topic (scope creep 방지)

LLM 이 ingest 시 *relevance 판단* + query 시 *scope-out 답변 회피* 에 사용.

### 3.4 Evolving Thesis

현재까지의 *working hypothesis*. "evolving" 표기로 시간에 따라 변할 수 있음을 명시. LLM 이 *새 source 의 contradiction detection* + *thesis update suggestion* 에 사용.

## 4. 우리 흡수 정공법

### 4.1 위치 결정

신규 `ai-workflow/memory/active/PURPOSE.md` 분리 (llm_wiki 정공법 그대로). `PROJECT_PROFILE.md` 와 별도 file.

근거:
- llm_wiki 정공법: `purpose.md` 와 `schema.md` 별도 file (역할 분리)
- 우리 PROJECT_PROFILE.md: 프로젝트 메타 (name / stakeholder / commands / validation / policy). *directional intent* 와 다른 역할
- 분리 시 R-cycle 운영: purpose refresh 가 PROJECT_PROFILE 변경과 독립 (관심사 분리)

### 4.2 4-element 구조 (우리 적용)

`ai-workflow/memory/active/PURPOSE.md` 의 §1~§4 section:
- §1 Goals — 저장소/프로젝트의 목표 (G1, G2, ... 형식)
- §2 Key Questions — 핵심 질문 3-5개 (Q1, Q2, ... 형식)
- §3 Research Scope — 포함/제외 영역 sub-section
- §4 Evolving Thesis — 현재 working hypothesis

frontmatter metadata (LLM-readable):
```yaml
---
purpose_version: 1
last_purpose_review: 2026-06-19
---
```

### 4.3 LLM context read pattern

session-start, backlog-update, doc-sync skill 의 *context load* 시 PURPOSE.md 자동 read. R-A follow-up 의 3 release 분할:

**v0.9.4 part 1 (본 release, chapter 8)** — `state.json.purpose_digest` 1-line 자동 생성:
- `ai-workflow/memory/active/state.json` 의 `purpose_digest` field (top-level) + `purpose_digest_rev` field (`last_purpose_review` date) 자동 생성
- `workflow_kit.common.workflow_state.refresh_workflow_state_cache` 의 output schema 에 2 field 추가
- `generate_workflow_state.py` 의 caller 자동 populate
- format: `purpose_digest` = "G1: 표준 AI 협업 워크플로우를 *독립 패키지 형태* 로 제공" (Goals §1 의 첫 번째 goal text), `purpose_digest_rev` = PURPOSE.md frontmatter 의 `last_purpose_review` date (YYYY-MM-DD)
- PURPOSE.md 부재 시 graceful skip (purpose_digest = null, purpose_digest_rev = null, *fall back* to no-digest)

**v0.9.5 part 2 (후속 release, chapter 9)** — skill context load integration:
- session-start / backlog-update / doc-sync skill 의 *context load* 시 `state.json.purpose_digest` 1-line + PURPOSE.md 본문 (≤200 token) 자동 read
- backlog-update 의 *in-scope check* 시 Research Scope 와 비교하여 *scope creep 경고*
- helper module: `workflow_kit.common.purpose_context.build_purpose_context(workspace_root, state_path)` 가 unified `purpose_context` dict 반환
- 3개 output schema (SessionStartOutput / BacklogUpdateOutput / DocSyncOutput) 의 `purpose_context` field (SessionStartPurposeContext / BacklogUpdatePurposeContext / DocSyncPurposeContext nested Pydantic model)
- `BacklogUpdateOutput.scope_creep_warnings: list[str]` 추가 — Research Scope §3 의 *제외 영역* 매칭 결과
- body excerpt max chars: 800 (≈200 token, 한국어 2-3 chars/token + 영어 4 chars/token 의 mixed content safe upper bound)
- PURPOSE.md 부재 시 graceful skip (모든 field null/empty, `scope_warnings: ["PURPOSE.md 부재 — scope check skipped"]`)
- §1 Goals 첫 번째 goal text + frontmatter `last_purpose_review` (YYYY-MM-DD) + §3 Research Scope 포함/제외 영역 — v0.9.4 builder 의 `_parse_purpose_summary` 와 동일 가정 (frontmatter 가 file 시작)

**v0.9.6 part 3 (후속 release, chapter 10)** — wiki-event-sync R-A trigger (4.4 참조)

### 4.4 Suggest-update trigger (wiki 운영 R-1~R9)

기존 R-1~R9 cycle 에 R-A 단계 통합:
- **R-A: Purpose Refresh** — 30일 안 ingest/query 분포 분석 → LLM 이 PURPOSE.md 보강 제안
- trigger: `wiki-event-sync` 의 release event 시 `last_purpose_review` 갱신 + LLM suggest prompt 생성
- LLM suggest 는 *advisory* (자동 ❌, human confirm 필요)

### 4.5 PROJECT_PROFILE.md update

`PROJECT_PROFILE.md` 에 §0 추가:
```
## 0. Purpose 참조
이 프로젝트의 *directional intent* (왜 존재하는지) 는 [`PURPOSE.md`](./PURPOSE.md) 참조. 본 문서는 프로젝트 메타 (name / stakeholder / commands) 만 다룬다.
```

## 5. Acceptance Criterion

- [ ] `ai-workflow/memory/active/PURPOSE.md` 존재, §1~§4 4-element section 모두 non-empty
- [ ] PURPOSE.md frontmatter `purpose_version: 1` + `last_purpose_review` (YYYY-MM-DD) 명시
- [ ] `PROJECT_PROFILE.md` §0 에 PURPOSE.md 참조 추가
- [ ] Goals G1+ (≥3), Key Questions Q1+ (3-5), Research Scope 포함/제외 모두 non-empty
- [ ] Evolving Thesis 에 hypothesis / 가설 명시
- [x] `state.json` 의 `purpose_digest` field 1-line summary (Goals 1-line) — follow-up (R-A 의 release event trigger) ✅ v0.9.4 part 1
- [x] session-start / backlog-update / doc-sync skill 의 context load 가 `state.json.purpose_digest` read (1 line) + PURPOSE.md 본문 (≤200 token) 자동 read — follow-up (R-A) ✅ v0.9.5 part 2
- [x] backlog-update 의 *in-scope check* 가 PURPOSE.md §3 Research Scope *제외 영역* 과 비교하여 scope creep warning emit — follow-up (R-A) ✅ v0.9.5 part 2
- [ ] wiki 운영 R-A (Purpose Refresh) trigger 가 `wiki-event-sync` 의 release event 와 hook — follow-up (R-A)
- [ ] `tests/check_purpose_concept_v0_9_2.py` 4-element + LLM-readable + structural verify 모두 PASS

## 6. Cross-reference

- v0.8.0 spec [`./v0_8_0_stable_api_spec.md`](./v0_8_0_stable_api_spec.md) — workflow state docs layer 의 SSOT
- v0.9.0 spec [`./v0_9_0_deprecation_policy_spec.md`](./v0_9_0_deprecation_policy_spec.md) — 동일 spec layer 의 chapter 1
- workflow_kit_roadmap §5.2 — Phase 12 정의
- PROJECT_PROFILE.md — 본 spec 의 §4.5 update 대상
- ai-workflow/memory/active/state.json — `purpose_digest` field 추가 대상 (follow-up) ✅ v0.9.4 part 1 (workflow_kit.common.state.builder._parse_purpose_summary + build_workflow_state_payload output schema 확장)
- workflow-source/workflow_kit/common/purpose_context.py — `build_purpose_context` helper (v0.9.5 part 2 신규)
- workflow-source/workflow_kit/common/schemas/session.py / backlog.py / doc_sync.py — `*PurposeContext` nested model + `*Output.purpose_context` field (v0.9.5 part 2)
- workflow-source/skills/{session-start,backlog-update,doc-sync}/scripts/run_*.py — context load 시 `build_purpose_context` 호출 (v0.9.5 part 2)
- workflow-source/tests/check_purpose_concept_skill_context_v0_9_5.py — skill context load 5 acceptance (v0.9.5 part 2 신규)

## 7. 1차 출처 Bundle 비율

| concept | bundle 비율 | 비고 |
|---|---|---|
| 4-element 구조 (Goals/Questions/Scope/Thesis) | 100% | 1차 출처와 동일 |
| LLM context read pattern | 80% | 우리 skill 시스템 통합, follow-up (R-A) |
| Suggest-update trigger (R-A) | 60% | R cycle 부분 통합, human confirm 필수 |
| schema/purpose 역할 분리 (별도 file) | 100% | file 분리 정공법 |
| LLM suggest update 자동화 (UI) | 0% | Tauri 한정, 우리 stack 외 |
| Multimodal image ingest | 0% | Tauri 한정 |

**전체 bundle 비율**: ~75%. v0.9.2 = spec + code + test 1 release 단위. follow-up (R-A) 는 별도 cycle.

## 8. LICENSE 안전선

1차 출처 = Karpathy gist (idea, copyright X) + llm_wiki README (설명, GPLv3 project). 본 spec 의 *컨셉/정공법* 차용은 자유. **코드 직접 차용 ❌** (GPLv3 영향 회피, 우리 저장소 LICENSE 미보유 상태). 본 spec 의 모든 code/test 는 *우리 own implementation* — Karpathy/llm_wiki 의 *concept* 만 참조, code 형식은 1차 출처와 *의도적으로 분리*.

## 9. 다음에 읽을 문서

- v0.9.0 deprecation spec: [`./v0_9_0_deprecation_policy_spec.md`](./v0_9_0_deprecation_policy_spec.md)
- v0.8.0 stable API spec: [`./v0_8_0_stable_api_spec.md`](./v0_8_0_stable_api_spec.md)
- workflow_kit_roadmap: [`./workflow_kit_roadmap.md`](./workflow_kit_roadmap.md)
- global_workflow_standard: [`./global_workflow_standard.md`](./global_workflow_standard.md)
- Karpathy llm-wiki.md: <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>
- llm_wiki: <https://github.com/nashsu/llm_wiki>

## 10. R-A follow-up cycle (v0.9.4 / v0.9.5 / v0.9.6)

R-A follow-up 은 3 release 로 분할 진행 (1 release = 1 deliverable, §3.2 의 *1 release DeprecationWarning → 1 release removal* 패턴과 정합):

| cycle | chapter | deliverable | spec layer | runtime layer |
|---|---|---|---|---|
| v0.9.4 (chapter 8) | part 1 | `state.json.purpose_digest` 1-line 자동 생성 | §4.3 part 1 | `workflow_kit.common.workflow_state.refresh_workflow_state_cache` output schema + `generate_workflow_state.py` caller |
| v0.9.5 (chapter 9) | part 2 | skill context load integration | §4.3 part 2 | `workflow_kit.common.purpose_context.build_purpose_context` helper + `SessionStartOutput` / `BacklogUpdateOutput` / `DocSyncOutput` 의 `purpose_context` field + `BacklogUpdateOutput.scope_creep_warnings` |
| v0.9.6 (chapter 10) | part 3 | wiki-event-sync R-A trigger | §4.4 | `wiki-event-sync` release event hook + 30일 ingest/query 분포 trigger + LLM suggest (advisory) |

[v0.9.4 chapter 8 = part 1 ✅ / v0.9.5 chapter 9 = part 2 ✅ / v0.9.6 chapter 10 = part 3 follow-up]
