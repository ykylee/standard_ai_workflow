#!/usr/bin/env python3
"""Meta-check: **검색이 매칭된 entry 를 실제로 돌려주는가** (TASK-2026-09-23-main-005).

승격한 entry 가 '걸리는지' 를 재다가 검색 경로 결함 3건을 실측했다. 셋 다
`status: ok` 였고 아무 검사도 red 가 아니었다.

1. **seed 가 자기 확장분에 밀려났다.** 선택이 `sorted(seed_and_linked)[:top_k]`
   였는데 ID 가 `MEM-<날짜>-<번호>` 라 사전순 = 날짜순이고, 이 저장소의 링크
   관례는 최신 → 기존(26/26 단방향)이라 **확장분이 항상 seed 보다 오래됐다**.
   그래서 entry 의 *정확한 cue* 로 질의해도 그 entry 가 상위 3에 한 번도 안
   들었다 — `cue_hits=1` 을 보고하면서 그 1건을 안 돌려주는 상태였다.
2. **`current_axis` 가 질의 token 상한을 독점했다.** 그 한 줄이 130 token 이고
   상한은 8이라 `done_items` 의 기여가 **정확히 0** 이었다. 세 소비자
   (session-start / doc-sync / backlog-update)가 전부 같은 상수 질의를 냈다 —
   ADR-006 W-2 가 고치려던 '고정 질의' 가 이름만 바꿔 돌아온 것이다.
3. **조용한 0.** `selected_count: 0` 만으로는 색인이 빈 것인지, 질의가 안 맞은
   것인지, 단계가 꺼진 것인지 구분되지 않았다. 셋의 처방이 다른데 화면이 같았다.

검증 케이스 (8):
    1. 정확한 cue 로 질의하면 그 entry 가 **결과에 있다**
    2. 그리고 **맨 앞**이다 (확장분보다 먼저)
    3. 확장분은 hop 거리순 — 가까운 이웃이 먼 이웃보다 먼저
    4. 빈 결과는 사유를 내놓는다 + BM25 가 꺼져 있으면 그 사실을 말한다
    5. 비-ASCII 질의는 cue 단계가 구조적으로 못 맞춘다고 사유에 적힌다
    6. 긴 axis 가 token 상한을 독점하지 못한다 (done_items 가 기여한다)
    7. session-start 배선이 실제로 BM25 를 켜고 부른다 (end-to-end, 임시 workspace)
    8. **이 저장소 전수** — 모든 entry 가 자기 cue 로 자신을 1순위로 돌려받는다

Stdlib only (+ subprocess 로 CLI 실측).
"""

from __future__ import annotations

#: 전역 선언 (spec `core/test_impact_tiering_spec.md` §2).
#: case 8 이 저장소의 entry **전수**를 읽고 case 7 이 CLI 를 end-to-end 로 돈다.
WATCHES_ALL_REASON = (
    "case 8 이 memory_index entry 전수를 각자의 cue 로 질의하고, case 7 이 "
    "`wk session-start` 를 임시 workspace 에서 end-to-end 로 돈다. 판정 정본은 "
    "`workflow_kit/common/state/memory_index.py` · 배선은 "
    "`workflow_kit/tools/{session_start,doc_sync,backlog_update}.py` 다"
)

#: 이 검사가 강제하는 정본 요구 (spec §7).
ENFORCES = ("retrieval-must-return-what-it-matched",)

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = TESTS_DIR.parent
REPO_ROOT = SOURCE_ROOT.parent
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.state.memory_index import (  # noqa: E402
    build_cue_anchor_index,
    derive_context_query_tokens,
    load_memory_index,
    query_memory_index_for_dispatcher,
)


def _write_entry(d: Path, eid: str, cue: str, related: list[str]) -> None:
    (d / f"{eid}.json").write_text(json.dumps({
        "id": eid, "schema_version": 1,
        "source_paths": [], "primary_abstraction": f"abstraction {eid}",
        "cue_anchors": [cue], "value_digest": f"digest {eid}",
        "owners": ["t"], "scope": ["t"], "merge_state": "active",
        "mentioned_in": [], "related_ids": related,
        "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
    }, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    ran: list[str] = []
    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        ran.append(label)
        if cond:
            print(f"  PASS  {label}")
        else:
            print(f"  FAIL  {label} — {detail}")
            failures.append(label)

    with tempfile.TemporaryDirectory() as td:
        ws = Path(td) / "ws"
        ent = ws / "ai-workflow" / "memory" / "active" / "memory_index" / "entries"
        ent.mkdir(parents=True)
        # seed 는 **가장 최신 ID**. 링크는 최신 → 기존 (이 저장소의 실제 관례).
        # 옛 정렬(ID 사전순)이면 seed 가 마지막으로 밀린다.
        _write_entry(ent, "MEM-2026-09-01-001", "seed-cue", ["MEM-2026-01-02-001"])
        _write_entry(ent, "MEM-2026-01-02-001", "hop1-cue", ["MEM-2026-01-01-001"])
        _write_entry(ent, "MEM-2026-01-01-001", "hop2-cue", [])

        r = query_memory_index_for_dispatcher(ws, ["seed-cue"], top_k=2)
        check("1) 정확한 cue 로 질의하면 그 entry 가 결과에 있다",
              "MEM-2026-09-01-001" in r.selected_ids, f"selected={r.selected_ids}")
        check("2) seed 가 맨 앞이다",
              bool(r.selected_ids) and r.selected_ids[0] == "MEM-2026-09-01-001",
              f"selected={r.selected_ids} (옛 정렬이면 ID 사전순이라 seed 가 뒤로 밀린다)")

        r3 = query_memory_index_for_dispatcher(ws, ["seed-cue"], top_k=3, max_depth=2)
        check("3) 확장분은 hop 거리순 (가까운 이웃이 먼저)",
              r3.selected_ids == ["MEM-2026-09-01-001", "MEM-2026-01-02-001",
                                  "MEM-2026-01-01-001"],
              f"selected={r3.selected_ids}")

        # 4) 빈 결과의 사유 — BM25 가 꺼져 있다는 사실이 나와야 한다
        empty = query_memory_index_for_dispatcher(ws, ["nope-cue"])
        check("4) 빈 결과는 사유를 내놓고 BM25 상태를 말한다",
              bool(empty.empty_reason) and "BM25" in empty.empty_reason
              and bool(empty.warnings),
              f"reason={empty.empty_reason!r} warnings={empty.warnings}")

        # 5) 비-ASCII 질의는 cue 단계가 구조적으로 못 맞춘다고 말해야 한다
        ko = query_memory_index_for_dispatcher(ws, ["한글토큰"])
        check("5) 비-ASCII 질의의 구조적 불일치를 사유가 설명한다",
              "kebab" in ko.empty_reason, f"reason={ko.empty_reason!r}")

        # 6) 긴 axis 가 token 상한을 독점하지 못한다
        state = ws / "state.json"
        state.write_text(json.dumps({
            "session": {"current_axis": " ".join(f"축{i}" for i in range(200))},
            "backlog": {"done_items": ["고유토큰가 고유토큰나 고유토큰다"]},
        }, ensure_ascii=False), encoding="utf-8")
        toks, src = derive_context_query_tokens(state, base_tokens=["x", "y"])
        check("6) 긴 axis 가 상한을 독점하지 못한다 (done 이 기여한다)",
              src == "context" and any(t.startswith("고유토큰") for t in toks),
              f"tokens={toks} source={src}")

        # 7) 배선 end-to-end — session-start 가 실제로 BM25 를 켜고 부르는가.
        #    소스에서 문자열을 찾지 않는다: 그건 배선 검사가 아니다.
        ws7 = Path(td) / "ws7"
        (ws7 / "docs").mkdir(parents=True)
        (ws7 / "docs" / "PROJECT_PROFILE.md").write_text(
            "# p\n\n- workflow_memory_dir: ai-workflow/memory\n", encoding="utf-8")
        ent7 = ws7 / "ai-workflow" / "memory" / "active" / "memory_index" / "entries"
        ent7.mkdir(parents=True)
        _write_entry(ent7, "MEM-2026-09-01-001", "seed-cue", [])
        # session-start 는 handoff 가 없으면 기준선 복원을 **중단**하고
        # retrieval 까지 가지 않는다 — 배선을 재려면 최소 workspace 가 실재해야
        # 한다 (안 만들면 이 case 는 배선이 아니라 '문서 부재' 를 재게 된다).
        # **임시 workspace 를 git 저장소로 만든다.** 안 하면 브랜치 해석이 바깥
        # 저장소로 폴백해, 게이트의 `slash` 컨텍스트에서만 `active/<브랜치>` 가
        # 엇나가 red 가 된다 (2026-09-23 실측: native green / slash red).
        # fixture 는 자기가 재려는 조건을 **스스로** 성립시켜야 한다.
        subprocess.run(["git", "init", "-q", "-b", "main"],
                       cwd=str(ws7), capture_output=True, text=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-q", "--allow-empty", "-m", "seed"],
            cwd=str(ws7), capture_output=True, text=True,
        )
        branch7 = ws7 / "ai-workflow" / "memory" / "active" / "main"
        (branch7 / "backlog").mkdir(parents=True)
        (branch7 / "session_handoff.md").write_text(
            "# Session Handoff\n\n## 1. 현재 작업 요약\n\n- 현재 기준선: probe\n\n"
            "## 2. 진행 중 작업\n\n- 현재 `in_progress` 작업:\n-\n"
            "## 3. 차단 작업\n\n- 현재 `blocked` 작업:\n-\n"
            "## 4. 최근 완료 작업\n\n- 최근 완료 작업 목록:\n-\n",
            encoding="utf-8")
        (branch7 / "backlog" / "2026-01-01.md").write_text(
            "# 2026-01-01\n", encoding="utf-8")
        # 브랜치 env 오버라이드는 fixture 밖의 컨텍스트다 — 물려받으면 게이트의
        # `slash` 셀에서 `active/<슬래시 브랜치>` 를 찾아 이 case 가 배선이 아니라
        # **경로 부재**를 재게 된다 (2026-09-23 실측: native green / slash red).
        # 정본은 `paths.BRANCH_ENV_KEYS` 이고 여기서 그것을 통째로 지운다.
        from workflow_kit.common.paths import BRANCH_ENV_KEYS
        env = {k: v for k, v in os.environ.items()
               if not k.startswith("STANDARD_AI_WF") and k not in BRANCH_ENV_KEYS}
        env["PYTHONPATH"] = str(SOURCE_ROOT)
        proc = subprocess.run(
            [sys.executable, "-m", "workflow_kit.workflow_kit_cli",
             "--command=session-start", "--project-profile-path=docs/PROJECT_PROFILE.md"],
            cwd=str(ws7), capture_output=True, text=True, env=env, timeout=120,
        )
        try:
            payload = json.loads(proc.stdout)
            q = payload.get("memory_index_query_output") or {}
            flag = (q.get("source_context") or {}).get("use_bm25_fallback")
        except (json.JSONDecodeError, AttributeError):
            flag = f"(파싱 실패 rc={proc.returncode} {proc.stderr[:120]})"
        check("7) session-start 배선이 BM25 를 켜고 부른다 (end-to-end)",
              flag is True, f"use_bm25_fallback={flag!r}")

    # 8) **이 저장소 전수.** 자기 cue 로 질의하면 자신이 **seed 블록 안**에 있는가.
    #    처음에는 '1순위' 로 썼는데 그건 틀린 계약이었다 — cue 를 두 entry 가
    #    공유하는 경우가 실재한다 (2026-09-23 실측 2건: `memory-index`, `p0`).
    #    그때는 둘 다 seed 이고 누가 먼저인지는 이 축이 정할 바가 아니다.
    #    계약은 "seed 는 전부 확장분보다 앞" 이지 "내가 1등" 이 아니다.
    entries = load_memory_index(REPO_ROOT)
    anchors = build_cue_anchor_index(entries)
    offenders: list[str] = []
    checked = 0
    for e in entries:
        if not e.cue_anchors:
            continue
        cue = e.cue_anchors[0]
        seed_n = len(anchors.get(cue.strip().lower(), [])) or 1
        got = query_memory_index_for_dispatcher(REPO_ROOT, [cue], top_k=seed_n + 2)
        checked += 1
        if e.id not in got.selected_ids[:seed_n]:
            offenders.append(f"{e.id}(cue={cue}, seed_n={seed_n}) → {got.selected_ids[:3]}")
    check(f"8) 저장소 전수 {checked}건이 자기 cue 의 seed 블록 안에 있다",
          not offenders, f"밀려난 entry: {offenders[:4]}")

    total = len(ran)
    print()
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
