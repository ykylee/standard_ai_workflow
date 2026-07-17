#!/usr/bin/env python3
"""Smoke test — Harness verification (v0.15.9+).

10 harness (codex, opencode, gemini-cli, antigravity, minimax-code, claude-code,
aider, goose, pi-dev, codewhale) 의 directory + apply_guide.md/AGENTS.md +
Panel 1+2 + maturity_matrix 3-way cross-check.

4 cases:
  1) **10 harness 디렉토리 존재 + non-empty**: `workflow-source/harnesses/{name}/`
     각 디렉토리 부재 시 fail, empty 시 fail. 비어있지 않은지 (적어도 1 file)
     검증.
  2) **apply_guide.md / AGENTS.md 존재**: 각 harness 의 진입점 file 부재 시 fail.
     pi-dev 는 AGENTS.md 만, 나머지는 apply_guide.md 정공법. (정밀도: 둘 중 하나
     이상 존재).
  3) **Panel 1+2 harness 정합**: Panel 1 `harness_supported_count` == Panel 2
     `harnesses.supported` == maturity_matrix `harnesses.supported` list 길이.
  4) **3-way set 동등성**: Panel 2 `harnesses.supported_names` (set) ==
     maturity_matrix `harnesses.supported` (set) ==
     `workflow-source/harnesses/` 실제 디렉토리 list (set, _template/custom 제외).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
HARNESSES_DIR = SOURCE_ROOT / "harnesses"
MATURITY_PATH = SOURCE_ROOT / "core" / "maturity_matrix.json"

# Harness 정공법: pi-dev 는 AGENTS.md 만, 나머지는 apply_guide.md 정공법
# (정밀도: 둘 중 하나 이상).
HARNESS_MIN_ENTRY_FILES = ["apply_guide.md", "AGENTS.md"]

# 실제 검증 대상 10개 (maturity_matrix.harnesses.supported 와 정합 검증용)
# 3-way cross-check 의 expected set.
EXPECTED_HARNESSES = {
    "codex", "opencode", "gemini-cli", "antigravity", "minimax-code",
    "claude-code", "aider", "goose", "pi-dev", "codewhale",
}


def _collect_dashboard() -> dict:
    """workflow_kit_cli dashboard --format=json subprocess 호출."""
    proc = subprocess.run(
        [sys.executable, "-m", "workflow_kit.workflow_kit_cli",
         "--command=dashboard", "--format=json"],
        cwd=str(REPO_ROOT),
        env={"PYTHONPATH": str(SOURCE_ROOT), "PATH": __import__("os").environ.get("PATH", "")},
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"dashboard --format=json failed: {proc.stderr[:300]}")
    return json.loads(proc.stdout)


def _load_maturity_matrix() -> dict:
    if not MATURITY_PATH.is_file():
        raise AssertionError(f"maturity_matrix 부재: {MATURITY_PATH}")
    return json.loads(MATURITY_PATH.read_text(encoding="utf-8"))


def case_1_harness_directories_exist() -> bool:
    """1) 10 harness 디렉토리 존재 + non-empty 검증."""
    if not HARNESSES_DIR.is_dir():
        print(f"  FAIL: harnesses dir 부재: {HARNESSES_DIR}")
        return False
    missing: list[str] = []
    empty: list[str] = []
    for name in EXPECTED_HARNESSES:
        h_dir = HARNESSES_DIR / name
        if not h_dir.is_dir():
            missing.append(name)
            continue
        # non-empty: 적어도 1 file
        if not any(h_dir.iterdir()):
            empty.append(name)
    if missing:
        print(f"  FAIL: harness 디렉토리 부재: {missing}")
        return False
    if empty:
        print(f"  FAIL: harness 디렉토리 empty: {empty}")
        return False
    print(f"  [info] 10 harness 디렉토리 모두 존재 + non-empty")
    return True


def case_2_entry_files_exist() -> bool:
    """2) apply_guide.md / AGENTS.md 존재 검증 (둘 중 하나 이상)."""
    missing_entry: dict[str, list[str]] = {}
    for name in EXPECTED_HARNESSES:
        h_dir = HARNESSES_DIR / name
        present = [f for f in HARNESS_MIN_ENTRY_FILES if (h_dir / f).is_file()]
        if not present:
            missing_entry[name] = HARNESS_MIN_ENTRY_FILES
    if missing_entry:
        print(f"  FAIL: harness 진입점 file 부재: {missing_entry}")
        return False
    print(f"  [info] 10 harness 진입점 file 모두 존재")
    return True


def case_3_panel_1_plus_2_harness_count() -> bool:
    """3) Panel 1+2 harness count 정합."""
    d = _collect_dashboard()
    panel_1 = d["panels"]["drift_prevention"]
    panel_2 = d["panels"]["maturity_distribution"]
    p1_count = int(panel_1.get("harness_supported_count", -1))
    p2_count = int(panel_2["harnesses"].get("supported", -1))
    mm = _load_maturity_matrix()
    mm_count = len(mm.get("harnesses", {}).get("supported", []))
    if p1_count != p2_count:
        print(f"  FAIL: Panel 1 harness={p1_count} != Panel 2 harness={p2_count}")
        return False
    if p1_count != mm_count:
        print(f"  FAIL: Panel harness={p1_count} != maturity_matrix={mm_count}")
        return False
    if p1_count != len(EXPECTED_HARNESSES):
        print(f"  FAIL: harness count={p1_count} != expected={len(EXPECTED_HARNESSES)}")
        return False
    print(f"  [info] Panel 1+2+mm harness count = {p1_count} (expected 10)")
    return True


def case_4_3_way_set_equality() -> bool:
    """4) 3-way set 동등성: Panel 2 names = mm supported = workflow-source/harnesses dir."""
    d = _collect_dashboard()
    panel_2 = d["panels"]["maturity_distribution"]
    p2_names = set(panel_2["harnesses"].get("supported_names", []))
    mm = _load_maturity_matrix()
    mm_names = set(mm.get("harnesses", {}).get("supported", []))
    # 실제 file system 의 harness 디렉토리 (set)
    # exclude: hidden, _template, custom (v0.10.0 이전 부가 디렉토리)
    EXCLUDED = {"_template", "custom"}
    fs_names: set[str] = set()
    if HARNESSES_DIR.is_dir():
        for entry in HARNESSES_DIR.iterdir():
            if entry.is_dir() and not entry.name.startswith(("_", ".")) and entry.name not in EXCLUDED:
                fs_names.add(entry.name)
    # 3-way set 동등성
    if p2_names != mm_names:
        print(f"  FAIL: Panel 2 names={p2_names} != maturity_matrix={mm_names}")
        return False
    if p2_names != fs_names:
        missing_in_panel = fs_names - p2_names
        extra_in_panel = p2_names - fs_names
        print(f"  FAIL: Panel 2 names={p2_names} != file system={fs_names}")
        if missing_in_panel:
            print(f"    file system 에만 있음: {missing_in_panel}")
        if extra_in_panel:
            print(f"    Panel 2 에만 있음 (stale): {extra_in_panel}")
        return False
    # 3-way 모두 동일 set 정합
    print(f"  [info] 3-way set 동등: {sorted(p2_names)} (10 harness)")
    return True


def main() -> int:
    cases = [
        ("case_1_harness_directories_exist", case_1_harness_directories_exist),
        ("case_2_entry_files_exist", case_2_entry_files_exist),
        ("case_3_panel_1_plus_2_harness_count", case_3_panel_1_plus_2_harness_count),
        ("case_4_3_way_set_equality", case_4_3_way_set_equality),
    ]
    results: list[tuple[str, bool]] = []
    for name, fn in cases:
        results.append((name, fn()))
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {name}")
    print(f"\n=== {passed}/{len(cases)} PASS ===")
    if passed != len(cases):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
