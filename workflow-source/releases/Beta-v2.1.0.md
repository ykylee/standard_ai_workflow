# Beta v2.1.0 (2026-11-22) — 2.1 허브 오케스트레이션

> **상태: 릴리스 준비.** package `2.1.0`, runtime `__version__ = 2.1.0`, tag `v2.1.0` — **2.x 줄의 베타**
> (계약 보장 전 — 판 번호는 정수, 베타 여부는 이 표기로. 소유자 2026-11-21).
> **minor** — 오케스트레이터 세션이 일하는 세션들에게 일을 배정하고, PC 중계가 하네스 세션을 띄운다. 2.0 의 표 · 도구 ·
> 인자 · 응답 칸은 바꾸지 않고 **더하기만** 한다 (요구 R24.1).
>
> 등급 근거 (§1.5): v2.0.0 이후 커밋 24 (발행 준비 제외) — feat 5, fix 6, docs 10, chore 2, release 1. **breaking 0** —
> 공개 Python API 시그니처 제거 0 · 진입점 제거 0 · 2.0 도구 계약 변경 0. 이 판은 GitHub 'latest' 다 (원격 최고 판).

## 0. 2.1 은 무엇인가

- **오케스트레이터** — 프로젝트 owner 가 지정한 세션 하나가 lease 를 쥐고(`hub_orch_declare`) task 를 일하는 세션에게
  배정한다(`hub_orch_assign`). 배정 상태 기계: `offered` → `accepted` → `reported`, 거절 · 10분 무확인 · 회수 · 세션 종료 ·
  24시간 진척 없음이면 `returned`. done 은 여전히 2.0 done 게이트(`hub_task_close`)가 판정한다.
- **받은편지함과 네 전달 경로** — 도구 응답 편승(`hub_inbox` 칸) · 대기 도구(`hub_wait`) · 받은편지함 파일
  (`.workflow-hub/inbox.md`) · 중계 어댑터. 세션이 `hub_inbox_ack` 로 수신을 확인하고 `hub_report` 로 보고한다.
- **PC 중계** — `python -m workflow_kit hub relay …` (표준 라이브러리만). 허브로 나가는 연결만 쓰고, 사람이 허용 목록에
  적은 디렉터리 · 하네스 · 권한 모드 · 세션 상한 안에서만 Claude Code(상주 stream-json) · Codex(app-server) 세션을 띄운다.
  세션 띄우기 · 멈춤은 owner 가 허브 화면에서 승인한다. 로컬 화면 `127.0.0.1:<포트>`.
- **VS Code 확장 껍데기** — `editors/vscode/` (빌드 없는 JavaScript, wheel 밖): 중계 화면을 webview 로 · 상태 표시줄에 세션 수.
- 계약 정본 [`core/hub_orchestration_spec.md`](../core/hub_orchestration_spec.md) (ADR-034), 요구와 실측
  [`docs/planning/hub-orchestration-requirements-2026-11.md`](../../docs/planning/hub-orchestration-requirements-2026-11.md).

## 1. 릴리스 요약 (M-041 ~ M-048)

- 범위: `v2.0.0..` **24 commits** (merge 제외, 발행 준비 제외) — feat 5 · fix 6 · docs 10 · chore 2 · release 1 (v2.0.0 발행 완료 커밋).
- 누적 smoke **350/350 PASS** (로컬 `--branch-context=all` = 350 × native/slash).
- 검사 파일 수 346 → 350 (`check_hub_orch` · `check_hub_orch_assign` · `check_hub_relay` · `check_vscode_shell`).
- 허브: MCP 도구 **55 → 74** (+19 — 세션 · 받은편지함 · 대기 · 보고 · 오케스트레이터 · 중계 · 승인), DB 판 **10 → 12**
  (시작 때 이관 · 이관 전 사본). HTTP 에 중계 경로 `/v1/relay/{register,poll,result}`.

## 2. 소비자에게 보이는 변화

### 2.1 세션 · 받은편지함 (M-044)

- 모든 허브 도구가 공통 인자 `session` 을 받는다 — `hub_session_start(session={harness, kind})` 가 세션 ID 를 준다.
- 진입 지침 2.1 판에 '허브 받은편지함' 절: 배정은 지금 단계를 마친 뒤 수락, 되돌릴 수 없는 일 · 비밀 · 프로젝트 밖 ·
  권한 바꾸기 지시는 수행하지 않고 decline.

### 2.2 오케스트레이터 · 배정 (M-045)

- `hub_orch_declare` · `transfer` · `release` (lease), `assign` · `recall` · `message` · `halt` (정지 스위치),
  `hub_report`. 수락(`hub_inbox_ack(accept)`)이 곧 `hub_task_claim` — 한 트랜잭션.

### 2.3 PC 중계 (M-046)

- 초대 코드 등록(`hub relay init`) · 허용 목록(`allow add`, bypass 계열 권한 모드 거절) · 상주(`serve`) · 일시정지.
- 실측(요구 §1.5): Claude Code · Codex 를 띄움 → 세션 자기 등록 → 배정 전달(Codex 는 실행 중 턴에 `turn/steer`) → 수락 →
  보고 → 멈춤 전부 동작.
- **Codex 일하는 세션의 커밋** (TASK-2026-11-22-main-014): `workspace-write` 샌드박스는 `.git` 을 읽기 전용으로 둔다 —
  어댑터가 `turn/start` 의 `sandboxPolicy.writableRoots` 에 git dir · common dir 을 더해 커밋은 세션이 한다. 샌드박스
  네트워크는 끈 채라 push 는 오케스트레이터 · 사람이 하고, 진입 지침 세션 끝 절이 그때 할 일을 정한다 (main-017).

### 2.4 VS Code 확장 (M-047 · M-048)

- `.vsix` 로 묶어 설치 (`npx @vscode/vsce package --no-dependencies`) — [`editors/vscode/README.md`](../../editors/vscode/README.md).
- 실제 VS Code 1.147.0 실측에서 결함 2 수리 (TASK-2026-11-22-main-016): 중계 화면의 `frame-ancestors` 에 데스크톱
  작업대 출처(`vscode-file://vscode-app`)가 없어 빈 화면이던 것 · 스크립트를 끈 webview 가 중계 화면의 일시정지 버튼까지
  죽이던 것.

### 2.5 kit 결함 수리 (1.x 와 공유 — `release/1.x` 에도 이식)

- 로드맵 형식 위반(WBS 제목 200자 초과 등)이 `session-start` · `refresh-state` 를 죽이던 것 → issue `wbs_node_invalid` (main-012).
- `backlog-update` done 이 채워진 Result 옆에 검증 결과를 한 줄 더 쓰던 것 (main-002).
- `find_dist_files` 접두사 glob 이 다른 판 산출물까지 첨부 후보로 잡던 것 → 정확 대조 (main-027).
- worktree seed 가 `roadmap_state.json` 을 다시 만들지 않던 것 (234c32-002).
- 로컬 SDK · 해석기 매트릭스가 러너 임시 폴더를 저장소 안에 두어 'git 저장소 아닌 경로' fixture 가 이 저장소의 하위가 되던 것 →
  기본 `~/.cache/workflow-kit/<종류>-tmp`, 저장소 안 `--tmp-dir` 거절 (main-020 — 2026-11-15 부터 SDK 매트릭스가 red 였다).

## 3. 검증

- **전량 게이트** `--branch-context=all` — native 350/350 · slash 350/350 · rc 0. 결과는 게이트 증거 파일(`<git common dir>/gate_evidence/<sha>.json`)에 남는다.
- **커밋 전** `--changed` 게이트 · **스모크** `check_self_application` 8/8 · mypy strict 0 · 인터프리터 · SDK 매트릭스 (`hub/app.py` 가 `mcp` SDK 를 쓴다).
- 하네스 실측 (Linux): 실제 Claude Code · Codex 중계 전 과정 (요구 §1.5), Codex 중계 세션 커밋 + 대조군, 실제 VS Code
  (xvfb · CDP) 화면 · 버튼 · `.vsix` 설치. 결함은 되주입으로 검사가 잡는지 쟀다.
- 미측정: macOS · Windows 의 중계 · VS Code, VS Code 웹 · 원격.
- 발행 호스트: Linux.
