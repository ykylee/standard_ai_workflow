# End-to-End Skill Demo

- 문서 목적: 1차 핵심 skill 4종이 예시 프로젝트 문서를 기준으로 어떻게 이어지는지 end-to-end 데모 흐름으로 설명한다.
- 범위: `session-start`, `backlog-update`, `doc-sync`, `merge-doc-reconcile` 실행 순서와 기대 결과
- 대상 독자: 개발자, 운영자, AI agent 설계자, 프로젝트 온보딩 담당자
- 상태: draft
- 최종 수정일: 2026-04-18
- 관련 문서: `./README.md`, `./acme_delivery_platform/project_workflow_profile.md`, `../skills/session-start/SKILL.md`, `../skills/backlog-update/SKILL.md`, `../skills/doc-sync/SKILL.md`, `../skills/merge-doc-reconcile/SKILL.md`

## 1. 목적

이 문서는 예시 프로젝트 `acme_delivery_platform` 을 기준으로 1차 핵심 skill 4종이 실제로 어떤 순서로 이어지는지 보여준다.

현재 프로토타입은 모두 읽기 전용 또는 JSON 초안 생성 단계이며, 실제 문서를 직접 수정하지 않는다. 대신 각 단계에서 무엇을 읽고 어떤 결과를 내는지 빠르게 검증할 수 있다.

통합 실행 스크립트도 제공한다:

- [../scripts/run_demo_workflow.py](../scripts/run_demo_workflow.py)

## 2. 준비 문서

데모에서 사용하는 예시 문서:

- [acme_delivery_platform/project_workflow_profile.md](./acme_delivery_platform/project_workflow_profile.md)
- [acme_delivery_platform/session_handoff.md](./acme_delivery_platform/session_handoff.md)
- [acme_delivery_platform/work_backlog.md](./acme_delivery_platform/work_backlog.md)
- [acme_delivery_platform/backlog/2026-04-18.md](./acme_delivery_platform/backlog/2026-04-18.md)

데모에서 사용하는 프로토타입:

- [../skills/session-start/scripts/run_session_start.py](../skills/session-start/scripts/run_session_start.py)
- [../skills/backlog-update/scripts/run_backlog_update.py](../skills/backlog-update/scripts/run_backlog_update.py)
- [../skills/doc-sync/scripts/run_doc_sync.py](../skills/doc-sync/scripts/run_doc_sync.py)
- [../skills/merge-doc-reconcile/scripts/run_merge_doc_reconcile.py](../skills/merge-doc-reconcile/scripts/run_merge_doc_reconcile.py)

## 3. Step 1: Session Start

세션 시작 시점에 현재 기준선을 복원한다.

```bash
python3 skills/session-start/scripts/run_session_start.py \
  --session-handoff-path examples/acme_delivery_platform/session_handoff.md \
  --work-backlog-index-path examples/acme_delivery_platform/work_backlog.md \
  --project-profile-path examples/acme_delivery_platform/project_workflow_profile.md
```

기대 결과:

- 현재 기준선 요약 출력
- 진행 중 작업과 차단 작업 목록 출력
- 최신 backlog 경로 식별
- 다음에 읽을 문서 경로 추천
- handoff 와 backlog 불일치 시 경고 출력

## 4. Step 2: Backlog Update

세션에서 수행할 작업을 날짜별 backlog 초안으로 만든다.

기존 항목 갱신 예시:

```bash
python3 skills/backlog-update/scripts/run_backlog_update.py \
  --project-profile-path examples/acme_delivery_platform/project_workflow_profile.md \
  --daily-backlog-path examples/acme_delivery_platform/backlog/2026-04-18.md \
  --mode update \
  --task-id TASK-021 \
  --task-name "배송 상태 동기화 실패 대응 절차 문서 정리" \
  --task-brief "runbook 및 handoff 반영 상태를 점검했다." \
  --status in_progress
```

신규 항목 생성 예시:

```bash
python3 skills/backlog-update/scripts/run_backlog_update.py \
  --project-profile-path examples/acme_delivery_platform/project_workflow_profile.md \
  --target-date 2026-04-19 \
  --mode create \
  --task-name "운영 허브 링크 무결성 재점검" \
  --task-brief "새 runbook 링크 반영 여부를 확인한다."
```

기대 결과:

- 신규/갱신 여부에 맞는 `operation_type` 출력
- 날짜별 backlog 대상 경로 계산
- 작업 항목 `draft_entry` JSON 초안 생성
- `done` 상태 오판 방지 경고 출력
- 사람이 직접 채워야 할 `fields_requiring_confirmation` 분리

## 5. Step 3: Doc Sync

변경 파일을 기준으로 어떤 문서를 함께 봐야 하는지 추천한다.

코드 변경 예시:

```bash
python3 skills/doc-sync/scripts/run_doc_sync.py \
  --project-profile-path examples/acme_delivery_platform/project_workflow_profile.md \
  --session-handoff-path examples/acme_delivery_platform/session_handoff.md \
  --work-backlog-index-path examples/acme_delivery_platform/work_backlog.md \
  --latest-backlog-path examples/acme_delivery_platform/backlog/2026-04-18.md \
  --changed-file app/jobs/delivery_sync.py \
  --change-summary "delivery sync 재시도 로직 변경"
```

문서 변경 예시:

```bash
python3 skills/doc-sync/scripts/run_doc_sync.py \
  --project-profile-path examples/acme_delivery_platform/project_workflow_profile.md \
  --session-handoff-path examples/acme_delivery_platform/session_handoff.md \
  --work-backlog-index-path examples/acme_delivery_platform/work_backlog.md \
  --latest-backlog-path examples/acme_delivery_platform/backlog/2026-04-18.md \
  --changed-file docs/operations/runbooks/delivery-sync.md
```

기대 결과:

- 영향 문서 후보 추천
- 허브 또는 인덱스 문서 재확인 후보 추천
- stale 가능성 경고 출력
- 후속 검토 순서와 행동 제안 출력

## 6. Step 4: Merge Doc Reconcile

병합 이후 상태 문서와 허브 문서의 재확정 포인트를 정리한다.

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

기대 결과:

- 병합 후 재확인 대상 문서 목록 출력
- handoff 와 backlog 간 상태 충돌 목록 출력
- 재확정 포인트와 재정리 메모 초안 출력
- 병합 후 검증 미완료 상태 경고 출력

## 7. 추천 읽기 순서

이 저장소를 처음 보는 사람에게는 아래 순서를 권장한다.

1. [../README.md](../README.md)
2. [./README.md](./README.md)
3. [acme_delivery_platform/project_workflow_profile.md](./acme_delivery_platform/project_workflow_profile.md)
4. [acme_delivery_platform/session_handoff.md](./acme_delivery_platform/session_handoff.md)
5. 이 문서의 4개 프로토타입 명령 실행

한 번에 흐름을 실행해보려면 아래 명령도 사용할 수 있다.

```bash
python3 scripts/run_demo_workflow.py
```

## 8. 현재 한계

- 예시 프로젝트 문서 구조는 단순화된 가상 사례다.
- 프로토타입은 JSON 추천과 초안 생성 단계까지이며 문서를 직접 수정하지 않는다.
- 허브 문서 후보는 실제 프로젝트 문서 구조에 따라 더 정교한 규칙이 필요할 수 있다.

## 다음에 읽을 문서

- examples 허브: [./README.md](./README.md)
- skills 허브: [../skills/README.md](../skills/README.md)
