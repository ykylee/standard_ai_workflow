# 세션 인계 문서

- 문서 목적: 새 세션이나 새 환경에서 이전 작업 상태를 빠르게 복원할 수 있도록 현재 기준 상태를 요약한다.
- 범위: 진행 중 작업, 차단 작업, 최근 완료 작업, 잔여 작업, 환경별 검증 현황
- 대상 독자: 개발자, 운영자, 리뷰어, 문서 작성자
- 상태: draft
- 최종 수정일: 2026-04-24
- 관련 문서: `./project_workflow_profile.md`, `./work_backlog.md`, `./backlog/2026-04-24.md`

## 1. 현재 작업 요약

- 현재 기준선:
- ai-workflow scaffold 와 Codex 진입점 `AGENTS.md` 를 이 저장소에 실제 배포했고, self-dogfood 기준으로 workflow 경계를 검증하는 중이다.
- 현재 주 작업 축:
- workflow state docs 와 실제 project docs 경계를 이 저장소 운영 방식에 맞게 고정하고, Codex 흐름에서 실제로 동작하는지 검증하는 작업
- 최근 핵심 기준 문서:
- `ai-workflow/project/project_workflow_profile.md`, `core/workflow_state_vs_project_docs.md`

## 1.1 기록 원칙

- 이 문서는 다음 세션이 바로 이어받는 데 필요한 핵심 사실만 간결하게 남긴다.
- 사용자에게 직접 보여지는 요약과 작업 보고는 한국어를 기본으로 한다.
- 코드, 명령어, 파일 경로, 설정 key 는 필요한 경우 원문 그대로 유지한다.
- 내부 탐색 메모나 장문의 reasoning 기록은 남기지 않고, 결정과 검증 결과 중심으로 정리한다.

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
- TASK-001 이 저장소에 Codex workflow 배포 및 self-dogfood 검증
## 3. 차단 작업

- 현재 `blocked` 작업:
- 
- 
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- 기존 저장소 구조 자동 스캔 완료
- ai-workflow bootstrap 과 Codex overlay 초안 생성 완료
- OpenCode 로컬 LLM edit 실패 회피 규칙을 worker prompt, harness 문서, agent topology 에 반영 완료
## 5. 잔여 작업 우선순위

### 우선순위 1

- profile 문서의 명령과 문서 경계를 실제 저장소 기준으로 확정
- 오늘 날짜 workflow backlog 에 실제 진행 작업과 검증 결과를 반영

### 우선순위 2

- 실제 OpenCode 적용 저장소에서 edit 실패 로그가 쌓이면 read-before-edit, small hunk, whitespace/line ending 정규화 규칙을 더 구체적인 taxonomy 로 정리
- 필요하면 실제 project docs 와 workflow state docs 의 동기화 규칙을 더 세분화

## 6. 환경별 검증 현황

- 검증 완료 호스트:
- `local / 127.0.0.1`
- 주요 제약:
- 루트 `.codex` 는 원래 빈 파일이었고, 현재는 `.codex.pre_workflow_2026-04-24` 로 보존했다. 전역 Codex 설정 병합은 별도 판단이 필요하다.
- 기존 `.codex` 파일과 Codex 설정 디렉터리 충돌 이력이 있어 전역 설정 병합은 수동 검토 후 진행해야 한다.

## 현재 세션 운영 메모

- workflow state write target 은 `ai-workflow/project/*` 로 유지한다.
- 실제 project docs 탐색은 `README.md`, `core/`, `backlog/` 를 우선 보고 `ai-workflow/` 는 메타 레이어로 분리한다.
- Codex 실제 적용 테스트에서는 `session-start`, `backlog-update --apply`, `doc-sync`, `validation-plan`, `code-index-update`, `merge-doc-reconcile --apply` 순으로 점검한다.
- OpenCode 로컬 LLM worker 는 `edit` 전 대상 파일을 바로 읽고, 작은 hunk 로 수정하며, tab/space 및 CRLF/LF 정규화가 필요하면 맡은 파일 범위로 제한한 뒤 reread/retry 하는 규칙을 기본값으로 둔다.

- [merge-doc-reconcile] 프로젝트 병합 규칙: ai-workflow/project/session_handoff.md 와 최신 workflow backlog 가 충돌하면 병합 후 handoff 를 우선 재작성한다.
- [merge-doc-reconcile] 병합 후 handoff 와 최신 backlog 의 상태값을 실제 저장소 기준으로 다시 맞춘다.
- [merge-doc-reconcile] 허브 및 인덱스 문서가 최신 문서 경로와 설명을 반영하는지 확인한다.
- [merge-doc-reconcile] 병합에 포함된 변경 파일과 문서 설명이 어긋나지 않는지 다시 본다.
## 다음에 읽을 문서

- 작업 백로그 인덱스: [./work_backlog.md](./work_backlog.md)
- 프로젝트 프로파일: [./project_workflow_profile.md](./project_workflow_profile.md)
