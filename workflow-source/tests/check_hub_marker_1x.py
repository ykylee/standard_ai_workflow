#!/usr/bin/env python3
"""1.x 쪽 '허브로 옮김' 표식 (M-038 WBS-38.3 · 요구 R14.6 · R14.7) — 표식이 있으면 쓰기 도구가 거절한다.

정본: ``workflow_kit/common/hub_marker.py``. 1.x 프로젝트 fixture(git 저장소)에 표식을 놓고 문서화된 입구
(``python -m workflow_kit <명령>``)로 부른다.

1. 분류 — CLI 명령 전부가 막음 / 면제(사유)로 나뉜다. 미분류 · 겹침 · 없는 이름 0
2. 거절 — 표식이 있으면 backlog-update --apply · refresh-state · rollover-handoff-notes --apply · todo 가
   종료 코드 3 · error_code hub_migrated · 허브 주소, 저장소 파일 변화 0. 하위 디렉터리에서 불러도 (위로 찾는다)
3. session-start — 표식이 있으면 종료 코드 0 · 허브 안내 · 파일 변화 0
4. 되돌리기 — 표식을 지우면 backlog-update --apply 가 다시 쓰고 session-start 에 허브 안내가 없다
5. MCP plan_import — 같은 입구를 지나 거절된다
6. 한 정본 — 허브(있으면)의 표식 경로가 같은 상수이고, kit 안에 경로 리터럴 사본이 없다
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 300

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/check_roadmap_gates.py",
    "workflow-source/tests/check_branch_memory_auto_seed.py",
    "workflow-source/tests/check_memory_lint.py",  # auto-seed fixture 가 import 한다
    "workflow-source/pyproject.toml",  # python -m workflow_kit 가 kit 전체를 읽는다
)

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_branch_memory_auto_seed as seedfx  # noqa: E402
import check_roadmap_gates as rg  # noqa: E402
from workflow_kit.common import hub_marker  # noqa: E402
from workflow_kit.workflow_kit_cli import COMMANDS  # noqa: E402

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    env["CODEX_WORKFLOW_BRANCH"] = rg.BRANCH
    for k in ("GIT_DIR", "GIT_WORK_TREE"):
        env.pop(k, None)
    return env


def wk(cwd: Path, *args: str) -> tuple[int, dict[str, Any], str]:
    proc = subprocess.run([sys.executable, "-m", "workflow_kit", *args], cwd=cwd, capture_output=True, text=True,
                          env=_env(), timeout=180, encoding="utf-8", errors="replace")
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else {}
    except json.JSONDecodeError:
        payload = {}
    return proc.returncode, payload, proc.stderr


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def git(root: Path, *args: str) -> None:
    env = {**_env(), "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.invalid", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=env)


def main() -> int:
    print("check_hub_marker_1x")
    # 1 분류
    names = set(COMMANDS)
    guarded, exempt = set(hub_marker.GUARDED_COMMANDS), set(hub_marker.EXEMPT_COMMANDS)
    unclassified = sorted(names - guarded - exempt)
    overlap = sorted(guarded & exempt)
    stale = sorted((guarded | exempt) - names)
    empty_reason = sorted(k for k, v in hub_marker.EXEMPT_COMMANDS.items() if not v.strip())
    ok1 = not unclassified and not overlap and not stale and not empty_reason and "backlog-update" in guarded
    print(f"    명령 {len(names)} · 막음 {len(guarded)} · 면제 {len(exempt)} · 미분류 {len(unclassified)}")
    _record("case 1 (분류 — 모든 명령이 막음/면제, 미분류 · 겹침 · 없는 이름 0)", ok1,
            f"미분류={unclassified} 겹침={overlap} 없는 이름={stale} 사유 없음={empty_reason}")

    with tempfile.TemporaryDirectory(prefix="hub-marker-") as d:
        root = Path(d) / "proj"
        profile = rg._fixture(root)
        git(root, "init", "-q", "-b", rg.BRANCH)
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "init")
        marker = root / hub_marker.MARKER_REL
        marker.write_text(json.dumps({"format": "workflow-hub-migrated/1", "hub": "https://hub.example.invalid",
                                      "project_id": "P-1", "migration_id": "MIG-0001"}), encoding="utf-8")
        prof = ["--project-profile-path", str(profile)]

        # 2 거절
        before = snapshot(root)
        r_bu = wk(root, "backlog-update", *prof, "--task-name", "x", "--task-brief", "y", "--mode", "create", "--apply")
        r_rs = wk(root, "refresh-state", *prof)
        r_ro = wk(root, "rollover-handoff-notes", "--apply")
        sub = root / "docs"
        r_sub = wk(sub, "todo", "add", "할 일")
        after = snapshot(root)
        results = [r_bu, r_rs, r_ro, r_sub]
        ok2 = (all(rc == hub_marker.REFUSAL_EXIT and p.get("error_code") == hub_marker.ERROR_CODE
                   and p.get("hub") == "https://hub.example.invalid" for rc, p, _ in results)
               and before == after and "허브" in r_bu[2])
        _record("case 2 (거절 — 쓰기 명령 넷 · 하위 디렉터리에서도, 종료 코드 3 · 허브 주소 · 파일 변화 0)", ok2,
                f"{[(rc, p.get('error_code')) for rc, p, _ in results]} same={before == after}")

        # 3 session-start — seed 하는 저장소(대조군은 실제로 쓴다)에서 표식이 있으면 쓰지 않는다
        problems3: list[str] = []
        for label, with_marker in (("control", False), ("marked", True)):
            clone = seedfx._make_repo(Path(d) / f"ss-{label}")
            seedfx._git(clone, "switch", "-q", "-c", "claude/marker-probe")
            (clone / "ai-workflow" / "memory" / "active" / "memory_index").mkdir(parents=True)
            if with_marker:
                m = clone / hub_marker.MARKER_REL
                m.write_text(json.dumps({"hub": "https://hub.example.invalid", "project_id": "P-1"}), encoding="utf-8")
            b0 = snapshot(clone)
            # fixture 의 실행 함수 그대로 — 브랜치 env 를 덮지 않아야 seed 경로를 지난다 (wk() 는 main 을 싣는다)
            ss = seedfx._session_start(clone)
            rc_ss = 0 if ss.get("status") == "ok" else 1
            changed = b0 != snapshot(clone)
            hub_warn = [w for w in ss.get("warnings", []) if "허브로 옮겼다" in w]
            if not with_marker and (not seedfx._seeded(ss) or not changed):
                problems3.append(f"대조군이 쓰지 않았다 — fixture 가 쓰기 경로를 안 지난다 (rc={rc_ss})")
            if with_marker and (rc_ss != 0 or changed or len(hub_warn) != 1 or seedfx._seeded(ss)
                                or "쓰지 않았다" not in hub_warn[0]):
                problems3.append(f"표식: rc={rc_ss} changed={changed} warn={hub_warn} seeded={seedfx._seeded(ss)}")
        _record("case 3 (session-start — 표식이 있으면 seed 등 쓰기 0 · 허브 안내 · 종료 코드 0, 대조군은 쓴다)",
                not problems3, "; ".join(problems3))

        # 5 MCP plan_import (표식이 있는 동안)
        from workflow_kit.common.plan_mcp import plan_import_payload
        mcp = plan_import_payload(workspace_root=str(root), apply=True, tool_version="t")
        ok5 = mcp.get("error_code") == hub_marker.ERROR_CODE or mcp.get("status") == "refused"
        _record("case 5 (MCP plan_import — 같은 입구에서 거절)", ok5, json.dumps(mcp, ensure_ascii=False)[:300])

        # 4 되돌리기
        marker.unlink()
        rc_back, back, _ = wk(root, "backlog-update", *prof, "--task-name", "되돌린 뒤", "--task-brief", "y",
                              "--mode", "create", "--wbs", "exempt", "--wbs-exempt-reason", "검사", "--apply")
        _rc_ss2, ss2, _ = wk(root, "session-start", *prof)
        created = sorted(p.name for p in (root / "ai-workflow/memory/active" / rg.BRANCH / "backlog/tasks").glob("*.md"))
        # 이 fixture 의 session-start 는 문서가 모자라 오류로 끝난다 — 표식 안내가 없다는 것만 본다
        ok4 = (rc_back == 0 and back.get("status") == "ok" and len(created) == 1
               and not any("허브로 옮겼다" in w for w in ss2.get("warnings", []))
               and "허브로 옮겼다" not in str(ss2.get("recovery_hint", "")))
        _record("case 4 (되돌리기 — 표식을 지우면 다시 쓰고 session-start 도 평소대로)", ok4,
                f"rc={rc_back} {back.get('status')} {back.get('error')} created={created}")

    # 6 한 정본
    literal = hub_marker.MARKER_REL.rsplit("/", 1)[-1]
    copies = sorted(str(p.relative_to(SOURCE_ROOT)) for p in (SOURCE_ROOT / "workflow_kit").rglob("*.py")
                    if literal in p.read_text(encoding="utf-8") and p.name != "hub_marker.py")
    try:
        from workflow_kit.hub import migrate1x  # noqa: PLC0415
        hub_same: bool | None = migrate1x.MARKER_PATH is hub_marker.MARKER_REL
    except ImportError:  # release/1.x 에는 허브가 없다 — 허브 쪽 대조는 해당 없음 (통과로 세지 않고 따로 적는다)
        hub_same = None
    print(f"    허브 상수 대조: {'해당 없음 (hub 패키지 없음)' if hub_same is None else hub_same}")
    ok6 = not copies and hub_same is not False
    _record("case 6 (한 정본 — 허브가 같은 상수, 경로 리터럴 사본 0)", ok6, f"사본={copies} hub_same={hub_same}")

    print(f"PASS {len(_passes)} · FAIL {len(_failures)}")
    for f in _failures:
        print(f"  FAIL {f}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
