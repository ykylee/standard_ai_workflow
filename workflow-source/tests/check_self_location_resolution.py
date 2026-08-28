#!/usr/bin/env python3
"""'자기 설치 위치를 대상으로 오인' 결함족의 회귀 방지 (M-007/WBS-7.2).

같은 결함이 이 저장소에서 네 번 나왔다. 전부 같은 모양이다 — 도구가 대상 트리를
**cwd 의 작업 저장소**가 아니라 `Path(__file__)` 파생 경로에서 잡는다. 소스
체크아웃에서 돌리면 두 값이 우연히 같아서 보이지 않고, `uv tool` / wheel 설치본에서만
드러난다:

- `release-status` 의 `local_mypy` 탐침 (TASK-2026-08-25-main-022) — 자기 인터프리터를 쟀다
- `suggest-memory-entries` 기본 handoff 경로 (TASK-2026-08-25-main-023)
- `archive-branch-memory` 기본 `--memory-root` (TASK-2026-08-28-main-003)
- `release-bump` 등 release 파이프라인의 `pyproject.toml` (TASK-2026-08-28-main-012)

본 검사는 뒤의 두 사본을 잡는다 (앞의 두 개는 각각
`check_release_status_v0_11_14` · `check_memory_entry_suggestions` 안에 있다).
**다음 사본도 여기에 붙인다** — 이 결함족이 모이는 자리다.

검증 케이스 (7):
    1. archive — cwd 의 작업 저장소를 memory root 로 해석 + path_source 명시
    2. archive — 브랜치를 **그 workspace 의 git** 에서 얻는다 (모듈 저장소가 아니라)
    3. archive — active dir 부재는 path_source 를 담은 exit 2 (조용한 폴백 금지)
    4. archive — git 아닌 트리에서는 판정 자체를 거부한다 (생존 판정의 근거 부재)
    5. release — 설치본 레이아웃은 두 경로를 명시하고 거부 (traceback 아님)
    6. release — 체크아웃 레이아웃은 통과 (판정이 정상 경로를 막지 않는다)
    7. release — cwd 에서 위로 거슬러 kit 체크아웃을 찾는다
    8. **정적** — `wk` 로 노출된 진입점의 `add_argument` 기본값이 모듈 위치 파생이
       아니다. 앞의 7개가 *사본 하나*를 잡는다면 이것은 **다음 사본이 생기는 것**을
       막는다 (2026-08-28: 사본을 하나씩 쫓는 것을 그만두기로 한 자리).

Stdlib only (+ subprocess 로 CLI 실측).
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
)
"""kit 전체가 import 표면이다 + 체크아웃 판정이 읽는 pyproject.

두 도구(`archive_branch_memory` / `release_pipeline_lib`)와 그 경로 해석 정본
(`common/paths.py`)을 재는데, 도구는 CLI 로 띄워지고 import 는 transitively
닫힌다 (ADR-028 결정 4). `pyproject.toml` 은 meta-watch 실측이 지목했다 —
`_require_source_checkout` 이 '여기가 체크아웃인가' 를 그 파일의 존재로 판정하므로
입력 표면이 맞다 (2026-08-28 첫 실행에서 선언 밖 접근 1건으로 잡혔다)."""

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
ARCHIVER = SOURCE_ROOT / "workflow_kit" / "tools" / "archive_branch_memory.py"
RELEASE_LIB = SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline_lib.py"

#: fixture 밖의 브랜치 컨텍스트가 이기지 않도록 걷어낸다 (CI 의 GITHUB_REF_NAME 등).
BRANCH_ENV_KEYS = (
    "CODEX_WORKFLOW_BRANCH", "GITHUB_HEAD_REF", "GITHUB_REF_NAME",
    "CI_COMMIT_REF_NAME", "BRANCH_NAME",
)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if not ok else ""))
    if not ok:
        failures.append(name)


def _clean_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in BRANCH_ENV_KEYS}
    env["PYTHONPATH"] = str(SOURCE_ROOT) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    return env


def _make_workspace(root: Path, *, branch: str | None, memory_branch: str) -> Path:
    """소비자 workspace fixture — profile + (선택) git + 브랜치 메모리 한 벌."""
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "PROJECT_PROFILE.md").write_text("# PROJECT_PROFILE\n", encoding="utf-8")
    branch_dir = root / "ai-workflow" / "memory" / "active" / memory_branch
    (branch_dir / "backlog").mkdir(parents=True)
    (branch_dir / "state.json").write_text("{}\n", encoding="utf-8")
    if branch is not None:
        subprocess.run(["git", "init", "-q", "-b", branch], cwd=str(root),
                       capture_output=True, text=True)
        # 커밋 0 인 저장소는 `git rev-parse --abbrev-ref HEAD` 가 실패해 브랜치
        # 해석이 모듈 저장소로 폴백된다 — 재려는 조건을 실재하게 만들려면 커밋이 필요하다.
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-q", "--allow-empty", "-m", "seed"],
            cwd=str(root), capture_output=True, text=True,
        )
    return root


def _run_archiver(cwd: Path) -> tuple[int, dict, str]:
    proc = subprocess.run(
        [sys.executable, str(ARCHIVER), "--dry-run", "--json"],
        cwd=str(cwd), capture_output=True, text=True, env=_clean_env(),
    )
    try:
        payload = json.loads(proc.stdout) if proc.stdout else {}
    except json.JSONDecodeError:
        payload = {}
    return proc.returncode, payload, proc.stderr


def _load_release_lib(root: Path, module_name: str):
    """`root/workflow_kit/tools/release_pipeline_lib.py` 사본을 모듈로 로드."""
    target = root / "workflow_kit" / "tools" / "release_pipeline_lib.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RELEASE_LIB, target)
    spec = importlib.util.spec_from_file_location(module_name, str(target))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod



def _module_location_names(tree: ast.Module) -> set[str]:
    """module-level 에서 ``__file__`` 파생으로 묶인 이름들 (REPO_ROOT / SOURCE_ROOT 등).

    ``REPO_ROOT = Path(__file__).resolve().parents[3]`` 와, 그것에서 다시 파생된
    ``SOURCE_ROOT = REPO_ROOT / "workflow-source"`` 까지 **전이적으로** 모은다.
    """
    names: set[str] = set()
    for _ in range(3):  # 파생의 파생까지 (고정점, 얕게)
        for node in tree.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            refs = {
                n.id for n in ast.walk(node.value) if isinstance(n, ast.Name)
            } | {
                n.id for n in ast.walk(node.value) if isinstance(n, ast.Name)
            }
            uses_file = any(
                isinstance(n, ast.Name) and n.id == "__file__"
                for n in ast.walk(node.value)
            )
            if uses_file or (refs & names):
                names.add(target.id)
    return names


def _module_location_defaults(path: Path) -> list[str]:
    """``add_argument(..., default=<모듈 위치 파생>)`` 을 찾아 flag 이름을 돌려준다."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tainted = _module_location_names(tree)
    if not tainted:
        return []
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "add_argument"):
            continue
        default = next((kw.value for kw in node.keywords if kw.arg == "default"), None)
        if default is None:
            continue
        if any(isinstance(n, ast.Name) and n.id in tainted for n in ast.walk(default)):
            flag = "?"
            if node.args and isinstance(node.args[0], ast.Constant):
                flag = str(node.args[0].value)
            found.append(flag)
    return found


def main() -> int:
    print("=== 자기 위치 오인 결함족 회귀 방지 ===")

    # --- archive-branch-memory (TASK-2026-08-28-main-003) --------------------
    with tempfile.TemporaryDirectory() as td:
        ws = _make_workspace(Path(td) / "consumer-ws", branch="feature/probe",
                             memory_branch="feature/probe")
        rc, payload, err = _run_archiver(ws)
        resolved = Path(payload.get("memory_root", "")) if payload.get("memory_root") else None
        expected = (ws / "ai-workflow" / "memory").resolve()
        check(
            "1) archive — cwd 의 작업 저장소를 memory root 로 해석 + path_source 명시",
            rc == 0 and resolved == expected
            and payload.get("path_source") == "cwd_project_profile",
            f"rc={rc} memory_root={resolved} source={payload.get('path_source')!r} err={err.strip()!r}",
        )
        check(
            "2) archive — 브랜치를 그 workspace 의 git 에서 얻는다",
            payload.get("current_branch") == "feature/probe",
            f"current_branch={payload.get('current_branch')!r}",
        )

    # 3) profile 은 있는데 메모리가 없다 — 조용한 폴백이 아니라 근거를 밝힌 exit 2.
    with tempfile.TemporaryDirectory() as td:
        bare = Path(td) / "no-memory-ws"
        (bare / "docs").mkdir(parents=True)
        (bare / "docs" / "PROJECT_PROFILE.md").write_text("# P\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=str(bare), capture_output=True, text=True)
        rc, payload, err = _run_archiver(bare)
        check(
            "3) archive — active dir 부재는 path_source 를 담은 exit 2",
            rc == 2 and "active dir 부재" in err and "cwd_project_profile" in err,
            f"rc={rc} err={err.strip()!r}",
        )

    # 4) git 이 없으면 "그 브랜치가 아직 사는가" 의 답이 전부 '없음' 이 된다 —
    #    살아 있는 메모리까지 종료로 읽히므로 판정 자체를 거부해야 한다.
    with tempfile.TemporaryDirectory() as td:
        nogit = _make_workspace(Path(td) / "nogit-ws", branch=None, memory_branch="main")
        rc, payload, err = _run_archiver(nogit)
        check(
            "4) archive — git 아닌 트리에서는 판정을 거부한다",
            rc == 2 and "git 저장소가 아니다" in err,
            f"rc={rc} err={err.strip()!r}",
        )

    # --- release 파이프라인 (TASK-2026-08-28-main-012) -----------------------
    with tempfile.TemporaryDirectory() as td:
        installed = Path(td) / "site-packages"          # pyproject 없음 = 설치본
        checkout = Path(td) / "repo" / "workflow-source"  # pyproject 있음 = 체크아웃
        checkout.mkdir(parents=True)
        (checkout / "pyproject.toml").write_text("[project]\nname='workflow-kit'\n", encoding="utf-8")
        (checkout / "workflow_kit").mkdir()

        installed_mod = _load_release_lib(installed, "_probe_release_lib_installed")
        raised: Exception | None = None
        try:
            installed_mod._require_source_checkout()
        except Exception as exc:  # noqa: BLE001 — 예외의 *모양* 을 재는 자리다
            raised = exc
        message = str(raised) if raised else ""
        check(
            "5) release — 설치본 레이아웃은 두 경로를 명시하고 거부",
            raised is not None
            and type(raised).__name__ == "SourceCheckoutRequired"
            and str(installed) in message
            and "체크아웃" in message,
            f"raised={type(raised).__name__ if raised else None} message={message!r}",
        )

        checkout_mod = _load_release_lib(checkout.parent / "workflow-source-copy",
                                         "_probe_release_lib_checkout")
        # 사본의 부모에 pyproject 를 두어 '체크아웃' 레이아웃을 만든다.
        (checkout.parent / "workflow-source-copy" / "pyproject.toml").write_text(
            "[project]\nname='workflow-kit'\n", encoding="utf-8")
        ok_no_raise = True
        try:
            checkout_mod._require_source_checkout()
        except Exception as exc:  # noqa: BLE001
            ok_no_raise = False
            message = f"{type(exc).__name__}: {exc}"
        check(
            "6) release — 체크아웃 레이아웃은 통과 (정상 경로를 막지 않는다)",
            ok_no_raise, message,
        )

        nested = checkout.parent / "sub" / "deeper"
        nested.mkdir(parents=True)
        found = installed_mod._discover_kit_checkout(nested)
        check(
            "7) release — cwd 에서 위로 거슬러 kit 체크아웃을 찾는다",
            found is not None and Path(found).resolve() == checkout.resolve(),
            f"found={found}",
        )

    # --- 8) 정적 — 새 사본이 생기는 것을 막는다 (TASK-2026-08-28-main-013) -----
    #
    # 앞의 7개는 이미 난 사본을 잡는다. 이 결함족은 그렇게 네 번 닫혔고 네 번 다
    # 다른 세션이었다. 여기서는 **`wk` 로 노출된 모든 진입점**을 훑어 무인자
    # 기본값이 모듈 위치에서 파생됐는지 정적으로 본다 — 대상은 cwd 에서
    # 해석해야 하고, 정본 진입점은 `paths.resolve_workspace_root` 다.
    sys.path.insert(0, str(SOURCE_ROOT))
    from workflow_kit.common.tool_dispatch import TOOL_MODULES  # noqa: E402

    offenders: dict[str, list[str]] = {}
    for name, module in sorted(TOOL_MODULES.items()):
        module_path = SOURCE_ROOT / Path(*module.split(".")).with_suffix(".py")
        if not module_path.is_file():
            continue
        flags = _module_location_defaults(module_path)
        if flags:
            offenders[name] = flags
    check(
        "8) 정적 — wk 진입점의 기본값이 모듈 위치 파생이 아니다",
        not offenders,
        f"모듈 위치 파생 기본값: {offenders} — cwd 에서 해석한다 "
        f"(paths.resolve_workspace_root)",
    )

    total = 8
    print()
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
