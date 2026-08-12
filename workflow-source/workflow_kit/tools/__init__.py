"""workflow_kit.tools — 운영 CLI 도구 모듈 (v1.1.8+, TASK-2026-08-12-main-006).

v1.1.1~v1.1.7 에는 top-level `tools` 패키지였다. `tools` 는 극히 일반적인
이름이라 공개 배포(PyPI) 시 다른 패키지와 site-packages 충돌을 일으킨다 —
배포 검토 (docs/planning/cli-distribution-review-2026-08.md §2) 의 처방으로
`workflow_kit.tools` 로 격상했다.

- 1st cycle (v1.1.8): 구경로 `tools.<name>` 은 shim 으로 유지 (deprecation).
- 2nd cycle: shim drop — 그때 PyPI 발행이 가능해진다.

각 모듈은 script 형태 (각자 `main()`) 이며, `wk <name>` dispatcher 와
`[project.scripts]` 의 `workflow-<name>` 진입점이 여기를 가리킨다.
"""
