---
id: M-004
title: backlog-update 게이트 + 예외 선언
sdlc_phase: implementation
status: done
order: 4
parallel_allowed: []
deliverables:
  - workflow-source/tests/check_roadmap_gates.py
---

# M-004 — backlog-update 게이트 + 예외 선언

스펙 §6 의 게이트 3종(WBS 링크 필수 / SDLC 순서 / done 역행 금지)을
backlog-update 생성 경로의 **단일 함수**로 강제하고, MCP
`create_backlog_entry` 도 같은 함수를 부른다. 예외는 침묵 우회가 아니라
`--wbs exempt --wbs-exempt-reason` 선언이다. breaking 등급은 `RELEASE.md`
§1.5 로 판정한다.

## WBS

- **WBS-4.1** 게이트 판정 단일 함수 + CLI 인자 (--wbs / exempt)
- **WBS-4.2** MCP 경로 동일 함수 배선
- **WBS-4.3** 게이트 검사 + 되주입 red 실증
