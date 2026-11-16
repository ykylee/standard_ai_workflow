#!/usr/bin/env python3
"""drift prevention 가드 출력 해석은 한 함수 — release self-recover 재검사의 집계 (TASK-2026-11-16-main-011).

release_pipeline 의 사본이 case 수 6 을 리터럴로 가져, 가드가 7 case 가 된 뒤 재검사가 `cases_pass 7 > cases_total 6` 을 냈다.

1. 실제 가드 — release 재검사의 pass + fail = total 이고 total 은 가드 파일의 case 수(`def test_case_` 개수, 바깥 증인)다
2. 합성 출력 — 일부 실패 · 요약 줄만 · 요약과 줄 수 불일치(사유 기록) · 가드가 돌지 못함(error) 을 바르게 센다
3. 한 출처 — release_pipeline 은 공용 파서를 부르고 case 수 리터럴 · 자체 정규식이 없다; 대시보드 · release_v0_13_0 도 같은 파서
4. 불일치는 소비자까지 간다 — release 재검사 결과의 `mismatch`, 대시보드 렌더(markdown · html)의 `guard_mismatch`
5. release_v0_13_0 preflight — 실제 가드 · 대시보드 검사가 green 이면 True (옛 "6/6" · "10/10" 문자열 대조는 늘 False 였다)
6. 가드를 돌리지 않은 대시보드 패널(inline_guard=False)은 센 값을 null · guard_measured=false 로 싣고 렌더가 '미측정' 을 보인다 —
   기대값 7 을 실측 자리에 싣지 않는다 (TASK-2026-11-16-main-012); 측정한 패널의 렌더는 그대로다
7. 가드를 돌렸지만 실패한 패널(실패 출력 · 시간 초과 · 가드 파일 없음)도 센 값은 null · 사유 guard_error · guard_measured=false,
   렌더는 '측정 실패 — 사유' 이고 '0/0' 을 그리지 않는다 (TASK-2026-11-16-main-015)
"""

from __future__ import annotations

#: 실제 가드 · 대시보드 검사를 subprocess 로 돈다.
CHECK_TIMEOUT_S = 240

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    # 실제 가드 · 대시보드 검사를 돌린다 — 그 둘의 입력 표면을 함께 진다.
    # case 6 은 살아 있는 저장소에서 collect_drift_prevention 을 부른다 — 메모리 · 원장 · 문서를 읽는다.
    "ai-workflow/*",
    "docs/*",
    "LICENSE",
    "README.md",
    "workflow-source/LICENSE",
    "workflow-source/core/*",
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/check_drift_prevention_v0_11_23.py",
    "workflow-source/tests/check_quality_dashboard_v0_13_0.py",
)

import re
import sys
import traceback
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import dashboard_data  # noqa: E402
from workflow_kit.common.dashboard_data import collect_drift_prevention, parse_drift_guard_output  # noqa: E402
from unittest import mock  # noqa: E402
import subprocess  # noqa: E402

from workflow_kit.common import dashboard_render_html, dashboard_render_markdown  # noqa: E402
from workflow_kit.tools import release_pipeline, release_v0_13_0  # noqa: E402

FAILURES: list[str] = []
GUARD = SOURCE_ROOT / "tests" / "check_drift_prevention_v0_11_23.py"


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def case_real_guard() -> list[str]:
    problems: list[str] = []
    expected = len(re.findall(r"^def test_case_", GUARD.read_text(encoding="utf-8"), flags=re.M))
    result = release_pipeline._run_drift_prevention_smoke()
    if result["cases_pass"] + result["cases_fail"] != result["cases_total"]:
        problems.append(f"집계가 맞지 않는다: {result}")
    if result["cases_total"] != expected:
        problems.append(f"total {result['cases_total']} 이 가드 파일의 case 수 {expected} 와 다르다")
    if result["guard_status"] == "pass" and result["cases_pass"] != expected:
        problems.append(f"pass 인데 cases_pass {result['cases_pass']} ≠ {expected}")
    return problems


def case_synthetic() -> list[str]:
    problems: list[str] = []
    lines = [f"  PASS: test_case_{i}" for i in range(1, 6)] + ["  FAIL: test_case_6", "  FAIL: test_case_7"]
    partial = parse_drift_guard_output("\n".join(lines + ["=== FAIL: 5/7 ==="]), 1)
    if (partial["status"], partial["passed"], partial["failed"], partial["total"], partial["mismatch"]) != (
            "fail", 5, 2, 7, None):
        problems.append(f"일부 실패: {partial}")
    summary_only = parse_drift_guard_output("=== PASS: 7/7 ===", 0)
    if (summary_only["passed"], summary_only["total"], summary_only["status"]) != (7, 7, "pass"):
        problems.append(f"요약만: {summary_only}")
    seven = [f"  PASS: test_case_{i}" for i in range(1, 8)]
    skew = parse_drift_guard_output("\n".join(seven + ["=== PASS: 6/6 ==="]), 0)
    if skew["total"] != 7 or skew["passed"] != 7 or not skew["mismatch"] or "6/6" not in skew["mismatch"]:
        problems.append(f"요약과 줄 수 불일치를 기록하지 않았다: {skew}")
    only_fail = parse_drift_guard_output("=== FAIL: 5/7 ===", 1)
    if (only_fail["status"], only_fail["passed"], only_fail["failed"], only_fail["total"]) != ("fail", 5, 2, 7):
        problems.append(f"요약 줄만 있는 실패 — pass + fail = total 이 아니거나 error 로 봤다: {only_fail}")
    silent = parse_drift_guard_output("", 0)
    if (silent["status"], silent["total"]) != ("error", 0):
        problems.append(f"rc 0 · 빈 출력을 pass 로 봤다 — 아무것도 재지 않았다: {silent}")
    broken = parse_drift_guard_output("Traceback ...\nImportError: x", 1)
    if (broken["status"], broken["total"]) != ("error", 0):
        problems.append(f"가드가 돌지 못한 출력: {broken}")
    return problems


def case_single_source() -> list[str]:
    problems: list[str] = []
    source = (SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline.py").read_text(encoding="utf-8")
    body = source[source.index("def _run_drift_prevention_smoke"):]
    body = body[:body.index("\ndef ", 1)]
    if "parse_drift_guard_output" not in body:
        problems.append("release 재검사가 공용 파서를 부르지 않는다")
    if re.search(r"/6\b|\b6\s*[,}]", body) or re.search(r"\bre\.(?:search|findall|match|compile|fullmatch)\(", body):
        problems.append("release 재검사에 case 수 리터럴 또는 자체 정규식이 남아 있다")
    legacy = (SOURCE_ROOT / "workflow_kit" / "tools" / "release_v0_13_0.py").read_text(encoding="utf-8")
    drift_fn = legacy[legacy.index("def check_drift_prevention_6_of_6"):]
    drift_fn = drift_fn[:drift_fn.index("\ndef ", 1)]
    if "parse_drift_guard_output" not in drift_fn or re.search(r"\d+/\d+ ===", drift_fn):
        problems.append("release_v0_13_0 의 drift preflight 가 공용 파서를 쓰지 않거나 case 수 문자열을 대조한다")
    if re.search(r"[\x27\"]ALL \d+/\d+ CASES", legacy):
        problems.append("release_v0_13_0 에 대시보드 case 수 리터럴(10/10)이 남아 있다")
    dash = (SOURCE_ROOT / "workflow_kit" / "common" / "dashboard_data.py").read_text(encoding="utf-8")
    inline = dash[dash.index("def run_drift_prevention_guard_inline"):]
    inline = inline[:inline.index("\ndef ", 1)]
    if "parse_drift_guard_output(" not in inline:
        problems.append("대시보드 inline 가드가 공용 파서를 부르지 않는다")
    return problems


def case_mismatch_reaches_consumers() -> list[str]:
    problems: list[str] = []
    seven = "\n".join([f"  PASS: test_case_{i}" for i in range(1, 8)] + ["=== PASS: 6/6 ==="])
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout=seven, stderr="")
    with mock.patch("subprocess.run", return_value=fake):
        result = release_pipeline._run_drift_prevention_smoke()
    if result.get("cases_total") != 7 or result.get("cases_pass") != 7 or "6/6" not in str(result.get("mismatch")):
        problems.append(f"release 재검사 결과에 불일치가 실리지 않았다: {result}")
    panel = {"guard_status": "pass", "guard_cases": 7, "expected_cases": 7, "guard_mismatch": "요약 6/6 와 case 줄 7/7"}
    md = "\n".join(dashboard_render_markdown._render_panel_1(panel))
    if "guard_mismatch" not in md or "6/6" not in md:
        problems.append("대시보드 markdown 이 불일치를 보이지 않는다")
    html_text = dashboard_render_html._render_html_panel_1(panel)
    if "guard_mismatch" not in html_text:
        problems.append("대시보드 html 이 불일치를 보이지 않는다")
    clean = {k: v for k, v in panel.items() if k != "guard_mismatch"}
    if "guard_mismatch" in "\n".join(dashboard_render_markdown._render_panel_1(clean)):
        problems.append("불일치가 없는데 markdown 에 guard_mismatch 줄을 그렸다")
    return problems


def case_legacy_preflight() -> list[str]:
    problems: list[str] = []
    if release_v0_13_0.check_drift_prevention_6_of_6() is not True:
        problems.append("실제 drift 가드가 green 인데 release_v0_13_0 preflight 가 False 다")
    if release_v0_13_0.check_dashboard_smoke_10_of_10() is not True:
        problems.append("실제 대시보드 검사가 green 인데 release_v0_13_0 preflight 가 False 다")
    return problems


def case_unmeasured_panel() -> list[str]:
    problems: list[str] = []
    panel = collect_drift_prevention(SOURCE_ROOT.parent, inline_guard=False)
    got = {k: panel.get(k) for k in ("guard_measured", "guard_cases", "guard_cases_pass", "guard_cases_fail", "expected_cases")}
    if got != {"guard_measured": False, "guard_cases": None, "guard_cases_pass": None, "guard_cases_fail": None,
               "expected_cases": 7}:
        problems.append(f"가드를 돌리지 않았는데 센 값을 실었다: {got}")
    def guard_lines(text: str) -> str:  # 다른 필드(silent_failing 등)의 '미측정' 과 섞지 않는다
        return "\n".join(line for line in text.splitlines() if "guard_cases:" in line or "guard:" in line)

    md = guard_lines("\n".join(dashboard_render_markdown._render_panel_1(panel)))
    html_text = guard_lines(dashboard_render_html._render_html_panel_1(panel))
    for label, text, bad in (("markdown", md, "`7 / 7`"), ("html", html_text, "0/7 pass")):
        if "미측정" not in text or bad in text:
            problems.append(f"{label} 렌더가 미측정을 보이지 않거나 숫자를 지어냈다")
    inline = collect_drift_prevention(SOURCE_ROOT.parent, inline_guard=True)
    if inline.get("guard_measured") is not True or not isinstance(inline.get("guard_cases"), int):
        problems.append(f"가드를 돌린 패널이 측정 표식 · 정수 값을 싣지 않았다: "
                        f"{ {k: inline.get(k) for k in ('guard_measured', 'guard_cases', 'guard_status')} }")
    measured = {"guard_status": "pass", "guard_measured": True, "guard_cases": 7, "guard_cases_pass": 7,
                "guard_cases_fail": 0, "expected_cases": 7, "guard_runtime_ms": 88}
    md_m = guard_lines("\n".join(dashboard_render_markdown._render_panel_1(measured)))
    html_m = guard_lines(dashboard_render_html._render_html_panel_1(measured))
    if "- guard_cases: `7 / 7`" not in md_m or "guard: 7/7 pass (expected 7)" not in html_m or "미측정" in md_m + html_m:
        problems.append("측정한 패널의 렌더가 바뀌었다")
    return problems


def case_failed_guard_panel() -> list[str]:
    problems: list[str] = []
    import tempfile

    def guard_lines(text: str) -> str:
        return "\n".join(line for line in text.splitlines() if "guard_cases:" in line or "guard:" in line)

    crashed = subprocess.CompletedProcess(args=[], returncode=1, stdout="Traceback (most recent call last):\n",
                                          stderr="ImportError: boom-import\n")
    empty = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    scenarios = (
        ("실패 출력", {"return_value": crashed}, "boom-import"),
        ("rc 0 · 빈 출력", {"return_value": empty}, "case 를 내지 못했다"),
        ("시간 초과", {"side_effect": subprocess.TimeoutExpired(cmd="x", timeout=30)}, "시간 초과"),
        ("실행 실패(OSError)", {"side_effect": OSError("exec format error")}, "OSError"),
    )
    for label, kwargs, needle in scenarios:
        with mock.patch.object(dashboard_data.subprocess, "run", **kwargs):
            panel = collect_drift_prevention(SOURCE_ROOT.parent, inline_guard=True)
        got = {k: panel.get(k) for k in ("guard_status", "guard_cases", "guard_cases_pass", "guard_cases_fail",
                                         "guard_measured")}
        if got != {"guard_status": "error", "guard_cases": None, "guard_cases_pass": None, "guard_cases_fail": None,
                   "guard_measured": False} or needle not in str(panel.get("guard_error")):
            problems.append(f"{label}: 실패한 가드가 센 값을 실었거나 사유가 없다: {got} · {panel.get('guard_error')}")
        md = guard_lines("\n".join(dashboard_render_markdown._render_panel_1(panel)))
        html_text = guard_lines(dashboard_render_html._render_html_panel_1(panel))
        for kind, text in (("markdown", md), ("html", html_text)):
            if "측정 실패" not in text or needle not in text or "0/0" in text or "`0 /" in text:
                problems.append(f"{label} · {kind}: '측정 실패 — 사유' 가 아니거나 0 을 그렸다: {text!r}")
    with tempfile.TemporaryDirectory(prefix="drift-noguard-") as td:
        missing = dashboard_data.run_drift_prevention_guard_inline(Path(td))
    if missing.get("guard_cases") is not None or "가드 파일이 없다" not in str(missing.get("guard_error")):
        problems.append(f"가드 파일이 없는데 센 값을 실었거나 사유가 없다: {missing}")
    return problems


CASES = (
    ("1 실제 가드 — pass + fail = total = 가드 파일의 case 수", case_real_guard),
    ("2 합성 출력 — 일부 실패 · 요약만 · 불일치 기록 · error", case_synthetic),
    ("3 한 출처 — release · 대시보드 · release_v0_13_0 이 같은 파서, 리터럴 없음", case_single_source),
    ("4 불일치는 release 결과 · 대시보드 렌더까지 간다", case_mismatch_reaches_consumers),
    ("5 release_v0_13_0 preflight 가 실제 green 에 True", case_legacy_preflight),
    ("6 가드를 돌리지 않은 패널은 미측정", case_unmeasured_panel),
    ("7 가드가 실패한 패널은 측정 실패 · 0 을 그리지 않는다", case_failed_guard_panel),
)


def main() -> int:
    print("check_drift_guard_parse — drift 가드 출력 해석 단일 출처 (TASK-2026-11-16-main-011)")
    for name, case in CASES:
        try:
            _record(name, case())
        except Exception:  # noqa: BLE001 — case 하나의 예외는 그 case 의 FAIL 이다
            _record(name, ["예외: " + traceback.format_exc().strip().splitlines()[-1]])
            traceback.print_exc()
    print(f"\n{len(CASES) - len(FAILURES)}/{len(CASES)} PASS")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
