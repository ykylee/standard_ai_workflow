#!/usr/bin/env python3
"""[은퇴] L1 wiki page → L2 파생 뷰 emit (TASK-2026-08-20-main-001).

**이 경로는 은퇴했다. 아무것도 쓰지 않는다.**

원래 계약은 "L1 wiki page(`concepts/` `decisions/` …) 마다 `wiki/sources/` 에
압축 파생 뷰를 둔다" 였다. 그 근거는 **외부 vault(`~/wiki/`) retrieval** 이었다 —
vault 는 저장소 본문을 못 읽으니 압축 사본이 있어야 검색이 됐다.

그 근거가 **v0.7.17 in-repo 전환 때 사라졌다.** L1 이 저장소 안으로 들어온
순간부터 L1 은 이미 검색 가능하고, L2 사본은 검색을 늘리지 않으면서
드리프트 표면만 늘린다. 실제로 이 저장소에서 L1 page 85장에 대한 파생 뷰는
**한 장도 만들어진 적이 없고**, 만들었다면 절삭 사본 ~170KB 가 늘 뿐이었다.

그래서 L2 의 정의를 좁혔다 (2026-08-20 소유자 결정):

> **L2 = wiki 모양이 아닌 SSOT 를 wiki 검색용으로 압축한 뷰.**
> `state.json` / 최신 backlog index / `session_handoff.md` / `wiki/log.md` 4종뿐이고,
> 생성기는 `refresh_wiki_memory --emit-l2` 하나다.

L1 wiki page 는 그 정의에 들지 않는다 — 이미 wiki 모양이고 이미 검색된다.

계약 원문은 `ai-workflow/wiki/sources/.gitkeep` 에 있다.

진입점(`workflow-emit-wiki-l2-body`, `wk emit-wiki-l2-body`)은 남긴다. 다만
**조용히 통과하지 않는다** — 왜 아무것도 안 하는지 말하고 rc=0 으로 끝낸다.
"""

from __future__ import annotations

import argparse
import sys

#: 은퇴 사유. 조용한 no-op 은 "돌렸으니 갱신됐겠지" 를 만든다.
RETIRED_MESSAGE = (
    "[RETIRED] emit_wiki_l2_body 는 아무것도 쓰지 않는다 (TASK-2026-08-20-main-001).\n"
    "  · L1 wiki page → L2 파생 뷰 경로가 은퇴했다. 근거였던 외부 vault retrieval 은\n"
    "    v0.7.17 in-repo 전환 때 사라졌고, in-repo 에서 L1 은 이미 검색 가능하다.\n"
    "  · L2 는 이제 memory SSOT 파생 4종뿐이다 (active-state · active-work-backlog ·\n"
    "    active-session-handoff · wiki-log). 생성기는 `refresh_wiki_memory --emit-l2` 하나다.\n"
    "  · 계약 원문: ai-workflow/wiki/sources/.gitkeep\n"
    "  L2 를 갱신하려면: wk wiki-emit --apply"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    # 옛 인자를 계속 받아 준다 — 스크립트에 박혀 있던 호출이 argparse 오류로 죽는
    # 것보다, 실행되고 **왜 아무것도 안 했는지 듣는** 편이 낫다.
    parser.add_argument("--project", default=None, help="[은퇴] 무시된다")
    parser.add_argument("--apply", action="store_true", help="[은퇴] 무시된다 — write 0")
    parser.add_argument("--max-chars", type=int, default=None, help="[은퇴] 무시된다")
    parser.add_argument("--limit", type=int, default=None, help="[은퇴] 무시된다")
    parser.add_argument("--mode", default=None, help="[은퇴] 무시된다")
    parser.add_argument("--bootstrap-missing", action="store_true", help="[은퇴] 무시된다")
    parser.parse_args()

    print(RETIRED_MESSAGE, file=sys.stderr)
    print("Applied 0 page (retired).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
