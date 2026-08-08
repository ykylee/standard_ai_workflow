# Beta v1.1.0 (2026-08-08)

> **상태: 릴리스.** `tool_version = v1.1.0-beta`, tag `v1.1.0-beta`, GitHub Release 발행.
> PyPI 배포는 정책상 미실행 (릴리스 채널 = GitHub Releases).
>
> **사이클 요약**: §0.8 의 4건 모두 close (registry federation / in-flight confidence /
> scope drift detection / --force server-side 이중화). §2.68 cycle (mavis attach) +
> §7.4 federation *읽기* 까지 한 cycle 에 묶음.

## 0. 릴리스 판정

본 사이클의 핵심 deliverable 은 **§0.8 의 *열려 있는 것* 4건을 모두 닫은 것** 이다.
이전 release (Beta-v1.0.0) 의 §0.7 / §0.8 *열린 채로* 진입했던 항목이 본 사이클에서
전부 close. PROJECT_PROFILE.md 의 "Phase 1–12 done, Phase 13 planned" 의 *Phase 13 진입
대기* 상태가 *§0.8 잔여 0건* 으로 정합.

| §0.8 항목 | TASK | close 시점 | 핵심 deliverable |
|---|---|---|---|
| #1 registry federation | TASK-015/016 | v0.15.23+ / v0.15.24+ | federation 정공법 + HTTP pull + dashboard 통합 |
| #2 in-flight 신뢰도 | TASK-014 | v0.15.22+ | 4-level enum + Panel 5 inline badge |
| #3 scope drift 검출 | TASK-018 | v0.15.26+ | 3-way enum + drift_score + score_band |
| #4 `--force` 이중화 | TASK-019 | v0.15.27+ | 3-layer defense (규약 + client hook + server branch protection) |

추가 deliverable:
- **TASK-012 갈래2 trust 채택** (§2.68 mavis attach 자동 검증 — e2e smoke 가 attach
  경로와 100% 동치 subprocess 라는 근거)
- **TASK-017 operational MCP tool CLI wrapper (dual mode)** — 4 종 operational
  tool 의 CLI + MCP 동시 지원

## 1. 릴리스 요약

- **§0.8 4건 닫음** — *열려 있는 것* 표가 비었다 (PROJECT_PROFILE.md 정합 회복).
- **federation 정공법** — central store / git-tracking / S3 / **federation** 4 후보
  검토. federation 채택 (각 호스트의 host-scoped file 보존 + `known_hosts.json` +
  HTTP pull + `merge_entries` API). `merge_with_remotes` 가 *read-only* in-memory
  합치기. 8+8 case smoke ALL PASS.
- **scope drift detection** — pre handoff 의 *다음에 할 일* + post handoff 의 *최근
  완료 작업* + git log 의 TASK-ID 3-way 비교. `drift_score` + `score_band` (advisory
  only, `--exit-on-drift` 명시 시 non-zero). 7+1 case smoke ALL PASS.
- **`--force` 3-layer defense** — 1st (claim_workspace.py 가 --force option 미제공) +
  2nd (pre-push hook 이 사람/스크립트의 직접 차단) + 3rd (server branch protection
  가이드). 7 case smoke ALL PASS.
- **operational CLI dual mode** — 4 tool (`rotate_workflow_logs` /
  `apply_robust_patch` / `create_environment_record_stub` / `check_quickstart_stale_links`)
  의 CLI wrapper 추가. CLI ↔ MCP *byte-equal* output. 4 case smoke ALL PASS.
- **in-flight 4-level confidence** — `fresh` / `recent` / `stale` / `orphan` 4-level
  enum. 3-way freshness signal = `path.is_dir()` + `last_seen_at` + `worktree_branch`.
  Panel 5 inline badge + CSS 4종. 8 case smoke ALL PASS.
- breaking change: ❌. (모두 additive — 기존 tool 들 그대로 동작.)

## 2. deliverable

### 2.1 §0.8 close 4건 (총 7 TASK)

| TASK | v0.15+ | kind | 핵심 |
|---|---|---|---|
| TASK-014 | v0.15.22+ | registry | in-flight confidence 4-level enum + Panel 5 badge |
| TASK-015 | v0.15.23+ | registry | known_hosts + merge_entries API + RegistryEntry.source_host_id |
| TASK-016 | v0.15.24+ | registry | HTTP pull + remote cache (TTL 1h) + dashboard 통합 |
| TASK-017 | v0.15.25+ | cli | operational MCP tool 4종 CLI wrapper (dual mode) |
| TASK-018 | v0.15.26+ | drift | scope drift detection (3-way enum + drift_score) |
| TASK-019 | v0.15.27+ | safety | pre-push hook (--force 3-layer defense) |

### 2.2 §2.68 cycle (TASK-001~013)

mavis 데스크탑 attach 회귀 — 글로벌 mcp.json 의 `standardAiWorkflowReadOnly` 가
13종 native tool 노출 미스. §6.5.2 정합으로 restore. **TASK-012 갈래2 trust** 채택
(수동 검증 → e2e smoke 가 실제 attach 경로와 100% 동치 subprocess 라는 근거).

### 2.3 도구 (신규 7 + 회귀 6)

**신규**:
- `tools/host_pull_registry.py` — federation pull CLI
- `tools/detect_scope_drift.py` — scope drift CLI
- `tools/rotate_workflow_logs.py` / `tools/apply_robust_patch.py` /
  `tools/create_environment_record_stub.py` / `tools/check_quickstart_stale_links.py`
  — dual mode CLI
- `tools/install_pre_push_hook.py` + `tools/hooks/pre-push-no-force.sh` — pre-push hook

**회귀 / 유지** (TASK-001~002):
- `tools/workspace_registry.py` (host-scoped registry CLI)
- `tools/seed_workspace_memory.py` / `tools/survey_remote_workspaces.py` /
  `tools/claim_workspace.py` (multi-workspace 도구 3종)

### 2.4 smoke 회귀 (8+8+7+7+4+4+8 = 46 case ALL PASS)

| smoke | case | v0.15+ |
|---|---|---|
| `check_host_pull.py` | 8 | v0.15.24+ |
| `check_host_federation.py` | 8 | v0.15.23+ |
| `check_registry_confidence.py` | 8 | v0.15.22+ |
| `check_scope_drift.py` | 7+1 | v0.15.26+ |
| `check_pre_push_hook.py` | 7 | v0.15.27+ |
| `check_cli_wrappers.py` | 4 | v0.15.25+ |
| `check_mavis_attach_e2e.py` | 4 (e2e) | §2.68 |

## 3. 1차 출처 (cross-ref)

- `core/multi_workspace_orchestration.md` — **§0.7 적용 상태 표** (모두 ✅) + **§0.8**
  4건 ~~취소선 + 닫힘~~ + **§7.4** federation *읽기* + **§7.5** scope drift +
  **§5D.4 (b)** 3-layer defense
- `core/global_workflow_standard.md §10` — 다중 작업·협업 규칙 (그대로)
- `MEMORY_GOVERNANCE.md` — memory governance
- `PROJECT_PROFILE.md` — Phase 13 진입 가능 상태 (renewed)

## 4. 후속

- **v1.1.0 → v1.2.0-beta** (다음 release 후보):
  - §0.7 의 모든 ✅ 항목이 *release-ready* 임을 smoke 46 case 가 보장.
  - `release_pipeline.py` 의 자체 도구 버그 (vv1.1.0-beta-beta 처럼 suffix 중복) 는
    release 운영자 판단으로 후속.
  - HTTP server 도구 (각 호스트가 자기 registry 를 serving) = TASK-021+ (운영자 결정).
  - v2: title semantic drift (LLM-based) = TASK-022+ 후속.
- **Phase 13 진입**: §0.8 잔여 0건 + 본 release 1.1.0 으로 *진입 가능* 상태. 운영자 결정.

## 5. compatibility

- breaking change: ❌
- 기존 도구 (`workspace_registry.py` / `seed_workspace_memory.py` / ...) 그대로 동작
- MCP server 변경 ❌ — 9 tool LLM-interpretation 은 MCP 유지, 4 tool operational 은
  dual mode (CLI + MCP 둘 다). 기존 MCP consumer 영향 0.
- 표준 §10 + §1 협업 규칙 — unchanged.
