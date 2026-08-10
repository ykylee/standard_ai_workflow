"""title drift 임계 캘리브레이션 고정 검사 (TASK-2026-08-10-main-008).

`TITLE_SIMILARITY_THRESHOLD = 0.6` 은 2026-08-09 에 "출발점" 으로 놓였고,
2026-08-10 에 저장소 자신의 제목 데이터로 실측 캘리브레이션했다
(`scripts/calibrate_title_drift.py` → `schemas/title_drift_calibration.json`).
이 검사는 그 조사를 일회용으로 끝내지 않기 위한 고정이다.

검증 케이스 (7):
    1. fixture 자기 정합 — 저장된 similarity == production `title_similarity` 재계산
       (유사도 함수가 바뀌면 fixture 가 낡았다는 것을 여기서 잡는다)
    2. 임계 == fixture 의 캘리브레이션 임계
       (임계를 바꾸려면 재캘리브레이션이 함께 가야 한다)
    3. 정본 소스(backlog bullet / task H1) 양성의 suspect 노이즈 ≤ 15%
       (실측 1/14 — 유일 사례는 "제목 vs 제목+괄호 부연")
    4. handoff 양성(계획 문구 vs 완료 제목)의 suspect 노이즈 ≤ 45%
       (실측 25/67 — 정당한 재표현이라 LLM 판정으로 가는 것이 설계다)
    5. 실질-다른-task 프록시 음성의 검출률 ≥ 95% (실측 373/375)
    6. 구조적 한계 고정 — 같은-축 형제 task 쌍은 임계 이상으로 남는다.
       임계를 올려 이걸 "고치면" case 3/4 의 노이즈 상한이 깨진다 —
       이 한계는 유사도가 아니라 LLM 판정 층의 몫이다.
    7. fixture 개수 == _meta 선언 (요구 목록은 파생시킨다)

기각된 대안 (실측 근거는 generator docstring): 꼬리 괄호 제거 정규화 —
양성 노이즈 26→17 vs 음성 놓침 115→287. 괄호 부연이 변별 정보였다.

Stdlib only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.drift_detection import (  # noqa: E402
    TITLE_SIMILARITY_THRESHOLD,
    title_similarity,
)

FIXTURE_PATH = SOURCE_ROOT / "schemas" / "title_drift_calibration.json"

#: 실측 2026-08-10 대비 여유를 둔 수용 상한 / 하한.
CANONICAL_NOISE_MAX = 0.15
HANDOFF_NOISE_MAX = 0.45
NEGATIVE_CATCH_MIN = 0.95

#: case 6 — 구조적 한계의 안정 표본 (같은-축 형제 task, 실측 0.694 / 0.706).
KNOWN_BLIND_PAIRS = [
    ("TASK-2026-08-08-main-001", "TASK-2026-08-08-main-002"),
    ("TASK-2026-08-09-main-017", "TASK-2026-08-10-main-003"),
]


def main() -> int:
    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        if cond:
            print(f"PASS: {label}")
        else:
            print(f"FAIL: {label} — {detail}")
            failures.append(label)

    fixture: dict[str, Any] = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    meta = fixture["_meta"]
    positives: list[dict[str, Any]] = fixture["positive_pairs"]
    negatives: list[dict[str, Any]] = fixture["negative_pairs"]
    representative: dict[str, str] = fixture["representative_titles"]
    threshold = float(meta["calibrated_threshold"])

    # 1) fixture 자기 정합 — 저장값과 production 재계산의 일치
    mismatches: list[str] = []
    for pair in positives:
        recomputed = round(title_similarity(pair["a"], pair["b"]), 4)
        if recomputed != pair["similarity"]:
            mismatches.append(f"pos {pair['task_id']}: {pair['similarity']} != {recomputed}")
    for pair in negatives:
        recomputed = round(
            title_similarity(representative[pair["a_id"]], representative[pair["b_id"]]), 4
        )
        if recomputed != pair["similarity"]:
            mismatches.append(
                f"neg {pair['a_id']}~{pair['b_id']}: {pair['similarity']} != {recomputed}"
            )
    check(
        "1) fixture similarity == production 재계산",
        not mismatches,
        f"{len(mismatches)}건 불일치 (유사도 함수가 바뀌었으면 재캘리브레이션): {mismatches[:3]}",
    )

    # 2) 임계 동결 — 바꾸려면 재캘리브레이션이 함께 가야 한다
    check(
        "2) TITLE_SIMILARITY_THRESHOLD == 캘리브레이션 임계",
        TITLE_SIMILARITY_THRESHOLD == threshold,
        f"code={TITLE_SIMILARITY_THRESHOLD} fixture={threshold} — "
        "임계를 바꿨으면 scripts/calibrate_title_drift.py --apply 로 재캘리브레이션할 것",
    )

    # 3) 정본 소스 양성 노이즈
    canonical = [p for p in positives if p["class"] == "canonical"]
    canonical_noise = sum(1 for p in canonical if p["similarity"] < threshold)
    check(
        f"3) 정본 양성 노이즈 ≤ {CANONICAL_NOISE_MAX:.0%}",
        bool(canonical) and canonical_noise / len(canonical) <= CANONICAL_NOISE_MAX,
        f"{canonical_noise}/{len(canonical)}",
    )

    # 4) handoff 양성 노이즈 — 계획 문구 vs 완료 제목의 정당한 재표현
    handoff = [p for p in positives if p["class"] == "handoff"]
    handoff_noise = sum(1 for p in handoff if p["similarity"] < threshold)
    check(
        f"4) handoff 양성 노이즈 ≤ {HANDOFF_NOISE_MAX:.0%}",
        bool(handoff) and handoff_noise / len(handoff) <= HANDOFF_NOISE_MAX,
        f"{handoff_noise}/{len(handoff)}",
    )

    # 5) 프록시 음성 검출률
    caught = sum(1 for p in negatives if p["similarity"] < threshold)
    check(
        f"5) 음성 검출률 ≥ {NEGATIVE_CATCH_MIN:.0%}",
        bool(negatives) and caught / len(negatives) >= NEGATIVE_CATCH_MIN,
        f"{caught}/{len(negatives)}",
    )

    # 6) 구조적 한계 고정 — 같은-축 형제 task 는 임계 이상으로 남는다
    blind_ok = True
    blind_detail: list[str] = []
    for a_id, b_id in KNOWN_BLIND_PAIRS:
        sim = title_similarity(representative[a_id], representative[b_id])
        blind_detail.append(f"{a_id}~{b_id}={sim:.3f}")
        if sim < threshold:
            blind_ok = False
    check(
        "6) 한계 표본 — 같은-축 형제 task 쌍은 유사도로 못 가른다 (임계 이상 유지)",
        blind_ok,
        f"{blind_detail} — 임계 이하가 됐다면 유사도 함수가 바뀐 것. 재캘리브레이션할 것",
    )

    # 7) 개수 정합
    check(
        "7) fixture 개수 == _meta 선언",
        len(representative) == meta["task_ids"],
        f"reps={len(representative)} meta={meta['task_ids']}",
    )

    total = 7
    print()
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
