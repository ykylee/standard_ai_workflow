---
type: decision
status: accepted
adr_id: ADR-006
decided_at: 2026-06-16
accepted_in: v0.7.33 (release note: workflow-source/releases/Beta-v0.7.33.md)
alternatives_considered: [strict-wiki-native-only, full-okf-rewrite, sidecar-bridge-file, no-formal-decision]
related_pages: [concepts/okf-open-knowledge-format, concepts/wiki-source-rule-r9, decisions/adr-004-wiki-layer, patterns/wiki-stub-emit, patterns/r4-anchor-index, decisions/adr-007-okf-consumer-mode, decisions/adr-008-in-repo-path-to-url, concepts/v-t1-title-consistency-lint, releases/Beta-v0.7.33]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-006: Wiki frontmatter 의 OKF v0.1 5-field 호환 layer 채택

## Status

**Accepted** (2026-06-16, v0.7.33). 2026-06-16 초안 (proposed) → 2026-06-16 v0.7.33 release note (`workflow-source/releases/Beta-v0.7.33.md`) 와 동시 accepted 전환. 본 ADR 의 1차 evidence: `concepts/okf-open-knowledge-format.md` (c-OKF-1 RESOLVED) 의 §12 gap 분석 + §13 bridge frontmatter sketch + `workflow_kit/okf_export.py` (PoC, 21.7 KB, 7/7 unit test PASS) + `tests/check_okf_export.py` (7/7 PASS) + `docs/samples/okf-bundle-2026-06-16/` (5 page PoC sample). ADR-007 (loose consumer mode) + ADR-008 (in-repo path resolve) + V-T1 (title consistency lint) 는 별도 proposed ADR, v0.7.34+ follow-up.

## Context

2026-06-12 Google Cloud 가 **Open Knowledge Format (OKF) v0.1** spec 을 발표했다 ([SPEC.md](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md), 457 lines). 우리 wiki schema (`ai-workflow/wiki/SCHEMA.md` R1~R9) 와 비교했을 때 양방향 갭이 관측됐다 (`concepts/okf-open-knowledge-format.md` §12 참조).

**관측된 갭 (요약):**

| 방향 | 갭 | 영향 |
|---|---|---|
| 우리 → OKF consumer | 우리 wiki 의 `type` (5 enum), `status`, `related_pages`, `last_ingested_from` 등이 OKF spec 의 free-string `type` + 선택 field 와 매핑되나, **양방향 검증 안 됨** | wiki 를 외부 OKF consumer (e.g. OKF spec 의 reference `visualize` HTML viewer) 가 못 읽음 |
| OKF → 우리 wiki consumer | 우리 의 strict 5 lint (V-1, V-4, V-R9) 가 OKF spec 위반 reject 가능 (e.g. unknown frontmatter key, broken link, missing optional) | 외부 OKF bundle 을 우리 wiki 가 import 불가 |
| **호환 layer 부재** | 위 두 방향 모두 formal decision 없음 | wiki schema 진화 vs 외부 format adopt 의 결정권이 Sisyphus/orchestrator ad-hoc 에 의존 |

**현재 상황 (2026-06-16):**

- `concepts/okf-open-knowledge-format.md` 초안 작성 (C-OKF-1 RESOLVED, primary source 확보)
- `workflow_kit/okf_export.py` PoC 구현 (wiki → OKF bundle 5 page export 검증, 7/7 unit test PASS)
- `workflow_kit/cli/doctor.py` 등 기존 OKF-비호환: 어떤 module 도 OKF `type: <string>` consume/warn/emit 하지 않음

## Decision

**우리 wiki schema 가 OKF v0.1 spec 과의 1-way 호환 (wiki → OKF export) 을 보장하도록, OKF 권장 5 field (`title` / `description` / `resource` / `tags` / `timestamp`) 를 wiki frontmatter 의 *optional bridge* 로 추가 채택한다.**

**구체적 결정:**

1. **frontmatter bridge** (wiki → OKF export 시에만 활성화):
   - `title` (optional) — body 의 H1 또는 explicit override. OKF §4.1 priority 1
   - `description` (optional) — body 의 첫 prose paragraph 또는 explicit override. OKF §4.1 priority 2
   - `resource` (optional) — URL `last_ingested_from` 자동 매핑 (in-repo path 면 보존 안 함). OKF §4.1 priority 3
   - `tags` (optional) — 우리 wiki 는 미사용. 0개여도 OK. OKF §4.1 priority 4
   - `timestamp` (optional) — `updated` 의 ISO 8601 변환 (`YYYY-MM-DD` → `YYYY-MM-DDTHH:MM:SSZ`). OKF §4.1 priority 5

2. **wiki schema 변경 (strict 부분)**: **변경 없음**. 기존 required 4 field (`type`, `status`, `last_ingested_from`, `related_pages` + `created`/`updated`) 는 그대로. OKF 5 field 는 모두 *optional*.

3. **lint 변경 (V-1, V-4, V-R9)**: **변경 없음**. OKF 5 field 미기재 시 lint fail 안 함. OKF field 기재 시 V-R9 가 unknown key 로 reject 안 함 (frontmatter 의 모든 key 는 자유 string — V-R9 는 `last_ingested_from` 의 *값* 만 검증).

4. **export helper**: `workflow_kit/okf_export.py` 가 canonical producer. CLI: `python -m workflow_kit.okf_export --wiki <path> --out <bundle>`.

5. **import (반대 방향)**: **범위 외**. OKF bundle → wiki import 는 별도 ADR 후보 (consumer mode 필요: unknown key tolerate, broken link tolerate, missing optional tolerate). 본 ADR 은 export 1-way 만 다룬다.

6. **versioning**: 우리 wiki 의 OKF 호환 선언은 `okf_version: "0.1"` 을 bundle root `index.md` frontmatter 에 emit (SPEC.md §11 권장).

## Alternatives Considered

### A. Strict wiki-native only (status quo + minor hardening)

- **장점**: schema 변경 없음, lint 그대로, 학습 비용 0
- **단점**: 외부 OKF consumer / viewer 와의 상호운용성 0. 우리 wiki 가 *closed island*.
- **탈락 사유**: OKF spec 의 loose consumer 정책 (unknown key / missing field / broken link MUST NOT reject) 이 우리 의 strict lint 와 정반대. 양립하려면 consumer mode 별도 — 이건 본 ADR 의 범위 외이나 *향후* 필요.

### B. Full OKF rewrite (wiki schema 를 OKF spec 에 1:1 정렬)

- **장점**: bidirectional 호환
- **단점**: 4 wiki-native field (`status`, `last_ingested_from`, `created`/`updated` 의 strict pair, `related_pages`) 가 OKF 의 unknown key 로 강등. 우리 의 R8/R9/R4 strict governance 와 충돌. wiki 운영 헌법 ([SCHEMA.md §5.1](../SCHEMA.md)) 전면 개편.
- **탈락 사유**: wiki 의 audit/governance 가치는 R8/R9/R4 에서 옴. OKF 가 이 governance 를 require 하지 않으므로 OKF 우선은 *wiki-as-OKF-tool* 의 over-fit. 본 ADR 은 wiki 가 *OKF 호환 export* 가능한 producer 역할만 채택.

### C. Sidecar bridge file (`<page>.okf.yaml` 별도)

- **장점**: wiki frontmatter 무변경, OKF metadata 별도 관리
- **단점**: 1 page = 2 file 의 fragmentation. lint 가 sidecar 검증해야 함 (V-1 location, V-R9 archive). R5 (additive merge) 가 더 어려워짐. merge conflict 2배.
- **탈락 사유**: 우리 R2 (page atomicity, 1 commit = 1 ingest), R5 (additive merge) 와 정면 충돌.

### D. No formal decision (Sisyphus ad-hoc)

- **장점**: 의사결정 비용 0
- **단점**: 향후 OKF 채택 강해질 때 retroactive migration 필요. wiki consumer 가 arbitrary OKF spec 변경에 매번 대응.
- **탈락 사유**: yklee 의 운영 헌법 선호 = "결정은 formal ADR 로". 본 ADR 의 작은 추가 비용 (frontmatter 5 optional field + 1 export tool) 이 *prospective* 안전성 ≫ *retrospective* 비용.

## Consequences

### Positive

1. **Interop unlock**: 우리 wiki 의 concept/decision/pattern/entity/query 가 외부 OKF consumer (`visualize` HTML viewer 등) 와 호환. export run 1회로 OKF spec 검증.
2. **Loose export safety**: OKF spec 의 MUST NOT reject 정책 (unknown key, broken link, missing optional) 이 우리 strict wiki 의 export 결과에 적용 가능 — wiki 의 lint 가 strict 이지만 OKF consumer 가 loose.
3. **Provenance 보존**: `last_ingested_from` 의 in-repo path 는 extra `last_ingested_from` key 로 보존 (OKF 가 unknown key tolerate, §4.1 Extensions). wiki 의 R9 audit 정보 손실 없음.
4. **Forward-compatible**: OKF v0.1 minor revision (backward-compatible additions) 시 wiki → export 영향 없음 (extra key 추가만).
5. **PoC 검증 완료**: `workflow_kit/okf_export.py` 5-page export + 7/7 unit test PASS. 1차 구현 위험 해소.

### Negative

1. **Schema 비대화**: 5 optional field 추가. V-1 (location), V-4 (index), V-R9 (source) lint 가 모두 `frontmatter 의 key set 을 enumerate` 하지 않으므로 영향 없음 — 그러나 *향후* field-aware lint 추가 시 5 field 등록 필요.
2. **Title/description 중복 위험**: frontmatter `title` 과 body H1 이 *동일한 정보를 다른 syntax* 로 표현. prose 도중 H1 변경 시 frontmatter 미갱신 가능. → lint 후보: V-T1 (title consistency check) — 본 ADR 범위 외.
3. **Resource URL 좁음**: `last_ingested_from` 가 in-repo path 면 OKF `resource` emit 안 함. OKF consumer 가 이 page 의 underlying asset URI 모름. → follow-up: in-repo path 를 외부 URL 로 resolve 하는 helper 검토 (별도 turn).
4. **Import 미지원**: OKF bundle → wiki import 는 본 ADR 범위 외. 외부 OKF bundle ingest 시 별도 ADR (consumer mode) 필요.
5. **Timestamp granularity**: `updated` 가 `YYYY-MM-DD` 면 ISO 8601 변환 시 `T00:00:00Z` 강제. actual edit 시각 손실. wiki 가 시간 정밀도를 가지지 않는 한 accept.

### Neutral

- `tags` field 추가되나 우리 wiki 는 사용 안 함. 0개. 향후 taxonomy 정착 시 활용 가능.
- `description` 자동 derive 가 body 첫 prose paragraph — wiki prose style 이 바뀌면 자동 description 도 바뀜. predictable but coupled.

## Compliance

- [SCHEMA.md](../SCHEMA.md) §5.1 R1~R9: 모두 unchanged
- [concepts/okf-open-knowledge-format.md](../concepts/okf-open-knowledge-format.md) §12 Gap 매트릭스: 1-way export 호환
- [OKF SPEC.md §4.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): priority order 준수 (`type → title → description → resource → tags → timestamp`)
- [OKF SPEC.md §4.1 Extensions](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): unknown key (e.g. `status`, `created`, `r9_skip`) preserve
- [OKF SPEC.md §11](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): `okf_version: "0.1"` in bundle root `index.md` frontmatter
- `workflow_kit/okf_export.py` v0.7.33+ PoC: 5 page export 검증, 7/7 unit test PASS (`tests/check_okf_export.py`)

## Implementation

| Item | Status | Location |
|---|---|---|
| `workflow_kit/okf_export.py` (PoC) | ✅ done (2026-06-16) | `workflow-source/workflow_kit/okf_export.py` |
| `tests/check_okf_export.py` (7 test) | ✅ done (2026-06-16, 7/7 PASS) | `workflow-source/tests/check_okf_export.py` |
| 5-page bundle export 검증 | ✅ done (2026-06-16) | `/tmp/okf_poc/{concepts,decisions,entities,patterns}/*.md` |
| Bridge frontmatter 5 field wiki schema 반영 | ⏳ proposed (본 ADR 채택 후) | `ai-workflow/wiki/SCHEMA.md` §2/§4 갱신 |
| `okf_version: "0.1"` in bundle root `index.md` | ⏳ proposed | `workflow_kit/okf_export.py` enhancement |
| V-T1 (title consistency) lint | ⏸️ deferred (별도 ADR) | `tests/check_wiki_title_consistency.py` |
| OKF consumer mode (import) | ⏸️ deferred (별도 ADR) | `workflow_kit/okf_import.py` |

## Follow-up Candidates (별도 ADR/turn)

1. **ADR-007**: OKF consumer mode — 우리 wiki 가 외부 OKF bundle 을 ingest 할 때 loose consumer mode (unknown key / broken link / missing field tolerate) 정의. R8/R4 와 양립.
2. **ADR-008**: in-repo path → 외부 URL resolve helper. `last_ingested_from` 이 in-repo 일 때 OKF `resource` 자동 매핑 (e.g. github.com blob URL).
3. **ADR-009**: V-T1 (title consistency) lint — frontmatter `title` vs body H1 일치 강제.
4. **v0.7.33 PATCH release note** (본 ADR 채택 시): `workflow_kit/okf_export.py` + ADR-006 + 5 page PoC run 등재.
5. **Sample OKF bundle commit** in repo: `ai-workflow/wiki/` → `docs/samples/okf-bundle-2026-06-16/` 로 5 page export 결과물 체크인 (R-2 batch 와 결합).

## Related

- [[concepts/okf-open-knowledge-format]] — ADR 의 1차 source. §12 gap matrix + §13 bridge sketch + §14 verification trail.
- [[concepts/wiki-source-rule-r9]] — R9 의 `last_ingested_from` 가 OKF 의 `resource` + `last_ingested_from` (extra) 양쪽으로 매핑.
- [[decisions/adr-004-wiki-layer]] — wiki layer 의 운영 헌법. 본 ADR 은 ADR-004 의 schema 위에 optional layer 1장 추가.
- [[patterns/wiki-stub-emit]] — wiki stub emit 패턴이 OKF 의 minimal example bundle (SPEC.md Appendix A) 과 직접 매핑 가능. 본 ADR 채택 시 wiki stub → OKF bundle 자동 emit.
- [[patterns/r4-anchor-index]] — anchor 기반 index 가 OKF 의 reserved `index.md` 의 progressive disclosure 와 패턴 유사.
- [OKF SPEC.md v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) — primary source. 457 lines, 11 sections + Appendix A.

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. `concepts/okf-open-knowledge-format.md` + `workflow_kit/okf_export.py` + 5 page PoC + 7/7 unit test PASS 기반 | Sisyphus (orchestrator) |
| 2026-06-16 | 0.2.0 | **Accepted**: status `proposed` → `accepted`. `workflow-source/releases/Beta-v0.7.33.md` 동시 release. `related_pages` 에 ADR-007/008, V-T1, Beta-v0.7.33 release note 추가. `accepted_in: v0.7.33` 명시. | Sisyphus (orchestrator) |
