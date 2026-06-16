"""workflow_kit.url_validity helper smoke test (v0.7.35+, V-R10 PoC).

V-R10 rule: URL validity (offline 8 check + optional online HEAD). ADR-010 채택.
PoC 단계: 6 test 로 offline 8 check 검증 (online layer 별도 turn).

Test list:
1. test_url_https_only_accept: https:// 만 accept, http:// reject
2. test_url_scheme_reject: ftp://, file://, javascript: reject
3. test_url_localhost_reject: localhost, 127.0.0.1, ::1 reject
4. test_url_private_ip_reject: 10.0.0.0/8, 192.168.0.0/16, 172.16.0.0/12 reject
5. test_url_credentials_reject: user:pass@host reject
6. test_url_path_traversal_reject: ../../etc/passwd reject
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
URL_VALIDITY = SOURCE_ROOT / "workflow_kit" / "url_validity.py"


def _import_url_validity():
    """url_validity module importlib 로 load."""
    import sys
    spec = importlib.util.spec_from_file_location("url_validity", str(URL_VALIDITY))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["url_validity"] = mod
    spec.loader.exec_module(mod)
    return mod


# --- Test 1: https only accept ---


def test_url_https_only_accept() -> None:
    """`https://` 만 accept. `http://` reject (downgrade attack 방지)."""
    mod = _import_url_validity()
    issues = mod.check_url("https://example.com/spec.md")
    # https 만, 다른 check 모두 pass
    errors = [i for i in issues if i.severity == "error"]
    assert not errors, f"https URL should pass: {errors}"
    issues_http = mod.check_url("http://example.com/spec.md")
    errors_http = [i for i in issues_http if i.severity == "error"]
    assert any("scheme" in i.message.lower() or "https" in i.message.lower() for i in errors_http), (
        f"http:// should be rejected: {errors_http}"
    )


# --- Test 2: ftp/file/javascript reject ---


def test_url_scheme_reject() -> None:
    """`ftp://`, `file://`, `javascript:` scheme reject."""
    mod = _import_url_validity()
    for bad in ("ftp://example.com/spec.md", "file:///etc/passwd", "javascript:alert(1)"):
        issues = mod.check_url(bad)
        errors = [i for i in issues if i.severity == "error"]
        assert errors, f"{bad!r} should produce errors, got: {issues}"


# --- Test 3: localhost reject ---


def test_url_localhost_reject() -> None:
    """`localhost`, `127.0.0.1`, `::1` reject (SSRF 방지)."""
    mod = _import_url_validity()
    for bad in ("https://localhost/spec.md", "https://127.0.0.1/spec.md", "https://[::1]/spec.md"):
        issues = mod.check_url(bad)
        errors = [i for i in issues if i.severity == "error"]
        assert any(
            kw in i.message.lower()
            for i in errors
            for kw in ("localhost", "loopback", "private", "internal")
        ), f"{bad!r} should reject localhost, got: {issues}"

# --- Test 4: private IP reject ---


def test_url_private_ip_reject() -> None:
    """private IP 대역 (10/8, 192.168/16, 172.16/12, fc00::/7) reject."""
    mod = _import_url_validity()
    for bad in (
        "https://10.0.0.1/spec.md",
        "https://192.168.1.1/spec.md",
        "https://172.16.0.1/spec.md",
        "https://[fc00::1]/spec.md",
    ):
        issues = mod.check_url(bad)
        errors = [i for i in issues if i.severity == "error"]
        assert any("private" in i.message.lower() or "internal" in i.message.lower() for i in errors), (
            f"{bad!r} should reject private IP, got: {issues}"
        )


# --- Test 5: credentials reject ---


def test_url_credentials_reject() -> None:
    """`user:pass@host` 형태의 credentials in URL reject (security)."""
    mod = _import_url_validity()
    issues = mod.check_url("https://user:pass@example.com/spec.md")
    errors = [i for i in issues if i.severity == "error"]
    assert any("credential" in i.message.lower() or "user" in i.message.lower() for i in errors), (
        f"credential URL should be rejected, got: {issues}"
    )


# --- Test 6: path traversal reject ---


def test_url_path_traversal_reject() -> None:
    """path 에 `..` segment 포함 시 reject."""
    mod = _import_url_validity()
    issues = mod.check_url("https://example.com/a/../../etc/passwd")
    errors = [i for i in issues if i.severity == "error"]
    assert any("traversal" in i.message.lower() or ".." in i.message for i in errors), (
        f"path traversal URL should be rejected, got: {issues}"
    )


# --- Test 7-12: Online HEAD layer (ADR-012) ---

import socket
import ssl
import urllib.error
from io import BytesIO


class _MockHTTPResponse:
    """Minimal mock for urllib.request.urlopen return value."""

    def __init__(self, status: int, headers: dict[str, str] | None = None):
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, *args):
        return b""


def _patch_urlopen(monkeypatch, mod, side_effect):
    """Replace urlopen with a mock returning the given side_effect."""
    monkeypatch.setattr(mod, "check_url_online", None)  # noop
    # patch urllib.request.urlopen via the module's import
    import urllib.request
    monkeypatch.orig_urlopen = urllib.request.urlopen
    urllib.request.urlopen = lambda *a, **kw: side_effect()
    return urllib.request


def test_online_http_200_pass() -> None:
    """HTTP 200 → pass (no issues)."""
    import urllib.request
    mod = _import_url_validity()

    orig = urllib.request.urlopen
    urllib.request.urlopen = lambda req, **kw: _MockHTTPResponse(200)
    try:
        issues = mod.check_url_online("https://example.com/spec.md", timeout=5.0)
        assert not issues, f"expected no issues for 200, got: {issues}"
    finally:
        urllib.request.urlopen = orig


def test_online_http_404_stale() -> None:
    """HTTP 404 → ERROR (stale URL)."""
    import urllib.request
    mod = _import_url_validity()

    orig = urllib.request.urlopen
    urllib.request.urlopen = lambda req, **kw: _MockHTTPResponse(404)
    try:
        issues = mod.check_url_online("https://example.com/spec.md", timeout=5.0)
        errors = [i for i in issues if i.severity == "error"]
        assert any("404" in i.message or "stale" in i.message.lower() for i in errors), (
            f"404 should be error, got: {issues}"
        )
    finally:
        urllib.request.urlopen = orig


def test_online_http_500_warn() -> None:
    """HTTP 500 → WARN (transient)."""
    import urllib.request
    mod = _import_url_validity()

    orig = urllib.request.urlopen
    urllib.request.urlopen = lambda req, **kw: _MockHTTPResponse(500)
    try:
        issues = mod.check_url_online("https://example.com/spec.md", timeout=5.0)
        warns = [i for i in issues if i.severity == "warn"]
        assert any("500" in i.message or "server error" in i.message.lower() for i in warns), (
            f"500 should be warn, got: {issues}"
        )
    finally:
        urllib.request.urlopen = orig


def test_online_timeout_warn() -> None:
    """Connection timeout → WARN (slow host)."""
    import urllib.request
    mod = _import_url_validity()

    orig = urllib.request.urlopen
    def _timeout(*a, **kw):
        raise socket.timeout("read timeout")
    urllib.request.urlopen = _timeout
    try:
        issues = mod.check_url_online("https://example.com/spec.md", timeout=5.0)
        warns = [i for i in issues if i.severity == "warn"]
        assert any("timeout" in i.message.lower() for i in warns), f"timeout should be warn, got: {issues}"
    finally:
        urllib.request.urlopen = orig


def test_online_tls_error_reject() -> None:
    """TLS error → ERROR (security risk)."""
    import urllib.request
    mod = _import_url_validity()

    orig = urllib.request.urlopen
    def _tls_fail(*a, **kw):
        raise ssl.SSLError("certificate verify failed")
    urllib.request.urlopen = _tls_fail
    try:
        issues = mod.check_url_online("https://example.com/spec.md", timeout=5.0)
        errors = [i for i in issues if i.severity == "error"]
        assert any("TLS" in i.message or "ssl" in i.message.lower() for i in errors), (
            f"TLS error should be error, got: {issues}"
        )
    finally:
        urllib.request.urlopen = orig


def test_online_dns_failure_reject() -> None:
    """DNS failure → ERROR (host does not exist)."""
    import urllib.request
    mod = _import_url_validity()

    orig = urllib.request.urlopen
    def _dns_fail(*a, **kw):
        raise urllib.error.URLError("Name or service not known")
    urllib.request.urlopen = _dns_fail
    try:
        issues = mod.check_url_online("https://example.com/spec.md", timeout=5.0)
        errors = [i for i in issues if i.severity == "error"]
        assert any("DNS" in i.message or "url error" in i.message.lower() or "Name" in i.message for i in errors), (
            f"DNS failure should be error, got: {issues}"
        )
    finally:
        urllib.request.urlopen = orig


# --- 메인 실행 ---


def main() -> int:
    test_funcs = [
        test_url_https_only_accept,
        test_url_scheme_reject,
        test_url_localhost_reject,
        test_url_private_ip_reject,
        test_url_credentials_reject,
        test_url_path_traversal_reject,
        test_online_http_200_pass,
        test_online_http_404_stale,
        test_online_http_500_warn,
        test_online_timeout_warn,
        test_online_tls_error_reject,
        test_online_dns_failure_reject,
    ]
    failed: list[str] = []
    for fn in test_funcs:
        name = fn.__name__
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed.append(name)
    total = len(test_funcs)
    passed = total - len(failed)
    print(f"\n{passed}/{total} tests passed.")
    if failed:
        print(f"\n{len(failed)} tests failed:")
        for name in failed:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
