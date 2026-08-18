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
- 포인터 줄은 §1 에 **정확히 하나**다. 이미 있으면 덧붙이지 않고 건수만 갱신하고,
  여러 줄이 쌓여 있으면 하나로 접는다 (2026-08-18 실측: 47차에 6회 실행하자 포인터가
  7줄 → 13줄이 됐다. handoff §1 은 매 세션 시작에 읽히는 자리라 노이즈가 선형으로 는다).
- 포인터의 이관 건수는 이번 실행분이 아니라 **`baselines.md` 의 실제 항목 수**다.
  누적이 아니면 두 번째 실행부터 숫자가 거짓말을 한다.
- 멱등이다. 상한 이하이고 포인터도 정상이면 no-op.
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


def _is_pointer(line: str) -> bool:
    """이관처를 가리키는 줄인가.

    `- 그 이전 기준선은 …` 이라 라벨(`- 그 이전 기준선:`)과 **조사 한 글자만 다르다**.
    :func:`_is_baseline` 은 콜론을 요구하므로 둘은 겹치지 않는다.
    """
    return line.startswith(_POINTER_PREFIX)


def count_archived(baselines_text: str) -> int:
    """`baselines.md` 본문의 이관 항목 수.

    포인터가 말하는 건수의 **정본은 이 파일**이지 직전 실행의 이관 수가 아니다.
    헤더의 메타 불릿(`- 문서 목적:` 등)은 첫 `## ` 앞에 있으므로 걷어낸다.
    """
    lines = baselines_text.split("\n")
    while lines and not lines[0].startswith("## "):
        lines.pop(0)
    return sum(1 for ln in lines if ln.startswith("- "))


def _body_of(line: str) -> str:
    """`- <라벨>: <본문>` 에서 본문만."""
    return line.split(":", 1)[1].lstrip()


def _blocks(lines: list[str]) -> list[tuple[int, int]]:
    """기준선 **블록** 목록 — `(시작, 끝exclusive)`.

    기준선은 한 줄이 아니다. 실제 handoff 는 `- 그 이전 기준선: …` 밑에 들여쓴 하위
    불릿을 여러 줄 달고 있다 (2026-08-14 실측: 그 사실을 놓친 첫 구현이 첫 줄만 옮겨
    **하위 줄을 §1 에 고아로 남겼다**). 블록은 다음 비들여쓰기 줄 직전까지다.
    """
    starts = [i for i, ln in enumerate(lines) if _is_baseline(ln)]
    out: list[tuple[int, int]] = []
    for s in starts:
        e = s + 1
        while e < len(lines) and (lines[e].startswith((" ", "\t")) or not lines[e].strip()):
            # 빈 줄만 이어지다 비들여쓰기 줄이 오면 그 빈 줄은 블록에 넣지 않는다.
            if not lines[e].strip():
                nxt = e + 1
                while nxt < len(lines) and not lines[nxt].strip():
                    nxt += 1
                if nxt >= len(lines) or not lines[nxt].startswith((" ", "\t")):
                    break
            e += 1
        out.append((s, e))
    return out


def plan(handoff_text: str, *, cap: int = BASELINE_ITEMS_CAP) -> dict:
    """이관 계획. 파일을 읽거나 쓰지 않는다 (fixture 로 계약을 재기 위해)."""
    lines = handoff_text.split("\n")
    blocks = _blocks(lines)
    kept, moved = blocks[:cap], blocks[cap:]
    pointer_count = sum(1 for ln in lines if _is_pointer(ln))
    return {
        "total": len(blocks),
        "cap": cap,
        "kept_count": len(kept),
        "moved_count": len(moved),
        "moved_bodies": ["\n".join([_body_of(lines[s])] + lines[s + 1:e]).rstrip()
                         for s, e in moved],
        "needs_rollover": bool(moved),
        "pointer_count": pointer_count,
        # 옮길 게 없어도 포인터가 쌓여 있으면 접어야 한다 — 그래서 별도 신호다.
        "needs_pointer_fix": pointer_count > 1,
    }


def apply_rollover(
    handoff_text: str, *, cap: int = BASELINE_ITEMS_CAP, pointer: str,
) -> tuple[str, list[str]]:
    """(새 handoff 본문, 옮긴 본문 목록). 옮길 것도 접을 것도 없으면 원문 그대로.

    포인터 줄은 **먼저 전부 걷어내고 하나만 다시 넣는다**. 그래서 이 함수는 옮길 게
    없어도 이미 쌓인 포인터를 하나로 접는다 — 상한 이하가 됐다고 no-op 로 빠지면
    쌓인 상태가 영원히 안 고쳐진다.
    """
    lines = handoff_text.split("\n")
    blocks = _blocks(lines)
    pointer_spans = [(i, i + 1) for i, ln in enumerate(lines) if _is_pointer(ln)]
    kept, moved = blocks[:cap], blocks[cap:]
    if not moved and len(pointer_spans) <= 1:
        return handoff_text, []

    moved_bodies = ["\n".join([_body_of(lines[s])] + lines[s + 1:e]).rstrip()
                    for s, e in moved]

    # 남는 블록의 라벨을 위치에 맞게 다시 붙인다 (첫 줄만).
    for position, (s, _e) in enumerate(kept):
        lines[s] = f"- {_baseline_label(position)}: {_body_of(lines[s])}"

    # 옮긴 블록은 **통째로** 지운다 — 첫 줄만 지우면 하위 줄이 고아로 남는다.
    # 기존 포인터 줄도 함께 걷는다. 둘은 겹치지 않으므로 뒤에서부터 지우면 된다.
    for s, e in sorted(moved + pointer_spans, reverse=True):
        del lines[s:e]
    # 삭제로 인덱스가 밀렸다 — 남은 블록에서 삽입 위치를 **다시** 구한다.
    remaining = _blocks(lines)
    insert_at = remaining[-1][1] if remaining else len(lines)
    lines.insert(insert_at, pointer)
    return "\n".join(lines), moved_bodies


def render_baselines_prepend(moved: list[str], *, today: str) -> str:
    """`baselines.md` 앞에 붙일 블록. 앞이 최신이다."""
    head = [f"## 롤오프 {today}", ""]
    for body in moved:
        first, _, rest = body.partition("\n")
        head.append(f"- {first}")
        if rest:
            head.append(rest)
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
    # 포인터가 말할 건수의 정본은 `baselines.md` 다 — 이번 이관분이 아니라 누적이다.
    archived_before = (
        count_archived(baselines_path.read_text(encoding="utf-8"))
        if baselines_path.is_file() else 0
    )
    result["archived_before"] = archived_before
    result["archived_total"] = archived_before + result["moved_count"]
    if not result["needs_rollover"] and not result["needs_pointer_fix"]:
        result["status"] = "ok"
        result["message"] = f"기준선 {result['total']}줄 ≤ 상한 {cap} — 옮길 것이 없다."
        return result

    pointer = (
        f"{_POINTER_PREFIX} [`{BASELINES_FILENAME}`](./{BASELINES_FILENAME}) 에 있다 "
        f"(이관 {result['archived_total']}건, 최신이 위)."
    )
    new_text, moved = apply_rollover(text, cap=cap, pointer=pointer)
    result["status"] = "ok"
    if moved:
        result["message"] = (
            f"기준선 {result['total']}줄 → {cap}줄, {len(moved)}건을 "
            f"{BASELINES_FILENAME} 로 이관한다."
        )
    else:
        result["message"] = (
            f"기준선 {result['total']}줄 ≤ 상한 {cap} — 옮길 것은 없고 "
            f"포인터 {result['pointer_count']}줄을 1줄로 접는다."
        )
    if not apply:
        return result

    # 포인터만 접는 경우엔 이관할 산문이 없다 — `baselines.md` 는 건드리지 않는다.
    if moved:
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
        baselines_path.write_text(
            _HEADER.format(cap=cap) + body.rstrip("\n") + "\n", encoding="utf-8")
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
        pending = result["needs_rollover"] or result["needs_pointer_fix"]
        if pending and not result["applied"]:
            print("  → 실제 반영: --apply")
        elif result["applied"]:
            print(f"  WROTE: {result['handoff_path']}")
            if result["moved_count"]:
                print(f"  WROTE: {result['baselines_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
