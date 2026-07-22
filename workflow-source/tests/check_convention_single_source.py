"""규약이 **정본 한 곳에서만** 정의되는가 (v1.0.1+).

## 왜 필요한가

같은 규약을 두 곳에 적으면 둘은 반드시 갈라지고, 갈라져도 아무 테스트가 실패하지 않으면
아무도 모른다. 한 사이클에 세 번 나왔다 (노트 §2.19~§2.21):

- `state.json` 경로 — writer 는 legacy 문자열 조립, reader 는 정본 helper. **네 개의
  skill 과 두 개의 tool 이 같은 legacy 조립을 하고 있었다** (본 check 도입 시 발견).
- task ID 문법 — 정규식이 4곳에 복제, branch-scoped ID 를 셋이 인식 못 함.
- 원장 경로 — writer(fallback) 와 reader 가 각자 문자열.

## 판정 규칙

각 규약마다 **정본 모듈**과 **정본 symbol** 이 있다. production 코드에서 그 규약의
리터럴을 쓰는 파일은 둘 중 하나여야 한다:

1. 정본 모듈 자신이거나,
2. 정본 symbol 을 **import** 하고 있거나.

둘 다 아니면 사본이다. 예외는 **이유와 함께** registry 에 명시한다 — 조용히 빠져나가는
경로를 만들지 않는다.

> **범위를 좁게 잡는 것이 핵심.** 일반적인 "중복 코드 탐지"로 만들면 위양성이 쏟아지고,
> 위양성을 내는 check 는 무시당해 결국 아무것도 막지 못한다. 그래서 *등록된 규약* 만
> 본다. `tests/` 는 제외한다 — 임시 fixture 경로 조립은 정당한 사용이다.

Test list (4 case):
1. test_no_duplicate_convention_literals
2. test_every_canonical_symbol_exists
3. test_exemptions_are_still_needed        ← 죽은 예외가 쌓이지 않게
4. test_detector_catches_injected_copy     ← 탐지기 자체가 동작하는지

Cross-ref: releases/Beta-v1.0.0.md §2.24.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

# production 코드만 본다 (tests/ 는 fixture 조립이 정당하므로 제외).
SCAN_DIRS = ("workflow_kit", "skills", "tools", "scripts")
SKIP_PARTS = ("build", "dist", "__pycache__", "egg-info", ".venv")


class Convention(NamedTuple):
    name: str
    literal: re.Pattern[str]        # 사본이면 반드시 나타나는 리터럴
    canonical: str                  # 정본 모듈 (SOURCE_ROOT 기준 상대 경로)
    symbols: tuple[str, ...]        # 이 중 하나라도 import 하면 정본 사용자
    exemptions: dict[str, str]      # path → 이유


CONVENTIONS: tuple[Convention, ...] = (
    Convention(
        name="state.json 경로 조립",
        literal=re.compile(r'/\s*"state\.json"'),
        canonical="workflow_kit/common/paths.py",
        symbols=("workflow_state_path", "state_path_for_workspace"),
        exemptions={
            "workflow_kit/common/ingest.py":
                "freeze/ingest 는 legacy 규약을 의도적으로 유지 (본문 주석에 근거 명시)",
            "workflow_kit/common/contracts/baselines.py":
                "temp 벤치 **사본** 파일명이라 실제 메모리 경로가 아니다",
            "scripts/bootstrap_lib/paths.py":
                "신규 프로젝트 템플릿 경로 emit — workflow_kit 에 의존하지 않는 부트스트랩 계층",
            "tools/migrate_memory_to_branch_scoped.py":
                "마이그레이션 도구 — legacy → branch-scoped 이동이 목적이라 양쪽 경로를 직접 다룬다",
            "tools/archive_branch_memory.py":
                "아카이브 대상 판별용 존재 확인 (경로 해석이 아니라 디렉터리 판정)",
        },
    ),
    Convention(
        name="task ID 정규식",
        literal=re.compile(r"re\.compile\(\s*r?\"[^\"]*TASK-"),
        canonical="workflow_kit/common/project_docs.py",
        symbols=("TASK_ID_PATTERN", "TASK_ID_CAPTURE_RE", "TASK_HEADER_RE"),
        exemptions={},
    ),
    Convention(
        name="drift 원장 경로",
        literal=re.compile(r"drift_ledger\.jsonl"),
        canonical="workflow_kit/common/dashboard_data.py",
        symbols=("DRIFT_LEDGER_RELPATH",),
        exemptions={},
    ),
)


def _production_files() -> list[Path]:
    out: list[Path] = []
    for d in SCAN_DIRS:
        base = SOURCE_ROOT / d
        if not base.is_dir():
            continue
        for p in base.rglob("*.py"):
            if any(part in SKIP_PARTS or part.endswith(".egg-info") for part in p.parts):
                continue
            out.append(p)
    return sorted(out)


def _violations(conv: Convention, *, files: list[Path] | None = None) -> list[str]:
    problems: list[str] = []
    for path in files if files is not None else _production_files():
        rel = str(path.relative_to(SOURCE_ROOT))
        if rel == conv.canonical or rel in conv.exemptions:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not conv.literal.search(text):
            continue
        if any(sym in text for sym in conv.symbols):
            continue  # 정본을 import 해서 쓰는 파일
        problems.append(rel)
    return problems


# --- Tests ---


def test_no_duplicate_convention_literals() -> None:
    """등록된 규약의 사본이 production 코드에 없다."""
    report: list[str] = []
    for conv in CONVENTIONS:
        bad = _violations(conv)
        if bad:
            report.append(
                f"[{conv.name}] 정본 `{conv.canonical}` 의 사본:\n    " + "\n    ".join(bad)
                + f"\n    → {conv.symbols[0]} 를 import 해 쓰거나, 이유를 달아 exemptions 에 등록할 것"
            )
    assert not report, "\n  ".join(report)


def test_every_canonical_symbol_exists() -> None:
    """정본 모듈에 등록된 symbol 이 실제로 있다 (registry 가 stale 하지 않은지)."""
    problems: list[str] = []
    for conv in CONVENTIONS:
        canonical = SOURCE_ROOT / conv.canonical
        if not canonical.is_file():
            problems.append(f"[{conv.name}] 정본 모듈 부재: {conv.canonical}")
            continue
        text = canonical.read_text(encoding="utf-8")
        for sym in conv.symbols:
            if not re.search(rf"^(?:def\s+)?{re.escape(sym)}\s*[:=\(]", text, re.M):
                problems.append(f"[{conv.name}] 정본에 `{sym}` 정의 없음")
    assert not problems, "\n  ".join(problems)


def test_exemptions_are_still_needed() -> None:
    """죽은 예외가 쌓이지 않게 — 예외로 등록됐는데 실제로는 리터럴이 없으면 지운다."""
    problems: list[str] = []
    for conv in CONVENTIONS:
        for rel in conv.exemptions:
            path = SOURCE_ROOT / rel
            if not path.is_file():
                problems.append(f"[{conv.name}] 예외 대상 파일이 없다: {rel}")
                continue
            if not conv.literal.search(path.read_text(encoding="utf-8")):
                problems.append(f"[{conv.name}] `{rel}` 은 더 이상 리터럴을 쓰지 않는다 — 예외 삭제")
    assert not problems, "\n  ".join(problems)


def test_detector_catches_injected_copy() -> None:
    """탐지기 자체가 동작하는지 — 사본을 흉내 낸 임시 파일을 만들어 잡히는지 본다.

    (실제 파일을 만들지 않고, 검사 대상 목록만 갈아끼워 순수하게 검증한다.)
    """
    import tempfile

    conv = CONVENTIONS[0]
    with tempfile.TemporaryDirectory() as td:
        fake = Path(td) / "fake_module.py"
        fake.write_text('p = memory_dir / "state.json"\n', encoding="utf-8")
        # relative_to 를 위해 SOURCE_ROOT 하위처럼 다루는 대신, 직접 로직을 재현한다.
        text = fake.read_text(encoding="utf-8")
        assert conv.literal.search(text), "리터럴 탐지가 동작하지 않는다"
        assert not any(sym in text for sym in conv.symbols), "정본 import 판정이 잘못됐다"

        ok = Path(td) / "ok_module.py"
        ok.write_text(
            "from workflow_kit.common.paths import workflow_state_path\n"
            'p = base / "state.json"\n',
            encoding="utf-8",
        )
        ok_text = ok.read_text(encoding="utf-8")
        assert conv.literal.search(ok_text)
        assert any(sym in ok_text for sym in conv.symbols), "정본 사용자를 사본으로 오판한다"


def main() -> int:
    test_funcs = [
        test_no_duplicate_convention_literals,
        test_every_canonical_symbol_exists,
        test_exemptions_are_still_needed,
        test_detector_catches_injected_copy,
    ]
    failures: list[tuple[str, str]] = []
    for func in test_funcs:
        try:
            func()
            print(f"  PASS: {func.__name__}")
        except AssertionError as e:
            failures.append((func.__name__, f"AssertionError: {e}"))
            print(f"  FAIL: {func.__name__} — {e}")
        except Exception as e:  # noqa: BLE001
            failures.append((func.__name__, f"{type(e).__name__}: {e}"))
            print(f"  FAIL: {func.__name__} — {type(e).__name__}: {e}")

    total = len(test_funcs)
    passed = total - len(failures)
    print(f"\n{passed}/{total} PASS")
    if failures:
        for name, err in failures:
            print(f"  - {name}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
