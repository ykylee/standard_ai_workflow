#!/usr/bin/env python3
"""허브 위키 (M-036 WBS-36.1) — ingest 묶음 · index/log 생성 · 읽기 · lint 를 잰다.

정본: ``core/hub_spec.md`` §3.3 · §4.5 · §6.7 (요구 R8.1 · R8.2 · R8.3 · R8.5).

1. ingest 묶음 = 트랜잭션 하나 — 한 페이지 version 충돌이면 전체 409 · 부분 반영 0 · 생성물 쓰기 거절 (R8.2 · E4)
2. index · log 는 허브가 생성 — 생성 index 가 V-4 를 통과, log 에 ingest 마다 한 항목 (concept §11.3)
3. 읽기 — 보기 · 목록 · 검색 왕복, 없는 페이지 404 (R8.5)
4. lint — 깨진 위키 링크를 잡고 고치면 통과, 저장소 참조 · freshness 는 '미측정' (대상 수 0), 빈 위키는 ok 없음 (R8.3 · R8.4)
5. 같은 함수 — 이 저장소 위키를 허브로 들여와 펼친 디렉터리에서 잰 링크 판정이 저장소 뿌리에서 잰 판정과 같다 (R8.3 [검증])
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 240

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/check_hub_core.py",
    "ai-workflow/wiki/*",
)

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


def main() -> int:
    print("=== 허브 위키 (M-036 WBS-36.1) ===")
    with tempfile.TemporaryDirectory(prefix="hubwiki-") as d:
        tmp = Path(d)
        hub = Hub(tmp / "hub.db")
        try:
            try:
                run(hub, tmp)
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
