---
id: M-054
title: 2.x 전면 Go 전환 — implementation S2-a (순수 판정 judge/1 · 차분 검사)
sdlc_phase: implementation
status: done
order: 54
parallel_allowed:
  - M-007
  - M-028
  - M-039
deliverables:
  - workflow-source/workflow_kit/judgecli.py
  - hub-go/internal/judge/
  - workflow-source/tests/check_judge_parity.py
goals: [G1, G3, G5]
---

# M-054 — S2-a 순수 판정(`judge/1`) · 차분 검사(`check_judge_parity`)

설계 정본: [`hub_go_spec.md`](../../../../workflow-source/core/hub_go_spec.md) §3 · §4 · §5.1 · §5.2 (DG1 · 요구 R27). DB 와 분리된 순수 판정 op 를 Python 정본(`python -m workflow_kit.judgecli`)과 Go 판(`workflow-hub judge`) 양쪽에 구현하고, corpus(fixture + 저장소 실데이터 + 경계 사례) 바이트 차분 검사로 불일치 0 을 검증한다.

## WBS

- **WBS-54.1** `judge/1` CLI 프로토콜(단건 · `--batch` JSON Lines · 오류 코드 2) + `plan.lint` · `plan.states` · `task.status` 두 언어 구현 — 산출물: `workflow-source/workflow_kit/judgecli.py`, `hub-go/internal/judge/plan.go`
- **WBS-54.2** `wbs.gate` · `roadmap.derive` · `handoff.parse` · `state.build` 두 언어 구현 — 산출물: `hub-go/internal/judge/roadmap.go`
- **WBS-54.3** corpus(`hub-go/testdata/corpus/{fixture,edge}/` + 실데이터) · 차분 검사 `check_judge_parity` (양방향 되주입 red) — 산출물: `workflow-source/tests/check_judge_parity.py`
