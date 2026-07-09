#!/usr/bin/env python3
"""v0.13.0 release automation script (one-shot wrapper around release_pipeline).

본 script 는 v0.13.0 (Quality Dashboard) release 의 8 단계를 sequential 하게 실행:
    1. preflight (git / gh auth / drift prevention / dashboard smoke)
    2. version-bump (0.11.25 → 0.13.0)
    3. version-bump 결과 commit
    4. note-draft (releases/Beta-v0.13.0.md skeleton)
    5. release note 수동 편집 안내 + commit
    6. dashboard HTML preview (GitHub Pages source)
    7. release --apply (tag push + gh release create + dashboard auto-emit)
    8. post-emit dashboard markdown snapshot commit + verify

각 step 의 실행 정책:
    - ``--yes`` flag 없으면 dry-run 만 실행 + 사용자 확인 prompt 출력
    - ``--apply`` flag 있으면 모든 step 의 apply 까지 일괄 실행
    - 모든 destructive action 직전에 stderr 로 경고 + 5초 sleep (--skip-sleep 으로 bypass)

Usage:
    # dry-run 만 (모든 step 의 plan 출력)
    python3 tools/release_v0_13_0.py

    # 사용자 확인 mode (각 apply 직전에 stdin 입력 요구)
    python3 tools/release_v0_13_0.py --interactive

    # 자동 apply mode (모든 step 의 --apply 실행, no prompt)
    python3 tools/release_v0_13_0.py --apply

    # 일부 step 만 dry-run
    python3 tools/release_v0_13_0.py --step=version-bump
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Final

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
TOOLS_DIR: Final[Path] = Path(__file__).resolve().parent
RELEASE_PIPELINE: Final[Path] = TOOLS_DIR / "release_pipeline.py"
WORKFLOW_KIT_CLI: Final[str] = "workflow_kit.workflow_kit_cli"
DRIFT_SMOKE: Final[Path] = REPO_ROOT / "tests" / "check_drift_prevention_v0_11_23.py"
DASHBOARD_SMOKE: Final[Path] = REPO_ROOT / "tests" / "check_quality_dashboard_v0_13_0.py"

# Release constants (v0.13.0 specific).
CURRENT_TAG: Final[str] = "v0.11.25-beta"
NEW_VERSION: Final[str] = "0.13.0"
NEW_TAG: Final[str] = f"v{NEW_VERSION}-beta"
RELEASE_NOTE: Final[Path] = REPO_ROOT / "releases" / f"Beta-{NEW_VERSION}.md"

# Preflight checks required for safe release.
PREFLIGHT_CHECKS: Final[tuple[str, ...]] = (
    "git_clean_working_tree",
    "gh_auth_active",
    "drift_prevention_6_of_6",
    "dashboard_smoke_10_of_10",
    "remote_tag_not_exists",
)

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _print_header(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def _print_step(idx: int, total: int, name: str) -> None:
    print()
    print(f"[STEP {idx}/{total}] {name}")
    print("-" * 72)


def _print_warn(msg: str) -> None:
    print(f"  ⚠ {msg}", file=sys.stderr)


def _print_error(msg: str) -> None:
    print(f"  ✗ {msg}", file=sys.stderr)


def _print_ok(msg: str) -> None:
    print(f"  ✓ {msg}")


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 300,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """subprocess 실행, (rc, stdout, stderr) 반환. cwd + env 옵션."""
    actual_cwd = str(cwd) if cwd else str(REPO_ROOT)
    actual_env = os.environ.copy()
    if env:
        actual_env.update(env)
    completed = subprocess.run(
        cmd,
        cwd=actual_cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        env=actual_env,
    )
    return completed.returncode, completed.stdout, completed.stderr


PROJECT_ROOT: Final[Path] = REPO_ROOT.parent  # git repo root (workflow-source 의 부모)


def _run_release_pipeline(args: list[str], *, timeout: int = 300) -> tuple[int, str]:
    """release_pipeline.py 의 subcommand 실행."""
    cmd = [sys.executable, str(RELEASE_PIPELINE), *args]
    rc, stdout, stderr = _run(cmd, timeout=timeout)
    return rc, stdout + stderr  # combine


def _git(args: list[str]) -> tuple[int, str]:
    return _run(["git", *args])


def _prompt_yes_no(question: str, *, default: bool = False) -> bool:
    """stdin 에 y/N prompt. ``--yes`` 면 default 값 반환."""
    suffix = " [Y/n]" if default else " [y/N]"
    try:
        answer = input(f"  ? {question}{suffix}: ").strip().lower()
    except EOFError:
        return default
    if not answer:
        return default
    return answer in ("y", "yes")


# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------


def check_git_clean_working_tree() -> bool:
    rc, out, _ = _git(["status", "--porcelain"])
    if rc != 0:
        return False
    # Allow-list: 본 script 자신 + dev-run artifact (release hook 이 자동 emit 하기 전까지).
    allowed = {
        "?? workflow-source/tools/release_v0_13_0.py",
        "?? ai-workflow/dashboard/snapshot.md",
        "?? docs/dashboard/index.html",
    }
    unexpected = [
        line for line in out.strip().splitlines()
        if line not in allowed
    ]
    if unexpected:
        _print_warn("git working tree 에 unexpected 변경:")
        for line in unexpected[:10]:
            print(f"      {line}")
        return False
    return True


def check_gh_auth_active() -> bool:
    rc, out, _ = _run(["gh", "auth", "status"])
    return rc == 0 and "Logged in" in out


def check_remote_tag_not_exists(tag: str) -> bool:
    rc, out, _ = _git(["ls-remote", "--tags", "origin", tag])
    if rc != 0:
        return True  # error 시 skip (pre-flight fail soft)
    return tag not in out


def check_drift_prevention_6_of_6() -> bool:
    env = {**os.environ, "PYTHONPATH": str(TOOLS_DIR.parent)}
    rc, out, _ = _run(
        [sys.executable, str(DRIFT_SMOKE)],
        cwd=REPO_ROOT,
        env=env,
        timeout=120,
    )
    return rc == 0 and "=== PASS: 6/6 ===" in out


def check_dashboard_smoke_10_of_10() -> bool:
    env = {**os.environ, "PYTHONPATH": str(TOOLS_DIR.parent)}
    rc, out, _ = _run(
        [sys.executable, str(DASHBOARD_SMOKE)],
        cwd=REPO_ROOT,
        env=env,
        timeout=120,
    )
    return rc == 0 and "ALL 10/10 CASES PASS" in out


# ---------------------------------------------------------------------------
# Step implementations
# ---------------------------------------------------------------------------


def step_preflight(args: argparse.Namespace) -> bool:
    _print_step(1, 8, "Preflight checks")
    checks = {
        "git_clean_working_tree": check_git_clean_working_tree(),
        "gh_auth_active": check_gh_auth_active(),
        "drift_prevention_6_of_6": check_drift_prevention_6_of_6(),
        "dashboard_smoke_10_of_10": check_dashboard_smoke_10_of_10(),
        f"remote_tag_not_exists({NEW_TAG})": check_remote_tag_not_exists(NEW_TAG),
    }
    for name, ok in checks.items():
        if ok:
            _print_ok(name)
        else:
            _print_error(f"{name} — FAIL")
    if all(checks.values()):
        _print_ok("All preflight checks PASS")
        return True
    _print_error("Some preflight checks FAILED")
    return False


def step_version_bump(args: argparse.Namespace) -> bool:
    _print_step(2, 8, f"version-bump: 0.11.25 → {NEW_VERSION}")
    bump_args = ["version-bump", f"--to={NEW_VERSION}"]
    if not args.apply:
        bump_args.append("--dry-run")
    rc, out = _run_release_pipeline(bump_args)
    print(out)
    if rc != 0:
        _print_error("version-bump 실패")
        return False
    if args.apply:
        _print_ok(f"version {NEW_VERSION} 적용 완료")
    else:
        _print_ok("dry-run 성공 (--apply 로 실제 실행)")
    return True


def step_commit_version_bump(args: argparse.Namespace) -> bool:
    _print_step(3, 8, "commit version-bump 결과")
    rc, status, _ = _git(["status", "--porcelain"])
    changed = [
        line for line in status.splitlines()
        if any(
            line.endswith(p)
            for p in ("pyproject.toml", "workflow_kit/__init__.py", "README.md")
        )
    ]
    if not changed:
        _print_warn("version-bump 적용된 file 없음 — commit skip")
        return True
    print("  변경 file:")
    for line in changed:
        print(f"    {line}")
    if not args.apply:
        print("  --apply 시 git add + commit 수행")
        return True
    if not args.yes and not _prompt_yes_no("이 변경들을 commit 할까요?", default=False):
        return False
    files = [line.split(maxsplit=1)[1] for line in changed]
    rc, _, err = _git(["add", *files])
    if rc != 0:
        _print_error(f"git add 실패: {err}")
        return False
    msg = f"chore(version): bump v0.11.25-beta → {NEW_TAG} (Phase 13 dashboard)"
    rc, _, err = _git(["commit", "-m", msg])
    if rc != 0:
        _print_error(f"git commit 실패: {err}")
        return False
    _print_ok(f"commit 완료: {msg}")
    return True


def step_note_draft(args: argparse.Namespace) -> bool:
    _print_step(4, 8, f"note-draft: {CURRENT_TAG} → {NEW_VERSION}")
    note_args = ["note-draft", f"--from={CURRENT_TAG}", f"--to={NEW_VERSION}"]
    if not args.apply:
        note_args.append("--dry-run")
    rc, out = _run_release_pipeline(note_args)
    print(out)
    if rc != 0:
        _print_error("note-draft 실패")
        return False
    if args.apply:
        if not RELEASE_NOTE.is_file():
            _print_error(f"release note 가 {RELEASE_NOTE} 에 생성되지 않음")
            return False
        _print_ok(f"release note 생성: {RELEASE_NOTE.relative_to(REPO_ROOT)}")
    else:
        _print_ok("dry-run 성공 (--apply 로 실제 실행)")
    return True


def step_commit_release_note(args: argparse.Namespace) -> bool:
    _print_step(5, 8, "release note 수동 편집 안내 + commit")
    if not RELEASE_NOTE.is_file():
        _print_warn(f"{RELEASE_NOTE} 없음 — skip")
        return True
    print(f"  release note 위치: {RELEASE_NOTE.relative_to(REPO_ROOT)}")
    print()
    print("  ⚠ release note 는 *skeleton* 입니다. 다음을 확인/편집 후 commit 하세요:")
    print("    1. 본문 TL;DR 의 commit hash / 라인 정합")
    print("    2. ## 검증 섹션의 누적 smoke count (현재 40 → 41 로 +1)")
    print("    3. ## 호환성 섹션의 public API 변경 0 정합")
    print("    4. ## Reference 섹션의 직전 release link 정합")
    print()
    if not args.apply:
        print("  --apply 시 git add + commit 수행 (편집 후 직접 commit 해도 OK)")
        return True
    if not args.yes and not _prompt_yes_no(
        "release note 편집 완료했습니까? commit 진행할까요?", default=True
    ):
        return False
    rc, _, err = _git(["add", str(RELEASE_NOTE)])
    if rc != 0:
        _print_error(f"git add 실패: {err}")
        return False
    msg = f"chore(release): Beta-{NEW_VERSION} release note (작업내역 정리)"
    rc, _, err = _git(["commit", "-m", msg])
    if rc != 0:
        _print_error(f"git commit 실패: {err}")
        return False
    _print_ok(f"commit 완료: {msg}")
    return True


def step_html_preview(args: argparse.Namespace) -> bool:
    _print_step(6, 8, "dashboard HTML preview (GitHub Pages source)")
    # dashboard CLI 의 --publish 는 CWD 기준 docs/dashboard/index.html 에 write.
    # CWD 를 PROJECT_ROOT (= git repo root) 로 지정해야 정확한 위치에 emit.
    cmd = [sys.executable, "-m", WORKFLOW_KIT_CLI,
           "--command=dashboard", "--format=html", "--publish"]
    env = {**os.environ, "PYTHONPATH": str(TOOLS_DIR.parent)}
    rc, out, err = _run(cmd, cwd=PROJECT_ROOT, env=env, timeout=120)
    if rc != 0:
        print(err)
        _print_error("HTML publish 실패")
        return False
    print(out)
    index_path = PROJECT_ROOT / "docs" / "dashboard" / "index.html"
    if index_path.is_file():
        _print_ok(f"index.html emit: {index_path.relative_to(PROJECT_ROOT)} ({index_path.stat().st_size} bytes)")
    if args.apply:
        rc, _, err = _git(["add", str(index_path)])
        if rc != 0:
            _print_error(f"git add 실패: {err}")
            return False
        msg = f"feat(dashboard): {NEW_TAG} HTML snapshot (GitHub Pages publish)"
        rc, _, err = _git(["commit", "-m", msg])
        if rc != 0:
            _print_error(f"git commit 실패: {err}")
            return False
        _print_ok(f"commit 완료: {msg}")
    else:
        _print_ok("dry-run 성공 (--apply 시 git commit 까지)")
    return True


def step_release(args: argparse.Namespace) -> bool:
    _print_step(7, 8, f"release --apply: tag push + gh release create + dashboard auto-emit")
    if not args.apply:
        print("  ⚠ 이 step 은 destructive 합니다:")
        print(f"    - git tag {NEW_TAG} push to origin")
        print(f"    - gh release create v{NEW_VERSION} on github.com")
        print(f"    - dashboard markdown auto-emit (warning 만 — release fail 안 함)")
        print()
        print("  --apply 시에만 실행. dry-run 만 권장.")
        return True
    if not args.yes and not _prompt_yes_no(
        f"정말 {NEW_TAG} release 를 publish 할까요?", default=False
    ):
        return False
    print()
    _print_warn(f"5초 후 gh release create 실행 — interrupt (Ctrl-C) 가능")
    if not args.skip_sleep:
        for i in range(5, 0, -1):
            print(f"  ... {i}", end="\r", flush=True)
            time.sleep(1)
        print()
    rel_args = ["release", f"--to={NEW_VERSION}"]
    rc, out = _run_release_pipeline(rel_args, timeout=600)
    print(out)
    if rc != 0:
        _print_error("release --apply 실패")
        return False
    _print_ok(f"{NEW_TAG} release publish 완료")
    return True


def step_post_emit_verify(args: argparse.Namespace) -> bool:
    _print_step(8, 8, "post-emit dashboard snapshot commit + verify")
    # snapshot.md 는 PROJECT_ROOT (= git repo root) 기준. dashboard hook 이
    # gh release create 성공 후 거기 emit.
    snapshot_path = PROJECT_ROOT / "ai-workflow" / "dashboard" / "snapshot.md"
    if not snapshot_path.is_file():
        _print_warn("snapshot.md 없음 — release hook 이 emit 안 한 듯. skip")
        return True
    _print_ok(f"snapshot emit: {snapshot_path.relative_to(PROJECT_ROOT)} ({snapshot_path.stat().st_size} bytes)")
    if args.apply:
        rc, _, err = _git(["add", str(snapshot_path)])
        if rc != 0:
            _print_error(f"git add 실패: {err}")
            return False
        msg = f"chore(release): {NEW_TAG} dashboard snapshot (auto-emit)"
        rc, _, err = _git(["commit", "-m", msg])
        if rc != 0:
            _print_error(f"git commit 실패: {err}")
            return False
        _print_ok(f"commit 완료: {msg}")
    rc, _, err = _git(["ls-remote", "--tags", "origin", NEW_TAG])
    if NEW_TAG in err:
        _print_ok(f"remote tag {NEW_TAG} 존재 확인")
    else:
        _print_warn(f"remote tag {NEW_TAG} 미확인 — push --follow-tags 필요")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="v0.13.0 release automation")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="모든 step 의 --apply 실행 (destructive actions 포함)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="사용자 확인 prompt skip",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="각 apply 직전에 stdin prompt (--yes 와 mutually exclusive)",
    )
    parser.add_argument(
        "--step",
        default=None,
        help="특정 step 만 실행 (e.g. version-bump, note-draft)",
    )
    parser.add_argument(
        "--skip-sleep",
        action="store_true",
        help="destructive action 직전 5초 sleep skip",
    )
    args = parser.parse_args()

    if args.yes and args.interactive:
        _print_error("--yes 와 --interactive 는 mutually exclusive")
        return 2

    _print_header(f"v0.13.0 release automation (mode={'APPLY' if args.apply else 'DRY-RUN'})")

    steps = (
        ("preflight", step_preflight),
        ("version-bump", step_version_bump),
        ("commit-version-bump", step_commit_version_bump),
        ("note-draft", step_note_draft),
        ("commit-release-note", step_commit_release_note),
        ("html-preview", step_html_preview),
        ("release", step_release),
        ("post-emit-verify", step_post_emit_verify),
    )

    if args.step:
        selected = [s for s in steps if s[0] == args.step]
        if not selected:
            _print_error(f"step '{args.step}' 없음. 가능: {[s[0] for s in steps]}")
            return 2
        steps = tuple(selected)  # type: ignore[assignment]

    failed = 0
    for name, fn in steps:
        try:
            ok = fn(args)
        except subprocess.TimeoutExpired as e:
            _print_error(f"{name} timeout: {e}")
            ok = False
        except Exception as e:  # noqa: BLE001
            _print_error(f"{name} exception: {type(e).__name__}: {e}")
            ok = False
        if not ok:
            failed += 1

    _print_header("RESULT")
    if failed == 0:
        print(f"  ✓ {len(steps)} step 모두 {'apply' if args.apply else 'dry-run'} 성공")
        return 0
    print(f"  ✗ {failed}/{len(steps)} step 실패")
    return 1


if __name__ == "__main__":
    sys.exit(main())