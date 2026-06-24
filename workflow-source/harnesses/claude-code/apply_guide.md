# Claude Code Workflow Apply Guide

- 문서 목적: 기존 또는 신규 프로젝트에 표준 AI 워크플로우를 **Claude Code** 하네스 기준으로 적용하는 실제 절차를 단계별로 안내한다.
- 범위: bootstrap 실행, Claude Code 설정 연결, project-local skill/command 검토, 첫 세션 시작 방법, **skill-only 진입 정공법**
- 대상 독자: Claude Code 사용자, 저장소 관리자, AI workflow 설계자
- 상태: beta
- 최종 수정일: 2026-06-24
- 관련 문서: [`../../core/workflow_adoption_entrypoints.md`](../../core/workflow_adoption_entrypoints.md), [`../../core/workflow_configuration_layers.md`](../../core/workflow_configuration_layers.md), [`../../core/workflow_global_injection_policy.md`](../../core/workflow_global_injection_policy.md), [`../../scripts/bootstrap_workflow_kit.py`](../../scripts/bootstrap_workflow_kit.py)

## 1. 언제 이 가이드를 쓰는가

- 프로젝트에서 **Claude Code** (Anthropic 공식 CLI) 를 주 하네스로 사용하려고 할 때
- 표준 workflow 문서를 `.claude/commands/` slash command 로 연결하려고 할 때
- AGENTS.md 가 아닌 **slash command 만** 으로 워크플로우 진입을 원하는 환경

## 1.1 Claude Code 의 *진입점* 특성

| Harness | Root 진입점 | 진입 mechanism |
|---|---|---|
| OpenCode / Codex / pi-dev | `AGENTS.md` (root) | 자동 read (harness 가 startup 에 load) |
| Gemini CLI | `GEMINI.md` (root) | 자동 read |
| Antigravity | `ANTIGRAVITY.md` (root) | 자동 read |
| **Claude Code** | **`.claude/commands/*.md` (slash command)** | **사용자 명시 invocation** |

→ Claude Code 는 *root 진입점 파일* (예: `CLAUDE.md` 같은) 을 자동 read 안 함. **slash command 가 진입 mechanism**. 본 가이드의 정공법은 `--entry-mode skill-only` 와 결합.

## 2. 적용 전 확인

- Claude Code 가 `.claude/commands/*.md` slash command 를 인식하는지 확인.
- 본 가이드는 `--entry-mode skill-only` 와 결합해 **AGENTS.md / GEMINI.md 같은 root 진입점 안 emit**. harness-specific command 만 emit.
- 프로젝트에서 `ai-workflow/memory/active/` 가 *single source of truth* 인지 확인 (session-start / backlog-update / doc-sync 의 reading target).
- `~/.mavis/agents/` 의 memory 와 본 repo 의 `ai-workflow/memory/active/` 가 *양방향* 정합 (R8 / R9 rule) 인지 확인.

## 2.1 권장 설정 계층 (Claude Code 정공법)

- **전역 (user-level)**: `~/.claude/CLAUDE.md` (없으면 생성 안 함 — 본 가이드는 의도적으로 *root 진입점 안 만듦*)
- **공유 (project-level)**: `.claude/commands/*.md` (3개 slash command) + `ai-workflow/` (workflow state docs)
- **로컬**: `ai-workflow/memory/active/` 의 *실제 명령 / backlog / handoff / state*

Claude Code 의 *project root 진입점 부재* 가 본 정공법의 핵심. 표준 workflow 진입의 *single mechanism* = slash command 3종.

## 3. 신규 프로젝트 적용 순서

### 3.1 bootstrap 실행 (skill-only 진입)

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

**핵심 flag**:
- `--harness claude-code` — Claude Code 하네스 adapter
- `--entry-mode skill-only` — root 진입점 (AGENTS.md 등) skip, `.claude/commands/*.md` 3종만 emit
- `--copy-core-docs` — workflow 표준 문서 (`ai-workflow/core/*.md`) 를 target 에 복사

### 3.2 emit 결과 verify

```bash
ls -la .claude/commands/
# 3 file:
#   workflow-session-start.md
#   workflow-backlog-update.md
#   workflow-doc-sync.md
```

**AGENTS.md 가 *없는지* 확인** (skill-only 진입의 의도):
```bash
ls -la AGENTS.md 2>/dev/null
# ls: AGENTS.md: No such file or directory
```

### 3.3 첫 세션 시작

1. Claude Code 실행 후 다음 slash command 입력:
   ```
   /workflow-session-start
   ```
2. command body 의 절차대로 `ai-workflow/memory/active/state.json` → `session_handoff.md` → `work_backlog.md` → `PROJECT_PROFILE.md` 순서로 read
3. 1줄 baseline 요약 + 3-5개 다음 작업 후보 + 권장 다음 행동 보고 (한국어)
4. 사용자 confirm 후 `/workflow-backlog-update` 로 오늘 작업 등록

### 3.4 일상 작업

- 작업 시작: `/workflow-session-start` (baseline 복원)
- 작업 등록: `/workflow-backlog-update` (TASK 추가/갱신)
- 영향 문서 동기화: `/workflow-doc-sync` (후보 식별 + anchor 추천)

## 4. 기존 프로젝트 적용 순서

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/existing-repo \
  --project-slug existing_repo \
  --project-name "Existing Repo" \
  --adoption-mode existing \
  --harness claude-code \
  --entry-mode skill-only \
  --copy-core-docs
```

**주의**:
- `--entry-mode skill-only` 일 때 root 진입점 (AGENTS.md) emit ❌ — 기존 repo 의 *다른 AGENTS.md* 와 충돌 없음
- `.claude/commands/` 가 이미 있으면 `--force` 명시 또는 `--no-force` 로 skip (default = `force=True`)
- 기존 repo 의 CLAUDE.md / AGENTS.md 는 *자동 제거 ❌* (사용자 직접 결정) — 본 가이드의 *non-destructive* 원칙

## 5. language + context 원칙 (Claude Code)

- 사용자에게 보이는 작업 보고, 상태 요약, 문서 갱신 문안 = **한국어**
- 코드, 명령어, file path, 설정 key = 원문 그대로
- handoff 와 backlog 에는 *다음 세션에 꼭 필요한 사실* 만
- 중간 reasoning / 중복 요약 / 자기 설명 금지
- `purpose_digest` (state.json) 의 1-line summary 가 directional intent 의 anchor

## 6. 다음에 읽을 문서

- 배포 전략: [`../workflow_harness_distribution.md`](../workflow_harness_distribution.md)
- 하네스 인덱스: [`../README.md`](../README.md)
- 스크립트 안내: [`../scripts/README.md`](../scripts/README.md)
- 표준 workflow 문서: [`../../core/workflow_adoption_entrypoints.md`](../../core/workflow_adoption_entrypoints.md)
- AGENTS.md 기반 진입: [`./opencode/apply_guide.md`](./opencode/apply_guide.md), [`./codex/apply_guide.md`](./codex/apply_guide.md)
