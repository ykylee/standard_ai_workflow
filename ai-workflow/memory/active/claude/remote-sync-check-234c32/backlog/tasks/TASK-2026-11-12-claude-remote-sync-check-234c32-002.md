---
id: TASK-2026-11-12-claude-remote-sync-check-234c32-002
status: done
created_at: 2026-11-12
source_anchor: generic-task-2026-11-12-claude-remote-sync-check-234c32-002
source_path: backlog/2026-11-12.md
kind: generic
wbs: M-022/WBS-22.1
---

# TASK-2026-11-12-claude-remote-sync-check-234c32-002 — html-plan 개념 흡수 concept 검토 — task Plan 주장·결정 계약(A) + 검토 브리지(B) 설계 초안

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-12
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `docs/planning/html-plan-absorption-review-2026-11.md`
  - `ai-workflow/memory/active/roadmap/M-022-claim-plan.md`

- Description: Anthropic 커뮤니티 html-plan(v1.0.0) 의 주장 트리 · 결정 배치 · 응답 왕복 개념을 task 파일 Plan 계약(A)과 plan-export/plan-import 브리지(B)로 흡수하는 설계 초안과 소유자 선택지를 concept 문서로 낸다
- Completion criteria: concept 문서가 html-plan 실측(구성 · 규칙 · pack 린트 · Respond 형식)을 원문 위치와 함께 적는다
- Completion criteria: A 안: 새 Plan 필드 · 라벨 · 별칭 · 린트 규칙 · 게이트 강도 · 기존 task 파일 호환이 판단 가능하게 적혀 있다
- Completion criteria: B 안: plan-export 매핑표 · plan-import 파싱 · 실패 시 닫힘 · 응답=데이터 규칙 · 형식 결합 위험이 적혀 있다
- Completion criteria: 소유자 선택지 2~5개가 기본값과 함께 있다; 문서 메타 · 링크 검사 통과; roadmap_state 재생성 issues 0

## 🧭 Plan

- Files that change: docs/planning/html-plan-absorption-review-2026-11.md
- Files that change: ai-workflow/memory/active/roadmap/M-022-claim-plan.md
- Files that change: ai-workflow/memory/active/roadmap/index.md
- Files that change: ai-workflow/memory/active/claude/remote-sync-check-234c32/** (task · backlog · handoff · state.json)
- Order of work: html-plan 구성 · 런타임 Respond 형식 실측 → 현 Plan 파서 · 게이트 · verifier 대조
- Order of work: concept 문서 작성 (실측 · A · B · 선택지) → 문서 검사 → refresh-state
- Plan risks: 외부 형식(html-plan 1.0.0) 결합 — Respond 는 id 없이 위치 번호로만 결정을 식별한다
- Plan risks: Plan 라벨 추가는 파싱 계약 변경 — 옛 리더가 새 라벨을 모르는 순서 문제
- Proof: check_docs (메타 · 링크 — check_doc_metadata/check_doc_links 라는 이름의 검사는 없다), refresh-state 뒤 roadmap_state issues, verifier

## 🛠️ Implementation / Content

- Progress: 2026-11-12 concept 종결 — 소유자 결정 = §7 기본값 D1~D5 전부 (문서 §10). M-023 requirements 선언(planned). verifier 4/4 PASS, 지적 오차 3건(task 파일 수 561 · 560–605행 · pack 채움 범위) 수정
- Next session starting point: M-023 requirements — concept §8 미실측(pack.mjs 격리 실측 · 옛 리더의 새 라벨 처리 · 주장 길이 예산 · 응답 상한) 먼저
- Remaining risks:

## ✅ Outcome

- Result: concept 문서 docs/planning/html-plan-absorption-review-2026-11.md 종결 — html-plan 1.0.0 실측 · 안 A(Claims/Decisions 필드 · 린트 L1~L8 · done 게이트 · verifier 묶음) · 안 B(plan-export/plan-import · 3중 대조 · 닫힘) · 소유자 결정 D1~D5 기본값 확정. M-022 done, M-023 [requirements] planned
- Verification: verifier(새 컨텍스트) 4/4 PASS — 원문 대조(htmlplan.js 590·1190행, SKILL.md, pack.mjs 44·48·52–56행) · check_docs.check_metadata/check_links 직접 적용 3문서 0건 · roadmap issues [] · check_roadmap_* 6종 PASS. 무관 실패: check_memory_lint T1d (seed 결함, 별도 브랜치 claude/objective-shamir-ffa258 에서 수리)
- Follow-up: check_docs 가 .claude/worktrees 아래 worktree 에서 IGNORED_PARTS 를 절대경로로 대조해 0개 문서를 검사하고 통과한다 (check_docs.py:155) — 별도 task
