# Standard AI Workflow Quickstart

- 문서 목적: Standard AI Workflow를 신규 프로젝트에 빠르게 도입하는 방법을 안내한다.
- 범위: 프로젝트 초기화, 환경 설정, 첫 세션 시작 가이드
- 대상 독자: AI 에이전트와 협업하려는 개발자
- 상태: beta
- 최종 수정일: 2026-06-12
- 관련 문서: `ai-workflow/README.md`, `AGENTS.md`, `GEMINI.md`, `MiniMax.md`, [`docs/INSTALLATION_AND_USAGE.md`](docs/INSTALLATION_AND_USAGE.md) (개발자용)

이 문서는 **Standard AI Workflow**를 여러분의 프로젝트에 5분 만에 도입하여 AI 에이전트와 체계적으로 Peer Programming을 시작하는 방법을 안내합니다.

## 1. 목적

- AI 에이전트가 프로젝트의 컨텍스트를 스스로 이해하고 관리하도록 합니다.
- 작업 이력(Backlog), 세션 상태(Handoff), 프로젝트 프로파일을 표준화된 방식으로 유지합니다.
- 복잡한 작업(문서 동기화, 테스트 검증 등)을 전용 스킬(Skill)과 MCP 도구로 자동화합니다.

## 2. 준비물

- **Python 3.10+** (3.11+ 권장): 워크플로우 도구 실행에 필요합니다. (3.9 이하는 `mcp` SDK 미지원)
- **에이전트 하네스**: 다음 중 하나를 선택합니다.
  - **MiniMax Code** (권장, Mavis 오케스트레이터/워커 오버레이 포함)
  - Codex CLI
  - OpenCode CLI
  - Gemini CLI
  - Antigravity
  - pi-dev
  - **배포 패키지**: `dist/harnesses/<선택한 하네스>/v0.6.5-beta/` 아래의 압축 파일.

## 3. 3단계 도입 가이드

### 1단계: 프로젝트 초기화

배포 패키지의 `bundle/` 디렉토리 내용을 프로젝트 루트에 복사합니다.

```bash
# MiniMax Code 패키지 (권장)
cp -r /path/to/bundle/ai-workflow .
cp /path/to/bundle/AGENTS.md .
cp /path/to/bundle/MiniMax.md .

# 다른 하네스
cp -r /path/to/bundle/ai-workflow .
cp /path/to/bundle/<HARNESS_ENTRIES> .   # 예: GEMINI.md, ANTIGRAVITY.md
```

- `ai-workflow/`: 워크플로우의 상태와 메타데이터가 저장되는 공간입니다.
- `AGENTS.md`, `GEMINI.md`, `MiniMax.md` 등: 선택한 하네스의 진입점입니다.

### 2단계: 의존성 설치 및 환경 설정

워크플로우 스크립트 실행을 위해 가상환경을 구축하고 필수 라이브러리를 설치합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### 3단계: 첫 세션 시작

선택한 하네스 세션을 시작하고 AI 에이전트에게 워크플로우 도입을 알립니다.

```bash
# MiniMax Code / Codex / OpenCode / Gemini CLI / Antigravity 세션 시작 시
"프로젝트 루트의 <HARNESS_ENTRY>를 읽고 워크플로우 세션을 시작해줘."
```

## 4. 핵심 워크플로우 도구 (Skills)

워크플로우가 안정되면 에이전트가 다음 도구들을 사용하여 작업을 보조합니다:

- **`session-start`**: 세션 시작 시 현재 상태 복원 및 작업 방향 제안.
- **`backlog-update`**: 새 작업 등록 및 진행 중인 작업 상태 업데이트.
- **`doc-sync`**: 코드 변경에 따른 관련 문서(Handoff, Profile 등) 자동 동기화 추천.
- **`validation-plan`**: 변경 사항 검증을 위한 테스트 계획 수립 및 실행.
- **`merge-doc-reconcile`**: 문서/상태 충돌 시 자동 조정 제안.
- **`workflow-linter`**: 문서 정합성/메타데이터/링크 무결성 자동 검사.
- **`code-index-update`**: 코드 인덱스 갱신 (v0.5.7+).
- **`project-status-assessment`**: 프로젝트 상태 자동 진단 (v0.5.7+).
- **`git-conflict-resolver`**: 컨텍스트 기반 Git 충돌 해결 (v0.5.7+).
- **`robust_patcher`**: 정밀 코드 편집 엔진 (v0.5.7+).
- **`automated-repro-scaffold`**: reproduction scaffold 생성 (v0.5.7+).

## 5. MCP 도구 사용 (선택 사항)

`python3 -m bootstrap_lib` (또는 레거시 `bootstrap_workflow_kit.py`) 가 각 하네스별 MCP config 스니펫을 자동으로 생성할 수 있다. 도입 시점에 한 번만 실행하면 된다.

```bash
# bootstrap 시 --enable-mcp 추가 (v0.5.2+ 권장 진입점)
python3 -m bootstrap_lib \
  --target-root <project_root> \
  --project-slug <slug> \
  --project-name "<name>" \
  --harness <harness> \
  --adoption-mode existing \
  --copy-core-docs \
  --enable-mcp                       # ← 이 한 줄
```

v0.5.8 부터 TTY 환경에서 `--harness` 미지정 시 interactive picker 가 자동 동작한다. 비대화형 환경 (CI, 스크립트) 에서는 `--harness` 명시가 필수.

생성되는 파일:

| 하네스 | 경로 | 스키마 |
| --- | --- | --- |
| Codex | `<root>/.codex/mcp.toml` | TOML |
| OpenCode | `<root>/mcp.opencode.json` | JSON (`mcp` 키) |
| Gemini CLI | `<root>/.gemini/mcp.json` | JSON (`mcpServers` 키) |
| Antigravity | `<root>/antigravity.mcp.json` | JSON (`mcpServers` 키) |
| MiniMax Code | `<root>/.minimax/mcp.json` | JSON (`mcp_servers` 키) |
| pi-dev | `<root>/.pi-dev/mcp.json` | JSON (`mcpServers` 키) |

전역 (사용자 홈) 에 등록하려면 bootstrap 출력 파일을 그대로 옮기거나 `mcp_servers` 블록을 `~/.codex/config.toml` / `~/.gemini/settings.json` / `~/.minimax/mcp.json` 등에 merge. 자세한 가이드: [`workflow-source/core/mcp_installation_by_harness.md`](workflow-source/core/mcp_installation_by_harness.md)

전송 방식 (transport) 선택:

- `--mcp-bridge jsonrpc-bridge` (default, 안정) — `python3 -m workflow_kit.server.read_only_jsonrpc --stdio-lines`
- `--mcp-bridge stdio-sdk` (실험적) — `python3 -m workflow_kit.server.read_only_mcp_sdk --stdio-sdk`. 정식 mcp SDK 호환이 필요한 경우에만.

정식 MCP SDK가 설치된 환경에서는 SDK stdio server 도 직접 띄울 수 있다:

```bash
python3 ai-workflow/workflow_kit/server/read_only_mcp_sdk.py --stdio-sdk
```

## 6. 하네스별 추가 가이드

각 하네스별 overlay 적용 방법은 다음 문서를 참고하세요:

- MiniMax Code: [`workflow-source/harnesses/minimax-code/README.md`](./workflow-source/harnesses/minimax-code/README.md)
- Codex: [`workflow-source/harnesses/codex/README.md`](./workflow-source/harnesses/codex/README.md)
- OpenCode: [`workflow-source/harnesses/opencode/README.md`](./workflow-source/harnesses/opencode/README.md)
- Gemini CLI: [`workflow-source/harnesses/gemini-cli/README.md`](./workflow-source/harnesses/gemini-cli/README.md)
- Antigravity: [`workflow-source/harnesses/antigravity/README.md`](./workflow-source/harnesses/antigravity/README.md)

---

더 자세한 내용은 `ai-workflow/README.md`와 [`workflow-source/harnesses/`](./workflow-source/harnesses/)를 참고하세요.
