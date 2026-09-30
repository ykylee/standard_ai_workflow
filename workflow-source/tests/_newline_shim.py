#!/usr/bin/env python3
"""**개행을 자르는 해석기 shim** 모형 — 검사 둘이 같은 모형을 쓴다.

Windows 에서 `which("python3")` 가 `python3.CMD` · `python3.10.bat` 같은 배치 shim 을
돌려주면 cmd.exe 가 명령행을 다시 해석하며 인자의 **첫 개행 뒤를 버린다**. `-c` 로 넘긴
다줄 스크립트는 첫 줄만 돌고 아무것도 찍지 않는다 (TASK-2026-09-29-main-013 ·
TASK-2026-09-30-main-002).

- Windows: 실제 배치 파일을 만들어 cmd.exe 의 동작 그 자체를 잰다.
- POSIX: 인자를 첫 개행에서 잘라 진짜 해석기로 `execv` 하는 스크립트로 흉내 낸다.

모형이 결함을 재현하는지는 `truncates()` 로 **같은 case 안에서 따로** 재야 한다 —
그것이 없으면 shim 경유 green 은 아무것도 증명하지 않는다.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_TRUNCATING_SHIM = """#!{python}
import os, sys
args = []
for arg in sys.argv[1:]:
    if "\\n" in arg:
        args.append(arg.split("\\n", 1)[0])
        break
    args.append(arg)
os.execv({python!r}, [{python!r}, *args])
"""


def make_truncating_shim(directory: Path, name: str = "python3") -> Path:
    """`directory` 에 `sys.executable` 로 넘기는 개행 절단 shim 을 만든다."""
    if os.name == "nt":
        shim = directory / f"{name}.cmd"
        shim.write_text(f'@echo off\r\n"{sys.executable}" %*\r\n', encoding="ascii")
    else:
        shim = directory / name
        shim.write_text(_TRUNCATING_SHIM.format(python=sys.executable), encoding="utf-8")
        shim.chmod(0o755)
    return shim


def truncates(shim: Path) -> bool:
    """모형 유효성 — shim 이 `-c` 다줄의 첫 개행 뒤를 실제로 버리는가."""
    seen = subprocess.run(
        [str(shim), "-c", "print('first')\nprint('second')"],
        capture_output=True, text=True, timeout=30,
    ).stdout.split()
    return seen == ["first"]
