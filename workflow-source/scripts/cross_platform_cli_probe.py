#!/usr/bin/env python3
"""wk CLI 의 cross-platform 핵심 경로 probe (TASK-2026-08-12-main-005).

## 왜 필요한가

전량 smoke 251개는 Linux CI + darwin homelab 에서만 돌았다 — Windows 는
**로컬에 없는 축**이라 아무도 잰 적이 없다 (darwin `/private` symlink 4건과
같은 계열: 그 축이 생기기 전에는 영영 안 드러난다). 이 probe 는 CI 의
`windows-latest` / `macos-latest` 에서 pip 로 설치된 kit 의 **소비자 표면**
(wk 핵심 명령 + MCP 브리지 기동) 을 실측한다.

전량 smoke 의 이식은 별건이다 — 여기서는 "소비자가 설치해서 부르는 경로가
그 OS 에서 사는가" 만 판정한다 (지원 tier: Linux/macOS = 전량, Windows = 본 probe).

Stdlib only. 실패한 probe 는 이름과 출력 꼬리를 남기고 exit 1.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

FIXTURE_BRANCH = "main"


def _fixture_workspace(root: Path) -> Path:
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "PROJECT_PROFILE.md").write_text("# profile\n", encoding="utf-8")
    branch = root / "ai-workflow" / "memory" / "active" / FIXTURE_BRANCH
    (branch / "backlog" / "tasks").mkdir(parents=True)
    (branch / "sessions").mkdir(parents=True)
    (branch / "session_handoff.md").write_text(
        "# Session Handoff\n\n"
        "## 1. 현재 작업 요약\n\n- 현재 기준선: probe baseline\n\n"
        "## 2. 진행 중 작업\n\n- 현재 `in_progress` 작업:\n-\n\n"
        "## 3. 차단 작업\n\n- 현재 `blocked` 작업:\n-\n\n"
        "## 4. 최근 완료 작업\n\n- 최근 완료 작업 목록:\n-\n",
        encoding="utf-8",
    )
    (branch / "backlog" / "2026-01-01.md").write_text(
        "# Backlog Index — 2026-01-01\n\n## Tasks\n\n"
        "- **TASK-2026-01-01-main-001** [generic] probe task\n"
        "  - path: [`./tasks/TASK-2026-01-01-main-001.md`](./tasks/TASK-2026-01-01-main-001.md)\n"
        "  - status: planned\n",
        encoding="utf-8",
    )
    (branch / "backlog" / "tasks" / "TASK-2026-01-01-main-001.md").write_text(
        "---\nid: TASK-2026-01-01-main-001\nstatus: planned\ncreated_at: 2026-01-01\n"
        "source_anchor: generic-task-2026-01-01-main-001\nsource_path: backlog/2026-01-01.md\n"
        "kind: generic\n---\n\n# TASK-2026-01-01-main-001 — probe task\n",
        encoding="utf-8",
    )
    return root


def main() -> int:
    env = dict(os.environ)
    # Windows 콘솔 기본 인코딩(cp125x)에서 한국어 출력이 죽지 않도록.
    env.setdefault("PYTHONUTF8", "1")
    env["CODEX_WORKFLOW_BRANCH"] = FIXTURE_BRANCH

    wk = [sys.executable, "-m", "workflow_kit.workflow_kit_cli"]
    failures: list[str] = []
    ran = 0

    with tempfile.TemporaryDirectory(prefix="wk-xplat-") as tmp:
        ws = _fixture_workspace(Path(tmp).resolve())

        def probe(label: str, cmd: list[str], *, cwd: Path | None = None,
                  expect_rc: int = 0, expect_stdout: str | None = None) -> None:
            nonlocal ran
            ran += 1
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=180,
                cwd=str(cwd) if cwd else None, env=env, encoding="utf-8", errors="replace",
            )
            ok = proc.returncode == expect_rc
            if ok and expect_stdout is not None:
                ok = expect_stdout in proc.stdout
            if ok:
                print(f"PASS: {label}")
            else:
                print(f"FAIL: {label} — rc={proc.returncode}\n"
                      f"  stdout: {proc.stdout[-400:]}\n  stderr: {proc.stderr[-400:]}")
                failures.append(label)

        probe("1) wk --help (dispatcher)", [*wk, "--help"], expect_stdout="session-start")
        probe("2) wk workspace-registry host-id", [*wk, "workspace-registry", "host-id"])
        probe("3) wk session-start (무인자, workspace 자동 탐색)",
              [*wk, "session-start"], cwd=ws, expect_stdout='"status"')
        probe("4) wk refresh-state (생성)", [*wk, "refresh-state"], cwd=ws,
              expect_stdout='"refreshed"')
        probe("5) wk refresh-state --check (무drift)", [*wk, "refresh-state", "--check"],
              cwd=ws, expect_stdout='"drift": false')
        probe("6) wk backlog-update (draft, 무-apply)",
              [*wk, "backlog-update", "--project-profile-path", str(ws / "docs" / "PROJECT_PROFILE.md"),
               "--task-name", "probe", "--task-brief", "cross-platform probe",
               "--target-date", "2026-01-01"], cwd=ws, expect_stdout='"draft_entry"')
        probe("7) MCP jsonrpc bridge initialize (read-only bundle)",
              [sys.executable, "-m", "workflow_kit.server.read_only_jsonrpc",
               "--request-json", json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
               "--bundle", "read-only"],
              expect_stdout="workflow_read_only_bundle")
        probe("8) wk host-serve-registry --check (bind 없이 설정 검증)",
              [*wk, "host-serve-registry", "--check", "--json"], expect_stdout='"ok": true')

    print()
    if failures:
        print(f"{ran - len(failures)}/{ran} PASS — FAILED: {failures}")
        return 1
    print(f"{ran}/{ran} PASS ({sys.platform})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
