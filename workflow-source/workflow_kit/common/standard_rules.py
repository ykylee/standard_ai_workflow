"""진입점에 주입되는 규칙 문장의 **정본 추출기** (v1.0.2+).

## 왜 필요한가

하네스 진입점 파일(`CLAUDE.md` / `AGENTS.md` / `GEMINI.md` …)은 에이전트가 세션을
열 때 가장 먼저 읽는 문서다. 여기 적힌 규칙이 곧 그 세션의 규칙이다. 그런데 그
문장들이 `bootstrap_lib/harnesses/renderers.py` 의 하네스별 f-string 에 **손으로
복제**돼 있었고, 정본인 `core/global_workflow_standard.md` 를 아무도 읽지 않았다.

결과는 예상대로였다 (2026-07-27 조사):

| 규칙 | 이 문장을 담은 진입점 |
|---|---|
| 검증하지 않은 결과는 완료로 확정하지 않는다 (§1) | 12개 중 6개 |
| 작업 상태값 4종 (§3) | 12개 중 6개 |
| **memory 갱신 → commit → push (§8)** | **12개 중 2개** |

§8 은 표준이 안티패턴까지 명시해 둔 규칙인데, 정작 그 규칙을 지켜야 할 에이전트
대부분이 규칙을 못 받고 있었다. 사본은 갈라진다 — 갈라져도 아무 검사가 실패하지
않으면 아무도 모른다.

## 정본과 생성물

- **정본**: `core/global_workflow_standard.md` §1 · §3 · §8 (마크다운 원문)
- **생성물 1**: 진입점 파일의 `## 작업 원칙` / `## 세션 종료 순서` 블록
- **생성물 2**: :mod:`workflow_kit.common._standard_rules_snapshot` (아래 참조)

## 왜 스냅샷이 필요한가 (그리고 왜 그게 사본이 아닌가)

bootstrap 은 wheel 설치 환경에서도 돈다. 그때는 `core/` 가 함께 배포되지 않아
`SOURCE_ROOT` 가 ``None`` 이고 (``bootstrap_lib.__main__`` 참조), 정본 파일을 읽을
수 없다. 그래서 패키지 안에 스냅샷 모듈을 둔다.

스냅샷은 **손으로 고치는 사본이 아니라 생성물**이다:

- 생성: ``python3 -m workflow_kit.common.standard_rules --apply``
- 검증: ``tests/check_standard_single_source.py`` 가 정본과 스냅샷의 일치를 강제

즉 정본은 언제나 마크다운 하나이고, 파일을 읽을 수 있으면 파일을, 없으면 검사로
동치가 보장된 스냅샷을 쓴다.

## 파싱이 실패하면 조용히 넘어가지 않는다

표준 문서의 구조가 바뀌어 추출이 비면 :class:`StandardParseError` 를 던진다.
기본값으로 조용히 떨어지면 "규칙이 주입된 줄 알았는데 안 됐다" 는 정확히 그
silent failing 을 다시 만드는 것이다.

Cross-ref: `core/global_workflow_standard.md`, `tests/check_standard_single_source.py`.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple, Sequence

__all__ = [
    "STANDARD_RELPATH",
    "StandardParseError",
    "StandardRules",
    "find_standard_path",
    "load_standard_rules",
    "parse_standard",
    "render_entrypoint_rules",
    "DEFAULT_STATE_DOCS",
]

STANDARD_RELPATH = Path("core") / "global_workflow_standard.md"

#: 진입점 블록 맨 위에 찍히는 표식. 검사기가 이 문자열로 생성 블록을 찾는다.
GENERATED_MARKER = (
    "<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 "
    "— 이 블록은 직접 고치지 않는다. 표준 문서를 고치고 다시 생성한다. -->"
)

#: 종료 시 갱신 대상 상태 문서 기본값 (하네스별로 경로 표기가 다를 수 있다).
DEFAULT_STATE_DOCS: tuple[str, ...] = ("state.json", "session_handoff.md", "최신 backlog")

_SECTION_PRINCIPLES = "## 1. 공통 원칙"
_SECTION_STATES = "## 3. 작업 상태값"
_SECTION_CLOSE = "## 8. 세션 종료 원칙 및 절차"


class StandardParseError(RuntimeError):
    """표준 문서에서 규칙을 추출하지 못했다 (구조 변경 또는 파일 손상)."""


class StandardRules(NamedTuple):
    """정본에서 추출한 규칙 묶음."""

    principles: tuple[str, ...]
    """§1 공통 원칙 bullet 원문 (앞의 ``- `` 제거)."""

    task_states: tuple[str, ...]
    """§3 표의 상태값 코드 (`planned` / `in_progress` / …)."""

    close_order: str
    """§8 첫 문단 — 세션 종료 순서 원문."""

    def as_dict(self) -> dict[str, object]:
        return {
            "principles": list(self.principles),
            "task_states": list(self.task_states),
            "close_order": self.close_order,
        }


# ---------------------------------------------------------------------------
# 파싱
# ---------------------------------------------------------------------------


def _section_body(text: str, heading: str) -> str:
    """``heading`` 부터 다음 ``## `` 직전까지의 본문을 돌려준다."""
    start = text.find(heading)
    if start < 0:
        raise StandardParseError(f"섹션을 찾지 못했다: {heading!r}")
    after = start + len(heading)
    nxt = text.find("\n## ", after)
    return text[after:] if nxt < 0 else text[after:nxt]


def parse_standard(text: str) -> StandardRules:
    """표준 문서 원문에서 §1 · §3 · §8 을 추출한다.

    추출 결과가 비면 :class:`StandardParseError` 를 던진다 — 조용한 기본값 없음.
    """
    principles = tuple(
        line[2:].strip()
        for line in _section_body(text, _SECTION_PRINCIPLES).splitlines()
        if line.startswith("- ") and line[2:].strip()
    )
    if not principles:
        raise StandardParseError(f"{_SECTION_PRINCIPLES}: bullet 을 찾지 못했다")

    states = tuple(
        m.group(1)
        for m in re.finditer(r"^\|\s*`([a-z_]+)`\s*\|", _section_body(text, _SECTION_STATES), re.M)
    )
    if not states:
        raise StandardParseError(f"{_SECTION_STATES}: 상태값 표를 찾지 못했다")

    close_body = _section_body(text, _SECTION_CLOSE)
    close_order = ""
    for para in close_body.strip().split("\n\n"):
        stripped = para.strip()
        if stripped and not stripped.startswith(("**", "#", "-", "|")):
            close_order = " ".join(stripped.split())
            break
    if not close_order:
        raise StandardParseError(f"{_SECTION_CLOSE}: 종료 순서 문단을 찾지 못했다")

    return StandardRules(principles=principles, task_states=states, close_order=close_order)


# ---------------------------------------------------------------------------
# 로딩 — 파일 우선, 없으면 스냅샷
# ---------------------------------------------------------------------------


def find_standard_path(start: Path | None = None) -> Path | None:
    """``core/global_workflow_standard.md`` 를 위로 거슬러 찾는다.

    ``bootstrap_lib.__main__`` 의 SOURCE_ROOT 탐색과 같은 규약을 쓴다 — 규약이
    갈라지지 않도록 판정 기준(``core/global_workflow_standard.md`` 존재)을 맞춘다.
    """
    base = (start or Path(__file__)).resolve()
    for candidate in (base, *base.parents):
        if (candidate / STANDARD_RELPATH).exists():
            return candidate / STANDARD_RELPATH
    return None


def load_standard_rules(source_root: Path | None = None) -> StandardRules:
    """정본 파일이 있으면 파일에서, 없으면 스냅샷에서 규칙을 읽는다.

    스냅샷은 검사(`check_standard_single_source.py`)로 정본과의 동치가 강제된다.
    """
    if source_root is not None:
        path: Path | None = source_root / STANDARD_RELPATH
        if path is not None and not path.exists():
            path = None
    else:
        path = find_standard_path()

    if path is not None:
        return parse_standard(path.read_text(encoding="utf-8"))

    from workflow_kit.common import _standard_rules_snapshot as snapshot

    return StandardRules(
        principles=snapshot.PRINCIPLES,
        task_states=snapshot.TASK_STATES,
        close_order=snapshot.CLOSE_ORDER,
    )


# ---------------------------------------------------------------------------
# 진입점 블록 렌더링
# ---------------------------------------------------------------------------


def render_entrypoint_rules(
    rules: StandardRules | None = None,
    *,
    state_docs: Sequence[str] = DEFAULT_STATE_DOCS,
    source_root: Path | None = None,
) -> str:
    """하네스 진입점에 넣을 `## 작업 원칙` + `## 세션 종료 순서` 블록.

    반환 문자열은 앞뒤에 빈 줄을 두지 않는다 (f-string 안에서 붙여 쓰기 쉽도록).
    """
    resolved = rules if rules is not None else load_standard_rules(source_root)
    bullets = "\n".join(f"- {p}" for p in resolved.principles)
    targets = ", ".join(f"`{d}`" if not d.startswith("최신") else d for d in state_docs)
    return (
        "## 작업 원칙\n"
        f"\n{GENERATED_MARKER}\n"
        f"\n{bullets}\n"
        "\n## 세션 종료 순서\n"
        f"\n{resolved.close_order}\n"
        f"\n- 종료 전 갱신 대상: {targets}"
    )


# ---------------------------------------------------------------------------
# 스냅샷 생성 CLI
# ---------------------------------------------------------------------------

_SNAPSHOT_PATH = Path(__file__).resolve().parent / "_standard_rules_snapshot.py"

_SNAPSHOT_HEADER = '''"""정본 규칙의 **생성된 스냅샷** — 직접 고치지 않는다.

생성: ``python3 -m workflow_kit.common.standard_rules --apply``
정본: ``core/global_workflow_standard.md`` §1 · §3 · §8
검증: ``tests/check_standard_single_source.py``

wheel 설치처럼 ``core/`` 가 함께 배포되지 않는 환경에서 진입점 렌더링이 규칙을
잃지 않도록 두는 사본이다. 정본과의 일치는 검사로 강제된다.
"""

from __future__ import annotations

'''


def render_snapshot_module(rules: StandardRules) -> str:
    """스냅샷 모듈 소스를 만든다."""
    lines = [_SNAPSHOT_HEADER, "PRINCIPLES: tuple[str, ...] = ("]
    lines.extend(f"    {p!r}," for p in rules.principles)
    lines.append(")")
    lines.append("")
    lines.append("TASK_STATES: tuple[str, ...] = (")
    lines.extend(f"    {s!r}," for s in rules.task_states)
    lines.append(")")
    lines.append("")
    lines.append(f"CLOSE_ORDER: str = {rules.close_order!r}")
    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="스냅샷 모듈을 정본 기준으로 다시 생성한다")
    parser.add_argument("--standard-path", type=Path, default=None, help="정본 경로 (기본: 자동 탐색)")
    args = parser.parse_args(argv)

    path = args.standard_path or find_standard_path()
    if path is None:
        print("FAIL: 정본 core/global_workflow_standard.md 를 찾지 못했다", file=sys.stderr)
        return 2
    rules = parse_standard(Path(path).read_text(encoding="utf-8"))
    generated = render_snapshot_module(rules)
    current = _SNAPSHOT_PATH.read_text(encoding="utf-8") if _SNAPSHOT_PATH.exists() else None

    if generated == current:
        print(f"OK: 스냅샷이 정본과 일치한다 ({path})")
        return 0
    if not args.apply:
        print(f"DRIFT: 스냅샷이 정본과 다르다. `--apply` 로 재생성한다 ({path})", file=sys.stderr)
        return 1
    _SNAPSHOT_PATH.write_text(generated, encoding="utf-8")
    print(f"WROTE: {_SNAPSHOT_PATH}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
