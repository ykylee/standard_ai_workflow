# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-11-21 (138차 세션 **종료** — Linux 호스트. 2.0 허브 M-037 · M-038 · M-040 done, M-039 진행(남은 것: macOS · Windows · 대화형 실측 · 이 저장소 표식 전환 · arcturus). 이 저장소 테스트베드 실제 등록 · `/setup.md` 4 하네스 실측 · 운영 가이드 · **v2.0.0 (베타 표기) · v1.30.0 발행**, latest = v2.0.0)
- 이전 수정일: 2026-11-19 (134차 세션 — macOS 호스트 Mac mini(두 번째 맥). 1.22.0 → 1.27.0 전 채널 재적용 · main-001 session-start 아카이브 거짓 보고 수리 · main-002 재사용 브랜치 재합류 병합 · main-003 memory_index 대조군 수리. 발행 없음)
- 이전 수정일: 2026-11-16 (132차 세션 진행 — Linux 호스트. 워크벤치 main-001 개방 모드 · main-002 자동 기동 · main-003 화면 개편 close, v1.25.0 발행)
- 이전 수정일: 2026-10-31 (121차 세션 **종료** — Windows 호스트 DESKTOP-DGPLBF7. main-003 **한글 Windows 프로필 확립**(자식 환경 정본 `platform_child_env` · cp949 인코딩 · LF 표준 · 교차 플랫폼 파일 락 · POSIX 경로 · mypy `platform=linux`) → **격차 52건 → 0건**, 커밋 전 `--changed` 게이트 289/289 pass. 판정 불변(skip/xfail 0 · 단언 삭제 0 · 기대값 하향 0). 전량 게이트 `--branch-context=all` 은 커밋 후 clean tree 에서 rc 0 과 증거 기록을 남긴 뒤 push)
- 이전 수정일: 2026-10-31 (120차 세션 **종료** — Windows 호스트 DESKTOP-DGPLBF7. main-001 MiniMax Code 채널 재적용(v1.21.0 플러그인 sync 13파일 + 글로벌 MCP 등록 · doctor in-sync) + main-002 게이트 러너 Windows 결함 수리(`_kill_process_group` POSIX 전용 API → `taskkill` 분기). main 은 v1.21.0 + 커밋 4건, 미push)
- 이전 수정일: 2026-10-22 (119차 세션 **종료** — Linux 호스트. 변경 없음: v1.21.0 발행 뒤 기준선 재측정 — doctor behind=[] · claude-code 재시작 확인 · 전량 게이트 309×2 green. 열린 task 는 Windows 실측 3건뿐, 이 호스트 착수 가능 작업 0)
- 이전 수정일: 2026-10-19 (118차 세션 **종료** — Linux 호스트. main-001 진입점 다이어트 harvest 재실행(v1.20.0 채취 + case 6 · 7) · main-002 check_memory_lint T1b branch-scoped 수리 · main-003 T1a 은퇴 + T1c · T1d branch-scoped 재작성 · main-004 goal coverage '선언 없는 goal' provenance 수리 + minimax 세션 합류(main-001 doctor 5채널 · main-003 origin 없는 auto-seed) → **v1.21.0 발행** (main-005) · 소유자 결정 3건 반영(main-006 G4 · G5 선언 · main-007 main · 태그 삭제 push 차단 · 매트릭스 요구 안 함))
- 이전 수정일: 2026-10-06 (117차 세션 **종료** — Linux 호스트. main-003 verifier 실제 로드 실측 close · main-008 RELEASE.md §2.8 minimax-code 절차 · main-009 minimax_plugin --apply 보고 오독 수리. 발행 없음)
- 이전 수정일: 2026-10-06 (116차 세션 **종료** — Linux 호스트. 플레이북 검토 · A1~A3 · 진입점 다이어트 3단계 · **v1.20.0 발행** · main-006 handoff 제목 동기화 수리 · **v1.20.1 발행**)
- 이전 수정일: 2026-10-02 (114차 세션 **종료** — Linux 호스트. main-006 · 007 구현(Windows cp949 · wk.exe 백신 차단 → python -m workflow_kit) + main-008 **v1.19.0 발행**, 006 · 007 은 Windows 실측 대기)
- 이전 수정일: 2026-10-02 (113차 세션 **종료** — Linux 호스트. main-004 close: worktree 합류 반영 — 병합된 브랜치 메모리를 모 브랜치 메모리에 기록하고 아카이브 → **v1.18.0 발행** (main-005))
- 이전 수정일: 2026-10-02 (112차 세션 **종료** — Linux 호스트. 원격 11커밋(110·111차 worktree 세션 · macOS main-014) 동기화 + main-001 close: worktree seed 가 모 브랜치 내용을 이어받는다(원류 기록 · 합류 시 되돌려 적기) → **v1.17.0 발행** (main-002) · 후속 main-003 등록)
- 이전 수정일: 2026-09-30 (109차 세션 **종료** — Linux 호스트. main-009 · 010 · 011 close: Codex 인증 압축 왕복 실측 → 세 hook `failed`(`[` 머리말 JSON 오판) · 재주입 0 → `--output-format codex-json` 수리 · 재실측 도달 → **v1.16.0 발행**)
- 이전 수정일: 2026-09-30 (108차 세션 **종료** — Linux 호스트. main-008 close: Codex 플러그인에 compact 중계 hook 3종 탑재(`adapters/codex/hooks.json`, 사용자 신뢰 필요) + 요약 원문 부재 시 '대조 불가'. 인증 압축 왕복은 main-009 로 이관)
- 이전 수정일: 2026-09-30 (107차 세션 **종료** — Linux 호스트. 새 기능 축 compact 중계 M-018~M-021 concept→implementation 완주: `wk compact-checkpoint` + 플러그인 스킬 `compact-relay` · hook 3종, ADR-030 → **v1.15.0 발행**)
- 이전 수정일: 2026-09-30 (106차 세션 **종료** — Linux 호스트. main-002 close: `python_floor` 하한 해석기 호출을 stdin 으로(배치 shim `-c` 개행 절단, main-013 후속) + main-001 minimax 패키지 형식 조사(공식 mcode 명세 vs 105차 기록 불일치 → macOS 채취 대기))
- 이전 수정일: 2026-09-30 (105차 세션 **종료** — macOS 호스트. minimax-code 플러그인 채널 갭 실측·등록 + MiniMax Plugin V1 배포 + `~/.mavis` 호환 링크 제거. 저장소 코드 변경은 없음)
- 이전 수정일: 2026-09-29 (104차 세션 **종료** — macOS 호스트. main-017 · 018 close + 08-25-main-017 Windows 실측 칸 신설: Windows 커밋이 `roadmap_state.json` source_path 를 역슬래시로 남겨 교차 호스트 diff 가 나던 것 → `as_posix()`, 후속으로 `wk doctor` 가 Windows 에서 정본 파일을 extra 로 오판하던 것)
- 이전 수정일: 2026-09-29 (103차 세션 **종료** — Windows 호스트. main-016 close: `wk` editable 재설치 확인 · 사용자 PATH 와 Codex 프로세스 PATH 비교. 사용자 PATH 에 venv Scripts 가 있으나 현재 데스크톱 프로세스에는 반영되지 않아 완전 재시작 필요)
- 이전 수정일: 2026-09-29 (100차 세션 **종료** — Linux 호스트. main-010 close: 살아있음 판정이 wiki frontmatter status · 굵은 '상태' 헤더를 못 읽던 것)
- 이전 수정일: 2026-09-29 (98차 세션 **종료** — Linux 호스트. task 5건 close(main-001~005) + **v1.14.1 · v1.14.2 발행** + GitHub #29 close)
- 이전 수정일: 2026-09-28 (96차 세션 **종료** — macOS 호스트. task 2건 close: 발행 완료된 채 열려 있던 main-016(v1.13.0) 정리 + `wk doctor` **plugin_enabled** 를 4채널로(main-018))
- 이전 수정일: 2026-09-28 (95차 세션 **종료** — macOS 호스트. 플러그인이 갱신 뒤 `disabled` 로 남아 스킬이 조용히 사라진 것을 잡는 `wk doctor` **plugin_enabled** 절 신설(9절째), TASK-2026-09-28-main-017 close)
- 이전 수정일: 2026-09-28 (94차 세션 **종료** — macOS 호스트 원격 동기화 + v1.13.0 채널 재적용(§2.8): 4채널 + MCP 해석기 1.11.0 → 1.13.0, doctor `behind=[]`. 원격에 이미 다른 구현으로 닫힌 main-015·016 의 로컬 유령 커밋 2건 폐기)
- 이전 수정일: 2026-09-28 (92차 세션 **종료** — task 10건 close: 게이트 처리량 · 결함 수리 · 세션 시작 컨텍스트 예산 concept→구현 완주, 필독 195→111KB)
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

- 현재 기준선: **138차 말 (2026-11-21, Linux 호스트) — v2.0.0 (2.0 허브, 베타 표기) · v1.30.0 (1.x 안내 판) 발행.** GitHub latest = v2.0.0. main 은 kit 플러그인 채널을 내지 않는다 (`KIT_PLUGIN_CHANNEL`, R16.6) — 이 호스트 Claude Code 채널은 `../standard_ai_workflow-1x` (Folder) 로 옮김. 판 번호는 정수 (2.0.0b1 은 키트 16곳이 깨져 소유자가 정수로 정함). 운영 가이드 `docs/HUB_OPERATIONS.md`, 두 줄 발행 정책 RELEASE.md §1.1. 게이트: main 346×2 (20c61a09) · 1.x 336×2 (24ca6ae3).
- 직전 기준선: **138차 (2026-11-21, Linux 호스트) — 2.0 허브 화면 · 1.x 전환 · 허브 간 이전 · 테스트베드 · 셋업 가이드.** M-037 done (화면 `/ui/` · 콜사인 표 · 지침 제안), M-038 WBS-38.1~38.3 (전환 계획 · 들여오기 · 표식 · 1.x 거절; 남은 몫 = 2.0.0 발행 때 1.x 안내판, main-011), M-039: 39.1 Linux 4하네스 · `/setup.md` + `hub_client.py bootstrap` (빈 폴더에서 Claude Code 완주), 39.2 리허설 · 테스트베드(`~/workflow-hub-testbed/start.sh`, :8770) · 이 저장소 실제 등록(P-20261121-fcfdccb1, 표식 보류), 39.4 허브 간 이전(CLI · HTTP 초대 코드). 마지막 push `53076aac` 뒤 세션 정리 커밋.
- 그 이전 기준선: **137차 (2026-11-21, Linux 호스트) — R16.5 1.x 분기 + 2.0 허브 main 병합 + M-036 done** (위키 · memory_index · 운반 · 선택 클라이언트 — TASK-2026-11-21-main-001~004, `check_hub_wiki` 12 · `check_hub_client` 5, 마지막 push `25e8574a`). 1.x 수리 `bidir_link` 는 `release/1.x` 에도(`05678400`), 1.x OKF 결함 2건은 `release/1.x` backlog. `release/1.x` 를 `main@bb943c81`(v1.29.0 + 메모리 커밋)에서 분기 · push — 1.x 결함 수리 · patch 발행은 그 브랜치 머리에서 (R16.1 · R16.2). 이어 `claude/workflow-hub-concept` 를 main 에 병합(`dd011029`, PR 없음 — 소유자 지시): 2.0 허브 M-030~M-035 done (요구 `docs/planning/workflow-hub-requirements-2026-11.md` · 설계 `workflow-source/core/hub_spec.md` · ADR-033 Accepted · PURPOSE 2.0판 · 코드 `workflow_kit/hub/`), kit 결함 수리 2(현재 마일스톤 병행 선언 기준 · handoff §5 서두 회차 줄 누적형). 브랜치 기록은 [`archived/claude/workflow-hub-concept/`](../../archived/claude/workflow-hub-concept/session_handoff.md). plugin/ 은 안 바뀌어 main 채널 소비자는 1.x 플러그인 그대로 — 2.0 이 plugin/ 을 바꾸기 전에 R16.4 안내 판 필요. **검증 간소화 기간 (소유자 2026-11-20)**: verifier · push 전 전량 게이트 생략, `--changed` + 스모크 뒤 `--no-verify` push, 발행 때만 전량. 다음 M-036.
- 그 이전 기준선: **134차 세션 (2026-11-19, macOS 호스트 Mac mini — 종전 맥과 다른 두 번째 맥) — 발행 없음, 정본 v1.27.0 + 미발행 수리 3건.** 이 호스트를 1.22.0 → 1.27.0 으로 올림(전역 `wk` uv tool · `.venv` editable · claude-code · codex · grok-build · minimax-code; antigravity 는 `agy` 부재) → doctor behind=[] · disabled=[]. `core.hooksPath=.githooks` 켬. 133차(worktree `claude/remote-sync-check-234c32`, v1.27.0 발행)의 기록이 재합류 결함으로 main 메모리에 못 들어와 있던 것을 수리와 함께 반영(완료 3 · 이월 2). 수리: main-001(session-start 가 아카이브 실패를 '이동했다' 로 보고) · main-002(`archived/<branch>/` 가 있으면 반영까지 건너뜀 → 파일 단위 병합, `superseded-<옛 날짜>.<이름>`) · main-003(`check_memory_index_cross_v0_15_7` case 5 대조군이 telemetry 누적량에 의존). 셋 다 verifier PASS. `run_all_checks --changed` green · smoke 8/8. **전량 게이트(`--branch-context=all`) 이 호스트 첫 실행 통과 — `7df480f9` 664 PASS · 실패 0, push 완료(`fc814642..7df480f9`).**
- 그 이전 기준선은 [`baselines.md`](./baselines.md) 에 있다 (이관 140건, 최신이 위).

- 현재 주 작업 축: **2.0 허브 (M-031~M-040, 2026-11-20 소유자) — M-031~M-037 done, M-038 · M-039 진행 — 남은 것: 실제 전환(상시 허브 위치 결정) · 39.1 다른 호스트/하네스 · M-040 2.0.0 발행.** 1.x 는 `release/1.x` 에서 결함 수리만. 이전 축: **로드맵·마일스톤·WBS 진척 관리 + SDLC 온보딩 기본 — 60차(2026-08-25) 소유자 지시로 확정.** ADR-027 accepted, 정본 스펙은 [`roadmap_milestone_wbs_spec.md`](../../../../workflow-source/core/roadmap_milestone_wbs_spec.md) (M-001 design 완료, 구현은 M-002~M-006 단계 실행 — 스펙 §10 이 임시 로드맵 정본). 직전 축(배포 일관성·멱등성)은 ✅ gap 4개 전부 닫혔다 (2026-08-18, 48차). 정본은 [`workflow_deployment_idempotency.md`](../../../../workflow-source/core/workflow_deployment_idempotency.md). ~~[main-016] `wk doctor`~~ ✅ · ~~[main-017] 채널 재실행 계약~~ ✅ (47차) · ~~[main-005] 드리프트 감지(페이로드 해시)~~ ✅ · ~~[main-019] 환경 pre-flight~~ ✅ (48차). 탐침은 이제 **7절**이다 (53차 `runtime_load` 신설 — 노출 미측정 한 칸을 측정으로 옮겼다). ~~[main-010] §7.0.2 의 '버전 상이' 셀~~ ✅ (53차 — 실측 + `installPath` 선언을 읽도록 교정). ~~[TASK-2026-08-14-main-009] 라벨 영어 전환~~ ✅ (53차 — 4단계 종료). ~~[main-004] wiki 3-step 하위 두 단계~~ ✅ (49차 — 1단계 은퇴 / 2단계 수리 / 3단계 재작성). **열린 후보**: ~~OKF v0.2 이행 ADR~~ ✅ (2026-08-20 ADR-026 로 전체 이행 완료, TASK-2026-08-20-main-003 — 이 줄이 그것을 안 따라와 58차가 낡은 후보를 다시 검토했다; 잔재였던 매니페스트 '0.1' 하드코딩은 58차 main-008 이 걷음) · ~~wiki L1→L2 갭 85개~~ ✅ (50차 — 계약을 4종으로 좁혀 닫음) · cross-host federation(MacBook, 시점 추후) · ~~[TASK-2026-08-13-main-004] mypy flake 관찰~~ ✅ (66차 close — 33/33 표본, mypy 실패 0).
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
- TASK-2026-11-17-claude-remote-sync-check-234c32-004 iPad Chrome(CriOS 156 · iPadOS 27)에서 워크벤치 폼 제출이 서버에 닿지 않는다 — 응답 보내기 · todo 추가 전부
- TASK-2026-11-17-claude-remote-sync-check-234c32-002 워크벤치 응답 · todo 변경이 Claude Code 컨텍스트에 실제로 주입되는지 실측 (main-014 미측정분)
- TASK-2026-10-02-main-007 Windows V3 백신이 wk.exe 를 평판 기반으로 차단한다 — pip 생성 console-script 런처 대체 진입 경로
- TASK-2026-10-02-main-006 Windows 로캘(cp949)에서 wk 가 UnicodeEncodeError 로 죽는다 — stdout 과 기본 인코딩 I/O 를 UTF-8 로 고정
- TASK-2026-08-25-main-017 MCP emit command 가 항상 python3 — PATH 에 python3 이 없는 Windows 에서 emit 설정으로 서버를 spawn 할 수 없다
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-11-22-main-015 VS Code 확장 껍데기 — 중계 화면 webview · 상태 표시줄 · 프레임 정책 · 게이트 검사 (M-047 WBS-47.1)
- TASK-2026-11-22-main-013 PC 중계 실제 어댑터 실측 — Claude Code · Codex 세션 띄우기 · 배정 전달 · 수락/보고 · 멈춤 (M-046 WBS-46.3)
- TASK-2026-11-22-main-011 PC 중계 — 허브 쪽 API · 중계 패키지 · 어댑터 · 게이트 검사 (M-046 WBS-46.1 · 46.2)
- TASK-2026-11-22-main-010 허브 오케스트레이션 구현 2 — 오케스트레이터 lease · 배정 상태 기계 · 보고 · 정지 · 진입 규칙 (M-045 WBS-45.1)
- TASK-2026-11-22-main-009 허브 오케스트레이션 구현 1 — DB 판 11 · 세션 · 받은편지함 편승 · 대기 도구 · 수신 확인 (M-044 WBS-44.1)
- TASK-2026-11-22-main-008 ADR-034 Accepted — design 결정 DO1~DO13 확정 (M-043 WBS-43.3)
- TASK-2026-11-22-main-007 허브 오케스트레이션 스펙 — DB 판 11 · 도구 표 · 세션 식별 · 전달 흐름 · 대기 도구 HTTP 실측 (M-043 WBS-43.1 · 43.2)
- TASK-2026-11-22-main-006 허브 오케스트레이션 ADR-034 초안 (M-042 WBS-42.3)
- TASK-2026-11-22-main-005 허브 오케스트레이션 요구 R · 추적표 (M-042 WBS-42.2)
- TASK-2026-11-22-main-004 허브 오케스트레이션 실측 S 2차 — hook · 신뢰 없는 간접 전달 수단 (도구 응답 편승 · 대기 도구 · 진입 지침) (M-042 WBS-42.1)
그 이전 완료 항목은 [3차 세션 기록](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md)·[2차 세션 기록](./sessions/adr006_retrospective_and_calibration_2026-08-10.md)과 각 task 파일에 있다.

## 5. 다음 세션 시작 포인트

- (139차, 2026-11-22, Linux) 결함 수리 2 (main-027 `find_dist_files` 정확 대조 · 234c32-002 seed 가 `roadmap_state.json` 재생성, 1.x 이식 release-1.x-008 · 009). **새 축 허브 오케스트레이션**: M-041 concept done (O1~O10 권고안) · M-042 requirements done — 실측 S 1차 · 2차(hook · 신뢰 없는 간접 수단: 도구 응답 편승 · 대기 도구 · 받은편지함 파일, 진입 지침 있을 때만 동작) · 요구 R17~R24 · Q1~Q4 권고안 · **ADR-034 Proposed**. 정본 `docs/planning/hub-orchestration-{review,requirements}-2026-11.md`. M-043 design done (`workflow-source/core/hub_orchestration_spec.md`, DO1~DO13 권고안 · ADR-034 Accepted). **M-044 구현 1 done** (TASK-2026-11-22-main-009 — DB 판 11 · `hub/orchestration.py` · 공통 `session` 인자 · 편승 · 대기 async · 수신 확인, `check_hub_orch` 10/10 · 되주입 12/12). **M-045 구현 2 done** (TASK-2026-11-22-main-010 — lease · 배정 상태 기계 · 수락=맡기 한 트랜잭션 · 보고 · 정지 · 2.1 진입 규칙 절, `check_hub_orch_assign` 9/9 · 되주입 16/16). **M-046 WBS-46.2 done** (TASK-2026-11-22-main-011 — 허브 중계 API · `workflow_kit/relay/` · `hub relay` 명령 · 어댑터 claude-code/codex/fake, `check_hub_relay` 9/9 · 되주입 13/13). **M-046 done** — main-013 실제 어댑터 실측(요구 §1.5: Claude · Codex 띄우기 → 자기 등록 → 배정 전달 → 수락 → 보고 → 멈춤 전부 동작) · 로컬 화면. **M-047 done** (main-015 — `editors/vscode/` 껍데기, `check_vscode_shell` 6/6, 실제 VS Code 로드 미측정). **다음: M-048 안정화 · 2.1.0 발행** (전량 게이트 · main-012 · main-014 결정 · VS Code 실측 · .vsix). 후속 planned: main-012 (로드맵 형식 위반이 session-start 를 죽임) · main-014 (Codex workspace-write 에서 .git 읽기 전용 — 소유자 결정).
- (138차, 2026-11-21) **M-037 in_progress — WBS-37.1 done** (TASK-2026-11-21-main-005: 허브 화면 `/ui/` · `/api`, 공용 web 토큰 `serve --web-token-name`(기본 꺼짐), hub_spec §4.7). 소유자 결정: **결정 답은 승인된 human 만 · responder = 그 콜사인** — MCP `hub_plan_respond` 도 같은 규칙, 승인은 새 도구 `hub_callsign_approve`(소유자). 실브라우저 실측 도구: 시스템에 playwright 가 없어 scratchpad 에 `playwright-core@1.56.1` + `~/.cache/ms-playwright/chromium-1223` 로 돌렸다. 이어 **WBS-37.2 done** (TASK-2026-11-21-main-006: 콜사인 표 · handoff 화면 · 화면 승인, 받은 판 기록 수리 — `guide_version_seen` 은 세션 시작 2단계에서도 · `client_version_seen` 은 `X-Hub-Client` 머리로). 이어 **WBS-37.3 done → M-037 done** (TASK-2026-11-21-main-007: DB 판 7 `guide_proposal` · 도구 `hub_guide_get` · `propose` · `decide` — 사람만 판을 올리고 에이전트는 제안, 낡은 기준 409 · 렌더 예산 422 · 화면 지침 · 위키 읽기). 이어 **M-038 in_progress — WBS-38.1 done** (TASK-2026-11-21-main-008: DB 판 8 `migration_1x` · `hub_migrate_plan` · `import` · `report`, 이 저장소 task 603개 전수 파싱 미분류 0). 이어 **WBS-38.2 done** (TASK-2026-11-21-main-009: `hub_migrate_marker` — 표식 쓰기 지시 · sha 확인 · 되돌리기). 이어 **WBS-38.3 일부 done** (TASK-2026-11-21-main-010 · release/1.x 의 `release-1.x-005`: 표식이 있으면 1.x 쓰기 거절 · session-start 는 허브를 가리킴, 양쪽 push). 남은 몫 = 1.x 안내 판 발행 — 소유자 결정: **2.0.0 발행 때 함께** (planned task 로 등록). 이어 **M-039 in_progress — WBS-39.1 Linux 실측 done** (TASK-2026-11-21-main-012: 4 하네스 모두 허브 MCP 로 부트스트랩 · 세션 시작 완주, 결함 2 수리 — Codex 승인 안내 · repo_results 목록 꼴; 기록 requirements §16.4). 남은 39.1 = macOS · Windows · 대화형 (planned). 이어 **WBS-39.2 리허설 done** (TASK-2026-11-21-main-014: 로컬 임시 허브로 이 저장소 들여오기 · 대조, 표식 없음 — 로드맵 진척 차이 0; 결함 수리 2 · 소유자 결정 2 — requirements §16.5). 이어 **main-015 (클라이언트 운반) · main-016 (범위 확장) done** — 리허설 재실행: task 646 · 보관 281 · 문서 2 실패 0, 결정 상태 · 목적 · 프로젝트 칸 1.x 와 같음 (requirements §16.5). 이어 **WBS-39.4 허브 간 프로젝트 이전 CLI done** (TASK-2026-11-21-main-017 — 묶음 · export/import · 봉인 410, 토큰 이어받음, hub_spec §3.5). 이어 **HTTP 경로 done** (TASK-2026-11-21-main-018 — 대상 허브 일회용 초대 코드 · hub_client.py move). 이어 release/1.x 러너 잠금 수리(`release-1.x-006`) · **테스트베드 실사용 done** (TASK-2026-11-21-main-020: 허브 loopback :8770 — `~/workflow-hub-testbed/start.sh` 로 다시 띄움, clone `../standard_ai_workflow-hub` 를 전환해 Claude Code 실작업 완주, 수리 7, requirements §16.6). 이어 **이 저장소 실제 등록 done** (TASK-2026-11-21-main-021: 테스트베드 DB 보관 · 새 DB 에 P-20261121-fcfdccb1 / yklee-linux, 커밋 1be9dfec 기준 들여오기 1193 파일 실패 0, Claude Code 는 local scope 로 연결 — 붙으려면 실행 셸에 `.workflow-hub/env` export, 표식 · CLAUDE.md 허브 영역 · .mcp.json 보류 → 1.x 가 정본 그대로). 이어 **`/setup.md` 가이드 done** (main-022: 빈 폴더에서 Claude Code 가 페이지만 읽고 `hub_client.py bootstrap` 으로 셋업 완주, 원격 없으면 로컬 키 → `hub_project_bind_remote`; requirements §16.7; main-023 으로 Codex · MiniMax · Antigravity 도 실측 — 3/3 setup_complete, agy 확인 결함 수리). 이어 **v2.0.0 · v1.30.0 발행** (main-024 범위 · 운영 가이드, main-025 채널 내리기, main-026 발행 · 도구 수리, main-011/release-1.x-007 안내 판). 남은 것: 운영 저장소 실제 전환(허브 위치 결정) · 39.1 다른 호스트 · M-040 발행. 실제 전환은 상시 허브 위치를 정한 뒤. 워크트리 `../standard_ai_workflow-1x` (release/1.x) 는 main `.venv` + `PYTHONPATH=<worktree>/workflow-source` 로 검사한다.
- (137차 후속, 2026-11-21) **M-036 done** — WBS-36.3 A (TASK-2026-11-21-main-003: 위키 운반 = 1.x 디렉터리 무손실, OKF 는 출판 · 남의 묶음 loose 만 — R8.6 소유자 결정으로 정정) · B (TASK-2026-11-21-main-004: 선택 클라이언트 `hub_client.py` 첫 판 — 보낼편지함 · 캐시 · 세션 시작 보고). 1.x OKF 결함 2건은 `release/1.x` backlog (`release-1.x-002` · `-003` — 그 브랜치 메모리에). **다음 M-037** (허브 화면 · 워크벤치 확장). 후속 후보: 클라이언트 hook 체크포인트(§7 ①) · 위키 점수 함수 인자화 · 원격 clone 캐시.
- (137차 후속, 2026-11-21) **M-036 WBS-36.2 done** (TASK-2026-11-21-main-002 — memory_index · 양방향 링크 · 출처 sha · 위키 원격 읽기, `check_hub_wiki` 9/9). 1.x 결함 `bidir_link` 수리는 main(`41b39d51`) · `release/1.x`(`05678400`) 둘 다 — 다음 1.x patch 노트에 싣는다. **다음 WBS-36.3** — 들여오기 · 내보내기 (OKF · git 스냅샷) · 오프라인 보낼편지함. 들여오기는 요청 상한 256KB 로 묶음을 나눈다. 후속 후보: 위키 점수 함수 인자화 · 원격 clone 캐시.
- (137차 후속, 2026-11-21) **M-036 WBS-36.1 done** (TASK-2026-11-21-main-001 — 허브 위키: DB 판 5 · `hub/wiki.py` · 도구 5종 · V-1/V-4 본체 `common/wiki_rules.py` 공유 · `check_hub_wiki` 5/5). **다음 WBS-36.2** — memory_index · 양방향 링크(E5) · 저장소 참조 sha · freshness 원격 읽기(R8.4, 지금은 미측정) · 점수 함수. 36.3 OKF 들여오기는 요청 상한 256KB 때문에 묶음을 나눠 보내야 한다. kit 결함 후보: 주장 린트 L7 이 인용된 주장을 '재지 않는' 으로 경고.
- Codex 데스크톱을 완전히 재시작한 뒤 새 셸에서 `Get-Command wk`, `wk session-start`, `gh`, `unzip`, `python3 --version`, `wk doctor --json` 을 확인한다. 재시작 후에도 `wk` 가 빠져 있으면 사용자 PATH 가 데스크톱에 전달되는지 다시 진단한다. Codex CLI 실행 파일이 계속 PATH 에 없으면 `codex` 채널의 `installable=false` 는 별도 CLI 미설치 상태로 기록한다.

- 누적 기록은 [`lessons.md`](./lessons.md) (규칙 15절) · [`sessions/handoff-notes_*.md`](./sessions/) (기록 14절) 로 이관됐다 — 최신이 위, 세션 시작에 읽지 않는다.

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

> ~~**89차가 남긴 결정 대기 2건**~~ ✅ **둘 다 해소** (2026-10-19 소유자 결정): ①매트릭스 실행 기록은 발행 게이트가
> **요구하지 않는다** — 현행 유지(해석기 · SDK 민감 코드를 건드린 발행만 돌리고, 생략 사유를 노트 §3 에 적는다. v1.20.1 · v1.21.0 이 그 방식). ②원격 브랜치 삭제 push 는
> **main · 태그만 막는다** (main-007, `gate_evidence.is_protected_delete`) — 기능 브랜치 삭제는 worktree 합류 흐름이라 통과. 새 클론·호스트는
> `git config core.hooksPath .githooks` 를 한 번 켜야 push 게이트가 선다.

> **main-014 는 93차에 닫혔다** — 발행 뒤 이 호스트 채널 재적용이 `docs/RELEASE.md` §2.8 이 됐고,
> `wk doctor` 의 `content_drift.behind` 가 '읽히는 사본 < 정본 버전' 을 발견으로 낸다. 이 호스트의
> 실제 재적용(1.10.0 → 1.11.0)도 93차에 §2.8 대로 실행해 doctor `behind=[]` 확인 — 남은 것은 claude-code CLI 재시작뿐.

> **v1.12.0 은 93차에 발행됐다** (`TASK-2026-09-28-main-014`) — minor + 은퇴 shim. **v1.13.0 에서
> `verify_required_ci` · `REQUIRED_CI_WORKFLOWS` 를 지운다** (deprecation policy spec §3.7 마지막 체크박스).

> **v1.14.0 은 97차에 발행됐다** (`TASK-2026-09-28-main-021`) — Antigravity MCP 도구 이름 수리(main-020) + doctor `plugin_enabled` 4채널. 남은 것: **macOS 호스트 §2.8 재적용**(1.13.0 → 1.14.0) 을 그 호스트 다음 세션에서 `wk doctor` `behind=[]` · `disabled=[]` 로 확인.

> **v1.13.0 은 발행됐다** (`TASK-2026-09-28-main-016`, 96차 close) — 태그 `1f16e431`, Release asset 4종, macOS §2.8 재적용 94차 완료. `plugin_enabled` 는 96차에 4채널로 넓혔다(main-018 close). Linux i5-1335U 호스트는 발행 직후 §2.8 을 했다 — 97차 doctor 4채널 `[in-sync]` 1.13.0 · `plugin_enabled` 4채널 enabled.

> **은퇴 shim 2종은 93차에 코드에서 지웠다** (`TASK-2026-09-28-main-015`). v1.13.0 으로 발행했다. blocked 1건: 08-25-main-017 Windows.

> **main-017(방치 worktree)은 94차에 닫혔다** — macOS 호스트의 worktree 4개 제거, `git worktree list` = main 하나.

> **main-018 은 93차에 닫혔다** — 편중은 배선 누락이 아니라 측정 오염(테스트·`check_self_application` 단독 실행) + 호출 빈도.

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
