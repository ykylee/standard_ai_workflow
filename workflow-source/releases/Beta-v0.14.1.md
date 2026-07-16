# Beta v0.14.1 — MCP 1st batch stable + workflow_log_rotator 정리 (2026-07-16)

> **Phase 14 close-out 의 MCP 부분.** v0.14.0 의 side-effect follow-up.
> MCP beta 4종 stable 승격 로드맵의 **1st batch** 정합. breaking change ❌.

## 1. 핵심 변경 (3 deliverable)

### 1.1 Pydantic schema 2 file 신규 (skill_beta_criteria §3.1 1st condition)

- **`workflow_kit/common/schemas/git_history_summarizer.py`** — `GitHistorySummarizerOutput` (BaseOutput 상속) + `GitHistorySummarizerCategories` (6 카테고리: feature / bug_fix / docs / refactor / test / chore / unknown) + `GIT_HISTORY_SUMMARIZER_ERROR_CODES` (4 종: missing_required_argument / git_log_fetch_failed / invalid_commit_range / git_history_summarizer_runtime_error).
- **`workflow_kit/common/schemas/smart_context_reader.py`** — `SmartContextReaderOutput` (BaseOutput 상속, 3 field: extracted_content / not_found_symbols / file_parse_info) + `SMART_CONTEXT_READER_ERROR_CODES` (4 종: missing_required_argument / file_not_found / python_parse_failed / smart_context_reader_runtime_error).

### 1.2 Smoke 5 case 정공법 (skill_beta_criteria §3.1 6th condition)

- **`tests/check_git_history_summarizer.py`** — 5 case 강화 (markdown / json / --help / pydantic validate / categories int) — 기존 2 case → 5 case 정공법 적용, **5/5 PASS**.
- **`tests/check_smart_context_reader.py`** — 기존 unittest 5 case 그대로 (test_extract_all_symbols / test_extract_specific_symbol / test_missing_symbol / test_invalid_file_extension / test_syntax_error) — **5/5 PASS**.

### 1.3 maturity_matrix mcp_tools 정합

| MCP | stage (이전) | stage (현재) | promotion_target |
|---|---|---|---|
| `git_history_summarizer` | beta | **stable** | stable_v0_14_1 |
| `smart_context_reader` | beta | **stable** | stable_v0_14_1 |
| `apply_robust_patch` | beta | beta (v0.14.2 batch) | stable_v0_14_2 |
| `workflow_log_rotator` | beta | **(deprecation batch 1 종결)** | dropped |

## 2. 검증

- 누적 smoke **260+ PASS** (회귀 ❌)
- drift_prevention 6/6 · memory_lint 4/4 · memory_freeze_lint · appendonly_memory_layout 6/6 + WARN 1 (transient, v0.15.0 에서 해소) · git_history_summarizer 5/5 · smart_context_reader 5/5 · phase15_dashboard_panels 4/4 · deprecation_cycle_v0_14_5 4/4 · refresh_maturity_v0_14_6 4/4

## 3. 일일 backlog (SSOT)

- [`ai-workflow/memory/release/v0.14.1/backlog/2026-07-16.md`](../ai-workflow/memory/release/v0.14.1/backlog/2026-07-16.md)

## 4. 다음 step

- MCP 2nd batch stable (`apply_robust_patch`) → **v0.14.2**.
- 2nd deprecation cycle 진입 (`--legacy-memory` flag) → **v0.14.5**.

---

release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.14.1-beta>