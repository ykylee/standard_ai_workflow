"""branch protection 판정 smoke (TASK-2026-08-09-main-004, 3-layer defense 3rd layer)

`evaluate_protection()` 은 pure function 이라 gh 없이 fixture JSON 으로 전부
검증할 수 있다. CLI 는 gh 유무에 따라 graceful skip 하는지만 본다 — 실제 GitHub
응답에 의존하는 검사는 네트워크/권한에 따라 흔들려서 회귀 검사로 쓸 수 없다.

검증 케이스 (8):
    1. 404 (보호 없음) → protected=False, ok=False
    2. force push 허용 → ok=False + finding
    3. 삭제 허용 → ok=False + finding
    4. 둘 다 차단 → ok=True
    5. 필드 부재(권한 부족) → *통과로 치지 않는다* (모름 ≠ 안전)
    6. 평평한 bool 형식도 읽는다
    7. advisory 수집 (reviews / status checks / enforce_admins)
    8. CLI graceful skip — gh 부재 시 rc 0, --require-gh 시 rc 1

Stdlib only.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.branch_protection import evaluate_protection  # noqa: E402

PROTECTED = {
    "allow_force_pushes": {"enabled": False},
    "allow_deletions": {"enabled": False},
    "enforce_admins": {"enabled": True},
    "required_pull_request_reviews": {"required_approving_review_count": 1},
    "required_status_checks": {"contexts": ["ci", "mcp-sdk-matrix"]},
}


def main() -> int:
    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        if cond:
            print(f"PASS: {label}")
        else:
            print(f"FAIL: {label} — {detail}")
            failures.append(label)

    # 1) 404
    v = evaluate_protection(None, not_found=True)
    check(
        "1) 404 → protected=False, ok=False",
        v.protected is False and v.ok is False and v.findings,
        f"{v.to_dict()}",
    )

    # 2) force push 허용
    v = evaluate_protection({**PROTECTED, "allow_force_pushes": {"enabled": True}})
    check(
        "2) force push 허용 → ok=False",
        v.ok is False and v.force_push_blocked is False
        and any("allow_force_pushes=true" in f for f in v.findings),
        f"{v.to_dict()}",
    )

    # 3) 삭제 허용
    v = evaluate_protection({**PROTECTED, "allow_deletions": {"enabled": True}})
    check(
        "3) 삭제 허용 → ok=False",
        v.ok is False and v.deletion_blocked is False
        and any("allow_deletions=true" in f for f in v.findings),
        f"{v.to_dict()}",
    )

    # 4) 둘 다 차단
    v = evaluate_protection(PROTECTED)
    check(
        "4) 둘 다 차단 → ok=True",
        v.ok is True and v.protected and v.force_push_blocked and v.deletion_blocked,
        f"{v.to_dict()}",
    )

    # 5) 필드 부재 — 모름을 안전으로 치면 안 된다
    v = evaluate_protection({"required_status_checks": {"contexts": []}})
    check(
        "5) 필드 부재 → 통과로 치지 않음 (모름 ≠ 안전)",
        v.protected is True and v.ok is False
        and any("읽지 못했다" in f for f in v.findings),
        f"{v.to_dict()}",
    )

    # 6) 평평한 bool
    v = evaluate_protection({"allow_force_pushes": False, "allow_deletions": False})
    check("6) 평평한 bool 형식도 읽는다", v.ok is True, f"{v.to_dict()}")

    # 7) advisory 수집
    v = evaluate_protection(PROTECTED)
    check(
        "7) advisory 수집",
        v.advisory.get("required_approving_review_count") == 1
        and v.advisory.get("required_status_checks") == 2
        and v.advisory.get("enforce_admins") is True,
        f"advisory={v.advisory}",
    )

    # 8) CLI graceful skip — PATH 를 비워 gh 를 없앤다
    cli = SOURCE_ROOT / "workflow_kit" / "tools" / "check_branch_protection.py"
    env_no_gh = {"PATH": "/nonexistent", "PYTHONPATH": str(SOURCE_ROOT)}
    plain = subprocess.run(
        [sys.executable, str(cli), "--json"],
        capture_output=True, text=True, timeout=60, env=env_no_gh,
    )
    strict = subprocess.run(
        [sys.executable, str(cli), "--json", "--require-gh"],
        capture_output=True, text=True, timeout=60, env=env_no_gh,
    )
    check(
        "8) gh 부재 → rc 0 (skip) / --require-gh → rc 1",
        plain.returncode == 0 and strict.returncode == 1 and "skipped" in plain.stdout,
        f"plain={plain.returncode} strict={strict.returncode} out={plain.stdout[:120]!r}",
    )

    total = 8
    print()
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
