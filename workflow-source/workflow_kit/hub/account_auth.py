"""Hub-local human accounts. Signing up grants nothing; projects open through a linked human callsign."""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta
from typing import Any

from workflow_kit.hub.errors import HubError, forbidden, invalid_field, not_found, unauthorized
from workflow_kit.hub.store import Ctx, Principal, Store, _iso, hash_token, new_token

SESSION_DAYS = 30
SIGNUPS_PER_HOUR = 30
PBKDF2_ROUNDS = 310_000


def _password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ROUNDS, base64.urlsafe_b64encode(salt).decode().rstrip("="),
        base64.urlsafe_b64encode(digest).decode().rstrip("="))


def _password_matches(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt, expected = encoded.split("$", 3)
        iterations = int(rounds)
        if scheme != "pbkdf2_sha256" or not 100_000 <= iterations <= 1_000_000:
            return False
        salt_bytes = base64.urlsafe_b64decode(salt + "=" * (-len(salt) % 4))
        expected_bytes = base64.urlsafe_b64decode(expected + "=" * (-len(expected) % 4))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt_bytes, iterations)
        return hmac.compare_digest(actual, expected_bytes)
    except (ValueError, TypeError):
        return False


class HubAccounts:
    def __init__(self, store: Store) -> None:
        self.store = store

    def enroll(self, token: str, username: str, display_name: str, password: str, now: datetime) -> tuple[str, dict[str, Any]]:
        if not all(isinstance(value, str) for value in (username, display_name, password)):
            raise invalid_field("account", "계정 이름·표시 이름·비밀번호는 문자열이어야 한다")
        # 토큰 없이 가입할 수 있다 — 가입만으로는 어떤 프로젝트도 열리지 않는다 (연결은 토큰이나 참여 뒤 소유자 승인).
        principal = self.store.authenticate(token, now) if token else None
        if token and (not principal or principal.kind != "callsign" or principal.callsign_kind != "human" or not principal.human_approved):
            raise forbidden("토큰을 넣으려면 승인된 사람 콜사인 토큰이어야 한다")
        username = username.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,63}", username):
            raise invalid_field("username", "영문 소문자·숫자·._- 3~64자")
        display_name = display_name.strip()
        if not display_name or len(display_name) > 100:
            raise invalid_field("display_name", "1~100자")
        if len(password) < 8 or len(password) > 256:
            raise invalid_field("password", "8~256자")
        account_id = "acct_" + secrets.token_hex(16)
        session = new_token()
        try:
            with self.store.write() as conn:
                if principal is None:
                    self._signup_slot(conn, now)
                elif conn.execute("SELECT 1 FROM hub_account_callsign WHERE project_id=? AND callsign=?",
                                  (principal.project_id, principal.callsign)).fetchone():
                    raise HubError(409, "callsign_already_linked", "이 사람 콜사인은 이미 계정에 연결됐다")
                conn.execute("INSERT INTO hub_account(id,username,display_name,password_hash,created_at) VALUES(?,?,?,?,?)",
                             (account_id, username, display_name, _password_hash(password), _iso(now)))
                if principal is not None:
                    conn.execute("INSERT INTO hub_account_callsign(account_id,project_id,callsign,linked_at) VALUES(?,?,?,?)",
                                 (account_id, principal.project_id, principal.callsign, _iso(now)))
                conn.execute("INSERT INTO hub_account_session(token_hash,account_id,created_at,expires_at) VALUES(?,?,?,?)",
                             (hash_token(session), account_id, _iso(now), _iso(now + timedelta(days=SESSION_DAYS))))
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise HubError(409, "username_taken", "이미 사용 중인 계정 이름이다") from exc
            raise
        return session, {"id": account_id, "username": username, "display_name": display_name,
                         "callsign": principal.callsign if principal else None, "project_id": principal.project_id if principal else None}

    @staticmethod
    def _signup_slot(conn: Any, now: datetime) -> None:
        """토큰 없는 가입은 허브 전체에서 시간당 :data:`SIGNUPS_PER_HOUR` — 공개 허브의 대량 가입을 막는다."""
        key = "signup:open"  # 로그인 키는 sha256 16진수라 겹치지 않는다
        row = conn.execute("SELECT attempts,window_started_at FROM hub_account_login_attempt WHERE username_hash=?", (key,)).fetchone()
        fresh = row is not None and now - datetime.fromisoformat(row["window_started_at"]) < timedelta(hours=1)
        count = int(row["attempts"]) + 1 if fresh else 1
        if count > SIGNUPS_PER_HOUR:
            raise HubError(429, "signup_rate_limited", "가입이 많다 — 잠시 뒤 다시 시도한다")
        conn.execute("INSERT INTO hub_account_login_attempt(username_hash,attempts,window_started_at,locked_until) VALUES(?,?,?,NULL) "
                     "ON CONFLICT(username_hash) DO UPDATE SET attempts=excluded.attempts,window_started_at=excluded.window_started_at",
                     (key, count, row["window_started_at"] if fresh else _iso(now)))

    def join(self, account_id: str, project: str, callsign: str, now: datetime) -> dict[str, Any]:
        """로그인한 계정이 프로젝트에 참여한다 — 승인 전 사람 콜사인을 만들어 연결한다 (토큰은 내지 않는다)."""
        if not isinstance(project, str) or not project.strip() or not isinstance(callsign, str):
            raise invalid_field("project", "프로젝트 ID 또는 git 주소")
        pid = project.strip()
        if not self.store.projects(pid):
            pid = self.store.lookup_project(pid).get("project_id") or ""
        if not pid:
            raise not_found("프로젝트가 없다 — ID 나 git 주소를 확인한다")
        moved = self.store.project_moved(pid)
        if moved:
            raise HubError(410, "project_moved", "프로젝트가 다른 허브로 이동했다", {"project_id": pid, "to": moved})
        with self.store.read() as conn:
            if conn.execute("SELECT 1 FROM hub_account_callsign WHERE account_id=? AND project_id=?", (account_id, pid)).fetchone():
                raise HubError(409, "already_joined", "이 계정은 이미 그 프로젝트에 연결됐다")
        ctx = Ctx(now=now, via="ui")
        self.store.register_callsign(ctx, pid, callsign.strip(), "human", "허브 계정 참여", "browser")
        with self.store.write() as conn:
            conn.execute("INSERT INTO hub_account_callsign(account_id,project_id,callsign,linked_at) VALUES(?,?,?,?)",
                         (account_id, pid, callsign.strip(), _iso(now)))
        return {"project_id": pid, "callsign": callsign.strip(), "human_pending": True}

    def login(self, username: str, password: str, now: datetime) -> tuple[str, dict[str, Any]]:
        if not isinstance(username, str) or not isinstance(password, str):
            raise unauthorized("계정 이름 또는 비밀번호가 맞지 않는다")
        username = username.strip().lower()
        uname_hash = hashlib.sha256(username.encode()).hexdigest()
        denied = False
        rate_limited = False
        with self.store.write() as conn:
            attempt = conn.execute("SELECT attempts,window_started_at,locked_until FROM hub_account_login_attempt WHERE username_hash=?",
                                   (uname_hash,)).fetchone()
            if attempt and attempt["locked_until"] and attempt["locked_until"] > _iso(now):
                rate_limited = True
                row = None
            else:
                row = conn.execute("SELECT id,username,display_name,password_hash FROM hub_account WHERE username=? AND active=1",
                                   (username,)).fetchone()
                # Hash a fixed dummy credential for unknown accounts too, keeping the user lookup timing similar.
                dummy = "pbkdf2_sha256$310000$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                valid = _password_matches(password, row["password_hash"] if row is not None else dummy) and row is not None
                if not valid:
                    started = datetime.fromisoformat(attempt["window_started_at"]) if attempt else now
                    count = int(attempt["attempts"]) + 1 if attempt and now - started < timedelta(minutes=15) else 1
                    locked_until = _iso(now + timedelta(minutes=15)) if count >= 8 else None
                    conn.execute("INSERT INTO hub_account_login_attempt(username_hash,attempts,window_started_at,locked_until) VALUES(?,?,?,?) "
                                 "ON CONFLICT(username_hash) DO UPDATE SET attempts=excluded.attempts,window_started_at=excluded.window_started_at,locked_until=excluded.locked_until",
                                 (uname_hash, count, _iso(started if count > 1 else now), locked_until))
                    denied = True
                else:
                    conn.execute("DELETE FROM hub_account_login_attempt WHERE username_hash=?", (uname_hash,))
        if rate_limited:
            raise HubError(429, "login_rate_limited", "로그인 시도가 많다 — 잠시 뒤 다시 시도한다")
        if denied:
            raise unauthorized("계정 이름 또는 비밀번호가 맞지 않는다")
        if row is None:
            raise unauthorized("계정 이름 또는 비밀번호가 맞지 않는다")
        session = new_token()
        with self.store.write() as conn:
            conn.execute("INSERT INTO hub_account_session(token_hash,account_id,created_at,expires_at) VALUES(?,?,?,?)",
                         (hash_token(session), row["id"], _iso(now), _iso(now + timedelta(days=SESSION_DAYS))))
        return session, {"id": row["id"], "username": row["username"], "display_name": row["display_name"]}

    def reset_password(self, username: str, password: str, now: datetime) -> dict[str, Any]:
        """운영자(서버의 ``hub admin``)가 비밀번호를 새로 정한다 — 로그인 세션 전부와 로그인 잠금을 푼다."""
        username = username.strip().lower()
        if len(password) < 8 or len(password) > 256:
            raise invalid_field("password", "8~256자")
        encoded = _password_hash(password)
        with self.store.write() as conn:
            row = conn.execute("SELECT id FROM hub_account WHERE username=? AND active=1", (username,)).fetchone()
            if row is None:
                raise not_found(f"계정이 없다: {username}")
            conn.execute("UPDATE hub_account SET password_hash=? WHERE id=?", (encoded, row["id"]))
            ended = conn.execute("DELETE FROM hub_account_session WHERE account_id=?", (row["id"],)).rowcount
            conn.execute("DELETE FROM hub_account_login_attempt WHERE username_hash=?", (hashlib.sha256(username.encode()).hexdigest(),))
            self.store._event(conn, Ctx(now=now, via="admin"), None, "hub_account", username, "reset_password", None,
                              {"sessions_ended": ended}, callsign="admin:hub")
        return {"username": username, "sessions_ended": ended}

    def link(self, account_id: str, token: str, now: datetime) -> dict[str, Any]:
        principal = self.store.authenticate(token, now)
        if not principal or principal.kind != "callsign" or principal.callsign_kind != "human" or not principal.human_approved:
            raise forbidden("승인된 사람 콜사인 토큰만 계정에 연결할 수 있다")
        with self.store.write() as conn:
            if not conn.execute("SELECT 1 FROM hub_account WHERE id=? AND active=1", (account_id,)).fetchone():
                raise unauthorized("허브 계정 세션이 만료됐다")
            linked = conn.execute("SELECT 1 FROM hub_account_callsign WHERE project_id=? AND callsign=?",
                                  (principal.project_id, principal.callsign)).fetchone()
            if linked:
                row = conn.execute("SELECT account_id FROM hub_account_callsign WHERE project_id=? AND callsign=?",
                                   (principal.project_id, principal.callsign)).fetchone()
                if row["account_id"] == account_id:
                    return {"project_id": principal.project_id, "callsign": principal.callsign, "unchanged": True}
                raise HubError(409, "callsign_already_linked", "이 사람 콜사인은 다른 허브 계정에 연결됐다")
            conn.execute("INSERT INTO hub_account_callsign(account_id,project_id,callsign,linked_at) VALUES(?,?,?,?)",
                         (account_id, principal.project_id, principal.callsign, _iso(now)))
        return {"project_id": principal.project_id, "callsign": principal.callsign}

    def account(self, token: str | None, now: datetime) -> dict[str, Any] | None:
        if not token:
            return None
        with self.store.read() as conn:
            row = conn.execute("SELECT a.id,a.username,a.display_name FROM hub_account_session s JOIN hub_account a ON a.id=s.account_id "
                               "WHERE s.token_hash=? AND s.revoked_at IS NULL AND s.expires_at>? AND a.active=1",
                               (hash_token(token), _iso(now))).fetchone()
        return dict(row) if row else None

    def callsign(self, account_id: str, project_id: str, now: datetime) -> Principal | None:
        with self.store.read() as conn:
            row = conn.execute("SELECT c.project_id,c.id,c.kind,c.human_approved,c.role,c.label,a.username "
                               "FROM hub_account_callsign l JOIN callsign c ON c.project_id=l.project_id AND c.id=l.callsign "
                               "JOIN hub_account a ON a.id=l.account_id "
                               "WHERE l.account_id=? AND l.project_id=? AND c.revoked_at IS NULL",
                               (account_id, project_id)).fetchone()
        if not row:
            return None
        return Principal(kind="callsign", project_id=row["project_id"], callsign=row["id"],
                         callsign_kind=row["kind"], human_approved=bool(row["human_approved"]),
                         role=row["role"], name=row["label"], auth_mode="account", account_name=row["username"])

    def projects(self, account_id: str) -> list[str]:
        with self.store.read() as conn:
            return [str(r["project_id"]) for r in conn.execute(
                "SELECT DISTINCT project_id FROM hub_account_callsign WHERE account_id=? ORDER BY project_id", (account_id,))]

    def logout(self, token: str | None, now: datetime) -> None:
        if token:
            with self.store.write() as conn:
                conn.execute("UPDATE hub_account_session SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL",
                             (_iso(now), hash_token(token)))
