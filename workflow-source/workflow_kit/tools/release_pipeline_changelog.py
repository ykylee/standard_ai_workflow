"""release_pipeline.py 에서 추출한 changelog / release-note 경로 helper 모듈 (TASK-2026-08-11-main-007).

`tools/release_pipeline.py` 의 changelog-gen (Phase 4 — v0.7.14+) 관련 함수·상수를
verbatim 으로 옮긴 것이다. `release_pipeline.py` 가 `from release_pipeline_changelog
import *` 로 전량 재-export 하므로, 기존 check / caller 는 계속
`release_pipeline` 의 attribute (`rp._parse_git_log`, `rp.draft_changelog` 등) 로
접근한다. 이 모듈은 release_pipeline 을 import 하지 않는다 (순환 금지).
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime
from pathlib import Path

# release_pipeline.py 의 REPO_ROOT 와 동일한 값 (같은 tools/ 디렉터리 기준).
# ⚠️ 이름과 달리 git 저장소 루트가 아니라 `workflow-source/` 다 (`parents[2]`).
REPO_ROOT = Path(__file__).resolve().parents[2]
RELEASES_DIR = REPO_ROOT / "releases"

__all__ = [
    "SMOKE_COUNT_RE",
    "RELEASE_RE",
    "RELEASE_RE_BARE",
    "NON_RELEASE_VERSIONS",
    "SECTION_PREFIXES",
    "collect_commits_all_time",
    "collect_commits_in_range",
    "_parse_git_log",
    "categorize_by_section",
    "_changelog_version_sort_key",
    "draft_changelog",
    "_resolve_notes_file",
    "find_dist_files",
]


#: dashboard 의 `SMOKE_COUNT_PATTERN` 과 **같은 것을 본다**. 두 곳이 다른 정규식을
#: 들면 "노트에 적었는데 dashboard 가 못 읽는" 상태가 조용히 생긴다.
SMOKE_COUNT_RE = re.compile(
    r"누적\s+(?:[\w\s]*?\s+)?smoke\s+(?:test\s+)?\*\*(\d+)(?:/(\d+)|\+)\s+PASS\*\*"
)

RELEASE_RE = re.compile(r"\(v(\d+\.\d+(?:\.\d+)?)\)")
# v0.15.21+: bare `type(scope): vX.Y.Z ...` release-commit 형식도 인식한다.
# 최근 commit 관례가 괄호형 `(vX.Y.Z)` → 맨몸 `... : vX.Y.Z — ...` 로 바뀌면서
# parenthesized-only RELEASE_RE 가 v0.12~v0.15 대 를 전부 놓쳐 [Unreleased] 로 흡수하던 backfill bug 해소.
# conventional-commit 접두사(`type(scope): `) *직후* 의 선행 version 만 매칭하여
# prose 안의 version (예: `... v0.13.3-beta → v0.14.0-beta`) 오분류를 회피한다.
RELEASE_RE_BARE = re.compile(r"^[a-z]+(?:\([^)]*\))?:\s+v(\d+\.\d+(?:\.\d+)?)\b")

#: **release 가 아닌** version 문자열의 선언된 예외 (v1.1.3+).
#:
#: `RELEASE_RE` 는 subject 안의 `(vX.Y)` 를 release 로 본다. 그런데 이 저장소 초기
#: commit 두 건은 *워크플로우 문서 체계* 의 Phase 5 버전을 그 형식으로 적었다 —
#: package release 가 아니다 (둘 다 `pyproject.toml` 을 건드리지 않았다). 걸러내지
#: 않으면 semver 정렬 때문에 `[3.0.1]` 이 **최신 release 자리에** 앉아, CHANGELOG 를
#: 읽는 사람에게 "최신이 3.0.1" 이라고 거짓말한다.
#:
#: git tag 와 대조하는 방법은 쓸 수 없다 — 0.15.x 대 다수가 tag 없이 릴리스돼
#: 진짜 release 를 대량으로 지운다 (2026-08-09 실측: CHANGELOG 152 vs tag 121).
#: 그래서 *선언된 예외* 로 둔다 (`ROOT_ANCHOR_LEDGER` 와 같은 정공법).
NON_RELEASE_VERSIONS: dict[str, str] = {
    "3.0": "3a7e4c1 'Phase 5 official release (v3.0)' — 워크플로우 문서 체계 버전, package release ❌",
    "3.0.1": "9c4fb1d 'add Pi Coding Agent harness support (v3.0.1)' — 같은 체계, package release ❌",
}
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
        # 괄호형 `(vX.Y.Z)` 우선, 없으면 선행 bare 형 `type(scope): vX.Y.Z` (v0.15.21+).
        m = RELEASE_RE.search(subject) or RELEASE_RE_BARE.match(subject)
        version = m.group(1) if m else "unreleased"
        # 선언된 예외는 release 로 치지 않는다 — 해당 commit 은 [Unreleased] 로 흡수.
        if version in NON_RELEASE_VERSIONS:
            version = "unreleased"
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


def _changelog_version_sort_key(version: str) -> tuple[int, int, int]:
    """changelog 전용 semver 정렬 key. "unreleased" 는 최상단 sentinel.

    (모듈 상단의 `_version_sort_key(tag)` 는 git *tag* (vX.Y.Z-suffix) 전용이라
    "unreleased" sentinel + suffix-less version 을 처리하지 못한다 → 별도 helper.)

    "0.11.2" → (0, 11, 2). patch 부재 시 0 padding. parse 실패 시 (0,0,0).
    문자열 사전순 정렬의 두 자리 minor 오정렬 ("0.11" < "0.7") 를 해소한다.
    """
    if version == "unreleased":
        return (10**9, 10**9, 10**9)
    parts = version.split(".")
    try:
        nums = [int(p) for p in parts[:3]]
    except ValueError:
        return (0, 0, 0)
    while len(nums) < 3:
        nums.append(0)
    return (nums[0], nums[1], nums[2])


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

    # version order: semver 기준 최신 우선 (v0.15.21+).
    # 기존 문자열 reverse 정렬은 두 자리 minor 를 오정렬했다 ("0.11" < "0.7" 사전순) →
    # semver tuple key 로 교체. "unreleased" 는 항상 맨 위 (미배포 = 최신).
    versions = sorted(by_version.keys(), key=_changelog_version_sort_key, reverse=True)

    # metadata block 은 **생성기 안에** 둔다 — CHANGELOG.md 는 매 release 마다 전체가
    # 재생성되므로, 파일에 직접 써 넣으면 다음 생성 때 지워져 doc lint 가 다시 깨진다.
    lines = [
        "# Changelog",
        "",
        "- 문서 목적: 저장소의 모든 주요 변경을 release 단위로 기록한다 (Keep a Changelog 형식).",
        "- 범위: git log 에서 추출한 release 별 Added / Changed / Fixed 항목.",
        "- 대상 독자: maintainer, 릴리스 매니저, 외부 consumer",
        "- 상태: stable (자동 생성물)",
        f"- 최종 수정일: {datetime.now().date().isoformat()}",
        "- 관련 문서: [`./releases/`](./releases/) (release note), [`../docs/RELEASE.md`](../docs/RELEASE.md) (릴리스 절차)",
        "",
        "All notable changes to this project will be documented in this file.",
        "",
        "본 파일은 `tools/release_pipeline.py changelog-gen` 으로 자동 생성됩니다 (v0.7.14+).",
        "수동 편집은 다음 생성 시 덮어써진다 — 형식/metadata 변경은 생성기를 고칠 것.",
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


def find_dist_files(version: str) -> list[Path]:
    """dist/ 의 wheel + sdist glob. PEP 440 normalize: 0.7.10 → 0.7.10b0."""
    dist = REPO_ROOT / "dist"
    if not dist.exists():
        return []
    # PEP 440: 0.7.10-beta → 0.7.10b0
    base = version.split("-")[0]
    pep_version = base  # wheel 파일명은 X.Y.Z 형태
    return sorted(dist.glob(f"standard_ai_workflow-{pep_version}*"))
