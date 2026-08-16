"""workflow_kit.cli_commands_doctor - 배포 탐침 dispatcher subcommand.

`wk doctor` 한 handler 뿐이다. 다른 `cli_commands_*` 모듈과 같이 `@register` 가
import 시점에 `cli_registry.COMMANDS` 에 등록하고, `workflow_kit_cli` 가 본
모듈의 handler 를 재-export 한다.

**이름 주의**: :mod:`workflow_kit.cli.doctor` 는 다른 물건이다 (7종 baseline
평가). 이쪽은 *배포 산출물*의 설치 현황을 보는 탐침이다
(`core/workflow_deployment_idempotency.md` §2 · §7 gap 1).
"""

from __future__ import annotations

import sys

from workflow_kit.cli_registry import register

__all__ = ["cmd_doctor"]


@register("doctor")
def cmd_doctor(argv: list[str]) -> int:
    """Forward argv to deploy_doctor.main() — its own argparse handles all flags.

    See :mod:`workflow_kit.deploy_doctor` for the flag surface
    (``--project-root`` / ``--home`` / ``--json`` / ``--strict``).
    """
    try:
        from workflow_kit.deploy_doctor import main as deploy_doctor_main
        return deploy_doctor_main(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
