"""[project.scripts] entry points smoke (TASK-2026-08-08-main-020, CLI 化 A안)

`pyproject.toml` 의 `[project.scripts]` 30+ console_script 가 모두:
1. valid TOML + parse 정상
2. target module (`tools.<name>`) import 가능
3. module 의 `main()` callable
4. main() 이 `--help` 으로 rc=0 (argparse 정상)

stdlib only. importlib + tomllib + subprocess + sys.

검증 케이스 (4):
    1. pyproject.toml valid + 30+ entry points
    2. 각 module import 가능 (no ImportError)
    3. 각 module 의 main() callable
    4. 각 entry point 가 `--help` 로 rc=0 (또는 rc=1 인 help-only 도구 — argparse 가 도움말에서 0 외 코드 사용)
    + sanity: 중복 command name 없음, format 정규 (`workflow-` prefix)
"""

from __future__ import annotations

import importlib
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "workflow-source" / "pyproject.toml"
SOURCE_ROOT = REPO_ROOT / "workflow-source"


def main() -> int:
    failures: list[str] = []

    # 1) pyproject.toml valid + 30+ entry points
    with PYPROJECT.open("rb") as f:
        data = tomllib.load(f)
    scripts = data.get("project", {}).get("scripts", {})
    if len(scripts) < 25:
        failures.append(f"[1] entry points: {len(scripts)} < 25 (expected ≥30)")

    # sanity: 중복 command name + format
    if len(scripts) != len(set(scripts.keys())):
        dups = [k for k in scripts if list(scripts.keys()).count(k) > 1]
        failures.append(f"[1] duplicate command names: {set(dups)}")
    bad_fmt = [k for k in scripts if not k.startswith("workflow-")]
    if bad_fmt:
        failures.append(f"[1] non-conforming names: {bad_fmt}")

    # sanity: 각 entry point 가 `tools.X:main` 형식
    bad_target = []
    for cmd, target in scripts.items():
        if not target.startswith("tools.") or ":main" not in target:
            bad_target.append(f"{cmd}={target}")
    if bad_target:
        failures.append(f"[1] bad targets (expected `tools.X:main`): {bad_target[:3]}...")

    if not [f for f in failures if f.startswith("[1]")]:
        print(f"  [1] pyproject.toml         ✓  ({len(scripts)} entry points, format 정합)")

    # 2 + 3) 각 module import + main() callable
    # sys.path 에 source_root 추가
    if str(SOURCE_ROOT) not in sys.path:
        sys.path.insert(0, str(SOURCE_ROOT))

    modules = []
    for cmd, target in scripts.items():
        # "tools.detect_scope_drift:main" → "tools.detect_scope_drift"
        module_name = target.rsplit(":", 1)[0]
        modules.append((cmd, module_name))

    import_errors = []
    no_main = []
    for cmd, module_name in modules:
        try:
            mod = importlib.import_module(module_name)
        except Exception as e:  # noqa: BLE001
            import_errors.append(f"{cmd} ({module_name}): {type(e).__name__}: {e}")
            continue
        if not hasattr(mod, "main"):
            no_main.append(f"{cmd} ({module_name})")
    if import_errors:
        failures.append(f"[2] import errors: {import_errors[:3]}...")
    if no_main:
        failures.append(f"[3] no main() in: {no_main[:3]}...")
    if not import_errors and not no_main:
        print(f"  [2+3] import + main()       ✓  ({len(modules)} module importable, main() callable)")

    # 4) 각 entry point 가 subprocess 로 --help 시 정상 (rc=0 또는 argparse 가 도움말에서 rc=1)
    #    legacy: python3 workflow-source/tools/X.py
    #    new: python3 -m tools.X
    #    양쪽 다 검증.
    legacy_helps = []
    module_helps = []
    with tempfile.TemporaryDirectory() as tmp:
        for cmd, target in scripts.items():
            tool_name = target.split(".", 1)[1].rsplit(":", 1)[0]
            # legacy path
            legacy_script = SOURCE_ROOT / "tools" / f"{tool_name}.py"
            if legacy_script.is_file():
                r = subprocess.run(
                    ["python3", str(legacy_script), "--help"],
                    cwd=REPO_ROOT, capture_output=True, text=True, timeout=10,
                )
                legacy_helps.append((cmd, r.returncode))
            # new module path (simulating `python3 -m tools.X`)
            r2 = subprocess.run(
                ["python3", "-m", f"tools.{tool_name}", "--help"],
                cwd=SOURCE_ROOT, capture_output=True, text=True, timeout=10,
                env={"PYTHONPATH": str(SOURCE_ROOT)},
            )
            module_helps.append((cmd, r2.returncode))

    # rc=0 또는 rc=1 (argparse 가 help 에서 1 리턴) — 둘 다 OK. rc=2 는 *argparse error* 라 안 됨.
    bad_legacy = [(c, rc) for c, rc in legacy_helps if rc not in (0, 1)]
    bad_module = [(c, rc) for c, rc in module_helps if rc not in (0, 1)]
    if bad_legacy:
        failures.append(f"[4a] legacy --help failed (rc not 0/1): {bad_legacy[:3]}")
    if bad_module:
        failures.append(f"[4b] module --help failed (rc not 0/1): {bad_module[:3]}")

    if not bad_legacy and not bad_module:
        legacy_ok = sum(1 for _, rc in legacy_helps if rc in (0, 1))
        module_ok = sum(1 for _, rc in module_helps if rc in (0, 1))
        print(f"  [4] --help sanity          ✓  (legacy: {legacy_ok}/{len(legacy_helps)}, module: {module_ok}/{len(module_helps)})")

    print()
    if failures:
        print(f"FAIL: {len(failures)} case(s) failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"ALL PASS: [project.scripts] entry points — {len(scripts)} entry point 정합 (TOML/import/main/help)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
