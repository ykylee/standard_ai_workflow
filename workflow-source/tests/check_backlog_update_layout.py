"""`backlog-update --apply` 의 산출물이 v0.14.0+ append-only layout 인가 (v1.0.1+).

## 왜 필요한가

stable 로 선언된 `backlog-update` 가 **governance 가 규정한 layout 을 만들지 못하고
있었다**. v0.14.0 전환이 절반만 적용돼 있었던 것:

- task file 은 만들지만 이름이 `YYYY-MM-DD_TASK-….md` (현행 규약은 `TASK-….md`)
- daily index 에 task 본문을 **통째로 인라인** (현행 index 는 link 모음)
- 덮어쓰기 전에 `.md.bak` 생성 — `.bak` 는 v0.15.0 에서 폐기된 개념

아무 테스트도 이를 잡지 못했다. 기존 smoke 는 "파일이 쓰였는가" 와 본문 문자열만 봤고,
**layout 자체를 규약으로 검사하지 않았다.** 그래서 skill 을 실제로 돌려 산출물을
governance 규약과 대조하는 본 smoke 를 둔다 (§2.18 "선언이 사실인가" 의 연장).

Test list (9 case):
1. test_daily_index_is_link_only
2. test_task_file_naming_and_frontmatter
3. test_no_bak_file_written
4. test_second_apply_replaces_block_not_duplicates
5. test_index_links_resolve_with_layout_checker_regex
6. test_update_preserves_unspecified_fields (TASK-2026-08-11-main-023 되주입)
7. test_update_preserves_index_extras (TASK-2026-08-11-main-023 되주입)
8. test_update_preserves_status_when_unspecified (TASK-2026-08-12-main-008 되주입)
9. test_handoff_dedupes_by_task_id (TASK-2026-08-11-main-023 되주입)

Cross-ref: workflow-source/MEMORY_GOVERNANCE.md §2 +
workflow-source/tests/check_appendonly_memory_layout.py (저장소 실물 검사).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.project_docs import TASK_ID_PATTERN  # noqa: E402

BRANCH = "layout-smoke"
TASK_FRONTMATTER_KEYS = {"id", "status", "created_at", "source_anchor", "source_path", "kind"}
SCRIPT = SOURCE_ROOT / "skills" / "backlog-update" / "scripts" / "run_backlog_update.py"


def _make_workspace(td: str) -> Path:
    ws = Path(td)
    (ws / "docs").mkdir(parents=True)
    (ws / "docs" / "PROJECT_PROFILE.md").write_text("# Profile\n", encoding="utf-8")
    base = ws / "ai-workflow" / "memory" / "active" / BRANCH
    (base / "backlog" / "tasks").mkdir(parents=True)
    (base / "sessions").mkdir(parents=True)
    return ws


def _branch_dir(ws: Path) -> Path:
    return ws / "ai-workflow" / "memory" / "active" / BRANCH


def _run_apply(ws: Path, *extra: str) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    env["CODEX_WORKFLOW_BRANCH"] = BRANCH
    proc = subprocess.run(
        [sys.executable, str(SCRIPT),
         "--project-profile-path", str(ws / "docs" / "PROJECT_PROFILE.md"),
         "--target-date", "2026-07-22",
         "--apply", *extra],
        capture_output=True, text=True, check=False, env=env, cwd=str(ws),
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout)


def _seed(ws: Path, *, name: str = "레이아웃 검증", kind: str = "release") -> dict:
    return _run_apply(ws, "--task-name", name, "--task-brief", "brief",
                      "--mode", "create", "--kind", kind)


# --- Tests ---


def test_daily_index_is_link_only() -> None:
    """index 는 머리말 + link block 만. task 본문이 인라인되면 안 된다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _make_workspace(td)
        _seed(ws)
        index = (_branch_dir(ws) / "backlog" / "2026-07-22.md").read_text(encoding="utf-8")
        assert index.startswith("# Backlog Index — 2026-07-22"), index[:80]
        assert "## Tasks" in index
        # legacy 인라인의 흔적들
        assert "작업 백로그" not in index, "legacy 머리말이 남아 있다"
        assert "- 우선순위:" not in index, "task 본문이 index 에 인라인됐다"
        assert "work_backlog.md" not in index, "legacy index 링크가 남아 있다"


def test_task_file_naming_and_frontmatter() -> None:
    """`tasks/TASK-<id>.md` + frontmatter 6 key (governance §2 Task Detail)."""
    with tempfile.TemporaryDirectory() as td:
        ws = _make_workspace(td)
        payload = _seed(ws)
        task_id = payload["task_id"]
        tasks_dir = _branch_dir(ws) / "backlog" / "tasks"
        files = sorted(p.name for p in tasks_dir.glob("*.md"))
        assert files == [f"{task_id}.md"], files
        assert re.fullmatch(TASK_ID_PATTERN, task_id), f"정본 ID 패턴 위반: {task_id}"

        text = (tasks_dir / f"{task_id}.md").read_text(encoding="utf-8")
        fm = re.match(r"^---\n(.+?)\n---", text, re.S)
        assert fm, "frontmatter 부재"
        keys = set(re.findall(r"^([a-z_]+):", fm.group(1), re.M))
        assert TASK_FRONTMATTER_KEYS <= keys, f"누락 key: {TASK_FRONTMATTER_KEYS - keys}"


def test_no_bak_file_written() -> None:
    """`.bak` 는 v0.15.0 에서 폐기됐다 — 재도입하면 안 된다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _make_workspace(td)
        _seed(ws)
        _seed(ws, name="두 번째")
        baks = [str(p) for p in ws.rglob("*.bak")]
        assert not baks, f".bak 생성됨: {baks}"


def test_second_apply_replaces_block_not_duplicates() -> None:
    """같은 task 를 다시 apply 하면 index block 이 *교체*된다 (중복 ❌)."""
    with tempfile.TemporaryDirectory() as td:
        ws = _make_workspace(td)
        task_id = _seed(ws)["task_id"]
        _run_apply(ws, "--task-name", "레이아웃 검증", "--task-brief", "완료",
                   "--task-id", task_id, "--mode", "update", "--kind", "release",
                   "--status", "done", "--validation-result", "smoke PASS")
        index = (_branch_dir(ws) / "backlog" / "2026-07-22.md").read_text(encoding="utf-8")
        assert index.count(f"- **{task_id}**") == 1, index
        assert "  - status: done" in index, index


def test_index_links_resolve_with_layout_checker_regex() -> None:
    """저장소 layout 체커가 쓰는 정규식으로 index 를 파싱해 task file 이 resolve 된다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _make_workspace(td)
        _seed(ws)
        _seed(ws, name="두 번째", kind="generic")
        backlog_dir = _branch_dir(ws) / "backlog"
        index = (backlog_dir / "2026-07-22.md").read_text(encoding="utf-8")
        link_re = re.compile(rf"\*\*({TASK_ID_PATTERN})\*\*\s*\[([^\]]+)\]")
        found = link_re.findall(index)
        assert len(found) == 2, f"link 파싱 실패: {found}"
        for task_id, kind in found:
            assert kind in {"release", "generic", "session"}, kind
            assert (backlog_dir / "tasks" / f"{task_id}.md").exists(), task_id


def test_update_preserves_unspecified_fields() -> None:
    """update 는 재생성이 아니라 병합이다 (TASK-2026-08-11-main-023).

    되주입 근거: 이전 구현은 인자만으로 문서를 다시 만들어, kind/우선순위/담당/
    작업 내용/완료 기준이 미지정 호출 한 번에 삭제됐다 (실측: TASK-018 손 복원).
    이 case 는 그 버전이라면 전부 FAIL 한다.
    """
    with tempfile.TemporaryDirectory() as td:
        ws = _make_workspace(td)
        task_id = _run_apply(
            ws, "--task-name", "원래 제목", "--task-brief", "원래 작업 내용",
            "--mode", "create", "--kind", "session", "--priority", "medium",
            "--owner", "Agent A", "--done-criteria", "기준 X", "--status", "planned",
        )["task_id"]
        # 미지정 update — 상태와 진행 현황만 바뀌어야 한다.
        payload = _run_apply(ws, "--task-name", "다르게 쓴 제목", "--task-brief", "진행 한 줄",
                             "--task-id", task_id, "--mode", "update", "--status", "in_progress")
        text = (_branch_dir(ws) / "backlog" / "tasks" / f"{task_id}.md").read_text(encoding="utf-8")
        assert "kind: session" in text, "kind 가 기본값으로 덮였다"
        assert "- 우선순위: medium" in text, "우선순위가 기본값으로 덮였다"
        assert "- 담당: Agent A" in text, "담당이 삭제됐다"
        assert "- 작업 내용: 원래 작업 내용" in text, "작업 내용이 brief 로 덮였다"
        assert "- 완료 기준: 기준 X" in text, "완료 기준이 삭제됐다"
        assert "status: in_progress" in text and "- 상태: in_progress" in text, "상태 미갱신"
        assert "진행 한 줄" in text, "진행 현황 미갱신"
        assert f"# {task_id} — 원래 제목" in text, "제목이 입력값으로 덮였다"
        assert any("제목이 기존과 다르다" in w for w in payload["warnings"]), "제목 차이 경고 부재"


def test_update_preserves_index_extras() -> None:
    """update 는 index block 의 부가 sub-bullet(notes 등)과 head 를 보존한다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _make_workspace(td)
        task_id = _seed(ws)["task_id"]
        index_path = _branch_dir(ws) / "backlog" / "2026-07-22.md"
        text = index_path.read_text(encoding="utf-8")
        text = re.sub(r"(  - status: \w+)", r"\1\n  - notes: 손으로 쓴 노트", text, count=1)
        index_path.write_text(text, encoding="utf-8")
        _run_apply(ws, "--task-name", "레이아웃 검증", "--task-brief", "갱신",
                   "--task-id", task_id, "--mode", "update", "--status", "in_progress")
        index = index_path.read_text(encoding="utf-8")
        assert "  - notes: 손으로 쓴 노트" in index, "index 의 손 sub-bullet 이 삭제됐다"
        assert "[release] 레이아웃 검증" in index, "index head 의 kind/제목이 덮였다"
        assert "  - status: in_progress" in index, "index status 미갱신"


def test_update_preserves_status_when_unspecified() -> None:
    """--status 미지정 update 는 기존 상태를 보존한다 (TASK-2026-08-12-main-008).

    되주입 근거: 이전 규칙은 미지정 update 를 무조건 in_progress 로 떨어뜨려,
    planned task 에 메모만 다는 호출이 상태를 승격시켰다. 미지정은 "바꾸지 말라" 다.
    done 보존도 확인한다 — 기존 done 은 재강등하지 않는다.
    """
    with tempfile.TemporaryDirectory() as td:
        ws = _make_workspace(td)
        task_id = _run_apply(ws, "--task-name", "상태 보존", "--task-brief", "생성",
                             "--mode", "create", "--status", "planned")["task_id"]
        task_file = _branch_dir(ws) / "backlog" / "tasks" / f"{task_id}.md"
        # 메모만 다는 update (--status 미지정) → planned 유지
        _run_apply(ws, "--task-name", "상태 보존", "--task-brief", "메모",
                   "--task-id", task_id, "--mode", "update")
        text = task_file.read_text(encoding="utf-8")
        assert "status: planned" in text and "- 상태: planned" in text, (
            f"미지정 update 가 상태를 바꿨다:\n{text[:200]}")
        # done (검증 포함) 전이 후, 미지정 update → done 유지 (재강등 금지)
        _run_apply(ws, "--task-name", "상태 보존", "--task-brief", "완료",
                   "--task-id", task_id, "--mode", "update", "--status", "done",
                   "--validation-result", "smoke PASS")
        _run_apply(ws, "--task-name", "상태 보존", "--task-brief", "사후 메모",
                   "--task-id", task_id, "--mode", "update")
        text = task_file.read_text(encoding="utf-8")
        assert "status: done" in text, f"미지정 update 가 done 을 되돌렸다:\n{text[:200]}"


def test_handoff_dedupes_by_task_id() -> None:
    """handoff 반영은 표기가 아니라 task ID 로 dedupe 한다 (중복 bullet 방지)."""
    with tempfile.TemporaryDirectory() as td:
        ws = _make_workspace(td)
        task_id = _seed(ws)["task_id"]
        handoff = _branch_dir(ws) / "session_handoff.md"
        handoff.write_text(
            "# Session Handoff\n\n## 2. 진행 중 작업\n\n- 현재 `in_progress` 작업:\n"
            f"- {task_id} — 다른 표기의 같은 작업 (부가 설명)\n\n"
            "## 3. 차단 작업\n\n- 현재 `blocked` 작업:\n-\n\n"
            "## 4. 최근 완료 작업\n\n- 최근 완료 작업 목록:\n-\n",
            encoding="utf-8",
        )
        _run_apply(ws, "--task-name", "레이아웃 검증", "--task-brief", "갱신",
                   "--task-id", task_id, "--mode", "update", "--status", "in_progress")
        text = handoff.read_text(encoding="utf-8")
        assert text.count(task_id) == 1, f"handoff 에 같은 task 가 중복됐다:\n{text}"
        # done 전이 시 in_progress 에서 빠지고 완료 목록에 1건만 남는다.
        _run_apply(ws, "--task-name", "레이아웃 검증", "--task-brief", "완료",
                   "--task-id", task_id, "--mode", "update", "--status", "done",
                   "--validation-result", "smoke PASS")
        text = handoff.read_text(encoding="utf-8")
        in_progress_section = text.split("## 2.")[1].split("## 3.")[0]
        done_section = text.split("## 4.")[1]
        assert task_id not in in_progress_section, "done 전이 후에도 in_progress 에 남았다"
        assert done_section.count(task_id) == 1, "완료 목록 중복/누락"


def main() -> int:
    test_funcs = [
        test_daily_index_is_link_only,
        test_task_file_naming_and_frontmatter,
        test_no_bak_file_written,
        test_second_apply_replaces_block_not_duplicates,
        test_index_links_resolve_with_layout_checker_regex,
        test_update_preserves_unspecified_fields,
        test_update_preserves_index_extras,
        test_update_preserves_status_when_unspecified,
        test_handoff_dedupes_by_task_id,
    ]
    failures: list[tuple[str, str]] = []
    for func in test_funcs:
        try:
            func()
            print(f"  PASS: {func.__name__}")
        except AssertionError as e:
            failures.append((func.__name__, f"AssertionError: {e}"))
            print(f"  FAIL: {func.__name__} — {e}")
        except Exception as e:  # noqa: BLE001
            failures.append((func.__name__, f"{type(e).__name__}: {e}"))
            print(f"  FAIL: {func.__name__} — {type(e).__name__}: {e}")

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
