# Beta v3.2.0 — 프로젝트 지식과 결정 공유 (2026-11-24)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다. Go/Python 허브 구현의 패리티 및 macOS·Windows native 실측이 모두 끝난 정식 운영판은 아니다.

## 변경

- project-scoped knowledge catalog를 추가해 등록된 Git 문서·ADR, Hub Wiki, DCR, memory 항목을 출처·판·해시가 포함된 ref로 검색하고 조회한다.
- Git source는 프로젝트 owner가 등록한 Markdown allowlist만 받고, 세션이 제공한 commit SHA와 content hash를 저장한다. Hub는 Git remote를 직접 읽거나 commit/push하지 않는다.
- DCR 생성·목록·상세·승인/거절 및 감사 timeline을 추가했다. 승인된 human project owner만 결정을 내릴 수 있다.
- DCR 승인 시 새 ADR 초안과 경로·SHA-256을 만들고 `approved_pending_export`로 둔다. 일치하는 ADR 내용을 등록 source에서 sync해야 accepted가 되며, 대체된 ADR projection은 superseded로 표시한다.
- Wiki 페이지 수정·삭제 이력을 보존한다. DB migration V13이 기존 Wiki 문서를 최초 revision으로 옮기며, Python과 Go migration이 바이트 단위로 일치한다.
- 허브 UI에 프로젝트별 지식 검색과 DCR 결정 이력을 추가했다. 통합 검색 결과는 출처가 분리되며 프로젝트 간 검색은 허용하지 않는다.

## 검증

- 누적 smoke **355/355 PASS** (`run_all_checks.py --branch-context=all`).
- Python·Go knowledge lifecycle 각각 17/17, hub UI 15/15, Wiki 12/12.
- Hub core Python 20/20, Go 11/11; `go test ./...`, `go vet ./...`, 변경 Python 파일 Ruff 검사 통과.
- PostgreSQL adapter 검사와 SQLite 기본 스키마 검사 통과; migration V1~V13 및 Go 내장 정적 자산 동기화 3/3.
- GitHub 배포에는 wheel/sdist, Go 6개 OS/아키텍처 산출물과 `SHA256SUMS`를 포함한다. kit plugin ZIP은 포함하지 않는다.

## 운영 범위

- 이 판은 평가용 pre-release다. 운영 DB를 전환하기 전에 일관된 복제본으로 검증한다.
- 홈랩 pilot은 프로젝트 지식 검색·출처 검증·DCR 승인 권한과 ADR hash sync를 확인한다. 전체 Go/Python shadow parity 및 Windows/macOS native 실행은 별도 검증 범위다.
