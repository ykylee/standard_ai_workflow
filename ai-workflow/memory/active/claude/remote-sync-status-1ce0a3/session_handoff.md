# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-10-02
- 관련 문서: [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: claude/remote-sync-status-1ce0a3 워크스페이스 — `main@309c9ddf` 에서 이어받음 (2026-10-02, macOS 호스트). **이 브랜치 작업 2건 done (TASK-2026-10-02-claude-remote-sync-status-1ce0a3-002 M-007/WBS-7.4 · -003 M-007/WBS-7.2)** — 이 호스트 v1.19.0 §2.8 재적용(4채널 + MCP 해석기 홈브루 python3 1.16.0→1.19.0, doctor behind=[] disabled=[]) + 고유 커밋 없는 worktree 4 · 브랜치 5 정리, 미커밋 브랜치 메모리 3개는 `archived/` 로 보관. 모 브랜치 기준선: **114차 세션 (2026-10-02, Linux 호스트) — task 1건 close (TASK-2026-10-02-main-008, M-007/WBS-7.4) + v1.19.0 발행, 2건 in_progress (main-006 · 007, Windows 실측 대기).** 소유자 보고 2건(같은 Windows · OpenCode 데스크톱). ①**main-006 cp949** — 하네스가 kit 를 파이프로 부르면 stdio 가 로캘 인코딩이라 `—` 출력에서 exit 2(터미널 직접 실행은 재현 안 됨, Linux 재현 `PYTHONIOENCODING=cp949`). `common/stdio.force_utf8_stdio`(wk_main · python -m 진입점 3) + 텍스트 I/O 115곳 encoding 명시(subprocess 108 은 errors=replace), check_text_io_encoding 5 cases(되주입 5 red) — `df975bbe`. ②**main-007 V3 가 wk.exe 평판 차단** — 소유자 결정 = `python -m workflow_kit` 직접(셸 미상). `workflow_kit/__main__.py` · `common/kit_invocation`(정본) · 정본 §11.1 명령 전환 + 해석기 안내 bullet → CLAUDE.md/AGENTS.md · 스킬 · hook(python3→python 중 kit import 되는 첫 해석기) · doctor(해석기별 import 실측, 플러그인 전제에서 wk 제거, `wk_on_path` legacy 유지) · 런타임 안내 30곳. check_kit_invocation 4 cases + payload bare-wk hook 가드 + 설치 문서 전제 표 정확 일치 강화 — `2eb7c315`. ③**main-008 v1.19.0** (파생 minor) — 발행 중 interpreter_matrix 가 상속 PYTHONPATH 에 속아 새 3.13 venv 의존성 설치를 건너뛰던 결함 수리(`fb957c5c`, case 5). 태그 → `ea193113`(게이트 302×2, 매트릭스 3.11 · 3.13 각 302), asset 4종, 발행 wheel 격리에서 cp949 session-start · dashboard · doctor rc 0 · hook 탐침이 Store 별칭형 python3 건너뜀, §2.8 behind=[] disabled=[]. **Codex hook 재신뢰 필요**.
- 현재 주 작업 축: **로드맵·마일스톤·WBS 진척 관리 + SDLC 온보딩 기본 — 60차(2026-08-25) 소유자 지시로 확정.** ADR-027 accepted, 정본 스펙은 [`roadmap_milestone_wbs_spec.md`](../../../../../workflow-source/core/roadmap_milestone_wbs_spec.md) (M-001 design 완료, 구현은 M-002~M-006 단계 실행 — 스펙 §10 이 임시 로드맵 정본). 직전 축(배포 일관성·멱등성)은 ✅ gap 4개 전부 닫혔다 (2026-08-18, 48차). 정본은 [`workflow_deployment_idempotency.md`](../../../../../workflow-source/core/workflow_deployment_idempotency.md). ~~[main-016] `wk doctor`~~ ✅ · ~~[main-017] 채널 재실행 계약~~ ✅ (47차) · ~~[main-005] 드리프트 감지(페이로드 해시)~~ ✅ · ~~[main-019] 환경 pre-flight~~ ✅ (48차). 탐침은 이제 **7절**이다 (53차 `runtime_load` 신설 — 노출 미측정 한 칸을 측정으로 옮겼다). ~~[main-010] §7.0.2 의 '버전 상이' 셀~~ ✅ (53차 — 실측 + `installPath` 선언을 읽도록 교정). ~~[TASK-2026-08-14-main-009] 라벨 영어 전환~~ ✅ (53차 — 4단계 종료). ~~[main-004] wiki 3-step 하위 두 단계~~ ✅ (49차 — 1단계 은퇴 / 2단계 수리 / 3단계 재작성). **열린 후보**: ~~OKF v0.2 이행 ADR~~ ✅ (2026-08-20 ADR-026 로 전체 이행 완료, TASK-2026-08-20-main-003 — 이 줄이 그것을 안 따라와 58차가 낡은 후보를 다시 검토했다; 잔재였던 매니페스트 '0.1' 하드코딩은 58차 main-008 이 걷음) · ~~wiki L1→L2 갭 85개~~ ✅ (50차 — 계약을 4종으로 좁혀 닫음) · cross-host federation(MacBook, 시점 추후) · ~~[TASK-2026-08-13-main-004] mypy flake 관찰~~ ✅ (66차 close — 33/33 표본, mypy 실패 0).
- 원류: `main@309c9ddf` — [`active/main/session_handoff.md`](../../main/session_handoff.md) 의 기준선 · 주 작업 축 · 열린 task 5건 · §5 를 옮겨 적었다 (모 브랜치에는 쓰지 않았다). 옮겨 온 task 는 frontmatter `inherited_from` 로 원류를 갖고, 합류 아카이브 때 고친 것만 원본에 되돌려 적힌다.

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
- TASK-2026-10-02-main-006 Windows 로캘(cp949)에서 wk 가 UnicodeEncodeError 로 죽는다 — stdout 과 기본 인코딩 I/O 를 UTF-8 로 고정
- TASK-2026-10-02-main-007 Windows V3 백신이 wk.exe 를 평판 기반으로 차단한다 — pip 생성 console-script 런처 대체 진입 경로
## 3. 차단 작업

- 현재 `blocked` 작업:
- TASK-2026-08-25-main-017 MCP emit command 가 항상 python3 — PATH 에 python3 이 없는 Windows 에서 emit 설정으로 서버를 spawn 할 수 없다
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-10-02-claude-remote-sync-status-1ce0a3-003 게이트의 저장소 관찰 검사가 worktree 의 현재 브랜치 메모리를 합류 반영·아카이브한다 — archive_branch_memory 가 브랜치 오버라이드만 보고 실제 checkout 을 안 봤다
- TASK-2026-10-02-claude-remote-sync-status-1ce0a3-002 macOS 호스트 v1.19.0 채널 재적용(§2.8) + 고유 커밋 없는 worktree 4개·브랜치 5개 정리
- TASK-2026-10-02-claude-remote-sync-status-1ce0a3-001 브랜치 네임스페이스 자동 seed — `main` 에서 이어받음
## 5. 다음 세션 시작 포인트

- (115차 macOS worktree `claude/remote-sync-status-1ce0a3`) **이 호스트 v1.19.0 §2.8 완료 — Claude Code · Codex 앱 재시작 + Codex hook 재신뢰만 남음** (runtime_load stale: claude pid 4225, codex pid 1241 · 1670). 함정: hook · MCP 가 고르는 `python3` 은 홈브루 3.14 의 **일반 설치**(릴리스 wheel)라 채널 재적용만으로는 안 올라간다 — `/opt/homebrew/bin/python3 -m pip install --break-system-packages <wheel>` 로 따로 올렸다 (doctor 의 MCP 해석기 발견이 잡는다). `feat/auto-20260930-f3de0dba` 의 `932a9d78` 은 main `8ccd6db8` 과 같은 작업(SHA 만 다름, `git cherry` 는 미병합으로 보임)이라 병합하지 않았다. **worktree seed 이어받기(1.17.0) 첫 실사용 확인** — 기준선 · 열린 task 5건 · §5 가 실렸다. **게이트 결함(-003)**: worktree 에서 `check_roadmap_wiring` 이 브랜치를 `main` 으로 강제해 실제 저장소에서 session-start 를 돌려 자기 브랜치 메모리를 합류 반영 · 아카이브했다 (같은 패턴 check_state_reconcile case 7 도) → **kit 수리**: `archive_branch_memory` 가 실제 checkout 브랜치(`git symbolic-ref`)를 보존하고 합류 반영은 checkout 이 기본 브랜치일 때만 (check_branch_join_reflect case 6) + roadmap_wiring 관찰 전후 무변화 단언. main 체크아웃에서는 미반영 병합 브랜치가 있을 때 같은 관찰이 여전히 쓴다(이제 red 로 알림) — 게이트 전에 main 의 session-start 를 먼저 돌릴 것. 합류 반영(1.18.0)은 이 브랜치를 main 에 올린 뒤 main 의 `session-start` 가 남기는지 다음 main 세션이 확인한다.
- (`main@309c9ddf` handoff §5 에서 이어받음 — 아래 10줄은 모 브랜치의 다음 시작 포인트다)
- (114차) **v1.19.0 발행됨 (main-008) — Windows 실측 대기, main-006 · 007 은 Linux 재현 조건으로만 검증해 in_progress.** 이 호스트는 §2.8 완료(behind=[] disabled=[]), claude-code · codex 재시작 필요(runtime_load), Codex hook 재신뢰 필요. Windows 호스트는 v1.19.0 wheel 로 갱신한 뒤 아래를 잰다. 소유자 보고 2건(같은 Windows · OpenCode 데스크톱): ①cp949 — 파이프 stdio 가 로캘 인코딩이라 `—` 출력에서 exit 2 → `common/stdio.force_utf8_stdio` + 텍스트 I/O 115곳 encoding 명시 + `check_text_io_encoding`. ②V3 가 `wk.exe`(pip 설치별 서명 없는 런처)를 평판 차단 → 하네스 호출을 `python -m workflow_kit <명령>` 으로 전환(소유자 결정, 셸 미상): 정본 §11.1 · 스킬 · 진입점 블록 · hook(python3→python import 탐침) · doctor(해석기별 import 실측) · 런타임 안내 30곳, `check_kit_invocation`. Windows 에서 확인할 것: `python -m workflow_kit session-start` rc 0 · OpenCode 에서 워크플로우 왕복 · `python -m workflow_kit doctor` 의 kit 해석기 줄 · OpenCode 실행 셸 종류(기록). 
- (113차) **v1.18.0 발행됨** — claude-code 는 재시작해야 새 코드가 돈다(runtime_load stale), macOS 호스트는 §2.8 재적용(→1.18.0). **worktree 메모리 왕복은 다음 worktree 세션이 첫 실사용** — worktree 의 `session-start` 가 모 브랜치 기준선 · 열린 task 를 이어받는지(1.17.0), 그 브랜치가 main 에 병합된 뒤 main 의 `session-start` 가 합류 반영 warning 과 함께 완료 · 이월 · 되돌려 적기 · §5 합류 줄을 남기는지(1.18.0) 확인하고 그 변경을 main 커밋에 싣는다. 합류 뒤 같은 worktree 에서 이어 작업하지 말고 새 브랜치로. origin 없는 저장소 한계는 TASK-2026-10-02-main-003.
- (110차 Claude Code worktree 합류) **worktree 브랜치는 이제 자기 네임스페이스로 자동 seed 된다** — `session-start` 가 `active/<branch>/` 부재 시 `main` 기준으로 seed, CI 밖 detached HEAD = 기본 브랜치, 비 git workspace = main (TASK-2026-09-30-claude-session-start-e6eb83-002, 6118db3d). 그 세션의 기준선·잔여 리스크는 [`archived/claude/session-start-e6eb83/session_handoff.md`](../../../archived/claude/session-start-e6eb83/session_handoff.md) (브랜치 삭제 뒤 아카이브 완료). main-012 · main-013 은 같은 세션이 close.
- (111차 Claude Code worktree 합류) **게이트 간헐 red 제거** — `check_v0_7_24_release_notes_template` 가 저장소 `releases/` 에 `Beta-v9.9.9-test*.md` 를 쓰던 것을 임시 디렉터리 주입(`_resolve_notes_file(..., releases_dir=)`)과 저장소 전후 스냅샷 단언으로 막았다 (TASK-2026-09-30-claude-exciting-ardinghelli-a0680d-001, 306adeaf, 게이트 native·slash 299/299). 기록은 [`archived/claude/exciting-ardinghelli-a0680d/session_handoff.md`](../../../archived/claude/exciting-ardinghelli-a0680d/session_handoff.md) — worktree·브랜치는 아직 남아 있어 `--branch` 강제 아카이브했다.
- (compact 중계 후속, M-007) 대화형 Claude Code 세션에서 **자동 압축(`trigger: auto`) 1회 실측** — 기계 층만 기록되고 재주입 머리말이 '판단 층 없음' 을 말하는지. **v1.16.0 발행됨** — macOS Codex 적용·사용자 hook 신뢰·재시작·실제 압축 왕복은 main-014에서 검증 완료. Claude Code 자동 압축 실측은 별도 환경에서 진행한다. 측정 방법(격리 CODEX_HOME + app-server 드라이버)은 저장소에 없다 — 다음에 필요하면 compact_relay_spec §7 기술로 재구성.
- (macOS 호스트) TASK-2026-09-30-main-001 착수 전 105차 배포본 채취: `find ~/.minimax/plugins/standard-ai-workflow -maxdepth 3 | sort` + 매니페스트 원문 + 제품(Desktop / CLI `mcode`)·버전. 공식 mcode 0.4+ 명세와 105차 기록이 우선순위가 반대라, 채취본을 정본 fixture 로 삼아 렌더러 → §2.8 → `deploy_doctor` 순. claude-code 매니페스트(hooks 경로 문자열)를 그대로 재사용하지 말 것.
- (Windows 호스트) main-002 실측: `check_python_floor_syntax` case 6 이 실제 `.cmd` shim 으로 PASS 하는지.
- Codex 데스크톱을 완전히 재시작한 뒤 새 셸에서 `Get-Command wk`, `wk session-start`, `gh`, `unzip`, `python3 --version`, `wk doctor --json` 을 확인한다. 재시작 후에도 `wk` 가 빠져 있으면 사용자 PATH 가 데스크톱에 전달되는지 다시 진단한다. Codex CLI 실행 파일이 계속 PATH 에 없으면 `codex` 채널의 `installable=false` 는 별도 CLI 미설치 상태로 기록한다.
- (Windows 호스트) 104차 main-018 실측: `wk doctor --json` 사본 대조에서 정본 파일이 extra 로 뜨던 잡음이 사라졌는지 확인. 같은 Windows 세션에서 blocked TASK-2026-08-25-main-017 완료 기준 2 를 한 명령으로 닫는다: `.venv\Scripts\python.exe workflow-source/tests/check_bootstrap_mcp_roundtrip.py --literal-command` (104차 신설 — emit 된 launcher 를 치환 없이 PATH 에서 해석해 spawn). 5/5 면 done.
- 누적 기록은 [`lessons.md`](../../main/lessons.md) (규칙 10절) · [`sessions/handoff-notes_*.md`](../../main/sessions) (기록 7절) 로 이관됐다 — 최신이 위, 세션 시작에 읽지 않는다.
- 실제 작업은 `python -m workflow_kit backlog-update` 로 새 task 를 만들어 기록한다.
- 작업 범위를 벗어나는 변경은 다른 워크스페이스와 충돌할 수 있으므로 backlog 에 별도 task 로 남긴다.

#### 작업 후보 — 정본은 `state.json` 의 `planned_items` · `in_progress_items`

- TASK-2026-10-02-main-006 — Windows 로캘(cp949)에서 wk 가 UnicodeEncodeError 로 죽는다 — stdout 과 기본 인코딩 I/O 를 UTF-8 로 고정
- TASK-2026-10-02-main-007 — Windows V3 백신이 wk.exe 를 평판 기반으로 차단한다 — pip 생성 console-script 런처 대체 진입 경로
- TASK-2026-09-30-main-001 — minimax-code 가 플러그인 채널로 미지원 — 배포·드리프트 판정·재생성이 모두 kit 밖
- TASK-2026-10-02-main-003 — 원격 없는 저장소의 worktree 는 자동 seed · 이어받기가 안 돈다 — 기본 브랜치 판정이 현재 브랜치로 떨어진다

## 6. 남은 리스크

- 이 호스트의 Claude Code · Codex 프로세스는 재시작 전까지 옛(1.16.0) 플러그인 코드로 돈다. Codex hook 은 재설치로 신뢰가 풀렸을 수 있다.
- 아카이브한 feat 브랜치 메모리 2개에는 `in_progress` · `planned` task 가 남아 있다 — 모두 main-001 · main-012 · 이번 재적용으로 대체됐으므로 다시 열지 말 것.
