"""Agent Plugins 1.0 **공유 payload 렌더러** (v1.1.9+, TASK-2026-08-12-main-014).

## 왜 필요한가

플러그인 배포 전환 계획(`docs/planning/plugin-transition-plan-2026-08.md`)의 원칙 1은
**"플러그인은 파생본이다"** 이다. 손으로 만든 플러그인 파일을 저장소에 두는 순간
§11 이전의 "손 사본" 세계로 돌아간다 — 사본은 갈라지고, 갈라져도 아무 검사가 실패
하지 않으면 아무도 모른다 (실측: §11.1 명령의 손 사본 7곳, 렌더러 26개의 메모리
갱신 지시 누락).

그래서 `plugin/` 디렉터리 **전체**를 이 모듈이 정본에서 생성한다:

```
plugin/
├── plugin.json                  # name / version / description (version 은 __version__ 파생)
├── .codex-plugin/plugin.json    # Codex plugin manifest (Codex distribution)
├── skills/                      # 스킬 4종 — Claude Code 와 Gemini 확장이 같은 관례 경로로 읽는다
│   ├── session-start/           # SKILL.md + Codex UI metadata (agents/openai.yaml)
│   ├── backlog-update/SKILL.md  # 상태값 4종은 rules.task_states 파생
│   ├── doc-sync/SKILL.md
│   └── session-end/SKILL.md
├── mcp.json                     # MCP mcpServers 스키마, read-only bundle (+ .mcp.json 동일 사본)
├── gemini-extension.json        # Gemini CLI 어댑터 — 확장 루트 = payload 루트 (P3)
├── GEMINI.md                    # Gemini 상시 주입 컨텍스트 — render_entrypoint_rules 파생
└── adapters/
    ├── claude-code/hooks.json   # 세션 경계 hook (P2) + 조건부 규칙 주입 (TASK-003)
    ├── claude-code/rules.md     # SessionStart 조건부 주입 규칙 블록 — render_entrypoint_rules 파생
    ├── goose/config-snippet.yaml      # goose extensions 병합 snippet (P3)
    └── opencode/opencode-snippet.json # OpenCode MCP 등록 snippet (P3)
```

## 무엇이 정본인가

| payload 축 | 정본 | 파생 경로 |
|---|---|---|
| §11 갱신 명령 | `core/global_workflow_standard.md` §11.1 | :func:`find_memory_command` |
| §11.2 파싱 계약 | 정본 §11.2 | :func:`render_memory_update_section` |
| 작업 상태값 4종 | 정본 §3 | ``rules.task_states`` |
| MCP 서버 command/args | :mod:`workflow_kit.bootstrap_lib.mcp` | :func:`mcp_server_command` |
| MCP 도구 구성 | :mod:`workflow_kit.server.read_only_registry` | ``tool_specs_for_bundle`` |
| plugin 버전 | ``workflow_kit.__version__`` | 직접 참조 |

**이 모듈에는 규칙 문장 리터럴을 두지 않는다.** `check_standard_single_source.py`
의 case 2 가 이 파일도 대상으로 삼는다 — 규칙을 여기 적으면 그 검사가 FAIL 한다.

## 스키마에 대해 알고 있는 것과 모르는 것

- `plugin.json` 은 계획 §3-P1 이 명시한 **name / version / description** 3필드만 쓴다.
  Agent Plugins 1.0 (2026-08-06 출범) 의 선택 필드 전체 스펙은 이 저장소가 아직
  원문으로 확인하지 못했다 — 확인되지 않은 필드를 지어 넣지 않는다. 필드 추가는
  스펙 확인 후 **명시 task** 로 한다 (계획 §5 리스크 표).
- `mcp.json` 은 사실상 전 하네스가 공유하는 MCP ``mcpServers`` 스키마를 쓴다
  (검토 문서 §1 의 "도구" 행). write bundle 은 payload 에 싣지 않는다 — 파일시스템을
  바꾸는 도구는 명시 opt-in 이다 (ADR-003).

## 생성과 검증

- 생성: ``python3 -m workflow_kit.plugin_payload --apply``
- 검증: ``tests/check_agent_plugin_payload.py`` (drift + frontmatter + 정본 파생 +
  registry 정합 + 되주입 실증)

Cross-ref: `docs/planning/plugin-transition-plan-2026-08.md` §3-P1,
`docs/planning/multi-harness-plugin-review-2026-08.md` §3.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, NamedTuple, Sequence

from workflow_kit.common.standard_rules import (
    StandardRules,
    find_memory_command,
    load_standard_rules,
    render_entrypoint_rules,
    render_memory_update_section,
)

__all__ = [
    "PAYLOAD_DIRNAME",
    "PLUGIN_NAME",
    "PLUGIN_DESCRIPTION",
    "PLUGIN_SKILLS",
    "MARKETPLACE_RELPATH",
    "PluginSkillSpec",
    "current_kit_version",
    "default_payload_root",
    "default_repo_root",
    "render_agent_plugin",
    "render_claude_code_hooks",
    "render_claude_code_manifest",
    "render_codex_manifest",
    "render_claude_code_rules",
    "render_gemini_context",
    "render_gemini_manifest",
    "render_goose_config_snippet",
    "render_marketplace_manifest",
    "render_opencode_snippet",
    "render_openai_agent_metadata",
    "render_plugin_manifest",
    "render_plugin_mcp_config",
    "render_plugin_skill",
    "render_repo_plugin_files",
    "write_agent_plugin",
    "write_repo_plugin_files",
]

#: payload 디렉터리 이름 (저장소 루트 기준). 어댑터(P2~P3)는 이 경로를 참조만 한다.
PAYLOAD_DIRNAME = "plugin"

#: 플러그인 식별자. Claude Code 는 스킬을 ``/<plugin-name>:<skill-name>`` 으로
#: 네임스페이스 하므로, bootstrap 이 심는 동명 스킬과 충돌하지 않는다 (계획 §5).
PLUGIN_NAME = "standard-ai-workflow"

#: MCP 서버 등록에 쓰는 bundle 선택자. write bundle 은 payload 에 싣지 않는다.
PAYLOAD_MCP_BUNDLE = "read-only"

#: payload 가 전제하는 MCP bridge. jsonrpc-bridge 는 `mcp` SDK 없이도 뜬다
#: (`MCP_BRIDGE_APPLY_MODE` 가 유일하게 ``active_ok`` 로 선언한 transport).
PAYLOAD_MCP_BRIDGE = "jsonrpc-bridge"

#: Claude Code 어댑터 manifest 의 payload 내 경로. 플러그인 **루트가 곧 payload
#: 루트**여야 한다 — 실측(`claude plugin validate`)에서 manifest 의 경로 필드가
#: ``..`` 를 거부했다 ("path traversal"). 즉 어댑터를 하위 디렉터리에 두고 payload 를
#: 올려다보는 배치는 성립하지 않는다. 대신 Claude Code 의 관례 경로(`skills/`)가
#: payload 배치와 그대로 겹쳐서, 어댑터는 manifest + hooks 두 장으로 끝난다.
CLAUDE_CODE_MANIFEST_RELPATH = ".claude-plugin/plugin.json"
CLAUDE_CODE_HOOKS_RELPATH = "adapters/claude-code/hooks.json"

#: SessionStart hook 이 조건부로 주입하는 규칙 블록 파일 (TASK-2026-08-13-main-003).
#: P5 실측이 근거다: hook stdout 은 모델 컨텍스트에 실제 주입된다. 다만 bootstrap
#: 이 이미 진입점(CLAUDE.md)에 규칙을 넣은 프로젝트에서는 **이중 주입**이 되므로,
#: hook 은 진입점의 생성 마커를 먼저 확인하고 없을 때만 이 파일을 cat 한다.
CLAUDE_CODE_RULES_RELPATH = "adapters/claude-code/rules.md"

#: Claude Code 가 MCP 서버를 **실제로 읽는** 경로. Agent Plugins 의 `mcp.json` 과
#: 내용이 같고 파일명만 다르다 — 두 표준이 같은 것을 다르게 부른다.
#:
#: 여기가 실측이 계획을 고친 자리다. manifest 에 ``"mcpServers": "./mcp.json"`` 을
#: 선언하면 `claude plugin validate --strict` 는 **통과하지만**
#: `claude plugin details` 의 인벤토리는 ``MCP servers (0)`` 이었다 — 검증기는
#: 경로 존재만 보고 로더는 그 필드를 그렇게 쓰지 않는다. 관례 경로 `.mcp.json`
#: 으로 옮기자 ``MCP servers (1)`` 로 잡혔다. **validate 통과는 로드 증명이 아니다.**
CLAUDE_CODE_MCP_RELPATH = ".mcp.json"

#: Codex plugin manifest. Codex 배포물은 이 파일과 ``skills/``를 최소 단위로
#: 묶으며, Claude Code manifest와 같은 payload를 공유하되 설치 surface는 분리한다.
CODEX_MANIFEST_RELPATH = ".codex-plugin/plugin.json"

#: Gemini CLI 어댑터 (P3, TASK-2026-08-12-main-016). Claude Code 와 같은 이유로
#: **확장 루트 = payload 루트**다: `gemini extensions list` 실측(0.42.0)에서 확장
#: 루트의 `skills/` 를 무변환으로 읽어 payload 스킬 4종이 그대로 인벤토리에 잡혔다.
#: 어댑터를 하위 디렉터리에 두면 그 공유가 깨지고 스킬 사본이 필요해진다.
#:
#: `GEMINI.md` 는 확장이 **상시 주입하는 컨텍스트 파일**이다 — Claude Code 플러그인의
#: 핵심 갭(§1·§3·§8 규칙 상시 주입 채널 부재)이 Gemini 에는 없다. 그래서 여기만
#: 진입점 전체 블록(`render_entrypoint_rules`)을 싣는다.
GEMINI_MANIFEST_RELPATH = "gemini-extension.json"
GEMINI_CONTEXT_RELPATH = "GEMINI.md"

#: goose / OpenCode 어댑터 — 두 하네스 모두 스킬은 `.agents/skills/` 를 직접 읽으므로
#: (multi-harness-plugin-review §2) 어댑터가 나를 것은 MCP 등록 snippet 뿐이다.
#: goose snippet 은 goose CLI 부재 환경에서 공식 문서 스키마로 작성했다 — 실측 미완
#: 이라는 사실을 snippet 주석에도 남긴다 (조용한 미검증 금지).
GOOSE_SNIPPET_RELPATH = "adapters/goose/config-snippet.yaml"
OPENCODE_SNIPPET_RELPATH = "adapters/opencode/opencode-snippet.json"

#: marketplace manifest 는 payload 밖 — **저장소 루트**가 marketplace 다
#: (`/plugin marketplace add <owner>/<repo>`).
MARKETPLACE_RELPATH = ".claude-plugin/marketplace.json"

#: manifest 의 author 필드. 없으면 `claude plugin validate --strict` 가 경고를
#: 에러로 올린다 (실측).
PLUGIN_AUTHOR = {"name": "ykylee"}


class PluginSkillSpec(NamedTuple):
    """payload 의 SKILL.md 한 장 — slug / description / 본문 렌더러."""

    slug: str
    description: str
    body: Callable[[StandardRules], str]


# ---------------------------------------------------------------------------
# SKILL.md 본문 — 절차만 쓰고, 규칙·명령·상태값은 정본에서 꺼낸다
# ---------------------------------------------------------------------------


def _session_start_body(rules: StandardRules) -> str:
    command = find_memory_command(rules, "세션 시작")
    return f"""## 역할

`ai-workflow/memory/active/<branch>/` 의 현재 baseline 을 복원하고, 다음 작업
후보를 보고한다.

## 절차

1. `state.json` — 현재 기준선 (`latest_backlog_path`, 진행/차단/최근 완료 목록)
2. `session_handoff.md` — 이전 세션의 인계 사항
3. `backlog/<YYYY-MM-DD>.md` — 현재 작업 목록
4. `docs/PROJECT_PROFILE.md` — 프로젝트 메타
5. (있으면) `ai-workflow/memory/active/PURPOSE.md` — directional intent

읽은 뒤 한국어로 **1줄 기준선 요약 + 3~5개 다음 작업 후보 + 권장 다음 행동** 만
보고한다. 중간 reasoning, 중복 요약, 자기 설명은 내지 않는다.

`state.json` 이나 `PURPOSE.md` 가 없으면 실패로 처리하지 말고 *graceful skip* 후
scaffold 를 제안한다.

## 실행

```bash
{command} --help
```

`{command.split()[0]}` 가 없으면 조용히 넘어가지 않는다 — 설치 안내를 보고하고
멈춘다 (`INSTALLATION_AND_USAGE.md` §3)."""


def _backlog_update_body(rules: StandardRules) -> str:
    command = find_memory_command(rules, "task 등록")
    states = " / ".join(f"`{state}`" for state in rules.task_states)
    return f"""## 역할

오늘 작업을 `ai-workflow/memory/active/<branch>/backlog/<YYYY-MM-DD>.md` 와
`./tasks/<TASK-ID>.md` 에 등록하거나 갱신한다.

## 절차

1. 오늘 날짜 backlog 파일이 없으면 신규 작성, 있으면 기존 항목에 병합한다.
2. 상태값은 {states} 넷만 쓴다.
3. **in-scope check** — `task_brief` 와 영향 문서를 `PURPOSE.md` §3 의 제외 영역과
   대조해, 겹치면 scope creep 경고를 1줄 남긴다. `PURPOSE.md` 가 없으면 경고 없이
   advisory 로만 진행한다.
4. 우선순위 / 담당 / 완료 기준을 명시한다.

## 실행

```bash
{command} --help
```

상태를 바꾸지 않을 때는 `--status` 를 주지 않는다 — 미지정은 "바꾸지 말라" 는
뜻이고 기존 상태가 보존된다."""


def _doc_sync_body(rules: StandardRules) -> str:
    command = find_memory_command(rules, "동기화")
    return f"""## 역할

변경된 파일에서 영향 문서 후보를 뽑고, 갱신 포인트를 **advisory 로** 제안한다.
자동 반영하지 않는다.

## 절차

1. 현재 변경된 파일 목록에서 영향 문서 후보를 식별한다.
2. `ai-workflow/wiki/index.md` 의 anchor 카탈로그와 대조한다.
3. 후보별로 경로 + 1줄 요약 + confidence (high / medium / low) 를 보고한다.
4. 새 concept / decision / pattern 페이지가 필요한지 판단해 제안한다.

## 실행

```bash
{command} --help
```"""


def _session_end_body(rules: StandardRules) -> str:
    command = find_memory_command(rules, "state.json 재생성")
    states = " / ".join(f"`{state}`" for state in rules.task_states)
    return f"""## 역할

세션을 종료하며, 다음 세션이 바로 이어받을 수 있게 상태를 남긴다.

## 순서

{rules.close_order}

## 절차

1. `session_handoff.md` 를 갱신한다 — 현재 기준선, 진행 중 / 차단 / 최근 완료 목록.
2. 오늘 날짜 backlog 의 task 상태를 실제 결과에 맞춘다 ({states}).
3. `state.json` 을 **재생성**한다 (손으로 고치지 않는다 — 아래 §11 계약).
4. 1~3 의 갱신분이 **같은 commit 에** 담기게 한 뒤 push 한다.

## 실행

```bash
{command}
```

`{command.split()[0]}` 가 없으면 조용히 넘어가지 않는다 — 설치 안내를 보고하고
멈춘다 (`INSTALLATION_AND_USAGE.md` §3). 재생성 없이 손으로 쓴 `state.json` 은
입력 문서와 갈라진다."""


#: payload 가 싣는 스킬 4종. slug 는 소문자·하이픈만 (Agent Skills 이름 규칙).
#: 정본 §11.1 의 명령 4개와 1:1 대응한다 — 명령만 있고 스킬이 없으면 하네스가
#: 그 단계를 밟을 방법을 모른다 (session-end 가 정확히 그 상태였다).
PLUGIN_SKILLS: tuple[PluginSkillSpec, ...] = (
    PluginSkillSpec(
        slug="session-start",
        description=(
            "표준 AI 워크플로우 세션 시작 — state.json + session_handoff.md + backlog 로 "
            "현재 기준선을 복원하고 다음 작업 후보를 보고한다."
        ),
        body=_session_start_body,
    ),
    PluginSkillSpec(
        slug="backlog-update",
        description=(
            "표준 AI 워크플로우 백로그 갱신 — 오늘 날짜 backlog 에 task 를 등록/갱신하고 "
            "PURPOSE.md 제외 영역과 겹치면 scope creep 을 경고한다."
        ),
        body=_backlog_update_body,
    ),
    PluginSkillSpec(
        slug="doc-sync",
        description=(
            "표준 AI 워크플로우 문서 동기화 — 변경된 파일에서 영향 문서 후보를 뽑고 "
            "wiki index 기준 갱신 포인트를 advisory 로 제안한다."
        ),
        body=_doc_sync_body,
    ),
    PluginSkillSpec(
        slug="session-end",
        description=(
            "표준 AI 워크플로우 세션 종료 — handoff 와 backlog 를 갱신하고 state.json 을 "
            "재생성해 다음 세션이 그대로 이어받게 남긴다."
        ),
        body=_session_end_body,
    ),
)

#: 스킬 개수는 :data:`PLUGIN_SKILLS` 에서 **파생**한다. 손으로 적으면 스킬을 늘릴 때
#: 이 문장만 낡는다 — 실측으로 확인했다: `session-end` 를 넣은 직후
#: `claude plugin details` 의 인벤토리는 ``Skills (4)`` 인데 그 바로 위 설명은
#: 여전히 "스킬 3종" 이었다. 이 저장소가 §11.1 명령 사본·MCP 도구 목록 사본에서
#: 이미 두 번 겪은 것과 같은 계열이다.
PLUGIN_DESCRIPTION = (
    f"세션 시작 / 백로그 갱신 / 문서 동기화 / 세션 종료를 표준 AI 워크플로우 절차로 "
    f"수행하는 스킬 {len(PLUGIN_SKILLS)}종과 read-only MCP 도구 번들."
)


# ---------------------------------------------------------------------------
# 렌더러
# ---------------------------------------------------------------------------


def current_kit_version() -> str:
    """**호출 시점**의 kit 버전.

    모듈 수준에서 읽은 버전을 기본 인자로 박으면 값이 두 겹으로 굳는다:
    ``workflow_kit.__version__`` 은 import 시점에 pyproject 를 1회 파싱하고,
    기본 인자는 **함수 정의 시점**에 그 값으로 고정된다. 그래서 같은 프로세스에서
    version bump 를 한 뒤 재생성하면 **낡은 버전이 조용히 박힌다** — 실측으로
    확인했다 (P4, TASK-2026-08-12-main-017): ``__version__`` 을 바꿔도 재생성된
    manifest 는 bump 이전 값이었다.

    검사는 매번 새 프로세스라 이 자리를 못 잡는다. 릴리스 파이프라인이 bump 와
    재생성을 한 프로세스에서 이어 하는 순간에만 발현하므로, 그 자리를 만들기
    전에 뿌리를 없애 둔다. 정본(pyproject → installed metadata) 을 호출 시점에
    다시 읽는다.
    """
    from workflow_kit import _read_pyproject_version

    return _read_pyproject_version()


def render_plugin_manifest(version: str | None = None) -> str:
    """``plugin/plugin.json`` — Agent Plugins 1.0 manifest.

    필드는 계획 §3-P1 이 명시한 3개뿐이다. 스펙 원문으로 확인하지 못한 선택 필드는
    넣지 않는다 — 지어낸 필드는 스펙 확정 시 조용히 틀린 값이 된다.

    ``version`` 기본값이 :func:`current_kit_version` 인 이유는 그 docstring 참조.
    """
    return json.dumps(
        {
            "name": PLUGIN_NAME,
            "version": version if version is not None else current_kit_version(),
            "description": PLUGIN_DESCRIPTION,
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def render_codex_manifest(version: str | None = None) -> str:
    """``plugin/.codex-plugin/plugin.json`` — Codex 전용 plugin manifest.

    Codex는 Agent Skills를 직접 읽지만 marketplace/install surface에서는
    ``.codex-plugin/plugin.json``이 필요하다. MCP는 read-only bundle만 연결한다.
    """
    return json.dumps(
        {
            "name": PLUGIN_NAME,
            "version": version if version is not None else current_kit_version(),
            "description": PLUGIN_DESCRIPTION,
            "author": {
                **PLUGIN_AUTHOR,
                "email": "yklee@users.noreply.github.com",
                "url": "https://github.com/ykylee",
            },
            "repository": "https://github.com/ykylee/standard_ai_workflow",
            "license": "MIT",
            "keywords": ["workflow", "codex", "agent-skills"],
            "skills": "./skills/",
            "mcpServers": f"./{CLAUDE_CODE_MCP_RELPATH}",
            "interface": {
                "displayName": "Standard AI Workflow",
                "shortDescription": "Standard session and documentation workflow",
                "longDescription": PLUGIN_DESCRIPTION,
                "developerName": PLUGIN_AUTHOR["name"],
                "category": "Productivity",
                "capabilities": ["Workflow", "MCP"],
                "defaultPrompt": [
                    "Use $session-start to restore the current workflow baseline.",
                    "Use $backlog-update to register today's workflow task.",
                ],
            },
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def render_plugin_mcp_config() -> str:
    """``plugin/mcp.json`` — read-only bundle 하나만 등록한다.

    command / args 는 :func:`workflow_kit.bootstrap_lib.mcp.mcp_server_command` 파생
    이다. 여기서 직접 조립하면 entry-point 모듈명이 바뀔 때 이 사본만 낡는다
    (실측: Grok 렌더러가 손으로 적은 command 를 들고 있었다).

    ``env`` 에 ``PYTHONPATH`` 를 넣지 않는 이유: 플러그인은 소비 프로젝트의 체크아웃
    구조를 모른다. `wk` / `workflow_kit` 은 설치 전제이고 (계획 원칙 4), 그 전제가
    깨지면 서버가 뜨지 않는 것으로 드러나야 한다 — 상대 경로를 심어 두면 "왜인지
    모르게 안 되는" 경로가 생긴다.
    """
    from workflow_kit.bootstrap_lib.mcp import MCP_SERVER_ALIAS, mcp_server_command

    command = mcp_server_command(PAYLOAD_MCP_BRIDGE, PAYLOAD_MCP_BUNDLE)
    return json.dumps(
        {
            "mcpServers": {
                MCP_SERVER_ALIAS: {
                    "type": "stdio",
                    "command": command[0],
                    "args": command[1:],
                    "env": {"STANDARD_AI_WORKFLOW_ROOT": "."},
                }
            }
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def _payload_mcp_entry() -> tuple[str, list[str]]:
    """payload 가 등록하는 MCP 서버의 (alias, command+args).

    모든 어댑터가 이 하나에서 파생한다 — 방언별 파일이 각자 command 를 조립하면
    entry-point 모듈명이 바뀔 때 일부 사본만 낡는다 (Grok 렌더러 실측 동형).
    """
    from workflow_kit.bootstrap_lib.mcp import MCP_SERVER_ALIAS, mcp_server_command

    return MCP_SERVER_ALIAS, mcp_server_command(PAYLOAD_MCP_BRIDGE, PAYLOAD_MCP_BUNDLE)


#: 어댑터 MCP 등록이 공유하는 env. ``PYTHONPATH`` 를 넣지 않는 이유는
#: :func:`render_plugin_mcp_config` docstring 과 같다 — 플러그인은 소비 프로젝트의
#: 체크아웃 구조를 모르고, 설치 전제가 깨지면 드러나야 한다 (계획 원칙 4).
_PAYLOAD_MCP_ENV = {"STANDARD_AI_WORKFLOW_ROOT": "."}


def render_gemini_manifest(version: str | None = None) -> str:
    """``plugin/gemini-extension.json`` — Gemini CLI 확장 manifest.

    필드 5개는 전부 실측으로 확정했다 (gemini 0.42.0, `extensions validate` +
    `extensions link` 후 `extensions list` 인벤토리):

    - ``contextFileName`` — 상시 주입 컨텍스트 파일 선언. 인벤토리의
      "Context files" 에 잡히는 것까지 확인했다 (모델 주입 계층은 P5 게이트).
    - ``mcpServers`` — Gemini 는 manifest **안에** 인라인으로 둔다 (Claude Code 의
      관례 파일 `.mcp.json` 과 다른 자리, 같은 파생).
    - ``skills/`` 는 선언이 필요 없다 — 확장 루트의 관례 경로를 그대로 읽는다.
      payload 스킬 4종이 무변환으로 잡히는 것을 실측했다.
    """
    alias, command = _payload_mcp_entry()
    return json.dumps(
        {
            "name": PLUGIN_NAME,
            "version": version if version is not None else current_kit_version(),
            "description": PLUGIN_DESCRIPTION,
            "contextFileName": GEMINI_CONTEXT_RELPATH,
            "mcpServers": {
                alias: {
                    "command": command[0],
                    "args": command[1:],
                    "env": dict(_PAYLOAD_MCP_ENV),
                }
            },
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def render_gemini_context(rules: StandardRules) -> str:
    """``plugin/GEMINI.md`` — Gemini 확장이 상시 주입하는 규칙 블록.

    내용은 bootstrap 이 진입점(`CLAUDE.md`/`GEMINI.md` …)에 주입하는 것과 **같은
    파생 함수**(:func:`render_entrypoint_rules`) 다 — 채널이 둘이어도 정본은 하나다.
    """
    return (
        "# 표준 AI 워크플로우 — 상시 규칙 (Gemini 확장 컨텍스트)\n"
        "\n"
        f"{render_entrypoint_rules(rules)}\n"
    )


def render_goose_config_snippet() -> str:
    """``plugin/adapters/goose/config-snippet.yaml`` — goose 는 extension = MCP 서버.

    사용자가 goose 설정(`config.yaml`)의 ``extensions:`` 아래에 병합하는 snippet 이다.
    스킬은 어댑터가 필요 없다 — goose 는 `.agents/skills/` 를 직접 읽는다.

    **실측 미완**: 이 환경에 goose CLI 가 없어 공식 문서 스키마로 작성했다.
    그 사실을 snippet 주석에도 남긴다 — 검증 안 된 산출물이 검증된 것과 같은
    얼굴을 하면 안 된다.
    """
    alias, command = _payload_mcp_entry()
    args_yaml = "\n".join(f"      - \"{arg}\"" for arg in command[1:])
    env_yaml = "\n".join(f"      {key}: \"{value}\"" for key, value in _PAYLOAD_MCP_ENV.items())
    return f"""# 생성물 — 손으로 고치지 않는다 (`python3 -m workflow_kit.plugin_payload --apply`).
# goose 설정(config.yaml)의 `extensions:` 아래에 병합한다.
# 스킬은 이 snippet 과 무관하게 goose 가 `.agents/skills/` 에서 직접 읽는다.
# 주의: goose CLI 부재 환경에서 공식 문서 스키마로 작성 — 실기 검증 미완 (계획 §3-P3).
extensions:
  {alias}:
    enabled: true
    type: stdio
    cmd: {command[0]}
    args:
{args_yaml}
    envs:
{env_yaml}
    timeout: 300
"""


def render_opencode_snippet() -> str:
    """``plugin/adapters/opencode/opencode-snippet.json`` — OpenCode MCP 등록.

    최상위 키는 bootstrap 의 OpenCode 방언과 같은 상수(``MCP_CONFIG_ROOT_KEY``)에서
    파생한다. entry 형태는 **opencode 1.17.12 실측**으로 확정했다 (`opencode mcp
    list` 가 서버 ``connected`` 까지 보고):

    - ``command`` 는 **배열 전체**다 — 문자열 ``command`` + ``args`` 분리형은
      *"Expected array"* 로 거부된다.
    - ``enabled`` 는 필수다 — 없으면 *"Missing key"*.
    - env 키 이름은 ``environment`` 다.

    entry 형태는 :func:`workflow_kit.bootstrap_lib.mcp.opencode_mcp_server_entry`
    (실측 정본, TASK-2026-08-13-main-002 에서 bootstrap 과 단일화) 파생이다.
    스킬은 snippet 과 무관하게 OpenCode 가 `.agents/skills/` / `.claude/skills/`
    에서 직접 읽는다.
    """
    from workflow_kit.bootstrap_lib.mcp import MCP_CONFIG_ROOT_KEY, opencode_mcp_server_entry

    alias, command = _payload_mcp_entry()
    return json.dumps(
        {
            MCP_CONFIG_ROOT_KEY["opencode"]: {
                alias: opencode_mcp_server_entry(command, _PAYLOAD_MCP_ENV)
            }
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def render_claude_code_manifest(version: str | None = None) -> str:
    """``plugin/.claude-plugin/plugin.json`` — Claude Code 어댑터 manifest.

    payload 를 **참조만** 한다. `skills/` 와 `.mcp.json` 은 Claude Code 의 관례
    경로라 선언조차 필요 없다 — manifest 에 남는 것은 이름·버전·저자와, 관례
    밖에 둔 hooks 경로뿐이다.

    필드 구성은 `claude plugin validate --strict` + `claude plugin details` 실측
    으로 정했다: `author` 가 없으면 경고를 에러로 올리고, 경로 필드의 ``..`` 는
    거부되며 (그래서 플러그인 루트 = payload 루트여야 한다), 미지 필드는
    "Claude Code ignores it at load time" 경고가 된다. ``mcpServers`` 경로 선언은
    :data:`CLAUDE_CODE_MCP_RELPATH` 주석의 이유로 쓰지 않는다.
    """
    return json.dumps(
        {
            "name": PLUGIN_NAME,
            "version": version if version is not None else current_kit_version(),
            "description": PLUGIN_DESCRIPTION,
            "author": PLUGIN_AUTHOR,
            "hooks": f"./{CLAUDE_CODE_HOOKS_RELPATH}",
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def _rules_marker_probe() -> str:
    """진입점에 규칙 블록이 이미 있는지 판정할 grep 탐침 — 생성 마커에서 파생.

    :data:`~workflow_kit.common.standard_rules.GENERATED_MARKER` 는 bootstrap 이
    진입점에 규칙 블록을 주입할 때 함께 넣는 HTML 주석이다. hook 은 그 앞부분
    (``generated-from: ...``)을 fixed-string 으로 찾는다 — 여기 문자열을 손으로
    박으면 마커 개정 시 hook 만 낡아 **항상 이중 주입**이 된다.
    """
    from workflow_kit.common.standard_rules import GENERATED_MARKER

    return GENERATED_MARKER.split("—")[0].removeprefix("<!--").strip()


def render_claude_code_rules(rules: StandardRules) -> str:
    """``plugin/adapters/claude-code/rules.md`` — SessionStart 조건부 주입 규칙 블록.

    내용은 bootstrap 진입점·Gemini 컨텍스트와 **같은 파생 함수**
    (:func:`render_entrypoint_rules`) 다 — 채널이 셋이어도 정본은 하나다.
    """
    return (
        "# 표준 AI 워크플로우 — 상시 규칙 (플러그인 SessionStart 주입)\n"
        "\n"
        f"{render_entrypoint_rules(rules)}\n"
    )


def render_claude_code_hooks(rules: StandardRules) -> str:
    """``plugin/adapters/claude-code/hooks.json`` — 세션 경계 자동화.

    세 개를 건다:

    - **SessionEnd** → §11.1 의 state.json 재생성 명령. 이 저장소가 오래 겪은
      문제가 "종료 절차에 생성기를 부르는 단계가 없어서 손으로 썼다" 였다
      (TASK-2026-08-11-main-018). 플러그인은 그 단계를 하네스가 대신 밟게 한다 —
      goose 말고는 없던 자동화다.
    - **SessionStart ①** → `wk` 부재 안내. 계획 원칙 4: 플러그인은 Python 의존을
      대신 설치해 주지 못하므로, 없으면 **조용히 실패하지 않고 말해야** 한다.
    - **SessionStart ②** → 규칙 블록 **조건부 주입** (TASK-2026-08-13-main-003).
      P5 실측: hook stdout 은 모델 컨텍스트에 주입된다. 진입점(`CLAUDE.md` /
      `.claude/CLAUDE.md` — Claude Code 가 자동 read 하는 두 파일)에 생성 마커가
      있으면 bootstrap 이 이미 규칙을 넣은 것이므로 생략한다 (이중 주입 방지).
      `@AGENTS.md` import 패턴(이 kit 의 CLAUDE.md 통합 권장안)도 AGENTS.md 쪽
      마커로 인정한다. 마커 탐침은 :func:`_rules_marker_probe` 파생.

    명령은 정본 §11.1 파생이다 (`find_memory_command`). 여기에 문자열을 박으면
    §11.1 개명 시 이 사본만 낡는다.
    """
    refresh_cmd = find_memory_command(rules, "state.json 재생성")
    binary = refresh_cmd.split()[0]
    guide = "docs/INSTALLATION_AND_USAGE.md §3"
    absent_notice = (
        f"[{PLUGIN_NAME}] `{binary}` 를 찾지 못했다 — 스킬은 절차를 안내하지만 "
        f"메모리 갱신 명령은 돌지 않는다. 설치: {guide}"
    )
    probe = _rules_marker_probe()
    rules_inject = (
        f"{{ grep -qsF '{probe}' CLAUDE.md .claude/CLAUDE.md; }} || "
        f"{{ grep -qsF '@AGENTS.md' CLAUDE.md && grep -qsF '{probe}' AGENTS.md; }} || "
        f'cat "${{CLAUDE_PLUGIN_ROOT}}/{CLAUDE_CODE_RULES_RELPATH}"'
    )
    return json.dumps(
        {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": (
                                    f"command -v {binary} >/dev/null 2>&1 || "
                                    f"echo '{absent_notice}'"
                                ),
                            },
                            {
                                "type": "command",
                                "command": rules_inject,
                            },
                        ]
                    }
                ],
                "SessionEnd": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": (
                                    f"command -v {binary} >/dev/null 2>&1 && {refresh_cmd} || "
                                    f"echo '{absent_notice}'"
                                ),
                            }
                        ]
                    }
                ],
            }
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def render_marketplace_manifest(version: str | None = None) -> str:
    """``<repo>/.claude-plugin/marketplace.json`` — 이 저장소가 곧 marketplace.

    `/plugin marketplace add <owner>/<repo>` → `/plugin install <name>@<market>`
    경로를 연다. payload 밖에 있는 이유는 소유 계층이 달라서다 — marketplace 는
    "이 저장소가 무엇을 서빙하는가" 이고, payload 는 "플러그인이 무엇인가" 다.
    """
    return json.dumps(
        {
            "name": PLUGIN_NAME,
            "owner": PLUGIN_AUTHOR,
            "description": (
                f"표준 AI 워크플로우 — 세션 경계 / 백로그 / 문서 동기화 스킬 "
                f"{len(PLUGIN_SKILLS)}종과 read-only MCP 도구를 배포하는 marketplace."
            ),
            "plugins": [
                {
                    "name": PLUGIN_NAME,
                    "source": f"./{PAYLOAD_DIRNAME}",
                    "version": version if version is not None else current_kit_version(),
                    "description": PLUGIN_DESCRIPTION,
                }
            ],
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def render_plugin_skill(spec: PluginSkillSpec, rules: StandardRules) -> str:
    """``plugin/skills/<slug>/SKILL.md`` — agentskills.io 스펙 SKILL.md.

    frontmatter 는 ``name`` / ``description`` 만 쓴다. 본문 끝에는 §11 섹션을
    붙인다 — 메모리 갱신을 지시하면서 방법을 안 알려주면 에이전트가 손으로 쓰고
    파싱 계약이 조용히 깨진다 (TASK-2026-08-11-main-020 전수검사의 결론).
    """
    return (
        "---\n"
        f"name: {spec.slug}\n"
        f"description: {spec.description}\n"
        "---\n"
        "\n"
        f"# {spec.slug}\n"
        "\n"
        f"{spec.body(rules)}\n"
        "\n"
        f"{render_memory_update_section(rules)}\n"
    )


def render_openai_agent_metadata(spec: PluginSkillSpec) -> str:
    """``skills/<slug>/agents/openai.yaml`` — Codex UI metadata.

    Agent Skills는 ``SKILL.md``만으로도 Codex에 로드되지만, 이 메타데이터를 같이
    제공하면 skill list와 invocation chip에 사람이 읽을 이름과 시작 prompt가
    나타난다. 실행 의존성은 ``wk``뿐이며, MCP는 read-only opt-in이므로 여기서
    자동 의존성으로 선언하지 않는다.
    """
    display_name = spec.slug.replace("-", " ").title()
    return (
        "interface:\n"
        f"  display_name: {json.dumps(display_name, ensure_ascii=False)}\n"
        f"  short_description: {json.dumps(spec.description, ensure_ascii=False)}\n"
        f"  default_prompt: {json.dumps(f'Use ${spec.slug} to follow the standard AI workflow.', ensure_ascii=False)}\n"
        "policy:\n"
        "  allow_implicit_invocation: true\n"
    )


def render_agent_plugin(
    rules: StandardRules | None = None,
    *,
    version: str | None = None,
    source_root: Path | None = None,
) -> dict[str, str]:
    """payload 전체를 ``{상대 경로: 내용}`` 으로 돌려준다.

    디스크를 건드리지 않는다 — 쓰기는 :func:`write_agent_plugin`, 대조는 검사가
    한다. 같은 함수가 생성과 검증 양쪽의 정본이라 drift 가 생길 자리가 없다.
    """
    resolved = rules if rules is not None else load_standard_rules(source_root)
    mcp_config = render_plugin_mcp_config()
    payload: dict[str, str] = {
        "plugin.json": render_plugin_manifest(version),
        CODEX_MANIFEST_RELPATH: render_codex_manifest(version),
        "mcp.json": mcp_config,
        # 같은 렌더러의 출력을 두 이름으로 둔다 — 정본이 하나라 갈라지지 않고,
        # 검사 case 가 두 파일의 동일성을 강제한다.
        CLAUDE_CODE_MCP_RELPATH: mcp_config,
        CLAUDE_CODE_MANIFEST_RELPATH: render_claude_code_manifest(version),
        CLAUDE_CODE_HOOKS_RELPATH: render_claude_code_hooks(resolved),
        CLAUDE_CODE_RULES_RELPATH: render_claude_code_rules(resolved),
        GEMINI_MANIFEST_RELPATH: render_gemini_manifest(version),
        GEMINI_CONTEXT_RELPATH: render_gemini_context(resolved),
        GOOSE_SNIPPET_RELPATH: render_goose_config_snippet(),
        OPENCODE_SNIPPET_RELPATH: render_opencode_snippet(),
    }
    for spec in PLUGIN_SKILLS:
        payload[f"skills/{spec.slug}/SKILL.md"] = render_plugin_skill(spec, resolved)
        payload[f"skills/{spec.slug}/agents/openai.yaml"] = render_openai_agent_metadata(spec)
    return payload


def render_repo_plugin_files(
    rules: StandardRules | None = None,
    *,
    version: str | None = None,
    source_root: Path | None = None,
) -> dict[str, str]:
    """payload + marketplace 를 **저장소 루트 기준 상대 경로**로 돌려준다.

    payload 는 `plugin/` 안에 살고 marketplace 는 저장소 루트에 산다 — 소유
    계층이 다르다. 재생성·drift 판정은 둘을 함께 봐야 버전이 갈라지지 않는다.
    """
    files = {
        f"{PAYLOAD_DIRNAME}/{rel}": content
        for rel, content in render_agent_plugin(rules, version=version, source_root=source_root).items()
    }
    files[MARKETPLACE_RELPATH] = render_marketplace_manifest(version)
    return files


# ---------------------------------------------------------------------------
# 쓰기 + CLI
# ---------------------------------------------------------------------------


def default_repo_root() -> Path:
    """저장소 체크아웃 루트 (`workflow-source/workflow_kit/` 의 두 단계 위)."""
    return Path(__file__).resolve().parents[2]


def default_payload_root() -> Path:
    """저장소 체크아웃에서의 기본 payload 경로 (``<repo>/plugin``)."""
    return default_repo_root() / PAYLOAD_DIRNAME


def write_agent_plugin(root: Path, payload: dict[str, str] | None = None) -> list[Path]:
    """payload 를 ``root`` 아래에 쓰고, 쓴 파일 목록을 돌려준다."""
    files = payload if payload is not None else render_agent_plugin()
    written: list[Path] = []
    for relpath, content in sorted(files.items()):
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(target)
    return written


def diff_payload(root: Path, payload: dict[str, str] | None = None) -> list[str]:
    """디스크와 생성물이 어긋난 항목을 사람이 읽을 문장으로 돌려준다."""
    files = payload if payload is not None else render_agent_plugin()
    problems: list[str] = []
    for relpath, content in sorted(files.items()):
        target = root / relpath
        if not target.is_file():
            problems.append(f"없음: {relpath}")
        elif target.read_text(encoding="utf-8") != content:
            problems.append(f"드리프트: {relpath}")
    if root.is_dir():
        expected = {(root / rel).resolve() for rel in files}
        for found in root.rglob("*"):
            if found.is_file() and found.resolve() not in expected:
                problems.append(f"미등록 파일: {found.relative_to(root)}")
    return problems


#: drift 판정 시 "등록되지 않은 파일" 을 찾을 디렉터리 (저장소 루트 기준).
_SCAN_DIRS = (PAYLOAD_DIRNAME, ".claude-plugin")


def write_repo_plugin_files(repo_root: Path, files: dict[str, str] | None = None) -> list[Path]:
    """payload + marketplace 를 저장소 루트 기준으로 쓴다."""
    return write_agent_plugin(repo_root, files if files is not None else render_repo_plugin_files())


def diff_repo_plugin_files(repo_root: Path, files: dict[str, str] | None = None) -> list[str]:
    """저장소의 플러그인 산출물 전체(payload + marketplace)와 생성물을 대조한다."""
    expected_files = files if files is not None else render_repo_plugin_files()
    problems: list[str] = []
    for relpath, content in sorted(expected_files.items()):
        target = repo_root / relpath
        if not target.is_file():
            problems.append(f"없음: {relpath}")
        elif target.read_text(encoding="utf-8") != content:
            problems.append(f"드리프트: {relpath}")
    expected_paths = {(repo_root / rel).resolve() for rel in expected_files}
    for scan in _SCAN_DIRS:
        base = repo_root / scan
        if not base.is_dir():
            continue
        for found in base.rglob("*"):
            if found.is_file() and found.resolve() not in expected_paths:
                problems.append(f"미등록 파일: {found.relative_to(repo_root)}")
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="플러그인 산출물(공유 payload + 어댑터 + marketplace)을 정본에서 생성한다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--apply", action="store_true", help="산출물을 디스크에 다시 생성한다")
    parser.add_argument("--out-dir", type=Path, default=None, help="저장소 루트 (기본: 자동 탐색)")
    args = parser.parse_args(argv)

    root = args.out_dir or default_repo_root()
    payload = render_repo_plugin_files()
    problems = diff_repo_plugin_files(root, payload)

    if not problems:
        print(f"OK: 플러그인 산출물이 정본과 일치한다 ({root})")
        return 0
    if not args.apply:
        for line in problems:
            print(f"  {line}")
        print(f"DRIFT: 산출물이 정본과 다르다. `--apply` 로 재생성한다 ({root})", file=sys.stderr)
        return 1
    for path in write_repo_plugin_files(root, payload):
        print(f"WROTE: {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
