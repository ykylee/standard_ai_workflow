"""workflow_kit.okf_export helper smoke test (v0.7.33+, OKF PoC).

OKF v0.1 spec 의 frontmatter mapping (SPEC.md §4.1) + body rewriting (§5.1) 검증.
PoC 단계: 7 test 로 핵심 mapping + body rewrite + CLI 동작 검증.

Test list:
1. test_frontmatter_parse_minimal: minimal wiki frontmatter (type 만) 파싱
2. test_frontmatter_parse_full: 모든 field 가 있는 wiki frontmatter 파싱
3. test_frontmatter_parse_missing_type_raises: type 없으면 InvalidFrontmatterError
4. test_map_to_okf_field_order: SPEC.md §4.1 priority order (type → title → description → resource → tags → timestamp)
5. test_map_to_okf_derives_title_from_body: frontmatter 에 title 없을 때 body H1 에서 derive
6. test_rewrite_wiki_links: [[path]] → [text](../path.md), [[path#anchor]] → [text](../path.md#anchor)
7. test_export_wiki_to_okf_end_to_end: 1 page export → OKF spec required field + body link rewrite 검증
"""

from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
OKF_EXPORT = SOURCE_ROOT / "workflow_kit" / "okf_export.py"

def _import_okf_export():
    """okf_export module importlib 로 load. dataclass decorator 가
    sys.modules 에서 호출 module 을 lookup 하므로 명시적 register 필수."""
    import sys
    spec = importlib.util.spec_from_file_location("okf_export", str(OKF_EXPORT))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["okf_export"] = mod  # dataclass 가 require
    spec.loader.exec_module(mod)
    return mod


# --- Test 1: minimal frontmatter 파싱 ---


def test_frontmatter_parse_minimal() -> None:
    """type 만 있는 minimal wiki frontmatter 파싱."""
    mod = _import_okf_export()
    text = "---\ntype: concept\n---\n\n# Title\n\nbody\n"
    fm = mod.Frontmatter.parse(text)
    assert fm.type == "concept", f"type mismatch: {fm.type!r}"
    assert fm.status is None, f"status should be None, got {fm.status!r}"
    assert fm.title is None
    assert fm.related_pages == (), f"related_pages should be empty, got {fm.related_pages!r}"


# --- Test 2: 모든 field 가 있는 full frontmatter ---


def test_frontmatter_parse_full() -> None:
    """모든 field 가 있는 wiki frontmatter 파싱 — list field + bool field + nested 구조 확인."""
    mod = _import_okf_export()
    text = (
        "---\n"
        "type: decision\n"
        "status: accepted\n"
        "title: ADR-001\n"
        "description: 3-layer separation\n"
        "last_ingested_from: docs/architecture/ADR-001.md\n"
        "created: 2026-05-01\n"
        "updated: 2026-05-15\n"
        "related_pages: [concepts/foo, concepts/bar]\n"
        "tags: [architecture, layer]\n"
        "adr_id: ADR-001\n"
        "r9_skip: true\n"
        "---\n\n"
        "# ADR-001\n\nbody\n"
    )
    fm = mod.Frontmatter.parse(text)
    assert fm.type == "decision"
    assert fm.status == "accepted"
    assert fm.title == "ADR-001"
    assert fm.description == "3-layer separation"
    assert fm.last_ingested_from == "docs/architecture/ADR-001.md"
    assert fm.created == "2026-05-01"
    assert fm.updated == "2026-05-15"
    assert fm.related_pages == ("concepts/foo", "concepts/bar"), fm.related_pages
    assert fm.tags == ("architecture", "layer"), fm.tags
    assert fm.adr_id == "ADR-001"
    assert fm.r9_skip is True


# --- Test 3: type 없으면 에러 ---


def test_frontmatter_parse_missing_type_raises() -> None:
    """OKF §4.1 required: `type` field 없거나 비면 InvalidFrontmatterError."""
    mod = _import_okf_export()
    # no type at all
    try:
        mod.Frontmatter.parse("---\nstatus: active\n---\nbody\n")
    except mod.InvalidFrontmatterError as e:
        assert "type" in str(e).lower()
    else:
        raise AssertionError("expected InvalidFrontmatterError for missing type")
    # empty type
    try:
        mod.Frontmatter.parse("---\ntype: \"  \"\n---\nbody\n")
    except mod.InvalidFrontmatterError as e:
        assert "type" in str(e).lower()
    else:
        raise AssertionError("expected InvalidFrontmatterError for empty type")


# --- Test 4: mapping field order (SPEC.md §4.1 priority) ---


def test_map_to_okf_field_order() -> None:
    """OKF §4.1 priority: type → title → description → resource → tags → timestamp.

    본 test 는 serialize 결과의 frontmatter lines 순서 검증.
    """
    mod = _import_okf_export()
    fm = mod.Frontmatter.parse(
        "---\n"
        "type: concept\n"
        "title: Test\n"
        "description: test desc\n"
        "last_ingested_from: https://example.com/x.md\n"
        "tags: [a, b]\n"
        "updated: 2026-06-16\n"
        "status: active\n"
        "related_pages: [foo]\n"
        "r9_skip: true\n"
        "---\n\nbody\n"
    )
    mapping = mod.map_frontmatter_to_okf(fm)
    keys_in_order: list[str] = []
    for line in mapping.frontmatter_lines:
        if line == "---" or ":" not in line:
            continue
        key = line.split(":", 1)[0].strip()
        if key:
            keys_in_order.append(key)
    # priority: type, title, description, resource, tags, timestamp, then extensions
    expected_priority_prefix = ["type", "title", "description", "resource", "tags", "timestamp"]
    actual_priority_prefix = [k for k in keys_in_order if k in expected_priority_prefix]
    assert actual_priority_prefix == expected_priority_prefix, (
        f"OKF §4.1 priority order violated: {actual_priority_prefix}"
    )


# --- Test 5: title/description body derivation ---


def test_map_to_okf_derives_title_from_body() -> None:
    """frontmatter 에 title/description 없을 때 body H1 + 첫 prose paragraph 에서 derive."""
    mod = _import_okf_export()
    fm = mod.Frontmatter.parse(
        "---\n"
        "type: pattern\n"
        "status: active\n"
        "---\n\n"
        "# R4 Anchor Index\n"
        "\n"
        "A knowledge index needs merge-safe structure. Free-form prose causes permanent conflicts.\n"
        "\n"
        "## When to Use\n"
        "\n"
        "- Master knowledge catalogs\n"
    )
    body = "# R4 Anchor Index\n\nA knowledge index needs merge-safe structure. Free-form prose causes permanent conflicts.\n\n## When to Use\n"
    mapping = mod.map_frontmatter_to_okf(fm, body=body)
    lines_str = "\n".join(mapping.frontmatter_lines)
    assert "title: R4 Anchor Index" in lines_str, f"title not derived: {lines_str!r}"
    assert "A knowledge index needs merge-safe structure" in lines_str, (
        f"description not derived: {lines_str!r}"
    )


# --- Test 6: body link rewrite (§5.1) ---


def test_rewrite_wiki_links() -> None:
    """[[path/to/page]] → [text](../path/to/page.md), [[path#anchor]] → [text](../path/to/page.md#anchor)."""
    mod = _import_okf_export()
    body_in = (
        "See [[concepts/foo]] for details. "
        "Also [[concepts/bar#section-2]]. "
        "And [[entities/simple-entity]] here."
    )
    body_out = mod.rewrite_wiki_links_to_okf(body_in)
    assert "[foo](../concepts/foo.md)" in body_out, f"foo link not rewritten: {body_out!r}"
    assert "[bar](../concepts/bar.md#section-2)" in body_out, f"anchor link not rewritten: {body_out!r}"
    assert "[simple-entity](../entities/simple-entity.md)" in body_out, (
        f"entity link not rewritten: {body_out!r}"
    )
    # round-trip: no [[...]] remaining
    assert "[[" not in body_out and "]]" not in body_out, f"wiki link not fully rewritten: {body_out!r}"


# --- Test 7: end-to-end export ---


def test_export_wiki_to_okf_end_to_end() -> None:
    """1 page export — OKF spec required (`type` non-empty) + body link rewrite 검증."""
    mod = _import_okf_export()
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_root = Path(tmpdir) / "wiki"
        out_bundle = Path(tmpdir) / "bundle"
        wiki_root.mkdir()
        # make a fake wiki page with a body wiki-link
        page = wiki_root / "concepts"
        page.mkdir()
        wiki_page = page / "test-concept.md"
        wiki_page.write_text(
            "---\n"
            "type: concept\n"
            "status: active\n"
            "related_pages: [concepts/other]\n"
            "---\n\n"
            "# Test Concept\n\nbody line one\nbody line two\n\nSee [[concepts/other]] for related.\n",
            encoding="utf-8",
        )
        # make sibling concept that the link refers to (OKF tolerates broken links, but for completeness)
        (page / "other.md").write_text(
            "---\ntype: concept\nstatus: active\n---\n\n# Other\n", encoding="utf-8"
        )
        report = mod.export_wiki_to_okf(wiki_root, out_bundle)
        assert report.pages_exported == 2, f"exported count: {report.pages_exported}, errors: {report.errors}"
        out_page = out_bundle / "concepts" / "test-concept.md"
        assert out_page.exists(), f"output not created: {out_page}"
        out_text = out_page.read_text(encoding="utf-8")
        # OKF spec required: `type` field present, non-empty
        assert re.search(r"^type: \S+", out_text, re.MULTILINE), f"`type` field missing: {out_text!r}"
        # wiki-link rewritten
        assert "[[concepts/other]]" not in out_text
        assert "[other](../concepts/other.md)" in out_text
        # related_pages emit
        assert "related_pages" in out_text
        # See Also section emitted (from related_pages)
        assert "## See Also" in out_text


# --- 메인 실행 ---


def main() -> int:
    test_funcs = [
        test_frontmatter_parse_minimal,
        test_frontmatter_parse_full,
        test_frontmatter_parse_missing_type_raises,
        test_map_to_okf_field_order,
        test_map_to_okf_derives_title_from_body,
        test_rewrite_wiki_links,
        test_export_wiki_to_okf_end_to_end,
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
