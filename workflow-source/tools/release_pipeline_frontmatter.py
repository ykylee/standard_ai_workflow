"""release_pipeline.py 에서 추출한 release-note frontmatter parser 모듈 (TASK-2026-08-11-main-007).

`tools/release_pipeline.py` 의 release note frontmatter sync (v0.11.23+ P2)
parser helper 를 verbatim 으로 옮긴 것이다. `cmd_maturity_matrix_sync` 자체는
release_pipeline.py 에 남는다. `release_pipeline.py` 가
`from release_pipeline_frontmatter import *` 로 전량 재-export 하므로, 기존
check / caller 는 계속 `release_pipeline` 의 attribute
(`rp._parse_release_note_frontmatter` 등) 로 접근한다. 이 모듈은
release_pipeline 을 import 하지 않는다 (순환 금지).
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = [
    "_RE_FRONTMATTER_BLOCK",
    "_parse_release_note_frontmatter",
    "_parse_inline_list",
    "_parse_inline_obj",
    "_split_top_level",
    "_scalar_or_str",
]


# ---------------------------------------------------------------------------
# Release note frontmatter sync — v0.11.23+ (P2 — sync-maturity-matrix)
# ---------------------------------------------------------------------------
#
# Release note `Beta-v<X>.<Y>.<Z>.md` 의 YAML frontmatter 에 다음 key 를 적으면
# cmd_maturity_matrix_sync 가 workflow-source/core/maturity_matrix.json 을 자동 patch 한다.
#
# ---
# closed_phases: [11]
# promoted_skills:
#   - { name: session-start, to: stable, release: v0.11.19 }
# added_harnesses:
#   - { name: codewhale, release: v0.10.4 }
# deprecated_symbols:
#   - { module: phishing_federation_v4, name: fetch_federated_phishing_urls_v4, release: v0.9.0 }
# ---
#
# 본 frontmatter schema 는 release note 의 첫 `---`/`---` block 안에 위치.


_RE_FRONTMATTER_BLOCK = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def _parse_release_note_frontmatter(path: Path) -> tuple[dict, str]:
    """Release note 의 첫 YAML frontmatter block 을 parse. 본 frontmatter 의 *subset* 만 지원:

      key: value
      key: [v1, v2]
      key:
        - item
        - { name: x, release: y }

    Returns: ({parsed dict}, rest_of_text)
    """
    text = path.read_text(encoding="utf-8")
    m = _RE_FRONTMATTER_BLOCK.match(text)
    if not m:
        return {}, text
    block = m.group(1)
    rest = text[m.end():]
    parsed: dict = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s or s.startswith("#"):
            i += 1
            continue
        m2 = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if not m2:
            i += 1
            continue
        key = m2.group(1)
        rest_val = m2.group(2).strip()
        if rest_val == "":
            items: list = []
            j = i + 1
            while j < len(lines):
                child = lines[j]
                if not (child.startswith((" ", "\t"))):
                    break
                stripped = child.strip()
                if stripped.startswith("- "):
                    one = stripped[2:].strip()
                    if one.startswith("{") and one.endswith("}"):
                        items.append(_parse_inline_obj(one[1:-1]))
                    elif one.startswith("[") and one.endswith("]"):
                        items.append(_parse_inline_list(one[1:-1]))
                    else:
                        items.append(_scalar_or_str(one))
                j += 1
            parsed[key] = items
            i = j
            continue
        if rest_val.startswith("[") and rest_val.endswith("]"):
            parsed[key] = _parse_inline_list(rest_val[1:-1])
        elif rest_val.startswith("{") and rest_val.endswith("}"):
            parsed[key] = _parse_inline_obj(rest_val[1:-1])
        elif rest_val.lower() in ("true", "false"):
            parsed[key] = rest_val.lower() == "true"
        elif re.match(r"^-?\d+$", rest_val):
            parsed[key] = int(rest_val)
        else:
            parsed[key] = _scalar_or_str(rest_val.strip('"').strip("'"))
        i += 1
    return parsed, rest


def _parse_inline_list(body: str) -> list:
    out: list = []
    cur = ""
    depth = 0
    for ch in body:
        if ch in "[{": depth += 1
        elif ch in "]}": depth -= 1
        if ch == "," and depth == 0:
            s = cur.strip()
            cur = ""
            if s:
                out.append(_scalar_or_str(s))
            continue
        cur += ch
    if cur.strip():
        out.append(_scalar_or_str(cur.strip()))
    return out


def _parse_inline_obj(body: str) -> dict:
    """`name: value, name: value` 형식의 inline dict object 를 parse.

    본 frontmatter 의 subset 만 지원 — 값 은 string / int / bool (scalar) 만, nested ❌.
    """
    out: dict = {}
    items = _split_top_level(body, ",")
    for item in items:
        if ":" not in item:
            continue
        # 첫 `:` 만 split 로 사용.
        key, _, val = item.partition(":")
        k = key.strip()
        v = val.strip().strip('"').strip("'")
        if k:
            out[k] = _scalar_or_str(v)
    return out


def _split_top_level(body: str, sep: str) -> list[str]:
    """bracket depth 를 추적하면서 top-level `sep` 으로 split. nested 가 있어도 안전."""
    out: list[str] = []
    cur = ""
    depth = 0
    for ch in body:
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ""
            continue
        cur += ch
    if cur.strip():
        out.append(cur)
    return out


def _scalar_or_str(s: str):
    if s.lower() == "true": return True
    if s.lower() == "false": return False
    if re.match(r"^-?\d+$", s): return int(s)
    return s
