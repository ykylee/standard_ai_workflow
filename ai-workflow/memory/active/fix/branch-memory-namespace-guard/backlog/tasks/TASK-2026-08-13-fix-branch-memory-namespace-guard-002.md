---
id: TASK-2026-08-13-fix-branch-memory-namespace-guard-002
status: planned
created_at: 2026-08-13
source_anchor: generic-task-2026-08-13-fix-branch-memory-namespace-guard-002
source_path: backlog/2026-08-13.md
kind: generic
---

# TASK-2026-08-13-fix-branch-memory-namespace-guard-002 — mavis attach e2e 기대치 vs read-only 번들 분리 — 13종 기대, 11종 실측

## 📝 Description

- 상태: planned
- 우선순위: high
- 요청일: 2026-08-13
- 담당:
- 호스트명:
- 호스트 IP:
- 영향 문서:
  - 

- 작업 내용: check_mavis_attach_e2e 가 read-only 번들에 13종을 기대하는데 실측 11종. 빠진 둘은 write 도구(apply_robust_patch/rotate_workflow_logs)로, v1.2.0 의 --bundle 기본값 all→read-only 전환과 어긋난다. 기대치를 11 로 낮출지 검사를 --bundle all 로 붙일지는 의도 판정. 깨끗한 트리에서 재현 확인 (2026-08-13).
- 완료 기준:

## 🛠️ Implementation / Content

- 진행 현황: `2026-08-13 22:39` 기준 check_mavis_attach_e2e 가 read-only 번들에 13종을 기대하는데 실측 11종. 빠진 둘은 write 도구(apply_robust_patch/rotate_workflow_logs)로, v1.2.0 의 --bundle 기본값 all→read-only 전환과 어긋난다. 기대치를 11 로 낮출지 검사를 --bundle all 로 붙일지는 의도 판정. 깨끗한 트리에서 재현 확인 (2026-08-13).
- 다음 세션 시작 포인트:
- 남은 리스크:

## ✅ Outcome

- 작업 결과:
- 후속 작업:
