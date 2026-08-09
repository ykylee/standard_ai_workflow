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
- 다음 후보 축: **Phase 13 P0-2** (telemetry source 다양성 — 실측 `by_source` 는 `session-start` 하나인데 문서는 'dispatcher' 라 적혀 있다) / **릴리스 도구 결함 2건** / Phase 13 P1 묶음.
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
- TASK-2026-08-09-main-008 v1.1.2-beta release — 본 세션 TASK-001~007 묶음. 릴리스 하나로 셋이 닫혔다: **`check_smoke_trend_cross`**(마지막 실질 red — 노트의 *누적 smoke* 줄이 `cumulative_total` 234 → 257) / **Phase 13 P0-1**(mypy strict venv verify, 128 files clean) / 문서 stamp 확정. **전체 257/257 PASS** — 오늘 아침 31 red → 0. **릴리스 도구 결함 2건 발견** — `release-bump` post-step 이 `git add` 경로를 중복 prefix 로 넘겨 실패 / `release-verify` 가 `AttributeError: 'dry_run'` 로 죽음. 둘 다 자동화 경로에만 있고 릴리스는 수동으로 완주했다. **릴리스 도구는 릴리스 때만 돌아 평소 검사에 안 걸린다** (`check_release_pipeline_lib` 9 case green 인데도 못 잡았다). + `release_pipeline_lib` dist skip 테스트가 버전 bump 직후 일회성 red.
- TASK-2026-08-09-main-007 남은 red 4건 close — TASK-006 이 "범위 밖"으로 남긴 근거가 **내가 잘못 센 숫자**였다. fixture 3건 재생성(stamp 6건과 같은 뿌리인데 놓쳤다) / 정리 없는 `mkdtemp` 11건 / `"/var/tmp"` 문자열 비교가 macOS 에서 늘 red (**구현은 정상, 검사가 플랫폼을 못 넘김**) / worker 가 local function 이라 **Linux 에서만 돌던 검사** / `release-doctor` mypy gate 의 뿌리인 `workspace_registry.py` **24건** 정리 → `workflow_kit/` **128 files clean 복구**. 부수 R3 1건(`survey()` 가 `repo_root` 를 받는데 브랜치는 모듈 앵커에서 얻던 것) → `branch_slug_for()` 신설. 효과: Phase 13 **P0-1 acceptance 실측 충족** + dashboard `guard_status` fail → **pass**.
- TASK-2026-08-09-main-006 rotate 도구 수정 + 사전 존재 red 검토 — **순서 규약을 최신-앞으로 통일했다**. `state.json.recent_done_items`(최신-앞)와 handoff §4 writer(뒤-최신 `append`)가 같은 사실을 반대로 들고 있었고, 실제 문서는 최신-앞이라 writer 를 고쳤다. `rotation.py` 는 결함이 둘 — 섹션 고정 문자열(늘 error) + `items[-max:]`; **섹션만 고쳤다면 도구가 동작하면서 최신을 지웠다**. `check_handoff_rotation.py` 9/9 신규 (이 도구엔 회귀 검사가 없었다). red: stamp 계열 6건 해소 + 내가 만든 신규 2건 즉시 해소 (`check_cli_wrappers` 가 저장소 실제 handoff 를 쓰고 있었다). **최종 전체 검사 red 5건, 전부 사전 존재**. 앞서 보고한 31/24 는 편집 중 실행이라 무효.
- TASK-2026-08-09-main-005 title semantic drift v2 — v1 은 TASK-ID *집합* 만 봐서 "TASK-001 계획 → TASK-001 완료" 면 내용이 통째로 바뀌어도 clean 이었다. v2 는 같은 ID 의 **제목** 을 `difflib` 로 비교해 후보를 고르고 판정은 LLM prompt 로 넘긴다 (`purpose_refresh` 와 같은 advisory 모델). `title_drift` **additive** (v1 필드 불변). 실측 함정: handoff §5 는 ID 가 **뒤에** 와서 처음엔 설명 꼬리를 집었다 → ID 앞 텍스트 우선으로 수정 + 회귀 케이스. 11/11 PASS.
- TASK-2026-08-09-main-004 branch protection 자동 check (3rd layer) — layer 2 는 로컬 설치형이라 hook 미설치 호스트를 못 막는다. 그 구멍인 서버측 protection 이 *가이드* 로만 있었다. 판정을 pure function 으로 분리 (gh 없이 fixture 검사). **보호를 켜지 않고 판정만** 한다. 필드를 못 읽으면 통과로 치지 않는다. gh 부재는 graceful skip (모름 ≠ 없음). 8/8 PASS. **실측: 이 저장소 main 에 protection 없음(404)**.
- TASK-2026-08-09-main-003 registry HTTP server (federation *쓰기*) — TASK-016 이 닫은 pull 의 상대편. 구멍이 둘이었다: 서빙하는 쪽 부재 + `add_known_host()` API 는 있는데 **부르는 CLI 가 없어** 상대가 등록조차 못 했다. loopback 기본 / read-only(405) / 경로 2개만 / 토큰은 환경변수 *이름* 으로 / registry 부재 → 빈 registry. 9/9 PASS — 실제로 서버를 띄워 pull 로 되받는다.
- TASK-2026-08-09-main-002 CLI 化 B안 단일 dispatcher `wk` — **새 dispatcher 를 만들지 않았다**. `workflow_kit_cli.py` 가 이미 38 subcommand dispatcher 여서 기존 registry 를 확장했다 (사용자 확인). 정공법도 이미 있던 것(`sys.argv` 치환 + SystemExit → rc)을 29개로 일반화. `TOOL_MODULES` ↔ `[project.scripts]` 일치를 smoke 가 강제. 10/10 PASS + venv e2e (`wk` + 29 binary, 65 command).
- TASK-2026-08-09-main-001 memory 문서 정합성 정리 — backlog 인덱스 TASK-020 `planned` → `done` + 깨진 `path:` href 3건(018·019·020, `-08-main` 누락) / task 본문 `- 상태: planned` 7건(014~020) → `done` / state.json `backlog.done_items` 에 014~020 + `recent_done_items` 에 018 / handoff stale 4곳. `check_self_application` 7/8 → **8/8 PASS**. state.json 전면 재생성은 **안 했다** — 재생성본이 `done_items` 를 10건으로 자르고 `current_focus` 를 끝난 TASK-014 로 잡아 정보가 깎인다.
- TASK-2026-08-08-main-020 `[project.scripts]` entry points (CLI 化 A안) — 29 entry point (`workflow-{name}`) + `tools` packages 등록. venv e2e (`pip install -e .` → 29 binary + `--help`) + 4 case smoke ALL PASS. **v1.1.1-beta release** (`6b92a60`). dispatcher `wk` (B안) = 후속.
- TASK-2026-08-08-main-019 `--force` server-side 이중화 (§0.8 #4) — **3-layer defense**: 도구 미제공(기존) + **pre-push hook**(본 task) + server branch protection(가이드). `tools/hooks/pre-push-no-force.sh` (POSIX sh, force 5변형 거부) + `tools/install_pre_push_hook.py` (install/uninstall/status, dry-run default, backup 자동) + smoke 7 case ALL PASS. **v1.1.0-beta release** (`564ce36`).

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
