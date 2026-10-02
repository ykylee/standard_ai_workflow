"""MiniMax Code 로컬 플러그인 설치본을 payload 정본에서 갱신한다.

## 왜 필요한가

MiniMax Code 의 `local` 마켓플레이스는 ``~/.minimax/plugins/`` **디렉터리 자체**를
스캔하고, 각 하위 디렉터리의 ``.minimax-plugin/plugin.json`` 을 읽는다. 즉 소비
surface 가 원격 레지스트리가 아니라 **로컬 디렉터리**다. 그래서

- 설치 명령이 ``mcode plugin add <name>@local`` 로 원격에서 당겨오는 경로가 없다 —
  디렉터리를 직접 써야 한다;
- 갱신 명령도 없다. Claude Code 는 ``plugin update`` 가 있고 Codex 는
  ``plugin add`` 가 캐시를 다시 복사하지만 (``docs/INSTALLATION_AND_USAGE.md`` §7.0.1
  채널 표), MiniMax Code 에는 둘 다 없다.

그 결과가 실제로 벌어진 것이 **설치본이 1.14.4 로 밀린 것**이다. 1.15 ~ 1.19 의
스킬 본문 변경 — 무엇보다 `wk` 실행 파일에서 `python -m workflow_kit` 으로의 전환
(TASK-2026-10-02-main-006 · 007) — 이 설치본에 반영되지 않았다. 이 모듈이 그
갱신을 한 명령으로 만든다.

## 무엇을 복사하는가

복사 목록은 :data:`workflow_kit.plugin_distribution.PLUGIN_HARNESS_SPECS` 의
``minimax-code`` 항목 ``include_prefixes`` **하나**에서 온다. 릴리스 ZIP 과 로컬
sync 가 같은 정본을 공유하게 하려는 의도다 — 두 대상이 갈라지면 어느 쪽이 옛
사본인지는 아무도 모른다.

특히 **payload 루트의 ``plugin.json`` 은 복사하지 않는다.** MiniMax V1 manifest
선택 규칙은 "유효한 Agent Plugins V1 root ``plugin.json`` 이 MiniMax manifest 를
가린다"이고, payload 루트의 3필드 manifest 가 유효한지는 이 저장소가 아직 원문으로
확인하지 못했다 (모름 ≠ 안전). 가려지면 플러그인은 조용히 MiniMax manifest 로
로드되지 않는다.

## 안전장치

- 기본이 **dry-run** 이다. 실제 반영은 ``--apply`` 를 줘야 한다.
- 반영 전에 기존 설치본을 타임스탬프 디렉터리로 **백업**한다. 되돌리기는 그
  디렉터리를 다시 복사하면 된다.
- 설치 대상에 **루트 ``plugin.json`` 이 있으면 실패**한다 (가린다면 모르는 사이
  조용히 MiniMax manifest 가 꺼진다). 사용자가 직접 넣은 파일을 임의로 지우지
  않는다 — 알리고 멈춘다.
- symlink 를 따라 쓰지 않는다.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow_kit.plugin_distribution import PLUGIN_HARNESS_SPECS
from workflow_kit.plugin_payload import (
    MINIMAX_MANIFEST_RELPATH,
    PAYLOAD_DIRNAME,
    PLUGIN_NAME,
    _is_hand_maintained,
    current_kit_version,
    default_repo_root,
)

#: MiniMax Code 데스크톱 데이터 디렉터리. 이 저장소의 MiniMax 채널 정본 경로다 —
#: ``workflow_kit.bootstrap_lib`` 의 ``DEFAULT_MAVIS_GLOBAL_MCP_PATH`` 가 같은
#: ``~/.minimax`` 을 단정하고 ``check_bootstrap_mavis_global_mcp.py`` 가 그 값을
#: 강제한다. 여기서 다른 값을 쓰면 두 경로가 갈라진다.
DEFAULT_MINIMAX_DATA_DIRNAME = ".minimax"


def minimax_plugin_root(data_dir: Path | None = None) -> Path:
    """MiniMax Code 로컬 마켓플레이스 디렉터리 (``<data>/plugins``)."""
    base = data_dir if data_dir is not None else Path.home() / DEFAULT_MINIMAX_DATA_DIRNAME
    return base / "plugins"


def default_plugin_dir(data_dir: Path | None = None) -> Path:
    """설치 대상 디렉터리 — 디렉터리 이름이 플러그인 ``name`` 과 같아야 한다."""
    return minimax_plugin_root(data_dir) / PLUGIN_NAME


def default_payload_dir(repo_root: Path | None = None) -> Path:
    """복사 원본 — 저장소 ``plugin/``."""
    return (repo_root or default_repo_root()) / PAYLOAD_DIRNAME


def _selected_files(payload_dir: Path, spec_prefixes: tuple[str, ...]) -> list[tuple[str, Path]]:
    """채널 접두 목록에 걸리는 payload 파일을 ``(상대 경로, 실제 경로)`` 로 돌려준다."""
    selected: list[tuple[str, Path]] = []
    for source in sorted(payload_dir.rglob("*")):
        if not source.is_file() or source.is_symlink():
            continue
        rel = source.relative_to(payload_dir).as_posix()
        if any(rel == prefix or rel.startswith(prefix) for prefix in spec_prefixes):
            selected.append((rel, source))
    return selected


def _shadowing_manifest(plugin_dir: Path) -> Path | None:
    """MiniMax manifest 를 가릴 수 있는 루트 ``plugin.json`` 의 경로 (없으면 ``None``)."""
    root_manifest = plugin_dir / "plugin.json"
    if root_manifest.is_file() and not _is_hand_maintained("plugin.json"):
        return root_manifest
    return None


def plan_minimax_sync(
    *,
    payload_dir: Path | None = None,
    plugin_dir: Path | None = None,
) -> dict[str, Any]:
    """설치본을 payload 정본에 맞춘다 — **디스크를 건드리지 않고** planned 결과만.

    반환 ``actions`` 는 ``{"action": ..., "relpath": ...}`` 목록이다. ``action`` 은
    ``create`` / ``update`` / ``unchanged`` 다. 제거는 하지 않는다 — payload 에 없는
    파일을 지우는 판단은 소유자의 몫이다 (``extra`` 로 보고만 한다).
    """
    source = payload_dir or default_payload_dir()
    target = plugin_dir or default_plugin_dir()
    spec = PLUGIN_HARNESS_SPECS["minimax-code"]

    if not (source / MINIMAX_MANIFEST_RELPATH).is_file():
        raise FileNotFoundError(
            f"payload 에 MiniMax manifest 가 없다: {source / MINIMAX_MANIFEST_RELPATH} "
            "— `python -m workflow_kit.plugin_payload --apply` 로 먼저 생성한다"
        )

    shadow = _shadowing_manifest(target)
    if shadow is not None:
        raise RuntimeError(
            f"설치 대상에 루트 plugin.json 이 있다: {shadow} — MiniMax manifest 를 "
            "가릴 수 있다. 사용자가 넣은 파일이라 임의로 지우지 않는다. 직접 옮기거나 지운 뒤 다시 실행한다"
        )

    actions: list[dict[str, str]] = []
    expected: set[str] = set()
    for rel, path in _selected_files(source, spec.include_prefixes):
        expected.add(rel)
        destination = target / rel
        if not destination.is_file():
            actions.append({"action": "create", "relpath": rel})
        elif destination.read_bytes() != path.read_bytes():
            actions.append({"action": "update", "relpath": rel})
        else:
            actions.append({"action": "unchanged", "relpath": rel})

    extra: list[str] = []
    if target.is_dir():
        for found in sorted(target.rglob("*")):
            if not found.is_file():
                continue
            rel = found.relative_to(target).as_posix()
            if rel not in expected:
                extra.append(rel)

    manifest_version: str | None = None
    manifest_path = target / MINIMAX_MANIFEST_RELPATH
    if manifest_path.is_file():
        try:
            manifest_version = str(json.loads(manifest_path.read_text(encoding="utf-8")).get("version"))
        except (OSError, ValueError, UnicodeDecodeError):
            manifest_version = None

    return {
        "payload_dir": str(source),
        "plugin_dir": str(target),
        "kit_version": current_kit_version(),
        "installed_version": manifest_version,
        "in_sync": manifest_version == current_kit_version() and all(
            action["action"] == "unchanged" for action in actions
        ),
        "actions": actions,
        "extra": extra,
    }


def sync_minimax_plugin(
    *,
    payload_dir: Path | None = None,
    plugin_dir: Path | None = None,
    apply: bool = False,
    backup: bool = True,
) -> dict[str, Any]:
    """설치본을 갱신한다. 기본은 dry-run — ``apply=True`` 로만 디스크를 쓴다.

    되돌리기: 반환값의 ``backup_dir`` 이 ``plugin_dir`` 을 통째로 받은 디렉터리다.
    그 안의 내용을 다시 ``plugin_dir`` 로 복사하면 이전 상태로 돌아간다.
    """
    plan = plan_minimax_sync(payload_dir=payload_dir, plugin_dir=plugin_dir)
    if not apply:
        return {**plan, "applied": False, "backup_dir": None}

    source = Path(plan["payload_dir"])
    target = Path(plan["plugin_dir"])
    spec = PLUGIN_HARNESS_SPECS["minimax-code"]

    backup_dir: Path | None = None
    if backup and target.is_dir():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        # 백업은 마켓플레이스 디렉터리 **밖**에 둔다. 안쪽이면 `local` 마켓플레이스가
        # 디렉터리를 스캔해 백업본을 플러그인으로 등록한다.
        backup_dir = target.parent.parent / "plugin-backups" / f"{PLUGIN_NAME}-{stamp}"
        if backup_dir.exists():
            raise FileExistsError(f"백업 경로가 이미 있다: {backup_dir}")
        backup_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(target, backup_dir, symlinks=False)

    written: list[str] = []
    for rel, path in _selected_files(source, spec.include_prefixes):
        destination = target / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        written.append(rel)

    result = plan_minimax_sync(payload_dir=source, plugin_dir=target)
    return {**result, "applied": True, "backup_dir": str(backup_dir) if backup_dir else None, "written": written}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="MiniMax Code 로컬 플러그인 설치본을 payload 정본에서 갱신한다.",
    )
    parser.add_argument("--apply", action="store_true", help="실제로 쓴다 (기본은 dry-run)")
    parser.add_argument("--no-backup", action="store_true", help="기존 설치본 백업을 건너뛴다")
    parser.add_argument("--payload-dir", type=Path, default=None, help="복사 원본 (기본: 저장소 plugin/)")
    parser.add_argument("--plugin-dir", type=Path, default=None, help="설치 대상 (기본: ~/.minimax/plugins/<name>)")
    parser.add_argument("--json", action="store_true", help="JSON 으로만 출력한다")
    args = parser.parse_args(argv)

    result = sync_minimax_plugin(
        payload_dir=args.payload_dir,
        plugin_dir=args.plugin_dir,
        apply=args.apply,
        backup=not args.no_backup,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"payload  : {result['payload_dir']}")
    print(f"설치 대상: {result['plugin_dir']}")
    print(f"kit      : {result['kit_version']}  ·  설치본: {result['installed_version'] or '없음'}")
    for action in result["actions"]:
        if action["action"] == "unchanged":
            continue
        print(f"  {action['action']:9} {action['relpath']}")
    unchanged = sum(1 for action in result["actions"] if action["action"] == "unchanged")
    print(f"  ({unchanged}개 이미 일치)")
    for rel in result["extra"]:
        print(f"  extra    {rel} (지우지 않음 — 소유자 판단)")
    if not result["applied"]:
        print("DRY-RUN: `--apply` 로 실제 반영한다")
        return 0
    print(f"APPLIED: {len(result['written'])}개 파일 기록")
    if result["backup_dir"]:
        print(f"백업    : {result['backup_dir']}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    from workflow_kit.common.stdio import force_utf8_stdio

    force_utf8_stdio()
    raise SystemExit(main())
