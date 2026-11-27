"""요청 본문 JSON 해석 — Go 허브(`encoding/json`)와 같은 의미로 맞춘다.

Go 의 `encoding/json` 은 짝 없는 서로게이트 escape(`"\\ud800"`)를 U+FFFD 로 바꿔 읽는다.
Python `json.loads` 는 그 코드 포인트를 문자열에 그대로 남겨, 뒤에서 `encode("utf-8")` 하는 곳마다
500 이 났다 (TASK-2026-11-24-claude-plex-003). 해석 직후 같은 치환을 해 두 런타임의 응답을 맞춘다.
"""

from __future__ import annotations

import json
import re
from typing import Any

# json.loads 는 올바른 짝을 이미 한 글자로 합치므로, 남은 서로게이트 코드 포인트는 모두 홀로 선 것이다.
_LONE_SURROGATE = re.compile("[\ud800-\udfff]")


def scrub_surrogates(value: Any) -> Any:
    """홀로 선 서로게이트를 하나에 U+FFFD 하나로 바꾼다 — 키 · 값 · 중첩 모두 (Go 와 같은 치환)."""
    if isinstance(value, str):
        return _LONE_SURROGATE.sub("�", value)
    if isinstance(value, dict):
        return {scrub_surrogates(k): scrub_surrogates(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub_surrogates(v) for v in value]
    return value


def loads_body(raw: bytes) -> Any:
    """요청 본문 bytes → 값. 실패는 호출자가 받던 예외(UnicodeDecodeError · JSONDecodeError) 그대로."""
    return scrub_surrogates(json.loads(raw.decode("utf-8")))


# 서로게이트 escape(\uD800–\uDFFF) — 이 꼴이 없는 본문은 손대지 않는다 (대부분의 요청).
_SURROGATE_ESCAPE = re.compile(rb"\\u[dD][89a-fA-F][0-9a-fA-F]{2}")


def scrub_json_bytes(raw: bytes) -> bytes:
    """본문 bytes 를 SDK 에 넘기기 전에 같은 치환을 한다 — `/mcp` 는 SDK(pydantic)가 해석하고, pydantic 은
    홀로 선 서로게이트를 파싱 오류(-32700)로 거절해 Go 와 갈렸다. 해석할 수 없거나 바뀔 것이 없으면 원문 그대로."""
    if not _SURROGATE_ESCAPE.search(raw):
        return raw
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return raw  # 해석 실패는 SDK 가 지금처럼 보고한다
    scrubbed = scrub_surrogates(value)
    if scrubbed == value:
        return raw  # 짝이 맞는 escape 뿐
    return json.dumps(scrubbed, ensure_ascii=False).encode("utf-8")
