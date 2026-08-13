---
id: TASK-2026-08-13-fix-branch-memory-namespace-guard-001
status: done
created_at: 2026-08-13
source_anchor: generic-task-2026-08-13-fix-branch-memory-namespace-guard-001
source_path: backlog/2026-08-13.md
kind: generic
---

# TASK-2026-08-13-fix-branch-memory-namespace-guard-001 — 브랜치 메모리 네임스페이스 가드 — 손 편집을 직접 지목하는 검사 신설

## 📝 Description

- 상태: done
- 요청일: 2026-08-13
- 담당: AI Agent
- 작업 내용: PR #23 세션 기록 §7 의 남은 구멍 — 작업 브랜치 메모리 네임스페이스 가드
- 범위 밖: 검사 실행 시간 최적화 (별건)
- 완료 기준: (작성 필요 — 검증 방법을 구체적으로 적는다)

## 🛠️ Implementation / Content

- 진행 현황: `2026-08-13 22:53` 기준 PR #23 세션 기록 §7 의 남은 구멍.

## ✅ Outcome

- 작업 결과: check_branch_memory_namespace 신설 (8 cases, A: 남의 네임스페이스 추가/수정 · B: 자기 디렉터리 부재). 정본 창구 정정 — seed-workspace-memory 가 한 벌 생성, backlog-update 만 쓰면 절반짜리. 부수 수리 2건: check_release_pipeline_phase2 acceptable 목록 / check_mavis_attach_e2e 하드코딩 사본 → 정본 registry 파생.
- 검증 결과: 전량 2축 254/254 ×2 green + CI env 축 254/254 + mypy strict 193 files 0 + SDK 매트릭스 3/3. 되주입: fixture 재현 + 살아있는 저장소에 오염 파일 심어 커밋 전 FAIL 확인.
- 후속 작업:
