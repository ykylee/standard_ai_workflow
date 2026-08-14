#!/usr/bin/env python3
"""Prototype runner for the backlog-update skill."""

from __future__ import annotations

import argparse
import json
import datetime as dt
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common.errors import build_error_result
from workflow_kit.common.contracts.stage_gate_runtime import build_stage_completion, merge_into_result
from workflow_kit.common.normalize import normalize_backticked
from workflow_kit.common.paths import (
    memory_active_dir,

    workflow_state_path,
    get_current_branch,
    resolve_existing_path,
    workflow_branch_dir,
    workflow_memory_dir,
)
from workflow_kit.common.planning import determine_conservative_task_status
from workflow_kit.common.project_docs import (
    TASK_ID_CAPTURE_RE,
    parse_backlog_task_entries,
    parse_project_profile_backlog,
)
from workflow_kit.common.purpose_context import build_purpose_context, check_scope_creep
from workflow_kit.common.workflow_state import build_state_cache_refresh_hint, refresh_workflow_state_cache
from workflow_kit.common.workflow_writes import (
    ensure_backlog_index_entry,
    merge_task_file,
    render_task_file,
    sync_handoff_status,
    upsert_backlog_entry,
)


def infer_backlog_path(project_profile_path: Path, target_date: str) -> Path:
    branch_dir = workflow_branch_dir(project_profile_path)
    return (branch_dir / "backlog" / f"{target_date}.md").resolve()


# task ID 문법은 project_docs 가 단일 출처 — 여기서 사본을 들면 갈라진다.
TASK_ID_RE = TASK_ID_CAPTURE_RE


def branch_slug(branch: str | None = None) -> str:
    """브랜치명을 파일명에 안전한 slug 로 정규화 (`feature/x` → `feature-x`)."""
    raw = branch or get_current_branch()
    slug = re.sub(r"[^0-9A-Za-z._-]+", "-", raw.replace("/", "-")).strip("-")
    return slug or "main"


def suggest_next_task_id(
    tasks: list[dict[str, Any]],
    *,
    target_date: str | None = None,
    branch: str | None = None,
) -> str:
    """`TASK-<date>-<slug>-<NNN>` 형식의 다음 task ID.

    **왜 slug 를 넣나**: 순번을 *브랜치 안에서만* 매기면 두 브랜치가 같은 날 동시에
    작업해도 ID 가 겹치지 않는다. 아카이브로 합쳐진 뒤에도 전역 유일하므로 과거 이력
    조회가 안전하다.

    **버그 수정**: 이전 구현은 `TASK-(\\d+)` 로 매칭해 `TASK-2026-07-20-001` 에서 연도
    `2026` 을 순번으로 오인, 다음 ID 가 `TASK-2027` 이 됐다. 이제 날짜/slug/순번을
    분리해 파싱하고, **같은 날짜 + 같은 브랜치** 인 것만 순번 비교 대상으로 삼는다.
    """
    date = target_date or dt.date.today().isoformat()
    slug = branch_slug(branch)
    max_num = 0
    for task in tasks:
        raw = str(task.get("task_id") or "")
        match = TASK_ID_RE.match(raw)
        if not match:
            continue
        task_date, task_slug, num = match.group(1), match.group(2), match.group(3)
        # 날짜가 있으면 같은 날만, slug 가 있으면 같은 브랜치만 비교 대상.
        if task_date and task_date != date:
            continue
        if task_slug and task_slug != slug:
            continue
        max_num = max(max_num, int(num))
    return f"TASK-{date}-{slug}-{max_num + 1:03d}"


def build_draft_entry(
    *,
    task_id: str,
    task_name: str,
    status: str,
    priority: str,
    request_date: str,
    owner: str | None,
    host_name: str | None,
    host_ip: str | None,
    affected_documents: list[str],
    task_summary: str | None,
    progress_note: str | None,
    done_criteria: list[str] | str | None,
    result_note: list[str] | str | None,
    next_step: str | None,
    risks: list[str] | str | None,
    follow_up: list[str] | str | None,
    validation_result: str | None = None,
    kind: str = "generic",
    source_anchor: str | None = None,
    source_path: str | None = None,
) -> list[str]:
    """per-task SSOT 파일 본문 (v0.14.0+ append-only layout).

    v1.0.1 이전에는 legacy 인라인 항목(`## TASK-… ` + `- 상태:` 나열)을 만들어 daily
    index 에 통째로 넣었다. 현행 layout 은 index=link 모음 / 본문=`tasks/TASK-….md`
    이므로, 여기서 만드는 것은 **task 파일 자체**다.

    `- 상태:` 라인은 frontmatter 와 중복이지만 남긴다 — `BacklogParser` 가 task 본문을
    읽어 상태를 뽑을 때 쓰는 라인이고, 이걸 빼면 update 모드가 상태를 못 읽는다.
    """
    detail: list[str] = [
        "## 📝 Description",
        "",
        f"- 상태: {status}",
        f"- 우선순위: {priority}",
        f"- 요청일: {request_date}",
        f"- 담당: {owner}" if owner else "- 담당:",
        f"- 호스트명: {host_name}" if host_name else "- 호스트명:",
        f"- 호스트 IP: {host_ip}" if host_ip else "- 호스트 IP:",
        "- 영향 문서:",
    ]
    if affected_documents:
        detail.extend([f"  - `{doc}`" for doc in affected_documents])
    else:
        detail.append("  - ")
    detail.extend(
        [
            "",
            f"- 작업 내용: {task_summary}" if task_summary else "- 작업 내용:",
            *_label_lines("완료 기준", done_criteria),
            "",
            "## 🛠️ Implementation / Content",
            "",
            f"- 진행 현황: {progress_note}" if progress_note else "- 진행 현황:",
            f"- 다음 세션 시작 포인트: {next_step}" if next_step else "- 다음 세션 시작 포인트:",
            *_label_lines("남은 리스크", risks),
            "",
            "## ✅ Outcome",
            "",
            *_label_lines("작업 결과", result_note),
        ]
    )
    # v1.0.2: `--validation-result` 를 산출물에 싣는다. 이전에는 이 값이 *result_note 가
    # 비어 있을 때만* 그 자리를 대신했고, 둘 다 주면 **검증 결과가 조용히 버려졌다** —
    # `done` 판정의 근거가 되는 값인데 정작 task SSOT 어디에도 남지 않았다.
    if validation_result and validation_result not in _as_list(result_note):
        detail.append(f"- 검증 결과: {validation_result}")
    detail.extend(_label_lines("후속 작업", follow_up))
    return render_task_file(
        task_id=task_id,
        title=task_name,
        status=status,
        created_at=request_date,
        kind=kind,
        source_anchor=source_anchor or f"{kind}-{task_id.lower()}",
        source_path=source_path or f"backlog/{request_date}.md",
        body_lines=detail,
    )


def _as_list(value: list[str] | str | None) -> list[str]:
    """단일 값과 목록을 같은 모양으로. 빈 문자열은 값이 아니다."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    return [v for v in value if v]


def _label_lines(label: str, value: list[str] | str | None) -> list[str]:
    """`- <label>: <값>` 줄들. 값이 없으면 빈 placeholder 한 줄.

    다중값을 **한 줄에 개행으로 밀어 넣지 않는다** — 그 우회책이 update 마다 줄을
    중복시켰다 (2026-08-14 실측). 값 하나당 한 줄이고, 갱신은 묶음 단위로 교체된다
    (:func:`workflow_kit.common.workflow_writes._set_list_field`).
    """
    items = _as_list(value)
    return [f"- {label}: {item}" for item in items] or [f"- {label}:"]


def detect_confirmation_fields(data: dict[str, Any]) -> list[str]:
    mapping = {
        "owner": "담당",
        "host_name": "호스트명",
        "host_ip": "호스트 IP",
        "affected_documents": "영향 문서",
        "done_criteria": "완료 기준",
        "result_note": "작업 결과",
        "next_step": "다음 세션 시작 포인트",
        "risks": "남은 리스크",
        "follow_up": "후속 작업",
    }
    missing: list[str] = []
    for key, label in mapping.items():
        value = data.get(key)
        if value is None or value == "" or value == []:
            missing.append(label)
    return missing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the backlog-update prototype.")
    parser.add_argument("--project-profile-path", required=True)
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--task-brief", required=True)
    parser.add_argument("--daily-backlog-path")
    parser.add_argument("--target-date")
    parser.add_argument("--task-id")
    parser.add_argument("--mode", choices=["create", "update", "auto"], default="auto")
    # v1.1.7 (TASK-2026-08-11-main-023): kind/priority 의 default 를 None 으로.
    # argparse default 가 있으면 update 모드에서 "명시 안 함" 과 "기본값 요청" 을
    # 구분할 수 없어, 미지정 호출이 기존 값(kind: feature 등)을 기본값으로 덮었다.
    parser.add_argument("--kind", choices=["release", "session", "generic"], default=None,
                        help="task SSOT frontmatter 의 kind (daily index 의 [kind] marker). create 기본값 generic, update 는 미지정 시 보존.")
    parser.add_argument("--status")
    parser.add_argument("--priority", default=None,
                        help="create 기본값 high, update 는 미지정 시 보존.")
    parser.add_argument("--owner")
    parser.add_argument("--host-name")
    parser.add_argument("--host-ip")
    parser.add_argument("--affected-document", action="append", dest="affected_documents", default=[])
    parser.add_argument("--progress-note")
    # v1.2.2 (task SSOT 2단계): 열거형 필드는 **반복 지정**을 받는다.
    # 이전에는 마지막 하나만 남아, 값을 여러 개 주면 나머지가 **조용히 사라졌다**
    # (2026-08-14 실측: 5건을 적었는데 1건만 들어갔다). 개행을 끼워 넣는 우회책은
    # update 마다 줄을 중복시켰다 — 그 둘이 같은 뿌리다.
    parser.add_argument("--done-criteria", action="append", dest="done_criteria", default=[],
                        help="완료 기준 (반복 지정 가능)")
    parser.add_argument("--result-note", action="append", dest="result_note", default=[],
                        help="작업 결과 (반복 지정 가능)")
    parser.add_argument("--next-step")
    parser.add_argument("--risks", action="append", dest="risks", default=[],
                        help="남은 리스크 (반복 지정 가능)")
    parser.add_argument("--follow-up", action="append", dest="follow_up", default=[],
                        help="후속 작업 (반복 지정 가능)")
    parser.add_argument("--validation-result")
    parser.add_argument("--work-backlog-index-path")
    parser.add_argument("--session-handoff-path")
    parser.add_argument("--apply", action="store_true")
    # v0.11.22+ Phase 3d: ADR-005 memory_index retrieval 3-tuple opt-in wiring (session-start / doc-sync 동일 패턴).
    parser.add_argument("--memory-index-dir",
                        help="memory_index 절대 path. 부재 시 skip.")
    parser.add_argument("--memory-query-tokens",
                        help="comma-separated query tokens. 부재 시 skip.")
    return parser.parse_args()


def _build_memory_index_query_output(
    args: argparse.Namespace,
    workspace_root: Path,
    warnings: list[str],
) -> dict[str, Any] | None:
    """v0.11.22+ Phase 3d: optional ADR-005 memory_index retrieval 3-tuple 호출 (session-start / doc-sync 동일 패턴).

    - flag 부재 + workspace memory_index dir 부재 → None (zero-risk skip).
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
    if args.memory_query_tokens:
        query_tokens = [t.strip() for t in args.memory_query_tokens.split(",") if t.strip()]
        query_source = QUERY_SOURCE_EXPLICIT
    else:
        try:
            _state_path = workflow_state_path(Path(args.project_profile_path))
        except (OSError, ValueError):
            _state_path = None
        query_tokens, query_source = derive_context_query_tokens(
            _state_path, base_tokens=["backlog", "task", "workflow"],
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
    except ValueError:
        warnings.append(
            "memory_index wiring: --memory-index-dir 가 workspace_root 외부. "
            "본 release (Phase 3d) 정공법은 ws subdir 만 지원."
        )
        # Phase 13 AC2: 외부 dir 도 telemetry emit (negative example).
        append_telemetry_event(
            workspace_root,
            MemoryIndexTelemetryEvent(
                timestamp=_dt.now(_tz.utc),
                source="backlog-update",
                workspace_root=str(workspace_root),
                query_tokens_count=len(query_tokens),
                query_tokens=query_tokens[:16],
                query_source=query_source,
                error=True,
            ),
        )
        return None
    try:
        result = query_memory_index_for_dispatcher(target, query_tokens)
        # Phase 13 AC2: telemetry emit (success path).
        append_telemetry_event(
            workspace_root,
            MemoryIndexTelemetryEvent(
                timestamp=_dt.now(_tz.utc),
                source="backlog-update",
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
                use_bm25_fallback=False,
            ),
        )
        return result.model_dump(mode="json")
    except Exception as e:
        warnings.append(
            f"memory_index wiring: retrieval 실패 ({type(e).__name__}: {e}). backlog-update 본체는 계속 진행."
        )
        # Phase 13 AC2: 예외 path 도 telemetry emit (negative example).
        append_telemetry_event(
            workspace_root,
            MemoryIndexTelemetryEvent(
                timestamp=_dt.now(_tz.utc),
                source="backlog-update",
                workspace_root=str(workspace_root),
                query_tokens_count=len(query_tokens),
                query_tokens=query_tokens[:16],
                query_source=query_source,
                error=True,
            ),
        )
        return None


def main() -> int:
    args = parse_args()
    source_context = {
        "project_profile_path": args.project_profile_path,
        "task_name": args.task_name,
        "task_brief": args.task_brief,
        "daily_backlog_path": args.daily_backlog_path,
        "memory_index_dir": args.memory_index_dir,
        "memory_query_tokens": args.memory_query_tokens,
        "target_date": args.target_date,
        "task_id": args.task_id,
        "mode": args.mode,
    }

    # v0.11.20: invalid_task_brief error_code (3rd stable error_code 정합)
    # task_brief 가 비어있거나 whitespace-only 면 backlog entry 의 `작업 내용` /
    # `진행 현황` line 이 `-` placeholder 만 남아 downstream consumer 가
    # 무엇을 했는지 알 수 없음. 명시적 차단.
    if not args.task_brief or not args.task_brief.strip():
        result = build_error_result(
            tool_version=TOOL_VERSION,
            error="backlog-update 의 task_brief 가 비어 있다.",
            error_code="invalid_task_brief",
            warnings=["--task-brief 에 작업의 핵심 변경/조치 1~2 문장을 입력해야 한다."],
            source_context=source_context,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    try:
        project_profile_path = resolve_existing_path(args.project_profile_path)
        profile_data = parse_project_profile_backlog(project_profile_path)
    except FileNotFoundError as exc:
        result = build_error_result(
            tool_version=TOOL_VERSION,
            error="backlog-update 에 필요한 입력 문서를 읽을 수 없다.",
            error_code="missing_required_document",
            warnings=["프로젝트 프로파일 경로를 다시 확인해야 한다."],
            source_context=source_context | {"missing_path_detail": str(exc)},
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    except Exception as exc:
        result = build_error_result(
            tool_version=TOOL_VERSION,
            error="backlog-update 실행 중 예기치 않은 오류가 발생했다.",
            error_code="backlog_update_runtime_error",
            warnings=["입력 값과 backlog 파서 동작을 점검한 뒤 다시 실행해야 한다."],
            source_context=source_context | {"exception_type": type(exc).__name__},
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    try:
        warnings: list[str] = []
        if "warnings" in profile_data:
            warnings.extend(profile_data["warnings"])

        request_date = args.target_date or datetime.now().strftime("%Y-%m-%d")
        work_backlog_index_path = (
            Path(args.work_backlog_index_path).expanduser().resolve()
            if args.work_backlog_index_path
            else (workflow_memory_dir(project_profile_path) / "work_backlog.md").resolve()
        )
        session_handoff_path = (
            Path(args.session_handoff_path).expanduser().resolve()
            if args.session_handoff_path
            else (workflow_branch_dir(project_profile_path) / "session_handoff.md").resolve()
        )

        daily_backlog_path: Path
        if args.daily_backlog_path:
            daily_backlog_path = Path(args.daily_backlog_path).expanduser().resolve()
        else:
            daily_backlog_path = infer_backlog_path(project_profile_path, request_date)

        existing_tasks = parse_backlog_task_entries(daily_backlog_path) if daily_backlog_path.exists() else []

        requested_mode = args.mode
        if requested_mode == "auto":
            # v1.0.2 정정 — 이전에는 `--task-id` 가 있으면 **무조건 update** 였다.
            # 그래서 아직 없는 ID 로 새 작업을 등록하려 하면 `cannot_determine` 이 되어
            # 아무것도 쓰지 않은 채 `status: ok` 를 냈다. auto 의 뜻은 "있으면 갱신,
            # 없으면 생성" 이다 — 존재 여부를 실제로 보고 정한다.
            known_ids = {t["task_id"] for t in existing_tasks}
            requested_mode = "update" if (args.task_id and args.task_id in known_ids) else "create"

        operation_type = "create_entry"
        if not daily_backlog_path.exists():
            operation_type = "create_daily_backlog"
        if requested_mode == "update":
            operation_type = "update_entry"

        matched_task: dict[str, Any] | None = None
        if requested_mode == "update":
            if not args.task_id:
                operation_type = "cannot_determine"
                warnings.append("기존 항목 갱신에는 `task_id` 가 필요하다.")
            else:
                for task in existing_tasks:
                    if task["task_id"] == args.task_id:
                        matched_task = task
                        break
                if matched_task is None and daily_backlog_path.exists():
                    operation_type = "cannot_determine"
                    warnings.append(f"`{args.task_id}` 항목을 대상 backlog 에서 찾지 못했다.")

        task_id = args.task_id or suggest_next_task_id(
            existing_tasks, target_date=getattr(args, 'target_date', None))
        # v1.1.8 (TASK-2026-08-12-main-008): update 에서 --status 미지정이면 기존
        # 상태를 보존한다 — 미지정은 "바꾸지 말라" 다. 기존 상태는 task SSOT
        # frontmatter (`status: X`) 에서 읽는다.
        current_status: str | None = None
        _ssot_probe = daily_backlog_path.parent / "tasks" / f"{task_id}.md"
        if requested_mode == "update" and _ssot_probe.exists():
            _m = re.search(r"^status:\s*(\S+)", _ssot_probe.read_text(encoding="utf-8"), re.M)
            if _m:
                current_status = _m.group(1)
        status, status_warnings = determine_conservative_task_status(
            args.status, args.validation_result, operation_type, current_status=current_status)
        warnings.extend(status_warnings)

        progress_note = args.progress_note
        if not progress_note:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            progress_note = f"`{timestamp}` 기준 {args.task_brief}"

        result_note = _as_list(args.result_note)
        if args.validation_result and not result_note:
            result_note = [args.validation_result]

        fields_data = {
            "owner": args.owner,
            "host_name": args.host_name,
            "host_ip": args.host_ip,
            "affected_documents": args.affected_documents,
            "done_criteria": args.done_criteria,
            "result_note": result_note,
            "next_step": args.next_step,
            "risks": args.risks,
            "follow_up": args.follow_up,
        }
        fields_requiring_confirmation = [normalize_backticked(item) for item in detect_confirmation_fields(fields_data)]

        resolved_kind = args.kind or "generic"
        resolved_priority = args.priority or "high"

        # v1.1.7 (TASK-2026-08-11-main-023): update 모드는 재생성이 아니라 **병합**이다.
        # 기존 task SSOT 파일이 있으면 그것을 원본으로 삼고 명시된 값만 반영한다 —
        # 이전에는 인자만으로 문서를 다시 만들어 미지정 필드(작업 내용·완료 기준·담당·
        # kind)를 삭제했다 (실측: TASK-018 파일 손 복원). draft(무-apply)에도 병합
        # 결과를 보여 준다 — 쓸 내용과 보여 준 초안이 달라선 안 된다.
        task_ssot_path = daily_backlog_path.parent / "tasks" / f"{task_id}.md"
        update_merge = requested_mode == "update" and task_ssot_path.exists()

        if update_merge:
            existing_lines = task_ssot_path.read_text(encoding="utf-8").splitlines()
            scalar_updates: dict[str, str] = {"진행 현황": progress_note}
            if args.priority:
                scalar_updates["우선순위"] = args.priority
            if args.owner:
                scalar_updates["담당"] = args.owner
            if args.host_name:
                scalar_updates["호스트명"] = args.host_name
            if args.host_ip:
                scalar_updates["호스트 IP"] = args.host_ip
            list_updates: dict[str, list[str]] = {}
            if args.done_criteria:
                list_updates["완료 기준"] = _as_list(args.done_criteria)
            if result_note:
                list_updates["작업 결과"] = _as_list(result_note)
            if args.validation_result and args.validation_result != result_note:
                scalar_updates["검증 결과"] = args.validation_result
            if args.next_step:
                scalar_updates["다음 세션 시작 포인트"] = args.next_step
            if args.risks:
                list_updates["남은 리스크"] = _as_list(args.risks)
            if args.follow_up:
                list_updates["후속 작업"] = _as_list(args.follow_up)
            # 작업 내용은 원문 보존이 원칙 — 비어 있을 때만 brief 로 채운다.
            if any(line.strip() == "- 작업 내용:" for line in existing_lines):
                scalar_updates["작업 내용"] = args.task_brief
            draft_entry, merge_missing = merge_task_file(
                existing_lines,
                status=status,
                kind=args.kind,
                scalar_updates=scalar_updates,
                list_updates=list_updates,
                affected_documents=args.affected_documents or None,
            )
            if merge_missing:
                warnings.append(
                    "update 병합에서 다음 라벨 줄을 문서에서 찾지 못해 반영하지 못했다: "
                    + ", ".join(merge_missing)
                )
            existing_title_match = next(
                (re.match(rf"^# {re.escape(task_id)} — (.+)$", line.strip()) for line in existing_lines
                 if line.strip().startswith(f"# {task_id} — ")),
                None,
            )
            if existing_title_match and existing_title_match.group(1) != args.task_name:
                warnings.append(
                    f"task 제목이 기존과 다르다 (기존 유지): 기존 `{existing_title_match.group(1)}` / 입력 `{args.task_name}`."
                )
        else:
            draft_entry = build_draft_entry(
                task_id=task_id,
                task_name=args.task_name,
                status=status,
                priority=resolved_priority,
                request_date=request_date,
                owner=args.owner,
                host_name=args.host_name,
                host_ip=args.host_ip,
                affected_documents=args.affected_documents,
                task_summary=args.task_brief,
                progress_note=progress_note,
                done_criteria=args.done_criteria,
                result_note=result_note,
                next_step=args.next_step,
                risks=args.risks,
                follow_up=args.follow_up,
                validation_result=args.validation_result,
                kind=resolved_kind,
            )

        if operation_type == "create_daily_backlog":
            warnings.append("대상 날짜 backlog 파일이 없어 새 파일 초안 생성이 필요하다.")

        # v0.9.5 chapter 9 R-A follow-up part 2: skill context load integration
        # backlog-update 가 PURPOSE.md §3 Research Scope 와 비교하여 scope creep 경고
        from workflow_kit.common.paths import project_workspace_root
        from workflow_kit.common.schemas import BacklogUpdateOutput, BacklogUpdatePurposeContext

        workspace_root = project_workspace_root(project_profile_path)
        state_json_path = workflow_state_path(project_profile_path)
        purpose_context_data = build_purpose_context(
            workspace_root=workspace_root,
            state_path=state_json_path,
        )
        purpose_context_obj = BacklogUpdatePurposeContext(**purpose_context_data)
        warnings.extend(purpose_context_data.get("scope_warnings", []))

        # v0.11.0 chapter 11 R-A follow-up cycle 3: two-step CoT ingest
        from workflow_kit.common.purpose_ingest import run_two_step_cot_ingest
        from workflow_kit.common.schemas import BacklogUpdatePurposeCoTTrace

        cot_result = run_two_step_cot_ingest(workspace_root=workspace_root)
        purpose_cot_trace = BacklogUpdatePurposeCoTTrace(
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
        from workflow_kit.common.purpose_graph import run_graph_insights
        from workflow_kit.common.schemas import BacklogGraphInsightsOutput

        graph_result = run_graph_insights(workspace_root=workspace_root)
        graph_insights = BacklogGraphInsightsOutput(
            coverage_pct=(graph_result.coverage.coverage_pct if graph_result.coverage else 0.0),
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

        scope_creep_warnings = check_scope_creep(
            task_brief=args.task_brief,
            affected_documents=args.affected_documents,
            scope={
                "included": purpose_context_data.get("scope_included", []),
                "excluded": purpose_context_data.get("scope_excluded", []),
            },
        )

        index_update_note = None
        if operation_type == "create_daily_backlog":
            index_update_note = "새 날짜 backlog 파일이 생성되면 backlog index 에 링크를 추가해야 한다."

        handoff_update_note = None
        if status in {"in_progress", "blocked", "done"}:
            handoff_update_note = "상태 변화가 handoff 에 반영되어야 하는지 확인한다."
        state_cache_update = build_state_cache_refresh_hint(
            project_profile_path=project_profile_path,
            latest_backlog_path=daily_backlog_path,
        )
        apply_result = {
            "status": "skipped",
            "written_paths": [],
            "created_paths": [],
            "updated_paths": [],
            "warnings": [],
        }
        if args.apply and operation_type != "cannot_determine":
            # v0.11.20: backlog_write_failed error_code (4th stable error_code 정합)
            # apply 모드에서 파일 쓰기 실패 시 (permission denied / disk full /
            # read-only fs) 명시적 차단 + 원본 보존. silently skip ❌.
            try:
                backlog_action = upsert_backlog_entry(
                    backlog_path=daily_backlog_path,
                    task_id=task_id,
                    entry_lines=draft_entry,
                    title=args.task_name,
                    kind=resolved_kind,
                    status=status,
                    # update 병합 시 index block 도 보존 — status 줄만 바꾼다.
                    preserve_index_block=update_merge,
                )
                apply_result["written_paths"].append(str(daily_backlog_path))
                # v1.0.2: `upsert_backlog_entry` 는 daily index 와 **task SSOT 두 파일**을
                # 쓴다. 보고에는 index 만 실려 있어서, 호출자가 무엇이 쓰였는지 알 수
                # 없었다 (실측: 4개를 쓰고 2개만 보고). 쓴 것은 전부 보고한다.
                apply_result["written_paths"].append(str(task_ssot_path))
                if backlog_action == "created":
                    apply_result["created_paths"].append(str(daily_backlog_path))
                    apply_result["created_paths"].append(str(task_ssot_path))
                else:
                    apply_result["updated_paths"].append(str(daily_backlog_path))
                    apply_result["updated_paths"].append(str(task_ssot_path))
            except OSError as exc:
                result = build_error_result(
                    tool_version=TOOL_VERSION,
                    error="backlog 파일 쓰기에 실패했다.",
                    error_code="backlog_write_failed",
                    warnings=[
                        "대상 backlog 파일의 쓰기 권한과 디스크 상태를 점검한 뒤 다시 시도해야 한다.",
                        f"실패 경로: {daily_backlog_path}",
                    ],
                    source_context=source_context | {
                        "exception_type": type(exc).__name__,
                        "errno": getattr(exc, "errno", None),
                    },
                )
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 1

            if work_backlog_index_path.exists():
                index_added = ensure_backlog_index_entry(
                    work_backlog_index_path=work_backlog_index_path,
                    daily_backlog_path=daily_backlog_path,
                )
                apply_result["written_paths"].append(str(work_backlog_index_path))
                apply_result["updated_paths"].append(str(work_backlog_index_path))
                if index_added:
                    warnings.append("backlog index 에 새 날짜 backlog 링크를 자동 추가했다.")
            else:
                apply_result["warnings"].append("work_backlog.md 가 없어 backlog index 자동 갱신을 건너뛰었다.")

            if session_handoff_path.exists() and status in {"in_progress", "blocked", "done"}:
                sync_handoff_status(
                    handoff_path=session_handoff_path,
                    task_label=f"{task_id} {args.task_name}",
                    status=status,
                )
                apply_result["written_paths"].append(str(session_handoff_path))
                apply_result["updated_paths"].append(str(session_handoff_path))
            elif status in {"in_progress", "blocked", "done"}:
                apply_result["warnings"].append("session_handoff.md 가 없어 handoff 상태 동기화를 건너뛰었다.")

            apply_result["status"] = "applied"

        # v1.0.1 fix: state cache 재생성은 **write** 다. `--apply` 없이 부르면 초안만
        # 달라는 호출이 저장소에 파일을 만든다 (skill 의 권한 경계 §5 "초안 생성 중심"
        # 위반이자 dry-run 오염). draft 경로에서는 hint 만 내고 쓰지 않는다.
        if args.apply:
            state_cache_refresh = refresh_workflow_state_cache(
                project_profile_path=project_profile_path,
                session_handoff_path=session_handoff_path if session_handoff_path.exists() else None,
                work_backlog_index_path=work_backlog_index_path if work_backlog_index_path.exists() else None,
                latest_backlog_path=daily_backlog_path if daily_backlog_path.exists() else None,
                generated_at=date.today().isoformat(),
            )
            # v1.0.2: state cache 재생성도 **write** 다. 이 경로가 보고에 빠져 있어서,
            # state.json 이 갱신된(그리고 손상될 수 있는) 사실이 호출자에게 안 보였다.
            refreshed_state_path = state_cache_refresh.get("state_path")
            if state_cache_refresh.get("status") == "refreshed" and refreshed_state_path:
                apply_result["written_paths"].append(str(refreshed_state_path))
                apply_result["updated_paths"].append(str(refreshed_state_path))
        else:
            state_cache_refresh = {
                "status": "skipped",
                "state_path": state_cache_update["state_path"],
                "refresh_command": state_cache_update["refresh_command"],
                "missing_paths": [],
            }
        warnings.extend(apply_result["warnings"])

        from workflow_kit.common.schemas import BacklogUpdateOutput
        
        output_model = BacklogUpdateOutput(
            status="ok",
            tool_version=TOOL_VERSION,
            operation_type=operation_type,
            target_backlog_path=str(daily_backlog_path),
            task_id=task_id,
            task_found=bool(matched_task),
            draft_entry=draft_entry,
            status_recommendation={
                "value": status,
                "reason": (
                    "검증 결과가 없으므로 완료 확정 대신 보수적인 상태를 유지한다."
                    if status != "done" and args.status == "done"
                    else "입력된 상태와 현재 작업 브리핑 기준으로 가장 보수적인 상태를 제안한다."
                ),
            },
            fields_requiring_confirmation=fields_requiring_confirmation,
            warnings=warnings,
            index_update_note=index_update_note,
            handoff_update_note=handoff_update_note,
            state_cache_update_note=(
                f"`--apply` 반영 결과를 포함한 현재 source-of-truth 문서를 기준으로 `{state_cache_update['state_path']}` 를 자동 재생성했다."
                if args.apply and state_cache_refresh["status"] == "refreshed"
                else f"draft 모드라 `{state_cache_update['state_path']}` 를 쓰지 않았다 — 재생성하려면 `--apply` 또는 위 refresh command."
                if not args.apply
                else f"source-of-truth 문서가 아직 부족해 `{state_cache_update['state_path']}` 자동 재생성을 건너뛰었다."
            ),
            state_cache_refresh_command=state_cache_update["refresh_command"],
            state_cache_status=state_cache_refresh["status"],
            state_cache_missing_paths=state_cache_refresh["missing_paths"],
            apply_status=apply_result["status"],
            written_paths=apply_result["written_paths"],
            created_paths=apply_result["created_paths"],
            updated_paths=apply_result["updated_paths"],
            validation_note=args.validation_result,
            source_context={
                "project_profile_path": str(project_profile_path),
                "daily_backlog_exists": daily_backlog_path.exists(),
                "existing_task_count": len(existing_tasks),
            },
            purpose_context=purpose_context_obj,
            purpose_cot_trace=purpose_cot_trace,
            graph_insights=graph_insights,
            scope_creep_warnings=scope_creep_warnings,
            memory_index_query_output=_build_memory_index_query_output(
                args, workspace_root, warnings,
            ),
        )
        result = output_model.model_dump()
    except Exception as exc:
        result = build_error_result(
            tool_version=TOOL_VERSION,
            error="backlog-update 실행 중 예기치 않은 오류가 발생했다.",
            error_code="backlog_update_runtime_error",
            warnings=["입력 값과 backlog 파서 동작을 점검한 뒤 다시 실행해야 한다."],
            source_context=source_context | {"exception_type": type(exc).__name__},
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

        # v0.6.5: stage_completion merge (pilot template, batch 적용)
        result = merge_into_result(
            result,
            build_stage_completion(
                stage_name="backlog-update",
                stage_status="ok" if result.get("status") in ("ok", "success") else "warning" if result.get("status") == "warning" else "error",
                artifacts=["ai-workflow/memory/active/backlog/<target_date>.md"],
                next_stage=None,
                notes=[result.get("summary", "")[:200]] if result.get("summary") else [],
            ),
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
