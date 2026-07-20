# Grok Build Harness Package

- 문서 목적: 표준 AI 워크플로우를 Grok Build (xAI CLI TUI) 하네스에 맞춰 배포할 때 생성되는 파일과 검토 포인트를 정리한다.
- 범위: `AGENTS.md` (root 진입점, Codex 와 공통), `GROK.md` (Grok Build 전용 진입점), `.grok/skills/standard-ai-workflow/SKILL.md` (TUI picker 표시), `.grok/config.toml.example` (MCP snippet + skill paths + memory opt-in)
- 대상 독자: Grok Build 사용자, 저장소 관리자, AI workflow 설계자
- 상태: beta
- 최종 수정일: 2026-07-20
- 관련 문서: `../../core/workflow_harness_distribution.md`, `../../core/mcp_installation_by_harness.md`, `../../scripts/bootstrap_workflow_kit.py`

## 1. 진입점 특성

Grok Build 의 project 진입점 메커니즘은 두 가지 root 진입점 + `.grok/` 디렉터리 통합이다.

| 진입점 | 자동 read | scope | 비고 |
|---|---|---|---|
| `AGENTS.md` (project root) | ✅ 매 세션 | project | **Codex 와 공통 root 진입점** |
| `~/.grok/AGENTS.md` | ✅ | user | user-level instructions |
| `GROK.md` (project root) | ✅ 매 세션 | project | **Grok Build 전용 진입점** (본 하네스가 emit) |
| `.grok/config.toml` | ✅ 매 세션 | project | MCP / plugin / permission (예시 emit) |
| `~/.grok/config.toml` | ✅ | user | 전역 설정 |
| `.grok/skills/` | ✅ | project | project skill 정의 (TUI picker 표시) |
| `.grok/agents/` | ✅ | project | agent 정의 (custom subagent) |
| `.grok/hooks/` | ✅ | project | lifecycle hooks |
| `.grok/memory/` | ✅ (opt-in) | cross-session | `--experimental-memory` 또는 `GROK_MEMORY=1` |

→ `AGENTS.md` 는 Codex 와 동일 본문 (한국어 baseline + worker 운영 원칙). `GROK.md` 는 **Grok Build 전용 additive rule** (subagent 활용 + MCP 등록 + memory opt-in + skill 등록) — Claude Code 의 `CLAUDE.md` 와 같은 *root 진입점* 역할.

## 2. 생성 대상

bootstrap 시 다음 4개 파일이 emit 된다.

- 프로젝트 루트 `AGENTS.md` (Codex render 재사용, Codex 와 동시 사용 시 동일 본문)
- 프로젝트 루트 `GROK.md` (Grok Build 전용 진입점, 한국어 baseline + subagent 패턴)
- `.grok/skills/standard-ai-workflow/SKILL.md` (TUI picker 표시, frontmatter 5 field 정공법)
- `.grok/config.toml.example` (MCP stdio snippet + `[skills] paths` + `[memory]` opt-in)

## 3. 구성 원칙

- `AGENTS.md` 는 Codex 와 공통 진입점. `main`/`small` 모델 구조 + 한국어 보고 + worker 분리 원칙을 Codex 와 정합.
- `GROK.md` 는 Grok Build 가 자동 read 하는 *Grok Build 전용* 진입점. Codex 와 동시 사용 시 *additive rule* 로 동작 (정책 중복 ❌).
- `.grok/config.toml.example` 는 caller 가 `cp .grok/config.toml.example .grok/config.toml` 로 실제 설정 파일 생성. 절대 경로 보정 필수.
- `--enable-mcp` 시 `.grok/config.toml` 의 `[mcp_servers.standardAiWorkflowReadOnly]` 블록이 자동 emit 됨.
- Grok Build 는 Claude Code (`.claude.json`) / Cursor (`.cursor/mcp.json`) / `.mcp.json` 호환성이 있으므로 기존 workflow MCP 등록을 자동 import 가능 (단, Codex 와 동시 사용 시 MCP alias 충돌 주의).
- 본 하네스는 orchestrator / worker 분리 패턴을 강제하지 않는다. Grok Build 의 내장 subagent (`explore` / `plan`) 와 custom agent (`.grok/agents/`) 로 bounded scope 분리.

## 4. AGENTS.md 와 GROK.md 의 역할 분리

### 4.1 `AGENTS.md` (Codex 와 공통)

- 한국어 baseline 보고 원칙
- main/small 모델 구조 + worker 분리 패턴
- `ai-workflow/memory/active/` 문서를 먼저 read 하도록 안내

### 4.2 `GROK.md` (Grok Build 전용)

- AGENTS.md 와 *정합* — AGENTS.md 가 *먼저* read 되므로 본문에서 @AGENTS.md import 안내
- Grok Build 의 subagent / memory / hooks 운영 원칙
- MCP 등록 절차 안내 (`.grok/config.toml` 의 `[mcp_servers]` 섹션)
- Skill 등록 절차 안내 (`.grok/skills/standard-ai-workflow/SKILL.md` 자동 load)
- 한국어 baseline + 3-5개 다음 작업 후보 + 권장 다음 행동 보고

### 4.3 두 문서가 가리키는 사실이 다르다면

- `GROK.md` 가 *additive rule* 이므로 우선 (Grok Build 세션에서).
- `AGENTS.md` 와 `GROK.md` 의 한국어 baseline / worker 분리 원칙은 *동일하게 유지*.

## 5. bootstrap 예시

### 신규 프로젝트 (default)

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/project \
  --project-slug my_project \
  --project-name "My Project" \
  --adoption-mode new \
  --harness grok-build \
  --copy-core-docs
```

### Codex 와 동시 사용 (둘 다 emit)

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/project \
  --project-slug my_project \
  --project-name "My Project" \
  --adoption-mode new \
  --harness codex --harness grok-build \
  --copy-core-docs
```

→ AGENTS.md 가 두 번 emit 되지 않음 (idempotent).

### MCP 자동 심기

```bash
python3 workflow-source/scripts/bootstrap_workflow_kit.py \
  --target-root <project_root> \
  --project-slug <slug> --project-name "<name>" \
  --harness grok-build --adoption-mode existing --copy-core-docs \
  --enable-mcp
```

## 6. 도입 후 확인 포인트

- `AGENTS.md` 와 `GROK.md` 가 root 에 존재
- `.grok/skills/standard-ai-workflow/SKILL.md` 의 frontmatter (name / description) 가 TUI picker 에서 표시되는지 확인
- `.grok/config.toml.example` 를 실제 `.grok/config.toml` 로 cp 했는지 확인 (절대 경로 보정)
- `ai-workflow/memory/active/state.json`, `session_handoff.md`, `work_backlog.md`, `PROJECT_PROFILE.md` 가 실제로 존재하고 최신 상태인지 확인
- Wiki 진입점: `ai-workflow/wiki/index.md` (R4 anchor 기반). AI agent query 시 먼저 로드.
- `--enable-mcp` 사용 시 `.grok/config.toml` 의 MCP 서버 정의가 실제 endpoint 와 일치하는지 확인
- 첫 세션에서 `state.json` + 오늘 날짜 backlog + handoff 를 갱신
- MCP draft 자료는 기본 export 에 포함되지 않으므로, runtime 적용 전에 별도 검토 없이 바로 연결하지 않는다
- Codex 와 동시 사용 시 MCP alias `standardAiWorkflowReadOnly` 가 양쪽 config 에 *동일하게* 등록되는지 확인 (priority 는 `cwd > repo > user`)

## 7. 자주 손보게 되는 부분

- `GROK.md` 의 한국어 baseline / 다음 작업 후보
- `PROJECT_PROFILE.md` 의 검증 규칙
- `session_handoff.md` 의 현재 기준선
- `.grok/config.toml` 의 절대 경로 (`PYTHONPATH` / `STANDARD_AI_WORKFLOW_ROOT`)

## 8. 피해야 할 구성

- `~/.grok/config.toml` 에 프로젝트별 명령을 직접 넣는 것
- 여러 프로젝트가 공유하는 전역 설정에 특정 저장소 backlog 경로를 넣는 것
- `AGENTS.md` 와 `GROK.md` 의 baseline 원칙이 서로 어긋나게 유지되는 것

## 9. 로컬 MCP 설치 (`--enable-mcp`)

Grok Build 의 MCP 연결은 `.grok/config.toml` 의 `[mcp_servers.<alias>]` 섹션이다.

### 9.1 자동 심기

`bootstrap_workflow_kit.py --harness grok-build --enable-mcp` 옵션이 `<root>/.grok/config.toml` 스니펫을 한 번에 생성한다. 예:

```bash
python3 workflow-source/scripts/bootstrap_workflow_kit.py \
  --target-root <project_root> \
  --project-slug <slug> --project-name "<name>" \
  --harness grok-build --adoption-mode existing --copy-core-docs \
  --enable-mcp
```

`--mcp-bridge jsonrpc-bridge|stdio-sdk` 로 transport 선택 가능. 기본값은 `jsonrpc-bridge` (안정적).

### 9.2 전역에 적용

`~/.grok/config.toml` 의 `[mcp_servers]` 테이블 아래에 스니펫을 그대로 복사한다. 절대 경로 보정:

```toml
[mcp_servers.standardAiWorkflowReadOnly]
command = "python3"
args = ["-m", "workflow_kit.server.read_only_jsonrpc", "--stdio-lines"]
PYTHONPATH = "/ABSOLUTE/PATH/TO/standard_ai_workflow/workflow-source"
STANDARD_AI_WORKFLOW_ROOT = "/ABSOLUTE/PATH/TO/<project_root>"
```

자세한 가이드: [`../../core/mcp_installation_by_harness.md`](../../core/mcp_installation_by_harness.md), 예시: [`../../examples/mcp_config_examples/codex-mcp.toml`](../../examples/mcp_config_examples/codex-mcp.toml)

### 9.3 호환성 (Claude / Cursor / .mcp.json 자동 import)

Grok Build 는 다음 호환 파일을 자동 로드한다.

| Source | Location | 우선순위 |
|---|---|---|
| `~/.grok/config.toml` | user | lowest |
| `<repo-root>/.grok/config.toml` | project | medium |
| `<cwd>/.grok/config.toml` | project | highest |
| `~/.claude.json` (Claude 호환) | user | claude compat |
| `<cwd>/.cursor/mcp.json` (Cursor 호환) | project | cursor compat |
| `<cwd>/.mcp.json` (MCP 표준) | project | lowest |

→ 동일 alias 가 여러 소스에 있으면 *config.toml > claude > cursor > .mcp.json* 순서로 우선 적용. 기존 Claude / Cursor 워크플로우가 있으면 *자동 import* 가능.

## 다음에 읽을 문서

- 적용 가이드: [./apply_guide.md](./apply_guide.md)
- 하네스 허브: [../README.md](../README.md)
- 배포 전략: [../../core/workflow_harness_distribution.md](../../core/workflow_harness_distribution.md)
- 설정 계층: [../../core/workflow_configuration_layers.md](../../core/workflow_configuration_layers.md)
- 글로벌 주입 정책: [../../core/workflow_global_injection_policy.md](../../core/workflow_global_injection_policy.md)
- MCP 설치 by 하네스: [../../core/mcp_installation_by_harness.md](../../core/mcp_installation_by_harness.md)
- 전역 snippet: [../../global-snippets/grok-build/config.toml.snippet](../../global-snippets/grok-build/config.toml.snippet)
- Codex 패키지 (AGENTS.md 진입점 비교): [./codex/README.md](./codex/README.md)
- Claude Code 패키지 (root 진입점 비교): [./claude-code/README.md](./claude-code/README.md)
