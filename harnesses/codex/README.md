# Codex Harness Package

- 문서 목적: 표준 AI 워크플로우를 Codex 하네스에 맞춰 배포할 때 생성되는 파일과 검토 포인트를 정리한다.
- 범위: `AGENTS.md`, Codex 설정 예시, 공통 문서 연결 방식
- 대상 독자: Codex 사용자, 저장소 관리자, AI workflow 설계자
- 상태: draft
- 최종 수정일: 2026-04-19
- 관련 문서: `../../core/workflow_harness_distribution.md`, `../../scripts/bootstrap_workflow_kit.py`

## 생성 대상

- 프로젝트 루트 `AGENTS.md`
- 프로젝트 루트 `.codex/config.toml.example`

## 구성 원칙

- `AGENTS.md` 는 Codex 의 프로젝트 지침 진입점으로 사용한다.
- 상세 정책은 `ai-workflow/project/` 문서를 먼저 읽도록 연결한다.
- `.codex/config.toml.example` 는 전역 Codex 설정에 병합 가능한 샘플 스니펫으로 유지한다.

## bootstrap 예시

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /tmp/example-repo \
  --project-slug example_repo \
  --project-name "Example Repo" \
  --harness codex \
  --copy-core-docs
```

## 도입 후 확인 포인트

- `AGENTS.md` 에 적힌 기본 명령이 실제 저장소와 맞는지 확인
- `ai-workflow/project/` 경로가 현재 저장소 구조와 맞는지 확인
- `.codex/config.toml.example` 를 실제 사용자 전역 설정에 반영할지 결정

## 다음에 읽을 문서

- 적용 가이드: [./apply_guide.md](./apply_guide.md)
- 하네스 허브: [../README.md](../README.md)
- 배포 전략: [../../core/workflow_harness_distribution.md](../../core/workflow_harness_distribution.md)
