#!/usr/bin/env python3
"""backlog-update skill runner — 구현은 `tools/backlog_update.py` 에 있다.

v1.1.7+ (TASK-2026-08-11-main-021): 구현을 `tools/` 로 올렸다. `skills/` 는 pip
패키지에도 bootstrap 번들에도 포함되지 않아서, 소비자 프로젝트에는 이 기능을
실행할 경로가 **아예 없었다** (TASK-020 진단) — 그래서 모든 하네스에서 에이전트가
메모리 문서를 손으로 썼고, `workflow_writes.py` 의 계약(빈 목록은 빈 bullet `-`,
상한 10, index block 모양)이 한 번도 적용되지 않았다. `tools/` 는 패키지에
포함되므로 같은 구현이 `wk backlog-update` 로 배포된다.

이 파일은 kit 저장소 안의 기존 호출 경로(문서·검사 약 30곳)를 깨지 않기 위한
얇은 wrapper 다. 로직을 여기에 다시 적지 않는다 — 두 벌이 되면 갈라진다.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from tools.backlog_update import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
