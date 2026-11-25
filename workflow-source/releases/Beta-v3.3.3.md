# Beta v3.3.3 — 로드맵 · 오케스트레이션 화면 수리 (2026-11-25)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- 로드맵 화면이 마일스톤 카드 대신 `[object HTMLElement]`만 보이던 결함을 고쳤다. 2.1 화면(M-053) 때부터 있었다.
- 로드맵은 열린 마일스톤을 먼저 보이고 완료한 것은 접는다. 자동 갱신이 펼친 접기를 닫지 않는다.
- 오케스트레이션 화면이 미확인 메시지의 내용을 보인다. 권한 안내에 허브 계정 로그인을 적었다.
- Go 허브가 문자열 본문 메시지가 있으면 오케스트레이션 화면을 열지 못하던 결함을 고쳤다.

## 검증

- 누적 smoke **359/359 PASS**
- 새 `check_hub_screens`가 14개 화면을 Chrome으로 그려 Python · Go 허브에서 잰다. `[object …]`, JS 오류, 빈 내용, 계정 로그인 소유자의 오케스트레이션 조작을 잡는다. Chrome이 없으면 미측정으로 알린다.

## 운영 범위

- 평가용 pre-release다. DB 판은 18 그대로다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-11-25T01:13:24Z)_

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
