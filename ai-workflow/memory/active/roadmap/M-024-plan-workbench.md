---
id: M-024
title: 계획·진척 워크벤치 — 웹으로 계획 검토 · 응답 반영 · 진척 조회
sdlc_phase: concept
status: done
order: 24
parallel_allowed:
  - M-007
  - M-023
deliverables:
  - docs/planning/plan-workbench-review-2026-11.md
goals: [G2, G5]
---

# M-024 — 계획·진척 워크벤치

소유자 제기(2026-11-12, 123차): 작업을 시작할 때 html-plan 으로 계획을 쓰고, 그 페이지를 호스팅해
사용자가 조회하고, 사용자의 동작(결정 · 주석)이 MCP · A2A 등으로 작업에 반영되게 한다. 같은 웹에서
작업 진척도 본다.

**전제 이력**:

- [`M-022`](./M-022-claim-plan.md) concept 결정 D1~D5 — 응답은 데이터, `plan-import` 는 결정 상태만,
  응답 원문은 브랜치 메모리에 커밋. 이 마일스톤은 안 B 의 응답 반영을 **kit 웹**으로 연다.
- **하네스 중립 (소유자 지시, 2026-11-12)**: kit 은 Claude 전용이 아니다 — html-plan 플러그인 · Claude Code
  channels · claude.ai Artifact 같은 Claude 전용 표면은 쓰지 않는다. M-022 안 B 정정(concept §11)과 함께 간다.
- HTTP 서빙 선례: `common/registry_server.py` (loopback 기본 · 고정 경로 · 토큰은 환경변수 이름).
- **접속 위치 무가정 (소유자 지시, 2026-11-12)**: 브라우저가 꼭 localhost 에 있는 것은 아니다 — 원격 작업 공간 ·
  다른 기기 · 팀원 열람을 전제로 노출 경로 · 인증 · 권한을 다시 본다 (concept §11, W6 · W7).
- 진척 원천: `roadmap_state.json` · 브랜치 `state.json` (생성물), task 파일. 진척을 날조하지 않는다.

**종결 (2026-11-12)**: 소유자 결정 = concept 문서 §8 기본값 W1~W5 전부 (알림 ① 정본 · ② 조건부 · 최소 JS 열림 측정 ·
A2A 보류 · M-023 먼저 · M-022 안 B 정정 확정, 산출물 §10). requirements 는 [`M-025`](./M-025-plan-workbench-requirements.md).

**정정 종결 (2026-11-12)**: 접속 위치 무가정 — W6 · W7 기본값 확정 (concept §11.7).

## WBS

- **WBS-24.1** concept 검토 — 호스팅 · 응답 수집 · 세션 전달(MCP · hook · channels · A2A) · 진척 화면 ·
  보안 — 하네스 중립, 소유자 선택지 — 산출물: `docs/planning/plan-workbench-review-2026-11.md`
  (TASK-2026-11-12-claude-remote-sync-check-234c32-003)
- **WBS-24.2** concept 정정 — 접속 위치 무가정: 노출 경로 · 항상 인증 · viewer/approver 역할, 소유자 선택지
  W6 · W7 — 산출물: `docs/planning/plan-workbench-review-2026-11.md` §11
  (TASK-2026-11-12-claude-remote-sync-check-234c32-004)
