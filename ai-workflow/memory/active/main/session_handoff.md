# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-13 (33차 세션 종료 — Codex·Claude Code 플러그인 release asset 분리)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **33차 세션 종료 — Codex·Claude Code native plugin release asset 분리 (TASK-2026-08-13-main-008).** 브랜치 `feat/plugin-harness-distribution`에 PR [#23](https://github.com/ykylee/standard_ai_workflow/pull/23)을 열고, 리뷰 HIGH/MEDIUM/LOW 3건을 `6e537c6a`에서 보완했다: Codex ZIP marketplace를 실제 탐색 경로 `.agents/plugins/marketplace.json`으로 옮기고 source 해석 smoke를 추가했으며, 수동 release 절차와 handoff 상태도 맞췄다. 집중 검증(payload 17/17, distribution smoke, 새 모듈 Ruff)은 PASS. **GitHub smoke CI 두 실행은 세션 종료 시 진행 중**이며, 다음 세션의 첫 행동은 PR #23의 CI 결과 확인 및 실패 시 원인 분리다.
- 현재 기준선: **32차 세션 종료 — v1.2.0-beta 발행 + 2nd deprecation cycle 완결 (TASK-2026-08-13-main-005).** `cmd_release` **6번째 실전**, [GitHub Release](https://github.com/ykylee/standard_ai_workflow/releases/tag/v1.2.0-beta) (whl+sdist, asset 2종 실측). 범위 = 21~31차 묶음 (플러그인 전환 P1~P5) + 2nd cycle (v1.1.8 이 시작한 시계를 닫음). **minor + breaking**: 구경로 `tools.*`/`bootstrap_lib` 제거 + `--bundle` 기본값 `all`→`read-only`. **핵심 실측: wheel top-level = `['workflow_kit']`** — PyPI 를 막던 일반명 충돌 사유가 사라졌고 `check_packaging.FORBIDDEN_IMPORTS` 가 재유입을 wheel 실측으로 막는다. **shim 을 지우자 드러난 것**: 숨어 있던 구경로 소비자 **10곳** (shim 은 호환을 준 게 아니라 의존을 숨기고 있었다) + **검사 무력화 1건** (`check_entry_points` [4] 가 `-m tools.tools.X` 의 ModuleNotFoundError rc=1 을 허용 범위로 통과시켜 36개 전부 green 이었다 → [4c] 신설). **릴리스 직후 재실행이 드리프트 3건 검출** (v1.1.7·v1.1.4 동형): stamp 상수 2 + **배포 사본 23건** — 후자는 `doc-headers-update` 가 정본만 고치고 `ai-workflow/core/` 사본을 몰랐던 자리라 **갱신기에 `_sync_distributed_core_mirror()` 를 심고 sandbox 되주입 test 로 고정**했다 (결함 코드 FAIL 실증). 전량 2축 **252/252 ×2 green** ×3회 + mypy strict 192 files 0 + SDK 매트릭스 3/3. **다음 후보: PyPI 발행 (기술 제약 0, 정책 소유자 결정 대기 — 신규 축) / TASK-2026-08-13-main-004 (mypy flake 재발 관찰) / TASK-2026-08-12-main-019 (macOS PEP 668, MacBook 전원 시).** 상세: [32차 세션 기록](./sessions/v1_2_0_release_2026-08-13.md).
- 직전 기준선: **31차 세션 종료 — 플러그인 SessionStart 조건부 규칙 주입 (TASK-2026-08-13-main-003).** P5 실측(hook stdout 주입 성립)을 실채널로 이었다: `adapters/claude-code/rules.md` (bootstrap 진입점·Gemini 와 **같은** `render_entrypoint_rules` 파생 — 채널 셋, 정본 하나) + SessionStart 두 번째 hook 이 `CLAUDE.md`/`.claude/CLAUDE.md` 의 **생성 마커를 grep** 해 있으면 생략(@AGENTS.md import 패턴 인정), 없을 때만 `cat "${CLAUDE_PLUGIN_ROOT}/..."`. 마커 탐침은 `GENERATED_MARKER` 파생. **실측 2경로 성립**: 진입점 없는 프로젝트 PRESENT(주입+CLAUDE_PLUGIN_ROOT 전개 확인) / 마커 있는 프로젝트 SKIPPED(이중 주입 없음). **부수 발견: CLAUDE.md 의 HTML 주석은 모델 컨텍스트에서 스트립된다** — 마커 존재 판정을 모델에게 물으면 안 된다 (파일 grep 은 무영향). case 8 확장 + 되주입 2종 실증, 15/15 + 전량 2축 **252/252 ×2 green**. **다음 후보: v1.1.9/v1.2.0 릴리스 — P1~P5+어댑터+조건부 주입이 전부 미발행으로 쌓여 있다 (소유자 발행 지시 대기) / 별건 TASK-2026-08-12-main-019 (macOS PEP 668, MacBook 전원 시)·TASK-2026-08-13-main-004 (mypy flake 재발 관찰).** 상세: [31차 세션 기록](./sessions/hook_conditional_rules_injection_2026-08-13.md).
- 그 이전 기준선: **30차 세션 종료 — bootstrap OpenCode MCP 방언 갱신 (TASK-2026-08-13-main-002).** P3 실측이 반증한 entry 형태(문자열 command+args, env, enabled 없음 — opencode 1.17.12 가 거부)를 실측 확정 형태(배열 `command` + `enabled` + `environment`)로 고쳤다. **형태를 아는 자리를 하나로**: `opencode_mcp_server_entry()` 신설 — bootstrap emit 과 플러그인 payload snippet 이 같은 함수 파생 (payload 재생성 diff 0). 독립 증인 `opencode-mcp.json` 도 구형이었음을 확인·갱신 (최상위 키만 대조하던 case 6 의 사각지대). `check_mcp_tool_descriptors` **case 8 신설** — 렌더러·독립 증인 양쪽의 entry 형태 대조 (되주입 실증: 구형 회귀 시 FAIL 3건). roundtrip spawner 배열 command/environment 정규화. **검증**: 새 emit 그대로 `opencode mcp list` connected 실측 + 8/8 + 전량 2축 252/252 ×2 green. **다음 후보: v1.1.9/v1.2.0 릴리스 (소유자 발행 지시 대기) 또는 별건 TASK-2026-08-13-main-003 (hook 조건부 규칙 주입)·TASK-2026-08-12-main-019 (macOS PEP 668).** 상세: [30차 세션 기록](./sessions/opencode_dialect_update_2026-08-13.md).
- 그 이전 기준선: **29차 세션 종료 — 원본 bump 검사 sandbox 이관 완료 (TASK-2026-08-13-main-001).** `watch_transient_writer` 로 writer 를 현장 특정 — 전량 중 원본 pyproject 왕복(1.1.8→1.1.9→1.1.8, 50ms)의 **유일한** 주범은 `check_release_pipeline.py::test_version_bump_apply_and_restore` 였다 (용의 계열 poststep 2종은 전부 mock 이라 무접촉). `repo_sandbox` 서브프로세스 방식(`version-bump --patch --apply --skip-sync-hash --json`)으로 재작성 + 원본 byte 무손상 assert. `check_no_repo_write` WATCHED_CHECKS 13→**15** (`check_release_pipeline.py` 회귀 방어 + `check_agent_plugin_payload.py` — P4 의 plugin/ 원본 덮임 사고 계열 이중 방어). **완료 기준 실측**: 이관 후 전량 2축 옆 watcher **관측 0건/12,403 poll** (이관 전 2건) + 감시 15개 전부 무접촉 + 252/252 ×2 green. **파생: TASK-2026-08-13-main-004 (CI native mypy exit 2 flake) 의 유력 원인이 이 왕복이었다** (mypy 는 시작 시 pyproject 를 config 로 읽는다) — 004 는 재발 관찰만 남김 (무재발 시 close). **다음 후보: v1.1.9/v1.2.0 릴리스 (소유자 발행 지시 대기) 또는 별건 TASK-2026-08-13-main-002 (bootstrap OpenCode 방언)·003 (hook 조건부 규칙 주입)·TASK-2026-08-12-main-019 (macOS PEP 668).** 상세: [29차 세션 기록](./sessions/bump_check_sandbox_migration_2026-08-13.md).
- 그 이전 기준선: **28차 세션 종료 — 플러그인 전환 P5 완료, 전환 계획 전체 종료 (TASK-2026-08-12-main-018).** 실측 3건: ①**SessionStart hook 의 stdout 이 모델 컨텍스트에 실제 주입된다** (프로브 플러그인 마커를 headless 모델이 그대로 반환 — 원칙 3 의 "상시 주입 갭" 전제 충족) ②Gemini 모델 주입 계층은 tier 차단으로 미검증 유지 (로드 계층 실측만 판정에 반영) ③marketplace 수동 업데이트 흐름 성립 (`plugin update` 는 **풀 id `<name>@<marketplace>` 필수** — 이름만 주면 not found). **부수 발견 — 설치 선언 소실 사고**: P2 자기 적용 선언(user settings 의 extraKnownMarketplaces/enabledPlugins)이 세션 시작 시점에 통째로 사라져 있었다 (settings.json 외부 재작성 추정, 원인 미확정) → 재설치 복구 + INSTALLATION 에 리스크·재설치 명령 명시. **판정 (소유자 확인): (a) 플러그인 = 주 채널 승격 + bootstrap 병행 유지** (진입점 규칙 주입·미지원 하네스·오프라인 담당). hook 에 규칙 블록을 싣는 것은 **조건부 주입 설계 선행**으로 별건 [TASK-2026-08-13-main-003]. 산출물: 계획 §3-P5 + **§6-보론 전환 완료 판정** (4조건 전부 성립, 계획 상태 = 완료) / INSTALLATION **§7.0 신설** (플러그인 권장 경로 — Gemini 는 GitHub URL 설치 불성립, 로컬 경로만) / 로드맵 §8 완료 갱신 + core 미러 동기. 전량 2축 **252/252 ×2 green**. **플러그인 전환 축이 닫혔다 — 다음 후보: v1.1.9/v1.2.0 릴리스 (P1~P5 + 2nd cycle 예약분, 소유자 결정) 또는 별건 TASK-2026-08-13-main-001·002·003.** 상세: [28차 세션 기록](./sessions/plugin_p5_channel_verdict_2026-08-13.md).
- 그 이전 기준선: **27차 세션 종료 — 플러그인 전환 P3 완료 (TASK-2026-08-12-main-016) — P1~P4 전부 닫힘, 남은 것은 P5 뿐.** 어댑터 3장이 렌더러 생성물로 편입됐다 (payload 14→**18 산출물**, 검사 13→**15 case**, 되주입 3종 실증). ①**Gemini 도 확장 루트 = payload 루트** — gemini 0.42.0 실측(`extensions new`→`validate`→`link`→`list`): 확장 루트의 `skills/` 관례 경로를 무변환으로 읽어 **payload 스킬 4종이 그대로 인벤토리에 잡혔다.** `gemini-extension.json`(5필드, mcpServers 인라인) + `GEMINI.md`(상시 주입 컨텍스트, bootstrap 진입점과 **같은** `render_entrypoint_rules` 파생) 두 장 — 규칙 상시 주입 채널 첫 개통(로드 계층). **모델 주입 계층은 실측 불가**: headless 호출이 `IneligibleTierError`(무료 tier 의 gemini-cli 지원 종료, Antigravity 이전 안내)로 차단 — P5 게이트 ② 는 연 채 유지. ②**OpenCode 실측이 bootstrap 방언을 반증** — 기존 `render_opencode_mcp_config` 형태(문자열 command+args, env)를 opencode 1.17.12 가 거부(*"Expected array"* / *"Missing key enabled"*). 실측 확정 형태(command **배열** + `enabled` + `environment`)로 `opencode mcp list` **connected** 확인. bootstrap 결함은 별건 [TASK-2026-08-13-main-002]. ③**`.agents/skills/` 수렴 기각** — Claude Code 2.1.229 가 읽지 않는다 (프로브 스킬 실측: `.claude/skills/` 양성 대조군만 노출 + 바이너리 문자열 73:0). ④**`<plugin>/bin` 미탑재 판정** (P2 잔여) — shim 은 좁은 틈만 메우고 Python 의존은 그대로, 그림자 경로 위험 (원칙 4 유지, 마찰 실측 쌓이면 재론). ⑤goose 는 CLI 부재로 실기 검증 미완 — snippet 주석 + case 15 가 미완 표기 강제. gemini-extension.json 이 **버전 4번째 장**으로 릴리스 게이트(case 10·11, release-doctor) 합류. `check_docs` 는 payload 를 `PAYLOAD_DIRNAME` 파생으로 제외 (payload .md 는 소비자 주입 생성물). 전량 2축 **252/252 ×2 green**. **사고 1건**: 되주입 실증 복원에 `git checkout` 을 써 미커밋 P3 수정까지 소실 → 재적용 복구, 이후 사본 백업 복원으로 전환 (작업 중 파일의 되주입 복원에 git 을 쓰지 않는다). **다음 작업 = TASK-2026-08-12-main-018 (P5 실측 게이트 + 채널 전환 판정)**. 상세: [27차 세션 기록](./sessions/plugin_multi_harness_adapters_2026-08-13.md) + 계획 §3-P3.
- 그 이전 기준선: **26차 세션 종료 — 플러그인 전환 P4 완료 + 스킬 4종 (TASK-2026-08-12-main-017·019·020).** 릴리스↔플러그인 연결이 **자동 재생성이 아니라 게이트**로 확정됐다 (소유자 판정). ①**stale 기본인자 제거**: `render_*` 의 version 기본값이 함수 정의 시점에 굳어 bump 후 재생성이 낡은 값을 쓰던 자리를 `current_kit_version()` 호출 시점 조회로 해소 — 검사는 매번 새 프로세스라 **디스크 대조로는 영영 못 잡는 자리**였다. ②bump 3경로가 정합 보고, `release-doctor` **6번째 source** 가 어긋남을 `ok=False`+`fix` 로 차단. ③**dist 자산 미포함 판정** — marketplace 설치 경로가 git 이라 wheel 자산을 안 읽는다. ④`session-end` 스킬 추가로 payload 스킬이 §11.1 명령 4개와 1:1 대응 (`plugin details` 실측 Skills **4**, always-on ~121 tok). **사고 1건**: 처음엔 bump 가 곧바로 재생성하게 짰는데, 릴리스 검사들이 원본에서 bump 를 apply 했다 되돌리고(실측 pyproject 1.1.8→1.1.9→1.1.8, **86ms 왕복**) 그 복원이 플러그인을 몰라 manifest 3장만 낡은 채 남았다. 게다가 목적지를 **모듈 위치**로 잡아 sandbox 실행이 원본을 v0.7.29 로 덮었다 (HEAD 무손상, 복원 완료). → 별건 [TASK-2026-08-13-main-001] 등록. 검사 9→**13 case** (되주입 3종 실증). 전량 2축 **252/252 ×2 green**. **P2 잔여 실측도 이 세션에서 전부 성립** (스킬 네임스페이스 / MCP 승인 / SessionStart hook) — 다만 호스트가 PATH 에 넣는 `<plugin>/bin` 이 payload 에 **비어 있다** (P3 판정 대상). 상세: 계획 §3-P2·§3-P4.
- 그 이전 기준선: **25차 세션 종료 — 플러그인 Claude Code 채널이 개통됐다 (TASK-2026-08-12-main-015, P2).** 어댑터 2장 (`.claude-plugin/plugin.json` + `adapters/claude-code/hooks.json`) + 관례 경로 `.mcp.json` + 저장소 루트 `marketplace.json` — 전부 렌더러 생성물. 검사 7→**9 case**. **`claude plugin` CLI 실측이 계획을 두 번 고쳤다**: ①경로 필드의 `..` 를 거부 → 플러그인 루트 = payload 루트 (어댑터가 manifest+hooks 두 장으로 더 얇아짐) ②manifest 의 `mcpServers` 경로 필드는 **validate 는 통과하는데 로드가 안 된다** (인벤토리 MCP 0) → 관례 `.mcp.json` 으로 옮겨 1 확인. **validate 통과는 로드 증명이 아니다.** 자기 적용 성공: `marketplace add ./` + `install` (scope user, enabled, Skills 3/Hooks 2/MCP 1), `wk` 부재 graceful 두 hook 실측. 전량 2축 **252/252 ×2 green**. **다음 세션 첫 확인 = 스킬 네임스페이스(`/standard-ai-workflow:session-start`) + MCP 승인 UX** (설치는 현재 세션에 소급 적용 안 됨) → 계획 §3-P2 실측표에 추가. 상세: [25차 세션 기록](./sessions/plugin_claude_code_adapter_2026-08-12.md).
- 그 이전 기준선: **24차 세션 종료 — 플러그인 전환 P1 완료, 공유 payload 가 파생물이 됐다 (TASK-2026-08-12-main-014).** `workflow_kit/plugin_payload.py` 의 `render_agent_plugin()` 이 `plugin/` 5파일 (plugin.json + skills 3종 + mcp.json) 을 정본에서 생성한다 — 생성과 검증이 **같은 함수**라 drift 자리가 구조적으로 없다. §11 명령·계약 / 상태값 / MCP command / 도구 구성 전부 정본 파생, 규칙 리터럴 사본 0 (18문장 대조). 신설 `check_agent_plugin_payload` 7 case, smoke 251→**252**. 되주입 실증: version 오염 → 드리프트 FAIL → 재생성 7/7. **판단 1건**: Agent Plugins 1.0 선택 필드 스펙을 원문 확인 못 해 `plugin.json` 을 계약 3필드로 고정하고 **검사가 필드 집합 자체를 강제**한다 (확장은 명시 task — P2 자기 적용이 확인 경로). 전량 2축 **252/252 ×2 green**, mypy strict 192파일 0. **다음 작업 = TASK-015 (P2 Claude Code 어댑터 + marketplace + 자기 적용)**. 상세: [24차 세션 기록](./sessions/plugin_payload_renderer_2026-08-12.md).
- 그 이전 기준선: **23차 세션 종료 — 플러그인 배포 전환 계획 확정 (TASK-2026-08-12-main-013, 사용자 지시 = 소유자 전환 go).** 계획: [plugin-transition-plan-2026-08.md](../../../../docs/planning/plugin-transition-plan-2026-08.md) — 원칙 5 (파생본/공유 payload=Agent Plugins 1.0 레이아웃/빅뱅 금지/graceful/버전 동기) + **P1~P5 로드맵 + WBS (TASK-014~018 planned 등록)**. 로드맵 §8 주 작업 축 등재. **다음 릴리스 목표 = P1+P2** (payload 렌더러 + Claude Code 어댑터·marketplace·자기 적용) + 기존 예약분 (2nd cycle shim drop + --bundle 기본값). **다음 작업 = TASK-014 (P1 render_agent_plugin)**. 상세: [23차 세션 기록](./sessions/plugin_transition_plan_2026-08-12.md).
- 그 이전 기준선: **22차 세션 종료 — 멀티 하네스 공유 플러그인 검토 완료 (TASK-2026-08-12-main-012, 사용자 지시).** 판정: **가능 — 공유 payload + 하네스별 얇은 manifest.** 무변환 단일 아티팩트는 부분 성립 (Agent Skills `SKILL.md` ~40제품 / **Agent Plugins 1.0** — 2026-08-06 출범, 5클라이언트 — 단 Claude Code·Gemini·goose·OpenCode 미합류). 권고: payload 물리 배치를 Agent Plugins 1.0 레이아웃 (`plugin.json`+`skills/`+`mcp.json`) 으로 채택 + 어댑터 4장, TASK-011 Phase A 를 `render_agent_plugin()` 계열로 재정의 (소유자 go 대기). 검토 문서: docs/planning/multi-harness-plugin-review-2026-08.md. 상세: [22차 세션 기록](./sessions/multi_harness_plugin_review_2026-08-12.md).
- 그 이전 기준선: **21차 세션 종료 — 플러그인 배포 검토 완료 (TASK-2026-08-12-main-011, 사용자 지시).** 결론: **채택 권고, 단 14번째 파생본으로** (렌더러 생성 + 검사 강제 — 손 플러그인 금지). 핵심 갭 = CLAUDE.md 형 상시 주입 불가 (SessionStart hook 실측 전까지 bootstrap 주입 유지) + Python 은 uv 전제. 이행 Phase A(렌더러)→B(marketplace)→C(실측 3건). 검토 문서: docs/planning/plugin-distribution-review-2026-08.md. 상세: [21차 세션 기록](./sessions/plugin_distribution_review_2026-08-12.md).
- 그 이전 기준선: **20차 세션 종료 — v1.1.8-beta 발행 (`cmd_release` 5번째 실전, TASK-2026-08-12-main-010).** 16~19차 묶음 (bundle 분리/cross-platform/네임스페이스 2단계/안전망 2건). **2nd deprecation cycle 시계 시작** (다음 릴리스에서 shim + --bundle 기본값 drop). 절차 수렴: v1.1.7 검출 2건 → v1.1.8 0건. 신규 착수: **플러그인 형태 재구성·배포 검토** (TASK-011, 사용자 지시 — Claude Code 플러그인 스펙 조사 진행 중). 상세: [20차 세션 기록](./sessions/v1_1_8_release_2026-08-12.md).
- 그 이전 기준선: **19차 세션 종료 — status 보존 규칙 + 실행-중 감시 (TASK-2026-08-12-main-008·009).** ①backlog-update `--status` 미지정 = 기존 상태 보존 (미지정은 "바꾸지 말라"). ②`check_no_repo_write` 가 실행-중 porcelain 폴링으로 touch-and-restore 를 검출 (§6 리스크 해소) — 감시 13개 실측 전부 무접촉, 원장 공집합 출발. 상세: [19차 세션 기록](./sessions/status_preserve_and_midrun_watch_2026-08-12.md).
- 그 이전 기준선: **18차 세션 종료 — 네임스페이스 격상 2단계 완결 (TASK-2026-08-12-main-007).** bootstrap_lib → workflow_kit.bootstrap_lib 물리 이동 + shim 패키지 (`python -m` 양경로 호환) + 소비면 24파일 재표적. wheel 실측 (impl 10 + shim 10, packaging PASS). **PyPI 잔여 = 2nd cycle 에 shim 2종 + --bundle 기본값 drop 뿐** (그 후 소유자 결정). 상세: [18차 세션 기록](./sessions/namespace_stage2_bootstrap_lib_2026-08-12.md).
- 그 이전 기준선: **17차 세션 종료 — CLI cross-platform + 네임스페이스 격상 1단계 (TASK-2026-08-12-main-005·006).** ①os-matrix CI 신설 — **Windows 첫 실측 8/8 PASS** (probe: wk 핵심 명령 + MCP 브리지), 지원 tier 문서화. ②tools 43모듈 → workflow_kit.tools 물리 이동 + 구경로 shim + 소비면(테스트 70파일·entry points·mkdocs) 재표적. 사고 1건 복원: shim 경유 monkeypatch 미적용으로 검사가 실저장소 pyproject 오염 (HEAD 무손상, 즉시 복원 — source-bound 소비자는 impl 직표적). 상세: [17차 세션 기록](./sessions/cross_platform_and_namespace_2026-08-12.md).
- 그 이전 기준선: **16차 세션 종료 — MCP bundle 분리 + CLI 배포 검토 (TASK-2026-08-12-main-003·004).** ①bundle 선택자 (read-only 11 / write 2 = `workflow_write_bundle` / all 13 기본+경고) + 렌더러 정직한 기본 (`--bundle read-only`, claude-code·MiniMax 는 write entry 동시 emit) + 검사 강제 + 자기 적용 (.mcp.json 2-server). 다음 cycle: 기본 all→read-only. ②배포 검토 (docs/planning/cli-distribution-review-2026-08.md): wheel top-level 에 일반명 `tools`/`bootstrap_lib` 실측 → PyPI 는 네임스페이스 격상 선행 필수. 권고 = uv/pipx + GH Release wheel 격리 설치 (INSTALLATION §3 반영). 상세: [16차 세션 기록](./sessions/mcp_bundle_split_and_cli_distribution_2026-08-12.md).
- 그 이전 기준선: **15차 세션 종료 — v1.1.7-beta 발행 (`cmd_release` 4번째 실전, TASK-2026-08-12-main-002).** tag + GitHub Release (whl+sdist). 범위 = 6~14차 묶음 (state.json 생성물 / 배타 락 / 리뷰 후속 6건 / federation self-host), smoke 249→251. 실전 검출 2건: CI 가 RELEASE.md stamp 누락을 잡음 (bump 후엔 필터가 아니라 **전량**) + 릴리스 직후 재실행이 3건 잡음 (stamp 상수 2 + 배포 사본 23 날짜 — v1.1.4 동형). 상세: [15차 세션 기록](./sessions/v1_1_7_release_2026-08-12.md).
- 그 이전 기준선: **14차 세션 종료 — plex 가 federation 의 첫 상시 참여자가 됐다 (TASK-2026-08-12-main-001).** `host-serve-registry --print-systemd-unit` 신설 + plex systemd user unit `wk-registry` 가동 (0.0.0.0:8765 + Bearer 토큰, LAN 실측 4종) + registry 위생 (`main` 등록) + 환경 기록 [environments/plex.md](../environments/plex.md) (합류 절차: add-known-host + pull 두 명령). cross-host 실측은 **두 번째 호스트 결정(사용자) 대기**. 상세: [14차 세션 기록](./sessions/federation_self_host_2026-08-12.md).
- 그 이전 기준선: **13차 세션 종료 — 전량 검사 배타 락 가동, 2026-08-11 backlog 28건 전부 done (TASK-019).** runner 진입 flock (.git/run_all_checks.lock, 계쟁 시 보유자 정보 + 즉시 실패, env 마커 재진입 승계, --no-lock 은 크게 기록), stale 은 커널 자동 해제로 원천 해소. `check_run_all_checks_lock` 5 case (부모 runner 보유 시 적응 모드). 전량 2축 **251/251 ×2 — 락 실전 첫 가동**, smoke 250→251. 한계: 직접 편집 충돌은 worktree 분리가 정공법 (CLAUDE.md 규약 층). 상세: [13차 세션 기록](./sessions/runner_exclusive_lock_2026-08-12.md).
- 그 이전 기준선: **12차 세션 종료 — TASK-020 발 렌더러 결함 계열이 완결됐다 (TASK-028).** 26개 결함이 0: 주입 9+4+6 (보조 6 은 `render_memory_update_section` §11 섹션), 잔여 8 은 이유 명시 원장 (case 9 양방향 판정 — 원장이 낡으면 red), 5 는 메모리 무관. pi-dev 는 전체 블록 승격 + 병합 시 블록 통째 제거 (중복 1회 실측). 부수: grok skill 의 낡은 flat 경로 generate_workflow_state 안내 → `wk refresh-state`. 상세: [12차 세션 기록](./sessions/secondary_renderer_s11_injection_2026-08-12.md).
- 그 이전 기준선: **11차 세션 종료 — 소비자 안내 표면이 전부 `wk` 를 가리킨다 (TASK-027).** SKILL.md 3종·apply_guide 의 미배포 `skills/` 경로 안내 제거, `check_packaging` 이 `tools` 배포를 wheel 에서 검증 (구판 1.1.6 wheel 에서 즉시 FAIL 실증), `--copy-core-docs` 는 죽는 wrapper 대신 SKILL.md 문서만 복사. 상세: [11차 세션 기록](./sessions/consumer_surface_cleanup_2026-08-12.md).
- 그 이전 기준선: **10차 세션 종료 — MCP 도구 목록 사본 3계열이 registry 하나로 수렴했다 (TASK-025).** MiniMax 렌더러 손 목록(10개, 3개 누락)→registry 파생, 유령 script_path 2건은 mcp_servers/ 실물 생성 + 실존 강제, 예시 tools 배열은 case 7 이 registry 와 대조. ADR-003 에 MCP(선별 부분집합)↔wk(전체 창구) 이원 표면 의도 명시. 상세: [10차 세션 기록](./sessions/mcp_tool_list_single_source_2026-08-12.md).
- 그 이전 기준선: **9차 세션 종료 — §11.1 명령의 손 사본 7곳이 정본 파생으로 바뀌었다 (TASK-026).** `find_memory_command` 로 렌더러가 정본 §11.1 에서 명령을 꺼내 쓰고, goose `on_session_end` 는 깨진 skills/ 경로 대신 `wk refresh-state`. 검출기가 §11.1 명령·§11.2 계약을 판정 대상에 추가, case 8 이 `PRIMARY ∪ EXEMPT == SUPPORTED_HARNESSES` 단언 (mavis 분류), self_application 이 §11 탐침 (낡은 루트 AGENTS.md 재생성). 되주입 3종 실증. 상세: [9차 세션 기록](./sessions/s11_single_source_hardening_2026-08-12.md).
- 그 이전 기준선: **8차 세션 종료 — MCP readOnlyHint 가 허위에서 registry 선언 파생으로 바뀌었다 (TASK-024).** `ReadOnlyToolSpec.read_only` + `WRITE_CAPABLE_TOOL_NAMES` 사실 목록, write 2종(`apply_robust_patch`/`rotate_workflow_logs`) hint=false, 검사가 삼자 일치 강제 (되주입 FAIL 실증). ADR-003 v1.1.7 개정 (13도구 현실) + wiki 갱신. 상세: [8차 세션 기록](./sessions/mcp_readonly_hint_truthful_2026-08-12.md).
- 그 이전 기준선: **7차 세션 종료 — backlog-update 가 재생성에서 병합으로 바뀌었다 (TASK-023).** `merge_task_file` (명시 인자만 반영) + index block 보존 (status 줄만 교체) + handoff task ID dedupe + `--kind`/`--priority` 미지정 시 보존. `check_backlog_update_layout` 5→8 case, 신설 3 case 는 버그 코드에서 FAIL 실증. 종결을 고친 도구 자신으로 수행. 상세: [7차 세션 기록](./sessions/backlog_update_merge_semantics_2026-08-12.md).
- 그 이전 기준선: **6차 세션 종료 — state.json 이 생성물로 선언되고 절차·검사가 붙었다.** 정본 §11.1 에 `wk refresh-state` 행, §11.2 에 생성물 선언 + "handoff/backlog 는 생성기 입력" 선언. `wk session-start` 무인자 동작 (workspace 자동 탐색 + branch-scoped daily 관측 — 인덱스 전제 오판 결함 해소). `check_state_json_generated` 6 case (되주입 + 자기 적용 + 선언↔창구 정합). smoke 249→**250**, 전량 2축 250/250 ×2 green. 리뷰 3종(하네스/스킬·CLI/MCP) 결함 목록은 [6차 세션 기록](./sessions/state_generated_and_composition_review_2026-08-11.md) §3·§4 — readOnlyHint 허위 주석, goose hook 깨진 경로, §11.1 손 사본 7곳, `wk backlog-update` 파괴적 update 등.
- 그 이전 기준선: **5차 세션 종료 — 하네스 파생본이 정본 하나로 통일됐다.** 2026-08-11 backlog 22건 중 20건 종결 (TASK-018 in_progress, 019 planned).
  - **층위가 계속 내려간 세션이었다**: 검사 4건 FAIL → 전부 macOS `/private` symlink 하나 → 재검증에서 state.json 이 생성기와 갈라짐 → 왜 갈라지나(아무도 생성기를 안 돌리고 에이전트가 손으로 쓴다) → **왜 손으로 쓰나: 소비자에게 실행 가능한 경로가 처음부터 없었다.** 마지막이 뿌리였다.
  - **TASK-017** — macOS 회귀 4건이 전부 `/private` symlink 뿌리. production 무수정, 검사 fixture 4곳 `.resolve()` 통일. **기능 회귀가 아니라 검사의 플랫폼 이식성 결함이고 Linux CI 에서는 영영 안 드러난다** — darwin homelab 이 그 축이다.
  - **TASK-020** — 렌더러 32개 전수검사: **26개**가 메모리 갱신을 지시하며 방법을 안 알려줬고, 유일한 '정상' 1개조차 **존재하지 않는 경로**를 가리켰다 (goose config 형식이 강제한 부산물). 배포물 확인 결과 skill 스크립트는 pip 패키지에도 bootstrap 번들에도 없고 `wk` 68개 중 해당 기능 0개 — `pyproject` 주석의 "bootstrap 이 복사한다" 는 **거짓 전제**였다.
  - **TASK-021** — skill 구현 3개(1,561줄)를 배포되는 `tools/` 로, 원 경로엔 wrapper. **wk 68→71 명령.** 소비자에게 실행 경로가 생겼다.
  - **TASK-022** — 정본 **§11 (메모리 갱신 경로 + 파싱 계약)** 신설 → `render_entrypoint_rules()` 로 전 하네스 주입 → `check_standard_single_source` 강제. **결함 26→14.** 자기 적용으로 이 저장소 CLAUDE.md·commands 재생성.
  - 상세: [5차 세션 기록](./sessions/darwin_verify_and_harness_unification_2026-08-11.md).

- 그 이전 기준선: **2026-08-11 backlog 16건 전부 종결** (4차 세션 — TASK-014~016). **기술보고서 논문 양식 문서** 완성 (`docs/reports/` 계획 md + 보고서 html, 사후 검토 4회전: 수치 날조 정정 → 어휘 정리 → 학습회 독립화) + **로컬 병렬 TIMEOUT flake 근본 해소** (`CHECK_TIMEOUT_S` 파일 안 선언 신설, 위험군 6검사 150s, 전량 2축 ×2회 TIMEOUT 0) + **watcher ready handshake** (CI flake 수정) + 소유자 결정 2건 (TASK-014 누적 표기 미삽입 / branch protection 보류). 상세: [4차 세션 기록](./sessions/tech_report_and_timeout_fix_2026-08-11.md). 그 이전 (저장소 리팩터링 사이클 TASK-001~013, 대형 파일 분할 −3,208줄 + 결함 4건 + 아카이브 + check 통합, smoke 268→249): [리팩터링 세션](./sessions/repo_refactoring_and_defect_fixes_2026-08-11.md). 그 이전 (CI 재현성 회복 + smoke 병렬화, 15연속 red 해소): [3차 세션](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md).
- 현재 주 작업 축: **없음 — 플러그인 전환 축(P1~P5)과 2nd deprecation cycle 이 v1.2.0-beta 발행으로 함께 닫혔다.** 미발행 누적분 0. **신규 후보 축 = PyPI 발행** (wheel top-level = `workflow_kit` 하나 실측으로 기술 제약 0, `check_packaging.FORBIDDEN_IMPORTS` 가 재유입 차단 — 남은 것은 **정책 결정(소유자)** 뿐이다. 순서: TestPyPI 검증(`wk release-dist` 가 명령을 이미 출력) → 정책 결정 → 발행). 대기 축: [TASK-2026-08-13-main-004] CI native mypy flake 재발 관찰 (유력 원인 제거됨, 무재발 시 close) / [TASK-2026-08-12-main-019] macOS PEP 668 (MacBook 전원 시) / cross-host federation — 두 번째 호스트 = MacBook 확정, 시점 추후 (합류는 MacBook 쪽 세션에서 environments/plex.md 절차 두 명령) / darwin mavis e2e / memory_index 3-tuple 추이.
- ~~소유자 결정 대기: state.json 생성물 여부~~ — ✅ **해소** (TASK-018, 2026-08-11): **생성물로 확정.** 정본 §11.2 에 선언, `wk refresh-state` 로 재생성, `check_state_json_generated` case 5 가 이 저장소의 정합을 상시 검사. 상세 요약·산문은 state.json 이 아니라 handoff §4 와 task 파일(SSOT)에 남긴다.
- 다음 후보 축: **PyPI 발행 (신규 — 기술 제약 0, 정책 소유자 결정 대기)** / cross-host federation (두 번째 호스트 = **MacBook 확정, 시점 추후**) / memory_index 3-tuple 지표 추이 관찰. ~~federation self-host add~~ ✅ (14차) · ~~v1.1.9/v1.2.0 미발행 누적~~ ✅ **해소 (32차 — v1.2.0-beta 발행, 누적분 0)**. (v1.1.0·v1.1.1 노트 누적 표기는 TASK-014 에서 **미삽입 확정**, branch protection 은 소유자가 **보류 결정** (2026-08-11) — 둘 다 후보 축에서 제거.)
- 발견한 cross-project 패턴 (agent memory 추가):
  - **Federation pattern** (4 후보 검토: central ❌ / git ❌ / S3 ❌ / federation ✅)
  - **MCP/CLI dual mode** (operational tool 의 4종 wrapper)
  - **3-layer defense** (규약 + client hook + server protection)
  - **Scope drift detection** (3-way enum: planned_done / planned_undone / unplanned_done)
  - **time.mktime → calendar.timegm** (UTC timestamp KST 환경 함정)
  - **[project.scripts] entry points** (CLI 化 A안, venv e2e 검증)
  - **기존 dispatcher 확장 > 새 dispatcher** (진입점이 둘로 갈리면 `--help` 도 갈린다)
  - **serving 없는 pull 은 반쪽** (API 만 있고 부를 CLI 가 없으면 기능이 없는 것과 같다)
  - **모름 ≠ 안전** (검사에서 못 읽은 필드를 통과로 치면 거짓 안심을 준다)
- 최근 핵심 기준 문서:
  - [multi_workspace_orchestration.md](../../../../workflow-source/core/multi_workspace_orchestration.md) — **§0.7 상태표 + §7.1·§7.3 구현 표시** + §0.8 *아직 열려 있는 것* 4건
  - [global_workflow_standard.md §10](../../../../workflow-source/core/global_workflow_standard.md) — 다중 작업·협업 규칙
  - [MEMORY_GOVERNANCE.md](../../../../workflow-source/MEMORY_GOVERNANCE.md)

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
-
## 3. 차단 작업

- 현재 `blocked` 작업:
-
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-08-13-main-008 Codex·Claude Code native plugin release asset 분리 및 release pipeline 연결
- TASK-2026-08-13-main-007 공개 배포 전 필수 수리 3건 — LICENSE 부재 / 버전 체계 모순 / 저자 이메일
- TASK-2026-08-13-main-006 PyPI 발행 정책 검토
- TASK-2026-08-13-main-005 2nd deprecation cycle 완결 + v1.2.0-beta 발행
- TASK-2026-08-13-main-003 플러그인 SessionStart hook 조건부 규칙 주입 — 진입점 규칙 블록 감지 시 생략
- TASK-2026-08-13-main-002 bootstrap OpenCode MCP 방언이 현행 opencode 에서 거부됨 — command 배열/enabled/environment 로 갱신
- TASK-2026-08-13-main-001 원본 저장소에서 bump 를 apply 하는 릴리스 검사를 sandbox 로 이관
- TASK-2026-08-12-main-018 플러그인 전환 P5 — 실측 게이트 + 채널 전환 판정
- TASK-2026-08-12-main-016 플러그인 전환 P3 — 멀티 하네스 어댑터 (gemini-cli/goose/opencode)
- TASK-2026-08-12-main-017 플러그인 전환 P4 — 릴리스 파이프라인 통합
- TASK-2026-08-12-main-020 플러그인 payload 에 session-end 스킬 추가 (스킬 3→4종)
그 이전 완료 항목은 [3차 세션 기록](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md)·[2차 세션 기록](./sessions/adr006_retrospective_and_calibration_2026-08-10.md)과 각 task 파일에 있다.

## 5. 다음 세션 시작 포인트

### 무엇이 끝났나 (2026-08-10, 3차 세션)

**CI 재현성 회복 + smoke 병렬화** (TASK-016~019). 상세는
[세션 기록](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md).
2차 세션(TASK-008~015, ADR-006 후속 + v1.1.6-beta 발행)은 §4 하단 항목 참조.

**push 전 재현 명령이 둘로 늘었다** — 둘 다 CLAUDE.md 에 적혀 있다:

```bash
# 브랜치 매트릭스 (CI 는 2축, 로컬 무인자는 1축 — 이 비대칭이 15연속 red 를 만들었다)
python3 workflow-source/tests/run_all_checks.py --branch-context=all --tmp-dir=<실디스크경로>

# SDK 매트릭스 (mcp 를 쓰는 코드를 건드렸으면)
PYTHONPATH=workflow-source python3 -m workflow_kit.common.sdk_matrix --run-local
```

전량 검사는 이제 **기본이 병렬**(`--jobs auto`)이다. 재현이 필요하면 `--jobs 1`.
저장소 전역을 관찰하는 검사를 새로 만들면 파일 안에 `REQUIRES_QUIET_REPO = True` 를
선언해야 한다 — 안 하면 병렬에서 오탐이 난다.

### 다음에 할 일 (순서)

이 세션에서 **저장소 리팩터링 조사**를 했고, 아래는 그 결과다 (근거는 §6 아래
"조사로 확정된 것" 참조). 사용자가 우선순위를 정한 항목만 실행했다 (정숙 구간 근본
수정 = TASK-019). 나머지는 미착수:

- ~~`check_mypy_strict_v0_11_3` ~ `v0_11_10` 8개 제거~~ — ✅ **완료**
  (TASK-2026-08-11-main-001, smoke 268→260).
- ~~`ai-workflow` 아카이브 정리~~ — ✅ **완료** (TASK-2026-08-11-main-003,
  185파일 제거, wiki 참조 1건 + freeze 최소 세트 6건 보존, README 링크 교정).
- ~~`check_cache_*` 13개 통합~~ — ✅ **완료** (TASK-2026-08-11-main-004,
  31 case verbatim 보존, smoke 260→248).
- ~~`release_pipeline.py` 분할~~ — ✅ **완료** (TASK-2026-08-11-main-007,
  3908→3174 + 모듈 4개, 분석 지도 방식). `dashboard_data.py` ✅ (TASK-010, 2488→1526),
  `workflow_kit_cli.py` ✅ (TASK-011, 2095→583) — **대형 파일 분할 완결**.
- ~~`docs/presentations/*.pdf|pptx` 5.2MB~~ — ✅ **완료** (TASK-2026-08-11-main-009, 파생 바이너리 제거·소스 보존).
- ~~branch protection~~ — **보류 결정** (2026-08-11, 소유자). `main` 미보호 (404 실측)
  상태를 인지한 채 일단 켜지 않기로 함. 재검토 시 `wk check-branch-protection` 으로
  현황 판정부터 (도구는 판정만 한다 — v1.1.2 §2.3).
- ~~`mooneye` 브랜치 처리~~ — ✅ **완료** (TASK-2026-08-11-main-012, `origin/mooneye`
  삭제. 고유 커밋 0 — 172 커밋 전부 main 에 존재, `active/mooneye/` 부재로
  memory 아카이브 해당 없음).

## 6. 남은 리스크 / 확인하지 못한 것

- ~~`cmd_release --apply` 실전 미검증~~ — ✅ **해소** (v1.1.4-beta 발행으로 apply
  경로 전체 실증: tag push / gh release / dashboard emit / audit append).
- **호스트 환경 의존 게이트** — 시스템 python 에는 mypy/mcp/twine 이 없어 관련 검사가
  fail 한다 (venv 에서 전부 PASS — `.venv` 에 dev,release,mcp-sdk 설치돼 있음).
  release 는 반드시 venv 에서 돌린다.
- ~~TST-WF-01 advisory red~~ — ✅ **해소** (TASK-004, 측정 재설계로 hard 복귀 +
  compliant). 남은 흔적: v0.15.18 dummy wrapper 는 측정에서 배제될 뿐 파일에
  남아 있다 — 물리 제거는 115 파일 churn 이라 별건.
- **darwin homelab 에서 mavis e2e 재확인 필요** — 검사를 정본 읽기로 바꿨으므로 mavis
  설치 호스트에서 한 번 돌려 기존과 동일하게 green 인지 확인하는 것이 안전하다.
- ~~title drift 임계 0.6 heuristic~~ — ✅ **해소** (TASK-008, 실측 캘리브레이션으로
  0.6 유지 확정 + `check_title_drift_calibration` 이 재캘리브레이션을 강제).
- ~~registry loopback 만 실측~~ — **부분 해소** (TASK-009, 비-loopback bind + pull
  왕복은 이 호스트에서 실측). **잔여**: 진짜 cross-host / 방화벽 / reverse proxy /
  TLS 종단 — 두 번째 호스트 필요 (darwin homelab).
- ~~`check_no_repo_write` 의 계약 한계~~ — ✅ **해소** (TASK-2026-08-12-main-009, 실행-중 폴링 + 원장). 이전 기술: 판정이 "실행 **후** 복원되었는가"
  라, 건드렸다 되돌리면 통과한다. `check_bidir_link_v0_13_3` 은 **이미 감시 목록에
  있었는데도** 그 이유로 안 잡혔다. 실행 *중* 감시(폴링)로 강화하면 남은 감시 대상
  다수가 같은 이유로 red 가 될 수 있어 범위가 크다. **되돌리는 것은 안 건드리는 것이
  아니다.**
- ~~amend Guard 2 의 staged-삭제 fatal~~ — ✅ **해소** (TASK-2026-08-11-main-002,
  `needs_add_only` 선별 + case 10 되주입으로 고정. §4 참조).
- **transient pyproject writer 정체 미상 (2026-08-11 1회 관측)** — 병렬 전량
  실행 중 원본 `pyproject.toml` 이 일시 변경됐다 되돌아왔다 (version_auto_sync
  byte-대조가 포착). 재현 실패 (표적 3회 + 전량 2회 + 50ms md5 watcher).
  관찰자 3검사는 정숙화(TASK-008)로 위양성 차단됨. **감시 수단은 저장소에
  고정됨** (TASK-013, `workflow-source/tools/watch_transient_writer.py` —
  일회용 `~/tmp` 스크립트의 승격판): 재발 의심 시 전량 검사 옆에 백그라운드로
  세워 두면 diff + ps 전량 + fuser 를 이벤트별로 남긴다 (로그는 temp 에만,
  저장소 안 로그는 거부). `check_watch_transient_writer` 5 case 가 되주입
  양방향으로 계약을 고정. `check_no_repo_write` 의 "실행 후 복원" 계약 한계와
  같은 뿌리로 추정 — writer 특정 자체는 재발 시의 일이다.
- **정숙 구간 6건** (TASK-008 로 3→6) — `check_no_repo_write`(전역 관찰) /
  `check_parallel_smoke`(runner 호출) / `check_source_without_runtime_layer`
  (저장소 복사) 는 본질적 직렬이고, `version_auto_sync` / `self_recovering` /
  `bidir_link` 는 원본 byte-대조 관찰 때문 (TASK-008). 병렬화로 더 줄이려면
  이들의 설계 자체를 바꿔야 한다.
- 이 밖의 과거 세션 리스크 (`--force` 3rd layer 미가동)는 변화 없음 —
  2026-08-09 까지의 세션 기록 참조.

## 7. 저장소 구성 조사 (2026-08-10 3차 세션)

리팩터링 판단 근거. git 추적 **1766 파일**:

| 영역 | 파일 | 비고 |
|---|---|---|
| `workflow-source` | 898 | tests 268, workflow_kit 129, releases 171, tools 74 |
| `ai-workflow` | 778 | **backlog tasks 193 + 아카이브 142**, wiki 81, sessions 18 |
| `docs` | 36 | presentations PDF/PPTX 가 **5.2MB** |

- **"버전 접미사 71개 = 중복" 은 틀렸다** (이 세션에서 정정). 주제별로 갈라보니
  대부분 고유하고, 진짜 중복은 `mypy_strict_v0_11_3~10` 8개뿐이다.
- 테스트가 느렸던 주된 원인은 **저장소 크기가 아니라 실행 방식**이었다 (순차 →
  병렬로 345s→118.8s). 위 정리 항목 중 실행 시간을 실제로 줄이는 것은 mypy 8개
  (15초) 뿐이고 나머지는 저장소 위생 문제다 — 섞어서 "정리하면 빨라진다" 고 말하지
  않는 편이 정확하다.

**이전 세션들의 교훈**은 각 세션 기록에 있다:
[2026-08-09](./sessions/cli_dispatcher_and_rotation_2026-08-09.md) ·
[2026-08-08](./sessions/multi_workspace_orchestration_2026-08-08.md) ·
[2026-08-05](./sessions/self_application_and_mcp_2026-08-05.md) ·
[2026-08-07 MCP](./sessions/mcp_load_verification_2026-08-07.md) ·
[2026-07-27](./sessions/selfref_cleanup_and_ci_measurement_2026-07-27.md)
