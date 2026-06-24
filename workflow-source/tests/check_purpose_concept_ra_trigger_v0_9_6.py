"""v0.9.6 R-A follow-up part 3: wiki-event-sync R-A trigger verify.

Acceptance criteria (workflow-source/core/llm_wiki_concept_purpose_spec.md §4.4):
1. analyze_30day_distribution 가 wiki log.md 의 30일 window event 들을
   ingest / query / release 카운트 + top topics 로 분류
2. generate_llm_suggest_prompt 가 분포 + PURPOSE.md 본문을 markdown 형식으로 emit
   + advisory disclaimer 포함
3. update_last_purpose_review 가 PURPOSE.md frontmatter 의
   `last_purpose_review` date 를 갱신 (이전/현재 추적)
4. run_purpose_refresh(apply=False) 일 때 PURPOSE.md 미변경 + prompt 정상 emit
5. run_purpose_refresh(apply=True) 일 때 frontmatter 갱신 + updated=True
6. log.md 부재 / PURPOSE.md 부재 시 graceful skip + advisory warning

모든 input file 은 임시 dir 에서 생성 (저장소 file layout 의존 ❌).
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import re
import sys
import tempfile
import types
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_KIT_DIR = SOURCE_ROOT / "workflow-source" / "workflow_kit"
COMMON_DIR = WORKFLOW_KIT_DIR / "common"

# workflow_kit namespace setup
_workflow_kit_pkg = types.ModuleType("workflow_kit")
_workflow_kit_pkg.__path__ = [str(WORKFLOW_KIT_DIR)]
sys.modules.setdefault("workflow_kit", _workflow_kit_pkg)

# workflow_kit.common sub-package setup (for relative imports in purpose_refresh.py)
_workflow_kit_common_pkg = types.ModuleType("workflow_kit.common")
_workflow_kit_common_pkg.__path__ = [str(COMMON_DIR)]
sys.modules.setdefault("workflow_kit.common", _workflow_kit_common_pkg)


def _load_module(name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(name, str(WORKFLOW_KIT_DIR / file_name))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_common(name: str, file_name: str):
    """common.* 모듈을 workflow_kit.common.* 로 등록 (relative import 지원)."""
    full_name = f"workflow_kit.common.{name}"
    spec = importlib.util.spec_from_file_location(full_name, str(WORKFLOW_KIT_DIR / "common" / file_name))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    setattr(_workflow_kit_common_pkg, name, mod)
    spec.loader.exec_module(mod)
    return mod


def _make_minimal_purpose(tmp_path: Path, last_review: str = "2026-06-19") -> Path:
    """최소 형식의 PURPOSE.md (frontmatter + 4-element 본문)."""
    purpose_path = tmp_path / "PURPOSE.md"
    purpose_path.write_text(
        "---\n"
        f"purpose_version: 1\n"
        f"last_purpose_review: {last_review}\n"
        "---\n\n"
        "# Purpose — Test\n\n"
        "## 1. Goals\n"
        "- **G1**: 표준 AI 협업 워크플로우를 *독립 패키지 형태* 로 제공\n"
        "- **G2**: skill / MCP / agent 구현 기준 분리\n"
        "\n## 2. Key Questions\n"
        "- **Q1**: 어떻게 *여러 프로젝트* 가 같은 워크플로우를 적용할 수 있는가?\n"
        "\n## 3. Research Scope\n"
        "### 포함 영역\n"
        "- 공통 표준 문서\n"
        "- workflow state docs\n"
        "### 제외 영역\n"
        "- 결제 / 의료 / 금융 도메인\n"
        "- LLM model fine-tuning\n"
        "\n## 4. Evolving Thesis\n"
        "- 표준 워크플로우는 *문서 + 프로토타입 + 운영 spec* 의 3-tuple 이다\n"
    )
    return purpose_path


def _make_minimal_log(
    tmp_path: Path,
    today: dt.date,
    *,
    ingest_count: int = 5,
    query_count: int = 2,
    release_count: int = 1,
) -> Path:
    """30일 window 안 event 들이 포함된 wiki log.md (임시)."""
    log_path = tmp_path / "log.md"
    lines: list[str] = ["# Wiki Log (test)\n"]
    # 5일 전 ingest
    for i in range(ingest_count):
        d = today - dt.timedelta(days=5 - i)
        lines.append(f"## [{d.isoformat()}] ingest | phase-{i+1} — test ingest {i+1} with deprecation policy\n")
    # 7일 전 query
    for i in range(query_count):
        d = today - dt.timedelta(days=7 + i)
        lines.append(f"## [{d.isoformat()}] query | scope creep check for {i+1}\n")
    # 1일 전 release
    for i in range(release_count):
        d = today - dt.timedelta(days=1)
        lines.append(f"## [{d.isoformat()}] release | v0.9.{i+5} — test release\n")
    # 60일 전 (window 밖, 무시되어야 함)
    d_out = today - dt.timedelta(days=60)
    lines.append(f"## [{d_out.isoformat()}] ingest | out-of-window event (skip 대상)\n")
    log_path.write_text("".join(lines))
    return log_path


# ---------------------------------------------------------------------------
# Acceptance #1: analyze_30day_distribution 가 30일 window event 들을 분류
# ---------------------------------------------------------------------------
def test_30day_distribution_analysis_v0_9_6() -> None:
    """Acceptance §4.4 #1: 30일 안 ingest / query / release 분포 + top topics."""
    helper = _load_common("purpose_refresh", "purpose_refresh.py")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        today = dt.date(2026, 6, 24)
        log_path = _make_minimal_log(
            tmp_path, today, ingest_count=5, query_count=2, release_count=1
        )

        dist = helper.analyze_30day_distribution(log_path, today=today, window_days=30)

        # window 정합
        assert dist["window_days"] == 30
        assert dist["from_date"] == "2026-05-25"  # 30일 전
        assert dist["to_date"] == "2026-06-24"

        # 60일 전 event 는 window 밖 → 제외. 5+2+1 = 8 events
        assert dist["total_events"] == 8, f"expected 8 events, got {dist['total_events']}"

        # events_by_type 카운트
        assert dist["events_by_type"].get("ingest", 0) == 5
        assert dist["events_by_type"].get("query", 0) == 2
        assert dist["events_by_type"].get("release", 0) == 1

        # ingest_count = ingest (5) 만 (lint-fix / backfill / promote 없음)
        assert dist["ingest_count"] == 5
        assert dist["query_count"] == 2
        assert dist["release_count"] == 1

        # top_ingest_topics: "deprecation" + "policy" 가 ingest summary 에 반복 등장
        ingest_topics = dict(dist["top_ingest_topics"])
        assert "deprecation" in ingest_topics, f"expected 'deprecation' in {ingest_topics}"
        assert ingest_topics["deprecation"] >= 5, f"expected >= 5 deprecation count, got {ingest_topics['deprecation']}"

        # top_query_topics: "scope" 가 query summary 에 등장
        query_topics = dict(dist["top_query_topics"])
        assert "scope" in query_topics, f"expected 'scope' in {query_topics}"

        # recent_releases: 1건
        assert len(dist["recent_releases"]) == 1
        version, _ = dist["recent_releases"][0]
        assert version == "v0.9.5"

        # warnings 비어있음 (window 안 event 존재)
        assert dist["warnings"] == []


# ---------------------------------------------------------------------------
# Acceptance #2: generate_llm_suggest_prompt 가 분포 + PURPOSE.md 본문 + advisory 포함
# ---------------------------------------------------------------------------
def test_llm_suggest_prompt_generation_v0_9_6() -> None:
    """Acceptance §4.4 #2: prompt 가 §1 분포 + §2 본문 + §3 advisory 요청 포함."""
    helper = _load_common("purpose_refresh", "purpose_refresh.py")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        today = dt.date(2026, 6, 24)
        log_path = _make_minimal_log(tmp_path, today, ingest_count=3, query_count=1)
        purpose_path = _make_minimal_purpose(tmp_path)

        dist = helper.analyze_30day_distribution(log_path, today=today, window_days=30)
        prompt = helper.generate_llm_suggest_prompt(dist, purpose_path)

        # §1: 30일 분포
        assert "30일 ingest/query/release 분포" in prompt
        assert "Window:" in prompt
        assert "2026-05-25" in prompt and "2026-06-24" in prompt
        assert "Total events:" in prompt
        assert "Ingest-like:" in prompt
        assert "Query-like:" in prompt
        assert "Release:" in prompt
        assert "deprecation" in prompt  # top ingest topic

        # §2: PURPOSE.md 본문 (≤800 char)
        assert "PURPOSE.md 현재 본문" in prompt
        assert "G1" in prompt  # PURPOSE.md 본문에 등장
        assert "표준 AI 협업 워크플로우" in prompt  # G1 본문 일부

        # §3: advisory 요청
        assert "LLM Suggest 요청" in prompt
        assert "Goals" in prompt and "Key Questions" in prompt
        assert "Research Scope" in prompt and "Evolving Thesis" in prompt
        assert "advisory" in prompt.lower()  # advisory disclaimer
        assert "사람이 review" in prompt or "human confirm" in prompt.lower()  # human confirm 필수

        # auto-commit 금지 명시
        assert "자동 commit ❌" in prompt or "자동 적용 ❌" in prompt


# ---------------------------------------------------------------------------
# Acceptance #3: update_last_purpose_review 가 frontmatter 갱신
# ---------------------------------------------------------------------------
def test_last_purpose_review_update_v0_9_6() -> None:
    """Acceptance §4.4 #3: PURPOSE.md frontmatter 의 last_purpose_review date 갱신."""
    helper = _load_common("purpose_refresh", "purpose_refresh.py")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        purpose_path = _make_minimal_purpose(tmp_path, last_review="2026-06-19")

        today = dt.date(2026, 6, 24)
        result = helper.update_last_purpose_review(purpose_path, today=today)

        # 갱신 성공
        assert result["updated"] is True
        assert result["previous"] == "2026-06-19"
        assert result["current"] == "2026-06-24"
        assert result["purpose_path"] == str(purpose_path)

        # 실제 file 에 반영
        text = purpose_path.read_text(encoding="utf-8")
        assert "last_purpose_review: 2026-06-24" in text
        # 기존 frontmatter 의 다른 field 보존
        assert "purpose_version: 1" in text
        # 본문 (§1 Goals 등) 보존
        assert "## 1. Goals" in text
        assert "G1" in text


# ---------------------------------------------------------------------------
# Acceptance #4: run_purpose_refresh(apply=False) 일 때 PURPOSE.md 미변경
# ---------------------------------------------------------------------------
def test_purpose_refresh_dry_run_v0_9_6() -> None:
    """Acceptance §4.4 #4: dry-run (apply=False) 일 때 PURPOSE.md 미변경 + prompt 정상 emit."""
    helper = _load_common("purpose_refresh", "purpose_refresh.py")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        today = dt.date(2026, 6, 24)
        log_path = _make_minimal_log(tmp_path, today, ingest_count=3)
        purpose_path = _make_minimal_purpose(tmp_path, last_review="2026-06-19")

        # apply=False
        result = helper.run_purpose_refresh(
            workspace_root=tmp_path,
            today=today,
            window_days=30,
            apply=False,
            wiki_log_path=log_path,
            purpose_path=purpose_path,
        )

        # applied=False
        assert result["applied"] is False
        # prompt 정상 emit
        assert "30일 ingest/query/release 분포" in result["prompt"]
        # distribution 정합
        assert result["distribution"]["total_events"] >= 3
        # purpose_update: updated=False, previous/current 만 채워짐
        assert result["purpose_update"]["updated"] is False
        assert result["purpose_update"]["previous"] == "2026-06-19"
        assert result["purpose_update"]["current"] == "2026-06-24"
        # warnings 비어있음
        assert result["purpose_update"]["warnings"] == []

        # 실제 file 미변경 verify
        text = purpose_path.read_text(encoding="utf-8")
        assert "last_purpose_review: 2026-06-19" in text
        assert "last_purpose_review: 2026-06-24" not in text


# ---------------------------------------------------------------------------
# Acceptance #5: run_purpose_refresh(apply=True) 일 때 frontmatter 갱신
# ---------------------------------------------------------------------------
def test_purpose_refresh_advisory_policy_v0_9_6() -> None:
    """Acceptance §4.4 #5: apply=True 일 때 PURPOSE.md frontmatter 갱신 + updated=True."""
    helper = _load_common("purpose_refresh", "purpose_refresh.py")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        today = dt.date(2026, 6, 24)
        log_path = _make_minimal_log(tmp_path, today, ingest_count=2)
        purpose_path = _make_minimal_purpose(tmp_path, last_review="2026-06-19")

        # apply=True
        result = helper.run_purpose_refresh(
            workspace_root=tmp_path,
            today=today,
            window_days=30,
            apply=True,
            wiki_log_path=log_path,
            purpose_path=purpose_path,
        )

        # applied=True
        assert result["applied"] is True
        # purpose_update: updated=True
        assert result["purpose_update"]["updated"] is True
        assert result["purpose_update"]["previous"] == "2026-06-19"
        assert result["purpose_update"]["current"] == "2026-06-24"

        # 실제 file 갱신 verify
        text = purpose_path.read_text(encoding="utf-8")
        assert "last_purpose_review: 2026-06-24" in text
        assert "last_purpose_review: 2026-06-19" not in text


# ---------------------------------------------------------------------------
# Acceptance #6: log.md 부재 / PURPOSE.md 부재 시 graceful skip
# ---------------------------------------------------------------------------
def test_purpose_refresh_graceful_skip_v0_9_6() -> None:
    """Acceptance §4.4 #6: log.md / PURPOSE.md 부재 시 advisory warning + no-op."""
    helper = _load_common("purpose_refresh", "purpose_refresh.py")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        today = dt.date(2026, 6, 24)

        # (1) log.md 부재: distribution.warnings 에 "log.md 부재"
        nonexistent_log = tmp_path / "does_not_exist_log.md"
        dist = helper.analyze_30day_distribution(
            wiki_log_path=nonexistent_log, today=today, window_days=30
        )
        assert dist["total_events"] == 0
        assert any("log.md 부재" in w for w in dist["warnings"])
        assert dist["ingest_count"] == 0
        assert dist["query_count"] == 0
        assert dist["top_ingest_topics"] == []

        # (2) PURPOSE.md 부재: update_last_purpose_review 가 updated=False + warning
        nonexistent_purpose = tmp_path / "does_not_exist_PURPOSE.md"
        upd = helper.update_last_purpose_review(
            purpose_path=nonexistent_purpose, today=today
        )
        assert upd["updated"] is False
        assert any("PURPOSE.md 부재" in w for w in upd["warnings"])

        # (3) run_purpose_refresh with both missing: prompt + distribution 모두
        #     advisory emit + file I/O 없음
        result = helper.run_purpose_refresh(
            workspace_root=tmp_path,
            today=today,
            window_days=30,
            apply=True,  # apply=True 여도 PURPOSE.md 부재 시 no-op
            wiki_log_path=nonexistent_log,
            purpose_path=nonexistent_purpose,
        )
        assert result["distribution"]["total_events"] == 0
        assert any("log.md 부재" in w for w in result["distribution"]["warnings"])
        assert result["purpose_update"]["updated"] is False
        assert any("PURPOSE.md 부재" in w for w in result["purpose_update"]["warnings"])
        # prompt 은 정상 emit (advisory)
        assert "R-A Purpose Refresh" in result["prompt"]
        assert "advisory" in result["prompt"].lower()
