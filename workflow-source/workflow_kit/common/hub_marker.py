"""'허브로 옮김' 표식 — 1.x 쪽 판정 (요구 R14.6 · R14.7 · DS9, M-038 WBS-38.3).

2.0 허브로 전환한 저장소에는 ``ai-workflow/HUB_MIGRATED.json`` 이 커밋돼 있다 (허브의
``hub_migrate_marker`` 가 쓰기 지시를 낸다). 그 저장소에서 1.x kit 의 쓰기 도구가 메모리를 고치면 정본이
둘이 된다 — 그래서 이 파일을 보면 **쓰기를 거절하고 허브를 가리킨다**. 표식만 지우면 1.x 흐름으로 돌아간다.

표식 경로의 정본은 여기다 — 허브(``workflow_kit.hub.migrate1x``)도 이 상수를 쓴다.

거절하는 곳은 문서화된 입구다: ``python -m workflow_kit <명령>`` (플러그인 스킬 · 하네스가 부르는 길,
:data:`GUARDED_COMMANDS`) 과 MCP 의 계획 응답 반영. 모듈을 직접 실행하는 길(``python -m
workflow_kit.tools.X``)은 이 입구를 지나지 않는다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

#: 표식 경로 (저장소 뿌리 상대) — 정본.
MARKER_REL = "ai-workflow/HUB_MIGRATED.json"
ERROR_CODE = "hub_migrated"
#: 거절 종료 코드 — 2 는 사용법 오류에 쓰인다.
REFUSAL_EXIT = 3

#: 표식이 있으면 거절하는 명령 — 워크플로우 상태(메모리 · 계획 · 위키 · 목적)를 쓰는 것.
GUARDED_COMMANDS: frozenset[str] = frozenset({
    "archive-branch-memory", "archive-stale-memory", "backlog-update", "claim-workspace", "compact-checkpoint",
    "ingest-purpose", "migrate-active-to-appendonly", "migrate-legacy-l2", "migrate-memory-to-branch-scoped",
    "migrate-task-labels", "plan-import", "refresh-purpose", "refresh-state", "refresh-wiki-memory",
    "rollover-baselines", "rollover-handoff-notes", "rotate-workflow-logs", "seed-workspace-memory",
    "suggest-memory-entries", "todo", "wiki-emit", "memory-index-telemetry",
})

#: 막지 않는 명령과 그 사유. 새 명령은 둘 중 하나에 들어가야 한다 (검사가 미분류를 red 로 본다).
EXEMPT_COMMANDS: dict[str, str] = {
    "session-start": "표식을 보면 스스로 읽기 전용으로 돈다 (seed · 합류 · 진입점 · telemetry 를 건너뛴다)",
    "doctor": "설치 진단 — 저장소 메모리를 쓰지 않는다",
    "dashboard": "읽기 · 보고", "dashboard-export": "읽기 · 보고", "alert": "읽기 · 보고",
    "plan-status": "읽기", "memory-index-query": "읽기", "graph-insights": "읽기", "consumer-metrics": "읽기",
    "detect-scope-drift": "읽기", "progress-nudge": "읽기", "doc-sync": "advisory — 제안만",
    "score-wiki-maintainability": "읽기", "score-wiki-trend": "읽기", "trend-chart": "읽기",
    "check-branch-protection": "읽기", "check-packaging": "kit 패키지 검사", "check-quickstart-stale-links": "읽기",
    "audit-root-anchors": "읽기", "survey-remote-workspaces": "읽기",
    "workbench": "보기 서버 — 쓰기는 받은편지함 응답뿐이고 반영(plan-import)이 막힌다",
    "ensure-entrypoints": "진입 파일 — 허브 렌더 영역과 겹치지 않는 1.x 영역만",
    "apply-robust-patch": "범용 패치 도구 — 워크플로우 상태 전용이 아니다",
    "create-environment-record-stub": "환경 기록 초안 — 출력만",
    "fill-reverse-engineering-artifacts": "역공학 산출물 — 워크플로우 상태 아님",
    "emit-wiki-l2-body": "출력만", "layer2": "읽기",
    "okf-export": "내보내기 — 출력 디렉터리에 쓴다", "okf-validate": "읽기", "okf-version-check": "읽기",
    "okf-import": "외부 묶음 → 작업 디렉터리 (전환 뒤에는 허브 hub_wiki_import_okf 를 쓴다)",
    "okf-cleanup": "OKF 출력 정리",
    "cache-dashboard": "캐시", "cache-decay": "캐시", "cache-export-json": "캐시", "cache-import-csv": "캐시",
    "cache-lfu-decay-persist": "캐시", "cache-lru-decay": "캐시", "cache-merge-csv": "캐시",
    "cache-merge-multi": "캐시", "cache-migrate": "캐시", "cache-prune": "캐시", "cascade-delete": "캐시",
    "federate": "호스트 간 레지스트리", "host-pull-registry": "호스트 간 레지스트리",
    "host-serve-registry": "호스트 간 레지스트리", "workspace-registry": "호스트 간 레지스트리",
    "install-pre-push-hook": "git hook 설치",
    "release-bump": "kit 발행 (kit 저장소 전용)", "release-changelog": "kit 발행", "release-create": "kit 발행",
    "release-dist": "kit 발행", "release-doctor": "kit 발행", "release-note": "kit 발행",
    "release-pipeline": "kit 발행", "release-rollback": "kit 발행", "release-status": "kit 발행",
    "release-v0-13-0": "kit 발행", "release-verify": "kit 발행", "sync-release-hash": "kit 발행",
    "fix-readme-for-release": "kit 발행",
}


def find_marker(start: Path) -> tuple[Path, dict[str, Any]] | None:
    """``start`` 에서 위로 올라가며 표식을 찾는다 (git 뿌리에서 멈춘다). 읽을 수 없는 표식도 표식이다."""
    here = start.resolve()
    for d in (here, *here.parents):
        path = d / MARKER_REL
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                data = {}
            return path, data if isinstance(data, dict) else {}
        if (d / ".git").exists():
            return None
    return None


def describe(path: Path, data: dict[str, Any]) -> str:
    hub = data.get("hub") or "(허브 주소 없음)"
    project = data.get("project_id") or "?"
    return (f"이 저장소는 워크플로우 허브로 옮겼다 ({hub} · 프로젝트 {project} · {data.get('migration_id', '?')}) — "
            f"작업 상태는 허브에서 쓴다 (hub_session_start · hub_task_* · hub_session_end). "
            f"1.x 로 되돌리려면 {path.name} 만 지우고 커밋한다 (허브 쪽 기록은 옮기지 않는다).")


def refusal(command: str, path: Path, data: dict[str, Any]) -> dict[str, Any]:
    return {"status": "refused", "error_code": ERROR_CODE, "command": command, "marker": str(path),
            "hub": data.get("hub"), "project_id": data.get("project_id"),
            "error": f"`{command}` 는 쓰지 않았다 — " + describe(path, data)}


def start_dir_from_argv(argv: list[str]) -> Path:
    """명령 인자의 ``--project-profile-path`` (``<root>/docs/PROJECT_PROFILE.md``)가 있으면 그 저장소, 없으면 cwd."""
    for i, arg in enumerate(argv):
        value = None
        if arg.startswith("--project-profile-path="):
            value = arg.split("=", 1)[1]
        elif arg == "--project-profile-path" and i + 1 < len(argv):
            value = argv[i + 1]
        if value:
            return Path(value).resolve().parent
    return Path.cwd()


def guard_command(command: str, argv: list[str]) -> int | None:
    """막을 명령이고 표식이 있으면 거절을 출력하고 종료 코드를 돌려준다. 아니면 ``None``."""
    if command not in GUARDED_COMMANDS:
        return None
    found = find_marker(start_dir_from_argv(argv))
    if found is None:
        return None
    payload = refusal(command, *found)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"ERROR: {payload['error']}", file=sys.stderr)
    return REFUSAL_EXIT
