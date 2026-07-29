"""optional dependency 의 **import 대상 정본** (TASK-2026-07-29-main-002).

## 왜 이 파일이 있는가

`pyproject.toml` 의 `[tool.mypy]` 는 `ignore_missing_imports = true` 다. 그 설정은
없는 모듈을 **error 가 아니라 `Any`** 로 바꾼다. 그래서 mcp 2.0.0 이
`mcp.server.fastmcp` 를 통째로 없앴을 때 mypy 가 보고한 것은 "모듈이 없다" 가 아니라
엉뚱한 줄의 `no-any-return` 이었다 (릴리스 노트 §2.41). 원인에서 한 칸 떨어진 신호다.

그 설정을 좁히는 것으로는 못 고친다. **optional dep 은 실제로 optional 이라서**,
`mcp.*` 만 override 에서 빼면 SDK 를 안 깐 로컬에서 mypy 가 red 가 된다. 즉 mypy 는
"안 깔린 것" 과 "깔렸는데 모듈이 없어진 것" 을 구분할 수 없다 — 그 구분은 **런타임
import** 에서만 가능하다.

그래서 판정을 런타임으로 옮기고, 이 파일이 그 판정의 입력이 된다:

- **무엇을 import 해서 쓰는지** 를 여기에 한 번만 적는다.
- `check_optional_dep_imports.py` 가 "배포판은 깔렸는데 그 모듈이 import 안 된다" 를
  **실패**로 만든다. 안 깔렸으면 skip 하되 **조용히 넘어가지 않고 드러낸다**.

## 두 종류의 대상

- `required_modules` — 그 extra 를 깔았다면 **전부** import 돼야 한다.
- `alternative_modules` — 묶음 안에서 **하나만** 되면 된다. SDK 가 이름을 옮겨도
  코드가 양쪽을 해석하기 때문이다 (`mcp.server.mcpserver` ↔ `mcp.server.fastmcp`).
  이 구분이 없으면 2.x 환경에서 검사 자체가 틀린 실패를 낸다.

extra 를 새로 만들면 여기에도 등록해야 한다. import 해서 쓰는 게 없으면
`required_modules=()` 로 **명시**한다 — 검사가 "등록 안 된 extra" 를 따로 실패로
드러내므로, 빠뜨리면 통과하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OptionalDependency:
    """`[project.optional-dependencies]` 의 한 extra 와 그 import 대상."""

    extra: str
    """pyproject 의 extra key. 검사가 이 이름으로 선언과 대조한다."""

    distributions: tuple[str, ...]
    """`importlib.metadata` 로 설치 여부를 볼 배포판 이름."""

    required_modules: tuple[str, ...] = ()
    """설치돼 있으면 **전부** import 돼야 하는 모듈."""

    alternative_modules: tuple[tuple[str, ...], ...] = ()
    """묶음마다 **하나만** import 되면 되는 모듈들."""

    note: str = field(default="")
    """import 대상이 없는 extra 는 왜 없는지 여기에 적는다 (subprocess 전용 등)."""


OPTIONAL_DEPENDENCIES: tuple[OptionalDependency, ...] = (
    OptionalDependency(
        extra="mcp-sdk",
        distributions=("mcp",),
        required_modules=(
            "mcp.types",
            "mcp.server.stdio",
            "mcp.server.lowlevel",
            "mcp.server.models",
        ),
        alternative_modules=(
            # 2.x 는 `mcpserver.MCPServer`, 1.x 는 `fastmcp.FastMCP`.
            # `mcp_v1_server.py` 가 이 순서로 시도한다.
            ("mcp.server.mcpserver", "mcp.server.fastmcp"),
        ),
    ),
    OptionalDependency(
        extra="mcp-jsonrpc",
        distributions=(),
        note="의존성 없는 draft fixture — 항상 사용 가능하다 (pyproject 에서도 빈 목록).",
    ),
    OptionalDependency(
        extra="pbt",
        distributions=("hypothesis",),
        required_modules=("hypothesis",),
    ),
    OptionalDependency(
        extra="profiling",
        distributions=("objgraph",),
        required_modules=("objgraph",),
    ),
    OptionalDependency(
        extra="dev",
        distributions=("pytest", "pytest-asyncio", "ruff", "mypy", "pyyaml"),
        note=(
            "workflow_kit / tools 는 이 중 어느 것도 import 하지 않는다. "
            "mypy·ruff 는 subprocess 로, pytest 는 tests/ 에서만 쓴다."
        ),
    ),
    OptionalDependency(
        extra="release",
        distributions=("build", "twine"),
        required_modules=("build",),
        note="twine 은 subprocess 전용이다 (`release_pipeline.py`).",
    ),
)


def optional_dependency_for(extra: str) -> OptionalDependency | None:
    for dependency in OPTIONAL_DEPENDENCIES:
        if dependency.extra == extra:
            return dependency
    return None


def import_targets_for(extra: str) -> tuple[str, ...]:
    """required + alternative 를 평평하게 편 목록 (진단 출력용)."""
    dependency = optional_dependency_for(extra)
    if dependency is None:
        return ()
    flattened = list(dependency.required_modules)
    for group in dependency.alternative_modules:
        flattened.extend(group)
    return tuple(flattened)
