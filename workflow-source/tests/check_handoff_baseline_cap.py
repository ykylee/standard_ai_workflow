#!/usr/bin/env python3
"""handoff §1 기준선 롤오프의 계약을 고정한다 (11 cases).

## 계보

`session_handoff.md` §1 은 세션마다 기준선 한 줄이 앞에 붙고 지워지지 않는다. 2026-08-14
실측: 기준선 **37줄이 handoff 41,880자 중 27,502자(66%)** 였고, 그 전부가 세션 시작마다
읽힌다. 완료 목록에는 이미 상한(`RECENT_DONE_ITEMS_CAP`)이 있는데 기준선에는 없었다.

## 이 검사가 재는 것 — 특히 '버리지 않는가'

완료 목록 상한은 넘치는 줄을 **버린다**. 그래도 되는 이유는 SSOT 가 `backlog/tasks/` 에
따로 있기 때문이다. 기준선은 다르다 — **그 산문은 다른 어디에도 없다.** 그래서 이
검사의 중심은 "줄었는가" 가 아니라 **"옮겨졌는가"** 다 (case 3·4). 자르는 구현으로
회귀하면 이력이 조용히 사라지고, 줄 수만 보는 검사는 그걸 통과시킨다.

10 cases:
  1) 상한 이하면 no-op (멱등)
  2) 상한 초과면 handoff 에 정확히 cap 줄만 남는다
  3) **옮긴 줄이 하나도 유실되지 않는다** (본문 대조)
  4) handoff 에 `baselines.md` 를 가리키는 포인터가 남는다
  5) 남은 줄의 라벨이 위치에 맞게 재작성된다 (현재 / 직전 / 그 이전…)
  6) 두 번 적용해도 baselines 헤더가 겹쳐 쌓이지 않는다 (append 는 newest-first)
  7) `--apply` 없이는 디스크를 건드리지 않는다
  8) `--cap 0` 은 거부한다 (현재 기준선까지 지우는 값)
  9) **생성기 입력이 깨지지 않는다** — 롤오프 후에도 `parse_handoff` 가 같은
     `current_baseline` 을 읽는다
 10) 자기 적용 — 현재 브랜치 handoff 가 상한 이하다
 11) **들여쓴 하위 줄까지 통째로** 옮긴다 (첫 줄만 옮기면 고아가 남는다)
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = TESTS_DIR.parent
REPO_ROOT = SOURCE_ROOT.parent
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.project_docs import (  # noqa: E402
    BASELINE_ITEMS_CAP,
    BASELINES_FILENAME,
    parse_handoff,
)
from workflow_kit.tools.rollover_handoff_baselines import (  # noqa: E402
    apply_rollover,
    plan,
    run,
)

FAILURES: list[str] = []

_HANDOFF_HEAD = """# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태
- 대상 독자: AI agent
- 상태: active
- 최종 수정일: 2026-08-14
- 관련 문서: [backlog](./backlog/)

## 1. 현재 작업 요약

"""

_HANDOFF_TAIL = """- 현재 주 작업 축: 축 한 줄.

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
-

## 3. 차단 작업

- 현재 `blocked` 작업:
-

## 4. 최근 완료 작업

- 최근 완료 작업 목록:
-
"""


def _handoff(n: int) -> str:
    """기준선 n 줄을 가진 handoff 본문 (앞이 최신)."""
    labels = ["현재 기준선", "직전 기준선"] + ["그 이전 기준선"] * max(0, n - 2)
    body = "\n".join(f"- {labels[i]}: 세션 {n - i} 의 기준선 산문." for i in range(n))
    return _HANDOFF_HEAD + body + "\n" + _HANDOFF_TAIL


def _write_handoff(root: Path, n: int) -> Path:
    p = root / "session_handoff.md"
    p.write_text(_handoff(n), encoding="utf-8")
    return p


def case_1_under_cap_is_noop(root: Path) -> None:
    p = _write_handoff(root, BASELINE_ITEMS_CAP)
    before = p.read_text(encoding="utf-8")
    res = run(p, cap=BASELINE_ITEMS_CAP, apply=True, today="2026-08-14")
    assert not res["needs_rollover"], res
    assert p.read_text(encoding="utf-8") == before, "상한 이하인데 handoff 를 고쳤다"
    assert not (root / BASELINES_FILENAME).exists(), "옮길 것이 없는데 파일을 만들었다"


def case_2_keeps_exactly_cap(root: Path) -> None:
    p = _write_handoff(root, BASELINE_ITEMS_CAP + 9)
    run(p, cap=BASELINE_ITEMS_CAP, apply=True, today="2026-08-14")
    left = plan(p.read_text(encoding="utf-8"), cap=BASELINE_ITEMS_CAP)
    assert left["total"] == BASELINE_ITEMS_CAP, f"남은 기준선 {left['total']}줄"


def case_3_moved_lines_are_not_lost(root: Path) -> None:
    """**핵심 case.** 자르는 구현으로 회귀하면 여기서 걸린다."""
    n = BASELINE_ITEMS_CAP + 6
    p = _write_handoff(root, n)
    before = plan(p.read_text(encoding="utf-8"), cap=BASELINE_ITEMS_CAP)
    run(p, cap=BASELINE_ITEMS_CAP, apply=True, today="2026-08-14")
    archive = (root / BASELINES_FILENAME).read_text(encoding="utf-8")
    for body in before["moved_bodies"]:
        assert body in archive, f"이관되지 않고 사라진 기준선: {body!r}"


def case_4_pointer_remains(root: Path) -> None:
    p = _write_handoff(root, BASELINE_ITEMS_CAP + 3)
    run(p, cap=BASELINE_ITEMS_CAP, apply=True, today="2026-08-14")
    text = p.read_text(encoding="utf-8")
    assert BASELINES_FILENAME in text, "handoff 에 이관처 포인터가 없다 — 참조가 끊긴다"


def case_5_labels_are_rewritten(root: Path) -> None:
    p = _write_handoff(root, BASELINE_ITEMS_CAP + 5)
    run(p, cap=BASELINE_ITEMS_CAP, apply=True, today="2026-08-14")
    lines = [ln for ln in p.read_text(encoding="utf-8").split("\n") if "기준선:" in ln]
    assert lines[0].startswith("- 현재 기준선:"), lines[0]
    assert lines[1].startswith("- 직전 기준선:"), lines[1]
    for ln in lines[2:]:
        assert ln.startswith("- 그 이전 기준선:"), ln


def case_6_second_run_does_not_stack_headers(root: Path) -> None:
    p = _write_handoff(root, BASELINE_ITEMS_CAP + 4)
    run(p, cap=BASELINE_ITEMS_CAP, apply=True, today="2026-08-14")
    # 다시 기준선을 밀어 넣고 한 번 더 롤오프
    text = p.read_text(encoding="utf-8")
    text = text.replace("## 1. 현재 작업 요약\n\n",
                        "## 1. 현재 작업 요약\n\n- 현재 기준선: 새 세션의 기준선.\n" * 1
                        + "- 현재 기준선: 더 새 세션의 기준선.\n")
    p.write_text(text, encoding="utf-8")
    run(p, cap=BASELINE_ITEMS_CAP, apply=True, today="2026-08-15")
    archive = (root / BASELINES_FILENAME).read_text(encoding="utf-8")
    assert archive.count("# Baselines (rolled off)") == 1, "헤더가 겹쳐 쌓였다"
    assert archive.index("## 롤오프 2026-08-15") < archive.index("## 롤오프 2026-08-14"), (
        "최신이 위가 아니다"
    )


def case_7_plan_only_without_apply(root: Path) -> None:
    p = _write_handoff(root, BASELINE_ITEMS_CAP + 2)
    before = p.read_text(encoding="utf-8")
    res = run(p, cap=BASELINE_ITEMS_CAP, apply=False, today="2026-08-14")
    assert res["needs_rollover"] and not res["applied"], res
    assert p.read_text(encoding="utf-8") == before, "--apply 없이 handoff 를 고쳤다"
    assert not (root / BASELINES_FILENAME).exists(), "--apply 없이 파일을 만들었다"


def case_8_cap_zero_rejected(root: Path) -> None:
    p = _write_handoff(root, 5)
    proc = subprocess.run(
        [sys.executable, "-m", "workflow_kit.tools.rollover_handoff_baselines",
         "--handoff-path", str(p), "--cap", "0", "--apply"],
        cwd=str(SOURCE_ROOT), capture_output=True, text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(SOURCE_ROOT)}, timeout=60,
    )
    assert proc.returncode != 0, "--cap 0 을 받아들였다 — 현재 기준선까지 지운다"


def case_9_generator_input_unchanged(root: Path) -> None:
    """롤오프 후에도 생성기가 **같은** `current_baseline` 을 읽는다."""
    p = _write_handoff(root, BASELINE_ITEMS_CAP + 7)
    before = parse_handoff(p)["current_baseline"]
    run(p, cap=BASELINE_ITEMS_CAP, apply=True, today="2026-08-14")
    after = parse_handoff(p)["current_baseline"]
    assert before == after, f"생성기 입력이 바뀌었다: {before!r} → {after!r}"


def case_11_multiline_blocks_move_whole(root: Path) -> None:
    """기준선은 한 줄이 아니다 — **들여쓴 하위 줄까지** 함께 옮긴다.

    2026-08-14 실측: 한 줄짜리 fixture 만 두었더니 첫 구현이 첫 줄만 옮겼고, 실제
    handoff 에 적용하자 하위 불릿이 §1 에 **고아로 남았다**. fixture 가 실물의 모양을
    안 닮으면 검사는 통과하고 산출물만 깨진다.
    """
    p = root / "session_handoff.md"
    body = []
    for i in range(BASELINE_ITEMS_CAP + 2):
        label = "현재 기준선" if i == 0 else ("직전 기준선" if i == 1 else "그 이전 기준선")
        body.append(f"- {label}: 세션 {i} 요약.")
        body.append(f"  - 하위 불릿 {i}-a")
        body.append(f"  - 하위 불릿 {i}-b")
    p.write_text(_HANDOFF_HEAD + "\n".join(body) + "\n" + _HANDOFF_TAIL, encoding="utf-8")
    run(p, cap=BASELINE_ITEMS_CAP, apply=True, today="2026-08-14")
    left = p.read_text(encoding="utf-8")
    archive = (root / BASELINES_FILENAME).read_text(encoding="utf-8")
    for i in range(BASELINE_ITEMS_CAP, BASELINE_ITEMS_CAP + 2):
        for suffix in ("a", "b"):
            token = f"하위 불릿 {i}-{suffix}"
            assert token not in left, f"옮긴 기준선의 하위 줄이 §1 에 고아로 남았다: {token}"
            assert token in archive, f"하위 줄이 이관되지 않고 사라졌다: {token}"
    for i in range(BASELINE_ITEMS_CAP):
        assert f"하위 불릿 {i}-a" in left, f"남겨야 할 하위 줄이 사라졌다: {i}"


def case_10_self_application() -> None:
    """자기 적용 — **현재 브랜치 네임스페이스의** handoff 가 상한 이하인가.

    main 의 handoff 를 보지 않는다. 작업 브랜치에서 `active/main/` 을 고치는 것은
    `check_branch_memory_namespace` 가 막는 일이고 그게 맞다 — 남의 네임스페이스를
    green 으로 만들려고 손대는 순간 그 가드를 우회하게 된다. 각 브랜치는 자기
    handoff 만 책임진다.
    """
    from workflow_kit.common.paths import memory_active_dir, path_in_active
    handoff = path_in_active(memory_active_dir(REPO_ROOT), "session_handoff.md")
    if not handoff.is_file():
        print(f"  SKIP  case_10 — 현재 브랜치 handoff 부재 ({handoff})")
        return
    got = plan(handoff.read_text(encoding="utf-8"), cap=BASELINE_ITEMS_CAP)
    assert got["total"] <= BASELINE_ITEMS_CAP, (
        f"{handoff} 의 기준선이 {got['total']}줄 — 상한 {BASELINE_ITEMS_CAP} 초과. "
        f"`wk rollover-baselines --handoff-path <path> --apply` 로 이관한다."
    )


def _run(fn, needs_root: bool = True) -> None:
    try:
        if needs_root:
            with tempfile.TemporaryDirectory(prefix="check-baseline-cap-") as tmp:
                fn(Path(tmp).resolve())
        else:
            fn()
        print(f"  PASS  {fn.__name__}")
    except AssertionError as e:
        FAILURES.append(fn.__name__)
        print(f"  FAIL  {fn.__name__} — {e}")
    except Exception as e:  # noqa: BLE001
        # AssertionError 만 잡으면 **구현이 깨졌을 때 검사가 통째로 죽는다** —
        # 남은 case 가 아예 안 돌고, 출력은 traceback 하나뿐이라 어느 계약이
        # 깨졌는지도 안 보인다 (2026-08-14 되주입에서 실측: 이관을 생략하자
        # case 3 이 FileNotFoundError 로 죽으며 case 4~10 이 사라졌다).
        FAILURES.append(fn.__name__)
        print(f"  FAIL  {fn.__name__} — 예외 {type(e).__name__}: {e}")


def main() -> int:
    print(f"=== handoff 기준선 롤오프 계약 (cap={BASELINE_ITEMS_CAP}) ===")
    for fn in (case_1_under_cap_is_noop, case_2_keeps_exactly_cap,
               case_3_moved_lines_are_not_lost, case_4_pointer_remains,
               case_5_labels_are_rewritten, case_6_second_run_does_not_stack_headers,
               case_7_plan_only_without_apply, case_8_cap_zero_rejected,
               case_9_generator_input_unchanged, case_11_multiline_blocks_move_whole):
        _run(fn)
    _run(case_10_self_application, needs_root=False)
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    print("\n11/11 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
