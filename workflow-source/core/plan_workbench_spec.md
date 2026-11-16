# 계획·진척 워크벤치 스펙

- 문서 목적: 브라우저에서 task 의 계획(주장 · 결정)과 진척을 읽고 결정에 답하는 `workbench` 서버의 kit 계약(명령 · 수명 · 경로 · 인증 · 응답 쓰기 · 진척 값 · 알림 · MCP · 노출 · 모듈 · 검증)을 정의한다.
- 범위: `python -m workflow_kit workbench`, 서버가 서빙하는 경로와 화면, 서버가 받은편지함에 쓰는 응답, 받은편지함 건수의 정본 함수, MCP 도구 `plan_inbox` · `plan_import`, §11.1 한 줄과 스킬, 검사 넷
- 대상 독자: workflow 설계자, AI agent, kit 소비 프로젝트
- 상태: draft (ADR-032 accepted 2026-11-13 — M-029 ② 서버 · 화면 · 검사 · MCP 두 도구 구현 2026-11-14, Windows 실측 전)
- 최종 수정일: 2026-11-16
- 관련 문서: `../../ai-workflow/wiki/decisions/adr-032-plan-workbench.md`, `../../docs/planning/plan-workbench-requirements-2026-11.md`, `./claim_plan_spec.md`, `./global_workflow_standard.md`

> **결정 근거는 ADR-032 에, 숫자의 실측은 requirements 에 있다.** 이 문서는 *계약* 만 적는다.
> 괄호 안의 `R…` 은 requirements(`plan-workbench-requirements-2026-11.md`)의 요구 사항 번호다 — 대응표는 §12.
> 응답 파일 형식 · 받은편지함 · 번호 · `plan-import` · 결정 상태 계산은 `claim_plan_spec.md` 가 정본이다 (아래에서 "주장 스펙 §…").

## 1. 불변 조건 (R0)

1. 서버 · 화면 · 알림은 파일 · CLI · MCP · 표준 HTTP 로만 선다 — 어느 하네스의 전용 표면에도 기대지 않는다.
2. 서버가 쓰는 워크플로우 상태는 **받은편지함 하나**다 (주장 스펙 §7). task 파일 · 보관 · `state.json` · `roadmap_state.json` 은 읽기만 한다.
   그 밖에 쓰는 것은 `.workbench/server.json` · 도착 신호 `.workbench/inbox.stamp`(§6.1) 와 그 디렉터리의 `.gitignore` 뿐이다 (§3). 접근 기록은 표준 오류로 낸다.
3. 폼으로 들어온 글은 데이터다 — 실행하지 않고, 경로로 쓰지 않고, 다른 곳으로 보내지 않는다. task 파일의 글도 화면에 넣을 때 이스케이프한다.
4. 화면의 숫자는 생성물(또는 같은 생성기로 원천에서 지금 계산한 값 — §7.1)과 task 파일에서만 온다. 재지 않은 것은 "미측정" 이다.
5. loopback 요청도 인증한다 — 소유자가 고르는 개방 모드(§5.6)만 예외다. 서버는 자기 공개 주소를 추측하지 않는다 — `public_url` 하나.
6. 페이지는 외부 자원을 부르지 않는다.
7. 모델 호출이 없다.
8. 주장 · 결정 읽기 · 지문 · 결정 상태 · 응답 렌더 · 공개 · 받은편지함 건수는 `plan_claims` · `plan_tasks` · `plan_responses` 의 함수만 쓴다
   (`inbox_census` — §8.1).

## 2. 명령 (R1.1 · R1.2)

```
python -m workflow_kit workbench [--bind 127.0.0.1] [--port 8766] [--public-url URL]
    --token <viewer|approver>:<name>=env:<VAR>|file:<path> [--token …]
    [--trusted-proxy ADDR]… [--tls-cert PATH --tls-key PATH] [--allow-plain-http] [--refresh SECONDS]
python -m workflow_kit workbench --open <name> [--bind ADDR] [--port N] [--public-url URL] [--trusted-proxy ADDR]…
python -m workflow_kit workbench --status
python -m workflow_kit workbench --autostart on <시작 인자…> | --autostart off
python -m workflow_kit workbench --stop [--autostarted-only]
python -m workflow_kit workbench --new-token <role>:<name> --out <path>
```

- 모르는 인자 · 접두 축약은 거절한다 (`allow_abbrev=False`).
- 시작을 거절하는 경우 (rc 2, 이유 한 줄): 토큰이 없다 · 토큰 값이 32자 미만 · 토큰 파일 모드가 `0600` 보다 넓다(POSIX) · 이름이 `[A-Za-z0-9_-]{1,32}` 가 아니거나
  겹친다 · 포트가 사용 중이다 · TLS 를 켰는데 `public_url` 이 `http` 다 · `--bind` 가 loopback 이 아닌데 TLS 도 `--allow-plain-http` 도 없다 ·
  같은 checkout 에 살아 있는 서버가 있다 (그 `public_url` 을 알린다).
- `public_url` 은 끝 슬래시를 갖는다 — 없으면 붙인다. 기본 `http://127.0.0.1:<port>/`. 시작할 때 `public_url` 을 출력하고, loopback 이 아닌 bind 면 경고 한 줄.
- `--new-token` 은 `secrets.token_urlsafe(32)` 를 `0600` 파일로 쓰고 값은 출력하지 않는다 (출력은 경로와 `--token` 에 줄 인자 한 줄). 있는 파일은 덮지 않는다. 부모 디렉터리가 없으면 `0700` 으로 만들고,
  `--out` · `=file:` 의 `~` 는 kit 이 펼친다 (셸은 `=file:~/…` 의 `~` 를 펼치지 않는다).
- TLS 는 표준 `ssl`, 최소 판 TLS 1.2 (`ssl.TLSVersion.TLSv1_2`). 인증서는 kit 이 만들지 않는다.
- `--status` 는 `.workbench/server.json` 을 읽어 `{"running": bool, "pid": …, "port": …, "public_url": …, "started_at": …, "autostarted": bool, "autostart": bool}` JSON 한 덩어리를 내고 끝난다
  (기록이 없거나 `pid` 가 죽었으면 `running: false`; `autostart` 는 §3.1 설정이 있는가).
- 정본 §11.1 에 `Review plans and progress in a browser | python -m workflow_kit workbench`. 스킬 `workbench` (+ bootstrap `/workflow-workbench`) —
  띄우는 법 · 토큰 만드는 법 · URL 을 사용자에게 알리는 것까지. 모델은 서버를 조작하지 않는다 — 자동 기동(§3.1)은 소유자가 켠 설정을
  `session-start` · hook 이 집행하는 것이다.

## 3. 수명 (R1.3)

- 실행 기록은 **checkout 루트**의 `.workbench/server.json` — `pid` · `port` · `public_url` · `started_at` · `instance`(시작 때 만든 무작위 32 hex, `healthz` 머리와 같은 값). 토큰 · 세션은 싣지 않는다.
  `.workbench/` 는 자기 무시 디렉터리다: 안의 `.gitignore` 가 `*\n` 인지 시작할 때마다 확인하고 다르면 다시 쓴다.
- checkout 하나에 서버 하나 — 기록의 `pid` 가 살아 있으면 시작을 거절한다. 죽은 `pid` 의 기록은 덮어쓴다. 정상 종료 때 기록을 지운다.
- 요청마다 현재 브랜치를 다시 읽는다 — 화면 머리에 브랜치 이름을 보인다.
- 세션 · 로그인 실패 표는 메모리에만 있다. 다시 띄우면 다시 로그인한다.
- 기록의 `pid` 가 살아 있으면 `session-start` 보고의 `summary` 에 `워크벤치 실행 중: <public_url>` 한 줄.

### 3.1 자동 기동 (소유자 결정 2026-11-16, TASK-2026-11-16-main-002)

- `--autostart on <시작 인자…>` 는 시작 인자를 §2 의 거절 규칙으로 검증한 뒤(살아 있는 서버 판정 제외) `.workbench/autostart.json`
  (`{"argv": […], "saved_at": …}`)에 쓴다. 토큰은 `env:` · `file:` 참조만 실린다. `--autostart off` 가 지운다. 설정은 checkout 로컬이고 git 이 무시한다.
- 설정이 있고 살아 있는 서버가 없으면 `session-start` 가 서버를 떨어진 자식(POSIX 새 세션 · Windows `DETACHED_PROCESS`)으로 띄우고
  실행 기록을 15초까지 기다린다(넘으면 자식을 내리고 실패로 본다) — `summary` 에 `워크벤치 시작: <public_url>`. 실패는 `warnings` 한 줄(`워크벤치 자동 기동 실패 — <이유>`)이고
  세션 진입을 막지 않는다. 자식의 표준 출력 · 오류는 `.workbench/server.log` (띄울 때마다 새로).
- 자동 기동한 서버의 실행 기록에는 `"autostarted": true` 와 `bind` 가 더 실린다.
- `WORKFLOW_KIT_NO_WORKBENCH_AUTOSTART` 가 있거나 검사 표식 `WORKFLOW_KIT_TELEMETRY_SKIP_ROOT` 가 이 작업 공간을 가리키면 띄우지 않는다 —
  러너 · 스모크가 살아 있는 저장소에서 `session-start` 를 불러도 서버가 남지 않는다.
- `--stop` 은 기록의 포트가 `healthz` 에 `ok` 로 답하고 그 응답의 `X-Workbench-Instance` 가 기록의 `instance` 와 같을 때만 기록의 pid 에 SIGTERM 을 보낸다 —
  기록의 pid 는 서버가 자기 자신을 적은 것이라, 같은 instance 로 답해야 그 pid 가 그 포트의 주인이다(pid 재사용 · 다른 checkout 의 워크벤치 방어, TASK-2026-11-16-main-005).
  `instance` 가 없는 옛 기록(1.24.0 이하)은 표식 없는 서버일 때만 옛 판정(`healthz` `ok`)으로 내린다. 10초 안에 끝나면 기록을 지운다.
  이 대조는 **우발 사고**(pid 재사용 · 같은 포트의 다른 checkout)를 막는다 — `instance` 는 비밀이 아니고, 기록을 쓸 수 있는 로컬 사용자를 막지 않는다.
  `--autostarted-only` 는 `autostarted` 기록만 내린다. 결과는 JSON 한 줄, rc 0.
- Claude Code 플러그인 hooks 의 `SessionEnd` 가 `workbench --stop --autostarted-only` 를 부른다 (출력은 버린다). SessionEnd 가 없는 하네스에서는
  서버가 남고, 다음 `session-start` 는 그것을 `실행 중` 으로 알린다.

## 4. 경로 · 머리 · 화면 (R2)

### 4.1 경로 — 이것 말고는 404

| 메서드 · 경로 (`public_url` 기준 상대) | 역할 | 인증 | 실패 |
|---|---|---|---|
| `GET healthz` | `ok` (머리 `X-Workbench-Instance: <instance>`) | 없음 | — |
| `GET login` · `POST login` | 토큰 폼 · 세션 시작 | 없음 | 401 (같은 폼) · 429 · 403 (`Origin`) · 413 (본문 > 4,096) |
| `POST logout` | 세션 끝 | 세션 | 401 · 403 (`Origin` · CSRF) |
| `GET ` (루트) | 진척 화면 (§7) | viewer 이상 | 세션 없음 → 303 `login` |
| `GET task/<TASK-ID>` | 계획 화면 (§4.4) | viewer 이상 | 세션 없음 → 303 `../login` · 없는 task 404 |
| `POST task/<TASK-ID>/respond` | 결정 응답 (§6) | approver | §5.4 · §6 |
| `POST todo` | todo 한 건 바꾸기 (§13.1) | approver | §5.4 · 413 (본문 > 8,192) · 400 (`back`) · 422 · 404 · 503 (락) |
| `GET api/state` | 진척 값 JSON (§7.3) | viewer 이상 | 401 |
| `GET static/<이름>` | 내장 자원 (고정 목록) | 없음 | 404 |

`<TASK-ID>` 는 작업 항목 ID 문법(`project_docs.WORK_ITEM_ID_PATTERN`)에 맞고 현재 브랜치에 그 task 파일이 있을 때만 받는다.

### 4.2 응답 머리

모든 응답: `Content-Security-Policy: default-src 'none'; style-src 'self'; script-src 'self'; connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'`,
`X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin` (`no-referrer` 면 브라우저가 폼 POST 에 `Origin: null` 을 실어 §5.4 대조가 막는다 — TASK-2026-11-16-main-007), `Cache-Control: no-store` (`static/` 는 `max-age=3600`). 인라인 스크립트 · 스타일 없음.

### 4.3 상대 경로

링크 · 폼 action · `Location` 은 전부 상대 경로다. 절대 URL 은 시작 시 출력 하나뿐이다. 렌더러는 현재 경로의 깊이로 상대 경로를 만드는 함수 하나를 쓴다.

### 4.4 계획 화면

task 파일에 있는 것만 그린다: 주장 트리(`<details>`, 접힌 상태 = 1단계 목록, ID 그대로) · 3단계 위치(경로와 줄만) · 주장별 완료 기준과 검증 줄
(`plan_claims.claim_bundles` 의 묶음 — `Verification` 줄의 글은 그대로 보이고 판정을 추론하지 않는다) · 결정(가리키는 주장 안에 닫힌 `<details>` 하나씩 — 질문 · 선택지 radio · 기본값에 "추천" 과 `checked` · **계산한**
상태, 칸이 다르면 "task 파일의 칸은 <값>") · 머리의 "열린 결정 n건" · "미반영 응답 n건" · 배치 문제(있으면) · 끝에 `Out of scope`.
`answered` 결정은 읽기 전용(답과 함께). 주장이 없는 task 는 Description · 완료 기준 · Plan 나머지 필드를 그대로(폼 없음). viewer 에게는 폼이 없다.

화면 모양 (TASK-2026-11-16-main-003 — 소유자 지시 "대시보드형"): 진척 화면은 요약 수치 다섯(진행 중 · 차단 · 계획 · 열린 결정 · 미반영 응답 —
`api/state` 에서 센 값, 없는 목록은 "미측정") → 계획 카드(열린 결정이 있으면 강조) → 작업 보드 4열 → 마일스톤 카드(진척 막대; 선언 · 파생이
둘 다 `done` 이고 문제 없는 것만 "완료된 마일스톤 n개" 아래로 접는다). 계획 화면은 머리 카드(상태 · 열린 결정 · 미반영 응답 칩) → 주장 카드 트리
(1단계까지 펼침) → 결정 카드(열린 결정은 `decision open` 강조, **닫힌 채** — 펼침이 곧 `opened` 기록) · 선택지 카드 → 하단 고정 제출 막대.
스타일은 `static/workbench.css` 하나 — 어두운 모드(`prefers-color-scheme`) · 좁은 폭(`max-width`) 규칙, 인라인 `style` 없음 (CSP).
글자는 박스를 넘지 않는다 (TASK-2026-11-16-main-013): 본문 `overflow-wrap: anywhere`, 박스 · flex/grid 자식 `min-width: 0`, 격자 칸은
`minmax(…, 1fr)` 로만, 카드 머리는 줄을 바꾸고 ID 를 자르지 않는다. 상태 배지 · 칩도 자르지 않고 줄을 바꾼다(말줄임은 "파생 …" 같은 요점을 잃는다). 카드 · 보드의 긴 글은 3줄까지 보이고 전문은 `title` 에 싣는다.
정적 파일 링크에 내용 지문 `?v=<sha256 앞 10 hex>` 를 붙여 브라우저 캐시(`max-age=3600`)가 바뀐 CSS · JS 를 가리지 않게 한다.

### 4.5 자동 새로고침 (TASK-2026-11-16-main-006 — 소유자 지시 "작업하면서 워크벤치 내용을 지속적으로 갱신")

- `--refresh SECONDS` (기본 5, 0~3600, 0 이면 끈다). 켜져 있으면 진척 · 계획 화면이 `<body data-refresh="N">` 와 `static/workbench.js` 를 싣고,
  `<main data-version="…">` 에 본문의 지문(sha256 앞 16 hex)을 싣는다.
- 스크립트는 N초마다(탭이 숨어 있으면 쉰다) 같은 주소를 `fetch` 로 다시 받아 `data-version` 이 다를 때만 `main` 을 갈아 끼운다.
  리다이렉트(세션 끝)는 따르지 않는다. CSP 는 이것을 위해 `connect-src 'self'` 하나만 더한다.
- 계획 화면에서 답을 쓰는 중(폼 입력 · 결정 펼침)이면 갈아 끼우지 않고 "내용이 바뀌었다" 알림과 새로고침 단추만 낸다 — 쓰던 답과 `opened` 기록을 지킨다.

## 5. 인증 (R3 · R4)

### 5.1 토큰

역할 `viewer` · `approver`. 이름은 `[A-Za-z0-9_-]{1,32}` 이고 유일하다 (응답의 `responder` 가 된다). 값은 환경변수 이름 또는 파일 경로로만 받고 32자 이상이다.
비교는 `hmac.compare_digest`. 거두기는 값을 바꾸고 다시 띄우는 것이다.

### 5.2 로그인

- 토큰은 `POST login` 본문(`token`)으로만 받는다. 질의 문자열의 토큰은 400.
- 성공: 세션 쿠키 + 303 `./`. 실패: 401 과 같은 폼.
- 실패 제한: 같은 요청자 주소에서 60초 안에 5회 실패하면 그 주소의 로그인을 60초 동안 429. 요청자 주소는 연결의 상대 주소이고,
  `--trusted-proxy` 에서 온 요청만 `X-Forwarded-For` 의 마지막 값을 쓴다.
- `POST login` · `POST logout` 도 `Origin` 을 대조하고 본문 4,096 바이트 이하만 받는다. `POST logout` 은 CSRF 값도 대조한다.

### 5.3 세션 · 쿠키

- 쿠키 `wb_session` — `HttpOnly` · **`SameSite=Lax`** (ADR-032 결정 8) · `Path` = `public_url` 의 경로 · `public_url` 이 `https` 면 `Secure`.
- 값은 `secrets.token_urlsafe(32)`, 서버 메모리의 표로만 이름 · 역할 · CSRF 값(세션마다 따로) · 만료(12시간)에 묶인다.

### 5.4 쓰기 요청의 대조 — 순서대로, 하나라도 어긋나면 아무것도 쓰지 않는다

1. `Content-Length` 가 있고 262,144 바이트 이하 (없으면 411, 넘으면 413 — 본문을 읽기 전에, 연결을 닫는다).
2. 세션이 있고 역할이 `approver` (401 · 403).
3. `Origin` = `public_url` 의 출처 (없거나 다르면 403 — 화면에 기대하는 출처를 보인다).
4. 폼의 `csrf` = 그 세션의 값 (403, 상수 시간 비교).

### 5.5 기록

접근 기록은 표준 오류 한 줄: 시각 · 메서드 · 경로 · 상태 · 사용자 이름. 토큰 · 쿠키 · CSRF · 폼 본문은 남기지 않는다.

위임 인증(신뢰 프록시의 사용자 머리)은 이 판에 없다 (requirements Q2).

### 5.6 개방 모드 `--open <name>` (소유자 결정 2026-11-16, TASK-2026-11-16-main-001)

토큰 · 로그인 없이 접속한 누구나 `<name>` 이름의 `approver` 다. 응답이 소유자에게서 왔다는 대조를 **없애는** 모드라
소유자가 고를 때만 쓴다 — 시작 때 표준 오류에 경고 한 줄(`인증 없이 열었다`, loopback 밖이면 그 주소도).

- `<name>` 은 토큰 이름과 같은 문법. `--token` 과 같이 주면 시작을 거절한다 (rc 2).
- loopback 밖 `--bind` 를 TLS · `--allow-plain-http` 없이 받는다. `--public-url` 이 없으면 기본 주소는 bind 주소이고,
  `0.0.0.0` · `::` 면 기본 경로의 이 호스트 주소다 (UDP `connect` 로 찾고 패킷은 보내지 않는다 — 못 찾으면 `127.0.0.1`).
- 세션이 없는 화면 · `api/state` 요청은 세션을 만들어 쿠키로 준다 — CSRF 값과 알림을 위한 것이지 인증이 아니다.
  `login` · `logout` 은 303 `./`. 화면 머리에 로그아웃 대신 `<name> · 인증 없음`.
- §5.4 의 대조는 그대로 하되 3 의 `Origin` 은 `public_url` 의 출처 **또는** 요청의 `Host` 출처면 통과한다 — 다른 기기가 IP 로 연다.
  `Host` 의 호스트는 IP 리터럴 · `localhost` · `public_url` 의 호스트만 받는다 — 다른 이름(DNS rebinding 의 모양)과
  다른 사이트의 페이지가 보낸 쓰기는 403 이다.
- 세션 표는 1,024 개가 상한이다 — 넘으면 만료된 것, 그다음 만료가 가장 이른 것부터 버린다 (쿠키 없는 요청마다 세션이 생긴다).
- 응답 파일 머리에 `client: <요청자 주소>` (§5.2 의 요청자 주소, `[0-9A-Za-z.:%_-]{1,64}` 밖이면 `unknown`). 토큰 모드는 싣지 않는다.

## 6. 응답 쓰기 (R5)

폼 필드: `csrf` · `plan_digest`(페이지를 그릴 때 계산) · 결정마다 `value_<D>` · `opened_<D>`(`yes` 만 yes) · 주석 `comment_<C 또는 D 또는 ->`(빈 칸은 싣지 않는다).
폼은 그 task 의 **모든** 결정을 싣는다. 스크립트 `static/workbench.js` 는 결정의 `<details>` 가 처음 열릴 때 그 `opened_<D>` 를 `yes` 로 바꾸는 일 하나만 한다.
스크립트가 꺼진 브라우저도 열고 제출할 수 있다 — 열림 기록만 없어 `opened: no` 다 (기본값 그대로면 `unopened`, 다른 값이면 `changed` — 서버는 가르지 않는다).

§5.4 를 통과한 뒤:

1. 배치 — `plan_responses.layout_problem(branch_dir)` 이 사유를 내면 **409** (사유를 보인다, 주장 스펙 §7-8 · §7-9).
2. 지문 — 지금 task 파일의 `plan_digest` 와 폼의 값이 다르면 **409** "계획이 바뀌었다, 다시 열어라". task 파일이 오류 규칙(L2 · L6 · L9)을 어기면 **409** (주장 스펙 §8.1 의 0 단계).
3. `answered` 가 **아닌** 결정의 `value` 가 선택지 밖이면 **422**.
4. `answered` 인 결정은 폼이 무엇을 보냈든 `value` = 기본값 · `opened: no` 로 적는다.
5. 주석의 CRLF · CR 을 LF 로 고친다. 그 뒤에도 `\n` · `\t` 밖의 제어 문자가 있으면 **422**.
6. `received_at` = 서버 시각 (`YYYY-MM-DDTHH:MM:SS.ffffff±HH:MM`, 주장 스펙 §6). 그 task 의 받은편지함 · 보관에서 **자격 있는** 같은 응답자의 가장 늦은 시각보다
   늦지 않으면 그 시각의 1마이크로초 뒤로 민다.
7. 본문은 `plan_responses.render_response`, 그 바이트가 주장 스펙 §6 의 한도를 넘거나 `plan_responses.qualify` 의 1~6 단계 중 하나에서 떨어지면 **422** (단계와 사유를 보인다).
8. `plan_responses.publish` 로 받은편지함에 공개한다 (다 쓴 뒤 한 번에, 번호는 주장 스펙 §7-1).
9. 303 `../<TASK-ID>` (계획 화면) — "<응답자> 의 응답을 <received_at> 에 받았다 — 작업 세션이 `plan-import` 로 반영한다". 번호는 보이지 않는다 (보관 때 바뀔 수 있다).

서버는 `plan-import` 를 부르지 않고 task 파일을 고치지 않는다. 서버는 시작할 때 받은편지함의 자기 임시 파일(`.tmp-<pid>-*`, 죽은 pid)을 지운다 — 임시 이름을 아는 `plan_responses.sweep_dead_temp_files` 로.

### 6.1 도착 신호와 작업 세션 hook 반영 (TASK-2026-11-16-main-014 — 소유자 결정: hook 이 자동 반영 + 알림)

- 서버는 응답을 공개한 뒤 checkout 루트의 `.workbench/inbox.stamp` 에 새 표식(시각 + 무작위)을 쓴다. task 파일은 여전히 쓰지 않는다(ADR-032 결정 15).
- `plan-import --hook <PostToolUse|UserPromptSubmit>` 은 `inbox.stamp` 와 `inbox.seen` 의 **내용**이 다를 때만 받은편지함의 **모든 task** 응답을 `--apply` 로 반영하고,
  결과를 `{"hookSpecificOutput": {"hookEventName": <event>, "additionalContext": "…"}}` 한 덩어리로 낸다 — task · 응답자 · 결정 변화 · 남은 열린 결정,
  자격 없는 응답은 받은편지함에 남기고 그 사유. 할 것이 없으면 아무것도 출력하지 않는다(rc 0). 반영이 바쁘면(`import_busy`) seen 을 두어 다음 hook 이 다시 본다.
  처리 뒤 `inbox.seen` 에 처리 시작 때 읽은 표식을 쓴다 — 처리 중 새 응답은 표식이 달라 다음 hook 이 본다. mtime 이 아니라 내용 비교라
  1초 단위 파일시스템에서도 같은 초의 두 번째 응답을 놓치지 않는다.
- Claude Code 플러그인 hooks 의 `PostToolUse` · `UserPromptSubmit` 명령: `$CLAUDE_PROJECT_DIR` 의 stamp 가 없거나 seen 과 같으면(`cmp`) 끝 — Python 을 띄우지 않는다.
  다르면 **이 기능을 아는** kit 이 깔린 인터프리터를 골라(`import workflow_kit.workbench.inbox_signal`) `$CLAUDE_PROJECT_DIR` 로 이동한 뒤 위 명령을 부른다.
  그런 인터프리터가 없으면(옛 kit 만) seen 을 stamp 로 맞추고 "직접 `plan-import --task <ID> --apply` 로 반영하라" 를 한 번 알린다 — 도구마다 Python 을 다시 띄우지 않는다.
- 계획 화면은 그 task 의 응답을 '반영 대기'(받은편지함) · '반영됨'(보관)과 응답자 · 시각으로 보인다 — §4.5 자동 새로고침으로 반영되는 순간이 보인다.
- **한계 (감추지 않는다)**: 한 세션 안에서는 hook 이 도구 호출 사이에 돌아 task 파일 쓰기가 순차다. 같은 checkout 을 두 세션이 쓰거나, 백그라운드로 돈 `backlog-update` 와
  hook 이 겹치면 task 파일의 read-modify-write 는 잠금이 없다(`inbox_lock` 은 plan-import 끼리만 직렬화한다) — 기존 `backlog-update` 끼리와 같은 조건이다.
  hook 명령은 POSIX sh 문법이다(Windows cmd · PowerShell 미측정). 같은 hooks 사본을 읽는 Grok Build 의 이 두 이벤트 처리와, Claude Code 가 이 JSON 을 실제로
  모델 컨텍스트에 넣는지는 아직 실측하지 않았다(검사는 bash 로 명령을 돌려 출력 모양을 잰다).

## 7. 진척 (R6)

### 7.1 원천

| 보이는 것 | 원천 |
|---|---|
| 마일스톤 · WBS · 파생 진척 · issues · `deliverables_missing` | `roadmap.build_roadmap_state` (실시간) 또는 `roadmap/roadmap_state.json` |
| 진행 · 차단 · 계획 · 최근 완료 task | `refresh_workflow_state_cache` 를 임시 출력으로 (실시간) 또는 브랜치 `state.json` |
| 완료 기준 · 검증 줄 · 주장 · 결정 | task 파일 |
| 지금 하는 일 (계획 카드 · 작업 보드의 진행 중 · 차단 항목) | task 파일의 `Progress` 한 줄 — 작업하는 에이전트가 단계마다 `backlog-update --progress-note` 로 바꾼다(create · update 모두 시각을 도구가 붙인다 — 노트가 이미 `` `YYYY-MM-DD HH:MM` `` 로 시작하면 그대로, TASK-2026-11-16-main-009) |
| 결정 상태 | `plan_tasks.computed_states` (보관 응답 포함) |
| 미반영 응답 · 알 수 없는 항목 · 배치 문제 | `plan_responses.inbox_census` (요청 시점) |

**실시간 계산** (TASK-2026-11-16-main-008 — 소유자 지시 "작업하면서 워크벤치 내용을 지속적으로 갱신"): 서버가 프로필을 알면(CLI 서버는 늘 안다)
진척 값을 `refresh-state` 와 **같은 생성기**로 원천에서 계산한다 — 생성기 출력은 임시 디렉터리에 쓰고 저장소에는 아무것도 쓰지 않는다.
원천(메모리 디렉터리 전체 · 프로필 · 마일스톤이 선언한 산출물 파일)의 stat 지문(경로 · mtime · 크기, 없음도 값)이 같고 **브랜치가 같으면** 다시 계산하지 않는다
— 캐시 키가 (프로필, 브랜치 디렉터리)다. 생성기가 거절하거나 실패하면 디스크의 생성물을 읽고 그 사유를 `api/state.live_error` 와 화면 경고로 보인다 —\n사유의 작업 공간 경로는 상대 경로로, 그 밖의 절대 경로는 `<경로>` 로 가린다(§7.2 의 "절대 경로를 싣지 않는다").
roadmap 원천이 없으면 마일스톤은 "미측정" 이다 — 디스크에 남은 낡은 `roadmap_state.json` 을 실시간 값으로 보이지 않는다. 화면은 실시간이면 "실시간" 표식을, 생성물이면 생성 시각을 보인다 — 계산 시각은 화면에 싣지 않는다(§4.5 의 지문이 원천이 바뀔 때만 바뀌게).

### 7.2 표시 규칙

선언 ≠ 파생이면 둘 다 · 진척은 센 값("완료 잎 3 / 전체 4")과 그 두 수에서만 그린 막대 · 잎 0 은 "미측정"(0% 로 그리지 않는다) · 검증 줄 없는 완료 기준은 "미측정" ·
결정 칸 ≠ 계산값이면 계산값과 "task 파일의 칸은 <값>" · 생성물마다 `generated_at` · 싣지 않는 것: 절대 경로 · 호스트 이름 · 사용자 홈 · 환경변수 · 토큰 이름 목록
(경로는 저장소 상대, 브랜치 이름은 싣는다) · 다른 worktree 는 보이지 않는다.

### 7.3 `api/state`

```json
{"schema": "workbench-state/1", "branch": "<branch>",
 "generated_at": {"roadmap": "<iso|null>", "state": "<iso|null>"}, "source": "live|generated", "computed_at": "<iso|null>", "live_error": "<사유|null>",
 "milestones": [{"id": "M-0NN", "title": "…", "declared": "<status>", "derived": "<status>",
                 "leaves_done": 3, "leaves_total": 4, "issues": ["…"]}],
 "tasks": {"in_progress": [{"id": "…", "title": "…", "progress": {…} | null}], "blocked": […], "planned": […], "recent_done": […]},
 "issues": ["<code>: <detail>"],
 "plans": [{"task": "<TASK-ID>", "title": "…", "status": "<status>", "open_decisions": ["D1"], "pending_responses": 1,
            "progress": {"at": "<YYYY-MM-DD HH:MM|null>", "text": "…"} | null}],
 "inbox": {"pending": {"<TASK-ID>": 1}, "unknown": ["<name>"], "layout_problem": "<사유|null>"}}
```

진척 화면이 그리는 값과 같은 원천 · 같은 규칙이고 화면에 없는 값을 더 싣지 않는다. `leaves_total` 이 0 이면 `leaves_done` 도 `null` 이다 ("미측정").
생성물에 없는 목록(예: `state.json` 에 `planned_items` 가 없다)은 빈 목록이 아니라 `null` 이다. roadmap issue 는 `where` 에 마일스톤 ID 가 든
마일스톤의 `issues` 에, 나머지는 최상위 `issues` 에 싣는다 — `where`(경로) 자체는 싣지 않는다. `plans` 는 진행 중 · 차단 · 계획 task 와 미반영 응답이 있는 task 다.

## 8. 알림 · 받은편지함 보고 · MCP (R8 · R9)

### 8.1 받은편지함 건수의 정본

`plan_responses.inbox_census(branch_dir) -> InboxCensus` 하나가 정본이다 — 받은편지함을 한 번 훑어 task 별 응답 경로(`files`, 번호 순)와
그 건수(`pending: dict[task, int]`), 알 수 없는 항목(`unknown`), 배치 문제(`layout_problem: str | None`)를 낸다 (M-029 ① 에서 구현 — 옛 조합 함수
`pending_by_task` · `unknown_inbox_files` · `pending_warning` 은 접었고, `inbox_files` 는 census 의 그 task 몫이다).
`backlog-update` 게이트 · `session-start` · `refresh-state` · `plan-status` · `plan-import` · 워크벤치 · `plan_inbox` 가 이것만 부른다 (ADR-032 결정 16).
게이트는 `layout_problem` 을 `warnings` 에 싣기만 하고 그것으로 막지 않는다 — 받은편지함 행은 census 의 미반영 건수로만 판정한다 (결정 25).
census 는 배치 문제가 있어도 받은편지함의 보통 파일을 센 그대로 낸다 — 같은 디렉터리 배치(지원 밖)에서는 보관된 응답도 세어져 `done` 이 막힐 수 있다.

### 8.2 당겨 오기 (①)

- `session-start` · `backlog-update` 의 `warnings`: `계획 응답 n건 미반영 (<TASK-ID> …) — plan-import 로 확인` (주장 스펙 §11). 응답의 내용은 싣지 않는다.
- 실행 중인 서버가 있으면 `session-start` 보고에 `public_url` 한 줄.
- 우회 검출(주장 스펙 §4)에 받은편지함 행: `refresh-state` · `session-start` 는 `done` 인데 받은편지함에 그 task 의 미반영 응답이 있으면
  `done 인데 계획 응답 n건 미반영: <TASK-ID>` 를 싣는다. 막지 않는다.
- `plan-status` 는 `layout_problem` 과 보관의 링크 · 비파일 항목을 `warnings` 에 싣는다.
- `plan-import` 출력의 `pending_responses` 는 **지금의** 건수(`plan-status` 와 같은 뜻), 반영 뒤 남을 건수는 `remaining_after`.

hook 머리말(②)은 만들지 않는다 (requirements R8.2 — 소유자 결정으로 Codex 주입 실측도 하지 않는다).

### 8.3 MCP 도구

| 번들 | 이름 | 입력 | 출력 |
|---|---|---|---|
| read-only | `plan_inbox` | `task_id`(선택) | `inbox_census` + 파일별 `{task, name, responder, received_at, stage, reason}` — 주석 본문 없음 |
| write | `plan_import` | `task_id` 또는 `discard` + `reason`, `response`(선택), `apply`(기본 false) | `plan-import` 의 출력 계약 family `plan_import` 그대로 |

구현: `workflow_kit/common/plan_mcp.py`. `plan_import` 는 서버 인터프리터로 CLI `plan-import` 를 하위 프로세스로 부른다 —
stdio 서버는 표준 출력이 전송로라 같은 프로세스에서 CLI 출력을 가로채지 않는다. 입력 `apply` 는 boolean 이다(문자열은 거절).
도구가 돌려준 오류 결과(없는 task 등)는 다른 도구처럼 `status: error` · `error_code` 다. 검사: `check_plan_mcp_tools`.

서버를 띄우거나 멈추는 MCP 도구는 없다. write 번들을 받지 않는 하네스(Codex)의 반영 경로는 CLI `plan-import` 다. 체크인 생성물(descriptor · JSON-RPC fixture · 하네스 MCP 예시)은 도구와 같은 커밋에서 다시 만든다.

## 9. 노출 경로 (R7)

| 경로 | 사용자 설정 | 서버가 지키는 것 |
|---|---|---|
| 같은 호스트 | 없음 | bind `127.0.0.1`, 그래도 인증 |
| 포워딩 · 터널 | 주소가 다르면 `--public-url` | 출처 · 쿠키 `Path` 를 `public_url` 에서 |
| 리버스 프록시 (접두사) | `--public-url https://host/prefix/` · `--trusted-proxy <주소>` | 상대 경로만, `X-Forwarded-For` 는 신뢰 프록시에서만, `https` 면 `Secure` |
| 직접 노출 | `--bind <주소>` + TLS 또는 `--allow-plain-http` | 둘 다 없으면 시작하지 않는다, 경고 |

프록시 예시 — requirements §1.4 에서 잰 구성이다 (프록시는 `Set-Cookie` · `Location` 을 고치지 않는다). Caddy 의 `redir` 줄은 측정 구성에 없던 것을
따로 더해 302 → `/workbench/` → 200 을 확인했다:

```nginx
location /workbench/ { proxy_pass http://127.0.0.1:8766/; }      # /workbench → /workbench/ 는 nginx 가 301
```

```caddy
redir /workbench /workbench/
handle_path /workbench/* {
	reverse_proxy 127.0.0.1:8766
}
```

## 10. 모듈 (ADR-032 결정 1 · 9 · 11)

| 경로 | 무엇 |
|---|---|
| `workflow_kit/tools/workbench.py` | 명령 진입 (`tool_dispatch` · `pyproject` 등록) |
| `workflow_kit/workbench/server.py` | 라우팅 · 응답 머리 · §5.4 · §6 의 순서 |
| `workflow_kit/workbench/auth.py` | 토큰 읽기 · 세션 표 · 실패 제한 |
| `workflow_kit/workbench/views.py` | HTML 렌더 (`html.escape` 를 거치는 조립 함수) |
| `workflow_kit/workbench/state_view.py` | §7 의 값 (화면과 `api/state` 가 같이 쓴다) |
| `workflow_kit/workbench/respond.py` | 폼 → 응답 본문 (§6 의 3~7) |
| `workflow_kit/workbench/static/workbench.css` · `workbench.js` | 내장 자원 — `pyproject` `package-data` |
| `workflow_kit/common/todo_list.py` | todo 파일(§13)의 유일한 읽기 · 쓰기 창구 — CLI 와 워크벤치가 같이 쓴다 |
| `workflow_kit/tools/todo.py` | `todo` 명령 진입 (`tool_dispatch` · `pyproject` 등록) |

## 11. 검증 (R10)

**모든 case 는 되주입으로 red 를 확인한다.**

| 검사 | case |
|---|---|
| `check_workbench_auth.py` | 시작 거절(토큰 없음 · 짧음 · 모드 넓음 · 이름 겹침 · 평문 노출) · 세션 없는 요청 401 · viewer POST 403 · 로그인 실패 제한 429 · 질의 토큰 400 · §5.4 네 단계마다 어긋난 요청 → 받은편지함 무변경 · 응답 머리 (§4.2) · 쿠키 속성 (`Lax` · `Path` · `HttpOnly` · `https` 의 `Secure`) |
| `check_workbench_proxy.py` | 검사 안의 접두사를 벗기는 프록시 뒤에서 로그인 → 계획 → 제출 → 도착이 전부 접두사 안 (판정은 도착 경로), 쿠키 `Path` = 접두사. 되주입: 절대 `Location` · `Path=/` |
| `check_workbench_write.py` | 왕복 — 서버가 쓴 응답이 `plan-import` 의 1~6 단계를 통과하고 상태에 든다 · 동시 제출(스레드 · 프로세스)에서 유실 0 · 독자가 덜 쓰인 파일을 보지 않는다 (번호는 연속이 아니다 — ADR-032 V7) · 되주입: `publish` 를 배타 생성 없이 · 임시 이름 없이 이어 쓰기(만들기와 쓰기 사이의 정해진 멈춤으로 결정적으로) · 413 · 422(선택지 밖 · 한도 · 제어 문자) · 409(지문 · 배치 · 오류 규칙) — 전부 받은편지함 무변경 · `answered` 결정의 조작된 값 무시 · 같은 응답자의 `received_at` 단조 증가 |
| `check_workbench_open.py` | 개방 모드(§5.6) — 비 loopback 평문 허용 · 경고 한 줄 · `--open`+`--token` 거절 · 쿠키 없는 GET 200 · 로그아웃 없음 · `Host` 출처 제출 통과 · 다른 출처 403 · `responder` · `client` · `plan-import` 반영 · 토큰 모드 그대로 · 주소 정리 · DNS rebinding 403 · 세션 표 상한 |
| `check_workbench_autostart.py` | 자동 기동(§3.1) — `--autostart on/off` · 인자 검증 · `session-start` 가 띄우고 다시 띄우지 않음 · 시작 실패 경고 한 줄 · 끄는 표식 둘 · `--stop` 의 안전(손으로 띄운 서버 · 워크벤치 아닌 pid) · SessionEnd hook · 대기 시간 초과는 자식을 거둔다 · pid ↔ 포트 주인 대조(instance) |
| `check_workbench_design.py` | 화면 구조(§4.4) — 요약 수치 = `api/state` · 보드 4열 · 계획 카드 강조 · 마일스톤 막대 · 완료분만 접기 · 열린 결정 강조 · 결정은 닫힌 채 · 선택지 카드 · 제출 막대 · `style=` · 인라인 스크립트 · 외부 URL 없음 · 어두운 모드 · 좁은 폭 · 박스 넘침 방지 바탕 규칙 · 자른 글의 title |
| `check_workbench_refresh.py` | 자동 새로고침(§4.5) — `data-refresh` · 스크립트 · `data-version` · CSP `connect-src` · 같은 상태의 지문 고정 · 바뀌면 달라짐 · 0 이면 끔 · `--refresh` 범위 · 자동 기동 저장 · 스크립트 분기(실제 브라우저 동작은 task Proof 의 CDP 실측) |
| `check_workbench_live.py` | 실시간 값(§7.1) — 낡은 `state.json` 위에서 방금 바뀐 task 가 보임 · `source` · 화면 표식 · 저장소 무변경 · 지문 같으면 재계산 0 · 바뀌면 재계산 · 프로필 없으면 생성물 · `where_for` 가 프로필을 싣는다 · 브랜치 전환 재계산 · 실패 사유 표시 · roadmap 실시간 · 낡은 roadmap 생성물 안 보임 · 산출물 지문 · 실패 사유에 절대 경로 없음 |
| `check_workbench_progress.py` | 진행 기록 — `--progress-note` 시각 접두 · 손으로 적은 시각 그대로 · 시각 아닌 백틱엔 붙임 · 이스케이프 · 차단 항목 · `api/state` progress = task 파일 · 계획 카드 · 보드의 '지금' · 노트 바뀌면 지문 바뀜 · 스킬 · CLAUDE.md 규칙 |
| `check_workbench_inbox_hook.py` | 도착 신호 · hook 반영(§6.1) — 서버는 stamp 만 · 화면 반영 대기→반영됨 · hook JSON(이벤트 · 결정 변화) · seen 시각 · 할 것 없으면 조용 · 자격 없는 응답은 남기고 사유 · hooks.json 명령을 실제 셸로 · 신호 없으면 Python 안 띄움 · 같은 초의 두 번째 응답(셸 · Python) · cwd 밖 · 옛 kit 뿐이면 한 번 알림 |
| `check_todo_list.py` | todo(§13) — 왕복(추가 · 끝냄 · 되돌림 · 고침 · 삭제 · 형식) · 손으로 쓴 파일의 결정적 id · 낯선 줄 · 제목 붙은 머리 · 범위 아닌 머리 보존 · code 별 거절(C0 · C1 · 줄 구분자 포함)과 파일 무변경 · 손글 NEL · 없는 브랜치 디렉터리 안 만듦 · 출발 장벽 두 프로세스 동시 쓰기 200건 보존 · CLI 조작 · 종료 코드 · dispatcher · pyproject |
| `check_workbench_todo.py` | todo 화면 · 편집(§13.1) — 진척 화면 할 일 · `todo n/m` · 체크리스트 · `api/state` · viewer 읽기만 · 이스케이프 · 폼 제출 왕복과 돌아갈 곳 · 401 · 403(viewer · Origin · CSRF) · 413 · 400 · 422 · 404 무변경 · hook 알림 한 번 · CLI 변경 안 알림 · 지문 · 넘침 방지 · 쓰는 중 |
| `check_workbench_views.py` | 선언 ≠ 파생 둘 다 · 잎 0 "미측정" · 절대 경로 · 호스트 이름이 어느 응답에도 없음 (`api/state` 포함) · 이스케이프 (task 파일의 `<script>` 가 글자로) · 읽기 전용 (`git status` 전후 동일) · 정적 자원이 wheel 에 실림 |

파서 단일성은 `check_plan_claims` case 6 의 소비자 목록에 `workbench/` 를 더해 그 한 곳에서 잰다 (ADR-032 결정 2).
쓰는 쪽 × 옮기는 쪽 · 옮기는 쪽 둘의 경합(requirements R10-4 의 뒤 절반)은 `check_plan_import` case 9 가 이미 잰다 — 서버는 같은 `publish` 를 쓴다.

실물 프록시(nginx · Caddy)와 실제 브라우저는 게이트에 넣지 않는다 — requirements §1.4 의 절차로 서버의 경로 · 쿠키 코드를 바꿀 때 다시 잰다.
Windows(NTFS) 의 포트 bind · 토큰 파일 모드(POSIX 모드 없음) · 콘솔 인코딩은 구현 뒤 Windows 호스트에서 잰다.

## 12. requirements 대응

| requirements | 이 문서 | 비고 |
|---|---|---|
| R0 | §1 | 쓰는 파일이 둘 (ADR-032 V6) |
| R1.1 · R1.2 | §2 | |
| R1.3 | §3 | `.workbench/` 는 자기 무시 (ADR-032 결정 21) |
| R2.1 · R2.2 · R2.3 · R2.4 | §4 | |
| R3.1 · R3.2 | §5.1 · §5.2 | |
| R3.3 · R3.4 | §5.3 | `SameSite=Lax` (ADR-032 V1) |
| R4.1 · R4.2 · R4.3 | §5.4 · §5.5 | 위임 인증 없음 |
| R5.1 · R5.2 · R5.3 · R5.4 | §6 | 번호는 주장 스펙 §7-1 (ADR-032 V2), 자격 있는 파일의 시각만 (V3), 배치 409 (V5) |
| R5.5 | 주장 스펙 §7 · §9 | `plan-import` 가 구현했다 |
| R6.1 · R6.2 · R6.3 | §7 | 건수는 `inbox_census` (V4) |
| R7 | §9 | 프록시 예시는 requirements §1.4 의 실측 |
| R8.1 · R8.2 | §8.2 | 우회 검출의 받은편지함 행 (V5) |
| R9 | §8.3 | |
| R10 | §11 | 실물 프록시 · 브라우저는 게이트 밖, 번호 연속은 없다 (V7), 경합의 뒤 절반은 `check_plan_import` case 9 |
| R11 | requirements §1.4 · §10 | design 전 둘: 프록시 · 브라우저 완료, Codex 주입은 재지 않는다 (소유자 결정) |
| R12 | ADR-032 Status | |

## 13. todo — 브랜치 할 일 · task 체크리스트 (소유자 지시 2026-11-16, TASK-2026-11-16-main-016)

소유자 결정: 브랜치 할 일(아직 task 가 아닌 일)과 task 체크리스트를 **둘 다** 두고, 워크벤치가 **바로 파일에 쓴다**.

- 파일은 `<branch_dir>/todo.md` 하나다 (ADR-032 V11). task 파일에 두지 않는다 — task 파일의 작성자는 작업 세션 하나다(결정 15).
- 형식: 머리 `# Todo`, 절 `## Branch` 와 `## <TASK-ID>`, 항목 `- [ ] 글 <!-- id:<hex> -->` · 끝낸 항목 `- [x]`. 항목이 없는 task 절은 쓰지 않는다.
- id 는 쓸 때 붙는다. 손으로 쓴 id 없는 줄은 (절 · 글 · 같은 글의 몇 번째)에서 **결정적으로** 만든 id 로 읽는다. 항목도 절 머리도 아닌 줄은 버리지 않고 그 자리에 다시 쓴다.
- 절 머리 뒤에 붙은 글(`## TASK-… — 제목`)은 그 절로 읽고 다시 쓸 때 그대로 둔다. 범위가 아닌 `## ` 머리 아래 줄은 어느 절에도 세지 않고 파일 끝에 그대로 다시 쓴다. 줄은 `\n` 하나로만 끊는다 (U+0085 · U+2028 을 줄 경계로 보지 않는다).
- 글: 앞뒤 공백을 다듬은 한 줄 · 1~300자 · 제어 문자(유니코드 Cc — C0 · DEL · C1) · 줄 · 문단 구분자(U+2028 · U+2029) 없음 · `<!--` / `-->` 없음. task 절은 그 브랜치에 task 파일이 있을 때만 만든다.
- 브랜치 메모리 디렉터리가 없으면 쓰지 않는다(`not_found`) — 그 디렉터리는 `backlog-update` 만 만든다.
- 쓰기는 `<branch_dir>/.todo/lock`(자기 무시 `.gitignore`) 배타 락 아래 *읽기 → 적용 → 원자 교체* — 기다림 상한 5초, 넘으면 `busy`.
- 읽기 · 쓰기는 `common/todo_list.py` 만 한다. 작업 세션은 `python -m workflow_kit todo` 를 쓴다:

| 인자 | 하는 일 |
|---|---|
| (없음) · `--task <ID>` | 목록 — 절마다 `(끝냄/전체)` 와 항목 id. `--format json` 은 `items` · `counts` |
| `--add "<글>" [--task <ID>]` | 더한다 (`--task` 가 없으면 브랜치 할 일) |
| `--done <id>` · `--undo <id>` · `--remove <id>` | 끝냄 · 되돌림 · 삭제 |
| `--edit <id> --text "<글>"` | 글을 고친다 |

종료 코드: 0 성공 · 1 없는 id · 없는 task(목록 `--task` 포함) · 브랜치 메모리 없음 · 락 시간 초과 · 2 인자 · 글이 틀렸다.

### 13.1 워크벤치 (TASK-2026-11-16-main-017)

- 진척 화면: 요약 수치 아래 **할 일** — 브랜치 할 일과 `끝냄/전체`, 항목마다 끝냄 단추(☐ · ☑) · 글(3줄 clamp, 전문은 `title`) ·
  '고치기'(글 · 삭제), 끝에 추가 폼. 계획 카드와 작업 보드의 task 에 `todo n/m` 칩, todo 가 있는 task 는 보드에서 링크된다.
- 계획 화면: 머리 카드 다음 **체크리스트** — 그 task 절에 같은 조작. 브랜치 할 일은 섞지 않는다.
- `api/state` 에 `todo: {branch: [...], counts: {절: [끝냄, 전체]}, error}` — 읽지 못하면 `branch: null` 과 사유.
- viewer 는 읽기만 (폼 없음). 개방 모드는 approver 다.
- `POST todo` 필드: `csrf` · `action`(`add` · `done` · `undo` · `edit` · `remove`) · `id` · `text` · `scope`(추가 · 기본 `Branch`) ·
  `back`(빈 값 = 진척 화면 · `task/<TASK-ID>`). 순서: 본문 크기(8,192) → 세션 401 → approver 403 → `Origin` 403 → CSRF 403 →
  `back` 400 → §13 의 거절(`invalid` 422 · `not_found` 404 · `busy` 503). 하나라도 어긋나면 쓰지 않고 기록도 남기지 않는다. 성공은 303 → `back`.
- 바꾼 뒤 checkout 루트의 `.workbench/todo-events.jsonl` 에 한 줄(시각 · 누가 · 동작 · 항목)을 더하고 도착 신호(§6.1 의 stamp)를 남긴다.
  작업 세션 hook(`plan-import --hook`)이 그 줄을 **읽고 비워** `[워크벤치] 소유자가 todo 를 바꿨다` 블록으로 싣는다 — 한 번만, 20줄 넘으면 '외 N건'.
  작업 세션의 `todo` CLI 변경은 기록하지 않는다.
- 자동 새로고침(§4.5)은 todo.md 가 바뀌면 지문이 바뀌어 화면을 갈아 끼운다. todo 폼에 글을 쓰는 중이거나 '고치기'를 펼친 동안은 갈아 끼우지 않고 알림만 낸다.
