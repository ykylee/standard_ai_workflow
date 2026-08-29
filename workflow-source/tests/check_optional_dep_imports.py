"""선언한 optional dep 의 import 가 **실제로 되는가** (TASK-2026-07-29-main-002).

## 왜 필요한가

`[tool.mypy]` 의 `ignore_missing_imports = true` 는 없는 모듈을 error 가 아니라
`Any` 로 바꾼다. mcp 2.0.0 이 `mcp.server.fastmcp` 를 통째로 없앴을 때 mypy 가 보고한
것은 "모듈이 없다" 가 아니라 엉뚱한 줄의 `no-any-return` 이었다 (§2.41). 원인에서 한 칸
떨어진 신호였고, 실제 사실은 `sys.exit(1)` 로 죽는 **런타임 파손**이었다.

**그 설정을 좁히는 것은 답이 아니다.** optional dep 은 실제로 optional 이라
`mcp.*` 만 override 에서 빼면 SDK 를 안 깐 로컬에서 mypy 가 red 가 된다. mypy 는
"안 깔림" 과 "깔렸는데 모듈이 사라짐" 을 구분하지 못한다 — 그 구분은 런타임 import
에서만 된다. 그래서 판정을 여기로 옮긴다.

## 계약

1. 배포판이 **깔려 있으면** 그 extra 의 `required_modules` 는 전부 import 된다.
   하나라도 안 되면 **실패**한다 — "모듈 없음" 으로, 그 모듈 이름을 대고.
2. `alternative_modules` 묶음은 **하나만** 되면 된다 (SDK 가 이름을 옮겨도 코드가
   양쪽을 해석하므로). 묶음 전체가 안 되면 실패한다.
3. 배포판이 **안 깔렸으면** skip 하되 **조용히 넘어가지 않는다** — 몇 개를 건너뛰었는지
   출력한다. "어느 목록에도 없으면 통과" 가 이 저장소가 이미 당한 결함이다 (§2.39).
4. `pyproject.toml` 의 extra 와 정본 registry 가 **양방향으로** 일치한다. 새 extra 를
   등록 안 하면 실패하고, 없는 extra 를 등록해도 실패한다.
5. import 대상은 정본(`common/optional_deps.py`) 하나뿐이다 — 소비자가 자기 사본을
   들고 있지 않다.

Cross-ref: TASK-2026-07-29-main-002, releases/Beta-v1.0.0.md §2.44.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import importlib
import importlib.metadata
import sys
import tomllib
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.optional_deps import (  # noqa: E402
    OPTIONAL_DEPENDENCIES,
    OptionalDependency,
    optional_dependency_for,
)

PYPROJECT_PATH = SOURCE_ROOT / "pyproject.toml"

_skipped: list[str] = []


def _declared_extras() -> set[str]:
    data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    return set(data["project"]["optional-dependencies"])


def _is_installed(dependency: OptionalDependency) -> bool:
    """배포판이 하나라도 깔려 있는가."""
    for distribution in dependency.distributions:
        try:
            importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            continue
        return True
    return False


def _import_error(module_name: str) -> str | None:
    try:
        importlib.import_module(module_name)
    except ImportError as exc:
        return f"{type(exc).__name__}: {exc}"
    return None


def test_registry_matches_declared_extras() -> None:
    declared = _declared_extras()
    registered = {dependency.extra for dependency in OPTIONAL_DEPENDENCIES}
    assert not (declared - registered), (
        f"pyproject 에 있는데 정본 registry 에 없는 extra: {sorted(declared - registered)} "
        "— common/optional_deps.py 에 등록할 것 (import 하는 게 없으면 required_modules=() 로 명시)"
    )
    assert not (registered - declared), (
        f"registry 에만 있는 extra: {sorted(registered - declared)} — pyproject 에서 지워졌는가?"
    )


def test_empty_targets_are_explained() -> None:
    """import 대상이 없는 extra 는 왜 없는지 적혀 있어야 한다."""
    for dependency in OPTIONAL_DEPENDENCIES:
        if dependency.required_modules or dependency.alternative_modules:
            continue
        assert dependency.note.strip(), (
            f"{dependency.extra}: import 대상이 없는데 이유(note)가 비어 있다 — "
            "빠뜨린 것인지 원래 없는 것인지 구분되지 않는다"
        )


def test_installed_extras_import_required_modules() -> None:
    """**이 검사가 이번 작업의 본체다.** 깔려 있는데 모듈이 없으면 실패."""
    problems: list[str] = []
    for dependency in OPTIONAL_DEPENDENCIES:
        if not dependency.distributions:
            continue
        if not _is_installed(dependency):
            _skipped.append(f"{dependency.extra}(미설치)")
            continue
        for module_name in dependency.required_modules:
            error = _import_error(module_name)
            if error is not None:
                problems.append(
                    f"{dependency.extra}: 배포판은 깔려 있는데 '{module_name}' 모듈이 없다 ({error})"
                )
    assert not problems, "\n      ".join(problems)


def test_installed_extras_satisfy_alternative_groups() -> None:
    problems: list[str] = []
    for dependency in OPTIONAL_DEPENDENCIES:
        if not dependency.alternative_modules or not _is_installed(dependency):
            continue
        for group in dependency.alternative_modules:
            errors = {name: _import_error(name) for name in group}
            if all(error is not None for error in errors.values()):
                problems.append(
                    f"{dependency.extra}: 대안 묶음 {list(group)} 이 **전부** import 실패 "
                    f"— SDK 가 또 이름을 옮겼는가? ({errors})"
                )
    assert not problems, "\n      ".join(problems)


def test_consumers_do_not_keep_their_own_copy() -> None:
    """소비자가 정본에서 가져오는가 (사본을 들고 있지 않은가)."""
    from workflow_kit.server import read_only_mcp_sdk

    dependency = optional_dependency_for("mcp-sdk")
    assert dependency is not None
    assert tuple(read_only_mcp_sdk.SDK_IMPORT_TARGETS) == dependency.required_modules, (
        "read_only_mcp_sdk.SDK_IMPORT_TARGETS 가 정본과 다르다 — 사본이 갈라졌다\n"
        f"      소비자: {tuple(read_only_mcp_sdk.SDK_IMPORT_TARGETS)}\n"
        f"      정본  : {dependency.required_modules}"
    )
    source = (SOURCE_ROOT / "workflow_kit/server/read_only_mcp_sdk.py").read_text(encoding="utf-8")
    assert "optional_deps" in source, (
        "read_only_mcp_sdk.py 가 정본 모듈을 import 하지 않는다 — 값만 우연히 같을 수 있다"
    )


def test_missing_module_is_reported_as_missing_module() -> None:
    """완료 기준: 모듈이 사라지면 `no-any-return` 이 아니라 '모듈 없음' 으로 실패한다.

    실제로 사라진 모듈(`mcp.server.fastmcp` 는 2.0.0 에 없다)을 required 로 놓고
    판정 함수를 돌려, 이 층이 내는 신호가 무엇인지 확인한다.
    """
    probe = OptionalDependency(
        extra="probe",
        distributions=("mcp",),
        required_modules=("mcp.server.definitely_not_a_real_module",),
    )
    if not _is_installed(probe):
        _skipped.append("probe(mcp 미설치)")
        return
    error = _import_error(probe.required_modules[0])
    assert error is not None, "없는 모듈이 import 됐다"
    assert "ModuleNotFoundError" in error or "No module named" in error, (
        f"'모듈 없음' 이 아닌 다른 신호가 나왔다: {error}"
    )


def main() -> int:
    test_funcs = [
        test_registry_matches_declared_extras,
        test_empty_targets_are_explained,
        test_installed_extras_import_required_modules,
        test_installed_extras_satisfy_alternative_groups,
        test_consumers_do_not_keep_their_own_copy,
        test_missing_module_is_reported_as_missing_module,
    ]
    failures: list[tuple[str, str]] = []
    for func in test_funcs:
        try:
            func()
            print(f"  PASS: {func.__name__}")
        except AssertionError as e:
            failures.append((func.__name__, f"AssertionError: {e}"))
            print(f"  FAIL: {func.__name__} — {e}")
        except Exception as e:  # noqa: BLE001
            failures.append((func.__name__, f"{type(e).__name__}: {e}"))
            print(f"  FAIL: {func.__name__} — {type(e).__name__}: {e}")

    # skip 을 조용히 넘기지 않는다 — 무엇을 안 봤는지가 결과의 일부다.
    if _skipped:
        print(f"  (skip) 미설치라 건너뛴 extra {len(_skipped)}건: {', '.join(sorted(set(_skipped)))}")
    else:
        print("  (skip 0건 — 선언한 extra 를 전부 실제로 검사했다)")

    total = len(test_funcs)
    print(f"\n{total - len(failures)}/{total} PASS")
    if failures:
        for name, err in failures:
            print(f"  - {name}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
