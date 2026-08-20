#!/usr/bin/env python3
"""L2 계약을 고정한다 — 정의 · 목록 · 소유 · 분모 (TASK-2026-08-20-main-001).

L2 는 2026-08-20 에 **정의가 좁아졌다**:

    L2 = wiki 모양이 *아닌* SSOT 를 wiki 검색용으로 압축한 뷰. 4종뿐이다.

L1 wiki page 파생 경로(`emit_wiki_l2_body`)는 은퇴했다 — 근거였던 외부 vault
retrieval 이 v0.7.17 in-repo 전환 때 사라졌고, in-repo 에서 L1 은 이미 검색
가능해서 사본은 드리프트 표면만 늘렸다.

계약은 **말로 적으면 지켜지지 않는다.** 이 검사가 고정하는 것 넷:

1. **은퇴한 경로가 아무것도 쓰지 않는다** — 조용한 no-op 이 아니라 사유를 말한다.
2. **은퇴한 기계가 파일에 없다** — 분기로만 막으면 다음 사람이 다시 부른다.
3. **목록이 한 곳에만 있다** — 지표가 복제하지 않고 생성기 상수를 본다.
4. **분모가 선언된 집합이다** — stub 을 지울수록 점수가 오르면 지표가 아니다.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
sys.path.insert(0, str(SOURCE_ROOT))

TOOLS = SOURCE_ROOT / "workflow_kit" / "tools"
EMIT_MODULE = "workflow_kit.tools.emit_wiki_l2_body"
WRAPPER_MODULE = "workflow_kit.tools.wiki_emit"

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
    """L1 wiki page + 운영 파일 + memory SSOT 를 갖춘 최소 저장소."""
    subprocess.run(["git", "init", "-q"], cwd=str(tmp), capture_output=True, timeout=30)
    wiki = tmp / "ai-workflow" / "wiki"
    _write(wiki / "concepts" / "alpha.md", "---\ntype: concept\n---\n\n# Alpha\n\n" + ("본문 줄.\n" * 40))
    _write(wiki / "concepts" / "beta.md", "---\ntype: concept\n---\n\n# Beta\n\n" + ("본문 줄.\n" * 40))
    _write(wiki / "log.md", "# Wiki Log\n\n## [2026-08-20] ingest | 항목\n- 본문\n")
    active = tmp / "ai-workflow" / "memory" / "active"
    _write(active / "state.json", json.dumps({
        "session": {"in_progress_items": [], "blocked_items": [], "recent_done_items": ["TASK-A 항목"]},
        "backlog": {"task_count": 1},
    }, ensure_ascii=False))
    _write(active / "session_handoff.md", "# Session Handoff\n\n## 1. 현재 작업 요약\n\n- 현재 기준선: 픽스처.\n")
    _write(active / "backlog" / "2026-08-20.md", "# Backlog\n\n- **TASK-A** 항목\n  - status: done\n")
    return tmp


# --- 1. 은퇴한 경로 -------------------------------------------------------


def test_retired_emit_writes_nothing_and_says_why() -> None:
    """`emit_wiki_l2_body` 는 write 0 이고 사유를 stderr 로 말한다 (rc=0)."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        before = _tree_digest(repo)
        proc = _run(EMIT_MODULE, ["--project", "x", "--bootstrap-missing", "--apply"], repo)
        after = _tree_digest(repo)
    problems = []
    if proc.returncode != 0:
        problems.append(f"exit {proc.returncode}: {proc.stderr[-200:]}")
    if before != after:
        problems.append("은퇴 경로가 파일을 바꿨다")
    if "RETIRED" not in proc.stderr:
        problems.append("사유를 말하지 않는다")
    _record("test_retired_emit_writes_nothing_and_says_why", not problems, "; ".join(problems))


def test_retired_emit_still_accepts_old_flags() -> None:
    """옛 인자를 계속 받는다 — argparse 오류로 죽는 대신 **사유를 듣게** 한다."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        proc = _run(EMIT_MODULE, ["--project", "x", "--mode", "all", "--max-chars", "2000",
                                  "--limit", "3", "--apply"], repo)
    _record("test_retired_emit_still_accepts_old_flags", proc.returncode == 0,
            f"exit {proc.returncode}: {proc.stderr[-200:]}")


def test_retired_machinery_is_gone_from_the_file() -> None:
    """은퇴한 기계가 **파일에 없다**. 분기로만 막으면 다음 사람이 다시 부른다."""
    src = (TOOLS / "emit_wiki_l2_body.py").read_text(encoding="utf-8")
    banned = [
        "def update_l2_full", "def build_emit_body", "def find_l1_files",
        "def needs_emit", "def path_to_stem", "RAW_MIRROR", "L2_SOURCES",
    ]
    present = [b for b in banned if b in src]
    _record("test_retired_machinery_is_gone_from_the_file", not present, f"잔존: {present}")


# --- 2. 파이프라인은 1-step ------------------------------------------------


def test_wrapper_runs_exactly_one_live_step() -> None:
    """`wk wiki-emit` 기본은 **1단계**고 은퇴한 둘을 돌리지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        proc = _run(WRAPPER_MODULE, ["--apply", "--json"], repo)
    problems = []
    if proc.returncode != 0:
        problems.append(f"exit {proc.returncode}: {proc.stderr[-300:]}")
    else:
        out = json.loads(proc.stdout)
        names = [s["name"] for s in out["steps"]]
        if names != ["3_reemit_stubs"]:
            problems.append(f"steps={names}")
        if out["skipped_steps"] != ["1_refresh_raw", "2_emit_l2_dense"]:
            problems.append(f"skipped={out['skipped_steps']}")
        for s in out["steps"]:
            if s["returncode"] != 0:
                problems.append(f"{s['name']} exit {s['returncode']}: {s['stderr_tail']}")
    _record("test_wrapper_runs_exactly_one_live_step", not problems, "; ".join(problems))


def test_pipeline_emits_exactly_the_declared_stubs() -> None:
    """파이프라인이 만드는 L2 는 **선언된 4종뿐**이다 — L1 wiki page 사본 0."""
    from workflow_kit.tools.refresh_wiki_memory import L2_STUBS

    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td))
        proc = _run(WRAPPER_MODULE, ["--apply"], repo)
        made = sorted(p.stem for p in (repo / "ai-workflow" / "wiki" / "sources").glob("*.md"))
    problems = []
    if proc.returncode != 0:
        problems.append(f"exit {proc.returncode}")
    if made != sorted(L2_STUBS):
        problems.append(f"emit 결과={made} (선언={sorted(L2_STUBS)})")
    _record("test_pipeline_emits_exactly_the_declared_stubs", not problems, "; ".join(problems))


# --- 3. 목록은 한 곳에만 ---------------------------------------------------


def test_metric_reads_the_generator_constant_not_a_copy() -> None:
    """지표가 stub 목록을 **복제하지 않는다** — 복제하면 한쪽만 바뀌어 갈라진다."""
    from workflow_kit.tools.refresh_wiki_memory import L2_STUBS
    from workflow_kit.tools.score_wiki_maintainability import _declared_l2_stubs

    problems = []
    if _declared_l2_stubs() != sorted(L2_STUBS):
        problems.append(f"불일치: {_declared_l2_stubs()} vs {sorted(L2_STUBS)}")
    src = (TOOLS / "score_wiki_maintainability.py").read_text(encoding="utf-8")
    for stem in L2_STUBS:
        if f'"{stem}"' in src:
            problems.append(f"목록 복제: {stem}")
    _record("test_metric_reads_the_generator_constant_not_a_copy", not problems, "; ".join(problems))


def test_contract_doc_names_the_generator_constant() -> None:
    """계약 문서가 정본이 어디인지 가리킨다 (두 번째 목록이 되지 않게)."""
    doc = (REPO_ROOT / "ai-workflow" / "wiki" / "sources" / ".gitkeep").read_text(encoding="utf-8")
    problems = []
    if "refresh_wiki_memory.L2_STUBS" not in doc:
        problems.append("정본 상수 이름 없음")
    if "emit_wiki_l2_body" not in doc:
        problems.append("은퇴 사실 미기재")
    _record("test_contract_doc_names_the_generator_constant", not problems, "; ".join(problems))


# --- 4. 분모는 선언된 집합 -------------------------------------------------


def test_missing_stub_lowers_the_score() -> None:
    """**stub 을 지우면 점수가 내려간다.**

    되주입 대상: 이전에는 분모가 *찾은 파일 수* 라 3장을 지워도
    total=1 / searchable=1 → **5.0 그대로** 였다. 사라짐이 지표에 안 잡혔다.
    """
    import importlib

    import workflow_kit.tools.score_wiki_maintainability as swm

    with tempfile.TemporaryDirectory() as td:
        sources = Path(td) / "sources"
        sources.mkdir(parents=True)
        stubs = ["active-state", "active-work-backlog", "active-session-handoff", "wiki-log"]
        for name in stubs:
            _write(sources / f"{name}.md", "---\ntype: meta\nlast_touched: 2099-01-01\n---\n\n"
                   + ("본문 줄.\n" * 40))
        orig_src, orig_decl = swm.L2_SOURCES, swm._declared_l2_stubs
        try:
            swm.L2_SOURCES = sources
            swm._declared_l2_stubs = lambda: sorted(stubs)
            full_disc, _ = swm.score_discoverability()
            full_life, _ = swm.score_lifecycle()
            for name in stubs[1:]:
                (sources / f"{name}.md").unlink()
            part_disc, disc_detail = swm.score_discoverability()
            part_life, life_detail = swm.score_lifecycle()
        finally:
            swm.L2_SOURCES, swm._declared_l2_stubs = orig_src, orig_decl
            importlib.reload(swm)

    problems = []
    if full_disc != 5.0 or full_life != 5.0:
        problems.append(f"온전할 때 {full_disc}/{full_life} (5.0 기대)")
    if part_disc >= full_disc:
        problems.append(f"discoverability 가 안 내려갔다: {part_disc} (분모={disc_detail.get('total')})")
    if part_life >= full_life:
        problems.append(f"lifecycle 이 안 내려갔다: {part_life} (분모={life_detail.get('total')})")
    if disc_detail.get("total") != 4 or life_detail.get("total") != 4:
        problems.append(f"분모가 선언 집합이 아니다: {disc_detail.get('total')}/{life_detail.get('total')}")
    _record("test_missing_stub_lowers_the_score", not problems, "; ".join(problems))


def test_placeholder_detection_is_line_anchored() -> None:
    """placeholder 를 **인용한** 문서를 placeholder 로 세지 않는다.

    부분 문자열 판정이 실제로 오탐을 냈다 (2026-08-20): handoff 파생 뷰가
    "게이트가 `<needs content>` 하나라" 고 설명하는데 검색 불가로 집계됐다.
    """
    from workflow_kit.tools.score_wiki_maintainability import _is_placeholder_body

    problems = []
    if not _is_placeholder_body("## Summary\n<needs content>\n"):
        problems.append("진짜 placeholder 를 못 잡는다")
    if _is_placeholder_body("게이트가 `<needs content>` 하나라 재emit 이 안 됐다."):
        problems.append("인용을 placeholder 로 오탐한다")
    _record("test_placeholder_detection_is_line_anchored", not problems, "; ".join(problems))


def test_this_repo_scores_the_declared_four() -> None:
    """이 저장소 실측: 분모가 4, 부재 0."""
    import importlib

    import workflow_kit.tools.score_wiki_maintainability as swm

    importlib.reload(swm)
    _, disc = swm.score_discoverability()
    _, life = swm.score_lifecycle()
    problems = []
    if disc.get("total") != 4:
        problems.append(f"discoverability 분모={disc.get('total')}")
    if disc.get("missing"):
        problems.append(f"부재 stub={disc['missing']}")
    if life.get("total") != 4:
        problems.append(f"lifecycle 분모={life.get('total')}")
    _record("test_this_repo_scores_the_declared_four", not problems, "; ".join(problems))


def main() -> int:
    test_retired_emit_writes_nothing_and_says_why()
    test_retired_emit_still_accepts_old_flags()
    test_retired_machinery_is_gone_from_the_file()
    test_wrapper_runs_exactly_one_live_step()
    test_pipeline_emits_exactly_the_declared_stubs()
    test_metric_reads_the_generator_constant_not_a_copy()
    test_contract_doc_names_the_generator_constant()
    test_missing_stub_lowers_the_score()
    test_placeholder_detection_is_line_anchored()
    test_this_repo_scores_the_declared_four()
    total = 10
    if FAILURES:
        print(f"\n{len(FAILURES)}/{total} tests failed: {FAILURES}")
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    print(f"\nAll {total} tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
