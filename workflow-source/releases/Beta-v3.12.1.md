# Beta v3.12.1 — 화면 재채점 P2 · P3 (2026-11-26)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

화면 재채점(3.10.0 기준, 위키 `queries/ui-rescore-2026-11-26-3.10.0.md`)에서 남은 허브 · PC 중계의 P2 · P3 를 닫는다. 워크벤치는 동결 화면이라 뺐다.

### 허브

- **마일스톤 순서 하나**: 진척 띠와 로드맵 화면이 같은 정렬(현재 → 진행 중 → 나머지, 같은 무리 안은 로드맵 순서)을 쓴다. 전에는 띠가 로드맵 문서 순서라 두 화면의 순서가 달랐다.
- **DCR 이름 하나**: '결정 변경' · '결정 변경 기록' · '결정 변경(DCR)' 이 섞여 있던 것을 `결정 변경(DCR)` 으로 맞췄다(목록 화면은 `결정 변경(DCR) 기록`). 휴대폰 아래 막대의 좁은 칸만 `DCR 기록` 으로 줄이고 전체 이름은 title 에 둔다.
- **'지금' 이 비면 다음 필터로**: 기본 필터(막힘 · 진행 중)가 0건이면 '예정'(그것도 없으면 '끝남')으로 떨어지고 그렇게 했다고 알린다. 분류 필터를 고른 때는 그대로 둔다.
- **단추 44px**: 넓은 폭에서 37px 이던 단추가 모든 폭에서 44px 이상이다.
- **용어집**: 개요뿐 아니라 결정 · 오케스트레이션 · 로드맵 머리에서도 연다.
- **현재 마일스톤 이름표**: 진척 띠의 현재 칸이 '현재 마일스톤 · …' 으로 읽힌다.

### PC 중계

- **종료 안내 · 결과 위치**: 화면 맨 위가 아니라 누른 종료 단추가 있는 세션 표 바로 아래에 뜬다.
- **실패 문구**: HTTP 코드만이 아니라 다음 행동을 앞에 쓴다(닿지 않음 → 중계가 도는지 확인, 403 → 새로고침, 404 종료 → 이미 끝남 · 할 일 없음, 5xx → 로그 보고 다시). 코드는 괄호 보조.
- **'대기' 칩 중립색**: 허브의 같은 상태와 같은 색. 초록은 성공에만.
- **세션 상한을 말로**: `띄운 세션 3 / 3` → `띄운 세션 3개 · 이 PC 상한 3개`.

## 검증

- 누적 smoke **362/362 PASS**
- `check_hub_screens` 137/137(Python · Go 허브, Chrome) · `check_relay_screen` 25/25(900 · 520 · 390px, 밝은 · 어두운). 새 case 마다 되주입 red 확인.

## 운영 범위

- **서버 API · DB 판(22) 변경 없음** — 정적 화면 파일만 바뀐다. 3.12.0 으로 되돌릴 때 실행 파일만 바꾸면 된다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-11-26T23:33:44Z)_

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
