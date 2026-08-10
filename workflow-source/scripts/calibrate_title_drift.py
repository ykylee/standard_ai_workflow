#!/usr/bin/env python3
"""title drift 임계 캘리브레이션 fixture 재생성 (TASK-2026-08-10-main-008).

`TITLE_SIMILARITY_THRESHOLD` 는 2026-08-09 에 "출발점" 으로 놓인 값이었다.
이 스크립트는 저장소 자신의 실제 제목 데이터로 그 임계를 실측한다:

- **양성** (같은 task 의 표기 변형): 같은 TASK-ID 의 distinct 제목 쌍.
  제목이 *정의되는* 자리만 읽는다 — backlog index 의 task bullet /
  task 파일 H1 / handoff 의 production 소비 섹션("다음에 할 일" +
  "최근 완료 작업"). 현재 트리 + git 히스토리 전 버전.
- **음성** (실질 교체의 프록시): 서로 다른 TASK-ID 의 대표 제목 쌍.
  ID 인접 3개 = hard negative (같은 날짜대 · 같은 축이라 표현이 비슷),
  원거리 window = easy negative.

산출물은 `schemas/title_drift_calibration.json` 에 고정하고
`tests/check_title_drift_calibration.py` 가 임계의 성질을 검증한다 —
조사를 일회용으로 끝내지 않기 위한 고정이다. 재캘리브레이션이 필요하면
이 스크립트를 `--apply` 로 다시 돌린다.

교훈 (1차 채굴의 실패): 임의 줄의 TASK-ID 언급을 전부 먹이면 제목 아닌
산문("있다", "[x] ~~")이 섞여 분포가 뒤집힌다. production 이 실제로 읽는
자리만 먹여야 한다.

기각된 대안 (실측): 꼬리 괄호 부연 제거 정규화는 양성 노이즈를 26→17 로
줄이지만 음성 놓침을 115→287 로 늘린다 — 괄호 부연이 정확히 변별
정보였다 (연속 릴리스류 제목). 정규화하지 않는다.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.drift_detection import (  # noqa: E402
    TASK_ID_PATTERN,
    TITLE_SIMILARITY_THRESHOLD,
    extract_section,
    extract_task_titles,
    title_similarity,
)

FIXTURE_PATH = SOURCE_ROOT / "schemas" / "title_drift_calibration.json"

#: backlog index 의 task bullet 만 (notes 줄의 ID 언급 배제). ID 정규식은 정본에서 유도.
BULLET = re.compile(rf"^-\s+\*\*{TASK_ID_PATTERN.pattern}\*\*\s+")
#: task 파일 H1. 제목 파싱 자체는 extract_task_titles 에 맡긴다 (규약 단일 출처).
H1 = re.compile(rf"^#\s+{TASK_ID_PATTERN.pattern}\s+[—–-]\s+")

#: handoff 에서 production (detect_scope_drift) 이 실제로 읽는 두 섹션.
PRODUCTION_SECTIONS = ("다음에 할 일", "최근 완료 작업")

TitleSink = Callable[[str, str], None]


def feed_index(text: str, source: str, record: TitleSink) -> None:
    for line in text.splitlines():
        if BULLET.match(line):
            for task_id, title in extract_task_titles(line).items():
                record(task_id, title)


def feed_taskfile(text: str, source: str, record: TitleSink) -> None:
    for line in text.splitlines():
        if H1.match(line):
            for task_id, title in extract_task_titles(line).items():
                record(task_id, title)
            return


def feed_handoff(text: str, source: str, record: TitleSink) -> None:
    for header in PRODUCTION_SECTIONS:
        for task_id, title in extract_task_titles(extract_section(text, header)).items():
            record(task_id, title)


SOURCES: list[tuple[str, Callable[[str, str, TitleSink], None], str]] = [
    ("ai-workflow/memory/active/*/backlog/*.md", feed_index, "canonical"),
    ("ai-workflow/memory/archived/*/backlog/*.md", feed_index, "canonical"),
    ("ai-workflow/memory/release/*/backlog/*.md", feed_index, "canonical"),
    ("ai-workflow/memory/active/*/backlog/tasks/*.md", feed_taskfile, "canonical"),
    ("ai-workflow/memory/archived/*/backlog/tasks/*.md", feed_taskfile, "canonical"),
    ("ai-workflow/memory/active/*/session_handoff.md", feed_handoff, "handoff"),
    ("ai-workflow/memory/archived/*/session_handoff.md", feed_handoff, "handoff"),
]


def mine(today: str) -> dict[str, Any]:
    # TASK-ID -> 제목 -> 출처 class ("canonical" 이 하나라도 있으면 canonical 승)
    titles_by_id: dict[str, dict[str, str]] = defaultdict(dict)

    def make_sink(cls: str) -> TitleSink:
        def record(task_id: str, title: str) -> None:
            title = title.strip()
            if not title:
                return
            prev = titles_by_id[task_id].get(title)
            if prev != "canonical":
                titles_by_id[task_id][title] = cls

        return record

    n_docs = 0
    n_versions = 0
    for pattern, fn, cls in SOURCES:
        sink = make_sink(cls)
        for path in sorted(REPO_ROOT.glob(pattern)):
            if not path.is_file():
                continue
            rel = str(path.relative_to(REPO_ROOT))
            fn(path.read_text(encoding="utf-8", errors="replace"), f"tree:{rel}", sink)
            n_docs += 1
            shas = subprocess.run(
                ["git", "log", "--format=%H", "--follow", "--", rel],
                cwd=REPO_ROOT, capture_output=True, text=True, check=True,
            ).stdout.split()
            for sha in shas:
                show = subprocess.run(
                    ["git", "show", f"{sha}:{rel}"],
                    cwd=REPO_ROOT, capture_output=True, text=True,
                )
                if show.returncode == 0:
                    fn(show.stdout, f"{sha[:8]}:{rel}", sink)
                    n_versions += 1

    positive_pairs: list[dict[str, Any]] = []
    for task_id in sorted(titles_by_id):
        variants = titles_by_id[task_id]
        for a, b in itertools.combinations(sorted(variants), 2):
            cls = "canonical" if (
                variants[a] == "canonical" and variants[b] == "canonical"
            ) else "handoff"
            positive_pairs.append({
                "task_id": task_id, "a": a, "b": b, "class": cls,
                "similarity": round(title_similarity(a, b), 4),
            })

    # 음성: ID 별 대표 제목 (canonical 우선, 그다음 사전순 첫 것)
    representative: dict[str, str] = {}
    for task_id in sorted(titles_by_id):
        variants = titles_by_id[task_id]
        canonical = sorted(t for t, c in variants.items() if c == "canonical")
        representative[task_id] = canonical[0] if canonical else sorted(variants)[0]

    ids = sorted(representative)
    negative_pairs: list[dict[str, Any]] = []
    for i, tid_a in enumerate(ids):
        hard = [ids[j] for j in range(i + 1, min(i + 4, len(ids)))]
        far = [ids[j] for j in range(i + 29, min(i + 31, len(ids)))]
        for cls, tid_bs in (("hard", hard), ("far", far)):
            for tid_b in tid_bs:
                negative_pairs.append({
                    "a_id": tid_a, "b_id": tid_b, "class": cls,
                    "similarity": round(
                        title_similarity(representative[tid_a], representative[tid_b]), 4
                    ),
                })

    return {
        "_meta": {
            "generated_by": "scripts/calibrate_title_drift.py",
            "calibrated_at": today,
            "calibrated_threshold": TITLE_SIMILARITY_THRESHOLD,
            "task_id_source": "TASK-2026-08-10-main-008",
            "docs_read": n_docs,
            "history_versions_read": n_versions,
            "task_ids": len(titles_by_id),
            "method": (
                "양성 = 같은 TASK-ID 의 distinct 제목 쌍 (정본 자리만: backlog bullet / "
                "task H1 / handoff production 섹션; 현재 트리 + git 히스토리). "
                "음성 = 다른 ID 의 대표 제목 쌍 (인접 3 = hard, +29~30 = far). "
                "정규화 없음 — 꼬리 괄호 제거는 실측 기각 (음성 놓침 115→287)."
            ),
        },
        "representative_titles": representative,
        "positive_pairs": positive_pairs,
        "negative_pairs": negative_pairs,
    }


def summarize(fixture: dict[str, Any]) -> str:
    threshold = fixture["_meta"]["calibrated_threshold"]
    pos = fixture["positive_pairs"]
    neg = fixture["negative_pairs"]
    lines = []
    for cls in ("canonical", "handoff"):
        xs = [p for p in pos if p["class"] == cls]
        noisy = sum(1 for p in xs if p["similarity"] < threshold)
        lines.append(f"양성[{cls}]: {noisy}/{len(xs)} 이 임계 미만 (suspect 노이즈)")
    caught = sum(1 for p in neg if p["similarity"] < threshold)
    lines.append(f"음성: {caught}/{len(neg)} 검출 (임계 미만 = suspect)")
    missed = [p for p in neg if p["similarity"] >= threshold]
    max_sim = max((p["similarity"] for p in neg), default=0.0)
    lines.append(
        f"구조적 한계: 임계 이상인 실질-다른-task 쌍 {len(missed)}건 (max {max_sim}) "
        "— 같은-축 형제 task 는 유사도로 못 가른다"
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true",
                        help="fixture 를 실제로 쓴다 (기본: dry-run 요약만)")
    parser.add_argument("--date", required=True,
                        help="캘리브레이션 날짜 YYYY-MM-DD (재현성 위해 명시)")
    args = parser.parse_args()

    fixture = mine(args.date)
    print(f"docs={fixture['_meta']['docs_read']} "
          f"versions={fixture['_meta']['history_versions_read']} "
          f"ids={fixture['_meta']['task_ids']} "
          f"pos={len(fixture['positive_pairs'])} neg={len(fixture['negative_pairs'])}")
    print(summarize(fixture))

    if not args.apply:
        print(f"\n(dry-run — {FIXTURE_PATH.relative_to(REPO_ROOT)} 미변경. --apply 로 고정)")
        return 0

    FIXTURE_PATH.write_text(
        json.dumps(fixture, ensure_ascii=False, indent=1, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote {FIXTURE_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
