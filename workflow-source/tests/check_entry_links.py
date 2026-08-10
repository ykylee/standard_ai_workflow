"""memory_index entry 간 링크 smoke (ADR-006 W-3, TASK-2026-08-10-main-013).

회고 실측: expansion(3단계)은 entry 가 전부 고아라 33일간 발동 0회였다.
W-3 은 명시 링크 `related_ids` (additive) 를 도입한다 — expansion 이 따라가고,
validation 이 dangling/self 를 잡고, W-1 suggest 가 skeleton 에 관련 entry 를
프리필해 신규 entry 가 링크를 갖고 태어나게 한다.

검증 케이스 (9):
    1. related_ids roundtrip — save → load 보존 (구 entry 는 빈 list 하위호환)
    2. expansion 이 related_ids 를 따라간다 (1-hop)
    3. max_depth cap — A→B→C 에서 depth 1 이면 C 는 못 간다
    4. legacy 하위호환 — mentioned_in 의 path stem 링크도 여전히 따라간다
    5. dangling related_ids → validation issue (태어난 적 없는 링크)
    6. self-reference → validation issue
    7. W-1 suggest skeleton 프리필 — 겹치는 entry 가 related 후보로 실린다
    8. 되주입 — 링크를 지우면 expansion 이 0 으로 돌아간다 (링크가 원인이라는 증명)
    9. merge --apply — related_ids union + target/source 자기참조 제거

Stdlib only.
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.schemas.memory_index import (  # noqa: E402
    MemoryEntry,
    MemoryMergeRequest,
)
from workflow_kit.common.state.memory_index import (  # noqa: E402
    apply_memory_merge,
    load_memory_index,
    query_memory_index_for_dispatcher,
    save_memory_entry,
    suggest_memory_entry_candidates,
    validate_related_links,
)

NOW = datetime(2026, 1, 5, tzinfo=timezone.utc)


def _entry(entry_id: str, anchors: list[str], **kw: object) -> MemoryEntry:
    return MemoryEntry(
        id=entry_id,
        primary_abstraction=f"abstraction {entry_id}",
        cue_anchors=anchors,
        created_at=NOW,
        updated_at=NOW,
        **kw,  # type: ignore[arg-type]
    )


def main() -> int:
    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        if cond:
            print(f"PASS: {label}")
        else:
            print(f"FAIL: {label} — {detail}")
            failures.append(label)

    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        # A --related--> B --related--> C, D 는 고아
        save_memory_entry(ws, _entry("MEM-2026-01-05-001", ["alpha"],
                                     related_ids=["MEM-2026-01-05-002"]))
        save_memory_entry(ws, _entry("MEM-2026-01-05-002", ["beta"],
                                     related_ids=["MEM-2026-01-05-003"]))
        save_memory_entry(ws, _entry("MEM-2026-01-05-003", ["gamma"]))
        save_memory_entry(ws, _entry("MEM-2026-01-05-004", ["delta"]))

        # 1) roundtrip + 하위호환
        entries = {e.id: e for e in load_memory_index(ws)}
        check(
            "1) related_ids roundtrip + 구 entry 빈 list",
            entries["MEM-2026-01-05-001"].related_ids == ["MEM-2026-01-05-002"]
            and entries["MEM-2026-01-05-004"].related_ids == [],
            f"{ {k: v.related_ids for k, v in entries.items()} }",
        )

        # 2) expansion 이 related_ids 를 따라간다 (depth 2 → A,B,C)
        r = query_memory_index_for_dispatcher(ws, ["alpha"], max_depth=2)
        check(
            "2) expansion related_ids 추적 (A→B→C)",
            r.cue_hits == 1 and r.expansion_hits == 2
            and set(r.selected_ids) == {"MEM-2026-01-05-001", "MEM-2026-01-05-002", "MEM-2026-01-05-003"},
            f"sel={r.selected_ids} exp={r.expansion_hits}",
        )

        # 3) depth cap — depth 1 이면 C 는 못 간다
        r1 = query_memory_index_for_dispatcher(ws, ["alpha"], max_depth=1)
        check(
            "3) max_depth cap (depth 1 → A,B 만)",
            r1.expansion_hits == 1
            and set(r1.selected_ids) == {"MEM-2026-01-05-001", "MEM-2026-01-05-002"},
            f"sel={r1.selected_ids} exp={r1.expansion_hits}",
        )

        # 4) legacy path-stem 링크 하위호환
        save_memory_entry(ws, _entry("MEM-2026-01-05-005", ["epsilon"],
                                     mentioned_in=["entries/MEM-2026-01-05-004.json"]))
        r4 = query_memory_index_for_dispatcher(ws, ["epsilon"], max_depth=1)
        check(
            "4) legacy mentioned_in stem 링크 유지",
            r4.expansion_hits == 1 and "MEM-2026-01-05-004" in r4.selected_ids,
            f"sel={r4.selected_ids}",
        )

        # 5) dangling → issue
        dangle = _entry("MEM-2026-01-05-006", ["zeta"], related_ids=["MEM-2099-01-01-001"])
        issues5 = validate_related_links(list(entries.values()) + [dangle])
        check(
            "5) dangling related_ids → validation issue",
            any(i.code == "dangling_related_id" and "MEM-2026-01-05-006" in i.affected_ids
                for i in issues5),
            f"{[i.code for i in issues5]}",
        )

        # 6) self-reference → issue
        selfref = _entry("MEM-2026-01-05-007", ["eta"], related_ids=["MEM-2026-01-05-007"])
        issues6 = validate_related_links([selfref])
        check(
            "6) self-reference → validation issue",
            any(i.code == "self_related_id" for i in issues6),
            f"{[i.code for i in issues6]}",
        )

        # 7) W-1 suggest skeleton 프리필
        handoff = "## 4. 최근 완료 작업\n\n- TASK-2026-01-05-main-001 alpha 계열 후속 작업 신규\n"
        s = suggest_memory_entry_candidates(load_memory_index(ws), handoff, date_str="2026-01-06")
        cand = s["candidates"][0] if s["candidates"] else {}  # type: ignore[index]
        check(
            "7) suggest — 겹치는 entry 가 related 프리필",
            bool(cand)
            and "MEM-2026-01-05-001" in cand["related_entry_ids"]  # type: ignore[index]
            and cand["skeleton"]["related_ids"] == cand["related_entry_ids"],  # type: ignore[index]
            f"cand={ {k: cand.get(k) for k in ('task_id', 'related_entry_ids')} if cand else None }",
        )

        # 8) 되주입 — 링크 제거 → expansion 0
        unlinked = entries["MEM-2026-01-05-001"].model_copy(update={"related_ids": []})
        save_memory_entry(ws, unlinked)
        r8 = query_memory_index_for_dispatcher(ws, ["alpha"], max_depth=2)
        check(
            "8) 되주입 — 링크 제거 → expansion 0",
            r8.expansion_hits == 0 and r8.selected_ids == ["MEM-2026-01-05-001"],
            f"sel={r8.selected_ids} exp={r8.expansion_hits}",
        )

        # 9) merge --apply — related union {002.related=003} 에서 target/source 제거 → [003]
        merged = apply_memory_merge(ws, MemoryMergeRequest(
            source_ids=["MEM-2026-01-05-001", "MEM-2026-01-05-002"], apply=True,
        ))
        after = {e.id: e for e in load_memory_index(ws)}
        target = after.get(merged.target_id)
        check(
            "9) merge --apply — related_ids union + target/source 제거",
            merged.applied is True and target is not None
            and target.related_ids == ["MEM-2026-01-05-003"],
            f"target={merged.target_id} related={target.related_ids if target else None}",
        )

    total = 9
    print()
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
