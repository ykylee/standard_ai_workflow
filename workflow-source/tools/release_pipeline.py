#!/usr/bin/env python3
"""v0.7.9+: standard-ai-workflow release pipeline 정식화 (7 subcommand).

release 절차 (validate → dist → version-bump → note-draft → release → verify → rollback) 의
*기계화 layer*. manual 절차 (memory #5 / docs/RELEASE.md) 의 *부족 부분* 자동화.

Phase 1 (v0.7.9): validate / version-bump / note-draft — 사전 점검 + version + note.
Phase 2 (v0.7.10): release / verify / rollback — gh CLI 통합 + read-only verify + destructive rollback.
Phase 3 (v0.7.11): dist — `python3 -m build` wheel + sdist 자동 빌드 (PEP 517/518).
Phase 5 (v0.7.18): release coordination observability — cmd_release 의 --auto-bump
  + remote tag pre-check (`git ls-remote origin`). v0.7.16 의 race lesson 반영.
Phase 6 (v0.13.1+): dashboard post-release emit — gh release create 성공 후
  workflow_kit.workflow_kit_cli --command=dashboard --format=markdown 자동 호출.
  --skip-dashboard-emit 으로 skip, --dashboard-output=PATH 로 경로 override.

PyPI/TestPyPI 업로드 ❌ (memory #5 의 release 채널 정책 — GitHub Releases 만).

Usage:
    # dry-run: 모든 subcommand plan 만 출력
    python3 tools/release_pipeline.py validate --dry-run
    python3 tools/release_pipeline.py version-bump --patch --dry-run
    python3 tools/release_pipeline.py note-draft --from=v0.7.8 --to=v0.7.9 --dry-run

    # apply
    python3 tools/release_pipeline.py version-bump --patch --apply
    python3 tools/release_pipeline.py note-draft --from=v0.7.8 --to=v0.7.9 --apply

    # JSON 출력 (CI integration)
    python3 tools/release_pipeline.py validate --json

Reference:
- tools/check_packaging.py (packaging 정합성 검증)
- tools/refresh_wiki_memory.py (v0.7.5, git log → memory emit 패턴)
- workflow_kit.cli.doctor (v0.7.8 state-aware baseline 검증)
- memory #5 standard-ai-workflow.md (release 채널 정책: GitHub Releases 만)
- docs/RELEASE.md (수동 release 절차)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# v0.7.15+ atomic_write (POSIX os.replace guarantee)
# workflow-source 를 sys.path 에 추가 (script 가 standalone 으로 실행될 때도
# workflow_kit 모듈이 import 가능하도록). v0.13.2+ 추가.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from workflow_kit.common.atomic_write import atomic_write_json, atomic_write_text
    from workflow_kit.common.state.cache import refresh_maturity_last_updated  # v0.14.6+ Task 3 follow-up
except ImportError:
    # standalone script (no workflow_kit on sys.path) — fall back to direct write.
    atomic_write_json = None  # type: ignore[assignment]
    atomic_write_text = None  # type: ignore[assignment]
    refresh_maturity_last_updated = None  # type: ignore[assignment]
# 1차 출처
REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
RELEASES_DIR = REPO_ROOT / "releases"
WORKFLOW_KIT_INIT = REPO_ROOT / "workflow_kit" / "__init__.py"

# 표준 sub-package list (check_packaging.py 와 동일 — packaging 정합성)
EXPECTED_SUBPACKAGES = [
    "workflow_kit",
    "workflow_kit.common",
    "workflow_kit.common.modes",
    "workflow_kit.common.state",
    "workflow_kit.common.contracts",
    "workflow_kit.common.schemas",
    "workflow_kit.contract_v1",
    "workflow_kit.server",
    "workflow_kit.harness",
    "bootstrap_lib",
    "bootstrap_lib.harnesses",
]

# tomllib (3.11+) / tomli (3.10) 분기
if sys.version_info >= (3, 11):
    import tomllib  # type: ignore[import-not-found]
else:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef, import-not-found]


# ---------------------------------------------------------------------------
# 1. validate
# ---------------------------------------------------------------------------


def cmd_validate(args) -> dict:
    """4 source 의 release-readiness 검증.

    1. check_packaging.py: pyproject 의 [tool.setuptools.packages] ↔ 디스크 정합
    2. workflow_kit.cli.doctor: 7 baseline 모두 evaluate (state-aware variant)
    3. state.json freshness: v0.7.5+ refresh_wiki_memory 의 last_freeze / last_ingest
    4. git status: working tree clean (release commit 의 clean state 보장)
    5. mypy strict: v0.11.12+ — workflow_kit/ mypy 2.1.0 strict 0 errors 강제
       (CI mypy-strict workflow 와 동일 invocation, release-time gate)
    """
    results: dict = {}

    # 1. check_packaging
    if not args.skip_packaging:
        # v0.11.17 in-scope fix: 부모 process 의 PYTHONPATH (예: `workflow-source`)
        # 가 상속되면, wheel install 의 site-packages/bootstrap_lib 가 shadowing
        # 되어 `No module named 'bootstrap_lib'` 실패. packaging check 는 venv
        # site-packages 만 사용해야 함. doctor/state/git check 는 venv site-packages
        # 만 사용하므로 동일 처리.
        clean_env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools/check_packaging.py")],
            capture_output=True, text=True, timeout=120,
            env=clean_env,
        )
        results["packaging"] = {
            "exit_code": proc.returncode,
            "ok": proc.returncode == 0,
            "last_line": proc.stdout.strip().split("\n")[-1] if proc.stdout else "",
        }
    else:
        results["packaging"] = {"ok": True, "skipped": True}

    # 2. workflow_kit.cli.doctor (v0.7.8)
    if not args.skip_doctor:
        proc = subprocess.run(
            [sys.executable, "-m", "workflow_kit.cli.doctor", "--json",
             "--project-root", str(REPO_ROOT)],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode == 0:
            try:
                doctor_out = json.loads(proc.stdout)
                cs_status = {
                    bl: doctor_out["results"][bl]["status"]
                    for bl in doctor_out["results"]
                }
                non_compliant = [
                    bl for bl, st in cs_status.items() if st == "non_compliant"
                ]
                results["doctor"] = {
                    "ok": len(non_compliant) == 0,
                    "baselines": cs_status,
                    "non_compliant": non_compliant,
                }
            except (json.JSONDecodeError, KeyError) as e:
                results["doctor"] = {"ok": False, "error": str(e)}
        else:
            results["doctor"] = {"ok": False, "exit_code": proc.returncode}
    else:
        results["doctor"] = {"ok": True, "skipped": True}

    # 3. state.json freshness
    if not args.skip_state:
        state_path = REPO_ROOT / "ai-workflow" / "memory" / "active" / "state.json"
        if state_path.exists():
            data = json.loads(state_path.read_text())
            last_freeze = data.get("memory", {}).get("last_freeze", "")
            last_ingest = data.get("wiki", {}).get("last_ingest", "")
            # last_freeze 가 v0.7.9 cycle 의 commit 범위 내면 OK
            results["state"] = {
                "ok": bool(last_freeze),
                "last_freeze": last_freeze,
                "last_ingest": last_ingest,
            }
        else:
            # state.json 부재도 OK (default empty state 시 v0.7.8 정합)
            results["state"] = {"ok": True, "absent": True}
    else:
        results["state"] = {"ok": True, "skipped": True}

    # 4. git status
    if not args.skip_git:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10,
        )
        clean = proc.stdout.strip() == ""
        results["git"] = {
            "ok": clean,
            "untracked_or_modified": proc.stdout.strip().split("\n") if not clean else [],
        }
    else:
        results["git"] = {"ok": True, "skipped": True}

    # 5. mypy strict (v0.11.12+ — release-time gate, CI mypy-strict workflow 의 local mirror)
    # v0.11.10 의 FULL mypy strict 도달 (35 file strict clean) 을 release-time 강제.
    # CI (.github/workflows/mypy-strict.yml) 가 PR-time 방어선이라면, 본 check 는
    # release-time 방어선. invocation 은 CI 와 동일:
    #   `mypy --no-incremental workflow_kit/` (cwd = parent_of_REPO_ROOT, 절대경로)
    # sub-package 의 workflow_kit/pyproject.toml (strict=false) 와 parent 의
    # workflow-source/pyproject.toml (strict=true) 의 merge 회피.
    # REPO_ROOT = workflow-source/ (release_pipeline.py 의 Path.__file__.parents[1] 정의)
    # 이므로, *project root* (REPO_ROOT.parent) 를 cwd 로 사용하고, target 을 절대경로.
    if not getattr(args, "skip_mypy", False):
        try:
            mypy_target = str(REPO_ROOT / "workflow_kit/")
            mypy_proc = subprocess.run(
                [sys.executable, "-m", "mypy", "--no-incremental", mypy_target],
                cwd=str(REPO_ROOT.parent), capture_output=True, text=True, timeout=120,
            )
            # error count: lines like "file.py:LINE: error: ... [rule]"
            error_lines = [
                line for line in mypy_proc.stdout.splitlines()
                if ".py:" in line and "error:" in line
            ]
            first_error = error_lines[0] if error_lines else None
            results["mypy"] = {
                "ok": mypy_proc.returncode == 0,
                "exit_code": mypy_proc.returncode,
                "error_count": len(error_lines),
                "first_error": first_error,
            }
        except FileNotFoundError:
            # mypy module 부재 — dev extra install 누락. v0.11.11 pin 정합 이지만
            # 환경 문제 가능. hard fail (gate 가 무효 = release 정지).
            results["mypy"] = {
                "ok": False,
                "error": "mypy module not installed (run `pip install -e ./workflow-source/workflow_kit[dev]`)",
            }
        except subprocess.TimeoutExpired:
            results["mypy"] = {"ok": False, "error": "mypy timeout (>120s)"}
    else:
        results["mypy"] = {"ok": True, "skipped": True}

    return results


# ---------------------------------------------------------------------------
# 1.4 mypy CI cross-verify (v0.11.13+ — Layer 1 CI ↔ Layer 2 local mypy gate 정합)
# ---------------------------------------------------------------------------


def _cross_verify_ci_mypy(*, timeout: int = 15) -> dict:
    """GH Actions mypy-strict workflow 의 last run 결과 와 local HEAD sha 비교.

    Layer 1 (CI, v0.11.11+) 와 Layer 2 (release-time gate, v0.11.12+) 의 정합 verify.
    verdict:
      - "sanity": CI success + local mypy 정합 (default, release 진행)
      - "drift_warning": CI success 인데 local fail (local drift, advisory)
      - "ci_stale": CI success 인데 headSha != HEAD (re-run 권고, advisory)
      - "ci_fail": CI failure (advisory)
      - "absent": gh CLI 성공 / no run found (advisory)
      - "skipped": gh CLI 부재 / error (advisory)

    Returns:
        {
            "verdict": str,
            "ci_run": dict | None,  # {databaseId, conclusion, headSha, event, status, createdAt, url}
            "head_sha": str | None,
            "head_sha_match": bool | None,
            "message": str,
        }
    """
    head_sha_proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPO_ROOT.parent), capture_output=True, text=True, timeout=5,
    )
    head_sha = head_sha_proc.stdout.strip() if head_sha_proc.returncode == 0 else None

    try:
        gh_proc = subprocess.run(
            ["gh", "run", "list", "--repo", "ykylee/standard_ai_workflow",
             "--workflow", "mypy-strict.yml", "--limit", "1",
             "--json", "databaseId,conclusion,headSha,event,status,createdAt,url"],
            cwd=str(REPO_ROOT.parent), capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        return {
            "verdict": "skipped",
            "ci_run": None,
            "head_sha": head_sha,
            "head_sha_match": None,
            "message": "gh CLI not found (skip cross-verify)",
        }
    except subprocess.TimeoutExpired:
        return {
            "verdict": "skipped",
            "ci_run": None,
            "head_sha": head_sha,
            "head_sha_match": None,
            "message": f"gh run list timeout (>{timeout}s)",
        }

    if gh_proc.returncode != 0:
        return {
            "verdict": "skipped",
            "ci_run": None,
            "head_sha": head_sha,
            "head_sha_match": None,
            "message": f"gh run list failed (exit={gh_proc.returncode}): {gh_proc.stderr.strip()[:200]}",
        }

    try:
        runs = json.loads(gh_proc.stdout)
    except json.JSONDecodeError as e:
        return {
            "verdict": "skipped",
            "ci_run": None,
            "head_sha": head_sha,
            "head_sha_match": None,
            "message": f"gh run list JSON parse error: {e}",
        }

    if not runs:
        return {
            "verdict": "absent",
            "ci_run": None,
            "head_sha": head_sha,
            "head_sha_match": None,
            "message": "no mypy-strict CI run found",
        }

    last_run = runs[0]
    ci_conclusion = last_run.get("conclusion")
    ci_head_sha = last_run.get("headSha")
    head_sha_match = (ci_head_sha == head_sha) if (ci_head_sha and head_sha) else None

    # verdict 결정 (Layer 1 CI ↔ Layer 2 local mypy 정합)
    # caller 가 별도로 local_mypy_ok / local_mypy_status 를 inject 해서
    # drift_warning / no_local_verify verdict 결정. 여기서는 CI-only verdict 반환.
    if ci_conclusion == "success":
        if head_sha_match is False:
            verdict = "ci_stale"
            message = (
                f"CI success for headSha={ci_head_sha[:7]}, "
                f"but local HEAD={head_sha[:7]} — re-run recommended"
            )
        else:
            verdict = "ci_sanity"
            message = (
                f"CI success for headSha={ci_head_sha[:7]} (matches local HEAD) — "
                f"local mypy 정합 verify 는 caller 가 verdict 결정"
            )
    elif ci_conclusion == "failure":
        verdict = "ci_fail"
        message = (
            f"CI failure for headSha={ci_head_sha[:7] if ci_head_sha else '?'}, "
            f"databaseId={last_run.get('databaseId')}"
        )
    else:
        verdict = "absent"
        message = (
            f"CI status {ci_conclusion!r} (not success/failure) for headSha={ci_head_sha[:7] if ci_head_sha else '?'}"
        )

    return {
        "verdict": verdict,
        "ci_run": last_run,
        "head_sha": head_sha,
        "head_sha_match": head_sha_match,
        "message": message,
    }


def _resolve_cross_verify_verdict(ci_mypy: dict, local_mypy: dict) -> str:
    """_cross_verify_ci_mypy 의 ci-only verdict 를 *local mypy* 와 결합하여 final verdict 결정.

    Verdict matrix:
      | CI verdict   | local mypy ok | local status | final verdict      |
      |--------------|---------------|--------------|--------------------|
      | ci_sanity    | True          | checked      | sanity             |
      | ci_sanity    | False         | checked      | drift_warning      |
      | ci_sanity    | N/A           | skipped      | no_local_verify    |
      | ci_stale     | (any)         | (any)        | ci_stale           |
      | ci_fail      | (any)         | (any)        | ci_fail            |
      | absent       | (any)         | (any)        | absent             |
      | skipped      | (any)         | (any)        | skipped            |
    """
    ci_verdict = ci_mypy.get("verdict")
    if ci_verdict != "ci_sanity":
        return ci_verdict or "absent"
    # ci_sanity 인 경우에만 local mypy 와 cross-verify
    # local_mypy 가 비어있거나 (--skip-validate) skipped 면 no_local_verify
    if not local_mypy or local_mypy.get("skipped"):
        return "no_local_verify"
    if local_mypy.get("ok"):
        return "sanity"
    return "drift_warning"


def _attach_release_summary(results: dict) -> dict:
    """results dict 에 v0.11.15+ 1-line summary 추가. 모든 return point 에서 호출.

    summary format: `ci_mypy=<verdict>, local_mypy=<ok|FAIL|skipped>,
    ready=<true|false>, next=<X.Y.Z|->, error=<error message or ok>`

    `cmd_release --json | jq -r '.summary'` 로 *1-line grep / pipe 가능*.
    """
    ci_verdict = results.get("ci_mypy", {}).get("verdict", "skipped")
    # local mypy 조회: pre_check.mypy (validate 활성 시) 또는 ci_mypy.local_mypy (cross-verify)
    local_mypy = results.get("pre_check", {}).get("mypy", {})
    if not local_mypy:
        # pre_check 가 비어있거나 mypy source 부재 (--skip-validate or --skip-mypy)
        local_mypy = results.get("ci_mypy", {}).get("local_mypy", {})
    if not local_mypy:
        # 둘 다 부재 → skipped (--skip-validate or mypy source 부재)
        local_str = "skipped"
    elif local_mypy.get("skipped"):
        local_str = "skipped"
    elif local_mypy.get("ok"):
        local_str = "ok"
    else:
        local_str = "FAIL"
    # ready_to_release (Layer 1 sanity + Layer 2 ok + tag mismatch X)
    if not results.get("error"):
        # success path: error 부재 + ci sanity
        if ci_verdict in ("sanity", "ci_sanity", "no_local_verify", "absent", "skipped") and local_str == "ok":
            ready = "true"
        else:
            ready = "false"
    else:
        ready = "false"
    # next version (version_source 또는 cli flag) — version_source 는 source label (cli-flag,
    # auto-bump, pyproject.toml) 이고 실제 version 은 다른 field. pyproject.toml 의 경우
    # read_version() 으로 읽은 값이지만, results 에는 source label 만 남는다.
    next_v = results.get("version") or results.get("version_source", "-")
    if next_v == "auto-bump" or next_v == "full-auto-bump":
        next_v = results.get("auto_bump", {}).get("next", "-")
    # version_source 가 label 이면 raw version 으로 fallback (없으면 label 유지)
    if next_v in ("cli-flag", "pyproject.toml", "auto-bump", "full-auto-bump"):
        # next_v 가 label 이면 results["error"] 부재 시엔 tag/version 표시, 있으면 "-"
        next_v = "-"
    err = results.get("error", "ok")
    summary = (
        f"ci_mypy={ci_verdict}, "
        f"local_mypy={local_str}, "
        f"ready={ready}, "
        f"next={next_v}, "
        f"error={err if isinstance(err, str) else 'ok'}"
    )
    results["summary"] = summary
    return results


# ---------------------------------------------------------------------------
# 1.5 release coordination observability (v0.7.18+)
# ---------------------------------------------------------------------------


def _check_remote_tag(tag: str, *, timeout: int = 15) -> dict:
    """원격 (origin) 에 주어진 tag 가 존재하는지 확인.

    Returns:
        {"exists": bool, "remote_url": str | None, "tag": str}
    """
    result: dict = {"exists": False, "remote_url": None, "tag": tag}
    # 1. remote URL 추출
    remote_proc = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=timeout,
    )
    if remote_proc.returncode != 0:
        return result
    result["remote_url"] = remote_proc.stdout.strip()
    # 2. ls-remote 로 tag 조회
    ls_proc = subprocess.run(
        ["git", "ls-remote", "origin", f"refs/tags/{tag}"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=timeout,
    )
    if ls_proc.returncode == 0 and ls_proc.stdout.strip():
        result["exists"] = True
    return result


def _list_remote_tags(pattern: str = "v*", *, timeout: int = 15) -> list[str]:
    """원격의 tag list (정규식 filter, sort -V)."""
    ls_proc = subprocess.run(
        ["git", "ls-remote", "--tags", "origin", pattern],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=timeout,
    )
    if ls_proc.returncode != 0:
        return []
    tags = []
    for line in ls_proc.stdout.strip().splitlines():
        # line: "<sha>\trefs/tags/<tagname>"
        parts = line.split("\t", 1)
        if len(parts) == 2:
            tag = parts[1].removeprefix("refs/tags/")
            # peel 된 ^{} tag 제외
            if not tag.endswith("^{}"):
                tags.append(tag)
    return sorted(tags, key=_version_sort_key)


def _version_sort_key(tag: str) -> tuple:
    """PEP 440 + suffix sort key. v0.7.17-beta → (0, 7, 17, 'beta'), v0.7.18 → (0, 7, 18, '').

    SemVer-ish + PEP 440 suffix 순서 (release < alpha < beta < rc). 정수 tuple 이므로
    `sorted(tags, key=_version_sort_key)` 가 *자동으로* numeric + suffix 순서.
    """
    # 'v' prefix 제거
    s = tag.lstrip("v")
    # '-suffix' 분리
    if "-" in s:
        base, suffix = s.split("-", 1)
    else:
        base, suffix = s, ""
    # base = 'X.Y.Z' → int tuple
    parts = base.split(".")
    nums = tuple(int(p) for p in parts if p.isdigit())
    # suffix sort: '' (release) < 'alpha' < 'beta' < 'rc'
    suffix_order = {"": 0, "alpha": 1, "beta": 2, "rc": 3}
    suffix_rank = suffix_order.get(suffix.split(".")[0], 99)
    return nums + (suffix_rank, suffix)


def next_available_version(local_version: str, *, remote_tags: list[str] | None = None) -> dict:
    """local_version 보다 큰, remote 에 없는 다음 version 결정.

    1차 출처: remote `git ls-remote --tags origin "vX.Y.*"` 의 latest + 0.0.1 bump.
    local_version 이 이미 remote 의 latest 보다 크면 그대로 (충돌 없음).
    같은 major.minor prefix 의 모든 tag → max + 0.0.1.

    Args:
        local_version: 현재 local pyproject 의 version (e.g. "0.7.17").
        remote_tags: pre-fetched list. None 이면 _list_remote_tags() 호출.

    Returns:
        {"next": "0.7.18", "current_local": "0.7.17", "remote_max": "0.7.17-beta", "bumped": True}
    """
    if remote_tags is None:
        remote_tags = _list_remote_tags()
    # local_version 의 major.minor prefix
    parts = local_version.split(".")
    if len(parts) < 2:
        major_minor_prefix = local_version
    else:
        major_minor_prefix = ".".join(parts[:2])
    # remote 의 같은 major.minor 의 tag 만 filter
    prefix = f"v{major_minor_prefix}."
    same_prefix = [t for t in remote_tags if t.startswith(prefix)]
    # numeric base 비교 (PEP 440 suffix 무시)
    def base_tuple(t: str) -> tuple:
        b = t.lstrip("v").split("-", 1)[0]
        try:
            return tuple(int(p) for p in b.split("."))
        except ValueError:
            return (0,)
    if same_prefix:
        remote_max = max(same_prefix, key=base_tuple)
    else:
        remote_max = None
    local_tuple = base_tuple(f"v{local_version}")
    if remote_max is None:
        # remote 에 같은 major.minor 부재 → local 그대로 (다음 patch 가 local 의 +1)
        next_v = local_version
        bumped = False
    else:
        remote_tuple = base_tuple(remote_max)
        if local_tuple > remote_tuple:
            # local 이 remote max 보다 큼 → 그대로
            next_v = local_version
            bumped = False
        elif local_tuple < remote_tuple:
            # local 이 remote max 보다 작음 → remote max + 0.0.1
            next_tuple = list(remote_tuple)
            next_tuple[-1] += 1
            next_v = ".".join(str(n) for n in next_tuple)
            bumped = True
        else:
            # local == remote max → patch bump
            next_tuple = list(remote_tuple)
            next_tuple[-1] += 1
            next_v = ".".join(str(n) for n in next_tuple)
            bumped = True
    return {
        "next": next_v,
        "current_local": local_version,
        "remote_max": remote_max,
        "bumped": bumped,
    }


# ---------------------------------------------------------------------------
# 2. version-bump
# ---------------------------------------------------------------------------


def read_version() -> str:
    """pyproject.toml 의 [project] version 읽기."""
    with PYPROJECT.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def write_version(new_version: str) -> None:
    """pyproject.toml 의 [project] version 갱신."""
    text = PYPROJECT.read_text()
    text = re.sub(
        r'(version\s*=\s*)"[\d.]+([^"]*)"',
        rf'\1"{new_version}\2"',
        text,
        count=1,
    )
    PYPROJECT.write_text(text)


def read_workflow_kit_version() -> str:
    """workflow_kit.__version__ 읽기. e.g. 'v0.7.13-beta'.

    v0.8.0+: SSOT = pyproject.toml [project] version (spec §4.3).
    workflow_kit/__init__.py 의 __version__ 은 runtime 에서 pyproject.toml 을 parse 해서
    compute (f"v{version}-beta") 하므로, 본 함수도 동일한 SSOT 에서 직접 compute.
    """
    return f"v{read_version()}-beta"


def write_workflow_kit_version(new_version: str, *, suffix: str = "-beta") -> str:
    """workflow_kit.__version__ 갱신.

    v0.8.0+: SSOT = pyproject.toml [project] version. workflow_kit/__init__.py 는 runtime
    compute 이므로 pyproject.toml 만 갱신하면 됨. __init__.py 의 literal fallback 도
    정합성 위해 함께 갱신 (spec §4.3 loud fallback chain).

    e.g. new_version='0.8.1' → pyproject.toml version 0.8.1, __init__.py fallback
    "v0.8.1-beta". __init__.py 의 SSOT compute (f"v{version}-beta") 가 pyproject 을
    parse 해서 같은 값을 return.
    """
    write_version(new_version)
    # __init__.py 의 literal fallback (loud fallback chain 의 3번째) 도 정합성 유지.
    # suffix 가 "" 이면 그냥 "v{version}", 그 외는 "v{version}{suffix}" (suffix 가 이미 -beta 같은 suffix 포함).
    # v0.11.22 → 0.11.23 사이에서 suffix 이중 처리 (v0.11.23-beta-beta) bug fix.
    text = WORKFLOW_KIT_INIT.read_text()
    replacement = f'v{new_version}{suffix or ""}'
    new_text, n = re.subn(
        r'(return\s+")v\d+\.\d+(?:\.\d+)?(?:[-+][a-zA-Z0-9.]+)?(")',
        rf'\g<1>{replacement}\g<2>',
        text,
    )
    if n == 0:
        # literal fallback 이 없는 경우 (e.g. v0.8.0 이전 패턴) — silent skip
        pass
    else:
        WORKFLOW_KIT_INIT.write_text(new_text)
    return f"v{new_version}{suffix or ''}"

def bump_version(version: str, *, patch: bool = False, minor: bool = False, major: bool = False, to: str | None = None) -> str:
    """version bump.

    --to=... 명시 시 그대로 사용. 아니면 --major/--minor/--patch 중 1개 (default: --patch).
    """
    if to is not None:
        return to
    major_n, minor_n, patch_n = parse_version(version)
    if major:
        return f"{major_n + 1}.0.0"
    if minor:
        return f"{major_n}.{minor_n + 1}.0"
    # default: patch
    return f"{major_n}.{minor_n}.{patch_n + 1}"


def parse_version(version: str) -> tuple[int, int, int]:
    """'0.7.8' → (0, 7, 8). pre-release 식별자 (e.g. '-beta') 는 무시."""
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    if not m:
        raise ValueError(f"invalid version: {version}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def cmd_refresh_maturity(args) -> dict:
    """maturity_matrix.json 의 `last_updated` field 자동 갱신 (v0.14.6+ Task 3 follow-up).

    v0.14.0+ dashboard Panel 1 freshness 보강을 위한 dispatcher subcommand.
    helper `refresh_maturity_last_updated` (cache.py) 를 호출하여 `last_updated` 를
    오늘 날짜로 갱신. idempotent (이미 today 면 no-op).

    v0.15.2+ (out-of-scope 1 해소): `--no-legacy-memory` strict opt-out caller 정합.
    legacy_memory=False 면 silent fallback 비활성 caller 로 간주, maturity refresh
    skip + warning emit (release note 가 legacy caller 의 silent fallback 자체가
    disable 된 caller 정합).

    Args (CLI namespace):
        apply (bool): default True. dry-run 모드 (--dry-run) 시 False.
        today (str | None): 명시적 override (default: date.today().isoformat()).
        maturity_path (str | None): 명시적 path (default: workflow-source/core/maturity_matrix.json).
        json (bool): JSON 출력.
        legacy_memory (bool | None): v0.15.2+ strict opt-out flag. False 면 skip.

    Returns:
        dict { refreshed: bool, before: str, after: str, today: str,
               maturity_path: str, mode: 'apply' | 'dry-run',
               legacy_memory_strict_opt_out: bool (v0.15.2+) }
    """
    from datetime import date as _date

    # v0.15.2+: legacy_memory strict opt-out (--no-legacy-memory) caller 정합.
    # silent fallback 비활성 caller 는 maturity refresh 자체를 skip.
    legacy_memory_strict_opt_out = getattr(args, "legacy_memory", None) is False
    if legacy_memory_strict_opt_out:
        return {
            "refreshed": False,
            "before": "",
            "after": "",
            "today": getattr(args, "today", None) or _date.today().isoformat(),
            "maturity_path": "<skipped — --no-legacy-memory strict opt-out>",
            "mode": "apply" if getattr(args, "apply", True) else "dry-run",
            "legacy_memory_strict_opt_out": True,
            "skip_reason": "v0.15.0+ ⚠️ BREAKING caller strict opt-out — silent fallback 비활성 정합. "
                           "maturity refresh skip.",
        }

    mode = "apply" if getattr(args, "apply", True) else "dry-run"
    today = getattr(args, "today", None) or _date.today().isoformat()
    maturity_path_arg = getattr(args, "maturity_path", None)
    if maturity_path_arg:
        maturity_path = Path(maturity_path_arg)
        if not maturity_path.is_absolute():
            maturity_path = (REPO_ROOT / maturity_path_arg).resolve()
    else:
        # release_pipeline.py 의 REPO_ROOT 는 workflow-source/ (tools/ 의 parent). 본
        # helper 는 root 기준이므로 REPO_ROOT.parent 사용 (doubled path 방지).
        maturity_path = (REPO_ROOT.parent / "workflow-source" / "core" / "maturity_matrix.json").resolve()

    result: dict[str, Any] = {
        "mode": mode,
        "today": today,
        "maturity_path": str(maturity_path),
        "refreshed": False,
        "before": "",
        "after": today,
    }
    if mode == "dry-run":
        # dry-run: 실제 갱신 없이 plan 만 emit
        if maturity_path.is_file():
            try:
                with maturity_path.open("r", encoding="utf-8") as fp:
                    mm = json.load(fp)
                result["before"] = str(mm.get("last_updated", ""))
            except (OSError, json.JSONDecodeError):
                pass
        result["dry_run_note"] = (
            "실제 last_updated 갱신 안 함. --apply 또는 --dry-run 미지정 시 자동 호출."
        )
        return result

    # apply mode — refresh_maturity_last_updated helper 호출
    if refresh_maturity_last_updated is None:
        result["error"] = (
            "refresh_maturity_last_updated helper unavailable (workflow_kit import 실패). "
            "workflow-source 가 sys.path 에 있는지 확인."
        )
        return result

    refreshed = refresh_maturity_last_updated(maturity_path, today=today)
    result["refreshed"] = refreshed["updated"]
    result["before"] = refreshed["before"]
    result["after"] = refreshed["after"]
    return result


def cmd_version_bump(args) -> dict:
    """pyproject.toml version patch + workflow_kit/__init__.py __version__ 자동 sync (v0.7.14+).

    --no-init flag 시 __init__.py sync skip (CI / override 시나리오).

    v0.7.27+: --apply 시 sync_release_hash.py 자동 호출 (TASK-V0726-003). 본 release 의
    state.json + backlog 의 hash = latest commit (apply 후의 chore commit) 으로 1 commit
    으로 정합. infinite fix(state) loop 회피.
    """
    current = read_version()
    current_wk = read_workflow_kit_version()
    if args.dry_run:
        new = bump_version(
            current,
            patch=args.patch, minor=args.minor, major=args.major, to=args.to,
        )
        result = {
            "mode": "dry-run",
            "current_pyproject": current,
            "current_workflow_kit": current_wk,
            "next_pyproject": new,
            "next_workflow_kit": f"v{new}-beta" if not getattr(args, "no_init", False) else "(skipped)",
        }
        return result
    if args.to is None and not (args.patch or args.minor or args.major):
        args.patch = True
    new = bump_version(
        current,
        patch=args.patch, minor=args.minor, major=args.major, to=args.to,
    )
    write_version(new)
    result = {
        "mode": "applied",
        "previous_pyproject": current,
        "current_pyproject": new,
    }
    if not getattr(args, "no_init", False):
        written = write_workflow_kit_version(new, suffix="-beta")
        result["previous_workflow_kit"] = current_wk
        result["current_workflow_kit"] = written
    else:
        result["workflow_kit_skipped"] = True

    # TASK-V0726-003 (v0.7.27): post-step 자동 sync — state.json + backlog 의 hash = latest
    # commit. --skip-sync-hash flag 시 skip (manual override).
    if not getattr(args, "skip_sync_hash", False):
        sync_result = _run_post_step_sync_hash(new)
        result["sync_hash_result"] = sync_result
    return result


def _run_post_step_sync_hash(version: str) -> dict:
    """sync_release_hash.py 자동 호출 (TASK-V0726-003 post-step) + amend 통합 (TASK-V0727-001).

    2-phase:
    1. sync_release_hash.py 자동 호출 — state.json + backlog 의 TBD → *current HEAD* hash
    2. `git add` (sync 의 변경) + `git commit --amend --no-edit` — 1 commit 통합 (별도 fix(state) commit 불필요)

    sync_release_hash.py 는 release_pipeline.py 와 같은 dir (workflow-source/tools/) 에
    위치. REPO_ROOT 와 무관하게 __file__ 의 parents[1] (workflow-source/tools/) 기준.

    Args:
        version: new version (e.g. "0.7.29").

    Returns:
        dict with keys: ok (bool), sync_result (subprocess result), amend_result (subprocess result),
        final_hash (amend 후의 HEAD short SHA, 또는 None).
        sync_release_hash.py 또는 git amend 의 returncode != 0 면 ok = False.
    """
    sync_tool = Path(__file__).resolve().parent / "sync_release_hash.py"
    if not sync_tool.exists():
        return {
            "ok": False, "sync_result": None, "amend_result": None, "final_hash": None,
            "error": f"sync_release_hash.py not found: {sync_tool}",
        }
    version_arg = f"v{version}" if not version.startswith("v") else version

    # Phase 1: sync_release_hash 호출
    proc_sync = subprocess.run(
        [sys.executable, str(sync_tool), f"--version={version_arg}", "--apply"],
        capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT),
    )
    sync_result = {
        "stdout": proc_sync.stdout,
        "stderr": proc_sync.stderr,
        "returncode": proc_sync.returncode,
    }
    if proc_sync.returncode != 0:
        return {
            "ok": False, "sync_result": sync_result, "amend_result": None, "final_hash": None,
            "error": f"sync_release_hash.py failed (returncode={proc_sync.returncode}): {proc_sync.stderr}",
        }

    # Phase 2: git add (sync 의 변경) + git commit --amend --no-edit (1 commit 통합)
    # amend 시 *HEAD* 의 *직전* commit (feat or chore) 이 amend 됨
    # sync_release_hash 의 변경 = state.json + backlog 의 TBD → HEAD hash
    # *이미* amend 후 의 *HEAD* 의 본 release 의 chore commit hash 와 정합
    proc_add = subprocess.run(
        ["git", "add", "-A"],
        capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT),
    )
    add_result = {
        "stdout": proc_add.stdout,
        "stderr": proc_add.stderr,
        "returncode": proc_add.returncode,
    }
    if proc_add.returncode != 0:
        return {
            "ok": False, "sync_result": sync_result, "amend_result": add_result, "final_hash": None,
            "error": f"git add failed (returncode={proc_add.returncode}): {proc_add.stderr}",
        }

    proc_amend = subprocess.run(
        ["git", "commit", "--amend", "--no-edit"],
        capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT),
    )
    amend_result = {
        "stdout": proc_amend.stdout,
        "stderr": proc_amend.stderr,
        "returncode": proc_amend.returncode,
    }
    if proc_amend.returncode != 0:
        return {
            "ok": False, "sync_result": sync_result, "amend_result": amend_result, "final_hash": None,
            "error": f"git commit --amend failed (returncode={proc_amend.returncode}): {proc_amend.stderr}",
        }

    # final hash (amend 후의 HEAD)
    # 2-step: full SHA → short=7 (F-7+ 의 정공법, v0.7.26)
    proc_full = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=5, cwd=str(REPO_ROOT),
    )
    if proc_full.returncode == 0 and proc_full.stdout.strip():
        head_full = proc_full.stdout.strip()
        proc_short = subprocess.run(
            ["git", "rev-parse", "--short=7", head_full],
            capture_output=True, text=True, timeout=5, cwd=str(REPO_ROOT),
        )
        if proc_short.returncode == 0 and proc_short.stdout.strip():
            final_hash = proc_short.stdout.strip()[:7]
        else:
            final_hash = None
    else:
        final_hash = None

    return {
        "ok": True, "sync_result": sync_result, "amend_result": amend_result, "final_hash": final_hash,
        "error": None,
    }


# ---------------------------------------------------------------------------
# 3. note-draft
# ---------------------------------------------------------------------------


def collect_commits_since(from_tag: str) -> list[dict]:
    """git log <from_tag>..HEAD 의 commit 목록."""
    proc = subprocess.run(
        ["git", "log", f"{from_tag}..HEAD", "--pretty=format:%h|%s|%an|%ai"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30,
    )
    if proc.returncode != 0:
        return []
    rows = []
    for line in proc.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 3)
        if len(parts) == 4:
            rows.append({
                "short": parts[0], "subject": parts[1],
                "author": parts[2], "date": parts[3][:10],
            })
    return rows


def draft_release_note(to_version: str, commits: list[dict], from_tag: str) -> str:
    """release note skeleton 자동 생성.

    기존 Beta-v<X>.<Y>.<Z>.md 의 패턴 따름:
    - TL;DR + 핵심 추가
    - Commit
    - Reference
    """
    today = datetime.now().strftime("%Y-%m-%d")
    feat_commits = [c for c in commits if c["subject"].startswith("feat")]
    chore_commits = [c for c in commits if c["subject"].startswith("chore")]
    docs_commits = [c for c in commits if c["subject"].startswith("docs")]

    lines = [
        f"# Beta v{to_version} — (자동 생성, 편집 필요) ({today})",
        "",
        "> 본 release note 는 `tools/release_pipeline.py note-draft` 의 *skeleton*.",
        "> commit hash / 본문 / Reference 등을 *수동 편집* 후 `docs/v<X>.<Y>.<Z>-release.md` 로 commit.",
        f"> 범위: `{from_tag}..HEAD` ({len(commits)} commit)",
        "",
        "## TL;DR",
        "",
        f"- {len(feat_commits)} feat / {len(chore_commits)} chore / {len(docs_commits)} docs commit",
        f"- 범위: `{from_tag}..HEAD`",
        "",
        "## 핵심 추가",
        "",
        "### feat",
        "",
    ]
    for c in feat_commits:
        lines.append(f"- `{c['short']}` {c['subject']}")
    if chore_commits:
        lines += ["", "### chore", ""]
        for c in chore_commits:
            lines.append(f"- `{c['short']}` {c['subject']}")
    if docs_commits:
        lines += ["", "### docs", ""]
        for c in docs_commits:
            lines.append(f"- `{c['short']}` {c['subject']}")

    lines += [
        "",
        "## Commit",
        "",
        "| Hash | Subject |",
        "|---|---|",
    ]
    for c in commits[:30]:  # max 30
        lines.append(f"| `{c['short']}` | {c['subject']} |")
    if len(commits) > 30:
        lines.append(f"| ... | ({len(commits) - 30} more) |")

    lines += [
        "",
        "## Reference",
        "",
        f"- 이전 release note: `Beta-v{from_tag.replace('v', '')}.md`",
        f"- memory entry: 추후 추가",
        "",
        "---",
        "",
        f"<!-- Auto-generated by tools/release_pipeline.py note-draft --from={from_tag} --to={to_version} -->",
        "",
    ]
    return "\n".join(lines)


def cmd_note_draft(args) -> dict:
    """git log --since=<from_tag> → release note skeleton."""
    commits = collect_commits_since(args.from_tag)
    if not commits:
        return {"mode": "error", "error": f"no commits since {args.from_tag}"}
    note = draft_release_note(args.to, commits, args.from_tag)
    output_path = RELEASES_DIR / f"Beta-v{args.to}.md"
    if args.dry_run:
        return {
            "mode": "dry-run",
            "output_path": str(output_path.relative_to(REPO_ROOT)),
            "commits": len(commits),
            "preview_first_500": note[:500],
        }
    output_path.write_text(note)
    return {
        "mode": "applied",
        "output_path": str(output_path.relative_to(REPO_ROOT)),
        "commits": len(commits),
    }


# ---------------------------------------------------------------------------
# 3.5 changelog-gen (Phase 4 — v0.7.14+)
# ---------------------------------------------------------------------------


RELEASE_RE = re.compile(r"\(v(\d+\.\d+(?:\.\d+)?)\)")
# commit subject prefix → Keep-a-Changelog section mapping
SECTION_PREFIXES = {
    "feat": "Added",
    "fix": "Fixed",
    "docs": "Changed",  # docs 변경 → Changed (Keep-a-Changelog 의 "Changed" 섹션)
    "refactor": "Changed",
    "perf": "Changed",
    "chore": "Changed",  # chore 는 빌드/CI → Changed 로 흡수 (Keep-a-Changelog 표준)
    "test": "Changed",
    "build": "Changed",
    "ci": "Changed",
}


def collect_commits_all_time() -> list[dict]:
    """git log all-time 의 commit (subject 의 vX.Y.Z 추출).

    v0.7.15+ deprecation: prefer collect_commits_in_range(from_ref, to_ref).
    """
    proc = subprocess.run(
        ["git", "log", "--all", "--pretty=format:%h|%H|%an|%ai|%s"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        return []
    return _parse_git_log(proc.stdout)


def collect_commits_in_range(from_ref: str | None, to_ref: str = "HEAD") -> list[dict]:
    """git log <from>..<to> 의 commit. (v0.7.15+ filter).

    Args:
        from_ref: 시작 ref (tag or commit hash). None 이면 --all (전체 history).
        to_ref: 종료 ref (default HEAD).

    Returns:
        commit dict list. from_ref 가 invalid (e.g. unknown tag) 시 empty list + stderr 의 error.
    """
    if from_ref is None:
        return collect_commits_all_time()
    # git log <from>..<to>
    range_arg = f"{from_ref}..{to_ref}"
    proc = subprocess.run(
        ["git", "log", range_arg, "--pretty=format:%h|%H|%an|%ai|%s"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        # from_ref 또는 to_ref invalid. caller 가 error 처리.
        return []
    return _parse_git_log(proc.stdout)


def _parse_git_log(pretty_output: str) -> list[dict]:
    """`git log --pretty=format:...` output → commit dict list (RELEASE_RE parse)."""
    rows = []
    for line in pretty_output.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 4)
        if len(parts) < 5:
            continue
        short, full, author, date, subject = parts
        m = RELEASE_RE.search(subject)
        version = m.group(1) if m else "unreleased"
        rows.append({
            "short": short, "full": full, "author": author,
            "date": date[:10], "subject": subject, "version": version,
        })
    return rows


def categorize_by_section(subject: str) -> str:
    """commit subject prefix → Keep-a-Changelog section."""
    # `feat(...)`, `fix:` 등 첫 token 추출
    m = re.match(r"^([a-zA-Z]+)", subject)
    if not m:
        return "Changed"
    prefix = m.group(1).lower()
    return SECTION_PREFIXES.get(prefix, "Changed")


def draft_changelog(commits: list[dict], unreleased_label: str = "Unreleased") -> str:
    """multi-release commit → Keep-a-Changelog 형식 CHANGELOG.md 본문.

    e.g.:
        # Changelog
        ...
        ## [0.7.10] - 2026-06-14
        ### Added
        - ...
        ### Fixed
        - ...
    """
    # group by version
    by_version: dict[str, list[dict]] = {}
    for c in commits:
        by_version.setdefault(c["version"], []).append(c)

    # version order: 사전 reverse (latest first)
    versions = sorted(by_version.keys(), reverse=True)

    lines = [
        "# Changelog",
        "",
        "All notable changes to this project will be documented in this file.",
        "",
        "본 파일은 `tools/release_pipeline.py changelog-gen` 으로 자동 생성됩니다 (v0.7.14+).",
        "수동 편집도 가능하나 다음 release 시 자동 갱신 시 충돌 가능.",
        "",
    ]

    for ver in versions:
        if ver == "unreleased":
            label = unreleased_label
        else:
            label = ver
        v_commits = by_version[ver]
        # head commit (latest)
        head = v_commits[0]
        # date = head commit 의 date
        lines += [
            f"## [{label}] - {head['date']}",
            "",
        ]
        # section 별 분류
        by_section: dict[str, list[dict]] = {}
        for c in v_commits:
            sec = categorize_by_section(c["subject"])
            by_section.setdefault(sec, []).append(c)
        # section 출력 (Keep-a-Changelog 표준 6 종)
        for sec in ["Added", "Changed", "Fixed", "Deprecated", "Removed", "Security"]:
            if sec not in by_section:
                continue
            lines += [f"### {sec}", ""]
            for c in by_section[sec][:30]:  # max 30
                lines.append(f"- {c['subject']} ({c['short']})")
            if len(by_section[sec]) > 30:
                lines.append(f"- ... ({len(by_section[sec]) - 30} more)")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _resolve_notes_file(version: str, template: str, *, dry_run: bool = False) -> dict:
    """v0.7.24+ --notes-template flag 의 release notes file 결정.

    Templates:
        - default: `Beta-v{version}.md` (기존 동작)
        - detailed: `Beta-v{version}.md` + 1st paragraph (default 와 동일, 명시적)
        - simple: `Beta-v{version}-simple.md` (1 line summary)
        - changelog: `CHANGELOG.md` (Keep-a-Changelog 1.1.0 형식, v0.7.14 의 changelog-gen 의 output)
        - custom:<path>: 임의 path

    Returns:
        {"notes_file": Path, "source": str, "error": str | None}
    """
    template = (template or "default").strip()
    if template == "default" or template == "detailed":
        notes_file = RELEASES_DIR / f"Beta-v{version}.md"
        return {"notes_file": notes_file, "source": template, "error": None}
    elif template == "simple":
        notes_file = RELEASES_DIR / f"Beta-v{version}-simple.md"
        if not notes_file.exists() and not dry_run:
            # simple: default notes 의 1st # 헤더 + 1st ## 헤더 + 1st paragraph 만 자동 generate
            # 본문 추출: 1st # + 1st ## + (1st blank skip) + 본문 line + 2nd blank (paragraph 끝)
            default_notes = RELEASES_DIR / f"Beta-v{version}.md"
            if default_notes.exists():
                content = default_notes.read_text(encoding="utf-8")
                lines = content.split("\n")
                # 1st # 헤더
                first_h1 = next((i for i, l in enumerate(lines) if l.startswith("# ")), -1)
                if first_h1 >= 0:
                    simple_lines: list[str] = []
                    seen_h1 = False
                    seen_first_h2 = False
                    # 1st # 헤더 + 1st ## 헤더 + 본문 (2nd ## 헤더 또는 2nd blank 전까지)
                    # 본문 = 1st ## 헤더 *후* 의 non-blank line 들
                    blank_count = 0
                    in_body = False
                    for i in range(first_h1, len(lines)):
                        line = lines[i]
                        if not seen_h1:
                            if line.startswith("# "):
                                simple_lines.append(line)
                                seen_h1 = True
                            continue
                        if line.startswith("## "):
                            if not seen_first_h2:
                                simple_lines.append(line)
                                seen_first_h2 = True
                                in_body = True
                            else:
                                # 2nd ## 헤더 → 끝
                                break
                        elif line.strip() == "":
                            if in_body:
                                blank_count += 1
                                if blank_count >= 2:
                                    # 2nd blank → 1st paragraph 끝
                                    break
                        else:
                            if in_body:
                                simple_lines.append(line)
                                blank_count = 0
                    notes_file.parent.mkdir(parents=True, exist_ok=True)
                    notes_file.write_text("\n".join(simple_lines).rstrip() + "\n", encoding="utf-8")
        return {"notes_file": notes_file, "source": template, "error": None}
    elif template == "changelog":
        notes_file = REPO_ROOT / "workflow-source" / "CHANGELOG.md"
        return {"notes_file": notes_file, "source": template, "error": None}
    elif template.startswith("custom:"):
        custom_path = Path(template[len("custom:"):])
        if not custom_path.is_absolute():
            custom_path = REPO_ROOT / custom_path
        return {"notes_file": custom_path, "source": template, "error": None}
    else:
        return {
            "notes_file": Path(),
            "source": template,
            "error": f"unknown --notes-template value: {template!r}. Use 'default' / 'detailed' / 'simple' / 'changelog' / 'custom:<path>'",
        }


def cmd_changelog_gen(args) -> dict:
    """multi-release git log → CHANGELOG.md 본문 생성 (Keep-a-Changelog 형식)."""
    from_tag = getattr(args, "from_tag", None)
    to_tag = getattr(args, "to_tag", "HEAD")
    commits = collect_commits_in_range(from_tag, to_tag)
    if not commits:
        if from_tag is not None:
            return {
                "error": f"no commits in range {from_tag}..{to_tag} (from_tag 또는 to_tag invalid 할 수 있음)",
            }
        return {"mode": "error", "error": "no commits in git log"}
    body = draft_changelog(commits, unreleased_label=getattr(args, "unreleased_label", "Unreleased"))
    output_path = Path(args.output) if args.output else (REPO_ROOT / "CHANGELOG.md")
    if args.dry_run:
        return {
            "mode": "dry-run",
            "output_path": str(output_path),
            "commits": len(commits),
            "versions": len(set(c["version"] for c in commits)),
            "from_tag": from_tag,
            "to_tag": to_tag,
            "preview_first_500": body[:500],
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if atomic_write_text is not None:
        atomic_write_text(output_path, body)
    else:
        output_path.write_text(body, encoding="utf-8")
    return {
        "mode": "applied",
        "output_path": str(output_path),
        "commits": len(commits),
        "versions": len(set(c["version"] for c in commits)),
        "from_tag": from_tag,
        "to_tag": to_tag,
    }


def find_dist_files(version: str) -> list[Path]:
    """dist/ 의 wheel + sdist glob. PEP 440 normalize: 0.7.10 → 0.7.10b0."""
    dist = REPO_ROOT / "dist"
    if not dist.exists():
        return []
    # PEP 440: 0.7.10-beta → 0.7.10b0
    base = version.split("-")[0]
    pep_version = base  # wheel 파일명은 X.Y.Z 형태
    return sorted(dist.glob(f"standard_ai_workflow-{pep_version}*"))


# ---------------------------------------------------------------------------
# Drift prevention helpers (v0.11.23+, P1 — doc-headers-update)
# ---------------------------------------------------------------------------

README_PATH = REPO_ROOT.parent / "README.md"
CORE_DOCS_DIR = REPO_ROOT / "core"
DOCS_DIR = REPO_ROOT.parent / "docs"

DOC_HEADER_DATE_RE = re.compile(
    r"^(-\s*최종\s*수정일:\s*)(\d{4}-\d{2}-\d{2})(\s*)$", re.MULTILINE
)


def _iter_doc_markdown_files(scope: str) -> list[Path]:
    """drift-prevention 대상 .md 파일들을 scope 별로 반환.

    scope:
      - 'all'         → README.md + docs/**/*.md + workflow-source/core/*.md
      - 'docs'        → docs/**/*.md 만
      - 'core'        → workflow-source/core/*.md 만
      - 'readme'      → README.md 만
    """
    out: list[Path] = []
    if scope in ("all", "readme") and README_PATH.exists():
        out.append(README_PATH)
    if scope in ("all", "core") and CORE_DOCS_DIR.exists():
        out.extend(sorted(CORE_DOCS_DIR.glob("*.md")))
    if scope in ("all", "docs") and DOCS_DIR.exists():
        out.extend(sorted(DOCS_DIR.rglob("*.md")))
    # de-dup
    seen: set[Path] = set()
    uniq: list[Path] = []
    for p in out:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        uniq.append(p)
    return uniq


def _today_iso() -> str:
    """UTC today ISO date (YYYY-MM-DD)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def cmd_doc_headers_update(args) -> dict:
    """docs/* + workflow-source/core/* + README.md 의 '- 최종 수정일: <date>' 헤더를 일괄 갱신.

    v0.11.23+ 신규. P1 (drift 재발 방지) 의 핵심. 매 release 마다 caller 가
    수동으로 "최종 수정일" 을 갱신하던 부담을 자동화. dry-run 으로 plan 검증 가능.

    Args (Namespace):
      scope    : 'all' (default) | 'docs' | 'core' | 'readme'
      date     : YYYY-MM-DD override (default: UTC today)
      dry_run  : True 면 plan 만 출력, write 안 함.

    Returns: dict { mode, scope, date, scanned, updated, files: [str] }
    """
    scope = getattr(args, "scope", "all") or "all"
    target_date = getattr(args, "date", None) or _today_iso()
    dry_run = getattr(args, "dry_run", False)

    files = _iter_doc_markdown_files(scope)
    updated_paths: list[str] = []
    scanned = 0
    for path in files:
        scanned += 1
        try:
            txt = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = DOC_HEADER_DATE_RE.sub(rf"\g<1>{target_date}\g<3>", txt)
        if new == txt:
            continue
        if dry_run:
            updated_paths.append(str(path.relative_to(REPO_ROOT.parent)))
            continue
        if atomic_write_text is not None:
            atomic_write_text(path, new)
        else:
            path.write_text(new, encoding="utf-8")
        updated_paths.append(str(path.relative_to(REPO_ROOT.parent)))

    return {
        "mode": "dry-run" if dry_run else "applied",
        "scope": scope,
        "date": target_date,
        "scanned": scanned,
        "updated": len(updated_paths),
        "files": updated_paths,
    }


# ---------------------------------------------------------------------------
# Release note frontmatter sync — v0.11.23+ (P2 — sync-maturity-matrix)
# ---------------------------------------------------------------------------
#
# Release note `Beta-v<X>.<Y>.<Z>.md` 의 YAML frontmatter 에 다음 key 를 적으면
# cmd_maturity_matrix_sync 가 workflow-source/core/maturity_matrix.json 을 자동 patch 한다.
#
# ---
# closed_phases: [11]
# promoted_skills:
#   - { name: session-start, to: stable, release: v0.11.19 }
# added_harnesses:
#   - { name: codewhale, release: v0.10.4 }
# deprecated_symbols:
#   - { module: phishing_federation_v4, name: fetch_federated_phishing_urls_v4, release: v0.9.0 }
# ---
#
# 본 frontmatter schema 는 release note 의 첫 `---`/`---` block 안에 위치.


_RE_FRONTMATTER_BLOCK = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def _parse_release_note_frontmatter(path: Path) -> tuple[dict, str]:
    """Release note 의 첫 YAML frontmatter block 을 parse. 본 frontmatter 의 *subset* 만 지원:

      key: value
      key: [v1, v2]
      key:
        - item
        - { name: x, release: y }

    Returns: ({parsed dict}, rest_of_text)
    """
    text = path.read_text(encoding="utf-8")
    m = _RE_FRONTMATTER_BLOCK.match(text)
    if not m:
        return {}, text
    block = m.group(1)
    rest = text[m.end():]
    parsed: dict = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s or s.startswith("#"):
            i += 1
            continue
        m2 = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if not m2:
            i += 1
            continue
        key = m2.group(1)
        rest_val = m2.group(2).strip()
        if rest_val == "":
            items: list = []
            j = i + 1
            while j < len(lines):
                child = lines[j]
                if not (child.startswith((" ", "\t"))):
                    break
                stripped = child.strip()
                if stripped.startswith("- "):
                    one = stripped[2:].strip()
                    if one.startswith("{") and one.endswith("}"):
                        items.append(_parse_inline_obj(one[1:-1]))
                    elif one.startswith("[") and one.endswith("]"):
                        items.append(_parse_inline_list(one[1:-1]))
                    else:
                        items.append(_scalar_or_str(one))
                j += 1
            parsed[key] = items
            i = j
            continue
        if rest_val.startswith("[") and rest_val.endswith("]"):
            parsed[key] = _parse_inline_list(rest_val[1:-1])
        elif rest_val.startswith("{") and rest_val.endswith("}"):
            parsed[key] = _parse_inline_obj(rest_val[1:-1])
        elif rest_val.lower() in ("true", "false"):
            parsed[key] = rest_val.lower() == "true"
        elif re.match(r"^-?\d+$", rest_val):
            parsed[key] = int(rest_val)
        else:
            parsed[key] = _scalar_or_str(rest_val.strip('"').strip("'"))
        i += 1
    return parsed, rest


def _parse_inline_list(body: str) -> list:
    out: list = []
    cur = ""
    depth = 0
    for ch in body:
        if ch in "[{": depth += 1
        elif ch in "]}": depth -= 1
        if ch == "," and depth == 0:
            s = cur.strip()
            cur = ""
            if s:
                out.append(_scalar_or_str(s))
            continue
        cur += ch
    if cur.strip():
        out.append(_scalar_or_str(cur.strip()))
    return out


def _parse_inline_obj(body: str) -> dict:
    """`name: value, name: value` 형식의 inline dict object 를 parse.

    본 frontmatter 의 subset 만 지원 — 값 은 string / int / bool (scalar) 만, nested ❌.
    """
    out: dict = {}
    items = _split_top_level(body, ",")
    for item in items:
        if ":" not in item:
            continue
        # 첫 `:` 만 split 로 사용.
        key, _, val = item.partition(":")
        k = key.strip()
        v = val.strip().strip('"').strip("'")
        if k:
            out[k] = _scalar_or_str(v)
    return out


def _split_top_level(body: str, sep: str) -> list[str]:
    """bracket depth 를 추적하면서 top-level `sep` 으로 split. nested 가 있어도 안전."""
    out: list[str] = []
    cur = ""
    depth = 0
    for ch in body:
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ""
            continue
        cur += ch
    if cur.strip():
        out.append(cur)
    return out


def _scalar_or_str(s: str):
    if s.lower() == "true": return True
    if s.lower() == "false": return False
    if re.match(r"^-?\d+$", s): return int(s)
    return s


def cmd_maturity_matrix_sync(args) -> dict:
    """Release note 의 frontmatter 를 읽어 maturity_matrix.json 의 SSOT 를 자동 patch.

    P2 핵심. closed_phases → done, promoted_skills → stage 전이 + provenance,
    added_harnesses → supported append. last_updated 도 today 로 갱신.

    Args (Namespace):
      from_release_note: Release note 경로 (required, YAML frontmatter 의 source)
      dry_run           : True 면 plan 만 출력, write 안 함.

    Returns: dict { mode, applied: [str], skipped: [str], files: [str], summary }
    """
    from_release_note = Path(args.from_release_note)
    if not from_release_note.exists():
        return {"mode": "error", "error": f"release note not found: {from_release_note}"}
    dry_run = getattr(args, "dry_run", False)

    fm, _rest = _parse_release_note_frontmatter(from_release_note)
    closed_phases = fm.get("closed_phases") or []
    promoted_skills = fm.get("promoted_skills") or []
    added_harnesses = fm.get("added_harnesses") or []
    deprecated_symbols = fm.get("deprecated_symbols") or []

    maturity_path = REPO_ROOT / "core" / "maturity_matrix.json"
    mm = json.loads(maturity_path.read_text(encoding="utf-8"))

    applied_ops: list[str] = []

    for phase_num in closed_phases:
        key = f"Phase {phase_num}"
        if key in mm["milestones"]:
            if mm["milestones"][key]["status"] != "done":
                mm["milestones"][key]["status"] = "done"
                applied_ops.append(f"phase:{key}→done")

    for entry in promoted_skills:
        if isinstance(entry, dict):
            name = entry.get("name", "")
            to_stage = entry.get("to", "stable")
            release = entry.get("release", "")
            if name in mm["skills"]:
                skill = mm["skills"][name]
                if skill["stage"] != to_stage:
                    skill["stage"] = to_stage
                    applied_ops.append(f"skill:{name}→{to_stage}")
                if release and "promoted_in_release" not in skill:
                    skill["promoted_in_release"] = release
                    applied_ops.append(f"skill:{name}.promoted_in_release=+{release}")

    for entry in added_harnesses:
        if isinstance(entry, dict):
            name = entry.get("name", "")
            release = entry.get("release", "")
            if name:
                supported = mm.setdefault("harnesses", {}).setdefault("supported", [])
                if name not in supported:
                    supported.append(name)
                    applied_ops.append(f"harness:{name}+supported")
                if release:
                    mm["harnesses"].setdefault("added_harness_log", []).append(
                        {"name": name, "release": release}
                    )

    for entry in deprecated_symbols:
        if isinstance(entry, dict):
            mod = entry.get("module", "")
            sym = entry.get("name", "")
            release = entry.get("release", "")
            if mod and sym:
                log = mm.setdefault("deprecation_log", [])
                log.append({"module": mod, "name": sym, "release": release})
                applied_ops.append(f"deprecated:{mod}.{sym}@{release}")

    mm["last_updated"] = _today_iso()

    summary = (
        f"closed_phases={len(closed_phases)} promoted_skills={len(promoted_skills)} "
        f"added_harnesses={len(added_harnesses)} deprecated_symbols={len(deprecated_symbols)}"
    )

    if dry_run:
        return {
            "mode": "dry-run",
            "applied": applied_ops,
            "summary": summary,
            "last_updated_after": mm["last_updated"],
            "files": [str(maturity_path.relative_to(REPO_ROOT.parent))],
        }

    # apply
    if atomic_write_json is not None:
        atomic_write_json(maturity_path, mm, indent=2, ensure_ascii=False)
    else:
        maturity_path.write_text(
            json.dumps(mm, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return {
        "mode": "applied",
        "applied": applied_ops,
        "summary": summary,
        "last_updated_after": mm["last_updated"],
        "files": [str(maturity_path.relative_to(REPO_ROOT.parent))],
    }


# ---------------------------------------------------------------------------
# Phase 13 AC3 self-recovering (v0.13.2+)
# ---------------------------------------------------------------------------
#
# drift prevention smoke (check_drift_prevention_v0_11_23.py) 의 6 case 가
# 검출한 drift 를 *자동 fix* 한다. 1-cycle close:
#   1. detect — smoke subprocess 실행, 6 case PASS/FAIL parse
#   2. classify — FAIL 중 auto-fixable / manual_required 분리
#   3. fix — auto-fixable case 각각 매핑된 fix 함수 호출
#   4. re-check — 동일 smoke 재실행 → 6/6 PASS 확인
#   5. emit — recovered / manual_required / re_check_pass 를 dict 로 반환
#             cmd_release 가 release note body 에 "## Self-recovery log" 섹션
#             자동 append.

# 6 case 의 fix 분류 매핑 (v0.13.2 baseline). 새 case 추가 시 본 dict 만 갱신.
# key = smoke 의 case func 이름, value = ("auto"|"manual", fix_callable_or_None)
_SELF_RECOVER_CASE_MAP: dict[str, tuple[str, str | None]] = {
    "test_case_1_pyproject_loud_fallback_sync": ("auto", "_fix_loud_fallback"),
    "test_case_2_maturity_matrix_phase_status": ("manual", None),
    "test_case_3_skill_stage_matches_promotion_set": ("manual", None),
    "test_case_4_readme_header_version_sync": ("auto", "_fix_readme_header_version"),
    "test_case_5_harness_supported_ssot_alignment": ("auto", "_fix_maturity_matrix_drift"),
    "test_case_6_maturity_last_updated_freshness": ("auto", "_fix_maturity_matrix_drift"),
}


def _classify_drift_failures(cases_fail: list[str]) -> tuple[list[str], list[str]]:
    """FAIL case 들을 (auto_fixable, manual_required) 2-bucket 분리.

    _SELF_RECOVER_CASE_MAP 정합 — 미등록 case 는 manual_required (fail-safe).
    """
    auto_fixable: list[str] = []
    manual_required: list[str] = []
    for case_name in cases_fail:
        entry = _SELF_RECOVER_CASE_MAP.get(case_name)
        if entry is None:
            manual_required.append(case_name)  # 미등록 → 보수적 manual
            continue
        bucket, _fix = entry
        (auto_fixable if bucket == "auto" else manual_required).append(case_name)
    return auto_fixable, manual_required


def _read_pyproject_version_str() -> str:
    """pyproject.toml [project] version 을 string 으로 read. atomic_write_text 의 source."""
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]


def _fix_loud_fallback() -> dict:
    """workflow_kit/__init__.py 의 loud fallback literal 을 pyproject version 으로 정합.

    return "v<X.Y.Z>-beta" 의 literal 을 regex 로 교체. pyproject 의 'X.Y.Z' 와
    suffix ('-beta' or '') 를 모두 정합.
    """
    if atomic_write_text is None:
        return {"ok": False, "error": "atomic_write_text unavailable"}
    py_v = _read_pyproject_version_str()
    src = WORKFLOW_KIT_INIT.read_text(encoding="utf-8")
    new_literal = f'return "v{py_v}-beta"'
    new_src, n = re.subn(r'return "v[\d.]+(?:-beta)?"', new_literal, src, count=1)
    if n == 0:
        return {"ok": False, "error": "loud fallback literal not found"}
    atomic_write_text(WORKFLOW_KIT_INIT, new_src)
    return {"ok": True, "old": "loud_fallback", "new": py_v, "file": str(WORKFLOW_KIT_INIT.relative_to(REPO_ROOT))}


def _fix_readme_header_version() -> dict:
    """README.md 의 '- 버전: vX.Y.Z-beta' 헤더 라인을 pyproject 와 정합."""
    if atomic_write_text is None:
        return {"ok": False, "error": "atomic_write_text unavailable"}
    py_v = _read_pyproject_version_str()
    src = README_PATH.read_text(encoding="utf-8")
    new_src, n = re.subn(r"- 버전: v[\d.]+-beta", f"- 버전: v{py_v}-beta", src, count=1)
    if n == 0:
        return {"ok": False, "error": "README header version line not found"}
    atomic_write_text(README_PATH, new_src)
    try:
        rel = str(README_PATH.relative_to(REPO_ROOT))
    except ValueError:
        rel = str(README_PATH.relative_to(REPO_ROOT.parent))
    return {"ok": True, "old": "readme_header", "new": py_v, "file": rel}


def _fix_maturity_matrix_drift() -> dict:
    """case 5 / case 6 의 maturity_matrix drift 를 cmd_maturity_matrix_sync 로 fix.

    release note 의 frontmatter 가 source. 부재 시 last_updated 만 갱신 (case 6 fix).
    """
    # release note 가 있으면 frontmatter 기반 sync. 없으면 last_updated 만 갱신.
    try:
        version = read_version()
        notes_resolution = _resolve_notes_file(version, "default", dry_run=False)
        notes_file = notes_resolution.get("notes_file")
        if notes_file and Path(notes_file).exists():
            smm_ns = argparse.Namespace(
                from_release_note=str(notes_file),
                dry_run=False,
                apply=True,
                json=False,
            )
            return cmd_maturity_matrix_sync(smm_ns)
        # release note 부재: last_updated 만 today 로 patch.
        maturity_path = REPO_ROOT / "core" / "maturity_matrix.json"
        mm = json.loads(maturity_path.read_text(encoding="utf-8"))
        mm["last_updated"] = _today_iso()
        if atomic_write_json is not None:
            atomic_write_json(maturity_path, mm, indent=2, ensure_ascii=False)
        else:
            maturity_path.write_text(
                json.dumps(mm, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return {"ok": True, "mode": "last_updated_only", "last_updated_after": mm["last_updated"]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _run_drift_prevention_smoke() -> dict:
    """drift prevention smoke 를 subprocess 로 inline 실행.

    Returns:
        dict with fields:
            guard_status: 'pass' | 'fail' | 'error'
            cases_pass: int
            cases_fail: int
            cases_total: int
            cases_fail_names: list[str]
            runtime_ms: int
    """
    import subprocess
    import time

    smoke_path = REPO_ROOT / "tests" / "check_drift_prevention_v0_11_23.py"
    if not smoke_path.exists():
        return {"guard_status": "error", "cases_pass": 0, "cases_fail": 0,
                "cases_total": 0, "cases_fail_names": [], "runtime_ms": 0,
                "error": f"smoke not found: {smoke_path}"}

    started = time.monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, str(smoke_path)],
            cwd=str(REPO_ROOT),
            capture_output=True, text=True, check=False, timeout=30,
        )
    except subprocess.TimeoutExpired:
        return {"guard_status": "error", "cases_pass": 0, "cases_fail": 0,
                "cases_total": 0, "cases_fail_names": [], "runtime_ms": 30000,
                "error": "smoke timeout (>30s)"}

    runtime_ms = int((time.monotonic() - started) * 1000)
    stdout = completed.stdout or ""
    cases_pass = re.findall(r"^\s*PASS:\s+(\S+)", stdout, flags=re.MULTILINE)
    cases_fail = re.findall(r"^\s*FAIL:\s+(\S+)", stdout, flags=re.MULTILINE)
    summary_match = re.search(r"=== (PASS|FAIL):\s*(\d+)/6 ===", stdout)
    total = (int(summary_match.group(2)) if summary_match else len(cases_pass) + len(cases_fail))

    if completed.returncode == 0 and not cases_fail:
        return {
            "guard_status": "pass",
            "cases_pass": len(cases_pass) or 6,
            "cases_fail": 0,
            "cases_total": 6,
            "cases_fail_names": [],
            "runtime_ms": runtime_ms,
        }
    return {
        "guard_status": "fail",
        "cases_pass": len(cases_pass),
        "cases_fail": len(cases_fail),
        "cases_total": total or 6,
        "cases_fail_names": cases_fail,
        "runtime_ms": runtime_ms,
    }


def _emit_recovery_summary(recovered: list[dict], manual_required: list[str],
                           re_check: dict, dry_run: bool) -> dict:
    """recovered + manual_required + re-check 결과를 1 dict 로 emit.

    cmd_release 가 release note 본문에 본 dict 를 append 할 수 있도록 shape 안정.
    """
    return {
        "mode": "dry-run" if dry_run else "applied",
        "recovered": recovered,
        "manual_required": manual_required,
        "re_check": re_check,
        "summary": (
            f"recovered={len(recovered)} manual_required={len(manual_required)} "
            f"re_check_status={re_check.get('guard_status', 'unknown')}"
        ),
    }


def cmd_self_recover(args) -> dict:
    """Phase 13 AC3 — drift 발견 시 자동 fix + release note log emit (v0.13.2+).

    detect (smoke subprocess) → classify (auto/manual 2-bucket) → fix (auto case 만) →
    re-check (smoke 재실행) → emit (dict).

    Args (Namespace):
        dry_run: True 면 fix 안 함, plan 만 emit. default True.
        apply: True 면 fix 실행. --dry-run 과 배타적.
        json: stdout JSON.

    Returns:
        dict { mode, recovered, manual_required, re_check, summary, detection }
    """
    dry_run = getattr(args, "dry_run", False)
    apply = getattr(args, "apply", False)
    if apply and not dry_run:
        # _attr_ns 에서 apply=True 가 default 인 release step 과 정합
        pass

    # 1. detect
    detection = _run_drift_prevention_smoke()

    if detection["guard_status"] == "pass":
        # drift 없음 — 즉시 pass
        return _emit_recovery_summary(
            recovered=[],
            manual_required=[],
            re_check=detection,
            dry_run=dry_run,
        ) | {"detection": detection}

    if detection["guard_status"] == "error":
        return _emit_recovery_summary(
            recovered=[],
            manual_required=[],
            re_check=detection,
            dry_run=dry_run,
        ) | {"detection": detection, "error": detection.get("error", "smoke error")}

    # 2. classify
    auto_fixable, manual_required = _classify_drift_failures(detection["cases_fail_names"])

    # 3. fix (auto case 만)
    recovered: list[dict] = []
    if not dry_run:
        for case_name in auto_fixable:
            entry = _SELF_RECOVER_CASE_MAP[case_name]
            fix_callable_name = entry[1]
            fix_fn = globals().get(fix_callable_name) if fix_callable_name else None
            if fix_fn is None:
                continue
            try:
                result = fix_fn()
                recovered.append({"case": case_name, "fix": fix_callable_name, "result": result})
            except Exception as e:  # noqa: BLE001
                recovered.append({"case": case_name, "fix": fix_callable_name,
                                  "result": {"ok": False, "error": f"{type(e).__name__}: {e}"}})
    else:
        # dry-run: fix skip, plan 만 emit
        for case_name in auto_fixable:
            entry = _SELF_RECOVER_CASE_MAP[case_name]
            recovered.append({"case": case_name, "fix": entry[1], "result": {"ok": True, "dry_run": True}})

    # 4. re-check (fix 후 smoke 재실행)
    re_check = _run_drift_prevention_smoke()

    return _emit_recovery_summary(recovered, manual_required, re_check, dry_run) | {
        "detection": detection,
    }


# ---------------------------------------------------------------------------
# Phase 13 AC4+ bidir-link (v0.13.3+, wiki ↔ memory)
# ---------------------------------------------------------------------------


def cmd_bidir_link(args) -> dict:
    """Phase 13 AC4+ — wiki ↔ memory 양방향 link 자동화 (v0.13.3+).

    default: audit (R-C, read-only).
    --apply: sync (R-A, memory entry.mentioned_in → wiki related_pages 자동 갱신).

    sync --apply 시 pre-audit (drift 검출) → fix (sync) → post-audit (re-check, 정합 확인)
    의 1-cycle orchestrator (v0.13.2 self-recover 와 동일 정공법).

    Args (Namespace):
      workspace_root: workspace root (default: REPO_ROOT.parent)
      apply: True 면 sync 실행 (destructive, idempotent).
      json: stdout JSON.

    Returns:
        dict { mode, audit (post-sync), pre_audit (if apply), sync, summary }
    """
    from workflow_kit.common.state.bidir_link import (
        audit_bidirectional_links,
        sync_memory_to_wiki,
    )

    workspace_root = getattr(args, "workspace_root", None)
    ws = Path(workspace_root) if workspace_root else REPO_ROOT.parent

    pre_audit = audit_bidirectional_links(ws)
    apply = getattr(args, "apply", False)

    sync = None
    if apply:
        sync = sync_memory_to_wiki(ws, dry_run=False)
        # post-audit: sync 후 정합 확인
        post_audit = audit_bidirectional_links(ws)
    else:
        post_audit = pre_audit

    result = {
        "mode": "applied" if apply else "audit",
        "audit": {
            "total_wiki_pages": post_audit.total_wiki_pages,
            "total_memory_entries": post_audit.total_memory_entries,
            "symmetric_links": post_audit.symmetric_links,
            "asymmetric_count": len(post_audit.asymmetric),
            "is_symmetric": post_audit.is_symmetric,
            "asymmetric": [
                {"memory_entry_id": a.memory_entry_id, "wiki_page": a.wiki_page, "direction": a.direction}
                for a in post_audit.asymmetric
            ],
            "wiki_pages_with_related_memory": post_audit.wiki_pages_with_related_memory,
            "memory_entries_with_mentioned_wiki": post_audit.memory_entries_with_mentioned_wiki,
        },
        "audited_at": post_audit.audited_at,
    }
    if apply:
        result["pre_audit"] = {
            "asymmetric_count": len(pre_audit.asymmetric),
            "is_symmetric": pre_audit.is_symmetric,
        }
    if sync is not None:
        result["sync"] = {
            "mode": sync.mode,
            "total_changes": sync.total_changes,
            "summary": sync.summary,
            "changes": [
                {"wiki_page": c.wiki_page, "added_paths": c.added_paths,
                 "already_present": c.already_present}
                for c in sync.changes
            ],
        }
    return result


def cmd_release(args) -> dict:
    """GitHub Release 생성 (gh release create).

    v0.11.16+ args normalize: release subcommand argparse 의 attribute 와
    cmd_validate 가 기대하는 attribute 가 비대칭. dispatcher (CLI argparse) 는
    skip_packaging / skip_doctor / skip_state / skip_git / skip_mypy 를 add 안 해서
    args.normalize 없이 cmd_release 진입 시 cmd_validate 호출에서 AttributeError.
    memory #11 의 _make_args 정공법 정합.

    사전 점검: --skip-validate 미지정 시 validate 4 source 자동 호출.
    1+ source fail 시 release 중단 (exit 1).

    **v0.7.18+ release coordination observability**:
    `tag` 결정 후 `git ls-remote origin` 로 *원격 tag 존재 여부* 확인. 존재 시
    - default: exit 1 + auto-bump hint
    - `--auto-bump`: `next_available_version()` 로 다음 version 결정 + version-bump 자동 + re-flow
    v0.7.16 의 race lesson 반영 (memory #22 §release coordination race).

    **v0.11.13+ mypy CI cross-verify**:
    validate 5번째 source mypy (Layer 2, v0.11.12+) 와 GH Actions mypy-strict workflow
    (Layer 1, v0.11.11+) 의 *결과 정합* 을 advisory verify. verdict:
    - "sanity": CI success + local mypy 정합 (release 진행)
    - "drift_warning": CI success 인데 local fail (local drift, advisory)
    - "ci_stale": CI success 인데 headSha != HEAD (re-run 권고)
    - "ci_fail": CI failure (advisory)
    - "absent" / "skipped": gh CLI 부재 / no run (skip, advisory)
    default = advisory (release 진행). `--strict-cross-verify` flag 시 hard fail (drift / ci_stale / ci_fail).

    **v0.13.1+ dashboard post-release emit**:
    `gh release create` 성공 후 dashboard markdown snapshot 을 자동 emit.
    --skip-dashboard-emit 으로 skip 가능. 실패 시 *warning* — release 자체는 성공.
    --dashboard-output PATH 로 출력 위치 override (default: ai-workflow/dashboard/snapshot.md).

    gh auth 인증된 환경 가정. token 회전 부담은 caller 책임.
    """
    # v0.11.16+ args normalize: dispatcher (CLI argparse) 의 release subcommand 는
    # skip_packaging / skip_doctor / skip_state / skip_git / skip_mypy 를 add 안 해서
    # cmd_release 진입 시 cmd_validate 호출에서 AttributeError. memory #11 의 _make_args
    # 정공법 정합 — release library wrapper 가 dispatcher 의 kwargs → Namespace 변환 후
    # *모든 skip flag / optional attr* 의 default fill.
    for attr in ("skip_packaging", "skip_doctor", "skip_state", "skip_git", "skip_mypy",
                 "skip_validate", "skip_cross_verify", "strict_cross_verify",
                 "skip_doc_headers_update", "skip_maturity_matrix_sync",
                 "skip_dashboard_emit", "dashboard_output",
                 "skip_self_recover",
                 "skip_bidir_link"):  # v0.13.3+ Phase 13 AC4+
        if not hasattr(args, attr):
            setattr(args, attr, False if attr == "skip_dashboard_emit" else None)

    def _attr_ns(**overrides) -> argparse.Namespace:
        """Create a fresh argparse.Namespace with default attrs (False) + overrides.

        본 helper 는 cmd_release 내부에서 drift-prevention helpers 를 자동 호출할 때 사용.
        직접 argv → Namespace 변환 없이, 안전 default set 으로 helper 진입 가능.
        """
        base_defaults = {
            "scope": "all",
            "date": None,
            "dry_run": False,
            "from_release_note": None,
            "json": False,
            "apply": True,
        }
        for k, v in base_defaults.items():
            base_defaults.setdefault(k, v)
        ns = argparse.Namespace(**{**base_defaults, **overrides})
        return ns

    results: dict = {"pre_check": {}, "gh_commands": [], "mode": "dry-run" if args.dry_run else "apply"}

    # 1. mypy CI cross-verify (v0.11.13+, Layer 1 ↔ Layer 2 정합 advisory)
    # validate 보다 *먼저* 실행 — advisory 라서 validate fail 시에도 결과 포함.
    # default = advisory (release 진행). --strict-cross-verify 시 hard fail.
    if not getattr(args, "skip_cross_verify", False):
        ci_mypy = _cross_verify_ci_mypy()
        results["ci_mypy"] = ci_mypy
        # CI-only verdict (Layer 1 결과) 저장. final verdict 는 validate 후 결합.
        results["ci_mypy"]["ci_only_verdict"] = ci_mypy.get("verdict")
        ci_verdict = ci_mypy.get("verdict")
        # --strict-cross-verify: ci_stale / ci_fail 시 hard fail
        if getattr(args, "strict_cross_verify", False):
            if ci_verdict in ("ci_stale", "ci_fail"):
                return _attach_release_summary({
                    **results,
                    "error": (
                        f"strict cross-verify failed: ci_mypy.verdict={ci_verdict!r}, "
                        f"message={ci_mypy.get('message')!r}"
                    ),
                })

    # 2. validate (사전 점검)
    if not args.skip_validate:
        val_result = cmd_validate(args)
        results["pre_check"] = val_result
        validate_failed = not all(v.get("ok", False) for v in val_result.values())
    else:
        validate_failed = False

    # 2.5 cross-verify final verdict (Layer 1 CI ↔ Layer 2 local mypy 결합)
    # validate fail 시에도 verdict 는 결합 (output 정합)
    if not getattr(args, "skip_cross_verify", False) and "ci_mypy" in results:
        local_mypy = results["pre_check"].get("mypy", {}) if not args.skip_validate else {}
        final_verdict = _resolve_cross_verify_verdict(results["ci_mypy"], local_mypy)
        results["ci_mypy"]["verdict"] = final_verdict
        results["ci_mypy"]["local_mypy"] = {
            "ok": local_mypy.get("ok") if local_mypy else None,
            "skipped": (not local_mypy) or local_mypy.get("skipped", False),
            "error_count": local_mypy.get("error_count") if local_mypy else None,
        }
        # --strict-cross-verify: final verdict 도 hard fail 대상
        if getattr(args, "strict_cross_verify", False):
            if final_verdict in ("drift_warning", "ci_stale", "ci_fail"):
                return _attach_release_summary({
                    **results,
                    "error": (
                        f"strict cross-verify failed: ci_mypy.verdict={final_verdict!r}, "
                        f"local_mypy={results['ci_mypy']['local_mypy']!r}, "
                        f"message={results['ci_mypy'].get('message')!r}"
                    ),
                })

    # 3. validate fail 시 early return (cross-verify 결과는 이미 results 에 포함됨)
    if validate_failed:
        return _attach_release_summary({**results, "error": "validate failed; abort release"})

    # 2.7 Phase 13 AC3 self-recovering (v0.13.2+) — drift 검출 시 자동 fix.
    # cmd_self_recover 의 emit 결과를 results 에 포함 (release note body injection 의 source).
    # manual_required > 0 이면 early return (drift fix 우선 — 사람의 명시 intervention 필요).
    # escape hatch: --skip-self-recover.
    if not getattr(args, "skip_self_recover", False):
        sr_ns = _attr_ns()
        sr_ns.apply = True
        sr_ns.dry_run = False
        sr_result = cmd_self_recover(sr_ns)
        results["self_recover"] = sr_result
        # manual_required 가 1+ 이면 early return (drift 가 사람이 fix 해야 함).
        if sr_result.get("manual_required"):
            return _attach_release_summary({
                **results,
                "error": (
                    f"self-recover: {len(sr_result['manual_required'])} drift case 가 "
                    f"manual_required (human review 필요): {sr_result['manual_required']}. "
                    f"fix 후 release 재실행 또는 --skip-self-recover 로 진행."
                ),
            })

    # 2.8 Phase 13 AC4+ wiki ↔ memory 양방향 link audit (v0.13.3+).
    # cmd_bidir_link 의 audit 결과를 results 에 포함 (release note body injection 의 source).
    # asymmetric > 0 이면 advisory (release 차단 ❌). wiki 갱신은 자동 (R-A) 가능하지만
    # caller 가 --apply 명시해야 destructive. 본 step 는 default = audit 만.
    # escape hatch: --skip-bidir-link.
    if not getattr(args, "skip_bidir_link", False):
        try:
            bl_ns = _attr_ns()
            bl_ns.workspace_root = None  # default = REPO_ROOT.parent
            bl_ns.apply = False  # release step 은 audit 만 (caller 가 --apply 명시)
            bl_result = cmd_bidir_link(bl_ns)
            results["bidir_link_audit"] = bl_result
        except Exception as exc:  # noqa: BLE001
            results["bidir_link_audit"] = {
                "mode": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }

    # 3.0 drift prevention auto-step (v0.11.23+) — release 시 docs/* / SSOT 자동 동기화.
    # 본 step 는 destructive 하지 않음 (write only on tracked files, atomic_write 보장).
    # escape hatch: --skip-doc-headers-update / --skip-maturity-matrix-sync.
    if not getattr(args, "skip_doc_headers_update", False):
        dhu = cmd_doc_headers_update(_attr_ns())
        results["doc_headers_update"] = dhu
        # P0 smoke fail 가능성: scan 결과 >= 1 인데 updated = 0 인 경우도 정상 (이미 정합).
        # 단, scan 결과 0 이면 silent skip (drift prevention 영역 밖).
    if not getattr(args, "skip_maturity_matrix_sync", False):
        # notes_file 결정은 3.4 step 에서 일어나므로, 그 전에 notes_file 가 이미 있는지 확인
        # (--notes-template 사용 가능). 없으면 skip (release note 가 없는 backfill 시나리오).
        try:
            _notes_template = getattr(args, "notes_template", "default") or "default"
            _notes_resolution = _resolve_notes_file(
                read_version(), _notes_template, dry_run=args.dry_run
            )
            _notes_file = _notes_resolution["notes_file"]
            if _notes_file.exists():
                smm_ns = _attr_ns()
                smm_ns.from_release_note = str(_notes_file)
                smm = cmd_maturity_matrix_sync(smm_ns)
                results["maturity_matrix_sync"] = smm
        except Exception as exc:  # noqa: BLE001
            results["maturity_matrix_sync"] = {
                "mode": "skipped",
                "reason": f"{type(exc).__name__}: {exc}",
            }

    # 2. dist 파일 glob
    # v0.7.13+: --version override (backfill 시 staging 용도). default 는 read_version().
    if getattr(args, "version", None):
        version = args.version
        results["version_source"] = "cli-flag"
    else:
        version = read_version()
        results["version_source"] = "pyproject.toml"

    # v0.7.18+ auto-bump: pre-check 후 tag 결정 전에 호출
    if getattr(args, "auto_bump", False):
        bump_info = next_available_version(version)
        if bump_info["bumped"]:
            version = bump_info["next"]
            results["version_source"] = "auto-bump"
            results["auto_bump"] = bump_info
            # version-bump 자동 적용 (in-place). write_version + write_workflow_kit_version
            write_version(version)
            suffix = "beta"
            if read_workflow_kit_version().endswith("-beta"):
                suffix = "beta"
            elif read_workflow_kit_version().endswith("-alpha"):
                suffix = "alpha"
            else:
                suffix = ""  # default
            write_workflow_kit_version(version, suffix=("-" + suffix) if suffix else "")
        else:
            results["auto_bump"] = bump_info  # bumped=False, info only

    dist_files = find_dist_files(version)
    if not dist_files:
        return _attach_release_summary({**results, "error": f"no dist files found for version {version} (run `python3 -m build` first)"})

    # 3. tag 결정 + 원격 tag pre-check (v0.7.18+)
    tag = f"v{version}-beta"
    # v0.7.24+: --notes-template flag 로 release notes format 자유도
    notes_template = getattr(args, "notes_template", "default") or "default"
    notes_resolution = _resolve_notes_file(version, notes_template, dry_run=args.dry_run)
    if notes_resolution.get("error"):
        return _attach_release_summary({**results, "error": notes_resolution["error"]})
    notes_file = notes_resolution["notes_file"]
    if not notes_file.exists():
        return _attach_release_summary({**results, "error": f"release note not found: {notes_file}"})

    # 3.5 원격 tag pre-check + tag push (v0.7.18+ race lesson, v0.7.21+ follow-up,
    # v0.9.1+ --full-auto: pre-check conflict 시 --auto-bump / --allow-existing-tag 자동 활성화)
    # v0.7.21 fix: tag push 와 release 의 coupling. *순서*:
    #   1. pre-check: remote 에 tag 가 이미 push 됐는지 확인
    #   2. tag push: pre-check fail 시 default = skip, --allow-existing-tag 면 skip + 진행, --auto-bump 면 bump
    #   3. gh release create: --verify-tag 가 tag 의 remote 존재 검증 (pre-check 와 *redundant* 한 부분)
    # v0.9.1+ --full-auto: pre-check fail 시 자동으로 다음 version 결정 (auto-bump 동작) 후
    #   새로 결정된 version 으로 tag + release 재실행. 1-cycle close.
    if not args.dry_run:
        tag_check = _check_remote_tag(tag)
        results["tag_pre_check"] = tag_check
        if tag_check["exists"]:
            # --full-auto: --auto-bump 와 동일 동작 (다음 version 자동 결정) 후 re-flow
            if getattr(args, "full_auto", False) and not getattr(args, "allow_existing_tag", False):
                bump_info = next_available_version(version)
                if bump_info["bumped"]:
                    new_version = bump_info["next"]
                    results["version_source"] = "full-auto-bump"
                    results["auto_bump"] = bump_info
                    # in-place version-bump
                    write_version(new_version)
                    suffix = "beta"
                    if read_workflow_kit_version().endswith("-beta"):
                        suffix = "beta"
                    write_workflow_kit_version(new_version, suffix=("-beta" if suffix else ""))
                    # re-flow with new version
                    version = new_version
                    tag = f"v{version}-beta"
                    dist_files = find_dist_files(version)
                    if not dist_files:
                        return _attach_release_summary({**results, "error": f"no dist files for {version} after --full-auto bump"})
                    tag_check = _check_remote_tag(tag)
                    results["tag_pre_check"] = tag_check
                    results["full_auto_re_tag"] = tag
                    if tag_check["exists"]:
                        # full-auto 도 bump 했는데 여전히 존재 → --allow-existing-tag 활성화
                        results["full_auto_fallback"] = "allow-existing-tag"
            if tag_check.get("exists") and not getattr(args, "allow_existing_tag", False):
                return {
                    **results,
                    "error": (
                        f"remote tag {tag} already exists at {tag_check['remote_url']}. "
                        f"v0.7.16 race 정공법: --auto-bump 으로 다음 version 자동 bump, "
                        f"--allow-existing-tag 으로 *기존 tag* 에 re-attach, "
                        f"--full-auto 으로 1-cycle close, "
                        f"또는 --version=<next> 명시."
                    ),
                }
            # --allow-existing-tag: skip pre-check fail, 그대로 release 진행
            results["tag_pre_check_skipped"] = "allow-existing-tag"

    # 3.6 local tag create + push (v0.7.21+ — tag push 와 release 의 coupling,
    # v0.9.0 chapter 4 fix: local tag create step 추가 — 이전엔 push 만 해서
    # `src refspec does not match any` fail)
    if not args.dry_run:
        tag_create_proc = subprocess.run(
            ["git", "tag", tag, "HEAD"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10,
        )
        results["tag_create"] = {
            "tag": tag,
            "returncode": tag_create_proc.returncode,
            "stdout_tail": tag_create_proc.stdout.strip(),
            "stderr_tail": tag_create_proc.stderr.strip(),
        }
        # tag 가 이미 존재하면 returncode != 0 일 수 있으나, --allow-existing-tag 의 경우
        # 그대로 진행. 그 외는 다음 step (push) 에서 검증.
        push_tag_proc = subprocess.run(
            ["git", "push", "origin", f"refs/tags/{tag}"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30,
        )
        results["tag_push"] = {
            "tag": tag,
            "returncode": push_tag_proc.returncode,
            "stdout_tail": push_tag_proc.stdout.strip().split("\n")[-1] if push_tag_proc.stdout else "",
            "stderr_tail": push_tag_proc.stderr.strip().split("\n")[-1] if push_tag_proc.stderr else "",
        }
        if push_tag_proc.returncode != 0 and not getattr(args, "allow_existing_tag", False):
            return _attach_release_summary({**results, "error": f"git push tag {tag} failed: {push_tag_proc.stderr.strip()}"})
    else:
        # dry-run: pre-check 결과 + warning (plan 검증)
        tag_check = _check_remote_tag(tag)
        results["tag_pre_check"] = tag_check
        if tag_check["exists"]:
            results["tag_pre_check_warning"] = f"remote tag {tag} already exists (dry-run: pre-check only)"

    rel_assets = [str(f.relative_to(REPO_ROOT)) for f in dist_files]
    results["tag"] = tag
    results["assets"] = rel_assets
    # v0.7.24+: notes_file 가 in-repo 면 relative path, 그 외 (예: changelog) 면 absolute
    try:
        results["notes_file"] = str(notes_file.relative_to(REPO_ROOT))
    except ValueError:
        results["notes_file"] = str(notes_file)

    # 4. gh command build
    repo_remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10,
    )
    repo = repo_remote.stdout.strip().replace("https://github.com/", "").replace(".git", "")
    results["repo"] = repo

    gh_cmd = [
        "gh", "release", "create", tag,
        "--repo", repo,
        "--title", f"Beta v{version}",
        "--notes-file", str(notes_file),
        "--target", "main",
        "--verify-tag",
    ] + [str(f) for f in dist_files]
    results["gh_command"] = " ".join(gh_cmd)

    if args.dry_run:
        return results

    # 5. gh auth check + release create
    auth_proc = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=10)
    if auth_proc.returncode != 0:
        return _attach_release_summary({**results, "error": "gh auth not authenticated"})
    results["gh_auth_ok"] = True

    proc = subprocess.run(gh_cmd, capture_output=True, text=True, timeout=120)
    results["gh_exit_code"] = proc.returncode
    if proc.stdout:
        results["gh_stdout_tail"] = proc.stdout.strip().split("\n")[-1]
    if proc.stderr:
        results["gh_stderr_tail"] = proc.stderr.strip().split("\n")[-1]
    if proc.returncode != 0:
        return _attach_release_summary({**results, "error": f"gh release create failed: exit {proc.returncode}"})

    # 6. v0.13.1+ dashboard post-release emit. Warning 만 — release 자체는 성공.
    dashboard_emit = _emit_dashboard_post_release(args, results)
    results["dashboard_emit"] = dashboard_emit
    if dashboard_emit.get("status") == "ok":
        print(f"  [dashboard] {dashboard_emit.get('path', '?')} ({dashboard_emit.get('bytes', 0)} bytes)")
    elif dashboard_emit.get("status") == "skipped":
        print(f"  [dashboard] skipped ({dashboard_emit.get('reason', '')})")
    else:
        print(f"  [dashboard] WARN: {dashboard_emit.get('error', 'unknown error')}")

    # 6.5 v0.13.2+ self-recovery log emit (Phase 13 AC3). release note 본문 끝에 자동 append.
    # results["self_recover"] 가 있을 때만 (drift 가 검출/fix 되었을 때만). 미존재 시 no-op.
    if "self_recover" in results:
        recovery_log = _format_self_recovery_log(results["self_recover"])
        if recovery_log:
            log_emit = _emit_self_recovery_log(args, recovery_log)
            results["self_recovery_log_emit"] = log_emit

    # 6.7 v0.14.6+ maturity_last_updated 자동 갱신 (Task 3 follow-up).
    # v0.15.3+ 변경: release_error (results["error"] 존재) 시에만 maturity refresh
    # 호출. v0.14.6 description 의 "Out of scope v0.15.0" 2건 중 2건 해소.
    # rationale: release 성공 후 (operator 가 이미 gh release create 성공 확인)
    # maturity 자체가 today 면 no-op 인 호출이 dashboard freshness 와 무관 —
    # release_error (gh release create fail) 상황 에서만 operator 가 retry 할
    # 수 있도록 panel 1 freshness 보강. release_error fallback 정공법.
    # v0.15.2+ legacy_memory strict opt-out (--no-legacy-memory) caller 정합 —
    # cmd_refresh_maturity 가 자체 skip + warning emit.
    release_error = "error" in results
    if release_error and not getattr(args, "dry_run", False) and refresh_maturity_last_updated is not None:
        try:
            maturity_result = cmd_refresh_maturity(args)
            results["maturity_refresh"] = maturity_result
            if maturity_result.get("legacy_memory_strict_opt_out"):
                # v0.15.2+ strict opt-out caller — maturity refresh skip.
                print(f"  [maturity] skip (--no-legacy-memory strict opt-out — v0.15.0+ ⚠️ BREAKING caller 정합)")
            elif maturity_result.get("refreshed"):
                print(f"  [maturity] {maturity_result['before']} → {maturity_result['after']} (release_error fallback)")
            else:
                print(f"  [maturity] no-op (already {maturity_result.get('before') or 'today'}) — release_error fallback")
        except Exception as exc:  # noqa: BLE001 — release_error 자체가 이미 set
            results["maturity_refresh"] = {"error": str(exc), "warning": True}
            print(f"  [maturity] WARN: {exc}")
    elif not release_error:
        # v0.15.3+ release 성공 시 maturity refresh skip (rationale 위 주석 참조).
        results["maturity_refresh"] = {
            "skipped_due_to_release_success": True,
            "reason": "v0.15.3+ release 성공 시 maturity refresh skip. release_error fallback 만 호출.",
        }

    # 6.6 v0.13.3+ bidir-link audit log emit (Phase 13 AC4+).
    # results["bidir_link_audit"] 가 있으면 release note 본문 끝에 audit 요약 자동 append.
    if "bidir_link_audit" in results:
        bl_log = _format_bidir_link_audit(results["bidir_link_audit"])
        if bl_log:
            bl_log_emit = _emit_bidir_link_audit_log(args, bl_log)
            results["bidir_link_log_emit"] = bl_log_emit

    return _attach_release_summary(results)


# ---------------------------------------------------------------------------
# 4.5 dashboard emit (v0.13.1+ Phase 13 sub-milestone)
# ---------------------------------------------------------------------------


def _emit_dashboard_post_release(args: argparse.Namespace, results: dict) -> dict:
    """gh release create 성공 후 dashboard markdown snapshot 자동 emit.

    Returns:
        dict with keys:
            status: 'ok' | 'skipped' | 'error'
            path: output file path (str, status='ok' 시)
            bytes: output file size (int, status='ok' 시)
            reason: skip reason (str, status='skipped' 시)
            error: error message (str, status='error' 시)
            executed_at: ISO 8601 timestamp (status='ok' 시)
            duration_ms: int (status='ok' 시)
    """
    skip = bool(getattr(args, "skip_dashboard_emit", False))
    if skip:
        return {"status": "skipped", "reason": "--skip-dashboard-emit"}

    # Project root = git repo root = REPO_ROOT.parent (workflow-source/tools/ 의 부모의 부모).
    # ai-workflow/ 는 project root 아래에 있으므로 dashboard CLI 의 _repo_root() 와 정합.
    project_root = REPO_ROOT.parent
    output = getattr(args, "dashboard_output", None)
    if not output:
        output = "ai-workflow/dashboard/snapshot.md"

    dashboard_path = project_root / output
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)

    cli_module = "workflow_kit.workflow_kit_cli"
    cmd = [
        sys.executable, "-m", cli_module,
        "--command=dashboard",
        "--format=markdown",
        f"--output={dashboard_path}",
    ]

    import time
    started = time.monotonic()
    # PYTHONPATH 에 workflow-source (= REPO_ROOT) 를 prepend. CI / release context
    # 에서 subprocess 가 workflow_kit 모듈을 import 할 수 있도록. check_packaging 의
    # *clean_env* 패턴의 반대 방향 — 본 helper 는 workflow_kit 이 *필요* 한 케이스.
    sub_env = os.environ.copy()
    existing_pp = sub_env.get("PYTHONPATH", "")
    sub_env["PYTHONPATH"] = (
        f"{REPO_ROOT}{os.pathsep}{existing_pp}" if existing_pp else str(REPO_ROOT)
    )
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
            env=sub_env,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        if completed.returncode != 0:
            return {
                "status": "error",
                "error": (
                    f"{cli_module} returned {completed.returncode}; "
                    f"stderr_tail: {(completed.stderr or '').strip().split(chr(10))[-1][:200]}"
                ),
            }
        if not dashboard_path.is_file():
            return {
                "status": "error",
                "error": f"{dashboard_path} not created despite rc=0",
            }
        # path 표시는 project_root 기준 relative (absolute path 입력이면 그대로 노출).
        try:
            display_path = str(dashboard_path.relative_to(project_root))
        except ValueError:
            display_path = str(dashboard_path)
        return {
            "status": "ok",
            "path": display_path,
            "bytes": dashboard_path.stat().st_size,
            "executed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration_ms": duration_ms,
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "dashboard emit timeout (60s)"}
    except (OSError, ValueError) as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# 4.6 self-recovery log emit (v0.13.2+ Phase 13 AC3 close-out)
# ---------------------------------------------------------------------------


def _format_self_recovery_log(sr_result: dict) -> str:
    """cmd_self_recover 의 results dict 를 release note 본문용 markdown 문자열로 format.

    drift 가 없거나 (`recovered=[]` + `manual_required=[]`) 면 빈 문자열 반환.
    """
    recovered = sr_result.get("recovered") or []
    manual_required = sr_result.get("manual_required") or []
    re_check = sr_result.get("re_check") or {}
    if not recovered and not manual_required:
        return ""
    lines = ["", "## Self-recovery log", ""]
    lines.append(f"_자동 emit (Phase 13 AC3, {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')})_")
    lines.append("")
    if recovered:
        lines.append(f"### 자동 fix ({len(recovered)}건)")
        lines.append("")
        for r in recovered:
            case = r.get("case", "?")
            fix = r.get("fix", "?")
            res = r.get("result", {})
            file_hint = res.get("file", "")
            new_val = res.get("new", "")
            lines.append(f"- `{case}` → `{fix}`")
            if new_val:
                lines.append(f"  - new value: `{new_val}`")
            if file_hint:
                lines.append(f"  - file: `{file_hint}`")
        lines.append("")
    if manual_required:
        lines.append(f"### Manual required ({len(manual_required)}건)")
        lines.append("")
        lines.append("- " + "\n- ".join(manual_required))
        lines.append("")
    lines.append(f"_re-check status: **{re_check.get('guard_status', 'unknown')}** "
                 f"(pass={re_check.get('cases_pass', '?')}/fail={re_check.get('cases_fail', '?')}/total={re_check.get('cases_total', '?')})_")
    return "\n".join(lines) + "\n"


def _emit_self_recovery_log(args: argparse.Namespace, recovery_log: str) -> dict:
    """release note 본문 끝에 self-recovery log append (Phase 13 AC3 close-out).

    release note 가 없거나 (backfill 시나리오) recovery_log 가 empty 면 no-op.
    """
    try:
        version = getattr(args, "version", None) or read_version()
        notes_resolution = _resolve_notes_file(version, "default", dry_run=False)
        notes_file = notes_resolution.get("notes_file")
        if not notes_file or not Path(notes_file).exists():
            return {"status": "skipped", "reason": "release note not found (backfill scenario)"}
        body = Path(notes_file).read_text(encoding="utf-8")
        # "## Self-recovery log" 헤더가 이미 있으면 중복 append 방지 (idempotent).
        marker = "## Self-recovery log"
        if marker in body:
            return {"status": "skipped", "reason": "self-recovery log already present (idempotent)"}
        new_body = body.rstrip("\n") + "\n" + recovery_log
        if atomic_write_text is not None:
            atomic_write_text(notes_file, new_body)
        else:
            notes_file.write_text(new_body, encoding="utf-8")
        return {
            "status": "ok",
            "path": str(notes_file),
            "bytes_appended": len(recovery_log),
        }
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# 4.7 Phase 13 AC4+ bidir-link audit log emit (v0.13.3+)
# ---------------------------------------------------------------------------


def _format_bidir_link_audit(audit_result: dict) -> str:
    """cmd_bidir_link audit dict → release note body markdown 문자열.

    asymmetric_count > 0 이면 비고 (advisory). 0 이면 *대칭* 표시.
    """
    audit = audit_result.get("audit") or {}
    if not audit:
        return ""
    lines = ["", "## Bidirectional link audit", ""]
    is_symmetric = bool(audit.get("is_symmetric"))
    lines.append(f"_자동 emit (Phase 13 AC4+, {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')})_")
    lines.append("")
    lines.append(f"- total wiki pages: **{audit.get('total_wiki_pages', 0)}**")
    lines.append(f"- total memory entries: **{audit.get('total_memory_entries', 0)}**")
    lines.append(f"- symmetric links: **{audit.get('symmetric_links', 0)}**")
    lines.append(f"- asymmetric count: **{audit.get('asymmetric_count', 0)}**")
    lines.append(f"- wiki pages with related memory: **{audit.get('wiki_pages_with_related_memory', 0)}**")
    lines.append(f"- memory entries with mentioned wiki: **{audit.get('memory_entries_with_mentioned_wiki', 0)}**")
    lines.append(f"- is_symmetric: **{is_symmetric}**")
    asymmetric = audit.get("asymmetric") or []
    if asymmetric:
        lines.append("")
        lines.append("### Asymmetric links (advisory)")
        lines.append("")
        for a in asymmetric[:20]:  # 최대 20건만 표시
            lines.append(f"- `{a['direction']}`: `{a['memory_entry_id']}` ↔ `{a['wiki_page']}`")
        if len(asymmetric) > 20:
            lines.append(f"- ... and {len(asymmetric) - 20} more")
    return "\n".join(lines) + "\n"


def _emit_bidir_link_audit_log(args: argparse.Namespace, bl_log: str) -> dict:
    """bidir-link audit log 를 release note 끝에 append (idempotent marker)."""
    try:
        version = getattr(args, "version", None) or read_version()
        notes_resolution = _resolve_notes_file(version, "default", dry_run=False)
        notes_file = notes_resolution.get("notes_file")
        if not notes_file or not Path(notes_file).exists():
            return {"status": "skipped", "reason": "release note not found (backfill scenario)"}
        body = Path(notes_file).read_text(encoding="utf-8")
        marker = "## Bidirectional link audit"
        if marker in body:
            return {"status": "skipped", "reason": "bidir link audit log already present (idempotent)"}
        new_body = body.rstrip("\n") + "\n" + bl_log
        if atomic_write_text is not None:
            atomic_write_text(notes_file, new_body)
        else:
            notes_file.write_text(new_body, encoding="utf-8")
        return {
            "status": "ok",
            "path": str(notes_file),
            "bytes_appended": len(bl_log),
        }
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# 5. verify (Phase 2 — v0.7.10)
# ---------------------------------------------------------------------------


def cmd_verify(args) -> dict:
    """GitHub Release 의 tag + asset 검증 (read-only)."""
    tag = args.tag
    if tag.startswith("v"):
        tag_full = tag
    else:
        tag_full = f"v{tag}"
    # 1. gh release view (--json tagName,name,url,assets,isPrerelease,publishedAt)
    gh_cmd = [
        "gh", "release", "view", tag_full,
        "--repo", _get_repo(),
        "--json", "tagName,name,url,assets,isPrerelease,publishedAt",
    ]
    results: dict = {"tag": tag_full, "gh_command": " ".join(gh_cmd), "mode": "read-only"}

    if args.dry_run:
        return results

    proc = subprocess.run(gh_cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        return {**results, "error": f"release not found: {tag_full} (gh exit {proc.returncode})"}

    try:
        release_data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return {**results, "error": f"gh release view JSON parse failed: {e}"}

    results["name"] = release_data.get("name")
    results["url"] = release_data.get("url")
    results["is_prerelease"] = release_data.get("isPrerelease")
    results["created_at"] = release_data.get("publishedAt")
    results["assets"] = [a.get("name") for a in release_data.get("assets", [])]
    return results


def _get_repo() -> str:
    """git remote origin → 'owner/repo' 추출."""
    proc = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10,
    )
    return proc.stdout.strip().replace("https://github.com/", "").replace(".git", "")


# ---------------------------------------------------------------------------
# 6. rollback (Phase 2 — v0.7.10)
# ---------------------------------------------------------------------------


def cmd_rollback(args) -> dict:
    """GitHub Release + git tag 삭제 (destructive).

    --dry-run: 삭제 명령만 print, 실제 호출 0.
    --apply: gh release delete + git tag -d + git push --delete origin <tag>.
    """
    tag = args.tag if args.tag.startswith("v") else f"v{args.tag}"
    repo = _get_repo()

    commands = [
        # local tag delete
        ["git", "tag", "-d", tag],
        # remote tag delete
        ["git", "push", "--delete", "origin", tag],
        # gh release delete
        ["gh", "release", "delete", tag, "--repo", repo, "--yes"],
    ]
    results: dict = {
        "tag": tag,
        "repo": repo,
        "commands": [" ".join(c) for c in commands],
        "mode": "dry-run" if args.dry_run else "apply",
    }

    if args.dry_run:
        return results

    # 실제 실행
    executed: list[dict] = []
    for cmd in commands:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        executed.append({
            "cmd": " ".join(cmd),
            "exit_code": proc.returncode,
            "stdout_tail": (proc.stdout or "").strip().split("\n")[-1] if proc.stdout else "",
        })
        if proc.returncode != 0:
            results["error"] = f"command failed: {' '.join(cmd)} (exit {proc.returncode})"
            break
    results["executed"] = executed
    results["ok"] = "error" not in results
    return results


# ---------------------------------------------------------------------------
# 7. dist (Phase 3 — v0.7.11)
# ---------------------------------------------------------------------------


def _check_build_module() -> dict:
    """`build` module 가용성 체크. 없으면 pip install 안내.

    Returns:
        {"available": bool, "hint": str (if not available)}
    """
    try:
        import build  # type: ignore[import-not-found]  # noqa: F401

        return {"available": True, "version": getattr(build, "__version__", "unknown")}
    except ImportError:
        return {
            "available": False,
            "hint": "pip install build (or `python3 -m pip install --user build`)",
        }


def _build_command(out_dir: Path, *, sdist_only: bool = False, wheel_only: bool = False) -> list[str]:
    """`python3 -m build` 호출 command list. PEP 517/518 build."""
    cmd = [sys.executable, "-m", "build", "--outdir", str(out_dir)]
    if sdist_only:
        cmd.append("--sdist")
    elif wheel_only:
        cmd.append("--wheel")
    cmd.append(str(REPO_ROOT))
    return cmd


def _expected_dist_pattern(version: str) -> str:
    """version (e.g. '0.7.10' or '0.7.10-beta') → dist file prefix (PEP 440 normalize)."""
    return version.split("-")[0]


def cmd_dist(args) -> dict:
    """Wheel + sdist 자동 빌드 (`python3 -m build`).

    pre-check: `build` module 가용성 → 부재 시 graceful fail.
    dry-run: command + PEP 440 normalize 만 print. exit 0.
    apply: subprocess `python3 -m build` 실행. exit code + dist glob 결과 report.

    v0.8.15 (spec §7 + §9 #7): 1-command build + check + TestPyPI simulation.
    `release-dist --apply` = build + twine check + TestPyPI upload simulation.
    `release-dist --apply --production` = + production upload simulation.
    Both `--apply` and `--apply --production` *simulate* upload (no actual PyPI/TestPyPI
    deployment per release channel policy: GitHub Releases only).
    """
    _dist_dir = REPO_ROOT / "dist"
    results: dict = {"mode": "dry-run" if args.dry_run else "apply", "out_dir": str(_dist_dir)}

    # 1) pre-check: build module 가용성
    build_check = _check_build_module()
    results["build_module"] = build_check
    if not build_check["available"]:
        results["error"] = f"build module not installed: {build_check['hint']}"
        return results

    # 2) version read (pyproject.toml)
    try:
        current_version = read_version()
    except Exception as e:  # pragma: no cover
        results["error"] = f"pyproject.toml version read 실패: {e}"
        return results
    results["version"] = current_version
    cmd = _build_command(
        _dist_dir,
        sdist_only=getattr(args, "sdist_only", False),
        wheel_only=getattr(args, "wheel_only", False),
    )
    results["command"] = " ".join(cmd)
    results["expected_pattern"] = f"standard_ai_workflow-{_expected_dist_pattern(current_version)}*"

    # 4) skip-existing check (--skip-existing) — skip build but still run
    #    twine check + upload simulation on existing artifacts (v0.8.15).
    if getattr(args, "skip_existing", False) and _dist_dir.exists():
        existing = find_dist_files(current_version)
        if existing:
            results["mode"] = "skip"
            results["skipped"] = True
            results["existing"] = [f.name for f in existing]
            # Still run post-build steps on existing artifacts.
            twine_check = _twine_check(_dist_dir, timeout=getattr(args, "timeout", 300))
            results["twine_check"] = twine_check
            if not twine_check["ok"]:
                results["error"] = (
                    f"twine check failed: {twine_check.get('error', 'unknown')}"
                )
                results["ok"] = False
                return results
            results["testpypi_simulation"] = _simulate_testpypi_upload(
                existing, current_version,
            )
            if getattr(args, "production", False):
                results["production_simulation"] = _simulate_production_upload(
                    existing, current_version,
                )
            results["ok"] = True
            return results

    # 5) dry-run: command plan 만 반환
    if args.dry_run:
        results["ok"] = True
        return results

    # 6) apply: subprocess `python3 -m build` 실행
    _dist_dir.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=args.timeout,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        results["error"] = f"build timeout after {args.timeout}s"
        return results

    results["returncode"] = proc.returncode
    # 마지막 5 line 의 stdout/stderr 만 report (full log 은 debug 용)
    out_tail = proc.stdout.strip().splitlines()[-5:] if proc.stdout.strip() else []
    err_tail = proc.stderr.strip().splitlines()[-5:] if proc.stderr.strip() else []
    results["stdout_tail"] = out_tail
    results["stderr_tail"] = err_tail

    if proc.returncode != 0:
        results["error"] = f"build failed: exit {proc.returncode}"
        results["ok"] = False
        return results

    # 7) post-check: dist glob 결과
    built = find_dist_files(current_version)
    results["built"] = [f.name for f in built]
    if not built:
        results["error"] = "no built artifacts found in dist/"
        results["ok"] = False
        return results

    # 8) twine check (metadata validation) — spec §7.1 step 2, §9 #7
    twine_check = _twine_check(_dist_dir, timeout=getattr(args, "timeout", 300))
    results["twine_check"] = twine_check
    if not twine_check["ok"]:
        results["error"] = f"twine check failed: {twine_check.get('error', 'unknown')}"
        results["ok"] = False
        return results

    # 9) TestPyPI upload simulation — spec §7.1 step 3, §9 #7.
    # Policy: no actual PyPI/TestPyPI deployment (release channel: GitHub Releases only).
    # We *simulate* the upload by reporting what *would* be uploaded.
    testpypi_sim = _simulate_testpypi_upload(built, current_version)
    results["testpypi_simulation"] = testpypi_sim

    # 10) Production upload simulation (only if --production flag set) — spec §7.1 step 5.
    if getattr(args, "production", False):
        production_sim = _simulate_production_upload(built, current_version)
        results["production_simulation"] = production_sim

    results["ok"] = True
    return results


def _twine_check(dist_dir: Path, *, timeout: int = 300) -> dict[str, object]:
    """Run `twine check dist/*` for metadata validation (spec §7.1 step 2).

    Args:
        dist_dir: dist/ directory containing wheel + sdist
        timeout: subprocess timeout in seconds (default 300)

    Returns:
        dict with `ok` (bool), `returncode`, `stdout_tail`, `stderr_tail`, optional `error`.
    """
    import sys
    artifacts = sorted(str(p) for p in dist_dir.glob("*") if p.suffix in (".whl", ".tar.gz"))
    if not artifacts:
        return {"ok": False, "error": "no wheel/sdist artifacts in dist/"}
    try:
        # `python -m twine` 는 PATH 와 무관하게 현재 Python 의 twine module 사용
        # (venv / system Python / pip install 모두 동작)
        proc = subprocess.run(
            [sys.executable, "-m", "twine", "check"] + artifacts,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"twine check timeout after {timeout}s"}
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout.strip().splitlines()[-5:] if proc.stdout.strip() else [],
        "stderr_tail": proc.stderr.strip().splitlines()[-5:] if proc.stderr.strip() else [],
    }


def _simulate_testpypi_upload(
    artifacts: list[Path], version: str,
) -> dict[str, object]:
    """Simulate `twine upload --repository testpypi` (spec §7.1 step 3).

    Policy: no actual TestPyPI deployment (release channel: GitHub Releases only).
    Reports what *would* be uploaded + command for manual execution.

    Returns:
        dict with `command`, `artifacts`, `note` (no-actual-upload policy).
    """
    artifact_names = [p.name for p in artifacts]
    cmd = ["twine", "upload", "--repository", "testpypi", "--skip-existing"] + artifact_names
    return {
        "command": " ".join(cmd),
        "artifacts": artifact_names,
        "version": version,
        "would_upload_to": "https://test.pypi.org/project/standard-ai-workflow/",
        "actual_upload": False,
        "note": (
            "Per release channel policy (memory #5: GitHub Releases only), "
            "no actual TestPyPI upload performed. Use the command above manually "
            "if TestPyPI validation is needed."
        ),
    }


def _simulate_production_upload(
    artifacts: list[Path], version: str,
) -> dict[str, object]:
    """Simulate `twine upload` to production PyPI (spec §7.1 step 5).

    Policy: no actual PyPI deployment (release channel: GitHub Releases only).
    Reports what *would* be uploaded + command for manual execution.

    Returns:
        dict with `command`, `artifacts`, `note` (no-actual-upload policy).
    """
    artifact_names = [p.name for p in artifacts]
    cmd = ["twine", "upload"] + artifact_names
    return {
        "command": " ".join(cmd),
        "artifacts": artifact_names,
        "version": version,
        "would_upload_to": "https://pypi.org/project/standard-ai-workflow/",
        "actual_upload": False,
        "note": (
            "Per release channel policy (memory #5: GitHub Releases only), "
            "no actual PyPI upload performed. Use the command above manually "
            "if PyPI production upload is needed."
        ),
    }


# ---------------------------------------------------------------------------
# 8. gen-schema (v0.8.0+ — runtime contract → JSON Schema SSOT)
# ---------------------------------------------------------------------------
# v0.7.59+ spec §6.1 정공법: Pydantic v2 model registry 의 모든 output/error schema 를
# JSON Schema (draft-07) 으로 dump. runtime contract (workflow_kit.common.output_contracts) 와
# byte-identical 임을 CI 의 `gen-schema --check` 가 검증. read-only MCP manifest 의
# outputSchema 가 generated schema 와 byte-identical 임을 assertion test 가 강제.
GEN_SCHEMA_DEFAULT_OUTPUT = REPO_ROOT / "schemas" / "generated_output_schemas.json"


def cmd_gen_schema(args) -> dict:
    """JSON Schema bundle 을 output path 에 write (또는 --check 으로 byte-identical 검증).

    Args:
        --output=PATH: 출력 file path (default: schemas/generated_output_schemas.json).
        --check: byte-identical 검증 (write 안 함, CI gate).
        --dry-run: write 안 함, write plan 만 출력.
        --json: JSON output.
        --family=NAME: 단일 family 만 dump (default: all families).
    """
    results: dict = {}
    output_path = Path(args.output) if args.output else GEN_SCHEMA_DEFAULT_OUTPUT
    results["output_path"] = str(output_path)
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from workflow_kit.common.output_contracts import output_json_schema_bundle, PYDANTIC_MODEL_REGISTRY
    except ImportError as e:
        results["error"] = f"output_contracts import failed: {type(e).__name__}: {e}"
        results["ok"] = False
        return results
    # 2. dump
    try:
        bundle = output_json_schema_bundle()
    except Exception as e:  # noqa: BLE001
        results["error"] = f"output_json_schema_bundle failed: {type(e).__name__}: {e}"
        results["ok"] = False
        return results
    # 3. family filter
    if args.family:
        if args.family not in bundle:
            results["error"] = f"family not in bundle: {args.family}. available: {sorted(bundle.keys())[:5]}..."
            results["ok"] = False
            return results
        bundle = {args.family: bundle[args.family]}
    results["family_count"] = len(bundle)
    results["registry_count"] = len(PYDANTIC_MODEL_REGISTRY)
    # 4. JSON encode (sort_keys=True 로 byte-identical 보장)
    try:
        encoded = json.dumps(bundle, sort_keys=True, indent=2, default=str)
    except (TypeError, ValueError) as e:
        results["error"] = f"JSON encode failed: {type(e).__name__}: {e}"
        results["ok"] = False
        return results
    results["encoded_bytes"] = len(encoded.encode("utf-8"))
    # 5. --check: byte-identical 검증 (no write)
    if args.check:
        if not output_path.exists():
            results["error"] = f"--check: output file does not exist: {output_path}"
            results["ok"] = False
            return results
        existing = output_path.read_text(encoding="utf-8")
        if existing != encoded:
            results["error"] = (
                f"--check: drift detected. existing={len(existing)} bytes, "
                f"expected={len(encoded)} bytes"
            )
            results["ok"] = False
            return results
        results["check_status"] = "identical"
        results["ok"] = True
        return results
    # 6. --dry-run: write 안 함
    if args.dry_run:
        results["dry_run_status"] = "plan-only"
        results["ok"] = True
        return results
    # 7. write (atomic)
    if atomic_write_text is not None:
        try:
            atomic_write_text(output_path, encoded)
        except Exception as e:  # noqa: BLE001
            results["error"] = f"atomic_write failed: {type(e).__name__}: {e}"
            results["ok"] = False
            return results
    else:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(encoded, encoding="utf-8")
        except OSError as e:
            results["error"] = f"write failed: {type(e).__name__}: {e}"
            results["ok"] = False
            return results
    results["written"] = str(output_path)
    results["ok"] = True
    return results


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(
        description="standard-ai-workflow release pipeline (v0.7.9+)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # validate
    p_val = sub.add_parser("validate", help="release-readiness 검증 (4 source + mypy)")
    p_val.add_argument("--skip-packaging", action="store_true", help="check_packaging skip")
    p_val.add_argument("--skip-doctor", action="store_true", help="doctor skip")
    p_val.add_argument("--skip-state", action="store_true", help="state.json check skip")
    p_val.add_argument("--skip-git", action="store_true", help="git status check skip")
    p_val.add_argument("--skip-mypy", action="store_true", help="mypy strict check skip (v0.11.12+)")
    p_val.add_argument("--dry-run", action="store_true")
    p_val.add_argument("--json", action="store_true")

    # version-bump (v0.7.14+ auto-sync workflow_kit/__init__.py)
    p_vb = sub.add_parser("version-bump", help="pyproject.toml version patch + workflow_kit/__init__.py __version__ auto-sync")
    p_vb.add_argument("--patch", action="store_true", help="patch bump (default)")
    p_vb.add_argument("--minor", action="store_true", help="minor bump")
    p_vb.add_argument("--major", action="store_true", help="major bump")
    p_vb.add_argument("--to", help="explicit version (e.g. 0.7.9)")
    p_vb.add_argument("--no-init", action="store_true", dest="no_init",
                       help="workflow_kit/__init__.py __version__ sync skip (CI / override 시나리오)")
    p_vb.add_argument("--dry-run", action="store_true", dest="dry_run",
                       help="bump plan 만 출력 (default: --apply)")
    p_vb.add_argument("--apply", dest="apply", action="store_true", default=True)
    p_vb.add_argument("--skip-sync-hash", action="store_true", dest="skip_sync_hash",
                       help="post-step sync_release_hash 자동 호출 skip (TASK-V0726-003, manual override)")
    p_vb.add_argument("--json", action="store_true", help="JSON output (CI integration)")

    # note-draft
    p_nd = sub.add_parser("note-draft", help="release note skeleton 자동 생성")
    p_nd.add_argument("--from", dest="from_tag", required=True, help="이전 release tag (e.g. v0.7.8)")
    p_nd.add_argument("--to", required=True, help="새 release version (e.g. 0.7.9)")
    p_nd.add_argument("--dry-run", action="store_true", dest="dry_run")
    p_nd.add_argument("--apply", dest="apply", action="store_true", default=True)

    # doc-headers-update (v0.11.23+ — drift prevention P1)
    p_dhu = sub.add_parser(
        "doc-headers-update",
        help="docs/* + workflow-source/core/* + README.md 의 '- 최종 수정일' 헤더를 일괄 갱신 (drift prevention)",
    )
    p_dhu.add_argument("--scope", default="all", choices=["all", "docs", "core", "readme"],
                       help="대상 scope (default: all)")
    p_dhu.add_argument("--date", default=None,
                       help="YYYY-MM-DD override (default: UTC today)")
    p_dhu.add_argument("--dry-run", action="store_true", dest="dry_run",
                       help="plan 만 출력 (write 안 함)")
    p_dhu.add_argument("--apply", dest="apply", action="store_true", default=True,
                       help="default: apply. --dry-run 으로 override")
    p_dhu.add_argument("--json", action="store_true")

    # sync-maturity-matrix (v0.11.23+ — drift prevention P2)
    p_smm = sub.add_parser(
        "sync-maturity-matrix",
        help=(
            "Release note (Beta-v<X>.md) 의 YAML frontmatter (closed_phases / promoted_skills / "
            "added_harnesses / deprecated_symbols) 를 읽어 workflow-source/core/maturity_matrix.json 자동 patch. "
            "drift prevention P2 핵심."
        ),
    )
    p_smm.add_argument("--from-release-note", required=True, dest="from_release_note",
                       help="Release note 경로 (e.g. workflow-source/releases/Beta-v0.11.23.md)")
    p_smm.add_argument("--dry-run", action="store_true", dest="dry_run",
                       help="plan 만 출력 (write 안 함)")
    p_smm.add_argument("--apply", dest="apply", action="store_true", default=True,
                       help="default: apply. --dry-run 으로 override")
    p_smm.add_argument("--json", action="store_true")

    # bidir-link (Phase 13 AC4+ — v0.13.3+, wiki ↔ memory 양방향 link sync + audit)
    p_bl = sub.add_parser(
        "bidir-link",
        help=(
            "Phase 13 AC4+ wiki ↔ memory 양방향 link 자동화. "
            "default: audit (read-only, R-C). --apply 로 sync (R-A). "
            "memory entry.mentioned_in → wiki related_pages 자동 갱신."
        ),
    )
    p_bl.add_argument("--workspace-root", dest="workspace_root", default=None,
                      help="workspace root (default: release --apply 의 cwd)")
    p_bl.add_argument("--apply", dest="apply", action="store_true", default=False,
                      help="sync 적용 (R-A, default: audit only)")
    p_bl.add_argument("--json", action="store_true")

    # self-recover (Phase 13 AC3 — v0.13.2+, drift prevention P3)
    p_sr = sub.add_parser(
        "self-recover",
        help=(
            "drift prevention smoke 의 FAIL case 자동 fix (Phase 13 AC3). "
            "detect → classify (auto_fixable / manual_required) → fix → re-check → emit. "
            "default: dry-run. --apply 로 실제 fix."
        ),
    )
    p_sr.add_argument("--apply", dest="apply", action="store_true", default=False,
                      help="fix 적용 (default: dry-run)")
    p_sr.add_argument("--dry-run", action="store_true", dest="dry_run",
                      help="plan 만 출력 (write 안 함, default)")
    p_sr.add_argument("--json", action="store_true")

    # changelog-gen (Phase 4 — v0.7.14+, Keep-a-Changelog 형식, v0.7.15+ filter)
    p_cl = sub.add_parser("changelog-gen", help="multi-release git log → CHANGELOG.md 본문 (Keep-a-Changelog 형식)")
    p_cl.add_argument("--output", default=None,
                      help="output file path (default: workflow-source/CHANGELOG.md)")
    p_cl.add_argument("--unreleased-label", default="Unreleased",
                      help="unreleased commit group 의 label (default: 'Unreleased')")
    p_cl.add_argument("--from-tag", default=None,
                      help="git log 시작 ref (e.g. v0.7.0-beta). 미지정 시 --all (전체 history)")
    p_cl.add_argument("--to-tag", default="HEAD",
                      help="git log 종료 ref (default: HEAD)")
    p_cl.add_argument("--dry-run", action="store_true", dest="dry_run")
    p_cl.add_argument("--apply", dest="apply", action="store_true", default=True)
    p_cl.add_argument("--json", action="store_true")

    # release (Phase 2 — v0.7.10, v0.7.13+ --version)
    p_rel = sub.add_parser("release", help="GitHub Release 생성 (gh release create)")
    p_rel.add_argument("--skip-validate", action="store_true", help="validate 사전 점검 skip")
    p_rel.add_argument("--skip-cross-verify", action="store_true",
                       help="mypy CI cross-verify skip (v0.11.13+, advisory 만 default)")
    p_rel.add_argument("--strict-cross-verify", action="store_true",
                       help="mypy CI cross-verify 시 drift / ci_stale / ci_fail hard fail (v0.11.13+)")
    p_rel.add_argument("--skip-self-recover", dest="skip_self_recover",
                       action="store_true", default=False,
                       help="drift prevention: Phase 13 AC3 self-recover step skip (v0.13.2+, manual override 용)")
    p_rel.add_argument("--skip-bidir-link", dest="skip_bidir_link",
                       action="store_true", default=False,
                       help="Phase 13 AC4+: wiki ↔ memory bidir-link audit step skip (v0.13.3+, manual override 용)")
    p_rel.add_argument("--skip-doc-headers-update", dest="skip_doc_headers_update",
                       action="store_true", default=False,
                       help="drift prevention: docs/ - 최종 수정일 헤더 자동 갱신 step skip (v0.11.23+)")
    p_rel.add_argument("--skip-maturity-matrix-sync", dest="skip_maturity_matrix_sync",
                       action="store_true", default=False,
                       help="drift prevention: release note frontmatter → maturity_matrix.json 자동 patch step skip (v0.11.23+)")
    p_rel.add_argument("--version", default=None,
                       help="version override (e.g. 0.7.5 for backfill). default: pyproject.toml [project] version")
    p_rel.add_argument("--auto-bump", dest="auto_bump", action="store_true", default=False,
                       help="remote tag pre-check fail 시 다음 version 으로 자동 bump + re-flow. "
                            "v0.7.18+: release coordination observability.")
    p_rel.add_argument("--allow-existing-tag", dest="allow_existing_tag", action="store_true", default=False,
                       help="remote tag pre-check 가 'already exists' 일 때 *skip* + 그대로 release 진행. "
                            "v0.7.21+ follow-up: tag push 와 release 의 coupling fix.")
    p_rel.add_argument("--full-auto", dest="full_auto", action="store_true", default=False,
                       help="release pipeline 1-step cycle close (v0.9.1+ automation): "
                            "pre-check conflict 시 자동으로 --auto-bump 동작 (다음 version 결정 + "
                            "version-bump + re-flow) 후 새로 결정된 tag 로 release 진행. "
                            "여전히 conflict 면 --allow-existing-tag 로 fallback. "
                            "최종적으로 *operator intervention 없이* tag push + gh release create "
                            "완료. release 채널 정책 (memory #5: --dry-run 필수) 유지 — "
                            "본 flag 는 --dry-run 과 동시 사용 가능 (plan 검증용).")
    p_rel.add_argument("--dry-run", action="store_true", dest="dry_run",
                       help="destructive subcommand 정공법 (memory #5): tag push + gh release create 의 "
                            "plan 만 출력, 실제 호출 0. --apply 가 default True 이므로 --dry-run 으로 "
                            "override. v0.9.0 chapter 4 에서 --dry-run flag 추가 (이전엔 argparse 누락 "
                            "으로 cmd_release 호출 시 즉시 AttributeError).")
    p_rel.add_argument("--apply", dest="apply", action="store_true", default=True)
    p_rel.add_argument("--json", action="store_true")
    p_rel.add_argument(
        "--legacy-memory", dest="legacy_memory", default=None,
        action=argparse.BooleanOptionalAction,
        help="v0.15.0+ ⚠️ BREAKING 정렬. --no-legacy-memory (strict opt-out) 면 "
             "step 6.7 maturity refresh skip (silent fallback 비활성 caller 정합). "
             "default: None (정공법 진행).",
    )

    # refresh-maturity (v0.14.6+ Task 3 follow-up)
    p_rm = sub.add_parser(
        "refresh-maturity",
        help="maturity_matrix.json 의 `last_updated` field 자동 갱신 (Task 3 follow-up, v0.14.6+). "
             "idempotent. --dry-run 으로 plan 만 emit 가능. "
             "default: workflow-source/core/maturity_matrix.json.",
    )
    p_rm.add_argument("--today", dest="today", default=None,
                      help="명시적 today override (default: date.today().isoformat())")
    p_rm.add_argument("--maturity-path", dest="maturity_path", default=None,
                      help="maturity_matrix.json 의 path (default: workflow-source/core/maturity_matrix.json)")
    p_rm.add_argument("--dry-run", action="store_true", dest="dry_run",
                      help="dry-run mode — 실제 last_updated 갱신 안 함, plan 만 emit")
    p_rm.add_argument("--apply", dest="apply", action="store_true", default=True)
    p_rm.add_argument("--json", action="store_true")
    p_rm.add_argument(
        "--legacy-memory", dest="legacy_memory", default=None,
        action=argparse.BooleanOptionalAction,
        help="v0.15.0+ ⚠️ BREAKING 정렬. --no-legacy-memory (strict opt-out) 면 "
             "maturity refresh skip + warning emit (silent fallback 비활성 caller 정합). "
             "default: None (skip 없이 정공법 진행).",
    )
    p_rel.add_argument("--skip-dashboard-emit", dest="skip_dashboard_emit",
                       action="store_true", default=False,
                       help="dashboard markdown post-release 자동 emit skip (v0.13.1+ Phase 13). "
                            "default: emit. 실패 시 release 자체는 성공.")
    p_rel.add_argument("--dashboard-output", dest="dashboard_output", default=None,
                       help="dashboard snapshot 출력 경로 (default: ai-workflow/dashboard/snapshot.md). "
                            "v0.13.1+ Phase 13.")

    # gen-schema (v0.8.0+ — runtime contract → JSON Schema SSOT)
    p_gs = sub.add_parser("gen-schema", help="JSON Schema bundle dump (Pydantic v2 → JSON Schema draft-07). v0.8.0+ SSOT")
    p_gs.add_argument("--output", help="출력 file path (default: schemas/generated_output_schemas.json)")
    p_gs.add_argument("--check", action="store_true", help="byte-identical 검증 (write 안 함, CI gate)")
    p_gs.add_argument("--dry-run", action="store_true", dest="dry_run", help="write 안 함, plan 만 출력")
    p_gs.add_argument("--family", help="단일 family 만 dump (default: all families)")
    p_gs.add_argument("--json", action="store_true", help="JSON output")

    # verify (Phase 2 — v0.7.10)
    p_ver = sub.add_parser("verify", help="GitHub Release 의 tag + asset 검증 (read-only)")
    p_ver.add_argument("--tag", required=True, help="tag 이름 (e.g. v0.7.9-beta 또는 0.7.9)")
    p_ver.add_argument("--dry-run", action="store_true", dest="dry_run")
    p_ver.add_argument("--json", action="store_true")

    # rollback (Phase 2 — v0.7.10)
    p_rb = sub.add_parser("rollback", help="GitHub Release + git tag 삭제 (destructive)")
    p_rb.add_argument("--tag", required=True, help="tag 이름 (e.g. v0.7.9-beta 또는 0.7.9)")
    p_rb.add_argument("--dry-run", action="store_true", dest="dry_run")
    p_rb.add_argument("--apply", dest="apply", action="store_true", default=True)
    p_rb.add_argument("--json", action="store_true")

    # dist (Phase 3 — v0.7.11)
    p_dist = sub.add_parser("dist", help="wheel + sdist 자동 빌드 (`python3 -m build`)")
    p_dist.add_argument("--sdist-only", action="store_true", help="sdist 만 빌드")
    p_dist.add_argument("--wheel-only", action="store_true", help="wheel 만 빌드")
    p_dist.add_argument("--skip-existing", action="store_true", help="dist/ 의 current-version 파일 있으면 skip")
    p_dist.add_argument("--timeout", type=int, default=300, help="subprocess timeout in sec (default 300)")
    p_dist.add_argument("--dry-run", action="store_true", dest="dry_run")
    p_dist.add_argument("--apply", dest="apply", action="store_true", default=True)
    p_dist.add_argument("--production", action="store_true", help="simulate production PyPI upload (after TestPyPI sim). actual upload not performed per release policy.")
    p_dist.add_argument("--json", action="store_true")

    args = p.parse_args()
    if getattr(args, "dry_run", False):
        args.apply = False
    if not getattr(args, "dry_run", False) and not getattr(args, "apply", False):
        # default = dry-run when neither flag is specified
        args.dry_run = True

    if args.command == "validate":
        result = cmd_validate(args)
    elif args.command == "version-bump":
        result = cmd_version_bump(args)
    elif args.command == "note-draft":
        result = cmd_note_draft(args)
    elif args.command == "changelog-gen":
        result = cmd_changelog_gen(args)
    elif args.command == "doc-headers-update":
        result = cmd_doc_headers_update(args)
    elif args.command == "sync-maturity-matrix":
        result = cmd_maturity_matrix_sync(args)
    elif args.command == "self-recover":
        result = cmd_self_recover(args)
    elif args.command == "bidir-link":
        result = cmd_bidir_link(args)
    elif args.command == "release":
        result = cmd_release(args)
    elif args.command == "refresh-maturity":
        result = cmd_refresh_maturity(args)
    elif args.command == "verify":
        result = cmd_verify(args)
    elif args.command == "rollback":
        result = cmd_rollback(args)
    elif args.command == "dist":
        result = cmd_dist(args)
    elif args.command == "gen-schema":
        result = cmd_gen_schema(args)
    else:
        p.error(f"unknown command: {args.command}")
        return 2

    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        dry_run = getattr(args, "dry_run", False)
        mode_label = "DRY-RUN" if dry_run else "APPLY"
        if args.command == "verify":
            mode_label = "READ-ONLY"
        print(f"=== {args.command} ({mode_label}) ===")
        for k, v in result.items():
            if isinstance(v, dict):
                print(f"  {k}:")
                for k2, v2 in v.items():
                    if isinstance(v2, list) and len(str(v2)) > 80:
                        print(f"    {k2}: [{', '.join(str(x) for x in v2[:3])}...]")
                    else:
                        print(f"    {k2}: {v2}")
            elif isinstance(v, list):
                if len(str(v)) > 80:
                    print(f"  {k}: [{', '.join(str(x) for x in v[:3])}...]")
                else:
                    print(f"  {k}: {v}")
            else:
                print(f"  {k}: {v}")

    # exit code: validate / release / verify / rollback / dist 의 ok/error 기반
    if args.command in ("validate", "release", "verify", "rollback", "dist"):
        if "error" in result:
            return 1
        if args.command in ("release", "rollback", "dist") and not result.get("ok", True):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
