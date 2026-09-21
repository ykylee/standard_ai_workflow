"""선언된 최소 Python 버전으로 소스를 **실물 해석기**에 물려 본다.

TASK-2026-09-21-main-005.

## 왜 이 축이 필요한가

로컬 개발 인터프리터가 CI 보다 새로우면, 새 문법을 쓴 코드가 **로컬에서만 통과**한다.
이 저장소는 같은 모양을 이미 두 번 겪고 로컬 재현 수단을 만들어 뒀다 —
`sdk_matrix`(mcp 1.x/2.x)와 `branch_matrix`(native/slash). 이것이 세 번째 축이다.

## 왜 `ast.parse(feature_version=...)` 로는 안 되는가 (실측이 전제를 뒤집었다)

처음 설계는 `ast.parse(..., feature_version=floor)` 였다. 그 수단은 이 축을 만들게 한
**바로 그 결함을 못 잡는다**. 2026-09-21 실측:

| 구문 | 도입 | `feature_version=(3,10)` |
|---|---|---|
| 중첩 f-string (PEP 701) | 3.12 | **통과** ← 못 잡는다 |
| `type X = int` | 3.12 | 거부 |
| `def f[T]()` | 3.12 | 거부 |
| `except*` | 3.11 | 거부 |

`feature_version` 은 파서가 *버전 게이트를 명시적으로 건* 구문만 거부한다. PEP 701 은
f-string 을 토크나이저 층에서 재작성한 변경이라 그 게이트에 걸리지 않는다.

그래서 **실물 해석기**로 잰다. 실측: 실물 3.10.20 은 `f"{"a" if x else "b"}"` 를
`SyntaxError: f-string: expecting '}'` 로 거부하고, 3.13 은 정상 문법으로 통과한다.

## 계약

- **하한의 출처는 `requires-python` 선언 하나다.** CI 매트릭스에서 읽지 않는다 —
  CI 는 3.10/3.11/3.12 를 섞어 쓰므로 그쪽을 기대값으로 삼으면 선언과 갈라진다.
- **판정은 긍정 증거로 한다** (`sdk_matrix` 와 같은 규율). "실패가 안 보였다" 가
  아니라 "하한 해석기가 N개를 실제로 컴파일했다" 를 요구한다. 해석기를 못 구하면
  통과가 아니라 **미측정**이다.
- **저장소에 아무것도 쓰지 않는다.** `py_compile` 은 `__pycache__` 를 소스 옆에
  남기므로 쓰지 않는다 — 메모리에서 `compile()` 만 한다.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

#: `requires-python` 에서 하한을 뽑는다. toml 파서를 쓰지 않는 이유: 하한 해석기가
#: 3.10 일 수 있고 `tomllib` 은 3.11+ 다. 읽는 필드가 하나뿐이라 정규식으로 족하다.
_REQUIRES_RE = re.compile(r"^\s*requires-python\s*=\s*[\"']\s*>=\s*(\d+)\.(\d+)", re.MULTILINE)


@dataclass(frozen=True)
class FloorProbe:
    """하한 판정 1회의 결과. 측정과 판정을 나눠 되주입이 가능하게 한다."""

    floor: tuple[int, int] | None
    floor_source: str
    interpreter: str | None
    interpreter_version: str | None
    compiled: int
    failures: list[tuple[str, str]]
    unmeasured_reason: str | None

    @property
    def measured(self) -> bool:
        return self.unmeasured_reason is None


def declared_floor(pyproject: Path) -> tuple[int, int] | None:
    """`requires-python = ">=X.Y"` 의 하한. 선언이 정본이다."""
    if not pyproject.is_file():
        return None
    match = _REQUIRES_RE.search(pyproject.read_text(encoding="utf-8"))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def find_interpreter(floor: tuple[int, int]) -> str | None:
    """하한 해석기를 찾는다 — PATH 우선, 없으면 `uv` 에게 묻는다.

    `uv` 는 이 저장소의 개발 환경에 이미 있다 (`.venv` 를 만든 도구). 없으면 None 을
    돌려주고 호출자가 **미측정**으로 처리한다 — 없는 것을 통과로 세지 않는다.
    """
    name = f"python{floor[0]}.{floor[1]}"
    found = shutil.which(name)
    if found:
        return found
    uv = shutil.which("uv")
    if not uv:
        return None
    for args in (["python", "find", f"{floor[0]}.{floor[1]}"],
                 ["python", "install", f"{floor[0]}.{floor[1]}"]):
        try:
            proc = subprocess.run([uv, *args], capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if args[1] == "find" and proc.returncode == 0:
            path = proc.stdout.strip().splitlines()[-1].strip() if proc.stdout.strip() else ""
            if path and Path(path).exists():
                return path
    # install 뒤 한 번 더 묻는다
    try:
        proc = subprocess.run([uv, "python", "find", f"{floor[0]}.{floor[1]}"],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    path = proc.stdout.strip().splitlines()[-1].strip() if proc.returncode == 0 and proc.stdout.strip() else ""
    return path if path and Path(path).exists() else None


#: 하한 해석기 안에서 도는 스크립트. **파일을 쓰지 않는다** — `compile()` 만 한다.
#: `py_compile` 을 쓰면 `__pycache__` 가 소스 옆에 생겨 저장소를 오염시킨다.
_COMPILE_SCRIPT = r"""
import json, sys
paths = json.load(sys.stdin)
failures = []
for p in paths:
    try:
        with open(p, "rb") as fh:
            src = fh.read()
        compile(src, p, "exec")
    except SyntaxError as exc:
        failures.append([p, "%s (line %s)" % (exc.msg, exc.lineno)])
    except OSError as exc:
        failures.append([p, "read error: %s" % exc])
json.dump({"compiled": len(paths) - len(failures), "failures": failures}, sys.stdout)
"""


def probe(source_root: Path, pyproject: Path) -> FloorProbe:
    """선언 하한으로 `source_root` 아래 `*.py` 전부를 컴파일해 본다."""
    floor = declared_floor(pyproject)
    if floor is None:
        return FloorProbe(None, str(pyproject), None, None, 0, [],
                          "requires-python 선언을 읽지 못했다")

    paths = sorted(
        str(p) for p in source_root.rglob("*.py")
        if "__pycache__" not in p.parts and ".venv" not in p.parts
    )
    if not paths:
        return FloorProbe(floor, str(pyproject), None, None, 0, [],
                          f"{source_root} 아래에서 *.py 를 찾지 못했다")

    interpreter = find_interpreter(floor)
    if interpreter is None:
        return FloorProbe(
            floor, str(pyproject), None, None, 0, [],
            f"하한 해석기 python{floor[0]}.{floor[1]} 를 구하지 못했다 "
            f"(PATH 에도 없고 uv 로도 못 얻었다) — 통과가 아니라 미측정이다",
        )

    try:
        ver = subprocess.run([interpreter, "-c", "import sys;print('%d.%d.%d'%sys.version_info[:3])"],
                             capture_output=True, text=True, timeout=60).stdout.strip()
        proc = subprocess.run([interpreter, "-c", _COMPILE_SCRIPT], input=json.dumps(paths),
                              capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return FloorProbe(floor, str(pyproject), interpreter, None, 0, [],
                          f"하한 해석기 실행 실패: {exc}")
    if proc.returncode != 0:
        return FloorProbe(floor, str(pyproject), interpreter, ver, 0, [],
                          f"하한 해석기가 exit {proc.returncode}: {proc.stderr[-200:]}")

    data = json.loads(proc.stdout)
    return FloorProbe(
        floor=floor,
        floor_source=str(pyproject),
        interpreter=interpreter,
        interpreter_version=ver,
        compiled=int(data["compiled"]),
        failures=[(f[0], f[1]) for f in data["failures"]],
        unmeasured_reason=None,
    )


def main(argv: list[str] | None = None) -> int:
    """로컬 재현 진입점 — `sdk_matrix --run-local` 과 같은 자리.

    대상 저장소는 **cwd 에서** 해석한다 (`resolve_workspace_root`). `Path(__file__)`
    파생으로 잡으면 설치본에서 `<venv>/lib/.../workflow-source` 를 대상으로 삼는다 —
    이 저장소가 여섯 번 고친 결함족이고 `check_deployed_layout` case 1 이 잡는다.
    """
    from workflow_kit.common.paths import resolve_workspace_root

    repo_root, _why = resolve_workspace_root()
    source_root = repo_root / "workflow-source"
    if not source_root.is_dir():
        # 소비 프로젝트에는 이 하위 디렉터리가 없다 — 그때는 저장소 루트를 훑는다.
        source_root = repo_root
    result = probe(source_root, source_root / "pyproject.toml")
    if not result.measured:
        print(f"[unmeasured] {result.unmeasured_reason}")
        return 2
    floor = f"{result.floor[0]}.{result.floor[1]}" if result.floor else "?"
    print(f"선언 하한 {floor} (출처: requires-python) · 해석기 {result.interpreter_version}")
    print(f"컴파일 {result.compiled}개 / 실패 {len(result.failures)}건")
    for path, why in result.failures:
        print(f"  ✗ {path}: {why}")
    return 1 if result.failures else 0


if __name__ == "__main__":
    sys.exit(main())
