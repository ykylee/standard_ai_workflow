# ADR-005: Memora-inspired Memory Index

- 문서 목적: Microsoft Research `Memora` (2026-06-29 공개) 의 본문/검색 분리 패턴을 차용하여, `standard_ai_workflow` 의 memory layer 위에 retrieval-facing metadata layer 를 얹는 결정을 정식 기록한다.
- 범위: 메모리 엔트리 스키마, merge 규칙, retrieval flow 3-tuple, 3-layer 분리와의 경계, 단계별 활성화 정책.
- 대상 독자: 워크플로우 설계자, 메모리 계층 설계자, README/INDEX 유지보수자.
- 상태: Accepted (draft phase 1)
- 최종 수정일: 2026-07-21
- 관련 문서: [`./MICROSOFT_MEMORA_EVALUATION.md`](./MICROSOFT_MEMORA_EVALUATION.md), [`./ADR-001-source-state-knowledge-3-layer-separation.md`](./ADR-001-source-state-knowledge-3-layer-separation.md), [`./ADR-004-llm-wiki-layer.md`](./ADR-004-llm-wiki-layer.md), [`../../workflow-source/core/workflow_state_vs_project_docs.md`](../../workflow-source/core/workflow_state_vs_project_docs.md)

- **Status**: Accepted (v0.11.22 계획, 본 commit 은 설계 + Phase 1 zero-risk prototype 채택)
- **Date**: 2026-07-02
- **Supersedes**: —
- **Superseded by**: —

## Context

`standard_ai_workflow` 의 memory layer (v0.5.2 부터 3-layer 분리 후) 는 본문 중심 운영이 잘 되어 있다. `ai-workflow/memory/active/session_handoff.md`, `work_backlog.md`, `state.json` 이 self-host state 의 SSOT 역할을 하고, v0.11.21 까지 누적된 release memory cycle 이 provenance 와 lifecycle 을 유지해 왔다.

다만 **retrieval 구조는 상대적으로 얇다**.

- 같은 사실을 사람, 프로젝트, 결정, 날짜, task id 등 서로 다른 관점에서 다시 찾으려면 본문 전체를 다시 읽어야 한다.
- handoff / backlog / wiki / docs 가 같은 topic 으로 얽힐 때, 한 쪽만 갱신해도 다른 쪽에서 재진입 경로가 약해진다.
- session-start / wiki-query 가 관련 문서를 고를 때 문서 선택과 링크 추적에 의존하여, memory-unit 수준의 canonical anchor 가 부재하다.

2026-06-29 Microsoft Research 가 공개한 **Memora** 는 같은 문제를 "저장은 풍부하게, 검색은 가볍게" 로 풀었다. `MICROSOFT_MEMORA_EVALUATION.md` 에 정리한 검토 결과, 우리 저장소와의 mapping 은 다음 같다.

- 우리가 잘하는 것: raw memory, provenance, state↔knowledge 경계.
- Memora 가 잘하는 것: retrieval-facing structure (`primary abstraction` + `cue anchors` + iterative retrieval policy).
- 따라서 **보완 관계** 가 크고, 원본 구현 직접 이식은 dependency 비대화로 부적합하다. metadata overlay 가 가장 안전하다.

## Decision

memory layer 위에 **`Memora-inspired memory index`** 를 얹는다. 본 ADR 은 (1) 디렉토리 layout, (2) 엔트리 스키마, (3) merge 규칙, (4) retrieval flow 3-tuple, (5) 3-layer 분리와의 경계, (6) 단계별 활성화 정책을 고정한다.

### 1. 디렉토리 layout (Phase 1 도입)

`ai-workflow/memory/active/` 아래에 retrieval 전용 sub-area 를 둔다. 본문 원문은 기존 문서를 그대로 유지한다.

```text
ai-workflow/memory/active/
  session_handoff.md          # 기존 본문 (불변)
  work_backlog.md             # 기존 본문 (불변)
  state.json                  # 기존 SSOT (불변)
  memory_index/               # 본 ADR 신규
    entries/
      MEM-YYYY-MM-DD-NNN.json
    anchors/
      by_task.json
      by_entity.json
      by_project.json
```

`memory_index/` 자체는 **state layer 의 sub-area** 이다. 따라서 `ai-workflow/memory/` 의 기존 `.gitignore` 정책과 정합한다. 영구 지식으로 끌어올릴 시점은 별도 후속 ADR (예: ADR-006) 에서 결정한다.

### 2. 엔트리 스키마 (`MEM-*.json`)

```json
{
  "id": "MEM-2026-07-02-001",
  "schema_version": 1,
  "source_paths": [
    "ai-workflow/memory/active/session_handoff.md",
    "ai-workflow/memory/active/backlog/2026-07-02.md"
  ],
  "primary_abstraction": "Memora evaluation for workflow memory retrieval",
  "cue_anchors": [
    "Microsoft Memora",
    "agent memory",
    "workflow retrieval",
    "research evaluation"
  ],
  "value_digest": "조사 결과와 도입 가능성 요약 1줄",
  "owners": ["session-orchestrator"],
  "scope": ["project"],
  "merge_state": "active",
  "mentioned_in": ["docs/architecture/MICROSOFT_MEMORA_EVALUATION.md"],
  "created_at": "2026-07-02T00:00:00+09:00",
  "updated_at": "2026-07-02T00:00:00+09:00"
}
```

필드 의미:

- `id` — `MEM-YYYY-MM-DD-NNN` (날짜 + 일련번호). 일련번호는 같은 날짜 내에서만 단조 증가.
- `schema_version` — 스키마 breaking change 추적.
- `source_paths` — 본문 원문이 있는 경로. memory-only entry 인 경우 빈 배열 허용.
- `primary_abstraction` — 6~8 단어 canonical 요약. 본 ADR §4 merge 규칙의 기준점.
- `cue_anchors` — 같은 entry 로 다시 들어올 수 있는 다중 semantic entry point.
- `value_digest` — 본문 1줄 요약. retrieval 결과 preview 용.
- `owners` / `scope` — 누가 / 어느 범위에서 이 entry 를 책임지는지.
- `merge_state` — `active` / `linked` / `merged` (Phase 2 opt-in 에서 사용).
- `mentioned_in` — 이 entry 를 참조하는 영구 문서 / 위키 페이지 (cross-ref).
- `created_at` / `updated_at` — ISO 8601 + tz.

### 3. Anchor index (`anchors/by_*.json`)

`cue_anchors` 를 사전(辞書)으로 inverse-index 한다. 키 검색 비용을 O(1) ~ O(log n) 으로 낮추기 위함.

- `by_task.json` — key: task id, value: `[entry_id]`
- `by_entity.json` — key: 사람 / 시스템 / 제품 / 조직 entity, value: `[entry_id]`
- `by_project.json` — key: project / milestone, value: `[entry_id]`

생성 규칙: source_paths / titles / mentioned_in 스캔 → 자동 빌드. 수동 편집은 *권장하지 않음* (entry 갱신 시 anchor index 도 같이 갱신).

### 4. Merge 규칙

기본 상태 = **advisory / no-op**. canonical merge 는 Phase 2 에서 opt-in 으로 활성화.

| 상황 | 동작 |
| --- | --- |
| `primary_abstraction` 동일 + `source_paths` 동일 | **duplicate 차단**. 신규 entry 생성 거부. caller 가 `linked` 로 전환할지 결정. |
| `primary_abstraction` 유사 + `source_paths` 부분 overlap | **linked expansion**. 두 entry 를 `merge_state=linked` 로 유지하고, retrieval 결과에 양쪽을 노출. |
| `cue_anchors` 다르고 `primary_abstraction` 도 다름 | 신규 entry 그대로 생성. |
| 본인이 `--merge` opt-in (Phase 2) 호출 시 | `merge_state=merged` 로 통합. 단 provenance 보존 위해 source_paths 합집합 유지. |

핵심: **aggressive 자동 병합을 default 로 두지 않는다**. 잘못 합치면 시간축 변화와 사실 충돌이 뭉개진다. Phase 2 opt-in 까지 보수적으로 유지한다.

### 5. Retrieval flow 3-tuple

session-start / doc-sync / backlog-update 가 memory_index 를 사용할 때 다음 순서로 탐색한다.

1. **Anchor exact match** — `cue_anchors` ↔ query token (정확 일치 + 케이스 비감수). anchor index `by_*.json` 으로 O(1) lookup.
2. **Embedding / BM25 fallback** — 1차에서 hit 없으면 `primary_abstraction` 임베딩 (vector 검색) 또는 BM25. threshold 미만이면 빈 결과로 종료.
3. **Linked entry expansion** — 선택된 entry 의 `mentioned_in` + `source_paths` 따라 1-hop 확장. multi-hop 은 depth 2 까지 (worker execution latency 보호).

각 단계에서 **충분성 체크** — 1차 hit 이 충분히 관련성 높으면 조기 종료. Memora 의 policy-guided retriever 가 iterative depth 를 조절하는 방식과 같으나, 본 ADR 은 처음 3-tuple 정도로 단순화한다.

### 6. 3-layer 분리와의 경계

본 ADR 은 [ADR-001](./ADR-001-source-state-knowledge-3-layer-separation.md) 의 3-layer 분리를 **깨지 않는다**.

- **Source (SSOT)**: `workflow-source/` 는 손대지 않는다. memory_index 생성기 / anchor 빌더가 향후 helper 로 추가될 수 있으나, 본 commit 에서는 미포함.
- **State (runtime)**: `memory_index/` 는 state layer 의 sub-area. `.gitignore` 정책과 정합. 기본 local-only, 공유가 필요하면 selective tracking.
- **Knowledge (영구)**: `docs/` 는 reviewable. 본 ADR 자체가 knowledge layer 에 있다. 평가 문서 (`MICROSOFT_MEMORA_EVALUATION.md`) 와 본 ADR 의 cross-ref 가 [ADR-004](./ADR-004-llm-wiki-layer.md) 의 wiki SSOT 와도 정합한다.

**금지 동작**: memory_index 가 wiki / docs 의 검색 역할을 *먹어버리는* 방향. 본 ADR 은 retrieval layer 만 강화하며, wiki 는 그대로 ingestion SSOT, docs 는 그대로 PR-reviewable knowledge.

## Consequences

### Positive

- **본문 변경 없이 retrieval 강화**. Phase 1 은 metadata 만 추가하므로 기존 handoff / backlog 작성자가 workflow 를 바꿀 필요 없음.
- **세션 시작 비용 절감**: session-start 가 적은 read 로 관련 문서 선택 가능. wiki-query 와 doc-sync 도 동일한 인덱스 재사용.
- **3-layer 정합**: ADR-001 의 state↔knowledge 경계를 흐리지 않음.
- **점진적 활성화**: Phase 2 (merge) / Phase 3 (policy) 는 opt-in. 먼저 안전하게 시작하고 데이터 모은 후 확장.

### Negative / Trade-offs

- **추가 tracked state**: `memory_index/entries/` 가 누적됨. 정리는 caller 책임.
- **anchor build 비용**: source_paths / mentioned_in 스캔. 큰 저장소에서 매번 재빌드 시 비용 발생 → Phase 1 에서는 incremental build 만 허용.
- **retrieve fail-safe**: retrieval 결과가 0 일 때 조용히 빈 결과 ❌ → caller 가 fallback (full read / wiki search) 가져야 함.
- **merge 활성화 시 provenance 희석**: Phase 2 opt-in 시 caller 가 명시적 책임. 본 ADR 은 default advisory 만 확정.

### 후속 작업 (현황 반영, v0.11.22 2026-07-03 기준)

[v0.11.22 release memory cycle 진행 중 — 8 release / 8 commit 누적, 48ec7d → 2ab3b6c]

- ✅ **Phase 1 (v0.11.22 release 1)**: zero-risk metadata prototype. `workflow_kit/common/state/memory_index.py` helper + `ai-workflow/memory/active/memory_index/entries/` `*.json` 자동 emit + smoke test.
- ✅ **Phase 1.5**: `state.json` hook (state.json 생성 시 optional `memory_entries[]` 추가).
- ✅ **Phase 2 (v0.11.22 release 3-4)**: `--merge` opt-in 의 canonical merge 활성화. `primary_abstraction` similarity + task lineage 기반. provenance 보존 위해 `source_paths` 합집합.
- ✅ **Phase 2b (v0.11.22 release 5)**: BM25 stdlib 2단계 fallback (embedding 없이도 retrieval 동작 보장).
- ✅ **Phase 3 (v0.11.22 release 6)**: dispatcher entry — `memory-index-query` skill beta, `cmd_memory_index_query` subcommand 신규.
- ✅ **Phase 3b1 (v0.11.22 release 7)**: `session-start` memory_index opt-in wiring.
- ✅ **Phase 3c (v0.11.22 release 8)**: `doc-sync` memory_index opt-in wiring.
- ✅ **Phase 3d (v0.11.22 release 9, last skill)**: `backlog-update` memory_index opt-in wiring.
- 📝 **ADR-006**: retrospective 자리 박기 (`34fb07f`). 회고 본문은 v0.11.23+ 또는 실 사용 30일 후 작성 — [./ADR-006-memory-index-retrospective.md](./ADR-006-memory-index-retrospective.md).

본 ADR 의 Phase 1~3d 누적 후, 후속 작업은 ADR-006 회고 + Phase 4 (구 consumer 통합) 가 본 ADR 의 follow-up 으로 자리.

## References

- [`./MICROSOFT_MEMORA_EVALUATION.md`](./MICROSOFT_MEMORA_EVALUATION.md) — 본 결정의 평가 배경 (commit `95d6eba`)
- [./ADR-001-source-state-knowledge-3-layer-separation.md](./ADR-001-source-state-knowledge-3-layer-separation.md) — 3-layer 분리 (state vs knowledge 경계)
- [./ADR-004-llm-wiki-layer.md](./ADR-004-llm-wiki-layer.md) — wiki SSOT 정합
- [`../../workflow-source/core/workflow_state_vs_project_docs.md`](../../workflow-source/core/workflow_state_vs_project_docs.md) — state ↔ docs 경계 가이드
- Microsoft Research Blog, 2026-06-29, "Memora: A Harmonic Memory Representation Balancing Abstraction and Specificity"
  https://www.microsoft.com/en-us/research/blog/memora-a-harmonic-memory-representation-balancing-abstraction-and-specificity/
- arXiv 2602.03315, "Memora: A Harmonic Memory Representation Balancing Abstraction and Specificity"
  https://arxiv.org/abs/2602.03315
- GitHub, `microsoft/Memora` (MIT) — reference implementation, 직접 의존 ❌
  https://github.com/microsoft/Memora
