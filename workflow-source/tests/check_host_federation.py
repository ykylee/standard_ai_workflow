"""registry federation smoke (TASK-2026-08-08-main-015, 표준 §0.8 #1)

§0.8 #1 *registry 저장 위치* 의 federation 정공법 검증. 4 후보 (central server /
git-tracking / S3 / **federation**) 중 federation 채택 — 각 호스트는 host-scoped
file 유지, 호스트 *목록* 만 별도 `known_hosts.json` 으로 관리, dashboard 가 모든
known host 의 registry 를 *읽기* 가능. 본 smoke 는 *merge_entries()* 와
*known_hosts CRUD* 의 결정 6+ case 를 격리 verify.

검증 케이스 (8):
    1. single host merge (no-op)
    2. multi-host dedup — 다른 path, 다른 host → 모두 보존
    3. conflict resolution — 같은 path, 다른 host, 더 최근 last_seen 우선
    4. legacy source_host_id missing (빈 string) — 입력 label 로 fallback
    5. known_hosts add + load + save roundtrip (atomic)
    6. known_hosts self-host idempotent (자기 자신 추가 시도 → no-op)
    7. known_hosts remove (있는 거 + 없는 거)
    8. merge_entries determinism (입력 순서 무관 — 정렬된 출력)

Stdlib only. `workspace_registry` 의 KnownHost / known_hosts_* / merge_entries
만 격리 검증. HTTP fetch / dashboard 통합은 TASK-016.
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

from workflow_kit.common import workspace_registry as R  # noqa: E402


FIXED_NOW = datetime(2026, 8, 8, 22, 0, 0, tzinfo=timezone.utc)


def _entry(path: str, branch: str, host_id: str, days_ago: int = 1) -> R.RegistryEntry:
    seen = (FIXED_NOW - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return R.RegistryEntry(
        path=path,
        branch=branch,
        harness="test",
        endpoint=None,
        registered_at="2026-08-01T00:00:00Z",
        last_seen_at=seen,
        source_host_id=host_id,
    )


def _entry_legacy(path: str, branch: str) -> R.RegistryEntry:
    """source_host_id field 가 없는 legacy entry (TASK-015 이전) — from_dict 의
    하위 호환 (기본값 빈 string) 시뮬레이션."""
    return R.RegistryEntry(
        path=path,
        branch=branch,
        harness="test",
        endpoint=None,
        registered_at="2026-08-01T00:00:00Z",
        last_seen_at="2026-08-07T00:00:00Z",
        source_host_id="",  # legacy
    )


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        # known_hosts path 를 tempdir 로 격리 — host-wide 파일 오염 방지.
        known_hosts_file = Path(tmp) / "known_hosts.json"
        R.known_hosts_path_orig = None  # sentinel

        # 1) single host merge — 입력 그대로 (sort 만) 반환
        single = [_entry("/wt/a", "feat-a", "hostA", days_ago=1)]
        out = R.merge_entries([("hostA", single)])
        if len(out) != 1 or out[0].path != "/wt/a" or out[0].source_host_id != "hostA":
            failures.append(f"[1] single host: expected 1 entry hostA/wt-a, got {out}")
        else:
            print("  [1] single host   ✓  (no-op dedup, source_host_id 보존)")

        # 2) multi-host dedup — 다른 path → 모두 보존
        out = R.merge_entries([
            ("hostA", [_entry("/wt/a", "feat-a", "hostA", days_ago=1)]),
            ("hostB", [_entry("/wt/b", "feat-b", "hostB", days_ago=2)]),
            ("hostC", [_entry("/wt/c", "feat-c", "hostC", days_ago=3)]),
        ])
        if len(out) != 3:
            failures.append(f"[2] multi-host: expected 3 entries, got {len(out)}")
        else:
            paths = {e.path for e in out}
            hosts = {e.source_host_id for e in out}
            if paths != {"/wt/a", "/wt/b", "/wt/c"} or hosts != {"hostA", "hostB", "hostC"}:
                failures.append(f"[2] multi-host: wrong paths/hosts, got {paths}/{hosts}")
            else:
                print(f"  [2] multi-host    ✓  (3 hosts × 1 path = 3 entries)")

        # 3) conflict resolution — 같은 path 다른 host, 더 최근 last_seen 우선
        out = R.merge_entries([
            ("hostA", [_entry("/wt/shared", "feat-shared", "hostA", days_ago=10)]),
            ("hostB", [_entry("/wt/shared", "feat-shared", "hostB", days_ago=1)]),  # 최신
        ])
        if len(out) != 1:
            failures.append(f"[3] conflict: expected 1 (dedup), got {len(out)}")
        elif out[0].source_host_id != "hostB":
            failures.append(f"[3] conflict: expected hostB (newer), got {out[0].source_host_id}")
        else:
            print("  [3] conflict      ✓  (hostB 가 1d 전, hostA 가 10d 전 → hostB 우선)")

        # 4) legacy source_host_id missing (빈 string) — 입력 label 로 fallback
        # merge_entries 는 entries.source_host_id 를 trust 하지만, 빈 string 일 때만
        # 입력 host_id_label 로 fallback 한다는 게 정공법.
        legacy = [_entry_legacy("/wt/legacy", "feat-legacy")]  # source_host_id = ""
        out = R.merge_entries([("hostLegacy", legacy)])
        if len(out) != 1:
            failures.append(f"[4] legacy: expected 1 entry, got {len(out)}")
        elif out[0].source_host_id != "hostLegacy":
            failures.append(f"[4] legacy: expected hostLegacy (label fallback), got {out[0].source_host_id!r}")
        else:
            print("  [4] legacy        ✓  (source_host_id='' → input label 로 fallback)")

        # 5) known_hosts add + load + save roundtrip (atomic)
        # 격리: known_hosts_path 를 tempdir 로 override.
        from unittest import mock
        with mock.patch.object(R, "known_hosts_path", lambda: known_hosts_file):
            hosts_before = R.load_known_hosts()
            if hosts_before:
                failures.append(f"[5] isolation: tempdir should be empty, got {hosts_before}")
            added = R.add_known_host("hostX", "http://hostx:8000/registry.json", note="test")
            if len(added) != 1 or added[0].host_id != "hostX" or added[0].endpoint != "http://hostx:8000/registry.json":
                failures.append(f"[5] add: unexpected result {added}")
            elif not known_hosts_file.is_file():
                failures.append(f"[5] save: file not created at {known_hosts_file}")
            else:
                # 권한 0o600 확인
                mode = known_hosts_file.stat().st_mode & 0o777
                if mode != 0o600:
                    failures.append(f"[5] save: perms {oct(mode)} != 0o600")
                else:
                    # load roundtrip
                    loaded = R.load_known_hosts()
                    if len(loaded) != 1 or loaded[0].host_id != "hostX":
                        failures.append(f"[5] roundtrip: expected hostX, got {loaded}")
                    else:
                        print("  [5] known_hosts   ✓  (add → save 0o600 → load roundtrip)")

            # 6) self-host idempotent — 자기 자신 추가 시도 → no-op
            self_id = R.host_id()
            pre = R.load_known_hosts()
            R.add_known_host(self_id, "http://self:0/registry.json")
            post = R.load_known_hosts()
            if len(pre) != len(post):
                failures.append(f"[6] self-host: pre={len(pre)} post={len(post)} (expected equal)")
            elif any(h.host_id == self_id for h in post):
                failures.append(f"[6] self-host: {self_id} 가 추가됨 (no-op 실패)")
            else:
                print(f"  [6] self-host     ✓  (자기 자신 {self_id!r} 추가 시도 → no-op)")

            # 7) known_hosts remove (있는 거 + 없는 거)
            R.add_known_host("hostY", "file:///tmp/hosty.json")
            pre_count = len(R.load_known_hosts())
            R.remove_known_host("hostY")
            mid_count = len(R.load_known_hosts())
            if mid_count != pre_count - 1:
                failures.append(f"[7a] remove existing: {pre_count} → {mid_count} (expected -1)")
            # 없는 거 remove → no-op
            R.remove_known_host("nonexistent-host-zzz")
            post_count = len(R.load_known_hosts())
            if post_count != mid_count:
                failures.append(f"[7b] remove missing: {mid_count} → {post_count} (expected equal)")
            if mid_count == pre_count - 1 and post_count == mid_count:
                print("  [7] remove        ✓  (existing → 삭제, missing → no-op)")

        # 8) merge_entries determinism — 입력 순서 무관
        entries_a = [_entry("/wt/x", "feat-x", "hostA", days_ago=1)]
        entries_b = [_entry("/wt/y", "feat-y", "hostB", days_ago=2)]
        out1 = R.merge_entries([("hostA", entries_a), ("hostB", entries_b)])
        out2 = R.merge_entries([("hostB", entries_b), ("hostA", entries_a)])
        if [e.path for e in out1] != [e.path for e in out2]:
            failures.append(f"[8] determinism: 순서 의존 — {[e.path for e in out1]} vs {[e.path for e in out2]}")
        else:
            print("  [8] determinism   ✓  (입력 순서 무관, (source_host_id, branch, path) 정렬)")

    print()
    if failures:
        print(f"FAIL: {len(failures)} case(s) failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL PASS: registry federation 8 case (merge / known_hosts CRUD / determinism)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
