#!/usr/bin/env python3
"""허브 선택 클라이언트 (M-036 WBS-36.3 B) — 허브를 실제로 내렸다 올리며 보낼편지함 · 캐시를 잰다.

정본: ``core/hub_spec.md`` §7 (요구 R12.1 · R12.2 · R12.3 · D4).

1. 내려받기 — ``/v1/bootstrap/hub_client.py`` 가 토큰 없이 패키지 원문 그대로, 큐에 넣는 도구는 모두 request_id 를 받는 도구
2. 꺼진 동안 — 쓰기는 보낼편지함에 쌓이고(exit 3) 읽기는 쌓이지 않는다(exit 2), 캐시 없으면 '허브 미확인 · 캐시 없음'
3. 다시 켜지면 — 오래된 것부터 보내고 비운다, 같은 항목을 두 번 보내도 한 번만 반영 (request_id)
4. 409 — 자동 병합하지 않고 항목이 남고 보고된다 (D4)
5. 세션 시작 — 남은 수가 hub 보고에 실린다, 클라이언트 없으면 'none', 꺼지면 캐시로 연다 (R12.1 · R12.3)
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 300

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/check_hub_core.py",
)

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_hub_core import Hub  # noqa: E402
from workflow_kit.hub.tools import TOOLS  # noqa: E402

CLIENT_SRC = SOURCE_ROOT / "workflow_kit" / "hub" / "client" / "hub_client.py"
_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


class Client:
    """저장소 뿌리(임시)에서 내려받은 hub_client.py 를 돌린다 — 에이전트가 하는 그대로."""

    def __init__(self, repo: Path) -> None:
        self.repo = repo

    def env(self, url: str, token: str) -> None:
        d = self.repo / ".workflow-hub"
        d.mkdir(parents=True, exist_ok=True)
        (d / "env").write_text(f"WORKFLOW_HUB_URL={url}\nWORKFLOW_HUB_TOKEN={token}\n", encoding="utf-8")

    def run(self, *args: str) -> tuple[int, dict[str, Any]]:
        cp = subprocess.run([sys.executable, ".workflow-hub/hub_client.py", *args], cwd=self.repo, capture_output=True,
                            text=True, encoding="utf-8", timeout=60)
        try:
            return cp.returncode, json.loads(cp.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return cp.returncode, {"stdout": cp.stdout[-500:], "stderr": cp.stderr[-500:]}

    def outbox(self) -> list[Path]:
        d = self.repo / ".workflow-hub" / "outbox"
        return sorted(d.glob("*.json")) if d.is_dir() else []


def run(tmp: Path) -> None:
    db = tmp / "hub.db"
    hub = Hub(db)
    hubs = [hub]
    try:
        reg = hub.call("hub_project_register", {"remote_url": "git@github.com:acme/cli.git", "display_name": "Cli",
                                                 "callsign": "agent-c", "kind": "agent"})[1]
        tok = reg["token"]
        # --- 1. 내려받기 -------------------------------------------------------------
        with urllib.request.urlopen(hub.base + "/v1/bootstrap/hub_client.py", timeout=10) as r:
            src = r.read().decode("utf-8")
        repo = tmp / "repo"
        (repo / ".workflow-hub").mkdir(parents=True)
        (repo / ".workflow-hub" / "hub_client.py").write_text(src, encoding="utf-8")
        ns: dict[str, Any] = {}
        exec(compile(src, "hub_client.py", "exec"), ns)  # noqa: S102 — 내려받은 원문의 선언을 읽는다
        with_rid = {name for name, spec in TOOLS.items() if "request_id" in spec.properties}
        stray = sorted(set(ns["QUEUEABLE"]) - with_rid)
        problems = []
        if src != CLIENT_SRC.read_text(encoding="utf-8"):
            problems.append("내려받은 원문이 패키지 원문과 다르다")
        if stray:
            problems.append(f"request_id 를 받지 않는 도구를 큐에 넣는다 (허브가 모르는 인자로 거절): {stray}")
        _record("case 1 내려받기 — 토큰 없이 원문 그대로 · 큐 도구 ⊆ request_id 도구", not problems, "; ".join(problems))

        cli = Client(repo)
        cli.env(hub.base, tok)
        rc, created = cli.run("call", "hub_task_create", json.dumps({"title": "보낼편지함 대상", "status": "in_progress"}))
        task = created.get("task", {})
        tid, ver = task.get("id"), task.get("version")

        # --- 2. 꺼진 동안 ------------------------------------------------------------
        hub.stop()
        rc_w1, q1 = cli.run("call", "hub_task_progress", json.dumps({"id": tid, "note": "꺼진 동안 1"}))
        rc_w2, q2 = cli.run("call", "hub_task_update", json.dumps({"id": tid, "expected_version": ver,
                                                                   "values": {"title": "꺼진 동안 고친 제목"}}))
        rc_w3, _q3 = cli.run("call", "hub_task_progress", json.dumps({"id": tid, "note": "꺼진 동안 2"}))
        rc_r, r_read = cli.run("call", "hub_task_get", json.dumps({"id": tid}))
        rc_ss, ss_down = cli.run("session-start")
        rc_st, st = cli.run("status")
        problems = []
        if rc != 0 or not tid:
            problems.append(f"켜진 동안 만들기 {rc} {created}")
        if (rc_w1, q1.get("status"), rc_w2, q2.get("status"), rc_w3) != (3, "queued", 3, "queued", 3):
            problems.append(f"쓰기 큐 {rc_w1} {q1} · {rc_w2} {q2}")
        if rc_r != 2 or r_read.get("queued") is not False:
            problems.append(f"읽기가 쌓였다 {rc_r} {r_read}")
        if rc_ss != 3 or ss_down.get("report") != "허브 미확인 · 캐시 없음":
            problems.append(f"캐시 없는 시작 {rc_ss} {ss_down}")
        if st.get("outbox_pending") != 3 or len(cli.outbox()) != 3:
            problems.append(f"보낼편지함 {st}")
        _record("case 2 꺼진 동안 — 쓰기만 쌓인다 · 캐시 없음", not problems, "; ".join(problems))

        # --- 3 · 4. 다시 켜지면 --------------------------------------------------------
        hub = Hub(db)
        hubs.append(hub)
        cli.env(hub.base, tok)
        # 같은 항목을 한 번 더 보낸다 — 첫 항목(진행 한 줄)을 복제해 두면 request_id 가 같다
        first = cli.outbox()[0]
        # 원본 바로 옆에 정렬되는 이름 — 맨 뒤에 두면 역순 보내기에서 우연히 같은 마지막 값이 나온다
        dup = first.with_name(first.stem + "-dup.json")
        shutil.copyfile(first, dup)
        # 409 를 만든다 — 다른 쪽이 그 사이 task 를 고쳤다
        hub.call("hub_task_update", {"id": tid, "expected_version": ver, "values": {"title": "다른 쪽이 고침"}}, tok)
        rc_f, fl = cli.run("flush")
        after = hub.call("hub_task_get", {"id": tid}, tok)[1].get("task", {})
        events = hub.call("hub_events", {"target_kind": "task", "target_id": tid}, tok)[1].get("events", [])
        progress_events = [e for e in events if e.get("op") == "progress"]
        remaining = cli.outbox()
        problems = []
        # 순서 — 진행 1 → 2 순으로 쌓였으니 오래된 것부터 보내면 마지막 값은 2 다
        if len(fl.get("sent", [])) != 3 or not after.get("progress_note", "").endswith("꺼진 동안 2"):
            problems.append(f"보냄 {fl.get('sent')} · 진행 {after.get('progress_note')!r} (기대: 마지막이 '꺼진 동안 2')")
        if len(progress_events) != 2:
            problems.append(f"같은 항목 두 번 → 진행 반영 {len(progress_events)} (기대 2 — 1 · 2 각 한 번, request_id 멱등)")
        _record("case 3 다시 켜지면 — 오래된 것부터 보냄 · 두 번 보내도 한 번 반영", not problems, "; ".join(problems))
        problems = []
        if rc_f != 1 or len(fl.get("conflicts", [])) != 1 or fl["conflicts"][0].get("tool") != "hub_task_update":
            problems.append(f"409 보고 {rc_f} {fl.get('conflicts')}")
        if len(remaining) != 1 or json.loads(remaining[0].read_text(encoding="utf-8"))["tool"] != "hub_task_update":
            problems.append(f"409 항목이 남지 않았다: {[p.name for p in remaining]}")
        if after.get("title") != "다른 쪽이 고침":
            problems.append(f"자동 병합됐다: 제목 {after.get('title')!r}")
        _record("case 4 409 — 자동 병합 없이 남고 보고", not problems, "; ".join(problems))

        # --- 5. 세션 시작 --------------------------------------------------------------
        rc5, ss = cli.run("session-start")
        bare = hub.call("hub_session_start", {}, tok)[1]
        hub.stop()
        rc5d, ss_cached = cli.run("session-start")
        problems = []
        lc = ss.get("hub", {}).get("local_client", {})
        if rc5 != 0 or lc.get("status") != "present" or lc.get("outbox_pending") != 1 or "flush" not in lc.get("notice", ""):
            problems.append(f"클라이언트 보고 {rc5} {lc}")
        if bare.get("hub", {}).get("local_client", {}).get("status") != "none":
            problems.append(f"클라이언트 없는 보고 {bare.get('hub', {}).get('local_client')}")
        if rc5d != 3 or not str(ss_cached.get("report", "")).startswith("허브 미확인 · 캐시 (") \
                or ss_cached.get("cached", {}).get("hub", {}).get("my_tasks") is None or ss_cached.get("outbox_pending") != 1:
            problems.append(f"캐시로 열기 {rc5d} {str(ss_cached)[:200]}")
        _record("case 5 세션 시작 — 남은 수 · 클라이언트 없음 · 캐시로 열기", not problems, "; ".join(problems))

        # --- 6. MCP 헤더 도우미 (Claude Code headersHelper) ----------------------------------
        # 하네스가 저장소 밖 cwd 에서 돌려도 이 파일 옆 env 를 읽는다 · 셸 환경 변수 없이 · 낸 헤더로 실제 인증된다
        hub = Hub(db)
        hubs.append(hub)
        cli.env(hub.base, tok)
        clean = {k: v for k, v in os.environ.items() if k not in ("WORKFLOW_HUB_TOKEN", "WORKFLOW_HUB_URL")}
        elsewhere = tmp / "elsewhere"
        elsewhere.mkdir()
        script = str(repo / ".workflow-hub" / "hub_client.py")
        cp6 = subprocess.run([sys.executable, script, "mcp-headers"], cwd=elsewhere, env=clean, capture_output=True,
                             text=True, encoding="utf-8", timeout=30)
        problems = []
        try:
            headers = json.loads(cp6.stdout)
        except ValueError:
            headers = {}
        if cp6.returncode != 0 or headers != {"Authorization": f"Bearer {tok}"} or len(cp6.stdout.strip().splitlines()) != 1:
            problems.append(f"헤더 출력 rc={cp6.returncode} keys={sorted(headers)} lines={len(cp6.stdout.splitlines())}")
        req = urllib.request.Request(hub.base + "/v1/tools/hub_whoami", data=b"{}", method="POST",
                                     headers={"content-type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                who = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            who = {"http": e.code}
        if json.dumps(who, ensure_ascii=False).find("agent-c") < 0:
            problems.append(f"낸 헤더로 인증되지 않았다: {str(who)[:200]}")
        (repo / ".workflow-hub" / "env").write_text(f"WORKFLOW_HUB_URL={hub.base}\n", encoding="utf-8")
        cp6b = subprocess.run([sys.executable, script, "mcp-headers"], cwd=elsewhere, env=clean, capture_output=True,
                              text=True, encoding="utf-8", timeout=30)
        if cp6b.returncode == 0 or cp6b.stdout.strip() or "WORKFLOW_HUB_TOKEN" not in cp6b.stderr:
            problems.append(f"토큰 없을 때 rc={cp6b.returncode} stdout={cp6b.stdout!r} (기대: 0 아님 · 빈 stdout · 이유)")
        _record("case 6 MCP 헤더 도우미 — 파일 옆 env · 환경 변수 없이 · 실제 인증 · 토큰 없으면 실패", not problems,
                "; ".join(problems))
    finally:
        for h in hubs:
            h.stop()


def main() -> int:
    print("=== 허브 선택 클라이언트 (M-036 WBS-36.3 B) ===")
    with tempfile.TemporaryDirectory(prefix="hubcli-") as d:
        try:
            run(Path(d))
        except Exception as exc:  # noqa: BLE001 — 예외도 판정으로
            _record("run (예외)", False, repr(exc))
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
