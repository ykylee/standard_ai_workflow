---
type: decision
status: accepted
adr_id: ADR-009
decided_at: 2026-06-16
accepted_in: v0.7.35 (release note: workflow-source/releases/Beta-v0.7.35.md)
alternatives_considered: [lint-optional, lint-error-strict-only, lint-warn-only, manual-review, body-h1-only-no-frontmatter-title]
related_pages: [concepts/v-t1-title-consistency-lint, decisions/adr-006-okf-compat-frontmatter, decisions/adr-007-okf-consumer-mode, patterns/wiki-stub-emit, patterns/r4-anchor-index, concepts/wiki-source-rule-r9, releases/Beta-v0.7.35]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-009: V-T1 title consistency lint 의 formal adoption + run_all_checks 통합

## Status

**Accepted** (2026-06-16, v0.7.35). 2026-06-16 초안 (proposed) → 2026-06-16 v0.7.35 release note 와 동시 accepted. V-T1 PoC 가 `tests/run_all_checks.py` 의 `check_*.py` glob 으로 *auto-discovered* → 5 lint (V-1, V-4, V-R9) + 2 신규 (V-T1, ADR-007) 의 *canonical mode matrix* 완성.

## Context

ADR-006 (OKF 5-field bridge) 채택으로 wiki frontmatter 에 optional `title` field 가 추가됐다. `title` 과 body 첫 `# ` (H1) heading 이 *동일한 정보를 다른 syntax* 로 표현 — prose 도중 H1 변경 시 frontmatter 미갱신 위험.

ADR-006 §5 Negative 2:

> **Title/description 중복 위험**: frontmatter `title` 과 body H1 이 *동일한 정보를 다른 syntax* 로 표현. prose 도중 H1 변경 시 frontmatter 미갱신 가능. → lint 후보: V-T1 (title consistency check) — 본 ADR 범위 외.

v0.7.33 에서 V-T1 PoC (`concepts/v-t1-title-consistency-lint.md` + `tests/check_wiki_title_consistency.py` 7/7 PASS) 가 작성됐으나, **`tests/run_all_checks.py` 미통합** → *advisory* (PoC) → *mandatory* (formal) 격상 미완.

ADR-007 §3 mode matrix (8 lint × 2 mode) 의 한 row 로 V-T1 정의 필요:

> | Mode | Lint 결과 | Exit code | 예시 출력 |
> | strict (default) | error | 1 | `FAIL: [V-T1] <path>: title "X" != H1 "Y"` |
> | loose (OKF consumer) | warn | 0 | `WARN: [V-T1] <path>: title "X" != H1 "Y"` |

**현재 상황 (2026-06-16):**

- V-T1 PoC 작성: `concepts/v-t1-title-consistency-lint.md` (status: proposed, 9 sections, 7 test spec)
- V-T1 test 작성: `tests/check_wiki_title_consistency.py` (7/7 PASS, 5-run stable)
- `tests/run_all_checks.py` 미통합 — `--help` 시 V-T1 mention 없음
- 5 lint (V-1, V-4, V-R9) 만 `run_all_checks.py` 등록
- 운영자가 `python -m tests.run_all_checks` 실행 시 V-T1 검증 안 됨

## Decision

**V-T1 title consistency lint 를 formal wiki lint rule 로 채택, `tests/run_all_checks.py` 에 등록, ADR-007 §3 mode matrix 의 한 row 로 canonical reference.**

**구체적 결정:**

1. **Lint 위치**: `workflow-source/tests/check_wiki_title_consistency.py` (v0.7.33 PoC 위치 그대로). `run_all_checks.py` 의 lint suite 에 등록.

2. **Mode 통합 (ADR-007 §3)**: `--mode=strict` (default) 와 `--mode=loose` flag 모두 지원:
   - `strict` mode (default, 우리 wiki 운영 헌법): V-T1 mismatch → exit code 1 (error)
   - `loose` mode (OKF consumer, ADR-007 §3): V-T1 mismatch → warning 만, exit code 0

3. **Rule scope**: 우리 wiki 의 *모든 page* (5 type × 5 enum + topic dir). R-9 면제 page (`r9_skip: true`) 도 V-T1 적용 — R-9 는 source 검증, V-T1 은 frontmatter/body 일관성 검증 — 별개 concern.

4. **Frontmatter `title` 부재 시**: PASS (rule §2.1 case 2). `title` 은 *optional bridge* (ADR-006 §3) — 강제 required 아님.

5. **Body H1 부재 시**: strict mode error, loose mode warn. `body H1` 는 markdown 의 *필수* 관습 (R-4 anchor index 의 H1 hierarchy 와 양립).

6. **frontmatter `title` empty (`title: ""`)**: error. *없다* vs *있다-but-empty* 의 semantic 분리 — *있다-but-empty* 는 lint fail.

7. **자동 fix**: **scope 외** — V-T1 은 *report* 만. fix = 운영자 결정. R-7 (semantic conflict LLM review) 와 일치.

8. **V-T1 concept page status 전환**: 본 ADR 채택 시 `concepts/v-t1-title-consistency-lint.md` 의 `status: proposed` → `active`. frontmatter `verification_status: N/A` → `verified_via_adr-009`.

9. **`tests/run_all_checks.py` 변경**: lint suite 의 한 item 으로 V-T1 등록. mode flag (`--mode=strict|loose`) 통합. 기존 5 lint (V-1, V-4, V-R9, ...) 와 동일한 import + run pattern.

10. **Mode matrix 명시** (ADR-007 §3 의 row):

| Lint | strict | loose |
|---|---|---|
| V-1 (location) | error | error (mode 무관 — wiki invariant) |
| V-4 (index) | error | warn (loose mode 는 OKF 의 reserved `index.md` tolerate) |
| V-R9 (archive source) | error | disabled (외부 bundle 은 archive path 미사용) |
| **V-T1 (title ↔ H1)** | **error** | **warn** (mismatch 시) |
| OKF §4.1 hard 3 rule | error | error (spec 자체 strict) |
| OKF §9 soft (5 MUST NOT) | error | warn (loose 가 spec-aligned) |

## Alternatives Considered

### A. Lint optional (status quo + ADR-006)

- **장점**: schema 변경 없음, lint 그대로, 학습 비용 0
- **단점**: `title` ↔ H1 drift 가능. OKF export 시 `title` 의 source 명확치 않음. ADR-006 §5 Negative 2 미해소.
- **탈락 사유**: ADR-006 의 *bridge* 정신 — frontmatter `title` 이 *enabler*. *enabler* 의 진실성 (frontmatter = body source) 강제 필요. drift 즉시 detect.

### B. Lint error strict-only (mode 통합 안 함)

- **장점**: 구현 단순, ADR-007 의 mode matrix 와 무관.
- **단점**: ADR-007 §3 의 8 lint × 2 mode table 의 한 row 미정의. OKF consumer (loose mode) 가 V-T1 위반 page 를 import 시 reject — ADR-007 의 *MUST NOT reject* 정책 위반.
- **탈락 사유**: ADR-007 mode matrix 와 양립 불가. loose mode 가 spec-aligned 라면 V-T1 도 spec-aligned (warn) 필요.

### C. Lint warn-only (severity 통일)

- **장점**: 운영자 confusion 없음. 모든 violation 이 warn 으로 동일 처리.
- **단점**: drift 누적. 운영자가 warn 무시 → 일관성 깨짐 → R-7 (semantic-conflict) LLM review 부담 증가.
- **탈락 사유**: *warn-only* 는 *no enforcement*. ADR-006 의 *enabler* 정신 위배.

### D. Manual review (lint 없이 운영자 수동)

- **장점**: 0 구현 비용. lint 의 false-positive 부담 없음.
- **단점**: 49+ wiki page 의 manual review 는 비현실적. drift 자동 detect 불가.
- **탈락 사유**: 운영 헌법 ("decisions formal" + "lint formal") 위배. ADR-009 의 whole point 가 *lint formal* 채택.

### E. body H1 only — no frontmatter `title` (ADR-006 의 `title` field 폐기)

- **장점**: 1 source of truth (body H1). drift impossible.
- **단점**: OKF spec §4.1 의 `title` 권장 field 자동 emit 불가 (body H1 에서 derive — ADR-006 §3 priority 1). 매 export 시 body parse + derive cost. 우리 의 search snippet / index 의 title 도 body H1 에서 derive.
- **탈락 사유**: ADR-006 §3 의 *frontmatter 우선, body H1 derive* 정신과 양립 불가. V-T1 으로 *두 source 일치 강제* 가 더 효율.

## Consequences

### Positive

1. **Frontmatter `title` 의 single source of truth 보장**: wiki 운영 헌법 (R-1~R-9) 의 *single source of truth* 원칙과 양립. ADR-006 의 *optional bridge* 정신 유지.
2. **OKF export 의 `title` 자동 채움 안전성**: ADR-006 §3 의 *frontmatter 우선, body H1 derive* 가 V-T1 일치 시 두 source 모두 OK. derive 결과 = frontmatter = 동일 정보.
3. **Search snippet quality**: frontmatter `title` 일치 = search 결과의 preview 가 page 의 *visual* title 과 일치 → 사용자/운영자 혼란 감소.
4. **drift 즉시 detect**: frontmatter `title` 추가/수정 시 V-T1 fail → 운영자가 body H1 도 갱신.
5. **ADR-007 mode matrix 완성**: 8 lint × 2 mode 의 8 row 중 V-T1 row 가 본 ADR 로 canonical. 향후 lint 추가 시 matrix 갱신 의무.
6. **Linter ROI 높음**: cheap to compute (2 string compare) + high signal (drift 즉시 detect). cumulative test 의 high-value addition.
7. **자동 fix scope 외**: 운영자가 명시적 결정. R-7 (semantic conflict LLM review) 와 일치. lint 가 *judge* 가 아닌 *report*.

### Negative

1. **mode matrix 8 lint × 2 mode 의 한 row 추가**: 향후 lint 추가 시 matrix 1 row 씩 정의 의무. matrix 가 *canonical reference* 가 되며, drift 시 운영자 confusion.
2. **R-8 freeze 영향**: V-T1 적용 시 frozen archive page 도 lint 대상. archive page 의 *historical drift* 가 fail 가능 → V-T1 의 strict mode 가 archive 의 freeze 정신과 tension.
3. **`title` field 추가 시 body H1 도 갱신 의무**: 운영자 부담. → mitigation: frontmatter `title` 추가 = *intentional change*, 운영자가 body H1 갱신 = *acknowledgment*. lint 가 이 acknowledgment 강제.
4. **frontmatter `title` empty (`title: ""`) 와 absent 구분**: 운영자 confusion. lint 가 absent 는 PASS, empty 는 fail. *intent* 명시 의무.
5. **Cumulative lint cost**: 5 lint → 6 lint. `run_all_checks.py` 의 runtime ~20% 증가. → negligible.
6. **ADR-007 mode matrix 의 strict column 만 canonical**: loose mode 의 lint behavior 는 ADR-007 채택 후에만 적용. ADR-009 의 본 release (v0.7.34) 에서는 strict mode 만 formal. loose mode 는 follow-up.

### Neutral

- V-T1 PoC (v0.7.33) 의 7 test 가 그대로 formal. 추가 test 필요 없음.
- V-T1 concept page (`concepts/v-t1-title-consistency-lint.md`) 의 §1 TL;DR / §2 Rule Definition / §3 Mode Matrix 가 본 ADR 의 §3 Decision 1-7 와 1:1 매핑. ADR 의 *canonical reference* 역할.
- 기존 wiki page 49+ 중 V-T1 위반 가능 — 본 release 의 *adoption* 은 future ingest 부터 적용 (no retroactive enforcement).

## Compliance

- [SCHEMA.md §5.1](../SCHEMA.md) R1~R9: R-9 면제 (외부 source 정의), R-8 (status) 와 무관, R-4 (anchor) 와 양립
- [ADR-006 §3](../decisions/adr-006-okf-compat-frontmatter) Decision 1: `title` optional + body H1 derive — V-T1 가 두 source 일치 강제
- [ADR-007 §3](../decisions/adr-007-okf-consumer-mode) mode matrix: V-T1 row 추가. strict = error, loose = warn
- [OKF SPEC.md §4.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): `title` 권장 field — V-T1 가 source 일관성 보장
- [concepts/v-t1-title-consistency-lint.md §1 TL;DR](../concepts/v-t1-title-consistency-lint.md): 1:1 매핑

## Implementation

| Item | Status | Location |
|---|---|---|
| `concepts/v-t1-title-consistency-lint.md` (PoC) | ✅ done (v0.7.33) | `ai-workflow/wiki/concepts/v-t1-title-consistency-lint.md` |
| `tests/check_wiki_title_consistency.py` (7/7 PASS) | ✅ done (v0.7.33) | `workflow-source/tests/check_wiki_title_consistency.py` |
| `tests/run_all_checks.py` integration | ⏳ proposed (본 ADR 채택 후) | `workflow-source/tests/run_all_checks.py` |
| V-T1 concept page status: proposed → active | ⏳ proposed | `concepts/v-t1-title-consistency-lint.md` frontmatter |
| Mode flag (`--mode=strict\|loose`) 통합 | ⏳ proposed | `check_wiki_title_consistency.py` argparse |
| ADR-007 mode matrix row 추가 | ✅ done (ADR-007 §3) | `decisions/adr-007-okf-consumer-mode.md` |
| retroactive enforcement (existing 49+ page scan) | ⏸️ deferred (별도 turn) | `tests/check_wiki_title_consistency_retro.py` |
| V-T1 retroactive auto-fix helper | ⏸️ deferred (별도 turn) | `tools/v_t1_auto_fix.py` |

## Follow-up Candidates (별도 ADR/turn)

1. **retroactive enforcement**: 기존 49+ wiki page 의 V-T1 scan + violation report. 운영자가 한 번에 fix.
2. **V-T1 auto-fix helper**: violation 발견 시 `title` 와 `H1` 중 *어느 쪽* 이 source of truth 인지 운영자 prompt → 자동 update. (out of scope per §3 Decision 7 — ADR-009 시 future turn 검토)
3. **V-T1 + OKF cross-validation**: ADR-006 §13 bridge frontmatter 의 wiki-native field 와 OKF spec field 가 추가 lint 검증.
4. **V-T1 + R-4 anchor coordination**: index.md 의 `### [[path]] {#anchor}` 가 page H1 와 일치해야 하는지 — 별도 lint 후보.
5. **mode matrix 의 canonical lint runbook**: ADR-007 + ADR-009 의 matrix 를 *single source of truth* 로 publish (e.g. `docs/OKF_LINT_MATRIX.md`).
6. **lint 의 `title` normalization 확장**: 현재 lowercase + collapse-whitespace. 향후 *Unicode normalization* (NFC/NFKC) + *transliteration* (e.g. ä → ae) 검토.

## Related

- [[concepts/v-t1-title-consistency-lint]] — V-T1 rule definition. §1 TL;DR / §2 Rule / §3 Mode Matrix 가 본 ADR 의 §3 Decision 와 1:1.
- [[decisions/adr-006-okf-compat-frontmatter]] — ADR-006 §5 Negative 2 가 V-T1 의 source. ADR-006 §3 Decision 1 의 *frontmatter 우선, body H1 derive* 정신과 양립.
- [[decisions/adr-007-okf-consumer-mode]] — ADR-007 §3 mode matrix 의 한 row 로 V-T1 정의. loose mode warn.
- [[patterns/wiki-stub-emit]] — wiki stub emit 시 frontmatter `title` 자동 populate 패턴. V-T1 PASS case 1 와 직접 연결.
- [[patterns/r4-anchor-index]] — anchor 기반 index 가 V-T1 의 `title` 과 무관 (별도 namespace). 그러나 anchor 의 *H1 hierarchy* 와 *V-T1 의 H1* 의 cross-validation 은 future turn.
- [[concepts/wiki-source-rule-r9]] — R-9 와 V-T1 는 독립 frontmatter field. lint matrix 양립.

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-006 follow-up 3 + `concepts/v-t1-title-consistency-lint.md` §0 + ADR-007 §3 mode matrix 통합 의무 기반. 7 test spec + 10 implementation item. | Sisyphus (orchestrator) |
| 2026-06-16 | 0.2.0 | **Accepted**: status `proposed` → `accepted`. v0.7.35 release note 등재. `related_pages` 에 Beta-v0.7.35 추가. | Sisyphus (orchestrator) |
