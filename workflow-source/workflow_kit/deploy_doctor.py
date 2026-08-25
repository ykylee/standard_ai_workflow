"""`wk doctor` — 배포 **post-apply 탐침** (컨셉 §2 의 1탐침, §7 gap 1).

## 왜 필요한가

지금까지 배포의 검증은 **"설치 명령이 성공했다"** 가 전부였다. 출력을 보는 도구가
없었다. 그래서 아래가 전부 조용히 성립했다 (전부 이 저장소에서 실제로 밟았다):

- 버전 문자열은 `1.2.0` 으로 같은데 **페이로드 내용만 낡은** 플러그인
  (2026-08-16 실측 — Codex 채널. 버전 비교로는 안 걸린다).
- 설치 선언이 사는 자리(`~/.claude/settings.json`)를 외부 도구가 재작성해
  **선언이 소실**된 상태 (실측 1회).
- 글로벌과 프로젝트에 **둘 다** 깔려 서로 다른 버전이 로드되는 상태 (§5.3).
- 개발 의존성이 빠진 인터프리터로 검사를 돌려 **의존성 부재를 코드 결함으로**
  읽은 상태 (main-019, 그리고 2026-08-16 에 또 한 번).

## 계약

- **report-only.** 이 모듈은 **아무것도 쓰지 않는다.** 양쪽 기설치는 오류가 아니라
  상태이고, 어느 쪽도 임의로 지우지 않는다 (§5.2). 제거는 사용자 결정이다.
- **rc 는 기본 0.** 발견은 보고이지 실패가 아니다. `--strict` 를 준 경우에만
  발견이 rc 1 이 된다 — CI 에 걸고 싶은 쪽이 명시적으로 고른다.
- **`project_root` / `home` 은 주입 인자다.** 실 홈을 읽는 탐침은 fixture 로
  검증할 수 없다 — 검사가 실제 사용자 홈을 건드리게 되기 때문이다.

## 이름 주의

:mod:`workflow_kit.cli.doctor` 는 **다른 물건**이다 (7종 baseline 평가). 이 모듈은
*배포 산출물*의 설치 현황을 본다. 둘을 섞지 않는다.

Cross-ref: `core/workflow_deployment_idempotency.md` §2 · §5 · §7,
`docs/INSTALLATION_AND_USAGE.md` §7.0.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import hashlib
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from workflow_kit.bootstrap_lib.harnesses import HARNESS_SPECS
from workflow_kit.common.python_launcher import python_launcher
from workflow_kit.upgrade_diff import compare_marker, parse_version_marker, read_kit_version

__all__ = [
    "GLOBAL_DECLARATION_HOMES",
    "GlobalDeclarationHome",
    "CHANNEL_PREREQUISITES",
    "ChannelPrerequisite",
    "PLUGIN_INSTALL_CACHES",
    "PluginInstallCache",
    "HARNESS_CLI_COMMANDS",
    "probe",
    "main",
]


@dataclass(frozen=True)
class GlobalDeclarationHome:
    """하네스별 **설치 선언의 거주지** (컨셉 §5.4).

    선언이 어디 사는지를 기록해 두지 않으면, 그 자리를 재작성하는 외부 도구가
    선언을 지웠을 때 *무엇이 사라졌는지*조차 알 수 없다 — 실측 1회.
    """

    harness: str
    relpath: str
    """홈 기준 상대 경로."""

    probe_keys: tuple[str, ...] = ()
    """이 파일 안에서 kit 설치를 가리키는 표식 (문자열 포함 검사)."""


#: 글로벌 선언 거주지 **정본**. 새 하네스의 글로벌 채널을 지원하면 여기 한 줄을
#: 더한다 — 손 목록을 따로 만들지 않는다 (컨셉 §2 선언 계약).
GLOBAL_DECLARATION_HOMES: tuple[GlobalDeclarationHome, ...] = (
    GlobalDeclarationHome(
        harness="claude-code",
        relpath=".claude/settings.json",
        probe_keys=("standard-ai-workflow",),
    ),
    GlobalDeclarationHome(
        harness="codex",
        relpath=".codex/config.toml",
        probe_keys=("standard-ai-workflow",),
    ),
    GlobalDeclarationHome(
        harness="gemini-cli",
        relpath=".gemini/settings.json",
        probe_keys=("standard-ai-workflow", "standardAiWorkflow"),
    ),
    GlobalDeclarationHome(
        harness="grok-build",
        relpath=".grok/config.toml",
        probe_keys=("standard-ai-workflow", "standardAiWorkflow"),
    ),
    GlobalDeclarationHome(
        harness="mavis",
        relpath=".minimax/mcp/mcp.json",
        probe_keys=("standardAiWorkflow", "standard-ai-workflow"),
    ),
    GlobalDeclarationHome(
        harness="opencode",
        relpath=".config/opencode/opencode.json",
        probe_keys=("standard-ai-workflow", "standardAiWorkflow"),
    ),
)


@dataclass(frozen=True)
class PluginInstallCache:
    """플러그인 채널이 **페이로드 사본을 두는 자리** (컨셉 §7 gap 3).

    마커 비교로는 "버전이 같고 내용만 낡은" 상태를 원리적으로 못 잡는다. 잡으려면
    사본이 어디 있는지 알아야 하고, 그 자리는 채널마다 다르다. 경로는 2026-08-18
    이 호스트 실측이고 `docs/INSTALLATION_AND_USAGE.md` §7.0.2 와 같은 출처다.
    """

    harness: str
    glob: str
    """홈 기준 glob. 매치 결과가 payload 루트다."""

    ignored: tuple[str, ...] = ()
    """채널이 자기 용도로 넣는 파일 — 드리프트가 아니다."""


#: 페이로드 사본의 거주지 **정본**. 사본을 두지 않는 채널은 여기 없다:
#: pi-dev 는 `~/.pi/agent/settings.json` 의 `packages[]` **경로 참조**라 사본이
#: 없어 내용 드리프트가 성립하지 않고, gemini-cli 는 이 호스트에 CLI 가 없어
#: **미실측**이다 (§7.0.2 표와 같은 상태).
PLUGIN_INSTALL_CACHES: tuple[PluginInstallCache, ...] = (
    PluginInstallCache(
        harness="claude-code",
        glob=".claude/plugins/cache/*/standard-ai-workflow/*",
        # `.in_use` 는 클라이언트가 쓰는 사용 표식이다.
        ignored=(".in_use",),
    ),
    PluginInstallCache(
        harness="codex",
        glob=".codex/plugins/cache/*/standard-ai-workflow/*",
    ),
    PluginInstallCache(
        harness="grok-build",
        glob=".grok/installed-plugins/*standard-ai-workflow*",
    ),
)

#: 채널을 **실행하는 프로세스**의 `ps comm` 이름. `runtime_load` 절이 "지금 돌고
#: 있는 호스트가 이 설치를 봤는가" 를 판정할 때 쓴다. 사본을 두는 채널
#: (:data:`PLUGIN_INSTALL_CACHES`) 과 1:1 로 대응한다 — 사본이 없으면 설치 시각이
#: 없고, 설치 시각이 없으면 이 판정이 성립하지 않는다.
HARNESS_CLI_COMMANDS: dict[str, tuple[str, ...]] = {
    "claude-code": ("claude",),
    "codex": ("codex",),
    "grok-build": ("grok",),
}

#: 어느 채널에서든 사본 안에 있어도 드리프트로 세지 않는 것들.
_UNIVERSAL_IGNORED = (".git", "__pycache__", ".DS_Store")


@dataclass(frozen=True)
class ChannelPrerequisite:
    """설치 **전에** 성립해야 하는 것 (컨셉 §7 gap 4).

    두 종류를 **구분해서** 담는다. 측정할 수 있는 것(실행 파일 존재)과 측정할 수
    없는 것(네트워크 도달성, 내려받은 ZIP)은 성질이 다르고, 섞으면 탐침이
    "모름" 을 "괜찮음" 으로 보고하게 된다 — 이 저장소가 이미 규칙으로 삼은
    *모름 ≠ 안전* 이다.
    """

    channel: str
    executables: tuple[str, ...] = ()
    """`shutil.which` 로 **측정 가능한** 전제."""

    declared: tuple[str, ...] = ()
    """측정하지 않고 **선언만** 하는 전제 (네트워크 등). 탐침은 이것을 통과로 세지 않는다."""

    note: str = ""

    launcher_adaptive: bool = False
    """True 면 ``executables`` 의 ``"python3"`` 를 프로브 시점에
    :func:`workflow_kit.common.python_launcher.python_launcher` 로 해석한다
    (win32: ``python``). **bootstrap 채널만** 켠다 — emit 이 같은 정본으로
    플랫폼을 따르기 때문이다 (main-017). 플러그인 채널은 켜지 않는다: payload 가
    ``python3`` 리터럴을 체크인하므로 (해시 고정, POSIX 관례) 그쪽 전제는 문자
    그대로 ``python3`` 이고, win32 로 완화하면 payload 가 spawn 못 하는 상태를
    preflight 가 green 으로 보고하는 거짓 안심이 된다."""


#: 모든 플러그인 채널이 공유하는 전제. 스킬이 지시하는 메모리 갱신 명령은 `wk` 로
#: 돌고, read-only MCP 서버는 `python3 -m workflow_kit.server…` 로 뜬다 — 둘 중
#: 하나가 없으면 설치는 성공해도 **기능이 없는 상태**가 된다.
#:
#: `python3` 는 win32 에서도 **리터럴 그대로** 잰다 (launcher_adaptive ❌):
#: 플러그인 payload 의 mcp.json 이 `python3` 를 체크인하므로 (platform="posix"
#: 고정 — 해시 안정), 이 채널들이 실제로 spawn 하는 이름이 그것이다. 전제를
#: 플랫폼으로 완화하면 payload 가 못 뜨는 호스트를 green 으로 보고하게 된다.
_PLUGIN_COMMON = ("wk", "python3")

#: 채널별 설치 전제 **정본**. `docs/INSTALLATION_AND_USAGE.md` §7.0.0 표는 여기서
#: 파생되고, `check_installation_usage` 가 복제를 검출한다 (컨셉 §2 선언 계약).
CHANNEL_PREREQUISITES: tuple[ChannelPrerequisite, ...] = (
    ChannelPrerequisite(
        channel="claude-code",
        executables=("claude", *_PLUGIN_COMMON),
        declared=("GitHub marketplace 도달 (네트워크)",),
    ),
    ChannelPrerequisite(
        channel="codex",
        executables=("codex", "unzip", *_PLUGIN_COMMON),
        declared=("GitHub Release 의 Codex ZIP 을 미리 내려받아 둘 것",),
        note="marketplace 가 로컬 디렉터리라 네트워크는 ZIP 내려받을 때만 필요하다",
    ),
    ChannelPrerequisite(
        channel="gemini-cli",
        executables=("gemini", "git", *_PLUGIN_COMMON),
        declared=("저장소 클론 (확장 루트가 `plugin/` 이라 로컬 경로 설치)",),
    ),
    ChannelPrerequisite(
        channel="grok-build",
        executables=("grok", *_PLUGIN_COMMON),
        declared=("GitHub marketplace 도달 (네트워크)", "`--trust` 없이는 MCP·훅이 비활성"),
    ),
    ChannelPrerequisite(
        channel="pi-dev",
        executables=("pi", *_PLUGIN_COMMON),
        declared=("로컬 경로 또는 git 태그 지정",),
        note="경로 참조 설치라 사본이 없다",
    ),
    ChannelPrerequisite(
        channel="bootstrap",
        executables=("python3",),
        declared=("PEP 668 인터프리터면 venv 필요 (§7.1)",),
        note="플러그인 미지원 하네스·오프라인 경로. `wk` 는 이 채널이 설치한다",
        launcher_adaptive=True,
    ),
)


# ---------------------------------------------------------------------------
# environment — 환경 전제 (컨셉 §7 gap 4 의 pre-flight 절)
# ---------------------------------------------------------------------------


def _pip_absence_verdict(prefix: Path, executable: str) -> tuple[str, str | None]:
    """venv 에 pip 이 없을 때의 판정 — (판정 라벨, finding 문구 또는 None).

    잰 단위가 틀리면 처방이 헛돈다 (2026-08-24 실측, main-009): 이 탐침은 pip 을
    **자기 인터프리터**에서 import 하는데, `wk` 가 `uv tool install` 로 깔려
    있으면 그 인터프리터는 개발 `.venv` 가 아니라 wk 의 도구 venv 다. uv tool
    venv 는 설계상 pip 없이 돌고 루트의 `uv-receipt.toml` 로 자신을 선언한다 —
    그 부재는 결함이 아니므로 finding 을 내지 않는다 (추측이 아니라 선언을
    읽는다). 판정 라벨은 payload 에 남아, 안 낸 이유가 조용히 사라지지 않는다.

    finding 을 낼 때는 잰 인터프리터를 명시한다 — 독자가 ensurepip 을 엉뚱한
    venv 에 적용하지 않도록 (실측: 처방이 pip 이 이미 있는 저장소 `.venv` 를
    향해 헛돌았다).
    """
    if (prefix / "uv-receipt.toml").exists():
        return ("by_design_uv_tool", None)
    return (
        "defect",
        f"venv 에 pip 이 없다 (잰 인터프리터: {executable}) — "
        "`python3 -m ensurepip --upgrade` 한 번으로 채운다",
    )


def _is_under(path: Path, root: Path) -> bool:
    """``path`` 가 ``root`` 아래인가 — resolve 실패는 False 로 둔다."""
    try:
        path.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return False
    return True


def _kit_resolution_verdict(
    origin: Path | None,
    project_root: Path,
    executable: str,
) -> tuple[str, str | None]:
    """실행 인터프리터가 ``workflow_kit`` 을 어디서 해석했는가 — (판정 라벨, finding).

    '탐침은 잰 단위가 맞아야 한다'의 **4번째 단위 = 해석되는 패키지의 출처**
    (TASK-2026-08-25-main-019). 2026-08-25 실측: PATH 의 전역 도구가 .pth 로
    *다른 체크아웃*의 workflow_kit(v1.1.8-beta)을 해석했고, 성공 코드를 내며
    그 사본의 산출물(legacy 라벨 task 4건 + 백슬래시 state.json)을 이 저장소에
    썼다 — 원복·재등록으로 수습했다. 도구가 조용히 남의 코드를 돌리는 상태는
    운영자에게 **두 경로를 명시해** 도달해야 한다.

    판정:
    - ``project_checkout``: project root 아래 (source checkout / editable 자기
      저장소) — by design.
    - ``interpreter_site_packages``: 실행 인터프리터의 prefix 아래 (wheel /
      uv tool 설치) — by design.
    - ``not_importable``: workflow_kit 자체가 안 잡힘 — ``modules`` 절이 이미
      부재를 말하므로 여기서 finding 을 중복하지 않는다.
    - ``foreign_path``: 둘 다 아님 — **project root 밖의 다른 체크아웃**이
      실행되고 있다. finding 에 잰 인터프리터·해석 출처·project root 를 전부
      명시한다 (처방이 엉뚱한 곳으로 가지 않게, main-009 와 같은 원칙).
    """
    if origin is None:
        return ("not_importable", None)
    if _is_under(origin, project_root):
        return ("project_checkout", None)
    for prefix in {sys.prefix, getattr(sys, "base_prefix", sys.prefix)}:
        if _is_under(origin, Path(prefix)):
            return ("interpreter_site_packages", None)
    return (
        "foreign_path",
        "실행 인터프리터가 workflow_kit 을 project root 밖의 다른 경로에서 해석한다 — "
        f"잰 인터프리터: {executable} · 해석 출처: {origin} · project root: "
        f"{project_root}. 이 상태로 도구를 돌리면 이 저장소가 아니라 그 사본의 "
        "코드가 실행된다 (2026-08-25 실측: 다른 체크아웃 v1.1.8-beta 산출물 오염)",
    )


def _probe_environment(project_root: Path) -> dict[str, Any]:
    """인터프리터·venv·PATH 전제를 본다.

    **의존성 부재를 코드 결함으로 읽는 사고**가 이 저장소에서 두 번 났다. 그
    전제를 여기서 먼저 말해 준다 — 검사 결과를 해석하기 *전에*.
    """
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    stdlib = Path(getattr(sys, "base_prefix", sys.prefix)) / "lib"
    externally_managed = [str(p) for p in stdlib.glob("python3*/EXTERNALLY-MANAGED")]

    findings: list[str] = []
    if not in_venv:
        findings.append(
            "venv 밖의 인터프리터다 — 개발 의존성(mypy/jsonschema/mcp)이 없으면 "
            "검사가 의존성 부재를 코드 결함으로 보고한다"
        )
    if not in_venv and externally_managed:
        findings.append(
            "PEP 668 externally-managed 인터프리터다 — pip install 이 거부된다"
        )

    modules: dict[str, str | None] = {}
    pip_absence: str | None = None
    for name in ("pip", "workflow_kit"):
        try:
            module = __import__(name)
        except Exception:
            modules[name] = None
            if name == "pip" and in_venv:
                pip_absence, pip_finding = _pip_absence_verdict(
                    Path(sys.prefix), sys.executable
                )
                if pip_finding:
                    findings.append(pip_finding)
            continue
        modules[name] = getattr(module, "__file__", None)

    wk_path = shutil.which("wk")
    if wk_path is None:
        findings.append(
            "`wk` 가 PATH 에 없다 — 플러그인 스킬이 지시하는 메모리 갱신 명령이 돌지 않는다 "
            "(docs/INSTALLATION_AND_USAGE.md §3)"
        )

    kit_origin = modules.get("workflow_kit")
    kit_resolution, kit_finding = _kit_resolution_verdict(
        Path(kit_origin) if kit_origin else None, project_root, sys.executable
    )
    if kit_finding:
        findings.append(kit_finding)

    return {
        "python_version": sys.version.split()[0],
        "executable": sys.executable,
        "in_virtualenv": in_venv,
        "externally_managed_markers": externally_managed,
        "modules": modules,
        # pip 부재 시의 판정 (None = pip 존재). by_design_uv_tool 은 finding 을
        # 내지 않은 이유의 기록이다 — 조용한 통과는 근거가 못 된다.
        "pip_absence": pip_absence,
        # workflow_kit 해석 출처의 판정 (main-019). foreign_path 만 finding 이
        # 되지만 by-design 라벨도 payload 에 남긴다 — 조용한 통과 금지.
        "kit_resolution": kit_resolution,
        "wk_on_path": wk_path,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# project_scope — 프로젝트 로컬 산출물
# ---------------------------------------------------------------------------


def _declared_relpaths() -> dict[str, tuple[str, ...]]:
    """`HARNESS_SPECS` 에서 하네스별 산출물 경로를 **읽어** 온다.

    손 목록을 만들지 않는다 — registry 가 정본이고 이 탐침은 파생이다 (§2).
    """
    return {
        name: tuple(spec.entry_files) + tuple(spec.extra_files)
        for name, spec in HARNESS_SPECS.items()
    }


def _file_marker(path: Path) -> str | None:
    try:
        return parse_version_marker(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return None


def _file_fork(path: Path) -> str | None:
    """이 산출물이 **포크됐다고 스스로 선언**하는가 (§3 소유권 4분류)."""
    from workflow_kit.upgrade_diff import parse_fork_declaration  # noqa: PLC0415

    try:
        return parse_fork_declaration(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return None


def _resolve_kit_version(project_root: Path) -> tuple[str | None, str]:
    """비교 기준이 될 kit 버전과 **그 출처**를 함께 돌려준다.

    `ai-workflow/VERSION` 은 bootstrap 채널이 남기는 파일이라, 플러그인 채널로만
    설치한 프로젝트와 소스 저장소 자신에는 **없다**. 그때 기준을 포기하면 드리프트
    절이 통째로 죽는다 — 실제로 이 저장소에서 `CLAUDE.md` 의 마커가 `1.0.0-beta`
    (kit 은 1.2.0) 인데도 아무 말도 못 하는 상태였다. 없으면 **돌고 있는 패키지**
    버전으로 떨어지고, 출처를 출력에 밝힌다.
    """
    from_file = read_kit_version(project_root)
    if from_file is not None:
        return from_file, "ai-workflow/VERSION"
    try:
        from workflow_kit.plugin_payload import current_kit_version

        return current_kit_version(), "running package"
    except Exception:
        return None, "unknown"


def _probe_project_scope(project_root: Path) -> dict[str, Any]:
    """프로젝트에 존재하는 산출물과 그 버전 마커를 본다.

    **존재는 적용이 아니다.** 파일이 있다는 사실만으로 "이 하네스가 적용됐다" 고
    말하면 과보고가 된다 — 실측(2026-08-16): 이 저장소의 `AGENTS.md` 는 다른
    도구가 쓴 파일인데, 그 하나가 codex/grok-build/minimax-code/opencode/pi-dev
    **5개 하네스를 적용됨으로** 만들었다. 그래서 `applied_harnesses` 는 kit 소유
    표식(버전 마커, §3)이 하나라도 있는 하네스만 센다. 마커 없이 존재만 하는
    쪽은 `candidate_harnesses` 로 따로 보고한다 — 공유 진입점(§3 "공유")이 그
    자리에 정당하게 올 수 있으므로 숨기지도 않는다.
    """
    declared = _declared_relpaths()
    kit_version, kit_version_source = _resolve_kit_version(project_root)

    harnesses: dict[str, Any] = {}
    applied: list[str] = []
    candidates: list[str] = []
    for harness, relpaths in sorted(declared.items()):
        present: list[dict[str, Any]] = []
        for rel in relpaths:
            path = project_root / rel
            if not path.is_file():
                continue
            record: dict[str, Any] = {"path": rel, "marker": _file_marker(path)}
            fork_note = _file_fork(path)
            if fork_note is not None:
                record["fork"] = fork_note
            present.append(record)
        if not present:
            continue
        marked = [record for record in present if record["marker"] is not None]
        harnesses[harness] = {
            "files_present": present,
            "files_declared": len(relpaths),
            "files_marked": len(marked),
        }
        (applied if marked else candidates).append(harness)

    return {
        "project_root": str(project_root),
        "kit_version": kit_version,
        "kit_version_source": kit_version_source,
        "applied_harnesses": sorted(applied),
        "candidate_harnesses": sorted(candidates),
        "harnesses": harnesses,
    }


# ---------------------------------------------------------------------------
# global_scope — 사용자 홈의 설치 선언
# ---------------------------------------------------------------------------


def _probe_global_scope(home: Path) -> dict[str, Any]:
    """글로벌 선언 거주지를 **읽기만** 한다 (§5.1 비침투, §5.2 report-only)."""
    homes: list[dict[str, Any]] = []
    declared_harnesses: list[str] = []
    for entry in GLOBAL_DECLARATION_HOMES:
        path = home / entry.relpath
        record: dict[str, Any] = {
            "harness": entry.harness,
            "path": str(Path("~") / entry.relpath),
            "exists": path.is_file(),
            "declares_kit": False,
        }
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                record["unreadable"] = True
            else:
                record["declares_kit"] = any(key in text for key in entry.probe_keys)
        if record["declares_kit"]:
            declared_harnesses.append(entry.harness)
        homes.append(record)

    return {
        "home": str(home),
        "declared_harnesses": sorted(declared_harnesses),
        "homes": homes,
    }


# ---------------------------------------------------------------------------
# drift — 마커 대 kit 버전, 스코프 간 어긋남
# ---------------------------------------------------------------------------


def _probe_drift(project: dict[str, Any], global_scope: dict[str, Any]) -> dict[str, Any]:
    """버전 어긋남을 보고한다 (§5.3, §7 gap 3).

    **마커가 같아도 내용이 낡을 수 있다** — 2026-08-16 에 Codex 플러그인이 정확히
    그 상태였다 (버전 `1.2.0` 동일, 페이로드만 구버전). 마커 비교는 드리프트의
    *일부*만 잡는다는 사실을 출력이 스스로 말해야 한다.
    """
    kit_version = project.get("kit_version")
    stale: list[dict[str, Any]] = []
    unmarked: list[str] = []
    forked: list[dict[str, Any]] = []

    for harness, info in sorted(project.get("harnesses", {}).items()):
        for record in info["files_present"]:
            marker = record["marker"]
            if record.get("fork") is not None:
                # 포크된 진입점은 **낡은 것이 아니라 갈라진 것**이다 (§3 소유권 4분류).
                # 여기에 "재적용 대상" 을 붙이면 그 조언이 파괴적이 된다 — 실측
                # (2026-08-20): 이 저장소의 CLAUDE.md 는 마커가 낡았고, 조언대로
                # 재적용하면 측정으로 얻은 운영 규칙 90여 줄이 TODO placeholder 로
                # 바뀐다. 마커는 그대로 실어 **어느 버전에서 갈라졌는지** 남긴다.
                forked.append(
                    {
                        "harness": harness,
                        "path": record["path"],
                        "forked_from": marker,
                        "kit_version": kit_version,
                        "note": record["fork"],
                    }
                )
                continue
            if marker is None:
                unmarked.append(record["path"])
                continue
            if kit_version is None:
                continue
            if compare_marker(marker, kit_version) < 0:
                stale.append(
                    {
                        "harness": harness,
                        "path": record["path"],
                        "marker": marker,
                        "kit_version": kit_version,
                    }
                )

    both_scopes = sorted(
        set(project.get("applied_harnesses", [])) & set(global_scope.get("declared_harnesses", []))
    )

    findings: list[str] = []
    if stale:
        findings.append(f"kit 버전보다 낡은 마커 {len(stale)}건 — 재적용 대상이다")
    if forked:
        # 발견이 아니라 **선언된 상태**다. 숨기지도 않는다 — 갈라진 시점을 같이 낸다.
        joined = ", ".join(
            f"{item['path']}(v{item['forked_from']} 에서)" for item in forked
        )
        findings.append(
            f"프로젝트가 포크한 진입 파일 {len(forked)}건 — 재적용은 **파괴적**이다: {joined}. "
            "kit 변경을 반영하려면 그 버전과 diff 해 손으로 병합한다"
        )
    if both_scopes:
        findings.append(
            f"글로벌·프로젝트 양쪽 설치 {len(both_scopes)}건 ({', '.join(both_scopes)}) — "
            "오류가 아니라 상태다. 로드는 하네스 우선순위(대개 project 우선)를 따른다"
        )
    return {
        "kit_version": kit_version,
        "stale_markers": stale,
        "forked_files": forked,
        "unmarked_files": unmarked,
        "installed_in_both_scopes": both_scopes,
        "findings": findings,
        "limitation": (
            "마커 비교는 버전이 같고 내용만 낡은 경우를 원리적으로 못 본다 — "
            "그 자리는 `content_drift` 절이 페이로드 해시로 본다 "
            "(TASK-2026-08-18-main-005)"
        ),
    }


# ---------------------------------------------------------------------------
# preflight — 설치 **전에** 성립하는가 (컨셉 §7 gap 4)
# ---------------------------------------------------------------------------


def _probe_preflight() -> dict[str, Any]:
    """채널별로 **설치 전에** 전제가 성립하는지 본다.

    `environment` 절과 다른 물건이다. 그쪽은 *지금 이 인터프리터*가 검사를 돌릴
    만한가를 보고, 여기는 *어느 채널로 설치할 수 있는가*를 본다. gap 4 의 잔여가
    이 자리였다 — 전제가 문서에 흩어져 있고 설치 전에 재는 도구가 없었다.

    **측정한 것과 선언만 한 것을 섞지 않는다.** 네트워크 도달성은 여기서 재지
    않으므로 `installable` 은 "실행 파일 전제는 충족" 이라는 뜻이지 "설치가
    성공한다" 는 뜻이 아니다. 출력이 그 차이를 스스로 말한다.
    """
    channels: list[dict[str, Any]] = []
    for entry in CHANNEL_PREREQUISITES:
        # launcher_adaptive 채널의 "python3" 는 잰 이름을 플랫폼으로 해석한다
        # (win32: "python") — emit 과 같은 정본을 따른다 (main-017). 결과 키는
        # **잰 이름**이다: 무엇을 which 했는지가 곧 판정의 증거다.
        found: dict[str, str | None] = {}
        for name in entry.executables:
            measured = (
                python_launcher()
                if entry.launcher_adaptive and name == "python3"
                else name
            )
            found[measured] = shutil.which(measured)
        missing = sorted(name for name, path in found.items() if path is None)
        record: dict[str, Any] = {
            "channel": entry.channel,
            "executables": found,
            "missing_executables": missing,
            "declared_unmeasured": list(entry.declared),
            "installable": not missing,
        }
        if entry.note:
            record["note"] = entry.note
        channels.append(record)

    ready = [c["channel"] for c in channels if c["installable"]]
    blocked = [c for c in channels if not c["installable"]]
    findings: list[str] = []
    for c in blocked:
        findings.append(
            f"{c['channel']} 채널은 지금 설치할 수 없다 — 없는 실행 파일: "
            f"{', '.join(c['missing_executables'])} "
            "(설치 안내는 docs/INSTALLATION_AND_USAGE.md §7.0.0)"
        )
    return {
        "ready_channels": ready,
        "blocked_channels": [c["channel"] for c in blocked],
        "channels": channels,
        "findings": findings,
        "measurement_note": (
            "실행 파일 존재만 측정한다. 네트워크 도달성·내려받은 아카이브는 "
            "`declared_unmeasured` 로 남긴다 — 모름을 통과로 세지 않는다"
        ),
    }


# ---------------------------------------------------------------------------
# content_drift — 페이로드 해시 비교 (컨셉 §7 gap 3 잔여)
# ---------------------------------------------------------------------------


def _is_pi_static(relpath: str) -> bool:
    """pi.dev 분배 자산인가 — 렌더 대상이 아니라 손으로 유지되는 패키지 메타다."""
    try:
        from workflow_kit.plugin_payload import _is_pi_static as impl  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return False
    return impl(relpath)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_payload() -> tuple[dict[str, str] | None, str | None]:
    """정본 페이로드 ``{상대 경로: 내용}``. 못 만들면 ``(None, 사유)``.

    생성기와 **같은 함수**(:func:`plugin_payload.render_agent_plugin`)를 쓴다 —
    비교 기준을 따로 두면 그 기준 자체가 드리프트한다.
    """
    try:
        from workflow_kit.plugin_payload import render_agent_plugin  # noqa: PLC0415

        return render_agent_plugin(), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def _installed_version(root: Path, manifest_rel: str | None) -> str | None:
    """설치 사본이 스스로 말하는 버전. 매니페스트 → 캐시 디렉터리 이름 순."""
    if manifest_rel:
        manifest = root / manifest_rel
        if manifest.is_file():
            try:
                declared = json.loads(manifest.read_text(encoding="utf-8")).get("version")
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                declared = None
            if isinstance(declared, str) and declared:
                return declared
    return root.name or None


def _channel_expected(harness: str, canonical: dict[str, str]) -> tuple[dict[str, str], str | None]:
    """이 채널이 **실제로 설치하는** 파일만 남긴 정본 + 매니페스트 상대 경로.

    채널마다 담는 것이 다르다 — codex 는 매니페스트·MCP·skills 만 담고, 정본
    payload 20개를 그대로 기대하면 **없음 10건**이 거짓 드리프트가 된다 (2026-08-18
    실측). 목록을 손으로 적지 않고 `PLUGIN_HARNESS_SPECS.include_prefixes` 에서
    파생한다 (컨셉 §2 선언 계약: registry 가 정본, 탐침은 파생).
    """
    try:
        from workflow_kit.plugin_distribution import (  # noqa: PLC0415
            PLUGIN_HARNESS_SPECS,
            _included,
        )
    except Exception:  # noqa: BLE001 - registry 를 못 읽으면 좁히지 않는다
        return canonical, None
    spec = PLUGIN_HARNESS_SPECS.get(harness)
    if spec is None:
        # 등록된 패키지 정의가 없는 채널(grok-build 등)은 payload 전체가 기대치다.
        return canonical, None
    return (
        {rel: body for rel, body in canonical.items() if _included(rel, spec)},
        spec.manifest_relpath,
    )


def _compare_cache(
    root: Path,
    canonical: dict[str, str],
    ignored: tuple[str, ...],
    *,
    full_payload: dict[str, str] | None = None,
) -> dict[str, Any]:
    """설치 사본 하나를 정본과 **내용으로** 대조한다. 쓰지 않는다.

    ``canonical`` 은 이 채널이 담기로 한 것, ``full_payload`` 는 payload 전체다.
    둘을 나누는 이유: claude-code 의 GitHub marketplace 설치는 `plugin/` 을 **통째로**
    복사하므로 채널 계약 밖의 파일이 정상적으로 함께 온다. 그것을 '미등록 파일' 로
    부르면 매 실행 잡음이 10건씩 난다 (2026-08-18 실측).
    """
    skip = set(ignored) | set(_UNIVERSAL_IGNORED)
    known = set(full_payload or canonical)

    def _skipped(rel: str) -> bool:
        return any(part in skip for part in rel.split("/"))

    differs: list[dict[str, str]] = []
    missing: list[str] = []
    for rel, content in sorted(canonical.items()):
        target = root / rel
        if not target.is_file():
            missing.append(rel)
            continue
        try:
            actual = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            differs.append({"path": rel, "expected": _sha256(content), "actual": "unreadable"})
            continue
        if actual != content:
            differs.append({"path": rel, "expected": _sha256(content), "actual": _sha256(actual)})

    extra: list[str] = []
    for found in sorted(root.rglob("*")):
        if not found.is_file():
            continue
        rel = str(found.relative_to(root))
        if rel in known or _skipped(rel) or _is_pi_static(rel):
            continue
        extra.append(rel)

    return {
        "path": str(root),
        "files_compared": len(canonical),
        "differs": differs,
        "missing": missing,
        "extra": extra,
        "in_sync": not (differs or missing),
    }


def _declared_install_roots(home: Path) -> tuple[set[str], str | None]:
    """하네스가 **스스로 말하는** 설치 경로. 없으면 ``(빈 집합, 사유)``.

    claude-code 의 `installed_plugins.json` 은 `installPath` 로 *어느 사본이
    설치본인지* 선언한다. 이것을 읽지 않으면 glob 매치가 전부 동등한 설치로
    보인다 — 그리고 그 순간 갱신이 보고를 **나쁘게** 만든다 (아래).
    """
    path = home / ".claude" / "plugins" / "installed_plugins.json"
    if not path.is_file():
        return set(), "installed_plugins.json 이 없다"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return set(), f"installed_plugins.json 을 읽지 못했다: {type(exc).__name__}"
    roots: set[str] = set()
    for key, entries in (payload.get("plugins") or {}).items():
        if "standard-ai-workflow" not in key:
            continue
        for item in entries if isinstance(entries, list) else []:
            raw = item.get("installPath") if isinstance(item, dict) else None
            if isinstance(raw, str) and raw:
                # 선언된 경로와 glob 이 찾은 경로는 **같은 곳을 다르게 적을 수 있다**
                # (macOS 의 `/var` → `/private/var` 심볼릭 링크가 그렇다). 문자열
                # 하나만 담으면 정상 설치가 '선언에 없는 사본' 으로 뒤집힌다.
                roots.add(str(Path(raw)))
                try:
                    roots.add(str(Path(raw).resolve()))
                except OSError:
                    pass
    if not roots:
        return set(), "installed_plugins.json 에 이 플러그인의 installPath 가 없다"
    return roots, None


def _resolve_install_roots(
    entry: PluginInstallCache, home: Path
) -> list[tuple[Path, bool, str]]:
    """``(사본, 지금 로드되는 것인가, 그 판정의 출처)``.

    **버전을 올리면 옛 디렉터리가 남는다** (2026-08-20 실측: `plugin update` 뒤
    `cache/.../1.2.0` 과 `1.3.0` 이 나란히 있었다). 그 잔재를 설치본과 동등하게
    세면 두 가지가 함께 깨진다 — 아무도 안 읽는 사본이 드리프트로 보고되고
    (게다가 `installed_version` 이 **옛 버전**을 말한다), 사본 개수만큼 같은
    발견이 복제된다. 즉 **갱신에 성공한 직후 보고가 나빠진다.**

    선언이 없는 채널은 glob 매치를 전부 설치로 본다 — 그러나 그 폴백을 조용히
    하지 않는다 (§0 *폴백은 조용히 하지 않는다*). 재지 못한 것을 잰 것처럼
    보이게 하지 않는 것이 이 절의 계약이다.
    """
    declared, why = _declared_install_roots(home) if entry.harness == "claude-code" else (set(), None)
    fallback = (
        f"선언 없음 — glob 매치를 전부 설치로 본다 ({why})"
        if entry.harness == "claude-code"
        else "이 채널은 설치 경로를 선언하지 않는다 — glob 매치를 전부 설치로 본다"
    )
    found: list[tuple[Path, bool, str]] = []
    for root in sorted(home.glob(entry.glob)):
        if not root.is_dir():
            continue
        if declared:
            # 정규화는 **선언 쪽에서** 끝난다 (`_declared_install_roots` 가 raw 와
            # resolve 를 둘 다 담는다). 여기서 다시 resolve 하는 분기는 `probe` 가
            # `home` 을 이미 resolve 하는 한 도달할 수 없고, 도달 불가능한 분기는
            # 검사되지 않은 분기다 — 되주입해도 red 가 안 났다 (2026-08-20 실측).
            found.append((root, str(root) in declared, "installed_plugins.json 의 installPath"))
        else:
            found.append((root, True, fallback))
    return found


def _probe_content_drift(home: Path) -> dict[str, Any]:
    """설치 사본의 **내용**이 정본과 같은가.

    마커 비교(:func:`_probe_drift`)가 원리적으로 못 보는 자리다 — 2026-08-16 에
    Codex 설치본이 버전 문자열은 정본과 같은 `1.2.0` 인데 페이로드만 구버전이었고,
    claude-code 는 그 상태에서 `plugin update` 를 **버전만 보고 거절**했다. 즉
    낡음이 보고되지도, 고쳐지지도 않았다. 그래서 비교 대상을 버전이 아니라
    **내용 해시**로 바꾼다.
    """
    canonical, error = _canonical_payload()
    caches: list[dict[str, Any]] = []
    for entry in PLUGIN_INSTALL_CACHES:
        for root, active, active_source in _resolve_install_roots(entry, home):
            record: dict[str, Any] = {"harness": entry.harness}
            if canonical is None:
                record.update({"path": str(root), "skipped": "정본 페이로드를 만들지 못했다"})
            else:
                expected, manifest_rel = _channel_expected(entry.harness, canonical)
                record.update(
                    _compare_cache(root, expected, entry.ignored, full_payload=canonical)
                )
                record["installed_version"] = _installed_version(root, manifest_rel)
            record["active"] = active
            record["active_source"] = active_source
            caches.append(record)

    # 지금 로드되는 사본만 발견을 낸다. 옛 버전 디렉터리는 **지우지도 숨기지도**
    # 않는다 — `superseded` 로 남겨 사람이 정리할 수 있게 하되, 아무도 안 읽는
    # 사본 때문에 매 실행 거짓 발견이 나지는 않게 한다.
    out_of_sync = [c for c in caches if c.get("in_sync") is False and c.get("active")]
    superseded = [
        {
            "harness": c["harness"],
            "path": c.get("path"),
            "installed_version": c.get("installed_version"),
            "in_sync": c.get("in_sync"),
        }
        for c in caches
        if not c.get("active")
    ]
    findings: list[str] = []
    for c in out_of_sync:
        findings.append(
            f"{c['harness']} 설치 사본의 내용이 정본과 다르다 — "
            f"다름 {len(c['differs'])} / 없음 {len(c['missing'])} "
            f"(설치 버전 {c.get('installed_version') or '알 수 없음'}, kit 과 같아도 내용은 다를 수 있다). "
            "복구는 docs/INSTALLATION_AND_USAGE.md §7.0.2 의 채널별 절차를 따른다"
        )
    return {
        "canonical_files": 0 if canonical is None else len(canonical),
        "canonical_error": error,
        "caches": caches,
        "out_of_sync": [c["harness"] for c in out_of_sync],
        # 선언에 없는 사본 — 갱신 뒤 남은 옛 버전 디렉터리가 여기 온다.
        "superseded": superseded,
        "findings": findings,
        # 사본을 두지 않는 채널은 내용 드리프트가 성립하지 않는다.
        "not_applicable": {
            "pi-dev": "경로 참조라 사본이 없다 — 원본이 곧 설치본이다",
            "gemini-cli": "이 호스트에 CLI 가 없어 미실측 (§7.0.2 와 같은 상태)",
        },
        # 이 절이 재는 것은 **파일이 같은가** 이지 **하네스가 그것을 실제로 노출하는가**
        # 가 아니다. 둘은 갈릴 수 있고 실제로 갈렸다 (2026-08-20 실측):
        # 설치본의 `skills/` 4종이 정본과 in-sync 였고 `claude plugin details` 도
        # `Skills (4)` 로 셌는데, **세션에는 그중 하나도 로드되지 않았다**
        # (`Unknown skill: standard-ai-workflow:doc-sync`).
        #
        # 재지 못하는 것을 통과로 세지 않는다 — `installable` 이 "설치 성공" 이
        # 아니듯, `in_sync` 도 "쓸 수 있음" 이 아니다 (main-019 와 같은 원칙).
        #
        # 이 미측정은 **한 칸 좁아졌다** (2026-08-20, main-009). 위 실측의 원인이
        # 규명됐기 때문이다: 충돌도 파손도 아니라 **호스트 프로세스가 설치보다
        # 먼저 시작했다**. 그 조건은 이제 잴 수 있고 `runtime_load` 절이 잰다.
        # 남는 미측정은 그 뒤의 한 칸 — 재시작이 최신이어도 하네스가 실제로
        # 노출하는지는 **실제 호출**로만 재진다.
        "declared_unmeasured": [
            "하네스가 이 사본을 실제로 세션에 노출하는지 — 파일 일치는 노출의 증거가 아니다 "
            "(2026-08-20 실측: in-sync + 인벤토리 4종인데 세션 로드 0종). "
            "원인 중 **설치보다 먼저 시작한 호스트**는 `runtime_load` 절이 재고, "
            "그 뒤 한 칸(실제 노출)만 여기 남는다",
        ],
    }


# ---------------------------------------------------------------------------
# runtime_load — 지금 돌고 있는 호스트가 이 설치를 봤는가 (main-009)
# ---------------------------------------------------------------------------


def _parse_etime(raw: str) -> float | None:
    """``ps -o etime`` 의 ``[[dd-]hh:]mm:ss`` 를 초로.

    ``lstart`` 를 쓰지 않는 이유: 그쪽은 **로케일로 번역된** 요일·월 이름을 낸다
    (이 호스트 실측: ``2026년 8월 16일 일요일 22시 53분 10초``). 어느 로케일에서도
    같은 모양인 필드는 ``etime`` 뿐이라, 시작 시각을 직접 읽지 않고 지금에서 뺀다.
    """
    text = raw.strip()
    if not text:
        return None
    days = 0
    if "-" in text:
        head, _, text = text.partition("-")
        try:
            days = int(head)
        except ValueError:
            return None
    parts = text.split(":")
    if not 2 <= len(parts) <= 3:
        return None
    try:
        nums = [int(part) for part in parts]
    except ValueError:
        return None
    hours, minutes, seconds = ([0, *nums] if len(nums) == 2 else nums)
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def _running_processes() -> tuple[list[dict[str, Any]], str | None]:
    """``(프로세스 목록, 실패 사유)``. 실패하면 목록은 비고 사유가 남는다."""
    ps_path = shutil.which("ps")
    if ps_path is None:
        return [], "ps 실행 파일이 없다 — 이 플랫폼에서는 실행 중 호스트를 못 센다"
    try:
        completed = subprocess.run(  # noqa: S603
            [ps_path, "-Ao", "pid=,etime=,comm="],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return [], f"ps 호출 실패: {type(exc).__name__}: {exc}"
    if completed.returncode != 0:
        return [], f"ps 가 rc {completed.returncode} 로 끝났다"

    found: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        fields = line.split(None, 2)
        if len(fields) < 3:
            continue
        pid_raw, etime_raw, command = fields
        elapsed = _parse_etime(etime_raw)
        if elapsed is None:
            continue
        try:
            pid = int(pid_raw)
        except ValueError:
            continue
        found.append({"pid": pid, "command": command.strip(), "elapsed_sec": elapsed})
    return found, None


def _iso(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch).astimezone().isoformat(timespec="seconds")


def _declared_install_epoch(home: Path) -> tuple[float | None, str | None]:
    """claude-code 가 **스스로 말하는** 설치/갱신 시각. 없으면 ``(None, 사유)``."""
    path = home / ".claude" / "plugins" / "installed_plugins.json"
    if not path.is_file():
        return None, "installed_plugins.json 이 없다"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"installed_plugins.json 을 읽지 못했다: {type(exc).__name__}"
    stamps: list[float] = []
    for key, entries in (payload.get("plugins") or {}).items():
        if "standard-ai-workflow" not in key:
            continue
        for entry in entries if isinstance(entries, list) else []:
            for field in ("lastUpdated", "installedAt"):
                raw = entry.get(field) if isinstance(entry, dict) else None
                if not isinstance(raw, str) or not raw:
                    continue
                try:
                    stamps.append(datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp())
                except ValueError:
                    continue
    if not stamps:
        return None, "installed_plugins.json 에 이 플러그인의 시각 기록이 없다"
    return max(stamps), None


def _install_epoch(harness: str, root: Path, home: Path) -> tuple[float | None, str]:
    """설치 시각과 **그 값을 어디서 읽었는지**.

    폴백을 조용히 하지 않는다 — 무엇을 정본으로 봤는지 결과에 남기지 않으면
    통과도 실패도 근거가 못 된다.
    """
    if harness == "claude-code":
        declared, _why = _declared_install_epoch(home)
        if declared is not None:
            return declared, "installed_plugins.json"
    try:
        return root.stat().st_mtime, "설치 사본 mtime (선언 기록이 없는 채널의 폴백)"
    except OSError as exc:
        return None, f"읽지 못했다: {type(exc).__name__}"


def _probe_runtime_load(
    home: Path,
    *,
    now: float | None = None,
    processes: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """**설치가 실행 중인 호스트에 실제로 로드됐는가** (2026-08-20, main-009).

    `content_drift` 가 "파일이 같은가" 를 재고 노출 여부를 미측정으로 선언했던
    자리 중 **한 칸을 측정으로 옮긴다**. 실측된 사례는 이렇다: 플러그인이 in-sync
    이고 `claude plugin details` 도 `Skills (4)` 로 셌는데 세션에서 부르면
    `Unknown skill` 이었다. 원인은 충돌도 파손도 아니라 **시간**이었다 — 호스트
    프로세스가 설치보다 35시간 먼저 시작했고, 플러그인은 프로세스 시작 때 로드된다.

    이것이 조용한 이유는 **단위 착시**다. 대화를 새로 열면(`/clear`) "새 세션" 이
    되지만 프로세스는 그대로다. 그래서 이 절은 세션이 아니라 **프로세스**를 잰다.
    """
    now_epoch = time.time() if now is None else now
    if processes is None:
        listed, list_error = _running_processes()
    else:
        listed, list_error = list(processes), None

    channels: list[dict[str, Any]] = []
    findings: list[str] = []
    skipped_superseded = 0
    for entry in PLUGIN_INSTALL_CACHES:
        commands = HARNESS_CLI_COMMANDS.get(entry.harness, ())
        for root, active, _active_source in _resolve_install_roots(entry, home):
            if not active:
                # 옛 버전 디렉터리마다 같은 발견을 복제하지 않는다. 설치 시각은
                # 플러그인 단위로 선언되므로 잔재까지 돌면 **글자까지 같은**
                # 발견이 사본 개수만큼 나온다 (2026-08-20 실측).
                skipped_superseded += 1
                continue
            epoch, source = _install_epoch(entry.harness, root, home)
            stale: list[dict[str, Any]] = []
            fresh: list[dict[str, Any]] = []
            for proc in listed:
                if Path(str(proc.get("command", ""))).name not in commands:
                    continue
                started = now_epoch - float(proc.get("elapsed_sec") or 0)
                record = {
                    "pid": proc.get("pid"),
                    "command": proc.get("command"),
                    "started_at": _iso(started),
                }
                (stale if epoch is not None and started < epoch else fresh).append(record)
            channels.append(
                {
                    "harness": entry.harness,
                    "path": str(root),
                    "installed_at": _iso(epoch),
                    "install_time_source": source,
                    "stale_hosts": stale,
                    "current_hosts": fresh,
                }
            )
            if stale:
                # 프로세스마다 같은 문장을 내지 않는다 — 사유는 채널당 하나이고
                # 다른 것은 pid 뿐이다.
                who = ", ".join(f"pid {proc['pid']}({proc['started_at']})" for proc in stale)
                findings.append(
                    f"{entry.harness} 호스트 {len(stale)}개가 설치({_iso(epoch)})보다 먼저 "
                    f"시작했다 — {who}. 플러그인은 **프로세스 시작 때** 로드되므로 CLI 를 "
                    "재시작하기 전까지 그 프로세스에는 스킬이 노출되지 않는다. 대화를 새로 "
                    "여는 것(`/clear`)으로는 부족하다 "
                    "(2026-08-20 실측, docs/INSTALLATION_AND_USAGE.md §7.0.1)"
                )

    return {
        "now": _iso(now_epoch),
        "process_error": list_error,
        "hosts_seen": sum(len(c["stale_hosts"]) + len(c["current_hosts"]) for c in channels),
        "superseded_skipped": skipped_superseded,
        "channels": channels,
        "stale": [c["harness"] for c in channels if c["stale_hosts"]],
        "findings": findings,
        "measurement_note": (
            "실행 중 호스트가 0개인 것은 통과가 아니라 **해당 없음**이다 — "
            "낡을 프로세스가 없다는 뜻일 뿐이다"
        ),
        "not_applicable": {
            "pi-dev": "경로 참조라 사본이 없다 — 설치 시각을 잴 자리가 없다",
            "gemini-cli": "이 호스트에 CLI 가 없어 미실측 (§7.0.2 와 같은 상태)",
        },
        "declared_unmeasured": [
            "프로세스 식별은 `ps` 의 `comm` 이름에 의존한다 — 런처가 다른 이름으로 "
            "뜨면(예: `node`) 이 절은 그 호스트를 세지 못한다",
            "재시작이 최신인 호스트라도 하네스가 스킬을 **노출하는지**까지는 "
            "이 절이 재지 않는다 — 마지막 한 칸은 실제 호출로만 재진다",
        ]
        + ([f"프로세스 목록을 얻지 못했다: {list_error}"] if list_error else []),
    }


# ---------------------------------------------------------------------------
# probe
# ---------------------------------------------------------------------------


def probe(
    project_root: Path | None = None,
    home: Path | None = None,
    *,
    now: float | None = None,
    processes: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """보고서를 만든다 — 아무것도 쓰지 않는다.

    Args:
        project_root: 검사할 프로젝트 루트 (기본: CWD).
        home: 사용자 홈 (기본: ``Path.home()``). fixture 주입용.
        now: 지금 시각 (epoch). `runtime_load` 판정의 기준점이고 fixture 주입용.
        processes: 실행 중 프로세스 목록. 주지 않으면 `ps` 로 잰다 — 실 호스트의
            프로세스를 읽는 탐침은 주입 없이는 검사할 수 없다 (`home` 과 같은 이유).
    """
    resolved_project = (project_root or Path.cwd()).resolve()
    resolved_home = (home or Path.home()).resolve()

    environment = _probe_environment(resolved_project)
    preflight = _probe_preflight()
    project = _probe_project_scope(resolved_project)
    global_scope = _probe_global_scope(resolved_home)
    drift = _probe_drift(project, global_scope)
    content_drift = _probe_content_drift(resolved_home)
    runtime_load = _probe_runtime_load(resolved_home, now=now, processes=processes)

    findings = [
        *environment["findings"],
        *preflight["findings"],
        *drift["findings"],
        *content_drift["findings"],
        *runtime_load["findings"],
    ]
    return {
        "status": "ok",
        "report_only": True,
        "environment": environment,
        "preflight": preflight,
        "project_scope": project,
        "global_scope": global_scope,
        "drift": drift,
        "content_drift": content_drift,
        "runtime_load": runtime_load,
        "finding_count": len(findings),
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# 사람이 읽는 출력
# ---------------------------------------------------------------------------


def _render_text(report: dict[str, Any]) -> str:
    lines: list[str] = ["=== wk doctor — 배포 탐침 (report-only) ==="]

    env = report["environment"]
    lines.append("")
    lines.append("[environment]")
    lines.append(f"  python      : {env['python_version']} ({env['executable']})")
    lines.append(f"  virtualenv  : {'yes' if env['in_virtualenv'] else 'no'}")
    lines.append(f"  wk on PATH  : {env['wk_on_path'] or '(없음)'}")
    lines.append(f"  workflow_kit: {env['modules'].get('workflow_kit') or '(import 실패)'}")

    project = report["project_scope"]
    lines.append("")
    lines.append("[project_scope]")
    lines.append(f"  root        : {project['project_root']}")
    lines.append(
        f"  kit version : {project['kit_version'] or '(알 수 없음)'}"
        f" ({project['kit_version_source']})"
    )
    if project["applied_harnesses"]:
        for harness in project["applied_harnesses"]:
            info = project["harnesses"][harness]
            lines.append(
                f"  - {harness}: 마커 {info['files_marked']}"
                f" / 존재 {len(info['files_present'])}"
                f" / 선언 {info['files_declared']}"
            )
    else:
        lines.append("  - kit 마커를 단 산출물이 없다")
    if project["candidate_harnesses"]:
        lines.append(
            "  · 마커 없이 파일만 있는 하네스: "
            f"{', '.join(project['candidate_harnesses'])}"
        )
        lines.append("    (공유 진입점이거나 다른 도구가 쓴 파일이다 — 적용으로 세지 않는다)")

    global_scope = report["global_scope"]
    lines.append("")
    lines.append("[global_scope]")
    for record in global_scope["homes"]:
        if record["declares_kit"]:
            state = "선언 있음"
        elif record["exists"]:
            state = "파일만 있음"
        else:
            state = "-"
        lines.append(f"  - {record['harness']:<12} {record['path']:<32} {state}")

    drift = report["drift"]
    lines.append("")
    lines.append("[drift]")
    for record in drift["stale_markers"]:
        lines.append(
            f"  - 낡음 {record['path']} (marker v{record['marker']} < kit v{record['kit_version']})"
        )
    for record in drift.get("forked_files", []):
        lines.append(
            f"  - 포크됨 {record['path']} (v{record['forked_from']} 에서 갈라짐"
            f" / kit v{record['kit_version']}) — 재적용은 파괴적이다"
        )
    if drift["installed_in_both_scopes"]:
        lines.append(f"  - 양쪽 설치: {', '.join(drift['installed_in_both_scopes'])}")
    if (
        not drift["stale_markers"]
        and not drift.get("forked_files")
        and not drift["installed_in_both_scopes"]
    ):
        lines.append("  - 마커 기준 어긋남 없음")
    lines.append(f"  ! {drift['limitation']}")

    pf = report.get("preflight") or {}
    lines.append("")
    lines.append("[preflight] 채널별 설치 전제 (설치 **전에** 잰다)")
    for channel in pf.get("channels", []):
        state = "설치 가능" if channel["installable"] else "막힘"
        lines.append(f"  - {channel['channel']}: {state}")
        if channel["missing_executables"]:
            lines.append(f"      없는 실행 파일: {', '.join(channel['missing_executables'])}")
        for item in channel.get("declared_unmeasured", []):
            lines.append(f"      (미측정 전제) {item}")
    if pf:
        lines.append(f"  ! {pf['measurement_note']}")

    content = report.get("content_drift") or {}
    lines.append("")
    lines.append(f"[content_drift] 정본 페이로드 {content.get('canonical_files', 0)}개와 해시 대조")
    if content.get("canonical_error"):
        lines.append(f"  ! 정본을 만들지 못했다: {content['canonical_error']}")
    caches = content.get("caches") or []
    if not caches:
        lines.append("  = 설치 사본 없음 (플러그인 채널 미설치)")
    for cache in caches:
        if not cache.get("active"):
            continue
        state = "in-sync" if cache.get("in_sync") else "DRIFT"
        lines.append(
            f"  - {cache['harness']} v{cache.get('installed_version') or '?'} "
            f"[{state}] 대조 {cache.get('files_compared', 0)}개 "
            f"(어느 사본인가: {cache.get('active_source')})"
        )
        for item in cache.get("differs", []):
            lines.append(f"      다름 {item['path']}: {item['expected'][:12]} != {item['actual'][:12]}")
        for rel in cache.get("missing", []):
            lines.append(f"      없음 {rel}")
    for old_copy in content.get("superseded") or []:
        lines.append(
            f"  ~ {old_copy['harness']} v{old_copy.get('installed_version') or '?'} — "
            "선언된 설치본이 아니다 (갱신 뒤 남은 옛 디렉터리). 발견으로 세지 않는다. "
            f"{old_copy.get('path')}"
        )
    for harness, why in sorted((content.get("not_applicable") or {}).items()):
        lines.append(f"  = {harness}: {why}")
    for item in content.get("declared_unmeasured", []):
        lines.append(f"  (미측정) {item}")

    runtime = report.get("runtime_load") or {}
    lines.append("")
    lines.append("[runtime_load] 실행 중 호스트가 이 설치를 봤는가 (세션이 아니라 **프로세스**)")
    if runtime.get("process_error"):
        lines.append(f"  ! {runtime['process_error']}")
    channels = runtime.get("channels") or []
    if not channels:
        lines.append("  = 설치 사본 없음 (플러그인 채널 미설치)")
    for channel in channels:
        lines.append(
            f"  - {channel['harness']}: 설치 {channel.get('installed_at') or '?'} "
            f"(출처 {channel.get('install_time_source')}) · 최신 호스트 "
            f"{len(channel['current_hosts'])}개 / 낡은 호스트 {len(channel['stale_hosts'])}개"
        )
        for proc in channel["stale_hosts"]:
            lines.append(f"      낡음 pid {proc['pid']} ({proc['command']}) 시작 {proc['started_at']}")
    if runtime:
        lines.append(f"  ! {runtime['measurement_note']}")
        for item in runtime.get("declared_unmeasured", []):
            lines.append(f"  (미측정) {item}")

    lines.append("")
    if report["findings"]:
        lines.append(f"발견 {report['finding_count']}건:")
        lines.extend(f"  - {item}" for item in report["findings"])
    else:
        lines.append("발견 0건.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wk doctor",
        description="배포 post-apply 탐침 — 설치 현황·버전·환경 전제를 보고한다 (report-only).",
    )
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--home", type=Path, default=None, help="사용자 홈 override (fixture 용)")
    parser.add_argument("--json", action="store_true", help="JSON 으로 출력한다")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="발견이 하나라도 있으면 rc 1 (기본은 발견이 있어도 rc 0 — 보고는 실패가 아니다)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    home = args.home
    if home is None:
        env_home = os.environ.get("WORKFLOW_DOCTOR_HOME")
        home = Path(env_home) if env_home else None

    report = probe(project_root=args.project_root, home=home)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_render_text(report))

    if args.strict and report["finding_count"]:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
