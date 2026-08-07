"""정본 규칙의 **생성된 스냅샷** — 직접 고치지 않는다.

생성: ``python3 -m workflow_kit.common.standard_rules --apply``
정본: ``core/global_workflow_standard.md`` §1 · §3 · §8
검증: ``tests/check_standard_single_source.py``

wheel 설치처럼 ``core/`` 가 함께 배포되지 않는 환경에서 진입점 렌더링이 규칙을
잃지 않도록 두는 사본이다. 정본과의 일치는 검사로 강제된다.
"""

from __future__ import annotations


PRINCIPLES: tuple[str, ...] = (
    '새 세션은 항상 현재 상태 요약 문서부터 읽는다.',
    '작업은 시작 전에 목적, 범위, 예상 산출물, 영향 문서를 짧게 브리핑한다.',
    '작업은 상태 문서에 기록하고, 진행 상태는 `planned`, `in_progress`, `blocked`, `done` 중 하나로 관리한다.',
    '검증하지 않은 결과는 완료로 확정하지 않는다.',
    '세션 종료 전에는 다음 세션이 바로 이어받을 수 있게 현재 상태를 요약한다.',
    '여러 에이전트가 함께 일할 수 있으므로, 작업 시작 전에 원격을 동기화해 다른 에이전트의 진행 상황을 확인하고 겹치지 않는 작업을 선택한다.',
    '다른 에이전트의 작업을 지우거나 덮어쓰는 등 되돌릴 수 없는 작업은 단독으로 결정하지 않고 사용자에게 확인한다.',
    '공통 표준은 얇게 유지하고, 프로젝트별 차이는 프로젝트 프로파일에 둔다.',
)

TASK_STATES: tuple[str, ...] = (
    'planned',
    'in_progress',
    'blocked',
    'done',
)

CLOSE_ORDER: str = '세션 종료는 **memory 갱신 → commit → push** 순서로 진행한다. memory 갱신을 commit 이후 별도 turn 에 분리하지 않는다 (push 시 memory 갱신 내용이 동일 commit 에 포함되도록 협업 정합 보장).'
