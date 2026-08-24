# 플러그인 배포 전환 계획 (Plugin Distribution Transition Plan)

- 문서 목적: 표준 AI 워크플로우의 배포 전략을 **플러그인 배포 중심**으로 전환하는 실행 계획 — 전환 원칙, 단계별 로드맵 (P1~P5), WBS, 완료 기준을 확정한다 (TASK-2026-08-12-main-013, 사용자 지시).
- 범위: TASK-011 (Claude Code 플러그인 검토) + TASK-012 (멀티 하네스 공유 검토) 의 권고를 실행 계획으로 통합. 구현은 본 계획의 WBS task 들 (TASK-014~018) 로 수행한다.
- 대상 독자: maintainer, 배포 정책 소유자, 구현 담당 AI agent
- 상태: **완료 — P1~P5 전부 종료, 전환 완료 판정 (§6-보론)** (TASK-014~018, 2026-08-12~13)
- 최종 수정일: 2026-08-24
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
5. **버전은 릴리스 절차와 동기.** plugin.json 의 version 이 pyproject 와 어긋나면
   **릴리스 게이트가 막는다** (`release-doctor`) — 릴리스마다 손으로 확인하는 필드를
   만들지 않는다. *(P4 실측으로 "bump 가 자동 재생성" → "게이트가 강제" 로 정정.
   근거는 §3-P4 실행 결과 2-1.)*

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

**P2 실행 결과 (2026-08-12, TASK-015)** — `claude plugin` CLI 로 실측했다.
계획이 실측에 두 번 고쳐졌다:

1. **어댑터를 하위 디렉터리에 둘 수 없다.** `plugin/adapters/claude-code/` 를
   플러그인 루트로 삼고 payload 를 `../../skills` 로 참조하는 배치는
   `claude plugin validate` 가 거부한다 — *"Path contains '..' which could be a
   path traversal attempt"*. 그래서 **플러그인 루트 = payload 루트**로 두고,
   Claude Code 의 관례 경로(`skills/`)가 payload 배치와 그대로 겹치게 했다.
   결과적으로 어댑터는 manifest + hooks **두 장**으로 줄었다 (계획이 예상한
   "정말 얇은 어댑터" 가 더 얇아진 셈).
2. **validate 통과는 로드 증명이 아니다.** manifest 에
   `"mcpServers": "./mcp.json"` 을 선언하면 `validate --strict` 는 통과하는데,
   `claude plugin details` 의 인벤토리는 **`MCP servers (0)`** 이었다. 관례 경로
   `.mcp.json` 으로 옮기자 `MCP servers (1)` 로 잡혔다. payload 의 `mcp.json` 과
   같은 렌더러 출력을 두 이름으로 둔다 (정본이 하나라 갈라지지 않고, 검사
   case 8 이 두 파일의 동일성을 강제한다).

실측 기록:

| 항목 | 결과 |
|---|---|
| `claude plugin validate --strict plugin` | ✔ passed |
| `claude plugin validate --strict .` (marketplace) | ✔ passed |
| `claude --plugin-dir plugin plugin details` | Skills **3** / Hooks **2** (SessionStart·SessionEnd) / MCP servers **1** |
| always-on 토큰 비용 | ~92 tok (스킬 3종 각 ~30, 호출 시 270~350) |

> 이 표는 **P2 시점(TASK-015)의 기록**이다. 이후 `session-end` 가 추가되어 현재는
> Skills **4** / always-on ~121 tok 이다 (TASK-020, 아래 P4 절 참조).
| `wk` 부재 graceful | 두 hook 모두 안내 출력 + exit 0 — 조용한 실패 없음 |
| **자기 적용** `claude plugin marketplace add ./` | ✔ `standard-ai-workflow` (user settings 선언) |
| **자기 적용** `claude plugin install standard-ai-workflow@standard-ai-workflow` | ✔ scope user, **enabled**, v1.1.8-beta — 설치본 인벤토리도 3/2/1 동일 |

`plugin.json` 의 `v1.1.8-beta` 형식도 Claude Code 가 수용한다 (semver 강제 없음).
`marketplace add` 의 경로 인자는 `.` 을 거부한다 — `./` 또는 절대 경로여야 한다
(*"Invalid marketplace source format. Try: owner/repo, https://..., or ./path"*).

**P2 잔여 실측 (2026-08-12, 26차 세션에서 확인)** — 설치 다음 세션에서 전부 성립했다.
이 세션 자체가 설치본으로 열렸다:

| 항목 | 결과 |
|---|---|
| 스킬 네임스페이스 `/standard-ai-workflow:session-start` | ✔ 호출 성립 — 이 세션이 그 경로로 시작했다 |
| MCP 승인 UX | ✔ 별도 승인 프롬프트 없이 로드 (read-only 12 + write 2 도구) |
| SessionStart hook 실효 | ✔ `wk` 부재를 세션 시작 시 안내, 세션은 중단되지 않음 (graceful) |
| 플러그인 `<plugin>/bin` PATH 주입 | ⚠ 호스트가 `<plugin>/bin` 을 PATH 에 넣지만 payload 에 `bin/` 이 **없다** |

마지막 항목이 P3·P4 설계에 걸린다: 호스트가 이미 **플러그인이 실행 파일을 배포할
자리**를 열어 두고 있는데 payload 가 비워 두고 있다. `wk` 부재 graceful 경로를
타는 근본 원인이기도 하다 (원칙 4 는 "설치를 대신 못 해 준다" 였는데, 이 통로가
있으면 전제가 달라진다). **실측만 기록하고 판정은 P3 으로 넘긴다** — payload 에
바이너리를 싣는 것은 "플러그인은 파생본" 원칙과 Python 의존 전제를 함께 건드린다.

규칙 상시 주입(SessionStart hook) 의 *실효* 판정은 원래대로 P5 항목이다.

### P3 — 멀티 하네스 어댑터 (TASK-016)

- gemini-cli: `gemini-extension.json` + GEMINI.md 컨텍스트 (**상시 주입 실측 포함**
  — 성립하면 Gemini 채널은 규칙 주입까지 완결되는 첫 사례)
- goose: config snippet (extension=MCP) / opencode: snippet + 스킬 마운트
- `.agents/skills/` 마운트 수렴 검토: Codex·OpenCode·goose 가 어댑터 없이 읽는
  경로 — bootstrap 스킬 emit 위치를 여기로 수렴할지 판정 (Claude Code 의
  `.agents/skills/` 판독 여부 실측 포함)

**P3 실행 결과 (2026-08-13, TASK-016)** — 어댑터 3장 전부 렌더러 생성물로 편입,
검사 13 → **15 case** (되주입 3종 실증: contextFileName 오염 / OpenCode 방언 키
오염 / GEMINI.md 규칙 블록 제거). 실측이 계획을 두 번, bootstrap 을 한 번 고쳤다.

1. **Gemini 도 확장 루트 = payload 루트다.** gemini 0.42.0 실측
   (`extensions new` 보일러플레이트 → `validate` → `link` → `list` 인벤토리):
   확장 루트의 `skills/` 관례 경로를 무변환으로 읽어 **payload 스킬 4종이 그대로
   인벤토리에 잡혔다.** 어댑터를 하위 디렉터리에 두면 이 공유가 깨진다 — Claude
   Code 와 정확히 같은 결론, 다른 이유 (path traversal 거부가 아니라 관례 경로
   공유). manifest 는 `plugin/gemini-extension.json` 5필드
   (name/version/description/contextFileName/mcpServers — validate 실측 확정,
   mcpServers 는 manifest 안 인라인), 컨텍스트는 `plugin/GEMINI.md` 로
   `render_entrypoint_rules` 파생 — bootstrap 진입점 주입과 **같은 파생 함수**라
   채널이 둘이어도 정본은 하나다. 자기 적용: 이 저장소의 `plugin/` 을
   `gemini extensions link` 로 등록, Context file + MCP + 스킬 4종 로드 확인.
2. **GEMINI.md 상시 주입의 "모델 주입 계층" 은 실측 불가로 남았다.** 인벤토리의
   Context files 등록(로드 계층)까지는 성립했지만, headless 모델 호출이
   `IneligibleTierError` (free tier 의 gemini-cli 클라이언트 지원 종료 — Antigravity
   이전 안내) 로 차단됐다. **로드 성립만 기록하고 주입 실효 판정은 P5 게이트 ②
   그대로 연다** — 실행 못 한 검사는 통과가 아니다.
3. **`.agents/skills/` 수렴 판정: 수렴하지 않는다.** Claude Code 2.1.229 실측 —
   임시 프로젝트에 `.agents/skills/` 와 `.claude/skills/` 프로브 스킬을 나란히
   심고 headless 로 물었더니 **`.claude/skills/` 쪽만 보였다.** 바이너리 문자열
   교차 확인도 같은 방향 (`.claude/skills` 73건, `.agents/skills` 0건). 즉
   bootstrap 스킬 emit 을 `.agents/skills/` 하나로 수렴하면 Claude Code 채널이
   빠진다. Codex·OpenCode·goose 용 **추가** emit 위치로의 도입은 가치가 남지만
   (3 하네스가 어댑터 없이 읽는다) 그건 bootstrap 쪽 별건이다.
4. **OpenCode 실측이 bootstrap 방언을 반증했다.** snippet 을 bootstrap 의
   `render_opencode_mcp_config` 형태(문자열 `command` + `args` 분리, `env`)로
   만들었더니 opencode 1.17.12 가 **거부했다** — *"Expected array"* / *"Missing key
   enabled"*. 실측 확정 형태는 `command` **배열 전체** + `enabled` 필수 + env 키
   `environment` 이고, 그 형태로 `opencode mcp list` 가 서버 **connected** 까지
   보고했다 (validate 가 아니라 로드 실측). bootstrap 방언 결함은 별건
   [TASK-2026-08-13-main-002] — 그 emit 을 따라한 사용자는 서버를 못 본다.
5. **goose 는 실기 검증 미완이다** (이 환경에 goose CLI 부재). snippet 은 공식
   문서 스키마로 작성하고, **미완 표기를 snippet 주석과 검사(case 15)가 강제한다**
   — 검증 안 된 산출물이 검증된 얼굴을 하면 안 된다.
6. **`<plugin>/bin` 판정 (P2 잔여): 싣지 않는다.** 호스트가 PATH 에 넣어 주는
   자리지만, shim 이 해소하는 폭은 "PATH 에 없지만 `workflow_kit` 은 import 되는"
   좁은 틈뿐이고 Python 의존 자체는 여전히 해소하지 못한다 (원칙 4 의 전제 유지).
   잘못 실리면 실제 설치본을 가리는 그림자 경로가 되고, Windows 등 타 플랫폼
   shim 을 검증할 수단도 없다. `wk` 부재 graceful 안내(SessionStart hook)가 이미
   그 틈을 사용자에게 드러낸다. 설치 마찰 실측이 쌓이면 명시 task 로 재론한다.
7. Claude Code 채널 무영향 확인 — 새 파일 4장이 실린 뒤에도
   `claude plugin validate --strict` 통과 + 인벤토리 Skills 4 / Hooks 2 /
   MCP servers 1 동일. gemini-extension.json 이 버전 넷째 장으로 합류해
   릴리스 게이트(case 10·11, `release-doctor`)가 4장을 본다.

### P4 — 릴리스 파이프라인 통합 (TASK-017)

- `cmd_release` 파생물 선재생성 목록에 plugin payload + 어댑터 추가
  (bump → plugin.json version 자동 동기)
- dist 자산에 플러그인 포함 (release-dist), 배포 사본 날짜/버전 드리프트 검사 확장
- CI: 플러그인 산출물 정합 검사가 smoke 에 편입되어 있는지 확인 (P1 검사의 CI 편입 검증)

**P4 실행 결과 (2026-08-12, TASK-017)** — 계획이 예측한 리스크가 실재했고,
예측한 것보다 한 겹 깊은 곳에 있었다.

1. **버전이 두 겹으로 굳어 있었다.** `workflow_kit.__version__` 은 import 시점에
   pyproject 를 1회 파싱하고, 렌더러의 `version: str = KIT_VERSION` **기본 인자는
   함수 정의 시점**에 그 값으로 고정된다. 그래서 bump 를 파이프라인에 편입하는
   순간 — 즉 한 프로세스에서 bump 후 재생성하는 순간 — **낡은 버전이 조용히
   박힌다.** 실측으로 확인했다 (`__version__` 을 바꿔도 재생성 결과는 bump 이전 값).
   기존 검사는 매번 새 프로세스라 이 자리를 **영영 못 잡는다**. `current_kit_version()`
   (호출 시점 조회) 으로 뿌리를 없앤 뒤에 파이프라인을 붙였다.
2. **bump 경로는 하나가 아니라 셋이다** — `cmd_version_bump` / auto-bump /
   full-auto. 하나만 빠져도 *그 경로로 낸 릴리스만* 낡는다. 셋 전부에서 정합을
   보고하고, 검사가 각 bump 호출 뒤 12줄 안에 보고 호출이 있는지 강제한다.

2-1. **자동 재생성은 하지 않는다 (소유자 판정, 2026-08-12).** 처음에는 bump 가 곧바로
   `plugin/` 을 재생성하게 짰는데, 그 설계가 이 저장소와 정면으로 충돌했다. 릴리스
   검사 여럿이 **원본 저장소에서 bump 를 apply 한 뒤 되돌리는데** (실측:
   `pyproject.toml` 이 1.1.8 → 1.1.9 → 1.1.8 로 **86ms 만에 왕복**), 그 복원 로직은
   플러그인 산출물을 모른다 — pyproject 는 제자리로 오는데 **manifest 3장만 낡은 채
   남아** 전량 검사가 매번 FAIL 했다. 그래서 `state.json` 과 **같은 규율**로 바꿨다:
   생성물은 사람이 명령(`python3 -m workflow_kit.plugin_payload --apply`)으로
   재생성하고, **게이트가 정합을 강제한다** — `release-doctor` 의 6번째 source 로
   편입했고, 어긋나면 `fix` 필드에 그 명령이 담긴 채 `ok=False` 가 된다.
   파이프라인이 플러그인을 **쓰지 않는다는 것 자체**를 검사 case 11 이 고정한다
   (소스에 `write_repo_plugin_files` 가 있으면 FAIL).

   여기서 얻은 것: **bump 에 파일 쓰기 부수효과를 붙이면, 그 bump 를 원본에서
   돌리는 모든 검사가 잠재적 오염원이 된다.** 원본 bump 검사들을 sandbox 로 옮기는
   일은 별건으로 남는다 (`_repo_sandbox` 가 이미 그 방향으로 만들어졌다).
3. **dist 자산 포함은 하지 않는다 (판정).** wheel/sdist 는 importable 코드만 싣는
   것이 이 저장소의 방침이고 (`pyproject` 주석), non-code asset 이 실린다고 착각한
   주석 때문에 v1.1.7 에 실제 사고가 났다 (skill 스크립트가 소비자에게 실행 경로
   없이 남음). 게다가 marketplace 설치 경로는 git (`owner/repo` 또는 `./path`) 이라
   **wheel 자산을 보지 않는다** — 넣으면 아무도 안 읽는 14번째 사본이 하나 더 는다.
   릴리스와 플러그인을 잇는 것은 자산이 아니라 **버전 동기**이고, 그건 위 1·2 와
   case 4·9·10·11 이 담당한다.
4. **CI 편입은 이미 되어 있었다** — 전량 runner 가 `tests/check_*.py` 를 glob 으로
   발견하므로 (`discover_checks`) 신설 검사는 자동으로 smoke 와 CI 2축에 들어간다.

`check_agent_plugin_payload` 9 → **12 case** (10·11 은 위 1·2, 12 는 아래 P4+ 참조).

**P4 에서 파생된 발견 (TASK-020)** — payload 에 `session-end` 스킬이 추가되면서
(사용자 지시), 실측이 결함 하나를 더 드러냈다: `claude plugin details` 인벤토리는
`Skills (4)` 인데 **바로 위에 뜨는 플러그인 설명은 "스킬 3종"** 이었다. 개수를 손으로
적어 둔 사본이라 스킬을 늘릴 때 갈라진다 — §11.1 명령 사본 7곳, MCP 도구 목록이
13 중 10 에서 멈춰 있던 사본과 같은 계열이고, **사용자에게 가장 먼저 보이는 문장인데
아무 검사도 보고 있지 않았다.** `len(PLUGIN_SKILLS)` 파생으로 바꾸고 case 12 로 고정.

스킬 4종은 정본 §11.1 의 명령 4개와 1:1 대응한다 — 그 전까지 `wk refresh-state`
하나만 대응 스킬 없이 남아 있었다 (하네스가 세션 종료 단계를 밟을 방법을 몰랐다).

### P5 — 실측 게이트 + 채널 전환 판정 (TASK-018)

- 실측 3건 종합: ① Claude Code SessionStart hook 규칙 주입 실효
  ② Gemini GEMINI.md 상시 주입 (P3 에서 선행 실측) ③ marketplace 자동 업데이트 주기·UX
- INSTALLATION_AND_USAGE 갱신: 플러그인 설치를 **권장 경로**로 승격, bootstrap 은
  플러그인 미지원 하네스·오프라인용으로 재배치
- **소유자 판정**: 실측 결과에 따라 (a) 플러그인 = 주 채널 + bootstrap 병행 유지,
  또는 (b) 플러그인 = Claude Code/Gemini 한정 채널. 판정 근거를 본 문서에 기록.

**P5 실행 결과 (2026-08-13, TASK-018)** — 실측 3건과 판정:

| 실측 | 결과 |
|---|---|
| ① SessionStart hook 규칙 주입 실효 | ✔ **성립** — 프로브 플러그인의 SessionStart hook 이 echo 한 마커를 headless 모델이 그대로 반환했다 (claude 2.1.229, 중립 디렉터리). hook stdout 은 모델 컨텍스트에 실제로 주입된다 — 원칙 3 이 열어 둔 "CLAUDE.md 형 상시 주입 갭" 을 플러그인 채널이 메울 수 있다 |
| ② Gemini GEMINI.md 상시 주입 | **로드 계층 성립 / 모델 주입 계층 미검증** — P3 의 `IneligibleTierError` 차단 그대로. 판정에는 로드 실측만 반영하고, 모델 계층은 tier 해소 후 별도 확인 항목으로 남긴다 |
| ③ marketplace 업데이트 UX | ✔ 수동 흐름 성립 — `claude plugin marketplace update <name>` (source 재검증) + `claude plugin update <name>@<marketplace>` (**풀 id 필수** — 이름만 주면 not found, 실측). 최신이면 "already at the latest version" 버전 비교, 적용은 재시작 후 |

**부수 발견 — 설치 선언 소실 사고 (지속성 리스크).** P2 에서 성립시킨 자기 적용
선언(user settings 의 `extraKnownMarketplaces` / `enabledPlugins`)이 이 세션
시작 시점에 **통째로 사라져 있었다** (marketplace 목록에 official 만 남음).
settings.json 이 외부 도구에 의해 재작성된 것으로 추정되나 원인 미확정. 재설치
(marketplace add + install) 로 복구했고, 소비자 문서(§7.0)에 재설치 명령과 이
리스크를 명시했다 — 설치 선언이 settings.json 에 사는 한 같은 계열 소실이 재발할
수 있다.

**소유자 판정 (2026-08-13): (a) 플러그인 = 주 채널 승격 + bootstrap 병행 유지.**
근거: ①의 성립으로 원칙 3 이 걸어 둔 전제(hook 주입 실효)가 채워졌고, 자기
적용·업데이트 흐름이 실측으로 성립한다. bootstrap 은 (1) 진입점 파일 규칙 상시
주입 (2) 플러그인 미지원 하네스 (3) 오프라인 환경 담당으로 병행 유지 — 기존
소비자 경로는 깨지지 않는다 (원칙 3). `INSTALLATION_AND_USAGE.md` §7.0 이
플러그인을 권장 경로로 안내한다.

hook 에 규칙 블록(`render_entrypoint_rules`)을 실제로 싣는 것은 별건
[TASK-2026-08-13-main-003] 으로 넘긴다 — 진입점 파일에 규칙 블록이 이미 있는
프로젝트(이 저장소 포함)에서 이중 주입이 되므로, **조건부 주입**(진입점 규칙
블록 감지 시 생략) 설계가 선행돼야 한다.

## 6-보론. 전환 완료 판정 (2026-08-13)

§6 의 4개 조건이 전부 성립했다:

1. ✔ payload + 어댑터 전부 렌더러 생성물 + 검사 15 case 강제 (P1~P3)
2. ✔ 자기 적용 — 이 저장소가 자신을 플러그인으로 설치해 쓰고 있다 (P2, P5 재설치 포함)
3. ✔ 릴리스 게이트가 버전 4장 정합을 강제한다 (P4, release-doctor 6번째 source)
4. ✔ INSTALLATION §7.0 권장 경로 승격 + 채널 전환 판정 (a) 기록 (P5)

**본 전환 계획은 완료로 판정한다.** 잔여는 계획 밖 후속 task 로 관리한다:
Gemini 모델 주입 계층 실측 (tier 해소 후) / goose 실기 검증 (goose 가용 환경) /
hook 조건부 규칙 주입 [TASK-2026-08-13-main-003] / bootstrap OpenCode 방언
[TASK-2026-08-13-main-002] / 원본 bump 검사 sandbox 이관 [TASK-2026-08-13-main-001].

## 4. WBS

| Task | Phase | 산출물 | 완료 기준 (검증 포함) | 의존 | 규모 |
|---|---|---|---|---|---|
| TASK-2026-08-12-main-013 | P0 | 본 계획 + 로드맵 갱신 + WBS task 등록 | 계획 문서 커밋 + 전량 2축 green | — | S |
| TASK-2026-08-12-main-014 | P1 | `render_agent_plugin()` + `plugin/` payload + 검사 확장 | payload 3축 (plugin.json/skills/mcp.json) 정본 파생 + 되주입 FAIL 실증 + 전량 2축 green | 013 | M |
| TASK-2026-08-12-main-015 | P2 | Claude Code 어댑터 + marketplace.json + 자기 적용 실측 | `/plugin install` 이 이 저장소에서 성립 (스킬 3종 호출 + SessionEnd hook + MCP 등록 실측 기록) + `wk` 부재 graceful 실측 | 014 | M |
| TASK-2026-08-12-main-016 ✅ | P3 | gemini-cli/goose/opencode 어댑터 + `.agents/skills/` 수렴 판정 | ✅ 어댑터 3장 렌더러 편입 (검사 15 case) + Gemini 로드 실측 (모델 주입 계층은 P5 이월) + `.agents/skills/` **비수렴 판정** (Claude Code 미판독 실측) | 014 | M |
| TASK-2026-08-12-main-017 ✅ | P4 | cmd_release 통합 (bump 정합 보고 + 릴리스 게이트 + 드리프트 검사) | ✅ bump 3경로가 정합 보고 + `release-doctor` 가 어긋남을 `ok=False` 로 차단 + 되주입 실증 3종 (dist 자산은 **미포함 판정**) | 014, 015 | S |
| TASK-2026-08-12-main-018 ✅ | P5 | 실측 종합 + INSTALLATION 개편 + 채널 전환 판정 기록 | ✅ 실측 3건 기록 (hook 주입 **성립** / Gemini 모델 계층 미검증 명시 / 업데이트 흐름) + INSTALLATION §7.0 승격 + 판정 **(a)** §3-P5 기록 + 전환 완료 판정 §6-보론 | 015, 016, 017 | M |

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
| plugin.json version 드리프트 (v1.1.7 stamp 누락 동형) | ✅ P4 완료 — `release-doctor` 6번째 source 가 어긋남을 `ok=False` 로 막고 `fix` 명령을 낸다. 자동 재생성은 **하지 않는다** (§3-P4 실행 결과 2-1) |
| Agent Plugins 1.0 스키마 변동 (신생 표준) | 어댑터가 얇아 payload 재배치 비용 낮음. 스키마 버전을 검사 fixture 로 고정하고 갱신은 명시 task 로 |
| 스킬 이중 배포 (bootstrap 산출 + 플러그인) 시 동명 충돌 | 플러그인 스킬은 네임스페이스 (`/standard-ai-workflow:*`) 로 분리. P2 자기 적용에서 공존 동작 실측 |
| Python 의존 자동 설치 부재로 첫 실행 실패 | 원칙 4: hook 이 부재 감지 시 설치 명령 안내. 조용한 실패 경로 금지 |

## 6. 전환 완료의 정의

아래 4개가 전부 성립하면 본 전환을 완료로 판정한다:

1. `plugin/` payload 와 어댑터 전부가 렌더러 생성물이고 검사가 정본 일치를 강제한다 (P1~P3).
2. 이 저장소가 자기 자신을 플러그인으로 설치해 쓰고 있다 — 자기 적용 (P2).
3. 릴리스 절차가 플러그인 버전 정합을 **게이트로 강제**한다 (P4).
4. INSTALLATION 이 플러그인을 권장 경로로 안내하고, 채널 전환 판정 (a/b) 이 기록돼 있다 (P5).
