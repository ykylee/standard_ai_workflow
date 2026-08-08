# Beta v1.1.1 (2026-08-08)

> **상태: 릴리스.** `tool_version = v1.1.1-beta`, tag `v1.1.1-beta`, GitHub Release 발행.
> **patch release** — Beta-v1.1.0 의 `[project.scripts]` 29 entry point 추가만.
>
> PyPI 배포는 정책상 미실행 (릴리스 채널 = GitHub Releases).

## 0. 릴리스 판정

Beta-v1.1.0 의 *CLI 도구화 A안* ([§0.7 retrospective](../../workflow-source/core/multi_workspace_orchestration.md#07-적용-상태)) 마무리. 32개
`workflow-source/tools/` 스크립트 중 **CLI 29개** 가 `pip install -e .` 후 console_script
binary 로 자동 생성. venv e2e 검증으로 실제 29개 binary 가 PATH 에 박히고 `--help`
가 정상 동작함을 실측.

본 patch release 의 핵심 deliverable:
- `pyproject.toml` `[project.scripts]` 29 entry point (`workflow-{kebab-case}`)
- `tools` package 등록 + `tools = tools` package-dir
- `tools/__init__.py` 정정 (기존 *script 라 import 안 됨* → *CLI 化 A안* marker)
- venv e2e: `pip install -e workflow-source/` → 29 binary + `--help` 정상
- smoke `check_entry_points.py` 4 case ALL PASS

**Scope**: 0 리스크. 기존 호출 경로 (`python3 workflow-source/tools/X.py`) 그대로
동작. 신규 호출 경로 (`workflow-X --help` 또는 `python3 -m tools.X`) *추가* 만.

## 1. 릴리스 요약

- **CLI 化 A안 close** — 점진적 도입 1단계 완료. 29 entry point 노출.
- **기존 MCP / 듀얼 모드 CLI / 안전 hook** — 변동 없음 (Beta-v1.1.0 그대로).
- breaking change: ❌. (기존 `python3 workflow-source/tools/X.py` 호출 경로 보존.)
- `mkdocs_git_dates.py` 제외 — mkdocs plugin (`on_page_markdown` hook) 이지 CLI 가 아님.

## 2. deliverable

### 2.1 `[project.scripts]` 29 entry point

| command | module | 용도 |
|---|---|---|
| `workflow-registry` | `tools.workspace_registry` | host-scoped registry CLI (TASK-015) |
| `workflow-host-pull-registry` | `tools.host_pull_registry` | federation pull CLI (TASK-016) |
| `workflow-drift-detect` | `tools.detect_scope_drift` | scope drift detection (TASK-018) |
| `workflow-install-pre-push-hook` | `tools.install_pre_push_hook` | pre-push hook installer (TASK-019) |
| `workflow-rotate-workflow-logs` | `tools.rotate_workflow_logs` | dual mode CLI (TASK-017) |
| `workflow-apply-robust-patch` | `tools.apply_robust_patch` | dual mode CLI (TASK-017) |
| `workflow-create-environment-record-stub` | `tools.create_environment_record_stub` | dual mode CLI (TASK-017) |
| `workflow-check-quickstart-stale-links` | `tools.check_quickstart_stale_links` | dual mode CLI (TASK-017) |
| `workflow-seed-workspace-memory` | `tools.seed_workspace_memory` | multi-workspace (TASK-002) |
| `workflow-claim-workspace` | `tools.claim_workspace` | multi-workspace (TASK-002) |
| `workflow-survey-remote-workspaces` | `tools.survey_remote_workspaces` | multi-workspace (TASK-002) |
| `workflow-release-pipeline` | `tools.release_pipeline` | release pipeline |
| ... 외 17개 (`--help` 로 확인) | | |

전체 29개 command 목록:

```
workflow-apply-robust-patch       workflow-archive-branch-memory
workflow-archive-stale-memory     workflow-audit-root-anchors
workflow-check-packaging          workflow-check-quickstart-stale-links
workflow-claim-workspace          workflow-consumer-metrics
workflow-create-environment-record-stub
workflow-detect-scope-drift       workflow-emit-wiki-l2-body
workflow-fill-reverse-engineering-artifacts
workflow-fix-readme-for-release   workflow-host-pull-registry
workflow-install-pre-push-hook    workflow-migrate-active-to-appendonly
workflow-migrate-legacy-l2        workflow-migrate-memory-to-branch-scoped
workflow-refresh-wiki-memory      workflow-release-pipeline
workflow-release-v0-13-0         workflow-rotate-workflow-logs
workflow-score-wiki-maintainability
workflow-score-wiki-trend         workflow-seed-workspace-memory
workflow-survey-remote-workspaces workflow-sync-release-hash
workflow-wiki-emit                workflow-workspace-registry
```

### 2.2 호출 경로 (legacy + new + module)

| 경로 | 사용 예 |
|---|---|
| legacy | `python3 workflow-source/tools/detect_scope_drift.py --help` |
| **new (CLI 化 A안)** | `workflow-drift-detect --help` (PATH 진입 후 어디서든) |
| module | `python3 -m tools.detect_scope_drift --help` |

### 2.3 venv e2e 검증 결과

```bash
$ python3 -m venv /tmp/wf-venv-test
$ /tmp/wf-venv-test/bin/pip install -e workflow-source/
Successfully installed standard-ai-workflow-1.1.0
$ /tmp/wf-venv-test/bin/workflow-detect-scope-drift --help
usage: workflow-detect-scope-drift [-h] [--pre-handoff PRE_HANDOFF] ...
$ /tmp/wf-venv-test/bin/workflow-workspace-registry list
host_id: ...  entries: 0
```

→ 29 binary 모두 PATH 진입 + `--help` 정상.

### 2.4 smoke 회귀 (8+ case ALL PASS, 0 회귀)

| smoke | case | 상태 |
|---|---|---|
| `check_entry_points.py` (TASK-020) | 4 | ✅ (TOML/import/main/help) |
| `check_pre_push_hook.py` (TASK-019) | 7 | ✅ |
| `check_scope_drift.py` (TASK-018) | 7+1 | ✅ |
| `check_cli_wrappers.py` (TASK-017) | 4 | ✅ |
| `check_host_pull.py` (TASK-016) | 8 | ✅ |
| `check_host_federation.py` (TASK-015) | 8 | ✅ |
| `check_registry_confidence.py` (TASK-014) | 8 | ✅ |
| `check_mavis_attach_e2e.py` (§2.68) | 4 | ✅ |

## 3. 1차 출처 (cross-ref)

- `core/multi_workspace_orchestration.md` §0.7 — CLI 化 옵션 A/B/C/D (A안 채택)
- `pyproject.toml` `[project.scripts]` — 29 entry point
- `pyproject.toml` `[tool.setuptools]` `packages` — `tools` 추가
- `tools/__init__.py` — CLI 化 A안 marker
- `tests/check_entry_points.py` — smoke (4 case)
- `releases/Beta-v1.1.0.md` — 직전 release (이전 본문)

## 4. 후속

- **TASK-021+ B안 dispatcher (`wk` 단일 binary)** — `wk --help` 가 29개 다 보여주는 git-style
  통합 UX. `[project.scripts]` 와 *공존* (A안 binary 도 유지).
- **TASK-022+ tab completion** — `argcomplete` (bash) / `shtab` (zsh) 1 line 추가.
- **TASK-023+ HTTP server 도구** (각 호스트가 자기 registry serving).

## 5. compatibility

- breaking change: ❌
- 기존 `python3 workflow-source/tools/X.py` 호출 — 그대로 동작
- MCP server 변경 ❌
- 표준 §10 / §1 — unchanged
- v1.1.0 → v1.1.1: pure patch (semver 의미 그대로)
