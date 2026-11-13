---
type: decision
status: proposed
adr_id: ADR-032
decided_at: 2026-11-13
alternatives_considered: [samesite-strict, strict-with-next-param, single-module-in-common, jinja-templates, token-config-file, root-gitignore-entry, mcp-tools-later, docker-proxy-in-gate, server-calls-plan-import, counter-numbering]
related_pages: [decisions/adr-031-claim-plan, decisions/adr-030-compact-relay, decisions/adr-027-roadmap-wbs-sdlc]
created: 2026-11-13
updated: 2026-11-13
r9_skip: true
---

# ADR-032: 계획·진척 워크벤치 — 브라우저에서 계획을 읽고 결정에 답하는 표준 라이브러리 서버

## Status

**Proposed** (2026-11-13, design 단계 — TASK-2026-11-13-claude-remote-sync-check-234c32-006, M-027/WBS-27.1).
requirements 정본은 `docs/planning/plan-workbench-requirements-2026-11.md` (sign-off Q1 · Q2, design 전 실측 §1.4),
kit 계약 정본은 `workflow-source/core/plan_workbench_spec.md`. 응답 파일 형식 · 받은편지함 · `plan-import` 는 ADR-031 과
`workflow-source/core/claim_plan_spec.md` 가 정본이고 이 ADR 은 그것을 **소비**한다 — 다시 정하지 않는다.

소유자가 이미 연 결정: SameSite 는 **Lax** (2026-11-13, task -006 의 D1 — requirements R3.3 대비 변경 V1).

## Context

ADR-031 로 task 의 주장 · 결정과 응답 파일 계약이 섰고 2단계 구현(M-028/WBS-28.2)이 끝났다. 결정은 대화에서 `answered` 로
닫을 수 있지만, 소유자가 주장 트리를 펼쳐 보고 결정마다 열어 본 뒤 답하는 화면은 없다. requirements(M-025)가 그 화면을 서버
하나로 고정했다: 표준 라이브러리 HTTP 서버, 항상 인증(viewer / approver), 상대 경로, 받은편지함에만 쓴다.

design 이 정할 것 (M-027): 서버 모듈 배치와 CLI 등록 · 토큰 설정의 형태 · 세션 표 · 화면 렌더러 · 내장 정적 자원 ·
`.workbench/` 와 받은편지함의 git 무시 수단 · MCP 도구 둘 · §11.1 문구와 스킬 · 검사 구성.
ADR-031 이 넘긴 것: MCP 도구 `plan_inbox` · `plan_import` (결정 23), 쓰는 쪽의 LF 의무 (결정 25), 번호 규칙 (결정 13 · 24).
2단계 구현이 넘긴 것 (handoff §5, 2026-11-13): 원본 받은편지함에 미반영이 있는 채 되돌려 적기로 원본 task 가 `done` 이 되는 길 ·
같은 디렉터리 배치를 `plan-status` · 게이트가 보지 않음 · 받은편지함 건수를 세는 길이 여럿 · `pending_responses` 의 의미 둘 ·
보관의 링크 · 비파일 항목 보고.

### design 전 실측 (requirements §1.4 — 2026-11-13, Linux 호스트)

| # | 실측 | 결과 | 이 ADR 에 미친 것 |
|---|---|---|---|
| M1 | nginx 1.27.5 · Caddy 2.10.0 실물(docker, digest 기록) 뒤에서 Chrome 154 로 §1.3 의 네 구성 | 프로토타입 프록시와 같다 — 상대 경로 + `Path` = 접두사만 접두사 안에 머물고 다른 앱에 쿠키가 가지 않는다 | 결정 6 · 7 그대로 |
| M2 | 같은 측정, 다른 사이트(`localhost`)의 링크 · 폼으로 들어오기 | `SameSite=Strict` 는 로그인해 둔 상태에서도 다른 사이트의 링크에서 로그인 화면으로 떨어진다. `Lax` 는 그 링크에 쿠키를 싣고, 두 설정 모두 다른 사이트의 POST 에는 싣지 않았다(Origin 대조가 403) | 결정 8 (V1) |
| M3 | 매치되지 않는 경로 · 끝 슬래시 없는 접두사 | nginx 404 · `/workbench` → 301, Caddy 는 둘 다 **빈 200** | 결정 21 (Caddy 예시에 `redir`), 결정 19 (검사는 도착 경로로 판정) |
| M4 | 9 구성 × 2 회 | 두 회가 같았다 | — |

재지 않은 것: TLS 뒤의 `Secure` 쿠키, Firefox · Safari, 클라우드 작업 공간의 포트 공유, Codex hook 주입(소유자 결정 — 재지 않는다),
Windows(NTFS) — 구현 뒤 (결정 22).

## Decision

### 배치 · 명령

1. **`workflow_kit/workbench/` 패키지를 새로 둔다.** `server.py`(라우팅 · 응답 머리 · 대조 순서) · `auth.py`(토큰 읽기 · 세션 표 ·
   로그인 실패 제한) · `views.py`(HTML 렌더러) · `state_view.py`(진척 화면과 `api/state` 의 값) · `respond.py`(폼 → 응답 파일 본문) ·
   `static/`(내장 자원). 명령 진입은 `workflow_kit/tools/workbench.py` 하나 — `tool_dispatch` 와 `pyproject` 에 등록한다.
   대안 — `common/registry_server.py` 처럼 모듈 하나: 인증 · 렌더 · 쓰기가 한 파일에 1,000줄을 넘고, 검사가 렌더만 바꿔도 인증 검사까지
   돈다 (`--changed` 의 단위가 파일이다).
2. **계산은 전부 기존 함수다.** 주장 · 결정 읽기 · 지문 · 결정 상태는 `plan_claims` · `plan_tasks`, 응답 파일의 렌더 · 공개 · 번호 ·
   받은편지함 건수는 `plan_responses` (requirements R0-8 · 주장 R0-6). `workbench/` 는 이 함수를 부르기만 한다 —
   `check_plan_claims` 의 파서 단일성 case 가 `workbench/` 를 소비자 목록에 더한다.
3. **CLI 는 requirements R1.1 그대로**다 (`--bind` · `--port` 8766 · `--public-url` · `--token` · `--trusted-proxy` · `--tls-cert` ·
   `--tls-key` · `--allow-plain-http` · `--status` · `--new-token … --out`). `allow_abbrev=False`.

### 토큰 · 세션 · 쿠키

4. **토큰은 `--token <role>:<name>=env:<변수>` · `=file:<경로>` 로만 받는다** (R3.1). 설정 파일은 두지 않는다 — 대안
   `.workbench/tokens.toml` 은 비밀을 checkout 안에 두게 하고, 그 파일의 git 무시가 깨지면 토큰이 커밋된다. 토큰을 거두는 길은
   값을 바꾸고 다시 띄우는 것 하나다.
5. **세션 표는 프로세스 메모리의 사전 하나**다 — 세션 id(`secrets.token_urlsafe(32)`) → 이름 · 역할 · CSRF 값 · 만료 시각.
   `threading.Lock` 아래에서 읽고 쓴다. 만료는 12시간, 요청 때 지난 것을 걷는다. 로그인 실패 표도 같은 방식이다 (주소 → 최근 실패 시각들).
6. **쿠키 `Path` 와 출처는 `public_url` 하나에서만** 얻는다 (R3.4 — M1). 서버는 `Host` 로 자기 주소를 추측하지 않는다.
7. **모든 링크 · 폼 action · `Location` 은 상대 경로다** (R2.3 — M1). 렌더러는 현재 경로의 깊이에서 상대 경로를 만드는 함수 하나를 쓴다
   (`task/<ID>` 에서 루트는 `../`, 루트에서 task 는 `task/<ID>`).
8. **세션 쿠키는 `SameSite=Lax`** 다 (소유자 결정 2026-11-13 — M2, requirements R3.3 대비 변경 V1). 다른 사이트의 링크(채팅 · 리뷰 댓글)로
   계획 화면에 바로 들어올 수 있어야 쓰인다. 지키는 것은 그대로다: 모든 POST 는 `Origin` = `public_url` 의 출처 · CSRF 값을 대조하고
   (Lax 도 다른 사이트의 POST 에 쿠키를 싣지 않는다 — M2), 모든 GET 은 읽기 전용이며(R0-2), `frame-ancestors 'none'` 이라 다른 사이트가
   화면을 틀에 넣지 못한다. 대안 — Strict 유지: 링크마다 로그인을 거친다. 대안 — Strict + 로그인 뒤 원래 경로로 돌려보내는 `next`
   값: 열린 리다이렉트를 막는 검증이 하나 더 는다 (`next` 가 경로 표의 경로인지).

### 화면 · 자원

9. **HTML 은 서버가 문자열로 만든다** — 표준 라이브러리 `html.escape` 를 거치는 작은 조립 함수만 쓴다. 대안 — Jinja 같은 템플릿 엔진:
   의존성이 늘고(kit 은 런타임 의존을 최소로 둔다), 자동 이스케이프의 범위를 따로 재야 한다. 모든 값은 이스케이프를 거쳐 들어간다 —
   task 파일의 글은 데이터다 (R0-3).
10. **스크립트는 하나, 일은 하나**다: 결정의 `<details>` 가 처음 열리면 그 결정의 숨은 `opened_<D>` 를 `yes` 로 (R5.2). 인라인 스크립트 ·
    스타일은 없다 (R2.2 CSP). 스크립트가 꺼져도 화면 · 제출은 된다 — 열림 기록만 없다.
11. **정적 자원은 패키지 데이터**(`workflow_kit/workbench/static/*.css` · `*.js`)이고, 서버는 시작할 때 **고정 목록**만 읽어 메모리에 두고
    `static/<이름>` 으로 낸다. 목록 밖은 404 — 경로 조각으로 파일을 가리킬 수 없다. `pyproject` 의 `package-data` 에 더하고, wheel 에
    실리는지를 검사가 본다 (kit 은 패키지 밖 자산이 설치본에서 사라진 선례가 있다 — `assets/hooks`).

### 쓰기 · 받은편지함

12. **응답 파일은 `plan_responses.render_response` 로 만들고 `plan_responses.publish` 로 받은편지함에 공개한다** (ADR-031 결정 13 · 24 ·
    `claim_plan_spec` §6 · §7). requirements R5.3-7 의 "가장 큰 번호 + 1" 은 ADR-031 결정 13 이 이미 바꿨다 — 번호는 `received_at` 의
    epoch 마이크로초에서 출발하고 접미사를 통틀어 유일하다. 쓰는 쪽의 LF 의무(ADR-031 결정 25)는 렌더가 `\n` 으로만 잇는 것으로 지키고,
    주석의 CRLF 는 렌더 전에 LF 로 고친다 (R5.3-4).
13. **같은 응답자의 `received_at` 은 늘 늘어난다** (R5.3-5): 그 task 의 받은편지함과 보관에서 **자격 있는** 그 응답자의 가장 늦은 시각보다
    늦지 않으면 1마이크로초 뒤로 민다. 자격 없는 파일의 시각은 보지 않는다 — 손으로 놓인 미래 시각 파일 하나가 응답자의 시계를 끌고 가지 않게.
14. **쓰기 전에 배치를 본다**: `plan_responses.layout_problem` 이 문제를 말하면 POST 는 409 와 그 사유이고 아무것도 쓰지 않는다
    (`claim_plan_spec` §7-8 · §7-9). 계획 화면 머리에도 같은 사유를 보인다.
15. **서버는 `plan-import` 를 부르지 않는다** (R0-2). 대안 — 제출 즉시 반영: 서버가 task 파일을 쓰게 되고, 작업 세션과 같은 파일을 두 프로세스가
    쓰게 된다. 반영은 작업 세션이 한다 — 화면은 "미반영 응답 n건" 을 보인다.

### 받은편지함 보고 · 이월 항목 (2단계 구현이 넘긴 것)

16. **받은편지함 건수의 정본은 `plan_responses.inbox_census(branch_dir)` 하나**로 접는다 — task 별 건수 · 알 수 없는 항목 · 배치 문제를 한 번에
    돌려준다. 게이트(`backlog-update`) · `session-start` · `plan-status` · `plan-import` · 워크벤치 · MCP `plan_inbox` 가 이것만 부른다.
    지금은 `inbox_files` · `pending_by_task` · `unknown_inbox_files` 를 각자 조합한다 — 하나가 바뀌면 보고가 갈린다 (2단계 검증 4차에서 실제로 갈렸다).
17. **`plan-import` 출력의 `pending_responses` 는 "지금의 건수" 로 맞추고, 반영 뒤 남을 건수는 `remaining_after` 로 따로 낸다.**
    `plan-status` 의 같은 이름 필드와 뜻이 같아야 한다. 두 필드 모두 아직 발행되지 않아 이름을 바꾸는 비용이 없다.
18. **우회 검출(`claim_plan_spec` §4, R3.4)에 받은편지함 행을 더한다**: `refresh-state` · `session-start` 는 `done` 인데 그 task 의 받은편지함에
    미반영 응답이 있으면 `done 인데 계획 응답 n건 미반영: <TASK-ID>` 를 싣는다. 2단계 검증이 찾은 길 — 원본 받은편지함에 응답이 온 뒤
    브랜치가 닫고 합류의 되돌려 적기로 원본 task 가 `done` 이 되는 것 — 은 `backlog-update` 전이를 거치지 않아 게이트로는 막을 수 없다.
    막지 않고 드러낸다 (열린 결정의 우회 검출과 같은 방식). 같은 자리에서 `plan-status` 는 `layout_problem` 과 보관의 링크 · 비파일 항목을
    `warnings` 에 싣는다.

### MCP · 정본 · 스킬 · 검사

19. **MCP 도구 둘을 이번 구현에 넣는다** (ADR-031 결정 23 — 서버와 한 번에): read-only 번들에 `plan_inbox`(task · 번호 · 응답자 ·
    `received_at` · 자격 단계, 주석 본문 없음 — R9), write 번들에 `plan_import`(CLI 와 같은 동작, 기본 dry-run, 적용은 `apply: true`).
    체크인 생성물(descriptor · JSON-RPC fixture · 하네스 MCP 예시)과 하드코딩된 도구 수(`check_v0_8_10_read_only_manifest_byte_identical` 의 13)를
    같은 커밋에서 다시 만든다. 대안 — 나중으로: 받은편지함에 응답이 생기는 것은 워크벤치가 있을 때뿐이라 둘은 같이 쓰인다.
20. **정본 §11.1 에 한 줄**: `Review plans and progress in a browser | python -m workflow_kit workbench` (R1.2). 스킬 `workbench` 하나
    (+ bootstrap slash command `/workflow-workbench`) — 본문은 서버를 띄우는 법 · 토큰을 만드는 법 · URL 을 사용자에게 알리는 것까지이고,
    모델이 서버를 대신 조작하지 않는다.
21. **`.workbench/` 는 자기 무시 디렉터리**다 — 안에 `*\n` 인 `.gitignore` 를 두고 서버가 시작할 때마다 확인한다 (ADR-030 의 `.compact/`,
    ADR-031 결정 14 의 받은편지함과 같은 수단). 대안 — 저장소 루트 `.gitignore` 에 줄: 재적용 전의 소비 프로젝트가 무방비다.
    프록시 예시(nginx · Caddy 각 한 덩어리)는 core 스펙 §9 에 M1 · M3 에서 잰 그대로 싣는다 — Caddy 에는 `redir /workbench /workbench/`.
22. **검사는 넷**이다 (requirements R10, core 스펙 §11):
    - `check_workbench_auth.py` — 토큰 · 로그인 · 실패 제한 · 세션 · POST 대조 네 단계 · 응답 머리.
    - `check_workbench_proxy.py` — 표준 라이브러리로 만든 **접두사를 벗기는 프록시**(검사 안에 둔다) 뒤에서 로그인 → 계획 → 제출 → 도착이
      전부 접두사 안, 쿠키 `Path` = 접두사. 판정은 상태 코드가 아니라 **도착 경로**다 (M3 — Caddy 는 접두사 밖에도 200 을 준다).
      되주입: 절대 `Location` · `Path=/`.
    - `check_workbench_write.py` — 왕복(서버가 쓴 응답이 `plan-import` 의 1~6 단계를 통과), 동시 제출 유실 0, 한도 413 · 422 · 409, 배치 409.
    - `check_workbench_views.py` — 선언 ≠ 파생 둘 다 · 잎 0 은 "미측정" · 절대 경로 · 호스트 이름이 어느 응답에도 없다 · 읽기 전용(`git status`
      전후 동일) · 이스케이프(task 파일에 `<script>` 를 넣어도 그대로 글자로).
    docker · 실제 브라우저는 게이트에 넣지 않는다 — 게이트가 docker 와 Chrome 에 묶이면 그것이 없는 호스트에서 돌지 않는다. 실물 측정(M1~M4)은
    requirements §1.4 의 절차로 남기고, 서버를 바꿀 때 다시 잰다. Windows(NTFS)의 포트 bind · 토큰 파일 모드 · 콘솔 인코딩은 구현 뒤
    Windows 호스트에서 잰다 (M-028 의 task -005 와 같은 호스트 · 같은 세션).
23. **구현은 마일스톤 하나**(M-029 — 이 ADR 이 accepted 되면 선언한다)로, 두 단계다: ① 이월 항목 정리(결정 16 · 17 · 18) — 서버 없이도
    값이 있고 작다 ② 서버 · 화면 · MCP · 정본 · 스킬 · 검사 넷.

## Requirements 대비 변경

| # | requirements | 이 ADR | 근거 |
|---|---|---|---|
| V1 | R3.3 쿠키 `SameSite=Strict` | **`Lax`** (결정 8) | M2 — Strict 는 다른 사이트의 링크에서 로그인으로 떨어진다. 소유자 결정 2026-11-13 |
| V2 | R5.3-7 번호 = 받은편지함 · 보관의 가장 큰 번호 + 1 | `received_at` 의 epoch 마이크로초, 접미사를 통틀어 유일 (결정 12) | ADR-031 결정 13 · 24 (두 호스트의 add/add 충돌) — 이미 구현됨 |
| V3 | R5.3-5 같은 응답자의 가장 늦은 `received_at` | **자격 있는** 파일만 본다 (결정 13) | 손으로 놓인 미래 시각 파일이 응답자의 시계를 끌고 가지 않게 |
| V4 | R6.1 "미반영 응답 건수 = 받은편지함을 요청 시점에 센 값" | 그 셈은 `inbox_census` 하나로 (결정 16) | 2단계 검증 — 세는 길이 여럿이면 보고가 갈린다 |
| V5 | (없음) | 쓰기 전 배치 판정 409 (결정 14) · task 파일이 오류 규칙을 어기면 409 (주장 스펙 §8.1 의 0 단계 — 어차피 자격이 없는 응답을 쓰지 않는다) · 우회 검출에 받은편지함 행 (결정 18) | ADR-031 2단계 구현이 넘긴 것 |

## Alternatives Considered

- **SameSite=Strict 유지 · Strict + `next`** — 결정 8.
- **모듈 하나(`common/workbench.py`)** — 결정 1.
- **템플릿 엔진** — 결정 9.
- **토큰 설정 파일** — 결정 4.
- **루트 `.gitignore` 줄** — 결정 21.
- **MCP 도구를 나중에** — 결정 19.
- **게이트에 docker 프록시 · 실제 브라우저** — 결정 22.
- **서버가 제출 즉시 `plan-import`** — 결정 15.
- **카운터 번호(requirements R5.3-7 그대로)** — V2.

## Consequences

- 소유자는 다른 사이트의 링크로 계획 화면에 들어와 결정을 열어 보고 답할 수 있다. 답은 받은편지함의 파일이고, 작업 세션이 `plan-import` 로
  반영할 때까지 상태를 바꾸지 않는다.
- 런타임 의존이 늘지 않는다 (표준 라이브러리 `http.server` · `ssl` · `html` · `secrets` · `hmac`).
- MCP 도구 수가 13(read-only 11 · write 2)에서 15(12 · 3)로 늘고 체크인 생성물 넷이 함께 움직인다.
- 실물 프록시 · 브라우저는 게이트가 재지 않는다 — 서버의 경로 · 쿠키 코드를 바꿀 때 requirements §1.4 의 절차를 다시 돌려야 한다.
- 받은편지함 건수의 정본이 하나가 되면서 `plan-status` · `plan-import` 의 출력 필드 하나의 뜻이 정해진다 (결정 17).

## References

- `docs/planning/plan-workbench-requirements-2026-11.md` (requirements, §1.4 실측, §13 sign-off)
- `docs/planning/plan-workbench-review-2026-11.md` (concept, W1~W7)
- `workflow-source/core/plan_workbench_spec.md` — kit 계약
- `workflow-source/core/claim_plan_spec.md` §6 · §7 · §8 — 응답 형식 · 받은편지함 · 상태 계산 (ADR-031)
- `workflow-source/workflow_kit/common/plan_responses.py` · `plan_claims.py` · `plan_tasks.py` — 소비하는 함수
- `workflow-source/workflow_kit/common/registry_server.py` — 표준 라이브러리 서버 · 토큰 관례의 선례
- `workflow-source/workflow_kit/server/read_only_registry.py` — MCP 번들 (`BUNDLE_READ_ONLY` · `BUNDLE_WRITE`)
