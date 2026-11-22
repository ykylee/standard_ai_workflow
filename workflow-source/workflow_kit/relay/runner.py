"""중계 한 바퀴 — 폴링 → 세션 요청 실행(허용 목록 · 상한) → 메시지 넣기 → 결과 보고 (스펙 §9)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from workflow_kit.relay import adapters, config
from workflow_kit.relay.adapters import Handle
from workflow_kit.relay.conn import HubError, HubUnreachable, post

FIRST_PROMPT = (
    "이 세션은 PC 중계가 워크플로우 허브의 세션 요청 {request} 로 띄운 **일하는 세션**이다. 먼저 "
    "hub_session_start(session={{\"harness\": \"{harness}\", \"kind\": \"worker\", "
    "\"delivery\": [\"adapter\", \"piggyback\", \"wait\"], \"spawn_request\": \"{request}\"}}) 를 부르고, 진입 파일의 "
    "워크플로우 허브 규칙을 따른다. 오케스트레이터가 남긴 지시: {prompt}"
)


class Relay:
    def __init__(self, log: Callable[[str], None] = print) -> None:
        self.cfg = config.read_json("relay.json", {})
        self.token = config.read_token()
        if not self.cfg.get("hub") or not self.token:
            raise SystemExit("relay: 등록 전이다 — `python -m workflow_kit hub relay init --hub URL --invite CODE --name NAME`")
        self.handles: dict[str, Handle] = {}       # 세션 요청 ID → 띄운 프로세스
        self.alias_of: dict[str, str] = {}         # 세션 요청 ID → 허용 목록 별칭
        self.session_of: dict[str, str] = {}       # 세션 ID → 세션 요청 ID
        self.seen: dict[str, set[str]] = {}        # 세션 ID → 넣은 메시지 ID (재전달 중복 거름)
        self.log = log
        self.last: dict[str, Any] = {}

    def _post(self, path: str, body: dict[str, Any], timeout: float = 40.0) -> dict[str, Any]:
        return post(str(self.cfg["hub"]), path, body, self.token, timeout)

    def _session_states(self) -> list[dict[str, str]]:
        out = []
        for sid, rid in self.session_of.items():
            h = self.handles.get(rid)
            if h is not None:
                out.append({"session": sid, "status": adapters.get(h.harness).status(h)})
        return out

    def once(self, wait_s: int = 25) -> dict[str, Any]:
        """폴링 한 번 + 처리. 일시정지면 폴링하지 않는다 — 허브의 승인된 요청은 그대로 남는다."""
        state = config.read_json("relay-state.json", {})
        if state.get("paused"):
            return {"paused": True}
        entries = config.load_allow()
        got = self._post("/v1/relay/poll", {"wait_s": wait_s, "sessions": self._session_states(),
                                            "allow_digest": config.allow_digest(entries)}, timeout=wait_s + 15)
        for s in got.get("sessions", []):
            self.session_of[s["session"]] = s["request"]
        for d in got.get("dispatch", []):
            self._dispatch(d, entries)
        for s in got.get("deliver", []):
            self._deliver(s)
        self.last = got
        return got

    def _result(self, d: dict[str, Any], state: str, result: dict[str, Any]) -> None:
        self._post("/v1/relay/result", {"project_id": d["project_id"], "request": d["request"], "state": state,
                                        "result": result})

    def _dispatch(self, d: dict[str, Any], entries: list[dict[str, Any]]) -> None:
        target = d.get("target") or {}
        if d.get("kind") == "stop":
            rid = self.session_of.get(str(target.get("session")))
            h = self.handles.get(rid or "")
            if h is None:
                self._result(d, "failed", {"reason": "이 중계가 띄운 세션을 찾지 못했다"})
                return
            adapters.get(h.harness).stop(h)
            self._result(d, "done", {"stopped": target.get("session")})
            self.log(f"stop {target.get('session')}")
            return
        live = {rid: h for rid, h in self.handles.items() if h.alive()}
        if len(live) >= config.MAX_SESSIONS:
            self._result(d, "refused_by_host", {"reason": f"이 PC 의 동시 세션 상한 {config.MAX_SESSIONS}"})
            return
        by_alias: dict[str, int] = {}
        for rid in live:
            by_alias[self.alias_of.get(rid, "")] = by_alias.get(self.alias_of.get(rid, ""), 0) + 1
        entry, why = config.check_request(entries, str(d["project_id"]), target, by_alias)
        if entry is None:
            self._result(d, "refused_by_host", {"reason": why})
            self.log(f"refuse {d['request']}: {why}")
            return
        harness = str(target["harness"])
        try:
            adapter = adapters.get(harness)
            prompt = FIRST_PROMPT.format(request=d["request"], harness=harness, prompt=target.get("prompt") or "(없음)")
            h = adapter.spawn(Path(entry["path"]), prompt, str(target.get("permission_mode") or "default"))
        except Exception as exc:  # noqa: BLE001 — 실패는 결과로 보고한다
            self._result(d, "failed", {"reason": f"{type(exc).__name__}: {exc}"[:300]})
            return
        self.handles[d["request"]] = h
        self.alias_of[d["request"]] = str(entry["alias"])
        self._result(d, "done", {"harness": harness, "pid": h.proc.pid, "harness_session_id": h.harness_session_id})
        self.log(f"spawn {d['request']} → {harness} pid {h.proc.pid}")

    def _deliver(self, s: dict[str, Any]) -> None:
        rid = self.session_of.get(s["session"])
        h = self.handles.get(rid or "")
        if h is None or not h.alive():
            return  # 이 실행이 띄운 것이 아니다 — 메시지는 ack 전까지 허브에 남아 편승 · 대기로도 간다
        seen = self.seen.setdefault(s["session"], set())
        for m in s.get("messages", []):
            if m["id"] in seen:
                continue  # 재전달 (실림 ≠ 소비) — 같은 프로세스에는 한 번만 넣는다
            text = (f"[워크플로우 허브 받은편지함 — {m['kind']} {m['id']} · from {m['from'].get('callsign')}"
                    f"{' (오케스트레이터)' if m['from'].get('orchestrator') else ''}] {m['body']} "
                    f"— 확인: hub_inbox_ack(session=\"{s['session']}\", message_id=\"{m['id']}\", decision=…)")
            how = adapters.get(h.harness).deliver(h, text)
            seen.add(m["id"])
            self.log(f"deliver {m['id']} → {s['session']} ({how})")

    def stop_all(self) -> None:
        for h in self.handles.values():
            if h.alive():
                adapters.get(h.harness).stop(h)

    def serve(self, *, once: bool = False, wait_s: int = 25) -> int:
        backoff = 1.0
        try:
            while True:
                try:
                    self.once(wait_s)
                    backoff = 1.0
                except HubUnreachable as e:
                    self.log(f"허브에 닿지 않는다: {e} — {backoff:.0f}초 뒤 다시")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60.0)
                except HubError as e:
                    self.log(f"허브 오류: {e}")
                    if e.status == 401:
                        return 3  # 거둔 토큰 — 다시 등록해야 한다
                    time.sleep(5)
                if once:
                    return 0
                if config.read_json("relay-state.json", {}).get("paused"):
                    time.sleep(2)
        finally:
            if not once:
                self.stop_all()
