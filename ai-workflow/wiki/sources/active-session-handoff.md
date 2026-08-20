---
type: meta
status: draft
r9_skip: true
title: active-session-handoff
created: 2026-07-22
last_touched: 2026-08-20
---

# Active Session Handoff (Derived View, 2026-08-20)

> L1 SSOT: `ai-workflow/memory/active/main/session_handoff.md` (364 lines)
> 본 L2 파생 뷰는 in-repo retrieval 용 압축 요약이다. 정본은 L1 SSOT 를 본다.
> 생성: `2026-08-20` by `workflow_kit.tools.refresh_wiki_memory --emit-l2`

## 현재 기준선

**50차 세션 (이어서) — main-002 close: linter 가 3자 대조의 세 번째 출처를 일자 index 에서 **task SSOT** 로 옮겼다.** 2세션 연속 손으로 이월하던 일이 사라진다. 갈래(자동 이월 vs 출처 교체)는 실측으로 닫혔다 — **자동 이월이 오답**이었다: `state.json` 의 `in_progress_items` 는 `state/builder._aggregate_from_appendonly_layout` 이 **`backlog/tasks/` 전체**를 집계해 만드는데 linter 는 **하루치 index 하나**를 봤고, 일자 index 의 정의는 그 문서 스스로 '해당 일자의 task' 다 — 즉 **어제 연 task 가 오늘 index 에 없는 것이 정상**이고 결함은 이월 누락이 아니라 **출처 선택**이었다. 자동 이월을 택했다면 append-only 이력을 매일 고쳐 쓰고 index 의 정의와도 싸웠을 것이다. **판정을 복제하지 않는다** — 새 규칙 대신 **생성기와 같은 함수**를 부른다(린터가 생성기와 다른 규칙으로 '불일치' 를 외치는 것이 최악이다). **출처는 레이아웃이 고르고 결과에 적는다** — v0.14.0+ 는 `backlog/tasks/`, 그 이전은 일자 backlog; 폴백을 조용히 하지 않도록 `summary.in_progress_source` `{kind, path}` 를 출력 계약에 추가(additive, JSON Schema 재생성). **검사는 약해지지 않고 하나 늘었다** — handoff 드리프트는 그대로 잡히고 **낡은 state.json**(`wk refresh-state` 누락)이 새로 잡힌다; 이전 조합으로는 **볼 수 없던** 상태다. `check_workflow_linter` 5→9 cases, 되주입 3종 red 실증, 검사 264 유지.

## 진행 중

- TASK-2026-08-14-main-009 task SSOT 4단계 — 본문 라벨 영어 전환 (release 경계)

## 차단

- (없음)
