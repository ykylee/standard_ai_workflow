# Beta v3.2.2 — 사람 계정 · 확인 요청과 Go 셋업 확인 (2026-11-24)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다. Go 허브에는 아직 미포팅 도구가 남아 있다.

## 변경

- 승인된 사람 콜사인 토큰으로 1회 등록한 뒤 계정으로 로그인하고, 연결된 프로젝트에서 에이전트 확인 요청을 웹에서 승인·거절한다. 결과는 A2A 받은편지함으로 전달한다. DB 판 16.
- Go 허브에 `hub_setup_confirm`을 구현했다. 3.2.1까지는 이 도구가 501을 반환해 `hub_client.py bootstrap`이 Go 허브에서 끝나지 않았고, 등록된 콜사인의 토큰이 저장되지 않았다.
- Go `hub_setup_plan`의 gitignore 단계가 `relay`·`legacy_1x`를 고정값으로 돌려주던 것을 고쳤다.
- Go 허브에 `hub_wiki_get`·`hub_wiki_list`·`hub_wiki_search`를 구현했다. 화면과 MCP가 같은 읽기 함수를 쓴다. 이 과정에서 index 절 순서와 제목 fallback의 Python 불일치도 고쳤다.
- Python `hub_setup_confirm`이 `.mcp.json`이 아닌 승인 프로필 설정 파일을 확인하지 못해 셋업이 완료되지 않던 결함을 고쳤다.
- 관리자 로그인 직후 상단 링크가 "관리자 로그인"으로 남던 것을 고쳤다.

## 검증

- 누적 smoke **357/357 PASS**
- `check_hub_bootstrap`이 Python과 Go 허브를 모두 잰다 (14/14).
- 홈랩 DB 사본에서 Wiki 읽기 응답 134건을 Python/Go 대조: 불일치 0.
- Chrome으로 관리자 비로그인·로그인·유효 토큰 복원·거둔 토큰 정리를 확인했다.

## 운영 범위

- 평가용 pre-release다. Go에서 미포팅 도구(1.x 이관, 프로젝트 이전, handoff·checkpoint·memory entry, Wiki 가져오기·내보내기·lint, relay 초대 MCP)는 `not_implemented_in_go`를 반환한다.
- 3.2.1 이하에서 시작하면 DB 판 15 → 16 migration이 실행된다. 시작 전에 백업한다.
