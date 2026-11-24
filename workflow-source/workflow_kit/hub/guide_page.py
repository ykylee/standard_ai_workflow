"""안내 페이지 ``GET /`` — 지원 하네스 4종의 허브 MCP 등록 명령 (hub_spec §4.1, 요구 R2.6 · I4).

토큰을 보이지 않는다. 두 단계로 보인다:
    ① 등록 전 — 토큰 없이 허브 MCP 를 등록해 부트스트랩 도구(프로젝트 조회 · 등록 · 합류 · 셋업)를 쓴다.
    ② 셋업 뒤 — 부트스트랩이 쓴 설정(환경 변수 참조)으로 다시 연결한다. 명령은 셋업 지시가 대신 낸다.

``GET /setup.md`` (M-039 WBS-39.1 · 소유자 2026-11-21) — **에이전트가 읽는** 셋업 절차. 사람은 "이 주소를 읽고 이
저장소를 셋업해" 한 줄만 말한다. 쓰는 내용은 페이지에 두지 않는다 — 허브의 셋업 지시(hub_setup_plan)가 저장소
상태를 보고 낸다. 페이지는 순서 · 하지 말 것 · 멈출 자리만 말한다.
"""

from __future__ import annotations

import html

from workflow_kit import __version__ as HUB_VERSION
from workflow_kit.hub import KIT_COMPAT_VERSION
from workflow_kit.hub.render import SUPPORTED_HARNESSES, entry_file

KIT_VERSION = KIT_COMPAT_VERSION  # setup asset generator compatibility


def harness_commands(public_url: str) -> dict[str, dict[str, str]]:
    """하네스 → {등록 전 명령, 셋업 뒤 설명}. 4종 목록은 :data:`SUPPORTED_HARNESSES` 에서 파생한다."""
    mcp = public_url.rstrip("/") + "/mcp"
    table = {
        "claude-code": {
            "before": f"claude mcp add --transport http workflow-hub {mcp}",
            "after": "부트스트랩이 .mcp.json 에 'Authorization: Bearer ${WORKFLOW_HUB_TOKEN}' 를 쓴다 (Claude Code 는 이 파일 쓰기에 "
                     "사람 승인을 요구한다) — 토큰을 환경에 올리고 다시 시작",
        },
        "codex": {
            "before": f"codex mcp add workflow-hub --url {mcp}",
            "after": "부트스트랩이 --bearer-token-env-var WORKFLOW_HUB_TOKEN 로 다시 등록한다. 대화형은 허브 도구마다 승인을 묻고, "
                     "비대화(codex exec)는 실행마다 -c 'mcp_servers.workflow-hub.default_tools_approval_mode=\"approve\"' 를 "
                     "줘야 허브 도구를 부른다 (부트스트랩 때도 같다 — 자동 승인은 사람의 선택이라 설정에 쓰지 않는다)",
        },
        "minimax-code": {
            "before": f"저장소 뿌리의 .mcp.json 에 {{\"mcpServers\": {{\"workflow-hub\": {{\"type\": \"http\", \"url\": \"{mcp}\"}}}}}}",
            "after": "부트스트랩이 같은 .mcp.json 에 환경 변수 참조 헤더를 더한다 (Claude Code 와 같은 파일)",
        },
        "antigravity": {
            "before": f"agy mcp add workflow-hub {mcp}",
            "after": "주의: Antigravity 는 헤더의 환경 변수 참조를 확장하지 않는다. 부트스트랩이 토큰을 사용자 범위 "
                     "~/.gemini/config/mcp_config.json 에 평문으로 넣는 명령을 경고와 함께 낸다 — 그 파일을 공유하지 않는다",
        },
    }
    return {h: table[h] for h in SUPPORTED_HARNESSES}


def render_page(public_url: str) -> str:
    rows = []
    for h, c in harness_commands(public_url).items():
        rows.append(
            f"<section><h2>{html.escape(h)} <small>({html.escape(entry_file(h))})</small></h2>"
            f"<p>① 등록 전</p><pre>{html.escape(c['before'])}</pre>"
            f"<p>② 셋업 뒤</p><p>{html.escape(c['after'])}</p></section>"
        )
    return (
        "<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>워크플로우 허브</title>"
        "<style>body{font-family:system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 16px;line-height:1.55}"
        "pre{background:#f4f4f5;padding:.6rem .8rem;overflow-x:auto;white-space:pre-wrap;word-break:break-all}"
        "@media (prefers-color-scheme:dark){body{background:#111;color:#eee}pre{background:#222}}</style></head><body>"
        f"<h1>워크플로우 허브</h1><p>Hub {html.escape(HUB_VERSION)} · kit 호환 {html.escape(KIT_COMPAT_VERSION)} · 계약 hub/1 · 주소 <code>{html.escape(public_url)}</code> · <a href=\"ui/\">화면</a></p>"
        "<p><b>가장 쉬운 길</b>: 에이전트에게 \"<code>" + html.escape(public_url.rstrip("/") + "/setup.md") + "</code> 를 읽고 이 저장소를 셋업해\" "
        "라고 한다 (<a href=\"setup.md\">에이전트용 절차</a>).</p>"
        "<p>저장소 뿌리에서 하네스에 허브 MCP 를 등록한 뒤, 에이전트에게 \"워크플로우 허브에 이 저장소를 등록하고 셋업해\" 라고 한다. "
        "부트스트랩 도구가 프로젝트 등록(또는 합류) · <code>.gitignore</code> 확인 · 토큰 저장 · 진입 파일 · 하네스 설정을 차례로 지시한다. "
        "세션은 허브 MCP에 직접 연결한다. PC에서 원격으로 하네스를 실행할 때만 선택형 로컬 중계를 추가한다.</p>"
        + "".join(rows)
        + "</body></html>"
    )


#: /setup.md 가 부르는 도구 — 허브 도구 표에 있어야 한다 (check_hub_setup_guide 가 대조).
SETUP_TOOLS = ("hub_project_lookup", "hub_project_register", "hub_callsign_register", "hub_setup_plan",
               "hub_setup_confirm", "hub_project_bind_remote", "hub_session_start")


def render_setup_md(public_url: str) -> str:
    """에이전트용 셋업 절차 (text/markdown). 하네스별 등록 명령은 :func:`harness_commands` 한 정본."""
    base = public_url.rstrip("/")
    cmds = harness_commands(public_url)
    harness_lines = "\n".join(
        f"- `{h}` (진입 파일 `{entry_file(h)}`) — 허브 MCP 등록: `{c['before']}`" for h, c in cmds.items())
    return f"""# 워크플로우 허브 셋업 — 에이전트용

허브: `{base}` · Hub {HUB_VERSION} · kit 호환 {KIT_COMPAT_VERSION} · 계약 hub/1

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
3. 이 세션은 등록한 허브 MCP로 직접 통신한다. PC에서 허브가 로컬 Claude Code/Codex 세션을 시작해야 할 때만
   사람에게 선택형 중계를 확인한다. 필요한 경우 bootstrap 명령에 `--relay` 를 더해 기존 설정과 Python `relay status` 를 점검한다.
   필요 없으면 옵션을 생략한다. 상태 출력에는 토큰을 넣지 않는다.

## 2. 부트스트랩 (Python 3.10+ 이 있을 때 — 기본)

```sh
mkdir -p .workflow-hub
curl -fsS -o .workflow-hub/hub_client.py {base}/v1/bootstrap/hub_client.py
python3 .workflow-hub/hub_client.py bootstrap {base} --harness <하네스> --callsign <콜사인> --kind <human|agent> [--relay]
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

Windows PowerShell에서는 위 명령을 `mkdir .workflow-hub` 대신 `New-Item -ItemType Directory -Force .workflow-hub`,
`curl` 대신 `Invoke-WebRequest -Uri <허브>/v1/bootstrap/hub_client.py -OutFile .workflow-hub/hub_client.py` 로 받는다.
그 다음 `python .workflow-hub/hub_client.py bootstrap <허브> --harness <하네스> --callsign <콜사인> --kind <human|agent> [--relay]` 를 쓴다.

## 3. Python 이 없을 때 — HTTP 로 직접

모든 도구는 `POST {base}/v1/tools/<도구>` (본문 JSON). 아래 넷은 토큰 없이 부른다.

1. `hub_project_lookup` `{{"remote_url": "<git remote get-url origin>"}}` — 원격이 없으면 건너뛴다.
2. `project_id` 가 있으면 `hub_callsign_register` `{{"project_id", "callsign", "kind"}}`, 없으면 `hub_project_register`
   `{{"remote_url"(없으면 빼기), "display_name", "callsign", "kind"}}`. **응답을 파일로 받고** (`-o`) 토큰을 화면에 내지 않는다.
3. `hub_setup_plan` `{{"project_id", "token", "harnesses": ["<하네스>"], "scan": {{"files": {{"<경로>": "<내용>" 또는 null}}, "relay": {{"required": <bool>, "config_present": <bool>, "status": <상태 또는 null>}}}}}}`
   — 훑을 파일: `.gitignore` · 진입 파일 · `.mcp.json`. 중계가 필요 없으면 `required: false`; 필요하면 토큰을 뺀 `relay status` 결과를 준다.
   응답 `steps` 를 차례로: `append_line` 은 줄 더하기, `write` 는 내용 그대로
   (`mode` 600 이면 권한), `run_and_report` 는 실행하고 `{{name, rc, output}}` 으로 보고.
4. `hub_setup_confirm` `{{"project_id", "token", "files": [{{"path", "sha256"}}], "checks": [...]}}` →
   `stage` 가 `gitignore` 였으면 3 을 다시 (그 전에는 토큰 파일 지시가 나오지 않는다).

## 4. PC 로컬 중계 (선택)

허브 MCP 연결만으로 세션은 허브와 직접 통신하므로 대부분의 셋업에는 필요 없다. 허브가 원격 task를 PC의 Claude Code 또는
Codex 세션에서 실행해야 할 때만 설치한다. V3가 Go 실행 파일을 차단하는 관리형 Windows에서는 Python 경로를 사용한다.

1. `python -m workflow_kit hub relay status` 로 등록 여부와 허용 목록을 확인한다. 명령을 찾지 못하면 허브 운영자가 제공한
   Python 배포판에서 `python -m pip install 'standard-ai-workflow[hub]'` 를 실행한다.
2. 미등록이면 허브 UI에서 중계 초대를 만들고, PC에서 `python -m workflow_kit hub relay init --hub {base} --invite <초대 코드> --name <PC 이름>` 을 실행한다. 초대 코드는 출력·로그·기록에 남기지 않는다.
3. `python -m workflow_kit hub relay allow add --alias <별칭> --path <허용할 작업 폴더> --harness <claude-code|codex>` 로 접근 범위를 명시한다.
4. `python -m workflow_kit hub relay status` 로 상태를 확인하고, `python -m workflow_kit hub relay serve` 로 실행한다. 중계는 필요할 때만 `pause` / `resume` 으로 제어한다.

Windows에서 Go relay 실행 파일은 필수가 아니다. Python 실행 모듈을 사용한다. 중계는 로컬 PC의 폴더 경로를 허브로 전송하지 않고, 허용 목록의 해시만 보고한다.

## 5. 원격이 나중에 생기면

로컬 키로 등록한 프로젝트는 주소로 찾을 수 없다 — 다른 환경이 합류하지 못한다. 원격을 만든 뒤 승인된 human 소유자가
`hub_project_bind_remote` `{{"remote_url"}}` (헤더 `Authorization: Bearer <토큰>`) 로 묶는다.

## 6. 끝난 뒤

- `.workflow-hub/env` 의 `WORKFLOW_HUB_TOKEN` 을 하네스가 도는 환경에 올리고 하네스를 다시 시작해야 허브 MCP 로 붙는다
  (등록 전 연결에는 토큰이 없다). 다시 붙으면 `hub_session_start`.
- 사람에게 보고: 프로젝트 ID · 콜사인 · 확인된 단계 · 남은 단계와 이유 · 커밋할 파일(`.gitignore` · 진입 파일 ·
  `.mcp.json` — `.workflow-hub/` 는 커밋하지 않는다).

## 하네스별 허브 MCP 등록 (토큰 없이 — 부트스트랩 전에 해도 되고 안 해도 된다)

{harness_lines}
"""
