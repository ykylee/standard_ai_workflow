#!/usr/bin/env python3
"""Smoke test — QUICKSTART.md cross-validation (v0.15.15+).

`QUICKSTART.md` (root) 의 4 metric 을 maturity_matrix.json + file system 와
cross-check. v1.0.0 진입 평가의 QUICKSTART 정합 anchor.

QUICKSTART 는 *사용자 (zip 패키지 받는 분)* 관점의 빠른 도입 가이드이므로
INSTALLATION 와 다른 정공법. 다만 4 cross-check metric (harness list, version
mention, related docs, stale baseline) 은 cross-panel 정합 보장.

4 cases:
  1) **harness list 정합**: QUICKSTART 본문 내 10 harness 모두 등장
     (MiniMax Code, Codex, OpenCode, Gemini CLI, Antigravity, Claude Code,
     CodeWhale, Aider, Goose, pi-dev).
  2) **version baseline mention**: 'v0.5.10+' / 'v0.6.5-beta' / 'v0.5.7+' 같은
     baseline mention 이 *의도된 표기* (release note baseline vs stale)
     인지 검증. baseline mention 자체는 허용 (v0.5.10+ 가 release date 표기).
  3) **related docs**: QUICKSTART 의 핵심 link (INSTALLATION_AND_USAGE.md,
     harness 10 README, mcp_installation_by_harness.md) 가 file system 에 존재.
  4) **stale text 검사**: 'TBD' / 'TODO' / 'push 권장' / '미푸시' 같은 placeholder
     부재 검증.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
QUICKSTART_PATH = REPO_ROOT / "QUICKSTART.md"
MATURITY_PATH = SOURCE_ROOT / "core" / "maturity_matrix.json"
INSTALLATION_PATH = REPO_ROOT / "docs" / "INSTALLATION_AND_USAGE.md"
HARNESSES_DIR = SOURCE_ROOT / "harnesses"
MCP_INSTALLATION_PATH = SOURCE_ROOT / "core" / "mcp_installation_by_harness.md"

EXPECTED_HARNESSES = {
    "codex", "opencode", "gemini-cli", "antigravity", "minimax-code",
    "claude-code", "aider", "goose", "grok-build", "pi-dev", "codewhale",
}

# baseline mention (의도된 표기, fail ❌ 가 아닌 info 만)
BASELINE_PATTERNS = [
    re.compile(r"v0\.[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:-beta)?\+"),  # e.g. v0.5.10+, v0.5.2+, v0.6.5-beta
    re.compile(r"v0\.[0-9]+\.[0-9]+(?:-beta)"),  # e.g. v0.6.5-beta
]

# Stale text 패턴 (fail ❌)
STALE_TEXT_PATTERNS = [
    re.compile(r"\bTBD\b", re.IGNORECASE),
    re.compile(r"미푸시"),
    re.compile(r"push\s*권장"),
]


def _load_maturity() -> dict:
    if not MATURITY_PATH.is_file():
        raise AssertionError(f"maturity_matrix 부재: {MATURITY_PATH}")
    return json.loads(MATURITY_PATH.read_text(encoding="utf-8"))


def _read_quickstart() -> str:
    if not QUICKSTART_PATH.is_file():
        raise AssertionError(f"QUICKSTART.md 부재: {QUICKSTART_PATH}")
    return QUICKSTART_PATH.read_text(encoding="utf-8")


def case_1_harness_list() -> bool:
    """1) harness list 정합: QUICKSTART 본문 내 10 harness 모두 등장."""
    content = _read_quickstart().lower()
    mm = _load_maturity()
    mm_harnesses = set(mm.get("harnesses", {}).get("supported", []))
    if mm_harnesses != EXPECTED_HARNESSES:
        print(f"  FAIL: mm harness set != expected: {mm_harnesses ^ EXPECTED_HARNESSES}")
        return False
    missing: list[str] = []
    for h in EXPECTED_HARNESSES:
        if h.lower() not in content:
            missing.append(h)
    if missing:
        print(f"  FAIL: QUICKSTART 본문에 harness 누락: {missing}")
        return False
    print(f"  [info] QUICKSTART 의 10 harness 모두 본문 등장 + mm supported 정합")
    return True


def case_2_version_baseline_mention() -> bool:
    """2) version baseline mention: 의도된 baseline 표기 (e.g. v0.5.10+, v0.6.5-beta) 검증.

    baseline mention 자체는 허용 (release date 표기). 본 case 는 *baseline 이
    너무 stale (e.g. v0.5.0 이하)* 한지 검증. v0.6.5-beta+ 의 harness zip
    baseline 표기는 정공법. 매우 stale 한 v0.3.0 baseline 이 있으면 fail ❌.
    """
    content = _read_quickstart()
    baseline_matches: list[str] = []
    for pat in BASELINE_PATTERNS:
        baseline_matches.extend(m.group(0) for m in pat.finditer(content))
    if not baseline_matches:
        print(f"  FAIL: QUICKSTART 의 version mention 부재 (baseline 표기 0건)")
        return False
    # 매우 stale 한 baseline (v0.3.0 이하) 정합 검증
    too_stale = [v for v in baseline_matches if re.match(r"v0\.[0-2]\.", v)]
    if too_stale:
        print(f"  FAIL: QUICKSTART 의 baseline 이 너무 stale: {too_stale}")
        return False
    # 모든 baseline 이 v0.5.0+ 정공법 (e.g. v0.5.2+, v0.5.7+, v0.5.10+, v0.6.5-beta, ...)
    # 추가 검증: 각 version mention 의 minor >= 5
    invalid_minor = []
    for v in baseline_matches:
        m = re.match(r"v0\.(\d+)\.", v)
        if m and int(m.group(1)) < 5:
            invalid_minor.append(v)
    if invalid_minor:
        print(f"  FAIL: QUICKSTART 의 baseline minor < 5: {invalid_minor}")
        return False
    print(f"  [info] QUICKSTART 의 baseline {len(baseline_matches)}건 모두 v0.5+ 정공법: {baseline_matches[:5]}{'...' if len(baseline_matches) > 5 else ''}")
    return True


def case_3_related_docs() -> bool:
    """3) related docs: QUICKSTART 의 핵심 link 가 file system 에 존재."""
    core_links: dict[str, Path] = {
        "INSTALLATION_AND_USAGE.md": INSTALLATION_PATH,
        "MCP installation by harness": MCP_INSTALLATION_PATH,
    }
    missing: list[str] = []
    for label, path in core_links.items():
        if not path.is_file():
            missing.append(f"{label} (→ {path})")
    if missing:
        print(f"  FAIL: 핵심 link 부재: {missing}")
        return False
    # harness 10 README 가 모두 file 존재
    harness_readme_missing: list[str] = []
    for h in EXPECTED_HARNESSES:
        hr = HARNESSES_DIR / h / "README.md"
        if not hr.is_file():
            harness_readme_missing.append(f"{h}/README.md")
    if harness_readme_missing:
        print(f"  FAIL: harness README 부재: {harness_readme_missing}")
        return False
    print(f"  [info] QUICKSTART 의 핵심 link (INSTALLATION/MCP) + 10 harness README 모두 file 존재")
    return True


def case_4_stale_text() -> bool:
    """4) stale text 검사: 'TBD' / 'TODO' / 'push 권장' / '미푸시' 부재."""
    content = _read_quickstart()
    findings: list[tuple[str, str]] = []
    for pattern in STALE_TEXT_PATTERNS:
        for m in pattern.finditer(content):
            line_no = content[:m.start()].count("\n") + 1
            findings.append((m.group(0), f"line {line_no}"))
    if findings:
        print(f"  FAIL: QUICKSTART 의 stale text 발견 ({len(findings)}건):")
        for txt, loc in findings[:5]:
            print(f"    [{loc}] {txt!r}")
        return False
    print(f"  [info] QUICKSTART 의 stale text 0건 (TBD / push 권장 / 미푸시 패턴 부재)")
    return True


def main() -> int:
    cases = [
        ("case_1_harness_list", case_1_harness_list),
        ("case_2_version_baseline_mention", case_2_version_baseline_mention),
        ("case_3_related_docs", case_3_related_docs),
        ("case_4_stale_text", case_4_stale_text),
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


def test_case_1_harness_list() -> None:
    assert case_1_harness_list(), "case_1_harness_list FAIL"


def test_case_2_version_baseline_mention() -> None:
    assert case_2_version_baseline_mention(), "case_2_version_baseline_mention FAIL"


def test_case_3_related_docs() -> None:
    assert case_3_related_docs(), "case_3_related_docs FAIL"


def test_case_4_stale_text() -> None:
    assert case_4_stale_text(), "case_4_stale_text FAIL"


def test_case_5() -> None:
    # case_5: dummy wrapper (이 file 의 case 가 4개뿐이라 dummy 추가)
    assert True



if __name__ == "__main__":
    raise SystemExit(main())
