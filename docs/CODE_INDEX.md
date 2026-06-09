# Code Index

- 문서 목적: 코드베이스 구조 및 핵심 컴포넌트를 안내하여 개발자의 코드 이해를 돕는다.
- 범위: 소스 코드 구조, 기술 스택, 핵심 모듈 설명
- 대상 독자: 개발자, AI 에이전트
- 상태: stable
- 최종 수정일: 2026-06-09
- 관련 문서: [./DOCUMENT_INDEX.md](./DOCUMENT_INDEX.md), [./INSTALLATION_AND_USAGE.md](./INSTALLATION_AND_USAGE.md), [../README.md](../README.md)

이 문서는 `Standard AI Workflow` 저장소의 코드 구조와 핵심 컴포넌트를 안내합니다 (v0.5.10-beta 기준).

## 1. 프로젝트 구조 개요

```text
.
├── workflow-source/                # ← Primary development source
│   ├── workflow_kit/               # 임포트 가능 Python 패키지
│   │   ├── common/                 # 공통 헬퍼 30+ submodule (paths, runner, errors, contracts, schemas, state, ...)
│   │   ├── contract_v1/            # Pydantic v2 contract v1 enforcement (output_validator, delegator, schemas)
│   │   ├── server/                 # read-only JSON-RPC bridge + MCP SDK v1.0 candidate
│   │   └── harness/                # 하네스별 메타 헬퍼
│   ├── bootstrap_lib/              # 부트스트랩 패키지 (v0.5.2+ 리팩터 결과, scripts/ 아래 위치)
│   ├── skills/                     # 11개 워크플로우 스킬 프로토타입
│   ├── mcp_servers/                # 8+ MCP 서버 프로토타입 + lib/
│   ├── scripts/                    # 부트스트랩, export, generate, demo, ... 엔트리
│   ├── tools/                      # check_packaging.py 등 운영 도구 (v0.5.8+)
│   ├── tests/                      # 52개 check_*.py 스모크 (CI 매 push)
│   ├── schemas/                    # JSON 스키마, 출력 샘플 계약, transport descriptor
│   ├── examples/                   # E2E 데모, 도입 예시, MCP config 5종, 출력 샘플
│   ├── harnesses/                  # 6개 하네스 오버레이 (codex, opencode, gemini-cli, antigravity, minimax-code, pi-dev) + _template
│   ├── templates/                  # 9개 템플릿 + prompts/ 3개 worker prompt
│   ├── core/                       # 35개 코어 표준 문서
│   ├── prompts/                    # 코어 표준 문서
│   ├── global-snippets/            # 하네스 전역 비침투적 snippet 예시
│   ├── releases/                   # 19개 릴리스 노트 (Alpha v0.1~v0.3 + Beta v0.5.0~v0.5.10)
│   ├── MEMORY_GOVERNANCE.md        # AI 메모리 문서 표준
│   └── pyproject.toml              # 패키지 매니페스트 (version 0.5.10-beta)
│
├── ai-workflow/                    # 런타임 state (bootstrap 으로 생성, .gitignore 일부)
│   ├── memory/                     # 세션 상태/백로그/릴리스별 스냅샷
│   │   ├── release/v0.5.1~v0.5.10/ # 릴리스별 스냅샷
│   │   ├── state.json              # 루트 baseline (latest_backlog_path)
│   │   ├── session_handoff.md
│   │   ├── work_backlog.md
│   │   └── plans/                  # 7개 TASK 계획 문서
│   ├── core/                       # 코어 문서 사본 (--copy-core-docs)
│   ├── mcp_servers/
│   ├── scripts/                    # 생성된 런타임 도구
│   ├── skills/
│   └── workflow_kit/
│
├── docs/                           # 영구 지식 베이스 (PR 리뷰 거쳐 main 머지)
│   ├── README.md                   # 문서 거버넌스 (state vs knowledge)
│   ├── DOCUMENT_INDEX.md           # 이 인덱스의 상위
│   ├── CODE_INDEX.md               # 이 문서
│   ├── PROJECT_PROFILE.md          # 프로젝트 운영 규칙/명령
│   ├── INSTALLATION_AND_USAGE.md   # 개발자 설치·사용 가이드
│   ├── RELEASE.md                  # 릴리스 절차
│   ├── architecture/               # ADR, 시스템 설계 (작성 예정)
│   ├── planning/                   # 마일스톤/로드맵 (작성 예정)
│   └── archive/                    # 폐기 후보
│
├── scripts/                        # 로컬 런타임 스크립트 (bootstrap 생성)
├── tests/                          # 개발 테스트 픽스처
├── dist/                           # 빌드 산출물 (.gitignore)
│   └── harnesses/                  # codex, opencode 패키지
├── .codex/                         # Codex 설정 예시
├── requirements.txt                # pydantic>=2, anyio>=4, mcp>=1
├── requirements-dev.txt            # mcp[cli]==1.27.0
├── .github/workflows/smoke.yml     # CI: 52개 check_*.py 병렬
├── AGENTS.md                       # Codex 진입 규칙 (bootstrap 생성)
└── README.md                       # 저장소 홈
```

## 2. 핵심 컴포넌트

### Workflow Kit (`workflow-source/workflow_kit/`)
- `common/`: 30+ submodule — `paths`, `project_docs`, `workflow_state`, `runner`, `errors`, `output_contracts`, `reconcile`, `scaffold`, `doc_sync`, `markdown`, `git`, `text`, `linter`, `patching`, `rotation`, `exploration`, `exploration_scope`, `normalize`, `session_outputs`, `workflow_writes`, `writing_bundle`, `read_only_bundle`, `milestones`, `planning`, `doc_transformer`, `docs`. `__init__.py` 가 비어 있으므로 `from workflow_kit.common.paths import ...` 처럼 submodule 명시 필요.
- `common/state/`, `common/contracts/`, `common/schemas/`, `common/modes/`: v0.5.7.1 부터 wheel packaging 에 포함 (subpackage)
- `contract_v1/` (v0.5.6+): Pydantic v2 기반 외부 contract v1 enforcement. `output_validator` (sub-agent 출력 §5 spec 검증), `delegator` (`choose_role` 단일 / `choose_roles` 배치 / `recommend_model_tier` 자동 / `DelegationDecision` / `DelegationRejected`).
- `server/`: `read_only_jsonrpc.py` (default 안정), `read_only_mcp_sdk.py` (v1.0 SDK candidate, 실험적), `mcp_v1_server.py` (정식 SDK stdio).

### Bootstrap (`workflow-source/scripts/bootstrap_lib/`)
v0.5.2+ 리팩터. 6-module 패키지:
- `__main__.py` (CLI 진입점)
- `cli.py`, `planner.py`, `renderers.py`, `validators.py`, `metadata.py`
- `harnesses/__init__.py` (HARNESS_SPECS + register_harness_builder)

권장 진입점: `python3 -m bootstrap_lib`. 레거시 호환 shim: `python3 workflow-source/scripts/bootstrap_workflow_kit.py`.

### Skills (`workflow-source/skills/`) — 11종
각 스킬은 특정 워크플로우 단계를 자동화하는 독립 패키지.
- **1차 핵심 6종** (v0.5.0+ stable/beta): `backlog-update`, `session-start`, `doc-sync`, `merge-doc-reconcile`, `validation-plan`, `workflow-linter`
- **2차 운영 2종** (v0.5.7+): `code-index-update`, `project-status-assessment`
- **3차 실전 3종** (v0.5.7+): `git-conflict-resolver`, `robust_patcher` (정밀 patch engine), `automated-repro-scaffold` (reproduction scaffold 생성)
- **추가** (v0.5.7+): `workers/backlog_steward.py` (workers/ subdir, 미문서화)

### MCP Servers (`workflow-source/mcp_servers/`) — 8+ documented, 3 undocumented
- 8 documented (with `MCP.md`): `latest-backlog` (v1), `check-doc-metadata` (v1), `check-doc-links`, `check-quickstart-stale-links`, `create-backlog-entry`, `git-history-summarizer`, `smart-context-reader` (implemented), `suggest-impacted-docs`
- 3 scripts-only (no MCP.md): `apply_robust_patch`, `create-environment-record-stub`, `create-session-handoff-draft`
- `lib/common_utils.py`: 공유 `TOOL_VERSION` helper
- Transport: `--mcp-bridge jsonrpc-bridge` (default, 안정) / `--mcp-bridge stdio-sdk` (실험적, 알려진 회귀)

### Harnesses (`workflow-source/harnesses/`) — 6 supported
`codex`, `opencode`, `gemini-cli`, `antigravity`, `minimax-code`, `pi-dev` + `_template`.
- 각 하네스: `README.md` + `apply_guide.md` (대부분) + `AGENTS.md` (pi-dev만) + 선택적 `overlay_spec.md` (antigravity만)
- 부트스트랩 등록: `workflow-source/scripts/bootstrap_lib/harnesses/__init__.py` 의 `HARNESS_SPECS` + `register_harness_builder`

## 3. 주요 진입점 (Entry Points)

- **부트스트랩 (v0.5.2+ 권장)**: `python3 -m bootstrap_lib ...`
- **부트스트랩 (레거시 shim)**: `python3 workflow-source/scripts/bootstrap_workflow_kit.py ...`
- **상태 생성**: `python3 workflow-source/scripts/generate_workflow_state.py ...`
- **테스트 실행**:
  - 개별: `python3 workflow-source/tests/check_<name>.py`
  - 일괄 (CI 동일): `for t in workflow-source/tests/check_*.py; do python3 "$t" || exit 1; done`
  - 패키징: `python3 workflow-source/tools/check_packaging.py`
- **배포 패키지 생성**: `python3 workflow-source/scripts/export_harness_package.py --harness codex --harness opencode`
- **MCP 서버 (안정)**: `PYTHONPATH=workflow-source python3 -m workflow_kit.server.read_only_jsonrpc --stdio-lines`
- **MCP 서버 (SDK)**: `PYTHONPATH=workflow-source python3 -m workflow_kit.server.read_only_mcp_sdk --stdio-sdk`

## 4. 기술 스택

| Layer | Technology |
|---|---|
| Language | Python 3.10+ (3.11+ 권장) |
| Schema/Contracts | Pydantic v2 |
| Async | anyio >= 4.0 |
| Agent Protocol | MCP (Model Context Protocol) Python SDK `mcp[cli]` >= 1.0 |
| Package Build | setuptools >= 68 + wheel |
| Linting | ruff (line-length 100, py310) |
| Type Checking | mypy (non-strict, py310) |
| CI | GitHub Actions, ubuntu-latest, Python 3.11, 52개 smoke 매 push |

## 5. 에이전트 활용 팁
- 코드 수정 시 `workflow-source/workflow_kit/common/`의 유틸리티를 먼저 확인하여 중복 구현을 방지하십시오.
- 새로운 스킬 추가 시 `workflow-source/skills/` 하위의 기존 패키지 구조를 준수하십시오 (`SKILL.md` 6필드 헤더, `scripts/run_*.py` 진입점, `tool_version` 포함).
- 새로운 MCP 서버 추가 시 `MCP.md` 6필드 헤더 + `tool_version` 출력 + `lib/common_utils.py` 의 `make_envelope()` 사용을 준수하십시오.
- 새 하네스 추가 시 `bootstrap_lib/harnesses/__init__.py` 의 `HARNESS_SPECS` 한 줄 + `bootstrap_lib/__main__.py` 의 `register_harness_builder` 한 줄로 끝납니다.
- 자세한 설치·호출 절차는 [`./INSTALLATION_AND_USAGE.md`](./INSTALLATION_AND_USAGE.md) §6-§7 참고.
