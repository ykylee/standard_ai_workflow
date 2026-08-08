# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-09 (memory 정합성 정리 + session close)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **v1.1.1-beta** + `origin/main` = `678806f` (2026-08-08, **§0.8 4건 close + dual mode + federation *읽기* + CLI 化 A안 묶음 release**). 2 release 발행 — v1.1.0-beta (564ce36) → v1.1.1-beta (6b92a60). tag `v1.1.1-beta` push + GitHub Release 발행.
- 현재 주 작업 축: **memory 문서 정합성 정리** (TASK-2026-08-09-main-001, 본 세션). 직전 세션이 TASK-014~020 을 끝내고 release 까지 냈는데 memory 문서 여러 곳이 그 이전 상태로 남아 있었다 → backlog status/링크 + task 본문 상태 7건 + state.json `done_items` + handoff stale 4곳 정리. `check_self_application` 7/8 → **8/8 PASS**.
- 직전 주 작업 축: **v1.1.1-beta release** (CLI 化 A안 — `[project.scripts]` 29 entry point). venv e2e 검증 완료 (`pip install -e .` → 29 binary + `--help` 정상). §0.8 의 *열린 채로* 남아있던 4건 모두 close + CLI 化 A안 close.
- 직전 축: **TASK-020** (29 entry points + venv e2e + 4 case smoke ALL PASS) + **TASK-019** (3-layer defense — pre-push hook) + **TASK-018** (scope drift detection) + **TASK-017** (operational CLI dual mode) + **TASK-016** (federation HTTP pull) + **TASK-015** (federation 정공법) + **TASK-014** (in-flight confidence 4-level) + **TASK-013** (mavis attach e2e) + **TASK-012** (갈래2 trust). 9 TASK + §2.68 cycle + CLI 化 A안 = 2 release.
- 다음 후보 축: TASK-021+ (B안 dispatcher `wk` 단일 binary + tab completion) / HTTP server 도구 / v2 title semantic drift (LLM-based) / Phase 13 진입.
- 발견한 cross-project 패턴 (agent memory 추가):
  - **Federation pattern** (4 후보 검토: central ❌ / git ❌ / S3 ❌ / federation ✅)
  - **MCP/CLI dual mode** (operational tool 의 4종 wrapper)
  - **3-layer defense** (규약 + client hook + server protection)
  - **Scope drift detection** (3-way enum: planned_done / planned_undone / unplanned_done)
  - **time.mktime → calendar.timegm** (UTC timestamp KST 환경 함정)
  - **[project.scripts] entry points** (CLI 化 A안, venv e2e 검증)
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
- TASK-2026-08-09-main-001 memory 문서 정합성 정리 — backlog 인덱스 TASK-020 `planned` → `done` + 깨진 `path:` href 3건(018·019·020, `-08-main` 누락) / task 본문 `- 상태: planned` 7건(014~020) → `done` / state.json `backlog.done_items` 에 014~020 + `recent_done_items` 에 018 / handoff stale 4곳. `check_self_application` 7/8 → **8/8 PASS**. state.json 전면 재생성은 **안 했다** — 재생성본이 `done_items` 를 10건으로 자르고 `current_focus` 를 끝난 TASK-014 로 잡아 정보가 깎인다.
- TASK-2026-08-08-main-020 `[project.scripts]` entry points (CLI 化 A안) — 29 entry point (`workflow-{name}`) + `tools` packages 등록. venv e2e (`pip install -e .` → 29 binary + `--help`) + 4 case smoke ALL PASS. **v1.1.1-beta release** (`6b92a60`). dispatcher `wk` (B안) = 후속.
- TASK-2026-08-08-main-019 `--force` server-side 이중화 (§0.8 #4) — **3-layer defense**: 도구 미제공(기존) + **pre-push hook**(본 task) + server branch protection(가이드). `tools/hooks/pre-push-no-force.sh` (POSIX sh, force 5변형 거부) + `tools/install_pre_push_hook.py` (install/uninstall/status, dry-run default, backup 자동) + smoke 7 case ALL PASS. **v1.1.0-beta release** (`564ce36`).
- TASK-2026-08-08-main-018 scope drift detection (§0.8 #3) — 3-way enum (`planned_done`/`planned_undone`/`unplanned_done`) + drift_score + score_band. `drift_detection.detect_scope_drift()` pure function + `tools/detect_scope_drift.py` CLI (advisory default, `--exit-on-drift` 시 non-zero). smoke 7 case ALL PASS. title semantic drift = v2 (LLM-based).
- TASK-2026-08-08-main-017 operational MCP tool 4종 CLI wrapper — **dual mode** (MCP server 무변경 + CLI 4개 추가). 같은 `*_payload` 호출 → CLI ↔ MCP *byte-equal*. rotate_workflow_logs / apply_robust_patch / create_environment_record_stub / check_quickstart_stale_links. smoke 4 case ALL PASS. 나머지 9 tool 은 MCP 유지 (LLM-interpretation 필수).
- TASK-2026-08-08-main-016 HTTP pull + dashboard federation 통합 — TASK-015 의 *읽기* 마무리. stdlib only (`urllib`) + remote cache TTL 1h + timeout 2s. **함정**: `time.mktime` 는 local TZ 해석 → KST 에서 9h 차이로 TTL 초과 → `calendar.timegm` 으로 정정. `tools/host_pull_registry.py` CLI. smoke 8 case ALL PASS.
- TASK-2026-08-08-main-015 registry federation 정공법 (§0.8 #1) — 4 후보 중 **federation ✅** (central/git/S3 ❌). `KnownHost` + known_hosts CRUD (atomic 0o600) + `merge_entries(sources)` (dedup key=`path`, last_seen_at 최신 우선) + `RegistryEntry.source_host_id` (additive, 하위호환). smoke 8 case ALL PASS. doc §7.4 신설.
- TASK-2026-08-08-main-014 in-flight 워크스페이스 신뢰도 표시 (§0.8 #2) — `workspace_registry.confidence()` 4-level enum (`fresh`/`recent`/`stale`/`orphan`) + Panel 5 inline badge + CSS 4종. 3-way freshness signal = `path.is_dir()` + `last_seen_at` + `worktree_branch`. smoke 8 case ALL PASS.
- TASK-2026-08-08-main-013 mavis attach end-to-end 회귀 smoke 자동화 — `check_mavis_attach_e2e.py` (stdlib only, 4-step ALL PASS — initialize / tools/list 13종 set equality / tools/call × 2). §2.68 cycle 의 *자동 검증* 닫음.
- TASK-2026-08-08-main-012 §2.68 mavis attach 수동 검증 — **갈래2 trust 채택**: 데스크탑 새 세션 rotate 대신 e2e smoke (실제 attach 경로와 100% 동치 subprocess) 의 ALL PASS 로 갈음. mavis 의 *silent fail* 가능성 (§1.2.1) 을 subprocess 직접 검증으로 회피. collateral: TASK-009/010/011 L14 in_progress → done.

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
- **다음 후보 축** (우선순위 미정, 다음 세션에서 결정):
  - TASK-021+ CLI 化 B안 — dispatcher `wk` 단일 binary + tab completion.
  - registry HTTP **server** 도구 — TASK-016 은 *읽기(pull)* 만 닫았고 서빙 측은 미구현.
  - server-side branch protection 자동 check (`gh api`) — TASK-019 3rd layer 잔여.
  - title semantic drift v2 (LLM-based) — TASK-018 후속.

## 6. 남은 리스크 / 확인하지 못한 것

**사전 존재 red — 4건 모두 닫힘**:

| 검사 | 상태 |
| --- | --- |
| `check_appendonly_memory_layout` | ✅ **닫음** — 2026-08-06 task 3건에 frontmatter 추가 |
| `check_self_application` (`handoff_bloat`) | ✅ **닫음** — 본 문서 1096줄 → 106줄, done items 10/10. **8/8 passed** |
| `check_standard_single_source` | ✅ **닫음** (TASK-2026-08-08-main-005) — `ai-workflow/core/mcp_installation_by_harness.md` 사본을 정본(`workflow-source/core/...`)으로 cp 동기화. 7/7 PASS. 정본 = 2026-08-07 00:12 갱신본 (mavis 데스크탑 §1.2.1 + §6.5.2). |
| `check_bootstrap_interactive_picker` | ✅ **닫음** (TASK-2026-08-08-main-005) — `bootstrap_lib.__main__` / `bootstrap_lib.harnesses` 가 `workflow-source/scripts/` 안에 있어 in-process tests 가 `sys.path` 에 `SCRIPTS_DIR` 를 올리도록 1줄 보강. 10/10 PASS. |

**별건**: dashboard `drift_prevention.guard_status: fail` — `maturity_last_updated` stale.
갱신 힌트는 dashboard 출력의 `maturity_refresh_hint`.

**구현했지만 검증 못 한 것**:

- 도구 3종은 **로컬 bare remote** 로만 검증했다. GitHub 등 실제 원격의 protected branch /
  push 권한 정책 아래에서는 다르게 동작할 수 있다.
- `--force` 는 **2-layer 까지 적용** (도구 미제공 + pre-push hook, TASK-019). hook 은 로컬
  설치형이라 **미설치 호스트는 여전히 막지 못한다.** 3rd layer (서버측 branch protection)
  는 가이드만 있고 **자동 check 미적용**.
- stale 임계 24h 는 heuristic 이다. 실제 운영 데이터로 조정한 적 없다.

**이전 세션들의 교훈**은 각 세션 기록에 있다:
[2026-08-08](./sessions/multi_workspace_orchestration_2026-08-08.md) ·
[2026-08-05](./sessions/self_application_and_mcp_2026-08-05.md) ·
[2026-08-07 MCP](./sessions/mcp_load_verification_2026-08-07.md) ·
[2026-07-27](./sessions/selfref_cleanup_and_ci_measurement_2026-07-27.md)
