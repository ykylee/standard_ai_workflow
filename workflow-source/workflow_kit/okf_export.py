"""workflow_kit.okf_export — wiki → OKF bundle export helper (PoC, v0.7.33+).

OKF (Open Knowledge Format) spec 의 reference: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
준수를 선언하는 버전은 `OKF_SPEC_VERSION` 이 정본이다 (v0.2, ADR-026 —
legacy 형태를 남긴 채 정규 필드를 더해 v0.1·v0.2 소비자를 함께 만족한다).

Wiki page (markdown + YAML frontmatter) 를 OKF "concept" 문서로 변환하여
지정 directory 에 bundle 로 export. 우리 wiki 의 5 type (entity/concept/decision/pattern/query) 을
OKF 의 free-string `type` 으로 그대로 보존 (OKF spec §4.1: type 은 non-empty string, no registry).

Frontmatter mapping (우리 wiki → OKF v0.2 + v0.1 legacy 병행, ADR-026):
  - `type`         → `type`           (우리 enum ⊂ OKF string, 그대로)
  - `title`        → `title`          (OKF recommended, optional)
  - `description`  → `description`    (OKF recommended, optional)
  - `last_ingested_from` (URL/path) → `resource` (if URL) + `sources` (§5.1, v0.2)
  - `tags`         → `tags`           (union with derived from `status`, `related_pages`)
  - `updated`      → `timestamp`      (legacy, §13.1 fallback 용으로 유지; `generated` 는 의도적으로 안 낸다)
  - `created`      → extra `created`  (OKF 가 unknown key tolerate, spec §4.1 Extensions)
  - `status`       → `status` (§5.4 어휘로 매핑) + 원문은 extra `wiki_status` 로 보존
  - `related_pages` → extra `related_pages` (and emit as cross-links in body §5.1)
  - `r9_skip`      → extra `r9_skip` (OKF 가 unknown key tolerate)
  - `last_ingested_from` 의 path 가 in-repo 일 때 → body 에 `# Citations` section 추가 (SPEC §8 h1, v0.2 legacy fallback)

Cross-link rewriting (OKF §5.1 bundle-relative):
  - 위키 `[[path/to/page]]` → `[page](../path/to/page.md)` body cross-link
  - `[[path/to/page#anchor]]` → `[page](../path/to/page.md#anchor)`

Usage:
    from workflow_kit.okf_export import export_wiki_to_okf, WikiToOkfError

    export_wiki_to_okf(
        wiki_root=Path("ai-workflow/wiki"),
        out_bundle=Path("/tmp/okf_bundle"),
        page_filter=lambda p: p.name != "okf-open-knowledge-format.md",  # skip self
    )

CLI:
    python -m workflow_kit.okf_export --wiki ai-workflow/wiki --out /tmp/okf_bundle
    python -m workflow_kit.okf_export --wiki ai-workflow/wiki --out /tmp/okf_bundle --include okf-open-knowledge-format
    python -m workflow_kit.okf_export --wiki ai-workflow/wiki/concepts/okf-open-knowledge-format.md --out /tmp/okf_one
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

# ---------------------------------------------------------------------------
# OKF spec constants (SPEC.md §3.1 reserved filenames, §4.1 frontmatter)
# ---------------------------------------------------------------------------
#: 우리가 준수를 선언하는 OKF spec 버전. **여기가 정본이다** — export 기본값,
#: 소비자 호환 판정(`okf_import.OUR_OKF_VERSION`), CLI·문서 문구가 전부 이 값에서
#: 나온다. 상수를 export 쪽에 두는 이유는 의존 방향이다: `okf_import` 가
#: `okf_export` 를 참조하므로 반대로 두면 순환이 된다.
#:
#: 2026-08-20 (ADR-026): v0.1 → **v0.2**. legacy 형태(`timestamp`, 본문
#: `# Citations`)는 SPEC §13.1 이 소비자 fallback 을 명시하므로 **남긴 채**
#: 정규 필드를 더한다 — 한 번들이 v0.1·v0.2 소비자를 다 만족한다.
OKF_SPEC_VERSION: str = "0.2"

OKF_RESERVED_FILES: frozenset[str] = frozenset({"index.md", "log.md"})

# Our wiki 5 valid `type` values (SCHEMA.md §1) — all map cleanly to OKF free-string
OKF_WIKI_VALID_TYPES: frozenset[str] = frozenset({"entity", "concept", "decision", "pattern", "query"})

#: OKF v0.2 §5.4 의 `status` 어휘. v0.1 에서는 `status` 가 정규 필드가 아니어서
#: 우리 값을 그대로 실어도 됐지만, v0.2 에서 **정규 필드로 승격**되면서 사정이
#: 달라졌다. §11 의 관용 보장("consumers MUST NOT reject ... unknown additional
#: frontmatter keys")은 *unknown key* 에만 걸리므로 정규 필드가 된 `status` 에는
#: 안 걸린다 — v0.2 소비자가 `stable` 필터를 걸면 우리 71장 중 69장이 조용히 빠진다.
OKF_STATUS_VOCABULARY: frozenset[str] = frozenset({"draft", "stable", "deprecated"})

#: 우리 wiki 어휘 → OKF v0.2 어휘. 우리 원래 값은 `wiki_status` 확장 키로 보존한다
#: (§11 이 unknown key 를 보장하므로 그쪽은 안전하다).
#:
#: `accepted`/`active` → `stable`: 둘 다 "지금 유효한 문서" 다.
#: `proposed`/`draft` → `draft`: §5.4 의 draft 는 "not yet reviewed; possibly
#: incomplete" 라 proposed ADR 의 뜻과 같다.
#: `superseded`/`deprecated` → `deprecated`: §5.4 의 "kept for links and history".
OKF_STATUS_MAP: dict[str, str] = {
    "active": "stable",
    "accepted": "stable",
    "stable": "stable",
    "draft": "draft",
    "proposed": "draft",
    "deprecated": "deprecated",
    "superseded": "deprecated",
}

#: 어휘 밖의 값을 만났을 때 실을 값.
#:
#: **`status` 를 빼는 것은 답이 아니다** — §5.4 가 `Absent status ⇒ stable` 이라고
#: 정하므로, 생략은 "안 정함" 이 아니라 **stable 이라는 주장**이다. 모르는 상태를
#: stable 로 세면 그게 거짓 안심이다 (저장소 규칙 *모름 ≠ 안전*). 그래서 가장
#: 보수적인 `draft`("not yet reviewed") 로 내리고, 원래 값은 `wiki_status` 에 남겨
#: 소비자가 원문을 볼 수 있게 한다.
OKF_STATUS_FALLBACK: str = "draft"


def map_status_to_okf(wiki_status: str | None) -> str | None:
    """wiki `status` → OKF v0.2 §5.4 어휘. 값이 없으면 None (필드 미기재)."""
    if not wiki_status:
        return None
    return OKF_STATUS_MAP.get(wiki_status.strip().lower(), OKF_STATUS_FALLBACK)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class WikiToOkfError(Exception):
    """Base error for wiki → OKF export."""


class InvalidFrontmatterError(WikiToOkfError):
    """Wiki page 의 frontmatter 가 우리 schema 위반."""


# ---------------------------------------------------------------------------
# Frontmatter (YAML)
# ---------------------------------------------------------------------------
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


@dataclass(frozen=True)
class Frontmatter:
    """Parsed wiki page frontmatter (subset of our schema, OKF-export relevant fields)."""

    type: str
    status: str | None
    title: str | None
    description: str | None
    last_ingested_from: str | None
    created: str | None
    updated: str | None
    related_pages: tuple[str, ...]
    tags: tuple[str, ...]
    adr_id: str | None
    vcs_commit: str | None  # ADR-018/019: per-page commit SHA for pinned URL
    vcs_ref: str | None    # ADR-018: per-page ref (branch/tag) for ref-pinned URL
    r9_skip: bool
    raw: dict[str, object] = field(default_factory=dict)
    @classmethod
    def parse(cls, text: str) -> "Frontmatter":
        """Parse wiki frontmatter block. Raises InvalidFrontmatterError on missing `type`."""
        m = _FRONTMATTER_RE.match(text)
        if not m:
            raise InvalidFrontmatterError("no YAML frontmatter block found (--- delimiters)")
        body_yaml = m.group(1)
        # Minimal YAML parse — our schema uses scalar values + list-of-strings only.
        # Avoid pulling in PyYAML dependency for this PoC.
        raw: dict[str, object] = _parse_simple_yaml(body_yaml)

        if "type" not in raw or not str(raw["type"]).strip():
            raise InvalidFrontmatterError("missing or empty `type` field (required by OKF §4.1)")

        type_val = str(raw["type"]).strip()
        if type_val not in OKF_WIKI_VALID_TYPES:
            # OKF 자체는 free-string tolerate. 우리 가 strict. warn 만.
            pass

        return cls(
            type=type_val,
            status=str(raw.get("status", "")).strip() or None,
            title=str(raw.get("title", "")).strip() or None,
            description=str(raw.get("description", "")).strip() or None,
            last_ingested_from=str(raw.get("last_ingested_from", "")).strip() or None,
            created=str(raw.get("created", "")).strip() or None,
            updated=str(raw.get("updated", "")).strip() or None,
            related_pages=tuple(_as_str_list(raw.get("related_pages"))),
            tags=tuple(_as_str_list(raw.get("tags"))),
            adr_id=str(raw.get("adr_id", "")).strip() or None,
            vcs_commit=str(raw.get("vcs_commit", "")).strip() or None,
            vcs_ref=str(raw.get("vcs_ref", "")).strip() or None,
            r9_skip=bool(raw.get("r9_skip", False)),
            raw=raw,
        )


def _parse_simple_yaml(body: str) -> dict[str, object]:
    """Minimal YAML parser for our frontmatter subset:
    - `key: value` (scalar string)
    - `key:` (empty / null)
    - `key: [a, b, c]` (inline list)
    - `key:\n  - a\n  - b` (block list)
    Lines starting with `#` are comments.
    """
    out: dict[str, object] = {}
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if ":" not in line and not line.startswith(" "):
            i += 1
            continue
        # Detect key (not indented)
        if not line.startswith((" ", "\t")):
            key, _, rest = line.partition(":")
            key = key.strip()
            rest = rest.strip()
            if not rest:
                # could be block list
                # peek next non-empty lines for "- ..."
                j = i + 1
                block_items: list[str] = []
                while j < len(lines):
                    nxt = lines[j]
                    if not nxt.strip():
                        j += 1
                        continue
                    if nxt.lstrip().startswith("- "):
                        block_items.append(nxt.lstrip()[2:].strip())
                        j += 1
                    else:
                        break
                if block_items:
                    out[key] = block_items
                    i = j
                    continue
                else:
                    out[key] = ""
                    i += 1
                    continue
            # inline list `[a, b]`
            if rest.startswith("[") and rest.endswith("]"):
                inner = rest[1:-1].strip()
                if not inner:
                    out[key] = []
                else:
                    out[key] = [s.strip().strip('"\'') for s in inner.split(",") if s.strip()]
                i += 1
                continue
            # boolean / scalar
            if rest in ("true", "True", "yes"):
                out[key] = True
            elif rest in ("false", "False", "no"):
                out[key] = False
            elif rest in ("null", "None", "~"):
                out[key] = None
            else:
                # strip surrounding quotes
                if (rest.startswith('"') and rest.endswith('"')) or (
                    rest.startswith("'") and rest.endswith("'")
                ):
                    rest = rest[1:-1]
                out[key] = rest
            i += 1
        else:
            i += 1
    return out


def _as_str_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        # Inline list
        if s.startswith("[") and s.endswith("]"):
            inner = s[1:-1].strip()
            if not inner:
                return []
            return [t.strip().strip('"\'') for t in inner.split(",") if t.strip()]
        return [s]
    return [str(value)]


# ---------------------------------------------------------------------------
# Mapping: wiki frontmatter → OKF frontmatter
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class OkfMapping:
    """Mapping decision log (per OKF spec §4.1)."""

    frontmatter_lines: tuple[str, ...]
    body_suffix: tuple[str, ...]  # extra body section(s) appended (e.g. # Citations, ## See Also)


def _date_to_iso8601(date_str: str | None) -> str | None:
    """`YYYY-MM-DD` → `YYYY-MM-DDTHH:MM:SSZ` (OKF recommended, ISO 8601)."""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _derive_resource(
    last_ingested_from: str | None,
    *,
    repo_root: Path | None = None,
    resolve: bool = True,
    vcs_commit: str | None = None,
    vcs_ref: str | None = None,
) -> str | None:
    """OKF `resource`: canonical URI for the underlying asset (ADR-006 + ADR-018).

    Resolution order:
    1. 복합 값(공백 포함) → None. `last_ingested_from` 은 자유 서술이고 URI 가 아니다.
    2. URL form (`http://` / `https://`) → 그대로 사용
    3. in-repo path 인데 **저장소에 없는 경로** → None (없는 URL 을 만들지 않는다)
    4. in-repo path + `vcs_commit` 명시 → commit-pinned URL (immutable, ADR-018)
    5. in-repo path + `vcs_ref` 명시 → ref-pinned URL (mutable but explicit)
    6. in-repo path + `resolve=True` + `repo_root` → `path_resolver.resolve_in_repo_path_to_url`
    7. in-repo path + `resolve=False` → None (ADR-006 status quo)
    8. None / empty → None

    **1 과 3 이 v1.0.4 에서 추가된 이유** (§2.58): 이 함수는 `last_ingested_from` 값을
    통째로 경로로 취급했다. 그런데 wiki 의 그 필드는 ``a + b``, ``path §4``,
    ``external (https://…, 2026-06-16)`` 같은 **출처 메모** 다. 그 값을 `path_resolver`
    에 넘기면 앞에 origin 만 붙어서 ``…/blob/main/external`` 처럼 *존재한 적 없는*
    URL 이 만들어지고, 그게 bundle 의 `resource` 로 커밋됐다. V-R10 은 그걸 "죽은 링크"
    라고 보고했지만 죽은 것이 아니라 **태어난 적이 없는** 링크였다.

    파생물을 만드는 쪽이 규약을 알아야 한다 — canonical URI 로 만들 수 없는 값이면
    `resource` 를 비우고, 호출부가 `last_ingested_from` extra key + Citations 로
    보존한다(사실을 줄이지 않으면서 URI 자리를 날조하지 않는 유일한 선택).
    """
    if not last_ingested_from:
        return None
    value = last_ingested_from.strip()
    if not value or value.split() != [value]:
        # 공백이 있으면 URI 가 아니라 서술이다.
        return None
    if value.startswith(("http://", "https://")):
        return value
    if not resolve or repo_root is None:
        return None
    if not (repo_root / value).exists():
        # 저장소에 없는 경로다 (`external`, glob 표기 등). 경로 해석은 사실 확인 없이
        # 문자열만 이어 붙이므로, 존재 여부는 부르는 쪽이 물어야 한다.
        return None
    last_ingested_from = value
    # Lazy import to avoid hard dependency if not used
    try:
        from workflow_kit.path_resolver import (
            resolve_in_repo_path_to_url,
            resolve_in_repo_path_to_url_pinned,
        )
    except ImportError:
        return None
    # commit-pinned URL (immutable) takes precedence over default-branch URL
    if vcs_commit or vcs_ref:
        return resolve_in_repo_path_to_url_pinned(
            last_ingested_from, repo_root,
            commit_sha=vcs_commit, ref=vcs_ref,
        )
    return resolve_in_repo_path_to_url(last_ingested_from, repo_root)


def _extract_title_and_description(body: str, fallback_title: str) -> tuple[str, str | None]:
    """Derive `title` (first H1) and `description` (first prose paragraph) from body.

    OKF §4.1 권장 field 가 frontmatter 에 없으면 body 에서 derive. 이건 consumer-friendly
    (index.md 생성기, search snippet) 위해 중요.
    """
    # title: 첫 `# ` (H1)
    title = fallback_title
    description: str | None = None
    lines = body.splitlines()
    i = 0
    # skip leading empty lines
    while i < len(lines) and not lines[i].strip():
        i += 1
    # first non-empty, non-heading paragraph
    prose_buf: list[str] = []
    saw_heading_or_block = False
    for line in lines[i:]:
        s = line.strip()
        if s.startswith("# "):
            title = s[2:].strip()
            saw_heading_or_block = True
            continue
        if s.startswith(("#", "```", "|", "- ", "* ", "> ", "###", "##")):
            if prose_buf:
                break
            saw_heading_or_block = True
            continue
        if not s:
            if prose_buf:
                break
            continue
        # plain prose line
        if not saw_heading_or_block and not title:
            continue
        prose_buf.append(s)
        if len(prose_buf) >= 3:
            break
    if prose_buf:
        joined = " ".join(prose_buf)
        if len(joined) > 200:
            joined = joined[:197] + "..."
        description = joined
    return title, description


def _derive_tags(frontmatter: Frontmatter) -> tuple[str, ...]:
    """OKF `tags` = wiki `tags` ∪ derived from `status` + `type`."""
    out: list[str] = list(frontmatter.tags)
    if frontmatter.status:
        out.append(f"status:{frontmatter.status}")
    if frontmatter.type:
        out.append(f"wiki-type:{frontmatter.type}")
    # de-dupe, preserve order
    seen: set[str] = set()
    deduped: list[str] = []
    for t in out:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    return tuple(deduped)


def _scalar(value: object) -> str:
    """YAML scalar 직렬화 — 특수문자가 있으면 인용한다."""
    text = str(value)
    if any(c in text for c in [":", "#", "&", "*", "{", "}", "[", "]", "|", ">", "<", "%", "@", "`"]):
        return f'"{text}"'
    return text


def map_frontmatter_to_okf(
    frontmatter: Frontmatter,
    body: str = "",
    *,
    repo_root: Path | None = None,
    resolve: bool = True,
    vcs_commit: str | None = None,
    vcs_ref: str | None = None,
    content_hash: str | None = None,
    range_refs: tuple[str, str] | None = None,
) -> OkfMapping:
    """wiki Frontmatter → OKF frontmatter (SPEC.md §4.1) + body suffix (Citations §8).

    vcs_commit/vcs_ref priority: explicit kwarg > frontmatter field. Per-page
    frontmatter `vcs_commit` field override site-wide CLI (ADR-018 follow-up).


    Field ordering follows SPEC.md §4.1 권장 priority:
    """
    okf: dict[str, object] = {}

    # required
    okf["type"] = frontmatter.type

    # recommended (priority order per SPEC.md §4.1)
    # 1. title — frontmatter 우선, 없으면 body H1 에서 derive, 그것도 없으면 파일명 stem
    fallback_title = frontmatter.type  # last-resort fallback
    body_title: str | None = None
    body_description: str | None = None
    if body:
        body_title, body_description = _extract_title_and_description(body, fallback_title)
    if frontmatter.title:
        okf["title"] = frontmatter.title
    elif body_title:
        okf["title"] = body_title
    # 2. description — frontmatter 우선, 없으면 body 첫 prose paragraph
    if frontmatter.description:
        okf["description"] = frontmatter.description
    elif body_description:
        okf["description"] = body_description
    # 3. resource — URL last_ingested_from 만 매핑
    # vcs_commit priority: kwarg > frontmatter field
    effective_vcs_commit = vcs_commit if vcs_commit else frontmatter.vcs_commit
    effective_vcs_ref = vcs_ref if vcs_ref else frontmatter.vcs_ref
    resource = _derive_resource(frontmatter.last_ingested_from, repo_root=repo_root, resolve=resolve, vcs_commit=effective_vcs_commit, vcs_ref=effective_vcs_ref)
    # v0.7.39+ ADR-019 layer 1: append ?hash=sha256:<hex> when content_hash provided
    if resource and content_hash:
        sep = "&" if "?" in resource else "?"
        resource = f"{resource}{sep}hash={content_hash}"
    # v0.7.40+ ADR-019 layer 2: append ?range=<sha1>..<sha2> when range_refs provided
    if resource and range_refs:
        sha1, sha2 = range_refs
        sep = "&" if "?" in resource else "?"
        resource = f"{resource}{sep}range={sha1}..{sha2}"
    if resource:
        okf["resource"] = resource
    tags = _derive_tags(frontmatter)
    if tags:
        okf["tags"] = list(tags)
    # `timestamp` 는 v0.2 에서 `generated.at` 으로 대체됐지만 **남긴다** — §13.1 이
    # "Consumers MAY fall back to a legacy `timestamp` when `generated` is absent"
    # 라고 적었고, 우리는 `generated` 를 내지 않기로 했기 때문이다 (아래 참조).
    timestamp = _date_to_iso8601(frontmatter.updated) or _date_to_iso8601(frontmatter.created)
    if timestamp:
        okf["timestamp"] = timestamp

    # `generated` 는 **의도적으로 내지 않는다** (ADR-026).
    #
    # §5.2 는 `generated.by` 를 REQUIRED 로 두고 §7 은 그것을 actor 로 규정한다.
    # 우리 wiki 는 페이지별 저자/생성 주체를 기록하지 않는다 — 도구 이름을 적으면
    # "이 도구가 내용을 썼다" 는 거짓이 되고, `human:` 을 적으면 생성물 페이지까지
    # 사람이 쓴 것으로 만든다. 근거 없이 채우느니 비워 두고 §13.1 의 `timestamp`
    # fallback 에 맡긴다 (저장소 규칙 *없는 것을 있는 것처럼 채우지 않는다*).

    # `sources` (v0.2 §5.1) — 우리 `last_ingested_from` 이 정확히 이 필드가 말하는
    # "이 개념이 파생된 재료" 다. v0.1 에서는 URL 일 때만 `resource` 로 나가고
    # in-repo 경로는 본문 산문(`# Citations`)으로만 남았는데, §5.1 은 entry 의
    # `resource` 값으로 **번들 상대 경로도** 허용한다 — 그래서 in-repo 출처가
    # 처음으로 기계가 읽는 필드에 들어간다.
    if frontmatter.last_ingested_from:
        source_ref = resource or frontmatter.last_ingested_from.strip()
        okf["sources"] = [{"resource": source_ref}]

    # Extensions (SPEC.md §4.1: producers MAY include additional keys; consumers SHOULD NOT reject)
    if frontmatter.created:
        okf["created"] = frontmatter.created
    if frontmatter.status:
        mapped = map_status_to_okf(frontmatter.status)
        if mapped:
            okf["status"] = mapped
        # 우리 어휘는 잃지 않는다 — 매핑은 소비자를 위한 것이고 원문은 확장 키로 남는다.
        if mapped != frontmatter.status:
            okf["wiki_status"] = frontmatter.status
    if frontmatter.related_pages:
        okf["related_pages"] = list(frontmatter.related_pages)
    if frontmatter.adr_id:
        okf["adr_id"] = frontmatter.adr_id
    if frontmatter.r9_skip:
        okf["r9_skip"] = True
    if frontmatter.last_ingested_from and not resource:
        # in-repo path — preserve as extra key (unknown key OK per §4.1)
        okf["last_ingested_from"] = frontmatter.last_ingested_from

    # serialize
    lines: list[str] = ["---"]
    for key, value in okf.items():
        if isinstance(value, list):
            if value and all(isinstance(v, dict) for v in value):
                # `sources` 같은 mapping list — block 형식으로 낸다.
                lines.append(f"{key}:")
                for entry in value:
                    items = list(entry.items())
                    first_k, first_v = items[0]
                    lines.append(f"  - {first_k}: {_scalar(first_v)}")
                    for k, v in items[1:]:
                        lines.append(f"    {k}: {_scalar(v)}")
            elif all(isinstance(v, str) and "," not in v and "[" not in v and "]" not in v for v in value):
                inline = ", ".join(value)
                lines.append(f"{key}: [{inline}]")
            else:
                lines.append(f"{key}:")
                for v in value:
                    lines.append(f"  - {v}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, str):
            if any(c in value for c in [":", "#", "&", "*", "{", "}", "[", "]", "|", ">", "<", "%", "@", "`"]):
                lines.append(f'{key}: "{value}"')
            else:
                lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")

    # body suffix: `# Citations` for in-repo last_ingested_from (per SPEC.md §8).
    #
    # 2026-08-18 실측 (TASK-2026-08-18-main-006): 우리는 `##` (h2) 로 내고 있었다.
    # SPEC 이 정한 것은 **h1 `# Citations`** 이고, v0.2 는 이 절을 `sources`
    # frontmatter 로 대체하면서 "consumers ... MAY still parse a legacy
    # `# Citations` body list for v0.1 documents" 라고 적었다 — 즉 h2 로 내면
    # v0.1 에서도 비표준이고, v0.2 소비자의 **legacy fallback 경로에서도 안 걸린다**.
    body_suffix: list[str] = []
    if frontmatter.last_ingested_from and not resource:
        body_suffix.append("")
        body_suffix.append("# Citations")
        body_suffix.append("")
        citation = frontmatter.last_ingested_from.strip()
        if citation.split() == [citation]:
            body_suffix.append(f"[1] [{citation}]({citation})")
        else:
            # 복합 출처 메모는 링크 대상이 아니다. `[a + b](a + b)` 는 깨진 링크다 —
            # 사실은 그대로 남기고 링크만 만들지 않는다 (§2.58).
            body_suffix.append(f"[1] {citation}")
    if frontmatter.related_pages:
        body_suffix.append("")
        body_suffix.append("## See Also")
        body_suffix.append("")
        for ref in frontmatter.related_pages:
            # OKF §5.1 bundle-relative link
            body_suffix.append(f"- [{ref}](../{ref})")

    return OkfMapping(frontmatter_lines=tuple(lines), body_suffix=tuple(body_suffix))


# ---------------------------------------------------------------------------
# Body rewriting: [[wiki-link]] → [text](../path.md#anchor)
# ---------------------------------------------------------------------------
_WIKI_LINK_RE = re.compile(r"\[\[([^\]]+?)\]\]")


def rewrite_wiki_links_to_okf(body: str) -> str:
    """[[path/to/page]] → [page](../path/to/page.md)
    [[path/to/page#anchor]] → [page](../path/to/page.md#anchor)
    """

    def _sub(m: re.Match[str]) -> str:
        target = m.group(1).strip()
        if "#" in target:
            path, _, anchor = target.partition("#")
            path = path.strip()
            anchor = anchor.strip()
        else:
            path = target
            anchor = ""
        # display text: page basename (sans path prefix)
        display = path.rsplit("/", 1)[-1] if path else target
        # OKF bundle-relative: ../<path>.md
        if not path.endswith(".md"):
            url = f"../{path}.md"
        else:
            url = f"../{path}"
        if anchor:
            url = f"{url}#{anchor}"
        return f"[{display}]({url})"

    return _WIKI_LINK_RE.sub(_sub, body)


def generate_index_md(
    pages: list[tuple[Path, str, Frontmatter]],
    *,
    okf_version: str = OKF_SPEC_VERSION,
    generated_at: str | None = None,
    generator: str = "workflow_kit.okf_export v0.7.34+",
) -> str:
    """Generate bundle root `index.md` content.

    OKF SPEC.md §6 index file format. Frontmatter per §11 `okf_version`.
    Body: section heading per type (concepts/decisions/entities/patterns/queries)
    with bullet list of `[title](relative-url) — description` entries.

    Args:
        pages: list of (out_path, relative_path, frontmatter) tuples for emitted pages
        okf_version: OKF spec version to declare in frontmatter
        generated_at: ISO 8601 timestamp (default: now UTC)
        generator: generator identifier string

    Returns:
        Full index.md content (frontmatter + body), ready to write.
    """
    if generated_at is None:
        generated_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # group by top-level dir (concepts/decisions/entities/patterns/queries)
    by_type: dict[str, list[tuple[str, str, str]]] = {}
    for _out_path, rel, fm in pages:
        parts = Path(rel).parts
        if not parts:
            continue
        type_dir = parts[0]
        # title fallback: H1 from body if not in frontmatter (we use fm.title if set)
        title = fm.title or Path(rel).stem
        description = (fm.description or "").strip()
        # shorten description to 1 line
        if description and len(description) > 120:
            description = description[:117] + "..."
        entry = (rel, title, description)
        by_type.setdefault(type_dir, []).append(entry)

    # stable ordering by type dir name + relative path
    type_order = ["concepts", "decisions", "entities", "patterns", "queries"]
    sorted_types = sorted(by_type.keys(), key=lambda t: (type_order.index(t) if t in type_order else 99, t))

    # frontmatter
    lines: list[str] = ["---"]
    lines.append(f"okf_version: \"{okf_version}\"")
    lines.append(f"generated_at: \"{generated_at}\"")
    lines.append(f"generator: \"{generator}\"")
    lines.append("---")
    lines.append("")
    lines.append("# Knowledge Bundle Index")
    lines.append("")
    lines.append(f"Auto-generated by `{generator}` on {generated_at}. OKF spec v{okf_version}.")
    lines.append("")

    for type_dir in sorted_types:
        type_title = type_dir.capitalize()
        lines.append(f"## {type_title}")
        lines.append("")
        for rel, title, description in sorted(by_type[type_dir], key=lambda e: e[0]):
            if description:
                lines.append(f"- [{title}]({rel}) — {description}")
            else:
                lines.append(f"- [{title}]({rel})")
        lines.append("")
    return "\n".join(lines) + "\n"


def _compute_bundle_integrity_hash(
    pages: list[tuple[Path, str, Frontmatter]],
) -> str:
    """SHA256 of all exported page bytes, sorted by relative path (deterministic).

    v0.7.38+ ADR-019 convention. The integrity hash is byte-level; consumers can
    recompute and compare to detect any byte change in the bundle.
    """
    import hashlib
    sha = hashlib.sha256()
    for out_path, rel, _fm in sorted(pages, key=lambda e: e[1]):
        sha.update(out_path.read_bytes())
    return f"sha256:{sha.hexdigest()}"


def _write_bundle_manifest(
    out_bundle: Path,
    pages: list[tuple[Path, str, Frontmatter]],
    *,
    vcs_commit: str | None = None,
    vcs_ref: str | None = None,
) -> Path:
    """Emit `okf-bundle.yaml` (per-bundle manifest) at the bundle root.

    Schema (v0.7.38+, ADR-019 convention):
      okf_version: "<OKF_SPEC_VERSION>"
      generated_at: <ISO 8601>
      generator: "workflow_kit.okf_export vX.Y.Z"
      vcs_commit: <sha>  (optional)
      vcs_ref: <ref>     (optional)
      integrity_hash: "sha256:<hex>"
      page_count: N

    `okf_version` 은 `OKF_SPEC_VERSION` 에서 파생한다 — 같은 번들의 index.md 와
    이 매니페스트는 **같은 사실을 말하는 두 자리**이고, `okf_import` 감지 2순위와
    `wk okf-version-check --bundle` 이 이쪽을 읽는다. ADR-026 이행 때 index.md 만
    정본 참조로 바뀌고 여기는 '0.1' 리터럴로 남아 두 선언이 갈렸었다
    (TASK-2026-08-24-main-008).
    """
    import hashlib
    try:
        from workflow_kit import __version__ as _wk_version
    except (ImportError, ModuleNotFoundError):
        _wk_version = "unknown"
    integrity = _compute_bundle_integrity_hash(pages)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest_lines = [
        f"okf_version: '{OKF_SPEC_VERSION}'",
        f"generated_at: '{generated_at}'",
        f"generator: 'workflow_kit.okf_export {_wk_version}'",
    ]
    if vcs_commit:
        manifest_lines.append(f"vcs_commit: '{vcs_commit}'")
    if vcs_ref:
        manifest_lines.append(f"vcs_ref: '{vcs_ref}'")
    manifest_lines.append(f"integrity_hash: '{integrity}'")
    manifest_lines.append(f"page_count: {len(pages)}")
    manifest_path = out_bundle / "okf-bundle.yaml"
    manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    return manifest_path


# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ExportReport:
    """Result summary of a wiki → OKF export run."""

    pages_exported: int
    pages_skipped: int
    out_bundle: Path
    errors: tuple[str, ...] = field(default_factory=tuple)


def _is_wiki_page(path: Path, wiki_root: Path) -> bool:
    """wiki page 인지 판별: 5 type 디렉토리 안의 .md."""
    if path.suffix != ".md":
        return False
    try:
        rel = path.relative_to(wiki_root)
    except ValueError:
        return False
    parts = rel.parts
    if not parts:
        return False
    if parts[0] not in ("concepts", "decisions", "entities", "patterns", "queries"):
        return False
    if path.name in OKF_RESERVED_FILES or path.name in ("SCHEMA.md", "INGEST_GUIDE.md", "index.md", "log.md"):
        return False
    return True


def _out_path_for_wiki_page(wiki_page: Path, wiki_root: Path, out_bundle: Path) -> Path:
    """wiki page path → OKF bundle path.

    Example:
        ai-workflow/wiki/concepts/foo.md → <bundle>/concepts/foo.md
        ai-workflow/wiki/decisions/adr-005-x.md → <bundle>/decisions/adr-005-x.md
    """
    rel = wiki_page.relative_to(wiki_root)
    return out_bundle / rel


def export_wiki_page(
    wiki_page: Path,
    out_path: Path,
    *,
    repo_root: Path | None = None,
    resolve: bool = True,
    vcs_commit: str | None = None,
    vcs_ref: str | None = None,
    content_hash: str | None = None,
    range_refs: tuple[str, str] | None = None,
) -> tuple[int, int]:
    text = wiki_page.read_text(encoding="utf-8")

    # split frontmatter / body
    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise InvalidFrontmatterError(f"{wiki_page}: no frontmatter block")
    body_text = m.group(2).rstrip("\n")
    fm = Frontmatter.parse(text)
    # v0.7.39+ ADR-019 layer 1: auto-compute content_hash from full page text (frontmatter + body)
    if content_hash == "auto":
        import hashlib
        content_hash = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    mapping = map_frontmatter_to_okf(fm, body=body_text, repo_root=repo_root, resolve=resolve, vcs_commit=vcs_commit, vcs_ref=vcs_ref, content_hash=content_hash, range_refs=range_refs)
    body_rewritten = rewrite_wiki_links_to_okf(body_text)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_text = "\n".join(mapping.frontmatter_lines) + "\n" + body_rewritten + "\n"
    if mapping.body_suffix:
        out_text += "\n".join(mapping.body_suffix) + "\n"
    out_path.write_text(out_text, encoding="utf-8")
    return (1, 0)
def export_wiki_to_okf(
    wiki_root: Path,
    out_bundle: Path,
    page_filter: Callable[[Path], bool] | None = None,
    *,
    repo_root: Path | None = None,
    resolve: bool = True,
    vcs_commit: str | None = None,
    vcs_ref: str | None = None,
    emit_manifest: bool = True,
    content_hash: str | None = None,
    range_refs: tuple[str, str] | None = None,
) -> ExportReport:
    """Export a wiki directory tree to an OKF bundle directory.

    Args:
        wiki_root: path to ai-workflow/wiki/ (or subdir thereof)
        out_bundle: target bundle directory (created if missing)
        page_filter: optional predicate(wiki_page) → bool. True = include.
        repo_root: path to git repository root (for `path_resolver` integration)
        resolve: if True (default), in-repo `last_ingested_from` path → GitHub URL
            via `workflow_kit.path_resolver`. Set False to skip resolve (ADR-006 status quo).

    Returns:
        ExportReport with counts and any per-file errors.
    """
    wiki_root = wiki_root.resolve()
    out_bundle = out_bundle.resolve()
    out_bundle.mkdir(parents=True, exist_ok=True)
    exported = 0
    skipped = 0
    errors: list[str] = []
    collected_pages: list[tuple[Path, str, Frontmatter]] = []

    for path in sorted(wiki_root.rglob("*.md")):
        if not _is_wiki_page(path, wiki_root):
            continue
        if page_filter and not page_filter(path):
            skipped += 1
            continue
        try:
            out_path = _out_path_for_wiki_page(path, wiki_root, out_bundle)
            ex, sk = export_wiki_page(
                path, out_path, repo_root=repo_root, resolve=resolve,
                vcs_commit=vcs_commit, vcs_ref=vcs_ref, content_hash=content_hash, range_refs=range_refs,
            )
            skipped += sk
            exported += ex
            try:
                rel = str(out_path.relative_to(out_bundle))
                exported_text = out_path.read_text(encoding="utf-8")
                fm = Frontmatter.parse(exported_text)
                collected_pages.append((out_path, rel, fm))
            except Exception:
                pass
        except WikiToOkfError as e:
            errors.append(str(e))
            skipped += 1

    # emit bundle root index.md (OKF SPEC.md §6 + §11)
    if collected_pages:
        try:
            index_content = generate_index_md(collected_pages)
            (out_bundle / "index.md").write_text(index_content, encoding="utf-8")
        except Exception as e:
            errors.append(f"index.md emission failed: {e}")

    # emit per-bundle manifest: okf-bundle.yaml (v0.7.38+, ADR-019 convention)
    # integrity_hash = SHA256 of all exported page bytes (deterministic order)
    if emit_manifest and collected_pages:
        try:
            _write_bundle_manifest(
                out_bundle, collected_pages,
                vcs_commit=vcs_commit, vcs_ref=vcs_ref,
            )
        except Exception as e:
            errors.append(f"okf-bundle.yaml emission failed: {e}")
    return ExportReport(
        pages_exported=exported,

        pages_skipped=skipped,
        out_bundle=out_bundle,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="workflow_kit.okf_export",
        description=f"wiki → OKF v{OKF_SPEC_VERSION} bundle export (PoC, v0.7.33+).",
    )
    p.add_argument(
        "--wiki",
        type=Path,
        required=True,
        help="path to ai-workflow/wiki/ root (or single .md page)",
    )
    p.add_argument(
        "--out",
        type=Path,
        required=True,
        help="output OKF bundle directory (created if missing)",
    )
    p.add_argument(
        "--include",
        action="append",
        default=[],
        help="page name substring to include (repeatable); default = all",
    )
    p.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="page name substring to exclude (repeatable); applied after --include",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="JSON output (ExportReport as JSON)",
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="path to git repo root (for path_resolver integration, ADR-008)",
    )
    p.add_argument(
        "--no-resolve",
        action="store_true",
        help="skip in-repo path → URL resolve (ADR-006 status quo; default: resolve ON)",
    )
    p.add_argument(
        "--vcs-commit",
        help="commit SHA for commit-pinned URL emit (ADR-018). Format: 7-40 hex chars.",
    )
    p.add_argument(
        "--vcs-ref",
        help="ref (branch/tag) for ref-pinned URL emit (ADR-018).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    wiki = args.wiki.resolve()
    if not wiki.exists():
        print(f"ERROR: --wiki path not found: {wiki}", file=sys.stderr)
        return 2

    if wiki.is_file():
        # single page mode
        if wiki.suffix != ".md":
            print(f"ERROR: --wiki file is not .md: {wiki}", file=sys.stderr)
            return 2
        try:
            # Use wiki's parent as root so the relative path resolves under "concepts/..." etc.
            guessed_root = wiki.parent.parent  # .../concepts/foo.md → .../concepts/.. = wiki
            out_path = args.out / wiki.relative_to(guessed_root)
            ex, sk = export_wiki_page(wiki, out_path)
            report = ExportReport(pages_exported=ex, pages_skipped=sk, out_bundle=args.out.resolve())
        except WikiToOkfError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
    else:
        includes: list[str] = list(args.include)
        excludes: list[str] = list(args.exclude)

        def _filter(p: Path) -> bool:
            name = p.name
            if includes and not any(inc in name for inc in includes):
                return False
            if excludes and any(exc in name for exc in excludes):
                return False
            return True

        repo_root = (args.repo_root or wiki).parent.parent.parent.parent  # heuristic: walk up from wiki/ to repo root
        # better: if --repo-root explicit, use it; else try to find git root
        if args.repo_root is None:
            from workflow_kit.path_resolver import _detect_origin_url
            # try each parent until origin found
            for candidate in [wiki, *wiki.parents]:
                if _detect_origin_url(candidate) is not None:
                    repo_root = candidate
                    break
            else:
                repo_root = wiki  # fallback
        report = export_wiki_to_okf(
            wiki, args.out, page_filter=_filter, repo_root=repo_root, resolve=not args.no_resolve,
        )

    if args.json:
        import json as _json

        print(
            _json.dumps(
                {
                    "pages_exported": report.pages_exported,
                    "pages_skipped": report.pages_skipped,
                    "out_bundle": str(report.out_bundle),
                    "errors": list(report.errors),
                },
                indent=2,
            )
        )
    else:
        print(f"OKF bundle exported: {report.out_bundle}")
        print(f"  pages_exported: {report.pages_exported}")
        print(f"  pages_skipped:  {report.pages_skipped}")
        if report.errors:
            print(f"  errors ({len(report.errors)}):")
            for err in report.errors:
                print(f"    - {err}")
    return 0 if not report.errors else 1


if __name__ == "__main__":
    sys.exit(main())
