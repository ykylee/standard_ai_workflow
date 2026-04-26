# Standard AI Workflow Quickstart

- 문서 목적: Standard AI Workflow를 신규 프로젝트에 빠르게 도입하는 방법을 안내한다.
- 범위: 프로젝트 초기화, 환경 설정, 첫 세션 시작 가이드
- 대상 독자: AI 에이전트와 협업하려는 개발자
- 상태: beta
- 최종 수정일: 2026-04-26
- 관련 문서: `ai-workflow/README.md`, `GEMINI.md`

이 문서는 **Standard AI Workflow**를 여러분의 프로젝트에 5분 만에 도입하여 AI 에이전트와 체계적으로 Peer Programming을 시작하는 방법을 안내합니다.

## 1. 목적

- AI 에이전트가 프로젝트의 컨텍스트를 스스로 이해하고 관리하도록 합니다.
- 작업 이력(Backlog), 세션 상태(Handoff), 프로젝트 프로파일을 표준화된 방식으로 유지합니다.
- 복잡한 작업(문서 동기화, 테스트 검증 등)을 전용 스킬(Skill)과 MCP 도구로 자동화합니다.

## 2. 준비물

- **Python 3.11+**: 워크플로우 도구 실행에 필요합니다.
- **Gemini CLI**: 권장 에이전트 하네스입니다.
- **배포 패키지**: `dist/harnesses/gemini-cli/beta-v2.0/` 에 있는 압축 파일.

## 3. 3단계 도입 가이드

### 1단계: 프로젝트 초기화

배포 패키지의 `bundle/` 디렉토리 내용을 프로젝트 루트에 복사합니다.

```bash
# 패키지 압축을 푼 후 프로젝트 루트에서 실행
cp -r /path/to/bundle/ai-workflow .
cp /path/to/bundle/GEMINI.md .
```

- `ai-workflow/`: 워크플로우의 상태와 메타데이터가 저장되는 공간입니다.
- `GEMINI.md`: AI 에이전트가 이 프로젝트의 워크플로우 규칙을 인지하게 하는 진입점입니다.

### 2단계: 의존성 설치 및 환경 설정

워크플로우 스크립트 실행을 위해 가상환경을 구축하고 필수 라이브러리를 설치합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### 3단계: 첫 세션 시작

AI 에이전트에게 워크플로우가 도입되었음을 알리고 상태를 점검하게 합니다.

```bash
# Gemini CLI 세션 시작 시 에이전트에게 다음을 요청하세요:
"프로젝트 루트의 GEMINI.md를 읽고 워크플로우 세션을 시작해줘."
```

## 4. 핵심 워크플로우 도구 (Skills)

워크플로우가 안정되면 에이전트가 다음 도구들을 사용하여 작업을 보조합니다:

- **`session-start`**: 세션 시작 시 현재 상태 복원 및 작업 방향 제안.
- **`backlog-update`**: 새 작업 등록 및 진행 중인 작업 상태 업데이트.
- **`doc-sync`**: 코드 변경에 따른 관련 문서(Handoff, Profile 등) 자동 동기화 추천.
- **`validation-plan`**: 변경 사항 검증을 위한 테스트 계획 수립 및 실행.

## 5. MCP 도구 사용 (선택 사항)

정식 MCP SDK가 설치된 경우, 에이전트는 더 강력한 도구를 직접 사용할 수 있습니다:

```bash
# MCP 서버 실행 예시
python3 workflow_kit/server/read_only_mcp_sdk.py --stdio-sdk
```

---
더 자세한 내용은 `ai-workflow/README.md`를 참고하세요.
