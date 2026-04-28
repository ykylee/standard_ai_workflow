"""Document metadata helpers for workflow kit scripts."""

from __future__ import annotations

import itertools
from pathlib import Path


REQUIRED_METADATA_FIELDS = [
    "문서 목적",
    "범위",
    "대상 독자",
    "상태",
    "최종 수정일",
    "관련 문서",
]


def missing_metadata_fields(path: Path, required_fields: list[str] | None = None) -> list[str]:
    fields = required_fields or REQUIRED_METADATA_FIELDS
    with path.open(encoding="utf-8") as f:
        lines = [line.rstrip("\r\n") for line in itertools.islice(f, 20)]

    missing: list[str] = []
    for field in fields:
        prefix = f"- {field}:"
        if not any(line.startswith(prefix) for line in lines):
            missing.append(field)
    if not lines or not lines[0].startswith("# "):
        missing.append("제목 헤더")
    return missing

