# Project Workflow Profile

- 문서 목적: 프로젝트 특화 규칙과 실행/검증 기준을 정의한다.
- 범위: 프로젝트 개요, 문서 구조, 기본 명령, 검증 포인트, 예외 규칙
- 대상 독자: 개발자, 운영자, AI agent, 프로젝트 온보딩 담당자
- 상태: draft
- 최종 수정일: 2026-05-02
- 관련 문서: [공통 표준](../ai-workflow/core/global_workflow_standard.md)

## 1. 프로젝트 개요
- 프로젝트명: Standard AI Workflow
- 프로젝트 목적: 여러 프로젝트에서 공통으로 사용할 수 있는 표준 AI 협업 워크플로우 문서와 템플릿, 향후 skill/MCP/agent 구현 기준을 독립 프로젝트 형태로 제공한다.
- 주요 이해관계자: 개발자, 운영자, AI agent 설계자, 프로젝트 온보딩 담당자

## 2. 문서 구조 (Path)
- 문서 위키 홈: docs/README.md
- 운영 문서 홈: ai-workflow/memory/
- 백로그 위치: ai-workflow/memory/backlog/
- 세션 인계 문서: ai-workflow/memory/session_handoff.md
- 환경 기록 위치: ai-workflow/memory/environments/

## 3. 기본 명령 (Commands)
- 설치: `python3 -m pip install -r requirements-dev.txt`
- 로컬 실행 (부트스트랩): 
  ```bash
  python3 workflow-source/scripts/bootstrap_workflow_kit.py \
    --target-root . \
    --project-slug standard-ai-workflow \
    --project-name "Standard AI Workflow" \
    --harness antigravity \
    --adoption-mode existing \
    --copy-core-docs \
    --force
  ```
- 빠른 테스트 (Smoke): `for t in workflow-source/tests/check_*.py; do python3 "$t" || exit 1; done`
- 격리 테스트 (Bootstrap): `python3 workflow-source/tests/check_bootstrap.py`
- 실행 확인 (상태 동기화): 
  ```bash
  python3 workflow-source/scripts/generate_workflow_state.py \
    --project-profile-path docs/PROJECT_PROFILE.md \
    --session-handoff-path ai-workflow/memory/session_handoff.md \
    --work-backlog-index-path ai-workflow/memory/work_backlog.md \
    --output-path ai-workflow/memory/state.json
  ```

## 4. 검증 포인트 (Validation)
- 코드 변경: 모든 `workflow-source/tests/check_*.py` 스모크 테스트 통과 및 출력 스키마 계약(`schemas/generated_output_schemas.json`) 준수 여부 확인.
- 문서 변경: 필수 메타데이터 존재 여부 및 Markdown 상대 링크 무결성 확인 (`python3 workflow-source/tests/check_docs.py`).
- UI 변경: 현재 프로젝트는 CLI/문서 위주이나, 하네스 오버레이 생성 시 각 하네스(Codex, Antigravity 등)에서의 렌더링 확인.
- 배포/운영: `workflow-source/scripts/export_harness_package.py`를 통한 패키지 생성 확인 및 `workflow-source/releases/` 가이드라인 준수.

## 5. 예외 규칙 (Policy)
- 병합: `ai-workflow/memory/state.json` 등 자동 생성 파일은 충돌 시 소스 문서(backlog, handoff)를 기준으로 재생성한다.
- 승인: 코어 문서(`workflow-source/core/`) 변경 시 아키텍처 리뷰 필수.
- 제약: Python 3.10+ 환경 필수 (MCP SDK 의존성).
- 기타: 모든 스킬 및 MCP 출력은 공통 JSON 계약 구조를 따라야 함.

## 다음에 읽을 문서
- [세션 인계 문서](../ai-workflow/memory/session_handoff.md)
- [작업 백로그](../ai-workflow/memory/work_backlog.md)
