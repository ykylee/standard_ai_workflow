#!/usr/bin/env python3
"""브랜치 할 일 · task 체크리스트 저장소와 ``todo`` CLI (`core/plan_workbench_spec.md` §13, TASK-2026-11-16-main-016).

1. 왕복 — 추가 · 끝냄 · 되돌림 · 고침 · 삭제가 id 로 동작하고 파일 형식(절 · 체크 · id 표식)이 스펙대로다
2. 손으로 쓴 파일 — id 없는 줄은 두 번 읽어도 같은 id, 낯선 줄 · 제목 붙은 절 머리 · 범위 아닌 머리 묶음은 쓰기 뒤에도 남고,
   범위 아닌 머리 아래 항목은 어느 절에도 세지 않는다
3. 거절 — 빈 글 · 과길이 · 제어 문자(C0 · C1 · 줄 · 문단 구분자) · 주석 표식 · 틀린 범위 · 없는 task · 없는 id 가 각자의
   code 로 막히고 파일은 그대로 · 손으로 넣은 NEL 은 줄을 쪼개지 않는다 · 없는 브랜치 디렉터리를 만들지 않는다
4. 동시 쓰기 — 출발 장벽을 둔 두 프로세스가 100건씩 더해도 200건이 다 남는다 (락 · 원자 교체)
5. CLI — 목록(text · json) · --add --task · --done · --undo · --edit · --remove, 없는 id rc 1, 틀린 인자 · 글 rc 2
6. 표면 — dispatcher · pyproject 스크립트에 todo 가 있다
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/_workbench_fixture.py",
)

import json
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402

from workflow_kit.common import todo_list  # noqa: E402

FAILURES: list[str] = []
LINE_RE = re.compile(r"^- \[( |x)\] (.+) <!-- id:([0-9a-z]+) -->$")


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def _todo(ws: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return fx.cli(ws, ["-m", "workflow_kit", "todo", "--project-profile-path", str(fx.profile(ws)), *args])


def case_roundtrip() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("todo-1-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        bd = fx.branch_dir(ws)
        a = todo_list.add(bd, todo_list.BRANCH_SCOPE, "  브랜치 할 일  ")
        b = todo_list.add(bd, task_id, "체크 항목")
        if a.text != "브랜치 할 일":
            problems.append(f"글 앞뒤 공백을 다듬지 않았다: {a.text!r}")
        todo_list.set_done(bd, b.id, True)
        text = todo_list.todo_path(bd).read_text(encoding="utf-8")
        expected_heads = ["# Todo", "## Branch", f"## {task_id}"]
        heads = [line for line in text.splitlines() if line.startswith("#")]
        if heads != expected_heads:
            problems.append(f"절 머리가 스펙과 다르다: {heads}")
        items = {m.group(3): (m.group(1), m.group(2)) for line in text.splitlines() if (m := LINE_RE.match(line))}
        if items != {a.id: (" ", "브랜치 할 일"), b.id: ("x", "체크 항목")}:
            problems.append(f"항목 줄이 스펙 형식과 다르다: {items}")
        todo_list.set_done(bd, b.id, False)
        todo_list.edit(bd, a.id, "고친 글")
        after = todo_list.read(bd)
        if after.find(b.id) is None or after.find(b.id).done:  # type: ignore[union-attr]
            problems.append("되돌림이 반영되지 않았다")
        if (after.find(a.id) or todo_list.Item("", "", "", False)).text != "고친 글":
            problems.append("고침이 반영되지 않았다")
        if after.counts() != {todo_list.BRANCH_SCOPE: (0, 1), task_id: (0, 1)}:
            problems.append(f"counts 가 틀리다: {after.counts()}")
        todo_list.remove(bd, b.id)
        final = todo_list.read(bd)
        if final.find(b.id) is not None or task_id in final.counts():
            problems.append("삭제가 반영되지 않았다")
        if f"## {task_id}" in todo_list.todo_path(bd).read_text(encoding="utf-8"):
            problems.append("항목이 없는 task 절이 남았다")
    return problems


def case_handwritten() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("todo-2-") as td:
        ws = fx.make_workspace(td)
        bd = fx.branch_dir(ws)
        todo_list.todo_path(bd).write_text(
            "# Todo\n\n메모 한 줄\n\n## Branch\n- [ ] 손으로 쓴 일\n자유 문단은 남는다\n- [X] 손으로 쓴 일\n\n"
            "## TASK-2026-11-14-workbench-001 — 제목 붙은 머리\n- [ ] 그 task 의 일\n\n"
            "## 메모 묶음\n- [ ] 범위 아닌 머리 아래 줄\n", encoding="utf-8")
        first, second = todo_list.read(bd), todo_list.read(bd)
        if first.counts() != {todo_list.BRANCH_SCOPE: (1, 2), "TASK-2026-11-14-workbench-001": (0, 1)}:
            problems.append(f"제목 붙은 머리 · 범위 아닌 머리 아래 항목을 잘못 셌다: {first.counts()}")
        ids = [item.id for item in first.items(todo_list.BRANCH_SCOPE)]
        if ids != [item.id for item in second.items(todo_list.BRANCH_SCOPE)] or len(set(ids)) != 2:
            problems.append(f"id 없는 줄의 id 가 결정적이지 않거나 겹친다: {ids} · {[i.id for i in second.items(todo_list.BRANCH_SCOPE)]}")
        if [item.done for item in first.items(todo_list.BRANCH_SCOPE)] != [False, True]:
            problems.append("[X] 를 끝냄으로 읽지 않았다")
        todo_list.set_done(bd, ids[0], True)
        text = todo_list.todo_path(bd).read_text(encoding="utf-8")
        for kept in ("메모 한 줄", "자유 문단은 남는다", "## TASK-2026-11-14-workbench-001 — 제목 붙은 머리",
                     "## 메모 묶음\n- [ ] 범위 아닌 머리 아래 줄"):
            if kept not in text:
                problems.append(f"낯선 줄이 쓰기 뒤에 사라졌다: {kept}")
        if text.index("자유 문단은 남는다") > text.index(ids[1]):
            problems.append("낯선 줄의 자리가 바뀌었다")
        if todo_list.read(bd).find(ids[0]) is None or not todo_list.read(bd).find(ids[0]).done:  # type: ignore[union-attr]
            problems.append("결정적 id 로 고친 결과가 그 id 로 다시 보이지 않는다")
    return problems


def case_reject() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("todo-3-") as td:
        ws = fx.make_workspace(td)
        bd = fx.branch_dir(ws)
        item = todo_list.add(bd, todo_list.BRANCH_SCOPE, "남는 일")
        before = todo_list.todo_path(bd).read_bytes()
        attempts = (
            ("빈 글", lambda: todo_list.add(bd, todo_list.BRANCH_SCOPE, "   "), "invalid"),
            ("과길이", lambda: todo_list.add(bd, todo_list.BRANCH_SCOPE, "가" * (todo_list.MAX_TEXT + 1)), "invalid"),
            ("줄바꿈", lambda: todo_list.add(bd, todo_list.BRANCH_SCOPE, "a\nb"), "invalid"),
            ("제어 문자", lambda: todo_list.edit(bd, item.id, "a\x07b"), "invalid"),
            ("C1 NEL", lambda: todo_list.add(bd, todo_list.BRANCH_SCOPE, "a\x85b"), "invalid"),
            ("C1 U+0090", lambda: todo_list.add(bd, todo_list.BRANCH_SCOPE, "a\x90b"), "invalid"),
            ("줄 구분자", lambda: todo_list.add(bd, todo_list.BRANCH_SCOPE, "a\u2028b"), "invalid"),
            ("문단 구분자", lambda: todo_list.edit(bd, item.id, "a\u2029b"), "invalid"),
            ("양방향 RLO", lambda: todo_list.add(bd, todo_list.BRANCH_SCOPE, "a\u202eb"), "invalid"),
            ("양방향 격리", lambda: todo_list.add(bd, todo_list.BRANCH_SCOPE, "a\u2068b"), "invalid"),
            ("주석 표식", lambda: todo_list.add(bd, todo_list.BRANCH_SCOPE, "a <!-- id:abcd --> b"), "invalid"),
            ("틀린 범위", lambda: todo_list.add(bd, "../etc", "x"), "invalid"),
            ("없는 task", lambda: todo_list.add(bd, "TASK-2026-01-01-none-001", "x"), "not_found"),
            ("없는 id", lambda: todo_list.set_done(bd, "abcdef", True), "not_found"),
            ("틀린 id", lambda: todo_list.remove(bd, "../x"), "invalid"),
        )
        for label, attempt, code in attempts:
            try:
                attempt()
            except todo_list.TodoError as error:
                if error.code != code:
                    problems.append(f"{label}: code {error.code} (기대 {code})")
            else:
                problems.append(f"{label}: 거절하지 않았다")
        if todo_list.todo_path(bd).read_bytes() != before:
            problems.append("거절된 요청이 파일을 바꿨다")
        if todo_list.add(bd, todo_list.BRANCH_SCOPE, "가" * todo_list.MAX_TEXT).text != "가" * todo_list.MAX_TEXT:
            problems.append("상한 길이 글을 거절했다")
        if todo_list.add(bd, todo_list.BRANCH_SCOPE, "👩\u200d💻 이모지").text != "👩\u200d💻 이모지":
            problems.append("ZWJ 이모지(Cf)를 거절했다 — 양방향 제어만 막는다")
        # 손으로 넣은 NEL 이 있어도 줄이 쪼개지지 않는다 (줄 경계는 \n 하나).
        path = todo_list.todo_path(bd)
        path.write_text(path.read_text(encoding="utf-8") + "- [ ] 손\x85글 <!-- id:abc123 -->\n", encoding="utf-8")
        if (todo_list.read(bd).find("abc123") or todo_list.Item("", "", "", False)).text != "손\x85글":
            problems.append("NEL 이 든 손글 줄을 쪼개 읽었다")
        missing = Path(td) / "no-branch"
        try:
            todo_list.add(missing, todo_list.BRANCH_SCOPE, "x")
            problems.append("없는 브랜치 디렉터리에 todo 를 썼다")
        except todo_list.TodoError as error:
            if error.code != "not_found":
                problems.append(f"없는 브랜치 디렉터리: code {error.code}")
        if missing.exists():
            problems.append("없는 브랜치 디렉터리를 만들었다 — 브랜치 메모리는 backlog-update 만 만든다")
    return problems


N = 100
_WRITER = f"N = {N}\n" + """
import sys, time
from pathlib import Path
from workflow_kit.common import todo_list
bd, tag, start = Path(sys.argv[1]), sys.argv[2], float(sys.argv[3])
while time.time() < start:  # 출발 장벽 — 인터프리터 기동 차이로 쓰기가 겹치지 않는 일을 막는다
    time.sleep(0.001)
for i in range(N):
    todo_list.add(bd, todo_list.BRANCH_SCOPE, f"{tag}-{i}")
"""


def case_concurrent() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("todo-4-") as td:
        ws = fx.make_workspace(td)
        bd = fx.branch_dir(ws)
        start = f"{time.time() + 3.0:.3f}"
        procs = [subprocess.Popen([sys.executable, "-c", _WRITER, str(bd), tag, start], env=fx.env(), cwd=str(ws),
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE) for tag in ("p", "q")]
        for proc in procs:
            _, err = proc.communicate(timeout=120)
            if proc.returncode != 0:
                problems.append(f"쓰는 프로세스가 실패했다: {err.decode(errors='replace')[-200:]}")
        texts = sorted(item.text for item in todo_list.read(bd).items())
        expected = sorted(f"{tag}-{i}" for tag in ("p", "q") for i in range(N))
        if texts != expected:
            problems.append(f"동시 쓰기에서 항목이 사라지거나 겹쳤다: {len(texts)}건 (기대 {2 * N})")
    return problems


def case_cli() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("todo-5-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        add = _todo(ws, "--add", "CLI 로 더한 일", "--task", task_id, "--format", "json")
        if add.returncode != 0:
            return [f"--add rc {add.returncode}: {add.stderr[-200:]}"]
        item_id = json.loads(add.stdout)["item"]["id"]
        _todo(ws, "--add", "브랜치 일")
        listed = json.loads(_todo(ws, "--format", "json").stdout)
        if sorted(i["text"] for i in listed["items"]) != ["CLI 로 더한 일", "브랜치 일"]:
            problems.append(f"json 목록이 틀리다: {listed['items']}")
        if listed["counts"].get(task_id) != [0, 1]:
            problems.append(f"json counts 가 틀리다: {listed['counts']}")
        scoped = json.loads(_todo(ws, "--task", task_id, "--format", "json").stdout)["items"]
        if [i["id"] for i in scoped] != [item_id]:
            problems.append(f"--task 목록이 그 task 만 보이지 않는다: {scoped}")
        for args, check in ((("--done", item_id), lambda i: i["done"] is True),
                            (("--undo", item_id), lambda i: i["done"] is False),
                            (("--edit", item_id, "--text", "고친 글"), lambda i: i["text"] == "고친 글")):
            proc = _todo(ws, *args, "--format", "json")
            if proc.returncode != 0 or not check(json.loads(proc.stdout)["item"]):
                problems.append(f"{args[0]}: rc {proc.returncode} {proc.stdout[-160:]}")
        text = _todo(ws).stdout
        if f"## {task_id} (0/1)" not in text or f"고친 글  ({item_id})" not in text:
            problems.append(f"text 목록이 절 · 개수 · id 를 보이지 않는다: {text[-200:]}")
        if _todo(ws, "--remove", item_id).returncode != 0 or todo_list.read(fx.branch_dir(ws)).find(item_id):
            problems.append("--remove 가 지우지 않았다")
        for args, rc in ((("--done", "abcdef"), 1), (("--remove", "abcdef"), 1), (("--add", ""), 2),
                         (("--add", "x", "--task", "TASK-2026-01-01-none-001"), 1), (("--edit", "abcd"), 2),
                         (("--text", "x"), 2), (("--done", "abcd", "--task", task_id), 2),
                         (("--done", "a", "--undo", "b"), 2), (("--task", "../x"), 2), (("--task", "TASK-2026-01-01-none-001"), 1)):
            proc = _todo(ws, *args)
            if proc.returncode != rc:
                problems.append(f"{' '.join(args)}: rc {proc.returncode} (기대 {rc})")
    return problems


def case_surface() -> list[str]:
    problems: list[str] = []
    from workflow_kit.common.tool_dispatch import TOOL_MODULES
    if TOOL_MODULES.get("todo") != "workflow_kit.tools.todo":
        problems.append("dispatcher 에 todo 가 없다")
    pyproject = (fx.SOURCE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if 'workflow-todo = "workflow_kit.tools.todo:main"' not in pyproject:
        problems.append("pyproject 스크립트에 workflow-todo 가 없다")
    return problems


CASES = (
    ("1 왕복 — 추가 · 끝냄 · 되돌림 · 고침 · 삭제 · 형식", case_roundtrip),
    ("2 손으로 쓴 파일 — 결정적 id · 낯선 줄 보존", case_handwritten),
    ("3 거절 — code 별 · 파일 그대로", case_reject),
    ("4 동시 쓰기 2 프로세스 장벽 — 200건 보존", case_concurrent),
    ("5 CLI — 목록 · 조작 · 종료 코드", case_cli),
    ("6 표면 — dispatcher · pyproject", case_surface),
)


def main() -> int:
    print("check_todo_list — 브랜치 할 일 · task 체크리스트 (plan_workbench_spec §13)")
    for name, case in CASES:
        try:
            _record(name, case())
        except Exception:  # noqa: BLE001 — case 하나의 예외는 그 case 의 FAIL 이다
            _record(name, ["예외: " + traceback.format_exc().strip().splitlines()[-1]])
            traceback.print_exc()
    print(f"\n{len(CASES) - len(FAILURES)}/{len(CASES)} PASS")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
