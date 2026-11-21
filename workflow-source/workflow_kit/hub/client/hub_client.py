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
    python .workflow-hub/hub_client.py move <대상 허브 주소> <초대 코드>   # 허브 간 이전 (소유자) — 봉인 · 뜨기 · 들이기 · 주소 바꾸기
    python .workflow-hub/hub_client.py bootstrap <허브 주소> --harness <h> --callsign <c> [--kind human|agent] [--name <표시 이름>]
                                                    # 빈 환경 부트스트랩 — 등록(또는 합류) · 셋업 지시 실행 · 확인 (토큰은 env 에만)

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


def cmd_move(target: str, invite: str) -> int:
    """허브 간 이전 (hub_spec §3.5, 소유자 2026-11-21) — 원본에서 봉인+묶음 → 대상에 초대 코드로 들이기.

    실패하면 원본 봉인을 풀어 되돌린다. 성공하면 ``.workflow-hub/env`` 의 주소를 바꾼다 (토큰은 그대로 —
    이어받는다). 그 뒤 새 허브의 셋업(hub_setup_plan)으로 .mcp.json 등 하네스 설정의 주소를 다시 쓴다.
    """
    target = target.rstrip("/")
    try:
        status, out = _post("hub_project_export", {"seal_to": target}, timeout=600)
    except Unreachable as e:
        print(json.dumps({"status": "unreachable", "where": "source", "reason": str(e)}, ensure_ascii=False))
        return 2
    if status >= 400:
        print(json.dumps({"status": "export_failed", "http": status, **out}, ensure_ascii=False))
        return 1
    bundle = out["bundle"]
    req = urllib.request.Request(f"{target}/v1/tools/hub_project_import",
                                 data=json.dumps({"invite": invite, "bundle": bundle}, ensure_ascii=False).encode("utf-8"),
                                 method="POST", headers={"content-type": "application/json", "x-hub-client": CLIENT_VERSION})
    imported: dict[str, Any] | None = None
    error: dict[str, Any] = {}
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            imported = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            error = {"http": e.code, **json.loads(e.read().decode("utf-8"))}
        except ValueError:
            error = {"http": e.code}
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        error = {"status": "unreachable", "where": "target", "reason": str(getattr(e, "reason", e))}
    if imported is None:
        # 되돌린다 — 이 실행이 건 봉인만 푼다 (대상은 거절했다). 원래 봉인돼 있던 프로젝트는 그대로 둔다 —
        # 풀면 이미 옮겨 간 정본과 둘이 된다.
        if out.get("was_sealed"):
            u_status, u_out = 0, {"note": "원래 봉인돼 있던 프로젝트 — 풀지 않았다"}
        else:
            try:
                u_status, u_out = _post("hub_project_unseal", {})
            except Unreachable as e:
                u_status, u_out = 0, {"reason": str(e)}
        print(json.dumps({"status": "import_failed", "target": error, "source_unsealed": u_status == 200, "unseal": u_out},
                         ensure_ascii=False))
        return 1
    env_path = HUB_DIR / "env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.is_file() else []
    lines = [ln for ln in lines if not ln.startswith("WORKFLOW_HUB_URL=")] + [f"WORKFLOW_HUB_URL={target}"]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "moved", "project_id": imported.get("project_id"), "target": target,
                      "digest": imported.get("digest"), "env_updated": str(env_path),
                      "next": "새 허브에서 셋업을 다시 돌려(hub_setup_plan → hub_setup_confirm) .mcp.json 등 하네스 설정의 주소를 "
                              "바꾼다 — 토큰은 그대로다. 1.x 에서 전환한 저장소면 hub_migrate_marker(action='issue') 로 표식 주소도"},
                     ensure_ascii=False, indent=1))
    return 0


# --- 부트스트랩 (M-039 WBS-39.1 · 소유자 2026-11-21 '가이드 페이지만 읽고 스스로 셋업') -----------------------

def _http(base: str, name: str, args: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """토큰 없는 부트스트랩 묶음 호출 (env 가 아직 없다)."""
    req = urllib.request.Request(f"{base}/v1/tools/{name}", data=json.dumps(args, ensure_ascii=False).encode("utf-8"),
                                 method="POST", headers={"content-type": "application/json", "x-hub-client": CLIENT_VERSION})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except ValueError:
            return e.code, {"error_code": "http_error"}
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        raise Unreachable(str(getattr(e, "reason", e))) from None


def _sha(path: Path) -> str:
    import hashlib  # noqa: PLC0415

    return hashlib.sha256(path.read_bytes()).hexdigest()


#: 스크립트가 직접 쓰지 않고 에이전트(또는 사람)에게 넘기는 단계 — 하네스의 안전 장치를 지나야 하는 것.
#: Claude Code 는 .mcp.json 쓰기에 사람 승인을 받는다 (M-039 실측). 스크립트가 쓰면 그 장치를 우회한다.
HANDOFF_STEPS = ("harness:mcp-json", "harness:antigravity")


def _scan() -> dict[str, Any]:
    paths = (".gitignore", "CLAUDE.md", "AGENTS.md", "MiniMax.md", "ANTIGRAVITY.md", ".mcp.json")
    return {"files": {p: (Path(p).read_text(encoding="utf-8") if Path(p).is_file() else None) for p in paths}}


def _bootstrap_out(payload: dict[str, Any], rc: int) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return rc


def cmd_bootstrap(argv: list[str]) -> int:
    """빈 환경 부트스트랩 — 등록(또는 합류) → .gitignore 확인 → env → 진입 파일 → 하네스 설정 지시.

    토큰은 출력하지 않는다 (env 에만). 다시 부르면 env 로 이어 간다 (확인된 단계는 허브가 건너뛴다).
    하네스의 안전 장치를 지나야 하는 단계(:data:`HANDOFF_STEPS`)는 쓰지 않고 ``for_agent`` 로 넘긴다 —
    에이전트가 자기 도구로 쓴 뒤(사람 승인) 이 명령을 다시 부르면 sha256 으로 확인한다.
    1.x kit 흔적이 있으면 진입 파일을 쓰지 않는다 — 전환(표식)은 사람이 정한다.
    """
    import argparse  # noqa: PLC0415

    ap = argparse.ArgumentParser(prog="hub_client.py bootstrap")
    ap.add_argument("hub")
    ap.add_argument("--harness", action="append", required=True)
    ap.add_argument("--callsign", required=True)
    ap.add_argument("--kind", default="agent", choices=("human", "agent"))
    ap.add_argument("--name", default="")
    ap.add_argument("--label", default="")
    a = ap.parse_args(argv)
    base = a.hub.rstrip("/")
    top = _run(["git", "rev-parse", "--show-toplevel"])
    if top["rc"] != 0:
        return _bootstrap_out({"status": "not_git_repo",
                               "next": "git 저장소가 아니다. 빈 폴더면 `git init` 뒤 다시 부른다. 파일이 있는 폴더면 git 저장소로 "
                                       "만들어도 되는지 사람에게 묻는다"}, 1)
    if Path(top["output"].strip()).resolve() != Path.cwd().resolve():
        return _bootstrap_out({"status": "not_repo_root", "root": top["output"].strip(),
                               "next": "저장소 뿌리에서 다시 부른다"}, 1)
    env = _env()
    joined: dict[str, Any] = {}
    try:
        if env.get("WORKFLOW_HUB_TOKEN") and env.get("WORKFLOW_HUB_PROJECT"):
            if env.get("WORKFLOW_HUB_URL", "").rstrip("/") != base:
                return _bootstrap_out({"status": "other_hub", "hub_in_env": env.get("WORKFLOW_HUB_URL"),
                                       "next": "이 저장소는 이미 다른 허브에 셋업돼 있다 — 사람에게 묻는다"}, 1)
            project_id, token = env["WORKFLOW_HUB_PROJECT"], env["WORKFLOW_HUB_TOKEN"]
            joined = {"resumed": True}
        else:
            remote = _run(["git", "remote", "get-url", "origin"])
            url = remote["output"].strip() if remote["rc"] == 0 else ""
            if not url:
                names = _run(["git", "remote"])["output"].split()
                url = _run(["git", "remote", "get-url", names[0]])["output"].strip() if names else ""
            name = a.name or Path.cwd().name
            found: dict[str, Any] = {}
            if url:
                st, found = _http(base, "hub_project_lookup", {"remote_url": url})
                if st != 200:
                    return _bootstrap_out({"status": "lookup_failed", "http": st, **found}, 1)
                if found.get("moved_to"):
                    return _bootstrap_out({"status": "moved", "moved_to": found["moved_to"],
                                           "next": "이 프로젝트는 다른 허브로 옮겼다 — 그 주소로 다시 부른다"}, 1)
            if found.get("project_id"):
                st, reg = _http(base, "hub_callsign_register", {"project_id": found["project_id"], "callsign": a.callsign,
                                                                "kind": a.kind, "label": a.label})
            else:
                st, reg = _http(base, "hub_project_register", {"remote_url": url, "display_name": name, "callsign": a.callsign,
                                                               "kind": a.kind, "label": a.label})
            if st != 200:
                return _bootstrap_out({"status": "register_failed", "http": st,
                                       **{k: v for k, v in reg.items() if k != "token"}}, 1)
            project_id, token = reg["project_id"], reg["token"]
            joined = {"joined" if found.get("project_id") else "registered": True, "key": reg.get("key"),
                      "local_key": bool(reg.get("local_key")), "role": reg.get("role")}
        base_args = {"project_id": project_id, "token": token, "harnesses": a.harness}
        done: list[str] = []
        pending: list[dict[str, Any]] = []
        for_agent: list[dict[str, Any]] = []
        legacy: Any = None
        for _ in range(3):
            st, plan = _http(base, "hub_setup_plan", {**base_args, "scan": _scan()})
            if st != 200:
                return _bootstrap_out({"status": "plan_failed", "http": st, **plan, "project_id": project_id, **joined}, 1)
            legacy = plan.get("legacy_1x") or legacy
            files: list[dict[str, str]] = []
            checks: list[dict[str, Any]] = []
            for s in plan["steps"]:
                sid, path = s["id"], Path(s.get("path") or ".")
                if s["op"] == "append_line":
                    if not s.get("already_present"):
                        prev = path.read_text(encoding="utf-8") if path.is_file() else ""
                        sep = "" if not prev or prev.endswith("\n") else "\n"
                        path.write_text(prev + sep + s["content"], encoding="utf-8")
                elif sid == "check_ignore":
                    HUB_DIR.mkdir(exist_ok=True)
                    checks.append({"name": "check_ignore", **_run(s["run"])})
                elif s["op"] == "write" and sid not in HANDOFF_STEPS:
                    if sid.startswith("entry:") and legacy:
                        pending.append({"id": sid, "reason": "1.x kit 흔적이 있어 진입 파일을 쓰지 않았다 — 전환은 사람이 정한다"})
                        continue
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(s["content"], encoding="utf-8")
                    if s.get("mode") == "600":
                        os.chmod(path, 0o600)
                    files.append({"path": s["path"], "sha256": _sha(path)})
                elif s["op"] == "write":  # 에이전트에게 넘긴다 — 이미 지시대로 있으면 확인만
                    if path.is_file() and _sha(path) == s.get("sha256_after"):
                        files.append({"path": s["path"], "sha256": _sha(path)})
                    else:
                        for_agent.append({"id": sid, "op": "write", "path": s["path"], "content": s["content"],
                                          "note": s.get("note", "")})
                elif sid == "harness:codex":
                    checks.append({"name": sid, **_run(s["run"])})
                else:  # antigravity — 사용자 범위에 토큰 평문: 사람이 정한다. 명령은 토큰을 가린다
                    pending.append({"id": sid, "reason": "사람이 정한다", "warning": s.get("warning", ""),
                                    "run_masked": [("Authorization: Bearer <WORKFLOW_HUB_TOKEN>" if "Bearer" in x else x)
                                                   for x in s.get("run", [])]})
            for b in plan.get("blocked") or []:
                pending.append({"id": b["id"], "reason": b.get("message", b.get("reason", ""))})
            st, conf = _http(base, "hub_setup_confirm", {"project_id": project_id, "token": token,
                                                          "files": files, "checks": checks})
            if st != 200:
                return _bootstrap_out({"status": "confirm_failed", "http": st, **conf}, 1)
            done += conf.get("confirmed", [])
            if conf.get("error_code") == "ignore_not_effective":
                return _bootstrap_out({"status": "ignore_not_effective", "unconfirmed": conf["unconfirmed"],
                                       "next": ".gitignore 의 /.workflow-hub/ 가 먹지 않는다 — 사람에게 보인다 (토큰 파일을 쓰지 않았다)"}, 1)
            if plan["stage"] == "files":
                complete = bool(conf.get("setup_complete"))
                break
        else:
            complete = False
    except Unreachable as e:
        return _bootstrap_out({"status": "unreachable", "hub": base, "reason": str(e)}, 2)
    pending_ids = {p["id"] for p in pending} | {f["id"] for f in for_agent}
    out = {"status": "complete" if complete else "partial", "hub": base, "project_id": project_id,
           "callsign": a.callsign, **joined, "confirmed": done, "for_agent": for_agent, "pending": pending,
           "legacy_1x": legacy,
           "next": ("셋업 완료 — .workflow-hub/env 의 WORKFLOW_HUB_TOKEN 을 환경에 올리고 하네스를 다시 시작한 뒤 hub_session_start"
                    if complete else
                    "for_agent 의 파일을 내용 그대로 쓰고(하네스가 승인을 물으면 사람이 답한다) 이 명령을 다시 부른다. "
                    "pending 은 사람에게 보인다" if pending_ids else "이 명령을 다시 부른다")}
    return _bootstrap_out(out, 0 if complete else 3)


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
    if cmd == "bootstrap":
        return cmd_bootstrap(rest)
    if cmd == "move" and len(rest) == 2:
        return cmd_move(rest[0], rest[1])
    if cmd == "migrate" and rest[:1] == ["plan"]:
        return cmd_migrate_plan()
    if cmd == "migrate" and len(rest) == 3 and rest[0] == "import":
        return cmd_migrate_import(rest[1], rest[2])
    print(f"hub_client: 모르는 명령 {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
