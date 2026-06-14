#!/usr/bin/env python3
"""v0.7.9+: standard-ai-workflow release pipeline 정식화 (3 subcommand).

release 절차 (validate → version-bump → note-draft → gh release create) 의
*기계화 layer*. manual 절차 (memory #5 / docs/RELEASE.md) 의 *부족 부분* 자동화.

3 subcommand (Phase 1 of 2; release trigger 는 v0.7.10+ follow-up):
- validate: check_packaging + v0.7.8 doctor + state.json freshness + git status clean
- version-bump: pyproject.toml version patch (--to=... or --patch / --minor / --major)
- note-draft: git log --since=<prev_tag> → release note skeleton 자동 생성

PyPI/TestPyPI 업로드 ❌ (memory #5 의 release 채널 정책 — GitHub Releases 만).
gh release create 는 수동 trigger (v0.7.10+ follow-up).

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

    args = p.parse_args()
    if args.dry_run:
        args.apply = False

    if args.command == "validate":
        result = cmd_validate(args)
    elif args.command == "version-bump":
        result = cmd_version_bump(args)
    elif args.command == "note-draft":
        result = cmd_note_draft(args)
    else:
        p.error(f"unknown command: {args.command}")
        return 2

    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"=== {args.command} ({'DRY-RUN' if getattr(args, 'dry_run', False) else 'APPLY'}) ===")
        for k, v in result.items():
            if isinstance(v, dict):
                print(f"  {k}:")
                for k2, v2 in v.items():
                    print(f"    {k2}: {v2}")
            elif isinstance(v, list):
                print(f"  {k}: [{', '.join(str(x) for x in v[:5])}...]")
            else:
                print(f"  {k}: {v}")

    # exit code: validate 만 exit 1 가능 (non-zero 시)
    if args.command == "validate":
        if not all(v.get("ok", False) for v in result.values()):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
