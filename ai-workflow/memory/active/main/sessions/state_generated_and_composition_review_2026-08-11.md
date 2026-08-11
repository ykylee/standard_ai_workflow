# 6차 세션 — state.json 생성물 전환 + 구성 리뷰 (2026-08-11)

- 문서 목적: TASK-2026-08-11-main-018 종결 기록 + 리뷰 3종(하네스 파생본 / 스킬·CLI / MCP)에서 발견한 결함 목록의 정본.
- 상태: done
- 관련: [TASK-018](../backlog/tasks/TASK-2026-08-11-main-018.md), [5차 세션 기록](./darwin_verify_and_harness_unification_2026-08-11.md)

## 1. 한 줄 요약

`state.json` 이 **생성물**로 선언되고 (`정본 §11`), 재생성 창구(`wk refresh-state`)와
드리프트 검사(`check_state_json_generated`, 6 case)가 생겼다. `wk session-start` 는
무인자로 동작한다. smoke 249→**250**, 전량 2축 250/250 ×2 green.

## 2. TASK-018 산출물

| 변경 | 파일 |
|---|---|
| workspace 자동 탐색 (`discover_project_profile_path`) | `workflow_kit/common/paths.py` |
| daily backlog 관측 공개화 (`find_latest_daily_backlog`) | `workflow_kit/common/state/builder.py` |
| 무인자 + branch-scoped latest backlog + self-bootstrap 안내를 `wk` 로 | `tools/session_start.py` |
| `wk refresh-state` (재생성 / `--check` drift 판정) 신설 | `tools/refresh_state.py`, `tool_dispatch.py`, `pyproject.toml` |
| §11.1 표에 refresh-state 행 + §11.2 에 생성물 선언 2 bullet | `core/global_workflow_standard.md` (+배포 사본 +스냅샷 +CLAUDE.md) |
| drift 검사 6 case (되주입 양방향 + 자기 적용 + 선언↔창구 정합) | `tests/check_state_json_generated.py` |
| smoke 수 파생 문서 249→250 | `docs/CODE_INDEX.md`, `docs/INSTALLATION_AND_USAGE.md`, `releases/Beta-v1.1.6.md` |

해소한 결함 (세션 중 실측 2건 포함 4건):

1. `find_latest_backlog_path` 인덱스 전제 — branch-scoped 저장소에서 task 상세
   파일을 최신 backlog 로 오판 → 인덱스가 없으면 daily 디렉터리 관측으로 판정.
2. `wk session-start` 무인자 호출 불가 — §11 안내와 실행 가능 명령의 간극 → 자동 탐색.
3. `_build_memory_index_query_output` 이 args 경유로 미해석 경로를 읽던 TypeError.
4. self-bootstrap 안내가 배포되지 않는 `skills/` 경로를 가리킴 → `wk session-start`.

## 3. 진행 중 실측된 도구 결함 (미수정, 후속 후보)

- **`wk backlog-update --mode update` 가 task 파일을 전체 재생성** — 미지정
  필드(작업 내용·완료 기준·담당·`kind`)를 삭제한다. daily index 의 항목도 같은
  방식으로 요약본으로 덮인다. 이번 세션에서 TASK-018 파일이 실제로 이렇게 깎여
  손으로 복원했다. 처방 후보: update 모드는 기존 파일을 읽어 미지정 필드를 보존.
- **handoff `in_progress` 중복 bullet** — 같은 task 를 표기만 다르게 한 줄 더
  추가한다 (task ID 기준 dedupe 부재).

## 4. 리뷰 3종 결함 목록 (2026-08-11, 6차 세션)

### 4.1 하네스 파생본 (정본→파생 배포)

정상 확인: `check_standard_single_source` 7/7, 스냅샷 정본 일치, 주입 렌더러 9 +
직접 주입 4, 루트 `CLAUDE.md` 정합.

- **§11.1 명령 문자열의 손 사본 7곳이 검사 사각지대** — `renderers.py:1093/1150/1207`
  (claude-code command 3) + `:1467/1471/1475` (goose) + `.claude/commands/*.md` 3개.
  `_rule_literals()` 가 `principles`+`close_order` 만 보므로 §11.1 개명 시 이들만 낡는다.
- **`render_goose_config` hook 에 깨진 경로 잔존** — `renderers.py:1489`
  `on_session_end` 가 존재하지 않는 `ai-workflow/skills/.../run_session_start.py
  --update-handoff` (플래그도 없음) 를 부른다. TASK-022 의 "goose 교체" 가 entry_points
  3곳만 갈고 hook 을 놓쳤다.
- **`mavis` 가 PRIMARY/EXEMPT 어느 쪽에도 없음** — `PRIMARY ∪ EXEMPT ==
  SUPPORTED_HARNESSES` 를 단언하는 코드가 없어 "새 하네스 누락을 검사가 잡는다" 는
  보장이 구조적으로 성립 안 함.
- **잔여 14개 렌더러가 미열거·과소기술** — 그중 6개는 TASK-020 이 1순위로 분류한
  에이전트 진입점 (`grok_build_skill` 최고 밀도 22건 포함). TASK-020 표합계 33 vs
  모집단 32 로 baseline "26" 도 완전 재구성 불가.
- 루트 `AGENTS.md` (gitignored) 낡음 — §11 이전 마커, §1 bullet 6/8.
  `check_self_application` 이 §11 을 탐침하지 않아 못 잡는다.

### 4.2 스킬·CLI

정상 확인: 구현 3종 verbatim 이동 + thin wrapper, `wk` 71(현재 72), dispatcher
검사 10/10, pyproject 거짓 전제 정정.

- **정본 `SKILL.md` 3종이 여전히 미배포 경로를 지시** — `skills/*/SKILL.md` 와
  `harnesses/claude-code/apply_guide.md:137,146` 이 `python3 skills/.../run_*.py` 안내.
- **`bootstrap --copy-core-docs` 가 wrapper 를 복사하는데, 복사본은 pip 설치 없이
  동작 불가** (`from tools... import` 실패) — TASK-021 이전 복사본은 자립형이었으므로
  이 조합에선 회귀.
- **`check_packaging` 의 `REQUIRED_IMPORTS` 에 `tools` 부재** — "tools/ 는 배포된다"
  는 TASK-021 의 전제가 wheel 에서 검증되지 않는다.
- `.venv` 에 낡은 editable(0.5.10b0) + `build/lib` 잔재 (환경 문제).

### 4.3 MCP

- **`readOnlyHint: true` 허위 주석** — `read_only_registry.py:440` 이 전 도구에
  하드코딩하는데 `apply_robust_patch` 는 실제로 파일을 쓴다 (`patching.py:218`,
  dry_run 입력조차 없음). `rotate_workflow_logs` 도 쓴다. 심지어
  `check_read_only_mcp_server.py:57` 이 이 허위를 **강제**한다.
- **ADR-003 낡음** — "6+1 도구, write 0" 서술 vs 실제 13 도구 + write 2.
- **레지스트리 이원화** — MCP `READ_ONLY_TOOL_SPECS`(13) 와 CLI
  `TOOL_MODULES`/`COMMANDS` 가 상호 무관, 겹침 5개뿐. session-start 3종은 CLI 전용
  (의도 문서 없음).
- **MiniMax MCP 렌더러의 손 목록 10개** (`bootstrap_lib/mcp.py:289`) 가 레지스트리
  13개와 어긋남 (3개 누락), 대조 검사 없음.
- **manifest 의 유령 경로** — `read_only_registry.py:297,321` 의 `script_path` 가
  존재하지 않는 `mcp_servers/...` 디렉터리를 광고.

## 5. 교훈

- **도구를 만들었으면 그 도구로 자기 저장소부터 돌려본다** — `wk backlog-update`
  1회 실행이 파괴적 update 와 handoff 중복을 즉시 드러냈다. 노출(TASK-021)과
  실사용 사이에 검증 공백이 있었다.
- **"안내하는 명령 = 실행 가능한 명령"** 은 §11 이후에도 저절로 성립하지 않는다 —
  무인자 호출 불가가 그 간극이었다.
- 살아있는 저장소 정합 검사(case 5)는 **세션 종료 절차(refresh)가 지켜질 때만
  green** — 검사가 절차를 강제한다.
