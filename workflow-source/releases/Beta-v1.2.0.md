# Beta v1.2.0 (2026-08-13)

> **상태: 릴리스 준비.** `tool_version = v1.2.0-beta`, tag `v1.2.0-beta`.
> **minor release (breaking)** — 21~31차 세션 묶음: **플러그인 배포 전환 P1~P5 완결**
> (공유 payload 렌더러 + Claude Code/Gemini/goose/OpenCode 어댑터 + SessionStart
> 조건부 규칙 주입, 플러그인 = 주 채널 승격) + **2nd deprecation cycle 완결**
> (구경로 shim `tools`/`bootstrap_lib` drop, `--bundle` 기본값 `all`→`read-only`).
> `cmd_release` 경로의 **6번째 실전 발행**.
>
> **breaking**: `import tools.*` / `import bootstrap_lib` / `python -m bootstrap_lib`
> 구경로가 제거됐다 (v1.1.8 에서 예고). 정위치는 `workflow_kit.tools` /
> `workflow_kit.bootstrap_lib`, CLI 는 `wk <name>`. `--bundle` 미지정 MCP 서버는
> 이제 read-only 11종만 서빙한다 — write 가 필요하면 `--bundle write` 서버를
> 명시 등록한다.
>
> wheel top-level 이 `workflow_kit` 하나가 됐다 — **PyPI 발행의 기술 제약 해소**
> (발행 여부는 정책, 소유자 결정). 릴리스 채널은 GitHub Releases 유지.

## 0. 릴리스 판정

본 릴리스의 공통 주제는 **"배포 표면을 하나로"** 다.

- **플러그인 = 주 채널** — 규칙·스킬·MCP·hook 이 전부 `render_agent_plugin()`
  하나에서 파생된다 (payload 18 산출물, 정본 하나·채널 셋). bootstrap 은 진입점
  규칙 주입·미지원 하네스·오프라인 담당으로 병행 유지 (P5 판정, 소유자 확인).
- **약속한 drop 은 시계대로** — v1.1.8 이 시작한 2nd cycle 을 이 릴리스가 닫았다.
  shim 을 지우자 숨어 있던 구경로 소비자 10곳과 무력화된 검사 1건이 드러났다
  (`check_entry_points` [4] 가 `-m tools.tools.X` 의 ModuleNotFoundError rc=1 을
  허용 범위로 통과시키고 있었다) — 전부 정위치 재표적 + 판정 강화로 정리.
- **validate 통과는 로드 증명이 아니다** — P2·P3·P5 전반의 실측 우선 원칙이
  계획을 다섯 번 고쳤다 (manifest mcpServers 미로드 / Gemini 확장 루트 / OpenCode
  방언 반증 / `plugin update` 풀 id / CLAUDE.md HTML 주석 스트립).

## 1. 릴리스 요약

- 범위: `v1.1.8-beta..HEAD` (TASK-2026-08-12-main-011~020 + TASK-2026-08-13-main-001~005, 14+ commit)
- 플러그인 전환 P1~P5: payload 렌더러(`workflow_kit/plugin_payload.py`) →
  Claude Code 어댑터+marketplace 자기 적용 → 멀티 하네스 어댑터
  (gemini-cli/goose/opencode) → 릴리스 게이트 통합 (release-doctor 6번째 source) →
  실측 게이트 + 주 채널 승격 판정
- SessionStart 조건부 규칙 주입: 진입점 생성 마커 grep — 있으면 SKIPPED, 없으면
  `rules.md` 주입 (bootstrap 과 같은 `render_entrypoint_rules` 파생)
- 2nd deprecation cycle 완결: shim drop + `--bundle` 기본 read-only +
  `check_packaging` FORBIDDEN_IMPORTS (일반명 top-level 재유입 차단)
- 별건 수리: bootstrap OpenCode MCP 방언 실측 정정 (배열 command + enabled +
  environment) / 원본 bump 릴리스 검사 sandbox 이관 (pyproject 왕복 0)
- 전량 검사 **260/260 PASS ×2축** + mypy strict 193파일 0 + SDK 매트릭스 3/3

## 2. deliverable

### 2.1 플러그인 배포 전환 P1~P5 (TASK-2026-08-12-main-013~018·020)

- **P1** `render_agent_plugin()` — `plugin/` 이 정본 파생물 (생성과 검증이 같은
  함수, drift 자리가 구조적으로 없다). `check_agent_plugin_payload` 신설.
- **P2** Claude Code 채널 — `.claude-plugin/plugin.json` + hooks + 관례 `.mcp.json`
  + 저장소 루트 marketplace. 실측 2건이 계획을 고쳤다 (경로 필드 `..` 거부 /
  manifest `mcpServers` 는 validate 만 통과하고 로드 안 됨).
- **P3** 멀티 하네스 — `gemini-extension.json`+`GEMINI.md` (확장 루트 = payload
  루트, 스킬 4종 무변환 인식 실측) / goose (CLI 부재, 미완 표기 강제) / OpenCode
  (방언 실측 반증 → 별건 002 로 정본 수정).
- **P4** 릴리스 게이트 — bump 3경로 정합 + release-doctor 가 payload 버전 드리프트
  를 `ok=False`+`fix` 로 차단 (자동 재생성이 아니라 게이트 — 소유자 판정).
- **P5** 실측 게이트 — SessionStart hook stdout 의 모델 컨텍스트 주입 실증 →
  **플러그인 주 채널 승격 + bootstrap 병행 유지** 판정. 스킬 4종 (§11.1 명령과
  1:1), always-on ~121 tok.
- 조건부 규칙 주입 (TASK-2026-08-13-main-003): 두 번째 hook 이 진입점 생성 마커를
  grep — 이중 주입 없음(SKIPPED)/주입(PRESENT) 실측 2경로. 부수 발견: CLAUDE.md
  의 HTML 주석은 모델 컨텍스트에서 스트립된다 — 마커 판정은 파일 grep 으로만.

### 2.2 2nd deprecation cycle 완결 (TASK-2026-08-13-main-005, `7fed415`)

- `workflow-source/tools/` 44 shim 모듈 + `scripts/bootstrap_lib/` 제거 — 자산
  (`tools/hooks/`·`tools/completions/`) 은 경로 계약대로 원위치, wheel 미포함.
- pyproject `packages` 에서 구경로 제거 → wheel top-level = `workflow_kit` 하나.
  `check_packaging` 에 **FORBIDDEN_IMPORTS** (wheel 에 `tools`/`bootstrap_lib` 가
  다시 실리면 FAIL) + `-m workflow_kit.bootstrap_lib` 로 CLI smoke 재표적.
- `--bundle` CLI 기본값 `all`→`read-only` (entrypoint/jsonrpc). `all` 은 명시
  opt-in + notice. `check_read_only_mcp_server` 가 기본 manifest 에 write 도구가
  실리면 FAIL (default flip 회귀 고정), 합집합 판정은 명시 `--bundle all` 기준.
- 숨은 구경로 소비자 10곳 재표적 (`workflow_kit_cli` in-process wrapper 2 /
  `cli_commands_cache`·`cli_commands_release`·`release_status` 의 sys.path 주입 /
  `claim_workspace`·`score_wiki_trend`·`score_wiki_maintainability`·
  `consumer_metrics`·`session_start` 의 경로 상수) + 문서·스킬 안내 `wk <name>` 화.
- `check_entry_points` [4] **무력화 정정** — module path 를 entry point target 에서
  직접 취하고, `No module named` 는 rc 무관 실패 판정 (신설 [4c]).

### 2.3 별건 수리 2건 (TASK-2026-08-13-main-001·002)

- 원본 bump 릴리스 검사 sandbox 이관 — 전량 중 원본 pyproject 왕복의 유일 주범
  (`test_version_bump_apply_and_restore`) 을 `repo_sandbox` 서브프로세스로 재작성,
  watcher 관측 0건/12,403 poll. `check_no_repo_write` 감시 13→15.
- bootstrap OpenCode MCP 방언 — 실측 확정 형태(배열 `command`+`enabled`+
  `environment`)로 정정, `opencode_mcp_server_entry()` 정본 단일화 + case 8 신설.

## 3. smoke 회귀

누적 smoke test **260/260 PASS** ×2축 (2026-08-14, `dev,release,mcp-sdk` extra 를
깐 격리 venv, `--tmp-dir` 실디스크). 이 줄은 릴리스 시점 스냅샷이 아니라 *최신
전량 결과* 를 반영하는 살아있는 지표다.

발행 뒤 드러난 red 2건을 이 축에서 함께 닫았다 — `check_release_pipeline_phase2`
(plugin ZIP 게이트가 dist 판정보다 먼저 걸리는데 acceptable 목록 미갱신) /
`check_mavis_attach_e2e` (`--bundle` 기본값 전환으로 read-only 가 11종이 됐는데
검사가 13종 하드코딩 사본을 들고 있었다 → 정본 registry 파생으로 교체).

릴리스 **시점**에는 신규 smoke 파일이 없었다 (252). 발행 뒤
`check_plugin_distribution` 이 더해져 253, 이어서
`check_branch_memory_namespace`·`check_archive_history_integrity` 가 더해져 255 가 됐다
(TASK-2026-08-13-main-009 / TASK-2026-08-13-fix-branch-memory-namespace-guard-001). 릴리스 시점 case 확장:

- `check_agent_plugin_payload` 7→**15** (어댑터 3장 + 조건부 주입 + 되주입 실증 누적)
- `check_mcp_tool_descriptors` case **8** 신설 (OpenCode entry 형태, 렌더러·독립 증인 양쪽)
- `check_packaging` REQUIRED 정리 + **FORBIDDEN_IMPORTS** 신설
- `check_read_only_mcp_server` 기본값 read-only 판정 추가
- `check_entry_points` [4c] 신설 (module import 실패를 실패로)
- `check_no_repo_write` WATCHED_CHECKS 13→**15**
- SDK 매트릭스 3/3 (mcp 1.27.0/1.29.0/2.0.0)

## 4. 1차 출처 (cross-ref)

- [TASK-2026-08-12-main-011](../../ai-workflow/memory/active/main/backlog/tasks/TASK-2026-08-12-main-011.md) ~ [TASK-2026-08-13-main-005](../../ai-workflow/memory/active/main/backlog/tasks/TASK-2026-08-13-main-005.md)
- 세션 기록: `ai-workflow/memory/active/main/sessions/` 21차~31차
- [플러그인 전환 계획](../../docs/planning/plugin-transition-plan-2026-08.md) (§6 전환 완료 판정) ·
  [배포 검토](../../docs/planning/cli-distribution-review-2026-08.md) (§2 PyPI 제약 해소) ·
  [ADR-003](../../docs/architecture/ADR-003-read-only-mcp-default-policy.md) (bundle 기본값 완결 절)
- 이전 release note: [Beta-v1.1.8.md](./Beta-v1.1.8.md)

## 5. 후속

- **PyPI 발행** — 기술 제약 0, 정책 소유자 결정 대기 (TestPyPI 검증 →
  `release-dist` 출력 명령 → 발행).
- cross-host federation — 두 번째 호스트 = MacBook 확정 (시점 추후, 전원 시
  TASK-2026-08-12-main-019 macOS PEP 668 건 동반).
- stdio-sdk bundle 지원 (승격 기준과 함께).
- TASK-2026-08-13-main-004 — CI native mypy flake 재발 관찰 (유력 원인 제거됨,
  무재발 시 close).

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-08-13T05:27:53Z)_

- total wiki pages: **93**
- total memory entries: **9**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
