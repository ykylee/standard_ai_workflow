# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-12 (22차 세션 종료 — 멀티 하네스 공유 플러그인 검토 완료)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **22차 세션 종료 — 멀티 하네스 공유 플러그인 검토 완료 (TASK-2026-08-12-main-012, 사용자 지시).** 판정: **가능 — 공유 payload + 하네스별 얇은 manifest.** 무변환 단일 아티팩트는 부분 성립 (Agent Skills `SKILL.md` ~40제품 / **Agent Plugins 1.0** — 2026-08-06 출범, 5클라이언트 — 단 Claude Code·Gemini·goose·OpenCode 미합류). 권고: payload 물리 배치를 Agent Plugins 1.0 레이아웃 (`plugin.json`+`skills/`+`mcp.json`) 으로 채택 + 어댑터 4장, TASK-011 Phase A 를 `render_agent_plugin()` 계열로 재정의 (소유자 go 대기). 검토 문서: docs/planning/multi-harness-plugin-review-2026-08.md. 상세: [22차 세션 기록](./sessions/multi_harness_plugin_review_2026-08-12.md).
- 직전 기준선: **21차 세션 종료 — 플러그인 배포 검토 완료 (TASK-2026-08-12-main-011, 사용자 지시).** 결론: **채택 권고, 단 14번째 파생본으로** (렌더러 생성 + 검사 강제 — 손 플러그인 금지). 핵심 갭 = CLAUDE.md 형 상시 주입 불가 (SessionStart hook 실측 전까지 bootstrap 주입 유지) + Python 은 uv 전제. 이행 Phase A(렌더러)→B(marketplace)→C(실측 3건). 검토 문서: docs/planning/plugin-distribution-review-2026-08.md. 상세: [21차 세션 기록](./sessions/plugin_distribution_review_2026-08-12.md).
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
- 현재 주 작업 축: (없음 — 2026-08-12 backlog 1건 done. 다음 축: cross-host federation — **두 번째 호스트 = MacBook (darwin homelab) 으로 확정, 시점은 추후** (사용자 결정 2026-08-12, 현재 MacBook 전원 꺼짐). 합류는 MacBook 쪽 세션에서 environments/plex.md 절차 두 명령 (`add-known-host` + `pull`, 토큰 값 전달 필요) / darwin mavis e2e / memory_index 3-tuple 추이).
- ~~소유자 결정 대기: state.json 생성물 여부~~ — ✅ **해소** (TASK-018, 2026-08-11): **생성물로 확정.** 정본 §11.2 에 선언, `wk refresh-state` 로 재생성, `check_state_json_generated` case 5 가 이 저장소의 정합을 상시 검사. 상세 요약·산문은 state.json 이 아니라 handoff §4 와 task 파일(SSOT)에 남긴다.
- 다음 후보 축: ~~federation self-host add~~ ✅ (14차, plex 상시 가동) → cross-host federation (두 번째 호스트 = **MacBook 확정, 시점 추후** — 2026-08-12 사용자 결정, 합류 두 명령) / memory_index 3-tuple 지표 추이 관찰. **v1.1.6-beta 발행 완료, ADR-006 후속 W-1~W-4 완결**. (v1.1.0·v1.1.1 노트 누적 표기는 TASK-014 에서 **미삽입 확정**, branch protection 은 소유자가 **보류 결정** (2026-08-11) — 둘 다 후보 축에서 제거.)
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
- TASK-2026-08-12-main-012 멀티 하네스 공유 플러그인 형태 검토
- TASK-2026-08-12-main-011 워크플로우 플러그인 형태 재구성·배포 검토
- TASK-2026-08-12-main-010 v1.1.8-beta 발행 (cmd_release 5번째 실전)
- TASK-2026-08-12-main-009 check_no_repo_write 실행-중 감시 강화
- TASK-2026-08-12-main-008 backlog-update --status 미지정 시 기존 상태 보존
- TASK-2026-08-12-main-007 네임스페이스 격상 2단계 — bootstrap_lib 를 workflow_kit.bootstrap_lib 로
- TASK-2026-08-12-main-006 네임스페이스 격상 — tools/bootstrap_lib 를 workflow_kit.* 로
- TASK-2026-08-12-main-005 CLI cross-platform 지원 (Linux/macOS/Windows)
- TASK-2026-08-12-main-004 CLI 툴(wk) 배포 방법 검토
- TASK-2026-08-12-main-003 MCP bundle 분리 — write 도구 2종을 별도 bundle 로
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
