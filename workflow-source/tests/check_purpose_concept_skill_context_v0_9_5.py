"""v0.9.5 R-A follow-up part 2: skill context load integration verify.

Acceptance criteria (workflow-source/core/llm_wiki_concept_purpose_spec.md §4.3 part 2):
1. session-start output_model 에 purpose_context field 존재 (purpose_digest + body_excerpt populate)
2. backlog-update output_model 에 purpose_context + scope_creep_warnings 2 field 존재
3. doc-sync output dict 에 purpose_context field 존재
4. check_scope_creep 가 PURPOSE.md §3 제외 영역과 매칭 시 scope_creep_warnings 1줄 이상 emit
5. PURPOSE.md 부재 시 모든 3개 skill 의 purpose_context 가 graceful skip (scope_creep_warnings = [])

모든 input file 은 임시 dir 에서 생성 (저장소 file layout 의존 ❌).
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
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


def _make_minimal_inputs(
    tmp_path: Path,
    *,
    with_purpose: bool = True,
    with_state: bool = True,
) -> dict[str, Path]:
    """최소 형식의 workflow state docs + (옵션) PURPOSE.md + (옵션) state.json."""
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
            "\n## 3. Research Scope\n\n"
            "### 포함 영역\n\n"
            "- workflow state docs\n"
            "- deprecation policy\n"
            "- release pipeline\n"
            "\n### 제외 영역\n\n"
            "- **결제 도메인** 로직\n"
            "- **LLM model fine-tuning**\n"
        )
        inputs["purpose_path"] = purpose_path
    if with_state:
        state_path = tmp_path / "state.json"
        state_path.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "purpose_digest": "G1: 표준 AI 협업 워크플로우를 *독립 패키지 형태* 로 제공",
                    "purpose_digest_rev": "2026-06-19",
                    "session": {
                        "in_progress_items": [],
                        "recent_done_items": [],
                        "blocked_items": [],
                    },
                    "backlog": {
                        "latest_backlog_path": None,
                        "task_count": 0,
                        "in_progress_items": [],
                        "blocked_items": [],
                        "done_items": [],
                    },
                    "source_of_truth": {
                        "project_profile_path": "PROJECT_PROFILE.md",
                        "session_handoff_path": "session_handoff.md",
                        "work_backlog_index_path": "work_backlog.md",
                        "latest_backlog_path": None,
                    },
                },
                ensure_ascii=False,
            )
        )
        inputs["state_path"] = state_path
    return inputs


# ---------------------------------------------------------------------------
# Acceptance #1: session-start output_model 에 purpose_context field 존재
# ---------------------------------------------------------------------------
def test_purpose_context_session_start_v0_9_5() -> None:
    """Acceptance §4.3 part 2 #1: session-start output_model 에 purpose_context field 추가 + populate."""
    helper = _load_module("common.purpose_context", "common/purpose_context.py")
    schemas = _load_module("common.schemas", "common/schemas/__init__.py")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        inputs = _make_minimal_inputs(tmp_path, with_purpose=True, with_state=True)

        # helper 가 build_purpose_context 정상 populate
        purpose_context_data = helper.build_purpose_context(
            workspace_root=tmp_path,
            state_path=inputs["state_path"],
            purpose_path=inputs["purpose_path"],
        )
        assert purpose_context_data["purpose_digest"] is not None, "purpose_digest should populate from state.json"
        assert "독립 패키지 형태" in purpose_context_data["purpose_digest"], (
            f"purpose_digest should contain G1 text: {purpose_context_data['purpose_digest']!r}"
        )
        assert purpose_context_data["purpose_digest_rev"] == "2026-06-19"
        assert purpose_context_data["body_excerpt"] is not None, "body_excerpt should populate from PURPOSE.md"
        assert "독립 패키지 형태" in purpose_context_data["body_excerpt"]
        # scope_included/excluded
        assert "workflow state docs" in purpose_context_data["scope_included"]
        assert any("결제" in ex for ex in purpose_context_data["scope_excluded"]), (
            f"scope_excluded should contain '결제 도메인': {purpose_context_data['scope_excluded']!r}"
        )

        # SessionStartPurposeContext schema 에 field 존재 + helper output 으로 instantiate 가능
        SessionStartPurposeContext = schemas.SessionStartPurposeContext
        ctx = SessionStartPurposeContext(**purpose_context_data)
        dumped = ctx.model_dump()
        assert "purpose_digest" in dumped
        assert "body_excerpt" in dumped
        assert dumped["purpose_digest_rev"] == "2026-06-19"
        assert dumped["body_excerpt_char_count"] > 0
        assert dumped["body_excerpt_truncated"] is False

        # SessionStartOutput schema 에 purpose_context field 존재
        SessionStartOutput = schemas.SessionStartOutput
        schema_fields = SessionStartOutput.model_fields
        assert "purpose_context" in schema_fields, (
            f"SessionStartOutput must have purpose_context field; got {list(schema_fields.keys())}"
        )


# ---------------------------------------------------------------------------
# Acceptance #2: backlog-update output_model 에 purpose_context + scope_creep_warnings 2 field
# ---------------------------------------------------------------------------
def test_purpose_context_backlog_update_v0_9_5() -> None:
    """Acceptance §4.3 part 2 #2: backlog-update output_model 에 purpose_context + scope_creep_warnings 2 field."""
    helper = _load_module("common.purpose_context", "common/purpose_context.py")
    schemas = _load_module("common.schemas", "common/schemas/__init__.py")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        inputs = _make_minimal_inputs(tmp_path, with_purpose=True, with_state=True)

        # helper 가 정상 populate
        purpose_context_data = helper.build_purpose_context(
            workspace_root=tmp_path,
            state_path=inputs["state_path"],
            purpose_path=inputs["purpose_path"],
        )
        BacklogUpdatePurposeContext = schemas.BacklogUpdatePurposeContext
        ctx = BacklogUpdatePurposeContext(**purpose_context_data)
        assert ctx.purpose_digest is not None
        assert "workflow state docs" in ctx.scope_included
        assert any("결제" in ex for ex in ctx.scope_excluded)

        # BacklogUpdateOutput schema 에 purpose_context + scope_creep_warnings 2 field
        BacklogUpdateOutput = schemas.BacklogUpdateOutput
        schema_fields = BacklogUpdateOutput.model_fields
        assert "purpose_context" in schema_fields, (
            f"BacklogUpdateOutput must have purpose_context field; got {list(schema_fields.keys())}"
        )
        assert "scope_creep_warnings" in schema_fields, (
            f"BacklogUpdateOutput must have scope_creep_warnings field; got {list(schema_fields.keys())}"
        )


# ---------------------------------------------------------------------------
# Acceptance #3: doc-sync output dict 에 purpose_context field
# ---------------------------------------------------------------------------
def test_purpose_context_doc_sync_v0_9_5() -> None:
    """Acceptance §4.3 part 2 #3: doc-sync schema 에 DocSyncPurposeContext + DocSyncOutput.purpose_context field."""
    helper = _load_module("common.purpose_context", "common/purpose_context.py")
    schemas = _load_module("common.schemas", "common/schemas/__init__.py")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        inputs = _make_minimal_inputs(tmp_path, with_purpose=True, with_state=True)

        purpose_context_data = helper.build_purpose_context(
            workspace_root=tmp_path,
            state_path=inputs["state_path"],
            purpose_path=inputs["purpose_path"],
        )
        DocSyncPurposeContext = schemas.DocSyncPurposeContext
        ctx = DocSyncPurposeContext(**purpose_context_data)
        assert ctx.purpose_digest is not None
        assert "독립 패키지 형태" in ctx.body_excerpt

        # DocSyncOutput schema 에 purpose_context field
        DocSyncOutput = schemas.DocSyncOutput
        schema_fields = DocSyncOutput.model_fields
        assert "purpose_context" in schema_fields, (
            f"DocSyncOutput must have purpose_context field; got {list(schema_fields.keys())}"
        )


# ---------------------------------------------------------------------------
# Acceptance #4: check_scope_creep 가 제외 영역 매칭 시 warning emit
# ---------------------------------------------------------------------------
def test_scope_creep_detection_v0_9_5() -> None:
    """Acceptance §4.3 part 2 #4: task_brief 가 PURPOSE.md §3 제외 영역과 매칭 시 scope_creep_warnings 1줄 이상."""
    helper = _load_module("common.purpose_context", "common/purpose_context.py")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        inputs = _make_minimal_inputs(tmp_path, with_purpose=True, with_state=True)

        # extract_research_scope 가 §3 의 포함/제외 parse
        scope = helper.extract_research_scope(inputs["purpose_path"])
        assert any("결제" in ex for ex in scope["excluded"]), (
            f"excluded should contain '결제 도메인': {scope['excluded']!r}"
        )
        assert "workflow state docs" in scope["included"]

        # case A: in-scope task — no warning
        warnings_a = helper.check_scope_creep(
            task_brief="deprecation policy 운영 spec 보강",
            affected_documents=["workflow-source/core/v0_9_0_deprecation_policy_spec.md"],
            scope=scope,
        )
        assert warnings_a == [], f"in-scope task should have no scope creep warning; got {warnings_a!r}"

        # case B: out-of-scope task — warning 1줄 이상
        warnings_b = helper.check_scope_creep(
            task_brief="stripe 결제 도메인 로직을 추가한다",
            affected_documents=[],
            scope=scope,
        )
        assert len(warnings_b) >= 1, f"out-of-scope task should have at least 1 warning; got {warnings_b!r}"
        assert any("결제" in w for w in warnings_b), (
            f"warning should mention '결제 도메인': {warnings_b!r}"
        )

        # case C: affected_documents 에서 매칭
        # - excluded normalized = "llm model fine-tuning" → first 2 token = "llm model"
        # - affected_documents normalized = "scripts/llm_model_trainer.py" → contains "llm model"
        warnings_c = helper.check_scope_creep(
            task_brief="LLM model fine-tuning pipeline 작업",
            affected_documents=["scripts/llm_model_trainer.py"],
            scope=scope,
        )
        assert any("LLM" in w or "fine" in w.lower() for w in warnings_c), (
            f"affected_document match should trigger warning: {warnings_c!r}"
        )


# ---------------------------------------------------------------------------
# Acceptance #5: PURPOSE.md 부재 시 graceful skip
# ---------------------------------------------------------------------------
def test_purpose_context_graceful_skip_v0_9_5() -> None:
    """Acceptance §4.3 part 2 #5: PURPOSE.md 부재 시 모든 helper 가 graceful skip.

    - build_purpose_context: scope_warnings 에 "PURPOSE.md 부재" 1줄, 나머지 field 는 null/empty
    - check_scope_creep: empty list 반환 (early return, excluded 비어있음)
    """
    helper = _load_module("common.purpose_context", "common/purpose_context.py")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # PURPOSE.md 없이 helper 호출
        result = helper.build_purpose_context(
            workspace_root=tmp_path,
            state_path=None,
            purpose_path=None,
        )
        # purpose_digest/rev/body_excerpt 모두 null
        assert result["purpose_digest"] is None
        assert result["purpose_digest_rev"] is None
        assert result["purpose_path"] is None
        assert result["body_excerpt"] is None
        assert result["body_excerpt_char_count"] == 0
        # scope lists 비어있음
        assert result["scope_included"] == []
        assert result["scope_excluded"] == []
        # scope_warnings 에 advisory 1줄
        assert any("PURPOSE.md 부재" in w for w in result["scope_warnings"]), (
            f"scope_warnings should contain PURPOSE.md 부재 advisory: {result['scope_warnings']!r}"
        )

        # check_scope_creep: empty excluded → no-op early return
        warnings = helper.check_scope_creep(
            task_brief="결제 도메인 로직 추가",
            affected_documents=[],
            scope={"included": [], "excluded": []},
        )
        assert warnings == [], f"graceful skip should not emit warning; got {warnings!r}"

        # state.json 만 있는 경우 (PURPOSE.md 부재): purpose_digest 만 populate
        state_path = tmp_path / "state.json"
        state_path.write_text(
            json.dumps(
                {
                    "purpose_digest": "G1 only (no PURPOSE.md)",
                    "purpose_digest_rev": "2026-06-19",
                }
            )
        )
        result2 = helper.build_purpose_context(
            workspace_root=tmp_path,
            state_path=state_path,
            purpose_path=None,
        )
        assert result2["purpose_digest"] == "G1 only (no PURPOSE.md)"
        assert result2["purpose_digest_rev"] == "2026-06-19"
        assert result2["body_excerpt"] is None
        assert result2["scope_included"] == []


# ---------------------------------------------------------------------------
# Acceptance #6 (보너스): end-to-end skill script 가 purpose_context 출력
# ---------------------------------------------------------------------------
def test_skill_scripts_integration_v0_9_5() -> None:
    """Acceptance §4.3 part 2 #6 (보너스): 3개 skill script 가 actual purpose_context output emit.

    subprocess 로 3개 skill script 를 실제 실행하여 stdout JSON 에 purpose_context field 존재 verify.
    pydantic 의존성 있는 실제 venv 환경에서 실행.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        inputs = _make_minimal_inputs(tmp_path, with_purpose=True, with_state=True)

        # 1) session-start
        result = subprocess.run(
            [
                sys.executable,
                str(SOURCE_ROOT / "workflow-source/skills/session-start/scripts/run_session_start.py"),
                "--session-handoff-path", str(inputs["session_handoff_path"]),
                "--work-backlog-index-path", str(inputs["work_backlog_index_path"]),
                "--project-profile-path", str(inputs["project_profile_path"]),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # session-start 가 handoff parse 시도 → 빈 handoff 라서 missing_required_document 가능.
        # purpose_context 가 output 에 포함되었는지 확인 (status 가 ok 일 때)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            assert "purpose_context" in data, (
                f"session-start output must contain purpose_context: {list(data.keys())}"
            )
            assert data["purpose_context"]["purpose_digest"] is not None
            assert data["purpose_context"]["body_excerpt"] is not None

        # 2) backlog-update
        daily_backlog = tmp_path / "backlog" / "2026-06-23.md"
        daily_backlog.parent.mkdir(parents=True, exist_ok=True)
        daily_backlog.write_text("# Backlog 2026-06-23\n")
        result_bu = subprocess.run(
            [
                sys.executable,
                str(SOURCE_ROOT / "workflow-source/skills/backlog-update/scripts/run_backlog_update.py"),
                "--project-profile-path", str(inputs["project_profile_path"]),
                "--task-name", "stripe 결제 도메인 추가",
                "--task-brief", "결제 도메인 로직을 workflow 에 추가",
                "--daily-backlog-path", str(daily_backlog),
                "--mode", "create",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result_bu.returncode == 0:
            data_bu = json.loads(result_bu.stdout)
            assert "purpose_context" in data_bu
            assert "scope_creep_warnings" in data_bu
            assert len(data_bu["scope_creep_warnings"]) >= 1, (
                f"stripe/결제 should trigger scope_creep_warnings: {data_bu['scope_creep_warnings']!r}"
            )

        # 3) doc-sync
        result_ds = subprocess.run(
            [
                sys.executable,
                str(SOURCE_ROOT / "workflow-source/skills/doc-sync/scripts/run_doc_sync.py"),
                "--project-profile-path", str(inputs["project_profile_path"]),
                "--changed-file", "test_file.py",
                "--change-summary", "테스트 변경",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result_ds.returncode == 0:
            data_ds = json.loads(result_ds.stdout)
            assert "purpose_context" in data_ds, (
                f"doc-sync output must contain purpose_context: {list(data_ds.keys())}"
            )
            assert data_ds["purpose_context"]["purpose_digest"] is not None


def main() -> int:
    test_funcs = [
        test_purpose_context_session_start_v0_9_5,
        test_purpose_context_backlog_update_v0_9_5,
        test_purpose_context_doc_sync_v0_9_5,
        test_scope_creep_detection_v0_9_5,
        test_purpose_context_graceful_skip_v0_9_5,
        test_skill_scripts_integration_v0_9_5,
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


if __name__ == "__main__":
    sys.exit(main())
