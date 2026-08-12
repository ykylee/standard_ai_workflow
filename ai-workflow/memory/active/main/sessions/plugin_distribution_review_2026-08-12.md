# 21차 세션 — 플러그인 형태 재구성·배포 검토 (2026-08-12)

- 문서 목적: TASK-2026-08-12-main-011 종결 기록 (사용자 지시 검토).
- 상태: done
- 관련: [TASK-011](../backlog/tasks/TASK-2026-08-12-main-011.md), [검토 문서](../../../../docs/planning/plugin-distribution-review-2026-08.md)

## 결론 — 채택 권고, 단 "14번째 파생본" 으로

Claude Code 플러그인 (marketplace + plugin.json + skills/hooks/MCP/bin) 은 현행
"clone → bootstrap → 수동 재적용" 의 소비자 마찰과 파생본 낡음 문제를 **자동
업데이트 채널**로 구조적으로 완화한다. 명령 3종·스킬·MCP 2-bundle 은 자연 이식.

- **핵심 갭**: CLAUDE.md 형 상시 규칙 주입이 플러그인에 없다 — 스킬은 호출형이라
  TASK-020 ("규칙을 안 받는 에이전트는 손으로 쓴다") 교훈과 충돌. SessionStart
  hook 주입 실측 전까지 bootstrap 의 CLAUDE.md 주입은 유지 (플러그인 = 보완 채널).
- **Python 제약**: 플러그인 자동 의존성 설치는 npm 만 — `wk` 는 uv 설치 전제 +
  부재 시 graceful 안내 패턴으로 시작.
- **아키텍처 원칙**: 플러그인 디렉터리는 렌더러(`render_claude_code_plugin`)가
  정본에서 생성하고 검사가 강제한다 — 손으로 만들면 §11 이전 세계로 회귀.
- 이행: Phase A (렌더러) → B (저장소 = marketplace) → C (실측 게이트: hook 주입
  실효 / MCP 승인 UX / wk 부재 graceful).
