"""Acceptance test for v0.11.11 mypy strict 통합.

1 acceptance test:
- test_mypy_strict_ci_v0_11_11 — dev extra mypy pin ==2.1.0 + loud fallback 정합
  + cumulative strict clean 35 file 유지 + pyproject version 형식
  + config 명시 mypy invocation 실제 실행 (exit 0)

2026-09-23 CI workflow 폐지(TASK-2026-09-23-main-022)로 `.github/workflows/mypy-strict.yml`
이 삭제돼, 그 파일을 재던 case 1~3(존재 · YAML/트리거 · invocation/핀)은 대상을 잃어
삭제했다. 남은 case 는 번호를 유지한다 (4~8). strict 검사는 이제 로컬 게이트에서
case 8 과 `check_mypy_config_actually_loaded` 가 돈다.
"""
from __future__ import annotations

import re
import subprocess
import os
import tempfile
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]



def _isolated_mypy_cache_dir() -> str:
    """이 프로세스 전용 mypy 캐시 경로 (TASK-2026-08-24-main-007).

    `--no-incremental` 은 캐시 **읽기**만 끄고 디렉터리는 그대로 만든다. 그래서
    병렬 구간의 mypy 호출들이 같은 cwd 의 `.mypy_cache` 를 두고 경합했고, 관찰
    4차의 트레이스백이 `mypy/build.py:create_metastore` 를 지목했다.

    **빈 문자열(`--cache-dir=`)로는 못 끈다** — 캐시를 *끄는* 것이 아니라 cwd 로
    *옮긴다* (실측: `3.13/cache.*.db` 가 작업 디렉터리에 쏟아진다). 처음에
    `.mypy_cache` 부재만 확인하고 "아무것도 안 만든다" 로 읽어 저장소에 캐시
    db 를 커밋했다 — 기대한 산출물의 부재를 산출물 전체의 부재로 읽은 것이다.

    그래서 **전용 경로**를 준다. 프로세스별로 갈라지므로 병렬에서 부딪히지 않고,
    `TMPDIR` 아래라 러너가 정리한다 (전량 runner 는 `--tmp-dir` 로 실디스크를 준다).
    """
    return str(Path(tempfile.gettempdir()) / f"mypy-cache-{os.getpid()}")

def test_mypy_strict_ci_v0_11_11() -> None:
    """v0.11.11 mypy strict CI 통합 verify."""
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
        "개발 `.venv` 와 발행 게이트가 이 extra 로 mypy 를 깐다 — "
        f"하한 지정이면 호스트마다 다른 버전으로 strict 결과가 갈린다.\n블록: {dev_block.strip()}"
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

    # case 8: 게이트 invocation 실제 mypy 실행 verify (REPO_ROOT cwd, full path)
    # 폐지된 CI(mypy-strict.yml, 2026-09-23 main-022)가 쓰던 working pattern (v1.0.2+):
    #   `mypy --no-incremental --config-file workflow-source/pyproject.toml
    #    workflow-source/workflow_kit/` from REPO_ROOT.
    #
    # v1.0.2: `--config-file` 추가. 이전 case 8 은 CI invocation 을 *충실히 재현* 했지만
    # 재현 대상이 깨져 있었다 — 설정 없이 도는 실행을 그대로 복제하고 exit 0 을 확인하니
    # 당연히 green 이었다. **재현이 곧 검증은 아니다**: 무엇을 재현하는지도 함께 봐야 한다.
    # 그 "무엇" 은 check_mypy_config_actually_loaded.py 가 담당한다.
    try:
        result_ci = subprocess.run(
            [sys.executable, "-m", "mypy", "--no-incremental", "--cache-dir", _isolated_mypy_cache_dir(),
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
        # 실패 메시지에 **mypy 자신의 말**을 싣는다 (TASK-2026-08-13-main-004).
        #
        # 이 게이트는 flake 로 4번 터졌는데 (2026-08-11 ~ 08-13) 그때마다 남은 기록은
        # `exit 2 (0 errors in workflow_kit/)` 한 줄뿐이었다. exit 2 는 mypy 의
        # **blocking error** 이고 그 사유는 stderr 로 나오는데, 위 `ci_errors` 필터는
        # stdout 에서 `.py:` + `error:` 형태만 세므로 blocking error 는 어디에도 안
        # 남는다. 즉 **진단에 필요한 유일한 증거를 버리고** 재발 관찰만 반복했다.
        # CI 로그는 만료되고 annotation 에는 검사 이름조차 안 실린다 (2026-08-13 실측:
        # annotation 은 "Process completed with exit code 1" 뿐) — 그러니 실패 메시지가
        # 증거를 들고 있지 않으면 그 사건은 영영 진단 불가가 된다.
        #
        # 유력 가설(미확정): 전량은 병렬이라 다른 check 가 스캔 대상 아래에 파일을
        # 잠깐 만들었다 지우면, mypy 가 나열한 파일을 읽는 순간 사라져 blocking error
        # 가 된다 ("can't read file"). 다음 재발의 stderr 가 이 가설을 판정한다.
        assert result_ci.returncode == 0, (
            f"CI mypy invocation exit {result_ci.returncode} "
            f"({len(ci_errors)} errors in workflow_kit/)\n"
            f"--- stderr ---\n{result_ci.stderr.strip() or '(비어 있음)'}\n"
            f"--- stdout (마지막 20줄) ---\n"
            + "\n".join(result_ci.stdout.splitlines()[-20:])
        )
        print(f"  case 8 (CI mypy invocation exit 0, {len(ci_errors)} errors): PASS")
    except FileNotFoundError:
        print("  case 8 (CI mypy invocation: mypy module not available, SKIP)")
    except subprocess.TimeoutExpired:
        print("  case 8 (CI mypy invocation: timeout, SKIP)")


def main() -> int:
    """1 acceptance test. 1 fail = exit 1."""
    print("=== v0.11.11 mypy strict 통합 acceptance test ===")
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
