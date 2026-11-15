# Beta v1.23.0 (2026-11-15)

> **상태: 릴리스 준비.** package `1.23.0`, runtime `__version__ = 1.23.0`, tag `v1.23.0`.
> **minor release** — 주장 트리 계획(ADR-031) · 계획 응답 반영(`plan-import`) · 계획·진척 워크벤치(ADR-032) · MCP `plan_inbox` · `plan_import` · MCP 도구 4종 성공 경로 수리.
>
> 등급 근거 (§1.5): `wk release-status` 의 파생 근거는 feat 5 · fix 17 · breaking 0 (발행 준비 직전, 수리 커밋 1건 포함 시 fix 18) — **minor**.
> 공개 Python API 시그니처 변경 0, 진입점 제거 0. 새 명령 `plan-status` · `plan-import` · `workbench`, 새 패키지 `workflow_kit.workbench`,
> 새 MCP 도구 둘은 **추가**다. backlog-update 의 새 플래그(`--plan-claim` · `--plan-decision` · `--decision-state`)는 선택이고,
> 주장 · 결정이 없는 task 는 이전과 같게 동작한다 (옛 소비자가 못 읽게 되는 변경 0).

## 0. 릴리스 판정

v1.22.0 이후 49커밋(병합 제외)이 발행되지 않은 채 쌓였다. 코드 커밋은 feat 5 · fix 18 이고, 나머지는 검사 보강 · 설계 문서 · 세션 기록이다.

이번 판의 축은 **"소유자가 열지 않은 결정은 동의가 아니다"** 를 도구로 강제한 것이다. task 의 계획에 주장(Claims)과
결정(Decisions)을 싣고, 열린 결정이 남은 task 는 `done` 으로 닫히지 않는다. 소유자의 답은 응답 파일로 받아
`plan-import` 가 자격을 판정해 반영하고, 그 응답을 브라우저에서 쓸 수 있게 하는 워크벤치 서버가 붙었다.

발행 직전에 **1.22.0 발행본에 있던 결함 하나**를 찾아 고쳤다(§2.5) — MCP 도구 4종이 성공 응답에서 항상 실패했다.

## 1. 릴리스 요약

- 범위: `v1.22.0..` 발행 준비 직전까지 **49 commit** (병합 1 제외) — feat 5 · fix 18 · test 5 · docs 9 · chore 11 · release 1.
- 누적 smoke **319/319 PASS** (로컬 `--branch-context=all` = 319 × native/slash, 발행 준비 커밋에서 실행).
- 검사 수 309 → 319 (새 검사 파일 10 — 계획 · 응답 · 워크벤치 · MCP 계약).

## 2. 소비자에게 보이는 변화

### 2.1 주장 트리 계획 — 열린 결정이 남은 task 는 닫히지 않는다 (`f45c6da1`, ADR-031 1단계)

- task 파일의 `## 🧭 Plan` 에 `Claims: C<n> …` · `Decisions: D<n> …` 를 싣는다. `backlog-update` 의 `--plan-claim` · `--plan-decision` ·
  `--decision-state D<n>=<state>` 로 쓴다.
- 쓰기 전에 린트(L1~L10)를 돌려 오류 규칙은 거부한다. `→ done` 은 열린 결정이 있으면 rc 1 로 거부되고 파일은 바뀌지 않는다.
  판정은 상태 칸이 아니라 **계산값**으로 한다 — 손으로 적은 `kept` 는 닫힌 것이 아니다.
- 새 명령 `plan-status`(읽기 전용) — 주장 × 인용 기준 × 결정의 계산 상태와 검증 보고에 붙일 markdown.
- `state.json` 에 `open_decisions`(있을 때만), `refresh-state` · `session-start` 가 우회를 경고한다.

### 2.2 계획 응답 반영 — `plan-import` (`c4c14c6b` · `bba68693`, ADR-031 2단계 · ADR-032 ①)

- 소유자의 답을 브랜치 받은편지함의 응답 파일로 받는다. `plan-import` 는 기본 dry-run, `--apply` 는 자격 있는 응답을 보관으로 옮기고
  결정 상태 칸을 다시 적는다. `--discard` + `--reason` 은 `.rejected.md` 로 거둔다.
- 받은편지함 건수의 정본은 `plan_responses.inbox_census` 하나다 — 게이트 · `session-start` · `refresh-state` · `plan-status` · `plan-import` 가 같은 값을 본다.
- 미반영 응답이 있는 task 는 `done` 으로 닫히지 않는다 (`pending_plan_responses`).
- 응답이 없는 저장소는 1단계와 같게 동작한다.

### 2.3 계획·진척 워크벤치 — `python -m workflow_kit workbench` (`a2e3b495`, ADR-032 ②)

- 브라우저에서 task 의 계획과 진척을 읽고 결정에 답한다. 서버가 쓰는 워크플로우 상태는 **받은편지함 하나**다.
- 표준 라이브러리 HTTP 서버, 이름 붙은 토큰(viewer / approver) · 세션 · 로그인 실패 제한, CSRF · Origin 검사, CSP 등 보안 머리.
  loopback 이어도 항상 인증한다. 경로 접두사 · 신뢰 프록시 설정으로 리버스 프록시 뒤에서 동작한다(상대 링크 · 쿠키 Path = 접두사).
- `--new-token` · `--status`, 실행 중이면 `session-start` 요약에 `워크벤치 실행 중: <url>` 한 줄. 스킬 `workbench` (+ `/workflow-workbench`).

### 2.4 MCP `plan_inbox` · `plan_import` (`f3223d6a`, 워크벤치 스펙 §8.3)

- `plan_inbox` (read-only 번들) — 받은편지함의 미반영 응답을 task 별 건수 · 파일별 자격(응답자 · 시각 · 단계 · 사유)으로. 주석 본문은 싣지 않는다.
- `plan_import` (write 번들) — CLI `plan-import` 를 같은 인터프리터의 하위 프로세스로 불러 출력 계약이 CLI 와 같다. 기본 dry-run, `apply` 는 boolean 만.
  인자 거절은 `invalid_tool_arguments`, 사유 없는 거둠은 `missing_discard_reason` 으로 입력 오류를 따로 알린다.

### 2.5 MCP 도구 4종이 성공 응답에서 실패하던 결함 (`bbcc2203`, TASK-2026-11-04-main-002) — **1.22.0 사용자 영향**

- `summarize_git_history` · `assess_milestone_progress` · `rotate_workflow_logs` · `apply_robust_patch` 가 **성공한 호출에서도**
  `invalid_tool_output_contract` 를 냈다. 출력 검증이 도구 이름을 family 로 찾는데 그 family 가 등록되지 않아 `Unknown family` 였다.
  오류 응답은 공통 `ErrorOutput` 이라 통과해서 '실패만 하는 도구' 로 보였다.
- 출력 모델을 등록했고, `rotate_workflow_logs` 의 오류 응답도 계약에 맞췄다. descriptor 의 `outputSchema` 가 generic `object` 에서 상세 스키마로 바뀐다.
- 새 검사 `check_mcp_tool_output_contracts` 가 레지스트리의 **모든** 도구에 family 가 있는지 단언한다.

### 2.6 그 밖의 수리

- `check_docs` 가 worktree 에서 문서 0개로 통과하던 결함 (`74021296`).
- seed 가 이어받은 handoff 가 인용하는 모 브랜치의 닫힌 task 를 원류로 푼다 (`bafecf74`).
- Windows 에서 쓰인 CRLF task 파일이 LF 로 뒤집히던 결함 — 정본 writer 가 EOL 을 보존한다 (`826af874`).

## 3. 검증

- **전량 게이트** `--branch-context=all` — native 319/319 · slash 319/319 · rc 0. 발행 준비 커밋의 clean tree 에서 실행하고,
  결과는 게이트 증거 파일(`<git common dir>/gate_evidence/<sha>.json`)에 남는다.
- **커밋 전** `--changed` 게이트 · **스모크** `check_self_application` 8/8 rc 0.
- 기능마다 verifier(새 컨텍스트에서 완료 기준 재측정) PASS 뒤에 닫았다 — 워크벤치 서버 7회, MCP 두 도구 3회, MCP 계약 수리 1회.
- 발행 호스트: Linux.

## 4. 알려진 한계 (감추지 않는다)

- **Windows 실측은 이번 판에 없다** (M-028/WBS-28.3). 응답 파일의 `os.link` 공개 · 배타 이동 · 잠금, 워크벤치의 포트 bind ·
  토큰 파일 모드(Windows 에 POSIX 모드 없음) · 콘솔 인코딩, `check_workbench_write` 의 inotify 층은 Linux 에서만 쟀다 — 미측정이다.
- 워크벤치의 덜 쓰인 파일 판정은 mmap 쓰기와, 다른 프로세스가 받은편지함 밖 하드링크 별칭으로 쓰는 경우를 재지 않는다.
- MCP 도구의 오류 신호 불일치 둘(계약 위반은 아님, 미수리): `summarize_git_history` 는 git 저장소가 아닌 경로에도 status ok,
  `apply_robust_patch` 는 SEARCH 불일치에 status error 인데 종료 코드 0.
- **case 수 선언 대조 축은 컨텍스트마다 83건이 미측정**이다(개수 선언 없음 79 · case 줄 없음 4, native · slash 합계 166) — 통과가 아니다.
- **PyPI 업로드는 하지 않는다**(§1 각주 0 — 2026-08-14 소유자 최종 결정). 배포는 GitHub Releases 하나다.
