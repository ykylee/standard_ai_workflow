# Beta v0.14.6 — `refresh-maturity` dispatcher + `cmd_release` auto-wire (2026-07-16)

> **Task 3 follow-up close-out.** Phase 14 dashboard Panel 1 freshness 보강을
> standalone dispatcher subcommand 로 노출 + `cmd_release` post-emit 자동 호출.
> breaking change ❌.

## 1. 배경

v0.14.0 의 `cache.py:refresh_maturity_last_updated` helper 는 *manual 호출* 필요.
release 시 별도 갱신 단계를 잊으면 Panel 1 의 `last_updated_delta_days` 가 drift 됨.

본 release 는 이 helper 를 CLI dispatcher + `cmd_release` 자동 wire 로 노출하여
**release 시 별도 manual 갱신 없이 freshness 자동 유지** 를 달성.

## 2. 핵심 변경 (4 deliverable)

### 2.1 `cmd_refresh_maturity` dispatcher subcommand 신규

`workflow-source/tools/release_pipeline.py` argparse:

```bash
# default = apply (오늘 날짜로 갱신)
python3 release_pipeline.py refresh-maturity

# --today override
python3 release_pipeline.py refresh-maturity --today 2027-01-01

# --dry-run (plan 만 emit)
python3 release_pipeline.py refresh-maturity --dry-run

# --json output
python3 release_pipeline.py refresh-maturity --json
```

- args: `--today` (override) / `--maturity-path` (default `workflow-source/core/...`) / `--dry-run` / `--apply` (default True) / `--json`.

### 2.2 `cmd_refresh_maturity(args)` 함수

- helper `refresh_maturity_last_updated` (cache.py) 호출.
- **idempotent** — 이미 today 면 no-op.
- output: mode (apply / dry-run) + refreshed + before + after + today + maturity_path 5+ field.
- dry-run: `dry_run_note` 명시 + 실제 갱신 안 함.
- `refresh_maturity_last_updated` import 실패 시 graceful error.

### 2.3 `cmd_release` step 6.7 auto-wire

`gh release create` 성공 후 dashboard post-emit + self-recovery log 사이 호출.

- `refresh_maturity_last_updated` helper 를 `is not None` 일 때 호출 (workflow_kit import 실패 시 silent skip).
- `--dry-run` mode 미동작.
- exception 시 warning 만 (release 자체는 성공 유지).

### 2.4 Path doubled fix

`REPO_ROOT = Path(__file__).resolve().parents[1]` 가 `workflow-source/` (tools/ 의 parent) 이므로 `REPO_ROOT / 'workflow-source' / ...` 가 doubled path.

fix: `REPO_ROOT.parent / 'workflow-source' / 'core' / maturity_matrix.json`. resolve.

## 3. 신규 smoke `tests/check_refresh_maturity_v0_14_6.py` 4/4 PASS

- case_1: default apply + file `last_updated == 오늘 날짜`.
- case_2: dry-run → `refreshed=False` + `dry_run_note`.
- case_3: idempotency → `refreshed=False` + `before == after` (no-op).
- case_4: `--today 2027-01-01` + helper 정합 + file 검증 (revoke 시 reset).

## 4. 검증

- 누적 smoke **260+ PASS** (회귀 ❌)
- drift_prevention 6/6 · memory_lint 4/4 · memory_freeze_lint · appendonly_memory_layout 6/6 + WARN 1 · git_history_summarizer 5/5 · smart_context_reader 5/5 · apply_robust_patch 5/5 · phase15_dashboard_panels 4/4 · deprecation_cycle_v0_14_5 4/4 · **refresh_maturity_v0_14_6 4/4**

## 5. 의의

release 시 별도 manual 갱신 없이 `maturity_last_updated` 자동 갱신 → dashboard Panel 1
`last_updated_delta_days = 0` 유지 → **freshness drift 자동 해소**.

## 6. 일일 backlog (SSOT)

- [`ai-workflow/memory/release/v0.14.6/backlog/2026-07-16.md`](../ai-workflow/memory/release/v0.14.6/backlog/2026-07-16.md)

## 7. 다음 step

- HTML renderer Panel 6/7/8 + git reflog 통합 → **v0.14.7**.
- 2nd deprecation cycle 종결 (`.bak` drop, ⚠️ BREAKING) → **v0.15.0**.

---

release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.14.6-beta>