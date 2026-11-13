#!/usr/bin/env python3
"""주장 트리 계획 — 응답 파일 · 받은편지함 · `plan-import` (ADR-031 2단계, `core/claim_plan_spec.md` §6~§9 · §11).

1. 자격 표 — 응답 바이트 → 처음 어긋난 단계(1~6) 를 **전부** 대조한다 (한도의 경계 포함)
2. 자격 없는 응답은 옮겨지지 않고 받은편지함에 남는다; 0 단계(task 파일의 오류 규칙)에서는 `--apply` · `--discard` 가
   rc 1 · `plan_lint_error` · 무변경이고, task 를 고친 뒤 같은 호출이 통한다
3. 정상 반영 — 보관으로 옮기고, 상태 칸을 적고, Progress 한 줄; dry-run 은 같은 판정에 무변경; 다시 불러도 그대로다
4. 순서 무관 — 같은 응답 집합을 일괄 · 하나씩 · 도착 사이사이에 반영해도 끝 상태 칸이 같고 순수 계산과 같다
5. `--discard` — `.rejected.md` 로 옮기고 다시 계산한다; 뒤 응답을 거두면 앞 응답이 다시 유효하다; 사유가 Progress 에 남는다
6. 번호는 접미사를 통틀어 유일하고 이동은 있는 파일을 덮지 않는다; 보관에 손으로 놓인 · 지문이 바뀐 응답은 세지 않는다
7. 잠금을 못 쥔 `plan-import` 는 `import_busy` (rc 0 · 무변경)다 — `--apply` 와 `--discard --apply` 둘 다
8. `inbox/.gitignore` 는 매번 `*\\n` 으로 되돌아간다
9. 경합 — 같은 `received_at` 으로 쓰는 쪽 넷 × 옮기는 쪽 둘: 중복 0 · 유실 0
10. 이어받기 — seed · 합류 이월 · 되돌려 적기가 보관 응답(`.md`)을 옮기고, 받은편지함 · `.rejected.md` 는 옮기지 않는다
11. 읽는 길은 디렉터리를 만들지 않는다 — dry-run · `plan-status` 뒤에도 `plan_responses/` 가 없다
12. 출력 계약 · 인자 — family `plan_import` 로 검증되고, 모르는 인자 · 접두 축약 · 받은편지함 밖의 경로는 거절된다
"""

from __future__ import annotations

#: 다중 프로세스 경합과 subprocess CLI 를 돌린다 — 기본 60s 상한을 넘는다.
CHECK_TIMEOUT_S = 240

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import contextlib
import hashlib
import io
import itertools
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import plan_claims as pc  # noqa: E402
from workflow_kit.common import plan_responses as pr  # noqa: E402
from workflow_kit.common import plan_tasks  # noqa: E402
from workflow_kit.common.output_contracts import validate_output_payload  # noqa: E402

BRANCH = "plan-import"
BACKLOG_UPDATE = SOURCE_ROOT / "workflow_kit" / "tools" / "backlog_update.py"
D1 = "D1 [C1] 막는가? | default: block | options: block = 거부한다; warn = 경고만 낸다"
D2 = "D2 [C2] 어느 쪽인가? | default: a | options: a = 가; b = 나"
AT = "2026-11-13T21:04:11.{:06d}+09:00"

FAILURES: list[str] = []


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    env["CODEX_WORKFLOW_BRANCH"] = BRANCH
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _workspace(td: str) -> Path:
    ws = Path(td)
    (ws / "docs").mkdir(parents=True)
    (ws / "docs" / "PROJECT_PROFILE.md").write_text("# Profile\n", encoding="utf-8")
    base = _branch(ws)
    (base / "backlog" / "tasks").mkdir(parents=True)
    (base / "sessions").mkdir(parents=True)
    return ws


def _branch(ws: Path) -> Path:
    return ws / "ai-workflow" / "memory" / "active" / BRANCH


def _snapshot(ws: Path) -> str:
    """작업 공간의 지문. 잠금 파일(`inbox/.lock`)은 뺀다 — 잠금을 쥐어 보는 것 자체가 그 파일을 만든다."""
    digest = hashlib.sha256()
    for path in sorted((ws / "ai-workflow").rglob("*")):
        if path.is_file() and "telemetry" not in path.parts and path.name != pr.LOCK_FILENAME:
            digest.update(path.relative_to(ws).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _cli(ws: Path, script_or_module: list[str], *args: str) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, *script_or_module, "--project-profile-path", str(ws / "docs" / "PROJECT_PROFILE.md"), *args],
        capture_output=True, encoding="utf-8", errors="replace", check=False, env=_env(), cwd=str(ws))
    try:
        return proc.returncode, json.loads(proc.stdout)
    except json.JSONDecodeError:
        return proc.returncode, {"_raw": proc.stdout[-300:], "_err": proc.stderr[-600:]}


def _backlog(ws: Path, *args: str) -> tuple[int, dict]:
    return _cli(ws, [str(BACKLOG_UPDATE)], "--target-date", "2026-11-13", "--apply", *args)


def _import(ws: Path, *args: str) -> tuple[int, dict]:
    return _cli(ws, ["-m", "workflow_kit", "plan-import"], *args)


def _create(ws: Path, *decisions: str, name: str = "응답을 받는 task") -> str:
    rc, out = _backlog(
        ws, "--mode", "create", "--status", "planned", "--task-name", name, "--task-brief", "b",
        "--done-criteria", "[C1] 닫히지 않는다", "--done-criteria", "[C2] 그대로다",
        "--plan-claim", "C1 열린 결정이 남으면 닫히지 않는다", "--plan-claim", "C2 옛 task 는 그대로 읽힌다",
        *itertools.chain.from_iterable(("--plan-decision", d) for d in (decisions or (D1, D2))))
    if rc != 0:
        raise AssertionError(f"create 실패: {out}")
    return str(out["task_id"])


def _task_path(ws: Path, task_id: str) -> Path:
    return _branch(ws) / "backlog" / "tasks" / f"{task_id}.md"


def _plan(ws: Path, task_id: str) -> pc.Plan:
    task = plan_tasks.read_task_plan(_task_path(ws, task_id))
    assert task is not None
    return task.plan


def _columns(ws: Path, task_id: str) -> dict[str, str]:
    return {d.id: d.state for d in _plan(ws, task_id).decisions}


def _progress(ws: Path, task_id: str) -> str:
    for line in _task_path(ws, task_id).read_text(encoding="utf-8").splitlines():
        if line.startswith("- Progress:"):
            return line[len("- Progress:"):].strip()
    return ""


def _response(ws: Path, task_id: str, responder: str, micro: int = 1, *, values: dict[str, str] | None = None,
              opened: dict[str, bool] | None = None, comments: list[tuple[str, str]] | None = None,
              role: str = pr.ROLE_APPROVER) -> bytes:
    return pr.render_response(
        task_id=task_id, plan=_plan(ws, task_id), responder=responder, received_at=AT.format(micro),
        values=values, opened=opened, comments=comments, role=role).encode("utf-8")


def _publish(ws: Path, task_id: str, data: bytes) -> Path:
    return pr.publish(_branch(ws), task_id, data)


def _archive(ws: Path, task_id: str) -> list[str]:
    return [p.name for p in pr.archive_files(_branch(ws), task_id)]


def _inbox(ws: Path, task_id: str) -> list[str]:
    return [p.name for p in pr.inbox_files(_branch(ws), task_id)]


# --------------------------------------------------------------------------- case 1


TASK = "TASK-2026-11-13-plan-import-001"
PLAN = pc.parse_plan_values(["C1 하나를 한다", "C2 둘을 한다"], [D1, D2])


def _base(**kw: object) -> str:
    args: dict = dict(task_id=TASK, plan=PLAN, responder="kim", received_at=AT.format(1))
    args.update(kw)
    return pr.render_response(**args)


def _swap(old: str, new: str) -> bytes:
    text = _base()
    assert old in text, old
    return text.replace(old, new, 1).encode("utf-8")


def _comments(n: int, size: int = 3) -> bytes:
    return _base(comments=[("C1", "가" * size)] * n).encode("utf-8")


def _padded(total: int) -> bytes:
    """정확히 ``total`` 바이트 — 본문 뒤에 어느 절에도 들지 않는 줄로 채운다."""
    text = _base() + "\n## Notes\n\n"
    return (text + "x" * (total - len(text.encode("utf-8")) - 1) + "\n").encode("utf-8")


DIGEST = pc.plan_digest(PLAN)
L1 = "- D1 [C1] value: block | default: block | opened: no"
L2 = "- D2 [C2] value: a | default: a | opened: no"

#: (설명, 응답 바이트, 처음 어긋난 단계 — 자격이 있으면 None).
QUALIFY_TABLE: list[tuple[str, bytes, int | None]] = [
    ("정상", _base().encode(), None),
    ("값을 고른 응답", _base(values={"D1": "warn"}, opened={"D1": True, "D2": True}).encode(), None),
    ("주석이 있는 응답", _base(comments=[("C1.1", "첫 줄\n둘째 줄"), ("-", "전체"), ("D1", "결정")]).encode(), None),
    ("소수 초 없는 시각", _swap(AT.format(1), "2026-11-13T21:04:11+09:00"), None),
    ("Z 가 아닌 음수 오프셋", _swap(AT.format(1), "2026-11-13T21:04:11.5-05:00"), None),
    ("탭은 제어 문자가 아니다", _base(comments=[("C1", "가\t나")]).encode(), None),
    # 1 단계 — 한도 · 인코딩 · 형식
    ("파일 65,536 바이트 (한도 안)", _padded(65_536), None),
    ("파일 65,537 바이트", _padded(65_537), 1),
    ("BOM", b"\xef\xbb\xbf" + _base().encode(), 1),
    ("UTF-8 이 아니다", _base().encode().replace("막".encode(), b"\xff") + b"\xff\xfe", 1),
    ("CRLF", _base().replace("\n", "\r\n").encode(), 1),
    ("CR 하나", _base(comments=[("C1", "가\r나")]).encode(), 1),
    ("NUL", _base(comments=[("C1", "가\x00나")]).encode(), 1),
    ("U+007F", _base(comments=[("C1", "가\x7f나")]).encode(), 1),
    ("U+001F", _base(comments=[("C1", "가\x1f나")]).encode(), 1),
    ("주석 20건 (한도 안)", _comments(20), None),
    ("주석 21건", _comments(21), 1),
    ("주석 1,000 code point (한도 안)", _comments(1, 1000), None),
    ("주석 1,001 code point", _comments(1, 1001), 1),
    ("주석 — 줄바꿈도 센다", _base(comments=[("C1", "가" * 500 + "\n" + "나" * 500)]).encode(), 1),
    ("주석 — 접두는 세지 않는다", _base(comments=[("C1", "\n".join(["가" * 99] * 10))]).encode(), None),
    ("responder 32자 (한도 안)", _base(responder="k" * 32).encode(), None),
    ("responder 33자", _base(responder="k" * 33).encode(), 1),
    ("responder 없음", _swap("responder: kim\n", "responder:\n"), 1),
    ("responder 줄 없음", _swap("responder: kim\n", ""), 1),
    ("received_at 에 시간대가 없다", _swap(AT.format(1), "2026-11-13T21:04:11.000001"), 1),
    ("received_at 이 날짜뿐", _swap(AT.format(1), "2026-11-13"), 1),
    ("received_at 의 날짜와 시각 사이가 공백", _swap(AT.format(1), "2026-11-13 21:04:11+09:00"), 1),
    ("received_at 이 시각이 아니다", _swap(AT.format(1), "어제"), 1),
    ("received_at 줄 없음", _swap(f"received_at: {AT.format(1)}\n", ""), 1),
    # 2 단계 — format
    ("format 이 다른 판", _swap(pr.FORMAT, "workflow-kit-plan-response/2"), 2),
    ("format 줄 없음", _swap(f"format: {pr.FORMAT}\n", ""), 2),
    ("머리말이 없다", _base().split("---\n", 2)[2].encode(), 1),
    ("머리말을 닫지 않았다", _base().replace("---\n\n## Decisions", "\n## Decisions", 1).encode(), 1),
    ("모르는 머리말 키", _swap("role: approver\n", "role: approver\nextra: x\n"), 2),
    ("겹친 머리말 키", _swap("role: approver\n", "role: approver\nrole: viewer\n"), 2),
    # 3 단계 — task
    ("다른 task", _swap(f"task: {TASK}", f"task: {TASK}9"), 3),
    ("task 줄 없음", _swap(f"task: {TASK}\n", ""), 3),
    # 4 단계 — 지문
    ("지문이 다르다", _swap(DIGEST, "sha256:" + "0" * 64), 4),
    ("지문 줄 없음", _swap(f"plan_digest: {DIGEST}\n", ""), 4),
    ("지문의 대소문자", _swap(DIGEST, DIGEST.upper()), 4),
    # 5 단계 — role
    ("role 이 viewer", _base(role="viewer").encode(), 5),
    ("role 줄 없음", _swap("role: approver\n", ""), 5),
    ("role 의 대소문자", _base(role="Approver").encode(), 5),
    # 6 단계 — 결정 줄
    ("결정 하나가 빠졌다", _swap(L2 + "\n", ""), 6),
    ("결정이 하나도 없다", _swap(L1 + "\n" + L2 + "\n", ""), 6),
    ("없는 결정이 더 있다", _swap(L2, L2 + "\n- D3 [C1] value: a | default: a | opened: no"), 6),
    ("같은 결정이 두 번", _swap(L2, L2 + "\n" + L2), 6),
    ("주장 ID 가 다르다", _swap("D1 [C1]", "D1 [C2]"), 6),
    ("default 가 다르다", _swap("value: block | default: block", "value: warn | default: warn"), 6),
    ("value 가 선택지 밖", _swap("value: block |", "value: nope |"), 6),
    ("opened 가 yes · no 가 아니다", _swap(L1, L1.replace("opened: no", "opened: maybe")), 6),
    ("opened 의 대소문자", _swap(L1, L1.replace("opened: no", "opened: Yes")), 6),
    ("결정 줄을 읽을 수 없다", _swap(L1, "- D1 block"), 6),
    ("결정은 다 있는데 읽을 수 없는 줄이 더 있다", _swap(L2, L2 + "\n- D1 block"), 6),
    ("결정 줄의 칸 순서가 다르다", _swap(L1, "- D1 [C1] default: block | value: block | opened: no"), 6),
    # 겹치면 앞 단계
    ("1 과 2 가 겹친다", _swap(pr.FORMAT, "x").replace(b"\n", b"\r\n"), 1),
    ("2 와 5 가 겹친다", _swap(pr.FORMAT, "x").replace(b"role: approver", b"role: viewer"), 2),
    ("3 과 4 가 겹친다", _swap(f"task: {TASK}", "task: T").replace(DIGEST.encode(), b"sha256:0"), 3),
    ("4 와 6 이 겹친다", _swap(DIGEST, "sha256:0").replace(b"value: block |", b"value: nope |"), 4),
    ("5 와 6 이 겹친다", _base(role="viewer").encode().replace(b"value: block |", b"value: nope |"), 5),
]


def case_1_qualification_table() -> None:
    problems: list[str] = []
    for label, data, expected in QUALIFY_TABLE:
        got = pr.qualify(pr.parse_response(data), PLAN, TASK).stage
        if got != expected:
            problems.append(f"{label}: 단계 {got!r} (기대 {expected!r})")
    # 읽은 값 — 입장의 재료가 그대로 넘어간다.
    parsed = pr.parse_response(_base(values={"D1": "warn"}, opened={"D2": True},
                                     comments=[("C1", "가\n나"), ("-", "다")]).encode(), name="n.md")
    response = pr.as_response(parsed)
    if (response.stance("D1"), response.stance("D2")) != ("warn", "a") or response.name != "n.md":
        problems.append(f"읽은 응답의 입장이 다르다: {response}")
    if parsed.comments != (("C1", "가\n나"), ("-", "다")) or response.responder != "kim":
        problems.append(f"주석 · 응답자를 다르게 읽었다: {parsed.comments}")
    if response.content_sha256 != hashlib.sha256(_base(values={"D1": "warn"}, opened={"D2": True},
                                                 comments=[("C1", "가\n나"), ("-", "다")]).encode()).hexdigest():
        problems.append("content_sha256 이 파일 바이트의 것이 아니다")
    unopened = pr.as_response(pr.parse_response(_base().encode()))
    if unopened.stance("D1") is not None:
        problems.append("열리지 않은 기본값이 입장으로 읽혔다")
    # 번호의 출발값 = received_at 의 epoch 마이크로초.
    if pr.received_micros("1970-01-01T00:00:01.000002+00:00") != 1_000_002:
        problems.append("번호의 출발값이 epoch 마이크로초가 아니다")
    if pr.received_micros("1970-01-01T09:00:00+09:00") != 0:
        problems.append("번호가 시간대 오프셋을 반영하지 않는다")
    # 오류 규칙을 어긴 계획에서는 보관 응답이 하나도 자격이 없다 (0 단계).
    broken = pc.parse_plan_values(["C1 하나", "C1 겹친다"], [D1])
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / pr.RESPONSES_DIRNAME).mkdir()
        good = pc.parse_plan_values(["C1 하나"], [D1])
        (Path(td) / pr.RESPONSES_DIRNAME / f"{TASK}-5.md").write_bytes(
            pr.render_response(task_id=TASK, plan=good, responder="kim", received_at=AT.format(1)).encode())
        if len(pr.qualified_archive(Path(td), TASK, good)) != 1:
            problems.append("자격 있는 보관 응답을 읽지 못했다")
        # 그 계획의 지문에 맞춘 응답이다 — 1~6 단계는 전부 통과한다. 떨어뜨리는 것은 0 단계뿐이다.
        fits_broken = pr.render_response(task_id=TASK, plan=broken, responder="kim", received_at=AT.format(1)).encode()
        if pr.qualify(pr.parse_response(fits_broken), broken, TASK).stage is not None:
            problems.append("fixture: 오류 계획에 맞춘 응답이 1~6 단계에서 떨어진다 — 0 단계를 재지 못한다")
        (Path(td) / pr.RESPONSES_DIRNAME / f"{TASK}-6.md").write_bytes(fits_broken)
        if pr.qualified_archive(Path(td), TASK, broken):
            problems.append("오류 규칙을 어긴 계획에서 보관 응답이 자격을 얻었다")
        judged = pr.judge(Path(td) / pr.RESPONSES_DIRNAME / f"{TASK}-6.md", broken, TASK, plan_has_errors=True)[1]
        if judged.stage != 0:
            problems.append(f"오류 규칙을 어긴 계획의 판정이 0 단계가 아니다: {judged.stage}")
    _record(f"case 1 (자격 표 — {len(QUALIFY_TABLE)} 입력의 단계 전부 대조)", problems)


# --------------------------------------------------------------------------- case 2


def case_2_ineligible_stays_and_stage_zero() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _create(ws)
        good = _response(ws, task_id, "kim").decode()
        digest = pc.plan_digest(_plan(ws, task_id))
        bad = {
            1: good.replace("\n", "\r\n"),
            2: good.replace(pr.FORMAT, "other/1"),
            3: good.replace(f"task: {task_id}", f"task: {task_id}9"),
            4: good.replace(digest, "sha256:" + "1" * 64),
            5: good.replace("role: approver", "role: viewer"),
            6: good.replace("value: block |", "value: nope |"),
        }
        names: dict[str, int] = {}
        for stage, text in bad.items():
            # 손으로 놓는다 — 쓰는 쪽이 번호를 정한다.
            path = pr.ensure_inbox(_branch(ws)) / f"{task_id}-{stage}.md"
            path.write_bytes(text.encode("utf-8"))
            names[path.name] = stage
        before = _snapshot(ws)
        for apply in (False, True):
            rc, out = _import(ws, "--task", task_id, *(("--apply",) if apply else ()))
            got = {r["name"]: (r["stage"], r["eligible"], r["action"]) for r in out.get("responses", [])}
            want = {name: (stage, False, "kept_in_inbox") for name, stage in names.items()}
            if rc != 0 or got != want:
                problems.append(f"apply={apply}: 파일별 단계가 다르다 rc={rc} {got}")
            if out.get("applied") or out.get("pending_responses") != 6:
                problems.append(f"apply={apply}: applied={out.get('applied')} pending={out.get('pending_responses')}")
            if _snapshot(ws) != before or _archive(ws, task_id):
                problems.append(f"apply={apply}: 자격 없는 응답뿐인데 무엇인가 바뀌었다")
        # 자격 없는 응답은 다른 응답의 판정에 영향이 없다.
        _publish(ws, task_id, _response(ws, task_id, "lee", 7, values={"D1": "warn"}))
        rc, out = _import(ws, "--task", task_id, "--apply")
        if rc != 0 or len(_archive(ws, task_id)) != 1 or len(_inbox(ws, task_id)) != 6:
            problems.append(f"자격 있는 응답만 옮겨져야 한다: 보관 {_archive(ws, task_id)} 받은편지함 {len(_inbox(ws, task_id))}")
        if _columns(ws, task_id).get("D1") != "changed:warn":
            problems.append(f"자격 있는 응답이 반영되지 않았다: {_columns(ws, task_id)}")

    # 0 단계 — task 파일이 오류 규칙을 어긴다.
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _create(ws)
        inbox_file = _publish(ws, task_id, _response(ws, task_id, "kim", values={"D1": "warn"}))
        _publish(ws, task_id, _response(ws, task_id, "lee", 2))
        rc, _ = _import(ws, "--task", task_id, "--response", inbox_file.name, "--apply")
        archived = _archive(ws, task_id)
        path = _task_path(ws, task_id)
        healthy = path.read_text(encoding="utf-8")
        path.write_text(healthy.replace("- Claims: C2 ", "- Claims: C1 ", 1), encoding="utf-8")  # L2 — 겹친 ID
        before = _snapshot(ws)
        calls = {
            "dry-run": ("--task", task_id),
            "--apply": ("--task", task_id, "--apply"),
            "--discard(보관)": ("--discard", archived[0], "--reason", "잘못 받았다", "--apply"),
            "--discard(받은편지함)": ("--discard", _inbox(ws, task_id)[0], "--reason", "잘못 받았다", "--apply"),
            "--discard dry-run": ("--discard", archived[0], "--reason", "잘못 받았다"),
        }
        for label, args in calls.items():
            rc, out = _import(ws, *args)
            if rc != 1 or out.get("error_code") != "plan_lint_error" or out.get("status") != "error":
                problems.append(f"0 단계 {label}: rc={rc} {out.get('error_code')}")
            if _snapshot(ws) != before:
                problems.append(f"0 단계 {label}: 거부인데 무엇인가 바뀌었다")
        if plan_tasks.archived_responses(plan_tasks.read_task_plan(path)):  # type: ignore[arg-type]
            problems.append("0 단계인데 보관 응답이 계산에 들었다")
        # 오류 계획의 지문에 맞춘 응답 — 1~6 단계를 통과하므로 0 단계만이 떨어뜨린다.
        fits = pr.inbox_dir(_branch(ws)) / f"{task_id}-3.md"
        fits.write_bytes(_response(ws, task_id, "han", 3))
        archived_fits = _branch(ws) / pr.RESPONSES_DIRNAME / f"{task_id}-4.md"
        archived_fits.write_bytes(_response(ws, task_id, "han", 4, values={"D1": "warn"}))
        if plan_tasks.archived_responses(plan_tasks.read_task_plan(path)):  # type: ignore[arg-type]
            problems.append("0 단계인데 오류 계획에 맞춘 보관 응답이 계산에 들었다")
        _, status = _cli(ws, ["-m", "workflow_kit", "plan-status"], "--task", task_id)
        stages = {r["name"]: r["stage"] for r in status.get("inbox", [])}
        if stages.get(fits.name) != 0 or set(stages.values()) != {0}:
            problems.append(f"plan-status 가 0 단계를 보고하지 않았다: {stages}")
        if any(d["state"] != "proposed" for d in status.get("decisions", [])):
            problems.append(f"0 단계인데 plan-status 의 계산 상태가 proposed 가 아니다: {status.get('decisions')}")
        fits.unlink()
        archived_fits.unlink()
        # 고친 뒤 같은 호출이 통한다.
        path.write_text(healthy, encoding="utf-8")
        rc, out = _import(ws, *calls["--discard(보관)"])
        if rc != 0 or out.get("outcome") != "discarded" or _archive(ws, task_id):
            problems.append(f"task 를 고친 뒤의 --discard 가 통하지 않았다: rc={rc} {out.get('outcome')}")
        rc, out = _import(ws, *calls["--apply"])
        if rc != 0 or len(_archive(ws, task_id)) != 1 or _inbox(ws, task_id):
            problems.append(f"task 를 고친 뒤의 --apply 가 통하지 않았다: rc={rc} 보관 {_archive(ws, task_id)}")
    _record("case 2 (자격 없는 응답은 남는다 · 0 단계는 아무것도 옮기지 않는다)", problems)


# --------------------------------------------------------------------------- case 3


def case_3_import_archives_and_records() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _create(ws)
        data = _response(ws, task_id, "kim", 42, values={"D1": "warn"},
                         comments=[("C1", "하나"), ("-", "둘")])
        published = _publish(ws, task_id, data)
        number = pr.received_micros(AT.format(42))
        if published.name != f"{task_id}-{number}.md":
            problems.append(f"받은편지함 이름의 번호가 received_at 의 epoch 마이크로초가 아니다: {published.name}")
        before = _snapshot(ws)
        rc, dry = _import(ws, "--task", task_id)
        if rc != 0 or _snapshot(ws) != before or dry.get("applied") is not False or dry.get("outcome") != "dry_run":
            problems.append(f"dry-run 이 무엇인가 썼다: rc={rc} applied={dry.get('applied')}")
        rc, out = _import(ws, "--task", task_id, "--apply")
        archive_rel = f"ai-workflow/memory/active/{BRANCH}/plan_responses/{task_id}-{number}.md"
        if rc != 0 or out.get("outcome") != "imported" or out.get("applied") is not True:
            problems.append(f"반영 실패: rc={rc} {out.get('outcome')} {out.get('_err')}")
        if _archive(ws, task_id) != [f"{task_id}-{number}.md"] or _inbox(ws, task_id):
            problems.append(f"보관 이름이 번호 그대로가 아니다: {_archive(ws, task_id)} / 받은편지함 {_inbox(ws, task_id)}")
        if (_branch(ws) / pr.RESPONSES_DIRNAME / f"{task_id}-{number}.md").read_bytes() != data:
            problems.append("보관된 파일의 바이트가 바뀌었다")
        if _columns(ws, task_id) != {"D1": "changed:warn", "D2": "unopened"}:
            problems.append(f"상태 칸: {_columns(ws, task_id)}")
        want = f"plan 응답 1건 (kim): 결정 2 (바뀜 1 · 유지 0 · 미열람 1 · 다툼 0) · 주석 2 · 대체 0 — {archive_rel}"
        if _progress(ws, task_id) != want or out.get("progress_line") != want:
            problems.append(f"Progress 한 줄이 스펙 §9 와 다르다: {_progress(ws, task_id)}")
        # dry-run 과 --apply 의 판정이 같다.
        for key in ("states", "open_decisions", "state_changes", "progress_line"):
            if dry.get(key) != out.get(key):
                problems.append(f"dry-run 과 --apply 의 {key} 가 다르다: {dry.get(key)} / {out.get(key)}")
        if [(r["name"], r["action"], r["moved_to"]) for r in dry["responses"]] != [
                (r["name"], r["action"], r["moved_to"]) for r in out["responses"]]:
            problems.append("dry-run 이 예고한 이동이 실제와 다르다")
        if out.get("state_changes") != [{"id": "D1", "before": "proposed", "after": "changed:warn"},
                                        {"id": "D2", "before": "proposed", "after": "unopened"}]:
            problems.append(f"state_changes: {out.get('state_changes')}")
        if out.get("open_decisions") != ["D2"] or out.get("pending_responses") != 0:
            problems.append(f"open_decisions={out.get('open_decisions')} pending={out.get('pending_responses')}")
        # 다시 불러도 그대로다.
        before = _snapshot(ws)
        rc, again = _import(ws, "--task", task_id, "--apply")
        if rc != 0 or _snapshot(ws) != before or again.get("applied") or again.get("outcome") != "nothing_to_do":
            problems.append(f"다시 부른 --apply 가 무엇인가 바꿨다: {again.get('outcome')}")
        # task 의 status 는 건드리지 않는다 — done 인 task 도 받는다.
        text = _task_path(ws, task_id).read_text(encoding="utf-8")
        _task_path(ws, task_id).write_text(text.replace("status: planned", "status: done", 1), encoding="utf-8")
        _publish(ws, task_id, _response(ws, task_id, "lee", 50, values={"D1": "block"}, opened={"D1": True}))
        rc, late = _import(ws, "--task", task_id, "--apply")
        status = next(line for line in _task_path(ws, task_id).read_text(encoding="utf-8").splitlines()
                      if line.startswith("status:"))
        if rc != 0 or status != "status: done" or _columns(ws, task_id).get("D1") != "disputed":
            problems.append(f"done 인 task 에 온 반대: rc={rc} {status} {_columns(ws, task_id)}")
        if "결정 2 (바뀜 0 · 유지 0 · 미열람 1 · 다툼 1)" not in _progress(ws, task_id):
            problems.append(f"다툼의 계수: {_progress(ws, task_id)}")
        if not any("다툼에 든 응답" in w for w in late.get("warnings", [])):
            problems.append(f"다툼에 든 응답을 알리지 않았다: {late.get('warnings')}")
        # 같은 응답자의 뒤 응답은 앞 응답을 대체한다 — "대체 1".
        _publish(ws, task_id, _response(ws, task_id, "lee", 60, values={"D1": "warn"}))
        rc, _ = _import(ws, "--task", task_id, "--apply")
        if "· 대체 1 —" not in _progress(ws, task_id) or _columns(ws, task_id).get("D1") != "changed:warn":
            problems.append(f"대체: {_progress(ws, task_id)} {_columns(ws, task_id)}")
        # CRLF 로 저장된 task 파일의 줄바꿈을 바꾸지 않는다.
        crlf = _task_path(ws, task_id).read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        _task_path(ws, task_id).write_bytes(crlf)
        _publish(ws, task_id, _response(ws, task_id, "park", 70, values={"D2": "b"}))
        rc, _ = _import(ws, "--task", task_id, "--apply")
        raw = _task_path(ws, task_id).read_bytes()
        if rc != 0 or raw.count(b"\r\n") != raw.count(b"\n") or b"changed:b" not in raw:
            problems.append("CRLF task 파일의 줄바꿈이 바뀌었거나 칸이 적히지 않았다")
    _record("case 3 (반영 — 보관 · 상태 칸 · Progress 한 줄 · dry-run 무변경 · 멱등)", problems)


# --------------------------------------------------------------------------- case 4


def _spec(responder: str, micro: int, d1: str | None, d2: str | None = None) -> dict:
    """응답 한 건 — 값이 ``None`` 이면 열지 않은 기본값, ``"="`` 이면 열어 본 기본값."""
    values, opened = {}, {}
    for decision, value, default in (("D1", d1, "block"), ("D2", d2, "a")):
        if value == "=":
            values[decision], opened[decision] = default, True
        elif value is not None:
            values[decision] = value
    return {"responder": responder, "micro": micro, "values": values, "opened": opened}


ORDER_SETS: dict[str, list[dict]] = {
    "둘이 갈린다": [_spec("a", 1, "warn"), _spec("b", 2, "=")],
    "같은 값 뒤 반대": [_spec("a", 1, "warn"), _spec("b", 2, "warn"), _spec("b", 3, "=")],
    "한 사람이 말을 바꾼다": [_spec("a", 1, "warn"), _spec("a", 2, "=")],
    "뒤 응답이 입장 없음": [_spec("a", 1, "warn"), _spec("a", 2, None)],
    "다른 결정": [_spec("a", 1, "warn"), _spec("b", 2, None, "b")],
    "세 사람": [_spec("a", 1, "warn", "b"), _spec("b", 2, "warn"), _spec("c", 3, None, "=")],
    "같은 received_at": [_spec("a", 5, "warn"), _spec("b", 5, "="), _spec("a", 5, "=")],
}


#: 스펙 §8 을 손으로 푼 끝 상태 — 순수 계산과 CLI 가 함께 틀리면 이 표가 잡는다.
#: ("같은 received_at" 은 동률을 파일 내용의 sha256 으로 가른다 — 손으로 풀 값이 아니다.)
EXPECTED_END: dict[str, dict[str, str]] = {
    "둘이 갈린다": {"D1": "disputed", "D2": "unopened"},
    "같은 값 뒤 반대": {"D1": "disputed", "D2": "unopened"},
    "한 사람이 말을 바꾼다": {"D1": "kept", "D2": "unopened"},
    "뒤 응답이 입장 없음": {"D1": "unopened", "D2": "unopened"},
    "다른 결정": {"D1": "changed:warn", "D2": "changed:b"},
    "세 사람": {"D1": "changed:warn", "D2": "disputed"},
}


def _final_state(
    specs: list[dict], order: tuple[int, ...], mode: str,
) -> tuple[dict[str, str], dict[str, str], list[str]]:
    """(끝 상태 칸, 같은 응답 바이트의 순수 계산, 문제)."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _create(ws)
        problems: list[str] = []
        blobs = [_response(ws, task_id, s["responder"], s["micro"], values=s["values"], opened=s["opened"])
                 for s in specs]
        # 순수 계산 — 도착 · 반영의 순서를 모르는 쪽. 응답 집합만 받는다.
        pure = pc.compute_states(
            _plan(ws, task_id), [pr.as_response(pr.parse_response(blob)) for blob in blobs]).states
        for index in order:
            path = _publish(ws, task_id, blobs[index])
            if mode == "each":
                rc, _ = _import(ws, "--task", task_id, "--response", path.name, "--apply")
            elif mode == "arrival":
                rc, _ = _import(ws, "--task", task_id, "--apply")
            else:
                rc = 0
            if rc != 0:
                problems.append(f"import rc={rc}")
        if mode == "batch":
            rc, _ = _import(ws, "--task", task_id, "--apply")
            if rc != 0:
                problems.append(f"import rc={rc}")
        columns = _columns(ws, task_id)
        before = _snapshot(ws)
        _import(ws, "--task", task_id, "--apply")
        if _snapshot(ws) != before:
            problems.append("다시 부른 import 가 무엇인가 바꿨다")
        if len(_archive(ws, task_id)) != len(specs) or _inbox(ws, task_id):
            problems.append(f"보관 {len(_archive(ws, task_id))}건 (기대 {len(specs)})")
        return columns, pure, problems


def case_4_order_independence() -> None:
    problems: list[str] = []
    seen_states: set[str] = set()
    for label, specs in ORDER_SETS.items():
        reached: set[tuple[tuple[str, str], ...]] = set()
        orders = list(itertools.permutations(range(len(specs))))
        if len(orders) > 3:
            orders = [orders[0], orders[len(orders) // 2], orders[-1]]
        for order in orders:
            for mode in ("batch", "each", "arrival"):
                got, expected, found = _final_state(specs, order, mode)
                problems.extend(f"{label} {order} {mode}: {p}" for p in found)
                if got != expected:
                    problems.append(f"{label} {order} {mode}: {got} (순수 계산 {expected})")
                reached.add(tuple(sorted(got.items())))
                seen_states.update(state.split(":")[0] for state in got.values())
        if len(reached) != 1:
            problems.append(f"{label}: 끝 상태가 {len(reached)}종이다 — {sorted(reached)}")
        want = EXPECTED_END.get(label)
        if want is not None and reached != {tuple(sorted(want.items()))}:
            problems.append(f"{label}: 끝 상태 {sorted(reached)} (스펙 §8 로 손으로 푼 값 {want})")
    for state in ("disputed", "kept", "changed", "unopened"):
        if state not in seen_states:
            problems.append(f"집합들이 {state} 를 한 번도 만들지 않았다 — 표가 그 상태를 재지 않는다")
    _record("case 4 (순서 무관 — 일괄 · 하나씩 · 도착 사이사이의 끝 상태가 순수 계산과 같다)", problems)


# --------------------------------------------------------------------------- case 5


def case_5_discard() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _create(ws)
        _publish(ws, task_id, _response(ws, task_id, "kim", 1, values={"D1": "warn"}))
        _import(ws, "--task", task_id, "--apply")
        _publish(ws, task_id, _response(ws, task_id, "kim", 2, values={"D1": "block"}, opened={"D1": True}))
        _import(ws, "--task", task_id, "--apply")
        if _columns(ws, task_id).get("D1") != "kept":
            problems.append(f"뒤 응답이 앞 응답을 대체하지 않았다: {_columns(ws, task_id)}")
        first, second = _archive(ws, task_id)
        # 사유가 없으면 거절한다 — 공백뿐인 값도 사유가 아니다. 대상 파일이 있는 동안 잰다.
        before = _snapshot(ws)
        for extra in ((), ("--reason", "   "), ("--reason", "-")):
            proc = subprocess.run(
                [sys.executable, "-m", "workflow_kit", "plan-import", "--project-profile-path",
                 str(ws / "docs" / "PROJECT_PROFILE.md"), "--discard", second, *extra, "--apply"],
                capture_output=True, encoding="utf-8", errors="replace", check=False, env=_env(), cwd=str(ws))
            if proc.returncode != 2 or _snapshot(ws) != before:
                problems.append(f"사유 없는 --discard {extra}: rc {proc.returncode} 무변경={_snapshot(ws) == before}")
        before = _snapshot(ws)
        rc, dry = _import(ws, "--discard", second, "--reason", "잘못 눌렀다")
        if rc != 0 or _snapshot(ws) != before or dry.get("states", {}).get("D1") != "changed:warn":
            problems.append(f"--discard dry-run: rc={rc} {dry.get('states')} 무변경={_snapshot(ws) == before}")
        rc, out = _import(ws, "--discard", second, "--reason", "잘못 눌렀다", "--apply")
        rejected = second.replace(".md", ".rejected.md")
        if rc != 0 or out.get("outcome") != "discarded" or _archive(ws, task_id) != [first]:
            problems.append(f"--discard: rc={rc} {out.get('outcome')} 보관 {_archive(ws, task_id)}")
        if not (_branch(ws) / pr.RESPONSES_DIRNAME / rejected).is_file():
            problems.append(f"거둔 응답이 {rejected} 로 남지 않았다")
        if _columns(ws, task_id).get("D1") != "changed:warn":
            problems.append(f"뒤 응답을 거뒀는데 앞 응답이 다시 유효해지지 않았다: {_columns(ws, task_id)}")
        progress = _progress(ws, task_id)
        if "잘못 눌렀다" not in progress or rejected not in progress or "D1 kept → changed:warn" not in progress:
            problems.append(f"Progress 에 사유 · 경로 · 재계산이 없다: {progress}")
        if dry.get("state_changes") != out.get("state_changes") or dry["responses"][0]["moved_to"] != out["responses"][0]["moved_to"]:
            problems.append("--discard 의 dry-run 과 --apply 가 다르다")
        # 받은편지함의 응답도 거둔다 — 상태는 그대로다.
        pending = _publish(ws, task_id, _response(ws, task_id, "lee", 3, values={"D1": "block"}, opened={"D1": True}))
        rc, out = _import(ws, "--discard", str(pending), "--reason", "중복", "--apply")
        if rc != 0 or _inbox(ws, task_id) or _columns(ws, task_id).get("D1") != "changed:warn":
            problems.append(f"받은편지함 응답의 --discard: rc={rc} 받은편지함 {_inbox(ws, task_id)}")
        if out.get("responses", [{}])[0].get("location") != "inbox":
            problems.append("거둔 응답의 위치가 inbox 가 아니다")
        # 마지막 보관 응답까지 거두면 proposed 다. 거둔 것은 다시 거둘 수 없다 — 지우는 명령은 없다.
        _import(ws, "--discard", first, "--reason", "철회", "--apply")
        if _columns(ws, task_id) != {"D1": "proposed", "D2": "proposed"}:
            problems.append(f"전부 거둔 뒤의 상태: {_columns(ws, task_id)}")
        before = _snapshot(ws)
        rc, out = _import(ws, "--discard", rejected, "--reason", "한 번 더", "--apply")
        if rc == 0 or _snapshot(ws) != before:
            problems.append(f"거둔 응답을 다시 거뒀다: rc={rc}")
        files = sorted(p.name for p in (_branch(ws) / pr.RESPONSES_DIRNAME).iterdir() if p.is_file())
        if len(files) != 3 or not all(name.endswith(pr.REJECTED_SUFFIX) for name in files):
            problems.append(f"거둔 응답 셋이 남아야 한다: {files}")
    _record("case 5 (--discard — .rejected.md · 재계산 · 사유 · 앞 응답이 다시 유효)", problems)


# --------------------------------------------------------------------------- case 6


def case_6_numbers_and_exclusive_move() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _create(ws)
        branch = _branch(ws)
        archive = branch / pr.RESPONSES_DIRNAME
        number = pr.received_micros(AT.format(9)) or 0
        # 같은 번호가 보관에 `.rejected.md` 로 있다 → 1 을 더한다 (번호는 접미사를 통틀어 유일하다).
        pr.ensure_inbox(branch)
        (archive / f"{task_id}-{number}.rejected.md").write_bytes(b"old")
        (archive / f"{task_id}-{number + 1}.md").write_bytes(b"hand")  # 손으로 놓인 것 — 덮이면 안 된다
        first = _publish(ws, task_id, _response(ws, task_id, "kim", 9, values={"D1": "warn"}))
        if first.name != f"{task_id}-{number + 2}.md":
            problems.append(f"쓰는 쪽이 쓰인 번호를 피하지 않았다: {first.name}")
        # 번호를 확인한 뒤 · 놓기 전에 같은 이름이 생겨도 덮지 않는다 — "없으면 만든다" 가 한 번의 호출이어야 한다.
        real_taken = pr.taken_numbers
        pr.taken_numbers = lambda *a, **k: set()  # type: ignore[assignment]  # 낡은 확인 — 아무 번호도 안 쓰였다고 답한다
        try:
            raced = _publish(ws, task_id, _response(ws, task_id, "race", 9, values={"D1": "warn"}))
            victim = pr.inbox_dir(branch) / f"{task_id}-{number + 2}.md"
            if raced.name == victim.name or pr.read_response(victim).responder != "kim":
                problems.append(f"공개가 있는 파일을 덮었다: {raced.name}")
            source = pr.inbox_dir(branch) / f"{task_id}-{number + 1}.md"
            source.write_bytes(_response(ws, task_id, "mover", 9, values={"D1": "warn"}))
            landed = pr.move_exclusive(source, branch, task_id)
            if (archive / f"{task_id}-{number + 1}.md").read_bytes() != b"hand" or landed.name == f"{task_id}-{number + 1}.md":
                problems.append(f"이동이 있는 파일을 덮었다 (낡은 번호 확인): {landed.name}")
            landed.unlink()
        finally:
            pr.taken_numbers = real_taken  # type: ignore[assignment]
        raced.unlink()
        # 같은 received_at 의 두 번째 응답 — 받은편지함에서도 번호가 겹치지 않는다.
        second = _publish(ws, task_id, _response(ws, task_id, "lee", 9, values={"D1": "warn"}))
        if second.name != f"{task_id}-{number + 3}.md":
            problems.append(f"받은편지함에서 번호가 겹쳤다: {second.name}")
        # 받은편지함에 손으로 놓인 파일의 번호가 보관에 이미 있다 → 옮길 때 1 을 더한다.
        clash = pr.inbox_dir(branch) / f"{task_id}-{number}.md"
        clash.write_bytes(_response(ws, task_id, "park", 9, values={"D1": "warn"}))
        rc, out = _import(ws, "--task", task_id, "--apply")
        moved = {r["name"]: r["moved_to"].rsplit("/", 1)[1] for r in out.get("responses", []) if r["action"] == "archived"}
        if rc != 0 or moved.get(clash.name) != f"{task_id}-{number + 4}.md":
            problems.append(f"쓰인 번호로 옮겼다: {moved}")
        if (archive / f"{task_id}-{number}.rejected.md").read_bytes() != b"old" or \
                (archive / f"{task_id}-{number + 1}.md").read_bytes() != b"hand":
            problems.append("이동이 있는 파일을 덮었다")
        names = sorted(p.name for p in archive.iterdir() if p.is_file())
        numbers = [name.split("-")[-1].split(".")[0] for name in names]
        if len(numbers) != len(set(numbers)) or len(names) != 5:
            problems.append(f"번호가 접미사를 통틀어 유일하지 않다: {names}")
        # 보관에 손으로 놓인 파일(자격 없음)은 세지 않는다.
        if _columns(ws, task_id).get("D1") != "changed:warn" or len(plan_tasks.archived_responses(
                plan_tasks.read_task_plan(_task_path(ws, task_id)))) != 3:  # type: ignore[arg-type]
            problems.append(f"손으로 놓인 보관 파일이 계산에 들었다: {_columns(ws, task_id)}")
        # 응답 이동 없이 칸만 바뀌어도 Progress 에 한 줄을 남긴다 — 보관에 직접 놓인 자격 있는 응답.
        (archive / f"{task_id}-777.md").write_bytes(
            _response(ws, task_id, "han", 11, values={"D2": "b"}))
        rc, out = _import(ws, "--task", task_id, "--apply")
        note = "결정 상태 재계산: D2 unopened → changed:b"
        if rc != 0 or _progress(ws, task_id) != note or out.get("progress_line") != note or not out.get("applied"):
            problems.append(f"이동 없는 재계산의 Progress: {_progress(ws, task_id)!r} applied={out.get('applied')}")
        if out.get("outcome") != "imported" or [r for r in out.get("responses", []) if r["action"] == "archived"]:
            problems.append(f"이동 없는 재계산의 outcome: {out.get('outcome')}")
        (archive / f"{task_id}-777.md").unlink()
        _import(ws, "--task", task_id, "--apply")
        # 접두가 겹치는 다른 task 의 파일을 잡지 않는다.
        other = f"{task_id}-001"   # 접두가 겹치는 **다른 task** 의 ID (slug 가 길어진 꼴)
        (archive / f"{other}-1.md").write_bytes(b"x")
        (pr.inbox_dir(branch) / f"{other}-1.md").write_bytes(b"x")
        (pr.inbox_dir(branch) / f"{task_id}-x.md").write_bytes(b"x")
        (pr.inbox_dir(branch) / "notes.md").write_bytes(b"x")
        (pr.inbox_dir(branch) / f".tmp-{task_id}-1").write_bytes(b"x")
        if _inbox(ws, task_id) or len(_archive(ws, task_id)) != 4:  # 손으로 놓인 것 하나 + 옮긴 셋
            problems.append(f"다른 이름의 파일을 그 task 의 응답으로 셌다: {_inbox(ws, task_id)}")
        if pr.pending_by_task(branch) != {other: 1}:
            problems.append(f"받은편지함의 task 별 건수: {pr.pending_by_task(branch)}")
        if pr.unknown_inbox_files(branch) != sorted([f"{task_id}-x.md", "notes.md"]):
            problems.append(f"알 수 없는 파일: {pr.unknown_inbox_files(branch)}")
        rc, out = _import(ws, "--task", task_id)
        if sorted(out.get("unknown_inbox_files", [])) != sorted([f"{task_id}-x.md", "notes.md"]):
            problems.append(f"plan-import 가 알 수 없는 파일을 보고하지 않았다: {out.get('unknown_inbox_files')}")
        # 지문이 바뀌면 보관된 응답도 자격을 잃는다 — 칸은 proposed 로 돌아간다.
        rc, out = _backlog(ws, "--mode", "update", "--task-id", task_id, "--task-name", "응답을 받는 task",
                           "--plan-claim", "C3 새 주장을 더한다")
        if rc != 0 or _columns(ws, task_id).get("D1") != "proposed":
            problems.append(f"지문이 바뀌었는데 옛 응답이 남았다: rc={rc} {_columns(ws, task_id)}")
    _record("case 6 (번호는 접미사를 통틀어 유일 · 이동은 덮지 않는다 · 보관도 자격을 다시 본다)", problems)


# --------------------------------------------------------------------------- case 7 · 8


def case_7_lock_busy() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _create(ws)
        _publish(ws, task_id, _response(ws, task_id, "kim", 1, values={"D1": "warn"}))
        _publish(ws, task_id, _response(ws, task_id, "lee", 2))
        _import(ws, "--task", task_id, "--response", _inbox(ws, task_id)[0], "--apply")
        archived = _archive(ws, task_id)[0]
        before = _snapshot(ws)
        with pr.inbox_lock(_branch(ws)) as held:
            if not held:
                problems.append("검사가 잠금을 쥐지 못했다")
            for label, args in (("--apply", ("--task", task_id, "--apply")),
                                ("--discard --apply", ("--discard", archived, "--reason", "r", "--apply"))):
                rc, out = _import(ws, *args)
                if rc != 0 or out.get("outcome") != "import_busy" or out.get("applied"):
                    problems.append(f"{label}: 잠금을 못 쥐었는데 rc={rc} {out.get('outcome')}")
                if _snapshot(ws) != before:
                    problems.append(f"{label}: import_busy 인데 무엇인가 바뀌었다")
            # dry-run 은 잠금을 쥐지 않는다.
            rc, out = _import(ws, "--task", task_id)
            if rc != 0 or out.get("outcome") != "dry_run":
                problems.append(f"dry-run 이 잠금에 막혔다: {out.get('outcome')}")
        rc, out = _import(ws, "--task", task_id, "--apply")
        if rc != 0 or out.get("outcome") != "imported":
            problems.append(f"잠금이 풀린 뒤의 import: {out.get('outcome')}")
    _record("case 7 (잠금을 못 쥐면 import_busy — rc 0 · 무변경)", problems)


def case_8_inbox_ignores_itself() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _create(ws)
        ignore = pr.inbox_dir(_branch(ws)) / ".gitignore"
        _publish(ws, task_id, _response(ws, task_id, "kim", 1))
        if ignore.read_bytes() != b"*\n":
            problems.append("받은편지함을 만든 쓰기가 .gitignore 를 두지 않았다")
        for label, breakage in (("지워짐", None), ("내용이 다름", b"*.md\n"), ("CRLF", b"*\r\n")):
            if breakage is None:
                ignore.unlink()
            else:
                ignore.write_bytes(breakage)
            _import(ws, "--task", task_id, "--apply")
            if not ignore.is_file() or ignore.read_bytes() != b"*\n":
                problems.append(f"{label}: plan-import --apply 가 .gitignore 를 되돌리지 않았다")
        ignore.write_bytes(b"x\n")
        _publish(ws, task_id, _response(ws, task_id, "lee", 2))
        if ignore.read_bytes() != b"*\n":
            problems.append("쓰는 쪽이 .gitignore 를 되돌리지 않았다")
        # 잠금 파일은 받은편지함 안에 있다 — 커밋 대상 디렉터리에 추적되지 않는 파일을 두지 않는다.
        stray = [p.name for p in (_branch(ws) / pr.RESPONSES_DIRNAME).iterdir() if p.is_file() and not p.name.endswith(".md")]
        if stray or not (pr.inbox_dir(_branch(ws)) / pr.LOCK_FILENAME).is_file():
            problems.append(f"잠금 파일의 자리가 inbox/.lock 이 아니다: {stray}")
    _record("case 8 (inbox/.gitignore 는 매번 `*` 로 되돌아간다)", problems)


# --------------------------------------------------------------------------- case 9 — 경합

WRITERS = 4
PER_WRITER = 15
MOVERS = 2


def _writer(ws: Path, task_id: str, index: int) -> int:
    for n in range(PER_WRITER):
        # 전부 같은 received_at — 번호가 겹치는 길을 일부러 만든다.
        pr.publish(_branch(ws), task_id, _response(ws, task_id, f"w{index}n{n}", 1, values={"D1": "warn"}))
    return 0


def _mover(ws: Path, task_id: str) -> int:
    from workflow_kit.tools import plan_import  # noqa: PLC0415

    os.environ["CODEX_WORKFLOW_BRANCH"] = BRANCH
    stop = ws / "stop"
    profile = str(ws / "docs" / "PROJECT_PROFILE.md")
    while True:
        done = stop.exists()
        with contextlib.redirect_stdout(io.StringIO()):
            plan_import.main(["--project-profile-path", profile, "--task", task_id, "--apply"])
        if done and not pr.inbox_files(_branch(ws), task_id):
            return 0
        time.sleep(0.005)


def case_9_race() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _create(ws)
        me = str(Path(__file__).resolve())
        movers = [subprocess.Popen([sys.executable, me, "--mover", str(ws), task_id], env=_env(), cwd=str(ws),
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) for _ in range(MOVERS)]
        writers = [subprocess.Popen([sys.executable, me, "--writer", str(ws), task_id, str(i)], env=_env(), cwd=str(ws),
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) for i in range(WRITERS)]
        for proc in writers:
            _, err = proc.communicate(timeout=120)
            if proc.returncode != 0:
                problems.append(f"쓰는 쪽이 죽었다: {err.decode('utf-8', 'replace')[-300:]}")
        (ws / "stop").write_text("", encoding="utf-8")
        for proc in movers:
            try:
                _, err = proc.communicate(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
                problems.append("옮기는 쪽이 시간 안에 끝나지 않았다")
                continue
            if proc.returncode != 0:
                problems.append(f"옮기는 쪽이 죽었다: {err.decode('utf-8', 'replace')[-300:]}")
        total = WRITERS * PER_WRITER
        archive = pr.archive_files(_branch(ws), task_id)
        responders = [pr.read_response(p).responder for p in archive]
        if len(archive) != total:
            problems.append(f"보관 {len(archive)}건 (쓴 것 {total}건) — 유실 또는 중복")
        if len(set(responders)) != total:
            problems.append(f"서로 다른 응답 {len(set(responders))}건 (기대 {total}) — 중복 {len(responders) - len(set(responders))}")
        if _inbox(ws, task_id):
            problems.append(f"받은편지함에 {len(_inbox(ws, task_id))}건이 남았다")
        leftovers = [p.name for p in pr.inbox_dir(_branch(ws)).iterdir() if p.name.startswith(".tmp-")]
        if leftovers:
            problems.append(f"임시 파일이 남았다: {leftovers[:3]}")
        if _columns(ws, task_id).get("D1") != "changed:warn":
            problems.append(f"경합 뒤의 상태 칸: {_columns(ws, task_id)}")
    _record(f"case 9 (경합 — 쓰는 쪽 {WRITERS} × 옮기는 쪽 {MOVERS}, {WRITERS * PER_WRITER}건: 중복 0 · 유실 0)", problems)


# --------------------------------------------------------------------------- case 10 — 이어받기


def case_10_inheritance() -> None:
    from workflow_kit.common import branch_inheritance as inherit  # noqa: PLC0415
    from workflow_kit.common import branch_join  # noqa: PLC0415
    from workflow_kit.tools import seed_workspace_memory as seed_tool  # noqa: PLC0415

    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _create(ws)
        rc, _ = _backlog(ws, "--mode", "update", "--task-id", task_id, "--task-name", "응답을 받는 task",
                         "--status", "in_progress")
        _publish(ws, task_id, _response(ws, task_id, "kim", 1, values={"D1": "warn"}, opened={"D2": True}))
        _publish(ws, task_id, _response(ws, task_id, "lee", 2, values={"D1": "block"}, opened={"D1": True}))
        _import(ws, "--task", task_id, "--response", _inbox(ws, task_id)[0], "--apply")
        kept = _archive(ws, task_id)[0]
        _import(ws, "--task", task_id, "--apply")
        _import(ws, "--discard", [n for n in _archive(ws, task_id) if n != kept][0], "--reason", "r", "--apply")
        waiting = _publish(ws, task_id, _response(ws, task_id, "park", 3))
        parent = _branch(ws)
        columns = _columns(ws, task_id)
        if columns != {"D1": "changed:warn", "D2": "kept"}:
            problems.append(f"fixture 의 상태가 다르다: {columns}")
        handoff = parent / "session_handoff.md"
        if not handoff.is_file():
            handoff.write_text("# handoff\n\n## 1. 현재 작업 요약\n\n- 현재 기준선: b\n- 현재 주 작업 축: a\n", encoding="utf-8")
        memory_root = ws / "ai-workflow" / "memory"
        seed_tool.seed(memory_root=memory_root, branch="child", axis="축", task_title="첫 task", out_of_scope=None,
                       today="2026-11-13", apply=True, force=False, inherit_from=BRANCH, origin_sha="abc1234")
        child = memory_root / "active" / "child"
        copied = sorted(p.name for p in (child / pr.RESPONSES_DIRNAME).rglob("*") if p.is_file()) \
            if (child / pr.RESPONSES_DIRNAME).is_dir() else []
        if copied != [kept]:
            problems.append(f"seed 가 옮긴 것이 보관 응답 하나가 아니다 (받은편지함 · 거둔 응답은 아니다): {copied}")
        child_task = plan_tasks.read_task_plan(child / "backlog" / "tasks" / f"{task_id}.md")
        if child_task is None or plan_tasks.computed_states(child_task).states != columns:
            problems.append("이어받은 task 의 계산 상태가 모 브랜치와 다르다 — 근거가 따라오지 않았다")
        if not waiting.is_file():
            problems.append("이어받기가 모 브랜치의 받은편지함을 건드렸다")

        # 합류 — 브랜치에서 보관한 응답이 이월 · 되돌려 적기와 함께 간다.
        own_id = "TASK-2026-11-13-child-777"
        own_text = (child / "backlog" / "tasks" / f"{task_id}.md").read_text(encoding="utf-8")
        own_text = inherit.strip_inherited(own_text).replace(task_id, own_id)
        (child / "backlog" / "tasks" / f"{own_id}.md").write_text(own_text, encoding="utf-8")
        own_plan = pc.parse_plan(own_text.splitlines())
        (child / pr.RESPONSES_DIRNAME).mkdir(exist_ok=True)
        (child / pr.RESPONSES_DIRNAME / f"{own_id}-7.md").write_bytes(pr.render_response(
            task_id=own_id, plan=own_plan, responder="kim", received_at=AT.format(7), values={"D2": "b"}).encode())
        (child / pr.RESPONSES_DIRNAME / f"{own_id}-8.rejected.md").write_bytes(b"x")
        pr.ensure_inbox(child)
        (pr.inbox_dir(child) / f"{own_id}-9.md").write_bytes(b"x")
        # 이어받은 task 를 브랜치에서 고치고(되돌려 적기 대상) 새 응답을 보관한다.
        inherited_path = child / "backlog" / "tasks" / f"{task_id}.md"
        inherited_path.write_text(inherited_path.read_text(encoding="utf-8").replace(
            "- Progress:", "- Progress: 브랜치에서 진행", 1), encoding="utf-8")
        (child / pr.RESPONSES_DIRNAME / f"{task_id}-99.md").write_bytes(
            _response(ws, task_id, "choi", 99, values={"D1": "warn"}))
        branch_join.reflect_join(branch="child", branch_dir=child, parent_branch=BRANCH,
                                 active_dir=memory_root / "active", sha="def5678", today="2026-11-13")
        parent_files = sorted(p.name for p in (parent / pr.RESPONSES_DIRNAME).iterdir() if p.is_file())
        if f"{own_id}-7.md" not in parent_files:
            problems.append(f"이월된 task 의 보관 응답이 따라오지 않았다: {parent_files}")
        if f"{task_id}-99.md" not in parent_files:
            problems.append(f"되돌려 적은 task 의 보관 응답이 따라오지 않았다: {parent_files}")
        if f"{own_id}-8.rejected.md" in parent_files or (pr.inbox_dir(parent) / f"{own_id}-9.md").exists():
            problems.append("합류가 거둔 응답 · 받은편지함을 옮겼다")
        if not (parent / "backlog" / "tasks" / f"{own_id}.md").is_file():
            problems.append("fixture: task 가 이월되지 않았다")
    # copy_archive 는 있는 파일을 덮지 않는다.
    with tempfile.TemporaryDirectory() as td:
        src, dst = Path(td) / "a", Path(td) / "b"
        (src / pr.RESPONSES_DIRNAME).mkdir(parents=True)
        (dst / pr.RESPONSES_DIRNAME).mkdir(parents=True)
        (src / pr.RESPONSES_DIRNAME / f"{TASK}-1.md").write_bytes(b"new")
        (dst / pr.RESPONSES_DIRNAME / f"{TASK}-1.md").write_bytes(b"old")
        (src / pr.RESPONSES_DIRNAME / f"{TASK}-2.md").write_bytes(b"two")
        (src / pr.RESPONSES_DIRNAME / f"{TASK}9-3.md").write_bytes(b"other")
        copied_paths = pr.copy_archive(src, dst, TASK)
        if [p.name for p in copied_paths] != [f"{TASK}-2.md"] or \
                (dst / pr.RESPONSES_DIRNAME / f"{TASK}-1.md").read_bytes() != b"old":
            problems.append("copy_archive 가 있는 파일을 덮었거나 다른 task 의 파일을 옮겼다")
    _record("case 10 (이어받기 — seed · 이월 · 되돌려 적기가 보관 응답만 옮긴다)", problems)


# --------------------------------------------------------------------------- case 11 · 12


def case_11_reads_do_not_create_directories() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _create(ws)
        target = _branch(ws) / pr.RESPONSES_DIRNAME
        _import(ws, "--task", task_id)
        _cli(ws, ["-m", "workflow_kit", "plan-status"], "--task", task_id)
        _backlog(ws, "--mode", "update", "--task-id", task_id, "--task-name", "응답을 받는 task", "--status", "in_progress")
        plan_tasks.archived_responses(plan_tasks.read_task_plan(_task_path(ws, task_id)))  # type: ignore[arg-type]
        pr.pending_warning(_branch(ws))
        pr.unknown_inbox_files(_branch(ws))
        if target.exists():
            problems.append("읽는 길이 plan_responses/ 를 만들었다 — 응답이 없는 저장소의 트리가 바뀐다")
    _record("case 11 (읽는 길은 디렉터리를 만들지 않는다)", problems)


def case_12_contract_and_arguments() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _create(ws)
        _publish(ws, task_id, _response(ws, task_id, "kim", 1, values={"D1": "warn"}))
        for args in (("--task", task_id), ("--task", task_id, "--apply")):
            rc, out = _import(ws, *args)
            errors = validate_output_payload(out, family="plan_import")
            if rc != 0 or errors:
                problems.append(f"출력이 family plan_import 계약과 다르다 ({args[-1]}): {errors[:2]}")
        rc, out = _cli(ws, ["-m", "workflow_kit", "plan-status"], "--task", task_id)
        if rc != 0 or validate_output_payload(out, family="plan_status"):
            problems.append("plan-status 의 출력이 계약과 다르다")
        # 받은편지함은 received_at 순(같으면 번호 순)으로 본다 — 도착(파일을 놓은) 순서가 아니다.
        for responder, micro in (("c", 30), ("a", 10), ("b", 20), ("d", 20)):
            _publish(ws, task_id, _response(ws, task_id, responder, micro, values={"D1": "warn"}))
        rc, out = _import(ws, "--task", task_id)
        early = pr.inbox_dir(_branch(ws)) / f"{task_id}-1.md"       # 번호는 가장 작지만 가장 늦게 받았다
        early.write_bytes(_response(ws, task_id, "z", 99, values={"D1": "warn"}))
        rc, out = _import(ws, "--task", task_id)
        if [r["responder"] for r in out.get("responses", [])] != ["a", "b", "d", "c", "z"]:
            problems.append(f"번호 순으로 봤다 (received_at 이 먼저다): {[r['responder'] for r in out.get('responses', [])]}")
        early.unlink()
        rc, out = _import(ws, "--task", task_id)
        seen = [r["responder"] for r in out.get("responses", [])]
        if seen != ["a", "b", "d", "c"]:
            problems.append(f"받은편지함을 received_at · 번호 순으로 보지 않았다: {seen}")
        _import(ws, "--task", task_id, "--apply")
        profile = str(ws / "docs" / "PROJECT_PROFILE.md")
        outside = ws / "elsewhere.md"
        outside.write_bytes(_response(ws, task_id, "lee", 2))
        (ws / "elsewhere").mkdir()
        named = ws / "elsewhere" / f"{task_id}-5.md"                # 이름은 응답 꼴이지만 받은편지함 밖이다
        named.write_bytes(_response(ws, task_id, "lee", 2))
        rejected_calls = {
            "모르는 인자": ("--task", task_id, "--force"),
            "접두 축약": ("--task", task_id, "--resp", "x.md"),
            "인자 없음": (),
            "--reason 만": ("--task", task_id, "--reason", "r"),
            "--discard 와 --response": ("--discard", "a.md", "--reason", "r", "--response", "b.md"),
            "받은편지함 밖의 --response": ("--task", task_id, "--response", str(outside)),
            "받은편지함 밖의 --discard": ("--discard", str(outside), "--reason", "r"),
            "이름만 맞는 밖의 --response": ("--task", task_id, "--response", str(named)),
            "이름만 맞는 밖의 --discard": ("--discard", str(named), "--reason", "r"),
            "보관 파일을 --response 로": ("--task", task_id, "--response", _archive(ws, task_id)[0]),
            "없는 task": ("--task", "TASK-2026-11-13-plan-import-999"),
            "다른 task 의 --discard": ("--task", task_id + "9", "--discard", _archive(ws, task_id)[0], "--reason", "r"),
        }
        before = _snapshot(ws)
        for label, args in rejected_calls.items():
            proc = subprocess.run(
                [sys.executable, "-m", "workflow_kit", "plan-import", "--project-profile-path", profile, *args, "--apply"],
                capture_output=True, encoding="utf-8", errors="replace", check=False, env=_env(), cwd=str(ws))
            if proc.returncode != 2:
                problems.append(f"{label}: rc {proc.returncode} (기대 2)")
        if _snapshot(ws) != before or not named.is_file():
            problems.append("거절된 호출이 무엇인가 바꿨다")
    _record("case 12 (출력 계약 · 모르는 인자 · 받은편지함 밖의 경로는 거절)", problems)


CASES = (
    case_1_qualification_table, case_2_ineligible_stays_and_stage_zero, case_3_import_archives_and_records,
    case_4_order_independence, case_5_discard, case_6_numbers_and_exclusive_move, case_7_lock_busy,
    case_8_inbox_ignores_itself, case_9_race, case_10_inheritance, case_11_reads_do_not_create_directories,
    case_12_contract_and_arguments,
)


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--writer":
        os.environ["CODEX_WORKFLOW_BRANCH"] = BRANCH
        return _writer(Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]))
    if len(sys.argv) > 1 and sys.argv[1] == "--mover":
        return _mover(Path(sys.argv[2]), sys.argv[3])
    print("=== 주장 트리 계획 — 응답 파일 · 받은편지함 · plan-import (ADR-031) ===")
    for case in CASES:
        case()
    print()
    total = len(CASES)
    if FAILURES:
        print(f"{total - len(FAILURES)}/{total} PASS")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
