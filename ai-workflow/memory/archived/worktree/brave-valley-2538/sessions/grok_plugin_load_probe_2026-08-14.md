# Grok Build 플러그인 로드 실측 (2026-08-14)

- 문서 목적: `plugin/` payload 를 Grok Build 가 플러그인으로 설치·로드하는지 기록한다.
- 범위: 격리 `GROK_HOME` 설치, inspect/details 인벤토리, 중립 cwd, `hooks/hooks.json` 프로브. payload 변경 없음.
- 대상 독자: 다음 세션, 배포 정책 소유자
- 상태: 실측 완료
- 최종 수정일: 2026-08-14
- 관련 문서: [TASK-2026-08-14-main-011](../backlog/tasks/TASK-2026-08-14-main-011.md), [plugin-transition-plan-2026-08.md](../../../../../docs/planning/plugin-transition-plan-2026-08.md)

## 1. 방법

격리 홈: `GROK_HOME=/tmp/grok-plugin-probe-011`. 사용자 `~/.grok` 는 건드리지 않았다.

```bash
GROK_HOME=/tmp/grok-plugin-probe-011 grok plugin validate plugin
GROK_HOME=/tmp/grok-plugin-probe-011 grok plugin install ./plugin --trust
GROK_HOME=/tmp/grok-plugin-probe-011 grok plugin details standard-ai-workflow
GROK_HOME=/tmp/grok-plugin-probe-011 grok inspect --json
# 중립 소비 프로젝트
(cd /tmp/grok-plugin-probe-011/neutral-consumer && GROK_HOME=... grok inspect --json)
# 훅 관례 경로 프로브 (repo 밖 사본)
cp plugin/adapters/claude-code/hooks.json /tmp/.../hooks/hooks.json
```

## 2. 결과

| 항목 | 현재 `plugin/` | `hooks/hooks.json` 사본 |
|---|---|---|
| `grok plugin validate` | 통과 — skill dir 1, MCP, **hooks 없음** | 통과 — skill dir 1, MCP, **hooks** |
| `install --trust` | 성공, v1.2.0, enabled | 성공 |
| inspect `provides.skills` | **4** | 4 |
| inspect 스킬 로드 | `session-start` / `backlog-update` / `doc-sync` / `session-end` (`source.type=plugin`, `userInvocable=true`) | 동일 |
| inspect MCP | `standardAiWorkflowReadOnly` (`source.type=plugin`) | 동일 |
| inspect `provides.hooks` | **false** | **true** |
| 중립 cwd (프로젝트 파일 없음) | 스킬 4 + MCP 1 유지 | — |
| marketplace add 저장소 루트 | `.claude-plugin/marketplace.json` 로 소스 등록 성공 (`worktree-brave-valley-2538`) | — |

validate 의 "skill dir 1" 은 디렉터리 수다. 실제 로드 단위는 스킬 4개다. **validate 통과 ≠ 훅 로드**.

이 저장소 cwd 에서 inspect 하면 Claude 호환 프로젝트 스킬(`.claude/skills`, `.claude/commands`)과 플러그인 스킬이 **같이** 보인다. 소비 프로젝트(중립 cwd)에서는 플러그인 스킬만 남는다.

## 3. 판정

스킬 4종과 read-only MCP 는 **현재 payload 그대로 Grok 플러그인으로 성립**한다. SessionStart/SessionEnd 훅은 Grok 관례 경로 `hooks/hooks.json` 이 없어서 안 붙는다. 그 파일만 두면 `provides.hooks=true` 가 된다.

후속: 렌더러가 `hooks/hooks.json` 을 emit 하고 SessionStart 탐침에 `GROK.md` 를 넣는다. 실측 전에는 INSTALLATION §7.0 에 Grok 을 권장 경로로 올리지 않는다.
