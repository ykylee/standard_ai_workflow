# 계획·진척 워크벤치 스펙

- 문서 목적: 브라우저에서 task 의 계획(주장 · 결정)과 진척을 읽고 결정에 답하는 `workbench` 서버의 kit 계약(명령 · 수명 · 경로 · 인증 · 응답 쓰기 · 진척 값 · 알림 · MCP · 노출 · 모듈 · 검증)을 정의한다.
- 범위: `python -m workflow_kit workbench`, 서버가 서빙하는 경로와 화면, 서버가 받은편지함에 쓰는 응답, 받은편지함 건수의 정본 함수, MCP 도구 `plan_inbox` · `plan_import`, §11.1 한 줄과 스킬, 검사 넷
- 대상 독자: workflow 설계자, AI agent, kit 소비 프로젝트
- 상태: draft (ADR-032 accepted 2026-11-13 — M-029 ② 서버 · 화면 · 검사 · MCP 두 도구 구현 2026-11-14, Windows 실측 전)
- 최종 수정일: 2026-11-14
- 관련 문서: `../../ai-workflow/wiki/decisions/adr-032-plan-workbench.md`, `../../docs/planning/plan-workbench-requirements-2026-11.md`, `./claim_plan_spec.md`, `./global_workflow_standard.md`

> **결정 근거는 ADR-032 에, 숫자의 실측은 requirements 에 있다.** 이 문서는 *계약* 만 적는다.
> 괄호 안의 `R…` 은 requirements(`plan-workbench-requirements-2026-11.md`)의 요구 사항 번호다 — 대응표는 §12.
> 응답 파일 형식 · 받은편지함 · 번호 · `plan-import` · 결정 상태 계산은 `claim_plan_spec.md` 가 정본이다 (아래에서 "주장 스펙 §…").

## 1. 불변 조건 (R0)

1. 서버 · 화면 · 알림은 파일 · CLI · MCP · 표준 HTTP 로만 선다 — 어느 하네스의 전용 표면에도 기대지 않는다.
2. 서버가 쓰는 워크플로우 상태는 **받은편지함 하나**다 (주장 스펙 §7). task 파일 · 보관 · `state.json` · `roadmap_state.json` 은 읽기만 한다.
   그 밖에 쓰는 것은 `.workbench/server.json` 과 그 디렉터리의 `.gitignore` 뿐이다 (§3). 접근 기록은 표준 오류로 낸다.
3. 폼으로 들어온 글은 데이터다 — 실행하지 않고, 경로로 쓰지 않고, 다른 곳으로 보내지 않는다. task 파일의 글도 화면에 넣을 때 이스케이프한다.
4. 화면의 숫자는 생성물과 task 파일에서만 온다. 재지 않은 것은 "미측정" 이다.
5. loopback 요청도 인증한다. 서버는 자기 공개 주소를 추측하지 않는다 — `public_url` 하나.
6. 페이지는 외부 자원을 부르지 않는다.
7. 모델 호출이 없다.
8. 주장 · 결정 읽기 · 지문 · 결정 상태 · 응답 렌더 · 공개 · 받은편지함 건수는 `plan_claims` · `plan_tasks` · `plan_responses` 의 함수만 쓴다
   (`inbox_census` — §8.1).

## 2. 명령 (R1.1 · R1.2)

```
python -m workflow_kit workbench [--bind 127.0.0.1] [--port 8766] [--public-url URL]
    --token <viewer|approver>:<name>=env:<VAR>|file:<path> [--token …]
    [--trusted-proxy ADDR]… [--tls-cert PATH --tls-key PATH] [--allow-plain-http]
python -m workflow_kit workbench --status
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
- `--status` 는 `.workbench/server.json` 을 읽어 `{"running": bool, "pid": …, "port": …, "public_url": …, "started_at": …}` JSON 한 덩어리를 내고 끝난다
  (기록이 없거나 `pid` 가 죽었으면 `running: false`).
- 정본 §11.1 에 `Review plans and progress in a browser | python -m workflow_kit workbench`. 스킬 `workbench` (+ bootstrap `/workflow-workbench`) —
  띄우는 법 · 토큰 만드는 법 · URL 을 사용자에게 알리는 것까지. 모델은 서버를 조작하지 않는다.

## 3. 수명 (R1.3)

- 실행 기록은 **checkout 루트**의 `.workbench/server.json` — `pid` · `port` · `public_url` · `started_at`. 토큰 · 세션은 싣지 않는다.
  `.workbench/` 는 자기 무시 디렉터리다: 안의 `.gitignore` 가 `*\n` 인지 시작할 때마다 확인하고 다르면 다시 쓴다.
- checkout 하나에 서버 하나 — 기록의 `pid` 가 살아 있으면 시작을 거절한다. 죽은 `pid` 의 기록은 덮어쓴다. 정상 종료 때 기록을 지운다.
- 요청마다 현재 브랜치를 다시 읽는다 — 화면 머리에 브랜치 이름을 보인다.
- 세션 · 로그인 실패 표는 메모리에만 있다. 다시 띄우면 다시 로그인한다.
- `session-start` 는 서버를 띄우지 않는다. 기록의 `pid` 가 살아 있으면 보고의 `summary` 에 `워크벤치 실행 중: <public_url>` 한 줄.

## 4. 경로 · 머리 · 화면 (R2)

### 4.1 경로 — 이것 말고는 404

| 메서드 · 경로 (`public_url` 기준 상대) | 역할 | 인증 | 실패 |
|---|---|---|---|
| `GET healthz` | `ok` | 없음 | — |
| `GET login` · `POST login` | 토큰 폼 · 세션 시작 | 없음 | 401 (같은 폼) · 429 · 403 (`Origin`) · 413 (본문 > 4,096) |
| `POST logout` | 세션 끝 | 세션 | 401 · 403 (`Origin` · CSRF) |
| `GET ` (루트) | 진척 화면 (§7) | viewer 이상 | 세션 없음 → 303 `login` |
| `GET task/<TASK-ID>` | 계획 화면 (§4.4) | viewer 이상 | 세션 없음 → 303 `../login` · 없는 task 404 |
| `POST task/<TASK-ID>/respond` | 결정 응답 (§6) | approver | §5.4 · §6 |
| `GET api/state` | 진척 값 JSON (§7.3) | viewer 이상 | 401 |
| `GET static/<이름>` | 내장 자원 (고정 목록) | 없음 | 404 |

`<TASK-ID>` 는 작업 항목 ID 문법(`project_docs.WORK_ITEM_ID_PATTERN`)에 맞고 현재 브랜치에 그 task 파일이 있을 때만 받는다.

### 4.2 응답 머리

모든 응답: `Content-Security-Policy: default-src 'none'; style-src 'self'; script-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'`,
`X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` (`static/` 는 `max-age=3600`). 인라인 스크립트 · 스타일 없음.

### 4.3 상대 경로

링크 · 폼 action · `Location` 은 전부 상대 경로다. 절대 URL 은 시작 시 출력 하나뿐이다. 렌더러는 현재 경로의 깊이로 상대 경로를 만드는 함수 하나를 쓴다.

### 4.4 계획 화면

task 파일에 있는 것만 그린다: 주장 트리(`<details>`, 접힌 상태 = 1단계 목록, ID 그대로) · 3단계 위치(경로와 줄만) · 주장별 완료 기준과 검증 줄
(`plan_claims.claim_bundles` 의 묶음 — `Verification` 줄의 글은 그대로 보이고 판정을 추론하지 않는다) · 결정(가리키는 주장 안에 닫힌 `<details>` 하나씩 — 질문 · 선택지 radio · 기본값에 "추천" 과 `checked` · **계산한**
상태, 칸이 다르면 "task 파일의 칸은 <값>") · 머리의 "열린 결정 n건" · "미반영 응답 n건" · 배치 문제(있으면) · 끝에 `Out of scope`.
`answered` 결정은 읽기 전용(답과 함께). 주장이 없는 task 는 Description · 완료 기준 · Plan 나머지 필드를 그대로(폼 없음). viewer 에게는 폼이 없다.

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

## 7. 진척 (R6)

### 7.1 원천

| 보이는 것 | 원천 |
|---|---|
| 마일스톤 · WBS · 파생 진척 · issues · `deliverables_missing` | `roadmap/roadmap_state.json` |
| 진행 · 차단 · 계획 · 최근 완료 task | 브랜치 `state.json` |
| 완료 기준 · 검증 줄 · 주장 · 결정 | task 파일 |
| 결정 상태 | `plan_tasks.computed_states` (보관 응답 포함) |
| 미반영 응답 · 알 수 없는 항목 · 배치 문제 | `plan_responses.inbox_census` (요청 시점) |

### 7.2 표시 규칙

선언 ≠ 파생이면 둘 다 · 진척은 센 값("완료 잎 3 / 전체 4")과 그 두 수에서만 그린 막대 · 잎 0 은 "미측정"(0% 로 그리지 않는다) · 검증 줄 없는 완료 기준은 "미측정" ·
결정 칸 ≠ 계산값이면 계산값과 "task 파일의 칸은 <값>" · 생성물마다 `generated_at` · 싣지 않는 것: 절대 경로 · 호스트 이름 · 사용자 홈 · 환경변수 · 토큰 이름 목록
(경로는 저장소 상대, 브랜치 이름은 싣는다) · 다른 worktree 는 보이지 않는다.

### 7.3 `api/state`

```json
{"schema": "workbench-state/1", "branch": "<branch>",
 "generated_at": {"roadmap": "<iso|null>", "state": "<iso|null>"},
 "milestones": [{"id": "M-0NN", "title": "…", "declared": "<status>", "derived": "<status>",
                 "leaves_done": 3, "leaves_total": 4, "issues": ["…"]}],
 "tasks": {"in_progress": [{"id": "…", "title": "…"}], "blocked": […], "planned": […], "recent_done": […]},
 "issues": ["<code>: <detail>"],
 "plans": [{"task": "<TASK-ID>", "title": "…", "status": "<status>", "open_decisions": ["D1"], "pending_responses": 1}],
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

## 11. 검증 (R10)

**모든 case 는 되주입으로 red 를 확인한다.**

| 검사 | case |
|---|---|
| `check_workbench_auth.py` | 시작 거절(토큰 없음 · 짧음 · 모드 넓음 · 이름 겹침 · 평문 노출) · 세션 없는 요청 401 · viewer POST 403 · 로그인 실패 제한 429 · 질의 토큰 400 · §5.4 네 단계마다 어긋난 요청 → 받은편지함 무변경 · 응답 머리 (§4.2) · 쿠키 속성 (`Lax` · `Path` · `HttpOnly` · `https` 의 `Secure`) |
| `check_workbench_proxy.py` | 검사 안의 접두사를 벗기는 프록시 뒤에서 로그인 → 계획 → 제출 → 도착이 전부 접두사 안 (판정은 도착 경로), 쿠키 `Path` = 접두사. 되주입: 절대 `Location` · `Path=/` |
| `check_workbench_write.py` | 왕복 — 서버가 쓴 응답이 `plan-import` 의 1~6 단계를 통과하고 상태에 든다 · 동시 제출(스레드 · 프로세스)에서 유실 0 · 독자가 덜 쓰인 파일을 보지 않는다 (번호는 연속이 아니다 — ADR-032 V7) · 되주입: `publish` 를 배타 생성 없이 · 임시 이름 없이 이어 쓰기(만들기와 쓰기 사이의 정해진 멈춤으로 결정적으로) · 413 · 422(선택지 밖 · 한도 · 제어 문자) · 409(지문 · 배치 · 오류 규칙) — 전부 받은편지함 무변경 · `answered` 결정의 조작된 값 무시 · 같은 응답자의 `received_at` 단조 증가 |
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
