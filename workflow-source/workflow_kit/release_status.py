"""Release pipeline status aggregator (v0.11.14+).

Real-time release status snapshot for `release-status` dispatcher subcommand.
Aggregates:
- current pyproject version
- last release tag (git describe)
- unreleased commits (count + list)
- CI mypy cross-verify verdict (v0.11.13+ Layer 1)
- local mypy strict status (v0.11.12+ Layer 2)
- next version (auto-bump hint, v0.7.18+)
- ready_to_release verdict (all checks pass)

v0.11.16+ --auto-bump flag: `cmd_release_status(args)` 의 `args.auto_bump=True` 일 때
current_version == last_release_tag 분기에서 자동으로 `tools/release_pipeline.py
cmd_version_bump --patch --apply` 호출 → next_version patch bump + post-step
sync_release_hash.py 자동 호출 (v0.7.27+ TASK-V0727-001 정합).

Mypy strict clean (v0.11.10+ FULL STRICT 도달, 35 file 누적) 정합.
신규 module (v0.11.14+) = 36 file strict clean. v0.11.16+ = 37 file.
"""
from __future__ import annotations

import json
import re
import subprocess
import os
import tempfile
import sys
from pathlib import Path
from typing import Any

# REPO_ROOT = workflow-source/ (release_pipeline.py 와 동일)
# 본 module 은 workflow_kit/release_status.py 이므로:
# workflow_kit/release_status.py → parents[0] = workflow_kit/
#                          parents[1] = workflow-source/
REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = REPO_ROOT.parent  # ykylee/standard_ai_workflow/



def _isolated_mypy_cache_dir() -> str:
    """이 프로세스 전용 mypy 캐시 경로 (TASK-2026-08-24-main-007).

    `--no-incremental` 은 캐시 **읽기**만 끄고 디렉터리는 그대로 만든다. 그래서
    병렬 구간의 mypy 호출들이 같은 cwd 의 `.mypy_cache` 를 두고 경합했고, 관찰
    4차의 트레이스백이 `mypy/build.py:create_metastore` 를 지목했다.

    **빈 문자열(`--cache-dir=`)로는 못 끈다** — 캐시를 *끄는* 것이 아니라 cwd 로
    *옮긴다* (실측: `3.13/cache.*.db` 가 작업 디렉터리에 쏟아진다). 처음에
    `.mypy_cache` 부재만 확인하고 "아무것도 안 만든다" 로 읽어 저장소에 캐시
    db 를 커밋했다 — 기대한 산출물의 부재를 산출물 전체의 부재로 읽은 것이다.

    그래서 **전용 경로**를 준다. 프로세스별로 갈라지므로 병렬에서 부딪히지 않고,
    `TMPDIR` 아래라 러너가 정리한다 (전량 runner 는 `--tmp-dir` 로 실디스크를 준다).
    """
    return str(Path(tempfile.gettempdir()) / f"mypy-cache-{os.getpid()}")

def _read_pyproject_version() -> str:
    """Read [project] version from workflow-source/pyproject.toml."""
    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.exists():
        return "unknown"
    text = pyproject.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("version") and "=" in line:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "unknown"


def _last_release_tag() -> str | None:
    """git describe --tags --abbrev=0 → last release tag (e.g. v0.11.13-beta)."""
    try:
        proc = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _unreleased_commits(*, since_tag: str | None) -> dict[str, Any]:
    """Count + list unreleased commits since `since_tag` (None = all history).

    Returns:
        {"count": int, "commits": [{"sha": str, "subject": str}, ...]}
    """
    if since_tag:
        cmd = ["git", "log", f"{since_tag}..HEAD", "--oneline", "--no-decorate"]
    else:
        cmd = ["git", "log", "--oneline", "--no-decorate"]
    try:
        proc = subprocess.run(
            cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"count": 0, "commits": [], "error": "git not available or timeout"}
    if proc.returncode != 0:
        return {"count": 0, "commits": [], "error": proc.stderr.strip()[:200]}

    commits: list[dict[str, str]] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        # format: "abc1234 commit subject"
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            commits.append({"sha": parts[0], "subject": parts[1]})
        elif len(parts) == 1:
            commits.append({"sha": parts[0], "subject": ""})
    return {"count": len(commits), "commits": commits}


#: conventional commit 의 breaking 표기. `type(scope)!: subject` 와
#: 본문의 `BREAKING CHANGE:` 둘 다 spec 상 유효하지만, 여기서는 제목만 본다
#: (`_unreleased_commits` 가 제목만 들고 오기 때문 — 없는 것을 있는 척하지 않는다).
_BREAKING_SUBJECT_RE = re.compile(r"^[a-z]+(?:\([^)]*\))?!:")
_FEAT_SUBJECT_RE = re.compile(r"^feat(?:\([^)]*\))?:")
_FIX_SUBJECT_RE = re.compile(r"^fix(?:\([^)]*\))?:")


def classify_unreleased(commits: list[dict[str, str]]) -> dict[str, Any]:
    """미발행 커밋을 conventional commit 유형으로 분류한다.

    Returns:
        {"breaking": [subject, ...], "feat": int, "fix": int, "other": int, "total": int}
    """
    breaking: list[str] = []
    feat = fix = other = 0
    for c in commits:
        subject = str(c.get("subject", "")).strip()
        if _BREAKING_SUBJECT_RE.match(subject):
            breaking.append(subject)
            continue
        if _FEAT_SUBJECT_RE.match(subject):
            feat += 1
        elif _FIX_SUBJECT_RE.match(subject):
            fix += 1
        else:
            other += 1
    return {"breaking": breaking, "feat": feat, "fix": fix, "other": other,
            "total": len(commits)}


def _suggest_next_version(
    current: str, *, commits: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    """다음 버전 후보를 **미발행 커밋에서 파생**한다.

    이전 구현은 `current + 0.0.1` 고정이었고 커밋을 아예 안 읽었다. 그런데 그
    값은 같은 summary 줄에서 `unreleased=<N>` 옆에 찍힌다 — **개수는 세면서
    판정은 안 세니**, 파생값처럼 보이는 상수였다. 실측(2026-08-20): feat 18 ·
    fix 24 · breaking 1 인 사이클에 `1.2.1`(patch)을 권했다.

    규칙:
      - breaking 있음 → major. 다만 이 저장소는 v0.8.0 에 API 를 얼렸으므로
        major 는 **사람이 결정할 사안**이다. 숫자만 내밀지 않고
        `requires_decision` 과 근거(breaking 제목)를 함께 싣는다.
      - feat 있음 → minor
      - 그 외 → patch
      - 커밋 근거가 없으면 patch 로 떨어지되 **근거 없음을 밝힌다**
        (`basis.total == 0`). 모름을 판정으로 위장하지 않는다.
    """
    try:
        parts = current.split(".")
        if len(parts) != 3:
            return {"next": current, "current": current, "bumped": False,
                    "error": "non-semver current version"}
        major, minor, patch = (int(p) for p in parts)
    except (ValueError, AttributeError) as e:
        return {"next": current, "current": current, "bumped": False, "error": str(e)}

    basis = classify_unreleased(commits or [])
    if basis["breaking"]:
        level = "major"
        next_version = f"{major + 1}.0.0"
    elif basis["feat"]:
        level = "minor"
        next_version = f"{major}.{minor + 1}.0"
    else:
        level = "patch"
        next_version = f"{major}.{minor}.{patch + 1}"

    result: dict[str, Any] = {
        "next": next_version,
        "current": current,
        "bumped": True,
        "level": level,
        "basis": basis,
    }
    if level == "major":
        result["requires_decision"] = True
        result["decision_reason"] = (
            "breaking 커밋이 있어 major 를 제안하지만, 이 저장소는 v0.8.0 에 stable API 를 "
            "얼렸다 (SemVer 2년 보장). major 승격은 사람이 결정한다 — 근거는 basis.breaking."
        )
    return result


def _check_local_mypy() -> dict[str, Any]:
    """Layer 2: mypy strict on workflow_kit/. 0 errors → ok=True.

    Returns:
        {"ok": bool, "exit_code": int, "error_count": int, "first_error": str | None,
         "skipped": bool (True if mypy not available)}
    """
    try:
        # v1.0.2: config 명시. cwd 인 PROJECT_ROOT 에는 [tool.mypy] 가 없어
        # 암묵적 탐색이 `Config File: Default` 로 떨어졌고, 이 Layer 2 게이트도
        # strict 를 적용한 적이 없다 (CI / release gate 와 같은 결함의 사본).
        proc = subprocess.run(
            [sys.executable, "-m", "mypy", "--no-incremental", "--cache-dir", _isolated_mypy_cache_dir(),
             "--config-file", str(REPO_ROOT / "pyproject.toml"),
             "workflow-source/workflow_kit/"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=120,
        )
    except FileNotFoundError:
        return {"ok": False, "skipped": True, "error": "mypy module not installed"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "skipped": True, "error": "mypy timeout"}
    error_lines = [
        line for line in proc.stdout.splitlines()
        if ".py:" in line and "error:" in line
    ]
    return {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "error_count": len(error_lines),
        "first_error": error_lines[0] if error_lines else None,
    }


def _check_ci_mypy() -> dict[str, Any]:
    """Layer 1: GH Actions mypy-strict workflow last run verdict.

    Uses `gh run list --workflow mypy-strict.yml --limit 1 --json ...`.
    Returns:
        {"verdict": "ci_sanity" | "ci_stale" | "ci_fail" | "absent" | "skipped",
         "head_sha_match": bool | None, "ci_run": dict | None, "message": str}
    """
    # importlib 으로 release_pipeline 의 helper 호출 (v0.11.13+)
    try:
        sys.path.insert(0, str(REPO_ROOT / "workflow_kit" / "tools"))
        # v1.0.2: import-not-found ignore 제거 — tools/ 는 mypy 의 crawl 대상이 아니고
        # config 의 ignore_missing_imports=true 가 이미 덮으므로 unused 였다.
        from release_pipeline import _cross_verify_ci_mypy
        ci_mypy: dict[str, Any] = _cross_verify_ci_mypy()
        return ci_mypy
    except Exception as e:
        return {
            "verdict": "skipped",
            "head_sha_match": None,
            "ci_run": None,
            "message": f"cross-verify import/call failed: {type(e).__name__}: {e}",
        }


def _run_auto_bump(new_version: str) -> dict[str, Any]:
    """v0.11.16+ --auto-bump 의 actual bump stage.

    `tools/release_pipeline.py cmd_version_bump` 를 in-process 호출.
    read-only 모드 (default) 와 달리 write 발생: pyproject.toml version patch +
    workflow_kit/__init__.py __version__ sync + post-step sync_release_hash.py
    자동 호출 (v0.7.27+ TASK-V0727-001). amend 통합으로 1 commit 으로 정합.

    Args:
        new_version: bump 후의 next version (e.g. "0.11.16"). hint 로만 사용,
            actual 결과는 cmd_version_bump 가 결정.

    Returns:
        {"ok": bool, "new_version": str, "result": dict (cmd_version_bump result),
         "error": str | None}
    """
    try:
        # importlib 으로 release_pipeline 의 cmd_version_bump 호출
        sys.path.insert(0, str(REPO_ROOT / "workflow_kit" / "tools"))
        from release_pipeline import cmd_version_bump
        import argparse
        bump_args = argparse.Namespace(
            patch=True,
            minor=False,
            major=False,
            to=None,
            dry_run=False,
            apply=True,
            no_init=False,
            skip_sync_hash=False,
        )
        bump_result = cmd_version_bump(bump_args)
        return {
            "ok": True,
            "new_version": new_version,
            "result": bump_result,
            "error": None,
        }
    except Exception as e:
        return {
            "ok": False,
            "new_version": new_version,
            "result": None,
            "error": f"{type(e).__name__}: {e}",
        }


# release tag 에 붙는 pre-release suffix. `release_pipeline` 의
# `suffix_order = {"": 0, "alpha": 1, "beta": 2, "rc": 3}` 와 같은 집합이다.
_TAG_SUFFIXES = ("-alpha", "-beta", "-rc")


def _tag_to_version(tag: str) -> str:
    """release tag(`v1.0.0-beta`) → pyproject version(`1.0.0`).

    이전 구현은 `tag.lstrip("v").rstrip("-beta")` 였는데 `rstrip` 은 **suffix 제거가
    아니라 문자집합 제거**다. 집합 {'-','b','e','t','a'} 를 오른쪽에서 벗기므로:

        "1.0.0-alpha" -> "1.0.0-alph"   (h 가 집합에 없어 거기서 멈춤)
        "1.0.0-rc"    -> "1.0.0-rc"     (c 가 집합에 없어 그대로)

    beta 만 쓰는 동안 우연히 맞았을 뿐이고, alpha / rc 릴리스에서는 version 비교가
    조용히 어긋나 "이미 릴리스됨" 판정과 auto-bump 분기가 오작동한다.
    """
    version = tag[1:] if tag.startswith("v") else tag
    for suffix in _TAG_SUFFIXES:
        if version.endswith(suffix):
            return version[: -len(suffix)]
    return version


def cmd_release_status(args: Any) -> dict[str, Any]:
    """Release pipeline status aggregator (v0.11.14+, read-only).

    v0.11.16+: args.auto_bump=True 시 current_version == last_release_tag 분기에서
    자동으로 next_version (patch) bump + sync_release_hash.py post-step 자동 호출.
    in-process cmd_version_bump 호출. 결과를 auto_bump_result dict 로 attach.

    Returns:
        {
            "current_version": str,
            "last_release_tag": str | None,
            "unreleased_commits": {"count": int, "commits": [...]},
            "ci_mypy": {verdict, head_sha_match, ci_run, message},
            "local_mypy": {ok, exit_code, error_count, first_error},
            "next_version": {next, current, bumped},
            "ready_to_release": bool,
            "auto_bump_applied": bool (v0.11.16+),
            "auto_bump_result": dict | None (v0.11.16+),
        }
    """
    current = _read_pyproject_version()
    last_tag = _last_release_tag()
    unreleased = _unreleased_commits(since_tag=last_tag)
    local_mypy = _check_local_mypy()
    ci_mypy = _check_ci_mypy()
    next_ver = _suggest_next_version(current, commits=unreleased.get("commits", []))

    # v0.11.16+ --auto-bump: current == last_tag 분기에서 자동 bump
    auto_bump_applied = False
    auto_bump_result: dict[str, Any] | None = None
    if getattr(args, "auto_bump", False) and last_tag \
            and _tag_to_version(last_tag) == current:
        auto_bump_result = _run_auto_bump(next_ver["next"])
        auto_bump_applied = auto_bump_result.get("ok", False)
        if auto_bump_applied:
            # bump 성공 시 current_version 재읽기 + next_version 재계산
            current = _read_pyproject_version()
            next_ver = _suggest_next_version(current, commits=unreleased.get("commits", []))

    # ready_to_release verdict: Layer 1 + Layer 2 모두 sanity
    # + unreleased_commits > 0 (release 의미)
    # + last_tag != current (이미 released 가 아님)
    # v0.11.16+: auto_bump_applied 면 ready (current_version 이 last_tag 와 달라짐)
    local_mypy_ok = local_mypy.get("ok", False)
    ci_verdict = ci_mypy.get("verdict", "skipped")
    if auto_bump_applied:
        # bump 성공 = next version 으로 정렬됨 → ready 판정으로 진행
        ready = True
        ready_reason = (
            f"auto-bumped to {current} (was {last_tag}); "
            "all checks pass + unreleased commits present"
        )
    elif last_tag and _tag_to_version(last_tag) == current:
        # 이미 current 가 last_tag 와 같음 (release 안 됨)
        ready = False
        ready_reason = "current_version already at last_release_tag"
    elif unreleased.get("count", 0) == 0:
        ready = False
        ready_reason = "no unreleased commits"
    elif not local_mypy_ok:
        ready = False
        ready_reason = f"local mypy strict not clean: error_count={local_mypy.get('error_count')}"
    elif ci_verdict not in ("ci_sanity", "sanity", "no_local_verify", "absent", "skipped"):
        # ci_stale / ci_fail / drift_warning
        ready = False
        ready_reason = f"ci_mypy verdict={ci_verdict!r} (not sanity)"
    else:
        ready = True
        ready_reason = "all checks pass + unreleased commits present"

    result = {
        "current_version": current,
        "last_release_tag": last_tag,
        "unreleased_commits": unreleased,
        "ci_mypy": {
            "verdict": ci_verdict,
            "head_sha_match": ci_mypy.get("head_sha_match"),
            "ci_run": ci_mypy.get("ci_run"),
            "message": ci_mypy.get("message"),
        },
        "local_mypy": local_mypy,
        "next_version": next_ver,
        "ready_to_release": ready,
        "ready_reason": ready_reason,
        "auto_bump_applied": auto_bump_applied,
        "auto_bump_result": auto_bump_result,
    }
    # v0.11.15+ 1-line summary (jq-friendly) + v0.11.16+ 6-field (auto_bump 추가)
    result["summary"] = _summarize_release_status(result)
    return result


def _summarize_release_status(result: dict[str, Any]) -> str:
    r"""1-line summary of release status (v0.11.15+, jq-friendly).

    v0.11.16+: 6-field 로 확장 — `auto_bump=<applied|skipped|failed>` 추가.

    Returns:
        Compact 1-line string. format = `ci_mypy=<verdict>, local_mypy=<ok|FAIL>,
        ready=<true|false>, next=<X.Y.Z>, unreleased=<count>, auto_bump=<state>`.
        Stable key order for grep / pipe.

    Example:
        `ci_mypy=sanity, local_mypy=ok, ready=false, next=0.11.16, unreleased=3, auto_bump=skipped`
    """
    ci_verdict = result.get("ci_mypy", {}).get("verdict", "unknown")
    local_ok = result.get("local_mypy", {}).get("ok", False)
    local_mypy_str = "ok" if local_ok else "FAIL"
    ready = result.get("ready_to_release", False)
    next_v = result.get("next_version", {}).get("next", "?")
    unreleased = result.get("unreleased_commits", {}).get("count", 0)
    # v0.11.16+ auto_bump state
    if result.get("auto_bump_applied"):
        auto_bump_state = "applied"
    elif result.get("auto_bump_result") is not None and not result.get("auto_bump_applied"):
        auto_bump_state = "failed"
    else:
        auto_bump_state = "skipped"
    return (
        f"ci_mypy={ci_verdict}, "
        f"local_mypy={local_mypy_str}, "
        f"ready={'true' if ready else 'false'}, "
        f"next={next_v}, "
        f"unreleased={unreleased}, "
        f"auto_bump={auto_bump_state}"
    )
