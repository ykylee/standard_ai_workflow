#!/usr/bin/env python3
"""Smoke test — Panel 1+2 maturity_distribution cross-validation (v0.15.8+).

Panel 1 (drift_prevention) + Panel 2 (maturity_distribution) 의 metric 들을
maturity_matrix.json + git log 와 cross-check. v1.0.0 진입 평가의 cross-panel
discipline anchor.

4 cases:
  1) **Panel 2 skills 정합**: Panel 2 skills.total == maturity_matrix.json
     `skills` key 갯수 + `by_stage.stable` == stable 인 skill 갯수 (각 skill 의
     `stage == "stable"` 직접 카운트).
  2) **Panel 2 mcp_tools 정합**: Panel 2 mcp.total == maturity_matrix.json
     `mcp_tools` key 갯수 + `by_stage.{stable, removed}` 분해 == maturity_matrix
     의 stage 분포.
  3) **Panel 2 milestones 정합**: Panel 2 milestones.total ==
     maturity_matrix.json `milestones` key 갯수 + `by_status.{done, in_progress}`
     분해 == maturity_matrix status 분포.
  4) **Panel 1+2 harness + maturity_last_updated 정합**: Panel 1
     `harness_supported_count` == Panel 2 `harnesses.supported` ==
     maturity_matrix.json `harnesses.supported` list 길이 + Panel 1
     `maturity_last_updated` == maturity_matrix.json `last_updated` + Panel 1
     `head_commit_date` == `git log -1` 의 commit date.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
MATURITY_PATH = SOURCE_ROOT / "core" / "maturity_matrix.json"


def _collect_dashboard() -> dict:
    """workflow_kit_cli dashboard --format=json subprocess 호출."""
    proc = subprocess.run(
        [sys.executable, "-m", "workflow_kit.workflow_kit_cli",
         "--command=dashboard", "--format=json"],
        cwd=str(REPO_ROOT),
        env={"PYTHONPATH": str(SOURCE_ROOT), "PATH": __import__("os").environ.get("PATH", "")},
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"dashboard --format=json failed: {proc.stderr[:300]}")
    return json.loads(proc.stdout)


def _load_maturity_matrix() -> dict:
    """maturity_matrix.json dict 반환."""
    if not MATURITY_PATH.is_file():
        raise AssertionError(f"maturity_matrix 부재: {MATURITY_PATH}")
    return json.loads(MATURITY_PATH.read_text(encoding="utf-8"))


def _git_head_commit_date() -> str:
    """git log -1 commit date (ISO date)."""
    proc = subprocess.run(
        ["git", "log", "-1", "--format=%cd", "--date=short"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git log failed: {proc.stderr[:200]}")
    return proc.stdout.strip()


def case_1_panel_2_skills() -> bool:
    """1) Panel 2 skills 정합: total + by_stage.stable == maturity_matrix skills."""
    d = _collect_dashboard()
    panel_skills = d["panels"]["maturity_distribution"]["skills"]
    panel_total = int(panel_skills.get("total", 0))
    panel_stable = int(panel_skills.get("stable", 0))
    mm = _load_maturity_matrix()
    mm_skills = mm.get("skills", {})
    if panel_total != len(mm_skills):
        print(f"  FAIL: panel skills total={panel_total} != maturity_matrix skills keys={len(mm_skills)}")
        return False
    actual_stable = sum(1 for k, v in mm_skills.items() if isinstance(v, dict) and v.get("stage") == "stable")
    if panel_stable != actual_stable:
        print(f"  FAIL: panel skills stable={panel_stable} != actual stable count={actual_stable}")
        return False
    print(f"  [info] skills: panel total={panel_total}, stable={panel_stable}, mm keys={len(mm_skills)}")
    return True


def case_2_panel_2_mcp_tools() -> bool:
    """2) Panel 2 mcp_tools 정합: total + by_stage.{stable, removed} == maturity_matrix mcp_tools."""
    d = _collect_dashboard()
    panel_mcp = d["panels"]["maturity_distribution"]["mcp_tools"]
    panel_total = int(panel_mcp.get("total", 0))
    panel_stable = int(panel_mcp.get("stable", 0))
    panel_by_stage = panel_mcp.get("by_stage", {})
    mm = _load_maturity_matrix()
    mm_mcp = mm.get("mcp_tools", {})
    if panel_total != len(mm_mcp):
        print(f"  FAIL: panel mcp total={panel_total} != maturity_matrix mcp_tools keys={len(mm_mcp)}")
        return False
    # stage 분포
    actual_by_stage: dict[str, int] = {}
    for k, v in mm_mcp.items():
        if isinstance(v, dict):
            stage = v.get("stage", "unknown")
            actual_by_stage[stage] = actual_by_stage.get(stage, 0) + 1
    # panel by_stage 와 actual stage 분포 정합
    for stage, count in actual_by_stage.items():
        if panel_by_stage.get(stage, 0) != count:
            print(f"  FAIL: panel mcp by_stage[{stage!r}]={panel_by_stage.get(stage, 0)} != actual={count}")
            return False
    # panel by_stage 의 stage 가 actual 에 있는지 (panel 에만 있는 stage 는 fail)
    for stage in panel_by_stage:
        if stage not in actual_by_stage:
            print(f"  FAIL: panel by_stage[{stage!r}]={panel_by_stage[stage]} (maturity_matrix 에 부재)")
            return False
    print(f"  [info] mcp_tools: total={panel_total}, stable={panel_stable}, by_stage={dict(panel_by_stage)}, actual={actual_by_stage}")
    return True


def case_3_panel_2_milestones() -> bool:
    """3) Panel 2 milestones 정합: total + by_status.{done, in_progress} == maturity_matrix milestones."""
    d = _collect_dashboard()
    panel_ms = d["panels"]["maturity_distribution"]["milestones"]
    panel_total = int(panel_ms.get("total", 0))
    panel_done = int(panel_ms.get("done", 0))
    panel_in_progress = int(panel_ms.get("in_progress", 0))
    panel_by_status = panel_ms.get("by_status", {})
    mm = _load_maturity_matrix()
    mm_milestones = mm.get("milestones", {})
    if panel_total != len(mm_milestones):
        print(f"  FAIL: panel milestones total={panel_total} != maturity_matrix milestones keys={len(mm_milestones)}")
        return False
    actual_by_status: dict[str, int] = {}
    for k, v in mm_milestones.items():
        if isinstance(v, dict):
            status = v.get("status", "unknown")
            actual_by_status[status] = actual_by_status.get(status, 0) + 1
    for status, count in actual_by_status.items():
        if panel_by_status.get(status, 0) != count:
            print(f"  FAIL: panel by_status[{status!r}]={panel_by_status.get(status, 0)} != actual={count}")
            return False
    for status in panel_by_status:
        if status not in actual_by_status:
            print(f"  FAIL: panel by_status[{status!r}]={panel_by_status[status]} (maturity_matrix 에 부재)")
            return False
    print(f"  [info] milestones: total={panel_total}, done={panel_done}, in_progress={panel_in_progress}, by_status={dict(panel_by_status)}")
    return True


def case_4_panel_1_plus_2_harness_and_last_updated() -> bool:
    """4) Panel 1+2 harness + maturity_last_updated 정합."""
    d = _collect_dashboard()
    panel_1 = d["panels"]["drift_prevention"]
    panel_2 = d["panels"]["maturity_distribution"]
    p1_harness = int(panel_1.get("harness_supported_count", -1))
    p2_harness = int(panel_2["harnesses"].get("supported", -1))
    p1_maturity = str(panel_1.get("maturity_last_updated", ""))
    p1_head = str(panel_1.get("head_commit_date", ""))
    mm = _load_maturity_matrix()
    mm_harness_list = mm.get("harnesses", {}).get("supported", [])
    mm_last_updated = str(mm.get("last_updated", ""))
    # harness count 정합
    if p1_harness != p2_harness:
        print(f"  FAIL: panel 1 harness={p1_harness} != panel 2 harness={p2_harness}")
        return False
    if p1_harness != len(mm_harness_list):
        print(f"  FAIL: panel harness={p1_harness} != maturity_matrix harness list={len(mm_harness_list)}")
        return False
    # panel 2 supported_names == maturity_matrix supported list
    p2_names = set(panel_2["harnesses"].get("supported_names", []))
    mm_names = set(mm_harness_list)
    if p2_names != mm_names:
        print(f"  FAIL: panel 2 supported_names={p2_names} != maturity_matrix={mm_names}")
        return False
    # maturity_last_updated 정합
    if p1_maturity != mm_last_updated:
        print(f"  FAIL: panel 1 maturity_last_updated={p1_maturity} != maturity_matrix last_updated={mm_last_updated}")
        return False
    # head_commit_date == git log -1
    try:
        git_head = _git_head_commit_date()
    except Exception as e:
        print(f"  FAIL: git head commit date 조회 실패: {e}")
        return False
    if p1_head != git_head:
        print(f"  FAIL: panel 1 head_commit_date={p1_head} != git log -1={git_head}")
        return False
    print(f"  [info] harness: p1={p1_harness}, p2={p2_harness}, mm={len(mm_harness_list)}; maturity={p1_maturity}; head={p1_head}")
    return True


def main() -> int:
    cases = [
        ("case_1_panel_2_skills", case_1_panel_2_skills),
        ("case_2_panel_2_mcp_tools", case_2_panel_2_mcp_tools),
        ("case_3_panel_2_milestones", case_3_panel_2_milestones),
        ("case_4_panel_1_plus_2_harness_and_last_updated", case_4_panel_1_plus_2_harness_and_last_updated),
    ]
    results: list[tuple[str, bool]] = []
    for name, fn in cases:
        results.append((name, fn()))
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {name}")
    print(f"\n=== {passed}/{len(cases)} PASS ===")
    if passed != len(cases):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
