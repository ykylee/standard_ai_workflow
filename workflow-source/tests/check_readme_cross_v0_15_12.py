#!/usr/bin/env python3
"""Smoke test — README.md cross-validation (v0.15.12+).

`README.md` (root) 의 4 metric 을 `pyproject.toml` + `maturity_matrix.json` +
file system 와 cross-check. v1.0.0 진입 평가의 README 정합 anchor.

4 cases:
  1) **README 헤더 버전 정합**: `**버전: vX.Y.Z**` 가 `pyproject.toml` 의
     `[project] version` 과 정합 (drift prevention case_4 의 *재 verify* leg).
  2) **README harness list 정합**: README 본문에 10 harness 가 모두 언급
     + maturity_matrix `harnesses.supported` list 와 정합 (10개).
  3) **README 헤더 줄 버전 리터럴 정합**: 헤더 `- 버전:` 줄의 네 자리
     (`- 버전: vX.Y.Z` / `package: standard-ai-workflow X.Y.Z` /
     ``runtime `__version__` = X.Y.Z`` / `latest tag **vX.Y.Z**`) 가 모두
     pyproject version 과 정합 (v1.9.2 — 이전에는 `package:` 하나만 봤다).
  4) **README stale text 검사**: "미푸시" / "push 권장" 등 명백한 stale
     placeholder text 부재 검증 (drift prevention smoke 미커버 영역).
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "README.md",
    "workflow-source/core/*",
    "workflow-source/pyproject.toml",
    # v1.9.2: 헤더 줄 리터럴 패턴의 정본이 kit 안에 있다 (TASK-2026-09-03-main-004).
    # `workflow_kit.common` 하나를 import 해도 패키지 `__init__` 이 딸려 오므로
    # 선언도 그 폭이어야 한다 — 게이트 채취 실측에서 41건이 선언 밖으로 잡혔다.
    "workflow-source/workflow_kit/*",
)

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import readme_version  # noqa: E402

PYPROJECT_PATH = SOURCE_ROOT / "pyproject.toml"
MATURITY_PATH = SOURCE_ROOT / "core" / "maturity_matrix.json"
README_PATH = REPO_ROOT / "README.md"

PYPROJECT_VERSION_RE = re.compile(r'version\s*=\s*"([\d.]+)"')
# v1.2.1: stable 정리로 `-beta` 접미사 제거. 구 포맷도 받아 준다.
README_HEADER_VERSION_RE = re.compile(r"- 버전:\s*v([\d.]+)(?:-beta)?")
# 10 harness 정합 (case_2) — README 본문에 등장해야 함
EXPECTED_HARNESSES = {
    "codex", "opencode", "antigravity", "minimax-code",
    "claude-code", "aider", "goose", "grok-build", "pi-dev", "codewhale",
}

# Stale text 패턴 (case_4)
STALE_TEXT_PATTERNS = [
    re.compile(r"미푸시"),
    re.compile(r"push\s*권장"),
    re.compile(r"TBD", re.IGNORECASE),
]


def _read_pyproject_version() -> str:
    if not PYPROJECT_PATH.is_file():
        raise AssertionError(f"pyproject.toml 부재: {PYPROJECT_PATH}")
    m = PYPROJECT_VERSION_RE.search(PYPROJECT_PATH.read_text(encoding="utf-8"))
    if not m:
        raise AssertionError("pyproject.toml version field 부재")
    return m.group(1)


def _read_maturity() -> dict:
    if not MATURITY_PATH.is_file():
        raise AssertionError(f"maturity_matrix 부재: {MATURITY_PATH}")
    import json
    return json.loads(MATURITY_PATH.read_text(encoding="utf-8"))


def _read_readme() -> str:
    if not README_PATH.is_file():
        raise AssertionError(f"README.md 부재: {README_PATH}")
    return README_PATH.read_text(encoding="utf-8")


def case_1_readme_header_version() -> bool:
    """1) README 헤더 버전 정합: '- 버전: vX.Y.Z' == pyproject version."""
    py_ver = _read_pyproject_version()
    expected = f"v{py_ver}"
    content = _read_readme()
    m = README_HEADER_VERSION_RE.search(content)
    if not m:
        print(f"  FAIL: README.md 헤더 버전 ('- 버전: vX.Y.Z-beta') 부재")
        return False
    actual = m.group(1)
    if actual != py_ver:
        print(f"  FAIL: README 헤더 버전 v{actual}-beta != pyproject v{py_ver}-beta")
        return False
    print(f"  [info] README 헤더 버전 == v{py_ver}-beta (pyproject + README 2-way 정합)")
    return True


def case_2_readme_harness_list() -> bool:
    """2) README harness list 정합: 10 harness 모두 README 본문에 등장 + mm supported 정합."""
    content = _read_readme().lower()
    mm = _read_maturity()
    mm_harnesses = set(mm.get("harnesses", {}).get("supported", []))
    if mm_harnesses != EXPECTED_HARNESSES:
        print(f"  FAIL: mm harness set != expected: {mm_harnesses ^ EXPECTED_HARNESSES}")
        return False
    # 각 harness 가 README 본문에 등장 (대소문자 무시)
    missing: list[str] = []
    for h in EXPECTED_HARNESSES:
        if h.lower() not in content:
            missing.append(h)
    if missing:
        print(f"  FAIL: README 본문에 harness 누락: {missing}")
        return False
    print(f"  [info] 10 harness 모두 README 본문 등장 + mm supported 정합")
    return True


def case_3_readme_header_line_versions() -> bool:
    """3) 헤더 `- 버전:` 줄의 버전 리터럴 4개 == pyproject version.

    v1.9.2 이전에는 `package: standard-ai-workflow X.Y.Z` 하나만 봤다.
    같은 줄의 ``runtime `__version__` `` 과 `latest tag **v…**` 는 **어떤
    검사도 보지 않았고**, 자동 수리도 닿지 않아 네 사이클 연속 손으로 고쳤다
    (TASK-2026-09-03-main-004). 판정 패턴은 수리와 같은 정본
    (`workflow_kit.common.readme_version`) 에서 온다.
    """
    py_ver = _read_pyproject_version()
    content = _read_readme()
    if readme_version.header_line(content) is None:
        print("  FAIL: README.md 헤더 '- 버전: vX.Y.Z' 줄 부재")
        return False
    bad = readme_version.mismatches(content, py_ver)
    if bad:
        print(f"  FAIL: 헤더 줄 버전 리터럴 정합 위반 (pyproject={py_ver}): "
              + ", ".join(f"{label}={found!r}" for label, found in bad))
        return False
    print(f"  [info] 헤더 줄 버전 리터럴 {len(readme_version.LITERALS)}개 모두 {py_ver} 정합")
    return True


def case_4_readme_stale_text() -> bool:
    """4) README stale text 검사: '미푸시' / 'push 권장' / 'TBD' 같은 placeholder 부재."""
    content = _read_readme()
    findings: list[tuple[str, str]] = []
    for pattern in STALE_TEXT_PATTERNS:
        for m in pattern.finditer(content):
            # line number 산출
            line_no = content[:m.start()].count("\n") + 1
            findings.append((m.group(0), f"line {line_no}"))
    if findings:
        # warn only — fail ❌
        # rationale: stale text 는 smoke 가 더 정밀하게 분리 가능 (예: 'push 권장' 은
        # 일부 의도된 메시지일 수 있어, fail ❌ 가 아닌 warn 만 emit)
        # 다만 본 smoke 는 v0.15.12 의 정공법 anchor 이므로 *실제 발견 시* fail ❌
        print(f"  FAIL: README.md 의 stale text 발견 ({len(findings)}건):")
        for txt, loc in findings[:5]:
            print(f"    [{loc}] {txt!r}")
        return False
    print(f"  [info] README.md 의 stale text 0건 (미푸시 / push 권장 / TBD 패턴 부재)")
    return True


def main() -> int:
    cases = [
        ("case_1_readme_header_version", case_1_readme_header_version),
        ("case_2_readme_harness_list", case_2_readme_harness_list),
        ("case_3_readme_header_line_versions", case_3_readme_header_line_versions),
        ("case_4_readme_stale_text", case_4_readme_stale_text),
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


def test_case_1_readme_header_version() -> None:
    assert case_1_readme_header_version(), "case_1_readme_header_version FAIL"


def test_case_2_readme_harness_list() -> None:
    assert case_2_readme_harness_list(), "case_2_readme_harness_list FAIL"


def test_case_3_readme_header_line_versions() -> None:
    assert case_3_readme_header_line_versions(), "case_3_readme_header_line_versions FAIL"


def test_case_4_readme_stale_text() -> None:
    assert case_4_readme_stale_text(), "case_4_readme_stale_text FAIL"


if __name__ == "__main__":
    raise SystemExit(main())
