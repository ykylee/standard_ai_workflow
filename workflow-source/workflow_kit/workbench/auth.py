"""토큰 읽기 · 세션 표 · 로그인 실패 제한 (워크벤치 스펙 §5).

토큰 값은 환경변수 이름이나 파일 경로로만 받는다 — 명령줄에 값이 실리지 않게 한다. 세션과 실패 표는
메모리에만 있다 (스펙 §3): 다시 띄우면 다시 로그인한다.
"""

from __future__ import annotations

import hmac
import os
import re
import secrets
import stat
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

ROLE_VIEWER = "viewer"
ROLE_APPROVER = "approver"
ROLES: tuple[str, ...] = (ROLE_VIEWER, ROLE_APPROVER)
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
MIN_TOKEN_CHARS = 32
SESSION_TTL_S = 12 * 3600
FAIL_WINDOW_S = 60.0
FAIL_LIMIT = 5
BLOCK_S = 60.0


class TokenError(ValueError):
    """시작을 거절할 토큰 문제 — 메시지가 거절 이유 한 줄이다 (스펙 §2)."""


@dataclass(frozen=True)
class Token:
    role: str
    name: str
    value: str = field(repr=False)


def parse_role_name(text: str) -> tuple[str, str]:
    """``<role>:<name>`` 을 읽는다 — 역할과 이름 문법이 틀리면 :class:`TokenError`."""
    role, sep, name = text.partition(":")
    if not sep or role not in ROLES:
        raise TokenError(f"역할은 {' · '.join(ROLES)} 중 하나다: {text.split('=', 1)[0]}")
    if not NAME_RE.match(name):
        raise TokenError(f"이름은 [A-Za-z0-9_-]{{1,32}} 이다: {name[:40]}")
    return role, name


def file_mode_too_wide(path: Path) -> bool:
    """POSIX 에서 그룹 · 기타에 권한이 있으면 참. POSIX 모드가 없는 곳(Windows)은 재지 않는다 (스펙 §11)."""
    if os.name != "posix":
        return False
    return bool(stat.S_IMODE(path.stat().st_mode) & 0o077)


def parse_token_arg(arg: str, *, environ: Mapping[str, str] | None = None) -> Token:
    """``<viewer|approver>:<name>=env:<VAR>|file:<path>`` 하나를 읽어 값까지 가져온다."""
    env = os.environ if environ is None else environ
    head, sep, source = arg.partition("=")
    if not sep:
        raise TokenError(f"--token 은 <역할>:<이름>=env:<VAR> 또는 =file:<경로> 다: {head[:40]}")
    role, name = parse_role_name(head)
    kind, sep, ref = source.partition(":")
    if not sep or not ref:
        raise TokenError(f"토큰 {name} 의 값은 env:<VAR> 또는 file:<경로> 로만 받는다")
    if kind == "env":
        value = env.get(ref)
        if value is None:
            raise TokenError(f"토큰 {name} 의 환경변수 {ref} 가 없다")
    elif kind == "file":
        path = Path(ref).expanduser()  # `=file:~/…` 의 `~` 는 셸이 펼치지 않는다
        if not path.is_file():
            raise TokenError(f"토큰 {name} 의 파일이 없다: {ref}")
        if file_mode_too_wide(path):
            raise TokenError(f"토큰 {name} 의 파일 모드가 0600 보다 넓다: {ref}")
        value = path.read_text(encoding="utf-8")
    else:
        raise TokenError(f"토큰 {name} 의 값은 env:<VAR> 또는 file:<경로> 로만 받는다")
    value = value.strip()
    if len(value) < MIN_TOKEN_CHARS:
        raise TokenError(f"토큰 {name} 의 값이 {MIN_TOKEN_CHARS}자 미만이다")
    return Token(role=role, name=name, value=value)


def load_tokens(args: Sequence[str], *, environ: Mapping[str, str] | None = None) -> tuple[Token, ...]:
    if not args:
        raise TokenError("토큰이 없다 — --token <역할>:<이름>=env:<VAR> 를 하나 이상 준다")
    tokens = tuple(parse_token_arg(arg, environ=environ) for arg in args)
    names = [token.name for token in tokens]
    duplicated = sorted({name for name in names if names.count(name) > 1})
    if duplicated:
        raise TokenError(f"토큰 이름이 겹친다: {', '.join(duplicated)}")
    return tokens


def match_token(tokens: Sequence[Token], presented: str) -> Token | None:
    """상수 시간 비교 — 맞는 것을 찾아도 끝까지 돈다."""
    given = presented.encode("utf-8")
    found: Token | None = None
    for token in tokens:
        if hmac.compare_digest(token.value.encode("utf-8"), given):
            found = token
    return found


def write_new_token(path: Path) -> None:
    """``secrets.token_urlsafe(32)`` 를 ``0600`` 파일로 쓴다. 있는 파일은 덮지 않는다 (스펙 §2)."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write((secrets.token_urlsafe(32) + "\n").encode("ascii"))


@dataclass
class Session:
    sid: str = field(repr=False)
    name: str
    role: str
    csrf: str = field(repr=False)
    expires: float
    #: 다음 화면에 한 번 보일 알림 (응답을 받았다는 줄).
    flash: str | None = None


class Sessions:
    """세션 표 — 서버 메모리에만 있다 (스펙 §5.3)."""

    def __init__(self, *, ttl_s: float = SESSION_TTL_S, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_s
        self._clock = clock
        self._table: dict[str, Session] = {}
        self._lock = threading.Lock()

    def _now(self) -> float:
        return self._clock()

    def create(self, token: Token) -> Session:
        session = Session(sid=secrets.token_urlsafe(32), name=token.name, role=token.role,
                          csrf=secrets.token_urlsafe(32), expires=self._now() + self._ttl)
        with self._lock:
            self._table[session.sid] = session
        return session

    def get(self, sid: str | None) -> Session | None:
        if not sid:
            return None
        with self._lock:
            session = self._table.get(sid)
            if session is None:
                return None
            if session.expires <= self._now():
                del self._table[sid]
                return None
            return session

    def drop(self, sid: str) -> None:
        with self._lock:
            self._table.pop(sid, None)


class LoginLimiter:
    """같은 요청자 주소에서 60초 안에 5회 실패하면 그 주소의 로그인을 60초 동안 막는다 (스펙 §5.2)."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._failures: dict[str, list[float]] = {}
        self._blocked_until: dict[str, float] = {}
        self._lock = threading.Lock()

    def _now(self) -> float:
        return self._clock()

    def blocked(self, addr: str) -> bool:
        with self._lock:
            until = self._blocked_until.get(addr)
            if until is None:
                return False
            if until <= self._now():
                del self._blocked_until[addr]
                return False
            return True

    def fail(self, addr: str) -> None:
        now = self._now()
        with self._lock:
            recent = [t for t in self._failures.get(addr, []) if now - t < FAIL_WINDOW_S]
            recent.append(now)
            if len(recent) >= FAIL_LIMIT:
                self._blocked_until[addr] = now + BLOCK_S
                recent = []
            self._failures[addr] = recent
