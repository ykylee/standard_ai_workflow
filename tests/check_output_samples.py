#!/usr/bin/env python3
"""Validate JSON output samples referenced by the workflow kit docs."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = REPO_ROOT / "examples" / "output_samples"
README_PATH = SAMPLES_DIR / "README.md"
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+\.json)\)")


def listed_sample_paths() -> list[Path]:
    text = README_PATH.read_text(encoding="utf-8")
    results: list[Path] = []
    for match in LINK_RE.finditer(text):
        target = match.group(1).strip()
        results.append((README_PATH.parent / target).resolve())
    return results


def main() -> int:
    failures: list[str] = []
    listed = listed_sample_paths()
    if not listed:
        failures.append("No JSON sample links were found in examples/output_samples/README.md.")

    for path in listed:
        if not path.exists():
            failures.append(f"Missing listed sample: {path.relative_to(REPO_ROOT)}")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"Invalid JSON in {path.relative_to(REPO_ROOT)}: {exc}")
            continue
        if not isinstance(payload, dict):
            failures.append(f"Sample is not a JSON object: {path.relative_to(REPO_ROOT)}")

    if failures:
        print("Output sample check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"Output sample check passed for {len(listed)} JSON files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
