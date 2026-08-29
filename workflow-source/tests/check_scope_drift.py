"""scope drift detection smoke (TASK-2026-08-08-main-018, §0.8 #3)

`workflow_kit.common.drift_detection.detect_scope_drift()` 의 5+ case 결정 검증.
stdlib only. *pure function* — subprocess 없음 (CLI 자체는 별도 운영).

검증 케이스 (6):
    1. clean — pre = post, planned_done = all, score = 0
    2. planned_undone — pre 의 일부가 post 에 없음
    3. unplanned_done — post 의 일부가 pre 에 없음 (scope creep)
    4. both — planned_undone + unplanned_done 둘 다
    5. missing-section — pre text 는 있지만 *다음에 할 일* 섹션이 없음
    6. no-pre — pre_text=None, 모든 done 은 unplanned
    7. band threshold — score 0~0.3 minor / 0.3~0.7 significant / 0.7+ major

Stdlib only.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.drift_detection import (  # noqa: E402
    detect_scope_drift,
    extract_section,
    extract_task_ids,
)


def _handoff(planned: list[str] | None = None, done: list[str] | None = None) -> str:
    """테스트용 handoff text. planned/done 섹션이 있는 markdown."""
    lines = ["# Session Handoff", ""]
    if planned is not None:
        lines += ["## 5. 다음에 할 일 (순서)", ""]
        for t in planned:
            lines.append(f"- {t}")
        lines.append("")
    if done is not None:
        lines += ["## 4. 최근 완료 작업", ""]
        for t in done:
            lines.append(f"- {t}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    failures: list[str] = []

    # 1) clean — pre = post (TASK-1, TASK-2)
    pre = _handoff(planned=["TASK-2026-08-08-main-001 alpha", "TASK-2026-08-08-main-002 beta"])
    post = _handoff(done=["TASK-2026-08-08-main-001 alpha — done", "TASK-2026-08-08-main-002 beta — done"])
    r = detect_scope_drift(pre_text=pre, post_text=post)
    if r["planned_done"] != ["TASK-2026-08-08-main-001", "TASK-2026-08-08-main-002"]:
        failures.append(f"[1] clean: planned_done mismatch — {r['planned_done']}")
    elif r["planned_undone"] or r["unplanned_done"]:
        failures.append(f"[1] clean: undone or unplanned should be empty, got {r['planned_undone']}/{r['unplanned_done']}")
    elif r["drift_score"] != 0.0 or r["score_band"] != "clean":
        failures.append(f"[1] clean: score={r['drift_score']} band={r['score_band']} (expected 0.0/clean)")
    else:
        print("  [1] clean                ✓  (planned_done=2, drift_score=0.0)")

    # 2) planned_undone — TASK-2 가 post 에 없음
    pre = _handoff(planned=["TASK-2026-08-08-main-001 alpha", "TASK-2026-08-08-main-002 beta"])
    post = _handoff(done=["TASK-2026-08-08-main-001 alpha — done"])
    r = detect_scope_drift(pre_text=pre, post_text=post)
    if r["planned_undone"] != ["TASK-2026-08-08-main-002"]:
        failures.append(f"[2] undone: planned_undone mismatch — {r['planned_undone']}")
    elif r["unplanned_done"]:
        failures.append(f"[2] undone: unplanned should be empty, got {r['unplanned_done']}")
    elif r["score_band"] != "significant":
        failures.append(f"[2] undone: band={r['score_band']} (expected significant, score=0.5)")
    else:
        print(f"  [2] planned_undone       ✓  (TASK-002 누락, drift_score={r['drift_score']}, band=significant)")

    # 3) unplanned_done — TASK-3 가 pre 에 없음
    pre = _handoff(planned=["TASK-2026-08-08-main-001 alpha"])
    post = _handoff(done=["TASK-2026-08-08-main-001 alpha — done", "TASK-2026-08-08-main-003 creep"])
    r = detect_scope_drift(pre_text=pre, post_text=post)
    if r["unplanned_done"] != ["TASK-2026-08-08-main-003"]:
        failures.append(f"[3] creep: unplanned_done mismatch — {r['unplanned_done']}")
    elif r["planned_undone"]:
        failures.append(f"[3] creep: undone should be empty, got {r['planned_undone']}")
    else:
        print(f"  [3] unplanned_done       ✓  (TASK-003 범위 creep, drift_score={r['drift_score']}, band={r['score_band']})")

    # 4) both — planned_undone + unplanned_done
    pre = _handoff(planned=["TASK-2026-08-08-main-001 alpha", "TASK-2026-08-08-main-002 beta"])
    post = _handoff(done=[
        "TASK-2026-08-08-main-001 alpha — done",
        "TASK-2026-08-08-main-004 unrelated",
    ])
    r = detect_scope_drift(pre_text=pre, post_text=post)
    if r["planned_undone"] != ["TASK-2026-08-08-main-002"]:
        failures.append(f"[4] both: planned_undone mismatch — {r['planned_undone']}")
    elif r["unplanned_done"] != ["TASK-2026-08-08-main-004"]:
        failures.append(f"[4] both: unplanned_done mismatch — {r['unplanned_done']}")
    elif r["score_band"] != "major":
        failures.append(f"[4] both: band={r['score_band']} (expected major, score=1.0)")
    else:
        print(f"  [4] both                 ✓  (undone=1 + unplanned=1, drift_score={r['drift_score']}, band=major)")

    # 5) missing-section — pre text 는 있지만 *다음에 할 일* 섹션이 없음
    pre = "# Handoff\n\n## 1. 기타\n\n- 내용 없음\n"
    post = _handoff(done=["TASK-2026-08-08-main-001 alpha"])
    r = detect_scope_drift(pre_text=pre, post_text=post)
    if r["planned_done"] or r["planned_undone"]:
        failures.append(f"[5] missing: planned_* should be empty, got done={r['planned_done']}, undone={r['planned_undone']}")
    elif r["unplanned_done"] != ["TASK-2026-08-08-main-001"]:
        failures.append(f"[5] missing: unplanned_done mismatch — {r['unplanned_done']}")
    elif not any("not found" in w for w in r["warnings"]):
        failures.append(f"[5] missing: warning 'not found' missing, got {r['warnings']}")
    else:
        print(f"  [5] missing-section      ✓  (warning 'not found' emit, 모두 unplanned 처리)")

    # 6) no-pre — pre_text=None
    post = _handoff(done=["TASK-2026-08-08-main-001", "TASK-2026-08-08-main-002"])
    r = detect_scope_drift(pre_text=None, post_text=post)
    if r["planned_done"] or r["planned_undone"]:
        failures.append(f"[6] no-pre: planned_* should be empty, got done={r['planned_done']}, undone={r['planned_undone']}")
    elif r["unplanned_done"] != ["TASK-2026-08-08-main-001", "TASK-2026-08-08-main-002"]:
        failures.append(f"[6] no-pre: unplanned_done mismatch — {r['unplanned_done']}")
    elif r["score_band"] != "major":
        failures.append(f"[6] no-pre: band={r['score_band']} (expected major, score=inf)")
    elif not any("pre_text is None" in w for w in r["warnings"]):
        failures.append(f"[6] no-pre: warning 'pre_text is None' missing, got {r['warnings']}")
    else:
        print(f"  [6] no-pre               ✓  (warning 'pre_text is None' emit, 모두 unplanned, band=major)")

    # 7) band threshold — score 0.2 → minor / 0.5 → significant / 0.8 → major
    pre = _handoff(planned=[f"TASK-2026-08-08-main-{i:03d} x" for i in range(10)])  # 10 planned
    # 1 undone + 1 unplanned → score = 2/10 = 0.2 → minor
    post = _handoff(done=[
        *(f"TASK-2026-08-08-main-{i:03d} x — done" for i in range(9)),  # 9 done
        "TASK-2026-08-08-main-099 creep",  # 1 unplanned
    ])
    r = detect_scope_drift(pre_text=pre, post_text=post)
    if r["score_band"] != "minor":
        failures.append(f"[7] band: expected minor for score 0.2, got {r['score_band']} (score={r['drift_score']})")
    else:
        print(f"  [7] band threshold       ✓  (planned=10, undone=1+unplanned=1 → score={r['drift_score']}, band=minor)")

    # 추가 sanity — extract_task_ids / extract_section 도 직접 verify
    text = "see TASK-2026-08-08-main-001 and TASK-2026-08-08-foo-002 but not TASK-bad-1"
    ids = extract_task_ids(text)
    if "TASK-2026-08-08-main-001" not in ids or "TASK-2026-08-08-foo-002" not in ids or "TASK-bad-1" in ids:
        failures.append(f"[sanity] extract_task_ids wrong — got {ids}")
    section = extract_section(_handoff(planned=["TASK-X"], done=["TASK-Y"]), "다음에 할 일")
    if "TASK-X" not in section or "TASK-Y" in section:
        failures.append(f"[sanity] extract_section wrong — got {section!r}")
    else:
        print(f"  [sanity] extractors      ✓  (task_ids regex + section boundary 정상)")

    print()
    if failures:
        print(f"FAIL: {len(failures)} case(s) failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL PASS: scope drift detection — 7 case (clean / undone / unplanned / both / missing / no-pre / band + sanity)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
