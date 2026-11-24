# 프로젝트 지식·결정 공유 시스템 — concept

- 문서 목적: 프로젝트 설계 문서·위키·기술 지식과 DCR/ADR 결정을 여러 허브 세션에서 출처와 승인 이력까지 보존하며 공유하는 개념을 정한다 (TASK-2026-11-24-main-002, M-059/WBS-59.1).
- 범위: 현행 자산과 공백, 지식 source와 Hub 공유 index의 경계, DCR→ADR 흐름, 권한·감사·검색, 전환 단계, 소유자 결정. 코드는 이 개념과 요구/ADR 합의 뒤에 시작한다.
- 대상 독자: 프로젝트 owner, maintainer, 허브 구현자
- 상태: concept 승인 (2026-11-24) — D1~D3 확정, M-059/WBS-59.3 구현 진행
- 최종 수정일: 2026-11-24
- 관련 문서: [`workflow-hub-review-2026-11.md`](./workflow-hub-review-2026-11.md), [`ADR-001`](../../ai-workflow/wiki/decisions/adr-001-3-layer-separation.md), [`ADR-004`](../../ai-workflow/wiki/decisions/adr-004-wiki-layer.md), [`ADR-033`](../../ai-workflow/wiki/decisions/adr-033-workflow-hub.md), [`hub_spec.md`](../../workflow-source/core/hub_spec.md), [`hub_knowledge_decisions_spec.md`](../../workflow-source/core/hub_knowledge_decisions_spec.md)

## 0. 한 줄 결론

허브를 프로젝트 세션이 **설계 문서·Wiki·기술 지식·결정 기록을 찾아 읽고, 검토 중인 결정을 공유하는 공통 접점**으로 만든다. 기존 문서의 정본은 명시된 source policy가 결정하며, Hub는 모든 문서를 자동으로 한 DB에 복사해 정본을 바꾸지 않는다. DCR은 변경 제안과 검토 이력을 보존하고, 승인된 human만 제안을 결정한다. 결정 결과는 ADR로 연결되고 이전 결정은 변경 이력을 잃지 않는다.

## 1. 현재 상태와 공백

| 자산/기능 | 현재 위치·기능 | 남은 공백 |
|---|---|---|
| 설계·요구·계약 문서 | `docs/planning/`, `docs/architecture/`, `workflow-source/core/`; Git 추적 | 허브 도구는 저장소 문서 전체를 한 catalog로 검색하지 않는다 |
| 프로젝트 Wiki | `ai-workflow/wiki/`; ADR-004 schema, type, relation, index, lint | 허브 Wiki 저장·ingest·list/search/get은 있지만 원격 설계 문서까지 통합한 출처/판 검색은 아니다 |
| Hub Wiki | `wiki_page`, version, source repo/SHA, ingest log, import/export; Python·Go MCP/UI 표면 | knowledge source 종류와 canonical authority를 구별하지 않는다 |
| Memory Index | `memory_entry`의 검증된 project entry 저장·조회 | 세션 기억/회고와 canonical project knowledge를 한 결과 집합에서 구분해야 한다 |
| ADR | Wiki `decisions/ADR-NNN-*.md`와 일부 `docs/architecture/ADR-*`; 상태·related/supersedes 링크 | 관계·현재 유효 결정·결정 변경 요청의 구조화된 허브 수명주기가 없다 |
| DCR | 전용 데이터 모델·정의·MCP/UI 흐름 없음 | 제안, human 검토, 결정, ADR 반영, 문서 export를 감사 가능하게 연결해야 한다 |

## 2. 설계 원칙

1. **현재 결정과 호환** — ADR-001의 Source/State/Knowledge 경계와 ADR-004의 Git 추적 Wiki를 유지한다. ADR-033의 Hub project 업무·Wiki 계약을 확장하되 기존 문서 정본을 암묵적으로 옮기지 않는다.
2. **명시적인 authority** — 각 source에는 `authority`를 선언한다. `git` source는 repository path와 commit SHA가 정본이고 Hub는 해당 SHA의 읽기 snapshot/index다. `hub` source는 Hub page/record가 정본이고 Git에는 검토 가능한 export를 제공한다.
3. **출처 우선 검색** — 검색 결과에 source 종류, canonical path/URL, revision/SHA, 상태, 갱신 시각을 반환한다. 같은 내용을 중복해도 출처를 합쳐 숨기지 않는다.
4. **DCR과 ADR을 구분** — DCR은 무엇을 왜 바꿀지 검토하는 변경 요청이다. ADR은 결정된 선택과 근거를 기록한다. DCR의 accepted 상태만으로 기존 Git ADR 본문이 조용히 수정되지 않는다.
5. **결정권 보존** — 프로젝트 콜사인은 자기 프로젝트 자료만 본다. 제안은 project writer가 할 수 있으나 DCR/ADR 수락·거절과 canonical decision promotion은 승인된 `human` owner만 한다.
6. **변경 충돌은 드러낸다** — source SHA나 record version이 바뀌었으면 stale/conflict를 반환하고 자동 merge하지 않는다. 결정 전후 본문과 event는 감사할 수 있어야 한다.
7. **Python/Go parity** — DB migration, API/MCP, authorization, search semantics, UI 동작은 두 hub가 같은 contract를 제공한다.

## 3. 제안 구조

### 3.1 지식 source catalog

각 프로젝트는 등록된 source들을 가진다. Source는 repository 전체가 아니라 명시된 범위(예: `docs/architecture/**`, `docs/planning/**`, `workflow-source/core/**`, `ai-workflow/wiki/**`)를 포함한다. Source metadata는 source ID, label, kind, authority, remote key/URL, path allowlist, indexed revision, last sync result를 보유한다.

Hub는 `git` authority source를 읽기 전용으로 snapshot/index한다. 기본 분류는 frontmatter의 `type`과 경로 규칙에서 추론하되, 분류를 추론하지 못하면 `document`로 표시한다. 기존 Hub Wiki 페이지는 현재 `wiki_page` 저장 구조를 보존하며 source policy에 따라 Wiki page 또는 Git snapshot으로 검색 결과에 노출한다. 공유 범위 기본값은 프로젝트 단위이며, cross-project 검색은 명시적 승인 없이는 제공하지 않는다.

### 3.2 통합 지식 검색

세션은 프로젝트 범위 `hub_knowledge_search(query, filters, limit)`로 Wiki, design/requirements/spec, ADR/DCR, Memory Index를 검색한다. 결과에는 `kind`, `title`, `status`, `canonical_ref`, `revision`, `authority`, `source_sha`, `updated_at`, 짧은 excerpt, relation IDs가 포함된다. `hub_knowledge_get(id, revision?)`는 검색 당시 판을 지정해 읽게 한다. DCR이 pending이거나 ADR superseded이면 상태를 결과에 표시한다.

### 3.3 DCR과 ADR 결정 흐름

```text
지식/ADR 검색 → DCR 초안 → 제안(open) → human 검토 → 수락 또는 거절
                                      │ 수락
                                      ├─ 결정 근거·범위·영향 기록
                                      ├─ 새 ADR 생성 또는 기존 ADR supersedes 링크
                                      └─ Git authority면 export 지시 → source SHA 확인 → 사용자 저장소 반영
```

- DCR은 대상 문서/ADR, 기존 revision/SHA, 요청된 변화, 이유, 영향 문서, 대안, 검증 계획, author, 상태·reviewer를 가진다.
- 상태는 최소 `draft`, `open`, `accepted`, `rejected`, `withdrawn`, `stale`을 구분한다. 수락/거절은 승인된 human만 하며 이유를 남긴다.
- DCR은 결정한 ADR과 역참조한다. accepted ADR은 `related DCR`, `supersedes`, `superseded_by` 관계를 명시한다. 이전 ADR을 삭제하거나 이력을 덮어쓰지 않는다.
- Git 정본 ADR의 본문 변경은 Hub가 직접 쓰지 않는다. 수락 결과는 source SHA를 포함하는 export/write instruction으로 내고, 저장소 변경 뒤 새로운 commit SHA를 sync한다.

### 3.4 시스템 연결 지점

| 표면 | 제공 기능 |
|---|---|
| MCP | knowledge source 등록/sync/status, 검색/get, DCR create/get/list/decide, ADR relation 및 export plan |
| Hub UI | source 상태, knowledge search/filter, 문서 provenance, DCR inbox와 diff/영향 링크, ADR relation view |
| 세션 시작 | 현재 task와 직접 연결된 DCR/ADR 및 pinned knowledge references를 짧게 제공; 전체 문서를 자동 context에 넣지 않음 |
| Git | 기존 문서 권한·PR review·이력 유지. Hub export instruction을 적용한 변경은 source SHA가 맞을 때만 반영 |
| 감사 | project event와 append-only DCR decision event에 actor, 시간, before/after revision, 이유 기록 |

## 4. 단계

1. WBS-59.1: source/authority와 DCR 용어·의도, 기존 계약 조사 및 concept/requirements 정리.
2. WBS-59.2: D1~D3 소유자 결정, data/API/security contract와 ADR 초안 확정.
3. WBS-59.3~59.4: Python·Go migration과 catalog/search, DCR/ADR lifecycle 및 export 구현.
4. WBS-59.5: UI, MCP/API parity, access control, stale/conflict, export, recovery 검증.
5. WBS-59.6: pilot 프로젝트의 docs/Wiki/ADR source를 연결하고 세션 조회를 실측.

## 5. 열린 결정

| ID | 질문 | 권고 기본값 | 선택지 |
|---|---|---|---|
| D1 | Git 문서와 Hub knowledge의 canonical authority를 어떻게 나눌까? | **hybrid — Git 설계 문서·accepted ADR은 Git 정본/projection, Hub-native Wiki·DCR은 Hub 정본** | git_projection · hybrid · hub_ssot |
| D2 | accepted DCR이 기존 ADR에 미치는 방식은? | **new_adr — 새 ADR을 만들고 대체된 ADR은 superseded로 보존** | new_adr · in_place |
| D3 | knowledge의 기본 가시 범위는? | **project_only — 등록 프로젝트의 콜사인만 접근** | project_only · hub_wide |

## 6. 제외

- Hub를 임의 Git 원격에 write/push하는 기능.
- 프로젝트 간 문서 자동 복제·권한 상속을 가정하는 federation.
- LLM이 DCR을 자동 수락하거나 accepted ADR을 자동 수정하는 동작.
- 현재 작업 memory/handoff/checkpoint를 영구 project knowledge로 자동 승격하는 동작.
