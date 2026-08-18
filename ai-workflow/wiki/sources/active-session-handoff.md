---
type: meta
status: draft
r9_skip: true
title: active-session-handoff
created: 2026-07-22
last_touched: 2026-08-19
---

# Active Session Handoff (Derived View, 2026-08-19)

> L1 SSOT: `ai-workflow/memory/active/main/session_handoff.md` (350 lines)
> 본 L2 파생 뷰는 in-repo retrieval 용 압축 요약이다. 정본은 L1 SSOT 를 본다.
> 생성: `2026-08-19` by `workflow_kit.tools.refresh_wiki_memory --emit-l2`

## 현재 기준선

**49차 세션 — main-004 close: wiki L2 파이프라인 회생 (`wk wiki-emit` 3-step → 2-step, 검사 263→264, 전량 2축 green).** 상세는 [49차 세션 기록](./sessions/wiki_l2_pipeline_revival_2026-08-19.md). 핵심은 크래시 두 개가 아니라 **세 단계가 각각 다른 이유로 이미 유효하지 않았다**는 것이었다 — 그래서 '고쳐서 rc=0 을 만든다' 가 오답이었다. **1단계는 소유권 충돌**: write 대상 4개가 전부 무너져 있었고(`state.json` 은 정본 §11.2 의 생성 산출물이라 이 단계가 **두 번째 writer** 였다 · `work_backlog.md` 는 v0.14.0 에서 사라짐 · `memory/log.md` write 는 죽은 코드 · `wiki/log.md` 는 2026-06 하드코딩), 은퇴시키되 **조용한 no-op 이 아니라 사유를 말하고**(rc=0) 함수 자체를 지웠다 — 분기로만 막으면 다음 사람이 다시 부른다. **2단계는 vault 화석 3종이 전부 실행 경로 위**에 있었고(이중 경로 · `parts.index("raw")` · **정의된 적 없는 `VAULT_ROOT`**) v0.7.17 이후 **한 번도 끝까지 실행된 적이 없었다**; 고쳐도 할 일이 없던 진짜 이유는 게이트가 `<needs content>` **일회성**이라 한 번 emit 된 page 가 영원히 대상이 아니었던 것 — **신선도 게이트**로 바꾸고, 본문 전체를 갈아끼우게 되므로 `> Generated:` 표식 없는 page 는 **manual 로 보고 건드리지 않는다**. **3단계는 2026-06-14 스냅샷 축자 재생성**이었고 `last_touched` 를 그 날짜로 되돌렸다 — 현재 SSOT 파생으로 재작성, `last_touched` 는 실제 emit 일자, 바이트가 같으면 write 0(`unchanged`), L1 없는 stub 은 `missing_l1` 로 밝힌다. **날짜 박힌 붕괴를 막았다**: L2 4개가 `2026-07-22` 라 **2026-08-21 에 lifecycle 5.0→0.0 / overall 4.71 A→3.88** 이 예약돼 있었고, 갱신할 유일한 도구가 67일 전으로 되돌리고 있었다(7/22 는 사람이 커밋 `dcbf2af7` 로 올린 값). **검사가 apply 를 잰다** — 이전 8 cases 는 전부 dry-run 이라 두 크래시를 구조적으로 못 봤다; `check_refresh_wiki_memory` 11 재작성 + `check_wiki_emit_pipeline` 11 신설, 되주입 6종 red 실증.

## 진행 중

- TASK-2026-08-14-main-009 task SSOT 4단계 — 본문 라벨 영어 전환 (release 경계)

## 차단

- (없음)
