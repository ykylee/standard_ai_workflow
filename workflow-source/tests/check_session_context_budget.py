#!/usr/bin/env python3
"""세션 시작 컨텍스트 예산 — 측정 · refresh-state 배선 · §5 이관 도구 (8 cases, ADR-029).

정본은 `workflow_kit/common/context_budget.py`, 계약은 `core/session_context_budget_spec.md`.

5 cases:
  1) §5 를 `###` 절로 나눠 현재형/누적형을 **이름 목록**으로 가른다 — 현재형 절 아래의
     `####` 는 현재형에 딸리고, 서두는 현재형이다
  2) 목록 밖의 새 `###` 절은 누적형이다 (선언 없이는 현재형으로 남지 못한다)
  3) 기준선 줄은 §1 의 라벨 줄만 센다 — 다른 절에 같은 낱말이 있어도 세지 않는다
  4) 파일이 없으면 `measured=False` 이고 초과로도 통과로도 치지 않는다 (모름 ≠ 통과)
  5) `wk refresh-state` 가 초과한 예산만 **출구 명령과 함께** warning 으로 내고, 측정 전부를
     `context_budget` 으로 싣는다 (seed 한 임시 workspace — 저장소를 건드리지 않는다).
     같은 실행이 쓴 `state.json` 의 `memory_entries` 가 v2 포인터다 (생성기 경로 배선, 17.2)
  6) `rollover-handoff-notes` 는 **무손실**이다 (requirements R4.1) — 누적형을 아래부터 옮겨 예산
     이하로 만들고, 옮긴 절은 대상 파일에 바이트 그대로 있으며(규칙 → lessons.md, 그 밖 →
     sessions/), 현재형은 그대로, §5 서두에 포인터가 정확히 하나다
  7) 멱등 — 두 번째 실행은 아무것도 쓰지 않고, 쌓인 포인터는 하나로 접는다
  8) 대상 파일은 newest-first 로 앞에 붙고 머리말은 한 번만 있다 · 포인터 건수는 대상 파일의
     실제 절 수다

이 저장소의 예산 red 판정(살아 있는 문서)은 이관을 실행한 뒤 켠다 — 스펙 §8 의 '출구 먼저,
red 나중'. 지금 켜면 만성 red 가 된다.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "docs/PROJECT_PROFILE.md",
)

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.context_budget import (  # noqa: E402
    BUDGETS_BY_KEY,
    HANDOFF_S5_CURRENT_SECTIONS,
    baseline_lines,
    measure,
    split_s5_blocks,
)
from workflow_kit.common.state.memory_index import TELEMETRY_SKIP_ROOT_ENV  # noqa: E402

SEED_TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "seed_workspace_memory.py"
PROFILE = REPO_ROOT / "docs" / "PROJECT_PROFILE.md"
FAILURES: list[str] = []

HANDOFF = """# Session Handoff

## 1. 현재 작업 요약

- 현재 기준선: **짧은 기준선**
- 직전 기준선: **조금 긴 기준선** {long}

## 5. 다음 세션 시작 포인트

서두 한 줄.

### ▶ 지금 할 일 — 운영

#### 작업 후보 — 정본은 state.json

- 현재 기준선: 이 줄은 §5 에 있으므로 기준선이 아니다

### 82차가 남긴 규칙 (재발 방지)

- 규칙 하나

### 무엇이 끝났나 (2026-08-14)

- 기록 하나

### 새로 만든 절

- 목록에 없는 절
"""


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for p in problems:
            print(f"        - {p}")
    else:
        print(f"  PASS  {name}")


def case_1_current_vs_accumulated() -> None:
    blocks = {b.title.split(" ")[0]: b for b in split_s5_blocks(HANDOFF.format(long=""))}
    problems = []
    if not blocks.get("(서두)") or not blocks["(서두)"].current:
        problems.append("서두가 현재형이 아니다")
    now = blocks.get("▶")
    if now is None or not now.current or "#### 작업 후보" not in now.text:
        problems.append(f"현재형 절이 `####` 자식을 품지 못했다: {now}")
    for key in ("82차가", "무엇이"):
        if key not in blocks or blocks[key].current:
            problems.append(f"{key} 절이 누적형이 아니다")
    if not all(p for p in HANDOFF_S5_CURRENT_SECTIONS):
        problems.append("현재형 목록에 빈 접두가 있다 — 모든 절이 현재형이 된다")
    _record("case 1 §5 현재형/누적형 = 이름 목록", problems)


def case_2_unlisted_section_is_accumulated() -> None:
    blocks = split_s5_blocks(HANDOFF.format(long=""))
    new = [b for b in blocks if b.title.startswith("새로 만든 절")]
    _record("case 2 목록 밖의 새 절은 누적형", [] if new and not new[0].current else [f"새 절: {new}"])


def case_3_baseline_lines_only_in_s1() -> None:
    lines = baseline_lines(HANDOFF.format(long="x" * 10))
    problems = []
    if len(lines) != 2:
        problems.append(f"기준선 줄 {len(lines)}개 (기대 2 — §5 의 같은 낱말은 세지 않는다): {lines}")
    _record("case 3 기준선 줄은 §1 라벨 줄만", problems)


def case_4_missing_is_unmeasured() -> None:
    with tempfile.TemporaryDirectory() as td:
        got = measure(handoff_path=Path(td) / "no.md", state_path=Path(td) / "no.json",
                      claude_md_path=Path(td) / "NO.md")
    problems = [f"{m.budget.key}: measured={m.measured} over={m.over}" for m in got if m.measured or m.over]
    if {m.budget.key for m in got} != set(BUDGETS_BY_KEY):
        problems.append("예산 일부를 재지 않았다")
    _record("case 4 파일 부재 = 미측정 (초과도 통과도 아님)", problems)


def _run(args: list[str]) -> subprocess.CompletedProcess:
    # 좁힌 환경 — 상속된 브랜치 오버라이드 없이 임시 workspace 자신의 브랜치(비 git → main)를 잰다.
    env = {"PYTHONPATH": str(SOURCE_ROOT), "PATH": "/usr/bin:/bin:/usr/local/bin"}
    if TELEMETRY_SKIP_ROOT_ENV in os.environ:
        env[TELEMETRY_SKIP_ROOT_ENV] = os.environ[TELEMETRY_SKIP_ROOT_ENV]
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, env=env)


def case_5_refresh_state_warns_with_exit() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "docs").mkdir()
        profile = root / "docs" / "PROJECT_PROFILE.md"
        profile.write_text(PROFILE.read_text(encoding="utf-8"), encoding="utf-8")
        memory_root = root / "ai-workflow" / "memory"
        (memory_root / "active").mkdir(parents=True)
        seeded = _run([str(SEED_TOOL), "--memory-root", str(memory_root), "--branch", "main",
                       "--axis", "예산 fixture", "--task-title", "예산 fixture task",
                       "--today", "2026-09-28", "--json", "--apply"])
        if seeded.returncode != 0:
            _record("case 5 refresh-state 경고 배선", [f"seed 실패: {seeded.stderr[-300:]}"])
            return
        handoff = memory_root / "active" / "main" / "session_handoff.md"
        acc_limit = BUDGETS_BY_KEY["handoff_s5_accumulated"].limit_bytes
        text = handoff.read_text(encoding="utf-8")
        block = "\n### 90차가 남긴 규칙 (재발 방지)\n\n- " + "가" * (acc_limit // 3 + 100) + "\n"
        # §5 **안에** 넣는다 — 파일 끝에 붙이면 §6 이후라 §5 예산이 재지 않는다.
        cut = text.find("\n## 6.")
        if "## 5." not in text:
            _record("case 5 refresh-state 경고 배선", ["seed handoff 에 §5 가 없다 — fixture 전제 붕괴"])
            return
        text = text[:cut] + block + text[cut:] if cut >= 0 else text + block
        handoff.write_text(text, encoding="utf-8")
        (root / "CLAUDE.md").write_text("x" * (BUDGETS_BY_KEY["claude_md"].limit_bytes + 1), encoding="utf-8")
        # memory_index entry 하나 — 생성기가 전문이 아니라 포인터를 싣는지 본다.
        entry_dir = memory_root / "active" / "memory_index" / "entries"
        entry_dir.mkdir(parents=True)
        (entry_dir / "MEM-2026-09-28-001.json").write_text(json.dumps({
            "id": "MEM-2026-09-28-001", "schema_version": 1,
            "source_paths": ["ai-workflow/memory/active/main/sessions#x"],
            "primary_abstraction": "예산 fixture entry", "cue_anchors": ["budget"],
            "value_digest": "본문 " * 200, "owners": ["session-orchestrator"], "scope": ["project"],
            "merge_state": "active", "mentioned_in": [], "related_ids": [],
            "created_at": "2026-09-28", "updated_at": "2026-09-28",
        }, ensure_ascii=False), encoding="utf-8")
        proc = _run(["-m", "workflow_kit.tools.refresh_state", "--project-profile-path", str(profile)])
        if proc.returncode != 0:
            _record("case 5 refresh-state 경고 배선", [f"refresh-state exit {proc.returncode}: {proc.stderr[-300:]}"])
            return
        out = json.loads(proc.stdout)
        state = json.loads((memory_root / "active" / "main" / "state.json").read_text(encoding="utf-8"))
        ptrs = state.get("memory_entries", [])
        if state.get("schema_version_memory_entries") != "2" or len(ptrs) != 1 \
                or set(ptrs[0]) != {"id", "primary_abstraction", "path"} \
                or not (root / ptrs[0]["path"]).is_file():
            problems.append(f"생성기가 v2 포인터를 싣지 않았다: v={state.get('schema_version_memory_entries')} {ptrs}")
    warned = {k for k in BUDGETS_BY_KEY if any(f"] {k}:" in w for w in out.get("warnings", []))}
    if warned != {"handoff_s5_accumulated", "claude_md"}:
        problems.append(f"경고한 예산 {sorted(warned)} (기대: handoff_s5_accumulated · claude_md 만)")
    for w in out.get("warnings", []):
        for k in warned:
            if f"] {k}:" in w and BUDGETS_BY_KEY[k].exit not in w:
                problems.append(f"{k} 경고에 출구가 없다: {w[:120]}")
    listed = {c.get("key") for c in out.get("context_budget", [])}
    if listed != set(BUDGETS_BY_KEY):
        problems.append(f"context_budget 에 실린 예산 {sorted(listed)}")
    _record("case 5 refresh-state 가 초과만 출구와 함께 경고", problems)


def _notes_fixture(n_rules: int, n_notes: int, *, size: int) -> str:
    """§5 에 현재형 하나 + 누적형 규칙 n_rules · 기록 n_notes 절 (위가 최신)."""
    parts = ["# Session Handoff\n\n## 1. 현재 작업 요약\n\n- 현재 기준선: **x**\n\n",
             "## 5. 다음 세션 시작 포인트\n\n서두.\n\n",
             "### ▶ 지금 할 일 — 운영\n\n#### 작업 후보 — 정본\n\n- `TASK-X` 후보\n\n"]
    for i in range(n_rules):
        parts.append(f"### {90 - i}차가 남긴 규칙 (재발 방지)\n\n- 규칙{i} " + "가" * size + "\n\n")
    for i in range(n_notes):
        parts.append(f"### 무엇이 끝났나 (2026-08-{20 - i:02d})\n\n- 기록{i} " + "나" * size + "\n\n")
    parts.append("## 6. 남은 리스크\n\n- r\n")
    return "".join(parts)


def case_6_rollover_is_lossless() -> None:
    from workflow_kit.tools.rollover_handoff_notes import run
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp) / "session_handoff.md"
        original = _notes_fixture(4, 3, size=1000)
        h.write_text(original, encoding="utf-8")
        before = {b.title: b for b in split_s5_blocks(original)}
        res = run(h, limit=8000, apply=True, today="2026-09-28")
        after_text = h.read_text(encoding="utf-8")
        after = {b.title: b for b in split_s5_blocks(after_text)}
        lessons = (Path(tmp) / "lessons.md").read_text(encoding="utf-8") if (Path(tmp) / "lessons.md").exists() else ""
        notes_f = Path(tmp) / "sessions" / "handoff-notes_2026-09-28.md"
        notes = notes_f.read_text(encoding="utf-8") if notes_f.exists() else ""
        acc_after = sum(b.size for b in after.values() if not b.current)
        if acc_after > 8000:
            problems.append(f"옮긴 뒤 누적형 {acc_after}B > 8000")
        moved = [t for t in before if t not in after]
        if not moved or res.get("moved_count") != len(moved):
            problems.append(f"옮긴 절 {moved} / 보고 {res.get('moved_count')}")
        # 아래(오래된 것)부터 옮겼는가 — 남은 누적형 절은 전부 옮긴 절보다 위에 있었다
        order = list(before)
        kept_acc = [t for t, blk in after.items() if not blk.current]
        if moved and kept_acc and max(order.index(t) for t in kept_acc) > min(order.index(t) for t in moved):
            problems.append(f"아래부터 옮기지 않았다: 남은 {kept_acc} / 옮긴 {moved}")
        for t in moved:
            dest = lessons if t[0].isdigit() else notes
            if before[t].text.rstrip("\n") not in dest:
                problems.append(f"무손실 위반: {t!r} 가 대상 파일에 바이트 그대로 없다")
        # 현재형 절(서두 제외 — 포인터가 들어간다)은 바이트 그대로 남는다
        for t, blk in before.items():
            if not blk.current or t == "(서두)":
                continue
            if t not in after or after[t].text.rstrip("\n") != blk.text.rstrip("\n"):
                problems.append(f"현재형 {t!r} 가 바뀌었다")
        pointers = [ln for ln in after_text.splitlines() if ln.startswith("- 누적 기록은")]
        if len(pointers) != 1:
            problems.append(f"포인터 {len(pointers)}줄")
        if "## 6. 남은 리스크" not in after_text or "## 1. 현재 작업 요약" not in after_text:
            problems.append("§5 밖의 절이 손상됐다")
    _record("case 6 §5 이관은 무손실 · 아래부터 · 현재형 보존 · 포인터 하나", problems)


def case_7_idempotent_and_folds_pointers() -> None:
    from workflow_kit.tools.rollover_handoff_notes import run
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp) / "session_handoff.md"
        h.write_text(_notes_fixture(4, 3, size=1000), encoding="utf-8")
        run(h, limit=8000, apply=True, today="2026-09-28")
        snap = {p: p.read_bytes() for p in Path(tmp).rglob("*") if p.is_file()}
        second = run(h, limit=8000, apply=True, today="2026-09-28")
        if second.get("applied") or {p: p.read_bytes() for p in Path(tmp).rglob("*") if p.is_file()} != snap:
            problems.append("두 번째 실행이 무언가를 썼다")
        text = h.read_text(encoding="utf-8")
        ptr = next(ln for ln in text.splitlines() if ln.startswith("- 누적 기록은"))
        h.write_text(text.replace(ptr, ptr + "\n" + ptr), encoding="utf-8")
        run(h, limit=8000, apply=True, today="2026-09-28")
        n = sum(1 for ln in h.read_text(encoding="utf-8").splitlines() if ln.startswith("- 누적 기록은"))
        if n != 1:
            problems.append(f"쌓인 포인터를 접지 못했다: {n}줄")
    _record("case 7 멱등 · 포인터 접기", problems)


def case_8_newest_first_and_counts() -> None:
    from workflow_kit.tools.rollover_handoff_notes import run
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp) / "session_handoff.md"
        h.write_text(_notes_fixture(3, 0, size=2000), encoding="utf-8")
        run(h, limit=2500, apply=True, today="2026-09-27")
        text = h.read_text(encoding="utf-8")
        cut = text.index("### ▶ 지금 할 일")
        head, rest = text[:cut], text[cut:]
        rest = rest.replace("### ▶ 지금 할 일", "### 99차가 남긴 규칙 (재발 방지)\n\n- 새 규칙 " + "다" * 3000 + "\n\n### ▶ 지금 할 일", 1)
        h.write_text(head + rest, encoding="utf-8")
        run(h, limit=2500, apply=True, today="2026-09-28")
        lessons = (Path(tmp) / "lessons.md").read_text(encoding="utf-8")
        if lessons.count("# Lessons") != 1:
            problems.append(f"머리말이 {lessons.count('# Lessons')}번")
        if not (0 <= lessons.find("## 이관 2026-09-28") < lessons.find("## 이관 2026-09-27")):
            problems.append("newest-first 가 아니다")
        n_blocks = sum(1 for ln in lessons.splitlines() if ln.startswith("### "))
        ptr = next(ln for ln in h.read_text(encoding="utf-8").splitlines() if ln.startswith("- 누적 기록은"))
        if f"규칙 {n_blocks}절" not in ptr:
            problems.append(f"포인터 건수가 실제({n_blocks})와 다르다: {ptr}")
    _record("case 8 newest-first · 머리말 한 번 · 포인터 건수 = 실제 절 수", problems)


CASES = (
    case_1_current_vs_accumulated,
    case_2_unlisted_section_is_accumulated,
    case_3_baseline_lines_only_in_s1,
    case_4_missing_is_unmeasured,
    case_5_refresh_state_warns_with_exit,
    case_6_rollover_is_lossless,
    case_7_idempotent_and_folds_pointers,
    case_8_newest_first_and_counts,
)


def main() -> int:
    print("=== 세션 시작 컨텍스트 예산 (ADR-029) ===")
    for fn in CASES:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            FAILURES.append(fn.__name__)
            print(f"  FAIL  {fn.__name__} — 예외 {type(exc).__name__}: {exc}")
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    print(f"\n{len(CASES)}/{len(CASES)} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
