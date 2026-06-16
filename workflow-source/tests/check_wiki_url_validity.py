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


# --- 메인 실행 ---


def main() -> int:
    test_funcs = [
        test_url_https_only_accept,
        test_url_scheme_reject,
        test_url_localhost_reject,
        test_url_private_ip_reject,
        test_url_credentials_reject,
        test_url_path_traversal_reject,
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
