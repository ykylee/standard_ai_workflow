#!/usr/bin/env python3
"""vault L2 sources/ 의 <needs content> placeholder 해소 + 본문 emit helper.

v0.7.0 wiki 유지보수 개선 (2026-06-13): L2 sources/ 가 frontmatter 만 있고 본문 비어있는
draft 80% page 들을 raw mirror 의 본문 일부를 추출하여 자동 emit. wiki 검색 정합성 +
vault retrieval 의 *검색 가능 본문* 보장.

Usage:
    # Dry-run: 어떤 page 가 emit 대상인지 확인
    python3 emit_wiki_l2_body.py --project=standard-ai-workflow --dry-run

    # 실제 emit (vault 의 ~/wiki 의 L2 sources/ 에 직접 작성)
    python3 emit_wiki_l2_body.py --project=standard-ai-workflow --apply

    # 본문 cap (char count) — 너무 긴 본문 truncate
    python3 emit_wiki_l2_body.py --project=standard-ai-workflow --apply --max-chars=2000

Body emit 정책 (v1):
- L1 raw mirror 의 첫 # 헤더 이후 본문 2000자 추출
- `# Title (Derived View, YYYY-MM-DD)` 형식 머리
- `> L1 SSOT: <path> (<line count> lines)` reference
- `> 본 L2 derived view 는 vault retrieval 용 압축 요약. dense content 는 L1 SSOT 참조.`
- `## TL;DR` 자동 추출 (frontmatter 의 summary field 가 있으면 우선)
- 기존 # 본문 보존 (overwrite ❌, skip ✅)

Reference:
- workflow-source/extensions/SCHEMA.md §3 (file format)
- vault 의 L2 sources/ 본문 형식 (topics-aidlc-benchmark-analysis-2026-06-12.md 와 동일)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

VAULT_ROOT = Path.home() / "wiki"
RAW_MIRROR = VAULT_ROOT / "raw" / "projects"
L2_SOURCES = VAULT_ROOT / "wiki" / "projects"

# L1 → L2 stem 변환 (AIDLC 의 stem_from_path 와 동일)
PATH_TO_STEM_RE = re.compile(r"[/._]+")


def path_to_stem(rel_path: str) -> str:
    """raw/projects/<project>/ai-workflow/wiki/concepts/foo.md → concepts-foo"""
    parts = rel_path.split("/")
    if "wiki" in parts:
        idx = parts.index("wiki")
        sub = parts[idx + 1:]  # ['concepts', 'foo.md']
    else:
        sub = parts
    stem = "-".join(s.rsplit(".", 1)[0] for s in sub)
    return PATH_TO_STEM_RE.sub("-", stem).lower()


def find_l1_files(project: str) -> list[Path]:
    """raw mirror 의 L1 wiki file 들 (in-repo wiki) — NOT raw project root."""
    l1_dir = RAW_MIRROR / project / "ai-workflow" / "wiki"
    if not l1_dir.exists():
        return []
    return sorted(p for p in l1_dir.rglob("*.md"))


def find_l2_pages(project: str) -> dict[str, Path]:
    """L2 sources/ 의 모든 page (stem → path) mapping."""
    l2_dir = L2_SOURCES / project / "sources"
    if not l2_dir.exists():
        return {}
    return {p.stem: p for p in l2_dir.glob("*.md")}


def needs_body(l2_path: Path) -> bool:
    """L2 page 의 본문이 <needs content> placeholder 인지 확인."""
    content = l2_path.read_text(encoding="utf-8")
    return "<needs content>" in content


def extract_l1_body(l1_path: Path, max_chars: int = 2000) -> str:
    """L1 raw mirror 의 본문 (frontmatter 제외) 추출 + truncate."""
    content = l1_path.read_text(encoding="utf-8")
    # frontmatter 제거
    if content.startswith("---\n"):
        end = content.find("\n---\n", 4)
        if end >= 0:
            content = content[end + 5:]
    # 첫 # 헤더 이후 본문만
    first_h1 = content.find("\n# ")
    if first_h1 >= 0:
        body = content[first_h1 + 1:]
    else:
        body = content
    body = body.strip()
    if len(body) > max_chars:
        body = body[:max_chars].rsplit("\n", 1)[0] + "\n\n... (L1 SSOT 의 후속 본문은 raw mirror 참조)"
    return body


def extract_tldr_from_l1(l1_path: Path) -> str:
    """L1 의 ## §1 TL;DR (or ## TL;DR) 의 table 첫 1-2 row 추출."""
    content = l1_path.read_text(encoding="utf-8")
    # §1 TL;DR 또는 ## TL;DR 찾기
    m = re.search(r"^## (?:§\d+\s+)?TL;DR\s*\n+(.*?)(?=^##|\Z)", content, re.MULTILINE | re.DOTALL)
    if not m:
        return ""
    tldr_block = m.group(1).strip()
    # table 형식이면 첫 3 row 만
    lines = tldr_block.splitlines()
    table_lines = [l for l in lines if l.strip().startswith("|")]
    if len(table_lines) >= 4:  # header + separator + 2 rows
        return "\n".join(table_lines[:4])
    # 아니면 처음 5 줄
    return "\n".join(lines[:5])


def build_emit_body(l1_path: Path, today: str, max_chars: int = 2000) -> str:
    """L2 derived view 본문 생성 (frontmatter 머리 + L1 SSOT ref + TL;DR + truncated body)."""
    title = l1_path.stem.replace("-", " ").title()
    l1_line_count = sum(1 for _ in l1_path.open(encoding="utf-8"))
    rel_l1 = l1_path.relative_to(RAW_MIRROR / l1_path.parts[RAW_MIRROR.parts.index("raw") + 2])
    tldr = extract_tldr_from_l1(l1_path)
    body = extract_l1_body(l1_path, max_chars=max_chars)

    parts = [
        f"# {title} (Derived View, {today})",
        "",
        f"> L1 SSOT: `~/{rel_l1}` ({l1_line_count} lines)",
        "> 본 L2 derived view 는 vault retrieval 용 압축 요약. dense content 는 L1 SSOT 참조.",
        "",
    ]
    if tldr:
        parts.extend(["## TL;DR", "", tldr, ""])
    if body:
        parts.extend(["## 본문 (발췌)", "", body])
    return "\n".join(parts)


def update_l2_full(l2_path: Path, l1_path: Path, today: str, max_chars: int = 2000) -> str:
    """L2 file 전체 갱신: frontmatter 보존 + `<needs content>` 자리에 emit body 삽입 + last_touched 갱신 + status reviewed.

    Returns the new full content.
    """
    content = l2_path.read_text(encoding="utf-8")
    # frontmatter 추출
    if not content.startswith("---\n"):
        return content
    fm_end = content.find("\n---\n", 4)
    if fm_end < 0:
        return content
    fm = content[4:fm_end]
    body = content[fm_end + 5:]

    # body 에서 `<needs content>` 자리만 교체 (placeholder 라인 전체 제거)
    new_body_section = build_emit_body(l1_path, today, max_chars=max_chars)
    new_body = body.replace("## Summary\n<needs content>", new_body_section, 1)
    if new_body == body:
        # fallback: bare <needs content> 만 교체
        new_body = body.replace("<needs content>", new_body_section, 1)

    # frontmatter 갱신: last_touched + status
    new_fm_lines = []
    for line in fm.split("\n"):
        if line.startswith("last_touched:"):
            new_fm_lines.append(f"last_touched: {today}")
        elif line.startswith("status: draft"):
            new_fm_lines.append("status: reviewed")
        else:
            new_fm_lines.append(line)
    new_fm = "\n".join(new_fm_lines)

    return f"---\n{new_fm}\n---\n{new_body}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project", required=True, help="my-harness | devhub | standard-ai-workflow | cross")
    parser.add_argument("--apply", action="store_true", help="실제 L2 file 에 emit (default: dry-run)")
    parser.add_argument("--max-chars", type=int, default=2000, help="L1 본문 cap (default: 2000)")
    parser.add_argument("--limit", type=int, default=0, help="max N page emit (default: 무제한)")
    args = parser.parse_args()

    today = date.today().isoformat()
    dry_run = not args.apply

    l1_files = find_l1_files(args.project)
    l2_pages = find_l2_pages(args.project)

    candidates: list[tuple[Path, Path]] = []
    for l1 in l1_files:
        stem = path_to_stem(str(l1.relative_to(RAW_MIRROR / args.project / "ai-workflow" / "wiki")))
        l2 = l2_pages.get(stem)
        if l2 and needs_body(l2):
            candidates.append((l1, l2))

    if args.limit > 0:
        candidates = candidates[:args.limit]

    print(f"Project: {args.project}")
    print(f"L1 files: {len(l1_files)}")
    print(f"L2 pages: {len(l2_pages)}")
    print(f"Candidates (needs content): {len(candidates)}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Max chars: {args.max_chars}")
    print()

    emitted = 0
    for l1, l2 in candidates:
        rel_l1 = l1.relative_to(RAW_MIRROR / args.project / "ai-workflow" / "wiki")

        if dry_run:
            print(f"  [DRY] {l2.relative_to(VAULT_ROOT)}")
            print(f"        ← raw: {rel_l1}")
        else:
            new_content = update_l2_full(l2, l1, today, max_chars=args.max_chars)
            l2.write_text(new_content, encoding="utf-8")
            print(f"  [APPLIED] {l2.relative_to(VAULT_ROOT)}")
            emitted += 1

    print()
    if dry_run:
        print(f"Dry-run complete. {len(candidates)} page 가 emit 대상. --apply 로 실제 실행.")
    else:
        print(f"Applied {emitted} page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
