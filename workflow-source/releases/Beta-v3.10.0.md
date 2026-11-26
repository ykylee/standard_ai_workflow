# Beta v3.10.0 — 신호 끊긴 세션 만료, 끝난 세션 따로 보이기 (2026-11-26)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- **신호 끊김 24시간 만료**: 하네스가 `hub_session_end` 없이 죽으면 그 세션이 목록에 '신호 끊김' 으로 영영 남았다. 마지막 신호가 24시간을 넘으면 허브가 세션을 `ended` 로 바꾼다 — 세션 목록 · 받은편지함을 읽을 때 판정한다. 이력에 `expire`(허브) 를 남기고, 그 세션이 맡던 배정은 `session_expired` 로 오케스트레이터에게 돌아간다. 만료된 세션의 이후 호출은 410 `session_ended` — 세션 시작으로 새 세션을 연다. 15분 뒤 '신호 끊김' 표시는 그대로다.
- **세션 보기에 끝난 까닭**: `hub_session_list` 의 세션에 `ended_at` · `end_reason`(`ended` 스스로 끝냄 · `expired` 만료 · 끝나지 않았으면 null) 이 실린다. Python · Go 같다.
- **끝난 세션 따로 보이기**: 오케스트레이션 화면의 세션 표는 살아 있는 세션만 보인다. 끝난 세션은 접힌 '끝난 세션 N' 묶음에 '끝냄' · '신호 끊겨 만료' 와 끝난 때를 함께 둔다. 이력 화면은 `expire` 를 '만료' 로 읽는다.

## 검증

- 누적 smoke **362/362 PASS**
- `check_hub_orch` case 13 · Go `TestSessionExpireAfterSilence` — 23시간 그대로 · 25시간 만료 · 배정 되돌림 · 410 · 스스로 끝냄은 `ended`. 되주입 5건 red.
- `check_hub_screens` 109/109 — Python · Go 실제 Chrome 렌더, 끝난 세션 묶음 case 추가.

## 운영 범위

- **DB 판은 22 그대로다** — 3.9.2 로 되돌릴 때 실행 파일만 바꾸면 된다(만료로 `ended` 가 된 세션은 그대로 남는다).
- 배포하면 24시간 넘게 신호 없는 세션이 첫 조회 때 한꺼번에 만료된다. 홈랩 배포 전 실측: 2건, 그 세션의 열린 배정 0건.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-11-26T11:57:45Z)_

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
