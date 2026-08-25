#!/usr/bin/env python3
import sys
from pathlib import Path

# Add lib to path for common_utils
LIB_PATH = Path(__file__).resolve().parents[2] / "lib"
if str(LIB_PATH) not in sys.path:
    sys.path.insert(0, str(LIB_PATH))

from common_utils import inject_workflow_source, mcp_main

inject_workflow_source()
from workflow_kit.common.read_only_bundle import assess_milestone_progress_payload

def build_args(parser):
    # ADR-027 M-003: 정본이 roadmap 층으로 바뀌며 입력이 workspace_root 하나가 됐다.
    parser.add_argument("--workspace-root", required=False, default=".",
                        help="Workspace root containing ai-workflow/memory/active/roadmap/. Defaults to cwd.")
    # 은퇴한 인자도 계속 받는다 — argparse 오류로 죽으면 호출자는 이유를 못 듣는다
    # (50차 규칙, v1.3.0 §1.5 선례). 왜 무시되는지는 payload warnings 가 말한다.
    parser.add_argument("--matrix-path", required=False, default=None,
                        help="DEPRECATED — ignored. The roadmap layer (ADR-027) is now the source of truth.")
    parser.add_argument("--backlog-path", required=False, default=None,
                        help="DEPRECATED — ignored. The roadmap layer (ADR-027) is now the source of truth.")

def main():
    mcp_main(
        description="Assess milestone progress from the ADR-027 roadmap layer (roadmap/ SSOT + task wbs links).",
        arg_builder=build_args,
        payload_func=assess_milestone_progress_payload,
    )

if __name__ == "__main__":
    main()
