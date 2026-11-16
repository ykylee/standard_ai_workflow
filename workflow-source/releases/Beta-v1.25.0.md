# Beta v1.25.0 (2026-11-16)

> **상태: 릴리스 준비.** package `1.25.0`, runtime `__version__ = 1.25.0`, tag `v1.25.0`.
> **minor release** — 워크벤치 지속 갱신(화면 자동 새로고침 · 진척 실시간 값 · 작업 중 진행 기록) + 수리 둘(실제 브라우저의 폼 POST 403 · `--stop` pid 대조).
>
> 등급 근거 (§1.5): v1.24.0 이후 코드 커밋 feat 3 · fix 2 · breaking 0 — **minor**.
> 공개 Python API 시그니처 제거 0, 진입점 제거 0. 새 플래그 `workbench --refresh`, `api/state` 의 새 필드(`source` · `computed_at` ·
> `live_error` · `progress`), 실행 기록의 `instance` 는 **추가**다. `backlog-update --progress-note` 는 이제 시각을 앞에 붙인다(§2.4) —
> Progress 줄을 해석하는 kit 안의 소비자는 워크벤치 하나다.

## 0. 릴리스 판정

v1.24.0 이후 5커밋(발행 · 정리 제외)이다. 소유자 지시 "작업하면서 워크벤치의 내용을 지속적으로 갱신하면 좋겠다" 를 셋으로 나눠
구현했고(화면 자동 새로고침 · 실시간 값 · 진행 기록), 그 검증 중 **실제 브라우저에서 워크벤치 응답이 제출되지 않던 결함**(1.23.0 부터)을
헤드리스 Chrome 실측으로 찾아 고쳤다(§2.5). 1.24.0 노트 §4 의 `--stop` pid 대조 한계도 해소했다(§2.6).

## 1. 릴리스 요약

- 범위: `v1.24.0..` 발행 준비 직전까지 **5 commit** — feat 3 · fix 2 (+ 발행 · 정리 2).
- 누적 smoke **325/325 PASS** (로컬 `--branch-context=all` = 325 × native/slash, 발행 준비 커밋에서 실행).
- 검사 수 322 → 325 (새 검사 파일 3 — `check_workbench_refresh` · `check_workbench_live` · `check_workbench_progress`).

## 2. 소비자에게 보이는 변화

### 2.1 화면 자동 새로고침 — `workbench --refresh SECONDS` (`f2ed8112`, spec §4.5)

- 기본 5초, 0 이면 끈다. 진척 · 계획 화면이 같은 주소를 다시 받아 `<main data-version>` 지문이 바뀌었을 때만 본문을 갈아 끼운다.
  숨은 탭은 쉬고, 세션이 끝나 리다이렉트되면 따르지 않는다.
- 계획 화면에서 답을 쓰는 중(입력 · 결정 펼침)이면 갈아 끼우지 않고 "내용이 바뀌었다" 알림과 새로고침 단추만 낸다 — 쓰던 답과 `opened` 기록을 지킨다.
- CSP 에 `connect-src 'self'` 하나만 더했다.

### 2.2 진척 실시간 값 (`b2b025c8`, spec §7.1)

- CLI 서버는 진척 값을 `refresh-state` 와 **같은 생성기**로 원천(task · handoff · roadmap)에서 계산한다 — `refresh-state` 를 돌리기 전에도
  방금 바뀐 task 가 보인다. 생성기 출력은 임시 디렉터리에만 쓰고 저장소에는 아무것도 쓰지 않는다.
- 원천(메모리 디렉터리 · 프로필 · 마일스톤 산출물)의 stat 지문과 브랜치가 같으면 다시 계산하지 않는다 (이 저장소 계산 132ms · 캐시 17ms).
- 화면에 "실시간" 표식, `api/state` 에 `source`(live · generated) · `computed_at`. 계산할 수 없으면 생성물을 읽고 그 사유를 `live_error` · 화면 경고로 보인다
  (사유의 작업 공간 경로는 상대, 그 밖 절대 경로는 가린다).

### 2.3 작업 중 진행 기록 — 워크벤치 '지금 하는 일' (`0c2f7fee`)

- 계획 카드 · 작업 보드(진행 중 · 차단)에 task 파일의 `Progress` 한 줄을 시각과 함께 보인다. `api/state` 의 `progress {at, text}`.
- backlog-update 스킬 7단계 · 이 저장소 `CLAUDE.md` 에 규칙: 계획 → 구현 → 검사 → verifier → 커밋 · push 마다 `--progress-note` 로 기록한다.
  노트가 바뀌면 화면 지문이 바뀌어 §2.1 이 바로 갱신한다.

### 2.4 `backlog-update --progress-note` 에 시각 접두 (`0c2f7fee`)

- 노트 앞에 `` `YYYY-MM-DD HH:MM` `` 을 도구가 붙인다(create · update). 이미 그 꼴의 시각으로 시작하면 그대로 둔다.

### 2.5 실제 브라우저에서 워크벤치 응답 · 로그인 · 로그아웃이 403 이던 결함 (`0721103a`) — **1.23.0 · 1.24.0 사용자 영향**

- `Referrer-Policy: no-referrer` 아래에서 Chrome 은 폼 POST 에 `Origin: null` 을 싣고, 서버의 Origin 대조가 그것을 거절했다.
  검사 fixture 는 Origin 을 직접 실어 이 경로를 재지 못했다.
- 정책을 `same-origin` 으로 — 같은 출처 POST 는 실제 Origin 을 싣고, 다른 출처로는 referrer 가 나가지 않는다. `Origin: null` 은 계속 거절한다.
- 헤드리스 Chrome 실측: 개방 모드 응답, 토큰 모드 로그인 · 응답 · 로그아웃 모두 303. 옛 정책으로 되돌리면 같은 브라우저가 403 을 재현한다.

### 2.6 `workbench --stop` 의 pid ↔ 포트 주인 대조 (`d862b009`) — 1.24.0 §4 한계 해소

- 서버가 시작 때 무작위 `instance` 를 실행 기록에 쓰고 `healthz` 머리 `X-Workbench-Instance` 로 낸다. `--stop` 은 둘이 같을 때만 기록의 pid 를 내린다
  (pid 재사용 · 같은 포트의 다른 checkout 방어). `instance` 없는 옛 기록 + 옛 서버는 옛 판정으로 내린다 — 업그레이드 과도기의 자동 기동 서버도 SessionEnd 가 내린다.

## 3. 검증

- **전량 게이트** `--branch-context=all` — native 325/325 · slash 325/325 · rc 0. 발행 준비 커밋의 clean tree 에서 실행하고,
  결과는 게이트 증거 파일(`<git common dir>/gate_evidence/<sha>.json`)에 남는다.
- **커밋 전** `--changed` 게이트 · **스모크** `check_self_application` 8/8 rc 0.
- task 마다 verifier PASS 뒤에 닫았다 — 5건. verifier 가 실측으로 찾은 결함은 커밋 전에 고쳤다: 실제 브라우저 POST 403(별도 task) ·
  실시간 캐시의 브랜치 누락 · 조용한 fallback · roadmap 산출물 지문 · 낡은 roadmap 생성물 · 실패 사유의 절대 경로 · 진행 노트 이스케이프 검사 부재.
- 브라우저 동작(자동 새로고침 · 폼 제출)은 헤드리스 Chrome + CDP 로 쟀다 — 게이트는 브라우저를 띄우지 않는다.
- 발행 호스트: Linux.

## 4. 알려진 한계 (감추지 않는다)

- **Windows 실측은 이번 판에도 없다** (M-028/WBS-28.3). 자동 기동 · `--stop` 의 Windows 경로, 응답 파일의 `os.link` 공개 · 잠금,
  워크벤치의 포트 bind · 토큰 파일 모드 · 콘솔 인코딩은 Linux 에서만 쟀다 — 미측정이다.
- 실시간 계산은 요청을 직렬화한다(캐시 잠금을 쥔 채 계산, 이 저장소 132ms) — 원천이 바뀐 직후의 동시 요청은 순서대로 기다린다.
- 자동 새로고침의 브라우저 동작은 게이트가 재지 않는다 — 스크립트의 분기 존재와 서버의 지문만 게이트에 있고, 실동작은 task Proof 의 CDP 실측이다.
- 진행 기록은 에이전트가 규칙대로 남길 때만 보인다 — 남기지 않으면 '지금 하는 일' 은 마지막 노트 그대로다.
- **case 수 선언 대조 축은 컨텍스트마다 83건이 미측정**이다(개수 선언 없음 79 · case 줄 없음 4, native · slash 합계 166) — 통과가 아니다.
- **PyPI 업로드는 하지 않는다**(§1 각주 0 — 2026-08-14 소유자 최종 결정). 배포는 GitHub Releases 하나다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-11-16T06:31:54Z)_

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
