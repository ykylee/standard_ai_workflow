# Beta v0.15.19 — cross-panel final 정합 (2026-07-20)

> v1.0.0 진입 평가의 **cross-panel final anchor**.
> Panel 1~8 모두 정합 + 누적 smoke 24종 PASS + 모든 housekeeping 정합 final review.
> 누적 smoke 24종, 회귀 0건.

## 1. 릴리스 요약

- Panel 1~8 cross-panel 정합 final review (8 panel 모두 SSOT 정합).
- 누적 smoke 24종 회귀 0 (24/24 PASS).
- 모든 housekeeping 정합 (sample / README / INSTALLATION / QUICKSTART / PROJECT_PROFILE / CODE_INDEX / RELEASE).
- v1.0.0 진입 평가의 cross-panel final anchor.

## 2. 검증 (3 정합 영역)

### 2.1 Panel 1~8 dashboard 정합

| Panel | Status | Metrics |
|---|---|---|
| Panel 1 (Drift Prevention) | pass | guard 6/6, harness_supported_count 11, maturity fresh, silent_failing 0 |
| Panel 2 (Maturity Distribution) | compliant | skills 12 stable + mcp 11+1 removed + milestones 11+1 + harnesses 11 |
| Panel 3 (Memory Index) | compliant | 7 entries, cue_anchors 40, retrieval_hit_rate 1.0 |
| Panel 4 (Smoke Trend) | compliant | 260/260 PASS, smoke_files_count 196 |
| Panel 5 (Recent Release Cycle) | compliant | items_total 10 (recent 10 releases) |
| Panel 6 (Multi-Agent Conflict) | pass | conflict_count 0, threshold 0 |
| Panel 7 (Deprecation Cycle) | complete | stage v0.15.0, next_release (complete) |
| Panel 8 (Telemetry v2) | compliant | events_total 1, hit_rate 1.0 |

### 2.2 11 harness cross-panel 정합

- `check_harness_v0_15_9.py` 4/4 PASS.
- Panel 1 `harness_supported_count` (11) == Panel 2 `harnesses.supported` (11) == maturity_matrix `harnesses.supported` (11) == `workflow-source/harnesses/` 실제 디렉토리 (11).
- 3-way set 동등성 (Panel 2 names == mm names == file system names).
- 적용 harness 11: codex, opencode, gemini-cli, antigravity, minimax-code, claude-code, aider, goose, grok-build, pi-dev, codewhale.

### 2.3 24 smoke full regression

- drift_prevention 6/6 + harness 4/4 + readme 4/4 + installation 4/4 + quickstart 4/4 + sample 4/4 + document_index 4/4 + code_index 5/5 + release 5/5 + memory_governance 5/5 + phase15_panels 4/4 + smoke_trend 5/5 + telemetry 4/4 + memory_index 4/4 + maturity_distribution 4/4 + harness_apply_guide 4/4 + refresh_maturity (3종) 11/11 + deprecation_3rd_cycle 3/3 + appendonly 6/6 + memory_lint 4/4 + audit_mkdocs_links 5/5 + quality_dashboard 12/12.

**누적 smoke 24종 PASS, 회귀 0**.

## 3. Housekeeping 정합 (final review)

| File | 변경 |
|---|---|
| README.md | `package: standard-ai-workflow 0.15.16` → `0.15.18` + harness list 정합 |
| sample 24 file | `v0.15.17-beta` → `v0.15.18-beta` (특히 `check_doc_metadata.examples.json` / `check_quickstart_stale_links.sample.json` 의 stale 2 file 정정) |
| docs/CODE_INDEX.md | `version 0.15.16` → `0.15.18` + `Beta v0.5.0 ~ v0.15.16` → `v0.15.18` |
| docs/PROJECT_PROFILE.md | `package: standard-ai-workflow 0.15.16` → `0.15.18` |
| maturity_matrix.json | v0.15.19 highlight 추가 (JSON escape 정공법) |
| ai-workflow/dashboard/snapshot.md | regen (Panel 1~8 모두 정합) |

## 4. v1.0.0 진입 평가 진행 상황

| Break Point | 상태 |
|---|---|
| #1 state.json / Panel 5 | ✅ CLOSED-OUT (v0.15.17) |
| #2 TST-WF-01 non_compliant | ✅ CLOSED-OUT (v0.15.18) |
| #3 mypy strict 직접 verify | ⏳ venv 활성화 후 (CI 3-layer defense 정합으로 운영 risk 낮음) |
| **Cross-panel final anchor** | ✅ **CLOSED-OUT (v0.15.19)** |

## 5. 다음 단계

- v0.15.20 — v1.0.0 pre-release final (stable API 명세 + SemVer 2-year guarantee doc + migration guide final).
- **v1.0.0** — stable release.

---

release target: `v0.15.19-beta`
