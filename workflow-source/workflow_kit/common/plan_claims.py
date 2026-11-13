"""주장 트리 계획 — task Plan 의 주장 · 결정 파서, 린트, 계획 지문, 결정 상태 계산.

계약 정본: ``workflow-source/core/claim_plan_spec.md`` (ADR-031). 이 모듈의 함수는 **순수**하다 —
파일도 git 도 만지지 않는다. 린트 · 게이트 · ``plan-status`` · (2단계의) ``plan-import`` ·
state 생성기가 전부 여기의 같은 함수를 부른다 (스펙 §1-6). 다른 구현을 두면 갈라진다.

순수해야 하는 이유는 상태 계산이다. "같은 입력이면 같은 출력" (응답이 도착한 순서, import 를
부른 횟수와 방식, ``answered`` 를 적은 시점과 무관)은 계산이 파일 없이 돌 때만 상태 기계로
전수 탐색할 수 있다 (``check_plan_decision_state``).
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone

from workflow_kit.common.project_docs import task_label, task_label_aliases

CLAIMS_KEY = "plan_claims"
DECISIONS_KEY = "plan_decisions"

#: 결정 상태 (스펙 §2.4). 앞의 셋이 "열린 결정" 이다.
STATE_PROPOSED = "proposed"
STATE_UNOPENED = "unopened"
STATE_DISPUTED = "disputed"
STATE_KEPT = "kept"
STATE_CHANGED = "changed"
STATE_ANSWERED = "answered"
OPEN_STATES: tuple[str, ...] = (STATE_PROPOSED, STATE_UNOPENED, STATE_DISPUTED)
_BARE_STATES: tuple[str, ...] = (STATE_PROPOSED, STATE_UNOPENED, STATE_DISPUTED, STATE_KEPT)
_VALUED_STATES: tuple[str, ...] = (STATE_CHANGED, STATE_ANSWERED)

#: 린트 한도 (스펙 §3 — 숫자의 실측은 requirements §1.2).
MAX_CHILDREN = 5
MAX_DECISIONS = 5
CLAIM_MAX_CHARS = 80

#: 결정 줄의 칸 이름 — 정본(쓰기)이 첫 번째, 그 뒤는 읽을 때 받는 표기 (ADR-031 결정 8).
DECISION_COLUMNS: dict[str, tuple[str, ...]] = {
    "default": ("default", "기본"),
    "options": ("options", "선택"),
    "state": ("state", "상태"),
}
_COLUMN_BY_ALIAS: dict[str, str] = {
    alias: canonical for canonical, aliases in DECISION_COLUMNS.items() for alias in aliases
}

COLUMN_SEP = " | "
OPTION_SEP = "; "

_VALUE_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
_CLAIM_ID_RE = re.compile(r"^C([1-9]\d*)(?:\.([1-9]\d*))?(?:\.([1-9]\d*))?$")
_CLAIM_HEAD_RE = re.compile(r"^(C[0-9.]+)\s+(.*)$")
_DECISION_HEAD_RE = re.compile(r"^(D[1-9]\d*)\s+\[(C[0-9.]+)\]\s+(.+)$")
_LOCATION_RE = re.compile(r"^@\s+(?P<path>\S+?):(?P<start>\d+)(?:-(?P<end>\d+))?\s+·\s+(?P<symbol>.+)$")
_NEW_LOCATION_RE = re.compile(r"^@\s+new:\s+(?P<path>\S+)\s+·\s+(?P<symbol>.+)$")
_CITATION_RE = re.compile(r"^\[(C[0-9.]+)\]")
_PERCENT_RE = re.compile(r"\d+\s*%")
_STATUS_TAILS: tuple[str, ...] = ("완료", "done", "✅")
_PATHISH_RE = re.compile(r"^(?:[\w.-]+/[\w./-]*|[\w-]+\.[A-Za-z0-9]{1,5})$")

ERROR_RULES: frozenset[str] = frozenset({"L2", "L6", "L9"})


# --------------------------------------------------------------------------- 자료형


@dataclass(frozen=True)
class ClaimLocation:
    """3단계 주장의 위치. ``new`` 면 아직 없는 코드다 (줄 번호 없음)."""

    path: str
    symbol: str
    start: int | None = None
    end: int | None = None
    new: bool = False


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    raw: str
    parts: tuple[int, ...] = ()
    location: ClaimLocation | None = None

    @property
    def depth(self) -> int:
        return len(self.parts)

    @property
    def valid_id(self) -> bool:
        return bool(self.parts)

    @property
    def parent_id(self) -> str | None:
        if len(self.parts) <= 1:
            return None
        return "C" + ".".join(str(p) for p in self.parts[:-1])

    @property
    def root_id(self) -> str:
        return f"C{self.parts[0]}" if self.parts else self.id


@dataclass(frozen=True)
class Decision:
    id: str
    claim_id: str
    question: str
    default: str
    options: tuple[tuple[str, str], ...]
    state: str
    raw: str
    #: 줄을 읽으며 찾은 형식 문제 (L6). 비어 있지 않으면 이 결정은 "읽을 수 없는" 결정이다.
    problems: tuple[str, ...] = ()

    @property
    def option_values(self) -> tuple[str, ...]:
        return tuple(v for v, _ in self.options)

    @property
    def state_kind(self) -> str:
        return self.state.split(":", 1)[0]

    @property
    def state_value(self) -> str | None:
        return self.state.split(":", 1)[1] if ":" in self.state else None

    @property
    def answered(self) -> bool:
        return self.state_kind == STATE_ANSWERED


@dataclass(frozen=True)
class Plan:
    claims: tuple[Claim, ...] = ()
    decisions: tuple[Decision, ...] = ()
    #: 라벨별 묶음(연속한 같은 라벨 줄) 수 — 2 이상이면 L9.
    claim_runs: int = 0
    decision_runs: int = 0
    #: 파일 순서의 (라벨 key, 값) — 지문의 입력.
    ordered_values: tuple[tuple[str, str], ...] = ()

    @property
    def empty(self) -> bool:
        return not self.claims and not self.decisions

    def claim(self, claim_id: str) -> Claim | None:
        for claim in self.claims:
            if claim.id == claim_id:
                return claim
        return None

    def decision(self, decision_id: str) -> Decision | None:
        for decision in self.decisions:
            if decision.id == decision_id:
                return decision
        return None


@dataclass(frozen=True)
class LintIssue:
    rule: str
    severity: str  # "error" | "warning" | "note"
    message: str
    ref: str = ""

    def render(self) -> str:
        head = f"{self.rule}" + (f" {self.ref}" if self.ref else "")
        return f"{head}: {self.message}"


@dataclass(frozen=True)
class ResponseDecision:
    decision_id: str
    value: str
    default: str
    opened: bool
    claim_id: str = ""

    @property
    def stance(self) -> str | None:
        """그 결정에 대해 실제로 밝힌 값 (스펙 §8.2). 열리지 않은 기본값은 입장이 아니다."""
        if self.value != self.default:
            return self.value
        return self.default if self.opened else None


@dataclass(frozen=True)
class Response:
    """자격 판정(스펙 §8.1)을 통과한 응답 한 건. 자격은 부르는 쪽이 본다."""

    responder: str
    received_at: str
    decisions: tuple[ResponseDecision, ...]
    #: 파일 내용의 sha256 hex — ``received_at`` 까지 같을 때의 동률 규칙.
    content_sha256: str = ""
    name: str = ""

    def stance(self, decision_id: str) -> str | None:
        for line in self.decisions:
            if line.decision_id == decision_id:
                return line.stance
        return None


@dataclass(frozen=True)
class StateResult:
    """결정 상태 계산의 결과."""

    states: dict[str, str] = field(default_factory=dict)
    #: 다툼에 든 유효 응답의 이름 (``Response.name``, 없으면 responder).
    disputed_responses: tuple[str, ...] = ()
    #: 같은 응답자의 뒤 응답 때문에 세지 않은 응답의 이름.
    superseded_responses: tuple[str, ...] = ()

    @property
    def open_ids(self) -> list[str]:
        return [d for d, s in self.states.items() if state_is_open(s)]


# --------------------------------------------------------------------------- 파서


def _label_prefixes(key: str) -> tuple[str, ...]:
    return tuple(f"- {alias}:" for alias in task_label_aliases(key))


def _match_label(stripped: str, prefixes: tuple[str, ...]) -> str | None:
    """``stripped`` 가 그 라벨 줄이면 값(라벨 뒤)을, 아니면 ``None`` 을 돌려준다."""
    for prefix in prefixes:
        if stripped == prefix:
            return ""
        if stripped.startswith(prefix + " "):
            return stripped[len(prefix):].strip()
    return None


def parse_claim_value(value: str) -> Claim:
    """주장 한 줄의 값(``C1.2 문장``)을 읽는다. ID 가 문법에 안 맞아도 예외 없이 돌려준다."""
    match = _CLAIM_HEAD_RE.match(value)
    if not match:
        head, _, rest = value.partition(" ")
        return Claim(id=head, text=rest.strip(), raw=value)
    claim_id, text = match.group(1), match.group(2).strip()
    id_match = _CLAIM_ID_RE.match(claim_id)
    if not id_match:
        return Claim(id=claim_id, text=text, raw=value)
    parts = tuple(int(g) for g in id_match.groups() if g is not None)
    location: ClaimLocation | None = None
    new = _NEW_LOCATION_RE.match(text)
    if new:
        location = ClaimLocation(path=new.group("path"), symbol=new.group("symbol").strip(), new=True)
    else:
        loc = _LOCATION_RE.match(text)
        if loc:
            start = int(loc.group("start"))
            end = int(loc.group("end")) if loc.group("end") else start
            location = ClaimLocation(
                path=loc.group("path"), symbol=loc.group("symbol").strip(), start=start, end=end)
    return Claim(id=claim_id, text=text, raw=value, parts=parts, location=location)


def _split_columns(value: str) -> tuple[str, dict[str, str], list[str]]:
    """결정 줄의 값을 머리와 칸들로 가른다. 칸 이름은 정본 표기로 바꾼다."""
    problems: list[str] = []
    segments = value.split(COLUMN_SEP)
    head = segments[0].strip()
    columns: dict[str, str] = {}
    for segment in segments[1:]:
        name, sep, body = segment.partition(":")
        canonical = _COLUMN_BY_ALIAS.get(name.strip())
        if not sep or canonical is None:
            problems.append(f"모르는 칸 `{segment.strip()[:40]}` — 질문 · 설명에 ` | ` 가 있거나 칸 이름이 틀렸다")
            continue
        if canonical in columns:
            problems.append(f"칸 `{canonical}` 이 두 번 나온다")
            continue
        columns[canonical] = body.strip()
    return head, columns, problems


def parse_state(raw: str) -> tuple[str, str | None] | None:
    """상태 문자열을 (종류, 값) 으로. 문법에 안 맞으면 ``None``."""
    if raw in _BARE_STATES:
        return raw, None
    kind, sep, value = raw.partition(":")
    if sep and kind in _VALUED_STATES and _VALUE_RE.match(value):
        return kind, value
    return None


def parse_decision_value(value: str) -> Decision:
    """결정 한 줄의 값을 읽는다. 형식 문제는 ``problems`` 에 모은다 (L6)."""
    head, columns, problems = _split_columns(value)
    match = _DECISION_HEAD_RE.match(head)
    if not match:
        problems.append("머리 `D<n> [C<id>] <질문>` 을 읽을 수 없다")
        decision_id = head.split(" ", 1)[0] if head else ""
        claim_id, question = "", head
    else:
        decision_id, claim_id, question = match.group(1), match.group(2), match.group(3).strip()

    default = columns.get("default", "")
    if "default" not in columns:
        problems.append("`default` 칸이 없다")
    elif not _VALUE_RE.match(default):
        problems.append(f"`default` 값 `{default}` 이 값 문법(`[a-z0-9_-]{{1,32}}`)에 안 맞는다")

    options: list[tuple[str, str]] = []
    if "options" not in columns:
        problems.append("`options` 칸이 없다")
    else:
        for item in columns["options"].split(OPTION_SEP):
            opt, sep, description = item.partition("=")
            opt = opt.strip()
            if not sep or not _VALUE_RE.match(opt):
                problems.append(f"선택지 `{item.strip()[:40]}` 를 `<value> = <설명>` 으로 읽을 수 없다")
                continue
            options.append((opt, description.strip()))
        values = [v for v, _ in options]
        if len(set(values)) != len(values):
            problems.append("선택지 값이 겹친다")

    state = columns.get("state", STATE_PROPOSED)
    parsed = parse_state(state)
    if parsed is None:
        problems.append(f"상태 `{state}` 를 읽을 수 없다")

    return Decision(
        id=decision_id, claim_id=claim_id, question=question, default=default,
        options=tuple(options), state=state, raw=value, problems=tuple(problems),
    )


def parse_plan(lines: Sequence[str]) -> Plan:
    """task 파일의 줄들에서 주장 · 결정을 읽는다.

    묶음은 **연속한** 같은 라벨 줄이다 (``workflow_writes._set_list_field`` 와 같은 경계).
    둘 이상으로 나뉘어 있어도 전부 읽고, 나뉜 사실은 ``*_runs`` 로 남긴다 — 리더가 첫 묶음만
    읽고 나머지를 조용히 버리면 L9 를 낼 수 없다.
    """
    claim_prefixes = _label_prefixes(CLAIMS_KEY)
    decision_prefixes = _label_prefixes(DECISIONS_KEY)
    claims: list[Claim] = []
    decisions: list[Decision] = []
    ordered: list[tuple[str, str]] = []
    runs = {CLAIMS_KEY: 0, DECISIONS_KEY: 0}
    previous: str | None = None
    for line in lines:
        stripped = line.strip()
        current: str | None = None
        claim_value = _match_label(stripped, claim_prefixes)
        decision_value = _match_label(stripped, decision_prefixes) if claim_value is None else None
        if claim_value == "" or decision_value == "":
            # 값 없는 라벨 줄(placeholder)은 묶음이 아니다 — 세지도, 묶음을 끊지도 않는다.
            continue
        if claim_value is not None:
            current = CLAIMS_KEY
            claims.append(parse_claim_value(claim_value))
            ordered.append((CLAIMS_KEY, claim_value))
        elif decision_value is not None:
            current = DECISIONS_KEY
            decisions.append(parse_decision_value(decision_value))
            ordered.append((DECISIONS_KEY, decision_value))
        if current is not None and current != previous:
            runs[current] += 1
        previous = current
    return Plan(
        claims=tuple(claims), decisions=tuple(decisions),
        claim_runs=runs[CLAIMS_KEY],
        decision_runs=runs[DECISIONS_KEY],
        ordered_values=tuple(ordered),
    )


def parse_plan_values(claims: Iterable[str], decisions: Iterable[str]) -> Plan:
    """값 목록(라벨 없는 줄)에서 Plan 을 만든다 — 쓰기 전에 린트할 때 쓴다."""
    claim_label, decision_label = task_label(CLAIMS_KEY), task_label(DECISIONS_KEY)
    lines = [f"- {claim_label}: {v}" for v in claims] + [f"- {decision_label}: {v}" for v in decisions]
    return parse_plan(lines)


# --------------------------------------------------------------------------- 쓰기 표기


def render_decision_value(decision: Decision, *, state: str | None = None) -> str:
    """결정 줄의 값을 정본 표기로 쓴다. 읽을 수 없는 줄은 원문을 그대로 돌려준다."""
    if decision.problems:
        return decision.raw
    return COLUMN_SEP.join((
        f"{decision.id} [{decision.claim_id}] {decision.question}",
        f"default: {decision.default}",
        "options: " + OPTION_SEP.join(f"{v} = {d}" for v, d in decision.options),
        f"state: {state if state is not None else decision.state}",
    ))


def _digest_value(key: str, value: str) -> str:
    if key == CLAIMS_KEY:
        return value.rstrip()
    # 읽을 수 없는 결정 줄(L6)은 원문 그대로다 (스펙 §5-2) — 반쯤 읽은 줄을 다시 쓰지 않는다.
    if parse_decision_value(value).problems:
        return value.rstrip()
    head, columns, _ = _split_columns(value)
    parts = [head]
    for name in ("default", "options"):
        if name in columns:
            parts.append(f"{name}: {columns[name]}")
    return COLUMN_SEP.join(parts).rstrip()


def plan_digest(plan: Plan) -> str:
    """계획 지문 (스펙 §5). 상태 칸만 바뀌면 같고, 그 밖의 무엇이 바뀌어도 다르다."""
    body = "\n".join(
        f"- {task_label(key)}: {_digest_value(key, value)}" for key, value in plan.ordered_values)
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def rewrite_decision_states(
    lines: Sequence[str], states: dict[str, str],
) -> tuple[list[str], list[tuple[str, str, str]]]:
    """결정 줄의 상태 칸을 ``states`` 대로 고쳐 쓴다. (새 줄들, [(결정 ID, 옛, 새)]) 를 돌려준다.

    읽을 수 없는 줄(L6)과 ``states`` 에 없는 결정은 건드리지 않는다. 고친 줄은 정본 표기로
    다시 쓴다 — 찾기는 넓게, 쓰기는 좁게.
    """
    prefixes = _label_prefixes(DECISIONS_KEY)
    label = task_label(DECISIONS_KEY)
    out: list[str] = []
    changes: list[tuple[str, str, str]] = []
    for line in lines:
        value = _match_label(line.strip(), prefixes)
        if not value:
            out.append(line)
            continue
        decision = parse_decision_value(value)
        new_state = states.get(decision.id)
        if decision.problems or new_state is None or new_state == decision.state:
            out.append(line)
            continue
        indent = line[: len(line) - len(line.lstrip())]
        out.append(f"{indent}- {label}: {render_decision_value(decision, state=new_state)}")
        changes.append((decision.id, decision.state, new_state))
    return out, changes


def remove_label_lines(lines: Sequence[str], key: str) -> list[str]:
    """그 라벨의 줄을 전부 걷는다 (선택 라벨은 placeholder 를 남기지 않는다)."""
    prefixes = _label_prefixes(key)
    return [line for line in lines if _match_label(line.strip(), prefixes) is None]


def normalize_new_decision(value: str) -> tuple[str, bool]:
    """`--plan-decision` 으로 들어온 줄을 정본 표기로, 상태는 ``proposed`` 로 (ADR-031 결정 9).

    (고친 값, 상태 칸을 버렸는가) 를 돌려준다. 읽을 수 없는 줄은 그대로 돌려준다 — 린트가 잡는다.
    """
    decision = parse_decision_value(value)
    if decision.problems:
        return value, False
    _, columns, _ = _split_columns(value)
    had_state = "state" in columns and decision.state != STATE_PROPOSED
    return render_decision_value(decision, state=STATE_PROPOSED), had_state


def decision_identity(value: str) -> str:
    """상태 칸을 뺀 결정 줄 — 같은 결정을 다시 넣었는지 가릴 때 쓴다."""
    return _digest_value(DECISIONS_KEY, value)


# --------------------------------------------------------------------------- 인용 · 묶음


def criterion_citation(criterion: str) -> str | None:
    """완료 기준 줄 머리의 ``[C<id>]`` 인용. 없으면 ``None``."""
    match = _CITATION_RE.match(criterion.strip())
    return match.group(1) if match else None


def _root_of(claim_id: str) -> str:
    return claim_id.split(".", 1)[0]


@dataclass(frozen=True)
class ClaimBundle:
    """1단계 주장 하나와, 그것(또는 후손)을 인용한 완료 기준의 번호(1부터)."""

    claim: Claim
    criteria: tuple[int, ...]

    @property
    def unmeasured(self) -> bool:
        return not self.criteria


def claim_bundles(plan: Plan, criteria: Sequence[str]) -> list[ClaimBundle]:
    """주장별 묶음 (스펙 §10). ``unmeasured`` 는 L7 의 "재지 않는 주장" 과 같은 판정이다."""
    known = {c.id for c in plan.claims}
    cited: dict[str, list[int]] = {}
    for index, criterion in enumerate(criteria, start=1):
        citation = criterion_citation(criterion)
        if citation is None or citation not in known:
            continue
        cited.setdefault(_root_of(citation), []).append(index)
    return [
        ClaimBundle(claim=claim, criteria=tuple(cited.get(claim.id, ())))
        for claim in plan.claims if claim.valid_id and claim.depth == 1
    ]


# --------------------------------------------------------------------------- 린트


def _ends_with_status(text: str) -> bool:
    tail = text.rstrip().rstrip(".").rstrip()
    return any(tail.endswith(marker) for marker in _STATUS_TAILS)


def lint_plan(
    plan: Plan,
    *,
    criteria: Sequence[str] = (),
    file_line_count: Callable[[str], int | None] | None = None,
) -> list[LintIssue]:
    """린트 L1~L10 (스펙 §3).

    ``file_line_count(path)`` 는 HEAD 의 그 파일 줄 수를, 없으면 ``None`` 을 돌려준다. 함수
    자체가 ``None`` 이면(git 밖) L5 를 건너뛰고 그 사실을 ``note`` 로 남긴다 — 못 잰 것을 통과로
    세지 않는다.
    """
    issues: list[LintIssue] = []
    if plan.empty:
        return issues

    # L9 — 묶음이 나뉘었다.
    for label_key, runs in ((CLAIMS_KEY, plan.claim_runs), (DECISIONS_KEY, plan.decision_runs)):
        if runs > 1:
            issues.append(LintIssue(
                "L9", "error",
                f"`{task_label(label_key)}` 묶음이 {runs}개로 나뉘어 있다 — 한 묶음으로 모은다"))

    # L2 — ID.
    seen: set[str] = set()
    valid = [c for c in plan.claims if c.valid_id]
    for claim in plan.claims:
        if not claim.valid_id:
            issues.append(LintIssue("L2", "error", "주장 ID 를 읽을 수 없다 (`C<n>[.<n>[.<n>]]`)", claim.id))
            continue
        if claim.id in seen:
            issues.append(LintIssue("L2", "error", "주장 ID 가 겹친다", claim.id))
        seen.add(claim.id)
    ids = {c.id for c in valid}
    children: dict[str | None, list[int]] = {}
    for claim in valid:
        if claim.parent_id is not None and claim.parent_id not in ids:
            issues.append(LintIssue("L2", "error", f"부모 `{claim.parent_id}` 가 없다", claim.id))
        children.setdefault(claim.parent_id, []).append(claim.parts[-1])
    for parent, numbers in children.items():
        expected = list(range(1, len(set(numbers)) + 1))
        if sorted(set(numbers)) != expected:
            where = parent or "1단계"
            issues.append(LintIssue(
                "L2", "error", f"형제 번호가 1 부터 연속이 아니다 ({sorted(set(numbers))})", where))

    # L1 — 폭.
    for parent, numbers in children.items():
        if len(set(numbers)) > MAX_CHILDREN:
            where = parent or "1단계"
            issues.append(LintIssue(
                "L1", "warning", f"주장이 {len(set(numbers))}개다 (≤ {MAX_CHILDREN})", where))

    # L3 · L4 · L8 — 문장.
    for claim in valid:
        if claim.depth <= 2:
            if ";" in claim.text:
                issues.append(LintIssue("L3", "warning", "한 주장에 두 사실이 `;` 로 이어져 있다", claim.id))
            if len(claim.text) > CLAIM_MAX_CHARS:
                issues.append(LintIssue(
                    "L3", "warning", f"{len(claim.text)}자다 (≤ {CLAIM_MAX_CHARS}자)", claim.id))
        if claim.depth == 1:
            first = claim.text.split(" ", 1)[0].strip("`")
            if first and _PATHISH_RE.match(first):
                issues.append(LintIssue(
                    "L4", "warning", "1단계 주장이 경로 · 파일명으로 시작한다 — 동작 단위로 나눈다", claim.id))
        if _PERCENT_RE.search(claim.text) or _ends_with_status(claim.text):
            issues.append(LintIssue("L8", "warning", "주장에 진척률 · 상태 표현이 있다", claim.id))

    # L5 — 위치.
    located = [c for c in valid if c.location is not None and not c.location.new]
    if located and file_line_count is None:
        issues.append(LintIssue(
            "L5", "note", f"git 밖이라 위치 {len(located)}건을 확인하지 못했다 (건너뜀)"))
    elif file_line_count is not None:
        for claim in located:
            location = claim.location
            assert location is not None and location.start is not None and location.end is not None
            count = file_line_count(location.path)
            if count is None:
                issues.append(LintIssue("L5", "warning", f"`{location.path}` 가 HEAD 에 없다", claim.id))
            elif location.start < 1 or location.end < location.start or location.end > count:
                issues.append(LintIssue(
                    "L5", "warning",
                    f"`{location.path}` 는 {count}줄인데 {location.start}-{location.end} 를 가리킨다", claim.id))
    for claim in valid:
        if claim.depth == 3 and claim.location is None:
            issues.append(LintIssue(
                "L5", "warning", "3단계 주장은 위치(`@ path:line · symbol` 또는 `@ new: …`)다", claim.id))

    # L6 — 결정.
    if len(plan.decisions) > MAX_DECISIONS:
        issues.append(LintIssue(
            "L6", "error", f"결정이 {len(plan.decisions)}개다 (≤ {MAX_DECISIONS})"))
    decision_ids: set[str] = set()
    for decision in plan.decisions:
        ref = decision.id or "(ID 없음)"
        for problem in decision.problems:
            issues.append(LintIssue("L6", "error", problem, ref))
        if decision.id in decision_ids:
            issues.append(LintIssue("L6", "error", "결정 ID 가 겹친다", ref))
        decision_ids.add(decision.id)
        if decision.problems:
            continue
        if decision.claim_id not in ids:
            issues.append(LintIssue("L6", "error", f"가리키는 주장 `{decision.claim_id}` 가 없다", ref))
        if len(decision.options) < 2:
            issues.append(LintIssue("L6", "error", "선택지가 둘 미만이다", ref))
        if decision.default not in decision.option_values:
            issues.append(LintIssue(
                "L6", "error", f"`default` 값 `{decision.default}` 이 선택지에 없다", ref))
        value = decision.state_value
        if value is not None and value not in decision.option_values:
            issues.append(LintIssue("L6", "error", f"상태의 값 `{value}` 이 선택지에 없다", ref))

    # L7 · L10 — 인용.
    for index, criterion in enumerate(criteria, start=1):
        citation = criterion_citation(criterion)
        if citation is not None and citation not in ids:
            issues.append(LintIssue(
                "L10", "warning", f"완료 기준 #{index} 가 없는 주장 `{citation}` 을 인용한다"))
    for bundle in claim_bundles(plan, criteria):
        if bundle.unmeasured:
            issues.append(LintIssue(
                "L7", "warning", "이 주장(과 후손)을 인용한 완료 기준이 없다 — 재지 않는 주장", bundle.claim.id))
    return issues


def lint_errors(issues: Iterable[LintIssue]) -> list[LintIssue]:
    return [i for i in issues if i.severity == "error"]


def has_error_rules(plan: Plan) -> bool:
    """오류 규칙(L2 · L6 · L9)을 어겼는가 — 0 단계 (스펙 §8.1)."""
    return bool(lint_errors(lint_plan(plan)))


# --------------------------------------------------------------------------- 상태 계산


def state_is_open(state: str) -> bool:
    return state.split(":", 1)[0] in OPEN_STATES


_RECEIVED_AT_RE = re.compile(
    r"^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,6}))?([+-])([0-9]{2}):([0-9]{2})$")


def parse_received_at(value: str) -> int | None:
    """``received_at`` 을 epoch 마이크로초로 (스펙 §6). 그 꼴이 아니면 ``None``.

    받는 꼴은 하나다: ``YYYY-MM-DDTHH:MM:SS[.ffffff]±HH:MM`` — 소수 초는 1~6 자리, 시간대는 숫자 오프셋.
    ``datetime.fromisoformat`` 에 맡기지 않는다 — 받는 범위가 Python 판마다 다르고(3.10 은 ``.5`` · ``Z`` 를
    거절한다) 스펙보다 넓다(주 날짜 · 기본형 · 초 생략 · 7 자리 이상의 소수).
    """
    match = _RECEIVED_AT_RE.match(value)
    if match is None:
        return None
    year, month, day, hour, minute, second = (int(match.group(i)) for i in range(1, 7))
    offset_hours, offset_minutes = int(match.group(9)), int(match.group(10))
    if hour > 23 or minute > 59 or second > 59 or offset_hours > 23 or offset_minutes > 59:
        return None
    try:
        days = (datetime(year, month, day, tzinfo=timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)).days
    except ValueError:
        return None
    offset = (offset_hours * 3600 + offset_minutes * 60) * (1 if match.group(8) == "+" else -1)
    micros = int((match.group(7) or "").ljust(6, "0") or 0)
    return (days * 86_400 + hour * 3600 + minute * 60 + second - offset) * 1_000_000 + micros


def _received_key(response: Response) -> tuple[int, int, str, str]:
    """유효 응답을 고를 때의 순서 — ``received_at`` 이 늦을수록, 같으면 sha256 이 클수록 뒤.

    시각을 읽을 수 있으면 epoch 마이크로초로, 못 읽으면 문자열로 가른다 (읽을 수 있는 쪽이 뒤).
    자격 있는 응답의 시각은 언제나 읽힌다 — 문자열 쪽은 결정적이기만 하면 된다.
    """
    micros = parse_received_at(response.received_at)
    if micros is None:
        return (0, 0, response.received_at, response.content_sha256)
    return (1, micros, "", response.content_sha256)


def _later(a: Response, b: Response) -> Response:
    return a if _received_key(a) >= _received_key(b) else b


def effective_responses(responses: Sequence[Response]) -> tuple[list[Response], list[Response]]:
    """응답자마다 가장 늦은 응답 하나 (스펙 §8.3). (유효, 대체된 것) 을 돌려준다."""
    latest: dict[str, Response] = {}
    for response in responses:
        current = latest.get(response.responder)
        latest[response.responder] = response if current is None else _later(current, response)
    effective = [latest[name] for name in sorted(latest)]
    chosen = {id(r) for r in effective}
    superseded = [r for r in responses if id(r) not in chosen]
    return effective, superseded


def compute_states(plan: Plan, responses: Sequence[Response] = ()) -> StateResult:
    """결정마다의 상태 (스펙 §8.4 · §8.5).

    입력은 계획과 **자격 있는** 보관 응답뿐이다. 상태 칸은 ``answered`` 인지만 읽는다 — 칸이
    계산의 입력이 되면 응답이 도착한 순서와 import 시점이 결과를 바꾼다.
    """
    effective, superseded = effective_responses(responses)
    answered = {d.id: d.state_value for d in plan.decisions if d.answered}

    disputed_ids: set[int] = set()
    disputed_decisions: set[str] = set()
    for decision in plan.decisions:
        stances = [(r, r.stance(decision.id)) for r in effective]
        stated = [(r, s) for r, s in stances if s is not None]
        if decision.id in answered:
            # 다툼 1 — 대화의 답과 다른 입장.
            for response, stance in stated:
                if stance != answered[decision.id]:
                    disputed_ids.add(id(response))
            continue
        # 다툼 2 — 서로 다른 응답자가 다른 값을 밝혔다 (다툼 1 로 물린 응답도 상대가 된다).
        if len({s for _, s in stated}) > 1:
            disputed_decisions.add(decision.id)
            for response, _ in stated:
                disputed_ids.add(id(response))

    adopted = [r for r in effective if id(r) not in disputed_ids]
    states: dict[str, str] = {}
    for decision in plan.decisions:
        if decision.id in answered:
            states[decision.id] = decision.state
        elif decision.id in disputed_decisions:
            states[decision.id] = STATE_DISPUTED
        else:
            gathered = {s for s in (r.stance(decision.id) for r in adopted) if s is not None}
            if gathered:
                # 다툼에 들지 않은 입장은 많아야 하나다 — 둘이면 위에서 다툼 2 로 걸렸다.
                value = sorted(gathered)[0]
                states[decision.id] = STATE_KEPT if value == decision.default else f"{STATE_CHANGED}:{value}"
            elif effective:
                states[decision.id] = STATE_UNOPENED
            else:
                states[decision.id] = STATE_PROPOSED
    return StateResult(
        states=states,
        disputed_responses=tuple(r.name or r.responder for r in effective if id(r) in disputed_ids),
        superseded_responses=tuple(r.name or r.responder for r in superseded),
    )


def open_decision_ids(plan: Plan, responses: Sequence[Response] = ()) -> list[str]:
    """열린 결정의 ID (스펙 §4). 읽을 수 없는 결정(L6)은 열린 것으로 센다."""
    result = compute_states(plan, responses)
    opened: list[str] = []
    for decision in plan.decisions:
        if decision.problems or state_is_open(result.states.get(decision.id, STATE_PROPOSED)):
            opened.append(decision.id or "(ID 없음)")
    return opened


def column_open_decision_ids(plan: Plan) -> list[str]:
    """상태 **칸** 기준의 열린 결정 — ``state.json`` 의 ``open_decisions`` 용 (스펙 §11).

    게이트는 이것을 쓰지 않는다. 생성기의 입력이 task 파일뿐이라 칸으로 세는 근사다.
    """
    return [d.id or "(ID 없음)" for d in plan.decisions if d.problems or state_is_open(d.state)]
