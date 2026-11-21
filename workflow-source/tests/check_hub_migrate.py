#!/usr/bin/env python3
"""허브 1.x 전환 (M-038 WBS-38.1) — 감지 · 전환 계획 · 들여오기.

정본: ``core/hub_spec.md`` §6.6 (요구 R14.1 ~ R14.5 · R14.9 · Q1 · Q2 · I1). 실제 git 저장소에 1.x 배치를
만들고(브랜치 네임스페이스 셋 · 같은 ID 셋 · 커밋 시각을 바꿔 가며), 에이전트 몫(명령 실행 · 파일 읽기)은
이 검사가 하고 허브 몫은 실제 허브 프로세스에 HTTP 로 넣는다.

1. 감지 — 명령 목록 → 결과 대조: 네임스페이스 · 현재 · 기본 브랜치 · kit 판 · 종류별 수 · checkpoint(무시 파일) ·
   4종 밖 하네스 · 플러그인 안내 · 남기는 파일(사유별 수, R14.2) · 커밋 안 된 파일 경고
2. 같은 ID 정본 (Q1) — 마지막 커밋이 늦은 브랜치 / 같은 시각이면 기본 브랜치 / 기본 브랜치가 없으면 이름순,
   들인 뒤 task 1 · 나머지는 이력(imported_variant), 근거가 보고에
3. task 칸 — 1.x 칸이 그대로 (제목 · 상태 · 우선순위 · wbs · 완료 기준 · 결과 · 영향 문서 · plan_md 원문),
   그리고 **이 저장소의 실제 task 파일 전수**를 파서에 넣어 독립 증인(frontmatter · 머리 줄 · 계획 지문)과 대조, 미분류 수
4. 고른 것만 · 원본 불변 · 보관 — tasks 만 고르면 그것만, 저장소 파일 변화 0, 보관 기록 원문 바이트 일치 + 메타,
   콜사인 handoff 는 현재 브랜치에서
5. 진입 파일 — kit 생성 절은 버리고 손 문단만 지침 제안 초안(open), 판 불변
6. 권한 · 입력 · 다시 보내기 — 소유자 아님 403, 계획 밖 경로 · 고르지 않은 종류 400, 다시 보내면 건너뜀,
   final 뒤 409
7. '허브로 옮김' 표식 (WBS-38.2 · R14.6) — 끝나지 않은 전환 409 · 소유자 아님 403, 쓰기 지시대로 쓰고 커밋 → sha 확인,
   다른 sha 미확인, 두 번 내도 같은 내용, 표식에 허브 · 프로젝트 · 전환 · 시각 · kit 판
8. 되돌리기 (R14.7) — 삭제 지시 + 확인 명령, 아직 추적되면 미확인, 지우고 커밋하면 확인, 허브 데이터 불변 · 주의 보고
9. 선택 클라이언트 운반 (소유자 2026-11-21, 리허설 §16.5) — 허브가 내려준 hub_client.py 를 kit 없는 격리
   인터프리터로 migrate plan → import all: MCP 와 같은 결과, 계획은 캐시에. 전환 두 도구만 큰 요청 상한
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 300

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/check_hub_core.py",
    "workflow-source/tests/check_roadmap_gates.py",
    "ai-workflow/memory/active/*/backlog/tasks/*",
)

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_roadmap_gates as rg  # noqa: E402
from check_hub_core import Hub  # noqa: E402
from workflow_kit.common import plan_claims  # noqa: E402
from workflow_kit.common.plan_tasks import read_task_plan  # noqa: E402
from workflow_kit.hub.migrate1x import COMMANDS, parse_task_file  # noqa: E402

_failures: list[str] = []
_passes: list[str] = []

A = "ai-workflow/memory/active"
ID1, ID2, ID3, ID4 = (f"TASK-2026-11-01-x-00{n}" for n in (1, 2, 3, 4))
PLAN = ("- Claims: C1 전환은 칸을 잃지 않는다\n"
        "- Decisions: D1 [C1] 어디에 두나? | default: hub | options: hub = 허브; git = 저장소 | state: proposed\n"
        "- Files that change: `x.py`\n- Proof: 검사\n")
HAND = "## 우리 프로젝트 규칙\n\n- 배포 전 반드시 스테이징에서 확인한다.\n"


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


def _git(repo: Path, *args: str, when: int | None = None) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.invalid", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    if when is not None:
        env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"] = f"@{when} +0000"
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=env).stdout


def _task_text(task_id: str, title: str, status: str = "in_progress", extra: str = "") -> str:
    return (f"---\nid: {task_id}\nstatus: {status}\ncreated_at: 2026-11-01\nsource_anchor: generic-{task_id.lower()}\n"
            f"source_path: backlog/2026-11-01.md\nkind: generic\nwbs: M-001/WBS-1.1\n---\n\n# {task_id} — {title}\n\n"
            f"## 📝 Description\n\n- Status: {status}\n- Priority: low\n- Request date: 2026-11-01\n{extra}")


def _write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_repo(tmp: Path) -> Path:
    """1.x 저장소 — 네임스페이스 main · feat/x · hotfix, 같은 ID 셋은 커밋 시각을 달리해 들인다."""
    remote, repo = tmp / "remote.git", tmp / "repo"
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(remote)], check=True)
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _write(repo, ".gitignore", "**/.compact/\n")
    full = ("- Affected documents:\n  - `docs/a.md`\n  - `docs/b.md`\n"
            "- Description: 전환 대상 task 의 설명\n"
            "- Completion criteria: [C1] 칸이 그대로다\n- Completion criteria: [C1] 계획이 그대로다\n\n"
            f"## 🧭 Plan\n\n{PLAN}\n## 🛠️ Implementation / Content\n\n- Progress: `2026-11-02 10:00` 들여오는 중\n"
            "- Next session starting point: 다음은 검증\n- Remaining risks: 형식 변종\n\n"
            "## ✅ Outcome\n\n- Result: 들였다\n- Verification: 검사 PASS\n- Follow-up: 표식\n")
    # t=1000: main 의 셋 · ID2 는 main 과 feat/x 에 같은 커밋 · ID3 는 feat/x 와 hotfix 에 같은 커밋
    for ns in ("main", "feat/x", "hotfix"):
        _write(repo, f"{A}/{ns}/backlog/tasks/{ID1}.md", _task_text(ID1, f"같은 ID ({ns})"))
    for ns in ("main", "feat/x"):
        _write(repo, f"{A}/{ns}/backlog/tasks/{ID2}.md", _task_text(ID2, f"같은 시각 ({ns})"))
    for ns in ("feat/x", "hotfix"):
        _write(repo, f"{A}/{ns}/backlog/tasks/{ID3}.md", _task_text(ID3, f"기본 브랜치 없음 ({ns})"))
    _write(repo, f"{A}/main/backlog/tasks/{ID4}.md", _task_text(ID4, "칸이 많은 task", "done", full))
    _write(repo, f"{A}/main/session_handoff.md",
           "# Session Handoff\n\n## 1. 현재 작업 요약\n\n- 현재 기준선: 1.x 기준선 M\n- 현재 주 작업 축: 전환\n\n"
           f"## 2. 진행 중 작업\n\n- 현재 `in_progress` 작업:\n- {ID1} 같은 ID\n\n## 3. 차단 작업\n\n- 현재 `blocked` 작업:\n-\n\n"
           f"## 4. 최근 완료 작업\n\n- 최근 완료 작업 목록:\n- {ID4} 칸이 많은 task\n- 산문 줄\n\n"
           "## 5. 다음 세션 시작 포인트\n\n- 허브로 옮긴다\n\n## 6. 남은 리스크\n\n- 형식 변종\n")
    _write(repo, f"{A}/feat/x/session_handoff.md", "# Session Handoff\n\n- 현재 기준선: 가지 X\n- 현재 주 작업 축: X\n")
    _write(repo, f"{A}/main/sessions/s1.md", "# 세션 1\n\n원문 그대로 — 바이트 대조 ✓\n")
    _write(repo, f"{A}/main/lessons.md", "# lessons\n\n- 규칙 하나\n")
    _write(repo, f"{A}/main/.compact/checkpoint.json",
           json.dumps({"next": "검증", "verified": ["a"], "tasks": [ID1], "branch": "main", "extra_key": 1}))
    rm_root = tmp / "rm"
    rg._fixture(rm_root)
    for p in sorted((rm_root / A / "roadmap").glob("*.md")):
        _write(repo, f"{A}/roadmap/{p.name}", p.read_text(encoding="utf-8"))
    _write(repo, f"{A}/memory_index/entries/MEM-2026-01-01-001.json", json.dumps(
        {"id": "MEM-2026-01-01-001", "schema_version": 1, "source_paths": ["ai-workflow/x.md"], "primary_abstraction": "e",
         "cue_anchors": ["x"], "value_digest": "x", "owners": ["o"], "scope": ["s"], "merge_state": "active",
         "mentioned_in": [], "related_ids": [], "created_at": "2026-01-01", "updated_at": "2026-01-01"}))
    _write(repo, "ai-workflow/wiki/concepts/a.md", "# 개념 A\n\n본문.\n")
    _write(repo, "ai-workflow/wiki/index.md", "# Master Knowledge Index\n\n- [[concepts/a]]\n")
    _write(repo, "CLAUDE.md",
           "<!-- standard-ai-workflow-kit: v1.29.0 -->\n# CLAUDE.md\n\n"
           "## Working Principles\n\n<!-- generated-from: core/global_workflow_standard.md §1 -->\n\n- kit 이 만든 줄\n\n" + HAND)
    _write(repo, ".mcp.json", '{"mcpServers": {}}\n')
    _write(repo, ".claude-plugin/plugin.json", "{}\n")
    _write(repo, ".grok/config.toml", "x = 1\n")
    # 계획이 들이지 않고 남기는 파일 (R14.2 — 숫자와 사유로 보여야 한다)
    _write(repo, f"{A}/main/backlog/2026-11-01.md", "# backlog\n")
    _write(repo, f"{A}/main/state.json", "{}\n")
    _write(repo, "ai-workflow/memory/archived/old/backlog/tasks/TASK-2026-10-01-old-001.md", "x\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "t1000", when=1000)
    # t=2000: hotfix 의 ID1 · t=3000: feat/x 의 ID1 (가장 늦다)
    _write(repo, f"{A}/hotfix/backlog/tasks/{ID1}.md", _task_text(ID1, "같은 ID (hotfix, 고침)"))
    _git(repo, "commit", "-q", "-am", "t2000", when=2000)
    _write(repo, f"{A}/feat/x/backlog/tasks/{ID1}.md", _task_text(ID1, "같은 ID (feat/x, 최신)"))
    _git(repo, "commit", "-q", "-am", "t3000", when=3000)
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "origin", "main")
    _git(repo, "remote", "set-head", "origin", "main")
    return repo


def run_commands(repo: Path) -> dict[str, Any]:
    """에이전트 몫 — 허브가 내준 명령을 그대로 돌린다."""
    out = {}
    for name, argv in COMMANDS.items():
        r = subprocess.run(argv, cwd=repo, capture_output=True, text=True)
        out[name] = {"rc": r.returncode, "output": r.stdout}
    return out


def snapshot(repo: Path) -> dict[str, bytes]:
    return {str(p.relative_to(repo)): p.read_bytes() for p in sorted(repo.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(repo).parts}


def send(hub: Hub, tok: str, mig: str, repo: Path, kinds: list[str], paths: list[str], final: bool = False) -> tuple[int, Any]:
    files = [{"path": p, "content": (repo / p).read_text(encoding="utf-8")} for p in paths]
    st, out, _ = hub.call("hub_migrate_import", {"migration_id": mig, "kinds": kinds, "files": files, "final": final}, tok)
    return st, out


def corpus_witness() -> tuple[int, list[str]]:
    """이 저장소의 실제 task 파일 전수 — 파서 결과를 독립 증인과 대조한다 (미분류는 숫자로)."""
    files = sorted((REPO_ROOT / A).glob("**/backlog/tasks/*.md"))
    bad: list[str] = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        try:
            t = parse_task_file(text)
        except Exception as exc:  # noqa: BLE001 — 무엇이든 미분류로 센다
            bad.append(f"{f.name}: 못 읽음 {exc}")
            continue
        tp = read_task_plan(f)
        head = re.search(rf"^#\s+{re.escape(t['id'])}\s+[—-]\s+(.+)$", text, re.M)
        full_digest = plan_claims.plan_digest(plan_claims.parse_plan(text.splitlines()))
        part_digest = plan_claims.plan_digest(plan_claims.parse_plan(t["plan_md"].splitlines()))
        if tp is None or tp.task_id != t["id"] or (tp.status or "") != t["status"]:
            bad.append(f"{f.name}: id · 상태")
        elif head and head.group(1).strip()[:200] != t["title"]:
            bad.append(f"{f.name}: 제목")
        elif list(tp.criteria) != t["fields"].get("done_criteria", []):
            bad.append(f"{f.name}: 완료 기준")
        elif full_digest != part_digest:
            bad.append(f"{f.name}: 계획 절")
    return len(files), bad


def main() -> int:
    print("check_hub_migrate")
    with tempfile.TemporaryDirectory(prefix="hub-mig-") as d:
        tmp = Path(d)
        repo = build_repo(tmp)
        hub = Hub(tmp / "hub.db")
        try:
            reg = hub.call("hub_project_register", {"remote_url": "git@github.com:acme/legacy.git", "display_name": "legacy",
                                                     "callsign": "owner-a", "kind": "human"})[1]
            tok, pid = reg["token"], reg["project_id"]
            other = hub.call("hub_callsign_register", {"project_id": pid, "callsign": "bot-a", "kind": "agent"})[1]["token"]

            # 1 감지
            s0, p1, _ = hub.call("hub_migrate_plan", {}, tok)
            untracked = repo / A / "main/backlog/tasks/TASK-2026-11-02-x-009.md"
            _write(repo, str(untracked.relative_to(repo)), _task_text("TASK-2026-11-02-x-009", "커밋 안 됨"))
            scan = run_commands(repo)
            untracked.unlink()
            s1, plan, _ = hub.call("hub_migrate_plan", {"scan": scan}, tok)
            det = plan.get("detected", {})
            c = det.get("counts", {})
            ok1 = (s0 == 200 and set(p1.get("commands", {})) == set(COMMANDS) and s1 == 200
                   and det.get("namespaces") == ["feat/x", "hotfix", "main"] and det.get("current_namespace") == "main"
                   and det.get("default_branch") == "main" and det.get("kit_versions") == ["1.29.0"]
                   and c == {"tasks": 8, "archive": 4, "handoff": 1, "roadmap": 3, "wiki": 2, "memory_index": 1,
                             "checkpoint": 1, "guide_draft": 1}
                   and det.get("unsupported_harnesses") == ["grok-build"] and det.get("unmeasured") == []
                   and any(".mcp.json" in g for g in plan.get("guidance", []))
                   and any("grok-build" in g for g in plan.get("guidance", []))
                   and det.get("uncommitted") == [f"{A}/main/backlog/tasks/TASK-2026-11-02-x-009.md"]
                   and any("커밋 안 된 파일 1개" in g for g in plan.get("guidance", []))
                   and det.get("left_in_repo_total") == 3
                   and {k.split(" — ")[0] for k in det.get("left_in_repo", {})}
                   == {"생성물", "아카이브된 브랜치 기록", "날짜별 backlog"})
            _record("case 1 (감지 — 네임스페이스 · 브랜치 · kit 판 · 종류별 수 · checkpoint · 4종 밖 하네스)", ok1,
                    f"{s0} {s1} det={det} guidance={plan.get('guidance')}")
            mig = plan.get("migration_id", "")
            files = plan.get("files", {})

            # 4 (앞부분) 고른 것만 · 원본 불변 — tasks 만 먼저
            before = snapshot(repo)
            st_t, out_t = send(hub, tok, mig, repo, ["tasks"], files.get("tasks", []))
            _, listing, _ = hub.call("hub_task_list", {"limit": 500}, tok)
            _, notes_none, _ = hub.call("hub_handoff_get", {}, tok)

            # 2 같은 ID 정본
            conf = {x["task_id"]: x for x in plan.get("conflicts", [])}
            got = {t["id"]: t for t in listing.get("tasks", [])}

            def variants(tid: str) -> int:
                ev = hub.call("hub_events", {"target_kind": "task", "target_id": tid}, tok)[1]["events"]
                return sum(1 for e in ev if e["op"] == "imported_variant")

            ok2 = (st_t == 200 and sorted(got) == [ID1, ID2, ID3, ID4]
                   and conf[ID1]["canonical"]["namespace"] == "feat/x" and conf[ID1]["canonical"]["committed_at"] == 3000
                   and "늦다" in conf[ID1]["canonical"]["reason"] and got[ID1]["title"] == "같은 ID (feat/x, 최신)"
                   and conf[ID2]["canonical"]["namespace"] == "main" and "기본 브랜치" in conf[ID2]["canonical"]["reason"]
                   and conf[ID3]["canonical"]["namespace"] == "feat/x" and "이름순" in conf[ID3]["canonical"]["reason"]
                   and got[ID1]["branch"] == "feat/x" and variants(ID1) == 2 and variants(ID2) == 1 and variants(ID3) == 1
                   and len(conf[ID1]["variants"]) == 2 and conf[ID1]["canonical"].get("commit"))
            _record("case 2 (같은 ID 정본 — 늦은 커밋 · 같은 시각은 기본 브랜치 · 없으면 이름순, 나머지는 이력)", ok2,
                    f"{st_t} {out_t.get('summary')} ids={sorted(got)} conf={ {k: (v['canonical']['namespace'], v['canonical']['reason']) for k, v in conf.items()} }")

            # 3 task 칸
            t4 = got.get(ID4, {})
            f4 = t4.get("fields", {})
            n_corpus, bad = corpus_witness()
            ok3 = (t4.get("status") == "done" and t4.get("priority") == "low" and t4.get("wbs") == "M-001/WBS-1.1"
                   and t4.get("title") == "칸이 많은 task" and t4.get("description") == "전환 대상 task 의 설명"
                   and f4.get("done_criteria") == ["[C1] 칸이 그대로다", "[C1] 계획이 그대로다"]
                   and f4.get("affected_documents") == ["docs/a.md", "docs/b.md"] and f4.get("result") == "들였다"
                   and f4.get("validation_result") == "검사 PASS" and f4.get("follow_up") == ["표식"]
                   and f4.get("risks") == ["형식 변종"] and f4.get("next_step") == "다음은 검증"
                   and t4.get("plan_md") == PLAN and "들여오는 중" in t4.get("progress_note", "")
                   and n_corpus > 100 and bad == [])
            print(f"    task 파일 전수 {n_corpus} · 미분류 {len(bad)}")
            _record("case 3 (task 칸 그대로 · 실제 task 파일 전수 독립 증인 대조, 미분류 0)", ok3,
                    f"t4={t4} corpus={n_corpus} bad={bad[:5]}")

            # 4 나머지 종류 · 보관 · handoff
            rest = ["archive", "handoff", "roadmap", "wiki", "memory_index", "checkpoint", "guide_draft"]
            paths = [p for k in rest for p in files.get(k, [])]
            st_r, out_r = send(hub, tok, mig, repo, rest, paths)
            after = snapshot(repo)
            status_clean = _git(repo, "status", "--porcelain") == ""
            rep = hub.call("hub_migrate_report", {"migration_id": mig}, tok)[1]
            ho = hub.call("hub_handoff_get", {}, tok)[1]
            sec = ho.get("handoff") or {}
            with __import__("sqlite3").connect(tmp / "hub.db") as conn:
                notes = {r[0]: (r[1], json.loads(r[2])) for r in conn.execute(
                    "SELECT title, body_md, meta_json FROM memory_note WHERE kind = 'archive_1x' AND title LIKE 'ai-workflow/%'")}
            s1_path = f"{A}/main/sessions/s1.md"
            ok4 = (notes_none.get("version") == 0 and st_r == 200 and before == after and status_clean
                   and set(notes) == {f"{A}/main/session_handoff.md", f"{A}/feat/x/session_handoff.md", s1_path, f"{A}/main/lessons.md"}
                   and notes[s1_path][0].encode() == (repo / s1_path).read_bytes()
                   and notes[s1_path][1].get("branch") == "main" and notes[s1_path][1].get("commit")
                   and notes[f"{A}/feat/x/session_handoff.md"][1].get("branch") == "feat/x"
                   and sec.get("baseline") == "1.x 기준선 M" and sec.get("in_progress") == [f"{ID1} 같은 ID"]
                   and sec.get("recent_done") == [f"{ID4} 칸이 많은 task"] and sec.get("next") == ["허브로 옮긴다"]
                   and sec.get("risks") == ["형식 변종"]
                   and out_r["summary"].get("roadmap", {}).get("imported") == 3
                   and out_r["summary"].get("wiki", {}).get("imported") == 1 and out_r["summary"].get("wiki", {}).get("archived_1x") == 1
                   and out_r["summary"].get("memory_index", {}).get("imported") == 1
                   and out_r["summary"].get("checkpoint", {}).get("imported") == 1
                   and not any("failed" in v for v in out_r["summary"].values())
                   and rep.get("report", {}).get("handoff", {}).get("imported", [{}])[0].get("dropped_lines") == ["산문 줄"])
            _record("case 4 (고른 것만 · 원본 불변 · 보관 원문 · 현재 브랜치 handoff · 나머지 종류)", ok4,
                    f"{st_r} summary={out_r.get('summary')} same={before == after} clean={status_clean} notes={sorted(notes)} sec={sec}")

            # 5 진입 파일
            g = hub.call("hub_guide_get", {}, tok)[1]
            drafts = [x for x in g.get("proposals", []) if x["status"] == "open"]
            ok5 = (g.get("version") == 0 and len(drafts) == 1 and drafts[0]["body_md"].strip() == HAND.strip()
                   and "kit 이 만든 줄" not in drafts[0]["body_md"] and "standard-ai-workflow-kit" not in drafts[0]["body_md"])
            _record("case 5 (진입 파일 — 생성 절은 버리고 손 문단만 초안, 판 불변)", ok5, f"v={g.get('version')} drafts={drafts}")

            # 6 권한 · 입력 · 다시 보내기
            human = hub.call("hub_callsign_register", {"project_id": pid, "callsign": "yk-h", "kind": "human"})[1]["token"]
            hub.call("hub_callsign_approve", {"callsign": "yk-h"}, tok)
            e0, _, _ = hub.call("hub_migrate_plan", {}, human)  # 승인된 human 이지만 소유자가 아니다
            e1, _, _ = hub.call("hub_migrate_plan", {}, other)
            e2, _ = send(hub, other, mig, repo, ["tasks"], files["tasks"][:1])
            e3, bad_path, _ = hub.call("hub_migrate_import", {"migration_id": mig, "kinds": ["tasks"],
                                                               "files": [{"path": "README.md", "content": "x"}]}, tok)
            e4, _ = send(hub, tok, mig, repo, ["tasks"], files["roadmap"][:1])
            e5, again = send(hub, tok, mig, repo, ["tasks", "archive"], files["tasks"] + files["archive"], final=True)
            e6, _ = send(hub, tok, mig, repo, ["tasks"], files["tasks"][:1])
            _, listing2, _ = hub.call("hub_task_list", {"limit": 500}, tok)
            ok6 = (e0 == 403 and e1 == 403 and e2 == 403 and e3 == 400 and bad_path["detail"].get("field") == "files[0].path" and e4 == 400
                   and e5 == 200 and again.get("status") == "done" and again["summary"]["tasks"] == {"skipped_exists": 8}
                   and again["summary"]["archive"].get("skipped_exists") == 4 and e6 == 409
                   and len(listing2["tasks"]) == 4 and variants(ID1) == 2)
            _record("case 6 (권한 · 계획 밖 경로 · 고르지 않은 종류 · 다시 보내기 · final 뒤 409)", ok6,
                    f"{e0} {e1} {e2} {e3} {e4} {e5}/{again.get('summary')} {e6}")

            # 7 표식
            import hashlib
            _, plan2, _ = hub.call("hub_migrate_plan", {"scan": run_commands(repo)}, tok)
            m1, _, _ = hub.call("hub_migrate_marker", {"migration_id": plan2.get("migration_id"), "action": "issue"}, tok)
            m2, _, _ = hub.call("hub_migrate_marker", {"migration_id": mig, "action": "issue"}, human)
            m3, iss, _ = hub.call("hub_migrate_marker", {"migration_id": mig, "action": "issue"}, tok)
            step = next((x for x in iss.get("steps", []) if x.get("op") == "write"), {})
            commit = next((x for x in iss.get("steps", []) if x.get("id") == "commit"), {})
            _write(repo, step.get("path", "x"), step.get("content", ""))
            _git(repo, *commit.get("run", ["status"])[1:])
            _git(repo, *commit.get("then", ["status"])[1:])
            written = (repo / "ai-workflow/HUB_MIGRATED.json").read_bytes()
            m4, again_iss, _ = hub.call("hub_migrate_marker", {"migration_id": mig, "action": "issue"}, tok)
            m5, wrong, _ = hub.call("hub_migrate_marker", {"migration_id": mig, "action": "confirm", "sha256": "0" * 64}, tok)
            m6, conf, _ = hub.call("hub_migrate_marker", {"migration_id": mig, "action": "confirm",
                                                           "sha256": hashlib.sha256(written).hexdigest()}, tok)
            body = json.loads(written)
            tracked = _git(repo, "ls-files", "--", "ai-workflow/HUB_MIGRATED.json").strip()
            ok7 = (m1 == 409 and m2 == 403 and m3 == 200 and step.get("path") == "ai-workflow/HUB_MIGRATED.json"
                   and step.get("sha256_after") == hashlib.sha256(written).hexdigest() and tracked == "ai-workflow/HUB_MIGRATED.json"
                   and m4 == 200 and next(x for x in again_iss["steps"] if x["op"] == "write")["content"] == step["content"]
                   and m5 == 200 and wrong.get("confirmed") is False and "sha256" in wrong.get("reason", "")
                   and m6 == 200 and conf.get("confirmed") is True and conf["marker"].get("confirmed_at")
                   and body.get("format") == "workflow-hub-migrated/1" and body.get("project_id") == pid
                   and body.get("migration_id") == mig and body.get("hub", "").startswith("http")
                   and body.get("from_kit_versions") == ["1.29.0"] and body.get("migrated_at") and body.get("kit_version")
                   and "지운다" in body.get("note", ""))
            _record("case 7 (표식 — 끝난 전환만 · 소유자만 · 지시대로 쓰고 커밋 → sha 확인 · 멱등 · 내용)", ok7,
                    f"{m1} {m2} {m3} {m4} {m5}/{wrong} {m6}/{conf} tracked={tracked!r} body={body}")

            # 8 되돌리기
            n_before = len(hub.call("hub_task_list", {"limit": 500}, tok)[1]["tasks"])
            r1, rv, _ = hub.call("hub_migrate_marker", {"migration_id": mig, "action": "revert"}, tok)
            check = next((x for x in rv.get("steps", []) if x.get("op") == "run_and_report"), {})
            delete = next((x for x in rv.get("steps", []) if x.get("op") == "delete"), {})

            def run_check() -> dict[str, Any]:
                r = subprocess.run(check.get("run", ["false"]), cwd=repo, capture_output=True, text=True)
                return {"rc": r.returncode, "output": r.stdout}

            r2, still, _ = hub.call("hub_migrate_marker", {"migration_id": mig, "action": "confirm_revert", "check": run_check()}, tok)
            _git(repo, "rm", "-q", "--", delete.get("path", "x"))
            _git(repo, "commit", "-q", "-m", "되돌림")
            r3, done_rv, _ = hub.call("hub_migrate_marker", {"migration_id": mig, "action": "confirm_revert", "check": run_check()}, tok)
            n_after = len(hub.call("hub_task_list", {"limit": 500}, tok)[1]["tasks"])
            rep8 = hub.call("hub_migrate_report", {"migration_id": mig}, tok)[1]["report"].get("marker", {})
            ok8 = (r1 == 200 and delete.get("path") == "ai-workflow/HUB_MIGRATED.json" and check.get("expect") == "empty"
                   and "데이터 이동은 없다" in rv.get("warning", "") and "건너뛴다" in rv.get("warning", "") and r2 == 200 and still.get("reverted") is False
                   and r3 == 200 and done_rv.get("reverted") is True and n_before == n_after == 4
                   and rep8.get("reverted_at") and rep8.get("confirmed_at") is None
                   and not (repo / "ai-workflow/HUB_MIGRATED.json").exists())
            _record("case 8 (되돌리기 — 삭제 지시 · 추적되면 미확인 · 지우면 확인 · 허브 데이터 불변)", ok8,
                    f"{r1} {r2}/{still.get('reverted')} {r3}/{done_rv.get('reverted')} tasks {n_before}->{n_after} marker={rep8}")

            # 9 선택 클라이언트 운반 — 새 저장소 · 새 프로젝트
            repo2 = build_repo(tmp / "c")
            reg2 = hub.call("hub_project_register", {"remote_url": "git@github.com:acme/legacy-client.git",
                                                      "display_name": "legacy-client", "callsign": "owner-c", "kind": "human"})[1]
            (repo2 / ".workflow-hub").mkdir()
            (repo2 / ".workflow-hub" / "env").write_text(
                f"WORKFLOW_HUB_URL={hub.base}\nWORKFLOW_HUB_TOKEN={reg2['token']}\n", encoding="utf-8")
            with urllib.request.urlopen(hub.base + "/v1/bootstrap/hub_client.py", timeout=20) as r:
                (repo2 / ".workflow-hub" / "hub_client.py").write_bytes(r.read())
            clean_env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "WORKFLOW_HUB_TOKEN", "WORKFLOW_HUB_URL")}

            def client(*args: str) -> tuple[int, dict[str, Any]]:
                r = subprocess.run([sys.executable, "-I", ".workflow-hub/hub_client.py", *args], cwd=repo2,
                                   capture_output=True, text=True, env=clean_env, timeout=300)
                try:
                    return r.returncode, json.loads(r.stdout)
                except json.JSONDecodeError:
                    return r.returncode, {"raw": r.stdout[-500:], "err": r.stderr[-500:]}

            c1, cplan = client("migrate", "plan")
            mig2 = cplan.get("migration_id", "")
            c2, cimp = client("migrate", "import", mig2, "all")
            tasks2 = hub.call("hub_task_list", {"limit": 500}, reg2["token"])[1].get("tasks", [])
            c3, again2 = client("migrate", "import", mig2, "all")
            cached = (repo2 / ".workflow-hub" / "cache" / f"migrate-{mig2}.json").is_file()
            # 큰 상한은 전환 두 도구에만 — 같은 300KB 본문이 다른 도구에서는 413
            big = {"scan": {"ls_tracked": {"rc": 0, "output": "\n".join(f"docs/x{i:06d}.md" for i in range(20000))},
                            "branch": {"rc": 0, "output": "main"}}}
            body = json.dumps(big).encode()
            def raw_post(name: str, data: bytes) -> int:
                req = urllib.request.Request(f"{hub.base}/v1/tools/{name}", data=data, method="POST",
                                             headers={"content-type": "application/json", "authorization": f"Bearer {reg2['token']}"})
                try:
                    with urllib.request.urlopen(req, timeout=60) as r:
                        return r.status
                except urllib.error.HTTPError as e:
                    return e.code
            s_big, s_other = raw_post("hub_migrate_plan", body), raw_post("hub_task_list", body)
            ok9 = (c1 == 0 and mig2.startswith("MIG-") and cplan.get("conflicts") == 3 and cached
                   and c2 == 0 and cimp.get("errors") == [] and cimp.get("unreadable") == []
                   and sorted(t["id"] for t in tasks2) == [ID1, ID2, ID3, ID4]
                   and cimp.get("total", {}).get("archive", {}).get("imported") == 4
                   and c3 == 1 and again2.get("errors", [{}])[0].get("error_code") == "already_done"
                   and len(body) > 256 * 1024 and s_big == 200 and s_other == 413)
            _record("case 9 (선택 클라이언트 운반 — kit 없는 클라이언트로 plan · import, 큰 상한은 전환 도구만)", ok9,
                    f"plan={c1}/{mig2}/{cplan.get('conflicts')} cached={cached} import={c2}/{cimp.get('errors')}/{cimp.get('total')} "
                    f"tasks={len(tasks2)} again={c3}/{again2.get('errors')} big={len(body)}:{s_big}/{s_other}")
        finally:
            hub.stop()
    print(f"PASS {len(_passes)} · FAIL {len(_failures)}")
    for f in _failures:
        print(f"  FAIL {f}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
