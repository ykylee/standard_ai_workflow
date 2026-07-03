# CodeWhale Harness

- 문서 목적: CodeWhale 환경에서 표준 AI 워크플로우를 운영하기 위한 진입점과 운영 원칙을 안내한다.
- 범위: `.codewhale/skills/codewhale-workflow/SKILL.md` 진입점, Constitution 보강 원칙, 적용 절차
- 대상 독자: CodeWhale 운영자, 저장소 관리자, AI workflow 설계자
- 상태: draft
- 최종 수정일: 2026-07-03
- 관련 문서: `../../core/workflow_harness_distribution.md`, `../../core/workflow_agent_topology.md`

## 1. CodeWhale 하네스의 철학

CodeWhale은 기존 하네스(Codex, OpenCode 등)와 근본적으로 다른 접근이 필요하다.
CodeWhale의 **Constitution**(Article I-VIII)이 이미 검증, 병렬화, 컨텍스트 관리,
계획 수립, 서브 에이전트 위임 전략을 내장하고 있기 때문이다.

따라서 CodeWhale overlay는 긴 규칙을 주입하는 대신,
**Constitution이 제공하지 않는 워크플로우 고유 가치만 얇게 추가**하는 방식을 취한다.

### Constitution이 이미 처리하는 항목 (중복 주입 금지)

| Constitution Article | 처리 내용 |
| --- | --- |
| Article II (Verification) | 검증 없이 완료 선언 금지 |
| Article III (Momentum) | 병렬 실행, 독립 작업 fan-out |
| Article IV (Legacy) | 불필요한 추가 금지, workspace 정리 |
| Article VI (Priority) | 규칙 우선순위 |
| Regulations | 컨텍스트 관리, plan 패턴, 오케스트레이션 |
| Statutes | 실행 규율, 도구 사용, scope discipline |

### 본 overlay가 추가하는 고유 가치

- 세션 시작 순서 (handoff → backlog → profile)
- 한국어 보고 원칙
- 백로그/handoff 관리 패턴 (날짜별, 최소 필드)
- 프로젝트 프로파일 기반 문서 탐색
- `ai-workflow/` 메타 레이어 인식

## 2. 진입 파일

CodeWhale overlay는 단일 파일을 생성한다:

- `.codewhale/skills/codewhale-workflow/SKILL.md`

이 파일은 project-local CodeWhale skill로, CodeWhale이 프로젝트 디렉터리에서
자동으로 인식한다.

## 3. bootstrap 적용

```bash
python3 workflow-source/scripts/bootstrap_workflow_kit.py \
  --target-root . \
  --project-slug <slug> \
  --project-name "<name>" \
  --harness codewhale \
  --adoption-mode existing \
  --copy-core-docs
```

## 4. 첫 세션

CodeWhale 세션에서 다음과 같이 요청해 워크플로우를 활성화한다:

> `.codewhale/skills/codewhale-workflow/SKILL.md` 를 읽고,
> `ai-workflow/memory/active/state.json` 을 기준으로 워크플로우 세션을 시작해줘.

## 5. 다른 하네스와의 차이

| 측면 | CodeWhale | 기존 하네스 (Codex, OpenCode 등) |
| --- | --- | --- |
| 생성 파일 수 | 1개 | 7~10개 |
| 규칙 중복 | 최소화 (Constitution 활용) | 높음 (기본 태도까지 명시) |
| 진입점 | `.codewhale/skills/` (project-local skill) | 루트 `AGENTS.md` 등 |
| 규칙 계층 | Constitution 아래 additive | 독립 실행 규칙 |

## 다음에 읽을 문서

- 적용 가이드: [./apply_guide.md](./apply_guide.md)
- 하네스 허브: [../README.md](../README.md)
- 배포 전략: [../../core/workflow_harness_distribution.md](../../core/workflow_harness_distribution.md)
- Constitution 분석: [../../core/workflow_harness_distribution.md §CodeWhale](../../core/workflow_harness_distribution.md)
