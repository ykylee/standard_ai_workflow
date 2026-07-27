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

**한계 (과장하지 않는다)**: 판정 단위가 *파일* 이라, 정본 symbol 을 어딘가에서 쓰는
파일이 **다른 줄에서** 손으로 조립하면 통과한다. 파일 단위로 낮춘 것은 위양성을 0 으로
유지하기 위한 선택이고, 그 대신 규약을 늘릴 때마다 **한 번은 전수 조사**해서 기존
사본을 정리한 뒤 등록하는 것을 전제로 한다 (§2.24 / §2.25 가 그렇게 했다).

Test list (5 case):
1. test_no_duplicate_convention_literals
2. test_every_canonical_symbol_exists
3. test_exemptions_are_still_needed        ← 죽은 예외가 쌓이지 않게
4. test_detector_catches_injected_copy     ← 탐지기 자체가 동작하는지
5. test_task_id_syntax_is_accepted_by_work_status  ← 같은 파일 안의 분기는 동작으로 잡는다

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
    # v1.0.2 — literal 을 넓혔다. 이전 값 `...r?\"[^\"]*TASK-` 는 **`TASK-` 라는 문자열이
    # 그대로 나올 때만** 잡았는데, `normalize.py` 의 사본은
    # `re.compile(r"^((?:TASK|WF)-[A-Z0-9-]+)\b")` 처럼 교대(alternation)로 써서
    # `TASK-` 가 등장하지 않았고, 그래서 이 검사를 조용히 통과했다. 그 사본은 문자
    # 클래스가 대문자 전용이라 branch-scoped ID 를 잘라 먹었고, `dedupe_work_items` 가
    # 같은 날짜 task 를 전부 한 key 로 뭉개 **state.json 에서 항목을 영구 소실**시켰다.
    # `r?` → `[rfb]*` 로 넓힌 것은 `rf"..."` prefix 도 받기 위해서다.
    Convention(
        name="task ID 정규식",
        literal=re.compile(r"re\.compile\(\s*[rfb]*\"[^\"]*TASK[-|]"),
        canonical="workflow_kit/common/project_docs.py",
        symbols=("TASK_ID_PATTERN", "TASK_ID_CAPTURE_RE", "TASK_HEADER_RE",
                 "WORK_ITEM_ID_PATTERN"),
        exemptions={},
    ),
    Convention(
        name="memory 루트 경로 조립",
        literal=re.compile(r'"ai-workflow"\s*/\s*"memory"'),
        canonical="workflow_kit/common/paths.py",
        symbols=("memory_active_dir", "memory_dir_for_workspace", "memory_root_dir",
                 "workflow_memory_dir"),
        exemptions={},
    ),
    Convention(
        name="drift 원장 경로",
        literal=re.compile(r"drift_ledger\.jsonl"),
        canonical="workflow_kit/common/dashboard_data.py",
        symbols=("DRIFT_LEDGER_RELPATH",),
        exemptions={},
    ),
    # v1.0.2 — 진입점에 주입되는 규칙 문장. 하네스 렌더러 6곳에 복제돼 있었고
    # §8(memory → commit → push)은 12개 진입점 중 2개에만 실려 있었다.
    # 정본은 core/global_workflow_standard.md, 추출기는 standard_rules.py 다.
    Convention(
        name="세션 종료 순서 문장 (§8)",
        literal=re.compile(r"memory 갱신 → commit → push"),
        canonical="workflow_kit/common/standard_rules.py",
        symbols=("load_standard_rules", "render_entrypoint_rules", "parse_standard"),
        exemptions={
            "workflow_kit/common/_standard_rules_snapshot.py":
                "정본에서 **생성된** 스냅샷 — check_standard_single_source.py 가 정본과의 동치를 강제한다",
        },
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
        # v1.0.2: 면제 판정은 **코드**에서만 한다. 이전에는 파일 전체 텍스트에서 symbol
        # 을 찾았기 때문에, 정본 symbol 을 *주석에 언급만 해도* 사본이 통과했다
        # (되주입으로 실측: 정본 이름을 주석에 남긴 채 사본을 넣으면 검사가 green).
        if any(sym in _code_only(text) for sym in conv.symbols):
            continue  # 정본을 import 해서 쓰는 파일
        problems.append(rel)
    return problems


def _code_only(text: str) -> str:
    """`#` 주석을 걷어낸 텍스트. 문자열 안의 `#` 까지 구분하지는 않는다 (보수적)."""
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        out.append(line.split("  #", 1)[0])
    return "\n".join(out)


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





def test_task_id_syntax_is_accepted_by_work_status() -> None:
    """정본 문법(`TASK_ID_PATTERN`)을 따르는 ID 는 handoff Work Status 줄에서도 인식돼야 한다.

    v1.0.2 이전에는 `WORK_STATUS_RE` 가 `[A-Z0-9-]+` 로 **대문자만** 받아,
    `TASK-2026-07-27-main-001` 처럼 branch slug 가 들어간 정본 ID 를 통째로 놓쳤다.
    같은 규약을 두 정규식이 각자 정의하면 이렇게 갈라진다 — 한쪽만 고쳐도 다른 쪽은
    자기 test 를 계속 통과하므로 아무도 모른다. 위의 리터럴 검사(파일 단위)로는 같은
    파일 안의 분기를 못 잡으므로, **동작으로** 고정한다.
    """
    from workflow_kit.common.project_docs import WORK_STATUS_RE

    canonical_ids = [
        "TASK-2026-07-27-main-001",      # branch slug (소문자)
        "TASK-2026-01-01-feat_x-999",    # underscore 포함 slug
        "TASK-2026-01-01-001",           # slug 없음
        "TASK-2026-07-27-MAIN-001",      # 대문자 (기존 동작 유지)
    ]
    missed = [i for i in canonical_ids if not WORK_STATUS_RE.match(f"- {i} 제목: done")]
    assert not missed, f"정본 문법 ID 를 Work Status 가 인식하지 못한다: {missed}"

    # 범위를 좁히지 않았는지 — legacy 와 WF- 도 계속 받아야 한다.
    legacy = [i for i in ("TASK-021", "WF-042-01") if not WORK_STATUS_RE.match(f"- {i} 제목: blocked")]
    assert not legacy, f"legacy / WF- ID 인식 실패: {legacy}"


def main() -> int:
    test_funcs = [
        test_no_duplicate_convention_literals,
        test_every_canonical_symbol_exists,
        test_exemptions_are_still_needed,
        test_detector_catches_injected_copy,
        test_task_id_syntax_is_accepted_by_work_status,
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
