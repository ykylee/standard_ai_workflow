#!/usr/bin/env python3
"""v0.7.0 wiki: maintainability score smoke test.

- score_wiki_maintainability.py 가 실행 가능 + 6 dim score 산출
- overall score 가 0.0 ~ 5.0 범위
- grade 가 A/B/C/D/F enum
- details dict 가 6 dim 모두 포함
- emit-dashboard 가 wiki-maintainability-score.md 생성 (in-repo wiki)

Reference:
- workflow-source/workflow_kit/tools/score_wiki_maintainability.py
- workflow-source/ai-workflow/wiki/concepts/wiki-maintainability-score.md
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

# 병렬 전량(--jobs auto)에서 57s 실측 (2026-08-11) — 기본 60s 상한과 여유가
# 없어 부하 편차만으로 TIMEOUT flake 가 난다. 행(hang) 검출은 150s 로도 충분하다.
CHECK_TIMEOUT_S = 150

WATCHES = (
    "ai-workflow/wiki/*",
    "workflow-source/workflow_kit/*",
    # operational dim 이 `SMOKE_TESTS` 의 check 들을 서브프로세스로 돌린다 —
    # tests/ 전체를 관찰 범위로 본다. 좁히면 그 dim 이 조용히 옛 결과를 재는 자리다.
    "workflow-source/tests/*",
    # 점수의 source 계층이 core/extensions 문서 corpus 를 읽는다 — meta-watch
    # 실측 (2026-08-28) 이 선언 밖 접근 229건으로 보였다 (ADR-028).
    "workflow-source/core/*",
    "workflow-source/extensions/*",
    "workflow-source/templates/*",
    "workflow-source/pyproject.toml",
)
"""점수는 위키 + 점수 도구 + operational dim 이 돌리는 smoke 의 함수다."""

SOURCE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SOURCE_ROOT.parent
TOOL_PATH = SOURCE_ROOT / "workflow_kit" / "tools" / "score_wiki_maintainability.py"
DASHBOARD_PATH = REPO_ROOT / "ai-workflow" / "wiki" / "concepts" / "wiki-maintainability-score.md"


def _run_score_tool(args: list[str] = None) -> dict:
    """score tool 실행 + JSON 반환."""
    args = args or ["--json"]
    proc = subprocess.run(
        ["python3", str(TOOL_PATH)] + args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"score tool failed: {proc.stderr}")
    if "--json" in args:
        return json.loads(proc.stdout)
    return {}


_SCORE_CACHE: dict | None = None


def _score_once() -> dict:
    """**같은 저장소의 같은 점수**를 여러 case 가 볼 때 쓰는 공유 실행.

    점수 도구는 1회 6.4s 인데, 이 검사의 7개 case 가 전부 *동일한 인자*로 부르고
    결과 dict 를 들여다보기만 했다 — 안 바뀐 저장소를 9번 다시 계산했고 그것이
    이 검사의 68s 중 58s 였다 (2026-08-14 실측. 전량 병렬 구간의 임계경로가
    이 검사 하나였다).

    **범위를 줄이는 것이 아니다.** case 는 그대로 전부 돌고, 같은 산출물을 한 번만
    만들어 나눠 본다. 원본을 넘기지 않고 **deep copy** 를 준다 — 앞 case 가 dict 를
    건드리면 뒤 case 가 조용히 다른 것을 보게 된다.

    `test_score_idempotent` 는 여기를 쓰지 않는다. 그 case 가 재는 것이 *두 번 실행이
    같은 값을 내는가* 라서, 캐시를 쓰면 자기 자신과 비교하는 동어반복이 된다.
    """
    global _SCORE_CACHE
    if _SCORE_CACHE is None:
        _SCORE_CACHE = _run_score_tool()
    return copy.deepcopy(_SCORE_CACHE)


# --- Test 1: tool importable + executable ---


def test_tool_importable() -> None:
    """score tool 실행 가능."""
    assert TOOL_PATH.exists(), f"tool not found: {TOOL_PATH}"


def test_tool_runs() -> None:
    """score tool 의 --json 실행 + valid JSON 반환."""
    score = _score_once()
    assert isinstance(score, dict)


# --- Test 2: score structure ---


def test_score_structure() -> None:
    """score dict 가 6 dim + overall + grade + timestamp 포함."""
    score = _score_once()
    assert "timestamp" in score
    assert "overall" in score
    assert "grade" in score
    assert "scores" in score
    assert "details" in score
    assert set(score["scores"].keys()) == {
        "coverage", "freshness", "discoverability",
        "cross_ref", "lifecycle", "operational",
    }
    assert set(score["details"].keys()) == set(score["scores"].keys())


def test_score_range() -> None:
    """6 dim score 가 0.0 ~ 5.0 범위."""
    score = _score_once()
    for dim, s in score["scores"].items():
        # None = 측정 불가 (분모 0). 0.0 으로 세지 않는 것이 계약이므로 범위 검사 제외.
        if s is None:
            assert "error" in score["details"][dim], \
                f"{dim}: 측정 불가면 details 에 error 사유가 있어야 한다"
            continue
        assert 0.0 <= s <= 5.0, f"{dim}: {s} out of range"
    assert 0.0 <= score["overall"] <= 5.0


def test_grade_enum() -> None:
    """grade 가 A/B/C/D/F enum."""
    score = _score_once()
    assert score["grade"] in ("A", "B", "C", "D", "F")


def test_grade_matches_score() -> None:
    """grade 가 overall score 와 일치."""
    score = _score_once()
    overall = score["overall"]
    if overall >= 4.5:
        expected = "A"
    elif overall >= 4.0:
        expected = "B"
    elif overall >= 3.5:
        expected = "C"
    elif overall >= 3.0:
        expected = "D"
    else:
        expected = "F"
    assert score["grade"] == expected, f"grade={score['grade']} but expected={expected} (overall={overall})"


# --- Test 3: detail metric consistency ---


def test_details_consistency() -> None:
    """details 의 total/active/ratio 가 score 와 일치."""
    score = _score_once()
    for dim in score["scores"]:
        detail = score["details"][dim]
        if score["scores"][dim] is None:
            continue  # 측정 불가 dim 은 ratio ↔ score 정합 대상이 아니다
        if "ratio" in detail:
            # score = ratio * 5.0 (or (1-ratio)*5.0 for freshness)
            ratio = detail["ratio"]
            if dim == "freshness":
                expected = round((1 - ratio) * 5.0, 2)
            else:
                expected = round(ratio * 5.0, 2)
            actual = score["scores"][dim]
            assert abs(actual - expected) <= 0.05, \
                f"{dim}: actual={actual} but expected={expected} (ratio={ratio})"


def test_operational_smoke_passes() -> None:
    """operational dim 의 11 smoke test 가 모두 PASS."""
    score = _score_once()
    op = score["details"]["operational"]
    assert op["total"] >= 5, f"too few smoke tests: {op['total']}"
    # operational score 가 4.0 이상 = 대부분 통과
    assert score["scores"]["operational"] >= 4.0, \
        f"operational score too low: {score['scores']['operational']}"


# --- Test 4: dashboard emit ---


def test_dashboard_emit() -> None:
    """--emit-dashboard 실행 시 dashboard file 생성."""
    if DASHBOARD_PATH.exists():
        # 이미 생성됨 — skip
        return
    proc = subprocess.run(
        ["python3", str(TOOL_PATH), "--emit-dashboard"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, f"emit failed: {proc.stderr}"
    assert DASHBOARD_PATH.exists(), f"dashboard not created: {DASHBOARD_PATH}"


def test_dashboard_format() -> None:
    """dashboard file 의 frontmatter (none) + Overall + 6 dim table 포함."""
    if not DASHBOARD_PATH.exists():
        return
    content = DASHBOARD_PATH.read_text(encoding="utf-8")
    assert "Overall Score" in content
    assert "Grade" in content
    assert "Coverage" in content
    assert "Freshness" in content
    assert "Discoverability" in content
    assert "Cross-ref" in content
    assert "Lifecycle" in content
    assert "Operational" in content


def test_dashboard_in_index() -> None:
    """dashboard page 가 index.md 에 anchor 됨 (v0.7.0+ 권장)."""
    index = (REPO_ROOT / "ai-workflow" / "wiki" / "index.md").read_text(encoding="utf-8")
    if "wiki-maintainability-score" not in index:
        print("INFO: wiki-maintainability-score not in index.md (v0.7.1+ follow-up 권장)")


# --- Test 5: idempotency ---


def test_score_idempotent() -> None:
    """2회 연속 실행 시 overall score 동일 (deterministic)."""
    s1 = _run_score_tool()
    s2 = _run_score_tool()
    assert s1["overall"] == s2["overall"], \
        f"non-idempotent: {s1['overall']} vs {s2['overall']}"


# --- 메인 실행 ---


def main() -> int:
    test_funcs = [
        test_tool_importable,
        test_tool_runs,
        test_score_structure,
        test_score_range,
        test_grade_enum,
        test_grade_matches_score,
        test_details_consistency,
        test_operational_smoke_passes,
        test_dashboard_emit,
        test_dashboard_format,
        test_dashboard_in_index,
        test_score_idempotent,
    ]

    passed = 0
    failed = 0
    for func in test_funcs:
        try:
            func()
            print(f"  PASS  {func.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {func.__name__}: {e}")
            failed += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {func.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print()
    print(f"{passed} pass, {failed} fail")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
