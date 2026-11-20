#!/usr/bin/env python3
"""읽기 전용 소비자 클론에서 session-start 는 저장소에 쓰지 않는다 (6 cases).

## 왜 (TASK-2026-11-20-claude-consumer-readonly-session-start-002)

이 저장소의 클론은 개발 참여자와 읽기 전용 소비자로 갈린다 (`docs/HOST_ROLES.md`, 클론별
`git config --local workflow.role`). 소비자는 pull · 환경 맞추기 · 버전 업데이트만 하는데,
하네스나 에이전트가 세션을 열며 `session-start` 를 부르면 브랜치 메모리 seed · 기본 브랜치의
합류 반영(아카이브) · 부재 진입점 생성 · telemetry 가 트리를 바꿨다 — 커밋할 일이 없는 클론에
커밋할 거리가 생긴다. 소유자 결정(2026-11-20): 소비자 클론이면 session-start 가 쓰지 않는다.

판정은 **파일 목록이 아니라 작업 트리 전체**(무시 파일 포함, `.git` 제외)의 실행 전후 스냅샷이다 —
아는 쓰기 경로만 막고 모르는 경로를 놓치지 않으려는 것이다. 각 fixture 가 실제로 쓰기 경로를
지나는지는 같은 fixture 를 역할 없이 돌린 대조군이 보인다 (대조군이 안 쓰면 그 case 는 아무것도 재지 않는다).

  1) 새 브랜치(seed 대상) + memory_index(telemetry 대상) — consumer 는 트리 불변 · 읽기 전용 안내 · seed 없음,
     대조군(미선언)은 seed 하고 트리가 바뀐다
  1b) 기본 브랜치 정상 경로 + memory_index(telemetry 대상) — consumer 는 트리 불변 · status ok,
     대조군(미선언)은 telemetry 를 쓴다
  2) 기본 브랜치에 병합된 worktree 메모리(합류 반영 대상) — consumer 는 트리 불변 · 합류 warning 없음,
     대조군(contributor)은 반영하고 트리가 바뀐다
  2b) bootstrap 된 프로젝트에서 진입점 하나가 빠졌다(진입점 생성 대상) — consumer 는 트리 불변 · 부재를 보고,
     대조군(미선언)은 그 파일을 만든다
  3) 역할 값은 대소문자를 가리지 않는다(`Consumer`) · 전역 설정(`--global`)의 consumer 는 무시한다
  4) 판정 정본이 하나다 — gate_evidence 와 session_start 가 `host_role.is_consumer` 를 쓴다
"""

from __future__ import annotations

#: 임시 저장소를 여러 벌 만들어 session-start 를 8번 띄운다 — 병렬 부하에서 기본 60s 상한을 넘을 수 있다.
CHECK_TIMEOUT_S = 180

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/check_branch_join_reflect.py",
    "workflow-source/tests/check_branch_memory_auto_seed.py",
    "workflow-source/tests/check_ensure_entrypoints.py",
    "workflow-source/tests/check_memory_lint.py",  # auto-seed fixture 가 import 한다
)

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE_ROOT = HERE.parent
sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(HERE))

import check_branch_join_reflect as join  # noqa: E402
import check_branch_memory_auto_seed as seedfx  # noqa: E402
import check_ensure_entrypoints as entryfx  # noqa: E402
from workflow_kit.common import gate_evidence, host_role  # noqa: E402
from workflow_kit.tools import session_start, workbench  # noqa: E402

READ_ONLY_MARK = "읽기 전용 소비자 클론"
FAILURES: list[str] = []


def _record(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + ("" if ok else f" — {detail}"))
    if not ok:
        FAILURES.append(name)


def _tree(root: Path) -> dict[str, bytes]:
    """작업 트리 전체(무시 파일 포함) — `.git` 만 뺀다 (git 명령이 index 의 stat 캐시를 갱신할 수 있다)."""
    out: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] == ".git":
            continue
        if path.is_file():
            out[rel.as_posix()] = path.read_bytes()
    return out


def _diff(before: dict[str, bytes], after: dict[str, bytes]) -> list[str]:
    changed = sorted(k for k in before.keys() & after.keys() if before[k] != after[k])
    return ([f"+{k}" for k in sorted(after.keys() - before.keys())]
            + [f"-{k}" for k in sorted(before.keys() - after.keys())] + [f"~{k}" for k in changed])


def _stop_workbench(workspace: Path) -> None:
    """자동 기동이 서버를 남겼으면 내린다 — 검사가 호스트에 프로세스를 남기지 않게."""
    profile = workspace / "docs" / "PROJECT_PROFILE.md"
    subprocess.run([sys.executable, "-m", "workflow_kit", "workbench", "--project-profile-path", str(profile), "--stop"],
                   cwd=str(workspace), capture_output=True, text=True, env=seedfx._env(), timeout=60,
                   encoding="utf-8", errors="replace")


def _seed_fixture(tmp: Path) -> Path:
    clone = seedfx._make_repo(tmp)
    seedfx._git(clone, "switch", "-q", "-c", "claude/consumer-probe")
    (clone / "ai-workflow" / "memory" / "active" / "memory_index").mkdir(parents=True)
    return clone


def _join_fixture(tmp: Path) -> Path:
    clone, wt = join._make(tmp)
    join._work_in_worktree(wt)
    join._git(clone, "merge", "-q", "--ff-only", "claude/w")
    return clone


def case_seed() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="consumer-ro-1-") as raw:
        clone = _seed_fixture(Path(raw) / "consumer")
        seedfx._git(clone, "config", "--local", "workflow.role", "consumer")
        before = _tree(clone)
        result = seedfx._session_start(clone)
        changed = _diff(before, _tree(clone))
        if changed:
            problems.append(f"consumer 가 트리를 바꿨다: {changed[:8]}")
        if seedfx._seeded(result):
            problems.append("consumer 가 seed 했다고 보고한다")
        notes = " ".join(result.get("warnings", []))
        if READ_ONLY_MARK not in notes or "HOST_ROLES.md" not in notes:
            problems.append(f"오류 경로 warnings 에 읽기 전용 안내가 없다: {result.get('status')} {notes[:200]!r}")
        # 복구 안내도 쓰기 명령(ensure-entrypoints --apply · seed-workspace-memory)을 권하지 않는다
        if result.get("recovery_hint") != session_start.READ_ONLY_HINT:
            problems.append(f"오류 경로 recovery_hint 가 소비자용이 아니다: {str(result.get('recovery_hint'))[:120]!r}")

        control = _seed_fixture(Path(raw) / "control")
        before = _tree(control)
        result = seedfx._session_start(control)
        if not seedfx._seeded(result) or not _diff(before, _tree(control)):
            problems.append(f"대조군(미선언)이 seed 하지 않았다 — fixture 가 쓰기 경로를 안 지난다: {result.get('status')}")
    _record("case_1_seed_branch_is_untouched", not problems, "; ".join(problems))


def case_telemetry() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="consumer-ro-1b-") as raw:
        def fixture(name: str) -> Path:
            clone = seedfx._make_repo(Path(raw) / name)
            (clone / "ai-workflow" / "memory" / "active" / "memory_index").mkdir(parents=True)
            # 워크벤치 자동 기동 설정 — 토큰 · 개방 모드가 없어 서버는 떠도 곧 실패한다(남는 프로세스 없음).
            # 검사 표식(CHECK_MARK_ENV)은 이 fixture 를 가리키지 않으므로 억제되지 않는다.
            record = workbench.record_dir(clone)
            record.mkdir()
            (record / workbench.AUTOSTART_FILENAME).write_text(
                json.dumps({"argv": ["--bind", "127.0.0.1", "--port", "0"]}), encoding="utf-8")
            return clone

        clone = fixture("consumer")
        seedfx._git(clone, "config", "--local", "workflow.role", "consumer")
        before = _tree(clone)
        result = seedfx._session_start(clone, env={workbench.AUTOSTART_OFF_ENV: ""})
        changed = _diff(before, _tree(clone))
        _stop_workbench(clone)
        if result.get("status") != "ok":
            problems.append(f"consumer 정상 경로가 ok 가 아니다: {result.get('status')} {str(result)[:200]}")
        if changed:
            problems.append(f"consumer 가 트리를 바꿨다: {changed[:8]}")
        control = fixture("control")
        before = _tree(control)
        seedfx._session_start(control, env={workbench.AUTOSTART_OFF_ENV: ""})
        control_changed = _diff(before, _tree(control))
        _stop_workbench(control)
        if not any("telemetry" in k for k in control_changed):
            problems.append("대조군(미선언)이 telemetry 를 쓰지 않았다 — fixture 가 telemetry 경로를 안 지난다")
        if not any(workbench.RECORD_DIRNAME in k and workbench.AUTOSTART_FILENAME not in k for k in control_changed):
            problems.append(f"대조군(미선언)이 워크벤치 자동 기동을 시도하지 않았다 — fixture 가 그 경로를 안 지난다: {control_changed}")
    _record("case_1b_main_with_memory_index_is_untouched", not problems, "; ".join(problems))


def case_join() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="consumer-ro-2-") as raw:
        clone = _join_fixture(Path(raw) / "consumer")
        join._git(clone, "config", "--local", "workflow.role", "consumer")
        before = _tree(clone)
        result = join._session_start(clone)
        changed = _diff(before, _tree(clone))
        if changed:
            problems.append(f"consumer 가 트리를 바꿨다: {changed[:8]}")
        if any(join.JOIN_MARK in w for w in result.get("warnings", [])):
            problems.append("consumer 가 합류를 반영했다고 보고한다")
        if not any(READ_ONLY_MARK in w for w in result.get("warnings", [])):
            problems.append("읽기 전용 안내가 없다")
        # 명시 아카이브 요청도 소비자 클론에서는 쓰지 않는다
        join._module(clone, "workflow_kit.tools.session_start", "--archive-stale-branches")
        changed = _diff(before, _tree(clone))
        if changed:
            problems.append(f"consumer 가 --archive-stale-branches 로 트리를 바꿨다: {changed[:8]}")

        control = _join_fixture(Path(raw) / "control")
        join._git(control, "config", "--local", "workflow.role", "contributor")
        before = _tree(control)
        result = join._session_start(control)
        if not any(join.JOIN_MARK in w for w in result.get("warnings", [])) or not _diff(before, _tree(control)):
            problems.append("대조군(contributor)이 합류를 반영하지 않았다 — fixture 가 쓰기 경로를 안 지난다")
    _record("case_2_default_branch_join_is_untouched", not problems, "; ".join(problems))


def case_entrypoints() -> None:
    problems: list[str] = []
    rel = Path(".claude") / "commands" / "workflow-session-end.md"
    with tempfile.TemporaryDirectory(prefix="consumer-ro-2b-") as raw:
        def fixture(name: str, role: str | None, *, branch: str | None = None) -> tuple[Path, dict, dict[str, bytes]]:
            target = Path(raw) / name
            target.mkdir()
            subprocess.run(["git", "init", "-q", "-b", "main", str(target)], check=True, capture_output=True)
            entryfx._bootstrap(target)
            (target / rel).unlink()
            if branch:  # 브랜치 메모리가 없는 브랜치 — 기준선 복원 실패(조기) 경로에서 진입점 복구를 부른다
                # 커밋이 없는 저장소의 브랜치는 기본 브랜치로 판정된다 — bootstrap 결과를 먼저 커밋한다
                git = ["git", "-C", str(target), "-c", "user.email=t@t", "-c", "user.name=t"]
                subprocess.run([*git, "add", "-A"], check=True, capture_output=True)
                subprocess.run([*git, "commit", "-qm", "bootstrap"], check=True, capture_output=True)
                subprocess.run([*git, "switch", "-q", "-c", branch], check=True, capture_output=True)
            if role:
                subprocess.run(["git", "-C", str(target), "config", "--local", "workflow.role", role],
                               check=True, capture_output=True)
            before = _tree(target)
            proc = subprocess.run([sys.executable, "-m", "workflow_kit.workflow_kit_cli", "session-start"],
                                  cwd=str(target), capture_output=True, text=True, env=entryfx._env(),
                                  encoding="utf-8", errors="replace", timeout=120)
            try:
                payload = json.loads(proc.stdout[proc.stdout.index("{"):])
            except ValueError:
                payload = {"status": "unparsable", "warnings": [proc.stderr[-200:]]}
            return target, payload, before

        target, payload, before = fixture("consumer", "consumer")
        changed = _diff(before, _tree(target))
        if changed:
            problems.append(f"consumer 가 트리를 바꿨다: {changed[:8]}")
        if not any("만들지 않았다" in w for w in payload.get("warnings", [])):
            problems.append(f"부재 진입점을 보고하지 않았다: {payload.get('warnings')}")
        control, _, _ = fixture("control", None)
        if not (control / rel).is_file():
            problems.append("대조군(미선언)이 부재 진입점을 만들지 않았다 — fixture 가 생성 경로를 안 지난다")
        early, payload, before = fixture("early", "consumer", branch="claude/early")
        changed = _diff(before, _tree(early))
        if payload.get("status") == "ok" or changed:
            problems.append(f"조기 경로(브랜치 메모리 없음)에서 consumer 가 썼거나 기준선을 복원했다: "
                            f"{payload.get('status')} {changed[:8]}")
        early_control, _, _ = fixture("early-control", "contributor", branch="claude/early")
        if not (early_control / rel).is_file():
            problems.append("대조군(contributor, 조기 경로)이 부재 진입점을 만들지 않았다 — fixture 가 그 경로를 안 지난다")
    _record("case_2b_missing_entrypoint_is_not_created", not problems, "; ".join(problems))


def case_role_reading() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="consumer-ro-3-") as raw:
        tmp = Path(raw)
        clone = _seed_fixture(tmp / "upper")
        seedfx._git(clone, "config", "--local", "workflow.role", "Consumer")
        before = _tree(clone)
        seedfx._session_start(clone)
        if _diff(before, _tree(clone)):
            problems.append("`Consumer`(대문자) 를 소비자로 읽지 않았다")
        # 전역 설정은 무시한다 — HOME 을 임시 디렉터리로 돌려 그 안의 ~/.gitconfig 에만 consumer 를 둔다
        home = tmp / "home"
        home.mkdir()
        (home / ".gitconfig").write_text("[workflow]\n\trole = consumer\n", encoding="utf-8")
        other = _seed_fixture(tmp / "global")
        saved = os.environ.get("HOME")
        os.environ["HOME"] = str(home)
        try:
            role = host_role.host_role(other)
        finally:
            if saved is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = saved
        if role is not None:
            problems.append(f"전역 ~/.gitconfig 의 역할을 읽었다: {role!r}")
    _record("case_3_role_value_and_scope", not problems, "; ".join(problems))


def case_single_source() -> None:
    problems: list[str] = []
    if getattr(gate_evidence, "is_consumer", None) is not host_role.is_consumer:
        problems.append("gate_evidence 가 host_role.is_consumer 를 쓰지 않는다")
    if getattr(session_start, "is_consumer", None) is not host_role.is_consumer:
        problems.append("session_start 가 host_role.is_consumer 를 쓰지 않는다")
    for module in (gate_evidence, session_start):
        source = Path(module.__file__ or "").read_text(encoding="utf-8")
        if '"workflow.role"' in source or "'workflow.role'" in source:
            problems.append(f"{Path(module.__file__ or '').name} 가 역할 키를 따로 읽는다")
    _record("case_4_single_source_of_role", not problems, "; ".join(problems))


def main() -> int:
    cases = (case_seed, case_telemetry, case_join, case_entrypoints, case_role_reading, case_single_source)
    for case in cases:
        case()
    print(f"\n{len(cases) - len(FAILURES)}/{len(cases)} PASS")
    return 1 if FAILURES else 0


def test_consumer_readonly_session_start() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
