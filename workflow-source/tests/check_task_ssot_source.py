#!/usr/bin/env python3
"""task 레코드의 **읽는 쪽 계약**을 고정한다 (10 cases).

## 계보 — 같은 필드에 소스가 둘, 그리고 index 방언이 셋

2026-08-14 실측으로 두 가지가 드러났다.

**(1) `status` 의 소스가 둘이었다.** 아카이브 도구와 축 분리 검사는 frontmatter 의
`status:` 를 읽고, backlog 파서는 본문의 `- 상태:` 를 읽었다. 277개 task 중
**105개(38%)에 본문 줄이 아예 없었고** — legacy 마이그레이션 산출물이다 — 그 task 들은
파서에게 *상태 없음* 이었다. 불일치는 0건이었지만 **부재가 문제였다.**

**(2) daily index 가 task 를 가리키는 방언이 셋이었다.**

| 방언 | 모양 | 파서가 봤나 |
|---|---|---|
| 링크 (신형) | ``path: [`./tasks/X.md`](./tasks/X.md)`` | ✅ |
| 백틱 (v0.14.0 마이그레이션) | ``path: `backlog/tasks/X.md` `` | ❌ |
| 인라인 (legacy 분할) | `path:` 자체가 없음 | ❌ |

`active/main` 의 daily index **20개가 task 를 0개로 읽고 있었다.** 파일은 그대로
있는데 어느 목록에도 안 나타났다. 그 0 은 "그 날 한 일이 없다" 로 읽힌다.

게다가 index 부재 시의 fallback 은 glob 패턴이 `<stem>_*.md` 였다 — 실제 파일명은
`TASK-<date>[-<slug>]-<NNN>.md` 라 **아무것도 매칭하지 않았다.** 있으나 마나인 채로
드러난 적이 없다.

## 이 검사가 재는 방향

자기 적용(case 8~10)만 두면 corpus 가 깨끗해지는 순간 무력화돼도 green 이다. 그래서
fixture 로 **세 방언과 두 소스를 각각** 재고(case 1~7), 자기 적용은 실물의 현재
상태를 잰다.

10 cases:
  1) frontmatter 가 본문과 다르면 **frontmatter 가 이긴다**
  2) 본문에 상태가 없어도 frontmatter 로 읽힌다
  3) frontmatter 가 없으면 본문으로 읽는다 (legacy 호환)
  4) 링크 방언 해석
  5) 백틱 방언 해석
  6) 인라인 방언 — `tasks/` glob fallback
  7) glob 패턴이 실제 파일명(`TASK-<date>-<NNN>.md`)을 잡는다
  8) 자기 적용 — task 0개로 읽히는 daily index 가 없다
  9) 자기 적용 — 읽힌 task 중 상태 없는 것이 없다
 10) 자기 적용 — frontmatter 와 본문이 둘 다 있을 때 어긋나지 않는다
"""

from __future__ import annotations

import glob as _glob
import re
import sys
import tempfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = TESTS_DIR.parent
REPO_ROOT = SOURCE_ROOT.parent
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.project_docs import parse_backlog  # noqa: E402

FAILURES: list[str] = []

_FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_FM_STATUS = re.compile(r"^status:\s*(\S+)\s*$", re.M)
_BODY_STATUS = re.compile(r"^- 상태:\s*(\S+)\s*$", re.M)


def _backlog_dir(root: Path) -> Path:
    """실물과 **같은 모양**으로 판다 — `<...>/backlog/` 아래에 index 와 `tasks/`.

    처음엔 root 바로 아래에 뒀는데, 구형 index 의 백틱 경로는 저장소 상대
    (`backlog/tasks/X.md`)라 그 모양에서만 해석된다. fixture 가 실물을 안 닮으면
    case 는 통과하고 실물만 안 읽힌다 (2026-08-14, 같은 실수 두 번째).
    """
    d = root / "backlog"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _task_file(root: Path, name: str, *, fm_status: str | None, body_status: str | None,
               title: str = "제목") -> Path:
    tasks = _backlog_dir(root) / "tasks"
    tasks.mkdir(parents=True, exist_ok=True)
    head = ""
    if fm_status is not None:
        head = f"---\nid: {name}\nstatus: {fm_status}\nkind: generic\n---\n\n"
    body = f"# {name} — {title}\n\n## 📝 Description\n\n"
    if body_status is not None:
        body += f"- 상태: {body_status}\n"
    body += "- 작업 내용: 무엇.\n"
    p = tasks / f"{name}.md"
    p.write_text(head + body, encoding="utf-8")
    return p


def _index(root: Path, stem: str, entries: str) -> Path:
    p = _backlog_dir(root) / f"{stem}.md"
    p.write_text(f"# Backlog Index — {stem}\n\n## Tasks\n\n{entries}\n", encoding="utf-8")
    return p


def _statuses(idx: Path) -> dict[str, str | None]:
    return {t["task_id"]: t.get("status") for t in parse_backlog(idx)["tasks"]}


def case_1_frontmatter_wins(root: Path) -> None:
    name = "TASK-2026-01-01-001"
    _task_file(root, name, fm_status="done", body_status="planned")
    idx = _index(root, "2026-01-01", f"- **{name}**\n  - path: [`./tasks/{name}.md`](./tasks/{name}.md)")
    assert _statuses(idx)[name] == "done", "본문이 frontmatter 를 이겼다 — 소스가 둘로 남는다"


def case_2_frontmatter_supplies_missing_body(root: Path) -> None:
    name = "TASK-2026-01-02-001"
    _task_file(root, name, fm_status="blocked", body_status=None)
    idx = _index(root, "2026-01-02", f"- **{name}**\n  - path: [`./tasks/{name}.md`](./tasks/{name}.md)")
    assert _statuses(idx)[name] == "blocked", "본문에 상태가 없다고 상태 없음으로 읽었다"


def case_3_body_only_still_works(root: Path) -> None:
    name = "TASK-2026-01-03-001"
    _task_file(root, name, fm_status=None, body_status="in_progress")
    idx = _index(root, "2026-01-03", f"- **{name}**\n  - path: [`./tasks/{name}.md`](./tasks/{name}.md)")
    assert _statuses(idx)[name] == "in_progress", "frontmatter 없는 legacy 를 못 읽는다"


def case_4_link_dialect(root: Path) -> None:
    name = "TASK-2026-01-04-001"
    _task_file(root, name, fm_status="done", body_status="done")
    idx = _index(root, "2026-01-04", f"- **{name}**\n  - path: [`./tasks/{name}.md`](./tasks/{name}.md)")
    assert len(parse_backlog(idx)["tasks"]) == 1, "링크 방언을 못 읽는다"


def case_5_backtick_dialect(root: Path) -> None:
    """**날짜가 다른 파일명**을 쓴다 — 그래야 백틱 해석만으로 통과한다.

    처음엔 index 와 같은 날짜를 썼는데, 그러면 백틱 처리를 통째로 제거해도
    `tasks/` glob fallback 이 같은 파일을 집어 **case 가 그대로 통과했다**
    (2026-08-14 되주입 실측). 자기가 말하는 것을 재지 않는 case 였다.
    """
    name = "TASK-2026-01-99-001"          # index stem(2026-01-05)과 다른 날짜
    _task_file(root, name, fm_status="done", body_status=None)
    idx = _index(root, "2026-01-05", f"- **{name}**\n  - path: `backlog/tasks/{name}.md`")
    got = parse_backlog(idx)["tasks"]
    assert len(got) == 1, f"백틱 방언을 못 읽는다 — 조용한 0 이 된다 (got {len(got)})"


def case_6_inline_dialect_falls_back(root: Path) -> None:
    name = "TASK-2026-01-06-001"
    _task_file(root, name, fm_status="done", body_status=None)
    idx = _index(root, "2026-01-06", f"- **{name}** 인라인으로만 적힌 항목 (path 없음)")
    got = parse_backlog(idx)["tasks"]
    assert len(got) == 1, f"인라인 방언에서 tasks/ fallback 이 안 걸린다 (got {len(got)})"


def case_7_glob_matches_real_naming(root: Path) -> None:
    """fallback glob 이 실제 파일명을 잡는가. `<stem>_*` 는 아무것도 안 잡았다."""
    name = "TASK-2026-01-07-main-001"
    _task_file(root, name, fm_status="done", body_status=None)
    idx = _backlog_dir(root) / "2026-01-07.md"  # index 파일을 만들지 않는다 (부재 fallback)
    got = parse_backlog(idx)["tasks"]
    assert len(got) == 1, f"index 부재 fallback 이 `TASK-<date>-<slug>-<NNN>` 을 못 잡는다 (got {len(got)})"


def _repo_indexes() -> list[Path]:
    return [Path(f) for f in sorted(
        _glob.glob(str(REPO_ROOT / "ai-workflow/memory/**/backlog/2*.md"), recursive=True))]


def case_8_self_no_zero_task_index() -> None:
    zero = []
    for idx in _repo_indexes():
        if not (idx.parent / "tasks").is_dir():
            continue
        if len(parse_backlog(idx)["tasks"]) == 0:
            zero.append(idx.relative_to(REPO_ROOT).as_posix())
    assert not zero, "task 0개로 읽히는 daily index (파일은 있는데 안 보인다):\n  " + "\n  ".join(zero)


def case_9_self_every_task_has_status() -> None:
    """계약은 **layout 이 적용되는 곳에만** 적용된다.

    `tasks/` 형제 디렉터리가 있는 index 만 본다 (v0.14.0 append-only layout). 그것이
    없는 곳은 legacy 인라인 backlog(`memory/release/<version>/`)이고, 그 안의
    `## TASK-...` 섹션은 얼어붙은 릴리스 기록이지 살아 있는 task SSOT 가 아니다.
    이름으로 거르지 않고 **layout 으로** 거르는 이유는, 이름 목록은 새 디렉터리가
    생기면 조용히 사각지대를 만들기 때문이다. case 8 과 같은 기준이다.
    """
    missing = []
    for idx in _repo_indexes():
        if not (idx.parent / "tasks").is_dir():
            continue
        for t in parse_backlog(idx)["tasks"]:
            if not t.get("status"):
                missing.append(f"{idx.name}:{t['task_id']}")
    assert not missing, "상태 없이 읽히는 task:\n  " + "\n  ".join(missing[:20])


def case_10_self_sources_agree() -> None:
    bad = []
    for f in sorted(_glob.glob(str(REPO_ROOT / "ai-workflow/memory/**/backlog/tasks/*.md"),
                               recursive=True)):
        text = Path(f).read_text(encoding="utf-8")
        fm = _FM.match(text)
        if not fm:
            continue
        a = _FM_STATUS.search(fm.group(1))
        b = _BODY_STATUS.search(text[fm.end():])
        if a and b and a.group(1) != b.group(1):
            bad.append(f"{Path(f).name}: frontmatter={a.group(1)} vs 본문={b.group(1)}")
    assert not bad, "두 소스가 어긋난 task:\n  " + "\n  ".join(bad[:20])


def _run(fn, needs_root: bool = True) -> None:
    try:
        if needs_root:
            with tempfile.TemporaryDirectory(prefix="check-task-ssot-") as tmp:
                fn(Path(tmp).resolve())
        else:
            fn()
        print(f"  PASS  {fn.__name__}")
    except AssertionError as e:
        FAILURES.append(fn.__name__)
        print(f"  FAIL  {fn.__name__} — {e}")
    except Exception as e:  # noqa: BLE001
        FAILURES.append(fn.__name__)
        print(f"  FAIL  {fn.__name__} — 예외 {type(e).__name__}: {e}")


def main() -> int:
    print("=== task SSOT 읽는 쪽 계약 ===")
    for fn in (case_1_frontmatter_wins, case_2_frontmatter_supplies_missing_body,
               case_3_body_only_still_works, case_4_link_dialect, case_5_backtick_dialect,
               case_6_inline_dialect_falls_back, case_7_glob_matches_real_naming):
        _run(fn)
    for fn in (case_8_self_no_zero_task_index, case_9_self_every_task_has_status,
               case_10_self_sources_agree):
        _run(fn, needs_root=False)
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    print("\n10/10 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
