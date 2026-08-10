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

검증 케이스 (10):
    1. release subparser 의 `--apply` default 는 False (AST)
    2. 무인자 `release` 는 dry-run 으로 진입한다 (subprocess)
    3. `--dry-run --apply` 동시 지정 시 dry-run 이 이긴다 (subprocess)
    4. doctor 호출 argv 에 `REPO_ROOT.parent` + `--config-path` 가 있다 (AST)
    5. baselines 가 저장소 루트 기준으로 test 파일을 실제로 본다 (≥ 100 files)
    6. cmd_validate doctor 게이트가 통과한다 (functional)
    7. cmd_validate state 게이트가 현 스키마(`generated_at`)로 통과한다
    8. generated_at / last_freeze 둘 다 없는 state 는 fail 한다 (결함 되주입)
    9. legacy 스키마 (`memory.last_freeze` 만) 는 여전히 통과한다 (하위호환)
    10. pyproject 의 testing partial_rules 선언이 살아 있다 (TST-WF-01 제외,
        02~06 hard 유지) — 선언된 예외가 조용히 사라지면 여기서 잡는다

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


def _release_subparser_defaults() -> dict[str, object]:
    """main() 안에서 `sub.add_parser("release")` 로 만든 parser 변수의
    add_argument 호출들에서 dest → default 를 뽑는다 (AST)."""
    tree = ast.parse(PIPELINE_PY.read_text(encoding="utf-8"))
    release_vars: set[str] = set()
    defaults: dict[str, object] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            if (isinstance(call.func, ast.Attribute) and call.func.attr == "add_parser"
                    and call.args and isinstance(call.args[0], ast.Constant)
                    and call.args[0].value == "release"
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

    def check(label: str, cond: bool, detail: str = "") -> None:
        if cond:
            print(f"PASS: {label}")
        else:
            print(f"FAIL: {label} — {detail}")
            failures.append(label)

    from tools import release_pipeline as rp  # noqa: E402

    # 1) --apply default False
    defaults = _release_subparser_defaults()
    check(
        "1) release subparser --apply default 는 False",
        defaults.get("--apply") is False,
        f"defaults={defaults}",
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

    # 7) state 게이트 — 현 스키마 generated_at 로 통과
    state_res = rp.cmd_validate(_validate_ns(skip_state=False))["state"]
    check(
        "7) state 게이트가 generated_at 로 통과",
        state_res.get("ok") is True and bool(state_res.get("generated_at")),
        f"state={state_res}",
    )

    # 8)~9) state 판정 되주입 — 경로만 tmp 로 바꿔 fail/legacy 를 확인
    orig_path_fn = rp.state_path_for_workspace
    try:
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "state.json"
            rp.state_path_for_workspace = lambda _root: fake  # type: ignore[assignment]

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
    finally:
        rp.state_path_for_workspace = orig_path_fn  # type: ignore[assignment]

    # 10) pyproject 의 testing partial 선언 고정
    from workflow_kit.common.metadata import load_config  # noqa: E402
    cfg = load_config(SOURCE_ROOT)
    testing_partial = set(cfg.partial_rules.get("testing", []))
    check(
        "10) testing partial_rules = TST-WF-02~06 (01 은 선언된 예외)",
        testing_partial == {"TST-WF-02", "TST-WF-03", "TST-WF-04", "TST-WF-05", "TST-WF-06"},
        f"partial={sorted(testing_partial)}",
    )

    total = 10
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
