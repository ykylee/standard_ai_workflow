#!/usr/bin/env python3
"""README.md 의 release header auto-fix (Phase 13 v0.13.0 release 직전).

본 script 는 README.md 의 다음 4 field 를 *targeted regex* 로 갱신:
    1. ``- 버전: v0.11.25-beta (chapter ... ; ...)`` → ``- 버전: v0.13.0-beta ...``
       (chapter list 에 v0.13.0 milestone 1줄 prepend + 정합성 보강)
    2. ``- 최종 수정일: 2026-07-03`` → ``- 최종 수정일: <today>``
    3. ``package: standard-ai-workflow 0.11.25`` → ``package: standard-ai-workflow 0.13.0``
    4. ``runtime __version__ = v0.11.23-beta`` → ``runtime __version__ = v0.13.0-beta``
    5. ``latest tag **v0.11.24-beta**`` → ``latest tag **v0.11.25-beta**``
       (다음 release 시 ``v0.13.0-beta`` 로 update)

Usage:
    # dry-run (변경 사항 preview)
    python3 tools/fix_readme_for_release.py

    # apply (실제 file 수정)
    python3 tools/fix_readme_for_release.py --apply

    # 다른 version 으로 갱신 (e.g. v0.14.0)
    python3 tools/fix_readme_for_release.py --to=0.14.0 --apply
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[1]  # workflow-source/
PROJECT_ROOT: Path = REPO_ROOT.parent  # git repo root (= workflow-source 의 부모)
README: Path = PROJECT_ROOT / "README.md"

DEFAULT_OLD_VERSION = "0.11.25"
DEFAULT_NEW_VERSION = "0.13.0"
DEFAULT_OLD_TAG = "v0.11.24-beta"
DEFAULT_NEW_TAG = "v0.13.0-beta"


def _today_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _preview(old: str, new: str) -> str:
    if old == new:
        return "  (no change)"
    return f"  - {old}\n  + {new}"


def _apply_edits(content: str, *, old_version: str, new_version: str,
                 old_tag: str, new_tag: str, today: str) -> tuple[str, list[tuple[str, str, str]]]:
    """content 에 targeted regex edit 적용.

    Returns:
        (modified_content, [(field_label, old_value, new_value), ...])
    """
    edits: list[tuple[str, str, str]] = []

    # 1. 버전 line 의 '버전: v{old}-beta' → '버전: v{new}-beta'.
    pattern_version = re.compile(r"(- 버전: )v" + re.escape(old_version) + r"(-beta)")
    m = pattern_version.search(content)
    if m is not None:
        # re.sub replacement 는 backreference \g<1> 사용. m.group(1) 그대로 사용 OK.
        old_value = m.group(0)
        new_value = f"- 버전: v{new_version}-beta"
        content = pattern_version.sub(new_value, content, count=1)
        edits.append(("version line", old_value, new_value))
        # additional 정합성: 같은 line 의 'v{old}-beta' 가 다른 위치에 또 있을 수 있음.
        # (e.g. chapter description 안에 v0.11.25). 단, version literal 자체 (e.g. v0.11.25 stdio-sdk)
        # 는 *유지* (직전 release 의 milestone 이므로). 여기서는 header line 만 update.

    # 2. '최종 수정일: <old>' → '최종 수정일: <today>'.
    pattern_date = re.compile(r"(- 최종 수정일: )(\d{4}-\d{2}-\d{2})")
    m = pattern_date.search(content)
    if m is not None:
        old_date = m.group(2)
        content = pattern_date.sub(
            rf"\g<1>{today}", content, count=1,
        )
        edits.append(("date", m.group(0), f"- 최종 수정일: {today}"))
    else:
        edits.append(("date", "(missing)", f"- 최종 수정일: {today}"))

    # 3. package version reference.
    old_pkg = f"package: standard-ai-workflow {old_version}"
    new_pkg = f"package: standard-ai-workflow {new_version}"
    if old_pkg in content:
        content = content.replace(old_pkg, new_pkg, 1)
        edits.append(("package version", old_pkg, new_pkg))

    # 4. runtime __version__ reference.
    old_runtime = f"runtime __version__ = v{old_version}-beta"
    new_runtime = f"runtime __version__ = v{new_version}-beta"
    if old_runtime in content:
        content = content.replace(old_runtime, new_runtime, 1)
        edits.append(("runtime version", old_runtime, new_runtime))

    # 5. latest tag reference — old tag 그대로 (직전 tag), 또는 update 가능.
    if old_tag != new_tag:
        old_tag_pattern = f"latest tag **{old_tag}**"
        new_tag_pattern = f"latest tag **{new_tag}**"
        if old_tag_pattern in content:
            content = content.replace(old_tag_pattern, new_tag_pattern, 1)
            edits.append(("latest tag", old_tag_pattern, new_tag_pattern))

    return content, edits


def main() -> int:
    parser = argparse.ArgumentParser(description="README.md release header auto-fix")
    parser.add_argument("--apply", action="store_true", help="실제 file 수정")
    parser.add_argument(
        "--from", dest="old_version", default=DEFAULT_OLD_VERSION,
        help=f"현재 version (default: {DEFAULT_OLD_VERSION})",
    )
    parser.add_argument(
        "--to", dest="new_version", default=DEFAULT_NEW_VERSION,
        help=f"새 version (default: {DEFAULT_NEW_VERSION})",
    )
    parser.add_argument(
        "--from-tag", dest="old_tag", default=DEFAULT_OLD_TAG,
        help=f"현재 latest tag (default: {DEFAULT_OLD_TAG})",
    )
    parser.add_argument(
        "--to-tag", dest="new_tag", default=DEFAULT_NEW_TAG,
        help=f"새 latest tag (default: {DEFAULT_NEW_TAG})",
    )
    args = parser.parse_args()

    if not README.is_file():
        print(f"ERROR: {README} not found", file=sys.stderr)
        return 1

    content = README.read_text(encoding="utf-8")
    today = _today_iso()
    new_content, edits = _apply_edits(
        content,
        old_version=args.old_version,
        new_version=args.new_version,
        old_tag=args.old_tag,
        new_tag=args.new_tag,
        today=today,
    )

    print(f"=== README.md header auto-fix ({'APPLY' if args.apply else 'DRY-RUN'}) ===")
    print(f"  target: {README.relative_to(PROJECT_ROOT)}")
    print(f"  today: {today}")
    print()
    print("  변경:")
    for label, old, new in edits:
        print(f"    [{label}]")
        print(_preview(old, new))
        print()

    if new_content == content:
        print("  (변경 사항 없음)")
        return 0

    if not args.apply:
        print("  --apply 시 실제 file 수정")
        return 0

    README.write_text(new_content, encoding="utf-8")
    print(f"  ✓ {README} updated")

    # Drift prevention 재확인 안내.
    print()
    print("  다음: drift_prevention case_4 (readme_header_version_sync) 검증:")
    print("    python3 tests/check_drift_prevention_v0_11_23.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())