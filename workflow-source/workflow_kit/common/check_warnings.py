"""검사 실행이 내는 **Python 경고**를 수집한다 (TASK-2026-09-21-main-007).

## 왜 이 파일이 있는가

82차(main-006)가 해석기 축을 세웠지만 **그 축이 보는 것은 종료 코드뿐**이다.
3.12+ 에서만 나는 `SyntaxWarning: invalid escape sequence` 는 exit 0 이라 CI 4셀이
전부 green 이었고, 그 결함은 사람이 두 실행의 출력을 눈으로 대조해서 찾았다 —
다음에는 못 찾는다.

## 수집 지점은 새로 만들 것이 없었다

`run_all_checks.run_one` 은 이미 `stdout + stderr` 를 **전량** 받아 두고
(`output = out + err`) `passed/failed/last_line/error_excerpt` 로 요약한 뒤 버린다.
경고는 그 `output` 안에 이미 있다. 이 모듈이 하는 일은 배선이 아니라 **버리지
않기** 다.

## 형식

CPython 의 기본 `showwarning` 은 이렇게 쓴다::

    <파일 또는 '<unknown>'>:<줄>: <범주>Warning: <메시지>
      <소스 줄 에코>          ← 있을 수도 없을 수도

검사들이 사람용으로 찍는 `WARN: ...` 산문과 섞이면 안 되므로, **위치와 줄 번호가
붙은 형태만** 경고로 센다. 그래야 `WARN: OpenPhish fetch attempt 3 failed` 같은
의도된 출력이 잡음으로 들어오지 않는다.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

_T = TypeVar("_T")

#: CPython 기본 경고 포맷. `<unknown>:93: SyntaxWarning: ...` 도 같은 모양이다.
#: 위치·줄 번호를 **요구**하는 것이 요점 — 검사가 찍는 `WARN:` 산문을 배제한다.
_WARNING_RE = re.compile(
    r"^(?P<location>\S.*?):(?P<line>\d+): (?P<category>[A-Za-z_][A-Za-z0-9_]*Warning): (?P<message>.*)$",
    re.MULTILINE,
)

#: 실행마다 달라지는 조각을 치환한다. 정규화하지 않으면 같은 경고가 실행마다
#: 다른 문자열이 되어 **비교가 성립하지 않는다** — 82차에 두 해석기 출력을
#: 대조했을 때 갈린 8건 중 3건이 정확히 이 부류였다 (tmp 디렉터리 경로 2건).
_VOLATILE_SUBS: tuple[tuple[re.Pattern[str], str], ...] = (
    # per-check 전용 TMPDIR: `<tmp_root>/<check_stem>-<랜덤8>/...`
    (re.compile(r"/tmp[^\s:]*|/var/tmp[^\s:]*"), "<TMP>"),
    (re.compile(r"\b0x[0-9a-fA-F]+\b"), "<ADDR>"),
)


@dataclass(frozen=True)
class CheckWarning:
    """검사 실행이 낸 Python 경고 하나 (정규화된 형태)."""

    category: str
    """`SyntaxWarning` · `DeprecationWarning` 등 범주 이름."""

    location: str
    """경고가 난 위치. 저장소 밖(site-packages)이면 서드파티다."""

    line: int

    message: str

    @property
    def key(self) -> str:
        """두 실행을 대조할 때 쓰는 동일성 키."""
        return f"{self.category}|{self.location}:{self.line}|{self.message}"

    def render(self) -> str:
        return f"{self.location}:{self.line}: {self.category}: {self.message}"


def normalize(text: str) -> str:
    """실행마다 달라지는 조각을 치환한다 (tmp 경로 · 객체 주소)."""
    for pattern, replacement in _VOLATILE_SUBS:
        text = pattern.sub(replacement, text)
    return text


def extract(output: str) -> list[CheckWarning]:
    """검사 출력에서 Python 경고를 뽑는다. 순서는 등장 순, 중복은 유지한다."""
    found: list[CheckWarning] = []
    for match in _WARNING_RE.finditer(normalize(output)):
        found.append(CheckWarning(
            category=match.group("category"),
            location=match.group("location"),
            line=int(match.group("line")),
            message=match.group("message").strip(),
        ))
    return found


def render_all(warnings: list[CheckWarning]) -> list[str]:
    """보고용 문자열 목록 (중복은 접어서 `×N` 로)."""
    counts: dict[str, int] = {}
    order: list[str] = []
    for entry in warnings:
        text = entry.render()
        if text not in counts:
            order.append(text)
        counts[text] = counts.get(text, 0) + 1
    return [f"{text} ×{counts[text]}" if counts[text] > 1 else text for text in order]


#: 경고 위치가 **서드파티**임을 나타내는 경로 조각. 저장소 안에 있어도 이 조각이
#: 들어 있으면 우리 코드가 아니다 (`.venv-interpreter-matrix/3.11/lib/.../site-packages/`
#: 가 실제로 저장소 루트 아래에 있다 — 루트 포함 여부만으로는 못 가른다).
_THIRD_PARTY_PARTS = ("site-packages", "dist-packages", "__pypackages__")

#: 위치를 특정할 수 없는 경고. 문자열을 `compile()`/`ast.parse()` 한 결과라 파일
#: 이름이 없다. **이것을 서드파티로 분류하면 이 축을 만든 결함이 그대로 빠져나간다** —
#: 2026-09-21 의 `SyntaxWarning: invalid escape sequence` 가 정확히 `<unknown>:93`
#: 이었다. 우리 코드가 우리 소스를 파싱하다 낸 것이므로 **우리 것으로 센다**.
UNATTRIBUTED = "<unknown>"

ORIGIN_REPO = "repo"
ORIGIN_THIRD_PARTY = "third-party"
ORIGIN_UNATTRIBUTED = "unattributed"


def classify(warning: CheckWarning, repo_root: str) -> str:
    """경고의 출처를 가른다 — 게이트 대상인지는 이 축이 정한다."""
    if warning.location == UNATTRIBUTED:
        return ORIGIN_UNATTRIBUTED
    if any(part in warning.location for part in _THIRD_PARTY_PARTS):
        return ORIGIN_THIRD_PARTY
    if "/.venv" in warning.location or warning.location.startswith(".venv"):
        return ORIGIN_THIRD_PARTY
    root = repo_root.rstrip("/")
    if warning.location.startswith(root + "/") or not warning.location.startswith("/"):
        return ORIGIN_REPO
    return ORIGIN_THIRD_PARTY


#: 게이트가 red 로 올리는 출처. 서드파티는 **보고만** 한다 — 우리가 못 고치는 것을
#: red 로 만들면 만성 red 가 되고, 만성 red 는 fixture 가 된다 (2026-08-10 실측).
#: 전수 census(2026-09-21, 288검사 × 2해석기)가 이 경계를 정했다: 갈린 2건은 전부
#: 서드파티였고 그 원인도 해석기가 아니라 **두 venv 의 의존성 해석 차이**였다.
GATED_ORIGINS = (ORIGIN_REPO, ORIGIN_UNATTRIBUTED)


def call_deprecated(
    fn: Callable[..., _T], /, *args: object, **kwargs: object,
) -> _T:
    """deprecation 경로를 **의도적으로** 부른다 (유예 기간 중 옛 동작 검증용).

    그냥 부르면 `DeprecationWarning` 이 게이트에 red 로 잡힌다. 그렇다고 조용히
    삼키면 '의도한 것' 과 '모르고 낸 것' 이 같은 모양이 된다. 그래서 삼키되
    **경고가 실제로 났는지 단언한다** — deprecation 이 사라지면 이쪽이 red 가 되어
    계약이 늘어난다 (`check_v0_9_1_deprecation_contract` 가 이미 쓰는 패턴).
    """
    import warnings as _warnings

    with _warnings.catch_warnings(record=True) as captured:
        _warnings.simplefilter("always")
        result = fn(*args, **kwargs)
    assert any(issubclass(entry.category, DeprecationWarning) for entry in captured), (
        f"{getattr(fn, '__name__', fn)} 이 DeprecationWarning 을 내지 않았다 — "
        "deprecation 계약이 깨졌거나, 이 호출은 애초에 옛 경로가 아니다"
    )
    return result
