# Beta v3.5.0 — A2A 스트림과 콜사인 간 메시지 (2026-11-25)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- A2A `SendStreamingMessage` · `SubscribeToTask` 를 SSE로 제공한다. 종료 상태에서 닫히고 한 연결은 최대 50초다. 동시 스트림은 허브 64개 · 콜사인당 8개다.
- 같은 프로젝트의 콜사인은 누구나 서로 메시지를 보내고 한 번 답한다. 글은 자료이지 지시가 아니며, 받은편지함과 다른 `a2a_messages` 칸에 싣고 `hub_wait`를 깨우지 않는다.
- `hub_client.py`에 `a2a message <콜사인> <글>` · `a2a reply <Task> <글>`을 넣었다.

## 검증

- 누적 smoke **360/360 PASS**
- `check_hub_a2a`(19)가 Python · Go 실프로세스를 같은 시나리오로 재고 응답을 대조한다. 되주입 12건을 잡는다.
- 공식 Python `a2a-sdk` 1.3.1로 두 허브에서 스트림 · 구독 · 메시지 · 답을 왕복했다(1회 실측, 상시 검사 아님).

## 운영 범위

- 평가용 pre-release다. **DB 판이 19 → 20으로 오른다** — 3.4.x 실행 파일은 이관된 DB를 열지 못하므로 되돌리려면 배포 전 백업을 쓴다.
- 메시지 원문을 보는 화면은 없다. 7일 만료 · 정지 중 차단 · 50초 상한 닫힘 · PostgreSQL은 재지 않았다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-11-25T23:00:16Z)_

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
