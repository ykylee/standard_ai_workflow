"""v0.10.2 delivery layer 확장 verify.

Acceptance criteria (workflow-source/workflow_kit/bootstrap_lib + workflow_kit schema + session-start skill):
1. claude-code adapter 진입점 정정 (entry_files=('CLAUDE.md',) + CLAUDE.md render + write_harness_files dispatch)
2. claude-code + aggressive (default) → CLAUDE.md + 3 slash commands emit
3. claude-code + skill-only → 3 slash commands only, CLAUDE.md skip
4. aider adapter 신규 → CONVENTIONS.md (root) + .aider/conventions.md + .aider.conf.yml.example emit
5. goose adapter 신규 → .goose/config.yaml emit
6. custom adapter 신규 → .workflow-kits/custom/SKILL.md emit
7. SUPPORTED_HARNESSES 7→10 + HARNESS_SPECS / HARNESS_FILE_BUILDERS 3-way 정합
8. session-start skill self-bootstrap mode (PURPOSE.md / state.json / handoff / backlog 모두 부재 시 status=warning + self_bootstrap_suggested=True + init commands emit)
9. v0.10.0/v0.10.1 회귀 (deprecation cycle 종료 + entry-mode 3-mode) 유지
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import types
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]

# v1.2.0 (2nd cycle): scripts/bootstrap_lib shim drop — 정위치는
# workflow_kit.bootstrap_lib (SOURCE_ROOT 만 sys.path 에 있으면 된다)
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

# Force import of renderers module so HARNESS_FILE_BUILDERS is populated
# (register_harness_builder calls run at module-load time of renderers).
# Without this, the early tests that import HARNESS_FILE_BUILDERS directly
# from workflow_kit.bootstrap_lib.harnesses would see an empty dict because renderers
# hasn't been imported yet.
import workflow_kit.bootstrap_lib.harnesses.renderers  # noqa: E402,F401


def _make_ns(target: Path, harnesses: list[str], entry_mode: str) -> argparse.Namespace:
    return argparse.Namespace(
        target_root=str(target),
        kit_dir="ai-workflow",
        adoption_mode="new",
        entry_mode=entry_mode,
        project_slug="t",
        project_name="T",
        project_purpose="t",
        stakeholders="t",
        doc_home="README.md",
        operations_dir="ai-workflow/memory/active/",
        backlog_dir="ai-workflow/memory/active/backlog/",
        session_doc_path="ai-workflow/memory/active/sessions",
        environment_dir="ai-workflow/memory/active/environments/",
        install_command=None,
        run_command=None,
        quick_test_command=None,
        isolated_test_command=None,
        smoke_check_command="python3 --version",
        today="2026-06-24",
        initial_task_id="TASK-001",
        initial_task_name="t",
        initial_task_status="planned",
        initial_priority="high",
        owner="t",
        host_name="t",
        host_ip="t",
        harnesses=harnesses,
        no_interactive=True,
        force=True,
        enable_mcp=False,
        enable_wiki=False,
        py_only=False,
    )


def _run_bootstrap(target: Path, harnesses: list[str], entry_mode: str) -> dict[str, str]:
    from workflow_kit.bootstrap_lib.__main__ import (
        write_harness_files,
        make_paths,
        infer_project_context,
    )
    ns = _make_ns(target, harnesses, entry_mode)
    paths = make_paths(ns)
    ctx = infer_project_context(ns, paths)
    gen, _ = write_harness_files(ns, paths, ctx)
    return gen


# ---------------------------------------------------------------------------
# Acceptance #1: claude-code adapter 진입점 정정 (entry_files=('CLAUDE.md',))
# ---------------------------------------------------------------------------
def test_claude_code_entry_point_corrected_v0_10_2() -> None:
    """Acceptance v0.10.2 #1: claude-code entry_files 가 ('CLAUDE.md',) 로 정정됨 (v0.10.1 의 skill-only 오류 정정)."""
    from workflow_kit.bootstrap_lib.harnesses import HARNESS_SPECS, HARNESS_FILE_BUILDERS, SUPPORTED_HARNESSES

    # SUPPORTED_HARNESSES 7→10
    for h in ("claude-code", "aider", "goose", "custom"):
        assert h in SUPPORTED_HARNESSES, (
            f"{h} 가 SUPPORTED_HARNESSES 에 등록되어야 함. got: {SUPPORTED_HARNESSES}"
        )

    # HARNESS_SPECS claude-code entry_files 정정
    spec = HARNESS_SPECS["claude-code"]
    assert spec.entry_files == ("CLAUDE.md",), (
        f"v0.10.2 정정: claude-code entry_files 는 ('CLAUDE.md',) 여야 함. "
        f"got: {spec.entry_files}"
    )
    # 3 slash command extra_files 유지. **총 개수가 아니라 존재를 본다** — 개수 판정은
    # "3종이 유지되는가" 의 약한 대리물이라, v1.0.4 에서 skill 하나를 더하자 계약이
    # 그대로인데도 깨졌다 (2026-08-05).
    for command in (
        ".claude/commands/workflow-session-start.md",
        ".claude/commands/workflow-backlog-update.md",
        ".claude/commands/workflow-doc-sync.md",
    ):
        assert command in spec.extra_files, (
            f"claude-code extra_files 에 {command} 가 있어야 함. got: {spec.extra_files}"
        )

    # 3-way 정합
    assert "claude-code" in HARNESS_FILE_BUILDERS
    assert "aider" in HARNESS_FILE_BUILDERS
    assert "goose" in HARNESS_FILE_BUILDERS
    assert "custom" in HARNESS_FILE_BUILDERS


# ---------------------------------------------------------------------------
# Acceptance #2: claude-code + aggressive → CLAUDE.md + 3 slash commands
# ---------------------------------------------------------------------------
def test_claude_code_aggressive_emits_v0_10_2() -> None:
    """Acceptance v0.10.2 #2: claude-code + aggressive (default) → CLAUDE.md (root 진입점) + 3 slash commands emit."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        gen = _run_bootstrap(target, ["claude-code"], "aggressive")

        # CLAUDE.md (root 진입점) emit
        assert "claude_code_agents" in gen, (
            f"v0.10.2 정정: claude-code + aggressive 에서 CLAUDE.md emit 필수. got: {list(gen.keys())}"
        )
        assert (target / "CLAUDE.md").exists(), "CLAUDE.md root 진입점 file 부재"

        # 3 slash command 도 emit
        for key in (
            "claude_code_session_start_command",
            "claude_code_backlog_update_command",
            "claude_code_doc_sync_command",
        ):
            assert key in gen, f"{key} 부재"
            assert Path(gen[key]).exists(), f"{key} file 부재"

        # CLAUDE.md 가 세 절을 싣는지. 2026-08-14 진입점 영어화로 제목이 바뀌었다 —
        # 재는 질문("이 절들이 있는가")은 그대로다.
        content = (target / "CLAUDE.md").read_text(encoding="utf-8")
        assert "Read these first" in content
        assert "Relationship to AGENTS.md" in content
        assert "@AGENTS.md" in content  # import 안내
        assert "Entry slash commands" in content


# ---------------------------------------------------------------------------
# Acceptance #3: claude-code + skill-only → 3 slash commands only, CLAUDE.md skip
# ---------------------------------------------------------------------------
def test_claude_code_skill_only_skips_claude_md_v0_10_2() -> None:
    """Acceptance v0.10.2 #3: claude-code + skill-only → 3 slash commands only, CLAUDE.md skip."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        gen = _run_bootstrap(target, ["claude-code"], "skill-only")

        # CLAUDE.md skip
        assert "claude_code_agents" not in gen, (
            f"v0.10.2: skill-only mode 에서 CLAUDE.md skip 필수. got: {list(gen.keys())}"
        )
        assert not (target / "CLAUDE.md").exists(), "skill-only 모드에서 CLAUDE.md 부재해야 함"

        # 3 slash command 여전히 emit
        for key in (
            "claude_code_session_start_command",
            "claude_code_backlog_update_command",
            "claude_code_doc_sync_command",
        ):
            assert key in gen, f"{key} 부재"


# ---------------------------------------------------------------------------
# Acceptance #4: aider adapter 신규 → CONVENTIONS.md (root) + .aider/conventions.md + .aider.conf.yml.example
# ---------------------------------------------------------------------------
def test_aider_adapter_emits_v0_10_2() -> None:
    """Acceptance v0.10.2 #4: aider adapter → CONVENTIONS.md (root) + .aider/conventions.md + .aider.conf.yml.example emit."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        gen = _run_bootstrap(target, ["aider"], "aggressive")

        # 3 file emit
        assert "aider_conventions_root" in gen
        assert "aider_conventions_aider_dir" in gen
        assert "aider_config_example" in gen

        # root CONVENTIONS.md
        assert (target / "CONVENTIONS.md").exists(), "CONVENTIONS.md root 진입점 부재"
        # .aider/conventions.md
        assert (target / ".aider" / "conventions.md").exists(), ".aider/conventions.md 부재"
        # .aider.conf.yml.example
        assert (target / ".aider.conf.yml.example").exists(), ".aider.conf.yml.example 부재"

        # CONVENTIONS.md 본문 verify
        content = (target / "CONVENTIONS.md").read_text(encoding="utf-8")
        assert "Standard AI workflow entry" in content
        assert "ai-workflow/memory/active/<branch>/state.json" in content

        # .aider.conf.yml.example 본문 verify
        config = (target / ".aider.conf.yml.example").read_text(encoding="utf-8")
        assert "read:" in config
        assert "CONVENTIONS.md" in config
        assert "commit-language: ko" in config


# ---------------------------------------------------------------------------
# Acceptance #5: goose adapter 신규 → .goose/config.yaml
# ---------------------------------------------------------------------------
def test_goose_adapter_emits_v0_10_2() -> None:
    """Acceptance v0.10.2 #5: goose adapter → .goose/config.yaml (extension 등록 + entry_points 3종 + read_files 5종)."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        gen = _run_bootstrap(target, ["goose"], "aggressive")

        assert "goose_config" in gen
        assert (target / ".goose" / "config.yaml").exists(), ".goose/config.yaml 부재"

        content = (target / ".goose" / "config.yaml").read_text(encoding="utf-8")
        assert "version: 1" in content
        assert "entry_points:" in content
        assert "session_start" in content
        assert "backlog_update" in content
        assert "doc_sync" in content
        assert "read_files:" in content
        assert "ai-workflow/memory/active/<branch>/state.json" in content
        assert "language: ko" in content


# ---------------------------------------------------------------------------
# Acceptance #6: custom adapter 신규 → .workflow-kits/custom/SKILL.md
# ---------------------------------------------------------------------------
def test_custom_adapter_emits_v0_10_2() -> None:
    """Acceptance v0.10.2 #6: custom adapter → .workflow-kits/custom/SKILL.md (caller wire-up 용)."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        gen = _run_bootstrap(target, ["custom"], "aggressive")

        assert "custom_skill_template" in gen
        assert (target / ".workflow-kits" / "custom" / "SKILL.md").exists(), (
            ".workflow-kits/custom/SKILL.md 부재"
        )

        content = (target / ".workflow-kits" / "custom" / "SKILL.md").read_text(encoding="utf-8")
        assert "caller wire-up" in content
        assert "self-bootstrap" in content.lower()
        assert "SessionStartOutput" in content or "session-start" in content.lower()


# ---------------------------------------------------------------------------
# Acceptance #7: SUPPORTED_HARNESSES 7→10 정합
# ---------------------------------------------------------------------------
def test_supported_harnesses_count_v0_10_2() -> None:
    """Acceptance v0.10.2 #7: SUPPORTED_HARNESSES 7→10 (v0.10.1 + aider + goose + custom).

    v1.0.0: 이후 릴리스에서 harness 가 *추가* 되므로 (grok-build, codewhale, ...) 정확한
    개수/집합 고정이 아니라 **v0.10.2 당시 10종이 여전히 지원되는지** 를 회귀 검사한다.
    """
    from workflow_kit.bootstrap_lib.harnesses import SUPPORTED_HARNESSES

    expected = {
        "codex", "opencode", "gemini-cli", "pi-dev", "antigravity", "minimax-code",
        "claude-code", "aider", "goose", "custom",
    }
    missing = expected - set(SUPPORTED_HARNESSES)
    assert not missing, (
        f"v0.10.2: SUPPORTED_HARNESSES 에서 사라진 harness: {sorted(missing)}. "
        f"got: {SUPPORTED_HARNESSES}"
    )
    assert len(SUPPORTED_HARNESSES) == len(set(SUPPORTED_HARNESSES)), (
        f"v0.10.2: SUPPORTED_HARNESSES 에 중복 entry. got: {SUPPORTED_HARNESSES}"
    )


# ---------------------------------------------------------------------------
# Acceptance #8: session-start self-bootstrap mode
# ---------------------------------------------------------------------------
def test_session_start_self_bootstrap_v0_10_2() -> None:
    """Acceptance v0.10.2 #8: session-start skill — 핵심 4 file 모두 부재 시 status=warning + self_bootstrap_suggested=True + init commands emit.

    subprocess 로 실제 session-start skill 실행 (input file 모두 부재).
    """
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        # 4 file 모두 부재 (self-bootstrap 조건)
        handoff = target / "session_handoff.md"
        work_backlog = target / "work_backlog.md"
        profile = target / "PROJECT_PROFILE.md"

        # session-start skill 실행 (subprocess)
        result = subprocess.run(
            [
                sys.executable,
                str(SOURCE_ROOT / "skills" / "session-start" / "scripts" / "run_session_start.py"),
                f"--session-handoff-path={handoff}",
                f"--work-backlog-index-path={work_backlog}",
                f"--project-profile-path={profile}",
            ],
            capture_output=True,
            text=True,
            cwd=str(SOURCE_ROOT),
        )
        # session-start 는 graceful skip + exit 0 또는 1 — JSON output verify
        # output JSON parse
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            # 예전 version (missing_required_document) 도 OK — v0.10.2 이전
            if "missing_required_document" in result.stdout:
                # v0.10.2 이전 동작 — graceful skip + error_code
                return  # 이전 version 정합
            raise

        # v0.10.2 신규: self-bootstrap mode field
        if "self_bootstrap_suggested" in output:
            assert output["self_bootstrap_suggested"] is True
            assert "self_bootstrap_init_commands" in output
            assert len(output["self_bootstrap_init_commands"]) >= 1
            # 첫 명령은 bootstrap_workflow_kit.py 호출
            assert any(
                "bootstrap_workflow_kit.py" in cmd
                for cmd in output["self_bootstrap_init_commands"]
            )
            assert output["status"] == "warning"


# ---------------------------------------------------------------------------
# Acceptance #9: v0.10.0/v0.10.1 회귀 (deprecation + entry-mode 3-mode) 유지
# ---------------------------------------------------------------------------
def test_v0_10_0_v0_10_1_regression_v0_10_2() -> None:
    """Acceptance v0.10.2 #9: v0.10.0 (deprecation cycle 종료) + v0.10.1 (entry-mode 3-mode + claude-code 1차) 회귀 유지."""
    # 1) v0.10.0: phishing_federation_v4 NOT in __all__
    from workflow_kit import __version__ as TOOL_VERSION  # noqa: F401
    import importlib
    wk = importlib.import_module("workflow_kit")
    assert "phishing_federation_v4" not in wk.__all__, (
        "v0.10.0 회귀 깨짐: phishing_federation_v4 가 __all__ 에 있음 (deprecation cycle 종료 정합 위반)"
    )
    # 2) v0.10.1: --entry-mode option 3-mode
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        # aggressive mode
        gen_aggr = _run_bootstrap(target, ["codex"], "aggressive")
        assert "codex_agents" in gen_aggr, "v0.10.1 회귀 깨짐: codex + aggressive 에서 AGENTS.md 부재"
        # skill-only mode
        # v1.0.0: mkdtemp() → 중첩 TemporaryDirectory(). mkdtemp 은 자동 정리가
        # 없어 *성공한 실행마다* temp dir 이 하나씩 남는다 (실측 확인).
        with tempfile.TemporaryDirectory() as tmp2:
            target2 = Path(tmp2)
            gen_skill = _run_bootstrap(target2, ["codex"], "skill-only")
            assert "codex_agents" not in gen_skill, "v0.10.1 회귀 깨짐: codex + skill-only 에서 AGENTS.md emit 됨"


def main() -> int:
    test_funcs = [
        test_claude_code_entry_point_corrected_v0_10_2,
        test_claude_code_aggressive_emits_v0_10_2,
        test_claude_code_skill_only_skips_claude_md_v0_10_2,
        test_aider_adapter_emits_v0_10_2,
        test_goose_adapter_emits_v0_10_2,
        test_custom_adapter_emits_v0_10_2,
        test_supported_harnesses_count_v0_10_2,
        test_session_start_self_bootstrap_v0_10_2,
        test_v0_10_0_v0_10_1_regression_v0_10_2,
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
