# Session — MCP 도구 13종 세션 로드 검증 (§2.67, 2026-08-07)

- 문서 목적: §2.60 / §2.66 / TASK-2026-08-05-main-002 가 남긴 "다음 세션 첫 확인" — `.mcp.json` 으로 만든 서버에 *이 세션이* 실제로 붙는지 검증한 결과. root cause 와 후속 후보를 남긴다.
- 범위: 서버 실측, 세션 attach 실측, root cause 3-layer, 1차 출처 stale 발견, 후속 사이클 후보.
- 대상 독자: AI agent, 저장소 관리자.
- 상태: stable.
- 최종 수정일: 2026-08-07
- 관련 문서: [TASK-2026-08-07-main-001](../backlog/tasks/TASK-2026-08-07-main-001.md), [`../../../../workflow-source/core/mcp_installation_by_harness.md`](../../../../workflow-source/core/mcp_installation_by_harness.md), [`./self_application_and_mcp_2026-08-05.md`](./self_application_and_mcp_2026-08-05.md).

## 1. 시작 지점

§2.60 이 `.mcp.json` 을 §2.60 세션에서 만들었고, §2.60 outcome 의 `tools/list 13종` / `tools/call latest_backlog isError=False` (실데이터 반환) 은 *서버 자체*의 실측이다. 그 세션은 시작 시점에 `.mcp.json` 이 없었으므로 attach 안 됨. TASK 의 "다음 세션 첫 확인" 은 — *파일이 있는* 세션이 attach 하는지.

본 세션 시작 시점 (2026-08-07 00:05:59 KST) 에 `.mcp.json` (mtime Aug 6 09:19) 은 존재했음.

## 2. 실측

### 2.1 서버 자체 (재확인)

```bash
cd /Users/yklee/repos/standard_ai_workflow
PYTHONPATH=workflow-source STANDARD_AI_WORKFLOW_ROOT=. \
  python3 -m workflow_kit.server.read_only_jsonrpc --stdio-lines
```

stdin 에 JSON-RPC line 4개 (`initialize` / `notifications/initialized` / `tools/list` / `tools/call latest_backlog {}`) 전송. stdout 결과:

| RPC | result 요약 | 판정 |
|---|---|---|
| `initialize` | `protocolVersion: 2025-03-26`, `serverInfo: {name: "workflow_read_only_bundle", version: "v1.0.0-beta"}`, `capabilities.tools.listChanged: false` | ✅ |
| `tools/list` | `_meta: {descriptor_target: "mcp_tools_list_draft", tool_count: 13, transport_phase: "jsonrpc_draft"}`, 13 tool descriptors | ✅ |
| `tools/call latest_backlog {}` | `error.code: -32000`, `error.data.error_code: "invalid_tool_payload_schema"`, `allowed_fields: ["backlog_dir_path", "work_backlog_index_path"]` | schema 정합 (옳음) |

13종 목록 (이름): `latest_backlog`, `check_doc_metadata`, `check_doc_links`, `suggest_impacted_docs`, `create_backlog_entry`, `create_session_handoff_draft`, `create_environment_record_stub`, `check_quickstart_stale_links`, `summarize_git_history`, `rotate_workflow_logs`, `assess_milestone_progress`, `smart_context_reader`, `apply_robust_patch`. §2.60 outcome 의 13종과 정합.

`transport_ready` 가 어디에도 없음 — §2.66 wire 제거 정합.

`tools/call latest_backlog` 의 `invalid_tool_payload_schema` 는 *결함이 아니라* schema 정합. handoff 의 "isError=False" 는 `latest_backlog_payload()` 의 정식 input (e.g. `{"work_backlog_index_path": "..."}`) 을 줬을 것. 본 task 의 빈 payload 시도는 *schema 가 anyOf 라서 빈 dict 도 거부한다는 사실의 실측*.

### 2.2 세션 attach

mavis 가 본 세션에 노출한 tool 의 출처 분류:

| 출처 | mavis native tool (예) | 비고 |
|---|---|---|
| `mcp.json:matrix` | `image_synthesize`, `gen_videos`, `batch_text_to_video`, `batch_image_to_video`, `synthesize_speech`, `batch_synthesize_speech`, `batch_text_to_music`, `transcribe_audio`, `audios_understand`, `get_voice_list`, `web_search`, `web_fetch` | builtin, "matrix biz-gateway" |
| `mcp.json:playwright` | `playwright` (cli wrapper) | builtin, `@playwright/mcp@0.0.70` |
| `mcp.json:cu` | `computer-use` (skill) | builtin, streamable-http |
| `mcp.json:trash` | (직접 command `mavis-trash` 안내만 — 별도 native tool 노출 ❌) | builtin, streamable-http |
| `mcp.json:github` | (직접 노출 ❌, 인증 helper 만) | enabled |
| **없음** | **`standardAiWorkflowReadOnly` 의 13종** | **글로벌 mcp.json 에 등록돼 있지 않음** |

**13종이 attach 되지 않음** — handoff 의 "그냥 넘기지 말 것" 함수 발동. §2.59 의 "로드는 됐는데 설명이 마커로 떴다" 처럼 *announce 됐지만 실체 없음* 의 변형: *실체는 서버에 있는데 클라이언트가 attach 안 함*.

## 3. root cause (3-layer)

### 3.1 클라이언트 위치 정책

mavis 공식 user-guide (`~/.minimax/.builtin-skills/mavis/references/user-guide.md`):

> "MCP servers live in `{{DATA_DIR}}/mcp.json`. Configure directly in `{{DATA_DIR}}/mcp.json` and validate via MiniMax Code's built-in MCP tooling; no dedicated builtin skill is shipped for onboarding."

> "changing config affects new sessions; old sessions keep their existing runtime context until they rotate"

`{{DATA_DIR}}` = `/Users/yklee/.minimax`. → **글로벌 한 곳** 만 읽음. workspace 단위 (`<root>/.mcp.json`) 자동 로드 *없음*. `{{DATA_DIR}}-<profile>/` 패턴 (e.g. `/Users/yklee/.minimax-coder/`) 만 별도.

`standard_ai_workflow/.mcp.json` (Claude Code §2.60) 은 mavis 가 자동으로 안 읽음.

### 3.2 글로벌 mcp.json 의 현재 등록

`/Users/yklee/.minimax/mcp/mcp.json` (`mtime Jul 12 18:56`, builtin) 의 `mcpServers` 5종: `matrix`, `playwright`, `cu`, `trash`, `github`. `standardAiWorkflowReadOnly` **없음**. → 13종이 mavis native tool 로 재노출되지 않음.

### 3.3 1차 출처 stale

`workflow-source/core/mcp_installation_by_harness.md`:

- §4 표의 **MiniMax Code** 행: 글로벌 위치 = "`~/.MiniMax/mcp.json` 또는 `~/.MiniMax/config.json` 의 `mcp_servers`" — **legacy 빌드 위치**.
- §6.5 의 MiniMax Code 절: "`~/.MiniMax/mcp.json` 또는 `~/.MiniMax/config.json`" 으로 emit / symlink 안내.

mavis 가 *실제* 로 읽는 위치 = `~/.minimax/mcp/mcp.json` (소문자, `/mcp/` 디렉터리). **1차 출처의 MiniMax Code 항목이 stale** 이라, 도입자가 §6.5 만 보고 mavis 글로벌 위치에 등록하면 *조용히* 안 붙는다 (서버는 뜨지만 native tool 로 안 노출).

`§1.2 "project-local config 의 STANDARD_AI_WORKFLOW_ROOT 는 상대 경로다"` 가 끝에 *글로벌은 절대 경로* 정책 한 줄을 두지만, **mavis 의 글로벌 위치 자체** 는 안 가리킴. → 같은 §1.2 의 MiniMax Code (mavis) 별도 안내가 필요.

## 4. 실측으로 뒤집힌 판단 (기록해 둘 것)

- **"다음 세션이 자동으로 attach 되겠지"** → 안 됨. mavis 글로벌 mcp.json 의 5개만 native tool 로 노출, 6번째 등록 없음. §2.60 의 `.mcp.json` 은 *Claude Code 사용자용*.
- **"TASK outcome 의 'isError=False' 가 schema 정합의 증거"** → 그게 *아니라* 정상 payload 의 결과. 빈 payload 거부가 schema 의 원래 모양 (anyOf). 결함 아님.
- **"`~/.MiniMax/mcp.json` 으로 심으면 된다"** (legacy §6.5) → *mavis* 가 안 읽음. mavis 는 `~/.minimax/mcp/mcp.json` 만.

## 5. 다음 한 걸음

`core/mcp_installation_by_harness.md` 보강 (1차 출처 정합) — 본 task 의 §6 산출물. 이 task 가 그 보강까지 같이 닫음.

## 6. 산출물

- `core/mcp_installation_by_harness.md`:
  - §4 표의 MiniMax Code 행 갱신 (글로벌: mavis `~/.minimax/mcp/mcp.json` *우선*, legacy `~/.MiniMax/mcp.json` *차선*).
  - §6.5 재작성: 두 위치 + STANDARD_AI_WORKFLOW_ROOT 절대 경로 정책 + mavis builtin mcp.json 와 merge 시 주의.
  - §1.2 끝에 "MiniMax Code (mavis) 글로벌 위치는 cwd 전제 ❌, 절대 경로 필수 + `STANDARD_AI_WORKFLOW_ROOT` 절대 경로" 한 줄.
  - §8 후속 TASK 1건 추가: bootstrap 에 mavis 자동 등록 옵션.

- `ai-workflow/memory/active/main/session_handoff.md` §5: "첫 번째로 할 일 — MCP 도구 13종이 실제로 붙는지" 를 **§2.67 에서 닫음** 표시 + 본 session 파일 link + 후속 후보 (§2.68) 로 이동.

- `ai-workflow/memory/active/main/state.json`: `generate_workflow_state.py` 재생성. `current_axis` / `recent_done_items` / `generated_at` 갱신.

## 7. 후속 후보 (급한 순)

1. **글로벌 mcp.json 에 standardAiWorkflowReadOnly 등록** — mavis 가 attach 할 수 있는 유일한 자리가 거기. command = `python3`, args = §6 와 동일, env 의 `STANDARD_AI_WORKFLOW_ROOT` 와 `PYTHONPATH` 모두 *절대 경로* (글로벌은 cwd 전제 ❌, §1.2 정책 정합). **새 세션에서 13종 attach 검증 필수** (rotate 후). 이게 닫히면 workflow 가 mavis 데스크탑의 *최초 consumer* 가 된다.
2. **bootstrap 에 mavis 자동 등록** — `bootstrap_workflow_kit.py --harness mavis` 가 `~/.minimax/mcp/mcp.json` 까지 emit 하도록. 1차 출처 §6.5 가 두 위치를 다루니 bootstrap 도 두 위치 옵션 필요.
3. **handoff §2.66 breaking / §2.59 stamp_marker 와 별개 점검** — mavis 가 글로벌 mcp.json 의 변경을 기존 세션에 전파하지 않는 사실이 *consumer 에게 silent* 인 다른 §2.66 breaking 들과 같은 부류인지. 본 task scope 아님.
