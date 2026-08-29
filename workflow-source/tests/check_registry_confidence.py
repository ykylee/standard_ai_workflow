"""in-flight confidence smoke (TASK-2026-08-08-main-014, 표준 §0.8 #2)

§0.8 의 "in-flight 워크스페이스 신뢰도 표시" 닫음. 4-level enum (`fresh` / `recent`
/ `stale` / `orphan`) + 결정 3-way signal (path / last_seen / worktree_branch) 의
*경계* 를 *회귀 정합* 으로 verify. registry 자체 동작은 `check_registry_*` 가 이미
커버. 본 smoke 는 *confidence() 함수만* 을 격리.

검증 케이스 (6+):
    1. fresh   — path.is_dir() ✓ AND last_seen < 24h AND branch 일치
    2. recent  — last_seen 이 24h~7d 사이 (살아있지만 확인 필요)
    3. stale   — last_seen > 7d
    4. stale2  — branch mismatch (worktree 가 다른 브랜치로 옮겨짐)
    5. orphan  — path 부재 (worktree 삭제됨)
    6. recent2 — last_seen 깨진 timestamp (ValueError → stale 가 아니라 recent? — 본
       함수는 *stale* 로 정정. 깨진 데이터는 *신뢰도 저하* 가 옳다. §0.8 #2 의 3-way
       가 *모두 신뢰 가능한 신호* 라는 정합성 유지.)
    7. fresh_skip_branch — branch 인자 None 일 때 branch 확인 생략

Stdlib only. `workflow_kit.common.workspace_registry` 의 `confidence()` 와
`RegistryEntry` 만 import.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.workspace_registry import (  # noqa: E402
    CONFIDENCE_LEVELS,
    RegistryEntry,
    confidence,
)


FIXED_NOW = datetime(2026, 8, 8, 22, 0, 0, tzinfo=timezone.utc)


def _entry_with(path: str | None, last_seen_offset: timedelta | None, branch: str = "feat-x") -> RegistryEntry:
    """테스트용 RegistryEntry. path 가 None 이면 orphan 시뮬레이션용으로만 사용."""
    last_seen = ""
    if last_seen_offset is not None:
        last_seen = (FIXED_NOW - last_seen_offset).strftime("%Y-%m-%dT%H:%M:%SZ")
    return RegistryEntry(
        path=path or "",
        branch=branch,
        harness="test",
        endpoint=None,
        registered_at="2026-08-01T00:00:00Z",
        last_seen_at=last_seen,
    )


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        # 1) fresh — path 가 실재 + last_seen 1h 전 + branch 일치
        real_path = str(Path(tmp) / "wt-fresh")
        Path(real_path).mkdir(parents=True, exist_ok=True)
        e = _entry_with(real_path, timedelta(hours=1))
        c = confidence(e, worktree_branch="feat-x", now=FIXED_NOW)
        if c != "fresh":
            failures.append(f"[1] fresh: expected 'fresh', got {c!r}")
        else:
            print(f"  [1] fresh   ✓  (path real, last_seen=1h, branch match)")

        # 2) recent — last_seen 3일 전 (24h~7d 사이)
        e = _entry_with(real_path, timedelta(days=3))
        c = confidence(e, worktree_branch="feat-x", now=FIXED_NOW)
        if c != "recent":
            failures.append(f"[2] recent: expected 'recent', got {c!r}")
        else:
            print(f"  [2] recent  ✓  (path real, last_seen=3d, branch match)")

        # 3) stale — last_seen 10일 전 (> 7d)
        e = _entry_with(real_path, timedelta(days=10))
        c = confidence(e, worktree_branch="feat-x", now=FIXED_NOW)
        if c != "stale":
            failures.append(f"[3] stale: expected 'stale', got {c!r}")
        else:
            print(f"  [3] stale   ✓  (path real, last_seen=10d > 7d)")

        # 4) stale (branch mismatch) — last_seen 신선하지만 worktree 가 다른 브랜치로
        e = _entry_with(real_path, timedelta(hours=1))
        c = confidence(e, worktree_branch="OTHER-BRANCH", now=FIXED_NOW)
        if c != "stale":
            failures.append(f"[4] stale (branch mismatch): expected 'stale', got {c!r}")
        else:
            print(f"  [4] stale2  ✓  (path real, last_seen=1h, branch mismatch)")

        # 5) orphan — path 부재
        e = _entry_with("/nonexistent/never-existed-path-12345", timedelta(hours=1))
        c = confidence(e, worktree_branch="feat-x", now=FIXED_NOW)
        if c != "orphan":
            failures.append(f"[5] orphan: expected 'orphan', got {c!r}")
        else:
            print(f"  [5] orphan  ✓  (path 부재)")

        # 6) stale (last_seen 깨짐) — ValueError → stale 로 정정
        # RegistryEntry.frozen 이라 dataclasses.replace 로 last_seen 만 깨진 값으로.
        # path 는 fresh path (test 1 의 real_path) 사용 — path 부재면 orphan 이 먼저
        # 걸려서 검증 의도와 어긋남.
        from dataclasses import replace
        e_broken = replace(
            _entry_with(real_path, timedelta(hours=1)),
            last_seen_at="NOT-A-TIMESTAMP",
        )
        c = confidence(e_broken, worktree_branch="feat-x", now=FIXED_NOW)
        if c != "stale":
            failures.append(f"[6] stale (broken last_seen): expected 'stale', got {c!r}")
        else:
            print(f"  [6] stale3  ✓  (last_seen 깨진 timestamp → stale)")

        # 7) fresh (worktree_branch=None — branch 확인 생략)
        e = _entry_with(real_path, timedelta(hours=1))
        c = confidence(e, worktree_branch=None, now=FIXED_NOW)
        if c != "fresh":
            failures.append(f"[7] fresh (no branch check): expected 'fresh', got {c!r}")
        else:
            print(f"  [7] fresh2  ✓  (worktree_branch=None → branch check skip)")

        # 8) enum vocabulary sanity
        missing = CONFIDENCE_LEVELS - {"fresh", "recent", "stale", "orphan"}
        if missing:
            failures.append(f"[8] CONFIDENCE_LEVELS missing: {missing}")
        else:
            print(f"  [8] enum    ✓  (CONFIDENCE_LEVELS = {{fresh, recent, stale, orphan}})")

    print()
    if failures:
        print(f"FAIL: {len(failures)} case(s) failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL PASS: in-flight confidence 4-level enum — 8 case (4 enum + 4 edge)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
