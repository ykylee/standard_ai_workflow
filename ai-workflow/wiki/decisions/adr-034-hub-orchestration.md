---
type: decision
status: proposed
adr_id: ADR-034
decided_at: 2026-11-22
alternatives_considered: [no-delivery-sessions-pull-only, hook-required-delivery, relay-required-for-participation, pty-screen-driving, harness-own-queue-as-ssot, vscode-extension-full-ui]
related_pages: [decisions/adr-033-workflow-hub, decisions/adr-027-roadmap-wbs-sdlc, decisions/adr-030-compact-relay]
created: 2026-11-22
updated: 2026-11-22
r9_skip: true
---

# ADR-034: 허브 오케스트레이션 — 중앙 허브 · PC 중계 · 하네스 · 세션, 메인 오케스트레이터가 일을 나눈다

## Status

**Proposed** (2026-11-22, TASK-2026-11-22-main-006, M-042/WBS-42.3) — design(M-043) 뒤 Accepted.
concept 결정 O1~O10 (`docs/planning/hub-orchestration-review-2026-11.md` §12) · 요구 결정 Q1~Q4 (`docs/planning/hub-orchestration-requirements-2026-11.md` §6) 는 소유자가 정했다 (2026-11-22, 권고안 전부).
요구와 실측: [`hub-orchestration-requirements-2026-11.md`](../../../docs/planning/hub-orchestration-requirements-2026-11.md) (R17~R24, 실측 §1).

## Context

- 2.0 허브(ADR-033)는 task · handoff · 이력의 정본이지만 **일을 나눠 주지 못한다** — 세션이 스스로 와서 읽어 갈 뿐이다. A2A 는 첫 판에서 뺐고(D5 · 요구 R15.3),
  1.x 다중 워크스페이스 설계는 "중앙은 하네스에 메시지를 보내지 않는다"(`multi_workspace_orchestration.md` §0.6)였다.
- 소유자 제기 (2026-11-22): 중앙 허브 → PC 중계 허브 → 하네스 → 세션 으로 관리하고, 선언된 메인 오케스트레이터 세션이 다른 세션을 관리 · 분배한다.
  중계 허브는 로컬 웹 · 스탠드얼론 · VS Code 확장으로 낼 수 있다.
- 실측 (Linux, Claude Code 2.1.330 · Codex 0.167.1, 요구 §1):
  - 두 하네스 모두 비대화 시작 · 이어 가기 · 한 프로세스 여러 입력 · 상태 읽기를 정식 수단으로 갖는다 (Claude stream-json · `--resume` · `claude agents --json`, Codex `exec resume` · app-server `turn/steer` · `codex queue`).
  - hook · 신뢰 없이도 전달이 닫힌다 — **허브 도구 응답 편승(M1)** · **대기 도구 긴 폴링(M2, Claude 300초 · Codex 120초 견딤)** · **받은편지함 파일(M3)**.
  - 셋 다 **진입 지침이 있을 때만** 동작한다. 지침이 없으면 Claude 는 거부하고 보고, Codex 는 말없이 무시한다 — 프롬프트 주입 방어가 기본으로 선다.
  - 신뢰가 필요한 것은 Claude `--bg`(디렉터리 신뢰, 상속 안 됨)와 Codex hook 뿐이다.

## Decision

소유자 결정 (2026-11-22):

| # | 결정 |
|---|---|
| O1 | **D5 · R15.3 을 연다** — 허브가 세션에 일을 전한다. 정본은 허브 받은편지함 |
| O2 | **세션 = 배정 · 전달 · 상태 단위**, 작업 기억은 콜사인 단위 그대로 |
| O3 | **PC 중계 = `workflow_kit[relay]` 선택 계층** — 참여에는 kit 불필요 (H4 유지) |
| O4 | 오케스트레이터의 **세션 요청 · 멈춤 요청은 요청마다 사람 승인** |
| O5 | 오케스트레이터는 **owner 만 지정 · 프로젝트당 하나 · lease** |
| O6 | 첫 하네스 **Claude Code + Codex** — 나머지는 원격 MCP 전달만 |
| O7 | 중앙 ↔ 중계는 **나가는 연결만**, 첫 판은 같은 머신 · LAN |
| O8 | 화면 **로컬 웹 → VS Code 확장(TS 는 webview 껍데기만, wheel 밖) → 스탠드얼론 보류** — PURPOSE 제외 영역에 껍데기 예외 |
| O9 | 상한 기본값 (PC 동시 세션 3 · 하루 세션 요청 10 · 대기 연속 30회) |
| O10 | **2.1.0, 더하기만** |

**전달 경로 우선순위 (소유자 2026-11-22 — "hook 이나 권한이 필요하지 않은 간접 수단")**: 기본 = M1 편승 · M2 대기 도구 (원격 MCP 만) → 선택 = 중계의 M3 파일 · T2 비대화 실행 → 보강 = hook.
진입 지침의 전달 규칙이 활성화 스위치이고, 수신 확인(ack)이 없는 배정은 미전달로 센다.

### 요구 결정 (Q1~Q4, 요구 §6)

- Q1 사람이 보는 대화형 세션의 대기 도구는 기본 꺼짐 (M1 만) · Q2 전달 규칙 없는 세션(2.0 판)에는 배정 409
- Q3 오케스트레이터도 직접 작업한다 · Q4 숫자 기본값 그대로 (design 이 실측으로 바꿀 수 있다)

## Consequences

- 2.1.0 의 새 표면: 세션 · 받은편지함 · 오케스트레이터 lease · 배정 · 세션 요청(승인) 표, 도구(대기 · ack · 배정 · 보고 · 지정 · 인계), 허브 도구 응답의 `hub_inbox` 칸,
  진입 영역의 전달 규칙, `workflow_kit[relay]` (하네스 어댑터 · 로컬 웹), VS Code 확장 껍데기(wheel 밖).
- 2.0 요구 R15.3 의 "A2A 도구 0" 검증은 2.0.x 에만 걸린다. `multi_workspace_orchestration.md` §0.6 은 1.x 흐름의 원칙으로 남는다.
- 2.0 R4.6(쓰기는 그 콜사인만)의 예외가 생긴다 — 오케스트레이터의 받은편지함 쓰기 · 배정 칸뿐 (요구 R19.5).
- 대기 도구는 하네스 턴을 붙잡는다 — 사람이 보는 세션에는 기본으로 쓰지 않는다 (Q1).
- 하네스 판이 바뀌면 실측 S(요구 §1)를 다시 돈다 — 제어 수단(`turn/steer` · `codex queue` · stream-json)은 하네스 쪽 실험 기능이 섞여 있다.

## Alternatives

- 지금처럼 세션이 끌어오기만 (전달 없음) — O1 에서 버림.
- hook 을 전달의 필수 경로로 — 신뢰 수락이 필요하고 하네스마다 다르다. 소유자 방향(간접 수단 우선)으로 보강 경로로 내림.
- 중계를 참여 조건으로 — H4 를 깬다. O3 에서 선택 계층으로.
- PTY 로 대화형 화면 조작 — 실측상 하네스가 정식 제어면을 갖고 있어 불필요 (요구 R21.5).
- 하네스 자체 큐(`codex queue`)를 정본으로 — 하네스마다 다르고 허브가 확인할 수 없다. 전달 수단으로만 (요구 R18.1).
- VS Code 확장에 화면 로직 — 화면이 두 벌로 갈린다. 껍데기만 (O8).
