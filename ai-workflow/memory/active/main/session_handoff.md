# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-09-28 (92차 세션 **종료** — task 10건 close: 게이트 처리량 · 결함 수리 · 세션 시작 컨텍스트 예산 concept→구현 완주, 필독 195→111KB)
- 이전 수정일: 2026-09-28 (91차 세션 **종료** — M-014 ① 안 구현: LPT + jobs=코어 수 + wiki_score 반복 제거, telemetry 경합·오염 수리)
- 이전 수정일: 2026-09-28 (90차 세션 **종료** — M-014 concept 종결(① 안) + Linux 호스트 python 3.14 업그레이드로 깨진 개발·MCP 환경 복구 + PURPOSE.md 개정)
- 이전 수정일: 2026-09-25 (89차 세션 **종료** — CI 폐지 뒷정리 + push 를 게이트 통과 기록에 묶음 + 무력하던 force 차단 hook 수리)
- 이전 수정일: 2026-09-24 (88차 세션 **종료** — main-020 감사 반복 제거 + **GitHub CI 테스트 workflow 폐지**, 발행 게이트 근거를 로컬 게이트 통과 기록으로)
- 이전 수정일: 2026-09-23 (87차 세션 **종료** — v1.11.0 환경 배포 정리 + 중첩 worktree 호스트 의존 red 수리 + 워크플로우 평가 → 이슈 10건 등록 · M-013(세션 컨텍스트 예산) · M-014(CI 처리량) 개설)
- 이전 수정일: 2026-09-23 (86차 세션 **종료** — task 8건 close + **v1.11.0 발행**. 두 결함족: 판정이 아무것도 재지 않는데 숫자는 멀쩡하다 / 범위가 좁은데 '대상이 없다' 로 보인다)
- 이전 수정일: 2026-09-21 (83차 세션 **종료** — 경고 게이트의 두 구멍: 부모 프로세스 경고 미수집 + 판정이 __pycache__ 에 달려 재실행만으로 green)
- 이전 수정일: 2026-09-21 (82차 세션 **종료** — 해석기 축 선언화: CI smoke 4셀(브랜치 2 × 해석기 2) + 저장소 코드가 낸 Python 경고를 게이트 red 로, 우연이던 3.13 커버리지를 선언으로)
- 이전 수정일: 2026-09-21 (81차 세션 **종료** — '범위가 조용히 좁으면 그 밖이 갈라진다' 4건 close: goal coverage 어휘→선언 / wiki_trend 시계 의존 / ENFORCES 축 신설 / smoke 수 포함목록→전수 / Python 하한을 실물 해석기로)
- 그 이전 수정일: 2026-09-18 (80차 세션 **종료** — 파생물 3건 close: backlog-update 가 roadmap_state 를 두고 갔다 / 노출 한 칸 첫 실측 / content_drift 가 읽히지 않는 사본을 재고 있었다)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **93차 세션 (2026-09-28, Linux 호스트 i5-1335U) — task 2건 close (TASK-2026-09-23-main-014 · 09-28-main-014), **v1.12.0 발행**.** 발행 뒤 이 호스트 채널 재적용을 `docs/RELEASE.md` §2.8 로 절차화 + `wk doctor` `content_drift.behind`(읽히는 사본 < 정본 버전 → 발견) 신설. §2.8 을 이 호스트에서 첫 실행: codex·grok-build·antigravity 1.10.0 → 1.11.0, claude-code 설치 기록 1.9.4 → 1.11.0, doctor `behind=[]`. **v1.12.0**: `release-status` 가 `!` 2건으로 2.0.0 제안 → `534e3a8d` 가 동결 표면 공개 API 2종을 유예 없이 지운 것이 드러남 → 소유자 결정 minor + 은퇴 shim(v1.13.0 제거). 태그 → `c26c92f8`, asset 4종, 발행 wheel 격리 설치 실측, §2.8 재적용 두 번째 실행(4채널 1.12.0). 이 호스트에 `python3.14-venv` 가 없어 packaging 점검이 실패했었다(설치로 해소). 남은 것: claude-code CLI 재시작(`runtime_load`). **교훈 재확인**: task close 뒤 `--changed` 에서 `check_handoff_next_steps` red — §5 후보가 닫힌 task 를 가리켰다.
- 직전 기준선: **92차 세션 (2026-09-28, Linux 호스트 i5-1335U) — task 10건 close, 세션 시작 컨텍스트 예산 축(M-013→M-017)을 concept 에서 구현까지 하루에 완주. 필독 195.1KB → 111.5KB.** 상세는 각 task 파일(SSOT). ①**게이트 처리량** (M-014 C) — main-007 release 계열 검사 내 mypy 반복 제거(44.2→28.3s) · main-008 러너·CLI 검사의 무거운 fixture·네트워크 제거(46.9→12.3s, `release-doctor --skip-mypy` 신설, git 추적 `.score_history.jsonl` 쓰기 경합 제거) · 검사 간 mypy 공유는 **보류(소유자)**. ②**결함 수리** — main-009 validate source 정본화(`VALIDATE_SOURCES`, plugin_payload skip 불가 = 소유자 결정, `check_validate_source_coverage`) · 09-23-main-015 대시보드 phase 를 로드맵에서 파생 · 09-23-main-016 + main-010 task ID 충돌 검출(대시보드 지표 + session-start warning). ③**컨텍스트 예산** — 09-23-main-012 concept(③ 출구+예산) → main-011 requirements(Q1~Q5 권고안) → main-012 design(ADR-029 accepted) → main-013 구현: `common/context_budget.py`(예산 4 · 현재형 절 목록) · `wk refresh-state` 초과 경고 · `state.json.memory_entries` v2 포인터(68.8→21.4KB) · `wk rollover-handoff-notes`(§5 누적형 17절 → `lessons.md`/`sessions/`, 39.6→7.9KB) · `CLAUDE.md` 운영 절 → `docs/LOCAL_GATE.md`(19.6→11.3KB) · `check_session_context_budget` 이 저장소 red 활성. **교훈**: task 를 `--changed` 뒤에 close 하면 handoff §5 후보 검사가 게이트에서야 red · `backlog-update --status done` 은 `--validation-result` 없이는 조용히 보수 유지 — frontmatter 를 확인할 것. 후속: §5 현재형 20KB(예산 밖, 관찰) · macOS 10코어 B 측정.
- 그 이전 기준선: **91차 세션 (2026-09-28, Linux 호스트 i5-1335U) — task 4건 close (09-28-main-004 · 09-28-main-003 · 09-28-main-005 · 09-28-main-006), M-014 ① 안 구현 완료. 게이트 두 축 합 277.5s → 218~220s (−21%).** ①**main-004** — `check_wiki_score` 멱등성 case 의 s1 을 공유 실행으로: 점수 도구 3→2회, 단독 27.3s → 18.3s, 비멱등 되주입 시 여전히 red. ②**main-003** — 병렬 구간 LPT 제출 + `--jobs auto` = 코어 수. 소요 출처 = `.git/run_all_checks_durations.json` 기록 → `CHECK_TIMEOUT_S` 선언 → 알파벳, `schedule:` 줄에 출처별 개수. 게이트 3회 실측 cold 224.1s / warm 218.0·220.1s (추정 ~208s 보다 +10~12s — 긴 검사끼리 앞에서 겹쳐 늘어짐, `branch_context_matrix` 50~53s/상한 150s). `check_parallel_smoke` case 11~13, 되주입 6건 전부 red. ③**LPT 가 드러낸 기존 경합** — `check_warning_gate` case 6 의 `tests/` probe 를 전수 컴파일 검사 2건이 읽다 red (알파벳순에선 `w` 가 끝물이라 우연히 안 겹쳤다) → 정숙 구간으로. 실측 표는 `local-gate-throughput-review-2026-09.md` §8. ④**push 게이트 1회 red → main-005 close** — `check_memory_index_cross_v0_15_7` 가 telemetry 이중 읽기 경합으로 slash 축 red. 대시보드가 telemetry 를 3회 읽던 것을 스냅샷 1회로 공유하고 Panel 8 의 별도 hit 정의를 흡수(실데이터 전 필드 동일), case 5 로 경합을 결정적으로 주입해 고정(되주입 2종 red). 쓰는 검사 5개 전수 실측 → ⑤**main-006 close** — writer 가 `WORKFLOW_KIT_TELEMETRY_SKIP_ROOT` 루트 아래는 안 쓰고(러너가 모든 검사에 주입, 환경을 좁히는 검사 2개는 표식 전달), 러너가 축마다 실제 `events.jsonl` 증가를 red 로 잰다(gitignore 라 git status 감시 밖이었다). 되주입 5종 red. 후속: macOS 10코어 호스트에서 B 이득 1회 측정 · C 다음 건(`release_*` 반복 계산).
- 그 이전 기준선: **90차 세션 (2026-09-28, Linux 호스트 i5-1335U) — task 3건 close (main-019 · 09-28-main-001 · 09-28-main-002), 2건 open (09-28-main-003 · main-004), M-014 done.** ①**환경** — 시스템 python 이 3.13→3.14 로 올라가 `.venv`(심볼릭 해석기)와 사용자 site 의 kit editable 이 함께 사라졌다: `wk` ModuleNotFoundError + 플러그인 MCP 2종 Connection closed. `.venv` 는 `uv venv --seed` 로 재생성(3.14 에 ensurepip 없음), `/usr/bin/python3` 에는 `uv pip install --prefix ~/.local -e ./workflow-source`. `core.hooksPath=.githooks` 도 이 호스트에서 켰다. ②**main-019** — M-014 concept 종결(`docs/planning/local-gate-throughput-review-2026-09.md`): 게이트 3회 실측(k=8 268/278s, k=12 249s) — 병렬 구간은 **처리량에 묶임**(최장 검사 35~40s < 처리량 하한 89~94s), 알파벳순 제출이 꼬리. 스케줄 시뮬레이션이 실측과 1s 이내. 소유자 ① 안 = LPT + jobs 상한→코어 수(추정 −25%) + 반복 계산 건별 수리, 두 축 동시 실행은 이득 0 으로 기각. ③**09-28-main-002** — `PURPOSE.md` 가 101일 stale 로 `check_memory_lint` red → 소유자 검토로 개정(G5 로드맵·SDLC 추가, 하네스 범위 플러그인 중심, state.json 생성물 정정, G3 재확인).
- 그 이전 기준선은 [`baselines.md`](./baselines.md) 에 있다 (이관 106건, 최신이 위).

- 현재 주 작업 축: **로드맵·마일스톤·WBS 진척 관리 + SDLC 온보딩 기본 — 60차(2026-08-25) 소유자 지시로 확정.** ADR-027 accepted, 정본 스펙은 [`roadmap_milestone_wbs_spec.md`](../../../../workflow-source/core/roadmap_milestone_wbs_spec.md) (M-001 design 완료, 구현은 M-002~M-006 단계 실행 — 스펙 §10 이 임시 로드맵 정본). 직전 축(배포 일관성·멱등성)은 ✅ gap 4개 전부 닫혔다 (2026-08-18, 48차). 정본은 [`workflow_deployment_idempotency.md`](../../../../workflow-source/core/workflow_deployment_idempotency.md). ~~[main-016] `wk doctor`~~ ✅ · ~~[main-017] 채널 재실행 계약~~ ✅ (47차) · ~~[main-005] 드리프트 감지(페이로드 해시)~~ ✅ · ~~[main-019] 환경 pre-flight~~ ✅ (48차). 탐침은 이제 **7절**이다 (53차 `runtime_load` 신설 — 노출 미측정 한 칸을 측정으로 옮겼다). ~~[main-010] §7.0.2 의 '버전 상이' 셀~~ ✅ (53차 — 실측 + `installPath` 선언을 읽도록 교정). ~~[TASK-2026-08-14-main-009] 라벨 영어 전환~~ ✅ (53차 — 4단계 종료). ~~[main-004] wiki 3-step 하위 두 단계~~ ✅ (49차 — 1단계 은퇴 / 2단계 수리 / 3단계 재작성). **열린 후보**: ~~OKF v0.2 이행 ADR~~ ✅ (2026-08-20 ADR-026 로 전체 이행 완료, TASK-2026-08-20-main-003 — 이 줄이 그것을 안 따라와 58차가 낡은 후보를 다시 검토했다; 잔재였던 매니페스트 '0.1' 하드코딩은 58차 main-008 이 걷음) · ~~wiki L1→L2 갭 85개~~ ✅ (50차 — 계약을 4종으로 좁혀 닫음) · cross-host federation(MacBook, 시점 추후) · ~~[TASK-2026-08-13-main-004] mypy flake 관찰~~ ✅ (66차 close — 33/33 표본, mypy 실패 0).
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
-
## 3. 차단 작업

- 현재 `blocked` 작업:
- TASK-2026-08-25-main-017 MCP emit command 가 항상 python3 — PATH 에 python3 이 없는 Windows 에서 emit 설정으로 서버를 spawn 할 수 없다
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-09-28-main-014 v1.12.0 발행 준비 — 삭제된 공개 API 에 deprecation shim 복원 + 버전 bump
- TASK-2026-09-23-main-014 발행 후 로컬 소비 채널 갱신이 절차에 없어 설치본이 조용히 낡는다
- TASK-2026-09-28-main-013 세션 시작 컨텍스트 예산 — implementation (출구 먼저, red 나중)
- TASK-2026-09-28-main-012 세션 시작 컨텍스트 예산 — design (ADR-029 + core 스펙 절)
- TASK-2026-09-28-main-011 세션 시작 컨텍스트 예산 — requirements (출구 + 예산)
- TASK-2026-09-23-main-012 세션 시작 필독 문서 부피 예산 — concept 검토
- TASK-2026-09-28-main-010 task ID 충돌 검출을 session-start warning 으로도 낸다
- TASK-2026-09-23-main-016 멀티에이전트 충돌 지표가 task ID 충돌을 못 센다
- TASK-2026-09-23-main-015 상위 요약의 phase 표시가 v0.15 에 멈춰 있다 — 상수 표시
- TASK-2026-09-28-main-009 release validate 의 source 목록 사본이 따로 낡는다 — '전부 skip' 이 새 source 를 못 따라감
그 이전 완료 항목은 [3차 세션 기록](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md)·[2차 세션 기록](./sessions/adr006_retrospective_and_calibration_2026-08-10.md)과 각 task 파일에 있다.

## 5. 다음 세션 시작 포인트

- 누적 기록은 [`lessons.md`](./lessons.md) (규칙 10절) · [`sessions/handoff-notes_*.md`](./sessions/) (기록 7절) 로 이관됐다 — 최신이 위, 세션 시작에 읽지 않는다.

### ▶ 지금 할 일 — M-007 운영 축 상시 운용 (63차 전환, 64·65차 검증)

**로드맵 현황**: M-001~M-006 done + **M-007 운영 축 상설 [stabilization]
in_progress** + **M-008~M-012 done** (64차 — 첫 병행 기능 축의 SDLC 완주:
`parallel_allowed: [M-007]` 계약이 실전에서 섰다. concept→release 하루,
게이트·재링크·done 경계 전부 설계대로 동작). 진척 정본은
[`roadmap_state.json`](../roadmap/roadmap_state.json). 새 작업은 M-007 의
반복 범주 leaf(7.1 플랫폼 / 7.2 탐침·도구 / 7.3 관찰·지표 / 7.4 릴리스·채널)에
링크하고, **exempt 는 이제 진짜 로드맵 밖에만** 쓴다. 새 기능 축은 M-013+ 로
선언하되 자기 파일에 `parallel_allowed: [M-007]` 을 적는다.

**커밋 전 단계가 바뀌었다 (v1.7.0, R4.2)**: 관련 검사를 사람이 고르지 않고
`run_all_checks.py --changed` 가 선언으로 고른다. meta-watch 가 게이트에
상주하며 좁은 선언을 red 로 잡는다 (분류 현황: **국소 208 / 전역 14 / 미분류 68**
— 86차 실측. 66차 보급 완주 이후. 남은 68건은 표면이 source 트리 전체라 선언해도 선택 이득이
0 이므로 일부러 미분류다. 미분류 개수가 관찰 지표다). 보급 절차는 스펙 §2.1 —
선언은 `--meta-watch-dump` 채취에서 뽑고 한 단계 넓혀 적는다. push 게이트
전량 2축은 불변.

**61차(Windows 호스트) 가 시작한 Windows 플랫폼 결함 축은 62차가 대부분 닫았다** —
전부 'POSIX 호스트 기준으론 써졌고, Windows 에서 조용히 썩는다' 의 한 모양이었다.
~~main-020(state.json 백슬래시)~~ ✅ (62차 close — CI green 확인) ·
~~main-018(emit PYTHONPATH)~~ ✅ (62차 — target 레이아웃 기준으로 교정) ·
~~main-019(전역 도구의 외부 체크아웃 해석)~~ ✅ (62차 — doctor `kit_resolution`
탐침 신설). main-017(MCP emit `python3`)은 **코드 수리 완료 + Windows 실측만
잔여** — 소유자 결정(62차) = ① 플랫폼별 커맨드명, 정본 `python_launcher` 신설,
체크인 산출물(플러그인 payload·예시)은 `platform="posix"` 고정으로 해시 안정
유지, preflight 는 bootstrap 채널만 launcher 해석(플러그인 채널은 payload 가
`python3` 리터럴을 spawn 하므로 리터럴 유지). v1.5.0 발행 시점 CI red 는 원격
세션이 수리 완료 — 62차 확인: 최신 main push 의 워크플로 전부 green. 다음 세션도
`gh run list --branch main` 으로 **main 의 워크플로 전체 상태** 를 본다.

> **이 절의 계약** (TASK-2026-08-22-main-001). 아래는 판정 기준이 **다른 부류**로
> 나뉜다. 예전에는 한 목록에 섞여 있었고, 그중 둘은 이미 기계가 읽는 자리를 가진
> 채 산문이 그것을 **복제**하고 있었다 — 복제는 갈라진다 (2026-08-20 하루에 잔재
> 2건). 각 부류는 자기 SSOT 를 가리키고, 산문은 *왜 그것이 후보인가* 만 적는다.
> **작업 후보 항목은 반드시 열린 task ID 를 인용한다** — `check_handoff_next_steps`
> 가 그 task 가 실제로 `planned` / `in_progress` 인지 대조한다.

#### 작업 후보 — 정본은 `state.json` 의 `planned_items` · `in_progress_items`

> **`main-002` 는 84차에 닫혔다** — 판정 정본을
> `workflow_kit/common/doc_stamp.py` 로 승격해 **쓰는 쪽도 같은 규약을 읽는다.**
> `doc-headers-update` 는 뒤처진 문서만 올리고 건너뛴 수를 `skipped_current` 로
> 말한다. 실측: 안 바뀐 92개 건너뜀 / 고친 1개만 갱신.
>
> **그 소급은 `main-004` 로 끝냈다** — 97건을 실제 내용 변경일로 교정했다(최대
> −126일). 다만 **판정을 먼저 고쳐야 했다**: `last_content_change_date` 가 스탬프만
> 바꾼 커밋도 내용 변경으로 세고 있었고, 그대로 되돌리면 전부 red 가 됐다.
>
> **남은 것은 범위다.** 게이트도 `doc-headers-update` 도 보지 않는 문서 **284건**의
> 스탬프가 뒤처져 있다 (`.omo/` · `QUICKSTART.md` 등). 옛/새 판정에서 수가 같으므로
> 기존 상태이고 이번 작업이 만든 것이 아니다 — 범위를 넓힐지는 별도 판단이다.

> **`main-003` 은 84차에 닫혔다** — 폴백이 **트리 전체의 최신 mtime** 이다
> (`_tree_newest_mtime`). 미측정으로 내리는 선택지는 쓰지 않았다: 트리 최댓값이
> 병합 복사에서도 실제 갱신 시각을 내는 것을 실 설치본에서 확인했기 때문이다
> (`09-18 00:16` → `09-22 03:01`, 39개 훑음). 그래도 **폴백임은 출처 문자열에
> 남는다** — 선언 기록(`installed_plugins.json`)을 읽는 채널과 근거가 다르다.

> **`main-001` 은 84차에 닫혔다** — 원인은 권한이 아니라 `gh issue comment` 에
> 없는 `--header` 플래그였고, 마커는 본문 끝 HTML 주석으로 옮겼다. 실증은 종료
> 코드가 아니라 **게시 단계 success + `#22` 코멘트 0 → 1** 로 했다.
>
> 남은 관찰: **이 실패가 3개월간 아무 데도 신호로 안 떴다.** 필수 CI 가 아닌
> cron 워크플로의 만성 red 를 어디서 볼지는 별도 판단이다.

> `main-001` · `main-002` · `main-003` 은 전부 v1.10.0 발행 준비·실행 중에
> 드러났고, **셋 다 84차 안에 닫혔다.** 발행 절차를 밟는 것 자체가 탐침이었다. **발행 절차를 밟는 것 자체가 탐침이었다** — 평소 경로로는 안
> 밟히는 자리들이다.

> **경고 게이트는 `main-007` 로 닫혔다 (82차).** 저장소 코드가 낸 Python 경고와
> `<unknown>`(문자열 compile 산물)은 검사 자신이 exit 0 이어도 게이트 red 다.
> 서드파티는 **보고만** 한다 — 전수 census 에서 두 해석기가 갈린 2건이 전부
> 그 부류였고 원인도 해석기가 아니라 venv 의 의존성 해석 차이였다. 정본
> `workflow_kit/common/check_warnings.py`, 판정 `check_warning_gate.py`.
> 의도한 deprecation 호출은 `call_deprecated` 로 감싼다(삼키되 단언한다).

> **그 게이트의 두 구멍은 `main-008` 로 닫혔다 (83차).** 수집 지점이 per-check
> 서브프로세스 출력 하나뿐이라 ① runner **부모** 가 낸 경고(kit 모듈 44/196 이 그
> 경로로 컴파일된다)와 ② `.pyc` 가 따뜻해 **아예 나지 않는** 컴파일 시점 경고를 둘 다
> 못 봤다. ②는 **소스를 그대로 둔 채 1차 `exit 1` / 2차 `exit 0`** 으로 실측됐다 —
> 고친 것 없이 재실행만으로 green 이 되는 게이트였다. 수리는 `PARENT_WARNINGS`(부모)
> 와 `check_source_compile_warnings`(저장소 소스 전수 566개를 메모리 `compile()`,
> 캐시 무관이 원리적). 정본 요구는
> `test_impact_tiering_spec.md` 의 `compile-warning-verdict-is-cache-independent`.
>
> 범주를 하드코딩하면 안 된다 — invalid escape 는 3.12+ 에서 `SyntaxWarning`,
> **3.11 이하에서 `DeprecationWarning`** 이다. 83차가 그것으로 3.11 셀에서만 red 를
> 냈고, 82차가 만든 해석기 축이 자기 자신을 잡았다.

> **해석기 축은 `main-006` 으로 닫혔다 (82차).** 정본 =
> `workflow_kit/common/interpreter_matrix.py` 의 `GATE_INTERPRETERS`, CI smoke 는
> 브랜치 2 × 해석기 2 = **4셀**, 로컬 재현은
> `python3 -m workflow_kit.common.interpreter_matrix --run-local`.
> **로컬 게이트는 안 늘렸다** — 벽시계 비용은 CI 셀 병렬로 옮겼다.
>
> 착수 전 가설('3.13 은 이미 로컬이 덮는다')이 실측에서 뒤집혔다: 그 커버리지는
> **선언이 아니라 우연**이었고(`.venv` 를 3.11 로 다시 만들면 조용히 사라진다),
> CI 가 못 보는 부류가 이미 살아 있었다 — 3.12+ 에서만 나는
> `SyntaxWarning: invalid escape sequence` 를 5개 검사가 3.13 에서만 보고
> 3.11(CI)은 완전히 침묵했다. 설계 3안 중 **선언된 부분집합은 기각**했다:
> 실측에서 민감한 쪽이 *저장소 소스를 파싱하는 검사* 라 미리 목록화할 수 없다.

> **Python 하한 축은 main-005 로 닫혔다 — 다만 CI 는 부분 측정이다 (소유자 보류).**
> 로컬은 실물 3.10 으로 전수(553개)를 컴파일하지만, CI 에는 `uv` 도 `python3.10` 도
> 없어 `feature_version` 부분 측정으로 떨어지고 **PEP 701 부류를 못 본다**. 검사가
> 그 사실을 `[unmeasured]` 두 줄로 출력한다. 전수로 올리려면 `smoke.yml` 에 `uv`
> 또는 3.10 setup 한 단계가 필요하다 — 2026-09-21 소유자 지시로 **올리지 않았다**.
> 현재 CI 커버리지는 `mypy-strict` 가 3.10 을 밟는 **우연한** 것뿐이고 그건 선언이
> 아니다. 필요해지면 그때 올린다.


> **81차가 연 축: `ENFORCES` 보급** (`TASK-2026-09-21-main-003` 에서 규약 확정).
> 현재 선언 3/285 이고 **미선언 282 는 의도된 관찰 지표**다 — meta-watch 의 `미분류 68`
> 과 같은 자리. 전수 이행을 게이트로 강제하지 않는 이유는 정본 스펙
> `test_impact_tiering_spec.md` §7.1 의 `Requirement: enforces-adoption-is-observed-not-gated`
> 에 적혀 있다. 보급은 **결함을 고칠 때 그 검사에 한 줄 얹는 방식**이 기본이고,
> 일괄 이행 세션을 따로 열지 않는다. 지표는 선언 수가 아니라 *미선언 수의 추이* 다.

> **G4 가 uncovered 인 것은 실측 결과이지 결함이 아니다** (`main-001`).
> 최근 완료 작업이 deprecation 전달 축(G4)을 실제로 밟지 않았다. `WBS-7.4`(릴리스·채널)에
> G4 를 얹으면 coverage 가 100% 상수가 되므로 일부러 얹지 않았다 — '안 한 일' 이 지표에
> 보이는 쪽을 택했다. **소유자가 다르게 보면 M-007 파일의 `wbs_goals` 한 줄로 바뀐다.**


> **mypy 게이트 flake 는 66차에 닫혔다** (`TASK-2026-08-13-main-004`, 관찰 9차).
> 62차 소유자 결정의 close 기준 — '격리(`19e40ac9`) 후 완료 smoke run 33건에서
> mypy 게이트 실패 0' — 을 **33/33 · 실패 0** 으로 충족했다. 표본 중 failure 6건은
> `--log-failed` 전수 분류 결과 전부 deterministic 비-mypy(스탬프 드리프트 4 ·
> 생성물 정합 2). close 의 주 근거는 통계가 아니라 **기전**이다: 경합면(공유
> `.mypy_cache`)이 제거됐고 캐시 생성 0 이 실증돼 있다. **재발하면 새 task 로 연다** —
> 증거 그물(`--show-traceback` + 결론-우선 절단)은 이미 게이트 안에 있다.

> **`TASK-2026-09-07-main-009` 는 87차에 닫혔다** — macOS 재측정에서 세 PID 가
> 모두 소멸, `runtime_load` 낡은 호스트 0 (claude-code·codex).
>
> **87차 평가**([`workflow-assessment-2026-09.md`](../../../../docs/planning/workflow-assessment-2026-09.md))
> 가 이슈 7건을 등록하고 새 기능 축 **M-013**(세션 시작 컨텍스트 예산, concept)을
> 열었다. 이어 소유자 제기로 **M-014**(CI·게이트 처리량, concept)와 반복 계산 수리 2건을 열었다. 아래 순서가 평가 §6 의 권고 순서다.
> **M-014 는 90차에 concept 종결** — 병렬 구간은 처리량에 묶여 있고 알파벳순 제출이
> 꼬리를 만든다. 구현은 M-007/WBS-7.2 의 main-003 · main-004 로 옮겼다.
> **91차에 둘 다 close** — 게이트 두 축 합 277.5s → 218~220s (−21%, 추정 ~208s).
> 소요 기록은 `.git/run_all_checks_durations.json` (호스트 로컬 순서 힌트, 지워도
> 선언·알파벳으로 돈다). 실측은 [`local-gate-throughput-review-2026-09.md`](../../../../docs/planning/local-gate-throughput-review-2026-09.md) §8.

> **89차가 남긴 결정 대기 2건** — ①발행 게이트가 해석기·SDK 매트릭스 실행 기록을 요구할지
> (요구하면 발행당 전량 × 해석기 수, 09-24-main-001 follow-up) ②원격 브랜치 **삭제** push 를
> force 차단 hook 이 막을지 (지금은 통과, 09-25-main-002 follow-up). 새 클론·호스트는
> `git config core.hooksPath .githooks` 를 한 번 켜야 push 게이트가 선다.

> **main-014 는 93차에 닫혔다** — 발행 뒤 이 호스트 채널 재적용이 `docs/RELEASE.md` §2.8 이 됐고,
> `wk doctor` 의 `content_drift.behind` 가 '읽히는 사본 < 정본 버전' 을 발견으로 낸다. 이 호스트의
> 실제 재적용(1.10.0 → 1.11.0)도 93차에 §2.8 대로 실행해 doctor `behind=[]` 확인 — 남은 것은 claude-code CLI 재시작뿐.

> **v1.12.0 은 93차에 발행됐다** (`TASK-2026-09-28-main-014`) — minor + 은퇴 shim. **v1.13.0 에서
> `verify_required_ci` · `REQUIRED_CI_WORKFLOWS` 를 지운다** (deprecation policy spec §3.7 마지막 체크박스).

- `TASK-2026-09-23-main-017` · `TASK-2026-09-23-main-018` — 방치 worktree 정리
  (소유자 확인) / memory_index 소비 편중 관찰.

> **세션 시작 컨텍스트 예산 축(M-013→M-017)은 92차에 구현까지 닫혔다** — 예산 정본 `common/context_budget.py`, 넘치면 `wk refresh-state` 가 출구 명령과 함께 경고하고 이 저장소 게이트(`check_session_context_budget`)가 red. §5 에 `###` 절을 새로 쌓았으면 세션 종료 때 `wk rollover-handoff-notes --apply`.

> **main-015 · main-016 은 92차에 닫혔다** — 대시보드 `phase` 를 로드맵 정본에서 파생 /
> 충돌 지표가 task ID 충돌(미커밋 task ↔ 원격 같은 ID·다른 제목)을 센다. 후속 후보:
> 그 검출을 session-start warning 으로도 낼지 → **main-010 으로 92차에 닫음**.

> **`TASK-2026-08-25-main-017` (MCP emit `python3`) 은 78차에 blocked 로 옮겼다
> — 무기한 연기 (소유자 결정).** 완료 기준 1(수리 + 판정)은 77차에 끝났고 회귀는
> `check_mcp_emit_launcher_sweep` 이 상시 보증한다. 남은 것은 기준 2(Windows
> 실측)뿐인데 실측 호스트 확보 시점이 정해지지 않았다. **후보로 올리지 않는다** —
> Windows 호스트를 확보한 세션에서만 재개한다.
> **문서 스탬프 하드코딩은 72차에 닫혔다** (`TASK-2026-09-01-main-002`). 기대값이
> 리터럴이 아니라 **git 파생**이다 — `스탬프 >= 그 문서의 마지막 내용 변경일`
> (`tests/_doc_stamp.py`). 발행 post-step 이 스탬프를 올려도 손댈 자리가 없다.
> 판정 자체는 `check_doc_stamp_rule.py` 6 cases 가 격리 저장소에서 고정한다 —
> **문서를 읽어 기대값으로 삼는 동어반복**과 **유예를 더러운 트리까지 넓히는 것**
> 둘 다 그 검사가 막는다.
> **패키징 선언 누락 결함족은 72차에 닫혔다** (main-001). `[tool.setuptools] packages`
> 는 손 목록이라 세 번(`common.*` v0.5.7.1 · `tools` v1.1.7 · `cli` v1.8.0) 같은
> 모양으로 빠졌다. 이제 `check_deployed_layout` **case 5** 가 디스크 하위 패키지와
> 그 선언을 매 게이트마다 양방향 대조하고, `check_packaging` 의 `REQUIRED_IMPORTS`
> 는 손 목록이 아니라 **디스크 파생**이다. **다음 하위 패키지는 세션이 아니라
> 게이트가 잡는다.** 이 수리는 **v1.8.1 로 발행됐다** — 73차가 v1.9.0 wheel 내용을
> 실측해 `workflow_kit/cli/doctor.py` 가 실려 나가는 것을 확인했다.
> **발행 게이트의 CI 범위와 `done` 강등 보존은 v1.9.0 으로 발행됐다** (73차,
> main-005 · main-003). 그 게이트는 v1.8.1 **태그 뒤에** 착지해 v1.8.1 소비자에게는
> 없었고, 자기 발행(`ff7ed4bc`)에서 처음 물었다 — `required_ci ok=true, blocking=[]`.
> **미발행 잔여는 현재 0 이다.**
> **'자기 위치 오인' 결함족은 65차에 닫혔다** (main-003·012·013). 위 줄이 예고했던
> "다음 수리 때 전수 조사" 를 그대로 했고, **수동 grep 4건에 정적 검사가 3건을 더
> 얹었다**. 정본은 `paths.resolve_workspace_root()`, 게이트는
> `check_self_location_resolution` case 8 (`TOOL_MODULES` 전 진입점의
> `add_argument` 기본값이 `__file__` 파생이면 red). **다음 사본은 세션이 아니라
> 게이트가 잡는다** — 이 항목이 후보 목록에 다시 오를 일은 없어야 한다.

~~`TASK-2026-08-25-main-022` local_mypy 오탐~~ ✅ (63차 close) ·
~~`main-023` 경로 해석~~ ✅ (63차) · ~~`main-002` update 재링크~~ ✅ (63차) ·
~~`main-003` archive memory-root~~ ✅ ~~`main-012` release-bump pyproject~~ ✅
~~`main-013` 결함족 전수 마감~~ ✅ (전부 65차) ·
~~`main-004`(08-28) concept~~ ✅ ~~`main-005` requirements~~ ✅
~~`main-006`·`main-007` design~~ ✅ ~~`main-008` 구현~~ ✅ ~~`main-009` mcp
2.1.1~~ ✅ ~~`main-010`·`main-011` release~~ ✅ (전부 64차 — 위 기준선).

#### 소유자 결정 대기 — task 가 아니다

결정이 나야 작업이 생긴다. 여기 있는 동안은 `planned` task 로 채번하지 않는다 —
채번하면 영원히 `planned` 로 남아 위 목록을 오염시킨다.

- ~~**memory_index 승격 후보 처리** (59차 성립)~~ — ✅ **해소** (60차,
  2026-08-25, 소유자 결정 = ①상위 후보 승격, TASK-2026-08-25-main-001):
  coverage 0.0 후보 2건을 `MEM-2026-08-25-001`(watch_transient flake) ·
  `-002`(세션 시작 자기 복구)로 승격. 재실측 덮인 것 2/10→**4/10**, 후보 8→6,
  저점 고착 해제. 잔여 후보 6건(coverage 0.17~0.33)의 추가 승격 여부는
  **관찰 축**의 지표 추이가 다시 고착을 가리킬 때 재론한다.
- ~~**MCP emit 해석기 방향 결정** (61차, main-017·018)~~ — ✅ **해소**
  (62차, 2026-08-25, 소유자 결정 = **① 플랫폼별 커맨드명**): win32 는
  `python`, 그 외 `python3` — emit 의 '공유 파일에 절대 경로 금지' 계약을
  지키는 보수적 수리. ②(`sys.executable`)는 머신 고유 절대 경로를 공유
  파일에 굽어 기각. 구현·검증은 main-017/018 task 파일 참고. 한계도 결정에
  포함: 체크인되는 플러그인 payload 는 `python3` 리터럴을 유지하므로
  (해시 고정), Windows 에서 플러그인 채널은 여전히 `python3` 별칭이 필요
  (INSTALLATION_AND_USAGE §7.0.0 플랫폼 주의).

#### 환경 상태 — 정본은 `wk doctor`

여기에 목록을 적지 않는다. 적으면 탐침이 이미 재는 것을 산문이 복제하게 되고,
고쳐도 산문이 안 따라온다. **`wk doctor` 를 돌려서 본다.**

- 현재 알려진 것 (61차 `wk doctor` 실측, 이 머신 = Windows 11): 설치 채널
  6개 전부 block — `python3` 부재(5개) + `claude` CLI 부재(claude-code).
  codex/gemini/pi CLI 는 실재. **이 머신에는 플러그인 설치 캐시가 없다**
  (content_drift caches 0, 전역 설정 4종은 존재하나 kit 선언 0) — 60차의
  '양 채널 1.5.0 재적용 · drift 0' 은 원격 호스트 상태였다. `runtime_load` 는
  `ps` 부재로 미실측(호스트 0 = 해당 없음). CLAUDE.md 는 포크본(v1.0.0-beta
  fork, 마지막 수동 병합 v1.3.0/2026-08-20) — 재적용은 파괴적이므로 kit 갱신은
  diff 후 수동 병합.

#### 관찰 축 — 신호를 기다린다

작업이 아니라 조건이 성립하기를 기다리는 것들이다.

- cross-host federation (두 번째 호스트 = MacBook 확정, **시점 추후**)
- **로드맵 exempt 비율** (60차 시작, 스펙 §11) — 정본은
  `roadmap_state.json` 의 `exempt_tasks`. 첫 실측(2026-08-25) 1/15(7%) →
  로드맵 close 후 등록 전건 exempt 로 상승, **트리거 성립 → 63차 M-007
  상설 마일스톤으로 해소** (열린 exempt 0, done 이력 7건 유지). 관찰은
  전제를 바꿔 계속한다: 이제 exempt 는 진짜 로드맵 밖 뿐이어야 하며,
  **열린 exempt 가 다시 쌓이면** M-007 leaf 범주가 현실과 안 맞는다는
  신호다 — leaf 를 늘리기 전에 범주 정의를 재검토한다 (M-007 파일 계약).
- memory_index 3-tuple 지표 추이 — 60차(2026-08-25) 승격 2건 반영 후
  `wk suggest-memory-entries`: 덮인 것 **4/10**, 후보 6건(threshold 0.5,
  coverage 0.17~0.33). 57~59차의 저점 고착(2/10)은 소유자 결정(승격)으로
  해소됐다. 트리거는 동일하게 유지 — **같은 수치가 3회 이어지면 소유자에게
  다시 묻는다** (다음 선택지에는 잔여 후보 추가 승격과 threshold 재캘리브레이션이
  올라간다).

### 82차가 남긴 규칙 (재발 방지)

- **되주입 harness 자신도 되주입 대상이다.** 주입 두 건의 소스 **길이가 같으면**
  `.pyc` 가 (mtime+size 로) 유효 판정돼 재사용되고, 복원한 원본 대신 **직전
  주입본이 실행된다**. 실제로 case 2 가 case 1 의 증상을 냈다. harness 는
  `PYTHONDONTWRITEBYTECODE=1` + `__pycache__` 삭제를 깔고, **각 주입이 자기
  이유로 red 인지** 를 눈으로 확인한다 — '전부 red' 는 각 판정이 살아 있다는
  증거가 아니다.
- **'문자열이 파일 어딘가에 있다' 는 배선 검사가 아니다.** `case 4` 는 파일
  전체에서 `matrix.python` 을 찾았는데 job 이름·artifact 이름에도 그것이 있어
  **정작 `setup-python` 배선을 끊어도 green** 이었다. 배선은 *받는 자리* 를 보고,
  그 자리의 값을 **전부** 나열해 하나라도 다르면 red 로 한다.
- **커버리지가 '이미 있다' 고 말하기 전에 그것이 선언인지 묻는다.** 3.13 커버리지는
  개발자 `.venv` 에 깔린 것이었고 아무 문서도 그것을 요구하지 않았다. 지우면
  조용히 사라지고 아무 검사도 실패하지 않는 커버리지는 **없는 것과 같은 취급**을
  받아야 한다 ('우연한 측정은 선언이 아니다' 재발, 2026-07-31 이후 두 번째).
- **정본의 방향은 registry → yml 이다.** task 등록 때 '기대값을 `smoke.yml` 에서
  파생' 이라고 적었는데 그러면 사본이 정본이 된다. `branch_matrix` · `sdk_matrix`
  가 이미 반대 방향으로 서 있다 — 새 축도 같은 방향으로 세우고, yml 의 리터럴은
  **복제로 검출**한다.

### 80차가 남긴 규칙 (재발 방지)

- **파생물이 둘이면 한쪽만 안다.** 한 도구가 생성물을 하나 갱신하고 있으면 "이미
  하고 있다" 가 "다 하고 있다" 로 읽힌다. `backlog-update --apply` 가 `state.json`
  은 재생성하면서 형제인 `roadmap_state.json` 은 두고 간 것이 그것이다 — 그 SSOT
  가 *방금 자기가 쓴* task frontmatter 인데도. **형제 파생물을 전수로 셀 것.**
- **정본 문서가 재생성 창구를 하나만 적으면, 그것이 다른 쓰기 경로를 규약 밖에
  두는 근거가 된다.** 스펙 §7.1 의 "재생성은 `wk refresh-state`" 가 정확히 그렇게
  쓰였다. 창구가 아니라 **누가 SSOT 를 쓰는가**로 적는다.
- **두 사본이 byte 동일이면 파일 비교는 원리적으로 아무것도 못 가른다.** 어느
  쪽이 읽히는지는 **한쪽만 오염시켜** 재야 한다. 캐시 사본에 마커를 넣고 새
  프로세스에 물어서야 "캐시는 안 읽힌다" 가 나왔다 — 그 전까지 `content_drift` 는
  아무도 안 읽는 사본을 재면서 in-sync 를 노출의 증거처럼 내놓고 있었다.
- **경유지는 사본과 별개로 판정을 바꾼다.** codex 에서는 경유지가 *사라지면*
  문제였는데(main-004), claude-code 에서는 경유지의 **유형**이 *무엇이 읽히는지*
  를 바꾼다. 설치 경로를 선언에서 읽는 것만으로 부족하다 — 그 선언이 가리키는
  것이 서빙되는 것인지까지 봐야 한다.
- **보고 문자열의 채널 리터럴을 의심할 것.** marketplace 행이 무조건
  `codex marketplace …` 로 찍히고 있었다. 목록이 단일 채널이던 동안은 맞았고,
  채널이 하나 늘어나는 순간 조용히 틀렸다.
- **착수 전에 자기가 적은 전제를 다시 잰다.** main-006 의 완료 기준 3번이 틀린
  전제("서빙 경로 = 정본 생성기의 입력")로 적혀 있었다. 정본은 `core/` 에서
  렌더되고 `plugin/` 은 입력이 아니라 산출물이다 — 어제의 나도 남이다.

### 79차가 남긴 규칙 (재발 방지)

- **'이 호스트' 는 쓴 사람의 호스트다.** 77차가 `이 호스트 소비자 채널 재적용` 을
  done 으로 남긴 뒤에도 plex 의 claude-code 는 **5주간 v1.1.8-beta** 였다. 채널 상태는
  세션마다 기록이 갈리는 값이라 **handoff 산문으로 판정하지 않는다** — `wk doctor` 를
  그 호스트에서 돌려서 본다. 반대로 채널 재적용을 기록할 때는 **호스트 이름을 제목에
  박는다**(이 세션의 main-002 가 그렇게 했다).
- **세션 시작의 첫 동작은 `git fetch` + behind 확인이다.** 159커밋 뒤처진 체크아웃에서
  `session-start` 는 **44차 기준선을 복원하면서 `status: ok, warnings: []`** 를 냈다.
  도구는 낡은 입력을 낡았다고 말하지 않는다 — 복원된 기준선의 날짜가 오늘과 한 달
  떨어져 있으면 그것이 신호다.
- **`--wbs` 를 붙인 task 는 로드맵 SSOT 를 바꾼다 — `wk refresh-state` 가 따라와야 한다.**
  `backlog-update --apply` 는 `roadmap_state.json` 을 재생성하지 않아
  `check_roadmap_state_generated` + `check_state_json_generated` 가 함께 red 가 된다.
  **78차 ⑤ 와 79차 ⑤ 가 같은 자리다 — 이틀에 두 번이면 다음은 도구가 잡을 자리다.**
- **포크 병합은 렌더된 문서가 아니라 렌더러 함수로 잰다.** 포크가 한국어고 kit
  템플릿이 영어라 문서 diff 는 65줄이 전부 다르게 나오고, 그 안에서 실제 델타를
  고르는 일은 사람이 할 수 없다. `git show <tag>:renderers.py` 로 렌더 함수만 뽑아
  대조하면 3초에 끝난다 (79차 실측: v1.3.0→HEAD 델타는 1건, 그것도 산출 동일).
- **게이트 종료코드는 파이프 뒤에서 사라진다.** 배경 실행의 래퍼는 마지막 명령(`tail`)의
  코드를 보고 `exit code 0` 이라 보고했지만 게이트는 red 였다. `GATE_EXIT=$?` 를 따로
  찍어 두지 않았으면 red 인 채로 커밋했다.

### 65차가 남긴 규칙 (재발 방지)

- **결함족은 사본이 아니라 판정으로 닫는다.** '자기 위치 오인' 은 네 세션에 걸쳐
  사본 하나씩 닫혀 왔고, 그때마다 "다음에 전수 조사" 라고 적혔다. 65차에 실제로
  전수를 하니 **수동 grep 4건 · 정적 검사 7건** 이었다 — 사람이 고른 패턴이 놓친
  3건(`consumer-metrics` 는 설치본에서 site-packages 에 history 를 쌓고 있었다)을
  AST 가 찾았다. 같은 모양이 3회 이상 반복되면 수리와 **함께 판정을 만든다.**
- **경로를 옮길 때 대상만 옮기면 절반이다.** archive 는 "git 에 그 브랜치가 있나"
  로 아카이브를 결정하고, migrate 는 `git mv` 를 돌리고, detect-scope-drift 는
  `git show`/`git log` 를 쓴다. 대상 트리만 cwd 로 옮기고 **git 질의 저장소와
  브랜치 해석**을 모듈 위치에 두면, 남의 브랜치 목록으로 이 workspace 를 판정한다.
  판정의 근거가 되는 축을 전부 세고 같이 옮긴다.
- **검사의 green 이 결함에 기대고 있을 수 있다.** `check_seed_workspace_memory` 는
  fixture 에 profile 이 없어서, seed 가 **모듈 저장소의 profile 을 빌려** state.json
  을 만들어 green 이었다 — 소비자 workspace 에 kit 의 프로젝트 메타를 찍는 결함
  그 자체였다. 도구를 고쳤더니 검사가 red 가 되면, **먼저 fixture 가 무엇을 전제로
  green 이었는지** 본다 (여기서는 fixture 가 비현실적이었던 쪽이 맞았다).
- **설치본에서 돌 수 없는 명령은 조용히 실패하지 말고 거부한다.** release 파이프라인은
  kit 자기 릴리스 기계다. 설치본에는 대상 트리가 없으므로 `FileNotFoundError` 대신
  **설치본 위치 · cwd 체크아웃 · 대체 명령**을 찍고 exit 2 한다. cwd 체크아웃의
  코드를 대신 로드하는 길은 62차 `foreign_path` 판정과 정면으로 부딪히므로 안 쓴다.

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
