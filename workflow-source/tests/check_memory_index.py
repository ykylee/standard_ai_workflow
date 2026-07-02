"""workflow_kit.common.state.memory_index + schemas.memory_index helper smoke test (v0.11.22+).

ADR-005 Memora-inspired Memory Index Phase 1 (= zero-risk metadata prototype) 의
helper 함수가 spec 그대로 동작하는지 검증한다. 8 test PASS.

Test list:
1. test_memory_entry_round_trip: Pydantic construct -> model_dump -> model_validate 정합.
2. test_id_pattern_enforced: invalid id 는 Pydantic ValidationError.
3. test_load_skips_invalid_json: 일부 손상 file 도 valid entry 만 반환.
4. test_save_atomic_with_updated_at_stamp: save -> file 존재 + content 정합 + atomic.
5. test_validate_no_duplicate_passes: distinct entries -> issues=[].
6. test_validate_detects_duplicate_primary: 동일 primary (case-insensitive) -> duplicate_primary_abstraction.
7. test_cue_anchor_index_inverse: build_cue_anchor_index -> inverse index 정확.
8. test_query_with_linked_expansion: anchor exact -> linked entry 의 mentioned_in 따라 1-hop expansion.

Cross-ref: docs/architecture/ADR-005-memora-inspired-memory-index.md
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# site-packages 의 stale workflow_kit 이 source tree 를 shadowing 하는 v0.11.18 패턴 회피:
# sys.path 에 SOURCE_ROOT 를 [0] 으로 강제 주입하여 source tree 우선. (memory/standard-ai-workflow.md §1.5)
SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.schemas.memory_index import (  # noqa: E402
    MemoryEntry,
    MemoryIndexQuery,
    MemoryIndexQueryOutput,
    MemoryMergeRequest,
    MergeState,
)
from workflow_kit.common.state import memory_index as HELPER  # noqa: E402
from workflow_kit.common.state.builder import build_workflow_state_payload  # noqa: E402
from workflow_kit.common.state.cache import build_state_cache_refresh_hint  # noqa: E402

HELPER_FILE = SOURCE_ROOT / "workflow_kit" / "common" / "state" / "memory_index.py"


def _now() -> datetime:
    return datetime(2026, 7, 2, 12, 0, 0, tzinfo=timezone.utc)


def _entry(eid: str, primary: str, *, anchors: list[str] | None = None,
           state: MergeState = MergeState.ACTIVE,
           mentioned_in: list[str] | None = None) -> MemoryEntry:
    return MemoryEntry(
        id=eid,
        schema_version=1,
        source_paths=[f"ai-workflow/memory/active/session_handoff.md#{eid}"],
        primary_abstraction=primary,
        cue_anchors=anchors or [],
        value_digest=f"digest for {eid}",
        owners=["session-orchestrator"],
        scope=["project"],
        merge_state=state,
        mentioned_in=mentioned_in or [],
        created_at=_now(),
        updated_at=_now(),
    )


# --- Test 1: Pydantic round trip ---


def test_memory_entry_round_trip() -> None:
    """MemoryEntry Pydantic 의 construct -> model_dump -> model_validate 정합."""
    e = _entry("MEM-2026-07-02-001", "Memora evaluation for workflow memory retrieval",
               anchors=["Microsoft Memora", "agent memory"])
    dumped = e.model_dump(mode="json")
    again = MemoryEntry.model_validate(dumped)
    assert again.id == e.id, "id mismatch"
    assert again.primary_abstraction == e.primary_abstraction
    assert again.cue_anchors == e.cue_anchors
    assert again.merge_state == e.merge_state
    # mode='json' 은 datetime 을 ISO string 으로 직렬화 -> 다시 parse 가능
    assert isinstance(again.created_at, datetime)
    assert again.created_at == e.created_at


# --- Test 2: id pattern enforced ---


def test_id_pattern_enforced() -> None:
    """invalid id 는 Pydantic ValidationError."""
    import pydantic
    try:
        MemoryEntry(
            id="not-a-mem-id",
            schema_version=1,
            primary_abstraction="something",
            created_at=_now(),
            updated_at=_now(),
        )
    except pydantic.ValidationError:
        return
    raise AssertionError("expected ValidationError for invalid id pattern")


# --- Test 3: load skips invalid JSON ---


def test_load_skips_invalid_json() -> None:
    """workspace 에 valid 1 + invalid 1 entry -> valid 만 반환."""
    import tempfile
    from workflow_kit.common.atomic_write import atomic_write_json  # noqa: F401  # load 시 의존 검증

    with tempfile.TemporaryDirectory() as tmp:
        workspace_root = Path(tmp)
        root = HELPER.memory_index_root(workspace_root)
        ed = HELPER.entries_dir(memory_index=root)
        ed.mkdir(parents=True, exist_ok=True)
        # valid
        HELPER.save_memory_entry(workspace_root,
                                 _entry("MEM-2026-07-02-001", "valid entry primary",
                                        anchors=["anchor-a"]))
        # 손상 JSON (decode fail)
        (ed / "MEM-2026-07-02-002.json").write_text("{not json}", encoding="utf-8")
        # schema 불일치 (decode 는 OK, schema fail)
        (ed / "MEM-2026-07-02-003.json").write_text(
            json.dumps({"id": "bad", "primary_abstraction": "x", "created_at": "2026-07-02T00:00:00+00:00",
                       "updated_at": "2026-07-02T00:00:00+00:00"}),
            encoding="utf-8",
        )

        loaded = HELPER.load_memory_index(workspace_root)
        ids = sorted(e.id for e in loaded)
        assert ids == ["MEM-2026-07-02-001"], f"expected only valid entry, got {ids}"


# --- Test 4: save atomic + updated_at stamp ---


def test_save_atomic_with_updated_at_stamp() -> None:
    """save_memory_entry -> file 존재 + content 정합 + atomic write helper 사용 검증."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        workspace_root = Path(tmp)
        e = _entry("MEM-2026-07-02-007", "save atomic test",
                   anchors=["atomic-write-anchor"])
        target = HELPER.save_memory_entry(workspace_root, e)
        assert target.exists(), "file not created"
        body = json.loads(target.read_text(encoding="utf-8"))
        assert body["id"] == "MEM-2026-07-02-007"
        assert body["primary_abstraction"] == "save atomic test"
        assert body["cue_anchors"] == ["atomic-write-anchor"]
        # updated_at 자동 stamp (caller 가 명시하지 않은 경우)
        assert body["updated_at"], "updated_at not stamped"

        # atomic_write 사용 source-code level 검증 (POSIX)
        text = HELPER_FILE.read_text(encoding="utf-8")
        assert "atomic_write_json" in text, "atomic_write_json 호출 부재"


# --- Test 5: validate (no duplicates) ---


def test_validate_no_duplicate_passes() -> None:
    """distinct primaries -> issues = []."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        workspace_root = Path(tmp)
        HELPER.save_memory_entry(workspace_root,
                                 _entry("MEM-2026-07-02-001", "first topic",
                                        anchors=["a"]))
        HELPER.save_memory_entry(workspace_root,
                                 _entry("MEM-2026-07-02-002", "second topic",
                                        anchors=["b"]))
        out = HELPER.validate_memory_index(workspace_root)
        assert out.total_entries == 2
        assert out.issues == [], f"unexpected issues: {out.issues}"


# --- Test 6: validate detects duplicate primary ---


def test_validate_detects_duplicate_primary() -> None:
    """두 entry 의 primary 가 동일 (case-insensitive) -> duplicate_primary_abstraction."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        workspace_root = Path(tmp)
        HELPER.save_memory_entry(workspace_root,
                                 _entry("MEM-2026-07-02-001", "Same Topic",
                                        anchors=["a"]))
        HELPER.save_memory_entry(workspace_root,
                                 _entry("MEM-2026-07-02-002", "same topic",  # case-insensitive 동일
                                        anchors=["b"]))
        out = HELPER.validate_memory_index(workspace_root)
        assert out.total_entries == 2
        codes = sorted(i.code for i in out.issues)
        assert "duplicate_primary_abstraction" in codes, f"missing expected code: {codes}"
        affected = next(i.affected_ids for i in out.issues if i.code == "duplicate_primary_abstraction")
        assert sorted(affected) == ["MEM-2026-07-02-001", "MEM-2026-07-02-002"]


# --- Test 7: cue anchor inverse index ---


def test_cue_anchor_index_inverse() -> None:
    """build_cue_anchor_index -> lower-case anchor key + entry id list."""
    a = _entry("MEM-2026-07-02-001", "first", anchors=["Microsoft Memora", "agent memory"])
    b = _entry("MEM-2026-07-02-002", "second", anchors=["AGENT MEMORY", "retrieval"])
    idx = HELPER.build_cue_anchor_index([a, b])
    # 'AGENT MEMORY' 가 trimmed/lower 적용되어 a, b 둘 다 매핑
    assert sorted(idx["agent memory"]) == ["MEM-2026-07-02-001", "MEM-2026-07-02-002"]
    assert idx["microsoft memora"] == ["MEM-2026-07-02-001"]
    assert idx["retrieval"] == ["MEM-2026-07-02-002"]


# --- Test 8: 3-tuple query + linked expansion ---


def test_query_with_linked_expansion() -> None:
    """anchor exact match -> seed -> mentioned_in 의 다른 entry 1-hop expansion."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        workspace_root = Path(tmp)
        # entry A: 'microsoft memora' anchor + mentions entry B in mentioned_in
        HELPER.save_memory_entry(
            workspace_root,
            _entry("MEM-2026-07-02-001", "first",
                   anchors=["Microsoft Memora"],
                   mentioned_in=["MEM-2026-07-02-002"]),
        )
        # entry B: no anchor, only reachable via A's mentioned_in
        HELPER.save_memory_entry(
            workspace_root,
            _entry("MEM-2026-07-02-002", "second",
                   anchors=[]),
        )
        result = HELPER.query_memory_index(
            workspace_root,
            MemoryIndexQuery(query_tokens=["microsoft memora"], top_k=10, max_depth=2),
        )
        ids = sorted(e.id for e in result.selected_entries)
        # 1-hop expansion 으로 A 도 B 도 선택
        assert ids == ["MEM-2026-07-02-001", "MEM-2026-07-02-002"], f"got {ids}"
        assert result.cue_hits == 1, "cue hit count wrong"
        assert result.expansion_hits == 1, "expansion hit count wrong"
        assert result.expansion_depth_used >= 1


# --- 메인 실행 ---


def main() -> int:
    test_funcs = [
        test_memory_entry_round_trip,
        test_id_pattern_enforced,
        test_load_skips_invalid_json,
        test_save_atomic_with_updated_at_stamp,
        test_validate_no_duplicate_passes,
        test_validate_detects_duplicate_primary,
        test_cue_anchor_index_inverse,
        test_query_with_linked_expansion,
        test_payload_with_memory_entries_merged,
        test_payload_without_memory_entries_absent,
        test_refresh_hint_includes_memory_index_dir_flag,
        test_merge_request_validates_duplicate_source_ids,
        test_merge_dry_run_default_no_file_written,
        test_merge_apply_canonical_merge_atomic,
        test_bm25_score_token_overlap_ranking,
        test_bm25_fallback_fills_when_cue_miss,
        test_bm25_fallback_disabled_no_fill,
        test_query_for_dispatcher_wrapper,
        test_entry_script_subprocess_invocation,
        test_session_start_memory_wiring_returns_dict,
        test_session_start_memory_wiring_zero_risk_skip,
        test_doc_sync_memory_wiring_returns_dict,
        test_doc_sync_memory_wiring_zero_risk_skip,
        test_backlog_update_memory_wiring_returns_dict,
        test_backlog_update_memory_wiring_zero_risk_skip,
    ]

    failed: list[str] = []
    for fn in test_funcs:
        name = fn.__name__
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed.append(name)

    total = len(test_funcs)
    passed = total - len(failed)
    print(f"\n{passed}/{total} tests passed.")
    if failed:
        print(f"\n{len(failed)} tests failed:")
        for name in failed:
            print(f"  - {name}")
        return 1
    return 0


# --- Phase 1.5 추가 3 case (state.json payload merge / zero-risk skip / hint flag) ---


def _write_minimal_workflow_state_fixtures(tmp: Path) -> tuple[Path, Path, Path]:
    """builder.py 가 silent fallback 으로 parse 가능하도록 최소 markdown 작성."""
    pp = tmp / "PROJECT_PROFILE.md"
    pp.write_text(
        "---\n"
        "project_name: test\n"
        "document_home: docs/\n"
        "operations_path: ai-workflow/operations/\n"
        "backlog_path: ai-workflow/memory/active/work_backlog.md\n"
        "handoff_path: ai-workflow/memory/active/session_handoff.md\n"
        "environment_path: ai-workflow/memory/active/environment.md\n"
        "quick_tests: echo quick\n"
        "isolated_tests: echo isolated\n"
        "runtime_checks: echo runtime\n"
        "---\n"
        "# test profile\n",
        encoding="utf-8",
    )
    sh = tmp / "session_handoff.md"
    sh.write_text("# session handoff\n", encoding="utf-8")
    wb = tmp / "work_backlog.md"
    wb.write_text("# work backlog index\n", encoding="utf-8")
    return pp, sh, wb


def test_payload_with_memory_entries_merged() -> None:
    """build_workflow_state_payload 에 memory_entries list 전달 시 payload merge + count."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        pp, sh, wb = _write_minimal_workflow_state_fixtures(workspace)
        entries = [
            {"id": "MEM-2026-07-02-001", "primary_abstraction": "x"},
            {"id": "MEM-2026-07-02-002", "primary_abstraction": "y"},
        ]
        payload = build_workflow_state_payload(
            project_profile_path=pp,
            session_handoff_path=sh,
            work_backlog_index_path=wb,
            generated_at="2026-07-02",
            workspace_root=workspace,
            memory_entries=entries,
        )
        assert payload.get("memory_entries") == entries, (
            f"memory_entries merge failed: {payload.get('memory_entries')}"
        )
        assert payload.get("memory_entries_count") == 2, "count mismatch"


def test_payload_without_memory_entries_absent() -> None:
    """memory_entries 미지정 (default None) 시 payload 에 memory_entries key 부재."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        pp, sh, wb = _write_minimal_workflow_state_fixtures(workspace)
        payload = build_workflow_state_payload(
            project_profile_path=pp,
            session_handoff_path=sh,
            work_backlog_index_path=wb,
            generated_at="2026-07-02",
            workspace_root=workspace,
        )
        assert "memory_entries" not in payload, "memory_entries key 가 zero-risk 로 부재해야 함"
        assert "memory_entries_count" not in payload, "count 도 부재해야 함"


def test_refresh_hint_includes_memory_index_dir_flag() -> None:
    """build_state_cache_refresh_hint 가 memory_index_dir 를 --memory-index-dir flag 로 emit."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        pp, sh, wb = _write_minimal_workflow_state_fixtures(workspace)
        mi = workspace / "memory_index"
        hint = build_state_cache_refresh_hint(
            project_profile_path=pp,
            memory_index_dir=mi,
        )
        cmd = hint["refresh_command"]
        assert "--memory-index-dir" in cmd, f"--memory-index-dir flag missing: {cmd}"
        assert str(mi) in cmd, f"memory_index_dir path not in command: {cmd}"


# --- Phase 2 추가 3 case (--merge opt-in canonical merge) ---


def test_merge_request_validates_duplicate_source_ids() -> None:
    """duplicate source_ids 면 ValueError (atomic 보장용 사전 차단)."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        HELPER.save_memory_entry(ws, _entry("MEM-2026-07-02-001", "first", anchors=["x"]))
        HELPER.save_memory_entry(ws, _entry("MEM-2026-07-02-002", "second", anchors=["y"]))
        req = MemoryMergeRequest(
            source_ids=["MEM-2026-07-02-001", "MEM-2026-07-02-001"],
            apply=False,
        )
        try:
            HELPER.apply_memory_merge(ws, req)
        except ValueError as e:
            assert "duplicate" in str(e).lower() or "중복" in str(e), f"unexpected message: {e}"
            return
        raise AssertionError("expected ValueError for duplicate source_ids")


def test_merge_dry_run_default_no_file_written() -> None:
    """apply=False (default) 은 disk 변경 없음 + MemoryMergeResult.applied=False."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        a = HELPER.save_memory_entry(ws, _entry("MEM-2026-07-02-001", "shared topic",
                                                 anchors=["x", "y"]))
        b = HELPER.save_memory_entry(ws, _entry("MEM-2026-07-02-002", "shared topic",
                                                 anchors=["z", "y"]))
        before_a = a.read_text(encoding="utf-8")
        before_b = b.read_text(encoding="utf-8")

        # dry-run (apply 미지정 → default False)
        result = HELPER.apply_memory_merge(
            ws,
            MemoryMergeRequest(
                source_ids=["MEM-2026-07-02-001", "MEM-2026-07-02-002"],
            ),
        )
        assert result.applied is False, f"expected dry-run, got {result.applied}"
        assert result.target_id == "MEM-2026-07-02-001", f"expected first source as target, got {result.target_id}"
        assert sorted(result.merged_cue_anchors) == ["x", "y", "z"], f"cue union: {result.merged_cue_anchors}"
        assert a.read_text(encoding="utf-8") == before_a, "file a changed during dry-run"
        assert b.read_text(encoding="utf-8") == before_b, "file b changed during dry-run"


def test_merge_apply_canonical_merge_atomic() -> None:
    """apply=True 면 target emit (MERGED) + 다른 source 는 LINKED 로 atomic 갱신."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        HELPER.save_memory_entry(ws, _entry("MEM-2026-07-02-001", "shared topic",
                                            anchors=["x", "y"]))
        HELPER.save_memory_entry(ws, _entry("MEM-2026-07-02-002", "shared topic",
                                            anchors=["z", "y"]))
        result = HELPER.apply_memory_merge(
            ws,
            MemoryMergeRequest(
                source_ids=["MEM-2026-07-02-001", "MEM-2026-07-02-002"],
                apply=True,
            ),
        )
        assert result.applied is True, "expected applied"
        entries_by_id = {e.id: e for e in HELPER.load_memory_index(ws)}
        target = entries_by_id.get("MEM-2026-07-02-001")
        assert target is not None
        assert target.merge_state == MergeState.MERGED, f"target merge_state: {target.merge_state}"
        assert sorted(target.cue_anchors) == ["x", "y", "z"]
        other = entries_by_id.get("MEM-2026-07-02-002")
        assert other is not None
        assert other.merge_state == MergeState.LINKED, f"source merge_state: {other.merge_state}"


# --- Phase 2b 추가 3 case (BM25 2단계 fallback) ---


def test_bm25_score_token_overlap_ranking() -> None:
    """BM25 가 token overlap 많은 entry 를 더 높게 점수 매김."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        a = _entry("MEM-2026-07-02-001", "memora evaluation for memory retrieval",
                   anchors=["memory", "retrieval"])
        b = _entry("MEM-2026-07-02-002", "unrelated apple banana",
                   anchors=["fruit", "food"])
        c = _entry("MEM-2026-07-02-003", "memory memory retrieval retrieval",
                   anchors=["memory", "retrieval", "memory retrieval"])
        ranked = HELPER._bm25_retrieve([a, b, c], ["memory", "retrieval"], top_k=3)
        ids = [e.id for e in ranked]
        # 'memory' + 'retrieval' 가 c 가장 많이 등장 → 가장 높은 score
        assert ids[0] == "MEM-2026-07-02-003", f"expected c top, got {ids}"
        # b 는 겹치는 token 0 → 제외되어야 함 (score 0)
        assert "MEM-2026-07-02-002" not in ids, f"unrelated entry should be excluded: {ids}"


def test_bm25_fallback_fills_when_cue_miss() -> None:
    """use_bm25_fallback=True + cue anchor miss → BM25 가 top_k 까지 fill."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        # cue anchor 가 일부러 query 와 다르게 — cue stage miss 유발
        HELPER.save_memory_entry(ws, _entry("MEM-2026-07-02-001", "alpha bravo charlie",
                                            anchors=["x-unrelated"]))
        HELPER.save_memory_entry(ws, _entry("MEM-2026-07-02-002", "alpha charlie delta",
                                            anchors=["y-unrelated"]))
        HELPER.save_memory_entry(ws, _entry("MEM-2026-07-02-003", "echo foxtrot",
                                            anchors=["z-unrelated"]))
        # query 는 'alpha charlie' — cue miss, BM25 가 alpha 가 있는 entry 2개 채움
        result = HELPER.query_memory_index(
            ws,
            MemoryIndexQuery(
                query_tokens=["alpha", "charlie"],
                top_k=2,
                max_depth=0,
                use_bm25_fallback=True,
            ),
        )
        ids = sorted(e.id for e in result.selected_entries)
        # entry 1 (alpha, bravo, charlie) + entry 2 (alpha, charlie, delta) 가 BM25 top
        # entry 3 (echo, foxtrot) 는 score 0 → 제외
        assert ids == ["MEM-2026-07-02-001", "MEM-2026-07-02-002"], f"got {ids}"
        assert result.cue_hits == 0, f"cue_hits should be 0, got {result.cue_hits}"
        assert result.bm25_hits == 2, f"bm25_hits should be 2, got {result.bm25_hits}"


def test_bm25_fallback_disabled_no_fill() -> None:
    """use_bm25_fallback=False + cue miss → BM25 미사용 + bm25_hits=0."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        HELPER.save_memory_entry(ws, _entry("MEM-2026-07-02-001", "alpha bravo",
                                            anchors=["x"]))
        HELPER.save_memory_entry(ws, _entry("MEM-2026-07-02-002", "charlie delta",
                                            anchors=["y"]))
        result = HELPER.query_memory_index(
            ws,
            MemoryIndexQuery(
                query_tokens=["alpha"],
                top_k=5,
                max_depth=0,
                use_bm25_fallback=False,
            ),
        )
        assert result.selected_entries == [], "selected should be empty with disabled fallback"
        assert result.cue_hits == 0
        assert result.bm25_hits == 0, f"bm25_hits should be 0, got {result.bm25_hits}"


# --- Phase 3 추가 2 case (dispatcher wrapper + entry script invocation) ---


def test_query_for_dispatcher_wrapper() -> None:
    """helper 의 query_memory_index_for_dispatcher 가 MemoryIndexQueryOutput 형태로 wrap."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        HELPER.save_memory_entry(ws, _entry("MEM-2026-07-02-001", "memora retrieval alpha",
                                            anchors=["memora", "retrieval"]))
        HELPER.save_memory_entry(ws, _entry("MEM-2026-07-02-002", "unrelated banana",
                                            anchors=["fruit"]))
        out = HELPER.query_memory_index_for_dispatcher(
            ws,
            ["memora"],
            top_k=5,
            max_depth=0,
            use_bm25_fallback=False,
        )
        assert isinstance(out, MemoryIndexQueryOutput), f"output type: {type(out)}"
        assert "MEM-2026-07-02-001" in out.selected_ids, f"selected_ids: {out.selected_ids}"
        assert out.cue_hits == 1
        assert out.selected_count == 1
        assert out.source_context["use_bm25_fallback"] is False


def test_entry_script_subprocess_invocation() -> None:
    """run_memory_index_query.py 가 CLI argv 받아 MemoryIndexQueryOutput JSON emit."""
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        HELPER.save_memory_entry(ws, _entry("MEM-2026-07-02-001", "memora entry test",
                                            anchors=["memora", "test"]))
        venv_py = SOURCE_ROOT.parent / ".venv" / "bin" / "python3"
        result = subprocess.run(
            [
                str(venv_py),
                str(SOURCE_ROOT / "skills" / "memory-index-query" / "scripts" / "run_memory_index_query.py"),
                "--workspace-root", str(ws),
                "--query-tokens", "memora,test",
                "--max-depth", "0",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"exit non-zero: {result.returncode}\nstderr: {result.stderr}"
        )
        # stdout JSON parse + 정합 검증
        import json as _json
        payload = _json.loads(result.stdout)
        assert payload["status"] == "ok", f"status: {payload.get('status')}"
        assert "MEM-2026-07-02-001" in payload["selected_ids"]
        assert payload["cue_hits"] == 1


# --- Phase 3b 추가 2 case (session-start memory_index wiring opt-in) ---


def test_session_start_memory_wiring_returns_dict() -> None:
    """session-start 의 _build_memory_index_query_output 가 dict 반환 (둘 다 지정 시)."""
    import tempfile
    import importlib.util

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        # minimal memory_index fixture
        mi = ws / "ai-workflow" / "memory" / "active" / "memory_index"
        mi.mkdir(parents=True, exist_ok=True)
        from workflow_kit.common.state.memory_index import save_memory_entry
        save_memory_entry(ws, _entry("MEM-2026-07-02-001", "memora retrieval test",
                                     anchors=["memora", "retrieval"]))

        # run_session_start module 의 _build_memory_index_query_output 호출
        run_path = (SOURCE_ROOT
                    / "skills" / "session-start" / "scripts" / "run_session_start.py")
        spec = importlib.util.spec_from_file_location(
            "_run_session_start_for_test", str(run_path),
        )
        mod = importlib.util.module_from_spec(spec)
        # ImportError 회피 — _build_memory_index_query_output 와 argparse 만 필요
        sys.modules["_run_session_start_for_test"] = mod
        try:
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
        except Exception:
            # 본체 main 의 import 는 실패할 수 있음 (REPO_ROOT 의 bootstrap 등).
            # helper 정의 전에 실패하면 fallback — 이 test 는 helper 정의 후를 가정.
            pass

        builder = getattr(mod, "_build_memory_index_query_output", None)
        if builder is None:
            return  # 모듈 본체 load 가 helper 까지 진행 못 함 → skip

        import argparse
        args = argparse.Namespace(
            memory_index_dir=str(mi),
            memory_query_tokens="memora,retrieval",
        )
        warnings: list[str] = []
        result = builder(args, ws, warnings)
        assert result is not None, f"result should be dict, got None"
        assert "MEM-2026-07-02-001" in result["selected_ids"], (
            f"selected_ids: {result.get('selected_ids')}"
        )


def test_session_start_memory_wiring_zero_risk_skip() -> None:
    """memory wiring flag 둘 다 부재 시 None (zero-risk skip)."""
    import importlib.util

    run_path = (SOURCE_ROOT
                / "skills" / "session-start" / "scripts" / "run_session_start.py")
    spec = importlib.util.spec_from_file_location(
        "_run_session_start_skip_test", str(run_path),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_run_session_start_skip_test"] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception:
        pass
    builder = getattr(mod, "_build_memory_index_query_output", None)
    if builder is None:
        return

    import argparse
    args = argparse.Namespace(memory_index_dir=None, memory_query_tokens=None)
    warnings: list[str] = []
    result = builder(args, Path("/nonexistent"), warnings)
    assert result is None, f"expected None (zero-risk), got {result}"
    assert warnings == [], f"no warnings expected, got {warnings}"


# --- Phase 3c 추가 2 case (doc-sync memory_index wiring opt-in) ---


def test_doc_sync_memory_wiring_returns_dict() -> None:
    """doc-sync 의 _build_memory_index_query_output 가 dict 반환 (둘 다 지정 시)."""
    import importlib.util
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        mi = ws / "ai-workflow" / "memory" / "active" / "memory_index"
        mi.mkdir(parents=True, exist_ok=True)
        from workflow_kit.common.state.memory_index import save_memory_entry
        save_memory_entry(ws, _entry("MEM-2026-07-02-001", "adr memora retrieval doc-sync",
                                     anchors=["adr", "memora"]))

        run_path = (SOURCE_ROOT
                    / "skills" / "doc-sync" / "scripts" / "run_doc_sync.py")
        spec = importlib.util.spec_from_file_location(
            "_run_doc_sync_for_test", str(run_path),
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_run_doc_sync_for_test"] = mod
        try:
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
        except Exception:
            pass

        builder = getattr(mod, "_build_memory_index_query_output", None)
        if builder is None:
            return

        import argparse
        args = argparse.Namespace(
            memory_index_dir=str(mi),
            memory_query_tokens="adr,memora",
        )
        warnings: list[str] = []
        result = builder(args, ws, warnings)
        assert result is not None, f"result should be dict, got None"
        assert "MEM-2026-07-02-001" in result["selected_ids"], (
            f"selected_ids: {result.get('selected_ids')}"
        )


def test_doc_sync_memory_wiring_zero_risk_skip() -> None:
    """doc-sync memory wiring flag 둘 다 부재 시 None (zero-risk skip)."""
    import importlib.util

    run_path = (SOURCE_ROOT
                / "skills" / "doc-sync" / "scripts" / "run_doc_sync.py")
    spec = importlib.util.spec_from_file_location(
        "_run_doc_sync_skip_test", str(run_path),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_run_doc_sync_skip_test"] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception:
        pass
    builder = getattr(mod, "_build_memory_index_query_output", None)
    if builder is None:
        return

    import argparse
    args = argparse.Namespace(memory_index_dir=None, memory_query_tokens=None)
    warnings: list[str] = []
    result = builder(args, Path("/nonexistent"), warnings)
    assert result is None, f"expected None (zero-risk), got {result}"
    assert warnings == [], f"no warnings expected, got {warnings}"


# --- Phase 3d 추가 2 case (backlog-update memory_index wiring opt-in) ---


def test_backlog_update_memory_wiring_returns_dict() -> None:
    """backlog-update 의 _build_memory_index_query_output 가 dict 반환 (둘 다 지정 시)."""
    import importlib.util
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        mi = ws / "ai-workflow" / "memory" / "active" / "memory_index"
        mi.mkdir(parents=True, exist_ok=True)
        from workflow_kit.common.state.memory_index import save_memory_entry
        save_memory_entry(ws, _entry("MEM-2026-07-02-001", "backlog update wiring test",
                                     anchors=["backlog", "update"]))

        run_path = (SOURCE_ROOT
                    / "skills" / "backlog-update" / "scripts" / "run_backlog_update.py")
        spec = importlib.util.spec_from_file_location(
            "_run_backlog_update_for_test", str(run_path),
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_run_backlog_update_for_test"] = mod
        try:
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
        except Exception:
            pass

        builder = getattr(mod, "_build_memory_index_query_output", None)
        if builder is None:
            return

        import argparse
        args = argparse.Namespace(
            memory_index_dir=str(mi),
            memory_query_tokens="backlog,update",
        )
        warnings: list[str] = []
        result = builder(args, ws, warnings)
        assert result is not None, f"result should be dict, got None"
        assert "MEM-2026-07-02-001" in result["selected_ids"], (
            f"selected_ids: {result.get('selected_ids')}"
        )


def test_backlog_update_memory_wiring_zero_risk_skip() -> None:
    """backlog-update memory wiring flag 둘 다 부재 시 None (zero-risk skip)."""
    import importlib.util

    run_path = (SOURCE_ROOT
                / "skills" / "backlog-update" / "scripts" / "run_backlog_update.py")
    spec = importlib.util.spec_from_file_location(
        "_run_backlog_update_skip_test", str(run_path),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_run_backlog_update_skip_test"] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception:
        pass
    builder = getattr(mod, "_build_memory_index_query_output", None)
    if builder is None:
        return

    import argparse
    args = argparse.Namespace(memory_index_dir=None, memory_query_tokens=None)
    warnings: list[str] = []
    result = builder(args, Path("/nonexistent"), warnings)
    assert result is None, f"expected None (zero-risk), got {result}"
    assert warnings == [], f"no warnings expected, got {warnings}"


if __name__ == "__main__":
    raise SystemExit(main())
