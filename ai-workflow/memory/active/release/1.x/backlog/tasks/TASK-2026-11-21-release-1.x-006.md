---
id: TASK-2026-11-21-release-1.x-006
status: done
created_at: 2026-11-21
source_anchor: generic-task-2026-11-21-release-1.x-006
source_path: backlog/2026-11-21.md
kind: generic
wbs: exempt
wbs_exempt_reason: 1.x 결함 수리 (R16.1)
---

# TASK-2026-11-21-release-1.x-006 — run_all_checks 잠금 파일 보유자 정보가 깨진다 — a+b 모드 (main 의 같은 수리를 1.x 로)

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-21
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: RunnerLock.acquire 가 a+b 로 열어 seek 후 덮어쓰기가 끝에 붙고 truncate 가 옛 내용 앞부분을 남겼다 → O_RDWR|O_CREAT + r+b. main 9eb3805b 이전 커밋 a6a442fa 의 같은 수리.
- Completion criteria: check_run_all_checks_lock 5/5 (더 긴 옛 보유자 정보 선행 조건), 이 브랜치 --changed green

## 🧭 Plan

- Files that change:
- Order of work:
- Plan risks:
- Proof:

## 🛠️ Implementation / Content

- Progress: `2026-11-21 10:35` 기준 RunnerLock.acquire 가 a+b 로 열어 seek 후 덮어쓰기가 끝에 붙고 truncate 가 옛 내용 앞부분을 남겼다 → O_RDWR|O_CREAT + r+b. main 9eb3805b 이전 커밋 a6a442fa 의 같은 수리.
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: check_run_all_checks_lock 5/5 (main 에서 되주입 red 확인한 같은 검사)
- Follow-up:
