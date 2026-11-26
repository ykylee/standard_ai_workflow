# Beta v3.6.1 — 아이디어 'task 로 등록' 의 WBS 면제 사유 (2026-11-26)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- 아이디어 회신 초안(`hub_idea_reply` 의 `draft`)이 `wbs_exempt_reason` 을 받는다. `wbs` 가 `exempt` 인데 사유가 없으면 회신 때 400 으로 거절한다 — 에이전트가 사람이 등록할 수 없는 초안을 남기지 않는다. Python · Go 같다.
- 화면의 'task 로 만들기' 가 초안의 면제 사유로 칸을 채운다. WBS 가 `exempt` 인데 사유 칸이 비면 보내지 않고 그 칸을 가리킨다.
- WBS 게이트 거절(`exempt_reason_required` · `wbs_required` · `wbs_ref_format`)을 화면의 칸 이름으로 말한다 — 전에는 CLI 옵션(`--wbs-exempt-reason`)으로 설명했다.

## 검증

- 누적 smoke **360/360 PASS**
- 운영 DB 사본을 Go 3.6.0 으로 띄워 결함을 재현했다(422 `gate_denied` · `exempt_reason_required`).
- `check_hub_ideas` 가 활성 로드맵(게이트가 서는 조건)에서 Python · Go 를 같은 시나리오로 잰다. 실제 Chrome 으로 사전 확인 · 화면용 문구 · 사유가 채워진 등록을 잰다. 되주입 5건(Python · Go 초안 검증, 사전 확인, 문구, 칸 채우기)이 각자의 case 만 red.

## 운영 범위

- DB 판은 21 그대로다. 이미 저장된 사유 없는 exempt 초안은 화면에서 사유 칸을 채워 등록한다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-11-26T02:40:34Z)_

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
