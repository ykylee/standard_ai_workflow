"""HTTP pull smoke (TASK-2026-08-08-main-016, federation §7.4 *읽기* 마무리)

known_hosts 의 endpoint 를 따라가서 원격 registry 를 fetch + cache + merge_entries
로 합치는 정공법 검증. stdlib only. `http.server` 를 thread 에 띄워 실제 HTTP pull
경로를 실측 (urllib 의 mock ❌ — 진짜 round-trip).

검증 케이스 (8):
    1. known_hosts 미등록 host → 즉시 error
    2. http.server in thread — 정상 registry JSON pull, cache 저장
    3. unreachable host (offline port) → cache fallback (성공)
    4. unreachable host + cache 부재 → error + from_cache=False
    5. malformed JSON response → error (cache 도 없으면)
    6. file:// URL (test only) — absolute path 검증
    7. merge_with_remotes — local + remote 합치기, source_host_id 보존
    8. cache TTL 만료 → cache 미사용 + 새 fetch

Stdlib only. `urllib.request` + `http.server` + `threading` + `tempfile`.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import http.server
import json
import socketserver
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import workspace_registry as R  # noqa: E402


def _make_registry_json(entries: list[dict], host_id: str = "remote-host") -> dict:
    return {
        "schema_version": "1",
        "host_id": host_id,
        "updated_at": "2026-08-08T22:00:00Z",
        "entries": entries,
    }


def _entry_dict(path: str, branch: str, host_id: str, days_ago: int = 1) -> dict:
    seen = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    return {
        "path": path,
        "branch": branch,
        "harness": "test",
        "endpoint": None,
        "registered_at": "2026-08-01T00:00:00Z",
        "last_seen_at": seen,
        "env": {},
        "source_host_id": host_id,
    }


class _RegistryHandler(http.server.BaseHTTPRequestHandler):
    """테스트용 HTTP server. ``self.registry_payload`` 가 응답.

    URL path 별 응답:
      ``/registry.json``         → 200 + self.registry_payload
      ``/malformed``             → 200 + "NOT JSON AT ALL"
      ``/slow``                  → time.sleep(self.delay) 후 응답 (timeout 검증)
    """

    registry_payload: dict = {}
    malformed: bool = False
    delay: float = 0.0

    def do_GET(self) -> None:  # noqa: N802 — http.server API
        if self.path == "/registry.json":
            if self.delay > 0:
                time.sleep(self.delay)
            body = json.dumps(self.registry_payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/malformed":
            body = b"NOT JSON AT ALL"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/slow":
            time.sleep(self.delay if self.delay > 0 else 5.0)
            body = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args, **kwargs) -> None:  # noqa: ANN001 — silence
        pass


def _start_server(registry_payload: dict | None = None, *, delay: float = 0.0) -> tuple[http.server.ThreadingHTTPServer, str]:
    """threading HTTP server 1개 띄우기. ``(server, base_url)`` 반환.

    caller 가 ``server.shutdown()`` + ``server.server_close()`` 로 정리.
    """
    if registry_payload is None:
        registry_payload = _make_registry_json([_entry_dict("/wt/a", "feat-a", "remote-host")])
    _RegistryHandler.registry_payload = registry_payload
    _RegistryHandler.delay = delay

    class _ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    server = _ThreadedServer(("127.0.0.1", 0), _RegistryHandler)
    host, port = server.server_address
    base_url = f"http://{host}:{port}"
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, base_url


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        # 격리: known_hosts + remote_cache 모두 tempdir 로
        known_hosts_file = Path(tmp) / "known_hosts.json"
        remote_cache_dir = Path(tmp) / "remote_cache"
        from unittest import mock

        with mock.patch.object(R, "known_hosts_path", lambda: known_hosts_file), \
             mock.patch.object(R, "remote_cache_path", lambda h: remote_cache_dir / f"{h}.json"):
            R._remote_cache_dir = lambda: remote_cache_dir  # internal hook
            remote_cache_dir.mkdir(parents=True, exist_ok=True)

            # 1) known_hosts 미등록 host → 즉시 error
            res = R.pull_remote_registry("not-registered-host", use_cache=False)
            if res.get("ok") is not False:
                failures.append(f"[1] not-registered: expected ok=False, got {res}")
            elif "not in known_hosts" not in res.get("error", ""):
                failures.append(f"[1] not-registered: error 메시지 이상, got {res.get('error')!r}")
            else:
                print("  [1] not-registered  ✓  (미등록 host → 즉시 error, no-op)")

            # 2) http.server — 정상 registry pull + cache 저장
            payload = _make_registry_json([
                _entry_dict("/wt/feat-x", "feat-x", "remote-A"),
                _entry_dict("/wt/feat-y", "feat-y", "remote-A", days_ago=3),
            ])
            server, base = _start_server(payload)
            try:
                R.add_known_host("remote-A", f"{base}/registry.json")
                res = R.pull_remote_registry("remote-A", use_cache=False)
                if not res.get("ok"):
                    failures.append(f"[2] http pull: expected ok=True, got {res}")
                elif res.get("from_cache"):
                    failures.append(f"[2] http pull: from_cache should be False, got {res}")
                elif not remote_cache_dir.joinpath("remote-A.json").is_file():
                    failures.append(f"[2] http pull: cache file not created")
                else:
                    # cache 0o600 확인
                    mode = remote_cache_dir.joinpath("remote-A.json").stat().st_mode & 0o777
                    if mode != 0o600:
                        failures.append(f"[2] http pull: cache perms {oct(mode)} != 0o600")
                    else:
                        # entries count 확인
                        regs = res.get("registry", {}).get("entries", [])
                        if len(regs) != 2:
                            failures.append(f"[2] http pull: expected 2 entries, got {len(regs)}")
                        else:
                            print("  [2] http pull       ✓  (2 entries + cache 0o600 saved)")
            finally:
                server.shutdown()
                server.server_close()

            # 3) unreachable host + cache 있음 → cache fallback (성공)
            # 위 2 의 cache 가 이미 있으니, *다른 offline port* 로 가서 cache miss 를
            # 만들면 4번 케이스가 됨. 여기선 cache 있는 상태에서 unreachable 은
            # 시뮬레이션 어려우니, *cache TTL 을 0 으로* 두고 fetch → 같은 응답.
            # 더 간단: cache 직접 쓴 다음 unreachable URL 로 fetch → cache fallback.
            cached_payload = _make_registry_json(
                [_entry_dict("/wt/cached", "feat-cached", "remote-B", days_ago=10)],
                host_id="remote-B",
            )
            R._save_remote_cache("remote-B", cached_payload)
            R.add_known_host("remote-B", "http://127.0.0.1:1/registry.json")  # port 1 = 거의 안 쓰임
            res = R.pull_remote_registry("remote-B", use_cache=True, timeout=0.5)
            if not res.get("ok"):
                failures.append(f"[3] cache fallback: expected ok=True, got {res}")
            elif not res.get("from_cache"):
                failures.append(f"[3] cache fallback: expected from_cache=True, got {res}")
            else:
                print("  [3] cache fallback  ✓  (unreachable + cache hit → from_cache=True)")

            # 4) unreachable host + cache 부재 → error
            R.add_known_host("remote-C", "http://127.0.0.1:1/registry.json")
            res = R.pull_remote_registry("remote-C", use_cache=True, timeout=0.5)
            if res.get("ok"):
                failures.append(f"[4] unreachable+no-cache: expected ok=False, got {res}")
            elif res.get("from_cache"):
                failures.append(f"[4] unreachable+no-cache: from_cache should be False, got {res}")
            elif "error" not in res:
                failures.append(f"[4] unreachable+no-cache: error key missing, got {res}")
            else:
                print("  [4] unreachable     ✓  (no cache → error, from_cache=False)")

            # 5) malformed JSON
            server, base = _start_server()
            try:
                # /malformed endpoint 는 _RegistryHandler 가 broken JSON 응답
                R.add_known_host("remote-D", f"{base}/malformed")
                res = R.pull_remote_registry("remote-D", use_cache=False, timeout=2.0)
                if res.get("ok"):
                    failures.append(f"[5] malformed: expected ok=False, got {res}")
                elif "JSONDecodeError" not in res.get("error", ""):
                    failures.append(f"[5] malformed: error 메시지 이상, got {res.get('error')!r}")
                else:
                    print("  [5] malformed       ✓  (JSONDecodeError → ok=False)")
            finally:
                server.shutdown()
                server.server_close()

            # 6) file:// URL (test only)
            # 임시 registry.json 파일을 만들어서 file:// 로 fetch
            tmp_registry = Path(tmp) / "served_registry.json"
            tmp_registry.write_text(
                json.dumps(_make_registry_json([_entry_dict("/wt/file-test", "feat-file", "remote-F")])),
                encoding="utf-8",
            )
            R.add_known_host("remote-F", f"file://{tmp_registry}")
            res = R.pull_remote_registry("remote-F", use_cache=False)
            if not res.get("ok"):
                failures.append(f"[6] file:// : expected ok=True, got {res}")
            else:
                regs = res.get("registry", {}).get("entries", [])
                if len(regs) != 1 or regs[0].get("path") != "/wt/file-test":
                    failures.append(f"[6] file:// : wrong payload, got {regs}")
                else:
                    print("  [6] file://         ✓  (local file fetched, 1 entry)")

            # 7) merge_with_remotes — local + remote 합치기, source_host_id 보존
            # known_hosts 를 비우지 않고 (merge_with_remotes 가 모든 known host 를 pull),
            # local entries + remote entries 가 섞인 결과 검증. unreachable host 의
            # error 는 정공법 (errors 리스트에 들어감) — 그것 자체로는 fail 아님.
            local_entries = [
                R.RegistryEntry(
                    path="/wt/local-feat",
                    branch="local-feat",
                    harness="test",
                    last_seen_at=(datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                ),
                # 충돌 entry: cache 의 remote-A 의 /wt/feat-x 와 같은 path.
                # local 의 last_seen 이 더 신선하면 local 우선.
                R.RegistryEntry(
                    path="/wt/feat-x",
                    branch="feat-x",
                    harness="test",
                    last_seen_at=(datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                ),
            ]
            merged, errors = R.merge_with_remotes(local_entries, timeout=2.0)
            # errors 는 *expected* (unreachable hosts) — 검증 ❌. 대신 merged 의
            # 정합성만 확인.
            missing_src = [e.path for e in merged if not e.source_host_id]
            if missing_src:
                failures.append(f"[7] merge: source_host_id missing on {missing_src}")
            # /wt/local-feat, /wt/feat-x (local 우선), /wt/feat-y (remote-A) 가 모두 있어야 함
            paths = {e.path for e in merged}
            if not {"/wt/local-feat", "/wt/feat-x", "/wt/feat-y"}.issubset(paths):
                failures.append(f"[7] merge: missing paths, got {paths}")
            else:
                # local 의 /wt/feat-x 가 remote-A 의 stale /wt/feat-x 보다 우선 (last_seen 최신).
                # winning entry 의 source_host_id 는 local host_id() 로 채워져야 함
                # (legacy source_host_id="" entry 가 merge 시 label 로 fallback — §7.4 정합).
                feat_x = next(e for e in merged if e.path == "/wt/feat-x")
                if feat_x.source_host_id != R.host_id():
                    failures.append(
                        f"[7] merge: /wt/feat-x 의 source_host_id = {feat_x.source_host_id!r} "
                        f"(local host {R.host_id()!r} 우선이어야 함)"
                    )
                else:
                    print(f"  [7] merge_with_remotes  ✓  ({len(merged)} entries, "
                          f"local /wt/feat-x 우선 (source_host_id={feat_x.source_host_id!r}), "
                          f"errors={len(errors)} (unreachable 정상))")

            # 8) cache TTL 만료 → cache 미사용, 새 fetch 시도
            # remote-A 의 cache 를 24h 전 _cached_at 으로 다시 쓰기.
            stale = {
                "_cached_at": (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "_host_id": "remote-A",
                "registry": _make_registry_json(
                    [_entry_dict("/wt/STALE", "feat-stale", "remote-A")],
                    host_id="remote-A",
                ),
            }
            (remote_cache_dir / "remote-A.json").write_text(json.dumps(stale), encoding="utf-8")
            # server 가 다시 떠야 함 (2번에서 shutdown 됨)
            server, base = _start_server()
            try:
                # known_hosts 의 endpoint 가 옛날 server 의 것일 수 있으니 update
                R.add_known_host("remote-A", f"{base}/registry.json")
                res = R.pull_remote_registry("remote-A", use_cache=True, timeout=2.0)
                if not res.get("ok"):
                    failures.append(f"[8] cache TTL: expected ok=True, got {res}")
                elif res.get("from_cache"):
                    failures.append(f"[8] cache TTL: expected from_cache=False (stale), got {res}")
                else:
                    print("  [8] cache TTL       ✓  (24h stale cache 무시 + 새 fetch)")
            finally:
                server.shutdown()
                server.server_close()

    print()
    if failures:
        print(f"FAIL: {len(failures)} case(s) failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL PASS: HTTP pull + remote cache + merge — 8 case (urllib in-process)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
