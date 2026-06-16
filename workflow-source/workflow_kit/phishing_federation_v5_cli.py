"""workflow_kit.phishing_federation_v5_cli - CLI for federation v5 (v0.7.51+).

ADR-023 follow-up: phishing federation v5 의 *CLI opt-in* 의 *operational* 보강.
- run_federation_v5_cli(argv) -> int
- Runs 3 source weighted voting (FREE tier: PhishTank + OpenPhish)
- Optional --phishtank-key=KEY + --min-confidence=0.0
- Prints JSON list of (url, confidence, source_names)

CLI 의 *federation v5* 의 *operational* 의 *low-friction* 정공법.
"""

from __future__ import annotations

import json
import sys


def run_federation_v5_cli(argv: list[str]) -> int:
    """Run federation v5 CLI from argv (v0.7.51+).

    Usage:
        python -m workflow_kit.phishing_federation_v5_cli --federate-v5 [--phishtank-key=KEY] [--min-confidence=0.0]

    Args:
        argv: list of CLI arguments (e.g. sys.argv[1:])

    Returns:
        Exit code (0 = success, 1 = error)
    """
    if "--federate-v5" not in argv:
        print("Usage: phishing_federation_v5_cli --federate-v5 [--phishtank-key=KEY] [--min-confidence=0.0]")
        return 1
    phishtank_key = None
    min_confidence = 0.0
    for arg in argv:
        if arg.startswith("--phishtank-key="):
            phishtank_key = arg.split("=", 1)[1]
        elif arg.startswith("--min-confidence="):
            try:
                min_confidence = float(arg.split("=", 1)[1])
            except ValueError:
                print(f"ERROR: invalid --min-confidence value", file=sys.stderr)
                return 1
    try:
        from workflow_kit.phishing_federation_v5 import (
            fetch_federated_phishing_urls_v5,
            build_default_sources_v5,
        )
        sources = build_default_sources_v5(phishtank_api_key=phishtank_key)
        result = fetch_federated_phishing_urls_v5(sources, min_confidence=min_confidence)
        # Convert to JSON-serializable list
        output = [
            {"url": url, "confidence": conf, "sources": srcs}
            for url, conf, srcs in result
        ]
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(run_federation_v5_cli(sys.argv[1:]))
