# Changelog

- 문서 목적: 저장소의 모든 주요 변경을 release 단위로 기록한다 (Keep a Changelog 형식).
- 범위: git log 에서 추출한 release 별 Added / Changed / Fixed 항목.
- 대상 독자: maintainer, 릴리스 매니저, 외부 consumer
- 상태: stable (자동 생성물)
- 최종 수정일: 2026-11-24
- 관련 문서: [`./releases/`](./releases/) (release note), [`../docs/RELEASE.md`](../docs/RELEASE.md) (릴리스 절차)

All notable changes to this project will be documented in this file.

본 파일은 `tools/release_pipeline.py changelog-gen` 으로 자동 생성됩니다 (v0.7.14+).
수동 편집은 다음 생성 시 덮어써진다 — 형식/metadata 변경은 생성기를 고칠 것.

## [Unreleased] - 2026-11-24

### Added

- feat(hub): serve approval requests as A2A 1.0 tasks (dc583488)
- feat(hub): allow signing up without a token (c5150883)
- feat(hub): run migrations through agent request and human login approval (85b9865a)
- feat(hub): port 1.x migration to Go and let admins delete unused callsigns (92124377)
- feat(hub): add human accounts and agent confirmations (8fde5f02)
- feat(hub): complete v3.2.0 pilot capabilities (d1c67801)
- feat(hub): add project knowledge and DCR sharing (679927a6)
- feat(mcp): release modern 2026-07-28 protocol support (ae732239)
- feat(hub): add PostgreSQL backend for Go and Python (152ef811)
- feat(hub): prepare Go 3.0.0 pre-release pilot (548e8654)
- feat(hub-go): extend web UI route coverage (b0214862)
- feat(release): package Go hub assets for 3.0 (2711126a)
- feat(hub-go): port sessions and orchestration (M-056) (08f9bd40)
- feat(judge): judge/1 CLI 프로토콜 및 plan.lint · plan.states · task.status Python·Go 순수 판정 구현 (M-054 WBS-54.1, TASK-2026-11-22-main-036) (8d1c2840)
- feat(ui): 중앙 허브 2.1 오케스트레이션·로드맵·워크벤치 UX 및 PC 중계(Python·Go) 무깜빡임 로컬 화면 완성 (M-053 WBS-53.1~53.2, TASK-2026-11-22-main-034~035) (1cfe442a)
- feat(hub-go): check_hub_relay 구현 스위치(python·go) + Go 중계 실제 어댑터 실측 — M-052 S1 완료 (WBS-52.3, TASK-2026-11-22-main-033) (7aff454b)
- feat(hub-go): PC 중계 Go 판 — CLI · 설정 · 긴 폴링 · 어댑터 3종 · 로컬 화면 (M-052 WBS-52.2, TASK-2026-11-22-main-032) (5bd6baf5)
- feat(hub-go): hub-go 모듈 뼈대 · cmd/workflow-hub · check_go_build 6 대상 크로스 빌드 (M-052 WBS-52.1, TASK-2026-11-22-main-031) (4cd322e3)
- feat(hub): mcp 2.x 지원 — [hub] 상한 <3, lowlevel 처리기 등록형 · SDK 매트릭스가 허브 MCP 경로를 밟는다 (TASK-2026-11-22-main-022) (99664b10)
- feat(editors): VS Code 확장 껍데기 — 중계 화면 webview · 상태 표시줄 (M-047, TASK-2026-11-22-main-015) (54d684ab)
- feat(relay): 중계 로컬 화면 + 실제 어댑터 실측 — Claude Code · Codex 전 과정 (M-046 WBS-46.3, TASK-2026-11-22-main-013) (7db4bdac)
- feat(hub): 2.1 PC 중계 — 허브 쪽 API · workflow_kit/relay 패키지 · 하네스 어댑터 (M-046 WBS-46.2, TASK-2026-11-22-main-011) (8dab7174)
- feat(hub): 2.1 오케스트레이션 구현 2 — 오케스트레이터 lease · 배정 상태 기계 · 보고 · 정지 · 진입 규칙 (M-045, TASK-2026-11-22-main-010) (a5149449)
- feat(hub): 2.1 오케스트레이션 구현 1 — DB 판 11 · 세션 · 받은편지함 편승 · 대기 도구 async · 수신 확인 (M-044, TASK-2026-11-22-main-009) (98571c65)
- feat(2.0)!: 2.0 줄은 kit 플러그인 채널을 내지 않는다 — marketplace.json · 발행 zip 을 KIT_PLUGIN_CHANNEL 하나로 (R16.6 · Q10, M-040 WBS-40.2, TASK-2026-11-21-main-025) (708042bb)
- feat(1.x): 1.x 안내 판 — session-start 의 2.0 안내 · EOL 한 줄, README '2.0 으로 옮기기 · 1.x 에 머물기' (TASK-2026-11-21-release-1.x-007, R16.4 · R14.8 · R16.3 · R16.6) (12c5d96f)
- feat(hub): /setup.md 실측 Codex · MiniMax · Antigravity — agy 등록을 mcp list 로 확인 (M-039 WBS-39.1, TASK-2026-11-21-main-023) (5602a2a8)
- feat(hub): 에이전트용 셋업 가이드 /setup.md · hub_client.py bootstrap · 원격 없는 등록과 원격 묶기 (M-039 WBS-39.1, TASK-2026-11-21-main-022) (53076aac)
- feat(hub): 이 호스트 테스트베드 실사용 — 발견 7건 수리 (M-039 WBS-39.2, TASK-2026-11-21-main-020) (dbe48ac1)
- feat(hub): 허브 간 프로젝트 이전 HTTP 경로 — 대상 허브 일회용 초대 코드 · hub_client.py move (M-039 WBS-39.4, TASK-2026-11-21-main-018) (9eb3805b)
- feat(hub): 허브 서버 간 프로젝트 이전 — 묶음 · 관리자 CLI export/import · 원본 봉인 (M-039 WBS-39.4, TASK-2026-11-21-main-017) (a6a442fa)
- feat(hub): 1.x 전환 범위 확장 — 아카이브 브랜치 · 결정 응답 · baselines · PURPOSE/PROFILE · 날짜별 backlog (M-039 WBS-39.2, TASK-2026-11-21-main-016) (1b0707ca)
- feat(hub): 1.x 전환 운반을 선택 클라이언트로 — hub_client.py migrate (M-039 WBS-39.2, TASK-2026-11-21-main-015) (580398d5)
- feat(hub): 이 저장소 전환 리허설 — 계획이 남기는 파일 · 커밋 안 된 파일을 보고 (M-039 WBS-39.2, TASK-2026-11-21-main-014) (1163428c)
- feat(hub): 하네스 4종 실측(Linux) — Codex 승인 안내 · repo_results 목록 꼴 (M-039 WBS-39.1, TASK-2026-11-21-main-012) (e62963f8)
- feat(1.x): '허브로 옮김' 표식이 있으면 쓰기 거절 · session-start 는 허브를 가리킨다 (M-038 WBS-38.3 일부, TASK-2026-11-21-main-010) (e58c3221)
- feat(hub): 1.x 전환 — '허브로 옮김' 표식 쓰기 지시 · 되돌리기 (M-038 WBS-38.2, TASK-2026-11-21-main-009) (9dfb42c5)
- feat(hub): 1.x 전환 — 감지 · 전환 계획 · 들여오기 (M-038 WBS-38.1, TASK-2026-11-21-main-008) (0bbbfcd3)
- feat(hub): 허브 화면 — 지침 편집 · 에이전트 제안 승인(D11) · 위키 읽기 (M-037 WBS-37.3, TASK-2026-11-21-main-007) · M-037 done (88523dc9)
- feat(hub): 허브 화면 — 콜사인별 handoff · 지금 누가 무엇을 · 지침 판 현황 (M-037 WBS-37.2, TASK-2026-11-21-main-006) (c86b58ef)
- feat(hub): 허브 화면 첫 판 — 프로젝트 · task 목록 · 계획 · 결정 답 · 이력 (M-037 WBS-37.1, TASK-2026-11-21-main-005) (69e65a37)
- feat(hub): 선택 클라이언트 첫 판 — 오프라인 보낼편지함 · 캐시 · 세션 시작 보고 (M-036 WBS-36.3 B, TASK-2026-11-21-main-004) · M-036 done (25e8574a)
- feat(hub): 위키 운반 — 디렉터리 무손실 들여오기 · 내보내기 + OKF 출판 · 남의 묶음 들여오기 (M-036 WBS-36.3 A, TASK-2026-11-21-main-003) (825cb49c)
- feat(hub): memory_index · 양방향 링크 · 출처 sha · 위키 원격 읽기 (M-036 WBS-36.2, TASK-2026-11-21-main-002) (d6c64e28)
- feat(hub): 위키 — 페이지 · ingest 묶음 · index/log 생성 · 읽기 · lint (M-036 WBS-36.1, TASK-2026-11-21-main-001) (c21bf708)
- feat(hub): 콜사인별 기억 — handoff · 세션 끝 · compact · state.json v1 (M-035 WBS-35.1, M-035 done) (7e42bf9e)
- feat(hub): 1.x 와 같은 판정 — 계획 린트 · done 게이트 · 결정 응답 · WBS 게이트 · 로드맵 진척 (M-035 WBS-35.2 · 35.3) (6337828e)
- feat(hub): 부트스트랩 셋업 · 지침 렌더링 · 세션 시작 확인 (M-034) (7c7df1db)
- feat(hub): 2.0 허브 코어 — 서버 · SQLite · 등록 · 콜사인 · task · 이력 · 원격 MCP 경계 (M-033) (67a00c96)
- feat(guard): 검증 간소화 기간 스위치 — <git common dir>/workflow-simplified-verification 이 있으면 --no-verify push 만 통과 (b0e3dde9)
- feat(workflow): 읽기 전용 소비자 클론에서 session-start 는 저장소에 쓰지 않는다 (-002) (cb31e317)
- feat(workflow): 호스트 역할 — 읽기 전용 소비자 클론은 pull · 환경 맞추기 · 버전 업데이트만, push 는 pre-push 가 막는다 (-001) (1fdcddc5)
- feat(workbench): iPad 폼 제출 수리 · 진행 기록 상기 · 한 호스트 여러 워크벤치 (-003 · -004 · -005) (0c23165f)
- feat(workbench): todo — 브랜치 할 일 · task 체크리스트를 워크벤치에서 보고 고친다 (main-016 · main-017) (78b66be9)
- feat(workbench): 응답 도착 신호 + 작업 세션 hook 자동 반영 · 알림 (main-014) (4dba0962)
- feat(workbench): 작업 중 진행 기록 — 단계마다 Progress 한 줄, 워크벤치가 '지금 하는 일'로 (main-009) (0c2f7fee)
- feat(workbench): 진척 실시간 값 — 원천에서 refresh-state 와 같은 생성기로 계산 (main-008) (b2b025c8)
- feat(workbench): 화면 자동 새로고침 — 바뀐 내용만 다시 그리고 답 쓰는 중이면 알림만 (main-006) (f2ed8112)
- feat(workbench): 화면 개편 — 대시보드형 진척 · 카드형 계획 화면 (main-003) (d1f11bed)
- feat(workbench): 자동 기동 — session-start 가 띄우고 SessionEnd hook 이 내린다 (main-002) (93133bb5)
- feat(workbench): 개방 모드 --open — 토큰 · 로그인 없이 IP 로 보고 답한다 (main-001) (42d74896)
- feat(mcp): plan_inbox(read-only) · plan_import(write) — 워크벤치 스펙 §8.3 (M-029/WBS-29.2) (f3223d6a)
- feat(workbench): M-029 ② 워크벤치 서버 · 화면 · 검사 넷 · 스킬 (ADR-032, M-029/WBS-29.2) (a2e3b495)
- feat(plan): M-029 ① 이월 정리 — inbox_census 단일 출처 · plan-import 건수 두 필드 · 받은편지함 우회 검출 · 배치 warnings · 정리 일곱 (ADR-032 결정 16 · 17 · 18 · 24 · 25, M-029/WBS-29.1) (bba68693)
- feat(plan): 주장 트리 계획 2단계 — 응답 파일 · 받은편지함 · plan-import · 받은편지함 게이트 · 이어받기 (ADR-031, M-028/WBS-28.2) (c4c14c6b)
- feat(plan): 주장 트리 계획 1단계 — task Plan 에 Claims · Decisions, 린트 · 전이 게이트 · plan-status (ADR-031, M-028/WBS-28.1) (f45c6da1)
- feat(gate): pre-push 가 main · 태그의 삭제 push 를 막는다 — 기능 브랜치 삭제는 통과 (main-007, 소유자 결정 2026-10-19) (dd8beb36)
- feat(minimax-code): doctor 가 이 채널을 잰다 — behind·disabled·재시작 3축 편입 (main-001) (4ab6938c)
- feat(entrypoints): ensure-entrypoints --diet — 기존 진입점에서 과거 kit 생성 그대로인 절만 교체/제거 (진입점 다이어트 3) (14fd87be)
- feat(bootstrap): 생성 진입점 템플릿 다이어트 + 하네스별 분량 예산 검사 (진입점 다이어트 2) (b575b670)
- feat(sdlc): AI-native SDLC 플레이북 A1~A3 적용 — task Plan 절 · verifier subagent · 검사 약화 차단 hook (d8bbf1e4)
- feat(plugin): MiniMax Code 소비 채널 추가 — 페이로드 · 릴리스 ZIP · 로컬 sync (d8e4ebee)
- feat(windows): 하네스가 wk 실행 파일 대신 python -m workflow_kit 으로 kit 를 부른다 (main-007) (2eb7c315)
- feat(branch-memory): worktree 합류 반영 — 병합된 브랜치 메모리를 모 브랜치 메모리에 기록하고 아카이브 (main-004) (82fece56)
- feat(branch-memory): worktree seed 가 모 브랜치 내용을 이어받는다 — 원류 기록 + 합류 시 되돌려 적기 (main-001) (bb1c6088)
- feat(compact-relay): Codex 플러그인에 압축 중계 hook 탑재 + 요약 부재 시 '대조 불가' (main-008) (0baeb787)
- feat(compact-relay): 압축 경계를 워크플로우 메모리로 중계 — wk compact-checkpoint · hook 3종 · 스킬 compact-relay (M-018~M-021, ADR-030) (5a3c9db4)
- feat(doctor): plugin_enabled 절을 4채널로 — codex·grok-build·antigravity 활성 선언 실측 (09-28-main-018) (90e3d52a)
- feat(doctor): plugin_enabled 절 신설 — 설치됐는데 꺼진 플러그인을 발견으로 (09-28-main-017) (880f8327)
- feat(doctor): 설치본 < 정본 버전을 발견으로 + RELEASE §2.8 채널 재적용 (TASK-2026-09-23-main-014) (22653225)
- feat(context-budget): 이관 실행 + 이 저장소 게이트 red 활성 — 필독 195KB → 111KB (M-017/WBS-17.5) (8b7119de)
- feat(handoff): wk rollover-handoff-notes — §5 누적형 절의 출구 (M-017/WBS-17.3) (0292d421)
- feat(state): state.json memory_entries v2 — 전문 복제 대신 포인터 (M-017/WBS-17.2) (10c166cd)
- feat(context-budget): 예산 정본 모듈 + refresh-state 초과 경고 (M-017/WBS-17.1) (ec21152a)
- feat(session-start): task ID 충돌 warning + M-013 concept 종결(③ 출구+예산) → M-015 개설 (dd9a004e)
- feat(dashboard): 멀티에이전트 충돌 지표가 task ID 충돌을 센다 (09-23-main-016) (4c8cd252)
- feat(gate): 게이트 통과 기록 없는 커밋의 push 를 막는다 (main-009) (33e58fdd)
- feat(doctor): 플러그인 MCP 가 실제로 띄우는 해석기의 kit 을 잰다 (main-013) (5631f059)
- feat(memory): memory_index 승격 4건 + 검색이 매칭된 entry 를 안 돌려주는 결함 노출 (f631c3c0)
- feat(tests): 요약의 case 개수를 발화 수와 대조하는 축 (main-004) (88b92542)
- feat(memory): memory_index 7건 승격 — 후보 판정식이 잡음이라 판단으로 골랐다 (main-001) (b7fd4b3a)
- feat(ci): 하한 해석기를 CI 셀에 깔아 부분 측정을 전수로 (main-007) (a9fd2c9c)
- feat(tests): 하한 호환 축의 범위를 저장소 루트 전수로 (main-009) (59e77dbd)
- feat(tests): 컴파일 시점 경고를 캐시와 무관하게 재는 축 (main-008) (73e781fc)
- feat(tests): 저장소 코드가 낸 Python 경고를 게이트 신호로 (main-007) (5205ba80)
- feat(tests): 검사를 도는 해석기를 선언 축으로 (main-006) + 82차 세션 종료 (e5f9b554)
- feat(tests): 선언 하한 Python 을 실물 해석기로 잰다 (main-005) (9915e4ad)
- feat(metrics): 어휘 겹침을 선언 사슬로 — goal coverage · 시계 의존 게이트 · ENFORCES 축 (c08dfebd)
- feat(release): 발행 게이트가 필수 CI 워크플로 전수를 보고 기본 차단한다 (main-005) (c49e2c74)
- feat(harness): gemini-cli 지원 종료 + antigravity 플러그인 채널 신설 — 전 계약 실측 (main-004·005·006 + 30일 main-001) (35a7a859)
- feat(meta-watch): 선언 보급 완주 — 국소 198 / 전역 10 / 미분류 68 (main-002·003) (18d8e369)
- feat(meta-watch): 선언 보급 1차 — 채취 실측에서 WATCHES 71건 + mypy flake close (main-004·main-001) (c3c8634f)
- feat(runner): M-011 — meta-watch 구현 (ADR-028) + 좁은 선언 7건 소탕 (11eb02d2)
- feat(design): M-010 완결 — ADR-028 + test_impact_tiering_spec (실측 3건 기반) (07b61f88)
- feat(roadmap): requirements sign-off — M-009 close + M-010 [design] 선언 (e3ac7a27)
- feat(roadmap): C안 채택 — M-008 close + M-009 [requirements] 진행 (requirements 초안) (12bb8d70)
- feat(roadmap): M-008 선언 — 검사 입력 표면 선언 + 계층별 회귀 실행 계약 (concept) (7aac9ee3)
- feat(harness): overlay 위임 선언(plugin-only) 신설 — 이 저장소 claude-code 채널 플러그인 단일화 (main-010) (caffb013)
- feat(roadmap)!: ADR-027 로드맵 층 — 스키마·파서·상태 생성기·배선·게이트·bootstrap 씨앗 (M-002~M-005) (9dc91713)
- feat(session-start): 부재 진입점을 스스로 채운다 — 낡음은 보고만 (main-006) (b119d68b)
- feat(handoff): §5 를 부류별로 가른다 — 산문이 SSOT 를 복제하던 자리 (main-001) (51cfa9ad)
- feat(deploy)!: 소유권 4번째 분류 '포크됨' + codex 채널 정리 (main-011, -012) (00d30914)
- feat(task-ssot)!: 본문 라벨을 영어로 전환한다 — 4단계 (main-009) (47c84ad4)
- feat(doctor): runtime_load — 노출 미측정 한 칸을 측정으로 옮긴다 (main-009 close) (deb74b82)
- feat(okf)!: v0.2 이행 — legacy 를 남긴 채 정규 필드를 더한다 (ADR-026, main-003) (8ead8bf7)
- feat(doctor): 환경 pre-flight — 배포 축 gap 4개가 전부 닫혔다 (main-019) (c92d3c7b)
- feat(doctor): 드리프트를 마커가 아니라 페이로드 해시로 본다 (main-005) (2f68fb2e)
- feat(entrypoint): AGENTS.md 를 공유 진입점으로 합친다 (main-001, 08-18) (c55631f4)
- feat(deploy): wk doctor — 배포 post-apply 탐침 (main-016, 컨셉 gap 1) (3b50ae95)
- feat(plugin): pi.dev (pi-coding-agent) 11번째 분배 채널 정식 등록 (main-012) (6f2b5435)
- feat(plugin): Grok Build 훅 관례 경로와 설치 채널을 연다 (ae9e1a73)
- feat(memory): task SSOT 4단계 준비 — 정본 표 누락 라벨 보강 + 검사 범위 확대 (43fe58ce)
- feat(memory): task SSOT 3단계 — 라벨을 바꿀 수 있는 상태로 (전환은 다음 release) (a576e92b)
- feat(memory): task SSOT 2단계 — 소실과 중복은 같은 뿌리였다 (0f63ddc0)
- feat(memory): task SSOT 1단계 — 읽는 쪽을 하나로 (index 20개가 조용히 0이었다) (21e96bf0)
- feat(memory): handoff 기준선 롤오프 — 자르지 않고 이관한다 (ab07bafe)
- feat(checks): 무거운 7개에 WATCHES 선언 + check_changed_selection 계약 9 cases (0fa23bab)
- feat(checks): run_all_checks --changed 기전 (WATCHES 선언 기반, 미선언은 항상 실행) (49da7655)
- feat(memory): seed 가 state.json 까지 만들어 끝을 맺는다 + 절반짜리 가드 강화 (96bfb700)
- feat(memory): 아카이브를 이동에서 이관으로 — 미완료 소실 + 참조 끊김 차단 (9b600efb)
- feat(smoke): 브랜치 메모리 네임스페이스 가드 신설 + 정본 창구 정정 (d818625e)
- feat(dist): ship native Codex and Claude plugin archives (51e04eb3)
- feat(dist)!: 2nd deprecation cycle 완결 — 구경로 shim drop + --bundle 기본 read-only (TASK-2026-08-13-main-005) (7fed4158)
- feat(plugin): SessionStart 조건부 규칙 주입 — rules.md + 마커 감지 hook (TASK-2026-08-13-main-003) (573f3138)
- feat(plugin): P3 멀티 하네스 어댑터 — gemini/goose/opencode + 수렴 판정 (TASK-2026-08-12-main-016) (7eb11c30)
- feat(plugin): P4 릴리스 게이트 + session-end 스킬 (TASK-2026-08-12-main-017·020) (2cf95764)
- feat(plugin): Claude Code 채널 개통 — 어댑터 + marketplace + 자기 적용 (TASK-2026-08-12-main-015) (35473da9)
- feat(plugin): 공유 payload 렌더러 — plugin/ 을 정본 파생물로 (TASK-2026-08-12-main-014) (005bc10d)
- feat(safety): backlog-update status 보존 + no_repo_write 실행-중 감시 (TASK-2026-08-12-main-008, -009) (5b89813e)
- feat(cli): cross-platform 지원 1단계 — OS 매트릭스 CI + Windows 가드 (TASK-2026-08-12-main-005) (9351e17b)
- feat(mcp): bundle 분리 — write 도구 별도 서버 + 배포 검토 (TASK-2026-08-12-main-003, -004) (bd121f58)
- feat(federation): self-host add — plex 상시 serving 편입 + --print-systemd-unit (TASK-2026-08-12-main-001) (e625c91e)
- feat(safety): 전량 검사 배타 락 — 동시 runner 의 정숙 구간 침범 차단 (TASK-2026-08-11-main-019) (e7f3ef15)
- feat(harness): 보조 렌더러 §11 주입 완결 — TASK-020 발 결함 26→0 (TASK-2026-08-11-main-028) (d35fe614)
- feat(state): state.json 을 생성물로 전환 — wk refresh-state + drift 검사 + session-start 결함 2건 (TASK-2026-08-11-main-018) (39dc234a)
- feat(standard): 정본 §11 메모리 갱신 경로 신설 + 전 하네스 주입 (TASK-2026-08-11-main-022, -020) (a3d00a64)
- feat(cli): wk 에 session-start / backlog-update / doc-sync 노출 (TASK-2026-08-11-main-021) (1d061474)
- feat(tools): transient writer 감시 도구 저장소 고정 (TASK-2026-08-11-main-013) (36cedf52)
- feat(tests): 브랜치 컨텍스트 정본화 + 로컬 재현 관행화 (TASK-2026-08-10-main-017) (d8d188fd)
- feat(memory): ADR-006 W-4 지표 재정의 — utilization_3tuple north-star (TASK-2026-08-10-main-014) (91e1551e)
- feat(memory): ADR-006 W-3 entry 간 링크 — related_ids + expansion 첫 발동 (TASK-2026-08-10-main-013) (713faec6)
- feat(memory): ADR-006 W-2 질의 다양화 — 컨텍스트 유래 query + telemetry 질의 내용 기록 (TASK-2026-08-10-main-012) (1e50701e)
- feat(memory): ADR-006 회고 (P2-1) + W-1 write-path advisory 루프 (TASK-2026-08-10-main-010, -011) (051e41a0)
- feat(drift): title drift 임계 0.6 실측 캘리브레이션 + registry 비-loopback bind 실측 (TASK-2026-08-10-main-008, -009) (41b98dbc)
- feat(quality): TST-WF-01 측정 재설계 — AST verification-signal, partial 예외 제거 (ff744b4b)
- feat(release): cmd_release 사용성 회복 — pre_check 만성 실패 3뿌리 + dry-run 기본값 (e741de60)
- feat(release): 릴리스 절차에 노트 누적 수치 검증 자리 (step 3.4) (268ede73)
- feat(skill): memory-index-query beta → stable (14/14, 잔여 beta 0) (fd612ad9)
- feat(telemetry): AC2 acceptance 를 윈도 기반 지표로 (c5b69d6b)
- feat(cli,registry,safety,drift): 다음 후보 축 4건 close — wk / HTTP server / branch protection / title drift v2 (ad3ab025)
- feat(cli): [project.scripts] entry points (CLI 化 A안, v1.1.1+) (029ee395)
- feat(safety): pre-push hook — --force server-side 이중화 (3-layer defense, §0.8 #4) (2b5969c7)
- feat(drift): scope drift detection (병합 시점, §0.8 #3) (c687dee8)
- feat(tools): operational MCP tool 4종 CLI wrapper (dual mode, TASK-017) (8b94db8a)
- feat(registry): federation HTTP pull + dashboard 통합 (§7.4 *읽기* 마무리, TASK-016) (1de3c81e)
- feat(registry): federation 정공법 — multi-host registry 합치기 (표준 §0.8 #1) (c32b3369)
- feat(registry): in-flight 워크스페이스 신뢰도 표시 (표준 §0.8 #2, §5A.3) (9326a9c0)
- feat(smoke): mavis attach e2e 회귀 자동화 (§2.68 자동 검증 닫음, TASK-013) (e4470e5f)
- feat(registry): endpoint 기반 mavis alias command/url 합성 (838b12f7)
- feat(registry): RegistryEntry env 필드 + sync_mavis env 합성 (e0cdebe3)
- feat(registry): registry ↔ mavis 글로벌 양방향 동기 (TASK-2026-08-08-main-009) (a51f683a)
- feat(registry): seed_workspace_memory self-register (TASK-2026-08-08-main-008) (29c3e4bf)
- feat(bootstrap): mavis 데스크탑 harness 신규 등록 + 글로벌 mcp.json 자동 emit (322a7924)
- feat(registry): workspace registry 신규 (표준 §10.2 §7.1, §5A.3) (a3a9442f)
- feat(dashboard): `_branch_state_paths` 복수 root 취합 (표준 §10.2 §7.3) (f97a9b12)
- feat(tools): 워크스페이스 선점 도구 — 표준 §10.2 플로우 완결 (c51d0521)
- feat(tools): 원격 워크스페이스 현황 조회 — 표준 §10.2 1~3단계 (e5479428)
- feat(tools): 워크스페이스 메모리 seed 도구 — 표준 §10.2 자동화 1단계 (9751cc56)
- feat(standard)!: 다중 작업·팀웍 워크플로우를 표준에 정식 반영 (§10 + §1) (8a2a7a97)
- feat(workflow): 다중 워크스페이스 오케스트레이션 설계 + union merge 적용 (7cfdb609)
- feat(sdk-compat): 버전 고정 SDK 필드 이름을 작성 시점에 막는다 (A안, §2.65) (0e9c5fa3)
- feat(sdk-matrix): 매트릭스를 로컬로 내렸다 — 알고 있던 함정을 다시 밟았다 (§2.64) (fff417bb)
- feat(mcp): transport_ready 축 분리 + apply_mode 승격 기준을 실행 가능한 검사로 (§2.63) (9835eeb7)
- feat(mcp): Claude Code MCP 를 붙였다 — 표가 선언만 하고 배송하지 않던 행 (§2.60) (6ebbd8b5)
- feat(tools): 네 번을 손으로 찾았다 — 기준 전수 조사를 저장소에 남긴다 (§2.52) (5c8a85f3)
- feat(ci): 두 major 커버리지를 선언으로 — mcp SDK 버전 matrix (§2.45) (4cfda75f)
- feat(deps): optional dep import 탐지층 — 관대한 설정은 판정을 지운다 (§2.44) (ea1576cd)
- feat(rules): 진입점 규칙을 정본에서 생성 + 자기 적용을 검사로 고정 (§2.31~§2.34) (6563974d)
- feat(checks): YAML·스킬·MCP 를 파서와 도구로 검사 + 배포판 단일화 (§2.30) (f1db90de)
- feat(tests): 규약 단일 출처 검사 + 남아 있던 사본 7건 해소 (전량 209/209) (fe6fcfaf)
- feat(dashboard): 판정 지표는 근거를 함께 낸다 + Panel 6 north-star 도 같은 결함 (208/208) (d5be282d)
- feat(tests): maturity registry 정합 메타 체크 + 드리프트 3건 해소 (전량 203/203) (43079c04)
- feat(skill+wiki): memory-freeze stable 승격 + wiki L2 계층 복구 (전량 202/202) (dcbf2af7)
- feat(tests): 실행 표면 / 저장소 오염 메타 체크 2종 + suffix strip 버그 수정 (95d3034b)
- feat(memory): branch-scoped 후속 — session-start 아카이브 wiring + 문서/smoke + TZ flaky 수정 (7dab09d6)
- feat(memory): 브랜치별 메모리(branch-scoped) + 종료 브랜치 자동 아카이브 (73b22a8e)
- feat(test): MEMORY_GOVERNANCE ↔ global_workflow_standard cross-check smoke 신규 (fd28356e)
- feat(test): DOCUMENT_INDEX / CODE_INDEX / RELEASE.md cross-check smoke 신규 (v0.15.16~18) (1158431a)
- feat(bidir-link): wiki↔memory 양방향 link 자동 sync + audit — Phase 13 AC4+ close-out (v0.13.3-beta) (1580aeb8)
- feat(release): self-recovering drift prevention — Phase 13 AC3 close-out (v0.13.2-beta) (b857ff30)
- feat(memory-index): telemetry sidecar — Phase 13 AC2 close-out (v0.13.1-beta) (216fd60a)
- feat(dist): add claude-code harness dist (v0.11.22-beta) (c2b201fc)
- feat(mcp+adr): stdio-sdk promotion readiness smoke + ADR-007 placeholder (8505aa2a)
- feat(mkdocs): drift prevention P3 — build-time git date inject plugin (e0637104)
- feat(release): drift prevention automation (v0.11.23 P0+P1+P2) (b623ae28)
- feat(skill): ADR-005 Memory Index Phase 3d backlog-update memory_index wiring (last skill) (2ab3b6c8)
- feat(skill): ADR-005 Memory Index Phase 3c doc-sync memory_index wiring (opt-in) (c46d7296)
- feat(skill): ADR-005 Memory Index Phase 3b session-start memory_index wiring (opt-in) (73564d90)
- feat(skill): ADR-005 Memory Index Phase 3 dispatcher entry (memory-index-query skill beta) (7be50290)
- feat(skill): ADR-005 Memory Index Phase 2b BM25 2단계 fallback (stdlib only) (59731465)
- feat(skill): ADR-005 Memory Index Phase 2 --merge opt-in canonical merge (d2d8a1cf)
- feat(skill): ADR-005 Memory Index Phase 1.5 state.json hook (memory_entries optional merge) (4655e7c1)
- feat(skill): ADR-005 Memory Index Phase 1 prototype (helper + schema + smoke) (e4c73438)
- feat(test): robust-patcher smoke test 신규 (5 case) (ba689a3a)
- feat(skill): robust-patcher run_robust_patcher.py 표준화 + 4종 error_code (92493249)
- feat(skill): robust-patcher Pydantic schema 정합 + apply_robust_patch_detailed helper (d90f7863)
- feat(test): 2 신규 smoke test (merge-doc-reconcile + project-status-assessment) (29ae1cc1)
- feat(skill): 2 skill stable error_code 추가 (backlog-update + merge-doc-reconcile) (ddac80e2)
- feat(skill): project-status-assessment Pydantic schema 정합 + missing_required_document error_code (65d55911)
- feat(wiki): score trend dim 별 alert (--alert --baseline + 4 smoke test) (0224a76f)
- feat(wiki): score trend over time (commit 별 추적) + 10 smoke test (99e299f8)
- feat(wiki): emit_wiki_l2_body.py --mode=metadata-only + 498 page 본문 emit (c72bdc31)
- feat(wiki): maintainability score metric (6 dim dashboard) + 12 smoke test (49dfc78c)
- feat(wiki): emit_wiki_l2_body.py update_l2_full() 추가 + 전체 apply 검증 (7a4dbaec)
- feat(v0.7.0 follow-up): packaging + session-start opt-in + evaluate_compliance (71de1b0e)
- feat(v0.7.0 step 7): Extension 시스템 일반화 (5 file, +1150 line, 23 test PASS) (0052da14)
- feat(v0.7.0 step 6): Reverse Engineering 9-Artifact (11 file, +925 line, 19 test PASS) (4bbd3915)
- feat(v0.7.0 step 8): Security Baseline extension (6 rule + opt-in + 15 test) (dc2c22b8)
- feat(v0.7.0 step 9): Unit of Work 3-layer template + smoke test (17 test PASS) (c981cac1)
- feat(v0.7.0 step 10): Audit Log 표준화 (1 spec + 1 helper fix + 13 test) (54e96a96)
- feat(v0.7.0 step 1): stage_completion required 격상 + ensure fallback (6e57cf3d)
- feat(v0.6.1.5): P2.5 R9 wiki-ingest source rule (archive/ only) (0634dd62)
- feat(v0.6.0.1): P1.5 memory/active/ rename + bootstrap --enable-wiki + 6 harness wiki/ stub (7134c5bf)
- feat(phase9): implement strict pydantic schemas, mcp v1.0 migration, and multi-agent topology (2bb8bc7d)
- feat: stabilize phase 8 and prepare for phase 9 evolution (dce9023f)
- feat: optimize auto-mode detection with prioritized keywords and reordering (5d208995)
- feat: complete Phase 6/7 residual tasks (robust-patcher MCP, smart-reader unification, auto-mode detection) (e12a3cf8)
- feat: complete Phase 8 infrastructure and maturity assessment (a6540425)
- feat: implement mode-aware workflow optimization (383a50c0)
- feat: improve multi-stack analyzer and update maturity matrix to Phase 6 done (ec0b6074)
- feat: bump version to v0.4.1-beta and implement legacy gitignore migration (88e5b126)
- feat: enhance packaging and deployment with version-aware upgrade and gitignore scripts (7a3b9327)
- feat(workflow): complete isolation of workflow infrastructure into ai-workflow/ folder (b86256f1)
- feat: Implement branch-isolated workspace, doc governance, and AI doc compiler (44709341)
- feat(workflow): implement Phase 6 tools and Event Sourcing backlog for conflict-free collaboration (1b37b86f)
- feat: complete transition to antigravity harness and enable package export (e8a6198d)
- feat: enhance antigravity harness with artifacts and browser sub-agent guidelines (221e02e2)
- feat: migrate workflow state paths to relative workspace-root basis (441d39d3)
- feat: Phase 6 prep and bug fixes (synchronized with main structure) (46011908)
- feat: integrate release note template into workflow core and scripts (4845aa1f)
- feat: implement robust-patcher and smart-context-reader for local LLM optimization (974a4e3e)
- feat: add Pi Coding Agent (pi.dev) harness support (v3.0.1) (9c4fb1d3)
- feat: Phase 5 official release (v3.0) with unified operations path and updated schemas (3a7e4c1d)
- feat: complete Phase 5 intelligence and governance automation (6419ef51)
- feat: implement git_history_summarizer MCP prototype and verify real-world pilot (4527e48e)
- feat: establish governance SSOT (Maturity Matrix) and zero-friction onboarding (c5818566)
- feat: enhance E2E demo workflow with write-capable pipelines (1da7ee8f)
- feat: enhance onboarding flow and stabilize document parsers (24bf2e06)
- feat: enhance bootstrap script with automatic dependency management (7ad8be07)
- feat: workflow 업데이트 마이그레이션 스펙 및 --preserve-data 지원 추가 (5887d2e7)

### Changed

- docs(workflow): record v3.2.2 rollout and open the A2A 1.0 transition (cbb0cc5c)
- docs(hub): call the hub inbox by its name instead of A2A (9682fc4d)
- docs(workflow): close human confirmation implementation task (190286cb)
- Sync embedded Go bootstrap guidance (08c2c3bd)
- Document all hub MCP workflows in bootstrap guidance (bfc553a5)
- Prepare workflow hub 3.2.1 prerelease (99866edc)
- docs(release): record v3.2.0 HomeLab pilot (84f222d2)
- docs(release): record 3.1.0 deployment evidence (eff1ebd7)
- release(hub): prepare 3.1.0 prerelease (e61e2e06)
- test(workflow): follow fixture default branch in memory check (91967155)
- chore(memory): close v3.0.2 prerelease deployment (3fa256b8)
- chore(release): sync v3.0.2 metadata (ad9e664a)
- docs(windows): prefer Python hub on managed PCs (95089177)
- docs(memory): record 3.0.1 verification progress (b8c0af8c)
- chore(memory): close Go UI verification session (a5a958a0)
- chore(memory): record Go UI verification stage (1f8f215d)
- chore(memory): close release prep session (92c52dce)
- chore(memory): record release prep push gate (cd2d8b37)
- chore(memory): record M-056 push gate (6c3acd07)
- chore(memory): 141차 세션 종료 — M-052~M-055 Go 전환 S1·UI·S2-a·S2-b 반영, 다음 S2-c/d (71954d44)
- hub-go: implement hub core db, assets, store, tools, mcpserver, httpapi, CLI (M-055) (7d7986cb)
- M-054 WBS-54.2~54.3: complete 7 pure judge/1 ops, corpus, and parity gate (468ff6eb)
- chore(memory): 140차 세션 종료 — v2.1.0 발행 · mcp 2.x · Go 전환 concept/requirements/design 반영, 다음 M-052 S1 중계 (07db4a9b)
- docs: Go 전환 design 확정 — DG1~DG5 권고안 · ADR-035 Accepted · PURPOSE Go 런타임 예외 · M-051 done · M-052 S1 중계 선언 (TASK-2026-11-22-main-030) (0199b6db)
- docs(core): 허브 Go 판 설계 hub_go_spec — hub-go 배치 · 순수 판정 op · judge/1 CLI · 차분 · 적합성 검사 · S1 중계 · 빌드 · DG1~DG5 (M-050 done · M-051, TASK-2026-11-22-main-024~030) (bf1116dd)
- docs(planning): 2.x 전면 Go 전환 requirements R25~R35 · 계약 표면 실측 · 정할 것 Q1~Q6 · ADR-035 Proposed (M-050, TASK-2026-11-22-main-024 · 025 · 026) (01d562fd)
- docs(planning): Go 전환 결정 — R1 전면 Go(허브 · 공유 판정 · 중계), 나머지 권고안 · M-049 done · M-050 requirements 선언 (TASK-2026-11-22-main-021 · 023) (30199b4d)
- docs(planning): 허브 · PC 중계 Go/Rust 전환 concept — SDK · 탐침 실측 · 이식량 · 선택지 A~D · 권고 B(중계만 Go) (M-049, TASK-2026-11-22-main-021) (ddfa5321)
- chore(memory): 2.1.0 발행 task 등록 (TASK-2026-11-22-main-019) (19fb3080)
- docs: README 재작성 — 2.0 허브 · 2.1 오케스트레이션 구성 · 시스템 구성도 · 아키텍처 (TASK-2026-11-22-main-018) (33a39ea8)
- docs(hub): 2.1 진입 지침 세션 끝 — push 가 막힌 일하는 세션은 권한을 바꾸지 않고 보고 (M-048 WBS-48.2, TASK-2026-11-22-main-017) (f0cd1248)
- docs(decisions): ADR-034 Accepted — design 결정 DO1~DO13 소유자 확정, M-043 종결 (TASK-2026-11-22-main-007 · 008) (70fa3683)
- docs(core): 허브 오케스트레이션 스펙 초안 — DB 판 11 · 도구 · 세션 식별 · 전달 · 중계 어댑터 계약 · DO1~DO13 (M-043, TASK-2026-11-22-main-007) (9ea249f1)
- docs(decisions): ADR-034 허브 오케스트레이션 Proposed · 요구 Q1~Q4 권고안 — M-042 종결 (TASK-2026-11-22-main-005 · 006) (c9c83d4f)
- docs(planning): 허브 오케스트레이션 요구 R17~R24 · 추적표 · 정할 것 Q1~Q4 (M-042 WBS-42.2, TASK-2026-11-22-main-005) (a1d0d0b0)
- docs(planning): 허브 오케스트레이션 실측 S 2차 — hook · 신뢰 없는 간접 전달 (도구 응답 편승 · 대기 도구 · 받은편지함 파일) (M-042 WBS-42.1, TASK-2026-11-22-main-004) (b36c65c7)
- docs(planning): 허브 오케스트레이션 requirements 개설 · 실측 S — Claude Code · Codex 세션 제어 수단 (M-042 WBS-42.1, TASK-2026-11-22-main-003) (36e80f85)
- docs(planning): 허브 오케스트레이션 concept 종결 — 소유자 O1~O10 권고안 (M-041 done, TASK-2026-11-22-main-001) (569fd7b3)
- docs(planning): 허브 오케스트레이션 concept 초안 — 중앙 허브 · PC 중계 허브 · 하네스 · 세션, 메인 오케스트레이터 (M-041 WBS-41.1, TASK-2026-11-22-main-001) (a2143e54)
- chore(memory): 138차 세션 종료 — v2.0.0 · v1.30.0 발행 반영, 후속 task main-027 (발행 산출물 접두사 glob) (1880ae95)
- docs(release): 두 줄 발행 정책 — 2.x(main) wheel+sdist · latest 규칙 · PEP 440 사전 판, 1.x(release/1.x) 플러그인 zip · --latest=false (R16.6 · R16.7, TASK-2026-11-21-main-026) (5ea567d6)
- docs(2.0): README 2.0 허브 안내 · 설치 문서 플러그인 채널은 1.x 줄(release/1.x 고정) (M-040 WBS-40.1, TASK-2026-11-21-main-026) (4ac980e7)
- docs(hub): 2.0.0-beta 발행 범위 확정 · 허브 운영 가이드 (M-040 WBS-40.1, TASK-2026-11-21-main-024) (dfec2494)
- chore(memory): 138차 세션 정리 — handoff 기준선 · 주 작업 축 갱신, 기준선 1건 이관 (M-039) (f044897b)
- chore(hub): 이 저장소 테스트베드 허브 실제 등록 close — 들여오기 1193 파일 실패 0, 표식 보류 (M-039 WBS-39.2, TASK-2026-11-21-main-021) (427e839e)
- chore(hub): 이 저장소 허브 등록 셋업 — .workflow-hub/ git-ignore (M-039 WBS-39.2, TASK-2026-11-21-main-021) (1be9dfec)
- chore(memory): WBS-38.3 일부 close (D1 = 1.x 안내 판은 2.0.0 발행 때) · 안내 판 발행 task 등록 (TASK-2026-11-21-main-010 · -011) (cc3beedb)
- test(hub): check_hub_wiki case 11 의 초 경계 흔들림 — OKF index.md 생성 시각만 걷어 비교 (0a56fe41)
- chore(memory): 합친 수정 브랜치 메모리 정리 — fix/1x-long-lived-branch-memory task 닫고 아카이브 · 명세 스탬프 (v1.29.1 게이트) (148e6cdc)
- Merge remote-tracking branch 'origin/main' (c150de60)
- Merge pull request #32 from ykylee/fix/long-lived-branch-memory (383d1fdf)
- Merge pull request #31 from ykylee/fix/1x-long-lived-branch-memory (0a7e4c76)
- chore(memory): 137차 세션 종료 — 기준선 M-036 done · 다음 M-037, 지난 compact 체크포인트 정리 (aa746c88)
- chore(memory): release/1.x 브랜치 메모리 seed · 1.x OKF 결함 2건 등록 (R16.8) (e16ce897)
- chore(memory): WBS-36.2 close · handoff 다음 WBS-36.3 (9e8f5817)
- chore(memory): 2.0 허브 합류 반영 · main 기준선 137차 · §5 이관 + fix(kit): sessions/ 로 옮기는 블록의 상대 링크 보정 (ddc703dd)
- merge: claude/workflow-hub-concept → main — 2.0 허브 M-031~M-035 (R16.5 release/1.x 분기 뒤) (dd011029)
- docs(hub): R16.5 1.x 분기 브랜치 이름 release/1.x 확정 · handoff (8ef1ee07)
- chore(memory): 137차 정리 — task -012 · -013 close, handoff 기준선 요약 · 다음 일 M-036 (287f6016)
- Merge remote-tracking branch 'origin/main' into claude/workflow-hub-concept (187f6832)
- chore(memory): 병합된 브랜치 2개 메모리 합류 반영 · 아카이브 (bb943c81)
- chore(memory): 136차 세션 종료 — handoff 기준선 · 다음 일 M-036 (d3d8c9a7)
- docs: ADR-033 Accepted · 허브 design DS1~DS9 확정 · PURPOSE 2.0판 적용 — M-032 done (d8bc205f)
- docs(core): 허브 스펙 초판 hub_spec.md — 스키마 · 도구 · 흐름 (M-032/WBS-32.1~32.3) (be13e544)
- docs(planning): 허브 requirements 종결 — Q6 · Q9 · Q10 확정, M-031 done (cc6bdba7)
- chore(memory): handoff — WBS-31.3 완료 · 다음 일 Q6 · Q9 · Q10 (cd7994de)
- docs(planning): PURPOSE 2.0 개정안 · 1.x 유지보수 정책 R16 (M-031/WBS-31.3) (9292da79)
- docs(planning): 허브 requirements Q7 — 참조 못 하는 하네스는 사용자 범위에만 토큰 (R2.5a) (86022db9)
- docs(planning): 2.0 허브 지원 하네스 4종 — Claude Code · Codex · MiniMax Code · Antigravity (Q8) (74f5156c)
- docs(planning): 허브 design 전 실측 S1~S3 — 판정 함수 입구 · 위키 검사 경로 · 하네스별 원격 MCP (M-031/WBS-31.2) (2a9a0776)
- docs(planning): 허브 requirements 소유자 결정 Q1~Q5 — Q4 화면 인증은 arcturus 과제 대시보드 방식 (3abd41be)
- docs(planning): 2.0 허브 requirements 초판 — R0~R15 · 추적표 · 열린 물음 Q1~Q6 (M-031/WBS-31.1) (78884807)
- chore(memory): 135차 후속 세션 종료 — H14 · 가드 스위치 · 다음 일 (M-031 착수) (8a595874)
- docs(planning): H14 — compact 직후에도 허브 확인 · 기록된 작업 이어 가기 (2.0 요구 입력) (3a5367b4)
- docs(roadmap): 2.0.0 로드맵 — M-031 requirements ~ M-040 release (허브 단일 흐름) (5ddaf63d)
- docs(planning): 워크플로우 허브 = 2.0.0 준비 — 열린 결정 전부 권고안 · 세션 시작 확인 · 1.x 전환 (M-030 done) (1d3f5a34)
- docs(planning): 워크플로우 허브 concept (M-030) — kit 없는 부트스트랩 · 허브가 task · handoff · 이력 · 지침 관리, ADR-033 Proposed (baf71ae6)
- chore(memory): 소비자 클론 읽기 전용 session-start task close (-002) — 게이트 333×2 · 브랜치 push, main 미병합 (d31259e4)
- chore(memory): 135차 세션 종료 — v1.28.0 발행 · 호스트 역할, 브랜치 main 합류 · 다음 작업은 새 브랜치로 (2757394f)
- test(workbench): check_workbench_multi case 3 — 호스트의 실제 워크벤치가 쥔 해시 포트면 fixture 를 다시 만든다 (8786cc4d)
- docs(workflow): 호스트 역할은 이 저장소 한정 — 소비자의 개선은 수정 · push 대신 GitHub Issue 로 (-001 보충) (289e2124)
- chore(memory): 호스트 역할 가이드 task close (-001) — 게이트 332×2 · contributor 클론 push 통과 (4ad517e5)
- chore(memory): 135차 세션 메모리 — 원격 동기화 · 재seed · push, seed roadmap_state 미갱신 결함 task 등록 (-002) (219a8460)
- chore(memory): claude/remote-sync-check-234c32 네임스페이스 재seed — main@ca3f59ea 에서 이어받음 (2787e9e0)
- chore(session): 134차 handoff 상태 정합 — 전량 게이트 통과 · push 완료 사실 반영 (ca3f59ea)
- chore(memory): 133차 세션 메모리 — -003 · -005 close, -002 · -004 는 소유자 iPad todo 한 번 대기 (e4bc269c)
- test(workbench): check_workbench_multi 보강 — TIME_WAIT 포트로 '다음 포트' 경로를 비켜 가던 blocker · 해시 분산 · 목록 파일 해제 (-005 verifier) (b58c0f28)
- chore(entry): 진입점 절 해시 재채취 — 0c23165f (정본 §1 진행 기록 원칙) (1b94a470)
- chore(session): 합류 반영 — claude/remote-sync-check-234c32@7fdf0eb5 (완료 14 · 이월 2) + main-002 done (d16eab89)
- test(plan): check_plan_import 의 시간 상한 240 → 480 — 부하에서 172~235s, 게이트 1회 초과 (442b9808)
- merge: origin/main(39a50a11) 을 claude/remote-sync-check-234c32 에 병합 — 11-04 세션 메모리 · roadmap_state 재생성 (6ffa3f69)
- chore(memory): M-029 종결 — task 11-14-003 done (verifier 3차 PASS), M-029 done · Windows 항목은 WBS-28.3 으로, handoff 129차 (7923f659)
- chore(memory): WBS-29.2 의 남은 일(MCP 두 도구)을 task 11-14-003 planned 로 등록 — 파생 진척이 done 으로 앞서가던 것 (c1586fb6)
- chore(memory): M-029 ② 워크벤치 서버 종결 — task 11-14-002 done (verifier 7차 PASS), handoff 128차 (1d0c989b)
- test(workbench): verifier 6차 — 공개의 세 길을 모두 계측 아래 (M-029/WBS-29.2) (d536de9d)
- test(workbench): verifier 5차 — 계측의 flush 가 결함을 가렸다 · link 원본의 구조 판정 (M-029/WBS-29.2) (9230ae82)
- test(workbench): verifier 4차 — 덜 쓰인 파일 판정에 커널 쪽 관찰자 (M-029/WBS-29.2) (ef7cfab0)
- test(workbench): verifier 3차 — 공개의 원자성을 구조로 판정 (M-029/WBS-29.2) (4219728d)
- chore(entry): 진입점 템플릿 변경(a2e3b495) 의 절 해시 재채취 — check_entry_diet case 6 (abf2143f)
- chore(memory): M-027 워크벤치 design 종결 — ADR-032 accepted, task 11-13-006 done, M-029 선언 (7511c1b6)
- docs(workbench): 1차 검증 — 결정 대상의 대안 · 스펙 대응 누락 · 넘긴 항목 복구 (M-027/WBS-27.1) (a71ad14b)
- docs(workbench): 프록시 · 브라우저 실측 + ADR-032 (proposed) + core 스펙 (M-027/WBS-27.1) (62c012aa)
- chore(memory): M-028/WBS-28.2 주장 트리 계획 구현 2단계 종결 — task 11-13-004 done, WBS-28.3(Windows 실측) 등록 (21fc873c)
- docs(plan): 지원하는 받은편지함 · 보관 배치를 스펙 §7-9 에 적고 검증 범위를 그 배치로 (소유자 결정, M-028/WBS-28.2) (593f643d)
- test(plan): 되주입이 빠져나간 자리 보강 — 한도 숫자 · 0 단계 · 배타 생성 · 순서 (ADR-031 2단계, M-028/WBS-28.2) (9577b9a3)
- chore(entry): 진입점 템플릿 변경(c4c14c6b) 의 절 해시 재채취 — check_entry_diet case 6 (668051b3)
- chore(memory): M-028/WBS-28.1 주장 트리 계획 구현 1단계 종결 — task 11-13-003 done, handoff · state 갱신 (a4d9495c)
- chore(entry): 진입점 템플릿 변경(f45c6da1) 의 절 해시 재채취 — check_entry_diet case 6 (9951d406)
- docs(design): 주장 트리 계획 design 종결 (M-026) — ADR-031 accepted + core 스펙 → M-027 · M-028 개설 (36e6540c)
- docs(planning): 계획·진척 워크벤치 requirements 종결 (M-025) — 실측 + R0~R12, 소유자 sign-off Q1 · Q2 (df602c4f)
- chore(session): 11-04 세션 메모리 반영 — minimax-code 채널 재적용 완료(main-001) + MCP 도구 4종 output contract 결함 등록(main-002) (39a50a11)
- docs(planning): 주장 트리 계획 requirements 종결 (M-023) — 실측 3건 + R0~R13, 소유자 sign-off Q1~Q7 → M-026 design 개설 (0a7da7b0)
- docs(planning): 워크벤치 concept 정정 — 접속 위치 무가정 (W6 · W7) (179b3ea7)
- chore(session): 123차 handoff — 두 수리 코드만 흡수 · 전량 게이트 green 반영 (63c2829c)
- docs(planning): 계획·진척 워크벤치 concept 종결 (W1~W5) + 하네스 중립 지시로 M-022 안 B 정정 → M-025 개설 (01f82984)
- docs(planning): html-plan 개념 흡수 concept 종결 — 주장·결정 계약(A) + 검토 브리지(B), 소유자 결정 D1~D5 → M-023 개설 (40e63779)
- chore(session): 121차 handoff 상태 정합 — push 완료 사실 반영 (main-003) (9da03e62)
- chore(session): 120차 세션 §1 기준선 갱신 + Windows 전량 게이트 52건 격차 등록(main-003) · baselines 롤오프 1건 · state.json 갱신 (3f03e903)
- chore(session): 120차 세션 — minimax-code 채널 재적용(v1.21.0 플러그인 sync + 글로벌 MCP 등록, main-001) · 게이트 러너 Windows 결함 수리 기록(main-002) · handoff · state.json 갱신 (f4ecc8e7)
- chore(session): 119차 세션 — 변경 없음: v1.21.0 발행 뒤 기준선 재측정(doctor behind=[] · 전량 게이트 309×2 green) · handoff §1 · §5 · baselines 롤오프 1건 · state.json 갱신 (8ea73719)
- chore(session): 118차 세션 — 소유자 결정 3건 반영: G4 · G5 선언(main-006, roadmap M-001~M-007 goals) · main · 태그 삭제 차단(main-007) · 매트릭스 기록 요구 안 함(기록) · handoff · state.json 갱신 (8f621453)
- chore(session): worktree 합류 반영 — feat/auto-20261019-a0afcf36 2건 close (be5e6da8)
- Merge branch 'feat/auto-20261019-a0afcf36' (1b1f7519)
- chore(session): 118차 세션 — main-004 close (goal coverage provenance) · G4 · G5 선언안 §5 · handoff · state.json 갱신 (6ca14604)
- chore(session): 118차 세션 — main-003 close (memory_lint T1a 은퇴 · T1c/T1d 재작성) · handoff · state.json 갱신 (6050e4e3)
- chore(session): 118차 세션 종료 — main-001 · 002 close (harvest v1.20.0 · memory_lint T1b, 미발행) · handoff · baselines 이관 · state.json 갱신 (4c39e752)
- chore(session): 117차 세션 종료 — main-003 · 008 · 009 close (verifier 실사용 · §2.8 minimax · apply 보고 수리, 미발행) · handoff · state.json 갱신 (06abaaf0)
- docs(release): §2.8 에 minimax-code 재적용 · 확인 절차 보강 (main-008) (2ef4682f)
- chore(session): main-003 close — verifier subagent 실제 로드 실측 (v1.20.1 발행 task 3/3 PASS) (bfd4e375)
- chore(session): 세션 종료 — main-006 close (handoff 제목 동기화 수리, 미발행) · handoff · state.json 갱신 (56ce4fd4)
- chore(session): 116차 세션 종료 — 플레이북 검토 · A1~A3 · 진입점 다이어트 · v1.20.0 발행 · handoff · state.json 갱신 (c166c6ad)
- docs(standard): 진입점 규칙 블록 압축 — 3,635B → 2,740B, 근거는 정본 본문으로 (진입점 다이어트 1) (062c4d64)
- docs(entry): CLAUDE.md 다이어트 — 12,184B → 7,733B (생성 규칙 블록은 바이트 동일) (55f9bb66)
- docs(planning): Anthropic "The AI-native SDLC playbook" 조사 정리 + 워크플로우 적용 검토 (7335cd97)
- chore(session): worktree 합류 반영 — feat/auto-20261002-4a5d394c 3건 close (c1a01964)
- Merge pull request #30 from ykylee/feat/auto-20261002-4a5d394c (a1f2ed68)
- refactor(test): 관찰 전용 session-start 를 공용 헬퍼로 — 재발을 막는다 (e98bc3a6)
- docs(plugin): MiniMax manifest 가 mcpServers 를 못 받는 이유를 정정한다 (b28bac31)
- chore(session): handoff §5 를 부류별로 되돌리고 후속 task 등록 (f706d2d0)
- chore(session): 세션 종료 — main-009 계열 2건 close · handoff §5 · state.json 재생성 (c2af79d9)
- chore(session): 115차 세션 종료 — macOS v1.19.0 §2.8 재적용 · 고유 커밋 없는 worktree/브랜치 정리 · 브랜치 메모리 3개 아카이브 (1ac26b0b)
- chore(session): 114차 세션 종료 — main-008 close (v1.19.0 발행) · main-006 · 007 Windows 실측 대기 · handoff · state.json 갱신 (309c9ddf)
- chore(session): 113차 세션 종료 — main-004 · 005 close (worktree 합류 반영 · v1.18.0 발행) · handoff · state.json 갱신 (11fe1e6f)
- chore(session): 112차 세션 종료 — main-001 · 002 close (worktree 모 브랜치 이어받기 · v1.17.0 발행) · main-003 등록 · handoff · state.json 갱신 (c44c09bf)
- dolt remote info (1534f260)
- chore(memory): 합류한 claude/exciting-ardinghelli-a0680d 브랜치 메모리 아카이브 · main handoff 포인터 갱신 (3c31ebb0)
- chore(memory): 종료된 claude/session-start-e6eb83 브랜치 메모리 아카이브 · main handoff 포인터 갱신 (84761318)
- chore(memory): main-012 close — 110차 worktree 수리(6118db3d)로 해소 · main handoff 에 worktree 합류 포인터 (1badb8bc)
- test(branch-memory): 슬래시 브랜치 task 수집이 형제 공유 디렉터리를 오인하지 않음을 잰다 (main-012 완료 기준 4) (b963f22c)
- merge: main(8ccd6db8·d89694b7) 을 claude/session-start-e6eb83 에 병합 (4eb71c93)
- chore(session): 110차 세션 종료 — claude-session-start-e6eb83-002 close (worktree 자동 seed) · §2.8 재적용 · handoff · state.json 갱신 (430999f4)
- docs(memory): macOS Codex v1.16.0 적용·신뢰·재시작 검증 반영 (d89694b7)
- docs(memory): minimax-code 배포본 채취 완료 — M-022 철회 · main-001 갱신 · glob 결함 2건 등록 (8ccd6db8)
- chore(session): 109차 세션 종료 — main-009 · 010 · 011 close (Codex hook 출력 수리 · v1.16.0 발행) · handoff · state.json 갱신 (6545f13a)
- chore(session): 108차 세션 종료 — main-008 close (Codex compact 중계 hook) · main-009 등록 · handoff · state.json 갱신 (bdfe4b31)
- chore(session): 107차 세션 종료 — compact 중계 M-018~M-021 완주 · v1.15.0 발행 · handoff · state.json 갱신 (8378809e)
- chore(memory): 107차 — compact 중계 M-021 close (main-006) · handoff 기준선 · state.json 재생성 (6067f865)
- chore(session): 106차 세션 종료 — main-002 close · main-001 minimax 형식 조사 기록 · handoff · state.json 갱신 (6b8d11e8)
- chore(state): 105차 state.json 재생성 — active/main/ 기준선에 minimax-code 갭 반영 (7b85854b)
- docs(memory): 105차 마감 — minimax-code 플러그인 채널 갭 등록 (M-007/WBS-7.4) (38cb7208)
- test(mcp): roundtrip 에 --literal-command — emit 된 launcher 를 치환 없이 PATH 에서 해석해 spawn (08-25-main-017 기준 2 실측 칸) (19b04e0a)
- docs(memory): close Windows wk PATH session (ed5b2ba9)
- chore(session): 101차 세션 종료 — handoff · state.json 갱신 (main-011 · 012) (29f92437)
- chore(session): 100차 세션 종료 — handoff · state.json 갱신 (main-010) (3eb769dc)
- chore(memory): 96차 세션 종료 — main-016 발행 기록 정리 + plugin_enabled 4채널 (09-28-main-018) (f8f40e99)
- chore(memory): 95차 세션 종료 — plugin_enabled 절 신설 뒤 게이트 기록 + macOS 전량 게이트 첫 실측 (09-28-main-017) (569f858c)
- chore(memory): 94차 세션 종료 — macOS 호스트 동기화 + v1.13.0 채널 재적용 + worktree 4개 정리 (09-23-main-017) (ab7bf648)
- refactor(release)!: v1.12.0 은퇴 shim 2종 제거 — verify_required_ci · REQUIRED_CI_WORKFLOWS (09-28-main-015) (2f3affc5)
- chore(memory): 방치된 worktree 잔재 정리 — 원격 브랜치 3 삭제 + clear-field memory 아카이브 (09-23-main-017) (46ce9f9f)
- docs(claude-md): 운영 절을 docs/LOCAL_GATE.md 로 이관 — CLAUDE.md 19.6KB → 11.3KB (M-017/WBS-17.4) (e1ef118b)
- docs(design): ADR-029 세션 시작 컨텍스트 예산 accepted + core 스펙 → M-017 개설 (751346a3)
- docs(planning): M-015 requirements sign-off (Q1~Q5 권고안) → M-016 design 개설 (e9a4b3c0)
- chore(memory): 92차 세션 종료 — main-009 · 015 · 016 반영 (44e0ff24)
- chore(memory): handoff §5 작업 후보에서 닫힌 main-015 · main-016 을 걷음 (70b13c19)
- chore(memory): 92차 세션 종료 — main-008 반영 (러너·CLI 검사 fixture·네트워크 제거) (7339bae5)
- perf(checks): 러너·CLI 검사의 무거운 fixture 와 네트워크 호출 제거 (09-28-main-008) (bf1417d5)
- chore(memory): 92차 세션 종료 — release 계열 검사 mypy 반복 제거 (main-007) (8648dfc6)
- perf(checks): release 계열 검사의 검사 내 mypy 반복 제거 (09-28-main-007) (5e0d0043)
- chore(memory): 91차 push 게이트 red 1건을 main-005 로 등록 (e6adb0df)
- chore(memory): 91차 세션 종료 — M-014 ① 안 구현 완료 (main-003 · main-004) (b73d9460)
- docs(gate): LPT·jobs 실측 결과 기록 + main-003·004 close (44695add)
- perf(gate): 병렬 구간 LPT 제출 + --jobs auto=코어 수, wiki_score 도구 실행 3→2회 (5b96ebb6)
- chore(memory): 90차 세션 종료 — M-014 concept 종결(① 안) · 3.14 환경 복구 · PURPOSE.md 개정 (dbf0287f)
- chore(memory): 89차 세션 종료 — CI 폐지 뒷정리 · push 게이트 · force 차단 hook 수리 (455d27c0)
- chore(memory): main-021 실측 종료 + main-019 범위를 로컬 게이트 처리량으로 (69a4648c)
- test(doctor): symlink 홈에서 경로 대조가 갈리던 검사 수리 (09-25-main-001) (b15d1dfe)
- refactor(release)!: mypy CI cross-verify 인터페이스 은퇴 (main-001) (53a3e152)
- ci!: GitHub Actions 테스트 workflow 폐지 — 발행 게이트 근거를 로컬 게이트 통과 기록으로 (main-022) (534e3a8d)
- perf(tests): check_root_anchor_audit 의 저장소 감사를 프로세스당 1회로 (main-020) (305d12a8)
- chore(memory): 87차 세션 종료 — 평가·로드맵 개편 반영 (0a253e83)
- docs(planning): 워크플로우 평가 + 도출 이슈 등록 + 로드맵 M-013·M-014 개설 (07ccab06)
- chore(memory): 87차 세션 종료 — main-010·main-011 close (f3c1d00e)
- chore(memory): 86차 세션 종료 — task 8건 close + v1.11.0 발행 + 승격 5건 (9a651225)
- chore(memory): main-008 승격 + 상한에 붙어 있던 검사에 CHECK_TIMEOUT_S (86차 최종) (f4504818)
- chore(memory): main-006·main-007 승격 — 86차 세션 최종 (entry 27 → 29) (709eb23c)
- chore(memory): 86차 세션 종료 마무리 — main-005 승격 + 기준선 정정 (3a92df61)
- chore(memory): 86차 세션 종료 — 판정이 아무것도 재지 않던 결함족 3건 (c3a4b39c)
- chore(memory): 85차 세션 종료 — memory_index 7건 승격 (749726ad)
- chore(memory): main-007 완료 기준 4 실측 — CI 가 전수 측정을 돈다 (2eb0f44c)
- chore(memory): 84차 세션 종료 — v1.10.0 발행 + 결함 6건 + 전량 시간 -38% (780f7b9b)
- perf(tests): 저장소 write 감시를 러너에 흡수 — 벽시계 221s → 138s (main-008) (709c792d)
- chore(memory): main-006 task 기록 — 앞 커밋이 가리키던 task 가 없었다 (8923dcfc)
- chore(memory): 84차 세션 종료 — v1.10.0 발행 + 결함 5건 전부 close (005e2051)
- chore(memory): main-005 close 기록 — 로컬 green 과 CI green 이 다른 경로였다 (b87770a6)
- chore(memory): main-004 close 기록 — 84차에 연 4건 전부 닫힘 (9b7ab66e)
- chore(memory): main-002 close 기록 — 84차에 연 3건 전부 닫힘 (3b1a88f6)
- chore(memory): main-003 close 기록 — 84차 누적 3건 close (be4c4968)
- chore(memory): main-001 close — 3개월 만의 첫 실제 게시를 실증으로 닫는다 (7c5601ca)
- chore(memory): 84차 세션 종료 — v1.10.0 발행 + 채널 재적용 + 절차가 드러낸 결함 3건 (ff55d8cc)
- chore(backlog): consumer-metrics-digest 만성 red task 등록 (main-001) (9056b21e)
- chore(memory): push 후 CI 실측 기록 + 83차 세션 최종 (main-009) (6ec86091)
- chore(memory): push 후 CI 실측 기록 — smoke 4셀이 선언대로 떴다 (main-008) (5990b96c)
- chore(memory): 82차 세션 종료 — main-006 · main-007 close + CI 실측 기록 (37d4d82e)
- chore(backlog): 해석기별로 갈리는 경고를 게이트 신호로 올릴지 task 등록 (main-007) (4a6079f0)
- chore(memory): push 후 CI 실측 기록 — smoke 4셀이 선언대로 떴다 (main-006) (a91549ba)
- chore(backlog): 검사를 CI 인터프리터로도 돌리는 축 task 등록 (main-006) (bb14bb93)
- chore(memory): 81차 세션 종료 — "범위가 조용히 좁으면 그 밖이 갈라진다" 4건 close (07ad98f9)
- chore(backlog): Python 문법 호환 축 task 등록 (main-005) (d4550ec3)
- chore(backlog): smoke 수 손 사본 task 등록 — 게이트가 8곳 중 2곳만 덮는다 (main-004) (fa4b1cb4)
- chore(memory): 80차 세션 종료 — 형제 파생물과 "재고 있던 사본" close-out (f8ab8ac8)
- docs(doctor): 노출 한 칸 첫 실측 — 그리고 캐시 사본은 읽히지 않는다 (main-005, -006) (d9102692)
- chore(memory): 79차 세션 종료 — 이 호스트 채널 5주 낡음 + 포크 병합 close-out (5354ea76)
- chore(env): 이 호스트 채널 v1.9.4 재적용 + CLAUDE.md 포크 병합 (main-002, -003) (6dd4c681)
- docs(sessions): 77차 세션 후반 기록 — 발행과 "성공했는데 틀린" 명령 (7a328527)
- docs(install): §7.0.2 가 존재하지 않는 맨 marketplace 명령을 적고 있었다 (0bcd757e)
- test(mcp): emit 산출물 전수를 win32 로 강제해 훑는 판정 — 수리를 지킬 자리가 비어 있었다 (3ae7bd04)
- docs(sessions): 77차 세션 기록 — 오탐인 줄 알았던 지표가 결함이었다 (7c298998)
- chore(memory): 76차 세션 종료 — 예제 산출물 드리프트에서 생성기 결함 2건을 파내 닫고 사본 1건·문서 오기 1건 정리 (fb9a6184)
- docs(installation): §7.0.2 grok 복구 열이 registry id 를 주는 것처럼 읽히던 것을 고친다 (14422cc2)
- chore(memory): 75차 세션 종료 — 손질 두 자리를 파생·판정으로 닫고 v1.9.2 발행·재적용 (0083eaaa)
- chore(memory): 74차 세션 종료 — 잦던 불일치 보고를 도구 결함으로 확정·수리·발행·적용 (2e57ad45)
- chore(memory): 72차 세션 종료 — 손 목록·리터럴·주장을 파생으로 전환 5건 + v1.8.1 발행 (0453dabf)
- chore(memory): 전역 wk 1.8.0 재설치 + 새 탐침이 패키징 결함 적발 (main-001 등록) (bfd25c15)
- chore(memory): 71차 — v1.8.0 발행 준비 완료 + 등급 전수 재평가 (main-005 in_progress) (6c495e61)
- chore(memory): 66차 세션 종료 — 관찰 축 2건 정리 + meta-watch 선언 보급 완주 (task 4건 close) (f879150a)
- chore(memory): 64차 세션 종료 — TDAD 축 M-008~M-012 완주 + v1.7.0 발행 (1f67f8e0)
- chore(roadmap): M-012 close — v1.7.0 발행 사이클 종결 (main-010·011 done) (818e199d)
- chore(roadmap): M-012 [release] 선언 + main-009 등록 (mcp 2.1.1 사건) (3669668b)
- chore(roadmap): M-011 close — meta-watch 구현 축 완결 (main-008 done) (9c41b488)
- docs(planning): M-008 concept 검토 — 계층별 회귀 실행 계약 (소유자 선택지 3안) (bf7f8788)
- chore(memory): brave-valley-2538 브랜치 메모리 아카이브 + main-003 등록 ('자기 위치 오인' 결함족 사본 발견) (9faa9924)
- chore(memory): 62차 세션 종료 — Windows 플랫폼 결함 축 수리 + v1.6.0 발행 + 이 호스트 채널 정렬 (2329bbf2)
- chore(memory): main-021 close — v1.6.0 발행 사이클 종결 (CI 전 워크플로 green + 이 호스트 채널 재적용 drift 0) (377ef605)
- chore(memory): main-004 close 기준 확정 — 격리 후 완료 run 33건에서 mypy 게이트 실패 0 (62차 소유자 결정) (de0f8307)
- chore(memory): 60차 세션 종료 — ADR-027 로드맵 층 완결 + v1.5.0 발행 (61차 병합 + main 생성물 치유) (6ecdeaa2)
- chore(memory): 61차 세션 종료 — Windows 플랫폼 결함 축 착수 (Oh My Pi) (3866c188)
- docs(work_logs): 2026-08-25 세션 기록 — 원격 동기화 + 플러그인 설치 검증(발견 3건) (b00b4a18)
- chore(memory): 60차 — M-006 close, v1.5.0 발행·재적용 완료, 로드맵 ADR-027 축 완결 (M-001~M-006 전부 done) (ff0ac3cc)
- chore(memory): 60차 진행분 — ADR-027 로드맵 층 M-001~M-005 close + mypy flake 관찰 6차 + memory_index 승격 2건 (379913b9)
- chore(schemas): output sample contracts 재생성 — SessionStartOutput.roadmap_context 반영 (b6afe828)
- docs(adr): ADR-027 — 로드맵·마일스톤·WBS 층과 SDLC 온보딩 기본 (M-001) (881c2cec)
- chore(memory): 59차 세션 종료 — doctor pip 오탐 수리 + memory_index 저점 고착 3회째 (4e4e8963)
- chore(memory): 58차 세션 종료 — OKF 매니페스트 잔재 수리 + mypy flake 관찰 5차 (ef5418fe)
- chore(memory): 57차 세션 종료 — v1.4.0 발행 + 혼합 표기 축 완결 + mypy flake 원인 규명 (b35fe6cf)
- chore(harness): 자기 적용 산출물을 v1.4.0 으로 재적용 — 낡은 마커 5 → 0 (69e35a8b)
- refactor(memory)!: 레거시 task 라벨 마이그레이션 — 도구로, 파싱 동일성을 잠금장치로 (main-004) (64a5370f)
- docs(decision): 혼합 표기 결정 재료 — 실측이 질문을 다시 세웠다 (main-002, -003) (dd682224)
- chore(memory): 53차 세션 종료 — 탐침 7절 + installPath 선언 + 라벨 영어 전환 (201f5a8e)
- chore(memory): 51차 세션 종료 — v1.3.0 발행 + 관찰 축 실측 + 채널 파리티 (75e9275a)
- chore(memory): 51차 세션 종료 — v1.3.0 발행 + 관찰 축 3개 실측 (main-004~007) (17847a0d)
- refactor(wiki): L2 계약을 memory 파생 4종으로 좁힌다 (main-001) (51b14113)
- chore(memory): 48차 세션 종료 — 배포 축 gap 4개 전부 닫힘 + OKF 상호운용 실측 (9a837e73)
- chore(memory): 47차 세션 종료 — 플러그인 설치 + 배포 축 gap 1·2 해소 + 결함 3건 (d25ed659)
- docs(deploy): 채널별 재실행 계약 4채널 실측 (main-017, 컨셉 gap 2) (c952dd64)
- chore(memory): 46차 세션 종료 — main-016 wk doctor 착수·구현 지점 조사 완료 (구현 미착수) (b6b91b85)
- chore(memory): 45차 세션 종료 — 배포 멱등성 컨셉 문서 + gap 4 task 등록 (main-015) (c59a9ade)
- docs(distribution): 배포 채널×하네스 매트릭스 정리 (main-014) (0e29bdbc)
- Merge pull request #28 from ykylee/worktree/clear-field-f112 (59ad6d43)
- Merge main into worktree/clear-field-f112 — case 19 충돌 해소 (Grok 19 · pi 20 공존) (7571f40d)
- docs(release): 현재 package version 표기 동기화 1.1.8 → 1.2.0 (PR #26 대체) (120a83ea)
- docs(harness): 배포 정책 문서 흠 2건 수리 — §번호 중복 + 누락 타겟 6종 (main-012) (2f0fde65)
- docs(plugin): 정직화 — pi v0.84.2 가 MCP 미지원임을 명시 (main-012) (ce595693)
- Merge pull request #27 from ykylee/worktree/brave-valley-2538 (ee1506c2)
- docs(memory): 조건부 1축 생략 기각 — 판단 기록 + 재론 방지 (main-004) (d1e0ef99)
- docs(claude-md): 실행 기본값을 .venv 전제로 — PEP 668 + 의존성 오탐 함정 봉인 (main-019) (115602a7)
- chore(memory): 44차 세션 종료 — task SSOT 3단계 완료, main-008 close (f0142542)
- Merge branch 'feat/task-label-registry' (207a6d1c)
- chore(memory): 43차 세션 종료 — task SSOT 2단계 close-out + 내 검사가 만든 오염 수리 (f3ae323a)
- Merge branch 'feat/task-ssot-writer' (6f2cc57e)
- chore(memory): 42차 세션 종료 — task SSOT 1단계 close-out (4eadb497)
- Merge branch 'feat/task-ssot-structured' (c26ac00a)
- chore(memory): 41차 세션 종료 — handoff 롤오프 적용 (26,582 → 10,789 tok, −59%) (15caeba7)
- Merge branch 'perf/handoff-baseline-rolloff' (b04428d6)
- chore(memory): 40차 세션 종료 — 영어화 3단계 close-out + 남은 축을 구조 작업으로 정리 (e6a3f402)
- Merge branch 'docs/english-entrypoints' (505e5d5d)
- docs(i18n): stage 3 완료 — plugin_payload 소비자 문안 + 검출기 9곳 동반 이동 (f8d2bce8)
- docs(i18n): stage 3 — bootstrap_lib/renderers.py 산문 영어화 + 경계 확정 (4eb2cd79)
- docs(i18n): stage 3 — harnesses/renderers.py 템플릿 전부 영어화 (docstring 제외) (6d2c1be3)
- docs(i18n): stage 3 — minimax/codex/claude-code/aider/goose/custom/pi-dev 템플릿 영어화 (8cc96b26)
- docs(i18n): stage 3 진행 중 — 공통 블록·gemini·antigravity 템플릿 영어화 (미완) (4054dccc)
- docs(i18n): 스킬 원본 13개를 영어로 (stage 2/3) — 16,253 → 12,437 tok (−23%) (825478bc)
- docs(i18n): 진입점 규칙 블록을 영어로 — 정본 §1·§3·§8·§11 부터 (stage 1/3) (194df08e)
- chore(memory): 39차 세션 종료 — main-003 close-out + 문서 개편 축 등록 (b594d87b)
- Merge branch 'perf/changed-selection' (58d6fd88)
- chore(memory): --changed 브랜치 close-out + 선언된 검사 수 255→256 (f7266118)
- chore(memory): 38차 세션 종료 — main-009 close-out + 아카이브 + 후속 2건 등록 (d4149839)
- Merge branch 'perf/heavy-check-runtime' (17c8ec13)
- perf(checks): 무거운 4개가 같은 계산을 반복하고 있었다 — 전량 벽시계 −21% (300a076b)
- chore(memory)+docs: 37차 세션 종료 — 전량 검사를 게이트로 되돌리고, 다음 축을 실측으로 확정 (e32dc75a)
- docs(release): PyPI 발행 안 함 확정 — 배포는 GitHub Releases 하나 (소유자 최종 결정) (e8dadf65)
- chore(memory): 37차 세션 handoff — 브랜치 정리 마감 + case 7 위양성 기록 (b2dcbe1f)
- chore(memory)+fix(check): 브랜치 정리 마감 — fix/archive-history-integrity 아카이브 + case 7 위양성 수리 (8a56e964)
- chore(memory): 36차 세션 handoff (PR #25 병합 — 브랜치 메모리 생애주기) (f8c3321b)
- Merge pull request #25 from ykylee/fix/archive-history-integrity (20fb1a80)
- chore(memory): 브랜치 메모리 아카이브 + 미완료 task main 이월 (47469ae1)
- chore(memory): 35차 세션 handoff (PR #24 병합 — 브랜치 메모리 네임스페이스 가드) (9099363e)
- Merge pull request #24 from ykylee/fix/branch-memory-namespace-guard (4ad47985)
- merge: main 의 mypy 증거 수집 수리 반영 (f860ee74)
- chore(memory): mavis 기대치 task 를 done 으로 (이 PR 에서 닫음) (b5c39092)
- chore(memory): 종료된 브랜치 메모리 아카이브 + 34차 세션 handoff (PR #23 병합) (ba9097b8)
- merge: Codex·Claude Code native plugin 배포 + 정합 보완 10건 (PR #23) (5d85028d)
- Merge branch 'main' into feat/plugin-harness-distribution (32c31de6)
- docs(memory): record plugin distribution PR handoff (bb7847ab)
- docs(memory): 33차 세션 종료 — PyPI 발행 준비 (handoff + state + 세션 기록) (215672c6)
- docs(policy): TestPyPI 1회 한정 허용 — 채널 정책 행 + 각주 1 (TASK-2026-08-13-main-008) (6ddb4b3d)
- docs(planning): TestPyPI 리허설 — 업로드 직전까지 검증 완료, 업로드는 blocked (TASK-2026-08-13-main-008) (2ce88cdd)
- docs(planning): PyPI 발행 정책 검토 — 기술 준비 완료, 공개 전 수리 3건 선행 (TASK-2026-08-13-main-006) (5655df86)
- docs(backlog): TASK-004 mypy flake 관찰 1차 — 재발 0건이나 표본 부족으로 close 불가 (cfd160cf)
- release(v1.2.0-beta): post-apply 정합 + 사본 동기화 결함 수리 + 메모리 종결 (6f70cf5f)
- release(v1.2.0-beta): 파생물 선재생성 + 노트 + dist (7c806191)
- chore(backlog): CI native 셀 mypy 게이트 flake 관찰 등록 (TASK-2026-08-13-main-004) (523018ca)
- docs(plugin): P5 실측 게이트 + 채널 전환 판정 — 전환 계획 완료 (TASK-2026-08-12-main-018) (2de04e84)
- docs(planning): 플러그인 배포 전환 계획 확정 — P1~P5 로드맵 + WBS 등록 (TASK-2026-08-12-main-013) (1806d751)
- docs(planning): 멀티 하네스 공유 플러그인 검토 — 공유 payload + 얇은 manifest 권고 (TASK-2026-08-12-main-012) (ab40a903)
- docs(planning): 플러그인 형태 재구성·배포 검토 — 채택 권고, 14번째 파생본 원칙 (TASK-2026-08-12-main-011) (e93e3b2e)
- release(v1.1.8-beta): post-apply 정합 + 메모리 종결 — 발행 완료, 2nd cycle 시계 시작 (f7209f4a)
- release(v1.1.8-beta): 파생물 선재생성 + 노트 + dist (79e2f515)
- docs(backlog): TASK-2026-08-12-main-010 등록 — v1.1.8-beta 발행 (6f053a00)
- refactor(namespace): bootstrap_lib → workflow_kit.bootstrap_lib (2단계) — PyPI 이동 단계 완결 (TASK-2026-08-12-main-007) (bcd2c7d5)
- refactor(namespace): tools → workflow_kit.tools 물리 이동 (1st cycle) — PyPI blocker 절반 해소 (TASK-2026-08-12-main-006) (74889f39)
- release(v1.1.7-beta): post-apply 정합 — 파이프라인 산출물 + 재실행이 잡은 3건 + 메모리 종결 (21b3e3c7)
- release(v1.1.7-beta): docs/RELEASE.md version stamp 갱신 — CI 가 잡은 누락 (e3e6df24)
- release(v1.1.7-beta): 파생물 선재생성 + 노트 + dist — bump 후 stamp/fixtures/samples 일괄 (2d228777)
- docs(backlog): TASK-2026-08-12-main-002 등록 — v1.1.7-beta 발행 (552e6f9e)
- docs(memory): cross-host 두 번째 호스트 = MacBook 확정 (시점 추후) 기록 (9a309760)
- docs(backlog): 6차 세션 리뷰 결함 후속 task 6건 등록 (TASK-2026-08-11-main-023~028) (add0e631)
- docs(memory): 5차 세션 종료 기록 — darwin 검증에서 하네스 파생본 통일까지 (4929aa5a)
- docs(memory): 5차 세션 시작 — darwin homelab 검증 1챕터 (macOS 1패스 245/249, 4 FAIL 발견) (45a6e1b0)
- docs(memory): session close — 4차 세션 기록 + 기준선 최종 정리 (backlog 16건 종결) (6678eafe)
- docs(reports): 학습회 독립화 — 보고서에서 학습회·발표 서술 제거 (TASK-2026-08-11-main-016 검토 4회전) (452d1a7f)
- docs(reports): 본문 폭 780→920px + 부제 축약 (TASK-2026-08-11-main-016 후속) (34ad9458)
- docs(reports): 문체·어휘 정리 — 비일상 어휘 12종 교체/풀이 (TASK-2026-08-11-main-016 검토 3회전) (dd227cf8)
- docs(memory): session close — TASK-016 검토 2회전 반영 + 세션 종결 기록 (fe085b91)
- docs(reports): 수치 전수 검토 반영 — 날조·과장 4건 정정 (TASK-2026-08-11-main-016 후속) (e5ba9394)
- docs(reports): 기간 날조 정정 — '14개월' → 실측 4개월 (최초 커밋 2026-04-18) (77e6c315)
- docs(reports): 검토 반영 — 실명 오류 1건 + 표3 전재 누락 1행 + 표현 보정 (TASK-2026-08-11-main-016 후속) (66db9fbf)
- docs(reports): mkdocs strict red 해소 — docs 트리 밖 링크를 code span 으로 (TASK-2026-08-11-main-016 후속) (73d673ac)
- docs(reports): 학습회 자료 → 사내 기술보고서 논문 양식 문서 (TASK-2026-08-11-main-016) + TIMEOUT flake backlog 등록 (TASK-015) (8254064f)
- docs(memory): session close — 2026-08-11 backlog 14건 종결 baseline 확정 (afe1dc6a)
- docs(memory): branch protection 보류 결정 (소유자) — 후보 축에서 제거 (d423d022)
- docs(memory): handoff §4 cap(10) 회복 — CI smoke handoff_bloat red 해소 (TASK-2026-08-11-main-014 후속) (6b550a9e)
- docs(memory): 후속 backlog 3건 등록 + origin/mooneye 삭제 close (TASK-2026-08-11-main-012) (a03de4dc)
- docs(memory): 2026-08-11 세션 기록에 후속 TASK-009~011 반영 (대형 파일 분할 완결) (f503cff8)
- refactor(cli): workflow_kit_cli.py 안전 부분 분할 — 2095→583줄 + 모듈 5개 (TASK-2026-08-11-main-011) (487d4d9b)
- refactor(dashboard): dashboard_data.py 안전 부분 분할 — 2488→1526줄 + 모듈 3개 (TASK-2026-08-11-main-010) (57583701)
- chore(docs): presentations 파생 바이너리 트리 제거 — 5.3MB (TASK-2026-08-11-main-009) (90dab220)
- refactor(release): release_pipeline.py 안전 부분 분할 — 3908→3174줄 + 모듈 4개 (TASK-2026-08-11-main-007) (4d311b54)
- refactor(tests): check_cache_* 13개를 check_cache.py 1개로 통합 — smoke 260→248 (TASK-2026-08-11-main-004) (286f5439)
- chore(memory): ai-workflow 아카이브 185파일 정리 — gemini + 2026-07-22 freeze (TASK-2026-08-11-main-003) (3f04bb7e)
- refactor(tests): mypy strict 부분집합 검사 8개 제거 — smoke 268→260 (TASK-2026-08-11-main-001) (beaaa718)
- docs(memory): 2026-08-10 3차 세션 기록 + handoff/state 동기 (TASK-016~019) (eb3b0a28)
- perf(tests): smoke 병렬화 + 저장소를 rename 하던 check 격리 (TASK-2026-08-10-main-018) (f4f7fc65)
- docs(memory): 2026-08-10 2차 세션 close — 세션 기록 + handoff/state 최종 동기 (TASK-008~015) (bdad1a10)
- chore(backlog): TASK-2026-08-10-main-015 등록 — v1.1.6-beta 발행 착수 (87d80ae9)
- docs(memory): TASK-2026-08-10-main-003 등록 — v1.1.4-beta cmd_release 발행 (3236bca0)
- docs(phase13): P0-2 close — telemetry 4 source 수렴 + 문서 정정 (87d0ea26)
- docs(memory): 2026-08-09 세션 close — 세션 기록 + state/handoff 최종 동기 (49a2b541)
- docs(memory): 정합성 정리 — backlog status/링크 + task 상태 + state/handoff 동기 (4e31d8ce)
- docs(memory): session close — v1.1.1-beta + state/handoff final sync (c0224c66)
- docs(memory): §2.68 cycle 완전 close — TASK-012 갈래2 trust 채택 (5fc1b6ef)
- docs(memory): §2.68 cycle close + baseline 통일 (838b12f) (4e85babb)
- chore(mcp): §2.68 mavis 글로벌 mcp.json 표준 register attach (이전 축) (27010a51)
- chore(red): 사전 존재 red 2건 정리 (회귀 정합 회복) (a845c318)
- docs(memory): 세션 close-out — 다중 워크스페이스 오케스트레이션 + 사전 red 2건 정리 (2d2199fc)
- docs(memory): handoff L12 baseline hash 명시 (§2.67 c63b54e) (9ef3cd8d)
- chore(mcp): §2.67 — mavis attach 안 붙음 진단, 1차 출처 보강 (§6.5.2) (c63b54ec)
- docs(presentation): 발표자료 32번 장표 1행 5컬럼 레이아웃 개편 및 37번 장표 카드 테마 통일 (d9b87d4d)
- chore(memory): Update session handoff, state & backlog for TASK-2026-08-06-main-003 (6fe76927)
- style(slide): Fix vertical content alignment and lock header baselines across 38 slides (8479cefd)
- chore(backlog): Add TASK-2026-08-06-main-002 to daily backlog (05cf9551)
- chore(memory): Update session handoff & state for TASK-2026-08-06-main-002 (3dc72311)
- docs: Add master HTML deck & update AI Agent Onboarding presentation design v2.4 (3f3aaaa3)
- docs(presentation): 학습회 발표 설계 v2 — 인과 사슬 재설계 + 세션 종료 memory 갱신 (c0acc70f)
- docs(memory): 세션 종료 — §2.59~§2.66 세션 기록 + 다음 시작 포인트 정리 (1cafb876)
- docs(memory): 기준선을 0f53458 로 갱신 (트리거된 CI 5종 green 실측) (76db79c6)
- refactor(mcp)!: transport_ready 를 wire 에서 제거했다 (§6.2 완료, §2.66) (0f534584)
- docs(memory): 기준선을 0ceca6b 로 갱신 (§2.62 커밋의 트리거 3종 green 실측) (e6e4623e)
- refactor(mcp): 세 번째 사본을 접었다 — 이미 갈라져 있었다 (§2.62) (0ceca6b2)
- docs(memory): 기준선을 8e4dccb 로 갱신 (§2.61 커밋의 트리거 3종 green 실측) (2ffd4c98)
- refactor(mcp): grok 의 하드코딩된 MCP 블록을 정본으로 접었다 + TOML 키 결함 (§2.61) (8e4dccbb)
- docs(memory): 기준선을 6ebbd8b 로 갱신 (§2.60 커밋의 트리거 3종 green 실측) (efca8b66)
- docs(memory): 기준선을 33424fc 로 갱신 (커밋 2건 각각 트리거된 CI 3종 green 실측) (4bfbc20c)
- docs(memory): 기준선을 c58111d 로 갱신 (트리거된 CI 6종 전부 green 실측) (7d18f2fe)
- docs(memory): 기준선을 7b076f8 로 갱신 + okf-validate 가 새로 드러낸 2건 기록 (4ac03ba0)
- docs(memory): 기준선을 9efbd88 로 갱신 (트리거된 CI 4종 green 실측) (19df5d76)
- ci(smoke): 슬래시 브랜치를 밟는 실행이 우연이었다 — smoke 를 2셀로 (§2.56) (9efbd881)
- docs(memory): 기준선을 dda0825 로 갱신 (트리거된 CI 3종 green 실측) (96e58268)
- docs(memory): 기준선을 99eb05a 로 갱신 (트리거된 CI 3종 green 실측) (0b9f9336)
- docs(memory): 기준선을 710ccea 로 갱신 (트리거된 CI 3종 green 실측) (9764538c)
- docs(memory): 기준선을 5c8a85f 로 갱신 (CI 4종 green 실측) (a633167e)
- docs(memory): 기준선을 1b52b85 로 갱신 (CI 4종 green 실측) (ee6a8011)
- docs(memory): 기준선을 15ee104 로 갱신 (CI 3종 green 실측) (8fcb48b5)
- docs(memory): 기준선을 607b84c 로 갱신 (CI 4종 green 실측) (3b308ff9)
- docs(memory): 기준선을 2e13931 로 갱신 (CI 4종 green 실측) (3eb42e52)
- docs(memory): 기준선을 14cd792 로 갱신 (CI 4종 green 실측) (33cf72a4)
- docs(memory): 기준선을 72bfbe0 로 갱신 (CI 4종 green 실측) (5269a25c)
- docs(memory): 기준선을 4cfda75 로 갱신 (CI 6종 green + matrix 3셀 실측) (273d662d)
- docs(memory): 기준선을 ea1576c 로 갱신 (CI 4종 green 실측) (d42459c3)
- docs(memory): 기준선을 1f1881c 로 갱신 (핀 해제 후 2.0.0 실측) (d3ba60ae)
- docs(memory): 기준선을 7b1404b 로 갱신 (CI 4종 green 실측) (699f1482)
- docs(memory): 기준선을 71feef3 으로 갱신 (CI 실측 완료) (a19bcf4f)
- docs(memory): 기준선을 d14d5f4 로 갱신 (CI 3종 green 실측) (23874d1f)
- docs(memory): 미판정 2건을 근거를 찾아 done 으로 판정 (§2.39 후속) (0206ac3b)
- docs(memory): 기준선을 c54220f 로 갱신 + 미확인 CI 3건을 관측으로 닫음 (e06fd377)
- docs: §2.37 릴리스 노트 + 세션 close-out (TASK-2026-07-27-main-004) (c54220f2)
- docs(memory): 세션 close-out — TASK-2026-07-27-main-003 + 세션 기록 (2f20cb5b)
- docs(release): CI red 의 원인을 계측해 확정 — mypy 가 아니라 gh 였다 (§2.36) (dac83e37)
- docs(memory): 푸시 후 CI 결과 기록 + 관측성 결함 1건 추가 (e7a08bf6)
- docs(memory): 세션 close-out — TASK-2026-07-25-main-001 + 세션 파일 + state.json 재생성 (6fe79342)
- docs: 루트 pyproject 를 "uv init 잔여물" 로 규정한 것은 내 오독이었다 (db744f46)
- docs(memory): Pages 를 켜니 mkdocs 3층의 맨 아래가 열렸다 — deploy 첫 성공 (c9849a81)
- docs(memory): 세션 close-out — TASK-2026-07-23-main-001 + 세션 파일 + state.json 재생성 (03cbfb04)
- ci(mkdocs): deploy 가 OIDC 권한 없이 돌고 있었다 — build 를 고치니 드러났다 (5b6a2a70)
- ci(smoke): 선언만 하고 설치하지 않던 dev/release extra 를 설치 — 11건 중 7건 해소 (eab24ac7)
- ci(smoke): set -e 때문에 실패 요약 블록이 한 번도 실행된 적이 없었다 (c686544b)
- ci(smoke): 실패 상세를 로그와 아티팩트로 보존 — 안 보이니 40회 red 가 방치됐다 (101125db)
- docs(release): §3 의 tmpfs 귀인 정정 — 2회 관측으로 인과를 단정했다 (600f6e1b)
- docs(wiki): ponytail 개념 조사 + 채택 설계 — 진짜 없는 것 2가지만 (설계 기록) (2e3c00b3)
- docs(memory): 세션 close-out — TASK-2026-07-22-003 + 세션 파일 + state.json 재생성 (576a05fb)
- refactor(paths): memory 경로 조립 14곳을 정본 helper 로 — 같은 부류 전수 조사 (209/209) (0116661a)
- test(contract): writer ↔ reader 왕복 계약 8쌍 (전량 207/207) (02161a33)
- docs(memory): TASK-2026-07-22-002 후속 작업 close 표시 (d285077) (77b7ea65)
- docs: P0-1 mypy strict venv verify 완료 (Break Point #3 close-out) (277ceff6)
- docs(roadmap): §8 P0-2 + P1-1 완료 표기 (v0.15.21-beta) (35442d8a)
- docs(roadmap): Phase 12 close-out + Phase 13 follow-up 정의 + housekeeping (31f07f11)
- chore(session): handoff state.json — v0.15.15 release + follow-up + 누수 진단 완료 (3bff888e)
- chore(session): 누수 진단 종합 결과 state.json + session 파일 기록 (23d5ee17)
- refactor(release_pipeline): dead code 3건 제거 (out-of-scope 후속 정리) (5408c2c3)
- chore(docs): 단순 stamp 갱신 — 2026-07-09 → 2026-07-18 (d1000586)
- refactor(workflow_kit): Status enum + TypedDict _BM25Index 적용 (17c44dda)
- chore(session): 2026-07-17 세션 handoff — v0.15.1~v0.15.15 follow-up 종합 (733b44da)
- docs(retrospective): ADR-006 Wiki OKF compat frontmatter full review (30일 cycle close-out, accepted) (414b6de1)
- chore(scaffold): root-level standard-ai-workflow package scaffold (v0.1.0 placeholder) (eb62f379)
- docs(release): rename Phase 13 close-out summary file (50540633)
- docs(release): 작업 내역 정리 — v0.13.1/2/3 release note + Phase 13 v1.0 close-out summary (6036e8d1)
- chore(docs): doc-headers-update v0.13.0 (60 file 동기화) (ed18eeba)
- chore(release): Beta-v0.13.0 release note (Quality Dashboard) (7082dbd1)
- chore(release): README v0.13.0 header + auto-fix tooling (e0c1d333)
- chore(audit-follow-up): 2026-07-09 audit 후보 10건 일괄 해소 (P0 3 + P1 3 + P2 4) (c966ca26)
- audit-session 2026-07-09: 워크플로우 구성 점검 + 고도화 후보 10건 영구 기록 (62229818)
- chore(cross-platform): 절대경로를 ~/ 표기로 통일 (10 files) (3b224f4e)
- docs(architecture): MCP stdio-sdk promotion feasibility report (v0.11.24 review) (fce8eb99)
- docs(release): Beta-v0.11.23.md housekeeping — P3 완료 + 잔여 표 정정 (07343cdb)
- docs: resolve v0.5.x~v0.11.x documentation drift across 13 files (drift remediation) (4633d348)
- chore(release): Beta-v0.11.22 release note (작업내역 정리) (c0b49cfa)
- chore(release): Beta-v0.11.22 release note (작업내역 정리) (1248c36d)
- chore(release): Beta-v0.11.22 release note (작업내역 정리) (185a1f11)
- docs(adr): ADR-006 ADR-005 Memory Index implementation retrospective 자리 박기 (34fb07f9)
- chore(state): ADR-005 v0.11.22+ Phase 1 candidate memory cycle (0f109267)
- docs(adr): ADR-005 Memora-inspired Memory Index 추가 (v0.11.22+ Phase 1 계획) (468ec7da)
- docs: add Memora evaluation note (95d6ebaf)
- chore(samples): output_samples tool_version v0.11.19 → v0.11.20 housekeeping (c90b4374)
- chore(spec): robust-patcher SKILL.md status → stable + spec layer 동기화 (63c22c8a)
- chore(samples): output_samples tool_version v0.11.17 → v0.11.19 housekeeping (af6baaf7)
- chore(spec): 4 skill SKILL.md status → stable + skill catalog/beta_criteria 갱신 (cb32d6cb)
- chore(state): session 마무리 memory cycle (4c83ed90)
- chore(state): read_only_mcp_sdk + doc_sync 묶음 격상 memory cycle (f54d7468)
- chore(state): mcp_v1_server + release_status 묶음 격상 memory cycle (7cf8f472)
- chore(state): mypy strict 묶음 격상 memory cycle (508d92a8)
- chore(state): schema drift housekeeping memory cycle (e7956f93)
- chore(state): mypy strict output_contracts 격상 memory cycle (66087038)
- chore(state): R9 lint fix memory cycle (001552ac)
- chore(state): wiki cross-ref 보강 memory cycle (e7a673f1)
- docs(wiki): workflow 종료 단계 commit/memory 순서 정합 cross-ref (298704f9)
- chore(state): workflow 종료 단계 commit/memory 순서 정정 memory cycle (df3d802d)
- chore(state): sync v0.11.15 — drift fix (no release, no version bump) (06a77707)
- chore(state): sync v0.11.10 — drift fix (no release, no version bump) (3c509e1b)
- chore(state): sync v0.10.3 — wiki concepts 28/decisions 25/entities 13 + backlog 2026-06-24 (1cc2702c)
- chore(work_backlog): compactify v0.7.25~v0.7.32 in-flight 8 detail block (5310e2a8)
- docs: README + work_backlog v0.9.0 chapter 1 baseline 동기화 (6a90ddbf)
- docs: README.md + work_backlog.md v0.8.15 baseline 동기화 (811a73e5)
- test(v0.8.10-11): read-only MCP manifest assertion (spec §9 #6) + phishing 2 pre-existing fix (2df7f925)
- merge: sync v0.7.58 release from origin (611b87ec)
- chore(v0.8.4-5): mypy strict 단계적 격상 4-5단계 (phishing + cache) (d1c12cbe)
- chore(v0.8.1-3): mypy strict 단계적 격상 1-3단계 (url_validity + okf_*) (46fe01e8)
- chore(v0.8.6-7): mypy strict 단계적 격상 6-7단계 (dispatcher + commit_diff) (5ef95790)
- chore(v0.7.60-62): follow-up batch — dispatcher 28 + mkdocs strict + trend/digest (93ec0081)
- docs(okf): OKF_CONSUMER_QUICKSTART.md (5 section tutorial, ADR-025 code-side) (f941ea6b)
- wiki(adr-025): formal acceptance in v0.7.44 (1 ADR + 1 concept, 17 ADR accepted cumulative) (28ad5b3b)
- wiki(adr-025): OKF consumer quick-start tutorial draft (status: proposed, 75/75 entries) (14ba098e)
- wiki(adr-023+024): formal acceptance in v0.7.43 (2 ADRs + 2 concepts, 16 ADR accepted cumulative) (30ec2a5a)
- chore: version bump v0.7.41 -> v0.7.42 (ae510e0b)
- wiki(adr-023+024): formal documentation draft (phishing API + per-strategy cache, status: proposed, 73/73 entries) (62e5f693)
- wiki(adr-020+021+022): formal acceptance in v0.7.41 (3 ADRs + 3 concepts, 14 ADR accepted cumulative) (55bd1091)
- wiki(adr-021+022): formal documentation (LFU + PhishTank, status: proposed, 69/69 entries) (2cc7d6eb)
- wiki(adr-020+v-r13-impl): PoC draft (status: proposed, 65/65 entries) (ea01e423)
- docs(okf): consumer guide (write/validate/ingest OKF bundle) (a2f8f72f)
- wiki(adr-019+v-r13): formal acceptance in v0.7.38 (e17609ea)
- wiki-ingest: v0.7.38 follow-up log entry (cache_stats + V-R13 + per-page + lock timeout) (309f34d9)
- test(okf_export): tag-based pinning (v0.7.37, main, feature/x, 13/13 PASS) (6ee15558)
- wiki-ingest: ADR-019 V-R13 semantic URL verification + v-r13 concept page (5f4fe725)
- wiki-ingest: v0.7.37 follow-up log entry (5 ADR acceptance + 4 enhancement) (0993b12d)
- wiki-ingest: v0.7.37 5 ADR formal acceptance + release note + version bump (ef95ff7e)
- wiki-ingest: v0.7.36 ADR-012/013 formal acceptance + release note (9617d92c)
- wiki-ingest: ADR-013 V-R10 v2 cache + v-r10-online concept page (5652e1aa)
- wiki-ingest: v0.7.35 ADR-009/010/011 formal acceptance + release note (2efcb0b6)
- wiki-ingest: ADR-009 v-t1 formal adoption (proposed) + V-T1 concept page promote (8db18579)
- test(okf): 9/9 PASS (added 8 §4.1 conformance + 9 bundle directory layout) (d472d8e8)
- wiki-ingest: ADR-007/008 + V-T1 + sample OKF bundle (4 followups closed) (6b293862)
- wiki-ingest: ADR-006 okf-compat-frontmatter + workflow_kit/okf_export.py PoC (149d1ac5)
- wiki-ingest: okf-open-knowledge-format (1 concept page, primary source verified) (efc1ea3d)
- chore: ignore local tooling (.mavis/, .obsidian/) (95b1d2c4)
- wiki: AIDLC benchmark topic §9 v0.6.5 → v0.6.6 정정 (17 commit, ~3,800 line) (58f3ad2e)
- wiki: promote topics/aidlc-benchmark-analysis-2026-06-12 (draft → active) (9946d913)
- wiki-ingest: AIDLC benchmark analysis (1 topic page) (2916d494)
- lint-fix: phase-7-verification — L1 log entry append (a8fc1adc)
- lint-fix: phase-7-verification — 11 broken wikilink 일괄 fix (a5762e5f)
- wiki-ingest: phase-5-topics — 3 cross-cutting topic (R2 batch 4) (10bbbd03)
- wiki-ingest: phase-4-patterns-entities — 3 pattern + 12 entity (R2 batch 3, 15 page 한도 매칭) (d95681e1)
- wiki-ingest: phase-3-decisions — 4 ADR 신규 + 1 ADR extend (R2 batch 2) (1f605542)
- wiki-ingest: phase-2-concepts — 5 concept pages 신규 (R2 batch 1) (5d7db104)
- wiki-ingest: phase-1-scaffold (INGEST_GUIDE + index anchors + log) (cae89f19)
- self-dogfood: wiki organization — 5 page types with 6 entries + V-R9 fix (73fea00a)
- self-dogfood: apply wiki + memory workflow to own project (792fddcf)
- docs(v0.5.10-post): full documentation refresh + dev install guide (e927060c)
- docs: add release notes for v0.5.0-beta (4af1a6a1)
- chore: release v0.5.0-beta - Multi-agent orchestration and workflow intelligence (35bf8119)
- docs: update project status and session handoff for Phase 9 merge (48736c46)
- chore(docs): untrack dated backlog ignore and add existing backlog files (3d8c97d8)
- Bump version to v0.4.2-beta (46951e07)
- Phase 8: Complete core engine refactoring and MCP standardization (24e18e75)
- Phase 8: Stabilize CI by renaming mcp to mcp_servers and updating all references (dae17c1d)
- chore: finalize Phase 6/7 cleanup and update maturity matrix (c8ef6e03)
- docs: specify version in asset glob pattern to avoid over-uploading (7d6ed67e)
- docs: define versioning policy and update release note template (8b794655)
- docs: generalize release procedure for platform-agnostic distribution (6fdd5b61)
- docs: add formal release procedure to workflow_release_spec (8126ab06)
- Merge pull request #10 from ykylee/gemini/phase7 (93e675a3)
- refactor(workflow): separate source from runtime layer (96431f1b)
- chore(workflow): sync main layout and clean artifacts (19af8239)
- chore: remove temporary test artifacts from git tracking (bb3dbce1)
- docs(workflow): update work_backlog and session_handoff with final isolation status (d41025e8)
- chore(workflow): track state.json and update command paths (22d79424)
- Standardize workflow architecture with branch isolation and memory/ structure (6fa035f4)
- docs: Finalize work_backlog.md and state.json for the session (25aef2f5)
- docs: Update session handoff and work backlog with latest achievements (dd648c6e)
- docs: update session handoff and backlog for completion of path migration and antigravity transition (60b1ec06)
- Merge pull request #6 from ykylee/gemini/init (f5a71ad8)
- docs: update 0.3.2-beta release note with runtime script hotfix (07838982)
- docs: update operational documents for Phase 6 and cleanup backlog (b07131ac)
- Merge pull request #5 from ykylee/testing-improvement-build-session-summary-10089196219796924349 (db5ecddb)
- Merge pull request #4 from ykylee/fix-unused-import-typing-any-run-demo-workflow-325793006892402125 (8064cdb4)
- Merge pull request #3 from ykylee/optimize-docs-metadata-reading-711467596835134650 (7e110cd2)
- 🧪 [testing improvement] Add unit tests for build_session_summary (84370f87)
- chore: remove unused import Any from scripts/run_demo_workflow.py (4098061e)
- perf: optimize metadata reading by avoiding full file load (e98fe097)
- docs: re-organize release history with new template and SemVer v0.x.x (fbeffd5b)
- docs: standardize release note format and update Beta v3.0.2 (735514d4)
- docs: add release notes for v3.0.2-beta (Prototype V6) (ad2e27ff)
- docs: finalize Beta v2.2 milestones in handoff and state (30632844)
- release: beta-v2.1 - workflow-linter Beta and project-status-assessment skill implementation (028618da)
- release: beta-v2.0 - Official MCP SDK integration and priority tools (5a45203f)
- chore: streamline workflow harness for gemini-cli (a150a670)
- release: beta-v1.1 - dependency injection and sequential apply (6ff0a827)
- test: modernize core skill tests and regenerate schemas for beta-v1 (f77952f1)
- release: standard-ai-workflow beta-v1 - promote core skills and add quickstart (236fe4ea)
- docs: optimize templates for context efficiency and update bootstrap script to use templates (ab59837c)
- merge: integrate origin/opencode/workflow_test - add OpenCode harness support and skill beta criteria (e8717114)
- docs: TASK-003 complete - update repository assessment and gemini-cli harness config (ade7e1b4)
- chore: remove legacy codex config example (28b10303)
- chore: remove legacy ai-workflow content from previous version (15b7ec78)
- chore: apply v3 bundle to repository - profile/handoff/state.json 보존模式下 applied (e519e814)
- chore: prototype-v3 패키지 준비 - skill beta upgrade, release note 추가 (aa64b648)
- Merge pull request #2 from ykylee/codex/opencode-edit-reliability (9460ce77)
- Refine workflow planning and state tracking (7d91ea09)
- Clarify OpenCode oldString matching guidance (13a45e34)
- Enhance validation-plan result handling (247415f3)
- Add OpenCode edit reliability workflow (46231120)
- Dogfood codex workflow deployment and safe updates (84fb0cc7)
- Refine workflow state boundaries and write paths (b29292a7)
- Tighten orchestrator read boundaries (63bcda88)
- Prepare prototype-v2 pre-release workflow package (4281a768)
- Clarify opencode implementation worker role (5d7d874b)
- Document AGENTS entrypoint for opencode exports (e059c29e)
- Improve runner traces and stabilize export fixtures (c0bf7b7b)
- Prepare prototype-v1 pre-release workflow package (8808f6de)
- Harden read-only JSON-RPC error envelopes (109a6adb)
- Update roadmap for read-only MCP transport work (6ddaf9f4)
- Add read-only MCP transport contracts (d842607a)
- Sync documentation with current workflow contracts (ea5d2572)
- Promote read-only bundle contracts and generated schemas (a33f19bd)
- Start draft read-only MCP bundle (cb3e56c9)
- Refresh onboarding samples and validation docs (250ede05)
- Add open_git_client pilot assessment (a414c245)
- Add concrete pilot candidate examples (ae60c253)
- Align workflow contracts and add pilot planning docs (d380b85f)
- Clarify onboarding contract consumption by harnesses (26c203cb)
- Add sample contract schemas for workflow outputs (397d065f)
- Add structured workflow runner outputs and smoke CI (6ef3b570)
- Refine workflow kit skill and runner helpers (e5510a37)
- Expand workflow kit shared parsers (6aad4c46)
- Add workflow kit package foundations (81dd42ef)
- Add onboarding runner and quickstart link MCP (75f5b36b)
- Add output samples for skill and MCP prototypes (7e7d3b94)
- Refresh workflow kit roadmap status (f892dc06)
- Add bootstrap output samples and manifest metadata (22636f7e)
- Add validation and index planning skill prototypes (9cde277e)
- Add harness workflow overlays and global config guides (88858187)
- Add second workflow example project (91e477d7)
- Add workflow roadmap and integrated demo runner (a9442989)
- Add MCP prototypes and demo flow (41f68680)
- Add workflow skill specs and runnable prototypes (bf0db4da)
- Initialize standard AI workflow kit (ed714739)

### Fixed

- fix(hub): accept a proxy-rewritten Origin scheme only for same-origin fetches (fad70a78)
- fix(hub): accept the configured public origin behind a proxy, allow 8-char passwords (8f0aa8f7)
- fix(hub): port Go setup confirm and wiki reads, prepare 3.2.2 prerelease (0166f0ce)
- fix(tests): make setup guide cases countable (fbe9c820)
- fix(release): align smoke and roadmap gates (7fda7fc3)
- fix(memory): resolve branch names beside version tags (0c57dcd6)
- fix(hub): align PostgreSQL release metadata (66c8d49f)
- fix(hub): prepare 3.0.1 Windows DSN and Python fallback (aa84d307)
- fix(matrix): SDK · 해석기 매트릭스 임시 폴더를 저장소 밖으로 — git 밖 fixture 가 이 저장소 하위가 되던 위양성 (TASK-2026-11-22-main-020) (99901ae8)
- fix(vscode): 실제 VS Code 실측 — 중계 화면이 비던 것 · 일시정지 버튼이 죽던 것 + .vsix (M-048 WBS-48.1, TASK-2026-11-22-main-016) (423ddfbb)
- fix(relay): Codex 일하는 세션이 커밋할 수 있게 — sandbox 쓰기 루트에 git dir 추가, push 는 보고 (TASK-2026-11-22-main-014) (63cb86fd)
- fix: 로드맵 WBS 한 줄 위반이 session-start 를 죽임 · backlog-update done 의 Result 중복 + 139차 세션 종료 (TASK-2026-11-22-main-012 · main-002) (3ba4f3a4)
- fix: 로드맵 WBS 한 줄 위반이 session-start 를 죽임 · backlog-update done 의 Result 중복 (main 의 같은 수리를 1.x 로, TASK-2026-11-22-release-1.x-001) (ee0deb94)
- fix(seed): 브랜치 자동 seed 가 roadmap_state.json 도 재생성 — seed 커밋 뒤 생성물 대조 검사 2건 red (TASK-2026-11-19-claude-remote-sync-check-234c32-002) (fc0b4a65)
- fix(seed): 브랜치 자동 seed 가 roadmap_state.json 도 재생성 — 생성물 대조 검사 red (main 의 같은 수리를 1.x 로, TASK-2026-11-21-release-1.x-009) (68156e52)
- fix(release): find_dist_files 를 정확한 wheel · sdist 파일명 대조로 — 2.0.0 이 2.0.0b1 · 2.0.01 산출물을 잡던 접두사 glob (TASK-2026-11-21-main-027) (25371094)
- fix(release): find_dist_files 를 정확한 wheel · sdist 파일명 대조로 — main TASK-2026-11-21-main-027 이식 (TASK-2026-11-21-release-1.x-008) (9ce34d5a)
- fix(1.x): 발행 도구 — 2.x 가 나온 뒤 1.x 판은 GitHub latest 를 가져가지 않는다 · PEP 440 정렬 · --target 현재 브랜치 (R16.7, main TASK-2026-11-21-main-026 이식) (f1ed96ca)
- fix(release): PEP 440 사전 판 정렬 · GitHub latest 판정(원격 최고일 때만) · --target 현재 브랜치 — 2.0.0b1 발행 준비 (R16.7, TASK-2026-11-21-main-026) (9e5fe6e8)
- fix(1.x): run_all_checks 잠금 파일 보유자 정보가 깨지던 것 — a+b 에서 seek 가 쓰기 위치를 못 바꿈 → r+b (TASK-2026-11-21-release-1.x-006) (7530b195)
- fix(1.x): '허브로 옮김' 표식이 있으면 쓰기 거절 · session-start 는 허브를 가리킨다 (TASK-2026-11-21-release-1.x-005) (072d62c3)
- fix(archive_branch_memory): 오래 사는 브랜치 표시 (.long-lived) — 1.x 결함 수리를 2.0 에도 (R16.5) (82edf09e)
- fix(archive_branch_memory): 오래 사는 브랜치 표시 (.long-lived) — 병합돼 있어도 합류 반영 · 아카이브하지 않는다 (R16.1 ②) (7178acd9)
- fix(bidir_link): 위키 언급이 없는 entry 에서 UnboundLocalError · 앞 entry id 로 거짓 비대칭 (05678400)
- fix(bidir_link): 위키 언급이 없는 entry 에서 UnboundLocalError · 앞 entry id 로 거짓 비대칭 (41b39d51)
- fix(kit): 현재 마일스톤 병행 선언 기준 · handoff §5 서두 회차 줄 누적형 (TASK-…-012 · -013) (08f82554)
- fix(errors): catch-all 오류 결과에 예외 원인을 싣는다 — 이름만 내던 ValidationError (0fa5566f)
- fix(memory): 재사용된 브랜치의 재합류가 반영 없이 막히고 '이동했다' 로 보고되던 결함 — 아카이브 병합 · 실행 결과 보고 (main-001 · main-002 · main-003) (7df480f9)
- fix(dashboard): drift 가드가 돌지 못하면 '0/0 pass' 로 그리던 결함 — 측정 실패로 (main-015) (8640b4c0)
- fix(workbench): 글자가 박스를 넘던 결함 — 긴 글 · 좁은 폭 · 다른 글꼴에서도 박스 안에 (main-013) (c5cc35d0)
- fix(dashboard): inline_guard=False 패널이 가드를 돌리지 않고 guard_cases 7 · pass 0 을 실측처럼 싣던 결함 (main-012) (b82944d8)
- fix(release): self-recover 재검사 집계 cases_pass 7 > cases_total 6 — drift 가드 해석을 한 함수로 (main-011) (4b18a68e)
- fix(workbench): 실제 브라우저의 폼 POST 가 Origin null 로 403 — Referrer-Policy same-origin (main-007) (0721103a)
- fix(workbench): --stop 이 기록의 pid 가 그 포트의 주인인지 대조 — 인스턴스 표식 (main-005) (d862b009)
- fix(mcp): 오류 신호 불일치 둘 — invoke_tool 이 status error 를 rc 0 으로, summarize_git_history 가 git 실패를 커밋 0건으로 (main-002) (85d9596c)
- fix(gate): 경고 분류기가 /tmp · /var/tmp 경로를 정규화한 뒤 분류해 서드파티 경고를 저장소 경고로 오판하던 결함 (main-001) (f75822ff)
- fix(memory): 합류 반영이 완료 task 를 archived/ 로만 보내 roadmap 근거를 잃던 결함 — 완료 task 도 모 브랜치로 (7fdf0eb5)
- fix(mcp): MCP 도구 4종 성공 경로의 output contract 미등록 — 1.22.0 발행본 결함 (TASK-2026-11-04-main-002) (bbcc2203)
- fix(mcp): verifier 2차 — 오류 규칙 분기 측정 · 값을 --flag=value 로 · 인자 거절은 입력 오류로 (M-029/WBS-29.2) (5d7b7e6d)
- fix(mcp): verifier 1차 — plan_inbox 파일별 값 · response 전달 · 사유 없는 discard · 숫자 apply (M-029/WBS-29.2) (fb3bdc48)
- fix(workbench): verifier 2차 — 모르는 메서드도 404 · 덜 쓰인 파일 case 를 audit 이벤트로 (M-029/WBS-29.2) (5442851b)
- fix(workbench): verifier 1차 — 검증 줄 없는 기준 '미측정' · 토큰 경로의 ~ · 표 밖 메서드 404 · 측정 구멍 보강 (M-029/WBS-29.2) (d74cf2a6)
- fix(plan): 지정한 링크는 응답이 아니다 · 받은편지함의 .rejected.md · 숨은 .md 보고 복구 (ADR-031 2단계, M-028/WBS-28.2) (2c49db32)
- fix(plan): 옮길 수 없는 받은편지함 · 보관 배치는 먼저 거절 · 링크 · 비파일 항목은 응답이 아니다 (ADR-031 2단계, M-028/WBS-28.2) (44c08042)
- fix(plan): 브랜치 안 디렉터리가 심볼릭 링크여도 옮기는 파일 자신을 세지 않는다 (ADR-031 2단계, M-028/WBS-28.2) (d6d46484)
- fix(plan): dry-run 이름 예고를 경로 단위로 · 다시 받은 응답은 거둠을 나르지 않는다 (ADR-031 2단계, M-028/WBS-28.2) (5385a728)
- fix(plan): dry-run 의 예고를 실제와 같게 · 되돌려 적기가 거둠도 나른다 · received_at 을 스펙의 한 꼴로 (ADR-031 2단계, M-028/WBS-28.2) (2ee1fd62)
- fix(plan): 사유 판정을 열거로 고정 — 빈칸 글자 여섯 (ADR-031 1단계, M-028/WBS-28.1) (81b74577)
- fix(plan): 사유는 보이는 글자 · 숫자가 있어야 + 무력화된 표 행 · 빈 결정 줄 검사 (ADR-031 1단계, M-028/WBS-28.1) (6eeae33d)
- fix(plan): 게이트를 지나는 길 둘 차단 + 지문 · 묶음을 스펙 문면대로 (ADR-031 1단계, M-028/WBS-28.1) (3223df79)
- fix(plan): 공백뿐인 사유 거부 + 린트 검사를 전부 대조하는 표로 (ADR-031 1단계, M-028/WBS-28.1) (8dd7027c)
- fix(plan): 검증이 찾은 스펙과 다른 동작 6건 수리 + 검사 보강 (ADR-031 1단계, M-028/WBS-28.1) (a0c8e8d9)
- fix(check_docs): worktree 에서 문서 0개로 통과하던 결함 — 제외 대조를 저장소 상대경로로 — 코드만 흡수 (74021296)
- fix(seed): 이어받은 handoff 가 인용하는 모 브랜치 닫힌 task 를 T1d 가 원류로 푼다 — 코드만 흡수 (bafecf74)
- fix(windows): task 파일 줄바꿈 CRLF→LF 뒤집힘 — 정본 writer EOL 보존으로 재발 차단 (826af874)
- fix(windows): Windows 격차 52건 수리 완성 — cp949 인코딩·교차 플랫폼 락·POSIX 경로·검사 결함 + 121차 세션 메모리 갱신 (main-003) (712e9414)
- fix(windows): 한글 Windows 프로필 — 자식 환경(home·UTF-8·PATH) 통일 · python3 하드코딩 제거 · 저장소 텍스트 LF 고정 (main-003 착수) (b5148946)
- fix(gate): 게이트 러너가 Windows 에서 첫 검사 완료와 함께 죽는다 — _kill_process_group 가 POSIX 전용 os.getpgid 를 쓴다 (main-002) (46701fda)
- fix(auto-seed): origin 없는 저장소에서도 이어받기 — 기준 브랜치 판정을 분리 (main-003) (cbe0b88b)
- fix(purpose_graph): 어느 마일스톤 · leaf 도 섬기지 않는 goal 을 provenance 로 지목 — 조용한 uncovered 금지 (main-004) (e88e4b48)
- fix(memory_lint): T1a 은퇴 · T1c/T1d 를 branch-scoped 로 — index path 선언 · archived 해소, 미분류 참조는 숫자로 (main-003) (094a51ba)
- fix(memory_lint): T1b stale 을 branch-scoped 로 — 공유층 면제 · 브랜치 메모리의 git 커밋 일자로 90일 판정 (main-002) (9f027210)
- fix(entry_diet): harvest 에 v1.20.0 채취 + '현행 생성물 ⊆ 알려진 생성물' 검사로 재실행 누락 고정 (main-001) (b64024b2)
- fix(minimax_plugin): --apply 보고를 반영 전 기준으로 — 첫 설치가 '이미 일치' 로 읽히던 오독 (main-009) (077474d8)
- fix(backlog-update): handoff 동기화 · 이월 색인이 보존된 task 제목을 쓴다 (main-006) (6c348937)
- fix(test): main 체크아웃 관찰에서 --no-reflect 없이는 session-start 가 쓴다 (4b1b5256)
- fix(test): check_state_reconcile 도 관찰 전용 경로로 돌린다 (582763f4)
- fix(test): session-start 합류 승격이 관찰 경로에서 저장소를 쓰지 않게 한다 (ed9eb423)
- fix(archive): 브랜치 오버라이드가 기본 브랜치여도 실제 checkout 브랜치는 합류 반영·아카이브하지 않는다 (remote-sync-status-1ce0a3-003) (f1a4b633)
- fix(matrix): interpreter_matrix 설치 탐침이 상속된 PYTHONPATH 에 속아 의존성 설치를 건너뛰던 것 (main-008) (fb957c5c)
- fix(windows): cp949 로캘에서 wk 가 UnicodeEncodeError 로 죽던 것 — stdio · 텍스트 I/O 를 UTF-8 로 고정 (main-006) (df975bbe)
- fix(release-notes-template): simple template 검사가 저장소 releases/ 에 쓰지 않는다 (306adeaf)
- fix(meta-watch): 저장소 안 중첩 체크아웃(worktree·clone) 경로를 좁은 선언 판정에서 뺀다 (main-013) (5d9b2228)
- fix(branch-memory): worktree 가 자기 네임스페이스로 시작한다 — 자동 seed · 로컬 detached HEAD = 기본 브랜치 · 비 git = main (6118db3d)
- fix(compact-relay): Codex hook 출력을 Codex wire JSON 으로 — `[` 머리말 오판으로 3종 failed · 재주입 0 이던 것 (main-009 · main-010) (8a35197b)
- fix(python-floor): 하한 해석기 호출을 stdin 으로 — Windows 배치 shim 에서 -c 다줄 스크립트가 첫 개행에서 잘리던 것 (09-30-main-002) (a86614aa)
- fix(doctor): wk doctor 가 Windows 에서 정본 파일을 extra 로 오판하던 것 — str(relative_to) 잔여 5곳을 as_posix() 로 (09-29-main-018) (b836d83d)
- fix(roadmap): roadmap_state.json source_path 를 호스트 독립(POSIX)으로 — Windows 커밋이 역슬래시를 남겨 교차 호스트 diff 가 나던 것 (09-29-main-017) (71c718a1)
- fix(windows): repair workflow probes and setup environment (d3bd8689)
- fix(doctor): MCP 해석기 탐침 스크립트를 stdin 으로 — Windows python3.CMD shim 에서 cmd.exe 가 -c 다줄을 첫 개행에서 자르던 것 (09-29-main-013) (388ee750)
- fix(doc-stamp): wiki 스탬프를 frontmatter updated: 하나로 — 게이트·doc-headers-update 가 같은 정본으로 판정·갱신 (09-29-main-012) (31fdfd64)
- fix(doc-layers): wiki frontmatter status · 굵은 '상태' 헤더를 살아있다는 선언으로 읽는다 (09-29-main-010) (c54a3a54)
- fix(backlog-update): update 의 명시 --kind 가 daily index 표식에 반영 + layout 검사의 session kind 오판 (09-29-main-008) (8f5619ca)
- fix(doc-stamp): 날짜 뒤 주석 달린 스탬프를 전수 게이트가 판정 없이 건너뛰던 것 (09-29-main-007) (cad0d836)
- fix(ensure-entrypoints,doctor): 공유 AGENTS.md 마커로 opencode 가 적용 판정돼 오버레이를 만들던 것 (09-29-main-004) (bd78a2ad)
- fix(bootstrap): minimax-code 경로 대소문자 불일치로 session-start 가 매 세션 빈 task 를 만들던 것 (#29, 09-29-main-002) (9e4660ba)
- fix(backlog-update): 날짜 경계 이월이 새 daily index 에 [generic] 을 적던 것 + 98차 세션 종료 (09-29-main-001) (6fd6af7c)
- fix(plugin): antigravity MCP 도구 11개가 전부 거부되던 것 — 사본 별칭을 ro 로 + grok 목록 부재 위양성 (09-28-main-019·020) (0a232c99)
- fix(tests): check_self_application 이 실제 사용 지표에 session-start 를 붙였다 + main-018 판정 (09-23-main-018) (23162c90)
- fix(release): 유예 없이 지운 공개 API 2종을 은퇴 shim 으로 복원 — v1.13.0 제거 (09-28-main-014) (891ce0b4)
- fix(dashboard): Panel 1 phase 를 로드맵 정본에서 파생 — v0.15 에 멈춘 상수 표시 (09-23-main-015) (6253791c)
- fix(release): validate source 목록을 정본 하나로 — 사본이 새 source 를 못 따라감 (09-28-main-009) (9c2bd06a)
- fix(telemetry): 검사가 실제 저장소 telemetry 에 쓰지 않게 + 러너가 증가를 red 로 (09-28-main-006) (4ea61232)
- fix(dashboard): telemetry 를 대시보드당 스냅샷 1회로 — Panel 3·8 hit_rate 경합 (09-28-main-005) (e5d2c6f4)
- fix(hooks): force 차단 hook 을 git 의 실제 pre-push 인터페이스로 판정 (09-25-main-002) (2dec51ca)
- fix(memory): main-019 index 제목 중복 + handoff §5 의 닫힌 후보 정리 (a1e93af9)
- fix(tests): 소스 전수 열거가 중첩 worktree 까지 훑었다 — 호스트 의존 red (main-011) (ca2db5ba)
- fix(docs): CLAUDE.md 스탬프 + 유예가 로컬 게이트를 가린 자리 등록 (main-009) (c2c7593f)
- fix(cli): 모르는 인자를 거절한다 — 조용히 버리면 요청과 다른 일을 한다 (main-008) (8ee16bdc)
- fix(tests): 롤업 표식이 하나뿐이라 흐름을 못 갈랐다 (main-007) (6b7a941e)
- fix(tests): case 수 대조 축의 범위를 실측으로 넓힌다 (main-006) + 86차 종료 (c3997a01)
- fix(memory): 검색이 자기가 집은 것을 돌려주게 (main-005) (70a97a5d)
- fix(tests): case 6 이 index 락을 잡아 병렬에서 터지던 것을 읽기 전용으로 (main-002) (f3ac2d13)
- fix(memory): 승격 후보 판정을 어휘 겹침에서 선언으로 (main-003) (a5961bd2)
- fix(tests): 하한 측정 모드를 요약 줄에 — green 이 승격의 증거가 아니었다 (main-007) (79b5ffd9)
- fix(ci): sdist 빌드 산출물 ignore + 요약에 저장소 write 축 반영 (main-008) (d3ece239)
- fix(ci): smoke.yml 의 연속 append 를 한 블록으로 — actionlint SC2129 (main-007) (16f9dab4)
- fix(release): 스탬프 범위를 손 목록에서 파생으로 + 뒤처진 116건 소급 교정 (main-006) (df4a3d53)
- fix(tests): version_flag 의 dist TOCTOU 제거 + 스탬프 판정 git 호출 1+N → 1 (main-005) (bee66a67)
- fix(doc-stamp): '마지막 내용 변경' 이 실제로 내용 변경을 재게 한다 + 스탬프 97건 소급 교정 (main-004) (2cf73e87)
- fix(release): 문서 스탬프를 뒤처진 것만 올린다 (main-002) (7b619a93)
- fix(doctor): 설치 시각 폴백을 트리 최신 mtime 으로 (main-003) (625d0ee2)
- fix(ci): digest 마커를 본문으로 — gh issue comment 에 없는 플래그였다 (main-001) (105f0043)
- fix(tests): case 3 의 전제가 호스트 의존이었다 + 81차 세션 종료 (e2d6b0d3)
- fix(docs): smoke 수 판정 범위를 포함 목록에서 전수 파생으로 (main-004) (d882b42a)
- fix(doctor): content_drift 가 읽히지 않는 사본을 재고 있었다 — 소스 유형을 읽는다 (main-006) (3d5c7830)
- fix(backlog-update): --apply 가 형제 생성물 roadmap_state.json 을 두고 갔다 (main-004) (cc172d6c)
- fix(backlog-update): update 에서 --task-brief 를 선택 인자로 — 뜻이 갈리는 필수 인자가 진행 기록을 덮었다 (371afdbf)
- fix(graph-insights): 완료한 일이 늘수록 내려가던 점수 — 오탐인 줄 알았던 자리가 지표 결함이었다 (878f0ae7)
- fix(paths): 설치본에서 증발하는 모듈 앵커 — 소비자 배포처 모순의 뿌리를 닫는다 (30d2804b)
- fix(backlog): task ID 채번이 원격을 함께 본다 — 코드가 적고 있던 거짓 보증을 지운다 (67fd0776)
- fix(state): 예제 산출물 드리프트에서 생성기 결함 2건을 파내 정본과 판정으로 닫는다 (f21838f4)
- fix(release): 발행마다 손이 가던 두 자리를 파생과 판정으로 닫는다 (main-003·004) (bb55ccd5)
- fix(session-start): 상태 불일치 경고의 분모를 task corpus 전수로 바꾼다 (main-002) (b3f3eff9)
- fix(backlog-update): done 강등이 이미 기록된 완료를 취소하지 않는다 (main-003) (e6f033db)
- fix(tests): 휘발 경로 리터럴이 Linux CI 를 10 커밋 red 로 만들었다 (main-004) (e7671d24)
- fix(checks): 문서 스탬프 기대값을 리터럴에서 git 파생으로 (main-002) (09a9df21)
- fix(packaging): workflow_kit.cli 를 wheel 에 싣고, 손 목록을 디스크 대조로 대체 (main-001) (12b9f311)
- fix(guarantee): 은퇴한 stable 행을 지우지 않는다 + v1.8.0 migration 절 (main-005) (2d8f4cad)
- fix(doctor): 탐침이 자기 자신의 낡음을 잰다 — 버전 같고 내용 다름 (main-002) (c88c0890)
- fix(doctor·backlog·docs): '존재가 정합으로 읽히는 자리' 3부류 + 69차 세션 종료 (main-001·003·004) (6d9ad763)
- fix(release): pi 매니페스트 version 을 kit 에 묶는다 + 68차 세션 종료 (main-004) (0c86b51f)
- fix(doctor): grok 설치본을 이름이 아니라 선언으로 찾는다 + 사본 0 채널의 침묵 제거 (main-002·003) (6efc45ec)
- fix(paths): '자기 위치 오인' 결함족 전수 마감 — 진입점 7건 + 정적 게이트 (main-003·012·013) (cffce266)
- fix(mcp): mcp 2.1.1 의 FastMCP 심볼 제거 대응 — importlib 동적 해석 (main-009) (62a12485)
- fix(memory): 아카이브된 brave-valley-2538 세션 기록의 깨진 링크 3건 교정 (874395f2)
- fix(ops): 63차 세션 — M-007 운영 축 상설 선언 + '자기 위치 오인' 결함족 3건 소탕 (b3eee5ad)
- fix(mcp): Windows 플랫폼 결함 축 — emit 해석기 플랫폼 분기 + PYTHONPATH target 레이아웃 교정 + doctor kit_resolution 탐침 (62차) (24b75e2a)
- fix(docs): work log 의 docs 밖 markdown 링크 2건 제거 — mkdocs strict build red 수리 (95fadfc2)
- fix(state): safe_relpath POSIX 정규화 — Windows 호스트 state.json 백슬래시 제거 (TASK-2026-08-25, cross-host 형식 결함) (bcb05cfb)
- fix(doctor): pip 부재 판정이 선언을 읽는다 — uv tool venv 의 부재는 설계다 (main-009) (4461e08e)
- fix(okf): 매니페스트 버전을 정본 파생으로 — 한 번들이 두 버전을 말하고 있었다 (main-008) (b09bbf16)
- fix(mypy)!: 캐시를 전용 경로로 격리 — 빈 문자열은 격리가 아니었다 (main-007) (19e40ac9)
- fix(mypy): 캐시 격리 — no-incremental 은 읽기만 끄고 디렉터리는 만든다 (main-007) (8454e4eb)
- fix(gate): 절단이 트레이스백 결론을 자르지 않게 — 범인이 지목됐다 (main-004 관찰 4차 후속) (ffe4bc77)
- fix(gate): mypy 게이트에 --show-traceback — 4차까지 증거가 없던 이유 (main-004 관찰 4차) (579e2f17)
- fix(bootstrap): daily backlog 를 정본 작성기로 조립한다 — 사본을 없앴다 (main-003) (6a2c94ad)
- fix(tests): watch_transient flake — 이벤트 1건은 완결본을 뜻하지 않는다 (main-001) (900c9455)
- fix(ci): consumer-metrics-digest 가 실재하는 경로를 부른다 (main-017) (8b2c6ebb)
- fix(ci): okf-validate 가 okf_version 을 정본에서 파생한다 (main-016) (72ecff6c)
- fix(entrypoint): 산문 목록 파생 + 사라지던 planned + 포크 병합 (main-013, -014, -015) (cd0ff943)
- fix(doctor): 어느 사본이 설치본인지 선언을 읽는다 — 갱신이 보고를 나쁘게 만들던 자리 (main-010) (151627ee)
- fix(harness): session-end 를 bootstrap 채널에도 — 두 채널의 스킬 집합이 갈라져 있었다 (main-008, -009) (43168b34)
- fix(release): next_version 을 커밋에서 파생한다 — 개수는 세고 판정은 안 세던 자리 (main-006) (40e86dc2)
- fix(observability): 관찰 축 3개 실측 — mypy 원인 계열 확정 + 승격 루프 배선 (main-004, -005) (a36c5edf)
- fix(linter): in_progress 대조의 세 번째 출처를 task SSOT 로 (main-002) (e64b4812)
- fix(wiki): L2 파이프라인 회생 — 화석 은퇴와 파생 뷰 재정의 (main-004) (3bd45c10)
- fix(okf): 상호운용을 자기 선언이 아니라 실측으로 (main-006) (426da99c)
- fix(deploy): 패키지가 체크아웃 레이아웃에 기대던 결함 (main-003) (2bd5417b)
- fix(rollover): 롤오프 포인터가 실행마다 쌓이던 결함 (main-002) (666424b2)
- fix(smoke): check_deprecation_3rd_cycle 의 죽어 있던 제외 목록 (main-003) (30369739)
- fix(backlog): 날짜 롤오버 시 진행 중 task 의 갱신이 사라지던 결함 (main-001) (d02d9663)
- fix(standard): 정본의 다중 줄 bullet 이 추출에서 잘리던 결함 수리 (main-002) (f3e9d0cc)
- fix(checks): timeout 선언 누락 3건 + 내장 worktree 스캔 제외 (main-011) (28f12ed1)
- fix(memory): seed 가 첫 세션 기록을 쓴다 — 갓 seed 한 브랜치가 layout green (main-005) (f9b374ee)
- fix(memory): 아카이브가 살아 있는 대상 상대 링크를 안 고치던 결함 수리 (main-006) (098386c0)
- fix(memory): 검증 결과 주입이 작업 결과 묶음을 가르던 결함 수리 (main-010) (0b2ef9b3)
- fix(checks): 영어화된 표면을 조회하던 assert 6건 동반 이동 (stage 3 진행분) (35a144e8)
- fix(memory): 리뷰에서 나온 결함 5건 — 소실 오판 1 · 침묵 1 · 정보손실 1 · 미처리 2 (f7989471)
- fix(release): mypy 게이트가 blocking error 사유를 버리던 자리 + TASK-004 관찰 2차 (8544facd)
- fix(smoke): 리뷰에서 나온 검출 누락 2건 + 오탐 1건 (case 9~11) (e10ba4cf)
- fix(resolver): remote 판단이 CI env 를 보던 gate 정정 (TASK-2026-08-13-feat-plugin-harness-distribution-001) (67d11dd3)
- fix(resolver): canonical URL 이 체크아웃한 브랜치를 따라다니던 자리 (TASK-2026-08-13-feat-plugin-harness-distribution-001) (ecb651da)
- fix(tests): 임시 workspace 판정이 호스트 저장소 state.json 에 달려 있던 자리 (TASK-2026-08-13-feat-plugin-harness-distribution-001) (6dee7aae)
- fix(memory): 작업 기록을 브랜치 메모리로 이관 — active/main 무접촉 (TASK-2026-08-13-feat-plugin-harness-distribution-001) (d265e981)
- fix(dist): main 정합 보완 6건 — 판정 사각지대 · 파생 신원 · fail-closed (TASK-2026-08-13-main-009) (77a18e71)
- fix(dist): package Codex marketplace at discovery path (6e537c6a)
- fix(dist): 공개 배포 전 필수 수리 3건 — LICENSE / 버전 체계 stable 정리 / 저자 이메일 (TASK-2026-08-13-main-007) (747ecfc6)
- fix(mcp): OpenCode 방언을 실측 형태로 — entry 정본 단일화 (TASK-2026-08-13-main-002) (364db82e)
- fix(tests): 원본 bump 검사 sandbox 이관 — 마지막 pyproject 왕복 제거 (TASK-2026-08-13-main-001) (cca074cd)
- fix(docs+packaging): 소비자 안내 표면을 wk 로 통일 + tools 배포를 wheel 에서 검증 (TASK-2026-08-11-main-027) (2d799f5a)
- fix(mcp): 도구 목록 사본 3계열을 registry 단일출처로 + 유령 script_path 실물화 (TASK-2026-08-11-main-025) (8f8e95da)
- fix(standard): §11.1 명령 손 사본 7곳을 정본 파생으로 + 검출기·분류 단언 강화 (TASK-2026-08-11-main-026) (267dfafb)
- fix(mcp): readOnlyHint 를 registry 선언 파생으로 — write 도구 2종 허위 주석 정정 + ADR-003 v1.1.7 (TASK-2026-08-11-main-024) (e6f1653a)
- fix(backlog-update): update 모드를 재생성에서 병합으로 + handoff task ID dedupe (TASK-2026-08-11-main-023) (30563a47)
- fix(tests): macOS /private symlink 로 갈린 검사 4건 이식성 수정 + state.json 갈라짐 해소 (TASK-2026-08-11-main-017) (24bcc902)
- fix(tests): CHECK_TIMEOUT_S 파일 안 선언 신설 — 로컬 병렬 TIMEOUT flake 해소 (TASK-2026-08-11-main-015) (b636e2fb)
- fix(tools): watcher 기동을 sleep 추측에서 ready handshake 로 — CI flake 해소 (708eb94c)
- fix(tests): 원본-무결성 관찰 검사 3건 정숙화 + 2026-08-11 세션 close (TASK-2026-08-11-main-008) (b4ef854e)
- fix(quality): PERF-WF-04 저장소 오염 제거 + sandbox 복사 소멸-파일 내성 (TASK-2026-08-11-main-006) (9502c43b)
- fix(release): amend Guard 2 의 staged-삭제 git add fatal 해소 (TASK-2026-08-11-main-002) (35d2b27d)
- fix(tests): version_flag test 3 의 dist 오염 우연 의존 해소 — smoke CI red 복구 (TASK-2026-08-11-main-005) (a9c408b8)
- fix(tests): 원본 저장소에 --apply 하던 검사 4건을 사본으로 (TASK-2026-08-10-main-019) (59f33655)
- fix(tests): smoke slash job 15연속 red 해소 — 검사가 살아있는 브랜치 상태에 의존 (TASK-2026-08-10-main-016) (099dba0d)
- fix(tests): dashboard timeline 검사 2건 — 살아있는 저장소/registry 상태 대신 결정적 fixture (26613590)
- fix(release): dist 기본값 dry-run 반전 — release 와 정합 (TASK-2026-08-10-main-005) (4c7895f6)
- fix(tests): doctor exit-on-fail 테스트 — 살아있는 저장소 상태 대신 결정적 fixture (c0ad1a6b)
- fix(tests): mavis e2e 호스트 사본 제거 + 세션 close memory 갱신 (4b67621a)
- fix(tests): smoke_trend 판정 복원 — 검사가 맞았고 내 진단이 틀렸다 (15d5a22a)
- fix(phase13,harness): 문서 전반 실측 대조 + harness 정본 정의 확정 (6a1ecf71)
- fix(changelog,docs): Phase 13 P1 close — 세 항목 모두 문서가 실제와 달랐다 (aeafaab5)
- fix(tests): dist skip 전제를 cmd_dist 와 같은 기준으로 (63d23662)
- fix(release): 릴리스 도구 결함 2건 + 릴리스 없이 잡히는 회귀 검사 (ca3c9c60)
- fix(tools): memory 경로 조립을 정본 API 로 + v1.1.2 릴리스 노트 초안 (6652ba6b)
- fix(mypy,tests): 남은 red 4건 close — FULL mypy strict 128 files clean 복구 (c6fba3c9)
- fix(rotation,docs): rotate 도구 순서 규약 통일 + 사전 존재 red 정리 (6cfb1688)
- fix(test): 새 검사가 mcp 2.0.0 에서 죽었다 — isError 는 1.x 이름이다 (§2.63 후속) (c6f31ffc)
- fix(claude-code): slash command 설명 자리에 버전 마커가 앉아 있었다 (§2.59 후속) (33424fcc)
- fix(claude-code): 자기 harness 를 부분만 적용하고 있었다 + 마커가 frontmatter 를 깨고 있었다 (§2.59) (227219ec)
- fix(okf): 검사가 처음 돌자 나온 URL 2건 — 죽은 링크가 아니라 태어난 적 없는 링크 (§2.58) (c58111de)
- fix(cli): 오래 red 인 스케줄 workflow 2건 — 둘 다 원인이 딴 데 있었다 (§2.57) (7b076f88)
- fix(tests): 슬래시 브랜치에서 깨지던 것들 — 셋이었고 원인이 서로 달랐다 (§2.55) (dda08258)
- fix(tools): 생성물인지를 이름으로 가르고 있었다 — 정본은 .gitignore 다 (§2.54) (99eb05a1)
- fix(tools): 조사가 어디까지 보는지를 선언하고 있었다 — 포함 목록을 없앤다 (§2.53) (710cceae)
- fix(dashboard): 모든 panel 의 기준이 자기 근거를 안 내고 있었다 (§2.51) (1b52b853)
- fix(tests): 검사가 CI 에서 무력화되고 있었다 — branch env 우선 규칙 (§2.50) (15ee1045)
- fix(paths): 세 번째를 찾으러 갔더니 다른 축에 있었다 — branch 해석기 합의 (§2.50) (d6a23fe2)
- fix(doctor): 같은 결함이 CLI 에도 있었다 — 기준 경로와 설정 출처 (§2.49) (607b84c3)
- fix(maturity): 검사가 처음 돌자 나온 2건 — 하나는 진짜, 하나는 위양성 (§2.48) (2e139319)
- fix(linter): 기준 경로가 한 칸 어긋나 있었다 — 설정과 maturity (§2.47) (14cd7928)
- fix(state): 파생물의 상한과 포인터 — 쓰는 쪽이 규약을 모르고 있었다 (§2.46) (72bfbe06)
- fix(server): lowlevel 도 1.x/2.x 를 해석한다 — 상한 핀 해제 (§2.43) (1f1881c6)
- fix(ci): 인스펙터가 서버 인자를 삼키고 있었다 — 도구도 의존성이다 (§2.42) (7b1404b3)
- fix(deps): 상한 핀 복원 — 이관 범위를 파일 하나로 잡았다 (§2.41 정정) (7469fb14)
- fix(server): mcp 1.x/2.x 양쪽을 해석한다 — 상한 핀 해제 (§2.41) (1b8a0eb9)
- fix(deps): mcp 상한 핀 — 2.0.0 이 fastmcp 모듈을 없애 CI 가 red 로 넘어갔다 (71feef3e)
- fix(migrate): 구분 heading 을 몰라서 두 가지를 동시에 잃고 있었다 (§2.40) (d14d5f4d)
- fix(state): status 칸에 출처를 적고 있었다 — 진행 상태 축과 출처 축의 분리 (§2.39) (5be5ba43)
- fix(state): "최근 완료" 가 최신을 고른 적이 없었다 — 상한·정렬·완료 판정 (§2.38) (047d4e5d)
- fix(backlog-update): state.json 을 파괴하던 정규식 사본 + 결함 3건 (§2.37) (fbdc8f95)
- fix(tests): 같은 자기참조가 넷이었다 — push 직전에는 통과할 수 없던 게이트 (§2.35 (8)) (fbca6d74)
- fix(smoke): 자기참조를 하나 더 남겼다 + 실패 사유가 늘 잘려 나가던 excerpt (§2.35 (6)(7)) (44b1b780)
- fix(workflow): 남겨 둔 결함 3건 + CI 를 상시 red 로 만들던 자기참조 (§2.35) (1943026d)
- fix(mypy): strict 가 v0.11.11 이래 적용된 적이 없었다 — 호출 23곳 중 21곳이 config 미명시 (212/212) (3a7bd37a)
- fix(mkdocs): plugin 이 로드 불가라 문서 사이트가 한 번도 배포된 적이 없었다 (211/211) (7b1d63e4)
- fix(tests): CI 잔여 3건 — 환경변수/외부 홈 경로/앞선 실행 결과에 기대던 것 (88d06416)
- fix(release): north-star 의 분자가 도달 불가였다 — 원장에 첫 entry 가 생길 수 없었다 (210/210) (fea44faf)
- fix(tests): 실행 환경에 누적된 상태에 의존하던 smoke 5건 — CI 가 40회 연속 red 였다 (209/209) (9d402896)
- fix(skill): backlog-update 가 governance layout 을 만들지 못했다 (전량 206/206) (d285077a)
- fix(state): state.json 이 아무도 읽지 않는 경로로 갱신되고 있었다 (전량 205/205) (ce81fa77)
- fix(dashboard): Panel 1 north-star / maturity_stale 재정의 — 달력 대신 drift (전량 204/204) (dbc4ec1d)
- fix(release): auto-bump 이 dry-run 에서 version 을 write 하던 결함 — 릴리스 직후 발현 (94e61e18)
- fix(memory): R9 위반 해소 — memory-freeze 스킬 복구 + 자기참조 게이트 제거 (전량 199/199) (999f1606)
- fix(release): 빌드 의존 red 4건 해소 — 릴리스 도구 의존 선언 + verify --apply 복구 (ee4e512e)
- fix(wiki): wiki_drift / wiki_trend red 해소 + smoke 의 미커밋 작업 파괴 경로 차단 (e914464c)
- fix(docs): doc lint 부채 해소 + source 계층 자립성 회복 (red 2건) (f48c8eb3)
- fix(tests): smoke 가 추적 중인 저장소 파일을 write 하던 오염 2경로 차단 (677f0c8a)
- fix(release): release --dry-run 이 저장소를 수정하던 오염 차단 (6a95eae0)
- fix(memory): workflow_memory_dir docs/ 분기의 active/ 누락 수정 — 구조적 red 3종 회복 (71c4ed53)
- fix(tests): 저장소 상태 결합 stale 테스트 4건 회복 (미조사 red 원인 확정) (263f75f3)
- fix(tests): 저장소 상태/버전 결합 테스트 2건 격리 + 잔여 red 착수 지점 문서화 (acf6c307)
- fix(tests): 잔여 red 3건 수정 — CLI 옵션 누락 복원 + 날짜/형태 결합 테스트 정정 (ff89e188)
- fix(release): release_pipeline --amend 3중 가드 + 저장소 히스토리 재작성 위험 차단 (c4df3587)
- fix(tooling): fork bomb + state.json 파괴 근절 — smoke 전량 실행 안전성 확보 (e6f8e3ee)
- fix(tooling): temp dir 누수 근절 — /var/tmp 211GB 회수 + 재발 방지 가드 (9a7a1288)
- fix(tooling): /var/tmp 누수 가드 + .venv 명시적 차단 (5706dda9)
- fix(docs): smoke count 195 → 196 (신규 MEMORY_GOVERNANCE cross-check 추가) (d4abac9b)
- fix(memory_governance): frontmatter stamp + status 템플릿 순서 정합 (f0ac5b36)
- fix(docs): smoke count 192 → 195 + CODE_INDEX 카운트 자동 추출 정합 (ac7952f4)
- fix(samples): output_samples 24 file tool_version v0.15.0-beta → v0.15.15-beta (f831a99c)
- fix(workflow): PROJECT_PROFILE 경로를 docs로 통일 (f23ba2fb)
- fix(audit): audit_mkdocs_links.py _strip_code_blocks out.append 누락 fix (57a00dc5)
- fix(memory): work_backlog.md.bak 의 audit_follow_up dead link → sessions/ 로 redirect (98437750)
- fix(release): __init__.py literal return v0.13.3-beta → v0.14.0-beta (12691dff)
- fix(dashboard): _repo_root 시그니처 Path | str | None 허용 (7a7f2fb5)
- fix(dist): strip repo-absolute paths from harness export (no runtime/source deps) (24b626b2)
- fix(linter): broken_link check 의 .. segment 정규화 + smoke test fixture 정합 (9960e8ff)
- fix(state): state.json path latent bug fix (v0.6.0.1 부터) + test fixture 정합 (4821b710)
- fix(ci): mypy-strict workflow install mcp-sdk extra — CI 의 [import-not-found] 해소 (80470cd8)
- fix(workflow_kit): mypy strict 잔여 13 error 일괄 격상 — FULL mypy strict 도달 (107 file clean) (4253eed6)
- fix(workflow_kit): mypy strict read_only_mcp_sdk + doc_sync 4 error 묶음 격상 (65f0b203)
- fix(workflow_kit): mypy strict mcp_v1_server + release_status 6 error 묶음 격상 (094cacf8)
- fix(workflow_kit): mypy strict cli/doctor + common/decorators 10 error 묶음 격상 (97795bc9)
- fix(samples): schema drift 회귀 방지 — sample 24 + schema 2 갱신 (00cc83e5)
- fix(workflow_kit): mypy strict output_contracts 15 error 격상 (f6b65a43)
- fix(wiki): R9 lint false-positive 회피 — dashboard emit multi-line 분리 (1333cc8a)
- fix(workflow): 세션 종료 단계 commit/memory 순서 정정 — memory → commit → push (32185c70)
- fix(release_pipeline): cmd_release --dry-run flag + local tag create (f531adb0)
- fix(v0.5.10.1): smart update — VERSION marker + content hash 기반 silent 갱신 (332de1aa)
- fix(v0.5.9.1): wire 가이드 §3 sub_payloads fix + 회귀 test (c2026344)
- fix(v0.5.7.1): include workflow_kit.common.{state,contracts,schemas} in wheel packaging (8e5cd7b3)
- fix: 42/42 smoke tests green + MiniMax Code harness overlay (#13) (fd120178)
- fix(mcp): remove unsupported version param from FastMCP init (fa0eee42)
- fix(ci): update test paths and dependencies in smoke.yml (d6df3d00)
- fix: address PR #10 review feedback (6d89752b)
- fix(workflow): stabilize beta 0.4.0 state configuration (49e74a79)
- fix: resolve PR #8 feedback, improve smart-reader formatting, and stabilize state management (1f807870)
- fix: update relative links in project documents to reflect new root structure (a76f34b3)
- fix: include runtime scripts in default bootstrap paths (d721cd91)
- fix: resolve empty project detection bug and update docs for team sharing (1c9860e1)
- fix: comprehensive smoke_check inference across all harnesses (Gemini, Codex, Antigravity, OpenCode) (7fca126c)
- fix: ensure smoke_check inference in all opencode agent templates (100b4de2)
- Fix CI-broken README dist links (c7fc67d6)

## [2.1.0] - 2026-11-22

### Changed

- release(v2.1.0): 발행 완료 — tag v2.1.0 (a423d21d) · GitHub Release Latest (wheel · sdist) · M-048 done · M-049 Go/Rust 전환 concept 등록 (46320576)
- release(v2.1.0): 발행 준비 — 2.1 허브 오케스트레이션 (minor, 베타 표기) (a423d21d)

## [2.0.0] - 2026-11-21

### Changed

- release(v2.0.0): 발행 완료 — tag v2.0.0 (20c61a09) · GitHub Release Latest (wheel · sdist) · v1.30.0 은 latest 아님 · CHANGELOG · maturity · dashboard · M-038 · M-040 done · task close (6b1501b7)
- release(v2.0.0): 발행 준비 — 2.0 워크플로우 허브 (베타 표기 · 판은 정수, 소유자 2026-11-21) (20c61a09)

## [1.30.0] - 2026-11-21

### Changed

- release(v1.30.0): 발행 완료 — tag v1.30.0 (24ca6ae3) · GitHub Release (asset 5) · CHANGELOG · dashboard · drift ledger · task close (00044aaa)
- release(v1.30.0): 노트 — 같은 날 내는 2.0 판은 v2.0.0 (베타 표기, 소유자 2026-11-21) (24ca6ae3)
- release(v1.30.0): 발행 준비 — 1.x 안내 판 (2.0 안내 · EOL · 표식 거절 · 채널 고정 안내, R16.4) (c6a9698e)

## [1.29.1] - 2026-11-21

### Changed

- release(v1.29.1): 발행 완료 — tag v1.29.1 (148e6cdc) · GitHub Release (asset 5) · CHANGELOG · maturity · drift ledger · task close (62879048)
- release(v1.29.1): 발행 준비 — 오래 사는 브랜치 표시 .long-lived (1.x 결함 수리 patch · R16.1 ②) (5e43f8f5)

## [1.29.0] - 2026-11-20

### Changed

- release(v1.29.0): 발행 완료 — 태그 push + GitHub Release(asset 5종) + §2.8 5채널 · task -003 close (fff952cd)
- release(v1.29.0): 발행 준비 — 읽기 전용 소비자 클론에서 session-start 는 저장소에 쓰지 않는다 (minor) (e3af1355)

## [1.28.0] - 2026-11-20

### Changed

- release(v1.28.0): 발행 완료 — 태그 push + GitHub Release(asset 5종) + §2.8 5채널 · task -002 close (b05dec29)
- release(v1.28.0): 발행 준비 — 호스트 역할(소비자 클론 push 차단) · 재사용 브랜치 재합류 수리 (minor) (256d36d0)

## [1.27.0] - 2026-11-17

### Changed

- release(v1.27.0): 발행 완료 — 태그 push + GitHub Release(asset 5종) + §2.8 5채널 · task -006 close (fc814642)
- release(v1.27.0): 발행 준비 — iPad 폼 제출 수리 · 진행 기록 상기 · 한 호스트 여러 워크벤치 (minor) (aa34ed8d)
- chore(memory): v1.27.0 발행 task 등록 (-006) (fef0d7b5)

## [1.26.0] - 2026-11-16

### Changed

- release(v1.26.0): 발행 완료 — 태그 push + GitHub Release(asset 5종) + §2.8 5채널 · task -018 close (90124a3a)
- release(v1.26.0): 발행 준비 — 워크벤치 todo · 응답 자동 반영 hook + 대시보드 · release · 워크벤치 수리 넷 (minor) (632cb661)

## [1.25.0] - 2026-11-16

### Changed

- release(v1.25.0): 발행 완료 — 태그 push + GitHub Release(asset 5종) + §2.8 5채널 · task -010 close (c84ab092)
- release(v1.25.0): 발행 준비 — 워크벤치 지속 갱신(자동 새로고침 · 실시간 값 · 진행 기록) + 폼 POST 403 · --stop pid 대조 수리 (minor) (d00fbfbd)

## [1.24.0] - 2026-11-16

### Changed

- chore(release): v1.24.0 발행 task close — claude-code 채널 재적용 · verifier PASS (main-004) (57f4d467)
- release(v1.24.0): 발행 완료 — 태그 push + GitHub Release(asset 5종) + §2.8 4채널 (3588c8b8)
- release(v1.24.0): 발행 준비 — 워크벤치 개방 모드 · 자동 기동 · 화면 개편 + 경고 분류기 · MCP 오류 신호 수리 (minor) (5d3419fa)

## [1.23.0] - 2026-11-15

### Changed

- release(v1.23.0): 발행 완료 — 태그 push + GitHub Release(asset 5종) + §2.8 · task -002 close (d680989d)
- docs(release): v1.23.0 노트의 미측정 건수를 이번 게이트 실측(컨텍스트당 83 = 79 · 4)으로 — 1.22.0 숫자를 옮겨 적었다 (0ce020df)
- release(v1.23.0): 발행 준비 — 주장 트리 계획 · plan-import · 워크벤치 · MCP plan_inbox/plan_import + MCP 4종 계약 수리 (minor) (58889bb6)

## [1.22.0] - 2026-10-31

### Changed

- release(v1.22.0): 발행 완료 — 태그 push + GitHub Release(asset 5종) + Windows 격차 1건 추가 수리 + §2.8 · main-004 close (8ef8c1c9)
- release(v1.22.0): 발행 준비 — 한글 Windows 프로필 확립 + Windows 격차 52건 수리 묶음 (minor) (a44b7d31)

## [1.21.0] - 2026-10-19

### Changed

- release(v1.21.0): 발행 완료 — 태그 push + GitHub Release(asset 5종) + 발행 wheel 격리 실측 + §2.8 · 노트 수치 정정 · main-005 close (5134bac8)
- release(v1.21.0): 발행 준비 — minimax-code doctor 5채널 편입 + 117 · 118차 수리 묶음 (minor) (a019c51b)

## [1.20.1] - 2026-10-06

### Changed

- release(v1.20.1): 발행 완료 — 태그 push + GitHub Release(asset 5종) + 발행 wheel 격리 실측 + §2.8 (868d11f0)
- release(v1.20.1): 발행 준비 — backlog-update handoff 제목 동기화 수리 (patch) (ffff4900)

## [1.20.0] - 2026-10-06

### Changed

- release(v1.20.0): 발행 완료 — 태그 push + GitHub Release(asset 5종) + 발행 wheel 격리 실측 + §2.8 (2e959331)
- release(v1.20.0): 발행 준비 — 진입점 다이어트 + AI-native SDLC A1~A3 + MiniMax Code 채널 (997b2b3b)

## [1.19.0] - 2026-10-02

### Changed

- release(v1.19.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + 발행 wheel 격리 실측 + §2.8 (e5f48f3e)
- release(v1.19.0): 발행 준비 — Windows: cp949 stdio/텍스트 I/O UTF-8 고정 + 하네스 호출 python -m workflow_kit 전환 (ea193113)

## [1.18.0] - 2026-10-02

### Changed

- release(v1.18.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + 발행 wheel 격리 실측 + §2.8 (fc56d4c4)
- release(v1.18.0): 발행 준비 — worktree 합류 반영 (병합된 브랜치 메모리를 모 브랜치 메모리에 기록) (1271be5f)

## [1.17.0] - 2026-10-02

### Changed

- release(v1.17.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + 발행 wheel 격리 실측 + §2.8 (e543e589)
- release(v1.17.0): 발행 준비 — worktree 모 브랜치 이어받기 + worktree 자동 seed · 게이트 호스트 의존 수리 2건 (35e4c7ef)

## [1.16.0] - 2026-09-30

### Changed

- release(v1.16.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + 발행 wheel 격리 실측 + §2.8 (9d6c1436)
- release(v1.16.0): 발행 준비 — Codex 플러그인 compact 중계 hook 탑재 + Codex wire JSON 출력 수리 (13314eaa)

## [1.15.0] - 2026-09-30

### Changed

- release(v1.15.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + 발행 wheel 격리 실측 + §2.8 (672fa400)
- release(v1.15.0): 발행 준비 — compact 중계 (wk compact-checkpoint · 스킬 compact-relay · hook 3종) + Windows 호스트 수리 4건 (e7835694)

## [1.14.4] - 2026-09-29

### Changed

- release(v1.14.4): 발행 완료 — 태그 push + GitHub Release(asset 4종) + wheel 격리 shim 실측 + §2.8 (5c78434f)
- release(v1.14.4): 발행 준비 — Windows doctor MCP 탐침 shim 절단 + wiki 스탬프 판정 수리 (e25239c5)

## [1.14.3] - 2026-09-29

### Changed

- release(v1.14.3): 발행 완료 — 태그 push + GitHub Release(asset 4종) + wheel 격리 실측 + §2.8 (0c7a89e9)
- release(v1.14.3): 발행 준비 — backlog-update kind 표식 + 스탬프 형식 판정 수리 (94afc6aa)

## [1.14.2] - 2026-09-29

### Changed

- release(v1.14.2): 발행 완료 — 태그 push + GitHub Release(asset 4종) + wheel 격리 실측 + §2.8 (5a0fd083)
- release(v1.14.2): 발행 준비 — 공유 AGENTS.md 마커로 opencode 오버레이가 생기던 것 수리 (92c43b19)

## [1.14.1] - 2026-09-29

### Changed

- release(v1.14.1): 발행 완료 — 태그 push + GitHub Release(asset 4종) + wheel 격리 실측 + §2.8 + #29 close (151fa7ac)
- release(v1.14.1): 발행 준비 — minimax-code 경로 불일치(#29) + backlog-update 이월 kind 수리 (9e5ccadf)

## [1.14.0] - 2026-09-29

### Changed

- release(v1.14.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + wheel 격리 실측 + §2.8 (8b434f4b)
- release(v1.14.0): 발행 준비 — Antigravity MCP 도구 11종 거부 수리 + doctor plugin_enabled 4채널 (188bb9b7)

## [1.13.0] - 2026-09-28

### Changed

- release(v1.13.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + wheel 격리 실측 (756a181e)
- release(v1.13.0): 발행 준비 — v1.12.0 에서 예고한 은퇴 API 제거 + telemetry 오염 수리 (1f16e431)

## [1.12.0] - 2026-09-28

### Changed

- release(v1.12.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + wheel 격리 실측 (18790f49)
- release(v1.12.0): 발행 준비 — CI 를 걷고 로컬 게이트를 근거로 세운 사이클 + 세션 시작 컨텍스트 예산 (c26c92f8)

## [1.11.0] - 2026-09-23

### Changed

- release(v1.11.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + wheel 격리 실측 (14f10cfc)
- release(v1.11.0): 발행 준비 — 판정이 아무것도 재지 않는데 숫자는 멀쩡했던 사이클 (eb8152ac)

## [1.10.0] - 2026-09-22

### Changed

- release(v1.10.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + wheel 격리 실측 (138304ac)
- release(v1.10.0): 발행 준비 — 게이트가 무엇을 재고 있었는지 다섯 번 뒤집은 사이클 (1a8e5c8b)

## [1.9.4] - 2026-09-07

### Changed

- release(v1.9.4): 발행 완료 — 태그 push + GitHub Release(asset 4종) + 이 호스트 채널 재적용 (0facde38)
- release(v1.9.4): 발행 준비 — 매 세션 보고되던 지표가 사실 고장 나 있었다 (51ab7cb2)

## [1.9.3] - 2026-09-07

### Changed

- chore(memory): v1.9.3 발행 + 이 호스트 소비자 채널 재적용 기록 (main-008) (9733d55e)
- release(v1.9.3): 발행 완료 — 태그 push + GitHub Release(asset 4종) + post-step 정합 (74995741)
- release(v1.9.3): 발행 준비 — 소비자 배포처 모순의 뿌리를 닫는다 (6b3c070e)

## [1.9.2] - 2026-09-04

### Changed

- chore(memory): v1.9.2 소비 채널 재적용 기록 (main-002) (f7796bdf)
- release(v1.9.2): 발행 완료 — 태그 push + GitHub Release(asset 4종) + post-step 정합 (cde2d0ef)
- release(v1.9.2): 발행 준비 — 발행 절차의 손질 두 자리 제거 (c5634267)

## [1.9.1] - 2026-09-03

### Changed

- chore(memory): v1.9.1 소비 채널 배포 기록 (96f5f386)
- release(v1.9.1): 발행 완료 — 태그 push + GitHub Release(asset 4종) + post-step 정합 (10f41465)
- release(v1.9.1): 발행 준비 — 불일치 경고 오탐 제거 (ea40d1d3)

## [1.9.0] - 2026-09-02

### Changed

- release(v1.9.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + post-step 정합 (573fa786)
- release(v1.9.0): 발행 준비 — 필수 CI 게이트 + done 강등 보존 (ff7ed4bc)

## [1.8.1] - 2026-09-01

### Changed

- release(v1.8.1): 발행 완료 — 태그 push + GitHub Release(asset 4종) + post-step 정합 (54ff793e)
- docs(release): v1.8.1 회귀 표 행 + 세션 기준선 갱신 (3afb48f8)
- release(v1.8.1): 발행 준비 — 패키징 결함 수리 + 스탬프 판정 git 파생 (abb10744)

## [1.8.0] - 2026-09-01

### Changed

- release(v1.8.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + post-step 정합 (main-005) (236a6aa9)
- release(v1.8.0): 발행 준비 — 지원 하네스 개편 + 탐침 침묵 제거 사이클 (main-005) (7489fe35)

## [1.7.0] - 2026-08-28

### Changed

- release(v1.7.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + 파생물 정합 (main-010) (a69d83bf)
- release(v1.7.0): 발행 준비 — meta-watch 축, 등급은 §1.5 판정으로 minor (d3fa719b)
- release(v1.7.0): bump 1.6.0→1.7.0 + main-009 close (mcp 2.1.1 수리 CI green) (cac3af1e)

### Fixed

- fix(checks): v1.7.0 post-step 스탬프 반영 — EXPECTED_LAST_UPDATED 08-25→08-28 (4d7a78da)

## [1.6.0] - 2026-08-28

### Changed

- chore(release-note): v1.6.0 누적 smoke 수치 274→275 (check_meta_watch 신설 반영) (2c998a3e)
- release(v1.6.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + 파생물 정합 (main-021) (ba7af58f)
- release(v1.6.0): 발행 준비 — Windows 플랫폼 결함 축, 등급은 §1.5 판정으로 minor (62953fb8)

## [1.5.0] - 2026-08-25

### Changed

- release(v1.5.0): 파생물 정합 2차 — bump 후 낡은 버전 스탬프 전수 갱신 (CI red 수리) (9feabcd8)
- release(v1.5.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + 파생물 정합 (main-014) (9e7b2645)
- release(v1.5.0): 발행 준비 — ADR-027 로드맵 층 사이클, 등급은 §1.5 4문항으로 minor (8520dc13)

## [1.4.0] - 2026-08-24

### Changed

- release(v1.4.0): 발행 완료 — 태그 push + GitHub Release + 파생물 정합 (main-005 close) (7343bddd)
- release(v1.4.0): 16 커밋 누적분 발행 준비 — 등급은 §1.5 4문항으로 minor (main-005) (7fa37940)
- chore(backlog): v1.4.0 릴리스 task 등록 — 등급 판단 근거 기록 (main-005) (e346243f)

## [1.3.0] - 2026-08-20

### Changed

- docs(release): v1.3.0 노트의 태그 표기를 RELEASE.md §2.2 규약에 맞춘다 (1f33a958)
- release(v1.3.0): 101 커밋 누적분 발행 준비 + 버전 등급 판단 기준 정본화 (main-007) (c61b2237)

## [1.1.6] - 2026-08-10

### Changed

- docs(release): v1.1.6-beta 발행 후처리 (TASK-2026-08-10-main-015) (c51d973e)
- chore(release): v1.1.6-beta 준비 — 노트 + 파생물 선재생성 + stamp (TASK-2026-08-10-main-015) (25e09d4a)

## [1.1.5] - 2026-08-10

### Changed

- docs(release): v1.1.5-beta 발행 후처리 + 세션 close memory (4e68c2e8)
- chore(release): v1.1.5-beta 준비 — 노트 + 파생물 선재생성 + stamp (6e77c14e)

## [1.1.4] - 2026-08-10

### Changed

- docs(release): v1.1.4-beta 발행 후처리 + 세션 close memory (ea7687be)
- chore(release): v1.1.4-beta 준비 — 노트 + stamp 정합 (7a12490a)

### Fixed

- fix(release): v1.1.4 파생물 재생성 — 릴리스 직후 전량 재실행이 잡은 9건 (890521f5)

## [1.1.3] - 2026-08-10

### Changed

- docs(memory): v1.1.3-beta 발행 기록 + 릴리스 파이프라인 후속 2건 (e956f221)
- chore(release): v1.1.3-beta 준비 — 노트 + version bump + stamp (6cadcca1)

## [1.1.2] - 2026-08-09

### Changed

- docs(memory): v1.1.2-beta 발행 기록 + 릴리스 도구 결함 2건 (74161f89)
- chore(release): v1.1.2-beta — federation 쓰기 / wk dispatcher / 3rd layer / drift v2 (b688a065)

## [1.1.1] - 2026-08-08

### Changed

- docs(memory): v1.1.1-beta release 반영 — baseline + current_axis 갱신 (678806f2)
- chore(release): v1.1.1-beta — [project.scripts] 29 entry points (CLI 化 A안) (6b92a602)

## [1.1.0] - 2026-08-11

### Changed

- docs(memory): v1.1.0·v1.1.1 노트 누적 표기 미삽입 확정 — backlog 14건 종결 (TASK-2026-08-11-main-014) (5e6ca22a)
- docs(memory): v1.1.0-beta release 반영 — baseline + current_axis + handoff 갱신 (02f80f29)
- chore(release): v1.1.0-beta — §0.8 4건 close + dual mode CLI + federation *읽기* (564ce36b)

## [1.0.0] - 2026-07-22

### Changed

- docs(memory): v1.0.0 사이클 close-out — task SSOT 3건 + 세션 + state.json 재생성 (3f017a2b)
- docs(v1.0.0): 릴리스 노트 §2.15 — auto-bump dry-run 결함 (릴리스 후 발견) 기록 (08391f26)
- docs(v1.0.0): 릴리스 노트 확정 — 보류/초안 → 릴리스, 본 사이클 해소 내역 §2.9~2.14 추가 (2e6ae449)
- docs(v1.0.0): dashboard snapshot + CHANGELOG 재생성 + 검증 수치 실측 정합 (17c3cb63)
- docs(v1.0.0): smoke 카운트 199 정합 + 릴리스 노트 검증 섹션 실측 기록 (5c690b97)
- chore(v1.0.0): version bump 1.0.0 + 버전 스탬프 정합 + Phase 13 진입 (릴리스 미완) (e574bf9d)
- docs(v1.0.0): Gate 1 ✅ PASS — Panel 5 items_total=11 (Break Point #1 close-out) (6e24b81d)

## [0.15.21] - 2026-07-21

### Added

- feat(release): v0.15.21 — Phase 13 follow-up 1차 (AC2 telemetry 다양성 + CHANGELOG lockdown) (8a93afa4)

### Changed

- chore(dashboard): v0.15.21 post-release snapshot refresh (37233c9f)

## [0.15.20] - 2026-07-20

### Fixed

- fix(release): v0.15.20 — v1.0.0 pre-release final (stable API + SemVer 2-year guarantee) (ab202d8c)

## [0.15.19] - 2026-07-20

### Fixed

- fix(release): v0.15.19 — cross-panel final 정합 (v1.0.0 pre-release anchor) (0d871478)
- fix(release): v0.15.19 — cross-panel final 정합 (v1.0.0 pre-release anchor) (271f96b8)

## [0.15.18] - 2026-08-10

### Changed

- chore(tests): v0.15.18 dummy wrapper 물리 제거 — 153개/60파일 (TASK-2026-08-10-main-007) (f7b5217e)

### Fixed

- fix(test): v0.15.18 — TST-WF-01 historical smoke 보강 + v1.0.0 Break Point #2 해소 (e5225a9c)
- fix(test): v0.15.18 — TST-WF-01 historical smoke 보강 + v1.0.0 Break Point #2 해소 (a5c0cfcb)

## [0.15.16] - 2026-07-20

### Added

- feat(harness): v0.15.16 — Grok Build (xAI CLI TUI) 11번째 harness + cross-check discipline anchor 확장 (v0.15.16~v0.15.19) (370cb237)
- feat(harness): v0.15.16 — Grok Build (xAI CLI TUI) 11번째 harness + cross-check discipline anchor 확장 (v0.15.16~v0.15.19) (dc64d2fe)
- feat(harness): v0.15.16 — Grok Build (xAI CLI TUI) 11번째 harness + cross-check discipline anchor 확장 (v0.15.16~v0.15.19) (fc834d1f)

### Changed

- chore(release): v0.15.16 정식 release — Beta note 신규 + version bump (09825f35)

## [0.15.15] - 2026-07-18

### Changed

- docs(release): v0.15.15 정식 release 정합 + Beta-v0.10.4 release note 신규 (d9aa69ef)
- chore(release): v0.15.15 정식 version bump (94a0174a)
- docs(planning): v0.15.15 baseline + draft → stable 격상 + maturity last_updated 갱신 (b3db12ce)
- docs(release): v0.15.15 baseline + 회귀 표 + PROJECT_PROFILE canonical path 반영 (37650331)
- docs(quickstart): v0.15.15 QUICKSTART.md cross-check smoke + 2 in-scope issue 정정 (3d59da88)

## [0.15.14] - 2026-07-17

### Changed

- docs(install): v0.15.14 INSTALLATION_AND_USAGE.md cross-check smoke + stale text 정정 (e1e0a54a)

## [0.15.13] - 2026-07-17

### Added

- feat(harness): v0.15.13 Harness apply_guide.md content cross-check smoke (56c39919)

## [0.15.12] - 2026-07-17

### Changed

- docs(readme): v0.15.12 README.md cross-check smoke + stale text 정정 (4dce84d3)

## [0.15.11] - 2026-07-17

### Fixed

- fix(release): v0.15.11 sample tool_version housekeeping + 3-way cross-check smoke (586424f8)

## [0.15.10] - 2026-07-17

### Changed

- docs(adr): v0.15.10 MICROSOFT_MEMORA_EVALUATION close-out — Memora-inspired metadata 도입 종결 (0ad13bd9)

## [0.15.9] - 2026-07-17

### Added

- feat(harness): v0.15.9 Harness verification smoke — 10 harness cross-check discipline anchor (2fd858e9)

## [0.15.8] - 2026-07-17

### Added

- feat(dashboard): v0.15.8 Panel 1+2 maturity_distribution cross-validation smoke (cb468740)

## [0.15.7] - 2026-07-17

### Added

- feat(dashboard): v0.15.7 Panel 3 memory_index cross-validation smoke (b5901b5f)

## [0.15.6] - 2026-07-17

### Added

- feat(dashboard): v0.15.6 Panel 6/8 telemetry cross-validation smoke (c0bce15f)

## [0.15.5] - 2026-07-17

### Added

- feat(dashboard): v0.15.5 Panel 4 cross-validation smoke — cross-check discipline anchor (5c13c7b9)

## [0.15.4] - 2026-07-17

### Changed

- docs(adr): v0.15.4 ADR-007 close-out — 3rd deprecation cycle accepted no-op (861267ce)

## [0.15.3] - 2026-07-17

### Added

- feat(release): v0.15.3 release_error 시에만 maturity refresh (v0.14.6 out-of-scope 2 해소) (5cec8e84)

## [0.15.2] - 2026-07-17

### Added

- feat(release): v0.15.2 legacy_memory strict opt-out + v0.15.1 dashboard 정합 (단일 commit) (a4749f39)

## [0.15.1] - 2026-07-17

### Fixed

- fix(dashboard): v0.15.1 Panel 4 SMOKE_COUNT_PATTERN N+ 표기 parse + 8 panel 정합 (abe071eb)

## [0.15.0] - 2026-07-17

### Added

- feat(memory): v0.15.0 ⚠️ BREAKING — 2nd deprecation cycle 종결 (work_backlog.md.bak drop) (d7109ef8)

### Changed

- chore(state): v0.15.0 ⚠️ BREAKING push + audit fix memory cycle (2aed584e)
- chore(release): v0.15.0 push prep — README header sync, drift G2 fix, panel 7 stage branch (b31beb2a)

## [0.14.7] - 2026-07-16

### Added

- feat(dashboard): v0.14.7 HTML renderer Panel 6/7/8 + Panel 6 git reflog (Phase 15 follow-up) (3a274808)

## [0.14.6] - 2026-07-16

### Added

- feat(workflow): v0.14.6 refresh-maturity dispatcher + cmd_release auto-wire (Task 3 follow-up) (d8eeae77)

## [0.14.5] - 2026-07-16

### Added

- feat(memory): v0.14.5 2nd deprecation cycle 시작 — --legacy-memory flag (49ac3f7b)

## [0.14.3] - 2026-07-16

### Added

- feat(dashboard): v0.14.3 Phase 15 신규 Panel 6/7/8 (north-star + deprecation + telemetry) (ec9d3890)

## [0.14.2] - 2026-07-16

### Added

- feat(mcp): v0.14.2 MCP 2nd batch stable — apply_robust_patch (쓰기 MCP 정공법) (5602f631)

## [0.14.1] - 2026-07-16

### Added

- feat(mcp): v0.14.1 MCP 1st batch stable + workflow_log_rotator 정리 (Phase 14 MCP close-out) (27d21786)
- feat(memory): v0.14.1 deprecation cycle 1st 종결 — .bak deprecation warning emit (3afb9ef9)

## [0.14.0] - 2026-07-16

### Added

- feat(dashboard): v0.14.0 Panel 1 freshness 보강 — maturity_last_updated stale warning + helper (2c52c590)
- feat(memory): v0.14.0 67-file path string 갱신 + governance layout 명세 (Phase 14 AC3 close-out) (104d028a)
- feat(memory): v0.14.0 builder/cache 신규 layout 입력 확장 (Phase 14 AC2 close-out) (5a6b0692)
- feat(memory): v0.14.0 1st deprecation cycle — append-only + rebuild layout (Phase 14 AC1 close-out, 93 entries split) (8c53c4a1)

### Changed

- docs(release): v0.14.0 Phase 14 close-out — Beta release note + daily backlog (22b3eeb6)
- chore(release): v0.14.0 housekeeping — version bump + sample regen + dashboard refresh (3ade29d4)
- test(memory): v0.14.0 신규 smoke check_appendonly_memory_layout.py 6/6 (Phase 14 AC4 close-out) (5549d7c5)

## [0.13.0] - 2026-07-09

### Added

- feat(dashboard): v0.13.0-beta HTML snapshot (GitHub Pages publish) (b55fcad2)
- feat(dashboard): v0.13.0~2 quality dashboard — 5 panel data + CLI + drift guard inline + HTML renderer (b7811686)
- feat(dashboard): v0.13.0~2 quality dashboard — 5 panel data + CLI + drift guard inline + HTML renderer (3a81281c)

### Changed

- chore(release): v0.13.0-beta dashboard snapshot (auto-emit) (772ae091)

## [0.11.25] - 2026-07-03

### Added

- feat(mcp): stdio-sdk 정식 stable 승격 (v0.11.25) (b8d7bdea)

## [0.11.24] - 2026-07-03

### Added

- feat(skill): git-conflict-resolver --apply 구현 + 11/11 stable milestone (v0.11.24) (b227656b)
- feat(skill): automated-repro-scaffold + git-conflict-resolver stable/beta 승격 (v0.11.24) (ac7c17ba)

## [0.11.22] - 2026-07-02

### Changed

- chore(state): v0.11.22 release memory cycle — 8 phase + ADR-006 retrospective anchor + 3 skill wiring 3/3 (ea013a26)
- chore(state): v0.11.22 ADR-006 retrospective 자리 memory cycle (a42cf61e)
- chore(state): v0.11.22 Phase 3d backlog-update wiring memory cycle (skill wiring 3/3 완료) (d89beae7)
- chore(state): v0.11.22 Phase 3c doc-sync wiring memory cycle (a5987063)
- chore(state): v0.11.22 Phase 3b1 session-start wiring memory cycle (01ed22d9)
- chore(state): v0.11.22 Phase 3 dispatcher entry memory cycle (2cc61798)
- chore(state): v0.11.22 Phase 2b BM25 fallback memory cycle (c90bde1e)
- chore(state): v0.11.22 Phase 2 --merge opt-in memory cycle (a712c957)
- chore(state): v0.11.22 Phase 1.5 state.json hook memory cycle (fa0ac324)
- chore(state): v0.11.22 ADR-005 Phase 1 prototype memory cycle (348048ca)

## [0.11.21] - 2026-07-02

### Changed

- chore(state): v0.11.21 release memory cycle (b378284e)

## [0.11.20] - 2026-07-01

### Changed

- chore(state): v0.11.20 release memory cycle (a6c76bdc)

## [0.11.19] - 2026-07-01

### Changed

- chore(state): v0.11.19 release memory cycle (143d2d3d)

## [0.11.18] - 2026-07-01

### Changed

- chore(state): v0.11.18 release memory cycle (dfafdc4b)
- chore(state): v0.11.18 release memory cycle (df506ed2)

## [0.11.17] - 2026-06-30

### Changed

- chore(state): v0.11.17 release memory cycle (4d991e84)
- chore(v0.11.17): version bump + release note — mypy strict cumulative 25 error 격상 + schema drift housekeeping (3d3387de)

## [0.11.16] - 2026-06-27

### Added

- feat+chore(v0.11.16): cmd_release_status --auto-bump flag (read-only → opt-in write) (d81c6397)

## [0.11.15] - 2026-06-26

### Added

- feat+chore(v0.11.15): release summary 1-line (jq-friendly verdict) (9ae46829)

## [0.11.14] - 2026-06-26

### Added

- feat+chore(v0.11.14): release-status dispatcher (신규 module mypy strict clean 2-layer defense 실증) (ed5148a1)

## [0.11.13] - 2026-06-26

### Added

- feat+chore(v0.11.13): mypy CI cross-verify (Layer 1 ↔ Layer 2 정합 advisory) (b3075efa)

## [0.11.12] - 2026-06-26

### Added

- feat+chore(v0.11.12): mypy strict release-time gate (cmd_release pre-check 확장) (731b2029)

## [0.11.11] - 2026-06-26

### Added

- feat+chore(v0.11.11): mypy strict CI 통합 (GH Actions mypy-strict workflow) (0994f147)

## [0.11.10] - 2026-06-26

### Changed

- chore(v0.11.10): mypy strict 단계적 격상 25-26단계 (project_docs + profiling) — FULL STRICT 도달 (b73799b8)

## [0.11.9] - 2026-06-26

### Changed

- chore(v0.11.9): mypy strict 단계적 격상 23-24단계 (testing + runner) (41ef022c)

## [0.11.8] - 2026-06-26

### Changed

- chore(v0.11.8): mypy strict 단계적 격상 21-22단계 (read_only_mcp_sdk + workflow_writes) (ae4058ad)

## [0.11.7] - 2026-06-26

### Changed

- chore(v0.11.7): mypy strict 단계적 격상 19-20단계 (workflow_kit_cli + doc_sync) (5c82bc3a)

## [0.11.6] - 2026-06-26

### Changed

- chore(v0.11.6): mypy strict 단계적 격상 17-18단계 (session_outputs + read_only_bundle) (c82bf72c)

## [0.11.5] - 2026-06-26

### Changed

- chore(v0.11.5): mypy strict 단계적 격상 15-16단계 (decorators + linter) (1a7e6658)

## [0.11.4] - 2026-06-26

### Changed

- chore(v0.11.4): mypy strict 단계적 격상 13-14단계 (output_contracts + milestones) (6f6bf38a)

## [0.11.3] - 2026-06-26

### Changed

- chore(v0.11.3): mypy strict 단계적 격상 11-12단계 (purpose_ingest + purpose_graph) (bfbd1001)

## [0.11.2] - 2026-06-26

### Added

- feat+chore(v0.11.2): cycle 4 deferred 통합 (graph_insights schema + 3 skill context load) (372b153c)

## [0.11.1] - 2026-06-26

### Added

- feat+chore(v0.11.1): graph insights (R-A follow-up cycle 4) (fef6374a)

## [0.11.0] - 2026-06-26

### Added

- feat+chore(v0.11.0): two-step CoT ingest (R-A follow-up cycle 3) (f71dde8e)

### Changed

- docs(v0.11.0): plan two-step CoT ingest (R-A follow-up cycle 3) (f4eeba23)

## [0.10.4] - 2026-07-03

### Added

- feat: CodeWhale harness support (v0.10.4) - HARNESS_SPECS+SUPPORTED_HARNESSES+builder registration - single SKILL.md overlay (Constitution handles verification/parallelism/context) - additive rules only: session start, Korean output, backlog mgmt - harness docs + apply guide + distribution spec (cf0060d6)

## [0.10.3] - 2026-06-24

### Added

- feat+chore(v0.10.3): wiki file deletion cascade cleanup (R-A follow-up cycle 2) (3ca3a497)

## [0.10.2] - 2026-06-24

### Added

- feat+chore(v0.10.2): delivery layer 확장 (claude-code 진입점 정정 + aider/goose/custom + self-bootstrap) (c657853a)

## [0.10.1] - 2026-06-24

### Added

- feat+chore(v0.10.1): skill-only entry mode + claude-code adapter (SemVer minor) (afccdab3)

## [0.10.0] - 2026-06-24

### Added

- feat+chore(v0.10.0): deprecation 1st + 2nd cycle 동시 종료 (SemVer major) (c5fb94c5)

## [0.9.6] - 2026-06-24

### Added

- feat+chore(v0.9.6): R-A follow-up part 3 (wiki-event-sync R-A trigger) (09282b0e)

## [0.9.5] - 2026-06-24

### Added

- feat+chore(v0.9.5): R-A follow-up part 2 (skill context load integration) (96f97152)

## [0.9.4] - 2026-06-19

### Added

- feat+chore(v0.9.4): R-A follow-up part 1 (state.json.purpose_digest 1-line 자동 생성) (48a3380e)

## [0.9.3] - 2026-06-19

### Added

- feat+chore(v0.9.3): deprecation 2nd cycle (build_default_sources_v4) (7e38e6f5)

## [0.9.2] - 2026-06-19

### Added

- feat+chore(v0.9.2): purpose.md concept 흡수 (외부 reference 차용 정공법 1차 적용) (51e7becd)

## [0.9.1] - 2026-06-18

### Added

- feat+chore(v0.9.1): mypy workflow_kit_cli strict + release --full-auto + deprecation contract (50c688f8)

## [0.9.0] - 2026-06-18

### Added

- feat+chore(v0.9.0): spec drift patch + release note + Phase 11 close (a1f8463f)
- feat(v0.9.0): deprecation 1st cycle - phishing_federation_v4 DeprecationWarning (bf03b95e)

## [0.8.15] - 2026-06-17

### Added

- feat+chore(v0.8.15): release-dist 1-command + housekeeping (spec §9 9/12) (841329ff)

## [0.8.0] - 2026-06-17

### Added

- feat(v0.8.0): Stable API frozen + mypy strict + generated JSON Schema SSOT (5042df1c)

### Fixed

- fix: v0.8.0 hotfix + v0.8.8 mypy strict 4 file + v0.8.9 dispatcher 29/30 + release_pipeline SSOT (fcb4e8b6)

## [0.7.59] - 2026-06-17

### Added

- feat(v0.7.59): cmd_consumer_metrics in-process refactor (dispatcher 27 정합) (f2b92cfb)

## [0.7.58] - 2026-06-17

### Added

- feat(v0.7.58): consumer feedback metrics tool + dispatcher subcommand 27 (38fe32ae)

### Changed

- merge: v0.7.58 release (757d51b5)
- merge: v0.7.58 release (bcc0e99a)
- chore(v0.7.58): version bump 0.7.57 → 0.7.58 + release note + state sync (1c7d8e95)

### Fixed

- fix(state): v0.7.58 chore commit hash 동기화 (1c7d8e9) (d0c7c538)

## [0.7.57] - 2026-06-16

### Added

- feat(v0.7.57): mkdocs cross-link audit + 1 broken link fix (cbcaaadc)
- feat(v0.7.57): <in-memory> cleanup + dispatcher 23 → 26 (cache format interop) (ec1223c5)

### Changed

- merge: v0.7.57 release (364b12ad)
- docs(v0.7.57): v0.7.57 release note + wiki log + memory log (1c83b6f7)
- chore(v0.7.57): .gitignore 에 /site/ 추가 (mkdocs build output) (654e21e6)

## [0.7.56] - 2026-06-16

### Added

- feat(v0.7.56): cache-lfu-decay-persist CSV in-place + dispatcher --inplace (7b4d6b7f)
- feat(v0.7.56): release_pipeline wrapper 7 추가 + dispatcher 16 → 23 (fb6ebc45)
- feat(v0.7.56): score-wiki-trend in-process + dispatcher 16+ (c3ef1255)

### Changed

- merge: v0.7.56 release (6 follow-up 통합) (79ace23a)
- docs(v0.7.56): v0.7.56 release note + wiki log entry (094cc2ce)
- docs(v0.7.56): GH Pages 외부 consumer feedback loop + FEEDBACK.md (1c5c1dfd)
- test(v0.7.56): OKF strict mode lint rule coverage 7 신규 (audit 3차) (58e2ac0d)

## [0.7.55] - 2026-06-16

### Changed

- test(v0.7.55): tools/release_pipeline_lib wrapper test 2 신규 (cmd_validate) (428a2d20)
- docs(wiki): v0.7.55 release entry (release-doctor in-process + cache-migrate split + 3 subcommand L/M/N) (6cda10fe)
- chore(v0.7.55): version bump 0.7.54 → 0.7.55 + release note (0436eb3f)
- test(v0.7.55): tools/release_pipeline_lib wrapper test 2 신규 (cmd_validate) (3ba61e87)
- refactor(v0.7.55): release-doctor in-process + cache-migrate LRU/LFU split + 3 subcommand (14 subcommand) (4b64b206)

## [0.7.54] - 2026-06-16

### Added

- feat(v0.7.54): workflow_kit_cli — okf-validate / cache-migrate / release-doctor (11 subcommand) (97adc0c8)

### Changed

- docs(wiki): v0.7.54 release entry (dispatcher 11 subcommand: I/J/K) (0d976d00)
- chore(v0.7.54): version bump 0.7.53 → 0.7.54 + release note (58fbb326)
- test(v0.7.54): dispatcher test 4 신규 (okf-validate × 2 + cache-migrate + release-doctor) (cde0a45b)

## [0.7.53] - 2026-06-16

### Added

- feat(v0.7.53): mkdocs 셋업 (GH Pages in-repo, public-facing consumer guide) (fda611b6)
- feat(v0.7.53): workflow_kit_cli — okf-export / okf-import subcommand 추가 (a9109882)

### Changed

- docs(wiki): v0.7.53 release entry (3 follow-up: F dispatcher + G audit + H mkdocs) (4af30bb7)
- chore(v0.7.53): version bump 0.7.52 → 0.7.53 + release note (3d7e232e)
- test(v0.7.53): url_validity test file 추가 (12 test, audit 2차 갭 해소) (05629312)

## [0.7.52] - 2026-06-16

### Added

- feat(v0.7.52): cache analytics snapshot diff (1/1 PASS) (f4adf8cc)
- feat(v0.7.52): cache analytics alerting CLI (--alert, zero-dep, 2/2 PASS) (fbbd2549)

### Changed

- docs(wiki): v0.7.52 release cut supersedes prior audit decision (ee59070d)
- chore(v0.7.52): version bump 0.7.6 → 0.7.52 + release note (b0491d05)
- docs(v0.7.52): log entry for retrospective consolidation cleanup (ee63739c)
- refactor(v0.7.52): collapse 6 CLI modules into workflow_kit_cli dispatcher (6/6 PASS) (71bf15da)
- refactor(v0.7.52): inline v_r13_commit_diff_integration + v_r13_layer2_pipeline into v_r13_commit_diff (6/6 PASS) (25c7c1a9)
- refactor(v0.7.52): consolidate cache_dashboard_export into cache_dashboard module (87f77bdd)
- refactor(v0.7.52): remove v2/v3/v4/v5 federation module + test files (081b72cc)
- refactor(v0.7.52): consolidate phishing_federation_v2/v3/v4/v5 into one module (4/4 PASS) (0d5a2c73)

## [0.7.51] - 2026-06-16

### Added

- feat(v0.7.51): phishing federation v5 CLI (--federate-v5, 2/2 PASS, FREE tier) (85be71c0)
- feat(v0.7.51): cache dashboard export CLI (--dashboard-export --output=PATH, 2/2 PASS) (88106953)
- feat(v0.7.51): cache trend chart CLI (--trend-chart --snapshots=PATH, 2/2 PASS) (4c579adc)
- feat(v0.7.51): LFU decay score automatic aging (decay_age_scores, 2/2 PASS, no regression) (42475898)
- feat(v0.7.51): cache analytics threshold-based alerting (2/2 PASS) (51868363)

### Changed

- release(v0.7.51): cache alerting + decay aging + trend chart CLI + dashboard export CLI + federation v5 CLI (201/201 PASS, FREE tier) (22541e23)

## [0.7.50] - 2026-06-16

### Added

- feat(v0.7.50): LFU decay score CSV export/import (cross-process, 2/2 PASS, no regression) (17e9da96)
- feat(v0.7.50): phishing federation v5 (3 source weighted voting, FREE-tier 3rd source, 2/2 PASS) (5057e774)
- feat(v0.7.50): cache dashboard HTML export (2/2 PASS, no regression) (24939df2)
- feat(v0.7.50): cache trend ASCII chart (zero-dep visualization, 2/2 PASS) (7e41eaaf)
- feat(v0.7.50): V-R13 layer 2 CLI (one-call URL verification, 2/2 PASS) (5b6c6f62)

### Changed

- release(v0.7.50): layer 2 CLI + trend ASCII chart + dashboard HTML + federation v5 + decay CSV (191/191 PASS) (00d2de4e)

## [0.7.49] - 2026-06-16

### Added

- feat(v0.7.49): cache dashboard export (JSON + Markdown, 2/2 PASS) (5834a9a7)
- feat(v0.7.49): cache analytics trend (snapshot over time, 2/2 PASS) (00a255d4)
- feat(v0.7.49): V-R13 layer 2 full pipeline (one-call parse+dispatch+format, 2/2 PASS) (5726fc07)
- feat(v0.7.49): per-URL LFU decay score persistence (cache_lfu_decay_persist, 2/2 PASS) (d9e050be)
- feat(v0.7.49): phishing federation v4 (weighted voting, 2/2 PASS) (bd7c8cb3)

### Changed

- release(v0.7.49): federation v4 + decay persistence + layer 2 pipeline + cache trend + dashboard export (181/181 PASS) (4093fcc6)

## [0.7.48] - 2026-06-16

### Added

- feat(v0.7.48): CLI --cache-dashboard flag (cache_dashboard_cli module, 2/2 PASS) (83ee37a5)
- feat(v0.7.48): phishing federation v3 (cross-source verification, 2/2 PASS) (ffacc800)
- feat(v0.7.48): per-strategy cache dashboard (cache_dashboard module, 2/2 PASS) (6d9ca13d)
- feat(v0.7.48): LFUConfig + _save_cache full refactor (save_cache_lfu_decay_full, 2/2 PASS) (d27004f5)
- feat(v0.7.48): V-R13 layer 2 commit-level diff integration (2/2 PASS) (9461ed14)

### Changed

- release(v0.7.48): V-R13 commit diff integration + LFU full refactor + cache dashboard + federation v3 + CLI flag (171/171 PASS) (74e3d596)

## [0.7.47] - 2026-06-16

### Added

- feat(v0.7.47): per-strategy eviction trigger by size cap (evict_lru/lfu_over_size, 2/2 PASS) (1c928751)
- feat(v0.7.47): per-strategy cross-strategy analytics (cache_analytics module, 2/2 PASS) (90f83fb9)
- feat(v0.7.47): LFUConfig + _save_cache direct integration (cache_lfu_decay module, 2/2 PASS) (1a606eac)
- feat(v0.7.47): V-R13 layer 2 commit-level diff (cross-vendor, 2/2 PASS) (75be24c9)

### Changed

- release(v0.7.47): V-R13 commit diff + LFU decay + ADR formal + analytics + eviction trigger (159/159 PASS) (a4e1522c)
- docs(v0.7.47): ADR-023/024/025 revision log v0.2.1 (1 release cycle 운영 evidence) (14753748)

## [0.7.46] - 2026-06-16

### Added

- feat(v0.7.46): multi-source phishing federation v2 (extensible, 2/2 PASS) (e7a5919a)
- feat(v0.7.46): Bitbucket v2 API commit history support (2/2 PASS) (cff0f2c4)
- feat(v0.7.46): LFUConfig + temporal decay integration (4/4 PASS) (d5b1ddc5)
- feat(v0.7.46): per-strategy cache size comparison (2/2 PASS) (0dffe7fe)

### Changed

- release(v0.7.46): CLI test fix + cache size + LFU decay + Bitbucket v2 + federation v2 (149/149 PASS) (92d9c2d0)
- test(v0.7.46): CLI --per-strategy + --cache-stats-strategy flag tests (2/2 PASS) (f4f02000)

## [0.7.45] - 2026-06-16

### Added

- feat(v0.7.45): CLI --per-strategy + --cache-stats-strategy flags (V-R10 v4) (c01d4f64)
- feat(v0.7.45): cache_stats_per_strategy_with_hit_rate (39/39 PASS) (1fde081a)
- feat(v0.7.45): LRU/LFU split in cache_migration (split_to_per_strategy, 2/2 PASS) (5073cf74)
- feat(v0.7.45): multi-source phishing federation (PhishTank + OpenPhish, 2/2 PASS) (6533a4db)

### Changed

- release(v0.7.45): multi-source phishing federation + LRU/LFU split + hit rate + CLI --per-strategy (137/137 PASS) (43a03227)
- docs(v0.7.45): OKF quick-start walkthrough output examples + verification table (227e1e8e)

## [0.7.44] - 2026-06-16

### Added

- feat(v0.7.44): cache_migration module (migrate v0.7.41 -> per-strategy, 1/1 PASS) (67265778)
- feat(v0.7.44): OpenPhish API integration (fetch_openphish_feed, 2/2 PASS) (27793aff)
- feat(v0.7.44): lfu_integration module (LFUConfig + _save_cache, 2/2 PASS) (8eb116cc)

### Changed

- release(v0.7.44): ADR-025 formal + OKF quick-start + LFUConfig + OpenPhish + cache migration (134/134 PASS) (d107dd38)

## [0.7.43] - 2026-06-16

### Added

- feat(v0.7.43): lfu_config module (V-R10 v3 LFU threshold tuning, 2/2 PASS) (53f774a8)
- feat(v0.7.43): cache_stats_per_strategy (cross-strategy compare, 39/39 PASS) (e289b198)
- feat(v0.7.43): PhishTank API integration (fetch_phishtank_feed, 13/13 PASS) (df088ee8)

### Changed

- release(v0.7.43): ADR-023/024 formal + ADR-025 quick-start draft + PhishTank API + cache_stats_per_strategy + lfu_config (129/129 PASS) (62a6507a)

## [0.7.42] - 2026-06-16

### Added

- feat(v0.7.42): per-strategy cache file (cache_file_for_strategy helper, 38/38 PASS) (e80cca83)
- feat(v0.7.42): R-2 audit precise (git log --oneline, 16/16 PASS) (386d68ce)
- feat(v0.7.42): V-R13 check 5 per-host extension (GitLab + Bitbucket API, 25/25 PASS) (64ca96c5)

### Changed

- release(v0.7.42): ADR-023/024 formal + V-R13 per-host + V-R12 composite + R-2 audit precise + per-strategy cache (124/124 PASS) (f592bff8)
- test(v0.7.42): V-R12 layer 1+2 composite URL emission (18/18 PASS) (77b0b873)

## [0.7.41] - 2026-06-16

### Added

- feat(v0.7.41): V-R12 composite layer 1+2 verification (check_url_semantic_composite, 23/23 PASS) (6a480aca)
- feat(v0.7.41): R-2 batch compliance audit (audit_r2_batch_history, 15/15 PASS) (a595fbb4)
- feat(v0.7.41): V-R10 v3 per-strategy eviction metric (evictions_lru/evictions_lfu, 36/36 PASS) (46b6b7ab)
- feat(v0.7.41): V-R13 ?range=A..B commit-level diff (git diff subprocess, 21/21 PASS) (6fcda94b)

### Changed

- release(v0.7.41): ADR-020/021/022 formal + V-R13 range diff + per-strategy metric + R-2 audit + V-R12 composite (118/118 PASS) (62d6e9a7)

## [0.7.40] - 2026-06-16

### Added

- feat(v0.7.40): R-2 batch compliance warning (5-15 page heuristic, 14/14 PASS) (85ecff60)
- feat(v0.7.40): CLI --semantic/--perform-head/--perform-github flags (18/18 PASS) (f4cf9090)
- feat(v0.7.40): okf_export per-page ?range=<sha>..<sha> emission (V-R12 layer 2, 17/17 PASS) (e365168a)
- feat(v0.7.40): V-R13 full 8/8 check (HEAD + GitHub API, 16/16 PASS) (7c69789f)

### Changed

- release(v0.7.40): ADR-021/022 formal + V-R13 full 8/8 + V-R12 layer 2 + R-2 batch (110/110 PASS) (b98e1eb3)

## [0.7.39] - 2026-06-16

### Added

- feat(v0.7.39): okf_export per-page ?hash=sha256:... emission (ADR-019 layer 1, 16/16 PASS) (dd8c177d)
- feat(v0.7.39): phishing_keywords module + 11 tests (V-R11 v2 PoC, 11/11 PASS) (e1904fd6)
- feat(v0.7.39): LFU eviction strategy + access_count tracking (34/34 PASS) (eab4d2e1)
- feat(v0.7.39): check_url_semantic() PoC (6/8 check, 13/13 PASS) (563ac5c9)

### Changed

- release(v0.7.39): V-R13 PoC + LFU cache + PhishTank + V-R12 carrier (102/102 PASS) (863c3b6e)

## [0.7.38] - 2026-06-16

### Added

- feat(v0.7.38): _CacheLock stale lock file orphan cleanup (32/32 PASS) (9f622d3c)
- feat(v0.7.38): cache gzip compression (4KB threshold, 31/31 PASS) (2e1a541c)
- feat(v0.7.38): okf-bundle.yaml emit (per-bundle vcs_commit + integrity_hash, 15/15 PASS) (c3a0f240)
- feat(v0.7.38): _CacheLock timeout + advisory wait (30/30 PASS) (fbf93b58)
- feat(v0.7.38): per-page frontmatter vcs_commit + vcs_ref (12/12 PASS) (96b6ef04)
- feat(v0.7.38): cache_stats session evictions + last_eviction_timestamp (29/29 PASS) (d06053a6)

### Changed

- release(v0.7.38): V-R13 formal + okf-bundle.yaml + cache gzip + lock orphan + OKF consumer guide (a04cf567)

## [0.7.37] - 2026-06-16

### Added

- feat(v0.7.37): okf_export vcs_commit integration (ADR-018, 11/11 PASS) (2eac0d3a)
- feat(v0.7.37): --body CLI flag + --timeout flag (28/28 PASS) (1da10efa)
- feat(v0.7.37): cache_stats() extension (bytes + evictions_total, 27/27 PASS) (8e88b47f)
- feat(v0.7.37): V-R12 commit-pinned URL (ADR-018 + 3 new tests, 9/9 PASS) (7aec7cf6)
- feat(v0.7.37): V-R11 body content audit (ADR-017 + 5 new tests, 27/27 PASS) (9ec0aad1)
- feat(v0.7.37): GHA actions/cache for cross-PR cache (ADR-016) (6a622ee0)
- feat(v0.7.37): V-R10 v3 file lock (ADR-015 + 2 new tests, 22/22 PASS) (735beac6)
- feat(v0.7.37): V-R10 v3 cache LRU (ADR-014 + 4 new tests, 20/20 PASS) (3349e792)

### Changed

- ci(v0.7.37): --body + --vcs-commit CI integration (f1a7bd39)

## [0.7.36] - 2026-06-16

### Added

- feat(v0.7.36): V-R10 v2 cache (ADR-013 + 4 new tests, 16/16 PASS) (5fec6646)

### Changed

- chore(v0.7.36): version bump v0.7.35 to v0.7.36 + log entry for follow-up bundle (208042dd)
- ci(v0.7.36): .github/workflows/okf-validate.yml (V-R10 online + cache + weekly cron) (c26349f9)

## [0.7.35] - 2026-06-16

### Added

- feat(v0.7.35): V-R10 online HEAD layer (ADR-012 + 6 new tests, 12/12 PASS) (515a352b)
- feat(v0.7.35): ADR-011 + OKF version auto-detect (5 new tests, 12/12 PASS) (e0f2ffc7)
- feat(v0.7.35): ADR-010 + V-R10 URL validity lint (offline 8 check, 6/6 PASS) (077b5a44)

## [0.7.34] - 2026-06-16

### Added

- feat(v0.7.34): bundle root index.md auto-emit + test 10 (10/10 PASS) (2fb014e9)
- feat(v0.7.34): ADR-008 accepted + path_resolver.py PoC + okf_export --no-resolve (24f85898)
- feat(v0.7.34): ADR-007 accepted + workflow_kit/okf_import.py PoC (7/7 PASS) (9e8b06d2)

## [0.7.33] - 2026-06-16

### Added

- feat(v0.7.33): TASK-V0733-001 atomic rotation (3-step crash safety) + TASK-V0734-001 yearly aggregation + 10 smoke (5-run stable) (9648a6e9)

### Changed

- chore(v0.7.33): version bump 0.7.32 → 0.7.33 (auto-sync verified) + Beta-v0.7.33.md + state/work_backlog sync (f3ef05bc)
- chore(v0.7.33): ADR-006 accepted + Beta-v0.7.33 release note + version bump (00942eff)

### Fixed

- fix(state): v0.7.33 2nd hash sync (1c8d54b8)

## [0.7.32] - 2026-06-16

### Added

- feat(v0.7.32): TASK-V0731-001 log rotation + TASK-V0732-001 metrics aggregation + 10 smoke (5-run stable) (75a8b4c4)

### Changed

- chore(v0.7.32): version bump 0.7.31 → 0.7.32 (auto-sync verified) + Beta-v0.7.32.md + state/work_backlog sync (ec723607)

### Fixed

- fix(state): v0.7.32 2nd hash sync (1348a3cf)

## [0.7.31] - 2026-06-16

### Added

- feat(v0.7.31): TASK-V0729-001 run-time metrics + TASK-V0730-001 install-cron idempotency + 10 smoke (a9b510e4)

### Changed

- chore(v0.7.31): version bump 0.7.30 → 0.7.31 (auto-sync verified) + Beta-v0.7.31.md + state/work_backlog sync (6732f488)

### Fixed

- fix(state): v0.7.31 2nd hash sync (fae91573)

## [0.7.30] - 2026-06-15

### Added

- feat(v0.7.30): TASK-V0728-001 archive_stale_memory cron integration (mavis cron create/disable/list) + 5 smoke (57d996db)

### Changed

- chore(v0.7.30): version bump 0.7.29 → 0.7.30 (auto-sync verified) + Beta-v0.7.30.md + state/work_backlog sync (23a20781)

### Fixed

- fix(state): v0.7.30 2nd hash sync (264ab5c9)

## [0.7.29] - 2026-06-15

### Added

- feat(v0.7.29): TASK-V0727-001 post-step 2-phase + amend integration (1 commit 통합, 33% 감소) + 5 smoke (850b7989)

### Fixed

- fix(state): v0.7.29 backlog = 2ee6dbf (본 release 의 fix(state) hash, v0.7.21 정공법) (fda9379f)
- fix(state): v0.7.29 2nd hash sync (68309937)
- fix(v0.7.29): rev-parse 2-step fix (full SHA → short=7) + state.json + backlog 정합 (2ee6dbf4)

## [0.7.28] - 2026-06-15

### Added

- feat(v0.7.28): TASK-V0726-004 detached HEAD memory dir age-based auto-archive + 5 smoke (b1b32f10)

### Fixed

- fix(state): v0.7.28 squash + state.json + backlog = chore commit hash (7bb6259, v0.7.21 정공법) (ca7d385f)

## [0.7.27] - 2026-06-15

### Added

- feat(v0.7.27): TASK-V0726-003 sync_release_hash post-step (release_pipeline.py version-bump auto-call) + 5 smoke (2aa1efa2)

### Fixed

- fix(state): v0.7.27 version-bump + state.json 정합 (v0.7.21 정공법, 2aa1efa = 본 release 의 feat commit) (66c18e7a)
- fix(state): v0.7.27 squash + 본 release 의 본 release 의 hash 정합 (v0.7.21 정공법, 2aa1efa = feat commit) (8ef94d61)

## [0.7.26] - 2026-06-15

### Added

- feat(v0.7.26): F-7 branch detection (detached HEAD → 7-char SHA) + F-7+ automated hash sync (infinite fix(state) loop 회피) + 10 smoke (e5fbd2b6)

### Changed

- chore(v0.7.26): version bump 0.7.25 → 0.7.26 (auto-sync verified) + Beta-v0.7.26.md + state/work_backlog sync (ecb6ce1b)

### Fixed

- fix(state): v0.7.26 squash + 본 release 의 본 release 의 hash 정합 (v0.7.21 정공법, ecb6ce1 = chore commit) (94136978)

## [0.7.25] - 2026-06-15

### Added

- feat(v0.7.25): tools/migrate_legacy_l2.py (F-6 closure, 15 legacy L2 page → in-repo mirror) + 5 smoke (8a61bd34)

### Changed

- chore(v0.7.25): version bump 0.7.24 → 0.7.25 (auto-sync verified) + Beta-v0.7.25.md + state/work_backlog sync (96a919d7)

### Fixed

- fix(state): v0.7.25 본 release hash (96a919d) 로 정합 (v0.7.21 정공법) (00e7ca88)
- fix(state): v0.7.25 hash 동기화 (squash 8 commits → 1) (2f5945db)

## [0.7.24] - 2026-06-15

### Added

- feat(v0.7.24): cmd_release --notes-template flag (5 template: default/detailed/simple/changelog/custom) + 5 smoke (1dfa8fb5)

### Changed

- chore(v0.7.24): version bump 0.7.23 → 0.7.24 (auto-sync verified) + Beta-v0.7.24.md + state/work_backlog sync (2c38d070)

### Fixed

- fix(state): v0.7.24 backlog.commit 을 fix(state) hash(ef13691) 로 동기화 (6e302c14)
- fix(state): v0.7.24 chore commit hash 동기화 (e802e56 → 2c38d07 amend 후 hash) (ef136910)

## [0.7.23] - 2026-06-15

### Added

- feat(v0.7.23): tools/wiki_emit.py 1-command wrapper (3-step cycle: refresh_raw + emit_l2 + reemit_stubs) + 5 smoke (b4936a27)

### Changed

- chore(v0.7.23): version bump 0.7.22 → 0.7.23 (auto-sync verified) + Beta-v0.7.23.md + state/work_backlog sync (8e339402)

### Fixed

- fix(state): v0.7.23 chore commit hash 동기화 (98442d12)

## [0.7.22] - 2026-06-15

### Changed

- chore(v0.7.22): version bump 0.7.21 → 0.7.22 (auto-sync verified) + Beta-v0.7.22.md + state/work_backlog sync (2d3cdbcb)

### Fixed

- fix(state): v0.7.22 chore commit hash 동기화 (8b02fe97)
- fix(v0.7.22): workflow_kit/common/linter.py .resolve() → .absolute() (mavis data dir 격리 환경 + macOS /var symlink fix) + 3 smoke (3c129502)

## [0.7.21] - 2026-06-15

### Changed

- chore(v0.7.21): version bump 0.7.20 → 0.7.21 (auto-sync verified) + Beta-v0.7.21.md + state/work_backlog sync (f014d59e)

### Fixed

- fix(state): v0.7.21 chore commit hash 동기화 (amend 후 hash drift 보정) (fa329b11)
- fix(v0.7.21): cmd_release --allow-existing-tag flag + tag push 자동화 (pre-check + release coupling) (0ef97db4)

## [0.7.20] - 2026-06-15

### Changed

- chore(v0.7.20): Beta-v0.7.20.md release note (release coordination observability + auto-bump chain) (57586577)
- chore(v0.7.20): version bump 0.7.19 → 0.7.20 (auto-bump chain) (556eb04b)

## [0.7.19] - 2026-06-15

### Changed

- chore(v0.7.19): version bump 0.7.18 → 0.7.19 (release coordination auto-bump) (8ada0f19)

## [0.7.18] - 2026-06-15

### Added

- feat(v0.7.18): release coordination observability (_check_remote_tag + next_available_version + --auto-bump) + 7 smoke (07bf145d)

### Changed

- chore(v0.7.18): version bump 0.7.17 → 0.7.18 (auto-sync verified) + Beta-v0.7.18.md + state/work_backlog sync (46066c3d)

## [0.7.17] - 2026-06-15

### Added

- feat(v0.7.17): wiki in-repo storage isolation (5 file redirect + ai-workflow/wiki/sources/ 신규 + 11 smoke) (6f6f1af2)

### Changed

- chore(v0.7.17): version bump 0.7.16 → 0.7.17 (auto-sync verified) + Beta-v0.7.17.md + state/work_backlog sync (4d09dee0)

## [0.7.16] - 2026-06-15

### Added

- feat(v0.7.16): [tool.workflow-doctor] config thresholds/excluded_paths 적용 (B-1/B-2/B-3) + linter IndentationError fix + 9 smoke (33f52431)

### Changed

- chore(v0.7.16): version bump 0.7.15 → 0.7.16 (auto-sync verified) + Beta-v0.7.16.md + state/work_backlog sync (f0126019)

## [0.7.15] - 2026-06-15

### Added

- feat(v0.7.15): atomic_write helper + changelog-gen --from-tag/--to-tag filter + 5 smoke (8d7acc4a)
- feat(v0.7.15): atomic_write helper + changelog-gen --from-tag/--to-tag filter + 5 smoke (5cd1fe11)

### Changed

- merge: v0.7.15 fix 3 commit (Beta-v0.7.15.md commit table 정합) + v0.7.16 작업 보존 (d9f1866d)
- chore(v0.7.15): version bump 0.7.14 → 0.7.15 (auto-sync verified) + Beta-v0.7.15.md (0dc813a5)
- chore(v0.7.15): state sync (atomic_write 적용) + 1 daily backlog (30496514)
- chore(v0.7.15): version bump 0.7.14 → 0.7.15 (auto-sync verified) + Beta-v0.7.15.md (a369e7c9)

### Fixed

- fix(v0.7.15): Beta-v0.7.15.md Commit table 정상화 (Deferred 표에서 중복 row 제거 + 4 commit hash) (68b0ae9d)
- fix(v0.7.15): Beta-v0.7.15.md Commit section + 3 commit hash (3dfb5a1d)

## [0.7.14] - 2026-06-15

### Added

- feat(v0.7.14): cmd_version_bump auto-sync workflow_kit/__init__.py + cmd_changelog_gen subcommand + 8 smoke (23eb7fd0)

### Changed

- chore(v0.7.14): version bump 0.7.13 → 0.7.14 (auto-sync verified) + Beta-v0.7.14.md + CHANGELOG.md + state/work_backlog sync (63ab483c)

### Fixed

- fix(v0.7.14): Beta-v0.7.14.md Commit + Reference section 정상화 (line 정렬 + 헤더) (29af65d8)
- fix(v0.7.14): Beta-v0.7.14.md commit table TBD → 23eb7fd + 63ab483 (a01c7b41)

## [0.7.13] - 2026-06-15

### Added

- feat(v0.7.13): cmd_release --version flag (staging backfill, pyproject 일시 patch 불필요) (922ebc08)

### Changed

- chore(v0.7.13): state sync (v0.7.12 + v0.7.13 backfill) + 2 daily backlog (afc685a1)
- chore(v0.7.13): version bump 0.7.11 → 0.7.13 + __version__ sync + Beta-v0.7.13.md (628bf934)

### Fixed

- fix(v0.7.13): Beta-v0.7.13.md Commit section + 3 commit hash (727c59cc)

## [0.7.12] - 2026-06-15

### Added

- feat(v0.7.12): refresh_wiki_memory REPO_ROOT auto-detect (CLI flag > env var > git rev-parse > legacy fallback) + 4 smoke (63080baa)

### Changed

- chore(v0.7.12): v0.7.5~v0.7.10 release backfill (6 wheel/sdist + 6 git tag + 6 GH release) + Beta-v0.7.12.md 갱신 (89b7af5e)

### Fixed

- fix(v0.7.12): Beta-v0.7.12.md commit table TBD → 89b7af5 (5b8e7301)
- fix(v0.7.12): Beta-v0.7.12.md commit table TBD → 63080ba (0b3e7040)

## [0.7.11] - 2026-06-15

### Added

- feat(v0.7.11): release_pipeline Phase 3 (dist subcommand) + state sync + 8 smoke (b2650f54)

### Changed

- chore(v0.7.11): version bump 0.7.10 → 0.7.11 + __version__ sync (ec407f1a)

### Fixed

- fix(v0.7.11): cmd_verify --json field names (tag → tagName, createdAt → publishedAt) + release note commit table (aa4e8379)

## [0.7.10] - 2026-06-14

### Added

- feat(v0.7.10): release_pipeline Phase 2 (release / verify / rollback) + 8 smoke test (fdf8159a)

### Changed

- docs(v0.7.10): release note backfill + refresh_wiki_memory v0.7.10 tracking (fc87fddf)
- chore(v0.7.10): version bump 0.7.9 → 0.7.10 + release note (67d4a37a)

## [0.7.9] - 2026-06-14

### Added

- feat(v0.7.9): release_pipeline tool 정식화 (validate / version-bump / note-draft) + 8 smoke test (cb0a8922)

### Changed

- docs(v0.7.9): release note backfill + refresh_wiki_memory v0.7.9 tracking (283823ed)
- chore(v0.7.9): version bump 0.7.8 → 0.7.9 + release note (d39be44f)

## [0.7.8] - 2026-06-14

### Added

- feat(v0.7.8): refresh_wiki_memory 에 v0.7.8 release tracking 추가 (662bead8)
- feat(v0.7.8): state-aware evaluate_compliance + config actual apply (d3235adc)

### Changed

- docs(v0.7.8): release note commit hash backfill (b67af83) (f444e688)
- chore(v0.7.8): version bump 0.7.7 → 0.7.8 + release note (b67af835)

## [0.7.7] - 2026-06-14

### Added

- feat(v0.7.7): refresh_wiki_memory 에 v0.7.7 release tracking 추가 (fd182882)
- feat(v0.7.7): workflow_kit.cli.doctor 에 load_config + should_fail integration (022672f3)

### Changed

- docs(v0.7.7): release note commit hash backfill (3300e73) (7581dd23)
- chore(v0.7.7): version bump 0.7.6 → 0.7.7 + release note (3300e73c)

## [0.7.6] - 2026-06-14

### Added

- feat(v0.7.6): refresh_wiki_memory 에 v0.7.6 release tracking 추가 (1fefdfdb)
- feat(v0.7.6): workflow_kit.metadata (pyproject.toml [tool.workflow-doctor] loader) + 10 smoke test (0daf6da9)
- feat(v0.7.6): run_all_checks 통합 runner + 10 smoke test (53d5dc89)

### Changed

- docs(v0.7.6): release note commit hash backfill (b9ede19) (7a5c56ea)
- chore(v0.7.6): version bump 0.7.5 → 0.7.6 + release note (b9ede19e)

## [0.7.5] - 2026-06-14

### Added

- feat(v0.7.5): refresh_wiki_memory 에 v0.7.5 release tracking 추가 (150ee320)
- feat(v0.7.5): refresh_wiki_memory tool 정식화 + 10 smoke test (Wiki 운영 자동화) (0741775e)

### Changed

- docs(v0.7.5): release note commit hash backfill (c2a75f8) (51edde58)
- chore(v0.7.5): version bump 0.7.4 → 0.7.5 + release note (c2a75f87)
- test(v0.7.5): 4 sub-cat dispatcher runtime test 보강 (12 → 16) (9e1f206c)

## [0.7.4] - 2026-06-13

### Added

- feat(v0.7.4): CLI wrapper (workflow doctor) + @graceful_shutdown + optional dep (hypothesis/objgraph) (22e77508)

### Changed

- chore(v0.7.4): score history v0.7.4 entry (Overall 4.67 A 유지) (cfb09fb1)
- docs(v0.7.4): wiki log v0.7.4-beta entry 추가 (1818dd64)

## [0.7.3] - 2026-06-13

### Added

- feat(v0.7.3): 4 runtime helper (auth/testing/profiling/resiliency) + 7 baseline dispatcher (d03348a2)

### Changed

- chore(v0.7.3): score history v0.7.2/v0.7.3 entry 추가 (Overall 4.66→4.67 A 유지) (c732c0fb)
- docs(v0.7.3): wiki log v0.7.3-beta entry 추가 (be49e0fb)

## [0.7.2] - 2026-06-13

### Added

- feat(v0.7.2): Extension sub-cat + 4종 (resiliency) 본 구현 (179 test PASS) (3bffba30)

### Changed

- docs(v0.7.2): wiki log commit hash TBD → 3bffba3 갱신 (7cae4961)

## [0.7.1] - 2026-06-13

### Added

- feat(v0.7.1): follow-up 4건 + wiki 개선 4건 묶음 (158 test PASS, GH release) (f09034dc)

### Changed

- docs(v0.7.1): wiki log commit hash TBD → 0224a76 갱신 (9935e06c)
- docs(v0.7.1): wiki log commit hash TBD → 99e299f 갱신 (d8c981cd)
- docs(v0.7.1): wiki log commit hash TBD → f09034d 갱신 (bad14d8a)

## [0.7.0] - 2026-06-13

### Changed

- docs(v0.7.0): wiki log commit hash TBD → c72bdc3 갱신 (bdc6ceb1)
- docs(v0.7.0): wiki log commit hash TBD → 49dfc78 갱신 (471fee2c)
- docs(v0.7.0): wiki log commit hash 갱신 TBD-pending → 7a4dbae (b3759519)
- docs(v0.7.0): wiki log commit hash TBD → 021ec16 갱신 (ac75d720)
- docs(wiki): v0.7.0 5 concept page + L2 emit helper + drift smoke test (021ec16c)
- docs(v0.7.0): wiki log entry header 에 commit hash 7자 prefix 명시 (3fcd4807)
- docs(v0.7.0): release note follow-up section 추가 (Task 3+2+1) (8818cbe3)
- chore(v0.7.0): version bump 0.6.3 → 0.7.0 (390a6e07)
- docs(v0.7.0): Release notes + wiki log entry (15 commit, ~3,200 line, 130 test PASS) (dff0aaec)
- wiki: v0.7.0 step 9 — Unit of Work 3-layer template (17 test PASS) (b7641e31)
- wiki: v0.7.0 step 10 — Audit Log 표준화 (1 spec + 1 helper fix + 13 test) (2458cf8c)
- wiki: v0.7.0 step 1 — stage_completion required 격상 (8 test PASS) (6148c0f8)

## [0.6.6] - 2026-06-12

### Added

- feat(v0.6.6): 5 SKILL.md-only skill runtime 통합 (12/12 spec+runtime 일관성) (6a9126c4)

### Changed

- wiki: v0.6.6 follow-up #1 — 5 SKILL.md-only skill runtime (12/12 일관성) (8ae91027)

## [0.6.5] - 2026-06-12

### Added

- feat(v0.6.5): batch stage_completion integration — 6 spec 보유 skill (10/11 완료) (ca7a6853)
- feat(v0.6.5): pilot stage_completion integration — automated-repro-scaffold (2fab8356)
- feat(v0.6.5): Stage Gate Runtime helper + migration guide (3 file, 13 test PASS) (dd98e699)
- feat(v0.6.5): StageCompletion field 11종 skill spec + catalog 보강 (13 file) (5b165170)

### Changed

- wiki: v0.6.5 release — AIDLC 패턴 차용 (10 commit, ~2,600 line) (46e4d1f5)
- release(v0.6.5): AIDLC 패턴 차용 (Question File Format + Stage Gate) (3897da7b)
- wiki: v0.6.5 batch runtime — 6 spec stage_completion (10/11, +72 line) (0ae8d4ab)
- wiki: v0.6.5 pilot runtime — automated-repro-scaffold stage_completion (1/11, +44 line) (fbe96730)
- wiki: v0.6.5 runtime — stage-gate-pattern §12 + log entry (35 test PASS) (fbc8370f)
- wiki: v0.6.5 — stage-gate-pattern §8 + log entry (StageCompletion 11종 적용 추적) (0001782b)

## [0.6.4] - 2026-06-12

### Added

- feat(v0.6.4): Question Format + Stage Gate 코드 (2 module + 2 smoke test) (bc16d914)
- feat(v0.6.4): Question File Format + Stage Gate 명시화 (4 doc) (25756bb1)

### Changed

- wiki: v0.6.4 신규 concept 2종 (Question File Format + Stage Gate Pattern) (d32226be)

### Fixed

- fix(v0.6.4): V-R9 skip marker — naive grep false-positive 17 → 0 (30183c51)

## [0.6.3] - 2026-06-12

### Added

- feat(v0.6.3): P4 memory/log.md + harness overlay consistency check (3261e20e)

### Changed

- release(v0.6.3): final v0.6.x series release — all 4 milestones complete (19237058)

### Fixed

- fix(v0.6.3): P6 phase-6 backfill — INGEST_GUIDE path 정정 + log 보강 (1d7ca77b)
- fix(v0.6.3): broken relative links after memory/active/ rename + fix bootstrap test leniency (6b2bf005)

## [0.6.2] - 2026-06-12

### Added

- feat(v0.6.2): P3 T2 work_backlog anchor + T3 ingest atomicity (2713059e)

## [0.6.1] - 2026-06-12

### Added

- feat(v0.6.1): P2 R8 freeze + R10 freeze lint + T1 memory lint 4종 + R7 merge-res ext (06203737)

## [0.5.11] - 2026-06-09

### Added

- feat(v0.5.11): Mavis engine hook (§6.5) + 회귀 test 강화 (4ce36353)

### Changed

- docs(v0.5.11): Beta-v0.5.11.md release note — 릴리스 일자 표현 정정 (5bd4c4f1)
- chore(v0.5.11): bump version to 0.5.11-beta (cfde435f)
- docs(v0.5.11): Beta-v0.5.11 release note (cb0f6986)
- docs(v0.5.11): governance 갱신 — 1인 dev 환경, 24h cool-down 명시 (c89971dd)
- docs(v0.5.11): --no-interactive 비대화형 가이드 보강 (7329dbe2)

### Fixed

- fix(v0.5.11): bootstrap MCP env — wheel install 시 PYTHONPATH omit (e388366f)
- fix(v0.5.11): MCP initialize response — protocolVersion 추가 (677bcff3)

## [0.5.10] - 2026-06-08

### Fixed

- fix(v0.5.10): choose_roles sub.delegation_id parent-prefix spec 정합 (8359cfc0)

## [0.5.9] - 2026-06-08

### Changed

- docs(v0.5.9): wire 가이드 §7/§8/§9 보강 — sub.delegation_id parent prefix 룰 명시 (1006ff0c)

## [0.5.8] - 2026-06-08

### Added

- feat(v0.5.8): interactive --harness picker + packaging smoke automation (6213dcc8)

## [0.5.7] - 2026-06-08

### Added

- feat(v0.5.7): contract v1 §4.2/§5.2 multi-component fan-out/in + §6.3 cross-ref row (#21) (ebf7e7c2)

## [0.5.6] - 2026-06-07

### Added

- feat(v0.5.6): contract v1 §5/§6 P0 enforcement (validator + delegator) (#20) (79f3bec2)

### Changed

- docs(v0.5.6): mark TASK-V056-001 done post-merge (731787b5)

## [0.5.5] - 2026-06-07

### Added

- feat(v0.5.5): Phase 11 본격 pilot (Devhub Example × Contract v1) (#19) (1f095ec5)

### Changed

- docs(v0.5.5): mark TASK-V055-001 done post-merge (75a3fc6c)

## [0.5.4] - 2026-06-07

### Added

- feat(v0.5.4): orchestrator ↔ sub-agent delegation contract v1 (closes #1) (#18) (7737e141)

## [0.5.3] - 2026-06-07

### Added

- feat(v0.5.3): antigravity MCP config 표준화 + cross-language stack 표시 (#17) (b6ae73aa)

### Changed

- docs(v0.5.3): mark tasks done + release notes for Beta v0.5.3 (a961fa04)

## [0.5.2] - 2026-06-06

### Changed

- refactor(v0.5.2): bootstrap_workflow_kit.py → bootstrap_lib/ 6-module package (#16) (9497a357)

## [0.5.1] - 2026-06-06

### Added

- feat(v0.5.1): end-to-end MCP round-trip smoke (#15) (73f8f2fa)
- feat(v0.5.1): per-harness MCP install + auto-emit + guide (#14) (c3c9a90c)
