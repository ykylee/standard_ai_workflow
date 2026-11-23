# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-11-23
- 관련 문서: [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: v3.0.2 워크스페이스 — `main@ae732239` 에서 이어받음 (2026-11-23). 이 브랜치의 작업은 아직 없다. 모 브랜치 기준선: **144차 세션 말 (2026-11-23, Linux 호스트) — `main`/`origin/main` = `1f8f215d`, 세션 변경 push 완료.** M-057/WBS-57.1은 Linux 테스트베드 복제본 shadow 범위 확대 중, WBS-57.2는 Go 화면·relay HTTP parity 중이다. Go UI에는 정적 `/ui/`, session/projects/project/tasks/callsigns/events, callsign 상세·handoff, guide GET, roadmap GET, wiki list/search/page, callsign register/approve, 계획 응답 POST가 있다. Go 화면 전체 shadow는 미수행이고 guide 제안/결정·orchestration API·`/v1/relay/{register,poll,result}`는 미구현이다. `go test ./...`, `go vet ./...`, 자산 동기화 3/3, Go 코어 실프로세스 11/11, 변경 게이트 124/124, 양 문맥 전량 게이트 353/353 통과. Python `check_hub_ui.py` 15/15는 Python 정본만 검사한다. **3.0.0 미발행**: Go 전체 parity·4 harness·macOS/Windows·동일 DB rollback 전이다.
- 현재 주 작업 축: **2.x 전면 Go 전환 (M-049~M-056, 2026-11-22 소유자, ADR-035) — M-049~M-056 done (concept · requirements · design · S1 PC 중계 · UI/UX · S2-a judge/1 · S2-b 중앙 허브 코어 · S2-c 세션/오케스트레이션).** 이전 2.0 허브 stabilization M-039 에는 WBS-39.1 macOS · Windows · 대화형 실측과 WBS-39.3 arcturus 이전이 남아 있다. 1.x 는 `release/1.x` 에서 결함 수리만. 이전 축: **로드맵·마일스톤·WBS 진척 관리 + SDLC 온보딩 기본 — 60차(2026-08-25) 소유자 지시로 확정.** ADR-027 accepted, 정본 스펙은 [`roadmap_milestone_wbs_spec.md`](../../../../workflow-source/core/roadmap_milestone_wbs_spec.md) (M-001 design 완료, 구현은 M-002~M-006 단계 실행 — 스펙 §10 이 임시 로드맵 정본). 직전 축(배포 일관성·멱등성)은 ✅ gap 4개 전부 닫혔다 (2026-08-18, 48차). 정본은 [`workflow_deployment_idempotency.md`](../../../../workflow-source/core/workflow_deployment_idempotency.md). ~~[main-016] `wk doctor`~~ ✅ · ~~[main-017] 채널 재실행 계약~~ ✅ (47차) · ~~[main-005] 드리프트 감지(페이로드 해시)~~ ✅ · ~~[main-019] 환경 pre-flight~~ ✅ (48차). 탐침은 이제 **7절**이다 (53차 `runtime_load` 신설 — 노출 미측정 한 칸을 측정으로 옮겼다). ~~[main-010] §7.0.2 의 '버전 상이' 셀~~ ✅ (53차 — 실측 + `installPath` 선언을 읽도록 교정). ~~[TASK-2026-08-14-main-009] 라벨 영어 전환~~ ✅ (53차 — 4단계 종료). ~~[main-004] wiki 3-step 하위 두 단계~~ ✅ (49차 — 1단계 은퇴 / 2단계 수리 / 3단계 재작성). **열린 후보**: ~~OKF v0.2 이행 ADR~~ ✅ (2026-08-20 ADR-026 로 전체 이행 완료, TASK-2026-08-20-main-003 — 이 줄이 그것을 안 따라와 58차가 낡은 후보를 다시 검토했다; 잔재였던 매니페스트 '0.1' 하드코딩은 58차 main-008 이 걷음) · ~~wiki L1→L2 갭 85개~~ ✅ (50차 — 계약을 4종으로 좁혀 닫음) · cross-host federation(MacBook, 시점 추후) · ~~[TASK-2026-08-13-main-004] mypy flake 관찰~~ ✅ (66차 close — 33/33 표본, mypy 실패 0).
- 원류: `main@ae732239` — [`active/main/session_handoff.md`](../main/session_handoff.md) 의 기준선 · 주 작업 축 · 열린 task 10건 · §5 를 옮겨 적었다 (모 브랜치에는 쓰지 않았다). 옮겨 온 task 는 frontmatter `inherited_from` 로 원류를 갖고, 합류 아카이브 때 고친 것만 원본에 되돌려 적힌다.

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
- TASK-2026-11-23-v3.0.2-002 MCP 2026-07-28 최신 프로토콜 v3.0.2 prerelease 발행
- TASK-2026-11-23-main-005 Go 허브 Linux 테스트베드 실전 shadow 검증
- TASK-2026-11-23-main-006 Go 허브 화면 API 및 PC 중계 HTTP parity
- TASK-2026-11-23-main-014 사내 Windows V3가 3.0 허브 실행 파일을 악성코드로 격리하는 탐지 조사
## 3. 차단 작업

- 현재 `blocked` 작업:
- TASK-2026-08-25-main-017 MCP emit command 가 항상 python3 — PATH 에 python3 이 없는 Windows 에서 emit 설정으로 서버를 spawn 할 수 없다
- TASK-2026-10-02-main-006 Windows 로캘(cp949)에서 wk 가 UnicodeEncodeError 로 죽는다 — stdout 과 기본 인코딩 I/O 를 UTF-8 로 고정
- TASK-2026-10-02-main-007 Windows V3 백신이 wk.exe 를 평판 기반으로 차단한다 — pip 생성 console-script 런처 대체 진입 경로
- TASK-2026-11-17-claude-remote-sync-check-234c32-002 워크벤치 응답 · todo 변경이 Claude Code 컨텍스트에 실제로 주입되는지 실측 (main-014 미측정분)
- TASK-2026-11-17-claude-remote-sync-check-234c32-004 iPad Chrome(CriOS 156 · iPadOS 27)에서 워크벤치 폼 제출이 서버에 닿지 않는다 — 응답 보내기 · todo 추가 전부
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-11-23-v3.0.2-001 브랜치 네임스페이스 자동 seed — `main` 에서 이어받음
## 5. 다음 세션 시작 포인트

- (`main@ae732239` handoff §5 에서 이어받음 — 아래 6줄은 모 브랜치의 다음 시작 포인트다)
- (145차, 2026-11-23, Linux) 수정 커밋 `b8c0af8c`를 push하고 v3.0.1 pre-release를 발행했다. Go Windows DSN 단위 회귀와 Python 3.0.1 wheel fallback을 준비했다. 다음은 M-057/WBS-57.1·57.2에서 Python/Go API parity를 업데이트하고 화면 write 및 relay DB 효과를 격리 복제 DB로 비교한다. native Windows 실행, 4 harness, same-DB rollback은 미검증이다. stable latest는 v2.1.0이다.
- (141차, 2026-11-23, Linux) **Go 전환 S1 · UI/UX · S2-a · S2-b 완주 (main-031~041, 전부 done)**: **M-052 S1 PC 중계 Go 판 done** (main-031 `hub-go/` 뼈대 · 6타깃 크로스 빌드 `check_go_build` 5/5, main-032 중계 CLI/설정/긴 폴링/어댑터 3종/로컬 화면, main-033 `check_hub_relay` `WORKFLOW_RELAY_IMPL=both` 22/22 · Claude Code 2.1.330 & Codex 0.171.0 실제 어댑터 실측). **M-053 허브·중계 UI/UX done** (main-034 허브 `/ui/` 2.1 오케스트레이션 판 · 로드맵 화면 · 1.x 워크벤치 결정 UX 복원, main-035 Python·Go 중계 로컬 화면 무깜빡임 fetch · 로컬 상세 · 허브 딥링크 · 개별 세션 종료). **M-054 S2-a 순수 판정 `judge/1` done** (main-036 `plan.lint` · `plan.states` · `task.status`, main-037 `wbs.gate` · `roadmap.derive` · `handoff.parse` · `state.build`, main-038 corpus 89케이스 · `check_judge_parity` 불일치 0). **M-055 S2-b 중앙 허브 코어 Go 판 done** (main-039 `internal/db` `modernc.org/sqlite` 판 1~12 SQL · 온라인 백업 · `internal/assets` · `check_go_assets_sync` 3/3, main-040 `internal/store` 인증/멱등/비밀스캔/콜사인/task CRUD/맡기/커밋/이력, main-041 `internal/{tools,mcpserver,httpapi}` 74도구 스키마·코어 핸들러·JudgeBridge·stateless JSON MCP·`serve`/`backup`/`admin` CLI · `check_hub_core` `WORKFLOW_HUB_IMPL=both` 18/18). **다음: S2-c/d** — 나머지 허브 도구(셋업 · 지침 · 1.x 전환 · 이전 · 메모리/위키/체크포인트 · 오케스트레이션 · 중계 서버 API) 및 웹 화면(`/ui/`, `/api/*`) Go 전환 (`workflow-source/core/hub_go_spec.md` §5).
- (140차, 2026-11-22, Linux) main-014 (Codex 일하는 세션 커밋 — `turn/start` sandboxPolicy.writableRoots 에 git dir · common dir, push 는 보고 B) · M-048: main-016 실제 VS Code 1.147 실측(test-electron · xvfb · CDP) 결함 2 수리 (`frame-ancestors` 에 `vscode-file://vscode-app` · `enableScripts` true) + `.vsix` · main-017 진입 지침 push 막힘 문구 · main-020 SDK/해석기 매트릭스 tmp 저장소 밖 · main-019 **v2.1.0 발행** (게이트 1~3회차 flake 원인 = 같은 호스트 arbiter.service 전역 OOM 재기동 루프 — 소유자 승인으로 mes-total-solution dev 환경 `dev-down.sh`, 그 개발 DB 비워짐) · main-018 README 재작성 · main-022 허브 mcp 2.x. Go 전환: M-049 (main-021 실측 — go-sdk v1.8.0 · rmcp 3.11 탐침이 Claude Code · Codex 에 붙음, `/var/tmp/claude-rtprobe/`) · M-050 (main-024~026) · M-051 (main-027~030) done. **다음: M-052 S1 — WBS-52.1 `hub-go/` 뼈대 · `check_go_build` → 52.2 중계 Go 판 → 52.3 `check_hub_relay` 스위치 · 실제 어댑터 실측** (hub_go_spec §6 · §8). 남은 후속: 해석기 매트릭스 전량 재실행(main-019 후속) · arbiter 메모리 상한 없음(그 저장소 몫).
- (139차, 2026-11-22, Linux) 결함 수리 2 (main-027 `find_dist_files` 정확 대조 · 234c32-002 seed 가 `roadmap_state.json` 재생성, 1.x 이식 release-1.x-008 · 009). **새 축 허브 오케스트레이션**: M-041 concept done (O1~O10 권고안) · M-042 requirements done — 실측 S 1차 · 2차(hook · 신뢰 없는 간접 수단: 도구 응답 편승 · 대기 도구 · 받은편지함 파일, 진입 지침 있을 때만 동작) · 요구 R17~R24 · Q1~Q4 권고안 · **ADR-034 Proposed**. 정본 `docs/planning/hub-orchestration-{review,requirements}-2026-11.md`. M-043 design done (`workflow-source/core/hub_orchestration_spec.md`, DO1~DO13 권고안 · ADR-034 Accepted). **M-044 구현 1 done** (TASK-2026-11-22-main-009 — DB 판 11 · `hub/orchestration.py` · 공통 `session` 인자 · 편승 · 대기 async · 수신 확인, `check_hub_orch` 10/10 · 되주입 12/12). **M-045 구현 2 done** (TASK-2026-11-22-main-010 — lease · 배정 상태 기계 · 수락=맡기 한 트랜잭션 · 보고 · 정지 · 2.1 진입 규칙 절, `check_hub_orch_assign` 9/9 · 되주입 16/16). **M-046 WBS-46.2 done** (TASK-2026-11-22-main-011 — 허브 중계 API · `workflow_kit/relay/` · `hub relay` 명령 · 어댑터 claude-code/codex/fake, `check_hub_relay` 9/9 · 되주입 13/13). **M-046 done** — main-013 실제 어댑터 실측(요구 §1.5: Claude · Codex 띄우기 → 자기 등록 → 배정 전달 → 수락 → 보고 → 멈춤 전부 동작) · 로컬 화면. **M-047 done** (main-015 — `editors/vscode/` 껍데기, `check_vscode_shell` 6/6, 실제 VS Code 로드 미측정). 결함 수리 2 — main-012 (WBS 한 줄 위반 → issue `wbs_node_invalid`, session-start 가 죽지 않음) · main-002 (backlog-update done 의 Result 중복 — 손으로 지우던 것 끝), 둘 다 release/1.x 이식(release-1.x-001). **다음: M-048 안정화 · 2.1.0 발행** (전량 게이트 · main-014 소유자 결정 — 권고 'A 실측 → 안 되면 B' · VS Code 실측 · .vsix · 발행 노트). 후속 planned: main-012 (로드맵 형식 위반이 session-start 를 죽임) · main-014 (Codex workspace-write 에서 .git 읽기 전용 — 소유자 결정).
- Codex 데스크톱을 완전히 재시작한 뒤 새 셸에서 `Get-Command wk`, `wk session-start`, `gh`, `unzip`, `python3 --version`, `wk doctor --json` 을 확인한다. 재시작 후에도 `wk` 가 빠져 있으면 사용자 PATH 가 데스크톱에 전달되는지 다시 진단한다. Codex CLI 실행 파일이 계속 PATH 에 없으면 `codex` 채널의 `installable=false` 는 별도 CLI 미설치 상태로 기록한다.
- 누적 기록은 [`lessons.md`](../main/lessons.md) (규칙 15절) · [`sessions/handoff-notes_*.md`](../main/sessions) (기록 17절) 로 이관됐다 — 최신이 위, 세션 시작에 읽지 않는다.
- 실제 작업은 `python -m workflow_kit backlog-update` 로 새 task 를 만들어 기록한다.
- 작업 범위를 벗어나는 변경은 다른 워크스페이스와 충돌할 수 있으므로 backlog 에 별도 task 로 남긴다.

#### 작업 후보 — 정본은 `state.json` 의 `planned_items` · `in_progress_items`

- TASK-2026-11-23-main-005 — Go 허브 Linux 테스트베드 실전 shadow 검증
- TASK-2026-11-23-main-006 — Go 허브 화면 API 및 PC 중계 HTTP parity
- TASK-2026-11-23-main-014 — 사내 Windows V3가 3.0 허브 실행 파일을 악성코드로 격리하는 탐지 조사
- TASK-2026-11-13-claude-remote-sync-check-234c32-005 — 주장 트리 계획 Windows 실측 — os.link 공개 · 배타 이동 · 잠금 (NTFS)
- TASK-2026-11-21-main-013 — 허브 하네스 실측 (macOS · Windows · 대화형 · 실제 원격) — WBS-39.1 남은 몫

## 6. 남은 리스크

- 아직 검증된 산출물이 없다.
