"""deprecated shim — 구현은 :mod:`workflow_kit.bootstrap_lib.renderers` 로 이동 (v1.1.8).

top-level `bootstrap_lib` 는 공개 배포 시 이름 충돌을 일으키는 일반명이라
`workflow_kit.bootstrap_lib` 로 격상했다 (TASK-2026-08-12-main-007, 1단계
tools 와 같은 처방). 본 shim 은 1st deprecation cycle 동안 구경로 호출을
지원하고 다음 cycle 에 제거된다.
"""

import sys as _sys
from pathlib import Path as _Path

_SOURCE_ROOT = _Path(__file__).resolve().parents[2]
if str(_SOURCE_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_SOURCE_ROOT))

import workflow_kit.bootstrap_lib.renderers as _impl

globals().update({
    _k: _v for _k, _v in vars(_impl).items()
    if _k not in {"__name__", "__file__", "__loader__", "__spec__",
                   "__package__", "__path__", "__builtins__"}
})
