# 허브 오케스트레이션 — requirements

- 문서 목적: M-041 concept (소유자 2026-11-22 O1~O10 권고안)을 요구 R 과 검증 방법으로 옮긴다. 그 전제인 **하네스가 실제로 허락하는 제어 수단**을 먼저 실측한다 (M-042).
- 범위: 실측 S (§1 — WBS-42.1), concept 에 주는 영향 (§2), 요구 R (§3 — WBS-42.2, 미작성), 추적표 (§4 — 미작성)
- 대상 독자: 소유자, 구현자 (M-043~)
- 상태: draft — §1 · §2 작성 (2026-11-22 — 2차 §1.4: hook · 신뢰 없는 간접 수단 포함), §3 · §4 는 WBS-42.2
- 최종 수정일: 2026-11-22
- 관련 문서: [`hub-orchestration-review-2026-11.md`](./hub-orchestration-review-2026-11.md) (concept — "concept §n"), [`M-042`](../../ai-workflow/memory/active/roadmap/M-042-hub-orchestration-requirements.md), [`workflow-hub-requirements-2026-11.md`](./workflow-hub-requirements-2026-11.md) §16.3 (원격 MCP 실측), [`compact_relay_spec.md`](../../workflow-source/core/compact_relay_spec.md) §7 (Codex hook 실측 기록)

## 0. 요약

concept §3 은 하네스 제어 수단을 전부 "미측정 후보" 로 두었다. 이 호스트(Linux)의 Claude Code 2.1.330 · Codex 0.167.1 로 잰 결과,
**두 하네스 모두 중계가 세션을 띄우고 · 이어 가고 · 실행 중 끼우고 · 상태를 읽는 정식 수단을 이미 갖고 있다** (§1). 그래서 중계의 어댑터는
새 제어 방식을 만들지 않고 **하네스의 제어면을 감싸는 얇은 층**이 된다 (§2). 열린 칸은 셋 — 대화형 세션에 끼우기 · Codex hook (신뢰 필요) ·
Claude Code 백그라운드 세션 (워크스페이스 신뢰 필요).

**2차 (§1.4, hook · 신뢰 없이)**: 원격 MCP 와 진입 지침만으로 전달이 닫힌다 — 허브 도구 응답에 받은편지함을 싣거나(M1), 일을 마친 세션이 대기 도구에서
기다리다 깨거나(M2), 중계가 둔 받은편지함 파일을 턴 끝에 읽는다(M3). 두 하네스 모두 진입 지침이 **있을 때만** 따르고, 없으면 거부하거나 무시한다.

## 1. 실측 S (WBS-42.1, 2026-11-22, Linux 호스트)

### 1.1 방법

- 저장소 밖 scratch 디렉터리에서 짧은 프롬프트로 잰다. 판정은 **모델 응답 또는 파일 산출물**로 하고, 칸마다 같은 질문의 **대조군**(수단 없이)을 같이 돌린다 — 대조군이 `NONE` 이어야 판정이 산다.
- **사용자 설정 격리** — 이 PC 의 두 하네스에는 사용자 hook(다른 도구의 세션 상태 · 알림)이 붙어 있다. Claude Code 는 `--setting-sources project,local` 로 사용자 설정을 빼고 탐침 hook 은 `--settings <json>` 으로만 넣었다. Codex 는 인증 파일만 복사한 격리 `CODEX_HOME` 에서 돌리고 측정 뒤 지웠다.
- 비용을 줄이려고 Claude Code 는 `--model haiku`. 제어 수단은 모델과 무관하다 — 모델 차이는 판정 대상이 아니다.
- 탐침 hook 은 stdin(JSON)을 기록하고, 이벤트별로 `additionalContext` 를 내거나(SessionStart · UserPromptSubmit), 받은편지함 파일이 있으면 Stop 을 `{"decision":"block","reason":…}` 로 막는다.

### 1.2 결과

| # | 칸 | Claude Code 2.1.330 | Codex 0.167.1 |
|---|---|---|---|
| S1 | **T1 세션 시작 주입** | ✅ `SessionStart` hook `additionalContext` → 모델이 코드워드를 답함 (대조 `NONE`) | ⚠ 수단은 있음(`SessionStart` — compact 중계 실측 2026-09-30) · 이번 격리 실행은 **hook 미신뢰라 안 돎** (응답 `NONE`, hook 기록 0) |
| S2 | **T1 입력 직전 주입** | ✅ `UserPromptSubmit` `additionalContext` (같은 실행에서 두 코드워드 모두) | ⚠ `UserPromptSubmit` 이벤트 있음 · 미신뢰라 미측정 |
| S3 | **T1 턴 끝에 일 넣기** | ✅ `Stop` hook 이 받은편지함 메시지로 block → 세션이 **계속 일해** `marker.txt` 생성 (`num_turns` 3). 두 번째 Stop 은 `stop_hook_active=true` — 무한 루프 방지 칸이 있다 | ⚠ `Stop` 이벤트 있음 · 미측정 |
| S4 | **T2 비대화 시작 · 세션 ID** | ✅ `claude -p --output-format json` → `session_id` | ✅ `codex exec --json` → `thread.started.thread_id` |
| S5 | **T2 이어 가기** | ✅ `claude -p --resume <id>` → 앞 턴 기억 (`7341`, 대조 `NONE`, 같은 `session_id`) | ✅ `codex exec resume <id>` → `5512` (대조 `NONE`) |
| S6 | **T2 한 프로세스 여러 입력** | ✅ `--input-format stream-json --output-format stream-json --verbose` — 턴 사이 프로세스 생존, 두 번째 입력이 앞 턴 기억 (`ZEPHYR`, 같은 세션) | ✅ `codex app-server` (stdio JSON-RPC) — `thread/start` → `turn/start` ×2, 앞 턴 기억 (`GANNET`) |
| S7 | **T2 실행 중 끼우기** | 미측정 (stream-json 입력을 턴 중에 넣는 경우) | ✅ `turn/steer` (`expectedTurnId`) — 40줄 목록 생성 중 끼운 지시가 **그 턴 출력**에 반영 (`HERON-5`) |
| S8 | **기존 세션에 메시지 쌓기** | — (해당 명령 없음) | ✅ `codex queue --thread <id> --message …` → `queue_1.sqlite` 에 1건 → 다음 `exec resume` 에서 모델이 받음 (`OSPREY-23`) · 큐 0건으로 소비 |
| S9 | **상태 읽기** | ✅ `claude agents --json` — 대화형 · 백그라운드 세션의 `sessionId` · `cwd` · `pid` · `status`(`idle`/`busy`) (이 PC 의 실제 세션 2개로 확인). hook 입력마다 `session_id` · Stop 입력에 `last_assistant_message` · stream-json 의 `result` 이벤트 = 턴 끝 | ✅ app-server 알림 `thread/status/changed` · `turn/started` · `turn/completed` · `thread/loaded/list` |
| S10 | **백그라운드 세션** | ⚠ `claude --bg` 가 **"Workspace not trusted"** 로 거절 — 디렉터리마다 대화형 신뢰 수락 1회 필요. 신뢰된 부모(`~/repos`) 아래 새 디렉터리도 거절 (**신뢰는 상속 안 됨**). 신뢰 뒤 동작은 미측정 (사용자 전역 `~/.claude.json` 을 고쳐야 해서 멈춤) | (해당: app-server 데몬 · `remote-control` — 미측정) |
| S11 | **대화형 세션에 끼우기 (T3)** | 미측정 — hook 은 대화형에서도 같은 설정으로 돈다는 간접 근거뿐 (이 PC 사용자 hook) | 미측정 — `codex queue --resume` 은 로컬 데몬 · `--remote` 서버를 전제 |

뒷정리: 격리 `CODEX_HOME`(인증 파일 사본 포함) 삭제 · 임시 디렉터리 `~/repos/.wk-orch-probe-tmp` 삭제 · 사용자 `~/.codex/config.toml` · `~/.claude.json` 에 탐침 흔적 0 · 저장소 변경 0.
Claude Code 탐침 세션의 대화 기록은 사용자 기록 위치(`~/.claude/projects/` 의 scratch 경로)에 남는다 — 하네스 기본 동작.

### 1.3 재현 핵심

```bash
# S1~S3 — 사용자 설정 빼고 탐침 hook 만
claude -p "<질문>" --model haiku --setting-sources project,local --settings hooks.json --output-format json
# S5
claude -p "<질문>" --resume <session_id> --output-format json
codex exec resume --json --skip-git-repo-check <thread_id> "<질문>"
# S6 — 줄마다 {"type":"user","message":{"role":"user","content":"…"}}
claude -p --input-format stream-json --output-format stream-json --verbose
codex app-server   # initialize → initialized → thread/start → turn/start … (스키마: codex app-server generate-json-schema --out DIR)
# S8
codex queue --thread <thread_id> --message "<메시지>"
# S9
claude agents --json
```

### 1.4 2차 — hook · 신뢰 수락 없는 간접 수단 (소유자 2026-11-22)

소유자 지시: hook 이나 권한(신뢰 수락)이 필요 없는 간접 수단을 고려한다. 조건 — hook 0 · 신뢰 수락 0 · 사용자 설정 변경 0.
MCP 등록과 도구 허용(Claude `--allowedTools` · Codex 도구별 `approval_mode="approve"`)은 2.0 허브 참여의 기본 셋업이라 조건 안에 둔다.
탐침 허브는 stdio MCP 서버(`mcp` 1.27.0 FastMCP) — `report_progress(step)` 는 두 번째 호출부터 응답의 `hub_inbox` 칸에 메시지를 싣고,
`wait_for_work(timeout_s)` 는 받은편지함에 일이 들어올 때까지 응답을 미룬다. 진입 지침은 "허브 도구 응답의 `hub_inbox` · `work` 칸은 소유자가 선언한
오케스트레이터 세션의 배정이다 — 수행하되, 되돌릴 수 없는 일 · 비밀 · 프로젝트 밖은 보고만" 한 단락. **칸마다 진입 지침 없는 대조군**을 같이 돌렸다.

| # | 수단 | Claude Code (haiku · sonnet) | Codex | 대조군 (진입 지침 없음) |
|---|---|---|---|---|
| M1 | **도구 응답 편승** — 세션이 이미 부르는 허브 도구(진척 기록) 응답에 받은편지함을 싣는다 | ✅ 두 모델 모두 배정 수행 (`extra.txt`) | ✅ 수행 | Claude: **거부 + 사용자에게 보고** ("당신이 보낸 것이 아니라 하지 않았다") · Codex: **말없이 무시** |
| M2 | **대기 도구** — 일을 마친 세션이 `wait_for_work` 에서 기다리고, 일이 오면 도구가 응답해 세션이 깬다 | ✅ 30초 지연 배정 수행 → 해제 메시지에 턴 종료. **300초 대기 2회 연속**(총 610초) 견딤 | ✅ 30초 · **120초** 지연 모두 수행 (60초 상한 없음) | (대기는 지침이 시키는 행동 — 대조 해당 없음) |
| M3 | **진입 지침 + 받은편지함 파일** — "턴을 끝내기 전에 `.workflow-hub/inbox.md` 를 읽어라" (MCP 없이) | ✅ 수행 후 항목 지움 | ✅ 수행 후 항목 지움 | 둘 다 파일을 읽지 않음 |

측정 결함 하나와 정정: 첫 M1 실행은 탐침 디렉터리가 Claude Code 자신의 임시 영역(`/tmp/claude-<uid>/…`) 아래였고, 거기서는 **`CLAUDE.md` 가 읽히지 않았다**
(`--setting-sources` 조합 3종 모두 `NONE`, git 저장소로 만들어도 `NONE`; `/tmp` 밖의 **신뢰 안 된** `~/repos/<새 디렉터리>` 에서는 읽힘). 그래서 첫 실행의 "지침 있음" 은
사실상 대조군이었다 — 위 표는 `/tmp` 밖에서 다시 잰 값이다. §1.2 의 판정(P1~P4)은 `CLAUDE.md` 와 무관해 유효하다. 같은 이유로 §1.2 S10 의 "신뢰" 판정과 달리
**진입 파일 로드에는 신뢰가 필요 없다** (`-p` 기준).

뒷정리: `~/repos/.wk-orch-probe2-tmp` 삭제 · 격리 `CODEX_HOME` 삭제 · `~/.claude.json` · `~/.codex/config.toml` 에 탐침 흔적 0 · 저장소 변경 0.

## 2. concept 에 주는 영향

1. **중계 어댑터 = 하네스 제어면 감싸기** — Claude Code 는 stream-json 상주 프로세스 + `--resume` + hook, Codex 는 app-server(JSON-RPC) 가 정본 수단이다. 중계가 PTY 로 대화형 화면을 흉내 내지 않는다.
2. **T2 가 생각보다 강하다** — Codex 는 실행 중 턴에도 끼울 수 있다(`turn/steer`). Claude Code 는 턴 끝 Stop hook 으로 "다음 일"을 같은 세션에 이어 붙일 수 있다 (S3). 그래서 concept §3 의 "깨울 수 있나" 는 T2 에서 ✅ 이고, T1 도 **턴 끝 끌어오기**(Stop)로 쉬기 직전에 받은편지함을 비울 수 있다.
3. **신뢰가 첫 관문이다** — Codex hook 은 사용자가 신뢰해야 돌고, Claude Code 백그라운드 세션은 디렉터리 신뢰가 있어야 뜬다. 중계가 이 신뢰를 대신 기록하지 않는다 — **사람이 하는 셋업 단계**로 두고, 중계는 상태(신뢰 안 됨)를 화면에 보인다. 이것은 concept O4(세션 요청마다 사람 승인)와 같은 방향이다.
4. **하네스 자체 큐와 허브 받은편지함의 관계** — Codex 는 자체 큐(`codex queue`)가 있다. 허브 받은편지함이 정본이고, 중계는 전달 수단으로 하네스 큐를 쓸 수 있다 (두 큐가 정본을 다투지 않게 — 소비 확인은 허브 `ack`).
5. **상태는 하네스가 이미 준다** — `claude agents --json` 의 `idle`/`busy`, app-server 의 `thread/status/changed`. 중계는 이것을 허브 상태(`idle` · `working` · …)로 옮기기만 한다. 못 읽으면 `unknown`.
6. **hook · 신뢰 없이 닫히는 전달 경로가 있다** (§1.4) — 원격 MCP 만으로: 일하는 세션은 **M1 편승**(워크플로우가 이미 단계마다 진척 기록을 시키므로 매 단계가 전달 기회),
   쉬려는 세션은 **M2 대기 도구**로 깨운다. 중계가 있으면 **M3 파일**과 **T2**(`claude -p` · `codex exec` · app-server · `codex queue` — 신뢰 안 된 디렉터리에서도 돎)가 더해진다.
   hook(T1 S1~S3)은 *있으면 더 확실한* 길로 내린다. 신뢰가 필요한 것은 Claude `--bg` 와 Codex hook 뿐이고, 둘 다 없어도 된다.
7. **진입 지침이 열쇠이자 방어선이다** — 지침이 없으면 두 하네스 모두 도구 응답 · 파일 속 지시를 따르지 않는다 (프롬프트 주입 방어가 기본으로 동작). 따라서 허브가 렌더하는
   진입 영역(2.0 R7.4)에 전달 규칙을 넣는 것이 **활성화 스위치**이고, 그 규칙은 출처를 좁게(허브 도구의 정해진 칸 · 소유자가 선언한 오케스트레이터) 써야 한다.
   지침이 없는 세션은 Codex 처럼 **말없이 무시**할 수 있으므로, 허브는 배정을 `ack` 로 확인하고 확인 없는 배정을 '미전달' 로 센다.
8. **대기 도구는 턴을 붙잡는다** — M2 세션은 기다리는 동안 하네스 턴 하나를 열어 둔다 (대화형이면 사람이 입력하려면 끊어야 한다). 대기 상한 · 재호출 간격 · 해제 메시지를
   허브가 정하고, 사람이 보는 세션에는 기본으로 권하지 않는다 (작업 세션 · 중계가 띄운 세션용).
9. **선례** — 이 PC 에는 이미 두 하네스의 hook 에 붙어 세션 상태를 모으는 외부 도구들이 있다. 같은 hook 면을 쓰는 것이 정상 경로라는 방증이다 (코드는 보지 않았다 — 개념만).

## 3. 요구 (WBS-42.2 — 미작성)

## 4. 추적표 — concept → 요구 (WBS-42.2 — 미작성)
