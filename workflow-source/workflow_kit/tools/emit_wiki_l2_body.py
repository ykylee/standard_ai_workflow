#!/usr/bin/env python3
"""in-repo wiki L2 sources/ 의 <needs content> placeholder 해소 + 본문 emit helper.

v0.7.0 wiki 유지보수 개선 (2026-06-13): L2 sources/ 가 frontmatter 만 있고 본문 비어있는
draft 80% page 들을 raw mirror 의 본문 일부를 추출하여 자동 emit. wiki 검색 정합성 +
vault retrieval 의 *검색 가능 본문* 보장.

**v0.7.17+ in-repo storage**: 외부 vault (~/wiki/) 연결 완전 제거. 본 project 의
L1 raw mirror = `ai-workflow/wiki/` (concepts/decisions/entities/patterns/topics),
L2 sources = `ai-workflow/wiki/sources/`. 모든 path 가 in-repo.

Usage:
    # Dry-run: 어떤 page 가 emit 대상인지 확인
    python3 emit_wiki_l2_body.py --project=standard-ai-workflow --dry-run

    # 실제 emit (in-repo L2 sources/ 에 직접 작성)
    python3 emit_wiki_l2_body.py --project=standard-ai-workflow --apply

    # 본문 cap (char count) — 너무 긴 본문 truncate
    python3 emit_wiki_l2_body.py --project=standard-ai-workflow --apply --max-chars=2000

Body emit 정책 (v1):
- L1 raw mirror 의 첫 # 헤더 이후 본문 2000자 추출
- `# Title (Derived View, YYYY-MM-DD)` 형식 머리
- `> L1 SSOT: <path> (<line count> lines)` reference
- `> 본 L2 derived view 는 in-repo retrieval 용 압축 요약. dense content 는 L1 SSOT 참조.`
- `## TL;DR` 자동 추출 (frontmatter 의 summary field 가 있으면 우선)
- 기존 # 본문 보존 (overwrite ❌, skip ✅)

Reference:
- workflow-source/extensions/SCHEMA.md §3 (file format)
- in-repo L2 sources/ 본문 형식 (concepts/*.md 와 동일)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

# v0.7.17+ in-repo storage. REPO_ROOT 결정 + L1/L2 path 모두 in-repo.
# 4-priority auto-detect (refresh_wiki_memory.py 와 동일) — git rev-parse 우선.
def _detect_repo_root() -> Path:
    """REPO_ROOT 결정 (priority: git rev-parse > cwd 기준 상위 dir 탐색).

    refresh_wiki_memory.py 와 동일 정공법. 단, 본 script 는 standalone 실행 가능
    형태를 위해 env var + CLI flag 는 생략 (v0.7.17+ 의 단순화).
    """
    try:
        import subprocess

        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return Path(proc.stdout.strip()).resolve()
    except Exception:
        pass
    return Path.cwd().resolve()


REPO_ROOT = _detect_repo_root()
L1_BASE = REPO_ROOT / "ai-workflow"
RAW_MIRROR = L1_BASE / "wiki"  # L1 raw mirror (in-repo)
L2_SOURCES = L1_BASE / "wiki" / "sources"  # L2 dense content emit target (in-repo)

#: 본문에 박히는 **생성물 표식**. 이 줄이 없는 L2 page 는 사람이 쓴 것으로 보고
#: 본 tool 이 덮어쓰지 않는다 (`manual` 로 보고). 재emit 은 본문 *전체* 를
#: 갈아끼우므로, 표식 없는 page 를 건드리면 사람의 글을 파괴한다.
L2_GENERATED_MARKER = "> Generated:"

#: `refresh_wiki_memory --emit-l2` 가 소유하는 stub. 같은 page 를 두 tool 이
#: 쓰면 마지막에 돈 쪽이 이기고 그 사실이 아무 데도 안 남는다 — 소유권을
#: 한쪽에만 둔다.
STUBS_OWNED_BY_REFRESH_WIKI_MEMORY = frozenset({
    "active-state", "active-work-backlog", "active-session-handoff", "wiki-log",
})

#: L2 page 의 `status`. wiki SCHEMA §1.1 의 어휘는 `active|draft|deprecated` 뿐이라
#: 이전 구현이 쓰던 `reviewed` 는 정의된 적이 없는 값이었다 (같은 지적이
#: `score_wiki_maintainability.score_lifecycle` docstring 에 있다). L2 는 매 사이클
#: 재생성되는 생성물이므로 `draft` 로 둔다.
GENERATED_STATUS = "draft"

# L1 → L2 stem 변환 (AIDLC 의 stem_from_path 와 동일)
PATH_TO_STEM_RE = re.compile(r"[/._]+")


def path_to_stem(rel_path: str) -> str:
    """ai-workflow/wiki/concepts/foo.md → concepts-foo"""
    parts = rel_path.split("/")
    if "wiki" in parts:
        idx = parts.index("wiki")
        sub = parts[idx + 1:]  # ['concepts', 'foo.md']
    else:
        sub = parts
    stem = "-".join(s.rsplit(".", 1)[0] for s in sub)
    return PATH_TO_STEM_RE.sub("-", stem).lower()


def find_l1_files(project: str) -> list[Path]:
    """in-repo L1 wiki file 들 (ai-workflow/wiki/concepts/*.md 등).

    v0.7.17+ in-repo storage. project 는 *legacy* field (multi-project metadata) 로
    무시 — 본 project 의 wiki 는 단일.
    """
    l1_dir = RAW_MIRROR
    if not l1_dir.exists():
        return []
    # `sources/` 는 L2 자신이다. 빼지 않으면 파생 뷰가 **자기 자신에서** 파생된다.
    return sorted(
        p for p in l1_dir.rglob("*.md")
        if L2_SOURCES not in p.parents
    )


def find_l2_pages(project: str) -> dict[str, Path]:
    """in-repo L2 sources/ 의 모든 page (stem → path) mapping."""
    l2_dir = L2_SOURCES
    if not l2_dir.exists():
        return {}
    return {p.stem: p for p in l2_dir.glob("*.md")}


#: L1 wiki 의 *page* 가 아닌 운영 파일. L2 파생 뷰 대상에서 뺀다.
L1_NON_PAGE_NAMES = frozenset({"log.md", "SCHEMA.md", "INGEST_GUIDE.md", "index.md"})


def is_l1_page(l1_path: Path) -> bool:
    """`concepts/` `decisions/` 같은 page 인가 (운영 파일이 아닌가)."""
    return l1_path.name not in L1_NON_PAGE_NAMES


def needs_body(l2_path: Path) -> bool:
    """L2 page 의 본문이 <needs content> placeholder 인지 확인."""
    content = l2_path.read_text(encoding="utf-8")
    return "<needs content>" in content


def l2_last_touched(l2_path: Path) -> date | None:
    """L2 page frontmatter 의 `last_touched`. 없거나 형식이 틀리면 None."""
    content = l2_path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"^last_touched:\s*(\d{4}-\d{2}-\d{2})", content, re.MULTILINE)
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:
        return None


def is_generated(l2_path: Path) -> bool:
    """본 tool 이 만든 page 인가 (생성물 표식 보유)."""
    return L2_GENERATED_MARKER in l2_path.read_text(encoding="utf-8", errors="ignore")


def needs_emit(l1_path: Path | None, l2_path: Path) -> tuple[bool, str]:
    """이 L2 page 를 지금 emit 해야 하는가. `(대상 여부, 사유)`.

    이전 게이트는 `<needs content>` placeholder **하나** 였다. 그래서 한 번
    emit 되고 나면 그 page 는 **영원히 재emit 대상이 아니었다** — L1 이 아무리
    바뀌어도 파생 뷰가 따라가지 않고 `last_touched` 가 얼어붙어, 그 자체가
    `score_wiki_maintainability` 의 `lifecycle` 을 갉아먹었다. 게이트를
    *신선도* 로 바꾼다: placeholder 이거나, L1 이 L2 보다 새로우면 대상.
    """
    if needs_body(l2_path):
        return True, "placeholder"
    if not is_generated(l2_path):
        # 사람이 쓴 본문은 덮어쓰지 않는다.
        return False, "manual"
    touched = l2_last_touched(l2_path)
    if touched is None:
        return True, "last_touched 부재"
    if l1_path is None:
        return False, "L1 부재"
    l1_mtime = date.fromtimestamp(l1_path.stat().st_mtime)
    if l1_mtime > touched:
        return True, "L1 이 더 새롭다 ({} > {})".format(l1_mtime, touched)
    return False, "최신"


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
    # 헤딩 꼬리의 R4 anchor(`{#s1-tldr}`)를 허용한다. 이 저장소의 wiki 헤딩은
    # 대부분 anchor 를 달고 있어서, 그걸 빼면 TL;DR 추출이 거의 항상 실패했다.
    m = re.search(
        r"^## (?:§\d+\s+)?TL;DR[^\n]*\n+(.*?)(?=^##|\Z)",
        content, re.MULTILINE | re.DOTALL,
    )
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
    # v0.7.17 in-repo 전환 전에는 L1 이 `~/wiki/raw/<project>/...` 였고, 이 줄은
    # 그 레이아웃의 `raw` 조각을 세어 project 디렉터리를 잘라냈다. in-repo 에는
    # `raw` 조각이 없어 `RAW_MIRROR` 기준 상대 경로면 충분하다.
    rel_l1 = l1_path.relative_to(RAW_MIRROR)
    tldr = extract_tldr_from_l1(l1_path)
    body = extract_l1_body(l1_path, max_chars=max_chars)

    parts = [
        f"# {title} (Derived View, {today})",
        "",
        f"> L1 SSOT: `ai-workflow/wiki/{rel_l1}` ({l1_line_count} lines)",
        "> 본 L2 derived view 는 in-repo retrieval 용 압축 요약. dense content 는 L1 SSOT 참조.",
        f"{L2_GENERATED_MARKER} {today} by `workflow_kit.tools.emit_wiki_l2_body`",
        "",
    ]
    if tldr:
        parts.extend(["## TL;DR", "", tldr, ""])
    if body:
        parts.extend(["## 본문 (발췌)", "", body])
    return "\n".join(parts)


def build_metadata_only_body(l2_path: Path, today: str) -> str:
    """L1 raw mirror 가 없는 page 의 metadata-only 본문 emit.

    frontmatter 의 title / tags / sources / related / contradictions 를 기반으로
    *vault-only entry* 정책의 본문 생성. L1 SSOT 가 없음을 명시.
    """
    content = l2_path.read_text(encoding="utf-8", errors="ignore")
    if not content.startswith("---\n"):
        return ""
    fm_end = content.find("\n---\n", 4)
    if fm_end < 0:
        return ""
    fm = content[4:fm_end]

    # frontmatter parse
    title = ""
    tags: list[str] = []
    sources: list[str] = []
    related: list[str] = []
    contradictions: list[str] = []
    status = ""
    in_list = False
    list_key = ""

    for line in fm.split("\n"):
        stripped = line.strip()
        if stripped.startswith("title:"):
            title = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("type:"):
            pass
        elif stripped.startswith("status:"):
            status = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("tags:"):
            in_list = True
            list_key = "tags"
            v = stripped.split(":", 1)[1].strip()
            if v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                if inner:
                    tags = [t.strip() for t in inner.split(",")]
                in_list = False
        elif stripped.startswith("sources:"):
            in_list = True
            list_key = "sources"
        elif stripped.startswith("related:"):
            in_list = True
            list_key = "related"
            v = stripped.split(":", 1)[1].strip()
            if v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                if inner:
                    related = [t.strip() for t in inner.split(",")]
                in_list = False
        elif stripped.startswith("contradictions:"):
            in_list = True
            list_key = "contradictions"
        elif in_list and stripped.startswith("- "):
            if list_key == "sources":
                sources.append(stripped[2:].strip())
            elif list_key == "related":
                related.append(stripped[2:].strip())
            elif list_key == "contradictions":
                contradictions.append(stripped[2:].strip())
        elif in_list and not stripped:
            in_list = False

    stem = l2_path.stem
    display_title = title if title else stem.replace("-", " ").title()

    parts = [
        f"# {display_title} (Vault-Only Entry, {today})",
        "",
        "> **Status**: vault-only — raw mirror 부재 (자체 생성 / 운영 log / archive)",
        "> 본 L2 entry 는 *frontmatter metadata* + *vault 운영 note* 만 포함.",
        "> raw mirror 가 없으므로 L1 SSOT 참조 불가. dense content 는 vault 운영자가 직접 작성.",
        "",
        "## Metadata",
        "",
    ]
    if tags:
        parts.append("**Tags**: " + ", ".join(f"`{t}`" for t in tags))
    if status:
        parts.append(f"**Status**: {status}")
    if sources:
        parts.append("")
        parts.append("**Sources**:")
        for s in sources:
            parts.append(f"- `{s}`")
    if related:
        parts.append("")
        parts.append("**Related**:")
        for r in related:
            parts.append(f"- {r}")
    if contradictions:
        parts.append("")
        parts.append("**Contradictions**:")
        for c in contradictions:
            parts.append(f"- {c}")

    parts.extend([
        "",
        "## 본 policy",
        "",
        "본 page 는 *vault 운영 중 작성된 page* (L1 raw mirror 없음):",
        "- 자체 운영 log (날짜 prefix, e.g. `2026-06-12-*-assessment.md`)",
        "- Obsidian metadata (`.omo-*`)",
        "- Example / sample project (e.g. `acme-delivery-platform-*`)",
        "- Template (`_*`)",
        "- 외부 system snapshot (IP prefix, e.g. `192.168.0.139-*`)",
        "",
        "vault 의 검색 정합도 (discoverability) 향상을 위해 *metadata-only 본문* 자동 emit.",
        "raw mirror 가 추가되거나 L1 page 가 생성되면 `l1` mode 로 재처리 가능.",
        "",
        f"> Generated: {today} by `tools/emit_wiki_l2_body.py --mode=metadata-only`",
    ])
    return "\n".join(parts)


def update_l2_full(l2_path: Path, l1_path: Path, today: str, max_chars: int = 2000, mode: str = "l1") -> str:
    """L2 file 전체 갱신: frontmatter 보존 + `<needs content>` 자리에 emit body 삽입 + last_touched 갱신 + status reviewed.

    mode: "l1" (default, L1 raw mirror 기반) | "metadata-only" (raw mirror 없는 page)
    """
    if not l2_path.exists():
        # 아직 없는 파생 뷰 — frontmatter 를 bootstrap 한다. 생성물이므로
        # `status` 는 SCHEMA 어휘의 `draft`, `r9_skip` 은 R9 wiki-source 규칙 예외.
        fm = (
            "type: meta\n"
            f"status: {GENERATED_STATUS}\n"
            "r9_skip: true\n"
            f"title: {l2_path.stem}\n"
            f"created: {today}\n"
            f"last_touched: {today}"
        )
        body = ""
    else:
        content = l2_path.read_text(encoding="utf-8")
        if not content.startswith("---\n"):
            return content
        fm_end = content.find("\n---\n", 4)
        if fm_end < 0:
            return content
        fm = content[4:fm_end]
        body = content[fm_end + 5:]

    if mode == "metadata-only":
        new_body_section = build_metadata_only_body(l2_path, today)
    else:
        new_body_section = build_emit_body(l1_path, today, max_chars=max_chars)

    # 본문은 **전부** 파생물이다. placeholder 자리에만 끼워 넣으면 두 번째
    # 실행부터 본문이 낡은 채 굳는다 (게이트가 신선도로 바뀐 이상 재emit 이
    # 정상 경로다). placeholder 가 남아 있는 첫 emit 도 같은 결과가 된다.
    new_body = "\n" + new_body_section.strip() + "\n"

    new_fm_lines = []
    seen_touched = False
    for line in fm.split("\n"):
        if line.startswith("last_touched:"):
            new_fm_lines.append(f"last_touched: {today}")
            seen_touched = True
        elif line.startswith("status:"):
            # SCHEMA §1.1 어휘 밖의 값(`reviewed`)을 쓰지 않는다.
            new_fm_lines.append(f"status: {GENERATED_STATUS}")
        else:
            new_fm_lines.append(line)
    if not seen_touched:
        new_fm_lines.append(f"last_touched: {today}")
    new_fm = "\n".join(new_fm_lines)

    return f"---\n{new_fm}\n---\n{new_body}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project", required=True, help="my-harness | devhub | standard-ai-workflow | cross")
    parser.add_argument("--apply", action="store_true", help="실제 L2 file 에 emit (default: dry-run)")
    parser.add_argument("--max-chars", type=int, default=2000, help="L1 본문 cap (default: 2000)")
    parser.add_argument("--limit", type=int, default=0, help="max N page emit (default: 무제한)")
    parser.add_argument(
        "--bootstrap-missing", action="store_true",
        help="L2 파생 뷰가 없는 L1 page 에 대해 L2 를 **새로 만든다** (default: 만들지 않고 개수만 보고). "
             "in-repo 저장소에서 L1 은 이미 검색 가능하므로 기본은 off 다 — 켜면 L1 의 절삭 사본이 "
             "저장소에 그만큼 늘어난다.",
    )
    parser.add_argument(
        "--mode",
        default="l1",
        choices=["l1", "metadata-only", "all"],
        help="l1 (L1 raw mirror 기반) | metadata-only (raw mirror 없는 page) | all (둘 다)",
    )
    args = parser.parse_args()

    today = date.today().isoformat()
    dry_run = not args.apply

    l1_files = find_l1_files(args.project)
    l2_pages = find_l2_pages(args.project)

    # 모드 별 후보 수집
    candidates: list[tuple[Path | None, Path, str]] = []  # (l1, l2, mode)
    skipped: list[tuple[str, str]] = []  # (stem, 사유)

    def _owned_elsewhere(stem: str) -> bool:
        return stem in STUBS_OWNED_BY_REFRESH_WIKI_MEMORY

    for l1 in l1_files:
        # v0.7.17 in-repo 전환 전 레이아웃(`<raw>/<project>/ai-workflow/wiki/`)이
        # 그대로 남아 있어, in-repo 경로에서는 `relative_to` 가 항상 ValueError 였다.
        stem = path_to_stem(str(l1.relative_to(RAW_MIRROR)))
        l2 = l2_pages.get(stem)
        if not l2 or args.mode not in ("l1", "all"):
            continue
        if _owned_elsewhere(stem):
            skipped.append((stem, "refresh_wiki_memory --emit-l2 소유"))
            continue
        want, reason = needs_emit(l1, l2)
        if want:
            candidates.append((l1, l2, "l1"))
        else:
            skipped.append((stem, reason))

    # metadata-only: L1 raw mirror 가 없는 page (frontmatter 에 source 없음)
    if args.mode in ("metadata-only", "all"):
        for stem, l2 in l2_pages.items():
            # 이미 l1 모드 후보/스킵에 포함된 page 는 skip
            if any(c[1] == l2 for c in candidates):
                continue
            if any(sk[0] == stem for sk in skipped):
                continue
            if _owned_elsewhere(stem):
                skipped.append((stem, "refresh_wiki_memory --emit-l2 소유"))
                continue
            want, reason = needs_emit(None, l2)
            if want:
                candidates.append((None, l2, "metadata-only"))
            else:
                skipped.append((stem, reason))

    # L2 파생 뷰가 아직 없는 L1 page. 이전 구현은 *이미 있는* L2 만 갱신할 수
    # 있어서 이 갭이 어디에도 드러나지 않았다 (후보 0 = "할 일 없음" 으로 보였다).
    missing_l2: list[Path] = []
    for l1 in l1_files:
        if not is_l1_page(l1):
            continue
        stem = path_to_stem(str(l1.relative_to(RAW_MIRROR)))
        if stem in l2_pages or _owned_elsewhere(stem):
            continue
        missing_l2.append(l1)

    if args.bootstrap_missing and args.mode in ("l1", "all"):
        # 파일은 여기서 만들지 않는다. 미리 placeholder 를 쓰면 `--limit` 이
        # emit 개수만 자르므로 **본문 없는 껍데기가 남는다** — 그 껍데기는
        # `<needs content>` 라 discoverability 를 오히려 끌어내린다.
        for l1 in missing_l2:
            stem = path_to_stem(str(l1.relative_to(RAW_MIRROR)))
            candidates.append((l1, L2_SOURCES / f"{stem}.md", "l1"))

    if args.limit > 0:
        candidates = candidates[:args.limit]

    print(f"Project: {args.project}")
    print(f"L1 files: {len(l1_files)}")
    print(f"L2 pages: {len(l2_pages)}")
    print(f"Candidates (needs content): {len(candidates)}")
    print(f"Mode: {args.mode}")
    print(f"Apply: {'YES' if args.apply else 'NO (DRY-RUN)'}")
    print(f"Max chars: {args.max_chars}")
    print()

    emitted = 0
    unchanged = 0
    for l1, l2, mode in candidates:
        # `VAULT_ROOT` 는 v0.7.17 in-repo 전환 때 사라진 이름인데 이 두 줄에만
        # 남아 있었다 — emit 이 여기까지 도달하기만 하면 NameError 였다.
        rel = l2.relative_to(REPO_ROOT)
        if dry_run:
            print(f"  [DRY ({mode})] {rel}")
            continue
        new_content = update_l2_full(l2, l1, today, max_chars=args.max_chars, mode=mode)
        l2.parent.mkdir(parents=True, exist_ok=True)
        if l2.exists() and l2.read_text(encoding="utf-8") == new_content:
            print(f"  [UNCHANGED ({mode})] {rel}")
            unchanged += 1
            continue
        l2.write_text(new_content, encoding="utf-8")
        print(f"  [APPLIED ({mode})] {rel}")
        emitted += 1

    if missing_l2 and not args.bootstrap_missing:
        print()
        print(f"L2 파생 뷰 없는 L1 page: {len(missing_l2)}개 (--bootstrap-missing 으로 생성)")

    if skipped:
        print()
        print("Skipped:")
        for stem, reason in sorted(skipped):
            print(f"  [skip] {stem:<28} {reason}")

    print()
    if dry_run:
        print(f"Dry-run complete. {len(candidates)} page 가 emit 대상. --apply 로 실제 실행.")
    else:
        print(f"Applied {emitted} page (unchanged {unchanged}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
