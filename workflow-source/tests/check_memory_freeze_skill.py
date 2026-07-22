#!/usr/bin/env python3
"""Smoke test — `memory-freeze` skill (R8) 의 실행 계약.

기존 `check_memory_freeze_lint.py` 는 **archive 무결성(R10)** 을 보는 lint 이지
skill 자체를 실행하지 않는다. 그래서 이 skill 이 v0.6.6(`6a9126c`) 부터 2026-07-22
까지 **문법 오류로 실행조차 불가능** 했는데도 아무 smoke 가 잡지 못했다.

본 test 는 skill 을 **실제로 실행**해 계약을 검증한다. 모든 case 는 temp 디렉터리
위에서 돌며 저장소의 `ai-workflow/memory/` 를 건드리지 않는다.

6 case:
  1. 정상 freeze — status=success + `.frozen` marker + frozen_files 비어있지 않음
  2. **recursive 포함** — `active/<branch>/` 하위 파일이 상대경로를 보존한 채 복사
  3. 중복 freeze — 같은 날짜 재실행 시 status=skipped (immutability 보존)
  4. `--freeze-date` override 가 archive 디렉터리 이름에 반영
  5. error: active dir 부재 → error_code=ACTIVE_DIR_MISSING, exit 1
  6. error: freeze 대상 0 → error_code=NO_FILES, exit 1
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = (
    REPO_ROOT / "workflow-source" / "skills" / "memory-freeze"
    / "scripts" / "run_memory_freeze.py"
)


def _run(active: Path, archive: Path, *extra: str) -> tuple[int, dict]:
    """skill 실행 → (exit_code, payload).

    스크립트는 `Path.cwd()` 기준으로 상대경로를 푸므로 절대경로를 넘긴다.
    """
    proc = subprocess.run(
        [
            sys.executable, str(SKILL),
            "--active-root", str(active),
            "--archive-root", str(archive),
            *extra,
        ],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"JSON 출력 아님 (exit {proc.returncode}): {exc}\n"
            f"stdout={proc.stdout[:400]}\nstderr={proc.stderr[:400]}"
        )
    return proc.returncode, payload


def _make_active(root: Path) -> Path:
    """branch-scoped layout 을 가진 최소 active/ 를 만든다."""
    active = root / "active"
    (active / "main" / "backlog" / "tasks").mkdir(parents=True)
    (active / "main" / "sessions").mkdir(parents=True)
    (active / "PROJECT_PROFILE.md").write_text("# profile\n", encoding="utf-8")
    (active / "state.json.template").write_text("{}\n", encoding="utf-8")
    (active / "main" / "state.json").write_text('{"session": {}}\n', encoding="utf-8")
    (active / "main" / "backlog" / "2026-07-22.md").write_text("# backlog\n", encoding="utf-8")
    (active / "main" / "sessions" / "s1.md").write_text("# session\n", encoding="utf-8")
    return active


def case_1_success() -> bool:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        active = _make_active(root)
        archive = root / "archive"
        rc, payload = _run(active, archive)
        if rc != 0 or payload.get("status") != "success":
            print(f"  FAIL: rc={rc}, status={payload.get('status')!r}")
            return False
        if not payload.get("frozen_files"):
            print("  FAIL: frozen_files 비어 있음")
            return False
        archive_dir = Path(payload["archive_path"])
        if not (archive_dir / ".frozen").exists():
            print("  FAIL: .frozen marker 부재")
            return False
        marker = (archive_dir / ".frozen").read_text(encoding="utf-8")
        if "frozen_at" not in marker:
            print("  FAIL: .frozen 에 frozen_at 부재")
            return False
    return True


def case_2_recursive() -> bool:
    """`active/<branch>/` 하위가 상대경로를 보존한 채 freeze 되는가.

    이전 구현은 최상위만 복사해 state.json / backlog / sessions 가 통째로 빠졌다.
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        active = _make_active(root)
        archive = root / "archive"
        rc, payload = _run(active, archive)
        if rc != 0:
            print(f"  FAIL: rc={rc}")
            return False
        archive_dir = Path(payload["archive_path"])
        required = [
            "PROJECT_PROFILE.md",
            "state.json.template",
            "main/state.json",
            "main/backlog/2026-07-22.md",
            "main/sessions/s1.md",
        ]
        missing = [r for r in required if not (archive_dir / r).exists()]
        if missing:
            print(f"  FAIL: recursive freeze 누락: {missing}")
            return False
        frozen = set(payload.get("frozen_files") or [])
        if "main/state.json" not in frozen:
            print(f"  FAIL: frozen_files 에 하위 경로 미포함: {sorted(frozen)[:6]}")
            return False
    return True


def case_3_duplicate_skipped() -> bool:
    """같은 날짜 재freeze → skipped (archive immutability 보존)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        active = _make_active(root)
        archive = root / "archive"
        rc1, _ = _run(active, archive)
        if rc1 != 0:
            print(f"  FAIL: 1차 freeze rc={rc1}")
            return False
        # 1차 이후 active 를 바꿔도 archive 는 덮어써지지 않아야 한다.
        (active / "PROJECT_PROFILE.md").write_text("# CHANGED\n", encoding="utf-8")
        rc2, payload2 = _run(active, archive)
        if rc2 != 0 or payload2.get("status") != "skipped":
            print(f"  FAIL: 2차 rc={rc2}, status={payload2.get('status')!r} (expected skipped)")
            return False
        frozen_profile = Path(payload2["archive_path"]) / "PROJECT_PROFILE.md"
        if "CHANGED" in frozen_profile.read_text(encoding="utf-8"):
            print("  FAIL: 중복 freeze 가 archive 를 덮어썼다 (immutability 위반)")
            return False
    return True


def case_4_freeze_date_override() -> bool:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        active = _make_active(root)
        archive = root / "archive"
        rc, payload = _run(active, archive, "--freeze-date", "2020-01-02")
        if rc != 0:
            print(f"  FAIL: rc={rc}")
            return False
        if Path(payload["archive_path"]).name != "2020-01-02":
            print(f"  FAIL: archive_path={payload['archive_path']!r}")
            return False
    return True


def case_5_active_dir_missing() -> bool:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        rc, payload = _run(root / "nonexistent", root / "archive")
        if rc != 1 or payload.get("error_code") != "ACTIVE_DIR_MISSING":
            print(f"  FAIL: rc={rc}, error_code={payload.get('error_code')!r}")
            return False
    return True


def case_6_no_files() -> bool:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        active = root / "active"
        active.mkdir()
        (active / "binary.bin").write_bytes(b"\x00\x01")  # freeze 대상 확장자 아님
        rc, payload = _run(active, root / "archive")
        if rc != 1 or payload.get("error_code") != "NO_FILES":
            print(f"  FAIL: rc={rc}, error_code={payload.get('error_code')!r}")
            return False
    return True


CASES = [
    ("case_1_success", case_1_success),
    ("case_2_recursive", case_2_recursive),
    ("case_3_duplicate_skipped", case_3_duplicate_skipped),
    ("case_4_freeze_date_override", case_4_freeze_date_override),
    ("case_5_active_dir_missing", case_5_active_dir_missing),
    ("case_6_no_files", case_6_no_files),
]


def main() -> int:
    print("=== memory-freeze skill (R8) 실행 계약 ===")
    results = [(name, fn()) for name, fn in CASES]
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"=== {passed}/{len(CASES)} PASS ===")
    return 0 if passed == len(CASES) else 1


def test_case_1_success() -> None:
    assert case_1_success(), "case_1_success FAIL"


def test_case_2_recursive() -> None:
    assert case_2_recursive(), "case_2_recursive FAIL"


def test_case_3_duplicate_skipped() -> None:
    assert case_3_duplicate_skipped(), "case_3_duplicate_skipped FAIL"


def test_case_4_freeze_date_override() -> None:
    assert case_4_freeze_date_override(), "case_4_freeze_date_override FAIL"


def test_case_5_active_dir_missing() -> None:
    assert case_5_active_dir_missing(), "case_5_active_dir_missing FAIL"


def test_case_6_no_files() -> None:
    assert case_6_no_files(), "case_6_no_files FAIL"


if __name__ == "__main__":
    sys.exit(main())
