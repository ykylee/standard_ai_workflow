# Aider Workflow Apply Guide

- 문서 목적: 기존 또는 신규 프로젝트에 표준 AI 워크플로우를 **Aider** 하네스 기준으로 적용하는 절차.
- 범위: bootstrap, Aider 설정, project-local 진입점 검토, 첫 세션.
- 대상 독자: Aider 사용자.
- 상태: beta
- 최종 수정일: 2026-06-24
- 관련 문서: [`../../core/workflow_adoption_entrypoints.md`](../../core/workflow_adoption_entrypoints.md), [`../../scripts/bootstrap_workflow_kit.py`](../../scripts/bootstrap_workflow_kit.py)

## 1. 언제 이 가이드를 쓰는가

- 프로젝트에서 **Aider** (https://aider.chat) 를 주 하네스로 사용하려고 할 때
- 표준 workflow 문서를 `CONVENTIONS.md` + `.aider.conf.yml` 의 `read:` list 로 연결

## 2. Aider 의 *진입점 특성*

| 진입점 | 자동 read | 비고 |
|---|---|---|
| `--read <file>` flag | ✅ (해당 session) | command-line 옵션 |
| `.aider.conf.yml` 의 `read:` list | ✅ (해당 project) | 자동 load |
| `CONVENTIONS.md` (root) | ❌ (명시 등록 필요) | `.aider.conf.yml` 의 `read:` list 에 추가 |
| `AGENTS.md` | ❌ (직접 read 안 함) | - |

→ Aider 는 `--read` flag 또는 `.aider.conf.yml` 의 `read:` list 로 *명시* 등록한 파일만 read. `CONVENTIONS.md` 만 root 에 두면 자동 read 안 됨 — `read:` list 등록 필수.

## 3. 적용 전 확인

- Aider 가 `.aider.conf.yml` 자동 load 확인
- 본 가이드의 bootstrap 은 `CONVENTIONS.md` (root) + `.aider/conventions.md` (양쪽) + `.aider.conf.yml.example` emit
- caller 는 `.aider.conf.yml.example` 을 `.aider.conf.yml` 로 `cp` 후 사용

## 4. 신규 프로젝트 적용 순서

### 4.1 bootstrap 실행

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/project \
  --project-slug my_project \
  --project-name "My Project" \
  --adoption-mode new \
  --harness aider \
  --copy-core-docs
```

**emit 결과**:
- `CONVENTIONS.md` (root)
- `.aider/conventions.md` (`.aider/` 디렉토리)
- `.aider.conf.yml.example` (caller 가 `.aider.conf.yml` 로 cp)

### 4.2 emit 결과 verify + setup

```bash
ls CONVENTIONS.md .aider/conventions.md .aider.conf.yml.example
cp .aider.conf.yml.example .aider.conf.yml
# 필요 시 .aider.conf.yml 의 model / read list 조정
```

### 4.3 Aider 실행

```bash
# 자동 read (CONVENTIONS.md + workflow state docs) 으로 baseline 복원
aider --read CONVENTIONS.md
# 또는 .aider.conf.yml 의 read: list 자동 load
aider
```

## 5. 기존 프로젝트 적용 순서

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /path/to/existing-repo \
  --project-slug existing_repo \
  --project-name "Existing Repo" \
  --adoption-mode existing \
  --harness aider \
  --copy-core-docs
```

**주의**:
- 기존 `CONVENTIONS.md` 가 있으면 *overwrite* 위험. `--no-force` 또는 `--entry-mode skill-only` 권장
- 기존 `.aider.conf.yml` 가 있으면 *수동 merge* 권장 (bootstrap 은 `.aider.conf.yml.example` 만 emit)

## 6. language + context 원칙

- 사용자에게 보이는 보고 = 한국어, `commit-language: ko` (`.aider.conf.yml` 의 commit-language: ko)
- 코드 / file path / 설정 key = 원문
- Aider 의 commit message 자동 생성 시 weak-model 사용 (`claude-3-5-haiku-20241022`)

## 7. 다음에 읽을 문서

- 배포 전략: [`../workflow_harness_distribution.md`](../workflow_harness_distribution.md)
- 표준 workflow 문서: [`../../core/workflow_adoption_entrypoints.md`](../../core/workflow_adoption_entrypoints.md)
- AGENTS.md 기반 진입: [`./codex/apply_guide.md`](./codex/apply_guide.md), [`./claude-code/apply_guide.md`](./claude-code/apply_guide.md)
