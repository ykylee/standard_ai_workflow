#!/usr/bin/env python3
"""Verify source development checks do not require the applied ai-workflow runtime layer.

v1.1.7(TASK-2026-08-10-main-018): **원본 저장소를 더 이상 건드리지 않는다.**

이전 판은 원본의 `ai-workflow/` 를 `.tmp-ai-workflow-runtime-hidden` 으로 rename 해
숨겼다가 `finally` 로 되돌렸다. 검증 자체는 맞았지만 대가가 컸다:

1. **`finally` 는 SIGKILL 에 돌지 않는다.** runner 의 timeout 처리는 프로세스 그룹에
   SIGTERM → SIGKILL 을 보낸다. 최악의 경우 저장소에 `ai-workflow/` 가 **사라진 채
   남는다** — 테스트가 저장소를 파괴하는 것이다.
2. 그 사이 `ai-workflow/` 가 통째로 없으므로, 같은 순간 그것을 읽는 누구든 깨진다.
   실측에서 병렬 실행의 다른 check 3건이 정확히 그렇게 깨졌고, CLAUDE.md 가 전제하는
   "여러 에이전트가 함께 일할 수 있다" 아래에서는 실사고가 된다.

이제 저장소 **사본** 에서 검증한다 (0.5s, ~41MB). 원본은 읽기만 하므로 병렬 실행에도
안전하고, 이 프로세스가 어떻게 죽든 원본은 무손상이다. temp 는 runner 가 준 전용
TMPDIR 아래에 잡히고 종료 시 회수된다.

`.git` 은 **복사한다** — `check_handoff_git_integration` 이 `--git-range HEAD~3..HEAD`
로 실제 히스토리를 요구한다. 사본에서 실행하면 각 check 의
`REPO_ROOT = Path(__file__).resolve().parents[2]` 가 사본을 가리키므로, 검증 대상이
정확히 "runtime layer 없는 저장소" 가 된다.
"""

from __future__ import annotations

#: 의도적 전역 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES_ALL_REASON = (
    "원본 저장소가 적용 runtime 레이어 없이도 서는지를 재는 검사라 관찰 대상이 저장소 자신이다 — meta-watch "
    "실측 (2026-08-29) 접근 2076건 · 최상위 30개 항목 전부"
)

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRES_QUIET_REPO = True
"""이 check 는 저장소를 통째로 복사한다 — 복사 순간의 일시 상태를 그대로 굳힌다.

다른 check 가 그 찰나에 파일을 재생성 중이면 오염된 사본을 검증하게 된다 (실측:
병렬 실행에서 "fixture out of date" 로 깨졌다). 원본을 건드리지는 않지만, 원본을
**한 시점의 정합 상태로 읽어야** 하므로 정숙 구간이 필요하다."""
REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR_NAME = "ai-workflow"

# 검증에 불필요하고 복사만 비싸지는 것들. `.git` 은 제외하지 않는다 (위 docstring).
COPY_IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".venv*", ".mypy_cache", ".pytest_cache",
    "node_modules", "dist", "build",
)

SOURCE_CHECKS = (
    "check_docs.py",
    "check_bootstrap.py",
    "check_export_harness_package.py",
    "check_read_only_jsonrpc_fixtures.py",
    "check_read_only_harness_mcp_examples.py",
    "check_workflow_state_generator.py",
    "check_handoff_git_integration.py",
    "check_paths.py",
)


def main() -> int:
    origin_runtime = REPO_ROOT / RUNTIME_DIR_NAME
    origin_present_before = origin_runtime.exists()

    with tempfile.TemporaryDirectory(prefix="src-without-runtime-") as tmp:
        sandbox = Path(tmp) / "repo"
        shutil.copytree(REPO_ROOT, sandbox, ignore=COPY_IGNORE, symlinks=True)

        runtime_dir = sandbox / RUNTIME_DIR_NAME
        if runtime_dir.exists():
            shutil.rmtree(runtime_dir)
        assert not runtime_dir.exists(), f"사본에서 runtime layer 를 못 지웠다: {runtime_dir}"

        for script_name in SOURCE_CHECKS:
            script_path = sandbox / "workflow-source" / "tests" / script_name
            assert script_path.is_file(), f"사본에 검사 스크립트가 없다: {script_path}"
            subprocess.run([sys.executable, str(script_path)], cwd=sandbox, check=True)

    # 이 check 의 핵심 계약 — **원본은 읽기만 한다** — 을 실행 경로에서 직접 잰다.
    # 이전 판은 원본을 rename 해 숨겼고, 그 사이 저장소에 `ai-workflow/` 가 없었다.
    # 계약을 파일 끝의 (실행되지 않는) test wrapper 가 아니라 여기서 확인하는 이유:
    # `python3 check_*.py` 는 `main()` 만 부르므로, wrapper 는 신호로 세어질 뿐
    # 실제로는 아무것도 검증하지 않는다.
    assert origin_runtime.exists() == origin_present_before, (
        f"원본 저장소의 {RUNTIME_DIR_NAME}/ 상태가 바뀌었다 "
        f"(before={origin_present_before}, after={origin_runtime.exists()}) — "
        "이 check 는 원본을 건드리면 안 된다"
    )
    assert not (REPO_ROOT / ".tmp-ai-workflow-runtime-hidden").exists(), (
        "옛 rename 방식의 흔적이 남았다 — 원본을 숨겼다 되돌리는 구현으로 회귀했다"
    )

    print("Source development checks passed without the applied ai-workflow runtime layer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
