# Beta v0.14.0 — Append-only Memory Layout (1st deprecation cycle) (2026-07-16)

> **Phase 14 (Append-only Memory Layout v1.0) 의 정식 close-out release**.
> 본 release 는 4 sub-milestone (Phase 14 AC1~AC4) 으로 분할 출시된 Phase 14 의 **1st release**.
> `work_backlog.md` 단일 파일 (58KB, 93 inline release entries) → append-only layout 의 본격 도입.

## 1. Phase 14 정의

**north-star metric**: `multi_agent_concurrent_write_conflict_count` — sub-agent 2개+ 동시
fan-out 시 mutable 공유 파일의 3-way merge conflict / overwrite race 누적 갯수. **0** 으로 수렴.

**Phase 14 이름**: "Append-only Memory Layout v1.0 — Single-mutable-file SSOT"

핵심: *memory write 가 mutable 공유 파일 (state.json 단 1개) 외에는 append-only 또는 자기 소유 파일에 한정* 되어 multi-agent 동시 작업 시 conflict 가 발생하지 않도록 함.

### 1.1 배경

기존 `ai-workflow/memory/active/` 모델은 단일 버킷에 **3개 mutable 공유 파일**:

| 파일 | 크기 | 충돌 강도 |
|---|---|---|
| `state.json` | 24KB (88 line, `recent_done_items` 1줄 직렬화) | 🔴 HIGH |
| `work_backlog.md` | **58KB** (330 line 누적 release history index) | 🔴 HIGH |
| `session_handoff.md` | 부재 (이미 제거됐지만 code reference 잔존) | 🟢 N/A |

**문제**: sub-agent 2개+ 동시 fan-out 시 `state.json.recent_done_items` append 경합, `work_backlog.md` 의 3-way merge 어려움 → multi-agent 운영의 structural bottleneck.

### 1.2 정공법

**`MEMORY_GOVERNANCE.md` §2** 가 **이미 per-task + daily-index 정공법**을 템플릿으로 명시:
- `backlog/tasks/TASK-XXX.md` (per-task SSOT)
- `backlog/YYYY-MM-DD.md` (daily index, link-only)
- "On merge conflicts, rebuild the daily index from task links"

실제 구현은 단일 `work_backlog.md` 로 collapsed — **spec drift 자체**였습니다. 본 release 는 governance 정공법으로 implementation 을 정렬.

## 2. Acceptance Criteria 종합 (4 AC 모두 ✅)

| AC | Status | 정의 | Commit |
|---|---|---|---|
| **AC1 (layout scaffold)** | ✅ | 신규 directory + migration tool + 93 entries 분할 | `8c53c4a` |
| **AC2 (state rebuild)** | ✅ | `state/builder.py` + `cache.py` 가 신규 layout 입력 받을 수 있도록 확장 (backward compatible) | `5a6b069` |
| **AC3 (path consistency)** | ✅ | 88 file 의 path reference 일관성 (sed 일괄 + governance 정합) | `104d028` |
| **AC4 (smoke)** | ✅ | 신규 `check_appendonly_memory_layout.py` 6/6 PASS (layout / legacy / source_of_truth / links / frontmatter / cross-ref) | `5549d7c` |

## 3. 신규 layout 명세

```
ai-workflow/memory/active/
├── state.json                     ← read-only snapshot (state/builder.py 가 rebuild)
├── state.json.template            ← unchanged (template)
├── PROJECT_PROFILE.md             ← manually maintained
├── PURPOSE.md                     ← manually maintained
├── project_status_assessment.md   ← manually maintained
├── repository_assessment.md       ← manually maintained
├── session_analysis_<date>.md     ← per-session (append 가능)
│
├── backlog/                       ← 🆕 per-day + per-task append-only
│   ├── YYYY-MM-DD.md              ← per-day index (append-only, links to tasks/)
│   └── tasks/
│       ├── TASK-YYYY-MM-DD-001.md ← 1 file = 1 task (per-task SSOT)
│       └── ...
│
├── sessions/                      ← 🆕 per-session (was session_handoff.md)
│   ├── session_analysis_2026-07-09.md ← per-session file
│   └── audit_follow_up_2026-07-09.md
│
├── memory_index/                  ← unchanged (이미 append-only 정공법)
│   ├── entries/MEM-YYYY-MM-DD-NNN.json
│   └── telemetry/events.jsonl
│
└── log.md                         ← append-only
```

**충돌 표면 분석** (multi-agent 동시 작업 시):

| 파일 | 충돌? | 비고 |
|---|---|---|
| `state.json` | ✅ `--apply` flag 로 1 agent 만 rebuild | atomic_write 보장 |
| `backlog/YYYY-MM-DD.md` | 🟡 3-way merge, 양쪽 항목 concat | 같은 날 다른 task 추가 시 |
| `backlog/tasks/TASK-XXX.md` | ❌ **물리 격리** | 다른 agent 가 다른 task file |
| `sessions/<date>-<topic>.md` | ❌ **물리 격리** | 다른 agent 가 다른 session file |
| `memory_index/entries/*.json` | ❌ 물리 격리 (기존) | v0.13.1 부터 |
| `memory_index/telemetry/events.jsonl` | ❌ append-only (기존) | v0.13.1 부터 |
| `log.md` | ❌ append-only (기존) | 2026-06-12 부터 |

→ **신규 layout 에서는 mutable 공유 파일이 `state.json` 단 1개**. 나머지는 모두 append-only 또는 자기 소유.

## 4. 핵심 변경 요약

### 4.1 Migration tool (AC1)
- `workflow-source/tools/migrate_active_to_appendonly.py` 신규 (idempotent, dry-run default, anchor 보존, path stem date fallback)
- 93 entries 분할: 19 daily index + 91 task file + 2 session file
- `work_backlog.md` → `work_backlog.md.bak` rename (legacy fallback 보존)

### 4.2 state.json rebuild 확장 (AC2)
- `workflow_kit/common/paths.py` helper 3개 (`workflow_backlog_dir` / `workflow_tasks_dir` / `workflow_sessions_dir`)
- `workflow_kit/common/state/builder.py` signature 확장 (`daily_backlog_dir` / `tasks_dir` / `sessions_dir` kwarg, default None, **legacy 1st cycle fallback**)
- `_aggregate_from_appendonly_layout` helper: tasks_dir 의 `TASK-*.md` frontmatter `status` aggregate + `recent_done_items` prose 1줄 (dashboard / purpose_graph 정합)
- `state/cache.py` refresh_wiritual_state_cache + build_state_cache_refresh_hint 자동 resolve
- `scripts/generate_workflow_state.py` CLI flag 3개 (`--daily-backlog-dir` / `--tasks-dir` / `--sessions-dir`)
- `state.json.source_of_truth` 5 → 9 keys (legacy 2 + 신규 3 + 정합 + repo_assess)

### 4.3 Path consistency (AC3)
- 88 file path string sed 일괄 (`work_backlog.md` → `backlog/`, `session_handoff.md` → `sessions/`)
- R9 immutable archive/release 디렉토리 revert 후 제외
- `MEMORY_GOVERNANCE.md` §2 4 템플릿 (Daily Index / Per-Task / Per-Session / State.json) + §3 deprecation timeline
- `ai-workflow/memory/active/state.json.template` 5 → 9 keys
- `ai-workflow/WORKFLOW_INDEX.md` v0.14.0 layout 운영 가이드 link + append-only 원칙
- `ai-workflow/README.md` §5 onboarding 절차 신규 layout 정합

### 4.4 Smoke (AC4)
- `tests/check_appendonly_memory_layout.py` 신규 (6 cases, 225 line):
  1. layout existence (backlog/, backlog/tasks/, sessions/)
  2. legacy absent (work_backlog.md 부재)
  3. state.json source_of_truth (3 dir 모두 dir path)
  4. daily index links (TASK-* 모두 resolve)
  5. task frontmatter (6 keys 정합)
  6. sessions cross-ref (1+ file 존재)
- `tests/check_memory_freeze_lint.py` REQUIRED_DIRS 추가 (R9 archive 는 R9 immutable)

## 5. Deprecation timeline (ADR-003)

| 버전 | 상태 | 비고 |
|---|---|---|
| **v0.14.0 (현재)** | 1st cycle — 신규 layout 추가, 구 layout **fallback 유지** | `work_backlog.md.bak` 이 있으면 warning, 없으면 정상 |
| v0.14.1 | 1st cycle 종결 | warning 강화 |
| v0.14.5 | 2nd cycle 시작 예정 | `work_backlog.md` 는 `--legacy-memory` opt-out flag 가 있을 때만 read |
| **v0.15.0** | 2nd cycle 종결 | `work_backlog.md` / `work_backlog.md.bak` 모두 drop. 신규 layout 만 사용 |

## 6. 검증 종합 (모두 PASS)

| 검증 | 결과 |
|---|---|
| 신규 `check_appendonly_memory_layout.py` | **6/6 PASS** |
| `check_drift_prevention_v0_11_23.py` | 6/6 PASS |
| `check_memory_lint.py` (contradiction/stale/orphan/missing) | 4/4 PASS |
| `check_memory_freeze_lint.py` (R8 archive legacy layout 보존 + active/ 신규 dir 검증) | PASS |
| `check_memory_index.py` / `check_bootstrap.py` / `check_doc_sync.py` / `check_code_index_update.py` / `check_validation_plan.py` / `check_project_status_assessment.py` / `check_export_harness_package.py` / `check_harness_overlay_consistency.py` | 모두 PASS |
| mypy strict (Phase 3 신규 변경분) | **0 NEW error** |
| 5 skill scripts `py_compile` | OK |
| backward compat (legacy caller, session_handoff_path / work_backlog_index_path default = None) | OK |

## 7. 산출물 + 4 commit

| Commit | Phase | 내용 |
|---|---|---|
| `8c53c4a` | AC1 | 신규 layout scaffold + migration script + 93 entries 분할 |
| `5a6b069` | AC2 | state/builder.py + cache.py 확장 (backward compatible) |
| `104d028` | AC3 | 88 file path string 갱신 + governance layout 명세 |
| `5549d7c` | AC4 | 신규 smoke `check_appendonly_memory_layout.py` 6/6 |

**누적 commit**: 4 commits (+472 file, +3104 / -432)

## 8. Out of scope (다음 release 에서)

- **v0.14.5 (2nd cycle 시작)**: `work_backlog.md` legacy read 는 `--legacy-memory` opt-out flag 가 있을 때만. 본 release 의 fallback 자동 read 단계 종료.
- **v0.15.0 (2nd cycle 종결)**: `work_backlog.md.bak` drop. 신규 layout 만 SSOT.
- **Phase 15 (다음)**: dashboard regen script 가 신규 layout 의 sessions/ + memory_index entries + teleMetry 를 통합 panel 로 emit
- **`audit_follow_up_*.md` 의 dead link 정리**: `work_backlog.md` (legacy) 의 `[[active/audit_follow_up_...]]` anchor 는 본 release 의 마이그레이션이 inline 본문을 보존하면서 link 그대로 유지. 추후 별도 정리.

## 9. 위험 + mitigation (회고)

| 위험 | 가능성 | 영향 | mitigation | 결과 |
|---|---|---|---|---|
| 마이그레이션 시 anchor 손실 | 🟠 MED | 외부 wiki link 깨짐 | migration script 가 anchor 그대로 보존 (`### [[path]] {#anchor}` 형식) | ✅ 보존 |
| `state.json` rebuild 결과가 legacy 와 diff | 🟠 MED | dashboard regen 깨짐 | `_aggregate_from_appendonly_layout` 의 prose summary 추출 (dashboard Panel 5 / purpose_graph 정합) | ✅ 정합 |
| skill spec 동기화 누락 | 🔴 HIGH | runtime path error | 1차 sed 일괄 (88 file) + 2차 손수정 (state.json.template / WORKFLOW_INDEX / governance) | ✅ 회귀 0 |
| harness 10종 README 일괄 누락 | 🟠 MED | 외부 user onboarding 깨짐 | sed 일괄 + `check_harness_overlay_consistency.py` 회귀 검증 | ✅ PASS |
| 신규 layout smoke 가 session entry 누락 검출 | 🟠 MED | 4) case FAIL | smoke 가 daily index 의 `[[source_path]]` 라인도 함께 parsing, session vs task 분기 | ✅ 해결 |

## 10. ADR / refs

- **ADR-001** (source-state-knowledge 3-layer separation) — `ai-workflow/memory/` 가 runtime State layer. 본 release 는 State layer 의 layout 만 변경 (Knowledge layer 무관)
- **ADR-003** (deprecation cycle pattern) — 1st/2nd cycle 의 정공법으로 본 release 진행
- **MEMORY_GOVERNANCE.md §2** — 본 layout 의 spec 출처 (Standard Templates)
- **project plan**: `~/.claude/plans/cheeky-zooming-axolotl.md`

## 11. 다음 step

`Phase 14 가 close-out 됨`. 다음 phase 후보:
- **v0.14.1 / v0.14.2 / ... / v0.14.5** — 1st cycle 종결 후 2nd cycle 진입 준비
- **v0.15.0** — 2nd cycle 종결, legacy drop
- **Phase 15** — Phase 14 의 smooth 운영을 위한 high-value P1 (예: 5 panel dashboard 의 신규 layout 정합, archive 처리 자동화)
- **별도 root scaffold** — root 의 `pyproject.toml` (v0.1.0 placeholder) + `main.py` 의 실제 구현은 별도 작업

— generated 2026-07-16
