"""tools/release_pipeline.py changelog-gen subcommand smoke test (v0.7.14+).

v0.7.14 follow-up: cmd_changelog_gen — multi-release git log → CHANGELOG.md (Keep-a-Changelog 형식).
v0.7.15 follow-up: --from-tag/--to-tag range filter 추가.
6 test PASS 기준.

Test list:
1. test_changelog_gen_argparse: --output / --unreleased-label / --dry-run / --json / --from-tag / --to-tag argparse error 없음
2. test_changelog_gen_dry_run: dry-run mode 에서 file 변경 없음 + result 정합
3. test_changelog_gen_apply: apply mode 에서 CHANGELOG.md 작성 + Keep-a-Changelog 형식 검증
4. test_changelog_gen_section_categorization: commit subject prefix → section mapping 검증
5. test_changelog_gen_range_filter (v0.7.15+): --from-tag/--to-tag range scan
6. test_changelog_gen_out_of_range_graceful (v0.7.15+): invalid --from-tag 시 graceful fail
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline.py"
DEFAULT_OUTPUT = SOURCE_ROOT / "CHANGELOG.md"

# workflow_kit.common.atomic_write import 위해 (v0.7.15+ release_pipeline.py 의 의존)
sys.path.insert(0, str(SOURCE_ROOT))


def _import_tool():
    """release_pipeline.py 를 importlib 로 로드."""
    spec = importlib.util.spec_from_file_location("release_pipeline", str(TOOL))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- Test 1: argparse 인식 ---


def test_changelog_gen_argparse() -> None:
    """changelog-gen 의 --output / --unreleased-label / --dry-run / --json / --from-tag / --to-tag argparse error 없음."""
    for args in [
        ["--dry-run", "--json"],
        ["--output=/tmp/test_changelog.md", "--dry-run"],
        ["--unreleased-label=Pending", "--dry-run"],
        ["--from-tag=v0.7.0-beta", "--to-tag=v0.7.10-beta", "--dry-run", "--json"],
        ["--from-tag=v0.7.5-beta", "--dry-run"],
    ]:
        proc = subprocess.run(
            [sys.executable, str(TOOL), "changelog-gen"] + args,
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
        )
        assert "unrecognized arguments" not in proc.stderr, \
            f"args={args} → argparse error: {proc.stderr}"


# --- Test 2: dry-run mode 에서 file 변경 없음 + result 정합 ---


def test_changelog_gen_dry_run() -> None:
    """dry-run mode 에서 file 변경 없음 + mode=dry-run + commits/versions 정합."""
    pre_exists = DEFAULT_OUTPUT.exists()
    pre_content = DEFAULT_OUTPUT.read_text() if pre_exists else ""

    proc = subprocess.run(
        [sys.executable, str(TOOL), "changelog-gen", "--dry-run", "--json"],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
    )
    assert proc.returncode == 0, f"exit {proc.returncode}: {proc.stderr}"
    out = json.loads(proc.stdout)
    assert out["mode"] == "dry-run"
    assert "output_path" in out
    assert out["commits"] > 0
    assert out["versions"] > 0

    # file 변경 없음
    post_exists = DEFAULT_OUTPUT.exists()
    assert pre_exists == post_exists, "dry-run 에서 file 부재 변경"
    if pre_exists:
        assert DEFAULT_OUTPUT.read_text() == pre_content, "dry-run 에서 file 내용 변경"


# --- Test 3: apply mode 에서 CHANGELOG.md 작성 + Keep-a-Changelog 형식 ---


def test_changelog_gen_apply() -> None:
    """apply mode 에서 CHANGELOG.md 작성 + Keep-a-Changelog 형식 검증.

    임시 output file 사용. 본 repo 의 CHANGELOG.md 는 건드리지 않음.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "CHANGELOG.md"
        proc = subprocess.run(
            [sys.executable, str(TOOL), "changelog-gen", "--output", str(out_path), "--apply", "--json"],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
        )
        assert proc.returncode == 0, f"exit {proc.returncode}: {proc.stderr}"
        out = json.loads(proc.stdout)
        assert out["mode"] == "applied"
        assert out["output_path"] == str(out_path)
        assert out["commits"] > 0
        assert out["versions"] > 0

        # file 존재
        assert out_path.exists()
        body = out_path.read_text()

        # Keep-a-Changelog 형식 검증
        assert body.startswith("# Changelog\n")
        assert "## [Unreleased]" in body or re.search(r"## \[\d+\.\d+\.\d+\]", body), \
            "no version section"
        # Section header
        assert "### Added" in body, "no Added section"
        # commit 형식: `<subject> (<short>)`
        assert re.search(r"\([0-9a-f]{7}\)", body), "no commit hash format"


# --- Test 4: section categorization (commit subject prefix → section) ---


def test_changelog_gen_section_categorization() -> None:
    """commit subject prefix → Keep-a-Changelog section mapping.

    categorize_by_section() 직접 호출 + 각 prefix 의 section 검증.
    """
    mod = _import_tool()
    # standard prefix
    assert mod.categorize_by_section("feat(v0.7.0): ...") == "Added"
    assert mod.categorize_by_section("fix(v0.7.0): ...") == "Fixed"
    assert mod.categorize_by_section("docs(v0.7.0): ...") == "Changed"
    assert mod.categorize_by_section("chore(v0.7.0): ...") == "Changed"
    # unknown prefix
    assert mod.categorize_by_section("random subject") == "Changed"
    # known: refactor, perf, test, build, ci
    assert mod.categorize_by_section("refactor(v0.7.0): ...") == "Changed"
    assert mod.categorize_by_section("perf(v0.7.0): ...") == "Changed"
    assert mod.categorize_by_section("test(v0.7.0): ...") == "Changed"


# --- Test 5: --from-tag/--to-tag range filter (v0.7.15+) ---


def test_changelog_gen_range_filter() -> None:
    """--from-tag/--to-tag 으로 range scan. dry-run mode.

    v0.7.0-beta..v0.7.10-beta range 의 commit count 가 full history 보다 적어야 함.
    """
    # full history
    proc_full = subprocess.run(
        [sys.executable, str(TOOL), "changelog-gen", "--dry-run", "--json"],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
    )
    assert proc_full.returncode == 0
    full = json.loads(proc_full.stdout)
    full_commits = full["commits"]
    assert full_commits > 50, f"full history expected 50+, got {full_commits}"

    # range v0.7.0..v0.7.10
    proc_range = subprocess.run(
        [sys.executable, str(TOOL), "changelog-gen",
         "--from-tag=v0.7.0-beta", "--to-tag=v0.7.10-beta",
         "--dry-run", "--json"],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
    )
    assert proc_range.returncode == 0
    rng = json.loads(proc_range.stdout)
    assert rng["from_tag"] == "v0.7.0-beta"
    assert rng["to_tag"] == "v0.7.10-beta"
    assert rng["commits"] < full_commits, \
        f"range commits ({rng['commits']}) should be < full ({full_commits})"
    assert rng["commits"] > 0

    # range v0.7.5..v0.7.8 (smaller)
    proc_small = subprocess.run(
        [sys.executable, str(TOOL), "changelog-gen",
         "--from-tag=v0.7.5-beta", "--to-tag=v0.7.8-beta",
         "--dry-run", "--json"],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
    )
    assert proc_small.returncode == 0
    small = json.loads(proc_small.stdout)
    assert small["commits"] < rng["commits"], \
        f"smaller range ({small['commits']}) should be < larger ({rng['commits']})"


# --- Test 6: out-of-range (invalid tag) graceful fail ---


def test_changelog_gen_out_of_range_graceful() -> None:
    """invalid --from-tag 시 graceful fail (mode=error, error 메시지).

    v9.9.9-beta 등 존재하지 않는 tag. `git log` 가 exit != 0 → empty commits → error.
    """
    proc = subprocess.run(
        [sys.executable, str(TOOL), "changelog-gen",
         "--from-tag=v9.9.9-beta", "--dry-run", "--json"],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
    )
    out = json.loads(proc.stdout) if proc.stdout else {}
    if "mode" not in out and "error" in out:
        # error dict (no mode key) — convert to {mode: "error", error: ...}
        out["mode"] = "error"
    assert out.get("mode") == "error", f"expected error mode, got {out.get('mode')}"
    err_msg = out.get("error", "")
    assert "v9.9.9-beta" in err_msg or "no commits" in err_msg, \
        f"expected error message, got {err_msg}"


# --- 메인 실행 ---



def test_non_release_versions_are_not_sections() -> None:
    """v1.1.3+: 선언된 예외 version 은 release section 이 되지 않는다.

    `RELEASE_RE` 는 subject 안의 `(vX.Y)` 를 release 로 본다. 이 저장소 초기 commit
    두 건은 *워크플로우 문서 체계* 의 Phase 5 버전을 그 형식으로 적었고 (package
    release 가 아니다 — `pyproject.toml` 미변경), semver 정렬 탓에 `[3.0.1]` 이
    **최신 release 자리에** 앉아 있었다. CHANGELOG 를 읽는 사람에게 거짓말이 된다.

    git tag 대조는 쓸 수 없다 — 0.15.x 대 다수가 tag 없이 릴리스돼 진짜 release 를
    대량으로 지운다 (2026-08-09 실측: CHANGELOG 152 vs tag 121). 그래서 선언된
    예외로 둔다. 이 test 는 그 예외가 실제로 걸러지는지 + 명세가 비지 않았는지 본다.
    """
    mod = _import_tool()
    assert getattr(mod, "NON_RELEASE_VERSIONS", None), "NON_RELEASE_VERSIONS 선언 부재"
    for version, reason in mod.NON_RELEASE_VERSIONS.items():
        assert reason.strip(), f"{version}: 예외에 이유가 없다 (원장은 이유가 정본)"

    # 예외 version 을 담은 가짜 commit 이 'unreleased' 로 흡수되는지
    sample = "\n".join([
        "aaa1111|aaa1111full|dev|2026-04-27|feat: Phase 5 official release (v3.0) with schemas",
        "bbb2222|bbb2222full|dev|2026-04-27|feat: add harness support (v3.0.1)",
        "ccc3333|ccc3333full|dev|2026-08-09|chore(release): v1.1.2 — real package release",
    ])
    rows = mod._parse_git_log(sample)
    by_version = {r["subject"][:20]: r["version"] for r in rows}
    assert all(
        v == "unreleased" for k, v in by_version.items() if "Phase 5" in k or "harness" in k
    ), f"예외 version 이 release 로 분류됨: {by_version}"
    assert any(v == "1.1.2" for v in by_version.values()), (
        f"진짜 release 는 그대로 인식돼야 한다: {by_version}"
    )

    # 실제 CHANGELOG 에도 예외 section 이 없어야 한다
    changelog = DEFAULT_OUTPUT
    if changelog.is_file():
        body = changelog.read_text(encoding="utf-8")
        for version in mod.NON_RELEASE_VERSIONS:
            assert f"## [{version}]" not in body, (
                f"CHANGELOG 에 예외 section 이 남아 있다: [{version}] — 재생성 필요"
            )

def main() -> int:
    test_funcs = [
        test_changelog_gen_argparse,
        test_changelog_gen_dry_run,
        test_changelog_gen_apply,
        test_changelog_gen_section_categorization,
        test_changelog_gen_range_filter,
        test_changelog_gen_out_of_range_graceful,
        test_non_release_versions_are_not_sections,
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
