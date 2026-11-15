---
merged_from: claude/remote-sync-check-234c32@7fdf0eb5
id: TASK-2026-11-15-claude-remote-sync-check-234c32-002
status: in_progress
created_at: 2026-11-15
source_anchor: release-task-2026-11-15-claude-remote-sync-check-234c32-002
source_path: backlog/2026-11-15.md
kind: release
wbs: M-007/WBS-7.1
---

# TASK-2026-11-15-claude-remote-sync-check-234c32-002 — v1.23.0 발행 — main 합류 · 발행 준비 · 태그 · GitHub Release

## 📝 Description

- Status: in_progress
- Priority: high
- Request date: 2026-11-15
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `workflow-source/releases/Beta-v1.23.0.md`
  - `docs/RELEASE.md`

- Description: v1.22.0..HEAD 49커밋(feat 5 · fix 18, breaking 0)을 minor 1.23.0 으로. 준비 커밋 → 전량 게이트 → push → main 합류 → release --apply(소유자 승인) → §2.8 채널 재적용.
- Completion criteria: version 1.23.0 이 pyproject · __init__ · plugin manifest · marketplace · README · docs 리터럴에 일치 (check_drift_prevention · 버전 검사 green)
- Completion criteria: 발행 준비 커밋 HEAD 에서 --branch-context=all 전량 게이트 rc 0 · 게이트 증거 파일 존재
- Completion criteria: origin/main 이 발행 준비 커밋을 포함한다
- Completion criteria: 태그 v1.23.0 과 GitHub Release(asset 포함)가 있다 — 소유자 승인 뒤 release --apply

## 🧭 Plan

- Claims: C1 등급은 minor — 공개 API 시그니처 변경 0 · 진입점 제거 0 · 추가만 (RELEASE §1.5)
- Claims: C2 태그 push · GitHub Release 는 외부 공개라 소유자 승인 뒤에만 실행한다
- Decisions: D1 [C2] release --apply(태그 v1.23.0 push · GitHub Release 생성)를 실행하는가? | default: hold | options: apply = 게이트 통과 커밋에 태그를 달고 Release 를 만든다; hold = main 합류까지만 하고 발행은 미룬다 | state: proposed
- Files that change: workflow-source/releases/Beta-v1.23.0.md
- Order of work: 1) 준비 커밋 2) 전량 게이트 3) branch push 4) main 합류 push 5) dist --apply · release --dry-run 6) D1=apply 면 release --apply · §2.8
- Plan risks: release --apply 의 post-step 산출물은 미커밋으로 남는다 — 별도 '발행 완료' 커밋
- Proof: 게이트 증거 · git log origin/main · gh release view v1.23.0

## 🛠️ Implementation / Content

- Progress: 게이트 2회차(0ce020df) slash 에서 check_plan_import 240s 시간 초과 — 실측 172~235s, 호스트에 다른 프로젝트 부하. CHECK_TIMEOUT_S 240 → 480. 같은 게이트에서 check_plan_gate 168s(이전 상한 150 이면 실패)
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result:
- Follow-up:
