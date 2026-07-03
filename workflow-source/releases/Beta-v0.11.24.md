---
release: v0.11.24
closed_phases: []
promoted_skills:
  - { name: automated-repro-scaffold, to: stable, release: v0.11.24 }
  - { name: git-conflict-resolver, to: stable, release: v0.11.24 }
added_harnesses: []
deprecated_symbols: []
---

# Beta v0.11.24 — 11/11 skill stable milestone (2026-07-03)

> Phase 12 의 *운영 자동화 + 안정화 완료*. v0.11.23 (drift prevention automation P0+P1+P2+P3) 의 잔여 cleanup 으로 **11/11 core skill 모두 stable** 달성. cumulative mypy strict 109+ file clean, 0 errors. task-modes 별도 track 도 stable (skill count 12 stable, 0 beta, 0 alpha).

## 핵심 (3-batch)

### 1) automated-repro-scaffold beta → stable (v0.11.24 4th batch)

v0.6.5 commit 5b16517 의 prototype 에서 stable 정합 6 조건 만족:

- **신규** `workflow_kit/common/schemas/automated_repro_scaffold.py` — Pydantic v2 `AutomatedReproScaffoldOutput` (BaseOutput 상속, Status.OK), nested `AutomatedReproScaffoldSourceContext`.
- **이동** `skills/automated-repro-scaffold/automated_repro_scaffold.py` → `skills/automated-repro-scaffold/scripts/run_automated_repro_scaffold.py` — 표준 진입점 정공법.
- argparse 보강: `--report` / `--output` (required) / `--dry-run` / `--json`.
- **error_code 4종**: `automated_repro_scaffold_report_file_not_found` / `automated_repro_scaffold_output_dir_unwritable` / `automated_repro_scaffold_template_render_failed` / `automated_repro_scaffold_runtime_error`.
- SKILL.md 의 `예시 실행` 섹션 (3 example: 정상 / report 부재 / dry-run).
- **신규** `tests/check_automated_repro_scaffold_v0_11_24.py` — 5 case smoke (PASS).

### 2) git-conflict-resolver alpha → beta → stable (v0.11.24 4th batch — 2-step)

v0.6.6+ prototype + v0.11.24 refactor + v0.11.24 --apply 구현으로 stable 정합 6 조건 만족:

- indentation 깨진 dead code 제거.
- 4 error_code: `git_conflict_resolver_handoff_parse_failed` / `git_conflict_resolver_file_unreadable` / `git_conflict_resolver_resolution_invalid` / `git_conflict_resolver_runtime_error`.
- **`--apply` 구현** (placeholder 에서 정식 구현으로):
  - `_apply_resolution(conflict)` helper — strategy 별 resolution_text 반환 (OURS / THEIRS / MERGE / MANUAL).
  - `_write_resolved_file(src, conflicts, output_dir)` — *in-place write ❌*, atomic write (.tmp → rename) + `*.resolved.py` suffix 또는 `--output-dir` redirect.
  - MANUAL strategy conflict 는 그대로 보존 (marker 유지).
- argparse: `--file action='append'` / `--handoff-path` / `--apply` / `--output-dir` / `--dry-run` / `--json`.
- **신규** `tests/check_git_conflict_resolver_v0_11_24.py` — 8 case smoke (apply / strategy unit / handoff graceful / in-place 안전 / MANUAL 보존).

### 3) MCP stdio-sdk promotion readiness smoke + ADR-007 placeholder

- **신규** `tests/check_mcp_stdio_sdk_promotion_readiness_v0_11_24.py` — 5 case smoke (spec §6 verification command 존재 / §1 transport status 정합 / sdk_runtime_status() advertise / §4 12 contract keyword / export file 존재).
- **신규** `docs/architecture/ADR-007-deprecation-3rd-cycle-candidates.md` — 1st (v0.9.0) + 2nd (v0.9.3) cycle 모두 v0.10.0 에서 removal 완료. 현재 codebase 의 영향 symbol 재스캔 결과: 0개 (의도된 결과). 후속 영향 식별 시 본문 작성 자리.

## 안정화 정합 (v0.11.24 cycle 검증)

```
Skill count:
  stable = 11 (session-start, backlog-update, doc-sync, merge-doc-reconcile,
              validation-plan, code-index-update, workflow-linter,
              project-status-assessment, robust-patcher,
              automated-repro-scaffold, git-conflict-resolver)
  stable (independent) = 1 (task-modes)
  beta  = 0
  alpha = 0
  ─────────────────────────────
  total = 12 stable, 0 beta, 0 alpha   ← v1.0.0 milestone 진입 평가 가능
```

```
누적 smoke test (v0.11.24 cycle):
  check_drift_prevention_v0_11_23.py                          6/6 PASS
  check_drift_prevention_helpers_v0_11_23.py                  5/5 PASS
  check_mkdocs_git_dates_plugin_v0_11_23.py                   5/5 PASS
  check_automated_repro_scaffold_v0_11_24.py                 5/5 PASS
  check_git_conflict_resolver_v0_11_24.py                    8/8 PASS  (--apply 신규 3 case)
  check_mcp_stdio_sdk_promotion_readiness_v0_11_24.py        5/5 PASS
  check_release_pipeline_changelog_gen.py                     6/6 PASS
  누적                                                              40/40 PASS
```

## 핵심 fix / 신규 (요약)

### F-1: git-conflict-resolver `--apply` 구현 (v0.11.24 cycle 의 *핵심*)

이전:
- `--apply` 가 placeholder ("Apply resolutions (placeholder; v0.11.24+ future work)").

신규:
- strategy 4종 (OURS / THEIRS / MERGE / MANUAL) 의 actual resolution_text 생성.
- per-file write: 원본 file unchanged, `*.resolved` suffix 또는 `--output-dir` redirect.
- atomic write (POSIX `os.replace` guarantee).
- MANUAL conflict marker 보존 (caller 가 후속 manual resolution 가능).
- _apply_resolution unit test 4종 + subprocess-level 3 case smoke.

### F-2: maturity_matrix stable 정합 보강 (11/11 milestone)

이전 (v0.11.21 ~ v0.11.23):
- 9 stable + 1 beta (automated-repro-scaffold) + 1 alpha (git-conflict-resolver).

v0.11.24 결과:
- 11 stable + 0 beta + 0 alpha (skill core 11종 + task-modes 1종 = 12 total stable).
- check_drift_prevention_v0_11_23.py 의 EXPECTED_STABLE_SKILLS set 이 12개로 확장 (automated-repro-scaffold, git-conflict-resolver 추가).
- 11/11 stable milestone 정공법 검증 — 모든 *core skill* 이 stable channel.

### F-3: MCP stdio-sdk 정식 승격 사전 검증

현황:
- jsonrpc-bridge (stable, default) + stdio-sdk (experimental, Connection closed 회귀 미완).
- 본 cycle 에서 promotion readiness smoke 5 case 추가. promotion 자체는 후속 release.

### F-4: ADR-007 placeholder (deprecation 3rd cycle)

deprecation 정책 운영 추적 anchor:
- 1st (v0.9.0) + 2nd (v0.9.3) cycle 완료 / v0.10.0 에서 removal.
- 3rd cycle 영향 symbol 재스캔 결과: 0개.
- 영향 식별 시 본문 작성 자리 (placeholder).
- v1.0.0 milestone 진입 평가 시 본문 작성 (legacy symbol audit 결과).

## 신규 파일 / 변경

| 변경 | 파일 | 비고 |
|---|---|---|
| 신규 | `workflow_kit/common/schemas/automated_repro_scaffold.py` | Pydantic v2 schema |
| 이동 | `skills/automated-repro-scaffold/automated_repro_scaffold.py` → `scripts/run_automated_repro_scaffold.py` | git mv (표준화) |
| 변경 | `skills/automated-repro-scaffold/SKILL.md` | stable / 예시 실행 / 4 error_code 표 |
| 변경 | `skills/git-conflict-resolver/scripts/run_git_conflict_resolver.py` | `--apply` / `--output-dir` / 4 error_code / per-file grouping |
| 변경 | `workflow_kit/common/schemas/__init__.py` | `AutomatedReproScaffoldOutput` + `AutomatedReproScaffoldSourceContext` export |
| 변경 | `core/maturity_matrix.json` | automated-repro-scaffold + git-conflict-resolver stable 승격, last_updated |
| 변경 | `tests/check_drift_prevention_v0_11_23.py` | EXPECTED_STABLE_SKILLS 확장 (10 → 12) |
| 변경 | `tests/check_git_conflict_resolver_v0_11_24.py` | 5 case → 8 case (--apply 3 case 추가) |
| 신규 | `tests/check_automated_repro_scaffold_v0_11_24.py` | 5 case smoke |
| 신규 | `tests/check_mcp_stdio_sdk_promotion_readiness_v0_11_24.py` | 5 case smoke |
| 신규 | `docs/architecture/ADR-007-deprecation-3rd-cycle-candidates.md` | deprecation 3rd cycle 자리 박기 |
| 변경 | `docs/architecture/README.md` | ADR-007 목록 추가 |
| 변경 | `workflow_kit/common/schemas/__init__.py` | (위와 동일) |

## 검증

- 누적 smoke test **40/40 PASS** (v0.11.23 22 + v0.11.24 skill 5+8 + v0.11.24 mcp 5).
- skill count: **12 stable + 0 beta + 0 alpha** (= 11/11 core + 1 task-modes).
- `__version__` = v0.11.24-beta (pyproject 0.11.24 정합).
- `workflow_kit/__version__` macro 변경 없음 (literal fallback 만 갱신).
- mypy strict 누적: 109+ file clean (v0.11.21 시점 + v0.11.24 신규 file — _write_resolved_file / _apply_resolution — mypy 정합).

## 호환성

- 2-year SemVer stable guarantee (v0.8.0 → v2.0.0) 유지.
- public API 추가 ❌ (Pydantic schema + dataclass 정합은 stable API 의 일부).
- breaking change ❌. 기존 dict caller 는 model_dump_json() 의 dict emission 과 정합.
- PyPI 배포: ❌. GitHub Releases only.
- 기존 v0.6.5+ 의 stage_completion merge 동작 보존.

## 잔여 (v0.11.25+ / Phase 12 후속 → v1.0.0 milestone 진입 평가)

1. **v1.0.0 milestone 진입 평가** — 본 cycle 의 11/11 stable milestone 이 trigger. 평가 항목:
   - 누적 smoke test 40/40 정합 유지.
   - consumer 1+ months 안정 운영 데이터 (현재 0 일; v0.11.22 release 직후).
   - ADR-006 Memory Index retrospective 본문 (≥ 14일 후, v0.11.22 release 직후).
   - ADR-007 legacy symbol audit (v1.0.0 진입 평가 시점).
2. **ADR-006 Memory Index 회고 본문** — v0.11.22 의 8 release 누적 ≥ 14일 후 (≥ 2026-07-17).
3. **MCP stdio-sdk 정식 승격** — `Connection closed` 회귀 fix + Pydantic v2 input schema 전면 적용 (코드 작업, 별도 release).
4. **(P3 후속) mkdocs-macros2 도입 검토** — custom plugin 으로 1차 안전망 확보. v1.0.0 milestone 진입 시 추가 평가.

## Reference

- 직전 release: [Beta-v0.11.23.md](Beta-v0.11.23.md) — drift prevention automation (P0+P1+P2+P3).
- 11/11 stable milestone 의 trigger: automated-repro-scaffold + git-conflict-resolver 의 4th batch.
- ADR: [ADR-005 Memora-inspired Memory Index](../../docs/architecture/ADR-005-memora-inspired-memory-index.md), [ADR-006 Retrospective (Placeholder)](../../docs/architecture/ADR-006-memory-index-retrospective.md), [ADR-007 3rd Cycle (Placeholder)](../../docs/architecture/ADR-007-deprecation-3rd-cycle-candidates.md).
- Memory cycle: `ai-workflow/memory/release/v0.11.24/` (생성 후속).
- Drift prevention chain: [Beta-v0.11.23 §핵심 신규 1/2/3](Beta-v0.11.23.md#핵심-신규-3-step-drift-prevention-chain).