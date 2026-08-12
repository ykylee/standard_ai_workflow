# 플러그인 배포 전환 계획 (Plugin Distribution Transition Plan)

- 문서 목적: 표준 AI 워크플로우의 배포 전략을 **플러그인 배포 중심**으로 전환하는 실행 계획 — 전환 원칙, 단계별 로드맵 (P1~P5), WBS, 완료 기준을 확정한다 (TASK-2026-08-12-main-013, 사용자 지시).
- 범위: TASK-011 (Claude Code 플러그인 검토) + TASK-012 (멀티 하네스 공유 검토) 의 권고를 실행 계획으로 통합. 구현은 본 계획의 WBS task 들 (TASK-014~018) 로 수행한다.
- 대상 독자: maintainer, 배포 정책 소유자, 구현 담당 AI agent
- 상태: 실행 중 — **P1 완료** (TASK-014, 2026-08-12), P2 착수 대기
- 최종 수정일: 2026-08-12
- 관련 문서: [plugin-distribution-review-2026-08.md](./plugin-distribution-review-2026-08.md), [multi-harness-plugin-review-2026-08.md](./multi-harness-plugin-review-2026-08.md), [cli-distribution-review-2026-08.md](./cli-distribution-review-2026-08.md), [workflow_kit_roadmap.md](../../workflow-source/core/workflow_kit_roadmap.md)

## 1. 전환 목표와 원칙

**목표**: 소비 프로젝트가 워크플로우를 얻는 주 경로를 "clone → bootstrap → 수동
재적용" 에서 **"플러그인 설치 1명령 + 자동 업데이트"** 로 바꾼다.

전환 원칙 5개 — 두 검토의 판정을 그대로 계승한다:

1. **플러그인은 파생본이다.** 플러그인 디렉터리 전체를 렌더러가 정본
   (`core/global_workflow_standard.md` §1·§3·§8·§11) 에서 생성하고
   `check_standard_single_source` 계열 검사가 강제한다. **손으로 만든 플러그인
   파일은 금지** — §11 이전의 "손 사본" 세계로 회귀하는 경로다.
2. **공유 payload + 하네스별 얇은 어댑터.** payload 물리 배치는 **Agent Plugins
   1.0 레이아웃** (`plugin.json` + `skills/` + `mcp.json`) 을 채택한다. 어댑터는
   payload 참조만 하는 얇은 manifest 로 유지해, 각 하네스가 표준에 합류하는
   순간 지울 수 있는 위치에 둔다.
3. **빅뱅 전환 금지 — 실측이 채널 전환을 결정한다.** CLAUDE.md 형 상시 규칙
   주입은 플러그인에 직접 대응물이 없다 (핵심 갭). SessionStart hook 주입 실효가
   실측으로 성립하기 전까지 **bootstrap 의 진입점 주입 아키텍처는 유지**하고,
   플러그인은 추가 채널로 도입한다. 기존 소비자의 경로는 전환 기간 중 깨지지 않는다.
4. **Python 실행 경로는 정직하게.** 플러그인은 `wk`/MCP 서버의 Python 의존을
   대신 설치해 주지 못한다 (자동 설치는 npm 만). 설치 전제 (uv/pipx + GH Release
   wheel) 를 문서화하고, hook 은 `wk` 부재 시 **조용히 실패하지 않고 안내**한다
   (graceful degradation — 조용한 fallback 금지 원칙).
5. **버전은 릴리스 절차와 동기.** plugin.json 의 version 은 `cmd_release` bump 의
   파생물 선재생성 목록에 들어간다 — 릴리스마다 손으로 맞추는 필드를 만들지 않는다.

## 2. 현행 → 목표 상태

| 층 | 현행 (v1.1.8) | 목표 (전환 완료 시) |
|---|---|---|
| 규칙 (§1·§3·§8·§11) | bootstrap 이 13 하네스 진입점에 주입 | **유지** + 플러그인 SessionStart hook 채널 (실측 성립 시 병행) |
| skills / commands | bootstrap 이 프로젝트에 파일 산출 (5 하네스 SKILL.md) | 공유 payload `skills/` (agentskills.io 스펙) 에서 파생 — 플러그인·bootstrap 양쪽이 같은 정본 소비 |
| MCP | bootstrap emit 7 방언 (.mcp.json 등) | payload `mcp.json` (Agent Plugins 스키마, read-only bundle) + 방언 emit 유지 |
| `wk` CLI | GH Release wheel + uv/pipx | **유지** (플러그인 범위 밖 — 설치 전제로 문서화) |
| 설치 | clone → bootstrap | `/plugin install standard-ai-workflow@<market>` (Claude Code) / `gemini extensions install` (Gemini) / `.agents/skills/` 마운트 (Codex·OpenCode·goose) |
| 갱신 | 재-bootstrap (수동) | marketplace 자동 업데이트 + semver pin |
| 상태 문서 (`ai-workflow/memory/`) | 프로젝트 저장소 소유 | **불변** (플러그인 범위 밖 — 올바름) |

## 3. 전환 로드맵 (P1 → P5)

의존 순서대로 실행한다. P1·P2 가 최소 성립 단위 (Claude Code 채널 개통),
P3 이 멀티 하네스 확장, P4 가 운영 통합, P5 가 전환 판정이다.

### P1 — 공유 payload 렌더러 (TASK-014)

`render_agent_plugin()` 신설: `plugin/` 디렉터리 (Agent Plugins 1.0 레이아웃)
전체를 정본에서 생성.

- `plugin.json` — name/version/description (version 은 `workflow_kit.__version__` 파생)
- `skills/` — session-start / backlog-update / doc-sync 3종 SKILL.md
  (agentskills.io 스펙 준수). §11 명령·계약 본문은 `render_memory_update_section()`
  / `find_memory_command()` 파생 — 손 사본 금지.
- `mcp.json` — Agent Plugins 스키마, read-only bundle 11 도구 (write 는 opt-in 문서)
- 검사: `check_standard_single_source` 계열 확장 (payload ↔ 정본 일치) +
  agentskills.io frontmatter 스키마 검사 + **되주입 FAIL 실증** (신설 검사 관행)

**P1 실행 결과 (2026-08-12, TASK-014)** — `workflow_kit/plugin_payload.py` +
`tests/check_agent_plugin_payload.py` (7 case). 계획과 달라진 점 하나:

- `plugin.json` 은 **name/version/description 3필드만** 쓴다. Agent Plugins 1.0
  (2026-08-06 출범) 의 선택 필드 스펙을 이 저장소가 아직 **원문으로 확인하지
  못했다** — 확인 안 된 필드를 지어 넣으면 스펙 확정 시 조용히 틀린 값이 된다.
  검사 case 4 가 필드 집합을 고정하므로, 필드를 늘리려면 그 검사가 먼저 FAIL
  한다 (§5 리스크 완화 "스키마를 fixture 로 고정" 의 구현). **스펙 확인 후
  필드 확장은 명시 task 로** — P2 자기 적용 때 실 클라이언트가 요구하는 필드가
  드러나면 거기서 확정한다.
- `mcp.json` 은 read-only bundle 서버 **하나만** 싣는다 (write 는 opt-in, ADR-003).
  `env` 에 `PYTHONPATH` 를 넣지 않는다 — 플러그인은 소비 프로젝트의 체크아웃
  구조를 모르고, `wk` 설치 전제가 깨지면 조용한 fallback 없이 드러나야 한다 (원칙 4).

### P2 — Claude Code 어댑터 + marketplace + 자기 적용 (TASK-015)

- 어댑터: `.claude-plugin/plugin.json` (payload 참조) + hooks
  (SessionStart 안내 / SessionEnd → `wk refresh-state`) + `.mcp.json`
- 저장소 루트 `marketplace.json` — 이 저장소 자체가 marketplace
  (`/plugin marketplace add ykylee/standard_ai_workflow`)
- **자기 적용**: 이 저장소에서 `/plugin install` 실측 — 스킬 네임스페이스
  (`/standard-ai-workflow:session-start`), hook 동작, MCP 승인 UX 기록
- `wk` 부재 시 graceful 안내 실측 (원칙 4)

### P3 — 멀티 하네스 어댑터 (TASK-016)

- gemini-cli: `gemini-extension.json` + GEMINI.md 컨텍스트 (**상시 주입 실측 포함**
  — 성립하면 Gemini 채널은 규칙 주입까지 완결되는 첫 사례)
- goose: config snippet (extension=MCP) / opencode: snippet + 스킬 마운트
- `.agents/skills/` 마운트 수렴 검토: Codex·OpenCode·goose 가 어댑터 없이 읽는
  경로 — bootstrap 스킬 emit 위치를 여기로 수렴할지 판정 (Claude Code 의
  `.agents/skills/` 판독 여부 실측 포함)

### P4 — 릴리스 파이프라인 통합 (TASK-017)

- `cmd_release` 파생물 선재생성 목록에 plugin payload + 어댑터 추가
  (bump → plugin.json version 자동 동기)
- dist 자산에 플러그인 포함 (release-dist), 배포 사본 날짜/버전 드리프트 검사 확장
- CI: 플러그인 산출물 정합 검사가 smoke 에 편입되어 있는지 확인 (P1 검사의 CI 편입 검증)

### P5 — 실측 게이트 + 채널 전환 판정 (TASK-018)

- 실측 3건 종합: ① Claude Code SessionStart hook 규칙 주입 실효
  ② Gemini GEMINI.md 상시 주입 (P3 에서 선행 실측) ③ marketplace 자동 업데이트 주기·UX
- INSTALLATION_AND_USAGE 갱신: 플러그인 설치를 **권장 경로**로 승격, bootstrap 은
  플러그인 미지원 하네스·오프라인용으로 재배치
- **소유자 판정**: 실측 결과에 따라 (a) 플러그인 = 주 채널 + bootstrap 병행 유지,
  또는 (b) 플러그인 = Claude Code/Gemini 한정 채널. 판정 근거를 본 문서에 기록.

## 4. WBS

| Task | Phase | 산출물 | 완료 기준 (검증 포함) | 의존 | 규모 |
|---|---|---|---|---|---|
| TASK-2026-08-12-main-013 | P0 | 본 계획 + 로드맵 갱신 + WBS task 등록 | 계획 문서 커밋 + 전량 2축 green | — | S |
| TASK-2026-08-12-main-014 | P1 | `render_agent_plugin()` + `plugin/` payload + 검사 확장 | payload 3축 (plugin.json/skills/mcp.json) 정본 파생 + 되주입 FAIL 실증 + 전량 2축 green | 013 | M |
| TASK-2026-08-12-main-015 | P2 | Claude Code 어댑터 + marketplace.json + 자기 적용 실측 | `/plugin install` 이 이 저장소에서 성립 (스킬 3종 호출 + SessionEnd hook + MCP 등록 실측 기록) + `wk` 부재 graceful 실측 | 014 | M |
| TASK-2026-08-12-main-016 | P3 | gemini-cli/goose/opencode 어댑터 + `.agents/skills/` 수렴 판정 | 어댑터 3장 렌더러 생성 + 검사 편입 + Gemini GEMINI.md 주입·Claude Code `.agents/skills/` 판독 실측 기록 | 014 | M |
| TASK-2026-08-12-main-017 | P4 | cmd_release 통합 (bump 동기 + dist 자산 + 드리프트 검사) | 릴리스 dry-run 에서 plugin version 자동 동기 확인 + 드리프트 검사 되주입 실증 | 014, 015 | S |
| TASK-2026-08-12-main-018 | P5 | 실측 종합 + INSTALLATION 개편 + 채널 전환 판정 기록 | 실측 3건 기록 + 문서 갱신 + 소유자 판정 본 문서 §3-P5 에 기록 | 015, 016, 017 | M |

규모: S = 1세션 내, M = 1~2세션. 015 와 016 은 014 완료 후 **병렬 가능**
(단 같은 워킹 트리 전량 검사 락 — 동시 진행 시 worktree 분리).

**다음 릴리스 (v1.1.9 또는 v1.2.0) 목표 범위**: P1+P2 (Claude Code 채널 개통) +
기존 예약분 (2nd cycle shim drop + `--bundle` 기본값 전환). P3~P5 는 그 다음
릴리스로 넘길 수 있다 — P2 까지만으로도 "플러그인 배포" 는 성립한다.

## 5. 리스크와 완화

| 리스크 | 완화 |
|---|---|
| SessionStart hook 주입이 실측에서 불성립 → 규칙 주입 갭 지속 | 원칙 3: bootstrap 주입 병행 유지가 기본값. 플러그인은 스킬/훅/MCP 채널로도 가치 성립 (P5 에서 (b) 판정) |
| 플러그인 산출물이 손 편집으로 오염 | P1 검사 강제 + 되주입 실증. `plugin/` 은 생성물 선언 (state.json 과 동일 지위) |
| plugin.json version 드리프트 (v1.1.7 stamp 누락 동형) | P4 에서 선재생성 목록 편입 + 드리프트 검사. "bump 후 전량" 관행 적용 |
| Agent Plugins 1.0 스키마 변동 (신생 표준) | 어댑터가 얇아 payload 재배치 비용 낮음. 스키마 버전을 검사 fixture 로 고정하고 갱신은 명시 task 로 |
| 스킬 이중 배포 (bootstrap 산출 + 플러그인) 시 동명 충돌 | 플러그인 스킬은 네임스페이스 (`/standard-ai-workflow:*`) 로 분리. P2 자기 적용에서 공존 동작 실측 |
| Python 의존 자동 설치 부재로 첫 실행 실패 | 원칙 4: hook 이 부재 감지 시 설치 명령 안내. 조용한 실패 경로 금지 |

## 6. 전환 완료의 정의

아래 4개가 전부 성립하면 본 전환을 완료로 판정한다:

1. `plugin/` payload 와 어댑터 전부가 렌더러 생성물이고 검사가 정본 일치를 강제한다 (P1~P3).
2. 이 저장소가 자기 자신을 플러그인으로 설치해 쓰고 있다 — 자기 적용 (P2).
3. 릴리스 절차가 플러그인 버전·자산을 자동 동기한다 (P4).
4. INSTALLATION 이 플러그인을 권장 경로로 안내하고, 채널 전환 판정 (a/b) 이 기록돼 있다 (P5).
