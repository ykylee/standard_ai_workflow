---
type: decision
status: proposed
adr_id: ADR-007
decided_at: 2026-06-16
accepted_in: (proposed — v0.7.33+ candidate)
alternatives_considered: [full-strict-mode-only, opt-in-loose-per-page, sidecar-okf-overlay, no-formal-decision]
related_pages: [concepts/okf-open-knowledge-format, decisions/adr-006-okf-compat-frontmatter, decisions/adr-004-wiki-layer, concepts/wiki-source-rule-r9, patterns/r4-anchor-index]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-007: OKF v0.1 loose consumer mode for external bundles

## Status

**Proposed** (2026-06-16). 본 ADR 은 ADR-006 의 follow-up 후보 1 ("OKF consumer mode — `concepts/okf-open-knowledge-format.md` follow-up 3 의 후속") + `concepts/okf-open-knowledge-format.md` §12.1 의 "OKF → 우리 consumer" 갭 해소. 채택 확정 시 status 를 `accepted` 로 전환하고 v0.7.33 PATCH release note 에 등재.

## Context

ADR-006 (wiki → OKF **export**) 채택으로 우리 wiki 가 OKF spec 과 1-way 호환 producer 가 됐다. 그러나 반대 방향 — **외부 OKF bundle 을 우리 wiki 가 ingest** — 은 미지원. `concepts/okf-open-knowledge-format.md` §12.1 의 핵심 갭:

> **OKF → 우리 consumer**: 우리 R8/R9/R4 strict lint 가 OKF spec 위반 reject 가능. **loose consumer mode 별도 필요** — 우리 wiki 가 OKF consumer 역할 시 strict lint disable + unknown key / broken link / missing field tolerate 모드.

**OKF SPEC.md §9 Conformance 의 loose consumer policy (verbatim):**

> Consumers SHOULD treat all other constraints as soft guidance. In particular, consumers MUST NOT reject a bundle because of:
> - Missing optional frontmatter fields.
> - Unknown `type` values.
> - Unknown additional frontmatter keys.
> - Broken cross-links.
> - Missing `index.md` files.

이 정책은 우리 wiki 의 strict governance (R8 strict type enum, R9 archive-only source, R4 anchor structure, V-1/V-4/V-R9 lint error-on-violation) 와 **정면 충돌**.

**현재 상황 (2026-06-16):**

- ADR-006 채택 (status: proposed). wiki → OKF export 가능. 5 page PoC + 7/7 unit test PASS.
- 외부 OKF bundle → wiki import 도구 **없음**.
- 우리 wiki 의 5 lint (V-1, V-4, V-R9 등) 는 모두 strict error-on-violation. OKF spec 의 MUST NOT reject 정책과 양립 불가.

## Decision

**외부 OKF bundle ingest 시 별도 "loose consumer mode" 를 도입한다. 본 모드는 opt-in (per-`okf-bundle.yaml` 또는 CLI flag) 이며, strict wiki governance (R1~R9) 와 양립한다.**

**구체적 결정:**

1. **Mode 정의**: 2 모드 (mutually exclusive per ingest run):
   - **strict mode** (default, 기존): 모든 wiki lint (V-1, V-4, V-R9, V-T1 등) 적용. OKF spec 위반 시 reject.
   - **loose mode** (opt-in): OKF SPEC.md §9 의 5 MUST NOT reject 정책 그대로 적용. 우리 wiki 의 strict 5 lint 는 *advisory* (warn) 만 emit, *error* 로 raise 안 함.

2. **opt-in trigger** (2 가지 동시 지원):
   - **per-bundle manifest**: ingest 대상 root 에 `okf-bundle.yaml` (또는 frontmatter `okf_mode: loose` in bundle root `index.md`) 존재 시 loose mode 자동 활성
   - **CLI flag**: `workflow_kit/okf_import --bundle <path> --mode=loose` (또는 `--mode=strict` 명시). manifest 와 flag 가 충돌 시 flag 우선 (명시 우선 원칙, R-3 와 일치)

3. **mode 별 lint behavior**:

| Lint | strict mode | loose mode (OKF consumer) |
|---|---|---|
| V-1 (wiki location) | error | error (wiki location invariant — mode 무관) |
| V-4 (index structure) | error | **warn** (OKF 의 reserved `index.md` 가 우리 anchor schema 미준수 가능) |
| V-R9 (archive source) | error | **disabled** (외부 bundle 은 archive path 미사용) |
| V-T1 (title consistency, ADR-009 후보) | error | **warn** |
| OKF spec §4.1 conformance (frontmatter required `type` 등 3 hard rule) | error | **error** (3 hard rule 은 OKF spec 자체가 strict 강제, §9 의 5 MUST NOT 와 별개) |
| OKF spec §4.1 Extensions (unknown key) | error (V-R9 외) | **warn** |
| Broken cross-link | error | **warn** (MUST NOT reject) |
| Missing optional frontmatter | error (필수 field 정의 시) | **warn** |

4. **staging directory**: 외부 OKF bundle 은 직접 wiki tree 에 import 안 함. staging 디렉토리 (default: `.okf_staging/<bundle-name>/`) 에 landing 후, 운영자가 명시적 promote (`workflow_kit/okf_import --promote`) 시 wiki 로 이동. promote 전 loose mode 의 warn 만 보고 운영자가 reject/approve.

5. **R-8 freeze 영향**: loose mode 로 ingest 된 page 는 status: draft 로 시작. 운영자가 명시적으로 `status: active` 승격. ADR-004 의 freeze 규칙 그대로 적용.

6. **scope 경계**:
   - **in-scope**: 외부 OKF bundle 의 frontmatter parse + body + cross-link 검증 + wiki page 로 변환 + staging landing
   - **out-of-scope**: bundle 의 enrichment (e.g. web crawl, BQ metadata pass) — `enrichment_agent` 의 별도 ADR 후보
   - **out-of-scope**: OKF spec 의 versioning 자동 detect (ADR-006 follow-up 5 의 `okf_version` parsing) — 본 ADR 범위 외

7. **도구 surface**: `workflow_kit/okf_import.py` 신규 module (ADR-006 의 `okf_export.py` 와 짝). CLI: `python -m workflow_kit.okf_import --bundle <path> [--mode=loose|strict] [--staging <path>] [--promote] [--json]`.

## Alternatives Considered

### A. Full strict mode only (status quo + ADR-006)

- **장점**: schema 변경 없음, lint 그대로, 학습 비용 0
- **단점**: 외부 OKF bundle 의 *spec-compliant* 작성물도 우리 strict lint 가 reject (e.g. unknown `type`, broken link, missing optional). 우리 wiki 가 *closed island*. OKF spec 의 MUST NOT reject 정책 무시.
- **탈락 사유**: ADR-006 의 *export* 는 OKF spec 권장 5 field 채택으로 *consumer-friendly*. 반대 방향 (*import*) 도 같은 friendly 정신이 들어가야 symmetric. closed island 는 yklee 의 운영 헌법 ("interop prefer closed isolation") 과 어긋남.

### B. Opt-in loose per-page (frontmatter `okf_loose: true`)

- **장점**: page-level granularity. 일부 page 만 loose 가능.
- **단점**: OKF spec 의 5 MUST NOT 가 *bundle-level* invariant (전체 bundle 이 loose consumer tolerate 여야). page-level partial loose 는 spec 위반. → 본 ADR 의 *bundle-level* loose 가 spec-aligned.
- **탈락 사유**: OKF spec 의 granularity 와 mismatch. 운영자 confusion (page 별 mode 다르면 lint 결과 비결정적).

### C. Sidecar OKF overlay (`<page>.okf-original.yaml` 보존)

- **장점**: 원본 OKF frontmatter 보존. round-trip 가능.
- **단점**: 1 page = 2 file 의 fragmentation (ADR-006 Alternative C 와 동일 문제). merge conflict 2배. 우리 R2/R5 와 충돌.
- **탈락 사유**: ADR-006 의 Alternative C 와 같은 pattern. 탈락 사유 동일.

### D. No formal decision (Sisyphus ad-hoc)

- **장점**: 의사결정 비용 0
- **단점**: 향후 외부 OKF bundle ingest 시 매번 ad-hoc lint bypass. 운영자별 inconsistency.
- **탈락 사유**: 운영 헌법 ("결정은 formal ADR 로") 선호. 작은 ADR 비용 ≪ ad-hoc inconsistency 비용.

## Consequences

### Positive

1. **OKF spec symmetric 호환**: ADR-006 (export) + 본 ADR (import) = 우리 wiki ↔ OKF spec bidirectional producer + consumer.
2. **Spec-aligned governance**: OKF spec §9 의 5 MUST NOT 정책 그대로 import 측에도 적용. 우리 의 strict governance 는 *mode flag* 로 opt-out 가능 — spec 과 governance 가 *additive* 가 됨.
3. **Staging safety**: 외부 bundle 의 직접 wiki tree 진입 차단. promote 전 운영자 review 필수. R-2 batch / R-5 additive merge 와 양립.
4. **Frontmatter provenance 보존**: OKF Extensions (unknown key) 는 우리 wiki 의 *extra frontmatter key* 로 그대로 보존. ADR-006 의 export 시 `last_ingested_from` 보존과 대칭.
5. **Lint granularity**: strict vs loose 가 *per-run* 결정. 운영자가 같은 bundle 에 대해 두 mode 로 dry-run 비교 가능.
6. **PoC 경로 명확**: ADR-006 의 `workflow_kit/okf_export.py` 와 짝이 되는 `workflow_kit/okf_import.py` 가 자연스럽게 따라옴. 둘 다 `workflow_kit/` 단일 dir.

### Negative

1. **Lint 행동 모드 2개**: 향후 lint 추가 시 (e.g. V-T1) strict/loose 양쪽 behavior 정의 필요. V-T1 ADR 시 *mode matrix* 명시 의무.
2. **Staging 디렉토리 관리**: `.okf_staging/` 의 lifecycle 정의 필요. R-8 freeze 와 양립 (staging = mutable, wiki = frozen). 운영자 cleanup 부담.
3. **`okf-bundle.yaml` manifest 위조 위험**: 임의의 bundle 에 `okf_mode: loose` manifest 주입 시 우리 strict lint 우회. → 본 ADR 의 *명시 flag 우선* 원칙이 mitigation. 그러나 *silent bypass* 가능성 잔존.
4. **cross-link 검증 약화**: loose mode 에서 broken link 가 warn 만. R-7 (merge-res 깨진 wikilink) 와 충돌. → staging → promote 2-stage 로 운영자 검수 게이트 유지.
5. **OKF spec §4.1 의 3 hard rule 여전히 strict**: frontmatter parse 실패 / `type` 부재 / reserved filename 위반은 reject. 본 ADR 은 *§4.1 hard* + *§9 soft* 분리 — 운영자 학습 필요.

### Neutral

- OKF spec 의 *non-goals* (Avro / Protobuf / OpenAPI 대체) 는 ADR-007 scope 외. 본 ADR 은 OKF v0.1 *consumer* 만 다룸.
- version detection (`okf_version: "0.1"`) 은 본 ADR 범위 외. ADR-006 follow-up 5 에서 별도 처리.
- 다른 spec (Frictionless Data Package, OpenAPI) 의 consumer mode 는 별도 ADR.

## Compliance

- [SCHEMA.md](../SCHEMA.md) §5.1 R1~R9: R1~R7 unchanged, **R8/R9 는 mode-conditional**
- [concepts/okf-open-knowledge-format.md](../concepts/okf-open-knowledge-format.md) §12.1 gap 2 ("OKF → 우리 consumer"): **해소** (loose mode 도입)
- [OKF SPEC.md §9 Conformance](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): 5 MUST NOT 정책 1:1 매핑
- [OKF SPEC.md §4.1 Frontmatter](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): 3 hard rule (parseable frontmatter / non-empty `type` / reserved filename) 은 strict 유지
- [OKF SPEC.md §5.1 Cross-Linking](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): broken link MUST NOT reject → loose mode warn

## Implementation

| Item | Status | Location |
|---|---|---|
| `concepts/okf-open-knowledge-format.md` follow-up 3 | ✅ closed (2026-06-16, ADR 제안) | 본 ADR |
| `workflow_kit/okf_import.py` (PoC) | ⏳ proposed (본 ADR 채택 후) | `workflow-source/workflow_kit/okf_import.py` |
| `tests/check_okf_import.py` (mode matrix) | ⏳ proposed | `workflow-source/tests/check_okf_import.py` |
| `--mode=loose\|strict` CLI flag | ⏳ proposed | `workflow_kit.okf_import` argparse |
| `okf-bundle.yaml` / `index.md` frontmatter detect | ⏳ proposed | `workflow_kit.okf_import._detect_mode` |
| staging directory + promote 2-stage | ⏳ proposed | `workflow_kit.okf_import.promote` |
| lint behavior matrix (8 lint × 2 mode) | ⏳ proposed (본 ADR §3 참조) | 각 lint module 의 `--mode` flag 통합 |

## Follow-up Candidates (별도 ADR/turn)

1. **ADR-008**: in-repo path → 외부 URL resolve helper. ADR-006 follow-up 2.
2. **ADR-009**: V-T1 (title consistency) lint + 본 ADR 의 mode matrix 통합. ADR-006 follow-up 3.
3. **ADR-010** (조건부): OKF spec 의 *versioning* 자동 detect (`okf_version` parsing) + unknown version 시 동작 정책.
4. **`workflow_kit/okf_import.py` PoC**: ADR-006 의 export 와 짝. 외부 sample bundle (e.g. `bundles/ga4/` PoC download) 로 round-trip 검증.
5. **lint mode matrix standardization**: `workflow_kit/lint_mode.py` (or `check_wiki_*.py --mode=` flag 통합 layer) — 향후 lint 추가 시 mode 별 behavior 한 곳에서 정의.
6. **staging lifecycle**: `.okf_staging/` 의 TTL / cleanup / promote-rollback 정책 — 운영 헌법 보강 필요.
7. **v0.7.33 PATCH release note** (본 ADR 채택 시): ADR-006 + ADR-007 + 5/7/9 page PoC 등재.

## Related

- [[concepts/okf-open-knowledge-format]] — ADR 의 1차 source. §12.1 의 OKF → 우리 consumer 갭 분석.
- [[decisions/adr-006-okf-compat-frontmatter]] — export 1-way 짝. 본 ADR 과 합쳐서 wiki ↔ OKF bidirectional 호환.
- [[decisions/adr-004-wiki-layer]] — wiki layer 의 운영 헌법. 본 ADR 은 ADR-004 의 schema 위에 optional mode layer 1장 추가.
- [[concepts/wiki-source-rule-r9]] — R9 의 archive-only source 가 외부 bundle 에는 부재. loose mode 에서 V-R9 disabled 가 spec-aligned.
- [[patterns/r4-anchor-index]] — anchor 기반 index 가 OKF 의 reserved `index.md` 와 충돌. loose mode 에서 V-4 warn 처리.
- [OKF SPEC.md v0.1 §9 Conformance](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) — 5 MUST NOT 정책의 primary source.

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. `concepts/okf-open-knowledge-format.md` §12.1 gap + ADR-006 follow-up 1 기반 | Sisyphus (orchestrator) |
