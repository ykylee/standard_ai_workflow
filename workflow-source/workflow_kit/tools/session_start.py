#!/usr/bin/env python3
"""Prototype runner for the session-start skill."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common.child_process import child_env, module_command
from workflow_kit.common.errors import build_error_result
from workflow_kit.common.contracts.stage_gate_runtime import build_stage_completion, merge_into_result
from workflow_kit.common.normalize import (
    dedupe_normalized_backticked,
    normalize_constraint_values,
)
from workflow_kit.common.paths import (
    discover_project_profile_path,
    memory_active_dir,
    resolve_existing_path,
    workflow_backlog_dir,
    workflow_handoff_path,
    workflow_state_path,
)
from workflow_kit.common.state.builder import collect_task_corpus_status, find_latest_daily_backlog
from workflow_kit.common.project_docs import (
    find_latest_backlog_path,
    parse_backlog,
    parse_handoff,
    parse_project_profile_session,
)
from workflow_kit.common.purpose_context import build_purpose_context
from workflow_kit.common.reconcile import compare_state_lists
from workflow_kit.common.session_outputs import build_session_summary, make_session_recommended_action


def _build_memory_index_query_output(
    args: argparse.Namespace,
    workspace_root: Path,
    warnings: list[str],
) -> dict[str, Any] | None:
    """v0.11.22+ Phase 3b: optional ADR-005 memory_index retrieval 3-tuple 호출.

    - flag 부재 + workspace memory_index dir 부재 → None (zero-risk skip, 기존 caller 정합).
    - flag 부재 + workspace memory_index dir 존재 → 자동 활성 (v0.15.21+ AC2), default query token 사용.
    - flag 명시 → override (외부 dir 지정 시 negative telemetry emit).
    - v0.13.1+ Phase 13 AC2: retrieval 성공/실패 후 telemetry sidecar 에 1 event append.
    """
    # v0.15.21+ AC2 (telemetry source 다양성 ≥ 4): opt-in flag 부재 시에도
    # workspace 표준 memory_index dir 이 존재하면 retrieval 자동 활성 (flag 는 override 유지).
    # dir 부재 시 zero-risk skip — memory_index 없는 기존 caller 정합.
    effective_dir = args.memory_index_dir
    if not effective_dir:
        _default_dir = memory_active_dir(workspace_root) / "memory_index"
        if _default_dir.is_dir():
            effective_dir = str(_default_dir)
    if not effective_dir:
        return None  # zero-risk default (memory_index 부재)
    from datetime import datetime as _dt, timezone as _tz
    from workflow_kit.common.state.memory_index import (
        MemoryIndexTelemetryEvent,
        QUERY_SOURCE_EXPLICIT,
        append_telemetry_event,
        derive_context_query_tokens,
        query_memory_index_for_dispatcher,
    )

    # W-2 (ADR-006): 고정 trio 는 공통 token 이 항상 같은 entry 를 집었다 —
    # flag 미지정 시 현재 컨텍스트(state.json 축 + 최근 done 제목)에서 유도.
    # 유도 실패는 기존 default 로 떨어지되 출처를 telemetry 에 남긴다.
    if args.memory_query_tokens:
        query_tokens = [t.strip() for t in args.memory_query_tokens.split(",") if t.strip()]
        query_source = QUERY_SOURCE_EXPLICIT
    else:
        try:
            _state_path = workflow_state_path(Path(args.project_profile_path))
        except (OSError, ValueError):
            _state_path = None
        query_tokens, query_source = derive_context_query_tokens(
            _state_path, base_tokens=["session", "handoff", "workflow"],
        )

    memory_index_dir = Path(effective_dir)
    if not query_tokens:
        warnings.append(
            "memory_index wiring: --memory-query-tokens 가 비어있음. retrieval skip."
        )
        return None
    target = workspace_root
    try:
        memory_index_dir.relative_to(workspace_root)
        # subdir — workspace_root 그대로 사용 (helper 내부 `memory_index_root(<root>)` 자동 계산)
    except ValueError:
        warnings.append(
            "memory_index wiring: --memory-index-dir 가 workspace_root 외부. "
            "현재 정공법은 ws 의 subdir 만 지원 (Phase 3c/d 개선 후보)."
        )
        # Phase 13 AC2: 외부 dir 도 telemetry 는 emit (negative example).
        append_telemetry_event(
            workspace_root,
            MemoryIndexTelemetryEvent(
                timestamp=_dt.now(_tz.utc),
                source="session-start",
                workspace_root=str(workspace_root),
                query_tokens_count=len(query_tokens),
                query_tokens=query_tokens[:16],
                query_source=query_source,
                error=True,
            ),
        )
        return None
    try:
        # **BM25 를 켠다** (TASK-2026-09-23-main-005). 이 caller 의 질의는 W-2 이후
        # state.json 에서 유도한 **한국어 산문 token** 인데 `cue_anchors` 는 영문
        # kebab 관례다 — 1단계(cue exact)는 구조적으로 못 맞춘다. 실측: 세 caller 가
        # 전부 selected_count=0 을 받고 있었고 아무도 몰랐다. BM25 를 켜면 같은
        # 질의가 4건을 집는다. 끄면 이 배선은 장식이다.
        result = query_memory_index_for_dispatcher(
            target, query_tokens, use_bm25_fallback=True)
        # Phase 13 AC2: telemetry emit (success path).
        append_telemetry_event(
            workspace_root,
            MemoryIndexTelemetryEvent(
                timestamp=_dt.now(_tz.utc),
                source="session-start",
                workspace_root=str(workspace_root),
                query_tokens_count=len(query_tokens),
                query_tokens=query_tokens[:16],
                query_source=query_source,
                selected_count=result.selected_count,
                selected_ids=result.selected_ids[:16],
                cue_hits=result.cue_hits,
                bm25_hits=result.bm25_hits,
                expansion_hits=result.expansion_hits,
                top_k=10,
                max_depth=2,
                use_bm25_fallback=True,
            ),
        )
        return result.model_dump(mode="json")
    except Exception as e:
        warnings.append(
            f"memory_index wiring: retrieval 실패 ({type(e).__name__}: {e}). session-start 본체는 계속 진행."
        )
        # Phase 13 AC2: 예외 path 도 telemetry emit (negative example).
        append_telemetry_event(
            workspace_root,
            MemoryIndexTelemetryEvent(
                timestamp=_dt.now(_tz.utc),
                source="session-start",
                workspace_root=str(workspace_root),
                query_tokens_count=len(query_tokens),
                query_tokens=query_tokens[:16],
                query_source=query_source,
                error=True,
            ),
        )
        return None



def _detect_stale_branch_memories(
    project_profile_path: Path,
    warnings: list[str],
    *,
    apply: bool = False,
) -> dict[str, Any] | None:
    """v1.0.0: 종료된 브랜치의 메모리를 탐지(선택적으로 아카이브)한다.

    브랜치별 메모리(`active/<branch>/`)는 브랜치가 사라져도 남아 **고아** 가 되므로,
    세션 진입 시 역방향 점검한다 — git 에 없는 브랜치의 디렉터리를 찾는다.

    기본은 **탐지 + 안내** 만 한다. session-start 는 read 중심 스킬이라 무단으로 파일을
    옮기면 위험하기 때문이다. `--archive-stale-branches` 를 주면 실제 이동까지 수행한다.
    도구는 commit/push 를 하지 않으므로 protected main 과 호환되며, 변경은 작업 브랜치의
    PR 에 실려 나간다(piggyback).
    """
    try:
        from workflow_kit.common.paths import memory_root_dir
        memory_root = memory_root_dir(project_profile_path)
    except Exception:  # noqa: BLE001
        return None
    if not (memory_root / "active").is_dir():
        return None
    # 파일 경로가 아니라 **모듈로** 부른다 — 설치본에는 `workflow-source/` 가 없다.
    cmd = module_command("workflow_kit.tools.archive_branch_memory",
                         "--memory-root", str(memory_root), "--json")
    import subprocess

    def run(extra: list[str]) -> dict[str, Any]:
        proc = subprocess.run(cmd + extra, capture_output=True, text=True, timeout=120,
                              env=child_env(), encoding="utf-8", errors="replace")
        return json.loads(proc.stdout) if proc.stdout.strip() else {}

    try:
        payload = run(["--apply"] if apply else [])
        # 합류 반영 (TASK-2026-10-02-main-004): 기본 브랜치 체크아웃이면 도구가 반영 모드다
        # (`reflect_enabled`). 그때는 묻지 않고 반영한다 — 병합된 worktree 의 기록이 모 브랜치
        # 메모리에 들어오는 것이 이 세션이 이어받을 사실이고, 무엇을 했는지는 아래 warning 이 말한다.
        if (not apply and payload.get("reflect_enabled")
                and any(c.get("action") == "archive" for c in payload.get("candidates", []))):
            payload = run(["--apply"])
            apply = True
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"stale branch memory 점검 실패: {type(exc).__name__}")
        return None
    for j in payload.get("joined", []):
        warnings.append(
            f"합류한 브랜치 `{j['origin']}` 의 메모리를 `{j['parent']}` 에 반영했다 — 완료 {len(j['done'])}건 · "
            f"이월 {len(j['carried'])}건 · 되돌려 적음 {len(j['written_back'])}건 (handoff 목록 · §5 합류 줄 · "
            f"합류 기록 {j['record']}). 이 변경을 현재 브랜치의 commit 에 포함시켜라."
        )
    for c in payload.get("candidates", []):
        if c.get("action") == "blocked":
            warnings.append(f"브랜치 메모리 `{c['branch']}` 를 반영·아카이브하지 못했다: {c.get('reason')}")
    stale = [c["branch"] for c in payload.get("candidates", []) if c.get("action") == "archive"]
    if stale:
        if apply:
            warnings.append(
                f"종료된 브랜치 메모리 {len(stale)}건을 archived/ 로 이동했다: {', '.join(stale)}. "
                f"이 변경을 현재 작업 브랜치의 commit 에 포함시켜라."
            )
        else:
            warnings.append(
                f"종료된 브랜치 메모리 {len(stale)}건이 active/ 에 남아 있다: {', '.join(stale)}. "
                f"`python -m workflow_kit archive-branch-memory --apply` 로 아카이브하라."
            )
    return {"stale_branches": stale, "archived": bool(apply and stale)}

def _auto_seed_branch_memory(project_profile_path: Path) -> dict[str, Any] | None:
    """브랜치 네임스페이스가 없으면 seed 해서 **시작할 수 있게** 한다 (TASK-2026-09-30-claude-session-start-e6eb83-002).

    `active/<branch>/` 는 브랜치를 만든다고 생기지 않는다 (orchestration §5A.2). 중앙이
    배정하는 워크스페이스는 `seed-workspace-memory` 를 먼저 돌리지만, **하네스가 스스로
    만드는 worktree**(Claude Code 데스크톱의 `claude/<name>`)는 그 단계를 거치지 않는다.
    110차 실측: session-start 는 `missing_required_document` 로 멈췄고, 이어진
    `backlog-update` 는 멈추지 않고 state.json 만 `active/claude/<name>/` 에 만들어
    브랜치 메모리가 절반짜리로 갈렸다.

    seed 하는 조건은 좁다 — 셋 다 참일 때만:

    - 브랜치를 **이 workspace 의 git** 에서 얻었다 (env override · 모듈 앵커 답은 제외).
    - 그 브랜치의 handoff 가 없고, legacy 평면 handoff 도 없다 (있으면 기존 fallback).
    - 기본 브랜치가 따로 있고 그 네임스페이스에 handoff 가 있다 — 이 저장소가 브랜치별
      layout 을 쓰고 있다는 근거. 없으면 처음 쓰는 프로젝트라 bootstrap 이 할 일이다.

    seed 는 멱등이다 (있는 파일은 덮지 않는다). 무엇을 만들었는지는 호출자가 warning 으로 말한다.
    """
    try:
        from datetime import date  # noqa: PLC0415

        from workflow_kit.common.paths import (  # noqa: PLC0415
            BRANCH_SOURCE_WORKSPACE_GIT,
            HANDOFF_FILENAME,
            memory_root_dir,
            path_in_active,
            project_workspace_root,
            resolve_branch_for_workspace,
        )
        from workflow_kit.path_resolver import _detect_default_branch  # noqa: PLC0415

        workspace_root = project_workspace_root(project_profile_path)
        resolution = resolve_branch_for_workspace(workspace_root)
        if resolution.source != BRANCH_SOURCE_WORKSPACE_GIT:
            return None
        branch = resolution.slug
        memory_root = memory_root_dir(project_profile_path)
        active_dir = memory_root / "active"
        # `path_in_active` 는 브랜치 자리가 없으면 legacy 평면 자리로 떨어진다 — 둘 중
        # 하나라도 있으면 읽을 handoff 가 있는 것이다.
        if path_in_active(active_dir, HANDOFF_FILENAME, branch).exists():
            return None
        base = _detect_default_branch(workspace_root)
        if base == branch or not path_in_active(active_dir, HANDOFF_FILENAME, base).exists():
            return None

        from workflow_kit.common.git import short_head_sha  # noqa: PLC0415
        from workflow_kit.tools.seed_workspace_memory import seed  # noqa: PLC0415

        # 모 브랜치 내용은 **이 체크아웃의** `active/<base>/` 에서 읽는다 — 분기 시점 상태이고,
        # 작업 중인 코드와 같은 커밋이다. 원류 sha 는 그 커밋이다 (TASK-2026-10-02-main-001).
        origin_sha = short_head_sha(workspace_root)
        result = seed(
            memory_root=memory_root,
            branch=branch,
            axis=(f"`{base}` 에서 분기한 worktree — 작업 축은 첫 backlog-update 로 등록하는 task 가 정한다. "
                  f"분기 시점 기준선은 `active/{base}/session_handoff.md`"),
            task_title=f"브랜치 네임스페이스 자동 seed — `{base}` 에서 이어받음",
            out_of_scope=None,
            today=date.today().isoformat(),
            apply=True,
            force=False,
            # 업무를 모르므로 seed 사건만 기록하고 닫는다 — 제목은 update 로 바뀌지 않는다.
            task_status="done",
            wbs_exempt_reason="로드맵 밖 — worktree 브랜치 네임스페이스 자동 seed 사건 기록",
            inherit_from=base,
            origin_sha=origin_sha,
        )
    except Exception as exc:  # noqa: BLE001 — seed 실패는 원래의 부재 오류로 이어진다
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
    return result | {"base_branch": base}


def _task_id_collision_warnings(workspace_root: Path) -> list[str]:
    """워킹 트리의 task 가 원격의 같은 ID·다른 task 와 부딪히면 warning (TASK-2026-09-28-main-010).

    검출 자체는 `common.git.task_id_collisions` 가 한다 (main-016). 대시보드 지표에만
    실어 두면 아무도 안 본다 — 동기화 직후 에이전트가 **반드시** 보는 자리가 여기다.
    87차에 실제로 났다: 미커밋 `main-009` 와 원격의 같은 ID 가 다른 task 였다.

    **원격을 못 봤을 때는 말하지 않는다.** 원격 추적 ref 가 없다는 것은 그 브랜치가
    원격에 없다는 뜻이라 같은 브랜치 충돌이 원리상 생기지 않는다 — 매 세션 경고하면
    로컬 전용 브랜치·원격 없는 저장소에서 소음이 된다. '못 봤음' 은 대시보드 지표가
    `task_id_collision_measured=false` + 이유로 계속 싣는다 (모름을 안전으로 바꾸지 않는다).
    ref 는 마지막 fetch 시점이다 — 세션 시작 전 원격 동기화(작업 원칙)가 전제다.
    """
    try:
        from workflow_kit.common.git import task_id_collisions
        from workflow_kit.common.paths import branch_for_workspace, memory_active_dir
        branch = branch_for_workspace(workspace_root)
        tasks_dir = memory_active_dir(workspace_root) / branch / "backlog" / "tasks"
        found = task_id_collisions(tasks_dir, branch=branch)
    except Exception as exc:  # noqa: BLE001 — 점검 실패가 세션 진입을 막지 않는다
        return [f"task ID 충돌 점검 실패 ({type(exc).__name__}) — `python -m workflow_kit dashboard` 의 충돌 지표로 확인하라."]
    return [
        f"task ID 충돌: {task_id} — 로컬 {local!r} ≠ {found.ref} {remote!r}. "
        "로컬 쪽을 새 ID 로 재번호하고 참조를 함께 고쳐라 (다른 에이전트의 미커밋 작업이면 소유자 확인)."
        for task_id, local, remote in found.collisions
    ]


def _repair_missing_entrypoints(source_context: dict) -> dict:
    """부재 산출물을 현재 kit 버전으로 채운다. 실패해도 세션 진입을 막지 않는다.

    **낡은 것은 건드리지 않는다** — `ensure_entrypoints` 가 create-only 로 돈다.
    프로젝트 정체를 모르면(`PROJECT_PROFILE.md` 부재) 아무것도 만들지 않고
    `needs_bootstrap` 을 그대로 돌려준다: 이름을 지어내면 그 거짓이 이후 모든
    산출물에 실린다.
    """
    try:
        from workflow_kit.tools.ensure_entrypoints import run as ensure_run  # noqa: PLC0415

        root = Path.cwd()
        profile = source_context.get("project_profile_path")
        if profile:
            root = Path(profile).resolve().parent.parent
        return ensure_run(project_root=root, apply=True)
    except Exception as exc:  # noqa: BLE001 — 복구 실패가 진입을 막지 않는다
        return {"status": "repair_failed", "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the session-start prototype.")
    # v1.1.7: 정본 §11 은 `wk session-start` 를 그대로 안내한다 — 무인자 호출이
    # 실행 가능해야 한다. 미지정 시 cwd 에서 workspace 를 자동 탐색하고
    # branch-scoped 기본 경로로 떨어진다. 탐색 실패는 조용한 기본값이 아니라
    # missing_required_document 오류다.
    parser.add_argument("--session-handoff-path", required=False, default=None)
    # branch-scoped 레이아웃(v1.0.0+)은 인덱스 문서가 없다 — optional.
    # 미지정 시 daily backlog 디렉터리 관측(find_latest_daily_backlog)으로 대체.
    parser.add_argument("--work-backlog-index-path", required=False, default=None)
    parser.add_argument("--project-profile-path", required=False, default=None)
    parser.add_argument("--latest-backlog-path")
    # v0.11.22+ Phase 3b: ADR-005 memory_index retrieval 3-tuple opt-in wiring.
    # 둘 다 지정되면 session-start 가 진입 시 memory_index 에서 query 후 hints emit.
    # 부재 시 zero-risk skip (default) — 기존 caller 깨지지 않음.
    parser.add_argument("--memory-index-dir",
                        help="memory_index 절대 path. 부재 시 skip.")
    parser.add_argument("--memory-query-tokens",
                        help="comma-separated query tokens. 예: 'adr,memora,retrieval'. 부재 시 skip.")
    parser.add_argument("--archive-stale-branches", action="store_true",
                        dest="archive_stale_branches",
                        help="종료된 브랜치 메모리를 archived/ 로 실제 이동 (기본: 탐지+안내만)")
    args = parser.parse_args()

    source_context = {
        "session_handoff_path": args.session_handoff_path,
        "work_backlog_index_path": args.work_backlog_index_path,
        "project_profile_path": args.project_profile_path,
        "latest_backlog_path": args.latest_backlog_path,
        "memory_index_dir": args.memory_index_dir,
        "memory_query_tokens": args.memory_query_tokens,
    }

    auto_seed: dict[str, Any] | None = None
    try:
        profile_raw = args.project_profile_path
        if not profile_raw:
            discovered = discover_project_profile_path()
            if discovered is None:
                raise FileNotFoundError(
                    "PROJECT_PROFILE.md 를 cwd 상위에서 찾지 못했다 "
                    "(docs/PROJECT_PROFILE.md 또는 ai-workflow/memory/active/PROJECT_PROFILE.md). "
                    "--project-profile-path 로 명시하라."
                )
            profile_raw = str(discovered)
        project_profile_path = resolve_existing_path(profile_raw)
        # handoff 를 명시했으면 호출자가 자리를 골랐다 — seed 하지 않는다.
        if not args.session_handoff_path:
            auto_seed = _auto_seed_branch_memory(project_profile_path)
        session_handoff_path = resolve_existing_path(
            args.session_handoff_path
            or str(workflow_handoff_path(project_profile_path))
        )
        work_backlog_index_path = (
            resolve_existing_path(args.work_backlog_index_path)
            if args.work_backlog_index_path
            else None
        )
        # 자동 탐색 결과를 args 에도 반영 — 아래 helper 들(_build_memory_index_query_output)
        # 이 args 경유로 profile 경로를 읽는다.
        args.project_profile_path = str(project_profile_path)
        args.session_handoff_path = str(session_handoff_path)
    except FileNotFoundError as exc:
        # **중단하기 전에 스스로 채워 본다** (TASK-2026-08-24-main-006).
        # CLAUDE.md 의 self-bootstrap 절은 "없으면 scaffold 를 제안한다" 고 이미
        # 약속하고 있었는데, 실제 동작은 `missing_required_document` 로 멈추고
        # 그마저 legacy shim 경로를 안내했다 — 소비자에게는 "워크플로우가 안 돈다"
        # 로만 보였다.
        #
        # 부재만 채운다. 낡은 산출물을 여기서 덮으면, 포크를 **선언하지 않은**
        # 손수정이 세션을 여는 것만으로 사라진다 (소유자 결정 2026-08-24).
        repair = _repair_missing_entrypoints(source_context)
        if repair.get("created"):
            try:
                return main()  # 채웠으니 한 번만 다시 시도한다
            except RecursionError:  # pragma: no cover — 방어
                pass
        result = build_error_result(
            tool_version=TOOL_VERSION,
            error="필수 입력 문서를 읽을 수 없다.",
            error_code="missing_required_document",
            warnings=["session-start 기준선을 복원할 수 없어 후속 판단을 중단한다."],
            source_context=source_context | {
                "missing_path_detail": str(exc),
                "auto_repair": repair,
                "auto_seed": auto_seed,
            },
            recovery_hint=(
                "`python -m workflow_kit ensure-entrypoints --apply` 로 부재 산출물을 현재 kit 버전으로 "
                "채운다. 브랜치 메모리(`active/<branch>/`)만 없으면 "
                "`python -m workflow_kit seed-workspace-memory --axis <축> --task-title <제목> --apply` 로 만든다. "
                "프로젝트가 처음이면 `python3 -m workflow_kit.bootstrap_lib "
                "--target-root . --project-slug <slug> --project-name <name> "
                "--harness <harness>` 로 최초 생성한다."
            ),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    warnings: list[str] = []
    if auto_seed and auto_seed.get("status") == "ok":
        created = [item["path"] for item in auto_seed.get("planned", [])]
        warnings.append(
            f"브랜치 메모리가 없어 `{auto_seed.get('branch')}` 네임스페이스를 seed 했다 "
            f"(기준 브랜치 `{auto_seed.get('base_branch')}`, task {auto_seed.get('task_id')}"
            + (f", 원류 `{auto_seed['inherited']['origin']}` 에서 열린 task {len(auto_seed['inherited']['task_ids'])}건 · "
               f"기준선 · §5 를 이어받음" if auto_seed.get("inherited") else "")
            + "): "
            f"{created}. 작업은 이 네임스페이스에 `python -m workflow_kit backlog-update` 로 새 task 를 만들어 기록한다."
        )
        if auto_seed.get("errors"):
            warnings.append(f"브랜치 메모리 seed 가 일부 실패했다: {auto_seed['errors']}")
    elif auto_seed:
        warnings.append(f"브랜치 메모리 자동 seed 실패: {auto_seed.get('error') or auto_seed.get('errors')}")
    # v1.0.0: 종료된 브랜치 메모리 역방향 점검 (고아 방지). 실패해도 세션 진입을 막지 않는다.
    _detect_stale_branch_memories(
        project_profile_path, warnings,
        apply=getattr(args, "archive_stale_branches", False),
    )
    # **매 시작마다** 진입점을 점검한다 (TASK-2026-08-24-main-006).
    #
    # 실패 경로에만 달았을 때는 절반만 동작했다 — 하네스 진입점
    # (`.claude/commands/*` 등)이 없어도 session-start 는 *상태 문서* 만 읽으므로
    # `status: ok` 로 끝났고, 복구 경로에 들어가지도 않았다. 실측으로 그 구멍을
    # 확인하고 성공 경로로 옮겼다.
    #
    # 부재만 채우고 낡음은 경고로 남긴다. 여기서 덮으면 포크를 **선언하지 않은**
    # 손수정이 세션을 여는 것만으로 사라진다.
    entrypoints = _repair_missing_entrypoints(source_context)
    if entrypoints.get("created"):
        warnings.append(
            "부재 진입점 "
            f"{len(entrypoints['created'])}건을 kit v{entrypoints.get('kit_version')} 로 "
            f"생성했다: {entrypoints['created']}"
        )
    for item in entrypoints.get("stale") or []:
        warnings.append(
            f"진입점이 낡았다: {item['path']} (v{item.get('marker')} < kit "
            f"v{item.get('kit_version')}) — 자동으로 덮지 않는다. 갱신은 bootstrap 을 "
            "직접 실행한다 (포크 선언이 있는 파일은 그때도 지켜진다)"
        )
    if entrypoints.get("status") == "needs_bootstrap":
        warnings.append(f"진입점 점검 생략: {entrypoints.get('reason')}")
    try:
        handoff = parse_handoff(session_handoff_path)
        warnings.extend(handoff.get("warnings", []))

        profile = parse_project_profile_session(project_profile_path)
        warnings.extend(profile.get("warnings", []))

        latest_backlog_path: Path | None
        if args.latest_backlog_path:
            latest_backlog_path = resolve_existing_path(args.latest_backlog_path)
        else:
            # legacy 인덱스 문서가 주어졌을 때만 링크 기반 판정을 쓴다.
            # branch-scoped 레이아웃(인덱스 없음)은 daily 디렉터리 관측이 정본이다 —
            # 인덱스 자리에 daily 파일을 넣으면 task 상세 파일을 최신 backlog 로
            # 오판하던 결함(TASK-018 확장분)의 처방.
            latest_backlog_path = (
                find_latest_backlog_path(work_backlog_index_path)
                if work_backlog_index_path is not None
                else None
            )
            if latest_backlog_path is None or not latest_backlog_path.exists():
                latest_backlog_path = find_latest_daily_backlog(
                    workflow_backlog_dir(project_profile_path)
                )
            if latest_backlog_path is None:
                warnings.append(
                    "최신 backlog 를 확인하지 못했다 (index 문서도, daily backlog 디렉터리도 없음)."
                )

        backlog: dict[str, Any] = {"tasks": [], "in_progress_items": [], "blocked_items": [], "done_items": [], "warnings": []}
        if latest_backlog_path is not None:
            backlog = parse_backlog(latest_backlog_path)
            warnings.extend(backlog.get("warnings", []))

        # 비교 분모는 **하루치 backlog 가 아니라 task corpus 전수** 다
        # (TASK-2026-09-02-main-002). `parse_backlog` 는 *오늘자 daily 파일 하나* 를
        # 읽는데, append-only 레이아웃에서 in_progress task 는 등록된 날짜의 파일에
        # 있다 — 그래서 어제 시작해 오늘 이어받는 작업이 하나만 있어도 매 세션
        # 시작마다 거짓 경고가 났다 (실측 2026-09-02: corpus in_progress 는 handoff
        # 와 정확히 일치하는데 오늘자 backlog 는 비어 있어 불일치로 보고).
        #
        # corpus 가 없는 legacy 프로젝트에서만 종전대로 daily backlog 를 쓴다.
        #
        # 분모의 뿌리는 **방금 고른 backlog 문서 자신** 이다 (`.parent`). profile 에서
        # 다시 유도하면 안 된다 — `--session-handoff-path` / `--work-backlog-index-path`
        # 로 다른 워크스페이스를 가리키면서 profile 만 호스트 저장소를 쓰는 호출이
        # 실재하고(seed / claim 스모크), 그때 profile 파생 경로는 **호스트 저장소의**
        # task corpus 를 집어 남의 저장소 task 와 대조하게 된다.
        corpus_dir = (
            latest_backlog_path.parent
            if latest_backlog_path is not None
            else workflow_backlog_dir(project_profile_path)
        )
        corpus = collect_task_corpus_status(corpus_dir)
        if corpus is not None:
            compare_in_progress = corpus["in_progress_items"]
            compare_blocked = corpus["blocked_items"]
        else:
            compare_in_progress = cast(list[str], backlog.get("in_progress_items", []))
            compare_blocked = cast(list[str], backlog.get("blocked_items", []))

        warnings.extend(
            compare_state_lists(handoff.get("in_progress_items", []), compare_in_progress, "in_progress")
        )
        warnings.extend(compare_state_lists(handoff.get("blocked_items", []), compare_blocked, "blocked"))

        next_documents = dedupe_normalized_backticked(
            [
                str(session_handoff_path),
                str(latest_backlog_path) if latest_backlog_path else "",
                str(project_profile_path),
                *[str(path) for path in handoff.get("next_documents", []) if path.exists()],
            ]
        )

        # v0.9.5 chapter 9 R-A follow-up part 2: skill context load integration
        # session-start 가 PURPOSE.md + state.json.purpose_digest 자동 read
        from workflow_kit.common.paths import project_workspace_root, workflow_memory_dir
        from workflow_kit.common.schemas import SessionStartOutput, SessionStartPurposeContext

        workspace_root = project_workspace_root(project_profile_path)
        warnings.extend(_task_id_collision_warnings(workspace_root))
        state_json_path = workflow_state_path(project_profile_path)
        purpose_context_data = build_purpose_context(
            workspace_root=workspace_root,
            state_path=state_json_path,
        )
        purpose_context = SessionStartPurposeContext(**purpose_context_data)
        warnings.extend(purpose_context_data.get("scope_warnings", []))

        # v0.11.0 chapter 11 R-A follow-up cycle 3: two-step CoT ingest
        # session-start 가 PURPOSE.md 를 2-step (raw -> structured + cross-ref) 으로 read
        from workflow_kit.common.purpose_ingest import run_two_step_cot_ingest
        from workflow_kit.common.schemas import SessionStartPurposeCoTTrace

        cot_result = run_two_step_cot_ingest(workspace_root=workspace_root)
        purpose_cot_trace = SessionStartPurposeCoTTrace(
            step1_raw_excerpt=cot_result.cot_trace.step1_raw_excerpt,
            step1_truncated=cot_result.cot_trace.step1_truncated,
            step1_char_count=cot_result.cot_trace.step1_char_count,
            step2_structured_summary=cot_result.cot_trace.step2_structured_summary,
            cross_ref_matched=cot_result.cross_ref.matched,
            cross_ref_missing=cot_result.cross_ref.missing_refs,
            cross_ref_warnings=cot_result.cross_ref.warnings,
            overall_warnings=cot_result.overall_warnings,
        )
        warnings.extend(cot_result.overall_warnings)

        # v0.11.2 chapter 13 R-A follow-up cycle 4 deferred 통합: graph insights
        # session-start 가 PURPOSE.md Goals ↔ deliverables 매핑 분석 자동 호출
        from workflow_kit.common.purpose_graph import run_graph_insights
        from workflow_kit.common.schemas import SessionGraphInsightsOutput

        # ADR-027 M-003: roadmap 층 보고. 부재 시 present=False (graceful skip).
        # 계산 실패는 조용히 넘기지 않고 warning 으로 남긴다 — 폴백은 조용히 하지 않는다.
        from workflow_kit.common.state.roadmap import build_session_roadmap_context
        try:
            roadmap_context = build_session_roadmap_context(workspace_root)
            if roadmap_context.issues_count:
                warnings.append(
                    f"roadmap 정합 이슈 {roadmap_context.issues_count}건 — "
                    "`python -m workflow_kit refresh-state --check` 로 확인하라 (ADR-027)."
                )
        except Exception as roadmap_exc:  # noqa: BLE001 — 로드맵 결함이 세션 진입을 막으면 안 된다
            roadmap_context = None
            warnings.append(f"roadmap 컨텍스트 계산 실패 ({type(roadmap_exc).__name__}) — roadmap/ 형식을 점검하라.")

        graph_result = run_graph_insights(workspace_root=workspace_root)
        graph_insights = SessionGraphInsightsOutput(
            coverage_pct=(graph_result.coverage.coverage_pct if graph_result.coverage else 0.0),
            coverage_mode=(graph_result.coverage.mode if graph_result.coverage else "none"),
            covered_count=(graph_result.coverage.covered_count if graph_result.coverage else 0),
            uncovered_count=(graph_result.coverage.uncovered_count if graph_result.coverage else 0),
            covered_goals=(graph_result.coverage.covered if graph_result.coverage else []),
            uncovered_goals=(graph_result.coverage.uncovered if graph_result.coverage else []),
            surprising_count=(len(graph_result.surprising.surprising) if graph_result.surprising else 0),
            scope_creep_warnings=(graph_result.surprising.scope_creep_warnings if graph_result.surprising else []),
            gaps_count=(len(graph_result.gaps.gaps) if graph_result.gaps else 0),
            health_score=(graph_result.health.score if graph_result.health else 0),
            health_tier=(graph_result.health.tier if graph_result.health else "unknown"),
            warnings=graph_result.overall_warnings,
        )
        warnings.extend(graph_result.overall_warnings)

        # v0.10.2: self-bootstrap mode
        # 핵심 4 file (handoff / backlog index / project profile / state.json) 모두
        # 부재 시 status="warning" + self_bootstrap_suggested=True + init commands emit.
        # AGENTS.md 부재 환경 (skill-only entry) 의 *최소 effort* 진입 정공법.
        all_missing = (
            not session_handoff_path.exists()
            and (work_backlog_index_path is None or not work_backlog_index_path.exists())
            and not state_json_path.exists()
        )
        self_bootstrap_suggested = all_missing
        self_bootstrap_init_commands: list[str] = []
        if all_missing:
            self_bootstrap_init_commands = [
                f"python3 scripts/bootstrap_workflow_kit.py --target-root {workspace_root} "
                f"--project-slug <slug> --project-name <name> --adoption-mode new "
                f"--harness claude-code --entry-mode skill-only",
                # v1.1.7: 소비자 실행 경로는 wk 하나다 (정본 §11) — skills/ 스크립트
                # 경로는 배포물에 없다 (TASK-021).
                "python -m workflow_kit session-start",
            ]
            warnings.append(
                "self-bootstrap mode: 핵심 4 file 모두 부재. "
                "bootstrap_workflow_kit.py 실행 권장 (위 self_bootstrap_init_commands 참조)."
            )

        output_model = SessionStartOutput(
            status="warning" if self_bootstrap_suggested else "ok",
            tool_version=TOOL_VERSION,
            summary=build_session_summary(handoff, backlog, profile),
            in_progress_items=dedupe_normalized_backticked(
                handoff.get("in_progress_items", []) + backlog.get("in_progress_items", [])
            ),
            blocked_items=dedupe_normalized_backticked(
                handoff.get("blocked_items", []) + backlog.get("blocked_items", [])
            ),
            latest_backlog_path=str(latest_backlog_path) if latest_backlog_path else None,
            next_documents=next_documents,
            recommended_next_action=make_session_recommended_action(warnings, backlog, profile),
            warnings=warnings,
            validation_notes=[],
            # state.json 쪽과 **같은 정본**을 쓴다. 이 자리는 원래 맞았고
            # builder 쪽이 틀렸는데, 변환이 두 곳에 있었던 것이 결함이다 (main-002).
            environment_constraints=normalize_constraint_values(
                handoff.get("constraints"), profile.get("constraints")
            ),
            source_documents={
                "session_handoff_path": str(session_handoff_path),
                # branch-scoped 레이아웃은 인덱스 문서가 없다 — 계약 키는 유지하되
                # 빈 문자열로 "관측된 인덱스 없음" 을 표기한다.
                "work_backlog_index_path": str(work_backlog_index_path) if work_backlog_index_path else "",
                "project_profile_path": str(project_profile_path),
            },
            purpose_context=purpose_context,
            purpose_cot_trace=purpose_cot_trace,
            graph_insights=graph_insights,
            self_bootstrap_suggested=self_bootstrap_suggested,
            self_bootstrap_init_commands=self_bootstrap_init_commands,
            memory_index_query_output=_build_memory_index_query_output(
                args, workspace_root, warnings
            ),
            roadmap_context=roadmap_context,
        )
        result = output_model.model_dump()
    except FileNotFoundError as exc:
        result = build_error_result(
            tool_version=TOOL_VERSION,
            error="참조 문서를 읽는 중 필요한 경로를 확인하지 못했다.",
            error_code="missing_referenced_document",
            warnings=["입력 문서의 링크 또는 명시 경로를 다시 확인해야 한다."],
            source_context=source_context | {"missing_path_detail": str(exc)},
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    except Exception as exc:
        result = build_error_result(
            tool_version=TOOL_VERSION,
            error="session-start 실행 중 예기치 않은 오류가 발생했다.",
            error_code="session_start_runtime_error",
            warnings=["파서 또는 입력 문서 형식을 점검한 뒤 다시 실행해야 한다."],
            source_context=source_context | {"exception_type": type(exc).__name__},
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

        # v0.6.5: stage_completion merge (pilot template, batch 적용)
        result = merge_into_result(
            result,
            build_stage_completion(
                stage_name="session-start",
                stage_status="ok" if result.get("status") in ("ok", "success") else "warning" if result.get("status") == "warning" else "error",
                artifacts=["ai-workflow/memory/active/state.json"],
                next_stage=None,
                notes=[result.get("summary", "")[:200]] if result.get("summary") else [],
            ),
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
