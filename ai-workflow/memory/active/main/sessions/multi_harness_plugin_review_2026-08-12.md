# 22차 세션 기록 — 멀티 하네스 공유 플러그인 형태 검토 (2026-08-12)

- 문서 목적: 22차 세션의 작업 내용·판정·다음 시작 포인트 기록
- 범위: TASK-2026-08-12-main-012 (사용자 지시 — TASK-011 플러그인 검토의 후속)
- 상태: done
- 최종 수정일: 2026-08-12
- 관련 문서: [docs/planning/multi-harness-plugin-review-2026-08.md](../../../../docs/planning/multi-harness-plugin-review-2026-08.md), [21차 세션 기록](./plugin_distribution_review_2026-08-12.md)

## 1. 지시와 질문

사용자: "여러 하네스 도구에서 공유할 수 있는 형태로 플러그인을 만들 수 있는지 검토해줘."
21차의 판정 (Claude Code 플러그인 = 14번째 파생본) 을 받아, **하나의 아티팩트를
여러 하네스가 공유**할 수 있는지가 이번 질문이다.

## 2. 조사 (2026-08 공식 문서 실사 + 저장소 인벤토리)

- **개방 표준 2층이 이미 존재** — ① Agent Skills (`SKILL.md`, agentskills.io,
  AAIF governance): ~40개 제품 채택, `.agents/skills/` 를 Codex·OpenCode·goose 가
  공통 판독 (OpenCode·goose 는 `.claude/skills/` 도). ② **Agent Plugins 1.0**
  (agent-plugins.org, **2026-08-06 출범**, Amazon·Cursor·Microsoft·OpenAI·Vercel·
  Google): `plugin.json` + `skills/` + `mcp.json` — VS Code / Cursor / Copilot /
  ChatGPT·Codex / Kiro 호환. 단 **Claude Code·Gemini CLI·goose·OpenCode 미합류**.
- 하네스별 포맷: Gemini CLI extensions (`gemini-extension.json` — context 파일
  **상시 주입 포함** 전 컴포넌트 번들, 유일), OpenCode (JS plugin + 스킬 네이티브),
  goose (extension=MCP), MCPB (Claude 계열 한정 — 범용 미달).
- 저장소 인벤토리: SKILL.md 를 이미 5개 하네스가 같은 파일·다른 마운트로 산출,
  MCP config 7 방언 emit, `export_harness_package.py` (6-하네스 zip) 이 원형.

## 3. 판정 (검토 문서: docs/planning/multi-harness-plugin-review-2026-08.md)

**가능하다 — "공유 payload + 하네스별 얇은 manifest" 형태로.**

- 무변환 단일 아티팩트는 **부분 성립**: skills 층 (agentskills.io) 과
  Agent Plugins 1.0 (5개 클라이언트) 은 이미 무변환 공유가 되나, 우리 주요 대상
  하네스 4개가 미합류라 전면 성립은 아직 아니다.
- **권고**: 공유 payload 의 물리 배치를 **Agent Plugins 1.0 레이아웃으로 채택**
  (`plugin.json` + `skills/` + `mcp.json`) + 하네스별 얇은 어댑터 4장 (claude-code /
  gemini-cli / goose / opencode). 표준 합류가 진행되면 어댑터를 지울 수 있는 위치.
- 이는 기존 "정본 하나 + 하네스별 파생본" 아키텍처의 플러그인 판 — TASK-011 의
  Phase A 를 `render_claude_code_plugin()` 단독에서 **`render_agent_plugin()`
  (공유 payload) + 어댑터 계열**로 재정의 (Phase A′~C′, 문서 §4).
- hooks·commands·상시 컨텍스트는 어느 표준에도 없음 — 하네스별 생성 유지.
- 부수 발견: `.agents/skills/` 마운트로 심으면 Codex·OpenCode·goose 3개가
  어댑터 없이 읽는다 — bootstrap 스킬 emit 위치 수렴은 후속 검토 가치.

## 4. 다음 시작 포인트

- Phase A′ (`render_agent_plugin` 공유 payload 렌더러 + 검사 확장) — **소유자 go 대기**
  (TASK-011 Phase A 와 통합 실행).
- 실측 필요 3건: Claude Code 의 `.agents/skills/` 판독 여부 / Gemini extension
  GEMINI.md 상시 주입 / SessionStart hook 규칙 주입 (21차와 공통).

## 5. 검증

- 구현 없음 (검토 task) — 전량 2축 게이트는 문서·메모리 변경의 무해성 확인용으로 실행.
