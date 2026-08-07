"""workflow_kit.common.workspace_registry — host-scoped workspace registry (v0.15.20+).

표준 §10.2 의 §7.1 (workspace registry) 구현. 모티프: 한 호스트 안의 여러 worktree
(워크스페이스) 경로를 *git 밖* 에 등록해, 다른 도구(dashboard Panel 5 등) 가
in-flight 워크스페이스를 알아낼 수 있게 한다.

## 왜 필요한가

- §5A.3 실측: 메모리는 git-tracked 라, *현재 진행 중인* 워크스페이스는 중앙이 알 수 없다.
  registry 는 그 *진행 중* 정보를 호스트 파일로 보존해, dashboard 가 in-flight
  worktree 의 state.json 을 합류시킬 수 있게 한다.
- §7.1 의 *범위가 줄어든* 모티프: registry 가 현재 책임지는 건 (a) `host_id` ↔
  워크스페이스 *경로* 매핑, (b) `branch` / `harness` / `endpoint` 정적 메타, (c)
  `registered_at` / `last_seen_at` 활동 시점. 배타 제어는 git(§5D) 이 맡고, lease
  같은 동적 상태는 들지 않는다.

## 저장 위치

- 기본: ``~/.cache/workflow_kit/registry.json``
- override: ``WORKFLOW_REGISTRY_PATH`` env, 또는 ``XDG_CACHE_HOME`` env
- 권한: 0o600 (single-host file).
- atomic write: ``tmp + os.replace`` (process crash safety).

## host_id

- 우선순위: ``WORKFLOW_HOST_ID`` env > ``socket.gethostname()`` > ``uuid.uuid4().hex[:8]``
- 결정은 *모듈 import 시점* 이 아니라 첫 registry read/write 시 (lazy) — 그래야
  CI 와 같은 매번 다른 hostname 환경에서 매번 다른 host_id 를 만들지 않는다.

Public API:
    host_id() -> str
    registry_path() -> Path
    load() -> Registry
    save(reg: Registry) -> None
    register(path, *, branch, harness=None, endpoint=None) -> Registry
    unregister(*, path=None, branch=None, all=False) -> Registry
    list_entries() -> list[RegistryEntry]
    registry_paths() -> list[Path]
    is_stale(entry, *, now=None, threshold_seconds=DEFAULT_STALE_SECONDS) -> bool
"""

from __future__ import annotations

import json
import os
import socket
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

SCHEMA_VERSION: Final[str] = "1"
DEFAULT_STALE_SECONDS: Final[int] = 7 * 24 * 60 * 60  # 7일


@dataclass(frozen=True)
class RegistryEntry:
    """workspace 한 건의 정적 메타.

    `path` 는 git-tracked 가 아니다 — registry 가 호스트 외부에 들고 있어야
    합쳐지지 않은(squash 못 한) worktree 도 dashboard 가 볼 수 있다 (§5A.3).
    """

    path: str
    branch: str
    harness: str | None = None
    endpoint: str | None = None
    registered_at: str = ""
    last_seen_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "RegistryEntry":
        return cls(
            path=str(d.get("path", "")),
            branch=str(d.get("branch", "")),
            harness=(str(d["harness"]) if d.get("harness") is not None else None),
            endpoint=(str(d["endpoint"]) if d.get("endpoint") is not None else None),
            registered_at=str(d.get("registered_at", "")),
            last_seen_at=str(d.get("last_seen_at", "")),
        )


@dataclass
class Registry:
    schema_version: str = SCHEMA_VERSION
    host_id: str = ""
    updated_at: str = ""
    entries: list[RegistryEntry] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(
            {
                "schema_version": self.schema_version,
                "host_id": self.host_id,
                "updated_at": self.updated_at,
                "entries": [e.to_dict() for e in self.entries],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, raw: str) -> "Registry":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return cls(entries=[])
        if not isinstance(data, dict):
            return cls(entries=[])
        entries_raw = data.get("entries", [])
        entries: list[RegistryEntry] = []
        if isinstance(entries_raw, list):
            for item in entries_raw:
                if isinstance(item, dict):
                    entries.append(RegistryEntry.from_dict(item))
        return cls(
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
            host_id=str(data.get("host_id", "")),
            updated_at=str(data.get("updated_at", "")),
            entries=entries,
        )


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def host_id() -> str:
    """이 호스트의 안정적 id. 캐시된 게 registry 에 있으면 그걸 우선."""
    return _resolve_host_id()


def _resolve_host_id() -> str:
    explicit = os.environ.get("WORKFLOW_HOST_ID", "").strip()
    if explicit:
        return explicit
    try:
        name = socket.gethostname().strip()
        if name:
            return name
    except OSError:
        pass
    return uuid.uuid4().hex[:8]


def registry_path() -> Path:
    """registry 파일의 현재 위치. env override > XDG_CACHE_HOME > default."""
    override = os.environ.get("WORKFLOW_REGISTRY_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_CACHE_HOME", "").strip()
    if xdg:
        return Path(xdg).expanduser() / "workflow_kit" / "registry.json"
    return Path.home() / ".cache" / "workflow_kit" / "registry.json"


def load() -> Registry:
    """registry 파일을 읽는다. 부재 / 깨짐 시 *빈 Registry* 를 돌려준다.

    host_id 가 비어 있으면 (즉, 파일이 없거나 새 호스트) 현재 host_id 로 채운다.
    """
    path = registry_path()
    if not path.is_file():
        return Registry(host_id=_resolve_host_id())
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return Registry(host_id=_resolve_host_id())
    reg = Registry.from_json(raw)
    if not reg.host_id:
        reg.host_id = _resolve_host_id()
    return reg


def save(reg: Registry) -> None:
    """registry 를 atomic 하게 저장. 권한 0o600. 단일 host 의 단일 file 이다."""
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    reg.updated_at = _utcnow_iso()
    payload = reg.to_json()
    # atomic write: tmp dir 같은 곳에서 rename. 같은 dir 내 tmp 가 가장 안전.
    fd, tmp_name = tempfile.mkstemp(
        prefix=".registry.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            fp.write(payload)
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
    except Exception:
        # tmp 잔여물 정리 — 다음 save 가 덮어쓰지만 명시적으로.
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _normalize(path: Path | str) -> str:
    p = Path(path).expanduser()
    try:
        return str(p.resolve())
    except OSError:
        return str(p)


def register(
    path: Path | str,
    *,
    branch: str,
    harness: str | None = None,
    endpoint: str | None = None,
) -> Registry:
    """workspace 한 건을 등록. 동일 path 가 이미 있으면 `last_seen_at` 만 갱신.

    Args:
        path: worktree 의 절대 경로. resolve 후 string 으로 보관.
        branch: 작업 브랜치 슬러그.
        harness: 하네스 식별자 (선택).
        endpoint: 외부에서 도달 가능한 endpoint (선택; 향후 cross-host 의 실마리).

    Returns:
        갱신된 ``Registry``. *save 전에* 다른 일을 보고 싶을 때 쓰거나,
        호출자가 한 번 더 save 해도 안전하다 (idempotent).
    """
    reg = load()
    norm = _normalize(path)
    now = _utcnow_iso()
    found = False
    new_entries: list[RegistryEntry] = []
    for entry in reg.entries:
        if entry.path == norm:
            new_entries.append(
                RegistryEntry(
                    path=entry.path,
                    branch=branch or entry.branch,
                    harness=harness if harness is not None else entry.harness,
                    endpoint=endpoint if endpoint is not None else entry.endpoint,
                    registered_at=entry.registered_at or now,
                    last_seen_at=now,
                )
            )
            found = True
        else:
            new_entries.append(entry)
    if not found:
        new_entries.append(
            RegistryEntry(
                path=norm,
                branch=branch,
                harness=harness,
                endpoint=endpoint,
                registered_at=now,
                last_seen_at=now,
            )
        )
    reg.entries = new_entries
    save(reg)
    return reg


def unregister(
    *,
    path: Path | str | None = None,
    branch: str | None = None,
    all: bool = False,
) -> Registry:
    """조건에 맞는 entry 를 제거. ``--all`` 이면 전부.

    Returns:
        갱신된 ``Registry``.
    """
    if not (path or branch or all):
        # 빈 호출은 no-op — caller 가 명시했어야 한다.
        return load()
    reg = load()
    if all:
        reg.entries = []
        save(reg)
        return reg
    target = _normalize(path) if path else None
    new_entries: list[RegistryEntry] = []
    for entry in reg.entries:
        if target and entry.path == target:
            continue
        if branch and entry.branch == branch:
            continue
        new_entries.append(entry)
    reg.entries = new_entries
    save(reg)
    return reg


def list_entries() -> list[RegistryEntry]:
    """전체 entry list 를 정렬된 상태로 돌려준다."""
    reg = load()
    return sorted(reg.entries, key=lambda e: (e.branch, e.path))


def registry_paths() -> list[Path]:
    """registry 의 모든 path 를 ``[Path]`` 로. dashboard 합류 후보."""
    return [Path(e.path) for e in list_entries()]


def is_stale(
    entry: RegistryEntry,
    *,
    now: datetime | None = None,
    threshold_seconds: int = DEFAULT_STALE_SECONDS,
) -> bool:
    """``last_seen_at`` 이 ``threshold_seconds`` 를 넘었으면 True.

    자동 비활성 ❌ (표시만 — §5D.4 의 *되돌릴 수 없는 작업은 확인 후* 원칙).
    """
    if not entry.last_seen_at:
        return True
    cur = now or datetime.now(timezone.utc)
    try:
        seen = datetime.strptime(entry.last_seen_at, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return True
    return (cur - seen).total_seconds() > threshold_seconds
