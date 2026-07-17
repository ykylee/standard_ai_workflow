#!/usr/bin/env python3
"""Smoke test — Harness apply_guide.md content cross-validation (v0.15.13+).

10 harness (codex, opencode, gemini-cli, antigravity, minimax-code, claude-code,
aider, goose, pi-dev, codewhale) 의 `apply_guide.md` content 정합 검증.

4 cases:
  1) **frontmatter 정합**: 10 harness 모두 `문서 목적` / `범위` / `대상 독자` /
     `상태` / `최종 수정일` 5 field 의 bullet point 정합.
  2) **chapter 구조**: 10 harness 모두 `## N.` 형태 의 chapter 섹션 ≥ 1 정합.
  3) **content size**: 각 apply_guide.md ≥ 80 line (non-trivial content 정공법).
  4) **related docs**: `관련 문서` line 의 상대 path (e.g. `./README.md`,
     `../../core/...`) 가 file system 에 존재 + maturity_matrix.harnesses.supported
     와 3-way set 동등성.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
HARNESSES_DIR = SOURCE_ROOT / "harnesses"
MATURITY_PATH = SOURCE_ROOT / "core" / "maturity_matrix.json"

# 10 harness 정공법 (v0.15.9 smoke 와 동일)
EXPECTED_HARNESSES = {
    "codex", "opencode", "gemini-cli", "antigravity", "minimax-code",
    "claude-code", "aider", "goose", "pi-dev", "codewhale",
}

REQUIRED_FRONTMATTER_FIELDS = [
    "문서 목적", "범위", "대상 독자", "상태", "최종 수정일",
]

CHAPTER_RE = re.compile(r"^##\s+\d+\.\s+", re.MULTILINE)
RELATED_DOCS_RE = re.compile(r"관련\s+문서\s*:\s*(.*)$", re.MULTILINE)
PATH_RE = re.compile(r"([./][\w/\-_.]+\.md)")


def _load_maturity() -> dict:
    if not MATURITY_PATH.is_file():
        raise AssertionError(f"maturity_matrix 부재: {MATURITY_PATH}")
    return json.loads(MATURITY_PATH.read_text(encoding="utf-8"))


def _load_apply_guide(name: str) -> str | None:
    f = HARNESSES_DIR / name / "apply_guide.md"
    if not f.is_file():
        return None
    return f.read_text(encoding="utf-8")


def case_1_frontmatter() -> bool:
    """1) frontmatter 정합: 5 field 모두 bullet point 로 정공법."""
    missing_field: dict[str, list[str]] = {f: [] for f in REQUIRED_FRONTMATTER_FIELDS}
    for name in EXPECTED_HARNESSES:
        content = _load_apply_guide(name)
        if content is None:
            print(f"  FAIL: {name}/apply_guide.md 부재")
            return False
        for field in REQUIRED_FRONTMATTER_FIELDS:
            # bullet point 로 등장해야 함 (예: '- 문서 목적: ...')
            if not re.search(rf"^-\s+{re.escape(field)}\s*:", content, re.MULTILINE):
                missing_field[field].append(name)
    failures = {f: hs for f, hs in missing_field.items() if hs}
    if failures:
        print(f"  FAIL: frontmatter field 부재: {failures}")
        return False
    print(f"  [info] 10 harness 모두 5 frontmatter field 정공법 정합")
    return True


def case_2_chapter_structure() -> bool:
    """2) chapter 구조: 10 harness 모두 `## N.` chapter ≥ 1 정합."""
    no_chapter: list[str] = []
    chapter_counts: dict[str, int] = {}
    for name in EXPECTED_HARNESSES:
        content = _load_apply_guide(name)
        if content is None:
            no_chapter.append(f"{name}(file 부재)")
            continue
        matches = CHAPTER_RE.findall(content)
        chapter_counts[name] = len(matches)
        if len(matches) == 0:
            no_chapter.append(name)
    if no_chapter:
        print(f"  FAIL: chapter 구조 부재: {no_chapter}")
        return False
    print(f"  [info] 10 harness chapter counts: {dict(sorted(chapter_counts.items()))}")
    return True


def case_3_content_size() -> bool:
    """3) content size: 각 apply_guide.md ≥ 80 line (non-trivial content 정공법)."""
    too_short: dict[str, int] = {}
    for name in EXPECTED_HARNESSES:
        content = _load_apply_guide(name)
        if content is None:
            too_short[name] = 0
            continue
        line_count = len(content.splitlines())
        if line_count < 80:
            too_short[name] = line_count
    if too_short:
        print(f"  FAIL: apply_guide.md < 80 line: {too_short}")
        return False
    print(f"  [info] 10 harness 모두 ≥ 80 line 정공법 정합")
    return True


def case_4_related_docs() -> bool:
    """4) related docs: 정공법 (./README.md 또는 ../../core/...) file 존재 + 3-way set 동등성."""
    # 4a: 각 apply_guide.md 의 '관련 문서' line 의 path 가 file system 에 존재
    unresolved: dict[str, list[str]] = {}
    for name in EXPECTED_HARNESSES:
        content = _load_apply_guide(name)
        if content is None:
            continue
        m = RELATED_DOCS_RE.search(content)
        if not m:
            unresolved[name] = ["(관련 문서 line 부재)"]
            continue
        related_line = m.group(1)
        # path 추출 (markdown link 또는 raw path)
        paths = PATH_RE.findall(related_line)
        if not paths:
            unresolved[name] = ["(path 추출 실패)"]
            continue
        # 각 path 의 file system 정합
        harness_dir = HARNESSES_DIR / name
        missing: list[str] = []
        for p in paths:
            # absolute path resolve (md link 의 경우 url 일 수 있어, ./ 로 시작하는 것만)
            if not p.startswith("./") and not p.startswith("../") and not p.startswith("/"):
                # URL 또는 external link → skip
                continue
            target = (harness_dir / p).resolve()
            if not target.is_file():
                missing.append(p)
        if missing:
            unresolved[name] = missing
    if unresolved:
        print(f"  FAIL: related docs path 부재: {unresolved}")
        return False
    # 4b: 3-way set 동등성 (Panel 2 names = mm = file system)
    panel_2 = json.loads(__import__("subprocess").run(
        [sys.executable, "-m", "workflow_kit.workflow_kit_cli",
         "--command=dashboard", "--format=json"],
        cwd=str(REPO_ROOT),
        env={"PYTHONPATH": str(SOURCE_ROOT), "PATH": __import__("os").environ.get("PATH", "")},
        capture_output=True, text=True, timeout=60,
    ).stdout)
    p2_names = set(panel_2["panels"]["maturity_distribution"]["harnesses"].get("supported_names", []))
    mm = _load_maturity()
    mm_names = set(mm.get("harnesses", {}).get("supported", []))
    fs_names: set[str] = set()
    EXCLUDED = {"_template", "custom"}
    for entry in HARNESSES_DIR.iterdir():
        if entry.is_dir() and not entry.name.startswith(("_", ".")) and entry.name not in EXCLUDED:
            fs_names.add(entry.name)
    if not (p2_names == mm_names == fs_names):
        print(f"  FAIL: 3-way set 불일치 — p2={p2_names}, mm={mm_names}, fs={fs_names}")
        return False
    print(f"  [info] 10 harness related docs 정합 + 3-way set 동등 (10 harness)")
    return True


def main() -> int:
    cases = [
        ("case_1_frontmatter", case_1_frontmatter),
        ("case_2_chapter_structure", case_2_chapter_structure),
        ("case_3_content_size", case_3_content_size),
        ("case_4_related_docs", case_4_related_docs),
    ]
    results: list[tuple[str, bool]] = []
    for name, fn in cases:
        results.append((name, fn()))
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {name}")
    print(f"\n=== {passed}/{len(cases)} PASS ===")
    if passed != len(cases):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
