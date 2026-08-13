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

**실행-중 감시 (v1.1.8, TASK-2026-08-12-main-009)**: 전후 비교는 "건드렸다
되돌리면 통과" 한다 — `check_bidir_link_v0_13_3` 은 감시 목록에 **있으면서도**
그 이유로 안 잡혔다 (§6 리스크, transient pyproject writer 미스터리와 같은 뿌리).
그래서 실행 *중* `git status --porcelain` 을 ~0.15s 간격으로 폴링해, 끝날 때는
깨끗해도 **중간에 나타난 변경**을 잡는다. 미지의 transient 접촉은 FAIL 이고,
알려진 touch-and-restore 는 `KNOWN_TRANSIENT_TOUCHERS` 원장에 이유와 함께 둔다.
한계 (과장하지 않는다): 폴링은 타이밍 의존이라 **음성은 증명이 아니다** — 짧은
접촉은 놓칠 수 있어 원장은 단방향이고, 검출은 best-effort 추가 방어층이다.

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
    # v1.1.2: rotate CLI 를 부른다. 예전에는 rotate 가 고장나 늘 `error` 였던 탓에
    # 아무것도 안 썼고, 그래서 이 검사가 실제 handoff 를 겨누고 있다는 사실이
    # 드러나지 않았다. 도구를 고치는 순간 저장소를 수정하기 시작했다.
    "check_cli_wrappers.py",
    # v1.1.4: release dry-run 을 실호출한다. `release --dry-run` 이 저장소 문서
    # 63개를 write 하던 전력이 있는 계열이라 (경로 1·5 와 같은 뿌리) 감시 대상.
    "check_release_pre_check_gates.py",
    # v1.1.7(TASK-019): 원본 저장소에 `--apply` 하던 것을 사본으로 옮긴 4건.
    # 각 파일이 자체적으로 "원본 무손상" 을 assert 하지만, 이 목록에도 넣어 이중으로
    # 막는다. 되돌리는 구현으로 회귀하면 여기서도 걸리게 하려는 것이다.
    "check_release_pipeline_version_auto_sync.py",   # pyproject / __init__ (--apply)
    "check_self_recovering_v0_13_2.py",              # README / pyproject / __init__ (drift 주입)
    "check_release_pipeline_phase3.py",              # dist 실빌드 산출물
    # v1.1.9(TASK-2026-08-13-main-001): 원본 pyproject 를 bump 했다 되돌리던 마지막
    # writer (watch_transient_writer 실측으로 전량 중 유일한 왕복이었다) 를 사본으로
    # 이관. 되돌리는 구현으로 회귀하면 실행-중 폴링이 왕복을 잡는다.
    "check_release_pipeline.py",                     # version-bump --apply (sandbox 이관)
    # v1.1.9(TASK-2026-08-13-main-001): P4 에서 plugin/ manifest 3장이 sandbox 실행에
    # 원본째 덮인 사고 계열 (case 13 이 뿌리를 막았고, 여기는 이중 방어).
    # plugin/ 산출물은 전부 git 추적이므로 이 검사의 porcelain/digest 감시 범위다.
    "check_agent_plugin_payload.py",                 # plugin/ + .claude-plugin/ byte 대조 + 되주입
)

CHECK_TIMEOUT_SEC = 300

#: 실행 *중* 추적 파일을 건드렸다 되돌리는 것이 **알려진** check — 이유를 명시한다.
#: 폴링이 타이밍 의존이라 "반드시 관측된다" 는 단언은 불가 — 단방향 원장 (case 9
#: 류의 양방향 판정을 여기 쓰면 flake 가 된다). 새 항목 추가는 그 check 를 사본
#: 위로 옮길 수 없는 이유가 있을 때만.
KNOWN_TRANSIENT_TOUCHERS: dict[str, str] = {}


REQUIRES_QUIET_REPO = True
"""이 check 는 실행 전후의 `git status` + tracked digest 를 **전역으로** 비교한다.

같은 순간 다른 check 가 무엇이든 건드리면 그것을 감시 대상의 소행으로 오탐한다 —
관찰 대상이 저장소 자신이라 격리로는 풀리지 않는다. runner 가 이 선언을 보고
정숙 구간(병렬 구간이 끝난 뒤 직렬)에 배치한다."""
def _porcelain(repo_root: Path = REPO_ROOT) -> str:
    return subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(repo_root), capture_output=True, text=True, timeout=60,
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


def _run_with_polling(
    cmd: list[str],
    *,
    repo_root: Path = REPO_ROOT,
    env: dict[str, str] | None = None,
    interval: float = 0.15,
    timeout: float = CHECK_TIMEOUT_SEC,
) -> set[str]:
    """명령을 실행하며 porcelain 을 폴링 — 실행 *중* baseline 대비 나타난 변경 라인.

    반환은 폴링 스냅샷들에서 관측된 변경의 합집합이다 (끝날 때 복원돼도 남는다).
    """
    import os
    import time
    baseline = set(_porcelain(repo_root).splitlines())
    transient: set[str] = set()
    proc = subprocess.Popen(
        cmd, cwd=str(repo_root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, **(env or {})},
    )
    deadline = time.monotonic() + timeout
    try:
        while proc.poll() is None:
            if time.monotonic() > deadline:
                proc.kill()
                proc.wait(timeout=10)
                raise TimeoutError(f"timeout: {' '.join(cmd[:2])}")
            transient |= set(_porcelain(repo_root).splitlines()) - baseline
            time.sleep(interval)
    finally:
        if proc.poll() is None:
            proc.kill()
    return transient


def _run_check(name: str, tmp_dir: str) -> set[str]:
    path = TESTS_DIR / name
    if not path.exists():
        return set()
    return _run_with_polling(
        [sys.executable, str(path)], env={"TMPDIR": tmp_dir},
    )


def test_watched_checks_do_not_touch_repo() -> None:
    """감시 대상 check 실행이 추적 파일 상태를 바꾸지 않는다."""
    missing = [n for n in WATCHED_CHECKS if not (TESTS_DIR / n).exists()]
    assert not missing, f"감시 목록에 존재하지 않는 check: {missing}"

    offenders: list[str] = []
    transient_offenders: list[str] = []
    with tempfile.TemporaryDirectory(prefix="no-repo-write-") as td:
        for name in WATCHED_CHECKS:
            before = _snapshot()
            transient = _run_check(name, td)
            after = _snapshot()
            if before != after:
                before_set = set(before[0].splitlines())
                changed = [ln for ln in after[0].splitlines() if ln not in before_set]
                detail = changed[:5] if changed else ["(status 동일 — 내용이 복원/변경됨)"]
                offenders.append(f"{name}: {detail}")
                # 다음 대상 판정을 오염시키지 않도록 기준선을 갱신한다.
                # (복구는 하지 않는다 — 여기서 git checkout 을 돌리면 본 check 자신이
                #  경로 4 와 같은 파괴형이 된다.)
            elif transient:
                # 끝은 깨끗했지만 *중간에* 건드렸다 — 되돌리는 것은 안 건드리는 것이 아니다.
                if name in KNOWN_TRANSIENT_TOUCHERS:
                    print(f"  [info] {name}: 알려진 transient 접촉 "
                          f"({KNOWN_TRANSIENT_TOUCHERS[name]}) — {sorted(transient)[:3]}")
                else:
                    transient_offenders.append(f"{name}: {sorted(transient)[:5]}")

    assert not offenders, (
        f"{len(offenders)}개 check 가 추적 중인 저장소 파일을 건드렸다:\n  "
        + "\n  ".join(offenders)
        + "\n\n→ 해당 check 는 temp 사본 위에서 돌거나, 도구의 경로 override "
          "(예: --maturity-path) 를 써야 한다. dry-run 이라면 도구가 dry-run 을 "
          "상속하지 않는 버그일 수 있다."
    )
    assert not transient_offenders, (
        f"{len(transient_offenders)}개 check 가 실행 중 추적 파일을 건드렸다 되돌렸다:\n  "
        + "\n  ".join(transient_offenders)
        + "\n\n→ 되돌리는 것은 안 건드리는 것이 아니다 — 사본 위에서 돌게 고치거나, "
          "불가피하면 KNOWN_TRANSIENT_TOUCHERS 에 이유와 함께 등록할 것."
    )
    print(f"  {len(WATCHED_CHECKS)} 감시 대상 check 모두 저장소 변경 0 (실행-중 포함)")


def test_polling_detects_touch_and_restore() -> None:
    """되주입: 건드렸다 되돌리는 스크립트를 폴링이 잡는다 (fixture 저장소)."""
    with tempfile.TemporaryDirectory(prefix="no-repo-write-reinject-") as td:
        repo = Path(td).resolve() / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(repo), check=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=str(repo), check=True)
        target = repo / "tracked.txt"
        target.write_text("original\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(repo), check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=str(repo), check=True)

        toucher = repo / "toucher.py"
        toucher.write_text(
            "import time, pathlib\n"
            "p = pathlib.Path('tracked.txt')\n"
            "p.write_text('touched')\n"
            "time.sleep(1.0)\n"
            "p.write_text('original\\n')\n",
            encoding="utf-8",
        )
        transient = _run_with_polling(
            [sys.executable, str(toucher)], repo_root=repo, interval=0.05, timeout=30,
        )
        assert any("tracked.txt" in line for line in transient), (
            f"폴링이 touch-and-restore 를 놓쳤다: {transient}"
        )
        assert _porcelain(repo).strip() == "?? toucher.py", "fixture 종료 상태가 예상과 다르다"

        clean = repo / "clean.py"
        clean.write_text("print('no touch')\n", encoding="utf-8")
        transient2 = _run_with_polling(
            [sys.executable, str(clean)], repo_root=repo, interval=0.05, timeout=30,
        )
        transient2 = {line for line in transient2 if "clean.py" not in line}
        assert not {line for line in transient2 if "tracked.txt" in line}, (
            f"무접촉 스크립트에서 위양성: {transient2}"
        )


def main() -> int:
    print("=== 저장소 write 금지 메타 체크 ===")
    passed = 0
    for fn in (test_polling_detects_touch_and_restore, test_watched_checks_do_not_touch_repo):
        try:
            fn()
        except AssertionError as exc:
            print(f"  FAIL: {fn.__name__}: {exc}")
            print(f"=== FAIL: {passed}/2 ===")
            return 1
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL: {fn.__name__}: {type(exc).__name__}: {exc}")
            print(f"=== FAIL: {passed}/2 ===")
            return 1
        print(f"  PASS: {fn.__name__}")
        passed += 1
    print("=== PASS: 2/2 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
