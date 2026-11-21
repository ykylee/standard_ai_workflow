"""위키 저장소 참조의 원격 읽기 (M-036 WBS-36.2) — 요구 R8.4 · E3, hub_spec §6.7.

허브는 프로젝트 주소를 식별에만 쓴다 (R3.7). 예외는 하나 — 소유자가 위키 원격 읽기를 켜면
(``project.settings_json`` 의 ``wiki_remote.fetch_url``) lint 때 그 저장소를 **읽기 전용**으로 받는다:
``git clone --bare --filter=blob:none`` 을 임시 디렉터리에 하고(파일 내용은 받지 않는다 — 트리 · 커밋만),
끝나면 지운다. 쓰기 · push 는 없다.

잰 것 / 못 잰 것:
- 저장소 참조 ``[[path.md]]`` — 기본 브랜치 머리 트리에 그 경로가 있는가
- 출처 sha — 그 커밋이 저장소에 있는가
- freshness — 출처 sha 이후 ``last_ingested_from`` 에 적힌 경로가 바뀌었는가 (대상 = sha 와 경로가 둘 다 있는 페이지)
- 받기 실패 · 시간 초과 · 꺼짐 → 셋 다 **'미측정'** (통과 0건) — 이유를 싣는다.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

#: 허용 주소 — ``ext::`` · ``fd::`` 같은 git 원격 도우미는 명령 실행이 되므로 막는다.
_URL = re.compile(r"^(?:https://[^\s]+|ssh://[^\s]+|git@[A-Za-z0-9.-]+:[^\s]+|file:///[^\s]+)$")
TIMEOUT_S = 120
_LAST_INGESTED_FROM = re.compile(r"^last_ingested_from:\s*(.+)$", re.M)


def check_fetch_url(url: str) -> str:
    if not isinstance(url, str) or not _URL.match(url) or url.startswith("-"):
        raise ValueError("https:// · ssh:// · git@host:path · file:/// 만 (git 원격 도우미 주소는 거절)")
    return url


def _git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "true", "SSH_ASKPASS": "true",
           "GIT_CONFIG_NOSYSTEM": "1", "LC_ALL": "C"}
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=TIMEOUT_S, env=env, check=False)


def source_paths(body: str) -> list[str]:
    """frontmatter ``last_ingested_from:`` 의 경로들 (쉼표 · 공백 구분, ``#절`` · 괄호 주석은 뗀다)."""
    if not body.startswith("---\n"):
        return []
    end = body.find("\n---", 4)
    m = _LAST_INGESTED_FROM.search(body[4:end] if end > 0 else "")
    if not m:
        return []
    raw = m.group(1).strip().strip("[]")
    out = []
    for part in re.split(r"[,\s]+", raw):
        part = part.strip().strip("'\"`").split("#", 1)[0]
        if part and ("/" in part or part.endswith((".md", ".py", ".json", ".toml"))):
            out.append(part.rstrip("/"))
    return out


def unmeasured(reason: str, repo_refs: int) -> dict[str, Any]:
    return {
        "repo_references": {"status": "unmeasured", "count": repo_refs, "reason": reason},
        "source_sha": {"status": "unmeasured", "reason": reason},
        "freshness": {"status": "unmeasured", "targets": 0, "reason": reason},
    }


def measure(fetch_url: str | None, pages: list[dict[str, Any]], repo_refs: list[tuple[str, str]]) -> dict[str, Any]:
    """``pages`` = ``[{path, body, source_sha}]``. 받지 못하면 전부 미측정."""
    if not fetch_url:
        return unmeasured("위키 원격 읽기 꺼짐 — 소유자가 hub_wiki_remote_set 으로 켠다 (R8.4)", len(repo_refs))
    with tempfile.TemporaryDirectory(prefix="hubwiki-remote-") as d:
        repo = Path(d) / "repo.git"
        try:
            cp = _git(["clone", "--bare", "--quiet", "--filter=blob:none", "--no-tags", "--", fetch_url, str(repo)])
        except subprocess.TimeoutExpired:
            return unmeasured(f"원격 받기 시간 초과 ({TIMEOUT_S}s)", len(repo_refs))
        except OSError as exc:
            return unmeasured(f"git 실행 실패: {exc}", len(repo_refs))
        if cp.returncode != 0:
            return unmeasured(f"원격 받기 실패: {cp.stderr.strip()[-300:]}", len(repo_refs))
        head = _git(["rev-parse", "HEAD"], repo).stdout.strip()
        if not head:
            return unmeasured("원격에 기본 브랜치 커밋이 없다", len(repo_refs))

        def exists(path: str) -> bool:
            return bool(_git(["ls-tree", "--name-only", "HEAD", "--", path], repo).stdout.strip())

        def has_commit(sha: str) -> bool:
            return _git(["cat-file", "-e", f"{sha}^{{commit}}"], repo).returncode == 0

        missing_refs = [{"page": page, "target": t} for page, t in repo_refs if not exists(t)]
        with_sha = [p for p in pages if p.get("source_sha")]
        unknown = [{"page": p["path"], "sha": p["source_sha"]} for p in with_sha if not has_commit(p["source_sha"])]
        stale, targets = [], 0
        for p in with_sha:
            paths = source_paths(p["body"])
            if not paths or not has_commit(p["source_sha"]):
                continue
            targets += 1
            n = _git(["rev-list", "--count", f"{p['source_sha']}..HEAD", "--", *paths], repo).stdout.strip()
            if n and n != "0":
                stale.append({"page": p["path"], "sha": p["source_sha"], "commits_since": int(n), "sources": paths})
        return {
            "repo_references": {"status": "measured", "count": len(repo_refs), "missing": missing_refs, "head": head},
            "source_sha": {"status": "measured", "pages": len(with_sha), "unknown": unknown},
            "freshness": {"status": "measured", "targets": targets, "stale": stale,
                          "unmeasured_pages": len(pages) - targets},
        }
