#!/usr/bin/env python3
"""워크플로우 허브 선택 클라이언트 — 표준 라이브러리만 (hub_spec §7, 요구 R2.7 · R12).

``GET /v1/bootstrap/hub_client.py`` 가 내려준다. 저장소 뿌리에서 돈다 (``.workflow-hub/env`` 를 읽는다).
모든 호출은 ``POST /v1/tools/<name>`` — MCP 도구와 같은 함수다.

    python .workflow-hub/hub_client.py call <tool> ['<json 인자>']   # 닿지 않으면 쓰기는 보낼편지함으로 (exit 3)
    python .workflow-hub/hub_client.py flush                        # 보낼편지함을 오래된 것부터 보낸다
    python .workflow-hub/hub_client.py status                       # 보낼편지함 · 캐시
    python .workflow-hub/hub_client.py session-start                # 남은 보낼편지함 수를 싣고 시작, 브리핑을 캐시

보낼편지함 (R12.2 · D4): 허브에 닿지 않는 동안의 **쓰기**는 ``.workflow-hub/outbox/<시각>-<난수>.json`` 에
``request_id`` 와 함께 남는다 (다시 보내도 허브가 한 번만 반영한다). 보낼 때 version 이 어긋나 409 면
**자동 병합하지 않고** 그 항목을 남긴 채 보고한다. 읽기는 쌓지 않는다 — 낡은 답을 지금 답처럼 내지 않게.

캐시 (R12.1): 마지막 ``session-start`` 응답을 ``.workflow-hub/cache/session_start.json`` 에 둔다. 허브가 꺼져
있으면 그것으로 열되 '허브 미확인 · 캐시(<시각>)' 라고 말한다. 캐시도 없으면 '허브 미확인 · 캐시 없음'.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

CLIENT_VERSION = "hub-client/1"
HUB_DIR = Path(".workflow-hub")
OUTBOX = HUB_DIR / "outbox"
CACHE = HUB_DIR / "cache"

#: 허브에 닿지 않을 때 보낼편지함에 쌓는 쓰기 도구 — 멱등 키(``request_id``)를 받는 것만이다.
#: 받지 않는 도구에 키를 실으면 허브가 모르는 인자로 거절하므로, 이 목록은 허브 도구 표에서
#: ``request_id`` 를 받는 도구의 부분집합이어야 한다 (check_hub_wiki 가 대조한다).
QUEUEABLE = frozenset({
    "hub_task_create", "hub_task_update", "hub_task_close", "hub_task_claim", "hub_task_release",
    "hub_task_progress", "hub_task_link_commit", "hub_wiki_ingest", "hub_wiki_import_dir", "hub_wiki_import_okf",
})


def _env() -> dict[str, str]:
    path = HUB_DIR / "env"
    out: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    for k in ("WORKFLOW_HUB_URL", "WORKFLOW_HUB_TOKEN"):
        if os.environ.get(k):
            out[k] = os.environ[k]
    return out


class Unreachable(Exception):
    """허브에 닿지 않았다 (연결 거부 · 이름 풀이 실패 · 시간 초과)."""


def _post(name: str, args: dict[str, Any], timeout: float = 20) -> tuple[int, dict[str, Any]]:
    env = _env()
    url, token = env.get("WORKFLOW_HUB_URL", "").rstrip("/"), env.get("WORKFLOW_HUB_TOKEN", "")
    if not url or not token:
        raise SystemExit("hub_client: .workflow-hub/env 에 WORKFLOW_HUB_URL · WORKFLOW_HUB_TOKEN 이 없다")
    req = urllib.request.Request(f"{url}/v1/tools/{name}", data=json.dumps(args).encode("utf-8"), method="POST",
                                 headers={"content-type": "application/json", "authorization": f"Bearer {token}",
                                          "x-hub-client": CLIENT_VERSION})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body)
        except ValueError:
            return e.code, {"error_code": "http_error", "message": body[:500]}
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        raise Unreachable(str(getattr(e, "reason", e))) from None


def _queue(name: str, args: dict[str, Any], reason: str) -> Path:
    OUTBOX.mkdir(parents=True, exist_ok=True)
    item = {"tool": name, "args": args, "queued_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "reason": reason}
    path = OUTBOX / f"{time.time_ns():020d}-{secrets.token_hex(4)}.json"
    path.write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def cmd_call(name: str, raw: str = "{}") -> int:
    args = json.loads(raw)
    if name in QUEUEABLE:
        args.setdefault("request_id", f"hc-{time.time_ns()}-{secrets.token_hex(6)}")
    try:
        status, body = _post(name, args)
    except Unreachable as e:
        if name not in QUEUEABLE:
            print(json.dumps({"status": "unreachable", "reason": str(e), "queued": False,
                              "note": "읽기 · 큐에 넣을 수 없는 도구는 쌓지 않는다"}, ensure_ascii=False))
            return 2
        path = _queue(name, args, str(e))
        print(json.dumps({"status": "queued", "outbox": str(path), "reason": str(e)}, ensure_ascii=False))
        return 3
    print(json.dumps({"http": status, **body}, ensure_ascii=False))
    return 0 if status < 400 else 1


def _items() -> list[Path]:
    return sorted(OUTBOX.glob("*.json")) if OUTBOX.is_dir() else []


def cmd_flush() -> int:
    sent: list[str] = []
    conflicts: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    kept: list[str] = []
    items = _items()
    for i, path in enumerate(items):
        item = json.loads(path.read_text(encoding="utf-8"))
        try:
            status, body = _post(item["tool"], item["args"])
        except Unreachable as e:
            kept = [p.name for p in items[i:]]
            print(json.dumps({"status": "unreachable", "reason": str(e), "sent": sent, "conflicts": conflicts,
                              "failed": failed, "remaining": kept}, ensure_ascii=False))
            return 3
        if status < 400:
            sent.append(path.name)
            path.unlink()
        elif status == 409:
            # 자동 병합하지 않는다 — 항목은 남고, 사람이 (또는 에이전트가 새로 읽고) 다시 쓴다 (D4).
            conflicts.append({"item": path.name, "tool": item["tool"], "detail": body.get("detail"),
                              "message": body.get("message")})
        else:
            failed.append({"item": path.name, "tool": item["tool"], "http": status, "error_code": body.get("error_code"),
                           "message": body.get("message")})
    remaining = [p.name for p in _items()]
    print(json.dumps({"status": "flushed", "sent": sent, "conflicts": conflicts, "failed": failed,
                      "remaining": remaining}, ensure_ascii=False))
    return 0 if not conflicts and not failed else 1


def cmd_status() -> int:
    cache = CACHE / "session_start.json"
    print(json.dumps({"client": CLIENT_VERSION, "outbox_pending": len(_items()), "outbox": [p.name for p in _items()],
                      "cache": json.loads(cache.read_text(encoding="utf-8")).get("cached_at") if cache.is_file() else None},
                     ensure_ascii=False))
    return 0


def cmd_session_start(raw: str = "{}") -> int:
    args = json.loads(raw)
    args["client"] = {"version": CLIENT_VERSION, "outbox_pending": len(_items())}
    cache = CACHE / "session_start.json"
    try:
        status, body = _post("hub_session_start", args)
    except Unreachable as e:
        if cache.is_file():
            cached = json.loads(cache.read_text(encoding="utf-8"))
            print(json.dumps({"status": "hub_unreachable", "report": f"허브 미확인 · 캐시 ({cached.get('cached_at')})",
                              "reason": str(e), "outbox_pending": len(_items()), "cached": cached.get("body")},
                             ensure_ascii=False))
        else:
            print(json.dumps({"status": "hub_unreachable", "report": "허브 미확인 · 캐시 없음", "reason": str(e),
                              "outbox_pending": len(_items())}, ensure_ascii=False))
        return 3
    if status < 400:
        CACHE.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"cached_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "body": body},
                                    ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"http": status, **body}, ensure_ascii=False))
    return 0 if status < 400 else 1


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "call" and rest:
        return cmd_call(rest[0], rest[1] if len(rest) > 1 else "{}")
    if cmd == "flush":
        return cmd_flush()
    if cmd == "status":
        return cmd_status()
    if cmd == "session-start":
        return cmd_session_start(rest[0] if rest else "{}")
    print(f"hub_client: 모르는 명령 {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
