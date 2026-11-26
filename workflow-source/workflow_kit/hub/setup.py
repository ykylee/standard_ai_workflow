"""부트스트랩 셋업 — 쓰기 지시 · 확인 (hub_spec §5.1 · §6.1, 요구 R2.4 · R2.5 · R2.5a · R4.2 · R7.4~R7.6).

원격 MCP 는 작업 환경의 파일을 쓸 수 없다. 허브는 **쓰기 지시**(경로 · 내용 · sha256 · 확인 방법)를
돌려주고, 에이전트가 쓴 뒤 ``hub_setup_confirm`` 이 해시 · 명령 결과를 대조한다 (I1).

단계 (앞 단계가 확인돼야 다음 지시가 나온다):
    1. ``gitignore``  — ``.gitignore`` 에 ``/.workflow-hub/`` + ``git check-ignore -v .workflow-hub/env`` 확인
    2. ``env``        — ``.workflow-hub/env`` (토큰). **1 이 확인되기 전에는 지시하지 않는다** (요구 R4.2)
    ``entry:<하네스>`` — 진입 파일 렌더 영역 (로컬에서 고친 영역이면 지시 없이 멈춤; 1.x 는 전환 표식 커밋 뒤 시작 안내만 제한 갱신)
       ``harness:<하네스>`` — 하네스 MCP 설정 (환경 변수 참조, Antigravity 만 사용자 범위 + 경고)
    3. 모두 확인되면 콜사인의 ``setup_complete`` = 1. 하네스를 다시 연결하라는 안내.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from workflow_kit.common.hub_marker import MARKER_REL
from workflow_kit.hub import render
from workflow_kit.hub.errors import HubError, invalid_field, unauthorized
from workflow_kit.hub.store import Ctx, Principal, Store, _iso

GITIGNORE_LINE = "/.workflow-hub/"
ENV_PATH = ".workflow-hub/env"
#: 진입 파일 · 설정에 남은 1.x kit 의 표식 — 셋업이 1.x 흔적을 알리는 근거 (테스트베드 실측: 알리지 않아 에이전트가
#: '1.x 흔적 없음' 으로 보고했다).
LEGACY_1X_MARKERS = ("standard-ai-workflow-kit:", "generated-from: core/global_workflow_standard.md", "workflow_kit.server.")
MCP_JSON = ".mcp.json"
SERVER_NAME = "workflow-hub"
TOKEN_ENV = "WORKFLOW_HUB_TOKEN"
# Claude Code 는 headersHelper 가 낸 헤더로 정적 headers 를 덮어쓴다 — 콜사인 토큰을 .workflow-hub/env 에서 바로 읽어
# 셸 환경에 토큰을 올리지 않아도 붙는다 (2026-11-25 실측: 변수 없이 ${VAR} 만이면 부트스트랩 도구 6종).
# 정적 headers 의 환경 변수 참조는 headersHelper 를 모르는 하네스를 위해 남긴다.
HEADERS_HELPER = "python3 .workflow-hub/hub_client.py mcp-headers"
MIGRATION_MARKER_FORMAT = "workflow-hub-migrated/1"
CHECK_IGNORE = ["git", "check-ignore", "-v", ENV_PATH]
AGY_WARNING = (
    "Antigravity 는 MCP 헤더의 환경 변수 참조를 확장하지 않는다 (requirements §16.3). 그래서 토큰 값이 "
    "사용자 범위 설정 ~/.gemini/config/mcp_config.json 에 평문으로 남는다 — 이 파일을 공유하지 말고, "
    "토큰을 거두려면 허브 소유자에게 콜사인 거두기를 요청한다 (요구 R2.5a)."
)


def principal_for(store: Store, project_id: str, token: str, ctx: Ctx) -> Principal:
    """부트스트랩 묶음 셋업 도구의 인자 토큰 인증 (DS4)."""
    p = store.authenticate(token, ctx.now)
    if p is None or p.kind != "callsign":
        raise unauthorized()
    if p.project_id != project_id:
        raise HubError(403, "forbidden", "이 토큰은 다른 프로젝트의 것이다")
    return p


def check_ignore_ok(rc: int, output: str) -> tuple[bool, str]:
    """``git check-ignore -v`` 결과 판정. 부정(``!``) 규칙 일치 · 미일치(추적 중 포함)는 실패."""
    if rc != 0:
        return False, "무시되지 않는다 (rc != 0 — 규칙이 없거나 이미 추적 중인 파일)"
    line = (output or "").strip().splitlines()
    if not line:
        return False, "출력이 없다"
    head = line[0].split("\t", 1)[0]
    parts = head.split(":", 2)
    pattern = parts[2] if len(parts) == 3 else head
    if pattern.startswith("!"):
        return False, f"부정 규칙에 걸렸다: {pattern}"
    if ENV_PATH not in line[0]:
        return False, f"다른 경로의 결과다: {line[0]}"
    return True, ""


def _mcp_json(existing: str | None, url: str, path: str = MCP_JSON, headers_helper: bool = False) -> str:
    try:
        data = json.loads(existing) if existing and existing.strip() else {}
    except json.JSONDecodeError as exc:
        raise HubError(409, "invalid_existing_file", f"{path} 이 JSON 이 아니다 — 손으로 고친 뒤 다시: {exc}") from exc
    if not isinstance(data, dict):
        raise HubError(409, "invalid_existing_file", f"{path} 의 최상위가 객체가 아니다")
    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise HubError(409, "invalid_existing_file", f"{path} 의 mcpServers 가 객체가 아니다")
    server: dict[str, Any] = {
        "type": "http",
        "url": url,
        "headers": {"Authorization": "Bearer ${" + TOKEN_ENV + "}"},
    }
    if headers_helper:
        server["headersHelper"] = HEADERS_HELPER
    servers[SERVER_NAME] = server
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _migration_marker_ready(files: dict[str, Any], project_id: str, hub_url: str) -> bool:
    raw = files.get(MARKER_REL)
    if not isinstance(raw, str):
        return False
    try:
        marker = json.loads(raw)
    except json.JSONDecodeError:
        return False
    return (isinstance(marker, dict) and marker.get("format") == MIGRATION_MARKER_FORMAT
            and marker.get("project_id") == project_id
            and str(marker.get("hub", "")).rstrip("/") == hub_url.rstrip("/"))


class Setup:
    def __init__(self, store: Store, public_url: str) -> None:
        self.store = store
        self.public_url = public_url.rstrip("/")

    @property
    def mcp_url(self) -> str:
        return f"{self.public_url}/mcp"

    # --- 상태 ---------------------------------------------------------------------

    @staticmethod
    def _steps(conn: sqlite3.Connection, p: Principal) -> dict[str, sqlite3.Row]:
        return {r["step_id"]: r for r in conn.execute(
            "SELECT * FROM setup_step WHERE project_id = ? AND callsign = ?", (p.project_id, p.callsign))}

    @staticmethod
    def _issue(conn: sqlite3.Connection, ctx: Ctx, p: Principal, step_id: str, kind: str, path: str = "",
               sha: str = "", guide_version: str = "") -> None:
        conn.execute(
            "INSERT INTO setup_step (project_id, callsign, step_id, kind, path, sha256, guide_version, status, issued_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'issued', ?) "
            "ON CONFLICT(project_id, callsign, step_id) DO UPDATE SET kind = excluded.kind, path = excluded.path, "
            "guide_version = excluded.guide_version, "
            # 같은 내용으로 이미 확인된 단계는 확인 상태를 지킨다 (재계획이 완료를 되돌리지 않게)
            "status = CASE WHEN setup_step.status = 'confirmed' AND setup_step.sha256 = excluded.sha256 "
            "THEN 'confirmed' ELSE 'issued' END, "
            "confirmed_at = CASE WHEN setup_step.status = 'confirmed' AND setup_step.sha256 = excluded.sha256 "
            "THEN setup_step.confirmed_at ELSE NULL END, "
            "sha256 = excluded.sha256, detail = '', issued_at = excluded.issued_at",
            (p.project_id, p.callsign, step_id, kind, path, sha, guide_version, _iso(ctx.now)),
        )

    def project_guide(self, conn: sqlite3.Connection, project_id: str) -> tuple[str, str, int]:
        proj = conn.execute("SELECT display_name FROM project WHERE id = ?", (project_id,)).fetchone()
        row = conn.execute(
            "SELECT version, body_md FROM guide WHERE project_id = ? ORDER BY version DESC LIMIT 1", (project_id,)
        ).fetchone()
        return proj["display_name"], (row["body_md"] if row else ""), (row["version"] if row else 0)

    # --- 계획 -----------------------------------------------------------------------

    def plan(self, ctx: Ctx, project_id: str, token: str, harnesses: list[str], scan: dict[str, Any]) -> dict[str, Any]:
        p = principal_for(self.store, project_id, token, ctx)
        if not harnesses:
            raise invalid_field("harnesses", f"하나 이상 — {', '.join(render.SUPPORTED_HARNESSES)}")
        setup_profiles: dict[str, dict[str, str]] = {}
        for h in harnesses:
            if h in render.SUPPORTED_HARNESSES:
                setup_profiles[h] = {"entry_file": render.entry_file(h), "kind": "builtin"}
                continue
            from workflow_kit.hub.harness_intake import registered_setup_profile

            with self.store.read() as conn:
                profile = registered_setup_profile(conn, h)
            if profile is None:
                return {
                    "stage": "harness_support",
                    "steps": [],
                    "blocked": [{"id": f"harness:{h}", "reason": "setup_profile_required",
                                 "message": f"{h} 는 아직 셋업 프로필이 없다. hub_harness_report 로 하네스 정보와 mcp-http-json-v1 설정 후보를 제보하고 허브 관리자의 승인을 기다린다.",
                                 "report_tool": "hub_harness_report",
                                 "required_report_fields": ["entry_file_candidates", "mcp_config_candidates",
                                                             "config_formats (mcp-http-json-v1)", "mcp_transports (streamable-http)"]}],
                    "next": "hub_harness_report 제보 후 웹 허브 관리자 승인까지 파일을 수정하지 않는다",
                }
            setup_profiles[h] = profile
        files = scan.get("files") or {}
        if not isinstance(files, dict):
            raise invalid_field("scan.files", "경로 → 내용(없으면 null) 객체")
        extra = set(scan) - {"files", "relay"}
        if extra:
            raise HubError(400, "unknown_field", f"scan 의 모르는 칸: {', '.join(sorted(extra))}", {"fields": sorted(extra)})
        legacy = sorted(path for path, text in files.items()
                        if isinstance(text, str) and any(m in text for m in LEGACY_1X_MARKERS))
        migration_complete = _migration_marker_ready(files, project_id, self.public_url)
        legacy_entries = {profile["entry_file"] for profile in setup_profiles.values()} & set(legacy)
        entry_update_allowed = migration_complete or not legacy_entries
        legacy_1x = {"files": legacy,
                     "migration_complete": migration_complete,
                     "entry_update_allowed": entry_update_allowed,
                     "next": "1.x kit 흔적이 있다 — 전환은 사람이 선택 클라이언트로 한다: "
                             "python .workflow-hub/hub_client.py migrate plan → (표를 보이고 고른 종류로) migrate import "
                             "(hub_spec §6.6). 가져오기와 ai-workflow/HUB_MIGRATED.json 표식 커밋을 마친 뒤 셋업을 다시 실행하면 진입 안내를 갱신한다"} if legacy else None
        relay_scan = scan.get("relay") or {"required": False}
        if not isinstance(relay_scan, dict) or set(relay_scan) - {"required", "config_present", "status"}:
            raise invalid_field("scan.relay", "{required, config_present, status} 객체")
        if not isinstance(relay_scan.get("required", False), bool):
            raise invalid_field("scan.relay.required", "boolean")
        relay_advice = {"required": relay_scan.get("required", False),
                        "config_present": bool(relay_scan.get("config_present", False)),
                        "status": relay_scan.get("status"),
                        "next": "Python 우선: python -m workflow_kit hub relay status → 필요하면 init → allow add → serve"
                        if relay_scan.get("required") else "선택 사항 — 현재 셋업에서는 로컬 중계가 필요하지 않음"}
        with self.store.write() as conn:
            done = {k: r["status"] for k, r in self._steps(conn, p).items()}
            if done.get("gitignore") != "confirmed":
                self._issue(conn, ctx, p, "gitignore", "gitignore", ".gitignore")
                gi = files.get(".gitignore")
                lines = (gi or "").splitlines()
                return {
                    "stage": "gitignore",
                    "steps": [
                        {"id": "gitignore", "op": "append_line", "path": ".gitignore", "content": GITIGNORE_LINE + "\n",
                         "already_present": GITIGNORE_LINE in [ln.strip() for ln in lines]},
                        {"id": "check_ignore", "op": "run_and_report", "run": CHECK_IGNORE,
                         "note": "출력과 종료 코드를 hub_setup_confirm 의 checks 로 보낸다"},
                    ],
                    "next": "hub_setup_confirm — 이 단계가 확인되기 전에는 토큰 파일 지시를 내지 않는다 (요구 R4.2)",
                    "legacy_1x": legacy_1x,
                    "relay": relay_advice,
                }
            steps: list[dict[str, Any]] = []
            blocked: list[dict[str, Any]] = []
            env_text = (
                f"WORKFLOW_HUB_URL={self.public_url}\nWORKFLOW_HUB_PROJECT={p.project_id}\n"
                f"WORKFLOW_HUB_CALLSIGN={p.callsign}\n{TOKEN_ENV}={token}\n"
            )
            self._issue(conn, ctx, p, "env", "env", ENV_PATH, render.sha256(env_text))
            steps.append({"id": "env", "op": "write", "path": ENV_PATH, "content": env_text, "mode": "600",
                          "sha256_after": render.sha256(env_text),
                          "note": "POSIX 는 권한 600. Windows 는 사용자 프로필 ACL 을 따른다 — 적용 결과를 사실대로 보고 (요구 R4.3)"})
            display, guide_body, guide_ver = self.project_guide(conn, project_id)
            mcp_json_written = False
            dynamic_configs_written: set[str] = set()
            for h in harnesses:
                setup_profile = setup_profiles[h]
                path = setup_profile["entry_file"]
                region, version = render.render_region(h, project_id, display, guide_body, guide_ver,
                                                       entry_path=path if setup_profile["kind"] != "builtin" else None)
                existing = files.get(path)
                existing_text = existing if isinstance(existing, str) else None
                entry_has_legacy = existing_text is not None and any(m in existing_text for m in LEGACY_1X_MARKERS)
                migrated_existing = existing_text
                # 진입 파일이 막혀도 하네스 MCP 단계는 낸다 — 허브에 붙는 것과 지침을 바꾸는 것은 따로다.
                stop: tuple[str, str] | None = None
                merged: str | None = None
                if entry_has_legacy and not migration_complete:
                    stop = ("legacy_1x_requires_migration",
                            "1.x 작업 정본을 Hub로 가져오고 ai-workflow/HUB_MIGRATED.json 을 커밋한 뒤 다시 셋업한다")
                elif entry_has_legacy:
                    migrated_existing = render.migrate_legacy_start_guidance(existing_text or "")
                    if migrated_existing is None:
                        stop = ("legacy_entry_needs_review",
                                "진입 파일의 1.x 시작 안내가 표준 생성 문안과 다르다 — 사람이 Hub 경로로 고친 뒤 다시 셋업한다")
                if stop is None:
                    merged, why = render.merge_into(migrated_existing, region)
                    if merged is None:
                        stop = (why or "local_edit_detected", "렌더 영역이 허브가 낸 판과 다르다 — 덮어쓰지 않는다. 고칠 것은 허브에 지침 제안으로 (요구 R7.5)")
                if stop is not None:
                    blocked.append({"id": f"entry:{h}", "path": path, "reason": stop[0], "message": stop[1]})
                    self._issue(conn, ctx, p, f"entry:{h}", "entry", path)
                    # 막힌 단계도 남긴다 — 안 남기면 나머지만 확인돼도 셋업이 끝난 것으로 보인다
                    conn.execute("UPDATE setup_step SET status = 'unconfirmed', detail = ?, confirmed_at = NULL "
                                 "WHERE project_id = ? AND callsign = ? AND step_id = ?",
                                 (f"blocked: {stop[0]}", p.project_id, p.callsign, f"entry:{h}"))
                    conn.execute("UPDATE callsign SET setup_complete = 0 WHERE project_id = ? AND id = ?", (p.project_id, p.callsign))
                elif merged is not None:
                    self._issue(conn, ctx, p, f"entry:{h}", "entry", path, render.sha256(merged), version)
                    steps.append({"id": f"entry:{h}", "op": "write", "path": path, "content": merged,
                                  "sha256_after": render.sha256(merged), "guide_version": version,
                                  "note": "이 파일은 커밋한다 (D10)"})
                if h in ("claude-code", "minimax-code") and not mcp_json_written:
                    content = _mcp_json(files.get(MCP_JSON), self.mcp_url, headers_helper=True)
                    self._issue(conn, ctx, p, "harness:mcp-json", "harness", MCP_JSON, render.sha256(content))
                    steps.append({"id": "harness:mcp-json", "op": "write", "path": MCP_JSON, "content": content,
                                  "sha256_after": render.sha256(content),
                                  "note": "Claude Code · MiniMax Code 가 읽는다. 토큰 값은 이 파일에 없다 (요구 R2.5) — Claude Code 는 headersHelper 로 "
                                          f".workflow-hub/env 의 콜사인 토큰을 읽고, 헬퍼를 모르는 하네스는 환경 변수 {TOKEN_ENV} 참조로 붙는다. "
                                          "Claude Code 는 .mcp.json 을 민감 파일로 다뤄 쓰기에 사람 승인이 필요하다 — 비대화 실행에서 막히면 "
                                          "사람이 이 내용 그대로 만들고 sha256 확인만 맡긴다 (M-039 실측)"})
                    mcp_json_written = True
                elif h == "codex":
                    self._issue(conn, ctx, p, "harness:codex", "harness")
                    steps.append({"id": "harness:codex", "op": "run_and_report",
                                  "run": ["codex", "mcp", "add", SERVER_NAME, "--url", self.mcp_url,
                                          "--bearer-token-env-var", TOKEN_ENV],
                                  "note": "이 명령은 서버 항목을 다시 써 도구 승인 설정을 남기지 않는다. 대화형 Codex 는 허브 도구를 부를 "
                                          "때마다 사람에게 승인을 묻는다. 비대화 실행(codex exec)은 승인 정책이 never 라 그대로는 허브 도구를 "
                                          "못 부른다 — 사람이 실행마다 -c 'mcp_servers." + SERVER_NAME
                                          + ".default_tools_approval_mode=\"approve\"' 를 준다. 자동 승인은 사람의 선택이라 이 지시는 "
                                          "설정에 쓰지 않는다 (M-039 실측)"})
                elif h == "antigravity":
                    self._issue(conn, ctx, p, "harness:antigravity", "harness")
                    steps.append({"id": "harness:antigravity", "op": "user_scope_write",
                                  "run": ["agy", "mcp", "add", "--header", f"Authorization: Bearer {token}", SERVER_NAME, self.mcp_url],
                                  "path": "~/.gemini/config/mcp_config.json", "warning": AGY_WARNING})
                elif setup_profile["kind"] == "mcp-http-json-v1":
                    config_path = setup_profile["mcp_config_path"]
                    if config_path not in dynamic_configs_written:
                        content = _mcp_json(files.get(config_path), self.mcp_url, config_path)
                        step_id = f"harness:mcp-json:{h}"
                        self._issue(conn, ctx, p, step_id, "harness", config_path, render.sha256(content))
                        steps.append({"id": step_id, "op": "write", "path": config_path, "content": content,
                                      "sha256_after": render.sha256(content),
                                      "note": "관리자가 승인한 MCP Streamable HTTP JSON 프로필. 토큰은 환경 변수 참조만 저장한다."})
                        dynamic_configs_written.add(config_path)
            return {
                "stage": "files",
                "steps": steps,
                "blocked": blocked,
                # 1.x 흔적 (요구 R14.1) — 셋업은 전환을 하지 않는다. 사람에게 알리고 클라이언트 전환으로 안내한다.
                "legacy_1x": legacy_1x,
                "relay": relay_advice,
                "next": "hub_setup_confirm — 쓴 파일의 sha256 과 명령 결과를 보낸다. 끝나면 하네스를 다시 연결한다 "
                        f"(Claude Code 는 .workflow-hub/env 를 headersHelper 로 읽는다 — 그 밖의 하네스는 `{TOKEN_ENV}` 를 환경에 올린다)",
            }

    # --- 확인 -----------------------------------------------------------------------

    def confirm(self, ctx: Ctx, project_id: str, token: str, files: list[dict[str, Any]],
                checks: list[dict[str, Any]]) -> dict[str, Any]:
        p = principal_for(self.store, project_id, token, ctx)
        by_path: dict[str, str] = {}
        for f in files:
            if not isinstance(f, dict) or set(f) - {"path", "sha256"} or not isinstance(f.get("path"), str):
                raise invalid_field("files", "[{path, sha256}] 형태")
            by_path[f["path"]] = str(f.get("sha256") or "")
        by_check: dict[str, dict[str, Any]] = {}
        for c in checks:
            if not isinstance(c, dict) or set(c) - {"name", "rc", "output"} or not isinstance(c.get("name"), str):
                raise invalid_field("checks", "[{name, rc, output}] 형태")
            by_check[c["name"]] = c
        confirmed: list[str] = []
        unconfirmed: list[dict[str, str]] = []
        with self.store.write() as conn:
            steps = self._steps(conn, p)
            for sid, row in steps.items():
                if row["status"] == "confirmed":
                    continue
                ok, why = False, "보고가 없다"
                if sid == "gitignore":
                    ci = by_check.get("check_ignore")
                    if ci is not None:
                        ok, why = check_ignore_ok(int(ci.get("rc", 1)), str(ci.get("output", "")))
                elif row["kind"] in ("env", "entry") or (row["kind"] == "harness" and row["path"]):
                    got = by_path.get(row["path"])
                    if got is not None:
                        ok = bool(row["sha256"]) and got == row["sha256"]  # 막힌 단계는 지시한 내용이 없다
                        why = "" if ok else f"sha256 이 지시와 다르다 (지시 {row['sha256'][:12]}…, 받음 {got[:12]}…)"
                elif row["kind"] == "harness":
                    hc = by_check.get(sid)
                    if hc is not None:
                        ok = int(hc.get("rc", 1)) == 0
                        why = "" if ok else f"명령 실패 rc={hc.get('rc')}"
                if ok:
                    conn.execute(
                        "UPDATE setup_step SET status = 'confirmed', detail = '', confirmed_at = ? "
                        "WHERE project_id = ? AND callsign = ? AND step_id = ?",
                        (_iso(ctx.now), p.project_id, p.callsign, sid))
                    confirmed.append(sid)
                    if row["kind"] == "entry" and row["guide_version"]:
                        conn.execute("UPDATE callsign SET guide_version_seen = ? WHERE project_id = ? AND id = ?",
                                     (row["guide_version"], p.project_id, p.callsign))
                else:
                    if sid in by_check or row["path"] in by_path or sid == "gitignore" and "check_ignore" in by_check:
                        conn.execute(
                            "UPDATE setup_step SET status = 'unconfirmed', detail = ? "
                            "WHERE project_id = ? AND callsign = ? AND step_id = ?",
                            (why, p.project_id, p.callsign, sid))
                    unconfirmed.append({"id": sid, "reason": why})
            after = self._steps(conn, p)
            complete = bool(after) and "env" in after and all(r["status"] == "confirmed" for r in after.values())
            conn.execute("UPDATE callsign SET setup_complete = ? WHERE project_id = ? AND id = ?",
                         (1 if complete else 0, p.project_id, p.callsign))
            self.store._event(conn, ctx, p.project_id, "callsign", p.callsign or "", "setup_confirm", None,
                              {"confirmed": confirmed, "unconfirmed": [u["id"] for u in unconfirmed], "complete": complete},
                              p.callsign)
        gitignore_failed = any(u["id"] == "gitignore" for u in unconfirmed) and "check_ignore" in by_check
        return {
            "confirmed": confirmed,
            "unconfirmed": unconfirmed,
            "setup_complete": complete,
            "error_code": "ignore_not_effective" if gitignore_failed else None,
            "next": ("하네스를 다시 연결한다 — 토큰 환경 변수를 올린 뒤 hub_session_start" if complete
                     else "hub_setup_plan 을 다시 부른다 (확인된 단계는 건너뛴다)"),
        }

    def guide_render(self, ctx: Ctx, harness: str, current: str | None) -> dict[str, Any]:
        """세션 중 지침 갱신 — 그 하네스 진입 파일의 새 내용 (토큰 묶음, hub_spec §6.5)."""
        p = ctx.principal
        assert p is not None and p.project_id is not None
        with self.store.write() as conn:
            display, body, ver = self.project_guide(conn, p.project_id)
            entry_path = render.entry_file(harness) if harness in render.SUPPORTED_HARNESSES else None
            if entry_path is None:
                from workflow_kit.hub.harness_intake import registered_setup_profile

                profile = registered_setup_profile(conn, harness)
                if profile is None:
                    return {"path": None, "blocked": True, "reason": "setup_profile_required",
                            "next": "hub_harness_report 제보 후 허브 관리자 승인을 기다린다"}
                entry_path = profile["entry_file"]
            path = entry_path
            if current and any(m in current for m in LEGACY_1X_MARKERS) and "workflow-hub:begin" not in current:
                # hub_setup_plan 과 같은 판정 — 1.x 지침이 든 파일에 허브 영역을 덧붙이면 두 정본이 한 파일에서 부딪힌다
                return {"path": path, "guide_version": render.guide_version(ver), "blocked": True,
                        "reason": "legacy_1x_requires_migration"}
            region, version = render.render_region(harness, p.project_id, display, body, ver,
                                                   entry_path=path if harness not in render.SUPPORTED_HARNESSES else None)
            merged, why = render.merge_into(current, region)
            if merged is None:
                return {"path": path, "guide_version": version, "blocked": True, "reason": why}
            self._issue(conn, ctx, p, f"entry:{harness}", "entry", path, render.sha256(merged), version)
            return {"path": path, "guide_version": version, "blocked": False,
                    "step": {"id": f"entry:{harness}", "op": "write", "path": path, "content": merged,
                             "sha256_after": render.sha256(merged)}}

    def set_guide(self, ctx: Ctx, project_id: str, body: str, actor: str) -> dict[str, Any]:
        """프로젝트 지침 새 판 (로컬 admin — 제안 · 승인 흐름은 M-037)."""
        with self.store.write() as conn:
            if not conn.execute("SELECT 1 FROM project WHERE id = ?", (project_id,)).fetchone():
                raise HubError(404, "not_found", f"프로젝트가 없다: {project_id}")
            from workflow_kit.hub.guide import check_renderable

            display = conn.execute("SELECT display_name FROM project WHERE id = ?", (project_id,)).fetchone()["display_name"]
            check_renderable(project_id, display, body)  # 예산을 넘는 판은 세우지 않는다 (R7.2)
            row = conn.execute("SELECT MAX(version) AS v FROM guide WHERE project_id = ?", (project_id,)).fetchone()
            ver = (row["v"] or 0) + 1
            conn.execute("INSERT INTO guide (project_id, version, body_md, updated_by, updated_at) VALUES (?, ?, ?, ?, ?)",
                         (project_id, ver, body, actor, _iso(ctx.now)))
            self.store._event(conn, ctx, project_id, "guide", str(ver), "set", None, {"version": ver}, actor)
        return {"project_id": project_id, "version": ver, "guide_version": render.guide_version(ver)}
