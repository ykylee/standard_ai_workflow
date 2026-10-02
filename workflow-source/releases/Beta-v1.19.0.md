# Beta v1.19.0 (2026-10-02)

> **상태: 릴리스 준비.** package `1.19.0`, runtime `__version__ = 1.19.0`, tag `v1.19.0`.
> **minor release** — Windows 에서 kit 가 **로캘 인코딩(cp949)에 죽지 않고**, 하네스가 **`wk.exe` 없이**
> `python -m workflow_kit` 으로 kit 를 부른다.
>
> 등급 근거 (§1.5): `wk release-status` 의 파생 근거는 feat 1 · fix 1 · breaking 0 — **minor**.
> 공개 Python API 는 **추가만** 있다 — `workflow_kit.common.stdio` · `workflow_kit.common.kit_invocation`
> (신규 모듈), `workflow_kit/__main__.py`(`python -m workflow_kit`), `interpreter_matrix.venv_has_kit`.
> 진입점 증감 0 — `wk` console script 는 남고 rc 0 이다. `wk doctor --json` 의 `environment.wk_on_path` 는
> 판정에서 빠졌지만 키와 값은 legacy 로 남는다(새 판정 필드는 `kit_interpreters`).
>
> **동작 변경**: 플러그인 hook · 스킬 · 진입점 규칙 블록이 지시하는 명령이 `wk <명령>` 에서
> `python -m workflow_kit <명령>` 으로 바뀌었다. **hook 명령 문자열이 바뀌므로 Codex 사용자는 hook 을
> 다시 신뢰해야 한다** (TUI "Hooks need review").

## 0. 릴리스 판정

소유자 보고 2건, 같은 Windows 호스트(OpenCode 데스크톱):

1. `wk` 실행이 **cp949 인코딩 에러**로 죽었다.
2. **AhnLab V3 가 `wk.exe` 를 평판 기반으로 차단**했다.

1 은 kit 결함이고, 2 는 배포 형태의 한계다 — pip 의 console-script 런처는 설치마다 새로 생성되는 서명 없는
실행 파일이라 평판이 쌓이지 않는다. 둘 다 Windows 소비자가 워크플로우를 아예 못 돌리는 문제라 함께 발행한다.

## 1. 릴리스 요약

- 범위: `v1.18.0..` 발행 준비 직전까지 **5 commit** — v1.18.0 발행 마무리 1건과 세션 기록 1건을 빼면 실질은
  **3 commit** (`df975bbe` · `2eb7c315` · `fb957c5c`).
- 누적 smoke **302/302 PASS** (로컬 `--branch-context=all` = 302 × native/slash).
- 검사 수 **300 → 302** (신설 2: `check_text_io_encoding` 5 cases, `check_kit_invocation` 4 cases).

## 2. 소비자에게 보이는 변화

### 2.1 cp949 로캘에서 죽지 않는다 (`df975bbe`, TASK-2026-10-02-main-006)

하네스가 kit 를 **파이프로** 부르면 Windows 의 Python 은 stdio 에 로캘 인코딩을 쓴다. 한국어 Windows 는 cp949 라
출력의 `—`(U+2014) · `✅` 에서 `UnicodeEncodeError` → exit 2. 터미널에서 직접 돌리면 콘솔 API 를 타서 재현되지 않는다.

- `wk` · `python -m workflow_kit` · 하네스가 `python -m` 으로 부르는 진입점이 시작 시 stdin/stdout/stderr 를 UTF-8
  로 고정한다 (`common/stdio.force_utf8_stdio`).
- 파일 · subprocess 텍스트 I/O **115곳**에 `encoding="utf-8"` 명시 (subprocess 108곳은 `errors="replace"` — 외부
  도구가 로캘 바이트를 내도 죽지 않는다). 수리 전 `-X warn_default_encoding` 으로 session-start 한 번에 13건이던
  EncodingWarning → 0.

### 2.2 하네스가 `wk.exe` 를 부르지 않는다 (`2eb7c315`, TASK-2026-10-02-main-007)

- **명령 형태**: 정본 §11.1 의 갱신 명령이 `python -m workflow_kit <명령>` 이다. 규칙 블록에 한 줄 — "workflow_kit
  를 깐 해석기로 실행(Windows `python`, macOS/Linux 대개 `python3`), `wk` 실행 파일은 부르지 말 것". CLAUDE.md ·
  AGENTS.md 블록, 플러그인 스킬 5종, bootstrap 산출물이 같은 정본에서 나온다.
- **hook**: 해석기 이름 하나에 기대지 않는다. `python3` → `python` 순으로 **`workflow_kit` 를 import 하는 첫 해석기**를
  골라 쓴다 — Windows 의 `python3` 는 대개 Store 별칭이라 탐침에서 떨어진다. 없으면 SessionStart 가 설치 안내를
  내고 나머지 hook 은 조용히 끝난다(exit 0).
- **`wk doctor`**: `wk` PATH 대신 `python3` · `python` 각각의 `workflow_kit` import 를 실측해 보고한다 (`kit 해석기`
  줄 · `kit_interpreters`). 플러그인 채널 설치 전제에서 `wk` 가 빠졌다.
- **kit 출력 안내**: session-start 경고 · seed 템플릿 등 에이전트가 그대로 실행할 수 있는 안내 문자열 30곳이 같은
  형태로 바뀌었다.
- `wk` 는 사람이 터미널에서 쓰는 단축형으로 남는다.

### 2.3 해석기 매트릭스가 새 venv 에 의존성을 깐다 (`fb957c5c`, 개발자용)

`interpreter_matrix --run-local` 을 문서의 명령(`PYTHONPATH=workflow-source …`)대로 돌리면, 새로 만든 matrix venv 에서도
상속된 `PYTHONPATH` 덕에 `import workflow_kit` 이 성공해 의존성 설치를 통째로 건너뛰었다(pydantic 부재로 전량 red).
설치 탐침은 이제 `PYTHONPATH` 를 지우고 잰다.

## 3. 검증

- 전량 게이트 `--branch-context=all` — 발행 준비 커밋에서 실행 (결과는 발행 기록에 남긴다)
- 해석기 매트릭스 3.11 · 3.13 각 302/302
- `check_text_io_encoding` 5/5 — AST 전수 · 스캐너 형태 23종 · `PYTHONIOENCODING=cp949` 대조군(죽는다) 대비 왕복 ·
  실물 `wk_main` · 진입점 배선. 되주입 5건 각 red
- `check_kit_invocation` 4/4 — 모듈 실행 · §11.1 하위 명령 실재 · 에이전트 표면 `wk <명령>` 0건 · 탐침이 Store 별칭형
  해석기를 건너뜀. 되주입 4건 각 red. 더해 plugin payload 의 bare-`wk` hook 가드, 설치 문서 전제 표 정확 일치(남은
  `wk` 를 못 잡던 포함 대조를 강화), compact relay case 15 를 fake 해석기 3벌(현재 · 구버전 · 부재)로

## 4. 알려진 한계 (감추지 않는다)

- **Windows 실물에서 재지 않았다.** 위 검증은 Linux 에서 Windows 조건(`PYTHONIOENCODING=cp949`, Store 별칭형
  해석기)을 만든 것이다. OpenCode 데스크톱의 실행 셸, `python` 이 kit 를 깐 해석기로 해석되는지, hook 왕복은 그
  호스트에서 확인 대기다 (TASK-2026-10-02-main-006 · 007 `in_progress`).
- 에이전트용 명령은 `python` 으로 적혀 있다 — POSIX 에서 `python` 이 없으면 에이전트가 규칙 블록의 안내대로
  `python3` 로 바꿔야 한다 (hook 은 스스로 고른다).
- 사람용 문서 곳곳의 `wk <명령>` 예시는 그대로다 (POSIX 단축형).
- `TASK-2026-08-25-main-017` (MCP emit command 가 항상 `python3`) 는 blocked, origin 없는 저장소의 worktree seed
  (`TASK-2026-10-02-main-003`) 와 minimax-code 채널(`TASK-2026-09-30-main-001`)은 planned 그대로다.
