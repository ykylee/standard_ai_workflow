"""workflow_kit.common.dashboard_data - Quality Dashboard 5-panel data collector (v0.13.0).

Phase 13 (Operational Intelligence v1.0) 의 sub-milestone v0.13.0 첫 deliverable.
본 모듈은 *read-only* — 5 panel 의 운영 metric 을 단일 dict 로 수집하여
``workflow_kit_cli --command=dashboard --format=json`` 으로 노출한다.

Panel 구성 (ai-workflow/wiki/topics/quality-dashboard-implementation-guide.md §2 정합):
    1. drift_prevention: drift guard 6 case PASS/FAIL + last_updated delta + smoke count
    2. maturity_distribution: skill / mcp_tools stage 분포 (stable / beta / alpha)
    3. memory_index_utilization: entries 갯수 + cue_anchor frequency + cumulative timeline
    4. smoke_trend: 누적 smoke count + 최근 release 의 smoke fail 갯수
    5. recent_releases: state.json.session.recent_done_items 시각화용 timeline

Acceptance criteria (구현 가이드 §4 정합):
    AC1: collect_dashboard_snapshot 가 5 panel 의 data 를 1 dict 로 emit
    AC2: 5 panel 모두 *실제 data* (fixture 아님) 기반
    AC3: release --apply 시 자동 emit (v0.13.1 sub-milestone — 본 모듈은 read-only 만)
    AC4: snapshot 의 last_updated ≤ release commit date (data freshness)

Public API:
    collect_dashboard_snapshot(workspace_root) -> dict[str, Any]
    render_dashboard_markdown(snapshot) -> str  (v0.13.0 무료 옵션; v0.13.1 release hook 의 preview)

본 모듈은 Pydantic schema 를 사용하지 않고 plain dict 를 emit 한다.
이유: dashboard 의 consumer (release note, wiki, dashboard HTML) 가 *schema-validation
없이 자유롭게 field 추가 / 소비* 할 수 있도록. Pydantic schema 가 필요한 경우
``workflow_kit.common.schemas.dashboard`` (후속 release) 로 분리.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Release note 의 누적 smoke count 패턴 (Beta-v0.11.25.md §검증 정합).
# 형식: "누적 smoke test **40/40 PASS**" 또는 "누적 ... smoke ... **N/N PASS**"
SMOKE_COUNT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"누적\s+smoke\s+test\s+\*\*(\d+)/(\d+)\s+PASS\*\*"
)

# smoke_trend panel 의 default release note top-N
DEFAULT_RECENT_RELEASES: Final[int] = 10

# drift_prevention panel 의 expected guard case 갯수 (v0.11.23 cycle 4-layer, v0.11.25 6/6 정합)
EXPECTED_DRIFT_GUARD_CASES: Final[int] = 6

# smoke_trend panel 의 minimal panel value (v0.11.25 cycle 의 누적 smoke 정합)
MIN_EXPECTED_SMOKE: Final[int] = 1

# drift prevention smoke 의 출력 line pattern (check_drift_prevention_v0_11_23.py §main 정합).
DRIFT_GUARD_PASS_LINE: Final[re.Pattern[str]] = re.compile(r"^\s*PASS:\s*(\S+)\s*$")
DRIFT_GUARD_FAIL_LINE: Final[re.Pattern[str]] = re.compile(r"^\s*FAIL:\s*(\S+)\s*$")
DRIFT_GUARD_SUMMARY: Final[re.Pattern[str]] = re.compile(
    r"===\s*(PASS|FAIL):\s*(\d+)/(\d+)\s*==="
)
# drift smoke 의 inline 실행 timeout (default: 30초 — git log + 6 case subprocess 호출)
DRIFT_GUARD_INLINE_TIMEOUT: Final[int] = 30


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _repo_root(workspace_root: Path | str | None) -> Path:
    """workspace_root 가 주어지지 않으면 REPO 부모 디렉토리로 fallback.

    표준화 정공법: caller 가 명시한 workspace_root 가 우선 (테스트 용이성).
    caller 가 미지정 시 ``workflow-source`` 의 부모 디렉토리 (REPO_ROOT) 를 반환.
    str path 도 허용 (test caller 용이성).

    Args:
        workspace_root: REPO_ROOT (Path) / git repo root 또는 "string path" / None.
    """
    if isinstance(workspace_root, str):
        candidate: Path | None = Path(workspace_root)
    elif workspace_root is None:
        candidate = None
    else:
        candidate = workspace_root
    if candidate is not None:
        return candidate
    # workflow-source/workflow_kit/common/dashboard_data.py → 4 단계 위 = REPO_ROOT
    return Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# Panel 1 — Drift Prevention Status
# ---------------------------------------------------------------------------


def collect_drift_prevention(
    workspace_root: Path,
    *,
    inline_guard: bool = True,
) -> dict[str, Any]:
    """drift prevention guard 의 현재 상태를 1 dict 로 emit.

    Args:
        workspace_root: REPO_ROOT or subdir
        inline_guard: True (default) 면 drift smoke 를 subprocess 로 호출하여
            ``guard_status`` 를 ``'pass' | 'fail' | 'error'`` 로 emit.
            False 면 ``guard_status = 'unknown'`` (legacy v0.13.0 behavior).

    Fields:
        guard_status: 'pass' | 'fail' | 'error' | 'unknown' (inline 실행 결과)
        guard_cases_pass: pass 한 case 갯수 (inline 실행 시)
        guard_cases_fail: fail 한 case 갯수 (inline 실행 시)
        guard_cases: 총 guard case 갯수 (expected = 6)
        expected_cases: EXPECTED_DRIFT_GUARD_CASES 정합
        guard_failure_names: fail case 의 name list (drift 발생 시)
        guard_executed_at: inline 실행 timestamp (ISO 8601)
        guard_runtime_ms: inline 실행 소요 시간 (ms)
        maturity_last_updated: maturity_matrix.json 의 last_updated (ISO date)
        maturity_last_updated_source: 'maturity_matrix.json'
        harness_supported_count: harness.supported 리스트 길이
        head_commit_date: HEAD commit 의 ISO date (subprocess git log -1)
        last_updated_delta_days: maturity_last_updated ↔ head_commit_date 의 일수 차이
        silent_failing_cycles_count: Phase 13 AC1 의 north-star metric (현 release 까지 0)

    Returns:
        dict — Panel 1 의 data shape. field 누락 시 *unknown* marker 사용.
    """
    root = _repo_root(workspace_root)
    maturity_path = root / "workflow-source" / "core" / "maturity_matrix.json"

    maturity_last_updated = ""
    harness_supported_count = 0
    if maturity_path.is_file():
        try:
            with maturity_path.open("r", encoding="utf-8") as fp:
                mm = json.load(fp)
            maturity_last_updated = str(mm.get("last_updated", ""))
            harnesses_obj = mm.get("harnesses", {})
            if isinstance(harnesses_obj, dict):
                supported = harnesses_obj.get("supported", [])
                if isinstance(supported, list):
                    harness_supported_count = len(supported)
        except (OSError, json.JSONDecodeError):
            # silent fallback — unknown marker 로 emit
            pass

    head_commit_date = _head_commit_date(root)
    last_updated_delta_days = _date_diff_days(maturity_last_updated, head_commit_date)

    guard_panel: dict[str, Any] = {
        "guard_status": "unknown",
        "guard_cases_pass": 0,
        "guard_cases_fail": 0,
        "guard_cases": EXPECTED_DRIFT_GUARD_CASES,
        "expected_cases": EXPECTED_DRIFT_GUARD_CASES,
        "guard_failure_names": [],
        "guard_executed_at": "",
        "guard_runtime_ms": 0,
    }
    if inline_guard:
        guard_result = run_drift_prevention_guard_inline(root)
        guard_panel.update(guard_result)

    return {
        **guard_panel,
        "maturity_last_updated": maturity_last_updated,
        "maturity_last_updated_source": "maturity_matrix.json",
        "harness_supported_count": harness_supported_count,
        "head_commit_date": head_commit_date,
        "last_updated_delta_days": last_updated_delta_days,
        "silent_failing_cycles_count": 0,  # Phase 13 AC1 north-star — release note 후속 parse
        "phase": "Phase 12 (in_progress) → Phase 13 (planned)",
    }


def run_drift_prevention_guard_inline(
    workspace_root: Path,
    *,
    timeout: int = DRIFT_GUARD_INLINE_TIMEOUT,
) -> dict[str, Any]:
    """drift prevention smoke 를 subprocess 로 inline 실행.

    check_drift_prevention_v0_11_23.py 의 main() 을 호출하여 6 case 의
    PASS/FAIL 을 parse. 결과는 dict 로 반환.

    Args:
        workspace_root: REPO_ROOT (git 작업 dir)
        timeout: subprocess timeout (default 30초)

    Returns:
        dict with fields:
            guard_status: 'pass' | 'fail' | 'error'
            guard_cases_pass: int
            guard_cases_fail: int
            guard_cases: int (total pass + fail)
            guard_failure_names: list[str]
            guard_executed_at: ISO 8601 timestamp
            guard_runtime_ms: int (milliseconds)
    """
    root = _repo_root(Path(workspace_root) if isinstance(workspace_root, str) else workspace_root)
    smoke_path = root / "workflow-source" / "tests" / "check_drift_prevention_v0_11_23.py"
    fallback: dict[str, Any] = {
        "guard_status": "error",
        "guard_cases_pass": 0,
        "guard_cases_fail": 0,
        "guard_cases": 0,
        "guard_failure_names": [],
        "guard_executed_at": _utcnow_iso(),
        "guard_runtime_ms": 0,
    }

    if not smoke_path.is_file():
        return fallback

    import time

    started = time.monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, str(smoke_path)],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        runtime_ms = int((time.monotonic() - started) * 1000)
        stdout = completed.stdout or ""
        cases_pass: list[str] = []
        cases_fail: list[str] = []
        summary_pass = 0
        summary_total = 0

        for line in stdout.splitlines():
            m_pass = DRIFT_GUARD_PASS_LINE.match(line)
            if m_pass is not None:
                cases_pass.append(m_pass.group(1))
                continue
            m_fail = DRIFT_GUARD_FAIL_LINE.match(line)
            if m_fail is not None:
                cases_fail.append(m_fail.group(1))
                continue
            m_sum = DRIFT_GUARD_SUMMARY.search(line)
            if m_sum is not None:
                # m_sum.group(1) = 'PASS' or 'FAIL', (2) = pass count, (3) = total
                try:
                    summary_pass = int(m_sum.group(2))
                    summary_total = int(m_sum.group(3))
                except ValueError:
                    pass

        # rc 가 0 이고 fail case 없으면 'pass', 그 외 'fail'. 예외 상황이면 'error'.
        if completed.returncode == 0 and not cases_fail:
            status = "pass"
        elif completed.returncode != 0 and not cases_fail and not cases_pass:
            # subprocess 자체가 fail (e.g. import error)
            status = "error"
        else:
            status = "fail"

        return {
            "guard_status": status,
            "guard_cases_pass": len(cases_pass) if cases_pass else summary_pass,
            "guard_cases_fail": len(cases_fail),
            "guard_cases": (len(cases_pass) + len(cases_fail)) or summary_total,
            "guard_failure_names": cases_fail,
            "guard_executed_at": _utcnow_iso(),
            "guard_runtime_ms": runtime_ms,
        }
    except subprocess.TimeoutExpired:
        runtime_ms = int((time.monotonic() - started) * 1000)
        return {
            "guard_status": "error",
            "guard_cases_pass": 0,
            "guard_cases_fail": 0,
            "guard_cases": 0,
            "guard_failure_names": [],
            "guard_executed_at": _utcnow_iso(),
            "guard_runtime_ms": runtime_ms,
        }
    except (OSError, ValueError):
        return fallback


def _head_commit_date(workspace_root: Path) -> str:
    """HEAD commit 의 ISO date (YYYY-MM-DD) 를 반환. git 실패 시 empty string."""
    try:
        completed = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=short"],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if completed.returncode == 0:
            return completed.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ""


def _date_diff_days(date_a: str, date_b: str) -> int | None:
    """두 ISO date (YYYY-MM-DD) 사이의 일수 차이. 한쪽이라도 invalid 면 None."""
    if not date_a or not date_b:
        return None
    try:
        d_a = datetime.strptime(date_a, "%Y-%m-%d").date()
        d_b = datetime.strptime(date_b, "%Y-%m-%d").date()
        return abs((d_b - d_a).days)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Panel 2 — Skill + MCP Maturity Distribution
# ---------------------------------------------------------------------------


def collect_maturity_distribution(workspace_root: Path) -> dict[str, Any]:
    """skill + mcp_tools 의 stage 분포를 1 dict 로 emit.

    Fields:
        skills: {
            "total": int,
            "stable": int, "beta": int, "alpha": int, "prototype": int,
            "by_stage": {stage: count, ...},
        }
        mcp_tools: {same shape}
        transports: {transport_name: stage, ...}
        harnesses: {
            "supported": int,
            "supported_names": [str, ...],
        }
        milestones: {
            "total": int,
            "done": int, "in_progress": int, "planned": int,
            "by_status": {status: count, ...},
        }
    """
    root = _repo_root(workspace_root)
    maturity_path = root / "workflow-source" / "core" / "maturity_matrix.json"

    if not maturity_path.is_file():
        return _empty_maturity_distribution()

    try:
        with maturity_path.open("r", encoding="utf-8") as fp:
            mm = json.load(fp)
    except (OSError, json.JSONDecodeError):
        return _empty_maturity_distribution()

    return {
        "skills": _stage_distribution(mm.get("skills", {})),
        "mcp_tools": _stage_distribution(mm.get("mcp_tools", {})),
        "transports": _transport_distribution(mm.get("transports", {})),
        "harnesses": _harness_distribution(mm.get("harnesses", {})),
        "milestones": _milestone_distribution(mm.get("milestones", {})),
    }


def _stage_distribution(items: dict[str, Any]) -> dict[str, Any]:
    """skill / mcp_tools 의 stage 분포 집계."""
    stages: Counter[str] = Counter()
    if isinstance(items, dict):
        for value in items.values():
            if isinstance(value, dict):
                stage = value.get("stage", "unknown")
                stages[str(stage)] += 1
    total = sum(stages.values())
    return {
        "total": total,
        "stable": stages.get("stable", 0),
        "beta": stages.get("beta", 0),
        "alpha": stages.get("alpha", 0),
        "prototype": stages.get("prototype", 0),
        "by_stage": dict(stages),
    }


def _transport_distribution(transports: Any) -> dict[str, Any]:
    """transports 의 name → stage 매핑."""
    if not isinstance(transports, dict):
        return {}
    out: dict[str, str] = {}
    for name, value in transports.items():
        if isinstance(value, dict):
            out[str(name)] = str(value.get("stage", "unknown"))
        else:
            out[str(name)] = str(value)
    return out


def _harness_distribution(harnesses: Any) -> dict[str, Any]:
    """harness.supported 의 count + names."""
    if not isinstance(harnesses, dict):
        return {"supported": 0, "supported_names": []}
    supported = harnesses.get("supported", [])
    if not isinstance(supported, list):
        return {"supported": 0, "supported_names": []}
    return {
        "supported": len(supported),
        "supported_names": [str(name) for name in supported],
    }


def _milestone_distribution(milestones: Any) -> dict[str, Any]:
    """milestones 의 status 분포."""
    statuses: Counter[str] = Counter()
    if isinstance(milestones, dict):
        for value in milestones.values():
            if isinstance(value, dict):
                status = value.get("status", "unknown")
                statuses[str(status)] += 1
    total = sum(statuses.values())
    return {
        "total": total,
        "done": statuses.get("done", 0),
        "in_progress": statuses.get("in_progress", 0),
        "planned": statuses.get("planned", 0),
        "by_status": dict(statuses),
    }


def _empty_maturity_distribution() -> dict[str, Any]:
    """maturity_matrix.json 부재 / parse 실패 시 fallback."""
    empty_stage: dict[str, Any] = {
        "total": 0,
        "stable": 0,
        "beta": 0,
        "alpha": 0,
        "prototype": 0,
        "by_stage": {},
    }
    return {
        "skills": dict(empty_stage),
        "mcp_tools": dict(empty_stage),
        "transports": {},
        "harnesses": {"supported": 0, "supported_names": []},
        "milestones": {
            "total": 0,
            "done": 0,
            "in_progress": 0,
            "planned": 0,
            "by_status": {},
        },
    }


# ---------------------------------------------------------------------------
# Panel 3 — Memory Index Utilization
# ---------------------------------------------------------------------------


def collect_memory_index_utilization(workspace_root: Path) -> dict[str, Any]:
    """memory_index 의 활용도 metric 을 1 dict 로 emit.

    Fields:
        entries_total: 전체 entry 갯수
        entries_by_merge_state: {merge_state: count, ...}
        cue_anchors_top: [{anchor: str, count: int}, ...] 상위 20
        cue_anchors_unique: unique anchor 갯수
        cumulative_timeline: [{date: 'YYYY-MM-DD', count: int}, ...]
        first_entry_date / last_entry_date: ISO date
        retrieval_hit_rate: Phase 13 AC2 의 hit rate (telemetry events.jsonl 집계)
        retrieval_hit_rate_source: 'memory_index_telemetry_v0_13_1'
        telemetry: {total_calls, total_hits, by_source, events_parsed, events_skipped,
                    first_event_at, last_event_at} — Phase 13 AC2 telemetry sidecar 집계

    Returns:
        dict — Panel 3 의 data shape.
    """
    root = _repo_root(workspace_root)
    memory_index_dir = root / "ai-workflow" / "memory" / "active" / "memory_index"
    entries_dir = memory_index_dir / "entries"

    if not entries_dir.is_dir():
        payload = _empty_memory_index_utilization()
        _attach_telemetry_summary(root, payload)
        return payload

    entry_files = sorted(entries_dir.glob("MEM-*.json"))
    if not entry_files:
        payload = _empty_memory_index_utilization()
        _attach_telemetry_summary(root, payload)
        return payload

    entries: list[dict[str, Any]] = []
    for entry_path in entry_files:
        try:
            with entry_path.open("r", encoding="utf-8") as fp:
                entry = json.load(fp)
            if isinstance(entry, dict):
                entries.append(entry)
        except (OSError, json.JSONDecodeError):
            continue

    payload = _aggregate_memory_index(entries)
    _attach_telemetry_summary(root, payload)
    return payload


def _attach_telemetry_summary(workspace_root: Path, payload: dict[str, Any]) -> None:
    """Panel 3 payload 에 telemetry sidecar 집계 attach (in-place mutation).

    v0.13.1+ Phase 13 AC2 정합: telemetry 부재 시에도 payload 는 *graceful* —
    `telemetry.total_calls=0` + `retrieval_hit_rate=0.0` 유지 (placeholder 와 동일).
    caller 는 `telemetry.source_version` 으로 fallback 구분 가능.
    """
    try:
        from workflow_kit.common.state.memory_index import summarize_telemetry
    except ImportError:
        return
    try:
        summary = summarize_telemetry(workspace_root)
    except Exception:
        return
    payload["retrieval_hit_rate"] = summary.hit_rate
    payload["retrieval_hit_rate_source"] = summary.source_version
    payload["telemetry"] = {
        "total_calls": summary.total_calls,
        "total_hits": summary.total_hits,
        "by_source": summary.by_source,
        "events_parsed": summary.events_parsed,
        "events_skipped": summary.events_skipped,
        "first_event_at": summary.first_event_at,
        "last_event_at": summary.last_event_at,
    }


def _empty_memory_index_utilization() -> dict[str, Any]:
    """memory_index 부재 / parse 실패 시 fallback."""
    return {
        "entries_total": 0,
        "entries_by_merge_state": {},
        "cue_anchors_top": [],
        "cue_anchors_unique": 0,
        "cumulative_timeline": [],
        "first_entry_date": "",
        "last_entry_date": "",
        "retrieval_hit_rate": 0.0,
        "retrieval_hit_rate_source": "memory_index_telemetry_v0_13_1",
        "telemetry": {
            "total_calls": 0,
            "total_hits": 0,
            "by_source": {},
            "events_parsed": 0,
            "events_skipped": 0,
            "first_event_at": "",
            "last_event_at": "",
        },
    }


def _aggregate_memory_index(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """entry list 를 Panel 3 의 dict shape 로 집계."""
    states: Counter[str] = Counter()
    anchor_counter: Counter[str] = Counter()
    by_date: Counter[str] = Counter()
    first_date = ""
    last_date = ""

    for entry in entries:
        merge_state = str(entry.get("merge_state", "unknown"))
        states[merge_state] += 1

        anchors = entry.get("cue_anchors", [])
        if isinstance(anchors, list):
            for a in anchors:
                anchor_counter[str(a)] += 1

        created_at = str(entry.get("created_at", ""))
        # ISO 8601 'YYYY-MM-DDTHH:MM:SSZ' 의 date 부분만 추출
        date_part = created_at[:10] if len(created_at) >= 10 else ""
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_part):
            by_date[date_part] += 1
            if not first_date or date_part < first_date:
                first_date = date_part
            if date_part > last_date:
                last_date = date_part

    # 누적 timeline — 날짜 오름차순
    cumulative: list[dict[str, Any]] = []
    running = 0
    for date in sorted(by_date.keys()):
        running += by_date[date]
        cumulative.append({"date": date, "count": running})

    # top 20 cue_anchors
    top_anchors = [
        {"anchor": anchor, "count": count}
        for anchor, count in anchor_counter.most_common(20)
    ]

    return {
        "entries_total": len(entries),
        "entries_by_merge_state": dict(states),
        "cue_anchors_top": top_anchors,
        "cue_anchors_unique": len(anchor_counter),
        "cumulative_timeline": cumulative,
        "first_entry_date": first_date,
        "last_entry_date": last_date,
        "retrieval_hit_rate": 0.0,  # Phase 13 AC2 telemetry 후속 (collect_memory_index_utilization 의 post-hook 가 덮어씀)
        "retrieval_hit_rate_source": "memory_index_telemetry_v0_13_1",
    }


# ---------------------------------------------------------------------------
# Panel 4 — Smoke Trend
# ---------------------------------------------------------------------------


def collect_smoke_trend(
    workspace_root: Path,
    *,
    recent_limit: int = 5,
) -> dict[str, Any]:
    """누적 smoke test 추세를 release note 에서 parse.

    Fields:
        cumulative_total: 가장 최근 release note 의 누적 smoke total (정수)
        cumulative_pass: 가장 최근 release note 의 누적 smoke pass (정수)
        cumulative_pass_rate: pass / total (0.0 ~ 1.0)
        recent_releases: [{version: str, pass: int, total: int, release_note_path: str}, ...]
        smoke_files_count: workflow-source/tests/check_*.py 의 실제 file 갯수 (cross-check)

    Returns:
        dict — Panel 4 의 data shape.
    """
    root = _repo_root(workspace_root)
    releases_dir = root / "workflow-source" / "releases"
    tests_dir = root / "workflow-source" / "tests"

    smoke_files_count = 0
    if tests_dir.is_dir():
        smoke_files_count = sum(1 for _ in tests_dir.glob("check_*.py"))

    recent: list[dict[str, Any]] = []
    if not releases_dir.is_dir():
        return {
            "cumulative_total": 0,
            "cumulative_pass": 0,
            "cumulative_pass_rate": 0.0,
            "recent_releases": [],
            "smoke_files_count": smoke_files_count,
        }

    # Beta-v0.*.md 만 대상 (prototype-v1 / prototype-v2 제외).
    # semver-natural sort — Beta-v0.9.6 이 Beta-v0.10.0 보다 "newer" 로 잘못 분류되는
    # lexicographic sort 함정 회피.
    release_files = sorted(
        releases_dir.glob("Beta-v*.md"),
        key=_release_version_key,
        reverse=True,  # newest first
    )

    for rf in release_files[:recent_limit]:
        parsed = _parse_smoke_count_from_release(rf)
        if parsed is not None:
            smoke_pass, smoke_total = parsed
            recent.append(
                {
                    "version": rf.stem,  # 'Beta-v0.11.25'
                    "pass": smoke_pass,
                    "total": smoke_total,
                    "release_note_path": str(rf.relative_to(root)),
                }
            )

    # 가장 최근 (첫 번째) entry 의 pass/total
    if recent:
        latest = recent[0]
        return {
            "cumulative_total": int(latest["total"]),
            "cumulative_pass": int(latest["pass"]),
            "cumulative_pass_rate": (
                int(latest["pass"]) / int(latest["total"])
                if int(latest["total"]) > 0
                else 0.0
            ),
            "recent_releases": recent,
            "smoke_files_count": smoke_files_count,
        }

    # parse 실패 또는 release note 부재
    return {
        "cumulative_total": 0,
        "cumulative_pass": 0,
        "cumulative_pass_rate": 0.0,
        "recent_releases": recent,
        "smoke_files_count": smoke_files_count,
    }


def _parse_smoke_count_from_release(release_path: Path) -> tuple[int, int] | None:
    """release note 본문에서 '누적 smoke test **N/N PASS**' 패턴 parse."""
    try:
        with release_path.open("r", encoding="utf-8") as fp:
            content = fp.read()
    except OSError:
        return None
    match = SMOKE_COUNT_PATTERN.search(content)
    if match is None:
        return None
    try:
        return int(match.group(1)), int(match.group(2))
    except ValueError:
        return None


_VERSION_PATTERN: Final[re.Pattern[str]] = re.compile(r"v(\d+(?:\.\d+)*)")


def _release_version_key(path: Path) -> tuple[int, ...]:
    """release note 의 version 을 semver-natural sort key 로 변환.

    ``Beta-v0.9.6.md`` → (0, 9, 6), ``Beta-v0.10.0.md`` → (0, 10, 0).
    lexicographic sort 의 함정 (예: ``Beta-v0.9.x`` > ``Beta-v0.10.x``) 회피.
    """
    match = _VERSION_PATTERN.search(path.name)
    if match is None:
        return (0,)
    try:
        return tuple(int(part) for part in match.group(1).split("."))
    except ValueError:
        return (0,)


# ---------------------------------------------------------------------------
# Panel 5 — Recent Release Cycle
# ---------------------------------------------------------------------------


def collect_recent_releases(
    workspace_root: Path,
    *,
    top_n: int = DEFAULT_RECENT_RELEASES,
) -> dict[str, Any]:
    """state.json.session.recent_done_items 의 상위 N 개 item 을 timeline 으로 emit.

    Fields:
        items_total: recent_done_items 전체 갯수
        top_n: emit 한 item 갯수 (default = 10)
        timeline: [{index: int, preview: str (≤120 char), length: int}, ...]

    Returns:
        dict — Panel 5 의 data shape.
    """
    root = _repo_root(workspace_root)
    state_path = root / "ai-workflow" / "memory" / "active" / "state.json"

    if not state_path.is_file():
        return {"items_total": 0, "top_n": top_n, "timeline": []}

    try:
        with state_path.open("r", encoding="utf-8") as fp:
            state = json.load(fp)
    except (OSError, json.JSONDecodeError):
        return {"items_total": 0, "top_n": top_n, "timeline": []}

    session = state.get("session", {})
    if not isinstance(session, dict):
        return {"items_total": 0, "top_n": top_n, "timeline": []}

    items = session.get("recent_done_items", [])
    if not isinstance(items, list):
        return {"items_total": 0, "top_n": top_n, "timeline": []}

    timeline: list[dict[str, Any]] = []
    for idx, item in enumerate(items[:top_n]):
        if isinstance(item, str):
            preview = item[:120] + ("…" if len(item) > 120 else "")
            timeline.append(
                {
                    "index": idx,
                    "preview": preview,
                    "length": len(item),
                }
            )

    return {
        "items_total": len(items),
        "top_n": top_n,
        "timeline": timeline,
    }


# ---------------------------------------------------------------------------
# Aggregator — 5 panel snapshot
# ---------------------------------------------------------------------------


def collect_dashboard_snapshot(
    workspace_root: Path | None = None,
    *,
    inline_guard: bool = True,
) -> dict[str, Any]:
    """5 panel 의 data 를 1 dict 로 집계. read-only, atomic.

    Args:
        workspace_root: REPO_ROOT (None 이면 자동 탐색)
        inline_guard: True 면 Panel 1 의 drift guard 를 subprocess 로 inline 실행.
            False 면 legacy v0.13.0 behavior (guard_status='unknown').
    """
    ws_root = _repo_root(workspace_root) if workspace_root is None else workspace_root
    return {
        "schema_version": "1.0",
        "tool_version": _workflow_kit_version(),
        "generated_at": _utcnow_iso(),
        "workspace_root": str(ws_root),
        "panels": {
            "drift_prevention": collect_drift_prevention(ws_root, inline_guard=inline_guard),
            "maturity_distribution": collect_maturity_distribution(ws_root),
            "memory_index_utilization": collect_memory_index_utilization(ws_root),
            "smoke_trend": collect_smoke_trend(ws_root),
            "recent_releases": collect_recent_releases(ws_root),
        },
    }


def _workflow_kit_version() -> str:
    """workflow_kit.__version__ 의 loud fallback (ADR-003 read-only 정책 정합)."""
    try:
        from workflow_kit import __version__ as _V
        return str(_V)
    except ImportError:  # pragma: no cover
        return "v0.11.22-beta"


def _utcnow_iso() -> str:
    """UTC ISO 8601 timestamp (e.g. '2026-07-09T01:30:00Z')."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Renderer — Markdown output (v0.13.0 무료 옵션)
# ---------------------------------------------------------------------------


def render_dashboard_markdown(snapshot: dict[str, Any]) -> str:
    """snapshot dict 를 markdown 표 형식으로 직렬화.

    v0.13.1 release hook 의 preview / Phase 13 wiki 자동 emit 의 자유 옵션.
    """
    lines: list[str] = []
    lines.append("# Quality Dashboard Snapshot")
    lines.append("")
    lines.append(f"- generated_at: `{snapshot.get('generated_at', '')}`")
    lines.append(f"- tool_version: `{snapshot.get('tool_version', '')}`")
    lines.append(f"- workspace_root: `{snapshot.get('workspace_root', '')}`")
    lines.append("")
    panels = snapshot.get("panels", {})
    if isinstance(panels, dict):
        lines.extend(_render_panel_1(panels.get("drift_prevention", {})))
        lines.extend(_render_panel_2(panels.get("maturity_distribution", {})))
        lines.extend(_render_panel_3(panels.get("memory_index_utilization", {})))
        lines.extend(_render_panel_4(panels.get("smoke_trend", {})))
        lines.extend(_render_panel_5(panels.get("recent_releases", {})))
    return "\n".join(lines) + "\n"


def _render_panel_1(p: dict[str, Any]) -> list[str]:
    lines: list[str] = ["## Panel 1 — Drift Prevention Status", ""]
    lines.append(f"- guard_status: `{p.get('guard_status', 'unknown')}`")
    lines.append(f"- guard_cases: `{p.get('guard_cases', 0)} / {p.get('expected_cases', 0)}`")
    lines.append(f"- maturity_last_updated: `{p.get('maturity_last_updated', '')}`")
    lines.append(f"- harness_supported_count: `{p.get('harness_supported_count', 0)}`")
    lines.append(f"- head_commit_date: `{p.get('head_commit_date', '')}`")
    delta = p.get("last_updated_delta_days")
    lines.append(f"- last_updated_delta_days: `{delta if delta is not None else 'unknown'}`")
    lines.append(f"- silent_failing_cycles_count: `{p.get('silent_failing_cycles_count', 0)}`")
    return lines + [""]


def _render_panel_2(p: dict[str, Any]) -> list[str]:
    lines: list[str] = ["## Panel 2 — Maturity Distribution", ""]
    for kind in ("skills", "mcp_tools", "milestones"):
        bucket = p.get(kind, {})
        if isinstance(bucket, dict):
            lines.append(f"### {kind}")
            lines.append("")
            lines.append("| metric | value |")
            lines.append("|---|---|")
            lines.append(f"| total | {bucket.get('total', 0)} |")
            if kind != "milestones":
                lines.append(f"| stable | {bucket.get('stable', 0)} |")
                lines.append(f"| beta | {bucket.get('beta', 0)} |")
                lines.append(f"| alpha | {bucket.get('alpha', 0)} |")
            else:
                lines.append(f"| done | {bucket.get('done', 0)} |")
                lines.append(f"| in_progress | {bucket.get('in_progress', 0)} |")
                lines.append(f"| planned | {bucket.get('planned', 0)} |")
            lines.append("")
    harnesses = p.get("harnesses", {})
    if isinstance(harnesses, dict):
        lines.append("### harnesses")
        lines.append("")
        lines.append(f"- supported: `{harnesses.get('supported', 0)}`")
        names = harnesses.get("supported_names", [])
        if isinstance(names, list) and names:
            lines.append(f"- names: {', '.join(f'`{n}`' for n in names)}")
        lines.append("")
    return lines


def _render_panel_3(p: dict[str, Any]) -> list[str]:
    lines: list[str] = ["## Panel 3 — Memory Index Utilization", ""]
    lines.append(f"- entries_total: `{p.get('entries_total', 0)}`")
    by_state = p.get("entries_by_merge_state", {})
    if isinstance(by_state, dict):
        if by_state:
            state_str = ", ".join(f"`{k}`={v}" for k, v in by_state.items())
        else:
            state_str = "(none)"
        lines.append(f"- entries_by_merge_state: {state_str}")
    lines.append(f"- cue_anchors_unique: `{p.get('cue_anchors_unique', 0)}`")
    lines.append(f"- first_entry_date: `{p.get('first_entry_date', '')}`")
    lines.append(f"- last_entry_date: `{p.get('last_entry_date', '')}`")
    top = p.get("cue_anchors_top", [])
    if isinstance(top, list) and top:
        lines.append("")
        lines.append("### Top cue anchors")
        lines.append("")
        lines.append("| anchor | count |")
        lines.append("|---|---|")
        for entry in top[:10]:
            if isinstance(entry, dict):
                lines.append(
                    f"| {entry.get('anchor', '')} | {entry.get('count', 0)} |"
                )
    return lines + [""]


def _render_panel_4(p: dict[str, Any]) -> list[str]:
    lines: list[str] = ["## Panel 4 — Smoke Trend", ""]
    lines.append(f"- cumulative_total: `{p.get('cumulative_total', 0)}`")
    lines.append(f"- cumulative_pass: `{p.get('cumulative_pass', 0)}`")
    rate = p.get("cumulative_pass_rate", 0.0)
    lines.append(f"- cumulative_pass_rate: `{rate:.4f}`")
    lines.append(f"- smoke_files_count: `{p.get('smoke_files_count', 0)}`")
    recent = p.get("recent_releases", [])
    if isinstance(recent, list) and recent:
        lines.append("")
        lines.append("### Recent release smoke counts")
        lines.append("")
        lines.append("| version | pass | total |")
        lines.append("|---|---|---|")
        for entry in recent:
            if isinstance(entry, dict):
                lines.append(
                    f"| {entry.get('version', '')} "
                    f"| {entry.get('pass', 0)} "
                    f"| {entry.get('total', 0)} |"
                )
    return lines + [""]


def _render_panel_5(p: dict[str, Any]) -> list[str]:
    lines: list[str] = ["## Panel 5 — Recent Release Cycle", ""]
    lines.append(f"- items_total: `{p.get('items_total', 0)}`")
    lines.append(f"- top_n: `{p.get('top_n', 0)}`")
    timeline = p.get("timeline", [])
    if isinstance(timeline, list) and timeline:
        lines.append("")
        lines.append("### Timeline (preview, first 120 char)")
        lines.append("")
        for entry in timeline:
            if isinstance(entry, dict):
                idx = entry.get("index", 0)
                preview = entry.get("preview", "")
                lines.append(f"- [{idx}] {preview}")
    return lines + [""]


# ---------------------------------------------------------------------------
# Renderer — HTML output (v0.13.2+)
# ---------------------------------------------------------------------------


# Chart.js CDN URL. Released under MIT license.
# https://www.chartjs.org/docs/latest/getting-started/installation.html
CHARTJS_CDN_URL: Final[str] = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"


def render_dashboard_html(snapshot: dict[str, Any]) -> str:
    """snapshot dict 를 단일 self-contained HTML page 로 직렬화 (v0.13.2+).

    Chart.js CDN + 5 panel widget (gauge / doughnut / line / bar / timeline list).
    prefers-color-scheme 의 dark mode 자동 인식. JavaScript off 시에도 static
    fallback 이 보임.

    Args:
        snapshot: collect_dashboard_snapshot() 의 결과 dict

    Returns:
        str — single HTML doc
    """
    panels = snapshot.get("panels", {})
    if not isinstance(panels, dict):
        panels = {}
    generated_at = str(snapshot.get("generated_at", ""))
    tool_version = str(snapshot.get("tool_version", ""))
    workspace_root = str(snapshot.get("workspace_root", ""))

    html = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">',
        f"  <title>Quality Dashboard · {tool_version}</title>",
        "  <style>",
        _HTML_CSS,
        "  </style>",
        "</head>",
        "<body>",
        "  <header>",
        f"    <h1>Quality Dashboard</h1>",
        f'    <p class="meta">generated_at: <code>{_html_escape(generated_at)}</code> · '
        f'tool_version: <code>{_html_escape(tool_version)}</code></p>',
        f'    <p class="meta">workspace: <code>{_html_escape(workspace_root)}</code></p>',
        "  </header>",
        "  <main>",
    ]
    html.append(_render_html_panel_1(panels.get("drift_prevention", {})))
    html.append(_render_html_panel_2(panels.get("maturity_distribution", {})))
    html.append(_render_html_panel_3(panels.get("memory_index_utilization", {})))
    html.append(_render_html_panel_4(panels.get("smoke_trend", {})))
    html.append(_render_html_panel_5(panels.get("recent_releases", {})))
    html.append("  </main>")

    # Charts (Chart.js) — graceful when JS off (canvas + static text fallback)
    html.append("  <script>")
    html.append(_render_html_charts_js(panels))
    html.append("  </script>")
    html.append(f'  <script src="{_html_escape(CHARTJS_CDN_URL)}"></script>')

    html.append("</body>")
    html.append("</html>")
    return "\n".join(html) + "\n"


# ---------------------------------------------------------------------------
# HTML helpers (private)
# ---------------------------------------------------------------------------


def _html_escape(text: str) -> str:
    """HTML escape — `<`, `>`, `&`, `"`, `'` 만 처리."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


_HTML_CSS: Final[str] = """
:root {
  color-scheme: light dark;
  --bg: #fff;
  --fg: #1a1a1a;
  --muted: #666;
  --border: #ddd;
  --panel: #f9f9f9;
  --pass: #1b8a3a;
  --fail: #c0392b;
  --error: #d68910;
  --link: #1d6fb8;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1a1a1a; --fg: #e0e0e0; --muted: #aaa;
    --border: #333; --panel: #252525;
    --pass: #58c47e; --fail: #ff6b5b; --error: #ffd066;
    --link: #5aa7e8;
  }
}
body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--fg); margin: 0; padding: 2rem; }
h1 { font-size: 1.8rem; margin-bottom: 0.3rem; }
.meta { color: var(--muted); font-size: 0.85rem; }
code { background: var(--panel); padding: 0.1em 0.3em; border-radius: 3px; font-size: 0.9em; }
main { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.5rem; margin-top: 2rem; }
.panel { background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 1.2rem; }
.panel h2 { font-size: 1.1rem; margin: 0 0 0.8rem; }
.panel .stat { font-size: 1.6rem; font-weight: 600; }
.panel .stat.pass { color: var(--pass); }
.panel .stat.fail { color: var(--fail); }
.panel .stat.error { color: var(--error); }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th, td { padding: 0.35rem 0.5rem; text-align: left; border-bottom: 1px solid var(--border); }
canvas { max-width: 100%; }
.timeline li { margin-bottom: 0.4rem; font-size: 0.85rem; color: var(--muted); }
ul.timeline { padding-left: 1.2rem; }
""".strip()


def _render_html_panel_1(p: dict[str, Any]) -> str:
    """Panel 1 HTML — drift guard status."""
    status = str(p.get("guard_status", "unknown"))
    guard_cases_pass = int(p.get("guard_cases_pass", 0))
    guard_cases = int(p.get("guard_cases", 0))
    expected = int(p.get("expected_cases", 0))
    runtime_ms = int(p.get("guard_runtime_ms", 0))
    maturity_last_updated = str(p.get("maturity_last_updated", ""))
    head_commit_date = str(p.get("head_commit_date", ""))
    delta = p.get("last_updated_delta_days")
    harness_supported_count = int(p.get("harness_supported_count", 0))
    silent_failing = int(p.get("silent_failing_cycles_count", 0))
    phase = str(p.get("phase", ""))

    status_class = status if status in ("pass", "fail", "error") else "unknown"
    return f"""  <section class="panel">
    <h2>Panel 1 — Drift Prevention Status</h2>
    <p>guard_status: <span class="stat {status_class}">{_html_escape(status)}</span></p>
    <p>guard: {guard_cases_pass}/{guard_cases} pass (expected {expected})</p>
    <p>guard_runtime_ms: {runtime_ms}</p>
    <p>maturity_last_updated: <code>{_html_escape(maturity_last_updated)}</code></p>
    <p>head_commit_date: <code>{_html_escape(head_commit_date)}</code></p>
    <p>last_updated_delta_days: {delta if delta is not None else 'unknown'}</p>
    <p>harness_supported_count: {harness_supported_count}</p>
    <p><strong>silent_failing_cycles_count: {silent_failing}</strong> (Phase 13 AC1 north-star)</p>
    <p class="meta">{_html_escape(phase)}</p>
  </section>"""


def _render_html_panel_2(p: dict[str, Any]) -> str:
    """Panel 2 HTML — maturity distribution + chart canvas."""
    skills = p.get("skills", {}) if isinstance(p.get("skills"), dict) else {}
    mcp = p.get("mcp_tools", {}) if isinstance(p.get("mcp_tools"), dict) else {}
    harnesses = p.get("harnesses", {}) if isinstance(p.get("harnesses"), dict) else {}
    milestones = p.get("milestones", {}) if isinstance(p.get("milestones"), dict) else {}
    return f"""  <section class="panel">
    <h2>Panel 2 — Maturity Distribution</h2>
    <table>
      <thead><tr><th>bucket</th><th>total</th><th>stable</th><th>beta</th><th>alpha</th></tr></thead>
      <tbody>
        <tr><td>skills</td><td>{int(skills.get('total', 0))}</td><td>{int(skills.get('stable', 0))}</td><td>{int(skills.get('beta', 0))}</td><td>{int(skills.get('alpha', 0))}</td></tr>
        <tr><td>mcp_tools</td><td>{int(mcp.get('total', 0))}</td><td>{int(mcp.get('stable', 0))}</td><td>{int(mcp.get('beta', 0))}</td><td>{int(mcp.get('alpha', 0))}</td></tr>
      </tbody>
    </table>
    <p>harnesses.supported: <strong>{int(harnesses.get('supported', 0))}</strong></p>
    <p>milestones: total={int(milestones.get('total', 0))} done={int(milestones.get('done', 0))} in_progress={int(milestones.get('in_progress', 0))}</p>
    <canvas id="chart-maturity" height="160"></canvas>
  </section>"""


def _render_html_panel_3(p: dict[str, Any]) -> str:
    """Panel 3 HTML — memory index utilization + chart canvas.

    v0.13.1+ Phase 13 AC2 telemetry 정합: retrieval_hit_rate 가 telemetry events.jsonl
    집계값으로 emit. by_source 분해 + events_parsed/skipped 도 표시.
    """
    entries_total = int(p.get("entries_total", 0))
    cue_unique = int(p.get("cue_anchors_unique", 0))
    first_date = str(p.get("first_entry_date", ""))
    last_date = str(p.get("last_entry_date", ""))
    hit_rate = float(p.get("retrieval_hit_rate", 0.0))
    by_state = p.get("entries_by_merge_state", {})
    state_str = ", ".join(
        f"{_html_escape(str(k))}={int(v)}" for k, v in (by_state.items() if isinstance(by_state, dict) else [])
    )
    telemetry = p.get("telemetry", {})
    if not isinstance(telemetry, dict):
        telemetry = {}
    t_total_calls = int(telemetry.get("total_calls", 0))
    t_total_hits = int(telemetry.get("total_hits", 0))
    t_by_source = telemetry.get("by_source", {})
    t_source_str = ", ".join(
        f"{_html_escape(str(k))}:calls={int(v.get('calls', 0))},hits={int(v.get('hits', 0))}"
        for k, v in (sorted(t_by_source.items()) if isinstance(t_by_source, dict) else [])
    )
    return f"""  <section class="panel">
    <h2>Panel 3 — Memory Index Utilization</h2>
    <p class="stat">{entries_total}</p>
    <p class="meta">total entries · unique cue anchors: {cue_unique}</p>
    <p class="meta">first_entry_date: <code>{_html_escape(first_date)}</code></p>
    <p class="meta">last_entry_date: <code>{_html_escape(last_date)}</code></p>
    <p class="meta">retrieval_hit_rate: <strong>{hit_rate:.4f}</strong> (Phase 13 AC2 telemetry)</p>
    <p class="meta">telemetry calls/hits: {t_total_calls}/{t_total_hits} · by_source: {t_source_str or '(none)'}</p>
    <p class="meta">by merge_state: {state_str or '(none)'}</p>
    <canvas id="chart-memory" height="160"></canvas>
  </section>"""


def _render_html_panel_4(p: dict[str, Any]) -> str:
    """Panel 4 HTML — smoke trend + chart canvas."""
    cum_total = int(p.get("cumulative_total", 0))
    cum_pass = int(p.get("cumulative_pass", 0))
    cum_rate = float(p.get("cumulative_pass_rate", 0.0))
    smoke_files = int(p.get("smoke_files_count", 0))
    return f"""  <section class="panel">
    <h2>Panel 4 — Smoke Trend</h2>
    <p class="stat pass">{cum_pass}/{cum_total}</p>
    <p class="meta">cumulative pass rate: {cum_rate:.4f}</p>
    <p class="meta">smoke test files: {smoke_files}</p>
    <canvas id="chart-smoke" height="160"></canvas>
  </section>"""


def _render_html_panel_5(p: dict[str, Any]) -> str:
    """Panel 5 HTML — recent releases timeline."""
    items_total = int(p.get("items_total", 0))
    top_n = int(p.get("top_n", 0))
    timeline = p.get("timeline", [])
    items: list[str] = []
    if isinstance(timeline, list):
        for entry in timeline:
            if isinstance(entry, dict):
                idx = entry.get("index", 0)
                preview = entry.get("preview", "")
                items.append(f"      <li>[{idx}] {_html_escape(str(preview))}</li>")
    timeline_html = "\n".join(items) if items else "      <li>(no items)</li>"
    return f"""  <section class="panel">
    <h2>Panel 5 — Recent Release Cycle</h2>
    <p>items_total: <strong>{items_total}</strong> (top_n={top_n})</p>
    <ul class="timeline">
{timeline_html}
    </ul>
  </section>"""


def _render_html_charts_js(panels: dict[str, Any]) -> str:
    """Chart.js 초기화 JS — graceful: JS off 시 static fallback 그대로 보임.

    Chart.js 가 로드된 후 chart 인스턴스 생성. 미로드 시 catch 후 silent.
    """
    # Panel 2: maturity (bar — skills stable/beta/alpha vs mcp stable/beta/alpha)
    p2 = panels.get("maturity_distribution", {}) if isinstance(panels.get("maturity_distribution"), dict) else {}
    skills = p2.get("skills", {}) if isinstance(p2.get("skills"), dict) else {}
    mcp = p2.get("mcp_tools", {}) if isinstance(p2.get("mcp_tools"), dict) else {}

    # Panel 3: memory cumulative timeline (line)
    p3 = panels.get("memory_index_utilization", {}) if isinstance(panels.get("memory_index_utilization"), dict) else {}
    timeline = p3.get("cumulative_timeline", [])
    timeline_dates: list[str] = []
    timeline_counts: list[int] = []
    if isinstance(timeline, list):
        for entry in timeline:
            if isinstance(entry, dict):
                timeline_dates.append(str(entry.get("date", "")))
                try:
                    timeline_counts.append(int(entry.get("count", 0)))
                except (TypeError, ValueError):
                    timeline_counts.append(0)

    # Panel 4: smoke trend (line — release versions)
    p4 = panels.get("smoke_trend", {}) if isinstance(panels.get("smoke_trend"), dict) else {}
    recent = p4.get("recent_releases", [])
    smoke_versions: list[str] = []
    smoke_counts: list[int] = []
    if isinstance(recent, list):
        for entry in recent:
            if isinstance(entry, dict):
                smoke_versions.append(str(entry.get("version", "")))
                try:
                    smoke_counts.append(int(entry.get("pass", 0)))
                except (TypeError, ValueError):
                    smoke_counts.append(0)
    smoke_versions.reverse()
    smoke_counts.reverse()

    import json as _json

    chart_data = {
        "maturity": {
            "labels": ["skills", "mcp_tools"],
            "stable": [int(skills.get("stable", 0)), int(mcp.get("stable", 0))],
            "beta": [int(skills.get("beta", 0)), int(mcp.get("beta", 0))],
            "alpha": [int(skills.get("alpha", 0)), int(mcp.get("alpha", 0))],
        },
        "memory": {
            "dates": timeline_dates,
            "counts": timeline_counts,
        },
        "smoke": {
            "versions": smoke_versions,
            "counts": smoke_counts,
        },
    }
    json_str = _json.dumps(chart_data, ensure_ascii=False)
    return f"""    (function() {{
      var data = {json_str};
      function ready(fn) {{
        if (typeof window.Chart !== 'undefined') {{ fn(); }}
        else {{ window.addEventListener('load', function() {{ if (typeof window.Chart !== 'undefined') fn(); }}); }}
      }}
      ready(function() {{
        try {{
          new Chart(document.getElementById('chart-maturity'), {{
            type: 'bar',
            data: {{
              labels: data.maturity.labels,
              datasets: [
                {{ label: 'stable', data: data.maturity.stable, backgroundColor: '#1b8a3a' }},
                {{ label: 'beta', data: data.maturity.beta, backgroundColor: '#d68910' }},
                {{ label: 'alpha', data: data.maturity.alpha, backgroundColor: '#c0392b' }},
              ],
            }},
            options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom' }} }}, scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, beginAtZero: true }} }} }}
          }});
          new Chart(document.getElementById('chart-memory'), {{
            type: 'line',
            data: {{
              labels: data.memory.dates,
              datasets: [{{ label: 'cumulative entries', data: data.memory.counts, borderColor: '#1d6fb8', fill: false, tension: 0.1 }}],
            }},
            options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom' }} }} }}
          }});
          new Chart(document.getElementById('chart-smoke'), {{
            type: 'line',
            data: {{
              labels: data.smoke.versions,
              datasets: [{{ label: 'pass count', data: data.smoke.counts, borderColor: '#1b8a3a', fill: false, tension: 0.1 }}],
            }},
            options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom' }} }} }}
          }});
        }} catch (e) {{ /* silent — static fallback already visible */ }}
      }});
    }})();"""


__all__: list[str] = [
    "collect_drift_prevention",
    "collect_maturity_distribution",
    "collect_memory_index_utilization",
    "collect_smoke_trend",
    "collect_recent_releases",
    "collect_dashboard_snapshot",
    "render_dashboard_markdown",
    "render_dashboard_html",
    "run_drift_prevention_guard_inline",
    "SMOKE_COUNT_PATTERN",
    "EXPECTED_DRIFT_GUARD_CASES",
    "DEFAULT_RECENT_RELEASES",
    "DRIFT_GUARD_INLINE_TIMEOUT",
    "CHARTJS_CDN_URL",
]