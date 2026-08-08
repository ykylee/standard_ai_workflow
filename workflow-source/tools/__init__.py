"""tools — CLI 化 A안 (v1.1.1+, TASK-2026-08-08-main-020)

`workflow-source/tools/` 의 30+ module 은 *script* 형태 (각자 `main()` 함수) 이지만,
v1.1.1+ 부터 **importable package** 이다 (`pip install -e .` 후 `tools.<name>` 으로
import 가능). 본 `__init__.py` 가 그 *loud* marker.

**CLI 진입점** (`[project.scripts]` 의 30+ console_script):
- `workflow-registry` → `tools.workspace_registry:main`
- `workflow-drift-detect` → `tools.detect_scope_drift:main`
- `workflow-seed-workspace-memory` → `tools.seed_workspace_memory:main`
- ... 외 27개.

기존 호출 경로 (legacy) — 그대로 동작:
- `python3 workflow-source/tools/detect_scope_drift.py --help`
- `python3 -m tools.detect_scope_drift` (새 진입점)

신규 호출 경로 (CLI 化 A안):
- `workflow-drift-detect --help` (PATH 진입 후, 어디서든)

**B안 (dispatcher `wk`)** 은 후속 release. A안은 0 리스크 (script 변경 0, 진입점만 추가).

History:
- v0.7.55: `release_pipeline_lib.py` in-process wrapper (1개 우회)
- v0.7.56: 본 `__init__.py` 추가 — *loud* import 가능 표시
- v1.1.1+: `[project.scripts]` 30+ console_script — `pip install -e .` 후 binary 자동 생성
"""
