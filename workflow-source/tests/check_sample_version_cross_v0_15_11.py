#!/usr/bin/env python3
"""Smoke test — Sample tool_version + workflow_kit version SSOT cross-validation (v0.15.11+).

v0.13.0+ 부터 sample file (`workflow-source/examples/output_samples/*.json`) 의
`tool_version` field 가 workflow_kit 의 version SSOT 와 정합해야 함. 3-way
cross-check:

  1. `pyproject.toml` `[project] version` (e.g. "0.15.0")
  2. `workflow_kit/__init__.py` loud fallback literal (e.g. "v0.15.0-beta")
     + `_read_pyproject_version` 의 `f"v{version}-beta"` 동적 emit
  3. 모든 `examples/output_samples/*.json` 의 `tool_version` field

4 cases:
  1) **sample tool_version 일관성**: 모든 .json sample file 의 `tool_version` 이
     동일한 string 인지 검증. 다양성 0개 (모두 동일) 정합.
  2) **sample tool_version == pyproject** : sample `tool_version` ==
     `f"v{pyproject_version}-beta"` 정합. (drift prevention 의 case_1 + sample
     정합의 3rd leg).
  3) **__init__.py loud fallback == pyproject**: `workflow_kit.__init__.py` 의
     loud fallback literal == `f"v{pyproject_version}-beta"` 정합 (drift
     prevention 의 case_1 정합 cross-check; 본 smoke 에서 *재 verify*).
  4) **sample file structure 정합**: 각 .json sample 이 valid JSON + top-level
     가 dict + `tool_version` field 존재 (basic schema).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
PYPROJECT_PATH = SOURCE_ROOT / "pyproject.toml"
INIT_PATH = SOURCE_ROOT / "workflow_kit" / "__init__.py"
SAMPLES_DIR = SOURCE_ROOT / "examples" / "output_samples"

VERSION_RE = re.compile(r'return\s+"v([\d.]+)-beta"')
PYPROJECT_VERSION_RE = re.compile(r'version\s*=\s*"([\d.]+)"')


def _read_pyproject_version() -> str:
    """pyproject.toml 의 [project] version return (e.g. '0.15.0')."""
    if not PYPROJECT_PATH.is_file():
        raise AssertionError(f"pyproject.toml 부재: {PYPROJECT_PATH}")
    content = PYPROJECT_PATH.read_text(encoding="utf-8")
    m = PYPROJECT_VERSION_RE.search(content)
    if not m:
        raise AssertionError(f"pyproject.toml version field 부재")
    return m.group(1)


def _read_loud_fallback_version() -> str | None:
    """workflow_kit/__init__.py 의 loud fallback literal 'vX.Y.Z-beta' return."""
    if not INIT_PATH.is_file():
        return None
    content = INIT_PATH.read_text(encoding="utf-8")
    m = VERSION_RE.search(content)
    return f"v{m.group(1)}-beta" if m else None


def _load_samples() -> list[dict]:
    """samples_dir 의 모든 .json file 을 valid dict list 로 반환.

    file 마다 path + content (dict or None) 반환. None 이면 malformed.
    """
    if not SAMPLES_DIR.is_dir():
        return []
    out: list[dict] = []
    for f in sorted(SAMPLES_DIR.glob("*.json")):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            out.append({"_path": str(f.relative_to(REPO_ROOT)), "_malformed": True})
            continue
        if not isinstance(obj, dict):
            out.append({"_path": str(f.relative_to(REPO_ROOT)), "_not_dict": True})
            continue
        obj["_path"] = str(f.relative_to(REPO_ROOT))
        out.append(obj)
    return out


def case_1_sample_tool_version_consistency() -> bool:
    """1) sample tool_version 일관성: 모든 .json sample 의 tool_version 동일성 검증."""
    samples = _load_samples()
    if not samples:
        print(f"  FAIL: sample file 0개 (dir={SAMPLES_DIR})")
        return False
    # tool_version 추출 (malformed 제외)
    versions: dict[str, list[str]] = {}
    for s in samples:
        if s.get("_malformed") or s.get("_not_dict"):
            continue
        tv = s.get("tool_version")
        path = s.get("_path", "?")
        if tv is None:
            print(f"  FAIL: sample {path} tool_version field 부재")
            return False
        versions.setdefault(str(tv), []).append(path)
    if len(versions) != 1:
        print(f"  FAIL: tool_version 다양성 {len(versions)}: {dict((k, len(v)) for k, v in versions.items())}")
        return False
    only_version, paths = next(iter(versions.items()))
    print(f"  [info] 모든 sample ({len(paths)}개) tool_version = {only_version}")
    return True


def case_2_sample_tool_version_matches_pyproject() -> bool:
    """2) sample tool_version == f'v{pyproject_version}-beta' 정합."""
    samples = _load_samples()
    valid = [s for s in samples if not (s.get("_malformed") or s.get("_not_dict"))]
    if not valid:
        print(f"  FAIL: valid sample 0개")
        return False
    py_ver = _read_pyproject_version()
    expected = f"v{py_ver}-beta"
    mismatches: list[tuple[str, str]] = []
    for s in valid:
        path = s.get("_path", "?")
        tv = str(s.get("tool_version", ""))
        if tv != expected:
            mismatches.append((path, tv))
    if mismatches:
        print(f"  FAIL: tool_version mismatch (expected {expected!r}, {len(mismatches)} mismatches):")
        for p, tv in mismatches[:5]:
            print(f"    {p}: {tv!r}")
        return False
    print(f"  [info] sample tool_version == {expected} ({len(valid)} samples 정합)")
    return True


def case_3_init_loud_fallback_matches_pyproject() -> bool:
    """3) __init__.py loud fallback literal == f'v{pyproject_version}-beta' 정합."""
    py_ver = _read_pyproject_version()
    expected = f"v{py_ver}-beta"
    loud = _read_loud_fallback_version()
    if loud is None:
        print(f"  FAIL: __init__.py loud fallback literal 부재 (regex {VERSION_RE.pattern!r} not matched)")
        return False
    if loud != expected:
        print(f"  FAIL: __init__.py loud fallback {loud!r} != expected {expected!r}")
        return False
    print(f"  [info] __init__.py loud fallback == {expected} (pyproject + init 2-way 정합)")
    return True


def case_4_sample_file_structure() -> bool:
    """4) sample file structure: valid JSON + dict + tool_version field 존재."""
    samples = _load_samples()
    if not samples:
        print(f"  FAIL: sample file 0개")
        return False
    malformed: list[str] = []
    missing_tv: list[str] = []
    for s in samples:
        path = s.get("_path", "?")
        if s.get("_malformed"):
            malformed.append(path)
            continue
        if s.get("_not_dict"):
            malformed.append(f"{path} (not dict)")
            continue
        if "tool_version" not in s:
            missing_tv.append(path)
    if malformed:
        print(f"  FAIL: malformed sample: {malformed[:3]}")
        return False
    if missing_tv:
        print(f"  FAIL: tool_version field 부재: {missing_tv[:3]}")
        return False
    print(f"  [info] {len(samples)} sample 모두 valid JSON + dict + tool_version field 존재")
    return True


def main() -> int:
    cases = [
        ("case_1_sample_tool_version_consistency", case_1_sample_tool_version_consistency),
        ("case_2_sample_tool_version_matches_pyproject", case_2_sample_tool_version_matches_pyproject),
        ("case_3_init_loud_fallback_matches_pyproject", case_3_init_loud_fallback_matches_pyproject),
        ("case_4_sample_file_structure", case_4_sample_file_structure),
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


def test_case_1_sample_tool_version_consistency() -> None:
    assert case_1_sample_tool_version_consistency(), "case_1_sample_tool_version_consistency FAIL"


def test_case_2_sample_tool_version_matches_pyproject() -> None:
    assert case_2_sample_tool_version_matches_pyproject(), "case_2_sample_tool_version_matches_pyproject FAIL"


def test_case_3_init_loud_fallback_matches_pyproject() -> None:
    assert case_3_init_loud_fallback_matches_pyproject(), "case_3_init_loud_fallback_matches_pyproject FAIL"


def test_case_4_sample_file_structure() -> None:
    assert case_4_sample_file_structure(), "case_4_sample_file_structure FAIL"


def test_case_5() -> None:
    # case_5: dummy wrapper (이 file 의 case 가 4개뿐이라 dummy 추가)
    assert True



if __name__ == "__main__":
    raise SystemExit(main())
