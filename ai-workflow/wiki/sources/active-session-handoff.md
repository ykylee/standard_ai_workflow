---
type: meta
status: draft
r9_skip: true
title: active-session-handoff
created: 2026-07-22
last_touched: 2026-08-20
---

# Active Session Handoff (Derived View, 2026-08-20)

> L1 SSOT: `ai-workflow/memory/active/main/session_handoff.md` (372 lines)
> 본 L2 파생 뷰는 in-repo retrieval 용 압축 요약이다. 정본은 L1 SSOT 를 본다.
> 생성: `2026-08-20` by `workflow_kit.tools.refresh_wiki_memory --emit-l2`

## 현재 기준선

**51차 세션 — 관찰 축 3개 실측. 두 축에서 결함이 나왔고 셋째는 왜 못 재는지 밝혔다.** **① mypy flake (관찰 3차, main-004)**: 2차 기준선 이후 smoke **69 run 중 1건** 재발 — 그리고 **native 전용이라던 서명이 깨졌다**(이번은 slash). **원인 계열 확정: race 가 아니라 mypy INTERNAL ERROR(크래시)** — 아티팩트 `stderr_tail` 원문이 근거이고, 검사 `duration_sec` 0.65s 대 정상 3.4s/197파일이라 **분석 중이 아니라 시작 단계**에서 죽었다. 2차의 transient-파일 가설은 반증. **4번 터지는 동안 원인을 못 좁힌 이유는 절단 두 겹**이었다 — `smoke.yml` 의 `[:120]` 과 `_error_excerpt(400)` 이 사유를 잘라, 원인은 **아티팩트를 내려받아서야** 보였다; mypy 크래시는 보일러플레이트로 시작해서 앞에서 자르면 잡음만 남는다. 수리 3건(신호를 앞으로 정렬 · 요약 120→800 · excerpt 400→1200)이고 **검사는 상한을 복제하지 않고 smoke.yml 에서 읽는다**. 완료 기준을 개정: 'N run 연속 green' 은 원인을 모르던 시점의 기준이라 폐기 → **다음 재발이 트레이스백을 로그에 남길 것**. **② memory_index 3-tuple (main-004 신규)**: `query_diversity` 4/285 · `entries_new_30d` 2 · `distinct_entries_retrieved` **1/9** — 8/10 회고가 미리 적어 둔 판정 조건('항상 저점이면 W-1/W-2 가 안 도는 것')에 걸렸다. **원인은 검색이 아니라 배선**이었다: 회고가 추가한 종료 단계 `wk suggest-memory-entries` 가 `memory_index/README.md` 에만 있고 정본·CLAUDE.md·AGENTS.md 어디에도 없어(grep 0건) **한 번도 안 돌았다** — 실제로 승격 후보 5건이 대기 중이었다. 정본 §8.1·§11.1 에 넣고 진입점 재생성. **드리프트가 조용히 지나간 이유도 고쳤다**: `check_standard_single_source` case 3 이 §11 표에서 **대표 1개만** 봐서 6번째 명령 추가가 안 보였다 — 전 항목 대조 + **이 저장소 자신의 진입점**을 재는 case 신설. 새 절차를 이번 세션에 적용해 1건 승격(`MEM-2026-08-20-001`). **③ cross-host federation**: 두 번째 호스트(MacBook)가 없어 **이 호스트에서는 원리적으로 못 잰다** — 관찰이 아니라 대기다. **부수(main-005)**: 게이트 slash 축에서 `check_watch_transient_writer` 가 1회 red — `REQUIRES_QUIET_REPO` 가 아니라 **타이밍 가정**이었다(`SETTLE_S` 의 '폴링 간격의 20배' 근거는 폴러가 실제로 스케줄된다는 전제인데 16-way 병렬에서 깨진다). 고정 sleep 을 **관측 대기**로 바꿨다 — mypy flake 와 같은 계열이지만 이쪽은 우리 검사라 바로 고쳤다. 검사 264 유지.

## 진행 중

- TASK-2026-08-13-main-004 CI native 셀 mypy 게이트 flake — cmd_validate mypy 전역 스캔의 병렬 race 판정
- TASK-2026-08-14-main-009 task SSOT 4단계 — 본문 라벨 영어 전환 (release 경계)

## 차단

- (없음)
