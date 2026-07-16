---
type: retrospective
status: accepted
target_decision: adr-006-okf-compat-frontmatter
scheduled_full_review: 2026-07-16
adopted_at: 2026-07-16
next_review: 2026-08-15
related_pages:
  - decisions/adr-006-okf-compat-frontmatter
  - concepts/okf-open-knowledge-format
  - decisions/adr-007-okf-consumer-mode
  - decisions/adr-008-in-repo-path-to-url
  - decisions/adr-009-v-t1-formal-adoption
created: 2026-07-09
updated: 2026-07-16
---

# ADR-006 Retrospective (Full Review, 2026-07-16)

## Status

- **Status**: accepted (full retrospective).
- **Decision under review**: [ADR-006](adr-006-okf-compat-frontmatter.md) — Wiki frontmatter 의 OKF v0.1 5-field 호환 layer 채택.
- **Decided at**: 2026-06-16 (v0.7.33 release note 동시).
- **Review age**: 30 일 (full cycle close).
- **Reviewer**: ykylee (single-maintainer) + 본 세션 AI agent.
- **Cycle**: 본 retrospective 는 ADR-006 의 *first retrospective* (cycle 1). next_review = 2026-08-15 (cycle 2, 채택 후 30 일 = 2026-08-15 예정).
- **Outcome**: ✅ **decisions accepted** — ADR-006 의 6 항목 결정 그대로 유지. follow-up ADR (007/008/009) 의 status 도 동시 추적.

## 1. 평가 메타 (Updated)

| 항목 | 값 |
|---|---|
| Decision under review | ADR-006 |
| Age (days) | 30 |
| Reviewer | ykylee + AI agent |
| Cycle | 1 (first retrospective) |
| Status (before / after) | in_progress / **accepted** |
| Next review | 2026-08-15 |

## 2. Decision 재확인 (snapshot)

ADR-006 의 6 핵심 결정 (snapshot, 2026-06-16 채택 시점과 동일):

1. Wiki → OKF **1-way export** 호환 (frontmatter bridge 5 field: `title` / `description` / `resource` / `tags` / `timestamp`).
2. 우리 wiki schema (required 4 field) 는 **unchanged**.
3. lint (V-1, V-4, V-R9) 는 **unchanged** (unknown key tolerate).
4. `workflow_kit/okf_export.py` 가 **canonical producer**.
5. **Import (반대 방향)** 는 scope 외.
6. `okf_version: "0.1"` in bundle root `index.md`.

## 3. 30 일 차 관측 (2026-06-16 → 2026-07-16)

### 3.1 잘 된 점 (What went well?)

| 항목 | 관측 | Evidence |
|---|---|---|
| **Schema 변경 zero** | wiki 4 required field 그대로 유지. 기존 wiki page 25+건 무중단 (28 concept + 25 decision + 13 entity v0.13.0 dashboard snapshot 기준). | `ai-workflow/wiki/SCHEMA.md` 무변경. |
| **Export PoC 동작** | `workflow_kit/okf_export.py` 5 page bundle 생성 정상. | `docs/samples/okf-bundle-2026-06-16/` PoC sample 보존. |
| **Lint 무영향** | V-R9 가 unknown key (`title`/`description`/...) reject 안 함. wiki linter 무중단 통과. | `tests/check_wiki_source_rule.py` 누적 PASS. |
| **Follow-up ADR 파이프라인** | ADR-006 의 §"Follow-up Candidates" 3 항목이 ADR-007/008/009 로 정확히 파생. seed ADR 의 role 모델 검증. | 3 ADR 모두 2026-06-16~2026-07-09 사이 초안 → accepted. |
| **R-A wiki-event-sync 통합** | v0.9.6 follow-up part 3 (R-A trigger) 가 ADR-006 의 bridge 5 field 의 wiki → OKF 양방향 reference 의 SSOT 성립. | `workflow-source/.../wiki_emit.py` 의 `emit_wiki_l2_body` 가 wiki page body emit 시 okf bridge 자동 적용. |
| **ADR-005 memory_index 와 호환** | ADR-006 의 OKF 5 field 가 ADR-005 의 memory_entry cue_anchor 와 직교성 유지 (OKF consumer 가 memory_index 의 JSON 을 ingest 해도 schema 충돌 0). | `memory_index/entries/MEM-*.json` 의 cue_anchors 가 ADR-006 의 OKF resource field 와 1:1 매핑 가능. |
| **Phase 14 append-only layout 정합** | 신규 layout 의 wiki/topics/* 35+ page 가 OKF bridge 5 field 그대로 유지. v0.14.0 layout 분할 시 bridge 손상 0. | wiki 35 file 모두 bridge 정합. |

### 3.2 미해결 / 보류 (Open issues status)

| # | 항목 | Severity | Status (early observation) | Current status (full review) |
|---|---|---|---|---|
| 1 | Wiki → OKF import 미지원 | P1 | ADR-007 후속 deferred | **ADR-007 accepted (2026-07-09)** — consumer mode 별도 helper 추가, ADR-006 의 1-way 제약 그대로 유지. *Intentional separation* — 이 자체가 ADR-006 의 defer 결정의 정합. |
| 2 | In-repo path 의 OKF `resource` 매핑 | P2 | ADR-008 후속 deferred | **ADR-008 accepted (2026-07-09)** — in-repo path → URL 변환 명세. wiki side 에서 처리, OKF schema 변경 0. *Closed*. |
| 3 | V-T1 (title consistency) lint 미구현 | P3 | ADR-009 후속 deferred | **ADR-009 accepted (2026-07-09)** — formal adoption. Wiki linter 의 V-T1 case 추가 구현. *Closed*. |
| 4 | Bundle sample 영구 보존 | P3 | 5 page PoC sample 보존 | **그대로 보존** — 추가 page consumer 부재. *Accepted as-is*. |
| 5 | Real consumer 부재 | P1 | 외부 OKF consumer 부재 | **현 status**: 외부 consumer 아직 없음. *Observation*. ADR-007 의 consumer mode 가 그 trigger 가 되어야 하나, **우리 wiki 의 consumer 가 자기 자신** (memora-inspired memory_index 가 ADR-005 + ADR-006 bridge 정합). 즉 *internal consumer* 는 존재. |
| 6 | `okf_version: "0.1"` 표기 일관성 | P3 | bundle root 에만 stamp, 다른 page 미표기 | **그대로**: bundle root `index.md` 의 단일 표기가 OKF spec §11 의 권고. 다른 page 의 표기는 spec violation 아님. *Accepted as-is*. |

### 3.3 Side-effect 관측 (What surprised us?)

- **의도하지 않은 긍정적 side-effect**: ADR-006 의 §"Follow-up Candidates" section 의 *구조* 가 후속 ADR 의 seed 역할 수행. 3 ADR 모두 (007/008/009) 가 본 section 에서 정확히 파생됨. **ADR 의 follow-up pattern 모델** 이 입증됨 — 향후 ADR 작성 시 본 패턴 (Decision + Follow-up Candidates 명시) 을 reference.
- **부정적 side-effect**: 없음. wiki schema 0 변경, lint 0 변경, blast radius 최소. ADR-006 자체는 "비파괴적인 채택" 의 예시로 자리잡음.
- **의도하지 않은 observation**: Phase 14 의 append-only layout (1st deprecation cycle) 가 도입되면서 OKF 5 field 가 wiki page 의 frontmatter 에서만 등장. memory_index/entries 의 JSON schema 와는 별개 (별도 namespace). **ADR-006 의 scope 외** (memory side 도 ADR-005 의 영역). Cross-cut 없음.

## 4. Lessons Learned

### 4.1 What went well?
- *Schema 변경 0* 으로 downstream risk 최소화. **결론**: 새 외부 표준 (OKF 등) 과 호환할 때 **우리 schema 변경 0 + bridge layer** 가 정공법.
- *Follow-up Candidates* section 의 도입이 후속 ADR 의 명확한 origin 제공. **결론**: ADR 본문에 *명시적 follow-up list* 포함은 knowledge graph 형성의 trigger 가 됨.
- *Phase 13 (Operational Intelligence) + Phase 14 (Append-only Layout)* 의 본 ADR-006 정공법이 그대로 적립. **결론**: 초기 ADR 의 단순한 결론이 후속 phase 의 foundation 으로 작동 — *minimal initial commit* 의 가치.

### 4.2 What went wrong?
- *Real consumer 부재 (issue #5)* 가 의도된 제약인 채로 30 일 경과. 본 ADR-006 의 *실효성 검증* 이 자기 자신 (memora memory_index) 으로만 가능. *External consumer emergence 가 ADR-006 의 진정한 validation trigger* 임. 본 cycle 1 에서는 미발생.
- *Bundle sample* (issue #4) 의 5 page 가 audit-trail 만 역할. 추가 consumer 없이는 *example expansion* 의 동기 부족.

### 4.3 What would we do differently?
- ADR 작성 시 **"real-world consumer profile"** 를 §"Use case" 에 명시. 본 ADR-006 는 "external OKF consumer 가 등장하면 trigger" 만 표기, 그 시나리오의 구체적 profile (예: "phishing_keywords 의 외부 audit, 또는 다른 wiki 의 ingest") 부재. *다음 ADR 작성 가이드* 로 §"Concrete consumer profile" 추가.
- ADR-006 의 schema 변경 0 정공법은 *영구 채택* 으로 확정. 별도 ADR 로 promote 불필요 (ADR 자체가 acceptance 의 SSOT).

## 5. Action items (next 30 일, 2026-07-16 → 2026-08-15)

본 retrospective 의 action items 는 **현실적으로 다음 phase (Phase 15+) 의 작업 candidate**:

| # | Action | Priority | Owner | Status |
|---|---|---|---|---|
| 1 | **Follow-up ADR 3 종의 status update** (007/008/009) — 본 retrospective 의 #1~#3 close-out 반영 | P1 | ykylee | ✅ DONE in §3.2 |
| 2 | **Real consumer emergence 추적** — external OKF consumer 가 등장하면 ADR-006 revisit (status `accepted` → `superseded` or `extended`) | P2 | ykylee | ⏳ next_review (2026-08-15) |
| 3 | **ADR 작성 가이드 갱신** — §"Use case" 에 *"Concrete consumer profile"* section 권장. 본 retrospective 의 lessons 의 actionable version. | P2 | ykylee + AI agent | 💡 proposed (next ADR 작성 시 적용) |
| 4 | **Bundle sample 활용** — `docs/samples/okf-bundle-2026-06-16/` 의 5 page PoC 를 README, Phase 14 release note, dashboard snapshot 등에서 reference (현재는 *static file*). | P3 | maintainer | 💡 proposed |
| 5 | **ADR-006 본문에 *사용 예시* 추가** — 채택 후 30 일 사이의 실제 사용 사례 (R-A wiki-event-sync / Phase 14 layout 정합 등) 를 ADR-006 본문에 addendum 으로 추가. | P3 | ykylee + AI agent | 💡 proposed (2026-08-15 next review 에서) |

### 5.1 Status of deferred items (4.5 의 보강)

| # | Initial severity | Current severity | Reason |
|---|---|---|---|
| 1 | P1 (import 미지원) | **drop** (ADR-007) | 의도된 separation 으로 ADR-006 의 1-way 제약 정합 |
| 2 | P2 (in-repo resource mapping) | **drop** (ADR-008) | ADR-008 accepted |
| 3 | P3 (V-T1 lint) | **drop** (ADR-009) | ADR-009 accepted |
| 4 | P3 (bundle sample 보존) | **closed** | sample audit-trail 역할 인정 |
| 5 | P1 (real consumer 부재) | **observation** | internal consumer (memory_index) 정합 |
| 6 | P3 (okf_version 일관성) | **closed** | bundle root 의 단일 표기로 OKF spec 정합 |

→ 6 deferred item 중 **5 closed / drop**, 1 **observation** 으로 유지.

## 6. Open questions (full retrospective)

| # | Question | Answer / Status |
|---|---|---|
| 1 | ADR-006 의 1-way 가 의도된 제약 vs ADR-007 trigger 부족? | **의도된 제약**. ADR-007 accepted 로 그 자체가 ADR-006 의 분리 정공법. |
| 2 | OKF spec 의 minor/patch release 시 우리 wiki schema 변경 범위? | **변경 0**. ADR-006 의 bridge layer 가 okf_version bump 을 흡수 (L4.1 의 schema 변경 0 정공법). |
| 3 | Wiki 운영 cycle 의 어느 cycle 에서 ADR-006 follow-up trigger? | **L4.1 follow-up Candidates section 의 채택 시점 = 트리거**. R-A wiki-event-sync 의 ADR cycle 통합으로 자동화 가능. |
| 4 | External consumer 등장 시 ADR-006 revisit? | **Yes, 자동**. next_review (2026-08-15) 에서 *real consumer observation* field 체크. 본 cycle 1 의 *open question* 은 cycle 2 에서 검증. |

## 7. 결론

- **ADR-006 (Wiki OKF compat frontmatter)**: ✅ **accepted**. 30 일 관측 동안 *side-effect 0*, *schema 변경 0*, *lint 변경 0* 모두 입증. bridge layer 의 정공법이 그대로 자리잡음.
- **Follow-up chain**: ADR-007/008/009 모두 accepted. 본 retrospective 의 보강으로 6 deferred item 중 5 closed.
- **Real consumer emergence**: internal consumer (memory_index) 정합. external consumer 는 *next_review (2026-08-15)* 까지 observation 유지.
- **최종 judgement**: ADR-006 은 *minimal initial commit* 의 본보기. schema 변경 0 + bridge layer + Follow-up Candidates 명시가 정공법.

## 8. 다음에 읽을 문서

- [ADR-006 본문 (decisions)](adr-006-okf-compat-frontmatter.md)
- [ADR-007 consumer mode (decisions)](adr-007-okf-consumer-mode.md)
- [ADR-008 in-repo path to URL (decisions)](adr-008-in-repo-path-to-url.md)
- [ADR-009 V-T1 formal adoption (decisions)](adr-009-v-t1-formal-adoption.md)
- [concepts/okf-open-knowledge-format.md](../concepts/okf-open-knowledge-format.md)
- [Early observation (이전 본문)](adr-006-retrospective-2026.md) — 본문 v1 (2026-07-09)
- [Next retrospective schedule (2026-08-15)](adr-006-retrospective-2026.md) — *next retrospective trigger*
- 본 retrospective 의 audit-trail: `ai-workflow/memory/release/v0.14.0/backlog/2026-07-16.md` §"ADR"
- memory_index entry: `memory_index/entries/MEM-2026-07-09-002.json` (cue anchor: ADR-005)

---

*Generated 2026-07-16 (full retrospective). Status: ✅ accepted. Next review: 2026-08-15 (cycle 2).*
