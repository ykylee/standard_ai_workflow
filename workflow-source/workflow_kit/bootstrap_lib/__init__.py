"""workflow_kit.bootstrap_lib — bootstrap 계층 (v1.1.8+, TASK-2026-08-12-main-007).

v1.1.7 까지는 top-level `bootstrap_lib` (scripts/bootstrap_lib) 였다. 일반명
top-level 은 공개 배포(PyPI) 시 site-packages 충돌을 일으키므로 격상했다
(배포 검토 §2, 1단계 tools 와 같은 처방). 구경로는 1st cycle shim 으로 유지.

진입점: `python -m workflow_kit.bootstrap_lib` (구: `python -m bootstrap_lib`).
"""
