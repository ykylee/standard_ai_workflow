"""v0.9.2 purpose.md concept 흡수 verification test.

Acceptance criteria (workflow-source/core/llm_wiki_concept_purpose_spec.md §5):
1. PURPOSE.md exists, §1~§4 4-element section 모두 non-empty
2. PURPOSE.md frontmatter `purpose_version: 1` + `last_purpose_review` (date) 명시
3. PROJECT_PROFILE.md §0 에 PURPOSE.md 참조 추가
4. 4-element content structural verify:
   - Goals G1+ (≥3)
   - Key Questions Q1+ (3-5)
   - Research Scope 포함/제외 영역
   - Evolving Thesis hypothesis / 가설 명시
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ACTIVE_DIR = Path(__file__).resolve().parents[2] / "ai-workflow" / "memory" / "active"
PURPOSE_PATH = ACTIVE_DIR / "PURPOSE.md"
PROFILE_PATH = ACTIVE_DIR / "PROJECT_PROFILE.md"


def test_purpose_file_exists_v0_9_2() -> None:
    """Acceptance §5 #1: PURPOSE.md exists."""
    assert PURPOSE_PATH.exists(), f"PURPOSE.md not found at {PURPOSE_PATH}"


def test_purpose_4_element_sections_v0_9_2() -> None:
    """Acceptance §5 #1: §1~§4 4-element sections 모두 non-empty."""
    src = PURPOSE_PATH.read_text()
    for sec in (
        "## 1. Goals",
        "## 2. Key Questions",
        "## 3. Research Scope",
        "## 4. Evolving Thesis",
    ):
        assert sec in src, f"section {sec!r} missing in PURPOSE.md"
    # each section must have non-empty content (skip sub-section headings)
    section_starts = [
        ("## 1. Goals", "## 2. Key Questions"),
        ("## 2. Key Questions", "## 3. Research Scope"),
        ("## 3. Research Scope", "## 4. Evolving Thesis"),
        ("## 4. Evolving Thesis", None),
    ]
    for start, end in section_starts:
        body = src.split(start, 1)[1]
        if end is not None:
            body = body.split(end, 1)[0]
        non_empty = [
            line
            for line in body.split("\n")
            if line.strip() and not line.startswith("## ") and not line.startswith("### ")
        ]
        assert non_empty, f"section {start!r} is empty"


def test_purpose_frontmatter_v0_9_2() -> None:
    """Acceptance §5 #2: frontmatter `purpose_version: 1` + `last_purpose_review` (YYYY-MM-DD)."""
    src = PURPOSE_PATH.read_text()
    m = re.match(r"^---\n(.+?)\n---", src, re.S)
    assert m is not None, "PURPOSE.md frontmatter missing"
    fm = m.group(1)
    assert "purpose_version" in fm, "purpose_version missing in frontmatter"
    assert re.search(r"purpose_version\s*:\s*1\b", fm), "purpose_version must be 1"
    assert "last_purpose_review" in fm, "last_purpose_review missing in frontmatter"
    assert re.search(
        r"last_purpose_review\s*:\s*\d{4}-\d{2}-\d{2}", fm
    ), "last_purpose_review must be YYYY-MM-DD date"


def test_project_profile_purpose_reference_v0_9_2() -> None:
    """Acceptance §5 #3: PROJECT_PROFILE.md §0 에 PURPOSE.md 참조 추가."""
    assert PROFILE_PATH.exists(), f"PROJECT_PROFILE.md not found at {PROFILE_PATH}"
    src = PROFILE_PATH.read_text()
    assert "## 0. Purpose 참조" in src, "PROJECT_PROFILE.md missing §0 Purpose 참조"
    assert "PURPOSE.md" in src, "PROJECT_PROFILE.md §0 missing PURPOSE.md reference"


def test_goals_minimum_count_v0_9_2() -> None:
    """Acceptance §5 #4: Goals has G1+ (≥3 goals)."""
    src = PURPOSE_PATH.read_text()
    goals_section = src.split("## 1. Goals", 1)[1].split("## 2. Key Questions", 1)[0]
    g_count = len(re.findall(r"-\s+\*\*G\d+\*\*\s*:", goals_section))
    assert g_count >= 3, f"Goals must have ≥3 (G1+), got {g_count}"


def test_key_questions_minimum_count_v0_9_2() -> None:
    """Acceptance §5 #4: Key Questions has Q1+ (3-5 questions)."""
    src = PURPOSE_PATH.read_text()
    q_section = src.split("## 2. Key Questions", 1)[1].split("## 3. Research Scope", 1)[0]
    q_count = len(re.findall(r"-\s+\*\*Q\d+\*\*\s*:", q_section))
    assert 3 <= q_count <= 5, f"Key Questions must be 3-5, got {q_count}"


def test_research_scope_include_exclude_v0_9_2() -> None:
    """Acceptance §5 #4: Research Scope has 포함/제외 영역 both."""
    src = PURPOSE_PATH.read_text()
    scope_section = src.split("## 3. Research Scope", 1)[1].split(
        "## 4. Evolving Thesis", 1
    )[0]
    assert "### 포함 영역" in scope_section, "Research Scope missing 포함 영역"
    assert "### 제외 영역" in scope_section, "Research Scope missing 제외 영역"
    include = scope_section.split("### 포함 영역", 1)[1].split("### 제외 영역", 1)[0]
    exclude = scope_section.split("### 제외 영역", 1)[1]
    assert re.search(r"-\s+", include), "포함 영역 must have ≥1 item"
    assert re.search(r"-\s+", exclude), "제외 영역 must have ≥1 item"


def test_evolving_thesis_hypothesis_v0_9_2() -> None:
    """Acceptance §5 #4: Evolving Thesis mentions hypothesis / 가설."""
    src = PURPOSE_PATH.read_text()
    thesis_section = src.split("## 4. Evolving Thesis", 1)[1]
    non_empty = [
        line
        for line in thesis_section.split("\n")
        if line.strip() and not line.startswith("## ")
    ]
    assert non_empty, "Evolving Thesis is empty"
    assert "hypothesis" in thesis_section.lower() or "가설" in thesis_section, (
        "Evolving Thesis must mention 'hypothesis' or '가설' (working hypothesis 명시)"
    )


def main() -> int:
    test_funcs = [
        test_purpose_file_exists_v0_9_2,
        test_purpose_4_element_sections_v0_9_2,
        test_purpose_frontmatter_v0_9_2,
        test_project_profile_purpose_reference_v0_9_2,
        test_goals_minimum_count_v0_9_2,
        test_key_questions_minimum_count_v0_9_2,
        test_research_scope_include_exclude_v0_9_2,
        test_evolving_thesis_hypothesis_v0_9_2,
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
