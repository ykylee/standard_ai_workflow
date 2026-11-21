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
from workflow_kit.hub.guide import Guides
from workflow_kit.hub.judge import Judge
from workflow_kit.hub.memory import Memory
from workflow_kit.hub.migrate1x import Migrator
from workflow_kit.hub.session import SessionStart
from workflow_kit.hub.setup import Setup
from workflow_kit.hub.store import Ctx, Store, scan_secrets
from workflow_kit.hub.wiki import Wiki

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


_PY_TYPES: dict[str, tuple[type, ...]] = {"string": (str,), "integer": (int,), "object": (dict,), "array": (list,),
                                         "boolean": (bool,)}


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
    return SessionStart(_setup(ctx, store)).run(ctx, a.get("repo_results"), a.get("client"))


def _whoami(store: Store, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    p = ctx.principal
    assert p is not None
    return {"project_id": p.project_id, "callsign": p.callsign, "kind": p.callsign_kind,
            "human_approved": p.human_approved, "role": p.role}


_TASK_VALUES = ("title", "status", "priority", "branch", "wbs", "wbs_exempt_reason", "description", "plan_md", "fields")


def _task_create(store: Store, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    return store.task_create(ctx, {k: a[k] for k in _TASK_VALUES if k in a}, a.get("request_id"),
                             prepare=Judge(store).prepare_create)


def _task_update(store: Store, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    judge = Judge(store)
    states = a.get("decision_states") or {}
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in states.items()):
        raise invalid_field("decision_states", "{D<n>: answered:<value> | proposed}")
    p = ctx.principal
    pid = p.project_id if p and p.project_id else ""
    values = a.get("values") or {}

    def prepare(conn: Any, before: dict[str, Any], vals: dict[str, Any]) -> dict[str, Any]:
        return judge.prepare_update(conn, pid, before, vals, states, a.get("note"))

    return store.task_update(ctx, a["id"], a["expected_version"], values, a.get("request_id"), prepare=prepare)


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
                 {"repo_results": _OBJ, "client": _OBJ}, (), _session_start),
        ToolSpec("hub_guide_render", "token",
                 "하네스 진입 파일의 새 내용 (렌더 영역 갱신). current = 지금 파일 내용 (없으면 생략). 로컬에서 고친 영역이면 blocked.",
                 {"harness": _STR, "current": _STR}, ("harness",), _guide_render),
        ToolSpec("hub_callsign_approve", "token",
                 "사람(human) 콜사인을 승인한다 — 승인된 human 소유자만. 승인 전 human 은 agent 권한이라 결정에 답할 수 없다.",
                 {"callsign": _STR}, ("callsign",), lambda s, c, a: s.approve_callsign(c, a["callsign"])),
        ToolSpec("hub_guide_get", "token", "프로젝트 지침 — 지금 판 · 판 이력 · 제안(열린 제안은 diff).", {}, (),
                 lambda s, c, a: Guides(s).get(c)),
        ToolSpec("hub_guide_propose", "token",
                 "프로젝트 지침 변경 — base_version 은 지금 판(다르면 409). 승인된 human 이면 바로 판 +1, "
                 "agent · 승인 전 human 은 제안으로 남는다 (D11). 렌더 예산(8KB)을 넘으면 422.",
                 {"base_version": _INT, "body": _STR, "note": _STR}, ("base_version", "body"),
                 lambda s, c, a: Guides(s).propose(c, a["base_version"], a["body"], a.get("note", ""))),
        ToolSpec("hub_guide_decide", "token", "열린 지침 제안을 승인(approve=true) · 거절한다 — 승인된 human 만.",
                 {"proposal_id": _STR, "approve": {"type": "boolean"}}, ("proposal_id", "approve"),
                 lambda s, c, a: Guides(s).decide(c, a["proposal_id"], bool(a["approve"]))),
        ToolSpec("hub_migrate_plan", "token",
                 "1.x 전환 계획 (소유자만) — 인자 없이 부르면 저장소에서 돌릴 명령, scan={name:{rc,output}} 을 실어 다시 부르면 "
                 "감지 보고 · 전환 표 · 같은 ID 정본 · 하네스 안내와 migration_id. 원본은 건드리지 않는다.",
                 {"scan": _OBJ}, (), lambda s, c, a: Migrator(s).plan(c, a.get("scan"))),
        ToolSpec("hub_migrate_import", "token",
                 "1.x 들여오기 묶음 (소유자만) — kinds: tasks · archive · handoff · roadmap · wiki · memory_index · checkpoint · "
                 "guide_draft 가운데 소유자가 고른 것. files=[{path, content}] 는 계획에 있는 경로만. 요청 상한(256KB) 안으로 나눠 "
                 "보내고 마지막에 final=true. 다시 보내도 있는 것은 건너뛴다.",
                 {"migration_id": _STR, "kinds": _ARR, "files": _ARR, "final": {"type": "boolean"}},
                 ("migration_id", "kinds"),
                 lambda s, c, a: Migrator(s).import_batch(c, a["migration_id"], a["kinds"], a.get("files") or [],
                                                          bool(a.get("final")))),
        ToolSpec("hub_migrate_report", "token", "1.x 전환 기록 — 계획 · 종류별 들인 것 · 건너뛴 것 · 실패.",
                 {"migration_id": _STR}, ("migration_id",), lambda s, c, a: Migrator(s).report(c, a["migration_id"])),
        ToolSpec("hub_whoami", "token", "이 토큰의 프로젝트 · 콜사인 · 권한.", {}, (), _whoami),
        ToolSpec("hub_task_list", "token", "task 목록 (status · assignee 로 거른다, assignee='' 는 맡은 이 없음).",
                 {"status": _STR, "assignee": _STR, "limit": _INT}, (),
                 lambda s, c, a: s.task_list(c, a.get("status"), a.get("assignee"), a.get("limit", 100))),
        ToolSpec("hub_task_get", "token", "task 하나 (묶인 커밋 포함).", {"id": _STR}, ("id",),
                 lambda s, c, a: s.task_get(c, a["id"])),
        ToolSpec("hub_task_create", "token", "task 를 만든다 — ID 는 TASK-<날짜>-<콜사인>-<NNN> (DS3). done 으로 만들 수 없다.",
                 {**_TASK_PROPS, "request_id": _REQ_ID}, ("title",), _task_create),
        ToolSpec("hub_task_update", "token",
                 "task 칸을 고친다 — expected_version 이 다르면 409. 계획(plan_md)은 1.x 계약으로 린트 · 결정 상태 재계산. "
                 "decision_states: {D<n>: answered:<value>|proposed}. 열린 결정을 걷으면 note 필수. done 은 hub_task_close.",
                 {"id": _STR, "expected_version": _INT, "values": _OBJ, "decision_states": _OBJ, "note": _STR,
                  "request_id": _REQ_ID},
                 ("id", "expected_version"), _task_update),
        ToolSpec("hub_task_close", "token",
                 "task 를 done 으로 닫는다 — done 게이트(검증 결과 필수 · 열린 결정 · 계획 오류 규칙)를 1.x 와 같은 함수로 판정.",
                 {"id": _STR, "expected_version": _INT, "validation_result": _STR, "request_id": _REQ_ID},
                 ("id", "expected_version", "validation_result"),
                 lambda s, c, a: Judge(s).task_close(c, a["id"], a["expected_version"], a["validation_result"], a.get("request_id"))),
        ToolSpec("hub_plan_respond", "token",
                 "결정 응답(workflow-kit-plan-response/1 본문 그대로)을 받는다 — 자격 판정 뒤에만 결정 상태에 반영한다.",
                 {"task_id": _STR, "body": _STR}, ("task_id", "body"),
                 lambda s, c, a: Judge(s).plan_respond(c, a["task_id"], a["body"])),
        ToolSpec("hub_plan_status", "token", "task 계획의 결정 상태 · 열린 결정 · 반영된 응답 수.",
                 {"task_id": _STR}, ("task_id",), lambda s, c, a: Judge(s).plan_status(c, a["task_id"])),
        ToolSpec("hub_handoff_get", "token", "콜사인의 handoff (기본: 나). 다른 콜사인 것도 읽을 수 있다 (G3).",
                 {"callsign": _STR}, (), lambda s, c, a: Memory(s).handoff_get(c, a.get("callsign"))),
        ToolSpec("hub_handoff_put", "token",
                 "내 handoff 를 쓴다 — 칸: baseline · focus · in_progress · blocked · recent_done(10건 넘치면 옮긴다) · next · risks.",
                 {"handoff": _OBJ, "expected_version": _INT}, ("handoff",),
                 lambda s, c, a: Memory(s).handoff_put(c, a.get("expected_version"), a["handoff"])),
        ToolSpec("hub_session_end", "token",
                 "세션 끝 — handoff 와 진행 한 줄들을 한 트랜잭션으로 쓴다. 다음은 커밋 → push.",
                 {"handoff": _OBJ, "expected_version": _INT, "progress": _ARR}, ("handoff",),
                 lambda s, c, a: Memory(s).session_end(c, a["handoff"], a.get("expected_version"), a.get("progress") or [])),
        ToolSpec("hub_checkpoint_put", "token", "compact 직전 체크포인트 — next · unverified · verified · rejected · tasks · branch.",
                 {"body": _OBJ}, ("body",), lambda s, c, a: Memory(s).checkpoint_put(c, a["body"])),
        ToolSpec("hub_compact_resume", "token",
                 "compact 직후 — 체크포인트 · 내 task · 그 사이 다른 콜사인의 변경 · 요약에서 빠진 식별자 (summary_ids 없으면 대조 불가).",
                 {"summary_ids": _ARR}, (), lambda s, c, a: Memory(s).compact_resume(c, a.get("summary_ids"))),
        ToolSpec("hub_state", "token", "상태 요약 (state.json v1 — 1.x 생성기로 만든다). callsign 기본: 나.",
                 {"callsign": _STR}, (), lambda s, c, a: Memory(s).state(c, a.get("callsign"))),
        ToolSpec("hub_roadmap_get", "token", "로드맵 원문 (index.md · M-NNN-*.md).", {}, (),
                 lambda s, c, a: Judge(s).roadmap_get(c)),
        ToolSpec("hub_roadmap_put", "token",
                 "로드맵 문서 하나를 쓴다 — 스키마 오류는 필드 · 제약과 함께 거절, expected_version 이 다르면 409 (새 문서는 0).",
                 {"path": _STR, "expected_version": _INT, "body": _STR}, ("path", "body"),
                 lambda s, c, a: Judge(s).roadmap_put(c, a["path"], a.get("expected_version"), a["body"])),
        ToolSpec("hub_roadmap_state", "token", "로드맵 진척 (roadmap_state v1 형식) — 산출물 존재는 미측정.", {}, (),
                 lambda s, c, a: Judge(s).roadmap_state(c)),
        ToolSpec("hub_wiki_ingest", "token",
                 "위키 ingest — 페이지 묶음 [{path, body | delete:true, expected_version(새 페이지 0), source?:{repo_key, sha}}] 을 한 번에 쓴다. "
                 "한 페이지라도 version 이 다르면 묶음 전체 409 (부분 반영 0). log 항목은 허브가 만든다. index.md · log.md 는 생성물이라 쓸 수 없다.",
                 {"pages": _ARR, "summary": _STR, "request_id": _REQ_ID}, ("pages", "summary"),
                 lambda s, c, a: Wiki(s).ingest(c, a["pages"], a["summary"], a.get("request_id"))),
        ToolSpec("hub_wiki_get", "token", "위키 페이지 하나 (index.md · log.md 는 생성해서 돌려준다).",
                 {"path": _STR}, ("path",), lambda s, c, a: Wiki(s).get(c, a["path"])),
        ToolSpec("hub_wiki_list", "token", "위키 페이지 목록 (경로 · 제목 · version). prefix 로 좁힌다.",
                 {"prefix": _STR}, (), lambda s, c, a: Wiki(s).list_pages(c, a.get("prefix", ""))),
        ToolSpec("hub_wiki_search", "token", "위키 검색 — 낱말이 모두 들어간 페이지 (경로 · 제목 · 본문).",
                 {"query": _STR, "limit": _INT}, ("query",), lambda s, c, a: Wiki(s).search(c, a["query"], a.get("limit", 20))),
        ToolSpec("hub_wiki_lint", "token",
                 "위키 lint — 1.x 와 같은 함수로 정위치(V-1) · index 구조(V-4) · 양방향 링크(bidir), 깨진 위키 링크. 저장소 참조 · 출처 sha · freshness 는 원격 읽기를 켰을 때만 측정, 아니면 미측정.",
                 {}, (), lambda s, c, a: Wiki(s).lint(c)),
        ToolSpec("hub_wiki_remote_set", "token",
                 "위키 원격 읽기를 켜고 끈다 (소유자만) — fetch_url 을 주면 lint 가 그 저장소를 읽기 전용으로 받아 "
                 "저장소 참조 · 출처 sha · freshness 를 잰다. 빈 값이면 끈다 (그 셋은 미측정).",
                 {"fetch_url": _STR}, ("fetch_url",), lambda s, c, a: Wiki(s).remote_set(c, a["fetch_url"])),
        ToolSpec("hub_memory_entry_put", "token",
                 "memory_index entry 하나를 쓴다 — 1.x 스키마(MemoryEntry)로 검증, expected_version 이 다르면 409 (새 entry 는 0).",
                 {"entry": _OBJ, "expected_version": _INT}, ("entry",),
                 lambda s, c, a: Wiki(s).memory_put(c, a["entry"], a.get("expected_version"))),
        ToolSpec("hub_memory_entry_get", "token", "memory_index entry 하나.", {"id": _STR}, ("id",),
                 lambda s, c, a: Wiki(s).memory_get(c, a["id"])),
        ToolSpec("hub_memory_entry_list", "token", "memory_index entry 목록 (id · version · primary_abstraction).", {}, (),
                 lambda s, c, a: Wiki(s).memory_list(c)),
        ToolSpec("hub_wiki_import_dir", "token",
                 "1.x 위키 디렉터리를 무손실로 들인다 — files [{path(위키 뿌리 상대), content}]. 페이지는 바이트 그대로, "
                 "index.md · log.md 원문은 보관 기록으로, .md 아닌 파일은 건너뛴다. overwrite 가 아니면 있는 페이지는 409. "
                 "요청 상한(256KB)을 넘으면 여러 번 나눠 부른다.",
                 {"files": _ARR, "summary": _STR, "overwrite": {"type": "boolean"}, "request_id": _REQ_ID}, ("files", "summary"),
                 lambda s, c, a: Wiki(s).import_dir(c, a["files"], a["summary"], bool(a.get("overwrite")), a.get("request_id"))),
        ToolSpec("hub_wiki_export", "token",
                 "위키 내보내기를 쓰기 지시로 돌려준다 (허브는 저장소에 쓰지 않는다). format=dir: 1.x 위키 배치 그대로(무손실) + "
                 "내보내기 표식. format=okf: OKF 출판(손실 — 빠진 페이지를 목록으로). 크면 next_cursor 로 이어 부른다.",
                 {"format": _STR, "out_dir": _STR, "cursor": _INT}, ("format",),
                 lambda s, c, a: Wiki(s).export(c, a["format"], a.get("out_dir"), a.get("cursor", 0))),
        ToolSpec("hub_wiki_import_okf", "token",
                 "남의 OKF 묶음을 들인다 — files [{path(묶음 뿌리 상대), content}], loose 한 방향 (OKF 형태 그대로 페이지가 된다).",
                 {"files": _ARR, "summary": _STR, "request_id": _REQ_ID}, ("files", "summary"),
                 lambda s, c, a: Wiki(s).import_okf(c, a["files"], a["summary"], a.get("request_id"))),
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
