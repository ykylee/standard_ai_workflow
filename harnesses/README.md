# Harnesses

- 문서 목적: 표준 AI 워크플로우를 하네스별 배포 패키지로 맞출 때 참고할 타겟별 안내 문서를 모은다.
- 범위: Codex, OpenCode 타겟별 파일 구성과 bootstrap 연결 방식, 추후 하네스 확장 포인트
- 대상 독자: 저장소 관리자, AI workflow 설계자, 하네스 통합 담당자
- 상태: draft
- 최종 수정일: 2026-04-19
- 관련 문서: `../core/workflow_harness_distribution.md`, `../scripts/bootstrap_workflow_kit.py`

## 현재 지원 타겟

- [codex/README.md](./codex/README.md)
- [codex/apply_guide.md](./codex/apply_guide.md)
- [opencode/README.md](./opencode/README.md)
- [opencode/apply_guide.md](./opencode/apply_guide.md)

## 추후 확장용 템플릿

- [_template/README.md](./_template/README.md)

## 공통 원칙

- 하네스별 파일은 정책 원문이 아니라 공통 workflow 문서로 연결하는 오버레이다.
- 공통 문서 세트는 `ai-workflow/` 아래에 유지한다.
- 실제 하네스가 읽는 파일은 프로젝트 루트 또는 하네스 전용 디렉터리에 생성한다.
- 새 하네스는 레지스트리 기반 bootstrap 확장 방식으로 추가한다.

## bootstrap 예시

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /tmp/example-repo \
  --project-slug example_repo \
  --project-name "Example Repo" \
  --harness codex \
  --harness opencode \
  --copy-core-docs
```

## 다음에 읽을 문서

- 배포 전략: [../core/workflow_harness_distribution.md](../core/workflow_harness_distribution.md)
- 하네스 템플릿: [./_template/README.md](./_template/README.md)
- 스크립트 안내: [../scripts/README.md](../scripts/README.md)
