#!/usr/bin/env python3
"""bootstrap 채널의 daily backlog 가 **현행 레이아웃**인가 (TASK-2026-08-24-main-003).

## 왜 필요한가

bootstrap 은 `templates/daily_backlog_template.md`(v0.14.0 **이전** 레이아웃)를
읽어 치환했다. 그래서 새로 bootstrap 한 프로젝트는 **첫날부터 어긋난 파일**을
받았다:

- **표기가 갈렸다** — bootstrap 은 한국어 라벨(`- 상태:`)을, 도구는 영어
  (`task_label` → `- Status:`)를 썼다. 같은 프로젝트 안에서 두 표기가 동시에
  생겼다. 이 저장소의 "혼합 표기" 문제가 레거시가 아니라 **매 bootstrap 마다
  새로 만들어지고** 있었던 것이다.
- **레이아웃이 겹쳤다** — 파일 머리에 임베드 task(`## 1. TASK-XXX` + 계획/실행/
  검증 절)가 있고 `wk backlog-update` 는 그 아래에 append-only 인덱스를 덧붙인다.
  한 파일에 두 형식이 쌓였다.
- **씨앗 task 가 파싱 불가였다** — 기본 ID `TASK-001` 은
  `project_docs.TASK_ID_PATTERN`(`TASK-YYYY-MM-DD-<slug>-NNN`)과 안 맞고,
  가리켜진 `tasks/` 파일도 없었다. 인덱스가 빈 곳을 가리켰다.

원인은 **사본**이다. 도구는 `workflow_writes` 의 정본 작성기로 쓰는데 bootstrap 은
따로 둔 템플릿으로 썼다. 사본은 갈라진다.

## 판정 규칙

1. bootstrap 이 내는 daily 파일이 **정본 작성기 출력과 같은 구조**다.
2. 배포되는 템플릿(`templates/daily_backlog_template.md`)도 같은 구조다 —
   소비자가 참고 자료로 받는 사본이므로 여기서도 갈라지면 안 된다.
3. 옛 레이아웃의 표식이 남아 있지 않다.
4. 씨앗 task 의 ID 가 `TASK_ID_PATTERN` 과 맞고, 가리켜진 task 파일이 실재한다.

**날짜 줄은 비교에서 제외한다.** `최종 수정일` 은 `date.today()` 라 매일 바뀐다 —
리터럴로 물면 이 검사가 내일 red 가 되고, 그것은 계약이 아니라 그 시점 상수를
지키는 것이다.
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/templates/*",
    "workflow-source/workflow_kit/*",
)

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.bootstrap_lib.renderers import (  # noqa: E402
    initial_task_id,
    render_daily_backlog,
    render_initial_task_file,
)
from workflow_kit.common.project_docs import TASK_ID_PATTERN  # noqa: E402
from workflow_kit.common.workflow_writes import (  # noqa: E402
    daily_index_entry_lines,
    render_daily_backlog_header,
)

TEMPLATE = SOURCE_ROOT / "templates" / "daily_backlog_template.md"

#: 옛 레이아웃(v0.14.0 이전)의 표식. 하나라도 남아 있으면 갈라진 것이다.
LEGACY_MARKERS = (
    "작업 백로그",          # `# YYYY-MM-DD 작업 백로그` 머리말
    "### 1.1",              # 임베드 task 의 계획/실행/검증 절
    "- 모드:",
    "- 상태:",              # 한국어 task 필드 라벨 (문서 메타 `- 상태:` 와 구분해 아래에서 처리)
)

FAILURES: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case}{(' — ' + detail) if detail else ''}")
        FAILURES.append(case)


def _args() -> argparse.Namespace:
    return argparse.Namespace(
        today="2026-01-02",
        project_slug="sampleproj",
        project_name="Sample Proj",
        owner="TODO",
        initial_task_id="TASK-001",  # 옛 기본값 — 파생으로 대체돼야 한다
        initial_task_name="표준 AI 워크플로우 초기 도입",
        initial_task_status="planned",
        initial_priority="high",
    )


def _structure(text: str) -> list[str]:
    """비교용 구조. 날짜 줄은 값이 매일 바뀌므로 제외한다."""
    out = []
    for line in text.splitlines():
        if line.startswith("- 최종 수정일:"):
            continue
        if line.strip():
            out.append(line.rstrip())
    return out


def test_bootstrap_daily_matches_canonical_writer() -> None:
    args = _args()
    rendered = render_daily_backlog(args, {})
    expected = render_daily_backlog_header(backlog_path=Path(f"{args.today}.md"))
    expected += daily_index_entry_lines(
        task_id=initial_task_id(args),
        title=args.initial_task_name,
        kind="generic",
        status=args.initial_task_status,
    )
    got, want = _structure(rendered), _structure("\n".join(expected))
    _record(
        "test_bootstrap_daily_matches_canonical_writer",
        got == want,
        f"bootstrap 출력이 정본 작성기와 다르다\n  got : {got}\n  want: {want}",
    )


def test_shipped_template_matches_canonical_writer() -> None:
    if not TEMPLATE.is_file():
        _record("test_shipped_template_matches_canonical_writer", False, f"템플릿 부재: {TEMPLATE}")
        return
    header = _structure("\n".join(render_daily_backlog_header(backlog_path=Path("YYYY-MM-DD.md"))))
    body = _structure(TEMPLATE.read_text(encoding="utf-8"))
    missing = [line for line in header if line not in body]
    _record(
        "test_shipped_template_matches_canonical_writer",
        not missing,
        f"배포 템플릿에 없는 정본 줄: {missing}",
    )


def test_no_legacy_layout_markers() -> None:
    args = _args()
    surfaces = {
        "bootstrap 출력": render_daily_backlog(args, {}),
        "배포 템플릿": TEMPLATE.read_text(encoding="utf-8") if TEMPLATE.is_file() else "",
    }
    problems: list[str] = []
    for name, text in surfaces.items():
        for marker in LEGACY_MARKERS:
            # 문서 메타의 `- 상태: stable (...)` 은 정본 머리말이 쓰는 줄이라 제외한다.
            if marker == "- 상태:" and "- 상태: stable" in text:
                continue
            if marker in text:
                problems.append(f"{name}: 옛 레이아웃 표식 {marker!r}")
    _record("test_no_legacy_layout_markers", not problems, "; ".join(problems))


def test_seed_task_is_parseable_and_present() -> None:
    args = _args()
    task_id = initial_task_id(args)
    problems: list[str] = []
    if not re.fullmatch(TASK_ID_PATTERN, task_id):
        problems.append(
            f"씨앗 task ID 가 TASK_ID_PATTERN 과 안 맞는다: {task_id!r} — "
            "kit 자신의 파서가 못 읽는 ID 를 심는 셈이다"
        )
    index = render_daily_backlog(args, {})
    if task_id not in index:
        problems.append("daily index 가 씨앗 task 를 안 가리킨다")
    body = render_initial_task_file(args)
    if f"id: {task_id}" not in body:
        problems.append("씨앗 task 파일의 frontmatter id 가 index 와 다르다")
    if f"status: {args.initial_task_status}" not in body:
        problems.append("씨앗 task 파일의 frontmatter status 가 없다")
    _record("test_seed_task_is_parseable_and_present", not problems, "; ".join(problems))


def main() -> int:
    cases = [
        test_bootstrap_daily_matches_canonical_writer,
        test_shipped_template_matches_canonical_writer,
        test_no_legacy_layout_markers,
        test_seed_task_is_parseable_and_present,
    ]
    for case in cases:
        case()
    total = len(cases)
    print(f"\n{total - len(FAILURES)}/{total} passed")
    if FAILURES:
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
