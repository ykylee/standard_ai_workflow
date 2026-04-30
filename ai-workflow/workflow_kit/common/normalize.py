"""Normalization helpers shared across workflow kit scripts."""

from __future__ import annotations


def normalize_whitespace(value: str) -> str:
    return " ".join(value.strip().split())


def normalize_backticked(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith("`") and normalized.endswith("`"):
        normalized = normalized[1:-1].strip()
    return normalize_whitespace(normalized)


def dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = normalize_whitespace(item)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def dedupe_normalized_backticked(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = normalize_backticked(item)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result

