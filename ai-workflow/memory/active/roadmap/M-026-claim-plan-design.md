---
id: M-026
title: 주장 트리 계획 — design (ADR-031 + core 스펙)
sdlc_phase: design
status: planned
order: 26
parallel_allowed:
  - M-007
deliverables:
  - ai-workflow/wiki/decisions/adr-031-claim-plan.md
  - workflow-source/core/claim_plan_spec.md
goals: [G2, G5]
---

# M-026 — 주장 트리 계획 — design

requirements sign-off ([`M-023`](./M-023-claim-plan-requirements.md) →
[`requirements 문서`](../../../../docs/planning/claim-plan-requirements-2026-11.md) §12, 2026-11-12) 를 받는 design 단계.
**[`M-025`](./M-025-plan-workbench-requirements.md) 뒤에 연다** — 응답 파일을 쓰는 쪽(워크벤치)의 요구 사항이 확정돼야
`plan-import` 와 응답 형식의 설계가 한 번에 선다.

- **ADR-031 결정 대상**: 공용 파서 모듈 배치 · 결정 줄 칸 이름의 쓰기 표기 · 주장별 묶음을 내는 명령(새 명령 또는 기존 명령의
  출력 필드, requirements Q5) · §11.1 문구와 스킬 수 · `open_decisions` 의 state.json 스키마 · `.gitignore` 를 누가 보장하는가
  (`plan_responses/inbox/`) · 검사 구성.
- **먼저 잴 것 (requirements R13)**: 정본 §1 · §11.1 개정 뒤 진입점 블록 크기(8KB 예산) · 다른 하네스의 새 컨텍스트 검증 수단.
- **requirements 검증(9차)이 design 으로 넘긴 것**: "통과한 상태 전이" 가 칸을 고쳐 쓰는 범위(→ blocked · 평범한 update) ·
  지문을 바꾼 뒤 받은편지함에 남는 옛 응답의 처리(자격 없는 파일이 done 을 막는다) · `answered` 의 다른 입력 경로(`--plan-decision` 에
  박힌 상태 · 손 편집)와 질문이 바뀐 뒤의 `answered` · done 인 task 에 대한 `plan-import` · 보관 디렉터리에 직접 놓인 파일의 자격 재검사 ·
  `--discard --apply` 와 칸만 고쳐진 재계산의 Progress 기록.
- **M-025 requirements 가 넘긴 것 (2026-11-13)**: import 는 잠금 아래 한 번에 하나 + 보관 이동은 배타(주장 R8.1 수정 — 워크벤치 §1.2 행 7~11 ·
  R5.5; 비차단 잠금 `common/file_lock.py` 로의 재현 · 잠금 파일 위치 · 배타 판정을 이름이 아니라 번호로 할지는 미정) · 응답 파일의
  `received_at` 은 소수 초 · 줄바꿈은 쓰는 쪽이 LF 로 고친다 · design 을 워크벤치와 한 ADR 묶음으로 낼지 (워크벤치 R12-③).
- **불변**: requirements R0.

## WBS

- **WBS-26.1** design 확정 — ADR-031 + core 스펙 — 산출물: `ai-workflow/wiki/decisions/adr-031-claim-plan.md`,
  `workflow-source/core/claim_plan_spec.md`
