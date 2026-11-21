---
carried_over_to: TASK-2026-11-20-claude-workflow-hub-concept-008@main
id: TASK-2026-11-20-claude-workflow-hub-concept-008
status: done
created_at: 2026-11-20
source_anchor: generic-task-2026-11-20-claude-workflow-hub-concept-008
source_path: backlog/2026-11-20.md
kind: generic
wbs: M-031/WBS-31.1
---

# TASK-2026-11-20-claude-workflow-hub-concept-008 — 2.0 허브 요구 목록 — concept 방향 · 결정을 검증 가능한 R 번호로 (requirements 문서 초판)

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-20
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `docs/planning/workflow-hub-requirements-2026-11.md`
  - `docs/planning/README.md`

- Description: M-031/WBS-31.1. concept(workflow-hub-review-2026-11.md)의 H1~H14 · D1~D11 · E1~E6 · F1~F5 · G1~G3 · I1~I4 를 영역별(API · MCP · 부트스트랩 · 등록 · 콜사인 기억 · 지침 · 위키 · 로드맵 · 세션 시작 · compact · 오프라인 · 노출 · 1.x 전환) 요구로 옮긴다. 실측(WBS-31.2) · PURPOSE 2.0(WBS-31.3)은 자리만.
- Completion criteria: requirements 문서가 있고 H1~H14 · D1~D11 · E1~E6 · F1~F5 · G1~G3 · I1~I4 전부가 추적표에 R 로 대응한다
- Completion criteria: 각 R 에 검증 방법이 있다
- Completion criteria: 열린 물음은 권고안과 함께 소유자 결정 절에 있다

## 🧭 Plan

- Claims: C1 concept 의 방향 · 결정 전부가 하나 이상의 R 에 대응한다 (추적표)
- Claims: C2 각 R 은 판정 가능한 문장(무엇을 · 언제 · 어떻게 거절)이고 검증 방법을 단다
- Claims: C3 1.x 생성물 형식 · stable API 불변을 R0 로 고정한다
- Files that change: docs/planning/workflow-hub-requirements-2026-11.md
- Files that change: docs/planning/README.md
- Order of work: 근거 사실 확인(형식 버전 · 진입 파일 · MCP 표면)
- Order of work: 문서 작성
- Order of work: 추적표 대조
- Order of work: 커밋 · push
- Plan risks: concept 에 없는 요구를 만들어 넣는 범위 확장 — 새로 생긴 물음은 권고안과 함께 소유자 결정 절에만 둔다
- Proof: 추적표에서 H/D/E/F/G/I 항목 누락 0 (스크립트 대조) · doc metadata 검사 green

## 🛠️ Implementation / Content

- Progress: `2026-11-20 22:48` 커밋 · push
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: docs/planning/workflow-hub-requirements-2026-11.md 초판 — R0 불변 7 · R1~R15 · 실측 자리 S1~S3(WBS-31.2) · PURPOSE/1.x 자리(WBS-31.3) · 추적표 · 열린 물음 Q1~Q6(권고안)
- Verification: 추적표 대조 스크립트: concept 항목 43개(H14 · D11 · E6 · F5 · G3 · I4) 누락 0 · 초과 0 · R 95개 전부 [검증] 있음 · 미정의 R 참조 0 · 참조 경로 3개 실재 · 진입 예산 8KB = ENTRY_BUDGET_BYTES 확인 · --changed 108/108 · verifier 생략(검증 간소화 기간)
- Follow-up: WBS-31.2 design 전 실측 S1~S3
- Follow-up: WBS-31.3 PURPOSE 2.0판 · 1.x 유지보수 정책
- Follow-up: 소유자 결정 Q1~Q5
