#!/usr/bin/env python3
"""v0.7.1+: wiki maintainability score trend smoke test.

- tools/score_wiki_trend.py 실행 가능
- .score_history.jsonl load + parse
- ASCII chart format 검증
- dashboard 가 trend section 포함 (emit-dashboard 후)

Reference:
- workflow-source/workflow_kit/tools/score_wiki_trend.py
- workflow-source/workflow_kit/tools/.score_history.jsonl
- workflow-source/concepts/wiki-maintainability-score.md
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SOURCE_ROOT.parent
TOOL_PATH = SOURCE_ROOT / "workflow_kit" / "tools" / "score_wiki_trend.py"
HISTORY_PATH = SOURCE_ROOT / "workflow_kit" / "tools" / ".score_history.jsonl"
DASHBOARD_PATH = REPO_ROOT / "ai-workflow" / "wiki" / "concepts" / "wiki-maintainability-score.md"


def _run(args: list[str], timeout: int = 60) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["python3", str(TOOL_PATH)] + args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


# --- Test 1: tool importable + executable ---


def test_tool_importable() -> None:
    """trend tool 실행 가능."""
    assert TOOL_PATH.exists(), f"tool not found: {TOOL_PATH}"


def test_tool_show_runs() -> None:
    """--show 실행 + 출력에 trend 시각화 포함."""
    rc, out, err = _run(["--show"])
    assert rc == 0, f"tool failed: {err}"
    assert "Wiki Maintainability Score Trend" in out
    assert "Overall (5.0 max)" in out
    assert "coverage" in out
    assert "freshness" in out
    assert "discoverability" in out


# --- Test 2: history jsonl ---


def test_history_file_exists() -> None:
    """.score_history.jsonl 존재 (v0.7.1+ 의 trend 누적)."""
    assert HISTORY_PATH.exists(), f"history not found: {HISTORY_PATH}"


def test_history_valid_jsonl() -> None:
    """history 의 각 줄이 valid JSON."""
    if not HISTORY_PATH.exists():
        return
    for i, line in enumerate(HISTORY_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as e:
            raise AssertionError(f"line {i+1} invalid JSON: {e}\n  {line[:100]}")
        # required fields
        for k in ("timestamp", "commit", "scores", "overall", "grade"):
            assert k in rec, f"line {i+1} missing field: {k}"


def test_history_score_in_range() -> None:
    """history 의 overall / scores 가 0.0~5.0 범위."""
    if not HISTORY_PATH.exists():
        return
    for i, line in enumerate(HISTORY_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()):
        if not line.strip():
            continue
        rec = json.loads(line)
        assert 0.0 <= rec["overall"] <= 5.0, f"line {i+1}: overall {rec['overall']} out of range"
        for dim, s in rec.get("scores", {}).items():
            assert 0.0 <= s <= 5.0, f"line {i+1}: {dim} {s} out of range"


# --- Test 3: chart format ---


def test_chart_bar_chars() -> None:
    """ASCII bar chart 가 █ / ░ chars 만 사용."""
    rc, out, _ = _run(["--show"])
    for line in out.splitlines():
        if "█" in line or "░" in line:
            # bar line
            for ch in line:
                if ch not in ("█", "░", " ", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ".", "-", "│", "└", "┌"):
                    pass  # ignore others
            # bar line 은 █ / ░ / space / digits 만
            non_bar = [c for c in line if c not in ("█", "░", " ", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ".")]
            # non-bar chars 는 prefix (commit, score) 만
            assert all(c.isalnum() or c in (".", " ", "│") for c in non_bar), \
                f"unexpected char in bar line: {line!r}"


def test_json_output() -> None:
    """--json 실행 + valid JSON."""
    rc, out, err = _run(["--json"])
    assert rc == 0, f"json failed: {err}"
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) >= 1


# --- Test 4: dashboard integration ---


def test_dashboard_trend_section() -> None:
    """dashboard page 가 trend section 포함 (Trend Over Time heading)."""
    if not DASHBOARD_PATH.exists():
        return
    content = DASHBOARD_PATH.read_text(encoding="utf-8")
    assert "## Trend Over Time" in content, "dashboard missing Trend Over Time section"
    # 1 row 이상 (commit hash + overall)
    assert "0052da1" in content or "bad14d8" in content, \
        "dashboard trend table missing sample commit"


def test_dashboard_includes_trend_tool_reference() -> None:
    """dashboard 가 trend tool 의 path 명시."""
    if not DASHBOARD_PATH.exists():
        return
    content = DASHBOARD_PATH.read_text(encoding="utf-8")
    assert "score_wiki_trend" in content, "dashboard missing trend tool reference"


# --- Test 5: idempotency ---


def test_show_idempotent() -> None:
    """--show 2회 연속 실행 시 결과 동일."""
    _, out1, _ = _run(["--show"])
    _, out2, _ = _run(["--show"])
    assert out1 == out2, "show not idempotent"


# --- Test 6: alert 분기 ---


def test_compare_scores_no_alert() -> None:
    """baseline < current → alert 0, exit 0."""
    import sys
    sys.path.insert(0, str(SOURCE_ROOT / "workflow_kit" / "tools"))
    import score_wiki_trend as swt

    baseline = {"scores": {d: 4.0 for d in swt.DIMS}}
    current = {"scores": {d: 4.5 for d in swt.DIMS}}  # +0.5 (info)
    alerts = swt.compare_scores(baseline, current, alert_threshold=0.3)
    assert all(a.severity in ("info", "ok") for a in alerts), "expected no alert"
    assert any(a.severity == "info" for a in alerts), "expected info"


def test_compare_scores_alert() -> None:
    """dim 별 -0.5 → alert 1, exit 1."""
    import sys
    sys.path.insert(0, str(SOURCE_ROOT / "workflow_kit" / "tools"))
    import score_wiki_trend as swt

    baseline = {"scores": {d: 5.0 for d in swt.DIMS}}
    current = {"scores": dict(baseline["scores"])}
    current["scores"]["freshness"] = 4.5  # -0.5

    alerts = swt.compare_scores(baseline, current, alert_threshold=0.3)
    alert_dims = [a.dim for a in alerts if a.severity == "alert"]
    assert "freshness" in alert_dims
    assert len(alert_dims) == 1


def test_alert_cli_exit_code_matches_alert_count() -> None:
    """CLI --alert 의 계약: **종료 코드가 자기가 출력한 alert 수와 일치**한다.

    옛 판정은 `rc == 0` 을 기대했다 — 즉 *살아있는 저장소가 마침 무결한가* 를
    push 게이트에 걸어 둔 것이다 (TASK-2026-09-21-main-002). `lifecycle` 은
    L2 stub 의 `last_touched` 가 30일을 넘기면 떨어지는 **시계 의존** 지표라,
    코드가 하나도 안 바뀌어도 31일째에 red 가 됐다. 실제로 그렇게 됐고
    (2026-09-21: stub 4종 전부 32일 경과 → 0.00), 80차 push 게이트 green 이후
    저장소 상태만으로 발현했다. 살아있는 저장소 상태는 기대값이 아니다.

    CLI 가 실제로 보증해야 하는 것은 **자기 출력과 자기 종료 코드가 어긋나지
    않는 것**이고, 그것은 저장소 상태와 무관하게 결정적이다. alert 판정 로직
    자체는 `test_compare_scores_no_alert` / `test_compare_scores_alert` 가
    고정 입력으로 양방향을 이미 잰다.
    """
    rc, out, err = _run(["--alert", "--baseline=7a4dbae"], timeout=120)
    assert rc in (0, 1), f"unexpected exit code: {rc} / {err[-200:]}"
    assert "Dim alerts" in out
    assert "alert(s)" in out

    m = re.search(r"Total:\s*(\d+)\s*alert\(s\)", out)
    assert m, f"alert 수를 출력에서 못 읽었다 — 계약이 깨졌다:\n{out[-400:]}"
    alert_count = int(m.group(1))
    expected_rc = 1 if alert_count else 0
    assert rc == expected_rc, (
        f"종료 코드가 자기 출력과 어긋난다: alert {alert_count}건인데 exit {rc} "
        f"(기대 {expected_rc}). 소비자는 종료 코드로 판단하므로 이 어긋남은 조용히 퍼진다."
    )


def test_l2_stubs_are_structurally_present() -> None:
    """L2 stub 의 **구조적** 방치만 게이트한다 — 경과일은 보고하되 막지 않는다.

    `lifecycle` 의 실패 사유는 두 부류인데 성질이 다르다:

    - **구조적**: 파일 부재 / `last_touched` 부재 / 형식 오류. 사람이나 emit 이
      뭔가를 깨뜨린 것이고, 시간이 지난다고 생기지 않는다 → 게이트한다.
    - **시계 의존**: `N일 경과`. 아무도 아무것도 안 해도 달력만으로 발생한다
      → 게이트하면 무관한 push 를 막는다. 보고만 한다
      (해소는 `refresh_wiki_memory.py --emit-l2 --apply`).

    옛 판정은 둘을 구분하지 않아 후자로 게이트를 닫았다. 구분을 없애고
    통째로 걷어내면 전자까지 놓치므로 — 검사는 깨지지 않고 무력화된다 —
    앞쪽만 남긴다.
    """
    sys.path.insert(0, str(SOURCE_ROOT / "workflow_kit" / "tools"))
    from score_wiki_maintainability import score_lifecycle

    score, detail = score_lifecycle()
    stale = detail.get("stale", [])
    structural = [s for s in stale if not re.search(r"\d+일 경과$", s)]
    assert not structural, (
        f"L2 stub 이 구조적으로 깨졌다 (경과일 아님): {structural}\n"
        f"  emit 으로 복구: refresh_wiki_memory.py --emit-l2 --apply"
    )
    aged = [s for s in stale if s not in structural]
    if aged:
        print(f"  [report] L2 stub 경과 {len(aged)}건 (게이트 아님): {aged}")
    print(f"  L2 stub 구조 무결 (lifecycle={score}, 선언 {detail.get('total')}종): PASS")


def test_alert_cli_missing_baseline() -> None:
    """--alert without --baseline → exit 2."""
    rc, out, _ = _run(["--alert"], timeout=30)
    assert rc == 2
    assert "ERROR" in out
    assert "--baseline" in out


# --- 메인 실행 ---


def main() -> int:
    test_funcs = [
        test_tool_importable,
        test_tool_show_runs,
        test_history_file_exists,
        test_history_valid_jsonl,
        test_history_score_in_range,
        test_chart_bar_chars,
        test_json_output,
        test_dashboard_trend_section,
        test_dashboard_includes_trend_tool_reference,
        test_show_idempotent,
        test_compare_scores_no_alert,
        test_compare_scores_alert,
        test_alert_cli_exit_code_matches_alert_count,
        test_l2_stubs_are_structurally_present,
        test_alert_cli_missing_baseline,
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
