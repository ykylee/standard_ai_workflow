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


def _load_workflow(path: Path) -> dict[str, object]:
    """워크플로우 YAML 을 **진짜 파서**로 읽는다.

    v1.0.3: 이전의 `_read_yaml_simple` / `_read_yaml_text_based` 를 폐기했다.
    PyYAML 이 없으면 정규식 fallback 으로 내려가는 구조였는데, 그 fallback 안에
    결함이 있었다 — raw string 의 `[^\\n]` 이 "줄바꿈 제외"가 아니라 "역슬래시와
    문자 n 제외"로 해석돼 여러 줄 invocation 허용이 전혀 동작하지 않았다.
    게다가 fallback 이 도는 조건(PyYAML 부재)이 곧 CI 였다 — `pyyaml` 이 dev extra 에
    선언돼 있지 않았기 때문이다. 즉 CI 에서는 항상 결함 있는 경로로 돌았다.

    이제 `pyyaml` 은 dev extra 에 선언돼 있으므로 부재는 설치 결함이다 — hard fail 한다.
    `check_yaml_surfaces.py` 가 자체 YAML 파서의 재등장을 금지한다.
    """
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"workflow 최상위가 매핑이 아니다: {path}"
    return data


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
    data = _load_workflow(workflow_path)
    assert data.get("name") == "mypy-strict", f"workflow name != mypy-strict: {data.get('name')!r}"
    # YAML 1.1 quirk: 키 `on` 은 boolean `True` 로 파싱된다 — 두 키를 모두 본다.
    # v1.0.3: 정규식 fallback 분기 제거. 진짜 파서만 쓰므로 `on` 블록은 항상 매핑이다.
    on_block = data.get("on", data.get(True))
    assert isinstance(on_block, dict), f"`on` 블록이 매핑이 아니다: {on_block!r}"
    triggers = list(on_block)
    print(f"  triggers: {triggers}")
    assert "push" in triggers, f"workflow push trigger 부재: {triggers}"
    assert "pull_request" in triggers, f"workflow pull_request trigger 부재: {triggers}"
    print("  case 2 (workflow YAML valid + push/PR trigger): PASS")

    # case 3: workflow 의 mypy invocation.
    # (workflow_text 는 case 1 끝에서 early-declare 됨)
    #
    # v1.0.2: **`--config-file` 을 필수로 격상.** 이전 버전은
    # `mypy --no-incremental workflow_kit/` 를 요구했는데, 그 invocation 은 cwd 의
    # 암묵적 config 탐색에 기대고 있었고 REPO_ROOT 에는 [tool.mypy] 가 없어 실제로는
    # `Config File: Default` 로 떨어졌다. 즉 이 case 는 **깨진 invocation 을 고정** 하고
    # 있었다. 이제 config 명시를 요구한다.
    #
    # 이전 fallback regex `r"mypy[^\\n]*..."` 의 char class 는 raw string 이라
    # `[^\n]` 이 아니라 **`[^\\n]` (역슬래시와 문자 n 을 제외)** 로 해석됐다.
    # 줄바꿈 허용 의도가 전혀 동작하지 않았으므로 re.DOTALL 로 바로잡는다.
    assert "--no-incremental" in workflow_text, "workflow 에 --no-incremental 부재"
    mypy_pattern = re.compile(
        r"mypy\b.*?--config-file\s+workflow-source/pyproject\.toml.*?workflow-source/workflow_kit/",
        re.DOTALL,
    )
    if not mypy_pattern.search(workflow_text):
        raise AssertionError(
            "workflow mypy invocation 이 --config-file workflow-source/pyproject.toml 을 "
            "명시하지 않는다 — 암묵적 cwd 탐색은 REPO_ROOT 에서 Config File: Default 로 "
            f"떨어진다 (strict 미적용):\n{workflow_text[:800]}"
        )
    # also verify python-version 3.10 (workflow_kit 정합)
    assert "python-version" in workflow_text, "workflow python-version 누락"
    assert "3.10" in workflow_text, "workflow python-version != 3.10 (workflow_kit python_version 정합)"
    # also verify mypy 2.1.0 pin
    assert "mypy==2.1.0" in workflow_text, "workflow mypy pin != mypy==2.1.0 (v0.11.10 release note 정합)"
    print("  case 3 (mypy invocation + python 3.10 + mypy 2.1.0 pin): PASS")

    # case 4: dev extra mypy pin ==2.1.0
    #
    # v1.0.2: 참조 대상을 sub-package → 정본 `workflow-source/pyproject.toml` 로 교정.
    # v0.11.11 이 선언한 pin 통일 규약("CI 는 ==2.1.0, local dev 가 >=1.0 이면 drift")은
    # **sub-package pyproject 에만** 적용돼 있었고, 정작 smoke 가 설치하는 정본은
    # `mypy>=1.0` 이라 실제로는 2.3.0 이 깔렸다 — 규약이 아무것도 지키지 못하는 파일에
    # 걸려 있었다. sub-package 를 제거하고 핀을 정본으로 옮겼다.
    dev_pyproject = REPO_ROOT / "workflow-source" / "pyproject.toml"
    dev_text = dev_pyproject.read_text(encoding="utf-8")
    # v1.0.2: 판정 범위를 **`dev = [...]` 블록** 으로 좁힌다. 이전 판정은 파일 전체를
    # 부분문자열로 훑어, 규약의 *유래를 설명하는 주석* 에 옛 표기가 등장하기만 해도
    # FAIL 했다 (실제로 이 파일을 고치다 그렇게 걸렸다). 판정은 선언을 봐야지
    # 선언에 대한 설명을 보면 안 된다.
    dev_block_match = re.search(r"^dev\s*=\s*\[(.*?)\]", dev_text, re.MULTILINE | re.DOTALL)
    assert dev_block_match, "pyproject.toml 에 dev extra 블록 부재"
    dev_block = dev_block_match.group(1)
    mypy_reqs = re.findall(r'"(mypy[^"]*)"', dev_block)
    assert mypy_reqs == ["mypy==2.1.0"], (
        f"dev extra mypy pin != ['mypy==2.1.0'] (실제: {mypy_reqs}). "
        "CI 의 mypy-strict 는 ==2.1.0 을 깔고 smoke 는 이 extra 를 깐다 — "
        f"하한 지정이면 서로 다른 버전으로 strict 결과가 갈린다.\n블록: {dev_block.strip()}"
    )
    print("  case 4 (dev extra mypy pin ==2.1.0): PASS")

    # case 5: __version__ loud fallback literal == pyproject version verify
    init_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "__init__.py"
    init_src = init_path.read_text(encoding="utf-8")
    # `return "X.Y.Z"` 패턴 (loud fallback literal, v1.2.1 부터 PEP 440 그대로)
    # comment "Loud fallback" + return statement 매칭
    loud_fallback_match = re.search(
        r'#\s*\d+\.\s*[Ll]oud\s+fallback[^"]*?\n\s*return\s+"([^"]+)"',
        init_src,
    )
    assert loud_fallback_match, (
        "loud fallback literal parse 실패 (regex 패턴 미스)"
    )
    current_loud = loud_fallback_match.group(1)
    # v1.0.0: 특정 버전을 하드코딩하면 *릴리스마다* 본 smoke 가 깨진다 (v0.11.11-beta 고정이
    # v1.0.0-beta 로 올리며 red 가 된 사례). 검증 의도는 "loud fallback 이 현재 릴리스
    # 버전과 정합하는가" 이므로 pyproject.toml 을 SSOT 로 삼아 동적으로 비교한다.
    pyproject_text = (REPO_ROOT / "workflow-source" / "pyproject.toml").read_text(encoding="utf-8")
    version_match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject_text, re.M)
    assert version_match, "pyproject.toml 의 version parse 실패"
    # v1.2.1 (TASK-2026-08-13-main-007): stable 정리로 loud fallback 도
    # PEP 440 그대로다 — pyproject version 과 **문자 그대로** 같아야 한다.
    expected_loud = version_match.group(1)
    assert current_loud == expected_loud, (
        f"loud fallback != {expected_loud} (pyproject 기준). current: {current_loud!r}"
    )
    print(f"  case 5 (loud fallback literal = {current_loud!r}): PASS")

    # case 6: cumulative strict clean 35 file 유지 verify
    all_counts = [int(m.group(1)) for m in re.finditer(r"\b(\d+)\s*file\s*strict\s*clean", init_src)]
    assert all_counts, "cumulative strict clean count 주석 부재"
    max_count = max(all_counts)
    print(f"  workflow_kit/__init__.py cumulative strict clean: {all_counts} (max={max_count})")
    assert max_count >= 35, f"max cumulative strict clean count {max_count} < 35 (v0.11.10 baseline)"
    print(f"  case 6 (cumulative strict clean max={max_count} >= 35, v0.11.10 baseline 유지): PASS")

    # case 7: pyproject.toml [project] version 형식 verify
    # v1.0.0: 특정 버전 고정은 릴리스마다 red 를 만든다. case 5 가 이미 __init__ loud
    # fallback 과 pyproject 의 *정합* 을 검증하므로, 여기서는 semver 형식만 확인한다.
    proj_pyproject = REPO_ROOT / "workflow-source" / "pyproject.toml"
    proj_text = proj_pyproject.read_text(encoding="utf-8")
    version_match = re.search(r'^version\s*=\s*"([^"]+)"', proj_text, re.MULTILINE)
    assert version_match, "pyproject.toml version field 부재"
    current_version = version_match.group(1)
    assert re.fullmatch(r"\d+\.\d+\.\d+", current_version), (
        f"pyproject version 이 semver 형식이 아님: {current_version!r}"
    )
    print(f"  case 7 (pyproject version = {current_version!r}): PASS")

    # case 8: CI 와 동일 invocation 실제 mypy 실행 verify (REPO_ROOT cwd, full path)
    # CI 의 working pattern (v1.0.2+):
    #   `mypy --no-incremental --config-file workflow-source/pyproject.toml
    #    workflow-source/workflow_kit/` from REPO_ROOT.
    #
    # v1.0.2: `--config-file` 추가. 이전 case 8 은 CI invocation 을 *충실히 재현* 했지만
    # 재현 대상이 깨져 있었다 — 설정 없이 도는 실행을 그대로 복제하고 exit 0 을 확인하니
    # 당연히 green 이었다. **재현이 곧 검증은 아니다**: 무엇을 재현하는지도 함께 봐야 한다.
    # 그 "무엇" 은 check_mypy_config_actually_loaded.py 가 담당한다.
    try:
        result_ci = subprocess.run(
            [sys.executable, "-m", "mypy", "--no-incremental",
             "--config-file", "workflow-source/pyproject.toml",
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
