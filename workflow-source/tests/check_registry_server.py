"""registry HTTP server smoke (TASK-2026-08-09-main-003, federation §7.4 *쓰기*)

TASK-016 은 pull(*읽기*) 을 닫았지만 서빙하는 쪽이 없어 `http://` endpoint 는
문서상의 형식일 뿐이었다. 본 검사는 **실제로 서버를 띄우고 pull 로 되받아** 왕복이
성립하는지 본다 — 서버 단독 응답만 보면 `_fetch_url` 쪽 계약 위반을 놓친다.

검증 케이스 (11):
    1. GET /registry.json — 200, 파일 내용 그대로
    2. GET /healthz — 200, 인증 없이도 답한다
    3. 알 수 없는 경로 — 404 (파일 시스템 탐색 없음)
    4. POST/PUT/DELETE — 405 + Allow 헤더 (read-only)
    5. 토큰 요구 시 헤더 없음 → 401 / 틀린 토큰 → 401 / 맞는 토큰 → 200
    6. registry 파일 부재 → 빈 registry (404 아님)
    7. pull_remote_registry() 왕복 — 서버 → known_hosts → pull → entries
    8. token_env 왕복 — 서버가 요구하고 pull 이 붙인다
    9. is_loopback() 판정 + KnownHost.token_env 하위호환 (missing → "")
    10. 비-loopback bind 왕복 (TASK-2026-08-10-main-009) — LAN 인터페이스 IP 로
        bind 하고 그 주소로 pull (토큰 포함). 2026-08-09 까지는 loopback 왕복만
        실측이었다. LAN IP 를 못 얻는 호스트는 graceful skip (`--require-lan`
        으로 강제). 진짜 cross-host / 방화벽 / TLS 는 여전히 이 검사 밖이다.
    11. --print-systemd-unit — 상시 가동 unit 출력 (토큰 env 미설정에도 성공,
        인자 반영, EnvironmentFile 은 --token-env 지정 시에만)

Stdlib only. http.server + threading + urllib + socket + tempfile.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import os
import socket
import subprocess
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

    def __init__(self, registry_path: Path, token_env: str = "", bind: str = "127.0.0.1") -> None:
        # port 0 → OS 가 빈 포트를 준다. 고정 포트는 CI 에서 충돌한다.
        self.bind = bind
        self.httpd = S.serve_registry(
            registry_path=registry_path, bind=bind, port=0,
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
        return f"http://{self.bind}:{self.port}{route}"


def _lan_ip() -> str | None:
    """이 호스트의 비-loopback IPv4. 못 얻으면 None (→ case 10 graceful skip).

    UDP connect 는 패킷을 보내지 않는다 — 목적지는 TEST-NET-1 (RFC 5737) 이라
    실제로 닿을 일도 없고, OS 가 라우팅으로 고를 source IP 만 얻는다.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("192.0.2.1", 9))
            ip = str(sock.getsockname()[0])
    except OSError:
        return None
    return None if S.is_loopback(ip) else ip


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
    ran = 0

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal ran
        ran += 1
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

            # 10) 비-loopback bind 왕복 — 2026-08-09 까지는 loopback 만 실측이었다.
            #     LAN IP 부재(오프라인 컨테이너 등)는 skip — 모름 ≠ 실패.
            #     cross-host / 방화벽 / TLS 는 여기서 못 본다 (darwin homelab 몫).
            lan_ip = _lan_ip()
            if lan_ip is None:
                msg = (
                    "SKIP: 10) 비-loopback bind — 이 호스트의 LAN IPv4 를 못 얻었다. "
                    "강제하려면 --require-lan."
                )
                if "--require-lan" in sys.argv:
                    print(f"FAIL(require-lan): {msg}")
                    failures.append("10) 비-loopback bind (require-lan)")
                    ran += 1
                else:
                    print(msg)
            else:
                with _Server(reg_file, token_env="WK_TEST_TOKEN", bind=lan_ip) as srv:
                    code, body, _ = _get(srv.url(), token="s3cret-value")
                    direct_ok = code == 200 and json.loads(body) == SAMPLE_REGISTRY

                    R.add_known_host("hostLan", srv.url(), token_env="WK_TEST_TOKEN")
                    lan_result = R.pull_remote_registry("hostLan", timeout=5, use_cache=False)
                    lan_entries = lan_result.get("registry", {}).get("entries", [])
                    check(
                        f"10) 비-loopback bind 왕복 ({lan_ip}) — GET + pull + 토큰",
                        direct_ok
                        and lan_result.get("ok") is True
                        and len(lan_entries) == 1,
                        f"direct code={code} pull_ok={lan_result.get('ok')} "
                        f"err={lan_result.get('error')}",
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

    # 11) --print-systemd-unit — 상시 가동의 실행 가능 경로 (TASK-2026-08-12-main-001).
    # 토큰 env 가 *비어 있어도* unit 출력은 성공해야 한다 (실행 시점에
    # EnvironmentFile 로 공급). ExecStart 는 인자를 그대로 실어야 한다.
    unit_env = {k: v for k, v in os.environ.items() if k != "WK_REGISTRY_TOKEN"}
    unit_env["PYTHONPATH"] = str(SOURCE_ROOT)
    proc = subprocess.run(
        [sys.executable, str(SOURCE_ROOT / "workflow_kit" / "tools" / "host_serve_registry.py"),
         "--print-systemd-unit", "--bind", "192.168.1.10", "--port", "8765",
         "--token-env", "WK_REGISTRY_TOKEN"],
        capture_output=True, text=True, timeout=30, env=unit_env,
    )
    unit_ok = (
        proc.returncode == 0
        and "[Service]" in proc.stdout
        and "--bind 192.168.1.10" in proc.stdout
        and "--port 8765" in proc.stdout
        and "--token-env WK_REGISTRY_TOKEN" in proc.stdout
        and "EnvironmentFile=%h/.config/workflow_kit/registry_server.env" in proc.stdout
        and "WantedBy=default.target" in proc.stdout
    )
    proc_no_token = subprocess.run(
        [sys.executable, str(SOURCE_ROOT / "workflow_kit" / "tools" / "host_serve_registry.py"),
         "--print-systemd-unit"],
        capture_output=True, text=True, timeout=30, env=unit_env,
    )
    no_token_ok = (
        proc_no_token.returncode == 0
        and "EnvironmentFile" not in proc_no_token.stdout  # 토큰 없으면 env file 도 없다
    )
    check(
        "11) --print-systemd-unit (토큰 미설정에도 출력 + 인자 반영 + EnvironmentFile 유무)",
        unit_ok and no_token_ok,
        f"rc={proc.returncode}/{proc_no_token.returncode}\n{proc.stdout[:300]}",
    )

    print()
    if failures:
        print(f"{ran - len(failures)}/{ran} PASS — FAILED: {failures}")
        return 1
    print(f"{ran}/{ran} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
