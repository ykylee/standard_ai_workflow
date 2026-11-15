#!/usr/bin/env python3
"""MCP 도구마다 성공 경로의 output contract family 가 있다 (TASK-2026-11-04-main-002).

`read_only_entrypoint.invoke_tool` 은 도구 이름을 family 로 써서 출력을 검증한다. family 가
`PYDANTIC_MODEL_REGISTRY` 에 없으면 **성공 응답만** `Unknown family` 로 `invalid_tool_output_contract`
가 된다 — 오류 응답은 공통 `ErrorOutput` 이라 통과해서 '실패만 되는 도구' 로 보였다 (1.22.0 발행본의
summarize_git_history · assess_milestone_progress · rotate_workflow_logs · apply_robust_patch).

1. 레지스트리의 모든 도구 이름이 family 로 등록돼 있고, 성공 경로 필수 키 표에도 있다
2. 네 도구를 임시 입력으로 실제 호출하면 rc 0 · status ok · error_code 없음
3. 네 도구의 실제 출력 키가 모델이 선언한 필드 안에 있고, 성공 필수 키를 전부 싣는다 —
   모델만 등록되고 출력과 어긋난 상태를 잡는다
4. 성공 아닌 경로도 계약 안에 있다 — rotate_workflow_logs 가 '최근 완료 작업' 절이 없는 handoff 에서
   ErrorOutput(`handoff_done_section_missing`)을 내고 invoke_tool 이 그것을 계약 위반으로 덮지 않는다;
   roadmap 이 없는 작업 공간의 assess_milestone_progress 도 성공 계약을 지킨다
"""

from __future__ import annotations

#: 임시 git 저장소를 만든다.
CHECK_TIMEOUT_S = 60

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    # registry 를 import 하면 패키지 전체가 입력이다 (check_v0_8_10_… 과 같은 이유).
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    # case 2 의 assess_milestone_progress 는 이 저장소의 roadmap 층을 실제로 읽는다 — 살아 있는 상태 위에서 잰다.
    "ai-workflow/memory/*",
    "docs/PROJECT_PROFILE.md",
)

import json
import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Callable
from unittest import mock

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common import output_contracts as oc
from workflow_kit.server import read_only_registry as reg
from workflow_kit.server.read_only_entrypoint import invoke_tool

FAILURES: list[str] = []
REPAIRED = ("summarize_git_history", "assess_milestone_progress", "rotate_workflow_logs", "apply_robust_patch")
REPO_ROOT = Path(__file__).resolve().parents[2]

HANDOFF = """# Session Handoff

## 4. 최근 완료 작업

- TASK-2026-01-03-main-003 셋째
- TASK-2026-01-02-main-002 둘째
- TASK-2026-01-01-main-001 첫째

## 5. 메모
"""


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def _clean_git_env() -> dict[str, str]:
    # 상속된 GIT_DIR · GIT_WORK_TREE 가 있으면 `git -C <임시 저장소>` 가 바깥 저장소를 읽는다.
    return {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}


def _make_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    env = _clean_git_env()
    git = ["git", "-C", str(repo), "-c", "user.name=check", "-c", "user.email=check@example.invalid",
           "-c", "commit.gpgsign=false"]
    subprocess.run(git[:3] + ["init", "-q"], check=True, env=env)
    for index, subject in enumerate(("feat: 하나", "fix: 둘")):
        (repo / f"f{index}.txt").write_text(subject + "\n", encoding="utf-8")
        subprocess.run(git + ["add", "-A"], check=True, env=env)
        subprocess.run(git + ["commit", "-q", "-m", subject], check=True, env=env)
    return repo


def _payloads(root: Path) -> dict[str, dict[str, Any]]:
    repo = _make_repo(root)
    handoff = root / "session_handoff.md"
    handoff.write_text(HANDOFF, encoding="utf-8")
    target = root / "target.txt"
    target.write_text("a\nb\n", encoding="utf-8")
    return {
        "summarize_git_history": {"repo_path": str(repo), "commit_range": "HEAD~1..HEAD"},
        "assess_milestone_progress": {"workspace_root": str(REPO_ROOT)},
        "rotate_workflow_logs": {"handoff_path": str(handoff), "max_done_items": "1"},
        "apply_robust_patch": {"file_path": str(target),
                               "patch_content": "<<<<<<< SEARCH\nb\n=======\nc\n>>>>>>> REPLACE\n"},
    }


def _invoke(name: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    with mock.patch.dict(os.environ, _clean_git_env(), clear=True):
        return invoke_tool(name, json.dumps(payload))


def case_every_tool_has_a_family() -> list[str]:
    problems = []
    names = [spec.name for spec in reg.READ_ONLY_TOOL_SPECS]
    for name in names:
        model = oc.PYDANTIC_MODEL_REGISTRY.get(name)
        if model is None:
            problems.append(f"`{name}` 의 family 가 PYDANTIC_MODEL_REGISTRY 에 없다 — 성공 응답이 Unknown family 로 죽는다")
        elif name not in oc.SUCCESS_PATH_CONTRACTS:
            problems.append(f"`{name}` 이 SUCCESS_PATH_CONTRACTS 에 없다")
    if len(names) < 15:
        problems.append(f"도구 목록이 {len(names)}개 — 레지스트리를 못 읽었다")
    return problems


def _run_repaired() -> dict[str, tuple[int, dict[str, Any]]]:
    with tempfile.TemporaryDirectory(prefix="mcp-contract-") as tmp:
        root = Path(tmp)
        payloads = _payloads(root)
        results = {name: _invoke(name, payloads[name]) for name in REPAIRED}
        results["_patched_text"] = (0, {"text": (root / "target.txt").read_text(encoding="utf-8")})
        results["_handoff_text"] = (0, {"text": (root / "session_handoff.md").read_text(encoding="utf-8")})
        return results


def case_repaired_tools_succeed() -> list[str]:
    problems = []
    results = _run_repaired()
    for name in REPAIRED:
        rc, out = results[name]
        if rc != 0 or out.get("status") != "ok" or out.get("error_code"):
            problems.append(f"{name}: rc={rc} status={out.get('status')} error_code={out.get('error_code')} "
                            f"warnings={out.get('warnings')}")
    rc, out = results["summarize_git_history"]
    if out.get("commit_count") != 1:
        problems.append(f"summarize_git_history commit_count={out.get('commit_count')} — 범위 HEAD~1..HEAD 는 1")
    if results["_patched_text"][1]["text"] != "a\nc\n":
        problems.append(f"apply_robust_patch 가 파일을 바꾸지 않았다: {results['_patched_text'][1]['text']!r}")
    if results["rotate_workflow_logs"][1].get("rotated_count") != 2 or "첫째" in results["_handoff_text"][1]["text"]:
        problems.append("rotate_workflow_logs 가 상한 1 로 두 줄을 옮기지 않았다")
    return problems


def case_output_keys_match_model() -> list[str]:
    problems = []
    results = _run_repaired()
    for name in REPAIRED:
        _, out = results[name]
        model = oc.PYDANTIC_MODEL_REGISTRY.get(name)
        if model is None:
            problems.append(f"{name}: family 없음")
            continue
        undeclared = sorted(set(out) - set(model.model_fields))
        missing = sorted(oc.SUCCESS_PATH_CONTRACTS.get(name, frozenset()) - set(out))
        if undeclared:
            problems.append(f"{name}: 모델이 선언하지 않은 출력 키 {undeclared}")
        if missing:
            problems.append(f"{name}: 성공 필수 키가 출력에 없다 {missing}")
        if not oc.SUCCESS_PATH_CONTRACTS.get(name):
            problems.append(f"{name}: 성공 필수 키 표가 비었다 — _SUCCESS_REQUIRED_FIELDS_BY_MODEL 에 모델이 없다")
    return problems


def case_non_success_paths_stay_in_contract() -> list[str]:
    problems = []
    with tempfile.TemporaryDirectory(prefix="mcp-contract-") as tmp:
        root = Path(tmp)
        handoff = root / "session_handoff.md"
        handoff.write_text("# Session Handoff\n\n## 5. 메모\n", encoding="utf-8")
        rc, out = _invoke("rotate_workflow_logs", {"handoff_path": str(handoff)})
        if out.get("error_code") != "handoff_done_section_missing" or out.get("status") != "error":
            problems.append(f"절 없는 handoff: rc={rc} status={out.get('status')} error_code={out.get('error_code')}")
        empty = root / "ws"
        empty.mkdir()
        rc, out = _invoke("assess_milestone_progress", {"workspace_root": str(empty)})
        if rc != 0 or out.get("status") != "ok" or out.get("roadmap_present") is not False:
            problems.append(f"roadmap 없는 작업 공간: rc={rc} status={out.get('status')} "
                            f"error_code={out.get('error_code')} roadmap_present={out.get('roadmap_present')}")
    return problems


CASES: list[tuple[str, Callable[[], list[str]]]] = [
    ("1 모든 MCP 도구에 family 가 있다", case_every_tool_has_a_family),
    ("2 고친 네 도구의 성공 경로 rc 0", case_repaired_tools_succeed),
    ("3 출력 키가 모델 선언과 맞다", case_output_keys_match_model),
    ("4 성공 아닌 경로도 계약 안에 있다", case_non_success_paths_stay_in_contract),
]


def main() -> int:
    print(f"check_mcp_tool_output_contracts — MCP 도구 output contract family (kit {TOOL_VERSION})")
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
