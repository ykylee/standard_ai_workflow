# CodeWhale Workflow Apply Guide

- 문서 목적: 기존 또는 신규 프로젝트에 표준 AI 워크플로우를 CodeWhale 하네스 기준으로 적용하는 실제 절차를 단계별로 안내한다.
- 범위: bootstrap 실행, 생성 파일 검토, 첫 세션 시작 방법
- 대상 독자: CodeWhale 사용자, 저장소 관리자, AI workflow 설계자
- 상태: draft
- 최종 수정일: 2026-07-03
- 관련 문서: `./README.md`, `../../core/workflow_adoption_entrypoints.md`, `../../core/workflow_harness_distribution.md`, `../../scripts/bootstrap_workflow_kit.py`

## 1. 언제 이 가이드를 쓰는가

- 프로젝트에서 CodeWhale 을 주 하네스로 사용하려고 할 때
- 표준 workflow 문서를 CodeWhale 의 project-local skill 로 연결하려고 할 때
- 신규 프로젝트 또는 기존 프로젝트에 CodeWhale 기준 도입을 시작하려고 할 때

## 2. 적용 전 확인

- CodeWhale 이 프로젝트 디렉터리의 `.codewhale/skills/` 를 인식할 수 있어야 한다 (v0.8.66+ 확인).
- 프로젝트에서 workflow 문서를 둘 위치를 `ai-workflow/` 로 유지할지 결정한다.
- 기존 프로젝트라면 기본 실행 명령과 테스트 명령을 자동 추정값과 대조할 사람이 필요하다.

## 2.1 Constitution 과의 관계 이해

CodeWhale 은 Constitution (Article I-VIII) 이라는 계층형 시스템 프롬프트를 사용한다.
본 워크플로우 skill 은 Constitution 아래에서 **additive rule** 로 동작한다.

- Constitution 이 이미 처리하는 규칙 (검증, 병렬화, 컨텍스트 관리) 은 skill 에서 반복하지 않는다.
- Skill 은 Constitution 이 제공하지 않는 세션 시작 순서, 한국어 보고, 백로그 관리 패턴만 추가한다.
- Constitution Article VI (Priority) 에 따라 project instructions → memory → handoff 순으로 우선순위가 결정된다.

## 2.2 권장 설정 계층

CodeWhale 에서는 아래 3계층을 권장한다:

- **전역**: `~/.codewhale/skills/` (사용자 개인 skill)
- **프로젝트**: `.codewhale/skills/codewhale-workflow/SKILL.md` (project-local, 본 overlay가 생성)
- **상태**: `ai-workflow/memory/active/` (세션 상태, backlog, handoff)

## 3. 신규 프로젝트 적용 순서

1. 아래 명령으로 기본 문서 세트와 CodeWhale overlay 를 생성한다.

```bash
python3 workflow-source/scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/project \
  --project-slug my_project \
  --project-name "My Project" \
  --adoption-mode new \
  --harness codewhale \
  --copy-core-docs
```

2. 생성된 `ai-workflow/memory/active/PROJECT_PROFILE.md` 에 실제 명령과 검증 규칙을 채운다.
3. `.codewhale/skills/codewhale-workflow/SKILL.md` 가 생성되었는지 확인한다.
4. 첫 세션에서 아래와 같이 요청한다:

> `.codewhale/skills/codewhale-workflow/SKILL.md` 를 읽고 워크플로우 세션을 시작해줘.

5. `session_handoff.md` 와 오늘 날짜 backlog 를 채운다.

## 4. 작업 중인 프로젝트 적용 순서

1. 아래 명령으로 기존 저장소 분석과 CodeWhale overlay 를 함께 생성한다.

```bash
python3 workflow-source/scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/project \
  --project-slug my_project \
  --project-name "My Project" \
  --adoption-mode existing \
  --harness codewhale \
  --copy-core-docs
```

2. `ai-workflow/memory/active/repository_assessment.md` 를 읽고 추정 스택, 명령, 문서 경로가 실제 저장소와 맞는지 검토한다.
3. `PROJECT_PROFILE.md` 의 설치, 실행, 테스트 명령을 실제 운영 기준으로 수정한다.
4. 첫 실제 작업을 오늘 날짜 backlog 에 등록하고, 세션 종료 직전(commit 직전) handoff 를 갱신한다. 종료 절차는 `memory 갱신 → commit → push` 순서.

## 5. CodeWhale 에서 첫 세션 시작하는 방법

- 먼저 `.codewhale/skills/codewhale-workflow/SKILL.md` 를 읽는다.
- 이어서 아래 문서를 순서대로 읽는다:
  - `ai-workflow/memory/active/state.json`
  - `ai-workflow/memory/active/sessions`
  - `ai-workflow/memory/active/backlog`
  - `ai-workflow/memory/active/PROJECT_PROFILE.md`
- 기존 프로젝트 도입 직후라면 `ai-workflow/memory/active/repository_assessment.md` 도 함께 읽는다.

## 6. CodeWhale 특화 운영 팁

- **서브 에이전트 활용**: CodeWhale 의 `agent` 도구 (`explore`, `plan`, `review`, `implementer`, `verifier`) 를 적극 활용한다. 메인 오케스트레이터는 조정/통합/보고에 집중하고, 대량 탐색과 구현은 서브 에이전트로 위임한다.
- **컨텍스트 관리**: Constitution Regulations 의 컨텍스트 관리 규칙을 신뢰한다. `/compact` 나 Ctrl+L 은 60% 근처에서만 제안한다.
- **병렬 실행**: Constitution Article III (Momentum) 에 따라 독립 작업은 fan-out 한다.

## 7. 적용 후 확인 체크리스트

- `.codewhale/skills/codewhale-workflow/SKILL.md` 가 존재한다.
- `ai-workflow/memory/active/` 문서 세트가 존재한다.
- profile 문서의 명령이 실제 저장소 기준으로 채워져 있다.
- 첫 backlog 항목과 handoff 가 비어 있지 않다.
- CodeWhale 이 `.codewhale/skills/` 를 인식하는지 확인했다.

## 8. 자주 손보게 되는 부분

- `PROJECT_PROFILE.md` 의 검증 규칙
- `session_handoff.md` 의 현재 기준선
- 최신 날짜 backlog 의 상태값과 다음 세션 시작 포인트
- `.codewhale/skills/codewhale-workflow/SKILL.md` 의 기본 검증 명령 (§7)

## 9. 피해야 할 구성

- `.codewhale/skills/codewhale-workflow/SKILL.md` 에 Constitution 과 중복되는 규칙을 추가하는 것
- `ai-workflow/memory/active/` 대신 다른 경로에 상태 문서를 두는 것
- 여러 하네스의 진입 파일(`AGENTS.md`, `MiniMax.md` 등)을 CodeWhale 용과 혼용하는 것
- CodeWhale Constitution 의 규칙을 skill 에서 재정의하려는 것 (Constitution Article VI 우선)

## 다음에 읽을 문서

- 하네스 README: [./README.md](./README.md)
- 도입 분기 가이드: [../../core/workflow_adoption_entrypoints.md](../../core/workflow_adoption_entrypoints.md)
- 설정 계층 가이드: [../../core/workflow_configuration_layers.md](../../core/workflow_configuration_layers.md)
