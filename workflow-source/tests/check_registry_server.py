"""registry HTTP server smoke (TASK-2026-08-09-main-003, federation §7.4 *쓰기*)

TASK-016 은 pull(*읽기*) 을 닫았지만 서빙하는 쪽이 없어 `http://` endpoint 는
문서상의 형식일 뿐이었다. 본 검사는 **실제로 서버를 띄우고 pull 로 되받아** 왕복이
성립하는지 본다 — 서버 단독 응답만 보면 `_fetch_url` 쪽 계약 위반을 놓친다.

검증 케이스 (9):
    1. GET /registry.json — 200, 파일 내용 그대로
    2. GET /healthz — 200, 인증 없이도 답한다
    3. 알 수 없는 경로 — 404 (파일 시스템 탐색 없음)
    4. POST/PUT/DELETE — 405 + Allow 헤더 (read-only)
    5. 토큰 요구 시 헤더 없음 → 401 / 틀린 토큰 → 401 / 맞는 토큰 → 200
    6. registry 파일 부재 → 빈 registry (404 아님)
    7. pull_remote_registry() 왕복 — 서버 → known_hosts → pull → entries
    8. token_env 왕복 — 서버가 요구하고 pull 이 붙인다
    9. is_loopback() 판정 + KnownHost.token_env 하위호환 (missing → "")

Stdlib only. http.server + threading + urllib + tempfile.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import registry_server as S  # noqa: E402
from workflow_kit.common import workspace_registry as R  # noqa: E402

SAMPLE_REGISTRY = {
    "host_id": "hostA",
    "updated_at": "2026-08-09T00:00:00Z",
    "entries": [
        {
            "path": "/tmp/ws-a",
            "branch": "feature/a",
            "harness": "claude-code",
            "last_seen_at": "2026-08-09T00:00:00Z",
            "source_host_id": "hostA",
        }
    ],
}


class _Server:
    """thread 에서 띄우고 확실히 접는다."""

    def __init__(self, registry_path: Path, token_env: str = "") -> None:
        # port 0 → OS 가 빈 포트를 준다. 고정 포트는 CI 에서 충돌한다.
        self.httpd = S.serve_registry(
            registry_path=registry_path, bind="127.0.0.1", port=0,
            token_env=token_env, quiet=True,
        )
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self) -> "_Server":
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)

    def url(self, route: str = S.REGISTRY_ROUTE) -> str:
        return f"http://127.0.0.1:{self.port}{route}"


def _get(url: str, *, token: str | None = None, method: str = "GET") -> tuple[int, bytes, dict]:
    req = urllib.request.Request(url, method=method)
    if token is not None:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def main() -> int:
    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        if cond:
            print(f"PASS: {label}")
        else:
            print(f"FAIL: {label} — {detail}")
            failures.append(label)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        reg_file = tmp / "registry.json"
        reg_file.write_text(json.dumps(SAMPLE_REGISTRY), encoding="utf-8")

        # 1~4) 인증 없는 서버
        with _Server(reg_file) as srv:
            code, body, _ = _get(srv.url())
            check(
                "1) GET /registry.json → 200 + 내용 일치",
                code == 200 and json.loads(body) == SAMPLE_REGISTRY,
                f"code={code}",
            )

            code, body, _ = _get(srv.url(S.HEALTH_ROUTE))
            check(
                "2) GET /healthz → 200 (인증 불요)",
                code == 200 and json.loads(body).get("ok") is True,
                f"code={code}",
            )

            code, _, _ = _get(srv.url("/etc/passwd"))
            code2, _, _ = _get(srv.url("/../registry.json"))
            check(
                "3) 알 수 없는 경로 → 404 (탐색 없음)",
                code == 404 and code2 == 404,
                f"codes={code}/{code2}",
            )

            codes = {}
            for method in ("POST", "PUT", "DELETE", "PATCH"):
                c, _, headers = _get(srv.url(), method=method)
                codes[method] = (c, headers.get("Allow"))
            check(
                "4) 쓰기 메서드 → 405 + Allow",
                all(c == 405 and allow == "GET, HEAD" for c, allow in codes.values()),
                f"codes={codes}",
            )

        # 5) 토큰 요구
        os.environ["WK_TEST_TOKEN"] = "s3cret-value"
        with _Server(reg_file, token_env="WK_TEST_TOKEN") as srv:
            no_hdr, _, _ = _get(srv.url())
            wrong, _, _ = _get(srv.url(), token="wrong")
            right, body, _ = _get(srv.url(), token="s3cret-value")
            health, _, _ = _get(srv.url(S.HEALTH_ROUTE))
            check(
                "5) 토큰: 없음 401 / 오답 401 / 정답 200 / health 200",
                no_hdr == 401 and wrong == 401 and right == 200 and health == 200,
                f"no_hdr={no_hdr} wrong={wrong} right={right} health={health}",
            )

        # 6) registry 파일 부재 → 빈 registry
        with _Server(tmp / "does-not-exist.json") as srv:
            code, body, _ = _get(srv.url())
            parsed = json.loads(body) if code == 200 else {}
            check(
                "6) registry 부재 → 200 + 빈 entries (404 아님)",
                code == 200 and parsed.get("entries") == [],
                f"code={code} body={body[:80]!r}",
            )

        # 7~8) pull 왕복. registry / known_hosts 경로를 tmp 로 돌려 실제 파일을 안 건드린다.
        old_env = {
            k: os.environ.get(k)
            for k in ("WORKFLOW_REGISTRY_PATH", "WORKFLOW_KNOWN_HOSTS_PATH", "XDG_CACHE_HOME")
        }
        try:
            os.environ["XDG_CACHE_HOME"] = str(tmp / "cache")
            os.environ["WORKFLOW_REGISTRY_PATH"] = str(tmp / "local-registry.json")
            os.environ.pop("WORKFLOW_KNOWN_HOSTS_PATH", None)

            with _Server(reg_file) as srv:
                R.add_known_host("hostA", srv.url())
                result = R.pull_remote_registry("hostA", timeout=5, use_cache=False)
                entries = result.get("registry", {}).get("entries", [])
                check(
                    "7) pull_remote_registry() 왕복 성공",
                    result.get("ok") is True and len(entries) == 1,
                    f"result={ {k: v for k, v in result.items() if k != 'registry'} }",
                )

            with _Server(reg_file, token_env="WK_TEST_TOKEN") as srv:
                R.add_known_host("hostB", srv.url(), token_env="WK_TEST_TOKEN")
                ok_result = R.pull_remote_registry("hostB", timeout=5, use_cache=False)

                # 토큰 이름을 비운 채로 등록하면 같은 서버라도 401 이어야 한다.
                R.add_known_host("hostC", srv.url())
                bad_result = R.pull_remote_registry("hostC", timeout=5, use_cache=False)
                check(
                    "8) token_env 왕복 — 붙이면 성공, 없으면 401",
                    ok_result.get("ok") is True and bad_result.get("ok") is False,
                    f"ok={ok_result.get('ok')} bad={bad_result.get('error')}",
                )
        finally:
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            os.environ.pop("WK_TEST_TOKEN", None)

    # 9) is_loopback + 하위호환
    loopback_ok = (
        S.is_loopback("127.0.0.1")
        and S.is_loopback("localhost")
        and S.is_loopback("::1")
        and not S.is_loopback("0.0.0.0")
        and not S.is_loopback("192.168.1.10")
    )
    legacy = R.KnownHost.from_dict({"host_id": "old", "endpoint": "file:///tmp/x"})
    check(
        "9) is_loopback 판정 + token_env 하위호환 (missing → \"\")",
        loopback_ok and legacy.token_env == "",
        f"loopback_ok={loopback_ok} token_env={legacy.token_env!r}",
    )

    total = 9
    print()
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
