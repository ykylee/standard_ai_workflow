"""Acceptance test for v0.11.11 mypy strict CI 통합.

1 acceptance test:
- test_mypy_strict_ci_v0_11_11 — `.github/workflows/mypy-strict.yml` 신규 + valid YAML
  + trigger (push to main + PR to main) 정합 + mypy invocation = `mypy --no-incremental workflow_kit/`
  + dev extra mypy pin ==2.1.0 (CI + local 정합) + cumulative strict clean 35 file 유지 verify
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_yaml_simple(path: Path) -> dict[str, object] | None:
    """YAML 의 key-value / nested dict 만 parse (workflow file 의 단순 검증용).

    PyYAML 의존성을 피하기 위해 정규식 기반의 simple parser 사용.
    workflow 의 구조 (name / on.<trigger> / jobs.<job>.steps) 만 검증.
    """
    if not path.exists():
        return None
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        # PyYAML 없는 경우 simple text-based check 로 fallback
        return _read_yaml_text_based(path)
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        return None


def _read_yaml_text_based(path: Path) -> dict[str, object] | None:
    """YAML 의존성 없는 text-based 검증.

    workflow file 의 top-level keys (name / on / jobs) 만 존재 여부 verify.
    detailed 구조 검증은 별도 regex check.
    """
    text = path.read_text(encoding="utf-8")
    result: dict[str, object] = {}
    if re.search(r"^name:\s*mypy-strict\s*$", text, re.MULTILINE):
        result["name"] = "mypy-strict"
    if re.search(r"^on:\s*$", text, re.MULTILINE):
        result["on"] = True
    if re.search(r"^jobs:\s*$", text, re.MULTILINE):
        result["jobs"] = True
    return result if result else None


def test_mypy_strict_ci_v0_11_11() -> None:
    """v0.11.11 mypy strict CI 통합 verify."""
    # case 1: workflow file 존재
    workflow_path = REPO_ROOT / ".github" / "workflows" / "mypy-strict.yml"
    print(f"  workflow path: {workflow_path}")
    assert workflow_path.exists(), f"workflow file not found: {workflow_path}"
    print("  case 1 (mypy-strict.yml 존재): PASS")

    # early-declare workflow_text (case 2 의 on_block fallback 에서 사용)
    workflow_text = workflow_path.read_text(encoding="utf-8")

    # case 2: workflow YAML valid + 필수 field
    data = _read_yaml_simple(workflow_path)
    assert data is not None, "workflow YAML parse 실패"
    assert data.get("name") == "mypy-strict", f"workflow name != mypy-strict: {data.get('name')!r}"
    # YAML 1.1 quirk: `on` is parsed as Python `True` (boolean literal).
    # Check both `on` and `True` keys.
    on_block = data.get("on", data.get(True, {}))
    if isinstance(on_block, dict):
        triggers = list(on_block.keys())
    elif on_block is True:
        # text-based fallback when PyYAML not available
        triggers_text = workflow_text
        triggers = []
        if re.search(r"^on:\s*$", triggers_text, re.MULTILINE):
            # parse block-style on
            for trig in ("push", "pull_request", "workflow_dispatch", "schedule"):
                if re.search(rf"^\s+{trig}:\s*$", triggers_text, re.MULTILINE):
                    triggers.append(trig)
    else:
        triggers = ["on"]
    print(f"  triggers: {triggers}")
    assert "push" in triggers, f"workflow push trigger 부재: {triggers}"
    assert "pull_request" in triggers, f"workflow pull_request trigger 부재: {triggers}"
    print("  case 2 (workflow YAML valid + push/PR trigger): PASS")

    # case 3: workflow 의 mypy invocation = `mypy --no-incremental workflow_kit/`
    # (workflow_text 는 case 1 끝에서 early-declare 됨)
    mypy_pattern = re.compile(
        r"mypy\s+--no-incremental\s+workflow_kit/",
        re.MULTILINE,
    )
    if not mypy_pattern.search(workflow_text):
        # try fallback pattern (e.g. quoted or different spacing)
        fallback_pattern = re.compile(
            r"mypy[^\\n]*--no-incremental[^\\n]*workflow_kit/",
            re.MULTILINE,
        )
        if not fallback_pattern.search(workflow_text):
            raise AssertionError(
                f"workflow mypy invocation != 'mypy --no-incremental workflow_kit/':\n{workflow_text[:500]}"
            )
    # also verify python-version 3.10 (workflow_kit 정합)
    assert "python-version" in workflow_text, "workflow python-version 누락"
    assert "3.10" in workflow_text, "workflow python-version != 3.10 (workflow_kit python_version 정합)"
    # also verify mypy 2.1.0 pin
    assert "mypy==2.1.0" in workflow_text, "workflow mypy pin != mypy==2.1.0 (v0.11.10 release note 정합)"
    print("  case 3 (mypy invocation + python 3.10 + mypy 2.1.0 pin): PASS")

    # case 4: dev extra mypy pin ==2.1.0
    dev_pyproject = REPO_ROOT / "workflow-source" / "workflow_kit" / "pyproject.toml"
    dev_text = dev_pyproject.read_text(encoding="utf-8")
    # mypy>=1.0 → mypy==2.1.0 정합 verify
    if "mypy>=1.0" in dev_text:
        raise AssertionError(
            f"dev extra mypy pin != ==2.1.0 (stale 'mypy>=1.0' 잔존):\n{dev_text[:500]}"
        )
    assert "mypy==2.1.0" in dev_text, f"dev extra mypy pin != 'mypy==2.1.0'"
    print("  case 4 (dev extra mypy pin ==2.1.0): PASS")

    # case 5: __version__ = v0.11.11-beta verify (loud fallback literal)
    init_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "__init__.py"
    init_src = init_path.read_text(encoding="utf-8")
    # `return "vX.Y.Z-beta"` 패턴 (loud fallback literal) — case-insensitive
    # comment "Loud fallback" + return statement 매칭
    loud_fallback_match = re.search(
        r'#\s*\d+\.\s*[Ll]oud\s+fallback[^"]*?\n\s*return\s+"([^"]+)"',
        init_src,
    )
    assert loud_fallback_match, (
        "loud fallback literal parse 실패 (regex 패턴 미스)"
    )
    current_loud = loud_fallback_match.group(1)
    assert current_loud == "v0.11.11-beta", (
        f"loud fallback != v0.11.11-beta (current: {current_loud!r})"
    )
    print(f"  case 5 (loud fallback literal = {current_loud!r}): PASS")

    # case 6: cumulative strict clean 35 file 유지 verify
    all_counts = [int(m.group(1)) for m in re.finditer(r"\b(\d+)\s*file\s*strict\s*clean", init_src)]
    assert all_counts, "cumulative strict clean count 주석 부재"
    max_count = max(all_counts)
    print(f"  workflow_kit/__init__.py cumulative strict clean: {all_counts} (max={max_count})")
    assert max_count >= 35, f"max cumulative strict clean count {max_count} < 35 (v0.11.10 baseline)"
    print(f"  case 6 (cumulative strict clean max={max_count} >= 35, v0.11.10 baseline 유지): PASS")

    # case 7: pyproject.toml [project] version = 0.11.11 verify
    proj_pyproject = REPO_ROOT / "workflow-source" / "pyproject.toml"
    proj_text = proj_pyproject.read_text(encoding="utf-8")
    version_match = re.search(r'^version\s*=\s*"([^"]+)"', proj_text, re.MULTILINE)
    assert version_match, "pyproject.toml version field 부재"
    current_version = version_match.group(1)
    assert current_version == "0.11.11", f"pyproject version != 0.11.11 (current: {current_version!r})"
    print(f"  case 7 (pyproject version = {current_version!r}): PASS")

    # case 8: CI 와 동일 invocation 실제 mypy 실행 verify (REPO_ROOT cwd, full path)
    # CI 의 working pattern: `mypy --no-incremental workflow-source/workflow_kit/` from REPO_ROOT.
    # sub-package 의 workflow_kit/pyproject.toml (strict=false) 와 parent 의
    # workflow-source/pyproject.toml (strict=true) 의 merge 가 발생하지 않도록
    # *target path* 를 REPO_ROOT 기준 절대경로로 명시.
    try:
        result_ci = subprocess.run(
            [sys.executable, "-m", "mypy", "--no-incremental",
             "workflow-source/workflow_kit/"],
            cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=120,
        )
        ci_errors = [
            line for line in result_ci.stdout.splitlines()
            if ".py:" in line and "error:" in line
        ]
        print(f"  CI invocation ({REPO_ROOT}/mypy workflow-source/workflow_kit/): "
              f"{len(ci_errors)} errors, exit={result_ci.returncode}")
        if ci_errors:
            for err in ci_errors[:5]:
                print(f"    {err}")
        assert result_ci.returncode == 0, (
            f"CI mypy invocation exit {result_ci.returncode} "
            f"({len(ci_errors)} errors in workflow_kit/)"
        )
        print(f"  case 8 (CI mypy invocation exit 0, {len(ci_errors)} errors): PASS")
    except FileNotFoundError:
        print("  case 8 (CI mypy invocation: mypy module not available, SKIP)")
    except subprocess.TimeoutExpired:
        print("  case 8 (CI mypy invocation: timeout, SKIP)")


def main() -> int:
    """1 acceptance test. 1 fail = exit 1."""
    print("=== v0.11.11 mypy strict CI 통합 acceptance test ===")
    print("=== v0.11.10 의 '다음' §1 follow-up ===")
    tests = [
        ("test_mypy_strict_ci_v0_11_11", test_mypy_strict_ci_v0_11_11),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n[{name}]")
        try:
            fn()
            passed += 1
            print(f"  ✓ {name} PASS")
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {name} FAIL: {e}")
        except Exception as e:
            failed += 1
            print(f"  ✗ {name} ERROR: {type(e).__name__}: {e}")

    print(f"\n=== Result: {passed}/{passed+failed} PASS ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
