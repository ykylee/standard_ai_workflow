#!/usr/bin/env python3
"""1.x 안내 판 — session-start 의 2.0 안내 · EOL 한 줄 (요구 R14.8 · R16.3 · R16.4).

정본: ``workflow_kit/common/transition_notice.py``. 실제 git 저장소 fixture 에서 문서화된 입구
(``python -m workflow_kit session-start``)로 부르고, 기준 날짜는 ``WORKFLOW_KIT_NOTICE_TODAY`` 로 주입한다.

1. 경계 — EOL 전날은 2.0 안내, 당일 · 뒤는 EOL 안내, 둘 다 EOL 날짜를 싣는다
2. session-start — EOL 전 · 뒤 모두 종료 코드 0 · status 같음 · summary 의 마지막 줄 하나가 그 안내 (막지 않는다),
   안내는 warnings 에 없고 권장 다음 행동이 안내 없는 대조군과 같다
3. 주입 값이 날짜가 아니면 오늘로 — 안내가 빠지지 않는다
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 300

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/check_branch_memory_auto_seed.py",
    "workflow-source/tests/check_memory_lint.py",  # auto-seed fixture 가 import 한다
    "workflow-source/pyproject.toml",
)

import json
import os
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_branch_memory_auto_seed as seedfx  # noqa: E402
from workflow_kit.common import transition_notice as tn  # noqa: E402

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


def _run(cwd: Path, today: str | None) -> tuple[int, dict[str, Any]]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    env.pop(tn.TODAY_ENV, None)
    for k in ("GIT_DIR", "GIT_WORK_TREE", "CODEX_WORKFLOW_BRANCH"):
        env.pop(k, None)
    if today is not None:
        env[tn.TODAY_ENV] = today
    p = subprocess.run([sys.executable, "-m", "workflow_kit", "session-start"], cwd=cwd, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    try:
        return p.returncode, json.loads(p.stdout)
    except ValueError:
        return p.returncode, {"status": "unparsable", "stdout": p.stdout[-300:], "stderr": p.stderr[-300:]}


def main() -> int:
    print("check_transition_notice")
    eol = tn.EOL_DATE
    before, on, after = tn.notice(eol - timedelta(days=1)), tn.notice(eol), tn.notice(eol + timedelta(days=400))
    ok1 = (before.startswith("[2.0]") and on.startswith("[EOL]") and after == on and before != on
           and all(eol.isoformat() in s for s in (before, on)) and "\n" not in before + on)
    _record("case 1 (경계 — 전날 2.0 안내 · 당일/뒤 EOL · 날짜 실음 · 한 줄)", ok1, f"{before!r} / {on!r}")

    with tempfile.TemporaryDirectory(prefix="notice-") as d:
        clone = seedfx._make_repo(Path(d))
        runs = {label: _run(clone, val) for label, val in
                (("before", (eol - timedelta(days=1)).isoformat()), ("after", eol.isoformat()))}
        problems = []
        for label, (rc, out) in runs.items():
            want = before if label == "before" else on
            summary = out.get("summary") or []
            hits = [s for s in summary if s in (before, on)]
            if rc != 0 or out.get("status") not in ("ok", "warning"):
                problems.append(f"{label}: rc={rc} status={out.get('status')} {str(out)[:200]}")
            elif not summary or summary[-1] != want or hits != [want]:
                problems.append(f"{label}: 마지막 줄={summary[-1:]} 안내 수={len(hits)}")
            if any(want in w for w in out.get("warnings", [])):
                problems.append(f"{label}: 안내가 warnings 에")
        (rc_b, b), (rc_a, a) = runs["before"], runs["after"]
        if b.get("status") != a.get("status") or rc_b != rc_a or b.get("recommended_next_action") != a.get("recommended_next_action"):
            problems.append("EOL 전후로 종료 코드 · status · 권장 행동이 달라졌다")
        _record("case 2 (session-start — 막지 않음 · 마지막 줄 하나 · warnings 아님 · EOL 전후 같은 판정)", not problems,
                "; ".join(problems))

        rc3, out3 = _run(clone, "not-a-date")
        want3 = tn.notice(date.today())
        _record("case 3 (주입 값이 날짜가 아니면 오늘 — 안내 유지)", rc3 == 0 and (out3.get("summary") or [""])[-1] == want3,
                f"rc={rc3} last={(out3.get('summary') or [''])[-1:]}")

    print(f"PASS {len(_passes)} · FAIL {len(_failures)}")
    for f in _failures:
        print(f"  FAIL {f}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
