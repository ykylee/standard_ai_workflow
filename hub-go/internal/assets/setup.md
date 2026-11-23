# 워크플로우 허브 셋업 — 에이전트용

허브: `{{BASE}}` · kit {{KIT_VERSION}} · 계약 hub/1

사람이 이 문서를 읽고 지금 저장소를 이 허브에 셋업하라고 했다. 아래 순서대로 한다. 쓸 파일의 내용은 이 문서에
없다 — 허브가 저장소 상태를 보고 지시한다.

## 지킬 것

- **토큰을 출력 · 기록하지 않는다.** 토큰은 `.workflow-hub/env` (git 제외, 권한 600) 에만 있다. 명령 인자 · 로그 ·
  보고에 싣지 않는다.
- 허브가 지시한 파일만 쓴다. 지시 밖 파일을 고치거나 지우지 않는다.
- 커밋 · push 는 하지 않는다 — 셋업 결과를 사람에게 보고하고, 커밋할지는 사람이 정한다.
- 하네스가 승인을 물으면 (예: Claude Code 의 `.mcp.json` 쓰기) 우회하지 않는다 — 사람이 답한다.
- 멈출 자리에서는 멈추고 사람에게 묻는다. 추측으로 진행하지 않는다.
- 하네스의 샌드박스가 막으면 (예: Codex 비대화의 `workspace-write` 는 `.git` 쓰기와 네트워크를 막는다) 풀거나 돌아가지
  않는다 — 무엇이 막혔는지 사람에게 말한다. `git init` 은 사람이 해도 된다.

## 1. 위치와 하네스

1. 저장소 뿌리에서 한다 (`git rev-parse --show-toplevel`). git 저장소가 아니면: **빈 폴더면 `git init`**,
   파일이 있는 폴더면 멈추고 묻는다.
2. 너 자신이 어느 하네스인지 정한다 — `claude-code` · `codex` · `minimax-code` · `antigravity`.
   그 밖이면 멈추고 묻는다.

## 2. 부트스트랩 (Python 3.10+ 이 있을 때 — 기본)

```sh
mkdir -p .workflow-hub
curl -fsS -o .workflow-hub/hub_client.py {{BASE}}/v1/bootstrap/hub_client.py
python3 .workflow-hub/hub_client.py bootstrap {{BASE}} --harness <하네스> --callsign <콜사인> --kind <human|agent>
```

- 콜사인: 소문자 · 숫자 · `-` 3~32자, 글자로 시작 (예: `claude-<호스트>`). 사람이 정해 줬으면 그것.
  사람이 직접 쓰는 환경이면 `--kind human`, 에이전트 전용 환경이면 `agent`.
- 한 번에 하는 일: git 원격으로 프로젝트 조회 → 없으면 등록, 있으면 합류 → `.gitignore` 확인 → `.workflow-hub/env`
  → 진입 파일 → 하네스 설정. 원격이 없으면 로컬 키로 등록한다.
- 출력(JSON)의 `status`:
  - `complete` — 끝. 5 로.
  - `partial` (종료 코드 3) — `for_agent` 의 파일을 **내용 그대로** 네 도구로 쓰고 (하네스가 승인을 물으면 사람이 답한다),
    같은 명령을 다시 부른다. `pending` 은 사람에게 보인다 — 사람이 끝냈다고 하면 같은 명령을 다시 불러 확인한다
    (Antigravity 등록은 `agy mcp list` 로 확인한다).
  - `not_git_repo` · `not_repo_root` · `other_hub` · `moved` · `ignore_not_effective` · 그 밖의 실패 — 멈추고 출력을 보인다.
  - `register_failed` 의 `callsign_taken` — 다른 콜사인으로 다시.
- `legacy_1x` 가 있으면 1.x kit 를 쓰던 저장소다. 진입 파일은 쓰지 않았다. 1.x 기록의 전환은 **사람이 정한다**
  (`python3 .workflow-hub/hub_client.py migrate plan` 으로 계획만 보일 수 있다).

## 3. Python 이 없을 때 — HTTP 로 직접

모든 도구는 `POST {{BASE}}/v1/tools/<도구>` (본문 JSON). 아래 넷은 토큰 없이 부른다.

1. `hub_project_lookup` `{"remote_url": "<git remote get-url origin>"}` — 원격이 없으면 건너뛴다.
2. `project_id` 가 있으면 `hub_callsign_register` `{"project_id", "callsign", "kind"}`, 없으면 `hub_project_register`
   `{"remote_url"(없으면 빼기), "display_name", "callsign", "kind"}`. **응답을 파일로 받고** (`-o`) 토큰을 화면에 내지 않는다.
3. `hub_setup_plan` `{"project_id", "token", "harnesses": ["<하네스>"], "scan": {"files": {"<경로>": "<내용>" 또는 null}}}`
   — 훑을 파일: `.gitignore` · 진입 파일 · `.mcp.json`. 응답 `steps` 를 차례로: `append_line` 은 줄 더하기, `write` 는 내용 그대로
   (`mode` 600 이면 권한), `run_and_report` 는 실행하고 `{name, rc, output}` 으로 보고.
4. `hub_setup_confirm` `{"project_id", "token", "files": [{"path", "sha256"}], "checks": [...]}` →
   `stage` 가 `gitignore` 였으면 3 을 다시 (그 전에는 토큰 파일 지시가 나오지 않는다).

## 4. 원격이 나중에 생기면

로컬 키로 등록한 프로젝트는 주소로 찾을 수 없다 — 다른 환경이 합류하지 못한다. 원격을 만든 뒤 승인된 human 소유자가
`hub_project_bind_remote` `{"remote_url"}` (헤더 `Authorization: Bearer <토큰>`) 로 묶는다.

## 5. 끝난 뒤

- `.workflow-hub/env` 의 `WORKFLOW_HUB_TOKEN` 을 하네스가 도는 환경에 올리고 하네스를 다시 시작해야 허브 MCP 로 붙는다
  (등록 전 연결에는 토큰이 없다). 다시 붙으면 `hub_session_start`.
- 사람에게 보고: 프로젝트 ID · 콜사인 · 확인된 단계 · 남은 단계와 이유 · 커밋할 파일(`.gitignore` · 진입 파일 ·
  `.mcp.json` — `.workflow-hub/` 는 커밋하지 않는다).

## 하네스별 허브 MCP 등록 (토큰 없이 — 부트스트랩 전에 해도 되고 안 해도 된다)

- `claude-code` (진입 파일 `CLAUDE.md`) — 허브 MCP 등록: `claude mcp add --transport http workflow-hub {{BASE}}/mcp`
- `codex` (진입 파일 `AGENTS.md`) — 허브 MCP 등록: `codex mcp add workflow-hub --url {{BASE}}/mcp`
- `minimax-code` (진입 파일 `MiniMax.md`) — 허브 MCP 등록: `저장소 뿌리의 .mcp.json 에 {"mcpServers": {"workflow-hub": {"type": "http", "url": "{{BASE}}/mcp"}}}`
- `antigravity` (진입 파일 `ANTIGRAVITY.md`) — 허브 MCP 등록: `agy mcp add workflow-hub {{BASE}}/mcp`
