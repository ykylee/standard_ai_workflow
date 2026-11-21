#!/usr/bin/env python3
"""워크플로우 허브 선택 클라이언트 — 표준 라이브러리만 (hub_spec §7, 요구 R2.7 · R12).

``GET /v1/bootstrap/hub_client.py`` 가 내려준다. 저장소 뿌리에서 돈다 (``.workflow-hub/env`` 를 읽는다).
모든 호출은 ``POST /v1/tools/<name>`` — MCP 도구와 같은 함수다.

    python .workflow-hub/hub_client.py call <tool> ['<json 인자>']   # 닿지 않으면 쓰기는 보낼편지함으로 (exit 3)
    python .workflow-hub/hub_client.py flush                        # 보낼편지함을 오래된 것부터 보낸다
    python .workflow-hub/hub_client.py status                       # 보낼편지함 · 캐시
    python .workflow-hub/hub_client.py session-start                # 남은 보낼편지함 수를 싣고 시작, 브리핑을 캐시
    python .workflow-hub/hub_client.py migrate plan                 # 1.x 전환 계획 — 허브 명령 실행 · 감지 전송 · 요약
    python .workflow-hub/hub_client.py migrate import <MIG> <종류,…|all>  # 고른 종류의 파일을 묶음으로 보내고 끝낸다

1.x 전환 (hub_spec §6.6 · 소유자 2026-11-21): 감지 결과와 파일 내용은 크다(리허설: task 600여 개 저장소의 감지만
~430KB). 에이전트(LLM)가 도구 인자로 싣지 않도록 이 클라이언트가 운반한다 — 에이전트는 계획 요약을 사람에게
보이고 고른 종류만 넘긴다. 전체 계획은 ``.workflow-hub/cache/migrate-<MIG>.json`` 에 남는다.

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
    # ensure_ascii=False — 한글을 \uXXXX 로 부풀리지 않는다 (요청 상한 안에 두 배를 싣는다)
    req = urllib.request.Request(f"{url}/v1/tools/{name}", data=json.dumps(args, ensure_ascii=False).encode("utf-8"),
                                 method="POST",
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


#: 전환 묶음 크기 — 허브의 큰 상한(8MiB) 안에서 한 묶음을 이만큼 (요청 하나 = 트랜잭션 몇 개).
MIGRATE_BATCH = 2 * 1024 * 1024


def _run(argv: list[str]) -> dict[str, Any]:
    import subprocess  # noqa: PLC0415 — 전환 때만

    try:
        r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        return {"rc": r.returncode, "output": r.stdout}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"rc": 127, "output": str(e)}


def cmd_migrate_plan() -> int:
    """허브가 낸 감지 명령을 저장소 뿌리에서 그대로 돌려 보내고, 계획 요약을 낸다 (전체는 캐시에)."""
    try:
        status, first = _post("hub_migrate_plan", {})
        if status >= 400:
            print(json.dumps({"http": status, **first}, ensure_ascii=False))
            return 1
        scan = {name: _run(argv) for name, argv in first.get("commands", {}).items()}
        status, plan = _post("hub_migrate_plan", {"scan": scan}, timeout=600)
    except Unreachable as e:
        print(json.dumps({"status": "unreachable", "reason": str(e)}, ensure_ascii=False))
        return 2
    if status >= 400:
        print(json.dumps({"http": status, **plan}, ensure_ascii=False))
        return 1
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"migrate-{plan['migration_id']}.json"
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    det = plan.get("detected", {})
    print(json.dumps({
        "migration_id": plan["migration_id"], "plan_file": str(path),
        "table": plan.get("table"), "conflicts": len(plan.get("conflicts", [])),
        "left_in_repo": {why: v.get("files") for why, v in det.get("left_in_repo", {}).items()},
        "uncommitted": det.get("uncommitted", []), "unsupported_harnesses": det.get("unsupported_harnesses", []),
        "kit_versions": det.get("kit_versions", []), "guidance": plan.get("guidance", []),
        "next": f"사람에게 표를 보이고 고른 종류로: hub_client.py migrate import {plan['migration_id']} <종류,…|all>",
    }, ensure_ascii=False, indent=1))
    return 0


def cmd_migrate_import(mig: str, kinds_arg: str) -> int:
    """계획의 파일을 읽어 묶음으로 보낸다. 다시 돌려도 허브가 있는 것을 건너뛴다 (마지막 묶음 final 뒤에는 409)."""
    path = CACHE / f"migrate-{mig}.json"
    if not path.is_file():
        print(json.dumps({"status": "error", "message": f"계획 캐시가 없다: {path} — migrate plan 을 먼저"}, ensure_ascii=False))
        return 2
    plan = json.loads(path.read_text(encoding="utf-8"))
    files_by_kind: dict[str, list[str]] = plan.get("files", {})
    # 계획 표의 순서대로 — 결정 응답은 그 task 뒤에 들어가야 자격을 판정할 수 있다
    order = [row["kind"] for row in plan.get("table", [])] or sorted(files_by_kind)
    wanted = set(order) if kinds_arg == "all" else {k.strip() for k in kinds_arg.split(",") if k.strip()}
    kinds = [k for k in order if k in wanted] + sorted(wanted - set(order))
    paths: list[str] = []
    for k in kinds:
        for p in files_by_kind.get(k, []):
            if p not in paths:
                paths.append(p)
    batches: list[list[dict[str, str]]] = [[]]
    size, unreadable = 0, []
    for p in paths:
        try:
            content = Path(p).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            unreadable.append({"path": p, "error": str(e)})
            continue
        n = len(json.dumps({"path": p, "content": content}, ensure_ascii=False).encode("utf-8"))
        if size + n > MIGRATE_BATCH and batches[-1]:
            batches.append([])
            size = 0
        batches[-1].append({"path": p, "content": content})
        size += n
    total: dict[str, Any] = {}
    errors = []
    for i, batch in enumerate(batches):
        try:
            status, out = _post("hub_migrate_import", {"migration_id": mig, "kinds": kinds, "files": batch,
                                                        "final": i == len(batches) - 1}, timeout=600)
        except Unreachable as e:
            print(json.dumps({"status": "unreachable", "reason": str(e), "sent_batches": i}, ensure_ascii=False))
            return 3
        if status >= 400:
            errors.append({"batch": i, "http": status, "error_code": out.get("error_code"), "message": out.get("message")})
            continue
        total = out.get("total", total)
    print(json.dumps({"migration_id": mig, "kinds": kinds, "files": len(paths), "batches": len(batches),
                      "total": total, "unreadable": unreadable, "errors": errors,
                      "next": "끝났으면 hub_migrate_marker(action='issue') 로 '허브로 옮김' 표식 — 사람이 확인한 뒤"},
                     ensure_ascii=False, indent=1))
    return 0 if not errors and not unreadable else 1


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
    if cmd == "migrate" and rest[:1] == ["plan"]:
        return cmd_migrate_plan()
    if cmd == "migrate" and len(rest) == 3 and rest[0] == "import":
        return cmd_migrate_import(rest[1], rest[2])
    print(f"hub_client: 모르는 명령 {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
