"""release pre_check 게이트 사용성 회귀 (TASK-2026-08-10-main-001)

v1.1.0~v1.1.3 네 릴리스가 전부 수동 발행됐다 — `cmd_release` pre_check 의
doctor / state 가 만성 실패였고 개별 skip 도 없었기 때문이다. 뿌리는 셋:

1. doctor 호출이 `--project-root REPO_ROOT`(= workflow-source/) 를 넘겼는데
   baselines 는 project_root 아래에서 `workflow-source/` 를 다시 조립한다 →
   tests 탐색이 `workflow-source/workflow-source/` 로 어긋나 **0 files 를 재고**
   non_compliant 를 냈다 (아무것도 안 잰 검사가 실패를 보고).
2. state freshness 가 `memory.last_freeze` 를 읽었는데 그 필드의 writer 는
   v0.7.x raw-mirror 전용 도구뿐 — 현재 정본 writer (generate_workflow_state)
   는 그 섹션을 안 쓴다. reader 만 legacy 에 남은 만성 fail.
3. 무인자 `release` 의 기본이 APPLY 였다 (--apply default True 가 main() 의
   "둘 다 없으면 dry-run" 정규화를 무력화).

검증 케이스 (14 — v1.1.5 에서 1b·3b dist 기본값, v1.1.7 에서 7b·11 추가):
    1. release subparser 의 `--apply` default 는 False (AST)
    2. 무인자 `release` 는 dry-run 으로 진입한다 (subprocess)
    3. `--dry-run --apply` 동시 지정 시 dry-run 이 이긴다 (subprocess)
    4. doctor 호출 argv 에 `REPO_ROOT.parent` + `--config-path` 가 있다 (AST)
    5. baselines 가 저장소 루트 기준으로 test 파일을 실제로 본다 (≥ 100 files)
    6. cmd_validate doctor 게이트가 통과한다 (functional)
    7. cmd_validate state 게이트가 현 스키마(`generated_at`)로 통과한다 (되주입)
    7b. 살아있는 저장소의 state 도 통과한다 — 부재하는 브랜치 컨텍스트에서는 SKIP
    8. generated_at / last_freeze 둘 다 없는 state 는 fail 한다 (결함 되주입)
    9. legacy 스키마 (`memory.last_freeze` 만) 는 여전히 통과한다 (하위호환)
    10. pyproject 의 testing partial_rules 선언이 살아 있다 (TST-WF-01 제외,
        02~06 hard 유지) — 선언된 예외가 조용히 사라지면 여기서 잡는다
    11. state.json 부재는 통과 + `absent`/`state_path` 를 보고한다 (되주입)

v1.1.7 — case 7 이 *살아있는 저장소* 의 state.json 을 읽던 것이 CI smoke 의
`slash` job (`CODEX_WORKFLOW_BRANCH` 로 브랜치를 강제) 을 15연속 red 로 만들었다.
그 브랜치엔 state.json 이 없고, 게이트는 부재를 정당한 통과로 설계했는데 검사만
결함으로 봤다. 판정은 되주입으로 결정적이어야 하고(7·8·9·11), 환경 의존은 분리해
명시적으로 skip 을 보고해야 한다(7b). 같은 유형을 08-10 에만 세 번 고쳤다
(doctor exit-on-fail, dashboard timeline 2건, 그리고 여기).

Stdlib only.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

PIPELINE_PY = SOURCE_ROOT / "tools" / "release_pipeline.py"

# 전체 case 수. 7b 는 브랜치 컨텍스트에 state.json 이 없으면 skip 되므로, 기대치는
# `TOTAL_CASES - (7b skip 이면 1)` 로 *계산* 한다 — 하한이 아니라 정확값이어야
# case 가 조용히 사라지는 것을 잡는다 (v1.1.6 까지 하드코딩 total 이 하던 역할).
TOTAL_CASES = 14


def _subparser_defaults(command: str) -> dict[str, object]:
    """main() 안에서 `sub.add_parser(command)` 로 만든 parser 변수의
    add_argument 호출들에서 flag → default 를 뽑는다 (AST)."""
    tree = ast.parse(PIPELINE_PY.read_text(encoding="utf-8"))
    release_vars: set[str] = set()
    defaults: dict[str, object] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            if (isinstance(call.func, ast.Attribute) and call.func.attr == "add_parser"
                    and call.args and isinstance(call.args[0], ast.Constant)
                    and call.args[0].value == command
                    and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)):
                release_vars.add(node.targets[0].id)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in release_vars):
            continue
        flag = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else ""
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        default_node = kw.get("default")
        if isinstance(flag, str) and isinstance(default_node, ast.Constant):
            defaults[flag] = default_node.value
    return defaults


def _doctor_subprocess_argv_exprs() -> list[str]:
    """cmd_validate 안의 doctor subprocess.run 첫 인자(list) 원소를 소스 문자열로."""
    tree = ast.parse(PIPELINE_PY.read_text(encoding="utf-8"))
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef) and fn.name == "cmd_validate":
            for node in ast.walk(fn):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "run" and node.args
                        and isinstance(node.args[0], ast.List)):
                    elems = [ast.unparse(e) for e in node.args[0].elts]
                    if any("workflow_kit.cli.doctor" in e for e in elems):
                        return elems
    return []


def _validate_ns(**overrides: object) -> SimpleNamespace:
    base = {"skip_packaging": True, "skip_doctor": True, "skip_state": True,
            "skip_git": True, "skip_mypy": True}
    return SimpleNamespace(**{**base, **overrides})


def _run_release(*extra: str) -> dict:
    argv = [sys.executable, str(PIPELINE_PY), "release", "--version", "9.9.9",
            "--skip-validate", "--skip-cross-verify", "--skip-self-recover",
            "--skip-bidir-link", "--skip-doc-headers-update",
            "--skip-maturity-matrix-sync", "--skip-changelog-gen",
            "--skip-smoke-count-check", "--json", *extra]
    proc = subprocess.run(
        argv, capture_output=True, text=True, timeout=120,
        env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
    )
    return json.loads(proc.stdout)


def main() -> int:
    failures: list[str] = []
    ran = [0]

    def check(label: str, cond: bool, detail: str = "") -> None:
        ran[0] += 1
        if cond:
            print(f"PASS: {label}")
        else:
            print(f"FAIL: {label} — {detail}")
            failures.append(label)

    from tools import release_pipeline as rp  # noqa: E402

    # 1) --apply default False — release 와 dist 둘 다 (destructive/부작용 있는
    # subcommand 의 무인자 실행은 dry-run 이어야 한다. release 는 v1.1.4, dist 는
    # v1.1.5 에서 반전 — 같은 결함이 두 subparser 에 복제돼 있었다).
    rel_defaults = _subparser_defaults("release")
    check(
        "1) release subparser --apply default 는 False",
        rel_defaults.get("--apply") is False,
        f"defaults={rel_defaults}",
    )
    dist_defaults = _subparser_defaults("dist")
    check(
        "1b) dist subparser --apply default 는 False",
        dist_defaults.get("--apply") is False,
        f"defaults={dist_defaults}",
    )

    # 2) 무인자 release → dry-run
    bare = _run_release()
    check(
        "2) 무인자 release 는 dry-run",
        bare.get("mode") == "dry-run",
        f"mode={bare.get('mode')!r}",
    )

    # 3) --dry-run --apply → dry-run 이 이긴다
    both = _run_release("--dry-run", "--apply")
    check(
        "3) --dry-run --apply 는 dry-run (안전측)",
        both.get("mode") == "dry-run",
        f"mode={both.get('mode')!r}",
    )

    # 3b) 무인자 dist → dry-run (빌드를 수행하지 않는다)
    dist_proc = subprocess.run(
        [sys.executable, str(PIPELINE_PY), "dist", "--json"],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
    )
    dist_out = json.loads(dist_proc.stdout)
    check(
        "3b) 무인자 dist 는 dry-run",
        dist_out.get("mode") == "dry-run",
        f"mode={dist_out.get('mode')!r}",
    )

    # 4) doctor 호출 argv — 저장소 루트 + --config-path
    argv_exprs = _doctor_subprocess_argv_exprs()
    check(
        "4) doctor argv 에 REPO_ROOT.parent + --config-path",
        any("REPO_ROOT.parent" in e for e in argv_exprs)
        and any("--config-path" in e for e in argv_exprs),
        f"argv={argv_exprs}",
    )

    # 5) baselines 가 저장소 루트에서 test 파일을 실제로 본다
    from workflow_kit.common.contracts.baselines import evaluate_compliance  # noqa: E402
    testing = evaluate_compliance(REPO_ROOT, "testing")
    tst01 = next(r for r in testing.results if r.rule_id == "TST-WF-01")
    m = re.search(r"across (\d+) files", tst01.notes)
    seen_files = int(m.group(1)) if m else 0
    check(
        "5) TST-WF-01 이 저장소 루트 기준 ≥ 100 files 를 잰다",
        seen_files >= 100,
        f"notes={tst01.notes!r}",
    )

    # 6) doctor 게이트 통과 (functional)
    doctor_res = rp.cmd_validate(_validate_ns(skip_doctor=False))["doctor"]
    check(
        "6) cmd_validate doctor 게이트 통과",
        doctor_res.get("ok") is True and doctor_res.get("non_compliant") == [],
        f"doctor={doctor_res}",
    )

    # 7)~9), 11) state 판정 되주입 — 경로만 tmp 로 바꿔 4 스키마를 결정적으로 확인.
    # v1.1.7: case 7 이 여기로 들어왔다. 이전엔 *살아있는 저장소* 의 state.json 을
    # 읽어 `generated_at` 을 요구했는데, 그 경로는 브랜치 컨텍스트에 따라 달라진다
    # — CI smoke 의 `slash` job (`CODEX_WORKFLOW_BRANCH=feature/ci-slash-probe`)
    # 에는 그 브랜치의 state.json 이 없어 게이트가 정당하게 absent 를 반환했고,
    # 검사만 그것을 fail 로 봤다 (15연속 red, native job 은 내내 green).
    # 판정 자체는 환경과 무관해야 한다 — 환경 의존은 아래 7b 로 분리한다.
    orig_path_fn = rp.state_path_for_workspace
    try:
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "state.json"
            rp.state_path_for_workspace = lambda _root: fake  # type: ignore[assignment]

            fake.write_text(
                json.dumps({"schema_version": "1", "generated_at": "2026-08-10"}),
                encoding="utf-8",
            )
            res7 = rp.cmd_validate(_validate_ns(skip_state=False))["state"]
            check(
                "7) state 게이트가 generated_at 로 통과 (되주입)",
                res7.get("ok") is True and res7.get("generated_at") == "2026-08-10",
                f"state={res7}",
            )

            fake.write_text(json.dumps({"schema_version": "1"}), encoding="utf-8")
            res8 = rp.cmd_validate(_validate_ns(skip_state=False))["state"]
            check(
                "8) generated_at/last_freeze 둘 다 없으면 fail (되주입)",
                res8.get("ok") is False,
                f"state={res8}",
            )

            fake.write_text(
                json.dumps({"memory": {"last_freeze": "2026-06-14-v0.7.4"}}),
                encoding="utf-8",
            )
            res9 = rp.cmd_validate(_validate_ns(skip_state=False))["state"]
            check(
                "9) legacy last_freeze 만 있어도 통과 (하위호환)",
                res9.get("ok") is True,
                f"state={res9}",
            )

            # 11) 부재 = 정당한 통과. 이 계약을 아무도 안 재고 있었기 때문에
            # case 7 이 그것을 결함으로 오인해도 드러나지 않았다. absent 응답은
            # *어느 경로를 봤는지* 도 실어야 한다 (안 그러면 진단이 불가능하다).
            fake.unlink()
            res11 = rp.cmd_validate(_validate_ns(skip_state=False))["state"]
            check(
                "11) state.json 부재는 통과 + absent/state_path 보고 (되주입)",
                res11.get("ok") is True
                and res11.get("absent") is True
                and res11.get("state_path") == str(fake),
                f"state={res11}",
            )
    finally:
        rp.state_path_for_workspace = orig_path_fn  # type: ignore[assignment]

    # 7b) 살아있는 저장소의 state — 있으면 게이트를 통과해야 한다. 브랜치 컨텍스트에
    # 따라 부재가 정상이므로(위 case 11 이 그 계약을 고정한다) 부재는 명시 SKIP 으로
    # 남긴다. 조용히 통과시키지 않는 이유는 "모름 ≠ 안전" — 안 잰 것은 안 잰 것으로
    # 보고한다.
    live = rp.cmd_validate(_validate_ns(skip_state=False))["state"]
    skipped_7b = bool(live.get("absent"))
    if skipped_7b:
        print(
            "SKIP: 7b) 살아있는 저장소 state — 이 브랜치 컨텍스트엔 state.json 이 없다 "
            f"(path={live.get('state_path')}). 판정 계약은 case 7~9·11 이 고정한다."
        )
    else:
        check(
            "7b) 살아있는 저장소의 state 가 게이트를 통과",
            live.get("ok") is True and bool(live.get("generated_at")),
            f"state={live}",
        )

    # 10) testing partial 예외가 *제거된 상태* 로 유지되는지 고정.
    # v1.1.4 에서 TST-WF-01 측정 결함 탓에 잠시 선언 예외였고, v1.1.5 에서 측정을
    # 재설계하며 제거했다 (TST-WF-01 다시 hard). 누군가 조용히 되살리면 여기서 잡힌다
    # — 예외는 측정을 고치는 대신 쓰는 우회이므로 재도입은 명시적 결정이어야 한다.
    from workflow_kit.common.metadata import load_config  # noqa: E402
    cfg = load_config(SOURCE_ROOT)
    check(
        "10) testing 은 partial_rules 에 없다 (TST-WF-01 hard 복귀, v1.1.5)",
        "testing" not in cfg.partial_rules,
        f"partial_rules={cfg.partial_rules}",
    )

    # v1.1.7: 총계는 하드코딩 대신 *계산* 한다 — 7b 는 브랜치 컨텍스트에 따라 skip
    # 되므로 실행 수가 가변이지만, skip 여부를 알고 있으니 기대치는 정확하다.
    expected = TOTAL_CASES - (1 if skipped_7b else 0)
    total = ran[0]
    if total != expected:
        print(f"FAIL: 실행된 case {total} 개 ≠ 기대 {expected} 개 — case 가 사라졌거나 늘었다")
        return 1
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
