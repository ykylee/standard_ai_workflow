#!/usr/bin/env python3
"""허브 위키 (M-036 WBS-36.1) — ingest 묶음 · index/log 생성 · 읽기 · lint 를 잰다.

정본: ``core/hub_spec.md`` §3.3 · §4.5 · §6.7 (요구 R8.1 · R8.2 · R8.3 · R8.5).

1. ingest 묶음 = 트랜잭션 하나 — 한 페이지 version 충돌이면 전체 409 · 부분 반영 0 · 생성물 쓰기 거절 (R8.2 · E4)
2. index · log 는 허브가 생성 — 생성 index 가 V-4 를 통과, log 에 ingest 마다 한 항목 (concept §11.3)
3. 읽기 — 보기 · 목록 · 검색 왕복, 없는 페이지 404 (R8.5)
4. lint — 깨진 위키 링크를 잡고 고치면 통과, 저장소 참조 · freshness 는 '미측정' (대상 수 0), 빈 위키는 ok 없음 (R8.3 · R8.4)
5. 같은 함수 — 이 저장소 위키를 허브로 들여와 펼친 디렉터리에서 잰 링크 판정이 저장소 뿌리에서 잰 판정과 같다 (R8.3 [검증])
6. memory_index — 1.x 스키마 검증 · version 409 · 보기 · 목록 (R8.1 · E5, WBS-36.2)
7. 양방향 링크 — lint 가 1.x audit 함수로 대칭 · 비대칭을 잰다 (E5)
8. 출처 — 저장소 키 · sha 를 싣고, 프로젝트 밖 키 · 틀린 sha 는 거절, 출처 없이 다시 쓰면 지운다 (R8.4)
9. 원격 읽기 — 소유자만 켠다, 켜면 저장소 참조 · 출처 sha · freshness 를 재고, 못 받거나 끄면 미측정 (R8.4 · E3)
10. 위키 디렉터리 운반 — 이 저장소 위키를 들였다 내보내면 페이지가 바이트 그대로 · 1.x index/log 원문은 보관 · 표식 (R8.6 소유자 결정 · R15.2)
11. OKF 출판 — 허브 내보내기 = 저장소에서 1.x export_wiki_to_okf 를 직접 돌린 결과, 빠진 페이지를 목록으로 (R8.6)
12. 남의 OKF 묶음 들여오기 — loose 한 방향, 같은 경로는 409 (R8.6)
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 420

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/check_hub_core.py",
    "ai-workflow/wiki/*",
)

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_hub_core import Hub  # noqa: E402
from workflow_kit.common.wiki_rules import classify_wikilinks, validate_index  # noqa: E402

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


PAGE_A = "---\ntitle: 알파 개념\n---\n\n# 알파\n\n베타와 이어진다: [[concepts/beta]]\n"
PAGE_B = "# 베타\n\n감마 검색어 하나.\n"


def run(hub: Hub, tmp: Path) -> None:
    reg = hub.call("hub_project_register", {"remote_url": "git@github.com:acme/wiki.git", "display_name": "Wiki",
                                             "callsign": "agent-a", "kind": "agent"})[1]
    tok = reg["token"]
    tok_b = hub.call("hub_callsign_register", {"project_id": reg["project_id"], "callsign": "agent-b", "kind": "agent"})[1]["token"]

    # 빈 위키 — 잴 것이 없음은 통과가 아니다
    st, empty, _ = hub.call("hub_wiki_lint", {}, tok)

    # --- 1. ingest 묶음 ---------------------------------------------------------
    st1, ing1, _ = hub.call("hub_wiki_ingest", {"summary": "첫 묶음", "pages": [
        {"path": "concepts/alpha.md", "body": PAGE_A}, {"path": "concepts/beta.md", "body": PAGE_B}]}, tok)
    st2, conflict, _ = hub.call("hub_wiki_ingest", {"summary": "둘째 묶음", "pages": [
        {"path": "concepts/alpha.md", "body": PAGE_A + "\n고침\n", "expected_version": 1},
        {"path": "concepts/beta.md", "body": PAGE_B + "\n고침\n", "expected_version": 0}]}, tok_b)
    alpha_after = hub.call("hub_wiki_get", {"path": "concepts/alpha.md"}, tok)[1]
    st_gen, gen_err, _ = hub.call("hub_wiki_ingest", {"summary": "생성물", "pages": [{"path": "index.md", "body": "# x\n"}]}, tok)
    st_dup, _, _ = hub.call("hub_wiki_ingest", {"summary": "겹침", "pages": [
        {"path": "concepts/c.md", "body": "# c\n"}, {"path": "concepts/c.md", "body": "# c\n"}]}, tok)
    st_trav, _, _ = hub.call("hub_wiki_ingest", {"summary": "탈출", "pages": [{"path": "../x.md", "body": "# x\n"}]}, tok)
    st3, ing3, _ = hub.call("hub_wiki_ingest", {"summary": "셋째 묶음", "pages": [
        {"path": "concepts/alpha.md", "body": PAGE_A + "\n고침\n", "expected_version": 1},
        {"path": "topics/gamma.md", "body": "# 감마\n\n[[concepts/alpha]] 참조. 저장소 [[workflow-source/README.md]]\n"}]}, tok_b)
    conflicts = (conflict.get("detail") or {}).get("conflicts", [])
    problems = []
    if st1 != 200 or ing1.get("ingest_id") != "ING-00001" or [p["version"] for p in ing1.get("pages", [])] != [1, 1]:
        problems.append(f"첫 묶음 {st1} {ing1}")
    if st2 != 409 or [c["path"] for c in conflicts] != ["concepts/beta.md"]:
        problems.append(f"충돌 묶음 {st2} {conflict}")
    if alpha_after.get("version") != 1 or "고침" in alpha_after.get("body", ""):
        problems.append(f"409 묶음의 다른 페이지가 반영됐다 (부분 반영): v{alpha_after.get('version')}")
    if st_gen != 400 or st_dup != 400 or st_trav != 400:
        problems.append(f"생성물 {st_gen} · 겹침 {st_dup} · 경로 탈출 {st_trav} (기대 400)")
    if st3 != 200 or ing3.get("ingest_id") != "ING-00002":
        problems.append(f"셋째 묶음 {st3} {ing3} — 409 묶음이 ingest 번호를 먹었거나 실패")
    _record("case 1 ingest 묶음 = 트랜잭션 하나 · 부분 반영 0 · 생성물 거절", not problems, "; ".join(problems))

    # --- 2. index · log 생성 ----------------------------------------------------
    index = hub.call("hub_wiki_get", {"path": "index.md"}, tok)[1]
    log = hub.call("hub_wiki_get", {"path": "log.md"}, tok)[1]
    problems = []
    root = tmp / "wiki2"
    for path in ("concepts/alpha.md", "concepts/beta.md", "topics/gamma.md"):
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text("x", encoding="utf-8")
    errors, entries = validate_index(index.get("body", "").splitlines(), root)
    if not index.get("generated") or errors or entries != 3:
        problems.append(f"생성 index V-4 {errors} · 항목 {entries}")
    if "## Concepts" not in index.get("body", "") or "### [[topics/gamma]] {#gamma}" not in index.get("body", ""):
        problems.append("index 의 절 · anchor 형식")
    body = log.get("body", "")
    if body.count("] ingest | ") != 2 or "첫 묶음" not in body or "셋째 묶음" not in body or "둘째 묶음" in body:
        problems.append(f"log 항목 (기대: 성공한 묶음 2개만): {body!r}")
    _record("case 2 index · log 는 허브가 생성 (V-4 통과 · ingest 마다 한 항목)", not problems, "; ".join(problems))

    # --- 3. 읽기 ----------------------------------------------------------------
    lst = hub.call("hub_wiki_list", {"prefix": "concepts/"}, tok)[1]
    hits = hub.call("hub_wiki_search", {"query": "감마 검색어"}, tok)[1]
    st404, _, _ = hub.call("hub_wiki_get", {"path": "concepts/none.md"}, tok)
    beta = hub.call("hub_wiki_get", {"path": "concepts/beta.md"}, tok)[1]
    problems = []
    if [p["path"] for p in lst.get("pages", [])] != ["concepts/alpha.md", "concepts/beta.md"] \
            or lst["pages"][0].get("title") != "알파 개념":
        problems.append(f"목록 {lst}")
    if [h["path"] for h in hits.get("hits", [])] != ["concepts/beta.md"] or "감마" not in hits["hits"][0].get("snippet", ""):
        problems.append(f"검색 {hits}")
    if beta.get("body") != PAGE_B or st404 != 404:
        problems.append(f"보기 왕복 · 404 ({st404})")
    _record("case 3 읽기 — 목록 · 검색 · 보기 왕복", not problems, "; ".join(problems))

    # --- 4. lint ----------------------------------------------------------------
    hub.call("hub_wiki_ingest", {"summary": "깨진 링크", "pages": [
        {"path": "topics/broken.md", "body": "# 깨짐\n\n[[concepts/nope]] 와 `[[코드 안은 링크 아님]]`\n"}]}, tok)
    bad = hub.call("hub_wiki_lint", {}, tok)[1]
    hub.call("hub_wiki_ingest", {"summary": "고침", "pages": [
        {"path": "topics/broken.md", "body": "# 고침\n\n[[concepts/beta]]\n", "expected_version": 1}]}, tok)
    good = hub.call("hub_wiki_lint", {}, tok)[1]
    problems = []
    if st != 200 or empty.get("ok") is not None or empty.get("status") != "empty":
        problems.append(f"빈 위키 lint 가 ok 를 냈다: {empty}")
    if bad.get("ok") is not False or bad.get("broken_links") != [{"page": "topics/broken.md", "target": "concepts/nope"}]:
        problems.append(f"깨진 링크 미검출: {bad.get('broken_links')} ok={bad.get('ok')}")
    if good.get("ok") is not True or good.get("index", {}).get("entries") != 4 or good.get("location", {}).get("errors"):
        problems.append(f"고친 뒤 lint: {good}")
    rr, fr = good.get("repo_references", {}), good.get("freshness", {})
    if rr.get("status") != "unmeasured" or rr.get("count") != 1 or fr.get("status") != "unmeasured" or fr.get("targets") != 0:
        problems.append(f"미측정 표시: repo_references={rr} freshness={fr}")
    _record("case 4 lint — 깨진 링크 · 미측정 · 빈 위키", not problems, "; ".join(problems))

    # --- 5. 같은 함수 · 다른 디렉터리 -------------------------------------------
    wiki = REPO_ROOT / "ai-workflow" / "wiki"
    reg2 = hub.call("hub_project_register", {"remote_url": "git@github.com:acme/real.git", "display_name": "Real",
                                              "callsign": "agent-r", "kind": "agent"})[1]
    pages = [{"path": f.relative_to(wiki).as_posix(), "body": f.read_text(encoding="utf-8")}
             for f in sorted(wiki.rglob("*.md")) if f.relative_to(wiki).as_posix() not in ("index.md", "log.md")]
    # 요청 본문 상한(256KB) 아래로 묶음을 나눈다 — 큰 들여오기는 여러 ingest 다.
    batches: list[list[dict[str, str]]] = [[]]
    for page in pages:
        if batches[-1] and sum(len(p["body"].encode("utf-8")) for p in batches[-1]) + len(page["body"].encode("utf-8")) > 160_000:
            batches.append([])
        batches[-1].append(page)
    results = [hub.call("hub_wiki_ingest", {"summary": f"저장소 위키 들여오기 {i + 1}/{len(batches)}", "pages": b}, reg2["token"])
               for i, b in enumerate(batches)]
    st5 = max(r[0] for r in results)
    ing5 = {"pages": [p for r in results for p in r[1].get("pages", [])]}
    lint5 = hub.call("hub_wiki_lint", {}, reg2["token"])[1]
    broken, repo_refs = classify_wikilinks(wiki)
    problems = []
    if st5 != 200 or len(ing5.get("pages", [])) != len(pages):
        problems.append(f"들여오기 {st5} {str(ing5)[:200]}")
    if lint5.get("broken_links") != [{"page": a, "target": b} for a, b in broken] \
            or lint5.get("repo_references", {}).get("count") != len(repo_refs):
        problems.append(f"허브 {len(lint5.get('broken_links', []))}/{lint5.get('repo_references')} ≠ 저장소 {len(broken)}/{len(repo_refs)}")
    if lint5.get("index", {}).get("entries") != len(pages) or lint5.get("index", {}).get("errors"):
        problems.append(f"생성 index {lint5.get('index')} (페이지 {len(pages)})")
    _record(f"case 5 같은 함수 — 저장소 위키 {len(pages)} 페이지, 저장소 뿌리 판정 = 허브 판정", not problems, "; ".join(problems))


def _entry(eid: str, mentioned: list[str]) -> dict:
    return {"id": eid, "schema_version": 1, "source_paths": ["ai-workflow/x.md"], "primary_abstraction": f"entry {eid}",
            "cue_anchors": ["x"], "value_digest": "x", "owners": ["o"], "scope": ["s"], "merge_state": "active",
            "mentioned_in": mentioned, "related_ids": [], "created_at": "2026-01-01", "updated_at": "2026-01-01"}


def _git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid", "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=env).stdout.strip()


def run_36_2(hub: Hub, tmp: Path) -> None:
    reg = hub.call("hub_project_register", {"remote_url": "git@github.com:acme/mem2.git", "display_name": "Mem2",
                                             "callsign": "owner-a", "kind": "agent"})[1]
    tok, key = reg["token"], reg["key"]
    tok_e = hub.call("hub_callsign_register", {"project_id": reg["project_id"], "callsign": "editor-b", "kind": "agent"})[1]["token"]

    # --- 6. memory_index --------------------------------------------------------
    e1 = _entry("MEM-2026-01-01-001", ["ai-workflow/wiki/topics/p.md"])
    s1, r1, _ = hub.call("hub_memory_entry_put", {"entry": e1, "expected_version": 0}, tok)
    s_stale, _, _ = hub.call("hub_memory_entry_put", {"entry": e1, "expected_version": 0}, tok_e)
    s_bad, bad, _ = hub.call("hub_memory_entry_put", {"entry": {**e1, "id": "MEM-bad"}}, tok)
    got = hub.call("hub_memory_entry_get", {"id": "MEM-2026-01-01-001"}, tok_e)[1]
    lst = hub.call("hub_memory_entry_list", {}, tok)[1]
    problems = []
    if s1 != 200 or r1.get("version") != 1 or s_stale != 409:
        problems.append(f"쓰기 {s1} {r1} · 낡은 version {s_stale}")
    if s_bad != 400 or "entry.id" not in str((bad.get("detail") or {}).get("field", "")):
        problems.append(f"스키마 거절 {s_bad} {bad}")
    if got.get("entry", {}).get("mentioned_in") != e1["mentioned_in"] or [e["id"] for e in lst.get("entries", [])] != [e1["id"]]:
        problems.append(f"보기 · 목록 {got} {lst}")
    _record("case 6 memory_index — 1.x 스키마 · 409 · 보기 · 목록", not problems, "; ".join(problems))

    # --- 7. 양방향 링크 ---------------------------------------------------------
    hub.call("hub_memory_entry_put", {"entry": _entry("MEM-2026-01-01-000", []), "expected_version": 0}, tok)
    page = "---\ntype: topic\ntitle: p\nrelated_pages: [MEM-2026-01-01-001]\n---\n\n# p\n"
    hub.call("hub_wiki_ingest", {"summary": "p", "pages": [{"path": "topics/p.md", "body": page}]}, tok)
    sym = hub.call("hub_wiki_lint", {}, tok)[1]
    hub.call("hub_memory_entry_put", {"entry": _entry("MEM-2026-01-01-002", ["ai-workflow/wiki/topics/p.md"]),
                                      "expected_version": 0}, tok)
    asym = hub.call("hub_wiki_lint", {}, tok)[1]
    problems = []
    if sym.get("ok") is not True or sym.get("bidir", {}).get("symmetric") != 1 or sym["bidir"].get("asymmetric"):
        problems.append(f"대칭 {sym.get('ok')} {sym.get('bidir')}")
    if asym.get("ok") is not False or asym.get("bidir", {}).get("asymmetric") != [
            {"entry": "MEM-2026-01-01-002", "page": "topics/p.md", "direction": "memory_only"}]:
        problems.append(f"비대칭 {asym.get('ok')} {asym.get('bidir')}")
    _record("case 7 양방향 링크 — 1.x audit 함수 (대칭 · 비대칭)", not problems, "; ".join(problems))

    # --- 8. 출처 ----------------------------------------------------------------
    sha = "a" * 40
    s_ok, _, _ = hub.call("hub_wiki_ingest", {"summary": "출처", "pages": [
        {"path": "topics/src.md", "body": "# s\n", "source": {"repo_key": key, "sha": sha}}]}, tok)
    src = hub.call("hub_wiki_get", {"path": "topics/src.md"}, tok)[1].get("source")
    s_key, _, _ = hub.call("hub_wiki_ingest", {"summary": "남의 키", "pages": [
        {"path": "topics/x.md", "body": "# x\n", "source": {"repo_key": "github.com/other/repo", "sha": sha}}]}, tok)
    s_sha, _, _ = hub.call("hub_wiki_ingest", {"summary": "틀린 sha", "pages": [
        {"path": "topics/x.md", "body": "# x\n", "source": {"repo_key": key, "sha": "zz"}}]}, tok)
    hub.call("hub_wiki_ingest", {"summary": "출처 없이", "pages": [
        {"path": "topics/src.md", "body": "# s2\n", "expected_version": 1}]}, tok)
    cleared = hub.call("hub_wiki_get", {"path": "topics/src.md"}, tok)[1].get("source")
    problems = []
    if s_ok != 200 or src != {"repo_key": key, "sha": sha}:
        problems.append(f"출처 싣기 {s_ok} {src}")
    if s_key != 400 or s_sha != 400:
        problems.append(f"남의 키 {s_key} · 틀린 sha {s_sha} (기대 400)")
    if cleared != {"repo_key": "", "sha": ""}:
        problems.append(f"출처 없이 다시 쓴 뒤 옛 출처가 남았다: {cleared}")
    _record("case 8 출처 — 저장소 키 · sha 싣기 · 거절 · 지움", not problems, "; ".join(problems))

    # --- 9. 원격 읽기 -----------------------------------------------------------
    repo = tmp / "origin"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "src").mkdir()
    (repo / "src" / "a.py").write_text("a = 1\n", encoding="utf-8")
    (repo / "README.md").write_text("# r\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "c1")
    c1 = _git(repo, "rev-parse", "HEAD")
    (repo / "src" / "a.py").write_text("a = 2\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "c2")
    c2 = _git(repo, "rev-parse", "HEAD")
    fm = "---\ntype: topic\ntitle: {t}\nlast_ingested_from: src/a.py\n---\n\n# {t}\n\n[[README.md]] [[docs/none.md]]\n"
    hub.call("hub_wiki_ingest", {"summary": "원격 대상", "pages": [
        {"path": "topics/old.md", "body": fm.format(t="old"), "source": {"repo_key": key, "sha": c1}},
        {"path": "topics/new.md", "body": fm.format(t="new"), "source": {"repo_key": key, "sha": c2}},
        {"path": "topics/ghost.md", "body": "# g\n", "source": {"repo_key": key, "sha": "b" * 40}}]}, tok)
    off = hub.call("hub_wiki_lint", {}, tok)[1]
    s_editor, _, _ = hub.call("hub_wiki_remote_set", {"fetch_url": repo.as_uri()}, tok_e)
    s_ext, _, _ = hub.call("hub_wiki_remote_set", {"fetch_url": "ext::sh -c id"}, tok)
    s_on, _, _ = hub.call("hub_wiki_remote_set", {"fetch_url": repo.as_uri()}, tok)
    on = hub.call("hub_wiki_lint", {}, tok)[1]
    hub.call("hub_wiki_remote_set", {"fetch_url": (tmp / "no-such-repo").as_uri()}, tok)
    fail = hub.call("hub_wiki_lint", {}, tok)[1]
    problems = []
    for name, res in (("꺼짐", off), ("받기 실패", fail)):
        st = [res.get(k, {}).get("status") for k in ("repo_references", "source_sha", "freshness")]
        if st != ["unmeasured"] * 3 or res.get("freshness", {}).get("targets") != 0 or not res.get("freshness", {}).get("reason"):
            problems.append(f"{name}: 미측정이 아니다 {st}")
    if s_editor != 403 or s_ext != 400 or s_on != 200:
        problems.append(f"설정 권한 · 주소: 편집자 {s_editor} (403) · ext:: {s_ext} (400) · 소유자 {s_on} (200)")
    rr, ss, fr = on.get("repo_references", {}), on.get("source_sha", {}), on.get("freshness", {})
    missing = sorted({m["target"] for m in rr.get("missing", [])})
    if rr.get("status") != "measured" or missing != ["docs/none.md"] or rr.get("head") != c2:
        problems.append(f"저장소 참조 {rr}")
    if ss.get("status") != "measured" or [u["page"] for u in ss.get("unknown", [])] != ["topics/ghost.md"]:
        problems.append(f"출처 sha {ss}")
    if fr.get("status") != "measured" or fr.get("targets") != 2 or [x["page"] for x in fr.get("stale", [])] != ["topics/old.md"]:
        problems.append(f"freshness {fr}")
    _record("case 9 원격 읽기 — 소유자만 · 켜면 측정 · 못 받거나 끄면 미측정", not problems, "; ".join(problems))


def _export_all(hub: Hub, tok: str, fmt: str, out_dir: str | None = None) -> tuple[dict[str, str], dict]:
    files: dict[str, str] = {}
    cursor, last, calls = 0, {}, 0
    while cursor is not None:
        args = {"format": fmt, "cursor": cursor, **({"out_dir": out_dir} if out_dir is not None else {})}
        st, last, _ = hub.call("hub_wiki_export", args, tok)
        if st != 200:
            raise RuntimeError(f"export {st} {last}")
        files.update({s_["path"]: s_["content"] for s_ in last["steps"]})
        cursor, calls = last["next_cursor"], calls + 1
    last["calls"] = calls
    return files, last


def run_36_3(hub: Hub, tmp: Path) -> None:
    wiki = REPO_ROOT / "ai-workflow" / "wiki"
    reg = hub.call("hub_project_register", {"remote_url": "git@github.com:acme/move.git", "display_name": "Move",
                                             "callsign": "mover", "kind": "agent"})[1]
    tok = reg["token"]
    all_files = [(q.relative_to(wiki).as_posix(), q.read_text(encoding="utf-8")) for q in sorted(wiki.rglob("*")) if q.is_file()]
    # 저장소 위키는 모두 줄바꿈 하나로 끝나 정규화가 바이트를 안 바꾼다 — 재려는 조건을 fixture 가 만든다.
    all_files.append(("concepts/zz-bytes.md", "# 바이트\r\n\n끝 공백   \n탭\t\n\n\n"))
    batches: list[list[dict[str, str]]] = [[]]
    for path, content in all_files:
        if batches[-1] and sum(len(f["content"].encode("utf-8")) for f in batches[-1]) + len(content.encode("utf-8")) > 160_000:
            batches.append([])
        batches[-1].append({"path": path, "content": content})
    results = [hub.call("hub_wiki_import_dir", {"files": b, "summary": f"1.x 위키 들여오기 {i + 1}/{len(batches)}"}, tok)
               for i, b in enumerate(batches)]
    one = [next({"path": path, "content": c} for path, c in all_files if path.startswith("concepts/"))]
    st_again, _, _ = hub.call("hub_wiki_import_dir", {"files": one, "summary": "다시"}, tok)
    st_over, _, _ = hub.call("hub_wiki_import_dir", {"files": one, "summary": "덮어쓰기", "overwrite": True}, tok)
    files, last = _export_all(hub, tok, "dir")
    pages = {path: c for path, c in all_files if path.endswith(".md") and path not in ("index.md", "log.md")}
    problems = []
    if any(r[0] != 200 for r in results):
        problems.append(f"들여오기 {[r[0] for r in results]} {[r[1] for r in results if r[0] != 200][:1]}")
    archived = sorted(a for r in results for a in r[1].get("archived_1x", []))
    skipped = sorted(x for r in results for x in r[1].get("skipped_non_page", []))
    if archived != ["index.md", "log.md"] or skipped != [".gitignore", "sources/.gitkeep"]:
        problems.append(f"보관 {archived} · 건너뜀 {skipped}")
    if st_again != 409 or st_over != 200:
        problems.append(f"다시 들이기 {st_again} (409) · overwrite {st_over} (200)")
    exported = {k[len("ai-workflow/wiki/"):]: v for k, v in files.items()}
    diff = [path for path, c in pages.items() if exported.get(path) != c]
    extra = sorted(set(exported) - set(pages) - {"index.md", "log.md", ".hub-export.json"})
    if diff or extra or len(pages) < 90:
        problems.append(f"바이트 불일치 {diff[:5]} · 남는 파일 {extra[:5]} (페이지 {len(pages)})")
    out_root = tmp / "exported-wiki"
    for path, c in exported.items():
        (out_root / path).parent.mkdir(parents=True, exist_ok=True)
        (out_root / path).write_text(c, encoding="utf-8")
    errors, _n = validate_index(exported.get("index.md", "").splitlines(), out_root)
    marker = exported.get(".hub-export.json", "")
    if errors or '"canonical": "hub"' not in marker or last.get("calls", 0) < 2:
        problems.append(f"생성 index {errors[:2]} · 표식 {marker[:60]!r} · 나눠 부르기 {last.get('calls')}")
    _record(f"case 10 위키 디렉터리 운반 — {len(pages)} 페이지 바이트 그대로 · 원문 보관 · 표식", not problems, "; ".join(problems))

    # --- 11. OKF 출판 -----------------------------------------------------------
    from workflow_kit.okf_export import export_wiki_to_okf
    okf, rep = _export_all(hub, tok, "okf", out_dir="pub")
    with tempfile.TemporaryDirectory(prefix="okf-native-") as d:
        export_wiki_to_okf(wiki, Path(d), resolve=False, emit_manifest=True)
        native = {q.relative_to(d).as_posix(): q.read_text(encoding="utf-8") for q in Path(d).rglob("*") if q.is_file()}
    hub_okf = {k[len("pub/"):]: v for k, v in okf.items()}
    problems = []
    vary = {"okf-bundle.yaml"}  # 생성 시각을 싣는다
    if set(hub_okf) != set(native) or [k for k in native if k not in vary and hub_okf.get(k) != native[k]]:
        problems.append(f"허브 OKF ≠ 1.x 직접 실행: {sorted(set(hub_okf) ^ set(native))[:5]} "
                        f"{[k for k in native if k not in vary and hub_okf.get(k) != native[k]][:5]}")
    if rep.get("lossy") is not True or len(rep.get("excluded", [])) != len(pages) - rep.get("pages_exported", -1) \
            or "concepts/zz-bytes.md" not in rep.get("excluded", []) or rep.get("excluded_by_error") != 1:
        problems.append(f"빠진 페이지 보고: exported {rep.get('pages_exported')} · excluded {len(rep.get('excluded', []))} · 페이지 {len(pages)}")
    _record(f"case 11 OKF 출판 = 1.x 함수 그대로 · 빠진 {len(rep.get('excluded', []))} 페이지를 목록으로", not problems, "; ".join(problems))

    # --- 12. 남의 OKF 묶음 들여오기 ---------------------------------------------
    small = hub.call("hub_project_register", {"remote_url": "git@github.com:acme/small.git", "display_name": "Small",
                                               "callsign": "pub", "kind": "agent"})[1]["token"]
    picks = [path for path in sorted(pages) if path.startswith("concepts/")][:3]
    hub.call("hub_wiki_ingest", {"summary": "작은 위키", "pages": [{"path": path, "body": pages[path]} for path in picks]}, small)
    bundle, _ = _export_all(hub, small, "okf", out_dir="b")
    dest = hub.call("hub_project_register", {"remote_url": "git@github.com:acme/dest.git", "display_name": "Dest",
                                              "callsign": "dest", "kind": "agent"})[1]["token"]
    bfiles = [{"path": k[len("b/"):], "content": v} for k, v in sorted(bundle.items())]
    st12, r12, _ = hub.call("hub_wiki_import_okf", {"files": bfiles, "summary": "남의 OKF"}, dest)
    st12b, _, _ = hub.call("hub_wiki_import_okf", {"files": bfiles, "summary": "또"}, dest)
    listed = [p_["path"] for p_ in hub.call("hub_wiki_list", {}, dest)[1].get("pages", [])]
    problems = []
    if st12 != 200 or r12.get("mode") != "loose" or r12.get("pages_staged") != 3 or listed != picks:
        problems.append(f"들여오기 {st12} {str(r12)[:200]} · 목록 {listed}")
    if st12b != 409:
        problems.append(f"같은 경로 다시 {st12b} (409)")
    _record("case 12 남의 OKF 묶음 — loose 한 방향 · 같은 경로 409", not problems, "; ".join(problems))


def main() -> int:
    print("=== 허브 위키 (M-036 WBS-36.1 · 36.2 · 36.3) ===")
    with tempfile.TemporaryDirectory(prefix="hubwiki-") as d:
        tmp = Path(d)
        hub = Hub(tmp / "hub.db")
        try:
            try:
                run(hub, tmp)
                run_36_2(hub, tmp)
                run_36_3(hub, tmp)
            except Exception as exc:  # noqa: BLE001 — 예외도 판정으로
                _record("run (예외)", False, repr(exc))
        finally:
            err = hub.stop()
            if _failures:
                print("  --- 허브 stderr ---\n" + err[-2000:])
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
