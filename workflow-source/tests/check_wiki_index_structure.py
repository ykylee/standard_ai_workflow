#!/usr/bin/env python3
"""Smoke test the wiki index structure validator (V-4, R4)."""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "ai-workflow/wiki/*",
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
)

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_WIKI_ROOT = REPO_ROOT / "ai-workflow" / "wiki"
CANONICAL_INDEX = CANONICAL_WIKI_ROOT / "index.md"

# 판정 본체는 패키지 하나 — 허브 lint 와 같은 함수 (요구 R8.3 · E2).
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
from workflow_kit.common.wiki_rules import validate_index as _validate  # noqa: E402


def main() -> int:
    if not CANONICAL_INDEX.exists():
        print(f"[V-4] FAIL: canonical index missing: {CANONICAL_INDEX.relative_to(REPO_ROOT)}")
        raise AssertionError("Wiki index structure check cannot run: index.md not found.")

    lines = CANONICAL_INDEX.read_text(encoding="utf-8").splitlines()
    errors, total = _validate(lines, CANONICAL_WIKI_ROOT)
    if errors:
        for line in errors:
            print(f"[V-4] FAIL: {line}")
        raise AssertionError(
            f"Wiki index structure check failed with {len(errors)} violation(s)."
        )
    print(f"Wiki index structure check passed (V-4, {total} entries validated).")
    return 0


def test_case_1() -> None:
    assert main() == 0, "case_1 smoke FAIL"


def test_case_2() -> None:
    assert main() == 0, "case_2 smoke FAIL"


def test_case_3() -> None:
    assert main() == 0, "case_3 smoke FAIL"


def test_case_4() -> None:
    assert main() == 0, "case_4 smoke FAIL"


def test_case_5() -> None:
    assert main() == 0, "case_5 smoke FAIL"



if __name__ == "__main__":
    sys.exit(main())
