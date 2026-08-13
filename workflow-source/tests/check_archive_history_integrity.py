#!/usr/bin/env python3
"""브랜치 아카이브가 **이력을 끊지 않는지** 검증한다 (10 cases).

## 계보 — 아카이브는 "이동" 만 하고 있었다

`archive_branch_memory` 는 `active/<branch>/` 를 `archived/<branch>/` 로 옮기기만
했다. 이관이라는 개념이 없었고, 그래서 두 갈래로 이력이 끊겼다 (2026-08-13 실측):

1. **미완료 task 소실** — 도구는 task 파일을 세어 `.archived.json` 에 id 를 적으면서
   **status 는 보지 않았다**. `archived/` 는 어떤 집계도 읽지 않으므로
   (state 생성기·dashboard 모두 `active/` 만 훑는다) 미완료 task 가 조용히 사라진다.
   실제로 `…-guard-003`(planned)이 그렇게 사라졌고 사람이 눈으로 알아채 이월했다.
2. **참조 미재작성** — 옮긴 뒤 그 경로를 가리키던 링크를 아무도 안 고쳤다.
   아카이브된 문서 22개 중 **12개**가 깨진 링크를 갖고 있었고,
   `archived/…/state.json` 의 `source_of_truth` **5개 경로 전부**가 사라진
   `active/…` 를 가리켰다.

그런데 **전량 254/254 는 green 이었다.** `check_doc_links` 는 `doc_dir_path` 를 받는
on-demand MCP 도구지 저장소를 훑는 smoke 가 아니라서, `archived/` 아래는 아무도 안
봤다. 회귀 방지 장치가 없으니 깨짐이 쌓이기만 했다 — `codex/phase6` 의 11개 파일은
1.5개월간 죽은 참조를 들고 있었다.

## 이 검사가 재는 것

fixture 로 **도구의 계약**(차단 / 재작성 / 오탐 없음)을, 자기 적용으로 **이 저장소의
archived/ 현재 상태**를 잰다. 후자가 없으면 계약만 지키고 실물은 썩는다.

10 cases:
  1) `open_tasks` 판정 — done 제외, **status 미기재는 미완료로 본다**
  2) 미완료 task 가 있으면 아카이브를 **막는다** (기본값)
  3) `--allow-open-tasks` 면 진행하되 `.archived.json` 에 `open_task_ids` 를 남긴다
  4) 이동 후 **markdown 링크 재작성** (상대 경로 `../../active/…` 형태)
  5) 이동 후 **state.json 경로 재작성**
  6) **살아 있는 링크는 안 건드린다** (오탐 방지 — 고치는 쪽이 손상이 되면 안 된다)
  7) **자기 적용** — 이 저장소 `archived/` 의 markdown 링크가 전부 resolve 된다
  8) **자기 적용** — `archived/**/state.json` 이 `active/` 를 가리키지 않는다
  9) **자기 적용** — `archived/` 에 미완료 task 가 없다
 10) `carried_over_to` 가 있으면 미완료로 세지 않는다 (이관 축 — `done` 으로 적으면 거짓)

Refs:
  - workflow_kit/tools/archive_branch_memory.py
  - workflow-source/MEMORY_GOVERNANCE.md — Branch-scoped layout (v1.0.0+)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.tools.archive_branch_memory import (  # noqa: E402
    _rewrite_markdown_links,
    open_tasks,
)

REQUIRES_QUIET_REPO = True
"""case 7~9 가 저장소의 살아있는 `memory/archived/` 를 관찰한다."""

TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "archive_branch_memory.py"
ARCHIVED_DIR = REPO_ROOT / "ai-workflow" / "memory" / "archived"
MEMORY_REL = "ai-workflow/memory"

LINK_RE = re.compile(r"\]\(([^)]+)\)")


# ---------------------------------------------------------------------------
# fixture
# ---------------------------------------------------------------------------
def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _task(status: str | None) -> str:
    head = "---\nid: TASK-2026-01-01-x-001\n"
    if status is not None:
        head += f"status: {status}\n"
    return head + "created_at: 2026-01-01\nkind: generic\n---\n\n# task\n"


def _branch_memory(root: Path, branch: str, *, statuses: list[str | None]) -> Path:
    """`active/<branch>/` 최소 세트 + 그것을 가리키는 이웃 문서."""
    d = root / "active" / branch
    for idx, st in enumerate(statuses, start=1):
        _write(d / "backlog" / "tasks" / f"TASK-2026-01-01-x-{idx:03d}.md", _task(st))
    _write(d / "backlog" / "2026-01-01.md", "# index\n")
    _write(d / "sessions" / "s.md", "# 세션 기록\n")
    _write(d / "session_handoff.md", "# handoff\n")
    _write(d / "state.json", json.dumps({
        "source_of_truth": {
            "tasks_dir": f"{MEMORY_REL}/active/{branch}/backlog/tasks",
            "sessions_dir": f"{MEMORY_REL}/active/{branch}/sessions",
        },
    }, ensure_ascii=False, indent=2) + "\n")
    return d


def _run_tool(memory_root: Path, *extra: str) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--memory-root", str(memory_root), "--json", *extra],
        capture_output=True, text=True, timeout=120,
    )
    try:
        return proc.returncode, json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"도구 출력이 JSON 이 아니다:\n{proc.stdout}\n{proc.stderr}")


# ---------------------------------------------------------------------------
# cases
# ---------------------------------------------------------------------------
def case_1_open_task_judgment(root: Path) -> None:
    d = _branch_memory(root, "feat/mixed", statuses=["done", "planned", None, "blocked"])
    found = dict(open_tasks(d))
    assert "TASK-2026-01-01-x-001" not in found, f"done 을 미완료로 봤다: {found}"
    assert found.get("TASK-2026-01-01-x-002") == "planned", found
    assert found.get("TASK-2026-01-01-x-003") == "(미기재)", (
        f"status 미기재는 미완료로 봐야 한다 (모르는 것을 끝난 것으로 세면 그게 소실): {found}"
    )
    assert found.get("TASK-2026-01-01-x-004") == "blocked", found


def case_2_open_tasks_block(root: Path) -> None:
    _branch_memory(root, "feat/open", statuses=["done", "planned"])
    rc, out = _run_tool(root, "--apply")
    blocked = [c for c in out["candidates"] if c["action"] == "blocked"]
    assert blocked, f"미완료 task 가 있는데 막지 않았다: {out['candidates']}"
    assert rc != 0, "막았으면 exit 0 이면 안 된다 (CI 가 못 본다)"
    assert (root / "active" / "feat" / "open").is_dir(), "막았는데 옮겼다"
    assert "TASK-2026-01-01-x-002" in blocked[0]["reason"], (
        f"어느 task 때문인지 지목하지 않는다: {blocked[0]['reason']}"
    )


def case_3_allow_open_records_them(root: Path) -> None:
    _branch_memory(root, "feat/forced", statuses=["done", "planned"])
    rc, out = _run_tool(root, "--apply", "--allow-open-tasks")
    assert out["archived"] == 1, out
    meta = json.loads((root / "archived" / "feat" / "forced" / ".archived.json").read_text("utf-8"))
    assert meta["open_task_ids"] == ["TASK-2026-01-01-x-002"], (
        f"강제로 넘긴 미완료를 기록하지 않았다: {meta}"
    )


def case_4_markdown_links_rewritten(root: Path) -> None:
    _branch_memory(root, "feat/linked", statuses=["done"])
    # 이웃 문서가 그 브랜치의 세션 기록을 가리킨다 (상대 경로 — 문자열 치환이 안 통한다)
    neighbor = root / "archived" / "old" / "sessions" / "n.md"
    _write(neighbor, "# 이웃\n\n[세션 기록](../../../active/feat/linked/sessions/s.md) 참조.\n")
    rc, out = _run_tool(root, "--apply")
    assert out["archived"] == 1, out
    text = neighbor.read_text("utf-8")
    link = LINK_RE.search(text).group(1)
    resolved = (neighbor.parent / link).resolve()
    assert resolved.exists(), f"링크가 여전히 깨져 있다: {link!r}"
    # 판정은 **해석된 경로**로 한다. 링크 문자열에 "archived" 가 들어 있길 기대하면
    # 안 된다 — archived/ 안에서 archived/ 를 가리키는 상대 경로에는 그 낱말이 없다.
    assert resolved == (root / "archived" / "feat" / "linked" / "sessions" / "s.md"), (
        f"옮겨진 자리를 가리키지 않는다: {link!r} → {resolved}"
    )


def case_5_state_json_paths_rewritten(root: Path) -> None:
    _branch_memory(root, "feat/statepath", statuses=["done"])
    rc, out = _run_tool(root, "--apply")
    assert out["archived"] == 1, out
    state = json.loads((root / "archived" / "feat" / "statepath" / "state.json").read_text("utf-8"))
    for key, value in state["source_of_truth"].items():
        assert "/active/" not in value, f"{key} 가 사라진 active 경로를 가리킨다: {value}"
        assert "/archived/feat/statepath/" in value, f"{key}: {value}"


def case_6_live_links_untouched(root: Path) -> None:
    """고치는 쪽이 손상이 되면 안 된다 — 살아 있는 링크는 그대로 둔다."""
    live = root / "archived" / "old" / "sessions" / "live.md"
    target = root / "archived" / "old" / "sessions" / "target.md"
    _write(target, "# 대상\n")
    original = "# 살아있음\n\n[대상](./target.md) 과 [외부](https://example.com) 링크.\n"
    _write(live, original)
    out = _rewrite_markdown_links(
        original,
        doc_dir=live.parent,
        old_root=root / "active" / "feat" / "whatever",
        new_root=root / "archived" / "feat" / "whatever",
    )
    assert out == original, f"살아 있는 링크를 건드렸다:\n{out}"


def case_7_self_archived_links_resolve() -> None:
    broken: list[str] = []
    for path in sorted(ARCHIVED_DIR.rglob("*.md")):
        doc_dir = path.parent
        for m in LINK_RE.finditer(path.read_text(encoding="utf-8", errors="replace")):
            link = m.group(1)
            if link.startswith(("http://", "https://", "#", "mailto:")):
                continue
            if not (doc_dir / link.split("#", 1)[0]).exists():
                broken.append(f"{path.relative_to(REPO_ROOT)} → {link}")
    assert not broken, (
        "archived/ 에 깨진 링크가 있다 (아카이브가 이력을 끊었다):\n"
        + "\n".join(f"  {b}" for b in broken)
    )


def case_8_self_archived_state_paths() -> None:
    offenders: list[str] = []
    for path in sorted(ARCHIVED_DIR.rglob("state.json")):
        sot = json.loads(path.read_text(encoding="utf-8")).get("source_of_truth", {})
        for key, value in sot.items():
            if isinstance(value, str) and f"{MEMORY_REL}/active/" in value:
                offenders.append(f"{path.relative_to(REPO_ROOT)} :: {key} = {value}")
    assert not offenders, (
        "archived/ 의 state.json 이 사라진 active 경로를 가리킨다:\n"
        + "\n".join(f"  {o}" for o in offenders)
    )


def case_9_self_no_open_tasks_archived() -> None:
    offenders: list[str] = []
    for meta in sorted(ARCHIVED_DIR.rglob(".archived.json")):
        for tid, status in open_tasks(meta.parent):
            offenders.append(f"{meta.parent.relative_to(REPO_ROOT)} :: {tid} ({status})")
    assert not offenders, (
        "미완료 task 가 archived/ 에 있다 — 어떤 집계도 이걸 읽지 않으므로 소실된다.\n"
        "main 네임스페이스로 이월하거나 닫을 것:\n"
        + "\n".join(f"  {o}" for o in offenders)
    )


def case_10_carried_over_is_resolved(root: Path) -> None:
    """브랜치는 끝났는데 일은 안 끝난 경우 — `done` 으로 적으면 거짓이다."""
    d = _branch_memory(root, "feat/carried", statuses=["planned"])
    task = d / "backlog" / "tasks" / "TASK-2026-01-01-x-001.md"
    assert open_tasks(d), "전제가 성립하지 않는다 (planned 인데 미완료로 안 잡힌다)"

    text = task.read_text("utf-8").replace(
        "status: planned\n", "status: planned\ncarried_over_to: TASK-2026-01-01-main-009\n", 1,
    )
    task.write_text(text, encoding="utf-8")
    assert not open_tasks(d), "이관 표기를 인정하지 않는다"

    # 이관 표기가 있으면 아카이브가 막히지 않는다 (end-to-end)
    rc, out = _run_tool(root, "--apply")
    assert out["archived"] == 1 and rc == 0, out
    # 그래도 status 는 planned 그대로다 — 거짓을 적지 않는다
    moved = root / "archived" / "feat" / "carried" / "backlog" / "tasks" / "TASK-2026-01-01-x-001.md"
    assert "status: planned" in moved.read_text("utf-8"), "이관을 done 으로 바꿔 적었다"


def _in_tmp(fn) -> None:
    with tempfile.TemporaryDirectory(prefix="check-archive-integrity-") as tmp:
        fn(Path(tmp).resolve())  # macOS /private symlink


def main() -> int:
    # **케이스마다 root 를 새로 판다.** 공유하면 앞 케이스가 남긴 브랜치가 뒤 케이스의
    # 판정에 섞인다 (실측: --allow-open-tasks 케이스가 3건을 아카이브했다).
    for case in (
        case_1_open_task_judgment,
        case_2_open_tasks_block,
        case_3_allow_open_records_them,
        case_4_markdown_links_rewritten,
        case_5_state_json_paths_rewritten,
        case_6_live_links_untouched,
        case_10_carried_over_is_resolved,
    ):
        _in_tmp(case)
    case_7_self_archived_links_resolve()
    case_8_self_archived_state_paths()
    case_9_self_no_open_tasks_archived()
    print("archive history integrity check passed (10 cases)")
    return 0


def test_case_1() -> None:
    _in_tmp(case_1_open_task_judgment)


def test_case_2() -> None:
    _in_tmp(case_2_open_tasks_block)


def test_case_3() -> None:
    _in_tmp(case_3_allow_open_records_them)


def test_case_4() -> None:
    _in_tmp(case_4_markdown_links_rewritten)


def test_case_5() -> None:
    _in_tmp(case_5_state_json_paths_rewritten)


def test_case_6() -> None:
    _in_tmp(case_6_live_links_untouched)


def test_case_7() -> None:
    case_7_self_archived_links_resolve()


def test_case_8() -> None:
    case_8_self_archived_state_paths()


def test_case_9() -> None:
    case_9_self_no_open_tasks_archived()


def test_case_10() -> None:
    _in_tmp(case_10_carried_over_is_resolved)


if __name__ == "__main__":
    raise SystemExit(main())
