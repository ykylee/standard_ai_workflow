#!/usr/bin/env python3
"""MCP `plan_inbox` · `plan_import` (`core/plan_workbench_spec.md` §8.3, ADR-032).

1. `plan_inbox` — census 와 같은 건수 · 파일별 자격(단계 · 사유) · 알 수 없는 항목 · 배치 문제, 주석 본문은 없다,
   아무것도 쓰지 않는다 (받은편지함이 없으면 만들지도 않는다)
2. `plan_inbox` 의 `task_id` — 그 task 몫만
3. `plan_import` — 기본 dry-run 이 CLI `plan-import` 의 출력과 글자 그대로 같고 아무것도 쓰지 않는다; `apply: true` 는
   보관으로 옮기고 상태를 적는다; `discard` + `reason` 은 `.rejected.md`; 출력은 family `plan_import` 로 검증된다
4. 번들 · 입력 — `plan_inbox` 는 read-only 번들(`readOnlyHint: true`), `plan_import` 는 write 번들에만
   (`readOnlyHint: false` · `WRITE_CAPABLE_TOOL_NAMES`), `apply` 는 boolean 이고 문자열은 거절, `task_id` · `discard` 중 하나는 필수,
   read-only 번들로 뜬 JSON-RPC 서버는 `plan_import` 호출을 거절한다
5. 체크인 생성물(descriptor · JSON-RPC fixture · 하네스 MCP 예시)이 지금 코드의 생성 결과와 같다
"""

from __future__ import annotations

#: plan-import subprocess · 생성기를 돈다.
CHECK_TIMEOUT_S = 180

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/mcp_servers/*",
    "workflow-source/scripts/generate_read_only_*",
    "workflow-source/schemas/*",
    "workflow-source/tests/_workbench_fixture.py",
)

import json
import os
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402
from workflow_kit import __version__ as TOOL_VERSION  # noqa: E402
from workflow_kit.common import plan_claims as pc  # noqa: E402
from workflow_kit.common import plan_responses as pr  # noqa: E402
from workflow_kit.common import plan_tasks  # noqa: E402
from workflow_kit.common.output_contracts import validate_output_payload  # noqa: E402
from workflow_kit.server import read_only_registry as reg  # noqa: E402
from workflow_kit.server.read_only_entrypoint import invoke_tool  # noqa: E402
from workflow_kit.server.read_only_jsonrpc import handle_jsonrpc_request  # noqa: E402

FAILURES: list[str] = []
SECRET_COMMENT = "주석본문은싣지않는다"


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def _call(name: str, arguments: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    with mock.patch.dict(os.environ, {"CODEX_WORKFLOW_BRANCH": fx.BRANCH}):
        return invoke_tool(name, json.dumps(arguments, ensure_ascii=False))


def _task(ws: Path, task_id: str) -> plan_tasks.TaskPlan:
    task = plan_tasks.read_task_plan(fx.branch_dir(ws) / "backlog" / "tasks" / f"{task_id}.md")
    assert task is not None
    return task


def _seed(ws: Path) -> tuple[str, str]:
    """task 둘 — A 에 자격 있는 응답 하나 · 지문이 옛 응답 하나, B 에 응답 하나, 알 수 없는 .md 하나."""
    a = fx.create_task(ws, name="응답 둘")
    b = fx.create_task(ws, name="응답 하나")
    branch = fx.branch_dir(ws)
    for task_id, responder, stale in ((a, "alice", False), (a, "bob", True), (b, "carol", False)):
        task = _task(ws, task_id)
        body = pr.render_response(task_id=task_id, plan=task.plan, responder=responder,
                                  received_at=f"2026-11-14T09:00:0{len(responder)}.000000+09:00",
                                  values={"D1": "warn"}, opened={"D1": True}, comments=[("C1", SECRET_COMMENT)])
        if stale:
            body = body.replace(pc.plan_digest(task.plan), "f" * 64)
        pr.publish(branch, task_id, body.encode())
    (pr.inbox_dir(branch) / "stray.md").write_text("x", encoding="utf-8")
    # 이 브랜치에 task 파일이 없는 응답 — 자격을 볼 수 없다 (stage 0).
    orphan = "TASK-2026-01-01-workbench-777"
    pr.publish(branch, orphan, pr.render_response(task_id=orphan, plan=_task(ws, a).plan, responder="dave",
                                                    received_at="2026-11-14T09:00:09.000000+09:00").encode())
    return a, b


def case_inbox() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("plan-mcp-1-") as td:
        ws = fx.make_workspace(td)
        # 받은편지함이 없으면 만들지 않는다 — 읽는 길이다.
        rc, empty = _call("plan_inbox", {"workspace_root": str(ws)})
        if rc != 0 or empty.get("pending") != {} or pr.inbox_dir(fx.branch_dir(ws)).exists():
            problems.append(f"빈 작업 공간: rc {rc} {empty.get('pending')} · 받은편지함 생김 {pr.inbox_dir(fx.branch_dir(ws)).exists()}")
        a, b = _seed(ws)
        before = fx.tree_snapshot(ws)
        rc, out = _call("plan_inbox", {"workspace_root": str(ws)})
        if fx.tree_snapshot(ws) != before:
            problems.append("plan_inbox 가 작업 공간에 썼다")
        if rc != 0:
            return problems + [f"plan_inbox rc {rc}: {out}"]
        if validate_output_payload(out, family="plan_inbox"):
            problems.append(f"family plan_inbox 로 검증되지 않는다: {validate_output_payload(out, family='plan_inbox')}")
        census = pr.inbox_census(fx.branch_dir(ws))
        orphan = "TASK-2026-01-01-workbench-777"
        if out["pending"] != census.pending or out["pending"] != {a: 2, b: 1, orphan: 1}:
            problems.append(f"pending 이 census 와 다르다: {out['pending']} · census {census.pending}")
        if out["unknown"] != ["stray.md"]:
            problems.append(f"알 수 없는 항목: {out['unknown']}")
        names = [f["name"] for f in out["files"]]
        if names != [p.name for t in sorted(census.files) for p in census.paths(t)]:
            problems.append(f"파일 목록이 census 의 번호 순과 다르다: {names}")
        by_responder = {f["responder"]: f for f in out["files"]}
        if sorted(by_responder) != ["alice", "bob", "carol", "dave"]:
            problems.append(f"응답자가 파일마다 실리지 않았다: {sorted(by_responder)}")
        # 파일별 값은 파일 자체를 읽은 값과 같아야 한다 — 응답자 · 시각 · 단계 · 사유 · task.
        for f in out["files"]:
            path = pr.inbox_dir(fx.branch_dir(ws)) / f["name"]
            parsed = pr.read_response(path)
            if (f["responder"], f["received_at"], f["task"]) != (parsed.responder, parsed.received_at,
                                                                    pr.task_of_response_name(f["name"])):
                problems.append(f"{f['name']}: 응답자 · 시각 · task 가 파일과 다르다: {f}")
        want = {"alice": (None, ""), "carol": (None, "")}
        for who, (stage, reason) in want.items():
            if (by_responder.get(who, {}).get("stage"), by_responder.get(who, {}).get("reason")) != (stage, reason):
                problems.append(f"{who}: 자격 있는 응답의 단계 · 사유가 (null, '') 가 아니다: {by_responder.get(who)}")
        bob = by_responder.get("bob", {})
        if bob.get("stage") != 4 or "plan_digest" not in (bob.get("reason") or ""):
            problems.append(f"bob: 지문이 옛 응답이 4 단계 · 지문 사유가 아니다: {bob}")
        dave = by_responder.get("dave", {})
        if dave.get("stage") != 0 or "task 파일" not in (dave.get("reason") or ""):
            problems.append(f"dave: task 파일이 없는 응답이 0 단계 · 사유가 아니다: {dave}")
        if SECRET_COMMENT in json.dumps(out, ensure_ascii=False):
            problems.append("주석 본문이 출력에 실렸다")
        if out["source_context"].get("branch") != fx.BRANCH or str(ws) in json.dumps(out, ensure_ascii=False):
            problems.append(f"source_context 가 브랜치가 아니거나 절대 경로가 실렸다: {out['source_context']}")
        if not any("미반영" in w for w in out["warnings"]):
            problems.append(f"미반영 경고가 없다: {out['warnings']}")
    return problems


def case_inbox_task_filter() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("plan-mcp-2-") as td:
        ws = fx.make_workspace(td)
        a, b = _seed(ws)
        rc, out = _call("plan_inbox", {"workspace_root": str(ws), "task_id": b})
        if rc != 0 or out["pending"] != {b: 1} or {f["task"] for f in out["files"]} != {b}:
            problems.append(f"task_id 필터: rc {rc} pending {out.get('pending')} files {[f['task'] for f in out.get('files', [])]}")
        # 배치 문제 — 받은편지함을 보관과 같은 디렉터리로.
        branch = fx.branch_dir(ws)
        inbox = pr.inbox_dir(branch)
        inbox.rename(inbox.with_name("inbox_real"))
        inbox.symlink_to(pr.responses_dir(branch), target_is_directory=True)
        rc, out = _call("plan_inbox", {"workspace_root": str(ws)})
        if rc != 0 or not out.get("layout_problem") or "배치" not in " ".join(out.get("warnings", [])):
            problems.append(f"배치 문제가 보고되지 않았다: {out.get('layout_problem')} {out.get('warnings')}")
    return problems


def _cli_import(ws: Path, *args: str) -> dict[str, Any]:
    proc = fx.cli(ws, ["-m", "workflow_kit", "plan-import", "--project-profile-path", str(fx.profile(ws)), *args])
    return json.loads(proc.stdout)


def case_import() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("plan-mcp-3-") as td:
        ws = fx.make_workspace(td)
        a, b = _seed(ws)
        before = fx.tree_snapshot(ws, skip=("ai-workflow/memory/active/workbench/plan_responses/inbox/.lock",))
        rc, dry = _call("plan_import", {"workspace_root": str(ws), "task_id": a})
        cli = _cli_import(ws, "--task", a)
        if rc != 0 or dry != cli:
            problems.append(f"dry-run 이 CLI 출력과 다르다: rc {rc} · MCP {str(dry)[:200]} · CLI {str(cli)[:200]}")
        if dry.get("applied") is not False or dry.get("outcome") != "dry_run":
            problems.append(f"기본이 dry-run 이 아니다: {dry.get('applied')} {dry.get('outcome')}")
        after = fx.tree_snapshot(ws, skip=("ai-workflow/memory/active/workbench/plan_responses/inbox/.lock",))
        if after != before:
            problems.append("dry-run 이 작업 공간에 썼다")
        # response 하나만 — b 에 응답을 하나 더 두고 그중 하나만 옮긴다.
        task_b = _task(ws, b)
        extra = pr.publish(fx.branch_dir(ws), b, pr.render_response(
            task_id=b, plan=task_b.plan, responder="erin", received_at="2026-11-14T09:00:20.000000+09:00").encode())
        rc, one = _call("plan_import", {"workspace_root": str(ws), "task_id": b, "response": extra.name, "apply": True})
        left = [p.name for p in pr.inbox_census(fx.branch_dir(ws)).paths(b)]
        if rc != 0 or one.get("outcome") != "imported" or len(left) != 1 or extra.name in left:
            problems.append(f"response 지정 apply 가 그 파일만 옮기지 않았다: {one.get('outcome')} 남은 것 {left}")
        rc, out = _call("plan_import", {"workspace_root": str(ws), "discard": left[0] if left else "x", "apply": True})
        if out.get("error_code") != "missing_discard_reason" or len(pr.inbox_census(fx.branch_dir(ws)).paths(b)) != 1:
            problems.append(f"reason 없는 discard 를 입력 단계에서 거절하지 않았다: {out.get('error_code')}")
        rc, applied = _call("plan_import", {"workspace_root": str(ws), "task_id": a, "apply": True})
        if rc != 0 or applied.get("applied") is not True or applied.get("outcome") != "imported":
            problems.append(f"apply: rc {rc} {applied.get('applied')} {applied.get('outcome')} {applied.get('error')}")
        if validate_output_payload(applied, family="plan_import"):
            problems.append("apply 출력이 family plan_import 로 검증되지 않는다")
        states = plan_tasks.computed_states(_task(ws, a)).states
        if states.get("D1") != f"{pc.STATE_CHANGED}:warn":
            problems.append(f"apply 뒤 결정 상태가 응답을 반영하지 않았다: {states}")
        remaining = pr.inbox_census(fx.branch_dir(ws)).count(a)
        if remaining != 1:  # 지문이 옛 응답은 받은편지함에 남는다
            problems.append(f"apply 뒤 받은편지함에 남은 건수: {remaining} (기대 1)")
        stale = pr.inbox_census(fx.branch_dir(ws)).paths(a)[0].name
        rc, out = _call("plan_import", {"workspace_root": str(ws), "discard": stale, "reason": "옛 계획", "apply": True})
        rejected = [p.name for p in pr.responses_dir(fx.branch_dir(ws)).iterdir() if p.name.endswith(".rejected.md")]
        if rc != 0 or out.get("outcome") != "discarded" or len(rejected) != 1:
            problems.append(f"discard: rc {rc} {out.get('outcome')} {out.get('error')} rejected={rejected}")
        rc, out = _call("plan_import", {"workspace_root": str(ws), "task_id": "TASK-2026-01-01-workbench-999"})
        # 도구가 돌려준 오류 결과는 전송 오류가 아니다 — 다른 도구처럼 status error · error_code 로 보고한다.
        if out.get("status") != "error" or out.get("error_code") != "task_not_found":
            problems.append(f"없는 task 가 오류로 보고되지 않았다: rc {rc} {out.get('status')} {out.get('error_code')}")
    return problems


def case_bundles_and_inputs() -> list[str]:
    problems: list[str] = []
    ro = {d["name"]: d for d in reg.build_transport_tool_descriptors(reg.BUNDLE_READ_ONLY)["tools"]}
    wr = {d["name"]: d for d in reg.build_transport_tool_descriptors(reg.BUNDLE_WRITE)["tools"]}
    if "plan_inbox" not in ro or ro["plan_inbox"]["annotations"]["readOnlyHint"] is not True:
        problems.append("plan_inbox 가 read-only 번들에 readOnlyHint true 로 없다")
    if "plan_import" in ro:
        problems.append("plan_import 가 read-only 번들에 있다 — 쓰는 도구다")
    if "plan_import" not in wr or wr["plan_import"]["annotations"]["readOnlyHint"] is not False:
        problems.append("plan_import 가 write 번들에 readOnlyHint false 로 없다")
    if "plan_import" not in reg.WRITE_CAPABLE_TOOL_NAMES:
        problems.append("WRITE_CAPABLE_TOOL_NAMES 에 plan_import 가 없다")
    schema = wr.get("plan_import", {}).get("inputSchema", {})
    if schema.get("properties", {}).get("apply", {}).get("type") != "boolean":
        problems.append(f"apply 가 boolean 이 아니다: {schema.get('properties', {}).get('apply')}")
    if schema.get("anyOf") != [{"required": ["task_id"]}, {"required": ["discard"]}]:
        problems.append(f"task_id · discard 중 하나가 필수가 아니다: {schema.get('anyOf')}")
    for args, label in (({"task_id": "x", "apply": "true"}, "문자열 apply"), ({"task_id": "x", "apply": 1}, "숫자 apply"), ({"apply": True}, "task_id · discard 없음"),
                        ({"task_id": "x", "nope": 1}, "모르는 필드")):
        rc, out = invoke_tool("plan_import", json.dumps(args))
        if rc == 0 or out.get("error_code") != "invalid_tool_payload_schema":
            problems.append(f"{label} 를 거절하지 않았다: rc {rc} {out.get('error_code')}")
    reply = handle_jsonrpc_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "plan_import", "arguments": {"task_id": "x"}}},
        bundle=reg.BUNDLE_READ_ONLY)
    if not reply or "error" not in reply or "bundle" not in json.dumps(reply.get("error", {})):
        problems.append(f"read-only 번들 서버가 plan_import 호출을 거절하지 않았다: {str(reply)[:200]}")
    for name in ("plan_inbox", "plan_import"):
        spec = reg.get_tool_spec(name)
        if spec is None or not spec.script_path.is_file() or not (spec.script_path.parents[1] / "MCP.md").is_file():
            problems.append(f"{name} 의 runner 스크립트 · MCP.md 가 없다")
    return problems


def case_generated_artifacts() -> list[str]:
    problems: list[str] = []
    root = fx.SOURCE_ROOT
    env = dict(os.environ, PYTHONPATH=str(root), PYTHONIOENCODING="utf-8")
    for script, artifact in (("generate_read_only_transport_descriptors", "read_only_transport_descriptors"),
                             ("generate_read_only_jsonrpc_fixtures", "read_only_jsonrpc_fixtures"),
                             ("generate_read_only_harness_mcp_examples", "read_only_harness_mcp_examples"),
                             ("generate_output_json_schema", "generated_output_schemas"),
                             ("generate_output_sample_contracts", "output_sample_contracts")):
        proc = subprocess.run([sys.executable, "-W", "ignore", str(root / "scripts" / f"{script}.py")], capture_output=True,
                              encoding="utf-8", check=False, env=env, cwd=str(root), timeout=120)
        checked = (root / "schemas" / f"{artifact}.json").read_text(encoding="utf-8")
        if proc.returncode != 0 or json.loads(proc.stdout) != json.loads(checked):
            problems.append(f"schemas/{artifact}.json 이 지금 코드의 생성 결과와 다르다 (rc {proc.returncode})")
        elif artifact != "output_sample_contracts" and "plan_inbox" not in checked:
            problems.append(f"schemas/{artifact}.json 에 plan_inbox 가 없다")
    return problems


CASES = (
    ("1 plan_inbox — census 건수 · 파일별 자격 · 주석 본문 없음 · 읽기 전용", case_inbox),
    ("2 plan_inbox — task_id 필터 · 배치 문제", case_inbox_task_filter),
    ("3 plan_import — dry-run = CLI · apply · discard · 오류", case_import),
    ("4 번들 · 입력 — readOnlyHint · write 목록 · boolean apply · 필수 · 번들 밖 호출 거절", case_bundles_and_inputs),
    ("5 체크인 생성물이 지금 코드의 생성 결과와 같다", case_generated_artifacts),
)


def main() -> int:
    print(f"check_plan_mcp_tools — MCP plan_inbox · plan_import (plan_workbench_spec §8.3, kit {TOOL_VERSION})")
    for name, case in CASES:
        try:
            _record(name, case())
        except Exception:  # noqa: BLE001 — case 하나의 예외는 그 case 의 FAIL 이다
            _record(name, ["예외: " + traceback.format_exc().strip().splitlines()[-1]])
            traceback.print_exc()
    print(f"\n{len(CASES) - len(FAILURES)}/{len(CASES)} PASS")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
