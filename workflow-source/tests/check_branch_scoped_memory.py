#!/usr/bin/env python3
"""v1.0.0: branch-scoped memory + 종료 브랜치 자동 아카이브 smoke (10 cases).

검증 대상:
  1) path helper 가 `active/<branch>/` 를 반환한다
  2) legacy fallback — 미마이그레이션 저장소(`active/backlog/`)는 깨지지 않는다
  3) task ID 가 `TASK-<date>-<slug>-<NNN>` 이고 **연도를 순번으로 오인하지 않는다**
     (기존 `TASK-(\\d+)` 정규식이 `TASK-2026-07-20-001` → `TASK-2027` 을 만들던 버그)
  4) 다른 브랜치의 task 번호는 순번에 영향을 주지 않는다 (동시 작업 충돌 0)
  5) branch slug 정규화 (`feature/x` → `feature-x`)
  6) 아카이버가 git 에 없는 브랜치를 탐지한다
  7) 아카이버가 살아있는 브랜치 / 현재 브랜치는 건드리지 않는다
  8) 아카이브 결과에 `.archived.json` 메타(task_ids 포함)가 남는다
  9) 슬래시 브랜치가 끝까지 동작한다 — 중첩 dir + 슬러그 파일명 (main 에서는 안 드러난다)
  10) CI 가 슬래시 브랜치 컨텍스트를 실제로 돌린다 (9 는 코드, 10 은 그 검증의 실행 보장)

Refs:
  - workflow-source/MEMORY_GOVERNANCE.md §2 (Branch-scoped layout)
  - ai-workflow/memory/active/README.md §1
  - workflow-source/workflow_kit/tools/archive_branch_memory.py
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import paths as P  # noqa: E402

ARCHIVER = SOURCE_ROOT / "workflow_kit" / "tools" / "archive_branch_memory.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_profile(root: Path, *, branch_scoped: bool, branch: str = "main") -> Path:
    """temp 저장소에 PROJECT_PROFILE.md + layout 을 만든다."""
    active = root / "ai-workflow" / "memory" / "active"
    base = (active / branch) if branch_scoped else active
    (base / "backlog" / "tasks").mkdir(parents=True, exist_ok=True)
    (base / "sessions").mkdir(parents=True, exist_ok=True)
    (base / "state.json").write_text("{}", encoding="utf-8")
    profile = active / "PROJECT_PROFILE.md"
    profile.write_text("# profile\n", encoding="utf-8")
    return profile


# --- case 1: branch-scoped 해석 ---
def case_1_branch_scoped_paths() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        branch = P.get_current_branch()
        profile = _make_profile(root, branch_scoped=True, branch=branch)
        backlog = P.workflow_backlog_dir(profile)
        # 슬래시 브랜치는 **중첩 디렉터리**가 된다(`active/feature/x/backlog`). 그래서
        # 마지막 한 컴포넌트(`.name`)를 브랜치명과 비교하면 안 된다 — `slash-probe` 와
        # `feature/slash-probe` 를 비교하게 되어, 경로가 옳은데도 FAIL 이 난다.
        # active/ 로부터의 **상대 경로 전체**로 판정한다.
        # macOS /tmp symlink 함정 (TASK-2026-08-11-main-017 §2챕터) — `P.workflow_backlog_dir`
        # 가 `Path.resolve()` 후 `/private/var/folders/...` prefix 를 돌려주지만
        # `root` 가 mktemp 의 raw `/var/folders/...` 라 prefix mismatch 로
        # `relative_to()` 가 `ValueError: ... is not in the subpath of ...` 를 raise.
        # `active` 도 resolve() 로 통일한다.
        active = P.memory_active_dir(root).resolve()
        got = backlog.parent.relative_to(active).as_posix()
        if got != branch:
            print(f"  FAIL: backlog 가 branch dir 하위가 아님: {backlog} (기대 branch={branch}, 실제={got})")
            return False
        if P.workflow_tasks_dir(profile) != backlog / "tasks":
            print("  FAIL: tasks_dir 불일치")
            return False
        print(f"  PASS: active/<branch>/backlog 로 해석 ({got})")
        return True


# --- case 2: legacy fallback ---
def case_2_legacy_fallback() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profile = _make_profile(root, branch_scoped=False)
        backlog = P.workflow_backlog_dir(profile)
        if backlog.name != "backlog" or backlog.parent.name != "active":
            print(f"  FAIL: legacy fallback 실패: {backlog}")
            return False
        state = P.workflow_state_path(profile)
        if state.parent.name != "active":
            print(f"  FAIL: state legacy fallback 실패: {state}")
            return False
        print("  PASS: 미마이그레이션 저장소는 legacy(active/) 로 fallback")
        return True


# --- case 3~5: task ID ---
def _backlog_mod():
    # v1.1.7+ (TASK-2026-08-11-main-021): 구현이 `tools/backlog_update.py` 로 옮겨졌다.
    # `skills/.../run_backlog_update.py` 는 이제 `main` 만 재수출하는 wrapper 라
    # `branch_slug` / `suggest_next_task_id` 같은 내부 심볼이 없다. 검사는 **구현체**를
    # 본다 — skills/ 는 pip 패키지에도 bootstrap 번들에도 안 들어가서 소비자에게는
    # 존재하지 않는 경로다 (TASK-020 진단).
    return _load(SOURCE_ROOT / "workflow_kit" / "tools" / "backlog_update.py", "_bu_mod")


def case_3_task_id_no_year_confusion() -> bool:
    m = _backlog_mod()
    got = m.suggest_next_task_id([{"task_id": "TASK-2026-07-20-001"}], target_date="2026-07-20")
    if got.startswith("TASK-2027") or "-2027" in got:
        print(f"  FAIL: 연도를 순번으로 오인: {got}")
        return False
    if not got.endswith("-002"):
        print(f"  FAIL: 같은 날짜 legacy ID 다음은 002 여야 함: {got}")
        return False
    print(f"  PASS: 연도 오인 없음 ({got})")
    return True


def case_4_other_branch_does_not_bump() -> bool:
    m = _backlog_mod()
    slug = m.branch_slug()
    other = [{"task_id": f"TASK-2026-07-21-someotherbranch-007"}]
    got = m.suggest_next_task_id(other, target_date="2026-07-21")
    if not got.endswith("-001"):
        print(f"  FAIL: 다른 브랜치 번호가 순번에 영향: {got}")
        return False
    if slug not in got:
        print(f"  FAIL: 현재 브랜치 slug 미포함: {got}")
        return False
    print(f"  PASS: 다른 브랜치는 순번에 영향 없음 ({got})")
    return True


def case_5_branch_slug_normalization() -> bool:
    m = _backlog_mod()
    if m.branch_slug("feature/x") != "feature-x":
        print(f"  FAIL: slug 정규화 실패: {m.branch_slug('feature/x')}")
        return False
    if "/" in m.branch_slug("a/b/c"):
        print("  FAIL: slug 에 '/' 잔존")
        return False
    print("  PASS: branch slug 정규화 (feature/x → feature-x)")
    return True


# --- case 6~8: 아카이버 ---
def _run_archiver(memory_root: Path, *args: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(ARCHIVER), "--memory-root", str(memory_root), "--json", *args],
        capture_output=True, text=True, timeout=60,
    )
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def _seed_branch(memory_root: Path, branch: str) -> None:
    """브랜치 메모리 하나를 만든다 — **제품이 실제로 쓰는 모양 그대로**.

    디렉터리는 브랜치명 그대로라 슬래시가 있으면 중첩되지만(`active/feature/x/`),
    **task 파일명은 슬러그**다(`TASK-<date>-feature-x-001.md`). 이전 구현은 파일명에도
    raw 브랜치를 써서 `feature/x` 에서 `TASK-…-feature/x-001.md` 라는 *경로* 가 됐고,
    없는 디렉터리에 쓰려다 `FileNotFoundError` 로 죽었다 — 제품은 그런 이름을 만들지
    않으므로 **fixture 가 제품을 잘못 흉내 낸 것**이었다. 슬러그는 제품에서 가져온다.
    """
    slug = _backlog_mod().branch_slug(branch)
    d = memory_root / "active" / branch / "backlog" / "tasks"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"TASK-2026-07-21-{slug}-001.md").write_text("# t\n", encoding="utf-8")


def case_6_detect_dead_branch() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        mr = Path(tmp)
        _seed_branch(mr, "definitely-not-a-real-branch-xyz")
        res = _run_archiver(mr)
        acts = [c for c in res.get("candidates", []) if c["action"] == "archive"]
        if not any("definitely-not-a-real-branch-xyz" == c["branch"] for c in acts):
            print(f"  FAIL: 종료 브랜치 미탐지: {res.get('candidates')}")
            return False
        print("  PASS: git 에 없는 브랜치를 아카이브 대상으로 탐지")
        return True


def case_7_keep_current_and_live() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        mr = Path(tmp)
        current = P.get_current_branch()
        _seed_branch(mr, current)
        res = _run_archiver(mr)
        for c in res.get("candidates", []):
            if c["branch"] == current and c["action"] == "archive":
                print(f"  FAIL: 현재 브랜치를 아카이브 대상으로 판정: {c}")
                return False
        print(f"  PASS: 현재/살아있는 브랜치는 보존 ({current})")
        return True


def case_9_slash_branch_end_to_end() -> bool:
    """9) 슬래시 브랜치가 **끝까지** 동작한다 — 중첩 디렉터리 + 슬러그 파일명.

    `feature/x` 는 `active/feature/x/` 라는 **중첩** 디렉터리가 되므로, 브랜치를
    `iterdir()` 한 단계로 세는 코드는 `feature` 를 브랜치로 착각한다. 아카이버는
    이미 `rglob` 으로 이 경우를 처리하지만, **그 사실을 밟아 보는 case 가 없었다** —
    그래서 이 경로는 아무도 검증하지 않은 채로 있었다.

    슬래시가 없으면 이 결함들이 전부 드러나지 않는다는 점이 핵심이다(main 에서는 안 보인다).
    """
    branch = "feature/slash-e2e-probe"
    with tempfile.TemporaryDirectory() as tmp:
        mr = Path(tmp)
        _seed_branch(mr, branch)

        # (a) 중첩 디렉터리로 만들어졌다 — 부모(`feature`)는 브랜치가 아니다.
        nested = mr / "active" / "feature" / "slash-e2e-probe"
        if not nested.is_dir():
            print(f"  FAIL: 중첩 디렉터리 미생성: {nested}")
            return False

        # (b) 아카이버가 `feature` 가 아니라 `feature/slash-e2e-probe` 를 브랜치로 본다.
        res = _run_archiver(mr)
        names = {c["branch"] for c in res.get("candidates", [])}
        if branch not in names:
            print(f"  FAIL: 슬래시 브랜치를 브랜치로 못 봤다 — 후보={sorted(names)}")
            return False
        if "feature" in names:
            print(f"  FAIL: 상위 디렉터리 `feature` 를 브랜치로 오인 — 후보={sorted(names)}")
            return False

        # (c) task ID 는 슬러그라 경로 구분자가 안 들어간다.
        got = _backlog_mod().suggest_next_task_id([], target_date="2026-07-21", branch=branch)
        if "/" in got:
            print(f"  FAIL: task ID 에 경로 구분자: {got}")
            return False

        # (d) 실제로 아카이브하면 **중첩 경로 그대로** 옮겨지고 메타가 온전하다.
        #     (task_ids 는 dry-run 후보가 아니라 `--apply` 후 `.archived.json` 에 있다.)
        _run_archiver(mr, "--apply")
        meta_path = mr / "archived" / "feature" / "slash-e2e-probe" / ".archived.json"
        if not meta_path.is_file():
            print(f"  FAIL: 중첩 경로로 아카이브되지 않았다: {meta_path}")
            return False
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        ids = data.get("task_ids", [])
        if data.get("branch") != branch or not ids or any("/" in i for i in ids):
            print(f"  FAIL: 메타 이상: {data}")
            return False
        if (mr / "active" / "feature" / "slash-e2e-probe").exists():
            print("  FAIL: 원본이 active/ 에 남아있음")
            return False

    print(f"  PASS: 중첩 dir + 슬러그 ID ({got}) + 아카이버 인식 ({branch})")
    return True


def case_8_archive_emits_metadata() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        mr = Path(tmp)
        branch = "gone-branch-for-smoke"
        _seed_branch(mr, branch)
        _run_archiver(mr, "--apply")
        dst = mr / "archived" / branch
        meta = dst / ".archived.json"
        if not meta.is_file():
            print(f"  FAIL: .archived.json 부재 ({dst})")
            return False
        data = json.loads(meta.read_text(encoding="utf-8"))
        if data.get("branch") != branch or data.get("task_count") != 1:
            print(f"  FAIL: 메타데이터 불일치: {data}")
            return False
        if (mr / "active" / branch).exists():
            print("  FAIL: 원본이 active/ 에 남아있음")
            return False
        print(f"  PASS: archived/{branch}/ 이동 + 메타(task_ids {data['task_ids']})")
        return True


def case_10_ci_runs_a_slash_branch_context() -> bool:
    """10) CI 가 **슬래시 브랜치 컨텍스트를 실제로 돌린다**.

    §2.55 의 결함 3건이 오래 살아 있던 이유는 단순하다 — 개발이 거의 main 에서
    이뤄지므로 슬래시 브랜치를 밟는 실행이 **아무도 보장하지 않는 우연**이었다.
    §2.56 이 smoke 를 2셀 matrix 로 만들어 그 우연을 없앴는데, 그 셀은 지우기 쉽다.
    선언만 있고 검사가 없으면 드리프트한다.

    `case_9` 는 *코드* 가 슬래시를 감당하는지 보고, 이 case 는 *그 검증이 CI 에서
    실제로 도는지* 를 본다 — 다른 층이다.
    """
    wf = REPO_ROOT / ".github" / "workflows" / "smoke.yml"
    if not wf.is_file():
        print(f"  FAIL: {wf} 부재")
        return False

    # v1.1.7(TASK-017): 셀 목록은 더 이상 yml 인라인이 아니다 — 정본
    # (`branch_matrix.BRANCH_CONTEXTS`) 을 prepare job 이 주입한다. 그래서 여기서도
    # 정본을 읽는다. yml 을 파싱해 셀을 세던 이전 판은 그 전환에서 정확히 깨졌고
    # (`fromJSON` 표현식은 dict 가 아니라 문자열이다), 그것이 이 case 가 살아 있다는
    # 증거이기도 하다.
    from workflow_kit.common.branch_matrix import BRANCH_CONTEXTS

    cells = BRANCH_CONTEXTS
    slashed = [c for c in cells if "/" in c.workflow_branch]
    if not slashed:
        print(f"  FAIL: 슬래시가 든 브랜치 셀이 없다: {[c.label for c in cells]}")
        return False
    native = [c for c in cells if not c.workflow_branch]
    if not native:
        print("  FAIL: 오버라이드 없는 셀이 없다 — 실제 브랜치를 재는 실행이 사라졌다: "
              f"{[c.label for c in cells]}")
        return False

    src = wf.read_text(encoding="utf-8")
    # CI 가 그 정본을 실제로 소비하는가 (선언만 있고 CI 가 안 읽으면 의미가 없다).
    if "workflow_kit.common.branch_matrix --github-matrix" not in src:
        print("  FAIL: smoke.yml 이 정본에서 셀 목록을 받지 않는다 — 슬래시 컨텍스트 미보장")
        return False
    # 오버라이드가 안 먹었을 때 조용히 넘어가지 않는지 (workflow 안의 자기 검증)
    if "브랜치 오버라이드가 적용되지 않았다" not in src:
        print("  FAIL: 오버라이드 적용 여부를 workflow 가 강제하지 않는다 — "
              "안 먹으면 두 셀이 같은 것을 재면서 '2셀 green' 이 된다")
        return False
    print(f"  PASS: CI 가 정본의 {len(cells)}셀로 돈다 "
          f"(슬래시={slashed[0].workflow_branch}, native 셀 존재, 오버라이드 자기 검증 있음)")
    return True


def main() -> int:
    print("=" * 60)
    print("branch-scoped memory + 자동 아카이브 smoke (v1.0.0)")
    print("=" * 60)
    cases = [
        case_1_branch_scoped_paths,
        case_2_legacy_fallback,
        case_3_task_id_no_year_confusion,
        case_4_other_branch_does_not_bump,
        case_5_branch_slug_normalization,
        case_6_detect_dead_branch,
        case_7_keep_current_and_live,
        case_8_archive_emits_metadata,
        case_9_slash_branch_end_to_end,
        case_10_ci_runs_a_slash_branch_context,
    ]
    passed = 0
    for c in cases:
        print(f"\n{c.__name__}:")
        try:
            if c():
                passed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL: {type(exc).__name__}: {exc}")
    print()
    print("=" * 60)
    print(f"Result: {passed}/{len(cases)} PASS")
    print("=" * 60)
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
