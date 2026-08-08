# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-09 (memory 정합성 정리 + session close)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **v1.1.1-beta** + `origin/main` = `678806f` (2026-08-08, **§0.8 4건 close + dual mode + federation *읽기* + CLI 化 A안 묶음 release**). 2 release 발행 — v1.1.0-beta (564ce36) → v1.1.1-beta (6b92a60). tag `v1.1.1-beta` push + GitHub Release 발행.
- 현재 주 작업 축: **다음 후보 축 4건 전부 close** (TASK-2026-08-09-main-002~005, 본 세션). handoff §5 에 후보로 적어 뒀던 4건을 모두 구현했다 — CLI 化 B안 `wk` / registry HTTP server / branch protection 자동 check / title drift v2. 38 case smoke ALL PASS + venv e2e. 앞서 같은 세션에서 memory 정합성 정리(TASK-001, `check_self_application` 7/8 → **8/8**)를 먼저 했다.
- 직전 주 작업 축: **v1.1.1-beta release** (CLI 化 A안 — `[project.scripts]` 29 entry point). venv e2e 검증 완료 (`pip install -e .` → 29 binary + `--help` 정상). §0.8 의 *열린 채로* 남아있던 4건 모두 close + CLI 化 A안 close.
- 직전 축: **TASK-020** (29 entry points + venv e2e + 4 case smoke ALL PASS) + **TASK-019** (3-layer defense — pre-push hook) + **TASK-018** (scope drift detection) + **TASK-017** (operational CLI dual mode) + **TASK-016** (federation HTTP pull) + **TASK-015** (federation 정공법) + **TASK-014** (in-flight confidence 4-level) + **TASK-013** (mavis attach e2e) + **TASK-012** (갈래2 trust). 9 TASK + §2.68 cycle + CLI 化 A안 = 2 release.
- 다음 후보 축: **v1.1.2-beta release 판단** (본 세션 4건 묶음) / rotate 도구 순서 규약 불일치 정리 (아래 §6) / Phase 13 진입.
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
- TASK-2026-08-09-main-005 title semantic drift v2 — v1 은 TASK-ID *집합* 만 봐서 "TASK-001 계획 → TASK-001 완료" 면 내용이 통째로 바뀌어도 clean 이었다. v2 는 같은 ID 의 **제목** 을 `difflib` 로 비교해 후보를 고르고 판정은 LLM prompt 로 넘긴다 (`purpose_refresh` 와 같은 advisory 모델). `title_drift` **additive** (v1 필드 불변). 실측 함정: handoff §5 는 ID 가 **뒤에** 와서 처음엔 설명 꼬리를 집었다 → ID 앞 텍스트 우선으로 수정 + 회귀 케이스. 11/11 PASS.
- TASK-2026-08-09-main-004 branch protection 자동 check (3rd layer) — layer 2 는 로컬 설치형이라 hook 미설치 호스트를 못 막는다. 그 구멍인 서버측 protection 이 *가이드* 로만 있었다. 판정을 pure function 으로 분리 (gh 없이 fixture 검사). **보호를 켜지 않고 판정만** 한다. 필드를 못 읽으면 통과로 치지 않는다. gh 부재는 graceful skip (모름 ≠ 없음). 8/8 PASS. **실측: 이 저장소 main 에 protection 없음(404)**.
- TASK-2026-08-09-main-003 registry HTTP server (federation *쓰기*) — TASK-016 이 닫은 pull 의 상대편. 구멍이 둘이었다: 서빙하는 쪽 부재 + `add_known_host()` API 는 있는데 **부르는 CLI 가 없어** 상대가 등록조차 못 했다. loopback 기본 / read-only(405) / 경로 2개만 / 토큰은 환경변수 *이름* 으로 / registry 부재 → 빈 registry. 9/9 PASS — 실제로 서버를 띄워 pull 로 되받는다.
- TASK-2026-08-09-main-002 CLI 化 B안 단일 dispatcher `wk` — **새 dispatcher 를 만들지 않았다**. `workflow_kit_cli.py` 가 이미 38 subcommand dispatcher 여서 기존 registry 를 확장했다 (사용자 확인). 정공법도 이미 있던 것(`sys.argv` 치환 + SystemExit → rc)을 29개로 일반화. `TOOL_MODULES` ↔ `[project.scripts]` 일치를 smoke 가 강제. 10/10 PASS + venv e2e (`wk` + 29 binary, 65 command).
- TASK-2026-08-09-main-001 memory 문서 정합성 정리 — backlog 인덱스 TASK-020 `planned` → `done` + 깨진 `path:` href 3건(018·019·020, `-08-main` 누락) / task 본문 `- 상태: planned` 7건(014~020) → `done` / state.json `backlog.done_items` 에 014~020 + `recent_done_items` 에 018 / handoff stale 4곳. `check_self_application` 7/8 → **8/8 PASS**. state.json 전면 재생성은 **안 했다** — 재생성본이 `done_items` 를 10건으로 자르고 `current_focus` 를 끝난 TASK-014 로 잡아 정보가 깎인다.
- TASK-2026-08-08-main-020 `[project.scripts]` entry points (CLI 化 A안) — 29 entry point (`workflow-{name}`) + `tools` packages 등록. venv e2e (`pip install -e .` → 29 binary + `--help`) + 4 case smoke ALL PASS. **v1.1.1-beta release** (`6b92a60`). dispatcher `wk` (B안) = 후속.
- TASK-2026-08-08-main-019 `--force` server-side 이중화 (§0.8 #4) — **3-layer defense**: 도구 미제공(기존) + **pre-push hook**(본 task) + server branch protection(가이드). `tools/hooks/pre-push-no-force.sh` (POSIX sh, force 5변형 거부) + `tools/install_pre_push_hook.py` (install/uninstall/status, dry-run default, backup 자동) + smoke 7 case ALL PASS. **v1.1.0-beta release** (`564ce36`).
- TASK-2026-08-08-main-018 scope drift detection (§0.8 #3) — 3-way enum (`planned_done`/`planned_undone`/`unplanned_done`) + drift_score + score_band. `drift_detection.detect_scope_drift()` pure function + `tools/detect_scope_drift.py` CLI (advisory default, `--exit-on-drift` 시 non-zero). smoke 7 case ALL PASS. title semantic drift = v2 (LLM-based).
- TASK-2026-08-08-main-017 operational MCP tool 4종 CLI wrapper — **dual mode** (MCP server 무변경 + CLI 4개 추가). 같은 `*_payload` 호출 → CLI ↔ MCP *byte-equal*. rotate_workflow_logs / apply_robust_patch / create_environment_record_stub / check_quickstart_stale_links. smoke 4 case ALL PASS. 나머지 9 tool 은 MCP 유지 (LLM-interpretation 필수).
- TASK-2026-08-08-main-016 HTTP pull + dashboard federation 통합 — TASK-015 의 *읽기* 마무리. stdlib only (`urllib`) + remote cache TTL 1h + timeout 2s. **함정**: `time.mktime` 는 local TZ 해석 → KST 에서 9h 차이로 TTL 초과 → `calendar.timegm` 으로 정정. `tools/host_pull_registry.py` CLI. smoke 8 case ALL PASS.

## 5. 다음 세션 시작 포인트

**이번 세션 기록**: [sessions/multi_workspace_orchestration_2026-08-08.md](./sessions/multi_workspace_orchestration_2026-08-08.md)
— 판단을 뒤집은 실측 6건, 검사 설계 원칙, 사고 1건이 거기 있다. 맥락이 필요하면 그걸 읽는다.

### 무엇이 끝났나

아래는 세션 전반부(`838b12f` 시점)의 묶음이다. 6건 + 5건 후속 + 1건 collateral 로
설계 → 도구 → dashboard 다중 root → registry 까지 닫았다. 이후 TASK-014~020 이
이어졌고 최종 `origin/main` = `c0224c6` (§1 참조).

- **표준 §10 "다중 작업과 협업"** 신설 + §1 bullet 2건 → **12 하네스 진입점에 자동 전파**
  (빈 저장소 bootstrap 으로 `AGENTS.md` 2/2 · `GEMINI.md` 2/2 실측).
- **`.gitattributes`** (저장소 최초) — `log.md` / telemetry / daily backlog 에 `merge=union`.
  `state.json` 은 **의도적 제외** (union 이 JSON 을 깨뜨린다).
- **도구 3종** (smoke 25 assertions, 전부 green):
  - `survey_remote_workspaces.py` — 원격 현황. fetch 기본, stale 은 **보고만**.
  - `claim_workspace.py` — 브랜치+seed+push 1회. **`--force` 수단 없음**.
  - `seed_workspace_memory.py` — `active/<branch>/` 생성. `state.json` 은 안 만든다.
- **dashboard Panel 5 다중 root** (smoke 6/6):
  - `_branch_state_paths(*roots)` — union + dedupe + sort. **파생 뷰 원칙 유지**.
  - `collect_recent_releases(extra_roots=)` + `git worktree list --porcelain` 자동
    합류 + `WORKFLOW_EXTRA_ROOTS` env + **registry** (실제 채워짐).
- **workspace registry** (smoke 8/8, §7.1):
  - `workflow_kit/common/workspace_registry.py` — host-scoped
    `~/.cache/workflow_kit/registry.json` (atomic write, 0o600). `register` idempotent.
  - `tools/workspace_registry.py` — `register/unregister/list/paths/host-id`.
  - dashboard 가 registry paths 를 자동 합류 — §5A.3 *in-flight 가시성* 의 첫 소비자.

세션 시작 플로우:

```bash
python3 workflow-source/tools/survey_remote_workspaces.py
python3 workflow-source/tools/claim_workspace.py --branch <b> --axis "<축>" --task-title "<제목>" --apply
python3 workflow-source/tools/seed_workspace_memory.py --branch <b> --axis "<축>" --task-title "<제목>" --apply  # 선점 시 자동 호출
python3 workflow-source/scripts/generate_workflow_state.py \
  --project-profile-path docs/PROJECT_PROFILE.md --output-path ai-workflow/memory/active/<b>/state.json
```

대시보드(Panel 5) 가 자동으로 모든 worktree 의 state.json 을 합쳐 본다. 다른 worktree
를 명시적으로 합류시켜야 하면 `WORKFLOW_EXTRA_ROOTS=/path1:/path2` env 1개면 충분.

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

**별건 3 (2026-08-09 실측) — 사전 존재 red 7건, 뿌리는 하나**:

전체 검사(`run_all_checks.py`, 격리 venv)에서 7건이 red 다. **전부 본 세션 이전부터**
red 였고 (`git stash` 로 확인), 뿌리는 두 가지다:

| 검사 | 증상 |
| --- | --- |
| `check_readme_cross_v0_15_12` | README 헤더 `v1.0.0-beta` ≠ pyproject `v1.1.1-beta` |
| `check_installation_usage_v0_15_14` | INSTALLATION status version 동일 문제 |
| `check_release_md_v0_15_18` | RELEASE.md 에 `1.1.1` stamp 부재 |
| `check_sample_version_cross_v0_15_11` | sample `tool_version` 24건 mismatch |
| `check_code_index_v0_15_17` | CODE_INDEX smoke count claim 234 ≠ actual |
| `check_smoke_trend_cross_v0_15_5` | 같은 count 불일치 |
| `check_mcp_apply_mode_criterion` | `mcp` SDK 부재 (dev venv 미설치, 환경 문제) |

1. **v1.1.0 / v1.1.1 릴리스 때 문서 버전 stamp 를 안 올렸다** (5건).
2. **smoke 파일 수 claim(234)이 실제와 벌어졌다** (2건). 본 세션이 4개를 더해
   256 이 됐으니 **내가 벌린 것도 있다** — 다만 234 claim 은 이전부터 틀려 있었다.

릴리스 판단(v1.1.2 발행 여부)과 엮여 있어 손대지 않았다. 발행한다면 그 사이클에서
같이 정리하는 게 맞다.

**별건 2 (2026-08-09 신규 발견) — rotate 도구가 이 저장소에서 한 번도 동작한 적이 없다**:

`handoff_bloat` 경고를 해소하라고 있는 `rotate_workflow_logs` 가 `status: error` 로
아무 일도 하지 않는다. 원인이 둘인데, 두 번째가 더 위험하다.

1. **섹션 이름 불일치** — `rotation.py` 는 `## 5. 최근 완료 작업` / `## 6. 잔여 작업` 을
   찾는데 실제 문서는 `## 4. 최근 완료 작업` / `## 5. 다음 세션 시작 포인트` 다.
2. **정렬 방향 불일치** — `workflow_writes.py:319` 는 *뒤가 최신* 을 가정해 앞에서
   버린다. 그런데 실제 §4 는 **최신이 위** 로 쌓여 왔다 (사람/에이전트가 앞에 붙였다).
   **1번만 고치면 도구가 "동작하면서 최신 4건을 지운다".**

`workflow_writes.py:317` 주석의 *"`handoff_bloat` 가 그걸 잡으면 사람이 손으로 지웠다"*
가 이 상태의 흔적이다. 본 세션에서도 손으로 지웠다 (14 → 10).

**먼저 규약을 정해야 한다** — (a) 문서를 오래된 순으로 뒤집어 도구에 맞출지,
(b) 도구를 최신 우선으로 바꿀지. 자동 경로(`workflow_writes`)와 수동 관행이 반대로
쌓고 있으므로 한쪽을 고르지 않으면 어느 수정도 다른 쪽을 깨뜨린다.

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
