#!/usr/bin/env python3
"""Meta-check: **요약의 case 개수 대조 기전이 살아 있는가** (TASK-2026-09-23-main-004).

많은 `check_*.py` 가 case 마다 `PASS:` / `FAIL:` 를 찍고 마지막에 `N/M PASS` 로
요약한다. 그 `M` 이 손으로 박은 상수이면, case 를 늘려도 줄여도 요약은 옛 숫자를
유지한다 — 2026-09-23 에 두 번 실물로 만났다 (`check_memory_entry_suggestions`
는 case 11개에 `9/9 PASS`, `check_release_wrapper_args` 는 12개에 `11/11 PASS`).
둘 다 전체 green 이라 아무도 보지 못했다. 이건 '검사는 깨지지 않고 무력화된다'
의 **계수 판**이다 — case 를 지워도 요약이 옛 개수를 유지하면, 무력화가
숫자에서도 안 보인다.

판정 자체는 러너가 **매 실행 전수로** 한다 (`case_count_verdict`). 러너는 이미
각 검사의 출력을 전량 받아 두므로 재실행 비용이 0이다. 그래서 이 검사가 할 일은
"지금 저장소가 일치하는가" 가 아니라 **"그 기전이 실제로 잡는가"** 다.

## 범위는 실측으로 넓혔다

처음에는 case 줄을 **줄 맨 앞**만 받았다 (남의 출력을 들여쓴 채 echo 하는
경우가 무서워서). 전량으로 재니 290개 중 **28개만** 읽혔고, 못 읽은 표본은 전부
자기 case 를 들여쓰는 검사였으며 선언과 들여쓴 case 수가 정확히 같았다
(10/10 · 8/8 · 7/7 · 5/5 · 4/4 · 6/6). 넓힌 뒤 전량에서 위양성 1건이 나왔고
(`check_agent_plugin_payload` — 콜론 없이 `PASS` 만 찍는 case 하나), 그것까지
받아 0으로 만들었다. case 3·4 가 이 두 넓힘을 각각 고정한다.

검증 케이스 (11):
    1. 선언과 발화가 같으면 일치 (위양성 없음)
    2. 상수 total 을 흉내 내면 `diverged` — 늘어난 쪽과 줄어든 쪽 모두
    3. 들여쓴 case 줄을 센다 (범위 넓힘 ①)
    4. 콜론 없는 `PASS` 도 센다 (범위 넓힘 ②, 위양성 1건의 원인)
    5. `All N tests passed.` 도 개수 선언으로 받는다
    6. 선언이 없거나 case 줄이 없으면 **미측정** — 통과로 세지 않는다
    7. 요약이 여러 번 나오면 **마지막**이 최종 요약이다
    8. 이 저장소에 상수 total 이 남아 있지 않다 (`total = <정수>` 전수)
    9. 장식·어순이 달라도 선언은 선언이다 (4 모양, main-006)
   10. 판정어가 줄 중간에 있는 case 줄(`case N (…): PASS`)을 센다
   11. 흐름이 둘이면 명시적 롤업(`[PASS] name`)이 이긴다

Stdlib only.
"""

from __future__ import annotations

#: 전역 선언 (spec `core/test_impact_tiering_spec.md` §2).
#: case 8 이 `tests/*.py` **전수**를 읽으므로 국소 선언으로는 담기지 않는다.
WATCHES_ALL_REASON = (
    "case 8 이 검사 전수(291개)에서 상수 `total` 리터럴을 훑는다 — meta-watch "
    "실측(2026-09-23) 접근 338건. 판정 정본은 "
    "`workflow_kit/common/case_count.py` · 게이트 배선은 "
    "`tests/run_all_checks.py` 의 `case_count_verdict` 다"
)

#: 이 검사가 강제하는 정본 요구 (spec §7).
ENFORCES = ("check-summary-must-count-what-ran",)

import re
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.case_count import count_cases  # noqa: E402


def main() -> int:
    ran: list[str] = []
    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        ran.append(label)
        if cond:
            print(f"  PASS  {label}")
        else:
            print(f"  FAIL  {label} — {detail}")
            failures.append(label)

    # 1) 일치 — 위양성이 없어야 한다
    ok = count_cases("PASS: 1) a\nPASS: 2) b\n\n2/2 PASS")
    check("1) 선언=발화면 일치", ok.measured and not ok.diverged,
          f"{ok}")

    # 2) 상수 total 흉내 — 양방향
    more = count_cases("PASS: 1) a\nPASS: 2) b\nPASS: 3) c\n\n2/2 PASS")
    fewer = count_cases("PASS: 1) a\n\n2/2 PASS")
    check("2) 선언과 발화가 갈리면 잡는다 (증가/감소 양방향)",
          more.diverged and more.seen == 3 and fewer.diverged and fewer.seen == 1,
          f"more={more} fewer={fewer}")

    # 3) 들여쓴 case 줄 — 범위 넓힘 ①. 이걸 안 세면 전량 290 중 28개만 읽힌다.
    ind = count_cases("  PASS: 1) a\n  PASS: 2) b\n\n2/2 PASS")
    check("3) 들여쓴 case 줄을 센다", ind.measured and ind.seen == 2, f"{ind}")

    # 4) 콜론 없는 `PASS` — 범위 넓힘 ②. 실제 위양성 1건의 원인이었다.
    bare = count_cases("PASS\nPASS: b\n\n2/2 PASS")
    check("4) 콜론 없는 PASS 도 센다", bare.measured and bare.seen == 2, f"{bare}")

    # 5) `All N tests passed.` 도 개수 선언이다 (형태만 다르고 계약은 같다)
    alln = count_cases("PASS: 1) a\nPASS: 2) b\nAll 2 tests passed.")
    alln_bad = count_cases("PASS: 1) a\nPASS: 2) b\nPASS: 3) c\nAll 2 tests passed.")
    check("5) All N tests passed 형태를 선언으로 받는다",
          alln.measured and not alln.diverged and alln_bad.diverged,
          f"ok={alln} bad={alln_bad}")

    # 6) 미측정은 통과가 아니다
    no_decl = count_cases("PASS: 1) a")
    no_case = count_cases("무언가 했다\n6/6 passed")
    check("6) 선언/ case 줄이 없으면 미측정 (통과 아님)",
          (not no_decl.measured and not no_decl.diverged
           and not no_case.measured and not no_case.diverged
           and no_decl.reason and no_case.reason),
          f"no_decl={no_decl} no_case={no_case}")

    # 7) 요약이 여럿이면 마지막이 최종이다 (하위 스위트가 중간 요약을 찍는다)
    multi = count_cases("PASS: 1) a\n1/1 PASS\nPASS: 2) b\n\n2/2 PASS")
    check("7) 마지막 요약 줄을 최종으로 읽는다",
          multi.measured and multi.declared == 2 and not multi.diverged, f"{multi}")

    # 9) **장식·어순이 달라도 선언은 선언이다** (main-006). 전수 실측에서 '개수
    #    선언이 없다' 로 분류된 153건 중 **36건이 사실은 선언하고 있었다** — 검사가
    #    제각각인 게 아니라 이 축의 정규식이 좁았던 것이다. 네 모양을 고정한다.
    for label, text in (
        ("=== N/M PASS ===", "  PASS: a\n  PASS: b\n=== 2/2 PASS ==="),
        ("=== PASS: N/M ===", "  PASS: a\n  PASS: b\n=== PASS: 2/2 ==="),
        ("N pass, M fail", "  PASS: a\n  PASS: b\n2 pass, 0 fail"),
        ("(N assertions)", "  PASS: a\n  PASS: b\n=== PASS: x smoke (2 assertions) ==="),
    ):
        cc = count_cases(text)
        check(f"9) 선언 형태 — {label}", cc.measured and cc.declared == 2 and not cc.diverged,
              f"{cc}")

    # 10) **판정어가 줄 중간에 있는 case 줄** — `case 3 (…): PASS — …`.
    #     미측정 7건 중 6건이 이 모양이었다.
    mid = count_cases("  case 1 (a): PASS — 어쩌고\n  case 2 (b): PASS\n\n2/2 passed")
    mid_bad = count_cases("  case 1 (a): PASS\n\n2/2 passed")
    check("10) 줄 중간 판정어(`case N (…): PASS`)를 센다",
          mid.measured and mid.seen == 2 and mid_bad.diverged, f"ok={mid} bad={mid_bad}")

    # 11) **흐름이 둘이면 명시적 롤업이 이긴다.** 하위 단언(`PASS: …`)과 case
    #     롤업(`[PASS] name`)이 같이 찍히면 더해서 13 이 되거나 6 만 세게 된다 —
    #     실물(`check_mypy_config_actually_loaded`)이 정확히 그랬다.
    two = count_cases(
        "  PASS: 하위 단언 1\n  PASS: 하위 단언 2\n"
        "  [PASS] test_a\n  [PASS] test_b\n  [PASS] test_c\n\n=== 3/3 PASS ===")
    check("11) 롤업이 있으면 하위 단언 대신 롤업을 센다",
          two.measured and two.seen == 3 and not two.diverged, f"{two}")

    # 8) 이 저장소에 **상수 total 이 남아 있지 않다.** 누산기(`total = 0` 뒤에
    #    `total += ...`)는 선언이 아니므로 제외한다 — 이름이 아니라 쓰임으로 가른다.
    leftovers: list[str] = []
    for path in sorted(TESTS_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"^[^\S\n]*total = (\d+)$", text, re.M):
            tail = text[m.end():]
            if re.search(r"^[^\S\n]*total \+=", tail, re.M):
                continue        # 누산기
            leftovers.append(f"{path.name}:{text[:m.start()].count(chr(10)) + 1} = {m.group(1)}")
    check("8) 저장소에 상수 total 이 없다", not leftovers,
          f"남은 상수: {leftovers}")

    total = len(ran)
    print()
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
