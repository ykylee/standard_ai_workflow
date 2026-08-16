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
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from workflow_kit.bootstrap_lib.harnesses import HARNESS_SPECS
from workflow_kit.upgrade_diff import compare_marker, parse_version_marker, read_kit_version

__all__ = [
    "GLOBAL_DECLARATION_HOMES",
    "GlobalDeclarationHome",
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


# ---------------------------------------------------------------------------
# environment — 환경 전제 (컨셉 §7 gap 4 의 pre-flight 절)
# ---------------------------------------------------------------------------


def _probe_environment() -> dict[str, Any]:
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
    for name in ("pip", "workflow_kit"):
        try:
            module = __import__(name)
        except Exception:
            modules[name] = None
            if name == "pip" and in_venv:
                findings.append(
                    "venv 에 pip 이 없다 (uv 로 만든 venv) — "
                    "`python3 -m ensurepip --upgrade` 한 번으로 채운다"
                )
            continue
        modules[name] = getattr(module, "__file__", None)

    wk_path = shutil.which("wk")
    if wk_path is None:
        findings.append(
            "`wk` 가 PATH 에 없다 — 플러그인 스킬이 지시하는 메모리 갱신 명령이 돌지 않는다 "
            "(docs/INSTALLATION_AND_USAGE.md §3)"
        )

    return {
        "python_version": sys.version.split()[0],
        "executable": sys.executable,
        "in_virtualenv": in_venv,
        "externally_managed_markers": externally_managed,
        "modules": modules,
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
            present.append({"path": rel, "marker": _file_marker(path)})
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

    for harness, info in sorted(project.get("harnesses", {}).items()):
        for record in info["files_present"]:
            marker = record["marker"]
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
    if both_scopes:
        findings.append(
            f"글로벌·프로젝트 양쪽 설치 {len(both_scopes)}건 ({', '.join(both_scopes)}) — "
            "오류가 아니라 상태다. 로드는 하네스 우선순위(대개 project 우선)를 따른다"
        )
    return {
        "kit_version": kit_version,
        "stale_markers": stale,
        "unmarked_files": unmarked,
        "installed_in_both_scopes": both_scopes,
        "findings": findings,
        "limitation": (
            "마커 비교는 드리프트의 일부만 잡는다 — 버전이 같고 내용만 낡은 경우는 "
            "여기서 안 걸린다 (2026-08-16 실측). 내용 대조는 채널별 재빌드로 확인한다"
        ),
    }


# ---------------------------------------------------------------------------
# probe
# ---------------------------------------------------------------------------


def probe(project_root: Path | None = None, home: Path | None = None) -> dict[str, Any]:
    """4절 보고서를 만든다 — 아무것도 쓰지 않는다.

    Args:
        project_root: 검사할 프로젝트 루트 (기본: CWD).
        home: 사용자 홈 (기본: ``Path.home()``). fixture 주입용.
    """
    resolved_project = (project_root or Path.cwd()).resolve()
    resolved_home = (home or Path.home()).resolve()

    environment = _probe_environment()
    project = _probe_project_scope(resolved_project)
    global_scope = _probe_global_scope(resolved_home)
    drift = _probe_drift(project, global_scope)

    findings = [*environment["findings"], *drift["findings"]]
    return {
        "status": "ok",
        "report_only": True,
        "environment": environment,
        "project_scope": project,
        "global_scope": global_scope,
        "drift": drift,
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
    if drift["installed_in_both_scopes"]:
        lines.append(f"  - 양쪽 설치: {', '.join(drift['installed_in_both_scopes'])}")
    if not drift["stale_markers"] and not drift["installed_in_both_scopes"]:
        lines.append("  - 마커 기준 어긋남 없음")
    lines.append(f"  ! {drift['limitation']}")

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
