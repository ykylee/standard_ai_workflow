# Grok Build Workflow Apply Guide

- 문서 목적: 기존 또는 신규 프로젝트에 표준 AI 워크플로우를 **Grok Build** (xAI CLI TUI) 하네스 기준으로 적용하는 절차.
- 범위: bootstrap 실행, 생성 파일 검토, Grok Build 설정 연결, 첫 세션 시작 방법, 트러블슈팅.
- 대상 독자: Grok Build 사용자, 저장소 관리자, AI workflow 설계자.
- 상태: beta
- 최종 수정일: 2026-07-20
- 관련 문서: [`./README.md`](./README.md), [`../../core/workflow_adoption_entrypoints.md`](../../core/workflow_adoption_entrypoints.md), [`../../core/workflow_configuration_layers.md`](../../core/workflow_configuration_layers.md), [`../../core/workflow_global_injection_policy.md`](../../core/workflow_global_injection_policy.md), [`../../scripts/bootstrap_workflow_kit.py`](../../scripts/bootstrap_workflow_kit.py)

## 1. 언제 이 가이드를 쓰는가

- 프로젝트에서 **Grok Build** (xAI Build, https://x.ai/build) 를 주 하네스로 사용하려고 할 때
- 표준 workflow 문서를 `AGENTS.md` + `GROK.md` + `.grok/config.toml` 진입점과 연결하려고 할 때
- 신규 프로젝트 또는 기존 프로젝트에 Grok Build 기준 도입을 시작하려고 할 때
- Codex 와 *동시에* 같은 AGENTS.md 진입점을 공유하면서 Grok Build 의 subagent / memory / MCP 기능을 활용하려고 할 때

## 2. Grok Build 의 *진입점 특성*

| 진입점 | 자동 read | scope | 비고 |
|---|---|---|---|
| `AGENTS.md` (project root) | ✅ 매 세션 | project | Codex 와 공통 진입점 |
| `~/.grok/AGENTS.md` | ✅ | user | user-level instructions |
| `GROK.md` (project root) | ✅ 매 세션 | project | **Grok Build 전용 진입점** (본 하네스 emit) |
| `.grok/config.toml` | ✅ 매 세션 | project | MCP / plugin / permission |
| `.grok/skills/` | ✅ | project | TUI picker 표시 |
| `.grok/agents/` | ✅ | project | custom agent |
| `.grok/hooks/` | ✅ | project | lifecycle hook |
| `--experimental-memory` / `GROK_MEMORY=1` | ✅ | cross-session | memory feature |
| `~/.claude.json` / `~/.cursor/mcp.json` / `.mcp.json` | ✅ (compat) | mixed | 자동 import (config > claude > cursor > mcp) |

→ Grok Build 의 진입점은 **AGENTS.md + GROK.md (root) + `.grok/` 디렉터리 통합**. Codex 와 동일한 AGENTS.md 진입점 + Grok Build 전용 GROK.md additive rule.

## 3. 적용 전 확인

- Grok Build 가 프로젝트 루트의 `AGENTS.md` 와 `GROK.md` 를 자동 read 하는 흐름을 사용할 수 있어야 한다.
- Grok Build 의 project-local config 우선순위 (cwd > repo > user) 를 이해한다.
- 프로젝트에서 workflow 문서를 둘 위치를 `ai-workflow/` 로 유지할지 결정한다.
- 기존 프로젝트라면 기본 실행 명령과 테스트 명령을 자동 추정값과 대조할 사람이 필요하다.

## 3.1 권장 설정 계층

- **전역**:
  - `~/.grok/config.toml` 에 공통 MCP 와 기본 진입 원칙만 둔다.
  - 기존 Codex / Claude / Cursor / MCP 표준 config 가 있으면 *자동 import* 됨 (단, alias 충돌 주의).
- **공유**:
  - 프로젝트 루트 `AGENTS.md` + `GROK.md` 와 `ai-workflow/` 패키지를 둔다.
- **로컬**:
  - `ai-workflow/memory/active/` 문서에서 실제 명령, 경로, backlog 상태를 관리한다.

프로젝트별 규칙은 항상 local 문서가 우선한다.

## 3.2 전역 기본값 보호 원칙

- Grok Build 전역 `config.toml` 에 이미 있는 model/provider 기본값 (`[models] default = "grok-build"`) 은 프로젝트 workflow 가 자동으로 덮어쓰지 않게 유지한다.
- `.grok/config.toml.example` 는 additive 한 MCP / skill / memory 예시 중심으로 유지한다.
- 프로젝트 특화 명령과 규칙은 `AGENTS.md` 와 `GROK.md` + `ai-workflow/memory/active/` 문서에서 읽게 한다.

## 3.3 전역에 넣을 것과 넣지 않을 것

- 전역에 넣기 좋은 것:
  - 공통 MCP 연결 (`[mcp_servers.<alias>]`)
  - `[skills] paths` (user-scope skill 디렉터리)
  - `[memory]` opt-in + 검색 threshold
  - 기본 안전 정책 철학 (`[permission]`)
- 전역에 넣지 않는 것이 좋은 것:
  - 프로젝트별 실행 명령
  - 특정 저장소 문서 경로
  - backlog 상태
  - model/provider 기본값 강제

## 3.4 추천 운영 패턴

- 개인 전역 Grok Build 설정:
  - `~/.grok/config.toml` 에 additive snippet 만 유지
  - `[compat.claude] mcps = true` / `[compat.cursor] mcps = true` 로 기존 workflow MCP 자동 import (선택)
- 프로젝트 공통 진입:
  - 루트 `AGENTS.md` (Codex 와 공통)
  - 루트 `GROK.md` (Grok Build 전용)
- 프로젝트 실제 운영값:
  - `ai-workflow/memory/active/` 문서 세트

이렇게 두면 전역 설정을 거의 건드리지 않으면서 프로젝트별 규칙만 교체할 수 있다.

## 3.5 언어와 컨텍스트 운영 원칙

- Grok Build 에서 사용자에게 직접 보이는 작업 보고, 상태 요약, 문서 초안은 한국어로 작성하도록 `AGENTS.md` 와 `GROK.md` 에 명시한다.
- 코드, 명령어, 파일 경로, 설정 key 는 필요한 경우 원문 그대로 유지한다.
- 내부 사고 과정, 임시 분류, 중간 reasoning 은 모델이 효율적으로 처리하게 두고, 사용자에게는 필요한 결론만 짧게 전달하도록 한다.
- 진행 업데이트는 짧고 목적 지향적으로 유지하고, 이미 확인한 사실을 반복해서 길게 설명하지 않는다.
- handoff 와 backlog 에는 다음 세션에 필요한 핵심 사실만 남겨 컨텍스트 누적을 줄인다.
- Grok Build 에서도 가능한 경우 메인 에이전트는 조정/통합에 집중하고, bounded scope 읽기/쓰기/검증은 내장 subagent (`explore` / `plan`) 또는 custom agent (`.grok/agents/`) 로 분리하는 운영 패턴을 권장한다.
- 메인 에이전트는 `grok-build` (default), bounded scope 서브 에이전트는 `[subagents] models.explore = "grok-4.20-multi-agent"` 같은 더 가벼운 모델로 분리하는 편이 효율적이다.

## 4. 신규 프로젝트 적용 순서

### 4.1 bootstrap 실행

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/project \
  --project-slug my_project \
  --project-name "My Project" \
  --adoption-mode new \
  --harness grok-build \
  --copy-core-docs
```

### 4.2 emit 결과 verify

```bash
ls AGENTS.md GROK.md
ls .grok/skills/standard-ai-workflow/SKILL.md
ls .grok/config.toml.example
```

**emit 결과** (4 file):
- `AGENTS.md` (root) — Codex 와 공통
- `GROK.md` (root) — Grok Build 전용
- `.grok/skills/standard-ai-workflow/SKILL.md` (TUI picker 표시)
- `.grok/config.toml.example` (caller 가 `.grok/config.toml` 로 cp)

### 4.3 config.toml 활성화

```bash
# 1. config.toml 초기화 (절대 경로 보정 필요)
mkdir -p .grok
cp .grok/config.toml.example .grok/config.toml
$EDITOR .grok/config.toml
# - PYTHONPATH 를 절대 경로로 보정 (예: "/home/user/repos/standard_ai_workflow/workflow-source")
# - STANDARD_AI_WORKFLOW_ROOT 를 절대 경로로 보정
```

### 4.4 첫 세션 검증

```bash
grok
# Grok Build 가 .grok/config.toml 자동 load → AGENTS.md + GROK.md 자동 read
# → .grok/skills/standard-ai-workflow/SKILL.md TUI picker 표시
```

세션이 정상 시작되면 다음을 확인한다.

- `AGENTS.md` 와 `GROK.md` 가 매 세션 자동 read 되어 한국어 baseline + 다음 작업 후보가 보고되는지
- `.grok/skills/standard-ai-workflow/SKILL.md` 가 TUI picker (`/` 입력 후 skill 검색) 에 표시되는지
- `.grok/config.toml` 의 MCP 서버가 정상 연결되는지 (`/mcps` modal 에서 확인)
- `ai-workflow/memory/active/state.json` 이 자동 갱신되는지
- `session_handoff.md` 의 "다음 세션 시작 포인트" 가 한 문장 갱신되는지
- Wiki 진입점: `ai-workflow/wiki/index.md` (R4 anchor 기반). AI agent query 시 먼저 로드.

## 5. 작업 중인 프로젝트 적용 순서

### 5.1 bootstrap 실행 (dry-run 권장)

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/existing-repo \
  --project-slug existing_repo \
  --project-name "Existing Repo" \
  --adoption-mode existing \
  --harness grok-build \
  --copy-core-docs
```

### 5.2 적용 후 검토

1. `ai-workflow/memory/active/repository_assessment.md` 를 읽고 추정 스택, 명령, 문서 경로가 실제 저장소와 맞는지 검토.
2. `PROJECT_PROFILE.md` 의 설치, 실행, 테스트 명령을 실제 운영 기준으로 수정.
3. 루트 `AGENTS.md` 와 `GROK.md` 의 기본 명령과 문서 경로가 맞는지 확인.
4. 작업 보고 언어와 컨텍스트 절약 원칙도 이 단계에서 함께 검토.
5. export bundle 을 쓰는 경우 read-only MCP descriptor 의 `transport_ready` 값이 `false` 임을 확인하고, 실제 MCP 연결은 별도 서버 루프가 준비된 뒤 진행.
6. 가능하면 메인 에이전트가 직접 모든 읽기/쓰기를 떠안지 않도록, bounded scope subagent 호출 원칙도 이 단계에서 같이 검토.
7. 첫 실제 작업을 오늘 날짜 backlog 에 등록하고, 세션 종료 직전(commit 직전) handoff 를 갱신. 종료 절차는 [`core/global_workflow_standard.md`](../../core/global_workflow_standard.md) §8 정합 — `memory 갱신 → commit → push` 순서.

기존 배포본을 갱신하는 상황이라면 먼저 dry-run 으로 변경 예정 경로와 backup 대상부터 확인.

```bash
python3 scripts/apply_harness_update.py \
  --source-root /path/to/exported-package \
  --target-root /path/to/project \
  --dry-run
```

## 6. Codex 와 동시 사용

Codex 와 Grok Build 가 *동시에* 같은 저장소를 다룰 수 있다. AGENTS.md 는 두 하네스 모두 자동 read 하므로 *동일 본문* 유지가 원칙.

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/project \
  --project-slug my_project \
  --project-name "My Project" \
  --adoption-mode new \
  --harness codex --harness grok-build \
  --copy-core-docs
```

→ AGENTS.md 가 idempotent 하게 한 번만 emit 됨. GROK.md 와 `.grok/` 디렉터리는 Grok Build 가 추가.

**주의**:
- Codex 의 `.codex/mcp.toml` 과 Grok Build 의 `.grok/config.toml` 의 `[mcp_servers.standardAiWorkflowReadOnly]` 가 *동일 alias* 면 runtime 은 양쪽 모두에서 정상 동작 (전역 ~ `~/.grok/config.toml` 으로 import 가능).
- Codex 와 Grok Build 를 동시에 *전역* MCP 등록하면 중복 등록 위험 → 사용자 전역 config 에서 한쪽만 활성화 권장.

## 7. 적용 후 확인 체크리스트

- `AGENTS.md` 가 root 에 존재
- `GROK.md` 가 root 에 존재
- `.grok/skills/standard-ai-workflow/SKILL.md` 가 TUI picker 에 표시
- `.grok/config.toml` 이 실제 절대 경로로 보정됨 (예시만 있는 `.config.toml.example` 과 구분)
- `ai-workflow/memory/active/` 문서 세트가 존재
- profile 문서의 명령이 실제 저장소 기준으로 채워져 있음
- 첫 backlog 항목과 handoff 가 비어 있지 않음
- Grok Build 가 읽어야 할 시작 문서 경로가 팀 내에서 합의되어 있음

## 8. 자주 손보게 되는 부분

- `GROK.md` 의 프로젝트 기본 명령 + 다음 작업 후보
- `PROJECT_PROFILE.md` 의 검증 규칙
- `session_handoff.md` 의 현재 기준선
- `.grok/config.toml` 의 절대 경로 (`PYTHONPATH` / `STANDARD_AI_WORKFLOW_ROOT`)
- 최신 날짜 backlog 의 상태값과 다음 세션 시작 포인트

## 9. 피해야 할 구성

- `~/.grok/config.toml` 에 프로젝트별 명령을 직접 넣는 것
- 여러 프로젝트가 공유하는 전역 설정에 특정 저장소 backlog 경로를 넣는 것
- `AGENTS.md` 와 `GROK.md` 의 baseline 원칙이 서로 어긋나게 유지되는 것
- `--experimental-memory` 또는 `GROK_MEMORY=1` 없이 `~/.grok/memory/` 를 신뢰하는 것 (opt-in 필요)

## 10. 로컬 MCP 설치 (`--enable-mcp`)

Grok Build 의 MCP 연결은 `.grok/config.toml` 의 `[mcp_servers.<alias>]` 섹션이다.

### 10.1 자동 심기

`bootstrap_workflow_kit.py` 의 `--harness grok-build --enable-mcp` 옵션이 `<root>/.grok/config.toml` 스니펫을 한 번에 생성한다. 예:

```bash
python3 workflow-source/scripts/bootstrap_workflow_kit.py \
  --target-root <project_root> \
  --project-slug <slug> --project-name "<name>" \
  --harness grok-build --adoption-mode existing --copy-core-docs \
  --enable-mcp
```

`--mcp-bridge jsonrpc-bridge|stdio-sdk` 로 transport 선택 가능. 기본값은 `jsonrpc-bridge` (안정적).

### 10.2 전역에 적용

`~/.grok/config.toml` 의 `[mcp_servers]` 테이블 아래에 스니펫을 그대로 복사한다. 절대 경로 보정:

```toml
[mcp_servers.standardAiWorkflowReadOnly]
command = "python3"
args = ["-m", "workflow_kit.server.read_only_jsonrpc", "--stdio-lines"]
PYTHONPATH = "/ABSOLUTE/PATH/TO/standard_ai_workflow/workflow-source"
STANDARD_AI_WORKFLOW_ROOT = "/ABSOLUTE/PATH/TO/<project_root>"
```

자세한 가이드: [`../../core/mcp_installation_by_harness.md`](../../core/mcp_installation_by_harness.md), 예시: [`../../examples/mcp_config_examples/codex-mcp.toml`](../../examples/mcp_config_examples/codex-mcp.toml)

### 10.3 Transport 선택

- 기본 `jsonrpc-bridge` (권장, 안정) — `python3 -m workflow_kit.server.read_only_jsonrpc --stdio-lines`
- `stdio-sdk` (실험적) — `python3 -m workflow_kit.server.read_only_mcp_sdk --stdio-sdk`. `--mcp-bridge stdio-sdk` 로 전환. `check_read_only_mcp_sdk_stdio.py` 가 그린이 되면 정식 권장으로 승격.

### 10.4 호환성 (Claude / Cursor / .mcp.json 자동 import)

Grok Build 는 다음 호환 파일을 자동 로드한다 (config > claude > cursor > mcp 순 우선순위).

| Source | Format | Location |
|---|---|---|
| `config.toml` | Native Grok config | `~/.grok/config.toml`, `.grok/config.toml` |
| `.claude.json` | Claude Code format | `~/.claude.json` (`[compat.claude] mcps`) |
| `.cursor/mcp.json` | Cursor format | `~/.cursor/mcp.json`, `<project>/.cursor/mcp.json` (`[compat.cursor] mcps`) |
| `.mcp.json` | MCP standard | Project root (cwd to git root) |

→ 기존 workflow MCP 등록이 Claude / Cursor / 표준 MCP 소스에 있으면 *자동 import* 됨. **단, 동일 alias 의 [mcp_servers] 가 여러 소스에 있으면 config.toml 이 우선** 이므로 의도치 않은 override 가능.

## 11. 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `GROK.md` 가 로드되지 않음 | root 가 Grok Build 의 신뢰 경로 밖 | 프로젝트 root 에 있는지 확인 후 세션 재시작 |
| `mcp_servers` 가 연결되지 않음 | `PYTHONPATH` 가 `workflow-source` 를 가리키지 않음 | `.grok/config.toml` 의 `mcp_servers.standardAiWorkflowReadOnly.env.PYTHONPATH` 절대 경로 확인 |
| Skill 이 TUI picker 에 표시 안 됨 | `.grok/skills/standard-ai-workflow/SKILL.md` 의 frontmatter 가 없거나 형식 오류 | frontmatter 의 `name` / `description` 5 field 정공법 확인 |
| AGENTS.md 와 GROK.md baseline 불일치 | 두 문서가 따로 evolve | `AGENTS.md` 가 master, `GROK.md` 는 additive rule 만 유지. 둘 다 동기화 |
| 한국어 보고가 영어로 나옴 | `language: "ko-KR"` 가 config 에 없음 | `.grok/config.toml` 또는 `GROK.md` 의 baseline 에 한국어 보고 명시 |
| Codex 와 동시 사용 시 MCP alias 충돌 | 양쪽 config 에 동일 alias | 사용자 전역 config 에서 한쪽만 활성화. project-local config 는 그대로 유지 |
| `~/.grok/memory/` 가 작동 안 함 | `--experimental-memory` 또는 `GROK_MEMORY=1` 미설정 | 환경 변수 또는 `[memory] enabled = true` 설정 |
| Claude / Cursor MCP 가 import 안 됨 | `[compat.claude] mcps = false` 또는 `GROK_CLAUDE_MCPS_ENABLED=0` | `~/.grok/config.toml` 에 `[compat.claude] mcps = true` 명시 |

## 12. 다음 단계

- 첫 적용이 끝나면 `workflow-source/harnesses/grok-build/README.md` 와 본 가이드를 함께 검토.
- 추가 custom agent 가 필요하면 `.grok/agents/` 에 새 파일 추가 (frontmatter 정공법).
- 운영 패턴이 안정되면 `pilot_adoption_record_template.md` 로 도입 기록을 남긴다.
- Codex 와 동시 사용 시 MCP alias 정책과 한국어 baseline 일관성을 주기적으로 검증.

## 다음에 읽을 문서

- Grok Build 패키지 안내: [`./README.md`](./README.md)
- 하네스 허브: [`../README.md`](../README.md)
- 도입 분기 가이드: [`../../core/workflow_adoption_entrypoints.md`](../../core/workflow_adoption_entrypoints.md)
- 설정 계층 가이드: [`../../core/workflow_configuration_layers.md`](../../core/workflow_configuration_layers.md)
- 비침투적 주입 정책: [`../../core/workflow_global_injection_policy.md`](../../core/workflow_global_injection_policy.md)
- **MCP 설치 by 하네스: [`../../core/mcp_installation_by_harness.md`](../../core/mcp_installation_by_harness.md)**
- 전역 snippet: [`../../global-snippets/grok-build/config.toml.snippet`](../../global-snippets/grok-build/config.toml.snippet)
- Codex 진입점 비교: [`./codex/apply_guide.md`](./codex/apply_guide.md)
- Claude Code 진입점 비교: [`./claude-code/apply_guide.md`](./claude-code/apply_guide.md)
