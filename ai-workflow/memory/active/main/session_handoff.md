# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-09 (memory 정합성 정리 + session close)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **v1.1.2-beta 발행 완료** (2026-08-09, tag `v1.1.2-beta` → `b688a06`, [GitHub Release](https://github.com/ykylee/standard_ai_workflow/releases/tag/v1.1.2-beta)). 본 세션 TASK-001~008. 전체 검사 **257/257 PASS** — 오늘 아침 baseline 31 red → 0. `workflow_kit/` mypy strict 128 files clean, dashboard `guard_status` pass. 직전: v1.1.0-beta (564ce36) → v1.1.1-beta (6b92a60).
- 현재 주 작업 축: **다음 후보 축 4건 전부 close** (TASK-2026-08-09-main-002~005, 본 세션). handoff §5 에 후보로 적어 뒀던 4건을 모두 구현했다 — CLI 化 B안 `wk` / registry HTTP server / branch protection 자동 check / title drift v2. 38 case smoke ALL PASS + venv e2e. 앞서 같은 세션에서 memory 정합성 정리(TASK-001, `check_self_application` 7/8 → **8/8**)를 먼저 했다.
- 직전 주 작업 축: **v1.1.1-beta release** (CLI 化 A안 — `[project.scripts]` 29 entry point). venv e2e 검증 완료 (`pip install -e .` → 29 binary + `--help` 정상). §0.8 의 *열린 채로* 남아있던 4건 모두 close + CLI 化 A안 close.
- 직전 축: **TASK-020** (29 entry points + venv e2e + 4 case smoke ALL PASS) + **TASK-019** (3-layer defense — pre-push hook) + **TASK-018** (scope drift detection) + **TASK-017** (operational CLI dual mode) + **TASK-016** (federation HTTP pull) + **TASK-015** (federation 정공법) + **TASK-014** (in-flight confidence 4-level) + **TASK-013** (mavis attach e2e) + **TASK-012** (갈래2 trust). 9 TASK + §2.68 cycle + CLI 化 A안 = 2 release.
- 다음 후보 축: **`memory-index-query` beta → stable** (유일 잔여 beta) / branch protection (소유자 결정).
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
- TASK-2026-08-09-main-015 `check_smoke_trend_cross` **오독 정정 — 검사가 맞았다**. 노트의 누적 수치는 *릴리스 스냅샷이 아니라 살아있는 지표* 였다 (smoke 가 늘면 최신 노트를 갱신해 온 관행; `Beta-v1.0.0.md` 199→…→234). 내가 본 '모순' 은 **사후 갱신을 모르고** 한 오독 — 태그 시점엔 199/199 정합. red 구간은 v1.1.0·v1.1.1 이 **표기를 빠뜨린** 탓. 판정 복원 + 노트 257→**259**. **검사를 고치기 전에 그 검사가 지켜 온 관행을 먼저 확인한다.**
- TASK-2026-08-09-main-014 `memory-index-query` **beta → stable** — §3.1 6 조건 중 2 미충족을 채움: **error_code 3종**(이전엔 stderr + rc 2 뿐이라 실패 종류 구분 불가 → `ErrorOutput` 을 stdout 에) + SKILL.md 실행 예시. smoke 26/26. **skill 14 stable / 0 beta**. **이번엔 문서가 맞았다** — 기준 문서(criteria)는 살아 있었고 상태 문서만 낡았다.
- TASK-2026-08-09-main-013 `phase_13_followup` **전반 실측 대조** — 정합 5 / 정정 3. **harness 는 숫자가 아니라 정의가 문제였다**: `mavis` 를 matrix 에 넣자 `check_harness_v0_15_9` 가 깨졌고, 그건 **project-local 산출물 0** 인 harness 라 디렉터리 없는 게 설계였기 때문이다 (`custom` 도 같은 부류). `harnesses.supported` = *overlay 배포* 목록 → 11 이 맞다. `NON_OVERLAY_HARNESSES` 에 이유와 함께 선언. **검사도 하드코딩 10개에 갇혀 새 harness 를 몰랐다** → 정본 유도로 교체.
- TASK-2026-08-09-main-012 Phase 13 **P1 묶음 close** — **세 항목이 전부 실제와 달랐다**. P1-1 "pre-step 부재" → v0.15.21+ 에 이미 있었고, 남은 건 (a) 최근 3 release 가 수동 발행이라 CHANGELOG 가 안 갱신된 것(**오늘 내가 그렇게 냈다**) (b) `(v3.0)` 오탐이 `[3.0.1]` 을 최신 자리에 앉힌 것 → `NON_RELEASE_VERSIONS` 선언 예외. P1-2/P1-3 은 **이미 v0.11.24 에서 stable**. 실측 skill stage **13 stable / 1 beta**(유일 beta = `memory-index-query`).
- TASK-2026-08-09-main-011 telemetry acceptance 를 **윈도 기반** 으로 — TASK-010 이 적은 사각을 메움. `summarize_telemetry(window_days=30)` 에 `window_source_count` 등 additive (전체 기간 필드 불변). `check_telemetry_window.py` 8/8 — **case 4 가 핵심**: *전체 4 source 인데 윈도 1* 을 잡는다. AC2 acceptance 를 "최근 30일 window_source_count ≥ 4" 로 갱신. 발견: `check_telemetry_source_diversity.py` docstring 은 자동 활성 전환을 **이미 정확히 적고 있었다** — TASK-010 의 문서 오류를 **검사는 알고 있었다**.
- TASK-2026-08-09-main-010 Phase 13 **P0-2 close** — AC2 4 source + hit_rate 1.0 수렴. **문서가 두 군데 틀려 있었다**: 1 source 는 `dispatcher` 가 아니라 `session-start` 였고(132 calls), "3 skill 활성화 필요" 는 **이미 v0.15.21+ 에서 끝난 일**이었다 (세 스크립트 코드가 동일). 남은 건 wiring 이 아니라 **실행 이력의 부재** — 한 번씩 돌리자 즉시 4 source. acceptance 약점도 기록: "4 source 등장" 은 1회씩이면 충족돼 *지속적 사용* 을 못 잰다.
- TASK-2026-08-09-main-009 릴리스 도구 결함 2건 수정 + 회귀 검사 — (1) `git add` 경로 중복: `release_pipeline.REPO_ROOT` 가 이름과 달리 `workflow-source/` 인데 porcelain 은 저장소 루트 기준 경로를 준다 → `_git_toplevel()` 신설. (2) `cmd_verify` AttributeError `dry_run` → defaults 안전측 True + wrapper 는 False 명시. (3) **`check_release_wrapper_args.py` 8/8 신설** — 릴리스 없이 잡히게 (AST 대조 + 두 cwd 의 `git add --dry-run` 대비로 **버그 자체를 회귀로 고정**). 검사 오탐 1건도 고쳤다 — 범위가 실제 호출 경로보다 넓으면 없는 결함을 만든다.
- TASK-2026-08-09-main-008 v1.1.2-beta release — 본 세션 TASK-001~007 묶음. 릴리스 하나로 셋이 닫혔다: **`check_smoke_trend_cross`**(마지막 실질 red — 노트의 *누적 smoke* 줄이 `cumulative_total` 234 → 257) / **Phase 13 P0-1**(mypy strict venv verify, 128 files clean) / 문서 stamp 확정. **전체 257/257 PASS** — 오늘 아침 31 red → 0. **릴리스 도구 결함 2건 발견** — `release-bump` post-step 이 `git add` 경로를 중복 prefix 로 넘겨 실패 / `release-verify` 가 `AttributeError: 'dry_run'` 로 죽음. 둘 다 자동화 경로에만 있고 릴리스는 수동으로 완주했다. **릴리스 도구는 릴리스 때만 돌아 평소 검사에 안 걸린다** (`check_release_pipeline_lib` 9 case green 인데도 못 잡았다). + `release_pipeline_lib` dist skip 테스트가 버전 bump 직후 일회성 red.
- TASK-2026-08-09-main-007 남은 red 4건 close — TASK-006 이 "범위 밖"으로 남긴 근거가 **내가 잘못 센 숫자**였다. fixture 3건 재생성(stamp 6건과 같은 뿌리인데 놓쳤다) / 정리 없는 `mkdtemp` 11건 / `"/var/tmp"` 문자열 비교가 macOS 에서 늘 red (**구현은 정상, 검사가 플랫폼을 못 넘김**) / worker 가 local function 이라 **Linux 에서만 돌던 검사** / `release-doctor` mypy gate 의 뿌리인 `workspace_registry.py` **24건** 정리 → `workflow_kit/` **128 files clean 복구**. 부수 R3 1건(`survey()` 가 `repo_root` 를 받는데 브랜치는 모듈 앵커에서 얻던 것) → `branch_slug_for()` 신설. 효과: Phase 13 **P0-1 acceptance 실측 충족** + dashboard `guard_status` fail → **pass**.
- TASK-2026-08-09-main-006 rotate 도구 수정 + 사전 존재 red 검토 — **순서 규약을 최신-앞으로 통일했다**. `state.json.recent_done_items`(최신-앞)와 handoff §4 writer(뒤-최신 `append`)가 같은 사실을 반대로 들고 있었고, 실제 문서는 최신-앞이라 writer 를 고쳤다. `rotation.py` 는 결함이 둘 — 섹션 고정 문자열(늘 error) + `items[-max:]`; **섹션만 고쳤다면 도구가 동작하면서 최신을 지웠다**. `check_handoff_rotation.py` 9/9 신규 (이 도구엔 회귀 검사가 없었다). red: stamp 계열 6건 해소 + 내가 만든 신규 2건 즉시 해소 (`check_cli_wrappers` 가 저장소 실제 handoff 를 쓰고 있었다). **최종 전체 검사 red 5건, 전부 사전 존재**. 앞서 보고한 31/24 는 편집 중 실행이라 무효.

## 5. 다음 세션 시작 포인트

**이번 세션 기록**: [sessions/cli_dispatcher_and_rotation_2026-08-09.md](./sessions/cli_dispatcher_and_rotation_2026-08-09.md)
— 이미 있는 것을 다시 만들 뻔한 일 2건, 고장난 도구가 숨긴 결함, 검사 설계 원칙,
사고 1건이 거기 있다. 맥락이 필요하면 그걸 읽는다.

이전 세션(설계 → §10.2 도구화 → registry)의 맥락은
[2026-08-08 기록](./sessions/multi_workspace_orchestration_2026-08-08.md)에 있다.

### 무엇이 끝났나

`origin/main` = `6cfb168`. 이번 세션 커밋 3건 / TASK 6건.

| 커밋 | 내용 |
| --- | --- |
| `4e31d8c` | memory 문서 정합성 정리 (TASK-001) |
| `ad3ab02` | 후보 축 4건 close — `wk` / HTTP server / branch protection / title drift v2 (TASK-002~005) |
| `6cfb168` | rotate 도구 순서 규약 통일 + 사전 존재 red 정리 (TASK-006) |

세션 시작 플로우는 그대로다 (v1.1.2+ 부터는 `wk` 로도 부를 수 있다):

```bash
wk survey-remote-workspaces
wk claim-workspace --branch <b> --axis "<축>" --task-title "<제목>" --apply
python3 workflow-source/scripts/generate_workflow_state.py \
  --project-profile-path docs/PROJECT_PROFILE.md --output-path ai-workflow/memory/active/<b>/state.json
```

federation 을 실제로 돌리려면 (v1.1.2+):

```bash
wk host-serve-registry --port 8765                      # 이 호스트가 서빙
wk host-pull-registry add-known-host --host-id <상대> \
    --endpoint http://<host>:8765/registry.json --apply  # 상대 등록
wk host-pull-registry pull --host <상대>
```

### 다음에 할 일 (순서)

- **§2.68 cycle** — ✅ **전부 닫힘** (TASK-006~013, 8커밋). 사용자가 본 세션 (2026-08-08 22:06 KST) 에서
  *갈래2 trust* 채택 — e2e smoke 가 실제 attach 경로와 100% 동치 subprocess 라는 근거.
- **§0.8 #2 in-flight 신뢰도** — ✅ **닫힘** (TASK-2026-08-08-main-014, 본 세션). 4-level enum + Panel 5
  inline badge + 8 case smoke ALL PASS. registry 의 §5A.3 *첫 소비자* 자리 채워짐.
- **§0.8 잔존 3건** — ✅ **전부 닫힘** (본 세션 후반):
  - #1 registry 저장 위치 → **TASK-015** federation 정공법 (`merge_entries` + known_hosts) + **TASK-016** HTTP pull.
  - #3 범위 이탈 검출 → **TASK-018** scope drift detection (3-way enum + drift_score).
  - #4 `--force` 이중화 → **TASK-019** 3-layer defense (pre-push hook).
- **묶음 release** — ✅ **발행 완료**. v1.1.0-beta (`564ce36`, §0.8 4건 + dual mode + federation *읽기*)
  → v1.1.1-beta (`6b92a60`, CLI 化 A안 29 entry points).
- **다음 후보 축 4건** — ✅ **전부 닫힘** (2026-08-09, TASK-002~005):
  - CLI 化 B안 `wk` → **TASK-002**. 기존 `workflow_kit_cli` 확장 (새 dispatcher ❌). 65 command.
  - registry HTTP server → **TASK-003**. serving + `add-known-host` CLI (둘 다 없었다).
  - branch protection 자동 check → **TASK-004**. 판정만 한다. 실측 결과 이 저장소는 **미보호**.
  - title semantic drift v2 → **TASK-005**. `difflib` 후보 선별 + LLM prompt (advisory).
- **다음 후보 축** (다음 세션에서 결정):
  - **v1.1.2-beta release** — 위 4건 묶음. 발행 여부/시점 판단 필요.
  - **rotate 도구 순서 규약 불일치** (아래 §6, 신규 발견) — 규약 결정이 선행돼야 한다.
  - Phase 13 진입.

## 6. 남은 리스크 / 확인하지 못한 것

**사전 존재 red — 4건 모두 닫힘**:

| 검사 | 상태 |
| --- | --- |
| `check_appendonly_memory_layout` | ✅ **닫음** — 2026-08-06 task 3건에 frontmatter 추가 |
| `check_self_application` (`handoff_bloat`) | ✅ **닫음** — 본 문서 1096줄 → 106줄, done items 10/10. **8/8 passed** |
| `check_standard_single_source` | ✅ **닫음** (TASK-2026-08-08-main-005) — `ai-workflow/core/mcp_installation_by_harness.md` 사본을 정본(`workflow-source/core/...`)으로 cp 동기화. 7/7 PASS. 정본 = 2026-08-07 00:12 갱신본 (mavis 데스크탑 §1.2.1 + §6.5.2). |
| `check_bootstrap_interactive_picker` | ✅ **닫음** (TASK-2026-08-08-main-005) — `bootstrap_lib.__main__` / `bootstrap_lib.harnesses` 가 `workflow-source/scripts/` 안에 있어 in-process tests 가 `sys.path` 에 `SCRIPTS_DIR` 를 올리도록 1줄 보강. 10/10 PASS. |

**별건 1**: dashboard `drift_prevention.guard_status: fail` — `maturity_last_updated` stale.
갱신 힌트는 dashboard 출력의 `maturity_refresh_hint`.

**별건 3 — 전체 검사 red (2026-08-09 최종 실측)**:

편집을 멈추고 돌린 전체 검사(격리 venv)에서 **red 5건, 전부 사전 존재**
(`git stash` 로 개별 확인). 본 세션이 만든 red 는 0건이다.

| 검사 | 증상 | 판단 |
| --- | --- | --- |
| `check_smoke_trend_cross_v0_15_5` | `cum_total=234 < smoke_files=257` | 릴리스 사이클에서 닫힌다 (아래) |
| `check_source_without_runtime_layer` | `read_only_jsonrpc_fixtures.json` stale | fixture 재생성 필요 |
| `check_tempdir_leak_guard` | 정리 없는 `mkdtemp` 11건 | 기존 테스트들의 문제 |
| `check_wiki_url_validity` | `PicklingError` (local object) | 테스트 자체 결함 |
| `check_workflow_kit_cli` | `test_release_doctor_all_skip` 1건 | — |

**`check_smoke_trend_cross` 보류 이유**: `cumulative_total` 은 *가장 최근 릴리스 노트*
에서 파싱하는데 v1.1.0 / v1.1.1 노트에 "누적 smoke **N/N PASS**" 줄이 없어 그보다
이전인 v1.0.0 의 234 를 읽는다. 고치려면 **이미 발행된 노트를 사후 수정** 해야 한다.
다음 릴리스 노트에 그 줄을 적으면 자연히 닫힌다.

**해소한 것** (stamp 계열 6건): README / RELEASE.md / CODE_INDEX / INSTALLATION 의
버전·smoke count stamp + `examples/output_samples/*.json` 24건의 `tool_version` +
`check_mcp_apply_mode_criterion` (환경 — 시스템 python3 에 `mcp` 미설치, 설치 후 2/2 PASS).

> **숫자를 두 번 잘못 셌다**: `[FAIL]` 패턴만 grep 해 7건이라 한 것, 그리고 전체 실행
> 두 번(31 / 24건)이 **편집 도중에** 돌아 반쯤 바뀐 트리를 본 것. 검사는 트리가
> 멈춘 뒤에 돌려야 한다.

**구현했지만 검증 못 한 것**:

- 도구 3종은 **로컬 bare remote** 로만 검증했다. GitHub 등 실제 원격의 protected branch /
  push 권한 정책 아래에서는 다르게 동작할 수 있다.
- `--force` 는 **2-layer 까지 적용** (도구 미제공 + pre-push hook, TASK-019). hook 은 로컬
  설치형이라 **미설치 호스트는 여전히 막지 못한다.** 3rd layer 는 이제 *확인* 은 되지만
  (TASK-004) **이 저장소 `main` 에 실제로 켜져 있지 않다** (404 실측). 켜는 건 소유자 판단.
- registry HTTP server (TASK-003) 는 **loopback 왕복만 실측**했다. 실제 LAN / 방화벽 너머,
  reverse proxy 뒤, TLS 종단 환경에서는 확인한 적이 없다.
- title drift 임계 0.6 (TASK-005) 은 **운영 데이터로 고른 값이 아니다.** 이 저장소 실측에서
  같은 일의 표현 차이도 후보로 올라온다 (similarity 0.48).
- stale 임계 24h 는 heuristic 이다. 실제 운영 데이터로 조정한 적 없다.

**이전 세션들의 교훈**은 각 세션 기록에 있다:
[2026-08-08](./sessions/multi_workspace_orchestration_2026-08-08.md) ·
[2026-08-05](./sessions/self_application_and_mcp_2026-08-05.md) ·
[2026-08-07 MCP](./sessions/mcp_load_verification_2026-08-07.md) ·
[2026-07-27](./sessions/selfref_cleanup_and_ci_measurement_2026-07-27.md)
