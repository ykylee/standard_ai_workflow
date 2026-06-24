"""v0.10.3 wiki file deletion cascade cleanup verify (R-A follow-up cycle 2).

Acceptance criteria (workflow_kit/common/wiki_cascade.py):
1. file_to_stem() — kebab-case + lower 변환 (3-method matching 의 SSOT)
2. find_cascade_targets() — 3-method matching 으로 cascade-delete 대상 wiki page 식별
   - (1) basename + .md
   - (2) stem 변환
   - (3) project-relative stem 변환
3. emit_cascade_plan() — 여러 deleted_paths 의 JSON plan emit
4. apply_cascade() — destructive subcommand 정공법 (apply=False default dry-run, --apply 명시 시 실제 delete)
5. render_cascade_plan_text() — human-readable text render (advisory)
6. cascade-delete CLI subcommand 등록 + 3-method 정합

모든 input file / wiki_root 은 임시 dir 에서 생성 (저장소 file layout 의존 ❌).
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import types
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_KIT_DIR = SOURCE_ROOT / "workflow_kit"

# workflow_kit namespace setup (mirrors check_purpose_concept_skill_context_v0_9_5.py)
_workflow_kit_pkg = types.ModuleType("workflow_kit")
_workflow_kit_pkg.__path__ = [str(WORKFLOW_KIT_DIR)]
sys.modules.setdefault("workflow_kit", _workflow_kit_pkg)

# workflow_kit.common sub-package setup
_workflow_kit_common_pkg = types.ModuleType("workflow_kit.common")
_workflow_kit_common_pkg.__path__ = [str(WORKFLOW_KIT_DIR / "common")]
sys.modules.setdefault("workflow_kit.common", _workflow_kit_common_pkg)


def _load_common(name: str, file_name: str):
    """common.* 모듈을 workflow_kit.common.* 로 등록 (relative import 지원)."""
    full_name = f"workflow_kit.common.{name}"
    spec = importlib.util.spec_from_file_location(
        full_name, str(WORKFLOW_KIT_DIR / "common" / file_name)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    setattr(_workflow_kit_common_pkg, name, mod)
    spec.loader.exec_module(mod)
    return mod


def _make_wiki_root(tmp_path: Path, project: str = "test-project") -> Path:
    """테스트용 wiki_root + 3 wiki page seed (3-method matching 의 3 case cover)."""
    wiki_root = tmp_path / "wiki" / "projects" / project / "sources"
    wiki_root.mkdir(parents=True, exist_ok=True)
    # Case 1: basename match — "AGENTS.md" → "AGENTS.md" stem
    (wiki_root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    # Case 2: stem match — "workflow-source/core/test.md" → "workflow-source-core-test" stem
    (wiki_root / "workflow-source-core-test.md").write_text("# Test\n", encoding="utf-8")
    # Case 3: project-relative match — "raw/projects/standard-ai-workflow/scripts/bootstrap.py" → "scripts-bootstrap" stem
    (wiki_root / "scripts-bootstrap.md").write_text("# Bootstrap\n", encoding="utf-8")
    return wiki_root


# ---------------------------------------------------------------------------
# Acceptance #1: file_to_stem SSOT
# ---------------------------------------------------------------------------
def test_file_to_stem_v0_10_3() -> None:
    """Acceptance v0.10.3 #1: file_to_stem() — kebab-case + lower 변환 SSOT."""
    cascade = _load_common("wiki_cascade", "wiki_cascade.py")

    # 기본 케이스
    assert cascade.file_to_stem("AGENTS.md") == "agents"
    assert cascade.file_to_stem("opencode.json") == "opencode"
    # nested path — full path 가 stem 에 포함 (wiki page 가 *mirror* 라는 contract)
    assert cascade.file_to_stem("workflow-source/core/v0_9_0_deprecation_policy_spec.md") == "workflow-source-core-v0-9-0-deprecation-policy-spec"
    # path separator
    assert cascade.file_to_stem("scripts/bootstrap_lib/wiki.py") == "scripts-bootstrap-lib-wiki"
    # lowercase
    assert cascade.file_to_stem("MyFile.MD") == "myfile"
    # 중복 dash
    assert cascade.file_to_stem("a--b__c.md") == "a-b-c"


# ---------------------------------------------------------------------------
# Acceptance #2: find_cascade_targets — 3-method matching
# ---------------------------------------------------------------------------
def test_find_cascade_targets_3_methods_v0_10_3() -> None:
    """Acceptance v0.10.3 #2: 3-method matching 으로 cascade-delete 대상 식별.

    Case 1 (basename): "AGENTS.md" → "AGENTS.md" 직접 매치
    Case 2 (stem): "workflow-source/core/test.md" → "workflow-source-core-test" stem
    Case 3 (project-relative): "raw/projects/standard-ai-workflow/scripts/bootstrap.py" + project="standard-ai-workflow" → "scripts-bootstrap"
    """
    cascade = _load_common("wiki_cascade", "wiki_cascade.py")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        wiki_root = _make_wiki_root(tmp_path, "standard-ai-workflow")

        # Case 1: basename match
        r1 = cascade.find_cascade_targets("AGENTS.md", wiki_root, project="standard-ai-workflow")
        assert len(r1.targets) == 1, f"basename match expected 1 target, got {len(r1.targets)}"
        assert r1.targets[0].path == wiki_root / "AGENTS.md"
        assert r1.targets[0].method == "basename"

        # Case 2: stem match
        r2 = cascade.find_cascade_targets(
            "workflow-source/core/test.md", wiki_root, project="standard-ai-workflow"
        )
        # basename "test.md" + stem "workflow-source-core-test" 둘 다 매치 → dedup 후 1 (stem 우선)
        # 1st try "test.md" → 없음, 2nd try "workflow-source-core-test" → 매치
        assert len(r2.targets) == 1, f"stem match expected 1 target, got {len(r2.targets)}"
        assert r2.targets[0].path == wiki_root / "workflow-source-core-test.md"
        assert "stem" in r2.targets[0].method

        # Case 3: project-relative match
        r3 = cascade.find_cascade_targets(
            "raw/projects/standard-ai-workflow/scripts/bootstrap.py",
            wiki_root,
            project="standard-ai-workflow",
        )
        # 1st try "bootstrap.py" → 없음, 2nd try "raw-projects-standard-ai-workflow-scripts-bootstrap" → 없음
        # 3rd try project="standard-ai-workflow" + prefix "raw/projects/standard-ai-workflow" → "scripts-bootstrap" 매치
        assert len(r3.targets) == 1, f"project-relative match expected 1 target, got {len(r3.targets)}"
        assert r3.targets[0].path == wiki_root / "scripts-bootstrap.md"
        assert "project-relative-stem" in r3.targets[0].method


# ---------------------------------------------------------------------------
# Acceptance #3: 3-method dedup + 부재 시 graceful
# ---------------------------------------------------------------------------
def test_cascade_graceful_missing_v0_10_3() -> None:
    """Acceptance v0.10.3 #3: 부재 시 graceful skip (cascade 대상 없음 + advisory warning)."""
    cascade = _load_common("wiki_cascade", "wiki_cascade.py")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        wiki_root = tmp_path / "wiki" / "empty-project" / "sources"
        wiki_root.mkdir(parents=True, exist_ok=True)

        # 부재 source file
        r = cascade.find_cascade_targets("non_existent_file.md", wiki_root, project="empty-project")
        assert len(r.targets) == 0
        assert any("cascade-delete 대상 없음" in w for w in r.warnings)

        # wiki_root 자체 부재
        r2 = cascade.find_cascade_targets("AGENTS.md", tmp_path / "non_existent_wiki", project="t")
        assert len(r2.targets) == 0
        assert any("wiki_root 부재" in w for w in r2.warnings)


# ---------------------------------------------------------------------------
# Acceptance #4: emit_cascade_plan — 다중 deleted_paths 의 JSON plan
# ---------------------------------------------------------------------------
def test_emit_cascade_plan_v0_10_3() -> None:
    """Acceptance v0.10.3 #4: emit_cascade_plan() — 여러 deleted_paths 의 plan emit."""
    cascade = _load_common("wiki_cascade", "wiki_cascade.py")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        wiki_root = _make_wiki_root(tmp_path, "test-project")

        plan = cascade.emit_cascade_plan(
            deleted_paths=["AGENTS.md", "workflow-source/core/test.md", "non_existent.md"],
            wiki_root=wiki_root,
            project="test-project",
        )
        assert plan["deleted_count"] == 3
        assert plan["total_targets"] == 2  # 2개 매치, 1개 부재
        assert len(plan["plans"]) == 3
        # plan[0] (AGENTS.md) — 1 target
        assert len(plan["plans"][0]["targets"]) == 1
        # plan[1] (test.md) — 1 target (stem match)
        assert len(plan["plans"][1]["targets"]) == 1
        # plan[2] (non_existent.md) — 0 target + warning
        assert len(plan["plans"][2]["targets"]) == 0
        assert any("cascade-delete 대상 없음" in w for w in plan["plans"][2]["warnings"])


# ---------------------------------------------------------------------------
# Acceptance #5: apply_cascade — destructive subcommand 정공법 (apply=False default dry-run)
# ---------------------------------------------------------------------------
def test_apply_cascade_destructive_pattern_v0_10_3() -> None:
    """Acceptance v0.10.3 #5: apply_cascade() — destructive subcommand 정공법 (apply=False default dry-run, --apply 명시 시 실제 delete)."""
    cascade = _load_common("wiki_cascade", "wiki_cascade.py")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        wiki_root = _make_wiki_root(tmp_path, "test-project")
        target = wiki_root / "AGENTS.md"
        assert target.exists()

        ct = cascade.CascadeTarget(path=target, method="basename")

        # dry-run (default)
        r1 = cascade.apply_cascade([ct], apply=False)
        assert r1["applied"] is False
        assert len(r1["executed"]) == 0
        assert len(r1["skipped"]) == 1
        assert r1["skipped"][0]["path"] == str(target)
        # file NOT deleted
        assert target.exists()

        # apply=True
        r2 = cascade.apply_cascade([ct], apply=True)
        assert r2["applied"] is True
        assert len(r2["executed"]) == 1
        assert r2["executed"][0]["path"] == str(target)
        # file deleted
        assert not target.exists()

        # 재apply → 부재 (cascade 대상 없음, 0 target)
        r3 = cascade.find_cascade_targets("AGENTS.md", wiki_root, project="test-project")
        assert len(r3.targets) == 0


# ---------------------------------------------------------------------------
# Acceptance #6: render_cascade_plan_text — human-readable advisory
# ---------------------------------------------------------------------------
def test_render_cascade_plan_text_v0_10_3() -> None:
    """Acceptance v0.10.3 #6: render_cascade_plan_text() — advisory text render."""
    cascade = _load_common("wiki_cascade", "wiki_cascade.py")

    plan = {
        "deleted_count": 2,
        "total_targets": 1,
        "plans": [
            {
                "deleted_path": "AGENTS.md",
                "targets": [{"path": "/tmp/wiki/AGENTS.md", "method": "basename"}],
                "warnings": [],
            },
            {
                "deleted_path": "non_existent.md",
                "targets": [],
                "warnings": ["3-method matching 결과 cascade-delete 대상 없음: non_existent.md"],
            },
        ],
        "warnings": [],
    }
    text = cascade.render_cascade_plan_text(plan)
    assert "Wiki Cascade-Delete Plan (advisory)" in text
    assert "deleted_count: 2" in text
    assert "total_targets: 1" in text
    assert "AGENTS.md" in text
    assert "[basename]" in text
    assert "non_existent.md" in text
    assert "(cascade 대상 없음)" in text
    assert "3-method matching 결과 cascade-delete 대상 없음" in text


# ---------------------------------------------------------------------------
# Acceptance #7: cascade-delete CLI subcommand 등록
# ---------------------------------------------------------------------------
def test_cascade_delete_cli_registered_v0_10_3() -> None:
    """Acceptance v0.10.3 #7: cascade-delete CLI subcommand 등록 + dry-run subprocess."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        wiki_root = _make_wiki_root(tmp_path, "test-project")
        # 실제 CLI 호출 (subprocess) — dry-run
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"import sys; sys.path.insert(0, '{SOURCE_ROOT}'); "
                f"from workflow_kit.workflow_kit_cli import run_workflow_kit_cli; "
                f"sys.exit(run_workflow_kit_cli(["
                f"'--command=cascade-delete', "
                f"'--deleted-paths=AGENTS.md', "
                f"'--deleted-paths=non_existent.md', "
                f"'--wiki-root={wiki_root}', "
                f"'--project=test-project'"
                f"]))",
            ],
            capture_output=True,
            text=True,
            cwd=str(SOURCE_ROOT),
        )
        assert result.returncode == 0, f"CLI fail: {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        assert "Wiki Cascade-Delete Plan (advisory)" in result.stdout
        assert "AGENTS.md" in result.stdout
        assert "non_existent.md" in result.stdout
        assert "[dry-run]" in result.stdout
        # dry-run 이므로 file 보존
        assert (wiki_root / "AGENTS.md").exists(), "dry-run 인데 file 이 삭제됨"


def main() -> int:
    test_funcs = [
        test_file_to_stem_v0_10_3,
        test_find_cascade_targets_3_methods_v0_10_3,
        test_cascade_graceful_missing_v0_10_3,
        test_emit_cascade_plan_v0_10_3,
        test_apply_cascade_destructive_pattern_v0_10_3,
        test_render_cascade_plan_text_v0_10_3,
        test_cascade_delete_cli_registered_v0_10_3,
    ]
    failed: list[str] = []
    for fn in test_funcs:
        name = fn.__name__
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed.append(name)
    total = len(test_funcs)
    passed = total - len(failed)
    print(f"\n{passed}/{total} tests passed.")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
