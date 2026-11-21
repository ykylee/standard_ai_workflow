---
id: TASK-2026-11-21-release-1.x-005
status: done
created_at: 2026-11-21
source_anchor: generic-task-2026-11-21-release-1.x-005
source_path: backlog/2026-11-21.md
kind: generic
wbs: exempt
wbs_exempt_reason: main M-038/WBS-38.3 의 1.x 쪽 — 2.0 전환 표식 거절 (R14.6 · R16.5)
---

# TASK-2026-11-21-release-1.x-005 — '허브로 옮김' 표식이 있으면 1.x 쓰기 거절 · session-start 는 허브를 가리킨다 (main 의 M-038 WBS-38.3 1.x 쪽)

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-21
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `workflow-source/workflow_kit/common/hub_marker.py`

- Description: main e58c3221 의 코드 · 검사를 옮긴다(허브 상수 연결 · hub 명령 면제는 main 만). 발행은 1.x 안내 판 때 (main task D1).
- Completion criteria: check_hub_marker_1x 6/6 (허브 상수 대조는 해당 없음), 이 브랜치 --changed green + 스모크

## 🧭 Plan

- Files that change:
- Order of work:
- Plan risks:
- Proof:

## 🛠️ Implementation / Content

- Progress: `2026-11-21 06:11` close
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: main e58c3221 의 common/hub_marker.py · CLI 입구 거절 · session-start 조기 종료 · check_hub_marker_1x 를 옮김. 1.x 에는 hub 명령이 없어 면제 표에서 그 항목만 뺌(각 브랜치가 자기 명령 표와 대조). 발행 안 함 — 1.x 안내 판 때(main task D1)
- Verification: check_hub_marker_1x 6/6 (허브 상수 대조는 해당 없음으로 따로 출력), run_all_checks --changed 312 PASS 0 FAIL(문서 스탬프 · 메모리 lint 2건 수리 뒤) · 스모크 8/8 · 실행 해석기는 main .venv + PYTHONPATH=worktree 소스(import 경로 1.29.1 확인)
- Follow-up:
