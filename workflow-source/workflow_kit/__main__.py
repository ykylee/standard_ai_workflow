"""``python -m workflow_kit <command>`` — 실행 파일 없이 도는 정식 진입점.

TASK-2026-10-02-main-007. pip 가 만드는 ``wk`` console-script 런처는 Windows 에서
설치마다 새로 생성되는 서명 없는 ``wk.exe`` 다. 평판 기반 백신(실측: AhnLab V3)이
이를 차단하면 하네스 워크플로우 전체가 멈춘다. 해석기 자체(``python.exe``)는 서명된
배포본이라 이 경로는 막히지 않는다.

``wk <command>`` 와 같은 dispatcher(:func:`workflow_kit.workflow_kit_cli.wk_main`)를
탄다 — stdio UTF-8 고정(main-006)도 같이 받는다.
"""

from __future__ import annotations

import sys

from workflow_kit.workflow_kit_cli import wk_main

if __name__ == "__main__":
    sys.exit(wk_main())
