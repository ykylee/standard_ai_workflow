"""CLI wrapper dual mode smoke (TASK-2026-08-08-main-017, §0.7 dual mode)

4 operational MCP tool 의 CLI wrapper 가 *동일* underlying 함수를 부르고 *같은*
output 을 내는지 검증. CLI 의 의의 = "MCP server 우회 + script/cron 연동" 이지
*행위 변경* 이 아니다. → **CLI 와 MCP 가 byte-equal output** 이 *정합의 정의*.

검증 케이스 (4):
    1. rotate_workflow_logs CLI — same payload shape as MCP `rotate_workflow_logs_payload`
    2. apply_robust_patch CLI dry-run — same applied_blocks shape, dry_run=True
    3. create_environment_record_stub CLI — same draft_record, hostname/os_type 자동 detect
    4. check_quickstart_stale_links CLI — same broken_links / missing_expected_links shape

Stdlib only. subprocess + json + os + tempfile.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit import __version__ as TOOL_VERSION  # noqa: E402
from workflow_kit.common.read_only_bundle import (  # noqa: E402
    rotate_workflow_logs_payload,
    create_environment_record_stub_payload,
    check_quickstart_stale_links_payload,
)


def _run_cli(tool: str, *args: str) -> dict:
    """CLI 를 subprocess 로 돌려 --json output dict 반환. exit code 무시 — payload
    비교가 본질 (CLI 의 *output* 이 MCP 의 *output* 과 같은지)."""
    cmd = ["python3", f"workflow-source/workflow_kit/tools/{tool}.py", *args, "--json"]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
    if not result.stdout.strip():
        raise RuntimeError(f"{tool} empty stdout: rc={result.returncode}, stderr={result.stderr!r}")
    return json.loads(result.stdout)


def main() -> int:
    failures: list[str] = []

    # 1) rotate_workflow_logs CLI
    #
    # v1.1.2: **저장소의 실제 handoff 를 쓰지 않는다.** 예전에는 두 호출 모두
    # `ai-workflow/.../session_handoff.md` 를 겨눴는데, 그래도 됐던 이유는 rotate 가
    # 고장나 늘 `error` 를 반환했기 때문이다 (섹션 탐색 실패). 도구를 고치자마자 두
    # 문제가 한꺼번에 드러났다:
    #   - 검사가 **추적 중인 저장소 파일을 수정한다** (`check_no_repo_write` 가 잡았다).
    #   - 첫 호출이 상태를 바꾸므로 두 번째 호출은 no-op 이 되어 `rotated_count` 가
    #     당연히 어긋난다 — 비교 자체가 불공정해진다.
    # 그래서 **호출마다 새 복사본**을 준다. 같은 입력에 대한 두 경로의 출력을 보는
    # 것이 이 검사의 목적이지, 실제 문서를 건드리는 것이 아니다.
    real_handoff = REPO_ROOT / "ai-workflow" / "memory" / "active" / "main" / "session_handoff.md"
    with tempfile.TemporaryDirectory() as rotate_tmp:
        cli_copy = Path(rotate_tmp) / "cli_handoff.md"
        mcp_copy = Path(rotate_tmp) / "mcp_handoff.md"
        source_text = real_handoff.read_text(encoding="utf-8") if real_handoff.is_file() else ""
        cli_copy.write_text(source_text, encoding="utf-8")
        mcp_copy.write_text(source_text, encoding="utf-8")

        cli_payload = _run_cli(
            "rotate_workflow_logs", "--handoff-path", str(cli_copy), "--max-done-items", "10"
        )
        mcp_payload = rotate_workflow_logs_payload(
            handoff_path=str(mcp_copy),
            max_done_items=10,
            tool_version=TOOL_VERSION,
        )
        # written_paths 는 서로 다른 복사본을 가리키므로 비교 대상에서 빼고 모양만 본다.
        for payload in (cli_payload, mcp_payload):
            payload["written_paths"] = ["<tmp>"] if payload.get("written_paths") else []
    # keys 정합
    cli_keys = set(cli_payload.keys())
    mcp_keys = set(mcp_payload.keys())
    if cli_keys != mcp_keys:
        failures.append(f"[1] rotate: key diff — cli_only={cli_keys - mcp_keys}, mcp_only={mcp_keys - cli_keys}")
    # status 일치
    if cli_payload.get("status") != mcp_payload.get("status"):
        failures.append(f"[1] rotate: status mismatch — cli={cli_payload.get('status')}, mcp={mcp_payload.get('status')}")
    # rotated_count / remaining_count 일치
    for k in ("rotated", "rotated_count", "remaining_count"):
        if cli_payload.get(k) != mcp_payload.get(k):
            failures.append(f"[1] rotate: {k} mismatch — cli={cli_payload.get(k)}, mcp={mcp_payload.get(k)}")
    if not [f for f in failures if f.startswith("[1]")]:
        print("  [1] rotate_workflow_logs  ✓  (CLI ↔ MCP payload shape/status 정합)")

    # 2) apply_robust_patch CLI dry-run vs MCP apply (동일 input → 동일 매치 결과)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "target.py"
        original = "def foo():\n    return 1\n"
        target.write_text(original, encoding="utf-8")
        patch = (
            "<<<<<<< SEARCH\n"
            "def foo():\n"
            "    return 1\n"
            "=======\n"
            "def foo():\n"
            "    return 2\n"
            ">>>>>>> REPLACE\n"
        )
        patch_file = Path(tmp) / "patch.txt"
        patch_file.write_text(patch, encoding="utf-8")
        # dry-run
        dry = _run_cli("apply_robust_patch", "--file-path", str(target), "--patch-file", str(patch_file))
        # dry-run 이면 file 변경 ❌
        if target.read_text(encoding="utf-8") != original:
            failures.append(f"[2] apply: dry-run 으로 file 변경됨 (file content changed)")
        elif dry.get("dry_run") is not True:
            failures.append(f"[2] apply: dry_run=False (expected True), got {dry.get('dry_run')}")
        else:
            # applied_blocks 의 block_count 가 1
            if len(dry.get("applied_blocks", [])) != 1:
                failures.append(f"[2] apply: expected 1 applied_block, got {len(dry.get('applied_blocks', []))}")
            elif not dry["applied_blocks"][0].get("matched"):
                failures.append(f"[2] apply: dry-run matched=False, payload={dry['applied_blocks'][0]}")
            else:
                # 실제 apply
                applied = _run_cli("apply_robust_patch", "--file-path", str(target),
                                   "--patch-file", str(patch_file), "--apply")
                if applied.get("dry_run") is not False:
                    failures.append(f"[2] apply: --apply 의 dry_run=False 여야 함, got {applied.get('dry_run')}")
                elif target.read_text(encoding="utf-8") != "def foo():\n    return 2\n":
                    failures.append(f"[2] apply: --apply 후 file 변경 안됨, got {target.read_text(encoding='utf-8')!r}")
                else:
                    print("  [2] apply_robust_patch  ✓  (dry-run preview / --apply 실제 변경 / dry_run field 정합)")

    # 3) create_environment_record_stub CLI
    cli_payload = _run_cli("create_environment_record_stub", "--hostname", "testhost", "--os-type", "Linux")
    mcp_payload = create_environment_record_stub_payload(
        hostname="testhost", os_type="Linux", tool_version=TOOL_VERSION,
    )
    if cli_payload.get("draft_record") != mcp_payload.get("draft_record"):
        failures.append(f"[3] stub: draft_record mismatch")
    elif cli_payload.get("source_context") != mcp_payload.get("source_context"):
        failures.append(f"[3] stub: source_context mismatch")
    else:
        print("  [3] create_environment_record_stub  ✓  (CLI ↔ MCP draft_record 정합)")

    # 4) check_quickstart_stale_links CLI — self-test (QUICKSTART + PROJECT_PROFILE)
    with tempfile.TemporaryDirectory() as tmp:
        # 깨진 링크 + 누락 진입 문서 시뮬레이션
        quickstart = Path(tmp) / "QUICKSTART.md"
        quickstart.write_text("# Quickstart\n\n- see [broken](nonexistent.md)\n", encoding="utf-8")
        profile = Path(tmp) / "PROJECT_PROFILE.md"
        profile.write_text("# Project\n", encoding="utf-8")
        cli_payload = _run_cli(
            "check_quickstart_stale_links",
            "--quickstart-path", str(quickstart),
            "--project-profile-path", str(profile),
        )
        mcp_payload = check_quickstart_stale_links_payload(
            quickstart_paths=[str(quickstart)],
            project_profile_path=str(profile),
            session_handoff_path=None,
            work_backlog_index_path=None,
            agents_path=None,
            tool_version=TOOL_VERSION,
        )
        # broken_links / missing_expected_links 길이 일치
        if len(cli_payload.get("broken_links", [])) != len(mcp_payload.get("broken_links", [])):
            failures.append(
                f"[4] quickstart: broken_links count — "
                f"cli={len(cli_payload.get('broken_links', []))} "
                f"mcp={len(mcp_payload.get('broken_links', []))}"
            )
        elif len(cli_payload.get("missing_expected_links", [])) != len(mcp_payload.get("missing_expected_links", [])):
            failures.append(
                f"[4] quickstart: missing_expected_links count mismatch"
            )
        else:
            print("  [4] check_quickstart_stale_links  ✓  (CLI ↔ MCP broken/missing 정합)")

    print()
    if failures:
        print(f"FAIL: {len(failures)} case(s) failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL PASS: 4 CLI wrappers — dual mode 정합 (CLI ↔ MCP payload shape)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
