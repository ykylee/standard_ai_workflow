#!/usr/bin/env python3
"""진입점·필요 파일을 **부재는 채우고 낡음은 보고**한다 (TASK-2026-08-24-main-006).

    wk ensure-entrypoints              # 계획만 (dry-run)
    wk ensure-entrypoints --apply      # 부재만 생성 (낡음은 보고)
    wk ensure-entrypoints --json

## 왜 필요한가

세션 시작이 필수 문서를 못 찾으면 `missing_required_document` 로 **중단**했고,
`recovery_hint` 는 legacy shim 경로를 가리켰다. 소비자 입장에서는 "워크플로우가
안 돈다" 로만 보인다 — 무엇이 없는지, 무엇으로 채우는지가 안 보였다.

필요한 조각은 이미 다 있었다. `HARNESS_SPECS` 가 **무엇이 필요한지** 선언하고,
`bootstrap_lib` 렌더러가 **현재 kit 버전으로** 찍으며, `decide_action` 이
CREATE / UPDATED / IGNORED / PRESERVED / FORKED 를 판정한다. 없던 것은 **배선**이다.

## 자동 적용의 경계 (소유자 결정, 2026-08-24)

- **부재 → 생성.** 없던 파일을 만드는 것은 되돌리기 쉽고, `CLAUDE.md` 의
  self-bootstrap 절이 **이미 약속한 동작**이다.
- **낡음 → 보고만.** 덮어쓰기는 다르다. 포크를 *선언한* 파일은 `FORKED` 가
  지키지만, **선언하지 않은 소비자의 손수정은 조용히 날아간다.** 그래서 갱신은
  사람이 고르게 하고, 이 도구는 무엇이 낡았는지와 고치는 명령만 말한다.

그 경계는 `writes.set_create_only()` 가 강제한다 — 쓰기 판정이 한 곳에 모여
있으므로(`_resolve_write`) 경로가 늘어도 새는 곳이 없다.

## 이 도구가 하지 않는 것

**프로젝트 정체를 지어내지 않는다.** `PROJECT_PROFILE.md` 가 없으면 프로젝트
이름·슬러그를 알 수 없고, 그것을 추측해 문서를 만들면 그 거짓이 이후 모든
산출물에 실린다. 그때는 `needs_bootstrap` 으로 보고하고 최초 bootstrap 명령을
안내한다 — 모르는 것을 아는 척하지 않는다.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
#: `workflow_kit` 패키지가 사는 곳. **저장소 루트가 아니다** — 내부 bootstrap 을
#: 자식 프로세스로 부를 때 `PYTHONPATH` 를 루트로 주면 import 가 실패한다.
#: 수동 시험에서는 PYTHONPATH 가 이미 export 돼 있어 가려졌고,
#: `check_ensure_entrypoints` 가 그것을 잡았다.
SOURCE_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.bootstrap_lib.harnesses import HARNESS_SPECS  # noqa: E402
from workflow_kit.common.paths import discover_project_profile_path  # noqa: E402
from workflow_kit.common.project_docs import parse_project_profile_core  # noqa: E402
from workflow_kit.upgrade_diff import (  # noqa: E402
    compare_marker,
    parse_fork_declaration,
    parse_overlay_declaration,
    parse_version_marker,
)

#: 하네스 산출물과 별개로 워크플로우가 **읽는** 상태 문서. 부재 판정만 한다.
STATE_DOCUMENT_RELPATHS = (
    "ai-workflow/memory/active/{branch}/session_handoff.md",
    "ai-workflow/memory/active/{branch}/state.json",
)


def _kit_version() -> str | None:
    try:
        import workflow_kit  # noqa: PLC0415

        return workflow_kit.__version__
    except Exception:  # noqa: BLE001
        return None


def _current_branch(project_root: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_root, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "main"
    name = proc.stdout.strip()
    return name if proc.returncode == 0 and name else "main"


def _applied_harnesses(project_root: Path) -> list[str]:
    """이 프로젝트에 **이미 적용된** 하네스. 마커가 하나라도 있으면 적용으로 본다.

    존재는 적용이 아니다 — `AGENTS.md` 처럼 다른 도구가 쓴 파일이 여러 하네스를
    적용됨으로 만들 수 있다 (`deploy_doctor` 가 같은 이유로 마커를 본다).
    """
    applied: list[str] = []
    for name, spec in sorted(HARNESS_SPECS.items()):
        for rel in (*spec.entry_files, *spec.extra_files):
            path = project_root / rel
            if not path.is_file():
                continue
            try:
                if parse_version_marker(path.read_text(encoding="utf-8")):
                    applied.append(name)
                    break
            except (OSError, UnicodeDecodeError):
                continue
    return applied


def classify(project_root: Path, harnesses: list[str]) -> dict[str, list[dict[str, str]]]:
    """선언된 파일을 missing / current / stale / forked / plugin_delegated 로 가른다.

    overlay 위임 (ADR-027 후속, 60차): entry 파일이
    `standard-ai-workflow-kit-overlay: plugin-only` 를 선언하면 그 하네스의
    extra_files(overlay) 부재는 결함이 아니라 **위임**이다 — 프로젝트가 같은
    스킬을 플러그인 채널로 소비한다는 선언이고, 자동 복구는 그 파일을
    되살리지 않는다. 존재하는 overlay 파일은 여전히 정상 분류한다(잔재가
    조용히 사라지면 안 된다 — 걷어내는 것은 사람의 일이다).
    """
    kit_version = _kit_version()
    out: dict[str, list[dict[str, str]]] = {
        "missing": [], "current": [], "stale": [], "forked": [], "unmarked": [],
        "plugin_delegated": [],
    }
    for harness in harnesses:
        spec = HARNESS_SPECS.get(harness)
        if spec is None:
            continue
        overlay_delegated = False
        for entry_rel in spec.entry_files:
            entry_path = project_root / entry_rel
            if entry_path.is_file():
                try:
                    if parse_overlay_declaration(entry_path.read_text(encoding="utf-8")) == "plugin-only":
                        overlay_delegated = True
                        break
                except (OSError, UnicodeDecodeError):
                    continue
        for rel in (*spec.entry_files, *spec.extra_files):
            path = project_root / rel
            record = {"harness": harness, "path": rel}
            if not path.is_file():
                if overlay_delegated and rel in spec.extra_files:
                    out["plugin_delegated"].append(record)
                else:
                    out["missing"].append(record)
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                out["unmarked"].append(record)
                continue
            if parse_fork_declaration(text) is not None:
                out["forked"].append(record)
                continue
            marker = parse_version_marker(text)
            if marker is None:
                out["unmarked"].append(record)
            elif kit_version and compare_marker(marker, kit_version) < 0:
                out["stale"].append({**record, "marker": marker, "kit_version": kit_version})
            else:
                out["current"].append(record)
    return out


def _missing_state_documents(project_root: Path, branch: str) -> list[str]:
    missing = []
    for template in STATE_DOCUMENT_RELPATHS:
        rel = template.format(branch=branch)
        if not (project_root / rel).is_file():
            missing.append(rel)
    return missing


def run(*, project_root: Path, apply: bool) -> dict[str, object]:
    profile_path = discover_project_profile_path(project_root)
    kit_version = _kit_version()
    branch = _current_branch(project_root)

    if profile_path is None:
        return {
            "status": "needs_bootstrap",
            "mode": "apply" if apply else "dry-run",
            "project_root": str(project_root),
            "kit_version": kit_version,
            "reason": (
                "PROJECT_PROFILE.md 이 없다 — 프로젝트 이름·슬러그를 알 수 없으므로 "
                "문서를 만들지 않는다. 지어내면 그 거짓이 이후 모든 산출물에 실린다."
            ),
            "next_command": (
                "python3 -m workflow_kit.bootstrap_lib --target-root . "
                "--project-slug <slug> --project-name <name> --harness <harness>"
            ),
        }

    harnesses = _applied_harnesses(project_root)
    classified = classify(project_root, harnesses)
    created: list[str] = []
    apply_error: str | None = None

    if apply and classified["missing"]:
        core = parse_project_profile_core(profile_path)
        name = str(core.get("project_name") or project_root.name)
        slug = name.lower().replace(" ", "_")
        argv = [
            sys.executable, "-m", "workflow_kit.bootstrap_lib",
            "--target-root", str(project_root),
            "--project-slug", slug,
            "--project-name", name,
            "--no-interactive",
            "--adoption-mode", "existing",
            "--create-missing-only",
        ]
        for harness in harnesses:
            argv += ["--harness", harness]
        env = {**dict(__import__("os").environ), "PYTHONPATH": str(SOURCE_ROOT)}
        proc = subprocess.run(argv, capture_output=True, text=True, env=env)
        if proc.returncode != 0:
            apply_error = (proc.stderr or proc.stdout)[-600:]
        else:
            try:
                manifest = json.loads(proc.stdout[proc.stdout.index("{"):])
                created = [
                    item["rel"]
                    for item in manifest.get("file_actions", {}).get("created", [])
                ]
            except (ValueError, KeyError):
                apply_error = "bootstrap 출력을 읽지 못했다"
        classified = classify(project_root, harnesses)

    return {
        "status": "blocked" if apply_error else "ok",
        "mode": "apply" if apply else "dry-run",
        "project_root": str(project_root),
        "project_profile_path": str(profile_path),
        "kit_version": kit_version,
        "branch": branch,
        "applied_harnesses": harnesses,
        "missing": classified["missing"],
        "stale": classified["stale"],
        "forked": classified["forked"],
        "unmarked": classified["unmarked"],
        # overlay 위임 부재 — missing 이 아니다. 보고에서 빠지면 "아무 일도
        # 없었다" 로 읽힌다 (손으로 유지하는 버킷은 새 분류를 조용히 삼킨다).
        "plugin_delegated": classified["plugin_delegated"],
        "current_count": len(classified["current"]),
        "missing_state_documents": _missing_state_documents(project_root, branch),
        "created": created,
        "apply_error": apply_error,
        "stale_hint": (
            "낡은 산출물은 **자동으로 덮지 않는다** — 포크를 선언하지 않은 손수정이 "
            "조용히 사라지기 때문이다. 갱신하려면 "
            "`python3 -m workflow_kit.bootstrap_lib --target-root . --harness <harness> …` "
            "를 직접 실행한다 (포크 선언이 있는 파일은 그때도 지켜진다)."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ensure-entrypoints",
        description="진입점·필요 파일을 부재는 채우고 낡음은 보고한다 (dry-run 기본).",
    )
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--apply", action="store_true", help="부재 파일을 실제로 생성")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve() if args.project_root else Path.cwd()
    result = run(project_root=project_root, apply=args.apply)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["status"] == "needs_bootstrap":
        print(f"[needs_bootstrap] {result['reason']}")
        print(f"  다음: {result['next_command']}")
    else:
        print(f"[{result['mode']}] {result['project_root']} (kit {result['kit_version']})")
        print(f"  적용된 하네스 : {result['applied_harnesses'] or '(없음)'}")
        print(f"  최신          : {result['current_count']}")
        print(f"  부재          : {len(result['missing'])}"
              + (f" → 생성 {len(result['created'])}" if result["created"] else ""))
        for item in result["missing"]:
            print(f"    - {item['path']}")
        print(f"  낡음(보고만)  : {len(result['stale'])}")
        for item in result["stale"]:
            print(f"    - {item['path']} (v{item['marker']} < kit v{item['kit_version']})")
        if result["forked"]:
            print(f"  포크(건드리지 않음): {[i['path'] for i in result['forked']]}")
        if result["missing_state_documents"]:
            print(f"  상태 문서 부재: {result['missing_state_documents']}")
        if result["stale"]:
            print(f"  ! {result['stale_hint']}")
        if result["apply_error"]:
            print(f"  ! 적용 실패: {result['apply_error']}")
    return 1 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
