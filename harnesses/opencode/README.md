# OpenCode Harness Package

- 문서 목적: 표준 AI 워크플로우를 OpenCode 하네스에 맞춰 배포할 때 생성되는 파일과 검토 포인트를 정리한다.
- 범위: `opencode.json`, project-local skill/agent 파일, 공통 문서 연결 방식
- 대상 독자: OpenCode 사용자, 저장소 관리자, AI workflow 설계자
- 상태: draft
- 최종 수정일: 2026-04-19
- 관련 문서: `../../core/workflow_harness_distribution.md`, `../../scripts/bootstrap_workflow_kit.py`

## 생성 대상

- 프로젝트 루트 `AGENTS.md`
- 프로젝트 루트 `opencode.json`
- 프로젝트 루트 `.opencode/skills/standard-ai-workflow/SKILL.md`
- 프로젝트 루트 `.opencode/agents/workflow-orchestrator.md`
- 프로젝트 루트 `.opencode/agents/workflow-worker.md`
- 프로젝트 루트 `.opencode/agents/workflow-doc-worker.md`
- 프로젝트 루트 `.opencode/agents/workflow-code-worker.md`
- 프로젝트 루트 `.opencode/agents/workflow-validation-worker.md`

## 구성 원칙

- `AGENTS.md` 를 공통 상위 진입 문서로 사용한다.
- `opencode.json` 은 공통 workflow 문서를 `instructions` 로 직접 가리킨다.
- `opencode.json` 은 기존 사용자 provider/model 기본값을 덮어쓰지 않도록 최소 키만 유지한다.
- project-local skill 은 세션 시작, backlog 갱신, handoff 정리를 위한 빠른 진입점 역할을 한다.
- project-local agent 는 workflow 문서와 기본 명령을 기준으로 조정 가능한 운영 오케스트레이터 역할을 한다.
- 메인 오케스트레이터 agent 는 read-mostly coordinator 로 두고, 실제 수정과 대량 탐색은 서브 에이전트로 분리하는 구성을 권장한다.
- worker agent 는 bounded scope 의 읽기/쓰기/검증 작업을 받아 실행하고, 핵심 결과만 오케스트레이터에 되돌려주는 역할을 맡는다.
- 문서/코드/검증 worker 를 나누면 역할이 더 선명해지고, `main orchestrator + small workers` 구조를 운영하기 쉬워진다.

## bootstrap 예시

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /tmp/example-repo \
  --project-slug example_repo \
  --project-name "Example Repo" \
  --harness opencode \
  --copy-core-docs
```

## 도입 후 확인 포인트

- `AGENTS.md` 가 생성됐는지 확인
- `opencode.json` 의 instruction 경로가 현재 저장소 구조와 맞는지 확인
- `.opencode/agents/` 권한 정책이 현재 팀 운영 방식과 맞는지 확인
- 메인 오케스트레이터의 툴 권한이 지나치게 넓지 않은지 확인
- worker agent 의 범위와 권한이 실제 실행 작업에 비해 과도하지 않은지 확인
- 문서/코드/검증 worker 분리가 현재 팀 운영 방식과 맞는지 확인
- `.opencode/skills/standard-ai-workflow/SKILL.md` 에 적힌 참조 문서가 최신 상태인지 확인
- 생성된 `AGENTS.md`, skill, agent 문구에 한국어 보고/컨텍스트 절약 원칙이 포함되는지 확인

## 다음에 읽을 문서

- 적용 가이드: [./apply_guide.md](./apply_guide.md)
- 하네스 허브: [../README.md](../README.md)
- 배포 전략: [../../core/workflow_harness_distribution.md](../../core/workflow_harness_distribution.md)
- bootstrap 생성물 샘플: [../../examples/bootstrap_output_samples.md](../../examples/bootstrap_output_samples.md)
