"""Per-harness overlay registry for ``bootstrap_workflow_kit``.

The bootstrap entry script stays the source of truth for the actual file
renderers (kept in the same file for visibility) but delegates the
"which harness produces which file" lookup through this module. New harnesses
only have to register an entry here, an :class:`HarnessSpec` describing the
entry-point files, and one ``write_*_harness_files`` function on the bootstrap
side.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class HarnessSpec:
    """Declarative description of a single harness overlay."""

    name: str
    description: str
    entry_files: tuple[str, ...]
    """Files created at the project root, relative to the target root."""

    extra_files: tuple[str, ...] = ()
    """Optional secondary files (configs, skills, agents)."""

    long_description: str = ""
    """One-paragraph description shown in the kit ``harnesses/`` index."""


#: Canonical list of supported harness identifiers.
#: Keep in sync with ``HARNESS_SPECS`` keys and the ``--harness`` argparse choices.
SUPPORTED_HARNESSES: tuple[str, ...] = (
    "codex",
    "opencode",
    "gemini-cli",
    "pi-dev",
    "antigravity",
    "minimax-code",
    "claude-code",
    "aider",
    "goose",
    "codewhale",
    "custom",
)


#: Declarative metadata for each supported harness. The bootstrap script reads
#: this to decide which files to emit, which docs to copy, and which descriptions
#: to surface in the generated ``harnesses/`` index.
HARNESS_SPECS: dict[str, HarnessSpec] = {
    "codex": HarnessSpec(
        name="codex",
        description="Codex CLI용 overlay. AGENTS.md 진입점과 .codex/config.toml.example 작성.",
        entry_files=("AGENTS.md",),
        extra_files=(".codex/config.toml.example",),
        long_description=(
            "Codex CLI 환경에 표준 AI 워크플로우를 도입할 때 사용하는 오버레이. "
            "루트의 `AGENTS.md` 진입점과 `.codex/config.toml.example` 설정 예시를 함께 생성한다."
        ),
    ),
    "opencode": HarnessSpec(
        name="opencode",
        description="OpenCode용 overlay. AGENTS.md + opencode.json + .opencode/agents, skills 작성.",
        entry_files=("AGENTS.md", "opencode.json"),
        extra_files=(
            ".opencode/skills/standard-ai-workflow/SKILL.md",
            ".opencode/agents/workflow-orchestrator.md",
            ".opencode/agents/workflow-worker.md",
            ".opencode/agents/workflow-doc-worker.md",
            ".opencode/agents/workflow-code-worker.md",
            ".opencode/agents/workflow-validation-worker.md",
        ),
        long_description=(
            "OpenCode CLI 환경용 오버레이. 메인 orchestrator와 doc/code/validation worker "
            "분리 패턴을 함께 적용해 다중 에이전트 토폴로지를 그대로 재현한다."
        ),
    ),
    "gemini-cli": HarnessSpec(
        name="gemini-cli",
        description="Gemini CLI용 overlay. GEMINI.md 진입점 작성.",
        entry_files=("GEMINI.md",),
        long_description=(
            "Gemini CLI 환경에 적합한 단일 진입점 오버레이. 워크플로우 세션 시작/종료와 "
            "백로그 갱신 절차를 한국어 안내와 함께 노출한다."
        ),
    ),
    "pi-dev": HarnessSpec(
        name="pi-dev",
        description="Pi Coding Agent용 overlay. AGENTS.md 진입점 작성 (Codex와 동일 위치).",
        entry_files=("AGENTS.md",),
        long_description=(
            "Pi Coding Agent 환경용 오버레이. Codex와 동일한 `AGENTS.md` 진입점을 사용한다. "
            "동시에 두 하네스를 선택하지 않는 것을 권장한다."
        ),
    ),
    "antigravity": HarnessSpec(
        name="antigravity",
        description="Antigravity용 overlay. ANTIGRAVITY.md 진입점 작성.",
        entry_files=("ANTIGRAVITY.md",),
        long_description=(
            "Antigravity 하네스용 오버레이. 워크플로우 표준 문서와 apply 가이드를 함께 노출한다."
        ),
    ),
    "minimax-code": HarnessSpec(
        name="minimax-code",
        description="MiniMax Code용 overlay. AGENTS.md + MiniMax.md + minimax_config_example.json + orchestrator/worker 분리.",
        entry_files=("AGENTS.md", "MiniMax.md"),
        extra_files=(
            "minimax_config_example.json",
            ".minimax/agents/workflow-orchestrator.md",
            ".minimax/agents/workflow-worker.md",
            ".minimax/agents/workflow-doc-worker.md",
            ".minimax/agents/workflow-code-worker.md",
            ".minimax/agents/workflow-validation-worker.md",
        ),
        long_description=(
            "MiniMax Code(미니맥스 코드) 환경용 오버레이. 메인 orchestrator + doc/code/validation "
            "worker 분화 패턴과 한국어 우선 보고 원칙, 백로그/handoff 자동 동기화 규칙을 "
            "AGENTS.md + MiniMax.md + .minimax/agents/ 구조로 한 번에 적용한다."
        ),
    ),
    "claude-code": HarnessSpec(
        name="claude-code",
        description="Claude Code용 overlay. CLAUDE.md 진입점 (root) + .claude/commands/workflow-{session-start,backlog-update,doc-sync}.md 3개 slash command.",
        entry_files=("CLAUDE.md",),
        extra_files=(
            ".claude/commands/workflow-session-start.md",
            ".claude/commands/workflow-backlog-update.md",
            ".claude/commands/workflow-doc-sync.md",
        ),
        long_description=(
            "Claude Code 환경용 오버레이. CLAUDE.md 를 root 진입점 (자동 read) 으로 emit + "
            ".claude/commands/ 아래 3개 slash command (`/workflow-session-start`, "
            "`/workflow-backlog-update`, `/workflow-doc-sync`) 를 *additive tool* 로 emit. "
            "v0.10.1 의 skill-only 진입 설계 오류 정정 (Claude Code 도 CLAUDE.md 자동 read). "
            "AGENTS.md 를 직접 read 하지는 않으므로, 기존 AGENTS.md 가 있으면 CLAUDE.md 에서 "
            "`@AGENTS.md` import 또는 symlink 으로 통합 가능."
        ),
    ),
    "aider": HarnessSpec(
        name="aider",
        description="Aider용 overlay. CONVENTIONS.md 진입점 (root + .aider/conventions.md 양쪽) + .aider.conf.yml.example.",
        entry_files=("CONVENTIONS.md",),
        extra_files=(
            ".aider/conventions.md",
            ".aider.conf.yml.example",
        ),
        long_description=(
            "Aider 환경용 오버레이. Aider 는 ``--read`` flag 또는 ``.aider.conf.yml`` 의 "
            "``read`` list 에 등록된 파일을 자동 read. CONVENTIONS.md 를 root 와 "
            "``.aider/conventions.md`` 양쪽에 emit (Aider default 동작 + "
            "``.aider.conf.yml`` 명시 read 둘 다 cover). .aider.conf.yml.example 은 "
            "caller 가 ``cp`` 로 실제 ``.aider.conf.yml`` 생성. commit-language: ko."
        ),
    ),
    "goose": HarnessSpec(
        name="goose",
        description="Goose용 overlay. .goose/config.yaml (extension 등록 + entry_points 3종 + read_files).",
        entry_files=(),
        extra_files=(".goose/config.yaml",),
        long_description=(
            "Goose 환경용 오버레이. Goose 는 *extension* 등록 메커니즘. 본 config 는 "
            "표준 AI workflow 의 3 skill (session-start / backlog-update / doc-sync) 을 "
            "Goose 의 entry_points 로 등록 + read_files (5종) 명시. on_session_end hook 으로 "
            "handoff 자동 갱신 (session-start skill 의 update-handoff flag). language: ko."
        ),
    ),
    "codewhale": HarnessSpec(
        name="codewhale",
        description="CodeWhale용 overlay. .codewhale/skills/codewhale-workflow/SKILL.md 진입점 (Constitution 보강).",
        entry_files=(),
        extra_files=(".codewhale/skills/codewhale-workflow/SKILL.md",),
        long_description=(
            "CodeWhale 환경용 오버레이. CodeWhale의 Constitution 은 이미 검증/병렬화/컨텍스트 관리 "
            "규칙을 내장하므로, 워크플로우 고유 가치(세션 시작 순서, 한국어 보고, 백로그/handoff 관리, "
            "프로젝트 프로파일 기반 탐색)만 얇은 skill 패키지로 주입한다. "
            "Constitution 과 충돌하지 않는 additive rule 만 포함."
        ),
    ),
    "custom": HarnessSpec(
        name="custom",
        description="Custom adapter. .workflow-kits/custom/SKILL.md (caller 가 자사 harness 에 wire-up).",
        entry_files=(),
        extra_files=(".workflow-kits/custom/SKILL.md",),
        long_description=(
            "Custom adapter (v0.10.2+). *특정 하네스에 종속되지 않는* 중립 진입점. "
            "caller 가 자사 internal harness / IDE / CLI 에 맞게 wire-up. 본 파일은 "
            "reference template 일 뿐, 특정 도구에 자동 load 안 됨. self-bootstrap mode "
            "(PURPOSE.md / state.json 부재 시 init light) 의 *neutral contract*."
        ),
    ),
}


def harness_names() -> tuple[str, ...]:
    """Return the tuple of supported harness names (mirrors :data:`SUPPORTED_HARNESSES`)."""
    return SUPPORTED_HARNESSES


def spec_for(name: str) -> HarnessSpec:
    """Return the :class:`HarnessSpec` for ``name`` or raise :class:`KeyError`."""
    return HARNESS_SPECS[name]


__all__ = [
    "HARNESS_SPECS",
    "HARNESS_FILE_BUILDERS",
    "HarnessSpec",
    "SUPPORTED_HARNESSES",
    "harness_names",
    "spec_for",
]


#: Type alias for the ``write_*_harness_files`` callables. Each builder is
#: defined in :mod:`bootstrap_workflow_kit` and registered at import time
#: below. Keeping the dict at module scope makes the dispatcher easy to extend
#: without touching ``write_harness_files``.
HARNESS_FILE_BUILDERS: dict[str, Callable[..., dict[str, str]]] = {}


def register_harness_builder(name: str, builder: Callable[..., dict[str, str]]) -> None:
    """Register a ``write_*_harness_files`` implementation under ``name``."""
    if name not in HARNESS_SPECS:
        raise KeyError(f"Unknown harness: {name}")
    HARNESS_FILE_BUILDERS[name] = builder
