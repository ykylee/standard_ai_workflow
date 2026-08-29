#!/usr/bin/env python3
"""`wk ensure-entrypoints` 와 세션 시작 자기 복구 (TASK-2026-08-24-main-006).

## 왜 필요한가

세션 시작이 필수 문서를 못 찾으면 `missing_required_document` 로 **중단**했고,
`recovery_hint` 는 legacy shim 경로를 가리켰다. `CLAUDE.md` 의 self-bootstrap
절은 "없으면 scaffold 를 제안한다" 고 **이미 약속**하고 있었는데 배선이 없었다.

## 자동 적용의 경계 (소유자 결정, 2026-08-24)

- **부재 → 생성.** 되돌리기 쉽고 self-bootstrap 이 약속한 동작이다.
- **낡음 → 보고만.** 포크를 *선언하지 않은* 소비자 손수정이 세션을 여는 것만으로
  사라지면 안 된다. 이 경계가 이 검사의 핵심 주장이다.

## 실측이 고친 설계 하나

처음에는 복구를 `session_start` 의 **실패 경로**에만 달았다. 그런데 하네스
진입점이 없어도 session-start 는 *상태 문서* 만 읽으므로 `status: ok` 로 끝났고,
복구가 아예 안 돌았다. 격리 fixture 로 그 구멍을 확인하고 **성공 경로**로
옮겼다 — 그래서 이 검사는 "실패했을 때 고치는가" 가 아니라 **"매 시작마다
점검하는가"** 를 잰다.
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.bootstrap_lib.writes import (  # noqa: E402
    drain_file_actions,
    set_create_only,
    write_text,
)
from workflow_kit.tools.ensure_entrypoints import run as ensure_run  # noqa: E402
from workflow_kit.upgrade_diff import Action  # noqa: E402

FAILURES: list[str] = []
STALE_MARKER = "0.0.1"


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case}{(' — ' + detail) if detail else ''}")
        FAILURES.append(case)


def _env() -> dict[str, str]:
    """fixture 용 env. **브랜치 오버라이드를 지운다.**

    `--branch-context=slash` 는 `CODEX_WORKFLOW_BRANCH` 를 주입해 *이 kit 저장소의*
    메모리 경로를 흉내 낸다. 그런데 이 검사의 fixture 는 git 저장소가 아닌 임시
    디렉터리이고, `bootstrap_branch_slug` 는 **대상의 git 브랜치만** 본다(오버라이드를
    의도적으로 무시한다 — `bootstrap_lib/paths.py` 주석의 sandbox caller 근거).
    그래서 상속하면 bootstrap 은 `active/main/` 에 쓰고 session-start 는
    `active/feature/ci-slash-probe/` 를 봐서, 재려던 것과 무관하게 red 가 난다.

    제품 결함이 아니라 fixture 가 남의 컨텍스트를 물려받은 것이므로 여기서 끊는다.
    브랜치 해석 자체는 `check_branch_context_matrix` 가 잰다.
    """
    from workflow_kit.common.branch_matrix import OVERRIDE_ENV_KEY  # noqa: PLC0415

    env = {**os.environ, "PYTHONPATH": str(SOURCE_ROOT)}
    env.pop(OVERRIDE_ENV_KEY, None)
    return env


def _bootstrap(target: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", "workflow_kit.bootstrap_lib",
         "--target-root", str(target), "--project-slug", "demoproj",
         "--project-name", "Demo Proj", "--harness", "claude-code",
         "--no-interactive", "--adoption-mode", "new"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, env=_env(), check=True,
    )


def _make_stale(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    marked = text.replace("standard-ai-workflow-kit: v", "standard-ai-workflow-kit: vSENTINEL", 1)
    import re
    marked = re.sub(r"vSENTINEL[\d.]+(-[A-Za-z0-9.]+)?", f"v{STALE_MARKER}", marked, count=1)
    path.write_text(marked + "\n<!-- 소비자가 손으로 더한 줄 -->\n", encoding="utf-8")


def test_create_only_writes_missing_but_not_stale() -> None:
    """쓰기 판정 한 곳(`_resolve_write`)이 경계를 강제하는가."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        stale = root / "stale.md"
        stale.write_text(
            f"<!-- standard-ai-workflow-kit: v{STALE_MARKER} -->\n\nOLD BODY\n",
            encoding="utf-8",
        )
        set_create_only(True)
        try:
            write_text(root / "missing.md", "NEW FILE\n", rel_to=root)
            write_text(stale, "NEW BODY\n", rel_to=root)
            actions = {a["rel"]: a["action"] for a in drain_file_actions()}
        finally:
            set_create_only(False)
        problems: list[str] = []
        if actions.get("missing.md") != Action.CREATE.value:
            problems.append(f"부재가 생성되지 않았다: {actions}")
        if actions.get("stale.md") != Action.UPDATE_AVAILABLE.value:
            problems.append(
                f"낡음이 {actions.get('stale.md')!r} 로 보고됐다 — "
                f"{Action.UPDATE_AVAILABLE.value!r} 여야 한다. `updated` 면 '덮었다' 는 "
                "거짓이고 `ignored` 면 '최신이다' 는 거짓이다"
            )
        if "OLD BODY" not in stale.read_text(encoding="utf-8"):
            problems.append("create-only 인데 낡은 파일을 덮었다")
    _record("test_create_only_writes_missing_but_not_stale", not problems, "; ".join(problems))


def test_ensure_classifies_and_fills_missing_only() -> None:
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "proj"
        target.mkdir()
        _bootstrap(target)
        gone = target / ".claude" / "commands" / "workflow-session-end.md"
        gone.unlink()
        stale_path = target / ".claude" / "commands" / "workflow-doc-sync.md"
        _make_stale(stale_path)

        plan = ensure_run(project_root=target, apply=False)
        ensure_run(project_root=target, apply=True)
        after = ensure_run(project_root=target, apply=False)
        # 파일 존재 판정은 **블록 안에서** 굳힌다 — `with` 를 벗어나면 임시
        # 디렉터리가 지워져 `.exists()` 가 무조건 False 다. 처음 판이 그래서
        # "채우지 않았다" 를 오보했고, 도구는 내내 옳았다.
        restored = gone.exists()
        stale_text = stale_path.read_text(encoding="utf-8")

    problems: list[str] = []
    if not any(i["path"].endswith("workflow-session-end.md") for i in plan["missing"]):
        problems.append(f"부재를 못 잡았다: {plan['missing']}")
    if not any(i["path"].endswith("workflow-doc-sync.md") for i in plan["stale"]):
        problems.append(f"낡음을 못 잡았다: {plan['stale']}")
    if plan["created"]:
        problems.append("dry-run 이 파일을 만들었다")
    if not restored:
        problems.append("--apply 가 부재 파일을 채우지 않았다")
    if after["missing"]:
        problems.append(f"적용 뒤에도 부재가 남았다: {after['missing']}")
    if not after["stale"]:
        problems.append("낡음이 사라졌다 — 자동으로 덮었다는 뜻이다")
    if "소비자가 손으로 더한 줄" not in stale_text:
        problems.append("낡은 파일의 소비자 손수정이 사라졌다")
    _record("test_ensure_classifies_and_fills_missing_only", not problems, "; ".join(problems))


def test_no_project_identity_means_no_invention() -> None:
    """`PROJECT_PROFILE.md` 가 없으면 **아무것도 만들지 않는다**.

    이름을 지어내면 그 거짓이 이후 모든 산출물에 실린다.
    """
    with tempfile.TemporaryDirectory() as td:
        empty = Path(td) / "empty"
        empty.mkdir()
        result = ensure_run(project_root=empty, apply=True)
        leftovers = [p.name for p in empty.iterdir()]
    problems: list[str] = []
    if result["status"] != "needs_bootstrap":
        problems.append(f"status={result['status']} — needs_bootstrap 이어야 한다")
    if leftovers:
        problems.append(f"정체를 모르는데 파일을 만들었다: {leftovers}")
    _record("test_no_project_identity_means_no_invention", not problems, "; ".join(problems))


def test_session_start_checks_on_every_start() -> None:
    """세션 시작이 **성공 경로에서도** 진입점을 점검하는가.

    실패 경로에만 달면 하네스 진입점 부재는 영원히 안 잡힌다 — session-start 는
    상태 문서만 읽으므로 `status: ok` 로 끝나기 때문이다 (실측으로 확인한 구멍).
    """
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "proj"
        target.mkdir()
        _bootstrap(target)
        gone = target / ".claude" / "commands" / "workflow-session-end.md"
        gone.unlink()
        proc = subprocess.run(
            [sys.executable, "-m", "workflow_kit.workflow_kit_cli", "session-start"],
            cwd=str(target), capture_output=True, text=True, env=_env(),
        )
        restored = gone.exists()
    problems: list[str] = []
    try:
        payload = json.loads(proc.stdout[proc.stdout.index("{"):])
    except ValueError:
        _record("test_session_start_checks_on_every_start", False,
                f"session-start 출력을 읽지 못했다: {proc.stdout[:200]}")
        return
    if payload.get("status") != "ok":
        problems.append(f"status={payload.get('status')}")
    if not restored:
        problems.append("성공 경로에서 부재 진입점이 복구되지 않았다")
    if not any("진입점" in w for w in payload.get("warnings", [])):
        problems.append(f"복구 사실을 warnings 에 안 남겼다: {payload.get('warnings')}")
    _record("test_session_start_checks_on_every_start", not problems, "; ".join(problems))


def main() -> int:
    cases = [
        test_create_only_writes_missing_but_not_stale,
        test_ensure_classifies_and_fills_missing_only,
        test_no_project_identity_means_no_invention,
        test_session_start_checks_on_every_start,
    ]
    for case in cases:
        case()
    total = len(cases)
    print(f"\n{total - len(FAILURES)}/{total} passed")
    if FAILURES:
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
