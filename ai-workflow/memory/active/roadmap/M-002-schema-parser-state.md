---
id: M-002
title: 스키마·파서·상태 생성기·검사·씨앗
sdlc_phase: implementation
status: done
order: 2
parallel_allowed: []
deliverables:
  - workflow-source/workflow_kit/common/schemas/roadmap.py
  - workflow-source/workflow_kit/common/state/roadmap.py
  - workflow-source/tests/check_roadmap_format.py
  - workflow-source/tests/check_roadmap_integrity.py
  - workflow-source/tests/check_roadmap_state_generated.py
---

# M-002 — 스키마·파서·상태 생성기·검사·씨앗

로드맵 층의 기계 기반: Pydantic 정본 스키마, roadmap/ 디렉터리 파서,
task `wbs:` 링크 수집, 진척 파생 롤업(스펙 §7.2), `roadmap_state.json`
생성기, 검사 3종, 그리고 이 roadmap/ 자체(자기 적용 씨앗).

> WBS 는 처음 세 leaf(스키마·검사·씨앗)로 갈랐다가 **한 leaf 로 합쳤다** —
> 실제 작업이 task 하나(main-003)로 완결됐고, task↔WBS 는 일대일이라(스펙 §11)
> 연결 없는 leaf 는 planned 로 파생돼 끝난 일이 안 끝난 것으로 보인다.
> WBS granularity 는 task granularity 를 따른다.

## WBS

- **WBS-2.1** Pydantic 스키마 + 파서 + 파생 롤업 + 생성기 + 검사 3종 + 자기 적용 씨앗
