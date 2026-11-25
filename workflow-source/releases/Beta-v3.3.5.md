# Beta v3.3.5 — 남은 승인 화면 · 받은편지함 · 비밀번호 경계 수리 (2026-11-25)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- Go 허브의 지침 화면이 제안의 차이를 항상 "(차이 없음)"으로 보이던 결함을 고쳤다.
- 세션 승인 · 지침 제안 · 미확인 메시지도 보이지 않는 문자를 드러내고, 저장된 글자 순서와 공백 그대로 보인다.
- 본문이 문자열 · 배열인 메시지가 있어도 받은편지함을 나열 · 확인한다(Go 500, Python 승인 메시지 500 수리).
- 비밀번호를 엉뚱한 인자 자리에 줘도 관리 명령(`admin`)의 오류문이 값을 되뇌지 않는다. 잘못된 UTF-8을 거절한다.
- 로그인 확인과 세션 열기 사이에 재설정이 끼면 옛 비밀번호로 세션이 열리지 않는다.
- 지침 차이가 끝 줄바꿈 변경까지 보인다. 객체가 아닌 본문의 메시지가 확인 요청 화면을 막지 않는다.

## 검증

- 누적 smoke **359/359 PASS**
- 지시문 · 메시지 · 지침 제안의 문자 표시, 글자 순서 규칙, 정리 안내문을 Chrome에서 Python · Go 허브로 잰다. 남의 콜사인의 정리 거절을 두 런타임에서 잰다.

## 운영 범위

- 평가용 pre-release다. DB 판은 18 그대로다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-11-25T07:41:21Z)_

- total wiki pages: **104**
- total memory entries: **30**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
