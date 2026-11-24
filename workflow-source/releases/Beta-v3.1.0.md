# Beta v3.1.0 — MCP 최신 프로토콜과 허브 작업 추적 (2026-11-24)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다. Go/Python 허브 구현의 패리티와 macOS·Windows native 실측이 모두 끝난 정식 운영판은 아니다.

## 변경

- Python MCP SDK 최소 지원을 2.3.0으로 올리고, Python과 Go의 MCP 연결을 `2026-07-28` 프로토콜에 맞췄다.
- Hub 런타임 버전과 kit 호환 계약 버전(2.1.0)을 API, MCP server info, 안내 페이지에서 구분한다.
- Go·Python 허브의 PostgreSQL 지원과 시작 시 schema migration을 제공한다. SQLite는 로컬·테스트 기본값이며 기존 SQLite 데이터 이전은 명시적 migration으로 수행한다.
- 세션이 허브 MCP에 직접 연결하는 경로를 기본으로 한다. PC 중계는 허브가 로컬 harness 세션을 시작할 때 선택적으로 설정한다.
- 사내 Windows 보안 환경에서는 Python 허브 경로를 우선 안내한다. setup 문서에는 선택형 중계 상태 확인을 추가했다.
- task에 3단계 category와 테스트 정의·실행 이력을 연결한다. 테스트는 세션이 로컬에서 실행하고 결과를 허브에 기록한다. task 완료에는 필수 테스트의 가장 최근 run이 `passed`여야 한다.
- 프로젝트 목록 UI에서 `null` 문자열 노출을 막고 task 목록·상세에 카테고리와 최근 테스트 결과를 표시한다.

## 검증

- 누적 smoke **354/354 PASS** (`run_all_checks.py --branch-context=all`).
- Go 허브 6개 OS/아키텍처 산출물, wheel/sdist와 `SHA256SUMS`를 첨부한다. kit plugin ZIP은 포함하지 않는다.
- Python·Go 허브 core 및 MCP 회귀, Go 전체 테스트/vet, 생성형 MCP fixture·asset 동기화를 릴리스 게이트에서 확인한다.

## 운영 범위

- 이 판은 평가용 pre-release다. 운영 DB를 전환하기 전에 일관된 복제본으로 검증한다.
- 실제 Windows/macOS native 실행과 전체 Go/Python shadow parity는 이 release 노트의 검증 범위가 아니다.
