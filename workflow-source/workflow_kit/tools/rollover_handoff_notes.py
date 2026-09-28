#!/usr/bin/env python3
"""handoff §5 의 누적형 절을 예산까지 줄이고 나머지를 `lessons.md` / `sessions/` 로 **이관**한다.

## 왜 필요한가 (ADR-029, M-017/WBS-17.3)

handoff §5 는 세션마다 `### N차가 남긴 규칙` · `### 무엇이 끝났나` 같은 절이 위에 쌓이고
**줄어드는 경로가 없었다** — 8/12 2.7KB → 9/28 59KB. 8/08 에 손으로 99KB → 6KB 로 줄인
handoff 는 7주 만에 82KB 로 돌아왔다. 예산(`common.context_budget`)이 초과를 알리고, 이
도구가 그 출구다.

## 계약 (`core/session_context_budget_spec.md` §3 — `rollover-baselines` 와 같은 모양)

- 현재형 절(`HANDOFF_S5_CURRENT_SECTIONS`)은 옮기지 않는다. 누적형 절을 **아래(오래된 것)부터**
  옮기고, 남은 누적형 합이 예산 이하가 되면 멈춘다.
- `### N차가 남긴 규칙` → 브랜치 디렉터리의 `lessons.md`, 그 밖 → `sessions/handoff-notes_<이관일>.md`.
  블록은 **바이트 그대로** 옮기고, 대상 파일에는 newest-first 로 앞에 붙인다.
- §5 서두(첫 `###` 앞, 현재형)에 이관처를 가리키는 **포인터 줄이 정확히 하나** 남는다. 건수는
  대상 파일의 실제 `###` 절 수다 — 이번 실행분이 아니다.
- 기본은 계획만 낸다. `--apply` 로 쓴다. 멱등 — 예산 이하이고 포인터가 정상이면 no-op.
- 이관은 삭제가 아니다: 옮긴 산문은 다른 어디에도 없다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.context_budget import (  # noqa: E402
    BUDGETS_BY_KEY,
    S5Block,
    section_span,
    split_s5_blocks,
)

LESSONS_FILENAME = "lessons.md"
NOTES_PREFIX = "handoff-notes_"
_POINTER_PREFIX = "- 누적 기록은"
_RULES_TITLE = re.compile(r"^\d+차가 남긴 규칙")
DEFAULT_LIMIT = BUDGETS_BY_KEY["handoff_s5_accumulated"].limit_bytes


def is_rules_block(block: S5Block) -> bool:
    return bool(_RULES_TITLE.match(block.title.strip()))


def plan(handoff_text: str, *, limit: int = DEFAULT_LIMIT) -> dict:
    """이관 계획 — 파일을 읽거나 쓰지 않는다 (fixture 로 계약을 재기 위해)."""
    blocks = split_s5_blocks(handoff_text)
    acc_idx = [i for i, b in enumerate(blocks) if not b.current]
    remaining = sum(blocks[i].size for i in acc_idx)
    moved_idx: list[int] = []
    for i in reversed(acc_idx):        # 아래(오래된 것)부터
        if remaining <= limit:
            break
        moved_idx.append(i)
        remaining -= blocks[i].size
    moved_idx.reverse()                # 원래 순서(최신이 위)로
    moved = [blocks[i] for i in moved_idx]
    head = blocks[0].text if blocks and blocks[0].title == "(서두)" else ""
    pointer_count = sum(1 for ln in head.splitlines() if ln.startswith(_POINTER_PREFIX))
    return {
        "limit": limit,
        "accumulated_before": sum(blocks[i].size for i in acc_idx),
        "accumulated_after": remaining,
        "moved_titles": [b.title for b in moved],
        "moved_count": len(moved),
        "needs_rollover": bool(moved),
        "pointer_count": pointer_count,
        "needs_pointer_fix": pointer_count > 1,
        "_moved": moved,
        "_moved_idx": moved_idx,
    }


def _strip_header(text: str) -> str:
    """대상 파일에서 머리말(첫 `## ` 앞)을 걷고 본문만."""
    lines = text.split("\n")
    while lines and not lines[0].startswith("## "):
        lines.pop(0)
    return "\n".join(lines).strip("\n")


def count_blocks(text: str) -> int:
    return sum(1 for ln in text.split("\n") if ln.startswith("### "))


_LESSONS_HEADER = """# Lessons (rolled off from handoff §5)

- 문서 목적: `session_handoff.md` §5 에서 이관된 `N차가 남긴 규칙` 절을 보존한다.
- 범위: 세션이 남긴 재발 방지 규칙 (최신이 위)
- 대상 독자: AI agent, 저장소 관리자
- 상태: append-only
- 관련 문서: [session_handoff.md](./session_handoff.md)

> 이 파일은 **읽기 대상이 아니라 조회 대상**이다. 세션 시작에 읽지 않는다 — 비슷한 작업을
> 시작할 때 찾아본다. 오래 살아남을 교훈은 `memory_index` 로 승격한다.

"""

_NOTES_HEADER = """# Handoff notes (rolled off from handoff §5)

- 문서 목적: `session_handoff.md` §5 에서 이관된 누적 기록(완료 기록 · 지난 계획 · 닫힌 안건)을 보존한다.
- 범위: 이관일 {today} 의 이관분
- 대상 독자: AI agent, 저장소 관리자
- 상태: append-only
- 관련 문서: [session_handoff.md](../session_handoff.md)

"""


def _prepend(path: Path, header: str, blocks: list[S5Block], today: str) -> None:
    section = [f"## 이관 {today}", ""]
    for b in blocks:
        section.append(b.text.rstrip("\n"))
        section.append("")
    body = "\n".join(section).rstrip("\n")
    prev = _strip_header(path.read_text(encoding="utf-8")) if path.is_file() else ""
    if prev:
        body = body + "\n\n" + prev
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + body + "\n", encoding="utf-8")


def _pointer(lessons: int, notes: int) -> str:
    return (
        f"{_POINTER_PREFIX} [`{LESSONS_FILENAME}`](./{LESSONS_FILENAME}) (규칙 {lessons}절) · "
        f"[`sessions/{NOTES_PREFIX}*.md`](./sessions/) (기록 {notes}절) 로 이관됐다 — 최신이 위, "
        "세션 시작에 읽지 않는다."
    )


def rewrite_s5(handoff_text: str, moved_idx: list[int], pointer: str) -> str:
    """§5 에서 옮긴 절(`split_s5_blocks` 의 인덱스)을 걷고, 서두의 포인터를 정확히 하나로 맞춘다.

    인덱스로 가른다 — 본문 대조로 고르면 같은 본문의 두 절 중 엉뚱한 쪽을 걷는다.
    """
    span = section_span(handoff_text, 5)
    assert span is not None
    blocks = split_s5_blocks(handoff_text)
    # 서두는 늘 있다 — `## 5.` 제목 줄이 첫 `###` 앞에 있기 때문이다.
    has_head = bool(blocks) and blocks[0].title == "(서두)"
    head = blocks[0].text if has_head else ""
    drop = set(moved_idx)
    kept = [b.text for i, b in enumerate(blocks) if i not in drop and not (has_head and i == 0)]
    head_lines = [ln for ln in head.rstrip("\n").split("\n") if not ln.startswith(_POINTER_PREFIX)]
    while head_lines and not head_lines[-1].strip():
        head_lines.pop()
    new_head = "\n".join(head_lines + ["", pointer, "", ""])
    body = "".join(kept)
    if body and not body.endswith("\n"):
        body += "\n"
    return handoff_text[: span[0]] + new_head + body + handoff_text[span[1]:]


def run(handoff_path: Path, *, limit: int, apply: bool, today: str) -> dict:
    text = handoff_path.read_text(encoding="utf-8")
    p = plan(text, limit=limit)
    moved: list[S5Block] = p.pop("_moved")
    moved_idx: list[int] = p.pop("_moved_idx")
    branch_dir = handoff_path.parent
    lessons_path = branch_dir / LESSONS_FILENAME
    notes_path = branch_dir / "sessions" / f"{NOTES_PREFIX}{today}.md"
    to_lessons = [b for b in moved if is_rules_block(b)]
    to_notes = [b for b in moved if not is_rules_block(b)]
    lessons_before = count_blocks(lessons_path.read_text(encoding="utf-8")) if lessons_path.is_file() else 0
    notes_before = sum(
        count_blocks(f.read_text(encoding="utf-8"))
        for f in (branch_dir / "sessions").glob(f"{NOTES_PREFIX}*.md")
    ) if (branch_dir / "sessions").is_dir() else 0
    result = {
        **p,
        "handoff_path": str(handoff_path),
        "lessons_path": str(lessons_path),
        "notes_path": str(notes_path),
        "to_lessons": len(to_lessons),
        "to_notes": len(to_notes),
        "applied": False,
    }
    if not p["needs_rollover"] and not p["needs_pointer_fix"]:
        result["status"] = "ok"
        result["message"] = f"§5 누적형 {p['accumulated_before']:,}B ≤ 예산 {limit:,}B — 옮길 것이 없다."
        return result
    pointer = _pointer(lessons_before + len(to_lessons), notes_before + len(to_notes))
    result["status"] = "ok"
    result["message"] = (
        f"§5 누적형 {p['accumulated_before']:,}B → {p['accumulated_after']:,}B, "
        f"{len(moved)}절 이관 (규칙 {len(to_lessons)} → {LESSONS_FILENAME}, 기록 {len(to_notes)} → sessions/)."
        if moved else f"옮길 것은 없고 포인터 {p['pointer_count']}줄을 1줄로 접는다."
    )
    if not apply:
        return result
    if to_lessons:
        _prepend(lessons_path, _LESSONS_HEADER, to_lessons, today)
    if to_notes:
        _prepend(notes_path, _NOTES_HEADER.format(today=today), to_notes, today)
    handoff_path.write_text(rewrite_s5(text, moved_idx, pointer), encoding="utf-8")
    result["applied"] = True
    return result


def _discover_handoff() -> Path | None:
    from workflow_kit.common.paths import discover_project_profile_path, workflow_handoff_path
    profile = discover_project_profile_path()
    return workflow_handoff_path(profile) if profile is not None else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--handoff-path", type=Path, default=None,
                    help="미지정 시 cwd 상위의 PROJECT_PROFILE.md 로 현재 브랜치 handoff 를 찾는다")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                    help=f"§5 누적형 합 상한 (바이트, 기본 = 예산 정본 {DEFAULT_LIMIT})")
    ap.add_argument("--today", default=date.today().isoformat())
    ap.add_argument("--apply", action="store_true", help="실제로 옮긴다 (기본: 계획만)")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args(argv)

    handoff = args.handoff_path or _discover_handoff()
    if handoff is None or not handoff.is_file():
        print(f"[error] handoff 부재: {handoff}", file=sys.stderr)
        return 2
    if args.limit < 0:
        print("[error] --limit 은 0 이상이어야 한다.", file=sys.stderr)
        return 2
    if section_span(handoff.read_text(encoding="utf-8"), 5) is None:
        print(f"[error] handoff 에 §5 가 없다: {handoff}", file=sys.stderr)
        return 2

    result = run(handoff, limit=args.limit, apply=args.apply, today=args.today)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["message"])
        pending = result["needs_rollover"] or result["needs_pointer_fix"]
        if pending and not result["applied"]:
            print("  → 실제 반영: --apply")
        elif result["applied"]:
            print(f"  WROTE: {result['handoff_path']}")
            if result["to_lessons"]:
                print(f"  WROTE: {result['lessons_path']}")
            if result["to_notes"]:
                print(f"  WROTE: {result['notes_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
