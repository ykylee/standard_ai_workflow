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

**50차 세션 — main-001 close: wiki L2 계약을 memory 파생 4종으로 좁혔다 (`wk wiki-emit` 2-step → **1-step**, 전량 2축 green).** 49차가 남긴 유일한 미결을 소유자 결정으로 닫았다. **정의**: `L2 = wiki 모양이 *아닌* SSOT 를 wiki 검색용으로 압축한 뷰` — 4종뿐이고 늘어나지 않는다. L1 wiki page 는 정의상 제외다(이미 wiki 모양이고 이미 검색된다). 갭 85장을 채우지 **않은** 이유: 계약의 근거였던 외부 vault retrieval 이 **v0.7.17 in-repo 전환 때 사라졌고**, 사본은 검색을 늘리지 않으면서 드리프트 표면만 늘린다. 정본은 `refresh_wiki_memory.L2_STUBS`, 설명은 `.gitkeep`. **은퇴 형태는 49차와 같다** — 진입점은 남기되 write 0 + 사유 보고(rc=0), **기계는 파일에서 지운다**; 옛 인자는 계속 받는다(박혀 있던 호출이 argparse 오류로 죽는 것보다 **왜 아무것도 안 했는지 듣는 편**이 낫다). **부수로 지표 결함 2건**: (a) discoverability·lifecycle 의 **분모가 찾은 파일 수**여서 stub 3장을 지워도 **5.0 그대로** 였다 — *사라짐* 이 지표에 안 잡혔다; 분모를 **선언된 집합**으로 바꿔 부재를 결함으로 센다. (b) **placeholder 판정이 부분 문자열**이라 `<needs content>` 를 *언급한* handoff 파생 뷰가 검색 불가로 집계됐다(5.0→3.75 실측) — 줄 전체 일치로 앵커링. 지표는 목록을 복제하지 않고 생성기 상수를 import 하며, 검사가 '복제 0' 을 직접 확인한다. 되주입 3종 red 실증, 검사 264 유지(재작성).

## 진행 중

- TASK-2026-08-14-main-009 task SSOT 4단계 — 본문 라벨 영어 전환 (release 경계)

## 차단

- (없음)
