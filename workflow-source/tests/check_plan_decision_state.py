#!/usr/bin/env python3
"""주장 트리 계획 — 결정 상태 계산을 상태 기계로 전수 탐색한다 (ADR-031, `core/claim_plan_spec.md` §8).

스펙이 내건 것: 결정의 상태는 **보관된 응답 집합과 `answered` 기록의 함수**다. 응답이 도착한 순서,
import 를 부른 횟수와 방식(일괄 / 하나씩), 그 사이에 `answered` 를 적었는지, 상태 칸을 손으로 고쳤는지가
결과를 바꾸지 않는다. requirements 검증이 이 규칙에서 일곱 번 순서 의존을 찾았다 — 손으로 고른 순서
몇 개로는 닫히지 않으므로 끼워 넣기 순서를 **전부** 돈다.

모델: 받은편지함 · 보관 · 거둔 응답 · `answered` 기록 · 상태 칸. 연산은 응답 도착, import(일괄 / 하나),
discard(받은편지함 / 보관), `answered` 적기 · 걷기, 손 편집. 계산은 `plan_claims.compute_states` 그대로다.

1. 끝 상태 1종 — 같은 연산 집합이면 어떤 순서로 끼워 넣어도 결정 상태와 `done` 판정이 같다
2. 멱등 — 끝에서 한 번 더 import 해도 변하지 않는다
3. 부분 채택 없음 — 닫힌 값의 근거가 된 응답은 어느 결정에서도 다투지 않는다 (계산과 따로 쓴 증인)
4. 다툼 — 서로 다른 응답자가 다른 값을 밝힌 결정은 `disputed`, 그렇지 않으면 아니다
5. 상태 여섯 종이 전부 한 번 이상 나온다 (탐색이 빈 구석 없이 돌았다)
6. 하네스가 살아 있다 — 계산을 세 가지로 망가뜨리면 위 판정이 각각 red 다
"""
from __future__ import annotations

WATCHES = (
    # plan_claims 를 import 하면 workflow_kit 패키지 전체가 실린다 — 좁은 선언은 meta-watch 가 잡는다.
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
)

import hashlib
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import plan_claims as pc  # noqa: E402

FAILURES: list[str] = []

DEFAULTS = {"D1": "d", "D2": "d"}
OPTIONS = {"D1": ("d", "x", "y", "z"), "D2": ("d", "p", "q")}
CLAIM_LINES = ["C1 첫 주장이다", "C2 둘째 주장이다"]

Compute = Callable[[pc.Plan, Sequence[pc.Response]], dict[str, str]]


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:8]:
            print(f"        - {problem}")
        if len(problems) > 8:
            print(f"        - … 그 밖 {len(problems) - 8}건")
    else:
        print(f"  PASS  {name}")


def stance_rows() -> list[str]:
    """입장 표(스펙 §8.2)의 세 행 — 계산을 거치지 않고 직접 본다."""
    problems: list[str] = []
    table = {
        ("x", "d", True): "x", ("x", "d", False): "x",       # 다른 값은 열림과 무관하게 입장이다
        ("d", "d", True): "d",                               # 열어 보고 기본값
        ("d", "d", False): None,                             # 열리지 않은 기본값은 입장이 아니다
    }
    for (value, default, opened), want in table.items():
        got = pc.ResponseDecision(decision_id="D1", value=value, default=default, opened=opened).stance
        if got != want:
            problems.append(f"입장({value}, default={default}, opened={opened}) = {got!r}, 기대 {want!r}")
    return problems


def response(responder: str, second: int, **stances: str | None) -> pc.Response:
    """응답 한 건. ``D1="x"`` 는 그 값을 고름, ``D1="d"`` 는 열어 보고 기본값, ``D1=None`` 은 안 열림."""
    lines = []
    for decision_id, default in DEFAULTS.items():
        chosen = stances.get(decision_id)
        lines.append(pc.ResponseDecision(
            decision_id=decision_id, value=chosen if chosen is not None else default,
            default=default, opened=chosen is not None))
    stamp = f"2026-11-13T10:00:{second:02d}+09:00"
    body = f"{responder}|{stamp}|{sorted(stances.items())}"
    return pc.Response(
        responder=responder, received_at=stamp, decisions=tuple(lines),
        content_sha256=hashlib.sha256(body.encode()).hexdigest(), name=f"{responder}@{second}:{sorted(stances.items())}")


def plan_with(answered: dict[str, str | None], columns: dict[str, str]) -> pc.Plan:
    decisions = []
    for index, (decision_id, default) in enumerate(DEFAULTS.items(), start=1):
        state = f"answered:{answered[decision_id]}" if answered.get(decision_id) else columns.get(decision_id, "proposed")
        options = "; ".join(f"{v} = 설명" for v in OPTIONS[decision_id])
        decisions.append(f"{decision_id} [C{index}] 질문 {index} | default: {default} | options: {options} | state: {state}")
    return pc.parse_plan_values(CLAIM_LINES, decisions)


def real_compute(plan: pc.Plan, archived: Sequence[pc.Response]) -> dict[str, str]:
    return pc.compute_states(plan, archived).states


# --------------------------------------------------------------------------- 모델


@dataclass(frozen=True)
class World:
    inbox: frozenset[int] = frozenset()
    #: 보관 — import 한 순서를 지킨다 (망가뜨린 계산이 순서를 읽을 수 있게).
    archive: tuple[int, ...] = ()
    rejected: frozenset[int] = frozenset()
    answered: tuple[tuple[str, str | None], ...] = tuple((d, None) for d in DEFAULTS)
    columns: tuple[tuple[str, str], ...] = tuple((d, "proposed") for d in DEFAULTS)

    def answered_map(self) -> dict[str, str | None]:
        return dict(self.answered)

    def column_map(self) -> dict[str, str]:
        return dict(self.columns)


@dataclass(frozen=True)
class Op:
    kind: str            # arrive | discard | answer | unanswer | hand
    target: object = None
    value: str | None = None
    after: tuple[int, ...] = ()   # 이 연산보다 먼저 끝나야 하는 연산의 번호


@dataclass(frozen=True)
class Scenario:
    name: str
    responses: tuple[pc.Response, ...]
    ops: tuple[Op, ...]


def recompute(world: World, scenario: Scenario, compute: Compute) -> World:
    """쓰는 연산이 끝날 때마다 하는 일 — 계산값을 상태 칸에 적는다 (스펙 §8.6)."""
    plan = plan_with(world.answered_map(), world.column_map())
    states = compute(plan, [scenario.responses[i] for i in world.archive])
    return World(world.inbox, world.archive, world.rejected, world.answered,
                 tuple((d, states[d]) for d in DEFAULTS))


def import_some(world: World, picked: frozenset[int], scenario: Scenario, compute: Compute) -> World:
    moved = World(world.inbox - picked, world.archive + tuple(sorted(picked)), world.rejected,
                  world.answered, world.columns)
    return recompute(moved, scenario, compute)


def apply(world: World, op: Op, scenario: Scenario, compute: Compute) -> World | None:
    """연산 하나. 지금 할 수 없으면 ``None``."""
    if op.kind == "arrive":
        index = int(op.target)  # type: ignore[call-overload]
        return World(world.inbox | {index}, world.archive, world.rejected, world.answered, world.columns)
    if op.kind == "discard":
        index = int(op.target)  # type: ignore[call-overload]
        if index not in world.inbox and index not in world.archive:
            return None
        moved = World(world.inbox - {index}, tuple(i for i in world.archive if i != index),
                      world.rejected | {index}, world.answered, world.columns)
        return recompute(moved, scenario, compute)
    if op.kind in ("answer", "unanswer"):
        decision_id = str(op.target)
        answered = dict(world.answered)
        if op.kind == "unanswer" and not answered[decision_id]:
            return None
        answered[decision_id] = op.value if op.kind == "answer" else None
        columns = dict(world.columns)
        if op.kind == "unanswer":
            columns[decision_id] = "proposed"
        moved = World(world.inbox, world.archive, world.rejected,
                      tuple((d, answered[d]) for d in DEFAULTS), tuple((d, columns[d]) for d in DEFAULTS))
        return recompute(moved, scenario, compute)
    if op.kind == "hand":
        decision_id = str(op.target)
        if dict(world.answered)[decision_id]:
            return None  # answered 칸의 손 편집은 answered 기록 자체를 바꾼다 — 다른 연산이다.
        columns = dict(world.columns)
        columns[decision_id] = str(op.value)
        return World(world.inbox, world.archive, world.rejected, world.answered,
                     tuple((d, columns[d]) for d in DEFAULTS))
    raise AssertionError(op.kind)


@dataclass(frozen=True)
class Final:
    states: tuple[tuple[str, str], ...]
    done_passes: bool
    archive: frozenset[int]
    answered: tuple[tuple[str, str | None], ...]


def explore(scenario: Scenario, compute: Compute) -> tuple[set[Final], int, list[str]]:
    """모든 끼워 넣기를 돈다. (끝 상태 집합, 본 상태 수, 멱등 위반) 을 돌려준다."""
    finals: set[Final] = set()
    idempotence: list[str] = []
    start = (frozenset[int](), World())
    seen = {start}
    frontier = [start]
    while frontier:
        done, world = frontier.pop()
        successors: list[tuple[frozenset[int], World]] = []
        for index, op in enumerate(scenario.ops):
            if index in done or not all(dep in done for dep in op.after):
                continue
            nxt = apply(world, op, scenario, compute)
            if nxt is not None:
                successors.append((done | {index}, nxt))
        if world.inbox:
            successors.append((done, import_some(world, world.inbox, scenario, compute)))
            for single in sorted(world.inbox):
                successors.append((done, import_some(world, frozenset({single}), scenario, compute)))
        if len(done) == len(scenario.ops):
            settled = import_some(world, world.inbox, scenario, compute)
            again = import_some(settled, frozenset(), scenario, compute)
            if again != settled:
                idempotence.append(f"{scenario.name}: 한 번 더 import 하니 {settled.columns} → {again.columns}")
            plan = plan_with(settled.answered_map(), settled.column_map())
            states = compute(plan, [scenario.responses[i] for i in settled.archive])
            opened = [d for d, s in states.items() if pc.state_is_open(s)]
            finals.add(Final(tuple(sorted(states.items())), not opened and not settled.inbox,
                             frozenset(settled.archive), settled.answered))
        for successor in successors:
            if successor not in seen:
                seen.add(successor)
                frontier.append(successor)
    return finals, len(seen), idempotence


# --------------------------------------------------------------------------- 증인 (계산과 따로 쓴다)


def _latest_per_responder(responses: Sequence[pc.Response]) -> list[pc.Response]:
    latest: dict[str, pc.Response] = {}
    for item in responses:
        held = latest.get(item.responder)
        if held is None or (item.received_at, item.content_sha256) > (held.received_at, held.content_sha256):
            latest[item.responder] = item
    return list(latest.values())


def witness(final: Final, scenario: Scenario) -> list[str]:
    """닫힌 값의 근거와 다툼 표시를 계산 함수 없이 다시 본다."""
    problems: list[str] = []
    states = dict(final.states)
    answered = dict(final.answered)
    effective = _latest_per_responder([scenario.responses[i] for i in sorted(final.archive)])

    def disagrees_somewhere(item: pc.Response) -> bool:
        for decision_id in DEFAULTS:
            own = item.stance(decision_id)
            if own is None:
                continue
            if answered[decision_id]:
                if own != answered[decision_id]:
                    return True
                continue
            if any(o is not item and o.stance(decision_id) not in (None, own) for o in effective):
                return True
        return False

    for decision_id, default in DEFAULTS.items():
        state = states[decision_id]
        stated = {s for s in (r.stance(decision_id) for r in effective) if s is not None}
        if answered[decision_id]:
            if state != f"answered:{answered[decision_id]}":
                problems.append(f"{decision_id}: answered 가 유지되지 않았다 ({state})")
            continue
        if (state == pc.STATE_DISPUTED) != (len(stated) > 1):
            problems.append(f"{decision_id}: 다툼 표시가 입장과 어긋난다 — 상태 {state}, 밝힌 값 {sorted(stated)}")
        if state == pc.STATE_KEPT or state.startswith(pc.STATE_CHANGED):
            value = default if state == pc.STATE_KEPT else state.split(":", 1)[1]
            supporters = [r for r in effective if r.stance(decision_id) == value]
            if not any(not disagrees_somewhere(r) for r in supporters):
                problems.append(
                    f"{decision_id}: `{state}` 의 근거가 없다 — 그 값을 밝힌 응답이 없거나 전부 다툼에 들었다")
        if state == pc.STATE_PROPOSED and effective:
            problems.append(f"{decision_id}: 유효 응답이 있는데 proposed 다")
        if state == pc.STATE_UNOPENED and not effective:
            problems.append(f"{decision_id}: 유효 응답이 없는데 unopened 다")
    return problems


# --------------------------------------------------------------------------- 시나리오


def scenarios() -> list[Scenario]:
    def arrive_all(responses: tuple[pc.Response, ...], *extra: Op) -> tuple[Op, ...]:
        return tuple(Op("arrive", i) for i in range(len(responses))) + extra

    out: list[Scenario] = []

    def add(name: str, responses: tuple[pc.Response, ...], *extra: Op) -> None:
        out.append(Scenario(name, responses, arrive_all(responses, *extra)))

    ax, by = response("alice", 1, D1="x"), response("bob", 2, D1="y")
    add("{a x, b y}", (ax, by))
    add("{a x, b x, b y(뒤)}", (ax, response("bob", 2, D1="x"), response("bob", 3, D1="y")))
    ay_later = response("alice", 2, D1="y")
    add("{a x, a y(뒤)}", (ax, ay_later))
    add("{a x, a y(뒤)} + discard y", (ax, ay_later), Op("discard", 1, after=(1,)))
    add("{a x, a y(뒤)} + discard x", (ax, ay_later), Op("discard", 0, after=(0,)))
    add("{a x, a 입장 없음(뒤)}", (ax, response("alice", 2)))
    add("{a x} + discard", (ax,), Op("discard", 0, after=(0,)))
    axp = response("alice", 1, D1="x", D2="p")
    add("{a x·p} + answered D1=y", (axp,), Op("answer", "D1", "y"))
    add("{a x·p, b y} + answered D1=x", (axp, by), Op("answer", "D1", "x"))
    add("{a x·p, b y} + answered D1=x → 걷기", (axp, by),
        Op("answer", "D1", "x"), Op("unanswer", "D1", after=(2,)))
    add("3인 {a x·p, b -·q, c y·-} + answered D1=y",
        (axp, response("bob", 2, D2="q"), response("carol", 3, D1="y")), Op("answer", "D1", "y"))
    add("같은 received_at {a x, a y}", (ax, response("alice", 1, D1="y")))
    add("{a 입장 없음, b y}", (response("alice", 1), by))
    add("{a 기본값을 열어 봄}", (response("alice", 1, D1="d", D2="d"),))
    add("응답 없음 + 손 편집 kept", (), Op("hand", "D1", "kept"))
    add("{a x} + 손 편집 changed:y", (ax,), Op("hand", "D1", "changed:y"))
    add("{a x, b y} + discard b", (ax, by), Op("discard", 1, after=(1,)))
    return out


# --------------------------------------------------------------------------- 망가뜨린 계산


def broken_partial_adoption(plan: pc.Plan, archived: Sequence[pc.Response]) -> dict[str, str]:
    """다툼에 든 응답이 **다른 결정**에 밝힌 입장을 채택한다."""
    result = pc.compute_states(plan, archived)
    states = dict(result.states)
    effective, _ = pc.effective_responses(archived)
    for decision in plan.decisions:
        if decision.answered or states[decision.id] not in (pc.STATE_UNOPENED, pc.STATE_PROPOSED):
            continue
        for item in effective:
            stance = item.stance(decision.id)
            if stance is not None:
                states[decision.id] = pc.STATE_KEPT if stance == decision.default else f"changed:{stance}"
                break
    return states


def broken_first_arrival_wins(plan: pc.Plan, archived: Sequence[pc.Response]) -> dict[str, str]:
    """응답자마다 가장 늦은 응답이 아니라 **먼저 보관된** 응답을 쓴다 (도착 · import 순서를 읽는다)."""
    first: dict[str, pc.Response] = {}
    for item in archived:
        first.setdefault(item.responder, item)
    return pc.compute_states(plan, list(first.values())).states


def broken_column_as_input(plan: pc.Plan, archived: Sequence[pc.Response]) -> dict[str, str]:
    """계산값이 열려 있으면 상태 칸에 적힌 `kept` · `changed` 를 믿는다."""
    states = dict(pc.compute_states(plan, archived).states)
    for decision in plan.decisions:
        if pc.state_is_open(states[decision.id]) and decision.state_kind in (pc.STATE_KEPT, pc.STATE_CHANGED):
            states[decision.id] = decision.state
    return states


def run_all(compute: Compute) -> tuple[list[str], list[str], list[str], set[str], int]:
    """(끝 상태가 갈린 것, 멱등 위반, 증인 위반, 나온 상태 종류, 본 상태 수)."""
    variety: list[str] = []
    idempotence: list[str] = []
    witnessed: list[str] = []
    kinds: set[str] = set()
    visited = 0
    for scenario in scenarios():
        finals, count, not_idempotent = explore(scenario, compute)
        visited += count
        idempotence.extend(not_idempotent)
        signatures = {(f.states, f.done_passes) for f in finals}
        if len(signatures) != 1:
            variety.append(f"{scenario.name}: 끝이 {len(signatures)}종 — {sorted(signatures)[:2]}")
        for final in finals:
            kinds.update(state.split(":", 1)[0] for _, state in final.states)
            witnessed.extend(f"{scenario.name}: {p}" for p in witness(final, scenario))
    return variety, idempotence, sorted(set(witnessed)), kinds, visited


_REAL: tuple[list[str], list[str], list[str], set[str], int] | None = None


def _real() -> tuple[list[str], list[str], list[str], set[str], int]:
    global _REAL
    if _REAL is None:
        _REAL = run_all(real_compute)
    return _REAL


def case_1_single_final_state() -> None:
    variety, _, _, _, visited = _real()
    _record(f"case 1 (끝 상태 1종 — {len(scenarios())} 시나리오, {visited} 상태)", variety)


def case_2_idempotent() -> None:
    _record("case 2 (멱등 — 한 번 더 import 해도 같다)", _real()[1])


def case_3_no_partial_adoption() -> None:
    _record("case 3 (부분 채택 없음 · 다툼 표시 — 계산과 따로 쓴 증인)", _real()[2])


def case_4_expected_outcomes() -> None:
    """손으로 정한 기대값 몇 개 — 증인이 계산과 같은 쪽으로 틀리는 것을 막는다."""
    problems: list[str] = []
    expected = {
        "{a x, b y}": {"D1": "disputed", "D2": "unopened"},
        "{a x, b x, b y(뒤)}": {"D1": "disputed", "D2": "unopened"},
        "{a x, a y(뒤)}": {"D1": "changed:y", "D2": "unopened"},
        "{a x, a y(뒤)} + discard y": {"D1": "changed:x", "D2": "unopened"},
        "{a x, a 입장 없음(뒤)}": {"D1": "unopened", "D2": "unopened"},
        "{a x} + discard": {"D1": "proposed", "D2": "proposed"},
        "{a x·p} + answered D1=y": {"D1": "answered:y", "D2": "unopened"},
        "{a x·p, b y} + answered D1=x": {"D1": "answered:x", "D2": "changed:p"},
        "{a x·p, b y} + answered D1=x → 걷기": {"D1": "disputed", "D2": "unopened"},
        "3인 {a x·p, b -·q, c y·-} + answered D1=y": {"D1": "answered:y", "D2": "disputed"},
        "{a 입장 없음, b y}": {"D1": "changed:y", "D2": "unopened"},
        "{a 기본값을 열어 봄}": {"D1": "kept", "D2": "kept"},
        "응답 없음 + 손 편집 kept": {"D1": "proposed", "D2": "proposed"},
        "{a x} + 손 편집 changed:y": {"D1": "changed:x", "D2": "unopened"},
        "{a x, b y} + discard b": {"D1": "changed:x", "D2": "unopened"},
    }
    by_name = {s.name: s for s in scenarios()}
    for name, want in expected.items():
        finals, _, _ = explore(by_name[name], real_compute)
        got = {tuple(sorted(f.states)) for f in finals}
        if got != {tuple(sorted(want.items()))}:
            problems.append(f"{name}: 기대 {want} · 실제 {sorted(got)}")
    same_time, _, _ = explore(by_name["같은 received_at {a x, a y}"], real_compute)
    if len({f.states for f in same_time}) != 1:
        problems.append("같은 received_at 의 동률이 도착 순서로 갈린다")
    _record("case 4 (기대값 — 손으로 정한 끝 상태)", problems)


def case_5_all_state_kinds_seen() -> None:
    kinds = _real()[3]
    rows = stance_rows()
    # JS 가 꺼진 브라우저 — 열림 기록 없이 다른 값을 고른 응답도 그 값이 입장이다 (requirements Q6).
    unopened_choice = pc.Response(
        responder="alice", received_at="2026-11-13T10:00:01+09:00",
        decisions=(pc.ResponseDecision("D1", "x", "d", False), pc.ResponseDecision("D2", "d", "d", False)))
    states = pc.compute_states(plan_with({"D1": None, "D2": None}, {}), [unopened_choice]).states
    if states != {"D1": "changed:x", "D2": "unopened"}:
        rows.append(f"열림 기록 없는 다른 값: {states}")
    if rows:
        _record("case 5 (입장 세 행 · 상태 여섯 종)", rows)
        return
    wanted = {pc.STATE_PROPOSED, pc.STATE_UNOPENED, pc.STATE_DISPUTED, pc.STATE_KEPT, pc.STATE_CHANGED, pc.STATE_ANSWERED}
    _record("case 5 (상태 여섯 종이 전부 나온다)",
            [] if wanted <= kinds else [f"안 나온 상태: {sorted(wanted - kinds)}"])


def case_6_harness_is_alive() -> None:
    problems: list[str] = []
    partial = run_all(broken_partial_adoption)
    if not partial[2]:
        problems.append("부분 채택을 넣었는데 증인이 조용하다")
    arrival = run_all(broken_first_arrival_wins)
    if not arrival[0]:
        problems.append("먼저 도착한 응답이 이기게 했는데 끝 상태가 갈리지 않는다")
    column = run_all(broken_column_as_input)
    if not (column[0] or column[1] or column[2]):
        problems.append("상태 칸을 입력으로 읽게 했는데 아무것도 걸리지 않는다")
    _record("case 6 (하네스가 살아 있다 — 망가뜨린 계산 셋이 각각 red)", problems)


CASES = [
    case_1_single_final_state,
    case_2_idempotent,
    case_3_no_partial_adoption,
    case_4_expected_outcomes,
    case_5_all_state_kinds_seen,
    case_6_harness_is_alive,
]


def main() -> int:
    print("=== 주장 트리 계획 — 결정 상태 계산 전수 탐색 (ADR-031) ===")
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
