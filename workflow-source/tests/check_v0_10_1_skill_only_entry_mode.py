"""v0.10.1 skill-only entry mode + claude-code adapter verify.

Acceptance criteria (workflow-source/core/llm_wiki_concept_purpose_spec.md §4.5 + workflow-source/scripts/bootstrap_lib/harnesses/__init__.py HARNESS_SPECS):
1. `--entry-mode skill-only` option 추가 + 3-mode (aggressive / safe / skill-only) validate
2. `--harness claude-code` adapter 등록 + HARNESS_SPECS entry 정합
3. claude-code + skill-only mode → 3 slash command (`.claude/commands/workflow-{session-start,backlog-update,doc-sync}.md`) emit + AGENTS.md 부재
4. claude-code + aggressive mode → 동일 3 slash command emit (entry-point 없음, 동일 결과)
5. codex + aggressive (default) → AGENTS.md + .codex/config.toml.example emit (기존 동작 유지)
6. codex + skill-only → AGENTS.md skip + .codex/config.toml.example emit (harness-specific file 유지)

모든 input file / target_root 은 임시 dir 에서 생성 (저장소 file layout 의존 ❌).
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
import types
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SOURCE_ROOT / "scripts"
BOOTSTRAP_LIB_DIR = SCRIPTS_DIR / "bootstrap_lib"

# Path setup
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _make_ns(
    target: Path,
    harnesses: list[str],
    entry_mode: str,
) -> argparse.Namespace:
    """bootstrap_lib.__main__ 가 받을 수 있는 argparse.Namespace 생성."""
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
    """bootstrap_lib write_harness_files 실행 → generated file map."""
    from bootstrap_lib.__main__ import (
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
# Acceptance #1: --entry-mode option 추가 + 3-mode validate
# ---------------------------------------------------------------------------
def test_entry_mode_option_present_v0_10_1() -> None:
    """Acceptance §4.5 #1: parse_args 가 --entry-mode option 을 3-mode (aggressive/safe/skill-only) 로 받음."""
    from bootstrap_lib.__main__ import parse_args

    # sys.argv 조작 (parse_args 는 sys.argv 를 직접 읽음)
    base_argv = [
        "--target-root=/tmp/test",
        "--project-slug=t",
        "--project-name=T",
        "--no-interactive",
        "--harness=claude-code",
    ]
    saved_argv = sys.argv
    try:
        sys.argv = ["bootstrap"] + base_argv + ["--entry-mode=skill-only"]
        ns = parse_args()
    finally:
        sys.argv = saved_argv

    assert hasattr(ns, "entry_mode"), (
        "parse_args 가 entry_mode field 를 가진 Namespace 를 반환해야 함"
    )
    assert ns.entry_mode == "skill-only", (
        f"entry_mode=skill-only expected, got {ns.entry_mode}"
    )

    # 다른 mode 도 validate
    for mode in ("aggressive", "safe"):
        saved_argv = sys.argv
        try:
            sys.argv = ["bootstrap"] + base_argv + [f"--entry-mode={mode}"]
            ns2 = parse_args()
        finally:
            sys.argv = saved_argv
        assert ns2.entry_mode == mode, f"entry_mode={mode} expected, got {ns2.entry_mode}"


# ---------------------------------------------------------------------------
# Acceptance #2: claude-code adapter 등록 + HARNESS_SPECS 정합
# ---------------------------------------------------------------------------
def test_claude_code_harness_registered_v0_10_1() -> None:
    """Acceptance §4.5 #2: 'claude-code' 가 SUPPORTED_HARNESSES + HARNESS_SPECS + HARNESS_FILE_BUILDERS 에 등록.

    **v0.10.2 갱신**: v0.10.1 의 "Claude Code 는 root 진입점 안 읽음" 가설이 잘못. Claude Code 도
    CLAUDE.md 를 root 진입점으로 자동 read. entry_files 는 ('CLAUDE.md',) 로 정정됨.
    """
    from bootstrap_lib.harnesses import (
        HARNESS_SPECS,
        HARNESS_FILE_BUILDERS,
        SUPPORTED_HARNESSES,
    )

    assert "claude-code" in SUPPORTED_HARNESSES, (
        f"claude-code 가 SUPPORTED_HARNESSES 에 등록되어야 함. got: {SUPPORTED_HARNESSES}"
    )
    assert "claude-code" in HARNESS_SPECS, (
        f"claude-code 가 HARNESS_SPECS 에 등록되어야 함. got: {list(HARNESS_SPECS.keys())}"
    )
    assert "claude-code" in HARNESS_FILE_BUILDERS, (
        f"claude-code 가 HARNESS_FILE_BUILDERS 에 등록되어야 함. got: {list(HARNESS_FILE_BUILDERS.keys())}"
    )

    # v0.10.2 정정: entry_files = ('CLAUDE.md',) (Claude Code 도 root 진입점 자동 read)
    spec = HARNESS_SPECS["claude-code"]
    assert spec.entry_files == ("CLAUDE.md",), (
        f"v0.10.2 정정: claude-code entry_files 는 ('CLAUDE.md',) 여야 함 (Claude Code 도 "
        f"root 진입점 자동 read). got: {spec.entry_files}"
    )
    # 3 slash command extra_files 유지 (additive 도구)
    assert len(spec.extra_files) == 3, (
        f"claude-code extra_files 는 3개 slash command 여야 함. got: {len(spec.extra_files)}"
    )


# ---------------------------------------------------------------------------
# Acceptance #3: claude-code + skill-only → 3 slash command emit + AGENTS.md 부재
# ---------------------------------------------------------------------------
def test_claude_code_skill_only_emits_v0_10_1() -> None:
    """Acceptance §4.5 #3: claude-code + skill-only mode → 3 slash command emit + AGENTS.md 부재."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        gen = _run_bootstrap(target, ["claude-code"], "skill-only")

        # 3 slash command 생성
        assert "claude_code_session_start_command" in gen
        assert "claude_code_backlog_update_command" in gen
        assert "claude_code_doc_sync_command" in gen

        # 파일 존재 verify
        for key in (
            "claude_code_session_start_command",
            "claude_code_backlog_update_command",
            "claude_code_doc_sync_command",
        ):
            path = Path(gen[key])
            assert path.exists(), f"{key} 경로 {path} 가 존재하지 않음"
            content = path.read_text(encoding="utf-8")
            assert len(content) > 100, f"{key} file 이 너무 짧음 (≤100 char)"

        # AGENTS.md 부재 verify (skill-only 진입의 의도)
        assert not (target / "AGENTS.md").exists(), (
            f"claude-code + skill-only 모드에서 AGENTS.md 가 emit 되지 않아야 함. "
            f"target_root: {target}"
        )
        # .claude/commands/ 디렉토리는 emit 됨
        assert (target / ".claude" / "commands").is_dir(), (
            f".claude/commands/ 디렉토리 emit 되어야 함. target: {target}"
        )


# ---------------------------------------------------------------------------
# Acceptance #4: claude-code + aggressive → 동일 3 slash command (root 진입점 없음)
# ---------------------------------------------------------------------------
def test_claude_code_aggressive_emits_v0_10_1() -> None:
    """Acceptance §4.5 #4: claude-code + aggressive mode → 동일 3 slash command (root 진입점 없음).

    claude-code 는 *원래* root 진입점이 없으므로 entry-mode 와 무관하게 동일한 결과.
    """
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        gen = _run_bootstrap(target, ["claude-code"], "aggressive")

        # 3 slash command 생성 (skill-only 와 동일)
        assert "claude_code_session_start_command" in gen
        assert "claude_code_backlog_update_command" in gen
        assert "claude_code_doc_sync_command" in gen

        # AGENTS.md 부재 (root 진입점 emit 안 함, 어느 mode 에서도)
        assert not (target / "AGENTS.md").exists(), (
            "claude-code 는 root 진입점 (AGENTS.md) 을 emit 하지 않음 (어느 mode 에서도)"
        )


# ---------------------------------------------------------------------------
# Acceptance #5: codex + aggressive (default) → AGENTS.md + .codex/config.toml.example
# ---------------------------------------------------------------------------
def test_codex_aggressive_emits_v0_10_1() -> None:
    """Acceptance §4.5 #5: codex + aggressive (default) → AGENTS.md + .codex/config.toml.example (기존 동작 유지)."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        gen = _run_bootstrap(target, ["codex"], "aggressive")

        # AGENTS.md + .codex/config.toml.example 둘 다 emit
        assert "codex_agents" in gen
        assert "codex_config_example" in gen
        assert (target / "AGENTS.md").exists(), (
            "codex + aggressive (default) 에서 AGENTS.md emit 되어야 함"
        )
        assert (target / ".codex" / "config.toml.example").exists(), (
            "codex + aggressive 에서 .codex/config.toml.example emit 되어야 함"
        )


# ---------------------------------------------------------------------------
# Acceptance #6: codex + skill-only → AGENTS.md skip + .codex/config.toml.example 유지
# ---------------------------------------------------------------------------
def test_codex_skill_only_skips_agents_v0_10_1() -> None:
    """Acceptance §4.5 #6: codex + skill-only → AGENTS.md skip, harness-specific config.toml.example 유지.

    entry-mode=skill-only 의 *contract*: root 진입점 (AGENTS.md) skip, harness-specific file 유지.
    """
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        gen = _run_bootstrap(target, ["codex"], "skill-only")

        # codex_agents NOT in gen (AGENTS.md skip)
        assert "codex_agents" not in gen, (
            f"codex + skill-only 모드에서 codex_agents 가 emit 되지 않아야 함. got: {list(gen.keys())}"
        )
        # codex_config_example 여전히 in gen
        assert "codex_config_example" in gen, (
            f"codex + skill-only 모드에서 codex_config_example 은 유지되어야 함. got: {list(gen.keys())}"
        )
        # AGENTS.md 부재
        assert not (target / "AGENTS.md").exists(), (
            "codex + skill-only 모드에서 AGENTS.md 가 emit 되지 않아야 함"
        )
        # .codex/config.toml.example 존재
        assert (target / ".codex" / "config.toml.example").exists(), (
            "codex + skill-only 모드에서 .codex/config.toml.example 은 emit 되어야 함"
        )


def main() -> int:
    test_funcs = [
        test_entry_mode_option_present_v0_10_1,
        test_claude_code_harness_registered_v0_10_1,
        test_claude_code_skill_only_emits_v0_10_1,
        test_claude_code_aggressive_emits_v0_10_1,
        test_codex_aggressive_emits_v0_10_1,
        test_codex_skill_only_skips_agents_v0_10_1,
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
