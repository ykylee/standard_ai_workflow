#!/usr/bin/env python3
"""`wk migrate-task-labels` 의 계약 (TASK-2026-08-24-main-004).

## 왜 도구이고, 왜 이 검사인가

`TASK_FIELD_LABELS` 가 2026-08-20 에 영어로 뒤집힌 뒤에도 코퍼스는 섞인 채
남았다. 읽는 쪽은 별칭이 덮으므로 **동작은 옳았지만**, 혼재는 정적이 아니다 —
`backlog-update --mode update` 는 **건드린 필드만** 정본 표기로 다시 쓰므로
옛 파일을 갱신할 때마다 한 파일 안에 두 표기가 생긴다.

손으로 고치면 파싱 계약이 조용히 깨진다(정본 §11). 그리고 같은 kit 을 쓰는
**소비자 저장소도 같은 레거시 코퍼스**를 가지므로, 일회성 스크립트로 처리하면
그들에게는 아무것도 남지 않는다.

## 재는 것

1. **매핑은 레지스트리 파생** — 손 목록을 만들면 어휘가 늘 때 갈라진다.
2. **줄머리 앵커** — 앵커 없이 치환하면 라벨을 *언급하는* 산문까지 바뀐다.
3. **멱등** — 두 번 돌려도 두 번째는 0건이다.
4. **파싱 동일성 잠금장치** — 바꾼 뒤 파서가 다르게 읽으면 **아무것도 쓰지 않고**
   되돌린다. 라벨은 사람이 읽는 면이고 상태의 근거는 frontmatter 이므로, 이
   마이그레이션은 정의상 집계를 바꾸면 안 된다. 바뀐다면 사고다.
5. **dry-run 이 기본** — `--apply` 없이는 디스크를 건드리지 않는다.
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "ai-workflow/memory/active/*",
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.project_docs import (  # noqa: E402
    TASK_FIELD_ALIASES,
    TASK_FIELD_LABELS,
)
from workflow_kit.tools.migrate_task_labels import (  # noqa: E402
    legacy_label_map,
    migrate_text,
    run,
)

FAILURES: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case}{(' — ' + detail) if detail else ''}")
        FAILURES.append(case)


def _fixture(root: Path, *, status: str = "in_progress") -> Path:
    active = root / "active"
    tasks = active / "main" / "backlog" / "tasks"
    tasks.mkdir(parents=True)
    (active / "main" / "sessions").mkdir(parents=True)
    (active / "main" / "backlog" / "2026-01-01.md").write_text(
        "# Backlog Index — 2026-01-01\n\n## Tasks\n\n"
        "- **TASK-2026-01-01-main-001** [generic] probe\n"
        "  - path: [`./tasks/TASK-2026-01-01-main-001.md`](./tasks/TASK-2026-01-01-main-001.md)\n"
        f"  - status: {status}\n",
        encoding="utf-8",
    )
    (tasks / "TASK-2026-01-01-main-001.md").write_text(
        "---\nid: TASK-2026-01-01-main-001\n"
        f"status: {status}\ncreated_at: 2026-01-01\nkind: generic\n---\n\n"
        "# TASK-2026-01-01-main-001 — probe\n\n"
        f"- 상태: {status}\n- 우선순위: high\n- 작업 내용: 라벨이 `- 상태:` 인 파일\n",
        encoding="utf-8",
    )
    return active


def test_mapping_is_derived_from_registry() -> None:
    mapping = legacy_label_map()
    expected = {
        alias: TASK_FIELD_LABELS[key]
        for key, aliases in TASK_FIELD_ALIASES.items()
        for alias in aliases
        if alias != TASK_FIELD_LABELS[key]
    }
    _record(
        "test_mapping_is_derived_from_registry",
        mapping == expected,
        f"레지스트리 파생이 아니다: {set(mapping) ^ set(expected)}",
    )


def test_replacement_is_line_anchored() -> None:
    """산문 안의 라벨 언급은 건드리지 않는다."""
    text = (
        "- 상태: in_progress\n"
        "본문에서 `- 상태:` 를 설명하는 문장이다.\n"
        "  - 상태: 들여쓰기된 줄\n"
    )
    migrated, hits = migrate_text(text, legacy_label_map())
    problems: list[str] = []
    if "- Status: in_progress" not in migrated:
        problems.append("줄머리 라벨이 안 바뀌었다")
    if "`- 상태:` 를 설명하는" not in migrated:
        problems.append("산문 안의 언급까지 바꿨다")
    if "  - 상태: 들여쓰기된 줄" not in migrated:
        problems.append("들여쓰기된 줄까지 바꿨다 — 필드 줄이 아니다")
    if hits != 1:
        problems.append(f"바꾼 줄 수가 1이 아니다: {hits}")
    _record("test_replacement_is_line_anchored", not problems, "; ".join(problems))


def test_dry_run_writes_nothing() -> None:
    with tempfile.TemporaryDirectory() as td:
        active = _fixture(Path(td))
        target = active / "main" / "backlog" / "tasks" / "TASK-2026-01-01-main-001.md"
        before = target.read_text(encoding="utf-8")
        result = run(active_dir=active, apply=False)
        after = target.read_text(encoding="utf-8")
    problems: list[str] = []
    if after != before:
        problems.append("dry-run 이 파일을 건드렸다")
    if result["files_to_change"] != 1:
        problems.append(f"바꿀 파일을 못 셌다: {result['files_to_change']}")
    _record("test_dry_run_writes_nothing", not problems, "; ".join(problems))


def test_apply_is_idempotent() -> None:
    with tempfile.TemporaryDirectory() as td:
        active = _fixture(Path(td))
        first = run(active_dir=active, apply=True)
        second = run(active_dir=active, apply=True)
        target = active / "main" / "backlog" / "tasks" / "TASK-2026-01-01-main-001.md"
        text = target.read_text(encoding="utf-8")
    problems: list[str] = []
    if first["lines_to_change"] == 0:
        problems.append("첫 적용이 아무것도 안 바꿨다")
    if second["lines_to_change"] != 0:
        problems.append(f"두 번째 적용이 또 바꿨다 — 멱등이 아니다: {second['lines_to_change']}")
    # **줄머리 기준으로** 본다. 산문 안의 `- 상태:` 언급은 남는 것이 옳고,
    # 처음엔 이 단언이 그것까지 잡아 스스로 red 였다 — 검사가 도구의 계약을
    # 잘못 적으면, 옳은 동작이 결함으로 보고된다.
    if re.search(r"^- 상태:", text, re.M):
        problems.append("줄머리의 옛 표기가 남았다")
    if "`- 상태:`" not in text:
        problems.append("산문 안의 라벨 언급까지 바꿨다")
    if "- Status: in_progress" not in text:
        problems.append("정본 표기가 안 들어갔다")
    _record("test_apply_is_idempotent", not problems, "; ".join(problems))


def test_parse_identity_interlock_blocks_and_rolls_back() -> None:
    """파서 출력이 달라지면 **아무것도 쓰지 않는다**.

    치환 자체는 집계를 바꿀 수 없으므로, 잠금장치가 실제로 도는지 보려면
    바뀌게 만들어야 한다. `migrate_text` 를 frontmatter 까지 건드리는 것으로
    갈아끼워 되주입한다.
    """
    import workflow_kit.tools.migrate_task_labels as tool

    original_fn = tool.migrate_text

    def sabotage(text: str, mapping: dict[str, str]) -> tuple[str, int]:
        migrated, hits = original_fn(text, mapping)
        if hits:
            migrated = migrated.replace("status: in_progress", "status: done", 1)
        return migrated, hits

    with tempfile.TemporaryDirectory() as td:
        active = _fixture(Path(td))
        target = active / "main" / "backlog" / "tasks" / "TASK-2026-01-01-main-001.md"
        before = target.read_text(encoding="utf-8")
        tool.migrate_text = sabotage
        try:
            result = run(active_dir=active, apply=True)
        finally:
            tool.migrate_text = original_fn
        after = target.read_text(encoding="utf-8")

    problems: list[str] = []
    if result["status"] != "blocked":
        problems.append(f"집계가 달라졌는데 막지 않았다: status={result['status']}")
    if after != before:
        problems.append("막았다면서 파일을 되돌리지 않았다")
    _record(
        "test_parse_identity_interlock_blocks_and_rolls_back",
        not problems,
        "; ".join(problems),
    )


def test_repo_corpus_is_migrated() -> None:
    """자기 적용 — 이 저장소의 `active/` 에 옛 표기가 남아 있지 않다."""
    from workflow_kit.common.paths import memory_active_dir

    result = run(active_dir=memory_active_dir(REPO_ROOT), apply=False)
    _record(
        "test_repo_corpus_is_migrated",
        result["files_to_change"] == 0,
        f"옛 표기가 남은 파일 {result['files_to_change']}건 — "
        "`wk migrate-task-labels --apply` 로 통일할 것",
    )


def main() -> int:
    cases = [
        test_mapping_is_derived_from_registry,
        test_replacement_is_line_anchored,
        test_dry_run_writes_nothing,
        test_apply_is_idempotent,
        test_parse_identity_interlock_blocks_and_rolls_back,
        test_repo_corpus_is_migrated,
    ]
    for case in cases:
        case()
    total = len(cases)
    print(f"\n{total - len(FAILURES)}/{total} passed")
    if FAILURES:
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
