---
id: TASK-2026-11-21-release-1.x-007
status: done
created_at: 2026-11-21
source_anchor: generic-task-2026-11-21-release-1.x-007
source_path: backlog/2026-11-21.md
kind: generic
wbs: exempt
wbs_exempt_reason: 1.x 유지보수 줄 — 로드맵은 main 에 있다 (M-038 WBS-38.3 의 1.x 몫)
---

# TASK-2026-11-21-release-1.x-007 — 1.x 안내 판 1.30.0 — session-start 2.0 안내 한 줄 · EOL 한 줄 · README · 채널 재등록 (R16.4 · R14.8 · R16.3 · R16.6)

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-21
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: main TASK-2026-11-21-main-011 의 1.x 쪽 몫. 2.0.0-beta 와 같은 때 발행
- Completion criteria: session-start 성공 출력 summary 끝에 안내 1줄 · 2028-07-20 이후 EOL 1줄 · 종료 코드 불변 (날짜 주입 fixture)
- Completion criteria: README 에 2.0 · 전환 경로 · EOL · 하네스별 채널 재등록 명령(Claude Code 실측)

## 🧭 Plan

- Files that change:
- Order of work:
- Plan risks:
- Proof:

## 🛠️ Implementation / Content

- Progress: `2026-11-21 13:54` 발행 준비 커밋 — 1.30.0 (대상 줄만 고침) · 노트 Beta-v1.30.0.md · --changed 통과 — 다음: 전량 게이트 → 소유자 확인 → release --apply
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: v1.30.0 발행 — 태그 24ca6ae3 · GitHub Release (wheel · sdist · 플러그인 zip 3, 발행 시점 Latest — 이어 v2.0.0 이 가져감). 안내 한 줄(EOL 전 2.0 · 뒤 EOL) · README §0 · 표식 거절 · 발행 도구 latest 판정 이식. 2.0 대응: 안내 · README 는 해당 없음(1.x 전용), 나머지는 main 에도 있음.
- Verification: 전량 게이트 --branch-context=all native 336/336 · slash 336/336 rc 0 (24ca6ae3 통과 기록) · check_transition_notice 3/3 · 되주입 4/4 · release dry-run ready
- Follow-up:
