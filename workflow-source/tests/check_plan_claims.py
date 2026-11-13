#!/usr/bin/env python3
"""주장 트리 계획 — 파서 · 린트 · 지문 · 묶음 (ADR-031, `core/claim_plan_spec.md` §2 · §3 · §5 · §10).

`workflow_kit/common/plan_claims.py` 는 순수 함수다. 여기서는 파일 없이 그 함수들을 잰다.

1. 파서 — 주장 3단계와 위치, 결정의 칸(영어 · 한국어 표기), 묶음 수
2. 린트 L1~L10 — 규칙마다 최소 위반 하나가 그 규칙으로 잡히고, 깨끗한 계획은 조용하다
3. 강도 — L2 · L6 · L9 만 오류이고 나머지는 경고다
4. 지문 — 상태만 바꾸면 같고, 주장 · 질문 · 선택지 · 기본값을 바꾸면 다르고, 칸 표기와 무관하다
5. Plan 키 목록은 `PLAN_FIELD_KEYS` 하나다 — 두 벌을 다시 만들지 않는다
6. 파서 단일성 — 주장 · 결정을 읽고 계산하는 함수는 `plan_claims` 에만 정의돼 있다
7. 호환 — 두 라벨이 없는 task 줄은 계약을 거쳐도 그대로이고, 새 task 는 빈 `Claims` 줄을 갖지 않는다
8. 쓰기 표기 — 새 결정은 `proposed` 로, 상태 칸 고쳐 쓰기는 정본 표기로
9. 묶음 — `plan-status` 의 "재지 않는 주장" 이 L7 의 것과 같고, 주장이 없으면 절을 내지 않는다
"""
from __future__ import annotations

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
)

import ast
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import plan_claims as pc  # noqa: E402
from workflow_kit.common import project_docs, workflow_writes  # noqa: E402
from workflow_kit.common.project_docs import PLAN_FIELD_KEYS, PLAN_OPTIONAL_KEYS, task_label  # noqa: E402
from workflow_kit.tools import backlog_update, plan_status  # noqa: E402

FAILURES: list[str] = []

CLAIMS = task_label(pc.CLAIMS_KEY)
DECISIONS = task_label(pc.DECISIONS_KEY)

GOOD_CLAIMS = [
    "C1 미열람 결정이 남은 task 는 done 으로 닫히지 않는다",
    "C1.1 backlog-update 는 done 전이에서 결정 상태를 계산한다",
    "C1.1.1 @ workflow-source/workflow_kit/tools/backlog_update.py:10-20 · main()",
    "C1.1.2 @ new: workflow-source/workflow_kit/common/plan_claims.py · compute_states()",
    "C2 옛 task 파일은 지금과 같게 읽힌다",
]
GOOD_DECISION = "D1 [C1] 막는가? | default: block | options: block = 거부한다; warn = 경고만 낸다 | state: proposed"
GOOD_CRITERIA = ["[C1.1] done 이 거부된다", "[C2] 기존 파일이 그대로다"]


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def _plan(claims: list[str] | None = None, decisions: list[str] | None = None) -> pc.Plan:
    return pc.parse_plan_values(GOOD_CLAIMS if claims is None else claims,
                                [GOOD_DECISION] if decisions is None else decisions)


def _rules(issues: list[pc.LintIssue], severity: str | None = None) -> set[str]:
    return {i.rule for i in issues if severity is None or i.severity == severity}


def _lines_of(file_path: str) -> int | None:
    return {"workflow-source/workflow_kit/tools/backlog_update.py": 100}.get(file_path)


def case_1_parser() -> None:
    problems: list[str] = []
    plan = _plan()
    depths = [c.depth for c in plan.claims]
    if depths != [1, 2, 3, 3, 1]:
        problems.append(f"깊이 {depths}")
    located = plan.claim("C1.1.1")
    if not (located and located.location and (located.location.start, located.location.end) == (10, 20)
            and located.location.symbol == "main()" and not located.location.new):
        problems.append(f"위치를 못 읽었다: {located}")
    fresh = plan.claim("C1.1.2")
    if not (fresh and fresh.location and fresh.location.new and fresh.location.start is None):
        problems.append(f"`@ new:` 를 못 읽었다: {fresh}")
    decision = plan.decisions[0]
    if (decision.id, decision.claim_id, decision.default, decision.option_values, decision.state) != (
            "D1", "C1", "block", ("block", "warn"), "proposed") or decision.problems:
        problems.append(f"결정을 못 읽었다: {decision}")
    korean = pc.parse_decision_value(
        "D1 [C1] 막는가? | 기본: block | 선택: block = 거부한다; warn = 경고만 낸다 | 상태: answered:warn")
    if korean.problems or korean.state != "answered:warn" or korean.option_values != ("block", "warn"):
        problems.append(f"한국어 칸 표기를 못 읽었다: {korean}")
    no_state = pc.parse_decision_value("D2 [C2] 질문 | default: a | options: a = 가; b = 나")
    if no_state.problems or no_state.state != pc.STATE_PROPOSED:
        problems.append(f"상태 칸이 없으면 proposed 여야 한다: {no_state}")
    split = pc.parse_plan([f"- {CLAIMS}: C1 하나", "- Files that change: a.py", f"- {CLAIMS}: C2 둘"])
    if split.claim_runs != 2 or len(split.claims) != 2:
        problems.append(f"나뉜 묶음을 전부 읽고 세어야 한다: runs={split.claim_runs} n={len(split.claims)}")
    alias = pc.parse_plan(["- 주장: C1 한국어 라벨", "- 결정: " + GOOD_DECISION])
    if len(alias.claims) != 1 or len(alias.decisions) != 1:
        problems.append("한국어 라벨 별칭을 못 읽었다")
    _record("case 1 (파서 — 주장 · 위치 · 결정 칸 · 묶음)", problems)


def case_2_each_rule_fires() -> None:
    problems: list[str] = []
    clean = pc.lint_plan(_plan(), criteria=GOOD_CRITERIA, file_line_count=_lines_of)
    if clean:
        problems.append(f"깨끗한 계획에서 린트가 났다: {[i.render() for i in clean]}")

    def expect(rule: str, plan: pc.Plan, criteria: list[str] | None = None, *, counter: object = _lines_of) -> None:
        issues = pc.lint_plan(plan, criteria=GOOD_CRITERIA if criteria is None else criteria,
                              file_line_count=counter)  # type: ignore[arg-type]
        if rule not in _rules(issues):
            problems.append(f"{rule} 가 안 났다: {[i.render() for i in issues]}")

    expect("L1", _plan([f"C{n} 주장 {n}" for n in range(1, 7)], []), [])
    expect("L2", _plan(["C1 하나", "C1 겹침"], []))
    expect("L2", _plan(["C1 하나", "C3 건너뜀"], []))
    expect("L2", _plan(["C1.1 부모 없음"], []))
    expect("L2", _plan(["Cx 이상한 ID"], []))
    expect("L3", _plan(["C1 " + "가" * 81], []))
    expect("L3", _plan(["C1 하나를 한다; 또 하나를 한다"], []))
    expect("L4", _plan(["C1 workflow_kit/tools/backlog_update.py 를 고친다"], []))
    expect("L5", _plan(["C1 하나", "C1.1 둘", "C1.1.1 @ 없는/파일.py:1 · f()"], []))
    expect("L5", _plan(["C1 하나", "C1.1 둘", "C1.1.1 @ workflow-source/workflow_kit/tools/backlog_update.py:90-200 · f()"], []))
    expect("L5", _plan(["C1 하나", "C1.1 둘", "C1.1.1 @ a.py:1 · f()"], []), counter=None)
    expect("L6", _plan(decisions=["D1 [C9] 없는 주장 | default: a | options: a = 가; b = 나"]))
    expect("L6", _plan(decisions=["D1 [C1] 기본값이 밖 | default: z | options: a = 가; b = 나"]))
    expect("L6", _plan(decisions=["D1 [C1] 선택지 하나 | default: a | options: a = 가"]))
    expect("L6", _plan(decisions=["D1 [C1] 질문 | 안에 구분자 | default: a | options: a = 가; b = 나"]))
    expect("L6", _plan(decisions=["D1 [C1] 상태 값이 밖 | default: a | options: a = 가; b = 나 | state: answered:z"]))
    expect("L6", _plan(decisions=["D1 [C1] 값 문법 | default: A값 | options: A값 = 가; b = 나"]))
    expect("L6", _plan(decisions=[f"D{n} [C1] 질문 {n} | default: a | options: a = 가; b = 나" for n in range(1, 7)]))
    expect("L6", _plan(decisions=[GOOD_DECISION, GOOD_DECISION]))
    expect("L7", _plan(), ["인용 없는 기준"])
    expect("L8", _plan(["C1 구현을 80% 마쳤다"], []))
    expect("L8", _plan(["C1 파서 작성 완료"], []))
    expect("L9", pc.parse_plan([f"- {CLAIMS}: C1 하나", "- Proof: p", f"- {CLAIMS}: C2 둘"]))
    expect("L10", _plan(), ["[C9] 없는 주장을 인용", *GOOD_CRITERIA])
    _record("case 2 (린트 L1~L10 — 규칙마다 최소 위반이 잡힌다)", problems)


def case_3_severity() -> None:
    problems: list[str] = []
    if pc.ERROR_RULES != frozenset({"L2", "L6", "L9"}):
        problems.append(f"오류 규칙 집합이 바뀌었다: {sorted(pc.ERROR_RULES)}")
    everything = pc.lint_plan(
        pc.parse_plan([
            f"- {CLAIMS}: C1 a/b.py 를 80% 고쳤다; 그리고 " + "가" * 80,
            f"- {CLAIMS}: C1 겹침",
            "- Proof: p",
            f"- {CLAIMS}: C3 건너뜀",
            f"- {DECISIONS}: D1 [C9] 질문 | default: z | options: a = 가",
        ]),
        criteria=["[C8] 없는 인용"], file_line_count=_lines_of)
    errors = _rules(everything, "error")
    warnings = _rules(everything, "warning")
    if errors != {"L2", "L6", "L9"}:
        problems.append(f"오류로 난 규칙: {sorted(errors)}")
    if not {"L3", "L4", "L7", "L8", "L10"} <= warnings or warnings & pc.ERROR_RULES:
        problems.append(f"경고로 난 규칙: {sorted(warnings)}")
    if not pc.has_error_rules(_plan(["C1 하나", "C1 겹침"], [])) or pc.has_error_rules(_plan()):
        problems.append("has_error_rules 가 오류 규칙과 어긋난다")
    _record("case 3 (강도 — L2 · L6 · L9 만 오류)", problems)


def case_4_digest() -> None:
    problems: list[str] = []
    base = pc.plan_digest(_plan())
    if not base.startswith("sha256:") or len(base) != 7 + 64:
        problems.append(f"지문 형식: {base}")
    same_state = pc.plan_digest(_plan(decisions=[GOOD_DECISION.replace("state: proposed", "state: answered:warn")]))
    if same_state != base:
        problems.append("상태만 바꿨는데 지문이 달라졌다")
    korean_columns = pc.plan_digest(_plan(decisions=[
        "D1 [C1] 막는가? | 기본: block | 선택: block = 거부한다; warn = 경고만 낸다 | 상태: kept"]))
    if korean_columns != base:
        problems.append("칸 이름 표기만 다른데 지문이 달라졌다")
    korean_label = pc.plan_digest(pc.parse_plan(
        [f"- 주장: {c}" for c in GOOD_CLAIMS] + [f"- 결정: {GOOD_DECISION}"]))
    if korean_label != base:
        problems.append("라벨 표기만 다른데 지문이 달라졌다")
    changed = {
        "주장 문장": _plan([GOOD_CLAIMS[0] + " 정말", *GOOD_CLAIMS[1:]]),
        "질문": _plan(decisions=[GOOD_DECISION.replace("막는가?", "막을까?")]),
        "선택지": _plan(decisions=[GOOD_DECISION.replace("warn = 경고만 낸다", "warn = 경고")]),
        "기본값": _plan(decisions=[GOOD_DECISION.replace("default: block", "default: warn")]),
    }
    for what, plan in changed.items():
        if pc.plan_digest(plan) == base:
            problems.append(f"{what} 을 바꿨는데 지문이 같다")
    _record("case 4 (지문 — 상태 · 표기와 무관, 내용이 바뀌면 다르다)", problems)


def case_5_single_plan_key_list() -> None:
    problems: list[str] = []
    if backlog_update.PLAN_FIELDS is not PLAN_FIELD_KEYS:
        problems.append("backlog_update.PLAN_FIELDS 가 PLAN_FIELD_KEYS 와 다른 객체다")
    if workflow_writes._plan_keys() is not PLAN_FIELD_KEYS:
        problems.append("workflow_writes 가 PLAN_FIELD_KEYS 를 쓰지 않는다")
    if PLAN_FIELD_KEYS[:2] != (pc.CLAIMS_KEY, pc.DECISIONS_KEY) or set(PLAN_OPTIONAL_KEYS) != {pc.CLAIMS_KEY, pc.DECISIONS_KEY}:
        problems.append(f"순서 · 선택 키: {PLAN_FIELD_KEYS} / {PLAN_OPTIONAL_KEYS}")
    # 같은 튜플을 리터럴로 다시 적은 곳이 없는가 — 다시 적으면 갈라진다.
    for path in sorted((SOURCE_ROOT / "workflow_kit").rglob("*.py")):
        if path.name == "project_docs.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Tuple, ast.List)):
                values = [e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                if {"plan_files", "plan_order", "plan_risks", "plan_proof"} <= set(values):
                    problems.append(f"Plan 키 목록을 다시 적었다: {path.relative_to(SOURCE_ROOT)}:{node.lineno}")
    for key in PLAN_FIELD_KEYS:
        if key not in project_docs.TASK_FIELD_LABELS or key not in project_docs.TASK_FIELD_ALIASES:
            problems.append(f"라벨 표에 {key} 가 없다")
    _record("case 5 (Plan 키 목록은 PLAN_FIELD_KEYS 하나다)", problems)


def case_6_single_parser() -> None:
    problems: list[str] = []
    owned = {"parse_plan", "parse_claim_value", "parse_decision_value", "lint_plan", "plan_digest",
             "compute_states", "effective_responses", "open_decision_ids", "claim_bundles"}
    for path in sorted((SOURCE_ROOT / "workflow_kit").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        defined = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        if path.name == "plan_claims.py":
            missing = owned - defined
            if missing:
                problems.append(f"plan_claims 에 없는 함수: {sorted(missing)}")
        elif owned & defined:
            problems.append(f"{path.relative_to(SOURCE_ROOT)} 가 같은 이름을 또 정의한다: {sorted(owned & defined)}")
    # 소비자가 그 모듈을 실제로 부르는가.
    consumers = {
        "tools/backlog_update.py": "plan_claims",
        "tools/plan_status.py": "plan_claims",
        "common/plan_tasks.py": "plan_claims",
        "common/state/builder.py": "plan_tasks",
        "tools/refresh_state.py": "plan_tasks",
        "tools/session_start.py": "plan_tasks",
    }
    for rel, module in consumers.items():
        if module not in (SOURCE_ROOT / "workflow_kit" / rel).read_text(encoding="utf-8"):
            problems.append(f"{rel} 가 {module} 를 쓰지 않는다")
    _record("case 6 (파서 단일성 — 계산 함수는 plan_claims 에만 있다)", problems)


LEGACY_LINES = [
    "---", "id: TASK-2026-10-01-x-001", "status: in_progress", "---", "",
    "# TASK-2026-10-01-x-001 — 옛 task", "", "## 📝 Description", "",
    "- Status: in_progress", "- Completion criteria: 옛 기준", "",
    "## 🧭 Plan", "", "- Files that change: a.py", "- Files that change: b.py", "- Files that change: c.py",
    "- Order of work:", "- Plan risks:", "- Proof:", "",
    "## 🛠️ Implementation / Content", "", "- Progress: 옛 진행", "",
]


def case_7_compat() -> None:
    problems: list[str] = []
    verdict = backlog_update.enforce_plan_contract(
        list(LEGACY_LINES), previous_lines=list(LEGACY_LINES), plan_claim_args=[], plan_decision_args=[],
        decision_state_args=[], replace_fields=set(), requested_status=None, status="in_progress",
        current_status="in_progress", progress_note="메모", workspace_root=SOURCE_ROOT)
    if verdict.lines != LEGACY_LINES or verdict.warnings or verdict.error_code:
        problems.append(f"두 라벨이 없는 task 가 계약을 거쳐 바뀌었다: {verdict.warnings} {verdict.error_code}")
    empty_plan = backlog_update.plan_section_lines({})
    if any(line.startswith((f"- {CLAIMS}", f"- {DECISIONS}")) for line in empty_plan):
        problems.append(f"새 task 에 빈 주장 · 결정 줄이 생긴다: {empty_plan}")
    if [l for l in empty_plan if l.startswith("- ")] != [
            f"- {task_label(k)}:" for k in PLAN_FIELD_KEYS if k not in PLAN_OPTIONAL_KEYS]:
        problems.append(f"기존 placeholder 넷이 바뀌었다: {empty_plan}")
    with_claims = backlog_update.plan_section_lines({pc.CLAIMS_KEY: ["C1 하나"]})
    if with_claims[2] != f"- {CLAIMS}: C1 하나":
        problems.append(f"주장은 절의 맨 앞이다: {with_claims}")
    # 4필드 Plan 절이 있는 파일에 Claims 줄을 제자리에 넣는다 (ADR-031 결정 3).
    inserted = workflow_writes._ensure_plan_section(list(LEGACY_LINES), frozenset({CLAIMS, DECISIONS}))
    plan_at = inserted.index("## 🧭 Plan")
    if inserted[plan_at + 2: plan_at + 5] != [f"- {CLAIMS}:", f"- {DECISIONS}:", "- Files that change: a.py"]:
        problems.append(f"선택 라벨 줄의 자리: {inserted[plan_at: plan_at + 6]}")
    if workflow_writes._ensure_plan_section(list(LEGACY_LINES)) != LEGACY_LINES:
        problems.append("값이 없는데 줄을 넣었다")
    _record("case 7 (호환 — 두 라벨이 없는 task 는 그대로, 새 task 에 빈 줄 없음)", problems)


def case_8_write_notation() -> None:
    problems: list[str] = []
    fixed, dropped = pc.normalize_new_decision(
        "D1 [C1] 막는가? | 기본: block | 선택: block = 거부한다; warn = 경고만 낸다 | 상태: kept")
    if fixed != GOOD_DECISION or not dropped:
        problems.append(f"새 결정은 정본 표기 · proposed 여야 한다: {fixed!r} dropped={dropped}")
    lines = [f"  - {DECISIONS}: " + GOOD_DECISION.replace("state: proposed", "상태: kept").replace("default:", "기본:")]
    rewritten, changes = pc.rewrite_decision_states(lines, {"D1": "answered:warn"})
    if changes != [("D1", "kept", "answered:warn")] or not rewritten[0].endswith("| state: answered:warn") \
            or not rewritten[0].startswith(f"  - {DECISIONS}: D1 [C1]") or "default: block" not in rewritten[0]:
        problems.append(f"상태 칸 고쳐 쓰기: {rewritten} {changes}")
    untouched, none = pc.rewrite_decision_states([f"- {DECISIONS}: D1 깨진 줄"], {"D1": "kept"})
    if none or untouched != [f"- {DECISIONS}: D1 깨진 줄"]:
        problems.append("읽을 수 없는 줄을 고쳐 썼다")
    if pc.decision_identity(GOOD_DECISION) != pc.decision_identity(GOOD_DECISION.replace("proposed", "kept")):
        problems.append("상태만 다른 결정을 다른 결정으로 본다")
    _record("case 8 (쓰기 표기 — 새 결정은 proposed, 고쳐 쓰기는 정본 표기)", problems)


def case_9_bundles_match_l7() -> None:
    problems: list[str] = []
    plan = _plan()
    criteria = ["[C1.1.1] 위치를 인용한 기준", "인용 없는 기준"]
    bundles = pc.claim_bundles(plan, criteria)
    unmeasured = {b.claim.id for b in bundles if b.unmeasured}
    l7 = {i.ref for i in pc.lint_plan(plan, criteria=criteria, file_line_count=_lines_of) if i.rule == "L7"}
    if unmeasured != l7 or unmeasured != {"C2"}:
        problems.append(f"재지 않는 주장: 묶음 {sorted(unmeasured)} · L7 {sorted(l7)}")
    if [(b.claim.id, b.criteria) for b in bundles] != [("C1", (1,)), ("C2", ())]:
        problems.append(f"후손 인용은 1단계 조상에 묶인다: {[(b.claim.id, b.criteria) for b in bundles]}")
    markdown = plan_status.render_markdown(bundles, [("D1", "proposed")])
    expected = "\n".join([
        "### 주장별", "", "| 주장 | 기준 | 판정 |", "|---|---|---|",
        "| C1 미열람 결정이 남은 task 는 done 으로 닫히지 않는다 | #1 |  |",
        "| C2 옛 task 파일은 지금과 같게 읽힌다 | — | 재지 않는 주장 |",
        "", "- 열린 결정: D1 (proposed)",
    ])
    if markdown != expected:
        problems.append(f"보고에 붙일 절이 기대와 다르다:\n{markdown}")
    if plan_status.render_markdown([], []) != "":
        problems.append("주장이 없는데 절을 냈다")
    _record("case 9 (묶음 — 재지 않는 주장은 L7 과 같은 판정)", problems)


CASES = [
    case_1_parser,
    case_2_each_rule_fires,
    case_3_severity,
    case_4_digest,
    case_5_single_plan_key_list,
    case_6_single_parser,
    case_7_compat,
    case_8_write_notation,
    case_9_bundles_match_l7,
]


def main() -> int:
    print("=== 주장 트리 계획 — 파서 · 린트 · 지문 (ADR-031) ===")
    for fn in CASES:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            FAILURES.append(fn.__name__)
            print(f"  FAIL  {fn.__name__} — 예외 {type(exc).__name__}: {exc}")
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    print(f"\n{len(CASES)}/{len(CASES)} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
