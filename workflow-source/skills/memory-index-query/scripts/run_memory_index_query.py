"""memory-index-query skill 표준 entry (v0.11.22+ Phase 3).

ADR-005 memory_index retrieval 3-tuple 의 CLI 진입점. read-only (디스크 변경 ❌).
session-start / doc-sync / backlog-update 가 본 entry 만 호출하면 retrieval layer 자동 활용.

Catalog §5 의 `scripts/run_<skill>.py` 패턴 정합.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# site-packages 의 stale workflow_kit shadowing 회피 (mavis memory §v0.11.18 §1 패턴).
SOURCE_ROOT = Path(__file__).resolve().parents[3]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common.errors import build_error_result
from workflow_kit.common.state.memory_index import query_memory_index_for_dispatcher


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Memory Index Query (v0.11.22+ Phase 3, ADR-005 retrieval 3-tuple)"
    )
    parser.add_argument("--workspace-root", required=True,
                        help="memory_index/ entries/ 가 있는 workspace root")
    parser.add_argument("--query-tokens", required=True,
                        help="comma-separated token list. 예: 'memora,memory retrieval'")
    parser.add_argument("--top-k", default=10, type=int,
                        help="default 10, range 1..100")
    parser.add_argument("--max-depth", default=2, type=int,
                        help="linked expansion depth cap, default 2, range 0..3")
    parser.add_argument("--use-bm25-fallback", action="store_true",
                        help="Phase 2b: 1단계 miss 시 BM25 2단계 fallback opt-in")
    parser.add_argument("--json", action="store_true",
                        help="stdout JSON (default human-readable text)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace_root = Path(args.workspace_root)
    source_context = {
        "workspace_root": str(workspace_root),
        "top_k": args.top_k,
        "max_depth": args.max_depth,
        "use_bm25_fallback": args.use_bm25_fallback,
    }

    # v1.1.3 (stable 승격): error_code 3종. 이전에는 stderr 문자열 + rc 2 뿐이라
    # caller 가 실패 *종류* 를 구분할 수 없었다 (`skill_beta_criteria.md` §3.1 의
    # "error_code 분류 최소 3종" 미충족). 다른 stable skill 과 같은 `ErrorOutput`
    # 형태로 stdout 에 emit 한다 — 기계가 읽는 것이 stdout, 사람이 읽는 것이 stderr.
    query_tokens = [t.strip() for t in args.query_tokens.split(",") if t.strip()]
    if not query_tokens:
        result = build_error_result(
            tool_version=TOOL_VERSION,
            error="--query-tokens 가 비어 있다.",
            error_code="invalid_query_tokens",
            warnings=["comma-separated token 을 최소 1개 준다. 예: --query-tokens 'memora,retrieval'"],
            source_context=source_context,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    if not workspace_root.is_dir():
        result = build_error_result(
            tool_version=TOOL_VERSION,
            error="workspace root 를 찾을 수 없다.",
            error_code="missing_required_document",
            warnings=[f"`--workspace-root` 경로를 다시 확인해야 한다: {workspace_root}"],
            source_context=source_context | {"missing_path": str(workspace_root)},
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    try:
        result_obj = query_memory_index_for_dispatcher(
            workspace_root,
            query_tokens,
            top_k=args.top_k,
            max_depth=args.max_depth,
            use_bm25_fallback=args.use_bm25_fallback,
        )
    except Exception as e:  # noqa: BLE001 — 어떤 실패든 기계가 읽을 수 있게 내보낸다
        result = build_error_result(
            tool_version=TOOL_VERSION,
            error=f"{type(e).__name__}: {e}",
            error_code="memory_index_query_runtime_error",
            warnings=["memory_index/ entries 가 손상됐는지 확인한다."],
            source_context=source_context | {"query_tokens": query_tokens},
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    result = result_obj

    if args.json:
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        print(f"status: {result.status.value}")
        print(f"selected_count: {result.selected_count}")
        print(f"cue_hits: {result.cue_hits}")
        print(f"bm25_hits: {result.bm25_hits}")
        print(f"expansion_hits: {result.expansion_hits}")
        print(f"expansion_depth_used: {result.expansion_depth_used}")
        print(f"selected_ids: {','.join(result.selected_ids) or '<empty>'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
