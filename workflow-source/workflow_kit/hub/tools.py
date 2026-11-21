"""허브 도구 표 — MCP 와 HTTP 가 **같은 함수 · 같은 인자 · 같은 결과** (hub_spec §4, DS5 · 요구 R2.7).

묶음 (hub_spec §4.4 · §4.5):
    ``bootstrap`` — 토큰 없이 부른다 (요구 R2.3, I2)
    ``token``     — 콜사인 토큰이 있어야 보이고 부를 수 있다

인자 검사는 여기 한 곳이다 — 모르는 인자는 거절한다 (hub_spec §1-5, 요구 R0.6).
M-033 범위: 등록 · 합류 · task CRUD · 맡기 · 진행 · 커밋 묶기 · 이력. 셋업 지시(M-034) ·
게이트와 닫기(M-035) 는 그 마일스톤이 이 표에 더한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from workflow_kit.hub.errors import HubError, invalid_field, unauthorized, unknown_field
from workflow_kit.hub.session import SessionStart
from workflow_kit.hub.setup import Setup
from workflow_kit.hub.store import Ctx, Store, scan_secrets

Handler = Callable[[Store, Ctx, dict[str, Any]], dict[str, Any]]

_STR = {"type": "string"}
_INT = {"type": "integer"}
_OBJ = {"type": "object"}
_ARR = {"type": "array"}
_REQ_ID = {"type": "string", "description": "멱등 키 — 같은 값으로 다시 보내면 처음 결과를 돌려준다"}


@dataclass(frozen=True)
class ToolSpec:
    name: str
    bundle: str
    description: str
    properties: dict[str, dict[str, Any]]
    required: tuple[str, ...]
    handler: Handler

    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"contract": {"type": "string"}, **self.properties},
            "required": list(self.required),
            "additionalProperties": False,
        }


_PY_TYPES: dict[str, tuple[type, ...]] = {"string": (str,), "integer": (int,), "object": (dict,), "array": (list,)}


def validate_args(spec: ToolSpec, args: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(args, dict):
        raise invalid_field("arguments", "객체여야 한다")
    allowed = set(spec.properties) | {"contract"}
    extra = set(args) - allowed
    if extra:
        raise unknown_field(sorted(extra))
    for name in spec.required:
        if args.get(name) is None:
            raise invalid_field(name, "필수")
    for name, value in args.items():
        if value is None or name == "contract":
            continue
        want = spec.properties[name].get("type")
        types = _PY_TYPES.get(str(want))
        if types and (not isinstance(value, types) or (want == "integer" and isinstance(value, bool))):
            raise invalid_field(name, f"{want} 이어야 한다")
    contract = args.get("contract")
    if contract is not None and contract != "hub/1":
        raise HubError(400, "unknown_contract", f"모르는 계약 판: {contract!r} — 이 허브는 hub/1", {"contract": contract})
    return {k: v for k, v in args.items() if k != "contract"}


def _lookup(store: Store, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    return store.lookup_project(a["remote_url"])


def _register_project(store: Store, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    return store.register_project(ctx, a["remote_url"], a["display_name"], a["callsign"], a["kind"],
                                  a.get("label", ""), a.get("host", ""))


def _register_callsign(store: Store, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    return store.register_callsign(ctx, a["project_id"], a["callsign"], a["kind"], a.get("label", ""), a.get("host", ""))


def _setup(ctx: Ctx, store: Store) -> Setup:
    return Setup(store, ctx.public_url)


def _setup_plan(store: Store, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    return _setup(ctx, store).plan(ctx, a["project_id"], a["token"], a["harnesses"], a.get("scan") or {})


def _setup_confirm(store: Store, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    return _setup(ctx, store).confirm(ctx, a["project_id"], a["token"], a.get("files") or [], a.get("checks") or [])


def _guide_render(store: Store, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    return _setup(ctx, store).guide_render(ctx, a["harness"], a.get("current"))


def _session_start(store: Store, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    return SessionStart(_setup(ctx, store)).run(ctx, a.get("repo_results"))


def _whoami(store: Store, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    p = ctx.principal
    assert p is not None
    return {"project_id": p.project_id, "callsign": p.callsign, "kind": p.callsign_kind,
            "human_approved": p.human_approved, "role": p.role}


_TASK_VALUES = ("title", "status", "priority", "branch", "wbs", "wbs_exempt_reason", "description", "plan_md", "fields")


def _task_create(store: Store, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    return store.task_create(ctx, {k: a[k] for k in _TASK_VALUES if k in a}, a.get("request_id"))


def _task_update(store: Store, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    return store.task_update(ctx, a["id"], a["expected_version"], a["values"], a.get("request_id"))


_TASK_PROPS: dict[str, dict[str, Any]] = {
    "title": _STR, "status": _STR, "priority": _STR, "branch": _STR, "wbs": _STR, "wbs_exempt_reason": _STR,
    "description": _STR, "plan_md": {"type": "string", "description": "1.x task 파일의 Plan 절 원문 (DS2)"},
    "fields": {"type": "object", "description": "affected_documents · done_criteria · result · risks · follow_up · validation_result · next_step"},
}

TOOLS: dict[str, ToolSpec] = {
    t.name: t for t in (
        ToolSpec("hub_project_lookup", "bootstrap", "git 원격 주소로 허브의 프로젝트를 찾는다 (없으면 project_id=null).",
                 {"remote_url": _STR}, ("remote_url",), _lookup),
        ToolSpec("hub_project_register", "bootstrap",
                 "프로젝트를 등록한다 — 등록자가 소유자 콜사인이 되고 토큰을 이 응답에서 한 번만 받는다.",
                 {"remote_url": _STR, "display_name": _STR, "callsign": _STR, "kind": _STR, "label": _STR, "host": _STR},
                 ("remote_url", "display_name", "callsign", "kind"), _register_project),
        ToolSpec("hub_callsign_register", "bootstrap",
                 "등록된 프로젝트에 콜사인으로 합류한다 — 토큰을 이 응답에서 한 번만 받는다. human 은 소유자 승인 전 agent 권한.",
                 {"project_id": _STR, "callsign": _STR, "kind": _STR, "label": _STR, "host": _STR},
                 ("project_id", "callsign", "kind"), _register_callsign),
        ToolSpec("hub_setup_plan", "bootstrap",
                 "셋업 쓰기 지시 — .gitignore 확인 전에는 토큰 파일 지시가 나오지 않는다. token 은 등록 응답의 것 (DS4). "
                 "harnesses: claude-code · codex · minimax-code · antigravity. scan.files: 경로 → 지금 내용(없으면 null) — "
                 ".gitignore · 진입 파일 · .mcp.json.",
                 {"project_id": _STR, "token": _STR, "harnesses": _ARR, "scan": _OBJ},
                 ("project_id", "token", "harnesses"), _setup_plan),
        ToolSpec("hub_setup_confirm", "bootstrap",
                 "쓴 파일의 sha256 · 명령 결과를 대조해 셋업 단계를 확인한다. files: [{path, sha256}], checks: [{name, rc, output}].",
                 {"project_id": _STR, "token": _STR, "files": _ARR, "checks": _ARR},
                 ("project_id", "token"), _setup_confirm),
        ToolSpec("hub_session_start", "token",
                 "세션 시작 확인 — 인자 없이 부르면 허브 쪽 결과와 저장소에서 돌릴 명령, repo_results 를 실어 다시 부르면 판정.",
                 {"repo_results": _OBJ}, (), _session_start),
        ToolSpec("hub_guide_render", "token",
                 "하네스 진입 파일의 새 내용 (렌더 영역 갱신). current = 지금 파일 내용 (없으면 생략). 로컬에서 고친 영역이면 blocked.",
                 {"harness": _STR, "current": _STR}, ("harness",), _guide_render),
        ToolSpec("hub_whoami", "token", "이 토큰의 프로젝트 · 콜사인 · 권한.", {}, (), _whoami),
        ToolSpec("hub_task_list", "token", "task 목록 (status · assignee 로 거른다, assignee='' 는 맡은 이 없음).",
                 {"status": _STR, "assignee": _STR, "limit": _INT}, (),
                 lambda s, c, a: s.task_list(c, a.get("status"), a.get("assignee"), a.get("limit", 100))),
        ToolSpec("hub_task_get", "token", "task 하나 (묶인 커밋 포함).", {"id": _STR}, ("id",),
                 lambda s, c, a: s.task_get(c, a["id"])),
        ToolSpec("hub_task_create", "token", "task 를 만든다 — ID 는 TASK-<날짜>-<콜사인>-<NNN> (DS3). done 으로 만들 수 없다.",
                 {**_TASK_PROPS, "request_id": _REQ_ID}, ("title",), _task_create),
        ToolSpec("hub_task_update", "token", "task 칸을 고친다 — expected_version 이 다르면 409. done 은 hub_task_close (M-035).",
                 {"id": _STR, "expected_version": _INT, "values": _OBJ, "request_id": _REQ_ID},
                 ("id", "expected_version", "values"), _task_update),
        ToolSpec("hub_task_claim", "token", "task 를 맡는다 — 다른 콜사인이 맡고 있으면 409.",
                 {"id": _STR, "request_id": _REQ_ID}, ("id",),
                 lambda s, c, a: s.task_claim(c, a["id"], a.get("request_id"))),
        ToolSpec("hub_task_release", "token", "맡은 task 를 놓는다 (맡은 이 · 소유자).",
                 {"id": _STR, "request_id": _REQ_ID}, ("id",),
                 lambda s, c, a: s.task_release(c, a["id"], a.get("request_id"))),
        ToolSpec("hub_task_progress", "token", "진행 한 줄을 남긴다 — 허브가 시각을 붙인다.",
                 {"id": _STR, "note": _STR, "request_id": _REQ_ID}, ("id", "note"),
                 lambda s, c, a: s.task_progress(c, a["id"], a["note"], a.get("request_id"))),
        ToolSpec("hub_task_link_commit", "token", "task 에 커밋 sha 를 묶는다 — 허브는 그 커밋을 읽지 않는다.",
                 {"id": _STR, "sha": _STR, "branch": _STR, "request_id": _REQ_ID}, ("id", "sha"),
                 lambda s, c, a: s.task_link_commit(c, a["id"], a["sha"], a.get("branch", ""), a.get("request_id"))),
        ToolSpec("hub_events", "token", "이력 (누가 · 언제 · 무엇 · 이전 값 · 새 값).",
                 {"target_kind": _STR, "target_id": _STR, "after_seq": _INT, "limit": _INT}, (),
                 lambda s, c, a: s.events(c, a.get("target_kind"), a.get("target_id"), a.get("after_seq", 0), a.get("limit", 200))),
    )
}


def visible_tools(authenticated: bool) -> list[ToolSpec]:
    """토큰 없는 연결에는 부트스트랩 묶음만 (요구 R2.3)."""
    return [t for t in TOOLS.values() if authenticated or t.bundle == "bootstrap"]


def call(store: Store, name: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
    """MCP · HTTP 가 부르는 단 하나의 입구."""
    spec = TOOLS.get(name)
    if spec is None:
        raise HubError(404, "unknown_tool", f"모르는 도구: {name}", {"tool": name})
    if spec.bundle != "bootstrap":
        if ctx.principal is None:
            raise unauthorized()
        if ctx.principal.kind != "callsign":
            raise HubError(403, "forbidden", "이 도구는 콜사인 토큰이 필요하다 (web · admin 토큰은 쓸 수 없다)")
    clean = validate_args(spec, args)
    # 모든 도구 인자 — 기록에 토큰이 실리지 않게 (hub_spec §1-4). 셋업 도구의 인자 ``token`` 은
    # 인증 수단이라 검사에서 뺀다 (DS4) — 기록에는 쓰지 않는다.
    scan_secrets({k: v for k, v in clean.items() if k != "token"})
    return spec.handler(store, ctx, clean)
