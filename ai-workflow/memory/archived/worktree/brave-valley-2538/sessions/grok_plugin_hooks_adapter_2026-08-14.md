# Grok Build 플러그인 훅 어댑터 (2026-08-14)

- 문서 목적: TASK-012 구현과 재실측을 남긴다.
- 범위: `plugin_payload` 가 `hooks/hooks.json` 을 Claude 훅과 동일 사본으로 emit, SessionStart 탐침에 `GROK.md` 추가, §7.0 문서.
- 대상 독자: 다음 세션
- 상태: 완료
- 최종 수정일: 2026-08-14
- 관련 문서: [TASK-2026-08-14-main-012](../backlog/tasks/TASK-2026-08-14-main-012.md), [TASK-011 실측](./grok_plugin_load_probe_2026-08-14.md)

## 한 일

- `GROK_HOOKS_RELPATH = hooks/hooks.json` — `mcp.json` / `.mcp.json` 과 같은 규율로 Claude 훅과 동일 렌더러 출력.
- SessionStart 탐침에 `GROK.md` 와 `@AGENTS.md` in GROK.md 를 추가.
- `check_agent_plugin_payload` 18 → **19** (되주입 2종: GROK.md 제거 / 두 훅 파일 분기).
- INSTALLATION §7.0 + grok-build apply_guide §3.6 에 `grok plugin install … --trust`.

## 검증

- `check_agent_plugin_payload` 19/19
- `check_standard_single_source` 9/9 (`PYTHONPATH=workflow-source`)
- `check_docs` 72 files, apply-guide 4/4
- 격리 `GROK_HOME=/tmp/grok-plugin-probe-012`: validate 에 hooks, inspect `provides.hooks=true`, 스킬 4 + MCP 1

## 자기 적용 (live `~/.grok`)

`grok plugin install ./plugin --trust` — 사용자 홈에 설치됨.

- 경로: `~/.grok/installed-plugins/plugin-27e2648f` (v1.2.0, enabled)
- inspect: 스킬 4 + MCP `standardAiWorkflowReadOnly` + `provides.hooks=true`
- 예전 Claude 캐시(v1.1.8-beta, 스킬 3 / hooks false) 는 더 이상 inspect 에 안 잡힘
- 이 대화 세션은 설치 전에 열렸으므로 슬래시 스킬은 **세션을 다시 열거나** Plugins 탭에서 `r` 로 다시 읽어야 한다
