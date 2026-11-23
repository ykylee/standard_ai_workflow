# Beta v3.0.1 — Go 허브 Windows DSN 수정 및 Python fallback (2026-11-23)

> **상태: 실환경 pilot용 pre-release.** GitHub Release 는 prerelease로 표시하고 안정판 latest 는 v2.1.0에 둔다. Go/Python parity가 완료되지 않았으므로 두 런타임 모두 운영 DB에 연결하지 말고 일관된 복제본에서 평가한다.

## 변경

- Go SQLite DSN이 Windows 드라이브 절대 경로를 `file:///C:/...` URI로 연다. 이전 `v3.0.0`은 `file:C:/...` 상대 URI를 만들 수 있어 Windows에서 DB를 잘못 찾거나 열지 못했다.
- Python 허브를 fallback 런타임으로 함께 제공한다. wheel의 `[hub]` extra와 `python -m workflow_kit hub serve --db <복제본>` 경로를 쓴다. Python은 SQLite 파일 경로를 직접 전달하므로 Go URI 경로 변환을 거치지 않는다.
- wheel/sdist, Linux · macOS · Windows × amd64 · arm64 Go 바이너리 6종 및 `SHA256SUMS`를 제공한다. kit plugin ZIP은 포함하지 않는다.

## 검증

- 누적 smoke **353/353 PASS** — 3.0.1 준비 커밋의 `--branch-context=all` 전량 게이트로 확인한다.

- Windows 경로 DSN 단위 회귀, `go test ./...`, Windows amd64/arm64 cross-build: PASS.
- clean commit 기준 양 문맥 전량 smoke **353/353 PASS**.
- Linux의 실제 릴리스 바이너리와 Python 허브는 각각 별도 consistent DB clone에서 HTTP smoke 한다. Windows native 실행은 Linux cross-build만으로 입증되지 않으며, 실제 Windows 호스트 검증은 남는다.
- 이전 3.0.0 shadow 결과: GET status 23/23 일치, body 14/23 일치. 화면 write 및 relay DB-effect parity는 미측정이다.

## 운영 범위

- Go/Python 어느 쪽도 운영 DB 전환용으로 승인된 판이 아니다. 평가할 때 각 서버에 독립된 DB 복제본을 준다.
- 3.0.0은 Windows DSN 결함이 있는 pre-release로 남는다. Windows 테스트에는 3.0.1 이상을 쓴다.
- macOS · Windows native 실행, 하네스 4종 실측, same-DB rollback은 계속 후속 검증 항목이다.
