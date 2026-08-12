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
├── skills/
│   ├── session-start/SKILL.md   # §11 명령·계약은 render_memory_update_section 파생
│   ├── backlog-update/SKILL.md  # 상태값 4종은 rules.task_states 파생
│   └── doc-sync/SKILL.md
└── mcp.json                     # MCP mcpServers 스키마, read-only bundle
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

from workflow_kit import __version__ as KIT_VERSION
from workflow_kit.common.standard_rules import (
    StandardRules,
    find_memory_command,
    load_standard_rules,
    render_memory_update_section,
)

__all__ = [
    "PAYLOAD_DIRNAME",
    "PLUGIN_NAME",
    "PLUGIN_DESCRIPTION",
    "PLUGIN_SKILLS",
    "PluginSkillSpec",
    "default_payload_root",
    "render_agent_plugin",
    "render_plugin_manifest",
    "render_plugin_mcp_config",
    "render_plugin_skill",
    "write_agent_plugin",
]

#: payload 디렉터리 이름 (저장소 루트 기준). 어댑터(P2~P3)는 이 경로를 참조만 한다.
PAYLOAD_DIRNAME = "plugin"

#: 플러그인 식별자. Claude Code 는 스킬을 ``/<plugin-name>:<skill-name>`` 으로
#: 네임스페이스 하므로, bootstrap 이 심는 동명 스킬과 충돌하지 않는다 (계획 §5).
PLUGIN_NAME = "standard-ai-workflow"

PLUGIN_DESCRIPTION = (
    "세션 시작 / 백로그 갱신 / 문서 동기화를 표준 AI 워크플로우 절차로 수행하는 "
    "스킬 3종과 read-only MCP 도구 번들."
)

#: MCP 서버 등록에 쓰는 bundle 선택자. write bundle 은 payload 에 싣지 않는다.
PAYLOAD_MCP_BUNDLE = "read-only"

#: payload 가 전제하는 MCP bridge. jsonrpc-bridge 는 `mcp` SDK 없이도 뜬다
#: (`MCP_BRIDGE_APPLY_MODE` 가 유일하게 ``active_ok`` 로 선언한 transport).
PAYLOAD_MCP_BRIDGE = "jsonrpc-bridge"


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


#: payload 가 싣는 스킬 3종. slug 는 소문자·하이픈만 (Agent Skills 이름 규칙).
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
)


# ---------------------------------------------------------------------------
# 렌더러
# ---------------------------------------------------------------------------


def render_plugin_manifest(version: str = KIT_VERSION) -> str:
    """``plugin/plugin.json`` — Agent Plugins 1.0 manifest.

    필드는 계획 §3-P1 이 명시한 3개뿐이다. 스펙 원문으로 확인하지 못한 선택 필드는
    넣지 않는다 — 지어낸 필드는 스펙 확정 시 조용히 틀린 값이 된다.
    """
    return json.dumps(
        {
            "name": PLUGIN_NAME,
            "version": version,
            "description": PLUGIN_DESCRIPTION,
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


def render_agent_plugin(
    rules: StandardRules | None = None,
    *,
    version: str = KIT_VERSION,
    source_root: Path | None = None,
) -> dict[str, str]:
    """payload 전체를 ``{상대 경로: 내용}`` 으로 돌려준다.

    디스크를 건드리지 않는다 — 쓰기는 :func:`write_agent_plugin`, 대조는 검사가
    한다. 같은 함수가 생성과 검증 양쪽의 정본이라 drift 가 생길 자리가 없다.
    """
    resolved = rules if rules is not None else load_standard_rules(source_root)
    payload: dict[str, str] = {
        "plugin.json": render_plugin_manifest(version),
        "mcp.json": render_plugin_mcp_config(),
    }
    for spec in PLUGIN_SKILLS:
        payload[f"skills/{spec.slug}/SKILL.md"] = render_plugin_skill(spec, resolved)
    return payload


# ---------------------------------------------------------------------------
# 쓰기 + CLI
# ---------------------------------------------------------------------------


def default_payload_root() -> Path:
    """저장소 체크아웃에서의 기본 출력 경로 (``<repo>/plugin``)."""
    return Path(__file__).resolve().parents[2] / PAYLOAD_DIRNAME


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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Agent Plugins 1.0 공유 payload 를 정본에서 생성한다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--apply", action="store_true", help="payload 를 디스크에 다시 생성한다")
    parser.add_argument("--out-dir", type=Path, default=None, help="출력 루트 (기본: <repo>/plugin)")
    args = parser.parse_args(argv)

    root = args.out_dir or default_payload_root()
    payload = render_agent_plugin()
    problems = diff_payload(root, payload)

    if not problems:
        print(f"OK: payload 가 정본과 일치한다 ({root})")
        return 0
    if not args.apply:
        for line in problems:
            print(f"  {line}")
        print(f"DRIFT: payload 가 정본과 다르다. `--apply` 로 재생성한다 ({root})", file=sys.stderr)
        return 1
    for path in write_agent_plugin(root, payload):
        print(f"WROTE: {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
