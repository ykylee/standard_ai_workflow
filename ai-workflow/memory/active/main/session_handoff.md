# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-25 (61차 세션 **종료** — cross-host 플랫폼 형식 수리(safe_relpath POSIX) + Windows 플랫폼 결함 task 3건 등록 / 60차 — ADR-027 로드맵 축 완결 + v1.5.0 발행 / 59차 — doctor pip 오탐 수리 / 58차 — OKF 매니페스트 버전 잔재 수리 + mypy flake 관찰 5차 / 57차 — v1.4.0 발행 + mypy flake 규명)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **61차 세션 종료 (2026-08-25, Windows 호스트 Oh My Pi) — main-020 in_progress (CI 대기) + Windows 플랫폼 결함 3건 등록 (main-017·018·019 planned).** **① cross-host 플랫폼 형식 결함을 잡고 닫았다** (main-020): `safe_relpath` 이 `os.path.relpath` 결과를 그대로 내니 Windows 호스트의 state.json 경로 값이 백슬래시 표기가 되고 POSIX 소비자(cross-host federation) 에서 단일 파일명으로 해석된다 — 형식 게이트 부재로 조용히 통과. 수리: 두 분기 `as_posix()` + `check_state_json_generated` case_7(단위 2분기 + 산출물 형식 대조) + 되주입 red 실증. **② 이 세션이 결함을 실증했다** (사건 기록): 인터프리터 시작 *후* 에 `os.environ['PYTHONPATH']` 를 세팅한 절차는 무효 — 그 절차로 등록한 task 4건이 **다른 체크아웃의 workflow_kit**(semcowork, v1.1.8-beta) 산출물로 나갔다 (legacy 한국어 라벨 + 백슬래시 state.json + `planned_items` 키 누락). 원복(`git checkout` + 미추적 5건 제거) 후 이 저장소 툴로 재등록. **'탐침은 잰 단위가 맞아야 한다'의 네 번째 사례** — ④번째 단위는 **해결되는 패키지의 출처** (main-019 가 그 도감을 쓴다). **③ mypy flake 관찰 7차**: 격리(`19e40ac9`) 후 smoke run 8건 중 green 5 · red 3 — red 3건 전부 **deterministic** 이고 mypy 가 아니다 (b6afe828 = schema 샘플 드리프트, 9e7b2645·ff0ac3cc = v1.5.0 bump 후 버전 스탬프 잔재 — 원격이 규명 중, `9feabcd8` 파생물 정합 2차). mypy 게이트 실패는 0 (mypy-strict workflow 도 ff0ac3cc 에서 green). 60차 관찰 6차의 '실패 run 0' 은 red run 완료 직전 산출물이었다 — **관찰은 run *완료* 기준이어야 한다.** **④ CI 현황**: v1.5.0 발행 시점 mcp-sdk-matrix 3셀 red + smoke 3연속 red, 원격 세션이 수리 진행 중 (62차 이후 상태는 `gh run list` 로 확인).
- 직전 기준선: **60차 세션 종료 — ADR-027 로드맵·마일스톤·WBS 층 한 사이클 완결 + v1.5.0 발행 (task 16건 close, 검사 268→274, push 4회, 최종 CI 워크플로 6종 green).** 소유자 지시("로드맵·마일스톤·WBS 진척 관리 + SDLC 온보딩 기본") 하나가 하루에 설계→구현→발행까지 갔다: **M-001** ADR-027 + 정본 스펙(결정 3건: 디렉터리 SSOT + 스키마 JSON 생성물 혼합 · 게이트 강제 · ADR 먼저) → **M-002** 스키마·파서·롤업(분모=선언 leaf)·roadmap_state 생성기·검사 3종·자기 적용 씨앗 → **M-003** refresh-state 통합 + session-start `roadmap_context` + 데모 milestones.py 함수까지 은퇴(MCP 는 roadmap 층) → **M-004** `evaluate_wbs_gate` 단일 판정(거부 7·허용 4코드, 예외는 exempt+사유 선언, 병행은 `parallel_allowed` 선언) → **M-005** bootstrap SDLC 씨앗(신규는 concept 부터, 기존은 draft — **draft 는 게이트를 발동시키지 않는다**) + 파생 불일치는 done 경계에서만 → **M-006** v1.5.0 발행(§1.5 로 minor — 도구 제안 2.0.0 기각, 옛 인자 rc=0 수용 추가) + 양 채널 재적용 drift 0 + 상시 운용 전환(exempt 1/15=7%). **부수 3건**: mypy flake 관찰 6차(6 run green, close 기준 33 run 복원) · memory_index 승격 2건(저점 2/10→4/10 해소) · 플러그인 단일화(overlay 위임 선언 신설, 프로젝트 overlay 5종 제거 — 게이트 첫 실전 exempt). **CI red 2건이 이 세션의 교훈이다**: 커밋 경계가 SSOT 를 갈랐고(게이트는 워킹 트리를 재지 커밋을 재지 않는다), bump 후 파생물 미갱신(§5 '60차가 남긴 규칙' 3건).
- 그 이전 기준선: **59차 세션 종료 — main-009 close: doctor pip 오탐 수리 (검사 268 유지, push 1회, 전량 2축 green).** `wk doctor` 정기 실행이 **탐침 자신의 결함**을 찾았다 — 'venv 에 pip 이 없다' finding 이 상시 오탐: 탐침이 pip 을 **자기 인터프리터**(wk 의 uv tool venv, `~/.local/share/uv/tools/standard-ai-workflow`)에서 import 하는데, uv tool venv 는 설계상 pip 없이 돌고 루트의 `uv-receipt.toml` 로 자신을 선언한다. 처방(ensurepip)은 pip 26.0.1 이 **이미 있는** 저장소 `.venv` 를 향해 헛돌았다(실측: Requirement already satisfied). **'탐침은 잰 단위가 맞아야 한다'(53차)의 세 번째 사례** — ①프로세스 vs 세션, ②glob vs `installPath` 선언에 이어 ③**자기 인터프리터 vs 개발 venv**. 수리: 판정을 순수 함수 `_pip_absence_verdict` 로 추출 — 선언이 있으면 `by_design_uv_tool` 로 finding 억제하되 payload `pip_absence` 키에 판정을 남기고(조용한 통과 금지), 선언 없는 부재는 여전히 결함이되 **잰 인터프리터를 finding 에 명시**(처방이 엉뚱한 venv 로 가지 않게). 되주입 red 실증(원복은 58차 교훈대로 `git restore --worktree` — 스테이징 보존) + **오탐을 냈던 바로 그 인터프리터**로 실환경 확증(`pip_absence=by_design_uv_tool`·finding 0). `check_deploy_doctor` 24→25 cases. **부수 확인 3건**: content drift(claude-code·codex 1.4.0)는 v1.4.0 태그 **이후** 커밋 `b119d68b` 가 session-start 스킬을 고쳐 생긴 정상적 사이클 중간 상태(다음 릴리스에서 해소, 조치 불요) · codex 낡은 호스트는 3→**2개**(pid 6191·97626, 재시작은 사용자 몫) · mypy flake 는 격리 후 **4 run 연속 green** (5번째 `4461e08e` 진행 중).
- 그 이전 기준선: **58차 세션 종료 — main-008 close: OKF 매니페스트 버전 잔재 + mypy flake 관찰 5차 (검사 268 유지, push 2회, 전량 2축 green).** **① 낡은 산문이 낡은 후보를 팔았다** — session-start 가 제시한 '다음 축: OKF v0.2 이행 ADR' 은 2026-08-20 에 ADR-026 으로 이미 끝난 일이었다(§1 '열린 후보' 줄과 §5 전량 검사 시간 절의 ①·② done 미표기가 SSOT 를 안 따라온 것 — 산문 2곳 교정). **② 그런데 그 재검토가 실제 잔재를 잡았다** (main-008): `okf-bundle.yaml` 매니페스트가 `okf_version: '0.1'` 하드코딩 — 같은 번들의 index.md(0.2)와 **두 선언이 갈렸고**, `okf_import` 감지 2순위와 `wk okf-version-check --bundle` 이 그쪽을 읽으며, ADR-026 이 도입한 '낮은 minor→pass' 소비 정책이 어긋남을 조용히 가렸다. **검사도 공범** — 기대값 `'0.1'` 리터럴이 이행 때 잔재를 green 으로 덮었다(검사가 리터럴로 든 기대값은 계약이 아니라 그 시점 상수다, 53차 규칙의 재현). 수리: 정본 상수 파생(리터럴 0) + 두 선언 자리의 **값을 추출해 3자 대조**하는 case 신설(26 cases) + 되주입 2건 red 실증 + 모듈 docstring·CLI 의 v0.1 잔재 문구 갱신. **③ mypy flake 관찰 5차** (main-004): 격리(`19e40ac9`) 이후 smoke 2 run 재발 0 — 8.8% 발생률 기준 2연속 green 은 83% 확률의 일상이라 close 유보, 이 세션 push 2회가 표본을 더한다. **④ 이 세션이 스스로 틀린 것 2건**: 되주입 원복을 `git checkout` 으로 해 미커밋 수정까지 날렸다(되주입은 수정을 커밋/스테이징한 뒤에) · 게이트를 `| tail -30` 뒤에 세워 **exit 0 이 러너가 아니라 tail 의 것**이었고 요약(failed: N)도 잘렸다 — 재실행으로 정식 판정(2축 268/268·failed 0)을 받고서야 push 했다. **절단은 결론만 자르는 게 아니라 판정 증거도 자른다** (main-004 관찰 4차의 절단 교훈이 셸 파이프라인에서 재현된 꼴).
- 그 이전 기준선은 [`baselines.md`](./baselines.md) 에 있다 (이관 74건, 최신이 위).

- 현재 주 작업 축: **로드맵·마일스톤·WBS 진척 관리 + SDLC 온보딩 기본 — 60차(2026-08-25) 소유자 지시로 확정.** ADR-027 accepted, 정본 스펙은 [`roadmap_milestone_wbs_spec.md`](../../../../workflow-source/core/roadmap_milestone_wbs_spec.md) (M-001 design 완료, 구현은 M-002~M-006 단계 실행 — 스펙 §10 이 임시 로드맵 정본). 직전 축(배포 일관성·멱등성)은 ✅ gap 4개 전부 닫혔다 (2026-08-18, 48차). 정본은 [`workflow_deployment_idempotency.md`](../../../../workflow-source/core/workflow_deployment_idempotency.md). ~~[main-016] `wk doctor`~~ ✅ · ~~[main-017] 채널 재실행 계약~~ ✅ (47차) · ~~[main-005] 드리프트 감지(페이로드 해시)~~ ✅ · ~~[main-019] 환경 pre-flight~~ ✅ (48차). 탐침은 이제 **7절**이다 (53차 `runtime_load` 신설 — 노출 미측정 한 칸을 측정으로 옮겼다). ~~[main-010] §7.0.2 의 '버전 상이' 셀~~ ✅ (53차 — 실측 + `installPath` 선언을 읽도록 교정). ~~[TASK-2026-08-14-main-009] 라벨 영어 전환~~ ✅ (53차 — 4단계 종료). ~~[main-004] wiki 3-step 하위 두 단계~~ ✅ (49차 — 1단계 은퇴 / 2단계 수리 / 3단계 재작성). **열린 후보**: ~~OKF v0.2 이행 ADR~~ ✅ (2026-08-20 ADR-026 로 전체 이행 완료, TASK-2026-08-20-main-003 — 이 줄이 그것을 안 따라와 58차가 낡은 후보를 다시 검토했다; 잔재였던 매니페스트 '0.1' 하드코딩은 58차 main-008 이 걷음) · ~~wiki L1→L2 갭 85개~~ ✅ (50차 — 계약을 4종으로 좁혀 닫음) · cross-host federation(MacBook, 시점 추후) · [TASK-2026-08-13-main-004] mypy flake 관찰.
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
- TASK-2026-08-25-main-017 MCP emit command 가 항상 python3 — PATH 에 python3 이 없는 Windows 에서 emit 설정으로 서버를 spawn 할 수 없다
## 3. 차단 작업

- 현재 `blocked` 작업:
-
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-08-25-main-021 v1.6.0 발행 — Windows 플랫폼 결함 축 (등급은 RELEASE.md §1.5, 소유자 결정 minor)
- TASK-2026-08-25-main-019 전역 도구가 다른 체크아웃의 workflow_kit 을 해결한다 — 이 저장소 대신 semcowork 사본이 실행된다
- TASK-2026-08-25-main-018 emit PYTHONPATH 가 source-checkout 모드에서만 실재 — 순수 신규 프로젝트에서 실재하지 않는 디렉터리를 가리킨다
- TASK-2026-08-25-main-020 state generator 가 Windows 호스트에서 백슬래시 경로를 쓴다 — safe_relpath 에 POSIX 정규화가 없다
- TASK-2026-08-25-main-016 roadmap M-006/WBS-6.3 — 로드맵 상시 운용 전환 + exempt 비율 관찰 시작
- TASK-2026-08-25-main-015 roadmap M-006/WBS-6.2 — 소비 채널 재적용 + doctor drift 0
- TASK-2026-08-25-main-014 roadmap M-006/WBS-6.1 — 릴리스 발행 (등급은 RELEASE.md §1.5)
- TASK-2026-08-25-main-013 roadmap M-005/WBS-5.3 — 채널 스킬 문안이 로드맵 게이트·컨텍스트를 안내한다
- TASK-2026-08-25-main-012 roadmap M-005/WBS-5.2 — 기존 프로젝트 온보딩은 draft 로드맵 초안을 받는다
- TASK-2026-08-25-main-011 roadmap M-005/WBS-5.1 — 신규 프로젝트 bootstrap 이 SDLC 로드맵 씨앗을 심는다
그 이전 완료 항목은 [3차 세션 기록](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md)·[2차 세션 기록](./sessions/adr006_retrospective_and_calibration_2026-08-10.md)과 각 task 파일에 있다.

## 5. 다음 세션 시작 포인트

### ▶ 지금 할 일 — Windows 플랫폼 결함 축 (61차 착수)

**ADR-027 로드맵 축 완결** (60차, 원격 호스트): M-001~M-006 전부 done, v1.5.0 발행,
상시 운용 전환. 진척 정본은 [`roadmap_state.json`](../roadmap/roadmap_state.json) —
다음 로드맵은 소유자가 선언한다 (session-start 가 그렇게 안내한다).

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

- `TASK-2026-08-13-main-004` — CI native 셀 mypy 게이트 flake. **관찰 4차에서 원인이
  잡혔다** (2026-08-24): 트레이스백이 `mypy/build.py:create_metastore` 를 지목했고,
  `--no-incremental` 이 캐시 **읽기**만 끄고 디렉터리는 만든다는 것이 실측으로
  확증됐다 — 병렬 호출 6곳이 같은 `.mypy_cache` 를 두고 경합했다. `main-007` 이
  전용 경로로 격리했다(저장소 오염 0, 전량 2축 green).
  **이제 기다리는 것은 '재발 여부' 다** — 멈추면 close, 재발하면 트레이스백의
  예외 이름으로 다시 좁힌다. 4차까지 온 이유는 `--show-traceback` 을 아무도 준
  적이 없어서였다(그 플래그와 결론-우선 절단을 57차가 넣었다).
  **관찰 8차** (62차, 2026-08-25, run 완료 기준): 격리(`19e40ac9`) 이후 완료
  run **13건 — green 8 · red 5, mypy 게이트 실패 누적 0.** red 5건 전부
  deterministic 이고 mypy 아님 (b6afe828 = schema 샘플 드리프트 ·
  9e7b2645·ff0ac3cc = v1.5.0 스탬프 잔재, 원격 수리 후 9feabcd8 green ·
  3866c188·95fadfc2 = 61차 종료 커밋의 생성물 정합 2종, 6ecdeaa2 치유로 해소 —
  실패 로그 실측). **close 기준 확정** (62차 소유자 결정): '33 run *연속*
  green' → **'격리 후 완료 run 33건에서 mypy 게이트 실패 0'** 으로 좁힘 —
  비-mypy deterministic red 는 카운터를 끊지 않는다 (재는 것은 격리 수리의
  유효성이지 CI 전체의 green 이 아니다). 현재 표본 **14/33** (`24b75e2a`
  green 포함, mypy 실패 0) — 통상 push 빈도면 2~3 세션 안에 닿는다.

- `TASK-2026-08-25-main-017` — MCP emit command 가 항상 python3.
  **62차에서 코드 수리 완료** (소유자 결정 = ① 플랫폼별 커맨드명): 정본
  `workflow_kit/common/python_launcher.py` + emit 분기 + doctor preflight
  bootstrap 채널 launcher 해석 + 검사 2종·되주입 red 실증. **잔여는 완료 기준
  2 하나** — Windows 호스트에서 bootstrap emit → 하네스 spawn 왕복 실측.
  다음 Windows 세션(Oh My Pi)에서 재고 close 한다.

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
  `roadmap_state.json` 의 `exempt_tasks`. 첫 실측(2026-08-25): **1/15 (7%)**
  — exempt 1건은 main-010(사용자 직접 요청). 비율이 지속 상승하면 '운영 축'
  상설 마일스톤 여부를 소유자에게 묻는다.
- memory_index 3-tuple 지표 추이 — 60차(2026-08-25) 승격 2건 반영 후
  `wk suggest-memory-entries`: 덮인 것 **4/10**, 후보 6건(threshold 0.5,
  coverage 0.17~0.33). 57~59차의 저점 고착(2/10)은 소유자 결정(승격)으로
  해소됐다. 트리거는 동일하게 유지 — **같은 수치가 3회 이어지면 소유자에게
  다시 묻는다** (다음 선택지에는 잔여 후보 추가 승격과 threshold 재캘리브레이션이
  올라간다).

### 60차가 남긴 규칙 (재발 방지)

- **게이트는 워킹 트리를 재지 커밋을 재지 않는다.** roadmap 선언(done)과 task
  링크(frontmatter)가 **다른 커밋**에 실리자, 중간 커밋의 CI 체크아웃에서만
  파생이 갈려 red 가 났다 — 로컬은 워킹 트리에 둘 다 있어 green 이었다.
  SSOT 가 여러 디렉터리에 걸치는 변경은 **한 커밋**에 싣거나, 커밋 경계마다
  정합을 확인한다.
- **버전 bump 뒤에는 전량을 다시 돈다.** bump 는 파생물 수십 개(샘플 24종
  tool_version · 스탬프 4곳 · read_only JSON 3종 · 검사 리터럴 2곳)를 낡게
  만든다. bump 이전의 green 은 bump 이후의 증거가 아니다 — 릴리스 준비
  커밋의 정답지는 직전 릴리스의 준비 커밋 diff 다.
- **파이프라인 게이트와 스모크 게이트는 다른 그물이다.** release pre_check
  6게이트가 green 이어도 스모크 274개는 안 돈 상태다. 발행 전 마지막 전량은
  release apply 가 아니라 사람이 세운다.

### 56차가 남긴 규칙 (재발 방지)

- **사본을 고치지 말고 없앤다.** bootstrap 이 템플릿 사본으로 쓰고 도구가 정본
  작성기로 쓰니 갈라졌다. 템플릿을 고쳐도 다음에 또 갈라진다 — 사본이 원인이다.
- **증상과 원인을 구분한다.** "표기가 섞였다" 는 증상이었고 원인은 레이아웃
  불일치였다. 증상만 보면 레거시 190파일을 옮기는 데 시간을 쓰고, 매일 새로
  생기는 쪽은 그대로 둔다.
- **씨앗이 자기 파서를 통과하는지 본다.** 기본 ID `TASK-001` 은 kit 자신의
  `TASK_ID_PATTERN` 과 안 맞았다. 심는 것이 읽히는지 확인하지 않으면, 소비자는
  첫날부터 파싱 안 되는 상태를 받는다.
- **일회성 작업도 소비자에게 같은 문제라면 도구로 만든다.** 스크립트로 처리하면
  우리 저장소만 나아지고, 같은 kit 을 쓰는 프로젝트는 그대로다.
- **바꾸면 안 되는 것을 잠금장치로 건다.** 라벨 통일은 정의상 집계를 바꾸면 안
  되므로, 도구가 스스로 전후를 대조하고 다르면 되돌린다 — "안 바뀔 것이다" 는
  가정이 아니라 **검증**이 된다.
- **검사가 도구의 계약을 잘못 적으면 옳은 동작이 결함으로 보고된다.** 산문 안의
  라벨 언급까지 "옛 표기가 남았다" 로 물어 스스로 red 였다.
- **판정이 복제된 곳에 새 분류를 넣지 않는다.** 쓰기 게이트가 다섯 곳이었다 —
  한 곳으로 모으고 나서야 create-only 를 안전하게 걸 수 있었다.
- **"덮었다" 도 "최신이다" 도 아닌 상태는 자기 이름을 가져야 한다.** 기존 값으로
  뭉개면 보고가 거짓이 된다 (`UPDATE_AVAILABLE`).
- **모르는 정체를 지어내지 않는다.** 프로젝트 이름을 추측해 문서를 만들면 그
  거짓이 이후 모든 산출물에 실린다 — 만들지 않고 그렇게 말한다.
- **복구는 실패했을 때가 아니라 매번 점검한다.** 실패 경로에만 달면, 실패하지
  않는 종류의 부재는 영원히 안 잡힌다.
- **fixture 는 남의 컨텍스트를 물려받는다.** 브랜치 오버라이드가 상속돼 재려던
  것과 무관하게 red 가 났다 — 필요 없는 컨텍스트는 fixture 에서 끊는다.
- **임시 디렉터리 판정은 블록 안에서 굳힌다.** `with` 를 벗어난 뒤의
  `.exists()` 는 무조건 False 다.
- **매일 바뀌는 값은 비교에서 뺀다.** 템플릿의 `최종 수정일` 을 리터럴로 물면
  그 검사는 내일 red 다 — 계약이 아니라 그 시점 상수를 지키는 것이다.

- **신호는 읽는 쪽 가정만큼을 뜻하지 않는다.** "이벤트가 1건 쌓였다" 는 "내
  주입 완결본이 관측됐다" 가 아니다. 이번 주에 세 번째로 같은 모양이다
  (`in_sync ≠ 쓸 수 있음` · `인벤토리 ≠ 세션 가용성` · `이벤트 1건 ≠ 완결본`).
- **테스트의 쓰기도 관측 대상이다.** `Path.write_text` 는 truncate 후 write 라
  비원자적이고, 그 중간 상태는 **디스크에 실재한다**. 파일을 보는 도구를
  시험할 때는 테스트 자신의 쓰기 방식이 곧 입력이다.
- **flake 를 고치는 검사가 스스로 flaky 하면 안 된다.** 새 case 의 첫 판이
  5회 중 4회 red 였다 — 좁은 창을 **운으로** 잡길 기대했기 때문이다. 재려는
  조건을 **보장된 시간 동안 실재**하게 만들고 재라.
- **우연히 성립하던 동작은 계약으로 못박는다.** 안 그러면 다음 사람이 그것을
  잡음으로 보고 도구 쪽을 뭉갠다 — 그러면 도구의 존재 이유가 사라진다.

### 55차가 남긴 규칙 (재발 방지)

- **산문이 SSOT 를 복제하면 반드시 갈라진다.** §5 후보 넷 중 둘은 이미 기계가
  읽는 자리(state.json · `wk doctor`)를 갖고 있었다. 그 자리를 **가리키고**
  내용을 옮겨 적지 않는다.
- **판정 기준이 다른 것을 한 목록에 담지 않는다.** 부류가 섞이면 어느 기준도
  못 쓴다 — 그래서 아무것도 낡음을 말해 주지 못했다.
- **결정 대기를 task 로 채번하지 않는다.** 결정은 사람이 내리므로 영원히
  `planned` 로 남아, 진짜 작업 후보 목록을 오염시킨다.
- **재지 못하는 부류는 검사가 보지 않는다고 적는다.** 세 부류는 기계가 낡음을
  판정할 수 없다 — 재는 척하면 거짓 안심을 준다.
- **문서에 쓰는 링크는 파서의 입력이다.** `parse_handoff` 는 파일 **전체**의
  markdown 링크를 `next_documents` 로 긁어간다. 편의로 링크를 다는 순간 다른
  산출물이 조용히 부푼다.

### 54차가 남긴 규칙 (재발 방지)

- **갱신이 상태를 나쁘게 만드는 조언은 틀린 조언이다.** 탐침이 `CLAUDE.md` 를
  "재적용 대상" 이라 말했는데, 그 조언을 따르면 측정으로 얻은 90여 줄이 `TODO`
  placeholder 가 된다. `installPath` 때(53차)와 **같은 모양**이 소비자 쪽에서
  다시 성립했다.
- **정본 안의 모순은 사고가 아니라 빠진 분류다.** §3(kit 소유, 덮는다)과
  §4-2(additive)가 같은 파일에 붙어 있었다. 둘 중 하나가 틀린 게 아니라
  **넷째 자리가 없었다** — '프로젝트가 가져간 kit 소유 파일'.
- **추측하지 말고 선언하게 한다.** "내용이 많으니 포크겠지" 는 휴리스틱이고
  휴리스틱은 조용히 틀린다. 파일이 스스로 말하게 했다.
- **표식을 덮어쓰면 병합 경로가 사라진다.** 포크 선언은 버전 marker 를 **건드리지
  않는다** — 갈라져 나온 버전이 곧 diff 대상이고, 그것이 놓친 kit 변경을 되찾는
  유일한 길이다.
- **`force` 가 이기는지 지는지가 분류를 가른다.** 불가침(사용자 상태)은 force 로도
  안 덮고, 포크는 덮는다. 포크는 *"덮지 마라"* 가 아니라 *"모르고 덮지 마라"* 다.
- **손으로 유지하는 버킷은 새 분류를 조용히 삼킨다.** 매니페스트 요약의 if/elif
  사슬이 `forked` 를 어디에도 안 담아, 조작자는 "아무 일도 없었다" 로 읽었을
  것이다. 열거형에서 파생하게 바꿨다.
- **그물이 두 자리만 보면 세 번째 자리에서 갈린다.** main-008 의 파리티 검사는
  생성기와 산출물을 대조했지만 **레지스트리 선언**은 안 봤다 — 그래서
  `session-end` 가 탐침에 아예 안 보였다. 같은 사실을 말하는 자리를 **전부**
  세어서 대조한다.
- **리터럴 기대값은 재적용하는 순간 터진다.** `check_self_application` 이
  `## 프로젝트 실행 기본값` 을 리터럴로 들고 있었고, 생성기는 이미 영어 제목을
  낸다. 재적용을 안 해서 green 이었을 뿐이다 — **잠복 red 는 green 이 아니다.**
- **채널마다 잔재 정책이 다르다.** claude-code 는 옛 버전 디렉터리를 남기고
  codex 는 지운다. 그래서 탐침은 glob 이 아니라 **선언**을 읽어야 한다.
- **산문은 그물에 안 걸린다.** 같은 어긋남이 네 자리에서 났는데(플러그인 ·
  생성기 · 산출물 · 레지스트리) 마지막 자리는 **손으로 쓴 목록**이었다. 목록을
  산문에서 빼내 파생으로 만들어야 검사가 볼 수 있다.
- **생성기 출력을 재고 저장소 사본을 재지 않는다.** 이 저장소의 `CLAUDE.md` 는
  포크본이라, 그것을 재면 소비 프로젝트가 받는 문서의 결함을 못 본다.
- **어휘 밖을 지키면서 어휘 안을 흘리지 않는다.** `unknown_status_items` 는
  어휘 밖 값을 끝까지 지켰는데, 정작 어휘 *안*의 `planned` 가 네 분기 어디에도
  안 담겨 사라졌다. 실측 비용은 6일이다.
- **없음을 확인하는 검사는 사라짐을 못 잡는다.** `test_planned_task_is_not_reported_done`
  은 planned 가 *아닌 것* 둘만 확인하고 **어디에 있는지는 묻지 않았다** — 그래서
  통과했다. 어휘는 **전수**로 돌려 "모두 어딘가에 담긴다" 를 주장한다.
- **포크는 병합 이력을 남긴다.** 어느 버전까지 봤고 무엇을 기각했는지 적지 않으면,
  다음 사람은 전수 열거를 처음부터 다시 한다.
- **돌지 않은 워크플로는 통과한 워크플로가 아니다.** `okf-validate` 는 경로
  필터가 걸려 있어 최근 푸시에서 트리거되지 않았고, 그동안 다른 job 들의 green
  만 보였다. 푸시 뒤 CI 를 볼 때는 **이번에 돈 것**이 아니라 **main 의 워크플로
  전체 상태**를 본다.
- **그물은 파일 형식 경계에서도 갈린다.** 같은 이행이 `.py` 의 버전 리터럴은
  정본 참조로 바꾸고 `.yml` 은 손대지 않았다. 표기를 바꿀 때 전수 조사할
  대상에 **YAML·셸·문서**를 넣는다.
- **'없음' 과 '어긋남' 을 같은 말로 부르지 않는다.** 옛 메시지는 값이 달랐을
  뿐인데 "필드가 없다" 고 보고했다 — 진단이 원인을 가리키지 못하면 red 를
  읽는 시간이 그만큼 늘어난다.
- **자주 안 도는 워크플로일수록 정적으로 잡는다.** 주간 cron 은 3일에 한 번도
  신호를 안 준다. 실행에 기대지 말고 참조 무결성(경로 실재 · 버전 파생)을
  검사로 세운다.
- **파일을 옮길 때 따라오지 않는 것은 코드만이 아니다.** `.yml` · 문서 ·
  주석의 경로 참조가 남는다. 이동 커밋의 전수 조사 대상에 넣는다.

### 53차가 남긴 규칙 (재발 방지)

- **세션은 프로세스의 대리값이 아니다.** `/clear` 는 대화만 새로 열고 프로세스는
  그대로다. 로드 단위가 프로세스인 것을 세션 시각으로 재면 옳은 가설이 기각된다.
  값싼 방증: 실행 중 프로세스의 버전과 `<cli> --version`(새 프로세스)이 어긋나면
  그 프로세스는 이미 디스크보다 낡았다.
- **갱신이 보고를 나쁘게 만들면 그 탐침은 틀렸다.** `plugin update` 성공 직후 발견이
  6→8건으로 늘었다. 옛 버전 디렉터리가 남는데 선언(`installPath`)을 안 읽고 glob
  매치를 전부 동등한 설치로 셌기 때문이다.
- **하네스가 이미 말하고 있는 것을 추측하지 않는다.** 어느 사본이 설치본인지는
  선언 파일에 있었다. 안 읽고 있었을 뿐이다.
- **버전 문자열은 태그가 아니라 브랜치 팁일 수 있다.** 마켓플레이스는 기본 브랜치를
  당긴다 — 같은 `1.3.0` 이 시점마다 다른 내용을 가리킨다. gap 3 의 교훈이 소비자
  쪽에서 다시 성립한다.
- **로케일로 번역되는 필드를 파싱하지 않는다.** `ps` 의 `lstart` 는 호스트마다
  다른 글자를 낸다. 형식이 고정된 `etime` 을 읽고 지금에서 뺀다.
- **도달 불가능한 분기는 제거한다.** 되주입해도 red 가 안 나는 방어 코드는 검사되지
  않은 코드다 (비교 쪽 `resolve()` 를 그렇게 지웠다).
- **검사가 리터럴로 든 기대값은 계약이 아니라 그 시점 상수다.** 라벨 전환에서 검사
  3종·18곳이 red 였고 동작은 내내 옳았다. 기대값은 정본에서 파생한다.
- **그물의 모양이 곧 주장의 범위다.** `- 라벨:` 콜론 모양만 보는 검사는 **라벨 이름만
  든 리터럴**을 못 본다 — 그 자리가 두 검사를 통과하고 살아남았다.
- **표기를 바꾸면 '읽는 쪽 리터럴'을 전수 조사한다.** `^- 상태:` 하나가 frontmatter
  우선순위를 뒤집었다. 산출물이 아니라 **파서**가 조용히 갈린다.
- **총계도 세어서 낸다.** `"10/10"` 리터럴이라 case 를 늘려도 숫자가 안 따라왔다 —
  그 숫자가 곧 "몇 개를 쟀나" 의 유일한 증거다.
- **전량 게이트는 필터로 대체되지 않는다.** 이 세션의 red 2건(배포 사본 드리프트 ·
  layout 리터럴)은 관련 검사 필터를 다 통과하고 **게이트에서만** 잡혔다.

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
- ~~① [TASK-2026-08-13-main-009] 무거운 8개~~ ✅ done
- ~~② [TASK-2026-08-14-main-003] `--changed` 선택 실행~~ ✅ done
- ~~③ [TASK-2026-08-14-main-004] 2축→1축 조건부~~ ⛔ **검토 후 기각** (재론 방지,
  CLAUDE.md 게이트 절에 명문) — 절감은 가장 크지만 15연속 CI red 를 만든 그
  비대칭이다. 안 하는 것도 결론이고, 이로써 **이 절의 실행형 잔여는 0** 이다.

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
