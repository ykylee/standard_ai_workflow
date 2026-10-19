# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-10-19
- 관련 문서: [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: feat/auto-20261019-a0afcf36 워크스페이스 — `main@06abaaf0` 에서 이어받음 (2026-10-19). 이 브랜치의 작업은 아직 없다. 모 브랜치 기준선: **117차 세션 (2026-10-06, Linux 호스트) — task 3건 close, 발행 없음 (main 은 v1.20.1 + 3커밋).** ①**main-003**(A2) — 재시작 뒤 `subagent_type=verifier` 로 v1.20.1 발행 task(main-007) 검증 3/3 PASS, 노출 도구 Bash·Read 뿐(쓰기 도구 미노출 실측). Bash 쓰기는 지시문 규율 의존, 선언한 Grep·Glob 은 이 빌드 미노출. ②**main-008**(WBS-7.4) — `docs/RELEASE.md` §2.8 에 `python -m workflow_kit.minimax_plugin` 재적용 + doctor `content_drift`·`plugin_enabled` 가 minimax 를 안 잰다는 사실 + `in_sync` 확인 one-liner (`2ef4682f`). ③**main-009**(WBS-7.2) — `--apply` 가 반영 뒤 상태를 찍어 첫 설치가 '13개 이미 일치' 로 읽히던 것: 바뀐 파일만 쓰고 `before` 를 싣고 '<옛> → <새>' · 무변경은 백업 없음 · 반영 뒤 불일치 rc 1(text·json), case 8 (`077474d8`). verifier 3회 — 기준 줄 부재로 1회 차단, 되주입 구멍 2건(목록 루프 · 화살표 조건) 추가 발견.
- 현재 주 작업 축: **로드맵·마일스톤·WBS 진척 관리 + SDLC 온보딩 기본 — 60차(2026-08-25) 소유자 지시로 확정.** ADR-027 accepted, 정본 스펙은 [`roadmap_milestone_wbs_spec.md`](../../../../../workflow-source/core/roadmap_milestone_wbs_spec.md) (M-001 design 완료, 구현은 M-002~M-006 단계 실행 — 스펙 §10 이 임시 로드맵 정본). 직전 축(배포 일관성·멱등성)은 ✅ gap 4개 전부 닫혔다 (2026-08-18, 48차). 정본은 [`workflow_deployment_idempotency.md`](../../../../../workflow-source/core/workflow_deployment_idempotency.md). ~~[main-016] `wk doctor`~~ ✅ · ~~[main-017] 채널 재실행 계약~~ ✅ (47차) · ~~[main-005] 드리프트 감지(페이로드 해시)~~ ✅ · ~~[main-019] 환경 pre-flight~~ ✅ (48차). 탐침은 이제 **7절**이다 (53차 `runtime_load` 신설 — 노출 미측정 한 칸을 측정으로 옮겼다). ~~[main-010] §7.0.2 의 '버전 상이' 셀~~ ✅ (53차 — 실측 + `installPath` 선언을 읽도록 교정). ~~[TASK-2026-08-14-main-009] 라벨 영어 전환~~ ✅ (53차 — 4단계 종료). ~~[main-004] wiki 3-step 하위 두 단계~~ ✅ (49차 — 1단계 은퇴 / 2단계 수리 / 3단계 재작성). **열린 후보**: ~~OKF v0.2 이행 ADR~~ ✅ (2026-08-20 ADR-026 로 전체 이행 완료, TASK-2026-08-20-main-003 — 이 줄이 그것을 안 따라와 58차가 낡은 후보를 다시 검토했다; 잔재였던 매니페스트 '0.1' 하드코딩은 58차 main-008 이 걷음) · ~~wiki L1→L2 갭 85개~~ ✅ (50차 — 계약을 4종으로 좁혀 닫음) · cross-host federation(MacBook, 시점 추후) · ~~[TASK-2026-08-13-main-004] mypy flake 관찰~~ ✅ (66차 close — 33/33 표본, mypy 실패 0).
- 원류: `main@06abaaf0` — [`active/main/session_handoff.md`](../../main/session_handoff.md) 의 기준선 · 주 작업 축 · 열린 task 5건 · §5 를 옮겨 적었다 (모 브랜치에는 쓰지 않았다). 옮겨 온 task 는 frontmatter `inherited_from` 로 원류를 갖고, 합류 아카이브 때 고친 것만 원본에 되돌려 적힌다.

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
- TASK-2026-10-02-main-006 Windows 로캘(cp949)에서 wk 가 UnicodeEncodeError 로 죽는다 — stdout 과 기본 인코딩 I/O 를 UTF-8 로 고정
- TASK-2026-10-02-main-007 Windows V3 백신이 wk.exe 를 평판 기반으로 차단한다 — pip 생성 console-script 런처 대체 진입 경로
## 3. 차단 작업

- 현재 `blocked` 작업:
- TASK-2026-08-25-main-017 MCP emit command 가 항상 python3 — PATH 에 python3 이 없는 Windows 에서 emit 설정으로 서버를 spawn 할 수 없다
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-09-30-main-001 minimax-code 가 플러그인 채널로 미지원 — 배포·드리프트 판정·재생성이 모두 kit 밖
- TASK-2026-10-19-feat-auto-20261019-a0afcf36-001 브랜치 네임스페이스 자동 seed — `main` 에서 이어받음
## 5. 다음 세션 시작 포인트

- (`main@06abaaf0` handoff §5 에서 이어받음 — 아래 14줄은 모 브랜치의 다음 시작 포인트다)
- (118차) **minimax-code 채널을 doctor 세 축에 편입** (TASK-2026-09-30-main-001 close) — 실측 정본: MiniMax Code 의 **활성 상태는 JSON 이 아니라 SQLite** 다 (`~/.minimax/v2/sqlite/runtime-state.sqlite` → `local_runtime_plugin_local_disabled` 표, **행 = 꺼짐**, `canonical_root` = 플러그인 디렉터리 절대경로). `mcode plugin disable` → 행 1개, `enable` → 행 0개 (2026-10-19 실측, mcode 0.6.2). claude-code 와 **정반대**라 부재가 꺼짐을 대신하지 않는다 — 행이 없으면 켜짐이다. `content_drift`(behind)·`plugin_enabled`(disabled)·`runtime_load`(재시작) 3축이 이 채널을 본다. 로더는 **MiniMax Code 데스크톱 앱**이다(`ps -Ao comm=` → `/Applications/MiniMax Code.app/Contents/MacOS/MiniMax Code`; CLI `mcode` 는 node 프로세스라 이름이 안 잡힌다).
- (118차) **이 호스트 §2.8 재적용 완료** — minimax 플러그인 1.19.0 → **1.20.1** (`python -m workflow_kit.minimax_plugin --apply`, 백업 `~/.minimax/plugin-backups/standard-ai-workflow-20261019T130050Z`, `.DS_Store` 는 소유자 판단으로 보존). **MiniMax Code 앱(pid 2767)이 재적용(22:00:50)보다 먼저 기동(21:41:44) — 앱 재시작 필요**(플러그인은 프로세스 시작 때 로드된다). 다음 세션 첫 확인: 앱 재시작 → `mcode plugin list` 로 스킬 5종 노출 확인 → `wk doctor --json` 의 `content_drift.behind` 에 minimax-code 가 없을 것.
- (118차) **main-006 · main-007 · main-017 은 이 호스트에서 닫을 수 없다** — 셋 다 **Windows 실물 실측** 이 남았다(006·007 은 코드가 이미 반영됐고 판정 근거만 부족 · 017 은 `--literal-command` 판정 기구까지 있고 완료 기준 2 만 남음). macOS 에서 코드를 더 고쳐도 근거가 늘지 않는다 — Windows 호스트에서만 닫는다.
- (117차) **verifier 실사용 개시** — task 를 done 으로 닫기 전에 `subagent_type=verifier` 를 부른다. 등록 때 `backlog-update --done-criteria` 를 반드시 같이 준다(기준 줄이 비면 verifier 가 막는다). 되주입 전수는 verifier 에게 '수리 부분을 빠짐없이 하나씩 되돌려라' 로 맡기면 작성자보다 넓게 찾는다. **minimax-code**: §2.8 절차 생김 — macOS 호스트 →1.20.1 적용 시 `python -m workflow_kit.minimax_plugin --apply` 후 `--json` 의 `in_sync` 로 확인, 앱 재시작 필요 여부와 `mcode plugin list` 인정은 그때 첫 실측. codex 3 · grok-build 1 프로세스가 1.20.1 이전 기동 — 재시작 필요.
- (116차) **v1.20.0 발행됨** (main-005) — 진입점 다이어트 3단계(정본 규칙 블록 3.6→2.7KB · bootstrap 템플릿 + `check_entry_budget` 8KB · `ensure-entrypoints --diet` 절 단위, 옛 생성물 해시는 `scripts/harvest_entry_sections.py`) + AI-native SDLC A1~A3(task Plan 절 · verifier · 검사 약화 차단 hook) + MiniMax Code 채널. 이 호스트 §2.8 완료 — claude-code · codex 재시작 필요. ~~verifier 실측 대기(main-003)~~ ✅ 117차. macOS: §2.8(→1.20.0, MiniMax 포함 — RELEASE.md §2.8 에 MiniMax 절차 없음). 새 발행이 진입점 템플릿을 바꾸면 harvest 재실행. main-006 수리는 v1.20.1 로 발행됨 — macOS §2.8 은 →1.20.1.
- (합류 `feat/auto-20261002-4a5d394c@e98bc3a6`, 2026-10-03) feat/auto-20261002-4a5d394c 워크스페이스 seed (2026-10-02). 아직 작업 전이다. — 완료 3건(TASK-2026-10-02-feat-auto-20261002-4a5d394c-001, TASK-2026-10-02-feat-auto-20261002-4a5d394c-002, TASK-2026-10-02-feat-auto-20261002-4a5d394c-003) · 이월 0건 · 되돌려 적음 0건. 기록: [`archived/feat/auto-20261002-4a5d394c/session_handoff.md`](../../../archived/feat/auto-20261002-4a5d394c/session_handoff.md) · [합류 기록](../../main/sessions/merge_feat-auto-20261002-4a5d394c_2026-10-03.md)
- (합류 `claude/remote-sync-status-1ce0a3@f1a4b633`, 2026-10-03) claude/remote-sync-status-1ce0a3 워크스페이스 — `main@309c9ddf` 에서 이어받음 (2026-10-02, macOS 호스트). **이 브랜치 작업 2건 done (TASK-2026-10-02-claude-remote-sync-status-1ce0a3-002 M-007/WBS-7.4 · -003 M-007/WBS-7.2)** — 이 호스트 v1.19.0 §2.8 재적용(4채널 + MCP 해석기… — 완료 2건(TASK-2026-10-02-claude-remote-sync-status-1ce0a3-002, TASK-2026-10-02-claude-remote-sync-status-1ce0a3-003) · 이월 0건 · 되돌려 적음 0건. 기록: [`archived/claude/remote-sync-status-1ce0a3/session_handoff.md`](../../../archived/claude/remote-sync-status-1ce0a3/session_handoff.md) · [합류 기록](../../main/sessions/merge_claude-remote-sync-status-1ce0a3_2026-10-03.md)
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
- TASK-2026-10-02-main-003 — 원격 없는 저장소의 worktree 는 자동 seed · 이어받기가 안 돈다 — 기본 브랜치 판정이 현재 브랜치로 떨어진다

## 6. 남은 리스크

- **MiniMax Code 앱 재시작 전까지 새 스킬이 노출되지 않는다** — 118차 §2.8 재적용(→1.20.1)이 이미 끝났으므로 남은 건 재시작뿐이다. 재시작 전 `wk doctor` 는 `runtime_load` 에서 minimax-code 호스트가 "설치보다 먼저 기동" 으로 보고한다(그건 결함이 아니라 사실이다).
- **doctor 의 minimax-code 활성 판정은 SQLite 한 곳에만 의존한다** — `~/.minimax/v2/sqlite/runtime-state.sqlite` 가 다른 경로로 옮겨가거나 MiniMax Code 가 표 이름을 바꾸면 판정이 "모름" 으로 물러난다(통과로 세지 않는다). MiniMax Code 를 업그레이드할 때 이 경로를 다시 실측할 것.
- **Windows 실측 3건이 그대로 남았다** — main-006 · 007 · 017. 이 호스트(macOS)에서는 닫을 수 없다.
- **이 브랜치의 §2.8 재적용은 kit 의 다음 버전이 나오면 또 뒤처진다** — doctor 의 `content_drift.behind` 가 그 신호다. behind 에 minimax-code 가 뜨면 §2.8 를 다시 돌린다.
