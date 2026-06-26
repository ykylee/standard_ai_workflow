"""Acceptance test for v0.11.1 graph insights (R-A follow-up cycle 4).

8 acceptance test:
1. test_extract_goal_keywords_v0_11_1 — Goals G1+ 추출 (3 case)
2. test_parse_recent_done_items_v0_11_1 — state.json recent_done_items 파싱 (3 case)
3. test_compute_goal_coverage_v0_11_1 — Goals ↔ deliverables 매칭 (3 case)
4. test_find_surprising_deliverables_v0_11_1 — scope creep 감지 (2 case)
5. test_find_gaps_v0_11_1 — Goals 중 deliverable 0 (1 case)
6. test_compute_health_score_v0_11_1 — 4 tier verify
7. test_run_graph_insights_unified_v0_11_1 — unified entry graceful skip (4 case)
8. test_graph_insights_cli_registered_v0_11_1 — CLI subcommand 34 등록 + dry-run
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"


def _ensure_sys_path() -> None:
    if str(SOURCE_ROOT) not in sys.path:
        sys.path.insert(0, str(SOURCE_ROOT))


_ensure_sys_path()


# ---------------------------------------------------------------------------
# Acceptance test 1: extract_goal_keywords
# ---------------------------------------------------------------------------


def test_extract_goal_keywords_v0_11_1() -> None:
    """PURPOSE.md §1 Goals 의 G1+ identifier + 본문 keyword 추출."""
    from workflow_kit.common.purpose_graph import extract_goal_keywords

    # case 1: 정상 (4 goals)
    with tempfile.TemporaryDirectory() as tmpdir:
        purpose_path = Path(tmpdir) / "PURPOSE.md"
        purpose_path.write_text(
            "## 1. Goals\n\n"
            "- **G1**: 표준 워크플로우 제공\n"
            "- **G2**: skill / MCP / agent 분리\n"
            "- **G3**: SemVer 2-year guarantee\n"
            "- **G4**: deprecation 운영 약속\n",
            encoding="utf-8",
        )
        goals = extract_goal_keywords(purpose_path)
        assert len(goals) == 4
        assert goals[0].gid == "G1"
        assert "표준" in goals[0].keywords or "워크플로우" in goals[0].keywords
        assert goals[3].gid == "G4"
        print("  case 1 (정상 4 goals): PASS")

    # case 2: 한국어 keyword
    with tempfile.TemporaryDirectory() as tmpdir:
        purpose_path = Path(tmpdir) / "PURPOSE.md"
        purpose_path.write_text(
            "## 1. Goals\n\n"
            "- **G1**: 여러 프로젝트에서 공통 표준 워크플로우 제공\n",
            encoding="utf-8",
        )
        goals = extract_goal_keywords(purpose_path)
        assert len(goals) == 1
        kw = goals[0].keywords
        # 한글 keyword 추출 확인
        assert any("워크플로우" in k or "프로젝트" in k or "공통" in k for k in kw)
        print(f"  case 2 (한국어 keyword, {len(kw)} tokens): PASS")

    # case 3: empty (no G1+)
    with tempfile.TemporaryDirectory() as tmpdir:
        purpose_path = Path(tmpdir) / "PURPOSE.md"
        purpose_path.write_text(
            "## 1. Goals\n\n(no goals defined)\n",
            encoding="utf-8",
        )
        goals = extract_goal_keywords(purpose_path)
        assert goals == []
        print("  case 3 (empty): PASS")

    # case 4: 부재
    goals = extract_goal_keywords(None)
    assert goals == []
    print("  case 4 (None path): PASS")


# ---------------------------------------------------------------------------
# Acceptance test 2: parse_recent_done_items
# ---------------------------------------------------------------------------


def test_parse_recent_done_items_v0_11_1() -> None:
    """state.json recent_done_items 파싱."""
    from workflow_kit.common.purpose_graph import parse_recent_done_items

    # case 1: 정상
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "state.json"
        state_path.write_text(json.dumps({
            "session": {
                "recent_done_items": [
                    "v0.11.0 (f71dde8): two-step CoT ingest",
                    "v0.10.3 (3ca3a49): wiki file deletion cascade cleanup",
                    "v0.10.0 (c5fb94c): deprecation cycle 종료",
                ]
            }
        }, ensure_ascii=False), encoding="utf-8")
        items = parse_recent_done_items(state_path)
        assert len(items) == 3
        assert items[0].version == "v0.11.0"
        assert items[0].commit_hash == "f71dde8"
        assert "ingest" in items[0].keywords or "two-step" in items[0].keywords
        print(f"  case 1 (정상 3 items): PASS")

    # case 2: 부재
    items = parse_recent_done_items(None)
    assert items == []
    print("  case 2 (None path): PASS")

    # case 3: corrupted
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "state.json"
        state_path.write_text("{ invalid json", encoding="utf-8")
        items = parse_recent_done_items(state_path)
        assert items == []
        print("  case 3 (corrupted JSON): PASS")


# ---------------------------------------------------------------------------
# Acceptance test 3: compute_goal_coverage
# ---------------------------------------------------------------------------


def test_compute_goal_coverage_v0_11_1() -> None:
    """Goals ↔ deliverables 매칭 (3 case)."""
    from workflow_kit.common.purpose_graph import (
        extract_goal_keywords,
        parse_recent_done_items,
        compute_goal_coverage,
    )

    # case 1: 전부 covered
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        purpose = ws / "PURPOSE.md"
        purpose.write_text(
            "## 1. Goals\n\n"
            "- **G1**: 표준 워크플로우 제공\n"
            "- **G2**: skill 분리\n",
            encoding="utf-8",
        )
        state = ws / "state.json"
        state.write_text(json.dumps({
            "session": {"recent_done_items": [
                "v0.1.0 (aaaaaaa): 표준 워크플로우 release",
                "v0.2.0 (bbbbbbb): skill 분리 정공법",
            ]}
        }, ensure_ascii=False), encoding="utf-8")
        goals = extract_goal_keywords(purpose)
        items = parse_recent_done_items(state)
        cov = compute_goal_coverage(goals, items)
        assert cov.total_goals == 2
        assert cov.covered_count == 2
        assert cov.uncovered_count == 0
        assert cov.coverage_pct == 100.0
        print(f"  case 1 (전부 covered 100%): PASS")

    # case 2: 일부 covered (1 covered + 1 uncovered)
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        purpose = ws / "PURPOSE.md"
        purpose.write_text(
            "## 1. Goals\n\n"
            "- **G1**: 표준 워크플로우\n"
            "- **G2**: 추적되지 않는 목표\n",
            encoding="utf-8",
        )
        state = ws / "state.json"
        state.write_text(json.dumps({
            "session": {"recent_done_items": [
                "v0.1.0 (aaaaaaa): 표준 워크플로우 release",
            ]}
        }, ensure_ascii=False), encoding="utf-8")
        goals = extract_goal_keywords(purpose)
        items = parse_recent_done_items(state)
        cov = compute_goal_coverage(goals, items)
        assert cov.total_goals == 2
        assert cov.covered_count == 1
        assert cov.uncovered_count == 1
        assert "G2" in cov.uncovered
        assert cov.coverage_pct == 50.0
        print(f"  case 2 (1/2 covered 50%): PASS")

    # case 3: 전부 uncovered
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        purpose = ws / "PURPOSE.md"
        purpose.write_text(
            "## 1. Goals\n\n"
            "- **G1**: 표준 워크플로우\n",
            encoding="utf-8",
        )
        state = ws / "state.json"
        state.write_text(json.dumps({
            "session": {"recent_done_items": [
                "v0.1.0 (aaaaaaa): unrelated work",
            ]}
        }, ensure_ascii=False), encoding="utf-8")
        goals = extract_goal_keywords(purpose)
        items = parse_recent_done_items(state)
        cov = compute_goal_coverage(goals, items)
        assert cov.covered_count == 0
        assert cov.uncovered_count == 1
        assert cov.coverage_pct == 0.0
        print(f"  case 3 (전부 uncovered 0%): PASS")


# ---------------------------------------------------------------------------
# Acceptance test 4: find_surprising_deliverables
# ---------------------------------------------------------------------------


def test_find_surprising_deliverables_v0_11_1() -> None:
    """scope creep 감지 (2 case)."""
    from workflow_kit.common.purpose_graph import (
        GoalKeyword,
        RecentDoneItem,
        find_surprising_deliverables,
    )

    # case 1: scope_creep 의심 (Goals 매핑 0 + scope_excluded 매칭 ❌)
    goals = [GoalKeyword(gid="G1", text="G1: 표준 워크플로우", keywords=["표준", "워크플로우"])]
    items = [
        RecentDoneItem(version="v0.1", commit_hash="aaa", summary="unrelated work", keywords=["unrelated"]),
        RecentDoneItem(version="v0.2", commit_hash="bbb", summary="표준 워크플로우 release", keywords=["표준", "워크플로우"]),
    ]
    scope_excluded = ["specific domain logic"]
    result = find_surprising_deliverables(goals, items, scope_excluded)
    assert len(result.surprising) == 1
    assert "unrelated" in result.surprising[0]
    assert result.is_scope_creep[0] is True
    assert len(result.scope_creep_warnings) == 1
    print(f"  case 1 (scope_creep 의심 1): PASS")

    # case 2: scope_excluded 매칭 (out-of-scope 의도)
    goals = [GoalKeyword(gid="G1", text="G1: 표준 워크플로우", keywords=["표준", "워크플로우"])]
    items = [
        RecentDoneItem(version="v0.1", commit_hash="aaa", summary="specific domain logic", keywords=["specific", "domain", "logic"]),
    ]
    result = find_surprising_deliverables(goals, items, scope_excluded)
    assert len(result.surprising) == 1
    assert result.is_scope_creep[0] is False  # scope_excluded 매칭 → 의도된 out-of-scope
    assert result.scope_creep_warnings == []
    print(f"  case 2 (out-of-scope 의도): PASS")


# ---------------------------------------------------------------------------
# Acceptance test 5: find_gaps
# ---------------------------------------------------------------------------


def test_find_gaps_v0_11_1() -> None:
    """Goals 중 deliverable 0 인 goal 식별."""
    from workflow_kit.common.purpose_graph import (
        GoalKeyword,
        RecentDoneItem,
        find_gaps,
    )

    goals = [
        GoalKeyword(gid="G1", text="G1: 표준 워크플로우", keywords=["표준", "워크플로우"]),
        GoalKeyword(gid="G2", text="G2: skill 분리", keywords=["skill", "분리"]),
        GoalKeyword(gid="G3", text="G3: SemVer", keywords=["semver"]),
    ]
    items = [
        RecentDoneItem(version="v0.1", commit_hash="aaa", summary="skill 분리 release", keywords=["skill", "분리"]),
    ]
    gaps = find_gaps(goals, items)
    # G1 + G3 uncovered, G2 covered
    assert gaps.gaps == ["G1", "G3"]
    assert gaps.priorities == [1, 2]
    assert gaps.descriptions[0].startswith("G1:")
    assert gaps.descriptions[1].startswith("G3:")
    print(f"  case 1 (2 gaps [G1, G3], priorities [1, 2]): PASS")


# ---------------------------------------------------------------------------
# Acceptance test 6: compute_health_score
# ---------------------------------------------------------------------------


def test_compute_health_score_v0_11_1() -> None:
    """4 tier verify."""
    from workflow_kit.common.purpose_graph import (
        GoalCoverageResult,
        SurprisingResult,
        GapResult,
        compute_health_score,
    )

    # case 1: excellent (coverage 100%, no scope_creep)
    cov = GoalCoverageResult(total_goals=3, covered_count=3, partial_count=0, uncovered_count=0, coverage_pct=100.0, covered=["G1", "G2", "G3"])
    surp = SurprisingResult(surprising=[], is_scope_creep=[], scope_creep_warnings=[])
    health = compute_health_score(cov, surp, None)
    assert health.score == 100
    assert health.tier == "excellent"
    print(f"  case 1 (100/100 excellent): PASS")

    # case 2: good (coverage 50%)
    cov = GoalCoverageResult(total_goals=2, covered_count=1, partial_count=0, uncovered_count=1, coverage_pct=50.0, covered=["G1"], uncovered=["G2"])
    health = compute_health_score(cov, surp, None)
    assert health.score == 85  # 100 - 1*15 + 0
    assert health.tier == "excellent"
    print(f"  case 2 (50% coverage 85 excellent): PASS")

    # case 3: poor (many uncovered + scope creep)
    cov = GoalCoverageResult(total_goals=5, covered_count=1, partial_count=0, uncovered_count=4, coverage_pct=20.0, covered=["G1"], uncovered=["G2", "G3", "G4", "G5"])
    surp = SurprisingResult(surprising=["a", "b", "c", "d"], is_scope_creep=[True, True, True, True], scope_creep_warnings=[])
    health = compute_health_score(cov, surp, None)
    # 100 - 4*15 - 4*10 + min(4*5, 25) = 100 - 60 - 40 + 20 = 20
    assert health.score == 20
    assert health.tier == "poor"
    print(f"  case 3 (4 uncovered + 4 scope_creep = 20 poor): PASS")

    # case 4: None coverage
    health = compute_health_score(None, None, None)
    assert health.score == 0
    assert health.tier == "poor"
    print(f"  case 4 (None coverage): PASS")


# ---------------------------------------------------------------------------
# Acceptance test 7: run_graph_insights unified entry
# ---------------------------------------------------------------------------


def test_run_graph_insights_unified_v0_11_1() -> None:
    """unified entry graceful skip (4 case)."""
    from workflow_kit.common.purpose_graph import run_graph_insights

    # case 1: 정상
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        purpose = ws / "PURPOSE.md"
        purpose.write_text(
            "## 1. Goals\n\n- **G1**: 표준 워크플로우\n\n"
            "## 3. Research Scope\n\n### 제외\n- 도메인 로직\n",
            encoding="utf-8",
        )
        state = ws / "state.json"
        state.write_text(json.dumps({
            "session": {"recent_done_items": ["v0.1.0 (aaaaaaa): 표준 워크플로우 release"]}
        }, ensure_ascii=False), encoding="utf-8")
        result = run_graph_insights(
            purpose_path=purpose,
            workspace_root=ws,
            state_path=state,
            auto_find=False,
        )
        assert len(result.goal_keywords) == 1
        assert len(result.recent_items) == 1
        assert result.coverage is not None
        assert result.coverage.coverage_pct == 100.0
        print("  case 1 (정상): PASS")

    # case 2: PURPOSE.md 부재
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        state = ws / "state.json"
        state.write_text(json.dumps({
            "session": {"recent_done_items": ["v0.1.0 (aaa): work"]}
        }, ensure_ascii=False), encoding="utf-8")
        result = run_graph_insights(
            purpose_path=ws / "nonexistent.md",
            workspace_root=ws,
            state_path=state,
            auto_find=False,
        )
        assert result.goal_keywords == []
        assert result.coverage is None
        assert any("PURPOSE.md" in w for w in result.overall_warnings)
        print("  case 2 (PURPOSE.md 부재): PASS")

    # case 3: state.json 부재
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        purpose = ws / "PURPOSE.md"
        purpose.write_text(
            "## 1. Goals\n\n- **G1**: 표준 워크플로우\n",
            encoding="utf-8",
        )
        result = run_graph_insights(
            purpose_path=purpose,
            workspace_root=ws,
            state_path=ws / "nonexistent.json",
            auto_find=False,
        )
        assert result.recent_items == []
        assert result.coverage is None
        assert any("state.json" in w for w in result.overall_warnings)
        print("  case 3 (state.json 부재): PASS")

    # case 4: 둘 다 부재
    result = run_graph_insights(
        purpose_path=Path("/nonexistent/PURPOSE.md"),
        workspace_root=Path("/nonexistent"),
        state_path=Path("/nonexistent/state.json"),
        auto_find=False,
    )
    assert result.goal_keywords == []
    assert result.recent_items == []
    assert result.health is not None  # health score 는 항상 emit
    assert result.health.score == 0
    print("  case 4 (둘 다 부재): PASS")


# ---------------------------------------------------------------------------
# Acceptance test 8: cmd_graph_insights CLI 등록 + dry-run
# ---------------------------------------------------------------------------


def test_graph_insights_cli_registered_v0_11_1() -> None:
    """CLI subcommand 34 등록 + dry-run subprocess verify."""
    # dispatcher registry 에 graph-insights 등록 확인
    from workflow_kit.workflow_kit_cli import COMMANDS
    assert "graph-insights" in COMMANDS, "graph-insights subcommand not registered"
    print(f"  CLI registered (subcommand 34, total {len(COMMANDS)} commands): PASS")

    # dry-run subprocess verify (state.json 미변경)
    state_path = REPO_ROOT / "ai-workflow" / "memory" / "active" / "state.json"
    if state_path.exists():
        before = state_path.read_text(encoding="utf-8")
    else:
        before = ""

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    result = subprocess.run(
        [sys.executable, "-m", "workflow_kit.workflow_kit_cli", "--command=graph-insights"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    # state.json 미변경 확인 (read-only dispatch)
    if state_path.exists():
        after = state_path.read_text(encoding="utf-8")
        assert before == after, "state.json should NOT change in read-only graph-insights"
        print(f"  dry-run subprocess verify (state.json preserved, {len(after)} bytes): PASS")
    else:
        print("  dry-run subprocess verify (state.json not present, skipped): PASS")

    # 출력에 핵심 field 포함 확인
    assert "Graph insights" in result.stdout
    assert "coverage:" in result.stdout
    assert "health:" in result.stdout
    print("  output field completeness: PASS")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """8 acceptance test 순차 실행. 1 fail = exit 1."""
    print("=== v0.11.1 graph insights (R-A follow-up cycle 4) acceptance test ===")
    tests = [
        ("test_extract_goal_keywords_v0_11_1", test_extract_goal_keywords_v0_11_1),
        ("test_parse_recent_done_items_v0_11_1", test_parse_recent_done_items_v0_11_1),
        ("test_compute_goal_coverage_v0_11_1", test_compute_goal_coverage_v0_11_1),
        ("test_find_surprising_deliverables_v0_11_1", test_find_surprising_deliverables_v0_11_1),
        ("test_find_gaps_v0_11_1", test_find_gaps_v0_11_1),
        ("test_compute_health_score_v0_11_1", test_compute_health_score_v0_11_1),
        ("test_run_graph_insights_unified_v0_11_1", test_run_graph_insights_unified_v0_11_1),
        ("test_graph_insights_cli_registered_v0_11_1", test_graph_insights_cli_registered_v0_11_1),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n[{name}]")
        try:
            fn()
            passed += 1
            print(f"  ✓ {name} PASS")
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {name} FAIL: {e}")
        except Exception as e:
            failed += 1
            print(f"  ✗ {name} ERROR: {type(e).__name__}: {e}")

    print(f"\n=== Result: {passed}/{passed+failed} PASS ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
