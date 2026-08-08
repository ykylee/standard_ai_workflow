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

## mavis 글로벌 동기

같은 호스트의 mavis 데스크탑 (``~/.minimax/mcp/mcp.json``) 와의 양방향 동기:
- ``import_mavis_aliases``: mavis 의 다른 alias 들을 registry entries 로 환원.
- ``export_to_mavis``: registry entries 를 mavis 글로벌에 ``mavis:<branch>`` alias 로
  emit (atomic, builtin 5종 + 우리 alias 보호).
- ``sync_mavis``: 위 둘을 한 번에.

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
    import_mavis_aliases(target_path=None, *, force=False) -> dict
    export_to_mavis(new_aliases, *, target_path=None, force=False) -> dict
    sync_mavis(target_path=None) -> dict
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


# ---------------------------------------------------------------------------
# mavis 글로벌 동기
# ---------------------------------------------------------------------------

#: mavis 데스크탑이 *유일하게* 읽는 글로벌 mcp.json. §6.5.2 의 DataDir = ~/.minimax.
#: ``bootstrap_lib.mcp.DEFAULT_MAVIS_GLOBAL_MCP_PATH`` 와 같은 상수. 본 모듈이
#: single source of truth (host-scoped resource 의 모든 일을 한 자리에).
DEFAULT_MAVIS_GLOBAL_MCP_PATH: Path = Path.home() / ".minimax" / "mcp" / "mcp.json"

#: mavis 글로벌의 alias 를 registry entry path 로 환원할 때 쓰는 prefix. 실제
#: 파일 시스템 경로가 아니라는 사실을 *명시적 prefix* 로 표시 (dashboard 가
#: ``__mavis__/`` 경로로 합류 시도하지 않게).
_MAVIS_PATH_PREFIX: str = "__mavis__/"

#: mavis 글로벌에서 *건드리면 안 되는* 보호 alias. 이 셋은 import 대상도 아니고
#: export 의 target 도 아니다.
MAVIS_PROTECTED_ALIASES: Final[frozenset[str]] = frozenset(
    {
        "matrix",
        "playwright",
        "cu",
        "trash",
        "github",
        # 우리 표준 alias (mavis 가 mcp.json 에 이미 가질 수 있는 이름).
        "standardAiWorkflowReadOnly",
    }
)


def mavis_global_path() -> Path:
    """현재 호스트의 mavis 데스크탑 글로벌 mcp.json 경로. override env 동일 패턴."""
    override = os.environ.get("WORKFLOW_MAVIS_GLOBAL_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return DEFAULT_MAVIS_GLOBAL_MCP_PATH


def _mavis_endpoint(entry: dict) -> str | None:
    """mavis 글로벌 alias 의 endpoint 추출 (command 또는 url)."""
    if not isinstance(entry, dict):
        return None
    cmd = entry.get("command")
    if isinstance(cmd, str) and cmd:
        return f"cmd:{cmd}"
    url = entry.get("url")
    if isinstance(url, str) and url:
        return f"url:{url}"
    return None


def import_mavis_aliases(
    target_path: Path | None = None,
    *,
    force: bool = False,
) -> dict:
    """mavis 글로벌 mcp.json 의 *workflow_kit 외* alias 들을 registry entries 로 환원.

    동작:
      1. ``target_path`` 가 없으면 ``mavis_global_path()`` 사용.
      2. 파일 부재 시 ``{"wrote": False, "skipped": True, "imported": [], "skipped_existing": []}``.
      3. ``mcpServers`` 아래 ``MAVIS_PROTECTED_ALIASES`` *제외* 한 alias 각각에
         대해 ``__mavis__/<alias>`` path 로 ``register()`` (idempotent).
      4. 동일 path 가 이미 있으면 ``force=False`` (default) 면 skip.
      5. ``force=True`` 면 ``register()`` 의 last_seen 갱신만 (덮어쓰지 않음 —
         register 자체가 idempotent).

    Returns:
        ``{"wrote": bool, "imported": list[str], "skipped_existing": list[str],
            "skipped_protected": list[str], "registry_path": str,
            "mavis_path": str}``
    """
    actual = Path(target_path) if target_path is not None else mavis_global_path()
    result = {
        "wrote": False,
        "imported": [],
        "skipped_existing": [],
        "skipped_protected": [],
        "registry_path": str(registry_path()),
        "mavis_path": str(actual),
    }
    if not actual.is_file():
        result["skipped"] = True
        return result

    try:
        data = json.loads(actual.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        result["error"] = f"mavis mcp.json broken JSON: {actual}"
        return result
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    if not isinstance(servers, dict):
        return result

    # 기존 registry 의 path 셋을 빠르게 본다.
    existing = {Path(e.path) for e in list_entries()}

    for alias, entry in servers.items():
        if alias in MAVIS_PROTECTED_ALIASES:
            result["skipped_protected"].append(alias)
            continue
        if not isinstance(entry, dict):
            continue
        canon = f"{_MAVIS_PATH_PREFIX}{alias}"
        # idempotency: _normalize 가 resolve() 로 cwd prefix 를 붙이므로 raw 비교.
        if canon in {e.path for e in list_entries()} and not force:
            result["skipped_existing"].append(alias)
            continue
        # register 가 _normalize(resolve) 로 cwd prefix 를 붙이는 걸 우회하기 위해
        # raw canonical string 을 registry 의 path 필드에 직접 적는다. 동결된
        # dataclass 이므로 dataclasses.replace 로 새 entry 를 만들어 save 한다.
        cur = load()
        now = _utcnow_iso()
        replaced = False
        new_entries: list[RegistryEntry] = []
        for e in cur.entries:
            if e.path == canon:
                new_entries.append(
                    RegistryEntry(
                        path=canon,
                        branch=alias,
                        harness="mavis-bridge",
                        endpoint=_mavis_endpoint(entry),
                        registered_at=e.registered_at or now,
                        last_seen_at=now,
                    )
                )
                replaced = True
            else:
                new_entries.append(e)
        if not replaced:
            new_entries.append(
                RegistryEntry(
                    path=canon,
                    branch=alias,
                    harness="mavis-bridge",
                    endpoint=_mavis_endpoint(entry),
                    registered_at=now,
                    last_seen_at=now,
                )
            )
        cur.entries = new_entries
        save(cur)
        result["imported"].append(alias)
    if result["imported"]:
        result["wrote"] = True
    return result


def export_to_mavis(
    new_aliases: list[dict],
    *,
    target_path: Path | None = None,
    force: bool = False,
) -> dict:
    """registry entries 를 mavis 글로벌에 ``mavis:<branch>`` alias 로 emit.

    Args:
        new_aliases: ``[{"branch": str, "command": str|None, "url": str|None,
            "env": dict|None, "description": str|None}]`` — registry 의
            ``list_entries()`` 결과를 가공해서 만들 수 있다.
        target_path: override. None 이면 ``mavis_global_path()``.
        force: 동일 alias 가 이미 있으면 덮어쓰기 (default: skip). builtin 5종 +
            표준 alias 는 *절대* 덮어쓰지 않음 (이 list 는 caller 가 책임).

    Returns:
        ``{"wrote": bool, "added": list[str], "skipped_existing": list[str],
            "skipped_protected": list[str], "mavis_path": str, "backup": str|None}``
    """
    actual = Path(target_path) if target_path is not None else mavis_global_path()
    result = {
        "wrote": False,
        "added": [],
        "skipped_existing": [],
        "skipped_protected": [],
        "mavis_path": str(actual),
        "backup": None,
    }
    if not new_aliases:
        return result

    # load existing (or create new)
    if actual.is_file():
        ts = _utcnow_iso().replace("-", "").replace(":", "").rstrip("Z")
        backup = actual.with_suffix(f".json.bak.{ts}Z")
        try:
            import shutil as _sh
            _sh.copy2(actual, backup)
            result["backup"] = str(backup)
        except OSError as e:
            result["error"] = f"backup failed: {e}"
            return result
        try:
            data = json.loads(actual.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            result["error"] = f"mavis mcp.json broken JSON: {e}"
            return result
        if not isinstance(data, dict):
            result["error"] = "mavis mcp.json top-level not dict"
            return result
        servers = data.get("mcpServers")
        if not isinstance(servers, dict):
            servers = {}
            data["mcpServers"] = servers
    else:
        actual.parent.mkdir(parents=True, exist_ok=True)
        data = {"mcpServers": {}}
        servers = data["mcpServers"]

    for entry in new_aliases:
        if not isinstance(entry, dict):
            continue
        branch = entry.get("branch")
        if not branch or not isinstance(branch, str):
            continue
        alias = f"mavis:{branch}"
        if alias in MAVIS_PROTECTED_ALIASES:
            result["skipped_protected"].append(alias)
            continue
        if alias in servers and not force:
            result["skipped_existing"].append(alias)
            continue
        block: dict[str, object] = {
            "enabled": True,
            "configured": True,
            "description": entry.get("description")
            or f"Exported by workspace_registry from registry entry (branch={branch})",
        }
        if entry.get("command"):
            block["command"] = entry["command"]
            if entry.get("args"):
                block["args"] = list(entry["args"])
        if entry.get("url"):
            block["url"] = entry["url"]
            if entry.get("type"):
                block["type"] = entry["type"]
        if entry.get("env"):
            block["env"] = dict(entry["env"])
        servers[alias] = block
        result["added"].append(alias)

    if not result["added"]:
        return result

    # atomic write
    fd, tmp_name = tempfile.mkstemp(
        prefix=".mcp.", suffix=".tmp", dir=str(actual.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
            fp.write("\n")
        if actual.is_file():
            os.chmod(tmp_name, actual.stat().st_mode)
        else:
            os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, actual)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    result["wrote"] = True
    return result


def sync_mavis(
    target_path: Path | None = None,
    *,
    apply_export: bool = False,
) -> dict:
    """mavis ↔ registry 양방향 동기 (import + export).

    - import 는 registry 가 *사용자 모르게 변하지 않게* default dry-run 처럼 동작
      (단, ``import_mavis_aliases`` 자체는 force=False 가 default 라 skip 이 default).
    - export 는 *default dry-run* (``apply_export=False``) — §5A.3 *부가 정보* 원칙.
      export 를 실제 적용하려면 ``apply_export=True``.

    Args:
        target_path: mavis 글로벌 override.
        apply_export: True 면 ``export_to_mavis`` 가 실제 write. False 면
            ``export_to_mavis(force=False)`` 의 *dry-run preview* 만 (write 0).

    Returns:
        ``{"imported": list, "skipped_existing": list, "export_preview": list,
            "export_applied": bool, "mavis_path": str}``
    """
    imp = import_mavis_aliases(target_path=target_path, force=False)
    # build a list of {branch, command, args, env, description, url, type} from
    # the *current* registry entries. caller (CLI) 가 가공한 형태 그대로 export.
    entries = list_entries()
    new_aliases: list[dict] = []
    for e in entries:
        if not e.branch or e.branch.startswith("__"):
            continue
        env = {}
        # registry entry 의 env 는 직접 없으므로, 표준 env 자동 합성 (있으면).
        new_aliases.append({
            "branch": e.branch,
            "command": None,
            "env": env,
            "description": (
                f"registry export (harness={e.harness or 'unknown'}, host={host_id()})"
            ),
        })
    if apply_export:
        exp = export_to_mavis(new_aliases, target_path=target_path, force=False)
    else:
        # dry-run preview: write 0
        exp = {
            "wrote": False,
            "added": [],
            "skipped_existing": [],
            "skipped_protected": [],
            "preview_only": True,
        }
    return {
        "imported": imp.get("imported", []),
        "skipped_existing": imp.get("skipped_existing", []),
        "skipped_protected": imp.get("skipped_protected", []),
        "export_preview": exp.get("added", []),
        "export_applied": apply_export and exp.get("wrote", False),
        "mavis_path": imp.get("mavis_path", ""),
        "registry_path": imp.get("registry_path", ""),
    }
