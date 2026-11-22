"""중앙 허브로 나가는 연결 (스펙 §9.2) — urllib 만. 중앙은 PC 로 들어오지 않는다."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class HubUnreachable(Exception):
    pass


class HubError(Exception):
    def __init__(self, status: int, payload: dict[str, Any]) -> None:
        super().__init__(f"{status} {payload.get('error_code')}: {payload.get('message')}")
        self.status = status
        self.payload = payload


def post(base: str, path: str, body: dict[str, Any], token: str | None = None, timeout: float = 40.0) -> dict[str, Any]:
    headers = {"content-type": "application/json", "x-hub-client": "workflow-hub-relay/1"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base.rstrip("/") + path, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out: dict[str, Any] = json.loads(r.read().decode("utf-8"))
            return out
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except ValueError:
            payload = {"error_code": "http_error", "message": str(e)}
        raise HubError(e.code, payload) from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise HubUnreachable(str(e)) from e
