"""legacy 이관 시 **구분 heading** 처리 계약 (v1.0.3).

## 왜 필요한가

legacy `work_backlog.md` 의 `## 최근 작업 백로그` 안에는 두 종류의 `###` 가 섞여 있다.

    ### [[release/v0.5.1/backlog/2026-06-05.md]] {#release-v0-5-1}   ← entry
    - 2026-06-05: v0.5.1 self-dogfooding bootstrap …

    ### Historical archives {#historical-archives}                    ← 구분 heading
    ### [[codex/phase6/backlog/2026-05-01.md]] {#codex-phase6}        ← entry (아카이브 포인터)
    - 2026-05-01: Phase 6 multi-agent delegation pilot

`migrate_active_to_appendonly.py` 는 두 번째 종류를 몰랐다. 결과가 둘이었다.

1. **직전 entry 의 body 로 흘러들었다.** 실측: `TASK-2026-06-05-001.md` 의 Implementation
   절에 `### Historical archives {#historical-archives}` 가 그대로 박혀 있었다. 이 entry 의
   내용이 아니라 *다음 묶음의 시작*을 알리는 줄이다.
2. **소속이 사라졌다.** 아카이브 포인터와 실제 작업 항목은 형태가 같아서(둘 다
   `### [[path]] {#anchor}` + 한 줄 요약) 구분할 단서가 이 heading 하나뿐인데, 그걸 버리니
   이관 후에는 알 수 없다. 실측: 포인터 2건이 "본문 한 줄짜리 정체불명 task" 로 남아
   완료 여부 판정에 한 세션을 소모했다 (§2.39).

## 계약

1. 구분 heading 은 **직전 entry 를 닫는다** — body 로 흘러들지 않는다.
2. 구분 heading 아래 entry 는 `source_group` 으로 소속을 보존한다.
3. 구분 heading 위 entry 에는 `source_group` 이 없다.
4. 구분 heading 은 entry 를 **삼키지 않는다** — entry 총 개수가 보존된다.
5. 저장소의 실제 task 파일 본문에 유출된 `###` heading 이 없다 (선언과 사실).

Cross-ref: releases/Beta-v1.0.0.md §2.40.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

SOURCE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SOURCE_ROOT.parent
sys.path.insert(0, str(SOURCE_ROOT))

MIGRATE_TOOL = SOURCE_ROOT / "tools" / "migrate_active_to_appendonly.py"

# 실제 legacy 파일의 모양을 그대로 축약한 fixture — 손으로 지어낸 형식이 아니라
# `work_backlog.md.bak` 에서 관찰된 배치다 (entry / 구분 heading / entry).
LEGACY_FIXTURE = """# 작업 백로그 인덱스

## 인덱스 규칙

- 규칙 한 줄.

## 최근 작업 백로그

### [[release/v0.5.1/backlog/2026-06-05.md]] {#release-v0-5-1}
- 2026-06-05: v0.5.1 self-dogfooding bootstrap + MCP 설치 가이드

### Historical archives {#historical-archives}
### [[codex/phase6/backlog/2026-05-01.md]] {#codex-phase6}
- 2026-05-01: Phase 6 multi-agent delegation pilot
### [[gemini/phase10/backlog/2026-04-24.md]] {#gemini-phase10}
- 2026-04-24: Phase 10 MCP/JSON-RPC draft

## 다음에 읽을 문서

- [어딘가](./somewhere.md)
"""

GROUP_NAME = "Historical archives"


def _load_migrate_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migrate_active_to_appendonly", str(MIGRATE_TOOL))
    assert spec is not None and spec.loader is not None, MIGRATE_TOOL
    mod = importlib.util.module_from_spec(spec)
    # `@dataclass` 가 annotation 해석 시 sys.modules 를 본다.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _entries() -> list:
    mod = _load_migrate_tool()
    _, entries, _ = mod.parse_entries(LEGACY_FIXTURE)
    return entries


def _by_anchor(entries: list, anchor: str):
    match = [e for e in entries if e.anchor == anchor]
    assert len(match) == 1, f"anchor={anchor} entry 가 {len(match)}건 — {[e.anchor for e in entries]}"
    return match[0]


# --- 1. body 오염 ---------------------------------------------------------


def test_group_heading_does_not_leak_into_previous_body() -> None:
    """구분 heading 이 직전 entry 의 body 로 흘러들지 않는다."""
    entries = _entries()
    for entry in entries:
        leaked = [line for line in entry.body_lines if line.lstrip().startswith("###")]
        assert not leaked, (
            f"{entry.anchor} 의 body 에 heading 이 흘러들었다: {leaked}\n"
            f"이 줄은 해당 entry 의 내용이 아니라 다음 묶음의 시작이다"
        )


# --- 2/3. 소속 보존 -------------------------------------------------------


def test_entries_under_group_carry_source_group() -> None:
    """구분 heading 아래 entry 는 소속을 들고 온다."""
    entries = _entries()
    for anchor in ("codex-phase6", "gemini-phase10"):
        entry = _by_anchor(entries, anchor)
        assert entry.group == GROUP_NAME, (
            f"{anchor} 의 소속이 사라졌다 (group={entry.group!r}) — 이관 후에는 "
            f"아카이브 포인터인지 작업 항목인지 구분할 단서가 없어진다"
        )


def test_entries_before_group_have_no_source_group() -> None:
    """구분 heading 위 entry 에는 소속이 붙지 않는다 (소급 오염 금지)."""
    entry = _by_anchor(_entries(), "release-v0-5-1")
    assert entry.group == "", f"heading 앞 entry 에 소속이 소급됐다: {entry.group!r}"


def test_source_group_reaches_task_file() -> None:
    """소속이 frontmatter 까지 간다 — 파싱 결과 안에만 있으면 아무도 못 본다."""
    mod = _load_migrate_tool()
    _, entries, _ = mod.parse_entries(LEGACY_FIXTURE)
    grouped = _by_anchor(entries, "codex-phase6")
    plain = _by_anchor(entries, "release-v0-5-1")
    for entry in (grouped, plain):
        mod.classify(entry)
        entry.task_id = "TASK-2026-05-01-001"
    grouped_text = mod.build_task_file(grouped)
    plain_text = mod.build_task_file(plain)
    assert f"source_group: {GROUP_NAME}" in grouped_text, (
        f"소속이 task 파일에 안 남았다:\n{grouped_text[:400]}"
    )
    assert "source_group:" not in plain_text, (
        f"소속 없는 entry 에 source_group 이 붙었다:\n{plain_text[:400]}"
    )


# --- 4. entry 손실 금지 ---------------------------------------------------


def test_group_heading_does_not_swallow_entries() -> None:
    """구분 heading 을 인식하느라 entry 를 잃지 않는다 (fixture 는 3건)."""
    entries = _entries()
    anchors = sorted(e.anchor for e in entries)
    assert anchors == ["codex-phase6", "gemini-phase10", "release-v0-5-1"], anchors


# --- 5. 저장소의 실제 산출물 ---------------------------------------------


def test_repository_task_bodies_have_no_leaked_heading() -> None:
    """실저장소 전수: task 본문에 유출된 `###` heading 이 없다."""
    active = REPO_ROOT / "ai-workflow" / "memory" / "active"
    if not active.exists():
        print("    (skip: ai-workflow/memory/active 없음 — 배포본)")
        return
    offenders: list[str] = []
    checked = 0
    for task_file in active.glob("*/backlog/tasks/TASK-*.md"):
        try:
            text = task_file.read_text(encoding="utf-8")
        except OSError:
            continue
        checked += 1
        body = re.sub(r"^---\n.+?\n---\n", "", text, count=1, flags=re.S)
        for lineno, line in enumerate(body.splitlines(), start=1):
            # `##` 는 정상 절 구분(`## 📝 Description` 등). 유출되는 건 `###` 다.
            if line.startswith("### "):
                offenders.append(f"{task_file.relative_to(REPO_ROOT)} (본문 {lineno}행): {line}")
    assert not offenders, (
        "task 본문에 legacy 구분 heading 이 유출돼 있다:\n  " + "\n  ".join(offenders)
    )
    print(f"    (task 파일 {checked}건 검사)")


def main() -> int:
    test_funcs = [
        test_group_heading_does_not_leak_into_previous_body,
        test_entries_under_group_carry_source_group,
        test_entries_before_group_have_no_source_group,
        test_source_group_reaches_task_file,
        test_group_heading_does_not_swallow_entries,
        test_repository_task_bodies_have_no_leaked_heading,
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
    print(f"\n{total - len(failures)}/{total} PASS")
    if failures:
        for name, err in failures:
            print(f"  - {name}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
