"""원장에 기록될 수 있는 경로가 **실제로 존재하는가** (v1.0.1+).

## 왜 왕복 계약(§2.22)만으로는 부족한가

`check_writer_reader_roundtrip.py` 는 writer 로 쓰고 reader 로 되읽는다. 그 pair 는
green 이었다. 그런데도 north-star `silent_failing_cycles_count` 는 영구히 0 이었다:

    cmd_release step 2.7 : manual_required 1+ → **early return**
    cmd_release step 6.5b: (gh release create 성공 뒤) 원장 append   ← 도달 불가

즉 `manual_required_count > 0` 인 line 을 원장에 남길 수 있는 **호출 경로가 없었다**.
왕복 테스트는 writer 를 직접 불러 dirty payload 를 넣었기 때문에 통과했다 — 프로덕션
orchestrator 는 writer 에게 그 payload 를 절대 건네지 못하는데도.

> 교훈: writer 와 reader 가 맞물리는지 보는 것만으로는 부족하다. **orchestrator 가
> writer 를 그 값으로 부를 수 있는가** 를 따로 봐야 한다. 지표가 한 방향으로만
> 움직일 수 있으면, 그 지표는 재고 있는 게 아니다.

release 가 한 번이라도 성공하면 `measured` 가 True 로 뒤집히므로, 정직한 *미측정* 이
"N cycle 재봤더니 0건" 이라는 거짓 초록불로 바뀐다는 점에서 단순 누락보다 나쁘다.

Test list (5 case):
1. manual_required cycle 이 원장에 기록된다 (분자 도달 가능) + release 는 멈춘다
2. clean cycle 이 원장에 기록된다 (분모)
3. dry-run 은 아무것도 쓰지 않는다 (저장소 오염 금지)
4. 같은 version 재시도는 한 cycle (분모 부풀림 없음, dirty 는 유지)
5. 원장 → north-star 가 분자/분모를 함께 낸다

Cross-ref: releases/Beta-v1.0.0.md §2.19 (north-star 재정의), §2.22 (왕복 계약).
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(SOURCE_ROOT / "tools"))

import release_pipeline  # noqa: E402
from release_pipeline import DRIFT_LEDGER_RELPATH, _self_recover_step  # noqa: E402
from workflow_kit.common.dashboard_data import collect_silent_failing_cycles  # noqa: E402


def _fake_self_recover(manual_required: list[str]):
    """cmd_self_recover 를 대신할 stub — drift 판정만 흉내낸다."""

    def _stub(_args: argparse.Namespace) -> dict:
        return {
            "recovered": [],
            "manual_required": list(manual_required),
            "re_check": {"guard_status": "fail" if manual_required else "pass"},
        }

    return _stub


def _run_step(ws: Path, *, version: str, manual: list[str], dry_run: bool = False) -> dict:
    """`_self_recover_step` 을 격리 workspace 에서 1회 실행하고 results 를 반환."""
    original = release_pipeline.cmd_self_recover
    release_pipeline.cmd_self_recover = _fake_self_recover(manual)  # type: ignore[assignment]
    try:
        args = argparse.Namespace(dry_run=dry_run, version=version, workspace_root=str(ws))
        results: dict = {}
        error = _self_recover_step(args, results, argparse.Namespace(dry_run=dry_run))
        return {"results": results, "error": error}
    finally:
        release_pipeline.cmd_self_recover = original  # type: ignore[assignment]


def _ledger_lines(ws: Path) -> list[dict]:
    ledger = ws / DRIFT_LEDGER_RELPATH
    if not ledger.is_file():
        return []
    return [json.loads(ln) for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]


def test_manual_required_cycle_is_recorded() -> None:
    """**본 smoke 의 핵심.** manual 개입이 필요했던 cycle 이 원장에 남는다.

    v1.0.0 에서는 이 line 이 만들어질 수 있는 경로 자체가 없었다 — early return 이
    append 보다 앞이었다. 그래서 north-star 의 분자가 구조적으로 0 에 고정됐다.
    """
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        out = _run_step(ws, version="v1.0.1", manual=["case_x"])

        # release 는 멈춘다 (기존 동작 유지 — 사람이 고쳐야 한다).
        assert out["error"], "manual_required 인데 release 가 계속 진행됐다"
        assert "case_x" in out["error"], out["error"]

        # 그리고 그 사실이 원장에 남는다.
        lines = _ledger_lines(ws)
        assert len(lines) == 1, f"원장 line {len(lines)}건 (기대 1) — early return 이 append 를 건너뛴다"
        assert lines[0]["manual_required_count"] == 1, lines[0]
        assert lines[0]["manual_required"] == ["case_x"], lines[0]
        assert lines[0]["version"] == "v1.0.1", lines[0]
        assert out["results"]["drift_ledger_append"]["status"] == "ok", out["results"]


def test_clean_cycle_is_recorded() -> None:
    """drift 가 없던 cycle 도 기록된다 — 분모가 있어야 "0건" 을 말할 수 있다."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        out = _run_step(ws, version="v1.0.1", manual=[])
        assert out["error"] is None, out["error"]
        lines = _ledger_lines(ws)
        assert len(lines) == 1, lines
        assert lines[0]["manual_required_count"] == 0, lines[0]


def test_dry_run_writes_nothing() -> None:
    """dry-run 은 원장을 만들지 않는다 (저장소 오염 금지)."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        out = _run_step(ws, version="v1.0.1", manual=["case_x"], dry_run=True)
        assert out["results"]["drift_ledger_append"]["status"] == "skipped", out["results"]
        assert not (ws / DRIFT_LEDGER_RELPATH).exists(), "dry-run 이 원장을 write 했다"
        assert _ledger_lines(ws) == []


def test_same_version_retry_is_one_cycle() -> None:
    """manual fix 후 재실행은 한 cycle 의 두 시도다 — 분모를 부풀리지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        _run_step(ws, version="v1.0.1", manual=["case_x"])  # 1차: 중단
        out = _run_step(ws, version="v1.0.1", manual=[])  # 2차: 고친 뒤 재실행
        assert out["error"] is None, out["error"]
        assert len(_ledger_lines(ws)) == 2, "원장은 append-only — 시도마다 line 이 남는다"

        north_star = collect_silent_failing_cycles(ws)
        assert north_star["measured_cycles"] == 1, north_star
        # 마지막 시도가 clean 이어도 그 cycle 은 manual 개입이 있었던 cycle 이다.
        assert north_star["count"] == 1, north_star


def test_ledger_feeds_north_star() -> None:
    """원장 → north-star 가 분자/분모를 함께 낸다 (미측정 → 실측 전환)."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        assert collect_silent_failing_cycles(ws)["measured"] is False, "원장 없이 measured=True"

        _run_step(ws, version="v1.0.1", manual=[])
        _run_step(ws, version="v1.0.2", manual=["case_x"])
        _run_step(ws, version="v1.0.3", manual=[])

        north_star = collect_silent_failing_cycles(ws)
        assert north_star["measured"] is True, north_star
        assert north_star["measured_cycles"] == 3, north_star
        assert north_star["count"] == 1, north_star
        assert north_star["source"] == DRIFT_LEDGER_RELPATH, north_star


def main() -> int:
    test_funcs = [
        test_manual_required_cycle_is_recorded,
        test_clean_cycle_is_recorded,
        test_dry_run_writes_nothing,
        test_same_version_retry_is_one_cycle,
        test_ledger_feeds_north_star,
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
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
