#!/usr/bin/env python3
"""Meta-check: 실행 표면(skill / tool / script)이 실제로 **실행 가능한가**.

## 왜 필요한가

`skills/memory-freeze/scripts/run_memory_freeze.py` 가 v0.6.6(`6a9126c`) 부터
2026-07-22 까지 **문법 오류로 실행 자체가 불가능**했는데 어떤 smoke 도 잡지 못했다.
당시 5개 skill 에 stage_completion 블록을 template 으로 삽입하면서 skill 이름을
그대로 변수명에 넣어 `memory-freeze_completion`(hyphen) 을 만든 것이 원인이다.

결과적으로 R8 memory freeze 가 1년 가까이 한 번도 수행되지 않았고, 그것이
`wiki_source_rule`(R9) red 의 근본 원인이었다. **"선언은 stable 인데 실행조차 안 되는"**
상태를 아무도 탐지하지 못한 것이 진짜 문제다.

본 check 는 그 부류를 원천 차단한다:

- case 1: 모든 실행 표면 `.py` 가 **compile 가능**한가 (문법 오류 0)
- case 2: `run_*.py` skill entrypoint 가 `--help` 에 정상 응답하는가 (import-time 오류 0)
- case 3: skill 이름이 hyphen 을 포함해도 생성 코드가 유효한 식별자를 쓰는가
          (v0.6.6 회귀 패턴 자체를 차단)

case 2 는 **실제로 프로세스를 띄워** import chain 까지 검증한다 — compile 만으로는
`from ... import X` 실패나 module-level 예외를 잡지 못하기 때문이다.
"""

from __future__ import annotations

import py_compile
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"

# 실행 표면 = 사람이/에이전트가 직접 호출하는 코드.
SURFACE_DIRS = (
    SOURCE_ROOT / "skills",
    SOURCE_ROOT / "tools",
    SOURCE_ROOT / "scripts",
)
# 생성물 / 캐시 제외.
EXCLUDED_PARTS = {"build", "__pycache__", ".venv", "dist", "node_modules"}

# `--help` 응답을 요구할 entrypoint 패턴.
ENTRYPOINT_GLOB = "run_*.py"
HELP_TIMEOUT_SEC = 30

# hyphen 이 섞인 식별자 (v0.6.6 회귀 패턴). `a-b_completion = ...` 형태.
HYPHEN_IDENT_RE = re.compile(r"^\s*[A-Za-z_][\w]*-[\w-]*\s*=\s*[^=]", re.MULTILINE)


def _iter_surface_files() -> list[Path]:
    files: list[Path] = []
    for root in SURFACE_DIRS:
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*.py")):
            if EXCLUDED_PARTS & set(p.parts):
                continue
            files.append(p)
    return files


def _iter_entrypoints() -> list[Path]:
    eps: list[Path] = []
    for root in SURFACE_DIRS:
        if not root.is_dir():
            continue
        for p in sorted(root.rglob(ENTRYPOINT_GLOB)):
            if EXCLUDED_PARTS & set(p.parts):
                continue
            eps.append(p)
    return eps


def test_case_1_all_surface_files_compile() -> None:
    """실행 표면의 모든 .py 가 문법 오류 없이 compile 된다."""
    files = _iter_surface_files()
    assert files, "실행 표면 파일을 하나도 찾지 못했다 (경로 규칙 확인 필요)"
    broken: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        for p in files:
            # cfile 을 temp 로 보내 저장소에 .pyc 를 남기지 않는다.
            cfile = Path(td) / (p.stem + ".pyc")
            try:
                py_compile.compile(str(p), cfile=str(cfile), doraise=True)
            except py_compile.PyCompileError as exc:
                broken.append(f"{p.relative_to(REPO_ROOT)}: {exc.msg.strip().splitlines()[-1]}")
    assert not broken, (
        f"{len(broken)}/{len(files)} 실행 표면 파일이 compile 실패:\n  "
        + "\n  ".join(broken)
    )
    print(f"  case 1: {len(files)} 실행 표면 파일 compile OK")


def test_case_2_entrypoints_respond_to_help() -> None:
    """skill entrypoint 가 `--help` 에 정상 응답한다 (import chain 검증).

    compile 만으로는 import 실패 / module-level 예외를 잡지 못한다. 실제 프로세스를
    띄워 exit code 와 usage 출력을 본다.
    """
    eps = _iter_entrypoints()
    assert eps, f"{ENTRYPOINT_GLOB} entrypoint 를 찾지 못했다"
    failures: list[str] = []
    for ep in eps:
        proc = subprocess.run(
            [sys.executable, str(ep), "--help"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=HELP_TIMEOUT_SEC,
        )
        rel = ep.relative_to(REPO_ROOT)
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout).strip().splitlines()[-1:] or ["(출력 없음)"]
            failures.append(f"{rel}: exit {proc.returncode} — {tail[0]}")
            continue
        combined = proc.stdout + proc.stderr
        if "usage" not in combined.lower():
            failures.append(f"{rel}: --help 에 usage 출력 부재")
    assert not failures, (
        f"{len(failures)}/{len(eps)} entrypoint 가 --help 에 정상 응답하지 않음:\n  "
        + "\n  ".join(failures)
    )
    print(f"  case 2: {len(eps)} entrypoint --help 응답 OK")


def test_case_3_no_hyphenated_identifiers() -> None:
    """hyphen 이 섞인 변수명이 없다 (v0.6.6 template 회귀 패턴 차단).

    `memory-freeze_completion = ...` 은 Python 에서 `memory - freeze_completion` 으로
    해석되거나 문법 오류가 된다. skill 이름을 코드 생성에 그대로 끼워 넣을 때 생긴다.
    case 1 이 문법 오류는 잡지만, 우연히 문법상 유효해지는 형태(뺄셈으로 해석)는
    잡지 못하므로 패턴 자체를 금지한다.
    """
    offenders: list[str] = []
    for p in _iter_surface_files():
        text = p.read_text(encoding="utf-8", errors="ignore")
        for m in HYPHEN_IDENT_RE.finditer(text):
            line = m.group(0).strip()
            offenders.append(f"{p.relative_to(REPO_ROOT)}: {line[:80]}")
    assert not offenders, (
        "hyphen 이 섞인 식별자 발견 (skill 이름을 변수명에 그대로 넣은 흔적):\n  "
        + "\n  ".join(offenders)
    )
    print("  case 3: hyphen 식별자 0")


def main() -> int:
    cases = [
        ("test_case_1_all_surface_files_compile", test_case_1_all_surface_files_compile),
        ("test_case_2_entrypoints_respond_to_help", test_case_2_entrypoints_respond_to_help),
        ("test_case_3_no_hyphenated_identifiers", test_case_3_no_hyphenated_identifiers),
    ]
    failures = 0
    print("=== 실행 표면 메타 체크 (skill / tool / script) ===")
    for name, fn in cases:
        try:
            fn()
            print(f"  PASS: {name}")
        except AssertionError as exc:
            print(f"  FAIL: {name}\n    {exc}")
            failures += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL: {name}\n    {type(exc).__name__}: {exc}")
            failures += 1
    total = len(cases)
    print(f"=== {'PASS' if failures == 0 else 'FAIL'}: {total - failures}/{total} ===")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
