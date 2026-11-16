"""``python -m workflow_kit todo`` — 브랜치 할 일 · task 체크리스트 (TASK-2026-11-16-main-016).

작업 세션 쪽 창구다. 워크벤치(소유자)와 같은 파일 ``<branch_dir>/todo.md`` 를 :mod:`workflow_kit.common.todo_list`
로만 읽고 쓴다.

    todo                         # 목록 (모든 절)
    todo --task <ID>             # 그 task 의 체크리스트만
    todo --add "글" [--task <ID>]  # --task 가 없으면 브랜치 할 일
    todo --done <id> | --undo <id> | --remove <id>
    todo --edit <id> --text "글"

종료 코드: 0 성공 · 1 그런 id · task 가 없거나 락을 못 잡았다 · 2 인자 · 글이 틀렸다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from workflow_kit.common import todo_list
from workflow_kit.common.paths import discover_project_profile_path, workflow_branch_dir
from workflow_kit.common.stdio import force_utf8_stdio

FORMAT_TEXT = "text"
FORMAT_JSON = "json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="todo",
        description="브랜치 할 일 · task 체크리스트 (<branch>/todo.md) 를 보고 고친다 — 워크벤치와 같은 파일이다.",
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--add", metavar="TEXT", help="할 일을 더한다 (--task 가 없으면 브랜치 할 일)")
    action.add_argument("--done", metavar="ID", help="끝냈다고 표시한다")
    action.add_argument("--undo", metavar="ID", help="끝냄 표시를 되돌린다")
    action.add_argument("--remove", metavar="ID", help="지운다")
    action.add_argument("--edit", metavar="ID", help="글을 고친다 (--text 와 함께)")
    parser.add_argument("--text", help="--edit 의 새 글")
    parser.add_argument("--task", metavar="TASK_ID", help="목록 · 추가의 범위를 그 task 로")
    parser.add_argument("--format", choices=(FORMAT_TEXT, FORMAT_JSON), default=FORMAT_TEXT, dest="output_format")
    parser.add_argument("--project-profile-path", default=None, help="미지정 시 cwd 상위에서 자동 탐색")
    return parser


def _render_text(todo: todo_list.TodoList, scope: str | None) -> str:
    lines: list[str] = []
    scopes = [scope] if scope else [todo_list.BRANCH_SCOPE, *sorted(s for s in todo.sections
                                                                     if s != todo_list.BRANCH_SCOPE)]
    for name in scopes:
        items = todo.items(name)
        if not items and name != todo_list.BRANCH_SCOPE and scope is None:
            continue
        done = sum(1 for item in items if item.done)
        lines.append(f"## {name} ({done}/{len(items)})")
        lines += [f"- [{'x' if item.done else ' '}] {item.text}  ({item.id})" for item in items] or ["- (없음)"]
        lines.append("")
    return "\n".join(lines).rstrip("\n")


def _emit(output_format: str, payload: dict[str, object], text: str, *, stream=None) -> None:
    out = stream or sys.stdout
    if output_format == FORMAT_JSON:
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=out)
    else:
        print(text, file=out)


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.text is not None and args.edit is None:
        parser.error("--text 는 --edit 와 함께만 쓴다")
    if args.edit is not None and args.text is None:
        parser.error("--edit 에는 --text 가 필요하다")
    if args.task is not None and any(v is not None for v in (args.done, args.undo, args.remove, args.edit)):
        parser.error("--task 는 목록 · --add 에만 쓴다 (id 로 고칠 때는 범위가 필요 없다)")
    if args.project_profile_path:
        profile = Path(args.project_profile_path).resolve()
    else:
        found = discover_project_profile_path()
        profile = Path(found).resolve() if found is not None else Path()
    if not profile.is_file():
        print("PROJECT_PROFILE.md 를 찾지 못했다 — --project-profile-path 로 명시하라.", file=sys.stderr)
        return 2
    branch_dir = workflow_branch_dir(profile)
    try:
        if args.add is not None:
            item = todo_list.add(branch_dir, args.task or todo_list.BRANCH_SCOPE, args.add)
            verb = "더했다"
        elif args.done is not None:
            item, verb = todo_list.set_done(branch_dir, args.done, True), "끝냈다고 표시했다"
        elif args.undo is not None:
            item, verb = todo_list.set_done(branch_dir, args.undo, False), "끝냄을 되돌렸다"
        elif args.remove is not None:
            item, verb = todo_list.remove(branch_dir, args.remove), "지웠다"
        elif args.edit is not None:
            item, verb = todo_list.edit(branch_dir, args.edit, args.text), "고쳤다"
        else:
            if args.task is not None and not todo_list.is_scope(args.task):
                parser.error(f"--task 가 task ID 형식이 아니다: {args.task}")
            if args.task is not None and not todo_list.has_task(branch_dir, args.task):
                raise todo_list.TodoError("not_found", f"이 브랜치에 task 가 없다: {args.task}")
            todo = todo_list.read(branch_dir)
            items = todo.items(args.task)
            _emit(args.output_format,
                  {"status": "ok", "path": todo_list.todo_path(branch_dir).as_posix(),
                   "items": [todo_list.as_json(item) for item in items],
                   "counts": {k: list(v) for k, v in todo.counts().items()}},
                  _render_text(todo, args.task))
            return 0
    except todo_list.TodoError as error:
        _emit(args.output_format, {"status": "error", "error_code": error.code, "error": str(error)},
              f"todo: {error}", stream=sys.stderr if args.output_format == FORMAT_TEXT else None)
        return 2 if error.code == "invalid" else 1
    _emit(args.output_format, {"status": "ok", "action": verb, "item": todo_list.as_json(item)},
          f"{verb}: [{item.scope}] {item.text}  ({item.id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
