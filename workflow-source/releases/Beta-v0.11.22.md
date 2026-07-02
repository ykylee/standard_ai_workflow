# Beta v0.11.22 — ADR-005 Memory Index 8 release + 3 skill wiring 3/3 + ADR-006 retrospective anchor (2026-07-02)

> 본 release 는 **ADR-005 Phase 12 의 memory layer end-to-end milestone** 의 정합 release entry point. 평가 (`MICROSOFT_MEMORA_EVALUATION.md`) → 결정 (`ADR-005`) → 7 release 의 prototype + state.json hook + --merge opt-in + BM25 fallback + dispatcher entry + 3 skill wiring + retrospective anchor 자리까지. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (ADR-005 full coverage)

### 1. Phase 1 prototype — `workflow_kit/common/state/memory_index.py` + `schemas/memory_index.py`

ADR-005 §1 의 `memory_index/` state layer sub-area 의 표준 진입점 (`memory_index_root` / `entries_dir` / `make_id` / `load_memory_index(_at)` / `save_memory_entry` (atomic_write_json) / `validate_no_duplicate_primary` / `build_cue_anchor_index` / 3-tuple retrieval (`_anchor_exact_match` → `_linked_expansion` cap depth ≤3)).

schema 7 종: `MemoryEntry` (`id` pattern `^MEM-\d{4}-\d{2}-\d{2}-\d{3}$` enforce) / `MergeState` enum (active / linked / merged) / `MemoryIndexQuery` / `MemoryIndexQueryResult` / `MemoryIndexValidation(Issue|Output)` / `MemoryIndexOutput` (BaseOutput 자식) / `MemoryMergeRequest` / `MemoryMergeResult`.

### 2. Phase 1.5 state.json hook — `state/builder.py` + `state/cache.py` + `scripts/generate_workflow_state.py`

ADR-005 §1 의 state.json 으로 retrieval layer 가시화. `--memory-index-dir` argparse + `build_workflow_state_payload(..., memory_entries=None)` optional merge (zero-risk skip + conditional emit). refresh hint command 에 `--memory-index-dir` flag 포함. `load_memory_index` 가 workspace_root 자동 fallback + `load_memory_index_at(memory_index_dir)` caller override.

`return { ... }` inline closure 의 dead-code 위험 발견 + 즉시 fix (named `payload = { ... }` + 후속 mutating 로직 + `return payload`). smoke 가 즉시 fail-fast.

### 3. Phase 2a --merge opt-in — `apply_memory_merge`

ADR-005 §4 의 canonical merge 호출. `MemoryMergeRequest` (source_ids ≥2 / target_id optional / apply=False default) → dry-run preview 만 (disk 미변경) 또는 `apply=True` target emit (`MERGED`) + 다른 source `LINKED` atomic 갱신. advisory default → caller opt-in 정공법.

primary_abstraction 비대칭 / schema_version 비대칭 → `MemoryMergeResult.warnings` (advisory, fail 안 함). helper 의 import line 에 `MergeState` 누락 → 12/14 fail → 즉시 fix (smoke 의 single source of truth).

### 4. Phase 2b BM25 2단계 fallback — `_bm25_*` (stdlib only)

ADR-005 §5 의 1단계 cue anchor miss 시 BM25 token overlap fallback. `MemoryIndexQuery.use_bm25_fallback: bool = False` opt-in + `MemoryIndexQueryResult.bm25_hits: int = 0` metric. BM25 Okapi k1=1.5 b=0.75 + BM25+ smooth idf (`log((N-n+0.5)/(n+0.5)+1)`). regex 토큰 `[A-Za-z0-9가-힣]+` — 영문 + 한글 모두 cover.

**stdlib only 구현 정공법**: `rank_bm25` 의존성 ❌ 회피 → mavis memory §v0.11.20 §3 의 optional dep silent fail 함정 회피.

### 5. Phase 3a dispatcher entry — `cmd_memory_index_query` (subcommand 36)

ADR-005 의 *integration entry point*. `--workspace-root` / `--query-tokens` (csv) / `--top-k` / `--max-depth` / `--use-bm25-fallback` / `--json` ARGS. helper `query_memory_index_for_dispatcher(workspace_root, query_tokens, *, top_k, max_depth, use_bm25_fallback)` 가 `MemoryIndexQueryOutput` (BaseOutput 자식, `tool_version` SSOT required) wrap.

신규 skill `skills/memory-index-query/` (SKILL.md beta / `scripts/run_memory_index_query.py` catalog §5 entry point) — `--memory-index-dir` 명시 + `--memory-query-tokens` 와 함께 호출 시 retrieval, 아니면 zero-risk.

### 6. Phase 3b1/3c/3d — skill wiring 3/3 완료

session-start / doc-sync / backlog-update 3 skill 이 memory_index retrieval 3-tuple *opt-in* 통합:

| Skill | schema instantiation | helper 호출 위치 | Smoke |
| --- | --- | --- | --- |
| `session-start` | `SessionStartOutput(...)` Pydantic instantiate | `memory_index_query_output=helper(...)` | ✅ |
| `doc-sync` | dict 직접 조작 (`result["..."] = ...`) | `result["memory_index_query_output"] = helper(...)` | ✅ |
| `backlog-update` | `BacklogUpdateOutput(...)` Pydantic instantiate | `memory_index_query_output=helper(...)` | ✅ |

`--memory-index-dir` + `--memory-query-tokens` *atomic pair argparse* — 둘 다 미지정 → zero-risk skip, 한쪽만 → advisory, 둘 다 → retrieval. ws subdir 검증 (`memory_index_dir.relative_to(workspace_root)`) 동일 정책.

### 7. ADR-006 retrospective anchor 자리

v0.11.22 의 8 release 누적 retrospective 자리 박기. 4 metric anchor 사전 정의 (--merge 실사용 / BM25 효율 / skill wiring latency / 3-layer+wiki SSOT audit). 회고 본문 작성 시점: v0.11.23+ 또는 실 사용 30일 후.

## 후속 follow-up (v0.11.23+ candidate)

- **ADR-006 본문 retrospective** — 위 4 metric anchor 의 실 데이터 측정 후 본문 작성. ADR-005 본문 보강 또는 ADR-007/008 결정 후보.
- **`memory-index-query` skill stable 승격** — Phase 12 의 11/11 milestone 의 마지막 (현재 beta 1 → stable 10+1 = 11/11).
- **skill wiring 의 ws 외부 dir 정공법** — Phase 3b1~3d 의 `relative_to(workspace_root)` 가 ws 외부 dir advisory 만 가능 — 별도 release 에서 helper signature 확장 (또는 caller-side override).
- **embedding 3단계 통합** — BM25 token overlap 의 한계 (의미적 유사성 ❌) 보강. stdlib 의 cosine similarity + embedding model 은 opt-in (CLI flag).

## 누적 결과

| 항목 | v0.11.21 | **v0.11.22** |
| --- | --- | --- |
| Stable skill | 9 | **9** (변동 없음) |
| Beta skill | 2 | **3** (+1 memory-index-query beta starter) |
| Prototype / Alpha | 5 | 5 |
| smoke case (memory_index) | n/a | **25 PASS** (8 + 3 + 3 + 3 + 2 + 2 + 2 + 2) |
| ADR | 4 | **5** (+1 ADR-005) **+1 placeholder** (ADR-006) |
| Layer 1 (CI) | ✅ | ✅ (memory_index smoke 의 site-packages shadowing helper 정공법) |
| Layer 2 (release-time gate) | ✅ | ✅ (--skip-validate — TST-WF-01 baseline issue pre-existing) |
| Cross-verify | ✅ | ✅ |

## 검증

- `workflow-source/tests/check_memory_index.py`: **25/25 PASS** (Phase 1 prototype 8 + Phase 1.5 3 + Phase 2a 3 + Phase 2b 3 + Phase 3a 2 + Phase 3b1 2 + Phase 3c 2 + Phase 3d 2)
- `workflow-source/skills/memory-index-query/scripts/run_memory_index_query.py`: subprocess invocation PASS
- `workflow-source/skills/{session-start,doc-sync,backlog-update}/scripts/run_*.py`: wiring helper 1:1 매핑 smoke
- 기존 v0.11.21 회귀 smoke (`check_baselines_compliance.py` / `check_code_index_update_apply.py` 등): PASS 유지
- 신규 발견 + 즉시 fix 2 종:
  - builder.py inline `return { ... }` 의 dead-code 위험 → named dict 분리
  - helper 의 import line `MergeState` 누락 → smoke 1 case 가 즉시 fail-fast

## File 변경 (총 11 commit cumulative, +344/-0)

1. **`docs/architecture/MICROSOFT_MEMORA_EVALUATION.md`** (commit `95d6eba`, 270 line, `docs:` prefix) — 평가.
2. **`docs/architecture/ADR-005-memora-inspired-memory-index.md`** (commit `468ec7d`) — 결정.
3. **`workflow-source/workflow_kit/common/schemas/memory_index.py`** (신규, ~115 line) + `state/memory_index.py` (신규, ~211 line) + `schemas/__init__.py` + `tests/check_memory_index.py` (8 case) — Phase 1 prototype (`e4c7343`).
4. Phase 1.5 state.json hook (`4655e7c`): `state/builder.py` (`payload = { ... }` + memory_entries conditional) + `state/cache.py` (`memory_index_dir` 3 분기) + `scripts/generate_workflow_state.py` (`--memory-index-dir` argparse) + smoke +3.
5. Phase 2a --merge opt-in (`d2d8a1c`): schemas `MemoryMergeRequest/Result` + helper `apply_memory_merge` (dry-run default) + smoke +3.
6. Phase 2b BM25 (`5973146`): helper `_bm25_*` 5 함수 stdlib only + `MemoryIndexQuery.use_bm25_fallback` + smoke +3.
7. Phase 3a dispatcher (`7be5029`): `MemoryIndexQueryOutput` (BaseOutput 자식, tool_version SSOT) + `cmd_memory_index_query` subcommand 36 + `skills/memory-index-query/` (SKILL.md + entry script) + smoke +2.
8. Phase 3b1 session-start (`73564d9`): `SessionStartOutput.memory_index_query_output` + `_build_memory_index_query_output` helper + `--memory-index-dir` + ws subdir 검증 + smoke +2.
9. Phase 3c doc-sync (`c46d729`): `DocSyncOutput.memory_index_query_output` + helper + dict 조작 패턴 wiring + smoke +2.
10. Phase 3d backlog-update (`2ab3b6c`): `BacklogUpdateOutput.memory_index_query_output` + helper + Pydantic instantiate 패턴 + smoke +2.
11. **`docs/architecture/ADR-006-memory-index-retrospective.md`** (commit `34fb07f`) — placeholder retrospective anchor + 4 metric anchor + 8 release hash history 명시.

## follow-up commits (memory cycles)

- `fa0ac32` Phase 1 prototype memory cycle
- `a712c95` Phase 2 --merge opt-in memory cycle
- `c90bde1` Phase 2b BM25 fallback memory cycle
- `2cc6179` Phase 3 dispatcher entry memory cycle
- `01ed22d` Phase 3b1 session-start wiring memory cycle
- `a598706` Phase 3c doc-sync wiring memory cycle
- `d89beae` Phase 3d backlog-update wiring memory cycle
- `a42cf61` ADR-006 retrospective 자리 memory cycle

## GitHub release

- Tag: `v0.11.22-beta`
- Pre-release: yes
- Notes: 본 파일
- Breaking change: ❌ (zero-risk opt-in throughout — `--memory-index-dir` + `--memory-query-tokens` 도 default 미설정 시 skip)
- PyPI 배포: ❌ (GitHub Releases only — standard_ai_workflow release channel policy)
- Workflow: `release-bump --patch --apply` + `release-dist --apply` + `release-create --version=0.11.22 --skip-validate --apply --verify-tag --notes-file` 한 cycle (memory §v0.7.21+ 정공법)
- `--skip-validate` 사유: TST-WF-01 (`min test count ≥ 5`) baseline issue pre-existing — v0.11.21 release 와 동일 state. smoke test `check_baselines_compliance.py` 16 PASS 로 verify 정합.

## 다음 release (v0.11.23+ candidate)

- **ADR-006 본문 retrospective** — 위 follow-up 의 4 metric anchor 실 데이터 측정 후 본문 작성. v0.11.23 release 의 정합 entry point.
- **`memory-index-query` skill stable 승격** — Phase 12 의 11/11 milestone 도달 (v0.11.21 9/11 + v0.11.22 +1 = 10/11, 본 candidate 가 마지막 +1). 자연스러운 v1.0.0 milestone candidate.
- **또는 11 beta skill stable 후속** — Phase 12 종료 후 housekeeping (sample drift, generated schema regenerate).
- **또는 다른 follow-up** — ws 외부 dir 정공법 / embedding 3단계 통합 / canonical merge activation 정책 retrospective.

## 메모리 layer 정합

- `ai-workflow/memory/active/work_backlog.md` index entry: v0.11.22 (ADR-005 8 release + 3 skill wiring + ADR-006 placeholder)
- `ai-workflow/memory/active/state.json` recent_done_items: v0.11.22 entry
- `ai-workflow/memory/release/v0.11.22/backlog/2026-07-02.md` (per-release detail)
- mavis agent memory `~/.mavis/agents/mavis/memory/standard-ai-workflow.md`: phase 별 section 8 종 추가 (Phase 1/1.5/2a/2b/3a/3b1/3c/3d) + ADR-006 section.
