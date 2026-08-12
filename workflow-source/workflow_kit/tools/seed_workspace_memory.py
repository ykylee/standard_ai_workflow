#!/usr/bin/env python3
"""새 워크스페이스(브랜치)의 메모리를 seed 한다 — 표준 §10.2 의 "상태 문서를 먼저 생성".

**왜 필요한가**: `active/<branch>/` 는 브랜치를 만든다고 생기지 않는다. 아무도 만들어
주지 않으므로, 새 worktree 에서 `session-start` 를 돌리면 그대로 실패한다:

    status: error
    error_code: missing_required_document

즉 워크스페이스를 배정해도 에이전트가 **시작조차 못 한다**. 2026-08-07 실측으로 확인한
실패이고, 표준 §10.2 가 "브랜치를 만들고 작업 상태 문서를 먼저 생성한 뒤 push" 를
요구하는 이유다. 본 도구가 그 "먼저 생성" 을 담당한다.

**무엇을 만드는가** (`active/<branch>/`):

- `session_handoff.md` — 작업 지시가 실린다. 표준 §10.2 의 "작업 예정 내역".
- `backlog/<today>.md` + `backlog/tasks/TASK-….md` — 기존 writer 재사용.
- `sessions/` — 빈 디렉터리 (session 기록 자리).

`state.json` 은 **만들지 않는다.** 파생 파일이므로 `scripts/generate_workflow_state.py`
가 rebuild 한다 (`memory/active/README.md` §4).

**지시는 전달되지 않고 놓인다**: `session-start` 는 인자로 받은 경로의 문서만 읽는다.
중앙이 에이전트에게 메시지를 보내는 채널은 없으므로, 여기서 쓴 handoff 가 곧 업무
지시다. 다른 에이전트는 `git show origin/<branch>:<path>` 로 이를 읽는다.

**멱등**: 이미 있는 파일은 덮어쓰지 않는다 (`--force` 로만 덮어쓴다). 진행 중인
워크스페이스를 실수로 초기화하면 남의 작업을 지우는 것과 같기 때문이다.

Usage:
    python3 tools/seed_workspace_memory.py --branch feat-login \\
        --axis "로그인 세션 만료 처리" --task-title "세션 만료 시 재인증" --dry-run
    python3 tools/seed_workspace_memory.py --branch feat-login \\
        --axis "..." --task-title "..." --apply

Cross-ref: `core/global_workflow_standard.md` §10.2,
`core/multi_workspace_orchestration.md` §5A.2 (실패 실측) · §0.4 (플로우).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.paths import (  # noqa: E402
    get_current_branch,
    memory_dir_for_workspace,
)
from workflow_kit.common.workflow_writes import (  # noqa: E402
    render_task_file,
    upsert_backlog_entry,
)

HANDOFF_NAME = "session_handoff.md"


def next_task_id(tasks_dir: Path, *, branch: str, today: str) -> str:
    """`TASK-<today>-<branch>-<NNN>` 중 비어 있는 다음 번호.

    번호는 **브랜치 안에서만** 매긴다 — 브랜치별로 격리돼 있으므로 다른 호스트가 동시에
    만들어도 겹치지 않는다 (`MEMORY_GOVERNANCE.md` §2).
    """
    slug = branch.replace("/", "-")
    prefix = f"TASK-{today}-{slug}-"
    used = set()
    if tasks_dir.is_dir():
        for p in tasks_dir.glob(f"{prefix}*.md"):
            tail = p.stem[len(prefix):]
            if tail.isdigit():
                used.add(int(tail))
    n = 1
    while n in used:
        n += 1
    return f"{prefix}{n:03d}"


def render_handoff(*, branch: str, axis: str, task_id: str, task_title: str,
                   today: str, out_of_scope: str | None) -> str:
    """seed handoff 본문. `session-start` 가 요구하는 섹션을 채운다.

    `현재 기준선` 이 없으면 session-start 가 warning 을 낸다 — seed 단계에서 채워 둔다.
    """
    lines = [
        "# Session Handoff",
        "",
        "- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.",
        "- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크",
        "- 대상 독자: AI agent, 저장소 관리자",
        "- 상태: active",
        f"- 최종 수정일: {today}",
        "- 관련 문서: [backlog](./backlog/), [sessions](./sessions/)",
        "",
        "## 1. 현재 작업 요약",
        "",
        f"- 현재 기준선: {branch} 워크스페이스 seed ({today}). 아직 작업 전이다.",
        f"- 현재 주 작업 축: {axis}",
    ]
    if out_of_scope:
        lines.append(f"- 범위 밖(건드리지 않는다): {out_of_scope}")
    lines += [
        "",
        "## 2. 진행 중 작업",
        "",
        "- 현재 `in_progress` 작업:",
        f"- {task_id} — {task_title}",
        "",
        "## 3. 차단 작업",
        "",
        "- 현재 `blocked` 작업:",
        "",
        "## 4. 최근 완료 작업",
        "",
        "- 최근 완료 작업 목록:",
        "",
        "## 5. 다음 세션 시작 포인트",
        "",
        f"- [`backlog/tasks/{task_id}.md`](./backlog/tasks/{task_id}.md) 의 완료 기준을 먼저 읽는다.",
        "- 작업 범위를 벗어나는 변경은 다른 워크스페이스와 충돌할 수 있으므로 backlog 에 별도 task 로 남긴다.",
        "",
        "## 6. 남은 리스크",
        "",
        "- 아직 검증된 산출물이 없다.",
        "",
    ]
    return "\n".join(lines)


def task_body(*, axis: str, out_of_scope: str | None) -> list[str]:
    body = [
        "## 📝 Description",
        "",
        "- 상태: in_progress",
        f"- 요청일: {date.today().isoformat()}",
        "- 담당: AI Agent",
        f"- 작업 내용: {axis}",
    ]
    if out_of_scope:
        body.append(f"- 범위 밖: {out_of_scope}")
    body += [
        "- 완료 기준: (작성 필요 — 검증 방법을 구체적으로 적는다)",
        "",
        "## 🛠️ Implementation / Content",
        "",
        "- 진행 현황: 시작 전.",
        "",
        "## ✅ Outcome",
        "",
        "- 작업 결과:",
        "- 검증 결과:",
        "- 후속 작업:",
        "",
    ]
    return body


def seed(*, memory_root: Path, branch: str, axis: str, task_title: str,
         out_of_scope: str | None, today: str, apply: bool,
         force: bool) -> dict:
    branch_dir = memory_root / "active" / branch
    tasks_dir = branch_dir / "backlog" / "tasks"
    handoff_path = branch_dir / HANDOFF_NAME
    backlog_path = branch_dir / "backlog" / f"{today}.md"

    task_id = next_task_id(tasks_dir, branch=branch, today=today)
    planned: list[dict] = []
    skipped: list[dict] = []

    def note(path: Path, kind: str) -> bool:
        """생성 대상이면 True. 이미 있으면 skip 기록 후 False."""
        if path.exists() and not force:
            skipped.append({"path": str(path), "kind": kind, "reason": "이미 존재 (--force 로 덮어쓴다)"})
            return False
        planned.append({"path": str(path), "kind": kind})
        return True

    write_handoff = note(handoff_path, "handoff")
    write_task = note(tasks_dir / f"{task_id}.md", "task")
    note(backlog_path, "backlog_index")
    planned.append({"path": str(branch_dir / "sessions"), "kind": "sessions_dir"})

    result = {
        "status": "ok",
        "mode": "apply" if apply else "dry-run",
        "branch": branch,
        "task_id": task_id,
        "branch_dir": str(branch_dir),
        "planned": planned,
        "skipped": skipped,
        "warnings": [],
    }

    if not apply:
        return result

    (branch_dir / "backlog" / "tasks").mkdir(parents=True, exist_ok=True)
    (branch_dir / "sessions").mkdir(parents=True, exist_ok=True)

    if write_task:
        upsert_backlog_entry(
            backlog_path=backlog_path,
            task_id=task_id,
            entry_lines=render_task_file(
                task_id=task_id,
                title=task_title,
                status="in_progress",
                created_at=today,
                kind="generic",
                source_anchor=f"generic-{task_id.lower()}",
                source_path=f"backlog/{today}.md",
                body_lines=task_body(axis=axis, out_of_scope=out_of_scope),
            ),
            title=task_title,
            kind="generic",
            status="in_progress",
        )

    if write_handoff:
        handoff_path.write_text(
            render_handoff(branch=branch, axis=axis, task_id=task_id,
                           task_title=task_title, today=today,
                           out_of_scope=out_of_scope),
            encoding="utf-8",
        )

    result["warnings"].append(
        "state.json 은 seed 하지 않는다 — scripts/generate_workflow_state.py 로 생성한다."
    )
    return result


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--memory-root", default=str(memory_dir_for_workspace(REPO_ROOT)))
    p.add_argument("--branch", default=None,
                   help="대상 브랜치 (default: 현재 브랜치)")
    p.add_argument("--axis", required=True, help="주 작업 축 — 한 줄. 이게 곧 업무 지시다.")
    p.add_argument("--task-title", required=True, help="첫 task 제목")
    p.add_argument("--out-of-scope", default=None,
                   help="이 워크스페이스가 건드리지 않을 영역 (다른 워크스페이스와의 충돌 방지)")
    p.add_argument("--today", default=date.today().isoformat())
    p.add_argument("--apply", action="store_true", help="실제 생성 (default: dry-run)")
    p.add_argument(
        "--no-register",
        action="store_true",
        help=(
            "성공 시 workspace_registry 에 self-register 하지 않는다. CI / 격리 "
            "테스트 / 회사 정책 (registry 외부 저장 금지) 등 용도. 기본은 register."
        ),
    )
    p.add_argument(
        "--harness",
        default=None,
        help=(
            "Self-register 시 registry entry 의 harness 필드. 미지정이면 "
            "WORKFLOW_HARNESS env 를 그대로 사용."
        ),
    )
    p.add_argument(
        "--endpoint",
        default=None,
        help=(
            "Self-register 시 registry entry 의 endpoint 필드. 미지정이면 "
            "WORKFLOW_ENDPOINT env 를 그대로 사용."
        ),
    )
    p.add_argument("--dry-run", action="store_true", dest="dry_run")
    p.add_argument("--force", action="store_true",
                   help="이미 있는 파일도 덮어쓴다 (진행 중 워크스페이스를 지울 수 있으니 주의)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    if args.dry_run:
        args.apply = False

    branch = args.branch or get_current_branch()
    memory_root = Path(args.memory_root).resolve()

    result = seed(
        memory_root=memory_root, branch=branch, axis=args.axis,
        task_title=args.task_title, out_of_scope=args.out_of_scope,
        today=args.today, apply=args.apply, force=args.force,
    )

    # self-register: --apply 성공 시에만 (TASK-2026-08-08-main-008).
    # register 는 *부가 정보* (in-flight 가시성) 이지 플로우의 본 동작이 아니므로
    # 실패가 seed 성공 판정을 깨뜨리지 않게 격리한다. §5A.3 정합.
    registry_status: dict[str, object] = {"attempted": False, "ok": False, "skipped": False}
    if args.apply and not args.no_register:
        registry_status["attempted"] = True
        try:
            from workflow_kit.common import workspace_registry as _wr
            detected_harness = (
                args.harness
                or os.environ.get("WORKFLOW_HARNESS")
            )
            detected_endpoint = (
                args.endpoint
                or os.environ.get("WORKFLOW_ENDPOINT")
            )
            # v0.15.21+ : env 자동 주입 — sync_mavis 가 mavis alias env 로
            # 그대로 emit 한다. mavis 가 cwd 가 데스크탑 런타임 자리인 점을
            # 감안, REPO_ROOT 와 PYTHONPATH 를 *절대* 경로로 박는다.
            auto_env = {
                "STANDARD_AI_WORKFLOW_ROOT": str(REPO_ROOT),
                "PYTHONPATH": str(REPO_ROOT / "workflow-source"),
            }
            _wr.register(
                REPO_ROOT,
                branch=branch,
                harness=detected_harness,
                endpoint=detected_endpoint,
                env=auto_env,
            )
            registry_status["ok"] = True
        except Exception as exc:  # noqa: BLE001 — 5.A.3 격리
            registry_status["error"] = f"{type(exc).__name__}: {exc}"
    elif args.no_register:
        registry_status["skipped"] = True

    if args.json:
        payload = dict(result)
        payload["registry"] = registry_status
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"=== workspace memory seed ({result['mode']}) — 브랜치: {branch} ===")
        for item in result["planned"]:
            print(f"  CREATE  {item['kind']:<14} {item['path']}")
        for item in result["skipped"]:
            print(f"  skip    {item['kind']:<14} {item['path']}  ({item['reason']})")
        if not args.apply:
            print("\n  → 실제 생성: --apply")
        else:
            print(f"\n  task_id: {result['task_id']}")
            print("  다음: python3 workflow-source/scripts/generate_workflow_state.py "
                  "--project-profile-path docs/PROJECT_PROFILE.md \\")
            print(f"          --output-path {result['branch_dir']}/state.json")
            if registry_status["attempted"]:
                if registry_status["ok"]:
                    print("  registry: self-register OK")
                elif registry_status.get("error"):
                    print(f"  registry: self-register failed ({registry_status['error']}) — advisory")
            elif registry_status["skipped"]:
                print("  registry: --no-register (skipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
