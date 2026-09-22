#!/usr/bin/env python3
"""Meta-check: **저장소 write 감시 기전이 살아 있는가** (TASK-2026-09-22-main-008).

## 역할이 바뀌었다

예전 이 검사는 대표 표본 **16개**를 서브프로세스로 다시 돌려 전후를 비교했다.
그것이 전량 벽시계의 **35%**(76.7s)를 혼자 썼다 — 이미 병렬 구간에서 돈 검사를
정숙 구간에서 **또 직렬로** 도는 비용이다 (2026-09-22 실측: 벽시계 221s 중
정숙 구간 103s).

감시 자체는 **러너**(`workflow_kit/common/repo_write_watch.py`)로 옮겼다. 러너는
어차피 모든 검사를 서브프로세스로 돌리므로 거기서 보면:

    감시 범위   표본 16개 → **검사 전수(290)**
    정상 비용   76.7s 재실행 → 폴링 하나 (실측 `git status --porcelain` 12.7ms,
                0.5s 간격이면 221s 동안 5.6s)

그래서 이 검사가 할 일은 "표본이 깨끗한가" 가 아니라 **"그 기전이 실제로
잡는가"** 다. 전자는 이제 매 실행이 전수로 판정한다.

## 왜 실 저장소를 쓰지 않는가

기전을 확인하려면 **저장소를 건드리는 probe** 가 필요한데, 실 저장소에 쓰면
러너 자신의 감시에 걸려 게이트가 red 가 된다. 그래서 임시 git 저장소에
`RepoWriteWatch` 를 걸어 잰다 — 덕분에 `REQUIRES_QUIET_REPO` 도 필요 없고
(정숙 구간에서 빠졌다) 병렬로 ~1s 에 끝난다.

## 무엇을 잃었는지 (감추지 않는다)

귀속이 약해졌다. 예전에는 표본을 하나씩 돌려 "이 검사가 썼다" 였고, 지금은
"변경이 보인 시각에 돌던 검사들" 이다 (실측 동시성 중앙 9). 대신 커버리지가
16 → 290 이고, 범인을 좁혀야 하면 그 9개만 `--filter` 로 다시 돌리면 된다.

검증 케이스 (5):
    1. 끝까지 남는 변경을 `lingering` 으로 잡는다
    2. touch-and-restore 를 `transient` 로 잡고 **그때 돌던 검사**를 단다
    3. 아무것도 안 건드리면 둘 다 비어 있다 (위양성 없음)
    4. git 을 못 읽으면 **미측정**이다 — 통과로 세지 않는다
    5. 원장에 있는 접촉만 `known_transient` 로 빠지고 나머지는 미지로 남는다

Stdlib only.
"""

from __future__ import annotations

#: 전역 선언 (spec `core/test_impact_tiering_spec.md` §2). 감시 정본이 바뀌면 돈다.
WATCHES = (
    "workflow-source/workflow_kit/common/repo_write_watch.py",
    "workflow-source/tests/run_all_checks.py",
)

#: 이 검사가 강제하는 정본 요구 (spec §7).
ENFORCES = ("suite-must-not-write-the-repo",)

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"

# **패키지로 import 하지 않는다.** `import workflow_kit...` 은 `__init__` 을 끌고 와
# 이 검사의 입력 표면을 kit 전체(실측 42파일)로 넓힌다 — meta-watch 가 `좁은 선언`
# 으로 잡는다. 감시 모듈은 **stdlib only** 라 패키지가 필요 없으므로 파일 경로로
# 직접 읽어 표면을 한 파일로 유지한다 (`tests/_doc_stamp.py` 와 같은 처리).
# 사본이 아니라 같은 파일이므로 러너가 쓰는 판정과 byte 단위로 같다.
import importlib.util  # noqa: E402

_WATCH_SRC = SOURCE_ROOT / "workflow_kit" / "common" / "repo_write_watch.py"
_spec = importlib.util.spec_from_file_location("_repo_write_watch", _WATCH_SRC)
if _spec is None or _spec.loader is None:  # pragma: no cover
    raise ImportError(f"감시 정본을 못 읽었다: {_WATCH_SRC}")
_mod = importlib.util.module_from_spec(_spec)
sys.modules["_repo_write_watch"] = _mod
_spec.loader.exec_module(_mod)
RepoWriteWatch = _mod.RepoWriteWatch

_failures: list[str] = []
_passes: list[str] = []


def _ok(name: str, detail: str = "") -> None:
    _passes.append(name)
    print(f"  [PASS] {name}{(' — ' + detail) if detail else ''}")


def _fail(name: str, why: str) -> None:
    _failures.append(f"{name}: {why}")
    print(f"  [FAIL] {name}: {why}")


def _git(repo: Path, *args: str) -> None:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": str(repo / ".gitconfig"),
           "GIT_CONFIG_SYSTEM": os.devnull}
    subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)


def _fixture(tmp: Path) -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    (repo / "tracked.md").write_text("original\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed")
    return repo


def _watch(repo: Path, body, *, name: str = "probe") -> dict:
    watch = RepoWriteWatch(repo_root=repo)
    watch.start()
    watch.note_start(name)
    body()
    watch.note_end(name)
    return watch.stop()


def case_1_lingering_change_is_caught() -> None:
    with tempfile.TemporaryDirectory(prefix="repo-write-1-") as td:
        repo = _fixture(Path(td))
        result = _watch(repo, lambda: (repo / "tracked.md").write_text("changed\n", encoding="utf-8"))
    lingering = result.get("lingering") or []
    _ok("case 1 (남는 변경을 잡는다)", f"lingering={lingering}") if lingering else _fail(
        "case 1 (남는 변경을 잡는다)", f"끝까지 남은 변경을 못 봤다: {result}")


def case_2_transient_touch_is_caught_with_attribution() -> None:
    def touch_and_restore() -> None:
        target = repo / "tracked.md"
        original = target.read_text(encoding="utf-8")
        target.write_text("transient\n", encoding="utf-8")
        time.sleep(1.6)          # 폴링(0.5s)이 반드시 한 번은 본다
        target.write_text(original, encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="repo-write-2-") as td:
        repo = _fixture(Path(td))
        result = _watch(repo, touch_and_restore, name="check_probe")
    transient = result.get("transient") or []
    if not transient:
        _fail("case 2 (touch-and-restore + 귀속)",
              "중간에만 나타난 변경을 못 봤다 — 폴링이 죽었거나 간격이 너무 길다")
        return
    flight = transient[0].get("in_flight") or []
    if "check_probe" not in flight:
        _fail("case 2 (touch-and-restore + 귀속)",
              f"그때 돌던 검사를 못 달았다: {flight} — 귀속이 사라지면 발견이 쓸모없다")
        return
    if result.get("lingering"):
        _fail("case 2 (touch-and-restore + 귀속)",
              f"되돌렸는데 lingering 으로 셌다: {result['lingering']}")
        return
    _ok("case 2 (touch-and-restore + 귀속)", f"in_flight={flight}")


def case_3_clean_run_is_silent() -> None:
    """위양성이 없다 — 아무것도 안 건드리면 둘 다 비어 있어야 한다."""
    with tempfile.TemporaryDirectory(prefix="repo-write-3-") as td:
        repo = _fixture(Path(td))
        result = _watch(repo, lambda: time.sleep(1.2))
    noise = (result.get("lingering") or []) + (result.get("transient") or [])
    _ok("case 3 (건드리지 않으면 조용하다)") if not noise else _fail(
        "case 3 (건드리지 않으면 조용하다)", f"위양성: {noise}")


def case_4_unmeasurable_is_not_a_pass() -> None:
    """git 을 못 읽으면 **미측정**이다 — 통과로 접으면 이 축이 사라진다."""
    with tempfile.TemporaryDirectory(prefix="repo-write-4-") as td:
        not_a_repo = Path(td) / "plain"
        not_a_repo.mkdir()
        watch = RepoWriteWatch(repo_root=not_a_repo)
        watch.start()
        result = watch.stop()
    if result.get("measured"):
        _fail("case 4 (못 재면 미측정)", "git 저장소가 아닌데 measured=True 로 보고했다")
        return
    _ok("case 4 (못 재면 미측정)", str(result.get("reason", ""))[:60])


def case_5_known_transient_is_separated_from_unknown() -> None:
    """원장에 있는 접촉은 `known_transient` 로, 나머지는 `transient` 로 간다.

    미지의 접촉은 러너가 **red** 로 올린다 — 되돌려 놓으면 `git status` 가 오히려
    깨끗해 보여 더 위험하기 때문이다(미커밋 작업이 사라진 사고가 그 모양이었다).
    구조적으로 불가피한 것만 원장에 이유와 함께 둔다.

    타이밍에 기대지 않는다 — 분류 함수를 직접 부른다. 폴링이 그 순간을 봤는지는
    이 case 가 재는 것이 아니다 (그쪽은 case 2 가 잰다).
    """
    from _repo_write_watch import KNOWN_TRANSIENT_PATHS, _known_reason

    if not KNOWN_TRANSIENT_PATHS:
        _fail("case 5 (원장 분류)", "원장이 비었다 — 분류를 실증할 표본이 없다")
        return
    listed = next(iter(KNOWN_TRANSIENT_PATHS))
    if _known_reason(f"?? {listed}") is None:
        _fail("case 5 (원장 분류)", f"원장에 있는 경로를 못 알아봤다: {listed}")
        return
    if _known_reason("?? workflow-source/tests/check_not_in_ledger.py") is not None:
        _fail("case 5 (원장 분류)", "원장에 없는 경로를 알려진 것으로 쟀다 — 면제가 샌다")
        return
    _ok("case 5 (원장 분류)", f"원장 {len(KNOWN_TRANSIENT_PATHS)}건, 그 밖은 미지로 남는다")


for fn in (case_1_lingering_change_is_caught,
           case_2_transient_touch_is_caught_with_attribution,
           case_3_clean_run_is_silent,
           case_4_unmeasurable_is_not_a_pass,
           case_5_known_transient_is_separated_from_unknown):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        _fail(fn.__name__, f"예외 {type(exc).__name__}: {exc}")

print()
print(f"=== Result: {len(_passes)}/{len(_passes) + len(_failures)} PASS ===")
for line in _failures:
    print(f"  ✗ {line}")
sys.exit(1 if _failures else 0)
