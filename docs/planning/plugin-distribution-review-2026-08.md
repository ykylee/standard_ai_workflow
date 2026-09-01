# 워크플로우 플러그인 형태 재구성·배포 검토

- 문서 목적: 표준 AI 워크플로우를 Claude Code **플러그인**으로 재구성해 배포하는 방안의 구조·장단·이행 경로를 검토한다 (TASK-2026-08-12-main-011, 사용자 지시).
- 범위: Claude Code 플러그인 시스템 (v2.1.223+ 공식 문서 기준) ↔ 현행 배포 모델 매핑, 제약, 권고
- 대상 독자: maintainer, 배포 정책 소유자
- 상태: 검토 완료 — 권고안 제시 (구현은 후속 task)
- 최종 수정일: 2026-09-01
- 관련 문서: [`cli-distribution-review-2026-08.md`](./cli-distribution-review-2026-08.md), `workflow-source/core/workflow_harness_distribution.md`, ADR-003

## 1. 현행 배포 모델 (v1.1.8 기준)

| 층 | 배포 수단 |
|---|---|
| 규칙 (정본 §1·§3·§8·§11) | bootstrap 이 하네스 진입점 파일에 **주입** (CLAUDE.md 등 13 하네스, `check_standard_single_source` 강제) |
| claude-code overlay | `CLAUDE.md` + `.claude/commands/workflow-*.md` 3종 + `.claude/skills/standard-ai-workflow/SKILL.md` — bootstrap 이 **프로젝트에 파일로 산출** |
| 실행 경로 (`wk` 72명령) | pip/uv wheel (GitHub Releases) |
| MCP | `.mcp.json` 2-server (read-only / write bundle) — bootstrap emit |
| 갱신 | 재-bootstrap (수동) — **자동 업데이트 채널 없음** |

## 2. Claude Code 플러그인 모델 요약 (공식 문서 조사, 2026-08)

- 구조: `.claude-plugin/plugin.json` (name/version/dependencies/userConfig …) + `skills/` `commands/` `agents/` `hooks/hooks.json` `.mcp.json` `bin/` `scripts/`.
- **배포·업데이트**: marketplace (`marketplace.json` — GitHub repo 로 서빙 가능) → `/plugin install name@market`, 자동 업데이트 (세션 시작 후 백그라운드), semver pin.
- **팀 배포**: 프로젝트 `.claude/settings.json` 의 `enabledPlugins` + `extraKnownMarketplaces` — 저장소가 기여자에게 플러그인을 권고/자동 활성.
- 스킬 네임스페이스: `/plugin-name:skill-name` (충돌 원천 차단).
- hooks: SessionStart/SessionEnd 포함 29 이벤트, `${CLAUDE_PLUGIN_ROOT}`(캐시, 휘발) / `${CLAUDE_PLUGIN_DATA}`(영속) 경로 변수.
- MCP: 플러그인 `.mcp.json` 으로 임의 명령 서버 등록 (project-scope 는 서버별 승인 게이트 유지).
- `bin/`: PATH 에 추가되는 실행물 동봉 가능.

## 3. 매핑 — 현행 claude-code 산출물 → 플러그인 컴포넌트

| 현행 | 플러그인 | 판정 |
|---|---|---|
| `.claude/commands/workflow-*.md` 3종 | `skills/` (→ `/standard-ai-workflow:session-start` 등) | **자연 이식** — 네임스페이스 개선 |
| `.claude/skills/standard-ai-workflow/SKILL.md` | `skills/` | 자연 이식 |
| `.mcp.json` (RO/write bundle) | 플러그인 `.mcp.json` | 이식 가능 — 단 §4-②(Python 전제) |
| **CLAUDE.md 규칙 블록 (§1·§3·§8·§11 상시 주입)** | **직접 대응물 없음** — 플러그인은 CLAUDE.md 형 상시 컨텍스트 주입 불가 | **핵심 갭** — SessionStart hook (`prompt`/`command` 로 컨텍스트 emit) 또는 스킬 안내로 우회, 실효는 실측 필요 |
| (없음 — goose 만 있던) 세션 종료 자동화 | `hooks/hooks.json`: SessionEnd → `wk refresh-state` | **플러그인이 더 강함** — §11 종료 절차의 자동화 |
| `wk` CLI | `bin/` wrapper 또는 hook 부트스트랩 | §4-② |
| 상태 문서 (`ai-workflow/memory/`) | 해당 없음 — 프로젝트 저장소 소유 | 플러그인 범위 밖 (올바름) |

## 4. 제약·리스크 (중요도순)

1. **CLAUDE.md 상시 주입 불가.** 우리 아키텍처의 축은 "진입 규칙이 매 세션 자동
   로드" 인데, 플러그인 스킬은 **호출형**이다. TASK-020 의 교훈 그대로 — 규칙을
   안 읽는 에이전트는 손으로 쓴다. 우회는 SessionStart hook 의 컨텍스트 emit 인데
   공식 지원 형태가 아니라 **실측 검증이 선행**돼야 한다. 실측 전까지 플러그인은
   CLAUDE.md 를 **대체하지 않고 보완**한다 (bootstrap 의 CLAUDE.md 주입 유지).
2. **Python 배포는 플러그인이 대신 못 해 준다.** 자동 의존성 설치는 Node
   (`npm ci`) 만. `wk`/MCP 서버는 `workflow_kit` 이 필요 → 두 패턴: (a) SessionStart
   hook 이 `${CLAUDE_PLUGIN_DATA}` 에 `uv tool install <wheel URL>` 부트스트랩,
   (b) 설치 전제 문서화 + hook 은 부재 시 안내만 (graceful). (b) 로 시작 권고 —
   (a) 는 조용한 네트워크 설치라 신뢰 문제.
3. **Claude Code 전용 채널이다.** 13 하네스 중 1개. 기존 "정본 하나 + 하네스별
   파생본" 아키텍처에서 플러그인은 **claude-code 파생본의 새 배포 채널**로
   위치시켜야 하며 (렌더러가 생성 + 검사 강제), 아키텍처 대체가 아니다. 플러그인
   디렉터리를 손으로 만들면 §11 이전의 "손 사본" 세계로 회귀한다.
4. `${CLAUDE_PLUGIN_ROOT}` 는 업데이트마다 바뀌는 캐시 — 상태를 거기 두면 안 된다
   (상태는 프로젝트 저장소, 영속 데이터는 `${CLAUDE_PLUGIN_DATA}`).

## 5. 얻는 것

- **설치 1명령 + 자동 업데이트**: `/plugin install standard-ai-workflow@<market>` —
  현행 "clone → bootstrap → 수동 재적용" 대비 소비자 마찰 대폭 감소, 파생본 낡음
  문제 (우리가 §11 검사로 싸워 온 것) 를 **업데이트 채널로 구조적으로 완화**.
- 프로젝트 `.claude/settings.json` 로 **팀 단위 권고/자동 활성** — 저장소가
  기여자의 도구를 선언하는 정공법.
- 스킬 네임스페이스·버전 pin·의존 선언 — 배포물의 계약화.
- SessionEnd hook 으로 **§11 종료 절차 자동화** (goose 에만 있던 것을 claude-code 에).

## 6. 권고안 — 채택 (단, "14번째 파생본" 으로)

**Phase A (구현 task 후보)**: 렌더러에 `render_claude_code_plugin()` 신설 —
플러그인 디렉터리 전체를 **정본에서 생성** (`plugin.json` + skills 3종 + hooks
(SessionStart 안내 / SessionEnd → `wk refresh-state`) + `.mcp.json` RO bundle).
`check_standard_single_source` 계열이 플러그인 산출물도 판정. 산출 위치:
`dist/plugins/standard-ai-workflow/` (릴리스 자산) 또는 저장소 내 `plugin/`.

**Phase B**: 저장소 루트에 `marketplace.json` 커밋 → 이 저장소 자체가 marketplace
(`/plugin marketplace add ykylee/standard_ai_workflow`). 버전은 릴리스 절차의
bump 와 동기 (파생물 선재생성 목록에 plugin.json 추가).

**Phase C (실측 게이트)**: ① SessionStart hook 의 규칙 주입 실효 실측 — 성립하면
CLAUDE.md 의존을 낮출 수 있고, 안 되면 플러그인은 명령/스킬/MCP/훅 채널로 확정.
② project-scope MCP 승인 UX ③ `wk` 부재 시 graceful 안내.

**하지 않는 것**: bootstrap/CLAUDE.md 주입 아키텍처의 대체 (플러그인은 추가 채널),
다른 12 하네스의 플러그인화 (각자 생태계가 다름 — 필요 시 개별 검토).

## 7. 미확정 (실측 필요)

- SessionStart hook 로 상시 규칙 주입이 실제로 컨텍스트에 남는가 (Phase C-①).
- marketplace 자동 업데이트가 프로젝트 스코프에서 도는 주기·UX.
- 플러그인 스킬과 기존 `.claude/skills` 동명 공존 시 동작 (문서상 override 불가).
