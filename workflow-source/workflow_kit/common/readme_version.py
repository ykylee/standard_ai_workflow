"""README 헤더 `- 버전:` 줄에 적힌 버전 리터럴의 정본 (v1.9.2).

## 왜 이 모듈이 있는가

README 의 헤더 **한 줄**에 같은 버전이 네 번 적힌다::

    - 버전: v1.9.1 (chapter ... ; package: standard-ai-workflow 1.9.1,
      runtime `__version__` = 1.9.1, latest tag **v1.9.1**)

발행 self-recover(`_fix_readme_header_version`)는 오랫동안 **맨 앞 하나만**
고쳤다. 나머지 셋은 71·72·73·74차 네 사이클 연속 손으로 고쳤고, 그중
`runtime` 과 `latest tag` 는 **어떤 검사도 보지 않았다** — `package:` 만
`check_readme_cross` case_3 이 봤고, 나머지 둘은 그 옆에 붙어 있었던 덕에
사람 눈에 걸렸을 뿐이다. 자동 수리가 닿지 않는 자리에 판정도 없으면 조용히
썩는다 (TASK-2026-09-03-main-004).

패턴을 여기 한 벌만 두고 **수리와 판정이 같은 것을 읽는다** — 복제하면 갈라진다.

## 왜 헤더 '줄' 단위인가

README 본문 아래쪽 changelog 에는 같은 모양의 문자열이 **역사 기록**으로 남아
있다 (예: v0.9.0 항목의 ``runtime `__version__` = v0.9.1-beta``). 그것은 그
릴리스 시점의 사실이므로 고치면 안 된다. 그래서 치환도 판정도 헤더 줄 하나로
범위를 좁힌다 — 문서 전체 치환은 역사를 덮어쓴다.
"""

from __future__ import annotations

import re
from typing import NamedTuple

#: 헤더 줄 자체를 고르는 패턴. 줄 맨 앞의 `- 버전: v` 로 식별한다.
HEADER_LINE_RE = re.compile(r"^- 버전: v[\d.]+.*$", re.MULTILINE)


class VersionLiteral(NamedTuple):
    """헤더 줄 안의 버전 리터럴 하나.

    Attributes:
        label: 사람이 읽는 이름. 판정 실패 메시지에 그대로 나간다.
        pattern: 버전 부분을 group 1 로 잡는 정규식. 접두/접미는 그룹 밖.
        template: ``{version}`` 을 채워 만드는 교체 문자열.
    """

    label: str
    pattern: re.Pattern[str]
    template: str


#: 헤더 줄 안에서 버전이 등장하는 자리 4개. 구 포맷(`v` 접두 / `-beta` 접미)도
#: 받아 마이그레이션한다 — v1.2.1 에서 stable 정리로 접미사가 사라졌다.
LITERALS: tuple[VersionLiteral, ...] = (
    VersionLiteral(
        "header",
        re.compile(r"- 버전: v([\d.]+)(?:-beta)?"),
        "- 버전: v{version}",
    ),
    VersionLiteral(
        "package",
        re.compile(r"package: standard-ai-workflow ([\d.]+)"),
        "package: standard-ai-workflow {version}",
    ),
    VersionLiteral(
        "runtime",
        re.compile(r"runtime `__version__` = v?([\d.]+)(?:-beta)?"),
        "runtime `__version__` = {version}",
    ),
    VersionLiteral(
        "latest_tag",
        re.compile(r"latest tag \*\*v([\d.]+)(?:-beta)?\*\*"),
        "latest tag **v{version}**",
    ),
)


def header_line(readme_text: str) -> str | None:
    """README 본문에서 헤더 `- 버전:` 줄을 고른다. 없으면 ``None``."""
    m = HEADER_LINE_RE.search(readme_text)
    return m.group(0) if m is not None else None


def found_versions(readme_text: str) -> dict[str, str | None]:
    """헤더 줄 안 리터럴 4개의 현재 값. 줄이나 리터럴이 없으면 ``None``.

    Returns:
        ``{label: "1.9.1" | None}`` — 키는 항상 :data:`LITERALS` 전부다.
    """
    line = header_line(readme_text)
    out: dict[str, str | None] = {}
    for lit in LITERALS:
        if line is None:
            out[lit.label] = None
            continue
        m = lit.pattern.search(line)
        out[lit.label] = m.group(1) if m is not None else None
    return out


def mismatches(readme_text: str, version: str) -> list[tuple[str, str | None]]:
    """``version`` 과 다른(또는 부재인) 리터럴 목록 ``[(label, found), ...]``."""
    return [
        (label, found)
        for label, found in found_versions(readme_text).items()
        if found != version
    ]


def sync(readme_text: str, version: str) -> tuple[str, list[tuple[str, str]]]:
    """헤더 줄의 리터럴 4개를 ``version`` 으로 맞춘다.

    헤더 줄 **하나만** 치환 대상이다 — 아래 changelog 의 같은 모양 문자열은
    역사 기록이라 손대지 않는다.

    Returns:
        ``(new_text, [(label, new_literal), ...])`` — 실제로 바뀐 것만 담는다.
        헤더 줄이 없으면 ``(readme_text, [])``.
    """
    line = header_line(readme_text)
    if line is None:
        return readme_text, []

    new_line = line
    changed: list[tuple[str, str]] = []
    for lit in LITERALS:
        replacement = lit.template.format(version=version)
        candidate, n = lit.pattern.subn(replacement, new_line, count=1)
        if n and candidate != new_line:
            changed.append((lit.label, replacement))
            new_line = candidate

    if new_line == line:
        return readme_text, []
    return readme_text.replace(line, new_line, 1), changed
