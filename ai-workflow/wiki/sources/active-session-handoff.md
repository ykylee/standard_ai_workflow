---
type: meta
status: draft
r9_skip: true
title: active-session-handoff
created: 2026-07-22
last_touched: 2026-08-20
---

# Active Session Handoff (Derived View, 2026-08-20)

> L1 SSOT: `ai-workflow/memory/active/main/session_handoff.md` (376 lines)
> 본 L2 파생 뷰는 in-repo retrieval 용 압축 요약이다. 정본은 L1 SSOT 를 본다.
> 생성: `2026-08-20` by `workflow_kit.tools.refresh_wiki_memory --emit-l2`

## 현재 기준선

**51차 세션 (이어서) — main-006 close: `release-status` 의 `next_version` 이 커밋을 읽지 않았다.** 릴리스 경계를 판단하려다 도구 결함을 먼저 만났다. `_suggest_next_version` 이 **현재 버전 문자열 하나만** 받아 `patch+1` 을 내놓았는데, 그 값이 같은 summary 줄에서 **`unreleased=101` 옆에 찍힌다** — 개수는 세면서 판정은 안 세니 파생값처럼 보이는 상수였다 (feat 17 · fix 24 · **breaking 1** 인 사이클에 `1.2.1` 을 권했다). 이제 미발행 커밋 유형에서 파생한다: breaking → major · feat → minor · 그 외 → patch · 근거 없으면 patch 이되 `basis.total=0` 으로 **모름을 밝힌다**. 교정 결과 `next=2.0.0` + basis(breaking 제목 포함). **숫자만 내밀지 않는 것이 설계의 핵심**이다 — 이 저장소는 v0.8.0 에 API 를 얼렸으므로 major 승격은 사람 결정이고, 도구는 판정과 **근거**를 같이 낸다(`requires_decision`). 부수: `check_release_status_auto_bump_v0_11_16` 의 기대값 `0.11.17` 이 patch 휴리스틱을 인코딩하고 있어 저장소 이력에 결합돼 있었다 — `_unreleased_commits` 를 mock 해 그 case 가 **재려던 것**만 남겼다. 되주입 3종 red 실증, 검사 264 유지.

## 진행 중

- TASK-2026-08-13-main-004 CI native 셀 mypy 게이트 flake — cmd_validate mypy 전역 스캔의 병렬 race 판정
- TASK-2026-08-14-main-009 task SSOT 4단계 — 본문 라벨 영어 전환 (release 경계)

## 차단

- (없음)
