# Beta v1.21.0 (2026-10-19)

> **상태: 릴리스 준비.** package `1.21.0`, runtime `__version__ = 1.21.0`, tag `v1.21.0`.
> **minor release** — `doctor` 가 MiniMax Code 채널을 세 축에서 잰다 + origin 없는 저장소의 worktree 자동 seed +
> 117 · 118차 수리 묶음(진입점 다이어트 harvest · 메모리 lint branch-scoped · goal coverage provenance · minimax_plugin 보고).
>
> 등급 근거 (§1.5): `wk release-status` 의 파생 근거는 feat 1 · fix 6 · breaking 0 — **minor**.
> 공개 Python API 시그니처 변경 0, 진입점 제거 0. 새 공개 모듈 `path_resolver` 의 seed 후보 판정과
> doctor payload 의 minimax-code 항목이 **추가**다 (옛 소비자가 못 읽게 되는 변경 0).

## 0. 릴리스 판정

v1.20.1 이후 두 호스트(Linux · macOS)에서 닫은 일곱 task 가 발행되지 않은 채 쌓였다. 그중 하나는 채널 기능이다 —
`wk doctor` 의 `content_drift` · `plugin_enabled` · `runtime_load` 가 MiniMax Code 를 보지 않아, 그 채널이 뒤처져도
`behind=[]` 였다. 나머지는 "검사가 조용히 통과하던 자리" 를 닫은 수리다: 다이어트 harvest 가 v1.20.0 생성물을 모르는 채
green · 메모리 lint 가 legacy 경로만 보며 green · goal coverage 가 닿을 수 없는 goal 을 warnings 없이 uncovered 로만 냄 ·
`minimax_plugin --apply` 가 첫 설치를 "이미 일치" 로 보고.

## 1. 릴리스 요약

- 범위: `v1.20.1..` 발행 준비 직전까지 **16 commit** — 세션 기록 6건 · 병합 1건 · 직전 발행 마무리 1건을 빼면 실질 **8 commit**.
- 누적 smoke **309/309 PASS** (로컬 `--branch-context=all` = 309 × native/slash, 발행 준비 커밋에서 실행).
- 검사 수 309 → 309 (새 검사 파일 0 — 기존 검사에 case 추가: `check_entry_diet` 6 · 7, `check_memory_lint` 3 self-test,
  `check_graph_insights_health_monotonic` case 7, `check_minimax_plugin_channel` · `check_branch_memory_auto_seed` 확장).

## 2. 소비자에게 보이는 변화

### 2.1 doctor 가 minimax-code 채널을 잰다 (`4ab6938c`, TASK-2026-09-30-main-001)

`content_drift` 는 `~/.minimax/plugins/standard-ai-workflow/` 를 사본으로 세어 behind 를 판정하고, `plugin_enabled` 는
MiniMax 로컬 런타임의 SQLite(`~/.minimax/v2/sqlite/runtime-state.sqlite` → `local_runtime_plugin_local_disabled`) 표로
켜짐 · 꺼짐을 판정한다 — 행이 있으면 꺼짐, 없으면 켜짐이다 (claude-code 와 반대). `runtime_load` 의 로더는 MiniMax Code
데스크톱 앱이다. DB 경로나 표 이름이 바뀌면 판정은 '모름' 으로 물러나고 통과로 세지 않는다. `docs/RELEASE.md` §2.8 의
확인 절차가 5채널 기준으로 바뀌었다.

### 2.2 origin 없는 저장소에서도 worktree 가 모 브랜치를 이어받는다 (`cbe0b88b`, TASK-2026-10-02-main-003)

기본 브랜치 판정이 remote 가 없으면 현재 브랜치로 떨어져 seed 조건(`base != 현재`)이 깨지고 session-start 가
`missing_required_document` 로 멈췄다. seed 전용 후보 판정(`path_resolver._seed_base_branch_candidates`)을 분리했다 —
origin 이 있으면 종전 판정, 없으면 `init.defaultBranch` → `main` → `master` 중 **로컬에 실재하고 handoff 가 있는 첫 것**.

### 2.3 진입점 다이어트가 v1.20.0 생성물을 알아본다 (`b64024b2`, TASK-2026-10-19-main-001)

채취 ref 가 다이어트 직전 커밋에서 멈춰 v1.20.0 · v1.20.1 로 bootstrap 한 진입점의 7절이 '알려진 생성물' 에 없었다.
`DEFAULT_REFS` 에 v1.20.0 을 더해 재채취(해시 102 → 112, 삭제 0). `check_entry_diet` case 6 이 하네스 12개를 하나씩
bootstrap 해 모든 절이 알려진 생성물인지 재고, case 7 이 데이터 모듈의 채취 ref 가 스크립트와 같은지 잰다 — 템플릿을
바꾸고 재채취하지 않으면 red 다. `harvest --ref X --apply` 는 거절한다(부분 채취가 나머지 해시를 지운다).

### 2.4 메모리 lint 가 branch-scoped 레이아웃을 본다 (`9f027210` · `094a51ba`, TASK-2026-10-19-main-002 · 003)

`check_memory_lint` 네 축이 v0.6.1 의 legacy 경로를 보고 있었다. T1b(stale)는 루트 공유층만 mtime 으로 재다 시간 경과만으로
red — 브랜치 메모리의 마지막 **git 커밋 일자**로 재고 공유층(`migrate_memory_to_branch_scoped.KEEP`)은 면제한다. T1a 는
`check_state_reconcile` 이 정본이라 은퇴. T1c(orphan) · T1d(missing)는 브랜치별 task 파일 ↔ daily index 를 대조하고, 참조
ID 를 index 의 `path:` 선언 → 브랜치 `tasks/` → `archived/` 순으로 해소한다. ID 정규식에 안 맞는 참조는 통과로 세지 않고
숫자로 보고한다.

### 2.5 goal coverage 가 '닿을 수 없는 goal' 을 지목한다 (`e88e4b48`, TASK-2026-10-19-main-004)

PURPOSE §1 에 있지만 어느 마일스톤 · leaf 도 선언하지 않은 goal 은 어떤 완료 항목으로도 닿을 수 없는데, session-start 는
warnings 없이 uncovered 로만 냈다. 이제 `선언 없는 goal: G4, G5 — … goals/wbs_goals 에 적으면 닿는다` 가 provenance 로
실린다. 수치 · 산식은 그대로다(섬기지 않는 goal 은 진짜 공백).

### 2.6 `minimax_plugin --apply` 가 바뀐 것을 보고한다 (`077474d8`, TASK-2026-10-06-main-009)

반영 **뒤** 상태를 찍어 첫 설치가 '13개 이미 일치' 로 읽히던 것을, 반영 전 기준으로 '<옛> → <새>' 를 보고하도록 고쳤다.
무변경은 백업을 만들지 않고, 반영 뒤 불일치면 rc 1 이다.

## 3. 검증

- 전량 게이트 `--branch-context=all` — 발행 준비 커밋에서 실행 (결과는 발행 기록에 남긴다)
- 각 task 는 별도 컨텍스트의 `verifier` subagent 가 완료 기준을 다시 쟀다 — 되주입 red 건수: main-001 7/7 · main-002 7/11
  (생존 중 1건은 git fixture 로 고정) · main-003 9/9 · main-004 4/7 (생존 중 2건을 fixture 로 고정, 1건은 상수 단일 출처라 의도된 생존)
- `check_minimax_plugin_channel` · `check_branch_memory_auto_seed` 는 macOS 호스트에서 mcode 0.6.2 · origin 0 저장소로 실측
- 해석기 매트릭스는 이번 minor 에서 **돌리지 않았다** — 변경이 I/O · 해석기 민감 코드가 아니고(SQLite 는 표준 라이브러리),
  하한 문법은 게이트의 `check_python_floor_syntax` 가 3.10 해석기로 잰다

## 4. 알려진 한계 (감추지 않는다)

- doctor 의 minimax-code 활성 판정은 SQLite 한 곳에 의존한다 — MiniMax Code 가 경로 · 표 이름을 바꾸면 '모름' 이다.
  Windows 의 DB 경로는 미실측.
- G4 · G5 의 선언은 소유자 결정 대기 — 적용 전까지 session-start 가 '선언 없는 goal: G4, G5' 를 낸다.
- Windows 실물 실측 3건(cp949 · wk.exe 백신 차단 · emit python3)은 그대로 열려 있다.
- v1.20.1 노트 §4 의 한계는 그대로다.
