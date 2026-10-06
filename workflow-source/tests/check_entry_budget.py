#!/usr/bin/env python3
"""bootstrap 이 생성하는 하네스 진입점의 분량 예산 (TASK-2026-10-06-main-003, 진입점 다이어트 2).

진입점(CLAUDE.md · AGENTS.md · GROK.md …)은 세션마다 통째로 컨텍스트에 실린다. 2026-10-06 신규
bootstrap 실측은 CLAUDE.md 7,758B · AGENTS.md 7,044B · GROK.md 10,532B 였다. 공유 절을
`bootstrap_lib/harnesses/entry_sections.py` 로 모으고 줄인 뒤, 그 상태를 이 검사로 고정한다.

1. 모든 하네스(`SUPPORTED_HARNESSES`)를 신규 bootstrap 해 registry 가 선언한 `.md` 진입점이
   `ENTRY_BUDGET_BYTES` 이하다. 선언됐는데 생성되지 않은 진입점은 실패다 (미측정은 통과가 아니다).
2. 공유 절의 옛 사본이 렌더러로 돌아오지 않는다 — 옛 문안 표식이 렌더러 소스에 0건.
3. "Read these first" · 언어 절을 가진 진입점은 공유 정본 문안을 그대로 싣는다.
"""
from __future__ import annotations

WATCHES = (
    "workflow-source/workflow_kit/*",
    # bootstrap 이 문서 템플릿을 읽어 산출물을 만든다.
    "workflow-source/templates/*",
    "workflow-source/core/global_workflow_standard.md",
    "workflow-source/pyproject.toml",
)

#: 하네스 12개를 각각 bootstrap 한다.
CHECK_TIMEOUT_S = 150

import os
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.bootstrap_lib.harnesses import HARNESS_SPECS, SUPPORTED_HARNESSES  # noqa: E402
from workflow_kit.bootstrap_lib.harnesses.entry_sections import (  # noqa: E402
    ENTRY_BUDGET_BYTES,
    language_section,
    read_first_section,
)

RENDERERS = SOURCE_ROOT / "workflow_kit" / "bootstrap_lib" / "harnesses" / "renderers.py"

#: 공유 절로 옮기기 전의 옛 문안 표식. 하나라도 렌더러에 다시 생기면 사본이 돌아온 것이다.
OLD_COPY_MARKERS = (
    "is a meta layer for session restore and workflow state",
    "Write user-facing work reports, status summaries",
    "## What this file is for",
    "## self-bootstrap (when PURPOSE.md / state.json are absent)",
    "Splitting per branch keeps concurrent work from overwriting itself",
)

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail else ''}")


def _bootstrap_all(root: Path) -> dict[str, tuple[int, str]]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SOURCE_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    results: dict[str, tuple[int, str]] = {}
    for name in SUPPORTED_HARNESSES:
        target = root / name
        target.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(target), check=False,
                       capture_output=True)
        proc = subprocess.run(
            [sys.executable, "-m", "workflow_kit.bootstrap_lib", "--target-root", str(target),
             "--adoption-mode", "new", "--harness", name, "--project-slug", "demo",
             "--project-name", "Demo"],
            capture_output=True, encoding="utf-8", errors="replace", env=env, timeout=120, check=False,
        )
        results[name] = (proc.returncode, proc.stderr[-300:])
    return results


_MEASURED: dict[str, int] = {}
_TEXTS: dict[str, str] = {}


def case_1_every_entry_within_budget() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for name, (rc, err) in _bootstrap_all(root).items():
            if rc != 0:
                problems.append(f"{name}: bootstrap rc={rc} {err!r}")
                continue
            for entry in HARNESS_SPECS[name].entry_files:
                if not entry.endswith(".md"):
                    continue
                path = root / name / entry
                if not path.is_file():
                    problems.append(f"{name}: 선언된 진입점 {entry} 가 생성되지 않았다")
                    continue
                text = path.read_text(encoding="utf-8")
                size = len(text.encode("utf-8"))
                _MEASURED[f"{name}:{entry}"] = size
                _TEXTS[f"{name}:{entry}"] = text
                if size > ENTRY_BUDGET_BYTES:
                    problems.append(f"{name}:{entry} {size}B > {ENTRY_BUDGET_BYTES}B")
    largest = max(_MEASURED.items(), key=lambda kv: kv[1]) if _MEASURED else ("-", 0)
    ok = not problems and len(_MEASURED) >= 5
    _record(f"case 1 (생성 진입점 {len(_MEASURED)}개가 예산 {ENTRY_BUDGET_BYTES}B 이하)", ok,
            f"최대 {largest[0]} {largest[1]}B" + (f" · {problems[:4]}" if problems else ""))


def _entry_renderer_sources() -> dict[str, str]:
    """진입점을 그리는 함수(`render_*_agents` · `render_aider_conventions`)의 본문.

    스킬 렌더러(codewhale · custom)는 스킬 맥락에 맞춘 변형을 갖는다 — 그쪽은 진입점이 아니라
    세션마다 실리지 않으므로 범위 밖이다.
    """
    import ast

    source = RENDERERS.read_text(encoding="utf-8")
    tree = ast.parse(source)
    return {
        node.name: ast.get_source_segment(source, node) or ""
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and (node.name.endswith("_agents") or node.name == "render_aider_conventions")
    }


def case_2_no_old_copies_in_renderers() -> None:
    sources = _entry_renderer_sources()
    hits = [f"{name}: {m}" for name, body in sources.items() for m in OLD_COPY_MARKERS if m in body]
    _record(f"case 2 (진입점 렌더러 {len(sources)}개에 공유 절의 옛 사본이 없다)",
            not hits and len(sources) >= 6, f"남은 표식: {hits}")


def case_3_entries_carry_shared_sections() -> None:
    base_read_first = read_first_section().split("\n", 2)[2]  # 제목 · 빈 줄 뒤 정본 bullet
    language = language_section()
    problems: list[str] = []
    checked = 0
    for key, text in _TEXTS.items():
        if "## Read these first" in text:
            checked += 1
            if base_read_first not in text:
                problems.append(f"{key}: Read these first 가 정본 문안이 아니다")
        if "## Language and context principles" in text:
            checked += 1
            if language not in text:
                problems.append(f"{key}: 언어 절이 정본 문안이 아니다")
    _record(f"case 3 (공유 절 {checked}곳이 정본 문안을 싣는다)", not problems and checked >= 5,
            "; ".join(problems[:4]))


def main() -> int:
    print("=== 진입점 분량 예산 (TASK-2026-10-06-main-003) ===")
    for fn in (case_1_every_entry_within_budget,
               case_2_no_old_copies_in_renderers,
               case_3_entries_carry_shared_sections):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            _record(fn.__name__, False, f"{type(exc).__name__}: {str(exc)[:300]}")
    for key, size in sorted(_MEASURED.items(), key=lambda kv: -kv[1]):
        print(f"    {size:6d}B  {key}")
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
