"""deprecated shim — 구현은 :mod:`workflow_kit.tools.mkdocs_git_dates` 로 이동 (v1.1.8).

top-level `tools` 는 공개 배포 시 이름 충돌을 일으키는 일반명이라
`workflow_kit.tools` 로 격상했다 (TASK-2026-08-12-main-006, 배포 검토 §2).
본 shim 은 1st deprecation cycle 동안 구경로 호출(import·path-load·직접 실행)을
전부 지원하고 다음 cycle 에 제거된다. 새 코드는 정위치를 직접 쓸 것.
"""

import sys as _sys
from pathlib import Path as _Path

_SOURCE_ROOT = _Path(__file__).resolve().parents[1]
if str(_SOURCE_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_SOURCE_ROOT))

import workflow_kit.tools.mkdocs_git_dates as _impl

# path-load(spec_from_file_location) 소비자가 private helper 까지 쓰므로
# 공개/비공개 가리지 않고 전체 namespace 를 노출한다 (모듈 메타키는 제외).
globals().update({
    _k: _v for _k, _v in vars(_impl).items()
    if _k not in {"__name__", "__file__", "__loader__", "__spec__",
                   "__package__", "__path__", "__builtins__"}
})

if __name__ == "__main__":
    raise SystemExit(_impl.main())
