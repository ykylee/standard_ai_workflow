"""1.x 줄의 2.0 안내 · EOL 한 줄 (요구 R14.8 · R16.3 · R16.4, 1.x 안내 판).

``session-start`` 가 성공할 때 요약 끝에 한 줄을 싣는다 — 막지 않고 종료 코드도 그대로다.
보장 끝(:data:`EOL_DATE`, stable_guarantee 의 2028-07-20) 전에는 2.0 허브와 옮기는 길을,
그날부터는 1.x 가 끝났다는 것을 말한다.

기준 날짜는 :data:`TODAY_ENV` 로 주입할 수 있다 (검사 fixture 용 — ``YYYY-MM-DD``).
"""

from __future__ import annotations

import os
from datetime import date

#: 1.x 줄의 끝 — stable_guarantee 의 보장 끝 (요구 R16.3 · Q6).
EOL_DATE = date(2028, 7, 20)
#: 기준 날짜 주입 (검사용).
TODAY_ENV = "WORKFLOW_KIT_NOTICE_TODAY"

NOTICE_BEFORE = (
    "[2.0] 워크플로우 허브(2.0)가 나왔다 — 이 1.x 줄은 {eol} 까지 결함 수리만 한다. "
    "옮기려면 허브 주소의 /setup.md 를 에이전트에게 읽힌다 (README '2.0 으로 옮기기')."
)
NOTICE_AFTER = (
    "[EOL] 1.x 줄은 {eol} 에 끝났다 — 결함 수리도 없다. 2.0 워크플로우 허브로 옮긴다 "
    "(README '2.0 으로 옮기기')."
)


def today() -> date:
    raw = os.environ.get(TODAY_ENV, "").strip()
    if raw:
        try:
            return date.fromisoformat(raw)
        except ValueError:
            pass
    return date.today()


def notice(on: date | None = None) -> str:
    """오늘(또는 ``on``) 의 안내 한 줄."""
    d = on or today()
    return (NOTICE_AFTER if d >= EOL_DATE else NOTICE_BEFORE).format(eol=EOL_DATE.isoformat())
