"""게이트가 밟는 mcp SDK 버전의 **정본 registry** (TASK-2026-07-31-main-001).

## 왜 이 파일이 있는가

mcp 를 쓰는 표면 둘은 v2 API 를 사용한다. 공식 최신 안정판 v2.3.0 을
개발·배포 최소 지원판으로 삼고, 로컬 매트릭스가 그 버전을 별도 venv 에서 직접 밟는다.

그래서 이 파일이 두 가지를 한 곳에 적는다:

1. **어떤 버전을 밟기로 했는가** (`PINNED_VERSIONS`).
2. **실측을 어떻게 확인하는가** — "깔렸는가"(`_assert_installed`)와 "그것으로
   실제로 쟀는가"(`judge_exercised`). 둘은 서로를 대신하지 못한다.

## CI 폐지 이후 (2026-09-23, TASK-2026-09-23-main-022)

GitHub Actions 검사 workflow 가 폐지돼 CI 전용 표면 — job 별 버전 정책
(`WORKFLOW_POLICIES`)과 `--github-matrix` / `--record` / `--assert-installed` /
`--assert-exercised` — 은 대상을 잃어 제거했다. 선언된 버전 전부를 밟는 곳은 이제
push 전 로컬 실행 하나이고, 두 층의 판정은 그 경로(`run_local_matrix`)가 셀마다
직접 부른다:

    PYTHONPATH=workflow-source .venv/bin/python3 -m workflow_kit.common.sdk_matrix --run-local

Cross-ref: TASK-2026-07-31-main-001, releases/Beta-v1.0.0.md §2.45.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from workflow_kit.common.paths import matrix_tmp_root, venv_executable

ROLE_FLOOR = "floor"


@dataclass(frozen=True)
class PinnedVersion:
    """matrix 가 실제로 설치해 검사할 버전 하나."""

    version: str
    role: str
    reason: str


PINNED_VERSIONS: tuple[PinnedVersion, ...] = (
    PinnedVersion(
        version="2.3.0",
        role=ROLE_FLOOR,
        reason=(
            "공식 MCP Python SDK 최신 안정판(2026-10-02 확인). "
            "최소 지원판으로 지정하고 허브 MCP 경로(`check_hub_core` case 9)를 실측한다."
        ),
    ),
)


def pinned_versions() -> tuple[str, ...]:
    return tuple(pinned.version for pinned in PINNED_VERSIONS)


def version_for_role(role: str) -> str | None:
    for pinned in PINNED_VERSIONS:
        if pinned.role == role:
            return pinned.version
    return None


def floor_version() -> str:
    version = version_for_role(ROLE_FLOOR)
    if version is None:  # pragma: no cover - 검사가 먼저 실패한다
        raise ValueError("PINNED_VERSIONS 에 floor role 이 없다")
    return version


def _assert_installed(expected: str, actual: str | None) -> str | None:
    """맞으면 `None`, 어긋나면 사람이 읽을 실패 사유."""
    if actual is None:
        return (
            f"mcp 를 {expected} 로 깔기로 했는데 **설치 자체가 안 됐다** "
            "— 설치 스텝이 조용히 실패했는가?"
        )
    if actual != expected:
        return (
            f"요청한 mcp 는 {expected} 인데 실제로 깔린 것은 {actual} 이다 "
            "— 다른 requirement 가 뒤에서 되돌렸다면 설치 순서를 보라."
        )
    return None


@dataclass(frozen=True)
class SdkExercisingCheck:
    """SDK 가 없으면 **통째로 건너뛰는** 검사와, 실제로 밟았을 때만 나오는 증거."""

    path: str
    """`workflow-source/` 기준 상대 경로."""

    evidence: str
    """그 검사가 SDK 로 실제 왕복을 끝냈을 때만 출력에 나오는 문자열."""

    why: str


SDK_EXERCISING_CHECKS: tuple[SdkExercisingCheck, ...] = (
    SdkExercisingCheck(
        path="tests/check_read_only_mcp_sdk_stdio.py",
        evidence="Read-only MCP SDK stdio smoke check passed.",
        why="실제 client 세션으로 initialize → tools/list → tools/call 왕복을 밟는다.",
    ),
    SdkExercisingCheck(
        path="tests/check_mcp_v1_server.py",
        evidence="MCP v1.0 smoke test passed.",
        why="설치된 SDK 로 v1 서버를 실제로 만들고 tool 을 등록한다.",
    ),
    SdkExercisingCheck(
        path="tests/check_hub_core.py",
        evidence="case 9 (MCP 인증 경계 · HTTP 와 같은 결과)",
        why="실제 허브 프로세스를 그 SDK 로 띄우고 MCP 클라이언트로 도구 목록 · 호출을 밟는다 (main-022 — 허브가 2.x 로).",
    ),
)
"""matrix 셀이 **아무것도 재지 않은 채 green** 이 되는 것을 막는 정본.

이 두 검사는 SDK 가 없으면 `Skipping…` 을 찍고 **exit 0** 으로 끝난다. 그래서
설치가 조용히 실패해도 셀 전체가 통과한다. `_assert_installed` 는 "깔렸는가" 까지만
보고, 여기서는 "그것으로 실제로 쟀는가" 를 본다 — 둘은 서로를 대신하지 못한다.

판정은 **긍정 증거**로 한다. 출력에서 "skip 처럼 보이는 말" 을 찾는 방식은 이미
위양성을 냈다 — `check_mcp_server_sdk_compat.py` 는 "둘 다 없을 때 fail-fast 하는가" 를
*의도적으로* 확인하느라 SDK 가 깔린 환경에서도 "SDK not installed" 를 출력한다.
없는 것을 찾는 대신 있어야 할 것을 요구한다.
"""


def judge_exercised(observations: dict[str, tuple[int, str]]) -> list[str]:
    """`{경로: (exit_code, 출력)}` 을 받아 증거가 없는 검사를 돌려준다.

    판정과 측정을 나눈 것은 검사(`check_mcp_sdk_matrix.py`)가 이 판정을 **되주입으로**
    확인할 수 있게 하기 위해서다.
    """
    problems: list[str] = []
    for declared in SDK_EXERCISING_CHECKS:
        observation = observations.get(declared.path)
        if observation is None:
            problems.append(f"{declared.path} 를 실행하지 못했다 ({declared.why})")
            continue
        exit_code, output = observation
        if exit_code != 0:
            problems.append(f"{declared.path} 가 exit {exit_code} 로 끝났다")
            continue
        if declared.evidence not in output:
            problems.append(
                f"{declared.path} 가 SDK 를 밟은 증거가 없다 "
                f"(기대: '{declared.evidence}' / 마지막 출력: '{output.strip()[-100:]}')"
            )
    return problems


def observe_exercised(python: str | None = None) -> dict[str, tuple[int, str]]:
    """선언된 검사를 **직접 돌려서** 증거를 관측한다.

    `python` 은 검사를 띄울 해석기 (기본: 현재 프로세스). `run_local_matrix` 는
    셀의 venv 해석기를 넘긴다 — 그 SDK 로 쟀는지를 봐야 하기 때문이다.

    `run_all_checks --json` 의 `last_line` 을 읽는 방식은 실패했다 — mcp 1.x 는 서버
    로그(`Processing request of type ListToolsRequest`)를 stderr 로 뒤에 붙여서, 검사가
    성공했는데도 마지막 줄이 성공 메시지가 아니다. 남이 요약한 필드를 믿는 대신 이
    판정이 자기 측정을 직접 한다.
    """
    source_root = Path(__file__).resolve().parents[2]
    env = dict(os.environ, PYTHONPATH=str(source_root))
    observations: dict[str, tuple[int, str]] = {}
    for declared in SDK_EXERCISING_CHECKS:
        completed = subprocess.run(  # noqa: S603
            [python or sys.executable, str(source_root / declared.path)],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(source_root.parent),
            timeout=120, encoding="utf-8", errors="replace",
        )
        observations[declared.path] = (
            completed.returncode,
            completed.stdout + completed.stderr,
        )
    return observations


#: 로컬 매트릭스가 만드는 venv 의 위치 (저장소 루트 기준). `.venv` 접두라
#: `.gitignore` 와 `check_docs` 의 기존 규칙이 그대로 적용된다.
LOCAL_MATRIX_VENV_DIR = ".venv-sdk-matrix"

#: 로컬 매트릭스가 도는 검사 filter (폐지된 CI `mcp-sdk-matrix` 셀과 같은 값).
LOCAL_MATRIX_FILTER = "mcp,optional_dep,hub_core,hub_orch"


def run_local_matrix(
    repo_root: Path,
    only_version: str | None = None,
    keep_venvs: bool = True,
    tmp_dir: str | None = None,
) -> int:
    """`PINNED_VERSIONS` 전부를 **로컬에서** 밟는다.

    ## 왜 필요한가

    매트릭스가 CI 에만 있던 시절 **"로컬 green → CI red" 가 구조적으로 발생했다.**
    개발 venv pin이자 최소 지원판인 2.3.0에서 실제 API를 밟는다.
    그보다 이전 SDK는 지원 대상에서 제외한다.

    버전 목록은 이 파일의 `PINNED_VERSIONS` 에서 읽는다.

    셀마다 두 층을 **둘 다** 본다 — "깔렸는가"(`_assert_installed`)와 "그것으로
    실제로 쟀는가"(`judge_exercised`). 후자가 없으면 SDK 검사가 `Skipping…` 후
    exit 0 으로 끝나도 셀이 green 이 된다.

    ## 한계 (과장하지 않는다)

    - `extra` 는 `dev,release` 만 깐다. `mcp` 는 버전을 고정해 따로 깐다 —
      지원 하한과 검증판이 같아야 한다.
    """
    versions = [pinned.version for pinned in PINNED_VERSIONS]
    if only_version is not None:
        if only_version not in versions:
            print(f"::error::{only_version} 은 PINNED_VERSIONS 에 없다 (선언: {versions})")
            return 1
        versions = [only_version]

    venv_root = repo_root / LOCAL_MATRIX_VENV_DIR
    try:
        tmp_root = matrix_tmp_root(repo_root, "sdk-matrix", tmp_dir)
    except ValueError as exc:
        print(f"::error::{exc}")
        return 2
    tmp_root.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    for version in versions:
        venv_path = venv_root / version
        python = venv_executable(venv_path, "python")
        print(f"\n=== mcp {version} ===")
        if not python.is_file():
            print(f"  venv 생성: {venv_path}")
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)  # noqa: S603
        installed = subprocess.run(  # noqa: S603
            [str(python), "-c",
             "import importlib.metadata as m;\ntry: print(m.version('mcp'))\nexcept Exception: print('')"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout.strip()
        if installed != version:
            print(f"  설치: -e workflow-source[dev,release,hub] + mcp=={version} (현재 {installed or '없음'})")
            subprocess.run(  # noqa: S603
                [str(python), "-m", "pip", "-q", "install",
                 "-e", f"{repo_root / 'workflow-source'}[dev,release,hub]", f"mcp=={version}"],
                check=True,
            )
        # 설치가 조용히 딴 버전을 집었을 수 있다 — 선언이 아니라 실측으로 확인한다.
        actual = subprocess.run(  # noqa: S603
            [str(python), "-c",
             "import importlib.metadata as m;\ntry: print(m.version('mcp'))\nexcept Exception: print('')"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout.strip()
        problem = _assert_installed(version, actual or None)
        if problem is not None:
            print(f"  ::error::{problem}")
            failures.append(f"mcp {version}: {problem}")
            continue

        completed = subprocess.run(  # noqa: S603
            [str(python), str(repo_root / "workflow-source" / "tests" / "run_all_checks.py"),
             f"--filter={LOCAL_MATRIX_FILTER}", "--timeout=120", f"--tmp-dir={tmp_root}"],
            cwd=str(repo_root),
        )
        if completed.returncode != 0:
            failures.append(f"mcp {version}: 검사 실패 (exit {completed.returncode})")

        # "깔렸다" 와 "그것으로 쟀다" 는 다르다 — SDK 검사가 skip 후 exit 0 이면
        # 위 runner 는 green 이다. 긍정 증거를 셀의 해석기로 직접 관측한다.
        for entry in judge_exercised(observe_exercised(str(python))):
            print(f"  ::error::{entry}")
            failures.append(f"mcp {version}: SDK 미사용 — {entry}")

    print("\n=== 로컬 SDK 매트릭스 결과 ===")
    for version in versions:
        mark = "FAIL" if any(f.startswith(f"mcp {version}:") for f in failures) else "PASS"
        print(f"  [{mark}] mcp {version}")
    if failures:
        for entry in failures:
            print(f"  - {entry}")
        return 1
    print(f"  {len(versions)}개 버전 전부 통과 (filter={LOCAL_MATRIX_FILTER})")
    return 0


def render_summary() -> str:
    """registry 전체를 사람이 읽는 표로. 로그·문서 양쪽에서 쓴다."""
    lines = ["| 버전 | role | 근거 |", "|---|---|---|"]
    for pinned in PINNED_VERSIONS:
        lines.append(f"| `{pinned.version}` | {pinned.role} | {pinned.reason} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--summary", action="store_true", help="registry 를 표로 출력")
    group.add_argument(
        "--run-local",
        action="store_true",
        help="PINNED_VERSIONS 전부를 로컬 venv 에서 밟는다 (push 전 매트릭스 재현)",
    )
    parser.add_argument(
        "--only",
        metavar="VERSION",
        help="--run-local 에서 한 버전만 (기본: 선언된 전부)",
    )
    parser.add_argument(
        "--tmp-dir",
        metavar="DIR",
        default=None,
        help="--run-local 이 runner 에 넘길 --tmp-dir — 저장소 밖 실디스크 (기본 ~/.cache/workflow-kit/sdk-matrix-tmp)",
    )
    args = parser.parse_args(argv)

    if args.run_local:
        return run_local_matrix(
            Path(__file__).resolve().parents[3],
            only_version=args.only,
            tmp_dir=args.tmp_dir,
        )

    print(render_summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
