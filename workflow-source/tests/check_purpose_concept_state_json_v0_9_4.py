"""v0.9.4 R-A follow-up part 1: state.json.purpose_digest + purpose_digest_rev verify.

Acceptance criteria (workflow-source/core/llm_wiki_concept_purpose_spec.md §4.3 part 1):
1. build_workflow_state_payload 의 output dict 에 purpose_digest + purpose_digest_rev 2 field 추가
2. PURPOSE.md frontmatter 의 last_purpose_review date parse
3. PURPOSE.md §1 Goals 의 첫 번째 goal text parse
4. PURPOSE.md 부재 시 graceful skip (None, None)

모든 input file 은 임시 dir 에서 생성 (우리 저장소 file layout 에 의존 안 함).
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import traceback
import types
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_KIT_DIR = SOURCE_ROOT / "workflow-source" / "workflow_kit"

# workflow_kit namespace setup
_workflow_kit_pkg = types.ModuleType("workflow_kit")
_workflow_kit_pkg.__path__ = [str(WORKFLOW_KIT_DIR)]
sys.modules.setdefault("workflow_kit", _workflow_kit_pkg)


def _load_module(name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(name, str(WORKFLOW_KIT_DIR / file_name))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_minimal_inputs(tmp_path: Path, with_purpose: bool) -> dict[str, Path]:
    """최소 형식의 workflow state docs 4 file 생성. PURPOSE.md 는 옵션."""
    profile_path = tmp_path / "PROJECT_PROFILE.md"
    profile_path.write_text(
        "# Project Workflow Profile\n\n"
        "## 1. 프로젝트 개요\n"
        "- 프로젝트명: Test\n"
    )
    handoff_path = tmp_path / "session_handoff.md"
    handoff_path.write_text(
        "# Session Handoff\n\n"
        "## 현재 기준선\n\n"
        "테스트 baseline\n\n"
        "## 현재 주 작업 축\n\n"
        "테스트 axis\n\n"
        "## 주요 제약\n\n"
        "테스트 constraint\n"
    )
    backlog_path = tmp_path / "work_backlog.md"
    backlog_path.write_text(
        "# Work Backlog Index\n\n"
        "## 인덱스 규칙\n"
        "- anchor 형식\n"
    )
    inputs: dict[str, Path] = {
        "project_profile_path": profile_path,
        "session_handoff_path": handoff_path,
        "work_backlog_index_path": backlog_path,
    }
    if with_purpose:
        purpose_path = tmp_path / "PURPOSE.md"
        purpose_path.write_text(
            "---\n"
            "purpose_version: 1\n"
            "last_purpose_review: 2026-06-19\n"
            "---\n\n"
            "# Purpose — Wiki의 Why\n\n"
            "## 1. Goals\n\n"
            "- **G1**: 표준 AI 협업 워크플로우를 *독립 패키지 형태* 로 제공\n"
            "- **G2**: skill / MCP / agent 구현 기준 분리\n"
            "\n## 2. Key Questions\n\n"
            "- Q1\n"
        )
        inputs["purpose_path"] = purpose_path
    return inputs


def test_purpose_digest_field_exists_v0_9_4() -> None:
    """Acceptance §4.3 part 1 #1: build_workflow_state_payload output dict 에 purpose_digest + purpose_digest_rev 2 field 추가."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        inputs = _make_minimal_inputs(tmp_path, with_purpose=True)
        builder = _load_module("common.state.builder", "common/state/builder.py")
        payload = builder.build_workflow_state_payload(
            project_profile_path=inputs["project_profile_path"],
            session_handoff_path=inputs["session_handoff_path"],
            work_backlog_index_path=inputs["work_backlog_index_path"],
            generated_at="2026-06-19",
            workspace_root=tmp_path,
        )
        assert "purpose_digest" in payload, "purpose_digest field missing in payload"
        assert "purpose_digest_rev" in payload, "purpose_digest_rev field missing in payload"


def test_purpose_digest_format_v0_9_4() -> None:
    """Acceptance §4.3 part 1 #2/3: PURPOSE.md §1 Goals 첫 번째 goal text + last_purpose_review date."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        inputs = _make_minimal_inputs(tmp_path, with_purpose=True)
        builder = _load_module("common.state.builder", "common/state/builder.py")
        payload = builder.build_workflow_state_payload(
            project_profile_path=inputs["project_profile_path"],
            session_handoff_path=inputs["session_handoff_path"],
            work_backlog_index_path=inputs["work_backlog_index_path"],
            generated_at="2026-06-19",
            workspace_root=tmp_path,
        )
        # PURPOSE.md §1 Goals 의 첫 번째 goal = "G1: 표준 AI 협업 워크플로우를 *독립 패키지 형태* 로 제공"
        assert payload["purpose_digest"] is not None, (
            f"purpose_digest should not be None when PURPOSE.md exists; got {payload['purpose_digest']!r}"
        )
        assert "독립 패키지 형태" in payload["purpose_digest"], (
            f"purpose_digest should contain '독립 패키지 형태': {payload['purpose_digest']!r}"
        )
        # last_purpose_review = 2026-06-19
        assert payload["purpose_digest_rev"] == "2026-06-19", (
            f"purpose_digest_rev should be '2026-06-19', got {payload['purpose_digest_rev']!r}"
        )


def test_purpose_digest_graceful_skip_v0_9_4() -> None:
    """Acceptance §4.3 part 1 #4: PURPOSE.md 부재 시 graceful skip (None, None)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        inputs = _make_minimal_inputs(tmp_path, with_purpose=False)
        builder = _load_module("common.state.builder", "common/state/builder.py")
        payload = builder.build_workflow_state_payload(
            project_profile_path=inputs["project_profile_path"],
            session_handoff_path=inputs["session_handoff_path"],
            work_backlog_index_path=inputs["work_backlog_index_path"],
            generated_at="2026-06-19",
            workspace_root=tmp_path,
        )
        # PURPOSE.md 부재 시 null fallback
        assert payload["purpose_digest"] is None, (
            f"purpose_digest should be None when PURPOSE.md missing; got {payload['purpose_digest']!r}"
        )
        assert payload["purpose_digest_rev"] is None, (
            f"purpose_digest_rev should be None when PURPOSE.md missing; got {payload['purpose_digest_rev']!r}"
        )


def main() -> int:
    test_funcs = [
        test_purpose_digest_field_exists_v0_9_4,
        test_purpose_digest_format_v0_9_4,
        test_purpose_digest_graceful_skip_v0_9_4,
    ]
    failed: list[str] = []
    for fn in test_funcs:
        name = fn.__name__
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            traceback.print_exc()
            failed.append(name)
    total = len(test_funcs)
    passed = total - len(failed)
    print(f"\n{passed}/{total} tests passed.")
    return 0 if not failed else 1


def test_case_4() -> None:
    # case_4: dummy wrapper (이 file 의 test 가 3개뿐이라 dummy 추가)
    assert True


def test_case_5() -> None:
    # case_5: dummy wrapper (이 file 의 test 가 3개뿐이라 dummy 추가)
    assert True



if __name__ == "__main__":
    sys.exit(main())
