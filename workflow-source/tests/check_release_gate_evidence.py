#!/usr/bin/env python3
"""발행 게이트가 **로컬 게이트 통과 기록**을 보고, 기본이 차단인지 고정한다 (9 cases).

## 계보

- v1.9.0 (TASK-2026-09-01-main-005): v1.8.0 이 `smoke` 10 커밋 연속 red 위에서 발행된
  뒤, 발행 게이트가 필수 CI 워크플로 전부를 HEAD sha 로 조회해 **기본 차단**하게 됐다
  (옛 이름 `check_release_ci_gate`).
- 2026-09-23 (TASK-2026-09-23-main-022): 소유자 결정으로 GitHub Actions 테스트 workflow
  를 폐지했다. 근거를 CI 에서 `run_all_checks.py --branch-context=all` 이 남기는
  **게이트 통과 기록**(`workflow_kit.common.gate_evidence`)으로 옮겼다.

지켜야 할 것은 그대로다 — **모름은 통과가 아니다.** 기록이 없거나, 커밋되지 않은
변경 위에서 쟀거나, 컨텍스트 하나를 빼먹었으면 막는다.

9 cases:
  1) 기록이 없으면 차단
  2) 전 컨텍스트가 담긴 기록 → 통과
  3) 컨텍스트가 빠진 기록 → 차단
  4) HEAD sha 를 못 읽으면(git 저장소 아님) 차단
  5) record ↔ lookup 왕복 + sha 가 어긋난 기록은 무효
  6) untracked 파일도 '깨끗하지 않음' — git 이 아니면 None(모름)
  7) runner 는 조건(exit 0 · 시작 시 깨끗 · HEAD 불변)을 **전부** 만족할 때만 기록
  8) runner 는 필터 없는 `--branch-context=all` 에서만 기록 대상으로 삼는다
  9) cmd_release 가 apply 경로에서 게이트로 **차단**한다 (advisory 로 되돌아가지 않았다)
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/run_all_checks.py",
)

import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
TESTS_DIR = SOURCE_ROOT / "tests"
for _p in (SOURCE_ROOT, TESTS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from workflow_kit.common import gate_evidence  # noqa: E402
from workflow_kit.common.branch_matrix import labels  # noqa: E402
from workflow_kit.tools.release_pipeline import verify_gate_evidence  # noqa: E402

PIPELINE_SRC = SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline.py"
RUNNER_SRC = TESTS_DIR / "run_all_checks.py"

FAILURES: list[str] = []
GIT_ENV = {"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}


def _record(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  PASS  {name}")
        return
    FAILURES.append(name)
    print(f"  FAIL  {name} — {detail}")


def _git_repo(td: str) -> Path:
    """커밋 1개짜리 깨끗한 저장소."""
    root = Path(td) / "repo"
    root.mkdir()
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    for args in (("init", "-q", "."), ("add", "-A"),
                 ("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")):
        subprocess.run(["git", *args], cwd=str(root), check=True, capture_output=True,
                       timeout=60, env={**GIT_ENV, "HOME": td})
    return root


def _full_evidence(sha: str) -> dict:
    return {"schema": gate_evidence.EVIDENCE_SCHEMA, "sha": sha, "contexts": list(labels())}


def case_1_no_evidence_blocks() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = _git_repo(td)
        r = verify_gate_evidence(repo_root=root)
    _record("case_1_no_evidence_blocks", r["ok"] is False and r["evidence"] is None,
            f"기록 없는 커밋이 통과했다: {r}")


def case_2_full_evidence_passes() -> None:
    r = verify_gate_evidence(head_sha="deadbeef", evidence=_full_evidence("deadbeef"))
    _record("case_2_full_evidence_passes", r["ok"] is True, f"{r}")


def case_3_missing_context_blocks() -> None:
    ev = _full_evidence("deadbeef")
    ev["contexts"] = ev["contexts"][:-1]
    r = verify_gate_evidence(head_sha="deadbeef", evidence=ev)
    _record("case_3_missing_context_blocks", r["ok"] is False,
            f"컨텍스트 {labels()[-1]!r} 없이 통과했다 — 2026-08-10 의 15연속 red 는 "
            f"한 축만 밟은 green 이었다: {r}")


def case_4_unreadable_head_blocks() -> None:
    with tempfile.TemporaryDirectory() as td:
        r = verify_gate_evidence(repo_root=Path(td))
    _record("case_4_unreadable_head_blocks", r["ok"] is False and r["head_sha"] is None, f"{r}")


def case_5_record_lookup_roundtrip() -> None:
    problems = []
    with tempfile.TemporaryDirectory() as td:
        root = _git_repo(td)
        sha = gate_evidence.head_sha(root)
        assert sha
        path = gate_evidence.record(root, sha, contexts=list(labels()), total=3)
        if path is None or not path.is_file():
            problems.append(f"기록 파일이 없다: {path}")
        elif ".git" not in path.parts:
            problems.append(f"기록이 git 디렉터리 밖에 있다(워킹 트리를 더럽힌다): {path}")
        got = gate_evidence.lookup(root, sha)
        if not got or got.get("contexts") != list(labels()):
            problems.append(f"lookup 이 기록을 못 돌려준다: {got}")
        if gate_evidence.tree_is_clean(root) is not True:
            problems.append("기록이 워킹 트리를 더럽혔다")
        # 다른 sha 의 내용을 이 sha 이름으로 두면 무효다
        if path is not None:
            path.write_text(path.read_text(encoding="utf-8").replace(sha, "0" * 40),
                            encoding="utf-8")
            if gate_evidence.lookup(root, sha) is not None:
                problems.append("sha 가 어긋난 기록을 유효로 읽었다")
    _record("case_5_record_lookup_roundtrip", not problems, "; ".join(problems))


def case_6_untracked_is_dirty() -> None:
    problems = []
    with tempfile.TemporaryDirectory() as td:
        root = _git_repo(td)
        (root / "new.py").write_text("x = 1\n", encoding="utf-8")
        if gate_evidence.tree_is_clean(root) is not False:
            problems.append("untracked 파일을 깨끗하다고 봤다")
    with tempfile.TemporaryDirectory() as td:
        if gate_evidence.tree_is_clean(Path(td)) is not None:
            problems.append("git 이 아닌데 판정했다 (모름이어야 한다)")
    _record("case_6_untracked_is_dirty", not problems, "; ".join(problems))


def case_7_runner_records_only_when_all_conditions_hold() -> None:
    import run_all_checks as runner

    passes = [(label, runner.RunSummary(total=5)) for label in labels()]
    problems = []
    with tempfile.TemporaryDirectory() as td:
        root = _git_repo(td)
        sha = gate_evidence.head_sha(root)
        assert sha
        for name, kwargs in (
            ("exit 1", dict(exit_code=1, sha=sha, clean_at_start=True)),
            ("시작 시 더러움", dict(exit_code=0, sha=sha, clean_at_start=False)),
            ("청결 모름", dict(exit_code=0, sha=sha, clean_at_start=None)),
            ("HEAD 변경", dict(exit_code=0, sha="0" * 40, clean_at_start=True)),
        ):
            runner._record_gate(root, kwargs["exit_code"], kwargs["sha"],
                                kwargs["clean_at_start"], passes, quiet=True)
            if gate_evidence.lookup(root, kwargs["sha"]) is not None:
                problems.append(f"{name} 인데 기록했다")
        runner._record_gate(root, 0, sha, True, passes, quiet=True)
        got = gate_evidence.lookup(root, sha)
        if not got or got.get("contexts") != list(labels()):
            problems.append(f"조건을 다 만족했는데 기록이 없다: {got}")
    _record("case_7_runner_records_only_when_all_conditions_hold", not problems,
            "; ".join(problems))


def case_8_runner_gate_scope() -> None:
    src = RUNNER_SRC.read_text(encoding="utf-8")
    problems = []
    for needle in ('args.branch_context == "all"', "args.filter is None", "not args.changed"):
        if needle not in src.split("gate_run = (", 1)[-1].split(")", 1)[0]:
            problems.append(f"기록 대상 조건에 `{needle}` 가 없다")
    if "_record_gate(" not in src.split("def main", 1)[-1]:
        problems.append("main 이 _record_gate 를 부르지 않는다")
    _record("case_8_runner_gate_scope", not problems, "; ".join(problems))


def case_9_release_blocks_on_gate() -> None:
    src = PIPELINE_SRC.read_text(encoding="utf-8")
    problems = []
    rel = src.split("def cmd_release(", 1)
    if len(rel) != 2:
        problems.append("cmd_release 가 없다")
    else:
        body = rel[1].split("\ndef ", 1)[0]
        if "verify_gate_evidence()" not in body:
            problems.append("cmd_release 가 verify_gate_evidence 를 부르지 않는다")
        if 'gate["ok"]' not in body or "not args.dry_run" not in body:
            problems.append("apply 경로에서 차단하지 않는다 — advisory 로 되돌아갔다")
    if "gh run list" in src.split("def verify_gate_evidence", 1)[-1].split("\ndef ", 1)[0]:
        problems.append("게이트가 아직 CI 를 조회한다")
    _record("case_9_release_blocks_on_gate", not problems, "; ".join(problems))


CASES = (
    case_1_no_evidence_blocks,
    case_2_full_evidence_passes,
    case_3_missing_context_blocks,
    case_4_unreadable_head_blocks,
    case_5_record_lookup_roundtrip,
    case_6_untracked_is_dirty,
    case_7_runner_records_only_when_all_conditions_hold,
    case_8_runner_gate_scope,
    case_9_release_blocks_on_gate,
)


def main() -> int:
    print("=== 발행 게이트 ↔ 로컬 게이트 통과 기록 ===")
    for fn in CASES:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            FAILURES.append(fn.__name__)
            print(f"  FAIL  {fn.__name__} — 예외 {type(exc).__name__}: {exc}")
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    print(f"\n{len(CASES)}/{len(CASES)} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
