"""release wrapper 의 args 계약 + git 경로 기준 (TASK-2026-08-09-main-009)

v1.1.2 release 에서 릴리스 도구 결함 2건이 **발행 도중에** 드러났다. 둘 다
`check_release_pipeline_lib` 9 case 가 green 인 상태에서 나왔다 —
**릴리스 도구는 릴리스 때만 실행되므로 평소 검사에 안 걸린다.**

1. `release-verify` → `AttributeError: 'types.SimpleNamespace' object has no
   attribute 'dry_run'`. `_make_args()` 가 `dry_run` 을 안 채웠는데
   `release_pipeline.cmd_verify` 는 `args.dry_run` 을 읽는다.
2. `release-bump` post-step → `git add` 가
   `workflow-source/workflow-source/pyproject.toml` 을 찾다 실패.
   `REPO_ROOT` 는 이름과 달리 `workflow-source/` 인데, `git status --porcelain` 은
   *저장소 루트* 기준 경로를 준다.

검증 케이스 (8):
    1. `_make_args()` 가 **wrapper 경유** `cmd_*` 의 flag args 를 덮는다 (AST 대조).
       argparse 로만 불리는 `cmd_gen_schema` 는 대상 밖 — 포함하면 없는 결함을 만든다.
    2. `dry_run` 기본값은 **안전측(True)** 이다
    3. `cmd_verify` wrapper 는 `dry_run=False` 를 명시한다 (조회가 목적)
    4. `_git_toplevel()` 이 실제 저장소 루트를 반환한다 (`REPO_ROOT` 와 다르다)
    5. `_git_dirty_paths()` 의 경로가 **저장소 루트 기준** 이다 (삭제 entry 는
       존재 검사에서 제외 — 삭제 경로는 정의상 존재하지 않는다)
    6. add 대상 선별 (`needs_add_only=True`) 을 `_git_toplevel()` cwd 에서
       `git add --dry-run` 하면 성공하고, `REPO_ROOT`(=`workflow-source/`) 에서는
       실패한다 (= v1.1.2 버그의 직접 회귀)
    7. read-only wrapper 실호출에 AttributeError 가 없다
    8. release note 의 누적 smoke 수치 검증이 동작한다 (표기 누락 / note 부재 검출)
    9. 그 검증이 note 를 **쓰지 않는다** — "전량 PASS" 는 사람의 주장이다
    10. (되주입, tmp repo) staged 삭제가 있으면 full dirty list 의 `git add` 는
        pathspec fatal 이고 (TASK-2026-08-11-main-002 의 함정 실증),
        `needs_add_only=True` 선별은 그걸 제외해 성공한다. unstaged 삭제는
        선별에 **포함** 되어야 한다 (add 로 삭제를 stage 하는 정당 경로).

Stdlib only.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/releases/*",
    "workflow-source/workflow_kit/*",
)

import ast
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

PIPELINE_PY = SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline.py"
LIB_PY = SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline_lib.py"


def _cmd_arg_attrs() -> dict[str, set[str]]:
    """release_pipeline 의 각 `cmd_*` 가 읽는 `args.X` 이름."""
    tree = ast.parse(PIPELINE_PY.read_text(encoding="utf-8"))
    out: dict[str, set[str]] = {}
    for fn in tree.body:
        if not isinstance(fn, ast.FunctionDef) or not fn.name.startswith("cmd_"):
            continue
        attrs = {
            n.attr
            for n in ast.walk(fn)
            if isinstance(n, ast.Attribute)
            and isinstance(n.value, ast.Name)
            and n.value.id == "args"
        }
        if attrs:
            out[fn.name] = attrs
    return out


def main() -> int:
    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        if cond:
            print(f"PASS: {label}")
        else:
            print(f"FAIL: {label} — {detail}")
            failures.append(label)

    from workflow_kit.tools import release_pipeline as rp  # noqa: E402
    from workflow_kit.tools import release_pipeline_lib as lib  # noqa: E402

    lib_src_for_scan = LIB_PY.read_text(encoding="utf-8")

    # 1) _make_args 가 **wrapper 를 통해 불리는** cmd_* 의 flag 성 args 를 덮는가
    #
    #    `_make_args` 를 거치지 않는 cmd_* (argparse 로만 불리는 것, 예:
    #    `cmd_gen_schema`) 는 대상이 아니다 — 그걸 포함하면 검사가 없는 결함을
    #    보고한다. `release_pipeline_lib` 가 `mod.cmd_X(...)` 로 부르는 것만 본다.
    #    caller 가 kwargs 로 넘기는 값(tag / to / version)은 defaults 에 없어도
    #    되므로 flag 성만 대조하고, 개별 wrapper 는 case 7 이 실호출로 확인한다.
    defaults = vars(lib._make_args())
    per_cmd = _cmd_arg_attrs()
    wrapped = {
        name
        for name in per_cmd
        if f"mod.{name}(" in lib_src_for_scan
    }
    flagish = {
        a
        for name in wrapped
        for a in per_cmd[name]
        if a.startswith("skip_") or a in {"dry_run", "strict_cross_verify"}
    }
    missing = sorted(flagish - set(defaults))
    check(
        "1) _make_args defaults 가 wrapper 경유 flag args 를 전부 덮는다",
        not missing,
        f"missing={missing} wrapped={sorted(wrapped)}",
    )

    # 2) dry_run 기본은 안전측
    check(
        "2) dry_run 기본값 = True (안전측)",
        defaults.get("dry_run") is True,
        f"dry_run={defaults.get('dry_run')!r}",
    )

    # 3) cmd_verify wrapper 가 dry_run=False 명시
    verify_src = lib_src_for_scan[lib_src_for_scan.index("def cmd_verify("):]
    verify_src = verify_src[: verify_src.index("\ndef ", 1)]
    check(
        "3) cmd_verify wrapper 가 dry_run=False 를 명시",
        "dry_run=False" in verify_src,
        "read-only 라도 실제 조회해야 검증이다",
    )

    # 4) _git_toplevel 이 저장소 루트
    toplevel = rp._git_toplevel()
    check(
        "4) _git_toplevel() = 저장소 루트 (REPO_ROOT 와 다르다)",
        toplevel == REPO_ROOT and rp.REPO_ROOT == SOURCE_ROOT,
        f"toplevel={toplevel} REPO_ROOT={rp.REPO_ROOT}",
    )

    # 5) dirty paths 가 저장소 루트 기준
    #    (변경이 없으면 이 case 는 자동 통과 — 비교할 대상이 없다)
    #    삭제 entry (index 든 worktree 든 D) 는 존재 검사에서 제외 — 삭제 경로는
    #    정의상 존재하지 않는 것이 정상이다 (TASK-2026-08-11-main-002).
    dirty = rp._git_dirty_paths()
    proc_st = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, timeout=15, cwd=str(toplevel),
    )
    deleted = set()
    for line in proc_st.stdout.splitlines():
        if len(line) >= 4 and "D" in line[:2]:
            p = line[3:]
            if " -> " in p:
                p = p.split(" -> ", 1)[1]
            deleted.add(p.strip().strip('"'))
    bad = [p for p in dirty if p not in deleted and not (REPO_ROOT / p).exists()]
    check(
        "5) _git_dirty_paths() 경로가 저장소 루트 기준 (삭제 제외)",
        not bad,
        f"루트 기준으로 존재하지 않는 path={bad[:3]}",
    )

    # 6) v1.1.2 에서 터진 조합의 직접 회귀 — add 대상 선별을 toplevel cwd 에서 add.
    #    full list 가 아니라 needs_add_only 선별을 쓴다 — production (amend Guard 2)
    #    이 실제로 add 하는 집합이 이것이고, staged 삭제가 섞인 full list 는
    #    pathspec fatal 이 정상이다 (그 함정은 case 10 이 tmp repo 로 고정한다).
    add_targets = rp._git_dirty_paths(needs_add_only=True)
    if add_targets:
        proc = subprocess.run(
            ["git", "add", "--dry-run", "--", *add_targets],
            capture_output=True, text=True, timeout=30, cwd=str(toplevel),
        )
        check(
            "6) add 대상 선별을 toplevel cwd 에서 git add 할 수 있다",
            proc.returncode == 0,
            f"rc={proc.returncode} stderr={proc.stderr[:160]}",
        )
        # 반대로 REPO_ROOT(=workflow-source) 에서 하면 실패해야 정상 — 그게 v1.1.2 의 버그다.
        proc_bad = subprocess.run(
            ["git", "add", "--dry-run", "--", *add_targets],
            capture_output=True, text=True, timeout=30, cwd=str(rp.REPO_ROOT),
        )
        check(
            "6b) 같은 경로를 workflow-source/ 에서 add 하면 실패한다 (버그 재현)",
            proc_bad.returncode != 0,
            "이게 성공하면 두 기준이 우연히 같아진 것 — case 6 의 의미가 사라진다",
        )
    else:
        print("PASS: 6) (add 대상 없음 — 생략)")
        print("PASS: 6b) (add 대상 없음 — 생략)")

    # 7) read-only wrapper 실호출 — AttributeError 류를 잡는다
    errors: list[str] = []
    for label, call in (
        ("cmd_version_bump(dry-run)", lambda: lib.cmd_version_bump(to="9.9.9", apply=False)),
        ("cmd_note_draft(dry-run)", lambda: lib.cmd_note_draft(to="9.9.9", from_tag="v1.1.1-beta")),
        ("cmd_changelog_gen(dry-run)", lambda: lib.cmd_changelog_gen()),
        ("cmd_dist(dry-run)", lambda: lib.cmd_dist(apply=False)),
    ):
        try:
            call()
        except AttributeError as e:
            errors.append(f"{label}: AttributeError: {e}")
        except Exception:  # noqa: BLE001 — 다른 실패는 이 검사의 관심사가 아니다
            pass
    check("7) read-only wrapper 실호출에 AttributeError 없음", not errors, f"{errors}")


    # 9) release note 누적 smoke 수치 검증 (v1.1.3+)
    #
    #    v1.1.0 / v1.1.1 이 이 줄을 통째로 빠뜨렸고, 그동안 dashboard 는 옛 note 를
    #    읽어 check_smoke_trend_cross 가 계속 red 였다. 릴리스 절차에 그걸 잡는
    #    자리가 없었다 — 이 case 가 그 자리가 생겼는지 본다.
    verify = rp.verify_release_note_smoke_count
    actual_files = rp._count_smoke_files()

    cur = verify(rp.read_version())
    ok_current = cur["ok"] and cur["found"] == (actual_files, actual_files)

    # 표기가 없는 note 는 잡아야 한다 (v1.1.0 이 실제 그 상태다)
    missing = verify("1.1.0")
    caught_missing = (not missing["ok"]) and "누적 smoke" in (missing["error"] or "")

    # 존재하지 않는 version → note 부재로 잡는다
    absent = verify("99.99.99")
    caught_absent = (not absent["ok"]) and "부재" in (absent["error"] or "")

    check(
        "9) release note 누적 수치 검증 (현재 ok / 표기누락·note부재 검출)",
        ok_current and caught_missing and caught_absent,
        f"cur={cur} missing_ok={caught_missing} absent_ok={caught_absent}",
    )

    # 9b) 도구가 그 줄을 **대신 적지 않는다** — "전량 PASS" 는 사람의 주장이다.
    src = (SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline.py").read_text(encoding="utf-8")
    fn_src = src[src.index("def verify_release_note_smoke_count"):]
    fn_src = fn_src[: fn_src.index("\ndef ", 1)]
    writes = any(w in fn_src for w in ("write_text(", "atomic_write", ".replace("))
    check(
        "9b) 검증만 하고 note 를 쓰지 않는다",
        not writes,
        "도구가 누적 수치를 대신 적으면 거짓 주장을 만든다",
    )

    # 10) 되주입 (tmp repo): staged 삭제가 있으면 full dirty list 의 add 는
    #     pathspec fatal — TASK-2026-08-11-main-002 의 함정을 결정적으로 고정.
    #     needs_add_only 선별은 staged 삭제 (`D `) 를 제외하고, unstaged 삭제
    #     (` D`) 는 **포함** 한다 (add 로 삭제를 stage 하는 정당 경로).
    with tempfile.TemporaryDirectory(prefix="wrapper_args_case10_") as td:
        tr = Path(td).resolve()

        def _g(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                ["git", *args],
                capture_output=True, text=True, timeout=15, cwd=str(tr),
            )

        _g("init", "-q")
        _g("config", "user.email", "case10@test")
        _g("config", "user.name", "case10")
        (tr / "a.txt").write_text("a\n", encoding="utf-8")
        (tr / "b.txt").write_text("b\n", encoding="utf-8")
        (tr / "d.txt").write_text("d\n", encoding="utf-8")
        _g("add", "-A")
        _g("commit", "-qm", "init")
        _g("rm", "-q", "a.txt")                              # staged 삭제 (D )
        (tr / "b.txt").write_text("b2\n", encoding="utf-8")  # unstaged 수정 ( M)
        (tr / "c.txt").write_text("c\n", encoding="utf-8")   # untracked (??)
        (tr / "d.txt").unlink()                              # unstaged 삭제 ( D)

        orig_toplevel = rp._git_toplevel
        rp._git_toplevel = lambda **kw: tr  # type: ignore[assignment]
        try:
            full = rp._git_dirty_paths()
            sel = rp._git_dirty_paths(needs_add_only=True)
        finally:
            rp._git_toplevel = orig_toplevel

        proc_trap = _g("add", "--dry-run", "--", *full)
        proc_fix = _g("add", "--dry-run", "--", *sel)
        check(
            "10) staged 삭제: full list add 는 fatal, needs_add_only 선별은 성공",
            set(full) == {"a.txt", "b.txt", "c.txt", "d.txt"}
            and set(sel) == {"b.txt", "c.txt", "d.txt"}
            and proc_trap.returncode != 0
            and proc_fix.returncode == 0,
            f"full={full} sel={sel} trap_rc={proc_trap.returncode} fix_rc={proc_fix.returncode}",
        )

    total = 11
    print()
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
