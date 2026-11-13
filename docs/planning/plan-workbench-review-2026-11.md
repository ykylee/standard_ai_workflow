# 계획·진척 워크벤치 — concept 검토

- 문서 목적: 작업을 시작할 때 쓴 계획을 웹으로 호스팅하고(접속 위치 무가정 — §11), 사용자의 동작(결정 · 주석)이 작업 세션에 반영되며, 같은 웹에서 진척을 보는 기능의 표면을 조사하고 소유자 선택지를 판단 가능한 형태로 정리한다 (TASK-2026-11-12-claude-remote-sync-check-234c32-003, M-024/WBS-24.1).
- 범위: 호스팅 위치, 계획 페이지 렌더링, 응답 수집, 작업 세션으로의 전달(MCP · hook · A2A), 진척 화면의 원천, 보안, 기존 자산 재사용, M-022 결정과의 정합 — **하네스 중립 제약 아래에서** (§1-1)
- 대상 독자: 소유자 (M-024 다음 단계 결정), maintainer
- 상태: **종결 (2026-11-12)** — 소유자 결정 = §8 기본값 W1~W5 전부 (§10). **§11 정정: 접속 위치를 가정하지 않는다 — W6 · W7 기본값 확정 (§11.7).** requirements 는 M-025 (M-023 뒤)
- 최종 수정일: 2026-11-13
- 관련 문서: [`M-024`](../../ai-workflow/memory/active/roadmap/M-024-plan-workbench.md), [`html-plan-absorption-review-2026-11.md`](./html-plan-absorption-review-2026-11.md) (선행 concept — 결정 D1~D5, §11 정정), [`registry_server.py`](../../workflow-source/workflow_kit/common/registry_server.py) (HTTP 서빙 선례), [`dashboard_render_html.py`](../../workflow-source/workflow_kit/common/dashboard_render_html.py) (기존 HTML 대시보드), [`compact-relay-review-2026-09.md`](./compact-relay-review-2026-09.md) (이식 층 + 가속 층 분리 선례)

## 0. 한 줄 결론

> 할 만하고, **하네스 중립으로만** 만들 수 있다. 워크벤치 서버(Python 표준 라이브러리, 작업 공간과 같은 호스트 —
> 브라우저는 어디서 접속해도 된다, §11)가
> task 파일의 계획(주장 트리 · 결정)과 진척을 **JS 없는 HTML** 로 서빙하고, 사용자가 폼으로 답한 결정을
> **브랜치 메모리의 받은편지함에 파일로** 떨군다. 반영은 지금처럼 작업 세션이 `plan-import` 로 한다.
> 세션에 알리는 길은 ①**당겨 오기**(session-start 보고 · MCP 도구 — 모든 하네스)가 정본이고, ②hook 머리말은
> **둘 이상 하네스에 같은 의미의 hook 이 있을 때만** 가속 층으로 둔다. html-plan 플러그인 · Claude Code channels ·
> claude.ai Artifact 는 Claude 전용이라 **쓰지 않는다.** A2A 는 하네스 중립이지만 지금은 상대가 없어 보류한다.

## 1. 전제 — 무엇을 하지 않는가

1. **Claude 전용 표면에 기대지 않는다** (소유자 지시, 2026-11-12). kit 은 Claude Code · Codex · Grok Build ·
   Antigravity 등에 배포된다. 정본 경로는 파일 · CLI · MCP 로만 둔다. 이 제약으로 M-022 안 B(html-plan 플러그인
   연동)도 정정된다 — [`html-plan-absorption-review-2026-11.md`](./html-plan-absorption-review-2026-11.md) §11.
2. **웹 서버는 task 파일을 고치지 않는다.** 쓰는 곳은 받은편지함 하나다. task 파일의 쓰기 주체는 지금처럼
   `backlog-update` · `plan-import` 다 — 쓰는 주체가 둘이 되면 생성기 입력(task SSOT)이 갈라진다.
3. **응답은 데이터다** (M-022 결정). 웹으로 들어온 주석이 무엇을 요구하든 서버도 세션도 실행하지 않는다.
   반영 범위는 결정 상태뿐이다 (D4).
4. **진척을 만들어 내지 않는다.** 화면의 숫자는 생성물(`roadmap_state.json` · `state.json`)과 verifier 판정에서만
   온다. 재지 않은 것은 "미측정" 으로 보인다.
5. ~~**외부에 열지 않는다.** 기본은 loopback 이다.~~ → **§11 로 정정**: 접속 위치를 가정하지 않는다. 대신 **어디서 오든 인증한다.**

## 2. 조사

### 2.1 이미 있는 것

| 자산 | 위치 | 재사용 |
|---|---|---|
| HTTP 서빙 | `common/registry_server.py` — `ThreadingHTTPServer`, 고정 경로 2개 외 404, loopback 기본(외부 bind 는 경고), 토큰은 **환경변수 이름**으로 받음, `hmac` 비교 | 워크벤치 서버의 골격 · 보안 관례 그대로 |
| MCP 서버 | `server/` — stdio read-only 번들(`latest_backlog` · `check_doc_*` · `create_backlog_entry` …) + write 번들 | 받은편지함 조회 · 반영 도구를 더할 자리. MCP 는 kit 이 배포하는 하네스 전부가 받는 표면이다 |
| HTML 대시보드 | `wk dashboard --format=html [--publish]` → `docs/dashboard/index.html` | Chart.js 를 **CDN** 으로 부른다 — 워크벤치는 오프라인 응답이어야 해 그대로 못 쓴다 |
| 진척 생성물 | `roadmap/roadmap_state.json` (마일스톤 · WBS · 파생 진척 · issues), `active/<branch>/state.json` | 진척 화면의 유일한 원천 |
| 워크스페이스 registry | federation registry — 같은 호스트의 워크스페이스 · 브랜치 목록 | worktree 여러 개의 진척을 한 화면에 모을 때 |
| hook 렌더러 | `plugin_payload.render_claude_code_hooks` — compact-relay 가 넣은 PreCompact · SessionStart. 같은 `hooks/hooks.json` 사본을 Grok Build 도 읽는다 | 세션 알림 층 ② 의 자리 — 단 §5 조건 |

### 2.2 배제한 Claude 전용 표면

조사는 했고, 제약(§1-1) 때문에 kit 기능으로 넣지 않는다.

| 표면 | 무엇을 줬을까 | 배제 이유 |
|---|---|---|
| html-plan 플러그인 (`anthropics/claude-plugins-community`, 1.0.0) | 목업 · 호출 스택이 들어간 풍부한 계획 페이지, Respond 응답 | Claude Code 플러그인(`.claude-plugin` 만 있음). 게다가 1.0.0 은 응답 전송 경로가 꺼져 있다 (`htmlplan.js` 627행 `const liveOn = false, send = null;`) |
| Claude Code channels ([문서](https://code.claude.com/docs/en/channels)) | 실행 중인 세션에 이벤트를 즉시 밀어 넣기 | Claude Code 전용 기능(research preview) · 세션이 열려 있을 때만 도착 · 허용 목록 밖 발신자는 조용히 버려짐 · 명시적 opt-in 필요 |
| claude.ai Artifact | 원격에서 계획 열람 | claude.ai 전용, 그리고 공개 페이지에서 사용자 PC 의 localhost 로 응답을 보낼 수 없다 |

html-plan 에서 가져오는 것은 **개념**(주장 트리 · 결정 배치 · 열리지 않은 기본값 ≠ 동의 · 응답 = 데이터)뿐이고,
그것은 M-022 안 A 로 task 파일 계약에 들어간다.

### 2.3 A2A (Agent2Agent)

출처: [a2aproject/A2A](https://github.com/a2aproject/A2A), [A2A protocol explained](https://www.glukhov.org/ai-systems/architecture/a2a-protocol-explained/).

- 에이전트가 다른 에이전트에게 일(Task)을 맡기는 **개방 프로토콜**이다 — 하네스 중립 제약에는 걸리지 않는다.
- `input-required`(최신 판 `TASK_STATE_INPUT_REQUIRED`) 상태에서 Task 가 멈추고, 같은 taskId 로 메시지를 보내면
  이어진다 — 우리의 "열리지 않은 결정이 있는 task" 와 모양이 같다.
- 그러나 **양쪽이 에이전트**다. 브라우저 앞의 사용자와 로컬 코딩 세션 사이에는 A2A 서버도 클라이언트도 없다.
  넣으면 서버 · SDK 의존 · 인증이 늘고, 사용자 경험은 그대로다.

## 3. 구조 초안

```
task 파일 (M-022 안 A: Claims · Decisions · Out of scope)
   │
wk workbench  (Python stdlib, 작업 공간 호스트에서 실행, bind · 공개 URL 은 설정 — §11, 항상 인증)
   ├─ GET  /                  진척: 마일스톤 · WBS · 진행/차단/최근 완료 · 열린 결정 수
   ├─ GET  /task/<TASK>       계획: 주장 트리(<details> 접기) · 결정 폼 · 바꾸지 않는 것 · 완료 기준별 판정
   ├─ POST /task/<TASK>/respond   결정 폼 + 주석 → 응답 markdown → 받은편지함
   ├─ GET  /api/state         위 화면의 JSON
   └─ GET  /healthz
   ▼
active/<branch>/plan_responses/inbox/<TASK>-<n>.md   (gitignore — 커밋은 반영 뒤 보관본만, M-023 Q1)
   │  세션 알림 (§5): ① 당겨 오기 · ② hook 머리말(조건부)
   ▼
wk plan-import --task=<TASK>  (대조 · 닫힘 · 결정 상태만)
   ▼
inbox → plan_responses/<TASK>-<n>.md 로 이동, task Decisions 갱신, Progress 한 줄
```

어느 하네스에서 작업하든 같은 흐름이다 — 서버와 import 는 kit CLI 이고, 알림 ① 은 모든 하네스가 읽는 보고와 MCP 다.

## 4. 결정 지점별 검토

### 4.1 호스팅 위치

| 안 | 볼 수 있는 곳 | 응답 반영 | 판정 |
|---|---|---|---|
| **워크벤치 서버** (작업 공간 호스트) | 사용자가 고른 노출 경로로 닿는 어느 브라우저든 (§11.2) | 가능 (서버가 받은편지함에 쓴다) | **권장** — 응답이 세션까지 닿는 유일한 안이고 하네스와 무관하다 |
| 정적 공개 호스팅 (GitHub Pages 등) | 누구나 | 불가 | 계획에 경로 · 결정 · 내부 사정이 들어간다 — 기본 금지 |
| claude.ai Artifact | 어디서나 | 불가 | Claude 전용 — 배제 (§2.2) |

### 4.2 계획 페이지 렌더링

html-plan 런타임을 쓰지 않으므로(§2.2) 워크벤치가 task 파일에서 직접 그린다. 범위를 **task 파일에 이미 있는 것**으로
묶어 "자체 계획 렌더러" 가 커지지 않게 한다:

- 주장 트리 — `<details>`/`<summary>` 로 접는다. 접힌 상태가 곧 1단계 주장 목록(요약)이다. 주장 번호는 task 파일의 `C` ID 그대로.
- 결정 — 가리키는 주장 안에 `<form>` 의 radio, 기본값 `checked`, "추천" 표시. 남은 결정 수를 머리에 센다.
- 3단계 `@ path:line` — 경로와 줄만 보인다(코드 발췌는 싣지 않는다 — 발췌는 비밀 노출 표면이고, 편집기가 더 잘 보여 준다).
- 완료 기준 · verifier 판정 — `[C<n>]` 인용으로 주장 아래에 묶는다 (M-022 D3).
- **JS 없음** 이 기본안이다: 접기는 `<details>`, 제출은 일반 폼 POST. JS 를 쓰면 열림 기록("열어 보고 유지" 와
  "열지 않음" 의 구분 — §4.3)을 정확히 잴 수 있다.

목업 · 상태 기계 · 호출 스택 같은 근거 자료는 그리지 않는다 — 그것은 판단이 필요한 저작물이고, kit 이 그리면 계획이 아니라 설계 문서가 된다.

### 4.3 "열지 않은 기본값" 을 어떻게 재는가

M-022 D2(열리지 않은 결정은 done 거부)는 응답이 `kept`(열어 보고 유지)와 `unopened`(열지 않음)를 구분해야 선다.

- JS 없는 폼: 사용자가 radio 를 바꾸지 않고 제출하면, 그 결정을 "보았다" 고 볼 근거는 **제출 행위**뿐이다.
  결정마다 "이대로 동의" 체크박스를 두고, 체크된 것만 `kept`, 아닌 것은 `unopened` 로 적는다.
- 최소 JS: `<details>` 의 `toggle` 이벤트로 결정이 화면에 열렸는지 기록해 숨은 필드로 보낸다 — html-plan 의 방식과 같다.

### 4.4 진척 화면

- 원천: `roadmap_state.json`(마일스톤 · WBS · 파생 진척 · issues · `deliverables_missing`), 브랜치 `state.json`
  (진행 · 차단 · 최근 완료), task 파일(완료 기준 · 주장 · 결정 상태), verifier 판정(task `Verification` 줄).
- 표시 규칙: 선언 상태와 파생 상태가 다르면 **둘 다** 보인다(roadmap issues). 미측정은 "미측정" — 0% 로 그리지 않는다.
- 렌더러: 기존 대시보드의 CDN 차트 대신 인라인 SVG 막대 — 오프라인 응답.
- worktree 여러 개: 서버는 자기 checkout 의 파일만 본다. 같은 호스트의 다른 worktree 진척은 워크스페이스 registry 로 모은다 (선택, 나중).

## 5. 작업 세션에 알리는 길

| 층 | 방식 | 하네스 | 즉시성 | 실패 시 |
|---|---|---|---|---|
| ① 당겨 오기 | `session-start` · `backlog-update` 보고에 "받은편지함 n건" + CLI `plan-import`; read-only MCP 도구 `plan_inbox`(목록), write 번들 `plan_import` | **모든 하네스** — 정본은 CLI 와 보고다. MCP write 번들은 하네스마다 연결이 다르다 (Codex 는 read-only 번들만 — `plugin_payload.py` 657행) | 다음 명령 · 다음 세션 | 없음 — 이 층이 정본 |
| ② hook 머리말 | 사용자 프롬프트 직전 hook 이 받은편지함을 보고 "새 계획 응답 n건 — plan-import 하라" 한 줄 주입 | **둘 이상 하네스에 같은 의미의 hook 이 있을 때만** — 없으면 만들지 않는다 | 사용자가 다음에 말할 때 | hook 없는 하네스 → ① 로 떨어짐 |

compact-relay 와 같은 원칙: **이식 층(①)이 정본이고, ② 는 가속 층**이다. 가속 층이 없거나 실패해도 받은편지함
파일이 남으므로 응답은 잃지 않는다. 주입 문구에는 응답 내용을 싣지 않고 "task · 건수 · 경로" 만 싣는다.

② 의 조건 확인은 design 전 실측 대상이다 (§9) — 프롬프트 직전 hook 이 Claude Code 에만 있으면 ② 는 만들지 않는다.

**A2A 판정**: 지금은 넣지 않는다 (§2.3). 다시 볼 조건: 다른 에이전트(다른 호스트 · 다른 벤더)가 이 워크플로우에
task 를 맡기고 결과를 받아야 할 때 — 그때 task 를 A2A Task 로, 열린 결정을 `input-required` 로 사상한다.

## 6. 보안

- **§11.3 으로 대체** — 아래 두 줄은 loopback 전제의 초안이었다: ~~bind 는 `127.0.0.1` 고정이 기본~~,
  ~~`Host` 헤더가 loopback 이름이 아니면 거부~~. 남는 원칙: POST 는 `Origin` 이 허용 출처이고 CSRF 토큰(`hmac` 비교)이 맞을 때만.
- POST 본문 상한 256KB, 제어 문자 거부, 받은편지함 밖 경로 쓰기 없음, 파일명은 서버가 정한다.
- 페이지에 코드 발췌를 싣지 않는다 (§4.2) — 비밀 거부 로직을 따로 둘 필요가 없어진다.
- 응답 = 데이터: 주석이 새 일이나 위험한 일을 요구하면 세션은 실행하지 않고 사용자에게 묻는다 (M-022 §5.6).

## 7. 수명 · 진입

- `wk workbench [--port] [--open]` — 오래 사는 프로세스다. `session-start` 가 띄우지 않는다(세션마다 프로세스가
  쌓인다). 실행 중이면 `.workbench/server.json`(pid · port, gitignore)을 보고 URL 을 알려 준다.
- 진입은 §11.1 명령(`workbench`, `plan-import`)과 1:1 스킬로 — 모든 하네스의 플러그인 · bootstrap 채널에 같은 파생본이 간다.

## 8. 소유자 선택지

| # | 결정 | 기본 (권장) | 대안 |
|---|---|---|---|
| W1 | 세션 알림 층 | **① 정본 + ② 조건부** (둘 이상 하네스에 같은 의미의 hook 이 실측될 때만) | ①만 |
| W2 | 계획 페이지 스크립트 | **최소 JS** — `toggle` 로 열림을 재서 `kept`/`unopened` 를 정확히 (§4.3) | JS 없음 — "이대로 동의" 체크박스 |
| W3 | A2A | **보류** — 다시 볼 조건만 기록 (§5) | 지금 Agent Card · Task 사상까지 |
| W4 | 진행 순서 | **M-023(A + B requirements) 먼저**, 워크벤치 requirements 는 그 뒤 — 받은편지함 · import 가 B 위에 선다 | M-023 에 합쳐 한 requirements 로 |
| W5 | M-022 안 B 정정 | **B = 워크벤치 결정 폼 + 받은편지함 + `plan-import`(우리 응답 형식)**; html-plan 형식 export/import 는 삭제 (§1-1, M-022 §11) | B 를 통째로 빼고 A 만 |

**권장 근거**: 사용자가 원하는 "웹에서 보고 답하면 작업에 반영" 은 ①만으로 **다음 대화 한 번** 안에 닿고, 어느
하네스에서나 같다. ② 는 즉시성을 조금 더할 뿐이라 한 하네스 전용이면 넣을 이유가 없다. W2 는 D2 게이트(열리지 않은
결정은 done 거부)가 기대는 구분을 사람의 체크 습관이 아니라 측정으로 얻는 쪽을 권한다.

## 9. 미실측 · 리스크

- 프롬프트 직전 hook 의 하네스별 존재 · 의미(Codex · Grok Build · Antigravity) — W1 ② 의 조건. design 전에 잰다.
- 받은편지함을 커밋 대상으로 두면(D5) 웹에서 응답이 올 때마다 작업 트리가 더러워진다 — 반영(`plan-import --apply`)
  때 함께 커밋되는 흐름을 requirements 에서 정한다.
- 같은 브랜치에 세션이 둘이면 둘 다 같은 받은편지함을 본다 — 먼저 import 한 쪽이 이긴다. 이동(inbox → 보관)이
  원자적이어야 한다.
- 계획 페이지가 "작은 자체 렌더러" 로 머물지 — 근거 자료(목업 등)를 그려 달라는 요구가 오면 범위가 커진다.
  §4.2 의 "task 파일에 이미 있는 것만" 을 requirements 의 경계로 고정한다.
- Windows: 포트 · 브라우저 열기 · 경로 — 한글 Windows 프로필(v1.22.0)에서 실측 필요.

## 10. 소유자 결정 (2026-11-12, 123차)

권장안(§8 기본값)대로:

1. **W1** 세션 알림 — **① 당겨 오기가 정본**(session-start · backlog-update 보고 + MCP `plan_inbox` · `plan_import`),
   ② hook 머리말은 **둘 이상 하네스에 같은 의미의 프롬프트 직전 hook 이 실측될 때만** 만든다.
2. **W2** 계획 페이지는 **최소 JS** — `<details>` 의 `toggle` 로 결정의 열림을 재서 `kept` / `unopened` 를 측정으로 구분한다.
   JS 가 꺼진 브라우저에서도 폼 제출은 되고, 그때 열림 기록이 없는 결정은 `unopened` 다.
   (M-023 Q6 으로 좁힘: 이 규칙은 **기본값을 그대로 둔** 결정에만 적용한다 — 다른 값을 고른 결정은 열림 기록이 없어도 `changed` 다, [`claim-plan-requirements-2026-11.md`](./claim-plan-requirements-2026-11.md) R6.3.)
3. **W3** A2A **보류** — 다시 볼 조건(다른 에이전트가 이 워크플로우에 task 를 맡길 때)만 기록.
4. **W4** 순서 — **M-023(A + B requirements) 먼저**, 워크벤치 requirements 는
   [`M-025`](../../ai-workflow/memory/active/roadmap/M-025-plan-workbench-requirements.md) 로 그 뒤.
5. **W5** M-022 안 B 정정 **확정** — html-plan 형식 export/import 삭제, 워크벤치 결정 폼 + 받은편지함 +
   `plan-import`(우리 응답 형식)로 대체 ([`html-plan-absorption-review-2026-11.md`](./html-plan-absorption-review-2026-11.md) §11).

모든 결정의 바탕: **kit 에 Claude 전용 기능을 두지 않는다** (§1-1).

## 11. 정정 — 접속 위치를 가정하지 않는다 (2026-11-12, 123차)

소유자 지시: **웹에 꼭 localhost 로 접속하는 것은 아니라고 보고 구성한다.**

§1-5 · §4.1 · §6 은 "작업 공간과 브라우저가 같은 호스트" 를 전제했다. 실제로는 그렇지 않은 경우가 흔하다 —
에이전트가 원격 개발 서버 · VM · 컨테이너 · 클라우드 작업 공간에서 돌고 브라우저는 노트북에 있거나, 사용자가 휴대폰 ·
다른 기기에서 진척을 보거나, 팀원이 진척을 보고 소유자만 결정에 답하는 경우다.

### 11.1 바뀌지 않는 것

- **서버는 작업 공간과 같은 호스트에서 돈다.** 받은편지함 · task 파일 · 생성물은 그 호스트의 checkout 에 있다 —
  서버가 그 파일을 읽고 받은편지함에 쓴다. 원격인 것은 **브라우저**뿐이다.
- 웹 서버는 받은편지함만 쓴다 · 응답 = 데이터 · 진척은 생성물과 verifier 판정에서만 · Claude 전용 표면 금지.

### 11.2 노출 경로 — kit 은 고르지 않고, 어느 경로든 동작하게 만든다

| 경로 | 예 | 서버가 지켜야 할 것 |
|---|---|---|
| 같은 호스트 | 노트북에서 작업 + 브라우저 | 기본 bind `127.0.0.1` 은 유지 — 노출하지 않는 것이 기본값이다 (가정이 아니라 **안전한 기본값**) |
| 포트 포워딩 · 터널 | `ssh -L`, IDE 원격 포트 포워딩, 클라우드 작업 공간의 포트 공유, 메시 VPN | 서버 입장에서는 loopback 요청이다. **원래 출처(공개 URL)** 를 설정으로 받아야 CSRF · 링크가 맞는다 |
| 리버스 프록시 | nginx · Caddy · 사내 게이트웨이, 경로 접두사(`/workbench/`) 포함 | **경로 접두사**, `X-Forwarded-*` 는 **설정한 프록시 주소에서 온 것만** 믿는다. TLS 는 프록시가 끝낸다 |
| 직접 노출 | `--bind 0.0.0.0` (사내망 · LAN) | 명시 옵션 + 경고. 인증 필수, **TLS 필수**(내장 `ssl` — 인증서 경로 설정) 또는 같은 망 한정임을 사용자가 선언 |

구현 원칙: 페이지 안의 모든 링크와 폼 action 은 **상대 경로**, 절대 URL 이 필요한 곳(CSRF 출처 대조 · 시작 시 출력 URL)은
`public_url` 설정 하나에서만 만든다. 서버 코드가 자기 주소를 추측하지 않는다.

### 11.3 인증 · 권한 — 접속 위치와 무관하게 항상

- **loopback 이라고 인증을 면제하지 않는다.** 포워딩 · 터널 · 프록시를 거친 요청은 서버에게 loopback 으로 보이므로,
  "loopback 이면 신뢰" 는 노출 경로가 하나 생기는 순간 구멍이 된다.
- **역할 두 개**: `viewer`(진척 · 계획 열람) 와 `approver`(결정 응답 제출). 토큰은 역할별로 따로 발급하고, 값이 아니라
  **환경변수 이름 또는 0600 파일 경로**로 받는다 (`registry_server` 관례 — `ps` · 셸 기록에 값이 남지 않게).
- 토큰에 **이름**을 붙인다 (`owner`, `alice` …). 응답 파일에 응답자 이름과 시각이 실린다 — 여러 사람이 볼 때 누가 답했는지가
  남아야 "열지 않은 기본값 ≠ 동의" 가 사람 단위로 성립한다.
- 브라우저 세션은 토큰을 한 번 받은 뒤 `HttpOnly` · `SameSite=Strict` 쿠키(TLS 이면 `Secure`)로 이어 간다. 토큰을 URL 에
  남기지 않는다(첫 진입 뒤 리다이렉트로 지운다). (M-025 requirements Q1 로 갱신: 토큰은 URL 로 받지 않고 로그인 폼의 본문으로만 받는다 — [`plan-workbench-requirements-2026-11.md`](./plan-workbench-requirements-2026-11.md) R3.2.)
- 위임 인증(선택): 사내 프록시가 이미 사용자를 인증한다면, **설정한 프록시 주소에서 온** 지정 헤더의 사용자 이름을 믿고
  역할 표에 매핑한다. 기본은 꺼짐.
- 남용 방지: 실패한 인증 시도 속도 제한, POST 본문 상한 256KB, 받은편지함 밖 쓰기 없음.

### 11.4 받은편지함 · 진척 화면에 생기는 변화

- 응답 파일 머리에 `responder` · `role` · `received_at` 이 실린다. `plan-import` 는 `approver` 응답만 결정 상태에 반영하고,
  `viewer` 는 응답 폼 자체를 보지 못한다.
- 같은 결정에 서로 다른 approver 의 답이 오면 import 는 **그 응답 묶음 전체를 쓰지 않고** 충돌로 보고한다 — 부분 반영은 하지 않는다 (M-022 §5.5 의 닫힘과 같다). 소유자가 대화로 정하거나 한쪽 응답을 받은편지함에서 거두면 다시 import 한다. (M-023 requirements R6.3 으로 구체화: 자격 있는 응답은 다툼에 들어도 **원문은 보관**하고 값만 결정 상태에 채택하지 않는다 — 그 결정은 `disputed` 로 다시 열린다, Q7.)
- 진척 화면은 viewer 에게도 열리므로 화면에 싣는 것을 다시 본다: 경로 · 브랜치 이름은 싣되, 작업 공간 절대 경로 ·
  호스트 이름은 싣지 않는다.

### 11.5 소유자 선택지 (추가)

| # | 결정 | 기본 (권장) | 대안 |
|---|---|---|---|
| W6 | 접근 모델 | **안전한 기본값(loopback bind) + 어느 노출 경로든 동작** — `public_url` · 경로 접두사 · 신뢰 프록시 설정, 직접 노출은 명시 옵션 + TLS | 직접 노출을 기본으로 (`0.0.0.0` + 내장 TLS) |
| W7 | 인증 · 권한 | **항상 인증 + viewer/approver 두 역할 + 이름 붙은 토큰**, 위임 인증은 선택(기본 꺼짐) | 단일 토큰 하나(역할 없음) |

**권장 근거**: kit 이 노출 경로를 하나로 고르면 원격 개발 서버 · 클라우드 작업 공간 · 사내 프록시 중 어딘가가 막힌다.
경로는 사용자 몫으로 두고, 서버는 "어느 경로로 오든 같은 인증 · 같은 출처 대조" 를 지키는 쪽이 이식성이 가장 높다.
역할을 나누는 것은 "진척은 팀이 보고, 결정은 소유자가 한다" 는 요구를 토큰 하나로는 표현할 수 없기 때문이다.

### 11.6 미실측 · 리스크 (추가)

- 경로 접두사가 있는 리버스 프록시 뒤에서 쿠키 경로 · 리다이렉트가 맞는지 — requirements 에서 nginx · Caddy 중 하나로 실측.
- 클라우드 작업 공간의 포트 공유가 자체 인증 페이지를 앞에 두는 경우, 우리 쿠키와의 충돌.
- 내장 TLS 의 인증서 갱신 책임 — 직접 노출을 쓰는 사용자에게 넘긴다(문서화), kit 이 인증서를 만들지 않는다.
- 진척 화면의 정보 노출 범위(§11.4) — viewer 가 팀 밖으로 링크를 넘기는 경우는 토큰 회수(재발급)로만 막는다.

### 11.7 소유자 결정 (2026-11-12, 123차)

권장안(§11.5 기본값)대로:

1. **W6** 접근 모델 — **안전한 기본값(loopback bind) + 어느 노출 경로든 동작.** 서버는 `public_url` · 경로 접두사 ·
   신뢰 프록시 주소를 설정으로 받고 자기 주소를 추측하지 않는다. 직접 노출은 명시 옵션 + 경고 + TLS(또는 같은 망 한정 선언).
2. **W7** 인증 · 권한 — **항상 인증**(loopback 도 면제 없음), **viewer / approver 두 역할**, **이름 붙은 토큰**(환경변수 이름 ·
   0600 파일 경로로 받음), 응답에 응답자 · 역할 · 시각 기록, approver 끼리 충돌하면 반영하지 않고 보고. 위임 인증(신뢰 프록시의
   사용자 헤더)은 선택 · 기본 꺼짐.

requirements([`M-025`](../../ai-workflow/memory/active/roadmap/M-025-plan-workbench-requirements.md))는 §11.6 미실측을 함께 잰다.

