# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-20 (50차 세션 — main-001 close: **L2 계약 축소 + 지표 분모 재정의**)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **51차 세션 종료 — v1.3.0 발행 + 관찰 축 실측 + 채널 파리티 (task 9건 close, push 7회, 전량 2축 매번 green, 검사 264 유지).** 상세는 [50~51차 세션 기록](./sessions/release_v1_3_0_and_channel_parity_2026-08-20.md). 직전 항목은 **main-008·009**: 사용자가 만든 session-end 스킬이 이 환경에서 안 쓰이던 문제.** **두 채널이 서로 다른 스킬 집합을 노출하고 있었다** — 플러그인은 처음부터 4종인데 bootstrap(`.claude/commands/`)은 3종만 emit(생성기 docstring 이 스스로 '3 slash command' 라 적고 있었다). 게다가 진입 스킬의 `description` 은 **이미 세션 종료를 약속**하고 있어서, 광고는 4단계인데 배선은 3개인 상태였다 — 모델이 있지도 않은 명령을 찾는다. 생성기에 `session-end` 명령을 넣고 진입 스킬 본문을 4종으로 맞췄고, **두 채널 집합을 대조하는 파리티 검사 2종**을 신설했다(개수만 세면 이름이 어긋난 채 통과한다). `/workflow-session-end` 는 파일을 쓰자마자 **이 세션에서 바로 잡혔다**. **남은 절반(main-009)**: 플러그인 스킬 4종이 인벤토리엔 있는데 세션엔 없다. 가설 4개 기각(파일 부재 · 비활성 · 매니페스트 파손 · **세션보다 늦은 설치** — 설치가 21시간 앞선다). 확정: `claude plugin details` 는 `Skills (4)` 로 다 세는데 호출하면 `Unknown skill` — **인벤토리는 세션 가용성의 증거가 아니다**. 그래서 `wk doctor` 의 `content_drift` 에 **노출 미측정 선언**을 넣고(`in_sync` 는 '쓸 수 있음' 이 아니다 — main-019 의 `installable` 과 같은 원칙) INSTALLATION §7.0.1 에 확인 방법을 적었다. **그 뒤 원인이 확정됐다 (52차 대조 실험 + 53차 확증)** — 충돌도 파손도 아니라 **시간**이었다. 호스트 프로세스가 설치보다 35시간 먼저 시작했고 플러그인은 **프로세스 시작 때** 로드된다 (`/clear` 는 프로세스를 재시작하지 않는다 — **세션은 프로세스의 대리값이 아니다**). 51차의 기각이 틀렸던 것은 잰 *단위*였다. 그 조건은 잴 수 있으므로 `declared_unmeasured` 에서 한 칸을 측정으로 옮겼다 — `wk doctor` 에 **`runtime_load` 절**(설치 시각 vs 실행 중 호스트 시작 시각, `etime` 만 읽어 로케일 비의존) 신설, 탐침 6→7절. 53차가 재시작 뒤 실제 호출로 확증했다: 플러그인 채널 로드 성공 + 같은 시점 `runtime_load` 가 claude-code `낡음 0 / 최신 1`, codex 낡은 호스트 3개. 검사 264 유지 (`check_deploy_doctor` 17→20 cases).
- 직전 기준선: **51차 세션 (이어서) — main-007 close: **v1.3.0 발행** (https://github.com/ykylee/standard_ai_workflow/releases/tag/v1.3.0, asset 4종).** 101 커밋 누적분. 소유자 결정은 **minor** 였고, 그 판단을 `docs/RELEASE.md` **§1.5** 로 정본화했다 — `!` 는 '무언가 깨진다' 는 표시일 뿐 **무엇이** 깨지는지 말하지 않으므로, 우리가 SemVer 로 보장하는 **공개 API** 기준 4문항으로 등급을 본다(공개 시그니처 / 진입점 소멸 / 소비자가 못 읽게 되나 / 외부 spec 버전). **외부 spec 버전이 오른 것만으로는 major 가 아니다** — v1.3.0 의 `feat(okf)!` 를 적용 사례로 근거 4가지와 함께 박았다(시그니처 변경 0 · 은퇴 진입점이 남아 rc=0 · 번들이 legacy 유지 · SPEC §13 자신이 minor 라 규정). **태그에서 `-beta` 가 빠진 첫 릴리스**다(§2.2 규약이 v1.2.1 부터 정리됐고 도구도 그렇게 만든다 — `v1.2.0-beta` 가 옛 표기의 마지막). 릴리스 노트는 자동 skeleton 을 버리고 축 4개 + 도구 결함 수리로 재작성했다. 버전 범프 파생물 **13종** 재생성. 부수: `check_deploy_doctor` fixture 가 설치 버전을 `"1.2.0"` 리터럴로 박고 있었다 — `__version__` 파생으로 바꿨다(리터럴이면 릴리스마다 red 가 되고, 그때 고치는 건 계약이 아니라 그 시점 상수다). 검사 264 유지.
- 그 이전 기준선: **51차 세션 (이어서) — main-006 close: `release-status` 의 `next_version` 이 커밋을 읽지 않았다.** 릴리스 경계를 판단하려다 도구 결함을 먼저 만났다. `_suggest_next_version` 이 **현재 버전 문자열 하나만** 받아 `patch+1` 을 내놓았는데, 그 값이 같은 summary 줄에서 **`unreleased=101` 옆에 찍힌다** — 개수는 세면서 판정은 안 세니 파생값처럼 보이는 상수였다 (feat 17 · fix 24 · **breaking 1** 인 사이클에 `1.2.1` 을 권했다). 이제 미발행 커밋 유형에서 파생한다: breaking → major · feat → minor · 그 외 → patch · 근거 없으면 patch 이되 `basis.total=0` 으로 **모름을 밝힌다**. 교정 결과 `next=2.0.0` + basis(breaking 제목 포함). **숫자만 내밀지 않는 것이 설계의 핵심**이다 — 이 저장소는 v0.8.0 에 API 를 얼렸으므로 major 승격은 사람 결정이고, 도구는 판정과 **근거**를 같이 낸다(`requires_decision`). 부수: `check_release_status_auto_bump_v0_11_16` 의 기대값 `0.11.17` 이 patch 휴리스틱을 인코딩하고 있어 저장소 이력에 결합돼 있었다 — `_unreleased_commits` 를 mock 해 그 case 가 **재려던 것**만 남겼다. 되주입 3종 red 실증, 검사 264 유지.
- 그 이전 기준선: **51차 세션 — 관찰 축 3개 실측. 두 축에서 결함이 나왔고 셋째는 왜 못 재는지 밝혔다.** **① mypy flake (관찰 3차, main-004)**: 2차 기준선 이후 smoke **69 run 중 1건** 재발 — 그리고 **native 전용이라던 서명이 깨졌다**(이번은 slash). **원인 계열 확정: race 가 아니라 mypy INTERNAL ERROR(크래시)** — 아티팩트 `stderr_tail` 원문이 근거이고, 검사 `duration_sec` 0.65s 대 정상 3.4s/197파일이라 **분석 중이 아니라 시작 단계**에서 죽었다. 2차의 transient-파일 가설은 반증. **4번 터지는 동안 원인을 못 좁힌 이유는 절단 두 겹**이었다 — `smoke.yml` 의 `[:120]` 과 `_error_excerpt(400)` 이 사유를 잘라, 원인은 **아티팩트를 내려받아서야** 보였다; mypy 크래시는 보일러플레이트로 시작해서 앞에서 자르면 잡음만 남는다. 수리 3건(신호를 앞으로 정렬 · 요약 120→800 · excerpt 400→1200)이고 **검사는 상한을 복제하지 않고 smoke.yml 에서 읽는다**. 완료 기준을 개정: 'N run 연속 green' 은 원인을 모르던 시점의 기준이라 폐기 → **다음 재발이 트레이스백을 로그에 남길 것**. **② memory_index 3-tuple (main-004 신규)**: `query_diversity` 4/285 · `entries_new_30d` 2 · `distinct_entries_retrieved` **1/9** — 8/10 회고가 미리 적어 둔 판정 조건('항상 저점이면 W-1/W-2 가 안 도는 것')에 걸렸다. **원인은 검색이 아니라 배선**이었다: 회고가 추가한 종료 단계 `wk suggest-memory-entries` 가 `memory_index/README.md` 에만 있고 정본·CLAUDE.md·AGENTS.md 어디에도 없어(grep 0건) **한 번도 안 돌았다** — 실제로 승격 후보 5건이 대기 중이었다. 정본 §8.1·§11.1 에 넣고 진입점 재생성. **드리프트가 조용히 지나간 이유도 고쳤다**: `check_standard_single_source` case 3 이 §11 표에서 **대표 1개만** 봐서 6번째 명령 추가가 안 보였다 — 전 항목 대조 + **이 저장소 자신의 진입점**을 재는 case 신설. 새 절차를 이번 세션에 적용해 1건 승격(`MEM-2026-08-20-001`). **③ cross-host federation**: 두 번째 호스트(MacBook)가 없어 **이 호스트에서는 원리적으로 못 잰다** — 관찰이 아니라 대기다. **부수(main-005)**: 게이트 slash 축에서 `check_watch_transient_writer` 가 1회 red — `REQUIRES_QUIET_REPO` 가 아니라 **타이밍 가정**이었다(`SETTLE_S` 의 '폴링 간격의 20배' 근거는 폴러가 실제로 스케줄된다는 전제인데 16-way 병렬에서 깨진다). 고정 sleep 을 **관측 대기**로 바꿨다 — mypy flake 와 같은 계열이지만 이쪽은 우리 검사라 바로 고쳤다. 검사 264 유지.
- 그 이전 기준선은 [`baselines.md`](./baselines.md) 에 있다 (이관 58건, 최신이 위).

- 현재 주 작업 축: **배포 일관성·멱등성 — ✅ gap 4개 전부 닫혔다 (2026-08-18, 48차).** 실행형 잔여가 이 축에는 없다.**다음 축은 소유자 판단 대기.** 정본은 [`workflow_deployment_idempotency.md`](../../../../workflow-source/core/workflow_deployment_idempotency.md). ~~[main-016] `wk doctor`~~ ✅ · ~~[main-017] 채널 재실행 계약~~ ✅ (47차) · ~~[main-005] 드리프트 감지(페이로드 해시)~~ ✅ · ~~[main-019] 환경 pre-flight~~ ✅ (48차). 탐침은 6절이다. **release 경계 대기** — [TASK-2026-08-14-main-009] 라벨 영어 전환은 `TASK_FIELD_LABELS` 한 줄만 남았다. ~~[main-004] wiki 3-step 하위 두 단계~~ ✅ (49차 — 1단계 은퇴 / 2단계 수리 / 3단계 재작성). **열린 후보**: OKF v0.2 이행 ADR(main-006 후속, `status` 어휘가 실질 위험) · ~~wiki L1→L2 갭 85개~~ ✅ (50차 — 계약을 4종으로 좁혀 닫음) · cross-host federation(MacBook, 시점 추후) · [TASK-2026-08-13-main-004] mypy flake 관찰.
- ~~소유자 결정 대기: state.json 생성물 여부~~ — ✅ **해소** (TASK-018, 2026-08-11): **생성물로 확정.** 정본 §11.2 에 선언, `wk refresh-state` 로 재생성, `check_state_json_generated` case 5 가 이 저장소의 정합을 상시 검사. 상세 요약·산문은 state.json 이 아니라 handoff §4 와 task 파일(SSOT)에 남긴다.
- 다음 후보 축: ~~PyPI 발행~~ → ⛔ **닫힘 (2026-08-14 소유자 최종 결정 = 발행 안 함, `RELEASE.md` §1 각주 0)** / cross-host federation (두 번째 호스트 = **MacBook 확정, 시점 추후**) / memory_index 3-tuple 지표 추이 관찰. ~~federation self-host add~~ ✅ (14차) · ~~v1.1.9/v1.2.0 미발행 누적~~ ✅ **해소 (32차 — v1.2.0-beta 발행, 누적분 0)**. (v1.1.0·v1.1.1 노트 누적 표기는 TASK-014 에서 **미삽입 확정**, branch protection 은 소유자가 **보류 결정** (2026-08-11) — 둘 다 후보 축에서 제거.)
- 발견한 cross-project 패턴 (agent memory 추가):
  - **Federation pattern** (4 후보 검토: central ❌ / git ❌ / S3 ❌ / federation ✅)
  - **MCP/CLI dual mode** (operational tool 의 4종 wrapper)
  - **3-layer defense** (규약 + client hook + server protection)
  - **Scope drift detection** (3-way enum: planned_done / planned_undone / unplanned_done)
  - **time.mktime → calendar.timegm** (UTC timestamp KST 환경 함정)
  - **[project.scripts] entry points** (CLI 化 A안, venv e2e 검증)
  - **기존 dispatcher 확장 > 새 dispatcher** (진입점이 둘로 갈리면 `--help` 도 갈린다)
  - **serving 없는 pull 은 반쪽** (API 만 있고 부를 CLI 가 없으면 기능이 없는 것과 같다)
  - **모름 ≠ 안전** (검사에서 못 읽은 필드를 통과로 치면 거짓 안심을 준다)
- 최근 핵심 기준 문서:
  - [multi_workspace_orchestration.md](../../../../workflow-source/core/multi_workspace_orchestration.md) — **§0.7 상태표 + §7.1·§7.3 구현 표시** + §0.8 *아직 열려 있는 것* 4건
  - [global_workflow_standard.md §10](../../../../workflow-source/core/global_workflow_standard.md) — 다중 작업·협업 규칙
  - [MEMORY_GOVERNANCE.md](../../../../workflow-source/MEMORY_GOVERNANCE.md)

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
- TASK-2026-08-13-main-004 CI native 셀 mypy 게이트 flake — cmd_validate mypy 전역 스캔의 병렬 race 판정
- TASK-2026-08-14-main-009 task SSOT 4단계 — 본문 라벨 영어 전환 (release 경계)
## 3. 차단 작업

- 현재 `blocked` 작업:
-
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-08-20-main-009 플러그인 스킬 4종이 인벤토리엔 있고 세션엔 없다 — in_sync 를 쓸 수 있음으로 읽던 자리
- TASK-2026-08-20-main-008 session-end 가 bootstrap 채널에 없다 — 두 채널의 스킬 집합이 갈라져 있었다
- TASK-2026-08-20-main-007 v1.3.0 릴리스 — 101 커밋 누적분 발행 + breaking 표기 판단 기준 문서화
- TASK-2026-08-20-main-006 release-status 의 next_version 이 커밋을 읽지 않는다 — 개수는 세고 판정은 안 센다
- TASK-2026-08-20-main-005 watch_transient_writer 의 고정 sleep 이 병렬 부하에서 깨진다 — 시간이 아니라 관측을 기다린다
- TASK-2026-08-20-main-004 memory_index 3-tuple 관찰 — 저점 고착의 원인은 검색이 아니라 종료 절차 배선
- TASK-2026-08-20-main-003 OKF v0.2 이행 — ADR-026 + status 어휘 매핑 + sources 필드
- TASK-2026-08-20-main-002 날짜 롤오버 때 열린 task 가 mismatch 로 잡힌다 — linter 가 SSOT 대신 하루치 index 를 본다
- TASK-2026-08-20-main-001 wiki L2 계약을 memory 파생 4종으로 좁힌다 — L1→L2 경로 은퇴 + 지표 분모 재정의
- TASK-2026-08-18-main-004 wiki 3-step 파이프라인의 하위 두 단계가 죽어 있다 — 스키마·레이아웃 드리프트
그 이전 완료 항목은 [3차 세션 기록](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md)·[2차 세션 기록](./sessions/adr006_retrospective_and_calibration_2026-08-10.md)과 각 task 파일에 있다.

## 5. 다음 세션 시작 포인트

### ▶ 지금 할 일 — 소유자 판단 대기

배포 축은 48차, wiki L2 축은 49~50차에 닫혔다. **다음 축은 소유자가 고른다.**
상세는 [49차 기록](./sessions/wiki_l2_pipeline_revival_2026-08-19.md) +
[TASK-2026-08-20-main-001](./backlog/tasks/TASK-2026-08-20-main-001.md).

후보 셋 (준비 상태 순):

1. **[TASK-2026-08-14-main-009] 라벨 영어 전환** — **release 경계가 풀렸다** (v1.3.0 발행).
   `TASK_FIELD_LABELS` 한 줄만 남았고 case 10 이 안전을 선실증했다. 지금 가장 준비된 항목이다.
2. **플러그인 설치본이 1.2.0 에 멈춰 있다** — 저장소는 v1.3.0 을 냈는데 `installed_plugins.json`
   은 1.2.0 / `2026-08-18T00:57:53Z` 다. `wk doctor` 의 content_drift 도 claude-code·codex 양쪽에
   내용 차이를 보고한다. 갱신 후 `runtime_load` 가 다시 낡음을 말할 것이므로 **CLI 재시작까지**
   한 묶음이다.

~~[TASK-2026-08-20-main-009] 플러그인 스킬 미로드 원인 규명~~ ✅ **닫혔다** — 52차가 대조 실험으로
원인을 확정(프로세스가 설치보다 먼저 시작)했고, 53차가 재시작 뒤 실제 호출로 확증했다
(플러그인 채널 로드 성공 + 같은 시점 `runtime_load` 가 `낡음 0 / 최신 1`).

관찰 축: cross-host federation(MacBook, 시점 추후) · mypy flake · memory_index 3-tuple.

### 50차가 남긴 규칙 (재발 방지)

- **지표의 분모는 '찾은 것' 이 아니라 '선언한 것' 이다.** 찾은 파일을 분모로
  잡으면 **대상을 지울수록 점수가 올라간다.** discoverability·lifecycle 이 정확히
  그랬다 — stub 3장을 지워도 5.0 이었다.
- **표식 판정은 앵커링한다.** placeholder 를 부분 문자열로 찾으면 그것을
  *설명하는* 문서가 그것을 *가진* 것으로 세어진다 (실측: 5.0 → 3.75 오탐).
- **은퇴한 진입점은 옛 인자를 계속 받는다.** argparse 오류로 죽으면 호출자는
  이유를 못 듣는다 — 실행되고 **왜 아무것도 안 했는지 듣는** 편이 낫다.
- **계약을 좁힐 때는 근거가 언제 사라졌는지를 적는다.** "L1 page 마다 L2" 는
  외부 vault 시절엔 옳았고 v0.7.17 in-repo 전환으로 근거를 잃었다. 그 문장이
  없으면 다음 사람이 같은 사본을 다시 만든다.
- **손으로 푸는 일이 2세션 반복되면 도구 결함이다** (backlog 이월). ✅ main-002 에서 닫음 —
  그리고 결함은 예상한 자리(이월 누락)가 아니라 **출처 선택**에 있었다.
- **검사가 '불일치' 를 외치기 전에 자기가 무엇과 비교하는지 확인한다.** 두 값이 서로
  다른 범위를 재고 있으면 불일치는 결함이 아니라 **검사의 오답**이다.
- **판정을 복제하지 말고 생성기와 같은 함수를 부른다.** 린터가 생성기와 다른 규칙으로
  불일치를 말하면 고칠 대상이 어느 쪽인지조차 알 수 없다.
- **버전을 올리는 일은 생산 형식만의 문제가 아니다.** 소비 정책을 같이 보지
  않았다면 OKF v0.2 이행이 유일하게 실측된 상호운용을 조용히 끊었을 것이다.
- **도달 불가능한 분기는 검사되지 않은 분기다.** `older → error` 는 우리가 최신
  버전인 동안 아무도 밟지 못했고, 전제가 바뀌는 순간 결함이 됐다.
- **관찰이 지표가 아니라 배선을 찾아낼 수 있다.** 3-tuple 은 정직하게 저점을
  가리키고 있었고, 저점의 이유는 종료 절차 한 단계가 **에이전트가 읽는 문서 체인
  밖**이라 한 번도 안 돈 것이었다. 지표를 의심하기 전에 그 지표를 움직이는 절차가
  실제로 도는지 본다.
- **증거는 만들어 두는 것으로 부족하고 소비 지점까지 도달해야 한다.** stderr 를
  잡아 뒀어도 상위 요약이 120자에서 자르면 없는 것과 같다. 그리고 **신호가 앞에
  와야** 한다 — 보일러플레이트로 시작하는 메시지는 잘리면 잡음만 남는다.
- **인벤토리는 가용성의 증거가 아니다.** `claude plugin details` 가 `Skills (4)` 를
  세는데 세션에서 호출하면 `Unknown skill` 이었다. 설치·활성화·파일 실재·인벤토리를
  다 통과하고도 못 쓴다 — 마지막 한 칸은 **실제 호출**로만 재진다.
- **같은 킷을 두 채널로 노출하면 집합이 갈라진다.** 개수가 아니라 **집합**을 대조해야
  이름이 어긋난 채 통과하는 것을 막는다.
- **폴백은 조용히 하지 않는다.** 무엇을 정본으로 봤는지 결과에 남기지 않으면 통과도
  실패도 근거가 못 된다 (`summary.in_progress_source`).

### 49차가 남긴 규칙 (재발 방지)

- **`rc=0` 은 무해의 증거가 아니다.** wiki-emit 3단계는 성공 코드를 내면서
  `last_touched` 를 67일 뒤로 돌려 lifecycle 지표를 무너뜨렸다.
- **dry-run 만 재는 검사는 apply 결함을 구조적으로 못 본다.** 이전 8 cases 가
  전부 dry 경로라 두 크래시를 한 번도 볼 수 없었다. 새 22 cases 는 임시 fixture
  저장소에 **실제로 쓰고 결과 파일을 읽는다**.
- **하드코딩된 날짜·버전은 도구를 스냅샷 재생성기로 만든다.** "정식화" 라고
  적혀 있어도 안이 1회용 백필이면 도구가 아니다.
- **은퇴는 함수까지 지운다.** CLI 분기로만 막으면 다음 사람이 다시 부른다.
  정적 부재를 검사가 고정한다.
- **생성물에 표식을 박는다.** 사람 글과 파생물을 구분 못 하면 재emit 이 사람의
  글을 지운다 (`> Generated:`).
- **지표를 사람이 30일마다 손으로 떠받치고 있으면 그건 도구 결함이다.**
  L2 `last_touched` 가 정확히 그랬다.

### 48차가 남긴 규칙 (재발 방지)

- **검사는 "있는가" 가 아니라 "몇 개인가 / 어느 것인가" 를 재야 할 때가 있다.**
  포인터는 개수, git root 는 어느 저장소, Citations 는 헤딩 레벨 — 셋 다 존재만
  확인하는 단언이 결함을 통과시켰다 (한 세션에 세 번).
- **mock 은 정작 깨진 자리를 가린다.** `_git_root` 를 monkeypatch 한 7 cases 가
  그랬다. 한 case 라도 mock 없이 실제 해석을 재는 것을 둔다.
- **판정을 좁히지 않으면 검사가 현상 유지를 박제한다.** 넓게 짜서 60건이 걸리면
  예외 목록이 곧 검사가 된다.
- **진단 실행이 저장소를 바꿀 수 있다.** `wk wiki-emit` 진단 한 번에 L2 stub 4개가
  퇴행했고 `rc=0` 이었다. HEAD 클린 워크트리와 대조해 원복했다.
- **editable 설치는 배포 결함을 영원히 숨긴다.** SDK 매트릭스·브랜치 매트릭스에
  이어 **세 번째 사각지대**다. 배포 표면을 건드렸으면 비-editable wheel 로 한 번 잰다.

### 47차가 남긴 규칙 (유효)

- **`git stash` 는 워킹 트리 복원 수단이 아니다** — untracked 를 안 건드린다.
  로컬/CI 차이를 볼 때는 **HEAD 클린 워크트리**로 잰다.
- **되주입은 fixture 가 실제로 판별하는지까지 확인한다.** 48차에도 한 번 밟았다 —
  `REPO_ROOT` 정의까지 지운 주입은 import 조차 안 돼 무효였고, 원 결함 형태로 다시
  넣어 확정했다.
- **검사를 하나 늘리면 개수 표기 3곳이 같이 움직인다** — INSTALLATION · release
  note · smoke trend. 게이트가 잡아 주지만 미리 맞추면 한 바퀴를 아낀다.
- **게이트에 비켜 둘 로컬 파일은 없다.** 다시 park 가 필요해지면 그건 새 결함이다.

### 다음에 할 일 — 전량 검사 시간 (소유자 승인 2026-08-14)

"전량 검사가 매번 도는 게 진행을 더디게 한다" 는 지적에서 나왔다. 실측 결론:
**벽시계를 정하는 것은 255개가 아니라 8개다.** 그리고 **가장 큰 낭비는 도구가 아니라
사용 패턴이었다** — 이 세션에 전량 2축을 5번 돌렸는데 게이트로서 의미 있던 것은 1번뿐.

| | 1축 실측 (2026-08-14, 부하 있는 상태) |
|---|---|
| 벽시계 / CPU | 196s / 819s (255 checks) |
| 정숙 구간(직렬) | 61s — 그중 `no_repo_write` **39s (64%)** |
| 병렬 임계경로 | `wiki_score` **68s** 단독 |
| 1초 미만 | **160개** (개수는 비용이 아니다) |

- ✅ **즉시 적용**: `CLAUDE.md` 에 3단 규칙 명문화 — 편집 중 `--filter` / 커밋 전
  관련 검사 + `check_self_application` / **push 직전 1회만 2축 전량**.
- ① [TASK-2026-08-13-main-009] 무거운 8개 (임계경로 둘부터)
- ② [TASK-2026-08-14-main-003] `--changed` 선택 실행 (미선언은 항상 실행 + 스킵 출력)
- ③ [TASK-2026-08-14-main-004] 2축→1축 조건부 — **앞의 둘을 끝낸 뒤에.**
  절감은 가장 크지만 15연속 CI red 를 만든 그 비대칭이다. 안 하는 것도 결론이다.

### ⛔ 닫힌 안건 — PyPI 발행 안 함 (2026-08-14, 소유자 최종 결정)

**배포는 이 저장소의 GitHub Releases 하나로 간다.** 토큰·OIDC 운영 비용을 상시로 지는
대신 얻는 것이 지금 없고, 공개는 되돌릴 수 없는 2년 backward compat 약속을 낯선
소비자에게 지운다.

**이 안건을 다시 제안하지 않는다.** 기술 준비는 v1.2.0 에서 이미 끝나 있으므로("이제
올릴 수 있다") 제안이 계속 생길 자리다 — 그래서 결정과 함께 **재검토 트리거 3개**를
정본에 박아 두었다: [`docs/RELEASE.md` §1 **각주 0**](../../../../docs/RELEASE.md).
그 트리거(외부 사용자의 실제 요청 / 저장소 밖 배포 사유 / 소유자 지시)가 성립하기
전에는 열지 않는다.

- [TASK-2026-08-13-main-008] TestPyPI 리허설 → **취소**. 업로드는 실행되지 않았고
  앞으로도 하지 않는다. 업로드 직전까지의 실측 8종은 **이력으로 보존** — GitHub
  Releases 소비자에게도 유효한 검증이다(README 렌더링·메타데이터·이름 해석·라이선스
  동봉·진입점 등).
- `RELEASE.md` §1 의 **각주 1**(TestPyPI 1회 한정 허용, 2026-08-13)은 **만료**.
- 검토 문서 2건(`pypi-publication-policy-review` / `cli-distribution-review`)은
  **종결 표기** 후 근거 자료로만 남는다.

### 무엇이 끝났나 (2026-08-14, 37차 세션)

**브랜치 정리 — 36차 기능의 첫 자기 적용** (TASK-2026-08-14-main-001). 상세는
[세션 기록](./sessions/branch_cleanup_and_case7_false_positive_2026-08-14.md).

아래 36차의 종료 순서를 그대로 밟았고 **도구는 설계대로 동작했다**:
`origin/fix/archive-history-integrity` 삭제(고유 커밋 0, tip `f798947` 은 main 이력에 남음)
→ `wk archive-branch-memory --apply` 가 **이 handoff 의 세션 기록 링크 2건**과 아카이브된
`state.json` **5경로 전부**를 재작성했다. `.archived.json` 의 `open_task_ids` 는 `[]` 다.
`active/` 에 남은 브랜치 네임스페이스는 `main` 하나.

**종료 순서에 0번이 빠져 있었다.** 브랜치 task 가 `in_progress` 인 채였고(일은 끝났는데
파일이 안 따라왔다) 아카이브가 정당하게 막혔다. 아래 1번은 "이월" 만 말하고 **"내 일이
끝났으면 닫는다"** 를 안 말하고 있었다:

```bash
# 0) 내 브랜치 task 를 먼저 done 으로 마감한다 (완료 기준·작업 결과·검증 결과를 채워서)
#    --validation-result 가 없으면 backlog-update 가 done 을 in_progress 로 낮춘다
#    함정: --done-criteria / --result-note 는 반복해도 마지막 하나만 남는다 (append 아님)
```

**유령 ID 2건.** 이 handoff §4 와 36차 세션 기록이 가리키던
`TASK-2026-08-13-fix-…-001` 은 **존재한 적 없는 ID** 였다 (실재는 `…-08-14-…`) — 세션
기록의 `관련 문서` 링크는 태어날 때부터 죽어 있었고, §4 의 완료 기록은 어느 task 파일과도
연결되지 않았다. 호스트가 UTC 라 도구 기본 날짜는 `08-13`, 사람이 쓴 문장은 KST `08-14`
였다. 둘 다 실재 ID 로 교정.

**아카이브 직후 `check_archive_history_integrity` 가 red — 위양성이었다.** case 7 의 링크
정규식이 **자체 사본**이라 label 을 요구하지 않아(`](path "제목")` 형태), 링크 문법을
*설명하는* 산문을 링크로 오인했다. 하필 그 문서가 방금 아카이브한 세션 기록이다 —
**검사가 자기 세션의 기록을 못 견뎠다.** 문서를 고치지 않고 판정을
정본(`workflow_kit.common.markdown`)에 맞추고 사본을 걷었다. 위양성을 내는 검사는
무시당한다. case 14 를 **양방향**으로 새로 두었다 (예시 산문은 안 잡고, 진짜 깨진 링크는
잡는다) — case 7 은 살아 있는 저장소를 관찰할 뿐이라 "안 잡는" 쪽으로 무력화돼도 조용히
green 이기 때문이다. 되주입으로 실측 확인. 13 → 14 cases.

### 무엇이 끝났나 (2026-08-14, 36차 세션)

**브랜치 메모리 생애주기** (PR #25 병합). 상세는
[세션 기록](../../archived/fix/archive-history-integrity/sessions/archive_history_integrity_2026-08-13.md).

**브랜치 종료 순서** — 아카이브가 이제 미완료 task 를 막는다:

```bash
# 1) 미완료 task 를 먼저 처리한다 (이월했으면 원본에 carried_over_to: <새 ID>)
# 2) 브랜치 삭제 (아카이브는 '브랜치 부재' 를 종료 신호로 쓴다 — 역방향 점검)
git push origin --delete <branch> && git branch -D <branch>
wk archive-branch-memory --dry-run   # 막히면 어느 task 때문인지 알려준다
wk archive-branch-memory --apply     # 참조(링크·state.json)도 함께 재작성한다
```

막히면 우회하지 말고 이월한다. `archived/` 는 state 생성기도 dashboard 도 읽지
않으므로, 미완료인 채 넘어가면 그 작업은 어디에서도 안 보이게 된다.

### 무엇이 끝났나 (2026-08-13, 35차 세션)

**브랜치 메모리 네임스페이스 가드** (PR #24 병합). 상세는
[세션 기록](../../archived/fix/branch-memory-namespace-guard/sessions/branch_memory_namespace_guard_2026-08-13.md).

**브랜치를 파면 제일 먼저 이걸 돌린다** — 순서가 거꾸로면 절반짜리 네임스페이스가 되고
3검사가 red 다 (이번에 그 순서로 밟아 실측):

```bash
git checkout -b <branch>
wk seed-workspace-memory --branch <branch> --axis '<작업 축>' --task-title '<제목>' --apply
# ↑ 여기까지가 한 벌 — handoff + backlog + sessions + state.json 이 다 생긴다 (v1.2.1+)
wk backlog-update ... --mode update    # 이후 갱신
```

`wk backlog-update` 는 `backlog/` 만 만든다 (`tasks_dir.mkdir()` 의 부수효과).
`sessions/` 와 `session_handoff.md` 가 빠진다. 이제 `check_branch_memory_namespace` 가
커밋 전에 지목한다.

~~**미결로 남긴 것**: `fix/branch-memory-namespace-guard` 미아카이브~~ — ✅ **완료**
(`archived/fix/branch-memory-namespace-guard/`). 이제 `active/` 에 남은 브랜치
네임스페이스는 `main` 하나다.

### 무엇이 끝났나 (2026-08-10, 3차 세션)

**CI 재현성 회복 + smoke 병렬화** (TASK-016~019). 상세는
[세션 기록](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md).
2차 세션(TASK-008~015, ADR-006 후속 + v1.1.6-beta 발행)은 §4 하단 항목 참조.

**push 전 재현 명령이 둘로 늘었다** — 둘 다 CLAUDE.md 에 적혀 있다:

```bash
# 브랜치 매트릭스 (CI 는 2축, 로컬 무인자는 1축 — 이 비대칭이 15연속 red 를 만들었다)
python3 workflow-source/tests/run_all_checks.py --branch-context=all --tmp-dir=<실디스크경로>

# SDK 매트릭스 (mcp 를 쓰는 코드를 건드렸으면)
PYTHONPATH=workflow-source python3 -m workflow_kit.common.sdk_matrix --run-local
```

전량 검사는 이제 **기본이 병렬**(`--jobs auto`)이다. 재현이 필요하면 `--jobs 1`.
저장소 전역을 관찰하는 검사를 새로 만들면 파일 안에 `REQUIRES_QUIET_REPO = True` 를
선언해야 한다 — 안 하면 병렬에서 오탐이 난다.

### 다음에 할 일 (순서)

이 세션에서 **저장소 리팩터링 조사**를 했고, 아래는 그 결과다 (근거는 §6 아래
"조사로 확정된 것" 참조). 사용자가 우선순위를 정한 항목만 실행했다 (정숙 구간 근본
수정 = TASK-019). 나머지는 미착수:

- ~~`check_mypy_strict_v0_11_3` ~ `v0_11_10` 8개 제거~~ — ✅ **완료**
  (TASK-2026-08-11-main-001, smoke 268→260).
- ~~`ai-workflow` 아카이브 정리~~ — ✅ **완료** (TASK-2026-08-11-main-003,
  185파일 제거, wiki 참조 1건 + freeze 최소 세트 6건 보존, README 링크 교정).
- ~~`check_cache_*` 13개 통합~~ — ✅ **완료** (TASK-2026-08-11-main-004,
  31 case verbatim 보존, smoke 260→248).
- ~~`release_pipeline.py` 분할~~ — ✅ **완료** (TASK-2026-08-11-main-007,
  3908→3174 + 모듈 4개, 분석 지도 방식). `dashboard_data.py` ✅ (TASK-010, 2488→1526),
  `workflow_kit_cli.py` ✅ (TASK-011, 2095→583) — **대형 파일 분할 완결**.
- ~~`docs/presentations/*.pdf|pptx` 5.2MB~~ — ✅ **완료** (TASK-2026-08-11-main-009, 파생 바이너리 제거·소스 보존).
- ~~branch protection~~ — **보류 결정** (2026-08-11, 소유자). `main` 미보호 (404 실측)
  상태를 인지한 채 일단 켜지 않기로 함. 재검토 시 `wk check-branch-protection` 으로
  현황 판정부터 (도구는 판정만 한다 — v1.1.2 §2.3).
- ~~`mooneye` 브랜치 처리~~ — ✅ **완료** (TASK-2026-08-11-main-012, `origin/mooneye`
  삭제. 고유 커밋 0 — 172 커밋 전부 main 에 존재, `active/mooneye/` 부재로
  memory 아카이브 해당 없음).

## 6. 남은 리스크 / 확인하지 못한 것

- ~~`cmd_release --apply` 실전 미검증~~ — ✅ **해소** (v1.1.4-beta 발행으로 apply
  경로 전체 실증: tag push / gh release / dashboard emit / audit append).
- **호스트 환경 의존 게이트** — 시스템 python 에는 mypy/mcp/twine 이 없어 관련 검사가
  fail 한다 (venv 에서 전부 PASS — `.venv` 에 dev,release,mcp-sdk 설치돼 있음).
  release 는 반드시 venv 에서 돌린다.
- ~~TST-WF-01 advisory red~~ — ✅ **해소** (TASK-004, 측정 재설계로 hard 복귀 +
  compliant). 남은 흔적: v0.15.18 dummy wrapper 는 측정에서 배제될 뿐 파일에
  남아 있다 — 물리 제거는 115 파일 churn 이라 별건.
- **darwin homelab 에서 mavis e2e 재확인 필요** — 검사를 정본 읽기로 바꿨으므로 mavis
  설치 호스트에서 한 번 돌려 기존과 동일하게 green 인지 확인하는 것이 안전하다.
- ~~title drift 임계 0.6 heuristic~~ — ✅ **해소** (TASK-008, 실측 캘리브레이션으로
  0.6 유지 확정 + `check_title_drift_calibration` 이 재캘리브레이션을 강제).
- ~~registry loopback 만 실측~~ — **부분 해소** (TASK-009, 비-loopback bind + pull
  왕복은 이 호스트에서 실측). **잔여**: 진짜 cross-host / 방화벽 / reverse proxy /
  TLS 종단 — 두 번째 호스트 필요 (darwin homelab).
- ~~`check_no_repo_write` 의 계약 한계~~ — ✅ **해소** (TASK-2026-08-12-main-009, 실행-중 폴링 + 원장). 이전 기술: 판정이 "실행 **후** 복원되었는가"
  라, 건드렸다 되돌리면 통과한다. `check_bidir_link_v0_13_3` 은 **이미 감시 목록에
  있었는데도** 그 이유로 안 잡혔다. 실행 *중* 감시(폴링)로 강화하면 남은 감시 대상
  다수가 같은 이유로 red 가 될 수 있어 범위가 크다. **되돌리는 것은 안 건드리는 것이
  아니다.**
- ~~amend Guard 2 의 staged-삭제 fatal~~ — ✅ **해소** (TASK-2026-08-11-main-002,
  `needs_add_only` 선별 + case 10 되주입으로 고정. §4 참조).
- **transient pyproject writer 정체 미상 (2026-08-11 1회 관측)** — 병렬 전량
  실행 중 원본 `pyproject.toml` 이 일시 변경됐다 되돌아왔다 (version_auto_sync
  byte-대조가 포착). 재현 실패 (표적 3회 + 전량 2회 + 50ms md5 watcher).
  관찰자 3검사는 정숙화(TASK-008)로 위양성 차단됨. **감시 수단은 저장소에
  고정됨** (TASK-013, `workflow-source/tools/watch_transient_writer.py` —
  일회용 `~/tmp` 스크립트의 승격판): 재발 의심 시 전량 검사 옆에 백그라운드로
  세워 두면 diff + ps 전량 + fuser 를 이벤트별로 남긴다 (로그는 temp 에만,
  저장소 안 로그는 거부). `check_watch_transient_writer` 5 case 가 되주입
  양방향으로 계약을 고정. `check_no_repo_write` 의 "실행 후 복원" 계약 한계와
  같은 뿌리로 추정 — writer 특정 자체는 재발 시의 일이다.
- **정숙 구간 6건** (TASK-008 로 3→6) — `check_no_repo_write`(전역 관찰) /
  `check_parallel_smoke`(runner 호출) / `check_source_without_runtime_layer`
  (저장소 복사) 는 본질적 직렬이고, `version_auto_sync` / `self_recovering` /
  `bidir_link` 는 원본 byte-대조 관찰 때문 (TASK-008). 병렬화로 더 줄이려면
  이들의 설계 자체를 바꿔야 한다.
- 이 밖의 과거 세션 리스크 (`--force` 3rd layer 미가동)는 변화 없음 —
  2026-08-09 까지의 세션 기록 참조.

## 7. 저장소 구성 조사 (2026-08-10 3차 세션)

리팩터링 판단 근거. git 추적 **1766 파일**:

| 영역 | 파일 | 비고 |
|---|---|---|
| `workflow-source` | 898 | tests 268, workflow_kit 129, releases 171, tools 74 |
| `ai-workflow` | 778 | **backlog tasks 193 + 아카이브 142**, wiki 81, sessions 18 |
| `docs` | 36 | presentations PDF/PPTX 가 **5.2MB** |

- **"버전 접미사 71개 = 중복" 은 틀렸다** (이 세션에서 정정). 주제별로 갈라보니
  대부분 고유하고, 진짜 중복은 `mypy_strict_v0_11_3~10` 8개뿐이다.
- 테스트가 느렸던 주된 원인은 **저장소 크기가 아니라 실행 방식**이었다 (순차 →
  병렬로 345s→118.8s). 위 정리 항목 중 실행 시간을 실제로 줄이는 것은 mypy 8개
  (15초) 뿐이고 나머지는 저장소 위생 문제다 — 섞어서 "정리하면 빨라진다" 고 말하지
  않는 편이 정확하다.

**이전 세션들의 교훈**은 각 세션 기록에 있다:
[2026-08-09](./sessions/cli_dispatcher_and_rotation_2026-08-09.md) ·
[2026-08-08](./sessions/multi_workspace_orchestration_2026-08-08.md) ·
[2026-08-05](./sessions/self_application_and_mcp_2026-08-05.md) ·
[2026-08-07 MCP](./sessions/mcp_load_verification_2026-08-07.md) ·
[2026-07-27](./sessions/selfref_cleanup_and_ci_measurement_2026-07-27.md)
