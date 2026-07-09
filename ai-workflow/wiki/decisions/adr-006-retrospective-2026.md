---
type: retrospective
status: in_progress
target_decision: adr-006-okf-compat-frontmatter
scheduled_full_review: 2026-07-16
current_age_days: 23
early_review_date: 2026-07-09
related_pages:
  - decisions/adr-006-okf-compat-frontmatter
  - concepts/okf-open-knowledge-format
  - decisions/adr-007-okf-consumer-mode
  - decisions/adr-008-in-repo-path-to-url
  - decisions/adr-009-v-t1-formal-adoption
created: 2026-07-09
updated: 2026-07-09
---

# ADR-006 Retrospective (Early Observation, 2026-07-09)

## Status

- **Early observation**, not full retrospective.
- 본문은 2026-07-09 시점의 *preliminary* 평가이며, **full retrospective 는 scheduled_full_review (2026-07-16, 채택 후 30일) 에 작성**한다.
- 본 문서는 lessons-learned template + 23일 차 관측치 + open question 만 보존.

## 1. 평가 메타

- **Decision under review**: [ADR-006](adr-006-okf-compat-frontmatter) — Wiki frontmatter 의 OKF v0.1 5-field 호환 layer 채택
- **Decided at**: 2026-06-16 (v0.7.33 release note 동시)
- **Review age**: 23 일 (전체 30 일 중 76.7%)
- **Reviewer**: ykylee (single-maintainer) + 다음 세션 AI agent
- **Cycle**: 본 retrospective 는 ADR-006 의 *first retrospective* (향후 major 변경 시 cycle 2 가능)

## 2. Decision 재확인 (snapshot)

ADR-006 의 핵심 결정 6 항목:

1. Wiki → OKF 1-way export 호환 (frontmatter bridge 5 field: `title` / `description` / `resource` / `tags` / `timestamp`).
2. 우리 wiki schema (required 4 field) 는 unchanged.
3. lint (V-1, V-4, V-R9) 는 unchanged (unknown key tolerate).
4. `workflow_kit/okf_export.py` 가 canonical producer.
5. **Import (반대 방향)** 는 범위 외.
6. `okf_version: "0.1"` in bundle root `index.md`.

## 3. 23일 차 early observation

### 3.1 잘 된 점 (Working as intended)

| 항목 | 관측 | Evidence |
|---|---|---|
| **Schema 변경 없음** | wiki 4 required field 그대로. 기존 wiki page 25건 무중단. | `ai-workflow/wiki/SCHEMA.md` (v0.7.33 이후 무변경). |
| **Export PoC 동작** | `workflow_kit/okf_export.py` 5 page bundle 생성 정상. | `docs/samples/okf-bundle-2026-06-16/` (5 page PoC sample 보존). |
| **Lint 무영향** | V-R9 가 unknown key (`title`, `description`, ...) reject 안 함. wiki linter 통과. | `tests/check_wiki_lint.py` 누적 PASS. |
| **Follow-up ADR 파이프라인** | ADR-007/008/009 가 ADR-006 의 §"Follow-up Candidates" 에서 정확히 파생. | 3 ADR 모두 2026-06-16~2026-07-09 사이 초안 → accepted. |

### 3.2 미해결 / 관측된 gap (Open issues)

| # | 항목 | Severity | 노트 |
|---|---|---|---|
| 1 | **Wiki → OKF import 미지원** | P1 | ADR-006 §"범위 외" 로 defer. ADR-007 (consumer mode) 후속. 외부 OKF bundle ingest 시 별도 helper 필요. |
| 2 | **In-repo path 의 OKF `resource` 매핑** | P2 | `last_ingested_from` 가 in-repo path 면 OKF `resource` emit 안 함. ADR-008 후속. |
| 3 | **V-T1 (title consistency) lint 미구현** | P3 | frontmatter `title` vs body H1 불일치 가능. ADR-009 후속 (v0.7.34+). |
| 4 | **Bundle sample 영구 보존** | P3 | `docs/samples/okf-bundle-2026-06-16/` 의 5 page 가 audit-trail. 추가 page 는 작성 시점 없음 (consumer 없음). |
| 5 | **Real consumer 부재** | P1 | 외부 OKF consumer 가 아직 우리 wiki 의 bundle 을 사용하지 않음. "1-way 만 보장" 의 실효성 검증 안 됨. |
| 6 | **`okf_version: "0.1"` 표기 일관성** | P3 | bundle root `index.md` frontmatter 에 stamp 되나, bundle 의 다른 page 에는 미표기. OKF spec §11 의 권고가 정확히 어디까지인지 재확인 필요 (full retrospective 에서). |

### 3.3 Side-effect 관측 (의도하지 않은 효과)

- **없음**. 본 결정은 wiki schema 변경 0, lint 변경 0 이므로 blast radius 최소.
- **긍정적 side-effect**: ADR-006 의 §"Follow-up Candidates" 구조가 *후속 ADR 의 seed* 역할 수행. 3 ADR 모두 본 section 에서 파생.

## 4. lessons-learned template (full retrospective 작성 시 채울)

본 template 은 2026-07-16 scheduled review 에서 채워진다.

### 4.1 What went well?
- (placeholder — full retrospective 에서 작성)

### 4.2 What went wrong?
- (placeholder)

### 4.3 What would we do differently?
- (placeholder)

### 4.4 Action items (carry-over to Phase 12 close / Phase 13)
- (placeholder)

### 4.5 Status of deferred items (3.2 의 6 항목)
- (placeholder — 6 항목 status 정리)

## 5. Open questions (full retrospective 에서 답할 것)

1. ADR-006 의 *현재* 사용 pattern 이 1-way export 만인 게 의도된 제약인지, 아니면 ADR-007 (consumer mode) 의 trigger 가 부족한 건지?
2. OKF v0.1 spec 의 후속 minor/patch release 가 있을 경우 (`okf_version` bump) 우리 wiki schema 변경 범위는?
3. Wiki 운영 cycle (R-1~R9) 의 어느 cycle 에서 ADR-006 follow-up 을 트리거해야 하는가?
4. 외부 OKF consumer 가 등장하면 본 ADR 을 *revisit* 해야 하는가 (status `accepted` → `superseded` 가능)?

## 6. 인용 및 후속

- Target decision: [adr-006-okf-compat-frontmatter.md](adr-006-okf-compat-frontmatter.md)
- Primary source: [concepts/okf-open-knowledge-format.md](../concepts/okf-open-knowledge-format.md) §12 gap matrix
- Follow-up chain: ADR-007 (consumer mode) / ADR-008 (in-repo path to URL) / ADR-009 (V-T1 lint)
- 본 early observation 의 audit-trail: `ai-workflow/memory/active/session_analysis_2026-07-09.md` §"P1-1"
- 본 P0-3 의 memory_index entry: [`memory_index/entries/MEM-2026-07-09-002.json`](../../memory/active/memory_index/entries/MEM-2026-07-09-002.json) (cue anchor: ADR-005)

## 다음에 읽을 문서
- [ADR-006 본문](adr-006-okf-compat-frontmatter.md)
- [concepts/okf-open-knowledge-format.md](../concepts/okf-open-knowledge-format.md)
- [adr-007-okf-consumer-mode.md](adr-007-okf-consumer-mode.md) (후속 ADR)
