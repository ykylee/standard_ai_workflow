#!/usr/bin/env python3
"""Meta-check: smoke 가 **추적 중인 저장소 파일을 건드리지 않는가**.

## 왜 필요한가

한 사이클 동안 smoke 가 저장소를 침범하는 경로가 **5건** 발견됐다:

1. `release --dry-run` 이 문서 63개를 write (auto-step 이 dry-run 을 상속하지 않음)
2. `check_merge_doc_reconcile` → 예제 fixture `state.json` 재생성
3. `check_refresh_maturity_*` 3종 → `core/maturity_matrix.json` 의 `last_updated`
4. `check_bidir_link_v0_13_3` → `git checkout HEAD --` 복원으로 **미커밋 작업 파괴**
5. `release --auto-bump --dry-run` → `pyproject.toml` / `__init__.py` version bump

전부 *사후에* `git status` 를 눈으로 보고 찾았다. `release_pipeline` 의 `git add` 와
겹치면 릴리스와 무관한 변경이 release commit 에 흡수되고, 4번처럼 **작업이 사라지는**
경우는 `git status` 가 오히려 깨끗해 보여 더 위험하다.

본 check 는 그 탐지를 자동화한다. 개별 경로를 막는 것이 아니라 **경로가 생기는 것 자체**
를 CI 에서 잡는다.

## 판정 방식

대상 check 를 서브프로세스로 실행하고 **실행 전후의 `git status --porcelain` +
추적 파일 해시**를 비교한다. 어느 쪽으로든(수정 / 생성 / 삭제 / 복원) 달라지면 실패.

- 이미 dirty 한 워킹트리에서도 동작한다 — 절대 상태가 아니라 **전후 delta** 를 본다.
  덕분에 작업 중에도 CI 와 로컬 양쪽에서 유효하다.
- 대상 선정: 과거에 실제로 오염을 일으켰던 check + 저장소를 write 할 소지가 큰
  release / memory / dashboard 계열. 전량을 돌리면 본 check 하나가 전체 smoke 시간을
  두 배로 만들기 때문에 **대표 표본**을 고정 목록으로 둔다.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = REPO_ROOT / "workflow-source" / "tests"

# 과거에 실제 오염을 일으켰던 check + 저장소 write 소지가 큰 계열.
# (전량 실행은 run_all_checks 의 역할이므로 여기서는 대표 표본만 검증한다.)
WATCHED_CHECKS = (
    "check_drift_prevention_helpers_v0_11_23.py",   # release --dry-run auto-step (경로 1·5)
    "check_merge_doc_reconcile.py",                 # 예제 fixture state.json (경로 2)
    "check_refresh_maturity_v0_14_6.py",            # maturity_matrix last_updated (경로 3)
    "check_refresh_maturity_v0_15_2.py",
    "check_refresh_maturity_v0_15_3.py",
    "check_bidir_link_v0_13_3.py",                  # wiki / memory_index 복원 (경로 4)
    "check_release_pipeline_release_coordination.py",  # auto-bump version write (경로 5)
    "check_quality_dashboard_v0_13_0.py",           # dashboard emit
)

CHECK_TIMEOUT_SEC = 300


def _porcelain() -> str:
    return subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60,
    ).stdout


def _tracked_digest() -> str:
    """추적 파일의 내용 해시 (삭제/복원까지 잡기 위해 status 와 별도로 본다).

    `git status` 는 "HEAD 로 되돌려진" 파괴형 변경을 **깨끗하게** 보여주므로,
    내용 자체를 요약해 둬야 4번 유형(미커밋 작업 파괴)을 탐지할 수 있다.
    """
    proc = subprocess.run(
        ["git", "diff", "HEAD", "--stat"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
    )
    return hashlib.sha256(proc.stdout.encode("utf-8")).hexdigest()


def _snapshot() -> tuple[str, str]:
    return _porcelain(), _tracked_digest()


def _run_check(name: str, tmp_dir: str) -> None:
    path = TESTS_DIR / name
    if not path.exists():
        return
    env_tmp = {"TMPDIR": tmp_dir}
    import os
    subprocess.run(
        [sys.executable, str(path)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=CHECK_TIMEOUT_SEC,
        env={**os.environ, **env_tmp},
    )


def test_watched_checks_do_not_touch_repo() -> None:
    """감시 대상 check 실행이 추적 파일 상태를 바꾸지 않는다."""
    missing = [n for n in WATCHED_CHECKS if not (TESTS_DIR / n).exists()]
    assert not missing, f"감시 목록에 존재하지 않는 check: {missing}"

    offenders: list[str] = []
    with tempfile.TemporaryDirectory(prefix="no-repo-write-") as td:
        for name in WATCHED_CHECKS:
            before = _snapshot()
            _run_check(name, td)
            after = _snapshot()
            if before != after:
                before_set = set(before[0].splitlines())
                changed = [ln for ln in after[0].splitlines() if ln not in before_set]
                detail = changed[:5] if changed else ["(status 동일 — 내용이 복원/변경됨)"]
                offenders.append(f"{name}: {detail}")
                # 다음 대상 판정을 오염시키지 않도록 기준선을 갱신한다.
                # (복구는 하지 않는다 — 여기서 git checkout 을 돌리면 본 check 자신이
                #  경로 4 와 같은 파괴형이 된다.)

    assert not offenders, (
        f"{len(offenders)}개 check 가 추적 중인 저장소 파일을 건드렸다:\n  "
        + "\n  ".join(offenders)
        + "\n\n→ 해당 check 는 temp 사본 위에서 돌거나, 도구의 경로 override "
          "(예: --maturity-path) 를 써야 한다. dry-run 이라면 도구가 dry-run 을 "
          "상속하지 않는 버그일 수 있다."
    )
    print(f"  {len(WATCHED_CHECKS)} 감시 대상 check 모두 저장소 변경 0")


def main() -> int:
    print("=== 저장소 write 금지 메타 체크 ===")
    try:
        test_watched_checks_do_not_touch_repo()
    except AssertionError as exc:
        print(f"  FAIL: {exc}")
        print("=== FAIL: 0/1 ===")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL: {type(exc).__name__}: {exc}")
        print("=== FAIL: 0/1 ===")
        return 1
    print("  PASS: test_watched_checks_do_not_touch_repo")
    print("=== PASS: 1/1 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
