#!/usr/bin/env python3
"""verifier subagent — 쓰기 도구 없이, 미측정을 통과로 세지 않고 보고만 한다 (TASK-2026-10-05-main-003).

AI-native SDLC 플레이북의 verifier subagent 대응
(`docs/planning/ai-native-sdlc-playbook-review-2026-10.md` §4.A2). task 를 `done` 으로 닫는
판정자가 그 task 를 작성한 세션 자신이던 것을, 새 컨텍스트의 읽기 전용 검증자로 나눈다.
정의는 저장소 루트 `.claude/agents/verifier.md`.

1. frontmatter — name · description · tools 가 있고, tools 는 읽기 계열만이다 (쓰기 도구 0)
2. 금지 — 상태를 바꾸는 명령(commit · push · `--apply` · refresh-state)과 파일 수정을 금지한다고 적혀 있다
3. 판정 어휘 — PASS / FAIL / UNMEASURED, "미측정은 통과가 아니다", 전부 PASS 일 때만 닫는다
4. 호출 지점 — CLAUDE.md 가 done 전에 verifier 를 부르라고 지시한다
"""
from __future__ import annotations

WATCHES = (
    ".claude/*",
    "CLAUDE.md",
)

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT = REPO_ROOT / ".claude" / "agents" / "verifier.md"

#: 검증자에게 허용하는 도구. Bash 는 검사를 돌리려면 필요하다 — 상태 변경 금지는 본문 규칙이 맡는다.
READ_ONLY_TOOLS = frozenset({"Bash", "Read", "Grep", "Glob"})
WRITE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail else ''}")


def _split(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    head, _, body = text[4:].partition("\n---\n")
    meta: dict[str, str] = {}
    for line in head.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip()
    return meta, body


def _load() -> tuple[dict[str, str], str]:
    return _split(AGENT.read_text(encoding="utf-8")) if AGENT.is_file() else ({}, "")


def case_1_frontmatter_is_read_only() -> None:
    meta, _ = _load()
    tools = {t.strip() for t in meta.get("tools", "").split(",") if t.strip()}
    problems = []
    if meta.get("name") != "verifier":
        problems.append(f"name={meta.get('name')!r}")
    if "done" not in meta.get("description", ""):
        problems.append("description 이 언제 부르는지(done 전)를 말하지 않는다")
    if not tools:
        problems.append("tools 선언이 없다 — 생략하면 모든 도구를 상속한다")
    if tools & WRITE_TOOLS:
        problems.append(f"쓰기 도구: {sorted(tools & WRITE_TOOLS)}")
    if tools - READ_ONLY_TOOLS:
        problems.append(f"허용 밖 도구: {sorted(tools - READ_ONLY_TOOLS)}")
    _record("case 1 (frontmatter — tools 는 읽기 계열만)", not problems, "; ".join(problems))


def case_2_forbids_state_changes() -> None:
    _, body = _load()
    section = body.split("## 절대 하지 않는 것", 1)[1].split("\n## ", 1)[0] if "## 절대 하지 않는 것" in body else ""
    needed = ("고치지 않는다", "git commit", "git push", "--apply", "refresh-state")
    missing = [n for n in needed if n not in section]
    _record("case 2 (금지 절이 파일 수정과 상태 변경 명령을 금지한다)", bool(section) and not missing,
            f"누락: {missing}" if section else "'절대 하지 않는 것' 절이 없다")


def case_3_unmeasured_is_not_pass() -> None:
    _, body = _load()
    needed = ("PASS", "FAIL", "UNMEASURED", "미측정은 통과가 아니다", "모든 기준이 PASS")
    missing = [n for n in needed if n not in body]
    _record("case 3 (판정 어휘 — 미측정은 통과가 아니고, 전부 PASS 일 때만 닫는다)", not missing,
            f"누락: {missing}")


def case_4_entrypoint_calls_verifier_before_done() -> None:
    text = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if "verifier" in line]
    ok = any(".claude/agents/verifier.md" in line and "done" in line for line in lines)
    _record("case 4 (CLAUDE.md 가 done 전에 verifier 를 부르라고 지시한다)", ok, f"관련 줄: {lines[:2]}")


def main() -> int:
    print("=== verifier subagent (TASK-2026-10-05-main-003) ===")
    for fn in (case_1_frontmatter_is_read_only,
               case_2_forbids_state_changes,
               case_3_unmeasured_is_not_pass,
               case_4_entrypoint_calls_verifier_before_done):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            _record(fn.__name__, False, f"{type(exc).__name__}: {exc}")
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
