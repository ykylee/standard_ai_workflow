# Beta v3.0.2 — MCP 2026-07-28 최신 프로토콜 전환 (2026-11-23)

> **상태: prerelease 파일럿.** Go 허브 parity와 플랫폼 실측은 진행 중이다. 운영 DB에 연결하지 말고 격리된 복제본에서 평가한다. v3.0.1 릴리스 파일은 변경하지 않는다.

## 변경

- Go 허브 HTTP MCP endpoint가 modern `server/discover`, 2026-07-28 protocol metadata, routing headers와 modern error mapping을 지원한다. 기존 initialize 기반 요청은 호환 경로로 유지한다.
- Python read-only stdio JSON-RPC bridge와 MCP SDK 기반 내부 클라이언트·검사도 modern lifecycle을 사용하도록 전환한다. Python MCP SDK 최소 버전은 2.3.0이다.
- modern/legacy 요청 fixture, 통합 검사, 프로토콜 운영 문서를 함께 갱신했다.
- 3.x 릴리스 자산: Python wheel/sdist, Linux · macOS · Windows × amd64 · arm64 Go 바이너리 6종, `SHA256SUMS`.

## 검증

- 누적 smoke **354/354 PASS** — clean release commit의 `--branch-context=all` 게이트로 확인한다.
- Go `go test ./...` 및 `go vet ./...` 통과.
- MCP SDK 2.3.0 기반 프로토콜 매트릭스 20/20, bootstrap round-trip 5 harnesses, hub core 20/20 통과.
- 홈랩 파일럿에서 `Client(mode="auto")`가 `2026-07-28`을 협상하고 도구 6개를 조회함을 확인했다.
- Windows/macOS native 실행과 Go/Python 전체 parity는 아직 완료되지 않았다.

## 운영 범위

- 이 prerelease는 평가용이다. 현재 Go/Python parity 미완료 상태이므로 운영 DB를 사용하지 않는다.
- v3.0.1은 기존 공개 릴리스 그대로 유지한다. modern protocol build는 v3.0.2 asset으로 배포한다.
- 다음 단계는 격리된 홈랩 DB와 `/workflow` reverse-proxy 경로에서 HTTP health 및 MCP round-trip 확인이다.
