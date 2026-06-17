"""tools.release_pipeline_lib — in-process wrapper for release_pipeline.py (v0.7.55+).

기존 `tools/release_pipeline.py` (1478 line) 는 *script* (`if __name__ == "__main__": main()`)
라 `import` 가 안 됨. 본 wrapper 는 *in-process* 호출을 위해:

1. `tools/` 를 sys.path 에 임시로 insert (relative import 회피)
2. `release_pipeline` module spec load via importlib
3. `cmd_validate` / `cmd_version_bump` / `cmd_note_draft` / `cmd_release` /
   `cmd_verify` / `cmd_rollback` / `cmd_dist` / `cmd_changelog_gen` 등 노출

Design note: `tools/release_pipeline.py` 의 REPO_ROOT = parents[1] (workflow-source/).
본 wrapper 도 같은 위치에 있으므로 REPO_ROOT 정합 — 추가 조정 불필요.

v0.7.56 follow-up (release_pipeline 의 다른 subcommand wrapper):
- v0.7.55: cmd_validate (1 wrapper, used by release-doctor in dispatcher)
- v0.7.56: cmd_version_bump / cmd_note_draft / cmd_changelog_gen / cmd_release /
  cmd_verify / cmd_rollback / cmd_dist (7 wrapper 추가 = 8 total)

Cross-ref: memory rule 12 (cleanup 정공법 — inline vs dispatcher), release_pipeline.py
의 module-level const (REPO_ROOT / PYPROJECT / WORKFLOW_KIT_INIT) 가 *load time* 에
계산되므로 wrapper module 위치 변경 시 REPO_ROOT drift 위험.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


_TOOLS_DIR = Path(__file__).resolve().parent
_RELEASE_PIPELINE_PATH = _TOOLS_DIR / "release_pipeline.py"


def _load_release_pipeline() -> ModuleType:
    """Load tools/release_pipeline.py as a module (script → module).

    Uses importlib.util.spec_from_file_location to bypass sys.path / package
    boundary. The module is cached in sys.modules under a stable name so
    subsequent imports return the same instance (avoids REPO_ROOT drift).
    """
    if "tools_release_pipeline" in sys.modules:
        return sys.modules["tools_release_pipeline"]
    spec = importlib.util.spec_from_file_location(
        "tools_release_pipeline", str(_RELEASE_PIPELINE_PATH),
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {_RELEASE_PIPELINE_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tools_release_pipeline"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_args(**kwargs):
    """Build a SimpleNamespace-like args object for release_pipeline cmd_ fns.

    release_pipeline's cmd_* functions read attributes from a parsed argparse
    Namespace. We build one from kwargs so callers don't need argparse.
    """
    from types import SimpleNamespace
    return SimpleNamespace(**kwargs)


# ---------------------------------------------------------------------------
# v0.7.55 wrappers
# ---------------------------------------------------------------------------

def cmd_validate(skip_packaging: bool = False, skip_doctor: bool = False,
                 skip_state: bool = False, skip_git: bool = False) -> dict:
    """Run cmd_validate from tools/release_pipeline.py in-process.

    Returns the dict shape produced by cmd_validate (4 keys: packaging / doctor /
    state / git, each with `ok` boolean + details).
    """
    mod = _load_release_pipeline()
    args = _make_args(
        skip_packaging=skip_packaging,
        skip_doctor=skip_doctor,
        skip_state=skip_state,
        skip_git=skip_git,
    )
    return mod.cmd_validate(args)


# ---------------------------------------------------------------------------
# v0.7.56 wrappers — extend to 7 more cmd_ functions
# ---------------------------------------------------------------------------

def cmd_version_bump(*, apply: bool = False, no_init: bool = False,
                     to: str | None = None, patch: bool = False,
                     minor: bool = False, major: bool = False) -> dict:
    """Run cmd_version_bump in-process (v0.7.56+).

    Args:
        apply: if True, actually write the version bump (default dry-run)
        no_init: if True, skip workflow_kit/__init__.py __version__ sync
        to: explicit target version (e.g. "0.7.56"). If None, bumps by patch.
        patch: increment patch version (e.g. 0.7.55 → 0.7.56)
        minor: increment minor version
        major: increment major version

    Returns:
        dict with mode (apply|dry-run), current_version, next_version
    """
    mod = _load_release_pipeline()
    args = _make_args(
        apply=apply,
        no_init=no_init,
        to=to,
        patch=patch,
        minor=minor,
        major=major,
        dry_run=not apply,
    )
    return mod.cmd_version_bump(args)


def cmd_note_draft(*, to: str, from_tag: str, dry_run: bool = True) -> dict:
    """Run cmd_note_draft in-process (v0.7.56+).

    Args:
        to: target version (e.g. "0.7.56")
        from_tag: source tag to collect commits since (e.g. "v0.7.55")
        dry_run: if True, don't write the file (default)

    Returns:
        dict with mode, output_path, commit_count
    """
    mod = _load_release_pipeline()
    args = _make_args(to=to, from_tag=from_tag, dry_run=dry_run)
    return mod.cmd_note_draft(args)


def cmd_changelog_gen(*, from_tag: str | None = None, to_tag: str = "HEAD",
                      dry_run: bool = True, output: str | None = None) -> dict:
    """Run cmd_changelog_gen in-process (v0.7.56+).

    Args:
        from_tag: start tag (None = all history)
        to_tag: end tag/REF (default "HEAD")
        dry_run: if True, don't write CHANGELOG.md (default)
        output: explicit output path (default: REPO_ROOT/CHANGELOG.md)

    Returns:
        dict with mode, changelog path, commit_count
    """
    mod = _load_release_pipeline()
    args = _make_args(
        from_tag=from_tag,
        to_tag=to_tag,
        dry_run=dry_run,
        output=output,
        unreleased_label="Unreleased",
    )
    return mod.cmd_changelog_gen(args)


def cmd_release(*, version: str, notes_template: str | None = None,
                skip_validate: bool = False, auto_bump: bool = False,
                apply: bool = False) -> dict:
    """Run cmd_release in-process (v0.7.56+, GitHub Release create).

    Args:
        version: target version (e.g. "0.7.56")
        notes_template: path to notes template (optional)
        skip_validate: skip 4-source validate (not recommended)
        auto_bump: if remote tag exists, auto-bump to next version
        apply: if True, actually create the release (default dry-run)

    Returns:
        dict with mode, version, release_url (if apply)
    """
    mod = _load_release_pipeline()
    args = _make_args(
        version=version,
        notes_template=notes_template,
        skip_validate=skip_validate,
        auto_bump=auto_bump,
        apply=apply,
        dry_run=not apply,
    )
    return mod.cmd_release(args)


def cmd_verify(*, tag: str) -> dict:
    """Run cmd_verify in-process (v0.7.56+, read-only GitHub Release check).

    Args:
        tag: tag to verify (e.g. "v0.7.56" or "0.7.56")

    Returns:
        dict with tag, ok, url, asset_count, errors
    """
    mod = _load_release_pipeline()
    args = _make_args(tag=tag)
    return mod.cmd_verify(args)


def cmd_rollback(*, tag: str, apply: bool = False) -> dict:
    """Run cmd_rollback in-process (v0.7.56+, destructive — use with --apply).

    Args:
        tag: tag to delete (e.g. "v0.7.56")
        apply: if True, actually delete (default dry-run)

    Returns:
        dict with mode, tag, commands_run
    """
    mod = _load_release_pipeline()
    args = _make_args(tag=tag, apply=apply, dry_run=not apply)
    return mod.cmd_rollback(args)


def cmd_dist(
    *,
    apply: bool = False,
    skip_existing: bool = False,
    production: bool = False,
    sdist_only: bool = False,
    wheel_only: bool = False,
    timeout: int = 300,
    json_output: bool = False,
) -> dict:
    """Run cmd_dist in-process (v0.7.56+, wheel + sdist build, v0.8.15 1-command 확장).

    Args:
        apply: if True, actually run `python3 -m build` (default dry-run)
        skip_existing: if True and dist/ 의 current-version 파일 있으면 build skip
        production: if True, also simulate production PyPI upload (spec §7.1 step 5)
        sdist_only: sdist 만 빌드
        wheel_only: wheel 만 빌드
        timeout: subprocess timeout in seconds (default 300)
        json_output: JSON output (release_pipeline 의 --json flag)

    Returns:
        dict with mode, out_dir, artifacts, twine_check, testpypi_simulation,
        and (if production=True) production_simulation.
    """
    mod = _load_release_pipeline()
    args = _make_args(
        apply=apply,
        dry_run=not apply,
        skip_existing=skip_existing,
        production=production,
        sdist_only=sdist_only,
        wheel_only=wheel_only,
        timeout=timeout,
        json=json_output,
    )
    return mod.cmd_dist(args)

def cmd_lfu_decay_persist(
    *,
    url: str,
    score: float,
    scores_path: str,
    apply: bool = False,
) -> dict:
    """Update a single URL's LFU decay score and persist to disk (v0.7.60+).

    In-process wrapper around workflow_kit.cache_lfu_decay_persist.update_decay_score.
    Dispatcher subcommand 28 (`cache-lfu-decay-persist`).

    Safety: default is `dry-run` (returns the would-be updated dict without
    writing to disk). Pass `apply=True` to actually persist. Mirrors the
    release-bump / cache-prune / okf-cleanup destructive-on-apply pattern
    (memory rule 5: default dry-run, --apply 명시 시에만 실제 동작).

    Args:
        url: URL key to update
        score: new decay score (0.0-1.0)
        scores_path: filesystem path to the JSON scores file (e.g.
            `cache/lfu_decay_scores.json`); created if missing
        apply: if True, actually persist the update (default dry-run)

    Returns:
        dict with `mode` (dry-run|applied), `url`, `score`, `scores_path`,
        `scores_count` (current count after update or hypothetical).
    """
    from workflow_kit.cache_lfu_decay_persist import (
        load_decay_scores,
        save_decay_scores,
    )
    # Load existing (or empty) scores
    existing = load_decay_scores(scores_path)
    if not apply:
        # Dry-run: simulate the update without writing
        would_be = dict(existing)
        would_be[url] = score
        return {
            "mode": "dry-run",
            "url": url,
            "score": score,
            "scores_path": scores_path,
            "scores_count": len(would_be),
            "current_count": len(existing),
        }
    # Apply: actually persist
    existing[url] = score
    save_decay_scores(existing, scores_path)
    return {
        "mode": "applied",
        "url": url,
        "score": score,
        "scores_path": scores_path,
        "scores_count": len(existing),
    }
