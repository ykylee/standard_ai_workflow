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
import warnings as _warnings_mod
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
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


# --- 컴파일 시점 경고: 실행 수집으로는 구조적으로 안 보인다 (TASK-2026-09-21-main-008) ---
#
# 위의 `extract` 는 **검사 실행의 출력** 에서 경고를 줍는다. 그 수집 지점에는 두
# 구멍이 있고 2026-09-21 실측이 둘 다 실증했다.
#
# **① 판정이 `__pycache__` 에 달려 있다.** Python 경고 중 `SyntaxWarning` 류는
# *컴파일 시점* 신호다. 모듈의 `.pyc` 가 유효하면 소스는 아예 다시 컴파일되지 않고
# 경고도 나지 않는다. 실측(`dashboard_data.py` 에 invalid escape 주입, 소스 동일):
#
#     1차 실행(cold cache): exit 1  ← 게이트가 잡는다
#     2차 실행(warm cache): exit 0  ← 고친 것이 없는데 green
#
# 즉 **재실행만으로 green 이 되는 게이트** 였다. CI 는 체크아웃이 fresh 라 안 물지만
# 로컬 push 게이트는 바로 문다.
#
# **② runner 부모가 낸 경고는 아무도 안 본다.** `warning_verdict` 는 per-check
# 서브프로세스 출력만 훑는데, runner 부모는 `workflow_kit` 모듈 44/196 을
# transitively import 한다. 그 안의 경고는 배너보다 먼저 stderr 에 찍히면서도
# 게이트는 EXIT=0 이다 (`branch_matrix.py` 주입으로 실측).
#
# `sweep_compile` 은 ①을 원리적으로 없앤다 — `compile()` 은 `__pycache__` 를 **보지
# 않으므로** 캐시 상태와 무관하게 매번 같은 답을 낸다. 덤으로 '누가 무엇을 import
# 했는가' 와도 무관해져 ②의 사각지대까지 덮는다 (부모가 낸 *런타임* 경고는 runner
# 쪽에서 따로 잡는다).


@dataclass(frozen=True)
class SweepResult:
    """컴파일 스윕 1회. 측정과 판정을 나눠 되주입이 가능하게 한다."""

    compiled: int
    """실제로 컴파일에 성공한 소스 수. **긍정 증거** 다 — '실패가 안 보였다' 가
    아니라 'N개를 실제로 컴파일했다' 를 요구한다 (`python_floor` 와 같은 규율)."""

    warnings: list[CheckWarning] = field(default_factory=list)

    errors: list[tuple[str, str]] = field(default_factory=list)
    """게이트 해석기에서 컴파일 자체가 실패한 소스. **삼키지 않는다** — 못 잰 것을
    통과로 세면 거짓 안심이 된다."""


def sweep_compile(sources: Iterable[Path]) -> SweepResult:
    """소스를 **메모리에서** 컴파일해 컴파일 시점 경고를 모은다.

    저장소에 아무것도 쓰지 않는다 — `py_compile` 은 `__pycache__` 를 소스 옆에
    남긴다 (`python_floor` 가 같은 이유로 `compile()` 만 쓴다).
    """
    found: list[CheckWarning] = []
    errors: list[tuple[str, str]] = []
    compiled = 0
    for path in sources:
        try:
            src = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append((str(path), f"read error: {exc}"))
            continue
        with _warnings_mod.catch_warnings(record=True) as captured:
            _warnings_mod.simplefilter("always")
            try:
                compile(src, str(path), "exec")
            except SyntaxError as exc:
                errors.append((str(path), f"{exc.msg} (line {exc.lineno})"))
                continue
        compiled += 1
        for entry in captured:
            found.append(CheckWarning(
                category=entry.category.__name__,
                location=str(entry.filename),
                line=int(entry.lineno or 0),
                message=normalize(str(entry.message)),
            ))
    return SweepResult(compiled=compiled, warnings=found, errors=errors)


def gated_only(warnings: Iterable[CheckWarning], repo_root: str) -> list[CheckWarning]:
    """게이트 대상 출처(저장소 · 귀속 불가)만 남긴다. 서드파티는 보고만 한다."""
    return [w for w in warnings if classify(w, repo_root) in GATED_ORIGINS]
