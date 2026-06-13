"""workflow_kit.cli.doctor — v0.7.4 CLI wrapper for 7 baseline compliance evaluation.

Usage:
    python -m workflow_kit.cli.doctor                       # all 7 baseline
    python -m workflow_kit.cli.doctor --baseline=security   # 1 baseline
    python -m workflow_kit.cli.doctor --json                # JSON output
    python -m workflow_kit.cli.doctor --pretty              # pretty table
    python -m workflow_kit.cli.doctor --exit-on-fail       # exit 1 if non_compliant

v0.7.3 의 7 baseline dispatcher (security / testing / performance / security-auth /
testing-property-based / performance-memory / resiliency) 를 CLI 로 expose.
v0.7.4 추가: 7 baseline 통합 evaluate_all + pretty table 출력 + --exit-on-fail.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Resolve project_root default
DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

# 7 baseline dispatcher
ALL_BASELINES = [
    "security",
    "testing",
    "performance",
    "security-auth",
    "testing-property-based",
    "performance-memory",
    "resiliency",
]


def evaluate(project_root: Path, baseline: str | None = None) -> dict:
    """7 baseline compliance 평가 (single or all).

    Args:
        project_root: 프로젝트 루트 (state.json 위치)
        baseline: 단일 baseline name, None 이면 7 baseline 모두

    Returns:
        dict with single baseline result or all 7 baseline results
    """
    from workflow_kit.common.contracts.baselines import (
        evaluate_all,
        evaluate_compliance,
    )

    if baseline:
        cs = evaluate_compliance(project_root, baseline)
        return {baseline: cs.to_dict()}

    all_summaries = evaluate_all(project_root)
    return {name: cs.to_dict() for name, cs in all_summaries.items()}


def render_pretty(results: dict) -> str:
    """7 baseline 결과를 사람이 읽기 좋은 table 로."""
    lines = []
    lines.append("=" * 78)
    lines.append(f" Workflow Doctor — 7 Baseline Compliance Report")
    lines.append("=" * 78)
    for baseline_name, cs in results.items():
        # status icon
        status_icon = {
            "compliant": "✓",
            "advisory": "△",
            "non_compliant": "✗",
            "not_applicable": "—",
        }.get(cs["status"], "?")

        lines.append(f"\n[{status_icon}] {baseline_name}: {cs['status']}")
        if cs.get("partial_rules"):
            lines.append(f"   partial rules: {', '.join(cs['partial_rules'])}")
        lines.append(f"   {'rule_id':<14} {'title':<40} {'status':<14}")
        lines.append(f"   {'-' * 70}")
        for r in cs["results"]:
            icon = {
                "compliant": "✓",
                "advisory": "△",
                "non_compliant": "✗",
                "not_applicable": "—",
            }.get(r["status"], "?")
            title_short = r["title"][:38] + ".." if len(r["title"]) > 40 else r["title"]
            lines.append(f"   {icon} {r['rule_id']:<12} {title_short:<40} {r['status']:<14}")
            if r.get("notes"):
                notes_short = r["notes"][:70] + "..." if len(r["notes"]) > 70 else r["notes"]
                lines.append(f"      └─ {notes_short}")
    lines.append("\n" + "=" * 78)
    # summary
    total = sum(len(cs["results"]) for cs in results.values())
    compliant = sum(
        1
        for cs in results.values()
        for r in cs["results"]
        if r["status"] == "compliant"
    )
    non_compliant = sum(
        1
        for cs in results.values()
        for r in cs["results"]
        if r["status"] == "non_compliant"
    )
    advisory = sum(
        1
        for cs in results.values()
        for r in cs["results"]
        if r["status"] == "advisory"
    )
    lines.append(
        f" Summary: {total} rule total, "
        f"{compliant} compliant, "
        f"{advisory} advisory, "
        f"{non_compliant} non_compliant"
    )
    lines.append("=" * 78)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="workflow-doctor",
        description="Workflow 7 baseline compliance evaluator (v0.7.4+)",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=DEFAULT_PROJECT_ROOT,
        help=f"프로젝트 루트 경로 (default: {DEFAULT_PROJECT_ROOT})",
    )
    parser.add_argument(
        "--baseline",
        choices=ALL_BASELINES + ["all"],
        default="all",
        help="평가할 baseline (default: all)",
    )
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("--json", action="store_true", help="JSON 출력")
    output_group.add_argument("--pretty", action="store_true", help="테이블 형식 출력 (default)")
    parser.add_argument(
        "--exit-on-fail",
        action="store_true",
        help="non_compliant 발견 시 exit 1",
    )

    args = parser.parse_args(argv)
    baseline = None if args.baseline == "all" else args.baseline

    try:
        results = evaluate(args.project_root, baseline)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        # pretty = default
        print(render_pretty(results))

    if args.exit_on_fail:
        for cs in results.values():
            if cs["status"] == "non_compliant":
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
