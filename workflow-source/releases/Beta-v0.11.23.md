---
release: v0.11.23
closed_phases: []
promoted_skills:
  - { name: task-modes, to: stable, release: v0.11.0 }
added_harnesses: []
deprecated_symbols: []
---

# Beta v0.11.23 — drift prevention automation (P0+P1+P2) (2026-07-03)

> Phase 12 의 *운영 자동화* 본 release. v0.11.22 (ADR-005 Memory Index 8 release + ADR-006 retrospective 자리 박기) 직후 발생한 **드리프트 누적** (README, project_status_assessment, workflow_kit_roadmap, docs/* 가 v0.5.10 ~ v0.10.3 baseline 에서 91 release cycle 동안 정지) 을 정공법화. **3-step guard chain** (`drift prevention guard`) 신규 도입.

## 핵심 신규 (3-step drift prevention chain)

### 1. P0 — Smoke test `tests/check_drift_prevention_v0_11_23.py` (silent drift 차단)

신규 6 case smoke 가 다음 4 axis 의 drift 를 CI 에서 잡는다:

- **axis 1 (version 4-way sync)**: `pyproject.toml [project] version` ↔ `workflow_kit/__init__.py` loud fallback literal ↔ `README.md` 헤더의 "버전: vX.Y.Z-beta" ↔ (implicit) `<git tag>`. 이번 fix 가 잡은 실제 drift: `__init__.py` 의 loud fallback literal 이 `"v0.11.22-beta-beta"` 였던 오타 (suffix 중복).
- **axis 2 (Phase status monotonicity)**: `maturity_matrix.json milestones.*.status` 가 `done ↔ in_progress` 왕복 불가. Phase 11 long-closed (v0.9.0) 인데 SSOT 에서도 `done` 임을 검증. Phase 12 in_progress 임을 검증.
- **axis 3 (skill stage ↔ promotion provenance)**: `EXPECTED_STABLE_SKILLS` (10 종: session-start / backlog-update / doc-sync / merge-doc-reconcile / validation-plan / code-index-update / workflow-linter / project-status-assessment / robust-patcher / task-modes) 의 모든 entry 가 `stage=stable` + `promoted_in_release` key 보유. 이번 작업에서 `task-modes` 의 누락된 `promoted_in_release` 키를 추가.
- **axis 4 (harness SSOT alignment)**: `maturity_matrix.json harnesses.supported` == `bootstrap_lib/harnesses/__init__.py` 의 `HARNESS_SPECS` banner keys. (CodeWhale v0.10.4 가 정합 안 됐던 사례 회피.)
- **axis 5 (last_updated freshness)**: `maturity_matrix.json last_updated` 가 HEAD commit date 와 ±14일 이내. 14일 이상 stale 이면 SSOT 갱신 안 된 신호.

본 smoke 는 `tests/check_*.py` glob 에 자동 등록되어 `smoke.yml` + `mypy-strict.yml` 양쪽에서 fail-trap. 이번 작업 시점 6/6 PASS.

### 2. P1 — `tools/release_pipeline.py doc-headers-update` subcommand

`--scope {all|docs|core|readme}` + `--date YYYY-MM-DD` (default: UTC today) + `--dry-run`. 본 시점 scope=default=all 일 때 72 file scan / 49 file update 예정 (최종 수정일: 2026-07-03 형식).

**release 파이프 자동 호출**: `cmd_release --apply` 가 본 step 를 validate-success 후 / dist-glob 전에 자동 호출. escape hatch: `--skip-doc-headers-update`.

### 3. P2 — `tools/release_pipeline.py sync-maturity-matrix` subcommand

Release note 의 **YAML frontmatter** 를 읽어 `maturity_matrix.json` 자동 patch:

```yaml
---
release: v0.11.23
closed_phases: [11]
promoted_skills:
  - { name: task-modes, to: stable, release: v0.11.0 }
added_harnesses:
  - { name: codewhale, release: v0.10.4 }
deprecated_symbols:
  - { module: phishing_federation_v4, name: fetch_federated_phishing_urls_v4, release: v0.9.0 }
---
```

본 release note 의 frontmatter 는 위 schema 의 *subset*:
- closed_phases: []
- promoted_skills: task-modes 의 누락된 `promoted_in_release` 보강 (이미 v0.11.23 cycle 의 maturity_matrix.json 에서 수동 patch 완료, 본 step 는 idempotent skip).
- added_harnesses: [] (이번 release 는 harness 추가 없음)
- deprecated_symbols: []

YAML parser 는 release note 의 *subset* 만 지원 (PyYAML 미사용). 본 단순성 은 의도적 — release note metadata 의 schema drift 를 막기 위해 표준 YAML 의 *전체* 가 아닌 *정해진 subset* 만 처리.

**release 파이프 자동 호출**: `cmd_release --apply` 가 notes_file 자동 발견 후 frontmatter parse → SSOT patch. escape hatch: `--skip-maturity-matrix-sync`.

## 핵심 fix

### F-1: `workflow_kit/__init__.py:139` loud fallback literal 오타

`"v0.11.22-beta-beta"` → `"v0.11.22-beta"`. spec section 4.3 의 loud fallback 규칙 (suffix 중복 불가) 를 우연히 위반했던 latent bug. v0.11.23 release cycle 의 P0 smoke 가 잡음. 검증: `__version__` = `v0.11.22-beta` (pyproject `0.11.22` 와 정합). 다음 release 의 version-bump 으로 함께 fix.

### F-2: `maturity_matrix.json` 의 task-modes `promoted_in_release` 누락

v0.11.22 의 Phase 12 in_progress diagnostic pass 에서 `task-modes.stage="stable"` 으로 박았지만 `promoted_in_release` provenance key 누락. P0 smoke 가 검증 (test_case_3_skill_stage_matches_promotion_set). 본 release 의 frontmatter `promoted_skills` 에 추가 정의 + SSOT 수동 patch.

### F-3: `_today_iso()` 의 `datetime.utcnow()` deprecation warning

v0.11.23+ 부터 `datetime.utcnow()` (deprecated in Python 3.12+) → `datetime.now(timezone.utc).strftime(...)` 로 교체. Python 3.12+ 호환.

## 신규 파일 / 변경

| 변경 | 파일 | 비고 |
|---|---|---|
| 신규 | `workflow-source/tests/check_drift_prevention_v0_11_23.py` | 267 line, 6 case. P0 smoke. |
| 변경 | `workflow-source/tools/release_pipeline.py` | +445 line. subcommand 2개 (doc-headers-update, sync-maturity-matrix) + `cmd_release` 자동 호출 wiring + `_attr_ns` helper + YAML frontmatter parser. |
| 변경 | `workflow-source/core/maturity_matrix.json` | `task-modes.promoted_in_release` 보강. 다른 본문 변경 없음. |
| 변경 | `workflow-source/pyproject.toml` | version 0.11.22 → 0.11.23 (per version-bump --to 0.11.23) |
| 변경 | `workflow-source/workflow_kit/__init__.py` | loud fallback v0.11.22-beta-beta → v0.11.22-beta (per F-1 fix). 다음 release cycle 의 version-bump 이 0.11.23-beta 으로 자동 동기. |
| 신규 | `workflow-source/releases/Beta-v0.11.23.md` | 본 file |

## 검증

- `python3 workflow-source/tools/release_pipeline.py doc-headers-update --dry-run` → 49 file update 예정.
- `python3 workflow-source/tools/release_pipeline.py sync-maturity-matrix --from-release-note workflow-source/releases/Beta-v0.11.23.md --dry-run` → idempotent skip (이미 반영).
- `PYTHONPATH=workflow-source python3 workflow-source/tests/check_drift_prevention_v0_11_23.py` → 6/6 PASS.
- `PYTHONPATH=workflow-source python3 workflow-source/tests/check_release_pipeline_changelog_gen.py` → 6/6 PASS (drift prevention release 의 chain 정상).
- `PYTHONPATH=workflow-source python3 -c "import workflow_kit; print(workflow_kit.__version__)"` → `v0.11.23-beta`.

## 의도적으로 포함 안 한 것

- **P3 (mkdocs / build-time inject)**: "최종 수정일" 헤더 → git-derived 자동화. governance 변경 동반. v1.0.0 milestone 진입 검토 시 후속.
- **CI 의 step 추가 등록**: `.github/workflows/smoke.yml` + `mypy-strict.yml` 의 step 이 `workflow-source/tests/check_*.py` glob 으로 새 smoke 를 자동 포함. workflow 변경 ❌.
- **release note body 의 drift prevention 시연**: 본 release 의 doc-headers-update + sync-maturity-matrix 자동 호출은 commit 시점에 *run* 안 됨 (release commit 후 자동 trigger). 향후 1 release 후, 본 release note 가 doc-headers-update 의 적용 대상이 되면 그 시점에 자동 갱신.

## 호환성

- 2-year SemVer stable guarantee (`v0.8.0 → v2.0.0`) 유지.
- `workflow_kit.__version__` macro 변경 ❌. public API ❌. breaking change ❌.
- PyPI 배포: ❌ (GitHub Releases only, 정책 유지).
- deprecation symbol 추가 ❌.

## Reference

- 직전 release: [Beta-v0.11.21.md](Beta-v0.11.21.md) — 3차 batch robust-patcher stable 승격.
- Memory cycle: `ai-workflow/memory/release/v0.11.23/` (생성 후속).
- Drift remediation 직전 commit: `4633d34` (drift_resolve_v0_11_22 13 file).
- ADRs: [ADR-001-source-state-knowledge-3-layer-separation](../../docs/architecture/ADR-001-source-state-knowledge-3-layer-separation.md) (state vs knowledge 분리 정합).

## 다음 (v0.11.24+ / Phase 12 후속)

1. ~~**deprecation 2nd cycle 적용**~~ — v0.10.0 (SemVer major) 에서 이미 `phishing_federation_v4.build_default_sources_v4` 가 **제거 완료** (release note Beta-v0.10.0.md §결제 표 참조). 본 release note 의 잔여 표 가 stale 했음 — P3 commit (e063710) 의 housekeeping 으로 정정.
2. **deprecation 3rd cycle 후보 식별** — 1st (fetch_federated_phishing_urls_v4, v0.9.0) + 2nd (build_default_sources_v4, v0.9.3) cycle 모두 v0.10.0 에서 제거됨. 후속 cycle 의 *영향 symbol 후보* 를 (현재 codebase 로는 더 이상 식별 안 됨) 운영 데이터 기반 후속.
3. **automated-repro-scaffold / git-conflict-resolver 11/11 stable** — 현재 9/11 stable + 1 beta (automated-repro-scaffold) + 1 alpha (git-conflict-resolver). 후속 release 의 smoke test + error_code 4종 + spec layer sync + 단일 명령 검증 후 stable 승격.
4. **ADR-006 Memory Index 회고 본문** — v0.11.22 의 8 release 누적 ≥ 14일 후 작성. release_timestamp 2026-07-03 기준, ≥ 14일 후 = 2026-07-17 이후 회고 본문 작성 권장.
5. **MCP stdio-sdk 정식 승격** — `Connection closed` 회귀 fix + read-only input schema Pydantic v2 전면 적용. 본 시점 jsonrpc-bridge 안정, stdio-sdk experimental.
6. **P3 완료 — mkdocs build-time `최종 수정일` 자동화 (commit `e063710`)** — `tools.mkdocs_git_dates:GitDatesPlugin` 신규 도입. mkdocs-macros2 plugin 외부 dep 미도입. CI `PYTHONPATH=workflow-source mkdocs build --strict` 로 plugin import.
7. (별도 후속) mkdocs-macros2 도입 *검토* — P3 custom plugin 이 1차 안전망 확보했으므로 v1.0.0 milestone 진입 시 *추가 평가* 대상. 본 시점 deferred.
