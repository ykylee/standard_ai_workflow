# Goose Workflow Apply Guide

- 문서 목적: 기존 또는 신규 프로젝트에 표준 AI 워크플로우를 **Goose** 하네스 기준으로 적용하는 절차.
- 범위: bootstrap, Goose extension 등록, 진입점 설정.
- 대상 독자: Goose 사용자.
- 상태: beta
- 최종 수정일: 2026-06-24
- 관련 문서: [`../../core/workflow_adoption_entrypoints.md`](../../core/workflow_adoption_entrypoints.md), [`../../scripts/bootstrap_workflow_kit.py`](../../scripts/bootstrap_workflow_kit.py)

## 1. 언제 이 가이드를 쓰는가

- 프로젝트에서 **Goose** (https://github.com/block/goose) 를 주 하네스로 사용하려고 할 때
- 표준 workflow 를 Goose 의 *extension* 메커니즘으로 등록

## 2. Goose 의 *진입점 특성*

| 진입점 | 자동 read | 비고 |
|---|---|---|
| `.goose/config.yaml` 의 `read_files` | ✅ (session 시작) | 자동 read |
| `.goose/config.yaml` 의 `entry_points` | ✅ (trigger 조건 시) | trigger 기반 |
| `.goose/config.yaml` 의 `hooks` (on_session_end 등) | ✅ (lifecycle) | shell command |
| `AGENTS.md` | ❌ (직접 read 안 함, 명시 read 필요) | - |

→ Goose 는 *config 기반* 진입. `.goose/config.yaml` 한 파일이 진입점 + extension + hook 의 *single source of truth*.

## 3. 적용 전 확인

- Goose 가 `.goose/config.yaml` 자동 load (project root) 확인
- 본 가이드의 bootstrap 은 `.goose/config.yaml` 1 file emit (root 진입점 없음)

## 4. 신규 프로젝트 적용 순서

### 4.1 bootstrap 실행

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/project \
  --project-slug my_project \
  --project-name "My Project" \
  --adoption-mode new \
  --harness goose \
  --copy-core-docs
```

**emit 결과**:
- `.goose/config.yaml` (extension 등록 + entry_points 3종 + read_files 5종 + on_session_end hook)

### 4.2 emit 결과 verify + Goose 실행

```bash
ls .goose/config.yaml
goose
# Goose 가 .goose/config.yaml 자동 load → read_files 5종 자동 read → entry_points 3종 등록
```

## 5. 기존 프로젝트 적용 순서

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/existing-repo \
  --project-slug existing_repo \
  --project-name "Existing Repo" \
  --adoption-mode existing \
  --harness goose \
  --copy-core-docs
```

**주의**:
- 기존 `.goose/config.yaml` 가 있으면 *overwrite* 위험. `--no-force` 또는 `--entry-mode skill-only` 권장
- 기존 config 가 있으면 *수동 merge* 권장 (bootstrap 은 새 `.goose/config.yaml` emit)

## 6. config.yaml 구조 (emit 결과 예시)

```yaml
version: 1
project:
  name: My Project
  workflow: standard-ai-workflow

entry_points:
  session_start:
    command: "python3 ai-workflow/skills/session-start/scripts/run_session_start.py"
    trigger: on_session_start
  backlog_update:
    command: "python3 ai-workflow/skills/backlog-update/scripts/run_backlog_update.py"
    trigger: manual
  doc_sync:
    command: "python3 ai-workflow/skills/doc-sync/scripts/run_doc_sync.py"
    trigger: manual

read_files:
  - ai-workflow/memory/active/state.json
  - ai-workflow/memory/active/session_handoff.md
  - ai-workflow/memory/active/work_backlog.md
  - ai-workflow/memory/active/PROJECT_PROFILE.md
  - ai-workflow/memory/active/PURPOSE.md

hooks:
  on_session_end:
    - "python3 ai-workflow/skills/session-start/scripts/run_session_start.py --update-handoff"

language: ko
```

## 7. language + context 원칙

- 사용자에게 보이는 보고 = 한국어 (`language: ko`)
- read_files 의 workflow state docs 가 *baseline 의 SSOT*

## 8. 다음에 읽을 문서

- 배포 전략: [`../workflow_harness_distribution.md`](../workflow_harness_distribution.md)
- 표준 workflow 문서: [`../../core/workflow_adoption_entrypoints.md`](../../core/workflow_adoption_entrypoints.md)
- AGENTS.md 기반 진입: [`./codex/apply_guide.md`](./codex/apply_guide.md), [`./claude-code/apply_guide.md`](./claude-code/apply_guide.md)
