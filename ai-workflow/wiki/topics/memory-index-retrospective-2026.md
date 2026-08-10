---
type: topic
status: active
last_ingested_from: docs/architecture/ADR-006-memory-index-retrospective.md
related_pages:
  - topics/phase-13-definition-north-star
  - docs/architecture/ADR-006-memory-index-retrospective.md
  - docs/architecture/ADR-005-memora-inspired-memory-index.md
  - workflow-source/core/phase_13_followup.md
created: 2026-08-10
updated: 2026-08-10
---

# Memory Index 30일 회고 — 검색은 정교했고 사용은 균질했다 (2026-08-10)

## TL;DR

ADR-005 memory_index 의 30일+ 실사용 회고 (P2-1, TASK-2026-08-10-main-010).
telemetry 256 events 전량 집계 결과: **아키텍처는 건강** (p50 0.18ms, error 0,
3-layer 정합 clean) 하지만 **사용은 "고정 질의 1종 → 고정 entry 1건" 으로
수렴** — 3-tuple retrieval 중 1단계(cue exact)만 발동했고 BM25 / expansion /
merge 는 33일간 0회. entries 는 2026-07-09 의 7건 이후 신규 0. 후속 우선순위는
검색 계층이 아니라 **운영** (write-path 루프 + 질의 다양화) 이다. 정본:
[ADR-006](../../../docs/architecture/ADR-006-memory-index-retrospective.md).

## 실측 요약 (2026-07-09 ~ 2026-08-10)

| 항목 | 값 | 해석 |
| --- | --- | --- |
| events | 256 (활동 14일/33일) | 읽기 자동화(v0.15.21)는 작동 |
| source | session-start 211 / backlog-update 43 / doc-sync 1 / dispatcher 1 | 다양성 4 달성, 분포는 편중 |
| 질의 다양성 | **1종** (default `session,handoff,workflow`) | caller 가 token 을 넘긴 사례 0 |
| 조회된 entry | **1건** (`MEM-2026-07-09-001` 고정) | 나머지 6건은 33일간 미조회 |
| bm25 / expansion / merge | 0 / 0 / 0 | 전제(다양한 질의·자라는 entry)가 없어 잠듦 |
| 신규 entry | **0건** | write-path 에 운영 루프 부재 |
| latency | p50 0.18ms / p95 0.19ms | 비용은 비문제로 종결 |

## 핵심 교훈

1. **hit_rate 1.0 은 캐시 적중이었다** — 같은 질의가 같은 1건을 돌려받는
   시스템의 1.0 은 검색 품질 증거가 아니다. 질의 다양성을 함께 재지 않는
   지표는 항상 green 이어도 정보가 없다 (north-star 재정의의 대칭 교훈).
2. **읽기 자동화 ≠ 사용의 다양화** — 자동 활성이 사용량은 늘렸지만 default
   query 고정과 결합해 사용을 균질화했다.
3. **검색 계층은 전제 위에서만 산다** — N=7 + 잘 큐레이션된 anchor 세계에서
   BM25 는 구조적으로 기여 공간이 없다 (cue 가 놓치면 BM25 도 놓친다, 실측).
   BM25+ tuning / embedding 추가는 실측 근거 부재로 기각.
4. **placeholder 의 metric 은 전부 읽기를 물었다** — 진짜 병목(쓰기)은 질문
   목록에 없었다. 회고 metric 을 미리 박을 때는 write-path 도 물을 것.

## 후속 (ADR-006 §후속 작업)

- W-1 write-path 운영 루프 — ✅ 구현 (`wk suggest-memory-entries`, advisory 무-write, TASK-2026-08-10-main-011)
- W-2 질의 다양화 — ✅ 구현 (`derive_context_query_tokens` + telemetry `query_tokens`/`query_source`, TASK-2026-08-10-main-012). 첫 컨텍스트 질의의 정직한 miss 가 hit_rate 1.0 뒤에 숨어 있던 패널 간 반올림 불일치까지 드러냈다
- W-3 entry 간 링크 — ✅ 구현 (`related_ids` additive + validation + skeleton 프리필, TASK-2026-08-10-main-013). 실물 링크로 33일 만의 expansion 첫 발동 실증
- W-4 지표 재정의 — ✅ 구현 (`utilization_3tuple` north-star + telemetry `selected_ids`, hit_rate 는 보조 강등, TASK-2026-08-10-main-014). 미측정은 `*_measurable` 분모로 0 과 구분
