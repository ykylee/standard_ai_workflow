"""위키 구조 규칙의 판정 본체 — 1.x 검사와 허브가 **같은 함수**를 부른다 (요구 R8.3 · E2).

- V-1 정위치 (`check_wiki_location` 의 정위치 부분): 위키 뿌리와 ``index.md`` 가 있는가.
  금지 위치 규칙(``docs/wiki/`` 등)은 저장소 배치 규칙이라 1.x 검사에만 남는다 (실측 §16.2).
- V-4 index 구조 (`check_wiki_index_structure`): ``# 제목`` 하나 · ``##`` 절 · 절마다
  ``### [[<path>]] {#<anchor>}`` 항목 · anchor 유일 · 항목 경로가 실제 페이지.

경로는 모두 인자다 — 저장소 뿌리든, 허브가 펼친 임시 디렉터리든 같은 판정을 낸다.
"""

from __future__ import annotations

import re
from pathlib import Path

#: R4 — index 항목 한 줄의 형식.
ENTRY_RE = re.compile(r"^### \[\[([^\]]+)\]\] \{#([^}]+)\}$")
H1_RE = re.compile(r"^# (.+)$")
H2_RE = re.compile(r"^## (.+)$")
H3_PREFIX_RE = re.compile(r"^### ")


def check_canonical_location(wiki_root: Path) -> list[str]:
    """V-1 정위치 — 위키 디렉터리와 ``index.md`` 가 있는가."""
    errors: list[str] = []
    if not wiki_root.is_dir():
        errors.append(f"Canonical wiki directory missing: {wiki_root} (R1 requires ai-workflow/wiki/)")
    if not (wiki_root / "index.md").is_file():
        errors.append(f"Canonical wiki index missing: {wiki_root / 'index.md'} (R1 requires ai-workflow/wiki/index.md)")
    return errors


def validate_index(lines: list[str], wiki_root: Path) -> tuple[list[str], int]:
    """V-4 — index.md 줄 목록을 R4 구조로 판정한다. ``(위반 목록, 검사한 항목 수)``."""
    errors: list[str] = []
    if not lines or not H1_RE.match(lines[0]):
        first = repr(lines[0]) if lines else "<empty file>"
        errors.append(f"First line must be a top-level '# Title' heading, got: {first}")
        return errors, 0

    seen: dict[str, int] = {}
    section: str | None = None
    section_has_entry = False
    saw_h2 = False
    total = 0

    for lineno, raw in enumerate(lines, start=1):
        line = raw.rstrip()
        if not line:
            continue
        if H1_RE.match(line):
            if lineno != 1:
                errors.append(f"Line {lineno}: extra '#' top-level heading '{line}' (R4 allows a single H1 per index.md).")
            continue
        h2 = H2_RE.match(line)
        if h2:
            if section is not None and not section_has_entry:
                errors.append(f"Line {lineno}: ## section '{section}' has no ### entries (R4 forbids empty sections).")
            section = h2.group(1).strip()
            section_has_entry = False
            saw_h2 = True
            continue
        if H3_PREFIX_RE.match(line):
            match = ENTRY_RE.match(line)
            if not match:
                errors.append(f"Line {lineno}: malformed ### entry '{line}' (R4 requires '### [[<path>]] {{#<anchor-id>}}' format).")
                continue
            path, anchor = match.group(1).strip(), match.group(2).strip()
            if not path:
                errors.append(f"Line {lineno}: empty path in entry '{line}'.")
                continue
            if not anchor:
                errors.append(f"Line {lineno}: empty anchor-id in entry '{line}'.")
                continue
            if anchor in seen:
                errors.append(f"Line {lineno}: duplicate anchor-id '{anchor}' (first seen on line {seen[anchor]}).")
            else:
                seen[anchor] = lineno
            target = wiki_root / f"{path}.md"
            if not target.exists():
                errors.append(f"Line {lineno}: entry path '{path}' does not resolve to a file (expected: {target}).")
            section_has_entry = True
            total += 1
            continue
        if section is None and not saw_h2:
            errors.append(f"Line {lineno}: orphan content '{line[:60]}' outside any '##' section (R4 requires anchor-based structure).")

    if section is not None and not section_has_entry:
        errors.append(f"## section '{section}' has no ### entries (R4 forbids empty sections).")
    if not saw_h2:
        errors.append("index.md has no '##' sections (R4 requires at least one).")
    return errors, total


#: 본문의 위키 링크 ``[[path]]`` · ``[[path|별칭]]`` · ``[[path#절]]`` — 코드 펜스 밖에서만 센다.
_WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")


def wikilinks(body: str) -> list[str]:
    """본문의 위키 링크 대상 (코드 펜스 · 인라인 코드 안은 뺀다)."""
    out: list[str] = []
    fenced = False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        out.extend(m.group(1).strip() for m in _WIKILINK.finditer(re.sub(r"`[^`]*`", "", line)))
    return out


def is_repo_reference(target: str) -> bool:
    """``.md`` 로 끝나는 대상은 위키 페이지가 아니라 **저장소 파일 참조**다 — 위키 링크는 확장자를 안 붙인다.
    저장소 참조의 실재는 원격 읽기(E3 · R8.4)로만 잴 수 있어 여기서는 깨짐으로 세지 않는다."""
    return target.endswith(".md")


def classify_wikilinks(wiki_root: Path) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """``(깨진 위키 링크, 저장소 참조)`` — 각각 ``(페이지, 대상)``. index · log 는 생성물이라 뺀다."""
    broken: list[tuple[str, str]] = []
    repo_refs: list[tuple[str, str]] = []
    for page in sorted(wiki_root.rglob("*.md")):
        rel = page.relative_to(wiki_root).as_posix()
        if rel in ("index.md", "log.md"):
            continue
        for target in wikilinks(page.read_text(encoding="utf-8")):
            if is_repo_reference(target):
                repo_refs.append((rel, target))
            elif not (wiki_root / f"{target}.md").is_file():
                broken.append((rel, target))
    return broken, repo_refs
