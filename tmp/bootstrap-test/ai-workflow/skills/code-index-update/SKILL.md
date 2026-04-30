# code-index-update

- 문서 목적: `code-index-update` skill 의 역할, 입력/출력, 실행 예시를 정리한다.
- 범위: 색인 문서 갱신 후보 추천, stale 경고, 허브 문서 우선순위 제안
- 대상 독자: AI agent 설계자, 개발자, 운영자
- 상태: draft
- 최종 수정일: 2026-04-19
- 관련 문서: `../../core/code_index_update_skill_spec.md`, `../../core/workflow_skill_catalog.md`

## 목적

변경 파일과 프로젝트 프로파일을 기준으로 다시 확인해야 할 색인 문서와 허브 문서를 구조화한다.

## 기대 입력

- `project_profile_path`
- `changed_files`

선택 입력:

- `work_backlog_index_path`
- `session_handoff_path`
- `change_summary`

## 기대 출력

- 색인 문서 갱신 후보
- 우선순위가 높은 색인 후보
- stale 가능성 경고
- 추천 근거 메모
- 추천 후속 행동
- 불확실성 메모

## 권한 경계

- 현재 프로토타입은 읽기 전용이다.
- 색인 문서를 직접 수정하지 않는다.
- 새 문서 추가 여부는 입력된 경로 기준으로만 보수적으로 추정한다.

## 구현 메모

- 문서 홈, 운영 허브, backlog index, 루트 README 를 기본 후보군으로 다룬다.
- runbook, report, dataset, prompt 같은 허브성 하위 문서 변경은 상위 허브 재검토 신호로 해석한다.
- 새 Markdown 문서 추가로 보이는 경우 `priority_index_candidates` 와 `missing_index_candidates` 를 함께 사용한다.
- `ai-workflow/` 경로는 workflow 메타 레이어로 보고, 일반 프로젝트 색인/허브 탐색 범위에서는 기본적으로 제외한다.

## 프로토타입 실행

```bash
python3 skills/code-index-update/scripts/run_code_index_update.py \
  --project-profile-path examples/acme_delivery_platform/project_workflow_profile.md \
  --work-backlog-index-path examples/acme_delivery_platform/work_backlog.md \
  --session-handoff-path examples/acme_delivery_platform/session_handoff.md \
  --changed-file app/jobs/delivery_sync.py \
  --changed-file docs/operations/runbooks/delivery-sync.md \
  --change-summary "delivery sync 재시도 로직과 운영 runbook 동시 수정"
```

## 현재 상태

- 읽기 전용 프로토타입이 있다.
- 색인 문서 후보와 허브 stale 경고를 JSON 으로 출력한다.
