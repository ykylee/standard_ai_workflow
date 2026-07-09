# Work Backlog Index

- 문서 목적: 일별 작업 백로그에 대한 인덱스로, 최근 작업 흐름을 빠르게 복원한다.
- 범위: 인덱스 항목, 백로그 경로 규약, 갱신 규칙
- 대상 독자: AI agent, 저장소 maintainer
- 상태: stable
- 최종 수정일: 2026-07-09 (audit-follow-up: P0 3 + P1 3 + P2 4 = 10건 후보 일괄 해소 entry 추가)
- 관련 문서: [./PROJECT_PROFILE.md](./PROJECT_PROFILE.md), 브랜치별 daily backlog (각 브랜치 디렉터리 아래 `backlog/YYYY-MM-DD.md`)

## 인덱스 규칙

- 각 `### [[release/v0.5.X/backlog/YYYY-MM-DD.md]] {#release-v0-5-X}` 형식의 anchor entry 로 인덱스 표시
- anchor ID 로 직접 retrieval (session-start 의 index-based load)
- 각 일자 백로그는 TASK-NNN 식별자를 가진 작업 항목 1개 이상 포함
- 같은 일자에 여러 브랜치 작업이 있으면 브랜치별로 별도 백로그 파일
- **세션 종료 절차는 [`../../workflow-source/core/global_workflow_standard.md`](../../workflow-source/core/global_workflow_standard.md) §8 정합 — `memory 갱신 → commit → push` 순서**

## 최근 작업 백로그

### [[active/session_analysis_2026-07-09.md]] {#active-session-analysis-2026-07-09}
- 2026-07-09: 워크플로우 구성 점검 + 고도화 후보 10건 도출 (audit-session, no release). 현 상태 v0.11.22-beta 스냅샷 (Phase 12 in_progress, skill stable=9 / MCP beta=4 / 10 harness / mypy 109 file clean). P0 3건 (project_status_assessment.md §2 점수 / PROJECT_PROFILE.md self-dogfood / memory_index/ 디렉토리 실재성) + P1 3건 (ADR-006 retrospective / MCP beta 승격 로드맵 / drift 91-cycle 사례 분류) + P2 4건 (Phase 13 정의 / wiki-memory 양방향 link / quality dashboard / automated-repro-scaffold AI 연동 강화). 산출물: `ai-workflow/memory/active/session_analysis_2026-07-09.md` (단기) + `ai-workflow/wiki/topics/workflow-audit-2026-07-09.md` (영구). state.json recent_done_items 1줄 추가. 다음 세션 권장 작업: P0 빠른 정리부터.

### [[active/audit_follow_up_2026-07-09.md]] {#active-audit-follow-up-2026-07-09}
- 2026-07-09: 2026-07-09 audit-session 의 고도화 후보 10건 일괄 해소 (audit-follow-up, no release). P0 3건: project_status_assessment.md §2 매트릭스 11항목 점수 (합계 26/33, 78.8%) / PROJECT_PROFILE.md self-dogfood §1/§3/§4/§5/§6 (152 line) / memory_index/ 디렉토리 + 7 seed entry (MEM-2026-07-09-001~007) + retrieval 동작 검증. P1 3건: adr-006-retrospective-2026.md early observation (109 line, full review scheduled 2026-07-16) / Beta MCP 4종 stable 승격 로드맵 (1st batch v0.11.26 + 2nd batch v0.11.28) + maturity_matrix 필드 추가 / drift-prevention 91 cycle 사례 5 category 분류 (13 file 영향, hook 5 후보). P2 4건: Phase 13 정의 (north-star = silent_failing_cycles_count, 운영 지능화 1차 north-star) / Wiki↔Memory 양방향 link R-A~R-C / Quality dashboard 5 panel / automated-repro-scaffold AI 연동 강화 R-1~R-4. **검증**: drift prevention smoke 6/6 PASS + memory_index validation 0 issue + maturity_matrix schema v1 정합 + memory_index retrieval cue anchor 매칭 정상. **도구 제약 관측**: MiniMax-M3 model_provider 환경에서 표준 Codex file-editor tool 미노출 → exec_command + heredoc + Python helper (save_memory_entry 등) 우회. ADR-003 read-only 정책과 정합. **산출물**: 4 file edit (project_status_assessment.md / PROJECT_PROFILE.md / maturity_matrix.json / memory_index/README.md 포함) + 7 신규 file (adr-006-retrospective-2026.md / mcp-beta-promotion-roadmap-2026.md / drift-prevention-91-cycle-classification-2026.md / phase-13-definition-north-star.md / wiki-memory-bidirectional-link-design.md / quality-dashboard-implementation-guide.md / automated-repro-scaffold-ai-integration.md) + 7 memory_index entry JSON. state.json recent_done_items 1줄 추가 (P0/P1/P2 10건 종합 요약). breaking change: ❌.

### [[release/v0.11.21/backlog/2026-07-02.md]] {#release-v0-11-21}
- 2026-07-02: v0.11.21 — **SemVer patch, 3차 batch robust-patcher stable 승격**. v0.11.20 (2차 batch 4 skill stable) 의 follow-up 인 1 skill stable 승격 (3 beta skill 중 가장 성숙한 Beta → stable). 누적 stable=9 / beta=2 / prototype=4. 6 조건 stable 정합 모두 충족 (CLI argparse / Pydantic schema / error_code 4종 / 단일 명령 / 예시 실행 섹션 / smoke test 5 case PASS). 신규 `workflow_kit/common/schemas/patcher.py` (35 line) 의 `RobustPatcherOutput` Pydantic schema 정합 (legacy `patch_engine.py` dict emission → 다른 stable skill 의 `BaseOutput` 패턴과 정합). **script 표준화** — 비표준 `scripts/patch_engine.py` (trash) → 표준 `scripts/run_robust_patcher.py` (180 line, `scripts/run_<skill>.py` catalog §5 패턴 정합). **신규 helper** `apply_robust_patch_detailed` 3-tuple (per-block detail: block_index / matched / fuzzy_score / preview). **atomic semantics** — fuzzy fail 시 즉시 rollback (caller 가 partial apply 결과 받지 않음). **housekeeping** — `examples/output_samples/*.json` 24 file tool_version v0.11.19-beta → v0.11.20-beta 갱신 + `schemas/generated_output_schemas.json` `robust_patcher` family 등록. 누적 mypy 108 → **109 file clean**, 0 errors. 6 commit + 1 amend (`d90f786` schema + helper → `9249324` script 표준화 → `ba689a3` smoke test → `63c22c8` spec layer sync → `356c8a1` samples housekeeping + release-bump amend → `c90b437`). GitHub Release `v0.11.21-beta` tag push + gh release create exit 0 (https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.21-beta). PyPI 배포: no. breaking change: ❌.

### [[release/v0.11.20/backlog/2026-07-01.md]] {#release-v0-11-20}
- 2026-07-01: v0.11.20 — **SemVer patch, 2차 batch 4 skill stable 승격 + 2 latent bug fix**. v0.11.19 (1차 batch) 의 follow-up 으로 4 skill (backlog-update / merge-doc-reconcile / workflow-linter / project-status-assessment) 의 stable 채널 승격 + 누적 stable=8 / beta=3 / prototype=4. 6 조건 stable 정합 모두 충족 (각 skill 별 신규 smoke test + error_code 4종 + 예시 실행 섹션). 신규 `workflow_kit/common/schemas/assessment.py` (71 line) 의 `ProjectStatusAssessmentOutput` Pydantic schema 정합 (legacy `build_runner_success_result` dict emission → 다른 stable skill 의 `BaseOutput` 패턴과 정합). **v0.6.0.1 부터 누적된 state.json path latent bug fix** — `workflow_kit/common/state/cache.py` 의 `/ "active"` suffix 제거 (production `ai-workflow/memory/active/state.json` 와 정합). **workflow-linter broken_link false-positive fix** — `os.path.normpath` 로 `..` 정규화. **housekeeping** — `examples/output_samples/*.json` 24 file tool_version v0.11.17-beta → v0.11.19-beta 갱신 + `schemas/generated_output_schemas.json` `project_status_assessment` family 등록. 누적 mypy 107 → **108 file clean**, 0 errors. 7 commit + 1 amend (`4821b71` cache fix → `9960e8f` linter fix → `65d5591` assessment schema → `ddac80e` 2 skill error_code → `29ae1cc` 2 신규 smoke test → `cb32d6c` spec layer sync → `e672ff2` samples housekeeping + release-bump amend → `af6baaf`). GitHub Release `v0.11.20-beta` tag push + gh release create exit 0 (https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.20-beta). PyPI 배포: no. breaking change: ❌.

### [[release/v0.11.19/backlog/2026-07-01.md]] {#release-v0-11-19}
- 2026-07-01: v0.11.19 — **SemVer patch, 1차 batch 4 skill stable 승격**. roadmap §8 Phase 12 in-progress 의 "11 beta skill stable 승격 1차 batch" deliverable. v0.5.10-beta 부터 beta 상태로 운영된 **4 skill** (session-start / doc-sync / validation-plan / code-index-update) 의 stable 채널 승격 + skill_beta_criteria.md + workflow_skill_catalog.md spec layer 동기화. stable 승격 정합 조건 6 항목 (CLI argparse / JSON 스키마 / error_code 3종+ / 단일 명령 / SKILL.md 실행 예시 / smoke test PASS) 모두 충족. 누적 stable=4 / beta=7 / prototype=4. follow-up batch: backlog-update / merge-doc-reconcile / workflow-linter / project-status-assessment 4 skill 의 blocker 해결 후 stable (v0.11.20+). GitHub Release `v0.11.19-beta` tag push + gh release create exit 0 (https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.19-beta). PyPI 배포: no. breaking change: ❌.

### [[release/v0.11.18/backlog/2026-07-01.md]] {#release-v0-11-18}
- 2026-07-01: v0.11.18 — **🎯 SemVer patch, FULL mypy strict 도달 공식 봉인 (107 file clean)**. 누적 mypy strict 잔여 23 → 0 error 격상 (`094cacf` mcp_v1_server + release_status 6 + `65f0b20` read_only_mcp_sdk + doc_sync 4 + `4253eed` 잔여 13 일괄) + in-scope fix CI mcp-sdk extra install (`7ffb17c` → amend `80470cd`, 4c83ed9 CI run 28453667753 의 `[import-not-found]` 해소). 누적 mypy 35 → **54 file clean**, 48 → **0 errors** (-48). 3-layer defense (Layer 1 CI ✅ / Layer 2 release-time gate ✅ / Cross-verify ci_sanity ✅). GitHub Release `v0.11.18-beta` tag push + gh release create exit 0 (https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.18-beta). PyPI 배포: no. breaking change: ❌.

### [[release/v0.11.17/backlog/2026-06-30.md]] {#release-v0-11-17}
- 2026-06-30: v0.11.17 — **SemVer patch**, mypy strict cumulative 25 error 격상 (output_contracts 15 + cli/doctor+common/decorators 10) + schema drift housekeeping (sample 24 + schema 2) + in-scope fix (release_pipeline.py PYTHONPATH shadowing bug). 누적 mypy 35 → 38 file clean, 48 → 23 errors (-25). GitHub Release `v0.11.17-beta` tag push + gh release create exit 0 (https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.17-beta). PyPI 배포: no. breaking change: ❌.

### [[main/backlog/2026-06-30.md]] {#main-2026-06-30}
- 2026-06-30: workflow 종료 단계 commit/memory 순서 정정 (commit `32185c7`) — 협업 결함 (push 시 memory 갱신 누락 / 추가 commit 유발) 해결. 11 file 변경: `workflow-source/core/global_workflow_standard.md` §8 + `MEMORY_GOVERNANCE.md` §3 + `phase5_governance_guide.md` §4 + `extensions/resiliency-baseline.md` RES-WF-08 + `harnesses/{pi-dev,codex,gemini-cli,opencode}/` AGENTS/apply_guide + `examples/{acme_delivery_platform,research_eval_hub}/work_backlog.md` + `templates/work_backlog_template.md` 모두 **`memory 갱신 → commit → push`** 순서로 정합. release: no / version bump: no (governance 문서 정정).
- 2026-06-30: workflow 종료 단계 §8 정합 후속 (commit `298704f`) — audit 잔재 0 확인 + `ai-workflow/wiki/` cross-ref 보강: `concepts/memory-3-state-lifecycle.md` §4 (Active 갱신 = commit 직전 정책 row) + §6 References + `concepts/project-architecture.md` 3-Layer 표 (Runtime layer 정합) + Memory 3-State 표 (Active lifecycle "→ commit → push") + §6 References + `log.md` 2026-06-30 governance entry append. 3 file 변경. release: no / version bump: no.
- 2026-06-30: R9 wiki source rule lint 검증 (commit `1333cc8`) — `check_wiki_source_rule.py` FAIL (1 violation: `wiki-maintainability-score.md` 의 dashboard emit line 405 표현이 R9 regex false-positive 트리거) → tool 수정 (`tools/score_wiki_maintainability.py` line 405 multi-line 분리) + dashboard regenerate → R9 lint PASS. 2 file 변경. release: no / version bump: no.
- 2026-06-30: mypy strict output_contracts 15 error 격상 (commit `f6b65a4`) — roadmap §8 #2 정공법 (1 release = 1 file). `schemas/__init__.py` `__all__` 확장 (14 attribute attr-defined 해소) + `output_contracts.py:360` unused type:ignore 제거. 누적 35 → 36 file clean, mypy 48 → 33 errors. 별도 발견: `check_output_json_schema.py` FAIL — 기존 schema drift (v0.9.x~v0.11.x 의 BacklogUpdateOutput/SessionStartOutput properties 진화 미반영), 본 fix 와 무관. release: no / version bump: no (별도 release cycle 결정).
- 2026-06-30: schema drift housekeeping (commit `00cc83e`) — `f6b65a4` mypy fix 의 lint sanity 에서 발견된 *기존* schema drift 해소: `examples/output_samples/*.json` 24 file 의 `tool_version` v0.5.10.1-beta → v0.11.16-beta 갱신 + runtime `SUCCESS_PATH_CONTRACTS`/`ERROR_PATH_CONTRACTS` 정합 (purpose_context, graph_insights 등 v0.9.x~v0.11.x 진화 누락분 default null 추가) + `output_sample_contracts.json` regenerate + `generated_output_schemas.json` regenerate. `check_output_samples.py` FAIL → PASS (24 files), `check_output_json_schema.py` FAIL → PASS. 26 file 변경. release: no / version bump: no (housekeeping).
- 2026-06-30: mypy strict cli/doctor + common/decorators 묶음 격상 (commit `97795bc`) — roadmap §8 #2 정공법 (1 release = 2 file). cli/doctor.py 6 error (DoctorConfig | None param + dict[str, Any] return + unused type:ignore) + common/decorators.py 4 error (redundant cast + unused type:ignore) → 0. 누적 36 → 38 file clean, mypy 33 → 23 errors. verification: check_baselines_compliance 16 PASS, check_output_samples 24 PASS, check_wiki_source_rule R9 PASS. 2 file 변경. release: no / version bump: no.
- 2026-06-30: mypy strict mcp_v1_server + release_status 묶음 격상 (commit `094cacf`) — roadmap §8 #2 정공법 (1 release = 2 file). v0.11.17 release 후속. mcp_v1_server.py 3 error (unused type:ignore + Callable[..., Any] + run() -> None) + release_status.py 3 error (no-any-return + unused type:ignore + args: Any) → 0. 누적 38 → 40 file clean, mypy 23 → 17 errors. in-scope fix: examples/output_samples/*.json 24 file tool_version v0.11.16-beta → v0.11.17-beta (v0.11.17 release 후 발생한 drift). verification: check_baselines_compliance 16 PASS, check_output_samples 24 PASS, check_wiki_source_rule R9 PASS. 26 file 변경 (2 source + 24 sample). release: no / version bump: no.
- 2026-06-30: mypy strict read_only_mcp_sdk + doc_sync 묶음 격상 (commit `65f0b20`) — roadmap §8 #2 정공법 (1 release = 2 file). server + common cross-layer. read_only_mcp_sdk.py 2 error (untyped-decorator × 2) + doc_sync.py 2 error (redundant cast × 2) → 0. 누적 40 → 42 file clean, mypy 17 → 13 errors. verification: check_baselines_compliance 16 PASS, check_wiki_source_rule R9 PASS. 2 file 변경. release: no / version bump: no.
- 2026-06-30: mypy strict 잔여 13 error 일괄 격상 (commit `4253eed`) — **FULL mypy strict 도달 (107 file clean)**. session 마무리. 12 file 일괄 격상 (정공법 1 release = 1-2 file 약간 over이지만 잔여 모두 정리): auth.py / stage_gate_runtime.py (2) / doc_transformer.py / exploration.py / git.py / metadata.py / profiling.py / resiliency.py / runner.py / testing.py / delegator.py / workflow_kit_cli.py → 0. 누적 42 → **54 file clean** (+12), mypy 13 → **0 errors** (-13). 107/107 file clean. verification: check_baselines_compliance 16 PASS, check_wiki_source_rule R9 PASS, check_output_samples 24 PASS, check_generated_schema_validation PASS, check_output_json_schema PASS. 12 file 변경. release: no / version bump: no (v0.11.18 candidate 에서 FULL mypy strict 도달의 공식 release).

### [[release/v0.11.15/backlog/2026-06-26.md]] {#release-v0-11-15}
- 2026-06-26: v0.11.15 — **SemVer patch**, release summary 1-line (jq-friendly verdict). `cmd_release` + `cmd_release_status` JSON output 에 `summary` 5-field (ci_mypy / local_mypy / ready / next / error|unreleased) 추가. `_summarize_release_status` (release_status.py) + `_attach_release_summary` (release_pipeline.py) 2 helper + 11 return point wrap. `_resolve_cross_verify_verdict` 정합 (local empty → no_local_verify, 이전 drift_warning 잘못). release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.15-beta>.

### [[release/v0.11.14/backlog/2026-06-26.md]] {#release-v0-11-14}
- 2026-06-26: v0.11.14 — **SemVer patch**, release-status dispatcher (신규 workflow_kit/<module> mypy strict clean 2-layer defense 실증). 신규 `workflow_kit/release_status.py` (6 helper + cmd_release_status) + dispatcher `release-status` subcommand (subcommand 35, read-only) + `__init__.py` import + `__all__` + cumulative count 35 → 36. Layer 1 + Layer 2 mypy strict defense 의 *실증 사례*. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.14-beta>.

### [[release/v0.11.13/backlog/2026-06-26.md]] {#release-v0-11-13}
- 2026-06-26: v0.11.13 — **SemVer patch**, mypy CI cross-verify (Layer 1 ↔ Layer 2 정합 advisory). `_cross_verify_ci_mypy` helper (gh run list mypy-strict.yml 조회) + `_resolve_cross_verify_verdict` (CI-only verdict + local mypy → 7 final verdict: sanity / drift_warning / ci_stale / ci_fail / no_local_verify / absent / skipped). argparse `--skip-cross-verify` / `--strict-cross-verify` flag. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.13-beta>.

### [[release/v0.11.12/backlog/2026-06-26.md]] {#release-v0-11-12}
- 2026-06-26: v0.11.12 — **SemVer patch**, mypy strict release-time gate (cmd_release pre-check 확장). `cmd_validate` 5번째 source `mypy` 추가 (REPO_ROOT.parent cwd + 절대경로, sub-package config merge 회피). argparse `--skip-mypy` flag. dispatcher 3 flag forwarding (--skip-mypy / --full-auto / --allow-existing-tag, in-scope fix: v0.7.21~v0.9.1 사이의 latent bug 9 release 동안 no-op). release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.12-beta>.

### [[release/v0.11.11/backlog/2026-06-26.md]] {#release-v0-11-11}
- 2026-06-26: v0.11.11 — **SemVer patch**, mypy strict CI 통합 (GH Actions mypy-strict workflow). `.github/workflows/mypy-strict.yml` 신규 (push to main + PR to main + workflow_dispatch). invocation = `mypy --no-incremental workflow-source/workflow_kit/` (REPO_ROOT cwd, 절대경로, sub-package config merge 회피). dev extra mypy pin `>=1.0` → `==2.1.0`. CI mypy-strict workflow passing. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.11-beta>.

### [[release/v0.10.3/backlog/2026-06-24.md]] {#release-v0-10-3}

### [[release/v0.11.0/backlog/2026-06-26.md]] {#release-v0-11-0}
- 2026-06-26: v0.11.0 — **SemVer minor**, Phase 12 의 *R-A follow-up cycle 3* (two-step CoT ingest). v0.9.2 spec §4.3 / §10 R-A follow-up table 의 cycle 3 정공법. **4 deliverable**: TASK-V1110-001 `workflow_kit.common.purpose_ingest` helper (5 함수 + 5 dataclass) + TASK-V1110-002 3 skill context load 통합 + TASK-V1110-003 `cmd_ingest_purpose` dispatcher subcommand (subcommand 33, destructive 정공법 memory #5) + TASK-V1110-004 acceptance test 6. spec layer 갱신: core/llm_wiki_concept_purpose_spec.md §4.3 cycle 3 + §5 + §6 + §10. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.0-beta>.

### [[release/v0.11.1/backlog/2026-06-26.md]] {#release-v0-11-1}
- 2026-06-26: v0.11.1 — **SemVer patch**, R-A follow-up cycle 4 (graph insights). workflow_kit.common.purpose_graph helper (6 함수 + 7 dataclass) + cmd_graph_insights dispatcher (subcommand 34, read-only) + 8 acceptance test + spec layer cycle 4 갱신. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.1-beta>.

### [[release/v0.11.2/backlog/2026-06-26.md]] {#release-v0-11-2}
- 2026-06-26: v0.11.2 — **SemVer patch**, cycle 4 deferred 통합. v0.11.1 release note 의 deferred TASK (TASK-V1111-003/004) 흡수. SessionGraphInsightsOutput + BacklogGraphInsightsOutput + DocSync dict 3 output schema extension + 3 skill context load 통합 (session-start / backlog-update / doc-sync) + 5 acceptance test. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.2-beta>.

### [[release/v0.11.3/backlog/2026-06-26.md]] {#release-v0-11-3}
- 2026-06-26: v0.11.3 — **SemVer patch**, mypy strict 누적 격상 19→21 file (cycle 3/cycle 4 의 신규 작성 module 의 strict clean 정식 인정: purpose_ingest + purpose_graph). v0.8.0 spec §5.3 정공법 정합 (1 release = 1-2 file 격상). release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.3-beta>.

### [[release/v0.11.4/backlog/2026-06-26.md]] {#release-v0-11-4}
- 2026-06-26: v0.11.4 — **SemVer patch**, mypy strict 누적 격상 21→23 file (output_contracts 6 + milestones 4 = 10 errors 해소). v0.8.0 spec §5.3 정공법 정합. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.4-beta>.

### [[release/v0.11.5/backlog/2026-06-26.md]] {#release-v0-11-5}
- 2026-06-26: v0.11.5 — **SemVer patch**, mypy strict 누적 격상 23→25 file (decorators 2 + linter 4 = 6 errors 해소). v0.8.0 spec §5.3 정공법 정합. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.5-beta>.

### [[release/v0.11.6/backlog/2026-06-26.md]] {#release-v0-11-6}
- 2026-06-26: v0.11.6 — **SemVer patch**, mypy strict 누적 격상 25→27 file (session_outputs 3 + read_only_bundle 3 = 6 errors 해소). v0.8.0 spec §5.3 정공법 정합. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.6-beta>.

### [[release/v0.11.7/backlog/2026-06-26.md]] {#release-v0-11-7}
- 2026-06-26: v0.11.7 — **SemVer patch**, mypy strict 누적 격상 27→29 file (workflow_kit_cli 4 + doc_sync 2 = 6 errors 해소). build_workflow_state_payload → purpose_context 직접 read 정공법 정합. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.7-beta>.

### [[release/v0.11.8/backlog/2026-06-26.md]] {#release-v0-11-8}
- 2026-06-26: v0.11.8 — **SemVer patch**, mypy strict 누적 격상 29→31 file (read_only_mcp_sdk 1 + workflow_writes 1 = 2 errors 해소). v0.8.0 spec §5.3 정공법 정합. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.8-beta>.

### [[release/v0.11.9/backlog/2026-06-26.md]] {#release-v0-11-9}
- 2026-06-26: v0.11.9 — **SemVer patch**, mypy strict 누적 격상 31→33 file (testing 1 + runner 1 = 2 errors 해소). `# type: ignore[import-not-found]` + `Path|None` 명시적 annotation. v0.8.0 spec §5.3 정공법 정합. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.9-beta>.

### [[release/v0.11.10/backlog/2026-06-26.md]] {#release-v0-11-10}
- 2026-06-26: v0.11.10 — **🎯 SemVer patch, FULL mypy strict 도달**. mypy strict 누적 격상 33→**35 file** (project_docs 1 + profiling 1 = 2 errors 해소). mypy workflow_kit/ exit 0 (106 source files clean). v0.8.0 spec §5.3 정공법 정합 (1 release = 1-2 file 격상). cumulative acceptance 90/90 PASS. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.11.10-beta>.
- 2026-06-24: v0.10.3 chapter 14 — **SemVer minor**, Phase 12 의 *wiki 운영 R-A follow-up cycle 2* release. v0.9.2 cycle 1 (외부 reference concept 흡수) 의 후속: **`wiki-event-sync.py` 의 3-method matching 을 `workflow_kit.common.wiki_cascade` 로 흡수** (delete 방향). source file 삭제 시 wiki page cascade-delete 대상 식별. **destructive subcommand 정공법** memory #5 정합: `apply=False` (default) dry-run + `--apply` 명시 시 실제 delete + `executed`/`skipped` list. 3-method matching (basename / stem / project-relative-stem) + macOS case-insensitive filesystem `Path.samefile()` dedup + v0.9.2 L3 raw mirror `raw/projects/<project>/` prefix 정합. Bug 발견+fix (acceptance test 작성 중): `Path(deleted_path).name` 가 이미 `.md` 포함 → 이중 .md 방지, macOS dedup `samefile()` 기반, `raw/projects/<project>/` prefix 추가. 신규 `workflow_kit.common.wiki_cascade` helper (5 함수 + 2 dataclass, ≈ 230 line): `file_to_stem` (kebab-case + lower SSOT) / `find_cascade_targets` (3-method) / `emit_cascade_plan` (다중 JSON) / `apply_cascade` (destructive) / `render_cascade_plan_text` (advisory). CLI subcommand 32 `cascade-delete` (--deleted-paths / --wiki-root / --project / --apply / --json). 7 acceptance test (`check_wiki_cascade_cleanup_v0_10_3.py`, file_to_stem SSOT / 3-method matching 3 case / graceful 부재 / 다중 plan emit / destructive apply 패턴 / text render / CLI dry-run subprocess) + v0.10.2 회귀 9/9 + v0.10.1 6/6 + v0.10.0 6/6 + v0.9.x 21/21 = **63/63 PASS**. 누적 smoke **162/162 + 63 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6 + v0.9.6 6 + v0.10.0 6 + v0.10.1 6 + v0.10.2 9 + v0.10.3 7). spec §9 acceptance **12/12 유지**. breaking change 없음 (default dry-run, v0.10.2 호환). release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.10.3-beta>.

### [[release/v0.10.2/backlog/2026-06-24.md]] {#release-v0-10-2}
- 2026-06-24: v0.10.2 chapter 13 — **SemVer minor**, Phase 12 의 *delivery layer 확장* release 의 후속. **v0.10.1 의 claude-code adapter 진입점 설계 오류 정정** (Claude Code 도 `CLAUDE.md` root 진입점 자동 read, v0.10.1 의 "slash command 만" 가설 틀림) + **3 신규 harness adapter** (aider / goose / custom) + **session-start self-bootstrap mode** (PURPOSE.md / state.json / handoff / backlog 모두 부재 시 status="warning" + self_bootstrap_suggested=True + init commands emit). `HARNESS_SPECS["claude-code"].entry_files` = `()` → `("CLAUDE.md",)` 정정 + `render_claude_code_agents` 신규. 3 신규 adapter: **aider** (`CONVENTIONS.md` root + `.aider/conventions.md` mirror + `.aider.conf.yml.example`, `commit-language: ko`), **goose** (`.goose/config.yaml` 1 file — entry_points 3종 + read_files 5종 + hooks: on_session_end + language: ko), **custom** (`.workflow-kits/custom/SKILL.md` 1 file — caller wire-up 3종: symlink / Python `with open` / YAML `workflow_skill`). `pi-dev` 는 기존 adapter 활용 (변동 ❌). 4 apply_guide 갱신/신규 (claude-code 정정 + aider / goose / custom 신규). `SessionStartOutput` schema 에 `self_bootstrap_suggested: bool` + `self_bootstrap_init_commands: list[str]` 2 field 신규. 9 acceptance test (`check_v0_10_2_delivery_layer_extension.py`, claude-code 진입점 정정 + 4 mode 조합 + 3 adapter emit verify + SUPPORTED_HARNESSES 10 정합 + session-start self-bootstrap subprocess + v0.10.0/v0.10.1 회귀) + v0.10.1 회귀 6/6 + v0.10.0 회귀 6/6 + v0.9.6 6/6 + v0.9.4 3/3 + v0.9.2 8/8 = **56/56 PASS**. 누적 smoke **162/162 + 56 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6 + v0.9.6 6 + v0.10.0 6 + v0.10.1 6 + v0.10.2 9). spec §9 acceptance **12/12 유지**. breaking change 없음. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.10.2-beta>.

### [[release/v0.10.1/backlog/2026-06-24.md]] {#release-v0-10-1}
- 2026-06-24: v0.10.1 chapter 12 — **SemVer minor**, Phase 12 의 *delivery layer 확장* release. v0.9.5 part 2 의 *contract layer / delivery layer 분리* 원칙 runtime 적용: **`--entry-mode skill-only` option** (3-mode: aggressive / safe / skill-only) + **`--harness claude-code` adapter** (1차 PoC, slash command 진입점). contract layer (universal skills) 는 harness-agnostic 유지, delivery layer (root 진입점) 만 harness-specific. Claude Code 는 *CLAUDE.md 같은 root 진입점 자동 read ❌*, *slash command* 가 진입 mechanism → 본 adapter 는 `.claude/commands/workflow-{session-start,backlog-update,doc-sync}.md` 3 slash command emit (entry_files=()). HARNESS_SPECS 6→7 + HARNESS_FILE_BUILDERS 6→7 + SUPPORTED_HARNESSES 6→7. `write_harness_files` 의 5 entry-point write block 모두 `entry_mode != "skill-only"` guard 추가 (default = aggressive, v0.10.0 호환, breaking change ❌). `harnesses/claude-code/apply_guide.md` 신규 (≈ 150 line). 6 acceptance test (`check_v0_10_1_skill_only_entry_mode.py`, --entry-mode option 3-mode / claude-code 3-way 정합 / claude-code + skill-only 3 slash command + AGENTS.md 부재 / claude-code + aggressive 동일 / codex + aggressive 기존 동작 / codex + skill-only AGENTS.md skip) + v0.10.0 회귀 6/6 + v0.9.1 contract 4/4 + v0.9.6 6/6 + v0.9.4 3/3 + v0.9.2 8/8 = **47/47 PASS**. 누적 smoke **162/162 + 47 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6 + v0.9.6 6 + v0.10.0 6 + v0.10.1 6). spec §9 acceptance **12/12 유지**. breaking change 없음. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.10.1-beta>.

### [[release/v0.10.0/backlog/2026-06-24.md]] {#release-v0-10-0}
- 2026-06-24: v0.10.0 chapter 11 — **SemVer major**, Phase 12 의 *deprecation 운영 안정화* cycle 종료. v0.9.0 (chapter 2) 의 1st cycle + v0.9.3 (chapter 7) 의 2nd cycle 가 동시에 *removal 시점* 도달. `phishing_federation_v4.py` file delete (104 line) + `workflow_kit/__init__.py` 의 import + `__all__` 에서 `phishing_federation_v4` 제거 + `DEPRECATION_MARKED_CALLABLES` whitelist empty + 2 deprecation cycle test file delete (`check_v0_9_0_deprecation_1st_cycle.py` + `check_v0_9_3_deprecation_2nd_cycle.py`, dead test cascade cleanup per memory). consumer 가 *명시적 except* 없으면 `ImportError` raise (semver major 정공법). consolidated `phishing_federation` (v0.7.52+) 은 *영향 0* — replacement module 이 이미 운영 중. 1 신규 acceptance test (`check_v0_10_0_deprecation_removal.py`, 6 test: file delete verify / `__all__` 정합 / `from workflow_kit import` ImportError / `importlib.import_module` ModuleNotFoundError / consolidated zero regression / whitelist empty) + v0.9.1 deprecation contract 갱신 (4 test, whitelist empty + `phishing_federation_v4 NOT in __all__`) + v0.9.6 regression 6/6 + v0.9.4 regression 3/3 + v0.9.2 regression 8/8 + v0.9.0~v0.9.3 deprecation cycle 회귀 4/4 = **41/41 PASS**. 누적 smoke **162/162 + 41 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6 + v0.9.6 6 + v0.10.0 6). spec `v0_9_0_deprecation_policy_spec.md` §3.3/§3.4/§3.5/§3.6 갱신 (removal column "v0.10.0 ✅" + cycle 종료 verify 항목 신규). spec §9 acceptance **12/12 유지** (deprecation 1st+2nd 종료 = spec §3.4/§3.6 cycle 종료 정합). phase 12 = **6/6 완료** (purpose.md concept 흡수 1차 + deprecation 2nd cycle 1차 + R-A follow-up 1+2+3 + deprecation 1st+2nd 종료 = 6 release 분할 cycle). release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.10.0-beta>.

### [[release/v0.9.6/backlog/2026-06-24.md]] {#release-v0-9-6}
- 2026-06-24: v0.9.6 chapter 10 — R-A follow-up part 3 (wiki-event-sync R-A trigger, R-A 3 release 분할 cycle 종료). v0.9.5 의 skill context load integration 후속으로, R-A (Purpose Refresh) 의 *trigger layer* 가 runtime 으로 추가: 30일 안 wiki log 의 ingest/query/release 분포 분석 + LLM suggest prompt (advisory, auto-commit ❌) + `last_purpose_review` date 갱신. 신규 `workflow_kit.common.purpose_refresh` helper (5 함수: `parse_log_events` / `analyze_30day_distribution` (ingest-like / query-like / release 분류 + top 10 topics + recent releases last 10) / `_read_last_purpose_review` / `update_last_purpose_review` (`re.MULTILINE` regex + 이전/현재 추적) / `generate_llm_suggest_prompt` (markdown §1 분포 + §2 본문 ≤800 char + §3 4-element advisory) + `run_purpose_refresh` unified entry) + CLI dispatcher subcommand 31 `refresh-purpose` 등록 (destructive subcommand 정공법 memory #5 정합: `apply=False` default dry-run + `--apply` 명시 시 frontmatter 갱신 + `--window-days` / `--wiki-log-path` / `--purpose-path` / `--json` flag). spec `llm_wiki_concept_purpose_spec.md` §4.4 7 detail 확장 + §5 follow-up ✅ + §6 cross-ref + §10 cycle table detail + `workflow_skill_catalog.md` §5.4 신규 + `workflow_kit_cli.py` docstring header + subcommand 표. 6 acceptance test (`check_purpose_concept_ra_trigger_v0_9_6.py`, 30일 분포 / LLM prompt / frontmatter 갱신 / dry-run / apply / graceful skip 모두 PASS) + v0.9.4 regression 3/3 + v0.9.2 regression 8/8 + v0.9.5 환경의존 3 제외 = **37/37 PASS**. 누적 smoke **162/162 + 37 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6 + v0.9.6 6). Graceful skip 정책: log.md / PURPOSE.md 부재 시 advisory warning 1줄 + no-op. LLM suggest 의 output 은 *advisory* 일 뿐, 자동 commit ❌ — 사람 review 후 `--apply` 로 명시적 갱신. spec §9 acceptance **12/12 유지** (R-A follow-up part 1 ✅ v0.9.4 + part 2 ✅ v0.9.5 + part 3 ✅ v0.9.6 = 3 release 분할 cycle 종료). release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.6-beta>.

### [[release/v0.9.0/backlog/2026-06-18.md]] {#release-v0-9-0}
- 2026-06-18: v0.9.0 chapter 1 — Deprecation Policy Operational Spec 작성 + SSOT 정합 (pyproject 0.8.1 → 0.9.1, __version__ = v0.9.1-beta) + mypy config 정합 ([tool.mypy] unknown option 5개 → [tool.workflow-doctor] section 분리) + syntax fix. commit 841329f force-push.
- 2026-06-18: v0.9.0 chapter 2 — Deprecation 1st Cycle 실제 적용 (phishing_federation_v4.fetch_federated_phishing_urls_v4 DeprecationWarning 추가 + 6 신규 test + 4 acceptance verify + zero behavior change). mypy strict 18 file baseline 유지.
- 2026-06-18: v0.9.0 chapter 3 — Spec drift patch (§4.2/§4.3/§7.1 v0.9.0-beta → v0.9.1-beta 정직하게) + Beta-v0.9.0.md release note 신규 + workflow_kit_roadmap.md Phase 11 close + Phase 12 kickoff 갱신. spec §7.5 acceptance 4/4 verify 완료.
- 2026-06-18: v0.9.0 chapter 4 — Release pipeline 실행 (git tag v0.9.0-beta push + gh release create + 3-way 정합 verify). cmd_release in-scope fix 2건: (1) argparse --dry-run flag 누락 fix (v0.7.10~v0.7.58 14 release 동안 모든 호출 fail 이었던 진짜 bug), (2) local tag create step 누락 fix. release URL: https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.0-beta.

### [[release/v0.9.5/backlog/2026-06-23.md]] {#release-v0-9-5}
- 2026-06-23: v0.9.5 chapter 9 — R-A follow-up part 2 (skill context load integration). v0.9.4 의 `state.json.purpose_digest` 1-line 자동 생성 후속으로, session-start / backlog-update / doc-sync 3종 skill 의 *context load* 시 `state.json.purpose_digest` + PURPOSE.md 본문 (≤200 token = ≤800 char) 자동 read + backlog-update 의 *in-scope check* 시 PURPOSE.md §3 Research Scope *제외 영역* 매칭 → scope creep 경고. 신규 `workflow_kit.common.purpose_context.build_purpose_context` helper (5 함수: `find_purpose_path` / `_read_state_digest_and_rev` / `read_purpose_body_excerpt` ≤800 char / `extract_research_scope` §3 포함·제외 / `check_scope_creep` hard warning = 제외 영역 substring + 첫 2 token 매칭) + 3 output schema 확장 (`SessionStartOutput.purpose_context` / `BacklogUpdateOutput.purpose_context` + `scope_creep_warnings: list[str]` / `DocSyncOutput.purpose_context`, 각각 nested `*PurposeContext` Pydantic model with 9 field) + 3 skill script 통합. spec `llm_wiki_concept_purpose_spec.md` §4.3 part 2 + §5 follow-up ✅ + §6 cross-ref + §10 cycle table detail + 3 skill spec §12/§13 신규 + `workflow_skill_catalog.md` §5.3 신규. 6 acceptance test (`check_purpose_concept_skill_context_v0_9_5.py`, 5 spec + 1 end-to-end subprocess) + v0.9.4 regression 3/3 + v0.9.2 regression 8/8 + deprecation cycle 14/14 = **31/31 PASS**. Graceful skip 정책: 3종 skill 모두 PURPOSE.md / state.json 부재 시 partial fill + `scope_warnings` advisory 1줄 (skill 실행 실패 ❌). spec §9 acceptance 11/12 → **12/12** (R-A follow-up part 1 + part 2 ✅, part 3 후속 = v0.9.6). release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.5-beta>.

### [[release/v0.9.4/backlog/2026-06-23.md]] {#release-v0-9-4}
- 2026-06-23: v0.9.4 chapter 8 — R-A follow-up part 1 (Purpose Refresh 3 release 분할의 첫 release). v0.9.2 chapter 6 의 follow-up R-A = "state.json `purpose_digest` + session-start context load + wiki-event-sync release event hook" 을 3 release 분할 (part 1 = v0.9.4, part 2 = v0.9.5, part 3 = v0.9.6). 신규 `workflow_kit.common.state.builder._parse_purpose_summary` helper (PURPOSE.md frontmatter `last_purpose_review` + §1 Goals 첫 번째 goal parse, 부재 시 graceful skip `(None, None)`) + `build_workflow_state_payload` output schema top-level 2 field 추가 (`purpose_digest`, `purpose_digest_rev`) + 3 candidate path resolution (primary: `ai-workflow/memory/active/PURPOSE.md` / parent: `../<workspace_parent>/ai-workflow/memory/active/PURPOSE.md` / fallback: `workspace_root/PURPOSE.md`). spec `llm_wiki_concept_purpose_spec.md` §4.3 part 1 + §10 (R-A follow-up cycle table 신규) + §5 follow-up checklist 갱신. 3 acceptance test (`check_purpose_concept_state_json_v0_9_4.py`) + v0.9.2 regression 8/8 + deprecation cycle 14/14 = 25/25 PASS. 1 in-scope fix 동반: `workflow_kit/__init__.py` loud fallback literal `"v0.9.4-beta-beta"` → `"v0.9.4-beta"` (suffix 중복, v0.9.3 commit 시점 spec drift 정정 — pyproject.toml 의 manual version sync 누락). spec §9 acceptance 10/12 → 11/12 (R-A follow-up part 1 ✅, part 2/3 후속). release URL: https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.4-beta.

### [[release/v0.9.3/backlog/2026-06-19.md]] {#release-v0-9-3}
- 2026-06-19: v0.9.3 chapter 7 — deprecation 2nd cycle 적용 (`phishing_federation_v4.build_default_sources_v4`). 1st cycle (v0.9.0) 운영 검증 결과: dispatcher (`cmd_federate`) 가 이미 `phishing_federation.build_default_sources` (consolidated) 사용 중 (line 255-257) → v4 module 자체가 *dead code 신호* → 2nd cycle first move 정공법. `phishing_federation_v4.build_default_sources_v4` 본문 DeprecationWarning 1-block 추가 (1st cycle 정공법 그대로: `stacklevel=2`, 3-element message `deprecated + replacement + v0.10.0 removal`). `DEPRECATION_MARKED_CALLABLES` whitelist +1 (총 2) + contract test `dict[str, tuple[str, tuple, dict]]` format 확장 (1st/2nd cycle signature 차이 흡수) + `v0_9_0_deprecation_policy_spec.md` §3.5 + §3.6 추가. 4 acceptance test (`check_v0_9_3_deprecation_2nd_cycle.py`) + 1st cycle regression 6/6 + contract test 4/4 = 14/14 PASS. 1st+2nd cycle 동시 종료 시점 = v0.10.0. release URL: https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.3-beta.

### [[release/v0.9.2/backlog/2026-06-19.md]] {#release-v0-9-2}
- 2026-06-19: v0.9.2 chapter 6 — purpose.md concept 흡수 (외부 reference 차용 정공법 1차 적용, llm_wiki Karpathy 패턴 + "Purpose.md — The Wiki's Soul" 4-element: Goals / Key Questions / Research Scope / Evolving Thesis). 신규 `ai-workflow/memory/active/PURPOSE.md` (4-element 본문 + frontmatter `purpose_version: 1` + `last_purpose_review: 2026-06-19`) + PROJECT_PROFILE.md §0 Purpose 참조 + 신규 spec `workflow-source/core/llm_wiki_concept_purpose_spec.md` (1차 출처 명시 + LICENSE 안전선: Karpathy gist + llm_wiki README GPLv3 영향 회피, 코드 직접 차용 ❌) + 8 acceptance test (4-element + LLM-readable + structural verify 모두 PASS). bundle 비율 ~75% (1차 출처와 동일 4-element 100% / LLM context read 80% follow-up R-A / suggest-update trigger 60% follow-up R-A / schema·purpose 분리 100%). follow-up R-A (Purpose Refresh) 별도 cycle 8 (state.json `purpose_digest` + session-start context load + wiki-event-sync release event hook). release URL: https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.2-beta.

### [[release/v0.9.1/backlog/2026-06-18.md]] {#release-v0-9-1}
- 2026-06-18: v0.9.1 chapter 5 — Phase 12 (운영 지능화 + deprecation 운영 안정화) 의 첫 release. 3 deliverables: (1) mypy strict workflow_kit_cli.py 49 → 0 error (register decorator Callable 명시 cascade fix + 6개 cast), cumulative 18 → 19 file clean. (2) cmd_release --full-auto flag 신규 (pre-check conflict 시 자동 --auto-bump + 1-cycle close). 2 in-scope fix 동반: cmd_rollback dispatch 누락 fix, test_release_dry_run_no_dist error message acceptance 확장. (3) deprecation policy contract test 신규 (check_v0_9_1_deprecation_contract.py, 4 test) — workflow_kit.__all__ 의 모든 public symbol 의 deprecation-free/deprecation-marked contract 자동 verify. release URL: https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.1-beta.

### [[release/v0.7.59/backlog/2026-06-17.md]] {#release-v0-7-59}
- 2026-06-17: v0.7.59 1개 TASK (cmd_consumer_metrics in-process refactor — subprocess → import_module, v0.7.56+ score-wiki-trend 정공법)

### [[release/v0.8.15/backlog/2026-06-17.md]] {#release-v0-8-15}
- 2026-06-17: v0.8.15 1개 TASK (release-dist 1-command + housekeeping — spec §9 #7 release-dist 1-command + #11 tools test ≥ 7 PASS + .gitignore history + work_backlog stale 정리)

### [[release/v0.8.14/backlog/2026-06-17.md]] {#release-v0-8-14}
- 2026-06-17: v0.8.14 1개 TASK (mypy strict 단계적 격상 10단계 — common/contracts/baselines.py 27 error → 0 + 2 real bug fix: AuditLogEvent → StageCompletion, append_audit_log arg 순서)

### [[release/v0.8.13/backlog/2026-06-17.md]] {#release-v0-8-13}
- 2026-06-17: v0.8.13 1개 TASK (mypy strict 단계적 격상 9단계 — common/state/builder.py 13 error → 0, cumulative fix 잔여분 흡수)

### [[release/v0.8.12/backlog/2026-06-17.md]] {#release-v0-8-12}
- 2026-06-17: v0.8.12 1개 TASK (GH Actions weekly cron — consumer-metrics --digest-markdown 자동화, .github/workflows/consumer-metrics-digest.yml 신규)

### [[release/v0.8.11/backlog/2026-06-17.md]] {#release-v0-8-11}
- 2026-06-17: v0.8.11 1개 TASK (phishing_keywords 2 pre-existing test fail fix — _load_external_feed lowercase + dedup + openphish mock-based verify)

### [[release/v0.8.10/backlog/2026-06-17.md]] {#release-v0-8-10}
- 2026-06-17: v0.8.10 1개 TASK (read-only MCP manifest byte-identical assertion — spec §9 #6, spec §9 8/12)

### [[release/v0.8.9/backlog/2026-06-17.md]] {#release-v0-8-9}
- 2026-06-17: v0.8.9 1개 TASK (dispatcher surface 28 → 30 — cache-lru-decay + cache-merge-csv, v0.7.58 의 3 subcommand 잔여분)

### [[release/v0.8.8/backlog/2026-06-17.md]] {#release-v0-8-8}
- 2026-06-17: v0.8.8 1개 TASK (mypy strict 단계적 격상 8단계 — upgrade_diff + bitbucket_v2 + lfu_integration + cache_size_compare 8 error → 0 + tools/release_pipeline.py SSOT refactor)

### [[release/v0.8.7/backlog/2026-06-17.md]] {#release-v0-8-7}
- 2026-06-17: v0.8.7 1개 TASK (mypy strict 단계적 격상 7단계 — v_r13_commit_diff + cache_analytics + cache_analytics_trend_chart 13 error → 0)

### [[release/v0.8.6/backlog/2026-06-17.md]] {#release-v0-8-6}
- 2026-06-17: v0.8.6 1개 TASK (mypy strict 단계적 격상 6단계 — workflow_kit_cli.py 44 error → 0, register decorator Callable 명시로 cascade untyped-ness 해소)

### [[release/v0.8.5/backlog/2026-06-17.md]] {#release-v0-8-5}
- 2026-06-17: v0.8.5 1개 TASK (mypy strict 단계적 격상 5단계 — phishing_keywords + cache_lfu_decay + cache_lfu_decay_persist 11 error → 0)

### [[release/v0.8.4/backlog/2026-06-17.md]] {#release-v0-8-4}
- 2026-06-17: v0.8.4 1개 TASK (mypy strict 단계적 격상 4단계 — phishing_federation + phishing_federation_v4 8 error → 0, _UrlRecord TypedDict 신규)

### [[release/v0.8.3/backlog/2026-06-17.md]] {#release-v0-8-3}
- 2026-06-17: v0.8.3 1개 TASK (mypy strict 단계적 격상 3단계 — workflow_kit/okf_export.py 2 error → 0)

### [[release/v0.8.2/backlog/2026-06-17.md]] {#release-v0-8-2}
- 2026-06-17: v0.8.2 1개 TASK (mypy strict 단계적 격상 2단계 — workflow_kit/okf_import.py 9 error → 0, opening docstring + → 제거 + cast(Mode) + lambda→def + e→err)

### [[release/v0.8.1/backlog/2026-06-17.md]] {#release-v0-8-1}
- 2026-06-17: v0.8.1 1개 TASK (mypy strict 단계적 격상 1단계 — workflow_kit/url_validity.py 25 error → 0, Severity='info' 확장 + EvictionStrategy + CacheEntry.timestamp real bug fix)

### [[release/v0.8.0/backlog/2026-06-17.md]] {#release-v0-8-0}
- 2026-06-17: v0.8.0 1개 TASK (Stable API frozen + mypy strict base + generated JSON Schema SSOT — pyproject.toml [project] version SSOT + __version__ 자동 derive + 21 family 85,743 bytes + __all__ 27 entry, spec §9 7/12)

### [[release/v0.7.62/backlog/2026-06-17.md]] {#release-v0-7-62}
- 2026-06-17: v0.7.62 1개 TASK (consumer-metrics trend snapshot + weekly digest — B+D 통합, 5 신규 function + 4 신규 flag, history jsonl local-only)

### [[release/v0.7.61/backlog/2026-06-17.md]] {#release-v0-7-61}
- 2026-06-17: v0.7.61 1개 TASK (mkdocs --strict 진짜 활성화 — 50+ cross-link GitHub URL rewrite + exclude_docs 4 dir + docs/README.md 삭제, 116 warnings → 0)

### [[release/v0.7.60/backlog/2026-06-17.md]] {#release-v0-7-60}
- 2026-06-17: v0.7.60 2개 TASK (5 module audit 4차 path_resolver + phishing_keywords 정합 + dispatcher 27→28 cache-lfu-decay-persist in-process)

### [[release/v0.7.58/backlog/2026-06-17.md]] {#release-v0-7-58}
- 2026-06-17: v0.7.58 1개 TASK (consumer feedback metrics — tools/consumer_metrics.py 155 line + cmd_consumer_metrics subcommand 27 + 9 smoke)

### [[release/v0.7.24/backlog/2026-06-15.md]] {#release-v0-7-24}
- 2026-06-15: v0.7.24 1개 TASK (cmd_release --notes-template flag — 5 template: default/detailed/simple/changelog/custom + 5 smoke)

### [[release/v0.7.23/backlog/2026-06-15.md]] {#release-v0-7-23}
- 2026-06-15: v0.7.23 1개 TASK (wiki 운영 cross-link 1-command wrapper — tools/wiki_emit.py 3-step cycle + 5 smoke)

### [[release/v0.7.22/backlog/2026-06-15.md]] {#release-v0-7-22}
- 2026-06-15: v0.7.22 1개 TASK (linter symlink-resolve fix — workflow_kit/common/linter.py .resolve() → .absolute() 2 site + 3 smoke)

### [[release/v0.7.21/backlog/2026-06-15.md]] {#release-v0-7-21}
- 2026-06-15: v0.7.21 1개 TASK (F-4 design 결함 fix — --allow-existing-tag flag + tag push 자동화 + 1 smoke)

### [[release/v0.7.20/backlog/2026-06-15.md]] {#release-v0-7-20}
- 2026-06-15: v0.7.20 1개 TASK (release coordination observability — auto-bump chain 최종)

### [[release/v0.7.19/backlog/2026-06-15.md]] {#release-v0-7-19}
- 2026-06-15: v0.7.19 1개 TASK (release coordination auto-bump — v0.7.18 → v0.7.19)

### [[release/v0.7.18/backlog/2026-06-15.md]] {#release-v0-7-18}
- 2026-06-15: v0.7.18 1개 TASK (release coordination observability — _check_remote_tag + next_available_version + --auto-bump + 7 smoke)

### [[release/v0.7.17/backlog/2026-06-15.md]] {#release-v0-7-17}
- 2026-06-15: v0.7.17 1개 TASK (wiki in-repo storage isolation — 5 file redirect + ai-workflow/wiki/sources/ 신규 + 11 smoke)

### [[release/v0.7.16/backlog/2026-06-15.md]] {#release-v0-7-16}
- 2026-06-15: v0.7.16 4개 TASK (config score_alert + memory_alert_mb consumer + linter excluded_paths + linter IndentationError/dict-slice fix + 9 smoke)

### [[release/v0.7.15/backlog/2026-06-15.md]] {#release-v0-7-15}
- 2026-06-15: v0.7.15 2개 TASK (atomic_write helper + changelog-gen --from-tag/--to-tag filter + 5 smoke)

### [[release/v0.7.14/backlog/2026-06-15.md]] {#release-v0-7-14}
- 2026-06-15: v0.7.14 4개 TASK (cmd_version_bump auto-sync + cmd_changelog_gen subcommand + 8 smoke + state sync)

### [[release/v0.7.13/backlog/2026-06-15.md]] {#release-v0-7-13}
- 2026-06-15: v0.7.13 3개 TASK (cmd_release --version flag + 3 smoke + version sync)

### [[release/v0.7.12/backlog/2026-06-15.md]] {#release-v0-7-12}
- 2026-06-15: v0.7.12 3개 TASK (REPO_ROOT auto-detect + 4 smoke + v0.7.5~v0.7.10 backfill)

### [[release/v0.7.11/backlog/2026-06-15.md]] {#release-v0-7-11}
- 2026-06-15: v0.7.11 5개 TASK (dist subcommand + state sync backfill + version string sync + release note + session_handoff)

### [[release/v0.7.10/backlog/2026-06-14.md]] {#release-v0-7-10}
- 2026-06-14: v0.7.10 3개 TASK (release / verify / rollback — release_pipeline Phase 2)

### [[release/v0.7.9/backlog/2026-06-14.md]] {#release-v0-7-9}
- 2026-06-14: v0.7.9 3개 TASK (validate / version-bump / note-draft — release_pipeline Phase 1)

### [[release/v0.7.8/backlog/2026-06-14.md]] {#release-v0-7-8}
- 2026-06-14: v0.7.8 2개 TASK (state-aware evaluate_compliance + config actual apply)

### [[release/v0.7.7/backlog/2026-06-14.md]] {#release-v0-7-7}
- 2026-06-14: v0.7.7 1개 TASK (workflow_kit.cli.doctor × load_config integration)

### [[release/v0.7.6/backlog/2026-06-14.md]] {#release-v0-7-6}
- 2026-06-14: v0.7.6 2개 TASK (run_all_checks 통합 runner + workflow_kit.metadata loader)

### [[release/v0.7.5/backlog/2026-06-14.md]] {#release-v0-7-5}
- 2026-06-14: v0.7.5 2개 TASK (Extension audit 4 dispatcher + refresh_wiki_memory 정식화)

### [[release/v0.7.4/backlog/2026-06-13.md]] {#release-v0-7-4}
- 2026-06-13: v0.7.4 3개 TASK (workflow doctor CLI + @graceful_shutdown + optional dep)

### [[release/v0.7.3/backlog/2026-06-13.md]] {#release-v0-7-3}
- 2026-06-13: v0.7.3 2개 TASK (4 Runtime Helper + 7 baseline dispatcher)

### [[release/v0.7.2/backlog/2026-06-13.md]] {#release-v0-7-2}
- 2026-06-13: v0.7.2 2개 TASK (Extension sub-cat lint + 4 baseline 본 구현)

### [[release/v0.7.1/backlog/2026-06-13.md]] {#release-v0-7-1}
- 2026-06-13: v0.7.1 5개 TASK (score dashboard / L2 emit / 위치 lint / drift check / follow-up 묶음)

### [[release/v0.7.0/backlog/2026-06-13.md]] {#release-v0-7-0}
- 2026-06-13: v0.7.0 7개 TASK (AIDLC Extension + Reverse Engineering + UOW + audit log + Stage Completion + Security Baseline + packaging)

### [[release/v0.5.10/backlog/2026-06-09.md]] {#release-v0-5-10}
- 2026-06-09: v0.5.10 1개 TASK (TASK-V0510-001: 개발자용 설치·사용 가이드)

### [[release/v0.5.6/backlog/2026-06-07.md]] {#release-v0-5-6}
- 2026-06-07: v0.5.6 1개 TASK (§5 출력 validator + §6.1 자동 위임 delegator)

### [[release/v0.5.5/backlog/2026-06-07.md]] {#release-v0-5-5}
- 2026-06-07: v0.5.5 1개 TASK (Phase 11 본격 pilot, contract v1 실전 검증)

### [[release/v0.5.4/backlog/2026-06-07.md]] {#release-v0-5-4}
- 2026-06-07: v0.5.4 3개 TASK (orchestrator delegation contract v1 / maturity matrix)

### [[release/v0.5.3/backlog/2026-06-07.md]] {#release-v0-5-3}
- 2026-06-07: v0.5.3 2개 TASK (antigravity MCP config 표준화 / cross-language stack)

### [[release/v0.5.2/backlog/2026-06-06.md]] {#release-v0-5-2}
- 2026-06-06: v0.5.2 3개 TASK (bootstrap 리팩터 / workflow_kit 패키지화)

### [[release/v0.5.1/backlog/2026-06-05.md]] {#release-v0-5-1}
- 2026-06-05: v0.5.1 self-dogfooding bootstrap + MCP 설치 가이드 (TASK-V051-001..006)

### Historical archives {#historical-archives}
### [[codex/phase6/backlog/2026-05-01.md]] {#codex-phase6}
- 2026-05-01: Phase 6 multi-agent delegation pilot
### [[gemini/phase10/backlog/2026-04-24.md]] {#gemini-phase10}
- 2026-04-24: Phase 10 MCP/JSON-RPC draft

## 다음에 읽을 문서

- [release/v0.5.6/session_handoff.md](../release/v0.5.6/session_handoff.md)
- [release/v0.5.6/backlog/2026-06-07.md](../release/v0.5.6/backlog/2026-06-07.md)
- [release/v0.5.5/session_handoff.md](../release/v0.5.5/session_handoff.md)
- [release/v0.5.5/backlog/2026-06-07.md](../release/v0.5.5/backlog/2026-06-07.md)
- [release/v0.5.4/session_handoff.md](../release/v0.5.4/session_handoff.md)
- [release/v0.5.4/backlog/2026-06-07.md](../release/v0.5.4/backlog/2026-06-07.md)
- [release/v0.5.3/session_handoff.md](../release/v0.5.3/session_handoff.md)
- [release/v0.5.3/backlog/2026-06-07.md](../release/v0.5.3/backlog/2026-06-07.md)
- [release/v0.5.2/session_handoff.md](../release/v0.5.2/session_handoff.md)
- [release/v0.5.2/backlog/2026-06-06.md](../release/v0.5.2/backlog/2026-06-06.md)
- [Maturity Matrix](../../workflow-source/core/maturity_matrix.json)

## v0.7.25~v0.7.32 (2026-06-15) — in-flight 8 housekeeping (v0.8.15 release note 의 housekeeping 의도 정합)

- **status**: **DONE** (2026-06-15 merged to main, 8 release / 25 commit / housekeeping by v0.8.15 commit 841329f)
- **8 release commit hash**: v0.7.25=`8a61bd3` / v0.7.26=`e5fbd2b` / v0.7.27=`2aa1efa` / v0.7.28=`b1b32f1` / v0.7.29=`850b798` / v0.7.30=`57d996d` / v0.7.31=`a9b510e` / v0.7.32=`75a8b4c`
- **정공법 (1줄)**: F-6 in-repo wiki mirror → F-7 detached HEAD short SHA → post-step sync_hash 자동화 → archive_stale_memory + cron 통합 → log rotation + metrics aggregation. v0.8.15 housekeeping 으로 in-flight 8 → 0 정리, 본 housekeeping 으로 detail block (62 line) → 1-line summary compactify.
- **detail 참조**: ai-workflow/memory/release/v0.7.25~v0.7.32/backlog/2026-06-15.md (per-release detail 파일 SSOT)

