"""release_pipeline.py 에서 추출한 post-release emit/format helper 모듈 (TASK-2026-08-11-main-007).

`tools/release_pipeline.py` 의 dashboard emit (v0.13.1+) / self-recovery log
format (v0.13.2+) / bidir-link audit format (v0.13.3+) helper 를 verbatim 으로
옮긴 것이다. `release_pipeline.py` 가 `from release_pipeline_emit import *` 로
전량 재-export 하므로, 기존 check / caller 는 계속 `release_pipeline` 의
attribute (`rp._emit_dashboard_post_release`, `rp._format_self_recovery_log` 등)
로 접근한다. `_emit_self_recovery_log` / `_emit_bidir_link_audit_log` /
`_append_drift_ledger_entry` 는 release_pipeline.py 의 stayed symbol
(`read_version`, `DRIFT_LEDGER_RELPATH`) 에 의존하므로 **옮기지 않고 남긴다**
(순환 import 금지). 이 모듈은 release_pipeline 을 import 하지 않는다.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# release_pipeline.py 의 REPO_ROOT 와 동일한 값 (같은 tools/ 디렉터리 기준).
# ⚠️ 이름과 달리 git 저장소 루트가 아니라 `workflow-source/` 다 (`parents[2]`).
REPO_ROOT = Path(__file__).resolve().parents[2]

__all__ = [
    "_emit_dashboard_post_release",
    "_format_self_recovery_log",
    "_format_bidir_link_audit",
]


def _emit_dashboard_post_release(args: argparse.Namespace, results: dict) -> dict:
    """gh release create 성공 후 dashboard markdown snapshot 자동 emit.

    Returns:
        dict with keys:
            status: 'ok' | 'skipped' | 'error'
            path: output file path (str, status='ok' 시)
            bytes: output file size (int, status='ok' 시)
            reason: skip reason (str, status='skipped' 시)
            error: error message (str, status='error' 시)
            executed_at: ISO 8601 timestamp (status='ok' 시)
            duration_ms: int (status='ok' 시)
    """
    skip = bool(getattr(args, "skip_dashboard_emit", False))
    if skip:
        return {"status": "skipped", "reason": "--skip-dashboard-emit"}

    # Project root = git repo root = REPO_ROOT.parent (workflow-source/tools/ 의 부모의 부모).
    # ai-workflow/ 는 project root 아래에 있으므로 dashboard CLI 의 _repo_root() 와 정합.
    project_root = REPO_ROOT.parent
    output = getattr(args, "dashboard_output", None)
    if not output:
        output = "ai-workflow/dashboard/snapshot.md"

    dashboard_path = project_root / output
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)

    cli_module = "workflow_kit.workflow_kit_cli"
    cmd = [
        sys.executable, "-m", cli_module,
        "--command=dashboard",
        "--format=markdown",
        f"--output={dashboard_path}",
    ]

    import time
    started = time.monotonic()
    # PYTHONPATH 에 workflow-source (= REPO_ROOT) 를 prepend. CI / release context
    # 에서 subprocess 가 workflow_kit 모듈을 import 할 수 있도록. check_packaging 의
    # *clean_env* 패턴의 반대 방향 — 본 helper 는 workflow_kit 이 *필요* 한 케이스.
    sub_env = os.environ.copy()
    existing_pp = sub_env.get("PYTHONPATH", "")
    sub_env["PYTHONPATH"] = (
        f"{REPO_ROOT}{os.pathsep}{existing_pp}" if existing_pp else str(REPO_ROOT)
    )
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
            env=sub_env,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        if completed.returncode != 0:
            return {
                "status": "error",
                "error": (
                    f"{cli_module} returned {completed.returncode}; "
                    f"stderr_tail: {(completed.stderr or '').strip().split(chr(10))[-1][:200]}"
                ),
            }
        if not dashboard_path.is_file():
            return {
                "status": "error",
                "error": f"{dashboard_path} not created despite rc=0",
            }
        # path 표시는 project_root 기준 relative (absolute path 입력이면 그대로 노출).
        try:
            display_path = str(dashboard_path.relative_to(project_root))
        except ValueError:
            display_path = str(dashboard_path)
        return {
            "status": "ok",
            "path": display_path,
            "bytes": dashboard_path.stat().st_size,
            "executed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration_ms": duration_ms,
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "dashboard emit timeout (60s)"}
    except (OSError, ValueError) as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


def _format_self_recovery_log(sr_result: dict) -> str:
    """cmd_self_recover 의 results dict 를 release note 본문용 markdown 문자열로 format.

    drift 가 없거나 (`recovered=[]` + `manual_required=[]`) 면 빈 문자열 반환.
    """
    recovered = sr_result.get("recovered") or []
    manual_required = sr_result.get("manual_required") or []
    re_check = sr_result.get("re_check") or {}
    if not recovered and not manual_required:
        return ""
    lines = ["", "## Self-recovery log", ""]
    lines.append(f"_자동 emit (Phase 13 AC3, {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')})_")
    lines.append("")
    if recovered:
        lines.append(f"### 자동 fix ({len(recovered)}건)")
        lines.append("")
        for r in recovered:
            case = r.get("case", "?")
            fix = r.get("fix", "?")
            res = r.get("result", {})
            file_hint = res.get("file", "")
            new_val = res.get("new", "")
            lines.append(f"- `{case}` → `{fix}`")
            if new_val:
                lines.append(f"  - new value: `{new_val}`")
            if file_hint:
                lines.append(f"  - file: `{file_hint}`")
        lines.append("")
    if manual_required:
        lines.append(f"### Manual required ({len(manual_required)}건)")
        lines.append("")
        lines.append("- " + "\n- ".join(manual_required))
        lines.append("")
    lines.append(f"_re-check status: **{re_check.get('guard_status', 'unknown')}** "
                 f"(pass={re_check.get('cases_pass', '?')}/fail={re_check.get('cases_fail', '?')}/total={re_check.get('cases_total', '?')})_")
    return "\n".join(lines) + "\n"


def _format_bidir_link_audit(audit_result: dict) -> str:
    """cmd_bidir_link audit dict → release note body markdown 문자열.

    asymmetric_count > 0 이면 비고 (advisory). 0 이면 *대칭* 표시.
    """
    audit = audit_result.get("audit") or {}
    if not audit:
        return ""
    lines = ["", "## Bidirectional link audit", ""]
    is_symmetric = bool(audit.get("is_symmetric"))
    lines.append(f"_자동 emit (Phase 13 AC4+, {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')})_")
    lines.append("")
    lines.append(f"- total wiki pages: **{audit.get('total_wiki_pages', 0)}**")
    lines.append(f"- total memory entries: **{audit.get('total_memory_entries', 0)}**")
    lines.append(f"- symmetric links: **{audit.get('symmetric_links', 0)}**")
    lines.append(f"- asymmetric count: **{audit.get('asymmetric_count', 0)}**")
    lines.append(f"- wiki pages with related memory: **{audit.get('wiki_pages_with_related_memory', 0)}**")
    lines.append(f"- memory entries with mentioned wiki: **{audit.get('memory_entries_with_mentioned_wiki', 0)}**")
    lines.append(f"- is_symmetric: **{is_symmetric}**")
    asymmetric = audit.get("asymmetric") or []
    if asymmetric:
        lines.append("")
        lines.append("### Asymmetric links (advisory)")
        lines.append("")
        for a in asymmetric[:20]:  # 최대 20건만 표시
            lines.append(f"- `{a['direction']}`: `{a['memory_entry_id']}` ↔ `{a['wiki_page']}`")
        if len(asymmetric) > 20:
            lines.append(f"- ... and {len(asymmetric) - 20} more")
    return "\n".join(lines) + "\n"
