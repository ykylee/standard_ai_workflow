#!/usr/bin/env python3
"""apply_robust_patch CLI — dual mode wrapper for MCP `apply_robust_patch` tool.

SEARCH/REPLACE 블록 형식의 patch 를 파일에 적용. underlying 함수는
`apply_robust_patch_to_file()` (`workflow_kit.common.patching`) — MCP server 의
`apply_robust_patch` tool 이 *항상 apply* (dry-run 미지원). 본 CLI 는 `--apply` 가
*명시* 되어야만 patch 를 *적용*. default = dry-run (검증만, 파일 변경 ❌).

**dry-run 의 의의**: patch 가 *어디에* 매치되는지, *몇 개* 가 매치되는지, *모양* 이
맞는지 미리 확인. 적용은 *사용자 판단* 후 명시적으로.

## Patch 형식

```
<<<<<<< SEARCH
old text
=======
new text
>>>>>>> REPLACE
```

(여러 블록 가능, 순서대로 적용.)

## 사용법

```bash
# patch 파일 명시 + dry-run
python3 workflow-source/tools/apply_robust_patch.py --file-path foo.py --patch-file /tmp/patch.txt

# patch stdin
python3 workflow-source/tools/apply_robust_patch.py --file-path foo.py --patch-stdin < patch.txt

# 실제 적용
python3 workflow-source/tools/apply_robust_patch.py --file-path foo.py --patch-file /tmp/patch.txt --apply
```

Cross-ref: `core/multi_workspace_orchestration.md` §0.7 dual mode (TASK-017).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit import __version__ as TOOL_VERSION  # noqa: E402
from workflow_kit.common import patching  # noqa: E402


def _read_patch(args: argparse.Namespace) -> str:
    if args.patch_file:
        return Path(args.patch_file).read_text(encoding="utf-8")
    if args.patch_stdin:
        return sys.stdin.read()
    print("ERROR: --patch-file 또는 --patch-stdin 필요", file=sys.stderr)
    sys.exit(2)


def _print_human(payload: dict) -> None:
    status = payload.get("status", "?")
    if status == "ok":
        print(f"  ✓ {payload.get('message', 'applied')}")
        for b in payload.get("applied_blocks", []):
            mark = "✓" if b.get("matched") else "✗"
            print(f"    {mark} block {b.get('block_index')}: "
                  f"score={b.get('fuzzy_score')} preview={b.get('preview', '')[:60]!r}")
    else:
        print(f"  ✗ {status} ({payload.get('error_code', '?')}): {payload.get('error', '?')}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="apply SEARCH/REPLACE patch to a file (dual mode CLI)")
    p.add_argument("--file-path", required=True, help="patch 적용할 파일")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--patch-file", help="patch 내용 file")
    g.add_argument("--patch-stdin", action="store_true", help="stdin 으로 patch 받기")
    p.add_argument("--apply", action="store_true", help="실제 적용 (default: dry-run)")
    p.add_argument("--json", action="store_true", help="JSON 출력")
    args = p.parse_args(argv)

    patch_content = _read_patch(args)
    file_path = Path(args.file_path)

    # dry-run 모드: patching.apply_robust_patch_detailed 직접 호출 (MCP wrapper 는
    # dry_run 미지원). 동일 underlying 함수를 두 layer 가 모두 사용.
    success, message, applied_blocks = patching.apply_robust_patch_detailed(
        file_path=file_path,
        patch_content=patch_content,
        dry_run=not args.apply,
    )
    payload: dict = {
        "status": "ok" if success else "error",
        "tool_version": TOOL_VERSION,
        "file_path": str(file_path),
        "message": message,
        "patches_applied": sum(1 for b in applied_blocks if b.get("matched")),
        "patches_failed": sum(1 for b in applied_blocks if not b.get("matched")),
        "dry_run": not args.apply,
        "applied_blocks": applied_blocks,
        "warnings": [],
    }
    if not success:
        payload["error"] = message
        payload["error_code"] = "apply_robust_patch_runtime_error"
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_human(payload)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
