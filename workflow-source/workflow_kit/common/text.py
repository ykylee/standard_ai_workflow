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


def extract_section_value(lines: list[str], label: str | tuple[str, ...]) -> str | None:
    """`- <label>:` 줄의 값을 뽑는다. label 을 여러 개 주면 **먼저 맞는 것**을 쓴다.

    2026-08-14: 진입점·산출물 문안이 영어로 옮겨지며 같은 필드가 두 라벨을 갖게 됐다.
    한쪽만 보면 아직 한국어인 문서(소비자 저장소의 기존 산출물)에서 조용히 `None` 이
    되고, 그 `None` 은 예외가 아니라 **빈 값**으로 흘러간다. 그래서 둘 다 받는다.
    """
    labels = (label,) if isinstance(label, str) else label
    for one in labels:
        found = _extract_one(lines, one)
        if found is not None:
            return found
    return None


def _extract_one(lines: list[str], label: str) -> str | None:
    prefix = f"- {label}:"
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(prefix):
            # 인라인 값 확인 (예: - 레이블: 값)
            value_part = stripped[len(prefix):].strip()
            if value_part:
                return normalize_inline_code(value_part)

            # 다음 줄 값 확인 (예: - 레이블:\n  - 값)
            if idx + 1 < len(lines):
                next_val = lines[idx + 1].strip()
                if next_val.startswith("- "):
                    next_val = next_val[2:].strip()
                if next_val:
                    return normalize_inline_code(next_val)
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

