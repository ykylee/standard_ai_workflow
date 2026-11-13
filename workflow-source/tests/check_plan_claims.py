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
10. 호환(전수) — 이 저장소의 task 파일 전부가 계약을 거쳐도 한 줄도 안 바뀐다 (주장 · 결정이 없는 파일)
11. 계약 적용 — 교체해도 `answered` 는 남고, 같은 상태를 다시 줘도 경고를 되풀이하지 않고, 오류 상태에서는 칸을 다시 적지 않는다
12. 린트 표 — 입력마다 나와야 하는 (규칙, 강도, 대상) 을 **전부** 대조한다: 경계 · 범위 · 강도 · 문법
13. 지문의 본문 — 스펙 §5 의 문면대로 손으로 만든 본문의 sha256 과 같다
14. 열린 상태 — `proposed` · `unopened` · `disputed` 만 열린 결정이고, 칸 기준 계수는 못 읽는 결정도 센다
"""
from __future__ import annotations

#: case 10 이 이 저장소의 task 파일을 읽는다 — 다른 쓰기와 겹치면 반쯤 쓰인 파일을 볼 수 있다.
REQUIRES_QUIET_REPO = True

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "ai-workflow/memory/*",
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
    indented = pc.parse_plan([f"    - {CLAIMS}: C1 들여쓴 줄", f"\t- {DECISIONS}: {GOOD_DECISION}"])
    if len(indented.claims) != 1 or len(indented.decisions) != 1:
        problems.append("들여쓴 주장 · 결정 줄을 못 읽었다 — 들여쓴 열린 결정이 게이트에 안 보인다")
    glued = pc.parse_plan([f"- {CLAIMS}:C1 하나", f"- {DECISIONS}:{GOOD_DECISION}"])
    if glued.claims or glued.decisions or glued.claim_runs or glued.decision_runs:
        problems.append("콜론 뒤 공백이 없는 줄을 라벨 줄로 읽었다 — 라벨 줄은 `- 라벨: 값` 이다")
    placeholder = pc.parse_plan([f"- {CLAIMS}:", f"- {CLAIMS}: C1 하나", "- Proof: p", f"- {CLAIMS}:"])
    if placeholder.claim_runs != 1 or len(placeholder.claims) != 1:
        problems.append(f"값 없는 라벨 줄을 묶음으로 셌다: runs={placeholder.claim_runs}")
    between = pc.parse_plan([f"- {CLAIMS}: C1 하나", f"- {CLAIMS}:", f"- {CLAIMS}: C2 둘"])
    if between.claim_runs != 1:
        problems.append(f"값 없는 라벨 줄이 묶음을 끊었다: runs={between.claim_runs}")
    for label in (DECISIONS, "결정"):
        blank = pc.parse_plan([f"- {CLAIMS}: C1 하나", f"- {label}:", f"- {DECISIONS}: {GOOD_DECISION}", f"- {label}:   "])
        if len(blank.decisions) != 1 or blank.decision_runs != 1 or pc.open_decision_ids(blank) != ["D1"]:
            problems.append(f"값 없는 `- {label}:` 줄을 결정 · 묶음으로 셌다: n={len(blank.decisions)} runs={blank.decision_runs}")
        only_blank = pc.parse_plan([f"- {CLAIMS}: C1 하나", f"- {label}:"])
        if only_blank.decisions or pc.open_decision_ids(only_blank) or pc.lint_errors(
                pc.lint_plan(only_blank, criteria=["[C1] 기준"], file_line_count=_lines_of)):
            problems.append(f"값 없는 `- {label}:` 줄이 결정으로 읽혔다")
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
    expect("L1", _plan(["C1 부모", *[f"C1.{n} 자식 {n}" for n in range(1, 7)]], []), [])
    expect("L2", _plan(["C1 하나", "C1.1 둘", "C1.1.1 @ new: a.py · f()", "C1.1.3 @ new: b.py · g()"], []))
    expect("L3", _plan(["C1 부모", "C1.1 " + "나" * 81], []))
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
    expect("L6", _plan(decisions=["D1 [C1] 선택지 값 문법 | default: a | options: a = 가; B값 = 나; c = 다"]))
    expect("L6", _plan(decisions=["D1 [C1] 상태를 못 읽음 | default: a | options: a = 가; b = 나 | state: maybe"]))
    expect("L6", _plan(decisions=["D1 [C1] 칸이 두 번 | default: a | default: b | options: a = 가; b = 나"]))
    expect("L6", _plan(decisions=["D1 [C1] 선택지가 겹침 | default: a | options: a = 가; a = 나"]))
    expect("L5", _plan(["C1 하나", "C1.1 둘", "C1.1.1 위치가 아니라 문장이다"], []))
    expect("L6", _plan(decisions=[f"D{n} [C1] 질문 {n} | default: a | options: a = 가; b = 나" for n in range(1, 7)]))
    expect("L6", _plan(decisions=[GOOD_DECISION, GOOD_DECISION]))
    expect("L7", _plan(), ["인용 없는 기준"])
    expect("L8", _plan(["C1 구현을 80% 마쳤다"], []))
    expect("L8", _plan(["C1 파서 작성 완료"], []))
    expect("L8", _plan(["C1 the parser is done."], []))
    expect("L8", _plan(["C1 파서를 썼다 ✅"], []))

    # 규칙마다 **그 규칙만** 어긴 입력이 그 규칙 하나로 잡히는가 — 다른 규칙이 대신 잡으면 판정이 죽어도 모른다.
    def only(rule: str, plan: pc.Plan, criteria: list[str]) -> None:
        got = _rules(pc.lint_plan(plan, criteria=criteria, file_line_count=_lines_of))
        if got != {rule}:
            problems.append(f"{rule} 만 나야 하는데 {sorted(got)}")

    only("L6", _plan(["C1 하나"], ["D1 [C1] 선택지 값 문법 | default: a | options: a = 가; B값 = 나"]), ["[C1] 기준"])
    only("L6", _plan(["C1 하나"], ["D1 [C1] 상태를 못 읽음 | default: a | options: a = 가; b = 나 | state: maybe"]), ["[C1] 기준"])
    only("L6", _plan(["C1 하나"], ["D1 [C1] 선택지가 겹침 | default: a | options: a = 가; a = 나"]), ["[C1] 기준"])
    only("L1", _plan(["C1 부모", *[f"C1.{n} 자식 {n}" for n in range(1, 7)]], []), ["[C1] 기준"])
    only("L3", _plan(["C1 부모", "C1.1 " + "나" * 81], []), ["[C1] 기준"])
    only("L8", _plan(["C1 the parser is done."], []), ["[C1] 기준"])
    only("L8", _plan(["C1 파서를 썼다 ✅"], []), ["[C1] 기준"])
    unreadable = _plan(["C1 하나"], ["D1 [C1] 상태를 못 읽음 | default: a | options: a = 가; b = 나 | state: maybe"])
    if pc.open_decision_ids(unreadable) != ["D1"]:
        problems.append(f"읽을 수 없는 결정은 열린 것으로 세어야 한다: {pc.open_decision_ids(unreadable)}")
    # 상태는 answered 로 읽히지만 줄의 다른 칸이 깨진 결정 — 닫힌 것으로 치면 안 된다.
    half_read = _plan(["C1 하나"], ["D1 [C1] 선택지가 깨짐 | default: a | options: a 가; b = 나 | state: answered:b"])
    if not half_read.decisions[0].problems or pc.open_decision_ids(half_read) != ["D1"]:
        problems.append(f"칸이 깨진 answered 결정을 닫힌 것으로 셌다: {pc.open_decision_ids(half_read)}")
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
    if {i.rule for i in pc.lint_errors(everything)} != {"L2", "L6", "L9"}:
        problems.append(f"lint_errors 가 오류 규칙 셋을 다 돌려주지 않는다: {sorted({i.rule for i in pc.lint_errors(everything)})}")
    split_only = pc.parse_plan([f"- {CLAIMS}: C1 하나", "- Proof: p", f"- {CLAIMS}: C2 둘"])
    if not pc.has_error_rules(split_only):
        problems.append("나뉜 묶음(L9)을 오류 규칙 위반으로 보지 않는다 — 쓰기를 막지 못한다")
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
    response_owned = {"parse_response", "qualify", "qualified_archive", "move_exclusive", "publish",
                      "inbox_files", "archive_files", "taken_numbers", "copy_archive"}
    for path in sorted((SOURCE_ROOT / "workflow_kit").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        defined = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        if path.name == "plan_claims.py":
            missing = owned - defined
            if missing:
                problems.append(f"plan_claims 에 없는 함수: {sorted(missing)}")
        elif owned & defined:
            problems.append(f"{path.relative_to(SOURCE_ROOT)} 가 같은 이름을 또 정의한다: {sorted(owned & defined)}")
        # 응답 파일의 형식 · 자격 · 이동도 한 곳이다 (2단계).
        if path.name == "plan_responses.py":
            if response_owned - defined:
                problems.append(f"plan_responses 에 없는 함수: {sorted(response_owned - defined)}")
        elif response_owned & defined:
            problems.append(
                f"{path.relative_to(SOURCE_ROOT)} 가 응답 함수를 또 정의한다: {sorted(response_owned & defined)}")
    # 소비자가 그 모듈을 실제로 부르는가.
    consumers = {
        "tools/backlog_update.py": "plan_claims",
        "tools/plan_status.py": "plan_claims",
        "common/plan_tasks.py": "plan_claims",
        "common/state/builder.py": "plan_tasks",
        "tools/refresh_state.py": "plan_tasks",
        "tools/session_start.py": "plan_tasks",
        "tools/plan_import.py": "plan_claims.compute_states",
        "common/plan_responses.py": "plan_claims.plan_digest",
    }
    response_consumers = {
        "tools/plan_import.py": "plan_responses.qualified_archive",
        "tools/backlog_update.py": "plan_responses.qualified_archive",
        "common/plan_tasks.py": "plan_responses.qualified_archive",
        "tools/plan_status.py": "plan_responses.judge",
        "tools/seed_workspace_memory.py": "plan_responses.copy_archive",
        "common/branch_join.py": "plan_responses.copy_archive",
    }
    for rel, needle in response_consumers.items():
        if needle not in (SOURCE_ROOT / "workflow_kit" / rel).read_text(encoding="utf-8"):
            problems.append(f"{rel} 가 {needle} 를 쓰지 않는다")
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
        current_status="in_progress", removal_note=None, workspace_root=SOURCE_ROOT)
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
    same, dropped = pc.normalize_new_decision(GOOD_DECISION)
    if dropped or same != GOOD_DECISION:
        problems.append(f"`state: proposed` 는 버릴 것이 없다 — 경고할 일이 아니다: dropped={dropped}")
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


def _contract(lines: list[str], previous: list[str] | None, **overrides: object) -> backlog_update.PlanVerdict:
    args: dict[str, object] = dict(
        previous_lines=previous, plan_claim_args=[], plan_decision_args=[], decision_state_args=[],
        replace_fields=set(), requested_status=None, status="in_progress", current_status="in_progress",
        removal_note=None, workspace_root=SOURCE_ROOT)
    args.update(overrides)
    return backlog_update.enforce_plan_contract(list(lines), **args)  # type: ignore[arg-type]


def case_10_whole_corpus_is_untouched() -> None:
    problems: list[str] = []
    repo = SOURCE_ROOT.parent
    files = sorted((repo / "ai-workflow" / "memory").rglob("tasks/TASK-*.md"))
    scanned = with_plan = 0
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        if not pc.parse_plan(lines).empty:
            with_plan += 1      # 주장 · 결정이 있는 파일은 계약의 대상이다 — 이 case 가 재는 것이 아니다.
            continue
        scanned += 1
        for requested in (None, "done"):
            verdict = _contract(lines, lines, requested_status=requested, status="done" if requested else "in_progress")
            if verdict.lines != lines or verdict.error_code:
                problems.append(f"{path.name}: 바뀌었거나 거부됐다 ({verdict.error_code}) requested={requested}")
                break
    if scanned < 100:
        problems.append(f"표본이 너무 적다 — task 파일 {scanned}개 (경로가 바뀌었는가)")
    _record(f"case 10 (호환 전수 — task 파일 {scanned}개 무변화, 주장 있는 파일 {with_plan}개 제외)", problems)


WITH_DECISION = [
    "## 📝 Description", "", "- Completion criteria: [C1] 기준", "",
    "## 🧭 Plan", "", f"- {CLAIMS}: C1 하나를 한다",
    f"- {DECISIONS}: {GOOD_DECISION.replace('state: proposed', 'state: answered:warn')}",
    "- Files that change: a.py", "",
]


def case_11_contract_application() -> None:
    problems: list[str] = []
    decision_at = next(i for i, l in enumerate(WITH_DECISION) if l.startswith(f"- {DECISIONS}:"))

    # 결정 줄을 교체해도 대화의 답은 남는다 (ADR-031 결정 12).
    replaced = list(WITH_DECISION)
    replaced[decision_at] = f"- {DECISIONS}: " + GOOD_DECISION.replace("막는가?", "막을까?")
    verdict = _contract(replaced, WITH_DECISION, plan_decision_args=["x"], replace_fields={pc.DECISIONS_KEY})
    if verdict.error_code or not verdict.lines[decision_at].endswith("| state: answered:warn"):
        problems.append(f"교체로 answered 가 사라졌다: {verdict.error_code} {verdict.lines[decision_at]}")
    if not any("질문이 바뀌었다 — answered 를 유지했다: D1" in w for w in verdict.warnings):
        problems.append(f"answered 유지 경고가 없다: {verdict.warnings}")
    gone = list(WITH_DECISION)
    gone[decision_at] = f"- {DECISIONS}: D1 [C1] 막는가? | default: block | options: block = 거부한다; stop = 멈춘다 | state: proposed"
    verdict = _contract(gone, WITH_DECISION, plan_decision_args=["x"], replace_fields={pc.DECISIONS_KEY})
    if verdict.error_code != "plan_lint_error":
        problems.append(f"답한 값이 새 선택지에 없는데 거부되지 않았다: {verdict.error_code} {verdict.lines[decision_at]}")
    claim_changed = [l.replace("C1 하나를 한다", "C1 하나를 정말 한다") for l in WITH_DECISION]
    verdict = _contract(claim_changed, WITH_DECISION, plan_claim_args=["x"], replace_fields={pc.CLAIMS_KEY})
    if not any("answered 를 유지했다: D1" in w for w in verdict.warnings):
        problems.append(f"주장이 바뀌어 지문이 달라졌는데 알리지 않았다: {verdict.warnings}")

    # 같은 상태를 다시 준 호출은 전이가 아니다 — 경고를 되풀이하지 않는다 (스펙 §3).
    unmeasured = [l for l in WITH_DECISION if "Completion criteria" not in l]
    again = _contract(unmeasured, unmeasured, requested_status="in_progress")
    if any(w.startswith("L7") for w in again.warnings):
        problems.append(f"전이가 아닌데 린트 경고를 되풀이했다: {again.warnings}")
    moved = _contract(unmeasured, unmeasured, requested_status="in_progress", current_status="planned")
    if not any(w.startswith("L7") for w in moved.warnings):
        problems.append(f"전이인데 린트 경고가 없다: {moved.warnings}")

    # 오류 규칙을 어긴 동안에는 칸을 다시 적지 않는다 (스펙 §8.6) — 손으로 적은 kept 가 그대로 남는다.
    broken = [l.replace("state: answered:warn", "state: kept") for l in WITH_DECISION]
    broken.insert(decision_at, f"- {CLAIMS}: C1 같은 ID 를 또 쓴다")
    verdict = _contract(broken, broken)
    if verdict.error_code or verdict.lines != broken:
        problems.append(f"오류 상태 파일의 칸을 다시 적었다: {verdict.error_code}")
    if not any("오류 규칙을 어긴 상태다" in w for w in verdict.warnings):
        problems.append(f"오류 상태를 알리지 않았다: {verdict.warnings}")
    # 통과한 쓰기는 뒷받침 없는 칸을 고치고 알린다.
    hand = [l.replace("state: answered:warn", "state: kept") for l in WITH_DECISION]
    verdict = _contract(hand, hand)
    if not verdict.lines[decision_at].endswith("| state: proposed") or \
            "뒷받침 없는 상태를 되돌렸다: D1 kept → proposed" not in verdict.warnings:
        problems.append(f"뒷받침 없는 칸: {verdict.lines[decision_at]} {verdict.warnings}")

    # 거부 사유가 겹치면 나머지도 싣는다 (스펙 §4).
    both = [l.replace("state: answered:warn", "state: proposed") for l in WITH_DECISION]
    both.insert(decision_at, f"- {CLAIMS}: C1 같은 ID 를 또 쓴다")
    verdict = _contract(both, both, requested_status="done", status="done")
    if verdict.error_code != "plan_lint_error" or not any("열린 결정 1건 (D1)" in w for w in verdict.warnings):
        problems.append(f"겹친 거부 사유: {verdict.error_code} {verdict.warnings}")
    # 경고의 조건 — 넓게 내면 읽히지 않는다.
    quiet = _contract(WITH_DECISION, WITH_DECISION)
    if any("answered 를 유지했다" in w for w in quiet.warnings):
        problems.append(f"계획이 안 바뀌었는데 answered 유지를 알렸다: {quiet.warnings}")
    fresh_before = [l.replace("state: answered:warn", "state: proposed") for l in WITH_DECISION]
    fresh_after = [l.replace("C1 하나를 한다", "C1 하나를 정말 한다") for l in fresh_before]
    fresh = _contract(fresh_after, fresh_before, plan_claim_args=["x"], replace_fields={pc.CLAIMS_KEY},
                      decision_state_args=["D1=answered:warn"])
    if any("answered 를 유지했다" in w for w in fresh.warnings):
        problems.append(f"이번 호출에서 처음 답한 결정을 '유지' 로 알렸다: {fresh.warnings}")
    touched_error = _contract(both, both, plan_claim_args=["x"])
    if touched_error.error_code != "plan_lint_error" or any("도 남아 있다" in w for w in touched_error.warnings):
        problems.append(f"done 이 아닌 거부에 열린 결정 사유를 실었다: {touched_error.warnings}")
    open_plan = [l.replace("state: answered:warn", "state: proposed") for l in WITH_DECISION]
    plain = _contract(open_plan, open_plan)
    if any(w.startswith("열린 결정") for w in plain.warnings):
        problems.append(f"전이가 아닌 쓰기에 열린 결정 경고를 냈다: {plain.warnings}")
    entering = _contract(open_plan, open_plan, requested_status="in_progress", current_status="planned")
    if not any(w.startswith("열린 결정 1건 (D1 proposed)") for w in entering.warnings):
        problems.append(f"→ in_progress 에 열린 결정 경고가 없다: {entering.warnings}")
    # 열린 결정을 없애는 쓰기는 사유가 있어야 한다 — 어떤 길로 없애든.
    no_plan = [l for l in open_plan if not l.startswith((f"- {CLAIMS}:", f"- {DECISIONS}:"))]
    for label, note, expect_refused in (
            ("사유 없음", None, True), ("공백", "   ", True), ("폭 없는 문자", "\u200b\ufeff\u2060", True),
            ("전각 공백", "\u3000", True), ("읽을 수 있는 사유", "소유자와 대화로 확인", False)):
        verdict = _contract(no_plan, open_plan, replace_fields={pc.CLAIMS_KEY, pc.DECISIONS_KEY},
                            removal_note=note, requested_status="done", status="done")
        if (verdict.error_code == "decision_removal_needs_note") != expect_refused:
            problems.append(f"주장 · 결정을 함께 걷기 ({label}): {verdict.error_code}")
    # 같은 ID 로 task 를 다시 만드는 쓰기(교체 표시 없음)도 마찬가지다.
    recreated = _contract(no_plan, open_plan, requested_status="done", status="done")
    if recreated.error_code != "decision_removal_needs_note":
        problems.append(f"교체 표시 없이 열린 결정이 사라졌는데 통과했다: {recreated.error_code}")
    hand_kept = [l.replace("state: proposed", "state: kept") for l in open_plan]
    verdict = _contract(no_plan, hand_kept, replace_fields={pc.DECISIONS_KEY, pc.CLAIMS_KEY})
    if verdict.error_code != "decision_removal_needs_note":
        problems.append(f"손으로 kept 로 적은 열린 결정을 사유 없이 걷었다: {verdict.error_code}")
    # 이미 done 인 task 에 done 을 다시 줘도 게이트는 돈다.
    redone = _contract(open_plan, open_plan, requested_status="done", status="done", current_status="done")
    if redone.error_code != "open_decisions":
        problems.append(f"이미 done 인 task 의 done 재요청이 통과했다: {redone.error_code}")
    # 주장 · 결정을 건드리는 인자는 무엇이든 린트 오류에서 쓰기를 막는다.
    for label, overrides in (
            ("깨진 --plan-decision", dict(plan_decision_args=["x"])),
            ("오류 상태 파일의 --decision-state", dict(decision_state_args=["D1=answered:warn"])),
            ("주장 교체", dict(replace_fields={pc.CLAIMS_KEY}))):
        verdict = _contract(both, both, **overrides)
        if verdict.error_code != "plan_lint_error":
            problems.append(f"{label}: 오류 규칙을 어긴 채 통과했다 ({verdict.error_code})")
        elif not verdict.warnings:
            problems.append(f"{label}: 거부 사유의 목록이 비었다")
    unknown = _contract(LEGACY_LINES, LEGACY_LINES, decision_state_args=["D1=answered:a"])
    if unknown.error_code != "decision_state_rejected":
        problems.append(f"결정이 없는 task 의 --decision-state 가 통과했다: {unknown.error_code}")
    three_files = [*WITH_DECISION[:-1], "- Files that change: b.py", "- Files that change: c.py", ""]
    with_claims = _contract(three_files, None, requested_status="in_progress", status="in_progress", current_status=None)
    if any("Claims 가 없다" in w for w in with_claims.warnings):
        problems.append(f"주장이 있는데 Claims 권고를 냈다: {with_claims.warnings}")
    without_claims = [l for l in three_files if not l.startswith((f"- {CLAIMS}:", f"- {DECISIONS}:"))]
    advised = _contract(without_claims, None, requested_status="in_progress", status="in_progress", current_status=None)
    if not any("Claims 가 없다 — 바뀌는 파일 3개 (R2.3)" in w for w in advised.warnings):
        problems.append(f"파일 셋인데 Claims 권고가 없다: {advised.warnings}")
    unreadable_line = [l.replace("options: block = 거부한다; warn = 경고만 낸다", "options: block 거부한다; warn = 경고") for l in open_plan]
    verdict = _contract(unreadable_line, unreadable_line, decision_state_args=["D1=answered:warn"])
    if verdict.error_code != "decision_state_rejected":
        problems.append(f"읽을 수 없는 결정에 답을 적으려는 호출의 오류 코드: {verdict.error_code}")
    dropped = _contract(open_plan, open_plan, replace_fields={pc.DECISIONS_KEY}, removal_note="불필요")
    if not any("기존 값 1건을 걷었다" in w for w in dropped.warnings):
        problems.append(f"걷은 것을 알리지 않았다: {dropped.warnings}")
    _record("case 11 (계약 적용 — answered 유지 · 경고의 조건 · 오류 상태의 칸 · 겹친 사유 · 사유 없는 제거)", problems)


D = "D1 [C1] 질문 | default: a | options: a = 가; b = 나"
LOC = "workflow-source/workflow_kit/tools/backlog_update.py"
CITE1 = ["[C1] 기준"]

#: (설명, 주장 줄, 결정 줄, 완료 기준, 기대 — 정확히 이 (규칙, 강도, 대상) 들).
#: 대상이 없는 규칙은 "" 이다. `_lines_of` 는 backlog_update.py 를 100줄로 본다.
LINT_TABLE: list[tuple[str, list[str], list[str], list[str], list[tuple[str, str, str]]]] = [
    ("깨끗한 계획", ["C1 하나를 한다"], [D], CITE1, []),
    # L1 — 폭의 경계와 범위.
    ("1단계 5개는 된다", [f"C{n} 주장 {n}" for n in range(1, 6)], [], [f"[C{n}] 기준" for n in range(1, 6)], []),
    ("1단계 6개", [f"C{n} 주장 {n}" for n in range(1, 7)], [], [f"[C{n}] 기준" for n in range(1, 7)], [("L1", "warning", "1단계")]),
    ("자식 5개는 된다", ["C1 부모", *[f"C1.{n} 자식 {n}" for n in range(1, 6)]], [], CITE1, []),
    ("자식 6개", ["C1 부모", *[f"C1.{n} 자식 {n}" for n in range(1, 7)]], [], CITE1, [("L1", "warning", "C1")]),
    # L2 — ID 문법 · 유일 · 부모 · 형제 연속.
    ("1 부터가 아니다", ["C2 하나"], [], ["[C2] 기준"], [("L2", "error", "1단계")]),
    ("부모가 없다", ["C1 하나", "C2.1 부모 없는 둘"], [], CITE1, [("L2", "error", "C2.1")]),
    ("4단계 ID", ["C1 하나", "C1.1.1.1 너무 깊다"], [], CITE1, [("L2", "error", "C1.1.1.1")]),
    ("0 은 양의 정수가 아니다", ["C0 영"], [], [], [("L2", "error", "C0")]),
    ("ID 가 겹친다", ["C1 하나", "C1 둘"], [], CITE1, [("L2", "error", "C1")]),
    ("형제를 건너뛴다", ["C1 하나", "C1.1 @ new: a.py · f()", "C1.3 @ new: b.py · g()"], [], CITE1, [("L2", "error", "C1")]),
    # L3 — 80자 경계, ID 는 세지 않는다, 3단계는 보지 않는다, 위치 꼴 1 · 2단계도 본다.
    ("정확히 80자", ["C1 " + "가" * 80], [], CITE1, []),
    ("81자", ["C1 " + "가" * 81], [], CITE1, [("L3", "warning", "C1")]),
    ("2단계 81자", ["C1 부모", "C1.1 " + "나" * 81], [], CITE1, [("L3", "warning", "C1.1")]),
    ("3단계 위치는 길어도 된다", ["C1 부모", "C1.1 둘", "C1.1.1 @ new: " + "d/" * 60 + "f.py · f()"], [], CITE1, []),
    ("위치 꼴 1단계의 `;`", ["C1 @ new: a/b.py · f(); g()"], [], CITE1, [("L3", "warning", "C1")]),
    # L4 — 1단계만, `/` 경로와 파일명, 백틱.
    ("경로로 시작", ["C1 workflow_kit/tools/x.py 를 고친다"], [], CITE1, [("L4", "warning", "C1")]),
    ("파일명으로 시작", ["C1 backlog_update.py 를 고친다"], [], CITE1, [("L4", "warning", "C1")]),
    ("백틱 친 경로", ["C1 `workflow_kit/x.py` 를 고친다"], [], CITE1, [("L4", "warning", "C1")]),
    ("2단계는 경로로 시작해도 된다", ["C1 부모", "C1.1 workflow_kit/x.py 가 읽는다"], [], CITE1, []),
    # L5 — 줄 범위.
    ("범위가 파일 안", ["C1 a", "C1.1 b", "C1.1.1 @ workflow-source/workflow_kit/tools/backlog_update.py:1-100 · f()"], [], CITE1, []),
    ("끝이 한 줄 넘는다", ["C1 a", "C1.1 b", "C1.1.1 @ workflow-source/workflow_kit/tools/backlog_update.py:1-101 · f()"], [], CITE1, [("L5", "warning", "C1.1.1")]),
    ("0 번 줄", ["C1 a", "C1.1 b", "C1.1.1 @ workflow-source/workflow_kit/tools/backlog_update.py:0 · f()"], [], CITE1, [("L5", "warning", "C1.1.1")]),
    ("거꾸로 된 범위", ["C1 a", "C1.1 b", "C1.1.1 @ workflow-source/workflow_kit/tools/backlog_update.py:5-3 · f()"], [], CITE1, [("L5", "warning", "C1.1.1")]),
    ("3단계가 문장", ["C1 a", "C1.1 b", "C1.1.1 위치가 아닌 문장"], [], CITE1, [("L5", "warning", "C1.1.1")]),
    # L6 — 결정.
    ("결정 5개는 된다", ["C1 하나"], [f"D{n} [C1] 질문 {n} | default: a | options: a = 가; b = 나" for n in range(1, 6)], CITE1, []),
    ("결정 6개", ["C1 하나"], [f"D{n} [C1] 질문 {n} | default: a | options: a = 가; b = 나" for n in range(1, 7)], CITE1, [("L6", "error", "")]),
    ("결정 ID 가 겹친다", ["C1 하나"], [D, D], CITE1, [("L6", "error", "D1")]),
    ("모르는 칸", ["C1 하나"], [D + " | 참고: 메모"], CITE1, [("L6", "error", "D1")]),
    ("`=` 없는 선택지", ["C1 하나"], ["D1 [C1] 질문 | default: a | options: a; b"], CITE1, [("L6", "error", "D1")] * 2),
    ("값 없는 answered", ["C1 하나"], [D + " | state: answered"], CITE1, [("L6", "error", "D1")]),
    ("모르는 상태 종류", ["C1 하나"], [D + " | state: approved:a"], CITE1, [("L6", "error", "D1")]),
    ("값에 대문자", ["C1 하나"], ["D1 [C1] 질문 | default: a | options: a = 가; Bb = 나"], CITE1, [("L6", "error", "D1")]),
    ("값 32자는 된다", ["C1 하나"], [f"D1 [C1] 질문 | default: a | options: a = 가; {'b' * 32} = 나"], CITE1, []),
    ("값 33자", ["C1 하나"], [f"D1 [C1] 질문 | default: a | options: a = 가; {'b' * 33} = 나"], CITE1, [("L6", "error", "D1")]),
    ("가리키는 주장이 없다", ["C1 하나"], ["D1 [C9] 질문 | default: a | options: a = 가; b = 나"], CITE1, [("L6", "error", "D1")]),
    ("상태의 값이 선택지 밖", ["C1 하나"], [D + " | state: changed:z"], CITE1, [("L6", "error", "D1")]),
    # 문법 (스펙 §2.2 · §2.3 · §2.4).
    ("값에 밑줄 · 하이픈 · 숫자", ["C1 하나"], ["D1 [C1] 질문 | default: a_1 | options: a_1 = 가; b-2 = 나; 3 = 다"], CITE1, []),
    ("빈 default 값", ["C1 하나"], ["D1 [C1] 질문 | default:  | options: a = 가; b = 나"], CITE1, [("L6", "error", "D1")]),
    ("질문이 없다", ["C1 하나"], ["D1 [C1] | default: a | options: a = 가; b = 나"], CITE1, [("L6", "error", "D1")]),
    ("주장을 대괄호 없이", ["C1 하나"], ["D1 C1 질문 | default: a | options: a = 가; b = 나"], CITE1, [("L6", "error", "D1")]),
    ("ID 뒤에 공백이 없다", ["C1하나"], [], [], [("L2", "error", "C1하나")]),
    ("`·` 없는 위치", ["C1 a", "C1.1 b", f"C1.1.1 @ {LOC}:1 f()"], [], CITE1, [("L5", "warning", "C1.1.1")]),
    ("`@ new:` 뒤에 공백이 없다", ["C1 a", "C1.1 b", "C1.1.1 @ new:a.py · f()"], [], CITE1, [("L5", "warning", "C1.1.1")]),
    ("unopened 는 읽힌다", ["C1 하나"], [D + " | state: unopened"], CITE1, []),
    ("disputed 는 읽힌다", ["C1 하나"], [D + " | state: disputed"], CITE1, []),
    ("changed:<값> 은 읽힌다", ["C1 하나"], [D + " | state: changed:b"], CITE1, []),
    ("kept 에는 값이 없다", ["C1 하나"], [D + " | state: kept:a"], CITE1, [("L6", "error", "D1")]),
    ("공백 없는 `;`", ["C1 하나를 한다;둘을 한다"], [], CITE1, [("L3", "warning", "C1")]),
    ("80 code point (UTF-16 으로는 160)", ["C1 " + "\U0001F600" * 80], [], CITE1, []),
    ("한 줄 위치 — 마지막 줄", ["C1 a", "C1.1 b", f"C1.1.1 @ {LOC}:100 · f()"], [], CITE1, []),
    ("한 줄 위치 — 한 줄 넘음", ["C1 a", "C1.1 b", f"C1.1.1 @ {LOC}:101 · f()"], [], CITE1, [("L5", "warning", "C1.1.1")]),
    ("결정이 없는 후손을 가리킨다", ["C1 하나"], ["D1 [C1.1] 질문 | default: a | options: a = 가; b = 나"], CITE1, [("L6", "error", "D1")]),
    ("닫는 대괄호 없는 인용", ["C1 하나"], [], ["[C1 기준"], [("L7", "warning", "C1")]),
    ("결정 ID 는 인용이 아니다", ["C1 하나"], [], ["[D1] 기준"], [("L7", "warning", "C1")]),
    ("줄 머리가 아닌 인용", ["C1 하나"], [], ["기준 [C1]"], [("L7", "warning", "C1")]),
    ("한 자리 퍼센트", ["C1 구현을 5% 했다"], [], CITE1, [("L8", "warning", "C1")]),
    ("3단계의 상태 표현", ["C1 a", "C1.1 b", "C1.1.1 @ new: a.py · f() 완료"], [], CITE1, [("L8", "warning", "C1.1.1")]),
    ("주장이 없으면 인용도 보지 않는다", [], [], ["[C9] 없는 주장"], []),
    ("빈 선택지 값", ["C1 하나"], ["D1 [C1] 질문 | default: a | options: a = 가; = 나"], CITE1, [("L6", "error", "D1")]),
    ("둘째 단계의 0", ["C1 a", "C1.0 b"], [], CITE1, [("L2", "error", "C1.0")]),
    ("셋째 단계의 0", ["C1 a", "C1.1 b", "C1.1.0 @ new: a.py · f()"], [], CITE1, [("L2", "error", "C1.1.0")]),
    ("부모가 다 있어도 4단계는 안 된다", ["C1 a", "C1.1 b", "C1.1.1 @ new: a.py · f()", "C1.1.1.1 깊다"], [], CITE1, [("L2", "error", "C1.1.1.1")]),
    ("결정 번호 0", ["C1 하나"], ["D0 [C1] 질문 | default: a | options: a = 가; b = 나"], CITE1, [("L6", "error", "D0")]),
    ("선택지가 하나", ["C1 하나"], ["D1 [C1] 질문 | default: a | options: a = 가"], CITE1, [("L6", "error", "D1")]),
    ("기본값이 선택지 밖", ["C1 하나"], ["D1 [C1] 질문 | default: z | options: a = 가; b = 나"], CITE1, [("L6", "error", "D1")]),
    ("2단계의 위치도 줄 범위를 본다", ["C1 a", f"C1.1 @ {LOC}:101 · f()"], [], CITE1, [("L5", "warning", "C1.1")]),
    # L7 · L10 — 인용.
    ("없는 후손을 인용", ["C1 하나"], [], ["[C1.9] 없는 주장"], [("L10", "warning", ""), ("L7", "warning", "C1")]),
    ("후손 인용은 조상을 잰다", ["C1 a", "C1.1 b"], [], ["[C1.1] 후손"], []),
    # L8 — 모든 단계, 공백 낀 %.
    ("공백 낀 퍼센트", ["C1 구현을 80 % 했다"], [], CITE1, [("L8", "warning", "C1")]),
    ("2단계의 상태 표현", ["C1 부모", "C1.1 파서 작성 완료"], [], CITE1, [("L8", "warning", "C1.1")]),
]


def case_12_lint_table() -> None:
    problems: list[str] = []
    for label, claims, decisions, criteria, expected in LINT_TABLE:
        issues = pc.lint_plan(pc.parse_plan_values(claims, decisions), criteria=criteria, file_line_count=_lines_of)
        got = sorted((i.rule, i.severity, i.ref) for i in issues)
        if got != sorted(expected):
            problems.append(f"{label}: 기대 {sorted(expected)} · 실제 {got}")
    # L9 는 줄 배치가 입력이다 — 결정 묶음이 나뉜 경우도 오류다.
    split_decisions = pc.parse_plan([
        f"- {CLAIMS}: C1 하나를 한다", f"- {DECISIONS}: {D}", "- Proof: p",
        f"- {DECISIONS}: D2 [C1] 질문 둘 | default: a | options: a = 가; b = 나"])
    got = sorted((i.rule, i.severity) for i in pc.lint_plan(split_decisions, criteria=CITE1, file_line_count=_lines_of))
    if got != [("L9", "error")]:
        problems.append(f"나뉜 Decisions 묶음: {got}")
    # 위치가 없으면 git 밖이어도 남길 말이 없다.
    nothing = pc.lint_plan(pc.parse_plan_values(["C1 하나를 한다"], []), criteria=CITE1, file_line_count=None)
    if nothing:
        problems.append(f"위치가 없는데 git 밖 보고를 냈다: {[i.render() for i in nothing]}")
    # git 밖에서는 L5 를 건너뛰고 그 사실을 남긴다 — 통과로 세지 않는다.
    located = pc.parse_plan_values(["C1 a", "C1.1 b", "C1.1.1 @ a.py:1 · f()"], [])
    got = [(i.rule, i.severity) for i in pc.lint_plan(located, criteria=CITE1, file_line_count=None)]
    if got != [("L5", "note")]:
        problems.append(f"git 밖의 L5: {got}")
    _record(f"case 12 (린트 표 — {len(LINT_TABLE)} 입력의 규칙 · 강도 · 대상 전부 대조)", problems)


def case_13_digest_body() -> None:
    import hashlib

    problems: list[str] = []
    plan = pc.parse_plan([
        "- 주장: C1 하나를 한다   ",
        "- Claims: C1.1 @ new: a.py · f()",
        "- 결정: D1 [C1] 막는가? | 선택: block = 거부한다; warn = 경고만 낸다 | 기본:  block  | 상태: kept",
    ])
    body = "\n".join([
        "- Claims: C1 하나를 한다",
        "- Claims: C1.1 @ new: a.py · f()",
        "- Decisions: D1 [C1] 막는가? | default: block | options: block = 거부한다; warn = 경고만 낸다",
    ])
    expected = "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()
    if pc.plan_digest(plan) != expected:
        problems.append("지문이 스펙 §5 의 본문(정본 라벨 · 정본 칸 이름 · default → options 순서 · 상태 칸 없음 · 줄 끝 공백 없음)의 sha256 과 다르다")
    # 파일 순서 그대로다 — 정렬하지 않는다.
    reordered = pc.parse_plan(["- Claims: C2 둘을 한다", "- Claims: C1 하나를 한다"])
    body = "- Claims: C2 둘을 한다\n- Claims: C1 하나를 한다"
    if pc.plan_digest(reordered) != "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest():
        problems.append("지문이 파일 순서를 지키지 않는다")
    # 읽을 수 없는 결정 줄은 원문 그대로다 — 반쯤 읽은 줄을 정본 표기로 다시 쓰지 않는다.
    raw = "D1 [C1] 막는가? | 기본: block | 선택: block 거부한다; warn = 경고 | 상태: kept"
    broken = pc.parse_plan(["- Claims: C1 하나를 한다", f"- Decisions: {raw}"])
    body = f"- Claims: C1 하나를 한다\n- Decisions: {raw}"
    if pc.plan_digest(broken) != "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest():
        problems.append("읽을 수 없는 결정 줄의 지문이 원문이 아니다")
    # 머리(ID · 인용)를 못 읽는 줄도 마찬가지다.
    raw = "D1 C1 막는가?  | 기본: block | 선택: block = 거부한다; warn = 경고만 낸다"
    headless = pc.parse_plan(["- Claims: C1 하나를 한다", f"- 결정: {raw}"])
    body = f"- Claims: C1 하나를 한다\n- Decisions: {raw}"
    if pc.plan_digest(headless) != "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest():
        problems.append("머리를 못 읽는 결정 줄의 지문이 원문이 아니다")
    _record("case 13 (지문의 본문 — 스펙 §5 문면대로)", problems)


def case_14_open_states() -> None:
    problems: list[str] = []
    if set(pc.OPEN_STATES) != {"proposed", "unopened", "disputed"}:
        problems.append(f"열린 상태 집합: {pc.OPEN_STATES}")
    verdicts = {s: pc.state_is_open(s) for s in ("proposed", "unopened", "disputed", "kept", "changed:x", "answered:x")}
    if verdicts != {"proposed": True, "unopened": True, "disputed": True, "kept": False, "changed:x": False, "answered:x": False}:
        problems.append(f"열린 상태 판정: {verdicts}")
    columns = pc.parse_plan_values(["C1 하나"], [
        "D1 [C1] 가 | default: a | options: a = 가; b = 나 | state: unopened",
        "D2 [C1] 나 | default: a | options: a = 가; b = 나 | state: disputed",
        "D3 [C1] 다 | default: a | options: a = 가; b = 나 | state: kept",
        "D4 [C1] 라 | default: a | options: a 가; b = 나 | state: answered:b",
    ])
    if pc.column_open_decision_ids(columns) != ["D1", "D2", "D4"]:
        problems.append(f"칸 기준 열린 결정: {pc.column_open_decision_ids(columns)}")
    _record("case 14 (열린 상태 — 셋만 열려 있고, 못 읽는 결정은 열린 것으로 센다)", problems)


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
    case_10_whole_corpus_is_untouched,
    case_11_contract_application,
    case_12_lint_table,
    case_13_digest_body,
    case_14_open_states,
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
