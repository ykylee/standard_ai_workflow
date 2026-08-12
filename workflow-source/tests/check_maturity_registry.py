#!/usr/bin/env python3
"""Meta-check: maturity_matrix 의 **선언**과 디스크의 **실제**가 일치하는가.

## 왜 필요한가

한 사이클에 "선언과 실제의 괴리" 가 두 번 나왔다:

- `git-conflict-resolver` — `stage: stable` 로 등재됐는데 entrypoint 가 ImportError 로
  **실행조차 되지 않았다** (`check_executable_surface` 가 잡음).
- `memory-freeze` — 실제로는 governance 필수 규칙(R8)의 구현인데 registry 에 **아예
  등재되지 않았고**, SKILL.md 는 `prototype` 이었다. v0.6.6 이후 1년 가까이 실행
  불가였던 것도 아무도 몰랐다.

그 밖에 registry ↔ 디스크가 **3방향으로 드리프트**해 있었다:
디렉터리명 규약 이탈(`robust_patcher`), 등재됐지만 디스크 부재(`task-modes`),
디스크에 있지만 미등재(`memory-index-query`).

`check_executable_surface` 는 "실행 가능한가" 를 보고, 본 check 는 **"선언이 사실인가"**
를 본다. 둘은 상보적이다.

3 case:
  1. registry ↔ 디스크 양방향 정합 (spec 항목과 명시적 exempt 는 제외)
  2. `stage: stable` 인 executable skill 이 `skill_beta_criteria.md` §3.1 의 조건 충족
  3. `test_path` 가 실재하는 파일을 가리킴
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
MATRIX = SOURCE_ROOT / "core" / "maturity_matrix.json"
SKILLS_DIR = SOURCE_ROOT / "skills"

sys.path.insert(0, str(SOURCE_ROOT))

# v1.0.4(§2.48): `kind: "spec"` 규약을 이 파일이 리터럴로 들고 있었다. 같은 규약을
# kit 의 린터는 몰라서 위양성을 냈다 — 어휘 정본은 common/maturity.py 한 곳이다.
from workflow_kit.common.maturity import is_spec_entry, requires_test_path  # noqa: E402


def _load() -> dict:
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def _disk_skill_dirs(exempt: set[str]) -> set[str]:
    """skill 디렉터리 = SKILL.md 를 가진 디렉터리.

    `workers/` 처럼 SKILL.md 가 없는 보조 디렉터리는 skill 이 아니다.
    """
    out: set[str] = set()
    for p in SKILLS_DIR.iterdir():
        if not p.is_dir() or p.name in exempt or p.name.startswith("__"):
            continue
        if (p / "SKILL.md").exists():
            out.add(p.name)
    return out


def test_case_1_registry_disk_parity() -> None:
    """등재 목록과 디스크 skill 디렉터리가 양방향으로 일치한다."""
    d = _load()
    skills = d["skills"]
    exempt = set(d.get("skill_registry_exempt_dirs", []))
    disk = _disk_skill_dirs(exempt)
    # spec 항목은 실행 디렉터리를 갖지 않는다.
    registered_exec = {k for k, v in skills.items() if not is_spec_entry(v)}

    unregistered = sorted(disk - registered_exec)
    missing_dir = sorted(registered_exec - disk)
    problems = []
    if unregistered:
        problems.append(f"디스크에 있으나 미등재: {unregistered}")
    if missing_dir:
        problems.append(f"등재됐으나 디렉터리 부재: {missing_dir}")
    assert not problems, (
        "maturity_matrix ↔ 디스크 드리프트:\n  " + "\n  ".join(problems)
        + "\n\n→ 실행 skill 이면 등재하고, 명세면 kind='spec', "
          "skill 이 아닌 디렉터리면 skill_registry_exempt_dirs 에 추가할 것."
    )
    print(f"  case 1: registry {len(registered_exec)} ↔ 디스크 {len(disk)} 일치 "
          f"(spec {len(skills) - len(registered_exec)}, exempt {len(exempt)})")


def test_case_2_stable_meets_criteria() -> None:
    """`stage: stable` 인 executable skill 이 승격 조건을 충족한다.

    `core/skill_beta_criteria.md` §3.1 의 조건 중 **기계적으로 검증 가능한** 것:
      - 단일 실행 스크립트 `scripts/run_<skill>.py`
      - CLI 파라미터 정의 (argparse `add_argument`)
      - (error_code 최소 3종은 선언 위치가 통일돼 있지 않아 정적 검증에서 제외 — 본문 주석 참조)
      - smoke test (`test_path`) 존재
      - SKILL.md 에 실행 예시 절
    """
    d = _load()
    violations: list[str] = []
    for name, entry in sorted(d["skills"].items()):
        if is_spec_entry(entry) or entry.get("stage") != "stable":
            continue
        skill_dir = SKILLS_DIR / name
        problems: list[str] = []

        run_script = skill_dir / "scripts" / f"run_{name.replace('-', '_')}.py"
        # v1.1.7+ (TASK-2026-08-11-main-021): 일부 skill 은 구현이 `tools/` 로 올라갔고
        # `skills/.../run_*.py` 에는 wrapper 만 남았다. 판정 대상은 **구현체**다 —
        # 기준의 뜻은 "이 skill 이 파라미터를 받는 CLI 를 갖는가" 이지 "특정 파일에
        # argparse 리터럴이 있는가" 가 아니다. 두 자리 중 하나라도 충족하면 통과한다.
        impl_candidates = [run_script, SOURCE_ROOT / "workflow_kit" / "tools" / f"{name.replace('-', '_')}.py"]
        if not run_script.exists():
            problems.append(f"실행 스크립트 부재({run_script.name})")
        else:
            if not any(
                p.exists() and "add_argument" in p.read_text(encoding="utf-8", errors="ignore")
                for p in impl_candidates
            ):
                problems.append("argparse add_argument 부재")
            # error_code 최소 3종은 §3.1 의 조건이지만 **정적으로 검증하지 않는다.**
            # 선언 위치가 통일돼 있지 않기 때문이다: run script 의 inline literal,
            # `.get("error_code", "...")` default, 그리고 일부는 schema 쪽
            # `*_ERROR_CODES` tuple (게다가 schema module 명이 skill 명과 1:1 이
            # 아니다 — workflow-linter → linter.py, git-conflict-resolver → git.py).
            # 어설픈 정규식 계수는 위양성을 내고, **위양성을 내는 check 는 무시당해
            # 결국 아무것도 막지 못한다.** 규약(`<SKILL>_ERROR_CODES` tuple 통일)이
            # 생기면 그때 기계 검증으로 승격한다.

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            problems.append("SKILL.md 부재")
        else:
            md = skill_md.read_text(encoding="utf-8", errors="ignore")
            if not re.search(r"##.*(실행|사용|Usage)", md):
                problems.append("SKILL.md 실행/사용 절 부재")

        if not entry.get("test_path"):
            problems.append("test_path 미지정")

        if problems:
            violations.append(f"{name}: {', '.join(problems)}")

    assert not violations, (
        "stable 등재인데 승격 조건 미충족:\n  " + "\n  ".join(violations)
        + "\n\n→ 조건을 채우거나 stage 를 낮출 것. **라벨만 stable 로 두지 않는다.**"
    )
    stable = [k for k, v in d["skills"].items()
              if v.get("stage") == "stable" and not is_spec_entry(v)]
    print(f"  case 2: stable {len(stable)}종 모두 승격 조건 충족")


def test_case_3_test_paths_exist() -> None:
    """`test_path` 가 실재하는 파일을 가리킨다 (spec 은 null 허용)."""
    d = _load()
    missing: list[str] = []
    checked = 0
    for name, entry in sorted(d["skills"].items()):
        tp = entry.get("test_path")
        if not tp:
            if requires_test_path(entry):
                missing.append(f"{name}: test_path null 인데 stage={entry.get('stage')}")
            continue
        checked += 1
        if not (SOURCE_ROOT / tp).exists():
            missing.append(f"{name}: {tp} 부재")
    assert not missing, "test_path 문제:\n  " + "\n  ".join(missing)
    print(f"  case 3: test_path {checked}건 모두 실재")


CASES = [
    ("test_case_1_registry_disk_parity", test_case_1_registry_disk_parity),
    ("test_case_2_stable_meets_criteria", test_case_2_stable_meets_criteria),
    ("test_case_3_test_paths_exist", test_case_3_test_paths_exist),
]


def main() -> int:
    print("=== maturity registry 선언 ↔ 실제 정합 ===")
    failures = 0
    for name, fn in CASES:
        try:
            fn()
            print(f"  PASS: {name}")
        except AssertionError as exc:
            print(f"  FAIL: {name}\n    {exc}")
            failures += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL: {name}\n    {type(exc).__name__}: {exc}")
            failures += 1
    print(f"=== {'PASS' if failures == 0 else 'FAIL'}: {len(CASES) - failures}/{len(CASES)} ===")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
