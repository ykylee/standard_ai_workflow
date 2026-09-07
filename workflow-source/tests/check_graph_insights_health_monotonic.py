"""graph_insights 지표의 세 결함을 고정하는 판정 (TASK-2026-09-07-main-010).

수리한 결함이 되살아나는 것을 막는다. 셋 다 *실측으로* 확인된 것이다:

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

이 셋은 사람이 grep 으로 지키지 못한다 — 사본이 남으면 조용히 되살아난다.
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/check_graph_insights_v0_11_1.py",
    "workflow-source/tests/check_graph_insights_skill_integration_v0_11_2.py",
)

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))


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
    graph_result = find_surprising_deliverables(
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


def test_fixtures_do_not_measure_the_identity_function() -> None:
    """case 3: fixture 가 goal 문자열을 deliverable 로 복사하지 않는다."""
    targets = [
        SOURCE_ROOT / "tests" / "check_graph_insights_v0_11_1.py",
        SOURCE_ROOT / "tests" / "check_graph_insights_skill_integration_v0_11_2.py",
    ]
    checked = 0
    for path in targets:
        assert path.exists(), path
        text = path.read_text(encoding="utf-8")
        goals = {m.group(2).strip() for m in _GOAL_LITERAL.finditer(text)}
        dones = {m.group(1).strip() for m in _DONE_LITERAL.finditer(text)}
        assert goals, f"{path.name}: goal 리터럴을 못 찾았다 — 이 판정의 전제가 깨졌다"
        assert dones, f"{path.name}: TASK- deliverable 리터럴을 못 찾았다"
        for d in dones:
            for g in goals:
                assert d != g, (
                    f"{path.name}: deliverable 이 goal 문자열의 복사다 — 항등함수를 잰다: {d!r}"
                )
        checked += len(dones)
    print(f"  fixture deliverable {checked}개 전부 goal 의 복사가 아니다: PASS")


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
