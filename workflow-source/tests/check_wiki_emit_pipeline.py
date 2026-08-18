#!/usr/bin/env python3
"""`wk wiki-emit` 파이프라인의 계약을 고정한다 (TASK-2026-08-18-main-004).

`emit_wiki_l2_body` 는 **한 번도 끝까지 실행된 적이 없었다.** v0.7.17 의
in-repo 전환 때 vault 시대 이름 셋이 남았고, 셋 다 실행 경로 위에 있었다:

- `RAW_MIRROR / <project> / "ai-workflow" / "wiki"` — 없는 경로라 `ValueError`
- `RAW_MIRROR.parts.index("raw")` — in-repo 에는 `raw` 조각이 없다
- `VAULT_ROOT` — **정의된 적 없는 이름**. 앞의 둘을 고쳐도 그 다음이 `NameError` 였다.

그리고 고쳐도 할 일이 없었다: 게이트가 `<needs content>` placeholder 하나라
**한 번 emit 된 page 는 영원히 재emit 대상이 아니었다** — L1 이 바뀌어도 파생
뷰가 따라가지 않고 `last_touched` 가 얼어붙는다.

그래서 여기서 재는 것은 "import 되는가" 가 아니라 **끝까지 실행되는가**, 그리고
**게이트가 신선도인가** 다.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
sys.path.insert(0, str(SOURCE_ROOT))

EMIT_MODULE = "workflow_kit.tools.emit_wiki_l2_body"
WRAPPER_MODULE = "workflow_kit.tools.wiki_emit"
TODAY = datetime.now().strftime("%Y-%m-%d")

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
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if ".git" in p.parts:
            continue
        h.update(str(p.relative_to(root)).encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


def _run(module: str, args: list[str], repo: Path, timeout: int = 90) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    env["STANDARD_AI_WF_REPO"] = str(repo)
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        capture_output=True, text=True, timeout=timeout, env=env, cwd=str(repo),
    )


def _fixture(tmp: Path) -> Path:
    """L1 wiki page 2장 + 운영 파일 + memory SSOT 를 갖춘 최소 저장소.

    `emit_wiki_l2_body` 의 REPO_ROOT 해석은 `git rev-parse` 뿐이라 fixture 를
    git 저장소로 만든다 — 그러지 않으면 cwd 상위의 실제 저장소를 잡을 수 있다.
    """
    subprocess.run(["git", "init", "-q"], cwd=str(tmp), capture_output=True, timeout=30)
    wiki = tmp / "ai-workflow" / "wiki"
    _write(wiki / "concepts" / "alpha.md", (
        "---\ntype: concept\nstatus: active\n---\n\n"
        "# Alpha 개념\n\n"
        "## §1 TL;DR  {#s1-tldr}\n\n"
        "| 항목 | 값 |\n|---|---|\n| 하나 | 값1 |\n| 둘 | 값2 |\n\n"
        "## §2 본문\n\n" + ("알파 본문 줄.\n" * 40)
    ))
    _write(wiki / "concepts" / "beta.md", (
        "---\ntype: concept\nstatus: active\n---\n\n"
        "# Beta 개념\n\n## §2 본문\n\n" + ("베타 본문 줄.\n" * 40)
    ))
    # 운영 파일 — page 가 아니므로 L2 대상에서 빠져야 한다.
    _write(wiki / "log.md", "# Wiki Log\n\n## [2026-08-18] ingest | 항목\n- 본문\n")
    _write(wiki / "index.md", "# Index\n")
    _write(wiki / "SCHEMA.md", "# Schema\n")
    _write(wiki / "INGEST_GUIDE.md", "# Guide\n")
    # refresh_wiki_memory 소유 stub — emit_wiki_l2_body 가 건드리면 안 된다.
    for name in ("active-state", "active-work-backlog", "active-session-handoff", "wiki-log"):
        _write(wiki / "sources" / f"{name}.md", (
            "---\ntype: meta\nstatus: draft\nr9_skip: true\n"
            f"title: {name}\ncreated: 2026-06-14\nlast_touched: 2026-06-14\n---\n\n"
            "> Generated: 2026-06-14 by `workflow_kit.tools.refresh_wiki_memory --emit-l2`\n\n본문\n"
        ))
    active = tmp / "ai-workflow" / "memory" / "active"
    _write(active / "state.json", '{"session": {"in_progress_items": [], "blocked_items": [], "recent_done_items": []}}')
    _write(active / "session_handoff.md", "# Session Handoff\n\n## 1. 현재 작업 요약\n\n- 현재 기준선: 픽스처.\n")
    _write(active / "backlog" / "2026-08-18.md", "# Backlog\n\n- **TASK-X** 항목\n  - status: done\n")
    return tmp


def _l2(repo: Path, stem: str) -> Path:
    return repo / "ai-workflow" / "wiki" / "sources" / f"{stem}.md"


# --- 1. 끝까지 실행된다 (화석 3종) ---------------------------------------


def test_emit_runs_to_completion_on_in_repo_layout() -> None:
    """in-repo 레이아웃에서 emit 이 끝까지 간다 (ValueError / NameError 없음)."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        proc = _run(EMIT_MODULE, ["--project", "x", "--bootstrap-missing", "--apply"], repo)
        made = sorted(p.stem for p in (repo / "ai-workflow" / "wiki" / "sources").glob("concepts-*.md"))
    problems = []
    if proc.returncode != 0:
        problems.append(f"exit {proc.returncode}: {proc.stderr[-300:]}")
    for fossil in ("ValueError", "NameError", "VAULT_ROOT"):
        if fossil in proc.stderr:
            problems.append(f"화석 잔존: {fossil}")
    if made != ["concepts-alpha", "concepts-beta"]:
        problems.append(f"emit 결과={made}")
    _record("test_emit_runs_to_completion_on_in_repo_layout", not problems, "; ".join(problems))


def test_emitted_body_references_l1_and_extracts_tldr() -> None:
    """파생 뷰가 L1 경로를 참조하고 anchor 달린 TL;DR 을 추출한다."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        _run(EMIT_MODULE, ["--project", "x", "--bootstrap-missing", "--apply"], repo)
        text = _l2(repo, "concepts-alpha").read_text(encoding="utf-8")
    problems = []
    if "ai-workflow/wiki/concepts/alpha.md" not in text:
        problems.append("L1 경로 참조 없음")
    if "## TL;DR" not in text:
        # 이 저장소 헤딩은 `## §1 TL;DR  {#s1-tldr}` 처럼 anchor 를 단다.
        problems.append("TL;DR 미추출 (헤딩 꼬리 anchor 미허용)")
    if "> Generated:" not in text:
        problems.append("생성물 표식 없음")
    if f"last_touched: {TODAY}" not in text:
        problems.append("last_touched 가 오늘이 아니다")
    _record("test_emitted_body_references_l1_and_extracts_tldr", not problems, "; ".join(problems))


# --- 2. 게이트가 신선도다 (한 번 쓰면 끝나던 자리) -----------------------


def test_gate_is_freshness_not_one_shot_placeholder() -> None:
    """L1 이 L2 보다 새로우면 **재emit 대상**이다.

    이전 게이트는 placeholder 하나라, 한 번 emit 된 page 는 L1 이 아무리 바뀌어도
    다시 대상이 되지 않았다.
    """
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        _run(EMIT_MODULE, ["--project", "x", "--bootstrap-missing", "--apply"], repo)
        # L2 를 과거로 되돌린 뒤 (= L1 이 더 새로움) 다시 돌린다.
        l2 = _l2(repo, "concepts-alpha")
        l2.write_text(
            l2.read_text(encoding="utf-8").replace(f"last_touched: {TODAY}", "last_touched: 2026-01-01"),
            encoding="utf-8",
        )
        proc = _run(EMIT_MODULE, ["--project", "x", "--apply"], repo)
        after = l2.read_text(encoding="utf-8")
    problems = []
    if proc.returncode != 0:
        problems.append(f"exit {proc.returncode}")
    if "[APPLIED (l1)]" not in proc.stdout or "concepts-alpha" not in proc.stdout:
        problems.append("낡은 L2 가 재emit 되지 않았다")
    if f"last_touched: {TODAY}" not in after:
        problems.append("last_touched 미갱신")
    _record("test_gate_is_freshness_not_one_shot_placeholder", not problems, "; ".join(problems))


def test_up_to_date_page_is_skipped() -> None:
    """최신 파생 뷰는 다시 쓰지 않는다 (재실행 멱등)."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        _run(EMIT_MODULE, ["--project", "x", "--bootstrap-missing", "--apply"], repo)
        before = _tree_digest(repo)
        proc = _run(EMIT_MODULE, ["--project", "x", "--apply"], repo)
        after = _tree_digest(repo)
    problems = []
    if before != after:
        problems.append("2회차가 파일을 바꿨다")
    if "최신" not in proc.stdout:
        problems.append("skip 사유를 말하지 않는다")
    _record("test_up_to_date_page_is_skipped", not problems, "; ".join(problems))


def test_manual_page_is_never_overwritten() -> None:
    """생성물 표식이 없는 page 는 사람이 쓴 것으로 보고 덮어쓰지 않는다.

    재emit 은 본문 *전체* 를 갈아끼우므로, 표식 확인이 없으면 사람의 글이 사라진다.
    """
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        handwritten = (
            "---\ntype: meta\nstatus: draft\nr9_skip: true\n"
            "title: concepts-alpha\ncreated: 2026-01-01\nlast_touched: 2026-01-01\n---\n\n"
            "# 사람이 쓴 본문\n\n이 문장은 지워지면 안 된다.\n"
        )
        _write(_l2(repo, "concepts-alpha"), handwritten)
        proc = _run(EMIT_MODULE, ["--project", "x", "--apply"], repo)
        after = _l2(repo, "concepts-alpha").read_text(encoding="utf-8")
    problems = []
    if after != handwritten:
        problems.append("사람이 쓴 본문이 덮어써졌다")
    if "manual" not in proc.stdout:
        problems.append("manual 사유를 말하지 않는다")
    _record("test_manual_page_is_never_overwritten", not problems, "; ".join(problems))


# --- 3. 소유권 / 범위 -----------------------------------------------------


def test_refresh_wiki_memory_stubs_are_not_touched() -> None:
    """L2 stub 4종은 `refresh_wiki_memory --emit-l2` 소유 — 두 tool 이 같이 쓰지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        stubs = ("active-state", "active-work-backlog", "active-session-handoff", "wiki-log")
        before = {n: _l2(repo, n).read_text(encoding="utf-8") for n in stubs}
        proc = _run(EMIT_MODULE, ["--project", "x", "--mode", "all", "--bootstrap-missing", "--apply"], repo)
        after = {n: _l2(repo, n).read_text(encoding="utf-8") for n in stubs}
    overwritten = [n for n in stubs if before[n] != after[n]]
    problems = [f"덮어씀: {overwritten}"] if overwritten else []
    unreported = [n for n in stubs if f"[skip] {n}" not in " ".join(proc.stdout.split())]
    if unreported:
        problems.append(f"소유 표기 없음: {unreported}")
    _record("test_refresh_wiki_memory_stubs_are_not_touched", not problems, "; ".join(problems))


def test_operational_files_are_not_l2_candidates() -> None:
    """`log.md` / `index.md` / `SCHEMA.md` / `INGEST_GUIDE.md` 는 page 가 아니다."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        _run(EMIT_MODULE, ["--project", "x", "--bootstrap-missing", "--apply"], repo)
        made = {p.stem for p in (repo / "ai-workflow" / "wiki" / "sources").glob("*.md")}
    leaked = made & {"log", "index", "schema", "ingest-guide"}
    _record("test_operational_files_are_not_l2_candidates", not leaked, f"누출: {sorted(leaked)}")


def test_sources_dir_is_excluded_from_l1_scan() -> None:
    """`sources/` 는 L2 자신 — 파생 뷰가 자기 자신에서 파생되지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        proc = _run(EMIT_MODULE, ["--project", "x"], repo)
        made = {p.stem for p in (repo / "ai-workflow" / "wiki" / "sources").glob("*.md")}
    leaked = {m for m in made if m.startswith("sources-")}
    problems = [f"자기 파생: {sorted(leaked)}"] if leaked else []
    if "L1 files: 6" not in proc.stdout:
        problems.append(f"L1 개수 오산: {[l for l in proc.stdout.splitlines() if l.startswith('L1 files')]}")
    _record("test_sources_dir_is_excluded_from_l1_scan", not problems, "; ".join(problems))


# --- 4. bootstrap 은 기본이 off, 켜도 껍데기를 남기지 않는다 --------------


def test_bootstrap_is_off_by_default() -> None:
    """기본 실행은 L2 를 새로 만들지 않고 갭 개수만 보고한다."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        before = _tree_digest(repo)
        proc = _run(EMIT_MODULE, ["--project", "x", "--apply"], repo)
        after = _tree_digest(repo)
    problems = []
    if before != after:
        problems.append("기본 실행이 파일을 만들었다")
    if "L2 파생 뷰 없는 L1 page: 2개" not in proc.stdout:
        problems.append("갭을 보고하지 않는다")
    _record("test_bootstrap_is_off_by_default", not problems, "; ".join(problems))


def test_bootstrap_with_limit_leaves_no_empty_shells() -> None:
    """`--limit` 이 걸려도 **본문 없는 껍데기를 남기지 않는다**.

    파일을 미리 만들고 나중에 자르면 `<needs content>` 만 든 page 가 남고,
    그 page 는 discoverability 를 오히려 끌어내린다.
    """
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        _run(EMIT_MODULE, ["--project", "x", "--bootstrap-missing", "--limit", "1", "--apply"], repo)
        made = sorted((repo / "ai-workflow" / "wiki" / "sources").glob("concepts-*.md"))
        shells = [p.name for p in made if "<needs content>" in p.read_text(encoding="utf-8")]
    problems = []
    if len(made) != 1:
        problems.append(f"생성 {len(made)}개 (limit=1)")
    if shells:
        problems.append(f"빈 껍데기: {shells}")
    _record("test_bootstrap_with_limit_leaves_no_empty_shells", not problems, "; ".join(problems))


# --- 5. wrapper ------------------------------------------------------------


def test_wrapper_runs_two_steps_and_skips_retired_one() -> None:
    """`wk wiki-emit` 기본은 2-step 이고 은퇴한 1단계를 돌리지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        proc = _run(WRAPPER_MODULE, ["--apply", "--json"], repo)
    problems = []
    if proc.returncode != 0:
        problems.append(f"exit {proc.returncode}: {proc.stderr[-300:]}")
    else:
        import json as _json
        out = _json.loads(proc.stdout)
        names = [s["name"] for s in out["steps"]]
        if names != ["2_emit_l2_dense", "3_reemit_stubs"]:
            problems.append(f"steps={names}")
        if out["skipped_steps"] != ["1_refresh_raw"]:
            problems.append(f"skipped={out['skipped_steps']}")
        for s in out["steps"]:
            if s["returncode"] != 0:
                problems.append(f"{s['name']} exit {s['returncode']}: {s['stderr_tail']}")
    _record("test_wrapper_runs_two_steps_and_skips_retired_one", not problems, "; ".join(problems))


def main() -> int:
    test_emit_runs_to_completion_on_in_repo_layout()
    test_emitted_body_references_l1_and_extracts_tldr()
    test_gate_is_freshness_not_one_shot_placeholder()
    test_up_to_date_page_is_skipped()
    test_manual_page_is_never_overwritten()
    test_refresh_wiki_memory_stubs_are_not_touched()
    test_operational_files_are_not_l2_candidates()
    test_sources_dir_is_excluded_from_l1_scan()
    test_bootstrap_is_off_by_default()
    test_bootstrap_with_limit_leaves_no_empty_shells()
    test_wrapper_runs_two_steps_and_skips_retired_one()
    total = 11
    if FAILURES:
        # 실패 요약 형식도 runner 의 파서(`run_all_checks.parse_output`)가 읽는 것으로.
        print(f"\n{len(FAILURES)}/{total} tests failed: {FAILURES}")
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    print(f"\nAll {total} tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
