---
type: decision
status: accepted
adr_id: ADR-011
decided_at: 2026-06-16
accepted_in: v0.7.35 (release note: workflow-source/releases/Beta-v0.7.35.md)
alternatives_considered: [no-version-detect, strict-major-match, strict-minor-match, opt-in-version, sidecar-version-manifest]
related_pages: [concepts/okf-open-knowledge-format, decisions/adr-006-okf-compat-frontmatter, decisions/adr-007-okf-consumer-mode, decisions/adr-010-v-r10-url-validity-lint, patterns/wiki-stub-emit, releases/Beta-v0.7.35]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-011: OKF v0.1 spec version auto-detect + best-effort fallback

## Status

**Accepted** (2026-06-16, v0.7.35). 2026-06-16 초안 (proposed) → 2026-06-16 v0.7.35 release note 와 동시 accepted. `_parse_okf_version` + `_check_version_compatibility` 가 `okf_import.py` 에 통합. 5 new test (12/12 PASS) — exact match / major mismatch reject / minor higher warn / missing warn / malformed.

## Context

ADR-006 (OKF 5-field bridge) 채택으로 우리 wiki 가 OKF spec 과 1-way producer 가 됐다. ADR-007 (loose consumer mode) 채택으로 1-way consumer. v0.7.34 의 follow-up 5 (bundle root `index.md` auto-emit) 로 `okf_version: "0.1"` declaration 가능.

그러나:

- **현재 `okf_import.py` 의 `ImportReport.okf_version` field 가 항상 `None`**: `import_okf_bundle` 이 `okf_version` extract 시도하지만, 그 결과는 *import 시점* 의 metadata 일 뿐 *spec version policy* 적용 안 함.
- **OKF spec §11 의 major version = breaking change 정책 미적용**: 우리 가 v0.1 consumer 지만 v0.2 bundle (hypothetical) 이 들어오면 어떻게 동작해야 하는지 미정의.
- **version detection 의 정확성**: `okf_version: "0.1"` field 가 *잘못* 명시된 경우 (typo, subversion 등) — fallback 정책 미정의.
- **backward-compatible minor bump**: OKF spec §11 의 minor version = backward-compatible addition. v0.2 (future) 가 들어와도 우리 v0.1 consumer 가 best-effort 로 동작해야.

**현재 상황 (2026-06-16):**

- v0.7.34 의 `okf_import.py` 가 `okf_version` extract *attempt* 하지만, *policy* 적용 안 함.
- `okf_export.py` 의 `generate_index_md` 가 `okf_version: "0.1"` emit (v0.7.34, follow-up 5).
- `docs/samples/okf-bundle-2026-06-16/index.md` 가 `okf_version: "0.1"` 포함 (v0.7.34 re-export).
- ADR-011 채택 안 됨 — v0.7.35+ candidate.

**왜 지금:** v0.7.34 의 `okf_import.py` 가 7/7 PASS 했지만, version detection 의 *policy* (major mismatch reject, minor mismatch best-effort) 미구현. v0.7.35 release 시 *formal adoption* 필요.

## Decision

**OKF spec version auto-detect + best-effort fallback 정책 도입. major version mismatch 시 reject, minor version mismatch 시 best-effort + warning, unknown version 시 best-effort + warning.**

**구체적 결정:**

1. **Version field location**: bundle root `index.md` frontmatter `okf_version: "X.Y"` (OKF spec §11 의 *only place* frontmatter 가 index.md 에서 허용됨). Detect 실패 시 → `None` (best-effort mode).

2. **Version policy** (OKF spec §11 의 *major = breaking*, *minor = backward-compatible* 와 정합):

| Bundle version | Our consumer version | Behavior |
|---|---|---|
| `0.1` (exact match) | 0.1 | PASS, no warning |
| `0.2`, `0.3`, ... (minor higher) | 0.1 | PASS, warning ("unknown minor version, best-effort") |
| `1.0`, `2.0`, ... (major higher) | 0.1 | REJECT ("major version mismatch: bundle is v1.x, our consumer is v0.1") |
| `0.0`, `0.0.x` (lower) | 0.1 | REJECT ("bundle is older than our consumer") |
| missing (no `okf_version` field) | any | PASS, warning ("no version declared, assuming v0.1") |
| malformed (`"v0.1"`, `"0.1.0"`, `"1.0"`, ...) | any | PASS, warning ("malformed version string, best-effort") |

3. **Severity mapping (ADR-007 §3 mode matrix)**:

| Bundle version | strict mode | loose mode |
|---|---|---|
| exact match (0.1 = 0.1) | PASS | PASS |
| minor higher (0.2 > 0.1) | WARN | WARN |
| major mismatch (1.x vs 0.x) | **ERROR** (reject) | **WARN** (best-effort continue) |
| older (0.0 < 0.1) | **ERROR** (reject) | **WARN** |
| missing | WARN | WARN |
| malformed | WARN | WARN |

4. **API** (okf_import.py enhancement):
   - `_parse_okf_version(s: str | None) -> tuple[int, int] | None` — parse "X.Y" → (X, Y)
   - `_check_version_compatibility(bundle_version: str, our_version: str, mode: str) -> VersionCheckResult` — return (status, message)
   - `ImportReport.version_check: VersionCheckResult` — field 추가
   - `ImportReport` 의 `pages_with_errors` 가 version mismatch (major) 시 +1 (strict mode)

5. **CLI output**:
   - import 시 version check 결과 표시: `bundle_version: 0.2 (warning: minor higher than our 0.1, best-effort)`
   - JSON output 에 `version_check` object include

6. **fallback policy** (5 case, version-check 의 status 별):
   - **PASS**: import 정상 진행
   - **WARN**: import 진행 + warning log
   - **ERROR** (strict mode): import 거부 (`ImportError` raise). `pages_with_errors` 0 = 0 (no page import)
   - **ERROR** (loose mode): import 진행 + warning log (best-effort)

7. **Scope 경계**:
   - **in-scope**: OKF spec §11 의 version policy (major/minor split)
   - **out-of-scope**: vendor-specific extensions (e.g. Google Cloud 의 GA4 metadata extension). ADR candidate.
   - **out-of-scope**: bundle 의 *individual page* 의 spec version. bundle-level only.

8. **도구 surface enhancement**:
   - `workflow_kit/okf_import.py` enhancement: `_parse_okf_version`, `_check_version_compatibility`, `VersionCheckResult` dataclass, `ImportReport.version_check` field
   - `tests/check_okf_import.py` enhancement: 3 new test (version parse, version check, malformed)
   - 1 new test for major mismatch reject (strict mode)

## Alternatives Considered

### A. No version detect (status quo + ADR-006)

- **장점**: 0 구현 비용. spec policy 미적용.
- **단점**: future OKF spec version bump 시 우리 consumer 의 *semantic* 의미 손실. major = breaking change 무방비.
- **탈락 사유**: 운영 헌법 ("formal version policy") 위배. ADR 의 whole point 가 *formal adoption*.

### B. Strict major match (1.x vs 0.x 모두 reject)

- **장점**: spec-aligned. breaking change 의 *zero-tolerance*.
- **단점**: minor higher (0.2 > 0.1) 도 reject. OKF spec §11 의 *backward-compatible minor* 와 양립 불가.
- **탈락 사유**: OKF spec §11 의 minor version = backward-compatible 정의. *strict* 가 spec 위반.

### C. Strict minor match (0.x 만 accept)

- **장점**: spec-aligned. minor 까지 strict → *zero-tolerance for unknown*.
- **단점**: 우리 의 *forward-compatible* 정책 (v0.1 consumer 가 v0.2 bundle 도 best-effort) 위배. OKF spec §11 의 *minor = backward-compatible* 무시.
- **탈락 사유**: spec 위반.

### D. Opt-in version (사용자 명시)

- **장점**: 운영자가 명시적으로 version policy 결정. *default* 는 opt-out.
- **단점**: 운영자 부담. silent failure (major mismatch 시 default opt-out 시 catch 못함).
- **탈락 사유**: 운영 헌법 ("decisions formal") 위배. *opt-in* 가 *ad-hoc* 와 유사.

### E. Sidecar version manifest (`okf-bundle.yaml` 에 version field)

- **장점**: bundle-root `index.md` 와 별개 위치. ADR-007 의 `okf-bundle.yaml` 와 양립.
- **단점**: OKF spec §11 의 *only place* 가 `index.md` frontmatter. sidecar 는 spec 위반.
- **탈락 사유**: spec 위반. ADR-007 의 manifest 는 *mode* (loose/strict) only, version 아님.

## Consequences

### Positive

1. **Spec-aligned governance**: OKF spec §11 의 major/minor policy 와 1:1 매핑. *formal* producer/consumer role.
2. **Forward-compatible consumer**: 우리 v0.1 consumer 가 v0.2+ bundle 도 best-effort. OKF ecosystem 의 *backward-compatible minor* 정신 보존.
3. **Breaking change 보호**: major version mismatch (1.x vs 0.x) 시 reject. 우리 wiki 의 *strict governance* 보존.
4. **Operator transparency**: import 시 version check 결과 항상 표시 (PASS/WARN/ERROR + reason). silent failure 0.
5. **ADR-007 mode matrix 완성**: 8 lint × 2 mode + 1 version check × 2 mode. 9 row canonical reference.
6. **Lint ROI 높음**: cheap to compute (string split + int compare). high signal (breaking change 즉시 catch).
7. **Future OKF ecosystem 호환**: OKF spec 의 minor bump 시 우리 consumer 자동 forward-compatible. major bump 시 manual review trigger.

### Negative

1. **CLI output 추가**: import 시 version check 결과 line 추가. → minimal UX impact.
2. **`ImportReport` 의 field 1개 추가**: backward-compatible (default `None`). 기존 caller 영향 0.
3. **strict mode 의 major mismatch 시 import 거부**: 운영자 *recovery* — bundle 의 `okf_version` field 확인 + 우리 consumer 의 spec policy 갱신. → trade-off (safety vs availability).
4. **Malformed version handling**: `"v0.1"`, `"0.1.0"` 같은 non-canonical form → best-effort + warning. 운영자 confusion 가능. → spec §11 의 *canonical form* 을 documentation 에 명시.
5. **Bundle 의 `okf_version` 누락**: warning 만. 운영자가 *version-less bundle* 도 accept 가능. → spec-aligned (no version = 0.1 가정).
6. **Online major bump 시 우리 consumer 가 0.1 고정**: 우리 의 spec version 갱신은 별도 turn. → V-R12 (semantic URL verification) 와 별개.

### Neutral

- Version check 는 *bundle-level* 만. page-level spec version 미지원.
- Vendor-specific extension (e.g. Google Cloud GA4) 의 version policy 는 별도 ADR.
- `okf_version` field 의 *semantic* 의미 (e.g. `0.1.0` vs `0.1`) — semver 호환 form 만 accept.

## Compliance

- [SCHEMA.md §5.1](../SCHEMA.md) R1~R9: R-9 면제 (외부 source 정의), R-8 (status) 와 무관
- [ADR-006 §3](../decisions/adr-006-okf-compat-frontmatter) Decision 1: `okf_version` field 가 ADR-006 의 bridge field. 본 ADR 가 그 bridge 의 *policy* 정의.
- [ADR-007 §3](../decisions/adr-007-okf-consumer-mode) mode matrix: V-R10 + V-Version row 추가. strict vs loose 의 version policy.
- [OKF SPEC.md §11](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): major = breaking, minor = backward-compatible. 본 ADR 가 1:1 매핑.
- [concepts/okf-open-knowledge-format.md §12.1 follow-up 4](../concepts/okf-open-knowledge-format.md): *okf_version parsing + unknown version handling* 해소

## Implementation

| Item | Status | Location |
|---|---|---|
| `concepts/okf-open-knowledge-format.md` follow-up 4 | ⏳ closing (본 ADR 채택 시) | 본 ADR |
| `workflow_kit/okf_import.py` enhancement | ⏳ proposed (v0.7.35 PoC) | `workflow_kit/okf_import.py` |
| `_parse_okf_version(s: str \| None) -> (int, int) \| None` | ⏳ proposed | `workflow_kit/okf_import.py` |
| `_check_version_compatibility(bundle, our, mode) -> VersionCheckResult` | ⏳ proposed | `workflow_kit/okf_import.py` |
| `VersionCheckResult` dataclass (status, message) | ⏳ proposed | `workflow_kit/okf_import.py` |
| `ImportReport.version_check: VersionCheckResult` field | ⏳ proposed | `workflow_kit/okf_import.py` |
| `tests/check_okf_import.py` enhancement | ⏳ proposed (3 new test) | `tests/check_okf_import.py` |
| `okf_export.py` `generate_index_md` 의 `okf_version` field | ✅ done (v0.7.34, follow-up 5) | `workflow_kit/okf_export.py` |
| `docs/samples/okf-bundle-2026-06-16/index.md` `okf_version: "0.1"` | ✅ done (v0.7.34) | `docs/samples/okf-bundle-2026-06-16/index.md` |

## Follow-up Candidates (별도 ADR/turn)

1. **V-Version v2 — per-page version**: bundle 의 individual page 가 *spec version* 다를 수 있는지 (e.g. 일부 page v0.1, 일부 v0.2). 본 ADR 의 bundle-level only 한계.
2. **vendor extension version policy**: Google Cloud GA4, AWS Glue, Azure Synapse 등 vendor-specific extension 의 spec version policy. 별도 ADR.
3. **V-Version + ADR-010 (V-R10 URL validity) 통합**: bundle 의 `okf_version` URL 의 validity 검증 (e.g. `https://github.com/.../blob/v0.1.0/SPEC.md` 같은 version-pinned URL).
4. **V-Version v3 — `okf_version` field 의 strict form enforcement**: spec §11 의 canonical form (X.Y) 강제. malformed 시 reject (warning → error).
5. **`okf_version` 자동 detect 의 CI integration**: GitHub Actions 의 OKF bundle import 시 version check 결과 *PR comment* 표시. ADR-007 §7 의 follow-up.
6. **V-Version + ADR-008 (path_resolver) 통합**: `path_resolver` 가 `okf_version` 의 *commit SHA* 를 GitHub URL 에 include (e.g. `blob/v0.1.0/...`).

## Related

- [[concepts/okf-open-knowledge-format]] — V-Version 의 1차 source. §12.1 follow-up 4.
- [[decisions/adr-006-okf-compat-frontmatter]] — `okf_version` field 가 ADR-006 의 bridge. 본 ADR 가 그 bridge 의 *policy* 정의.
- [[decisions/adr-007-okf-consumer-mode]] — ADR-007 mode matrix 의 V-Version row 정의. strict/loose version policy.
- [[decisions/adr-010-v-r10-url-validity-lint]] — V-R10 의 URL validity 와 V-Version 의 *semantic* URL verify. 별개 lint.
- [[patterns/wiki-stub-emit]] — wiki stub emit 시 version field 자동 populate 패턴. V-Version 과 양립.
- [OKF SPEC.md §11](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) — primary source. major/minor policy.

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. `concepts/okf-open-knowledge-format.md` §12.1 follow-up 4 + ADR-006 follow-up 5 + ADR-007 follow-up 4 기반. 6 implementation item + 6 follow-up. | Sisyphus (orchestrator) |
| 2026-06-16 | 0.2.0 | **Accepted**: status `proposed` → `accepted`. v0.7.35 release note 등재. `related_pages` 에 Beta-v0.7.35 추가. | Sisyphus (orchestrator) |
