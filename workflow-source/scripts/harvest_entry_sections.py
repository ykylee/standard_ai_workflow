#!/usr/bin/env python3
"""과거 kit 버전이 생성한 진입점 절을 채취해 `_entry_known_sections.py` 를 만든다.

TASK-2026-10-06-main-004 (진입점 다이어트 3). `common/entry_diet.py` 는 기존 진입점의 절이
"과거 kit 가 생성한 그대로" 인지를 해시로 판정한다. 그 해시를 손으로 적으면 어느 버전의 무엇인지
아무도 모른다 — 그래서 **발행 태그를 실제로 bootstrap 한 출력**에서 채취한다.

각 ref 를 분리 worktree 로 꺼내 모든 하네스를 신규 bootstrap 하고, 루트 `*.md` 진입점(README 제외)과
`.aider/*.md` 의 `## ` 절 본문을 정규화(공백 묶음 → 한 칸)해 SHA-256 앞 16자로 모은다.
저장소 작업 트리는 건드리지 않는다.

    python3 workflow-source/scripts/harvest_entry_sections.py --tmp-dir <실디스크경로> --apply

ref 를 늘리면(새 발행) 다시 돌린다 — 현행 템플릿이 바뀐 발행 뒤에 돌리지 않으면, 그 발행으로
만든 진입점의 절은 '알려진 생성물' 로 인식되지 않아 다이어트에서 보수적으로 남는다(해롭지 않다).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "workflow-source" / "workflow_kit" / "common" / "_entry_known_sections.py"

#: 채취 대상 ref. `workflow_kit.bootstrap_lib` 네임스페이스(2026-08-12) 이후의 발행 태그를 고르고,
#: 한국어 템플릿의 마지막 상태(영어 전환 4054dccc 직전 825478bc)와 다이어트 직전(062c4d64)을 더했다.
DEFAULT_REFS = (
    "v1.2.0-beta", "825478bc", "v1.3.0", "v1.5.0", "v1.7.0", "v1.9.4", "v1.12.0",
    "v1.14.4", "v1.16.0", "v1.19.0", "062c4d64",
)
HARNESSES = ("codex", "opencode", "pi-dev", "antigravity", "minimax-code", "claude-code",
             "aider", "goose", "grok-build", "gemini-cli", "codewhale", "custom", "mavis")


def _hash(body: str) -> str:
    return hashlib.sha256(" ".join(body.split()).encode("utf-8")).hexdigest()[:16]


def _sections(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, list[str]]] = []
    for line in text.split("\n"):
        if line.startswith("## "):
            out.append((line[3:].strip(), []))
        elif out:
            out[-1][1].append(line)
    return [(title, "\n".join(body)) for title, body in out]


def harvest(refs: tuple[str, ...], tmp: Path) -> tuple[dict[str, set[str]], list[str]]:
    known: dict[str, set[str]] = {}
    log: list[str] = []
    for ref in refs:
        wt = tmp / f"wt-{ref}"
        subprocess.run(["git", "-C", str(REPO), "worktree", "add", "--detach", "-q", str(wt), ref],
                       check=True, capture_output=True)
        try:
            env = {**os.environ, "PYTHONPATH": str(wt / "workflow-source")}
            ok = 0
            for harness in HARNESSES:
                target = Path(tempfile.mkdtemp(dir=tmp))
                subprocess.run(["git", "init", "-q", "-b", "main"], cwd=target, capture_output=True)
                proc = subprocess.run(
                    [sys.executable, "-m", "workflow_kit.bootstrap_lib", "--target-root", str(target),
                     "--adoption-mode", "new", "--harness", harness, "--project-slug", "demo",
                     "--project-name", "Demo"],
                    cwd=target, env=env, capture_output=True, encoding="utf-8", errors="replace", check=False,
                )
                if proc.returncode == 0:
                    ok += 1
                    for path in sorted([*target.glob("*.md"), *target.glob(".aider/*.md")]):
                        if path.name == "README.md":
                            continue
                        for title, body in _sections(path.read_text(encoding="utf-8")):
                            known.setdefault(title, set()).add(_hash(body))
                shutil.rmtree(target, ignore_errors=True)
            log.append(f"{ref}: bootstrap {ok}/{len(HARNESSES)}")
        finally:
            subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", str(wt)], capture_output=True)
    return known, log


def render_module(known: dict[str, set[str]], refs: tuple[str, ...], log: list[str]) -> str:
    lines = [
        '"""과거 kit 버전이 생성한 진입점 절의 해시 — **생성물, 직접 고치지 않는다.**',
        "",
        "생성: ``python3 workflow-source/scripts/harvest_entry_sections.py --tmp-dir <경로> --apply``",
        f"채취 ref: {', '.join(refs)}",
        "결과: " + " · ".join(log),
        "",
        "키는 절 제목(`## ` 뒤), 값은 정규화 본문(공백 묶음 → 한 칸)의 SHA-256 앞 16자.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "KNOWN_GENERATED: dict[str, frozenset[str]] = {",
    ]
    for title in sorted(known):
        hashes = ", ".join(repr(h) for h in sorted(known[title]))
        lines.append(f"    {title!r}: frozenset({{{hashes}}}),")
    lines += ["}", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--tmp-dir", required=True, help="실디스크 경로 (worktree · bootstrap 대상)")
    parser.add_argument("--ref", action="append", dest="refs", default=[], help="채취 ref (반복, 기본 DEFAULT_REFS)")
    parser.add_argument("--apply", action="store_true", help="데이터 모듈을 쓴다 (기본: 요약만)")
    args = parser.parse_args()
    refs = tuple(args.refs) or DEFAULT_REFS
    with tempfile.TemporaryDirectory(dir=args.tmp_dir) as td:
        known, log = harvest(refs, Path(td))
    print("\n".join(log))
    print(f"제목 {len(known)}종 · 해시 {sum(len(v) for v in known.values())}개")
    if args.apply:
        OUT.write_text(render_module(known, refs, log), encoding="utf-8")
        print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
