# Goose Harness Package

- 문서 목적: 표준 AI 워크플로우를 Goose 하네스에 맞춰 배포할 때 생성되는 파일과 검토 포인트를 정리한다.
- 범위: `AGENTS.md`, Goose 설정 예시, 공통 문서 연결 방식
- 대상 독자: Goose 사용자, 저장소 관리자, AI workflow 설계자
- 상태: draft
- 최종 수정일: 2026-07-17
- 관련 문서: `../../core/workflow_harness_distribution.md`, `../../scripts/bootstrap_workflow_kit.py`

## 생성 대상

- 프로젝트 루트 `AGENTS.md`
- 프로젝트 루트 `.goose/config.toml.example`

## 구성 원칙

- `AGENTS.md` 는 Goose 의 프로젝트 지침 진입점으로 사용한다.
- 상세 정책은 `ai-workflow/memory/active/` 문서를 먼저 읽도록 연결한다.
- `.goose/config.toml.example` 은 전역 Goose 설정에 병합 가능한 샘플 스니펫으로 유지한다.
