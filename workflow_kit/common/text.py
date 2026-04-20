"""Text parsing helpers shared across workflow kit prototypes."""

from __future__ import annotations

from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def iter_lines(path: Path) -> list[str]:
    return read_text(path).splitlines()


def normalize_inline_code(value: str) -> str:
    normalized = value.strip()
    while normalized.startswith("`"):
        normalized = normalized[1:].strip()
    while normalized.endswith("`"):
        normalized = normalized[:-1].strip()
    return normalized


def extract_section_value(lines: list[str], label: str) -> str | None:
    prefix = f"- {label}:"
    for idx, line in enumerate(lines):
        if line.strip() == prefix and idx + 1 < len(lines):
            value = lines[idx + 1].strip()
            if value.startswith("- "):
                value = value[2:].strip()
            return normalize_inline_code(value)
    return None


def extract_list_after_label(lines: list[str], label: str) -> list[str]:
    prefix = f"- {label}:"
    results: list[str] = []
    capture = False
    for line in lines:
        stripped = line.strip()
        if stripped == prefix:
            capture = True
            continue
        if capture:
            if stripped.startswith("## "):
                break
            if stripped.startswith("- "):
                results.append(normalize_inline_code(stripped[2:].strip()))
            elif stripped:
                break
    return results


def extract_named_section_bullets(lines: list[str], title: str) -> list[str]:
    heading = f"## {title}"
    collecting = False
    items: list[str] = []
    for line in lines:
        stripped = line.rstrip()
        if stripped.startswith("## "):
            if collecting:
                break
            collecting = stripped == heading
            continue
        if not collecting:
            continue
        if stripped.startswith("- "):
            value = normalize_inline_code(stripped[2:].strip())
            if value.endswith(":"):
                continue
            items.append(value)
    return items

