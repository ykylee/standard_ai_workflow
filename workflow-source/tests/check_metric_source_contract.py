"""판정 지표는 **무엇을 보고 그렇게 판정했는지** 함께 내는가 (v1.0.1+).

## 왜 필요한가

v0.14.0 ~ v1.0.0 동안 Phase 13 north-star 자리에는 아무 상관 없는 freshness proxy 가
앉아 있었다 (노트 §2.19). 아무도 못 알아챈 이유는 단순하다 — **값의 타입은 맞았고,
근거를 말하지 않으니 대조할 것이 없었다.**

`check_writer_reader_roundtrip.py` 가 잡는 것은 *복제로 인한 갈라짐* 이다. 이 결함은
복제가 아니라 **대체**(진짜 측정 자리에 대충 계산한 값을 앉힘)라서 왕복 계약으로는
안 잡힌다. 그래서 별도의 규칙을 둔다:

> 판정 지표는 값과 함께 **판정 근거(`*_source`)** 를 emit 한다.
> north-star 는 추가로 **측정 여부(`*_measured`)** 를 emit 하고, 측정 못 했으면
> 0 이 아니라 *미측정* 으로 렌더한다.

근거를 강제하면 proxy 로 때운 지표가 payload 에 그대로 드러난다.

**한계 (과장하지 않는다)**: 근거 이름을 그럴듯하게 지어 붙이면 이 check 는 통과한다.
본 smoke 가 구조적으로 보장하는 것은 (a) 근거 field 자체의 존재, (b) '아직 안 정했다'
류 표현의 배제, (c) **새 north-star 가 registry 를 우회할 수 없다**는 것 — 이 셋이다.
근거가 *사실인지* 는 여전히 `check_writer_reader_roundtrip.py` 같은 실측 계약이 본다.

Test list (5 case):
1. test_every_judgment_metric_emits_its_source
2. test_source_never_contains_forbidden_token
3. test_north_star_metrics_emit_measured_flag
4. test_unmeasured_north_star_renders_as_unmeasured
5. test_registry_covers_every_declared_north_star

Cross-ref: releases/Beta-v1.0.0.md §2.19 / §2.22.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.dashboard_data import (  # noqa: E402
    FORBIDDEN_SOURCE_TOKENS,
    JUDGMENT_METRICS,
    _render_panel_1,
    _render_panel_6,
    collect_dashboard_snapshot,
)

REPO_ROOT = SOURCE_ROOT.parent


def _panels() -> dict:
    snapshot = collect_dashboard_snapshot(REPO_ROOT)
    return snapshot.get("panels", snapshot)


# --- Tests ---


def test_every_judgment_metric_emits_its_source() -> None:
    """등록된 판정 지표는 값과 근거를 **둘 다** emit 한다."""
    panels = _panels()
    problems: list[str] = []
    for c in JUDGMENT_METRICS:
        panel = panels.get(c.panel)
        if not isinstance(panel, dict):
            problems.append(f"{c.panel} panel 부재")
            continue
        if c.metric not in panel:
            problems.append(f"{c.panel}.{c.metric} 값 부재")
        source = panel.get(c.source)
        if not source:
            problems.append(f"{c.panel}.{c.metric} 의 근거 `{c.source}` 부재/빈 값")
    assert not problems, "판정 근거 누락:\n  " + "\n  ".join(problems)


def test_source_never_contains_forbidden_token() -> None:
    """근거 자리에 'proxy' / 'placeholder' 같은 미정 표현이 오면 안 된다."""
    panels = _panels()
    problems: list[str] = []
    for c in JUDGMENT_METRICS:
        source = str(panels.get(c.panel, {}).get(c.source, "")).lower()
        for token in FORBIDDEN_SOURCE_TOKENS:
            if token in source:
                problems.append(f"{c.panel}.{c.metric} 근거가 `{source}` — '{token}' 은 근거가 아니다")
    assert not problems, "\n  ".join(problems)


def test_north_star_metrics_emit_measured_flag() -> None:
    """north-star 는 '재봤는가' 를 별도로 말한다 — 0 과 미측정은 다른 상태다."""
    panels = _panels()
    problems: list[str] = []
    for c in JUDGMENT_METRICS:
        if not c.measured:
            continue
        panel = panels.get(c.panel, {})
        if not isinstance(panel.get(c.measured), bool):
            problems.append(f"{c.panel}.{c.measured} 가 bool 이 아니다: {panel.get(c.measured)!r}")
    assert not problems, "\n  ".join(problems)


def test_unmeasured_north_star_renders_as_unmeasured() -> None:
    """측정 못 한 north-star 는 렌더에서 0 이 아니라 '미측정' 으로 보여야 한다."""
    unmeasured_panel_1 = {
        "silent_failing_cycles_count": 0,
        "silent_failing_cycles_measured": False,
        "silent_failing_cycles_source": "ledger",
    }
    rendered_1 = "\n".join(_render_panel_1(unmeasured_panel_1))
    assert "미측정" in rendered_1, rendered_1

    unmeasured_panel_6 = {
        "north_star": "multi_agent_concurrent_write_conflict_count",
        "conflict_count": 0,
        "conflict_count_measured": False,
        "conflict_count_source": "unknown",
        "status": "unknown",
    }
    rendered_6 = "\n".join(_render_panel_6(unmeasured_panel_6))
    assert "미측정" in rendered_6, rendered_6
    # threshold 의 `0` 은 정상이므로 conflict_count 줄만 본다.
    count_line = next(line for line in rendered_6.splitlines() if "conflict_count:" in line)
    assert "`0`" not in count_line, f"측정도 안 하고 0 을 값처럼 보여주고 있다: {count_line}"


def test_registry_covers_every_declared_north_star() -> None:
    """`north_star` 를 선언한 panel 은 반드시 registry 에 등록돼 있어야 한다.

    새 north-star 를 추가하면서 근거 규칙을 빠뜨리는 경로를 막는다.
    """
    panels = _panels()
    registered = {c.panel for c in JUDGMENT_METRICS}
    problems = [
        f"{name} 이 north_star(`{data['north_star']}`) 를 선언했는데 JUDGMENT_METRICS 미등록"
        for name, data in panels.items()
        if isinstance(data, dict) and data.get("north_star") and name not in registered
    ]
    assert not problems, "\n  ".join(problems)


def main() -> int:
    test_funcs = [
        test_every_judgment_metric_emits_its_source,
        test_source_never_contains_forbidden_token,
        test_north_star_metrics_emit_measured_flag,
        test_unmeasured_north_star_renders_as_unmeasured,
        test_registry_covers_every_declared_north_star,
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
