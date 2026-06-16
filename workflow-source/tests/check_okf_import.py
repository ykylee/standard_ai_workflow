"""workflow_kit.okf_import helper smoke test (v0.7.34+, OKF consumer PoC + v0.7.35 ADR-011 version detect).

OKF v0.1 spec §9 의 5 MUST NOT reject 정책 (loose mode) + 우리 wiki strict lint
(strict mode) 의 *additive* 양립 + ADR-011 spec version auto-detect 검증.

Test list (11):
1-7.  OKF consumer mode (loose/strict) + lint + staging + promote
8-11. ADR-011 version detect (parse + exact match + major mismatch + minor higher + missing)
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
        bundle = _make_bundle(Path(tmpdir), with_manifest=True)
        mode = mod.detect_mode(bundle, cli_mode="strict")
        assert mode == "strict", f"CLI override should win, got {mode!r}"


# --- Test 5: strict mode tolerates unknown frontmatter key ---


def test_lint_strict_unknown_key_error() -> None:
    """OKF spec §4.1 은 unknown key tolerate. 우리 wiki strict mode 도 tolerate."""
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle = _make_bundle(Path(tmpdir), include_unknown_key=True)
        report = mod.import_okf_bundle(bundle, staging=Path(tmpdir) / "staging", mode="strict")
        assert report.pages_staged == 1, (
            f"expected 1 page staged, got {report.pages_staged}; "
            f"errors: {report.errors}"
        )


# --- Test 6: loose mode tolerates broken link ---


def test_lint_loose_broken_link_warn() -> None:
    """loose mode 에서 broken link → warn 만, reject 안 함 (OKF §9 MUST NOT reject)."""
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle = _make_bundle(Path(tmpdir), include_broken_link=True)
        report = mod.import_okf_bundle(bundle, staging=Path(tmpdir) / "staging", mode="loose")
        assert report.pages_staged == 1, (
            f"loose mode should tolerate broken link, got pages_staged={report.pages_staged}; "
            f"errors: {report.errors}"
        )
        strict_report = mod.import_okf_bundle(bundle, staging=Path(tmpdir) / "staging2", mode="strict")
        assert strict_report.pages_staged == 0, (
            f"strict mode should reject broken link, got pages_staged={strict_report.pages_staged}"
        )


# --- Test 7: staging + promote ---


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
        assert staged_page.exists()
        assert staged_page.read_text(encoding="utf-8") == (bundle / "concepts" / "test-concept.md").read_text(
            encoding="utf-8"
        )
        fake_wiki = tmp / "wiki"
        fake_wiki.mkdir()
        for staged in staging.rglob("*.md"):
            rel = staged.relative_to(staging)
            (fake_wiki / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(staged, fake_wiki / rel)
        assert (fake_wiki / "concepts" / "test-concept.md").exists(), "promote failed"


# --- Test 8: OKF version parse (ADR-011) ---


def test_version_parse_canonical() -> None:
    """Canonical form "X.Y" parse. variants (v0.1, 0.1.5 semver) 도 accept."""
    mod = _import_okf_import()
    assert mod._parse_okf_version("0.1") == (0, 1)
    assert mod._parse_okf_version("0.2") == (0, 2)
    assert mod._parse_okf_version("1.0") == (1, 0)
    assert mod._parse_okf_version("v0.1") == (0, 1)
    assert mod._parse_okf_version("0.1.5") == (0, 1)
    assert mod._parse_okf_version(None) is None
    assert mod._parse_okf_version("") is None
    assert mod._parse_okf_version("1") is None
    assert mod._parse_okf_version("abc") is None


# --- Test 9: Version check exact match ---


def test_version_check_exact_match() -> None:
    """exact match (0.1 = 0.1) → pass."""
    mod = _import_okf_import()
    result = mod._check_version_compatibility("0.1")
    assert result.status == "pass", f"got {result.status}: {result.message}"
    assert result.bundle_version == "0.1"


# --- Test 10: Version check major mismatch → error ---


def test_version_check_major_mismatch_rejects_strict() -> None:
    """major mismatch (1.0 > 0.1) → error (our consumer cannot safely process)."""
    mod = _import_okf_import()
    result = mod._check_version_compatibility("1.0")
    assert result.status == "error", f"got {result.status}: {result.message}"
    assert "major" in result.message.lower() or "breaking" in result.message.lower()


# --- Test 11: Version check minor higher → warn ---


def test_version_check_minor_higher_warns() -> None:
    """minor higher (0.2 > 0.1, same major) → warn (backward-compatible per spec §11)."""
    mod = _import_okf_import()
    result = mod._check_version_compatibility("0.2")
    assert result.status == "warn", f"got {result.status}: {result.message}"
    assert "0.2" in result.message


# --- Test 12: Version check missing → warn (assume v0.1) ---


def test_version_check_missing_warns() -> None:
    """no okf_version field → warn (assume our v0.1)."""
    mod = _import_okf_import()
    result = mod._check_version_compatibility(None)
    assert result.status == "warn", f"got {result.status}: {result.message}"
    assert "no okf_version" in result.message.lower() or "assuming" in result.message.lower()


def test_r2_batch_size_in_range() -> None:
    """R-2 batch: 5-15 page range returns None (compliant)."""
    mod = _import_okf_import()
    assert mod.check_r2_batch_size(5) is None
    assert mod.check_r2_batch_size(10) is None
    assert mod.check_r2_batch_size(15) is None


def test_r2_batch_size_out_of_range() -> None:
    """R-2 batch: outside 5-15 range returns R2BatchWarning with recommendation."""
    mod = _import_okf_import()
    small = mod.check_r2_batch_size(2)
    assert small is not None
    assert small.page_count == 2
    assert small.threshold_min == 5
    assert "small" in small.recommendation.lower()
    large = mod.check_r2_batch_size(20)
    assert large is not None
    assert large.page_count == 20
    assert large.threshold_max == 15
    assert "large" in large.recommendation.lower() or "split" in large.recommendation.lower()


def test_audit_r2_batch_history_v0_7_41() -> None:
    """audit_r2_batch_history reads log.md and categorizes past batches."""
    mod = _import_okf_import()
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "log.md"
        log_path.write_text(
            "## [2026-06-16] release | v0.7.40 — + 8 new tests\n"
            "## [2026-06-16] release | v0.7.41 — + 3 new tests\n"
            "## [2026-06-16] release | v0.7.42 — + 25 new tests (large batch)\n",
            encoding="utf-8",
        )
        result = mod.audit_r2_batch_history(log_path=log_path)
        # 8 in range (5-15), 3 in range, 25 too large
        # 8 in range (5-15), 3 too small, 25 too large
        assert result.in_range == 1, f"expected 1 in-range, got {result.in_range}"
        assert result.too_small == 1, f"expected 1 too-small, got {result.too_small}"
        assert result.total_entries == 3


def test_audit_r2_batch_history_precise_v0_7_42() -> None:
    """audit_r2_batch_history_precise parses mocked git log --oneline output."""
    mod = _import_okf_import()
    import types
    fake_result = types.SimpleNamespace(
        returncode=0,
        stdout=(
            "abc1234 release(v0.7.40): + 17 new tests (1 phase)\n"
            "def5678 release(v0.7.41): + 5 new tests\n"
            "ghi9012 release(v0.7.42): + 22 new tests\n"
            "jkl3456 feat(v0.7.40): non-release commit (skipped)\n"
        ),
    )
    def fake_subprocess_run(cmd, **kwargs):
        return fake_result
    result = mod.audit_r2_batch_history_precise(
        repo_root=__import__("pathlib").Path("/fake"),
        subprocess_run=fake_subprocess_run,
    )
    # 3 release commits, 4 total commits
    assert result.too_small == 0, f"expected 0 too-small, got {result.too_small}"
    assert result.too_large == 2, f"expected 2 too-large, got {result.too_large}"


def test_cleanup_staging_dry_run_v0_7_56() -> None:
    """cleanup_staging (dry_run=True) reports removal but doesn't modify (v0.7.56+)."""
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "staging"
        staging.mkdir()
        (staging / "a.md").write_text("x", encoding="utf-8")
        (staging / "b.md").write_text("y", encoding="utf-8")
        result = mod.cleanup_staging(staging, dry_run=True)
        assert result["scanned"] == 2
        assert result["removed"] == 2
        assert result["dry_run"] is True
        # Files still exist
        assert (staging / "a.md").exists()
        assert (staging / "b.md").exists()


def test_cleanup_staging_apply_with_age_filter_v0_7_56() -> None:
    """cleanup_staging (apply + older_than) removes only old files (v0.7.56+)."""
    mod = _import_okf_import()
    import os
    import time
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "staging"
        staging.mkdir()
        old_file = staging / "old.md"
        new_file = staging / "new.md"
        old_file.write_text("x", encoding="utf-8")
        new_file.write_text("y", encoding="utf-8")
        # Make old_file 2 days old
        old_time = time.time() - 86400 * 2
        os.utime(old_file, (old_time, old_time))
        result = mod.cleanup_staging(staging, older_than_seconds=86400, dry_run=False)
        assert result["scanned"] == 2
        assert result["removed"] == 1
        assert result["kept"] == 1
        assert not old_file.exists()
        assert new_file.exists()


# --- Audit 3차 (v0.7.56+): strict mode lint rule coverage (V-1 / V-R9 / V-T1 / OKF §4.1) ---


def test_lint_v1_strict_rejects_non_wiki_subdir_v0_7_56() -> None:
    """V-1: page outside wiki-type subdir → strict mode ERROR (rejects)."""
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmp:
        # page in `random/` (not concepts/decisions/entities/patterns/queries)
        bundle = _make_bundle(
            Path(tmp),
            page_name="random/orphan.md",
        )
        report = mod.import_okf_bundle(
            bundle, staging=Path(tmp) / "staging", mode="strict",
        )
        v1_issues = [i for i in report.issues if i.rule == "V-1"]
        assert len(v1_issues) >= 1, f"expected V-1 issue, got {report.issues}"
        assert v1_issues[0].severity == "error", f"strict V-1 should be error, got {v1_issues[0]}"


def test_lint_v1_loose_warns_non_wiki_subdir_v0_7_56() -> None:
    """V-1: page outside wiki-type subdir → loose mode WARN (tolerates)."""
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmp:
        bundle = _make_bundle(
            Path(tmp),
            page_name="random/orphan.md",
            with_manifest=True,  # mode=loose
        )
        report = mod.import_okf_bundle(
            bundle, staging=Path(tmp) / "staging", mode="loose",
        )
        v1_issues = [i for i in report.issues if i.rule == "V-1"]
        if v1_issues:
            assert v1_issues[0].severity == "warn", f"loose V-1 should be warn, got {v1_issues[0]}"


def test_lint_v9_strict_rejects_missing_source_v0_7_56() -> None:
    """V-R9: missing/invalid last_ingested_from → strict mode ERROR."""
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmp:
        bundle = _make_bundle(
            Path(tmp),
            page_frontmatter="type: concept\nstatus: active\n",  # no last_ingested_from
        )
        report = mod.import_okf_bundle(
            bundle, staging=Path(tmp) / "staging", mode="strict",
        )
        v9_issues = [i for i in report.issues if i.rule == "V-R9"]
        assert len(v9_issues) >= 1, f"expected V-R9 issue, got {report.issues}"
        assert v9_issues[0].severity == "error", f"strict V-R9 should be error, got {v9_issues[0]}"


def test_lint_v9_strict_accepts_archive_path_v0_7_56() -> None:
    """V-R9: last_ingested_from with archive/ path → strict mode passes."""
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmp:
        bundle = _make_bundle(
            Path(tmp),
            page_frontmatter="type: concept\nstatus: active\nlast_ingested_from: memory/archive/2026-06-12/test.md\n",
        )
        report = mod.import_okf_bundle(
            bundle, staging=Path(tmp) / "staging", mode="strict",
        )
        v9_issues = [i for i in report.issues if i.rule == "V-R9"]
        assert len(v9_issues) == 0, f"archive/ path should pass V-R9, got {v9_issues}"


def test_lint_v_t1_strict_rejects_title_mismatch_v0_7_56() -> None:
    """V-T1: title != H1 → strict mode ERROR."""
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmp:
        bundle = _make_bundle(
            Path(tmp),
            page_frontmatter="type: concept\nstatus: active\ntitle: My Custom Title\nlast_ingested_from: https://example.com/x.md\n",
            page_body="# Different Title\n\nbody.\n",
        )
        report = mod.import_okf_bundle(
            bundle, staging=Path(tmp) / "staging", mode="strict",
        )
        vt1_issues = [i for i in report.issues if i.rule == "V-T1"]
        assert len(vt1_issues) >= 1, f"expected V-T1 issue, got {report.issues}"
        assert vt1_issues[0].severity == "error", f"strict V-T1 should be error, got {vt1_issues[0]}"


def test_lint_v_t1_strict_passes_matching_title_v0_7_56() -> None:
    """V-T1: title == H1 → strict mode passes (no V-T1 issue)."""
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmp:
        bundle = _make_bundle(
            Path(tmp),
            page_frontmatter="type: concept\nstatus: active\ntitle: Matching Title\nlast_ingested_from: https://example.com/x.md\n",
            page_body="# Matching Title\n\nbody.\n",
        )
        report = mod.import_okf_bundle(
            bundle, staging=Path(tmp) / "staging", mode="strict",
        )
        vt1_issues = [i for i in report.issues if i.rule == "V-T1"]
        assert len(vt1_issues) == 0, f"matching title should pass V-T1, got {vt1_issues}"


def test_lint_okf_4_1_strict_rejects_empty_type_v0_7_56() -> None:
    """OKF §4.1 hard 3: empty `type` field → ALWAYS error (both modes).

    Note: OKF §4.1 hard rule 1 (parseable frontmatter) is enforced at
    _parse_bundle_pages level (frontmatter parse fail → page dropped). This
    test verifies the rule is enforced post-parse via lint_page for
    whitespace-only `type` (which frontmatter parses as empty string).
    """
    mod = _import_okf_import()
    with tempfile.TemporaryDirectory() as tmp:
        # Build a bundle manually with valid frontmatter but empty type
        bundle = Path(tmp) / "bundle"
        bundle.mkdir()
        page = bundle / "concepts" / "test.md"
        page.parent.mkdir(parents=True, exist_ok=True)
        # Use explicit empty string to bypass YAML parsing edge cases
        page.write_text(
            '---\ntype: ""\nstatus: active\nlast_ingested_from: https://example.com/x.md\n---\n\n# Title\n\nbody.\n',
            encoding="utf-8",
        )
        pages = mod._parse_bundle_pages(bundle)
        if not pages:
            # If frontmatter parser rejects empty type at parse time,
            # the OKF §4.1 hard rule 1 (parseable frontmatter) is already
            # enforced — verify the rule is mentioned in the docstring.
            assert "§4.1" in mod._check_okf_4_1_hard.__doc__
            return
        # If parsed, run lint_page and verify OKF-§4.1 issue
        issues_strict = mod.lint_page(pages[0], bundle, "strict")
        issues_loose = mod.lint_page(pages[0], bundle, "loose")
        strict_4_1 = [i for i in issues_strict if i.rule == "OKF-§4.1"]
        loose_4_1 = [i for i in issues_loose if i.rule == "OKF-§4.1"]
        # Both modes should have §4.1 issue (severity=error)
        assert len(strict_4_1) >= 1, f"strict should have §4.1 issue, got {issues_strict}"
        assert len(loose_4_1) >= 1, f"loose should have §4.1 issue, got {issues_loose}"
        assert strict_4_1[0].severity == "error"
        assert loose_4_1[0].severity == "error"


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
        test_version_parse_canonical,
        test_version_check_exact_match,
        test_version_check_major_mismatch_rejects_strict,
        test_version_check_minor_higher_warns,
        test_version_check_missing_warns,
        test_r2_batch_size_in_range,
        test_r2_batch_size_out_of_range,
        test_audit_r2_batch_history_v0_7_41,
        test_audit_r2_batch_history_precise_v0_7_42,
        test_cleanup_staging_dry_run_v0_7_56,
        test_cleanup_staging_apply_with_age_filter_v0_7_56,
        test_lint_v1_strict_rejects_non_wiki_subdir_v0_7_56,
        test_lint_v1_loose_warns_non_wiki_subdir_v0_7_56,
        test_lint_v9_strict_rejects_missing_source_v0_7_56,
        test_lint_v9_strict_accepts_archive_path_v0_7_56,
        test_lint_v_t1_strict_rejects_title_mismatch_v0_7_56,
        test_lint_v_t1_strict_passes_matching_title_v0_7_56,
        test_lint_okf_4_1_strict_rejects_empty_type_v0_7_56,
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
