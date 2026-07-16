# Project Workflow Profile (Active Memory)

- 문서 목적: 본 저장소(`standard_ai_workflow`) 자신의 운영 profile. 외부 배포용은 [`../../docs/PROJECT_PROFILE.md`](../../docs/PROJECT_PROFILE.md) (consolidated reference).
- 범위: 프로젝트 메타, 자기 참조 명령, 자기 검증, 자기 정책
- 대상 독자: AI agent (session-start / backlog-update), 다음 세션의 본인, 멀티 에이전트 운영자
- 상태: stable (self-dogfood, 2026-07-09 갱신)
- 최종 수정일: 2026-07-09
- 관련 문서: [공통 표준](../core/global_workflow_standard.md), [PURPOSE.md](./PURPOSE.md) (directional intent), [project_status_assessment.md](./project_status_assessment.md) (자가진단 점수), 외부 [docs/PROJECT_PROFILE.md](../../docs/PROJECT_PROFILE.md) (배포 reference)

## 0. Purpose 참조

이 프로젝트의 *directional intent* (왜 존재하는지) 는 [`PURPOSE.md`](./PURPOSE.md) 참조. 본 문서는 프로젝트 메타 (name / stakeholder / commands / validation / policy) 만 다룬다.

PURPOSE.md 의 4-element (Goals / Key Questions / Research Scope / Evolving Thesis) 는 LLM 이 매 ingest/query 시 context load 의 *directional intent* 의 SSOT.

## 1. 프로젝트 개요 (Self)

- **프로젝트명**: Standard AI Workflow
- **프로젝트 슬러그**: `standard-ai-workflow`
- **GitHub**: `https://github.com/ykylee/standard_ai_workflow`
- **PyPI 패키지명**: `standard-ai-workflow`
- **프로젝트 목적**: 여러 프로젝트에서 공통으로 사용할 수 있는 표준 AI 협업 워크플로우 문서, 템플릿, skill/MCP/agent 구현 기준을 *독립 패키지* 형태로 제공한다. (PURPOSE.md G1-G4 참조)
- **주요 이해관계자**:
  - **저장소 maintainer**: `ykylee` (single-maintainer, self-dogfood 운영자)
  - **외부 consumer**: 워크플로우 도입 검토자, 멀티 에이전트 운영자, OKF bundle consumer
  - **내부**: AI 에이전트 (Sisyphus / Momus / doc-worker / code-worker), 다음 세션의 본인
- **현재 베이스라인**: **v0.11.22-beta** (package: standard-ai-workflow 0.11.22, runtime `__version__` = v0.11.22-beta)
- **Phase**: **Phase 1–11 done, Phase 12 in_progress** (운영 지능화 + deprecation 안정화). SSOT: [`../../workflow-source/core/maturity_matrix.json`](../../workflow-source/core/maturity_matrix.json)
- **누적 release cycle (memory 스냅샷)**: 91+ (v0.5.1 ~ v0.11.21, v0.11.22 release memory cycle 진행 중)

### 1.1 핵심 마일스톤 (v0.11.18 ~ v0.11.22)

| 버전 | 핵심 결과물 | commit |
|---|---|---|
| v0.11.18 | **FULL mypy strict 도달** (109 file clean, 0 errors) | 80470cd |
| v0.11.19 | 1st batch 4 skill stable (session-start / doc-sync / validation-plan / code-index-update) | dfafdc4 |
| v0.11.20 | 2nd batch 4 skill stable (backlog-update / merge-doc-reconcile / workflow-linter / project-status-assessment) + 2 latent bug fix | af6baaf |
| v0.11.21 | 3rd batch 1 skill stable (robust-patcher) | c90b437 |
| v0.11.22 | ADR-005 Memory Index Phase 1~3d 8 release 완료 + ADR-006 retrospective 자리 박기 | ea013a2 (memory cycle) |
| v0.10.4 | **CodeWhale 10번째 하네스** 추가 | cf0060d |

## 2. 문서 구조 (Path)

- **외부 문서 홈**: [`../../docs/index.md`](../../docs/index.md) (GitHub Pages site)
- **운영 문서 홈 (active memory)**: `ai-workflow/memory/active/`
- **백로그 위치**:
  - 인덱스: `ai-workflow/memory/active/backlog` (cross-version anchor)
  - 사이클별: `ai-workflow/memory/release/<version>/backlog/<YYYY-MM-DD>.md`
- **세션 인계**: 본 저장소는 `session_handoff.md` 패턴 대신 **`session_analysis_YYYY-MM-DD.md`** 패턴 사용 (예: `session_analysis_2026-07-09.md`). state.json 의 `recent_done_items` 가 provenance SSOT.
- **환경 기록 위치**: `ai-workflow/memory/active/environments/` (디렉토리 부재 — 부재 자체가 노트)
- **위키**: `ai-workflow/wiki/` (concepts / decisions / entities / topics / patterns / queries / sources)

## 3. 기본 명령 (Commands — self-reference)

### 3.1 환경 셋업 (최초 1회)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### 3.2 로컬 실행 (CLI 진입점)
```bash
# dispatcher 확인
PYTHONPATH=workflow-source python3 -m workflow_kit.cli --help

# read-only MCP stdio-sdk (v0.11.25 stable)
python3 -m workflow_kit.server.read_only_mcp_sdk --stdio-sdk

# read-only MCP jsonrpc-bridge (default)
python3 -m workflow_kit.server.read_only_jsonrpc --stdio-lines
```

### 3.3 부트스트랩 (다른 프로젝트에 도입)
```bash
python3 workflow-source/scripts/bootstrap_workflow_kit.py \
  --target-root . \
  --project-slug <consumer-slug> \
  --project-name "<consumer-name>" \
  --harness codex \
  --adoption-mode existing \
  --copy-core-docs \
  --enable-mcp \
  --force
```

### 3.4 회귀 (Smoke)
```bash
# 전체 스모크 (CI 동일)
for t in workflow-source/tests/check_*.py; do python "$t" || exit 1; done

# 핵심 subset
python workflow-source/tests/check_docs.py
python workflow-source/tests/check_bootstrap.py
python workflow-source/tests/check_bootstrap_mcp_roundtrip.py
python workflow-source/tests/check_drift_prevention_v0_11_23.py  # v0.11.23+
```

### 3.5 mypy strict (v0.11.18 도달)
```bash
mypy workflow-source/ --strict --extra mcp-sdk
```

### 3.6 상태 동기화 (state.json 생성)
```bash
python3 workflow-source/scripts/generate_workflow_state.py \
  --project-profile-path docs/PROJECT_PROFILE.md \
  --session-handoff-path ai-workflow/memory/session_handoff.md \
  --work-backlog-index-path ai-workflow/memory/work_backlog.md \
  --output-path ai-workflow/memory/state.json
```

## 4. 검증 포인트 (Validation — self)

| 영역 | 검증 방법 | 통과 기준 |
|---|---|---|
| **코드 변경** | `workflow-source/tests/check_*.py` + mypy strict | 200+ smoke PASS, mypy 0 errors |
| **출력 스키마** | `schemas/generated_output_schemas.json` 정합 | 모든 stable skill 이 BaseOutput 패턴 |
| **문서 변경** | `python workflow-source/tests/check_docs.py` | 124+ files 메타 + 링크 무결성 |
| **Drift prevention** | `check_drift_prevention_v0_11_23.py` | 6 case cross-check (v0.11.23+) |
| **UI 변경** | 하네스 overlay 별 렌더링 (현재 없음, N/A) | N/A |
| **배포/운영** | `workflow-source/scripts/export_harness_package.py` | 패키지 생성 + release note 검증 |
| **contract v1** | `check_contract_v1_*.py` (5종) | orchestrator ↔ sub-agent 위임 §4/§5 스키마 |

## 5. 예외 규칙 (Policy — self)

- **병합**: `ai-workflow/memory/state.json` 등 자동 생성 파일은 충돌 시 소스 문서 (backlog, handoff, analysis) 를 기준으로 재생성한다. LLM 의 manual edit 은 SSOT 위반.
- **승인**: 코어 문서 (`workflow-source/core/`) 변경 시 아키텍처 리뷰 필수. 특히 `global_workflow_standard.md`, `maturity_matrix.json`, `orchestrator_subagent_contract_v1.md` 는 본인 (ykylee) 의 명시적 commit 만 허용.
- **제약**:
  - Python 3.10+ 필수 (MCP SDK 의존성). 시스템 python 으로는 `ModuleNotFoundError`.
  - 모든 skill / MCP 출력은 공통 JSON 계약 구조 (`workflow_kit/common/schemas/*.py`) 준수.
  - stable skill 의 `apply` 필드는 항상 `True` (default). `False` 는 명시적 opt-out (예: `git-conflict-resolver`).
- **Deprecation policy** (G4 운영 약속):
  - 1 release `DeprecationWarning` → 다음 release `removal`
  - contract test (`check_deprecation_*.py`) 가 자동 verify
  - breaking change 시 migration 가이드를 release note 본문에 필수 포함
- **세션 종료 절차** ([`global_workflow_standard.md`](../core/global_workflow_standard.md) §8 정합): `memory 갱신 → commit → push` 순서.
- **ADR 작성 정책**: 본 저장소의 모든 architecture decision 은 `ai-workflow/wiki/decisions/adr-NNN-<slug>.md` 에 기록. 영구 보존 (R-9 wiki-source-rule).

## 6. Self-dogfood 운영 노트

- 본 저장소는 본인이 만든 도구의 *최초 consumer* (self-dogfood). 모든 release 는 본 저장소에서 먼저 검증 후 외부 consumer 에게 노출.
- self-bootstrap: `dist/harnesses/<harness>/<version>/bundle/` 가 본 저장소의 *자기 패키지*. 외부 배포와 동일 절차로 검증.
- audit 패턴: 분기 1회 본 저장소에 대해 `ai-workflow/memory/active/session_analysis_<YYYY-MM-DD>.md` + `ai-workflow/wiki/topics/workflow-audit-<YYYY-MM-DD>.md` 작성. (예: 2026-07-09 audit-session)

## 다음에 읽을 문서

- [PURPOSE.md](./PURPOSE.md) — *왜* 존재하는지 (directional intent SSOT)
- [project_status_assessment.md](./project_status_assessment.md) — 자가진단 매트릭스 (합계 26/33)
- [work_backlog.md](./work_backlog.md) — 일별 작업 백로그 인덱스
- 외부 [docs/PROJECT_PROFILE.md](../../docs/PROJECT_PROFILE.md) — 배포 reference
- [workflow_audit_2026-07-09.md](../../wiki/topics/workflow-audit-2026-07-09.md) — 최근 audit 보고서 (후속 10건 후보)
