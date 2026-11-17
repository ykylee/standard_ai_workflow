---
id: TASK-2026-11-17-claude-remote-sync-check-234c32-006
status: in_progress
created_at: 2026-11-17
source_anchor: release-task-2026-11-17-claude-remote-sync-check-234c32-006
source_path: backlog/2026-11-17.md
kind: release
wbs: M-007/WBS-7.4
---

# TASK-2026-11-17-claude-remote-sync-check-234c32-006 — v1.27.0 발행 — iPad 폼 제출 수리 · 진행 기록 상기 · 한 호스트 여러 워크벤치

## 📝 Description

- Status: in_progress
- Priority: high
- Request date: 2026-11-17
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: 소유자 지시(2026-11-17 '좋아 발행하자'). 이 브랜치 커밋(0c23165f · 1b94a470 · b58c0f28)을 main 에 ff 하고 v1.27.0 minor 발행 + §2.8.
- Completion criteria: [C1] 태그 v1.27.0 = 발행 준비 커밋 = origin/main, 그 sha 의 게이트 통과 기록(native · slash)
- Completion criteria: [C2] GitHub Release v1.27.0 Latest · draft=false · asset 5종, 노트 수치(커밋 · 검사 수 · smoke)가 사실과 같다
- Completion criteria: [C3] §2.8 — doctor --json 의 content_drift.behind=[] · disabled=[]

## 🧭 Plan

- Files that change:
- Order of work: 1 버전 박기 · 노트 → 2 --changed · smoke → 3 커밋 · 게이트 → 4 main ff · push → 5 dist · release --dry-run → 6 release --apply → 7 §2.8 → 8 verifier · 완료 커밋
- Plan risks: release post-step 의 auto-amend · 스탬프 재삽입 — 실행 전 clean tree, 뒤에 diff 확인
- Proof: 게이트 증거 · release --dry-run ready=true · gh release view asset 5 · doctor --json

## 🛠️ Implementation / Content

- Progress: `2026-11-17 06:01` 버전 박기 · 노트 완료 — --changed + smoke
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result:
- Follow-up:
