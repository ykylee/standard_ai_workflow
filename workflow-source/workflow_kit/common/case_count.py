"""검사 요약이 **실제 발화한 case 수**를 말하는지 판정한다 (TASK-2026-09-23-main-004).

많은 `check_*.py` 가 case 마다 `PASS: ...` / `FAIL: ...` 를 찍고 마지막에
`N/M PASS` 로 요약한다. 그런데 그 `M` 이 **손으로 박은 상수**인 경우가 있다.
그러면 case 를 늘려도 줄여도 요약은 옛 숫자를 유지한다 — 2026-09-23 에 두 번
실물로 만났다 (`check_memory_entry_suggestions` 는 case 11개에 `9/9 PASS`,
`check_release_wrapper_args` 는 12개에 `11/11 PASS`). 둘 다 전체 green 이라
아무도 보지 못했다.

이것은 '검사는 깨지지 않고 무력화된다' 의 **계수 판**이다. case 를 지워도
요약이 옛 개수를 유지하면, 무력화가 숫자에서도 안 보인다.

판정은 **출력에서 파생**한다 — 재실행 비용이 0이다. runner 는 이미 각 검사의
stdout+stderr 를 전량 받아 두고 요약 뒤 버리고 있었다 (경고 축과 같은 자리).

**세지 못한 것은 통과가 아니다.** case 줄이나 요약 줄 중 하나라도 없으면
`measured=False` 로 사유와 함께 올린다 — 그 검사가 옳다는 뜻이 아니라 이 축이
그것을 볼 수 없다는 뜻이다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

#: 마지막 요약 줄. 여러 개면 **마지막**이 최종 요약이다.
#:
#: 처음에는 `9/9 PASS` 계열만 받았다. 전수 실측(2026-09-23, main-006)에서
#: '개수 선언이 없다' 로 분류된 153건 중 **36건이 사실은 선언하고 있었고**, 단지
#: 장식(`=== `)이 앞에 붙거나 `PASS:` 가 비율보다 먼저 오는 모양이었다. 검사들이
#: 제각각인 게 아니라 **내 정규식이 좁았던 것**이다. 받는 모양:
#:     `9/9 PASS` · `10/11 PASS — FAILED: [...]` · `4/4 tests passed.` · `6/6 passed`
#:     `=== 6/6 PASS ===` · `=== PASS: 5/5 ===` · `Result: 5/5 PASS`
_SUMMARY_RE: Final = re.compile(
    r"^[^\S\n]*(?:=+[^\S\n]*)?(?:(?:PASS|FAIL|Result)[^\S\n]*:[^\S\n]*)?"
    r"(\d+)[^\S\n]*/[^\S\n]*(\d+)\b"
    r"(?=[^\S\n]*(?:PASS|passed|tests|=|$))",
    re.MULTILINE,
)

#: `7 pass, 0 fail` 계열 — 비율이 아니라 **두 수의 합**이 총 개수다.
_PASS_FAIL_SUM_RE: Final = re.compile(
    r"^[^\S\n]*(?:=+[^\S\n]*)?(\d+)[^\S\n]+pass(?:ed)?[^\S\n]*,[^\S\n]*(\d+)[^\S\n]+fail",
    re.MULTILINE | re.IGNORECASE,
)

#: `=== PASS: claim_workspace smoke (9 assertions) ===` — 개수가 산문 안에 있다.
_ASSERTIONS_RE: Final = re.compile(
    r"\((?:all[^\S\n]+)?(\d+)[^\S\n]+(?:assertions?|checks?)\)", re.IGNORECASE)

#: `All 16 tests passed.` 도 **개수 선언**이다. 형태가 다를 뿐 계약은 같다.
_ALL_N_RE: Final = re.compile(
    r"^[^\S\n]*All (\d+) (?:\w+ )?(?:tests?|checks?|cases?)\b[^\n]*pass",
    re.MULTILINE | re.IGNORECASE,
)

#: case 한 줄. `PASS: 1) ...` / `  FAIL: 6) ... — 사유`.
#:
#: 처음에는 줄 맨 앞만 받았다 (남의 출력을 들여쓴 채 echo 하는 경우가 무서워서).
#: 그런데 전량 실측에서 **290개 중 28개만** 읽혔고, 못 읽은 표본은 전부 자기
#: case 를 들여쓰는 검사였으며 선언과 들여쓴 case 수가 정확히 같았다
#: (10/10 · 8/8 · 7/7 · 5/5 · 4/4 · 6/6). 조용히 좁은 범위는 그 밖을 갈라지게
#: 두므로 들여쓰기를 받는다 — echo 위양성이 실제로 나는지는 전량으로 잰다.
#: 콜론은 **선택**이다 — 사유 없이 `  PASS` 만 찍는 case 가 있고, 그걸 안 세면
#: 이미 파생으로 고쳐 둔 검사에 위양성을 낸다 (check_agent_plugin_payload 23/22).
_CASE_RE: Final = re.compile(r"^[^\S\n]*(PASS|FAIL)\b[^\S\n]*:?", re.MULTILINE)

#: `  [PASS] test_foo` 형태의 **명시적 롤업**. 이게 있으면 이것이 case 목록이다.
#: 한 검사의 출력에 흐름이 둘일 수 있다 — 하위 단언(`PASS: …`)과 case 롤업.
#: `check_mypy_config_actually_loaded` 가 그랬다: 선언 7, 롤업 7줄, 하위 단언 6줄.
#: 둘을 더하면 13 이고 하위 단언만 세면 6 이라, **롤업이 있으면 그것만** 센다.
#: 롤업 표식은 두 가지다 — `[PASS] name` 과 `✓ name PASS` / `✗ name FAIL`.
#: **`SKIP` 도 발화한 case 다** — 선언에 세어지면서 롤업에서 빠지면 그 자체로
#: 불일치가 되고, 무엇보다 '모름' 이 조용히 통과가 된다.
#: 후자를 안 받으면 흐름이 둘인 검사 9건에서 **하위 case** 를 세게 되고
#: (실측: 선언 8 vs 하위 22), 접두 확장이 그대로 위양성이 된다 (main-007).
_BRACKET_CASE_RE: Final = re.compile(
    r"^[^\S\n]*(?:\[(?:PASS|FAIL|SKIP)\]"
    r"|[\u2713\u2717][^\n]*?\b(?:PASS|FAIL|ERROR|SKIP)\b)",
    re.MULTILINE,
)

#: `  case 3 (범위가 비어 있지 않다): PASS — …` 형태. 판정어가 **줄 중간**에 있어
#: 위 정규식이 못 본다. 전수 실측(2026-09-23, main-006)에서 개수를 선언하고도
#: 못 읽히던 7건 중 6건이 이 모양이었다 — 표식이 다를 뿐 같은 계약이다.
#: `case <번호>` 접두를 요구해 산문 속 'PASS' 를 배제한다.
_LABELLED_CASE_RE: Final = re.compile(
    r"^[^\S\n]*case[^\S\n]+\d+\b[^\n]*?:[^\S\n]*(PASS|FAIL)\b",
    re.MULTILINE | re.IGNORECASE,
)


@dataclass(frozen=True)
class CaseCount:
    """한 검사의 (선언, 실측) 쌍."""

    declared: int | None
    seen: int
    measured: bool
    reason: str = ""

    @property
    def diverged(self) -> bool:
        return self.measured and self.declared != self.seen


def count_cases(output: str) -> CaseCount:
    """검사 출력에서 선언된 총 개수와 실제 발화한 case 수를 뽑는다."""
    summaries: list[tuple[str, str]] = _SUMMARY_RE.findall(output)
    if not summaries:
        pf = _PASS_FAIL_SUM_RE.findall(output)
        if pf:
            summaries = [("0", str(int(pf[-1][0]) + int(pf[-1][1])))]
        else:
            asserts = _ASSERTIONS_RE.findall(output)
            if asserts:
                summaries = [("0", asserts[-1])]
    bracket = len(_BRACKET_CASE_RE.findall(output))
    seen = bracket or (len(_CASE_RE.findall(output))
                       + len(_LABELLED_CASE_RE.findall(output)))
    if summaries:
        declared: int | None = int(summaries[-1][1])
    else:
        all_n = _ALL_N_RE.findall(output)
        declared = int(all_n[-1]) if all_n else None
    if declared is None:
        return CaseCount(None, seen, False, f"개수 선언이 없다 [case={seen}]")
    if seen == 0:
        return CaseCount(declared, 0, False, f"case 줄(`PASS:` / `FAIL:`)이 없다 [선언={declared}]")
    return CaseCount(declared, seen, True)
