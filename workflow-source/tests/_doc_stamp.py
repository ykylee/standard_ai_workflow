#!/usr/bin/env python3
"""문서 스탬프 판정의 **재수출**. 정본은 `workflow_kit/common/doc_stamp.py` 다.

## 왜 옮겼는가 (TASK-2026-09-22-main-002)

이 판정은 원래 `tests/` 안에 있었고, 그래서 **읽는 쪽(검사)만** 알고 **쓰는 쪽**
(`release_pipeline.cmd_doc_headers_update`)은 몰랐다. 쓰는 쪽은 헤더가 있는 문서를
전부 오늘로 올렸고, 그 결과 2026-09-22 v1.10.0 발행 준비에서 **내용이 한 줄도 안
바뀐 문서 100개**가 '오늘 수정됨' 을 주장하게 됐다. 파생물은 만드는 쪽이 규약을
알아야 한다 — 그래서 정본을 kit 으로 올렸다.

## 왜 `import workflow_kit...` 이 아니라 파일로 읽는가

`workflow_kit` 패키지를 import 하면 `__init__` 이 딸려 와 이 판정 하나를 쓰는
검사 5종의 **입력 표면이 kit 전체(43파일)로 넓어진다** — meta-watch 실측이
`좁은 선언` 으로 그것을 잡았다. 판정 모듈 자신은 **stdlib only** 라 패키지가
필요 없다. 그래서 파일 경로로 직접 읽어 표면을 한 파일로 유지한다.

**사본이 아니다** — 같은 파일을 읽으므로 `release_pipeline` 이 쓰는 판정과
byte 단위로 같은 것이다.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_CANONICAL = (
    Path(__file__).resolve().parents[1] / "workflow_kit" / "common" / "doc_stamp.py"
)

_spec = importlib.util.spec_from_file_location("_doc_stamp_canonical", _CANONICAL)
if _spec is None or _spec.loader is None:  # pragma: no cover - 배치가 깨진 경우
    raise ImportError(f"문서 스탬프 판정 정본을 못 읽었다: {_CANONICAL}")
_mod = importlib.util.module_from_spec(_spec)
sys.modules["_doc_stamp_canonical"] = _mod
_spec.loader.exec_module(_mod)

GRACE_DAYS = _mod.GRACE_DAYS
check_frontmatter_stamp = _mod.check_frontmatter_stamp
last_content_change_date = _mod.last_content_change_date

__all__ = ["GRACE_DAYS", "check_frontmatter_stamp", "last_content_change_date"]
