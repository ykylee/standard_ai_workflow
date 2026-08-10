"""Phase 13 AC4+ wiki ↔ memory bidir-link smoke test (v0.13.3+).

R-A (sync) + R-C (audit) 의 정확성을 검증. R-B (wiki → memory reverse lookup) 는
v0.13.4+ 후속.

Test list (6 case):
1. test_audit_returns_correct_shape
2. test_path_normalization_round_trip
3. test_sync_dry_run_does_not_modify
4. test_sync_apply_updates_wiki_frontmatter
5. test_audit_is_symmetric_after_sync
6. test_format_bidir_link_audit_returns_markdown

Cross-ref: ai-workflow/wiki/topics/phase-13-definition-north-star.md §AC4+
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _repo_sandbox import repo_sandbox  # noqa: E402

# v1.1.7(TASK-019): 아래 경로들은 `main()` 이 **저장소 사본** 으로 갈아끼운다.
# 이전에는 실제 `ai-workflow/` 의 memory_index entry 와 wiki topic 을 --apply 로
# 갱신했다 되돌렸다. 되돌리므로 전후 비교는 통과하지만, 그 사이 다른 에이전트가
# 읽으면 주입된 값을 본다.
REPO_ROOT = SOURCE_ROOT.parent  # workflow-source/ 의 부모
WIKI_DIR = REPO_ROOT / "ai-workflow" / "wiki"
ENTRIES_DIR = REPO_ROOT / "ai-workflow" / "memory" / "active" / "memory_index" / "entries"

def _run_bidir_link(args: list[str]) -> dict:
    """bidir-link CLI invocation → dict parse."""
    cmd = [sys.executable, "workflow-source/tools/release_pipeline.py",
           "bidir-link"] + args + ["--json"]
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                          check=False, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(f"bidir-link failed (rc={proc.returncode}): {proc.stderr}")
    return json.loads(proc.stdout)


# 본 smoke 는 실제 저장소의 wiki / memory_index 를 변경한 뒤 되돌린다.
# 이전 구현은 `git checkout HEAD -- <path>` 로 복원했는데, 이는 **HEAD 기준 복원**
# 이므로 그 경로의 *미커밋 작업을 조용히 파괴* 한다 (실제로 본 세션에서 wiki
# frontmatter 수정분이 전량 smoke 실행 한 번에 사라졌다).
# 지금은 실행 직전 파일 내용을 그대로 snapshot 해 두고 그 snapshot 으로 복원하므로,
# 미커밋 상태든 아니든 **실행 전 상태가 정확히 보존**된다.
_SNAPSHOT: dict[Path, bytes] | None = None
_SNAPSHOT_ROOTS = (WIKI_DIR, ENTRIES_DIR)


def _take_snapshot() -> dict[Path, bytes]:
    snap: dict[Path, bytes] = {}
    for root in _SNAPSHOT_ROOTS:
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if f.is_file():
                snap[f] = f.read_bytes()
    return snap


def _restore_state() -> None:
    """실행 전 snapshot 으로 복원 (미커밋 작업 보존)."""
    global _SNAPSHOT
    if _SNAPSHOT is None:
        return
    for path, data in _SNAPSHOT.items():
        if not path.exists() or path.read_bytes() != data:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    # snapshot 이후 새로 생긴 파일은 제거 (test 가 만든 산출물).
    for root in _SNAPSHOT_ROOTS:
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if f.is_file() and f not in _SNAPSHOT:
                f.unlink()


# --- Tests ---


def test_audit_returns_correct_shape() -> None:
    """audit 결과 dict 가 spec 형식 (total_wiki_pages / total_memory_entries / symmetric_links / asymmetric / is_symmetric) 모두 포함."""
    _restore_state()
    result = _run_bidir_link([])
    audit = result["audit"]
    assert "total_wiki_pages" in audit
    assert "total_memory_entries" in audit
    assert "symmetric_links" in audit
    assert "asymmetric_count" in audit
    assert "is_symmetric" in audit
    assert isinstance(audit["asymmetric"], list)
    assert audit["total_wiki_pages"] >= 1  # 최소 1 wiki page 존재
    assert audit["total_memory_entries"] >= 1


def test_path_normalization_round_trip() -> None:
    """normalize_memory_path_to_wiki_relative 가 in-repo 절대 path → wiki relative 변환 정확."""
    sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
    from workflow_kit.common.state.bidir_link import normalize_memory_path_to_wiki_relative
    # 정상 case: ai-workflow/wiki/topics/foo.md → topics/foo.md
    rel = normalize_memory_path_to_wiki_relative("ai-workflow/wiki/topics/foo.md", REPO_ROOT)
    assert rel == "topics/foo.md", f"got {rel!r}"
    # 이미 relative 인 case
    rel2 = normalize_memory_path_to_wiki_relative("topics/foo.md", REPO_ROOT)
    assert rel2 == "topics/foo.md", f"got {rel2!r}"
    # wiki path 아닌 case → None
    rel3 = normalize_memory_path_to_wiki_relative("workflow_kit/foo.py", REPO_ROOT)
    assert rel3 is None, f"got {rel3!r}"


def test_sync_dry_run_does_not_modify() -> None:
    """drift 주입 (entry 의 mentioned_in 에 신규 wiki path) + dry-run → file unchanged."""
    _restore_state()
    # MEM-2026-07-09-001 의 mentioned_in 에 가짜 wiki page path 추가
    entry_file = ENTRIES_DIR / "MEM-2026-07-09-001.json"
    backup = entry_file.read_text(encoding="utf-8")
    data = json.loads(backup)
    fake_wiki_path = "ai-workflow/wiki/topics/phase-13-definition-north-star.md"
    if fake_wiki_path not in data["mentioned_in"]:
        data["mentioned_in"].append(fake_wiki_path)
        entry_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        # dry-run
        result = _run_bidir_link([])
        # audit 가 1+ asymmetric 표시 (위에서 추가했으므로)
        assert result["audit"]["asymmetric_count"] >= 1
        # wiki page 의 frontmatter 는 변경 안 됨 (dry-run 만)
        wiki_text = (WIKI_DIR / "topics" / "phase-13-definition-north-star.md").read_text(encoding="utf-8")
        assert "MEM-2026-07-09-001.json" not in wiki_text, \
            "dry-run 이 wiki page 를 modify 하면 안 됨"
    finally:
        entry_file.write_text(backup, encoding="utf-8")
        _restore_state()


def test_sync_apply_updates_wiki_frontmatter() -> None:
    """drift 주입 + --apply → wiki page 의 frontmatter 에 memory entry path 추가 + is_symmetric."""
    _restore_state()
    entry_file = ENTRIES_DIR / "MEM-2026-07-09-001.json"
    backup = entry_file.read_text(encoding="utf-8")
    data = json.loads(backup)
    fake_wiki_path = "ai-workflow/wiki/topics/phase-13-definition-north-star.md"
    if fake_wiki_path not in data["mentioned_in"]:
        data["mentioned_in"].append(fake_wiki_path)
        entry_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        result = _run_bidir_link(["--apply"])
        sync = result.get("sync") or {}
        assert sync.get("total_changes", 0) >= 1
        assert any("phase-13" in c["wiki_page"] for c in sync.get("changes", []))
        # audit 결과 재확인 — symmetric
        audit = result["audit"]
        assert audit["is_symmetric"] is True, f"asymmetric=0 expected: got {audit}"
    finally:
        entry_file.write_text(backup, encoding="utf-8")
        _restore_state()


def test_audit_is_symmetric_after_sync() -> None:
    """sync --apply 후 re-audit (default) → is_symmetric = True."""
    _restore_state()
    # 현재 상태 (sync 적용 후)에서 audit
    _run_bidir_link(["--apply"])
    result = _run_bidir_link([])
    assert result["audit"]["is_symmetric"] is True
    _restore_state()


def test_format_bidir_link_audit_returns_markdown() -> None:
    """_format_bidir_link_audit 가 dict → markdown 문자열. 깨끗한 audit result 에 대해 본문 검증."""
    sys.path.insert(0, str(REPO_ROOT / "workflow-source" / "tools"))
    import importlib
    rp = importlib.import_module("release_pipeline")

    # audit dict 만 (sync 없음)
    audit_dict = {
        "mode": "audit",
        "audit": {
            "total_wiki_pages": 87,
            "total_memory_entries": 7,
            "symmetric_links": 1,
            "asymmetric_count": 0,
            "is_symmetric": True,
            "asymmetric": [],
            "wiki_pages_with_related_memory": 1,
            "memory_entries_with_mentioned_wiki": 1,
        },
    }
    md = rp._format_bidir_link_audit(audit_dict)
    assert "## Bidirectional link audit" in md
    assert "is_symmetric: **True**" in md
    assert "asymmetric count: **0**" in md

    # asymmetric 1+ 인 case: 비고 표시
    audit_dict2 = {
        "mode": "audit",
        "audit": {
            "total_wiki_pages": 87,
            "total_memory_entries": 7,
            "symmetric_links": 0,
            "asymmetric_count": 2,
            "is_symmetric": False,
            "asymmetric": [
                {"memory_entry_id": "MEM-001", "wiki_page": "topics/foo.md", "direction": "memory_only"},
                {"memory_entry_id": "MEM-002", "wiki_page": "concepts/bar.md", "direction": "wiki_only"},
            ],
            "wiki_pages_with_related_memory": 0,
            "memory_entries_with_mentioned_wiki": 1,
        },
    }
    md2 = rp._format_bidir_link_audit(audit_dict2)
    assert "Asymmetric links" in md2
    assert "MEM-001" in md2
    assert "MEM-002" in md2


# --- 메인 실행 ---


def main() -> int:
    """저장소 **사본** 에서 돌린다 — 원본은 읽기만 한다 (TASK-019)."""
    global REPO_ROOT, WIKI_DIR, ENTRIES_DIR
    origin = REPO_ROOT
    watched = sorted((origin / "ai-workflow").rglob("*.json")) + \
              sorted((origin / "ai-workflow" / "wiki").rglob("*.md"))
    before = {q: q.read_bytes() for q in watched if q.is_file()}

    with repo_sandbox(origin) as sandbox:
        REPO_ROOT = sandbox
        WIKI_DIR = sandbox / "ai-workflow" / "wiki"
        ENTRIES_DIR = sandbox / "ai-workflow" / "memory" / "active" / "memory_index" / "entries"
        # snapshot 도 사본 기준으로 다시 잡는다. 모듈 로드 시점의 것은 원본 경로를
        # 가리키므로, 그대로 두면 `_restore_state()` 가 사본이 아니라 **원본** 에 쓴다.
        global _SNAPSHOT_ROOTS, _SNAPSHOT
        _SNAPSHOT_ROOTS = (WIKI_DIR, ENTRIES_DIR)
        _SNAPSHOT = _take_snapshot()
        rc = _run_cases()

    changed = [str(q.relative_to(origin)) for q, b in before.items()
               if q.is_file() and q.read_bytes() != b]
    assert not changed, f"원본을 건드렸다: {changed[:5]} — 사본에서만 --apply 해야 한다"
    return rc


def _run_cases() -> int:
    test_funcs = [
        test_audit_returns_correct_shape,
        test_path_normalization_round_trip,
        test_sync_dry_run_does_not_modify,
        test_sync_apply_updates_wiki_frontmatter,
        test_audit_is_symmetric_after_sync,
        test_format_bidir_link_audit_returns_markdown,
    ]
    failures: list[tuple[str, str]] = []
    global _SNAPSHOT
    _SNAPSHOT = _take_snapshot()  # 실행 전 상태 보존 (미커밋 작업 포함)
    try:
        for func in test_funcs:
            try:
                func()
                print(f"  PASS: {func.__name__}")
            except AssertionError as e:
                failures.append((func.__name__, f"AssertionError: {e}"))
                print(f"  FAIL: {func.__name__} — {e}")
            except Exception as e:
                failures.append((func.__name__, f"{type(e).__name__}: {e}"))
                print(f"  FAIL: {func.__name__} — {type(e).__name__}: {e}")
    finally:
        _restore_state()

    total = len(test_funcs)
    passed = total - len(failures)
    print(f"\n{passed}/{total} PASS")
    if failures:
        for name, err in failures:
            print(f"  - {name}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
