#!/usr/bin/env python3
"""워크벤치 — 응답 쓰기 (`core/plan_workbench_spec.md` §6 · §11, ADR-032 V2 · V3 · V5 · V7).

1. 왕복 — 서버가 쓴 응답이 `plan-import` 의 1~6 단계를 통과해 보관으로 가고 결정 상태에 든다
2. 동시 제출 — 서버 스레드(여러 클라이언트) · 여러 프로세스의 `build_and_publish` 에서 유실 0 · 이름 중복 0 · 전부 자격
3. 독자는 덜 쓰인 파일을 보지 않는다 — 세 층으로 잰다: (a) 공개 도중 파일을 열고 · 쓰고 · 이름을 붙이는 audit 이벤트마다
   받은편지함을 훑는다, (b) 응답 이름 꼴을 쓰기로 열거나 덜 쓰인 원본에 응답 이름을 붙이면 위반 (audit), (c) Linux 에서는
   inotify 로 응답 이름이 생긴 뒤의 쓰기를 커널 쪽에서 본다 (다른 프로세스 · fd 쓰기 포함, mmap 쓰기는 못 본다 — 한계;
   inotify 가 없는 OS 는 (c) 를 미측정으로 출력한다);
   같은 바이트를 두 번 공개하면 두 파일이다 (배타 생성)
4. 거절은 받은편지함을 바꾸지 않는다 — 413 · 422(선택지 밖 · 한도 · 제어 문자) · 409(지문 · 배치 · 오류 규칙)
5. `answered` 결정은 폼이 무엇을 보냈든 기본값 · `opened: no` 로 적힌다
6. 같은 응답자의 `received_at` 은 단조 증가한다 — 시계가 멈춰도, 보관에 더 늦은 응답이 있어도
"""

from __future__ import annotations

#: 프로세스 경합과 `plan-import` subprocess 를 돈다.
CHECK_TIMEOUT_S = 240

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/_workbench_fixture.py",
)

import datetime as dt
import multiprocessing
import os
import re
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402
from workflow_kit.common import plan_claims as pc  # noqa: E402
from workflow_kit.common import plan_responses as pr  # noqa: E402
from workflow_kit.common import plan_tasks  # noqa: E402
from workflow_kit.workbench import respond  # noqa: E402

FAILURES: list[str] = []


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def _task(ws: Path, task_id: str) -> plan_tasks.TaskPlan:
    task = plan_tasks.read_task_plan(fx.branch_dir(ws) / "backlog" / "tasks" / f"{task_id}.md")
    assert task is not None
    return task


def _logged_in(port: int) -> fx.Browser:
    browser = fx.Browser(port)
    reply = browser.login(fx.APPROVER)
    if reply.status != 303:
        raise AssertionError(f"로그인이 {reply.status} 다")
    return browser


def case_round_trip() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-write-1-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with fx.running(ws) as srv:
            browser = _logged_in(srv.port)
            reply, _ = fx.submit(browser, f"/task/{task_id}", overrides={"value_D1": "warn", "opened_D2": "yes"},
                                 extra_fields=[("comment_C1", "첫 줄\r\n둘째 줄"), ("comment_-", "")])
            if reply.status != 303 or reply.header("Location") != f"../{task_id}":
                problems.append(f"제출이 303 ../{task_id} 가 아니다: {reply.status} {reply.header('Location')}")
            after = browser.get(f"/task/{task_id}")
            if "의 응답을" not in after.text or "plan-import" not in after.text:
                problems.append("제출 뒤 계획 화면에 받았다는 줄이 없다")
        inbox = list(fx.inbox_snapshot(ws))
        if len(inbox) != 1:
            return problems + [f"받은편지함에 응답이 1건이 아니다: {inbox}"]
        parsed = pr.read_response(pr.inbox_dir(fx.branch_dir(ws)) / inbox[0])
        if parsed.responder != fx.APPROVER.name or parsed.fields.get("role") != "approver":
            problems.append(f"응답자 · 역할이 토큰과 다르다: {parsed.fields}")
        if ("C1", "첫 줄\n둘째 줄") not in parsed.comments:
            problems.append(f"주석이 LF 로 고쳐져 실리지 않았다: {parsed.comments}")
        rc, out = fx.plan_import(ws, "--task", task_id, "--apply")
        verdicts = out.get("responses") or out.get("inbox") or []
        if rc != 0 or not any(v.get("eligible") for v in verdicts):
            problems.append(f"plan-import 가 응답을 자격 있게 보지 않았다: rc {rc} {str(out)[:300]}")
        states = plan_tasks.computed_states(_task(ws, task_id)).states
        if states.get("D1") != f"{pc.STATE_CHANGED}:warn" or states.get("D2") != pc.STATE_KEPT:
            problems.append(f"결정 상태가 응답을 반영하지 않았다: {states}")
        if fx.inbox_snapshot(ws):
            problems.append("반영 뒤에도 받은편지함에 응답이 남았다")
    return problems


def _publish_in_process(args: tuple[str, str, str, int]) -> int:
    ws_s, task_id, responder, count = args
    ws = Path(ws_s)
    fixed = dt.datetime(2026, 11, 14, 9, 0, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
    published = 0
    for _ in range(count):
        task = _task(ws, task_id)
        outcome = respond.build_and_publish(
            branch_dir=fx.branch_dir(ws), task=task, responder=responder, now=lambda: fixed,
            form={"plan_digest": [pc.plan_digest(task.plan)], "value_D1": ["warn"], "value_D2": ["a"]})
        published += outcome.ok
    return published


def case_concurrent() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-write-2-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with fx.running(ws) as srv:
            browser = _logged_in(srv.port)
            page = browser.get(f"/task/{task_id}")
            form = fx.respond_form(page.text)
            assert form is not None
            action = fx.resolve(f"/task/{task_id}", form["action"])
            statuses: list[int] = []
            lock = threading.Lock()

            def worker() -> None:
                for _ in range(4):
                    reply = browser.post(action, form["fields"])
                    with lock:
                        statuses.append(reply.status)

            real_latest = respond._latest_eligible_micros

            def slow_latest(*args: object, **kwargs: object) -> int | None:
                # 시각을 정한 뒤 공개하기까지의 창을 넓힌다 — 잠금이 없으면 같은 응답자의 시각이 겹친다.
                found = real_latest(*args, **kwargs)  # type: ignore[arg-type]
                time.sleep(0.05)
                return found

            frozen = dt.datetime(2026, 11, 14, 9, 0, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
            threads = [threading.Thread(target=worker) for _ in range(6)]
            with mock.patch.object(respond, "_latest_eligible_micros", slow_latest), \
                    mock.patch.object(respond, "_now", lambda: frozen):
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
        if statuses.count(303) != 24:
            problems.append(f"스레드 제출 24건 중 303 이 {statuses.count(303)}건")
        with multiprocessing.get_context("spawn").Pool(4) as pool:
            done = pool.map(_publish_in_process, [(str(ws), task_id, f"p{i}", 5) for i in range(4)])
        if sum(done) != 20:
            problems.append(f"프로세스 공개 20건 중 {sum(done)}건만 성공")
        names = list(fx.inbox_snapshot(ws))
        if len(names) != 44:
            problems.append(f"받은편지함 응답이 44건이 아니다: {len(names)} (유실 또는 덮어쓰기)")
        task = _task(ws, task_id)
        census = pr.inbox_census(fx.branch_dir(ws))
        bad = [p.name for p in census.paths(task_id)
               if not pr.judge(p, task.plan, task_id, plan_has_errors=False)[1].eligible]
        if bad:
            problems.append(f"자격 없는 응답 {len(bad)}건: {bad[:3]}")
        stamps = {}
        for path in census.paths(task_id):
            parsed = pr.read_response(path)
            stamps.setdefault(parsed.responder, []).append(parsed.received_at)
        alice = stamps.get(fx.APPROVER.name, [])
        if not all(stamp.startswith("2026-11-14T09:00:00") for stamp in alice):
            problems.append("스레드 제출이 멈춘 시계를 쓰지 않았다 — 이 case 가 경합을 재지 못한다")
        if len(set(alice)) != len(alice):
            problems.append("같은 응답자의 received_at 이 겹친다 (스레드 제출)")
    return problems


def case_no_partial_reads() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-write-3-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        task = _task(ws, task_id)
        body = pr.render_response(task_id=task_id, plan=task.plan, responder="r", received_at=fx_at(1)).encode()
        branch = fx.branch_dir(ws)
        seen: list[str] = []
        real_fsync = os.fsync

        def paused_fsync(fd: int) -> None:
            # 쓰기와 fsync 사이 — 여기서 독자가 받은편지함을 훑는다 (정해진 멈춤).
            for path in pr.inbox_census(branch).paths(task_id):
                data = path.read_bytes()
                seen.append(f"{path.name}:{len(data)}")
            real_fsync(fd)

        real_open = open

        class Paused:
            """만들기와 쓰기 사이 · 쓰기마다 독자가 훑는다 — fsync 를 부르지 않는 쓰는 쪽도 잰다."""

            def __init__(self, handle: Any) -> None:
                self._handle = handle

            def write(self, data: bytes) -> int:
                n = int(self._handle.write(data))
                self._handle.flush()
                look("쓰기 뒤")
                return n

            def __getattr__(self, name: str) -> Any:
                return getattr(self._handle, name)

            def __enter__(self) -> "Paused":
                return self

            def __exit__(self, *exc: object) -> None:
                self._handle.close()

        def look(when: str) -> None:
            for path in pr.inbox_census(branch).paths(task_id):
                seen.append(f"{when} {path.name}:{len(path.read_bytes())}")

        def paused_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            handle = real_open(file, mode, *args, **kwargs)
            if "w" in mode or "x" in mode or "a" in mode:
                look("만든 뒤")
                return Paused(handle)
            return handle

        # 쓰는 쪽이 어떤 API 를 쓰든 파일을 열거나 이름을 붙이는 순간은 audit 이벤트다 — 그때마다 훑는다.
        WATCH.update(look=look, inbox=pr.ensure_inbox(branch), body=body, violations=[])
        kernel: InboxWatch | None = None
        if sys.platform.startswith("linux"):
            kernel = InboxWatch(pr.inbox_dir(branch))
        else:
            print("        (미측정: inotify 가 없는 OS — 커널 쪽 관찰자 판정을 건너뛴다)")
        WATCH["on"] = True
        try:
            with mock.patch.object(pr.os, "fsync", paused_fsync), \
                    mock.patch.object(pr, "open", paused_open, create=True):
                pr.publish(branch, task_id, body)
        finally:
            WATCH["on"] = False
        if kernel is not None:
            events = kernel.events()
            kernel.close()
            if not any(mask & (InboxWatch.IN_CREATE | InboxWatch.IN_MOVED_TO) and name.endswith(".md")
                       for mask, name in events):
                problems.append(f"커널 관찰자가 공개를 보지 못했다 — 이 판정이 재지 못한다: {events}")
            problems.extend(exposed_writes(events))
        if seen:
            problems.append(f"공개가 끝나기 전에 독자가 응답을 봤다: {seen}")
        if WATCH["violations"]:
            problems.append(f"공개 방식이 원자적이지 않다: {WATCH['violations']}")
        pr.publish(branch, task_id, body)
        names = sorted(fx.inbox_snapshot(ws))
        if len(names) != 2:
            problems.append(f"같은 바이트 두 번 공개가 두 파일이 아니다 (배타 생성 아님): {names}")
        leftovers = [e.name for e in pr.inbox_dir(branch).iterdir() if e.name.startswith(".tmp-")]
        if leftovers:
            problems.append(f"임시 파일이 남았다: {leftovers}")
    return problems


class InboxWatch:
    """커널 쪽 관찰자 (Linux inotify) — 프로세스 · API 와 무관하게 받은편지함의 이벤트를 순서대로 받는다.

    판정: 공개하는 동안 ``*.md`` 이름이 생긴(IN_CREATE · IN_MOVED_TO) 뒤 받은편지함 안에서 쓰기(IN_MODIFY)가 있으면
    덜 쓰인 파일이 이름을 가진 채 노출된 것이다. 올바른 공개는 임시 이름에 다 쓴 뒤 이름만 붙인다.
    mmap 쓰기는 inotify 도 보지 못한다 — 한계.
    """

    IN_MODIFY, IN_MOVED_TO, IN_CREATE = 0x2, 0x80, 0x100

    def __init__(self, directory: Path) -> None:
        import ctypes
        import ctypes.util
        self._libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)
        self.fd = self._libc.inotify_init1(os.O_NONBLOCK)
        if self.fd < 0:
            raise OSError(ctypes.get_errno(), "inotify_init1")
        mask = self.IN_MODIFY | self.IN_MOVED_TO | self.IN_CREATE
        if self._libc.inotify_add_watch(self.fd, os.fsencode(directory), mask) < 0:
            raise OSError(ctypes.get_errno(), "inotify_add_watch")

    def events(self) -> list[tuple[int, str]]:
        import struct
        out: list[tuple[int, str]] = []
        while True:
            try:
                data = os.read(self.fd, 65536)
            except BlockingIOError:
                return out
            offset = 0
            while offset < len(data):
                _wd, mask, _cookie, size = struct.unpack_from("iIII", data, offset)
                name = data[offset + 16: offset + 16 + size].split(b"\0", 1)[0].decode("utf-8", "replace")
                out.append((mask, name))
                offset += 16 + size

    def close(self) -> None:
        os.close(self.fd)


def exposed_writes(events: list[tuple[int, str]]) -> list[str]:
    named = False
    found: list[str] = []
    for mask, name in events:
        if mask & (InboxWatch.IN_CREATE | InboxWatch.IN_MOVED_TO) and name.endswith(".md"):
            named = True
        elif mask & InboxWatch.IN_MODIFY and named:
            found.append(f"응답 이름이 생긴 뒤 받은편지함에 쓰기: {name}")
    return found


#: audit hook 은 지울 수 없다 — 한 번만 걸고 스위치로 켠다.
WATCH: dict[str, Any] = {"on": False, "look": None, "busy": False, "inbox": None, "body": b"", "violations": []}
_AUDITED = {"open", "os.link", "os.rename", "os.replace", "os.symlink"}


_RESPONSE_NAME_RE = re.compile(r"^TASK-.+-[0-9]+\.md$")
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC


def _is_response_name(path: object) -> bool:
    try:
        target = Path(os.fsdecode(path))  # type: ignore[arg-type]
    except TypeError:
        return False
    inbox = WATCH.get("inbox")
    return (inbox is not None and target.name.endswith(".md")
            and target.parent.resolve() == inbox.resolve())


def _audit(event: str, args: tuple[Any, ...]) -> None:
    """구조 판정 — 쓰는 쪽이 어떤 API 를 쓰든 (스펙 §6-8 · 주장 스펙 §7-2):

    - 받은편지함의 응답 이름(``*.md``)을 쓰기 · 생성 플래그로 여는 것 자체가 위반이다 — 이름이 생긴 뒤 쓰는 길이다.
    - 응답 이름을 붙이는 순간(``os.link`` · ``os.rename`` · ``os.replace``) 원본은 이미 완성된 바이트여야 한다.
    - 그 밖의 열기 · 이름 붙이기마다 독자가 받은편지함을 훑는다.
    """
    if not WATCH["on"] or WATCH["busy"] or event not in _AUDITED:
        return
    WATCH["busy"] = True  # 훑는 동안의 open 은 다시 걸리지 않게
    try:
        if event == "open" and len(args) >= 3 and isinstance(args[0], (str, bytes, os.PathLike)) \
                and _RESPONSE_NAME_RE.match(Path(os.fsdecode(args[0])).name):
            # 디렉터리와 무관하게 이름 꼴로 본다 — dir_fd 상대 이름(openat)은 audit 인자에 dir_fd 가 없다.
            mode, flags = args[1], args[2]
            writing = (isinstance(mode, str) and any(c in mode for c in "wxa+")) or \
                (isinstance(flags, int) and flags & _WRITE_FLAGS)
            if writing:
                WATCH["violations"].append(f"응답 이름을 쓰기로 열었다: {Path(os.fsdecode(args[0])).name}")
        if event in ("os.link", "os.rename", "os.replace") and len(args) >= 2 \
                and isinstance(args[1], (str, bytes, os.PathLike)) \
                and _RESPONSE_NAME_RE.match(Path(os.fsdecode(args[1])).name):
            src_dir_fd = args[2] if len(args) > 2 and isinstance(args[2], int) and args[2] >= 0 else None
            source = Path(os.fsdecode(args[0]))
            if src_dir_fd is not None and not source.is_absolute():
                source = Path(f"/proc/self/fd/{src_dir_fd}") / source
            try:
                data = source.read_bytes()
            except OSError:
                data = b""
            if data != WATCH["body"]:
                WATCH["violations"].append(f"덜 쓰인 원본({len(data)}B)에 응답 이름을 붙였다")
        WATCH["look"](f"audit {event}")
    finally:
        WATCH["busy"] = False


sys.addaudithook(_audit)


def fx_at(micro: int) -> str:
    return f"2026-11-14T09:00:00.{micro:06d}+09:00"


def case_rejections_leave_inbox() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-write-4-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        other = fx.create_task(ws, name="오류 규칙을 어길 task")
        with fx.running(ws) as srv:
            browser = _logged_in(srv.port)
            path = f"/task/{task_id}"
            before = fx.inbox_snapshot(ws)

            def expect(label: str, reply: fx.Reply, status: int, needle: str = "") -> None:
                if reply.status != status:
                    problems.append(f"{label}: {reply.status} (기대 {status})")
                elif needle and needle not in reply.text:
                    problems.append(f"{label}: 사유에 `{needle}` 이 없다 — 다른 단계에서 거절됐다")
                if fx.inbox_snapshot(ws) != before:
                    problems.append(f"{label}: 받은편지함이 바뀌었다")

            big = [("comment_-", "x" * 262_200)]
            reply, _ = fx.submit(browser, path, extra_fields=big)
            expect("413 본문 한도", reply, 413, "바이트를 넘는다")
            reply, _ = fx.submit(browser, path, overrides={"value_D1": "nope"})
            expect("422 선택지 밖", reply, 422, "선택지에 없다")
            reply, _ = fx.submit(browser, path, drop=("value_D1",))
            expect("422 값 없음", reply, 422, "선택지에 없다")
            reply, _ = fx.submit(browser, path, extra_fields=[("comment_C1", "y" * 1_001)])
            expect("422 주석 한도", reply, 422, "자격 1 단계")
            reply, _ = fx.submit(browser, path, extra_fields=[("comment_C1", "줄\x07종")])
            expect("422 제어 문자", reply, 422, "제어 문자")
            reply, _ = fx.submit(browser, path, extra_fields=[("comment_C9", "없는 주장")])
            expect("422 없는 주석 대상", reply, 422, "주석 대상")
            reply, _ = fx.submit(browser, path, overrides={"plan_digest": "0" * 64})
            expect("409 지문", reply, 409, "다시 열어라")
            # 지문은 맞지만 그 사이 계획이 바뀌었다 — 페이지를 연 뒤 task 를 고친다.
            page = browser.get(path)
            form = fx.respond_form(page.text)
            assert form is not None
            fx.backlog(ws, "--mode", "update", "--task-id", task_id, "--task-name", "x",
                       "--plan-claim", "C3 새 주장이 생겼다")
            reply = browser.post(fx.resolve(path, form["action"]), form["fields"])
            expect("409 계획이 바뀜", reply, 409, "다시 열어라")
            if "다시 열어라" not in reply.text:
                problems.append("409 지문 화면에 다시 열라는 안내가 없다")
            # 배치 — 받은편지함을 보관과 같은 디렉터리로 (링크).
            branch = fx.branch_dir(ws)
            archive = pr.responses_dir(branch)
            inbox = pr.inbox_dir(branch)
            page = browser.get(path)
            form = fx.respond_form(page.text)
            assert form is not None
            pr.ensure_inbox(branch)
            before = fx.inbox_snapshot(ws)
            saved = inbox.with_name("inbox_real")
            inbox.rename(saved)
            inbox.symlink_to(archive, target_is_directory=True)
            try:
                listing = sorted(e.name for e in archive.iterdir())
                reply = browser.post(fx.resolve(path, form["action"]), form["fields"])
                if reply.status != 409 or "배치" not in reply.text:
                    problems.append(f"409 배치: {reply.status} {reply.text[-200:]}")
                if sorted(e.name for e in archive.iterdir()) != listing:
                    problems.append("409 배치: 보관 · 받은편지함이 바뀌었다")
            finally:
                inbox.unlink()
                saved.rename(inbox)
            # 오류 규칙 — 같은 결정 ID 둘 (L6).
            task_file = branch / "backlog" / "tasks" / f"{other}.md"
            opage = browser.get(f"/task/{other}")
            oform = fx.respond_form(opage.text)
            assert oform is not None
            text = task_file.read_text(encoding="utf-8")
            line = next(ln for ln in text.splitlines() if ln.lstrip().startswith("- Decisions: D2"))
            task_file.write_text(text.replace(line, line + "\n" + line), encoding="utf-8")
            reply = browser.post(fx.resolve(f"/task/{other}", oform["action"]), oform["fields"])
            expect("409 오류 규칙", reply, 409, "오류 규칙")
    return problems


def case_answered_ignored() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-write-5-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        fx.backlog(ws, "--mode", "update", "--task-id", task_id, "--task-name", "x", "--decision-state", "D2=answered:b")
        with fx.running(ws) as srv:
            browser = _logged_in(srv.port)
            page = browser.get(f"/task/{task_id}")
            if 'name="value_D2"' in page.text:
                problems.append("answered 결정에 입력칸이 있다 (읽기 전용이어야 한다)")
            reply, _ = fx.submit(browser, f"/task/{task_id}",
                                 extra_fields=[("value_D2", "b"), ("opened_D2", "yes")])
            if reply.status != 303:
                problems.append(f"제출이 303 이 아니다: {reply.status} {reply.text[:200]}")
            # 선택지 밖 값도 answered 결정이면 무시한다 — 422 가 아니다 (§6-3 은 answered 가 아닌 결정만).
            reply, _ = fx.submit(browser, f"/task/{task_id}", extra_fields=[("value_D2", "zzz-not-an-option")])
            if reply.status != 303:
                problems.append(f"answered 결정의 선택지 밖 값을 거절했다: {reply.status}")
        names = list(fx.inbox_snapshot(ws))
        if len(names) != 2:
            return problems + [f"응답이 2건이 아니다: {names}"]
        for name in names:
            parsed = pr.read_response(pr.inbox_dir(fx.branch_dir(ws)) / name)
            line = next((d for d in parsed.decisions if d.decision_id == "D2"), None)
            if line is None or line.value != "a" or line.opened:
                problems.append(f"answered 결정이 기본값 · opened no 로 적히지 않았다: {line}")
    return problems


def case_monotonic() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-write-6-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        branch = fx.branch_dir(ws)
        frozen = dt.datetime(2026, 11, 14, 9, 0, 0, 5, tzinfo=dt.timezone(dt.timedelta(hours=9)))
        with fx.running(ws) as srv, mock.patch.object(respond, "_now", lambda: frozen):
            browser = _logged_in(srv.port)
            for _ in range(3):
                fx.submit(browser, f"/task/{task_id}")
        stamps = [pr.read_response(p).received_at for p in pr.inbox_census(branch).paths(task_id)]
        micros = sorted(pr.received_micros(s) or 0 for s in stamps)
        base = pr.received_micros(frozen.isoformat(timespec="microseconds")) or 0
        if micros != [base, base + 1, base + 2]:
            problems.append(f"시계가 멈췄을 때 received_at 이 1µs 씩 늘지 않는다 (시계를 바꿔 끼우지 못했다?): {stamps}")
        # 보관에 더 늦은 자격 있는 응답이 있으면 그보다 뒤로.
        task = _task(ws, task_id)
        later = "2026-11-15T00:00:00.000000+09:00"
        archive = pr.responses_dir(branch)
        archive.mkdir(parents=True, exist_ok=True)
        (archive / f"{task_id}-1.md").write_text(pr.render_response(
            task_id=task_id, plan=task.plan, responder=fx.APPROVER.name, received_at=later), encoding="utf-8")
        # 자격 없는(지문이 다른) 더 늦은 응답은 세지 않는다.
        far = "2027-01-01T00:00:00.000000+09:00"
        stale = pr.render_response(task_id=task_id, plan=task.plan, responder=fx.APPROVER.name, received_at=far)
        stale = stale.replace(pc.plan_digest(task.plan), "f" * 64)
        (archive / f"{task_id}-2.md").write_text(stale, encoding="utf-8")
        outcome = respond.build_and_publish(
            branch_dir=branch, task=task, responder=fx.APPROVER.name, now=lambda: frozen,
            form={"plan_digest": [pc.plan_digest(task.plan)], "value_D1": ["block"], "value_D2": ["a"]})
        got = pr.received_micros(outcome.received_at or "") or 0
        want = (pr.received_micros(later) or 0) + 1
        if got != want:
            problems.append(f"보관의 늦은 응답 뒤 1µs 가 아니다: {outcome.received_at} (기대 {want})")
    return problems


CASES = (
    ("1 왕복 — 서버가 쓴 응답이 plan-import 를 통과해 상태에 든다", case_round_trip),
    ("2 동시 제출 — 스레드 · 프로세스에서 유실 0 · 전부 자격", case_concurrent),
    ("3 독자는 덜 쓰인 파일을 보지 않는다 · 배타 생성", case_no_partial_reads),
    ("4 거절(413 · 422 · 409)은 받은편지함을 바꾸지 않는다", case_rejections_leave_inbox),
    ("5 answered 결정의 조작 값은 무시된다", case_answered_ignored),
    ("6 같은 응답자의 received_at 은 단조 증가한다", case_monotonic),
)


def main() -> int:
    print("check_workbench_write — 워크벤치 응답 쓰기 (plan_workbench_spec §6)")
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
