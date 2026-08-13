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
from typing import Any, Final, NamedTuple
from workflow_kit.common.paths import state_path_for_workspace, memory_active_dir

# v1.1.7+ 분리 (2026-08-11): renderer / workspace-root helper 를 sibling module 로
# verbatim 이동. 아래 재-import + __all__ 등재로 기존 소비자 표면을 그대로 유지한다.
from workflow_kit.common.dashboard_render_html import (
    CHARTJS_CDN_URL,
    render_dashboard_html,
)
from workflow_kit.common.dashboard_render_markdown import (
    render_dashboard_markdown,
    _render_panel_1,
    _render_panel_2,
    _render_panel_3,
    _render_panel_4,
    _render_panel_5,
    _render_panel_6,
    _render_panel_7,
    _render_panel_8,
)
from workflow_kit.common.dashboard_workspace_roots import (
    _branch_state_paths,
    _auto_extra_roots,
    _env_extra_roots,
    _worktree_branch_map,
    _state_path_to_worktree_root,
    _confidence_for_state_path,
    _registry_extra_roots,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Release note 의 누적 smoke count 패턴 (Beta-v0.11.25.md §검증 정합).
# 형식 1: "누적 smoke test **N/N PASS**" (v0.13.0 정공법)
# 형식 2: "누적 smoke **N+ PASS**" (v0.14.1+ 슬랙 표기 — `test` token 생략 + `N+` 표기)
#   parse 시 N+ 표기는 (N, N) 으로 정규화 (pass = total 가정, 실제 100% pass 정합)
# 형식 3: "누적 ... smoke ... **N/N PASS**" (forward-compat alias)
SMOKE_COUNT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"누적\s+(?:[\w\s]*?\s+)?smoke\s+(?:test\s+)?\*\*(\d+)(?:/(\d+)|\+)\s+PASS\*\*"
)

# smoke_trend panel 의 default release note top-N
DEFAULT_RECENT_RELEASES: Final[int] = 10

# drift_prevention panel 의 expected guard case 갯수 (v0.11.23 cycle 4-layer, v0.11.25 6/6 정합)
EXPECTED_DRIFT_GUARD_CASES: Final[int] = 7  # v1.2.1: case 7 (LICENSE 사본 정합) 추가

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

# maturity 선언(`maturity_matrix.json`)이 *따라가야 하는* 실제 surface.
# 이 경로들이 `last_updated` 이후에 바뀌었다면 선언이 뒤처진 것 = 진짜 drift.
# (v1.0.1 재정의 이전에는 `last_updated != 오늘` 을 stale 로 봤다 — 파일을 매일
#  스탬프하지 않는 한 영구히 red 인, 구조적으로 초록이 될 수 없는 판정이었다.)
MATURITY_SURFACE_PATHS: Final[tuple[str, ...]] = (
    "workflow-source/core/maturity_matrix.json",
    "workflow-source/skills",
    "workflow-source/mcp_servers",
    "workflow-source/harnesses",
)

# Phase 13 AC1 north-star 의 원장 (append-only JSONL, release cycle 당 1 line).
# release pipeline 이 self-recover 결과를 여기에 기록하고, dashboard 는 *읽기만* 한다.
DRIFT_LEDGER_RELPATH: Final[str] = "ai-workflow/memory/release/drift_ledger.jsonl"


class MetricContract(NamedTuple):
    """판정 지표 하나가 지켜야 하는 계약.

    Attributes:
        panel: snapshot 의 panel key
        metric: 값 field 이름
        source: 판정 **근거** field 이름 (무엇을 보고 그 값을 냈는가)
        measured: 측정 여부 field 이름 (north-star 만; 없으면 빈 문자열)
    """
    panel: str
    metric: str
    source: str
    measured: str


# **판정 지표는 값만 내지 않는다 — 무엇을 보고 그렇게 판정했는지 함께 낸다.**
#
# v0.14.0~v1.0.0 동안 north-star 자리에 freshness proxy 가 앉아 있어도 아무도 몰랐다.
# 값의 타입은 맞았고, 근거를 말하지 않으니 대조할 것이 없었기 때문이다 (노트 §2.19).
# 근거를 강제하면 "무엇을 재고 있는지" 가 payload 에 드러나고, proxy/placeholder 로
# 때운 지표는 `check_metric_source_contract.py` 가 즉시 잡는다.
JUDGMENT_METRICS: Final[tuple[MetricContract, ...]] = (
    MetricContract("drift_prevention", "maturity_stale", "maturity_staleness_source", ""),
    MetricContract("drift_prevention", "silent_failing_cycles_count",
                   "silent_failing_cycles_source", "silent_failing_cycles_measured"),
    MetricContract("multi_agent_concurrent_write_conflict", "conflict_count",
                   "conflict_count_source", "conflict_count_measured"),
    MetricContract("memory_index_utilization", "retrieval_hit_rate",
                   "retrieval_hit_rate_source", ""),
)

# 근거 자리에 오면 안 되는 말들 — "아직 안 정했다" 를 값처럼 흘려보내는 표현.
FORBIDDEN_SOURCE_TOKENS: Final[tuple[str, ...]] = (
    "proxy", "placeholder", "pending", "tbd", "todo", "fixme",
)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


#: workspace root 를 **어디서 얻었는지**. 판정이 아니라 출처다 (§2.51).
WORKSPACE_SOURCE_ARGUMENT: Final[str] = "argument"
WORKSPACE_SOURCE_CWD: Final[str] = "cwd"


def resolve_workspace_root(workspace_root: Path | str | None) -> tuple[Path, str]:
    """측정 대상 workspace 와 **그것을 어디서 얻었는지** 를 함께 돌려준다.

    v1.0.7(§2.51) 이전에는 미지정 시 ``Path(__file__).resolve().parents[3]`` 로
    떨어졌다. 이 저장소는 editable install 이라 그 값이 우연히 저장소 루트였지만,
    **설치본에서는 workspace 가 아니다** — 실측:

        모듈: <venv>/lib/python3.13/site-packages/workflow_kit/common/dashboard_data.py
        parents[3] → <venv>/lib/python3.13     (실재하는 디렉터리, ai-workflow/ 없음)

    그러면 8 panel 이 전부 빈 값을 내고, 그 빈 값이 **그 경로의 측정 결과처럼** 보고된다.
    오류가 아니라 조용히 틀린 측정이다. 모듈 위치로 사용자의 workspace 를 추측할 수
    있다는 전제 자체가 틀렸다 (doctor 의 §2.49 와 같은 축).

    이제 (명시 인자 → cwd) 두 갈래뿐이고, 어느 쪽이었는지는 snapshot 의
    ``workspace_root_source`` 에 남는다.
    """
    if workspace_root is None:
        return Path.cwd(), WORKSPACE_SOURCE_CWD
    return Path(workspace_root), WORKSPACE_SOURCE_ARGUMENT


def _repo_root(workspace_root: Path | str | None) -> Path:
    """`resolve_workspace_root` 의 값만 필요한 자리 (panel 내부용).

    출처까지 필요하면 `resolve_workspace_root` 를 쓴다 — 보고하는 경로와 실제로 쓰는
    경로가 갈라지면 보고가 사실이 아니게 된다.
    """
    root, _source = resolve_workspace_root(workspace_root)
    return root


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
        guard_cases: 총 guard case 갯수 (expected = EXPECTED_DRIFT_GUARD_CASES)
        expected_cases: EXPECTED_DRIFT_GUARD_CASES 정합
        guard_failure_names: fail case 의 name list (drift 발생 시)
        guard_executed_at: inline 실행 timestamp (ISO 8601)
        guard_runtime_ms: inline 실행 소요 시간 (ms)
        maturity_last_updated: maturity_matrix.json 의 last_updated (ISO date)
        maturity_last_updated_source: 'maturity_matrix.json'
        harness_supported_count: harness.supported 리스트 길이
        head_commit_date: HEAD commit 의 ISO date (subprocess git log -1)
        last_updated_delta_days: maturity_last_updated ↔ head_commit_date 의 일수 차이
        maturity_surface_changed_at: maturity surface 를 마지막으로 바꾼 commit 의 ISO date
        maturity_staleness_source: 'maturity_surface_commit' | 'unknown' (판정 근거)
        silent_failing_cycles_count: Phase 13 AC1 north-star (원장 기반, 미측정이면 0 + measured=False)
        silent_failing_cycles_measured: 원장에 cycle 이 1건 이상 기록됐는가
        silent_failing_cycles_measured_cycles: 원장에 기록된 총 release cycle 갯수

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

    # v1.0.1 재정의 — stale 은 *달력* 이 아니라 *drift* 다.
    #
    # 기존: `maturity_last_updated != 오늘` → 파일을 매일 스탬프하지 않는 한 항상 True.
    #       지표를 초록으로 만드는 유일한 방법이 "날짜만 찍기" 였고, 그건 실질 없는
    #       초록불이다 (Beta-v1.0.0.md §2.18 의 maturity_stale 경고 참조).
    # 현재: maturity surface (skills / mcp_servers / harnesses / matrix 자신) 가
    #       `last_updated` **이후** commit 으로 바뀌었으면 선언이 뒤처진 것 → stale.
    #       surface 가 그대로면 며칠이 지나도 stale 아님. 스탬프로는 못 속이고,
    #       선언을 실제로 갱신해야만 초록이 된다.
    #
    # git 을 못 읽거나 last_updated 가 비면 **stale 로 단정하지 않는다** (source=unknown).
    # 판정 근거가 없을 때 red 를 내는 체크는 위양성으로 무시당한다.
    from datetime import date as _date
    today_iso = _date.today().isoformat()
    maturity_surface_changed_at = _last_commit_date_for_paths(root, MATURITY_SURFACE_PATHS)
    if maturity_last_updated and maturity_surface_changed_at:
        # ISO date 는 사전순 = 시간순.
        maturity_stale = maturity_surface_changed_at > maturity_last_updated
        maturity_staleness_source = "maturity_surface_commit"
    else:
        maturity_stale = False
        maturity_staleness_source = "unknown"
    maturity_refresh_hint = (
        "python3 -c \"from workflow_kit.common.state.cache import refresh_maturity_last_updated; "
        "from pathlib import Path; "
        "print(refresh_maturity_last_updated(Path('workflow-source/core/maturity_matrix.json')))\""
    ) if maturity_stale else ""

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

    # north-star 는 freshness proxy 가 아니다 (v1.0.1 분리).
    # 정의(wiki/topics/phase-13-definition-north-star.md §2.2): "drift 를 guard 가
    # 검출했으나 manual fix 까지 걸린 release cycle 의 누적 갯수". maturity 날짜
    # 스탬프와는 아무 상관이 없다 — v0.14.0 에서 임시 proxy 로 붙였던 것을 떼어내고
    # 실제 원장(`DRIFT_LEDGER_RELPATH`)에서 읽는다. 원장이 비면 0 이 아니라
    # **미측정** 으로 표시한다 (measured=False).
    north_star = collect_silent_failing_cycles(root)

    return {
        **guard_panel,
        "maturity_last_updated": maturity_last_updated,
        "maturity_last_updated_source": "maturity_matrix.json",
        "maturity_stale": maturity_stale,
        "maturity_staleness_source": maturity_staleness_source,
        "maturity_surface_changed_at": maturity_surface_changed_at,
        "maturity_refresh_hint": maturity_refresh_hint,
        "today_iso": today_iso,
        "harness_supported_count": harness_supported_count,
        "head_commit_date": head_commit_date,
        "last_updated_delta_days": last_updated_delta_days,
        "silent_failing_cycles_count": north_star["count"],  # Phase 13 AC1 north-star
        "silent_failing_cycles_measured": north_star["measured"],
        "silent_failing_cycles_measured_cycles": north_star["measured_cycles"],
        "silent_failing_cycles_source": north_star["source"],
        "phase": "Phase 12 (done, v0.15.20) → Phase 13 (planned, v1.0.0 stable 진입 후)",
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


def _last_commit_date_for_paths(workspace_root: Path, paths: tuple[str, ...]) -> str:
    """주어진 경로들을 마지막으로 건드린 commit 의 ISO date. git 실패 시 empty string.

    실재하지 않는 pathspec 이 섞여도 git 이 나머지로 계산하도록 ``--`` 뒤에 그대로
    넘긴다 (`--ignore-unmatch` 는 log 에 없으므로 존재하는 경로만 추려서 전달).
    """
    existing = [p for p in paths if (workspace_root / p).exists()]
    if not existing:
        return ""
    try:
        completed = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=short", "--", *existing],
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


def collect_silent_failing_cycles(workspace_root: Path | str | None = None) -> dict[str, Any]:
    """Phase 13 AC1 north-star — drift 를 manual fix 해야 했던 release cycle 의 누적 갯수.

    원장(`DRIFT_LEDGER_RELPATH`)은 release pipeline 이 release 시도마다 1 line 씩
    append 하는 JSONL 이다. 본 함수는 **읽기만** 한다.

    **line 과 cycle 은 1:1 이 아니다.** manual_required drift 가 나오면 release 는
    중단되고, 사람이 고친 뒤 *같은 version 으로* 다시 돌린다 — 이 재시도는 한 cycle
    안의 두 시도다. line 을 그대로 세면 정상 운영 흐름이 분모를 계속 부풀린다
    (1 cycle 이 "1/2" 로 보인다). 그래서 ``version`` 으로 묶고, 한 cycle 안에서
    **한 번이라도** manual 개입이 필요했으면 그 cycle 을 분자로 센다.

    원장이 없거나 비어 있으면 ``count=0`` 이되 ``measured=False`` 로 emit 한다.
    "아직 안 재봤다" 와 "재봤더니 0" 은 다른 상태이고, 둘을 같은 0 으로 보여주면
    실질 없는 초록불이 된다.

    Returns:
        dict {count, measured, measured_cycles, source, ledger_path}
    """
    root = _repo_root(workspace_root)
    ledger = root / DRIFT_LEDGER_RELPATH
    out: dict[str, Any] = {
        "count": 0,
        "measured": False,
        "measured_cycles": 0,
        "source": DRIFT_LEDGER_RELPATH,
        "ledger_path": str(ledger),
    }
    if not ledger.is_file():
        return out
    # version → "이 cycle 에서 manual 개입이 있었나". version 없는 line 은 묶을 근거가
    # 없으므로 각자 별개 cycle 로 (합치면 서로 다른 cycle 을 하나로 눌러버린다).
    cycles: dict[str, bool] = {}
    unkeyed = 0
    try:
        for line in ledger.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                # malformed line 은 skip (telemetry summarize 와 동일 정공법).
                continue
            if not isinstance(entry, dict):
                continue
            version = entry.get("version")
            if isinstance(version, str) and version:
                key = version
            else:
                unkeyed += 1
                key = f"__unkeyed_{unkeyed}"
            try:
                dirty = int(entry.get("manual_required_count", 0)) > 0
            except (TypeError, ValueError):
                # 셀 수 없는 값은 판정하지 않는다 — cycle 자체는 분모에 남긴다.
                dirty = False
            cycles[key] = cycles.get(key, False) or dirty
    except OSError:
        return out
    out["count"] = sum(1 for is_dirty in cycles.values() if is_dirty)
    out["measured_cycles"] = len(cycles)
    out["measured"] = len(cycles) > 0
    return out


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
# Panel 6 — Multi-Agent Concurrent Write Conflict (Phase 15 north-star)
# ---------------------------------------------------------------------------

def collect_multi_agent_concurrent_write_conflict(workspace_root: Path) -> dict[str, Any]:
    """Phase 14 north-star: `multi_agent_concurrent_write_conflict_count` = 0.

    v0.14.0+ append-only layout 의 structural 정합성 검증 — sub-agent 2개+ 동시
    fan-out 시 mutable 공유 파일의 3-way merge conflict / overwrite race 가 working
    tree 에 잔존하는지 check.

    측정원 (v0.14.7 Phase 15 follow-up 통합):
    1. active/ 하위 working tree 의 git merge conflict marker (`<<<<<<<`)
       — agent 가 `<<<<<<<` / `=======` / `>>>>>>>` 잔존한 채 commit 한 경우 검출.
    2. git log --all --merges 의 commit message 에 "CONFLICT" keyword 포함 (subprocess)
       — historical merge conflict 검출.

    Returns:
        dict {
            north_star: 'multi_agent_concurrent_write_conflict_count',
            working_tree_conflict_count: int,   # working tree markers
            git_log_conflict_count: int,         # git merge history
            conflict_count: int,                 # combined (= working + git_log)
            conflict_locations: list[str],       # working tree 만
            status: 'pass' | 'fail',
            threshold: int,
        }
    """
    import subprocess as _subprocess

    root = _repo_root(workspace_root)
    active_dir = memory_active_dir(root)
    working_tree_conflict_count = 0
    conflict_locations: list[str] = []
    if active_dir.is_dir():
        for f in active_dir.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix not in (".md", ".json"):
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if "<<<<<<<" in text:
                working_tree_conflict_count += 1
                try:
                    conflict_locations.append(str(f.relative_to(root)))
                except ValueError:
                    conflict_locations.append(str(f))

    # git log --all --merges 의 conflict keyword count (historical)
    #
    # git 을 못 읽었을 때 0 을 그대로 두면 "충돌 없음" 과 "못 셌음" 이 같은 0 이 된다.
    # 어느 측정원이 실제로 돌았는지를 `conflict_count_source` 로 함께 낸다 (§2.19 규칙).
    git_log_conflict_count = 0
    git_log_measured = False
    try:
        proc = _subprocess.run(
            ["git", "log", "--all", "--merges", "--pretty=format:%H %s"],
            cwd=str(root), capture_output=True, text=True, timeout=10, check=False,
        )
        if proc.returncode == 0:
            git_log_measured = True
            git_log_conflict_count = sum(
                1
                for line in proc.stdout.splitlines()
                if "CONFLICT" in line.upper()
            )
    except (_subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    measured_sources = []
    if active_dir.is_dir():
        measured_sources.append("working_tree")
    if git_log_measured:
        measured_sources.append("git_log")

    conflict_count = working_tree_conflict_count + git_log_conflict_count
    measured = bool(measured_sources)
    return {
        "north_star": "multi_agent_concurrent_write_conflict_count",
        "working_tree_conflict_count": working_tree_conflict_count,
        "git_log_conflict_count": git_log_conflict_count,
        "git_log_measured": git_log_measured,
        "conflict_count": conflict_count,
        "conflict_count_source": "+".join(measured_sources) if measured_sources else "unknown",
        "conflict_count_measured": measured,
        "conflict_locations": conflict_locations,
        # 측정원이 하나도 안 돌았으면 pass 라고 말하지 않는다.
        "status": ("pass" if conflict_count == 0 else "fail") if measured else "unknown",
        "threshold": 0,
    }


# ---------------------------------------------------------------------------
# Panel 7 — Deprecation Cycle Progress (v0.14.0+ ADR-003)
# ---------------------------------------------------------------------------

def collect_deprecation_cycle_progress(workspace_root: Path) -> dict[str, Any]:
    """v0.14.0+ 1st/2nd deprecation cycle 진행 상태 (Panel 7).

    ADR-003 deprecation cycle 의 정공법:
    - **v0.14.0** (1st cycle 시작): `work_backlog.md` → `.bak` silent fallback.
    - **v0.14.1** (1st cycle 종결): `.bak` 존재 시 warning stage (cache.py 가 emit).
    - **v0.14.5** (2nd cycle 시작): `--legacy-memory` opt-out flag 가 있을 때만 read.
    - **v0.15.0** (2nd cycle 종결): `.bak` 완전 drop.

    본 panel 은 `bak_present` + `deprecation_stage` + timeline 명시.
    v0.14.5+ 에서 `maturity_matrix.deprecation_cycle_stage` field 기반 stage 표시.

    Returns:
        dict {
            stage: 'v0.14.0' | 'v0.14.1' | 'v0.14.5' | 'v0.15.0',
            bak_present: bool,
            legacy_present: bool,  # (구) work_backlog.md 부재 — True 면 cycle 진행
            deprecation_warning_supported: bool,  # v0.14.1+ cache.py 정합
            timeline: dict,
            next_release: str,
        }
    """
    root = _repo_root(workspace_root)
    memory_dir = memory_active_dir(root)
    bak = memory_dir / "work_backlog.md.bak"
    legacy = memory_dir / "work_backlog.md"

    bak_present = bak.exists()
    legacy_present = legacy.exists()

    # v0.14.5+: maturity_matrix.deprecation_cycle_stage field 기반 동적 stage 표시
    maturity_path = root / "workflow-source" / "core" / "maturity_matrix.json"
    declared_stage: str | None = None
    if maturity_path.is_file():
        try:
            import json as _json
            mm = _json.loads(maturity_path.read_text(encoding="utf-8"))
            declared_stage = mm.get("deprecation_cycle_stage")
        except (OSError, ValueError):
            pass

    if not bak_present and not legacy_present:
        # 둘 다 부재 — cycle 완전 drop (v0.15.0 도달)
        stage = "v0.15.0"
        next_release = "(complete)"
    elif bak_present and not legacy_present:
        # cycle 진행 중 — declared_stage (maturity_matrix.deprecation_cycle_stage) 우선 사용.
        # default: v0.14.1 (1st cycle 종결 warning stage). v0.14.5 release 후
        # maturity_matrix 에서 'v0.14.5' 로 갱신 시 자동 표시.
        if declared_stage in ("v0.14.0", "v0.14.1", "v0.14.5", "v0.15.0"):
            stage = declared_stage
        else:
            stage = "v0.14.1"
        # next_release = declared_stage 다음 step
        next_map = {
            "v0.14.0": "(migrate to v0.14.0+)",
            "v0.14.1": "v0.14.5",
            "v0.14.5": "v0.15.0",
            "v0.15.0": "(complete)",
        }
        next_release = next_map.get(stage, "v0.15.0")
    elif legacy_present and not bak_present:
        stage = "v0.14.0"
        next_release = "(migrate to v0.14.0+ layout)"
    else:
        stage = "v0.14.0"
        next_release = "(migrate: remove legacy, keep bak)"

    return {
        "stage": stage,
        "declared_stage": declared_stage,
        "bak_present": bak_present,
        "legacy_present": legacy_present,
        "deprecation_warning_supported": True,  # cache.py:refresh_workflow_state_cache
        "timeline": {
            "v0.14.0": "1st cycle 시작 (silent fallback)",
            "v0.14.1": "1st cycle 종결 (warning stage)",
            "v0.14.5": "2nd cycle 시작 (--legacy-memory opt-out flag) — current" if declared_stage == "v0.14.5" else "2nd cycle 시작 (--legacy-memory opt-out flag)",
            "v0.15.0": "2nd cycle 종결 (.bak drop)",
        },
        "next_release": next_release,
    }


# ---------------------------------------------------------------------------
# Panel 8 — Memory Index + Telemetry Utilization v2 (Phase 15)
# ---------------------------------------------------------------------------

def collect_memory_index_utilization_v2(workspace_root: Path) -> dict[str, Any]:
    r"""Phase 15 Panel 8: memory_index entries + telemetry integration.

    기존 Panel 3 (collect_memory_index_utilization) 의 강화판 — v0.13.1+ telemetry
    sidecar 의 실측값 통합. AC2 north-star: telemetry_hit_rate = (cue + bm25 +
    expansion hits) / total queries.

    측정원:
    1. entries_total + by_merge_state: ai-workflow/memory/active/memory_index/entries/MEM-*.json
    2. telemetry_events_total + by_source + hit_rate: telemetry/events.jsonl

    Returns:
        dict { entries_total, entries_by_merge_state, telemetry_events_total,
               telemetry_by_source, telemetry_total_queries, telemetry_hit_count,
               telemetry_hit_rate, phase_15_north_star }
    """
    import json as _json

    root = _repo_root(workspace_root)
    memory_dir = memory_active_dir(root)
    memory_index_dir = memory_dir / "memory_index"

    # 1. entries count by merge_state (+ W-4: 30일 신규 유입)
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    _cutoff = _dt.now(_tz.utc) - _td(days=30)
    entries_by_merge_state: dict[str, int] = {}
    entries_total = 0
    entries_new_30d = 0
    entries_dir = memory_index_dir / "entries"
    if entries_dir.is_dir():
        for f in entries_dir.glob("MEM-*.json"):
            try:
                data = _json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            state = data.get("merge_state", "active")
            entries_by_merge_state[state] = entries_by_merge_state.get(state, 0) + 1
            entries_total += 1
            try:
                created = _dt.fromisoformat(str(data.get("created_at", "")).replace("Z", "+00:00"))
                if created.tzinfo is None:
                    created = created.replace(tzinfo=_tz.utc)
                if created >= _cutoff:
                    entries_new_30d += 1
            except ValueError:
                pass

    # 2. telemetry events parse
    telemetry_path = memory_index_dir / "telemetry" / "events.jsonl"
    telemetry_events_total = 0
    telemetry_by_source: dict[str, int] = {}
    telemetry_total_queries = 0
    telemetry_hit_count = 0
    if telemetry_path.is_file():
        try:
            for line in telemetry_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    ev = _json.loads(line)
                except ValueError:
                    continue
                if ev.get("error"):
                    continue
                telemetry_events_total += 1
                src = ev.get("source", "unknown")
                telemetry_by_source[src] = telemetry_by_source.get(src, 0) + 1
                hits = (
                    (ev.get("cue_hits", 0) or 0)
                    + (ev.get("bm25_hits", 0) or 0)
                    + (ev.get("expansion_hits", 0) or 0)
                )
                if hits > 0:
                    telemetry_hit_count += 1
                telemetry_total_queries += 1
        except OSError:
            pass

    hit_rate = (
        telemetry_hit_count / telemetry_total_queries
        if telemetry_total_queries > 0 else 0.0
    )

    # W-4 (ADR-006): 3-tuple 지표 — hit_rate 단독은 33일간 1.0 으로 고정돼
    # 정보가 없었다 (고정 질의 1종 → 고정 entry 1건). north-star 를 (질의
    # 다양성 / 신규 entry / distinct 조회) 로 교체, hit_rate 는 보조로 강등.
    # 값은 summarize_telemetry 단일 출처에서 온다. measurable=0 이면 해당
    # 지표는 "미측정" — 0 으로 위장하지 않는다.
    utilization_3tuple: dict[str, Any] = {
        "query_diversity": 0,
        "query_diversity_measurable": 0,
        "entries_new_30d": entries_new_30d,
        "distinct_entries_retrieved": 0,
        "selected_ids_measurable": 0,
    }
    try:
        from workflow_kit.common.state.memory_index import summarize_telemetry
        _summary = summarize_telemetry(root)
        utilization_3tuple.update({
            "query_diversity": _summary.query_diversity,
            "query_diversity_measurable": _summary.query_diversity_measurable,
            "distinct_entries_retrieved": _summary.distinct_entries_retrieved,
            "selected_ids_measurable": _summary.selected_ids_measurable,
        })
    except Exception:
        pass

    return {
        "entries_total": entries_total,
        "entries_by_merge_state": entries_by_merge_state,
        "telemetry_events_total": telemetry_events_total,
        "telemetry_by_source": telemetry_by_source,
        "telemetry_total_queries": telemetry_total_queries,
        "telemetry_hit_count": telemetry_hit_count,
        "telemetry_hit_rate": round(hit_rate, 4),
        "utilization_3tuple": utilization_3tuple,
        "phase_15_north_star": (
            "utilization_3tuple (query_diversity / entries_new_30d / "
            "distinct_entries_retrieved — ADR-006 W-4; hit_rate 는 보조)"
        ),
    }



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
    memory_index_dir = memory_active_dir(root) / "memory_index"
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
        excluded = _parse_self_gate_excluded(
            root / str(latest["release_note_path"])
        )
        eff_total = max(int(latest["total"]) - excluded, 0)
        eff_pass = min(int(latest["pass"]), eff_total)
        return {
            "cumulative_total": int(latest["total"]),
            "cumulative_pass": int(latest["pass"]),
            "cumulative_pass_rate": (
                int(latest["pass"]) / int(latest["total"])
                if int(latest["total"]) > 0
                else 0.0
            ),
            # 자기참조 게이트를 뺀 실효 지표. 원 수치(cumulative_*)는 그대로 남긴다 —
            # 무엇을 왜 뺐는지 감사 가능해야 하므로 숫자를 줄여 적지 않는다.
            "self_referential_excluded": excluded,
            "effective_total": eff_total,
            "effective_pass": eff_pass,
            "effective_pass_rate": (eff_pass / eff_total if eff_total > 0 else 0.0),
            "recent_releases": recent,
            "smoke_files_count": smoke_files_count,
        }

    # parse 실패 또는 release note 부재
    return {
        "cumulative_total": 0,
        "cumulative_pass": 0,
        "cumulative_pass_rate": 0.0,
        "self_referential_excluded": 0,
        "effective_total": 0,
        "effective_pass": 0,
        "effective_pass_rate": 0.0,
        "recent_releases": recent,
        "smoke_files_count": smoke_files_count,
    }


def _parse_self_gate_excluded(release_path: Path) -> int:
    """release note 의 자기참조 게이트 제외 수 (없으면 0)."""
    try:
        content = release_path.read_text(encoding="utf-8")
    except OSError:
        return 0
    m = SMOKE_SELF_GATE_PATTERN.search(content)
    return int(m.group(1)) if m else 0


def _parse_smoke_count_from_release(release_path: Path) -> tuple[int, int] | None:
    """release note 본문에서 누적 smoke count 패턴 parse.

    v0.15.0+ 확장: 두 가지 표기 모두 지원.
    - 형식 1: ``누적 smoke test **N/N PASS**`` (v0.13.0 정공법)
    - 형식 2: ``누적 smoke **N+ PASS**`` (v0.14.1+ 슬랙 표기 — pass=total 가정)
    형식 2 의 N+ 는 release note 가 이미 100% pass 를 단언했음을 의미하므로
    (N, N) 으로 정규화.
    """
    try:
        with release_path.open("r", encoding="utf-8") as fp:
            content = fp.read()
    except OSError:
        return None
    match = SMOKE_COUNT_PATTERN.search(content)
    if match is None:
        return None
    try:
        pass_count = int(match.group(1))
        # group(2) 는 N/N 표기일 때만 존재; N+ 표기일 때는 None
        total_str = match.group(2)
        total_count = int(total_str) if total_str is not None else pass_count
        return pass_count, total_count
    except ValueError:
        return None


# 자기참조 게이트 제외 표기 파서.
# `quality_dashboard` Panel 4 와 `smoke_trend_cross` case_5 는 "전량 PASS" 를 요구하는데
# **자기 자신도 전량에 포함**되어 있다. 따라서 두 게이트가 red 인 한 pass != total 이고,
# pass == total 이 되려면 두 게이트가 green 이어야 하는 순환이 생긴다. 실제로 과거
# release note 들이 이 게이트를 통과했던 것은 전량이 아니라 *일부만* 세어 적었기
# 때문이며, 전량을 정직하게 기록한 순간 게이트는 만족 불가능해졌다.
#
# 해결: 원 수치(N/M)는 그대로 두고, **제외 대상을 note 에 명시**해 실효 지표를 따로 낸다.
# 숫자를 줄여 적는 것이 아니라 무엇을 왜 뺐는지 감사 가능하게 남기는 방식이다.
SMOKE_SELF_GATE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^-\s*smoke\s*자기참조\s*게이트\s*제외:\s*(\d+)", re.MULTILINE
)


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
    extra_roots: tuple[Path, ...] | None = None,
) -> dict[str, Any]:
    """state.json.session.recent_done_items 의 상위 N 개 item 을 timeline 으로 emit.

    Fields:
        items_total: recent_done_items 전체 갯수
        top_n: emit 한 item 갯수 (default = 10)
        timeline: [{index: int, preview: str (≤120 char), length: int}, ...]

    Returns:
        dict — Panel 5 의 data shape.

    v0.15.20+: ``extra_roots`` 는 *같은 저장소의 다른 worktree 경로* 모음. 생략 시
    `self_root` 의 `git worktree list --porcelain` 결과 + `WORKFLOW_EXTRA_ROOTS`
    env 로 자동 보강한다. (registry 도입 시 registry 가 이 인자를 만들어주는 자리가 된다.)
    """
    root = _repo_root(workspace_root)
    # v1.0.0 branch-scoped: 메모리가 `active/<branch>/` 로 분리되므로 Panel 5 는 **모든
    # 브랜치의 state.json 을 집계** 한 뷰로 만든다. 이렇게 하면 main 전용 집계 파일을
    # 따로 커밋할 필요가 없어, protected main 에서도 merge 마다 갱신할 대상이 없다.
    if extra_roots is None:
        # 0-config: 자기 worktree 외 + env 기반 추가 + registry(§7.1) 가 알려주는
        # 호스트 워크스페이스 경로. registry 부재 시 자동 fallback (빈 리스트).
        extras = [
            *_auto_extra_roots(root),
            *_env_extra_roots(),
            *_registry_extra_roots(root),
        ]
    else:
        extras = list(extra_roots)
    state_paths = _branch_state_paths(root, *extras)
    if not state_paths:
        legacy = state_path_for_workspace(root)
        state_paths = [legacy] if legacy.is_file() else []

    if not state_paths:
        return {"items_total": 0, "top_n": top_n, "timeline": [], "confidence_counts": {}}

    # §0.8 #2 / §5A.3 — in-flight 신뢰도 (3-way signal). registry + worktree branch +
    # system path existence. 한 번만 호출 (per-collect).
    branch_map = _worktree_branch_map(root)
    registry_entries: list[Any] = []
    try:
        from workflow_kit.common import workspace_registry as _wr  # noqa: PLC0415
        registry_entries = _wr.list_entries()
    except Exception:  # noqa: BLE001 — registry 부재/실패 시 조용히 fresh 로 fallback
        registry_entries = []

    items: list[Any] = []
    item_confidences: list[str] = []  # items 와 1:1 대응
    for path in state_paths:
        try:
            with path.open("r", encoding="utf-8") as fp:
                state = json.load(fp)
        except (OSError, json.JSONDecodeError):
            continue
        session = state.get("session", {})
        if not isinstance(session, dict):
            continue
        branch_items = session.get("recent_done_items", [])
        if isinstance(branch_items, list):
            conf = _confidence_for_state_path(
                path,
                main_root=root,
                registry_entries=registry_entries,
                branch_map=branch_map,
            )
            for it in branch_items:
                items.append(it)
                item_confidences.append(conf)

    timeline: list[dict[str, Any]] = []
    confidence_counts: dict[str, int] = {}
    for idx, (item, conf) in enumerate(zip(items[:top_n], item_confidences[:top_n])):
        if isinstance(item, str):
            preview = item[:120] + ("…" if len(item) > 120 else "")
            timeline.append(
                {
                    "index": idx,
                    "preview": preview,
                    "length": len(item),
                    "confidence": conf,
                }
            )
            confidence_counts[conf] = confidence_counts.get(conf, 0) + 1

    return {
        "items_total": len(items),
        "top_n": top_n,
        "timeline": timeline,
        # §0.8 #2 — Panel 5 summary: 4-level 분포. 0인 enum 도 emit (render 가
        # "fresh: 5, recent: 0, stale: 0, orphan: 0" 으로 일관 표시).
        "confidence_counts": {
            level: confidence_counts.get(level, 0)
            for level in ("fresh", "recent", "stale", "orphan")
        },
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
        workspace_root: workspace root. None 이면 **cwd** (v1.0.7+, 모듈 위치 추측 ❌).
            어느 쪽이었는지는 결과의 `workspace_root_source` 에 남는다.
        inline_guard: True 면 Panel 1 의 drift guard 를 subprocess 로 inline 실행.
            False 면 legacy v0.13.0 behavior (guard_status='unknown').
    """
    ws_root, ws_source = resolve_workspace_root(workspace_root)
    return {
        "schema_version": "1.1",  # v0.14.3 Phase 15 — Panel 6/7/8 추가
        "tool_version": _workflow_kit_version(),
        "generated_at": _utcnow_iso(),
        "workspace_root": str(ws_root),
        # v1.0.7(§2.51): 값 옆에 출처. 어디를 쟀는지가 명시였는지 cwd 였는지 모르면
        # 빈 panel 이 "그 workspace 에 아무것도 없다" 인지 "엉뚱한 데를 쟀다" 인지
        # 구별되지 않는다.
        "workspace_root_source": ws_source,
        "panels": {
            "drift_prevention": collect_drift_prevention(ws_root, inline_guard=inline_guard),
            "maturity_distribution": collect_maturity_distribution(ws_root),
            "memory_index_utilization": collect_memory_index_utilization(ws_root),
            "smoke_trend": collect_smoke_trend(ws_root),
            "recent_releases": collect_recent_releases(ws_root),
            # Phase 15 (v0.14.3+) Panel 6/7/8 — north-star metrics
            "multi_agent_concurrent_write_conflict": collect_multi_agent_concurrent_write_conflict(ws_root),
            "deprecation_cycle_progress": collect_deprecation_cycle_progress(ws_root),
            "memory_index_utilization_v2": collect_memory_index_utilization_v2(ws_root),
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


__all__: list[str] = [
    "collect_drift_prevention",
    "collect_maturity_distribution",
    "collect_memory_index_utilization",
    "collect_smoke_trend",
    "collect_recent_releases",
    "collect_dashboard_snapshot",
    "resolve_workspace_root",
    "WORKSPACE_SOURCE_ARGUMENT",
    "WORKSPACE_SOURCE_CWD",
    "render_dashboard_markdown",
    "render_dashboard_html",
    "run_drift_prevention_guard_inline",
    "SMOKE_COUNT_PATTERN",
    "EXPECTED_DRIFT_GUARD_CASES",
    "DEFAULT_RECENT_RELEASES",
    "DRIFT_GUARD_INLINE_TIMEOUT",
    "CHARTJS_CDN_URL",
    # 분리 module 재-export (mypy no_implicit_reexport + ruff F401 정합)
    "_render_panel_1",
    "_render_panel_2",
    "_render_panel_3",
    "_render_panel_4",
    "_render_panel_5",
    "_render_panel_6",
    "_render_panel_7",
    "_render_panel_8",
    "_branch_state_paths",
    "_auto_extra_roots",
    "_env_extra_roots",
    "_worktree_branch_map",
    "_state_path_to_worktree_root",
    "_confidence_for_state_path",
    "_registry_extra_roots",
]
