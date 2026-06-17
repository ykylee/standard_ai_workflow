"""Consumer feedback metrics snapshot (v0.7.58+) + trend (v0.7.62+) + digest (v0.7.62+).

Reports consumer feedback signal sources:
1. GH Pages traffic (via gh API traffic/views + traffic/clones)
2. GitHub issues with consumer-feedback label
3. GitHub discussions
4. Recent releases

Use case: weekly / monthly snapshot of consumer engagement. Pure read-only,
no side effects (record-snapshot writes to local history file, not to remote).

Usage (v0.7.58+):
    python3 tools/consumer_metrics.py [--json] [--days=14] [--repo=OWNER/REPO]

Usage (v0.7.62+ — trend snapshot + weekly digest):
    python3 tools/consumer_metrics.py --record              # 현재 snapshot 을 history 에 기록
    python3 tools/consumer_metrics.py --show-trend           # history 의 views_total 추세 chart
    python3 tools/consumer_metrics.py --show-trend=clones_total  # clones 추세 chart
    python3 tools/consumer_metrics.py --digest              # 7일 Slack-style text summary
    python3 tools/consumer_metrics.py --digest --digest-markdown  # GH issue comment markdown

Trend history file: tools/.consumer_metrics_history.jsonl (per-line snapshot).
Follows v0.7.1+ score_wiki_trend.py 의 jsonl pattern (1 commit 1 line).

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
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
HISTORY_PATH = SOURCE_ROOT / "tools" / ".consumer_metrics_history.jsonl"

# trend chart dim (mappable from snapshot)
TREND_DIMS = ["views_total", "views_uniques", "clones_total", "feedback_total", "feedback_open"]

# weekly digest lookback
DIGEST_DAYS_DEFAULT = 7


def _gh_api(endpoint: str, repo: str) -> dict | list:
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


# ---------------------------------------------------------------------------
# v0.7.62+ — trend snapshot (record + chart)
# ---------------------------------------------------------------------------
def record_snapshot(metrics: dict, history_path: Path = HISTORY_PATH) -> dict:
    """Append current snapshot to history jsonl (1 line 1 snapshot).

    History schema per line:
        {
          "snapshot_at": "<iso8601>",
          "repo": "owner/repo",
          "days": 14,
          "views_total": int,
          "views_uniques": int,
          "clones_total": int,
          "feedback_total": int,
          "feedback_open": int,
          "releases_recent_count": int,
        }
    """
    cf = metrics["consumer_feedback"]
    record = {
        "snapshot_at": metrics["snapshot_at"],
        "repo": metrics["repo"],
        "days": metrics["days"],
        "views_total": metrics["gh_pages"]["views_total"],
        "views_uniques": metrics["gh_pages"]["views_uniques"],
        "clones_total": metrics["gh_clones"]["clones_total"],
        "feedback_total": cf["total"],
        "feedback_open": cf["open"],
        "releases_recent_count": len(metrics["releases_recent"]),
    }
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
    return record


def load_history(history_path: Path = HISTORY_PATH) -> list[dict]:
    """Load history from jsonl. Missing file returns empty list."""
    if not history_path.exists():
        return []
    records: list[dict] = []
    for line in history_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def ascii_trend(records: list[dict], dim: str = "views_total") -> str:
    """ASCII chart: x=snapshot_at (date), y=value.

    Mirrors score_wiki_trend.ascii_chart 의 정신 (bar chart).
    - x축: YYYY-MM-DD (snapshot_at 의 date prefix)
    - y축: dim value (auto-scaled 0~max)
    """
    if dim not in TREND_DIMS:
        return f"(unknown dim: {dim}. valid: {TREND_DIMS})"
    if not records:
        return "(no records)"
    rows = []
    values = [r.get(dim, 0) for r in records]
    max_v = max(values) if values else 0
    if max_v == 0:
        max_v = 1  # avoid div/0
    for r in records:
        snapshot_at = r.get("snapshot_at", "")
        date = snapshot_at[:10] if snapshot_at else "?"
        v = r.get(dim, 0)
        bar_len = int(v / max_v * 30)
        bar = "█" * bar_len + "░" * (30 - bar_len)
        rows.append(f"  {date}  {v:>6}  {bar}")
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# v0.7.62+ — weekly digest
# ---------------------------------------------------------------------------
def format_digest(metrics: dict) -> str:
    """Slack-style text summary of metrics.

    한눈에 보기 (Slack mrkdwn 기준):
    *Consumer digest ({days}d, {repo})*
    • views_total: {N}  ({delta vs prior})
    • clones_total: {N}
    • feedback: {N} ({open} open, {closed} closed)
    • releases: {N}
    """
    gp = metrics["gh_pages"]
    cf = metrics["consumer_feedback"]
    days = metrics["days"]
    return (
        f"*Consumer digest ({days}d, {metrics['repo']})*\n"
        f"• views_total: {gp['views_total']}  ({gp['views_uniques']} unique)\n"
        f"• clones_total: {metrics['gh_clones']['clones_total']}\n"
        f"• feedback: {cf['total']} ({cf['open']} open, {cf['closed']} closed)\n"
        f"• releases: {len(metrics['releases_recent'])}\n"
    )


def format_digest_markdown(metrics: dict) -> str:
    """GH issue comment markdown summary.

    형식: GitHub issue comment 와 정합 (h2 heading + table).
    """
    gp = metrics["gh_pages"]
    cf = metrics["consumer_feedback"]
    days = metrics["days"]
    rows = [
        f"## Consumer digest — {days}d window ({metrics['repo']})",
        "",
        f"_snapshot_at: {metrics['snapshot_at']}_",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| GH Pages views (total) | {gp['views_total']} |",
        f"| GH Pages views (unique) | {gp['views_uniques']} |",
        f"| GH Clones (total) | {metrics['gh_clones']['clones_total']} |",
        f"| Consumer feedback issues (total) | {cf['total']} |",
        f"| Consumer feedback (open) | {cf['open']} |",
        f"| Consumer feedback (closed) | {cf['closed']} |",
        f"| Recent releases | {len(metrics['releases_recent'])} |",
    ]
    if metrics["releases_recent"]:
        rows += ["", "### Recent releases", ""]
        for r in metrics["releases_recent"][:5]:
            rows.append(f"- **{r['tag']}** — {r['name']}  ({r['published_at']})")
    if cf.get("issues"):
        rows += ["", "### Open feedback issues", ""]
        for issue in cf["issues"]:
            if issue.get("state") == "OPEN":
                rows.append(
                    f"- #{issue['number']} {issue['title']}  "
                    f"_(created {issue.get('createdAt', '')})_"
                )
    return "\n".join(rows) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", default="ykylee/standard_ai_workflow", help="owner/repo")
    parser.add_argument("--days", type=int, default=14, help="lookback window in days (default 14)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    # v0.7.62+ — trend snapshot + weekly digest flags
    parser.add_argument("--record", action="store_true", help="현재 snapshot 을 history jsonl 에 기록 (v0.7.62+)")
    parser.add_argument("--show-trend", nargs="?", const="views_total", default=None,
                        help=f"history 의 trend chart 출력 (v0.7.62+). default dim: views_total. valid: {TREND_DIMS}")
    parser.add_argument("--history-path", default=str(HISTORY_PATH),
                        help=f"history jsonl path (default: {HISTORY_PATH}, v0.7.62+)")
    parser.add_argument("--digest", action="store_true", help="weekly digest text 출력 (v0.7.62+)")
    parser.add_argument("--digest-markdown", action="store_true",
                        help="GH issue comment markdown 형식 digest (v0.7.62+)")
    args = parser.parse_args()
    if args.days < 1 or args.days > 90:
        print("ERROR: --days must be 1-90", file=sys.stderr)
        return 2
    history_path = Path(args.history_path)
    # v0.7.62+ — trend show 는 gh API 호출 없이 history 에서만 계산 (offline 가능)
    if args.show_trend is not None:
        records = load_history(history_path)
        if not records:
            print(f"(no history yet at {history_path}; --record 로 snapshot 기록 후 사용)", file=sys.stderr)
            return 0
        print(f"Consumer feedback trend (dim={args.show_trend}, {len(records)} snapshots)")
        print(ascii_trend(records, args.show_trend))
        return 0
    # v0.7.62+ — 나머지 명령 (--record / --digest / --digest-markdown / default) 는 gh API 호출
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
    # v0.7.62+ — record branch (snapshot 을 history 에 append)
    if args.record:
        record = record_snapshot(metrics, history_path)
        print(f"Recorded snapshot to {history_path}")
        print(f"  views_total={record['views_total']} clones_total={record['clones_total']} feedback_total={record['feedback_total']}")
        return 0
    # v0.7.62+ — digest branch
    if args.digest or args.digest_markdown:
        if args.digest_markdown:
            print(format_digest_markdown(metrics))
        else:
            print(format_digest(metrics))
        return 0
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
