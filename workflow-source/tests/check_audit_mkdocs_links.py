"""scripts/audit_mkdocs_links test (v0.7.57+).

Verifies the cross-link audit script:
1. test_audit_clean_v0_7_57: clean docs (no broken links) → rc 0
2. test_audit_with_broken_link_v0_7_57: docs with broken link → rc 1
3. test_audit_skips_code_blocks_v0_7_57: links inside code blocks are not checked
4. test_audit_skips_excluded_dirs_v0_7_57: --exclude dirs are skipped
5. test_audit_skips_absolute_urls_v0_7_57: http/https links are not checked
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "audit_mkdocs_links.py"


def _run_audit(docs_dir: Path, *extra_args: str) -> subprocess.CompletedProcess:
    """Run audit_mkdocs_links.py with --docs pointing to a temp dir."""
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), f"--docs={docs_dir}", *extra_args],
        capture_output=True, text=True, timeout=30,
    )


def test_audit_clean_v0_7_57() -> None:
    """Clean docs (no broken links) returns rc 0."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "docs"
        d.mkdir()
        (d / "index.md").write_text("# Test\n\n[link](page2.md)\n", encoding="utf-8")
        (d / "page2.md").write_text("# Page 2\n", encoding="utf-8")
        result = _run_audit(d)
        assert result.returncode == 0, f"expected rc=0, got {result.returncode}: {result.stdout} {result.stderr}"


def test_audit_with_broken_link_v0_7_57() -> None:
    """Docs with broken link returns rc 1 with report."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "docs"
        d.mkdir()
        (d / "index.md").write_text("# Test\n\n[broken](nonexistent.md)\n", encoding="utf-8")
        result = _run_audit(d, "--json")
        assert result.returncode == 1, f"expected rc=1, got {result.returncode}"
        report = json.loads(result.stdout)
        assert report["broken_count"] == 1
        assert report["broken"][0]["link"] == "nonexistent.md"


def test_audit_skips_code_blocks_v0_7_57() -> None:
    """Links inside fenced code blocks are not checked."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "docs"
        d.mkdir()
        (d / "index.md").write_text(
            "# Test\n\n```bash\n"
            "cat > my-bundle/concepts/hello.md <<'EOF'\n"
            "- [Hello](concepts/hello.md)\n"
            "EOF\n"
            "```\n",
            encoding="utf-8",
        )
        result = _run_audit(d)
        assert result.returncode == 0, f"code block link should be ignored: {result.stdout} {result.stderr}"


def test_audit_skips_excluded_dirs_v0_7_57() -> None:
    """--exclude dirs are skipped."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "docs"
        d.mkdir()
        (d / "index.md").write_text("# Test\n", encoding="utf-8")
        archive = d / "archive"
        archive.mkdir()
        (archive / "old.md").write_text("[broken](nonexistent.md)\n", encoding="utf-8")
        # default excludes archive/
        result = _run_audit(d)
        assert result.returncode == 0, f"archive/ should be excluded: {result.stdout} {result.stderr}"


def test_audit_skips_absolute_urls_v0_7_57() -> None:
    """http/https/mailto URLs are not checked."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "docs"
        d.mkdir()
        (d / "index.md").write_text(
            "# Test\n\n"
            "[ext](https://example.com)\n"
            "[mail](mailto:test@test.com)\n"
            "[anchor](#section)\n",
            encoding="utf-8",
        )
        result = _run_audit(d)
        assert result.returncode == 0, f"absolute URLs should be ignored: {result.stdout} {result.stderr}"


def main() -> int:
    test_funcs = [
        test_audit_clean_v0_7_57,
        test_audit_with_broken_link_v0_7_57,
        test_audit_skips_code_blocks_v0_7_57,
        test_audit_skips_excluded_dirs_v0_7_57,
        test_audit_skips_absolute_urls_v0_7_57,
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
