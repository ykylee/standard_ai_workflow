# 23차 세션 기록 — 플러그인 배포 전환 계획 수립 (2026-08-12)

- 문서 목적: 23차 세션의 작업 내용·산출물·다음 시작 포인트 기록
- 범위: TASK-2026-08-12-main-013 (사용자 지시 — 배포 전략의 플러그인 전환 착수, 계획+로드맵+WBS)
- 상태: done
- 최종 수정일: 2026-08-12
- 관련 문서: [docs/planning/plugin-transition-plan-2026-08.md](../../../../docs/planning/plugin-transition-plan-2026-08.md), [22차 세션 기록](./multi_harness_plugin_review_2026-08-12.md)

## 1. 지시

사용자: "워크플로우 배포 전략을 플러그인 배포로 전환하는 작업을 시작하자.
먼저 전환 계획부터 수립하고 로드맵 갱신 및 WBS 작성해줘." — 21·22차 검토 2건의
권고가 **소유자 결정 (전환 go)** 으로 확정된 것.

## 2. 산출물

1. **전환 계획** `docs/planning/plugin-transition-plan-2026-08.md` — 원칙 5개
   (①플러그인은 파생본 — 렌더러 생성+검사 강제, 손 편집 금지 ②공유 payload =
   Agent Plugins 1.0 레이아웃 + 얇은 어댑터 ③빅뱅 금지 — bootstrap 주입 병행
   유지, 실측이 채널 전환 결정 ④Python 의존은 graceful 안내 ⑤plugin.json
   version 은 릴리스 bump 파생물) + P1~P5 로드맵 + WBS + 리스크 6건 +
   전환 완료 정의 4항.
2. **로드맵 갱신** `workflow-source/core/workflow_kit_roadmap.md` §8 — 플러그인
   배포 전환을 신규 주 작업 축으로 등재 (2026-08-12 소유자 결정 명시).
3. **planning README §4** — 검토 2건 + 계획 1건 인덱싱.
4. **WBS task 등록** — TASK-2026-08-12-main-014 (P1 payload 렌더러, high) /
   015 (P2 Claude Code 어댑터+marketplace+자기 적용, high) / 016 (P3 멀티 하네스
   어댑터, medium) / 017 (P4 릴리스 파이프라인 통합, medium) / 018 (P5 실측
   게이트+채널 전환 판정, medium) — 전부 planned, 의존·완료 기준 명시.

## 3. 핵심 결정

- **다음 릴리스 목표 범위 = P1+P2** (Claude Code 채널 개통) + 기존 예약분
  (2nd cycle shim drop + `--bundle` 기본값 전환). P3~P5 는 다음 릴리스로 넘길 수 있다.
- 015 와 016 은 014 완료 후 병렬 가능 (동시 진행 시 worktree 분리 — 전량 검사 락).
- 채널 전환의 최종 형태 (a: 주 채널 / b: Claude Code·Gemini 한정) 는 P5 실측
  후 소유자 판정으로 남긴다 — 지금 확정하지 않는다.

## 4. 다음 시작 포인트

- **TASK-014 (P1)**: `render_agent_plugin()` — plugin/ payload (plugin.json +
  skills/ 3종 + mcp.json read-only bundle) 정본 생성 + 검사 확장 + 되주입 실증.
- 열려 있는 실측 (P2·P3 에서 소화): SessionStart hook 주입 실효 / Gemini
  GEMINI.md 상시 주입 / Claude Code 의 `.agents/skills/` 판독 여부.

## 5. 검증

- 구현 없음 (계획 task) — WBS 6건 backlog 등록 실측 (전부 ok), 전량 2축 게이트
  green 확인 후 커밋.
