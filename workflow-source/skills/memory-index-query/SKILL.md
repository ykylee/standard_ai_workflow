# Memory Index Query Skill

- 문서 목적: ADR-005 memory_index retrieval 3-tuple 의 skill 진입점과 출력을 정리한다.
- 범위: 입력/출력, 권한 경계, session-start / doc-sync / backlog-update 통합 자리.
- 대상 독자: skill caller (session-start / doc-sync / backlog-update), memory_index 사용자.
- 상태: beta (v0.11.22+ Phase 3, subcommand 36)
- 최종 수정일: 2026-07-02
- 관련 문서: `../../../docs/architecture/ADR-005-memora-inspired-memory-index.md`, `../../../workflow-source/core/workflow_skill_catalog.md`

## 1. 목적

ADR-005 memory_index 의 retrieval 3-tuple (cue exact → BM25 fallback → linked expansion) 을
session-start, doc-sync, backlog-update 의 표준 retrieval layer 로 노출한다. Phase 3 의 본
skill 은 retrieval 만 (read-only, disk 변경 없음).

## 2. 진입점

```bash
python3 scripts/run_memory_index_query.py \
  --workspace-root <ws> \
  --query-tokens <csv> \
  [--top-k 10] [--max-depth 2] [--use-bm25-fallback] [--json]
```

또는 dispatcher subcommand:

```bash
python3 -m workflow_kit.workflow_kit_cli --command memory-index-query \
  --workspace-root <ws> \
  --query-tokens <csv> \
  [--top-k 10] [--max-depth 2] [--use-bm25-fallback] [--json]
```

## 3. 입력

- `--workspace-root` (필수) — `ai-workflow/memory/active/memory_index/` 가 있는 workspace.
- `--query-tokens` (필수) — comma-separated token list. 예: `"memora,memory retrieval"`.
- `--top-k` (optional, default 10, range 1..100).
- `--max-depth` (optional, default 2, range 0..3) — linked expansion depth cap.
- `--use-bm25-fallback` (optional, default False — opt-in).
- `--json` (optional, default False) — JSON stdout vs human-readable text.

## 4. 출력

`MemoryIndexQueryOutput` (BaseOutput 자식, Pydantic):

| field | 의미 |
| --- | --- |
| `status` | `ok` / `warning` / `error` |
| `query_tokens` | echo |
| `selected_ids` | retrieval 결과 entry id list |
| `selected_count` | 위 길이 |
| `cue_hits` | 1단계 (cue anchor exact) hit 수 |
| `bm25_hits` | 2단계 (BM25 fallback) fill 수 (`use_bm25_fallback=True` 시만) |
| `expansion_hits` | 3단계 (linked expansion) unique 추가 수 |
| `expansion_depth_used` | 실제 적용된 expansion depth |
| `source_context` | workspace_root, top_k, max_depth, use_bm25_fallback 등 호출 정보 |

## 4.1 error_code (v1.1.3+, stable 승격)

실패는 **stdout 에 `ErrorOutput` JSON** 으로 나온다 (기계가 읽는 것이 stdout,
사람이 읽는 것이 stderr). `skill_beta_criteria.md` §3.1 의 "error_code 분류 최소
3종" 정합.

| error_code | 언제 |
| --- | --- |
| `invalid_query_tokens` | `--query-tokens` 가 비어 있다 (구분자만 준 경우 포함) |
| `missing_required_document` | `--workspace-root` 경로가 없다 |
| `memory_index_query_runtime_error` | retrieval 중 예외 (entries 손상 등) |

## 4.2 실행 예시

```bash
# 기본 (human-readable)
python3 workflow-source/skills/memory-index-query/scripts/run_memory_index_query.py \
    --workspace-root . --query-tokens "telemetry,memory-index"

# JSON + BM25 fallback opt-in
python3 workflow-source/skills/memory-index-query/scripts/run_memory_index_query.py \
    --workspace-root . --query-tokens "memora,retrieval" \
    --top-k 5 --max-depth 1 --use-bm25-fallback --json

# dispatcher 경유 (telemetry source = "dispatcher" 로 기록된다)
wk memory-index-query --workspace-root=. --query-tokens="telemetry,phase-13"
```

실패 예시 — `error_code` 로 종류를 구분한다:

```bash
$ ... --workspace-root /nonexistent --query-tokens t
{
  "status": "error",
  "error_code": "missing_required_document",
  ...
}
```

## 5. 권한

read-only — caller 가 `use_bm25_fallback=True` 해도 memory_index 디스크는 변경 없음.
결과는 stdout JSON or text. 후속 skill (session-start 등) 이 본 output 을 받아 workflow
layer 에 그대로 활용 가능.

## 6. 후속

- Phase 3b: session-start / doc-sync / backlog-update 의 wiring (Phase 3 본 release 는 entry + dispatcher 만 노출).
- Phase 3+: anchoring 인 `workflow_kit.common.state.memory_index.query_memory_index_for_dispatcher` 가 v0.11.23+ skill canvas 의 표준 retrieval layer 진입점.
- ADR-006 retrospective: Phase 3b wiring 완료 + 실 사용 데이터 기반.
