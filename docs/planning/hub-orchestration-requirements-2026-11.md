# 허브 오케스트레이션 — requirements

- 문서 목적: M-041 concept (소유자 2026-11-22 O1~O10 권고안)을 요구 R 과 검증 방법으로 옮긴다. 그 전제인 **하네스가 실제로 허락하는 제어 수단**을 먼저 실측한다 (M-042).
- 범위: 실측 S (§1 — WBS-42.1), concept 에 주는 영향 (§2), 요구 R (§3 — WBS-42.2, 미작성), 추적표 (§4 — 미작성)
- 대상 독자: 소유자, 구현자 (M-043~)
- 상태: draft — §1 · §2 작성 (2026-11-22), §3 · §4 는 WBS-42.2
- 최종 수정일: 2026-11-22
- 관련 문서: [`hub-orchestration-review-2026-11.md`](./hub-orchestration-review-2026-11.md) (concept — "concept §n"), [`M-042`](../../ai-workflow/memory/active/roadmap/M-042-hub-orchestration-requirements.md), [`workflow-hub-requirements-2026-11.md`](./workflow-hub-requirements-2026-11.md) §16.3 (원격 MCP 실측), [`compact_relay_spec.md`](../../workflow-source/core/compact_relay_spec.md) §7 (Codex hook 실측 기록)

## 0. 요약

concept §3 은 하네스 제어 수단을 전부 "미측정 후보" 로 두었다. 이 호스트(Linux)의 Claude Code 2.1.330 · Codex 0.167.1 로 잰 결과,
**두 하네스 모두 중계가 세션을 띄우고 · 이어 가고 · 실행 중 끼우고 · 상태를 읽는 정식 수단을 이미 갖고 있다** (§1). 그래서 중계의 어댑터는
새 제어 방식을 만들지 않고 **하네스의 제어면을 감싸는 얇은 층**이 된다 (§2). 열린 칸은 셋 — 대화형 세션에 끼우기 · Codex hook (신뢰 필요) ·
Claude Code 백그라운드 세션 (워크스페이스 신뢰 필요).

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

## 2. concept 에 주는 영향

1. **중계 어댑터 = 하네스 제어면 감싸기** — Claude Code 는 stream-json 상주 프로세스 + `--resume` + hook, Codex 는 app-server(JSON-RPC) 가 정본 수단이다. 중계가 PTY 로 대화형 화면을 흉내 내지 않는다.
2. **T2 가 생각보다 강하다** — Codex 는 실행 중 턴에도 끼울 수 있다(`turn/steer`). Claude Code 는 턴 끝 Stop hook 으로 "다음 일"을 같은 세션에 이어 붙일 수 있다 (S3). 그래서 concept §3 의 "깨울 수 있나" 는 T2 에서 ✅ 이고, T1 도 **턴 끝 끌어오기**(Stop)로 쉬기 직전에 받은편지함을 비울 수 있다.
3. **신뢰가 첫 관문이다** — Codex hook 은 사용자가 신뢰해야 돌고, Claude Code 백그라운드 세션은 디렉터리 신뢰가 있어야 뜬다. 중계가 이 신뢰를 대신 기록하지 않는다 — **사람이 하는 셋업 단계**로 두고, 중계는 상태(신뢰 안 됨)를 화면에 보인다. 이것은 concept O4(세션 요청마다 사람 승인)와 같은 방향이다.
4. **하네스 자체 큐와 허브 받은편지함의 관계** — Codex 는 자체 큐(`codex queue`)가 있다. 허브 받은편지함이 정본이고, 중계는 전달 수단으로 하네스 큐를 쓸 수 있다 (두 큐가 정본을 다투지 않게 — 소비 확인은 허브 `ack`).
5. **상태는 하네스가 이미 준다** — `claude agents --json` 의 `idle`/`busy`, app-server 의 `thread/status/changed`. 중계는 이것을 허브 상태(`idle` · `working` · …)로 옮기기만 한다. 못 읽으면 `unknown`.
6. **선례** — 이 PC 에는 이미 두 하네스의 hook 에 붙어 세션 상태를 모으는 외부 도구들이 있다. 같은 hook 면을 쓰는 것이 정상 경로라는 방증이다 (코드는 보지 않았다 — 개념만).

## 3. 요구 (WBS-42.2 — 미작성)

## 4. 추적표 — concept → 요구 (WBS-42.2 — 미작성)
