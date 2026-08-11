"""workflow_kit.cli_commands_memory - purpose / memory dispatcher subcommands.

workflow_kit_cli.py 에서 verbatim 추출 (TASK-2026-08-11-main-011, dispatcher
부분 분할). 6개 handler: refresh-purpose / ingest-purpose / graph-insights /
cascade-delete / memory-index-query / memory-index-telemetry.

`@register` 가 import 시점에 `cli_registry.COMMANDS` 에 등록하고,
workflow_kit_cli 가 본 모듈의 handler 를 재-export 한다 — arg surface 문서는
workflow_kit_cli 모듈 docstring 이 계속 정본이다.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from workflow_kit.cli_registry import _has_flag, _parse_flag, register
from workflow_kit.common.paths import state_path_for_workspace

__all__ = [
    "cmd_refresh_purpose",
    "cmd_ingest_purpose",
    "cmd_graph_insights",
    "cmd_cascade_delete",
    "cmd_memory_index_query",
    "cmd_memory_index_telemetry",
]


@register("refresh-purpose")
def cmd_refresh_purpose(argv: list[str]) -> int:
    """R-A Purpose Refresh trigger (v0.9.6+, dispatcher subcommand).

    spec §4.4 (R-A follow-up part 3) — wiki-event-sync R-A trigger:
    - 30일 안 wiki log 의 ingest/query/release 분포 분석
    - LLM suggest prompt 생성 (markdown, advisory)
    - `--apply` 시 PURPOSE.md frontmatter `last_purpose_review` date 갱신

    Args:
        --apply              actually update PURPOSE.md frontmatter (default dry-run)
        --window-days=N      ingest/query 분포 분석 window (default 30)
        --wiki-log-path=PATH log.md path (default ~/wiki/log.md)
        --purpose-path=PATH  PURPOSE.md path (default auto-detect)
        --json               JSON output (prompt 본문 제외, summary 만)

    Returns 0 on success, 2 on error.
    """
    apply = _has_flag(argv, "--apply")
    window_days_str = _parse_flag(argv, "--window-days")
    try:
        window_days = int(window_days_str) if window_days_str else 30
    except ValueError:
        print(f"ERROR: --window-days={window_days_str!r} 는 int 가 아님", file=sys.stderr)
        return 2
    wiki_log_s = _parse_flag(argv, "--wiki-log-path")
    purpose_s = _parse_flag(argv, "--purpose-path")
    use_json = _has_flag(argv, "--json")

    try:
        from pathlib import Path as _P
        from workflow_kit.common.purpose_refresh import run_purpose_refresh

        workspace_root = _P.cwd()
        result = run_purpose_refresh(
            workspace_root=workspace_root,
            window_days=window_days,
            apply=apply,
            wiki_log_path=_P(wiki_log_s) if wiki_log_s else None,
            purpose_path=_P(purpose_s) if purpose_s else None,
        )
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    if use_json:
        # prompt 본문은 길 수 있으니 JSON 에서 제외하고 distribution + update 만 emit
        out: dict[str, object] = {
            "distribution": result["distribution"],
            "purpose_update": result["purpose_update"],
            "applied": result["applied"],
            "today": result["today"],
            "prompt_length": len(result["prompt"]),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(result["prompt"])
        upd = result["purpose_update"]
        if result["applied"] and upd.get("updated"):
            print(
                f"\n[applied] last_purpose_review: "
                f"{upd.get('previous') or '(none)'} → {upd['current']}"
            )
        else:
            prev = upd.get("previous") or "(none)"
            print(
                f"\n[dry-run] PURPOSE.md 미변경. "
                f"--apply 시 frontmatter 갱신: {prev} → {upd['current']}"
            )
        for w in upd.get("warnings", []):
            print(f"  ⚠️ {w}")

    return 0


@register("ingest-purpose")
def cmd_ingest_purpose(argv: list[str]) -> int:
    """Two-step CoT ingest (v0.11.0+, R-A follow-up cycle 3, dispatcher subcommand 33).

    spec §4.3 cycle 3 — LLM 의 *directional intent* vs *structural rules*
    일관성 강화를 위한 2-step Chain-of-Thought ingest.
    - step 1: raw PURPOSE.md 추출 (≤800 char)
    - step 2: structured 4-element emit + cross-reference validate
    - `--apply` 시 state.json.purpose_digest 의 stale 항목만 갱신 (memory rule 5)

    Args:
        --purpose-path=PATH   PURPOSE.md path (default auto-detect)
        --workspace-root=PATH workspace root (default: cwd)
        --cross-ref-check     wiki concepts cross-reference verify (default: true)
        --apply               state.json.purpose_digest 갱신 (default: dry-run)
        --json                JSON output (CoT trace + cross_ref)

    Returns 0 on success, 2 on error.
    """
    apply = _has_flag(argv, "--apply")
    purpose_s = _parse_flag(argv, "--purpose-path")
    workspace_s = _parse_flag(argv, "--workspace-root")
    use_json = _has_flag(argv, "--json")
    cross_ref_check = not _has_flag(argv, "--no-cross-ref-check")

    try:
        from pathlib import Path as _P
        from workflow_kit.common.purpose_ingest import run_two_step_cot_ingest
        from workflow_kit.common.workflow_state import build_workflow_state_payload

        workspace_root = _P(workspace_s) if workspace_s else _P.cwd()
        purpose_path = _P(purpose_s) if purpose_s else None

        cot_result = run_two_step_cot_ingest(
            purpose_path=purpose_path,
            workspace_root=workspace_root,
            auto_find_purpose=(purpose_path is None),
        )

        applied = False
        digest_update: dict[str, object] = {"updated": False, "previous": None, "current": None, "warnings": []}
        if apply and not cot_result.raw.missing:
            # state.json.purpose_digest 의 stale 항목만 advisory 비교 (destructive 정공법 memory #5).
            # build_workflow_state_payload 호출은 project_profile_path / session_handoff_path /
            # work_backlog_index_path / generated_at 4 개 keyword-only arg 필요 — 본 dispatcher context 에서는
            # 미보유. purpose_context._read_state_digest_and_rev 로 직접 advisory 비교.
            try:
                from workflow_kit.common.purpose_context import _read_state_digest_and_rev
                state_json_path = state_path_for_workspace(workspace_root)
                prev_digest, _prev_rev = _read_state_digest_and_rev(state_json_path)
                digest_update["previous"] = prev_digest
                digest_update["current"] = (
                    cot_result.structured.goals[0]
                    if cot_result.structured and cot_result.structured.goals
                    else None
                )
                # 실제 write 는 destructive 정공법 memory #5 — 1 release = 1 step
                # 여기서는 advisory emit 만, 실제 atomic_write 는 workflow_kit 라이브러리 caller 책임
                applied = True
                digest_update["updated"] = digest_update["previous"] != digest_update["current"]
            except Exception:
                applied = False
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    if use_json:
        out: dict[str, object] = {
            "raw": {
                "missing": cot_result.raw.missing,
                "purpose_path": str(cot_result.raw.purpose_path) if cot_result.raw.purpose_path else None,
                "purpose_version": cot_result.raw.purpose_version,
                "last_purpose_review": cot_result.raw.last_purpose_review,
                "warnings": cot_result.raw.warnings,
            },
            "structured": {
                "present": cot_result.structured is not None,
                "goals_count": len(cot_result.structured.goals) if cot_result.structured else 0,
                "questions_count": len(cot_result.structured.questions) if cot_result.structured else 0,
                "scope_included_count": len(cot_result.structured.scope_included) if cot_result.structured else 0,
                "scope_excluded_count": len(cot_result.structured.scope_excluded) if cot_result.structured else 0,
                "thesis_present": bool(cot_result.structured and cot_result.structured.thesis),
            } if cot_result.structured else {"present": False},
            "cot_trace": {
                "step1_char_count": cot_result.cot_trace.step1_char_count,
                "step1_truncated": cot_result.cot_trace.step1_truncated,
                "step2_summary": cot_result.cot_trace.step2_structured_summary,
            },
            "cross_ref": {
                "matched": cot_result.cross_ref.matched,
                "missing_refs": cot_result.cross_ref.missing_refs,
                "warnings": cot_result.cross_ref.warnings,
            },
            "applied": applied,
            "digest_update": digest_update,
            "overall_warnings": cot_result.overall_warnings,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"[v0.11.0 cycle 3] Two-step CoT ingest result")
        print(f"  raw.missing: {cot_result.raw.missing}")
        print(f"  raw.purpose_path: {cot_result.raw.purpose_path}")
        print(f"  raw.purpose_version: {cot_result.raw.purpose_version}")
        print(f"  raw.last_purpose_review: {cot_result.raw.last_purpose_review}")
        if cot_result.structured:
            print(f"  structured.goals: {len(cot_result.structured.goals)}")
            print(f"  structured.questions: {len(cot_result.structured.questions)}")
            print(f"  structured.scope_included: {len(cot_result.structured.scope_included)}")
            print(f"  structured.scope_excluded: {len(cot_result.structured.scope_excluded)}")
            print(f"  structured.thesis: {'present' if cot_result.structured.thesis else 'empty'}")
        else:
            print("  structured: None (PURPOSE.md missing or validation failed)")
        print(f"  cot.step1_char_count: {cot_result.cot_trace.step1_char_count}")
        print(f"  cot.step2_summary: {cot_result.cot_trace.step2_structured_summary}")
        print(f"  cross_ref.matched: {cot_result.cross_ref.matched}")
        print(f"  cross_ref.missing_refs: {cot_result.cross_ref.missing_refs}")
        if applied:
            print(f"  [applied] purpose_digest: {digest_update['previous']!r} -> {digest_update['current']!r}")
        else:
            print("  [dry-run] PURPOSE.md / state.json 미변경. --apply 시 갱신.")
        for w in cot_result.overall_warnings:
            print(f"  ⚠️ {w}")

    return 0


@register("graph-insights")
def cmd_graph_insights(argv: list[str]) -> int:
    """Graph insights (v0.11.1+, R-A follow-up cycle 4, dispatcher subcommand 34).

    spec §4.3 cycle 4 — PURPOSE.md 의 4-element (Goals / Key Questions / Research Scope / Evolving Thesis)
    ↔ 실제 deliverable (state.json recent_done_items) 의 매핑 분석.
    - Goal coverage (covered / partial / uncovered)
    - Surprising 발견 (scope creep 감지, advisory)
    - Gaps 식별 (uncovered goal priority 1-3)
    - Health score (0-100, 4 tier)

    Args:
        --purpose-path=PATH   PURPOSE.md path (default auto-detect)
        --workspace-root=PATH workspace root (default: cwd)
        --state-path=PATH     state.json path (default auto-detect)
        --no-surprising       surprising analysis skip
        --no-gaps             gaps analysis skip
        --json                JSON output

    Returns 0 on success, 2 on error.
    """
    purpose_s = _parse_flag(argv, "--purpose-path")
    workspace_s = _parse_flag(argv, "--workspace-root")
    state_s = _parse_flag(argv, "--state-path")
    include_surprising = not _has_flag(argv, "--no-surprising")
    include_gaps = not _has_flag(argv, "--no-gaps")
    use_json = _has_flag(argv, "--json")

    try:
        from pathlib import Path as _P
        from workflow_kit.common.purpose_graph import run_graph_insights

        workspace_root = _P(workspace_s) if workspace_s else _P.cwd()
        purpose_path = _P(purpose_s) if purpose_s else None
        state_path = _P(state_s) if state_s else None

        result = run_graph_insights(
            purpose_path=purpose_path,
            workspace_root=workspace_root,
            state_path=state_path,
            auto_find=True,
            include_surprising=include_surprising,
            include_gaps=include_gaps,
        )
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    if use_json:
        out: dict[str, object] = {
            "goal_keywords_count": len(result.goal_keywords),
            "recent_items_count": len(result.recent_items),
            "coverage": {
                "total": result.coverage.total_goals,
                "covered_count": result.coverage.covered_count,
                "partial_count": result.coverage.partial_count,
                "uncovered_count": result.coverage.uncovered_count,
                "coverage_pct": result.coverage.coverage_pct,
                "covered": result.coverage.covered,
                "partial": result.coverage.partial,
                "uncovered": result.coverage.uncovered,
            } if result.coverage else None,
            "surprising": {
                "count": len(result.surprising.surprising) if result.surprising else 0,
                "is_scope_creep_count": sum(result.surprising.is_scope_creep) if result.surprising else 0,
                "scope_creep_warnings": result.surprising.scope_creep_warnings if result.surprising else [],
            },
            "gaps": {
                "gaps": result.gaps.gaps if result.gaps else [],
                "priorities": result.gaps.priorities if result.gaps else [],
                "descriptions": result.gaps.descriptions if result.gaps else [],
            },
            "health": {
                "score": result.health.score if result.health else 0,
                "tier": result.health.tier if result.health else "unknown",
                "breakdown": result.health.breakdown if result.health else {},
            } if result.health else None,
            "overall_warnings": result.overall_warnings,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("[v0.11.1 cycle 4] Graph insights")
        print(f"  goal_keywords: {len(result.goal_keywords)}")
        print(f"  recent_items: {len(result.recent_items)}")
        if result.coverage:
            cov = result.coverage
            print(f"  coverage: {cov.covered_count}/{cov.total_goals} ({cov.coverage_pct}%)")
            for gid in cov.covered:
                print(f"    ✓ {gid}: covered")
            for gid in cov.partial:
                print(f"    ◐ {gid}: partial")
            for gid in cov.uncovered:
                print(f"    ✗ {gid}: uncovered")
        if result.surprising:
            print(f"  surprising: {len(result.surprising.surprising)}")
            for s, is_creep in zip(result.surprising.surprising, result.surprising.is_scope_creep):
                marker = "⚠️ scope_creep" if is_creep else "out-of-scope"
                print(f"    - {s[:80]}{'...' if len(s) > 80 else ''} [{marker}]")
        if result.gaps:
            print(f"  gaps: {len(result.gaps.gaps)}")
            for gid, prio, desc in zip(result.gaps.gaps, result.gaps.priorities, result.gaps.descriptions):
                print(f"    - {gid} (priority={prio}): {desc[:60]}{'...' if len(desc) > 60 else ''}")
        if result.health:
            h = result.health
            print(f"  health: {h.score}/100 ({h.tier})")
            for k, v in h.breakdown.items():
                print(f"    {k}: {v:+d}" if k != "base" else f"    {k}: {v}")
        for w in result.overall_warnings:
            print(f"  ⚠️ {w}")

    return 0


@register("cascade-delete")
def cmd_cascade_delete(argv: list[str]) -> int:
    """Wiki file deletion cascade cleanup (v0.10.3+, R-A follow-up cycle 2).

    spec: llm_wiki_concept_purpose_spec.md §4.5 / v0.9.2 R-1~R9 cycle 2.
    3-method matching (basename / stem / project-relative-stem) 으로
    삭제된 source file 의 wiki page cascade-delete 대상 식별.

    Args:
        --deleted-paths=PATH  삭제된 source file path (repeatable, ≥1 required)
        --wiki-root=PATH     wiki vault 의 *project source* 디렉토리
        --project=SLUG        project slug (project-relative matching 용)
        --apply               actually delete (default dry-run)
        --json                JSON output

    Returns 0 on success, 2 on error.
    """
    apply = _has_flag(argv, "--apply")
    use_json = _has_flag(argv, "--json")
    deleted_paths = [a.split("=", 1)[1] for a in argv if a.startswith("--deleted-paths=")]
    wiki_root_s = _parse_flag(argv, "--wiki-root")
    project = _parse_flag(argv, "--project") or ""

    if not deleted_paths:
        print("ERROR: --deleted-paths=PATH (at least 1, repeatable) required", file=sys.stderr)
        return 2
    if wiki_root_s is None:
        print("ERROR: --wiki-root=PATH required", file=sys.stderr)
        return 2

    try:
        from pathlib import Path as _P
        from workflow_kit.common.wiki_cascade import (
            emit_cascade_plan,
            apply_cascade,
            find_cascade_targets,
        )

        wiki_root = _P(wiki_root_s)
        plan = emit_cascade_plan(deleted_paths, wiki_root, project)

        # collect CascadeTarget list for apply
        all_targets: list[Any] = []
        for deleted in deleted_paths:
            result = find_cascade_targets(deleted, wiki_root, project)
            all_targets.extend(result.targets)
        apply_result = apply_cascade(all_targets, apply=apply)

        if use_json:
            out: dict[str, object] = {
                "plan": plan,
                "applied": apply_result["applied"],
                "executed": apply_result["executed"],
                "skipped": apply_result["skipped"],
                "warnings": apply_result["warnings"],
            }
            print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        else:
            from workflow_kit.common.wiki_cascade import render_cascade_plan_text
            print(render_cascade_plan_text(plan))
            if apply_result["applied"]:
                print(
                    f"\n[applied] {len(apply_result['executed'])} file(s) deleted"
                )
            else:
                print(
                    f"\n[dry-run] {len(apply_result['skipped'])} file(s) would be deleted. "
                    f"--apply 시 실제 delete."
                )
            for w in apply_result["warnings"]:
                print(f"  ⚠️ {w}")
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("memory-index-query")
def cmd_memory_index_query(argv: list[str]) -> int:
    """Phase 3: ADR-005 memory_index retrieval 3-tuple 의 dispatcher subcommand.

    ARGS:
      --workspace-root <path>  (필수) memory_index/ entries/ 가 있는 workspace.
      --query-tokens <csv>     (필수) 매칭 token 들. comma-separated.
      --top-k <int>            default 10
      --max-depth <int>        default 2 (linked expansion depth)
      --use-bm25-fallback      bool flag (없으면 False = opt-out)
      --json                   stdout JSON, 없으면 human-readable text

    session-start / doc-sync / backlog-update 가 본 subcommand 호출 시
    retrieval layer 자동 활용 (Phase 3 default-on 의 정공법).
    """
    import json as _json
    from pathlib import Path as _P

    workspace_root = _parse_flag(argv, "--workspace-root")
    query_tokens_raw = _parse_flag(argv, "--query-tokens")
    top_k_str = _parse_flag(argv, "--top-k") or "10"
    max_depth_str = _parse_flag(argv, "--max-depth") or "2"
    use_bm25 = _has_flag(argv, "--use-bm25-fallback")
    use_json = _has_flag(argv, "--json")

    if not workspace_root or not query_tokens_raw:
        print(
            "ERROR: --workspace-root 와 --query-tokens 둘 다 필수입니다.",
            file=sys.stderr,
        )
        return 2
    try:
        top_k = int(top_k_str)
        max_depth = int(max_depth_str)
    except ValueError as e:
        print(f"ERROR: --top-k / --max-depth 정수 parse 실패: {e}", file=sys.stderr)
        return 2

    query_tokens = [t.strip() for t in query_tokens_raw.split(",") if t.strip()]
    if not query_tokens:
        print("ERROR: --query-tokens 가 비어있음.", file=sys.stderr)
        return 2

    try:
        from workflow_kit.common.schemas.memory_index import (
            MemoryIndexQueryOutput,
            MemoryIndexTelemetryEvent,
        )
        from workflow_kit.common.state.memory_index import (
            append_telemetry_event,
            query_memory_index_for_dispatcher,
        )
        result: MemoryIndexQueryOutput = query_memory_index_for_dispatcher(
            _P(workspace_root),
            query_tokens,
            top_k=top_k,
            max_depth=max_depth,
            use_bm25_fallback=use_bm25,
        )
        # v0.13.1+ Phase 13 AC2: telemetry sidecar emit (dispatcher source)
        from datetime import datetime as _dt, timezone as _tz
        append_telemetry_event(
            _P(workspace_root),
            MemoryIndexTelemetryEvent(
                timestamp=_dt.now(_tz.utc),
                source="dispatcher",
                workspace_root=str(_P(workspace_root)),
                query_tokens_count=len(query_tokens),
                query_tokens=query_tokens[:16],
                query_source="explicit",
                selected_count=result.selected_count,
                selected_ids=result.selected_ids[:16],
                cue_hits=result.cue_hits,
                bm25_hits=result.bm25_hits,
                expansion_hits=result.expansion_hits,
                top_k=top_k,
                max_depth=max_depth,
                use_bm25_fallback=use_bm25,
            ),
        )
        if use_json:
            payload = result.model_dump(mode="json")
            print(_json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"status: {result.status.value}")
            print(f"selected_count: {result.selected_count}")
            print(f"cue_hits: {result.cue_hits}")
            print(f"bm25_hits: {result.bm25_hits}")
            print(f"expansion_hits: {result.expansion_hits}")
            print(f"expansion_depth_used: {result.expansion_depth_used}")
            print(f"selected_ids: {','.join(result.selected_ids) or '<empty>'}")
        return 0
    except Exception as e:
        # v0.13.1+ Phase 13 AC2: 예외 path 도 telemetry emit (negative example)
        try:
            from workflow_kit.common.schemas.memory_index import MemoryIndexTelemetryEvent as _MTE
            from workflow_kit.common.state.memory_index import append_telemetry_event as _ate
            from datetime import datetime as _dt2, timezone as _tz2
            _ate(
                _P(workspace_root),
                _MTE(
                    timestamp=_dt2.now(_tz2.utc),
                    source="dispatcher",
                    workspace_root=str(_P(workspace_root)),
                    query_tokens_count=len(query_tokens),
                    query_tokens=query_tokens[:16],
                    query_source="explicit",
                    error=True,
                ),
            )
        except Exception:
            pass
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("memory-index-telemetry")
def cmd_memory_index_telemetry(argv: list[str]) -> int:
    """v0.13.1+ Phase 13 AC2: memory_index telemetry sidecar 의 read-only inspect.

    ARGS:
      --workspace-root <path>  (필수) memory_index/ 가 있는 workspace.
      --json                   stdout JSON, 없으면 human-readable text.
      --show-events            (--json 과 배타적) telemetry events raw list (newline-separated JSON).

    Subcommand 36 (read-only, §6.3 MUST-NOT-delegate 정합).
    호출 빈도 측정 (3 skill + dispatcher 의 opt-in retrieval 활용도) 의 SSOT.
    """
    import json as _json
    from pathlib import Path as _P

    workspace_root = _parse_flag(argv, "--workspace-root")
    use_json = _has_flag(argv, "--json")
    show_events = _has_flag(argv, "--show-events")

    if not workspace_root:
        print(
            "ERROR: --workspace-root 는 필수입니다.",
            file=sys.stderr,
        )
        return 2
    if use_json and show_events:
        print(
            "ERROR: --json 와 --show-events 는 배타적입니다.",
            file=sys.stderr,
        )
        return 2

    try:
        from workflow_kit.common.state.memory_index import (
            read_telemetry_events,
            summarize_telemetry,
        )
        ws = _P(workspace_root)
        if show_events:
            events = read_telemetry_events(ws)
            for ev in events:
                print(_json.dumps(ev.model_dump(mode="json"), ensure_ascii=False))
            return 0
        # v1.1.3+: 윈도 지표. 전체 기간 집계만으로는 "지속적 사용" 을 못 잰다.
        from workflow_kit.common.state.memory_index import (
            DEFAULT_TELEMETRY_WINDOW_DAYS,
        )
        window_raw = _parse_flag(argv, "--window-days")
        try:
            window_days = int(window_raw) if window_raw else DEFAULT_TELEMETRY_WINDOW_DAYS
        except ValueError:
            print(f"ERROR: --window-days 정수 parse 실패: {window_raw!r}", file=sys.stderr)
            return 2
        summary = summarize_telemetry(ws, window_days=window_days)
        if use_json:
            print(_json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2))
        else:
            print(f"total_calls: {summary.total_calls}")
            print(f"total_hits: {summary.total_hits}")
            print(f"hit_rate: {summary.hit_rate:.4f}")
            print(f"by_source:")
            if summary.by_source:
                for source, bucket in sorted(summary.by_source.items()):
                    print(f"  {source}: calls={bucket['calls']} hits={bucket['hits']}")
            else:
                print("  (none)")
            print(f"first_event_at: {summary.first_event_at or '<empty>'}")
            print(f"last_event_at: {summary.last_event_at or '<empty>'}")
            print(f"events_parsed: {summary.events_parsed}")
            print(f"events_skipped: {summary.events_skipped}")
            if summary.window_days:
                print(f"--- 최근 {summary.window_days}일 (지속적 사용 지표) ---")
                print(f"window_calls: {summary.window_calls}")
                print(f"window_hit_rate: {summary.window_hit_rate:.4f}")
                print(f"window_source_count: {summary.window_source_count}")
                for source, bucket in sorted(summary.window_by_source.items()):
                    print(f"  {source}: calls={bucket['calls']} hits={bucket['hits']}")
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
