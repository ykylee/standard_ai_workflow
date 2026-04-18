# Merge-Doc-Reconcile Skill

- 문서 목적: `merge-doc-reconcile` skill 프로토타입의 역할과 구현 진입점을 정리한다.
- 범위: 목적, 연결 스펙, 예상 입력/출력, 권한 경계, 구현 메모
- 대상 독자: skill 구현자, AI agent 설계자, 운영자
- 상태: prototype
- 최종 수정일: 2026-04-18
- 관련 문서: `../../core/merge_doc_reconcile_skill_spec.md`, `../../core/workflow_skill_catalog.md`, `../../core/workflow_agent_topology.md`

## 1. 목적

병합 이후 handoff, backlog, 허브 문서 사이의 상태 불일치와 재확정 포인트를 구조화해 후속 정리를 돕는다.

## 2. 연결 스펙

- 상세 스펙: [../../core/merge_doc_reconcile_skill_spec.md](../../core/merge_doc_reconcile_skill_spec.md)
- 카탈로그: [../../core/workflow_skill_catalog.md](../../core/workflow_skill_catalog.md)

## 3. 예상 입력

- `project_profile_path`
- `merge_result_summary`
- 조건부로 `session_handoff_path`, `work_backlog_index_path`, `latest_backlog_path`
- 선택적으로 `hub_documents`, `changed_files`, `pre_merge_notes`, `validation_result`

## 4. 예상 출력

- `reconcile_targets`
- `state_conflicts`
- `reconfirmation_points`
- `draft_reconcile_notes`
- `recommended_review_order`
- `warnings`

## 5. 권한 경계

- 읽기 중심 재정리 단계
- 병합 전 상태 자동 합치기 금지
- `done` 확정과 차단 해제 자동 처리 금지

## 6. 구현 메모

- handoff 와 최신 backlog 를 먼저 대조
- 허브/인덱스 문서는 링크와 구조 설명 최신성 중심으로 점검
- 병합 후 검증 미완료 상태는 재확정 포인트로 유지

## 7. 프로토타입 실행

- 실행 스크립트: [scripts/run_merge_doc_reconcile.py](./scripts/run_merge_doc_reconcile.py)
- 예시 실행:

```bash
python3 skills/merge-doc-reconcile/scripts/run_merge_doc_reconcile.py \
  --project-profile-path examples/acme_delivery_platform/project_workflow_profile.md \
  --session-handoff-path examples/acme_delivery_platform/session_handoff.md \
  --work-backlog-index-path examples/acme_delivery_platform/work_backlog.md \
  --latest-backlog-path examples/acme_delivery_platform/backlog/2026-04-18.md \
  --merge-result-summary "runbook 링크와 상태 문서가 함께 수정된 브랜치 병합 후 재정리" \
  --changed-file docs/operations/runbooks/delivery-sync.md \
  --changed-file app/jobs/delivery_sync.py
```

- 현재 프로토타입은 병합 후 재확정 포인트를 JSON 으로 출력하고 문서를 직접 수정하지 않는다.

## 8. 현재 상태

- 읽기 전용 재정리 프로토타입 있음
- handoff, backlog, 허브 문서 재확인 대상과 상태 충돌을 출력할 수 있음
- 병합 후 검증 미완료 상태는 경고로 유지함

## 다음에 읽을 문서

- skills 허브: [../README.md](../README.md)
- 상세 스펙: [../../core/merge_doc_reconcile_skill_spec.md](../../core/merge_doc_reconcile_skill_spec.md)
