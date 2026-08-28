#!/usr/bin/env python3
"""ADR-027 M-004 — task 생성 게이트 검사 (스펙 §6).

주장:
1. **판정은 한 곳이다** — CLI(backlog-update)와 MCP(create_backlog_entry)가
   `evaluate_wbs_gate` 하나를 거치고, 같은 입력에 같은 판정 코드를 낸다.
2. **게이트 전 분기가 되주입으로 red 다**: wbs 미지정 / 사유 없는 exempt /
   형식 위반 / dangling / 비-leaf / done 역행 / SDLC 순서 — 그리고 허용 3종
   (링크 · 사유 있는 exempt · `parallel_allowed` 선언)이 실제로 통과한다.
3. **roadmap 부재 프로젝트는 아무것도 달라지지 않는다** (additive).
4. **이 저장소에서 게이트가 실제로 무장돼 있다** (자기 적용, 읽기 전용 관찰).
5. **update `--wbs` 재링크도 같은 게이트를 탄다** — 갱신·사유 제거·보존·upsert
   (TASK-2026-08-28-main-002).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.read_only_bundle import create_backlog_entry_payload  # noqa: E402
from workflow_kit.common.state.roadmap import evaluate_wbs_gate  # noqa: E402

BACKLOG_TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "backlog_update.py"
BRANCH = "main"

FAILURES: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case}{(' — ' + detail) if detail else ''}")
        FAILURES.append(case)


M1_TEXT = """---
id: M-001
title: 컨셉
sdlc_phase: concept
status: {status}
order: 1
parallel_allowed: []
deliverables: []
---

# M-001

## WBS

- **WBS-1.1** 부모
  - **WBS-1.1.1** 자식
- **WBS-1.2** 리뷰
"""

M2_TEXT = """---
id: M-002
title: 설계
sdlc_phase: design
status: planned
order: 2
parallel_allowed: [{parallel}]
deliverables: []
---

# M-002

## WBS

- **WBS-2.1** 설계 문서
"""


def _fixture(root: Path, *, with_roadmap: bool = True, m1_status: str = "in_progress",
             m2_parallel: str = "") -> Path:
    (root / "docs").mkdir(parents=True)
    profile = root / "docs" / "PROJECT_PROFILE.md"
    profile.write_text("# profile\n", encoding="utf-8")
    branch_dir = root / "ai-workflow" / "memory" / "active" / BRANCH
    (branch_dir / "backlog" / "tasks").mkdir(parents=True)
    if with_roadmap:
        roadmap = root / "ai-workflow" / "memory" / "active" / "roadmap"
        roadmap.mkdir(parents=True)
        (roadmap / "index.md").write_text(
            "# Roadmap — fixture\n\n## Milestones\n\n"
            f"- **M-001** [concept] 컨셉 — status: {m1_status}\n"
            "  - path: [`./M-001-concept.md`](./M-001-concept.md)\n"
            "- **M-002** [design] 설계 — status: planned\n"
            "  - path: [`./M-002-design.md`](./M-002-design.md)\n",
            encoding="utf-8",
        )
        (roadmap / "M-001-concept.md").write_text(M1_TEXT.format(status=m1_status), encoding="utf-8")
        (roadmap / "M-002-design.md").write_text(M2_TEXT.format(parallel=m2_parallel), encoding="utf-8")
    return profile


def _run_cli(profile: Path, extra: list[str]) -> tuple[int, dict]:
    env = dict(os.environ)
    env["CODEX_WORKFLOW_BRANCH"] = BRANCH
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    proc = subprocess.run(
        [sys.executable, str(BACKLOG_TOOL),
         "--project-profile-path", str(profile),
         "--task-name", "게이트 fixture task", "--task-brief", "게이트 시험",
         "--mode", "create", *extra],
        capture_output=True, text=True, timeout=120, env=env,
    )
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        raise AssertionError(f"CLI 출력이 JSON 이 아니다:\n{proc.stdout[:400]}\n{proc.stderr[:400]}")
    return proc.returncode, payload


def test_gate_verdict_matrix() -> None:
    """단일 판정 함수의 전 분기 — 거부 7종 + 허용 3종 + 부재 additive."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _fixture(root)
        expect_denied = {
            None: "wbs_required",
            "exempt": "exempt_reason_required",
            "banana": "wbs_ref_format",
            "M-001/WBS-1.9": "wbs_dangling",
            "M-001/WBS-1.1": "wbs_not_leaf",
            "M-002/WBS-2.1": "sdlc_order",  # M-001 이 in_progress 인 채 M-002 로
        }
        for wbs, code in expect_denied.items():
            verdict = evaluate_wbs_gate(root, wbs=wbs)
            if verdict.allowed or verdict.code != code:
                problems.append(f"{wbs!r}: 기대 {code}, 실제 {verdict.code}(allowed={verdict.allowed})")
        for wbs, reason, code in (
            ("M-001/WBS-1.2", None, "linked"),
            ("exempt", "로드맵 밖 긴급 수리", "exempt_declared"),
        ):
            verdict = evaluate_wbs_gate(root, wbs=wbs, exempt_reason=reason)
            if not verdict.allowed or verdict.code != code:
                problems.append(f"{wbs!r}: 기대 허용 {code}, 실제 {verdict.code}(allowed={verdict.allowed})")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _fixture(root, m1_status="done")
        verdict = evaluate_wbs_gate(root, wbs="M-001/WBS-1.2")
        if verdict.allowed or verdict.code != "milestone_done":
            problems.append(f"done 역행: 기대 milestone_done, 실제 {verdict.code}")
        verdict = evaluate_wbs_gate(root, wbs="M-002/WBS-2.1")
        if not verdict.allowed:  # M-001 done → 순서 게이트 통과
            problems.append(f"앞 마일스톤 done 인데 거부: {verdict.code}")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _fixture(root, m2_parallel="M-001")
        verdict = evaluate_wbs_gate(root, wbs="M-002/WBS-2.1")
        if not verdict.allowed:
            problems.append(f"parallel_allowed 선언인데 거부: {verdict.code} — 게이트는 로드맵 선언이 결정한다")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _fixture(root, with_roadmap=False)
        verdict = evaluate_wbs_gate(root, wbs=None)
        if not verdict.allowed or verdict.code != "not_applicable":
            problems.append(f"roadmap 부재: 기대 not_applicable, 실제 {verdict.code}")
    with tempfile.TemporaryDirectory() as tmp:
        # draft 는 발동 전이다 — 그리고 active 로 바꾸면(확정) 그 자리에서 선다.
        root = Path(tmp).resolve()
        _fixture(root)
        index = root / "ai-workflow" / "memory" / "active" / "roadmap" / "index.md"
        original = index.read_text(encoding="utf-8")
        index.write_text(original.replace("# Roadmap — fixture\n", "# Roadmap — fixture\n\n- 상태: draft\n", 1), encoding="utf-8")
        verdict = evaluate_wbs_gate(root, wbs=None)
        if not verdict.allowed or verdict.code != "draft_roadmap":
            problems.append(f"draft: 기대 draft_roadmap 허용, 실제 {verdict.code}(allowed={verdict.allowed})")
        index.write_text(original, encoding="utf-8")
        verdict = evaluate_wbs_gate(root, wbs=None)
        if verdict.allowed:
            problems.append("확정(active) 후에도 게이트가 안 선다")
    _record("test_gate_verdict_matrix", not problems, "; ".join(problems))


def test_cli_denies_and_records_declarations() -> None:
    """CLI: 거부는 쓰기 전이고, 허용은 frontmatter 에 링크/예외 선언을 남긴다."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        profile = _fixture(root)
        tasks_dir = root / "ai-workflow" / "memory" / "active" / BRANCH / "backlog" / "tasks"

        rc, payload = _run_cli(profile, ["--apply"])
        if rc != 1 or payload.get("error_code") != "wbs_gate_denied":
            problems.append(f"미링크 create 미거부: rc={rc} {payload.get('error_code')}")
        if list(tasks_dir.glob("TASK-*.md")):
            problems.append("거부됐는데 task 파일이 쓰였다")

        rc, payload = _run_cli(profile, ["--apply", "--wbs", "M-001/WBS-1.2"])
        files = list(tasks_dir.glob("TASK-*.md"))
        if rc != 0 or len(files) != 1:
            problems.append(f"링크 create 실패: rc={rc} files={len(files)}")
        elif "wbs: M-001/WBS-1.2" not in files[0].read_text(encoding="utf-8"):
            problems.append("frontmatter 에 wbs 링크가 없다")

        rc, payload = _run_cli(profile, [
            "--apply", "--task-id", "TASK-2026-01-01-main-002",
            "--wbs", "exempt", "--wbs-exempt-reason", "로드맵 밖 긴급 수리",
        ])
        exempt_file = tasks_dir / "TASK-2026-01-01-main-002.md"
        if rc != 0 or not exempt_file.is_file():
            problems.append(f"exempt create 실패: rc={rc}")
        else:
            text = exempt_file.read_text(encoding="utf-8")
            if "wbs: exempt" not in text or "wbs_exempt_reason: 로드맵 밖 긴급 수리" not in text:
                problems.append("exempt 선언이 frontmatter 에 안 남았다")

        rc, payload = _run_cli(profile, ["--apply", "--task-id", "TASK-2026-01-01-main-003",
                                         "--wbs", "exempt"])
        if rc != 1 or payload.get("source_context", {}).get("gate_code") != "exempt_reason_required":
            problems.append(f"사유 없는 exempt 미거부: rc={rc}")
    _record("test_cli_denies_and_records_declarations", not problems, "; ".join(problems))


def test_cli_without_roadmap_is_additive() -> None:
    """roadmap 부재 프로젝트: --wbs 없이도 기존 그대로 생성된다."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        profile = _fixture(root, with_roadmap=False)
        rc, payload = _run_cli(profile, ["--apply"])
        files = list((root / "ai-workflow" / "memory" / "active" / BRANCH / "backlog" / "tasks").glob("TASK-*.md"))
        ok = rc == 0 and payload.get("status") == "ok" and len(files) == 1
    _record("test_cli_without_roadmap_is_additive", ok, f"rc={rc} files={len(files)}")


def test_mcp_uses_same_verdict() -> None:
    """MCP 경로가 같은 판정 코드를 낸다 — 판정은 한 곳이다."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _fixture(root)
        denied = create_backlog_entry_payload(
            task_id="TASK-2026-01-01-main-001", task_name="t", request_date="2026-01-01",
            status=None, priority=None, tool_version="test", workspace_root=str(root),
        )
        if denied.get("status") != "error" or denied.get("gate_code") != "wbs_required":
            problems.append(f"MCP 미거부: {denied.get('gate_code')}")
        allowed = create_backlog_entry_payload(
            task_id="TASK-2026-01-01-main-001", task_name="t", request_date="2026-01-01",
            status=None, priority=None, tool_version="test", workspace_root=str(root),
            wbs="M-001/WBS-1.2",
        )
        if allowed.get("status") != "ok" or allowed.get("gate_code") != "linked":
            problems.append(f"MCP 링크 허용 실패: {allowed.get('gate_code')}")
    _record("test_mcp_uses_same_verdict", not problems, "; ".join(problems))


def test_cli_update_relinks_wbs() -> None:
    """update `--wbs` 재링크 (TASK-2026-08-28-main-002).

    이전 update 병합은 `--wbs` 를 조용히 버렸다 — M-007 선언 때 열린 exempt
    task 4건의 재링크를 frontmatter 손편집으로 우회해야 했다. 주장:
    ① 재링크가 frontmatter 를 갱신하고 낡은 exempt 사유를 걷는다,
    ② 재링크도 **같은 게이트**를 탄다 (dangling 거부, 쓰기 전),
    ③ `--wbs` 미지정 update 는 기존 링크를 보존한다,
    ④ wbs 줄이 아예 없던(로드맵 이전) task 에도 삽입된다.
    """
    problems: list[str] = []
    task_id = "TASK-2026-01-01-main-004"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        profile = _fixture(root)
        task_file = (root / "ai-workflow" / "memory" / "active" / BRANCH
                     / "backlog" / "tasks" / f"{task_id}.md")

        rc, _ = _run_cli(profile, ["--apply", "--task-id", task_id,
                                   "--wbs", "exempt", "--wbs-exempt-reason", "긴급 수리"])
        if rc != 0 or not task_file.is_file():
            problems.append(f"seed exempt create 실패: rc={rc}")

        # ① exempt → leaf 재링크: 링크 갱신 + 낡은 사유 제거
        rc, _ = _run_cli(profile, ["--apply", "--task-id", task_id,
                                   "--mode", "update", "--wbs", "M-001/WBS-1.2"])
        text = task_file.read_text(encoding="utf-8")
        if rc != 0 or "wbs: M-001/WBS-1.2" not in text:
            problems.append(f"재링크 미반영: rc={rc}")
        if "wbs_exempt_reason" in text:
            problems.append("낡은 exempt 사유가 남았다 — 링크와 사유가 다른 말을 한다")

        # ② dangling 재링크는 게이트가 거부하고 파일은 그대로다
        rc, payload = _run_cli(profile, ["--apply", "--task-id", task_id,
                                         "--mode", "update", "--wbs", "M-001/WBS-9.9"])
        if rc != 1 or payload.get("source_context", {}).get("gate_code") != "wbs_dangling":
            problems.append(f"dangling 재링크 미거부: rc={rc} "
                            f"{payload.get('source_context', {}).get('gate_code')}")
        if "wbs: M-001/WBS-1.2" not in task_file.read_text(encoding="utf-8"):
            problems.append("거부됐는데 파일이 바뀌었다")

        # ③ --wbs 미지정 update 는 링크를 보존한다
        rc, _ = _run_cli(profile, ["--apply", "--task-id", task_id,
                                   "--mode", "update", "--progress-note", "진행 갱신"])
        if rc != 0 or "wbs: M-001/WBS-1.2" not in task_file.read_text(encoding="utf-8"):
            problems.append(f"미지정 update 가 링크를 지웠다: rc={rc}")

        # ④ wbs 줄이 없던 task (로드맵 이전 생성) 에도 upsert 된다
        stripped = "\n".join(
            line for line in task_file.read_text(encoding="utf-8").splitlines()
            if not line.startswith("wbs")
        ) + "\n"
        task_file.write_text(stripped, encoding="utf-8")
        rc, _ = _run_cli(profile, ["--apply", "--task-id", task_id,
                                   "--mode", "update", "--wbs", "M-001/WBS-1.1.1"])
        if rc != 0 or "wbs: M-001/WBS-1.1.1" not in task_file.read_text(encoding="utf-8"):
            problems.append(f"wbs 줄 없던 task 에 삽입 실패: rc={rc}")
    _record("test_cli_update_relinks_wbs", not problems, "; ".join(problems))


def test_repo_gate_is_armed() -> None:
    """이 저장소에서 게이트가 무장돼 있다 — draft(무-apply)도 거부된다 (읽기 전용)."""
    rc, payload = _run_cli(REPO_ROOT / "docs" / "PROJECT_PROFILE.md", [])
    ok = rc == 1 and payload.get("error_code") == "wbs_gate_denied"
    _record("test_repo_gate_is_armed", ok, f"rc={rc} {payload.get('error_code')}")


def main() -> int:
    cases = [
        test_gate_verdict_matrix,
        test_cli_denies_and_records_declarations,
        test_cli_update_relinks_wbs,
        test_cli_without_roadmap_is_additive,
        test_mcp_uses_same_verdict,
        test_repo_gate_is_armed,
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
