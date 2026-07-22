---
type: topic
status: active
last_ingested_from: ai-workflow/memory/archive/2026-07-22/main/session_analysis_2026-07-09.md + workflow-source/workflow_kit/common/state/memory_index.py + workflow-source/workflow_kit/okf_export.py + workflow-source/workflow_kit/common/wiki_cascade.py
related_pages:
  - topics/workflow-audit-2026-07-09
  - topics/phase-13-definition-north-star
  - workflow-source/workflow_kit/common/state/memory_index.py
  - workflow-source/workflow_kit/okf_export.py
  - workflow-source/workflow_kit/common/wiki_cascade.py
created: 2026-07-09
updated: 2026-07-09
---

# Wiki ↔ Memory 양방향 Link 자동화 검토 (2026-07-09)

## TL;DR

본 토픽은 2026-07-09 audit 의 P2-2 후보 (Wiki ↔ Memory 양방향 link 수동) 를 해소하기 위한 *설계 검토*. 현 상태의 양방향 link 메커니즘을 평가하고, 3 단계 자동화 roadmap (R-A sync + R-B reverse lookup + R-C audit) 을 제안한다. memory_index 의 `mentioned_in[]` field 가 부분적 자동화의 *anchor* 역할.

## 1. 현 상태 평가 (as-is)

### 1.1 단방향 link (현재)

| 방향 | 메커니즘 | 자동 / 수동 |
|---|---|---|
| Memory → Wiki | `memory_index.entries[].mentioned_in[]` field | **수동** (entry 작성 시 명시) |
| Wiki → Memory | `wiki.*.related_pages[]` frontmatter | **수동** (wiki 작성 시 명시) |
| Memory → Source | `memory_index.entries[].source_paths[]` | **수동** (entry 작성 시) |

### 1.2 단방향의 한계

- 같은 정보 (예: ADR-005 의 wiki page path) 가 memory entry 와 wiki page 양쪽에 *중복 표기* 되어야 함.
- 한쪽만 갱신 시 다른 쪽이 stale.
- cross-link 의 *신뢰성* 검증 부재.

### 1.3 부분적 자동화 (기존 infra)

- `okf_export.py` 의 `related_pages` 자동 cross-link (wiki → OKF bundle). 단방향 export.
- ADR-005 Memory Index 가 `source_paths` / `mentioned_in` 을 통해 *memory side 만* 보강. provenance → wiki page 의 자동 link 후보.

## 2. 자동화 3 단계 (제안)

### 2.1 R-A: Memory → Wiki single-direction sync (단방향)

**목표**: memory_index entry 작성 시 `mentioned_in[]` 의 wiki page path 가 *자동으로 wiki 의 `related_pages` 에 추가* 되도록.

**메커니즘**:
1. `save_memory_entry(workspace_root, entry)` 호출 시 entry 의 `mentioned_in[]` 순회.
2. 각 path 가 `ai-workflow/wiki/**/*.md` 의 frontmatter `related_pages` 와 매치되면 *양방향 link 표시* (e.g. 메모: "이 entry 를 참조").
3. wiki page 갱신은 *제안* 만 (auto-apply 아님, dry-run).

**구현 위치**: `workflow_kit/common/state/memory_index.py` 의 `save_memory_entry` 확장 또는 신규 `bidir_sync.py`.

**acceptance**: 
- 1 release = 1 wiki page 에서 memory entry 의 mentioned_in ↔ wiki 의 related_pages 양방향 매치 100%.

### 2.2 R-B: Wiki → Memory reverse lookup (역방향)

**목표**: wiki page 의 `related_pages[]` 항목이 memory_index 의 `source_paths[]` 또는 `mentioned_in[]` 와 매치되면 *memory entry 생성 제안*.

**메커니즘**:
1. wiki page 의 `related_pages[]` 변경 (release 시 lint cycle) 시 자동 trigger.
2. memory_index 에 매칭되는 entry 가 없으면 *제안 emit* (caller 가 새 entry 생성 결정).
3. dry-run 권장.

**구현 위치**: `workflow-source/skills/doc-sync/` 의 opt-in wiring 확장 또는 신규 `wiki_memory_reverse_lookup.py`.

**acceptance**:
- 1 release = wiki 갱신 시 memory_index 신규 entry 제안 ≥ 1건 (단, *수동 confirm* 필요).

### 2.3 R-C: Bidirectional link audit (양방향 검증)

**목표**: wiki ↔ memory 양방향 link 의 *정합성* 을 smoke test 로 검증.

**메커니즘**:
1. `tests/check_bidir_link_v0_13_0.py` 신규.
2. wiki 의 `related_pages[]` ∩ memory_index 의 `mentioned_in[]` 의 *교집합* 카운트 + *비대칭* (한쪽만) 카운트.
3. 비대칭 0 건이면 PASS.

**구현 위치**: `workflow-source/tests/check_bidir_link_v0_13_0.py`.

**acceptance**:
- 1 release = 비대칭 link 0 건.

## 3. memory_index 의 `mentioned_in` field 의 anchor 역할

### 3.1 schema 검토

```python
mentioned_in: list[str] = Field(default_factory=list,
                                description="이 entry 를 참조하는 영구 문서 / wiki / ADR 경로")
```

이미 wiki path 와 ADR path 를 *모두* 포함할 수 있는 design. 본 필드는 R-A 의 *1차 anchor*.

### 3.2 활용 예 (P0-3 의 seed entry 기준)

`MEM-2026-07-09-002.json` (ADR-005 Memory Index):
```json
"mentioned_in": [
  "ai-workflow/memory/active/memory_index/README.md",
  "workflow-source/workflow_kit/common/schemas/memory_index.py"
]
```

→ R-A 가 자동으로 wiki `concepts/memory-3-state-lifecycle` 등의 `related_pages` 에 `ai-workflow/memory/active/memory_index/README.md` 추가 *제안*.

## 4. Risk / Open issues

1. **자동 갱신의 blast radius**: wiki 25 page + memory entry 7+ 의 양방향 sync. 1 cycle 내 fix 어려움. dry-run 필수.
2. **path 정규화**: in-repo path vs wiki relative path vs ADR canonical path 의 표기 차이. helper 에 정규화 layer 필요.
3. **wiki SCHEMA 변경**: 본 자동화는 wiki 의 `related_pages[]` schema 변경 0. lint 변경 0. 기존 wiki page 무영향.
4. **operational load**: 1 release = 1+ R-A 호출, 1+ R-B trigger. 측정 가능한 telemetry 필요 (Phase 13 AC2 와 정합).

## 5. 적용 일정 (제안)

| 단계 | release | acceptance |
|---|---|---|
| R-A 단방향 sync | v0.13.0 | 1 release = 1 wiki page 에서 양방향 매치 100% |
| R-B 역방향 lookup | v0.13.1 | 1 release = 신규 memory entry 제안 ≥ 1건 |
| R-C audit smoke | v0.13.2 | 비대칭 link 0 건 |

각 단계 = 1 release. Phase 13 의 sub-milestone.

## 6. 인용 및 후속

- 2026-07-09 audit: [`workflow-audit-2026-07-09.md`](workflow-audit-2026-07-09.md) §3.3 P2-2
- 본 P0-3 seed: [`../../../ai-workflow/memory/active/memory_index/README.md`](../../../ai-workflow/memory/active/memory_index/README.md)
- 본 P2-1 follow-up: [`phase-13-definition-north-star.md`](phase-13-definition-north-star.md)
- 단방향 infra: [`../../../workflow-source/workflow_kit/okf_export.py`](../../../workflow-source/workflow_kit/okf_export.py)

## 다음에 읽을 문서
- [`workflow-audit-2026-07-09.md`](workflow-audit-2026-07-09.md)
- [`phase-13-definition-north-star.md`](phase-13-definition-north-star.md)
- [`../../../workflow-source/workflow_kit/common/state/memory_index.py`](../../../workflow-source/workflow_kit/common/state/memory_index.py)
