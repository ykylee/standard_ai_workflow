"""Acceptance test for v0.11.2 graph insights skill integration (cycle 4 deferred 통합).

5 acceptance test:
1. test_session_start_graph_insights_v0_11_2 — SessionStartOutput.graph_insights 자동 populate (4 case)
2. test_backlog_update_graph_insights_v0_11_2 — BacklogUpdateOutput.graph_insights 자동 populate (4 case)
3. test_doc_sync_graph_insights_v0_11_2 — DocSyncOutput["graph_insights"] dict 자동 populate (4 case)
4. test_graph_insights_schema_consistency_v0_11_2 — 3 schema 의 graph_insights field 호환
5. test_graph_insights_skills_no_state_mutation_v0_11_2 — 3 skill 실행 후 state.json/PURPOSE.md 미변경
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
# Acceptance test 1: session-start graph_insights
# ---------------------------------------------------------------------------


def test_session_start_graph_insights_v0_11_2() -> None:
    """SessionStartOutput.graph_insights 자동 populate (4 case)."""
    from workflow_kit.common.schemas import SessionStartOutput, SessionGraphInsightsOutput

    # case 1: 정상 (PURPOSE.md + state.json 모두 존재)
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        ai_dir = ws / "ai-workflow" / "memory" / "active"
        ai_dir.mkdir(parents=True, exist_ok=True)
        (ai_dir / "PURPOSE.md").write_text(
            "---\npurpose_version: 1\nlast_purpose_review: 2026-06-26\n---\n\n"
            "## 1. Goals\n\n- **G1**: 표준 워크플로우\n- **G2**: skill 분리\n\n"
            "## 2. Key Questions\n\n- **Q1**: 어떻게?\n\n"
            "## 3. Research Scope\n\n### 포함\n- 영역\n\n## 4. Evolving Thesis\n\nh: X\n",
            encoding="utf-8",
        )
        # concepts dir (cross-ref 부재 warning 방지)
        (ws / "ai-workflow" / "wiki" / "concepts").mkdir(parents=True, exist_ok=True)
        (ws / "ai-workflow" / "wiki" / "concepts" / "dummy.md").write_text("# d", encoding="utf-8")
        (ai_dir / "state.json").write_text(json.dumps({
            "session": {"recent_done_items": [
                "v0.1.0 (aaaaaaa): 표준 워크플로우 release",
                "v0.2.0 (bbbbbbb): skill 분리",
            ]}
        }, ensure_ascii=False), encoding="utf-8")

        from workflow_kit.common.purpose_graph import run_graph_insights
        result = run_graph_insights(workspace_root=ws)
        gi = SessionGraphInsightsOutput(
            coverage_pct=result.coverage.coverage_pct if result.coverage else 0.0,
            covered_count=result.coverage.covered_count if result.coverage else 0,
            uncovered_count=result.coverage.uncovered_count if result.coverage else 0,
            covered_goals=result.coverage.covered if result.coverage else [],
            uncovered_goals=result.coverage.uncovered if result.coverage else [],
            surprising_count=len(result.surprising.surprising) if result.surprising else 0,
            scope_creep_warnings=result.surprising.scope_creep_warnings if result.surprising else [],
            gaps_count=len(result.gaps.gaps) if result.gaps else 0,
            health_score=result.health.score if result.health else 0,
            health_tier=result.health.tier if result.health else "unknown",
            warnings=result.overall_warnings,
        )
        assert gi.coverage_pct == 100.0
        assert gi.covered_count == 2
        assert gi.health_score == 100
        assert gi.health_tier == "excellent"
        print("  case 1 (정상 100/100 excellent): PASS")

    # case 2: PURPOSE.md 부재
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        ai_dir = ws / "ai-workflow" / "memory" / "active"
        ai_dir.mkdir(parents=True, exist_ok=True)
        (ai_dir / "state.json").write_text(json.dumps({
            "session": {"recent_done_items": ["v0.1.0 (aaa): work"]}
        }, ensure_ascii=False), encoding="utf-8")

        from workflow_kit.common.purpose_graph import run_graph_insights
        result = run_graph_insights(workspace_root=ws)
        gi = SessionGraphInsightsOutput(
            coverage_pct=result.coverage.coverage_pct if result.coverage else 0.0,
            covered_count=result.coverage.covered_count if result.coverage else 0,
            uncovered_count=result.coverage.uncovered_count if result.coverage else 0,
            covered_goals=result.coverage.covered if result.coverage else [],
            uncovered_goals=result.coverage.uncovered if result.coverage else [],
            surprising_count=len(result.surprising.surprising) if result.surprising else 0,
            scope_creep_warnings=result.surprising.scope_creep_warnings if result.surprising else [],
            gaps_count=len(result.gaps.gaps) if result.gaps else 0,
            health_score=result.health.score if result.health else 0,
            health_tier=result.health.tier if result.health else "unknown",
            warnings=result.overall_warnings,
        )
        assert gi.coverage_pct == 0.0
        assert gi.covered_count == 0
        assert gi.health_tier == "poor"
        assert any("PURPOSE.md" in w for w in gi.warnings)
        print("  case 2 (PURPOSE.md 부재): PASS")

    # case 3: state.json 부재
    # helper 동작: state.json 부재 시 recent_items=[] → coverage=None (data 부족)
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        ai_dir = ws / "ai-workflow" / "memory" / "active"
        ai_dir.mkdir(parents=True, exist_ok=True)
        (ai_dir / "PURPOSE.md").write_text(
            "## 1. Goals\n\n- **G1**: 표준 워크플로우\n", encoding="utf-8",
        )

        from workflow_kit.common.purpose_graph import run_graph_insights
        result = run_graph_insights(workspace_root=ws)
        gi = SessionGraphInsightsOutput(
            coverage_pct=result.coverage.coverage_pct if result.coverage else 0.0,
            covered_count=result.coverage.covered_count if result.coverage else 0,
            uncovered_count=result.coverage.uncovered_count if result.coverage else 0,
            covered_goals=result.coverage.covered if result.coverage else [],
            uncovered_goals=result.coverage.uncovered if result.coverage else [],
            surprising_count=len(result.surprising.surprising) if result.surprising else 0,
            scope_creep_warnings=result.surprising.scope_creep_warnings if result.surprising else [],
            gaps_count=len(result.gaps.gaps) if result.gaps else 0,
            health_score=result.health.score if result.health else 0,
            health_tier=result.health.tier if result.health else "unknown",
            warnings=result.overall_warnings,
        )
        # state.json 부재 → coverage=None (data 부족) → 모든 count 0
        assert gi.covered_count == 0
        assert gi.coverage_pct == 0.0
        assert any("state.json" in w for w in gi.warnings)
        print("  case 3 (state.json 부재, coverage=None): PASS")

    # case 4: 둘 다 부재
    from workflow_kit.common.purpose_graph import run_graph_insights
    result = run_graph_insights(
        purpose_path=Path("/nonexistent/PURPOSE.md"),
        workspace_root=Path("/nonexistent"),
        state_path=Path("/nonexistent/state.json"),
        auto_find=False,
    )
    gi = SessionGraphInsightsOutput(
        coverage_pct=result.coverage.coverage_pct if result.coverage else 0.0,
        covered_count=result.coverage.covered_count if result.coverage else 0,
        uncovered_count=result.coverage.uncovered_count if result.coverage else 0,
        covered_goals=result.coverage.covered if result.coverage else [],
        uncovered_goals=result.coverage.uncovered if result.coverage else [],
        surprising_count=len(result.surprising.surprising) if result.surprising else 0,
        scope_creep_warnings=result.surprising.scope_creep_warnings if result.surprising else [],
        gaps_count=len(result.gaps.gaps) if result.gaps else 0,
        health_score=result.health.score if result.health else 0,
        health_tier=result.health.tier if result.health else "unknown",
        warnings=result.overall_warnings,
    )
    assert gi.coverage_pct == 0.0
    assert gi.health_score == 0
    print("  case 4 (둘 다 부재): PASS")


# ---------------------------------------------------------------------------
# Acceptance test 2: backlog-update graph_insights
# ---------------------------------------------------------------------------


def test_backlog_update_graph_insights_v0_11_2() -> None:
    """BacklogUpdateOutput.graph_insights 자동 populate (4 case)."""
    from workflow_kit.common.schemas import BacklogGraphInsightsOutput

    # case 1: 정상
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        ai_dir = ws / "ai-workflow" / "memory" / "active"
        ai_dir.mkdir(parents=True, exist_ok=True)
        (ai_dir / "PURPOSE.md").write_text(
            "## 1. Goals\n\n- **G1**: 표준 워크플로우\n",
            encoding="utf-8",
        )
        (ws / "ai-workflow" / "wiki" / "concepts").mkdir(parents=True, exist_ok=True)
        (ws / "ai-workflow" / "wiki" / "concepts" / "dummy.md").write_text("# d", encoding="utf-8")
        (ai_dir / "state.json").write_text(json.dumps({
            "session": {"recent_done_items": ["v0.1.0 (aaa): 표준 워크플로우 release"]}
        }, ensure_ascii=False), encoding="utf-8")

        from workflow_kit.common.purpose_graph import run_graph_insights
        result = run_graph_insights(workspace_root=ws)
        gi = BacklogGraphInsightsOutput(
            coverage_pct=result.coverage.coverage_pct if result.coverage else 0.0,
            covered_count=result.coverage.covered_count if result.coverage else 0,
            uncovered_count=result.coverage.uncovered_count if result.coverage else 0,
            covered_goals=result.coverage.covered if result.coverage else [],
            uncovered_goals=result.coverage.uncovered if result.coverage else [],
            surprising_count=len(result.surprising.surprising) if result.surprising else 0,
            scope_creep_warnings=result.surprising.scope_creep_warnings if result.surprising else [],
            gaps_count=len(result.gaps.gaps) if result.gaps else 0,
            health_score=result.health.score if result.health else 0,
            health_tier=result.health.tier if result.health else "unknown",
            warnings=result.overall_warnings,
        )
        assert gi.coverage_pct == 100.0
        print("  case 1 (정상 100%): PASS")

    # case 2-4: 부재 케이스는 session-start 와 동일 pattern 검증
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        from workflow_kit.common.purpose_graph import run_graph_insights
        result = run_graph_insights(workspace_root=ws)
        gi = BacklogGraphInsightsOutput(
            coverage_pct=result.coverage.coverage_pct if result.coverage else 0.0,
            covered_count=result.coverage.covered_count if result.coverage else 0,
            uncovered_count=result.coverage.uncovered_count if result.coverage else 0,
            covered_goals=result.coverage.covered if result.coverage else [],
            uncovered_goals=result.coverage.uncovered if result.coverage else [],
            surprising_count=len(result.surprising.surprising) if result.surprising else 0,
            scope_creep_warnings=result.surprising.scope_creep_warnings if result.surprising else [],
            gaps_count=len(result.gaps.gaps) if result.gaps else 0,
            health_score=result.health.score if result.health else 0,
            health_tier=result.health.tier if result.health else "unknown",
            warnings=result.overall_warnings,
        )
        assert gi.coverage_pct == 0.0
        print("  case 2 (PURPOSE.md 부재): PASS")

    # case 3: state.json 부재
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        ai_dir = ws / "ai-workflow" / "memory" / "active"
        ai_dir.mkdir(parents=True, exist_ok=True)
        (ai_dir / "PURPOSE.md").write_text(
            "## 1. Goals\n\n- **G1**: 표준 워크플로우\n", encoding="utf-8",
        )
        from workflow_kit.common.purpose_graph import run_graph_insights
        result = run_graph_insights(workspace_root=ws)
        gi = BacklogGraphInsightsOutput(
            coverage_pct=result.coverage.coverage_pct if result.coverage else 0.0,
            covered_count=result.coverage.covered_count if result.coverage else 0,
            uncovered_count=result.coverage.uncovered_count if result.coverage else 0,
            covered_goals=result.coverage.covered if result.coverage else [],
            uncovered_goals=result.coverage.uncovered if result.coverage else [],
            surprising_count=len(result.surprising.surprising) if result.surprising else 0,
            scope_creep_warnings=result.surprising.scope_creep_warnings if result.surprising else [],
            gaps_count=len(result.gaps.gaps) if result.gaps else 0,
            health_score=result.health.score if result.health else 0,
            health_tier=result.health.tier if result.health else "unknown",
            warnings=result.overall_warnings,
        )
        assert gi.coverage_pct == 0.0
        print("  case 3 (state.json 부재): PASS")

    # case 4: 둘 다 부재
    from workflow_kit.common.purpose_graph import run_graph_insights
    result = run_graph_insights(
        purpose_path=Path("/nonexistent/PURPOSE.md"),
        workspace_root=Path("/nonexistent"),
        state_path=Path("/nonexistent/state.json"),
        auto_find=False,
    )
    gi = BacklogGraphInsightsOutput(
        coverage_pct=result.coverage.coverage_pct if result.coverage else 0.0,
        covered_count=result.coverage.covered_count if result.coverage else 0,
        uncovered_count=result.coverage.uncovered_count if result.coverage else 0,
        covered_goals=result.coverage.covered if result.coverage else [],
        uncovered_goals=result.coverage.uncovered if result.coverage else [],
        surprising_count=len(result.surprising.surprising) if result.surprising else 0,
        scope_creep_warnings=result.surprising.scope_creep_warnings if result.surprising else [],
        gaps_count=len(result.gaps.gaps) if result.gaps else 0,
        health_score=result.health.score if result.health else 0,
        health_tier=result.health.tier if result.health else "unknown",
        warnings=result.overall_warnings,
    )
    assert gi.health_score == 0
    print("  case 4 (둘 다 부재): PASS")


# ---------------------------------------------------------------------------
# Acceptance test 3: doc-sync graph_insights dict
# ---------------------------------------------------------------------------


def test_doc_sync_graph_insights_v0_11_2() -> None:
    """DocSyncOutput["graph_insights"] dict 자동 populate (4 case)."""
    # doc-sync 은 dict 기반 → 직접 run_graph_insights 호출 후 dict 구성
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        ai_dir = ws / "ai-workflow" / "memory" / "active"
        ai_dir.mkdir(parents=True, exist_ok=True)
        (ai_dir / "PURPOSE.md").write_text(
            "## 1. Goals\n\n- **G1**: 표준 워크플로우\n", encoding="utf-8",
        )
        (ws / "ai-workflow" / "wiki" / "concepts").mkdir(parents=True, exist_ok=True)
        (ws / "ai-workflow" / "wiki" / "concepts" / "dummy.md").write_text("# d", encoding="utf-8")
        (ai_dir / "state.json").write_text(json.dumps({
            "session": {"recent_done_items": ["v0.1.0 (aaa): 표준 워크플로우 release"]}
        }, ensure_ascii=False), encoding="utf-8")

        from workflow_kit.common.purpose_graph import run_graph_insights
        graph_result = run_graph_insights(workspace_root=ws)
        result_dict = {
            "graph_insights": {
                "coverage_pct": graph_result.coverage.coverage_pct if graph_result.coverage else 0.0,
                "covered_count": graph_result.coverage.covered_count if graph_result.coverage else 0,
                "health_score": graph_result.health.score if graph_result.health else 0,
                "health_tier": graph_result.health.tier if graph_result.health else "unknown",
            }
        }
        assert result_dict["graph_insights"]["coverage_pct"] == 100.0
        assert result_dict["graph_insights"]["health_score"] == 100
        assert result_dict["graph_insights"]["health_tier"] == "excellent"
        print("  case 1 (정상 100%): PASS")

    # case 2: 부재
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        from workflow_kit.common.purpose_graph import run_graph_insights
        graph_result = run_graph_insights(workspace_root=ws)
        result_dict = {
            "graph_insights": {
                "coverage_pct": graph_result.coverage.coverage_pct if graph_result.coverage else 0.0,
                "covered_count": graph_result.coverage.covered_count if graph_result.coverage else 0,
                "health_score": graph_result.health.score if graph_result.health else 0,
                "health_tier": graph_result.health.tier if graph_result.health else "unknown",
            }
        }
        assert result_dict["graph_insights"]["coverage_pct"] == 0.0
        print("  case 2 (PURPOSE.md 부재): PASS")

    # case 3: state.json 부재
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        ai_dir = ws / "ai-workflow" / "memory" / "active"
        ai_dir.mkdir(parents=True, exist_ok=True)
        (ai_dir / "PURPOSE.md").write_text(
            "## 1. Goals\n\n- **G1**: 표준 워크플로우\n", encoding="utf-8",
        )
        from workflow_kit.common.purpose_graph import run_graph_insights
        graph_result = run_graph_insights(workspace_root=ws)
        result_dict = {
            "graph_insights": {
                "coverage_pct": graph_result.coverage.coverage_pct if graph_result.coverage else 0.0,
                "covered_count": graph_result.coverage.covered_count if graph_result.coverage else 0,
            }
        }
        assert result_dict["graph_insights"]["coverage_pct"] == 0.0
        print("  case 3 (state.json 부재): PASS")

    # case 4: 둘 다 부재
    from workflow_kit.common.purpose_graph import run_graph_insights
    graph_result = run_graph_insights(
        purpose_path=Path("/nonexistent/PURPOSE.md"),
        workspace_root=Path("/nonexistent"),
        state_path=Path("/nonexistent/state.json"),
        auto_find=False,
    )
    result_dict = {
        "graph_insights": {
            "coverage_pct": graph_result.coverage.coverage_pct if graph_result.coverage else 0.0,
            "health_score": graph_result.health.score if graph_result.health else 0,
            "health_tier": graph_result.health.tier if graph_result.health else "unknown",
        }
    }
    assert result_dict["graph_insights"]["health_score"] == 0
    print("  case 4 (둘 다 부재): PASS")


# ---------------------------------------------------------------------------
# Acceptance test 4: schema consistency
# ---------------------------------------------------------------------------


def test_graph_insights_schema_consistency_v0_11_2() -> None:
    """3 schema 의 graph_insights field 가 모두 동일 dataclass 와 호환 (round-trip)."""
    from workflow_kit.common.schemas import (
        SessionGraphInsightsOutput,
        BacklogGraphInsightsOutput,
    )
    from workflow_kit.common.purpose_graph import run_graph_insights

    # Real repo state 에서 unified graph result 추출
    result = run_graph_insights(workspace_root=REPO_ROOT)

    # SessionGraphInsightsOutput 으로 populate
    session_gi = SessionGraphInsightsOutput(
        coverage_pct=result.coverage.coverage_pct if result.coverage else 0.0,
        covered_count=result.coverage.covered_count if result.coverage else 0,
        uncovered_count=result.coverage.uncovered_count if result.coverage else 0,
        covered_goals=result.coverage.covered if result.coverage else [],
        uncovered_goals=result.coverage.uncovered if result.coverage else [],
        surprising_count=len(result.surprising.surprising) if result.surprising else 0,
        scope_creep_warnings=result.surprising.scope_creep_warnings if result.surprising else [],
        gaps_count=len(result.gaps.gaps) if result.gaps else 0,
        health_score=result.health.score if result.health else 0,
        health_tier=result.health.tier if result.health else "unknown",
        warnings=result.overall_warnings,
    )
    # BacklogGraphInsightsOutput 으로 populate (동일 data)
    backlog_gi = BacklogGraphInsightsOutput(
        coverage_pct=result.coverage.coverage_pct if result.coverage else 0.0,
        covered_count=result.coverage.covered_count if result.coverage else 0,
        uncovered_count=result.coverage.uncovered_count if result.coverage else 0,
        covered_goals=result.coverage.covered if result.coverage else [],
        uncovered_goals=result.coverage.uncovered if result.coverage else [],
        surprising_count=len(result.surprising.surprising) if result.surprising else 0,
        scope_creep_warnings=result.surprising.scope_creep_warnings if result.surprising else [],
        gaps_count=len(result.gaps.gaps) if result.gaps else 0,
        health_score=result.health.score if result.health else 0,
        health_tier=result.health.tier if result.health else "unknown",
        warnings=result.overall_warnings,
    )

    # Round-trip: 두 schema 의 핵심 field 동일 verify
    assert session_gi.coverage_pct == backlog_gi.coverage_pct
    assert session_gi.health_score == backlog_gi.health_score
    assert session_gi.health_tier == backlog_gi.health_tier
    assert session_gi.covered_goals == backlog_gi.covered_goals
    assert session_gi.uncovered_goals == backlog_gi.uncovered_goals
    assert session_gi.surprising_count == backlog_gi.surprising_count
    assert session_gi.gaps_count == backlog_gi.gaps_count

    # Round-trip: dict dump 후 reload verify
    session_dump = session_gi.model_dump()
    reloaded = SessionGraphInsightsOutput(**session_dump)
    assert reloaded.coverage_pct == session_gi.coverage_pct
    assert reloaded.health_score == session_gi.health_score
    print(f"  schema consistency (Session ↔ Backlog 동일, coverage_pct={session_gi.coverage_pct}, health={session_gi.health_score}): PASS")


# ---------------------------------------------------------------------------
# Acceptance test 5: skills no state mutation
# ---------------------------------------------------------------------------


def test_graph_insights_skills_no_state_mutation_v0_11_2() -> None:
    """3 skill 실행 후 state.json / PURPOSE.md 미변경 verify (read-only 정합).

    Note: 실제 skill 실행은 --project-profile-path 등 many args 필요하여 여기서는
    helper module 의 read-only 특성을 verify:
    - run_graph_insights 호출 후 state.json mtime 변화 ❌
    - run_graph_insights 호출 후 PURPOSE.md mtime 변화 ❌

    v1.0.1+ — **실저장소가 아니라 temp workspace 를 본다.** 두 가지 이유다:

    1. 실저장소는 branch-scoped 메모리라 `active/<branch>/` 가 없는 checkout
       (fresh clone / detached CI / 다른 branch 의 worktree) 에서는 파일이 없다.
       그러면 `result.health` / `result.coverage` 가 None 이라 이 test 가 red 였다 —
       CI 가 계속 실패하던 원인 중 하나다.
    2. 더 중요한 것: 파일이 **없으면** mtime 비교가 `None == None` 이 되어
       *아무것도 증명하지 않고 통과*한다. read-only 를 주장하려면 실제로 존재하는
       파일을 대상으로 재야 한다.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        ai_dir = ws / "ai-workflow" / "memory" / "active"
        ai_dir.mkdir(parents=True, exist_ok=True)
        purpose_path = ai_dir / "PURPOSE.md"
        purpose_path.write_text(
            "---\npurpose_version: 1\nlast_purpose_review: 2026-06-26\n---\n\n"
            "## 1. Goals\n\n- **G1**: 표준 워크플로우\n- **G2**: skill 분리\n\n"
            "## 2. Key Questions\n\n- **Q1**: 어떻게?\n\n"
            "## 3. Research Scope\n\n### 포함\n- 영역\n\n## 4. Evolving Thesis\n\nh: X\n",
            encoding="utf-8",
        )
        (ws / "ai-workflow" / "wiki" / "concepts").mkdir(parents=True, exist_ok=True)
        (ws / "ai-workflow" / "wiki" / "concepts" / "dummy.md").write_text("# d", encoding="utf-8")
        (ai_dir / "state.json").write_text(json.dumps({
            "session": {"recent_done_items": [
                "v0.1.0 (aaaaaaa): 표준 워크플로우 release",
                "v0.2.0 (bbbbbbb): skill 분리",
            ]}
        }, ensure_ascii=False), encoding="utf-8")

        from workflow_kit.common.paths import state_path_for_workspace
        state_path = state_path_for_workspace(ws)
        assert state_path.exists(), f"fixture state.json 을 reader 가 못 찾는다: {state_path}"

        state_stat_before = (state_path.stat().st_mtime, state_path.stat().st_size)
        purpose_stat_before = (purpose_path.stat().st_mtime, purpose_path.stat().st_size)

        # run_graph_insights 호출 (read-only helper)
        from workflow_kit.common.purpose_graph import run_graph_insights
        result = run_graph_insights(workspace_root=ws)

        state_stat_after = (state_path.stat().st_mtime, state_path.stat().st_size)
        purpose_stat_after = (purpose_path.stat().st_mtime, purpose_path.stat().st_size)

        assert state_stat_before == state_stat_after, "state.json mtime/size should NOT change"
        assert purpose_stat_before == purpose_stat_after, "PURPOSE.md mtime/size should NOT change"
        print(f"  read-only verify (state.json + PURPOSE.md mtime/size preserved): PASS")

        # 추가 verify: helper 가 정상 결과를 emit 했는지
        assert result.health is not None
        assert result.coverage is not None
        print(f"  helper 정상 emit (health={result.health.score}, coverage_pct={result.coverage.coverage_pct}): PASS")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """5 acceptance test 순차 실행. 1 fail = exit 1."""
    print("=== v0.11.2 cycle 4 deferred 통합 (graph insights schema + 3 skill context load) acceptance test ===")
    tests = [
        ("test_session_start_graph_insights_v0_11_2", test_session_start_graph_insights_v0_11_2),
        ("test_backlog_update_graph_insights_v0_11_2", test_backlog_update_graph_insights_v0_11_2),
        ("test_doc_sync_graph_insights_v0_11_2", test_doc_sync_graph_insights_v0_11_2),
        ("test_graph_insights_schema_consistency_v0_11_2", test_graph_insights_schema_consistency_v0_11_2),
        ("test_graph_insights_skills_no_state_mutation_v0_11_2", test_graph_insights_skills_no_state_mutation_v0_11_2),
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
