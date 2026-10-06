#!/usr/bin/env python3
"""기존 진입점 다이어트 — kit 가 생성한 그대로인 절만 고친다 (TASK-2026-10-06-main-004, 진입점 다이어트 3).

판정 정본은 `workflow_kit/common/entry_diet.py`, 배선은 `ensure-entrypoints --diet`. 옛 생성물 fixture 는
`tests/fixtures/entry_diet/` — 발행 태그 v1.19.0 과 한국어 템플릿 마지막 상태(825478bc)를 실제로
bootstrap 한 출력이다 (`.txt` — 문서 검사가 진입점 문서로 읽지 않게).

1. 옛 생성물 3종 → 다이어트 후 크게 줄고, 걷힌 절이 남지 않고, 남은 kit 절은 현행 템플릿과 같다
2. 사용자가 고친 옛 절은 `edited` 로 남는다 (본문 보존)
3. 멱등 — 다이어트한 결과를 다시 돌리면 바꿀 것이 없다
4. `ensure-entrypoints` 배선 — `--apply` 없이는 안 쓰고, 포크 선언 파일은 `--apply` 여도 안 쓴다
"""
from __future__ import annotations

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/fixtures/entry_diet/*",
    "workflow-source/templates/*",
    "workflow-source/core/global_workflow_standard.md",
    "workflow-source/pyproject.toml",
)

#: 현행 템플릿을 얻으려고 하네스를 bootstrap 한다.
CHECK_TIMEOUT_S = 150

import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.bootstrap_lib.harnesses.entry_sections import ENTRY_BUDGET_BYTES  # noqa: E402
from workflow_kit.common.entry_diet import HEADING_ALIASES, normalize, plan_diet, split_sections  # noqa: E402
from workflow_kit.tools.ensure_entrypoints import _current_templates, diet  # noqa: E402

FIXTURES = SOURCE_ROOT / "tests" / "fixtures" / "entry_diet"
#: fixture → (하네스, 진입점 파일)
CASES = {
    "v1.19.0-claude-code-CLAUDE.md.txt": ("claude-code", "CLAUDE.md"),
    "v1.19.0-grok-build-GROK.md.txt": ("grok-build", "GROK.md"),
    "825478bc-claude-code-CLAUDE.md.txt": ("claude-code", "CLAUDE.md"),
}
FORK_LINE = "<!-- standard-ai-workflow-kit-fork: check_entry_diet -->"
#: 다이어트 뒤에도 반드시 있어야 하는 절 (현행 템플릿에 있을 때).
CORE_TITLES = ("Read these first", "Working Principles", "Session Close Order", "Memory Update Paths",
               "Language and context principles")

_failures: list[str] = []
_passes: list[str] = []
_TEMPLATES: dict[str, str] = {}


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail else ''}")


def _templates() -> dict[str, str]:
    if not _TEMPLATES:
        _TEMPLATES.update(_current_templates(["claude-code", "grok-build"]))
    return _TEMPLATES


def case_1_old_generated_entries_shrink_to_current() -> None:
    problems: list[str] = []
    summary: list[str] = []
    for fixture, (_harness, entry) in CASES.items():
        old = (FIXTURES / fixture).read_text(encoding="utf-8")
        current = _templates()[entry]
        plan = plan_diet(old, current, ENTRY_BUDGET_BYTES)
        _, after = split_sections(plan.new_text)
        _, cur_sections = split_sections(current)
        cur = {t: b for t, b in cur_sections}
        stale = [t for t, _ in after if t not in cur]
        drifted = [t for t, b in after if t in cur and normalize(b) != normalize(cur[t])
                   and t not in ("Project run defaults", "Documentation conventions")]
        counts = plan.counts()
        # 걷기만 하고 교체를 놓치면(별칭 누락 등) 핵심 절이 통째로 사라진다 — 존재를 따로 잰다.
        lost = [t for t in CORE_TITLES if t in cur and t not in {title for title, _ in after}]
        if lost:
            problems.append(f"{fixture}: 핵심 절이 사라졌다 {lost}")
        summary.append(f"{fixture.split('-')[0]}:{entry} {plan.bytes_before}→{plan.bytes_after}B")
        if counts["edited"] or stale or drifted:
            problems.append(f"{fixture}: edited={counts['edited']} 남은 옛 제목={stale} 현행과 다른 kit 절={drifted}")
        if plan.bytes_after > ENTRY_BUDGET_BYTES or plan.bytes_after >= plan.bytes_before * 0.85:
            problems.append(f"{fixture}: {plan.bytes_before}→{plan.bytes_after}B (예산 {ENTRY_BUDGET_BYTES}B, 15% 이상 줄어야)")
    _record("case 1 (옛 생성물 3종이 현행 템플릿 절로 줄어든다)", not problems, "; ".join(problems or summary))


def case_2_user_edited_section_is_kept() -> None:
    old = (FIXTURES / "v1.19.0-claude-code-CLAUDE.md.txt").read_text(encoding="utf-8")
    edited = old.replace("## Read next\n", "## Read next\n\n- 우리 팀 위키: https://wiki.example/x\n", 1)
    plan = plan_diet(edited, _templates()["CLAUDE.md"], ENTRY_BUDGET_BYTES)
    actions = {a.title: a.action for a in plan.actions}
    # 별칭으로 현행 절에 대응하는 한국어 제목을 고친 경우는 걷힌 절이 아니다 — keep (edited 오보 방지).
    ko = (FIXTURES / "825478bc-claude-code-CLAUDE.md.txt").read_text(encoding="utf-8")
    ko_edited = ko.replace("## 항상 먼저 읽을 문서\n", "## 항상 먼저 읽을 문서\n\n- 팀 규칙: docs/TEAM.md\n", 1)
    ko_actions = {a.title: a.action for a in plan_diet(ko_edited, _templates()["CLAUDE.md"], ENTRY_BUDGET_BYTES).actions}
    ok = (actions.get("Read next") == "edited" and "wiki.example/x" in plan.new_text and "## Read next" in plan.new_text
          and ko_actions.get("항상 먼저 읽을 문서") == "keep")
    _record("case 2 (고친 옛 절은 남는다 — 걷힌 제목이면 edited, 현행에 대응하면 keep)", ok,
            f"Read next={actions.get('Read next')} · 항상 먼저 읽을 문서={ko_actions.get('항상 먼저 읽을 문서')}")


def case_3_idempotent() -> None:
    problems = []
    for fixture, (_harness, entry) in CASES.items():
        current = _templates()[entry]
        once = plan_diet((FIXTURES / fixture).read_text(encoding="utf-8"), current, ENTRY_BUDGET_BYTES)
        twice = plan_diet(once.new_text, current, ENTRY_BUDGET_BYTES)
        counts = twice.counts()
        if counts["replace"] or counts["remove"] or twice.new_text != once.new_text:
            problems.append(f"{fixture}: 두 번째 {counts}")
    _record("case 3 (멱등 — 두 번째 다이어트는 바꿀 것이 없다)", not problems, "; ".join(problems))


def case_4_ensure_entrypoints_writes_only_with_apply_and_never_forks() -> None:
    old = (FIXTURES / "v1.19.0-claude-code-CLAUDE.md.txt").read_text(encoding="utf-8")
    forked = old.replace("\n", f"\n{FORK_LINE}\n", 1)
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        path = root / "CLAUDE.md"
        path.write_text(old, encoding="utf-8")
        report, applied = diet(root, ["claude-code"], apply=False)
        if applied or path.read_text(encoding="utf-8") != old:
            problems.append("--apply 없이 썼다")
        if not report or report[0]["counts"]["remove"] == 0:
            problems.append(f"dry-run 보고가 비었다: {report}")
        path.write_text(forked, encoding="utf-8")
        report, applied = diet(root, ["claude-code"], apply=True)
        if applied or path.read_text(encoding="utf-8") != forked or not report[0]["forked"]:
            problems.append("포크 선언 파일을 썼다")
        path.write_text(old, encoding="utf-8")
        report, applied = diet(root, ["claude-code"], apply=True)
        written = path.read_text(encoding="utf-8")
        if applied != ["CLAUDE.md"] or len(written.encode()) != report[0]["bytes_after"]:
            problems.append(f"--apply 가 쓰지 않았다: applied={applied}")
    _record("case 4 (ensure-entrypoints --diet: --apply 일 때만 쓰고 포크는 쓰지 않는다)", not problems,
            "; ".join(problems))


def case_5_aliases_point_at_current_titles() -> None:
    titles = {t for text in _templates().values() for t, _ in split_sections(text)[1]}
    dangling = [f"{k}→{v}" for k, v in HEADING_ALIASES.items() if v not in titles]
    _record("case 5 (한국어 제목 별칭이 현행 템플릿 제목을 가리킨다)", not dangling, f"없는 대상: {dangling}")


def main() -> int:
    print("=== 기존 진입점 다이어트 (TASK-2026-10-06-main-004) ===")
    for fn in (case_1_old_generated_entries_shrink_to_current,
               case_2_user_edited_section_is_kept,
               case_3_idempotent,
               case_4_ensure_entrypoints_writes_only_with_apply_and_never_forks,
               case_5_aliases_point_at_current_titles):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            _record(fn.__name__, False, f"{type(exc).__name__}: {str(exc)[:300]}")
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
