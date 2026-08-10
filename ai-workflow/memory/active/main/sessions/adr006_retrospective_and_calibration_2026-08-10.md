# 실측이 결정한 하루 — 캘리브레이션부터 ADR-006 완결까지 (2026-08-10, 2차 세션)

- 문서 목적: 이번 세션의 판단 근거와 실측을 남긴다. handoff 가 담기엔 긴 맥락.
- 범위: title drift 캘리브레이션 → registry 비-loopback → ADR-006 회고 →
  후속 W-1~W-4 → v1.1.6-beta 발행 (TASK-008~015)
- 대상 독자: 다음 세션의 AI agent, 저장소 관리자
- 상태: closed
- 최종 수정일: 2026-08-10
- 관련 문서: [ADR-006](../../../../../docs/architecture/ADR-006-memory-index-retrospective.md), [backlog/2026-08-10.md](../backlog/2026-08-10.md), [Beta-v1.1.6.md](../../../../../workflow-source/releases/Beta-v1.1.6.md)

## 1. 무엇을 했나 (커밋 8건, TASK 8건, 릴리스 1회)

| 커밋 | 내용 |
| --- | --- |
| `41b98db` | title drift 임계 0.6 실측 캘리브레이션 + registry 비-loopback bind 실측 (TASK-008·009) |
| `051e41a` | ADR-006 회고 (P2-1) + W-1 write-path advisory 루프 (TASK-010·011) |
| `1e50701` | W-2 질의 다양화 — 컨텍스트 유래 query + telemetry 질의 내용 (TASK-012) |
| `713faec` | W-3 entry 간 링크 — related_ids + expansion 첫 발동 (TASK-013) |
| `91e1551` | W-4 지표 재정의 — utilization_3tuple north-star (TASK-014) |
| `87d80ae`·`25e09d4`·`c51d973` | v1.1.6-beta 발행 3부작 — 등록 / 준비 / 후처리 (TASK-015) |

공통 주제는 **측정이 결정한다** 였다 — 그리고 측정 자체가 세 번 우리를 속이려
했다 (아래 §3).

## 2. ADR-006 사이클 — 회고가 곧 수리 목록이 됐다

P2-1 은 "회고 본문 작성" 이었는데, telemetry 256 events 를 실측하니 회고가
곧 수리 목록이었다: 30일 실사용 = **고정 질의 1종 → 고정 entry 1건**
(BM25/expansion/merge 발동 0, 신규 entry 0). 그래서 회고와 같은 날 후속
4건을 전부 구현했다:

- **W-1** `wk suggest-memory-entries` — 쓰기 운영 루프 (무-write advisory).
  적재 판단은 사람/에이전트. 이 세션 close 에서 실제로 두 번째 entry
  (`MEM-2026-08-10-002`, 캘리브레이션 방법론) 를 이 도구의 제안에서 골랐다 —
  루프가 두 바퀴째 돈다.
- **W-2** 컨텍스트 유래 질의 + telemetry `query_tokens`/`query_source`.
- **W-3** `related_ids` 명시 링크 — 33일 만의 expansion 첫 발동.
- **W-4** north-star = `utilization_3tuple`, hit_rate 는 보조 강등.
  첫 실측은 정직한 저점 (diversity 1/8 · new_30d 1(→2) · distinct 0/1).

## 3. 측정이 우리를 속이려 한 세 번

1. **캘리브레이션 1차 채굴 오염** — 임의 줄의 TASK-ID 언급을 전부 제목으로
   먹이니 분포가 통째로 뒤집혔다 (양성 median 0.07 / 음성 1.0). production
   이 실제로 읽는 자리만 먹이니 정상. → agent memory
   `calibration-mines-the-production-path`.
2. **hit_rate 1.0 의 침묵** — W-2 의 첫 정직한 miss 가 33일간 1.0 뒤에 숨어
   있던 패널 간 반올림 불일치 (Panel 3 raw vs Panel 8 round-4) 를 즉시
   드러냈다. round-at-source 로 통일. 변하지 않는 지표는 자기 소비자의
   결함도 숨긴다.
3. **RELEASE.md 의 우연한 통과** — v1.1.5 때 §65 산문의 "v1.1.5+" 가 version
   stamp 검사를 우연히 통과시키고 있었다 (정본 stamp 는 v1.1.3 정지).
   v1.1.6 릴리스 직후 전량 재실행이 잡았고 정본 3곳을 갱신했다.

이 밖에 W-4 구현 중 함정 하나: miss 의 `selected_ids: []` 가 구 라인 기본값과
구분되지 않았다 → measurable 판정을 값-비어있음에서 **필드 존재**
(`model_fields_set`) 로. 0건 조회도 어엿한 측정이다.

## 4. 검증 못 한 것 / 남은 것

- **cross-host federation / mavis e2e** — 여전히 darwin homelab 몫 (registry
  는 이번에 비-loopback bind 까지는 실측).
- **branch protection** — 도구는 준비돼 있고 소유자 결정 대기.
- **3-tuple 지표의 추이** — 정직한 저점에서 출발했다. 오르는지 (질의가
  다양해지고 entry 가 쌓이고 distinct 조회가 느는지) 는 다음 세션들의 실사용이
  말해 준다. 항상 저점이면 W-2 의 컨텍스트 유도나 W-1 루프가 안 도는 것.
- title drift 임계는 캘리브레이션 fixture 가 2026-08-10 스냅샷 — 데이터가
  충분히 쌓이면 `scripts/calibrate_title_drift.py --apply` 로 재캘리브레이션.

## 5. 다음 세션에

시작은 `wk survey-remote-workspaces` + session-start 그대로. 새 종료 절차가
하나 늘었다: **close 전에 `wk suggest-memory-entries` 를 한 번 돌려 entry
승격 후보를 판단한다** (advisory — 자동 적재 아님). memory_index README
운영 규칙에 명시돼 있다.
