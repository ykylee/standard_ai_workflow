---
type: meta
status: draft
r9_skip: true
title: active-session-handoff
created: 2026-07-22
last_touched: 2026-08-20
---

# Active Session Handoff (Derived View, 2026-08-20)

> L1 SSOT: `ai-workflow/memory/active/main/session_handoff.md` (382 lines)
> 본 L2 파생 뷰는 in-repo retrieval 용 압축 요약이다. 정본은 L1 SSOT 를 본다.
> 생성: `2026-08-20` by `workflow_kit.tools.refresh_wiki_memory --emit-l2`

## 현재 기준선

**51차 세션 (이어서) — main-008·009: 사용자가 만든 session-end 스킬이 이 환경에서 안 쓰이던 문제.** **두 채널이 서로 다른 스킬 집합을 노출하고 있었다** — 플러그인은 처음부터 4종인데 bootstrap(`.claude/commands/`)은 3종만 emit(생성기 docstring 이 스스로 '3 slash command' 라 적고 있었다). 게다가 진입 스킬의 `description` 은 **이미 세션 종료를 약속**하고 있어서, 광고는 4단계인데 배선은 3개인 상태였다 — 모델이 있지도 않은 명령을 찾는다. 생성기에 `session-end` 명령을 넣고 진입 스킬 본문을 4종으로 맞췄고, **두 채널 집합을 대조하는 파리티 검사 2종**을 신설했다(개수만 세면 이름이 어긋난 채 통과한다). `/workflow-session-end` 는 파일을 쓰자마자 **이 세션에서 바로 잡혔다**. **남은 절반(main-009)**: 플러그인 스킬 4종이 인벤토리엔 있는데 세션엔 없다. 가설 4개 기각(파일 부재 · 비활성 · 매니페스트 파손 · **세션보다 늦은 설치** — 설치가 21시간 앞선다). 확정: `claude plugin details` 는 `Skills (4)` 로 다 세는데 호출하면 `Unknown skill` — **인벤토리는 세션 가용성의 증거가 아니다**. 그래서 `wk doctor` 의 `content_drift` 에 **노출 미측정 선언**을 넣고(`in_sync` 는 '쓸 수 있음' 이 아니다 — main-019 의 `installable` 과 같은 원칙) INSTALLATION §7.0.1 에 확인 방법을 적었다. 유력 가설은 로컬 `.claude/skills/standard-ai-workflow/` 와 **같은 이름의 플러그인** 사이 자기 충돌인데, 검증에 새 세션이 필요하다. 검사 264 유지.

## 진행 중

- TASK-2026-08-20-main-009 플러그인 스킬 4종이 인벤토리엔 있고 세션엔 없다 — in_sync 를 쓸 수 있음으로 읽던 자리
- TASK-2026-08-13-main-004 CI native 셀 mypy 게이트 flake — cmd_validate mypy 전역 스캔의 병렬 race 판정
- TASK-2026-08-14-main-009 task SSOT 4단계 — 본문 라벨 영어 전환 (release 경계)

## 차단

- (없음)
