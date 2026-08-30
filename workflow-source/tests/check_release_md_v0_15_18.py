#!/usr/bin/env python3
"""Smoke test — RELEASE.md cross-validation (v0.15.18+).

`docs/RELEASE.md` 가 릴리스 절차·회귀 표·버전 정보를 정확히 유지하는지
검증한다. 7 cases:

  1) **회귀 표 v0.15.1~v0.15.15 status**: 본 회귀 표의 마지막 행
     `v0.15.1~v0.15.15-beta` 의 release page 상태가 v0.15.15 정식 release
     완료 후 stale 하지 않은지 확인 (✅ 또는 명시적 in-release 표기).
  2) **현재 package version 필드 정합**: 헤더의 `- 현재 package version: X.Y.Z`
     == `workflow-source/pyproject.toml` 의 version.
  3) **회귀 표 v0.5.7 행**: wheel packaging 도입 행의 wheel/sdist 가
     `GitHub Release + wheel/sdist` 인지 확인.
  4) **frontmatter stamp**: `- 최종 수정일: 2026-07-18` 이 v0.15.15
     release day 와 정합.
  5) **회귀 표의 모든 vN.N.N 가 Beta-v*.md 파일 존재**: 본문에 등장하는
     주요 release version 들이 `workflow-source/releases/Beta-v*.md` 로
     존재 (드리프트 검출).
  6) **상태 줄 version 정합**: 헤더 `- 상태:` 의 `vX.Y.Z 기준` == pyproject.
  7) **현재 릴리스 노트 링크 정합**: `[현재 릴리스 노트 vX.Y.Z](...)` 가 현재
     버전을 가리키고 그 `Beta-vX.Y.Z.md` 가 실재.

case 2·6·7 은 '**현재**' 를 주장하는 세 자리를 각각 pyproject 와 대조한다
(TASK-2026-08-31-main-001). 이 문서는 회귀 표에 발행된 모든 버전을 영구히
담으므로, '본문 어딘가에 버전 문자열이 있는가' 로는 고착을 원리적으로 검출할 수
없다 — 옛 case 2 가 그 모양이었고 5개 minor 동안 red 가 되지 못했다.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "docs/RELEASE.md",
    "workflow-source/pyproject.toml",
)

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
RELEASE_MD_PATH = REPO_ROOT / "docs" / "RELEASE.md"
PYPROJECT_PATH = SOURCE_ROOT / "pyproject.toml"
RELEASES_DIR = SOURCE_ROOT / "releases"

# v1.0.0: 특정 날짜 고정은 문서를 갱신할 때마다 red 를 만든다 (2026-07-18 고정이
# 2026-07-21 갱신으로 깨진 사례). 본 case 의 의도는 *stale 검출* 이므로 "이 날짜보다
# 과거로 퇴행하지 않았는가" 를 하한으로 검증한다. ISO-8601 은 문자열 비교로 순서가 성립한다.
MIN_LAST_UPDATED = "2026-07-18"    # v0.15.15 release day — 이보다 과거면 stale

# '현재' 를 주장하는 헤더 필드들 (TASK-2026-08-31-main-001). 이 셋은 pyproject 를
# 따라와야 하며, 회귀 표처럼 **역사를 적는 자리와는 판정 기준이 다르다** — 회귀 표의
# `| v1.2.0 | ... |` 행은 옛 버전을 적는 것이 옳고, 아래 필드는 옛 버전이면 틀렸다.
CURRENT_VERSION_RE = re.compile(r"^-\s*현재 package version:\s*([\d.]+)", re.MULTILINE)
#: `- 상태:` 줄의 `vX.Y.Z 기준` / `vX.Y.Z-beta 기준`. `-beta` 접미사는 §2.2 가
#: v1.2.1 부터 뗐으므로 옛 표기도 받되 정본은 접미사 없는 쪽이다
#: (`check_installation_usage_v0_15_14.py` 의 같은 필드와 동일 어휘).
STATUS_VERSION_RE = re.compile(r"(v[\d.]+(?:-beta)?)\s*기준")
#: '다음에 읽을 문서' 의 `[현재 릴리스 노트 vX.Y.Z](<target>)`
CURRENT_NOTE_LINK_RE = re.compile(r"\[현재 릴리스 노트 v([\d.]+)\]\(([^)]+)\)")

# 회귀 표에 등장하는 주요 vN.N.N 패턴 (cross-check anchor)
# 본문에 등장하면 Beta-v<pattern>.md 가 존재해야 함
ANCHOR_VERSIONS = [
    "v0.5.0", "v0.5.7", "v0.5.10", "v0.5.11", "v0.6.0.1",
    "v0.8.0", "v0.9.0", "v0.9.1", "v0.10.0", "v0.10.2",
    "v0.10.4", "v0.11.0", "v0.11.18", "v0.11.21", "v0.11.22",
    "v0.15.0", "v0.15.15",
]


def _load_release_md() -> str:
    if not RELEASE_MD_PATH.is_file():
        raise AssertionError(f"RELEASE.md 부재: {RELEASE_MD_PATH}")
    return RELEASE_MD_PATH.read_text(encoding="utf-8")


def _load_pyproject() -> str:
    if not PYPROJECT_PATH.is_file():
        raise AssertionError(f"pyproject.toml 부재: {PYPROJECT_PATH}")
    return PYPROJECT_PATH.read_text(encoding="utf-8")


def _read_pyproject_version() -> str:
    m = re.search(r'^version\s*=\s*"([^"]+)"', _load_pyproject(), re.MULTILINE)
    if not m:
        raise AssertionError(f"pyproject.toml 에서 version 추출 실패: {PYPROJECT_PATH}")
    return m.group(1)


def _list_release_notes() -> set[str]:
    """Beta-v*.md 파일들의 version stem 반환. 예: {'v0.5.0', 'v0.15.15'}"""
    if not RELEASES_DIR.is_dir():
        return set()
    notes: set[str] = set()
    for p in RELEASES_DIR.glob("Beta-v*.md"):
        # Beta-v0.15.15.md -> v0.15.15
        stem = p.stem  # 'Beta-v0.15.15'
        if stem.startswith("Beta-"):
            notes.add(stem[len("Beta-"):])
    return notes


def case_1_regression_last_row_stale() -> bool:
    """1) 회귀 표 마지막 행 (v0.15.1~v0.15.15) 의 release page 상태 검증.

    v0.15.15 정식 release 가 완료된 상태이므로, 마지막 행은 ✅ 여야 함.
    `**in release**` 표기는 release 직전 단계 표기이므로 stale."""
    content = _load_release_md()
    # 마지막 행 (v0.15.1~v0.15.15-beta) 의 release page 컬럼 추출
    m = re.search(
        r"v0\.15\.1~v0\.15\.15-beta\s*\|[^\n]*\|\s*\*?\*?(in release|pending|✅)[^\n]*\|",
        content,
    )
    if not m:
        print("  FAIL: 회귀 표의 'v0.15.1~v0.15.15-beta' 행을 찾지 못함")
        return False
    cell = m.group(0)
    if "**in release**" in cell or "pending" in cell:
        print(f"  FAIL: 마지막 행 status 가 stale — '{cell.split('|')[-2].strip()}' "
              f"(v0.15.15 정식 release 완료 후 ✅ 여야 함)")
        return False
    if "✅" not in cell:
        print(f"  FAIL: 마지막 행 status 가 ✅ 가 아님 — '{cell[:100]}'")
        return False
    print(f"  [info] v0.15.1~v0.15.15 행 release page = ✅ 정합")
    return True


def case_2_pyproject_version() -> bool:
    """2) 헤더의 `현재 package version` 필드 == pyproject.toml version.

    **왜 '본문 어딘가에 등장' 이 아닌가** (TASK-2026-08-31-main-001): 원래 이
    case 는 5가지 표기 중 하나라도 본문에 있으면 PASS 였다. 그런데 같은 문서의
    회귀 표가 **발행된 모든 버전을 영구히 담는다** — `| v1.7.0 | ... |` 행이
    생기는 순간 `v1.7.0` 이 본문에 있게 되므로, 이 검사는 원리적으로 red 가
    될 수 없었다. 그 사이 헤더의 `- 현재 package version:` 은 1.2.0 에 고착해
    pyproject 1.7.0 과 5개 minor 갈라졌는데 **아무 검사도 그 필드를 안 봤다.**
    존재는 정합이 아니다 — '현재' 를 주장하는 필드를 직접 대조한다.
    """
    py_ver = _read_pyproject_version()
    content = _load_release_md()
    m = CURRENT_VERSION_RE.search(content)
    if not m:
        print(
            "  FAIL: RELEASE.md 헤더에 '- 현재 package version: X.Y.Z' 필드 부재 "
            "— 이 필드가 정합 대조 지점이다"
        )
        return False
    declared = m.group(1)
    if declared != py_ver:
        print(
            f"  FAIL: RELEASE.md '현재 package version: {declared}' "
            f"!= pyproject {py_ver}"
        )
        return False
    print(f"  [info] RELEASE.md 현재 package version={declared} = pyproject 정합")
    return True


def case_6_status_line_version() -> bool:
    """6) 헤더 `- 상태:` 줄의 `vX.Y.Z 기준` == pyproject version.

    `docs/INSTALLATION_AND_USAGE.md` 는 같은 필드를 이미 게이트로 잡고 있어
    (`check_installation_usage_v0_15_14.py` case 2) 현재를 유지해 왔는데,
    RELEASE.md 에는 대응 게이트가 없어 같은 자리가 고착했다.
    """
    py_ver = _read_pyproject_version()
    accepted = {f"v{py_ver}", f"v{py_ver}-beta"}
    content = _load_release_md()
    status_line = next(
        (ln for ln in content.splitlines() if ln.startswith("- 상태:")), None
    )
    if status_line is None:
        print("  FAIL: RELEASE.md 헤더에 '- 상태:' 줄 부재")
        return False
    found = set(STATUS_VERSION_RE.findall(status_line))
    if not found:
        print(f"  FAIL: '- 상태:' 줄에 'vX.Y.Z 기준' 표기 부재 — {status_line[:80]!r}")
        return False
    if not (found & accepted):
        print(
            f"  FAIL: RELEASE.md 상태 줄 version {sorted(found)} "
            f"!= pyproject {sorted(accepted)}"
        )
        return False
    print(f"  [info] RELEASE.md 상태 줄 v{py_ver} 정합")
    return True


def case_7_current_release_note_link() -> bool:
    """7) '현재 릴리스 노트 vX.Y.Z' 링크가 현재 버전을 가리키고 그 파일이 실재한다.

    '다음에 읽을 문서' 의 이 링크는 **현재**를 주장한다. 고착하면 독자를 5개
    minor 낡은 노트로 보낸다 (실측: `Beta-v1.2.0.md` 를 가리키는 동안
    `Beta-v1.7.0.md` 가 이미 있었다).
    """
    py_ver = _read_pyproject_version()
    content = _load_release_md()
    m = CURRENT_NOTE_LINK_RE.search(content)
    if not m:
        print("  FAIL: '현재 릴리스 노트 vX.Y.Z' 링크 부재")
        return False
    label_ver, target = m.group(1), m.group(2)
    if label_ver != py_ver:
        print(
            f"  FAIL: '현재 릴리스 노트 v{label_ver}' != pyproject {py_ver}"
        )
        return False
    if not target.endswith(f"Beta-v{py_ver}.md"):
        print(
            f"  FAIL: '현재 릴리스 노트' 링크 대상이 Beta-v{py_ver}.md 가 아니다: {target}"
        )
        return False
    note_path = RELEASES_DIR / f"Beta-v{py_ver}.md"
    if not note_path.is_file():
        print(f"  FAIL: 릴리스 노트 파일 부재: {note_path}")
        return False
    print(f"  [info] 현재 릴리스 노트 v{py_ver} 링크·파일 정합")
    return True


def case_3_wheel_packaging_row() -> bool:
    """3) 회귀 표의 v0.5.7 행 wheel/sdist 컬럼이 'GitHub Release + wheel/sdist' 인지."""
    content = _load_release_md()
    m = re.search(
        r"v0\.5\.7-beta\s*\|\s*\*?\*?GitHub Release \+ wheel/sdist\*?\*?",
        content,
    )
    if not m:
        print("  FAIL: v0.5.7 행의 wheel/sdist 컬럼이 'GitHub Release + wheel/sdist' 가 아님")
        return False
    print(f"  [info] v0.5.7 행 wheel/sdist = 'GitHub Release + wheel/sdist' 정합")
    return True


def case_4_frontmatter_stamp() -> bool:
    """4) frontmatter `- 최종 수정일: 2026-07-18` 정합."""
    content = _load_release_md()
    m = re.search(r"^-\s+최종\s*수정일\s*:\s*(\S+)", content, re.MULTILINE)
    if not m:
        print("  FAIL: frontmatter '최종 수정일' line 부재")
        return False
    actual = m.group(1).strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", actual):
        print(f"  FAIL: frontmatter stamp 형식 오류 (YYYY-MM-DD 아님) — actual={actual}")
        return False
    if actual < MIN_LAST_UPDATED:
        print(f"  FAIL: frontmatter stamp stale — actual={actual} < 하한 {MIN_LAST_UPDATED}")
        return False
    print(f"  [info] frontmatter stamp 정합: {actual}")
    return True


def case_5_release_notes_exist() -> bool:
    """5) 회귀 표의 주요 version 들이 Beta-v*.md 로 존재."""
    content = _load_release_md()
    notes = _list_release_notes()
    missing: list[str] = []
    for ver in ANCHOR_VERSIONS:
        # 본문에 등장 (v0.5.7, v0.5.7-beta 등 다양한 표기 흡수)
        pattern = re.escape(ver)
        if not re.search(pattern, content):
            # 본문에도 없으면 skip (anchor list 자체 drift)
            continue
        if ver not in notes:
            missing.append(ver)
    if missing:
        print(f"  FAIL: RELEASE.md 에 등장하지만 Beta-v*.md 부재: {missing}")
        return False
    found = sum(1 for v in ANCHOR_VERSIONS if v in notes)
    print(f"  [info] {found}/{len(ANCHOR_VERSIONS)} anchor versions 모두 Beta-v*.md 존재 ({len(notes)} total)")
    return True


def main() -> int:
    cases = [
        ("case_1_regression_last_row_stale", case_1_regression_last_row_stale),
        ("case_2_pyproject_version", case_2_pyproject_version),
        ("case_3_wheel_packaging_row", case_3_wheel_packaging_row),
        ("case_4_frontmatter_stamp", case_4_frontmatter_stamp),
        ("case_5_release_notes_exist", case_5_release_notes_exist),
        ("case_6_status_line_version", case_6_status_line_version),
        ("case_7_current_release_note_link", case_7_current_release_note_link),
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


# v0.15.18+: pytest-friendly wrappers (TST-WF-01 정합 — def test_ 패턴 추가).
# 기존 `def case_*` 와 `def main()` 정합 유지. pytest collection 에서도 5 case 모두 검증.
def test_case_1_regression_last_row_stale() -> None:
    assert case_1_regression_last_row_stale(), "case_1_regression_last_row_stale FAIL"


def test_case_2_pyproject_version() -> None:
    assert case_2_pyproject_version(), "case_2_pyproject_version FAIL"


def test_case_3_wheel_packaging_row() -> None:
    assert case_3_wheel_packaging_row(), "case_3_wheel_packaging_row FAIL"


def test_case_4_frontmatter_stamp() -> None:
    assert case_4_frontmatter_stamp(), "case_4_frontmatter_stamp FAIL"


def test_case_5_release_notes_exist() -> None:
    assert case_5_release_notes_exist(), "case_5_release_notes_exist FAIL"


def test_case_6_status_line_version() -> None:
    assert case_6_status_line_version(), "case_6_status_line_version FAIL"


def test_case_7_current_release_note_link() -> None:
    assert case_7_current_release_note_link(), "case_7_current_release_note_link FAIL"


if __name__ == "__main__":
    raise SystemExit(main())
