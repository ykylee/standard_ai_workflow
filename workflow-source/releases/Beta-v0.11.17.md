# Beta v0.11.17 — mypy strict cumulative 격상 + schema drift housekeeping (2026-06-30)

> Phase 12 의 *운영 안정화 + 누적 격상* release. v0.11.10 (chapter 7, FULL mypy strict 35 file clean) + v0.11.11~v0.11.16 의 mypy strict CI 통합 / cross-verify / release-status 등 patch release 의 후속 — v0.11.16 의 *workflow 종료 commit/memory 순서 정합 (32185c7, 298704f, 1333cc8 hotfix)* + *mypy strict 누적 25 error 격상 (f6b65a4 + 97795bc)* + *schema drift housekeeping (00cc83e)*. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (mypy strict 25 error 격상 + schema 2 regenerate + sample 24 갱신)

### 1. mypy strict cumulative 격상 — output_contracts 15 error (commit `f6b65a4`)

**Roadmap §8 #2 정공법 정합** — 1 release = 1 file (가장 큰 단일 파일 우선). v0.11.10 의 FULL mypy strict 도달(35 file clean) 후 residual 처리:

- **`workflow_kit/common/schemas/__init__.py` `__all__` 확장** (attr-defined 14 error 해소):
  - CreateBacklogEntryOutput / OnboardingOutput / DemoWorkflowOutput / WorkerTask / WorkerResponse / WorkflowLinterOutput / LatestBacklogOutput / CheckDocMetadataOutput / CheckDocLinksOutput / SuggestImpactedDocsOutput / CheckQuickstartStaleLinksOutput / CreateSessionHandoffDraftOutput / CreateEnvironmentRecordStubOutput / SmartContextReaderOutput
  - + 8 related attribute (BacklogUpdatePurposeCoTTrace / SessionStartPurposeCoTTrace / BacklogGraphInsightsOutput / SessionGraphInsightsOutput / ConflictPoint / ResolutionStrategy 등)
- **`workflow_kit/common/output_contracts.py:360` unused `# type: ignore[assignment]` 제거** (`defs.get(ref_name)` 의 `object | None` return type 이 `target: object` 와 정합)

### 2. mypy strict 묶음 격상 — cli/doctor + common/decorators 10 error (commit `97795bc`)

**Roadmap §8 #2 정공법 (1 release = 2 file)** 후속:

- **`cli/doctor.py` (6 error → 0)**:
  - `evaluate()` / `render_pretty()` 의 `config=None` param type → `DoctorConfig | None`
  - return type `dict` → `dict[str, Any]` (state dict `dict[str, Any] | None` 동일)
  - `from typing import Any` + `from workflow_kit.common.metadata import DoctorConfig` import 추가
  - unused `# type: ignore` 제거 (1 site)
- **`common/decorators.py` (4 error → 0)**:
  - redundant `cast(F, _wrap_with_shutdown(...))` 제거
  - redundant `cast(str, {...})` 제거
  - unused `# type: ignore[attr-defined]` 제거 (2 site, `wrapper.__wrapped__` 는 functools 표준 attr)
  - `__graceful_shutdown__` / `__deprecated__` / `return wrapper` 의 type:ignore 는 유지 (custom attr / Callable narrow)

### 3. schema drift housekeeping (commit `00cc83e`)

`f6b65a4` mypy fix 의 lint sanity 에서 발견된 *기존* schema drift 해소 (회귀 방지):

- **`examples/output_samples/*.json` 24 file 갱신**:
  - `tool_version` v0.5.10.1-beta (구) → v0.11.16-beta (현, `workflow_kit.__version__`)
  - runtime `SUCCESS_PATH_CONTRACTS` / `ERROR_PATH_CONTRACTS` 의 누락 field default null 추가 (purpose_context, purpose_cot_trace, graph_insights, self_bootstrap_suggested, self_bootstrap_init_commands, scope_creep_warnings 등 v0.9.2 ~ v0.11.2 schema 진화 누락분)
- **`schemas/output_sample_contracts.json` regenerate** — runtime `COMMON_REQUIRED_KEYS` / `SUCCESS_PATH_CONTRACTS` / `ERROR_PATH_CONTRACTS` / `field_shapes` / `error_field_shapes` 와 정합
- **`schemas/generated_output_schemas.json` regenerate** — BacklogUpdateOutput/SessionStartOutput 의 `purpose_context`, `graph_insights`, `self_bootstrap_suggested` 등 properties 추가

### 4. Hotfix 동반 (in-scope, 별도 commit 없음)

- **`workflow-source/pyproject.toml` version bump** `0.11.16` → `0.11.17` (suffix bug fix — memory #6 v0.9.4 의 "v0.9.4-beta-beta" suffix 중복 정직하게 회피, manual sync)
- **runtime `__version__` 자동 derive** = `v0.11.17-beta` (workflow_kit/__init__.py 의 `_read_pyproject_version()`)

## 누적 결과

- **mypy strict cumulative**: 35 → **38 file clean** (+3: output_contracts, cli/doctor, common/decorators)
- **mypy strict errors**: 48 → **23 errors** (-25)
- **누적 smoke**: 162/162 + 25 별도 subset (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6 + v0.9.6 6 + v0.10.0 6 + v0.10.1 6 + v0.10.2 9 + v0.10.3 7 + v0.11.0 6 + v0.11.1 8 + v0.11.2 5 + v0.11.3 2 + v0.11.4 2 + v0.11.5 2 + v0.11.6 2 + v0.11.7 2 + v0.11.8 2 + v0.11.9 2 + v0.11.10 2 + v0.11.11 1 + v0.11.12 1 + v0.11.13 2 + v0.11.14 1 + v0.11.15 2 + v0.11.16 1 + **v0.11.17 3**)
- **Spec §9 acceptance**: 12/12 유지

## 검증

- `workflow-source/tests/check_baselines_compliance.py`: 16 tests PASS
- `workflow-source/tests/check_output_samples.py`: 24 JSON files PASS
- `workflow-source/tests/check_output_json_schema.py`: PASS
- `workflow-source/tests/check_wiki_source_rule.py` (V-R9): PASS
- `workflow-source/skills/workflow-linter/scripts/run_workflow_linter.py --maturity`: status=ok, total_issues=0
- `mypy --no-incremental --strict workflow-source/workflow_kit/`: 23 errors (38 file clean)

## GitHub release

- Tag: `v0.11.17-beta`
- Pre-release: yes
- Notes: 본 파일
- Breaking change: ❌
- PyPI 배포: ❌ (GitHub Releases only)

## 다음 release (v0.11.18 candidate)

- mypy strict residual 23 errors 중 다음 묶음 격상 후보: `mcp_v1_server.py` (4) + `release_status.py` (3) + `read_only_mcp_sdk.py` (2) = 9 error (1 release = 2 file 정공법 정합)
- 또는 governance 후속 (11 beta skill stable 승격 1차 batch, roadmap §8 Phase 12 in-progress)
- 또는 다른 housekeeping

## 메모리 layer (memory → commit → push 흐름 정합)

- `ai-workflow/memory/active/work_backlog.md` index entry: v0.11.17 (cumulative)
- `ai-workflow/memory/active/state.json` recent_done_items: v0.11.17 entry
- `ai-workflow/memory/release/v0.11.17/backlog/2026-06-30.md` (per-release detail): cumulative 작업 log