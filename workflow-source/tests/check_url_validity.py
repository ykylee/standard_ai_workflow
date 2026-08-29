"""workflow_kit.url_validity helper smoke test (v0.7.53+, ADR-010/012/013/018/019/020).

Test list (offline only — online HEAD / GitHub API 는 network 의존이라 skip):
1. test_check_url_https_valid: https://example.com → 0 issue
2. test_check_url_http_rejected: http:// → V-R10-scheme error
3. test_check_url_no_scheme_rejected: example.com → V-R10-scheme error
4. test_check_url_localhost_rejected: localhost host → V-R10-localhost error
5. test_check_url_private_ip_rejected: 192.168.1.1 → V-R10-private-ip error
6. test_check_url_path_traversal_rejected: ../../etc/passwd → V-R10-traversal error
7. test_check_url_file_scheme_rejected: file:// → V-R10-file-scheme error
8. test_check_url_credentials_rejected: user:pass@host → V-R10-credentials error
9. test_check_url_github_form_unusual_warn: github.com URL with unusual 3rd path → warn
10. test_cache_stats_zero_on_empty: empty cache file → 0/0
11. test_cache_clear_idempotent: clear on non-existent file → no error
12. test_cache_file_for_strategy_suffix: per-strategy cache file naming
13. test_cli_accepts_the_flags_ci_actually_passes: okf-validate.yml 의 실제 인자 ↔ 파서 대조
14. test_online_path_parses_and_exposes_cache_attr: --online 경로 파싱 + args.cache 실재
15. test_main_runs_the_ci_invocation_end_to_end: CI 실제 호출을 main() 으로 끝까지 (네트워크만 스텁)

추가 audit (v0.7.53 audit 2차):
- online / cache / semantic_* 함수 **호출**은 *외부 의존* (network, GitHub API) — 명시적 skip
  단, **인자 계약은 오프라인이라 skip 하지 않는다** (13·14). 그 틈으로 `--cache` 등록이
  사라져 `--online` CLI 경로가 7주간 죽어 있었다 (§2.57)
- module 자체는 zero-dep (stdlib only: urllib / socket / ssl / ipaddress)
- 5 caller (workflow_kit_cli, okf_export, okf_import, v_r13_commit_diff, ...) — public surface 정합
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    ".github/workflows/*",
    "workflow-source/workflow_kit/*",
)

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
URL_VALIDITY = SOURCE_ROOT / "workflow_kit" / "url_validity.py"


def _import_url_validity():
    """url_validity module importlib 로 load."""
    spec = importlib.util.spec_from_file_location("url_validity", str(URL_VALIDITY))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["url_validity"] = mod
    spec.loader.exec_module(mod)
    return mod


REPO_ROOT = SOURCE_ROOT.parent
OKF_VALIDATE_WF = REPO_ROOT / ".github" / "workflows" / "okf-validate.yml"


def _flags_ci_passes() -> list[str]:
    """`okf-validate.yml` 이 CLI 에 **실제로 넘기는** 플래그.

    손으로 베낀 목록을 두지 않는다 — 그것은 소비자와 갈라지고, 갈라진 사실이
    안 보인다. 소비자 파일에서 직접 뽑아 파서와 대조한다.
    """
    text = OKF_VALIDATE_WF.read_text(encoding="utf-8")
    flags: list[str] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "workflow_kit.url_validity" not in line:
            continue
        # 백슬래시로 이어지는 셸 명령을 끝까지 모은다.
        chunk = [line]
        j = i
        while lines[j].rstrip().endswith("\\") and j + 1 < len(lines):
            j += 1
            chunk.append(lines[j])
        for token in " ".join(chunk).split():
            if token.startswith("--"):
                flags.append(token.split("=", 1)[0])
    return sorted(set(flags))


def test_cli_accepts_the_flags_ci_actually_passes() -> None:
    """CI 가 넘기는 플래그를 파서가 **전부 안다**.

    **왜 이 case 가 필요한가**: 이 파일 상단이 "online / cache 는 network 의존이라
    명시적 skip" 이라고 적고 있다. 그 판단은 옳지만, *네트워크 의존은 호출을 건너뛸
    이유이지 **인자 계약**을 건너뛸 이유가 아니다* — 파싱은 오프라인이다.

    그 틈으로 실제 사고가 났다: `46b6b7a`(v0.7.41)가 무관한 커밋에서
    `--cache` 등록 한 줄만 지웠고, `main()` 의 `args.cache` 참조와 모듈 docstring 과
    `okf-validate` 워크플로우는 그대로였다. `--online` CLI 경로가 **7주간 통째로**
    죽어 있었는데(주면 `ambiguous option`, 안 주면 `AttributeError`) smoke 232건 중
    아무것도 그 경로를 밟지 않았고, 유일한 소비자는 red 인 채 방치됐다.
    """
    mod = _import_url_validity()
    parser = mod._build_arg_parser()
    known = set(parser._option_string_actions)

    flags = _flags_ci_passes()
    assert flags, f"{OKF_VALIDATE_WF} 에서 CLI 플래그를 못 뽑았다 — 호출 형태가 바뀌었나?"
    unknown = [f for f in flags if f not in known]
    assert not unknown, (
        f"CI 가 넘기는데 파서가 모르는 플래그 {unknown} — CLI 표면이 소비자를 두고 갈라졌다. "
        f"(CI 인자: {flags})"
    )


def _ci_argv(dummy_url: str = "https://example.com") -> list[str]:
    """`okf-validate.yml` 의 **실제 호출 토큰** (URL 은 xargs 가 넣으므로 dummy 로 대체)."""
    lines = OKF_VALIDATE_WF.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if "workflow_kit.url_validity" not in line or "--cache-stats" in line:
            continue
        chunk = [line]
        j = i
        while lines[j].rstrip().endswith("\\") and j + 1 < len(lines):
            j += 1
            chunk.append(lines[j])
        tokens = " ".join(chunk).replace("\\", " ").split()
        tokens = tokens[tokens.index("workflow_kit.url_validity") + 1:]
        if "|" in tokens:                      # `| tee …` 이후는 셸 파이프다
            tokens = tokens[: tokens.index("|")]
        return [dummy_url, *tokens]
    raise AssertionError(f"{OKF_VALIDATE_WF} 에서 CLI 호출을 못 찾았다")


def test_main_runs_the_ci_invocation_end_to_end() -> None:
    """CI 의 **실제 호출을 `main()` 으로 끝까지** 돌린다 (네트워크만 스텁).

    **파싱이 통과한다고 실행이 되는 것이 아니다.** 위 case 두 개는 파서만 봤고,
    그래서 `main()` 이 읽는 `args.max_bytes` 가 없다는 것을 **못 잡았다** — 실제
    CI 호출은 파싱을 지나 `AttributeError: 'Namespace' object has no attribute
    'max_bytes'` 로 죽고 있었다. `--cache`(§2.57)와 완전히 같은 사고가 두 번이다
    (`1da10ef` 가 `--max-bytes` 등록만 지우고 참조는 남겼다).

    네트워크만 스텁하고 **분기와 속성 접근은 전부 실제로 실행**한다 — 스텁이
    호출 시점까지 살아 있어야 하므로 모듈 속성을 직접 갈아 끼운다.
    """
    mod = _import_url_validity()
    argv = _ci_argv()
    assert "--online" in argv and "--cache" in argv, f"CI 호출 추출 실패: {argv}"

    saved = (mod.check_url_with_cache, mod.check_url_online, mod.check_url_body)
    calls: list[str] = []
    try:
        mod.check_url_with_cache = lambda url, **kw: calls.append("cache") or []
        mod.check_url_online = lambda url, **kw: calls.append("online") or []
        mod.check_url_body = lambda url, **kw: calls.append("body") or []
        rc = mod.main(argv)
    finally:
        mod.check_url_with_cache, mod.check_url_online, mod.check_url_body = saved

    assert rc == 0, f"CI 호출이 exit {rc} 로 끝났다 (argv={argv})"
    assert "cache" in calls, f"--cache 인데 캐시 경로를 안 탔다: {calls}"
    assert "body" in calls, f"--body 인데 body 검사를 안 탔다: {calls}"


def test_online_path_parses_and_exposes_cache_attr() -> None:
    """`--online` 경로가 파싱되고 `args.cache` 가 **실재**한다 (네트워크 없이).

    옵션 등록이 사라지면 `--cache` 를 안 줘도 `main()` 이
    `AttributeError: 'Namespace' object has no attribute 'cache'` 로 죽는다.
    접두 충돌(`--cache` ↔ `--cache-stats`/`--cache-clear`/`--cache-stats-strategy`)도
    같이 고정한다.
    """
    mod = _import_url_validity()
    parser = mod._build_arg_parser()

    plain = parser.parse_args(["https://example.com", "--online"])
    assert hasattr(plain, "cache"), "args.cache 부재 — main() 이 AttributeError 로 죽는다"
    assert plain.cache is False, plain.cache

    cached = parser.parse_args(["https://example.com", "--online", "--cache"])
    assert cached.cache is True, "‑‑cache 가 안 먹는다 (접두 충돌이거나 등록 부재)"


def test_check_url_https_valid_v0_7_53() -> None:
    """https://example.com → 0 issue (정합 URL)."""
    mod = _import_url_validity()
    issues = mod.check_url("https://example.com/path")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-scheme" not in rule_codes, f"https rejected: {issues}"
    assert "V-R10-host" not in rule_codes, f"valid host rejected: {issues}"


def test_check_url_http_rejected_v0_7_53() -> None:
    """http:// → V-R10-scheme error (only https allowed)."""
    mod = _import_url_validity()
    issues = mod.check_url("http://example.com")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-scheme" in rule_codes, f"http not rejected: {issues}"


def test_check_url_no_scheme_rejected_v0_7_53() -> None:
    """example.com (no scheme) → V-R10-scheme error."""
    mod = _import_url_validity()
    issues = mod.check_url("example.com")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-scheme" in rule_codes, f"no-scheme not rejected: {issues}"


def test_check_url_localhost_rejected_v0_7_53() -> None:
    """https://localhost → V-R10-localhost error (private host)."""
    mod = _import_url_validity()
    issues = mod.check_url("https://localhost")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-localhost" in rule_codes, f"localhost not rejected: {issues}"


def test_check_url_private_ip_rejected_v0_7_53() -> None:
    """https://192.168.1.1 → V-R10-private-ip error (RFC 1918)."""
    mod = _import_url_validity()
    issues = mod.check_url("https://192.168.1.1")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-private-ip" in rule_codes, f"private IP not rejected: {issues}"


def test_check_url_path_traversal_rejected_v0_7_53() -> None:
    """https://example.com/../../etc/passwd → V-R10-traversal error."""
    mod = _import_url_validity()
    issues = mod.check_url("https://example.com/../../etc/passwd")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-traversal" in rule_codes, f"traversal not rejected: {issues}"


def test_check_url_file_scheme_rejected_v0_7_53() -> None:
    """file:///etc/passwd → V-R10-file-scheme error."""
    mod = _import_url_validity()
    issues = mod.check_url("file:///etc/passwd")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-file-scheme" in rule_codes, f"file:// not rejected: {issues}"


def test_check_url_credentials_rejected_v0_7_53() -> None:
    """https://user:pass@example.com → V-R10-credentials error (security risk)."""
    mod = _import_url_validity()
    issues = mod.check_url("https://user:pass@example.com")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-credentials" in rule_codes, f"credentials not rejected: {issues}"


def test_check_url_github_form_unusual_warn_v0_7_53() -> None:
    """github.com with unusual 3rd path → V-R10-github-form warn (not error)."""
    mod = _import_url_validity()
    # github.com/foo/bar/zzz → 3rd segment 'zzz' is not in allowed list
    issues = mod.check_url("https://github.com/foo/bar/zzz")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-github-form" in rule_codes, f"unusual github form not flagged: {issues}"
    severities = [i.severity for i in issues if i.rule == "V-R10-github-form"]
    assert severities == ["warn"], f"unusual form should be warn, got {severities}"


def test_cache_stats_zero_on_empty_v0_7_53() -> None:
    """cache_stats on non-existent file → 0 hits, 0 misses."""
    mod = _import_url_validity()
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp) / "nonexistent.json"
        stats = mod.cache_stats(cache)
        assert stats.get("hits", 0) == 0, f"non-empty hits: {stats}"
        assert stats.get("misses", 0) == 0, f"non-empty misses: {stats}"


def test_cache_clear_idempotent_v0_7_53() -> None:
    """cache_clear on non-existent file → no error (idempotent)."""
    mod = _import_url_validity()
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp) / "nonexistent.json"
        mod.cache_clear(cache)  # should not raise
        # Verify no file created
        assert not cache.exists(), f"cache_clear should not create file"


def test_cache_file_for_strategy_suffix_v0_7_53() -> None:
    """cache_file_for_strategy returns per-strategy file (stem-suffix pattern)."""
    mod = _import_url_validity()
    base = Path("/tmp/cache.json")
    for strategy in ("lru", "lfu", "mixed"):
        f = mod.cache_file_for_strategy(base, strategy)
        # Naming convention: <stem>_<strategy>.<ext> (e.g. /tmp/cache_lru.json)
        # Different strategies produce different files.
        assert strategy in f.name, f"strategy {strategy!r} not in filename: {f}"
        assert f.suffix == ".json", f"expected .json suffix, got {f.suffix}"


def test_cache_prune_dry_run_preserves_data_v0_7_56() -> None:
    """cache_prune (dry_run=True) reports removal but does not modify cache (v0.7.56+)."""
    import time
    mod = _import_url_validity()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "cache.json"
        cache_data = {
            "https://a.com/": {
                "timestamp": time.time() - 86400 * 7,  # 7d old
                "issues": [],
                "access_count": 0,
            },
            "https://b.com/": {
                "timestamp": time.time(),
                "issues": [],
                "access_count": 5,
            },
        }
        cf = mod.cache_file_for_strategy(base, "mixed")
        cf.write_text(json.dumps(cache_data), encoding="utf-8")
        result = mod.cache_prune(base_path=base, max_age_seconds=86400, dry_run=True)
        assert result["mixed"]["removed"] == 1
        assert result["mixed"]["kept"] == 1
        assert result["_overall"]["dry_run"] is True
        # File should be unchanged
        after = json.loads(cf.read_text(encoding="utf-8"))
        assert len(after) == 2


def test_cache_prune_apply_removes_old_v0_7_56() -> None:
    """cache_prune (apply) actually removes old entries from cache (v0.7.56+)."""
    import time
    mod = _import_url_validity()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "cache.json"
        cache_data = {
            "https://old.com/": {
                "timestamp": time.time() - 86400 * 7,
                "issues": [],
                "access_count": 0,
            },
            "https://fresh.com/": {
                "timestamp": time.time(),
                "issues": [],
                "access_count": 5,
            },
        }
        cf = mod.cache_file_for_strategy(base, "mixed")
        cf.write_text(json.dumps(cache_data), encoding="utf-8")
        result = mod.cache_prune(base_path=base, max_age_seconds=86400, min_access_count=5, dry_run=False)
        assert result["mixed"]["removed"] == 1
        assert result["_overall"]["dry_run"] is False
        after = json.loads(cf.read_text(encoding="utf-8"))
        assert "https://fresh.com/" in after
        assert "https://old.com/" not in after


def main() -> int:
    test_funcs = [
        test_check_url_https_valid_v0_7_53,
        test_check_url_http_rejected_v0_7_53,
        test_check_url_no_scheme_rejected_v0_7_53,
        test_check_url_localhost_rejected_v0_7_53,
        test_check_url_private_ip_rejected_v0_7_53,
        test_check_url_path_traversal_rejected_v0_7_53,
        test_check_url_file_scheme_rejected_v0_7_53,
        test_check_url_credentials_rejected_v0_7_53,
        test_check_url_github_form_unusual_warn_v0_7_53,
        test_cache_stats_zero_on_empty_v0_7_53,
        test_cache_clear_idempotent_v0_7_53,
        test_cache_file_for_strategy_suffix_v0_7_53,
        test_cache_prune_dry_run_preserves_data_v0_7_56,
        test_cache_prune_apply_removes_old_v0_7_56,
        test_cli_accepts_the_flags_ci_actually_passes,
        test_online_path_parses_and_exposes_cache_attr,
        test_main_runs_the_ci_invocation_end_to_end,
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
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
