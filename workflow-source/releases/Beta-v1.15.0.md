# Beta v1.15.0 (2026-09-30)

> **상태: 릴리스 준비.** package `1.15.0`, runtime `__version__ = 1.15.0`, tag `v1.15.0`.
> **minor release** — **compact 중계**(컨텍스트 압축 전후로 작업 상태를 기록 · 대조 · 재주입)
> 신설 + Windows 호스트 결함 4건 수리.
>
> 등급 근거 (§1.5): `wk release-status` 의 파생 근거는 feat 1 · fix 4 · breaking 0 — **minor**.
> 공개 Python API 는 **추가만** 있다 — `workflow_kit.common.compact_relay` (신규 모듈),
> `context_budget.measure` 의 키워드 인자 `project_profile_path` (기본값 `None`, 기존 호출 그대로),
> `context_budget.BUDGETS` 의 레코드 `compact_reinjection`. 진입점은 **1 증가** (`wk compact-checkpoint`
> · console script `workflow-compact-checkpoint`), 감소 0.

## 0. 릴리스 판정

새 기능 축(M-018~M-021)이 concept → implementation 을 끝냈고, 플러그인 소비자에게 닿으려면 발행이
필요하다 — 플러그인의 hook 은 설치된 kit 의 `wk compact-checkpoint` 를 부르므로, 발행 전에는 어느
소비 호스트에서도 돌지 않는다.

## 1. 릴리스 요약

- 범위: `v1.14.4..` 발행 준비 직전까지 **12 commit**. 이 중 1건(`5c78434f`)은 **v1.14.4 발행
  마무리**가 태그 뒤에 착지한 것이고 5건은 세션 기록이라 실질은 **6 commit** 이다.
- 누적 smoke **298/298 PASS** (로컬 `--branch-context=all` = 298 × native/slash).
- 검사 **296 → 298** (신설 2: `check_relpath_posix` · `check_compact_relay`).

## 2. 소비자에게 보이는 변화

### 2.1 compact 중계 — 압축 요약이 잃는 것을 브랜치 메모리로 건너뛴다 (`5a3c9db4`, ADR-030)

하네스가 컨텍스트를 압축하면 요약은 결론을 남기고 **"확인했다 / 아직 안 확인했다" 의 구분과 다음
한 걸음**을 버리기 쉽다. 이제 압축 전에 그것을 브랜치 메모리에 적고, 압축 뒤 다시 넣는다.

- **스킬 `compact-relay`** (플러그인 5번째 스킬, bootstrap 채널은 `/workflow-compact-relay`) — 모델이
  판단 층(다음 한 걸음 · 미검증 · 검증됨 · 기각한 안)을 `wk compact-checkpoint --note` 로 기록하고,
  사용자에게 붙여 넣을 `/compact …` 한 줄을 준다 (스킬은 `/compact` 를 실행하지 못한다).
- **플러그인 hook 3종** — `PreCompact` 가 기계 층(브랜치 · HEAD · 열린 task · 미커밋 파일)을 기록하고
  대기 중인 판단 층을 이 세션으로 인수한다. `PostCompact` 가 하네스 요약 원문과 식별자(task ID ·
  M/WBS · 백틱 경로 · sha)를 대조해 **요약에서 빠진 것을 한 줄로** 말한다. `SessionStart(compact)` 가
  4,096 바이트 안에서 상태 기록을 재주입한다 (우선순위: 다음 한 걸음 → 미검증 → task → …).
  자동 압축에서도 기계 층은 남고, 판단 층이 없다는 사실을 재주입 머리말이 말한다.
- checkpoint 는 `ai-workflow/memory/active/<branch>/.compact/` — **자기 무시 `.gitignore`** 를 가져
  커밋되지 않고, `session_handoff.md` · `state.json` 은 건드리지 않는다. 세션 종료 스킬이 남길 줄을
  handoff 로 옮기고 `--clear` 한다.
- 워크플로우 밖 프로젝트(전역 설치된 플러그인)에서는 **출력도 파일도 없다**.
- 정본 §11.1 에 한 줄: `Relay working state across a context compaction (skill + hooks)` → 생성 규칙
  블록(`CLAUDE.md` · `AGENTS.md` 등)이 한 줄 늘어난다.

**실측** (Claude Code 2.1.285, `claude -p` 압축 왕복 2회): 플러그인 hook 3종 발화 · 재주입 도달 ·
hook 출력 인라인 상한 ≈10,000 **자**(초과 시 앞 2KB 미리보기만) · **`SessionStart(compact)` 가
`PostCompact` 보다 먼저 돈다** — 그래서 누락 목록은 재주입이 아니라 post 출력이 싣는다.

**적용**: kit 과 플러그인을 **같은 버전(1.15.0)** 으로 올린다. 플러그인만 새것이면 압축 때
"`wk compact-checkpoint` failed — the installed kit may be older than the plugin" 한 줄이 뜨고
중계는 건너뛴다 (압축은 막지 않는다).

### 2.2 Windows 호스트 수리 4건

- **`wk doctor` 가 Windows 에서 정본 파일을 extra 로 오판하던 것** (`b836d83d`) — 사본 대조가 POSIX 정본
  키와 역슬래시 상대 경로를 비교해 하위 디렉터리 파일 전부를 미등록으로 보고했다. 비교·커밋·교환에 쓰이는
  `relative_to` 5곳을 `as_posix()` 로. 신규 `check_relpath_posix` 가 `PureWindowsPath` 로 Windows 를 흉내 낸다.
- **`roadmap_state.json` 의 `source_path` 가 Windows 커밋에서 역슬래시로 남던 것** (`71c718a1`) — 교차
  호스트 diff 가 났다. POSIX 로 고정.
- **doctor 의 휘발 경로 판정 · 설정 경로 표기** (`d3bd8689`) — Windows 사용자 temp 디렉터리를 `/tmp` 의
  짝으로 휘발 판정에 넣고, 경로 비교를 `normcase` 로. `plugin_enabled` 의 사용자 설정 경로를 POSIX 로 표기.
- **개발 게이트 `python_floor` 의 하한 해석기 호출을 stdin 으로** (`a86614aa`) — v1.14.4 노트 §4 가 남긴
  같은 부류의 마지막 다줄 `-c` 사이트. 배치 shim(pyenv-win 등)에서 첫 개행 뒤가 잘려 크래시하던 것.

## 3. 검증

- 전량 게이트 `--branch-context=all` — 발행 준비 커밋에서 실행 (결과는 발행 기록에 남긴다)
- `check_compact_relay` 12/12 — case 마다 결함 되주입(13건) 전부 red
- `claude -p --plugin-dir plugin` 압축 왕복 E2E 2회 — 모델이 재주입 블록을 원문 인용하고, 요약이 잃은
  task ID · 재현 결과 · 미검증 항목을 스스로 짚었다
- `check_relpath_posix` 4/4 (수정 되돌리면 0/4), `check_python_floor_syntax` case 6 (옛 호출 되주입 red)

## 4. 알려진 한계 (감추지 않는다)

- **재주입은 Claude Code 에서만 실측됐다.** Grok Build 는 같은 hook 사본을 읽지만 `SessionStart` 출력을
  무시해 재주입이 없다(공식 문서 기준 선언). Codex manifest 에는 hook 을 싣지 않았다(미실측). 이 하네스들에서는
  스킬 절차(기록 → `/compact` → 압축 뒤 checkpoint 파일 직접 읽기)만 통한다.
- **자동 압축(`trigger: auto`) 경로는 미실측**이다 — headless 로 한계까지 채우기 어렵다. 대화형 세션 실측은 후속.
- Windows 수리 4건 중 cmd.exe 실측은 여전히 소유자 환경에 맡긴다 (fake shim · `PureWindowsPath` 모형으로 검증).
- `TASK-2026-08-25-main-017` (MCP emit command 가 항상 `python3`) 는 blocked 그대로다.
- minimax-code 플러그인 채널(`TASK-2026-09-30-main-001`)은 형식 미확정으로 planned 그대로다.
