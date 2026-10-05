#!/usr/bin/env python3
"""task 파일 `## 🧭 Plan` 절 — 작업 전 계획을 기록으로 남긴다 (TASK-2026-10-05-main-002).

AI-native SDLC 플레이북 Stage 3 의 `plan.md` 대응
(`docs/planning/ai-native-sdlc-playbook-review-2026-10.md` §4.A1). 정본 §1 의 "작업 전
목적·범위·산출물 진술" 이 대화에만 남아 compact · 세션 경계에서 사라지고, 결과를 계획과
대조할 근거가 없었다. 새 파일 없이 task SSOT 에 절 하나를 둔다.

1. create 가 Plan 절을 Description 과 Implementation 사이에 쓴다 (값 · 빈 placeholder 둘 다)
2. Plan 절이 없는 옛 task 파일에 update 로 값을 쓰면 절을 끼워 넣는다
3. 한국어 표기 Plan 줄이 이미 있으면 절을 두 벌 만들지 않는다 (별칭까지 찾는다)
4. Plan 필드는 기본 병합, `--replace-field plan_*` 는 교체 + 버린 값 경고
5. 지시 표면 — 정본 §1 원칙과 backlog-update 스킬이 Plan 기록을 말한다 (생성물 기준)
"""
from __future__ import annotations

WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/skills/backlog-update/*",
    "workflow-source/core/global_workflow_standard.md",
)

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.project_docs import task_label  # noqa: E402
from workflow_kit.common.workflow_writes import PLAN_HEADING  # noqa: E402

BRANCH = "plan-smoke"
SCRIPT = SOURCE_ROOT / "skills" / "backlog-update" / "scripts" / "run_backlog_update.py"
FILES, ORDER, RISKS, PROOF = (task_label(k) for k in ("plan_files", "plan_order", "plan_risks", "plan_proof"))

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail else ''}")


def _workspace(td: str) -> Path:
    ws = Path(td)
    (ws / "docs").mkdir(parents=True)
    (ws / "docs" / "PROJECT_PROFILE.md").write_text("# Profile\n", encoding="utf-8")
    base = ws / "ai-workflow" / "memory" / "active" / BRANCH
    (base / "backlog" / "tasks").mkdir(parents=True)
    (base / "sessions").mkdir(parents=True)
    return ws


def _tasks(ws: Path) -> Path:
    return ws / "ai-workflow" / "memory" / "active" / BRANCH / "backlog" / "tasks"


def _run(ws: Path, *extra: str) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    env["CODEX_WORKFLOW_BRANCH"] = BRANCH
    proc = subprocess.run(
        [sys.executable, str(SCRIPT),
         "--project-profile-path", str(ws / "docs" / "PROJECT_PROFILE.md"),
         "--target-date", "2026-10-05", "--apply", *extra],
        capture_output=True, encoding="utf-8", errors="replace", check=False, env=env, cwd=str(ws),
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr[-1500:])
    return json.loads(proc.stdout)


def _plan_block(text: str) -> list[str]:
    """Plan 절 본문의 `- ` 줄들. 절이 없으면 []."""
    if PLAN_HEADING not in text:
        return []
    body = text.split(PLAN_HEADING, 1)[1].split("\n## ", 1)[0]
    return [line for line in body.splitlines() if line.startswith("- ")]


def case_1_create_writes_plan_between_sections() -> None:
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        out = _run(ws, "--mode", "create", "--task-name", "계획 있음", "--task-brief", "b",
                   "--plan-file", "a.py", "--plan-file", "b.py", "--plan-step", "1. x (d1)",
                   "--plan-proof", "check_x 5/5")
        text = (_tasks(ws) / f"{out['task_id']}.md").read_text(encoding="utf-8")
        out2 = _run(ws, "--mode", "create", "--task-name", "계획 없음", "--task-brief", "b")
        empty = (_tasks(ws) / f"{out2['task_id']}.md").read_text(encoding="utf-8")
    order_ok = (text.index("## 📝 Description") < text.index(PLAN_HEADING)
                < text.index("## 🛠️ Implementation"))
    expected = [f"- {FILES}: a.py", f"- {FILES}: b.py", f"- {ORDER}: 1. x (d1)",
                f"- {RISKS}:", f"- {PROOF}: check_x 5/5"]
    placeholders = [f"- {FILES}:", f"- {ORDER}:", f"- {RISKS}:", f"- {PROOF}:"]
    ok = order_ok and _plan_block(text) == expected and _plan_block(empty) == placeholders
    _record("case 1 (create 가 Plan 절을 Description 과 Implementation 사이에 쓴다)", ok,
            f"순서={order_ok} 값={_plan_block(text)} 빈={_plan_block(empty)}")


def _legacy_task(ws: Path, task_id: str, extra_plan: str = "") -> Path:
    """Plan 절이 없던 시절 형식의 task 파일 (본문 라벨은 한국어 별칭)."""
    path = _tasks(ws) / f"{task_id}.md"
    path.write_text(
        "---\n"
        f"id: {task_id}\nstatus: in_progress\ncreated_at: 2026-10-01\n"
        f"source_anchor: generic-{task_id.lower()}\nsource_path: backlog/2026-10-01.md\nkind: generic\n"
        "---\n\n"
        f"# {task_id} — 옛 task\n\n"
        "## 📝 Description\n\n- 상태: in_progress\n- 작업 내용: 옛 본문\n- 완료 기준: 옛 기준\n\n"
        f"{extra_plan}"
        "## 🛠️ Implementation / Content\n\n- 진행 현황: 옛 진행\n\n"
        "## ✅ Outcome\n\n- 작업 결과:\n",
        encoding="utf-8",
    )
    return path


def case_2_update_inserts_section_into_legacy_file() -> None:
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        path = _legacy_task(ws, "TASK-2026-10-01-plan-smoke-001")
        _run(ws, "--mode", "update", "--task-id", "TASK-2026-10-01-plan-smoke-001",
             "--task-name", "옛 task", "--plan-step", "1. y", "--plan-proof", "p")
        text = path.read_text(encoding="utf-8")
    block = _plan_block(text)
    ok = (text.count(PLAN_HEADING) == 1
          and text.index(PLAN_HEADING) < text.index("## 🛠️ Implementation")
          and f"- {ORDER}: 1. y" in block and f"- {PROOF}: p" in block
          and "옛 본문" in text and "옛 진행" in text)
    _record("case 2 (옛 task 파일에 update 하면 Plan 절을 끼워 넣는다)", ok, f"block={block}")


def case_3_korean_alias_section_is_not_duplicated() -> None:
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        path = _legacy_task(ws, "TASK-2026-10-01-plan-smoke-002",
                            extra_plan="## 🧭 Plan\n\n- 작업 순서: 1. 옛 단계\n- 검증 방법: 옛 증명\n\n")
        _run(ws, "--mode", "update", "--task-id", "TASK-2026-10-01-plan-smoke-002",
             "--task-name", "옛 task", "--plan-step", "2. 새 단계")
        text = path.read_text(encoding="utf-8")
    block = _plan_block(text)
    ok = text.count(PLAN_HEADING) == 1 and any("옛 단계" in b for b in block) and any("새 단계" in b for b in block)
    _record("case 3 (한국어 표기 Plan 이 있으면 절을 두 벌 만들지 않고 병합한다)", ok,
            f"절 수={text.count(PLAN_HEADING)} block={block}")


def case_4_merge_by_default_replace_on_request() -> None:
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        out = _run(ws, "--mode", "create", "--task-name", "병합", "--task-brief", "b",
                   "--plan-file", "a.py", "--plan-proof", "old")
        tid = out["task_id"]
        _run(ws, "--mode", "update", "--task-id", tid, "--task-name", "병합", "--plan-file", "c.py")
        merged = _plan_block((_tasks(ws) / f"{tid}.md").read_text(encoding="utf-8"))
        out3 = _run(ws, "--mode", "update", "--task-id", tid, "--task-name", "병합",
                    "--plan-proof", "new", "--replace-field", "plan_proof")
        replaced = _plan_block((_tasks(ws) / f"{tid}.md").read_text(encoding="utf-8"))
    ok = (f"- {FILES}: a.py" in merged and f"- {FILES}: c.py" in merged
          and f"- {PROOF}: new" in replaced and f"- {PROOF}: old" not in replaced
          and any("plan_proof" in w and "old" in w for w in out3.get("warnings", [])))
    _record("case 4 (Plan 은 기본 병합, --replace-field 는 교체 + 버린 값 경고)", ok,
            f"merged={merged} replaced={replaced}")


def case_5_instruction_surfaces_ask_for_plan() -> None:
    from workflow_kit.common.standard_rules import load_standard_rules, render_entrypoint_rules
    from workflow_kit.plugin_payload import render_agent_plugin

    rules = load_standard_rules(SOURCE_ROOT)
    principle = next((p for p in rules.principles if p.startswith("Before starting work")), "")
    block = render_entrypoint_rules(rules)
    skill = next((v for k, v in render_agent_plugin(rules).items() if k.endswith("backlog-update/SKILL.md")), "")
    flags = ("--plan-file", "--plan-step", "--plan-risk", "--plan-proof")
    ok = ("record the plan in the task file" in principle and principle in block
          and all(f in skill for f in flags))
    _record("case 5 (정본 §1 원칙 · 진입점 블록 · backlog-update 스킬이 Plan 기록을 지시한다)", ok,
            f"원칙={principle[:80]!r} 스킬 인자={[f for f in flags if f in skill]}")


def main() -> int:
    print("=== task Plan 절 (TASK-2026-10-05-main-002) ===")
    for fn in (case_1_create_writes_plan_between_sections,
               case_2_update_inserts_section_into_legacy_file,
               case_3_korean_alias_section_is_not_duplicated,
               case_4_merge_by_default_replace_on_request,
               case_5_instruction_surfaces_ask_for_plan):
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
