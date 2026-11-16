# Beta v1.26.0 (2026-11-16)

> **상태: 릴리스 준비.** package `1.26.0`, runtime `__version__ = 1.26.0`, tag `v1.26.0`.
> **minor release** — 워크벤치 todo(브랜치 할 일 · task 체크리스트) · 응답 자동 반영 hook + 수리 넷(대시보드 drift 가드 값 둘 · release 재검사 집계 · 워크벤치 글자 넘침).
>
> 등급 근거 (§1.5): v1.25.0 이후 코드 커밋 feat 2 · fix 4 · breaking 0 — **minor**.
> 공개 Python API 시그니처 제거 0, 진입점 제거 0. 새 명령 `todo`, `plan-import --hook`, 워크벤치 경로 `POST todo`, `api/state` 의 `todo`,
> 플러그인 hook 두 개(`PostToolUse` · `UserPromptSubmit`)는 **추가**다. 대시보드 drift 패널의 `guard_cases` · `guard_pass` · `guard_fail` 은
> 가드를 돌리지 않았거나 돌지 못했을 때 0 대신 **null** 이다(§2.4 · §2.5) — 0 을 실측으로 읽던 소비자는 null 을 '미측정 · 측정 실패' 로 다뤄야 한다.

## 0. 릴리스 판정

v1.25.0 이후 6커밋(발행 · 정리 제외)이다. 소유자 지시 둘 — "워크벤치에서 응답을 보냈는데 바로 확인을 못한다" 와 "워크벤치에서 todo 도 표시하고 관리" —
을 기능으로 넣었고, 소유자가 다른 환경에서 본 글자 넘침과 대시보드 · release 의 측정 값 결함 셋을 고쳤다.

## 1. 릴리스 요약

- 범위: `v1.25.0..` 발행 준비 직전까지 **6 commit** — feat 2 · fix 4 (+ 발행 완료 1).
- 누적 smoke **329/329 PASS** (로컬 `--branch-context=all` = 329 × native/slash, 발행 준비 커밋에서 실행).
- 검사 수 325 → 329 (새 검사 파일 4 — `check_drift_guard_parse` · `check_workbench_inbox_hook` · `check_todo_list` · `check_workbench_todo`).

## 2. 소비자에게 보이는 변화

### 2.1 워크벤치 todo — 브랜치 할 일 · task 체크리스트 (`78b66be9`, spec §13 · §13.1)

- 진척 화면 맨 위에 **할 일**(아직 task 가 아닌 일), 계획 카드 · 작업 보드에 `todo n/m`, 계획 화면에 그 task 의 **체크리스트**.
  추가 · 끝냄 · 고침 · 삭제를 브라우저에서 바로 한다(approver · 개방 모드). viewer 는 읽기만.
- 저장은 `<branch>/todo.md` 하나다 — task 파일 밖이라 "task 파일은 작업 세션만 쓴다"(ADR-032 결정 15)는 그대로다 (V11).
  쓰기는 `.todo/lock` 아래 읽기 → 적용 → 원자 교체 — 워크벤치와 작업 세션이 동시에 써도 항목을 잃지 않는다.
- 작업 세션 쪽 명령: `python -m workflow_kit todo` (목록 · `--add "…" [--task <ID>]` · `--done` · `--undo` · `--edit --text` · `--remove`).
- 소유자가 브라우저에서 바꾸면 다음 hook(§2.2)이 "누가 · 무엇을 · 어느 항목" 을 한 번 알린다. 작업 세션의 CLI 변경은 알리지 않는다.
- 글은 한 줄 1~300자. 제어 문자 · 줄 구분자(U+2028 · U+2029) · 양방향 제어 문자는 거절한다 — 파일 줄이 쪼개지거나 화면 글이 뒤집혀 보이지 않게.

### 2.2 워크벤치 응답 도착 신호 + 작업 세션 hook 자동 반영 (`4dba0962`, spec §6.1)

- 서버가 응답을 받으면 `.workbench/inbox.stamp` 에 새 표식을 쓰고, Claude Code 플러그인의 `PostToolUse` · `UserPromptSubmit` hook 이
  표식이 바뀌었을 때만 `plan-import --hook` 을 불러 **반영(`--apply`)하고 결과를 모델 컨텍스트에 알린다**. 바뀌지 않았으면 Python 을 띄우지 않는다.
- 계획 화면에 응답마다 '반영 대기 → 반영됨'. 서버는 여전히 task 파일을 쓰지 않는다 — 반영은 작업 세션의 hook 이 한다 (ADR-032 V10).
- 설치된 kit 이 이 기능을 모르면 hook 은 한 번만 알리고 조용해진다.

### 2.3 워크벤치 글자가 박스를 넘던 결함 (`c5cc35d0`)

- 긴 글 · 좁은 폭 · 다른 글꼴에서 카드 · 보드 · 배지의 글자가 박스를 넘었다. 넘침 방지 바탕 규칙과 3줄 clamp(전문은 `title`), 배지는 자르지 않고 줄바꿈.
- 정적 자원 링크에 내용 지문 `?v=` — 바뀐 CSS 를 브라우저 캐시가 가리지 않는다.

### 2.4 대시보드 drift 패널 — 가드를 돌리지 않았는데 `guard_cases 7 · pass 0` 을 싣던 결함 (`b82944d8`)

- `inline_guard=False` 이면 센 값은 null · `guard_measured=false` · 렌더 '미측정'.

### 2.5 대시보드 drift 패널 — 가드가 돌지 못하면 '0/0 pass' 로 그리던 결함 (`8640b4c0`)

- 가드 파일 없음 · 시간 초과 · 실행 실패 · 빈 출력이면 센 값 null · `guard_error` 사유 · 렌더 '측정 실패 — 사유'.

### 2.6 release self-recover 재검사 집계 `cases_pass 7 > cases_total 6` (`4b18a68e`)

- drift 가드 출력 해석을 `parse_drift_guard_output` 하나로 모았다(release 재검사 · 대시보드 · `release_v0_13_0` preflight). case 수 리터럴을 지웠다.

## 3. 검증

- **전량 게이트** `--branch-context=all` — native 329/329 · slash 329/329 · rc 0. 발행 준비 커밋의 clean tree 에서 실행하고,
  결과는 게이트 증거 파일(`<git common dir>/gate_evidence/<sha>.json`)에 남는다.
- **커밋 전** `--changed` 게이트 · **스모크** `check_self_application` 8/8 rc 0.
- task 마다 verifier PASS 뒤에 닫았다 — 7건(main-011 ~ main-017). verifier 가 실측으로 찾은 결함은 커밋 전에 고쳤다: todo 글의 C1 제어 문자 ·
  줄 구분자가 파일 줄을 쪼갬 · 동시 쓰기 검사가 락 제거를 거의 못 잡음(출발 장벽으로 고정) · 없는 브랜치 디렉터리 생성 · `back` 끝 줄바꿈 ·
  같은 초의 두 번째 응답을 놓치는 mtime 신호(내용 표식으로) · 옛 kit 에서 조용히 아무것도 안 하는 hook · rc 0 빈 출력을 통과로 읽음.
- 브라우저 동작(todo 조작 · 자동 새로고침 · 글자 넘침)은 헤드리스 Chrome + CDP 로 쟀다 — 게이트는 브라우저를 띄우지 않는다.
- 발행 호스트: Linux.

## 4. 알려진 한계 (감추지 않는다)

- **Claude Code 가 hook JSON 을 실제로 모델 컨텍스트에 넣는지는 미측정이다** — hook 명령의 출력 형식 · 셸 동작은 검사가 재지만,
  하네스의 주입은 플러그인 갱신 · 재시작 뒤 워크벤치 응답을 하나 보내 확인해야 한다. 다른 하네스(Codex · Grok)의 hook 처리도 미측정이다.
- **Windows 실측은 이번 판에도 없다** (M-028/WBS-28.3). hook 셸 명령 · todo 락(`msvcrt`) · 워크벤치는 Linux 에서만 쟀다 — 미측정이다.
- todo 의 '쓰는 중이면 새로고침 보류' 와 '고치기' 펼침 넘침은 게이트가 재지 않는다 — 스크립트 분기 존재만 게이트에 있고 실동작은 CDP 실측이다.
- todo 를 task 로 승격하는 동작은 없다 — 작업 세션이 `backlog-update` 로 만든다.
- release self-recover 재검사의 오류 경로는 아직 `cases 0` 을 싣는다 — 후속.
- **case 수 선언 대조 축은 컨텍스트마다 83건이 미측정**이다(개수 선언 없음 79 · case 줄 없음 4, native · slash 합계 166) — 통과가 아니다.
- **PyPI 업로드는 하지 않는다**(§1 각주 0 — 2026-08-14 소유자 최종 결정). 배포는 GitHub Releases 하나다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-11-16T15:18:07Z)_

- total wiki pages: **99**
- total memory entries: **30**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
