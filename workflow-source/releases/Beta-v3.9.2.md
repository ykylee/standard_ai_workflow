# Beta v3.9.2 — PC 중계 화면 재정비, 워크벤치 동결, 허브 승인 카드 (2026-11-26)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- **PC 중계 '종료' 가 VS Code 안에서 동작한다**: 실제 VS Code 1.148(test-electron · xvfb)에서 재 보니 webview 의 iframe sandbox 에 `allow-modals` 가 없어 `confirm()` 이 즉시 false 였고 '종료' 는 아무 요청도 보내지 않았다. 같은 자리를 두 번 누르는 확인으로 바꿨다(6초 안에 '정말 종료').
- **중계 화면 한 벌**: 화면이 `workflow_kit/relay/static/relay.{html,css,js}` 정적 파일 하나가 되고 Go 중계는 같은 바이트를 내장한다. 색 값은 허브와 같다. 상태를 두 번 연속 못 받으면 `aria-live` 경보 · 상태 '확인 안 됨' · 마지막 확인 시각을 보인다. 세션 수는 도는 세션만 센다(화면 · 상태 표시줄), 끝난 세션은 접는다, 상태는 한국어. 640px 아래는 카드형 줄, 한국어는 어절로 꺾는다.
- **VS Code 테마를 따른다**: 확장이 테마 종류를 `?theme=` 로 넘기고 테마가 바뀌면 다시 그린다 — webview 안의 `prefers-color-scheme` 는 VS Code 테마를 따르지 않았다(실측).
- **워크벤치 동결**: 결정 라디오를 미리 고르지 않는다 — 기본값이 골라져 있어 펼쳐 보지 않은 결정에도 값이 실려 나갔다. 열린 결정을 다 고르기 전에는 '응답 보내기' 가 꺼지고, 추천값은 '추천 받아들이기' 단추로만 고른다. 서버도 고르지 않은 결정을 422 로 거절한다. 허브로 옮긴 저장소에서는 머리에 '정본은 허브' 안내와 허브 링크가 붙는다. 색 값만 허브와 같게 맞췄다(작은 칩 대비 4.5 이상).
- **허브 승인 카드는 사람 말 먼저**: "<요청자> 가 <PC> 에서 <하네스> 세션을 띄우려 한다" 가 제목이고 요청 · PC · 세션 ID 는 보조 줄이다. 승인 대기가 있으면 오케스트레이터 제어보다 위에 온다. '오케스트레이터 내려놓기' 는 확인을 묻는다. task 전체 주석 칸에 보이는 이름표, DCR 목록의 '결정 대기' 중복 · 확인 요청 머리의 빈 띠를 없앴다.

## 검증

- 누적 smoke **362/362 PASS**
- `check_relay_screen`(신규) 16/16 — 900 · 520 · 390px × 밝음/어두움, 두 번 누름 · 연결 끊김 경보 · 주 단추 대비. 되주입 8건 red.
- `check_workbench_decide`(신규) 5/5 — 실브라우저로 처음 무선택 · 보내기 꺼짐 · 하나만 고르면 여전히 꺼짐 · 다 고르면 POST 1. 되주입 7건 red.
- `check_hub_screens` 107/107 — Python · Go 실제 Chrome 렌더. 승인 카드 문구 · 순서, 결정 단추 두 번 누름(POST 1 · 두 단추 꺼짐) case 추가. 되주입 6건 red.
- 실제 VS Code 1.148.0 실측: 두 번 누름 종료 POST · 어두움 → 밝음 테마 전환 · 상태 표시줄 '중계 1/3'.

## 운영 범위

- **DB 판은 22 그대로다** — 3.9.1 로 되돌릴 때 실행 파일만 바꾸면 된다.
- 중계 화면의 일시정지 실패 메시지 · '오케스트레이터 내려놓기' 확인창의 '취소' 쪽은 브라우저 case 가 없다. macOS · Windows VS Code 는 재지 않았다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-11-26T11:25:38Z)_

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
