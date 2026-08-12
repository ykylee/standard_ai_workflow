#!/usr/bin/env python3
"""create_environment_record_stub CLI — dual mode wrapper for MCP `create_environment_record_stub` tool.

`ai-workflow/memory/active/environments/<hostname>/record.md` 의 *stub* (초안) 을
생성. underlying 함수는 `create_environment_record_stub_payload()` — MCP server 의
동명 tool 이 *draft_record* (string list) 를 반환. 본 CLI 는 그 draft 를
*stdout / --output-path 파일* 로 emit. **default = stdout (파일 변경 ❌)**.

## 사용법

```bash
# stdout 으로 draft 출력 (default)
python3 workflow-source/tools/create_environment_record_stub.py

# 자동 detect (hostname, os_type) override
python3 workflow-source/tools/create_environment_record_stub.py --hostname myhost --os-type Linux

# 파일로 직접 emit
python3 workflow-source/tools/create_environment_record_stub.py --output-path environments/myhost/record.md
```

Cross-ref: `core/multi_workspace_orchestration.md` §0.7 dual mode (TASK-017).
"""

from __future__ import annotations

import argparse
import json
import platform
import socket
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit import __version__ as TOOL_VERSION  # noqa: E402
from workflow_kit.common.read_only_bundle import (  # noqa: E402
    create_environment_record_stub_payload,
)


def _detect_hostname() -> str:
    try:
        return socket.gethostname()
    except OSError:
        return "unknown"


def _detect_os_type() -> str:
    return platform.system()  # "Darwin" / "Linux" / "Windows"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="create environment record stub (dual mode CLI)")
    p.add_argument("--hostname", default=_detect_hostname(), help="호스트명 (default: 자동 detect)")
    p.add_argument("--os-type", default=_detect_os_type(), help="OS 유형 (default: 자동 detect)")
    p.add_argument("--output-path", type=Path, help="파일로 emit (default: stdout)")
    p.add_argument("--json", action="store_true", help="JSON envelope + draft_record 출력")
    args = p.parse_args(argv)

    payload = create_environment_record_stub_payload(
        hostname=args.hostname,
        os_type=args.os_type,
        tool_version=TOOL_VERSION,
    )
    draft = payload.get("draft_record", [])

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if args.output_path:
        args.output_path.parent.mkdir(parents=True, exist_ok=True)
        args.output_path.write_text("\n".join(draft) + "\n", encoding="utf-8")
        print(f"  ✓ written: {args.output_path} ({len(draft)} lines)", file=sys.stderr)
    else:
        for line in draft:
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
