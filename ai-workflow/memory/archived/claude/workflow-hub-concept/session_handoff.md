# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-11-20
- 관련 문서: [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: claude/workflow-hub-concept 워크스페이스 — `main@fff952cd` 에서 이어받음 (2026-11-20). **137차 (2026-11-21, Linux 호스트) — 정리: kit 결함 2 수리(-012 현재 마일스톤 병행 선언 기준 · -013 §5 서두 회차 줄 누적형 → 이 브랜치 §5 29KB→6KB), 1.x 실측 대기 4건 blocked, 병합 브랜치 2개 삭제 + main 에서 메모리 아카이브(`bb943c81`) 후 main 병합. 다음 M-036.** **136차 (2026-11-20 ~ 21, Linux 호스트) — 2.0 허브: M-031 requirements · M-032 design(ADR-033 Accepted · PURPOSE 2.0판 적용) · M-033 코어 · M-034 부트스트랩 · M-035 판정 · 기억 done. 다음 M-036.** 정본: `docs/planning/workflow-hub-requirements-2026-11.md` (R0~R16 · 실측 §16 · 결정 Q1~Q10) · `workflow-source/core/hub_spec.md` (DS1~DS9) · `core/hub_workflow_standard.md` · 코드 `workflow_kit/hub/` (DB 판 4, 도구 34종) · 검사 `check_hub_core` · `check_hub_bootstrap` · `check_hub_judge` · `check_hub_memory`. 1.x 결함 수리 1(-007 catch-all 오류 원인) · 1.x 판정 함수 데이터 입구(동작 불변). **이 브랜치는 1.x 분기(R16.5) 전에 main 에 합치지 않는다** (PURPOSE 2.0판). 이전 기준선 — 135차 후속 (2026-11-20): M-030 concept done — 개념 문서 `docs/planning/workflow-hub-review-2026-11.md`, 소유자 방향 H1~H14 (상세는 그 문서 · ADR-033), 로드맵 M-031~M-040. 가드 hook 스위치 `b0e3dde9` — `<git common dir>/workflow-simplified-verification` 표식이 있으면 `--no-verify` push 만 통과(이 Linux 클론에만 표식, 기간 끝나면 지운다). **검증 간소화 기간 (소유자 2026-11-20)**: verifier · push 전 전량 게이트 생략, `--changed` + 스모크 뒤 `--no-verify` push, 발행 때만 전량. 모 브랜치 기준선: 134차 (2026-11-19, macOS Mac mini) — 정본 v1.27.0 + 미발행 수리 3건 (상세는 [`active/main/session_handoff.md`](../../../active/main/session_handoff.md)).
- 현재 주 작업 축: **로드맵·마일스톤·WBS 진척 관리 + SDLC 온보딩 기본 — 60차(2026-08-25) 소유자 지시로 확정.** ADR-027 accepted, 정본 스펙은 [`roadmap_milestone_wbs_spec.md`](../../../../../workflow-source/core/roadmap_milestone_wbs_spec.md) (M-001 design 완료, 구현은 M-002~M-006 단계 실행 — 스펙 §10 이 임시 로드맵 정본). 직전 축(배포 일관성·멱등성)은 ✅ gap 4개 전부 닫혔다 (2026-08-18, 48차). 정본은 [`workflow_deployment_idempotency.md`](../../../../../workflow-source/core/workflow_deployment_idempotency.md). ~~[main-016] `wk doctor`~~ ✅ · ~~[main-017] 채널 재실행 계약~~ ✅ (47차) · ~~[main-005] 드리프트 감지(페이로드 해시)~~ ✅ · ~~[main-019] 환경 pre-flight~~ ✅ (48차). 탐침은 이제 **7절**이다 (53차 `runtime_load` 신설 — 노출 미측정 한 칸을 측정으로 옮겼다). ~~[main-010] §7.0.2 의 '버전 상이' 셀~~ ✅ (53차 — 실측 + `installPath` 선언을 읽도록 교정). ~~[TASK-2026-08-14-main-009] 라벨 영어 전환~~ ✅ (53차 — 4단계 종료). ~~[main-004] wiki 3-step 하위 두 단계~~ ✅ (49차 — 1단계 은퇴 / 2단계 수리 / 3단계 재작성). **열린 후보**: ~~OKF v0.2 이행 ADR~~ ✅ (2026-08-20 ADR-026 로 전체 이행 완료, TASK-2026-08-20-main-003 — 이 줄이 그것을 안 따라와 58차가 낡은 후보를 다시 검토했다; 잔재였던 매니페스트 '0.1' 하드코딩은 58차 main-008 이 걷음) · ~~wiki L1→L2 갭 85개~~ ✅ (50차 — 계약을 4종으로 좁혀 닫음) · cross-host federation(MacBook, 시점 추후) · ~~[TASK-2026-08-13-main-004] mypy flake 관찰~~ ✅ (66차 close — 33/33 표본, mypy 실패 0).
- 원류: `main@fff952cd` — [`active/main/session_handoff.md`](../../../active/main/session_handoff.md) 의 기준선 · 주 작업 축 · 열린 task 6건 · §5 를 옮겨 적었다 (모 브랜치에는 쓰지 않았다). 옮겨 온 task 는 frontmatter `inherited_from` 로 원류를 갖고, 합류 아카이브 때 고친 것만 원본에 되돌려 적힌다.

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
- TASK-2026-11-21-claude-workflow-hub-concept-013 handoff §5 서두의 회차 줄이 예산 밖에서 쌓인다 — 누적형으로 세고 이관
- TASK-2026-11-21-claude-workflow-hub-concept-012 로드맵 현재 마일스톤을 병행 선언 기준으로 — 상시 운영 M-007 이 늘 '현재' 로 보고되던 것
- TASK-2026-11-21-claude-workflow-hub-concept-011 허브 콜사인별 기억 — handoff · 세션 끝 · compact 체크포인트 · state.json v1 · 보관
- TASK-2026-11-21-claude-workflow-hub-concept-010 허브 로드맵 — 마일스톤 · WBS · WBS 게이트 · 진척 파생
- TASK-2026-11-21-claude-workflow-hub-concept-009 허브 판정 — 계획 린트 · done 게이트 · 결정 응답 (1.x 와 같은 함수)
- TASK-2026-11-21-claude-workflow-hub-concept-008 허브 세션 시작 확인 · 하네스 등록 안내 페이지
- TASK-2026-11-21-claude-workflow-hub-concept-007 허브 지침 렌더링 — 표준 규칙(2.0판) · 프로젝트 지침 · 하네스 4종 · 판 · 로컬 수정 감지
- TASK-2026-11-21-claude-workflow-hub-concept-006 허브 부트스트랩 셋업 — 쓰기 지시 · .gitignore 먼저 · 확인 도구
- TASK-2026-11-21-claude-workflow-hub-concept-005 허브 코어 — 원격 MCP 골격 · 부트스트랩 묶음 · 인증 경계
- TASK-2026-11-21-claude-workflow-hub-concept-004 허브 코어 — task CRUD · 이력 · version 409 · 맡기
## 5. 다음 세션 시작 포인트

- (137차 후속, 2026-11-21) **R16.5 1.x 분기 완료 → main 병합.** 소유자 지시로 `release/1.x` 를 `main@bb943c81`(v1.29.0 + 메모리 커밋)에서 분기 · push 한 뒤 이 브랜치를 main 에 PR 없이 병합했다. 1.x 결함 수리 · 1.x patch 발행은 `release/1.x` 머리에서 (R16.1 · R16.2), 2.0 작업은 이제 main 에서. 이 브랜치는 합류 반영 뒤 더 쓰지 않는다. plugin/ 은 안 바뀌었으므로 main 채널 소비자는 여전히 1.x 플러그인을 받는다 — 2.0 이 plugin/ 을 바꾸기 전에 R16.4 안내 판(채널 재등록 명령)이 필요하다.
- (137차, 2026-11-21) **정리 끝 → 다음 일 M-036 WBS-36.1** (위키 페이지 · ingest · index/log · lint, E2). 시작할 때 M-036 을 `in_progress` 로 열면 `current_milestone_id` 가 M-036 이 된다(-012 규칙, 지금은 M-028). ①병합된 `claude/consumer-readonly-session-start` · `claude/remote-sync-check-234c32` 로컬 · origin 삭제, 메모리는 main 에서 합류 반영 · 아카이브(`bb943c81`, -002 main 이월) 후 이 브랜치에 main 병합 ②1.x 실측 대기 4건(-006 · -007 Windows, 234c32-002 · -004 소유자) blocked ③kit 수리 2(-012 · -013) — 1.x 결함 수리라 다음 1.x 발행 노트에 싣는다 ④`/var/tmp` 지난 검증 디렉터리 1.4GB 정리.
- (136차, 2026-11-20) **결함 수리 1 + M-031 착수.** ①task -007 close — catch-all 오류 결과가 예외 이름만 싣던 결함 수리: `common/errors.py` `exception_context` · `describe_exception`, 6곳 적용, 오류 문안 끝에 `ValidationError(WbsNode) — title: …200 characters` 꼴의 첫 원인, 검사 `check_exception_context` (8 case, 되주입 4종 red). 1.x 결함 수리라 다음 1.x 발행 노트에 싣는다. ②task -008 close — WBS-31.1 requirements 초판 `docs/planning/workflow-hub-requirements-2026-11.md` (R0 불변 · R1~R15 · 95개 요구 전부 [검증] · 추적표 concept 43항목 누락 0). ③task -009 close — **소유자 결정 Q1~Q5 반영** ("권고안대로, Q4 는 arcturus 과제 대시보드 참조"): Q4 = 화면 로그인 없음 · 브라우저가 콜사인 등록 → 토큰 브라우저 저장소 → `Bearer`, 토큰 없는 화면 요청은 공용 `web` 토큰(기본 꺼짐), 근거 arcturus-port `8d24fcd7` (R13.2a). 후속 후보: `check_entry_points` 의 `--help` 하위 프로세스 timeout 10s 가 load 15 에서 red (오늘 2회, 단독 green). ④task -010 close — **WBS-31.2 실측** (requirements §16): S1 판정 핵심은 그대로 · 얇은 입구, 리팩터는 입력 수집 층(상태 생성 · handoff 파서 · 로드맵 수집)만 · S2 V-1/V-4/점수 인자화 필요, `bidir_link` 그대로 · S3 Claude Code · Codex · MiniMax 원격 MCP 실측 지원, Grok 연결 · 인증만(모델 자격 없음), **Antigravity 는 `${VAR}` 헤더 미확장 → Q7 신설**. 1.x 결함 후보 2: `bidir_link.py` `entry_id_stem` 미정의/잔존 · `score_freshness` 가 대상이 줄면 점수 상승. ⑤task -011 close — **지원 하네스 4종 확정 (Q8)**: Claude Code · Codex · MiniMax Code · Antigravity (R2.8), Grok 등은 실측 뒤 추가 결정. ⑥task -012 close — Q7 권고안 (R2.5a: Antigravity 토큰은 사용자 범위에만 + 경고). ⑦task -013 close — **WBS-31.3**: requirements §17.1 PURPOSE 2.0 개정안 · §17.2 R16 1.x 유지보수(결함만 · 2028-07-20 · 안내 판 · 분기 · 1.x 소비자 채널 보호). **M-031 WBS 3개 완료.** ⑧task -014 close — **Q6 · Q9 · Q10 권고안 확정** (1.x 2028-07-20 까지 결함 수리 · PURPOSE 2.0판은 ADR-033 Accepted 때 적용 · 2.0 은 같은 이름의 kit 플러그인 채널을 내지 않음), **requirements 종결 · M-031 done** (선언 · 파생 done 1.0). ⑨task -015 · -016 · -017 close — **M-032 design 초판 `workflow-source/core/hub_spec.md`** (WBS-32.1 스키마 21표 · 32.2 도구 · HTTP 거울 · 오류 코드 · 32.3 흐름 7 · requirements R 106개 대응 누락 0). M-032 0.75. ⑩(2026-11-21) TASK-2026-11-21-…-001 close — **DS1~DS9 확정 · ADR-033 Accepted · PURPOSE 2.0판 적용 (`purpose_version: 2`) · M-032 done**. `check_purpose_concept_v0_9_2` 의 판 1 고정을 형식 계약으로 고침, `active/main/state.json` purpose 키 재생성. **주의: 이 브랜치를 main 에 합치기 전에 1.x 분기(R16.5)** — 그대로 합치면 1.x 줄의 PURPOSE 가 2.0판이 된다. ⑪(2026-11-21) TASK-2026-11-21-…-002~005 close — **M-033 허브 코어 done**: `workflow_kit/hub/` (errors · gitkey · db · store · tools · app) + `python -m workflow_kit hub serve|backup|admin` + `workflow_kit[hub]` (mcp>=1.27,<2). 검사 `check_hub_core` 10 case · 되주입 6종. `check_state_json_generated` case 5 를 현재 브랜치 생성물로(main 고정이 네임스페이스 규칙과 충돌) · `active/main/state.json` 은 origin/main 판으로 되돌림. 1.x 결함 후보 추가: `sdk_matrix` 의 tmp 가 저장소 안이라 `check_mcp_tool_output_contracts` case 5 가 매트릭스에서만 red. ⑫(2026-11-21) TASK-2026-11-21-…-006~008 close — **M-034 done**: 셋업 쓰기 지시(.gitignore 확인 전 토큰 지시 없음 · env · 진입 파일 렌더 영역 · .mcp.json 환경 변수 참조 · codex 명령 · agy 사용자 범위 + 경고) · 확인 도구(해시 · check-ignore 대조) · 표준 규칙 2.0 정본 `core/hub_workflow_standard.md` + 생성 스냅샷 · 세션 시작 2단(start / fast-forward / 멈춤 / 미확인 · 지침 [바뀜] · 없는 커밋) · 안내 페이지 `/` · DB 판 2. 검사 `check_hub_bootstrap` 8 case · 되주입 6종. ⑬(2026-11-21) TASK-2026-11-21-…-009~011 close — **M-035 done**: 1.x 판정 함수에 데이터 입구(enforce_plan_contract 선택 인자 · judge_wbs · assemble_roadmap · derive_state 콜백, 1.x 동작 불변) + `hub/judge.py`(계획 린트 · done 게이트 · 결정 응답 · WBS 게이트 · 로드맵 진척 — `check_hub_judge` 가 1.x 와 대조) + `hub/memory.py`(콜사인별 handoff · 세션 끝 · compact · state.json v1 은 1.x 배치로 펼쳐 같은 생성기). DB 판 4. **다음 일**: ①**M-036 착수** (위키 · memory_index · 들여오기/내보내기 · 오프라인 보낼편지함) ②Antigravity 도구 호출 경로 재실측 ③1.x 결함 후보 3: `bidir_link` `entry_id_stem` · `score_freshness` 조용한 좁힘 · `check_entry_points` `--help` timeout. `--changed` 중 `check_entry_points` · `check_v0_7_4_followup` 이 load 17 에서 timeout red → 단독 green (부하성).
- (135차 후속, 2026-11-20) **다음 일**: ①2.0.0 로드맵 M-031~M-040 작성됨 (2.0.0 = M-033~M-039 전부, 1.x 는 결함 수리만 병행) — **M-031 requirements 착수** (WBS-31.1 요구 목록 · 31.2 design 전 실측 · 31.3 PURPOSE 2.0 판) ②kit 결함 후보: `backlog-update` 가 예외를 `ValidationError` 이름만 내고 원인(필드 · 메시지)을 감춘다 — 이번에 WBS 제목 200자 초과가 그렇게 숨었다 ③이 호스트의 실행 중 claude · codex 재시작 뒤 1.29.0 로드 확인 ④design 전 조사 두 가지 — 판정 함수(`plan_claims` · 게이트 · 상태 생성)를 데이터만으로 부를 수 있는지, `check_wiki_*` · `score_wiki_*` · `bidir_link` 가 펼친 임시 디렉터리에서 같은 판정을 내는지 · 하네스별 원격 MCP(HTTP) 지원 실측 (kit MCP 는 지금 stdio 전용)
- 실제 작업은 `python -m workflow_kit backlog-update` 로 새 task 를 만들어 기록한다.
- 작업 범위를 벗어나는 변경은 다른 워크스페이스와 충돌할 수 있으므로 backlog 에 별도 task 로 남긴다.

- 누적 기록은 [`sessions/handoff-notes_*.md`](./sessions/) (기록 1절) 로 이관됐다 — 최신이 위, 세션 시작에 읽지 않는다.

#### 작업 후보 — 정본은 `state.json` 의 `planned_items` · `in_progress_items`

- TASK-2026-11-13-claude-remote-sync-check-234c32-005 — 주장 트리 계획 Windows 실측 — os.link 공개 · 배타 이동 · 잠금 (NTFS) — Windows 호스트에서

## 6. 남은 리스크

- 아직 검증된 산출물이 없다.
