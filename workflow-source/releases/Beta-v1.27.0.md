# Beta v1.27.0 (2026-11-17)

> **상태: 릴리스 준비.** package `1.27.0`, runtime `__version__ = 1.27.0`, tag `v1.27.0`.
> **minor release** — iPad Chrome 워크벤치 폼 제출 수리 · 작업 중 진행 기록 상기(정본 원칙 + hook) · 한 호스트에 워크벤치 여러 개(포트 분배 · 저장소/브랜치 표시 · 목록).
>
> 등급 근거 (§1.5): v1.26.0 이후 코드 커밋 3 — feat 1(수리 셋 포함) · chore 1 · test 1, breaking 0 — **minor**.
> 공개 Python API 시그니처 제거 0, 진입점 제거 0. 새 명령 `progress-nudge`, `workbench --list`, 플러그인 `PostToolUse` 두 번째 hook 명령,
> 실행 기록의 `bind` 필드는 **추가**다. **동작이 바뀌는 곳 하나**: `workbench` 에 `--port` 를 주지 않으면 이제 8766 고정이 아니라
> checkout 경로 해시로 정한 포트(8766~8865)를 쓴다(§2.3) — 8766 을 북마크한 소비자는 `--port 8766` 을 명시하거나 자동 기동 인자에 다시 저장한다.

## 0. 릴리스 판정

v1.26.0 이후 3커밋(발행 · 메모리 정리 제외)이다. 소유자 보고 · 지시 셋 — "아이패드에서 버튼 클릭이 안 먹는다", "작업 중에 지속적으로 워크벤치를
업데이트하도록 지침이 들어가야 한다", "한 환경에 여러 개의 워크벤치가 열리는 케이스(포트 분배 · 저장소명 · 브랜치명 표시)" — 을 넣었다.

## 1. 릴리스 요약

- 범위: `v1.26.0..` 발행 준비 직전까지 **3 commit** — feat 1 · chore 1 · test 1 (+ 발행 완료 1 · 메모리 커밋).
- 누적 smoke **332/332 PASS** (로컬 `--branch-context=all` = 332 × native/slash, 발행 준비 커밋에서 실행).
- 검사 수 329 → 332 (새 검사 파일 3 — `check_workbench_submit` · `check_progress_nudge` · `check_workbench_multi`).

## 2. 소비자에게 보이는 변화

### 2.1 iPad Chrome 에서 워크벤치 폼 제출이 서버에 닿지 않던 결함 (`0c23165f`, spec §4.5)

- iOS Chrome(CriOS 156 · iPadOS 27)에서 응답 보내기 · todo 추가 버튼이 아무 일도 하지 않았다. 진단 서버 실측: 탭 → click → submit 까지 일어나고
  스크립트가 막지도 않았는데 서버 접속은 0(TLS · 깨진 요청도 0), CSP 위반 이벤트도 0 — **폼 제출의 페이지 이동만** 브라우저가 버렸다.
  같은 화면의 `fetch` POST 는 닿았다.
- 화면 스크립트가 쓰기 폼(응답 · todo · 로그인 · 로그아웃)의 submit 을 가로채 `fetch` POST(같은 출처 쿠키 · urlencoded — 서버가 받는 것은 폼과 같다)로 보낸다.
  리다이렉트면 그 주소로 가고, 오류 화면(403 · 409 …)은 그 자리에 그린다. 스크립트가 없으면 폼이 원래대로 간다.
- 서버는 POST 에 답한 뒤 연결을 닫는다 — 본문을 읽지 않고 답하는 경로(경로 표 밖 404 · 개방 모드 로그인 · 로그아웃)가 남긴 본문이
  같은 연결의 다음 요청을 `probe=1GET …` 404 로 깨뜨렸다.
- `workbench --stop` 이 loopback 이 아닌 주소(예: tailscale IP)에만 바인드한 서버를 "워크벤치로 답하지 않는다" 로 내리지 못하던 결함 —
  실행 기록에 `bind` 를 늘 싣고, 탐침은 `bind` → (옛 기록이면) `public_url` 의 호스트 → `127.0.0.1` 순이다.

### 2.2 작업 중 진행 기록 상기 — 정본 원칙 + hook (`0c23165f`, spec §4.6)

- 정본 §1 원칙: *작업 중 단계마다(계획 → 구현 → 검사 → verifier → 커밋 · push) `backlog-update --progress-note` 로 진행 기록을 남긴다* —
  모든 하네스 진입점 규칙 블록에 실린다. 워크벤치의 '지금 하는 일' 이 이 줄이다.
- `python -m workflow_kit progress-nudge --hook <EVENT>` — 현재 브랜치의 in_progress task 중 Progress 가 최근 12시간 안인 것('작업 중')의
  가장 새 기록이 **15분** 넘게 그대로면 hook JSON 으로 상기한다. 물려받아 손대지 않은 in_progress · 시각 없는 옛 기록은 보지 않는다.
- Claude Code 플러그인 `PostToolUse` 에 두 번째 명령 — 워크플로우 프로젝트(`ai-workflow/memory`)가 아니면 끝나고, 확인 표식이 15분 안이면
  `find` 하나로 끝난다(Python 을 띄우지 않는다). 상기는 낡은 동안 15분마다 많아야 한 번. 다른 하네스는 원칙 줄만 받는다.

### 2.3 한 호스트에 워크벤치 여러 개 (`0c23165f` · `b58c0f28`, spec §3.2)

- **포트**: `--port` 를 생략하면 checkout 경로 해시로 8766~8865 중 한 포트를 먼저 쓰고, 차 있으면 그 범위에서 다음 빈 포트로 넘어간다.
  같은 checkout 은 늘 같은 포트를 먼저 시도한다. `--port N` 은 그 포트만(차 있으면 rc 2), `--port 0` 은 OS 가 고른다. 자동 기동도 같다.
- **이름**: 화면 머리에 `저장소 <이름>` · `브랜치 <이름>`, 탭 제목은 `<저장소> · <브랜치> — <화면>`. worktree 는 공통 `.git` 의 저장소 이름이다.
- **목록**: 서버가 `${XDG_CACHE_HOME:-~/.cache}/workflow_kit/workbenches/` 에 자기를 적고 내릴 때 지운다. `workbench --list` 가 살아 있는
  워크벤치들의 저장소 · 브랜치(지금 HEAD) · URL 을 JSON 으로 낸다(죽은 기록은 지운다). 위치는 `WORKFLOW_KIT_WORKBENCH_REGISTRY` 로 바꾼다.

### 2.4 검사 · 기준

- `check_standard_single_source` — 이 저장소 진입점이 §11 명령만이 아니라 §1 **원칙**도 싣는지 대조한다(정본에 원칙이 늘어도 따라오지 않은 채 green 이던 사각).
- `check_entry_diet` case 1 기준 15% → **10%** (소유자 결정 2026-11-17) — 15% 는 여유가 13B 라 정본 원칙 한 줄만 더해도 red 였다.
- 진입점 절 해시 재채취(`1b94a470`, `DEFAULT_REFS` += `0c23165f`).

## 3. 검증

- **전량 게이트** `--branch-context=all` — native 332/332 · slash 332/332 · rc 0. 발행 준비 커밋의 clean tree 에서 실행하고,
  결과는 게이트 증거 파일(`<git common dir>/gate_evidence/<sha>.json`)에 남는다.
- **커밋 전** `--changed` 게이트 · **스모크** `check_self_application` 8/8 rc 0.
- 수리마다 되주입 red 를 쟀다 — 작성 세션: submit 5 · progress-nudge 7 · 진입점 원칙 1 · multi 10, verifier: submit 7 · 원칙 제거 8 · multi 12.
  검사 · verifier 가 찾은 결함은 발행 전에 고쳤다: 계획(주장 · 결정)이 없는 task 를 건너뛰던 상기 대상 조회 · todo 폼의 `<input name="action">` 이
  가리던 `form.action`(첫 구현이 `POST /task/[object HTMLInputElement]`) · TIME_WAIT 포트 때문에 '다음 포트' 경로를 비켜 가던 검사
  (되주입 5회 중 1회 green → 보강 뒤 5/5 red) · 해시 분산 · 목록 해제를 재지 않던 검사.
- 실측: 실제 iPad(CriOS 156)의 응답 제출 `POST …/respond 303`, 헤드리스 Chrome iPad 에뮬 + CDP 로 todo 303 · 낡은 CSRF 403 화면 · 응답 303 ·
  `fetch` 없을 때 원래 폼 제출(navigation POST 0). Claude Code 에서 `PostToolUse`(todo) · `UserPromptSubmit`(응답) hook 의 additionalContext 가
  모델 컨텍스트에 들어오는 것을 관측했다 — v1.26.0 의 '미측정' 한 칸이 측정이 됐다(재시작 없이 현재 설치본 hook 을 읽었다).
- 발행 호스트: Linux.

## 4. 알려진 한계 (감추지 않는다)

- **실제 iPad 에서 todo 추가 한 번은 아직 재지 않았다** — 응답 제출만 실기기로 쟀고 todo 는 Chrome 에뮬 + CDP 로 쟀다. 같은 이유로
  '실제 화면의 todo 변경이 hook 으로 모델 컨텍스트에 들어간다' 도 서버 파일을 흉내 낸 탐침으로만 관측했다.
- iOS Chrome 이 폼 제출 페이지 이동을 버리는 **원인은 확정하지 못했다**(CSP 위반 보고 없음 · 접속 0) — `fetch` 우회로 고쳤다. WebKit(Safari)은
  이 호스트에서 실행 불가(ICU 74 등 라이브러리 부재)라 재지 못했다.
- **진행 기록 상기 hook 은 Claude Code 에만 배선**했다. 다른 하네스는 정본 원칙 줄만 받는다.
- `--list` 는 이 판 이전 kit 으로 띄운 서버를 보이지 않는다(등록 전).
- 계획에 결정을 더하는 쓰기는 계획 지문을 바꿔 앞선 워크벤치 응답의 자격을 푼다(설계 동작) — 이번에 소유자 응답 하나가 `kept → proposed` 로
  돌아갔다. 결정 추가 뒤에는 `plan-status` 로 확인하고 필요하면 `--decision-state D<n>=answered:<value>` 로 기록한다.
- **Windows 실측은 이번 판에도 없다** (M-028/WBS-28.3). hook 셸 명령(`find -mmin`) · 워크벤치 포트 분배는 Linux 에서만 쟀다.
- **case 수 선언 대조 축은 컨텍스트마다 83건이 미측정**이다(개수 선언 없음 79 · case 줄 없음 4, native · slash 합계 166) — 통과가 아니다.
- **PyPI 업로드는 하지 않는다**(§1 각주 0 — 2026-08-14 소유자 최종 결정). 배포는 GitHub Releases 하나다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-11-17T06:14:14Z)_

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
