"""Phase 13 AC1 north-star 지표의 **판정 근거**를 검사한다 (v1.0.1+).

## 왜 필요한가

v0.14.0 ~ v1.0.0 동안 Panel 1 의 두 지표는 실질이 없었다.

- `maturity_stale = (last_updated != 오늘)` — `maturity_matrix.json` 을 **매일**
  날짜 스탬프하지 않는 한 항상 True. 초록으로 만드는 유일한 방법이 "날짜만 찍기"
  였고, 그건 릴리스 노트 §2.18 이 하지 말라고 경고한 바로 그 행위다.
- `silent_failing_cycles_count = 1 if maturity_stale else 0` — north-star 의 정의
  (drift 를 manual fix 해야 했던 release cycle 의 누적 갯수) 와 아무 관계가 없는
  freshness proxy 를 north-star 자리에 앉혀 놓은 것이었다.

본 smoke 는 재정의된 판정이 **날짜가 아니라 drift 에** 반응하는지, 그리고 north-star
가 원장에서만 나오며 원장이 비면 0 이 아니라 *미측정* 으로 표시되는지를 고정한다.

Test list (6 case):
1. test_stale_when_surface_changed_after_declaration
2. test_not_stale_when_declaration_current_even_if_old   ← 날짜 스탬프 회귀 방지
3. test_unknown_source_when_git_unavailable              ← 위양성 red 금지
4. test_north_star_unmeasured_when_ledger_empty
5. test_north_star_counts_only_manual_required_cycles
6. test_ledger_path_shared_between_writer_and_reader

Cross-ref: ai-workflow/wiki/topics/phase-13-definition-north-star.md §2.2 +
workflow-source/releases/Beta-v1.0.0.md §2.18.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

# site-packages 의 stale workflow_kit shadowing 회피.
SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.dashboard_data import (  # noqa: E402
    DRIFT_LEDGER_RELPATH,
    _render_panel_1,
    collect_drift_prevention,
    collect_silent_failing_cycles,
)


def _git(ws: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=smoke@test", "-c", "user.name=smoke", *args],
        cwd=str(ws), capture_output=True, text=True, check=True,
    )


def _make_repo(ws: Path, *, last_updated: str, commit_date: str) -> None:
    """maturity 선언과 surface commit 날짜를 임의로 세팅한 temp git repo.

    commit 날짜를 명시적으로 고정하므로 판정이 *오늘* 에 의존하면 즉시 드러난다.
    """
    matrix = ws / "workflow-source" / "core" / "maturity_matrix.json"
    matrix.parent.mkdir(parents=True, exist_ok=True)
    matrix.write_text(
        json.dumps({"last_updated": last_updated, "harnesses": {"supported": ["codex"]}}),
        encoding="utf-8",
    )
    _git(ws, "init", "-q")
    _git(ws, "add", "-A")
    stamp = f"{commit_date}T12:00:00+00:00"
    _git(ws, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "seed",
         "--date", stamp)
    # committer date 는 -c 로 못 넣으므로 env 로 rewrite.
    subprocess.run(
        ["git", "-c", "user.email=smoke@test", "-c", "user.name=smoke",
         "commit", "--amend", "--no-edit", "-q", "--date", stamp],
        cwd=str(ws), capture_output=True, text=True, check=True,
        env={"GIT_COMMITTER_DATE": stamp, "PATH": "/usr/bin:/bin"},
    )


def _panel(ws: Path) -> dict:
    return collect_drift_prevention(ws, inline_guard=False)


# --- Tests ---


def test_stale_when_surface_changed_after_declaration() -> None:
    """surface commit 이 선언보다 나중 → stale (진짜 drift)."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        _make_repo(ws, last_updated="2026-01-01", commit_date="2026-01-05")
        p = _panel(ws)
        assert p["maturity_surface_changed_at"] == "2026-01-05", p["maturity_surface_changed_at"]
        assert p["maturity_stale"] is True, p
        assert p["maturity_staleness_source"] == "maturity_surface_commit"


def test_not_stale_when_declaration_current_even_if_old() -> None:
    """선언이 surface 를 따라잡았으면, 그게 몇 달 전이어도 stale 이 아니다.

    구 판정(`last_updated != 오늘`)에서는 이 case 가 반드시 stale 이었다.
    """
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        _make_repo(ws, last_updated="2026-01-05", commit_date="2026-01-05")
        p = _panel(ws)
        assert p["maturity_stale"] is False, p
        assert p["today_iso"] != "2026-01-05", "fixture 가 오늘 날짜와 겹치면 회귀를 못 잡는다"
        assert p["maturity_refresh_hint"] == ""


def test_unknown_source_when_git_unavailable() -> None:
    """git repo 가 아니면 판정 근거가 없다 → stale 로 단정하지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        matrix = ws / "workflow-source" / "core" / "maturity_matrix.json"
        matrix.parent.mkdir(parents=True, exist_ok=True)
        matrix.write_text(json.dumps({"last_updated": "2026-01-01"}), encoding="utf-8")
        p = _panel(ws)
        assert p["maturity_staleness_source"] == "unknown", p
        assert p["maturity_stale"] is False, "근거 없이 red 를 내면 위양성으로 무시당한다"


def test_north_star_unmeasured_when_ledger_empty() -> None:
    """원장이 없으면 count=0 이되 measured=False — 렌더에도 '미측정' 으로 나온다."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        ns = collect_silent_failing_cycles(ws)
        assert ns["count"] == 0 and ns["measured_cycles"] == 0
        assert ns["measured"] is False, ns
        # panel 이 *원장에서* 읽는지까지 본다 — proxy 를 north-star 자리에 앉히면 여기서 걸린다.
        p = _panel(ws)
        assert p["silent_failing_cycles_source"] == DRIFT_LEDGER_RELPATH, p
        assert p["silent_failing_cycles_measured"] is False, p
        assert "미측정" in "\n".join(_render_panel_1(p))


def test_north_star_counts_only_manual_required_cycles() -> None:
    """분자 = manual fix 가 필요했던 cycle, 분모 = 기록된 전체 cycle."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        ledger = ws / DRIFT_LEDGER_RELPATH
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(
            "\n".join([
                json.dumps({"version": "v1.0.1", "manual_required_count": 0}),
                json.dumps({"version": "v1.0.2", "manual_required_count": 2}),
                "not json",  # malformed line 은 skip (cycle 로도 세지 않는다)
                json.dumps({"version": "v1.0.3", "manual_required_count": 1}),
                "",
            ]),
            encoding="utf-8",
        )
        ns = collect_silent_failing_cycles(ws)
        assert ns["measured_cycles"] == 3, ns
        assert ns["count"] == 2, ns
        assert ns["measured"] is True


def test_ledger_path_shared_between_writer_and_reader() -> None:
    """writer(release_pipeline) 의 fallback 상수가 reader 와 갈라지면 원장이 둘로 쪼개진다."""
    text = (SOURCE_ROOT / "tools" / "release_pipeline.py").read_text(encoding="utf-8")
    literals = {
        line.split("=", 1)[1].strip().strip('"')
        for line in text.splitlines()
        if line.strip().startswith("DRIFT_LEDGER_RELPATH =")
    }
    assert literals == {DRIFT_LEDGER_RELPATH}, (
        f"release_pipeline 의 fallback 경로 {literals} ≠ dashboard 의 {DRIFT_LEDGER_RELPATH}"
    )


def main() -> int:
    test_funcs = [
        test_stale_when_surface_changed_after_declaration,
        test_not_stale_when_declaration_current_even_if_old,
        test_unknown_source_when_git_unavailable,
        test_north_star_unmeasured_when_ledger_empty,
        test_north_star_counts_only_manual_required_cycles,
        test_ledger_path_shared_between_writer_and_reader,
    ]
    failures: list[tuple[str, str]] = []
    for func in test_funcs:
        try:
            func()
            print(f"  PASS: {func.__name__}")
        except AssertionError as e:
            failures.append((func.__name__, f"AssertionError: {e}"))
            print(f"  FAIL: {func.__name__} — {e}")
        except Exception as e:  # noqa: BLE001
            failures.append((func.__name__, f"{type(e).__name__}: {e}"))
            print(f"  FAIL: {func.__name__} — {type(e).__name__}: {e}")

    total = len(test_funcs)
    passed = total - len(failures)
    print(f"\n{passed}/{total} PASS")
    if failures:
        for name, err in failures:
            print(f"  - {name}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
