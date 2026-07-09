---
release: v0.13.2
closed_phases: []
promoted_skills: []
added_harnesses: []
deprecated_symbols: []
phase_13_sub_milestones:
  - { name: v0.13.2, scope: "self-recovering drift prevention", status: shipped }
---

# Beta v0.13.2 — self-recovering drift prevention (Phase 13 AC3 close) (2026-07-09)

> Phase 13 (Operational Intelligence v1.0) 의 sub-milestone 3rd release.
> drift prevention smoke 의 6 case 가 검출한 drift 를 **자동 fix** +
> **manual_required 분리** + **release note self-recovery log 자동 emit**
> 의 1-cycle orchestrator. AC3 close-out.

## 핵심 (self-recover orchestrator)

### 1. Self-recover orchestrator (`tools/release_pipeline.py`)

- **detect** (`_run_drift_prevention_smoke`) — `check_drift_prevention_v0_11_23.py`
  를 subprocess 로 inline 실행. stdout 에서 `PASS:` / `FAIL:` line regex
  parse + summary line. `dashboard_data.py:run_drift_prevention_guard_inline`
  과 동일 정공법.
- **classify** (`_classify_drift_failures`) — `_SELF_RECOVER_CASE_MAP`
  dict 기반 auto_fixable / manual_required 2-bucket 분리. 미등록 case 는
  manual_required (fail-safe).
- **fix** — auto_fixable case 각각 매핑된 fix 함수 호출:
  - `test_case_1_pyproject_loud_fallback_sync` → `_fix_loud_fallback`
    (regex 교체 + atomic_write_text)
  - `test_case_4_readme_header_version_sync` → `_fix_readme_header_version`
  - `test_case_5_harness_supported_ssot_alignment` → `_fix_maturity_matrix_drift`
  - `test_case_6_maturity_last_updated_freshness` → `_fix_maturity_matrix_drift`
  - `test_case_2_maturity_matrix_phase_status` / `test_case_3_skill_stage_matches_promotion_set`
    → **manual_required** (human judgment 필요)
- **re-check** — 동일 smoke 재실행 → 6/6 PASS 검증.
- **emit** (`_emit_recovery_summary`) — `{mode, recovered, manual_required,
  re_check, summary}` dict. `cmd_release` 가 release note body 에 자동
  append 의 source.

### 2. cmd_release 자동 wiring

- validate step 후 `cmd_self_recover(_attr_ns(apply=True))` 자동 호출.
- §3.0 doc-headers-update / sync-maturity-matrix step 의 *선행* 으로
  self-recover 가 자동 fix 후 doc-header 가 그 위에 다시 sync (defense
  in depth).
- **manual_required > 0** 이면 `results["self_recover"]` 포함 후 **early
  return** (drift fix 우선 — 사람의 명시 intervention 필요).
- **`--skip-self-recover`** escape hatch (manual override).
- **`_attr_ns.normalize`** 에 `skip_self_recover` 추가.

### 3. Self-recovery log release note emit

- `_format_self_recovery_log(sr_result)` — dict → markdown 문자열. drift
  가 없거나 (`recovered=[]` + `manual_required=[]`) 면 빈 문자열.
- `_emit_self_recovery_log(args, recovery_log)` — release note 끝에
  `## Self-recovery log` 섹션 자동 append. **idempotent** (이미 섹션
  존재 시 skip).
- release note 가 없거나 (backfill 시나리오) recovery_log empty 면 no-op.
- release pipeline step 6.5 (dashboard emit 다음) 에서 호출.

### 4. 신규 dispatcher subcommand 37: `cmd_self_recover`

- ARGS: `--apply` (default False) / `--dry-run` (default True) / `--json`.
- detect → classify → fix → re-check → emit 의 1-cycle orchestrator.
- §6.3 MUST-NOT-delegate 정합.

### 5. in-scope fix 동반 (3 건)

- **(a)** `tools/release_pipeline.py` 의 `sys.path.insert(0, ...)` 추가
  — standalone 실행 시 `workflow-source` 가 import 안 되던 v0.11.22~v0.13.1
  latent bug. atomic_write_text / atomic_write_json 가 실제로 import
  가능해짐.
- **(b)** README_PATH 정정 — `REPO_ROOT / "README.md"` (`workflow-source/README.md`,
  stub) → `REPO_ROOT.parent / "README.md"` (실제 root README 47KB).
  case_4 README header fix 가 정상 동작.
- **(c)** `workflow_kit_cli.py:cmd_memory_index_query` 의
  `MemoryIndexTelemetryEvent` import schemas layer 로 정정 (explicit
  export, mypy strict error 1개 해소).

## 신규 파일 / 변경

| 변경 | 파일 | 비고 |
|---|---|---|
| 신규 | `workflow-source/tests/check_self_recovering_v0_13_2.py` | 8 case smoke (clean state / loud fallback fix / README header fix / dry-run no modify / classify / re_check pass / format / emit) |
| 신규 | `ai-workflow/memory/release/v0.13.2/backlog/2026-07-09.md` | release note (cycle archive) |
| extend | `tools/release_pipeline.py` | 10 helper (`_SELF_RECOVER_CASE_MAP` / `_classify_drift_failures` / `_fix_loud_fallback` / `_fix_readme_header_version` / `_fix_maturity_matrix_drift` / `_run_drift_prevention_smoke` / `_emit_recovery_summary` / `cmd_self_recover` / `_format_self_recovery_log` / `_emit_self_recovery_log`) + `cmd_release` step 2.7 + argparse `self-recover` subcommand 37 + `--skip-self-recover` flag + sys.path fix + README_PATH fix |
| extend | `workflow_kit/workflow_kit_cli.py` | MemoryIndexTelemetryEvent import schemas layer |

## housekeeping

- samples 24 file `tool_version` v0.13.1-beta → v0.13.2-beta
- schemas regen (generated_output_schemas + output_sample_contracts)
- dashboard HTML regen
- pyproject.toml 0.13.1 → 0.13.2
- workflow_kit/__init__.py loud fallback v0.13.1-beta → v0.13.2-beta
- README.md header v0.13.1-beta → v0.13.2-beta + Phase 13 v0.13.2 follow-up 1줄
- maturity_matrix.json v0.13.2 1줄 추가

## 검증 결과

- 신규 smoke **8/8 PASS** (check_self_recovering_v0_13_2)
- 3 skill smoke (session-start / doc-sync / backlog-update) **3/3 PASS**
- memory_index smoke **25/25 PASS**
- memory_index telemetry smoke **6/6 PASS**
- Quality Dashboard smoke **10/10 PASS**
- drift prevention smoke **6/6 PASS** (drift 주입 후 self-recover apply → 자동 정합)
- output samples + schema validation **3/3 PASS**
- mypy strict **0 new error** (22→21 errors, 1 less due to import fix)

**누적 smoke 219+ PASS** (v0.13.1 211+ + 신규 8 + 회귀 0 net new)

## release URL

- tag: `v0.13.2-beta`
- breaking change: ❌
- PyPI 배포: no