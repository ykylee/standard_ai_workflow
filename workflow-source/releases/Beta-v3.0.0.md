# Beta v3.0.0 — Go 허브 pre-release pilot (2026-11-23)

> **상태: 실환경 pilot용 pre-release. 안정판으로 쓰지 않는다.** GitHub Release 는 prerelease로 표시하고
> `latest` 는 v2.1.0에 둔다. 소유자 지시에 따라 M-057 S2 parity 완료 전에 제한 배포한다.
> Go/Python shadow에서 차이가 확인됐으므로 운영 중인 DB에 연결하지 말고, 실제 Linux 호스트에서 일관된 DB 사본으로 평가한다.

## TL;DR

- Go 허브와 PC relay 구현, 화면 API, 오케스트레이션 경로를 포함한다.
- Python wheel/sdist와 Linux · macOS · Windows × amd64 · arm64 Go 바이너리 6종 및 `SHA256SUMS`를 제공한다.
- kit plugin ZIP은 포함하지 않는다. 3.x Go runtime release line의 산출물 정책을 따른다.

## 검증 결과

- `go test ./...` PASS · `go vet ./...` PASS.
- `check_go_assets_sync.py` 3/3 PASS · Go 허브 코어 실프로세스 11/11 PASS.
- 동일 online-backup DB snapshot의 Python/Go 격리 서버 GET 23개: HTTP status 23/23 일치, 본문 14/23 일치.
- JSON API 본문 14개 중 7개 일치. 남은 차이: root 안내 HTML, principal `project_id`, guide proposal diff, wiki 검색 snippet, wiki page body 및 orchestration principal.
- 화면 POST와 relay register/poll/result의 Python/Go DB 효과 비교는 미실행이다. S2 적합성 조건을 통과한 릴리스가 아니다.

## Pilot 범위와 제한

- Go 허브는 운영 DB와 분리된 일관된 사본에서 side-by-side로 실행한다. parity 차이가 남아 있는 동안 live DB로의 전환이나 쓰기 허용은 하지 않는다.
- Linux 호스트의 실제 서비스 구동·셋업·화면 흐름을 평가한다. macOS · Windows 실행, 4개 하네스 실측, 동일 DB Python rollback은 이후 검증 과제다.
- 평가 중 확인한 차이는 TASK-2026-11-23-main-005 및 TASK-2026-11-23-main-006에 기록한다.

## 패키지 검증

- 누적 smoke **353/353 PASS** — 이 pre-release 준비 커밋의 `--branch-context=all` 전량 게이트 결과로 확인한다.
- 자산 동기화 3/3 · Go 허브 코어 11/11 · Go unit/vet 통과.

## 이전 판

- v2.1.0 — Python 허브 안정판. 이 pilot 동안 GitHub `latest`를 유지한다.
