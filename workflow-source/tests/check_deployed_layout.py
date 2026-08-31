#!/usr/bin/env python3
"""패키지가 **저장소 체크아웃 레이아웃**에 기대지 않는지 고정한다 (5 cases).

## 계보 (TASK-2026-08-18-main-003)

소비자는 ``standard-ai-workflow`` 를 **wheel 로 설치**한다. 그러면 ``workflow_kit``
패키지만 존재하고 ``workflow-source/`` 라는 디렉터리는 없다. 그런데 패키지 코드 여럿이
자기 파일 위치에서 ``REPO_ROOT/"workflow-source"/...`` 를 역산해 **파일을 읽거나
subprocess 로 실행**하고 있었다. 2026-08-18 실측 red 3건:

- ``wk wiki-emit`` — ``workflow-source/tools/refresh_wiki_memory.py`` 실행. 그 파일은
  v1.2.0 shim drop 이후 **저장소에도 없었다** → 배포본 이전에 이 저장소에서 죽어 있었다.
- ``wk rotate-workflow-logs`` — 기본 handoff 가 ``<venv>/lib/python3.x/ai-workflow/…``.
- ``wk install-pre-push-hook`` — hook 원본이 wheel 미포함 자산 + git root 를 모듈
  위치에서 물었다.

## 왜 개발 호스트가 못 잡았나 — 이 검사의 존재 이유

개발 호스트의 ``wk`` 는 **editable 설치**라 ``parents[3]`` 가 우연히 맞는다. 전량 검사도
`wk` 도 전부 체크아웃에서 도니까, 이 어긋남은 **로컬에서 영원히 green** 이다 (SDK 매트릭스
· 브랜치 매트릭스와 같은 계열의 사각지대). 그래서 실행이 아니라 **레이아웃 계약**으로 잰다.

## 5번째 case 의 계보 (TASK-2026-09-01-main-001)

`[tool.setuptools] packages` 는 **손 목록**이고, 거기서 빠진 하위 패키지는 wheel 에
디렉터리째 실리지 않는다. 그런데 저장소 체크아웃에는 그 디렉터리가 실재하니 위와 똑같은
사각지대가 성립한다 — 로컬 영원히 green, 소비자만 `ModuleNotFoundError`. 실제로 **세 번**
났다: `common.state|contracts|schemas` (v0.5.7.1 hotfix) · `tools` (v1.1.7) ·
`cli` (v1.8.0 까지 실려 나갔다). 세 번 다 사람이 목록 갱신을 잊은 것이라, 사람에게 다시
부탁하는 대신 **디스크와 대조**한다.

`tools/check_packaging.py` 도 같은 축을 재지만 그쪽은 **빌드된 wheel** 이 있어야 하는
릴리스 시점 검사다. 게이트에서 매번 도는 정적 대조는 여기 있어야 한다.

5 cases:
  1) `workflow_kit/` 이 `"workflow-source"` 를 경로로 조립하지 않는다 (선언된 예외만)
  2) 런타임 자산은 `workflow_kit/assets/` 아래 있고 실재한다
  3) 그 자산이 pyproject `package-data` 에 선언돼 있다 (선언 없으면 wheel 에 안 실린다)
  4) 자기 모듈을 **파일 경로로** 재실행하지 않는다 — `-m` 으로 부른다 (선언된 예외만)
  5) 디스크의 모든 하위 패키지가 pyproject `packages` 에 선언돼 있다 (양방향)
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = TESTS_DIR.parent
PKG = SOURCE_ROOT / "workflow_kit"
PYPROJECT = SOURCE_ROOT / "pyproject.toml"

FAILURES: list[str] = []

#: `"workflow-source"` 를 경로로 조립해도 되는 모듈 — **저장소에서만 도는 것들**.
#: 이유를 함께 적는다. 목록이 늘어나면 그만큼 소비자 표면이 좁아진다는 뜻이다.
LAYOUT_EXEMPT: dict[str, str] = {
    "plugin_payload.py": "플러그인 페이로드 빌더 — 저장소 체크아웃에서만 돈다",
    "plugin_distribution.py": "배포 산출물 빌더 — 저장소 체크아웃에서만 돈다",
    "release_status.py": "릴리스 파이프라인 — 저장소 체크아웃에서만 돈다",
    "upgrade_diff.py": "문서 문자열의 경로 표기",
    "path_resolver.py": "in-repo 경로 예시 문자열 (해석 대상이지 조립 대상이 아니다)",
    "tools/release_pipeline.py": "릴리스 파이프라인 — 저장소 전용",
    "tools/release_pipeline_dist.py": "릴리스 파이프라인 — 저장소 전용",
    "tools/release_pipeline_changelog.py": "릴리스 파이프라인 — 저장소 전용",
    "tools/watch_transient_writer.py": "전량 검사 보조 — 저장소 전용",
    "tools/wiki_emit.py": "REPO_ROOT 는 소비자 저장소, 문서 문자열만 남음",
    "tools/score_wiki_maintainability.py": "wiki 점수 — 저장소 문서 트리를 잰다",
    "tools/score_wiki_trend.py": "wiki 점수 — 저장소 문서 트리를 잰다",
    "tools/refresh_wiki_memory.py": "wiki 원본 미러 — 저장소 문서 트리를 잰다",
    "tools/migrate_active_to_appendonly.py": "일회성 마이그레이션 — 저장소 전용",
    "tools/seed_workspace_memory.py": "안내 문자열의 경로 표기",
    "tools/claim_workspace.py": "안내 문자열의 경로 표기",
    "tools/wiki_emit_shim.py": "미사용 shim",
    "server/read_only_registry.py": "script_path 는 **설명용 메타데이터**이지 실행 경로가 아니다",
}

#: subprocess 인자로 `.py` 파일 경로를 넘겨도 되는 모듈 (같은 이유).
EXEC_EXEMPT: dict[str, str] = {
    "cli_commands_release.py": "릴리스 파이프라인 — 저장소 전용",
    "tools/release_pipeline.py": "릴리스 파이프라인 — 저장소 전용",
    "tools/release_pipeline_lib.py": "릴리스 파이프라인 — 저장소 전용",
    "tools/release_v0_13_0.py": "릴리스 파이프라인 — 저장소 전용",
    "tools/audit_root_anchors.py": "git ls-files 의 glob 인자 (`*.py`)",
    "tools/fix_readme_for_release.py": "안내 문자열",
    "tools/sync_release_hash.py": "릴리스 파이프라인 — 저장소 전용",
    "common/sdk_matrix.py": "SDK 매트릭스 — 저장소의 전량 검사를 여러 SDK 버전으로 돌린다",
}

#: 런타임에 읽는 자산 — 패키지 안에 있어야 하고 package-data 에 선언돼야 한다.
RUNTIME_ASSETS = (
    ("assets/hooks/pre-push-no-force.sh", "assets/hooks/*.sh"),
    ("assets/reverse-engineering/01-business-overview.md", "assets/reverse-engineering/*.md"),
    ("assets/prompts/code_worker.md", "assets/prompts/*.md"),
)


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """docstring 인 문자열 노드의 id — 산문은 계약이 아니다."""
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                out.add(id(body[0].value))
    return out


def _used_only_for_sys_path(tree: ast.AST, name: str) -> bool:
    """``name`` 의 모든 Load 사용처가 ``sys.path`` 관련 statement 안인가."""
    guarded: set[int] = set()
    for node in ast.walk(tree):
        touches_sys_path = any(
            isinstance(sub, ast.Attribute) and sub.attr == "path"
            and isinstance(sub.value, ast.Name) and sub.value.id == "sys"
            for sub in ast.walk(node)
        )
        if touches_sys_path:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and sub.id == name:
                    guarded.add(id(sub))
    return all(
        id(node) in guarded
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == name
    )


def _load_sources() -> list[tuple[str, str, ast.AST]]:
    out = []
    for f in sorted(PKG.rglob("*.py")):
        rel = str(f.relative_to(PKG))
        src = f.read_text(encoding="utf-8")
        out.append((rel, src, ast.parse(src)))
    return out


def _module_derived_roots(tree: ast.AST) -> set[str]:
    """``Path(__file__)…parents[N]`` 에서 역산한 이름들 (전이 포함).

    이 검사가 겨냥하는 것은 **모듈 자신의 설치 위치를 체크아웃이라고 가정하는 것**이다.
    런타임에 발견한 타깃 workspace(``project_root`` / ``target_root`` 등) 밑의
    ``workflow-source/`` 는 정당하다 — 이 저장소를 자기 자신에게 적용할 때 실제로
    그런 디렉터리가 있다. 둘을 섞어 재면 검사가 현상 유지를 박제하게 된다.
    """
    roots: set[str] = set()
    for _ in range(3):  # 전이 (REPO_ROOT → SOURCE_ROOT → …)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not isinstance(node.targets[0], ast.Name):
                continue
            src_names = {n.id for n in ast.walk(node.value) if isinstance(n, ast.Name)}
            has_file = any(
                isinstance(n, ast.Name) and n.id == "__file__" for n in ast.walk(node.value)
            )
            if has_file or (src_names & roots):
                roots.add(node.targets[0].id)
    return roots


def case_1_no_checkout_layout_paths(sources) -> None:
    offenders: list[str] = []
    for rel, src, tree in sources:
        if rel in LAYOUT_EXEMPT:
            continue
        roots = _module_derived_roots(tree)
        if not roots:
            continue
        lines = src.split("\n")
        for node in ast.walk(tree):
            if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
                continue
            names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            if not (names & roots):
                continue
            consts = [
                n.value for n in ast.walk(node)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
            ]
            if "workflow-source" not in consts:
                continue
            # `X = <root> / "workflow-source"` 를 sys.path 에만 쓰는 형태는 무해하다
            # (없는 경로를 넣는 no-op, 체크아웃에서 설치 없이 실행할 때만 의미).
            holder = None
            for stmt in ast.walk(tree):
                if isinstance(stmt, ast.Assign) and any(b is node for b in ast.walk(stmt.value)) \
                        and isinstance(stmt.targets[0], ast.Name):
                    holder = stmt.targets[0].id
            if holder and _used_only_for_sys_path(tree, holder):
                continue
            offenders.append(f"{rel}:{node.lineno}: {lines[node.lineno - 1].strip()[:90]}")
    assert not offenders, (
        "**모듈 자신의 설치 위치**에서 체크아웃 레이아웃(`workflow-source/`)을 역산한다 — "
        "설치본에는 그런 디렉터리가 없다:\n  "
        + "\n  ".join(sorted(set(offenders)))
        + "\n저장소 전용 모듈이면 LAYOUT_EXEMPT 에 **이유와 함께** 선언한다."
    )


def case_2_runtime_assets_live_in_package(sources) -> None:
    for rel_asset, _pattern in RUNTIME_ASSETS:
        path = PKG / rel_asset
        assert path.is_file(), (
            f"런타임 자산이 패키지 안에 없다: {path}. "
            "런타임이 읽는 파일은 wheel 에 실려야 하므로 `workflow_kit/assets/` 아래에 둔다."
        )


def case_3_assets_declared_in_package_data(sources) -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    block = text.split("[tool.setuptools.package-data]", 1)
    assert len(block) == 2, "pyproject 에 [tool.setuptools.package-data] 가 없다"
    declared = block[1].split("\n[", 1)[0]
    for _rel_asset, pattern in RUNTIME_ASSETS:
        assert pattern in declared, (
            f"package-data 에 `{pattern}` 선언이 없다 — 선언 없으면 wheel 에 안 실리고, "
            "설치본에서 그 자산을 읽는 명령이 죽는다."
        )


def case_4_no_module_reexec_by_file_path(sources) -> None:
    offenders: list[str] = []
    for rel, src, tree in sources:
        if rel in EXEC_EXEMPT:
            continue
        docs = _docstring_nodes(tree)
        lines = src.split("\n")
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            is_run = (isinstance(func, ast.Attribute) and func.attr in ("run", "Popen")
                      and isinstance(func.value, ast.Name) and func.value.id == "subprocess")
            if not is_run or not node.args:
                continue
            for sub in ast.walk(node.args[0]):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str) \
                        and sub.value.endswith(".py") and id(sub) not in docs:
                    offenders.append(f"{rel}:{sub.lineno}: {lines[sub.lineno - 1].strip()[:90]}")
    assert not offenders, (
        "자기 모듈을 **파일 경로로** 재실행한다 — 설치본에는 그 경로가 없다. "
        "`python -m <module>` (workflow_kit.common.child_process.module_command) 로 부른다:\n  "
        + "\n  ".join(offenders)
    )


def _declared_packages(text: str) -> set[str]:
    """pyproject `[tool.setuptools]` 의 `packages = [...]` 를 읽는다.

    `tomllib` 을 안 쓰는 이유: `requires-python = ">=3.10"` 이고 tomllib 은 3.11+ 다.
    이 검사가 3.10 에서만 조용히 빠지면 검사의 존재 이유가 사라진다.
    """
    after = text.split("[tool.setuptools]", 1)
    assert len(after) == 2, "pyproject 에 [tool.setuptools] 가 없다"
    block = after[1].split("packages = [", 1)
    assert len(block) == 2, "[tool.setuptools] 에 packages 선언이 없다"
    return set(re.findall(r'"([^"]+)"', block[1].split("]", 1)[0]))


def _ondisk_packages() -> set[str]:
    """`.py` 를 담은 디스크의 디렉터리 → 점 표기 패키지 이름."""
    out: set[str] = set()
    for f in PKG.rglob("*.py"):
        parts = f.parent.relative_to(PKG.parent).parts
        if "__pycache__" in parts:
            continue
        out.add(".".join(parts))
    return out


def case_5_every_ondisk_package_is_declared(sources) -> None:
    declared = _declared_packages(PYPROJECT.read_text(encoding="utf-8"))
    ondisk = _ondisk_packages()
    undeclared = sorted(ondisk - declared)
    assert not undeclared, (
        "디스크에 있는데 pyproject `[tool.setuptools] packages` 에 없는 하위 패키지: "
        f"{undeclared}. 선언이 없으면 wheel 에 **디렉터리째** 안 실린다 — 체크아웃에는 "
        "그 디렉터리가 있으니 로컬은 green 이고 소비자만 ModuleNotFoundError 다 "
        "(v0.5.7.1 · v1.1.7 · v1.8.0 에서 세 번)."
    )
    phantom = sorted(declared - ondisk)
    assert not phantom, (
        f"pyproject `packages` 가 디스크에 없는 패키지를 선언한다: {phantom}. "
        "이름이 바뀌었거나 지워진 뒤 목록만 남은 것이다 — setuptools 가 조용히 넘기므로 "
        "여기서 잡지 않으면 목록이 사실과 갈라진 채 굳는다."
    )


def _run(fn, sources) -> None:
    try:
        fn(sources)
        print(f"  PASS  {fn.__name__}")
    except AssertionError as e:
        FAILURES.append(fn.__name__)
        print(f"  FAIL  {fn.__name__} — {e}")
    except Exception as e:  # noqa: BLE001
        FAILURES.append(fn.__name__)
        print(f"  FAIL  {fn.__name__} — 예외 {type(e).__name__}: {e}")


def main() -> int:
    print("=== 배포 레이아웃 계약 (패키지가 체크아웃에 기대지 않는가) ===")
    sources = _load_sources()
    for fn in (case_1_no_checkout_layout_paths,
               case_2_runtime_assets_live_in_package,
               case_3_assets_declared_in_package_data,
               case_4_no_module_reexec_by_file_path,
               case_5_every_ondisk_package_is_declared):
        _run(fn, sources)
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    print("\n5/5 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
