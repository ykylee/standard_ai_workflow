---
type: sample
status: snapshot
okf_version: "0.1"
generated_at: 2026-06-16
generator: workflow_kit.okf_export v0.7.33+ PoC
source: ai-workflow/wiki/
related_pages: [concepts/okf-open-knowledge-format, decisions/adr-006-okf-compat-frontmatter, decisions/adr-007-okf-consumer-mode, decisions/adr-008-in-repo-path-to-url, concepts/v-t1-title-consistency-lint]
r9_skip: true
---

# OKF v0.1 Sample Bundle (2026-06-16 snapshot)

본 디렉토리는 우리 wiki (`ai-workflow/wiki/`) 의 5 page 를 **Open Knowledge Format (OKF) v0.1** spec 으로 export 한 sample bundle 입니다.

## §0 Source  {#s0-source}

- **Generator**: `workflow-source/workflow_kit/okf_export.py` (v0.7.33+ PoC)
- **Source wiki**: `ai-workflow/wiki/` (commit `149d1ac` of 2026-06-16)
- **OKF spec**: [`https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md`](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) v0.1 (Draft, 457 lines, 2026-06-12)

## §1 Contents  {#s1-contents}

```
okf-bundle-2026-06-16/
├── README.md                              # 본 파일 (sample metadata, not a wiki concept)
├── concepts/
│   ├── okf-open-knowledge-format.md       # OKF spec 정리 (19.4 KB)
│   └── wiki-source-rule-r9.md             # R9 rule
├── decisions/
│   └── adr-001-3-layer-separation.md     # ADR-001
├── entities/
│   └── workflow-kit.md                    # workflow_kit entity
└── patterns/
    └── r4-anchor-index.md                 # R4 anchor-based index pattern
```

5 pages covering 4 of our 5 wiki types (concept, decision, entity, pattern). `query` type 의 page 는 위키에 부재 (empty `queries/` directory).

## §2 OKF Spec Conformance  {#s2-conformance}

모든 exported page 가 OKF v0.1 spec 의 conformance requirements 충족:

- **§4.1 frontmatter**: 모든 page 가 `type` field (non-empty) 보유
- **§4.1 권장 field**: 5 page 모두 `title` (frontmatter 우선 or body H1 derive), 5 page 모두 `description` (body derive), 5 page 모두 `tags` (status + wiki-type derive), 5 page 모두 `timestamp` (ISO 8601)
- **§4.1 Extensions**: 모든 page 가 wiki-native field (`status`, `created`, `related_pages`, `r9_skip`, `last_ingested_from`) 를 extra key 로 보존. OKF spec §4.1 의 "consumers SHOULD NOT reject unknown keys" 준수.
- **§5.1 cross-link**: body 의 `[[wiki-link]]` 가 모두 `[text](../path.md#anchor)` (bundle-relative) 로 rewriting
- **§9 conformance**: 3 hard rule (parseable frontmatter / non-empty `type` / reserved filename 준수) 모두 충족
- **§11 versioning**: 본 README 의 frontmatter `okf_version: "0.1"` 선언

## §3 Reproduction  {#s3-reproduction}

```bash
# 1. wiki → OKF bundle export (5 page)
cd workflow-source
python3 -m workflow_kit.okf_export \
  --wiki ../ai-workflow/wiki \
  --out /tmp/okf_poc \
  --include okf-open-knowledge-format \
  --include adr-001-3-layer-separation \
  --include workflow-kit \
  --include r4-anchor-index \
  --include wiki-source-rule-r9

# 2. copy to sample dir
mkdir -p ../docs/samples/okf-bundle-2026-06-16
cp -r /tmp/okf_poc/* ../docs/samples/okf-bundle-2026-06-16/
```

## §4 Verification  {#s4-verification}

| Test | Status |
|---|---|
| `workflow-source/tests/check_okf_export.py` 7/7 PASS | ✅ |
| `workflow-source/tests/check_wiki_title_consistency.py` 7/7 PASS | ✅ |
| `workflow-source/tests/check_wiki_lint.py` V-1/V-4 PASS (49 entries) | ✅ |
| Wiki V-R9 lint for sample | ✅ (R-9 면제 — 외부 source 정의 자체) |
| OKF spec §4.1 conformance (frontmatter required `type`) | ✅ |

## §5 Consumer Compatibility  {#s5-consumer}

본 sample 은 다음의 OKF consumer 와 호환 가능 (이론):

- **OKF reference `visualize`** ([GoogleCloudPlatform/knowledge-catalog `okf/bundles/ga4/viz.html`](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/bundles/ga4/viz.html)): Cytoscape.js graph + marked.js markdown. 본 sample 의 5 page + cross-link 30+ 표시 가능
- **`workflow_kit/okf_import.py`** (ADR-007 PoC, 별도 구현): 본 sample 을 ingest 시 loose mode 의 `V-T1` warn / `V-R9` disabled / broken link warn 으로 동작

## §6 Limitations  {#s6-limitations}

- **`resource` field 부재**: 우리 wiki 의 5 page 모두 `last_ingested_from` 가 in-repo path (e.g. `workflow-source/...`) 이므로 OKF `resource` 비어있음. **ADR-008** 채택 시 in-repo path → GitHub blob URL 자동 resolve.
- **`okf_version` only in README**: bundle root 의 `index.md` 미존재. **ADR-006 follow-up 5** 에서 `index.md` 자동 emit PoC 예정.
- **Sample is snapshot**: 2026-06-16 commit 기준. wiki 의 신규 page / 수정 시 본 sample 도 re-export 필요.

## §7 Related  {#s7-related}

- [[concepts/okf-open-knowledge-format]] — OKF spec 의 우리 wiki 정리. §12 gap matrix + §13 bridge frontmatter.
- [[decisions/adr-006-okf-compat-frontmatter]] — 본 sample 의 mapping 정책. ADR-006 §3 Decision 1.
- [[decisions/adr-007-okf-consumer-mode]] — 본 sample 의 consumer 모드 정의. ADR-007 §3 mode matrix.
- [[decisions/adr-008-in-repo-path-to-url]] — `resource` URL 자동 resolve ADR. 본 sample 의 limitations §6.1.
- [[concepts/v-t1-title-consistency-lint]] — V-T1 lint 가 본 sample 의 `title` ↔ H1 일치 강제. PoC 단계.

## §8 Revision Log  {#s8-revision-log}

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초기 sample. 5 page (concept 2 + decision 1 + entity 1 + pattern 1). `workflow_kit/okf_export.py` v0.7.33+ PoC 로 export. ADR-006 채택 (proposed) + 7/7 unit test PASS + 7/7 V-T1 test PASS 기반. | Sisyphus (orchestrator) |
