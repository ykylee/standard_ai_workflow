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
from workflow_kit.common.planning import (
    DEMOTION_REVERTS_DONE,
    determine_conservative_task_status,
)
from workflow_kit.common.project_docs import (
    TASK_ID_CAPTURE_RE,
    parse_backlog_task_entries,
    is_empty_label_line,
    parse_project_profile_backlog,
    task_label,
    task_label_aliases,
)
from workflow_kit.common.purpose_context import build_purpose_context, check_scope_creep
from workflow_kit.common.workflow_state import build_state_cache_refresh_hint, refresh_workflow_state_cache
from workflow_kit.common.workflow_writes import (
    ensure_backlog_index_entry,
    merge_preserving_order,
    merge_task_file,
    read_task_affected_documents,
    read_task_list_field,
    render_task_file,
    sync_handoff_status,
    upsert_backlog_entry,
)

#: `--replace-field` 로 지정할 수 있는 **누적 성격** 필드들 (의미 key → 라벨 key).
#:
#: 이 필드들은 task 에 대한 *누적 사실*이다 — 완료 기준이 셋이면 셋 다 참이고,
#: 영향 문서가 넷이면 넷 다 영향받는다. 그래서 update 의 기본은 **병합**이다.
#: `Progress` · `Status` 처럼 *현재값*인 필드는 여기 없다 — 그쪽은 교체가 맞다.
#: 한 정책을 두 부류에 함께 쓴 것이 TASK-2026-08-31-main-003 의 뿌리였다.
CUMULATIVE_FIELDS: tuple[str, ...] = (
    "affected_documents",
    "done_criteria",
    "result",
    "risks",
    "follow_up",
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
    wbs: str | None = None,
    wbs_exempt_reason: str | None = None,
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
        _one(task_label("status"), status),
        _one(task_label("priority"), priority),
        f"- {task_label('request_date')}: {request_date}",
        _one(task_label("owner"), owner),
        _one(task_label("host_name"), host_name),
        _one(task_label("host_ip"), host_ip),
        f"- {task_label('affected_documents')}:",
    ]
    if affected_documents:
        detail.extend([f"  - `{doc}`" for doc in affected_documents])
    else:
        detail.append("  - ")
    detail.extend(
        [
            "",
            _one(task_label("summary"), task_summary),
            *_label_lines(task_label("done_criteria"), done_criteria),
            "",
            "## 🛠️ Implementation / Content",
            "",
            _one(task_label("progress"), progress_note),
            _one(task_label("next_step"), next_step),
            *_label_lines(task_label("risks"), risks),
            "",
            "## ✅ Outcome",
            "",
            *_label_lines(task_label("result"), result_note),
        ]
    )
    # v1.0.2: `--validation-result` 를 산출물에 싣는다. 이전에는 이 값이 *result_note 가
    # 비어 있을 때만* 그 자리를 대신했고, 둘 다 주면 **검증 결과가 조용히 버려졌다** —
    # `done` 판정의 근거가 되는 값인데 정작 task SSOT 어디에도 남지 않았다.
    if validation_result and validation_result not in _as_list(result_note):
        detail.append(f"- {task_label('validation')}: {validation_result}")
    detail.extend(_label_lines(task_label("follow_up"), follow_up))
    return render_task_file(
        task_id=task_id,
        title=task_name,
        status=status,
        created_at=request_date,
        kind=kind,
        source_anchor=source_anchor or f"{kind}-{task_id.lower()}",
        source_path=source_path or f"backlog/{request_date}.md",
        body_lines=detail,
        wbs=wbs,
        wbs_exempt_reason=wbs_exempt_reason,
    )


def _one(label: str, value: str | None) -> str:
    """`- <label>: <값>` 한 줄. 값이 없으면 빈 placeholder — 형식은 유지한다."""
    return f"- {label}: {value}" if value else f"- {label}:"


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
    """비어 있는 필드의 **라벨**을 돌려준다 — 이름은 정본 표에서만 가져온다.

    리터럴로 들고 있던 자리다. 라벨을 전환하면 문서는 새 표기로 적히는데 이
    보고만 옛 표기를 말해, 사용자가 문서에서 찾을 수 없는 이름을 듣는다.
    """
    # 입력 key → 정본 표의 의미 key. 이름이 다른 것만 옮긴다.
    mapping = {
        "owner": "owner",
        "host_name": "host_name",
        "host_ip": "host_ip",
        "affected_documents": "affected_documents",
        "done_criteria": "done_criteria",
        "result_note": "result",
        "next_step": "next_step",
        "risks": "risks",
        "follow_up": "follow_up",
    }
    missing: list[str] = []
    for key, label_key in mapping.items():
        value = data.get(key)
        if value is None or value == "" or value == []:
            missing.append(task_label(label_key))
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
    # v1.7.1: 스칼라 필드도 **반복 지정을 받아 놓고 거부**한다. 이전에는 argparse
    # 기본 동작으로 마지막 하나만 남아 나머지가 조용히 사라졌다 — 열거 필드는
    # v1.2.2 가 이 부류를 고쳤는데 이 둘이 빠져 있었다. 여기서 합치지 않는 이유:
    # `Progress` 는 **한 줄** 필드라 구분자를 도구가 지어내면 그것도 추측이다.
    # 못 쓴 것을 성공으로 보고하지 않되, 구조는 호출자가 정한다.
    parser.add_argument("--progress-note", action="append", dest="progress_note", default=[])
    # v1.2.2 (task SSOT 2단계): 열거형 필드는 **반복 지정**을 받는다.
    # 이전에는 마지막 하나만 남아, 값을 여러 개 주면 나머지가 **조용히 사라졌다**
    # (2026-08-14 실측: 5건을 적었는데 1건만 들어갔다). 개행을 끼워 넣는 우회책은
    # update 마다 줄을 중복시켰다 — 그 둘이 같은 뿌리다.
    parser.add_argument("--done-criteria", action="append", dest="done_criteria", default=[],
                        help="완료 기준 (반복 지정 가능)")
    parser.add_argument("--result-note", action="append", dest="result_note", default=[],
                        help="작업 결과 (반복 지정 가능)")
    parser.add_argument("--next-step", action="append", dest="next_step", default=[])
    parser.add_argument("--risks", action="append", dest="risks", default=[],
                        help="남은 리스크 (반복 지정 가능)")
    parser.add_argument("--follow-up", action="append", dest="follow_up", default=[],
                        help="후속 작업 (반복 지정 가능)")
    parser.add_argument("--validation-result")
    parser.add_argument("--replace-field", action="append", dest="replace_fields", default=[],
                        choices=CUMULATIVE_FIELDS,
                        help="update 에서 이 누적 필드를 병합하지 않고 **교체**한다 (반복 지정 가능). "
                             "기본은 병합 — 이전 세션이 적은 값을 지우려면 여기에 명시한다. "
                             f"지정 가능: {', '.join(CUMULATIVE_FIELDS)}")
    # ADR-027 M-004 (스펙 §6): roadmap 이 있는 프로젝트의 task 생성 게이트.
    parser.add_argument("--wbs", default=None,
                        help="WBS leaf 참조 'M-NNN/WBS-N.N', 또는 로드맵 밖 작업 선언 'exempt'. "
                             "roadmap 이 있는 프로젝트의 create 는 필수 (ADR-027 §6). "
                             "update 는 선택 — 지정 시 재링크(같은 게이트를 탄다), 미지정은 보존.")
    parser.add_argument("--wbs-exempt-reason", default=None,
                        help="--wbs exempt 의 필수 사유 — frontmatter 에 남아 생성물이 센다.")
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


def read_task_ssot_state(path: Path) -> tuple[str | None, str | None]:
    """task SSOT 파일에서 ``(status, 기록된 검증 결과)`` 를 읽는다.

    v1.8.2 (TASK-2026-09-01-main-003). 이 둘은 `determine_conservative_task_status`
    의 서로 다른 인자로 들어간다 — 상태는 "미지정이면 보존" 판정에, 기록된 검증은
    "이미 검증된 done 을 강등하지 않는다" 판정에 쓴다. 후자를 안 읽던 동안
    `--status done` 재호출이 완료 기록을 취소했다.

    검증 라벨은 **별칭까지** 받는다. 라벨을 리터럴 하나로 비교하다 영어 표기 문서에서
    조용히 빗나간 전례가 있다 (`project_docs.is_empty_label_line` 주석).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None, None
    status: str | None = None
    m = re.search(r"^status:\s*(\S+)", text, re.M)
    if m:
        status = m.group(1)
    alt = "|".join(re.escape(a) for a in task_label_aliases("validation"))
    v = re.search(rf"^-\s*(?:{alt})\s*:\s*(\S.*)$", text, re.M)
    recorded = v.group(1).strip() if v else None
    return status, (recorded or None)


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
                    # v1.2.1 (TASK-2026-08-16-main-001): 오늘 index 에 없다고 곧바로
                    # 포기하면 **날짜가 바뀔 때마다** 진행 중인 task 의 갱신이 사라진다.
                    # daily index 는 "그날 손댄 task" 의 목록이고 SSOT 는 `tasks/<id>.md`
                    # 다 — task 파일이 있으면 이건 미지의 ID 가 아니라 **이월**이다.
                    # 2회 연속 세션에서 밟았고, 두 번째에는 linter 의
                    # `task_status_mismatch` 를 거쳐 커밋 게이트를 세웠다.
                    ssot_probe = daily_backlog_path.parent / "tasks" / f"{args.task_id}.md"
                    if ssot_probe.is_file():
                        operation_type = "carry_over_entry"
                        warnings.append(
                            f"`{args.task_id}` 가 대상 backlog 에 없어 task SSOT 를 근거로 "
                            "이월 항목을 만든다 (날짜 롤오버)."
                        )
                    else:
                        operation_type = "cannot_determine"
                        warnings.append(
                            f"`{args.task_id}` 항목을 대상 backlog 에서 찾지 못했고 "
                            f"task SSOT (`{ssot_probe.name}`) 도 없다 — 갱신할 대상이 없다."
                        )

        task_id = args.task_id or suggest_next_task_id(
            existing_tasks, target_date=getattr(args, 'target_date', None))
        # v1.1.8 (TASK-2026-08-12-main-008): update 에서 --status 미지정이면 기존
        # 상태를 보존한다 — 미지정은 "바꾸지 말라" 다. 기존 상태는 task SSOT
        # frontmatter (`status: X`) 에서 읽는다.
        current_status: str | None = None
        # v1.8.2 (TASK-2026-09-01-main-003): **이미 기록된** 검증 결과도 함께 읽는다.
        # 이것이 없으면 `--status done` 재호출이 파일의 검증을 못 보고 강등하면서
        # 이미 기록된 완료를 취소한다 (실측: handoff §4 → §2 되돌림).
        # 라벨은 별칭까지 받는다 — 영어 표기 문서에서 리터럴 비교가 조용히 빗나간
        # 전례가 있다 (`project_docs.is_empty_label_line` 주석).
        recorded_validation: str | None = None
        _ssot_probe = daily_backlog_path.parent / "tasks" / f"{task_id}.md"
        if requested_mode == "update" and _ssot_probe.exists():
            current_status, recorded_validation = read_task_ssot_state(_ssot_probe)
        status, status_warnings = determine_conservative_task_status(
            args.status, args.validation_result, operation_type,
            current_status=current_status, recorded_validation=recorded_validation)
        warnings.extend(status_warnings)
        # 강등이 **이미 기록된 완료를 취소**했으면 그것은 성공이 아니다 —
        # `cannot_determine` 을 warning 으로 올린 v1.2.1 과 같은 처방.
        demotion_reverted_done = any(
            DEMOTION_REVERTS_DONE in w for w in status_warnings)

        # 스칼라 필드는 여러 번 받으면 **거부**한다 — 조용히 마지막만 쓰지 않는다.
        for flag, values in (("--progress-note", args.progress_note),
                             ("--next-step", args.next_step)):
            if len(values) > 1:
                raise SystemExit(
                    f"{flag} 를 {len(values)}번 지정했다. 이 필드는 한 줄이라 여러 값을 "
                    f"합칠 구분자를 도구가 정할 수 없다 — 하나로 합쳐서 넘긴다. "
                    f"받은 값: {values!r}"
                )
        progress_note = args.progress_note[0] if args.progress_note else None
        next_step = args.next_step[0] if args.next_step else None
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
            "next_step": next_step,
            "risks": args.risks,
            "follow_up": args.follow_up,
        }
        fields_requiring_confirmation = [normalize_backticked(item) for item in detect_confirmation_fields(fields_data)]

        resolved_kind = args.kind or "generic"
        resolved_priority = args.priority or "high"

        # ADR-027 M-004 (스펙 §6): roadmap 이 있는 프로젝트의 task **생성** 게이트.
        # 판정은 정본 한 곳(evaluate_wbs_gate)이고 MCP 경로도 같은 함수를 부른다.
        # draft(무-apply)도 막는다 — 거부될 초안을 보여 주는 것은 초안이 아니라 함정이다.
        # v1.6.1 (TASK-2026-08-28-main-002): **update 재링크도 같은 게이트를 탄다** —
        # 이전에는 update 가 --wbs 를 조용히 버려 재링크 수단이 없었고, 게이트 없이
        # 병합만 붙이면 dangling leaf / done 마일스톤 재링크가 무검증으로 뚫린다.
        # update 에서 --wbs 미지정은 "바꾸지 말라" 이므로 게이트 대상이 아니다.
        if requested_mode == "create" or (requested_mode == "update" and args.wbs):
            from workflow_kit.common.paths import project_workspace_root as _pwr
            from workflow_kit.common.state.roadmap import evaluate_wbs_gate

            gate = evaluate_wbs_gate(
                _pwr(project_profile_path),
                wbs=args.wbs,
                exempt_reason=args.wbs_exempt_reason,
            )
            if not gate.allowed:
                gate_action = "생성이" if requested_mode == "create" else "wbs 재링크가"
                result = build_error_result(
                    tool_version=TOOL_VERSION,
                    error=f"task {gate_action} 로드맵 게이트에 막혔다: {gate.detail}",
                    error_code="wbs_gate_denied",
                    warnings=[f"게이트 판정 코드: {gate.code}"],
                    source_context=source_context | {
                        "gate_code": gate.code,
                        "gate_milestone_id": gate.milestone_id,
                        "wbs": args.wbs,
                    },
                )
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 1
            if gate.code == "exempt_declared":
                warnings.append(f"로드맵 게이트 예외로 생성한다 — 사유: {args.wbs_exempt_reason}")

        # v1.1.7 (TASK-2026-08-11-main-023): update 모드는 재생성이 아니라 **병합**이다.
        # 기존 task SSOT 파일이 있으면 그것을 원본으로 삼고 명시된 값만 반영한다 —
        # 이전에는 인자만으로 문서를 다시 만들어 미지정 필드(작업 내용·완료 기준·담당·
        # kind)를 삭제했다 (실측: TASK-018 파일 손 복원). draft(무-apply)에도 병합
        # 결과를 보여 준다 — 쓸 내용과 보여 준 초안이 달라선 안 된다.
        task_ssot_path = daily_backlog_path.parent / "tasks" / f"{task_id}.md"
        update_merge = requested_mode == "update" and task_ssot_path.exists()

        if update_merge:
            existing_lines = task_ssot_path.read_text(encoding="utf-8").splitlines()
            scalar_updates: dict[str, str] = {task_label("progress"): progress_note}
            if args.priority:
                scalar_updates[task_label("priority")] = args.priority
            if args.owner:
                scalar_updates[task_label("owner")] = args.owner
            if args.host_name:
                scalar_updates[task_label("host_name")] = args.host_name
            if args.host_ip:
                scalar_updates[task_label("host_ip")] = args.host_ip
            list_updates: dict[str, list[str]] = {}
            if args.done_criteria:
                list_updates[task_label("done_criteria")] = _as_list(args.done_criteria)
            if result_note:
                list_updates[task_label("result")] = _as_list(result_note)
            if args.validation_result and args.validation_result != result_note:
                scalar_updates[task_label("validation")] = args.validation_result
            if next_step:
                scalar_updates[task_label("next_step")] = next_step
            if args.risks:
                list_updates[task_label("risks")] = _as_list(args.risks)
            if args.follow_up:
                list_updates[task_label("follow_up")] = _as_list(args.follow_up)
            # 작업 내용은 원문 보존이 원칙 — 비어 있을 때만 brief 로 채운다.
            if any(is_empty_label_line(line, "summary") for line in existing_lines):
                scalar_updates[task_label("summary")] = args.task_brief

            # --- 누적 필드 병합 (TASK-2026-08-31-main-003) ---------------------
            # `merge_task_file` 은 묶음을 **통째로 교체**하는 저수준 setter 다. 그
            # 아래에서 "무엇을 쓸 것인가" 를 정하는 것은 정책이고, 정책은 여기 산다.
            # 이전에는 정책이 없어 늘 교체였고, 이전 세션이 적은 완료 기준·영향
            # 문서가 **경고 한 줄 없이** 사라졌다 (실측 2026-08-31: 영향 문서 1건 +
            # 완료 기준 2건 소실). 기본은 병합, 교체는 `--replace-field` 로 명시한다.
            replace_fields = set(args.replace_fields or [])
            for field_key in CUMULATIVE_FIELDS:
                if field_key == "affected_documents":
                    continue
                label = task_label(field_key)
                if label not in list_updates:
                    continue
                previous = read_task_list_field(existing_lines, label)
                if field_key in replace_fields:
                    dropped = [v for v in previous if v not in list_updates[label]]
                    if dropped:
                        warnings.append(
                            f"--replace-field {field_key}: 기존 값 {len(dropped)}건을 "
                            f"교체로 버렸다 — {dropped}"
                        )
                    continue
                list_updates[label] = merge_preserving_order(previous, list_updates[label])

            merged_docs = args.affected_documents or None
            if args.affected_documents:
                previous_docs = read_task_affected_documents(existing_lines)
                if "affected_documents" in replace_fields:
                    dropped_docs = [d for d in previous_docs
                                    if d not in args.affected_documents]
                    if dropped_docs:
                        warnings.append(
                            f"--replace-field affected_documents: 기존 값 "
                            f"{len(dropped_docs)}건을 교체로 버렸다 — {dropped_docs}"
                        )
                else:
                    merged_docs = merge_preserving_order(previous_docs, args.affected_documents)

            draft_entry, merge_missing = merge_task_file(
                existing_lines,
                status=status,
                kind=args.kind,
                scalar_updates=scalar_updates,
                list_updates=list_updates,
                affected_documents=merged_docs,
                wbs=args.wbs,
                wbs_exempt_reason=args.wbs_exempt_reason,
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
                next_step=next_step,
                risks=args.risks,
                follow_up=args.follow_up,
                validation_result=args.validation_result,
                kind=resolved_kind,
                wbs=args.wbs,
                wbs_exempt_reason=args.wbs_exempt_reason,
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
            # v1.2.1 (TASK-2026-08-16-main-001): `cannot_determine` 은 성공이 아니다.
            # 예전에는 apply 를 통째로 스킵하고도 최상위 `status` 가 `ok` 라, 호출자가
            # "갱신됐다" 고 읽었다 — 조용한 미반영. 아무것도 안 썼으면 그렇게 말한다.
            #
            # v1.8.2 (TASK-2026-09-01-main-003): **이미 기록된 완료를 취소한 강등**도
            # 같은 부류다. 그것은 요청대로 된 것이 아니라 요청을 되돌린 것이고,
            # 실제로 그 상태 그대로 커밋·push 된 적이 있다 (`12b9f311`).
            status=(
                "warning"
                if operation_type == "cannot_determine" or demotion_reverted_done
                else "ok"
            ),
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
