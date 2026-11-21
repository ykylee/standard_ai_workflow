---
id: TASK-2026-11-21-release-1.x-008
status: done
created_at: 2026-11-21
source_anchor: generic-task-2026-11-21-release-1.x-008
source_path: backlog/2026-11-21.md
kind: generic
wbs: exempt
wbs_exempt_reason: 발행 도구 결함 수리 — 마일스톤 밖
---

# TASK-2026-11-21-release-1.x-008 — 발행 산출물 선택이 접두사 glob — find_dist_files 정확한 파일명 대조 (main TASK-2026-11-21-main-027 이식)

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-21
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: find_dist_files 의 {name}-{판}* 접두사 glob 이 다른 판(1.3.0 → 1.3.0b1 · 1.3.01) 산출물까지 잡는다. 파일명 판 칸 정확 대조로 바꾸고 check_release_prerelease_latest case 7 추가
- Completion criteria: find_dist_files 가 정확한 판의 wheel · sdist 만 고른다 · case 7 + 되주입

## 🧭 Plan

- Files that change:
- Order of work:
- Plan risks:
- Proof:

## 🛠️ Implementation / Content

- Progress: `2026-11-21 23:46` done
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: case 7 PASS (1.x 코드로 import 확인) · --changed rc 0 FAIL 0 · smoke 8/8 · 되주입은 main 에서 같은 코드로 FAIL 확인
- Verification: case 7 PASS (1.x 코드로 import 확인) · --changed rc 0 FAIL 0 · smoke 8/8 · 되주입은 main 에서 같은 코드로 FAIL 확인
- Follow-up:
