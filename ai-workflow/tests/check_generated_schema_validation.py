#!/usr/bin/env python3
"""Validate output samples against the generated JSON Schema drafts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLES_DIR = REPO_ROOT / "ai-workflow" / "examples" / "output_samples"
README_PATH = SAMPLES_DIR / "README.md"
SCHEMA_PATH = REPO_ROOT / "ai-workflow" / "schemas" / "generated_output_schemas.json"
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+\.json)\)")

if str(REPO_ROOT / "ai-workflow") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "ai-workflow"))

from workflow_kit.common.output_contracts import detect_sample_family


def listed_sample_paths() -> list[Path]:
    text = README_PATH.read_text(encoding="utf-8")
    return [((README_PATH.parent / match.group(1).strip()).resolve()) for match in LINK_RE.finditer(text)]


def main() -> int:
    generated = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    families = generated["families"]
    failures: list[str] = []

    for path in listed_sample_paths():
        payload = json.loads(path.read_text(encoding="utf-8"))
        family = detect_sample_family(path)
        if not family:
            failures.append(f"Could not infer family for sample {path.relative_to(REPO_ROOT)}")
            continue
        schema = families.get(family)
        if schema is None:
            failures.append(f"Missing generated JSON Schema for family {family}")
            continue
        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
        for error in errors:
            location = ".".join(str(part) for part in error.absolute_path) or "<root>"
            failures.append(f"{path.relative_to(REPO_ROOT)} @ {location}: {error.message}")

    if failures:
        print("Generated schema validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Generated schema validation check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
