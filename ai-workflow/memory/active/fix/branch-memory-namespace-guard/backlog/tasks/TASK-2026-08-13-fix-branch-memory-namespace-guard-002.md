---
id: TASK-2026-08-13-fix-branch-memory-namespace-guard-002
status: done
created_at: 2026-08-13
source_anchor: generic-task-2026-08-13-fix-branch-memory-namespace-guard-002
source_path: backlog/2026-08-13.md
kind: generic
---

# TASK-2026-08-13-fix-branch-memory-namespace-guard-002 — mavis attach e2e 기대치 vs read-only 번들 분리 — 13종 기대, 11종 실측

## 📝 Description

- 상태: done
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

- 진행 현황: `2026-08-13 23:08` 기준 check_mavis_attach_e2e 하드코딩 사본이 --bundle 기본값 전환과 갈라짐.
- 다음 세션 시작 포인트:
- 남은 리스크:

## ✅ Outcome

- 작업 결과: 의도는 추측 불필요했다 — v1.2.0 노트가 'read-only 11종만 서빙' 을 명시하고 registry 의 tool_specs_for_bundle 이 정본이다. 13종 하드코딩 사본을 정본 파생으로 교체.
- 검증 결과: check_mavis_attach_e2e green (11 tools), 전량 2축 254/254.
- 후속 작업:
