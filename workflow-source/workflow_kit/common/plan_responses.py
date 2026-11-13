"""주장 트리 계획 — 응답 파일 · 받은편지함 · 보관 (ADR-031 2단계).

계약 정본: ``core/claim_plan_spec.md`` §6 (응답 파일) · §7 (`plan_responses/`) · §8.1 (자격).

이 모듈이 하는 일은 셋이다.

1. **읽기** — 응답 파일의 바이트를 :class:`ParsedResponse` 로 (:func:`parse_response`). 줄바꿈을 고치지 않는다:
   CR 은 제어 문자로 자격 1 단계에서 떨어진다 (ADR-031 결정 25).
2. **자격** — 0 단계는 부르는 쪽이 본다 (task 파일의 오류 규칙). 1~6 단계는 :func:`qualify` 다. 보관된
   파일도 매 계산에서 다시 본다 (결정 16) — :func:`qualified_archive`.
3. **디렉터리** — 받은편지함의 자기 무시 · 번호 · 공개 · 배타 이동 · 잠금.

상태 계산은 하지 않는다 — 그것은 :mod:`workflow_kit.common.plan_claims` 다. **읽는 길은 디렉터리를 만들지
않는다**: 응답이 없는 저장소의 트리는 이 모듈 때문에 바뀌지 않는다.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from workflow_kit.common import file_lock, plan_claims
from workflow_kit.common.project_docs import WORK_ITEM_ID_PATTERN

FORMAT = "workflow-kit-plan-response/1"
ROLE_APPROVER = "approver"

#: 한도 (스펙 §6, R5.3) — 각각 적용한다.
MAX_BYTES = 65_536
MAX_COMMENTS = 20
MAX_COMMENT_CHARS = 1_000
MAX_RESPONDER_CHARS = 32

RESPONSES_DIRNAME = "plan_responses"
INBOX_DIRNAME = "inbox"
GITIGNORE_BODY = "*\n"
LOCK_FILENAME = ".lock"
REJECTED_SUFFIX = ".rejected.md"

_DECISION_LINE_RE = re.compile(
    r"^- (?P<id>D[1-9][0-9]*) \[(?P<claim>C[0-9.]+)\] value: (?P<value>\S+) \| default: (?P<default>\S+)"
    r" \| opened: (?P<opened>\S+)$")
_COMMENT_HEAD_RE = re.compile(r"^- \[(?P<target>[^\]]+)\]$")
_COMMENT_PREFIX = "  > "
#: 응답 파일 이름 — `<작업 항목 ID>-<숫자>.md`. ID 문법의 정본은 `project_docs.WORK_ITEM_ID_PATTERN` 이다
#: (게이트가 세는 `_name_re` 와 같은 집합을 봐야 한다 — 좁으면 세어진 파일이 "알 수 없는 파일" 이 된다).
#: 숫자는 ASCII `0-9` 다.
_ANY_RESPONSE_NAME_RE = re.compile(rf"^(?P<task>{WORK_ITEM_ID_PATTERN})-(?P<n>[0-9]+)\.md$")
_FRONTMATTER_KEYS = ("format", "task", "plan_digest", "responder", "role", "received_at")


@dataclass(frozen=True)
class ParsedResponse:
    """응답 파일 한 건을 읽은 것. 자격은 :func:`qualify` 가 본다."""

    name: str
    content_sha256: str
    fields: dict[str, str]
    decisions: tuple[plan_claims.ResponseDecision, ...]
    #: 읽은 결정 줄의 ``opened`` 원문 — ``yes`` · ``no`` 가 아니면 6 단계에서 떨어진다.
    opened_raw: tuple[str, ...]
    comments: tuple[tuple[str, str], ...]
    #: 1 단계(한도 · 인코딩 · 형식)를 어긴 사유.
    limit_problems: tuple[str, ...]
    #: 구조를 읽지 못한 사유 — 머리말은 2 단계, 결정 줄은 6 단계에서 떨어진다.
    header_problems: tuple[str, ...] = ()
    decision_problems: tuple[str, ...] = ()

    @property
    def responder(self) -> str:
        return self.fields.get("responder", "")

    @property
    def received_at(self) -> str:
        return self.fields.get("received_at", "")


@dataclass(frozen=True)
class Verdict:
    """자격 판정. ``stage`` 가 ``None`` 이면 자격이 있다 — 아니면 처음 어긋난 단계(0~6)다."""

    stage: int | None
    reason: str = ""

    @property
    def eligible(self) -> bool:
        return self.stage is None


# --------------------------------------------------------------------------- 읽기


def received_micros(value: str) -> int | None:
    """``received_at`` 의 epoch 마이크로초 — 번호의 출발값 (스펙 §7-1). 스펙 §6 의 꼴이 아니면 ``None``."""
    return plan_claims.parse_received_at(value)


def parse_response(data: bytes, *, name: str = "") -> ParsedResponse:
    """응답 파일의 바이트를 읽는다. 어긋난 것은 버리지 않고 사유로 남긴다."""
    limits: list[str] = []
    header: list[str] = []
    decision_problems: list[str] = []
    digest = hashlib.sha256(data).hexdigest()
    if len(data) > MAX_BYTES:
        limits.append(f"파일이 {len(data):,} 바이트다 (한도 {MAX_BYTES:,})")
    if data.startswith(b"\xef\xbb\xbf"):
        limits.append("BOM 이 있다")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return ParsedResponse(
            name=name, content_sha256=digest, fields={}, decisions=(), opened_raw=(), comments=(),
            limit_problems=(*limits, "UTF-8 이 아니다"), header_problems=("머리말을 읽지 못했다",))
    controls = sorted({ch for ch in text if (ord(ch) < 0x20 and ch not in "\n\t") or ord(ch) == 0x7F})
    if controls:
        limits.append("제어 문자가 있다: " + ", ".join(f"U+{ord(ch):04X}" for ch in controls))

    lines = text.split("\n")
    fields: dict[str, str] = {}
    body_start = 0
    if lines and lines[0] == "---" and "---" in lines[1:]:
        end = lines.index("---", 1)
        for line in lines[1:end]:
            key, sep, value = line.partition(":")
            if not sep or key.strip() not in _FRONTMATTER_KEYS or key.strip() in fields:
                header.append(f"머리말 줄을 읽지 못했다: {line[:40]}")
                continue
            fields[key.strip()] = value.strip()
        body_start = end + 1
    else:
        header.append("머리말(`---` 두 줄)이 없다")

    responder = fields.get("responder", "")
    if not responder:
        limits.append("responder 가 없다")
    elif len(responder) > MAX_RESPONDER_CHARS:
        limits.append(f"responder 가 {len(responder)}자다 (한도 {MAX_RESPONDER_CHARS})")
    if received_micros(fields.get("received_at", "")) is None:
        limits.append("received_at 이 `YYYY-MM-DDTHH:MM:SS[.ffffff]±HH:MM` 꼴이 아니다")

    decisions: list[plan_claims.ResponseDecision] = []
    opened_raw: list[str] = []
    comments: list[tuple[str, str]] = []
    section = ""
    current: tuple[str, list[str]] | None = None
    for line in lines[body_start:]:
        if line.startswith("## "):
            if current is not None:
                comments.append((current[0], "\n".join(current[1])))
                current = None
            section = line[3:].strip()
            continue
        if section == "Decisions":
            if not line.strip():
                continue
            match = _DECISION_LINE_RE.match(line)
            if match is None:
                decision_problems.append(f"결정 줄을 읽지 못했다: {line[:40]}")
                continue
            decisions.append(plan_claims.ResponseDecision(
                decision_id=match["id"], value=match["value"], default=match["default"],
                opened=match["opened"] == "yes", claim_id=match["claim"]))
            opened_raw.append(match["opened"])
        elif section == "Comments":
            head = _COMMENT_HEAD_RE.match(line)
            if head is not None:
                if current is not None:
                    comments.append((current[0], "\n".join(current[1])))
                current = (head["target"], [])
            elif current is not None and line.startswith(_COMMENT_PREFIX):
                current[1].append(line[len(_COMMENT_PREFIX):])
    if current is not None:
        comments.append((current[0], "\n".join(current[1])))

    if len(comments) > MAX_COMMENTS:
        limits.append(f"주석이 {len(comments)}건이다 (한도 {MAX_COMMENTS})")
    for target, body in comments:
        if len(body) > MAX_COMMENT_CHARS:
            limits.append(f"주석 [{target}] 이 {len(body):,} code point 다 (한도 {MAX_COMMENT_CHARS:,})")
    return ParsedResponse(
        name=name, content_sha256=digest, fields=fields, decisions=tuple(decisions),
        opened_raw=tuple(opened_raw), comments=tuple(comments), limit_problems=tuple(limits),
        header_problems=tuple(header), decision_problems=tuple(decision_problems))


def read_response(path: Path) -> ParsedResponse:
    """파일 하나를 읽는다. 한도보다 한 바이트만 더 읽는다 — 큰 파일을 통째로 올리지 않는다."""
    with open(path, "rb") as handle:
        data = handle.read(MAX_BYTES + 1)
        oversized = bool(handle.read(1))
    parsed = parse_response(data, name=path.name)
    if oversized:
        return ParsedResponse(
            name=parsed.name, content_sha256=parsed.content_sha256, fields=parsed.fields,
            decisions=parsed.decisions, opened_raw=parsed.opened_raw, comments=parsed.comments,
            limit_problems=(f"파일이 한도 {MAX_BYTES:,} 바이트를 넘는다",), header_problems=parsed.header_problems,
            decision_problems=parsed.decision_problems)
    return parsed


# --------------------------------------------------------------------------- 자격


def qualify(parsed: ParsedResponse, plan: plan_claims.Plan, task_id: str) -> Verdict:
    """자격 1~6 단계 (스펙 §8.1). 0 단계(task 파일의 오류 규칙)는 부르는 쪽이 먼저 본다."""
    if parsed.limit_problems:
        return Verdict(1, parsed.limit_problems[0])
    if parsed.header_problems or parsed.fields.get("format") != FORMAT:
        return Verdict(2, parsed.header_problems[0] if parsed.header_problems
                       else f"format 이 {FORMAT} 이 아니다: {parsed.fields.get('format', '(없음)')}")
    if parsed.fields.get("task") != task_id:
        return Verdict(3, f"task 가 {task_id} 가 아니다: {parsed.fields.get('task', '(없음)')}")
    if parsed.fields.get("plan_digest") != plan_claims.plan_digest(plan):
        return Verdict(4, "plan_digest 가 지금의 계획과 다르다 — 옛 계획에 대한 응답이다")
    if parsed.fields.get("role") != ROLE_APPROVER:
        return Verdict(5, f"role 이 {ROLE_APPROVER} 가 아니다: {parsed.fields.get('role', '(없음)')}")
    if parsed.decision_problems:
        return Verdict(6, parsed.decision_problems[0])
    expected = {d.id: d for d in plan.decisions}
    seen = [line.decision_id for line in parsed.decisions]
    if len(seen) != len(set(seen)) or set(seen) != set(expected):
        return Verdict(6, "결정 ID 집합이 task 의 것과 다르다")
    for line, opened in zip(parsed.decisions, parsed.opened_raw):
        decision = expected[line.decision_id]
        if line.claim_id != decision.claim_id:
            return Verdict(6, f"{line.decision_id} 의 주장 ID 가 다르다: {line.claim_id}")
        if line.default != decision.default:
            return Verdict(6, f"{line.decision_id} 의 default 가 다르다: {line.default}")
        if line.value not in decision.option_values:
            return Verdict(6, f"{line.decision_id} 의 value 가 선택지에 없다: {line.value}")
        if opened not in ("yes", "no"):
            return Verdict(6, f"{line.decision_id} 의 opened 가 yes · no 가 아니다: {opened}")
    return Verdict(None)


def as_response(parsed: ParsedResponse) -> plan_claims.Response:
    return plan_claims.Response(
        responder=parsed.responder, received_at=parsed.received_at, decisions=parsed.decisions,
        content_sha256=parsed.content_sha256, name=parsed.name)


# --------------------------------------------------------------------------- 디렉터리


def responses_dir(branch_dir: Path) -> Path:
    return branch_dir / RESPONSES_DIRNAME


def inbox_dir(branch_dir: Path) -> Path:
    return responses_dir(branch_dir) / INBOX_DIRNAME


def ensure_inbox(branch_dir: Path) -> Path:
    """받은편지함과 자기 무시 ``.gitignore`` 를 보장한다 — 내용을 **매번** 확인한다 (스펙 §7-3)."""
    inbox = inbox_dir(branch_dir)
    inbox.mkdir(parents=True, exist_ok=True)
    ignore = inbox / ".gitignore"
    try:
        # 바이트로 본다 — 텍스트 읽기는 CRLF 를 LF 로 바꿔 "같다" 고 답한다.
        current = ignore.read_bytes() if ignore.is_file() else None
    except OSError:
        current = None
    if current != GITIGNORE_BODY.encode("utf-8"):
        ignore.write_text(GITIGNORE_BODY, encoding="utf-8", newline="\n")
    return inbox


def _name_re(task_id: str) -> re.Pattern[str]:
    # `<TASK-ID>-*` 는 접두가 겹치는 다른 task 를 잡는다 — 숫자와 접미사까지 맞춘다 (결정 24).
    return re.compile(rf"^{re.escape(task_id)}-(?P<n>[0-9]+)(?P<rejected>\.rejected)?\.md$")


def _numbered(directory: Path, task_id: str) -> list[tuple[int, bool, Path]]:
    """그 디렉터리의 ``<TASK-ID>-<숫자>.md`` · ``.rejected.md`` — (번호, 거둔 것인가, 경로)."""
    if not directory.is_dir():
        return []
    pattern = _name_re(task_id)
    found: list[tuple[int, bool, Path]] = []
    for entry in directory.iterdir():
        match = pattern.match(entry.name)
        if match is not None and entry.is_file():
            found.append((int(match["n"]), match["rejected"] is not None, entry))
    return sorted(found)


def inbox_files(branch_dir: Path, task_id: str) -> list[Path]:
    """받은편지함의 그 task 응답 — "건수" 는 이 목록의 길이다 (스펙 §7-7)."""
    return [path for _, rejected, path in _numbered(inbox_dir(branch_dir), task_id) if not rejected]


def archive_files(branch_dir: Path, task_id: str) -> list[Path]:
    """보관된 그 task 응답 — 거둔 것(``.rejected.md``)은 뺀다."""
    return [path for _, rejected, path in _numbered(responses_dir(branch_dir), task_id) if not rejected]


def unknown_inbox_files(branch_dir: Path) -> list[str]:
    """받은편지함의 ``.md`` 중 응답 이름 꼴이 아닌 것 — 보고만 한다, 게이트는 막지 않는다."""
    inbox = inbox_dir(branch_dir)
    if not inbox.is_dir():
        return []
    return sorted(
        entry.name for entry in inbox.iterdir()
        if entry.is_file() and entry.name.endswith(".md") and not _ANY_RESPONSE_NAME_RE.match(entry.name))


def task_of_response_name(name: str) -> str | None:
    """``<TASK-ID>-<숫자>.md`` 의 task ID — 그 꼴이 아니면(``.rejected.md`` 포함) ``None``."""
    match = _ANY_RESPONSE_NAME_RE.match(name)
    return match["task"] if match is not None else None


def pending_by_task(branch_dir: Path) -> dict[str, int]:
    """받은편지함의 미반영 응답 수 — task 별. 이름만 본다 (내용은 읽지 않는다)."""
    inbox = inbox_dir(branch_dir)
    counts: dict[str, int] = {}
    if not inbox.is_dir():
        return counts
    for entry in sorted(inbox.iterdir()):
        match = _ANY_RESPONSE_NAME_RE.match(entry.name)
        if match is not None and entry.is_file():
            counts[match["task"]] = counts.get(match["task"], 0) + 1
    return counts


def pending_warning(branch_dir: Path) -> str | None:
    """``session-start`` · ``backlog-update`` 가 싣는 한 줄 (스펙 §11). 응답의 내용은 싣지 않는다."""
    counts = pending_by_task(branch_dir)
    if not counts:
        return None
    return (f"계획 응답 {sum(counts.values())}건 미반영 ({', '.join(sorted(counts))}) — plan-import 로 확인")


def taken_numbers(branch_dir: Path, task_id: str, *, ignore: Path | None = None) -> set[int]:
    """그 task 에 이미 쓰인 번호 — 접미사를 통틀어, 받은편지함과 보관 양쪽에서 (스펙 §7-1)."""
    taken: set[int] = set()
    for directory in (inbox_dir(branch_dir), responses_dir(branch_dir)):
        for number, _, path in _numbered(directory, task_id):
            if ignore is None or path != ignore:
                taken.add(number)
    return taken


def numbers_in(directory: Path, task_id: str) -> set[int]:
    """그 디렉터리에서 그 task 가 쓴 번호 — 접미사를 통틀어."""
    return {number for number, _, _ in _numbered(directory, task_id)}


def number_of(path: Path, task_id: str) -> int | None:
    match = _name_re(task_id).match(path.name)
    return int(match["n"]) if match is not None else None


def _place_exclusive(source: Path, directory: Path, task_id: str, number: int, *, suffix: str,
                     branch_dir: Path, ignore: Path | None) -> Path:
    """``source`` 를 ``directory`` 의 빈 번호에 **덮지 않고** 놓는다. 놓인 경로를 돌려준다.

    ``os.link`` 는 이름이 있으면 실패한다 — "없으면 만든다" 가 한 번의 시스템 호출이다. 확인하고 rename
    하면 그 사이에 생긴 파일을 덮는다 (requirements 실측: 900 건 중 500~600 건 유실).
    """
    while True:
        while number in taken_numbers(branch_dir, task_id, ignore=ignore):
            number += 1
        target = directory / f"{task_id}-{number}{suffix}"
        try:
            os.link(source, target)
        except FileExistsError:
            number += 1
            continue
        return target


def publish(branch_dir: Path, task_id: str, data: bytes) -> Path:
    """응답 한 건을 받은편지함에 공개한다 — **쓰는 쪽**의 길이다 (스펙 §7-2). 잠금을 쥐지 않는다.

    ``*.md`` 가 아닌 임시 이름에 다 쓴 뒤 최종 이름으로 한 번에 공개한다. 번호는 ``received_at`` 의
    epoch 마이크로초에서 출발한다 — 읽을 수 없으면 0 에서 (그 응답은 어차피 1 단계에서 떨어진다).
    """
    inbox = ensure_inbox(branch_dir)
    parsed = parse_response(data)
    # epoch 이전의 시각은 음수다 — 이름의 `-<숫자>` 가 깨지지 않게 0 에서 시작한다.
    number = max(received_micros(parsed.received_at) or 0, 0)
    temp = inbox / f".tmp-{os.getpid()}-{secrets.token_hex(8)}"
    with open(temp, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        return _place_exclusive(temp, inbox, task_id, number, suffix=".md", branch_dir=branch_dir, ignore=None)
    finally:
        temp.unlink(missing_ok=True)


def move_exclusive(source: Path, branch_dir: Path, task_id: str, *, rejected: bool = False) -> Path:
    """받은편지함 또는 보관의 응답을 보관(또는 ``.rejected.md``)으로 옮긴다 — 있는 파일을 덮지 않는다 (스펙 §7-5).

    번호는 그대로 가고, 그 번호가 이미 있으면(접미사를 통틀어) 1 씩 더한다. **잠금을 쥔 쪽만** 부른다.
    """
    number = number_of(source, task_id)
    if number is None:
        raise ValueError(f"응답 파일 이름이 아니다: {source.name}")
    archive = responses_dir(branch_dir)
    archive.mkdir(parents=True, exist_ok=True)
    target = _place_exclusive(
        source, archive, task_id, number, suffix=REJECTED_SUFFIX if rejected else ".md",
        branch_dir=branch_dir, ignore=source)
    source.unlink()
    return target


@contextmanager
def inbox_lock(branch_dir: Path) -> Iterator[bool]:
    """``inbox/.lock`` 의 비차단 배타 잠금 (스펙 §7-4). 쥐었으면 ``True`` — 못 쥐면 기다리지 않는다."""
    lock_path = ensure_inbox(branch_dir) / LOCK_FILENAME
    file_lock.prepare_lock_file(lock_path)
    with open(lock_path, "r+b") as handle:
        held = file_lock.try_lock_exclusive(handle)
        try:
            yield held
        finally:
            if held:
                file_lock.unlock(handle)


# --------------------------------------------------------------------------- 보관 응답 읽기 · 옮기기


def judge(path: Path, plan: plan_claims.Plan, task_id: str, *, plan_has_errors: bool) -> tuple[ParsedResponse, Verdict]:
    """파일 하나의 자격 — 0 단계 포함."""
    parsed = read_response(path)
    if plan_has_errors:
        return parsed, Verdict(0, "task 파일의 주장 · 결정이 오류 규칙(L2 · L6 · L9)을 어겼다")
    return parsed, qualify(parsed, plan, task_id)


def qualified_archive(branch_dir: Path, task_id: str, plan: plan_claims.Plan) -> tuple[plan_claims.Response, ...]:
    """그 task 의 **자격 있는** 보관 응답 — 상태 계산의 입력 (스펙 §8).

    보관에 있다는 것은 자격의 근거가 아니다: 지문이 바뀌기 전의 응답, 손으로 놓인 파일은 세지 않는다.
    """
    if plan_claims.has_error_rules(plan):
        return ()
    found: list[plan_claims.Response] = []
    for path in archive_files(branch_dir, task_id):
        try:
            parsed = read_response(path)
        except OSError:
            continue
        if qualify(parsed, plan, task_id).eligible:
            found.append(as_response(parsed))
    return tuple(found)


def copy_archive(source_branch_dir: Path, target_branch_dir: Path, task_id: str) -> list[Path]:
    """이어받기 — 그 task 의 보관 응답을 다른 브랜치 네임스페이스로 복사한다 (스펙 §11, 결정 20).

    보관만이다: 받은편지함 · ``.rejected.md`` 는 옮기지 않는다. 같은 이름이 이미 있으면 두고 넘어간다.
    """
    copied: list[Path] = []
    for path in archive_files(source_branch_dir, task_id):
        target = responses_dir(target_branch_dir) / path.name
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        copied.append(target)
    return copied


def carry_discards(source_branch_dir: Path, target_branch_dir: Path, task_id: str) -> list[Path]:
    """되돌려 적기 — 브랜치에서 **거둔** 응답을 원본 쪽 보관에서도 거둔다 (스펙 §11).

    거둔 응답은 처음부터 없던 것이다 (§8.3). task 만 돌아가고 거둠이 안 따라가면 원본 쪽 보관에 그 응답이
    `.md` 로 남아, 브랜치에서 `proposed` 로 되돌린 결정이 다시 `kept` · `changed` 로 계산된다.
    짝은 **내용이 같은** 보관 응답이다 (번호는 옮기면서 바뀔 수 있다). 짝이 없으면 아무것도 하지 않는다.
    """
    rejected_bodies = {
        path.read_bytes() for _, rejected, path in _numbered(responses_dir(source_branch_dir), task_id) if rejected}
    moved: list[Path] = []
    for path in archive_files(target_branch_dir, task_id):
        if path.read_bytes() in rejected_bodies:
            moved.append(move_exclusive(path, target_branch_dir, task_id, rejected=True))
    return moved


# --------------------------------------------------------------------------- 쓰는 쪽을 위한 렌더


def render_response(
    *, task_id: str, plan: plan_claims.Plan, responder: str, received_at: str,
    values: dict[str, str] | None = None, opened: dict[str, bool] | None = None,
    comments: list[tuple[str, str]] | None = None, role: str = ROLE_APPROVER,
) -> str:
    """응답 파일의 본문 (스펙 §6). ``values`` 에 없는 결정은 기본값, ``opened`` 에 없으면 ``no`` 다."""
    values, opened = values or {}, opened or {}
    lines = [
        "---", f"format: {FORMAT}", f"task: {task_id}", f"plan_digest: {plan_claims.plan_digest(plan)}",
        f"responder: {responder}", f"role: {role}", f"received_at: {received_at}", "---", "", "## Decisions", "",
    ]
    for decision in sorted(plan.decisions, key=lambda d: int(d.id[1:]) if d.id[1:].isdigit() else 0):
        value = values.get(decision.id, decision.default)
        flag = "yes" if opened.get(decision.id, False) else "no"
        lines.append(f"- {decision.id} [{decision.claim_id}] value: {value} | default: {decision.default} | opened: {flag}")
    if comments:
        lines.extend(["", "## Comments", ""])
        for target, body in comments:
            lines.append(f"- [{target}]")
            lines.extend(f"{_COMMENT_PREFIX}{part}" for part in body.split("\n"))
    return "\n".join(lines) + "\n"
