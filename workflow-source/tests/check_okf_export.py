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

import contextlib
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


@contextlib.contextmanager
def _repo_containing(*relative_paths: str):
    """지정한 파일이 **실제로 존재하는** 임시 repo root 를 yield.

    §2.58 이후 `_derive_resource` 는 저장소에 없는 경로를 URL 로 만들지 않는다.
    그 전까지 이 파일의 pinning fixture 들은 `repo_root=Path("/fake")` 처럼 존재하지
    않는 root 를 넘기고 있었다 — 제품이 실제로 보는 모양이 아니었고, 그래서 없는
    경로가 URL 이 되는 결함을 이 검사들이 잡을 수 없었다. fixture 를 제품 쪽 모양으로
    맞춘다.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        for rel in relative_paths:
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("fixture\n", encoding="utf-8")
        yield root


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


# --- Test 8: OKF spec §4.1 full conformance ---


def test_okf_spec_4_1_full_conformance() -> None:
    """OKF SPEC.md §4.1 full conformance: 3 hard rule + 5 recommended field.

    Hard rule (§9 conformance):
    1. Every non-reserved `.md` file has parseable YAML frontmatter
    2. Every frontmatter has non-empty `type` field
    3. Reserved filenames (`index.md`, `log.md`) follow structure

    Recommended (priority order): type → title → description → resource → tags → timestamp

    본 test 는 export 된 bundle 의 모든 page 가 §4.1 conformance 충족 검증.
    """
    mod = _import_okf_export()
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_root = Path(tmpdir) / "wiki"
        out_bundle = Path(tmpdir) / "bundle"
        wiki_root.mkdir()
        # 3 page: 1 with full frontmatter, 1 minimal, 1 in different subdir
        (wiki_root / "concepts").mkdir()
        (wiki_root / "entities").mkdir()
        (wiki_root / "concepts" / "full.md").write_text(
            "---\n"
            "type: concept\n"
            "title: Full Page\n"
            "description: All fields populated.\n"
            "last_ingested_from: https://example.com/spec.md\n"
            "tags: [a, b]\n"
            "updated: 2026-06-16\n"
            "status: active\n"
            "---\n\n# Full Page\n\nbody\n",
            encoding="utf-8",
        )
        (wiki_root / "concepts" / "minimal.md").write_text(
            "---\ntype: concept\n---\n\n# Minimal\n\nbody\n",
            encoding="utf-8",
        )
        (wiki_root / "entities" / "entity.md").write_text(
            "---\ntype: entity\nstatus: active\n---\n\n# Entity\n\nbody\n",
            encoding="utf-8",
        )
        report = mod.export_wiki_to_okf(wiki_root, out_bundle)
        assert report.pages_exported == 3, f"exported count: {report.pages_exported}, errors: {report.errors}"
        assert not report.errors, f"export errors: {report.errors}"

        # verify every exported page meets §4.1 conformance
        for out_path in sorted(out_bundle.rglob("*.md")):
            # §6 index.md 는 reserved 이며 frontmatter 가 다름 (okf_version, generated_at, generator).
            # §4.1 hard rule 은 *non-reserved* page 에만 적용.
            if out_path.name == "index.md" and out_path.parent == out_bundle:
                # bundle-root index.md: OKF spec §6 + §11 형식 (okf_version field)
                text = out_path.read_text(encoding="utf-8")
                assert text.startswith("---\n"), f"index.md missing frontmatter: {out_path}"
                assert "okf_version" in text, f"index.md missing okf_version (SPEC §11): {out_path}"
                continue
            text = out_path.read_text(encoding="utf-8")
            # §4.1 hard rule 1: parseable YAML frontmatter (lines start with ---)
            assert text.startswith("---\n"), f"{out_path}: missing frontmatter"
            # §4.1 hard rule 2: non-empty `type` field
            type_match = re.search(r"^type: (\S.*)$", text, re.MULTILINE)
            assert type_match, f"{out_path}: missing `type` field"
            type_val = type_match.group(1).strip().strip('"').strip("'")
            assert type_val, f"{out_path}: empty `type` field"
            # §4.1 hard rule 3: reserved filename structure
            # (per-page index.md/log.md 는 우리 export 가 emit 안 함 — subdir 의 reserved 는 안 OK)
            assert out_path.name not in ("index.md", "log.md"), (
                f"{out_path}: reserved filename in concept export (subdir)"
            )

        # verify priority order (type → title → description → resource → tags → timestamp) for full page
        full_text = (out_bundle / "concepts" / "full.md").read_text(encoding="utf-8")
        # find positions of first occurrence
        priority = ["type", "title", "description", "resource", "tags", "timestamp"]
        positions: list[tuple[str, int]] = []
        for key in priority:
            m = re.search(rf"^{key}:", full_text, re.MULTILINE)
            if m:
                positions.append((key, m.start()))
        # sort by position
        positions.sort(key=lambda x: x[1])
        actual_order = [k for k, _ in positions]
        assert actual_order == priority, (
            f"OKF §4.1 priority order violated: {actual_order} != {priority}"
        )


# --- Test 9: bundle directory layout (reserved file isolation, subdir preservation) ---


def test_okf_bundle_directory_layout() -> None:
    """Bundle directory layout: reserved filename 격리 + subdirectory 보존.

    OKF SPEC.md §3.1: `index.md` 와 `log.md` 는 reserved. §2.2: directory hierarchy 보존.
    본 test 는 export 시:
    1. reserved filename (`index.md`, `log.md`) 이 wiki 의 reserved file 과 충돌 시 skip
    2. subdirectory hierarchy 보존
    3. 우리 wiki 의 SCHEMA.md / INGEST_GUIDE.md 같은 reserved file 도 skip
    """
    mod = _import_okf_export()
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_root = Path(tmpdir) / "wiki"
        out_bundle = Path(tmpdir) / "bundle"
        wiki_root.mkdir()
        # create SCHEMA.md (reserved) at wiki root + INGEST_GUIDE.md (reserved)
        (wiki_root / "SCHEMA.md").write_text("---\ntype: schema\n---\n\nschema\n", encoding="utf-8")
        (wiki_root / "INGEST_GUIDE.md").write_text("# Guide\n", encoding="utf-8")
        (wiki_root / "index.md").write_text("# Index\n", encoding="utf-8")
        (wiki_root / "log.md").write_text("# Log\n", encoding="utf-8")
        # nested subdirectories with pages
        (wiki_root / "concepts").mkdir()
        (wiki_root / "concepts" / "a.md").write_text(
            "---\ntype: concept\n---\n\n# A\n\nbody\n", encoding="utf-8"
        )
        (wiki_root / "concepts" / "sub").mkdir()
        (wiki_root / "concepts" / "sub" / "b.md").write_text(
            "---\ntype: concept\n---\n\n# B\n\nbody\n", encoding="utf-8"
        )
        (wiki_root / "decisions").mkdir()
        (wiki_root / "decisions" / "d.md").write_text(
            "---\ntype: decision\n---\n\n# D\n\nbody\n", encoding="utf-8"
        )
        report = mod.export_wiki_to_okf(wiki_root, out_bundle)
        # only 3 concept/decision pages exported, reserved + non-type-dir files skipped
        assert report.pages_exported == 3, (
            f"exported count: {report.pages_exported} (expected 3), errors: {report.errors}"
        )
        # reserved wiki-root files NOT in output
        assert not (out_bundle / "SCHEMA.md").exists(), "SCHEMA.md leaked to bundle"
        assert not (out_bundle / "INGEST_GUIDE.md").exists(), "INGEST_GUIDE.md leaked"
        # bundle-root index.md IS auto-emitted (OKF spec §6 + §11) — verify it has okf_version
        index_path = out_bundle / "index.md"
        assert index_path.exists(), "bundle-root index.md not auto-emitted"
        index_text = index_path.read_text(encoding="utf-8")
        assert "okf_version" in index_text, "bundle-root index.md missing okf_version"
        # log.md 는 export 가 emit 안 함 (별도 기능)
        assert not (out_bundle / "log.md").exists(), "log.md leaked (not emitted by our export)"
        # subdirectory hierarchy preserved
        assert (out_bundle / "concepts" / "a.md").exists(), "concepts/a.md missing"
        assert (out_bundle / "concepts" / "sub" / "b.md").exists(), "concepts/sub/b.md missing"
        assert (out_bundle / "decisions" / "d.md").exists(), "decisions/d.md missing"
        # exact file list: 3 concept/decision pages + 1 bundle-root index.md + 1 okf-bundle.yaml
        all_files = sorted(p.relative_to(out_bundle) for p in out_bundle.rglob("*") if p.is_file())
        expected = sorted(
            [
                Path("index.md"),
                Path("okf-bundle.yaml"),
                Path("concepts/a.md"),
                Path("concepts/sub/b.md"),
                Path("decisions/d.md"),
            ]
        )
        assert all_files == expected, f"layout mismatch:\n  got: {all_files}\n  expected: {expected}"


# --- Test 10: bundle root index.md auto-emit (OKF SPEC §6 + §11) ---


def test_okf_bundle_root_index_md_emit() -> None:
    """Bundle root `index.md` 자동 emit (OKF SPEC.md §6 + §11).

    §6: index.md MAY appear in any directory to enumerate contents.
    §11: bundle-root `index.md` frontmatter 의 `okf_version` 으로 spec version 선언.
    """
    mod = _import_okf_export()
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_root = Path(tmpdir) / "wiki"
        out_bundle = Path(tmpdir) / "bundle"
        wiki_root.mkdir()
        (wiki_root / "concepts").mkdir()
        (wiki_root / "concepts" / "alpha.md").write_text(
            "---\ntype: concept\nstatus: active\n---\n\n# Alpha\n\nbody\n",
            encoding="utf-8",
        )
        (wiki_root / "decisions").mkdir()
        (wiki_root / "decisions" / "beta.md").write_text(
            "---\ntype: decision\nstatus: active\n---\n\n# Beta\n\nbody\n",
            encoding="utf-8",
        )
        report = mod.export_wiki_to_okf(wiki_root, out_bundle)
        assert report.pages_exported == 2, f"got {report.pages_exported}, errors: {report.errors}"
        index_path = out_bundle / "index.md"
        assert index_path.exists(), "bundle-root index.md not auto-emitted"
        text = index_path.read_text(encoding="utf-8")
        # §11: okf_version field — 리터럴을 박지 않는다. 버전이 오를 때마다 여기가
        # red 가 되면 검사가 계약이 아니라 그 시점 상수를 지키게 된다.
        assert f'okf_version: "{mod.OKF_SPEC_VERSION}"' in text, (
            f"index.md missing okf_version field:\n{text}"
        )
        # generated_at + generator field
        assert "generated_at:" in text, "index.md missing generated_at"
        assert "generator:" in text, "index.md missing generator"
        # body: section heading per type + entries
        assert "## Concepts" in text, "index.md missing Concepts section"
        assert "## Decisions" in text, "index.md missing Decisions section"
        assert "alpha.md" in text, "index.md missing alpha.md entry"
        assert "beta.md" in text, "index.md missing beta.md entry"
        # bundle-root index.md 는 §4.1 hard rule 적용 안 됨 (no `type` field, has `okf_version`)
        assert "type:" not in text.split("---")[1], "index.md should NOT have `type` field (reserved)"


# --- ADR-026: OKF v0.2 이행 (status 어휘 · sources · legacy 병행) ---


def test_status_is_mapped_to_okf_vocabulary() -> None:
    """우리 `status` 가 v0.2 §5.4 어휘로 매핑되고 원문은 확장 키로 남는다.

    v0.1 에서 `status` 는 정규 필드가 아니어서 우리 값을 그대로 실어도 됐다.
    v0.2 에서 **정규 필드로 승격**되면서 사정이 달라졌다 — §11 의 관용 보장은
    *unknown key* 에만 걸리므로, `stable` 필터를 건 소비자는 `active`/`accepted`
    를 조용히 버린다.
    """
    mod = _import_okf_export()
    vocab = mod.OKF_STATUS_VOCABULARY
    cases = {"active": "stable", "accepted": "stable", "proposed": "draft",
             "draft": "draft", "deprecated": "deprecated", "superseded": "deprecated"}
    problems = []
    for ours, expected in cases.items():
        got = mod.map_status_to_okf(ours)
        if got != expected:
            problems.append(f"{ours} -> {got} (기대 {expected})")
        if got not in vocab:
            problems.append(f"{ours} -> {got} 이 v0.2 어휘 밖")
    # 어휘 밖 값은 stable 로 올리지 않는다 (부재 == stable 주장이므로 생략도 불가).
    unknown = mod.map_status_to_okf("완전히-모르는-값")
    if unknown != "draft":
        problems.append(f"unknown -> {unknown} (기대 draft)")
    assert not problems, "; ".join(problems)


def test_export_emits_mapped_status_and_preserves_ours() -> None:
    """export 산출물에 매핑된 `status` 와 원문 `wiki_status` 가 둘 다 있다."""
    mod = _import_okf_export()
    fm = mod.Frontmatter.parse("---\ntype: concept\nstatus: active\n---\n\n# T\n\nbody\n")
    mapping = mod.map_frontmatter_to_okf(fm, body="# T\n\nbody\n")
    text = "\n".join(mapping.frontmatter_lines)
    assert "status: stable" in text, text
    assert "wiki_status: active" in text, text


def test_export_emits_sources_for_in_repo_and_url() -> None:
    """`last_ingested_from` 이 `sources`(v0.2 §5.1)로 나간다 — in-repo 도 포함.

    v0.1 에서 in-repo 경로는 `resource` 로 못 나가고 본문 `# Citations` 산문으로만
    남았다. §5.1 은 entry 의 `resource` 로 번들 상대 경로/범위 서술도 허용하므로,
    in-repo 출처가 처음으로 기계가 읽는 필드에 들어간다.
    """
    mod = _import_okf_export()
    problems = []
    in_repo = mod.map_frontmatter_to_okf(
        mod.Frontmatter.parse(
            "---\ntype: concept\nlast_ingested_from: workflow-source/core/x.md\n---\n\n# T\n\nbody\n"
        ),
        body="# T\n\nbody\n", resolve=False,
    )
    in_repo_text = "\n".join(in_repo.frontmatter_lines)
    if "sources:" not in in_repo_text or "workflow-source/core/x.md" not in in_repo_text:
        problems.append(f"in-repo sources 누락:\n{in_repo_text}")
    # legacy 형태도 남아야 한다 (v0.1 소비자용, §13.1)
    if "# Citations" not in "\n".join(in_repo.body_suffix):
        problems.append("legacy # Citations 가 사라졌다")

    url = mod.map_frontmatter_to_okf(
        mod.Frontmatter.parse(
            "---\ntype: concept\nlast_ingested_from: https://example.com/a.md\n---\n\n# T\n\nbody\n"
        ),
        body="# T\n\nbody\n", resolve=False,
    )
    url_text = "\n".join(url.frontmatter_lines)
    if "sources:" not in url_text or "https://example.com/a.md" not in url_text:
        problems.append(f"URL sources 누락:\n{url_text}")
    assert not problems, "; ".join(problems)


def test_legacy_timestamp_is_kept_and_generated_is_not_fabricated() -> None:
    """`timestamp` 는 남기고 `generated` 는 **짓지 않는다**.

    §5.2 는 `generated.by` 를 REQUIRED 로 두는데 우리는 페이지별 actor 기록이
    없다. 도구 이름을 적으면 "이 도구가 내용을 썼다" 는 거짓이 되고, `human:` 을
    적으면 생성물 페이지까지 사람이 쓴 것이 된다. §13.1 의 `timestamp` fallback
    이 그 자리를 덮으므로 비워 두는 편이 정확하다.
    """
    mod = _import_okf_export()
    mapping = mod.map_frontmatter_to_okf(
        mod.Frontmatter.parse("---\ntype: concept\nupdated: 2026-08-20\n---\n\n# T\n\nbody\n"),
        body="# T\n\nbody\n",
    )
    text = "\n".join(mapping.frontmatter_lines)
    assert "timestamp:" in text, text
    assert "generated:" not in text, f"근거 없는 generated 를 냈다:\n{text}"


def test_consumer_docs_declare_the_canonical_version() -> None:
    """소비자 문서의 `okf_version` 예시가 **정본 상수**와 같다.

    이 두 문서는 아무 검사도 대조하지 않아서, 도구가 v0.2 를 내는 동안 문서만
    v0.1 을 말하고 있어도 아무도 몰랐을 자리다 (ADR-026 에서 실제로 그렇게 될
    뻔했다). 정본은 `OKF_SPEC_VERSION` 하나이고 문서는 파생이다.
    """
    mod = _import_okf_export()
    ours = mod.OKF_SPEC_VERSION
    docs = [
        SOURCE_ROOT.parent / "docs" / "OKF_CONSUMER_GUIDE.md",
        SOURCE_ROOT.parent / "docs" / "OKF_CONSUMER_QUICKSTART.md",
    ]
    problems = []
    for doc in docs:
        if not doc.exists():
            problems.append(f"{doc.name}: 문서 부재")
            continue
        text = doc.read_text(encoding="utf-8")
        declared = set(re.findall(r"""okf_version:\s*["']([0-9.]+)["']""", text))
        if not declared:
            problems.append(f"{doc.name}: okf_version 예시 없음")
            continue
        # 문서는 "우리가 내는 버전" 을 보여 주되, 하위 버전 수용을 **설명** 할 수 있다.
        # 그래서 정본이 예시에 **포함**돼야 한다는 것까지만 요구한다.
        if ours not in declared:
            problems.append(f"{doc.name}: 예시가 {sorted(declared)} — 정본 {ours} 없음")
    assert not problems, "; ".join(problems)


# --- Test 11: vcs_commit field → commit-pinned URL (ADR-018) ---


def test_vcs_commit_emits_pinned_url() -> None:
    """vcs_commit 명시 시 _derive_resource 가 commit-pinned URL emit (ADR-018)."""
    import importlib.util
    import sys
    # Patch via sys.modules BEFORE _derive_resource's lazy import
    pr_spec = importlib.util.spec_from_file_location(
        "workflow_kit.path_resolver", str(SOURCE_ROOT / "workflow_kit" / "path_resolver.py")
    )
    pr = importlib.util.module_from_spec(pr_spec)
    pr_spec.loader.exec_module(pr)
    sys.modules["workflow_kit.path_resolver"] = pr
    orig_url = pr.resolve_in_repo_path_to_url
    orig_pinned = pr.resolve_in_repo_path_to_url_pinned
    pr.resolve_in_repo_path_to_url = lambda path, root: "https://github.com/foo/bar/blob/main/" + path
    pr.resolve_in_repo_path_to_url_pinned = lambda path, root, commit_sha=None, ref=None: (
        f"https://github.com/foo/bar/blob/{commit_sha or ref}/" + path
    )
    try:
        mod = _import_okf_export()
        with _repo_containing("docs/spec.md") as repo_root:
            # in-repo path + vcs_commit → commit-pinned URL
            url = mod._derive_resource(
                "docs/spec.md", repo_root=repo_root, vcs_commit="abc1234"
            )
            assert url == "https://github.com/foo/bar/blob/abc1234/docs/spec.md", f"got {url!r}"
            # in-repo path + vcs_ref → ref-pinned URL
            url = mod._derive_resource(
                "docs/spec.md", repo_root=repo_root, vcs_ref="v0.7.37"
            )
            assert url == "https://github.com/foo/bar/blob/v0.7.37/docs/spec.md", f"got {url!r}"
            # 저장소에 없는 경로는 pinning 여부와 무관하게 URL 이 되지 않는다 (§2.58)
            missing = mod._derive_resource(
                "docs/does-not-exist.md", repo_root=repo_root, vcs_commit="abc1234"
            )
            assert missing is None, f"없는 경로가 URL 이 됐다: {missing!r}"
        # URL form unchanged (vcs_commit ignored)
        url = mod._derive_resource("https://example.com/spec.md")
        assert url == "https://example.com/spec.md", f"got {url!r}"
    finally:
        pr.resolve_in_repo_path_to_url = orig_url
        pr.resolve_in_repo_path_to_url_pinned = orig_pinned


def test_per_page_frontmatter_vcs_commit() -> None:
    """per-page frontmatter `vcs_commit` field → commit-pinned URL emit (ADR-018 follow-up)."""
    import importlib.util
    import sys
    pr_spec = importlib.util.spec_from_file_location(
        "workflow_kit.path_resolver", str(SOURCE_ROOT / "workflow_kit" / "path_resolver.py")
    )
    pr = importlib.util.module_from_spec(pr_spec)
    pr_spec.loader.exec_module(pr)
    sys.modules["workflow_kit.path_resolver"] = pr
    orig_url = pr.resolve_in_repo_path_to_url
    orig_pinned = pr.resolve_in_repo_path_to_url_pinned
    pr.resolve_in_repo_path_to_url = lambda path, root: (
        "https://github.com/foo/bar/blob/main/" + path
    )
    pr.resolve_in_repo_path_to_url_pinned = lambda path, root, commit_sha=None, ref=None: (
        f"https://github.com/foo/bar/blob/{commit_sha or ref}/" + path
    )
    mod = _import_okf_export()
    try:
        # parse frontmatter with vcs_commit field
        text = (
            "---\n"
            "type: concept\n"
            "status: active\n"
            "last_ingested_from: workflow-source/docs/spec.md\n"
            "vcs_commit: deadbeef\n"
            "---\n\n"
            "# Title\n\nbody\n"
        )
        fm = mod.Frontmatter.parse(text)
        assert fm.vcs_commit == "deadbeef", f"vcs_commit parse failed: {fm.vcs_commit!r}"
        # call _derive_resource with fm.vcs_commit (per-page frontmatter precedence)
        with _repo_containing("workflow-source/docs/spec.md") as repo_root:
            url = mod._derive_resource(
                fm.last_ingested_from, repo_root=repo_root, vcs_commit=fm.vcs_commit,
            )
        assert url == "https://github.com/foo/bar/blob/deadbeef/workflow-source/docs/spec.md", (
            f"got {url!r}"
        )
    finally:
        pr.resolve_in_repo_path_to_url = orig_url
        pr.resolve_in_repo_path_to_url_pinned = orig_pinned


def test_tag_based_pinning_v0_7_37() -> None:
    """vcs_ref=release tag (e.g. 'v0.7.37') → ref-pinned URL (ADR-018 v2)."""
    import importlib.util
    import sys
    pr_spec = importlib.util.spec_from_file_location(
        "workflow_kit.path_resolver", str(SOURCE_ROOT / "workflow_kit" / "path_resolver.py")
    )
    pr = importlib.util.module_from_spec(pr_spec)
    pr_spec.loader.exec_module(pr)
    sys.modules["workflow_kit.path_resolver"] = pr
    orig_url = pr.resolve_in_repo_path_to_url
    orig_pinned = pr.resolve_in_repo_path_to_url_pinned
    pr.resolve_in_repo_path_to_url = lambda path, root: (
        "https://github.com/foo/bar/blob/main/" + path
    )
    pr.resolve_in_repo_path_to_url_pinned = lambda path, root, commit_sha=None, ref=None: (
        f"https://github.com/foo/bar/blob/{commit_sha or ref}/" + path
    )
    mod = _import_okf_export()
    try:
        with _repo_containing("docs/spec.md") as repo_root:
            # release tag v0.7.37 → ref-pinned URL
            url = mod._derive_resource(
                "docs/spec.md", repo_root=repo_root, vcs_ref="v0.7.37"
            )
            assert url == "https://github.com/foo/bar/blob/v0.7.37/docs/spec.md", f"got {url!r}"
            # branch name "main"
            url = mod._derive_resource(
                "docs/spec.md", repo_root=repo_root, vcs_ref="main"
            )
            assert url == "https://github.com/foo/bar/blob/main/docs/spec.md", f"got {url!r}"
            # feature/branch with / → mocked ref always succeeds, so the real path_resolver
            # would reject it. With our mock, ref is interpolated as-is. Test that the mock
            # produces a URL with the ref embedded.
            url = mod._derive_resource(
                "docs/spec.md", repo_root=repo_root, vcs_ref="feature/okf-export"
            )
            assert url == "https://github.com/foo/bar/blob/feature/okf-export/docs/spec.md", f"got {url!r}"
    finally:
        pr.resolve_in_repo_path_to_url = orig_url
        pr.resolve_in_repo_path_to_url_pinned = orig_pinned


def test_okf_bundle_manifest_emits_v0_7_38() -> None:
    """v0.7.38+: okf-bundle.yaml emit with per-bundle vcs_commit + integrity_hash (ADR-019)."""
    mod = _import_okf_export()
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_root = Path(tmpdir) / "wiki"
        out_bundle = Path(tmpdir) / "bundle"
        wiki_root.mkdir()
        (wiki_root / "concepts").mkdir()
        (wiki_root / "concepts" / "a.md").write_text(
            "---\ntype: concept\n---\n\n# A\n\nbody\n", encoding="utf-8"
        )
        (wiki_root / "decisions").mkdir()
        (wiki_root / "decisions" / "d.md").write_text(
            "---\ntype: decision\n---\n\n# D\n\nbody\n", encoding="utf-8"
        )
        report = mod.export_wiki_to_okf(
            wiki_root, out_bundle, vcs_commit="abc1234def", vcs_ref="v0.7.38"
        )
        assert report.pages_exported == 2
        manifest_path = out_bundle / "okf-bundle.yaml"
        assert manifest_path.exists(), "okf-bundle.yaml not emitted"
        text = manifest_path.read_text(encoding="utf-8")
        assert "okf_version: '0.1'" in text, f"missing okf_version: {text}"
        assert "vcs_commit: 'abc1234def'" in text, f"missing vcs_commit: {text}"
        assert "vcs_ref: 'v0.7.38'" in text, f"missing vcs_ref: {text}"
        assert "integrity_hash: 'sha256:" in text, f"missing integrity_hash: {text}"
        assert "page_count: 2" in text, f"missing page_count: {text}"


def test_okf_bundle_manifest_skip_emit() -> None:
    """v0.7.38+: emit_manifest=False skips okf-bundle.yaml emit (escape hatch)."""
    mod = _import_okf_export()
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_root = Path(tmpdir) / "wiki"
        out_bundle = Path(tmpdir) / "bundle"
        wiki_root.mkdir()
        (wiki_root / "concepts").mkdir()
        (wiki_root / "concepts" / "a.md").write_text(
            "---\ntype: concept\n---\n\n# A\n\nbody\n", encoding="utf-8"
        )
        report = mod.export_wiki_to_okf(wiki_root, out_bundle, emit_manifest=False)
        assert report.pages_exported == 1
        assert not (out_bundle / "okf-bundle.yaml").exists(), "okf-bundle.yaml should not exist"


def test_okf_resource_content_hash_v0_7_39() -> None:
    """v0.7.39+: content_hash='auto' appends ?hash=sha256:<hex> to resource URL (ADR-019 layer 1)."""
    mod = _import_okf_export()
    import importlib.util
    import sys as _sys
    pr_spec = importlib.util.spec_from_file_location(
        "workflow_kit.path_resolver", str(SOURCE_ROOT / "workflow_kit" / "path_resolver.py")
    )
    pr = importlib.util.module_from_spec(pr_spec)
    pr_spec.loader.exec_module(pr)
    _sys.modules["workflow_kit.path_resolver"] = pr
    orig_url = pr.resolve_in_repo_path_to_url
    orig_pinned = pr.resolve_in_repo_path_to_url_pinned
    pr.resolve_in_repo_path_to_url = lambda p, r: "https://github.com/foo/bar/blob/main/" + p.lstrip("./")
    pr.resolve_in_repo_path_to_url_pinned = lambda p, r, commit_sha=None, ref=None: (
        f"https://github.com/foo/bar/blob/{commit_sha or ref or 'main'}/{p.lstrip('./')}"
    )
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_root = Path(tmpdir) / "wiki"
            out_bundle = Path(tmpdir) / "bundle"
            wiki_root.mkdir()
            (wiki_root / "concepts").mkdir()
            (wiki_root / "concepts" / "h.md").write_text(
                "---\ntype: concept\nlast_ingested_from: ./docs/spec.md\n---\n\n# H\n\nbody\n",
                encoding="utf-8",
            )
            # §2.58: 참조 대상이 저장소에 실재해야 `resource` 가 만들어진다.
            (Path(tmpdir) / "docs").mkdir()
            (Path(tmpdir) / "docs" / "spec.md").write_text("spec\n", encoding="utf-8")
            # auto-compute content hash from full page text
            mod.export_wiki_to_okf(wiki_root, out_bundle, content_hash="auto", repo_root=Path(tmpdir))
            text = (out_bundle / "concepts" / "h.md").read_text(encoding="utf-8")
            assert "hash=sha256:" in text, f"missing hash query param: {text}"
            import re
            m = re.search(r"hash=(sha256:[0-9a-f]{64})", text)
            assert m, f"hash format wrong: {text}"
    finally:
        pr.resolve_in_repo_path_to_url = orig_url
        pr.resolve_in_repo_path_to_url_pinned = orig_pinned


def test_okf_resource_range_refs_v0_7_40() -> None:
    """v0.7.40+: range_refs=(sha1, sha2) appends ?range=<sha1>..<sha2> to resource URL (ADR-019 layer 2)."""
    mod = _import_okf_export()
    import importlib.util
    import sys as _sys
    pr_spec = importlib.util.spec_from_file_location(
        "workflow_kit.path_resolver", str(SOURCE_ROOT / "workflow_kit" / "path_resolver.py")
    )
    pr = importlib.util.module_from_spec(pr_spec)
    pr_spec.loader.exec_module(pr)
    _sys.modules["workflow_kit.path_resolver"] = pr
    orig_url = pr.resolve_in_repo_path_to_url
    orig_pinned = pr.resolve_in_repo_path_to_url_pinned
    pr.resolve_in_repo_path_to_url = lambda p, r: "https://github.com/foo/bar/blob/main/" + p.lstrip("./")
    pr.resolve_in_repo_path_to_url_pinned = lambda p, r, commit_sha=None, ref=None: (
        f"https://github.com/foo/bar/blob/{commit_sha or ref or 'main'}/{p.lstrip('./')}"
    )
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_root = Path(tmpdir) / "wiki"
            out_bundle = Path(tmpdir) / "bundle"
            wiki_root.mkdir()
            (wiki_root / "concepts").mkdir()
            (Path(tmpdir) / "docs").mkdir()
            (Path(tmpdir) / "docs" / "spec.md").write_text("spec\n", encoding="utf-8")
            (wiki_root / "concepts" / "r.md").write_text(
                "---\ntype: concept\nlast_ingested_from: ./docs/spec.md\n---\n\n# R\n\nbody\n",
                encoding="utf-8",
            )
            mod.export_wiki_to_okf(
                wiki_root, out_bundle,
                range_refs=("aaa1111", "fffeeee"),
                repo_root=Path(tmpdir),
            )
            text = (out_bundle / "concepts" / "r.md").read_text(encoding="utf-8")
            assert "range=aaa1111..fffeeee" in text, f"missing range query param: {text}"
    finally:
        pr.resolve_in_repo_path_to_url = orig_url
        pr.resolve_in_repo_path_to_url_pinned = orig_pinned


def test_okf_resource_layer1_layer2_composite_v0_7_42() -> None:
    """v0.7.42+: composite URL emission with both ?hash= (layer 1) and ?range= (layer 2) carriers."""
    mod = _import_okf_export()
    import importlib.util
    import sys as _sys
    pr_spec = importlib.util.spec_from_file_location(
        "workflow_kit.path_resolver", str(SOURCE_ROOT / "workflow_kit" / "path_resolver.py")
    )
    pr = importlib.util.module_from_spec(pr_spec)
    pr_spec.loader.exec_module(pr)
    _sys.modules["workflow_kit.path_resolver"] = pr
    orig_url = pr.resolve_in_repo_path_to_url
    orig_pinned = pr.resolve_in_repo_path_to_url_pinned
    pr.resolve_in_repo_path_to_url = lambda p, r: "https://github.com/foo/bar/blob/main/" + p.lstrip("./")
    pr.resolve_in_repo_path_to_url_pinned = lambda p, r, commit_sha=None, ref=None: (
        f"https://github.com/foo/bar/blob/{commit_sha or ref or 'main'}/{p.lstrip('./')}"
    )
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_root = Path(tmpdir) / "wiki"
            out_bundle = Path(tmpdir) / "bundle"
            wiki_root.mkdir()
            (wiki_root / "concepts").mkdir()
            (Path(tmpdir) / "docs").mkdir()
            (Path(tmpdir) / "docs" / "spec.md").write_text("spec\n", encoding="utf-8")
            (wiki_root / "concepts" / "c.md").write_text(
                "---\ntype: concept\nlast_ingested_from: ./docs/spec.md\n---\n\n# C\n\nbody\n",
                encoding="utf-8",
            )
            # composite: both content_hash (auto) + range_refs
            import hashlib
            sha256 = hashlib.sha256(b"test").hexdigest()
            mod.export_wiki_to_okf(
                wiki_root, out_bundle,
                content_hash=f"sha256:{sha256}",
                range_refs=("aaa1111", "fffeeee"),
                repo_root=Path(tmpdir),
            )
            text = (out_bundle / "concepts" / "c.md").read_text(encoding="utf-8")
            # Both query params present (in any order, joined by ? or &)
            assert "hash=sha256:" in text, f"missing layer 1: {text}"
            assert "range=aaa1111..fffeeee" in text, f"missing layer 2: {text}"
            # The two carriers are joined by '&' separator
            assert "hash=" in text and "&range=" in text, f"composite URL not properly joined: {text}"
    finally:
        pr.resolve_in_repo_path_to_url = orig_url
        pr.resolve_in_repo_path_to_url_pinned = orig_pinned

def test_citations_heading_is_h1_spec_8() -> None:
    """Citations 절은 **h1 `# Citations`** 다 (SPEC §8).

    2026-08-18 실측 (TASK-2026-08-18-main-006): 우리는 `##` (h2) 로 내고 있었고
    18 cases 중 어느 것도 그 자리를 재지 않았다. SPEC v0.2 는 이 절을 `sources`
    frontmatter 로 대체하면서 "consumers ... MAY still parse a legacy
    `# Citations` body list for v0.1 documents" 라고 적었다 — h2 로 내면 v0.1
    에서도 비표준이고 v0.2 소비자의 **legacy fallback 경로에서도 안 걸린다**.
    """
    with tempfile.TemporaryDirectory(prefix="okf-cit-") as tmp:
        wiki = Path(tmp) / "wiki"
        (wiki / "concepts").mkdir(parents=True)
        (wiki / "concepts" / "p.md").write_text(
            "---\ntype: concept\ntitle: P\nlast_ingested_from: docs/x.md\n---\n\n# P\n\n본문\n",
            encoding="utf-8",
        )
        out = Path(tmp) / "bundle"
        _import_okf_export().export_wiki_to_okf(wiki, out, resolve=False)
        body = (out / "concepts" / "p.md").read_text(encoding="utf-8")
        assert "\n# Citations\n" in body, f"h1 Citations 가 없다:\n{body[-300:]}"
        assert "\n## Citations\n" not in body, "h2 로 냈다 — SPEC §8 은 h1 이다"


def test_every_wiki_page_exports_self_application() -> None:
    """**자기 적용.** 이 저장소의 wiki 가 한 장도 빠짐없이 export 되는가.

    2026-08-18 실측: `concepts/wiki-maintainability-score.md` 가 frontmatter 없이
    생성돼 `no frontmatter` 로 **조용히 빠지고 있었다** (71장 중 70장만 export).
    wiki lint 는 V-1(위치)·V-4(index) 만 보므로 아무도 몰랐다 — export 가 곧
    frontmatter 계약의 실사용 검증이다.
    """
    wiki = SOURCE_ROOT.parent / "ai-workflow" / "wiki"
    if not wiki.is_dir():
        print("  SKIP  wiki 부재")
        return
    with tempfile.TemporaryDirectory(prefix="okf-self-") as tmp:
        report = _import_okf_export().export_wiki_to_okf(
            wiki, Path(tmp) / "bundle", resolve=False)
        assert not report.errors, (
            f"export 되지 않은 wiki 페이지 {len(report.errors)}건:\n  "
            + "\n  ".join(report.errors[:5])
        )
        assert report.pages_exported > 0


def main() -> int:
    test_funcs = [
        test_frontmatter_parse_minimal,
        test_frontmatter_parse_full,
        test_frontmatter_parse_missing_type_raises,
        test_map_to_okf_field_order,
        test_map_to_okf_derives_title_from_body,
        test_rewrite_wiki_links,
        test_export_wiki_to_okf_end_to_end,
        test_okf_spec_4_1_full_conformance,
        test_okf_bundle_directory_layout,
        test_okf_bundle_root_index_md_emit,
        test_consumer_docs_declare_the_canonical_version,
        test_status_is_mapped_to_okf_vocabulary,
        test_export_emits_mapped_status_and_preserves_ours,
        test_export_emits_sources_for_in_repo_and_url,
        test_legacy_timestamp_is_kept_and_generated_is_not_fabricated,
        test_vcs_commit_emits_pinned_url,
        test_per_page_frontmatter_vcs_commit,
        test_tag_based_pinning_v0_7_37,
        test_okf_bundle_manifest_emits_v0_7_38,
        test_okf_bundle_manifest_skip_emit,
        test_okf_resource_content_hash_v0_7_39,
        test_okf_resource_range_refs_v0_7_40,
        test_okf_resource_layer1_layer2_composite_v0_7_42,
        test_citations_heading_is_h1_spec_8,
        test_every_wiki_page_exports_self_application,
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
