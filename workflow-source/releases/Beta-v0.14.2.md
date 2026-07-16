# Beta v0.14.2 — MCP 2nd batch stable (apply_robust_patch, 쓰기 MCP 정공법) (2026-07-16)

> **Phase 14 close-out 의 MCP 부분.** v0.14.1 의 follow-up.
> MCP beta 4종 stable 승격 로드맵의 **2nd batch**. **쓰기 MCP** 의 첫 stable.
> ADR-003 (read-only default) 와 명시 분리 — opt-in / 명시 호출 정합.
> breaking change ❌.

## 1. 핵심 변경 (3 deliverable)

### 1.1 Pydantic schema 신규 (`ApplyRobustPatchOutput`)

`workflow_kit/common/schemas/apply_robust_patch.py` (skill_beta_criteria §3.1 1st condition):

- `BaseOutput` 상속: status / tool_version / warnings 3 field 자동.
- 추가 field 7 종:
  - `file_path: str` (absolute path)
  - `message: str` (summary)
  - `patches_applied: int` (success count)
  - `patches_failed: int` (failure count)
  - `dry_run: bool` (preview mode)
  - `applied_blocks: list[AppliedPatchBlock]` (per-block detail)
  - `error / error_code / source_context: optional` (ErrorOutput envelope)
- `AppliedPatchBlock` nested: `block_index / matched / fuzzy_score / preview`.

### 1.2 `writing_bundle.py` 96 lines 확장

`workflow_kit/common/writing_bundle.py`:

- `apply_robust_patch(file_path, patches, dry_run=False)` core helper 정공법:
  - **fuzzy match**: exact match 실패 시 `difflib.SequenceMatcher` 로 partial match 시도.
  - **block-level apply**: multi-patch batch 에서 부분 성공 / 부분 실패를 분리 처리.
  - **dry-run**: 미리 적용 결과 preview 만 emit.
  - **write-target 명시**: file_path 인자가 *반드시* required — bare `apply()` 류의 destruct 동작 ❌.

### 1.3 Smoke 신규 (`tests/check_apply_robust_patch.py`)

5 case 정공법 (skill_beta_criteria §3.1 6th condition):

- case_1: exact match 적용 (success)
- case_2: fuzzy match 적용 (success)
- case_3: dry-run mode (no write)
- case_4: 부분 실패 (multi-patch batch)
- case_5: pydantic validate / output schema 정합

**5/5 PASS**.

## 2. ADR-003 정합

ADR-003 (read-only MCP default) 와의 분리:

- read-only MCP 8종 — `--mcp-bridge jsonrpc-bridge` default, *쓰기 권한 없음*.
- `apply_robust_patch` 는 **명시 호출 시에만** opt-in (destructive subcommand 정공법).
- 디폴트 dispatch path 에서는 노출 ❌ — caller 가 *explicit* file_path + patches 를 전달해야 함.

## 3. 검증

- 누적 smoke **260+ PASS** (회귀 ❌)
- drift_prevention 6/6 · memory_lint 4/4 · memory_freeze_lint · appendonly_memory_layout 6/6 + WARN 1 · git_history_summarizer 5/5 · smart_context_reader 5/5 · **apply_robust_patch 5/5** · phase15_dashboard_panels 4/4 · deprecation_cycle_v0_14_5 4/4 · refresh_maturity_v0_14_6 4/4

## 4. 일일 backlog (SSOT)

- [`ai-workflow/memory/release/v0.14.2/backlog/2026-07-16.md`](../ai-workflow/memory/release/v0.14.2/backlog/2026-07-16.md)

## 5. 다음 step

- Phase 15 dashboard Panel 6/7/8 신규 (north-star + deprecation + telemetry) → **v0.14.3**.
- 2nd deprecation cycle 진입 (`--legacy-memory` flag) → **v0.14.5**.

---

release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.14.2-beta>