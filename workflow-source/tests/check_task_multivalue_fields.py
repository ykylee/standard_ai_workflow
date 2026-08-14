#!/usr/bin/env python3
"""task SSOT 의 **다중값 필드** 계약을 고정한다 (12 cases).

## 계보 — 소실과 중복은 같은 뿌리다

`--done-criteria` 같은 열거형 필드가 단일값이었다. 그래서 두 가지가 함께 일어났다:

1. **소실** — 값을 여러 번 주면 `argparse` 가 마지막 하나만 남겼다. 2026-08-14 실측:
   완료 기준 5건을 적었는데 1건만 들어갔고, diff 를 보고서야 알았다.
2. **중복** — 그걸 피하려고 값 안에 개행과 `- 완료 기준: ` 접두사를 끼워 넣었더니,
   `_set_inline_field` 가 **첫 줄만** 교체해서 2번째 이후가 남았다. update 두 번에
   같은 줄이 두 벌이 됐다.

둘 다 "열거인데 스칼라로 다뤘다" 하나에서 나온다. 그래서 처방도 하나다 —
`action="append"` + **묶음 단위 교체**(`_set_list_field`).

12 cases:
  1) create — 반복 지정한 값이 **전부** 남는다
  2) create — 값 하나면 한 줄
  3) create — 값이 없으면 빈 placeholder 한 줄 (형식 유지)
  4) update — 묶음이 통째로 교체된다 (3 → 2, 중복 ❌)
  5) update — **멱등**. 같은 값으로 두 번 돌리면 파일이 동일하다
  6) update — 지정하지 않은 다중값 필드는 보존된다
  7) update — 개수를 줄이면 남는 줄이 사라진다
  8) 묶음 교체가 **다른 절의 같은 라벨**까지 삼키지 않는다
  9) 자기 적용 — 저장소의 task 파일에 같은 라벨 줄이 **중복 누적**돼 있지 않다
 10) `검증 결과` 주입이 `작업 결과` 묶음 **끝** 뒤에 들어간다 (묶음을 안 가른다)
 11) 이미 갈라진 파일이 갱신 시 **치유**되고 고아 줄이 남지 않는다
 12) 자기 적용 — 저장소의 task 파일에 갈라진 묶음이 없다
"""

from __future__ import annotations

import glob as _glob
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = TESTS_DIR.parent
REPO_ROOT = SOURCE_ROOT.parent
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.workflow_writes import (  # noqa: E402
    _label_prefixes,
    _matches_label,
    _set_list_field,
    merge_task_file,
)

FAILURES: list[str] = []

#: **실제 저장소 프로파일을 쓰지 않는다.** `backlog-update --apply` 는 프로파일을
#: 기준으로 workspace 를 잡고 그 workspace 의 `state.json` 을 재생성한다. 실물
#: 프로파일을 넘기면 temp 안에서 돌린 fixture 가 **저장소의 state.json 을 덮어쓴다**
#: (2026-08-14 실측: `latest_backlog_path` 가 temp 경로를 가리켰다). 저장소가 이미
#: 아는 오염 계열이라, 프로파일 사본을 sandbox 안에 두고 그것만 가리킨다.
_REAL_PROFILE = REPO_ROOT / "docs" / "PROJECT_PROFILE.md"


def _sandbox_profile(root: Path) -> Path:
    dst = root / "docs" / "PROJECT_PROFILE.md"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(_REAL_PROFILE.read_text(encoding="utf-8"), encoding="utf-8")
    return dst


def _run_bu(backlog: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    import os
    # backlog 는 `<sandbox>/backlog/<date>.md` 이므로 sandbox root 는 parent.parent
    profile = _sandbox_profile(backlog.parent.parent)
    argv = [sys.executable, "-m", "workflow_kit.tools.backlog_update",
            "--project-profile-path", str(profile),
            "--daily-backlog-path", str(backlog),
            "--task-name", "테스트", "--task-brief", "브리프", "--apply", *extra]
    return subprocess.run(argv, cwd=str(SOURCE_ROOT), capture_output=True, text=True,
                          env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)}, timeout=180)


def _task_path(backlog: Path) -> Path:
    found = sorted((backlog.parent / "tasks").glob("*.md"))
    assert found, "task 파일이 생성되지 않았다"
    return found[0]


def _lines(path: Path, label: str) -> list[str]:
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip().startswith(f"- {label}:")]


def _fresh(root: Path) -> Path:
    b = root / "backlog" / "2026-08-14.md"
    b.parent.mkdir(parents=True, exist_ok=True)
    (b.parent / "tasks").mkdir(exist_ok=True)
    return b


def case_1_create_keeps_all(root: Path) -> None:
    b = _fresh(root)
    _run_bu(b, "--mode", "create",
            "--done-criteria", "A", "--done-criteria", "B", "--done-criteria", "C")
    got = _lines(_task_path(b), "완료 기준")
    assert got == ["- 완료 기준: A", "- 완료 기준: B", "- 완료 기준: C"], (
        f"반복 지정한 값이 소실됐다: {got}"
    )


def case_2_create_single(root: Path) -> None:
    b = _fresh(root)
    _run_bu(b, "--mode", "create", "--done-criteria", "하나")
    assert _lines(_task_path(b), "완료 기준") == ["- 완료 기준: 하나"]


def case_3_create_empty_placeholder(root: Path) -> None:
    b = _fresh(root)
    _run_bu(b, "--mode", "create")
    got = _lines(_task_path(b), "완료 기준")
    assert got == ["- 완료 기준:"], f"빈 placeholder 형식이 깨졌다: {got}"


def case_4_update_replaces_group(root: Path) -> None:
    b = _fresh(root)
    _run_bu(b, "--mode", "create", "--done-criteria", "A", "--done-criteria", "B",
            "--done-criteria", "C")
    tid = _task_path(b).stem
    _run_bu(b, "--mode", "update", "--task-id", tid,
            "--done-criteria", "X", "--done-criteria", "Y")
    got = _lines(_task_path(b), "완료 기준")
    assert got == ["- 완료 기준: X", "- 완료 기준: Y"], f"묶음 교체가 아니다: {got}"


def case_5_update_is_idempotent(root: Path) -> None:
    b = _fresh(root)
    _run_bu(b, "--mode", "create", "--done-criteria", "A")
    tid = _task_path(b).stem
    _run_bu(b, "--mode", "update", "--task-id", tid, "--done-criteria", "X", "--done-criteria", "Y")
    once = _task_path(b).read_text(encoding="utf-8")
    _run_bu(b, "--mode", "update", "--task-id", tid, "--done-criteria", "X", "--done-criteria", "Y")
    twice = _task_path(b).read_text(encoding="utf-8")
    # `진행 현황` 은 타임스탬프를 담아 매번 달라진다 — 그 줄만 빼고 비교한다.
    def _strip(text: str) -> list[str]:
        return [ln for ln in text.splitlines() if not ln.startswith("- 진행 현황:")]
    assert _strip(once) == _strip(twice), "같은 값으로 두 번 돌렸는데 파일이 달라졌다"


def case_6_update_preserves_untouched(root: Path) -> None:
    b = _fresh(root)
    _run_bu(b, "--mode", "create", "--done-criteria", "A", "--result-note", "R1",
            "--result-note", "R2")
    tid = _task_path(b).stem
    _run_bu(b, "--mode", "update", "--task-id", tid, "--done-criteria", "X")
    got = _lines(_task_path(b), "작업 결과")
    assert got == ["- 작업 결과: R1", "- 작업 결과: R2"], f"지정 안 한 필드가 바뀌었다: {got}"


def case_7_update_shrinks(root: Path) -> None:
    b = _fresh(root)
    _run_bu(b, "--mode", "create", "--done-criteria", "A", "--done-criteria", "B",
            "--done-criteria", "C")
    tid = _task_path(b).stem
    _run_bu(b, "--mode", "update", "--task-id", tid, "--done-criteria", "하나만")
    got = _lines(_task_path(b), "완료 기준")
    assert got == ["- 완료 기준: 하나만"], f"줄이 남았다: {got}"


def case_8_group_does_not_swallow_other_section() -> None:
    """연속한 묶음만 바꾼다 — 다른 절의 같은 라벨은 건드리지 않는다."""
    lines = [
        "- 완료 기준: A",
        "- 완료 기준: B",
        "",
        "## 다른 절",
        "- 완료 기준: 여기는 남아야 한다",
    ]
    out, found = _set_list_field(lines, "완료 기준", ["새 값"])
    assert found
    assert out == [
        "- 완료 기준: 새 값",
        "",
        "## 다른 절",
        "- 완료 기준: 여기는 남아야 한다",
    ], f"다른 절까지 삼켰다: {out}"


def case_9_self_no_accumulated_duplicates() -> None:
    """저장소의 task 파일에 **똑같은 줄이 연달아** 쌓여 있지 않다 (옛 중복의 흔적)."""
    labels = ("완료 기준", "작업 결과", "남은 리스크", "후속 작업")
    bad: list[str] = []
    for f in sorted(_glob.glob(str(REPO_ROOT / "ai-workflow/memory/**/backlog/tasks/*.md"),
                               recursive=True)):
        text = Path(f).read_text(encoding="utf-8").splitlines()
        for label in labels:
            group = [ln.strip() for ln in text if ln.strip().startswith(f"- {label}:")]
            dupes = {v for v in group if group.count(v) > 1}
            if dupes:
                bad.append(f"{Path(f).name} [{label}]: {sorted(dupes)[0][:60]}")
    assert not bad, "같은 줄이 중복 누적된 task:\n  " + "\n  ".join(bad[:15])


def case_10_validation_injects_after_group_end() -> None:
    """`검증 결과` 주입이 `작업 결과` 묶음 **끝** 뒤에 들어간다.

    첫 줄 뒤(idx+1)에 꽂던 때는 열거 묶음이 [a1][검증][a2][a3] 로 갈라졌다
    (main-010). 갈라짐은 조용하다 — 다음 갱신에서야 고아 줄로 나타난다.
    """
    body = ["# T", "- 상태: in_progress", "## ✅ Outcome", "", "- 작업 결과:", "- 후속 작업:"]
    body, _ = merge_task_file(body, status="in_progress",
                              list_updates={"작업 결과": ["a1", "a2", "a3"]},
                              scalar_updates={"검증 결과": "v1"}, affected_documents=None)
    got = [ln for ln in body if ln.startswith(("- 작업 결과:", "- 검증 결과:"))]
    assert got == ["- 작업 결과: a1", "- 작업 결과: a2", "- 작업 결과: a3",
                   "- 검증 결과: v1"], f"주입이 묶음을 갈랐다: {got}"


def case_11_split_file_heals_without_orphans() -> None:
    """이미 갈라진 파일이 갱신 시 치유되고 고아 줄이 남지 않는다.

    구버전 주입이 만든 디스크 상태 [a1][검증][a2][a3] 를 그대로 되주입한 뒤
    묶음을 2줄로 갱신한다 — 수리 전에는 a2·a3 가 옛 값 그대로 고아로 남았다.
    """
    split = ["# T", "- 상태: in_progress", "## ✅ Outcome", "",
             "- 작업 결과: a1", "- 검증 결과: v1", "- 작업 결과: a2", "- 작업 결과: a3",
             "- 후속 작업:"]
    healed, missing = merge_task_file(split, status="in_progress",
                                      list_updates={"작업 결과": ["b1", "b2"]},
                                      scalar_updates=None, affected_documents=None)
    orphans = [ln for ln in healed if ln.startswith("- 작업 결과: a")]
    assert not orphans, f"갈라진 뒤 조각이 고아로 남았다: {orphans}"
    got = [ln for ln in healed if ln.startswith(("- 작업 결과:", "- 검증 결과:"))]
    assert got == ["- 작업 결과: b1", "- 작업 결과: b2", "- 검증 결과: v1"], f"치유 결과가 다르다: {got}"
    assert not missing, f"필드를 놓쳤다: {missing}"


def case_12_self_no_split_groups() -> None:
    """자기 적용 — 저장소의 task 파일에 갈라진 묶음이 없다.

    갈라짐의 서명은 [작업 결과][검증 결과][작업 결과] 다. 실물에서 이 패턴이
    발견되면 구버전 주입이 만든 파일이 치유되지 않고 남아 있다는 뜻이다.
    """
    rp = _label_prefixes("작업 결과")
    vp = _label_prefixes("검증 결과")
    bad: list[str] = []
    for f in sorted(_glob.glob(str(REPO_ROOT / "ai-workflow/memory/**/backlog/tasks/*.md"),
                               recursive=True)):
        text = Path(f).read_text(encoding="utf-8").splitlines()
        for i in range(1, len(text) - 1):
            if (_matches_label(text[i].strip(), vp)
                    and _matches_label(text[i - 1].strip(), rp)
                    and _matches_label(text[i + 1].strip(), rp)):
                bad.append(Path(f).name)
                break
    assert not bad, "갈라진 묶음이 남은 task (wk backlog-update 로 touch 하면 치유된다):\n  " + "\n  ".join(bad[:10])


def _run(fn, needs_root: bool = True) -> None:
    try:
        if needs_root:
            with tempfile.TemporaryDirectory(prefix="check-multivalue-") as tmp:
                fn(Path(tmp).resolve())
        else:
            fn()
        print(f"  PASS  {fn.__name__}")
    except AssertionError as e:
        FAILURES.append(fn.__name__)
        print(f"  FAIL  {fn.__name__} — {e}")
    except Exception as e:  # noqa: BLE001
        FAILURES.append(fn.__name__)
        print(f"  FAIL  {fn.__name__} — 예외 {type(e).__name__}: {e}")


def main() -> int:
    print("=== task 다중값 필드 계약 ===")
    for fn in (case_1_create_keeps_all, case_2_create_single, case_3_create_empty_placeholder,
               case_4_update_replaces_group, case_5_update_is_idempotent,
               case_6_update_preserves_untouched, case_7_update_shrinks):
        _run(fn)
    for fn in (case_8_group_does_not_swallow_other_section, case_9_self_no_accumulated_duplicates,
               case_10_validation_injects_after_group_end, case_11_split_file_heals_without_orphans,
               case_12_self_no_split_groups):
        _run(fn, needs_root=False)
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    print("\n12/12 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
