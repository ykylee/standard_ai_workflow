#!/usr/bin/env python3
"""검사 약화 차단 가드 hook — 막을 것은 막고, 정상 경로는 통과시킨다 (TASK-2026-10-05-main-004).

AI-native SDLC 플레이북 Stage 4 "hook 으로 검사가 약해지는 것을 막는다" 대응
(`docs/planning/ai-native-sdlc-playbook-review-2026-10.md` §4.A3). 가드는 저장소 루트
`.claude/hooks/guard_check_weakening.py`, 등록은 `.claude/settings.json` 이다.

1. 차단 — `git push --no-verify` · `run_all_checks --no-lock` · `gate_evidence/` 쓰기 (exit 2 + 이유)
2. 통과 — 일반 push · dry-run push · `--changed` · gate_evidence **읽기** · 일반 파일 편집
3. 파일 도구 — Write/Edit 의 gate_evidence 경로 차단 (Windows 역슬래시 포함)
4. 입력을 못 읽으면 통과 (가드 고장이 모든 작업을 막지 않는다)
5. 등록 — settings.json 의 hook 명령을 **그대로** 셸로 돌려 차단이 일어난다 (설정 · 경로 · 해석기 탐침까지)
"""
from __future__ import annotations

WATCHES = (
    ".claude/*",
)

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD = REPO_ROOT / ".claude" / "hooks" / "guard_check_weakening.py"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail else ''}")


def _run(payload: object | str) -> subprocess.CompletedProcess[str]:
    stdin = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return subprocess.run([sys.executable, str(GUARD)], input=stdin, capture_output=True,
                          encoding="utf-8", errors="replace", timeout=30, check=False)


def _bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


BLOCKED = (
    "git push --no-verify origin main",
    "git -C /repo push origin main --no-verify",
    "cd /repo && git push --no-verify",
    ".venv/bin/python3 workflow-source/tests/run_all_checks.py --no-lock --tmp-dir=/x",
    "python3 run_all_checks.py --branch-context=all --no-lock",
    "echo '{}' > .git/gate_evidence/abc.json",
    "cp /tmp/x.json .git/gate_evidence/abc.json",
    "python3 -c \"import pathlib; pathlib.Path('.git/gate_evidence/a.json').write_text('{}')\"",
    "git status\ngit push --no-verify",
    "/usr/bin/git push origin main --no-verify",
)
ALLOWED = (
    "git push origin main",
    "git push -n origin main",
    "git status && git log --oneline -3",
    ".venv/bin/python3 workflow-source/tests/run_all_checks.py --changed --tmp-dir=/x",
    "ls .git/gate_evidence/ | tail -1",
    "cat .git/gate_evidence/abc.json",
    "python3 -c \"import json; print(json.load(open('.git/gate_evidence/a.json')))\"",
    "grep -n no-verify CLAUDE.md",
    # 따옴표 안의 언급은 명령이 아니다 — 2026-10-05 실측 오탐 (task 기록 문장에 반응해 막았다)
    "python3 -m workflow_kit backlog-update --validation-result \"git push --no-verify --dry-run 이 막혔다\"",
    "git commit -m 'docs: run_all_checks.py --no-lock 금지 설명'",
    "echo \"gate_evidence 는 > 로 쓰지 않는다\"",
)


def case_1_blocks_weakening_commands() -> None:
    missed = []
    for command in BLOCKED:
        proc = _run(_bash(command))
        if proc.returncode != 2 or "차단" not in proc.stderr:
            missed.append(f"{command!r} rc={proc.returncode}")
    _record(f"case 1 (검사 약화 명령 {len(BLOCKED)}종을 이유와 함께 막는다)", not missed, f"놓침: {missed}")


def case_2_allows_normal_commands() -> None:
    wrongly = []
    for command in ALLOWED:
        proc = _run(_bash(command))
        if proc.returncode != 0:
            wrongly.append(f"{command!r} rc={proc.returncode} {proc.stderr[:80]!r}")
    for payload in ({"tool_name": "Write", "tool_input": {"file_path": "/repo/docs/x.md"}},
                    {"tool_name": "Read", "tool_input": {"file_path": "/repo/.git/gate_evidence/a.json"}}):
        proc = _run(payload)
        if proc.returncode != 0:
            wrongly.append(f"{payload['tool_name']} rc={proc.returncode}")
    _record(f"case 2 (정상 명령 {len(ALLOWED)}종 · 일반 편집 · gate_evidence 읽기는 통과)", not wrongly,
            f"오차단: {wrongly}")


def case_3_file_tools_on_evidence_are_blocked() -> None:
    missed = []
    for tool, path in (("Write", "/repo/.git/gate_evidence/abc.json"),
                       ("Edit", "C:\\repo\\.git\\gate_evidence\\abc.json"),
                       ("MultiEdit", "/repo/.git/gate_evidence/x.json")):
        proc = _run({"tool_name": tool, "tool_input": {"file_path": path}})
        if proc.returncode != 2:
            missed.append(f"{tool} {path} rc={proc.returncode}")
    _record("case 3 (파일 도구의 gate_evidence 편집을 막는다 — 역슬래시 경로 포함)", not missed, f"놓침: {missed}")


def case_4_unreadable_input_passes() -> None:
    results = {label: _run(raw).returncode
               for label, raw in (("not-json", "not json"), ("empty", ""), ("list", "[1,2]"),
                                  ("no-input", json.dumps({"tool_name": "Bash"})))}
    _record("case 4 (입력을 못 읽으면 통과 — 가드 고장이 작업 전체를 막지 않는다)",
            all(rc == 0 for rc in results.values()), f"{results}")


def case_5_settings_registration_runs_end_to_end() -> None:
    try:
        settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
        groups = settings["hooks"]["PreToolUse"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        _record("case 5 (settings.json 등록 → 실제 hook 명령이 차단한다)", False, f"설정을 못 읽었다: {exc}")
        return
    entries = [(g.get("matcher", ""), h.get("command", "")) for g in groups for h in g.get("hooks", [])]
    hits = [(m, c) for m, c in entries if "guard_check_weakening.py" in c]
    problems: list[str] = []
    if not hits:
        problems.append("PreToolUse 에 가드가 등록되지 않았다")
    else:
        matcher, command = hits[0]
        tools = set(matcher.split("|"))
        if not {"Bash", "Write", "Edit"} <= tools:
            problems.append(f"matcher 가 좁다: {matcher!r}")
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(REPO_ROOT)
        for payload, want in ((_bash("git push --no-verify"), 2), (_bash("git push origin main"), 0)):
            proc = subprocess.run(["bash", "-c", command], input=json.dumps(payload), capture_output=True,
                                  encoding="utf-8", errors="replace", env=env, timeout=30, check=False)
            if proc.returncode != want:
                problems.append(f"{payload['tool_input']['command']!r}: rc={proc.returncode} (기대 {want}) "
                                f"{proc.stderr[:120]!r}")
    _record("case 5 (settings.json 등록 → 실제 hook 명령이 차단한다)", not problems, "; ".join(problems))


def main() -> int:
    print("=== 검사 약화 차단 가드 hook (TASK-2026-10-05-main-004) ===")
    for fn in (case_1_blocks_weakening_commands,
               case_2_allows_normal_commands,
               case_3_file_tools_on_evidence_are_blocked,
               case_4_unreadable_input_passes,
               case_5_settings_registration_runs_end_to_end):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            _record(fn.__name__, False, f"{type(exc).__name__}: {str(exc)[:300]}")
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
