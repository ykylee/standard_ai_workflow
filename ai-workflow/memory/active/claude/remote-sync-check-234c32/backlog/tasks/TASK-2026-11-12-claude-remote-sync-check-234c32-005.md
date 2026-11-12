---
id: TASK-2026-11-12-claude-remote-sync-check-234c32-005
status: done
created_at: 2026-11-12
source_anchor: generic-task-2026-11-12-claude-remote-sync-check-234c32-005
source_path: backlog/2026-11-12.md
kind: generic
wbs: M-023/WBS-23.1
---

# TASK-2026-11-12-claude-remote-sync-check-234c32-005 — 주장 트리 계획 requirements — 미실측 3건 실측 + A · B 요구 사항 · 숫자 · design 진입 조건 확정

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-12
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `docs/planning/claim-plan-requirements-2026-11.md`
  - `ai-workflow/memory/active/roadmap/M-023-claim-plan-requirements.md`
  - `docs/planning/html-plan-absorption-review-2026-11.md`
  - `docs/planning/plan-workbench-review-2026-11.md`
  - `ai-workflow/memory/active/roadmap/M-026-claim-plan-design.md`

- Description: M-022 concept(§10 결정 D1~D5 · §11 하네스 중립 정정)을 받아 requirements 문서를 낸다. 먼저 옛 리더의 미지 라벨 줄 처리 · 주장 길이 예산 · 응답 크기 상한을 재고, 그 숫자로 필드 문법 · 린트 강도 · 게이트 문구 · verifier 묶음 · 응답 형식 · import 대조 · 닫힘 조건 · 보관 경로 · state.json 반영 · design 진입 조건을 확정한다
- Completion criteria: 옛 리더(현 HEAD 의 task 파서 · state 생성기)가 모르는 '- Claims:' · '- Decisions:' 줄을 만났을 때의 동작이 명령과 결과로 적혀 있고, 리더 · 라이터 릴리스 순서가 그 결과에서 정해진다
- Completion criteria: 주장 길이 예산이 이 저장소 task 완료 기준 길이 분포 실측(표본 수 · 분위수)에서 나온 숫자로 확정돼 있다
- Completion criteria: 응답 크기 상한이 근거(응답 구성 요소별 최대 크기 계산 또는 실측)와 함께 확정돼 있다
- Completion criteria: M-023 의 '확정할 것' 10항목(필드 문법 · 린트 L1~L8 강도 · 게이트 문구 · verifier 묶음 형식 · 응답 형식 · import 대조 · 닫힘 조건 · 응답 보관 경로 · state.json 반영 여부 · design 진입 조건)이 각각 식별자 붙은 요구 사항으로 있고 D1~D5 · concept §11 · 워크벤치 W1~W7 과 어긋나지 않는다
- Completion criteria: check_docs 통과; roadmap issues 0; M-023 deliverables_missing 이 빈다

## 🧭 Plan

- Files that change: docs/planning/claim-plan-requirements-2026-11.md
- Files that change: ai-workflow/memory/active/roadmap/M-023-claim-plan-requirements.md
- Files that change: ai-workflow/memory/active/claude/remote-sync-check-234c32/** (task · backlog · handoff · state.json)
- Files that change: ai-workflow/memory/active/roadmap/index.md
- Files that change: ai-workflow/memory/active/roadmap/roadmap_state.json (생성물)
- Files that change: ai-workflow/memory/active/roadmap/M-026-claim-plan-design.md (신규 — design 마일스톤 선언)
- Files that change: docs/planning/html-plan-absorption-review-2026-11.md (D1 에 Q4 갱신 주석 1줄)
- Files that change: docs/planning/plan-workbench-review-2026-11.md (§3 그림 받은편지함 표기 — Q1)
- Order of work: 실측 3건(옛 리더 · 완료 기준 길이 분포 · 응답 크기) → 결과를 문서 §2 에
- Order of work: 요구 사항 A(필드 · 린트 · 게이트 · verifier) · B(응답 형식 · import · 닫힘 · 보관) · design 진입 조건 작성 → check_docs → refresh-state → verifier
- Plan risks: 실측 스크립트가 저장소를 쓰면 안 된다 — 읽기 전용 + scratchpad 사본에서만
- Plan risks: B 응답 형식은 M-025(워크벤치)와 경계가 겹친다 — 형식 계약만 여기서, 서버 동작은 M-025 로
- Proof: 실측 명령 재실행으로 같은 숫자, check_docs, roadmap_state issues, verifier

## 🛠️ Implementation / Content

- Progress: 2026-11-12 종결 — requirements 문서 sign-off Q1~Q7 권고안(§12). verifier 9회: 기준 1 · 2 · 3 · 5 는 3차부터 PASS, 기준 4 는 R6.3(응답 → 결정 상태)에서 2~8차 매회 1건 FAIL → 수리, 9차 다섯 기준 전부 PASS. M-023 done · M-026 [design] planned
- Next session starting point: M-025 (워크벤치 requirements) → 그 뒤 M-026 design. M-026 파일에 9차 검증이 design 으로 넘긴 미정 사항 목록
- Remaining risks:

## ✅ Outcome

- Result: docs/planning/claim-plan-requirements-2026-11.md — 실측 3건(옛 리더는 새 라벨 줄을 무시 · 보존 → 리더 · 라이터 같은 릴리스 / 주장 80자 / 응답 64KiB) + R0~R13. 결정 상태는 보관 응답 집합 + answered 기록의 함수(순서 무관 · 멱등), 다른 approver 의 반대는 disputed 로 결정을 다시 연다, 게이트는 칸이 아니라 계산값으로 판정
- Verification: verifier 9차(새 컨텍스트) 5/5 PASS — §1.2 전수 재계수 일치(563 · 403 · 774 · p75 75 · ≤80 78.6%), R6.3 을 상태 기계로 모델링해 19 시나리오 × 2 해석 전수 탐색(끝 상태 1종 · 멱등 · done 판정 순서 무관 · 부분 채택 0, 되주입 3건 red), 소유자 결정 어긋남 0, 10항목 누락 0, check_docs 78 PASS, roadmap issues []
- Follow-up:
