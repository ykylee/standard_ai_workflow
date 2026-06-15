#!/usr/bin/env python3
"""v0.7.9+: standard-ai-workflow release pipeline 정식화 (7 subcommand).

release 절차 (validate → dist → version-bump → note-draft → release → verify → rollback) 의
*기계화 layer*. manual 절차 (memory #5 / docs/RELEASE.md) 의 *부족 부분* 자동화.

Phase 1 (v0.7.9): validate / version-bump / note-draft — 사전 점검 + version + note.
Phase 2 (v0.7.10): release / verify / rollback — gh CLI 통합 + read-only verify + destructive rollback.
Phase 3 (v0.7.11): dist — `python3 -m build` wheel + sdist 자동 빌드 (PEP 517/518).

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
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 1차 출처
REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
RELEASES_DIR = REPO_ROOT / "releases"

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
    """
    results: dict = {}

    # 1. check_packaging
    if not args.skip_packaging:
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools/check_packaging.py")],
            capture_output=True, text=True, timeout=120,
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

    return results


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


def parse_version(version: str) -> tuple[int, int, int]:
    """'0.7.8' → (0, 7, 8). pre-release 식별자 (e.g. '-beta') 는 무시."""
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    if not m:
        raise ValueError(f"invalid version: {version}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


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


def cmd_version_bump(args) -> dict:
    """pyproject.toml version patch."""
    current = read_version()
    if args.dry_run:
        new = bump_version(
            current,
            patch=args.patch, minor=args.minor, major=args.major, to=args.to,
        )
        return {
            "mode": "dry-run",
            "current": current,
            "next": new,
        }
    if args.to is None and not (args.patch or args.minor or args.major):
        args.patch = True
    new = bump_version(
        current,
        patch=args.patch, minor=args.minor, major=args.major, to=args.to,
    )
    write_version(new)
    return {
        "mode": "applied",
        "previous": current,
        "current": new,
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
# 4. release (Phase 2 — v0.7.10)
# ---------------------------------------------------------------------------


def find_dist_files(version: str) -> list[Path]:
    """dist/ 의 wheel + sdist glob. PEP 440 normalize: 0.7.10 → 0.7.10b0."""
    dist = REPO_ROOT / "dist"
    if not dist.exists():
        return []
    # PEP 440: 0.7.10-beta → 0.7.10b0
    base = version.split("-")[0]
    pep_version = base  # wheel 파일명은 X.Y.Z 형태
    return sorted(dist.glob(f"standard_ai_workflow-{pep_version}*"))


def cmd_release(args) -> dict:
    """GitHub Release 생성 (gh release create).

    사전 점검: --skip-validate 미지정 시 validate 4 source 자동 호출.
    1+ source fail 시 release 중단 (exit 1).

    gh auth 인증된 환경 가정. token 회전 부담은 caller 책임.
    """
    results: dict = {"pre_check": {}, "gh_commands": [], "mode": "dry-run" if args.dry_run else "apply"}

    # 1. validate (사전 점검)
    if not args.skip_validate:
        val_result = cmd_validate(args)
        results["pre_check"] = val_result
        if not all(v.get("ok", False) for v in val_result.values()):
            return {**results, "error": "validate failed; abort release"}

    # 2. dist 파일 glob
    version = read_version()
    dist_files = find_dist_files(version)
    if not dist_files:
        return {**results, "error": f"no dist files found for version {version} (run `python3 -m build` first)"}

    # 3. tag + gh command
    tag = f"v{version}-beta"
    notes_file = RELEASES_DIR / f"Beta-v{version}.md"
    if not notes_file.exists():
        return {**results, "error": f"release note not found: {notes_file}"}

    rel_assets = [str(f.relative_to(REPO_ROOT)) for f in dist_files]
    results["tag"] = tag
    results["assets"] = rel_assets
    results["notes_file"] = str(notes_file.relative_to(REPO_ROOT))

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
        return {**results, "error": "gh auth not authenticated"}
    results["gh_auth_ok"] = True

    proc = subprocess.run(gh_cmd, capture_output=True, text=True, timeout=120)
    results["gh_exit_code"] = proc.returncode
    if proc.stdout:
        results["gh_stdout_tail"] = proc.stdout.strip().split("\n")[-1]
    if proc.stderr:
        results["gh_stderr_tail"] = proc.stderr.strip().split("\n")[-1]
    if proc.returncode != 0:
        return {**results, "error": f"gh release create failed: exit {proc.returncode}"}
    return results


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

    # 3) build command
    cmd = _build_command(
        _dist_dir,
        sdist_only=getattr(args, "sdist_only", False),
        wheel_only=getattr(args, "wheel_only", False),
    )
    results["command"] = " ".join(cmd)
    results["expected_pattern"] = f"standard_ai_workflow-{_expected_dist_pattern(current_version)}*"

    # 4) skip-existing check (--skip-existing)
    if getattr(args, "skip_existing", False) and _dist_dir.exists():
        existing = find_dist_files(current_version)
        if existing:
            results["mode"] = "skip"
            results["skipped"] = True
            results["existing"] = [f.name for f in existing]
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
    p_val = sub.add_parser("validate", help="release-readiness 검증 (4 source)")
    p_val.add_argument("--skip-packaging", action="store_true", help="check_packaging skip")
    p_val.add_argument("--skip-doctor", action="store_true", help="doctor skip")
    p_val.add_argument("--skip-state", action="store_true", help="state.json check skip")
    p_val.add_argument("--skip-git", action="store_true", help="git status check skip")
    p_val.add_argument("--dry-run", action="store_true")
    p_val.add_argument("--json", action="store_true")

    # version-bump
    p_vb = sub.add_parser("version-bump", help="pyproject.toml version patch")
    p_vb.add_argument("--patch", action="store_true", help="patch bump (default)")
    p_vb.add_argument("--minor", action="store_true", help="minor bump")
    p_vb.add_argument("--major", action="store_true", help="major bump")
    p_vb.add_argument("--to", help="explicit version (e.g. 0.7.9)")
    p_vb.add_argument("--dry-run", action="store_true", dest="dry_run")
    p_vb.add_argument("--apply", dest="apply", action="store_true", default=True)

    # note-draft
    p_nd = sub.add_parser("note-draft", help="release note skeleton 자동 생성")
    p_nd.add_argument("--from", dest="from_tag", required=True, help="이전 release tag (e.g. v0.7.8)")
    p_nd.add_argument("--to", required=True, help="새 release version (e.g. 0.7.9)")
    p_nd.add_argument("--dry-run", action="store_true", dest="dry_run")
    p_nd.add_argument("--apply", dest="apply", action="store_true", default=True)

    # release (Phase 2 — v0.7.10)
    p_rel = sub.add_parser("release", help="GitHub Release 생성 (gh release create)")
    p_rel.add_argument("--skip-validate", action="store_true", help="validate 사전 점검 skip")
    p_rel.add_argument("--dry-run", action="store_true", dest="dry_run")
    p_rel.add_argument("--apply", dest="apply", action="store_true", default=True)
    p_rel.add_argument("--json", action="store_true")

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
    p_dist.add_argument("--json", action="store_true")

    args = p.parse_args()
    if getattr(args, "dry_run", False):
        args.apply = False

    if args.command == "validate":
        result = cmd_validate(args)
    elif args.command == "version-bump":
        result = cmd_version_bump(args)
    elif args.command == "note-draft":
        result = cmd_note_draft(args)
    elif args.command == "release":
        result = cmd_release(args)
    elif args.command == "verify":
        result = cmd_verify(args)
    elif args.command == "rollback":
        result = cmd_rollback(args)
    elif args.command == "dist":
        result = cmd_dist(args)
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
