"""graph_insights 지표의 네 결함을 고정하는 판정 (TASK-2026-09-07-main-010 · -09-21-main-001).

수리한 결함이 되살아나는 것을 막는다. 넷 다 *실측으로* 확인된 것이다:

1. **점수가 일한 것을 벌했다.** 옛 산식
   `100 - uncovered*15 - scope_creep*10 + min(surprising*5, 25)` 은 벌점이 항목
   수에 비례해 무한히 커지는데 보너스는 25 에서 막혀 있어, goal 매칭 0 을 고정하고
   재면 0건 40 → 3건 25 → 10건 -35(0 으로 clamp) 였다. 표준이 recently-done 을
   10건으로 상한하므로 활발한 저장소는 영구히 바닥에 눌렸고, 그 0 은 '나쁘다' 가
   아니라 **clamp 자국**이었다.
2. **정반대 술어가 같은 경고 접두사를 썼다.** `purpose_context` 는 제외 영역에
   *걸리면* scope creep 이라 하고, `purpose_graph` 는 *안 걸리면* 그렇다 했는데,
   둘 다 `"scope creep 의심:"` 으로 시작하면서 `scope_creep_warnings` 라는 같은
   이름의 두 필드로 나갔다 — 읽는 쪽이 어느 규칙이 울렸는지 구분할 수 없었다.
3. **좋은 점수를 내는 유일한 fixture 가 항등식을 쟀다.** goal 문자열을
   deliverable 문자열에 그대로 복사해 두어 coverage 100% 가 나왔다. 실제 작업
   제목은 goal 의 재진술이 아니므로 그 case 는 아무것도 재지 않았다.

4. **판정이 애초에 어휘를 재고 있었다.** Goal 산문과 완료 task 제목의 표면 어휘
   겹침이 실물에서 **정확히 0** 이었고(4개 goal 전부), 조사 제거·CJK bigram 두
   대안 토크나이저로 다시 재도 최대 0.07 — 그 유일한 겹침은 기능어 `처럼` 이었다.
   분류 축도 같은 결함을 공유해, 미분류를 면한 2건의 근거가 전부 동음이의
   (`runtime` / `흡수`)였다. 즉 coverage 축은 상수 0 이고 분류 축은 잡음이었다.
   `task.wbs → milestone.goals → PURPOSE §1` **선언 사슬**로 갈아탔다.
   3번의 가드가 이것을 못 막은 이유도 여기 있다 — 문자열 완전일치만 보던 가드는
   `G1: 표준 워크플로우` 를 통째로 품은 deliverable 을 통과시켰다.

이 넷은 사람이 grep 으로 지키지 못한다 — 사본이 남으면 조용히 되살아난다.
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/check_graph_insights_v0_11_1.py",
    "workflow-source/tests/check_graph_insights_skill_integration_v0_11_2.py",
    "workflow-source/tests/_goal_coverage_fixture.py",
)

#: 이 검사가 강제하는 정본 요구 (spec `core/test_impact_tiering_spec.md` §7).
ENFORCES = (
    "goal-coverage-derives-from-declaration",
    "leaf-goal-declaration-wins-over-milestone",
    "undeclared-coverage-is-unmeasured-not-poor",
)

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
_TESTS_DIR = str(Path(__file__).resolve().parent)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from workflow_kit.common.check_warnings import call_deprecated  # noqa: E402

#: 어휘 판정을 **시험 대상으로** 부르는 함수들 (deprecated). 이들을 부르는
#: 시험은 fixture 어휘가 겹쳐야 의미가 있으므로 항등 가드에서 면제한다.
#: 면제 근거가 코드 호출이므로 함수가 사라지면 면제도 같이 사라진다.
#: 함수를 **인자로** 받아 대신 부르는 래퍼. 호출 그래프 파생이 이것을 모르면
#: 감싼 호출이 목록에서 사라진다 (TASK-2026-09-21-main-007).
_CALL_INDIRECTIONS = frozenset({"call_deprecated"})

_LEXICAL_FUNCTIONS = frozenset({"compute_goal_coverage", "find_surprising_deliverables", "find_gaps"})

#: fixture 의 deliverable 이 goal 어휘를 이 비율 이상 포함하면 항등함수다.
#: 실물 실측값은 0.00 이고 옛 항등 fixture 는 1.00 이었다 — 그 사이를 넉넉히 가른다.
_IDENTITY_OVERLAP_MAX = 0.5


def test_score_never_falls_as_work_is_done() -> None:
    """case 1: 비율이 같으면 항목 수는 점수를 못 움직인다 + 매칭된 일은 점수를 못 내린다."""
    from workflow_kit.common.purpose_graph import (
        GoalCoverageResult,
        SurprisingResult,
        compute_health_score,
    )

    def score(total_goals: int, covered: int, unclassified: int, total_items: int) -> int:
        cov = GoalCoverageResult(
            total_goals=total_goals,
            covered_count=covered,
            partial_count=0,
            uncovered_count=total_goals - covered,
            coverage_pct=round(100.0 * covered / total_goals, 2),
        )
        sur = SurprisingResult(
            surprising=["x"] * unclassified,
            is_scope_creep=[True] * unclassified,
            scope_creep_warnings=[],
            total_items=total_items,
        )
        return compute_health_score(cov, sur, None).score

    # (a) 비율 고정 + 규모만 확대 → 점수 불변
    for covered, total_goals in ((0, 4), (2, 4), (4, 4)):
        for uncl_ratio in (0.0, 0.5, 1.0):
            base = None
            for scale in (1, 2, 3, 5, 10, 30):
                items = 2 * scale
                s = score(total_goals, covered, int(items * uncl_ratio), items)
                if base is None:
                    base = s
                assert s == base, (
                    f"규모만 늘렸는데 점수가 움직였다: goals={covered}/{total_goals} "
                    f"미분류비율={uncl_ratio} scale={scale} {base} -> {s}"
                )
    print("  (a) 비율 고정 시 규모 1~30배에서 점수 불변: PASS")

    # (b) 분류된 deliverable 을 **추가**하는 것은 점수를 절대 내리지 않는다.
    #     옛 산식이 죽은 자리가 정확히 여기다.
    for total_goals in (1, 3, 5):
        for covered in range(total_goals + 1):
            prev = None
            for extra in range(0, 11):
                # 미분류 수는 그대로 2, 분류된 항목만 extra 만큼 늘린다
                s = score(total_goals, covered, 2, 2 + extra)
                if prev is not None:
                    assert s >= prev, (
                        f"분류된 일을 더 했는데 점수가 내려갔다: "
                        f"goals={covered}/{total_goals} extra={extra} {prev} -> {s}"
                    )
                prev = s
    print("  (b) 분류된 일을 추가할수록 점수가 내려가지 않는다: PASS")

    # (c) clamp 에 닿는 입력이 없어야 한다 — 0 이 '바닥에 눌린 자국' 이면 안 된다.
    for total_goals in (1, 3, 5, 10):
        for covered in range(total_goals + 1):
            for items in (1, 4, 10, 30):
                for uncl in range(items + 1):
                    s = score(total_goals, covered, uncl, items)
                    assert 0 <= s <= 100, s
                    if covered == 0 and uncl == items:
                        assert s == 0, f"최악 입력이 0 이 아니다: {s}"
                    if covered == total_goals and uncl == 0:
                        assert s == 100, f"최선 입력이 100 이 아니다: {s}"
    print("  (c) 최악=0 / 최선=100 이고 clamp 자국이 없다: PASS")


def test_two_opposite_rules_do_not_share_a_prefix() -> None:
    """case 2: 정반대 술어의 두 경고가 같은 접두사를 쓰지 않는다."""
    from workflow_kit.common.purpose_graph import (
        UNCLASSIFIED_WARNING_PREFIX,
        GoalKeyword,
        RecentDoneItem,
        find_surprising_deliverables,
    )
    from workflow_kit.common.purpose_context import check_scope_creep

    # purpose_context 쪽: 제외 영역에 **걸려서** 우는 경고
    ctx_warnings = check_scope_creep(
        task_brief="llm model fine-tuning pipeline 을 추가한다",
        affected_documents=[],
        scope={"excluded": ["LLM model fine-tuning / training pipeline"]},
    )
    assert ctx_warnings, "제외 영역 매칭이 경고를 못 냈다 — 이 case 의 전제가 깨졌다"

    # purpose_graph 쪽: goal 에도 제외 영역에도 **안 걸려서** 우는 경고
    graph_result = call_deprecated(
        find_surprising_deliverables,
        goal_keywords=[GoalKeyword(gid="G1", text="G1: 표준 워크플로우", keywords=["표준", "워크플로우"])],
        recent_items=[RecentDoneItem(version="TASK-2026-01-01-main-001", commit_hash="",
                                     summary="전혀 다른 낱말", keywords=["전혀", "다른", "낱말"])],
        scope_excluded=["결제 도메인"],
    )
    assert graph_result.scope_creep_warnings, "미분류 경고가 안 났다 — 이 case 의 전제가 깨졌다"

    for cw in ctx_warnings:
        for gw in graph_result.scope_creep_warnings:
            assert not cw.startswith(gw[:8]) and not gw.startswith(cw[:8]), (
                "정반대 술어의 두 경고가 접두사를 공유한다 — 읽는 쪽이 구분할 수 없다:\n"
                f"  purpose_context: {cw}\n  purpose_graph  : {gw}"
            )
    assert all(g.startswith(UNCLASSIFIED_WARNING_PREFIX) for g in graph_result.scope_creep_warnings)
    assert not any(c.startswith(UNCLASSIFIED_WARNING_PREFIX) for c in ctx_warnings)
    print(f"  두 접두사 분리 확인 ({UNCLASSIFIED_WARNING_PREFIX!r} vs 'scope creep 의심:'): PASS")


_GOAL_LITERAL = re.compile(r"\*\*(G\d+)\*\*:\s*([^\\\"\n]+?)(?:\\n|\")")
_DONE_LITERAL = re.compile(r"\"TASK-\d{4}-\d{2}-\d{2}-[A-Za-z0-9._-]+?-\d{3}\s*[—–-]\s*([^\"]+)\"")


def _functions_with_calls(text: str) -> list[tuple[str, set[str]]]:
    """모듈의 각 함수를 (원문, 그 안에서 호출한 이름 집합) 으로.

    호출 이름은 `f(...)` 와 `mod.f(...)` 둘 다 잡는다.

    **간접 호출도 호출이다** (TASK-2026-09-21-main-007). `call_deprecated(fn, ...)`
    처럼 함수를 *인자로* 넘기는 래퍼를 모르면 `fn` 이 호출 목록에서 사라지고, 이
    파생에 기대던 면제가 **조용히 풀린다** — 실제로 그렇게 됐고 이 판정이 잡았다.
    래퍼를 새로 만들면 여기도 같이 가르쳐야 한다.
    """
    import ast

    tree = ast.parse(text)
    lines = text.splitlines()
    out: list[tuple[str, set[str]]] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        src = "\n".join(lines[node.lineno - 1:node.end_lineno])
        names: set[str] = set()
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                func = sub.func
                if isinstance(func, ast.Name):
                    names.add(func.id)
                    if func.id in _CALL_INDIRECTIONS and sub.args:
                        # 첫 인자가 실제로 불리는 함수다.
                        target = sub.args[0]
                        if isinstance(target, ast.Name):
                            names.add(target.id)
                        elif isinstance(target, ast.Attribute):
                            names.add(target.attr)
                elif isinstance(func, ast.Attribute):
                    names.add(func.attr)
        out.append((src, names))
    return out


def test_fixtures_do_not_measure_the_identity_function() -> None:
    """case 3: fixture 가 goal 어휘를 deliverable 로 복사하지 않는다.

    **완전일치만 막던 옛 가드는 무력했다** (TASK-2026-09-21-main-001).
    `G1: 표준 워크플로우` ↔ `표준 워크플로우 패키지의 배포 경로를 정리했다` 는
    `d != g` 를 통과하면서 goal 어휘를 100% 포함해 coverage 100 을 만들었다.
    막으려던 성질은 문자열 동일성이 아니라 **어휘 겹침**이므로 그것을 잰다.
    """
    from _goal_coverage_fixture import assert_fixture_resembles_reality
    from workflow_kit.common.purpose_graph import _tokenize

    targets = [
        SOURCE_ROOT / "tests" / "check_graph_insights_v0_11_1.py",
        SOURCE_ROOT / "tests" / "check_graph_insights_skill_integration_v0_11_2.py",
    ]
    checked = 0
    scanned_functions = 0
    for path in targets:
        assert path.exists(), path
        text = path.read_text(encoding="utf-8")
        assert _GOAL_LITERAL.search(text), f"{path.name}: goal 리터럴을 못 찾았다 — 전제가 깨졌다"
        assert _DONE_LITERAL.search(text), f"{path.name}: TASK- deliverable 리터럴을 못 찾았다"

        # **어느 fixture 를 면제하는가는 손 목록이 아니라 코드에서 파생한다.**
        # deprecated 어휘 함수를 직접 부르는 시험은 겹침이 설계상 필요하다
        # (그 함수가 어휘를 재는 것이 시험 대상이다). 선언 경로로 흐르는 fixture 만 본다.
        for func_src, calls in _functions_with_calls(text):
            if calls & _LEXICAL_FUNCTIONS:
                continue
            scanned_functions += 1
            goals = {m.group(2).strip() for m in _GOAL_LITERAL.finditer(func_src)}
            dones = {m.group(1).strip() for m in _DONE_LITERAL.finditer(func_src)}
            for d in dones:
                done_tokens = set(_tokenize(d))
                for g in goals:
                    goal_tokens = set(_tokenize(g))
                    if not goal_tokens:
                        continue
                    ratio = len(goal_tokens & done_tokens) / len(goal_tokens)
                    assert ratio < _IDENTITY_OVERLAP_MAX, (
                        f"{path.name}: deliverable 이 goal 어휘를 {ratio:.0%} 포함한다 "
                        f"(상한 {_IDENTITY_OVERLAP_MAX:.0%}) — 항등함수를 잰다.\n"
                        f"  goal: {g!r}\n  done: {d!r}"
                    )
            checked += len(dones)
    assert scanned_functions, "면제가 전부를 먹었다 — 이 판정이 아무것도 안 본다"

    # 선언 경로 fixture 자신도 같은 성질을 지켜야 한다. 여기가 정본이고 위는 잔재 검사다.
    goal_count, done_count = assert_fixture_resembles_reality()
    print(
        f"  fixture deliverable {checked}개 어휘 겹침 < {_IDENTITY_OVERLAP_MAX:.0%}"
        f" + 선언 fixture(goal {goal_count} / done {done_count}) 겹침 0: PASS"
    )


def test_coverage_comes_from_declarations_not_vocabulary() -> None:
    """case 5: coverage 는 선언 사슬에서 나온다 — 어휘가 0% 겹쳐도 닿는다.

    옛 판정이 무엇을 재고 있었는지는 `compute_health_score` docstring 이 적는다.
    여기서는 **두 방향**을 고정한다:

    - 어휘 겹침 0 인데 선언이 있으면 → 닿는다 (어휘를 안 읽는다는 증거)
    - 선언만 지우면 → `undeclared` / `unmeasured` (못 잰 것을 나쁨으로 세지 않는다)
    """
    import tempfile

    import _goal_coverage_fixture as fixture
    from workflow_kit.common.purpose_graph import (
        COVERAGE_MODE_DECLARED,
        COVERAGE_MODE_UNDECLARED,
        TIER_UNMEASURED,
        run_graph_insights,
    )

    fixture.assert_fixture_resembles_reality()

    with tempfile.TemporaryDirectory() as tmp:
        ws = fixture.build_workspace(Path(tmp))
        result = run_graph_insights(workspace_root=ws)
        assert result.coverage is not None
        assert result.coverage.mode == COVERAGE_MODE_DECLARED, result.coverage.mode
        assert result.coverage.coverage_pct == 100.0, result.coverage
        assert result.surprising is not None and not result.surprising.surprising, (
            "선언이 다 붙은 fixture 에서 미분류가 나오면 분류 축이 선언을 안 읽는 것이다"
        )
        print("  어휘 겹침 0 + 선언 → coverage 100 · 미분류 0: PASS")

    with tempfile.TemporaryDirectory() as tmp:
        ws = fixture.build_workspace(Path(tmp), omit_goals=True)
        result = run_graph_insights(workspace_root=ws)
        assert result.coverage is not None
        assert result.coverage.mode == COVERAGE_MODE_UNDECLARED, result.coverage.mode
        assert result.health is not None and result.health.tier == TIER_UNMEASURED, result.health
        assert result.coverage.provenance, "못 쟀으면 사유를 내놓아야 한다 (조용한 0 금지)"
        print("  선언 제거 → undeclared · unmeasured · 사유 보고: PASS")


def test_leaf_declaration_wins_over_milestone() -> None:
    """case 6: leaf 선언이 마일스톤 선언을 이긴다.

    상설 마일스톤은 leaf 마다 섬기는 goal 이 갈린다 — 실측에서 최근 완료 10건이
    **전부** 한 마일스톤(M-007)이었으므로, 마일스톤 단위로만 선언하면 coverage 가
    다시 상수가 된다. 옛 결함이 '항상 0' 이었던 자리를 '항상 같은 값' 으로
    바꾸는 것은 수리가 아니다.
    """
    import tempfile

    import _goal_coverage_fixture as fixture
    from workflow_kit.common.state.roadmap import resolve_task_goals

    with tempfile.TemporaryDirectory() as tmp:
        ws = fixture.build_workspace(Path(tmp))
        resolution = resolve_task_goals(ws)
        # M-100 은 `goals: []` 이고 leaf 로만 선언한다 — 그래도 닿아야 한다.
        reached = resolution.goals_by_task
        expected = {
            "TASK-2026-01-01-main-002": ["G1"],   # M-100/WBS-100.1 (leaf 선언)
            "TASK-2026-01-01-main-001": ["G2"],   # M-100/WBS-100.2 (같은 마일스톤, 다른 goal)
            "TASK-2026-01-01-main-003": ["G2"],
            "TASK-2026-01-02-main-004": ["G3"],   # M-101 은 leaf 선언이 없어 마일스톤 상속
        }
        for task_id, goals in expected.items():
            # `.get` 으로 읽는다 — leaf 우선이 빠지면 키 자체가 사라지고,
            # 그때 KeyError 로 죽으면 판정이 아니라 사고가 된다.
            assert reached.get(task_id) == goals, (
                f"{task_id}: 기대 {goals}, 실제 {reached.get(task_id)!r} — "
                f"leaf 선언 우선이 깨졌다. 전체: {reached}"
            )
        assert not resolution.milestones_without_goals, resolution.milestones_without_goals
    print("  leaf 선언 우선 + 미선언 leaf 는 마일스톤 상속: PASS")


def test_current_task_format_is_parsed_without_id_noise() -> None:
    """case 4: 살아 있는 `TASK-` 형식을 인식하고 ID 토큰을 본문에 섞지 않는다."""
    import json
    import tempfile
    from workflow_kit.common.purpose_graph import parse_recent_done_items

    with tempfile.TemporaryDirectory() as tmp:
        sp = Path(tmp) / "state.json"
        sp.write_text(json.dumps({"session": {"recent_done_items": [
            "TASK-2026-09-07-main-008 — v1.9.3 발행 + 이 호스트 소비자 채널 재적용",
            "TASK-2026-09-07-feature.x-001 — 브랜치 해석 수리",
            "v0.1.0 (aaaaaaa): legacy 형식도 계속 받는다",
        ]}}, ensure_ascii=False), encoding="utf-8")
        items = parse_recent_done_items(sp)

    assert len(items) == 3, items
    assert items[0].version == "TASK-2026-09-07-main-008", items[0].version
    assert items[1].version == "TASK-2026-09-07-feature.x-001", items[1].version
    assert items[2].version == "v0.1.0", items[2].version

    # ID 는 모든 항목이 공유하므로 본문에 섞이면 순수한 잡음이 된다.
    noise = {"task", "2026", "09", "07", "main", "008", "001"}
    for it in items[:2]:
        leaked = noise & set(it.keywords)
        assert not leaked, f"ID 토큰이 키워드에 샜다: {sorted(leaked)} in {it.keywords}"
    assert "발행" in items[0].keywords, items[0].keywords
    print("  TASK- 형식 인식 + ID 토큰 누출 0 (legacy 병행): PASS")


def main() -> int:
    tests = [
        test_score_never_falls_as_work_is_done,
        test_two_opposite_rules_do_not_share_a_prefix,
        test_fixtures_do_not_measure_the_identity_function,
        test_current_task_format_is_parsed_without_id_noise,
        test_coverage_comes_from_declarations_not_vocabulary,
        test_leaf_declaration_wins_over_milestone,
    ]
    passed = 0
    for t in tests:
        print(f"[{t.__name__}]")
        try:
            t()
            passed += 1
            print(f"  ✓ {t.__name__} PASS\n")
        except AssertionError as exc:
            print(f"  ✗ {t.__name__} FAIL: {exc}\n")
    print(f"=== Result: {passed}/{len(tests)} PASS ===")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
