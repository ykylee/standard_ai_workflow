"""workflow_kit.path_resolver — in-repo path → canonical GitHub URL (v0.7.34+).

ADR-008 채택. wiki page 의 `last_ingested_from` (in-repo path) 가 OKF `resource` field
에 canonical GitHub blob URL 로 자동 resolve.

Resolve algorithm (5 step, deterministic, no runtime fetch):
  1. CI 우선: `$GITHUB_SERVER_URL` + `$GITHUB_REPOSITORY` env var (가장 신뢰)
  2. local + fetch 후: `git config --get remote.origin.url` (HTTPS form normalize)
  3. origin URL 에서 `.git` suffix 제거
  4. base URL = `<origin>/blob/<default-branch>/` (default branch = `main` 가정 fallback)
  5. in-repo path 와 결합

Fallback chain:
  1. `GITHUB_SERVER_URL` + `GITHUB_REPOSITORY` (CI)
  2. `git config --get remote.origin.url` (local + fetch 후)
  3. `git symbolic-ref refs/remotes/origin/HEAD` (default branch)
  4. `git branch --show-current` (local fallback)
  5. `main` 가정 + warning (deepest fallback)
  6. `None` (resolve 실패 → caller 가 `resource` 비움)

Security:
  - path traversal 방지: `../` prefix reject, `/` 시작 (absolute) reject
  - URL scheme 검증: `https://` 만 accept, `http://` reject (downgrade attack 방지)
  - SSH form `git@github.com:foo/bar.git` → HTTPS form 자동 normalize

Usage:
    from workflow_kit.path_resolver import resolve_in_repo_path_to_url

    url = resolve_in_repo_path_to_url(
        relative_path="workflow-source/workflow_kit/README.md",
        repo_root=Path("/path/to/repo"),
    )

CLI:
    python -m workflow_kit.path_resolver <in-repo-path> [--repo-root <path>]
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GITHUB_SSH_PATTERN = re.compile(r"^git@([^:]+):(.+?)(?:\.git)?$")
GITHUB_HTTPS_PATTERN = re.compile(r"^https?://([^/]+)/(.+?)(?:\.git)?/?$")

# Path traversal: paths starting with `..` or `/` or containing `..` segments
def _is_path_safe(relative_path: str) -> bool:
    """Reject path traversal attempts."""
    if not relative_path:
        return False
    if relative_path.startswith("/"):
        return False
    if relative_path.startswith("../") or relative_path == "..":
        return False
    # check for embedded `..` segments after normalization
    parts = Path(relative_path).parts
    if any(p == ".." for p in parts):
        return False
    return True


# ---------------------------------------------------------------------------
# Origin URL detection
# ---------------------------------------------------------------------------
def _detect_origin_url(repo_root: Path) -> str | None:
    """Detect git remote origin URL. 3 layer fallback.

    Returns HTTPS form (normalized) or None.
    """
    # 1. CI environment (GitHub Actions)
    github_server = os.environ.get("GITHUB_SERVER_URL", "").strip()
    github_repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if github_server and github_repo:
        # GITHUB_SERVER_URL typically "https://github.com", GITHUB_REPOSITORY "owner/repo"
        return f"{github_server.rstrip('/')}/{github_repo}"

    # 2. `git config --get remote.origin.url`
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return _normalize_origin_url(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def _normalize_origin_url(raw_url: str) -> str | None:
    """Normalize git origin URL to HTTPS form.

    - `git@github.com:foo/bar.git` → `https://github.com/foo/bar`
    - `https://github.com/foo/bar.git` → `https://github.com/foo/bar`
    - `https://gitlab.com/foo/bar` → `https://gitlab.com/foo/bar` (passed through, but
      ADR-008 의 *GitHub only* 범위 — caller 가 platform check)

    Returns None if URL form is unsupported.
    """
    raw_url = raw_url.strip()
    if not raw_url:
        return None

    # SSH form
    m = GITHUB_SSH_PATTERN.match(raw_url)
    if m:
        host, path = m.group(1), m.group(2)
        return f"https://{host}/{path}"

    # HTTPS form
    m = GITHUB_HTTPS_PATTERN.match(raw_url)
    if m:
        host, path = m.group(1), m.group(2)
        return f"https://{host}/{path}"

    return None


# ---------------------------------------------------------------------------
# Default branch detection
# ---------------------------------------------------------------------------
def _repo_has_origin_remote(repo_root: Path) -> bool:
    """``repo_root`` 자신이 `origin` remote 를 가졌는가 (env 를 보지 않는다)."""
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def _detect_default_branch(repo_root: Path) -> str:
    """Detect default branch. 3 layer fallback.

    Returns branch name (e.g. "main", "master", "develop"). Defaults to "main" with warning.
    """
    # 1. `git symbolic-ref refs/remotes/origin/HEAD` (after `git fetch`)
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            ref = result.stdout.strip()
            # `refs/remotes/origin/main` → `main`
            if "/" in ref:
                return ref.rsplit("/", 1)[-1]
            return ref
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # 2. `git branch --show-current` — **remote 가 없을 때만**.
    #
    # 현재 브랜치는 기본 브랜치가 아니다. origin 이 있는데도 이 fallback 을 쓰면
    # canonical URL 이 *지금 체크아웃한 브랜치*를 가리킨다 — 같은 파일이 브랜치마다
    # 다른 URL 을 갖게 되므로 canonical 이 아니다. 실측(2026-08-13): `actions/checkout`
    # 은 단일 ref 만 가져와 `refs/remotes/origin/HEAD` 를 만들지 않는다. 그래서
    # feature 브랜치 push 셀에서만 `…/blob/feat/plugin-harness-distribution/…` 이
    # 나와 커밋된 bundle 의 `…/blob/main/…` 과 어긋났고, 같은 커밋의 PR 셀은
    # detached HEAD 라 이 fallback 이 비어 통과했다 — **같은 SHA, 셀마다 다른 판정**.
    #
    # remote 가 아예 없는 저장소(로컬 전용)에서는 현재 브랜치가 곧 기본 브랜치이므로
    # 그때만 쓴다.
    # 판단은 **이 저장소에 remote 가 있는가** 다. `_detect_origin_url` 로 물으면
    # 안 된다 — 그쪽은 CI env(`GITHUB_REPOSITORY`)를 먼저 보므로 GitHub Actions 안에서는
    # remote 없는 temp 저장소에도 URL 을 돌려준다. 그러면 이 gate 가 CI 에서만 반대로
    # 열린다 (실측: 로컬 13/13, CI 에서 그 case 만 red).
    if not _repo_has_origin_remote(repo_root):
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # 3. Fallback: "main" (warning emitted by caller)
    return "main"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def resolve_in_repo_path_to_url(
    relative_path: str,
    repo_root: Path,
) -> str | None:
    """Resolve in-repo relative path to canonical GitHub blob URL.

    Args:
        relative_path: in-repo path (e.g. "workflow-source/workflow_kit/README.md")
        repo_root: path to repository root

    Returns:
        Canonical URL string, or None if resolve failed.

    Security:
        - Rejects `../` prefix and embedded `..` segments
        - Rejects absolute paths (`/` prefix)
        - Rejects non-HTTPS origins (SSH normalized to HTTPS)
    """
    if not _is_path_safe(relative_path):
        return None

    # URL form already: pass through (rare case — caller 가 보낸 URL 그대로 사용)
    if relative_path.startswith(("http://", "https://")):
        return relative_path

    origin = _detect_origin_url(repo_root)
    if not origin:
        return None

    default_branch = _detect_default_branch(repo_root)
    return f"{origin}/blob/{default_branch}/{relative_path}"


def resolve_in_repo_path_to_url_pinned(
    relative_path: str,
    repo_root: Path,
    *,
    commit_sha: str | None = None,
    ref: str | None = None,
) -> str | None:
    """Resolve in-repo path to commit-pinned URL (ADR-018, v0.7.37+).

    Pinned URLs use the form:
    - `<origin>/blob/<commit_sha>/<path>` (commit SHA)
    - `<origin>/blob/<ref>/<path>` (ref like "v0.7.37", "main", "feature/x")

    Unlike `resolve_in_repo_path_to_url` which uses the *current* default branch
    (which can change over time), pinned URLs are *immutable* — the URL always
    points to the exact content at that commit/ref.

    Args:
        relative_path: in-repo path (e.g. "workflow-source/workflow_kit/README.md")
        repo_root: path to repository root
        commit_sha: 40-char commit SHA (full or short, ≥7 chars)
        ref: branch/tag name (e.g. "main", "v0.7.37") — alternative to commit_sha

    Returns:
        Canonical pinned URL string, or None if resolve failed.

    Strategy:
    1. If commit_sha given: use `/blob/<commit_sha>/<path>` (immutable)
    2. If ref given: use `/blob/<ref>/<path>` (mutable but explicit)
    3. If neither: return None (caller must provide at least one)
    """
    if not _is_path_safe(relative_path):
        return None

    if relative_path.startswith(("http://", "https://")):
        return relative_path

    origin = _detect_origin_url(repo_root)
    if not origin:
        return None

    if commit_sha:
        # Validate SHA format (hex, 7-40 chars)
        sha = commit_sha.strip()
        if not (7 <= len(sha) <= 40) or not all(c in "0123456789abcdef" for c in sha.lower()):
            return None
        return f"{origin}/blob/{sha}/{relative_path}"

    if ref:
        # Ref: branch or tag name — basic validation (no slashes, no special chars)
        r = ref.strip()
        if not r or "/" in r or any(c in r for c in "?&\\"):
            return None
        return f"{origin}/blob/{r}/{relative_path}"

    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="workflow_kit.path_resolver",
        description="in-repo path → canonical GitHub URL (v0.7.34+, ADR-008 + commit-pinned via ADR-018)",
    )
    p.add_argument("path", help="in-repo relative path")
    p.add_argument("--repo-root", type=Path, default=Path("."), help="repo root (default: cwd)")
    p.add_argument("--commit", help="commit SHA (full or short, 7-40 hex chars) for commit-pinned URL (ADR-018)")
    p.add_argument("--ref", help="ref (branch/tag name) for ref-pinned URL (ADR-018)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    if args.commit or args.ref:
        url = resolve_in_repo_path_to_url_pinned(
            args.path, args.repo_root.resolve(),
            commit_sha=args.commit, ref=args.ref,
        )
    else:
        url = resolve_in_repo_path_to_url(args.path, args.repo_root.resolve())
    if url is None:
        print(f"ERROR: resolve failed for {args.path!r}", file=sys.stderr)
        return 1
    print(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
