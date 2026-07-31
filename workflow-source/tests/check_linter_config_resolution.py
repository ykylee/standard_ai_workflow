"""workflow-linter 의 **기준 경로**와 설정 출처 계약 (v1.0.3).

## 왜 필요한가

`run_workflow_linter.py` 는 기준을 이렇게 잡고 있었다.

    project_root = project_profile_path.parent.parent.parent

`<root>/docs/PROJECT_PROFILE.md` 에서 이 값은 root 가 아니라 **root 의 한 단계 위**다
(docs → root → 그 위). 그 값이 두 곳으로 갔다.

1. `load_config(project_root)` — 없는 pyproject 를 물어 **언제나 기본값**. 즉
   `[tool.workflow-doctor]` 의 `excluded_paths` 는 한 번도 적용된 적이 없다.
2. `--maturity` 의 matrix/roadmap 경로 — 늘 빗나가 `status: skipped`. 그런데 runner 는
   `issues_found` 만 반영해서, 실행되지 못한 검사가 **`status: ok / total_issues: 0`**
   으로 보고됐다 (v0.11.17 backlog 에 "정합 검증 통과" 로 기록돼 있다).

둘 다 조용했다. `load_config` 는 어떤 경우에도 실패하지 않도록 설계돼 있어서, "설정이
적용됨" 과 "기본값으로 떨어짐" 이 산출물에서 구별되지 않았기 때문이다.

## 계약

1. `project_root` 는 workspace root 다 (`docs/PROJECT_PROFILE.md` 의 상위).
2. workspace root 의 `[tool.workflow-doctor]` 가 **실제로 린터까지 도달**한다.
3. 설정을 어디에 물었고 얻었는지가 `source_context` 에 남는다
   (`config_consulted_path` / `config_source` / `config_default_reason`).
4. `--config-path` 는 파일이든 디렉터리든 명시가 우선한다.
5. `--maturity` 는 실재하는 matrix 를 고르고, **실행되지 못하면 통과로 보고하지 않는다**.

Cross-ref: releases/Beta-v1.0.0.md §2.47.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SOURCE_ROOT.parent
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.metadata import (  # noqa: E402
    CONFIG_REASON_FILE_MISSING,
    CONFIG_REASON_SECTION_MISSING,
    CONFIG_SOURCE_DEFAULT,
    CONFIG_SOURCE_PYPROJECT,
)

RUNNER = SOURCE_ROOT / "skills" / "workflow-linter" / "scripts" / "run_workflow_linter.py"
BRANCH = "linter-config-smoke"

PROFILE = """# Project Profile

- 문서 목적: 검사용 fixture.
- 최종 수정일: 2026-07-31

## 1. 기본 정보

- 프로젝트 이름: Linter Config Fixture
- 문서 홈: docs/index.md
"""

HANDOFF = """# Session Handoff

- 최종 수정일: 2026-07-31

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
-

## 4. 최근 완료 작업

- 최근 완료 작업 목록:
-
"""

BACKLOG = """# Backlog Index — 2026-07-31

## Tasks

"""

MATRIX = {
    "skills": {
        "ghost-skill": {"stage": "stable", "test_path": "tests/check_does_not_exist.py"},
    },
    "milestones": {},
}


def _workspace(td: str, *, pyproject: str | None = None) -> Path:
    ws = Path(td)
    (ws / "docs").mkdir(parents=True)
    (ws / "docs" / "PROJECT_PROFILE.md").write_text(PROFILE, encoding="utf-8")
    base = ws / "ai-workflow" / "memory" / "active" / BRANCH
    (base / "backlog" / "tasks").mkdir(parents=True)
    (base / "sessions").mkdir(parents=True)
    (base / "session_handoff.md").write_text(HANDOFF, encoding="utf-8")
    (base / "backlog" / "2026-07-31.md").write_text(BACKLOG, encoding="utf-8")
    (base / "state.json").write_text(
        json.dumps({"source_of_truth": {}, "session": {"in_progress_items": []}}),
        encoding="utf-8",
    )
    if pyproject is not None:
        (ws / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return ws


def _run(ws: Path, *extra: str) -> dict:
    base = ws / "ai-workflow" / "memory" / "active" / BRANCH
    proc = subprocess.run(
        [
            sys.executable, str(RUNNER),
            "--project-profile-path", str(ws / "docs" / "PROJECT_PROFILE.md"),
            "--state-json-path", str(base / "state.json"),
            "--session-handoff-path", str(base / "session_handoff.md"),
            "--latest-backlog-path", str(base / "backlog" / "2026-07-31.md"),
            *extra,
        ],
        capture_output=True, text=True, timeout=120,
        env={"PYTHONPATH": str(SOURCE_ROOT), "PATH": "/usr/bin:/bin"},
    )
    assert proc.stdout.strip(), f"runner 가 아무것도 출력하지 않았다.\nstderr: {proc.stderr[-800:]}"
    return json.loads(proc.stdout)


# --- 1. 기준 경로 ---------------------------------------------------------


def test_project_root_is_workspace_root() -> None:
    """`project_root` 는 저장소 루트다 — 그 위가 아니다 (원래 결함)."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        result = _run(ws)
        actual = result["source_context"].get("project_root")
        assert actual is not None, f"project_root 가 산출물에 없다: {result['source_context']}"
        assert Path(actual).resolve() == ws.resolve(), (
            f"project_root={actual} 가 workspace root({ws}) 가 아니다."
        )


# --- 2. 설정이 실제로 도달하는가 -----------------------------------------


def test_declared_excluded_paths_reach_the_linter() -> None:
    """workspace root 에 선언한 `excluded_paths` 가 깨진 링크 판정에 실제로 쓰인다.

    "load_config 를 부르는 줄이 있다" 는 검사로는 이걸 못 잡는다 — 실제로 그 줄은
    있었고, 다만 없는 파일을 묻고 있었다.
    """
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(
            td,
            pyproject='[tool.workflow-doctor]\nexcluded_paths = ["skipped-dir/*"]\n',
        )
        base = ws / "ai-workflow" / "memory" / "active" / BRANCH
        # 둘 다 실재하지 않는 대상을 가리키는 링크. 하나만 제외 대상이다.
        (base / "session_handoff.md").write_text(
            HANDOFF
            + "\n- [제외 대상](../../../../skipped-dir/ghost.md)\n"
            + "- [제외 아님](../../../../watched-dir/ghost.md)\n",
            encoding="utf-8",
        )

        result = _run(ws)
        broken = [i["description"] for i in result["issues"] if i["type"] == "broken_link"]
        assert any("watched-dir" in d for d in broken), (
            f"제외 대상이 아닌 깨진 링크가 보고되지 않았다: {broken}"
        )
        assert not any("skipped-dir" in d for d in broken), (
            f"선언한 excluded_paths 가 적용되지 않았다 (설정이 린터까지 못 왔다): {broken}"
        )
        assert result["source_context"]["config_source"] == CONFIG_SOURCE_PYPROJECT, (
            result["source_context"]
        )


# --- 3. 출처가 산출물에 남는가 -------------------------------------------


def test_missing_config_is_reported_not_silent() -> None:
    """pyproject 자체가 없으면 `default` + `file_missing` 으로 드러난다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        ctx = _run(ws)["source_context"]
        assert ctx["config_source"] == CONFIG_SOURCE_DEFAULT, ctx
        assert ctx["config_default_reason"] == CONFIG_REASON_FILE_MISSING, ctx
        assert ctx["config_consulted_path"].endswith("pyproject.toml"), ctx


def test_section_missing_is_distinct_from_file_missing() -> None:
    """pyproject 는 있는데 section 이 없는 것은 **다른 사실**이다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td, pyproject='[project]\nname = "x"\n')
        ctx = _run(ws)["source_context"]
        assert ctx["config_source"] == CONFIG_SOURCE_DEFAULT, ctx
        assert ctx["config_default_reason"] == CONFIG_REASON_SECTION_MISSING, ctx


# --- 4. 명시가 우선 -------------------------------------------------------


def test_explicit_config_path_wins() -> None:
    """`--config-path` 는 디렉터리든 파일이든 workspace root 보다 우선한다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td, pyproject='[project]\nname = "x"\n')  # section 없음
        other = ws / "kit"
        other.mkdir()
        (other / "pyproject.toml").write_text(
            '[tool.workflow-doctor]\nexcluded_paths = ["skipped-dir/*"]\n', encoding="utf-8"
        )

        for arg in (str(other), str(other / "pyproject.toml")):
            ctx = _run(ws, "--config-path", arg)["source_context"]
            assert ctx["config_source"] == CONFIG_SOURCE_PYPROJECT, (arg, ctx)
            assert Path(ctx["config_path"]).resolve() == (other / "pyproject.toml").resolve(), ctx


# --- 5. --maturity 는 못 돌면 통과라고 하지 않는다 ------------------------


def test_maturity_runs_against_the_real_matrix() -> None:
    """consumer layout 의 matrix 를 찾아 **실제로 판정**한다.

    `test_path` 의 기준은 **matrix 를 담은 kit root**(= `core/` 의 부모)다. 저장소
    루트를 기준으로 삼으면 consumer 의 앱 테스트를 가리키게 된다 — 아래 decoy 가
    정확히 그 상황이라, 기준이 어긋나면 "파일이 있다" 로 보여 결함을 놓친다.
    """
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        core = ws / "ai-workflow" / "core"
        core.mkdir(parents=True)
        (core / "maturity_matrix.json").write_text(json.dumps(MATRIX), encoding="utf-8")
        # decoy: 저장소 루트 기준으로는 존재하는 동명 파일 (kit root 기준으로는 없다).
        (ws / "tests").mkdir()
        (ws / "tests" / "check_does_not_exist.py").write_text("# decoy\n", encoding="utf-8")

        result = _run(ws, "--maturity")
        ctx = result["source_context"]
        assert ctx["maturity_status"] == "issues_found", ctx
        assert Path(ctx["maturity_matrix_path"]).resolve() == (core / "maturity_matrix.json").resolve(), ctx
        codes = [i["code"] for i in result["issues"]]
        assert "missing_test_file" in codes, (
            f"matrix 가 선언한 없는 test_path 를 못 잡았다 (기준 경로가 어긋났을 수 있다): {codes}"
        )


def test_maturity_falls_back_to_kit_layout() -> None:
    """consumer layout 이 없으면 kit layout(`workflow-source/core/`)을 고른다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        core = ws / "workflow-source" / "core"
        core.mkdir(parents=True)
        (core / "maturity_matrix.json").write_text(json.dumps(MATRIX), encoding="utf-8")

        ctx = _run(ws, "--maturity")["source_context"]
        assert Path(ctx["maturity_matrix_path"]).resolve() == (core / "maturity_matrix.json").resolve(), ctx
        assert ctx["maturity_status"] == "issues_found", ctx


def test_maturity_without_matrix_is_not_reported_as_pass() -> None:
    """matrix 가 없으면 `ok` 가 아니라 **실행되지 못했다**고 적는다 (원래 결함)."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        result = _run(ws, "--maturity")
        codes = [i["code"] for i in result["issues"]]
        assert "maturity_check_not_run" in codes, (
            f"matrix 부재인데 통과로 보고됐다: status={result['status']} issues={codes}"
        )
        assert result["source_context"]["maturity_status"] == "skipped", result["source_context"]


def test_explicit_maturity_path_wins() -> None:
    """`--maturity-path` 로 kit layout 의 matrix 를 직접 지정할 수 있다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        core = ws / "vendor" / "core"
        core.mkdir(parents=True)
        matrix = core / "maturity_matrix.json"
        matrix.write_text(json.dumps(MATRIX), encoding="utf-8")

        ctx = _run(ws, "--maturity", "--maturity-path", str(matrix))["source_context"]
        assert Path(ctx["maturity_matrix_path"]).resolve() == matrix.resolve(), ctx
        assert ctx["maturity_status"] == "issues_found", ctx


def main() -> int:
    test_funcs = [
        test_project_root_is_workspace_root,
        test_declared_excluded_paths_reach_the_linter,
        test_missing_config_is_reported_not_silent,
        test_section_missing_is_distinct_from_file_missing,
        test_explicit_config_path_wins,
        test_maturity_runs_against_the_real_matrix,
        test_maturity_falls_back_to_kit_layout,
        test_maturity_without_matrix_is_not_reported_as_pass,
        test_explicit_maturity_path_wins,
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

    total = len(test_funcs)
    print(f"\n{total - len(failures)}/{total} PASS")
    if failures:
        for name, err in failures:
            print(f"  - {name}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
