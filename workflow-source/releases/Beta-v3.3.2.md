# Beta v3.3.2 — 승인받은 에이전트의 프로젝트 문서 쓰기 (2026-11-24)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- 프로젝트 문서(`purpose` · `profile`)를 사람이 로그인 승인하면 에이전트가 쓸 수 있다. 실행 승인 `project_doc_put`은 콜사인 · 문서 · 판 · 본문 sha256에 묶이고 24시간 안에 한 번만 쓴다.
- 확인 요청 화면이 허브가 보관한 본문과 그 판의 줄 단위 차이를 보인다. 설명은 에이전트가 쓰지만 차이는 허브가 계산한다.
- `hub_client.py doc request|put`을 더했다.
- A2A Task의 상태에는 문서 본문을 싣지 않는다(sha256만).

## 검증

- 누적 smoke **358/358 PASS**
- `check_hub_migrate` case 11이 Python · Go 모두에서 승인 없음 · 대기 · 다른 콜사인 · 본문 · 판 · 문서 · 재사용 · 판 충돌 · 비밀을 잰다. 실제 브라우저로 승인 화면과 쓰기 왕복을 확인했다.

## 운영 범위

- 평가용 pre-release다. DB 판은 18 그대로다.
- 결정 응답 · DCR 결정 · 콜사인 승인 · 소유자 변경은 여전히 사람만 한다.
