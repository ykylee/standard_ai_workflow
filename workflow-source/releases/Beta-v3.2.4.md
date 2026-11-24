# Beta v3.2.4 — Origin을 바꾸는 프록시 뒤 계정 로그인 (2026-11-24)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- 3.2.3의 출처 수리는 홈랩에서 듣지 않았다. 실측한 원인은 프록시가 자기 호스트의 `Origin`을 `https`에서 `http`로 바꾸는 것이었다. 공개 호스트의 다른 scheme은 브라우저가 붙이는 `Sec-Fetch-Site: same-origin`이 함께 있을 때만 받는다. 다른 사이트의 요청은 계속 거절한다.

## 검증

- 누적 smoke **357/357 PASS**
- 홈랩 프록시가 실제로 넘긴 헤더 조합을 `check_hub_ui` case 17이 Python·Go 허브에서 재현한다.

## 운영 범위

- 평가용 pre-release다. DB 판은 17 그대로다. 서비스 교체 전 백업한다.
