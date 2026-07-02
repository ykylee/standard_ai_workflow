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
    MergeState,
)
from workflow_kit.common.state import memory_index as HELPER  # noqa: E402

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


if __name__ == "__main__":
    raise SystemExit(main())
