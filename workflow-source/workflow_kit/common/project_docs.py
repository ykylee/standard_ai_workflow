"""Project workflow document parsers shared across skill prototypes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from workflow_kit.common.markdown import markdown_targets
from workflow_kit.common.text import (
    extract_list_after_label,
    extract_named_section_bullets,
    extract_section_value,
    iter_lines,
    normalize_inline_code,
)

# task 의 진행 상태 어휘 — **여기가 단일 출처다**. CLAUDE.md / global_workflow_standard
# 이 선언하는 네 값이고, 아래 정규식들은 전부 이걸로 조립한다. 예전에는 같은 목록이
# `STATUS_RE` 와 `WORK_STATUS_RE` 에 각각 리터럴로 박혀 있었고, builder 는 셋 중 어느
# 것도 참조하지 않은 채 `in_progress`/`blocked`/`done` 만 비교해서 **그 밖의 값을 조용히
# 버렸다** (실측: `status: recorded` 3건이 아무 목록에도 안 들어간 뒤 daily index
# fallback 에 의해 done 으로 되살아났다).
TASK_STATUSES: tuple[str, ...] = ("planned", "in_progress", "blocked", "done")
_STATUS_ALT = "|".join(TASK_STATUSES)

# `status` 는 **진행 상태 축**이고, 여기부터는 **출처 축**이다. 둘을 한 칸에 넣으면 둘 다
# 망가진다 — `migrate_active_to_appendonly.py` 가 어휘 밖의 `recorded` 를 status 칸에
# 적고 있었는데, 그 값이 뜻한 것은 진행 상태가 아니라 "legacy work_backlog.md 에서
# 이관됐고 진행 상태는 모른다" 는 출처 사실이었다. 출처는 `provenance` 로 따로 적고,
# 진행 상태는 **판정 근거가 있을 때만** 적는다.
TASK_PROVENANCE_MIGRATED_LEGACY = "migrated-legacy"

# frontmatter 에 `status:` 줄이 아예 없을 때 `unknown_status_items` 에 붙는 표식.
# "판정하지 않았다" 와 "어휘 밖의 값을 적었다" 는 다른 사실이라 구분해서 드러낸다.
MISSING_STATUS_MARKER = "<미기재>"

# "최근 완료" 파생물의 상한 — **여기가 단일 출처다**.
#
# 이 값을 아는 자리가 셋이다: 쓰는 쪽(`sync_handoff_status` 가 handoff §4 에 append),
# 조립하는 쪽(`build_workflow_state_payload` 의 `recent_done_items`), 보는 쪽
# (`linter` 의 `handoff_bloat`). 상한이 조립 쪽에만 있어서 **쓰는 쪽은 무한히 쌓았고**,
# 보는 쪽은 리터럴 `10` 을 따로 들고 있었다. 그래서 close-out 마다 handoff 가 11이 되고
# 사람이 한 줄 지우는 수작업이 반복됐다 (2026-07-28 / 2026-07-31 연속 2회 실측).
# 상한을 아는 곳은 전부 여기를 import 한다 — 리터럴을 다시 적지 않는다.
RECENT_DONE_ITEMS_CAP = 10

#: handoff §1 이 들고 있을 **기준선 줄** 상한 (`현재/직전/그 이전 기준선`).
#:
#: 완료 목록 상한(:data:`RECENT_DONE_ITEMS_CAP`)과 **다루는 방식이 다르다.** 완료 항목은
#: SSOT 가 `backlog/tasks/` 에 따로 있어 목록에서 잘라도 사실이 사라지지 않는다. 기준선
#: 줄은 그 산문이 **다른 어디에도 없다** — 그래서 자르면 안 되고 `baselines.md` 로
#: **이관**한다. 상한만 두고 버리면 세션 이력이 조용히 지워진다.
#:
#: 실측(2026-08-14): 기준선 37줄이 handoff 41,880자 중 27,502자(66%)였고 세션마다
#: 평균 785자씩 단조 증가했다. 그 전부가 매 세션 시작에 읽힌다.
BASELINE_ITEMS_CAP = 4

#: 롤오프된 기준선이 쌓이는 파일 이름 (브랜치 네임스페이스 안, handoff 옆).
BASELINES_FILENAME = "baselines.md"

#: 기준선 줄의 라벨 — 앞이 최신이다.
BASELINE_LABELS: tuple[str, ...] = ("현재 기준선", "직전 기준선", "그 이전 기준선")

#: task SSOT 본문 라벨의 **정본**. 의미 key → 현재 쓰는 라벨.
#:
#: 리터럴이 `backlog_update` / `workflow_writes` / `read_only_bundle` 에 흩어져 있었다
#: (2026-08-14 조사: 12개 라벨이 46곳). 라벨은 곧 파싱 계약이라, 흩어진 채로는
#: 바꿀 수가 없다 — 한 곳만 고치면 나머지가 조용히 갈라진다.
TASK_FIELD_LABELS: dict[str, str] = {
    "status": "상태",
    "priority": "우선순위",
    "owner": "담당",
    "host_name": "호스트명",
    "host_ip": "호스트 IP",
    "affected_documents": "영향 문서",
    "summary": "작업 내용",
    "done_criteria": "완료 기준",
    "progress": "진행 현황",
    "next_step": "다음 세션 시작 포인트",
    "risks": "남은 리스크",
    "result": "작업 결과",
    "validation": "검증 결과",
    "follow_up": "후속 작업",
}

#: 읽을 때 **받아들이는** 표기들. 정본이 바뀌어도 옛 문서를 계속 읽기 위한 창구다.
#:
#: 영어 표기를 미리 넣어 둔다 — 전환은 아직 하지 않지만(소비자 저장소의 리더가
#: 먼저 이 표를 갖고 있어야 한다), **리더가 먼저 두 표기를 받는 것**이 deprecation
#: 창구의 첫 단계다. 쓰는 쪽을 먼저 바꾸면 옛 리더가 새 문서를 못 읽는다.
TASK_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "status": ("상태", "Status"),
    "priority": ("우선순위", "Priority"),
    "owner": ("담당", "Owner"),
    "host_name": ("호스트명", "Host"),
    "host_ip": ("호스트 IP", "Host IP"),
    "affected_documents": ("영향 문서", "Affected documents"),
    "summary": ("작업 내용", "Description"),
    "done_criteria": ("완료 기준", "Completion criteria"),
    "progress": ("진행 현황", "Progress"),
    "next_step": ("다음 세션 시작 포인트", "Next session starting point"),
    "risks": ("남은 리스크", "Remaining risks"),
    "result": ("작업 결과", "Result"),
    "validation": ("검증 결과", "Verification"),
    "follow_up": ("후속 작업", "Follow-up"),
}


def task_label(key: str) -> str:
    """의미 key → 현재 정본 라벨. 없는 key 는 즉시 실패한다 (오타를 숨기지 않는다)."""
    return TASK_FIELD_LABELS[key]


def is_empty_label_line(line: str, key: str) -> bool:
    """`- <label>:` 만 있고 값이 없는 줄인가. **별칭도 인식**한다.

    값 유무를 리터럴 비교로 보던 자리가 있었다 — 영어 표기로 적힌 문서에서는
    그 비교가 항상 거짓이라, "비어 있으니 채운다" 분기가 조용히 안 돌았다.
    """
    stripped = line.strip()
    return any(stripped == f"- {alias}:" for alias in task_label_aliases(key))


def task_label_aliases(key: str) -> tuple[str, ...]:
    """읽을 때 받아들일 표기들. 정본이 항상 첫 번째다."""
    canonical = TASK_FIELD_LABELS[key]
    rest = tuple(a for a in TASK_FIELD_ALIASES.get(key, ()) if a != canonical)
    return (canonical, *rest)


# Standard Regexes
# 본문 상태 줄 — 정본과 별칭을 모두 받는다 (frontmatter 가 우선이고 이건 fallback).
_STATUS_LABEL_ALT = "|".join(
    re.escape(a) for a in TASK_FIELD_ALIASES["status"]
)
STATUS_RE = re.compile(rf"- (?:{_STATUS_LABEL_ALT}):\s*({_STATUS_ALT})\s*$")
MODE_RE = re.compile(r"- 모드:\s*(Analysis|Requirements|Design|Planning|Implementation|Refactoring)\s*$")

# 정본 task ID 패턴 — `TASK-<date>[-<branch-slug>]-<NNN>` (v1.0.0 branch-scoped).
# 브랜치 slug 는 소문자를 포함할 수 있으므로(`main`, `feature-x`) 문자집합을 대문자로
# 제한하면 안 된다. slug 없는 legacy(`TASK-2026-07-20-001`)도 같은 패턴으로 매칭된다.
# **여기가 단일 출처다** — builder / layout check / skill 이 각자 정규식을 들고 있으면
# 조용히 갈라진다 (실제로 갈라져서 slug ID 가 daily index 에서 인식되지 않았다).
TASK_ID_PATTERN = r"TASK-\d{4}-\d{2}-\d{2}(?:-[A-Za-z0-9._-]+?)?-\d{3}"
TASK_HEADER_RE = re.compile(r"^#{1,2}\s+(TASK-[A-Za-z0-9._-]+)\s+(.+)$")

# 순번 채번용 분해 정규식 — (date, branch-slug, NNN). `TASK-021` 같은 초기 legacy 도
# 받아야 하므로 `TASK_ID_PATTERN` 보다 관대하다. **문법의 정의는 여기 한 곳**이고,
# backlog-update 가 이걸 import 한다 (skill 이 자기 사본을 들고 있어서 갈라졌었다).
TASK_ID_CAPTURE_RE = re.compile(r"^TASK-(?:(\d{4}-\d{2}-\d{2})-)?(?:(.+?)-)?(\d{1,3})$")
# handoff 의 `- <ID> <제목>: <상태>` 줄에서 쓰는 **작업 항목 ID** 문법.
#
# v1.0.2 정정: 이전에는 `[A-Z0-9-]+` 라 **대문자만** 받았는데, `TASK_ID_PATTERN` 은
# branch slug 세그먼트에 `[A-Za-z0-9._-]` 를 허용한다. 그래서 `TASK-2026-07-27-main-001`
# 처럼 *정본 문법에 맞는 ID* 를 handoff 의 Work Status 줄에서 인식하지 못했다. 같은
# 규약의 두 정규식이 갈라져 있던 것이다 (§2.24 가 등록한 부류와 같은 모양).
#
# 셋의 관계: `TASK_ID_PATTERN`(정본 문법) ⊂ `WORK_ITEM_ID_PATTERN`(느슨, WF- 와 legacy
# `TASK-021` 까지) 이고, `TASK_ID_CAPTURE_RE` 는 채번용 분해다.
WORK_ITEM_ID_PATTERN = r"(?:TASK|WF)-[A-Za-z0-9._-]+"
WORK_STATUS_RE = re.compile(
    rf"^-\s+({WORK_ITEM_ID_PATTERN})\s+(.+?):\s*({_STATUS_ALT})\s*$"
)


class WorkflowDocParser:
    """Base parser for workflow markdown documents."""
    def __init__(self, path: Path):
        self.path = path
        # 부재 파일에서 즉시 터지지 않는다. `_task_lines_for_backlog` 의
        # "index 가 없으면 tasks/ 를 글롭한다" fallback 은 생성자가 먼저 죽는 바람에
        # **도달 불가능한 죽은 코드**였다 (2026-08-14 실측). 부재는 여기서 빈 줄로
        # 두고, 그 사실이 필요한 곳에서 판단한다.
        self.lines = iter_lines(path) if path.exists() else []
        self.warnings: list[str] = []

    def get_value(self, label: str, required: bool = False) -> str | None:
        val = extract_section_value(self.lines, label)
        if val is None and required:
            self.warnings.append(f"필수 섹션 누락: `{label}` ({self.path.name})")
        return val

    def get_list(self, label: str) -> list[str]:
        return extract_list_after_label(self.lines, label)

    def get_named_bullets(self, title: str) -> list[str]:
        return extract_named_section_bullets(self.lines, title)

    def _section_lines(self, title: str) -> list[str]:
        heading = f"## {title}"
        collecting = False
        section: list[str] = []
        for line in self.lines:
            stripped = line.rstrip()
            if stripped.startswith("## "):
                if collecting:
                    break
                collecting = stripped == heading
                continue
            if collecting:
                section.append(line)
        return section


class HandoffParser(WorkflowDocParser):
    """Parser for session_handoff.md."""
    def parse(self) -> dict[str, object]:
        current_focus = self._first_bullet_or_text(self._section_lines("Current Focus"))
        work_status = self._work_status_items(self._section_lines("Work Status"))
        data = {
            "current_baseline": self.get_value("현재 기준선", required=current_focus is None) or current_focus,
            "current_axis": self.get_value("현재 주 작업 축", required=current_focus is None) or current_focus,
            "recent_core_docs": self.get_list("최근 핵심 기준 문서"),
            "in_progress_items": self.get_list("현재 `in_progress` 작업") or work_status["in_progress_items"],
            "blocked_items": self.get_list("현재 `blocked` 작업") or work_status["blocked_items"],
            "recent_done_items": self.get_list("최근 완료 작업 목록") or work_status["done_items"],
            "constraints": self.get_value("주요 제약"),
            "next_documents": [self.path.parent / target for target in markdown_targets(self.path)],
        }
        return {**data, "warnings": self.warnings}

    def _first_bullet_or_text(self, lines: list[str]) -> str | None:
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("- "):
                return normalize_inline_code(stripped[2:].strip())
            return normalize_inline_code(stripped)
        return None

    def _work_status_items(self, lines: list[str]) -> dict[str, list[str]]:
        items: dict[str, list[str]] = {"in_progress_items": [], "blocked_items": [], "done_items": []}
        for line in lines:
            match = WORK_STATUS_RE.match(line.strip())
            if not match:
                continue
            task_id, title, status = match.groups()
            item = f"{task_id} {title}"
            if status == "in_progress":
                items["in_progress_items"].append(item)
            elif status == "blocked":
                items["blocked_items"].append(item)
            elif status == "done":
                items["done_items"].append(item)
        return items


class BacklogParser(WorkflowDocParser):
    """Parser for daily backlog documents."""
    def parse(self) -> dict[str, object]:
        lines, warnings = self._task_lines_for_backlog()
        self.lines = lines
        self.warnings.extend(warnings)

        tasks: list[dict[str, str]] = []
        current_task: dict[str, str] | None = None

        for idx, line in enumerate(self.lines):
            stripped = line.strip()
            header_match = TASK_HEADER_RE.match(stripped)
            if header_match:
                if current_task:
                    tasks.append(current_task)
                current_task = {"task_id": header_match.group(1), "title": header_match.group(2)}
                continue

            if current_task is None:
                continue

            status_match = STATUS_RE.match(stripped)
            if status_match:
                current_task["status"] = status_match.group(1)
            elif stripped.startswith("- 상태:") and not STATUS_RE.match(stripped):
                self.warnings.append(f"잘못된 상태 형식 (L{idx+1}): `{stripped}`")

            mode_match = MODE_RE.match(stripped)
            if mode_match:
                current_task["mode"] = mode_match.group(1)

        if current_task:
            tasks.append(current_task)

        return {
            "tasks": tasks,
            "in_progress_items": [f"{task['task_id']} {task['title']}" for task in tasks if task.get("status") == "in_progress"],
            "blocked_items": [f"{task['task_id']} {task['title']}" for task in tasks if task.get("status") == "blocked"],
            "done_items": [f"{task['task_id']} {task['title']}" for task in tasks if task.get("status") == "done"],
            "warnings": self.warnings,
        }

    def parse_task_entries(self) -> list[dict[str, str | None]]:
        lines, _warnings = self._task_lines_for_backlog()
        self.lines = lines
        tasks: list[dict[str, str | None]] = []
        current_task: dict[str, str | None] | None = None
        for idx, line in enumerate(self.lines):
            stripped = line.strip()
            header_match = TASK_HEADER_RE.match(stripped)
            if header_match:
                if current_task:
                    tasks.append(current_task)
                current_task = {"task_id": header_match.group(1), "title": header_match.group(2), "status": None}
                continue
            if current_task is None:
                continue
            status_match = STATUS_RE.match(stripped)
            if status_match:
                current_task["status"] = status_match.group(1)
            mode_match = MODE_RE.match(stripped)
            if mode_match:
                current_task["mode"] = mode_match.group(1)
        if current_task:
            tasks.append(current_task)
        return tasks

    def _task_lines_for_backlog(self) -> tuple[list[str], list[str]]:
        path = self.path
        warnings: list[str] = []
        if not path.exists():
            # task 파일명은 `TASK-<date>[-<slug>]-<NNN>.md` 다. `<stem>_*` 로 찾던
            # 옛 패턴은 **아무것도 매칭하지 않았다** — 그래서 이 fallback 은 있으나
            # 마나였고, 그 사실이 드러난 적이 없다 (조용한 0).
            task_files = sorted((path.parent / "tasks").glob(f"TASK-{path.stem}*.md"))
            if not task_files:
                return [], [f"백로그 파일({path.name}) 및 태스크 파일을 찾을 수 없습니다."]
            lines: list[str] = []
            for task_file in task_files:
                lines.extend(_task_lines_with_frontmatter_status(task_file))
                lines.append("")
            return lines, warnings

        lines = path.read_text(encoding="utf-8").splitlines()
        has_inline_header = any(TASK_HEADER_RE.match(line.strip()) for line in lines)
        linked_task_paths = self._linked_task_paths(path)
        if linked_task_paths and not has_inline_header:
            lines = []
            for task_file in linked_task_paths:
                lines.extend(_task_lines_with_frontmatter_status(task_file))
                lines.append("")
            return lines, warnings

        if not linked_task_paths and not has_inline_header:
            # 세 번째 방언 — index 가 task 를 **인라인 불릿**으로만 담고 `path:` 도
            # `# TASK-` 헤더도 없다 (legacy work_backlog 분할 산출물). 여기서 그냥
            # 돌려주면 task 0개가 되고, 그 0 은 "그 날 한 일이 없다" 로 읽힌다.
            # 파일은 `tasks/<index-stem>-*.md` 에 그대로 있으므로 그것을 집는다 —
            # index 부재 시의 fallback 과 **같은 규칙**이다.
            fallback = sorted((path.parent / "tasks").glob(f"TASK-{path.stem}*.md"))
            if fallback:
                lines = []
                for task_file in fallback:
                    lines.extend(_task_lines_with_frontmatter_status(task_file))
                    lines.append("")
        return lines, warnings

    #: daily index 가 task 파일을 가리키는 **두 방언**.
    #:
    #: 신형은 마크다운 링크(`path: [`./tasks/X.md`](./tasks/X.md)`), 구형(v0.14.0
    #: 마이그레이션 산출물)은 백틱 경로(``path: `backlog/tasks/X.md` ``)다. 링크만
    #: 보던 리더는 구형 index 에서 **task 를 0개로 읽었다** — 파일은 그대로 있는데
    #: 어느 목록에도 안 나타난다 (2026-08-14 실측: `active/main` 의 20개 index 가
    #: 그 상태였다). 조용한 0 은 "그 날 한 일이 없다" 로 읽힌다.
    _BACKTICK_PATH_RE = re.compile(r"^\s*-?\s*path:\s*`([^`]+)`", re.M)

    def _linked_task_paths(self, path: Path) -> list[Path]:
        task_paths: list[Path] = []
        seen: set[Path] = set()

        def _add(raw: str) -> None:
            candidate = (path.parent / raw).resolve()
            if not candidate.exists():
                # 구형은 저장소 상대(`backlog/tasks/X.md`)로 적히기도 한다.
                candidate = (path.parent.parent / raw).resolve()
            if candidate.exists() and candidate.parent.name == "tasks" and candidate not in seen:
                seen.add(candidate)
                task_paths.append(candidate)

        for target in markdown_targets(path):
            _add(target)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return task_paths
        for match in self._BACKTICK_PATH_RE.finditer(text):
            _add(match.group(1).strip())
        return task_paths



_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_FM_STATUS_RE = re.compile(r"^status:\s*(\S+)\s*$", re.M)
_BODY_STATUS_LINE_RE = re.compile(r"^- 상태:")


def _task_lines_with_frontmatter_status(task_file: Path) -> list[str]:
    """task 파일의 줄 목록. **frontmatter `status:` 를 본문보다 우선**한다.

    같은 필드에 소스가 둘이었다 — 아카이브 도구와 축 분리 검사는 frontmatter 를
    읽고, backlog 파서는 본문 `- 상태:` 를 읽었다. 2026-08-14 실측: 277개 중
    **105개(38%)에 본문 줄이 아예 없었고**(legacy 마이그레이션 산출물), 그 task 들은
    파서에게 *상태 없음* 이었다. 불일치는 0건이었지만 **부재가 문제였다.**

    본문을 지우지 않고 frontmatter 값을 본문 형식으로 **앞에 덧대** 준다 —
    `STATUS_RE` 가 먼저 만나는 값이 frontmatter 가 되고, 본문은 그대로 남아
    소비자 저장소의 기존 리더도 계속 동작한다 (2년 compat).
    """
    text = task_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    fm = _FRONTMATTER_RE.match(text)
    if not fm:
        return lines
    status = _FM_STATUS_RE.search(fm.group(1))
    if not status:
        return lines
    # 파서는 뒤에 오는 값으로 덮어쓴다. 그래서 헤더 뒤에 끼워 넣는 것만으로는
    # 부족하고, **본문의 상태 줄을 합성 목록에서 빼야** frontmatter 가 이긴다
    # (디스크의 파일은 건드리지 않는다 — 소비자의 기존 리더는 본문을 계속 본다).
    kept = [ln for ln in lines if not _BODY_STATUS_LINE_RE.match(ln.strip())]
    for i, line in enumerate(kept):
        if TASK_HEADER_RE.match(line.strip()):
            return kept[: i + 1] + [f"- 상태: {status.group(1)}"] + kept[i + 1 :]
    return lines

# Legacy Function Wrappers for Compatibility
def parse_project_profile_core(path: Path) -> dict[str, Any]:
    parser = WorkflowDocParser(path)
    data = {
        "project_name": parser.get_value("프로젝트명", required=True),
        "document_home": parser.get_value("문서 위키 홈"),
        "operations_path": parser.get_value("운영 문서 위치"),
        "backlog_path": parser.get_value("백로그 위치"),
        "handoff_path": parser.get_value("세션 인계 문서 위치"),
        "environment_path": parser.get_value("환경 기록 위치"),
    }
    return {**data, "warnings": parser.warnings}

def parse_project_profile_validation(path: Path) -> dict[str, Any]:
    parser = WorkflowDocParser(path)
    data = {
        "project_name": parser.get_value("프로젝트명"),
        "quick_tests": parser.get_value("빠른 테스트"),
        "isolated_tests": parser.get_value("격리 테스트"),
        "runtime_checks": parser.get_value("UI/API 실행 확인"),
        "validation_points": parser.get_named_bullets("4. 프로젝트 특화 검증 포인트"),
        "exception_rules": parser.get_named_bullets("5. 프로젝트 특화 예외 규칙"),
    }
    return {**data, "warnings": parser.warnings}

def parse_project_profile_session(path: Path) -> dict[str, Any]:
    parser = WorkflowDocParser(path)
    data = {
        "project_name": parser.get_value("프로젝트명", required=True),
        "document_home": parser.get_value("문서 위키 홈"),
        "operations_path": parser.get_value("운영 문서 위치"),
        "backlog_path": parser.get_value("백로그 위치"),
        "handoff_path": parser.get_value("세션 인계 문서 위치"),
        "environment_path": parser.get_value("환경 기록 위치"),
        "quick_test": parser.get_value("빠른 테스트"),
        "constraints": parser.get_value("환경 제약"),
    }
    return {**data, "warnings": parser.warnings}

def parse_project_profile_merge(path: Path) -> dict[str, Any]:
    parser = WorkflowDocParser(path)
    data = {
        "project_name": parser.get_value("프로젝트명"),
        "document_home": parser.get_value("문서 위키 홈"),
        "operations_path": parser.get_value("운영 문서 위치"),
        "backlog_path": parser.get_value("백로그 위치"),
        "handoff_path": parser.get_value("세션 인계 문서 위치"),
        "constraints": parser.get_value("환경 제약"),
        "merge_rule": parser.get_value("병합 규칙"),
    }
    return {**data, "warnings": parser.warnings}

def parse_project_profile_backlog(path: Path) -> dict[str, Any]:
    parser = WorkflowDocParser(path)
    data = {
        "project_name": parser.get_value("프로젝트명"),
        "backlog_path": parser.get_value("백로그 위치"),
        "handoff_path": parser.get_value("세션 인계 문서 위치"),
        "constraints": parser.get_value("환경 제약"),
    }
    return {**data, "warnings": parser.warnings}

def parse_handoff(path: Path) -> dict[str, object]:
    return HandoffParser(path).parse()

def parse_backlog(path: Path) -> dict[str, object]:
    return BacklogParser(path).parse()

def parse_backlog_task_entries(path: Path) -> list[dict[str, str | None]]:
    return BacklogParser(path).parse_task_entries()


def find_latest_backlog_path(index_path: Path) -> Path | None:
    linked_paths = [index_path.parent / target for target in markdown_targets(index_path)]
    if linked_paths:
        return linked_paths[-1]
    # Fallback to date search
    from workflow_kit.common.text import iter_lines
    lines = iter_lines(index_path)
    date_candidates: list[Path] = []
    for line in lines:
        stripped = line.strip()
        if re.search(r"\d{4}-\d{2}-\d{2}\.md", stripped):
            match = re.search(r"(\.?\.?/.*\d{4}-\d{2}-\d{2}\.md)", stripped)
            if match:
                date_candidates.append(index_path.parent / match.group(1))
    return date_candidates[-1] if date_candidates else None
