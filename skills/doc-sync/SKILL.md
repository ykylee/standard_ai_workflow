# Doc-Sync Skill

- 문서 목적: `doc-sync` skill 프로토타입의 역할과 구현 진입점을 정리한다.
- 범위: 목적, 연결 스펙, 예상 입력/출력, 권한 경계, 구현 메모
- 대상 독자: skill 구현자, AI agent 설계자, 운영자
- 상태: prototype
- 최종 수정일: 2026-04-18
- 관련 문서: `../../core/doc_sync_skill_spec.md`, `../../core/workflow_skill_catalog.md`, `../../core/workflow_agent_topology.md`, `../../core/workflow_mcp_candidate_catalog.md`

## 1. 목적

변경 파일 목록을 바탕으로 함께 확인하거나 갱신해야 할 기준 문서, 허브 문서, 상태 문서를 추천한다.

## 2. 연결 스펙

- 상세 스펙: [../../core/doc_sync_skill_spec.md](../../core/doc_sync_skill_spec.md)
- 카탈로그: [../../core/workflow_skill_catalog.md](../../core/workflow_skill_catalog.md)

## 3. 예상 입력

- `project_profile_path`
- `changed_files`
- 선택적으로 `baseline_documents`, `hub_documents`, `session_handoff_path`, `latest_backlog_path`, `change_summary`

## 4. 예상 출력

- `impacted_documents`
- `hub_update_candidates`
- `stale_warnings`
- `reasoning_notes`
- `recommended_review_order`
- `follow_up_actions`

## 5. 권한 경계

- 읽기 전용 추천 단계
- 문서 자동 수정 금지
- 추천은 후보와 경고 중심으로 표현

## 6. 구현 메모

- 변경 파일을 문서/비문서로 분류
- runbook, handoff, backlog, 허브 문서를 서로 다른 후보 그룹으로 다룸
- 허브 stale 가능성과 결과 기록 누락 가능성을 별도 경고로 분리
- `ai-workflow/` 경로는 workflow 메타 레이어로 보고, 프로젝트 문서 탐색 후보에서는 기본적으로 제외한다.

## 7. 프로토타입 실행

- 실행 스크립트: [scripts/run_doc_sync.py](./scripts/run_doc_sync.py)
- 코드 변경 예시:

```bash
python3 skills/doc-sync/scripts/run_doc_sync.py \
  --project-profile-path examples/acme_delivery_platform/project_workflow_profile.md \
  --session-handoff-path examples/acme_delivery_platform/session_handoff.md \
  --work-backlog-index-path examples/acme_delivery_platform/work_backlog.md \
  --latest-backlog-path examples/acme_delivery_platform/backlog/2026-04-18.md \
  --changed-file app/jobs/delivery_sync.py \
  --change-summary "delivery sync 재시도 로직 변경"
```

- 문서 변경 예시:

```bash
python3 skills/doc-sync/scripts/run_doc_sync.py \
  --project-profile-path examples/acme_delivery_platform/project_workflow_profile.md \
  --session-handoff-path examples/acme_delivery_platform/session_handoff.md \
  --work-backlog-index-path examples/acme_delivery_platform/work_backlog.md \
  --latest-backlog-path examples/acme_delivery_platform/backlog/2026-04-18.md \
  --changed-file docs/operations/runbooks/delivery-sync.md
```

- 현재 프로토타입은 추천 결과를 JSON 으로만 출력하고 문서를 직접 수정하지 않는다.

## 8. 현재 상태

- 읽기 전용 추천 프로토타입 있음
- 변경 파일 기준으로 영향 문서, 허브 후보, stale 경고, 후속 행동을 출력할 수 있음
- 프로젝트별 문서 구조는 project profile 을 기준으로 해석함

## 다음에 읽을 문서

- skills 허브: [../README.md](../README.md)
- 상세 스펙: [../../core/doc_sync_skill_spec.md](../../core/doc_sync_skill_spec.md)
