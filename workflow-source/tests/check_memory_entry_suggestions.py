"""memory_index entry 승격 후보 제안 smoke (ADR-006 W-1, TASK-2026-08-10-main-011).

30일 실사용 회고 (ADR-006) 의 결론: 신규 entry 0건의 원인은 쓰기 운영 루프
부재였다. W-1 은 handoff §4 의 완료 작업을 기존 entry corpus 와 대조해
"index 가 모르는 것" 을 **advisory 로만** 제안한다 — 자동 적재는 하지 않는다.

검증 케이스 (8):
    1. 기존 entry 가 덮는 제목 → 후보 아님 (covered)
    2. index 가 모르는 제목 → 후보 + cue 제안 (stopword/숫자 제외)
    3. §4 섹션 부재 → compared 0, 오류 없음
    4. skeleton id — 같은 날짜 기존 002 → 003 제안
    5. advisory 무-write — 실행 전후 entries/ 불변 + written_paths []
    6. max_candidates 상한 + coverage 오름차순 정렬
    7. 되주입 — novel 제목 token 을 가진 entry 를 넣으면 그 후보가 사라진다
       (비교가 실제로 entry corpus 를 읽는다는 증명)
    8. CLI — --json 파싱 + handoff 부재 시 status=error / exit 1

Stdlib only (+ subprocess 로 CLI 실측).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.state.memory_index import (  # noqa: E402
    load_memory_index,
    suggest_memory_entry_candidates,
)

HANDOFF = """# Session Handoff

## 4. 최근 완료 작업

- TASK-2026-01-05-main-001 registry federation 정공법 — merge_entries API
- TASK-2026-01-05-main-002 학습회 발표자료 슬라이드 레이아웃 개편 — 38장
- TASK-2026-01-05-main-003 telemetry 윈도 기반 acceptance 재설계 2026 — case 4

## 5. 다음
"""


def _write_entry(entries_dir: Path, entry_id: str, abstraction: str, anchors: list[str]) -> None:
    entries_dir.mkdir(parents=True, exist_ok=True)
    (entries_dir / f"{entry_id}.json").write_text(json.dumps({
        "id": entry_id,
        "schema_version": 1,
        "source_paths": [],
        "primary_abstraction": abstraction,
        "cue_anchors": anchors,
        "value_digest": "",
        "owners": [],
        "scope": [],
        "merge_state": "active",
        "mentioned_in": [],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }, ensure_ascii=False), encoding="utf-8")


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
        entries_dir = ws / "ai-workflow" / "memory" / "active" / "memory_index" / "entries"
        _write_entry(
            entries_dir, "MEM-2026-01-05-002",
            "registry federation 정공법 merge_entries",
            ["registry", "federation", "merge_entries"],
        )
        entries = load_memory_index(ws)

        result = suggest_memory_entry_candidates(entries, HANDOFF, date_str="2026-01-05")
        by_id = {str(c["task_id"]): c for c in result["candidates"]}  # type: ignore[union-attr]

        # 1) 덮인 제목은 후보가 아니다
        check(
            "1) 기존 entry 가 덮는 제목 → covered",
            "TASK-2026-01-05-main-001" not in by_id and result["covered"] == 1,
            f"covered={result['covered']} candidates={sorted(by_id)}",
        )

        # 2) novel 제목 → 후보 + cue 제안 위생
        slide = by_id.get("TASK-2026-01-05-main-002")
        tele = by_id.get("TASK-2026-01-05-main-003")
        anchors = list(tele["suggested_cue_anchors"]) if tele else []
        check(
            "2) novel 제목 → 후보 + cue 제안 (숫자 제외)",
            slide is not None and tele is not None
            and "telemetry" in anchors and "2026" not in anchors,
            f"slide={slide is not None} tele={tele is not None} anchors={anchors}",
        )

        # 3) §4 부재 → 조용히 0
        empty = suggest_memory_entry_candidates(entries, "# 아무 섹션 없음\n", date_str="2026-01-05")
        check(
            "3) §4 부재 → compared 0, 오류 없음",
            empty["compared"] == 0 and empty["candidates_total"] == 0,
            f"{empty}",
        )

        # 4) skeleton id 다음 sequence
        skeleton_id = str(slide["skeleton"]["id"]) if slide else ""  # type: ignore[index]
        check(
            "4) skeleton id — 기존 002 다음은 003",
            skeleton_id == "MEM-2026-01-05-003",
            f"id={skeleton_id}",
        )

        # 5) advisory 무-write
        before = sorted(p.name for p in entries_dir.iterdir())
        suggest_memory_entry_candidates(entries, HANDOFF, date_str="2026-01-05")
        after = sorted(p.name for p in entries_dir.iterdir())
        check(
            "5) advisory — entries/ 불변",
            before == after == ["MEM-2026-01-05-002.json"],
            f"before={before} after={after}",
        )

        # 6) max_candidates 상한 + 정렬
        capped = suggest_memory_entry_candidates(
            entries, HANDOFF, date_str="2026-01-05", max_candidates=1,
        )
        coverages = [float(str(c["best_coverage"])) for c in result["candidates"]]  # type: ignore[union-attr]
        check(
            "6) max_candidates 상한 + coverage 오름차순",
            len(capped["candidates"]) == 1  # type: ignore[arg-type]
            and capped["candidates_total"] == 2
            and coverages == sorted(coverages),
            f"capped={len(capped['candidates'])} total={capped['candidates_total']} covs={coverages}",  # type: ignore[arg-type]
        )

        # 7) 되주입 — novel 을 아는 entry 를 넣으면 후보에서 사라진다
        _write_entry(
            entries_dir, "MEM-2026-01-05-005",
            "학습회 발표자료 슬라이드 레이아웃",
            ["학습회", "발표자료", "슬라이드", "레이아웃", "개편", "38장"],
        )
        entries2 = load_memory_index(ws)
        result2 = suggest_memory_entry_candidates(entries2, HANDOFF, date_str="2026-01-05")
        ids2 = {str(c["task_id"]) for c in result2["candidates"]}  # type: ignore[union-attr]
        check(
            "7) 되주입 — corpus 에 넣으면 후보가 사라진다",
            "TASK-2026-01-05-main-002" not in ids2 and result2["covered"] == 2,
            f"ids={sorted(ids2)} covered={result2['covered']}",
        )

        # 8) CLI — --json + error path
        handoff_file = ws / "session_handoff.md"
        handoff_file.write_text(HANDOFF, encoding="utf-8")
        tool = SOURCE_ROOT / "workflow_kit" / "tools" / "suggest_memory_entries.py"
        ok = subprocess.run(
            [sys.executable, str(tool), "--handoff-path", str(handoff_file),
             "--workspace-root", str(ws), "--date", "2026-01-05", "--json"],
            capture_output=True, text=True,
        )
        ok_payload = json.loads(ok.stdout) if ok.returncode == 0 else {}
        missing = subprocess.run(
            [sys.executable, str(tool), "--handoff-path", str(ws / "no-such.md"),
             "--workspace-root", str(ws), "--json"],
            capture_output=True, text=True,
        )
        missing_payload = json.loads(missing.stdout) if missing.stdout else {}
        check(
            "8) CLI — json ok / 부재 시 error + exit 1",
            ok.returncode == 0 and ok_payload.get("status") == "ok"
            and ok_payload.get("written_paths") == []
            and missing.returncode == 1 and missing_payload.get("status") == "error",
            f"ok_rc={ok.returncode} missing_rc={missing.returncode} "
            f"missing_status={missing_payload.get('status')}",
        )

    total = 8
    print()
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
