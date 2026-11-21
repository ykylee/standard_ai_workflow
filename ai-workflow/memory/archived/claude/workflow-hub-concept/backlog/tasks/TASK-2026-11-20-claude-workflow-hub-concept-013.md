---
carried_over_to: TASK-2026-11-20-claude-workflow-hub-concept-013@main
id: TASK-2026-11-20-claude-workflow-hub-concept-013
status: done
created_at: 2026-11-20
source_anchor: generic-task-2026-11-20-claude-workflow-hub-concept-013
source_path: backlog/2026-11-20.md
kind: generic
wbs: M-031/WBS-31.3
---

# TASK-2026-11-20-claude-workflow-hub-concept-013 — PURPOSE 2.0판 · 1.x 유지보수 정책 — G1 · G3 · §4 명제(D9) 개정안과 1.x 줄 운영 요구

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-20
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `docs/planning/workflow-hub-requirements-2026-11.md`
  - `ai-workflow/memory/active/PURPOSE.md`

- Description: M-031/WBS-31.3. concept §16: PURPOSE G1 · G3 · §4 명제를 2.0판으로(D9 = 2.0 명제, E1 위키 포함), G4 deprecation 에 따른 1.x 유지보수 줄 정책. 산출물: requirements §17 (PURPOSE 개정안 · 1.x 요구) · R14.8. PURPOSE.md 자체는 적용 시점 결정 전까지 고치지 않는다.
- Completion criteria: requirements §17 에 PURPOSE 2.0 개정안과 1.x 유지보수 요구가 있다
- Completion criteria: 2년 보장과의 관계가 명시돼 있다
- Completion criteria: 열린 물음(Q6 등)은 권고안과 함께 §20 에 있다

## 🧭 Plan

- Claims: C1 PURPOSE 2.0 개정안이 바뀌는 칸(G1 · G3 · G4 · Q2 · 범위 · §4 명제)만 지금 문구와 나란히 보인다
- Claims: C2 1.x 유지보수 정책이 판정 가능한 요구(R16)로 있고 stable_guarantee 의 2년 보장(2028-07-20)과 어긋나지 않는다
- Claims: C3 새로 생긴 열린 물음은 권고안과 함께 §20 에 있다
- Files that change: docs/planning/workflow-hub-requirements-2026-11.md
- Order of work: 근거 확인(PURPOSE · stable_guarantee · RELEASE §1 · deprecation spec)
- Order of work: §17 작성
- Order of work: 검사
- Order of work: 커밋 · push
- Plan risks: 2.0 조기 발행이 SemVer 2년 보장(v0.8.0 → 2.0.0, ~2028-07-20)과 부딪칠 수 있다 — 1.x 줄 유지 기간으로 지킨다
- Proof: 개정안 · R16 · Q 행 · R 검증 대조 · --changed

## 🛠️ Implementation / Content

- Progress: `2026-11-20 23:30` 커밋 · push
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: requirements §17.1 PURPOSE 2.0 개정안(G1 · G3 · G4 · Q2 · 범위 · §4 명제 둘째 · 셋째) · §17.2 R16.1~R16.8 1.x 유지보수(결함만 · patch 만 · 2028-07-20 · 안내 판 · 분기 · 소비자 채널 보호 · latest · 결함 후보) · R14.8 연결. PURPOSE.md 는 적용 시점(Q9) 결정 전이라 고치지 않음
- Verification: 근거 대조: PURPOSE v1 원문 · stable_guarantee 2026-07-20~2028-07-20 · deprecation 1 release 경고→제거 · marketplace.json source ./plugin · 발행 코드 main 고정 없음(grep) · R 106 전부 [검증] · 미정의 참조 0 · 추적 43/43 · --changed 108/108 · verifier 생략(검증 간소화 기간)
- Follow-up: 소유자 결정 Q6 · Q9 · Q10
