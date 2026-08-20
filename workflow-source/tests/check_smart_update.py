#!/usr/bin/env python3
"""Regression test for the smart-update policy added in v0.5.10.1.

Covers the file-write decision used by both ``bootstrap_lib`` and
``apply_workflow_upgrade``: when the destination already exists, the
write must be skipped (ignored) or applied (updated) based on a
VERSION-marker comparison, with content-hash comparison as the
fallback. Preserved paths (user data under ``ai-workflow/memory/``
and friends) are never overwritten, even with ``--force``.

Run as a script. Exits 0 on success, raises AssertionError otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
SCRIPTS_ROOT = SOURCE_ROOT / "scripts"  # apply_workflow_upgrade.py 등 비-shim 스크립트


def _run_bootstrap_lib(args: list[str], env: dict[str, str] | None = None) -> dict:
    """Run ``python3 -m workflow_kit.bootstrap_lib`` and return the parsed manifest."""
    full_env = os.environ.copy()
    full_env["PYTHONPATH"] = (
        f"{SOURCE_ROOT}" + os.pathsep + full_env.get("PYTHONPATH", "")
    )
    if env:
        full_env.update(env)
    completed = subprocess.run(
        [sys.executable, "-m", "workflow_kit.bootstrap_lib", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=full_env,
        check=True,
    )
    return json.loads(completed.stdout)


def _bucket(actions: dict, action_name: str) -> list[dict]:
    return list(actions.get(action_name, []))


def test_bootstrap_first_run_creates_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        manifest = _run_bootstrap_lib(
            [
                "--target-root", str(target),
                "--project-slug", "test",
                "--project-name", "Test",
                "--harness", "opencode",
                "--no-interactive",
                "--adoption-mode", "new",
            ]
        )
        actions = manifest.get("file_actions", {})
        created = _bucket(actions, "created")
        assert len(created) > 0, "first run should CREATE files"
        # All non-preserved harness files should appear in created.
        rels = {a["rel"] for a in created}
        assert "AGENTS.md" in rels
        assert "opencode.json" in rels
        # Verify the marker was stamped on a markdown file.
        agents = (target / "AGENTS.md").read_text(encoding="utf-8")
        # 특정 버전을 고정하면 릴리스마다 red 가 된다 (v0.5.10.1 고정이 v1.0.0 에서 깨짐).
        # 검증 의도는 "marker 가 *현재 kit 버전* 으로 스탬프되는가" 이므로 동적으로 비교한다.
        from workflow_kit import __version__ as _kit_version
        # marker 는 `v` 접두사를 유지한다 (MARKER_REGEX 가 요구 — 기존 스탬프 파일과의
        # 호환). v1.2.1 부터 __version__ 자체에는 접두사가 없으므로 여기서 붙인다.
        assert f"standard-ai-workflow-kit: v{_kit_version.lstrip('v')}" in agents, (
            f"marker 가 현재 kit 버전({_kit_version})으로 스탬프되지 않았다")


def test_bootstrap_second_run_ignores_matching_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        common = [
            "--target-root", str(target),
            "--project-slug", "test",
            "--project-name", "Test",
            "--harness", "opencode",
            "--no-interactive",
            "--adoption-mode", "new",
        ]
        _run_bootstrap_lib(common)

        manifest2 = _run_bootstrap_lib(common)
        actions = manifest2["file_actions"]
        ignored = _bucket(actions, "ignored")
        assert len(ignored) > 0, "second run should IGNORE files with matching marker + hash"
        created2 = _bucket(actions, "created")
        assert len(created2) == 0, (
            f"second run should not CREATE; got {created2}"
        )


def test_bootstrap_preserves_user_data_with_force() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        # Pre-create a user file under preserved path.
        memory_dir = target / "ai-workflow" / "memory"
        memory_dir.mkdir(parents=True)
        user_file = memory_dir / "user_notes.md"
        user_file.write_text("# My own notes\n", encoding="utf-8")

        _run_bootstrap_lib(
            [
                "--target-root", str(target),
                "--project-slug", "test",
                "--project-name", "Test",
                "--harness", "opencode",
                "--no-interactive",
                "--adoption-mode", "new",
                "--force",
            ]
        )

        # File should still exist, untouched.
        assert user_file.exists()
        content = user_file.read_text(encoding="utf-8")
        assert content == "# My own notes\n", (
            f"PRESERVE path was overwritten: {content!r}"
        )


def test_forked_entry_point_survives_reapply() -> None:
    """포크를 선언한 진입점은 재적용에서 **살아남는다** (TASK-2026-08-20-main-012).

    단위 검사만으로는 부족하다 — 실제 손실은 `decide_action` 이 아니라 그것을
    부르는 bootstrap 경로에서 난다. 이 저장소의 `CLAUDE.md` 가 실측으로 얻은
    운영 규칙 90여 줄을 담고 있었고, `wk doctor` 는 그 파일을 "재적용 대상"
    으로 조언하고 있었다. 조언을 따랐다면 전부 placeholder 가 됐다.
    """
    marker = "PROJECT-OWNED-SENTINEL"
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        base = [
            "--target-root", str(target),
            "--project-slug", "test",
            "--project-name", "Test",
            "--harness", "claude-code",
            "--no-interactive",
            "--adoption-mode", "new",
        ]
        _run_bootstrap_lib(base)

        entry = target / "CLAUDE.md"
        assert entry.is_file(), "claude-code 진입점이 생성되지 않았다"
        original = entry.read_text(encoding="utf-8")
        forked = (
            "<!-- standard-ai-workflow-kit-fork: project owns this entry point -->\n"
            + original
            + f"\n## Project section\n\n{marker}\n"
        )
        entry.write_text(forked, encoding="utf-8")

        manifest = _run_bootstrap_lib(base)
        actions = manifest["file_actions"]
        forked_rels = {record["rel"] for record in _bucket(actions, "forked")}
        assert "CLAUDE.md" in forked_rels, (
            f"포크된 진입점이 forked 버킷에 없다 — 요약에서 사라지면 조작자는 "
            f"'아무 일도 없었다' 로 읽는다. buckets={ {k: len(v) for k, v in actions.items()} }"
        )
        assert marker in entry.read_text(encoding="utf-8"), (
            "재적용이 프로젝트 소유 내용을 지웠다"
        )

        # --force 는 이긴다 — 포크는 "덮지 마라" 가 아니라 "모르고 덮지 마라" 다.
        _run_bootstrap_lib([*base, "--force"])
        assert marker not in entry.read_text(encoding="utf-8"), (
            "--force 가 포크된 진입점을 덮지 못했다 — 불가침(사용자 상태)과 "
            "구분되지 않으면 명시적 재적용 경로가 사라진다"
        )


def test_apply_upgrade_smart_update() -> None:
    """apply_workflow_upgrade should use the same smart-update policy."""
    with tempfile.TemporaryDirectory() as tmp:
        bundle = Path(tmp) / "bundle"
        target = Path(tmp) / "target"
        (bundle / "ai-workflow").mkdir(parents=True)
        (bundle / "ai-workflow" / "VERSION").write_text("v0.5.10.1-beta\n", encoding="utf-8")
        (bundle / "ai-workflow" / "PROFILE.md").write_text(
            "<!-- standard-ai-workflow-kit: v0.5.10.1-beta -->\n# New profile\n",
            encoding="utf-8",
        )
        target.mkdir()

        env = {"PYTHONPATH": f"{SOURCE_ROOT}{os.pathsep}{SCRIPTS_ROOT}"}
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "apply_workflow_upgrade.py"),
                "--source-root", str(bundle),
                "--target-root", str(target),
            ],
            cwd=str(REPO_ROOT),
            env={**env, **os.environ},
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Created:" in completed.stdout
        # First run creates both VERSION and PROFILE.md.
        assert (target / "ai-workflow" / "VERSION").exists()
        assert (target / "ai-workflow" / "PROFILE.md").exists()

        # Second run: should be all IGNORED via the kit-version short-circuit.
        completed2 = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "apply_workflow_upgrade.py"),
                "--source-root", str(bundle),
                "--target-root", str(target),
                "--dry-run",
            ],
            cwd=str(REPO_ROOT),
            env={**env, **os.environ},
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Ignored:" in completed2.stdout
        assert "already up to date" in completed2.stdout


def test_upgrade_diff_unit() -> None:
    """Quick unit smoke of the underlying decision function."""
    sys.path.insert(0, str(SOURCE_ROOT))
    from workflow_kit.upgrade_diff import Action, decide_action  # type: ignore[import-not-found]

    dec = decide_action(
        src_text="<!-- standard-ai-workflow-kit: v0.5.10.1-beta -->\nNEW",
        dst_text="<!-- standard-ai-workflow-kit: v0.5.0-beta -->\nOLD",
    )
    assert dec.action == Action.UPDATED, dec

    dec = decide_action(
        src_text="<!-- standard-ai-workflow-kit: v0.5.10.1-beta -->\nNEW",
        dst_text="<!-- standard-ai-workflow-kit: v0.5.10.1-beta -->\nNEW",
    )
    assert dec.action == Action.IGNORED, dec

    dec = decide_action(src_text="x", dst_text="y", is_preserved_path=True, force=True)
    assert dec.action == Action.PRESERVED, dec

    # 소유권 4번째 분류: 포크 선언은 재적용을 막고, force 는 그것을 이긴다.
    forked_dst = (
        "<!-- standard-ai-workflow-kit: v0.5.0-beta -->\n"
        "<!-- standard-ai-workflow-kit-fork: project owns this -->\n"
        "OLD"
    )
    dec = decide_action(
        src_text="<!-- standard-ai-workflow-kit: v0.5.10.1-beta -->\nNEW",
        dst_text=forked_dst,
    )
    assert dec.action == Action.FORKED, dec
    # 갈라져 나온 시점을 잃지 않는다 — 그 버전과 diff 하는 것이 유일한 병합 경로다.
    assert dec.dst_marker == "0.5.0-beta", dec

    dec = decide_action(
        src_text="<!-- standard-ai-workflow-kit: v0.5.10.1-beta -->\nNEW",
        dst_text=forked_dst,
        force=True,
    )
    assert dec.action == Action.UPDATED, dec

    # 불가침은 force 로도 안 덮인다 — 포크와 갈리는 자리가 정확히 여기다.
    dec = decide_action(
        src_text="NEW", dst_text=forked_dst, is_preserved_path=True, force=True
    )
    assert dec.action == Action.PRESERVED, dec


def test_bootstrap_wheel_install_graceful_when_no_source() -> None:
    """Verify graceful skip when SOURCE_ROOT is unresolvable (wheel install
    without bundled core-docs data) and that global_snippet_sources accepts
    None without crashing. Also sanity-checks dev-install still copies
    core docs.
    """
    sys.path.insert(0, str(SOURCE_ROOT))
    sys.path.insert(0, str(SCRIPTS_ROOT))
    import workflow_kit.bootstrap_lib.__main__ as BM  # type: ignore[import-not-found]
    from workflow_kit.bootstrap_lib.discovery import global_snippet_sources  # type: ignore[import-not-found]

    assert global_snippet_sources(None) == {}, (
        "global_snippet_sources must return empty dict when source_root is None"
    )

    real_source_root = BM.SOURCE_ROOT
    BM.SOURCE_ROOT = None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            _make_args(target, copy_core_docs=True, force=True)
            manifest = _run_bootstrap_lib(
                [
                    "--target-root", str(target),
                    "--project-slug", "test",
                    "--project-name", "Test",
                    "--harness", "opencode",
                    "--no-interactive",
                    "--adoption-mode", "new",
                    "--copy-core-docs",
                ],
                env={"BOOTSTRAP_LIB_NO_SOURCE": "1"},
            )
            assert manifest.get("copied_core_docs") == [], (
                f"wheel install with SOURCE_ROOT=None should skip core docs; got {manifest.get('copied_core_docs')!r}"
            )
            warnings = manifest.get("warnings", [])
            assert any("core docs are not bundled" in w for w in warnings), (
                f"expected a manifest warning about missing core docs; got {warnings!r}"
            )
    finally:
        BM.SOURCE_ROOT = real_source_root

    assert real_source_root is not None, (
        "sanity: the dev-install SOURCE_ROOT should resolve"
    )

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        manifest = _run_bootstrap_lib(
            [
                "--target-root", str(target),
                "--project-slug", "test",
                "--project-name", "Test",
                "--harness", "opencode",
                "--no-interactive",
                "--adoption-mode", "new",
                "--copy-core-docs",
            ]
        )
        assert len(manifest.get("copied_core_docs", [])) > 0, (
            "dev-install should copy core docs"
        )


def _make_args(target_root: Path, copy_core_docs: bool = True, force: bool = False):
    return argparse.Namespace(
        target_root=str(target_root),
        kit_dir="ai-workflow",
        project_slug="test",
        project_name="Test",
        project_intro="Test",
        today="2026-06-09",
        adoption_mode="new",
        copy_core_docs=copy_core_docs,
        force=force,
        update_deps=False,
        enable_mcp=False,
        mcp_bridge="jsonrpc-bridge",
        harnesses=["opencode"],
        no_interactive=True,
        dry_run=False,
    )


def main() -> int:
    # 총계는 여기서 **세어서** 낸다 — `"6 checks"` 리터럴이었을 때는 case 를
    # 늘려도 숫자가 안 따라왔고, 그 숫자가 곧 "몇 개를 쟀나" 의 유일한 증거다.
    cases = [
        ("unit", test_upgrade_diff_unit),
        ("first-run CREATE", test_bootstrap_first_run_creates_files),
        ("second-run IGNORE", test_bootstrap_second_run_ignores_matching_files),
        ("PRESERVE+force", test_bootstrap_preserves_user_data_with_force),
        ("FORKED survives re-apply", test_forked_entry_point_survives_reapply),
        ("apply_upgrade round-trip", test_apply_upgrade_smart_update),
        ("wheel-install graceful", test_bootstrap_wheel_install_graceful_when_no_source),
    ]
    for _name, case in cases:
        case()
    labels = ", ".join(name for name, _ in cases)
    print(
        f"Smart update regression check passed ({len(cases)} checks: {labels})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
