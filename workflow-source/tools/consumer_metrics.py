"""Consumer feedback metrics snapshot (v0.7.58+).

Reports consumer feedback signal sources:
1. GH Pages traffic (via gh API traffic/views + traffic/clones)
2. GitHub issues with consumer-feedback label
3. GitHub discussions
4. Recent releases

Use case: weekly / monthly snapshot of consumer engagement. Pure read-only,
no side effects.

Usage:
    python3 tools/consumer_metrics.py [--json] [--days=14] [--repo=OWNER/REPO]

Exit codes:
    0 = success (with or without issues)
    1 = gh CLI not authenticated
    2 = usage error / API error
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone


def _gh_api(endpoint: str, repo: str) -> dict | list:
    """Call gh API and return JSON. Empty dict on error."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/{endpoint}"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"WARN: gh api {endpoint} failed: {result.stderr.strip()}", file=sys.stderr)
            return {}
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"WARN: gh api {endpoint} error: {type(e).__name__}: {e}", file=sys.stderr)
        return {}


def _gh_issue_list(label: str, repo: str, state: str = "all") -> list[dict]:
    """List issues with a specific label via gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "issue", "list", "--repo", repo, "--label", label,
             "--state", state, "--json", "number,title,state,createdAt",
             "--limit", "100"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return []
        return json.loads(result.stdout) if result.stdout.strip() else []
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return []


def collect_metrics(repo: str, days: int) -> dict:
    """Collect consumer feedback metrics from multiple sources."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    # 1. GH Pages traffic (last `days` days)
    traffic_views = _gh_api("traffic/views", repo)
    traffic_clones = _gh_api("traffic/clones", repo)
    # Filter to last `days` days
    recent_views = []
    if isinstance(traffic_views, dict) and "views" in traffic_views:
        for v in traffic_views.get("views", []):
            if v.get("timestamp", "") >= cutoff[:10]:  # YYYY-MM-DD
                recent_views.append(v)
    total_views = sum(v.get("count", 0) for v in recent_views)
    total_uniques = sum(v.get("uniques", 0) for v in recent_views)
    recent_clones = []
    if isinstance(traffic_clones, dict) and "clones" in traffic_clones:
        for c in traffic_clones.get("clones", []):
            if c.get("timestamp", "") >= cutoff[:10]:
                recent_clones.append(c)
    total_clones = sum(c.get("count", 0) for c in recent_clones)
    # 2. Issues with consumer-feedback label
    feedback_issues = _gh_issue_list("consumer-feedback", repo, state="all")
    open_feedback = [i for i in feedback_issues if i.get("state") == "OPEN"]
    closed_feedback = [i for i in feedback_issues if i.get("state") == "CLOSED"]
    # 3. Recent releases (last `days` days)
    releases_data = _gh_api("releases?per_page=20", repo)
    recent_releases = []
    if isinstance(releases_data, list):
        for r in releases_data:
            if r.get("published_at", "") >= cutoff:
                recent_releases.append({
                    "tag": r.get("tag_name"),
                    "name": r.get("name"),
                    "published_at": r.get("published_at"),
                })
    return {
        "repo": repo,
        "days": days,
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "gh_pages": {
            "views_total": total_views,
            "views_uniques": total_uniques,
            "views_daily": recent_views[-days:] if len(recent_views) > days else recent_views,
        },
        "gh_clones": {
            "clones_total": total_clones,
            "clones_daily": recent_clones[-days:] if len(recent_clones) > days else recent_clones,
        },
        "consumer_feedback": {
            "total": len(feedback_issues),
            "open": len(open_feedback),
            "closed": len(closed_feedback),
            "issues": feedback_issues,
        },
        "releases_recent": recent_releases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", default="ykylee/standard_ai_workflow", help="owner/repo")
    parser.add_argument("--days", type=int, default=14, help="lookback window in days (default 14)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()
    if args.days < 1 or args.days > 90:
        print("ERROR: --days must be 1-90", file=sys.stderr)
        return 2
    # Verify gh CLI is authenticated
    try:
        r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            print("ERROR: gh CLI not authenticated. Run `gh auth login` first.", file=sys.stderr)
            return 1
    except FileNotFoundError:
        print("ERROR: gh CLI not found in PATH", file=sys.stderr)
        return 1
    metrics = collect_metrics(args.repo, args.days)
    if args.json:
        print(json.dumps(metrics, indent=2, default=str))
    else:
        gp = metrics["gh_pages"]
        cf = metrics["consumer_feedback"]
        print(f"Consumer feedback metrics ({metrics['days']} day window, repo={metrics['repo']})")
        print(f"  GH Pages views: {gp['views_total']} total, {gp['views_uniques']} unique")
        print(f"  GH Clones:      {metrics['gh_clones']['clones_total']} total")
        print(f"  Feedback issues: {cf['total']} total ({cf['open']} open, {cf['closed']} closed)")
        if metrics["releases_recent"]:
            print(f"  Recent releases: {len(metrics['releases_recent'])}")
            for r in metrics["releases_recent"][:3]:
                print(f"    - {r['tag']}: {r['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
