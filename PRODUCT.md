# Product

- 문서 목적: 화면을 만들고 고치는 사람 · 에이전트가 따를 제품 사실(사용자 · 목적 · 제약 · 원칙)을 한곳에 둔다 — impeccable 이 읽는 PRODUCT.md 형식
- 범위: 허브 · 워크벤치 · PC 중계(VS Code) 화면의 제품 맥락. 시각 규약은 `DESIGN.md`
- 대상 독자: 화면 작업자, AI 에이전트
- 상태: beta
- 최종 수정일: 2026-11-26
- 관련 문서: [`DESIGN.md`](./DESIGN.md), [`docs/FRONTEND_TOOLKIT.md`](./docs/FRONTEND_TOOLKIT.md)

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **팀** (2026-11-26 소유자 확인): 프로젝트 소유자 한 사람만이 아니라 동료 · 사내 사용자 여럿이 같은 허브를 본다. 처음 오는 사람도 용어집 없이 화면을 읽을 수 있어야 한다.
- **소유자 · 관리자**: 계정 · 콜사인 · 승인 · 지침 판을 결정한다. 승인과 DCR 결정은 권한 있는 사람만 한다.
- **AI 에이전트 세션** (Claude Code · Codex · Gemini CLI 등): 화면이 아니라 MCP 도구로 같은 데이터를 쓴다. 화면은 사람이 에이전트의 일을 보고 판단하는 곳이다.

장면: PC 브라우저가 중심이고, iPad · 휴대폰으로 확인하거나 승인하는 일도 있다. VS Code 안에서는 PC 중계 화면을 webview 로 본다.

## Product Purpose

여러 하네스 · 여러 PC 의 AI 에이전트가 하는 일을 한곳에 모은다 — task · handoff · 로드맵 · 공유 지침 · 위키 · 결정(DCR) · 승인 · 오케스트레이션의 정본이 허브이고, 저장소의 파일은 내보내기다.

화면이 가장 먼저 성공해야 하는 일 (2026-11-26 소유자): **전체 진척 파악** — 로드맵과 task 진척이 한눈에 보인다. 사람이 결정할 일(승인 · 열린 결정 · 막힌 task)은 그 그림 안에서 놓치지 않게 드러난다.

## Positioning

하네스 중립이다 — 특정 에이전트 제품의 대시보드가 아니라, 어떤 하네스든 MCP · A2A 로 붙어 같은 task · 같은 승인 흐름을 쓴다. 상태는 권한이 아니다: 실행은 승인 ID 로만 열린다.

## Operating Context

- 서버: Python 허브와 Go 허브가 같은 정적 화면(`workflow-source/workflow_kit/hub/static/`, Go 사본 `hub-go/internal/assets/static/`)을 내준다. 운영 정본은 홈랩 허브.
- 1.x 워크벤치(`workflow-source/workflow_kit/workbench/`)는 로컬 계획 검토 화면으로 남아 있다.
- PC 중계(`workflow-source/workflow_kit/relay/ui.py`, Go `hub-go/internal/relay/ui.go`)는 한 PC 의 세션 · 허용 경로 · 로그를 보이고, VS Code 확장(`editors/vscode/`)이 iframe 으로 담는다.
- 회귀 검사: `workflow-source/tests/check_hub_screens.py` 가 headless Chrome 으로 전 화면을 그린다. CI 는 없고 로컬 게이트다(`docs/LOCAL_GATE.md`).

## Capabilities and Constraints

- 외부 자원 없음 — 글꼴 · CDN · 빌드 단계 없이 손으로 쓴 HTML · CSS · JS. 허브는 CSP `style-src 'self'` 라 인라인 style 을 쓰지 않는다.
- 같은 정적 파일이 두 서버(Python · Go)에서 같은 API 로 돌아야 한다.
- 계정 로그인(쿠키)과 토큰이 있다. 권한 없는 사람에게는 승인 단추가 보이지 않거나 꺼진다.
- 용어: task · handoff · 콜사인 · 세션 · 로드맵 · WBS · 마일스톤 · DCR · 아이디어 박스 · 승인 · 오케스트레이터 · 중계.

## Evidence on Hand

- 실측 기준선: `docs/FRONTEND_TOOLKIT.md` §8 (2026-11-26 허브 3.6.0 화면 critique).
- 실제 운영 데이터는 홈랩 허브에 있다. 화면 예시 · 문서에 고객 · 사용 수치를 지어내지 않는다.

## Product Principles

1. 진척이 먼저 보이고, 사람의 결정은 그 안에서 놓치지 않는다.
2. 처음 온 팀원도 읽을 수 있다 — 내부 ID 보다 제목과 상태 글자가 앞선다.
3. 확인한 것과 확인하지 못한 것을 구분해 보인다. 미측정을 통과처럼 그리지 않는다.
4. 되돌릴 수 없는 동작은 권한 · 승인 뒤에만 있고, 화면은 그 경계를 분명히 한다.

## Accessibility & Inclusion

WCAG 2.2 AA (대비 · 키보드 · 보이는 라벨). 화면 문구는 한국어, 코드 · 명령 · ID 는 원문.
