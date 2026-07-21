# ADR-006: ADR-005 Memory Index Implementation Retrospective (Placeholder)

- 문서 목적: v0.11.22 의 ADR-005 memory_index 8 release (`Phase 1 prototype` ~ `Phase 3d backlog-update wiring`) 누적의 retrospective 자리 + 후속 release 의 회고 본문 anchor.
- 범위: merge rule / 3-tuple retrieval / skill wiring 의 실 사용 데이터 retrospective. helper API 의 backward compatibility / wiring latency 등.
- 대상 독자: 워크플로우 설계자, 메모리 계층 설계자, 후속 release reviewer.
- 상태: **draft (placeholder, 후속 release 에 본문 작성)**
- 최종 수정일: 2026-07-21
- 관련 문서: [`./MICROSOFT_MEMORA_EVALUATION.md`](./MICROSOFT_MEMORA_EVALUATION.md), [`./ADR-005-memora-inspired-memory-index.md`](./ADR-005-memora-inspired-memory-index.md), [`./ADR-001-source-state-knowledge-3-layer-separation.md`](./ADR-001-source-state-knowledge-3-layer-separation.md), [`./ADR-004-llm-wiki-layer.md`](./ADR-004-llm-wiki-layer.md)

- **Status**: Accepted (placeholder 본 release, 회고 본문은 후속 release)
- **Date**: 2026-07-02
- **Supersedes**: —
- **Superseded by**: —
- **Resolves 후속**: v0.11.23+ 또는 실 사용 30일 후 회고 본문.

## Context

v0.11.22 의 ADR-005 memory_index 는 본 release 의 end-to-end milestone 에 도달했다. 누적된 8 release / 8 commit (`48ec7d → 2ab3b6c`) 의 의의:

```
ADR-005 결정 (468ec7d)
  ↓
Phase 1 prototype (e4c7343)         helper + schema + 8 smoke
Phase 1.5 state.json hook (4655e7c) 3 smoke (11/11)
Phase 2a --merge opt-in (d2d8a1c)   3 smoke (14/14)
Phase 2b BM25 fallback (5973146)    3 smoke (17/17, stdlib only)
Phase 3a dispatcher entry (7be5029) 2 smoke (19/19)
Phase 3b1 session-start wiring (73564d9) 2 smoke (21/21)
Phase 3c doc-sync wiring (c46d729)   2 smoke (23/23)
Phase 3d backlog-update wiring (2ab3b6c) 2 smoke (25/25)
```

본 retrospective 의 필요성:

1. **`--merge` opt-in 의 실 사용 효과**: Phase 2a 의 `apply_memory_merge` 가 canonical merge 의 caller 빈도 / `MERGED` / `LINKED` 비율 — *advisory default* 정책이 caller 의 *aggro merge* 가능성을 의도대로 막았는지 검증.
2. **BM25 token overlap fallback 의 효율**: Phase 2b 의 `_bm25_retrieve` 호출 시 `cue_hits < top_k` 인 비율 / BM25 hit 의 *quality* (top-N relevant recall@k) / stdlib only 구현의 latency vs rank_bm25 의 차이.
3. **3 skill wiring 의 실 작업 latency 영향**: Phase 3b1~3d 의 session-start / doc-sync / backlog-update 가 memory_index_query_output 을 더할 때 *추가된 wall-clock time* / worker execution latency 영향.
4. **3-layer 분리 (ADR-001) + wiki SSOT (ADR-004) 정합 유지 audit**: 본 release 의 4 file × 8 release 의 commit history 가 state ↔ knowledge 경계를 일관되게 유지했는지 (cross-ref / milestone 정합).

## Decision

**본 ADR-006 은 회고 자리만 박는다.** 회고 본문은 후속 release 에서 채운다.

### 회고 자리 (placeholder 본문)

1. **`--merge` opt-in 실 사용 데이터**
   - *metric*: `apply_memory_merge` 호출 횟수, `MERGED` 비율, advisory emit 빈도, dry-run vs apply 비율.
   - *의사결정 후보*: default advisory 유지 / opt-in 변경 / Phase 4 활성화.

2. **BM25 fallback 의 효율**
   - *metric*: `query_memory_index` 호출 시 `cue_hits=0` 비율, BM25 top-k recall@5/10, stdlib only 의 smoke latency.
   - *의사결정 후보*: BM25+ tuning / embedding 3단계 추가 (Phase 4 follow-up) / 작업 별 BM25 threshold.

3. **Skill wiring 의 latency**
   - *metric*: `query_memory_index_for_dispatcher` 의 session-start / doc-sync / backlog-update 별 wall-clock p50/p95.
   - *의사결정 후보*: `--memory-index-dir` default-on 전환 (Phase 4) / ws subdir 만 정공법 유지 / ws 외부 dir 정공법 확장.

4. **3-layer + wiki SSOT 정합 audit**
   - *metric*: 본 release 의 commit diff 가 source/state/knowledge 어떤 레이어 변경인지 분포.
   - *의사결정 후보*: ADR-001 / ADR-004 의 본문 갱신 / ADR-006 의 final retrospective 결정.

### 회고 본문 작성 시점 (후속 release 의 정공법)

- v0.11.23+ release 시작 시 (≥ 14일 누적 사용 데이터 후)
- 또는 실 사용 30일 후 (권장)
- 또는 v0.11.24 milestone (다음 stable guarantee release) 시 필수 retrospective

## Consequences

### Positive

- **retrospective 자리 박기**: 본 release 의 placeholder 가 *후속 release 의 anchor* 역할. 다음 회고 시점에 본문만 채우면 됨.
- **cross-ref 정합**: ADR-005 / MICROSOFT_MEMORA_EVALUATION / ADR-001 / ADR-004 모두 직접 참조. 회고 본문 작성 시 cross-ref 자체 검증.
- **4 metric anchor 사전 정의**: 회고 시점에 metric 정의가 흔들리지 않도록 *placeholder 본문* 에 metric 후보 4 가지 명시.

### Negative / Trade-offs

- **placeholder 의 단기 한계**: 본 ADR-006 는 본 release 에 정합성/검증 안 됨 (실 데이터 부재). 후속 release 의 retrospective 작성자에게 책임.
- **cross-project 적용**: 본 retrospective 패턴 (placeholder ADR + 후속 release retrospective 본문) 은 *다른 project 의 milestone* 도 적용 가능하나, 본 release 는 standard_ai_workflow 만.

### 후속 작업

- v0.11.23 release 본문 작성 시 본 ADR-006 본문 회고 + metric 측정.
- 실 사용 30일 후 회고 본문 (권장 2026-08-01 ~ 2026-08-15).
- 회고 결과에 따라 ADR-005 본문 직접 갱신 (merge rule / 3-tuple 의 본문 보강) 또는 ADR-007 / ADR-008 신규 결정.
- 본 ADR-006 status: `draft (placeholder)` → 회고 시 `accepted` 전환.

## References

- ADR-005 implementation history (8 release):
  - 결정: `468ec7d docs(adr): ADR-005 Memora-inspired Memory Index 추가`
  - Phase 1 prototype: `e4c7343`
  - Phase 1.5 state.json: `4655e7c`
  - Phase 2a --merge opt-in: `d2d8a1c`
  - Phase 2b BM25 fallback: `5973146`
  - Phase 3a dispatcher entry: `7be5029`
  - Phase 3b1 session-start wiring: `73564d9`
  - Phase 3c doc-sync wiring: `c46d729`
  - Phase 3d backlog-update wiring: `2ab3b6c`
- 평가: [`./MICROSOFT_MEMORA_EVALUATION.md`](./MICROSOFT_MEMORA_EVALUATION.md)
- 결정: [`./ADR-005-memora-inspired-memory-index.md`](./ADR-005-memora-inspired-memory-index.md)
- 3-layer 분리 정합: [`./ADR-001-source-state-knowledge-3-layer-separation.md`](./ADR-001-source-state-knowledge-3-layer-separation.md)
- wiki SSOT 정합: [`./ADR-004-llm-wiki-layer.md`](./ADR-004-llm-wiki-layer.md)
- Source-of-truth 평가: Microsoft Research Blog, "Memora: A Harmonic Memory Representation Balancing Abstraction and Specificity", 2026-06-29.
- Reference impl: github.com/microsoft/Memora (MIT).
