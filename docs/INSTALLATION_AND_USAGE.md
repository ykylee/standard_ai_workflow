# Installation & Usage Guide

- 문서 목적: Standard AI Workflow를 **소스에서 설치해 개발/검증 환경**으로 쓰는 방법을 안내한다.
- 범위: 의존성 설치, 패키지 임포트, 스모크 테스트 실행, bootstrap/demo/MCP 실행, 핵심 워크플로우 호출 예시
- 대상 독자: 워크플로우를 직접 수정·검증하려는 개발자, 패키지 인테그레이션을 시도하는 통합 담당자
- 상태: stable (v1.6.0 기준; 일부 본문 예시는 v0.5.10 시점 baseline 으로 표기, 동작 자체는 v1.1.6 과 정합)
- 최종 수정일: 2026-08-14 (§7.0 Grok Build 플러그인 설치 경로 추가)
- 관련 문서: [README.md](https://github.com/ykylee/standard_ai_workflow/blob/main/README.md), [QUICKSTART.md](https://github.com/ykylee/standard_ai_workflow/blob/main/QUICKSTART.md), [./DOCUMENT_INDEX.md](./DOCUMENT_INDEX.md), [./CODE_INDEX.md](./CODE_INDEX.md), [Workflow Kit Roadmap](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/workflow_kit_roadmap.md)

> [!NOTE]
> 이 문서는 **개발자/통합 담당자** 관점의 설치·사용 가이드다. 일반 사용자가 미리 빌드된 패키지(`dist/harnesses/<harness>/v*.zip`)를 받아 AI 에이전트에게 적용하는 흐름은 [`QUICKSTART.md`](https://github.com/ykylee/standard_ai_workflow/blob/main/QUICKSTART.md) 를 참고한다.

## 1. 이 문서가 다루는 것 / 다루지 않는 것

### 다루는 것
- 저장소를 clone한 뒤 `workflow-source/` 를 editable mode로 설치하는 방법
- 의존성 (`pydantic`, `anyio`, `mcp[cli]`) 설치
- `workflow_kit` (하위: `workflow_kit.bootstrap_lib`) 임포트와 기본 사용 예
- 275개 스모크 테스트 (`workflow-source/tests/check_*.py`) 실행 방법 (v1.1.6+ 정합)
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
| OS | Linux / macOS / Windows | **지원 tier** (v1.1.8+): Linux = 전량 smoke (CI 2축) · macOS = CLI probe (CI, `os-matrix.yml`) + 전량 2축 (darwin 실측 2026-08-11) · Windows = CLI probe (CI — wk 핵심 명령 + MCP 브리지; 전량 smoke 이식은 별건) |
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

> **CLI(`wk`)만 쓰는 소비자의 권장 경로 (v1.1.7+)**: uv 또는 pipx 로 GitHub Release
> 의 wheel 을 격리 설치한다 — 전용 venv + PATH 등록이 자동이다. v1.2.0 부터
> wheel top-level 은 `workflow_kit` 하나라 (구경로 shim `tools`/`bootstrap_lib`
> 는 2nd deprecation cycle 로 drop) site-packages 충돌 여지 자체가 없다
> (근거: [`planning/cli-distribution-review-2026-08.md`](./planning/cli-distribution-review-2026-08.md)).
>
> ```bash
> uv tool install https://github.com/ykylee/standard_ai_workflow/releases/download/v1.1.8-beta/standard_ai_workflow-1.1.8-py3-none-any.whl
> # 또는: pipx install <같은 URL>
> # 또는 tag 에서 직접: uv tool install "git+https://github.com/ykylee/standard_ai_workflow@v1.1.8-beta#subdirectory=workflow-source"
> wk --help
> ```

### 3.A. 소스에서 editable 설치 (권장, 개발자용)

`workflow-source/` 안에 importable 패키지 `workflow_kit` (하위 `workflow_kit.bootstrap_lib`, `workflow_kit.tools` 포함)와 한 개의 레거시 CLI shim(`bootstrap_workflow_kit`)이 들어 있다. editable mode로 설치하면 소스 수정사항이 즉시 반영된다.

```bash
cd workflow-source
python3 -m venv .venv          # 별도 venv 권장 (저장소 루트의 .venv 와 충돌 방지)
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[mcp-sdk,dev]"
```

`.[mcp-sdk,dev]` 가 설치하는 것:

- 본 패키지 (`workflow_kit`) — editable link
- `mcp[cli]>=1.0` (extras `mcp-sdk`) — MCP SDK stdio server 사용 시 필요
- `pytest`, `ruff`, `mypy` (extras `dev`) — 테스트/린트/타입체크

설치 검증:

```bash
python3 -c "import workflow_kit, workflow_kit.bootstrap_lib, mcp; print('ok')"
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
for pkg in ['pydantic', 'anyio', 'mcp', 'workflow_kit']:
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
```

## 5. 스모크 테스트 실행

저장소에는 275개의 `workflow-source/tests/check_*.py` 가 있다. CI는 매 push 마다 이 전부를 돌린다.

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
> 저장소 루트(`~/repos/standard_ai_workflow`)에서 실행하면 §8.7 의 namespace shadowing 때문에 **반드시 실패**한다. `/tmp` 등 저장소 밖에서 실행하거나, `cd workflow-source` 안에서 실행한다.

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

### 7.0. 플러그인 설치 (권장 경로 — Codex / Claude Code / Gemini CLI / Grok Build / pi.dev)

소비 프로젝트가 워크플로우를 얻는 **권장 경로**다 (소유자 판정 2026-08-13,
근거: [`planning/plugin-transition-plan-2026-08.md`](./planning/plugin-transition-plan-2026-08.md)
§3-P5). 스킬 4종 (session-start / backlog-update / doc-sync / session-end) +
read-only MCP 번들 + 세션 경계 hook 2종이 설치 1명령으로 들어온다.

```bash
# Codex — GitHub Release의 Codex ZIP을 푼 뒤 marketplace로 등록하고 설치
unzip standard-ai-workflow-codex-plugin-<VERSION>.zip
codex plugin marketplace add ./standard-ai-workflow-codex-plugin-<VERSION>
codex plugin add standard-ai-workflow@standard-ai-workflow

# Claude Code — marketplace 등록 + 설치
claude plugin marketplace add ykylee/standard_ai_workflow
claude plugin install standard-ai-workflow@standard-ai-workflow

# 업데이트 (plugin update 는 풀 id `<name>@<marketplace>` 가 필요하다 — 실측)
claude plugin marketplace update standard-ai-workflow
claude plugin update standard-ai-workflow@standard-ai-workflow   # 재시작 후 적용
```

```bash
# Gemini CLI — 확장 루트가 저장소의 plugin/ 이므로 로컬 경로로 설치한다
# (GitHub URL 설치는 manifest 가 저장소 루트에 있어야 해 성립하지 않는다)
git clone https://github.com/ykylee/standard_ai_workflow.git
gemini extensions install ./standard_ai_workflow/plugin --consent
# 개발 추적이 필요하면 install 대신: gemini extensions link ./standard_ai_workflow/plugin
```

```bash
# Grok Build — 저장소 루트가 marketplace (.claude-plugin/marketplace.json 동등물)
# 훅은 hooks/hooks.json 관례 경로. 설치는 --trust 가 있어야 MCP/훅이 활성화된다
# (실측 2026-08-14: 스킬 4 + read-only MCP + hooks).
grok plugin marketplace add ykylee/standard_ai_workflow
grok plugin install standard-ai-workflow --trust

# 로컬 체크아웃
grok plugin install ./plugin --trust
```

```bash
# pi.dev (pi-coding-agent) — marketplace.json 대신 npm/git 패키지 방식
# (plugin/package.json 의 `pi` manifest + `pi-package` keyword 가 갤러리 등록 단위)
pi install ./plugin
# 또는 태그 고정 설치:
pi install git:github.com/ykylee/standard_ai_workflow@v1.2.0
```

전제 두 가지:

- **플러그인은 `wk` / Python 의존을 대신 설치해 주지 않는다** (전환 원칙 4).
  스킬·hook 이 부르는 메모리 갱신 명령은 §3 의 uv/pipx wheel 설치가 선행돼야
  돌고, 없으면 SessionStart hook 이 설치 안내를 출력한다 (조용한 실패 없음).
- 설치 선언은 user settings (`~/.claude/settings.json` 의
  `extraKnownMarketplaces` / `enabledPlugins`) 에 산다 — settings 를 재작성하는
  외부 도구가 있으면 선언이 소실될 수 있다 (실측 1회). 그 경우 위 두 명령으로
  재설치한다.

bootstrap (아래 7.1) 은 **플러그인 미지원 하네스와 오프라인 환경**, 그리고
진입점 파일(CLAUDE.md 등)에 대한 규칙 상시 주입 담당으로 병행 유지된다.

### 7.0.0. 설치 전 전제 — `wk doctor` 의 `preflight` 절

**설치 명령을 치기 전에** 무엇이 있어야 하는지 한 번에 본다:

```bash
wk doctor                 # preflight 절이 채널별 설치 가능 여부를 보고
wk doctor --json          # 기계가 읽는 형태 (`.preflight.ready_channels`)
```

| 채널 | 측정하는 전제 (실행 파일) | 선언만 하는 전제 (미측정) |
|---|---|---|
| **claude-code** | `claude` · `wk` · `python3` | GitHub marketplace 도달 (네트워크) |
| **codex** | `codex` · `unzip` · `wk` · `python3` | GitHub Release 의 Codex ZIP 을 미리 내려받아 둘 것 |
| **gemini-cli** | `gemini` · `git` · `wk` · `python3` | 저장소 클론 (확장 루트가 `plugin/` 이라 로컬 경로 설치) |
| **grok-build** | `grok` · `wk` · `python3` | GitHub marketplace 도달 (네트워크) · `--trust` 없이는 MCP·훅이 비활성 |
| **pi-dev** | `pi` · `wk` · `python3` | 로컬 경로 또는 git 태그 지정 |
| **bootstrap** | `python3` (win32 는 `python` 으로 잰다) | PEP 668 인터프리터면 venv 필요 (§7.1) |

**두 열을 섞지 않는다.** 왼쪽은 `shutil.which` 로 실제로 재고, 오른쪽은 재지
않고 적어만 둔다 — 네트워크 도달성을 탐침이 "모름" 인 채 통과로 세면 그게
거짓 안심이 된다 (이 저장소의 규칙: *모름 ≠ 안전*). 그래서 `installable: true`
는 "실행 파일 전제는 충족" 이라는 뜻이지 "설치가 성공한다" 는 뜻이 아니다.

`wk` 와 `python3` 이 모든 플러그인 채널의 공통 전제인 이유: 스킬이 지시하는
메모리 갱신 명령은 `wk` 로 돌고 read-only MCP 서버는 `python3 -m
workflow_kit.server…` 로 뜬다. 둘 중 하나가 없으면 **설치는 성공해도 기능이
없는 상태**가 된다.

플랫폼 주의 (main-017): **bootstrap 채널만** 인터프리터 이름을 플랫폼으로
해석한다 (win32 는 `python` — bootstrap 이 emit 하는 MCP command 도 같은
정본을 따라 win32 에서 `python` 을 쓴다). 플러그인 채널들의 `python3` 는
win32 에서도 문자 그대로다 — 플러그인 payload 의 `mcp.json` 이 `python3` 를
체크인하기 때문이다 (체크인 산출물은 호스트 독립, 해시 고정). Windows 에서
플러그인 채널을 쓰려면 `python3` 별칭이 PATH 에 있어야 한다.

> 이 표는 손 목록이 아니다. `workflow_kit.deploy_doctor.CHANNEL_PREREQUISITES`
> 가 정본이고 `check_installation_usage` 가 복제를 검출한다 (컨셉 §2 선언 계약).

### 7.0.1. 설치 뒤 확인 — `wk doctor` (post-apply 탐침)

**설치 명령의 성공은 설치의 성공이 아니다.** 무엇이 · 어떤 버전으로 · 어느
스코프에 깔렸는지 한 명령으로 본다:

```bash
wk doctor                 # 사람이 읽는 절별 보고
wk doctor --json          # 기계가 읽는 형태
wk doctor --strict        # 발견이 있으면 rc 1 (CI 용)
```

7절: **environment** (venv·PEP 668·`wk` PATH·`workflow_kit` import) ·
**preflight** (채널별 설치 전제, §7.0.0) · **project_scope** (하네스별 산출물과
버전 마커) · **global_scope** (하네스별 설치 선언의 거주지) · **drift** (낡은
마커, 스코프 간 어긋남) · **content_drift** (설치 사본의 페이로드 해시 대조) ·
**runtime_load** (실행 중 호스트가 이 설치를 봤는가).

계약 셋을 기억한다:

- **report-only** — 아무것도 쓰지 않는다. 양쪽 기설치는 **오류가 아니라 상태**이고,
  어느 쪽도 임의로 지우지 않는다 (컨셉 §5.2). 제거는 사용자 결정이다.
- **기본 rc 0** — 발견은 보고이지 실패가 아니다. CI 에 걸 때만 `--strict`.
- **존재는 적용이 아니다** — kit 소유 표식(버전 마커, 컨셉 §3)이 있는 것만
  "적용됨" 으로 센다. 마커 없이 파일만 있는 하네스는 *후보*로 따로 보고한다
  (다른 도구가 쓴 `AGENTS.md` 하나가 5개 하네스를 적용됨으로 만든 실측이 있다).

**내용 드리프트도 본다** (2026-08-18+). 마커 비교는 **버전이 같고 내용만 낡은**
경우를 원리적으로 못 잡는다 — 2026-08-16 에 Codex 플러그인이 정확히 그
상태였다(`1.2.0` 동일, 페이로드만 구버전). 그래서 `content_drift` 절이 설치
사본을 **정본 페이로드 해시**와 대조한다. 정본은 생성기와 같은 함수이고,
기대 파일 집합은 채널별로 파생된다(채널마다 담는 것이 다르다). 어긋남이
보고되면 복구 절차는 §7.0.2 의 복구 열을 따른다.

**`in_sync` 는 "쓸 수 있음" 이 아니다** (2026-08-20 실측). 이 절이 재는 것은
*파일이 같은가* 이지 *하네스가 그것을 실제로 노출하는가* 가 아니다. 둘은 갈릴 수
있고 실제로 갈렸다 — Claude Code 설치본의 `skills/` 4종이 정본과 in-sync 였고
`claude plugin details` 도 `Skills (4)` 로 셌는데, **세션에는 그중 하나도 로드되지
않았다** (`Unknown skill: standard-ai-workflow:doc-sync`). 설치·활성화·파일 실재·
인벤토리까지 전부 통과하고도 쓸 수 없었다.

**그 사례의 원인은 규명됐다 — 시간이었다** (같은 날 재실측). 호스트 프로세스가
**설치보다 35시간 먼저 시작**했고, 플러그인은 프로세스 시작 때 로드된다. 대조
실험이 결론을 고정한다: 같은 저장소 cwd 에서 `claude -p`(새 프로세스)를 띄우면
플러그인 스킬 4종이 **전부 뜬다**. 이름 충돌도, 매니페스트 파손도 아니었다.

> **오진의 원인은 잰 *단위*였다.** 처음에는 설치 시각을 *대화(session)* 시작
> 시각과 대조해 "설치가 21시간 앞선다" 며 이 가설을 기각했다. 그런데 `/clear` 는
> 대화만 새로 열 뿐 **프로세스를 재시작하지 않는다** — 대화는 설치 뒤에 시작했고
> 프로세스는 설치 앞에 시작해 있었다. **세션이 아니라 프로세스를 재야 한다.**
> 값싼 방증 하나: 실행 중 프로세스의 버전과 `claude --version`(새 프로세스)이
> 어긋나 있으면 그 프로세스는 이미 디스크보다 낡았다.

그래서 이 조건은 이제 **잰다** — `runtime_load` 절이 설치 시각(claude-code 는
`installed_plugins.json` 선언, 그 외 채널은 설치 사본 mtime — 어느 쪽을 봤는지
`install_time_source` 에 남긴다)과 **실행 중 호스트의 시작 시각**을 대조해
"재시작 전까지 노출되지 않는다" 를 발견으로 낸다. 시작 시각은 `ps` 의 `etime`
에서만 읽는다 (`lstart` 는 로케일로 번역돼 파싱이 호스트마다 갈린다).

`content_drift` 는 **어느 사본이 설치본인지**부터 가른다 — 갱신하면 옛 버전
디렉터리가 남으므로(§7.0.2 의 4), `installed_plugins.json` 의 `installPath` 선언을
읽어 로드되는 사본만 발견으로 세고 나머지는 `superseded` 로 남긴다. 선언이 없는
채널은 glob 매치를 전부 설치로 보되 **그것이 폴백임을 결과에 적는다**.

남는 미측정은 **그 뒤 한 칸**이다: 재시작이 최신인 호스트라도 하네스가 실제로
노출하는지는 이 탐침 밖이라 `content_drift` 가 `declared_unmeasured` 로
**밝힌다** — 재지 못하는 것을 통과로 세지 않는 원칙은 §7.0.0 의 `installable` 과
같다. 스킬이 안 보이면 파일 비교로 끝내지 말고 **CLI 를 재시작한 뒤 실제 호출**
로 확인한다.

> `wk doctor` 와 `wk release-doctor` 는 **다른 물건**이다. 전자는 배포 산출물의
> 설치 현황, 후자는 릴리스 baseline 평가다.

### 7.0.2. 채널별 재실행 계약 — 같은 명령을 다시 돌리면 무슨 일이 나는가

**채널마다 다르고, 문서가 없으면 알 수 없다.** smart update(`decide_action`)는
bootstrap 채널의 규율일 뿐이고, 플러그인 채널은 각 하네스의 설치기가 정한다.
아래는 **이 호스트에서 실측**한 결과다 (추정 없음) — 표는 2026-08-18,
*버전이 다를 때*의 셀은 2026-08-20 (v1.3.0 발행으로 처음 그 상태가 생겼다).

| 채널 | 설치본의 정체 | 설치 명령 재실행 | update 명령 | **페이로드가 낡았을 때 복구** |
|---|---|---|---|---|
| **claude-code** | 캐시 사본 (`~/.claude/plugins/cache/<mp>/<plugin>/<version>/`) | `already installed` — no-op | **버전이 같으면** `plugin update` 가 **버전 문자열만 보고 거절** (`already at the latest version`) · **버전이 다르면** 실제로 올린다 (아래 4) | 같은 버전: **`uninstall` → `install`** · 다른 버전: `plugin update <plugin>@<marketplace>` |
| **codex** | 캐시 사본 (`~/.codex/plugins/cache/<mp>/<plugin>/<version>/`) | `plugin add` 가 **marketplace 루트에서 캐시를 다시 복사** — 같은 버전에서도 갱신된다 | `marketplace upgrade` 는 **Git 소스 전용** (로컬 소스에는 해당 없음) | 같은 버전: `plugin add` 재실행 · 다른 버전: **`marketplace remove` → `marketplace add <새 경로>` → `plugin add`** (아래 5) |
| **grok-build** | 사본 (`~/.grok/installed-plugins/<id>/`) | **거부** — `Error: repo '<id>' already installed` (중복 항목은 안 생긴다) | `plugin update` 가 `local symlink, already live` 를 출력하지만 **실제로는 갱신하지 않는다** (원본에 표식을 넣고 실측) | `uninstall` → `install` |
| **pi-dev** | **경로 참조** — `~/.pi/agent/settings.json` 의 `packages[]`. 사본 없음 | 성공, 항목 중복 없음 (멱등) | `pi update <source>` 성공 | **불필요** — 원본이 곧 설치본이다 |
| **gemini-cli** | 미실측 | 미실측 | 미실측 | 이 호스트에 `gemini` CLI 가 없다 |

읽는 법 다섯 가지:

1. **"버전이 같으면 내용도 같다" 는 성립하지 않는다.** claude-code 는 이 전제로
   업데이트를 거절한다 — 실측 중 설치본이 정본보다 낡아 있었고(같은 `1.2.0`),
   `plugin update` 는 끝까지 거절했다. 개발 중 재배포에서는 **버전을 올리거나
   재설치**해야 한다.
2. **`marketplace update` 는 설치본을 안 고친다.** claude-code 에서 이 명령은
   marketplace **클론**만 최신으로 당긴다 (실측: 클론은 최신 커밋으로 갱신됐는데
   설치 캐시는 그대로였다). 설치본까지 가려면 위 표의 복구 열을 따른다.
3. **`grok plugin update` 의 출력을 믿지 말 것.** `already live` 라고 말하지만
   설치본은 inode 가 다른 **사본**이고, 원본을 바꿔도 반영되지 않았다.
4. **버전이 실제로 다를 때는 이야기가 다르다** (2026-08-20 실측, v1.2.0 → v1.3.0 —
   이 표의 나머지가 전부 *같은 버전*에서 측정된 것이라 이 셀만 비어 있었다):
   - **맨 이름은 실패한다.** `claude plugin update standard-ai-workflow` 는
     **rc 1** 로 `Plugin "standard-ai-workflow" not found` 를 낸다. `install` 은
     맨 이름을 받는데 `update` 는 안 받는다 — **`<plugin>@<marketplace>` 로 적는다.**
   - **`marketplace update` 를 먼저 돌릴 필요가 없다.** `plugin update` 가 클론을
     스스로 당긴다 (실측: 클론 HEAD 가 옛 커밋에서 최신으로 이동했다). 위 2번은
     "`marketplace update` 만으로는 설치본이 안 고쳐진다" 는 뜻이지 그 명령이
     선행 조건이라는 뜻이 아니다.
   - **당겨오는 것은 태그가 아니라 브랜치 팁이다.** 실측에서 설치된 `1.3.0` 의
     `gitCommitSha` 는 `v1.3.0` 태그가 아니라 **그 시점 main 의 팁**이었다. 즉
     같은 `1.3.0` 문자열이 시점마다 다른 내용을 가리킬 수 있다 — 위 1번의 함정이
     *소비자 쪽에서* 다시 성립한다.
   - **옛 버전 디렉터리는 남는다.** `cache/.../1.2.0` 과 `1.3.0` 이 나란히 있고
     `installed_plugins.json` 의 `installPath` 만 새것을 가리킨다. 그래서
     `wk doctor` 는 **선언을 읽어** 어느 사본이 설치본인지 가른다 (§7.0.1).
   - **`Restart to apply changes.`** — CLI 자신이 그렇게 말한다. §7.0.1 의
     `runtime_load` 가 재는 것이 정확히 그 조건이다.
5. **codex 는 같은 자리에서 정반대로 움직인다** (2026-08-20 실측, 로컬 소스
   1.2.0 → 1.3.0 — 이 채널의 나머지 셀도 *같은 버전*에서만 측정돼 있었다):
   - **마켓플레이스가 버전 경로에 고정된다.** 로컬 소스 등록은
     `dist/plugins/codex/<version>/install-root/...` 를 통째로 가리키므로,
     새 버전은 **소스 자체를 갈아야** 보인다. claude-code 처럼 이름 하나로
     당겨올 대상이 없다 — 마켓플레이스가 곧 그 버전이다.
   - **덮어쓰기를 거부한다.** 같은 이름에 다른 경로를 주면
     `Error: marketplace '<name>' is already added from a different source;
     remove it before adding this source` 가 난다. `marketplace remove` 를
     **먼저** 돌려야 한다.
   - **옛 버전 디렉터리가 남지 않는다.** `plugin add` 뒤 캐시에는 `1.3.0`
     하나만 남았다 — 위 4의 claude-code 와 **정반대**다. 그래서 `wk doctor`
     의 `installPath` 선언 읽기(§7.0.1)가 claude-code 에서는 필수이고
     codex 에서는 폴백(glob)으로 충분하다. 채널마다 잔재 정책이 다르다는
     사실 자체가 탐침이 선언을 읽어야 하는 이유다.

> 이 표는 `wk doctor` (§7.0.1) 의 **복구 열**이다. 탐침의 `content_drift` 절이
> 페이로드 해시로 *어긋났다* 는 사실까지 말해 주지만(2026-08-18+), 고치는 방법은
> 채널마다 다르므로 그 절의 보고를 받으면 여기 복구 열을 그대로 밟는다.

### 7.1. 부트스트랩 (플러그인 미지원 하네스 · 오프라인 · 진입점 규칙 주입)

```bash
# 옵션 A: 신 패키지 (path-style, 권장)
python3 -m workflow_kit.bootstrap_lib \
  --target-root /tmp/sample-repo \
  --project-slug sample_api \
  --project-name "Sample API" \
  --harness codex --harness opencode --harness antigravity --harness grok-build \
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
python3 -m workflow_kit.bootstrap_lib \
  --target-root "$REPO" \
  --project-slug "$SLUG" \
  --harness opencode \
  --no-interactive \
  --adoption-mode existing \
  --copy-core-docs
```

핵심 옵션:

- `--harness <name>` — `codex` / `opencode` / `gemini-cli` / `antigravity` / `minimax-code` / `claude-code` / `codewhale` (v0.10.4 신규) / `aider` / `goose` / `grok-build` (v0.15.16 신규, xAI CLI TUI) / `pi-dev` (11개, 반복 가능)
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
