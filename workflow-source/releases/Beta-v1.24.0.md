# Beta v1.24.0 (2026-11-16)

> **상태: 릴리스 준비.** package `1.24.0`, runtime `__version__ = 1.24.0`, tag `v1.24.0`.
> **minor release** — 워크벤치 개방 모드(`--open`) · 자동 기동(`--autostart` · `--stop`) · 화면 개편 + 수리 둘(경고 분류기 `/var/tmp` · MCP 오류 신호).
>
> 등급 근거 (§1.5): v1.23.0 이후 코드 커밋 feat 3 · fix 2 · breaking 0 — **minor**.
> 공개 Python API 시그니처 제거 0, 진입점 제거 0. 새 플래그 `workbench --open` · `--autostart` · `--stop` · `--autostarted-only` 와
> 응답 파일의 선택 키 `client` 는 **추가**다. 토큰 모드의 동작, 자동 기동 설정이 없는 `session-start` 의 동작은 이전과 같다.
> MCP 진입점의 종료 코드가 `status: error` 에서 1 이 된 것은 결함 수리다 (이전에는 오류를 rc 0 으로 냈다 — §2.5).

## 0. 릴리스 판정

v1.23.0 이후 5커밋(병합 · 발행 제외)이다. 소유자 지시 세 가지 — "세션 작업 시작할 때 워크벤치 서버를 띄우도록",
"토큰 없이 localhost 말고 IP 로도 그냥 들어가게", "워크벤치 디자인이 너무 별로다" — 를 task 셋으로 나눠 구현했고,
1.23.0 노트 §4 에 **미수리**로 적었던 MCP 오류 신호 불일치 둘과 발행 뒤 찾은 경고 분류기 결함을 고쳤다.

## 1. 릴리스 요약

- 범위: `v1.23.0..` 발행 준비 직전까지 **5 commit** — feat 3 · fix 2.
- 누적 smoke **322/322 PASS** (로컬 `--branch-context=all` = 322 × native/slash, 발행 준비 커밋에서 실행).
- 검사 수 319 → 322 (새 검사 파일 3 — `check_workbench_open` · `check_workbench_autostart` · `check_workbench_design`).

## 2. 소비자에게 보이는 변화

### 2.1 워크벤치 개방 모드 — `workbench --open <이름>` (`42d74896`, spec §5.6 · ADR-032 V8)

- 토큰 · 로그인 없이 접속한 누구나 `<이름>` 의 approver 로 보고 답한다. loopback 밖 `--bind` 를 TLS 없이 받고, 시작 때 경고 한 줄.
  `--bind 0.0.0.0` 이면 기본 `public_url` 은 이 호스트의 LAN 주소다.
- 응답 파일 머리에 선택 키 `client: <요청자 주소>` 가 실린다 (자격 판정에는 쓰지 않는다). 토큰 모드는 싣지 않는다.
- 쓰기의 Origin 은 `public_url` 출처 또는 요청 `Host` 출처 — `Host` 는 IP 리터럴 · `localhost` · `public_url` 호스트만 받아 DNS rebinding 을 막는다.
  세션 표 상한 1,024.
- **대가**: 응답이 소유자에게서 왔다는 대조가 없다 — 같은 네트워크의 누구나 그 이름으로 답할 수 있다. 소유자가 고를 때만 쓴다.
- `--open` 과 `--token` 은 같이 줄 수 없다 (rc 2).

### 2.2 워크벤치 자동 기동 (`93133bb5`, spec §3.1 · ADR-032 V9)

- `workbench --autostart on <시작 인자…>` 가 인자를 검증해 checkout 로컬 `.workbench/autostart.json` 에 저장한다 (git 무시, 토큰은 참조만). `off` 가 지운다.
- 설정이 있고 살아 있는 서버가 없으면 `session-start` 가 서버를 떨어진 자식으로 띄우고 보고에 `워크벤치 시작: <url>`.
  실패는 `warnings` 한 줄이고 세션 진입을 막지 않는다. 15초 안에 실행 기록이 없으면 자식을 내린다.
- `workbench --stop [--autostarted-only]` — 기록의 서버가 `healthz` 에 답할 때만 내린다 (pid 재사용 방어).
- Claude Code 플러그인 `SessionEnd` hook 이 `workbench --stop --autostarted-only` 를 부른다. SessionEnd 가 없는 하네스에서는 서버가 남고,
  다음 `session-start` 가 그것을 `워크벤치 실행 중` 으로 알린다.
- 검사 표식(`WORKFLOW_KIT_TELEMETRY_SKIP_ROOT`)이 이 작업 공간을 가리키거나 `WORKFLOW_KIT_NO_WORKBENCH_AUTOSTART` 가 있으면 띄우지 않는다.

### 2.3 워크벤치 화면 개편 (`d1f11bed`, spec §4.4)

- 진척: 요약 수치 다섯(진행 중 · 차단 · 계획 · 열린 결정 · 미반영 응답) · 계획 카드(열린 결정 강조) · 작업 보드 4열 · 마일스톤 카드와 진척 막대
  (선언 · 파생 모두 `done` 이고 문제 없는 것만 접는다).
- 계획: 머리 카드와 상태 칩 · 주장 카드 트리 · 열린 결정 강조(닫힌 채 — 펼침이 곧 `opened` 기록) · 선택지 카드 · 하단 고정 제출 막대.
- CSS 하나로 밝은 · 어두운 모드 · 좁은 폭. 외부 자원 · 인라인 style/script 없음 (CSP 그대로). 화면의 계약 문자열 · 폼 · 상대 경로는 그대로다.

### 2.4 경고 분류기 — 저장소가 `/tmp` · `/var/tmp` 아래면 서드파티 경고를 저장소 경고로 (`f75822ff`)

- 경로의 임시 디렉터리 부분을 `<TMP>` 로 지우는 정리가 출처 판정보다 먼저 돌아 `site-packages` 단서가 사라졌다. 이제 원래 경로로 판정하고
  표시와 중복 제거에만 `<TMP>` 를 쓴다. `/var/tmp` 아래 worktree 에서 게이트가 거짓 red 를 내던 것이 사라진다.

### 2.5 MCP 오류 신호 불일치 둘 — 1.23.0 §4 의 미수리 항목 해소 (`85d9596c`)

- `invoke_tool` 이 모든 도구의 `status: error` 응답을 종료 코드 0 으로 냈다 — CLI `--tool` 과 JSON-RPC 경로가 실패를 성공으로 보고했다.
  이제 rc 1 (JSON-RPC 는 오류 응답). `apply_robust_patch` 의 SEARCH 불일치도 여기에 든다.
- `summarize_git_history` 가 git 저장소가 아닌 경로 · 풀 수 없는 범위에 status ok · 커밋 0건이었다 — 이제 `git_log_failed` 오류. 빈 범위는 그대로 ok · 0건.

## 3. 검증

- **전량 게이트** `--branch-context=all` — native 322/322 · slash 322/322 · rc 0. 발행 준비 커밋의 clean tree 에서 실행하고,
  결과는 게이트 증거 파일(`<git common dir>/gate_evidence/<sha>.json`)에 남는다.
- **커밋 전** `--changed` 게이트 · **스모크** `check_self_application` 8/8 rc 0.
- task 마다 verifier(새 컨텍스트에서 완료 기준 재측정) PASS 뒤에 닫았다 — 5건. verifier 가 실측으로 찾은 결함(DNS rebinding 통과 ·
  세션 표 무상한 · 자동 기동 대기 초과 시 고아 자식 · 화면 사소 2건)은 커밋 전에 고쳤다.
- 화면은 헤드리스 Chrome 으로 밝은 · 어두운 · 420px 를 찍어 눈으로 확인했다 (가로 넘침 0 — CDP 실측).
- 발행 호스트: Linux.

## 4. 알려진 한계 (감추지 않는다)

- **Windows 실측은 이번 판에도 없다** (M-028/WBS-28.3). 자동 기동의 `DETACHED_PROCESS` · `--stop` 의 TerminateProcess 경로, 응답 파일의 `os.link`
  공개 · 배타 이동 · 잠금, 워크벤치의 포트 bind · 토큰 파일 모드 · 콘솔 인코딩은 Linux 에서만 쟀다 — 미측정이다.
- `--stop` 의 pid 재사용 방어는 "기록의 포트가 워크벤치로 답하는가" 다 — 그 pid 가 그 포트의 주인인지는 보지 않는다(좁은 경우).
- 한 checkout 에서 여러 세션을 동시에 쓰면 한 세션의 SessionEnd 가 자동 기동 서버를 내린다 — 다음 `session-start` 가 다시 띄운다.
- `run_create_session_handoff_draft.py` 를 직접 실행하면 git 실패가 오류 응답 대신 스택 트레이스와 rc 1 로 끝난다(MCP 도구 경로는 영향 없음).
  `apply_robust_patch` 의 SEARCH 불일치 error_code 는 여전히 `malformed_patch_block` 이다(나누려면 출력 계약 변경).
- **case 수 선언 대조 축은 컨텍스트마다 83건이 미측정**이다(개수 선언 없음 79 · case 줄 없음 4, native · slash 합계 166) — 통과가 아니다.
- **PyPI 업로드는 하지 않는다**(§1 각주 0 — 2026-08-14 소유자 최종 결정). 배포는 GitHub Releases 하나다.
