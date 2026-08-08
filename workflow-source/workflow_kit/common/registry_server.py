"""registry HTTP serving — federation 의 *쓰기* 쪽 (v1.1.2+, TASK-022)

TASK-016 이 federation 의 *읽기* (`pull_remote_registry`) 를 닫았지만, 상대편이
없었다 — 읽을 곳을 아무도 서빙하지 않으니 `endpoint` 는 사실상 `file://` 로만
쓸 수 있었다. 본 모듈이 그 반대편이다.

**서빙하는 것은 registry 파일 하나뿐이다.** `http.server` 의
`SimpleHTTPRequestHandler` 를 쓰지 않는다 — 그건 디렉터리를 통째로 노출하고
path traversal 표면을 함께 들여온다. 여기서는 경로 2개(`/registry.json`,
`/healthz`)만 알고 나머지는 404 다.

기본값이 loopback 인 이유: registry 에는 워크스페이스 **절대 경로와 브랜치 이름**
이 들어 있다. 파일 자체는 0o600 으로 보호하면서 HTTP 로는 0.0.0.0 에 열어 두면
그 보호가 무의미해진다. 외부 bind 는 명시적으로 골라야 하고, 그때는 경고한다.

인증은 `token_env` — **환경변수 이름** 을 받고 값은 안 받는다. `--token=SECRET`
형태를 지원하지 않는 이유는 `ps` / shell history 에 그대로 남기 때문이다.

Public API:
    RegistryRequestHandler          — BaseHTTPRequestHandler 하위
    build_handler(...)              — 설정을 담은 handler class 를 만든다
    serve_registry(...)             — blocking serve
    is_loopback(host) -> bool
"""

from __future__ import annotations

import hmac
import ipaddress
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Final


#: 서빙하는 경로. 이 둘 외에는 전부 404 — 파일 시스템을 탐색하지 않는다.
REGISTRY_ROUTE: Final[str] = "/registry.json"
HEALTH_ROUTE: Final[str] = "/healthz"

DEFAULT_BIND: Final[str] = "127.0.0.1"
DEFAULT_PORT: Final[int] = 8765


def is_loopback(host: str) -> bool:
    """bind 주소가 loopback 인지. 이름(`localhost`)과 IP 둘 다 받는다."""
    if host in ("localhost", ""):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _read_registry(registry_path: Path) -> tuple[bytes, str | None]:
    """registry 파일을 읽어 (body, error) 로 돌려준다.

    파일이 없으면 *빈 registry* 를 만든다 — 아직 아무 워크스페이스도 등록 안 한
    호스트도 federation 참여자로서는 정상이고, pull 측은 `entries: []` 를 문제
    없이 먹는다. 404 로 답하면 상대가 *호스트 자체가 죽었다* 고 오해한다.
    """
    if not registry_path.is_file():
        empty: dict[str, Any] = {"host_id": "", "entries": [], "updated_at": ""}
        return json.dumps(empty, ensure_ascii=False).encode("utf-8"), None
    try:
        raw = registry_path.read_bytes()
    except OSError as e:
        return b"", f"{type(e).__name__}: {e}"
    # 깨진 JSON 을 그대로 흘리면 상대가 JSONDecodeError 로만 알게 된다. 여기서 본다.
    try:
        json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as e:
        return b"", f"registry is not valid JSON: {e}"
    return raw, None


def build_handler(
    *,
    registry_path: Path,
    token_env: str = "",
    quiet: bool = False,
) -> type[BaseHTTPRequestHandler]:
    """설정을 클로저로 담은 handler class 를 만든다.

    Args:
        registry_path: 서빙할 registry 파일.
        token_env: 비어 있지 않으면 `Authorization: Bearer <값>` 을 요구한다.
                   여기 담기는 건 환경변수 *이름* 이고, 값은 요청마다 읽는다.
        quiet: access log 억제.
    """
    expected_token = os.environ.get(token_env, "") if token_env else ""

    class RegistryRequestHandler(BaseHTTPRequestHandler):
        server_version = "workflow_kit_registry/1.1.2"
        # HTTP/1.0 로 두면 매 요청 연결이 끊긴다. pull 은 단발성이라 그래도 되지만
        # keep-alive 가 없으면 Content-Length 를 반드시 보내야 한다 — 아래에서 항상 보낸다.
        protocol_version = "HTTP/1.1"

        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            # registry 는 자주 바뀐다. 중간 캐시가 오래된 뷰를 주면 confidence 판정이
            # 통째로 거짓말이 된다 (§0.8 #2 의 fresh/stale 은 last_seen_at 을 믿는다).
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _send_json(self, code: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(code, body, "application/json; charset=utf-8")

        def _authorized(self) -> bool:
            if not token_env:
                return True
            header = self.headers.get("Authorization", "")
            prefix = "Bearer "
            if not header.startswith(prefix):
                return False
            supplied = header[len(prefix):]
            # 길이/내용 비교를 상수 시간으로 — 토큰 비교에서 조기 리턴은 피한다.
            return bool(expected_token) and hmac.compare_digest(supplied, expected_token)

        def do_GET(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler 규약
            route = self.path.split("?", 1)[0].rstrip("/") or "/"

            if route == HEALTH_ROUTE:
                # health 는 인증 없이 답한다 — 살아있는지 여부에 비밀이 없고,
                # 운영자가 토큰 없이 확인할 수 있어야 한다.
                self._send_json(200, {"ok": True, "service": "workflow_kit-registry"})
                return

            if route != REGISTRY_ROUTE:
                self._send_json(404, {"ok": False, "error": "not found"})
                return

            if not self._authorized():
                self._send_json(401, {"ok": False, "error": "unauthorized"})
                return

            body, error = _read_registry(registry_path)
            if error is not None:
                self._send_json(500, {"ok": False, "error": error})
                return
            self._send(200, body, "application/json; charset=utf-8")

        def do_HEAD(self) -> None:  # noqa: N802
            self.do_GET()

        def _reject_write(self) -> None:
            self.send_response(405)
            self.send_header("Allow", "GET, HEAD")
            self.send_header("Content-Length", "0")
            self.end_headers()

        # read-only 서버다. 쓰기 메서드는 전부 405 — federation 은 *읽어서 판단* 하는
        # 모델이고, 원격이 남의 registry 를 고칠 수 있으면 그 모델이 무너진다.
        do_POST = _reject_write
        do_PUT = _reject_write
        do_DELETE = _reject_write
        do_PATCH = _reject_write

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            if not quiet:
                super().log_message(format, *args)

    return RegistryRequestHandler


def serve_registry(
    *,
    registry_path: Path,
    bind: str = DEFAULT_BIND,
    port: int = DEFAULT_PORT,
    token_env: str = "",
    quiet: bool = False,
    server_class: type[ThreadingHTTPServer] = ThreadingHTTPServer,
) -> ThreadingHTTPServer:
    """서버를 만들어 돌려준다 (아직 serve 하지 않는다).

    caller 가 `serve_forever()` 를 부른다 — 그래야 테스트가 thread 에서 띄우고
    `shutdown()` 으로 정확히 접을 수 있다.
    """
    handler = build_handler(
        registry_path=registry_path, token_env=token_env, quiet=quiet
    )
    return server_class((bind, port), handler)
