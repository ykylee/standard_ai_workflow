# Repository Assessment

- 문서 목적: 기존 프로젝트에 표준 AI 워크플로우를 도입하기 전에 현재 코드베이스와 문서 구조를 빠르게 진단한다.
- 범위: 저장소 구조, 추정 기술 스택, 문서 위치, 테스트 흔적, 초기 워크플로우 도입 포인트
- 대상 독자: 개발자, 운영자, AI agent, 프로젝트 온보딩 담당자
- 상태: stable
- 최종 수정일: 2026-04-25
- 관련 문서: `./PROJECT_PROFILE.md`, `./session_handoff.md`, `../core/workflow_adoption_entrypoints.md`

## 1. 요약

- 분석 대상 프로젝트:
- `Standard AI Workflow`
- 분석 모드:
- `self-dogfooding` (워크플로우 키트 자체 개발 저장소)
- 기본 스택:
- `Python 3.11+`
- 감지된 스택 라벨:
- `MCP SDK`, `JSON Schema`, `Markdown-based operations`

## 2. 저장소 구조 관찰

- 상위 디렉터리 항목:
- `ai-workflow/`: 워크플로우 핵심 로직, 프로젝트 메타데이터, 스킬, MCP 관련 파일들
- `core/`, `harnesses/`, `mcp/`, `skills/`, `templates/`: 개별 워크플로우 컴포넌트들
- `scripts/`: 워크플로우 운영 및 자동화를 위한 Python 스크립트들
- `tests/`: 문서 정합성 및 스크립트 기능 검증용 테스트들
- `GEMINI.md`: Gemini CLI 전용 운영 지침
- 소스 디렉터리 후보:
- `scripts/`, `workflow_kit/`
- 문서 디렉터리 후보:
- `ai-workflow/`, `core/`, `README.md`
- 테스트 디렉터리 후보:
- `tests/`

## 3. 확정 명령

- 설치:
- `python3 -m pip install -r requirements-dev.txt`
- 로컬 실행:
- `python3 scripts/run_demo_workflow.py`
- 빠른 테스트:
- `python3 tests/check_docs.py`
- 격리 테스트:
- `for t in tests/check_*.py; do python3 "$t" || exit 1; done`
- 실행 확인:
- `python3 scripts/bootstrap_workflow_kit.py --help`

## 4. package script 및 경로 샘플

- package script 목록:
- N/A (Python scripts 중심)
- 분석 중 확인한 주요 경로:
- `GEMINI.md`
- `ai-workflow/memory/state.json`
- `ai-workflow/memory/session_handoff.md`
- `ai-workflow/memory/work_backlog.md`
- `scripts/bootstrap_workflow_kit.py`
- `scripts/export_harness_package.py`

## 5. 워크플로우 운영 설정

- 문서 위키 홈:
- `README.md`
- 운영 문서 위치:
- `ai-workflow/memory/`
- backlog 위치:
- `ai-workflow/memory/backlog/`
- session handoff 위치:
- `ai-workflow/memory/session_handoff.md`

## 6. 특이 사항

- 이 저장소는 워크플로우 키트 자체의 개발 저장소이므로, `ai-workflow/` 디렉터리가 개발 대상이자 동시에 운영 도구로 사용되는 "self-dogfooding" 구조이다.
- 모든 운영 문서는 한국어를 기본으로 하며, 기술적 용어만 영어로 유지한다.

## 다음에 읽을 문서

- 프로젝트 프로파일: [./PROJECT_PROFILE.md](./PROJECT_PROFILE.md)
- 세션 인계 문서: [./session_handoff.md](./session_handoff.md)
- 도입 분기 가이드: [../core/workflow_adoption_entrypoints.md](../core/workflow_adoption_entrypoints.md)
