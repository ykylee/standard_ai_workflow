"""tools/* in-process dispatch — CLI 化 B안 (v1.1.2+)

A안 (v1.1.1, TASK-020) 은 `tools/*.py` 의 `main()` 을 `[project.scripts]` 로 박아
29개 binary 를 만들었다. B안은 그걸 **단일 진입점 `wk`** 로 묶는다.

정공법은 이미 저장소에 있었다 — `workflow_kit_cli` 의 `score-wiki-trend` (v0.7.56+)
/ `consumer-metrics` (v0.7.59+) wrapper 가 쓰던 *sys.argv 치환 + SystemExit → rc*
패턴을 29개 전체로 일반화한 것이 본 모듈이다. 새 dispatcher 를 만들지 않았다:
`workflow_kit_cli.COMMANDS` 하나가 계속 정본이고, 본 모듈은 거기에 tools 를
*늦게(lazy)* 실어 주기만 한다.

두 가지 `main()` 시그니처를 모두 받는다 (29개 중 13 : 16 으로 갈려 있다):
    - ``main(argv: list[str] | None = None) -> int``  — argv 를 그대로 넘긴다
    - ``main() -> int``                               — `sys.argv` 를 치환해 넘긴다

Public API:
    TOOL_MODULES: dict[str, str]        — command name → module path (정본)
    ALREADY_REGISTERED: frozenset[str]  — dispatcher 가 먼저 들고 있던 이름
    tool_command_names() -> list[str]
    run_tool(name, argv) -> int
    make_tool_runner(name) -> Callable[[list[str]], int]
"""

from __future__ import annotations

import importlib
import importlib.util  # `importlib` 만으로는 `.util` 이 안 붙는다 (submodule)
import inspect
import sys
from pathlib import Path
from typing import Callable, Final, cast


#: command name → `tools.<module>` 경로. **이 dict 가 정본이다.**
#:
#: `pyproject.toml` 의 `[project.scripts]` 와 이름이 갈라지면
#: `tests/check_wk_dispatcher.py` 가 red 를 낸다 — A안(entry point)과 B안(dispatcher)
#: 이 *같은 29개* 를 가리킨다는 것이 두 표면의 유일한 약속이라, 한쪽만 늘어나는
#: 사고를 검사로 막는다. `workflow-<name>` binary 와 `wk <name>` 은 같은 것이다.
#:
#: 제외한 2개는 CLI 가 아니다:
#:   - `mkdocs_git_dates`   — mkdocs plugin (on_page_markdown hook)
#:   - `release_pipeline_lib` — library (release_pipeline 이 쓰는 helper)
TOOL_MODULES: Final[dict[str, str]] = {
    "apply-robust-patch": "tools.apply_robust_patch",
    "archive-branch-memory": "tools.archive_branch_memory",
    "archive-stale-memory": "tools.archive_stale_memory",
    "audit-root-anchors": "tools.audit_root_anchors",
    "check-branch-protection": "tools.check_branch_protection",
    "check-packaging": "tools.check_packaging",
    "check-quickstart-stale-links": "tools.check_quickstart_stale_links",
    "claim-workspace": "tools.claim_workspace",
    "consumer-metrics": "tools.consumer_metrics",
    "create-environment-record-stub": "tools.create_environment_record_stub",
    "detect-scope-drift": "tools.detect_scope_drift",
    "emit-wiki-l2-body": "tools.emit_wiki_l2_body",
    "fill-reverse-engineering-artifacts": "tools.fill_reverse_engineering_artifacts",
    "fix-readme-for-release": "tools.fix_readme_for_release",
    "host-pull-registry": "tools.host_pull_registry",
    "host-serve-registry": "tools.host_serve_registry",
    "install-pre-push-hook": "tools.install_pre_push_hook",
    "migrate-active-to-appendonly": "tools.migrate_active_to_appendonly",
    "migrate-legacy-l2": "tools.migrate_legacy_l2",
    "migrate-memory-to-branch-scoped": "tools.migrate_memory_to_branch_scoped",
    "refresh-wiki-memory": "tools.refresh_wiki_memory",
    "release-pipeline": "tools.release_pipeline",
    "release-v0-13-0": "tools.release_v0_13_0",
    "rotate-workflow-logs": "tools.rotate_workflow_logs",
    "score-wiki-maintainability": "tools.score_wiki_maintainability",
    "score-wiki-trend": "tools.score_wiki_trend",
    "seed-workspace-memory": "tools.seed_workspace_memory",
    "suggest-memory-entries": "tools.suggest_memory_entries",
    "survey-remote-workspaces": "tools.survey_remote_workspaces",
    "sync-release-hash": "tools.sync_release_hash",
    "wiki-emit": "tools.wiki_emit",
    "workspace-registry": "tools.workspace_registry",
}


#: `workflow_kit_cli.COMMANDS` 가 *본 모듈보다 먼저* 들고 있던 이름.
#:
#: 둘 다 결국 같은 `tools.*` 모듈을 in-process 로 부르므로 동작은 같다. 그래도
#: 기존 wrapper 를 남긴다 — 그쪽에는 docstring 에 arg surface 가 적혀 있고
#: `--command=score-wiki-trend` 호출 경로가 v0.7.56 부터 약속돼 있다. 등록 시
#: 본 모듈이 그걸 *덮어쓰지 않는다*.
ALREADY_REGISTERED: Final[frozenset[str]] = frozenset({
    "consumer-metrics",
    "score-wiki-trend",
})


def tool_command_names() -> list[str]:
    """dispatcher 에 실을 tool command 이름 (정렬)."""
    return sorted(TOOL_MODULES)


def _ensure_tools_importable() -> None:
    """`workflow-source/` 를 `sys.path` 에 올려 `import tools.*` 가 되게 한다.

    v0.7.56 의 발견: `tools/` 에 `__init__.py` 가 없어 `import tools.x` 가 실패했고,
    그래서 예전 wrapper 는 subprocess 로 우회했다. 지금은 package 이므로 경로만
    맞으면 in-process 로 붙는다. 설치본(`pip install -e .`)에서는 이미 import 가
    되므로 이 함수는 아무 일도 하지 않는다.
    """
    if importlib.util.find_spec("tools") is not None:
        return
    # workflow_kit/common/tool_dispatch.py → workflow_kit/common → workflow_kit → workflow-source
    workflow_source_dir = Path(__file__).resolve().parent.parent.parent
    if str(workflow_source_dir) not in sys.path:
        sys.path.insert(0, str(workflow_source_dir))


def _accepts_argv(fn: Callable[..., int]) -> bool:
    """`main` 이 argv 를 받는지 본다.

    29개가 `main(argv=None)` 13 : `main()` 16 으로 갈려 있다. 전부 한 시그니처로
    통일하는 편이 깔끔하지만, 그건 29개 파일을 건드리는 변경이고 각 tool 의
    `__main__` 블록까지 따라 바뀌어야 한다. 여기서 *읽어서 맞추는* 쪽이 변경면이
    훨씬 작다 — 판단 근거는 TASK-021 기록에 있다.
    """
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):  # builtin / C-extension — 알 수 없으면 안 넘긴다
        return False
    return len(sig.parameters) > 0


def run_tool(name: str, argv: list[str]) -> int:
    """`tools.<module>.main()` 을 in-process 로 실행하고 exit code 를 돌려준다.

    Args:
        name: `TOOL_MODULES` 의 key (예: ``"survey-remote-workspaces"``).
        argv: tool 에 그대로 전달할 인자 (`wk <name>` 뒤의 나머지).

    Returns:
        int — tool 의 exit code. 알 수 없는 name 이면 2, 예외면 2.
    """
    module_path = TOOL_MODULES.get(name)
    if module_path is None:
        print(f"ERROR: unknown tool command: {name}", file=sys.stderr)
        return 2

    old_argv = sys.argv
    try:
        _ensure_tools_importable()
        mod = importlib.import_module(module_path)
        main_fn = cast("Callable[..., int]", mod.main)
        # argv 를 안 받는 main() 은 argparse 로 sys.argv 를 직접 읽는다. prog 이름은
        # module 의 basename 으로 맞춰 준다 — 안 그러면 --help 가 `wk` 를 못 알아본다.
        sys.argv = [module_path.rsplit(".", 1)[-1], *argv]
        if _accepts_argv(main_fn):
            return int(main_fn(argv))
        return int(main_fn())
    except SystemExit as e:
        # argparse 의 --help / 인자 오류는 SystemExit 으로 나온다. dispatcher 가
        # 통째로 죽으면 안 되므로 rc 로 되돌린다 (기존 wrapper 와 동일 정공법).
        return e.code if isinstance(e.code, int) else 2
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    finally:
        sys.argv = old_argv


def make_tool_runner(name: str) -> Callable[[list[str]], int]:
    """`COMMANDS` 에 실을 클로저를 만든다 — import 는 *호출 시점* 에 일어난다.

    등록 시점에 29개를 전부 import 하면 `wk --help` 한 번이 모든 tool 의
    import 비용을 문다. lazy 로 둬야 dispatcher 기동이 지금 속도를 유지한다.
    """
    def _run(argv: list[str]) -> int:
        return run_tool(name, argv)

    _run.__name__ = f"cmd_tool_{name.replace('-', '_')}"
    _run.__doc__ = f"tools/{TOOL_MODULES[name].rsplit('.', 1)[-1]}.py (CLI 化 B안, v1.1.2+)"
    return _run
