# Installation & Usage Guide

- 문서 목적: Standard AI Workflow를 **소스에서 설치해 개발/검증 환경**으로 쓰는 방법을 안내한다.
- 범위: 의존성 설치, 패키지 임포트, 스모크 테스트 실행, bootstrap/demo/MCP 실행, 핵심 워크플로우 호출 예시
- 대상 독자: 워크플로우를 직접 수정·검증하려는 개발자, 패키지 인테그레이션을 시도하는 통합 담당자
- 상태: stable
- 최종 수정일: 2026-06-12
- 관련 문서: [README.md](https://github.com/ykylee/standard_ai_workflow/blob/main/README.md), [QUICKSTART.md](https://github.com/ykylee/standard_ai_workflow/blob/main/QUICKSTART.md), [./DOCUMENT_INDEX.md](./DOCUMENT_INDEX.md), [./CODE_INDEX.md](./CODE_INDEX.md)

> [!NOTE]
> 이 문서는 **개발자/통합 담당자** 관점의 설치·사용 가이드다. 일반 사용자가 미리 빌드된 패키지(`dist/harnesses/<harness>/v*.zip`)를 받아 AI 에이전트에게 적용하는 흐름은 [`QUICKSTART.md`](https://github.com/ykylee/standard_ai_workflow/blob/main/QUICKSTART.md) 를 참고한다.

## 1. 이 문서가 다루는 것 / 다루지 않는 것

### 다루는 것
- 저장소를 clone한 뒤 `workflow-source/` 를 editable mode로 설치하는 방법
- 의존성 (`pydantic`, `anyio`, `mcp[cli]`) 설치
- `workflow_kit` / `bootstrap_lib` 임포트와 기본 사용 예
- 52개 스모크 테스트 (`workflow-source/tests/check_*.py`) 실행 방법
- `bootstrap_workflow_kit.py` 와 `generate_workflow_state.py` 실행
- MCP 서버 (jsonrpc-bridge / stdio-sdk) 실행
- 자주 만나는 문제 해결

### 다루지 않는 것
- 미리 빌드된 zip 패키지(`dist/harnesses/`)로 다른 프로젝트에 적용하는 절차 → [`QUICKSTART.md`](https://github.com/ykylee/standard_ai_workflow/blob/main/QUICKSTART.md)
- 코어 표준 문서(`workflow-source/core/*.md`)의 내용 자체
- 릴리스 절차 → [`docs/RELEASE.md`](./RELEASE.md)
- `workflow-source/core/orchestrator_subagent_contract_v1.md` 의 contract v1 wire format 자체

## 2. 사전 준비

| 항목 | 권장 버전 | 비고 |
| --- | --- | --- |
| OS | macOS / Linux | Windows는 미검증 (CI는 ubuntu-latest) |
| Python | **3.11+** (저장소는 `>=3.10` 선언) | 3.11.15 / 3.12.x / 3.13.x 모두 동작 확인됨 |
| Git | 2.30+ |  |
| 선택 도구 | `make`, `curl`, `unzip` |  |

Python 버전 확인:

```bash
python3 --version
# Python 3.11.x 이상이어야 함 (3.9 이하는 mcp SDK 미지원)
```

저장소 클론:

```bash
git clone https://github.com/ykylee/standard_ai_workflow.git
cd standard_ai_workflow
```

## 3. 설치 경로 — 세 가지

용도에 따라 세 가지 중 하나를 선택한다. **대부분의 개발자는 3.A (editable install) 만으로 충분**하다.

### 3.A. 소스에서 editable 설치 (권장, 개발자용)

`workflow-source/` 안에 두 개의 importable 패키지(`workflow_kit`, `bootstrap_lib`)와 한 개의 CLI shim(`bootstrap_workflow_kit`)이 들어 있다. editable mode로 설치하면 소스 수정사항이 즉시 반영된다.

```bash
cd workflow-source
python3 -m venv .venv          # 별도 venv 권장 (저장소 루트의 .venv 와 충돌 방지)
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[mcp-sdk,dev]"
```

`.[mcp-sdk,dev]` 가 설치하는 것:

- 본 패키지 (`workflow_kit`, `bootstrap_lib`) — editable link
- `mcp[cli]>=1.0` (extras `mcp-sdk`) — MCP SDK stdio server 사용 시 필요
- `pytest`, `ruff`, `mypy` (extras `dev`) — 테스트/린트/타입체크

설치 검증:

```bash
python3 -c "import workflow_kit, bootstrap_lib, mcp; print('ok')"
# ok
```

> [!IMPORTANT]
> **반드시 `workflow-source/` 안에서** `pip install -e .` 를 실행해야 한다. `pyproject.toml` 이 그 안에 있다. 저장소 루트에서 실행하면 editable install 자체는 진행되지만 `cwd` 기준 namespace 해석 때문에 위 §8.6 의 "stale root `workflow_kit/`" 문제가 생길 수 있다.

### 3.B. requirements*.txt 로 런타임만 설치 (CI / 검증자용)

CI (`/.github/workflows/smoke.yml`) 가 그대로 쓰는 경로다. editable 가 아니므로 `workflow_kit` 의 소스 수정이 반영되지 않는다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

이 모드에서 임포트하려면 `PYTHONPATH` 가 필요하다 (editable install 이 아니므로 Python 이 패키지 위치를 모름):

```bash
PYTHONPATH=workflow-source python3 -c "import workflow_kit; print(workflow_kit.__file__)"
# .../standard_ai_workflow/workflow-source/workflow_kit/__init__.py
```

### 3.C. GitHub Release zip 으로 설치 (사용자/통합자용, 가장 간단)

릴리스 페이지에서 `standard-ai-workflow-*.zip` 또는 하네스별 패키지 (`standard-ai-workflow-codex-v*.zip` 등) 를 받아 압축 해제 후 그 안의 wheel 을 설치한다. 자세한 절차는 [`QUICKSTART.md`](https://github.com/ykylee/standard_ai_workflow/blob/main/QUICKSTART.md) §3 참고.

```bash
unzip standard-ai-workflow-codex-v0.6.0-beta.zip
cd standard-ai-workflow-codex-v0.6.0-beta
pip install dist/*.whl       # 또는: pip install -e .
```

## 4. 환경 진단 한 줄

`workflow_kit` 의 빠른 헬스체크:

```bash
python3 -c "
import importlib.metadata as m
import sys
print('python:', sys.version.split()[0])
for pkg in ['pydantic', 'anyio', 'mcp', 'workflow_kit', 'bootstrap_lib']:
    try:
        v = m.version(pkg)
        print(f'  {pkg}=={v}')
    except m.PackageNotFoundError:
        print(f'  {pkg} [MISSING]')
"
```

기대 출력 예 (venv 의존성 상태에 따라 버전은 다를 수 있음):

```text
python: 3.13.7
  pydantic==2.13.3
  anyio==4.13.0
  mcp==1.27.0
  workflow_kit==0.6.0-beta
  bootstrap_lib==0.6.0-beta
```

## 5. 스모크 테스트 실행

저장소에는 52개의 `workflow-source/tests/check_*.py` 가 있다. CI는 매 push 마다 이 전부를 돌린다.

### 5.1. 한꺼번에 전부 돌리기 (CI 와 동일)

CI 는 `pip install -r requirements*.txt` + `PYTHONPATH=workflow-source` 경로를 쓰므로 그 형태를 그대로 흉내낸다. **editable install (3.A) 을 했다면 `PYTHONPATH` 가 없어도 동작**한다.

```bash
# CI 와 동일한 경로 (3.B / requirements.txt)
PYTHONPATH=workflow-source \
  bash -c 'set -e; for t in workflow-source/tests/check_*.py; do echo "=== $t ==="; python3 "$t" || exit 1; done'

# editable install (3.A) 환경 — 더 짧음
bash -c 'set -e; for t in workflow-source/tests/check_*.py; do python3 "$t" || exit 1; done'
```

성공 시 마지막 라인: `=== workflow-source/tests/check_zzz_*.py ===` 후 추가 출력 없음.

### 5.2. 개별 테스트 (개발 중 빠른 피드백)

```bash
# editable install (3.A) 환경 — PYTHONPATH 불필요
python3 workflow-source/tests/check_bootstrap.py
python3 workflow-source/tests/check_contract_v1_multi_component.py
python3 workflow-source/tests/check_wire_guide_v059.py

# 또는 CI 와 동일하게
PYTHONPATH=workflow-source python3 workflow-source/tests/check_contract_v1_multi_component.py
```

핵심 회귀 테스트:

| 테스트 | 검증 범위 |
| --- | --- |
| `check_bootstrap.py` | bootstrap scaffold (4개 하네스 + `--enable-mcp` 포함) |
| `check_contract_v1_*.py` | orchestrator↔sub-agent delegation contract v1 (choose_roles, validate_fanin_output, delegator) |
| `check_wire_guide_v059.py` | wire guide §3/§7/§8/§9 fan-out/in 회귀 (v0.5.9.1) |
| `check_packaging_smoke.py` | wheel packaging 누락 모듈 회귀 (v0.5.7.1) |
| `check_workflow_linter.py` | 문서 정합성 린터 동작 (※ v0.5.0 시점의 경고 baseline 사용) |

> [!IMPORTANT]
> `PYTHONPATH=workflow-source` 가 빠져 있으면 `ModuleNotFoundError: No module named 'workflow_kit'` 가 발생한다. **editable install (3.A) 을 했다면 `PYTHONPATH` 없이도 동작**한다.

### 5.3. 실패가 났을 때

1. 출력의 마지막 5줄을 본다 — 어떤 체크가 실패했는지 거의 항상 거기 있다.
2. 같은 명령을 한 번 더 돌린다 — 가끔 일시적인 파일 시스템 이슈.
3. 깨진 테스트가 `check_workflow_linter.py` 라면, **이 문서 작성 시점(v0.5.10) 기준** 사전부터 `warning` 을 반환하는 알려진 케이스다. 의도된 동작이므로 그대로 둔다.
4. 위 방법으로 안 풀리면 `git log --oneline -5 -- workflow-source/tests/check_<name>.py` 로 최근 변경 이력을 본 뒤 [`./RELEASE.md`](./RELEASE.md) 의 triage 절차로 넘어간다.

## 6. `workflow_kit` 핵심 API 빠른 사용법

`workflow_kit` 은 두 가지 큰 표면을 가진다 — **공통 헬퍼** (`workflow_kit.common.*`) 와 **contract v1** (`workflow_kit.contract_v1.*`).

### 6.1. 공통 헬퍼 (`workflow_kit.common.*`)

`workflow_kit/common/` 은 30여 개의 submodule 로 구성되어 있다. 패키지 `__init__.py` 가 비어 있으므로 `from workflow_kit.common import paths` 처럼은 안 되고, 항상 submodule 경로를 명시해야 한다.

자주 쓰는 진입점:

```python
# 각각 별도 submodule
from workflow_kit.common import paths            # 경로 해석 (workflow-source/, ai-workflow/, docs/ 등)
from workflow_kit.common import project_docs     # docs/PROJECT_PROFILE.md 파서
from workflow_kit.common import workflow_state   # state.json / session_handoff.md / work_backlog.md 헬퍼
from workflow_kit.common import runner           # 통합 runner (skill/MCP 호출 표준 패턴)
from workflow_kit.common import errors           # 표준 에러 envelope (status, error_code, source_context)
from workflow_kit.common import output_contracts # 출력 JSON contract 검증
from workflow_kit.common import reconcile        # 문서 정합성 / merge-doc-reconcile 의 코어
from workflow_kit.common import scaffold         # 자동 검증 scaffold 헬퍼
from workflow_kit.common import doc_sync         # docs 동기화 헬퍼
```

> 잘못된 import 예: `from workflow_kit.common import paths, runner, errors` → `ImportError: cannot import name 'paths' from 'workflow_kit.common'`. **반드시 한 줄에 하나씩** submodule 경로로 import 한다.

### 6.2. contract v1 (`workflow_kit.contract_v1.*`)

v0.5.4 부터 메인 orchestrator 와 sub-agent 사이의 위임은 `workflow-source/core/orchestrator_subagent_contract_v1.md` 의 contract v1 을 따른다. Pydantic v2 기반.

```python
from workflow_kit.contract_v1 import choose_roles        # fan-out 시 sub-agent 역할 선택
from workflow_kit.contract_v1 import validate_fanin_output  # fan-in 시 sub 결과 검증
from workflow_kit.contract_v1 import delegator           # delegate_to_subagent() — wire format v1
```

- `choose_roles(parent_intent, candidates)` — fan-out 시 sub-agent 역할 선택
- `validate_fanin_output(parent_id, sub_results)` — fan-in 시 sub 결과 검증
- `delegator.delegate_to_subagent(...)` — Pydantic envelope 으로 sub 위임

스펙은 [`workflow-source/core/orchestrator_subagent_contract_v1.md`](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/orchestrator_subagent_contract_v1.md) 와 [`workflow-source/core/orchestrator_contract_v1_wire_guide.md`](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/orchestrator_contract_v1_wire_guide.md) 참고.

### 6.3. 임포트만 검증하는 한 줄 스모크

`workflow_kit.common` 은 submodule 별로, `workflow_kit.contract_v1` 은 `__init__.py` 가 re-export 하므로 한 줄에 여러 이름 가능.

> [!WARNING]
> 저장소 루트(`/home/yklee/repos/standard_ai_workflow`)에서 실행하면 §8.7 의 namespace shadowing 때문에 **반드시 실패**한다. `/tmp` 등 저장소 밖에서 실행하거나, `cd workflow-source` 안에서 실행한다.

```bash
# 저장소 밖에서 (권장 — CWD 영향 없음)
cd /tmp && python3 -c "
import workflow_kit
from workflow_kit.common import paths, runner, errors
from workflow_kit.contract_v1 import choose_roles, validate_fanin_output, delegator
print('workflow_kit:', workflow_kit.__file__)
print('paths:', paths.__file__)
print('all critical imports OK')
"
# workflow_kit: .../standard_ai_workflow/workflow-source/workflow_kit/__init__.py
# paths: .../standard_ai_workflow/workflow-source/workflow_kit/common/paths.py
# all critical imports OK
```

검증의 핵심은 `workflow_kit.__file__` 이 `workflow-source/workflow_kit/__init__.py` 로 끝나는지다. 만약 `None` 이거나 다른 경로가 나오면 §8.7 의 namespace shadowing 문제.

## 7. 부트스트랩 / 상태 생성 / MCP 실행

### 7.1. 부트스트랩 (다른 저장소에 워크플로우 도입)

```bash
# 옵션 A: 신 패키지 (path-style, 권장)
python3 -m bootstrap_lib \
  --target-root /tmp/sample-repo \
  --project-slug sample_api \
  --project-name "Sample API" \
  --harness codex --harness opencode --harness antigravity \
  --copy-core-docs

# 옵션 B: 레거시 CLI shim (동일 기능)
python3 workflow-source/scripts/bootstrap_workflow_kit.py \
  --target-root /tmp/sample-repo \
  --project-slug sample_api \
  --project-name "Sample API" \
  --harness codex \
  --copy-core-docs

# 옵션 C: CI / 스크립트 환경 (--no-interactive 필수)
# 비대화형 환경에서 --harness 미지정 시 SystemExit(1) + harness 목록 fail-fast
# v0.5.8+ 의 interactive picker 는 TTY 미감지 시 자동 skip 됨. --no-interactive 는 명시적.
python3 -m bootstrap_lib \
  --target-root "$REPO" \
  --project-slug "$SLUG" \
  --harness opencode \
  --no-interactive \
  --adoption-mode existing \
  --copy-core-docs
```

핵심 옵션:

- `--harness <name>` — `codex` / `opencode` / `gemini-cli` / `antigravity` / `minimax-code` (반복 가능)
- `--adoption-mode {new,existing}` — `existing` 은 `repository_assessment.md` 도 생성
- `--copy-core-docs` — `core/*.md` 를 타겟 저장소에 복사
- `--no-interactive` — 비대화형 환경(CI/파이프라인/자동 에이전트) 에서 interactive picker 자동 실행을 비활성화. `--harness` 미지정 시 fail-fast.
- `--enable-mcp` — 하네스별 MCP config 스니펫 동시 emit
- `--mcp-bridge {jsonrpc-bridge,stdio-sdk}` — MCP 전송 방식 (default: `jsonrpc-bridge`, 안정; `stdio-sdk` 는 정식 SDK 호환)

`--enable-mcp` 로 emit 되는 파일 위치는 [`QUICKSTART.md`](https://github.com/ykylee/standard_ai_workflow/blob/main/QUICKSTART.md) §5 표 참고.

### 7.2. 상태 동기화 (`state.json` 재생성)

```bash
python3 workflow-source/scripts/generate_workflow_state.py \
  --project-profile-path docs/PROJECT_PROFILE.md \
  --session-handoff-path ai-workflow/memory/session_handoff.md \
  --work-backlog-index-path ai-workflow/memory/work_backlog.md \
  --output-path ai-workflow/memory/state.json
```

`backlog-update`, `merge-doc-reconcile` 등의 스킬이 내부적으로 같은 헬퍼를 호출한다. 수동 호출은 보통 필요 없지만, 손으로 `state.json` 을 망가뜨렸을 때 복구용으로 쓴다.

### 7.3. MCP 서버 실행

**A. jsonrpc-bridge (안정, default)** — 정식 MCP SDK 없이 동작:

```bash
PYTHONPATH=workflow-source \
  python3 -m workflow_kit.server.read_only_jsonrpc --stdio-lines
```

**B. stdio-sdk (실험적)** — 정식 `mcp` SDK 필요 (`pip install -e ".[mcp-sdk]"` 선행):

```bash
PYTHONPATH=workflow-source \
  python3 -m workflow_kit.server.read_only_mcp_sdk --stdio-sdk
```

실제 stdio round-trip 검증은 `workflow-source/tests/check_read_only_mcp_sdk_stdio.py` 로 확인한다.

### 7.4. 데모 워크플로우 실행

스킬 + MCP + runner 가 함께 도는 end-to-end 데모:

```bash
# 스킬 데모
python3 workflow-source/scripts/run_demo_workflow.py

# 기존 프로젝트 온보딩 데모
python3 workflow-source/scripts/run_existing_project_onboarding.py

# 다중 에이전트 오케스트레이션 데모
python3 workflow-source/scripts/orchestration_demo.py
```

각 데모의 기대 출력 형태는 `workflow-source/examples/output_samples/` 에 있다.

## 8. 자주 만나는 문제

### 8.1. `ModuleNotFoundError: No module named 'workflow_kit'`

- editable install 을 안 했고 (3.A) `PYTHONPATH` 도 안 잡혀 있다. 둘 중 하나를 한다.
- 또는 3.B 경로인데 `pip install` 시점이 너무 오래되어 패키지가 누락됐다. `pip install -r requirements.txt` 를 다시.

### 8.2. `pip install -e .` 가 패키지를 못 찾는다

- cwd 가 `workflow-source/` 가 맞는지 확인한다. `pyproject.toml` 이 그 안에 있다.
- 빌드 시스템: setuptools>=68.0 + wheel. `python3 -m pip install --upgrade pip setuptools wheel` 먼저.

### 8.3. `mcp` import 가 `ImportError` 를 던진다

- mcp SDK 는 Python 3.10+ 필요. `python3 --version` 확인.
- editable install 의 extras 가 `mcp-sdk` 가 빠져 있다. `pip install -e ".[mcp-sdk]"` 로 재설치.

### 8.4. macOS Homebrew Python 버전 충돌

저장소 검증은 `/opt/homebrew/bin/python3.11` (macOS) / CI 의 `python 3.11` 기준. 로컬에 3.13 이 있고 mcp SDK 가 import 안 되면:

```bash
brew install python@3.11
/opt/homebrew/bin/python3.11 -m venv .venv-311
.venv-311/bin/python -m pip install -e ".[mcp-sdk,dev]"
```

### 8.5. `check_workflow_linter.py` 가 `warning` 을 반환

- **v0.5.10 기준 사전부터 알려진 동작**이다. fail 이 아니라 warning 이면 테스트는 의도된 통과다.
- 진짜로 fail (`status: "error"`) 이면 [`workflow-source/skills/workflow-linter/`](https://github.com/ykylee/standard_ai_workflow/tree/main/workflow-source/skills/workflow-linter/) 의 진짜 린터를 직접 돌려본다.

### 8.6. `ai-workflow/` 가 비어 있다

- `ai-workflow/` 의 하위 (`scripts/`, `skills/`, `workflow_kit/`, `mcp_servers/`, `examples/`) 는 `.gitignore` 로 제외되어 있다. 첫 체크아웃 후에는 부트스트랩 한 번 실행해 로컬에 생성:

```bash
python3 workflow-source/scripts/bootstrap_workflow_kit.py \
  --target-root . \
  --project-slug standard-ai-workflow \
  --project-name "Standard AI Workflow" \
  --harness antigravity \
  --adoption-mode existing \
  --copy-core-docs \
  --force
```

### 8.7. `workflow_kit` 이 import 되는데 `__file__` 이 `None` 이거나 `workflow-source/` 가 아닌 다른 경로

- 저장소 **루트에 옛날 `workflow_kit/` 폴더** 가 남아 있어서 namespace 가 그것을 가리키는 경우다. `git log --diff-filter=D -- workflow_kit/` 로 확인: commit `96431f1 refactor(workflow): separate source from runtime layer` (v0.5.2) 이전의 잔재.
- v0.5.2 이후 정식 위치는 `workflow-source/workflow_kit/` 다. 루트의 잔존 폴더는 **이동된 것이 아니라 옛 스냅샷**이므로 안전하게 삭제 가능:

```bash
git log --oneline -- workflow_kit/ | head -3
# 96431f1 refactor(workflow): separate source from runtime layer
# (이전 커밋들 — workflow_kit 이 workflow-source/ 아래로 이동)

# 안전한 확인 후 정리
rm -rf workflow_kit/
# 또는 stash: git stash --include-untracked -- workflow_kit/

# 그 다음 editable install 을 §3.A 절차로 다시
cd workflow-source
pip install -e ".[mcp-sdk,dev]"
```

- 진단 명령: §6.3 의 한 줄 스모크에서 `workflow_kit.__file__` 이 `None` 이거나 `workflow-source/` 가 아닌 경로로 나오면 이 문제다.

## 9. 다음 단계

이 문서로 설치/기본 사용이 끝났다면, 아래 문서로 진행한다.

| 하고 싶은 것 | 참고 문서 |
| --- | --- |
| 미리 빌드된 zip 으로 다른 프로젝트에 적용 | [`QUICKSTART.md`](https://github.com/ykylee/standard_ai_workflow/blob/main/QUICKSTART.md) |
| contract v1 wire format 의 모든 필드 | [`workflow-source/core/orchestrator_subagent_contract_v1.md`](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/orchestrator_subagent_contract_v1.md) |
| 다중 에이전트 토폴로지 (orchestrator / doc / code / validation worker) | [`workflow-source/core/workflow_agent_topology.md`](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/workflow_agent_topology.md) |
| 스킬 카탈로그 | [`workflow-source/core/workflow_skill_catalog.md`](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/workflow_skill_catalog.md) |
| MCP 후보 카탈로그 | [`workflow-source/core/workflow_mcp_candidate_catalog.md`](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/workflow_mcp_candidate_catalog.md) |
| 릴리스 절차 (GitHub Release zip 생성) | [`./RELEASE.md`](./RELEASE.md) |
| 마지막 릴리스 노트 | [`workflow-source/releases/Beta-v0.6.0.1.md`](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/releases/Beta-v0.6.0.1.md) |
| 변경 이력 / 로드맵 | [`workflow-source/core/workflow_kit_roadmap.md`](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/workflow_kit_roadmap.md) |
