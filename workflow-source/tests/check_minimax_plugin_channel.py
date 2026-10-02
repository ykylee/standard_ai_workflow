#!/usr/bin/env python3
"""MiniMax Code 플러그인 채널 정합 (TASK-2026-10-02-main-009).

이 채널이 없던 동안 설치본이 1.14.4 로 밀렸다. drift 는 조용했다 — 세 채널은
자동 갱신되지만 MiniMax Code 의 `local` 마켓플레이스는 디렉터리 스캔이라 갱신
surface 자체가 없었고, 그래서 아무 검사가 red 가 되지 않았다. 이 파일은 그
사이에 사라진 검사 자리를 되돌린다.

case 구성:

  1. **payload drift** — ``plugin/.minimax-plugin/plugin.json`` 이 정본 렌더러
     출력과 일치한다 (다른 채널 manifest 와 같은 계약).
  2. **V1 스펙 정합** — 필수 필드·schemaVersion·SemVer·``name`` 정규식·
     ``category`` 열거·``apps`` 빈 배열·스킬 경로 형태.
  3. **스킬 목록 파생** — manifest 의 ``skills`` 가 :data:`PLUGIN_SKILLS` 에서
     파생되고, 참조 파일이 payload 에 **실제로** 있다. 그리고 ``exampleQueries``
     가 스킬 수와 같다 — 손으로 적은 개수가 stale 해지는 사고를 직접 막는다.
  4. **아이콘 유효성** — payload 루트의 정확한 두 경로가 존재하고 PNG 시그니처를
     갖는다. drift 대조에서 빠진 자리를 여기서 메운다.
  5. **릴리스 ZIP 격리** — ``minimax-code`` ZIP 이 자기 manifest·스킬·아이콘을
     싣고, 다른 채널 manifest 를 싣지 않는다.
  6. **로컬 sync 계약** — 계획이 1.14.4 상태를 drift 로 잡고, 반영하면 in_sync 가
     되고, 되돌리면 원래 상태로 돌아간다. 백업이 마켓플레이스 **밖**에 생긴다.
  7. **그림자 manifest 거부** — 설치 대상에 루트 ``plugin.json`` 이 있으면 지우지
     않고 실패한다 (MiniMax manifest 를 가릴 수 있다).
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit import __version__ as VERSION  # noqa: E402
from workflow_kit.minimax_plugin import (  # noqa: E402
    plan_minimax_sync,
    sync_minimax_plugin,
)
from workflow_kit.plugin_distribution import PLUGIN_HARNESS_SPECS, build_plugin_archives  # noqa: E402
from workflow_kit.plugin_payload import (  # noqa: E402
    CODEX_MANIFEST_RELPATH,
    CLAUDE_CODE_MANIFEST_RELPATH,
    MINIMAX_ICON_DARK_RELPATH,
    MINIMAX_ICON_RELPATH,
    MINIMAX_MANIFEST_RELPATH,
    PAYLOAD_DIRNAME,
    PLUGIN_NAME,
    PLUGIN_SKILLS,
    current_kit_version,
    default_repo_root,
    render_minimax_manifest,
)

PAYLOAD_ROOT = default_repo_root() / PAYLOAD_DIRNAME
MANIFEST_PATH = PAYLOAD_ROOT / MINIMAX_MANIFEST_RELPATH

#: MiniMax Local Plugin V1 이 강제하는 이름 규칙.
NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
CATEGORIES = frozenset(
    {
        "Office",
        "Studio",
        "Design & Sites",
        "Code",
        "Business",
        "Sales",
        "Productivity",
        "Science & Healthcare",
        "Education",
        "Other",
    }
)
REQUIRED_FIELDS = frozenset(
    {
        "schemaVersion",
        "name",
        "version",
        "description",
        "author",
        "icon",
        "category",
        "exampleQueries",
        "apps",
        "mcpServers",
        "skills",
    }
)
KNOWN_FIELDS = REQUIRED_FIELDS | {"displayName", "darkIcon", "hooks", "$schema"}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2). 채널이 셋
#: (정본 렌더러 · 분배 레지스트리 · 로컬 sync) 이고 각 채널이 자기 표면을 가진다 —
#: 그 셋을 한 튜플로 묶는다.
#:
#: `plugin/*` 는 **한 줄**이다. 좁게 적으려고 파일을 나열하면
#: :func:`build_plugin_archives` 가 `rglob` 으로 훑는 payload 트리 전체가 "선언 밖
#: 접근" 이 되고 meta-watch 가 red 로 잡는다 (실측: 파일 6개 나열 → 61건 결손).
#: fnmatch 의 `*` 는 `/` 를 넘으므로 이 한 줄이 payload 전체를 덮고, 아이디어콘
#: 2장도 `plugin/*` 에 이미 들어 있다 — 따로 적으면 "접근 0 인 glob" 경고만 늘어난다.
WATCHES = (
    # 이 검사는 `workflow_kit` 패키지 전체를 import 경로로 끌어들인다 — 버전
    # 파싱(``pyproject.toml``)과 `read_only_registry` 도구 목록이 각각
    # ``__init__`` 을 통해 전 패키지에 닿는다 (실측: 파일 6개 나열 → 미선언
    # 111건). 그래서 모듈 3개를 손으로 나열하지 않고 패키지 하나를 선언한다
    # (``check_deploy_doctor`` 와 같은 결정 — 좁히면 meta-watch 가 red).
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/check_minimax_plugin_channel.py",
    "plugin/*",
)

FAILURES: list[str] = []


def _assert(condition: bool, message: str) -> None:
    if not condition:
        FAILURES.append(message)


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def check_payload_drift() -> None:
    _assert(MANIFEST_PATH.is_file(), f"payload 에 MiniMax manifest 가 없다: {MANIFEST_PATH}")
    if not MANIFEST_PATH.is_file():
        return
    _assert(
        MANIFEST_PATH.read_text(encoding="utf-8") == render_minimax_manifest(),
        "MiniMax manifest 가 정본 렌더러 출력과 다르다 — `python -m workflow_kit.plugin_payload --apply`",
    )


def check_v1_schema() -> None:
    if not MANIFEST_PATH.is_file():
        return
    manifest = _manifest()
    _assert(not (set(manifest) - KNOWN_FIELDS), f"스펙에 없는 필드: {sorted(set(manifest) - KNOWN_FIELDS)}")
    _assert(not (REQUIRED_FIELDS - set(manifest)), f"필수 필드 누락: {sorted(REQUIRED_FIELDS - set(manifest))}")
    _assert(manifest.get("schemaVersion") == 1, f"schemaVersion 은 1 이어야 한다: {manifest.get('schemaVersion')}")
    _assert(bool(SEMVER_RE.match(str(manifest.get("version")))), f"version 이 SemVer 가 아니다: {manifest.get('version')}")
    _assert(bool(NAME_RE.match(str(manifest.get("name")))), f"name 이 V1 규칙에 어긋난다: {manifest.get('name')}")
    _assert(manifest.get("name") == PLUGIN_NAME, "manifest name 과 payload 이름이 다르다")
    _assert(manifest.get("category") in CATEGORIES, f"category 가 열거에 없다: {manifest.get('category')}")
    _assert(manifest.get("apps") == [], f"apps 는 빈 배열이어야 한다: {manifest.get('apps')!r}")
    _assert(isinstance(manifest.get("mcpServers"), list), "mcpServers 는 배열이어야 한다")
    _assert(isinstance(manifest.get("hooks", []), list), "hooks 는 배열이어야 한다")
    _assert(
        bool(manifest.get("mcpServers") or manifest.get("skills") or manifest.get("hooks")),
        "효과 있는 역량(MCP·Skill·Hook)이 하나도 없다",
    )
    queries = manifest.get("exampleQueries") or []
    _assert(bool(queries) and all(str(q).strip() for q in queries), "exampleQueries 가 비었거나 빈 문자열이 있다")
    for rel in manifest.get("skills") or []:
        _assert(
            bool(re.fullmatch(r"skills/[A-Za-z0-9._-]+/SKILL\.md", rel)),
            f"스킬 참조가 V1 경로 형태를 벗어난다: {rel}",
        )


def check_skills_derived() -> None:
    if not MANIFEST_PATH.is_file():
        return
    manifest = _manifest()
    expected = [f"skills/{spec.slug}/SKILL.md" for spec in PLUGIN_SKILLS]
    _assert(
        manifest.get("skills") == expected,
        f"스킬 목록이 PLUGIN_SKILLS 파생과 다르다: {manifest.get('skills')} != {expected}",
    )
    for rel in expected:
        _assert((PAYLOAD_ROOT / rel).is_file(), f"매니페스트가 가리키는 스킬이 payload 에 없다: {rel}")
    queries = manifest.get("exampleQueries") or []
    # 손으로 적은 개수가 stale 해지는 사고는 이 저장소가 두 번 겪었다
    # (PLUGIN_DESCRIPTION 주석 — "Skills (4) 인데 설명은 스킬 3종"). 예시 질의도
    # 스킬과 1:1 이므로 같은 가드를 건다.
    _assert(
        len(queries) == len(PLUGIN_SKILLS),
        f"exampleQueries {len(queries)}개가 스킬 {len(PLUGIN_SKILLS)}개와 다르다 — MINIMAX_EXAMPLE_QUERIES 갱신 필요",
    )


def check_icons() -> None:
    manifest = _manifest() if MANIFEST_PATH.is_file() else {}
    for field, rel in (("icon", MINIMAX_ICON_RELPATH), ("darkIcon", MINIMAX_ICON_DARK_RELPATH)):
        _assert(manifest.get(field) == rel, f"manifest {field} 이 {rel} 을 가리키지 않는다: {manifest.get(field)}")
        path = PAYLOAD_ROOT / rel
        _assert(path.is_file(), f"payload 루트에 {rel} 이 없다 (MiniMax V1 은 {field} 를 필수로 한다)")
        if path.is_file():
            _assert(path.read_bytes()[:8] == PNG_SIGNATURE, f"{rel} 이 PNG 이 아니다")


def check_archive_isolation() -> None:
    _assert("minimax-code" in PLUGIN_HARNESS_SPECS, "minimax-code 채널이 분배 레지스트리에 없다")
    if "minimax-code" not in PLUGIN_HARNESS_SPECS:
        return
    with tempfile.TemporaryDirectory() as tmpdir:
        archives = {path.name: path for path in build_plugin_archives(Path(tmpdir), version=VERSION)}
        archive = next((path for name, path in archives.items() if "minimax-code" in name), None)
        _assert(archive is not None, "minimax-code ZIP 이 생성되지 않았다")
        if archive is None:
            return
        with zipfile.ZipFile(archive) as bundle:
            names = set(bundle.namelist())
            _assert(
                any(name.endswith(f"/{MINIMAX_MANIFEST_RELPATH}") for name in names),
                "MiniMax ZIP 이 자기 manifest 를 싣지 않는다",
            )
            _assert(
                all(any(name.endswith(f"/skills/{spec.slug}/SKILL.md") for name in names) for spec in PLUGIN_SKILLS),
                "MiniMax ZIP 이 스킬 일부를 빠뜨린다",
            )
            for rel in (MINIMAX_ICON_RELPATH, MINIMAX_ICON_DARK_RELPATH):
                _assert(
                    any(name.endswith(f"/{rel}") for name in names),
                    f"MiniMax ZIP 이 필수 아이콘 {rel} 을 싣지 않는다",
                )
            for foreign in (CLAUDE_CODE_MANIFEST_RELPATH, CODEX_MANIFEST_RELPATH, "mcp.json"):
                _assert(
                    not any(name.endswith(f"/{foreign}") for name in names),
                    f"MiniMax ZIP 이 남의 채널 파일 {foreign} 를 싣는다",
                )
            # payload 루트 `plugin.json` 은 MiniMax manifest 를 가릴 수 있다 (렌더러
            # docstring 참조). 판정은 **루트 한 단계**로 좁힌다 — 그냥 `plugin.json`
            # 으로 보면 `.minimax-plugin/plugin.json` 까지 잡아 자기 manifest 를
            # 남의 파일로 오보고한다.
            _assert(
                not any(name.endswith(f"/{PLUGIN_NAME}/plugin.json") for name in names),
                "MiniMax ZIP 이 MiniMax manifest 를 가릴 루트 plugin.json 을 싣는다",
            )


def _stale_plugin_dir(root: Path) -> Path:
    """1.14.4 처럼 오래되고 스킬 하나가 없는 설치본을 만든다 (격리 디렉터리)."""
    plugin_dir = root / "plugins" / PLUGIN_NAME
    (plugin_dir / ".minimax-plugin").mkdir(parents=True)
    (plugin_dir / MINIMAX_ICON_RELPATH).write_bytes(b"")
    (plugin_dir / MINIMAX_ICON_DARK_RELPATH).write_bytes(b"")
    (plugin_dir / "skills" / "session-start").mkdir(parents=True)
    (plugin_dir / "skills" / "session-start" / "SKILL.md").write_text("stale\n", encoding="utf-8")
    (plugin_dir / ".minimax-plugin" / "plugin.json").write_text(
        json.dumps({"version": "1.14.4"}, ensure_ascii=False), encoding="utf-8"
    )
    return plugin_dir


def check_local_sync() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        plugin_dir = _stale_plugin_dir(root)

        plan = plan_minimax_sync(payload_dir=PAYLOAD_ROOT, plugin_dir=plugin_dir)
        _assert(plan["installed_version"] == "1.14.4", f"설치본 버전을 못 읽었다: {plan['installed_version']}")
        _assert(plan["in_sync"] is False, "1.14.4 설치본을 in_sync 로 판정했다")
        planned = {action["relpath"]: action["action"] for action in plan["actions"]}
        _assert(
            planned.get(MINIMAX_MANIFEST_RELPATH) == "update",
            f"매니페스트 갱신을 계획하지 않았다: {planned.get(MINIMAX_MANIFEST_RELPATH)}",
        )
        # 1.14.4 격리본에는 session-start 하나뿐이라 나머지는 create 다. "누락을
        # 잡았다" 의 판정은 unchanged 가 아닌지로 한다 — create/update 를 따로 보면
        # 격리 fixture 를 바꿀 때마다 이 단언이 조용히 vacuous 해진다.
        for spec in PLUGIN_SKILLS:
            if spec.slug == "session-start":
                continue
            _assert(
                planned.get(f"skills/{spec.slug}/SKILL.md") in {"create", "update"},
                f"누락된 스킬 {spec.slug} 을 계획하지 않았다: {planned.get(f'skills/{spec.slug}/SKILL.md')}",
            )
        _assert(plan["actions"], "계획이 비었다")

        dry = sync_minimax_plugin(payload_dir=PAYLOAD_ROOT, plugin_dir=plugin_dir, apply=False)
        _assert(dry["applied"] is False, "dry-run 이 applied 를 보고했다")
        _assert(
            json.loads((plugin_dir / ".minimax-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"] == "1.14.4",
            "dry-run 이 디스크를 고쳤다",
        )

        applied = sync_minimax_plugin(payload_dir=PAYLOAD_ROOT, plugin_dir=plugin_dir, apply=True)
        _assert(applied["applied"] is True, "반영이 failed 했다")
        _assert(applied["in_sync"] is True, "반영 후에도 in_sync 가 아니다")
        _assert(
            json.loads((plugin_dir / ".minimax-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"] == VERSION,
            f"반영 후 버전이 {VERSION} 이 아니다",
        )
        for rel in (MINIMAX_ICON_RELPATH, MINIMAX_ICON_DARK_RELPATH):
            _assert((plugin_dir / rel).read_bytes() == (PAYLOAD_ROOT / rel).read_bytes(), f"아이콘 {rel} 이 다르다")
        _assert(
            not (plugin_dir / "plugin.json").exists(),
            "sync 가 MiniMax manifest 를 가릴 루트 plugin.json 을 심었다",
        )

        backup_dir = Path(applied["backup_dir"] or "")
        _assert(backup_dir.is_dir(), f"백업이 없다: {backup_dir}")
        if backup_dir.is_dir():
            # 백업이 마켓플레이스 안이면 스캔이 백업본을 플러그인으로 등록한다.
            _assert(
                plugin_dir.resolve() not in backup_dir.resolve().parents,
                f"백업이 마켓플레이스 안에 있다: {backup_dir}",
            )
            restored = root / "restored"
            shutil.copytree(backup_dir, restored)
            _assert(
                json.loads((restored / ".minimax-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"] == "1.14.4",
                "백업에서 되돌린 상태가 1.14.4 이 아니다",
            )

        # 재실행은 멱등 — 두 번째 반영이 no-op 이어야 한다.
        again = sync_minimax_plugin(payload_dir=PAYLOAD_ROOT, plugin_dir=plugin_dir, apply=True, backup=False)
        _assert(
            all(action["action"] == "unchanged" for action in again["actions"]),
            "재실행이 멱등하지 않다",
        )


def check_shadow_manifest_refused() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        plugin_dir = _stale_plugin_dir(root)
        (plugin_dir / "plugin.json").write_text('{"name": "shadow"}\n', encoding="utf-8")
        try:
            plan_minimax_sync(payload_dir=PAYLOAD_ROOT, plugin_dir=plugin_dir)
        except RuntimeError as error:
            _assert("plugin.json" in str(error), f"거부 사유가 그림자 파일을 지목하지 않는다: {error}")
        else:
            FAILURES.append("루트 plugin.json 이 있어도 sync 가 거부하지 않았다")
        _assert((plugin_dir / "plugin.json").is_file(), "sync 가 사용자의 루트 plugin.json 을 지웠다")


def _missing_payload_assets() -> list[str]:
    """payload 에 **있어야 하는데 없는** 파일 — 있으면 아래 case 들이 그 경로를 열어
    ``FileNotFoundError`` 로 죽는다.

    죽으면 안 되는 이유가 두 가지다. 하나는 진단이다 — traceback 은 어느 채널이
    무너졌는지 안 말한다. 다른 하나는 **뒤 case 가 통째로 건너뛰어진다**는 것:
    아이콘 하나가 없으면 ``check_shadow_manifest_refused`` 까지 실행되지 않아
    그림자 manifest 거부 계약이 검증되지 않는다. 조용한 미검증 금지 원칙상
    필수 자산이 없으면 그 사실 하나를 명시적으로 보고하고 여기서 끝낸다.
    """
    required = [
        MINIMAX_MANIFEST_RELPATH,
        MINIMAX_ICON_RELPATH,
        MINIMAX_ICON_DARK_RELPATH,
        *(f"skills/{spec.slug}/SKILL.md" for spec in PLUGIN_SKILLS),
    ]
    return [rel for rel in required if not (PAYLOAD_ROOT / rel).is_file()]


def main() -> int:
    missing = _missing_payload_assets()
    if missing:
        for rel in missing:
            FAILURES.append(f"payload 에 필수 파일이 없다: {rel}")
        print(f"FAIL: MiniMax 채널 payload 가 불완전하다 — {len(missing)}개 결손 (아래 case 미실행)")
        for failure in FAILURES:
            print(f"  FAIL: {failure}")
        return 1

    check_payload_drift()
    check_v1_schema()
    check_skills_derived()
    check_icons()
    check_archive_isolation()
    check_local_sync()
    check_shadow_manifest_refused()

    if FAILURES:
        for failure in FAILURES:
            print(f"  FAIL: {failure}")
        print(f"FAIL: {len(FAILURES)} case(s) failed: {FAILURES}")
        return 1
    print(
        f"OK: MiniMax Code 채널 정합 (version={current_kit_version()} · "
        f"skills={len(PLUGIN_SKILLS)} · manifest={MINIMAX_MANIFEST_RELPATH})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
