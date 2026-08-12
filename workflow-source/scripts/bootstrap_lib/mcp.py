"""MCP config renderers for the generated kit.

The bootstrap script can optionally emit per-harness MCP config
snippets (``--enable-mcp``). Each harness has its own config dialect
(TOML for Codex, JSON for the rest), so the renderers live in their
own module and are dispatched through :data:`MCP_CONFIG_RENDERERS`.

Adding a new harness only requires:

1. Writing a ``render_<harness>_mcp_config(args, paths) -> str`` function
2. Adding an entry to :data:`MCP_CONFIG_RENDERERS`
3. Adding a branch in :func:`write_mcp_config_files` that picks the right
   output path

mavis 는 예외: project-local 산출물 0. *호스트 글로벌* ``~/.minimax/mcp/mcp.json``
에 atomic merge 만 한다 (§6.5.2). 따라서 :func:`write_mavis_global_mcp_files`
가 그 일을 들고, :func:`write_mcp_config_files` 의 mavis 분기는 호출하지
*않고* dispatch 가 별도 진입으로 호출된다.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from bootstrap_lib.paths import Paths
from bootstrap_lib.writes import write_text


MCP_SERVER_ALIAS = "standardAiWorkflowReadOnly"
MCP_TOOL_NAME = "workflow_kit.read_only"
MCP_TOOL_DESCRIPTION = (
    "Read-only MCP tools (latest_backlog, check_doc_metadata, ...) "
    "for the Standard AI Workflow kit."
)

#: bridge → **구현 단계** (transport_phase 축). 이 값은 "무엇으로 구현됐는가" 만
#: 말한다 — 쓸 수 있는가(정책)도, SDK 를 import 할 수 있는가(런타임 능력)도 아니다.
MCP_BRIDGE_PHASE: dict[str, str] = {
    "jsonrpc-bridge": "jsonrpc_draft",
    "stdio-sdk": "official_sdk",
}

#: bridge → **정책** (apply_mode 축). "사용자가 활성 설정으로 붙여도 되는가".
#:
#: 승격 기준은 `core/read_only_mcp_transport_promotion.md` §6 이고,
#: `tests/check_mcp_apply_mode_criterion.py` 가 그것을 실행한다. 여기 `active_ok`
#: 를 적으면 그 검사가 **실제로 서버를 띄워** 증명을 요구한다 — 선언만으로는
#: 통과하지 못한다.
#:
#: `stdio-sdk` 가 `manual_review_only` 인 이유는 성숙도가 아니라 **의존성** 이다:
#: emit 되는 command 는 `python3`(하네스가 보는 인터프리터)인데 거기에 `mcp` SDK 가
#: 없으면 `Connection closed` 로 죽는다. `mcp` extra 가 보장된 환경에서만 쓸 것.
MCP_BRIDGE_APPLY_MODE: dict[str, str] = {
    "jsonrpc-bridge": "active_ok",
    "stdio-sdk": "manual_review_only",
}

#: harness → JSON 설정 파일의 **최상위 키**. 하네스마다 방언이 다르다.
#:
#: 이 표가 없던 동안 `scripts/generate_read_only_harness_mcp_examples.py` 의 OpenCode
#: 예시가 `mcp_servers` 를 가르치고 있었다 — 실제 `render_opencode_mcp_config` 이
#: 내보내는 키는 `mcp` 다. 예시대로 붙여넣으면 OpenCode 가 서버를 못 본다.
#: 방언을 아는 자리를 하나로 둔다 (2026-08-05).
MCP_CONFIG_ROOT_KEY: dict[str, str] = {
    "opencode": "mcp",
    "gemini-cli": "mcpServers",
    "antigravity": "mcpServers",
    "claude-code": "mcpServers",
    "minimax-code": "mcp_servers",
}


def mcp_server_command(bridge: str) -> list[str]:
    """Return the ``command + args`` that the per-harness MCP config should spawn.

    ``command`` is always ``python3`` (the same Python that runs the
    bootstrap script) and ``args`` points at the entry point module so the
    harness can launch it without a shell. ``PYTHONPATH`` is set in
    ``env`` so the entry point can locate ``workflow_kit``.
    """
    if bridge == "stdio-sdk":
        return ["python3", "-m", "workflow_kit.server.read_only_mcp_sdk", "--stdio-sdk"]
    return ["python3", "-m", "workflow_kit.server.read_only_jsonrpc", "--stdio-lines"]


def _mcp_server_env() -> dict[str, str]:
    """Return the per-harness MCP server ``env`` block.

    ``STANDARD_AI_WORKFLOW_ROOT`` lets the server locate the kit root.
    Every file :func:`write_mcp_config_files` emits is **project-local**
    (it lives under ``target_root`` and, for Claude Code's ``.mcp.json``,
    is checked into the repository). So the value is ``"."``, not an
    absolute path: an absolute path bakes one machine's checkout location
    into a shared file and is wrong in every other clone.

    이 블록은 이미 cwd = target_root 를 전제하고 있었다 — ``PYTHONPATH`` 가
    상대 경로 ``"workflow-source"`` 다. ROOT 만 절대였던 것은 두 값이 서로
    어긋나 있었다는 뜻이고, 절대 경로 쪽이 *기계 고유값* 이라 틀린 쪽이었다.
    글로벌 설정(``~/.claude.json`` 등)에 손으로 심을 때는 절대 경로를 쓴다 —
    거기서는 cwd 전제가 성립하지 않는다 (``core/mcp_installation_by_harness.md`` §2).

    ``PYTHONPATH`` is only set when the bootstrap itself is running
    from a source repo checkout (SOURCE_ROOT is available). In a wheel
    install the server should resolve ``workflow_kit`` from the wheel's
    site-packages, so the bootstrap does NOT preprend
    ``workflow-source`` — that path would otherwise shadow the installed
    wheel and break protocolVersion / smart-update fixes.
    """
    from bootstrap_lib import __main__ as _bm  # local import to avoid cycle

    env = {"STANDARD_AI_WORKFLOW_ROOT": "."}
    if _bm.SOURCE_ROOT is not None:
        env["PYTHONPATH"] = "workflow-source"
    return env


def render_mcp_toml_block(
    bridge: str,
    env: dict[str, str],
    *,
    settings: dict[str, object] | None = None,
    descriptions_comment: str | None = None,
    commented: bool = False,
) -> str:
    """Return the ``[mcp_servers.<alias>]`` TOML block.

    Codex 와 Grok Build 는 **같은 TOML 방언**을 쓴다. 전에는 Codex 쪽만 이 모듈의
    `mcp_server_command` 를 쓰고, Grok 쪽은 `renderers.py` 안에 command/args/alias/
    tool 설명을 **손으로 적어** 두고 있었다 (활성 블록 1 + 주석 처리된 stdio-sdk
    변형 1, 2026-08-05). 사본은 반드시 갈라진다 — transport 기본값이나 entry-point
    모듈명이 바뀌면 Grok 만 옛 값을 계속 내보낸다. 조립을 여기 한 곳에 둔다.

    ``env`` 는 caller 가 준다. project-local config 는 :func:`_mcp_server_env`
    (상대 경로)이고, Grok 의 ``config.toml.example`` 은 사용자가 cp 후 고치는
    템플릿이라 ``/ABSOLUTE/PATH/TO/...`` placeholder 를 쓴다 — 값은 다르지만
    **무엇을 실행하는가는 같아야 한다.**

    ``commented=True`` 면 모든 줄을 ``# `` 로 접두해 "대안 설정" 주석 블록이 된다.
    """
    cmd = mcp_server_command(bridge)
    lines = [
        f"[mcp_servers.{MCP_SERVER_ALIAS}]",
        f"command = {json.dumps(cmd[0])}",
        "args = [" + ", ".join(json.dumps(part) for part in cmd[1:]) + "]",
    ]
    lines += [f"{key} = {json.dumps(value)}" for key, value in env.items()]
    lines += [f"{key} = {json.dumps(value)}" for key, value in (settings or {}).items()]
    lines.append("")
    if descriptions_comment:
        lines.append(f"# {descriptions_comment}")
    lines += [
        f"[mcp_servers.{MCP_SERVER_ALIAS}.tool_descriptions]",
        # 키를 **따옴표로 감싼다**. `workflow_kit.read_only` 를 그냥 쓰면 TOML 의
        # dotted key 규칙에 따라 `{{workflow_kit = {{read_only = "…"}}}}` 로 중첩된다 —
        # 즉 코드가 쓴 키(`MCP_TOOL_NAME`)와 파일이 뜻하는 키가 달라진다. 조립을
        # 여기로 접기 전까지는 아무도 산출물을 파싱해 본 적이 없어서 보이지 않았다
        # (Codex·Grok 양쪽 동일, 2026-08-05).
        f"{json.dumps(MCP_TOOL_NAME)} = {json.dumps(MCP_TOOL_DESCRIPTION)}",
    ]
    if commented:
        lines = [("# " + line).rstrip() for line in lines]
    return "\n".join(lines) + "\n"


def render_codex_mcp_config(args: argparse.Namespace, paths: Paths) -> str:
    """Return a Codex ``.codex/config.toml`` snippet that registers the MCP server.

    Codex accepts TOML with ``[mcp_servers.<alias>]`` sections. We keep
    this as a *snippet* (not a full config) so users can paste it into
    their existing ``~/.codex/config.toml`` without losing other entries.
    """
    bridge = getattr(args, "mcp_bridge", "jsonrpc-bridge")
    block = render_mcp_toml_block(
        bridge,
        _mcp_server_env(),
        settings={"startup_timeout_sec": 15, "tool_timeout_sec": 30},
        descriptions_comment="Tool description shown in the Codex tool picker",
    )
    return f"""# Codex MCP server snippet for the Standard AI Workflow kit.
# Drop this into ~/.codex/config.toml under the [mcp_servers] table, or keep
# the bootstrap-generated .codex/config.toml.example as a starting point.

{block}"""


def render_opencode_mcp_config(args: argparse.Namespace, paths: Paths) -> str:
    """Return an OpenCode MCP config block to embed in ``opencode.json``.

    OpenCode expects ``"mcp": { "<name>": { ... } }`` at the top level. The
    bootstrap writes a standalone ``mcp.opencode.json`` that can be merged
    or symlinked into the project ``opencode.json``.
    """
    bridge = getattr(args, "mcp_bridge", "jsonrpc-bridge")
    return json.dumps(
        {
            MCP_CONFIG_ROOT_KEY["opencode"]: {
                MCP_SERVER_ALIAS: {
                    "type": "local",
                    "command": mcp_server_command(bridge)[0],
                    "args": mcp_server_command(bridge)[1:],
                    "env": _mcp_server_env(),
                    "timeout": 30000,
                }
            }
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def render_gemini_cli_mcp_config(args: argparse.Namespace, paths: Paths) -> str:
    """Return a Gemini CLI ``.gemini/settings.json`` snippet."""
    bridge = getattr(args, "mcp_bridge", "jsonrpc-bridge")
    return json.dumps(
        {
            MCP_CONFIG_ROOT_KEY["gemini-cli"]: {
                MCP_SERVER_ALIAS: {
                    "command": mcp_server_command(bridge)[0],
                    "args": mcp_server_command(bridge)[1:],
                    "env": _mcp_server_env(),
                    "trust": True,
                    "includeTools": [
                        "latest_backlog",
                        "check_doc_metadata",
                        "check_doc_links",
                        "suggest_impacted_docs",
                    ],
                }
            }
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def render_antigravity_mcp_config(args: argparse.Namespace, paths: Paths) -> str:
    """Return an Antigravity MCP snippet.

    Antigravity shares the JSON ``mcpServers`` shape with Gemini CLI. The
    bootstrap writes the file as ``.antigravity/mcp.json`` (project-local),
    following the same dot-dir convention as ``.codex/``, ``.gemini/``,
    and ``.MiniMax/``.
    """
    bridge = getattr(args, "mcp_bridge", "jsonrpc-bridge")
    return json.dumps(
        {
            MCP_CONFIG_ROOT_KEY["antigravity"]: {
                MCP_SERVER_ALIAS: {
                    "type": "stdio",
                    "command": mcp_server_command(bridge)[0],
                    "args": mcp_server_command(bridge)[1:],
                    "env": _mcp_server_env(),
                }
            }
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def _read_only_tool_names() -> list[str]:
    """MCP config 에 싣는 도구 이름 목록 — registry 가 정본이다.

    `workflow_kit.server.read_only_registry.READ_ONLY_TOOL_SPECS` 에서 파생한다.
    렌더러가 이름을 직접 나열하면 registry 확장 시 그 사본만 낡는다
    (실측: 13개 중 10개에서 멈춰 있었다 — TASK-2026-08-11-main-025).
    """
    from workflow_kit.server.read_only_registry import READ_ONLY_TOOL_SPECS

    return [spec.name for spec in READ_ONLY_TOOL_SPECS]


def render_minimax_code_mcp_config(args: argparse.Namespace, paths: Paths) -> str:
    """Return a MiniMax Code ``.MiniMax/mcp.json`` config.

    The bootstrap writes the file as ``.MiniMax/mcp.json`` (project-local).
    Users can symlink it into their ``~/.MiniMax/mcp.json`` or copy the
    ``mcp_servers`` block into the global config.
    """
    bridge = getattr(args, "mcp_bridge", "jsonrpc-bridge")
    descriptor = {
        MCP_SERVER_ALIAS: {
            "command": mcp_server_command(bridge)[0],
            "args": mcp_server_command(bridge)[1:],
            "env": _mcp_server_env(),
            "transport": bridge,
            "transport_phase": MCP_BRIDGE_PHASE[bridge],
            "apply_mode": MCP_BRIDGE_APPLY_MODE[bridge],
            "description": (
                "Read-only MCP tools for the Standard AI Workflow kit. "
                "Draft JSON-RPC bridge by default; switch to stdio-sdk once "
                "check_read_only_mcp_sdk_stdio.py is green."
            ),
            # v1.1.7 (TASK-2026-08-11-main-025): 도구 목록은 registry 가 정본이다.
            # 손 목록은 10개에서 멈춰 있었고 (rotate_workflow_logs /
            # assess_milestone_progress / apply_robust_patch 누락) 아무 검사도
            # 그 어긋남을 보지 않았다 — 요구 목록은 파생시킨다.
            "tools": _read_only_tool_names(),
        }
    }
    return json.dumps({MCP_CONFIG_ROOT_KEY["minimax-code"]: descriptor}, ensure_ascii=False, indent=2) + "\n"


#: mavis 데스크탑 글로벌 mcp.json 의 고정 경로. mavis 공식 user-guide 기준
#: (*"MCP servers live in {{DATA_DIR}}/mcp.json"*) — DATA_DIR = ~/.minimax. 본
#: harness 는 workspace 단위 자동 로드 ❌ 라서 *project-local* 사본을 emit 하지
#: 않고 이 한 곳만 merge 한다. CLI 옵션 ``--mavis-global-mcp-path`` 로 테스트
#: 격리가 가능 (실 사용 시 default 고정).
DEFAULT_MAVIS_GLOBAL_MCP_PATH: Path = Path.home() / ".minimax" / "mcp" / "mcp.json"


def render_mavis_global_mcp_config(args: argparse.Namespace) -> dict:
    """Return mavis 데스크탑 merge 의 **block** (dict).

    정본 §6.5.2 형식. `args.mcp_bridge` 에 따라 같은 bridge 표를 따른다.
    절대 경로 env 두 개 모두 박혀야 한다 — mavis 가 띄울 때 cwd 가 *프로젝트
    루트가 아니라* 데스크탑 런타임 자리라, 상대 경로면 `ModuleNotFoundError` 로
    *조용히* 죽는다 (§1.2.1).
    """
    bridge = getattr(args, "mcp_bridge", "jsonrpc-bridge")
    target_root = Path(getattr(args, "target_root", ".")).resolve()
    pythonpath = (target_root / "workflow-source").resolve()
    return {
        MCP_SERVER_ALIAS: {
            "command": mcp_server_command(bridge)[0],
            "args": mcp_server_command(bridge)[1:],
            "env": {
                "STANDARD_AI_WORKFLOW_ROOT": str(target_root),
                "PYTHONPATH": str(pythonpath),
            },
            "enabled": True,
            "configured": True,
        }
    }


def atomic_merge_mavis_global(
    target_path: Path,
    new_block: dict,
    *,
    force: bool = False,
) -> dict:
    """``~/.minimax/mcp/mcp.json`` 을 atomic merge 한다 (§6.5.2).

    동작:
      1. ``target_path`` 가 없으면 *신규* 작성 (backup 없음 — 부재 시).
      2. 있으면 ``<path>.bak.<UTC-iso>`` 로 backup (기존 권한/소유권 보존).
      3. ``mcpServers`` key 아래 ``new_block`` 을 merge. 동일 alias 가 이미
         있으면 ``force=True`` 일 때만 덮어쓴다 (default = keep).
      4. tmp 파일을 *같은 dir* 에 만들고 ``os.replace`` 로 atomic write.

    Returns:
        ``{"backup": Path | None, "merged": Path, "wrote": bool, "skipped": bool}``
    """
    result = {"backup": None, "merged": target_path, "wrote": False, "skipped": False}

    if target_path.is_file():
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = target_path.with_suffix(f".json.bak.{ts}")
        shutil.copy2(target_path, backup)
        result["backup"] = backup
        raw = target_path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise SystemExit(
                f"existing mavis mcp.json broken at {target_path}: {e}"
            )
        if not isinstance(data, dict):
            raise SystemExit(
                f"existing mavis mcp.json top-level not dict: {target_path}"
            )
        servers = data.get("mcpServers")
        if not isinstance(servers, dict):
            servers = {}
            data["mcpServers"] = servers
    else:
        # 신규 파일 — directory 확보 + 새 dict 시작.
        target_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"mcpServers": {}}
        servers = data["mcpServers"]

    alias = MCP_SERVER_ALIAS
    if alias in servers and not force:
        # default: keep — 사용자 mimic → init 시 그대로 두는 게 기대.
        result["skipped"] = True
        return result

    servers.update(new_block)

    # atomic write — tmp + os.replace. 같은 dir.
    fd, tmp_name = tempfile.mkstemp(prefix=".mcp.", suffix=".tmp", dir=str(target_path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
            fp.write("\n")
        # 권한은 기존 파일이 있으면 그것을, 없으면 0o600.
        if target_path.is_file():
            os.chmod(tmp_name, target_path.stat().st_mode)
        else:
            os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, target_path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise

    result["wrote"] = True
    return result


def write_mavis_global_mcp_files(
    args: argparse.Namespace,
    *,
    target_path: Path | None = None,
) -> dict:
    """``--harness mavis`` + ``--enable-mcp`` 의 실제 emit 진입.

    ``write_mcp_config_files`` 와는 *별도* — project-local 산출물 0 이라
    dispatch 표에서 *호출되지 않는다*. 메인 bootstrap CLI 가 직접 이 함수를
    호출한다.

    Args:
        args: argparse namespace. ``args.target_root`` / ``args.mcp_bridge`` 사용.
        target_path: 테스트 / 명시 override 용. None 이면
            :data:`DEFAULT_MAVIS_GLOBAL_MCP_PATH`.

    Returns:
        :func:`atomic_merge_mavis_global` 의 dict + ``alias`` / ``path`` key.
    """
    actual_target = Path(target_path) if target_path is not None else DEFAULT_MAVIS_GLOBAL_MCP_PATH
    block = render_mavis_global_mcp_config(args)
    out = atomic_merge_mavis_global(actual_target, block, force=getattr(args, "force", False))
    out["alias"] = MCP_SERVER_ALIAS
    out["path"] = str(actual_target)
    return out


def render_claude_code_mcp_config(args: argparse.Namespace, paths: Paths) -> str:
    """Return a Claude Code ``.mcp.json`` (project-scoped MCP server registration).

    Claude Code reads ``<root>/.mcp.json`` with the JSON ``mcpServers`` shape,
    the same dialect as Gemini CLI / Antigravity. ``core/mcp_installation_by_harness.md``
    §4 has listed this row from the start, but **no renderer produced it** — the
    table declared a delivery that did not exist (2026-08-05).

    **transport 는 `args.mcp_bridge` 를 그대로 따른다** (default ``jsonrpc-bridge``).
    특별대우하지 않는 이유는 실측이다: emit 되는 ``command`` 는 `python3` 즉
    **시스템 python3** 인데, `stdio-sdk` 는 거기에 `mcp` SDK 가 있어야 뜬다. 이 저장소
    에서 재 보니 시스템 python3 로 `stdio-sdk` 는 `Connection closed` 로 죽고
    `jsonrpc-bridge` 는 공식 MCP 클라이언트와 initialize / tools/list / tools/call
    왕복이 정상이었다. 이름과 달리 두 transport 모두 MCP 프로토콜을 말하며, 의존성이
    적은 default 가 더 넓게 뜬다. SDK 가 있는 환경은 ``--mcp-bridge stdio-sdk`` 로 전환.
    """
    bridge = getattr(args, "mcp_bridge", "jsonrpc-bridge")
    return json.dumps(
        {
            MCP_CONFIG_ROOT_KEY["claude-code"]: {
                MCP_SERVER_ALIAS: {
                    "type": "stdio",
                    "command": mcp_server_command(bridge)[0],
                    "args": mcp_server_command(bridge)[1:],
                    "env": _mcp_server_env(),
                }
            }
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def write_mcp_config_files(
    args: argparse.Namespace,
    paths: Paths,
    harnesses: list[str],
) -> dict[str, str]:
    """Emit per-harness MCP config snippets when ``--enable-mcp`` is set."""
    generated: dict[str, str] = {}

    if "codex" in harnesses or "opencode" in harnesses:
        codex_path = paths.target_root / ".codex" / "mcp.toml"
        write_text(codex_path, render_codex_mcp_config(args, paths), force=args.force, rel_to=paths.target_root)
        generated["codex_mcp_config"] = str(codex_path)

    if "opencode" in harnesses:
        opencode_path = paths.target_root / "mcp.opencode.json"
        write_text(opencode_path, render_opencode_mcp_config(args, paths), force=args.force, rel_to=paths.target_root)
        generated["opencode_mcp_config"] = str(opencode_path)

    if "gemini-cli" in harnesses:
        gemini_path = paths.target_root / ".gemini" / "mcp.json"
        write_text(gemini_path, render_gemini_cli_mcp_config(args, paths), force=args.force, rel_to=paths.target_root)
        generated["gemini_cli_mcp_config"] = str(gemini_path)

    if "antigravity" in harnesses:
        antigravity_path = paths.target_root / ".antigravity" / "mcp.json"
        write_text(antigravity_path, render_antigravity_mcp_config(args, paths), force=args.force, rel_to=paths.target_root)
        generated["antigravity_mcp_config"] = str(antigravity_path)

    if "minimax-code" in harnesses:
        minimax_path = paths.target_root / ".MiniMax" / "mcp.json"
        write_text(minimax_path, render_minimax_code_mcp_config(args, paths), force=args.force, rel_to=paths.target_root)
        generated["minimax_code_mcp_config"] = str(minimax_path)

    # mavis 는 *project-local* 산출물 0. 글로벌 mcp.json merge 는
    # write_mavis_global_mcp_files (별도 진입) 가 맡는다. 호출은 bootstrap CLI 의
    # 메인 함수에서 --harness mavis && --enable-mcp 시점에 한다.

    if "claude-code" in harnesses:
        claude_path = paths.target_root / ".mcp.json"
        write_text(claude_path, render_claude_code_mcp_config(args, paths), force=args.force, rel_to=paths.target_root)
        generated["claude_code_mcp_config"] = str(claude_path)

    return generated


#: Dispatch table from harness name to its MCP config renderer.
#: Adding a new harness only requires an entry here and a branch in
#: :func:`write_mcp_config_files`.
MCP_CONFIG_RENDERERS: dict[str, Callable[[argparse.Namespace, Paths], str]] = {
    "codex": render_codex_mcp_config,
    "opencode": render_opencode_mcp_config,
    "gemini-cli": render_gemini_cli_mcp_config,
    "antigravity": render_antigravity_mcp_config,
    "minimax-code": render_minimax_code_mcp_config,
    "claude-code": render_claude_code_mcp_config,
    # mavis 는 글로벌 mcp.json merge 만 하는 별도 진입이라 dispatch 표에
    # str-returning 렌더러를 두지 않는다. (project-local 산출물 0.)
}


__all__ = [
    "MCP_CONFIG_RENDERERS",
    "MCP_SERVER_ALIAS",
    "MCP_TOOL_NAME",
    "MCP_TOOL_DESCRIPTION",
    "DEFAULT_MAVIS_GLOBAL_MCP_PATH",
    "render_antigravity_mcp_config",
    "render_claude_code_mcp_config",
    "render_codex_mcp_config",
    "render_gemini_cli_mcp_config",
    "render_minimax_code_mcp_config",
    "render_opencode_mcp_config",
    "render_mavis_global_mcp_config",
    "atomic_merge_mavis_global",
    "write_mavis_global_mcp_files",
    "write_mcp_config_files",
]
