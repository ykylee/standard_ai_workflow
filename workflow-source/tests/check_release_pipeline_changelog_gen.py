"""tools/release_pipeline.py changelog-gen subcommand smoke test (v0.7.14+).

v0.7.14 follow-up: cmd_changelog_gen — multi-release git log → CHANGELOG.md (Keep-a-Changelog 형식).
4 test PASS 기준.

Test list:
1. test_changelog_gen_argparse: --output / --unreleased-label / --dry-run / --json argparse error 없음
2. test_changelog_gen_dry_run: dry-run mode 에서 file 변경 없음 + mode=dry-run + commits/versions 정합
3. test_changelog_gen_apply: apply mode 에서 CHANGELOG.md 작성 + Keep-a-Changelog 형식 검증
4. test_changelog_gen_section_categorization: commit subject prefix → section mapping 검증
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
TOOL = SOURCE_ROOT / "tools" / "release_pipeline.py"
DEFAULT_OUTPUT = SOURCE_ROOT / "CHANGELOG.md"


def _import_tool():
    """release_pipeline.py 를 importlib 로 로드."""
    spec = importlib.util.spec_from_file_location("release_pipeline", str(TOOL))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- Test 1: argparse 인식 ---


def test_changelog_gen_argparse() -> None:
    """changelog-gen 의 --output / --unreleased-label / --dry-run / --json argparse error 없음."""
    for args in [
        ["--dry-run", "--json"],
        ["--output=/tmp/test_changelog.md", "--dry-run"],
        ["--unreleased-label=Pending", "--dry-run"],
    ]:
        proc = subprocess.run(
            [sys.executable, str(TOOL), "changelog-gen"] + args,
            capture_output=True, text=True, timeout=30,
        )
        assert "unrecognized arguments" not in proc.stderr, \
            f"args={args} → argparse error: {proc.stderr}"


# --- Test 2: dry-run mode 에서 file 변경 없음 + result 정합 ---


def test_changelog_gen_dry_run() -> None:
    """dry-run mode 에서 file 변경 없음 + mode=dry-run + commits/versions 정합."""
    pre_exists = DEFAULT_OUTPUT.exists()
    pre_content = DEFAULT_OUTPUT.read_text() if pre_exists else ""

    proc = subprocess.run(
        [sys.executable, str(TOOL), "changelog-gen", "--dry-run", "--json"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, f"exit {proc.returncode}: {proc.stderr}"
    out = json.loads(proc.stdout)
    assert out["mode"] == "dry-run"
    assert "output_path" in out
    assert out["commits"] > 0
    assert out["versions"] > 0

    # file 변경 없음
    post_exists = DEFAULT_OUTPUT.exists()
    assert pre_exists == post_exists, "dry-run 에서 file 부재 변경"
    if pre_exists:
        assert DEFAULT_OUTPUT.read_text() == pre_content, "dry-run 에서 file 내용 변경"


# --- Test 3: apply mode 에서 CHANGELOG.md 작성 + Keep-a-Changelog 형식 ---


def test_changelog_gen_apply() -> None:
    """apply mode 에서 CHANGELOG.md 작성 + Keep-a-Changelog 형식 검증.

    임시 output file 사용. 본 repo 의 CHANGELOG.md 는 건드리지 않음.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "CHANGELOG.md"
        proc = subprocess.run(
            [sys.executable, str(TOOL), "changelog-gen", "--output", str(out_path), "--apply", "--json"],
            capture_output=True, text=True, timeout=60,
        )
        assert proc.returncode == 0, f"exit {proc.returncode}: {proc.stderr}"
        out = json.loads(proc.stdout)
        assert out["mode"] == "applied"
        assert out["output_path"] == str(out_path)
        assert out["commits"] > 0
        assert out["versions"] > 0

        # file 존재
        assert out_path.exists()
        body = out_path.read_text()

        # Keep-a-Changelog 형식 검증
        assert body.startswith("# Changelog\n")
        assert "## [Unreleased]" in body or re.search(r"## \[\d+\.\d+\.\d+\]", body), \
            "no version section"
        # Section header
        assert "### Added" in body, "no Added section"
        # commit 형식: `<subject> (<short>)`
        assert re.search(r"\([0-9a-f]{7}\)", body), "no commit hash format"


# --- Test 4: section categorization (commit subject prefix → section) ---


def test_changelog_gen_section_categorization() -> None:
    """commit subject prefix → Keep-a-Changelog section mapping.

    categorize_by_section() 직접 호출 + 각 prefix 의 section 검증.
    """
    mod = _import_tool()
    # standard prefix
    assert mod.categorize_by_section("feat(v0.7.0): ...") == "Added"
    assert mod.categorize_by_section("fix(v0.7.0): ...") == "Fixed"
    assert mod.categorize_by_section("docs(v0.7.0): ...") == "Changed"
    assert mod.categorize_by_section("chore(v0.7.0): ...") == "Changed"
    # unknown prefix
    assert mod.categorize_by_section("random subject") == "Changed"
    # known: refactor, perf, test, build, ci
    assert mod.categorize_by_section("refactor(v0.7.0): ...") == "Changed"
    assert mod.categorize_by_section("perf(v0.7.0): ...") == "Changed"
    assert mod.categorize_by_section("test(v0.7.0): ...") == "Changed"


# --- 메인 실행 ---


def main() -> int:
    test_funcs = [
        test_changelog_gen_argparse,
        test_changelog_gen_dry_run,
        test_changelog_gen_apply,
        test_changelog_gen_section_categorization,
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
    if failed:
        print(f"\n{len(failed)} tests failed:")
        for name in failed:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
