#!/usr/bin/env python3
"""compact 중계 — `wk compact-checkpoint` 모드 계약 · 재주입 예산 · 요약 대조 · hook 파생 (12 cases, ADR-030).

정본은 `workflow_kit/common/compact_relay.py`, 계약은 `core/compact_relay_spec.md`.

12 cases:
  1) 워크플로우 밖 · 브랜치 디렉터리 없는 workspace 에서 hook 3모드는 출력도 파일도 없이 exit 0
  2) `.compact/` 는 스스로를 git 에서 무시한다 — `git status` 에 안 잡히고 `check-ignore` 가 맞다
  3) `--note` 는 판단 층을 **대체**하고 `pending` 으로 둔다 · 항목 없는 `--note` · 모르는 인자는 exit 2 ·
     항목 하나가 600 바이트를 넘으면 잘린다
  4) `--hook pre` 는 대기 판단 층을 입력 세션으로 인수하고, 다른 세션의 인수된 checkpoint 는 버리고 새로
     시작한다 · 판단 층 없는 기록(자동 압축)은 재주입 머리말이 그것을 말한다 · 기계 층은 SSOT 의 열린 task 만
  5) 재주입은 예산(4,096 바이트) 안이고, 넘치면 **우선순위 뒤쪽부터** 빠지며 생략 줄이 남는다
  6) 입력 세션이 checkpoint 세션과 다르면 본문 없이 불일치만 알린다
  7) checkpoint 가 없으면 재주입 출력이 없다
  8) `--hook post` 는 요약에 없는 식별자를 세어 **자기 출력으로** 말하고(재주입이 post 보다 먼저 돈다),
     대조 대상이 0 이면 '누락 0' 과 다르게 말한다
  9) 모든 모드를 거쳐도 `session_handoff.md` · `state.json` 은 바이트 그대로다
 10) hook 모드는 깨진 stdin · 내부 예외에도 exit 0 이고 한 줄로 말한다
 11) 플러그인 hook 3종은 정본 §11.1 명령에서 파생되고, `wk` 부재에 조용하되 명령 실패(구버전 kit)는 말한다 ·
     저장된 사본이 렌더와 같다
 12) 예산 레코드 `compact_reinjection` 은 checkpoint 가 있으면 재고, 없으면 `measured=False` 다

임시 workspace 는 실물 배치를 닮는다 — `git init -b main` · `docs/PROJECT_PROFILE.md` ·
`ai-workflow/memory/active/main/backlog/tasks/`. CLI 는 **좁힌 환경**의 subprocess 로 부른다 — 상속된
브랜치 오버라이드(slash 셀)가 fixture 의 브랜치를 바꾸지 않게.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    # CLI 를 subprocess 로 띄우고 plugin_payload 를 import 해 kit 전반을 싣는다 — 좁은 선언은
    # meta-watch 가 '선언 밖 접근' 으로 잡는다 (ADR-028).
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "workflow-source/core/global_workflow_standard.md",
    "plugin/*",
)

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import compact_relay as relay  # noqa: E402
from workflow_kit.common.context_budget import BUDGETS_BY_KEY  # noqa: E402

FAILURES: list[str] = []
NOW = "2026-09-30T12:00:00+00:00"
BRANCH_ENV_KEYS_TO_DROP = ("CODEX_WORKFLOW_BRANCH", "GITHUB_HEAD_REF", "GITHUB_REF_NAME")

OPEN_TASK = """---
id: TASK-2026-09-30-main-001
status: in_progress
created_at: 2026-09-30
kind: generic
wbs: M-003/WBS-3.2
---

# TASK-2026-09-30-main-001 — 열린 fixture task

- 상태: in_progress
"""

DONE_TASK = OPEN_TASK.replace("main-001", "main-002").replace("status: in_progress", "status: done").replace(
    "열린 fixture task", "닫힌 fixture task"
)


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for p in problems:
            print(f"        - {p}")
    else:
        print(f"  PASS  {name}")


def _env() -> dict[str, str]:
    env = {
        "PYTHONPATH": str(SOURCE_ROOT),
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": os.environ.get("HOME", "/tmp"),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    return env


def _git(ws: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "user.name=fixture", "-c", "user.email=f@x", "-C", str(ws), *args],
        capture_output=True, text=True, env=_env(), check=False,
    )


def _cli(ws: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "workflow_kit.tools.compact_checkpoint", "--now", NOW, *args],
        input=stdin if stdin is not None else "", capture_output=True, text=True,
        encoding="utf-8", cwd=str(ws), env=_env(), check=False,
    )


def _payload(ws: Path, session: str = "S1", **extra: object) -> str:
    return json.dumps({"session_id": session, "cwd": str(ws), **extra}, ensure_ascii=False)


def _workspace(root: Path, *, profile: bool = True, branch_dir: bool = True) -> Path:
    ws = root / "ws"
    ws.mkdir()
    _git(ws, "init", "-q", "-b", "main")
    (ws / "README.md").write_text("fixture\n", encoding="utf-8")
    if profile:
        (ws / "docs").mkdir()
        (ws / "docs" / "PROJECT_PROFILE.md").write_text("# Project Profile\n\n- 이름: fixture\n", encoding="utf-8")
        memory = ws / "ai-workflow" / "memory" / "active"
        memory.mkdir(parents=True)
        if branch_dir:
            tasks = memory / "main" / "backlog" / "tasks"
            tasks.mkdir(parents=True)
            (tasks / "TASK-2026-09-30-main-001.md").write_text(OPEN_TASK, encoding="utf-8")
            (tasks / "TASK-2026-09-30-main-002.md").write_text(DONE_TASK, encoding="utf-8")
            (memory / "main" / "session_handoff.md").write_text("# Session Handoff\n\n- x\n", encoding="utf-8")
            (memory / "main" / "state.json").write_text('{"k": 1}\n', encoding="utf-8")
    _git(ws, "add", "-A")
    _git(ws, "commit", "-q", "-m", "fixture")
    return ws


def _compact_dir(ws: Path) -> Path:
    return ws / "ai-workflow" / "memory" / "active" / "main" / ".compact"


def _checkpoint(ws: Path) -> dict:
    return json.loads((_compact_dir(ws) / "checkpoint.json").read_text(encoding="utf-8"))


def _loc(ws: Path) -> relay.RelayLocation:
    return relay.RelayLocation(workspace_root=ws, branch_dir=ws / "ai-workflow" / "memory" / "active" / "main")


# --- cases -------------------------------------------------------------------------------


def case_1_outside_workflow_is_silent() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        for label, kwargs in (("프로필 없음", {"profile": False}), ("브랜치 디렉터리 없음", {"branch_dir": False})):
            sub = Path(tmp) / label.replace(" ", "_")
            sub.mkdir()
            ws = _workspace(sub, **kwargs)
            before = sorted(p.relative_to(ws).as_posix() for p in ws.rglob("*") if ".git" not in p.parts)
            for args in (("--hook", "pre"), ("--hook", "post"), ("--restore",)):
                proc = _cli(ws, *args, stdin=_payload(ws, compact_summary="s"))
                if proc.returncode != 0 or proc.stdout or proc.stderr:
                    problems.append(f"{label} {args}: rc={proc.returncode} out={proc.stdout!r} err={proc.stderr[-200:]!r}")
            after = sorted(p.relative_to(ws).as_posix() for p in ws.rglob("*") if ".git" not in p.parts)
            if after != before:
                problems.append(f"{label}: 파일이 생겼다 {sorted(set(after) - set(before))}")
    _record("case 1 워크플로우 밖 · 브랜치 없음 → 무출력 무파일", problems)


def case_2_compact_dir_ignores_itself() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        ws = _workspace(Path(tmp))
        # 저장소처럼 memory 를 재포함하는 루트 규칙이 있어도 성립해야 한다
        (ws / ".gitignore").write_text("ai-workflow/*\n!/ai-workflow/memory/\n", encoding="utf-8")
        _cli(ws, "--note", "--next", "n")
        _cli(ws, "--hook", "post", stdin=_payload(ws, compact_summary="s"))
        _cli(ws, "--hook", "pre", stdin=_payload(ws))
        _cli(ws, "--hook", "post", stdin=_payload(ws, compact_summary="s"))
        status = _git(ws, "status", "--porcelain", "--untracked-files=all").stdout
        if ".compact" in status:
            problems.append(f"git status 에 잡힌다: {status.strip()}")
        for name in (".gitignore", "checkpoint.json", "summary.md"):
            path = _compact_dir(ws) / name
            if not path.exists():
                problems.append(f"{name} 가 없다")
            elif _git(ws, "check-ignore", "-q", str(path)).returncode != 0:
                problems.append(f"{name} 가 무시되지 않는다")
    _record("case 2 .compact/ 자기 무시", problems)


def case_3_note_replaces_and_validates() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        ws = _workspace(Path(tmp))
        _cli(ws, "--note", "--next", "첫 기록", "--verified", "v1")
        _cli(ws, "--note", "--unverified", "두 번째", "--next", "가" * 400)
        j = _checkpoint(ws)["judgment"]
        if j.get("verified") or j.get("unverified") != ["두 번째"]:
            problems.append(f"대체가 아니다: {j}")
        if j.get("pending") is not True:
            problems.append("pending 이 아니다")
        if len(j["next"][0].encode("utf-8")) > relay.ITEM_MAX_BYTES:
            problems.append(f"항목이 잘리지 않았다: {len(j['next'][0].encode('utf-8'))}B")
        if (rc := _cli(ws, "--note").returncode) != 2:
            problems.append(f"항목 없는 --note rc={rc}")
        if (rc := _cli(ws, "--note", "--next", "x", "--bogus").returncode) != 2:
            problems.append(f"모르는 인자 rc={rc}")
        if (rc := _cli(ws, "--clear", "--next", "x").returncode) != 2:
            problems.append(f"--clear 에 항목 rc={rc}")
    _record("case 3 --note 대체 · pending · 인자 검증 · 항목 상한", problems)


def case_4_pre_adopts_or_restarts() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        ws = _workspace(Path(tmp))
        _cli(ws, "--note", "--next", "이어서 할 일")
        _cli(ws, "--hook", "pre", stdin=_payload(ws, "S1", trigger="manual", custom_instructions="keep"))
        cp = _checkpoint(ws)
        if cp["session_id"] != "S1" or not cp["judgment"] or cp["judgment"]["pending"] is not False:
            problems.append(f"인수 실패: session={cp['session_id']} judgment={cp['judgment']}")
        tasks = [t["id"] for t in cp["mechanical"]["tasks"]]
        if tasks != ["TASK-2026-09-30-main-001"]:
            problems.append(f"기계 층 task 가 열린 것만이 아니다: {tasks}")
        if cp["mechanical"]["tasks"][0].get("wbs") != "M-003/WBS-3.2" or not cp["head"]:
            problems.append(f"wbs/head 누락: {cp['mechanical']['tasks'][0]} head={cp['head']}")
        if cp["custom_instructions"] != "keep":
            problems.append("지시문을 기록하지 않았다")
        # 같은 세션의 두 번째 압축 — 판단 층 유지
        _cli(ws, "--hook", "pre", stdin=_payload(ws, "S1", trigger="auto"))
        if not _checkpoint(ws)["judgment"]:
            problems.append("같은 세션 재압축에서 판단 층을 버렸다")
        # 다른 세션 — 인수된 checkpoint 는 버리고 새로 시작
        _cli(ws, "--hook", "pre", stdin=_payload(ws, "S2", trigger="auto"))
        cp2 = _checkpoint(ws)
        if cp2["session_id"] != "S2" or cp2["judgment"] is not None:
            problems.append(f"다른 세션인데 판단 층을 물려받았다: {cp2['judgment']}")
        out = _cli(ws, "--restore", stdin=_payload(ws, "S2")).stdout
        if "판단 층 없음" not in out:
            problems.append(f"자동 압축 재주입이 판단 층 부재를 말하지 않는다: {out[:200]!r}")
    _record("case 4 pre 인수 · 타 세션 새 시작 · 판단 층 부재 명시", problems)


def _big_checkpoint() -> dict:
    data = relay.empty_checkpoint(NOW)
    data.update(session_id="S1", head="abc1234", trigger="manual")
    data["judgment"] = {
        "pending": False, "noted_at": NOW,
        "next": ["NEXT-KEEP 다음 한 걸음"],
        "unverified": [f"UNVERIFIED-{i} " + "나" * 150 for i in range(3)],
        "verified": [f"VERIFIED-{i} " + "다" * 150 for i in range(20)],
        "rejected": [f"REJECTED-{i} " + "라" * 150 for i in range(20)],
    }
    data["mechanical"] = {"tasks": [{"id": "TASK-2026-09-30-main-001", "status": "in_progress", "title": "t", "wbs": ""}],
                          "dirty_files": [], "dirty_count": 0}
    return data


def case_5_restore_budget_and_priority() -> None:
    problems: list[str] = []
    loc = _loc(Path("/ws"))
    now = datetime.fromisoformat(NOW)
    limit = relay.restore_limit_bytes()
    text = relay.render_restore(loc, _big_checkpoint(), session_id="S1", head="abc1234", now=now)
    size = len(text.encode("utf-8"))
    if size > limit:
        problems.append(f"예산 초과 {size}B > {limit}B")
    for must in (relay.HEADER_TAG, "NEXT-KEEP", "UNVERIFIED-2", "TASK-2026-09-30-main-001", "생략"):
        if must not in text:
            problems.append(f"'{must}' 가 없다")
    if "REJECTED-19" in text and "VERIFIED-19" not in text:
        problems.append("뒤 우선순위(기각)가 앞(검증됨)보다 살아남았다")
    if text.index("미검증") > text.index("진행 중"):
        problems.append("절 순서가 스펙 §4 와 다르다")
    small = relay.render_restore(loc, _big_checkpoint(), session_id="S1", head="abc1234", now=now, limit=600)
    if len(small.encode("utf-8")) > 600 or "NEXT-KEEP" not in small:
        problems.append(f"좁은 예산에서 첫 우선순위를 잃었거나 넘쳤다: {len(small.encode('utf-8'))}B")
    _record("case 5 재주입 예산 · 우선순위 절단", problems)


def case_6_session_mismatch_withholds_body() -> None:
    problems: list[str] = []
    text = relay.render_restore(_loc(Path("/ws")), _big_checkpoint(), session_id="OTHER", head=None,
                                now=datetime.fromisoformat(NOW))
    if "다른 세션" not in text or "NEXT-KEEP" in text or "UNVERIFIED" in text:
        problems.append(f"불일치인데 본문이 들어갔다: {text[:300]!r}")
    _record("case 6 세션 불일치 → 본문 없음", problems)


def case_7_absent_checkpoint_is_silent() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        ws = _workspace(Path(tmp))
        proc = _cli(ws, "--restore", stdin=_payload(ws))
        if proc.returncode != 0 or proc.stdout:
            problems.append(f"rc={proc.returncode} out={proc.stdout!r}")
    _record("case 7 checkpoint 없음 → 재주입 없음", problems)


def case_8_summary_diff_counts_identifiers() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        ws = _workspace(Path(tmp))
        _cli(ws, "--note", "--unverified", "`check_x.py` 가 abc1234f 에서 red 인지", "--next", "자연어만 있는 항목")
        _cli(ws, "--hook", "pre", stdin=_payload(ws))
        post = _cli(ws, "--hook", "post", stdin=_payload(ws, compact_summary="TASK-2026-09-30-main-001 과 check_x.py 를 봤다"))
        r = _checkpoint(ws)["relay"]
        # 재주입이 PostCompact 보다 먼저 돈다 (Claude Code 실측) — 누락 목록은 post 출력이 말해야 모델에 닿는다
        if not all(t in post.stdout for t in ("누락 3/5", "M-003", "WBS-3.2", "abc1234f")):
            problems.append(f"post 출력이 누락 식별자를 말하지 않는다: {post.stdout!r}")
        expected_missing = {"M-003", "WBS-3.2", "abc1234f"}
        if set(r["missing"]) != expected_missing:
            problems.append(f"누락 {r['missing']} (기대 {sorted(expected_missing)})")
        if r["checked_count"] != 5:
            problems.append(f"대조 수 {r['checked_count']} (기대 5: TASK · M · WBS · 백틱 · sha)")
        if (_compact_dir(ws) / "summary.md").read_text(encoding="utf-8") != "TASK-2026-09-30-main-001 과 check_x.py 를 봤다":
            problems.append("요약 원문이 그대로 보관되지 않았다")
    with tempfile.TemporaryDirectory() as tmp:
        ws = _workspace(Path(tmp))
        (ws / "ai-workflow/memory/active/main/backlog/tasks/TASK-2026-09-30-main-001.md").unlink()
        _cli(ws, "--note", "--next", "식별자 없는 자연어")
        _cli(ws, "--hook", "pre", stdin=_payload(ws))
        _cli(ws, "--hook", "post", stdin=_payload(ws, compact_summary="요약"))
        out = _cli(ws, "--restore", stdin=_payload(ws)).stdout
        if "대조 대상 없음" not in out or "누락 0/" in out:
            problems.append(f"대상 0 을 '누락 0' 과 구분하지 않는다: {out.splitlines()[1:2]}")
    _record("case 8 요약 대조 — 식별자 누락 · 대상 없음 구분", problems)


def case_9_handoff_and_state_untouched() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        ws = _workspace(Path(tmp))
        branch = ws / "ai-workflow" / "memory" / "active" / "main"
        before = {n: (branch / n).read_bytes() for n in ("session_handoff.md", "state.json")}
        _cli(ws, "--note", "--next", "n")
        _cli(ws, "--hook", "pre", stdin=_payload(ws))
        _cli(ws, "--hook", "post", stdin=_payload(ws, compact_summary="s"))
        _cli(ws, "--restore", stdin=_payload(ws))
        _cli(ws, "--clear")
        for name, data in before.items():
            if (branch / name).read_bytes() != data:
                problems.append(f"{name} 가 바뀌었다")
        if (_compact_dir(ws) / "checkpoint.json").exists():
            problems.append("--clear 뒤 checkpoint 가 남았다")
    _record("case 9 handoff · state.json 바이트 불변", problems)


def case_10_hook_never_fails() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        ws = _workspace(Path(tmp))
        # 깨진 stdin — 위치는 cwd 탐색으로 찾고, 한 줄로 말한 뒤 0
        proc = _cli(ws, "--hook", "pre", stdin="not json")
        if proc.returncode != 0 or relay.HEADER_TAG not in proc.stdout:
            problems.append(f"깨진 stdin: rc={proc.returncode} out={proc.stdout!r}")
        # 내부 예외 — checkpoint 자리에 디렉터리를 둬 쓰기가 실패하게 한다
        (_compact_dir(ws) / "checkpoint.json").mkdir(parents=True)
        for args in (("--hook", "pre"), ("--hook", "post"), ("--restore",)):
            proc = _cli(ws, *args, stdin=_payload(ws, compact_summary="s"))
            if proc.returncode != 0:
                problems.append(f"{args} 예외에서 rc={proc.returncode}: {proc.stderr[-200:]}")
        proc = _cli(ws, "--hook", "pre", stdin=_payload(ws))
        if "실패" not in proc.stdout:
            problems.append(f"예외를 말하지 않았다: {proc.stdout!r}")
    _record("case 10 hook 모드는 항상 exit 0", problems)


def case_11_plugin_hooks_derive_from_standard() -> None:
    from workflow_kit.common.standard_rules import find_memory_command, load_standard_rules
    from workflow_kit.plugin_payload import CLAUDE_CODE_HOOKS_RELPATH, GROK_HOOKS_RELPATH, render_claude_code_hooks

    problems: list[str] = []
    rules = load_standard_rules()
    command = find_memory_command(rules, "Relay working state")
    rendered = render_claude_code_hooks(rules)
    hooks = json.loads(rendered)["hooks"]

    def commands(event: str, matcher: str | None) -> list[str]:
        return [h["command"] for g in hooks.get(event, []) if g.get("matcher") == matcher for h in g["hooks"]]

    for event, matcher, mode in (("PreCompact", None, "--hook pre"), ("PostCompact", None, "--hook post"),
                                 ("SessionStart", "compact", "--restore")):
        cmds = commands(event, matcher)
        if len(cmds) != 1 or f"{command} {mode}" not in cmds[0]:
            problems.append(f"{event}({matcher}): {cmds}")
        elif not cmds[0].endswith("|| true") or "command -v" not in cmds[0]:
            problems.append(f"{event}: wk 부재에 조용하지 않다: {cmds[0]}")
        elif "failed" not in cmds[0].split(f"{command} {mode}", 1)[1]:
            problems.append(f"{event}: wk 는 있는데 명령이 실패하면(구버전 kit) 말하지 않는다: {cmds[0]}")
    for rel in (CLAUDE_CODE_HOOKS_RELPATH, GROK_HOOKS_RELPATH):
        path = REPO_ROOT / "plugin" / rel
        if path.read_text(encoding="utf-8") != rendered:
            problems.append(f"{rel} 가 렌더와 다르다 — `python3 -m workflow_kit.plugin_payload --apply`")
    if not (REPO_ROOT / "plugin" / "skills" / "compact-relay" / "SKILL.md").is_file():
        problems.append("스킬 compact-relay 가 payload 에 없다")
    _record("case 11 플러그인 hook 3종 = 정본 §11.1 파생", problems)


def case_12_budget_record_measures() -> None:
    problems: list[str] = []
    budget = BUDGETS_BY_KEY.get(relay.RESTORE_BUDGET_KEY)
    if budget is None or budget.limit_bytes != 4096:
        problems.append(f"예산 레코드: {budget}")
    probe = (
        "import json,sys; from pathlib import Path;"
        "from workflow_kit.common.context_budget import measure;"
        "p=Path(sys.argv[1]);"
        "m=[x for x in measure(handoff_path=None,state_path=None,claude_md_path=None,project_profile_path=p)"
        " if x.budget.key=='compact_reinjection'][0];"
        "print(json.dumps([m.measured,m.size]))"
    )
    with tempfile.TemporaryDirectory() as tmp:
        ws = _workspace(Path(tmp))
        profile = str(ws / "docs" / "PROJECT_PROFILE.md")

        def run() -> list:
            proc = subprocess.run([sys.executable, "-c", probe, profile], capture_output=True, text=True,
                                  env=_env(), check=False)
            return json.loads(proc.stdout) if proc.returncode == 0 else [f"rc={proc.returncode} {proc.stderr[-200:]}"]

        if (got := run()) != [False, 0]:
            problems.append(f"checkpoint 없음인데 {got}")
        _cli(ws, "--note", "--next", "n")
        _cli(ws, "--hook", "pre", stdin=_payload(ws))
        got = run()
        if len(got) != 2 or got[0] is not True or not 0 < got[1] <= 4096:
            problems.append(f"checkpoint 있음인데 {got}")
    _record("case 12 예산 레코드 측정", problems)


CASES = [
    case_1_outside_workflow_is_silent,
    case_2_compact_dir_ignores_itself,
    case_3_note_replaces_and_validates,
    case_4_pre_adopts_or_restarts,
    case_5_restore_budget_and_priority,
    case_6_session_mismatch_withholds_body,
    case_7_absent_checkpoint_is_silent,
    case_8_summary_diff_counts_identifiers,
    case_9_handoff_and_state_untouched,
    case_10_hook_never_fails,
    case_11_plugin_hooks_derive_from_standard,
    case_12_budget_record_measures,
]


def main() -> int:
    print("=== compact 중계 (ADR-030) ===")
    for fn in CASES:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            FAILURES.append(fn.__name__)
            print(f"  FAIL  {fn.__name__} — 예외 {type(exc).__name__}: {exc}")
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    print(f"\n{len(CASES)}/{len(CASES)} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
