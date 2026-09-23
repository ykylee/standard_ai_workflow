#!/usr/bin/env python3
"""Meta-check: **CLI 가 모르는 인자를 거절하는가** (TASK-2026-09-23-main-008).

v1.11.0 발행 준비에서 `wk release-bump --version 1.11.0 --apply` 를 돌렸다.
실제 플래그는 `--to` 였고, 도구는 **모르는 `--version` 을 조용히 버린 뒤**
patch 자동 증가(1.10.0 → 1.10.1)를 하고 post-step 이 `git commit --amend` 로
직전 커밋을 덮었다. push 전이라 되돌렸지만, 인자를 버리는 CLI 는 **사용자가
요청한 것과 다른 일을 하면서 성공을 보고한다.**

원인은 `release-bump` 하나가 아니었다. `cli_commands_*` 계열은 argparse 대신
`_parse_flag` / `_has_flag` 로 손수 파싱하는데, 그 함수들은 찾는 것만 보고
**나머지는 전부 무시**한다. 등록 커맨드 76개 중 이 방식이 37개다.

허용집합은 **손 목록이 아니라 소스에서 파생**한다 (`known_flags_for`):
자기 docstring 의 `--flag` 표기 ∪ 자기 본문의 `_parse_flag`/`_has_flag` 리터럴
∪ 같은 모듈 `_` 헬퍼의 리터럴. 호출한 헬퍼만으로 좁히지 않는다 — 함수를 인자로
받는 래퍼 하나에 호출그래프 파생이 조용히 풀리는 것을 이미 겪었다. 실측 허용집합
중앙값은 4개다.

나머지 39개는 argparse 기반이라 **자기 파서가 이미 거절한다.** 거기서는 가드를
켜지 않는다 — 켜면 argparse 의 풍부한 `--help` 를 빈약한 docstring 으로 덮는다.
그 39개가 정말 거절하는지는 case 3 이 실측한다 (미측정을 통과로 세지 않는다).

검증 케이스 (8):
    1. 손 파싱 커맨드가 모르는 플래그를 rc=2 로 거절한다
    2. 거절 메시지가 **받는 목록**을 알려준다 (사용자가 다음에 뭘 칠지 안다)
    3. argparse 커맨드도 모르는 플래그를 거절한다 (전수 실측, 통과로 세지 않는다)
    4. 정상 플래그는 그대로 통과한다 (위양성 없음)
    5. `--help` 는 부수효과 없이 도움말만 낸다
    6. 허용집합이 docstring **에만** 있는 플래그를 받는다 (탐침)
    6b. 허용집합이 본문 **에만** 있는 플래그를 받는다 (탐침)
    6c. 실물 커맨드가 받는 것만 받고 `--version` 은 안 받는다

Stdlib only (+ subprocess 로 CLI 실측).
"""

from __future__ import annotations

#: 전역 선언 — case 3 이 등록 커맨드 **전수**를 서브프로세스로 돈다.
WATCHES_ALL_REASON = (
    "case 3 이 argparse 기반 등록 커맨드 전수에 모르는 플래그를 물려 거절을 "
    "실측한다. 판정 정본은 `workflow_kit/cli_registry.py` 의 `known_flags_for` 와 "
    "`register` 가드다"
)

#: 이 검사가 강제하는 정본 요구 (spec §7).
ENFORCES = ("cli-must-reject-unknown-flags",)

import os
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.cli_registry import (  # noqa: E402
    COMMANDS, _has_flag, known_flags_for,
)

#: 저장소를 건드리거나 네트워크를 타는 커맨드는 case 3 에서 **부르지 않는다** —
#: 모르는 플래그로도 거절 전에 초기화가 돌 수 있다. 거절만 재는 데는 불필요하다.
_SKIP_IN_SWEEP = {
    "release-pipeline", "release-create", "release-dist", "release-rollback",
    "release-v0-13-0", "host-serve-registry", "host-pull-registry",
    "install-pre-push-hook", "claim-workspace", "federate",
}


def _probe_command(argv: list[str]) -> int:
    """탐침 — 허용집합 파생의 **두 출처**를 각각 발화시킨다.

    Args:
        --doc-only   docstring 에만 있다 (본문은 안 읽는다)
    """
    # 본문에만 있는 쪽 — docstring 에는 없다
    _ = _has_flag(argv, "--body-only")
    return 0


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items()}
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    return subprocess.run(
        [sys.executable, "-m", "workflow_kit.workflow_kit_cli", *args],
        cwd=str(cwd), capture_output=True, text=True, timeout=120, env=env,
    )


def main() -> int:
    ran: list[str] = []
    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        ran.append(label)
        if cond:
            print(f"  PASS  {label}")
        else:
            print(f"  FAIL  {label} — {detail}")
            failures.append(label)

    repo = SOURCE_ROOT.parent

    # 1·2) 손 파싱 커맨드
    p = _run(["--command=release-bump", "--zzz-nope"], repo)
    check("1) 손 파싱 커맨드가 모르는 플래그를 rc=2 로 거절한다",
          p.returncode == 2, f"rc={p.returncode} out={(p.stdout + p.stderr)[:160]}")
    msg = p.stdout + p.stderr
    check("2) 거절 메시지가 받는 목록을 알려준다",
          "--to" in msg and "--apply" in msg, f"msg={msg[:200]}")

    # 3) **argparse 계열도 거절하는가 — 전수 실측.** 가드가 꺼진 자리를
    #    '알아서 거절하겠지' 로 넘기면 그건 미측정이지 통과가 아니다.
    guardless = [
        n for n, fn in sorted(COMMANDS.items())
        if not known_flags_for(getattr(fn, "__wrapped__", fn)) and n not in _SKIP_IN_SWEEP
    ]
    accepted: list[str] = []
    for name in guardless:
        r = _run([f"--command={name}", "--zzz-nope"], repo)
        if r.returncode == 0:
            accepted.append(name)
    check(f"3) argparse 계열 {len(guardless)}개가 모르는 플래그를 받아들이지 않는다",
          not accepted, f"rc=0 으로 받아들인 커맨드: {accepted[:5]}")

    # 4) 위양성 없음 — 정상 플래그는 통과한다
    ok = _run(["--command=release-bump", "--to=9.9.9"], repo)
    check("4) 정상 플래그는 통과한다 (위양성 없음)",
          ok.returncode == 0 and "9.9.9" in ok.stdout,
          f"rc={ok.returncode} out={ok.stdout[:160]}")

    # 5) --help 는 부수효과가 없다
    before = (SOURCE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    h = _run(["--command=release-bump", "--help"], repo)
    after = (SOURCE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    check("5) --help 는 도움말만 내고 아무것도 안 바꾼다",
          h.returncode == 0 and "--to=VERSION" in h.stdout and before == after,
          f"rc={h.returncode} 변경={before != after} out={h.stdout[:120]}")

    # 6) 허용집합이 **소스에서 파생**된다 — 두 출처를 **각각** 발화시킨다.
    #    실물(`cmd_release_bump`)만 쓰면 네 플래그가 docstring 과 본문 양쪽에 있어
    #    docstring 기여를 지워도 case 가 green 이다 (2026-09-23 되주입 M3 실측:
    #    발화 불가능한 case 였다). 탐침은 한쪽에만 있는 플래그를 각각 둔다.
    probe_known = known_flags_for(_probe_command)
    check("6) 허용집합이 docstring **에만** 있는 플래그를 받는다",
          "--doc-only" in probe_known, f"known={sorted(probe_known)}")
    check("6b) 허용집합이 본문 **에만** 있는 플래그를 받는다",
          "--body-only" in probe_known, f"known={sorted(probe_known)}")

    from workflow_kit.cli_commands_release import cmd_release_bump
    known = known_flags_for(cmd_release_bump)
    check("6c) 실물 커맨드: 받는 것만 받고 `--version` 은 안 받는다",
          {"--to", "--patch", "--apply", "--json"} <= known and "--version" not in known,
          f"known={sorted(known)}")

    total = len(ran)
    print()
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
