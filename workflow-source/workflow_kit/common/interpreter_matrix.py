"""검사를 **어느 Python 해석기로 도는가** 의 정본 registry (TASK-2026-09-21-main-006).

## 왜 이 파일이 있는가

2026-09-21, `check_python_floor_syntax` 의 case 3 이 **로컬 3.13 에서 green, CI 3.11
에서 red** 였다 (9915e4ad). 판정이 실행 해석기에 달려 있었는데, 로컬에는 그 축을
밟을 수단이 없었다.

이 저장소는 같은 모양을 이미 두 번 겪었다:

    mcp SDK 버전   → `sdk_matrix.py`     (로컬 green / matrix 2.0.0 셀만 red)
    브랜치 컨텍스트 → `branch_matrix.py`  (로컬 green / slash 셀만 15연속 red)

세 번째다. 대응도 같다 — **정본을 한 곳에 두고 게이트가 그것을 읽는다.**

## 이 축에서 특히 고약했던 것: 한쪽 커버리지가 *우연* 이었다

착수 시점의 실측:

| 해석기 | 누가 검사를 그것으로 도는가 |
|---|---|
| 3.11 | CI (당시 `smoke.yml` / `mcp-sdk-matrix.yml` 의 `setup-python`) |
| 3.13 | 개발자 로컬 `.venv` — **선언이 아니라 그 호스트에 깔린 것** |

3.13 축은 아무 데도 선언돼 있지 않았다. `.venv` 를 3.11 로 다시 만드는 순간 그
커버리지는 **조용히 사라지고 아무 검사도 실패하지 않는다**. 부수 효과로 얻은
커버리지를 선언으로 고정하는 것 — 2026-07-31 에 CI 에서 같은 일을 했다.

그래서 이 registry 는 두 해석기를 **둘 다 선언**한다. 로컬이 무엇으로 돌든
커버리지가 변하지 않는다.

## CI 폐지 이후 (2026-09-23, TASK-2026-09-23-main-022)

GitHub Actions 검사 workflow 가 폐지돼 smoke.yml 의 prepare job 주입
(`--github-matrix`)과 셀의 긍정 증거(`--assert-running`)는 대상을 잃어 제거했다.
선언된 해석기 전부를 밟는 곳은 이제 push 전 로컬 실행 하나다:

    PYTHONPATH=workflow-source .venv/bin/python3 -m workflow_kit.common.interpreter_matrix --run-local

그 경로는 venv 마다 실제 해석기 버전을 실측해 선언과 대조한다 (`_ensure_venv`).

Stdlib only.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROLE_CI_RUNNER = "ci-runner"
"""CI 가 검사를 돌던 해석기 (CI 폐지 후에도 role 이름은 유지 — 선언의 연속성)."""

ROLE_DEV_LOCAL = "dev-local"
"""저장소가 로컬 개발자를 유도하는 해석기 (`.python-version`)."""


@dataclass(frozen=True)
class Interpreter:
    """게이트가 검사를 돌려 보는 Python 해석기 하나."""

    version: str
    """`X.Y`. `uv python` / `find_interpreter` 의 인자."""

    role: str
    """`ci-runner` / `dev-local`."""

    source: str
    """이 값이 **어디서 오는가**. 선언이 저장소의 어느 사실과 묶여 있는지 적는다."""

    reason: str
    """왜 이 해석기를 밟는가."""


GATE_INTERPRETERS: tuple[Interpreter, ...] = (
    Interpreter(
        version="3.11",
        role=ROLE_CI_RUNNER,
        source="이 registry 선언 (CI smoke.yml 의 setup-python 이 출처였다 — 2026-09-23 폐지, main-022)",
        reason=(
            "CI 가 검사를 돌던 해석기. 여기서만 red 인 판정이 실제로 있었다 — "
            "`check_python_floor_syntax` case 3 (2026-09-21, 9915e4ad)."
        ),
    ),
    Interpreter(
        version="3.13",
        role=ROLE_DEV_LOCAL,
        source="저장소 루트 `.python-version` (pyenv/uv 가 로컬 개발자를 유도하는 값)",
        reason=(
            "개발자가 평소 검사를 도는 해석기. 착수 시점에는 **아무 데도 선언돼 있지 "
            "않았고** 그 호스트에 깔린 것에 기대고 있었다 — `.venv` 를 다시 만들면 "
            "커버리지가 조용히 사라진다."
        ),
    ),
)


def versions() -> tuple[str, ...]:
    return tuple(i.version for i in GATE_INTERPRETERS)


def interpreter_for(version: str) -> Interpreter | None:
    for entry in GATE_INTERPRETERS:
        if entry.version == version:
            return entry
    return None


def role_version(role: str) -> str | None:
    for entry in GATE_INTERPRETERS:
        if entry.role == role:
            return entry.version
    return None


def declared_local_version(repo_root: Path) -> str | None:
    """`.python-version` 이 선언한 로컬 개발 해석기. registry 의 출처 대조용."""
    pin = repo_root / ".python-version"
    if not pin.is_file():
        return None
    match = re.match(r"\s*(\d+\.\d+)", pin.read_text(encoding="utf-8"))
    return match.group(1) if match else None


#: 로컬 매트릭스가 만드는 venv 의 위치 (저장소 루트 기준). `.venv` 접두라
#: `.gitignore` 와 `check_docs` 의 기존 규칙이 그대로 적용된다.
LOCAL_MATRIX_VENV_DIR = ".venv-interpreter-matrix"


def running_version() -> str:
    return f"{sys.version_info[0]}.{sys.version_info[1]}"


def _ensure_venv(repo_root: Path, version: str) -> Path | None:
    """`version` 해석기로 개발 `.venv` 와 같은 의존성을 깐 venv 를 만든다 (있으면 재사용).

    해석기를 못 구하면 None — **통과가 아니라 미측정**이다 (`python_floor` 와 같은
    규율). 없는 것을 밟았다고 세지 않는다.
    """
    from workflow_kit.common.python_floor import find_interpreter

    major, minor = (int(part) for part in version.split("."))
    base = find_interpreter((major, minor))
    if base is None:
        return None

    venv_path = repo_root / LOCAL_MATRIX_VENV_DIR / version
    python = venv_path / "bin" / "python"
    if not python.is_file():
        print(f"  venv 생성: {venv_path} (base={base})")
        subprocess.run([base, "-m", "venv", str(venv_path)], check=True)  # noqa: S603

    actual = subprocess.run(  # noqa: S603
        [str(python), "-c", "import sys;print('%d.%d'%sys.version_info[:2])"],
        capture_output=True, text=True,
    ).stdout.strip()
    if actual != version:
        print(f"  ::error::{version} venv 인데 실제 해석기는 {actual} 다")
        return None

    have_kit = subprocess.run(  # noqa: S603
        [str(python), "-c", "import workflow_kit"], capture_output=True,
    ).returncode == 0
    if not have_kit:
        # 개발 `.venv` 와 **같은 순서**로 깐다 — 뒤에 깔린 것이 이긴다는 사실이
        # `sdk_matrix` 가 존재하는 이유 자체다 (mcp 핀이 editable 뒤에 온다).
        print(f"  설치: requirements → requirements-dev → -e workflow-source[dev,release,mcp-sdk]")
        for spec in (["-r", str(repo_root / "requirements.txt")],
                     ["-r", str(repo_root / "requirements-dev.txt")],
                     ["-e", f"{repo_root / 'workflow-source'}[dev,release,mcp-sdk]"]):
            subprocess.run([str(python), "-m", "pip", "-q", "install", *spec], check=True)  # noqa: S603
    return python


def run_local_matrix(
    repo_root: Path,
    only_version: str | None = None,
    check_filter: str | None = None,
    tmp_dir: str | None = None,
) -> int:
    """선언된 해석기 전부로 **로컬에서** 전량 검사를 돌린다.

    ## 한계 (과장하지 않는다)

    - 패치 버전은 호스트가 구한 것을 따른다 (`X.Y` 까지만 선언과 대조한다).
    - 해석기를 못 구하면 그 축은 **미측정**으로 보고한다. 못 잰 것을 통과로 세지
      않는다.
    """
    targets = list(versions())
    if only_version is not None:
        if only_version not in targets:
            print(f"::error::{only_version} 은 GATE_INTERPRETERS 에 없다 (선언: {targets})")
            return 1
        targets = [only_version]

    runner = repo_root / "workflow-source" / "tests" / "run_all_checks.py"
    tmp_root = Path(tmp_dir) if tmp_dir else repo_root / LOCAL_MATRIX_VENV_DIR / "_tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)

    verdicts: list[tuple[str, str, str]] = []   # (version, mark, detail)
    for version in targets:
        # 자식이 stdout 을 물려받으므로 **먼저 비운다**. 안 그러면 셀 헤더가
        # runner 출력 뒤에 찍혀 어느 해석기의 결과인지 읽을 수 없다 (실측).
        print(f"\n=== Python {version} ===", flush=True)
        if version == running_version():
            # 이미 이 해석기로 돌고 있다 — venv 를 또 만들 이유가 없다.
            python: Path | None = Path(sys.executable)
            print(f"  현재 해석기 재사용: {python}", flush=True)
        else:
            python = _ensure_venv(repo_root, version)
        if python is None:
            verdicts.append((version, "UNMEASURED",
                             f"python{version} 해석기를 구하지 못했다 "
                             f"(PATH 에도 없고 uv 로도 못 얻었다)"))
            continue

        argv = [str(python), str(runner), "--timeout=120", f"--tmp-dir={tmp_root}"]
        if check_filter:
            argv.append(f"--filter={check_filter}")
        sys.stdout.flush()
        completed = subprocess.run(argv, cwd=str(repo_root))  # noqa: S603
        verdicts.append((version, "PASS" if completed.returncode == 0 else "FAIL",
                         f"exit {completed.returncode}"))

    print("\n=== 로컬 해석기 매트릭스 결과 ===")
    for version, mark, detail in verdicts:
        entry = interpreter_for(version)
        role = f" [{entry.role}]" if entry else ""
        print(f"  [{mark}] Python {version}{role} — {detail}")
    if any(mark == "FAIL" for _, mark, _ in verdicts):
        return 1
    if any(mark == "UNMEASURED" for _, mark, _ in verdicts):
        print("  미측정이 있다 — 통과가 아니다. `uv python install <버전>` 후 다시 돌릴 것")
        return 2
    print(f"  선언된 {len(verdicts)}개 해석기 전부 통과"
          + (f" (filter={check_filter})" if check_filter else " (전량)"))
    return 0


def render_summary() -> str:
    lines = ["| 버전 | role | 출처 | 이유 |", "|---|---|---|---|"]
    for entry in GATE_INTERPRETERS:
        lines.append(f"| `{entry.version}` | {entry.role} | {entry.source} | {entry.reason} |")
    lines.append("")
    lines.append(
        "로컬 재현: "
        "`PYTHONPATH=workflow-source .venv/bin/python3 -m workflow_kit.common.interpreter_matrix --run-local`"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    from workflow_kit.common.paths import resolve_workspace_root

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--versions", action="store_true",
                       help="버전을 한 줄에 하나씩 출력")
    group.add_argument("--summary", action="store_true", help="registry 를 표로 출력")
    group.add_argument("--run-local", action="store_true",
                       help="선언된 해석기 전부로 전량 검사를 돌린다 (push 전 재현)")
    parser.add_argument("--only", metavar="VERSION", default=None,
                        help="--run-local 에서 한 버전만 (기본: 선언된 전부)")
    parser.add_argument("--filter", metavar="NAME", default=None, dest="check_filter",
                        help="--run-local 이 runner 에 넘길 --filter (기본: 전량)")
    parser.add_argument("--tmp-dir", metavar="DIR", default=None,
                        help="--run-local 이 runner 에 넘길 --tmp-dir (실디스크 경로 권장)")
    args = parser.parse_args(argv)

    if args.versions:
        for version in versions():
            print(version)
    elif args.summary:
        print(render_summary())
    else:
        repo_root, _why = resolve_workspace_root()
        return run_local_matrix(repo_root, args.only, args.check_filter, args.tmp_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
