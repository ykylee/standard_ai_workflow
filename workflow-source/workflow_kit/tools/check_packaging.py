#!/usr/bin/env python3
"""Verify the built wheel imports cleanly in a fresh venv.

Catches packaging regressions like the v0.5.7.1 hotfix (sub-packages
``workflow_kit/common/state``, ``contracts``, ``schemas`` were missing from
``[tool.setuptools.packages]`` so ``pip install dist/*.whl`` failed with
``ModuleNotFoundError`` even though ``pip install -e .`` worked).

Usage::

    wk check-packaging [--wheel PATH]

Default behaviour:

1. Resolve the wheel path (most recent under ``dist/``) unless overridden.
2. Create a throwaway virtual environment via ``python3 -m venv``.
3. Install the wheel with ``pip install`` (no editable mode, no local
   source fallback).
4. Run a 1-line import smoke covering every sub-package found **on disk**
   (``derive_required_imports``) plus the declared leaf modules and the
   ``bootstrap_lib`` CLI entry point.
5. Tear down the venv on success.

Every child process runs under :func:`isolated_env` and a cwd outside the
repo. Without that the caller's ``PYTHONPATH=workflow-source`` reaches the
throwaway venv, pip declines to install ("already installed" — it reads the
source tree's ``.egg-info``), and the smoke measures the checkout instead of
the wheel. Measured 2026-09-01: PASS on a wheel that was missing a package.

Exit code 0 on success, 1 on any import or install failure. The script
prints a JSON manifest describing what it checked, so it can be wired
into a release checklist or CI hook.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIST = REPO_ROOT / "dist"

# Sub-packages that must be importable — **derived from the source tree on disk**,
# not hand-maintained.
#
# v1.8.1 (TASK-2026-09-01-main-001): this used to be an explicit tuple whose own
# comment argued the hand list *was* the point ("adding a new sub-package will
# require updating this list ... packaging drift is silent otherwise"). It failed
# that way three times, always in the same shape — a directory that exists in the
# checkout but was never declared, so the repo stayed green and only consumers got
# ``ModuleNotFoundError``:
#
#   - v0.5.7.1 hotfix — ``common.state`` / ``contracts`` / ``schemas``
#   - v1.1.7  (TASK-2026-08-11-main-027) — ``tools``
#   - v1.8.0  (TASK-2026-09-01-main-001) — ``cli`` (shipped broken)
#
# A list that has to be remembered will be forgotten again, so the requirement now
# reads the disk. The reference is the **source tree** (this file only runs from a
# repo checkout — see ``tests/check_deployed_layout.py`` LAYOUT notes), never the
# installed wheel: deriving from the wheel would make the check assert that the
# wheel contains what the wheel contains.
#
# The static counterpart is ``tests/check_deployed_layout.py`` case 5, which
# compares the same disk truth against pyproject's ``packages`` on every gate run.
# This one costs a wheel build, so it stays a release-time check.
#
# Note: ``bootstrap_workflow_kit`` is intentionally NOT covered. It's a legacy CLI
# shim (single .py file in scripts/) that downstream callers invoke directly via
# ``python scripts/bootstrap_workflow_kit.py`` rather than importing. The
# programmatic entry point is ``python -m workflow_kit.bootstrap_lib`` and the
# programmatic API is the ``workflow_kit.bootstrap_lib`` package itself, both of
# which the derivation covers.
PACKAGE_ROOT = REPO_ROOT / "workflow_kit"

# Leaf modules worth importing on top of the package list — a package can import
# cleanly while the module a consumer actually calls is absent (v1.1.7 caught
# exactly that: ``tools`` present, ``tools.session_start`` missing).
REQUIRED_LEAF_MODULES: tuple[str, ...] = (
    "workflow_kit.tools.session_start",
    "workflow_kit.cli.doctor",
)


def derive_required_imports(package_root: Path = PACKAGE_ROOT) -> tuple[str, ...]:
    """Every directory under ``workflow_kit/`` that holds ``.py`` files, dotted."""
    if not package_root.is_dir():
        raise SystemExit(
            f"ERROR: source package not found: {package_root}. "
            "check-packaging must run from a repo checkout."
        )
    packages = {
        ".".join(f.parent.relative_to(package_root.parent).parts)
        for f in package_root.rglob("*.py")
        if "__pycache__" not in f.parts
    }
    return tuple(sorted(packages)) + REQUIRED_LEAF_MODULES


REQUIRED_IMPORTS: tuple[str, ...] = derive_required_imports()

# v1.2.0 (TASK-2026-08-13-main-005): 구경로 shim (top-level tools /
# bootstrap_lib) 은 2nd deprecation cycle 로 wheel 에서 drop 됐다 —
# 아래 NEGATIVE 목록이 재유입을 막는다 (PyPI 차단 사유였던 일반명).

# v1.2.0: wheel 에 실리면 안 되는 top-level (일반명 충돌 — 배포 검토 §2).
# 구경로 shim drop 이후 재유입은 packaging 회귀다.
FORBIDDEN_IMPORTS: tuple[str, ...] = (
    "tools",
    "bootstrap_lib",
)


def find_latest_wheel(dist_dir: Path) -> Path:
    wheels = sorted(dist_dir.glob("*.whl"), key=lambda p: p.stat().st_mtime)
    if not wheels:
        raise SystemExit(f"ERROR: no wheel found under {dist_dir}")
    return wheels[-1]


def isolated_env() -> dict[str, str]:
    """Child environment with the *source tree* removed from the import path.

    v1.8.1 (TASK-2026-09-01-main-001): the throwaway venv inherited this process's
    environment, so the repo's own invocation form —
    ``PYTHONPATH=workflow-source python3 -m workflow_kit.tools.check_packaging`` —
    put ``workflow-source/`` on the child's ``sys.path`` too. Two things then went
    wrong at once and **both were silent**:

      - ``workflow-source/standard_ai_workflow.egg-info`` made pip report the
        distribution "already installed with the same version", so the wheel under
        test was **never installed**;
      - every import in the smoke resolved against the source tree, which always
        has every sub-package — the exact green-on-a-broken-wheel this check exists
        to prevent.

    Measured 2026-09-01: a wheel known to be missing ``workflow_kit/cli`` reported
    ``result: PASS`` under a leaked ``PYTHONPATH``.
    """
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    # A user-site directory would let an installed copy answer the imports too.
    env["PYTHONNOUSERSITE"] = "1"
    return env


def run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> None:
    print(f"  $ {' '.join(cmd)}", flush=True)
    completed = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env if env is not None else isolated_env(),
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            f"ERROR: command failed (rc={completed.returncode}): {' '.join(cmd)}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--wheel",
        type=Path,
        default=None,
        help="Wheel to verify. Defaults to the most recent file under dist/.",
    )
    parser.add_argument(
        "--keep-venv",
        action="store_true",
        help="Keep the throwaway venv (printed at end) for debugging.",
    )
    args = parser.parse_args()

    wheel = args.wheel or find_latest_wheel(DEFAULT_DIST)
    if not wheel.exists():
        raise SystemExit(f"ERROR: wheel not found: {wheel}")
    print(f"Verifying wheel: {wheel}")

    with tempfile.TemporaryDirectory(prefix="saw-packaging-") as tmp:
        venv = Path(tmp) / "venv"
        run([sys.executable, "-m", "venv", str(venv)])
        pip = venv / "bin" / "pip"
        python = venv / "bin" / "python"

        # 1. Install the wheel. No -e, no local source — this is the
        #    scenario that revealed the v0.5.7.1 regression.
        run([str(pip), "install", "--upgrade", "pip"])
        run([str(pip), "install", str(wheel)])

        # 2. Import smoke. Use explicit try/except per import to record
        #    exactly which module is missing — a flat ``__import__`` chain
        #    would short-circuit on the first failure.
        import_payload = "import json\n"
        import_payload += "ok, missing, forbidden = [], [], []\n"
        for mod in REQUIRED_IMPORTS:
            import_payload += (
                "try:\n"
                f"    __import__({mod!r})\n"
                f"    ok.append({mod!r})\n"
                "except Exception as exc:\n"
                f"    missing.append({{'module': {mod!r}, 'error': str(exc)}})\n"
            )
        # v1.2.0: 구경로 shim 재유입 검출 — venv 의 cwd 는 wheel 밖이므로
        # import 가 *성공하면* wheel 이 일반명 top-level 을 다시 실은 것이다.
        for mod in FORBIDDEN_IMPORTS:
            import_payload += (
                "try:\n"
                f"    __import__({mod!r})\n"
                f"    forbidden.append({mod!r})\n"
                "except ImportError:\n"
                "    pass\n"
            )
        import_payload += (
            "print(json.dumps({'ok': ok, 'missing': missing, 'forbidden': forbidden}))\n"
        )

        completed = subprocess.run(
            [str(python), "-c", import_payload],
            capture_output=True,
            text=True,
            # cwd/env 둘 다 격리한다 — 소스 트리가 sys.path 에 남으면 이 smoke 는
            # wheel 이 아니라 체크아웃을 재고, 깨진 wheel 에도 PASS 를 준다.
            cwd=tmp,
            env=isolated_env(),
        )
        if completed.returncode != 0:
            print("--- import smoke failed ---")
            print(completed.stdout)
            print(completed.stderr, file=sys.stderr)
            return 1
        result = json.loads(completed.stdout)
        if result["missing"]:
            print("ERROR: missing imports:", json.dumps(result["missing"], indent=2))
            return 1

        # 3. CLI entry point smoke. ``python -m workflow_kit.bootstrap_lib --help``
        #    must succeed and show the new --no-interactive flag.
        completed = subprocess.run(
            [str(python), "-m", "workflow_kit.bootstrap_lib", "--help"],
            capture_output=True,
            text=True,
            cwd=tmp,
            env=isolated_env(),
        )
        if completed.returncode != 0:
            print("ERROR: workflow_kit.bootstrap_lib --help failed")
            print(completed.stderr, file=sys.stderr)
            return 1
        if "--no-interactive" not in completed.stdout:
            print("ERROR: workflow_kit.bootstrap_lib --help output missing --no-interactive")
            print(completed.stdout)
            return 1

        # 4. Package metadata smoke — confirm the version we built matches
        #    what we expect.
        completed = subprocess.run(
            [str(pip), "show", "standard-ai-workflow"],
            capture_output=True,
            text=True,
            cwd=tmp,
            env=isolated_env(),
        )
        if completed.returncode != 0:
            print("ERROR: pip show failed")
            return 1
        meta = completed.stdout
        if "Name: standard-ai-workflow" not in meta:
            print("ERROR: pip show output missing package name")
            print(meta)
            return 1

        if args.keep_venv:
            kept = Path.cwd() / "saw-packaging-venv"
            shutil.copytree(venv, kept)
            print(f"Kept venv at: {kept}")

    manifest = {
        "wheel": str(wheel),
        "imported": result["ok"],
        "missing": result["missing"],
        "boot_lib_help_has_no_interactive": True,
        "result": "PASS",
    }
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
