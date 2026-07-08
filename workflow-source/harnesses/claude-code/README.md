# Claude Code Harness Package

- 문서 목적: 표준 AI 워크플로우를 Claude Code 하네스에 맞춰 배포할 때 생성되는 파일과 검토 포인트를 정리한다.
- 범위: `CLAUDE.md` (root 진입점) + `.claude/commands/workflow-*.md` 3종 slash command, 공통 문서 연결 방식
- 대상 독자: Claude Code 사용자, 저장소 관리자, AI workflow 설계자
- 상태: beta (v0.10.2 진입점 정정 반영)
- 최종 수정일: 2026-07-08
- 관련 문서: `../../core/workflow_harness_distribution.md`, `../../core/workflow_adoption_entrypoints.md`, `../../scripts/bootstrap_workflow_kit.py`

## 1. 진입점 특성

Claude Code 의 진입 mechanism 은 두 가지다 (v0.10.2 정정).

| 진입점 | 자동 read | scope |
|---|---|---|
| `CLAUDE.md` (root or `.claude/CLAUDE.md`) | ✅ 매 세션 | project |
| `~/.claude/CLAUDE.md` | ✅ | user |
| `CLAUDE.local.md` (root, .gitignore) | ✅ | local |
| `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS) | ✅ | org policy |
| `.claude/commands/*.md` (slash command) | ❌ (user invocation) | project |
| `AGENTS.md` | ❌ (직접 read 안 함) | - |

→ **`CLAUDE.md` 가 root 진입점** (자동 read). slash command 3종은 *additive tool* (user invocation).

## 2. 생성 대상

bootstrap 시 다음 4개 파일이 emit 된다.

- 프로젝트 루트 `CLAUDE.md` (root 진입점, 자동 read)
- `.claude/commands/workflow-session-start.md` (slash command)
- `.claude/commands/workflow-backlog-update.md` (slash command)
- `.claude/commands/workflow-doc-sync.md` (slash command)

## 3. 구성 원칙

- `CLAUDE.md` 는 Claude Code 의 *project 진입점*. 매 세션 시작 시 자동 read 되므로 한국어 baseline + 3-5개 다음 작업 후보 + 권장 다음 행동 보고를 짧게 포함한다.
- 상세 정책은 `ai-workflow/memory/active/` 문서를 먼저 읽도록 연결한다.
- 3개 slash command 는 user invocation 방식의 *additive 도구*. 자동 실행되지 않으므로 필요 시 사용자가 `/workflow-session-start`, `/workflow-backlog-update`, `/workflow-doc-sync` 로 호출한다.
- 기존 `AGENTS.md` 가 있으면 `CLAUDE.md` 의 `@AGENTS.md` import 또는 symlink 으로 통합한다. Claude Code 는 `AGENTS.md` 를 *직접 read 하지 않음* (v0.10.2 정정).
- `entry-mode=skill-only` 옵션으로 `CLAUDE.md` 진입점 생성을 skip 하고 slash command 3종만 emit 가능 (기존 `CLAUDE.md` 가 있는 환경에서 caller 가 직접 관리).
- 본 하네스는 orchestrator / worker 분리 패턴을 강제하지 않는다. bounded scope 작업이 필요하면 Bash / Agent tool 로 분리하고 메인 에이전트는 결과 통합에 집중한다.
- `--enable-mcp` 시 `.mcp.json` 에 MCP 서버 등록 스니펫이 함께 emit 되며, Claude Code 의 MCP 설정 형식에 맞춰진다.

## 4. AGENTS.md 통합

기존 프로젝트에 `AGENTS.md` 가 있는 경우 두 가지 방식 중 선택한다.

### Import 방식 (권장, cross-platform)

`CLAUDE.md` 첫 줄에 `@AGENTS.md` 추가:

```markdown
@AGENTS.md

## Claude Code

Use plan mode for changes under `src/billing/`.
```

### Symlink 방식 (Linux/macOS only)

```bash
ln -s AGENTS.md CLAUDE.md
```

## 5. bootstrap 예시

### 신규 프로젝트 (default = aggressive)

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/project \
  --project-slug my_project \
  --project-name "My Project" \
  --adoption-mode new \
  --harness claude-code \
  --copy-core-docs
```

### skill-only 진입 (CLAUDE.md skip)

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/project \
  --project-slug my_project \
  --project-name "My Project" \
  --adoption-mode new \
  --harness claude-code \
  --entry-mode skill-only \
  --copy-core-docs
```

### 기존 프로젝트 적용

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/existing-repo \
  --project-slug existing_repo \
  --project-name "Existing Repo" \
  --adoption-mode existing \
  --harness claude-code \
  --copy-core-docs
```

## 6. 도입 후 확인 포인트

- `CLAUDE.md` 가 자동 read 되어 한국어 baseline + 다음 작업 후보가 보고되는지 확인
- `ai-workflow/memory/active/state.json`, `session_handoff.md`, `work_backlog.md`, `PROJECT_PROFILE.md` 가 실제로 존재하고 최신 상태인지 확인
- Wiki 진입점: `ai-workflow/wiki/index.md` (R4 anchor 기반). AI agent query 시 먼저 로드.
- 기존 `AGENTS.md` 와 통합 시 `@AGENTS.md` import 또는 symlink 이 정상 동작하는지 확인
- 3개 slash command (`/workflow-session-start`, `/workflow-backlog-update`, `/workflow-doc-sync`) 가 호출 가능한지 확인
- 첫 세션에서 `state.json`, `session_handoff.md`, `work_backlog.md`, 오늘 날짜 backlog 를 실제 저장소 상태로 갱신
- `--enable-mcp` 사용 시 `.mcp.json` 의 서버 정의가 실제 MCP 서버 endpoint 와 일치하는지 확인
- MCP draft 자료는 기본 export 에 포함되지 않으므로, runtime 적용 전에 별도 검토 없이 바로 연결하지 않는다

## 7. 다음에 읽을 문서

- 적용 가이드: [./apply_guide.md](./apply_guide.md)
- 하네스 허브: [../README.md](../README.md)
- 배포 전략: [../../core/workflow_harness_distribution.md](../../core/workflow_harness_distribution.md)
- 설정 계층: [../../core/workflow_configuration_layers.md](../../core/workflow_configuration_layers.md)
- 글로벌 주입 정책: [../../core/workflow_global_injection_policy.md](../../core/workflow_global_injection_policy.md)
- 진입 mechanism 비교: [./codex/apply_guide.md](./codex/apply_guide.md), [./opencode/apply_guide.md](./opencode/apply_guide.md)