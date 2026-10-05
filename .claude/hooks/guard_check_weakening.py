#!/usr/bin/env python3
"""PreToolUse 가드 — 검사를 약하게 만드는 도구 호출을 이유와 함께 막는다.

TASK-2026-10-05-main-004 (AI-native SDLC 플레이북 Stage 4 "hook 으로 검사가 약해지는 것을
막는다", `docs/planning/ai-native-sdlc-playbook-review-2026-10.md` §4.A3). 이전에는 CLAUDE.md
산문 규칙뿐이었다 — 규칙은 권고이고, 늘 성립해야 하는 정책은 결정적 장치가 받쳐야 한다.

막는 것 (정상 경로는 막지 않는다):

1. ``git push --no-verify`` — pre-push 게이트(HEAD sha 의 통과 기록)를 건너뛴다.
2. ``run_all_checks.py … --no-lock`` — 워킹 트리 배타 락 없이 전량을 돌린다. 두 에이전트의
   전량이 같은 트리에서 섞인다 (CLAUDE.md: worktree 를 나눈다).
3. 게이트 근거 ``gate_evidence/`` 에 **쓰기** — 근거는 ``run_all_checks.py --branch-context=all``
   이 깨끗한 트리에서만 남긴다. 읽기(cat · ls · json.load)는 막지 않는다.

Claude Code hook 계약: stdin 으로 ``{"tool_name", "tool_input"}`` JSON 을 받고, exit 2 + stderr 면
도구 호출이 막히고 stderr 가 모델에게 간다. 그 밖의 exit 는 통과다 — 입력을 못 읽으면 통과시킨다
(가드가 고장 나서 모든 작업을 막는 것보다 낫다. 대신 검사 `check_guard_check_weakening` 이
가드가 살아 있는지를 잰다).

정말 필요하면 사람이 프롬프트에서 ``!`` 로 직접 실행한다 — 사람의 명령은 이 hook 을 거치지 않는다.
"""
from __future__ import annotations

import json
import re
import shlex
import sys

_EVIDENCE = "gate_evidence"
#: 명령 경계 토큰 — 이 사이를 한 명령으로 본다.
_SEPARATORS = {";", "&&", "||", "|", "&", ";;"}
#: gate_evidence 를 **쓰는** 명령 단어. 읽기 도구(cat · ls · head · jq)는 없다.
_WRITE_COMMANDS = {"tee", "cp", "mv", "rm", "touch", "ln", "install", "dd", "truncate"}
#: 한 토큰(예: `python -c "…"` 의 코드) 안에서 쓰기를 뜻하는 표기.
_WRITE_IN_CODE = re.compile(r"write_text|write_bytes|open\([^)]*['\"][wax]")
_FILE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

GATE_HINT = (
    "게이트 근거는 커밋 후 깨끗한 트리에서 "
    "`.venv/bin/python3 workflow-source/tests/run_all_checks.py --branch-context=all --tmp-dir=<실디스크경로>` "
    "가 남긴다 (CLAUDE.md · docs/LOCAL_GATE.md)."
)


def _segments(command: str) -> list[list[str]]:
    """셸 명령을 **토큰** 단위의 명령 묶음으로 나눈다.

    정규식으로 문자열을 훑으면 따옴표 안의 글(커밋 메시지 · task 기록 문장)까지 명령으로
    오인한다 — 2026-10-05 실측 오탐: task 기록에 적은 "…--no-verify --dry-run 이 막혔다" 에
    반응해 기록 명령을 막았다. shlex 는 따옴표 안을 한 토큰으로 묶으므로, 플래그가 **독립
    토큰**일 때만 명령으로 본다. 줄바꿈은 명령 경계다.
    """
    segments: list[list[str]] = []
    for line in command.splitlines() or [""]:
        lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        current: list[str] = []
        for token in lexer:
            if token in _SEPARATORS:
                segments.append(current)
                current = []
            else:
                current.append(token)
        segments.append(current)
    return [seg for seg in segments if seg]


def _basename(token: str) -> str:
    return token.replace("\\", "/").rsplit("/", 1)[-1]


def _bash_verdict(command: str) -> str | None:
    try:
        segments = _segments(command)
    except ValueError:
        # 따옴표가 안 닫힌 명령 — 셸도 그 명령을 못 돌리므로 통과시킨다.
        return None
    for tokens in segments:
        names = [_basename(t) for t in tokens]
        if "git" in names and "push" in names[names.index("git"):] and "--no-verify" in tokens:
            return ("`git push --no-verify` 는 pre-push 게이트(HEAD sha 의 통과 기록)를 건너뛴다 — "
                    "근거 없는 커밋이 원격에 간다. " + GATE_HINT)
        if any(n in ("run_all_checks.py", "run_all_checks") for n in names) and "--no-lock" in tokens:
            return ("`run_all_checks.py --no-lock` 는 워킹 트리 배타 락을 끈다 — 다른 에이전트의 전량과 "
                    "같은 트리에서 섞인다. 동시에 돌려야 하면 worktree 를 나눈다 (CLAUDE.md).")
        if any(_EVIDENCE in t for t in tokens):
            redirect = any(t in (">", ">>", ">|") for t in tokens)
            writer = bool(set(names) & _WRITE_COMMANDS) or ("sed" in names and "-i" in tokens)
            code_write = any(_EVIDENCE in t and _WRITE_IN_CODE.search(t) for t in tokens)
            if redirect or writer or code_write:
                return ("`gate_evidence/` 에 직접 쓰지 않는다 — 통과 기록을 손으로 만들면 게이트가 근거 없이 "
                        "열린다. " + GATE_HINT)
    return None


def verdict(tool_name: str, tool_input: dict) -> str | None:
    """막아야 하면 그 이유(모델에게 보일 문장), 아니면 None."""
    if tool_name == "Bash":
        return _bash_verdict(str(tool_input.get("command") or ""))
    if tool_name in _FILE_TOOLS:
        path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        if f"{_EVIDENCE}/" in path.replace("\\", "/") or path.replace("\\", "/").endswith(_EVIDENCE):
            return "`gate_evidence/` 파일을 편집하지 않는다 — " + GATE_HINT
    return None


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0
    tool_input = payload.get("tool_input")
    reason = verdict(str(payload.get("tool_name") or ""), tool_input if isinstance(tool_input, dict) else {})
    if reason is None:
        return 0
    sys.stderr.write(f"[guard_check_weakening] 차단: {reason}\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
