# Beta v3.2.1 — 관리자 UX와 미지원 하네스 셋업 등록 (2026-11-24)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다. 전체 Go/Python shadow parity 및 macOS·Windows native 실측이 모두 끝난 정식 운영판은 아니다.

## 변경

- 웹 허브 홈과 상단에 관리자 모드 진입을 추가하고, 저장된 관리자 토큰을 홈에서 검증·복원한다. 로그인 화면에 토큰 발급 명령과 권한 안내를 제공한다.
- bootstrap 이후 `AGENTS.md` 등 허브 진입 파일에 새 task 등록·조회·수정·종료 흐름과 MCP 전체 도구 카탈로그를 렌더링한다. 생성된 안내가 서버 도구 레지스트리의 모든 도구 이름을 포함하는지 회귀 검사한다.
- task 표의 카테고리 열이 폭 0으로 눌려 상태 칸과 겹치던 레이아웃을 고치고, 작은 화면에서는 표가 가로 스크롤되도록 최소 열 폭을 고정한다.
- 셋업 미지원 하네스는 `hub_setup_plan`에서 400 대신 등록 대기 단계를 받는다. 클라이언트는 안전한 진입 파일·MCP 설정 경로 후보와 호환 정보를 `hub_harness_report`로 제보한다.
- 관리자는 후보를 검토하고 사람 담당자 한 명 이상 및 명시적 프로필 확인과 함께 `mcp-http-json-v1` 설정 지원을 승인한다.
- 승인된 선언형 프로필만 Go/Python `hub_setup_plan`과 `hub_guide_render`에서 사용한다. 표준 안내와 Streamable HTTP JSON 설정을 병합하며 토큰은 `${WORKFLOW_HUB_TOKEN}` 환경 변수 참조로 저장한다. 임의 명령·코드는 실행하지 않는다.
- 승인 전 또는 지원 프로필이 없는 하네스에는 프로젝트 파일 쓰기 단계가 나오지 않는다. 기존 metadata-only 등록도 세션 시작에서 재제보 도구와 필수 정보를 안내한다.

## 검증

- 누적 smoke **357/357 PASS**

- Go `go build ./...` 통과.
- 변경된 Python 허브 모듈 컴파일과 관리자 UI JavaScript 구문 검사 통과.
- Go 내장 UI와 Python 정적 자산 바이트 일치, `git diff --check` 통과.
- 전체 native/slash release gate: 배포 직전 실행 결과를 기록한다.
- 홈랩 live health/MCP: 배포 직전 실행 결과를 기록한다.

## 운영 범위

- 이 판은 평가용 pre-release다. 새 셋업 프로필은 관리자 승인과 책임자 등록을 거친다.
- GitHub 배포에는 Python wheel/sdist, Go 6개 OS/아키텍처 산출물과 `SHA256SUMS`를 포함한다. kit plugin ZIP은 포함하지 않는다.
- 홈랩 pilot은 기존 SQLite DB 판 15를 유지하며 새 버전 시작 시 추가 migration이 예상되지 않는다. 자동화 백업과 이전 Go 바이너리를 보존한다.
