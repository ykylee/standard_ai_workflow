#!/usr/bin/env python3
"""`refresh_wiki_memory` 의 L2 파생 계약을 고정한다 (TASK-2026-08-18-main-004).

이 검사가 왜 다시 쓰였는지가 이 파일의 핵심이다. 이전 8 cases 는 **전부
dry-run 경로**만 밟았고, 실제 결함 둘은 apply 에서만 났다:

- `update_state_json` 의 `KeyError: 'memory'` — dry 는 write 직전에 반환했다.
- L2 stub `last_touched` 를 **하드코딩된 2026-06-14 로 되돌리는** 퇴행 —
  종료 코드는 `0` 이라 아무도 몰랐고, `score_wiki_maintainability` 의
  `lifecycle`(30일 신선도)만 조용히 무너졌다.

그래서 여기서 재는 것은 "dry 가 몇 줄을 반환하는가" 가 아니라 아래 넷이다:

1. **apply 가 실제로 무엇을 쓰는가** — 임시 fixture 저장소에 emit 하고 결과 파일을 읽는다.
2. **`last_touched` 가 뒤로 가지 않는다** — 원 결함을 되주입 형태로 고정한다.
3. **은퇴한 `--refresh-raw` 가 아무것도 쓰지 않는다** — 트리 스냅샷 대조.
4. **재실행이 멱등이다** — 진단 실행이 저장소를 바꾸면 안 된다.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
sys.path.insert(0, str(SOURCE_ROOT))

TOOL_MODULE = "workflow_kit.tools.refresh_wiki_memory"

FAILURES: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case}{(' — ' + detail) if detail else ''}")
        FAILURES.append(case)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _tree_digest(root: Path) -> str:
    """디렉터리 전체의 경로+내용 해시. write 0 을 증명하는 데 쓴다."""
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        h.update(str(p.relative_to(root)).encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


def _run(args: list[str], repo: Path, timeout: int = 60) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    env["STANDARD_AI_WF_REPO"] = str(repo)
    return subprocess.run(
        [sys.executable, "-m", TOOL_MODULE, *args],
        capture_output=True, text=True, timeout=timeout, env=env, cwd=str(repo),
    )


def _fixture(tmp: Path, *, stub_last_touched: str | None = "2026-06-14") -> Path:
    """L1 SSOT 4종을 갖춘 최소 저장소.

    `memory/active/` **바로 아래**에 둔다 — `path_in_active` 의 legacy fallback
    이 걸려 브랜치 이름과 무관하게 해석된다 (검사가 실행 브랜치에 흔들리지 않게).
    """
    active = tmp / "ai-workflow" / "memory" / "active"
    _write(active / "state.json", json.dumps({
        "purpose_digest": "픽스처 목적 요약",
        "source_of_truth": {"latest_backlog_path": "backlog/2026-08-18.md"},
        "session": {
            "current_focus": "픽스처 초점",
            "in_progress_items": ["TASK-X 진행 중 항목"],
            "blocked_items": [],
            "recent_done_items": ["TASK-Y 완료 항목", "TASK-Z 완료 항목"],
        },
        "backlog": {"task_count": 2},
    }, ensure_ascii=False, indent=2))
    _write(active / "session_handoff.md", (
        "# Session Handoff\n\n"
        "## 1. 현재 작업 요약\n\n"
        "- 현재 기준선: 픽스처 기준선 한 줄. 다음 세션이 이어받을 사실만 남긴다.\n\n"
        "## 2. 진행 중 작업\n\n"
        "- 현재 `in_progress` 작업:\n"
        "- TASK-X 진행 중 항목\n\n"
        "## 3. 차단 작업\n\n"
        "- 현재 `blocked` 작업:\n"
        "-\n\n"
        "## 4. 최근 완료 작업\n\n"
        "- TASK-Y 완료 항목\n"
    ))
    # 날짜 두 개 — 최신 하나만 골라야 한다.
    _write(active / "backlog" / "2026-08-01.md", "# Backlog\n\n- **TASK-OLD** 옛 항목\n  - status: done\n")
    _write(active / "backlog" / "2026-08-18.md", (
        "# Backlog Index — 2026-08-18\n\n"
        "## Tasks\n\n"
        "- **TASK-X** [generic] 진행 중 항목\n"
        "  - status: in_progress\n"
        "- **TASK-Y** [generic] 완료 항목\n"
        "  - status: done\n"
    ))
    _write(tmp / "ai-workflow" / "wiki" / "log.md", (
        "# Wiki Log\n\n"
        "## [2026-07-01] ingest | 첫 항목\n- 본문 1\n\n"
        "## [2026-08-18] ingest | 최신 항목\n- 본문 2\n"
    ))
    if stub_last_touched is not None:
        for name in ("active-state", "active-work-backlog", "active-session-handoff", "wiki-log"):
            _write(tmp / "ai-workflow" / "wiki" / "sources" / f"{name}.md", (
                "---\ntype: meta\nstatus: draft\nr9_skip: true\n"
                f"title: {name}\ncreated: 2026-06-14\n"
                f"last_touched: {stub_last_touched}\n---\n\n<needs content>\n"
            ))
    return tmp


TODAY = datetime.now().strftime("%Y-%m-%d")
STUBS = ("active-state", "active-work-backlog", "active-session-handoff", "wiki-log")


# --- 1. CLI 계약 ---------------------------------------------------------


def test_cli_requires_a_subcommand() -> None:
    """--refresh-raw / --emit-l2 둘 다 없으면 에러."""
    with tempfile.TemporaryDirectory() as td:
        proc = _run(["--dry-run"], _fixture(Path(td)))
    _record(
        "test_cli_requires_a_subcommand",
        proc.returncode != 0 and ("refresh-raw" in proc.stderr or "emit-l2" in proc.stderr),
        f"exit {proc.returncode}",
    )


def test_dry_run_reports_four_stubs_and_writes_nothing() -> None:
    """dry-run 은 4 stub 을 보고하고 **파일을 건드리지 않는다**."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        before = _tree_digest(repo)
        proc = _run(["--emit-l2", "--dry-run", "--json"], repo)
        after = _tree_digest(repo)
    problems = []
    if proc.returncode != 0:
        problems.append(f"exit {proc.returncode}: {proc.stderr[-200:]}")
    else:
        out = json.loads(proc.stdout)
        emit = out["emit_l2"]
        if emit["mode"] != "dry-run":
            problems.append(f"mode={emit['mode']}")
        if {row["stub"] for row in emit["emitted"]} != set(STUBS):
            problems.append(f"stubs={[r['stub'] for r in emit['emitted']]}")
        if emit["missing_l1"]:
            problems.append(f"missing_l1={emit['missing_l1']}")
    if before != after:
        problems.append("dry-run 이 파일을 바꿨다")
    _record("test_dry_run_reports_four_stubs_and_writes_nothing", not problems, "; ".join(problems))


# --- 2. apply 경로 (이전 검사가 한 번도 밟지 않은 자리) -------------------


def test_apply_writes_derived_bodies() -> None:
    """apply 가 4 stub 을 **실제로** 쓰고 본문이 L1 에서 나온다."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        proc = _run(["--emit-l2", "--apply", "--json"], repo)
        sources = repo / "ai-workflow" / "wiki" / "sources"
        texts = {n: (sources / f"{n}.md").read_text(encoding="utf-8") for n in STUBS}
    problems = []
    if proc.returncode != 0:
        problems.append(f"exit {proc.returncode}: {proc.stderr[-300:]}")
    for name, text in texts.items():
        body = text.split("---\n", 2)[-1]
        if "<needs content>" in text:
            problems.append(f"{name}: placeholder 잔존")
        if len(body.strip()) < 200:
            problems.append(f"{name}: 본문 {len(body.strip())}자 (200 미만)")
        if "L1 SSOT:" not in text:
            problems.append(f"{name}: L1 SSOT 참조 없음")
    # 각 stub 이 자기 L1 의 내용을 실제로 담았는가
    if "픽스처 초점" not in texts["active-state"]:
        problems.append("active-state: state.json 내용 미반영")
    if "TASK-X" not in texts["active-work-backlog"]:
        problems.append("active-work-backlog: backlog 내용 미반영")
    if "픽스처 기준선" not in texts["active-session-handoff"]:
        problems.append("active-session-handoff: handoff 내용 미반영")
    if "최신 항목" not in texts["wiki-log"]:
        problems.append("wiki-log: wiki/log.md 내용 미반영")
    _record("test_apply_writes_derived_bodies", not problems, "; ".join(problems))


def test_last_touched_moves_forward_never_back() -> None:
    """**원 결함 되주입**: emit 이 `last_touched` 를 오늘로 올린다.

    이전 구현은 하드코딩된 `2026-06-14` 를 찍었다. fixture 의 stub 은 그 날짜로
    시작하므로, 결함이 되살아나면 값이 그대로 남아 이 case 가 red 가 된다.
    """
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td), stub_last_touched="2026-06-14")
        _run(["--emit-l2", "--apply"], repo)
        sources = repo / "ai-workflow" / "wiki" / "sources"
        touched = {}
        for name in STUBS:
            for line in (sources / f"{name}.md").read_text(encoding="utf-8").splitlines():
                if line.startswith("last_touched:"):
                    touched[name] = line.split(":", 1)[1].strip()
                    break
    problems = [f"{n}={v}" for n, v in touched.items() if v != TODAY]
    if len(touched) != len(STUBS):
        problems.append(f"last_touched 없는 stub: {set(STUBS) - set(touched)}")
    _record("test_last_touched_moves_forward_never_back", not problems, "; ".join(problems))


def test_status_stays_in_schema_vocabulary() -> None:
    """`status` 는 SCHEMA §1.1 어휘(active|draft|deprecated) 안에 있어야 한다.

    이전 emit 경로는 `reviewed` 를 썼는데 그 값은 SCHEMA 어디에도 없다.
    """
    allowed = {"active", "draft", "deprecated"}
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        _run(["--emit-l2", "--apply"], repo)
        sources = repo / "ai-workflow" / "wiki" / "sources"
        found = {}
        for name in STUBS:
            for line in (sources / f"{name}.md").read_text(encoding="utf-8").splitlines():
                if line.startswith("status:"):
                    found[name] = line.split(":", 1)[1].strip()
                    break
    problems = [f"{n}={v}" for n, v in found.items() if v not in allowed]
    _record("test_status_stays_in_schema_vocabulary", not problems, "; ".join(problems))


def test_apply_is_idempotent() -> None:
    """같은 날 두 번 돌려도 두 번째는 write 0 (`unchanged`)."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        _run(["--emit-l2", "--apply"], repo)
        after_first = _tree_digest(repo)
        proc = _run(["--emit-l2", "--apply", "--json"], repo)
        after_second = _tree_digest(repo)
    problems = []
    if after_first != after_second:
        problems.append("2회차가 파일을 바꿨다")
    if proc.returncode == 0:
        actions = {row["stub"]: row["action"] for row in json.loads(proc.stdout)["emit_l2"]["emitted"]}
        bad = {k: v for k, v in actions.items() if v != "unchanged"}
        if bad:
            problems.append(f"action={bad}")
    else:
        problems.append(f"exit {proc.returncode}")
    _record("test_apply_is_idempotent", not problems, "; ".join(problems))


def test_bootstraps_stub_when_absent() -> None:
    """L2 stub 이 아예 없으면 frontmatter 째로 만든다."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td), stub_last_touched=None)
        proc = _run(["--emit-l2", "--apply", "--json"], repo)
        sources = repo / "ai-workflow" / "wiki" / "sources"
        missing = [n for n in STUBS if not (sources / f"{n}.md").exists()]
    problems = []
    if proc.returncode != 0:
        problems.append(f"exit {proc.returncode}: {proc.stderr[-200:]}")
    if missing:
        problems.append(f"생성 안 됨: {missing}")
    else:
        actions = {row["stub"]: row["action"] for row in json.loads(proc.stdout)["emit_l2"]["emitted"]}
        if set(actions.values()) != {"created"}:
            problems.append(f"action={actions}")
    _record("test_bootstraps_stub_when_absent", not problems, "; ".join(problems))


# --- 3. 없는 것을 있는 것처럼 채우지 않는다 ------------------------------


def test_missing_l1_is_reported_not_fabricated() -> None:
    """L1 이 없는 stub 은 건너뛰고 `missing_l1` 로 밝힌다."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        (repo / "ai-workflow" / "wiki" / "log.md").unlink()
        proc = _run(["--emit-l2", "--apply", "--json"], repo)
    problems = []
    if proc.returncode != 0:
        problems.append(f"exit {proc.returncode}: {proc.stderr[-200:]}")
    else:
        emit = json.loads(proc.stdout)["emit_l2"]
        if emit["missing_l1"] != ["wiki-log"]:
            problems.append(f"missing_l1={emit['missing_l1']}")
        if any(row["stub"] == "wiki-log" for row in emit["emitted"]):
            problems.append("L1 없는 stub 을 emit 했다")
    _record("test_missing_l1_is_reported_not_fabricated", not problems, "; ".join(problems))


def test_latest_backlog_is_picked() -> None:
    """일자별 index 가 여럿이면 **최신** 하나만 L1 으로 삼는다."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        proc = _run(["--emit-l2", "--apply", "--json"], repo)
        text = (repo / "ai-workflow" / "wiki" / "sources" / "active-work-backlog.md").read_text(encoding="utf-8")
    problems = []
    if proc.returncode != 0:
        problems.append(f"exit {proc.returncode}")
    if "2026-08-01" in text or "TASK-OLD" in text:
        problems.append("옛 backlog 를 골랐다")
    if "2026-08-18" not in text:
        problems.append("최신 backlog 참조 없음")
    _record("test_latest_backlog_is_picked", not problems, "; ".join(problems))


# --- 4. 은퇴한 단계 -------------------------------------------------------


def test_retired_refresh_raw_writes_nothing() -> None:
    """`--refresh-raw` 는 **아무것도 쓰지 않고** 사유를 말한다.

    이 단계가 쓰려던 `state.json` 은 정본 §11.2 의 생성 산출물이고 생성기는
    `wk refresh-state` 하나다 — 두 번째 writer 를 두지 않는 것이 계약이다.
    """
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        before = _tree_digest(repo)
        proc = _run(["--refresh-raw", "--apply", "--json"], repo)
        after = _tree_digest(repo)
    problems = []
    if proc.returncode != 0:
        problems.append(f"exit {proc.returncode}")
    else:
        raw = json.loads(proc.stdout)["refresh_raw"]
        if raw["mode"] != "retired" or raw["writes"] != 0:
            problems.append(f"raw={raw}")
    if before != after:
        problems.append("은퇴 단계가 파일을 바꿨다")
    if "RETIRED" not in proc.stderr:
        problems.append("사유를 stderr 로 말하지 않는다")
    _record("test_retired_refresh_raw_writes_nothing", not problems, "; ".join(problems))


def test_no_second_writer_to_state_json() -> None:
    """모듈에 `state.json` 을 **쓰는** 경로가 남아 있지 않다 (정적 확인).

    은퇴를 CLI 분기로만 막으면 다음 사람이 함수를 다시 부른다. 파일 안에
    write 대상이 없다는 것까지 고정한다.
    """
    src = (SOURCE_ROOT / "workflow_kit" / "tools" / "refresh_wiki_memory.py").read_text(encoding="utf-8")
    banned = ["atomic_write_json", "update_state_json", "update_work_backlog", "update_memory_log"]
    present = [b for b in banned if b in src]
    _record("test_no_second_writer_to_state_json", not present, f"잔존: {present}")


def main() -> int:
    test_cli_requires_a_subcommand()
    test_dry_run_reports_four_stubs_and_writes_nothing()
    test_apply_writes_derived_bodies()
    test_last_touched_moves_forward_never_back()
    test_status_stays_in_schema_vocabulary()
    test_apply_is_idempotent()
    test_bootstraps_stub_when_absent()
    test_missing_l1_is_reported_not_fabricated()
    test_latest_backlog_is_picked()
    test_retired_refresh_raw_writes_nothing()
    test_no_second_writer_to_state_json()
    total = 11
    if FAILURES:
        # 실패 요약 형식도 runner 의 파서(`run_all_checks.parse_output`)가 읽는 것으로.
        print(f"\n{len(FAILURES)}/{total} tests failed: {FAILURES}")
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    print(f"\nAll {total} tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
