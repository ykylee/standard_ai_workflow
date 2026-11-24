"""허브로 옮긴 저장소의 진입 파일 판정 — 1.x 규칙 블록 대신 허브 렌더 영역이 규칙을 싣는다."""

from __future__ import annotations

from pathlib import Path

from workflow_kit.common.hub_marker import find_marker
from workflow_kit.hub import render


def hub_entry_problem(repo: Path, name: str, text: str) -> str | None:
    """``None`` 이면 이 파일은 허브 영역이 다스린다. 아니면 1.x 판정으로 가야 하는 까닭을 돌려준다."""
    if find_marker(repo) is None:
        return "표식 없음"
    region = render.find_region(text)
    if region is None:
        return "허브 영역 없음"
    if render.sha256(region.body) != region.sha:
        return "허브 영역이 손으로 바뀌었다"
    if "## Working Principles" in text or "## Memory Update Paths" in text:
        return "1.x 규칙 블록이 남아 있다"  # 두 규칙이 같이 있으면 어느 쪽이 정본인지 갈린다
    return None
