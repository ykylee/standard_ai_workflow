#!/usr/bin/env python3
"""handoff §1 의 기준선 줄을 상한까지 줄이고 나머지를 `baselines.md` 로 **이관**한다.

## 왜 필요한가

`session_handoff.md` §1 은 세션마다 기준선 한 줄이 앞에 붙는다. 줄은 길고(평균 785자,
최대 2,082자) 지워지지 않으므로 handoff 는 **단조 증가**한다. 2026-08-14 실측:

| | |
|---|---|
| handoff 전체 | 41,880자 / 25,373 토큰 |
| §1 기준선 37줄 | **27,502자 (66%)** |

그리고 그 전부가 세션 시작마다 읽힌다 (`CLAUDE.md` + `state.json` + handoff ≈ 36K 토큰).

## 왜 '자르기' 가 아니라 '이관' 인가

완료 목록 상한(:data:`~workflow_kit.common.project_docs.RECENT_DONE_ITEMS_CAP`)은 넘치는
줄을 **버린다**. 그래도 되는 이유는 그 사실의 SSOT 가 `backlog/tasks/` 에 따로 있기
때문이다. 기준선 줄은 다르다 — **그 산문은 다른 어디에도 없다.** 버리면 세션 이력이
조용히 사라진다. 그래서 상한을 넘는 줄은 `baselines.md` 로 옮기고, handoff 에는 그
파일을 가리키는 한 줄을 남긴다.

같은 이유로 이 도구는 **파괴적이지 않다**: 옮길 대상이 없으면 아무것도 쓰지 않고,
`--apply` 없이는 계획만 출력한다.

## 계약

- 앞이 최신이다 — `현재 기준선` → `직전 기준선` → `그 이전 기준선`(여러 줄) 순.
- 상한 안에 남는 줄의 **라벨은 재작성한다**: 남은 것이 3줄이면 `현재` / `직전` /
  `그 이전`. 라벨이 어긋나면 사람이 읽을 때 순서를 오해한다.
- `baselines.md` 는 **newest-first append** 다. 이번에 옮긴 줄이 기존 내용 앞에 붙는다.
- 멱등이다. 상한 이하이면 no-op.
- `state.json` 생성기는 §1 의 **첫 `현재 기준선`** 만 읽으므로(``project_docs.get_value``)
  이관은 생성물에 영향이 없다. 그 사실은 `check_handoff_baseline_cap` 이 확인한다.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.project_docs import (  # noqa: E402
    BASELINE_ITEMS_CAP,
    BASELINE_LABELS,
    BASELINES_FILENAME,
)

_POINTER_PREFIX = "- 그 이전 기준선은"


def _baseline_label(index: int) -> str:
    """0-based 위치 → 라벨. 두 번째 이후는 전부 `그 이전 기준선`."""
    if index < len(BASELINE_LABELS) - 1:
        return BASELINE_LABELS[index]
    return BASELINE_LABELS[-1]


def _is_baseline(line: str) -> bool:
    return any(line.startswith(f"- {label}:") for label in BASELINE_LABELS)


def _body_of(line: str) -> str:
    """`- <라벨>: <본문>` 에서 본문만."""
    return line.split(":", 1)[1].lstrip()


def plan(handoff_text: str, *, cap: int = BASELINE_ITEMS_CAP) -> dict:
    """이관 계획. 파일을 읽거나 쓰지 않는다 (fixture 로 계약을 재기 위해)."""
    lines = handoff_text.split("\n")
    idx = [i for i, ln in enumerate(lines) if _is_baseline(ln)]
    kept, moved = idx[:cap], idx[cap:]
    return {
        "total": len(idx),
        "cap": cap,
        "kept_count": len(kept),
        "moved_count": len(moved),
        "moved_bodies": [_body_of(lines[i]) for i in moved],
        "needs_rollover": bool(moved),
    }


def apply_rollover(
    handoff_text: str, *, cap: int = BASELINE_ITEMS_CAP, pointer: str,
) -> tuple[str, list[str]]:
    """(새 handoff 본문, 옮긴 본문 목록). 옮길 게 없으면 원문 그대로."""
    lines = handoff_text.split("\n")
    idx = [i for i, ln in enumerate(lines) if _is_baseline(ln)]
    if len(idx) <= cap:
        return handoff_text, []

    kept_idx, moved_idx = idx[:cap], idx[cap:]
    moved_bodies = [_body_of(lines[i]) for i in moved_idx]

    # 남는 줄의 라벨을 위치에 맞게 다시 붙인다.
    for position, i in enumerate(kept_idx):
        lines[i] = f"- {_baseline_label(position)}: {_body_of(lines[i])}"

    # 옮긴 줄은 지우고, 마지막으로 남은 기준선 바로 뒤에 포인터 한 줄을 둔다.
    for i in reversed(moved_idx):
        del lines[i]
    insert_at = kept_idx[-1] + 1
    lines.insert(insert_at, pointer)
    return "\n".join(lines), moved_bodies


def render_baselines_prepend(moved: list[str], *, today: str) -> str:
    """`baselines.md` 앞에 붙일 블록. 앞이 최신이다."""
    head = [f"## 롤오프 {today}", ""]
    head += [f"- {body}" for body in moved]
    head.append("")
    return "\n".join(head)


_HEADER = """# Baselines (rolled off)

- 문서 목적: `session_handoff.md` §1 에서 롤오프된 기준선 줄을 이력으로 보존한다.
- 범위: 과거 세션의 기준선 산문 (최신이 위)
- 대상 독자: AI agent, 저장소 관리자
- 상태: append-only
- 관련 문서: [session_handoff.md](./session_handoff.md)

> 이 파일은 **읽기 대상이 아니라 조회 대상**이다. 세션 시작에 읽지 않는다 —
> handoff §1 이 최근 {cap}개만 들고 있고, 그 이전이 필요할 때만 여기를 본다.

"""


def run(handoff_path: Path, *, cap: int, apply: bool, today: str) -> dict:
    text = handoff_path.read_text(encoding="utf-8")
    result = plan(text, cap=cap)
    baselines_path = handoff_path.parent / BASELINES_FILENAME
    result["handoff_path"] = str(handoff_path)
    result["baselines_path"] = str(baselines_path)
    result["applied"] = False
    if not result["needs_rollover"]:
        result["status"] = "ok"
        result["message"] = f"기준선 {result['total']}줄 ≤ 상한 {cap} — 옮길 것이 없다."
        return result

    pointer = (
        f"{_POINTER_PREFIX} [`{BASELINES_FILENAME}`](./{BASELINES_FILENAME}) 에 있다 "
        f"(이관 {result['moved_count']}건, 최신이 위)."
    )
    new_text, moved = apply_rollover(text, cap=cap, pointer=pointer)
    result["status"] = "ok"
    result["message"] = (
        f"기준선 {result['total']}줄 → {cap}줄, {len(moved)}건을 "
        f"{BASELINES_FILENAME} 로 이관한다."
    )
    if not apply:
        return result

    # 기존 파일에서 **헤더를 걷고 본문만** 남긴다 — 아래에서 헤더를 다시 얹는다.
    # (헤더가 여러 번 쌓이면 그 자체가 이 파일의 오염이다.)
    prev = ""
    if baselines_path.is_file():
        prev_lines = baselines_path.read_text(encoding="utf-8").split("\n")
        while prev_lines and not prev_lines[0].startswith("## "):
            prev_lines.pop(0)
        prev = "\n".join(prev_lines).strip("\n")
    body = render_baselines_prepend(moved, today=today)
    if prev:
        body = body.rstrip("\n") + "\n\n" + prev
    baselines_path.write_text(_HEADER.format(cap=cap) + body.rstrip("\n") + "\n", encoding="utf-8")
    handoff_path.write_text(new_text, encoding="utf-8")
    result["applied"] = True
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--handoff-path", required=True, type=Path)
    p.add_argument("--cap", type=int, default=BASELINE_ITEMS_CAP)
    p.add_argument("--today", default=date.today().isoformat())
    p.add_argument("--apply", action="store_true", help="실제로 옮긴다 (기본: 계획만)")
    p.add_argument("--json", action="store_true", dest="as_json")
    args = p.parse_args(argv)

    if not args.handoff_path.is_file():
        print(f"[error] handoff 부재: {args.handoff_path}", file=sys.stderr)
        return 2
    if args.cap < 1:
        print("[error] --cap 은 1 이상이어야 한다 — 0 은 현재 기준선까지 지운다.", file=sys.stderr)
        return 2

    result = run(args.handoff_path, cap=args.cap, apply=args.apply, today=args.today)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["message"])
        if result["needs_rollover"] and not result["applied"]:
            print("  → 실제 이관: --apply")
        elif result["applied"]:
            print(f"  WROTE: {result['handoff_path']}")
            print(f"  WROTE: {result['baselines_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
