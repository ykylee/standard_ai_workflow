#!/usr/bin/env python3
"""check_quickstart_stale_links CLI — dual mode wrapper for MCP `check_quickstart_stale_links` tool.

QUICKSTART 문서(들) 의 *상대 링크 무결성* + *핵심 진입 문서* (project_profile_path /
session_handoff_path / work_backlog_index_path / agents_path) 가 quickstart 에서
*직접 가리키는지* 확인. **read-only** — 변경 없음. *--apply* 불필요.

underlying 함수는 `check_quickstart_stale_links_payload()` — MCP server 동명 tool
과 같은 함수. 본 CLI 는 *운영자 수동* / *CI smoke* 용으로 *직접* 부른다.

## 사용법

```bash
# 단일 quickstart
python3 workflow-source/tools/check_quickstart_stale_links.py --quickstart-path QUICKSTART.md

# multi
python3 workflow-source/tools/check_quickstart_stale_links.py \
    --quickstart-path QUICKSTART.md --quickstart-path docs/index.md

# 핵심 진입 문서 명시 (default: 자동 detect, REPO_ROOT 기준)
python3 workflow-source/tools/check_quickstart_stale_links.py \
    --quickstart-path QUICKSTART.md \
    --project-profile-path docs/PROJECT_PROFILE.md \
    --session-handoff-path ai-workflow/memory/active/main/session_handoff.md \
    --work-backlog-index-path ai-workflow/memory/active/main/backlog/2026-08-08.md \
    --agents-path AGENTS.md

# JSON
python3 workflow-source/tools/check_quickstart_stale_links.py --quickstart-path QUICKSTART.md --json
```

Cross-ref: `core/multi_workspace_orchestration.md` §0.7 dual mode (TASK-017).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit import __version__ as TOOL_VERSION  # noqa: E402
from workflow_kit.common.paths import memory_active_dir  # noqa: E402
from workflow_kit.common.read_only_bundle import (  # noqa: E402
    check_quickstart_stale_links_payload,
)


def _default_target(label: str) -> str | None:
    """REPO_ROOT 기준 default path. 부재 시 None."""
    candidates = {
        "project_profile": REPO_ROOT / "docs" / "PROJECT_PROFILE.md",
        "session_handoff": memory_active_dir(REPO_ROOT) / "main" / "session_handoff.md",
        "work_backlog": next(
            (memory_active_dir(REPO_ROOT) / "main" / "backlog").glob("*.md"),
            None,
        ) if (memory_active_dir(REPO_ROOT) / "main" / "backlog").is_dir() else None,
        "agents": REPO_ROOT / "AGENTS.md",
    }
    p = candidates.get(label)
    if p is None:
        return None
    if not p.exists():
        return None
    return str(p)


def _print_human(payload: dict) -> None:
    print(f"  status: {payload.get('status')}")
    for w in payload.get("stale_link_warnings", []):
        print(f"  ⚠️  {w}")
    for entry in payload.get("broken_links", []):
        for link in entry.get("broken_links", []):
            print(f"  ✗ broken: {entry.get('path')} → {link}")
    for entry in payload.get("missing_expected_links", []):
        for tgt in entry.get("missing_targets", []):
            print(f"  ✗ missing: {entry.get('path')} → {tgt}")
    if not payload.get("broken_links") and not payload.get("missing_expected_links"):
        print("  ✓ no stale links")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="check quickstart stale links (dual mode CLI)")
    p.add_argument("--quickstart-path", action="append", required=True, help="검증할 QUICKSTART (multi)")
    p.add_argument("--project-profile-path", default=_default_target("project_profile"))
    p.add_argument("--session-handoff-path", default=_default_target("session_handoff"))
    p.add_argument("--work-backlog-index-path", default=_default_target("work_backlog"))
    p.add_argument("--agents-path", default=_default_target("agents"))
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    payload = check_quickstart_stale_links_payload(
        quickstart_paths=list(args.quickstart_path),
        project_profile_path=args.project_profile_path,
        session_handoff_path=args.session_handoff_path,
        work_backlog_index_path=args.work_backlog_index_path,
        agents_path=args.agents_path,
        tool_version=TOOL_VERSION,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_human(payload)
    # broken_links / missing_expected_links 가 있으면 non-zero
    return 0 if not (payload.get("broken_links") or payload.get("missing_expected_links")) else 1


if __name__ == "__main__":
    sys.exit(main())
