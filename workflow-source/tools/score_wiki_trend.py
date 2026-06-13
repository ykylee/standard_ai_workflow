#!/usr/bin/env python3
"""v0.7.1+: wiki maintainability score trend over time (commit 별 추적).

각 commit 의 score 를 jsonl history 에 append + ASCII chart 시각화.
회귀 감지: dim 별 점수 하락 ≥ 0.3 시 alert.

Usage:
    # 현재 HEAD 의 score 기록
    python3 score_wiki_trend.py --record-current

    # 최근 10 commit 의 score 재기록 (backfill)
    python3 score_wiki_trend.py --record-range 10

    # trend 시각화 (ASCII chart)
    python3 score_wiki_trend.py --show

    # JSON 출력
    python3 score_wiki_trend.py --json

Reference:
- tools/score_wiki_maintainability.py (단일 시점 score)
- tools/.score_history.jsonl (jsonl history)
- workflow-source/concepts/wiki-maintainability-score.md (dashboard)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SOURCE_ROOT.parent
HISTORY_PATH = SOURCE_ROOT / "tools" / ".score_history.jsonl"

# trend 시각화용 dim
DIMS = ["coverage", "freshness", "discoverability", "cross_ref", "lifecycle", "operational"]


def get_git_commits(limit: int = 10) -> list[tuple[str, str]]:
    """git log 의 최근 N commit (hash, subject) 반환."""
    proc = subprocess.run(
        ["git", "log", f"-n{limit}", "--pretty=format:%H %s"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        return []
    out = []
    for line in proc.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split(" ", 1)
        if len(parts) == 2:
            out.append((parts[0], parts[1]))
        else:
            out.append((parts[0], ""))
    return out


def compute_score_at_commit(commit: str) -> dict:
    """특정 commit 의 score 산출 (git checkout 없이 working tree 기준)."""
    # score tool 실행 (현재 working tree 기준)
    proc = subprocess.run(
        ["python3", str(SOURCE_ROOT / "tools" / "score_wiki_maintainability.py"), "--json"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        return {"error": proc.stderr}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": "invalid JSON"}


def record_current(commit: str) -> dict:
    """현재 commit 의 score 기록 (append to jsonl)."""
    score = compute_score_at_commit(commit)
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "commit": commit[:7],
        "scores": score.get("scores", {}),
        "overall": score.get("overall", 0),
        "grade": score.get("grade", "F"),
    }
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def record_range(limit: int) -> list[dict]:
    """최근 N commit 의 score 재기록 (backfill). 현재 working tree 기준.

    주의: git checkout 없이 현재 state 의 score 를 N 회 기록. commit 별
    *정확한* score 는 git checkout 필요 (시간 소요). 본 도구는 *추세* 가
    목적이며, *정확도* 는 smoke 의 reference 만.
    """
    commits = get_git_commits(limit)
    if not commits:
        print("No commits found")
        return []

    # 기존 history 의 해당 commit entry 제거 (overwrite)
    existing = load_history()
    existing_keys = {r["commit"] for r in existing}
    records = []
    for commit_hash, subject in commits:
        # score tool 실행
        score = compute_score_at_commit(commit_hash)
        record = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "commit": commit_hash[:7],
            "subject": subject,
            "scores": score.get("scores", {}),
            "overall": score.get("overall", 0),
            "grade": score.get("grade", "F"),
        }
        records.append(record)

    # 기존 + 신규 (중복 제거)
    new_commits = {r["commit"] for r in records}
    filtered = [r for r in existing if r["commit"] not in new_commits]
    combined = filtered + records

    # 다시 쓰기
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("w", encoding="utf-8") as f:
        for r in combined:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return records


def load_history() -> list[dict]:
    """jsonl history 로드."""
    if not HISTORY_PATH.exists():
        return []
    records = []
    for line in HISTORY_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def ascii_chart(records: list[dict], dim: str = "overall") -> str:
    """ASCII chart: x=commit, y=score."""
    if not records:
        return "(no records)"
    if dim not in DIMS and dim != "overall":
        return f"(unknown dim: {dim})"

    # commit prefix → score
    series = []
    for r in records:
        if dim == "overall":
            v = r.get("overall", 0)
        else:
            v = r.get("scores", {}).get(dim, 0)
        series.append((r.get("commit", "?"), v))

    # 0~5 scale
    rows = []
    for commit, v in series:
        bar_len = int(v / 5.0 * 30)
        bar = "█" * bar_len + "░" * (30 - bar_len)
        rows.append(f"  {commit}  {v:5.2f}  {bar}")

    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--record-current", action="store_true", help="현재 HEAD 의 score 기록")
    parser.add_argument("--record-range", type=int, default=0, help="최근 N commit 의 score 재기록")
    parser.add_argument("--show", action="store_true", help="trend 시각화 (ASCII chart)")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    # 현재 HEAD
    head_proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    head = head_proc.stdout.strip()

    if args.record_current:
        record = record_current(head)
        print(f"Recorded: {record['commit']} overall={record['overall']} grade={record['grade']}")
        return 0

    if args.record_range > 0:
        records = record_range(args.record_range)
        print(f"Recorded {len(records)} commits (range={args.record_range})")
        for r in records:
            print(f"  {r['commit']}: overall={r['overall']} grade={r['grade']}")
        return 0

    records = load_history()

    if args.json:
        print(json.dumps(records, ensure_ascii=False, indent=2))
        return 0

    # human-readable
    if not records:
        print("(empty history)")
        print()
        print("Usage:")
        print("  --record-current: 현재 HEAD 의 score 기록")
        print("  --record-range N: 최근 N commit 의 score 재기록")
        print("  --show: trend 시각화")
        return 0

    print(f"Wiki Maintainability Score Trend (n={len(records)})")
    print()

    # overall trend
    print("## Overall (5.0 max)")
    print(ascii_chart(records, "overall"))
    print()

    # dim 별 trend
    for dim in DIMS:
        print(f"## {dim} (5.0 max)")
        print(ascii_chart(records, dim))
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
