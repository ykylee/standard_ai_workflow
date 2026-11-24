"""지침 렌더링 — 표준 규칙 층(2.0) + 프로젝트 지침 층 → 하네스별 진입 파일 렌더 영역 (hub_spec §5.2 · §6.5).

렌더 영역::

    <!-- workflow-hub:begin project=P-… guide=<kit판>+p<프로젝트 판> sha256=<영역 본문 해시> -->
    …본문…
    <!-- workflow-hub:end -->

- 영역 밖은 건드리지 않는다.
- 다시 쓰기 전에 지금 영역 본문의 해시를 머리의 ``sha256`` 과 대조한다 — 다르면 쓰지 않고
  ``local_edit_detected`` 로 멈춘다 (요구 R7.5).
- 표준 규칙 층의 정본은 ``core/hub_workflow_standard.md`` 의 ``hub-standard`` 표식 사이다 (DS6).
  wheel 에는 ``core/`` 가 없으므로 :mod:`workflow_kit.hub._standard_snapshot` 을 읽는다 —
  ``python -m workflow_kit.hub.render --write-snapshot`` 으로 생성하고 검사가 일치를 강제한다.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from workflow_kit.hub import KIT_COMPAT_VERSION as KIT_VERSION
from workflow_kit.bootstrap_lib.harnesses import spec_for
from workflow_kit.bootstrap_lib.harnesses.entry_sections import ENTRY_BUDGET_BYTES
from workflow_kit.hub.errors import HubError

#: 지원 하네스 4종 — 이 목록 하나에서 렌더 대상 · 안내 페이지 · 실측 대상이 파생된다 (요구 R2.8, Q8).
SUPPORTED_HARNESSES: tuple[str, ...] = ("claude-code", "codex", "minimax-code", "antigravity")

BEGIN_RE = re.compile(
    r"<!-- workflow-hub:begin project=(?P<project>\S+) guide=(?P<guide>\S+) sha256=(?P<sha>[0-9a-f]{64}) -->\n"
)
END_MARK = "<!-- workflow-hub:end -->"
_STD_RE = re.compile(r"<!-- hub-standard:begin -->\n(?P<body>.*?)<!-- hub-standard:end -->", re.S)

_CORE_PATH = Path(__file__).resolve().parents[2] / "core" / "hub_workflow_standard.md"


def standard_block_from_core(path: Path = _CORE_PATH) -> str:
    m = _STD_RE.search(path.read_text(encoding="utf-8"))
    if not m:
        raise RuntimeError(f"{path} 에 hub-standard 표식이 없다")
    return m.group("body")


def standard_block() -> str:
    from workflow_kit.hub._standard_snapshot import STANDARD_BLOCK

    return STANDARD_BLOCK


def entry_file(harness: str) -> str:
    if harness not in SUPPORTED_HARNESSES:
        raise HubError(400, "unsupported_harness",
                       f"지원 하네스가 아니다: {harness!r} — {', '.join(SUPPORTED_HARNESSES)} (요구 R2.8)",
                       {"supported": list(SUPPORTED_HARNESSES)})
    files = spec_for(harness).entry_files
    if not files:
        raise RuntimeError(f"하네스 표에 {harness} 의 진입 파일이 없다")
    return files[0]


def guide_version(project_version: int) -> str:
    return f"{KIT_VERSION}+p{project_version}"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Region:
    start: int
    end: int
    project: str
    guide: str
    sha: str
    body: str


def find_region(text: str) -> Region | None:
    m = BEGIN_RE.search(text)
    if not m:
        return None
    end = text.find(END_MARK, m.end())
    if end < 0:
        return None
    stop = end + len(END_MARK)
    if text[stop:stop + 1] == "\n":
        stop += 1
    return Region(m.start(), stop, m.group("project"), m.group("guide"), m.group("sha"), text[m.end():end])


def render_body(harness: str, project_display: str, project_guide: str) -> str:
    entry = entry_file(harness)
    parts = [
        f"<!-- 이 영역은 워크플로우 허브가 렌더링한다 ({entry} · {harness}). 고칠 것은 허브에 지침 제안으로. -->\n",
        standard_block(),
    ]
    if project_guide.strip():
        parts.append(f"\n## 프로젝트 지침 — {project_display}\n\n{project_guide.strip()}\n")
    return "".join(parts)


def render_region(harness: str, project_id: str, project_display: str, project_guide: str,
                  project_version: int) -> tuple[str, str]:
    """(영역 문자열, 지침 판). 예산을 넘으면 거절한다 (요구 R7.2)."""
    body = render_body(harness, project_display, project_guide)
    version = guide_version(project_version)
    region = f"<!-- workflow-hub:begin project={project_id} guide={version} sha256={sha256(body)} -->\n{body}{END_MARK}\n"
    size = len(region.encode("utf-8"))
    if size > ENTRY_BUDGET_BYTES:
        raise HubError(422, "entry_budget_exceeded",
                       f"{entry_file(harness)} 렌더 영역 {size}B > 예산 {ENTRY_BUDGET_BYTES}B — 프로젝트 지침을 줄인다",
                       {"size": size, "budget": ENTRY_BUDGET_BYTES})
    return region, version


def merge_into(existing: str | None, region: str) -> tuple[str | None, str | None]:
    """기존 파일에 영역을 넣은 새 내용. ``(새 내용, None)`` 또는 ``(None, 멈춘 사유)``.

    영역이 있으면 그 자리를 바꾸고, 없으면 파일 끝에 붙인다. 영역 본문이 머리의 해시와
    다르면(로컬에서 고침) 바꾸지 않는다.
    """
    text = existing or ""
    found = find_region(text)
    if found is None:
        if "workflow-hub:begin" in text:
            return None, "local_edit_detected"  # 머리가 깨졌거나 끝 표식이 없다 — 손으로 고친 것
        sep = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        return text + sep + region, None
    if sha256(found.body) != found.sha:
        return None, "local_edit_detected"
    return text[:found.start] + region + text[found.end:], None


def write_snapshot() -> Path:
    block = standard_block_from_core()
    target = Path(__file__).with_name("_standard_snapshot.py")
    target.write_text(
        '"""허브 표준 규칙 층의 **생성된 스냅샷** — 직접 고치지 않는다.\n\n'
        "생성: ``python -m workflow_kit.hub.render --write-snapshot``\n"
        "정본: ``core/hub_workflow_standard.md`` 의 ``hub-standard`` 표식 사이\n"
        "검증: ``tests/check_hub_bootstrap.py``\n\n"
        "wheel 에는 ``core/`` 가 없어서 허브가 이 사본을 읽는다.\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        f"STANDARD_BLOCK = {block!r}\n",
        encoding="utf-8",
    )
    return target


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workflow_kit.hub.render")
    p.add_argument("--write-snapshot", action="store_true")
    a = p.parse_args(argv)
    if a.write_snapshot:
        print(write_snapshot())
        return 0
    p.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
