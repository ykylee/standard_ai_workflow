"""workflow_kit.v_r13_layer2_cli - CLI for V-R13 layer 2 one-call URL verification (v0.7.50+).

ADR-019 + ADR-023 follow-up: V-R13 layer 2 pipeline 의 *CLI opt-in* 의 *operational* 보강.
- run_layer2_cli(argv) -> int: parses argv for --layer2 flag, runs pipeline
- Prints PipelineResult.to_dict() as JSON
- Exits 0 on success, 1 on error

CLI surface 의 *one-call* 의 *operational* 의 *low-friction* 정공법.
"""

from __future__ import annotations

import json
import sys


def run_layer2_cli(argv: list[str]) -> int:
    """Run V-R13 layer 2 CLI from argv (v0.7.50+).

    Usage:
        python -m workflow_kit.v_r13_layer2_cli --layer2 URL [--user=USER --token=TOKEN]

    Args:
        argv: list of CLI arguments (e.g. sys.argv[1:])

    Returns:
        Exit code (0 = success, 1 = error)
    """
    if "--layer2" not in argv:
        print("Usage: v_r13_layer2_cli --layer2 URL [--user=USER --token=TOKEN]")
        return 1
    # Find URL (first non-flag arg after --layer2)
    url = None
    user = None
    token = None
    for i, arg in enumerate(argv):
        if arg == "--layer2":
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                url = argv[i + 1]
        elif arg.startswith("--user="):
            user = arg.split("=", 1)[1]
        elif arg.startswith("--token="):
            token = arg.split("=", 1)[1]
    if url is None:
        print("ERROR: --layer2 requires a URL argument", file=sys.stderr)
        return 1
    try:
        from workflow_kit.v_r13_layer2_pipeline import run_layer2_pipeline
        result = run_layer2_pipeline(url, user=user, token=token)
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(run_layer2_cli(sys.argv[1:]))
