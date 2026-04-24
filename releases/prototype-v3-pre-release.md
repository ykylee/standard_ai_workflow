# Prototype-v3 Pre-release

- 문서 목적: `prototype-v3` pre-release 의 주요 변경점, 배포 산출물, 적용 대상, 검증 결과를 기록한다.
- 범위: skill beta upgrade, workflow 통합 검증, MCP read-only server 검토
- 대상 독자: 저장소 관리자, 배포 담당자, 하네스 통합 담당자, 파일럿 적용자
- 상태: draft
- 최종 수정일: 2026-04-24
- 관련 문서: `../README.md`, `../core/workflow_kit_roadmap.md`, `../core/workflow_release_spec.md`

## 1. 릴리즈 성격

- 버전: `prototype-v3`
- 채널: `pre-release`
- 릴리즈 초점: skill beta upgrade, workflow 통합 검증, MCP read-only server 검토
- 제외 범위: 정식 MCP server 기본 활성화, multi-project 파일럿 일반화

## 2. 핵심 변경

### skill beta upgrade 축

- session-start, backlog-update, doc-sync, merge-doc-reconcile 4종 skill beta 수준의 upgrade
- 각 skill smoke test 통과
- error_code 기반 구조화된 실패 출력 패턴 적용

### workflow 통합축

- session-start → backlog-update 연결 검증
- doc-sync → validation-plan 연결 검증
- end2end_runner 통합 검증
- existing project onboarding 통합 검증

### MCP read-only 축

- read-only MCP server prototype 검토
- JSON-RPC bridge draft 구조
- official MCP SDK candidate 검증

## 3. 배포 산출물

### Codex

- package root: `dist/harnesses/codex/prototype-v3/`
- zip: `dist/harnesses/codex/prototype-v3/standard-ai-workflow-codex-prototype-v3.zip`
- 포함 파일 수: 13개

### OpenCode

- package root: `dist/harnesses/opencode/prototype-v3/`
- zip: `dist/harnesses/opencode/prototype-v3/standard-ai-workflow-opencode-prototype-v3.zip`
- 포함 파일 수: 19개

## 4. 검증 결과

- session-start smoke test: ✅ 통과
- backlog-update smoke test: ✅ 통과
- doc-sync smoke test: ✅ 통과
- merge-doc-reconcile smoke test: ✅ 통과
- validation-plan smoke test: ✅ 통과
- code-index-update smoke test: ✅ 통과
- end-to-end demo workflow: ✅ 통과
- existing project onboarding: ✅ 통과

## 5. 다음 단계 권장

- MCP server 승격 검토
- 패키지 배포 (GitHub release)
- 다른 프로젝트 파일럿 적용