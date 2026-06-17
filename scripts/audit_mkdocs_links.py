#!/usr/bin/env python3
"""mkdocs cross-link audit (v0.7.57+) + gate (v0.7.61+).

Walk docs/ (excluding samples/) and verify all relative links resolve.
Exits 0 if all links are valid, 1 if any broken.

v0.7.61+ status: mkdocs build --strict is now ACTIVE in CI (after cross-link
rewrite + exclude_docs). This script remains as a defense-in-depth gate for
the *public-facing* docs — it walks docs/ directly (mkdocs only walks nav files)
and catches any link that mkdocs --strict missed.

Why both mkdocs --strict AND this script:
- mkdocs --strict: walks only files in `nav`, follows the docs_dir tree
- this script: walks all .md under docs/ (regardless of nav), useful for catching
  issues in pages that will be re-added to nav later or in CI logs

Pre-v0.7.61: --strict was OFF because ai-workflow/wiki/ was external to docs_dir
(116 broken warnings). v0.7.61 fix:
- Cross-link rewrite: all `../README.md`, `../QUICKSTART.md`, `../ai-workflow/...`,
  `../workflow-source/...` rewritten to GitHub absolute URL
- exclude_docs: samples/, archive/, planning/, architecture/ excluded from build
- docs/README.md: removed (conflict with index.md, merged into DOCUMENT_INDEX)

This script is the *defense-in-depth* layer for v0.7.61+:
- Audit only the *public-facing* docs (the ones in nav)
- Skip samples/ bundle (cross-refs are intentional, not broken)
- Report broken links in human + JSON format
- Return rc 0/1 for CI integration

Usage:
    python3 scripts/audit_mkdocs_links.py [--json] [--docs=PATH] [--exclude=DIR]

Exit codes:
    0 = all links valid
    1 = at least one broken link
    2 = usage error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Pattern for relative link in markdown: [text](path)
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
# Pattern for html-embedded links
HTML_LINK_RE = re.compile(r'href=["\']([^"\']+)["\']')


def _strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks (```...```) and inline code (`...`) from text.

    Returns text with code content replaced by blank lines (preserving line
    numbers for accurate error reporting).
    """
    lines = text.split("\n")
    out: list[str] = []
    in_fence = False
    fence_marker: str | None = None
    for line in lines:
        stripped = line.strip()
        if in_fence:
            if fence_marker and stripped.startswith(fence_marker):
                in_fence = False
                fence_marker = None
                out.append("")  # preserve line as empty
            else:
                out.append("")  # skip code line
        elif stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = True
            fence_marker = stripped[:3]
            out.append("")  # skip fence line
        else:
            # Strip inline code: `...` → ``
            cleaned = re.sub(r"`[^`]+`", "``", line)
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--docs", default="docs/", help="docs dir (default: docs/)")
    parser.add_argument(
        "--exclude", action="append", default=["samples/", "archive/"],
        help="exclude dir (default: samples/, archive/, repeatable)",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    docs_dir = Path(args.docs).resolve()
    if not docs_dir.is_dir():
        print(f"ERROR: --docs path is not a directory: {docs_dir}", file=sys.stderr)
        return 2

    broken: list[dict[str, str]] = []
    checked = 0
    skipped = 0

    # Update excludes with default + user-specified
    all_excludes = [docs_dir / "samples", docs_dir / "archive", docs_dir / "architecture", docs_dir / "planning"]
    for e in args.exclude:
        path = docs_dir / e.rstrip("/")
        if path not in all_excludes:
            all_excludes.append(path)

    for md_path in sorted(docs_dir.rglob("*.md")):
        # Skip excluded dirs
        if any(md_path.is_relative_to(e) for e in all_excludes):
            skipped += 1
            continue
        text = md_path.read_text(encoding="utf-8", errors="replace")
        # Strip code blocks (```...```) and inline code (`...`)
        # before scanning for links. Inside code, [text](path) is just example text.
        cleaned = _strip_code_blocks(text)
        # Find markdown links
        for match in LINK_RE.finditer(cleaned):
            link = match.group(2)
            # Skip absolute URLs (http/https)
            if link.startswith(("http://", "https://", "mailto:", "#", "tel:")):
                continue
            # Skip query-only / fragment-only
            if link.startswith(("?", "#")):
                continue
            # Strip fragment
            link_path = link.split("#", 1)[0]
            if not link_path:
                continue  # fragment-only
            # Resolve relative to md file's directory
            target = (md_path.parent / link_path).resolve()
            checked += 1
            if not target.exists():
                broken.append({
                    "source": str(md_path.relative_to(docs_dir)),
                    "link": link,
                    "resolved": str(target.relative_to(docs_dir.parent)) if target.is_relative_to(docs_dir.parent) else str(target),
                    "rule": "missing-target",
                })

    if args.json:
        report = {
            "docs_dir": str(docs_dir),
            "checked": checked,
            "skipped_files": skipped,
            "broken_count": len(broken),
            "broken": broken,
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Cross-link audit: {checked} links checked, {skipped} files skipped")
        if broken:
            print(f"  BROKEN: {len(broken)} link(s)")
            for b in broken[:20]:
                print(f"    {b['source']}: [{b['link']}] → not found")
            if len(broken) > 20:
                print(f"    ... +{len(broken) - 20} more")
        else:
            print("  OK: all links valid")

    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
