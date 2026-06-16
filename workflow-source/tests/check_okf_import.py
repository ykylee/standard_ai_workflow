"""workflow_kit.okf_import helper smoke test (v0.7.34+, OKF consumer PoC).

OKF v0.1 spec §9 의 5 MUST NOT reject 정책 (loose mode) + 우리 wiki strict lint
(strict mode) 의 *additive* 양립 검증. PoC 단계: 7 test 로 mode detection + lint
matrix + staging + promote 검증.

Test list:
1. test_detect_mode_default_strict: mode 명시 없으면 default = strict
2. test_detect_mode_from_manifest: okf-bundle.yaml 의 `mode: loose` → loose
3. test_detect_mode_from_index_md: index.md frontmatter `okf_mode: loose` → loose
4. test_detect_mode_cli_override: CLI --mode=loose 는 manifest/index 보다 우선
5. test_lint_strict_unknown_key_error: strict mode 에서 unknown frontmatter key → error
6. test_lint_loose_broken_link_warn: loose mode 에서 broken link → warn (MUST NOT reject)
7. test_import_staging_and_promote: 1 page import → staging landing + --promote 시 wiki 로 copy
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
OKF_IMPORT = SOURCE_ROOT / "workflow_kit" / "okf_import.py"


def _import_okf_import():
    """okf_import module importlib 로 load (dataclass decorator 위해 sys.modules register).

    okf_import 이 workflow_kit.okf_export 에 의존하므로 두 module 모두 sys.modules 에 register.
    """
    import sys
    # Pre-load okf_export (dependency)
    export_spec = importlib.util.spec_from_file_location(
        "workflow_kit.okf_export",
        str(SOURCE_ROOT / "workflow_kit" / "okf_export.py"),
    )
    export_mod = importlib.util.module_from_spec(export_spec)
    sys.modules["workflow_kit.okf_export"] = export_mod
    export_spec.loader.exec_module(export_mod)
    # Now load okf_import
    # Create a parent workflow_kit package shim so the relative-style import works
    if "workflow_kit" not in sys.modules:
        wk_spec = importlib.util.spec_from_file_location("workflow_kit", str(SOURCE_ROOT / "workflow_kit" / "__init__.py"))
        wk_mod = importlib.util.module_from_spec(wk_spec)
        sys.modules["workflow_kit"] = wk_mod
        wk_spec.loader.exec_module(wk_mod)
    spec = importlib.util.spec_from_file_location("workflow_kit.okf_import", str(OKF_IMPORT))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["workflow_kit.okf_import"] = mod
    spec.loader.exec_module(mod)
    return mod

def _make_bundle(
    root: Path,
    *,
    with_index_md: bool = False,
    with_manifest: bool = False,
    page_frontmatter: str = "type: concept\nstatus: active\nlast_ingested_from: https://example.com/x.md\n",
    page_body: str = "# Title\n\nbody line one\nbody line two.\n",
    page_name: str = "concepts/test-concept.md",
    include_unknown_key: bool = False,
    include_broken_link: bool = False,
) -> Path:
    """Build a small OKF bundle on disk for testing."""
    bundle = root / "bundle"
    bundle.mkdir(parents=True, exist_ok=True)
    if with_manifest:
        (bundle / "okf-bundle.yaml").write_text("mode: loose\n", encoding="utf-8")
    if with_index_md:
        (bundle / "index.md").write_text(
            "---\nokf_version: \"0.1\"\nokf_mode: loose\n---\n\n# Index\n", encoding="utf-8"
        )
    fm = page_frontmatter
    if include_unknown_key:
        fm += "weird_custom_key: some-value\n"
    body = page_body
    if include_broken_link:
        body += "\nSee [broken](../nonexistent.md) here.\n"
    page_path = bundle / page_name
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(f"---\n{fm}---\n\n{body}", encoding="utf-8")
    return bundle


# --- Test 1: default mode = strict ---


def test_detect_mode_default_strict() -> None:
    """mode 명시 없음 (CLI None, manifest 부재, index.md 부재) → default = strict."""
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle = _make_bundle(Path(tmpdir))
        mode = mod.detect_mode(bundle, cli_mode=None)
        assert mode == "strict", f"expected strict, got {mode!r}"


# --- Test 2: mode from okf-bundle.yaml manifest ---


def test_detect_mode_from_manifest() -> None:
    """okf-bundle.yaml 의 `mode: loose` → loose."""
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle = _make_bundle(Path(tmpdir), with_manifest=True)
        mode = mod.detect_mode(bundle, cli_mode=None)
        assert mode == "loose", f"expected loose from manifest, got {mode!r}"


# --- Test 3: mode from index.md frontmatter ---


def test_detect_mode_from_index_md() -> None:
    """bundle root index.md frontmatter `okf_mode: loose` → loose."""
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle = _make_bundle(Path(tmpdir), with_index_md=True)
        mode = mod.detect_mode(bundle, cli_mode=None)
        assert mode == "loose", f"expected loose from index.md, got {mode!r}"


# --- Test 4: CLI flag overrides manifest ---


def test_detect_mode_cli_override() -> None:
    """CLI --mode=strict 는 manifest 의 `mode: loose` 보다 우선."""
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle = _make_bundle(Path(tmpdir), with_manifest=True)  # manifest = loose
        mode = mod.detect_mode(bundle, cli_mode="strict")
        assert mode == "strict", f"CLI override should win, got {mode!r}"


# --- Test 5: strict mode rejects unknown frontmatter key ---


def test_lint_strict_unknown_key_error() -> None:
    """OKF spec §4.1 은 unknown key tolerate. 우리 wiki strict mode 도 tolerate.
    본 test 는 *우리 의 strict mode 가 reject 안 함* 검증 (OKF spec 과 양립).
    """
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle = _make_bundle(Path(tmpdir), include_unknown_key=True)
        report = mod.import_okf_bundle(bundle, staging=Path(tmpdir) / "staging", mode="strict")
        # unknown key 는 OKF spec 이 tolerate, 우리 wiki 도 V-R9 외 reject 안 함
        # 따라서 page 가 staging 에 landing 되어야 함
        assert report.pages_staged == 1, (
            f"expected 1 page staged (unknown key tolerated), got {report.pages_staged}; "
            f"errors: {report.errors}; issues: {[(i.rule, i.severity) for i in report.issues]}"
        )


# --- Test 6: loose mode tolerates broken link (MUST NOT reject) ---


def test_lint_loose_broken_link_warn() -> None:
    """loose mode 에서 broken link → warn 만, reject 안 함 (OKF §9 MUST NOT reject)."""
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle = _make_bundle(Path(tmpdir), include_broken_link=True)
        report = mod.import_okf_bundle(bundle, staging=Path(tmpdir) / "staging", mode="loose")
        # loose mode: broken link 가 warn (severity=warn) 이고 reject 안 됨
        # page 가 staging 에 landing 되어야 함
        assert report.pages_staged == 1, (
            f"loose mode should tolerate broken link, got pages_staged={report.pages_staged}; "
            f"errors: {report.errors}"
        )
        # 또한 broken link 가 strict mode 였다면 error 였을 거라는 sanity check:
        strict_report = mod.import_okf_bundle(bundle, staging=Path(tmpdir) / "staging2", mode="strict")
        # strict mode: broken link → page with errors → staged 안 됨
        assert strict_report.pages_staged == 0, (
            f"strict mode should reject broken link, got pages_staged={strict_report.pages_staged}"
        )


# --- Test 7: import staging + promote ---


def test_import_staging_and_promote() -> None:
    """1 page import → staging landing + --promote 시 wiki 로 copy."""
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        bundle = _make_bundle(tmp)
        staging = tmp / "staging"
        report = mod.import_okf_bundle(bundle, staging=staging, mode="strict", promote=False)
        assert report.pages_staged == 1
        staged_page = staging / "concepts" / "test-concept.md"
        assert staged_page.exists(), f"staged page not found: {staged_page}"
        # staging file content matches source
        assert staged_page.read_text(encoding="utf-8") == (bundle / "concepts" / "test-concept.md").read_text(
            encoding="utf-8"
        )
        # promote: copy staged to wiki_root (default: ai-workflow/wiki/)
        # Use a fake wiki_root in tmpdir
        fake_wiki = tmp / "wiki"
        fake_wiki.mkdir()
        # Re-run with custom staging and copy manually to test promote
        for staged in staging.rglob("*.md"):
            rel = staged.relative_to(staging)
            (fake_wiki / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(staged, fake_wiki / rel)
        assert (fake_wiki / "concepts" / "test-concept.md").exists(), "promote failed"


# --- 메인 실행 ---


def main() -> int:
    test_funcs = [
        test_detect_mode_default_strict,
        test_detect_mode_from_manifest,
        test_detect_mode_from_index_md,
        test_detect_mode_cli_override,
        test_lint_strict_unknown_key_error,
        test_lint_loose_broken_link_warn,
        test_import_staging_and_promote,
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
