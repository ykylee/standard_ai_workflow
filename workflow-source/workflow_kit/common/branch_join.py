"""worktree 합류 반영 — 모 브랜치에 병합된 브랜치 네임스페이스의 기록을 **모 브랜치 메모리에** 옮긴다.

## 왜 필요한가 (TASK-2026-10-02-main-004)

110·111차는 worktree 브랜치가 main 에 fast-forward 된 뒤 main 세션이 **손으로** 브랜치 메모리를 강제
아카이브하고 handoff §5 에 "(110차 worktree 합류) …" 포인터를 적었다 (`84761318` · `3c31ebb0`). 그 손일이
없으면: worktree 의 task 는 `archived/` 로 들어가 main 집계에서 사라지고(archived/ 는 아무 집계도 안 본다),
열린 task 는 아카이브를 막고, 이어받은 task 의 되돌려 적기(main-001)는 브랜치가 삭제된 뒤에만 돈다.

## 무엇을 하는가 (아카이브 이동 **전에**, 모 브랜치 체크아웃에서)

1. 이어받은 task 중 고친 것을 원본에 되돌려 적고(:func:`branch_inheritance.apply_write_back`), 모 브랜치
   handoff 의 진행·차단·완료 목록을 그 status 로 옮긴다.
2. 브랜치 자체의 **열린** task 를 같은 ID 로 모 브랜치 네임스페이스에 이월한다 — frontmatter 맨 앞에
   ``merged_from: <branch>@<sha>``, 브랜치 쪽 사본에는 ``carried_over_to`` (아카이브의 미완료 판정 면제 축).
3. 브랜치 자체의 **완료** task 를 모 브랜치 handoff "최근 완료" 에 올린다 (자동 seed 사건 task 는 뺀다).
4. 모 브랜치 handoff §5 맨 앞에 합류 줄 하나, `sessions/merge_<slug>_<date>.md` 에 합류 기록.

모 브랜치는 **이 체크아웃의 현재 브랜치**이고, 호출자(archive 도구)가 그것이 기본 브랜치일 때만 부른다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from workflow_kit.common import branch_inheritance as inherit
from workflow_kit.common.paths import HANDOFF_FILENAME, path_in_active

MERGED_FROM_KEY = "merged_from"
#: archive 도구의 이관 축 (`archive_branch_memory.CARRIED_OVER_KEY`) — 같은 키를 쓴다.
CARRIED_OVER_KEY = "carried_over_to"
#: 자동 seed 사건 task 제목 접두 — 합류 기록의 '완료' 로 올리지 않는다 (업무가 아니라 사건이다).
SEED_TITLE_PREFIX = "브랜치 네임스페이스 자동 seed"
HANDOFF_NAME = HANDOFF_FILENAME  # 파일명 정본은 `common.paths` — 별칭만 둔다
BASELINE_EXCERPT_CHARS = 240
_LIST_STATES = ("in_progress", "blocked", "done")


@dataclass
class JoinPlan:
    carry: list[str] = field(default_factory=list)      # 이월할 열린 자체 task
    clashes: list[str] = field(default_factory=list)    # 모 브랜치에 같은 ID 가 있어 이월 불가
    done: list[str] = field(default_factory=list)       # 최근 완료로 올릴 자체 task


def _own_tasks(branch_dir: Path) -> list[tuple[Path, str]]:
    tasks_dir = branch_dir / "backlog" / "tasks"
    out = []
    for path in sorted(tasks_dir.glob("TASK-*.md")) if tasks_dir.is_dir() else []:
        text = path.read_text(encoding="utf-8")
        if inherit.inheritance_of(text) is None and not inherit._frontmatter_value(text, CARRIED_OVER_KEY):
            out.append((path, text))
    return out


def plan_join(branch_dir: Path, parent_dir: Path) -> JoinPlan:
    plan = JoinPlan()
    for path, text in _own_tasks(branch_dir):
        status = inherit._frontmatter_value(text, "status")
        if status == "done":
            if not inherit.task_title(text, path.stem).startswith(SEED_TITLE_PREFIX):
                plan.done.append(path.stem)
        elif (parent_dir / "backlog" / "tasks" / path.name).exists():
            plan.clashes.append(path.stem)
        else:
            plan.carry.append(path.stem)
    return plan


@dataclass
class JoinReport:
    branch: str
    origin: str
    written_back: list[str] = field(default_factory=list)
    carried: list[str] = field(default_factory=list)
    done: list[str] = field(default_factory=list)
    record_path: str = ""


def _label(text: str, task_id: str) -> str:
    return f"{task_id} {inherit.task_title(text, task_id)}"


def _sync_lists(handoff: Path, label: str, status: str) -> None:
    from workflow_kit.common.workflow_writes import sync_handoff_status  # noqa: PLC0415 — 순환 회피

    if status in _LIST_STATES and handoff.is_file():
        sync_handoff_status(handoff_path=handoff, task_label=label, status=status)


def _ids(items: list[str]) -> str:
    return f"({', '.join(items)})" if items else ""


def _insert_next_step(handoff: Path, bullet: str) -> None:
    lines = handoff.read_text(encoding="utf-8").split("\n")
    for idx, line in enumerate(lines):
        if line.startswith("## 5."):
            at = idx + 1
            while at < len(lines) and not lines[at].strip():
                at += 1
            lines.insert(at, bullet)
            handoff.write_text("\n".join(lines), encoding="utf-8")
            return
    handoff.write_text(handoff.read_text(encoding="utf-8").rstrip("\n") + f"\n\n## 5. 다음 세션 시작 포인트\n\n{bullet}\n",
                       encoding="utf-8")


def reflect_join(*, branch: str, branch_dir: Path, parent_branch: str, active_dir: Path,
                 sha: str | None, today: str) -> JoinReport:
    """모듈 docstring 의 1~4. 모 브랜치 쪽 파일만 쓰고(브랜치 쪽은 이월 표시만), commit 은 하지 않는다."""
    from workflow_kit.common.workflow_writes import upsert_backlog_entry  # noqa: PLC0415

    parent_dir = active_dir / parent_branch
    handoff = path_in_active(active_dir, HANDOFF_FILENAME, parent_branch)
    origin = inherit.origin_label(branch, sha)
    report = JoinReport(branch=branch, origin=origin)

    # 1. 이어받은 task 되돌려 적기 + 목록
    for item in inherit.plan_write_back(branch_dir, active_dir):
        if item.action != inherit.WRITE_BACK:
            continue
        inherit.apply_write_back(item)
        report.written_back.append(item.task_id)
        if item.origin_branch == parent_branch:
            restored = item.origin_path.read_text(encoding="utf-8")
            _sync_lists(handoff, _label(restored, item.task_id),
                        inherit._frontmatter_value(restored, "status"))

    # 2 · 3. 자체 task — 열린 것은 이월, 완료는 최근 완료
    plan = plan_join(branch_dir, parent_dir)
    for path, text in _own_tasks(branch_dir):
        task_id, status = path.stem, inherit._frontmatter_value(text, "status")
        if task_id in plan.carry:
            source = inherit._frontmatter_value(text, "source_path")
            source = source if source.startswith("backlog/") else f"backlog/{today}.md"
            upsert_backlog_entry(
                backlog_path=parent_dir / source,
                task_id=task_id,
                entry_lines=inherit.insert_frontmatter_line(text, MERGED_FROM_KEY, origin).rstrip("\n").split("\n"),
                title=inherit.task_title(text, task_id),
                kind=inherit._frontmatter_value(text, "kind") or "generic",
                status=status or "planned",
            )
            path.write_text(inherit.insert_frontmatter_line(text, CARRIED_OVER_KEY, f"{task_id}@{parent_branch}"),
                            encoding="utf-8")
            _sync_lists(handoff, _label(text, task_id), status)
            report.carried.append(task_id)
        elif task_id in plan.done:
            _sync_lists(handoff, _label(text, task_id), "done")
            report.done.append(task_id)

    # 4. §5 합류 줄 + 합류 기록
    branch_handoff = path_in_active(active_dir, HANDOFF_FILENAME, branch)
    baseline = inherit.handoff_line(branch_handoff.read_text(encoding="utf-8"), "현재 기준선") \
        if branch_handoff.is_file() else ""
    if len(baseline) > BASELINE_EXCERPT_CHARS:
        baseline = baseline[:BASELINE_EXCERPT_CHARS].rstrip() + "…"
    slug = branch.replace("/", "-")
    record_rel = f"sessions/merge_{slug}_{today}.md"
    up = "../" * (len(Path(parent_branch).parts) + 1)  # active/<parent…>/ → memory/
    archived_link = f"{up}archived/{branch}/{HANDOFF_NAME}"
    counts = (f"완료 {len(report.done)}건{_ids(report.done)} · 이월 {len(report.carried)}건{_ids(report.carried)} · "
              f"되돌려 적음 {len(report.written_back)}건{_ids(report.written_back)}")
    if handoff.is_file():
        _insert_next_step(handoff, (
            f"- (합류 `{origin}`, {today}) {baseline or '(브랜치 기준선 없음)'} — {counts}. "
            f"기록: [`archived/{branch}/{HANDOFF_NAME}`]({archived_link}) · [합류 기록](./{record_rel})"))
    record = parent_dir / record_rel
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text("\n".join([
        f"# 세션 기록 — 브랜치 합류 반영 `{branch}` ({today})",
        "",
        f"- 문서 목적: `{origin}` 이 `{parent_branch}` 에 병합된 뒤 그 브랜치 메모리의 기록을 이 네임스페이스로 옮긴 사건을 남긴다.",
        "- 범위: 되돌려 적은 이어받은 task · 이월한 열린 task · 최근 완료로 올린 task · 브랜치 기준선",
        "- 대상 독자: AI agent, 저장소 관리자",
        "- 상태: active",
        f"- 최종 수정일: {today}",
        f"- 관련 문서: [handoff](../{HANDOFF_NAME}), [브랜치 기록]({'../' + archived_link})",
        "",
        "## 1. 무엇을 옮겼나",
        "",
        f"- 원류: `{origin}` (아카이브: `archived/{branch}/`)",
        f"- 브랜치 기준선: {baseline or '(없음)'}",
        f"- {counts}",
        "",
    ]) + "\n", encoding="utf-8")
    report.record_path = str(record)
    return report
