#!/usr/bin/env python3
"""scope drift detection CLI — §0.8 #3 (TASK-2026-08-08-main-018)

pre handoff (작업 시작 시점) 의 *다음에 할 일* 섹션 TASK-ID + post handoff 의
*최근 완료 작업* + git log 의 TASK-ID 를 비교해 *범위 이탈* 검출. **advisory
default** — 사람 판단 영역 (§5D.4 정합). `--exit-on-drift` 명시 시 non-zero.

## 사용법

```bash
# default: post handoff (REPO_ROOT/ai-workflow/memory/active/main/session_handoff.md)
# + git log origin/main..HEAD 비교
python3 workflow-source/tools/detect_scope_drift.py

# pre handoff 명시 (작업 시작 commit 의 handoff)
python3 workflow-source/tools/detect_scope_drift.py \
    --pre-handoff /path/to/pre-session_handoff.md

# pre handoff 를 git show 로 (branch 시작점)
python3 workflow-source/tools/detect_scope_drift.py \
    --pre-commit origin/main

# git range 명시
python3 workflow-source/tools/detect_scope_drift.py \
    --git-range "origin/main..HEAD"

# CI 용 — drift 발견 시 non-zero exit
python3 workflow-source/tools/detect_scope_drift.py --exit-on-drift
```

Cross-ref: `core/multi_workspace_orchestration.md` §0.8 #3 / §5B.1 (TASK-018).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.drift_detection import (  # noqa: E402
    TITLE_SIMILARITY_THRESHOLD,
    detect_scope_drift,
    detect_title_drift,
    extract_section,
    generate_title_drift_prompt,
)


DEFAULT_POST_HANDOFF = (
    REPO_ROOT / "ai-workflow" / "memory" / "active" / "main" / "session_handoff.md"
)
DEFAULT_PRE_COMMIT = "origin/main"
DEFAULT_GIT_RANGE = "origin/main..HEAD"


def _git_show(commit: str, path: str, cwd: Path) -> str | None:
    """``git show <commit>:<path>`` 의 stdout. 실패 시 None.

    §0.8 #3 — pre handoff 의 *canonical source* 는 *작업 시작 commit* 의 handoff.
    branch 시작 commit (또는 사용자가 명시한 commit) 의 handoff 본문을 가져온다.
    """
    try:
        result = subprocess.run(
            ["git", "show", f"{commit}:{path}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not result.stdout:
        return None
    return result.stdout


def _git_log(range_spec: str, cwd: Path) -> str:
    """``git log <range>`` 의 commit message 들. 실패 시 빈 string."""
    try:
        result = subprocess.run(
            ["git", "log", "--pretty=format:%s%n%b", range_spec],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout


def _print_human(payload: dict) -> None:
    counts = payload.get("counts", {})
    print(f"  drift_score: {payload.get('drift_score'):.3f}  band: {payload.get('score_band')}")
    print(f"  counts: planned={counts.get('planned')} done={counts.get('done')} "
          f"planned_done={counts.get('planned_done')} planned_undone={counts.get('planned_undone')} "
          f"unplanned_done={counts.get('unplanned_done')}")
    for w in payload.get("warnings", []):
        print(f"  ⚠️  {w}")
    if payload.get("planned_done"):
        print(f"  ✓ planned_done: {', '.join(payload['planned_done'])}")
    if payload.get("planned_undone"):
        print(f"  ✗ planned_undone (놓친 일): {', '.join(payload['planned_undone'])}")
    if payload.get("unplanned_done"):
        print(f"  ⚠ unplanned_done (범위 creep): {', '.join(payload['unplanned_done'])}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="detect scope drift between handoff pre/post (dual mode CLI)")
    p.add_argument("--pre-handoff", type=Path, help="pre handoff 파일 경로 (생략 시 --pre-commit 의 git show 사용)")
    p.add_argument("--pre-commit", default=DEFAULT_PRE_COMMIT,
                   help=f"pre handoff 의 git commit (default: {DEFAULT_PRE_COMMIT})")
    p.add_argument("--post-handoff", type=Path, default=DEFAULT_POST_HANDOFF,
                   help=f"post handoff 파일 경로 (default: {DEFAULT_POST_HANDOFF})")
    p.add_argument("--git-range", default=DEFAULT_GIT_RANGE,
                   help=f"git log 범위 (default: '{DEFAULT_GIT_RANGE}')")
    p.add_argument("--json", action="store_true", help="JSON 출력")
    p.add_argument("--exit-on-drift", action="store_true", help="drift 발견 시 non-zero exit (CI/pre-merge)")
    # v2 (TASK-023): 같은 TASK-ID 인데 제목이 달라진 경우
    p.add_argument("--emit-title-prompt", action="store_true",
                   help="title drift 후보에 대한 LLM 판정 prompt 를 출력 (advisory)")
    p.add_argument("--title-threshold", type=float, default=None,
                   help=f"title 유사도 임계값 (default: {TITLE_SIMILARITY_THRESHOLD})")
    p.add_argument("--exit-on-title-drift", action="store_true",
                   help="title drift 후보가 있으면 non-zero exit")
    args = p.parse_args(argv)

    # pre handoff 결정: --pre-handoff 가 있으면 그 파일, 없으면 git show.
    if args.pre_handoff and args.pre_handoff.is_file():
        pre_text = args.pre_handoff.read_text(encoding="utf-8")
    else:
        pre_path = str(args.pre_handoff) if args.pre_handoff else str(DEFAULT_POST_HANDOFF)
        # path 를 REPO_ROOT 기준으로 정규화 (hand off 는 항상 REPO_ROOT 안)
        rel_path = pre_path
        try:
            # 절대 경로면 REPO_ROOT 기준 상대로
            if Path(pre_path).is_absolute():
                rel_path = str(Path(pre_path).resolve().relative_to(REPO_ROOT))
        except ValueError:
            rel_path = pre_path
        pre_text = _git_show(args.pre_commit, rel_path, REPO_ROOT) or ""

    post_text = ""
    if args.post_handoff.is_file():
        post_text = args.post_handoff.read_text(encoding="utf-8")

    git_log_text = _git_log(args.git_range, REPO_ROOT)

    payload = detect_scope_drift(
        pre_text=pre_text,
        post_text=post_text,
        git_log_text=git_log_text,
    )

    # 임계값을 바꿨으면 title drift 만 다시 계산한다 (v1 판정은 영향 없음).
    if args.title_threshold is not None:
        payload["title_drift"] = detect_title_drift(
            extract_section(pre_text, "다음에 할 일"),
            extract_section(post_text, "최근 완료 작업"),
            threshold=args.title_threshold,
        )

    title_drift = payload.get("title_drift", {})

    if args.emit_title_prompt:
        prompt = generate_title_drift_prompt(title_drift)
        print(prompt if prompt else "# (title drift 후보 없음)")
        return 1 if (args.exit_on_title_drift and title_drift.get("suspect_count")) else 0

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_human(payload)
        suspects = [p for p in title_drift.get("pairs", []) if p.get("suspect")]
        if suspects:
            print()
            print(f"title drift 후보 {len(suspects)}건 "
                  f"(비교 {title_drift.get('compared')}건, 임계 {title_drift.get('threshold')}):")
            for pair in suspects:
                print(f"  - {pair['task_id']} (similarity {pair['similarity']})")
                print(f"      계획: {pair['pre_title']}")
                print(f"      완료: {pair['post_title']}")
            print("  → 판정 prompt: --emit-title-prompt (advisory, 자동 적용 ❌)")

    if args.exit_on_drift and (payload["planned_undone"] or payload["unplanned_done"]):
        return 1
    if args.exit_on_title_drift and title_drift.get("suspect_count"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
