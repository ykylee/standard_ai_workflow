"""tools — deprecated shim package (v1.1.8, TASK-2026-08-12-main-006).

구현은 전부 :mod:`workflow_kit.tools` 로 이동했다. top-level `tools` 는 공개
배포(PyPI) 시 다른 패키지와 site-packages 충돌을 일으키는 일반명이기 때문이다
(docs/planning/cli-distribution-review-2026-08.md §2).

본 패키지의 각 모듈은 같은 이름의 `workflow_kit.tools.<name>` 을 재수출하는
shim 이며, 1st deprecation cycle 동안 유지 후 다음 cycle 에 제거된다.
hooks/ 와 completions/ 자산은 여기 남는다 (경로 계약 유지).
"""
