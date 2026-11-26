# Beta v3.8.0 — 아이디어 박스 I2 · I3, 온보딩 에이전트의 지식 원본 등록 (2026-11-26)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- **아이디어 ↔ 이미 있는 task**: `hub_idea_reply` 가 `task_id`(그 프로젝트의 task) · `related_ideas`(5개 이하)를 받는다. 사람 처리 `link` — 화면 "이 task 로 처리" — 가 새 task 없이 아이디어를 그 task 에 묶어 adopted 로 닫는다.
- **I2a 회신 도착 알림**: 사람이 아직 안 본 회신을 목록 칩 · 목록 머리 · 프로젝트 개요("아이디어에 새 회신 N건") · 요약 `ideas_unread` 에 보인다. 아이디어를 열면 읽음(`seen`)이 되고 판은 그대로다.
- **I2b 비슷한 아이디어**: 적기 응답과 상세가 글자 3-gram Jaccard × 100(정수) 30 이상인 기존 아이디어를 최대 3건 싣는다.
- **I3 검토 전용 세션**: `hub_session_start(session={kind: "worker", review_ideas: true})` 세션은 배정이 없을 때 `hub_wait` 가 검토 대기 아이디어를 `{kind: "idea_review", idea_id}` 로 준다.
- **지식 원본 등록**: 에이전트가 `hub_approval_request(action={type: "knowledge_source_register", source_id, repo_key, allowlist})` 로 요청하고 소유자가 확인 요청 화면에서 경로 목록을 보고 승인하면, 같은 인자 + `approval_id` 로 직접 등록한다(요청 콜사인 · 24시간 · 한 번). 같은 저장소의 두 번째 원본은 500 대신 `409 source_exists_for_repo`.

## 검증

- 누적 smoke **360/360 PASS**
- `check_hub_ideas` 66/66 — Python · Go 응답 대조, 실제 Chrome 으로 새 회신 알림 · 열면 읽음 · "이 task 로 처리". 되주입 7건 red.
- `check_hub_knowledge` Python · Go 각 22/22 — 승인 없는 에이전트 403 · 대상 다르면 403 · 승인 뒤 등록 · 승인 used · 같은 저장소 409. `check_hub_screens` 69/69 — 원본 등록 승인 카드. 되주입 4건 red.

## 운영 범위

- **DB 판이 21 → 22로 오른다** (`idea.seen_seq` · `session.review_ideas`) — 3.7.x 실행 파일은 이관된 DB를 열지 못하므로 되돌리려면 배포 전 백업을 쓴다.
- 검토 전용 세션을 상시로 둘지는 운영 선택이다 — 떠 있는 동안 사용량이 든다. 지식 원본의 허용 목록을 늘리는 길은 아직 없다.
