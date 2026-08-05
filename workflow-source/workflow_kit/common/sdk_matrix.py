"""CI 가 밟는 mcp SDK 버전의 **정본 registry** (TASK-2026-07-31-main-001).

## 왜 이 파일이 있는가

mcp 를 쓰는 표면 둘은 1.x/2.x 를 모두 해석한다 (§2.41, §2.43). 그런데 **CI 가 그 두
major 를 실제로 밟고 있던 이유는 선언이 아니라 설치 순서였다**:

- `smoke` 는 `requirements.txt`(상한 없음) → `requirements-dev.txt`(`mcp[cli]==1.27.0`)
  → editable install 순으로 깔아서, **뒤에 깔린 핀이 되돌려** 1.x 로 돈다.
- `mypy-strict` / `mcp-inspector` 는 그 파일을 안 깔아서 extra 의 상한 없는
  `mcp[cli]>=1.0` 이 그대로 최신(2.x)을 집는다.

즉 `requirements-dev.txt` 의 한 줄을 지우면 **1.x 커버리지가 조용히 사라지는데 아무
검사도 실패하지 않는다.** 커버리지가 넓은 것과 넓다고 말할 수 있는 것은 다른 일이다.

그래서 이 파일이 세 가지를 한 곳에 적는다:

1. **어떤 버전을 밟기로 했는가** (`PINNED_VERSIONS`) — matrix workflow 가 여기서
   목록을 뽑는다. yml 에는 버전 문자열이 없다.
2. **각 job 의 버전 정책이 무엇인가** (`WORKFLOW_POLICIES`) — 고정인지 부동인지,
   그 버전이 어디서 오는지.
3. **실측을 어떻게 확인하는가** (`record` / `assert_installed`) — 각 job 이 실제로
   집은 버전을 로그에 남기고, 고정이라고 선언한 job 은 그 값을 강제한다.

## floating 을 없애지 않는 이유

상한 없는 설치가 mcp 2.0.0 을 CI 로 끌고 들어와 red 를 냈고, 그래서 이관을 할 수
있었다. 나쁜 것은 부동인 것이 아니라 **부동인 줄 몰랐던 것**이다 — 커밋과 무관한
red 앞에서 원인을 짚는 데 걸린 시간이 그 대가였다. 그래서 부동은 부동이라고 적고,
집힌 버전을 step summary 에 남긴다. "코드는 안 바뀌었는데 결과가 바뀌었다" 에 대한
답이 첫 화면에 있어야 한다.

Cross-ref: TASK-2026-07-31-main-001, releases/Beta-v1.0.0.md §2.45.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DISTRIBUTION = "mcp"
"""버전을 재는 배포판 이름. extra 는 `mcp[cli]` 지만 metadata 이름은 `mcp` 다."""

ROLE_FLOOR = "floor"
ROLE_LATEST_1X = "latest-1x"
ROLE_LATEST_2X = "latest-2x"

POLICY_PINNED = "pinned"
"""그 job 이 도는 버전이 고정돼 있다. 어긋나면 실패시킨다."""

POLICY_FLOATING = "floating"
"""상한 없이 최신을 집는다. 강제하지 않고 **집힌 값을 기록**한다."""

POLICY_MATRIX = "matrix"
"""이 registry 가 선언한 버전 전부를 셀마다 하나씩 밟는다."""


@dataclass(frozen=True)
class PinnedVersion:
    """matrix 가 실제로 설치해 검사할 버전 하나."""

    version: str
    role: str
    reason: str


@dataclass(frozen=True)
class WorkflowPolicy:
    """workflow 하나의 mcp 버전 정책."""

    workflow: str
    """`.github/workflows/<workflow>.yml` 의 이름."""

    policy: str
    """`pinned` / `floating` / `matrix`."""

    source: str
    """그 버전이 **어디서 오는가**. 정책이 지켜지는 물리적 이유를 적는다."""

    reason: str
    """왜 그 정책인가."""

    expected_role: str = ""
    """`pinned` 일 때 어느 role 의 버전이어야 하는가."""


PINNED_VERSIONS: tuple[PinnedVersion, ...] = (
    PinnedVersion(
        version="1.27.0",
        role=ROLE_FLOOR,
        reason=(
            "지원 하한. `maturity_matrix.json` 의 stdio-sdk `sdk_requirement` "
            "(`mcp>=1.27.0`) 와 같은 값이고, `requirements-dev.txt` 가 이 버전을 깔아 "
            "smoke 가 실제로 도는 버전이다."
        ),
    ),
    PinnedVersion(
        version="1.29.0",
        role=ROLE_LATEST_1X,
        reason=(
            "2.x 직전 마지막 1.x. 하한만 밟으면 1.x 안에서 생긴 변화를 놓친다 — "
            "1.x 에 머무는 소비자가 실제로 만나는 버전이다."
        ),
    ),
    PinnedVersion(
        version="2.0.0",
        role=ROLE_LATEST_2X,
        reason=(
            "`mcp.server.fastmcp` 를 없애고 lowlevel decorator 를 "
            "`add_request_handler` 로 바꾼 major (§2.41, §2.43)."
        ),
    ),
)


WORKFLOW_POLICIES: tuple[WorkflowPolicy, ...] = (
    WorkflowPolicy(
        workflow="mcp-sdk-matrix",
        policy=POLICY_MATRIX,
        source="이 registry 의 `PINNED_VERSIONS` (`--github-matrix` 로 주입)",
        reason=(
            "두 major 커버리지의 **선언된** 자리. 다른 job 의 커버리지는 부수 효과라 "
            "설치 순서가 바뀌면 사라지지만, 여기서는 사라지면 job 이 없어진다."
        ),
    ),
    WorkflowPolicy(
        workflow="smoke",
        policy=POLICY_PINNED,
        expected_role=ROLE_FLOOR,
        source="`requirements-dev.txt` 의 `mcp[cli]==1.27.0` (editable install 뒤에 깔려 되돌린다)",
        reason=(
            "전량 smoke 는 **하한**에서 돈다. 누적 baseline 이 이 버전에서 측정돼 왔고, "
            "하한이 깨지는 것은 상한이 깨지는 것과 다른 사건이다."
        ),
    ),
    WorkflowPolicy(
        workflow="mypy-strict",
        policy=POLICY_FLOATING,
        source="`workflow-source/pyproject.toml` 의 `mcp-sdk` extra (`mcp[cli]>=1.0`, 상한 없음)",
        reason=(
            "새 major 가 나오면 **여기서 먼저 걸린다**. 실제로 2.0.0 을 이 job 이 물어 왔다 "
            "(§2.41). 부동을 없애면 그 조기 경보를 잃는다 — 대신 집힌 버전을 기록한다."
        ),
    ),
    WorkflowPolicy(
        workflow="mcp-inspector",
        policy=POLICY_FLOATING,
        source="`workflow-source/pyproject.toml` 의 `mcp-sdk` extra (`mcp[cli]>=1.0`, 상한 없음)",
        reason=(
            "프로토콜 왕복을 최신 SDK 로 밟는 자리. Node 쪽 인스펙터는 별도로 "
            "`@2` 로 고정돼 있다 (§2.42) — 도구도 의존성이다."
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


def policy_for(workflow: str) -> WorkflowPolicy | None:
    for entry in WORKFLOW_POLICIES:
        if entry.workflow == workflow:
            return entry
    return None


def github_matrix_json() -> str:
    """GitHub Actions `fromJson` 이 받는 형태 (문자열 배열)."""
    return json.dumps(list(pinned_versions()))


def installed_version() -> str | None:
    try:
        return importlib.metadata.version(DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError:
        return None


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


def render_record(workflow: str, actual: str | None) -> tuple[str, str | None]:
    """`(step summary 에 남길 줄, 실패 사유 또는 None)`."""
    entry = policy_for(workflow)
    if entry is None:
        return (
            f"- mcp SDK: `{actual or '미설치'}` (정책 미선언 workflow: {workflow})",
            (
                f"'{workflow}' 가 sdk_matrix 의 WORKFLOW_POLICIES 에 없다 "
                "— mcp 를 깔면서 정책을 선언하지 않은 job 이다"
            ),
        )

    shown = actual or "미설치"
    line = f"- mcp SDK 실측: `{shown}` — {entry.workflow} 정책 `{entry.policy}` ({entry.source})"

    if entry.policy != POLICY_PINNED:
        return line, None

    expected = version_for_role(entry.expected_role)
    if expected is None:
        return line, (
            f"{entry.workflow} 는 role '{entry.expected_role}' 을 고정한다고 선언했는데 "
            "PINNED_VERSIONS 에 그 role 이 없다"
        )
    return line, _assert_installed(expected, actual)


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
)
"""matrix 셀이 **아무것도 재지 않은 채 green** 이 되는 것을 막는 정본.

이 두 검사는 SDK 가 없으면 `Skipping…` 을 찍고 **exit 0** 으로 끝난다. 그래서
설치가 조용히 실패해도 셀 전체가 통과한다. `--assert-installed` 는 "깔렸는가" 까지만
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


def observe_exercised() -> dict[str, tuple[int, str]]:
    """선언된 검사를 **직접 돌려서** 증거를 관측한다.

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
            [sys.executable, str(source_root / declared.path)],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(source_root.parent),
            timeout=120,
        )
        observations[declared.path] = (
            completed.returncode,
            completed.stdout + completed.stderr,
        )
    return observations


#: 로컬 매트릭스가 만드는 venv 의 위치 (저장소 루트 기준). `.venv` 접두라
#: `.gitignore` 와 `check_docs` 의 기존 규칙이 그대로 적용된다.
LOCAL_MATRIX_VENV_DIR = ".venv-sdk-matrix"

#: 로컬 매트릭스가 도는 검사 filter. CI 의 `mcp-sdk-matrix` 셀과 같은 값이어야
#: "로컬에서 통과했는데 CI 에서 깨졌다" 가 안 생긴다.
LOCAL_MATRIX_FILTER = "mcp,optional_dep"


def run_local_matrix(
    repo_root: Path,
    only_version: str | None = None,
    keep_venvs: bool = True,
) -> int:
    """`PINNED_VERSIONS` 전부를 **로컬에서** 밟는다.

    ## 왜 필요한가

    매트릭스가 CI 에만 있어서 **"로컬 green → CI red" 가 구조적으로 발생했다.**
    개발 venv 는 `requirements-dev.txt` 가 깐 하한(1.27.0) 하나뿐이라, 2.0.0 에서만
    갈라지는 코드를 로컬에서 밟을 방법이 없다. 실제로 2026-08-05 에
    `check_mcp_apply_mode_criterion` 이 `result.isError`(1.x 이름)를 써서 로컬은
    통과하고 matrix 2.0.0 셀만 red 였다 — 저장소가 **이미 알고 있던 함정**인데
    로컬에서 재현할 수단이 없었다.

    버전 목록은 이 파일의 `PINNED_VERSIONS` 에서 읽는다. CI yml 과 같은 정본이므로
    사본이 갈라질 자리가 없다.

    ## 한계 (과장하지 않는다)

    - CI 셀과 **완전히 같은 환경은 아니다** (러너 OS / 파이썬 패치 버전이 다르다).
      이것은 CI 를 대신하는 것이 아니라 push 전에 *같은 부류의* 결함을 잡는 도구다.
    - `extra` 는 `dev,release` 만 깐다. `mcp` 는 버전을 고정해 따로 깐다 —
      `mcp-sdk` extra 를 쓰면 상한이 없어 매번 최신을 집어 매트릭스가 무의미해진다.
    """
    versions = [pinned.version for pinned in PINNED_VERSIONS]
    if only_version is not None:
        if only_version not in versions:
            print(f"::error::{only_version} 은 PINNED_VERSIONS 에 없다 (선언: {versions})")
            return 1
        versions = [only_version]

    venv_root = repo_root / LOCAL_MATRIX_VENV_DIR
    tmp_root = venv_root / "_tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    for version in versions:
        venv_path = venv_root / version
        python = venv_path / "bin" / "python"
        print(f"\n=== mcp {version} ===")
        if not python.is_file():
            print(f"  venv 생성: {venv_path}")
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)  # noqa: S603
        installed = subprocess.run(  # noqa: S603
            [str(python), "-c",
             "import importlib.metadata as m;\ntry: print(m.version('mcp'))\nexcept Exception: print('')"],
            capture_output=True, text=True,
        ).stdout.strip()
        if installed != version:
            print(f"  설치: -e workflow-source[dev,release] + mcp=={version} (현재 {installed or '없음'})")
            subprocess.run(  # noqa: S603
                [str(python), "-m", "pip", "-q", "install",
                 "-e", f"{repo_root / 'workflow-source'}[dev,release]", f"mcp=={version}"],
                check=True,
            )
        # 설치가 조용히 딴 버전을 집었을 수 있다 — 선언이 아니라 실측으로 확인한다.
        actual = subprocess.run(  # noqa: S603
            [str(python), "-c", "import importlib.metadata as m; print(m.version('mcp'))"],
            capture_output=True, text=True,
        ).stdout.strip()
        if actual != version:
            print(f"  ::error::요청 {version} 인데 설치된 것은 {actual} 다")
            failures.append(f"mcp {version}: 설치 버전 불일치 ({actual})")
            continue

        completed = subprocess.run(  # noqa: S603
            [str(python), str(repo_root / "workflow-source" / "tests" / "run_all_checks.py"),
             f"--filter={LOCAL_MATRIX_FILTER}", "--timeout=120", f"--tmp-dir={tmp_root}"],
            cwd=str(repo_root),
        )
        if completed.returncode != 0:
            failures.append(f"mcp {version}: 검사 실패 (exit {completed.returncode})")

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
    lines.append("")
    lines.append("| workflow | 정책 | 버전 출처 |")
    lines.append("|---|---|---|")
    for entry in WORKFLOW_POLICIES:
        lines.append(f"| `{entry.workflow}` | {entry.policy} | {entry.source} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--github-matrix",
        action="store_true",
        help="선언한 버전 목록을 JSON 배열로 (Actions 의 fromJson 입력)",
    )
    group.add_argument(
        "--assert-installed",
        metavar="VERSION",
        help="설치된 mcp 가 이 버전인지 실측 확인 (matrix 셀에서 사용)",
    )
    group.add_argument(
        "--record",
        metavar="WORKFLOW",
        help="그 job 이 집은 버전을 기록한다. 정책이 pinned 면 강제까지 한다",
    )
    group.add_argument(
        "--assert-exercised",
        action="store_true",
        help="설치된 SDK 로 실제 왕복을 밟았는지 직접 돌려서 확인",
    )
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
    args = parser.parse_args(argv)

    if args.run_local:
        return run_local_matrix(
            Path(__file__).resolve().parents[3],
            only_version=args.only,
        )

    if args.github_matrix:
        print(github_matrix_json())
        return 0

    if args.summary:
        print(render_summary())
        return 0

    if args.assert_exercised:
        problems = judge_exercised(observe_exercised())
        if problems:
            print(
                "::error::SDK 를 깔고 도는 셀인데 그것으로 쟀다는 증거가 없다 "
                f"({len(problems)}건) — 설치가 조용히 실패했는가?"
            )
            for entry in problems:
                print(f"  - {entry}")
            return 1
        for declared in SDK_EXERCISING_CHECKS:
            print(f"  {declared.path} — '{declared.evidence}' 확인")
        print(f"{len(SDK_EXERCISING_CHECKS)}건이 설치된 SDK 로 실제 왕복을 밟았다")
        return 0

    if args.assert_installed:
        actual = installed_version()
        problem = _assert_installed(args.assert_installed, actual)
        if problem is not None:
            print(f"::error::{problem}")
            return 1
        print(f"mcp {actual} — 요청한 버전과 일치한다")
        return 0

    line, problem = render_record(args.record, installed_version())
    print(line)
    if problem is not None:
        print(f"::error::{problem}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
