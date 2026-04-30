#!/usr/bin/env python3
"""Generate checked-in JSON Schema drafts from runtime output contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "ai-workflow") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "ai-workflow"))

from workflow_kit.common.output_contracts import output_json_schema_bundle


def main() -> int:
    print(json.dumps(output_json_schema_bundle(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
