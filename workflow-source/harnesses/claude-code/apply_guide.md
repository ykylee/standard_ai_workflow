# Claude Code Workflow Apply Guide (v0.10.2 정정본)

- 문서 목적: 기존 또는 신규 프로젝트에 표준 AI 워크플로우를 **Claude Code** 하네스 기준으로 적용하는 실제 절차를 단계별로 안내한다.
- 범위: bootstrap 실행, Claude Code 설정 연결, project-local 진입점 검토, 첫 세션 시작 방법
- 대상 독자: Claude Code 사용자, 저장소 관리자, AI workflow 설계자
- 상태: beta (v0.10.2 정정)
- 최종 수정일: 2026-06-24
- 관련 문서: [`../../core/workflow_adoption_entrypoints.md`](../../core/workflow_adoption_entrypoints.md), [`../../core/workflow_configuration_layers.md`](../../core/workflow_configuration_layers.md), [`../../core/workflow_global_injection_policy.md`](../../core/workflow_global_injection_policy.md), [`../../scripts/bootstrap_workflow_kit.py`](../../scripts/bootstrap_workflow_kit.py)

## ⚠️ v0.10.2 정정 사항

v0.10.1 의 본 apply_guide 가 *잘못된 가설* 을 포함했습니다:

- ❌ v0.10.1: "Claude Code 는 root 진입점 자동 read 안 함, slash command 가 진입점"
- ✅ v0.10.2 (정정): **Claude Code 는 `CLAUDE.md` 를 root 진입점으로 자동 read**. `AGENTS.md` 는 *직접* read 하지 않음. 본 가이드는 두 진입 mechanism (CLAUDE.md + slash command) 을 *모두* 설명합니다.

## 1. Claude Code 의 *진입점 특성*

| 진입점 | 자동 read | scope |
|---|---|---|
| `CLAUDE.md` (root or `.claude/CLAUDE.md`) | ✅ 매 세션 | project |
| `~/.claude/CLAUDE.md` | ✅ | user |
| `CLAUDE.local.md` (root, .gitignore) | ✅ | local |
| `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS) | ✅ | org policy |
| `.claude/commands/*.md` (slash command) | ❌ (user invocation) | project |
| `AGENTS.md` | ❌ (직접 read 안 함) | - |

→ **CLAUDE.md 가 root 진입점** (자동 read, AGENTS.md 와 parallel). slash command 는 *additive 도구* (user invocation).

## 2. 적용 전 확인

- Claude Code 가 `CLAUDE.md` 자동 read 동작 (v0.10.1 의 잘못된 가설 정정 후)
- 본 가이드는 `--entry-mode skill-only` 와 결합해 *root 진입점 skip* 옵션 제공 (default = aggressive, v0.10.1 의 가드 정합)
- 프로젝트에서 `ai-workflow/memory/active/` 가 *single source of truth* 인지 확인
- `~/.mavis/agents/` 의 memory 와 본 repo 의 `ai-workflow/memory/active/` 가 *양방향* 정합 (R8 / R9 rule) 인지 확인

## 2.1 AGENTS.md 와의 통합 (기존 AGENTS.md 가 있으면)

Claude Code 는 `AGENTS.md` 를 *직접 read 안 함*. 통합 방법 2종:

### Import 방식 (권장, cross-platform)

`CLAUDE.md` 첫 줄에 `@AGENTS.md` 추가:

```markdown
# CLAUDE.md

@AGENTS.md

## Claude Code

Use plan mode for changes under `src/billing/`.
```

Claude 가 session 시작 시 `@AGENTS.md` 의 내용을 자동으로 expand.

### Symlink 방식 (Linux/macOS only)

```bash
ln -s AGENTS.md CLAUDE.md
```

## 2.2 권장 설정 계층

- **전역 (user-level)**: `~/.claude/CLAUDE.md` (없으면 생성 안 함)
- **공유 (project-level)**: `CLAUDE.md` (root 진입점) + `.claude/commands/*.md` (3개 slash command) + `ai-workflow/`
- **로컬**: `ai-workflow/memory/active/` 의 *실제 명령 / backlog / handoff / state*

## 3. 신규 프로젝트 적용 순서

### 3.1 bootstrap 실행 (default = aggressive)

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/project \
  --project-slug my_project \
  --project-name "My Project" \
  --adoption-mode new \
  --harness claude-code \
  --copy-core-docs
```

**emit 결과**:
- `CLAUDE.md` (root 진입점) — 자동 read
- `.claude/commands/workflow-session-start.md` — slash command
- `.claude/commands/workflow-backlog-update.md` — slash command
- `.claude/commands/workflow-doc-sync.md` — slash command

### 3.2 skill-only 진입 (CLAUDE.md skip)

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

**emit 결과**:
- ~~`CLAUDE.md`~~ (entry-mode=skill-only 로 skip)
- `.claude/commands/workflow-{session-start,backlog-update,doc-sync}.md` (3 slash command)

→ *기존 CLAUDE.md 가 있는 환경* 에서 사용. 또는 *caller 가 직접 CLAUDE.md 를 관리* 하는 환경.

### 3.3 emit 결과 verify

```bash
ls -la CLAUDE.md .claude/commands/
# CLAUDE.md (root 진입점)
# 3 file: .claude/commands/workflow-{session-start,backlog-update,doc-sync}.md
```

### 3.4 첫 세션 시작

Claude Code 실행 시:
1. `CLAUDE.md` 가 *자동* read (session 시작 시 root 진입점)
2. 한국어 baseline + 3-5개 다음 작업 후보 + 권장 다음 행동 보고
3. 사용자가 slash command 로 추가 진입:
   ```
   /workflow-session-start  (또는 CLAUDE.md 의 baseline 으로 충분)
   /workflow-backlog-update
   /workflow-doc-sync
   ```

## 4. self-bootstrap mode (v0.10.2 신규)

session-start skill 의 핵심 4 file (`session_handoff.md` / `work_backlog.md` / `state.json` / `PROJECT_PROFILE.md`) 모두 부재 시:

- `status="warning"` + `self_bootstrap_suggested=True`
- `self_bootstrap_init_commands: list[str]` 에 scaffold 명령 emit
- session-start 자체는 *graceful* (exit code 0) — 사용자에게 scaffold 권장

```
$ python3 skills/session-start/scripts/run_session_start.py \
    --session-handoff-path ai-workflow/memory/active/sessions \
    --work-backlog-index-path ai-workflow/memory/active/backlog \
    --project-profile-path docs/PROJECT_PROFILE.md
{
  "status": "warning",
  "self_bootstrap_suggested": true,
  "self_bootstrap_init_commands": [
    "python3 scripts/bootstrap_workflow_kit.py --target-root /path --project-slug ... --entry-mode skill-only",
    "python3 skills/session-start/scripts/run_session_start.py ..."
  ],
  "warnings": ["self-bootstrap mode: 핵심 4 file 모두 부재..."]
}
```

## 5. 기존 프로젝트 적용 순서

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/existing-repo \
  --project-slug existing_repo \
  --project-name "Existing Repo" \
  --adoption-mode existing \
  --harness claude-code \
  --copy-core-docs
```

**주의**:
- 기존 `CLAUDE.md` 가 있으면 *overwrite* (default `force=True`). `--no-force` 또는 `--entry-mode skill-only` 로 skip 가능
- 기존 `AGENTS.md` 가 있으면 → `CLAUDE.md` 에 `@AGENTS.md` import 추가 또는 symlink

## 6. language + context 원칙

- 사용자에게 보이는 작업 보고, 상태 요약, 문서 갱신 문안 = **한국어**
- 코드, 명령어, file path, 설정 key = 원문 그대로
- handoff 와 backlog 에는 *다음 세션에 꼭 필요한 사실* 만
- 중간 reasoning / 중복 요약 / 자기 설명 금지
- `purpose_digest` (state.json) 의 1-line summary 가 directional intent 의 anchor

## 7. 다음에 읽을 문서

- 배포 전략: [`../workflow_harness_distribution.md`](../workflow_harness_distribution.md)
- 하네스 인덱스: [`../README.md`](../README.md)
- 스크립트 안내: [`../scripts/README.md`](../scripts/README.md)
- 표준 workflow 문서: [`../../core/workflow_adoption_entrypoints.md`](../../core/workflow_adoption_entrypoints.md)
- AGENTS.md 기반 진입: [`./codex/apply_guide.md`](./codex/apply_guide.md), [`./opencode/apply_guide.md`](./opencode/apply_guide.md)
- Aider 진입: [`./aider/apply_guide.md`](./aider/apply_guide.md) (v0.10.2+)
- Goose 진입: [`./goose/apply_guide.md`](./goose/apply_guide.md) (v0.10.2+)
- Custom 진입: [`./custom/apply_guide.md`](./custom/apply_guide.md) (v0.10.2+)
