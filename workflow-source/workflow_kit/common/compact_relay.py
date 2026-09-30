"""compact 중계 — 압축 경계를 워크플로우 메모리로 건너뛴다 (ADR-030, `core/compact_relay_spec.md`).

하네스가 컨텍스트를 압축하면 요약이 "확인했다 / 아직 안 확인했다" 의 구분과 다음 한 걸음을
잃을 수 있다. 압축 **전**에 checkpoint 를 적고(스킬 = 판단 층, `PreCompact` = 기계 층),
압축 **뒤** 하네스 요약과 식별자를 대조하고(`PostCompact`), `SessionStart(compact)` 로
예산 안의 상태 기록을 다시 넣는다.

계약 (스펙 §1):

- `session_handoff.md` · `state.json` 은 읽기만 한다. transcript 는 읽지 않는다.
- `.compact/` 는 자기 무시 `.gitignore` 를 갖는다 — 소비자 루트 `.gitignore` 에 기대지 않는다.
- 재주입은 `context_budget` 의 `compact_reinjection` 바이트를 넘지 않는다 (렌더러가 자른다).
- 워크플로우 메모리가 없는 workspace, 브랜치 디렉터리가 아직 없는 브랜치에서는 아무것도
  만들지 않는다 — 브랜치 메모리는 `wk backlog-update` 만 만든다.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow_kit.common.context_budget import BUDGETS_BY_KEY
from workflow_kit.common.paths import project_workspace_root, workflow_branch_dir, workflow_memory_dir
from workflow_kit.common.project_docs import TASK_ID_PATTERN

SCHEMA_VERSION = 1
COMPACT_DIRNAME = ".compact"
CHECKPOINT_FILENAME = "checkpoint.json"
SUMMARY_FILENAME = "summary.md"
GITIGNORE_BODY = "*\n"

#: 재주입 상한 — 예산 정본에서 읽는다 (값을 여기 다시 적지 않는다).
RESTORE_BUDGET_KEY = "compact_reinjection"

#: 판단 층 항목 하나의 상한. 한 항목이 예산을 통째로 먹으면 뒤 절이 전부 밀려난다.
ITEM_MAX_BYTES = 600
#: 기계 층 미커밋 파일 목록 상한 — 넘으면 개수만 남긴다.
DIRTY_FILES_MAX = 20

JUDGMENT_KEYS: tuple[str, ...] = ("next", "unverified", "verified", "rejected")
OPEN_TASK_STATES: frozenset[str] = frozenset({"in_progress", "blocked"})

HEADER_TAG = "[compact-checkpoint]"

# 스펙 §5 — 대조하는 식별자형 토큰. 자연어는 대조하지 않는다.
_TASK_ID_RE = re.compile(TASK_ID_PATTERN)
_MILESTONE_RE = re.compile(r"\bM-\d{3}\b")
_WBS_RE = re.compile(r"\bWBS-\d+(?:\.\d+)*\b")
_BACKTICK_RE = re.compile(r"`([^`\n]{2,200})`")
_SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")


def restore_limit_bytes() -> int:
    return BUDGETS_BY_KEY[RESTORE_BUDGET_KEY].limit_bytes


def _utf8_len(text: str) -> int:
    return len(text.encode("utf-8"))


def _clip(text: str, limit: int) -> str:
    """UTF-8 바이트 기준으로 자른다 (문자 경계 유지)."""
    if _utf8_len(text) <= limit:
        return text
    raw = text.encode("utf-8")[: max(limit - 3, 0)]
    return raw.decode("utf-8", errors="ignore") + "…"


def now_iso(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(timespec="seconds")


# --- 위치 -------------------------------------------------------------------------------


@dataclass(frozen=True)
class RelayLocation:
    workspace_root: Path
    branch_dir: Path

    @property
    def compact_dir(self) -> Path:
        return self.branch_dir / COMPACT_DIRNAME

    @property
    def checkpoint_path(self) -> Path:
        return self.compact_dir / CHECKPOINT_FILENAME

    @property
    def summary_path(self) -> Path:
        return self.compact_dir / SUMMARY_FILENAME

    def rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.workspace_root).as_posix()
        except ValueError:
            return path.as_posix()


def _git(workspace: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(workspace), *args],
            capture_output=True, text=True, encoding="utf-8", timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def _profile_under(workspace: Path) -> Path | None:
    for candidate in (
        workspace / "docs" / "PROJECT_PROFILE.md",
        workspace / "ai-workflow" / "memory" / "active" / "PROJECT_PROFILE.md",
    ):
        if candidate.is_file():
            return candidate
    return None


def locate_from_profile(profile: Path) -> RelayLocation | None:
    """profile 에서 브랜치 디렉터리를 푼다. 메모리 · 브랜치 디렉터리가 없으면 ``None``."""
    if not workflow_memory_dir(profile).is_dir():
        return None
    branch_dir = workflow_branch_dir(profile)
    if not branch_dir.is_dir():
        return None
    return RelayLocation(workspace_root=project_workspace_root(profile).resolve(), branch_dir=branch_dir)


def locate_from_cwd(cwd: str | os.PathLike[str] | None) -> RelayLocation | None:
    """hook 입력 ``cwd`` → 그 git toplevel 순서로 workspace 를 찾는다 (ADR-030 결정 2).

    위로 무한히 거슬러 올라가지 않는다 — 전역 설치된 플러그인이 워크플로우 밖 프로젝트의
    상위 디렉터리에 있는 남의 메모리를 집어 들면 안 된다.
    """
    if not cwd:
        return None
    base = Path(cwd)
    if not base.is_dir():
        return None
    candidates = [base]
    top = _git(base, "rev-parse", "--show-toplevel")
    if top and top.strip():
        candidates.append(Path(top.strip()))
    for workspace in candidates:
        profile = _profile_under(workspace)
        if profile is not None:
            return locate_from_profile(profile)
    return None


def ensure_compact_dir(loc: RelayLocation) -> Path:
    """`.compact/` 와 자기 무시 `.gitignore` 를 보장한다 (ADR-030 결정 3)."""
    loc.compact_dir.mkdir(exist_ok=True)
    ignore = loc.compact_dir / ".gitignore"
    if not ignore.is_file() or ignore.read_text(encoding="utf-8") != GITIGNORE_BODY:
        ignore.write_text(GITIGNORE_BODY, encoding="utf-8")
    return loc.compact_dir


# --- checkpoint 입출력 --------------------------------------------------------------------


def empty_checkpoint(now: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": None,
        "branch": None,
        "head": None,
        "created": now,
        "updated": now,
        "trigger": None,
        "custom_instructions": None,
        "judgment": None,
        "mechanical": None,
        "relay": None,
    }


def load_checkpoint(loc: RelayLocation) -> dict[str, Any] | None:
    if not loc.checkpoint_path.is_file():
        return None
    try:
        data = json.loads(loc.checkpoint_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        return None
    return data


def save_checkpoint(loc: RelayLocation, data: dict[str, Any]) -> None:
    ensure_compact_dir(loc)
    tmp = loc.checkpoint_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, loc.checkpoint_path)


# --- 기계 층 ------------------------------------------------------------------------------


_TASK_TITLE_RE = re.compile(r"^#\s+TASK-[^\s]+\s+[—-]\s+(.+?)\s*$", re.MULTILINE)
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def _task_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """task frontmatter 의 스칼라 키만. hook 은 압축마다 돌므로 무거운 파서(pydantic)를 싣지 않는다."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    pairs: dict[str, str] = {}
    for raw in match.group(1).splitlines():
        key, sep, value = raw.partition(":")
        if sep and key and not key.startswith((" ", "-", "#")):
            pairs[key.strip()] = value.split("#", 1)[0].strip()
    return pairs, text[match.end():]


def collect_open_tasks(branch_dir: Path) -> list[dict[str, str]]:
    """브랜치 `backlog/tasks/` frontmatter(SSOT) 에서 in_progress · blocked task."""
    tasks: list[dict[str, str]] = []
    for path in sorted((branch_dir / "backlog" / "tasks").glob("TASK-*.md")):
        text = path.read_text(encoding="utf-8")
        pairs, body = _task_frontmatter(text)
        status = pairs.get("status", "")
        if status not in OPEN_TASK_STATES:
            continue
        title_match = _TASK_TITLE_RE.search(body)
        tasks.append({
            "id": pairs.get("id") or path.stem,
            "status": status,
            "title": _clip(title_match.group(1), 200) if title_match else "",
            "wbs": pairs.get("wbs", ""),
        })
    return tasks


def collect_mechanical(loc: RelayLocation) -> dict[str, Any]:
    porcelain = _git(loc.workspace_root, "status", "--porcelain") or ""
    dirty = [line[3:] for line in porcelain.splitlines() if len(line) > 3]
    return {
        "tasks": collect_open_tasks(loc.branch_dir),
        "dirty_files": dirty[:DIRTY_FILES_MAX],
        "dirty_count": len(dirty),
    }


def current_head(workspace: Path) -> str | None:
    out = _git(workspace, "rev-parse", "--short", "HEAD")
    return out.strip() if out and out.strip() else None


# --- 모드 ---------------------------------------------------------------------------------


def write_note(
    loc: RelayLocation,
    *,
    next_steps: list[str],
    unverified: list[str],
    verified: list[str],
    rejected: list[str],
    now: str,
) -> dict[str, Any]:
    """판단 층을 **대체**해 쓰고 ``pending`` 으로 둔다 (스펙 §2, ADR-030 결정 5)."""
    data = load_checkpoint(loc) or empty_checkpoint(now)
    data["judgment"] = {
        "pending": True,
        "noted_at": now,
        **{
            key: [_clip(item.strip(), ITEM_MAX_BYTES) for item in items if item.strip()]
            for key, items in zip(JUDGMENT_KEYS, (next_steps, unverified, verified, rejected))
        },
    }
    data["updated"] = now
    save_checkpoint(loc, data)
    return data


def hook_pre(loc: RelayLocation, payload: dict[str, Any], *, now: str) -> dict[str, Any]:
    """기계 층을 수집하고 대기 중인 판단 층을 이 세션으로 인수한다."""
    session_id = payload.get("session_id") or None
    data = load_checkpoint(loc)
    judgment = (data or {}).get("judgment")
    pending = isinstance(judgment, dict) and judgment.get("pending") is True
    same_session = data is not None and session_id is not None and data.get("session_id") == session_id
    if data is None or not (pending or same_session):
        data = empty_checkpoint(now)
        judgment = None
    if isinstance(judgment, dict):
        judgment["pending"] = False
    data["judgment"] = judgment
    data["session_id"] = session_id
    data["branch"] = loc.branch_dir.name
    data["head"] = current_head(loc.workspace_root)
    data["trigger"] = payload.get("trigger")
    data["custom_instructions"] = payload.get("custom_instructions") or None
    data["mechanical"] = collect_mechanical(loc)
    data["relay"] = None
    data["updated"] = now
    save_checkpoint(loc, data)
    return data


def checkpoint_identifiers(data: dict[str, Any]) -> list[str]:
    """스펙 §5 — checkpoint 의 식별자형 토큰 (정렬, 중복 제거)."""
    texts: list[str] = []
    judgment = data.get("judgment") or {}
    for key in JUDGMENT_KEYS:
        texts.extend(judgment.get(key) or [])
    mechanical = data.get("mechanical") or {}
    for task in mechanical.get("tasks") or []:
        texts.append(task.get("id", ""))
        texts.append(task.get("wbs", ""))
    found: set[str] = set()
    for text in texts:
        found.update(_TASK_ID_RE.findall(text))
        found.update(_MILESTONE_RE.findall(text))
        found.update(_WBS_RE.findall(text))
        found.update(tok.strip() for tok in _BACKTICK_RE.findall(text) if tok.strip())
        found.update(
            sha for sha in _SHA_RE.findall(text)
            if re.search(r"\d", sha) and re.search(r"[a-f]", sha)
        )
    # WBS 참조(`M-021/WBS-21.1`) 는 M · WBS 두 토큰으로 이미 잡힌다 — 합성 문자열은 빼지 않는다.
    return sorted(t for t in found if t)


def hook_post(loc: RelayLocation, payload: dict[str, Any], *, now: str) -> dict[str, Any] | None:
    """요약 원문을 보관하고 누락 식별자를 센다. checkpoint 가 없으면 ``None``.

    하네스가 요약 원문(``compact_summary``)을 주지 않으면 대조하지 않는다 — 빈 문자열과 대조하면
    식별자 전부가 '누락' 으로 날조된다. Codex 0.143.0 의 ``PostCompact`` 입력 스키마에는 이 필드가
    없다 (TASK-2026-09-30-main-008 실측). 그때 ``relay`` 는 ``summary_available: false`` 이고
    ``missing_count`` 는 ``None`` 이다 — 0 누락과 구분한다.
    """
    data = load_checkpoint(loc)
    if data is None:
        return None
    summary = payload.get("compact_summary")
    ids = checkpoint_identifiers(data)
    if not isinstance(summary, str):
        if loc.summary_path.is_file():
            loc.summary_path.unlink()  # 이전 압축의 요약이 이번 것으로 읽히지 않게
        data["relay"] = {
            "summary_available": False,
            "summary_path": None,
            "summary_bytes": 0,
            "checked_count": len(ids),
            "missing_count": None,
            "missing": [],
        }
        data["updated"] = now
        save_checkpoint(loc, data)
        return data
    ensure_compact_dir(loc)
    loc.summary_path.write_text(summary, encoding="utf-8")
    missing = [t for t in ids if t not in summary]
    data["relay"] = {
        "summary_available": True,
        "summary_path": loc.rel(loc.summary_path),
        "summary_bytes": _utf8_len(summary),
        "checked_count": len(ids),
        "missing_count": len(missing),
        "missing": missing,
    }
    data["updated"] = now
    save_checkpoint(loc, data)
    return data


#: `--hook post` 보고 한 줄의 상한. Claude Code 는 이 출력을 압축 뒤 컨텍스트에 싣는다.
POST_REPORT_MAX_BYTES = 600


def render_post_report(data: dict[str, Any]) -> str:
    """`PostCompact` 출력 — 누락 식별자를 **여기서** 말한다.

    Claude Code 2.1.285 실측(2026-09-30): `SessionStart(compact)` 재주입이 `PostCompact` 보다
    **먼저** 돈다. 재주입 본문은 대조 결과를 볼 수 없으므로, 모델에게 닿는 대조 결과는 이 줄이다.
    """
    r = data.get("relay") or {}
    if r.get("summary_available") is False:
        return f"{HEADER_TAG} 요약 대조 불가 — 하네스가 요약 원문을 주지 않았다 (식별자 {r.get('checked_count', 0)}개 미대조)"
    if not r.get("checked_count"):
        return f"{HEADER_TAG} 요약 대조 대상 없음 (checkpoint 에 식별자가 없다)"
    head = f"{HEADER_TAG} 요약 대조: 누락 {r['missing_count']}/{r['checked_count']}"
    if not r.get("missing"):
        return head
    return _clip(f"{head} — 요약에 없는 식별자: {', '.join(r['missing'])}", POST_REPORT_MAX_BYTES)


def clear(loc: RelayLocation) -> list[str]:
    removed: list[str] = []
    for path in (loc.checkpoint_path, loc.summary_path):
        if path.is_file():
            path.unlink()
            removed.append(loc.rel(path))
    return removed


# --- 재주입 -------------------------------------------------------------------------------


def _age_text(then_iso: str | None, now: datetime) -> str:
    if not then_iso:
        return "나이 모름"
    try:
        then = datetime.fromisoformat(then_iso)
    except ValueError:
        return "나이 모름"
    seconds = max(int((now - then).total_seconds()), 0)
    if seconds < 3600:
        return f"{seconds // 60}분 전"
    if seconds < 86400:
        return f"{seconds // 3600}시간 전"
    return f"{seconds // 86400}일 전"


def _sections(data: dict[str, Any]) -> list[tuple[str, list[str]]]:
    """스펙 §4 — 순서가 곧 우선순위다."""
    judgment = data.get("judgment") or {}
    mechanical = data.get("mechanical") or {}
    relay = data.get("relay") or {}
    tasks = [
        f"{t['id']} [{t['status']}]" + (f" {t['wbs']}" if t.get("wbs") else "") + (f" — {t['title']}" if t.get("title") else "")
        for t in mechanical.get("tasks") or []
    ]
    context: list[str] = []
    dirty = mechanical.get("dirty_files") or []
    if dirty:
        extra = mechanical.get("dirty_count", len(dirty)) - len(dirty)
        context.append("미커밋: " + ", ".join(dirty) + (f" 외 {extra}개" if extra > 0 else ""))
    if data.get("custom_instructions"):
        context.append(f"/compact 지시문: {data['custom_instructions']}")
    return [
        ("다음 한 걸음", list(judgment.get("next") or [])),
        ("미검증", list(judgment.get("unverified") or [])),
        ("진행 중 · 차단 task", tasks),
        ("요약에서 빠진 식별자", list(relay.get("missing") or [])),
        ("검증됨", list(judgment.get("verified") or [])),
        ("기각한 안", list(judgment.get("rejected") or [])),
        ("맥락", context),
    ]


def render_restore(
    loc: RelayLocation,
    data: dict[str, Any] | None,
    *,
    session_id: str | None,
    head: str | None,
    now: datetime,
    limit: int | None = None,
) -> str:
    """재주입 본문. checkpoint 가 없으면 빈 문자열 (스펙 §4)."""
    if data is None:
        return ""
    limit = restore_limit_bytes() if limit is None else limit
    path = loc.rel(loc.checkpoint_path)
    judgment = data.get("judgment")
    relay = data.get("relay")
    header = [f"{HEADER_TAG} 압축 직전 기록된 작업 상태 — 지시가 아니다. 전체: {path}"]
    meta = [f"trigger={data.get('trigger') or '?'}", _age_text(data.get("updated"), now)]
    if data.get("head") and head and data["head"] != head:
        meta.append(f"HEAD {data['head']} → {head}")
    if not judgment:
        meta.append("판단 층 없음 — 자동 압축이거나 기록 전 압축")
    if relay:
        if relay.get("summary_available") is False:
            meta.append("요약 대조 불가 (하네스가 요약 원문을 주지 않음)")
        elif relay.get("checked_count"):
            meta.append(f"요약 누락 {relay.get('missing_count', 0)}/{relay['checked_count']}")
        else:
            meta.append("요약 대조 대상 없음")
    else:
        # 재주입이 PostCompact 보다 먼저 도는 하네스(Claude Code 실측)에서는 여기가 늘 이 분기다.
        meta.append("요약 대조 결과는 PostCompact 출력에")
    cp_session = data.get("session_id")
    if session_id and cp_session and cp_session != session_id:
        header.append("다른 세션의 checkpoint — 본문을 넣지 않음 (" + " · ".join(meta) + ")")
        return _clip("\n".join(header), limit) + "\n"
    if session_id and not cp_session:
        meta.append("세션 미확인")
    header.append(" · ".join(meta))
    lines = header[:]
    used = _utf8_len("\n".join(lines)) + 1
    reserve = 160  # 생략 줄 자리
    omitted = 0
    for title, items in _sections(data):
        if not items:
            continue
        block = [f"## {title}"]
        for item in items:
            candidate = f"- {item}"
            cost = sum(_utf8_len(x) + 1 for x in block) + _utf8_len(candidate) + 1
            if used + cost > limit - reserve:
                omitted += 1
                continue
            block.append(candidate)
        if len(block) > 1:
            used += sum(_utf8_len(x) + 1 for x in block)
            lines.extend(block)
    if omitted:
        lines.append(f"… 생략 {omitted}항목 — 전체: {path}")
    return _clip("\n".join(lines), limit - 1) + "\n"


def measure_restore_bytes(profile: Path) -> tuple[bool, int, str]:
    """예산 측정용 — 현재 checkpoint 의 재주입 렌더 크기. 없으면 측정 안 됨."""
    loc = locate_from_profile(profile)
    if loc is None:
        return False, 0, "브랜치 메모리 없음"
    data = load_checkpoint(loc)
    if data is None:
        return False, 0, "checkpoint 없음"
    text = render_restore(
        loc, data, session_id=None, head=current_head(loc.workspace_root), now=datetime.now(timezone.utc)
    )
    return True, _utf8_len(text), loc.rel(loc.checkpoint_path)
