# Custom Workflow Apply Guide

- 문서 목적: 기존 또는 신규 프로젝트에 표준 AI 워크플로우를 *caller 자사 custom harness* 에 적용하는 절차.
- 범위: bootstrap, custom 진입점 wire-up.
- 대상 독자: custom harness / internal IDE / CLI 사용자.
- 상태: beta
- 최종 수정일: 2026-06-24
- 관련 문서: [`../../core/workflow_adoption_entrypoints.md`](../../core/workflow_adoption_entrypoints.md), [`../../scripts/bootstrap_workflow_kit.py`](../../scripts/bootstrap_workflow_kit.py)

## 1. 언제 이 가이드를 쓰는가

- 표준 6개 하네스 (Codex / OpenCode / Gemini CLI / Antigravity / MiniMax Code / pi-dev / Claude Code / Aider / Goose) 외 *caller 자사 custom 도구* 가 있을 때
- AGENTS.md 자동 read 도 안 하고, slash command / extension / `--read` flag 메커니즘도 안 가질 때
- 표준 workflow 의 *중립 contract* (3 skill output schema) 만 caller 자사 도구에 wire-up 하고 싶을 때

## 2. Custom 진입점 특성

| 진입점 | 자동 read | 비고 |
|---|---|---|
| `.workflow-kits/custom/SKILL.md` | ❌ (caller 가 wire-up) | reference template |
| caller 자사 tool 의 system prompt | caller 결정 | 본 파일을 import |
| `AGENTS.md` | caller 결정 | - |

→ **중립 (neutral) 진입점** — 특정 도구에 자동 load 안 됨. caller 가 *참조 template* 으로 사용.

## 3. 적용 전 확인

- caller 자사 custom 도구가 system prompt / context 에 *markdown file* 을 include / reference 할 수 있는지 확인
- 본 가이드의 bootstrap 은 `.workflow-kits/custom/SKILL.md` 1 file emit (root 진입점 없음)

## 4. 신규 프로젝트 적용 순서

### 4.1 bootstrap 실행

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/project \
  --project-slug my_project \
  --project-name "My Project" \
  --adoption-mode new \
  --harness custom \
  --copy-core-docs
```

**emit 결과**:
- `.workflow-kits/custom/SKILL.md` (caller wire-up 용 reference template)

### 4.2 caller wire-up

```bash
# 예 1: 사내 internal CLI 의 경우 (symlink)
ln -s .workflow-kits/custom/SKILL.md ~/.internal-cli/standard-ai-workflow.md
```

```python
# 예 2: 사내 Python 도구에서 (reference doc)
with open(".workflow-kits/custom/SKILL.md") as f:
    workflow_skill = f.read()
# → caller tool 의 system prompt 에 append
```

```yaml
# 예 3: 사내 config 기반 tool (YAML import)
workflow_skill:
  source: .workflow-kits/custom/SKILL.md
  auto_load: true
```

## 5. 기존 프로젝트 적용 순서

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/existing-repo \
  --project-slug existing_repo \
  --project-name "Existing Repo" \
  --adoption-mode existing \
  --harness custom \
  --copy-core-docs
```

## 6. wire-up 시 주의

- **Standard contract 정합**: caller tool 이 *3 skill output schema* (SessionStartOutput / BacklogUpdateOutput / DocSyncOutput) 를 *정확히* consume 해야 함. v0.9.5 part 2 의 *purpose_context* + v0.9.6 part 3 의 *advisory pattern* 포함.
- **graceful skip 정공법 정합**: 3 skill 모두 input file 부재 시 *no-op* + advisory (status 0). caller tool 이 *fail* 처리하면 안 됨.
- **self-bootstrap mode** (v0.10.2): session-start 의 `self_bootstrap_suggested=True` + `self_bootstrap_init_commands` field 를 caller 가 *명시적으로* 표시 권장.

## 7. 다음에 읽을 문서

- 배포 전략: [`../workflow_harness_distribution.md`](../workflow_harness_distribution.md)
- 표준 workflow 문서: [`../../core/workflow_adoption_entrypoints.md`](../../core/workflow_adoption_entrypoints.md)
- AGENTS.md 기반 진입: [`./codex/apply_guide.md`](./codex/apply_guide.md)
- Claude Code 진입 (slash command): [`./claude-code/apply_guide.md`](./claude-code/apply_guide.md)
