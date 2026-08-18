# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-19 (49차 세션 — main-004 close: **wiki L2 파이프라인 회생**)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **49차 세션 — main-004 close: wiki L2 파이프라인 회생 (`wk wiki-emit` 3-step → 2-step, 검사 263→264, 전량 2축 green).** 상세는 [49차 세션 기록](./sessions/wiki_l2_pipeline_revival_2026-08-19.md). 핵심은 크래시 두 개가 아니라 **세 단계가 각각 다른 이유로 이미 유효하지 않았다**는 것이었다 — 그래서 '고쳐서 rc=0 을 만든다' 가 오답이었다. **1단계는 소유권 충돌**: write 대상 4개가 전부 무너져 있었고(`state.json` 은 정본 §11.2 의 생성 산출물이라 이 단계가 **두 번째 writer** 였다 · `work_backlog.md` 는 v0.14.0 에서 사라짐 · `memory/log.md` write 는 죽은 코드 · `wiki/log.md` 는 2026-06 하드코딩), 은퇴시키되 **조용한 no-op 이 아니라 사유를 말하고**(rc=0) 함수 자체를 지웠다 — 분기로만 막으면 다음 사람이 다시 부른다. **2단계는 vault 화석 3종이 전부 실행 경로 위**에 있었고(이중 경로 · `parts.index("raw")` · **정의된 적 없는 `VAULT_ROOT`**) v0.7.17 이후 **한 번도 끝까지 실행된 적이 없었다**; 고쳐도 할 일이 없던 진짜 이유는 게이트가 `<needs content>` **일회성**이라 한 번 emit 된 page 가 영원히 대상이 아니었던 것 — **신선도 게이트**로 바꾸고, 본문 전체를 갈아끼우게 되므로 `> Generated:` 표식 없는 page 는 **manual 로 보고 건드리지 않는다**. **3단계는 2026-06-14 스냅샷 축자 재생성**이었고 `last_touched` 를 그 날짜로 되돌렸다 — 현재 SSOT 파생으로 재작성, `last_touched` 는 실제 emit 일자, 바이트가 같으면 write 0(`unchanged`), L1 없는 stub 은 `missing_l1` 로 밝힌다. **날짜 박힌 붕괴를 막았다**: L2 4개가 `2026-07-22` 라 **2026-08-21 에 lifecycle 5.0→0.0 / overall 4.71 A→3.88** 이 예약돼 있었고, 갱신할 유일한 도구가 67일 전으로 되돌리고 있었다(7/22 는 사람이 커밋 `dcbf2af7` 로 올린 값). **검사가 apply 를 잰다** — 이전 8 cases 는 전부 dry-run 이라 두 크래시를 구조적으로 못 봤다; `check_refresh_wiki_memory` 11 재작성 + `check_wiki_emit_pipeline` 11 신설, 되주입 6종 red 실증.
- 직전 기준선: **48차 세션 종료 — 배포 일관성·멱등성 축의 gap 4개가 전부 닫혔다 (task 5건 close, push 5회, 전량 2축 매번 green, 검사 262→263).** 상세는 [48차 세션 기록](./sessions/deployment_axis_closed_and_okf_interop_2026-08-18.md). 직전 항목은 **main-019**(환경 pre-flight): 설계의 핵심은 `environment` 절과 **다른 물건**이라는 것이었다 — 그쪽은 *지금 이 인터프리터가 검사를 돌릴 만한가*, `preflight` 는 *어느 채널로 설치할 수 있는가*. 탐침이 4절 → **6절**이 됐다(environment · preflight · project_scope · global_scope · drift · content_drift). **축은 측정과 선언의 분리**다: 실행 파일은 `shutil.which` 로 실제로 재고, 네트워크 도달성·내려받은 아카이브는 `declared_unmeasured` 로 남긴다. `installable: true` 는 "실행 파일 전제 충족" 이지 "설치 성공" 이 아니다 — **모름을 통과로 세면 그게 거짓 안심**이다(저장소 규칙 *모름 ≠ 안전*). 모든 플러그인 채널의 공통 전제로 `wk`·`python3` 을 명시했다: 둘 중 하나가 없으면 **설치는 성공해도 기능이 없는 상태**가 된다. `CHANNEL_PREREQUISITES` 가 정본이고 `INSTALLATION` §7.0.0 표는 파생 — `check_installation_usage` case 6 이 채널 이름뿐 아니라 **측정 대상 실행 파일까지** 대조해 "채널은 있는데 전제만 낡은" 상태를 잡는다. 이 호스트 실측: 6채널 중 **gemini-cli 만 막힘**(`gemini` 부재) — §7.0.2 의 '미실측' 과 같은 사실을 도구가 스스로 말한다. `check_deploy_doctor` 13→16 cases, 되주입 2종 red. 부수: §7.0.1 의 '한계' 문단이 main-005 이후 사실이 아니어서 고쳤다.
- 그 이전 기준선: **48차 세션 (이어서) — main-006 close: OKF 상호운용을 자기 선언이 아니라 실측으로 (전량 2축 green).** 소유자가 조사를 지시한 [langchain-ai/openwiki](https://github.com/langchain-ai/openwiki) 가 **우리와 같은 OKF v0.1** 을 쓴다는 데서 출발했다 (저장소에 언급 0건 — 서로 모르는 채 같은 포맷에 도착). 우리 wiki 71장을 번들로 뽑아 SPEC 원문 + openwiki 가 커밋해 둔 `openwiki/` 번들과 대조. **① SPEC 이 v0.2 로 움직였다** — ADR-006 은 2026-06-16 에 v0.1 을 고정했다. 변경 3건(`timestamp`→`generated.at` · `# Citations`→`sources` · **`status` 가 정규 필드로 승격**). 앞의 둘은 legacy fallback 이 열려 있다. **② `status` 만 실질 위험** — 우리 값은 `active` 42·`accepted` 25·`draft` 2·`proposed` 1 인데 v0.2 어휘는 `draft|stable|deprecated` 다. SPEC 의 관용 보장은 *unknown key* 에만 걸리므로 정규 필드가 된 `status` 에는 안 걸린다 — v0.2 소비자가 `stable` 필터를 걸면 69장이 빠진다. **③ 다른 생산자와는 실제로 읽힌다** — 둘 다 `okf_version: "0.1"` 선언, `index.md` 예약, **둘 다 `log.md` 미발행**, `type/title/description/tags`, 상대 링크. **④ 그런데 `type` 으로 라우팅은 원리적으로 불가능** — SPEC 이 `type` 을 registry 없는 자유 문자열로 정의해서, 우리 닫힌 enum 과 openwiki 의 자유 산문(`Architecture overview`)이 **둘 다 적합**하다. 어느 쪽 결함도 아니다. **고친 것 2건**: Citations 헤딩 h2→**h1**(SPEC §8, v0.2 의 legacy fallback 도 h1 을 본다 — h2 면 양쪽에서 안 걸린다) · wiki score 대시보드가 **frontmatter 없이 생성**돼 export 가 71장 중 1장을 조용히 빠뜨리던 것(lint 는 위치·index 만 봐서 아무도 몰랐다; 생성물이라 템플릿에서 emit). `check_okf_export` 18→20 cases(h1 고정 + **자기 적용**), 되주입 2종 red. **v0.2 이행은 ADR 이 필요해 남겼다** — 최소안은 `status` 어휘 매핑.
- 그 이전 기준선: **48차 세션 (이어서) — main-005 close: 드리프트 감지를 마커에서 페이로드 해시로 (배포 축 gap 3 해소, 전량 2축 263/263 green).** 47차에 관측만 해 둔 상태 — 버전은 같은데 내용만 낡은 설치본 — 을 이제 `wk doctor` 가 **본다**. `content_drift` 절 신설. **전제가 먼저 막혔다**: 정본 렌더러 `render_agent_plugin()` 이 설치본에서 통째로 죽어 있었다(`_project_table()` 이 체크아웃 경로만 봤다) — 소비자 호스트에서 대조가 성립하려면 그것부터 살아야 해서 설치 metadata fallback 을 넣었다(main-003 과 같은 결함 계열). 지키는 것 넷: ①**정본은 생성기와 같은 함수** — 기준을 따로 두면 기준이 드리프트한다 ②**기대치는 채널별 파생**(`include_prefixes`) — codex 는 매니페스트·MCP·skills 만 담아서 payload 20개를 기대하면 정상 설치가 *없음 10건* 으로 보고됐다(실측) ③**사본 거주지도 registry**, 사본 없는 채널(pi-dev)·미실측(gemini-cli)은 `not_applicable` 로 밝힌다 ④**report-only 유지**. `check_deploy_doctor` 9→13 cases, 되주입(내용 비교 제거)으로 핵심 case red 실증. 이 호스트 실측: claude-code 12개·codex 10개 **in-sync**. 컨셉 §7 gap 3 → ✅, INSTALLATION §7.0.2 꼬리를 '한계' 에서 '복구 열' 로. **배포 축 잔여는 [main-019] 환경 pre-flight 하나다.**
- 그 이전 기준선은 [`baselines.md`](./baselines.md) 에 있다 (이관 51건, 최신이 위).

- 현재 주 작업 축: **배포 일관성·멱등성 — ✅ gap 4개 전부 닫혔다 (2026-08-18, 48차).** 실행형 잔여가 이 축에는 없다.**다음 축은 소유자 판단 대기.** 정본은 [`workflow_deployment_idempotency.md`](../../../../workflow-source/core/workflow_deployment_idempotency.md). ~~[main-016] `wk doctor`~~ ✅ · ~~[main-017] 채널 재실행 계약~~ ✅ (47차) · ~~[main-005] 드리프트 감지(페이로드 해시)~~ ✅ · ~~[main-019] 환경 pre-flight~~ ✅ (48차). 탐침은 6절이다. **release 경계 대기** — [TASK-2026-08-14-main-009] 라벨 영어 전환은 `TASK_FIELD_LABELS` 한 줄만 남았다. ~~[main-004] wiki 3-step 하위 두 단계~~ ✅ (49차 — 1단계 은퇴 / 2단계 수리 / 3단계 재작성). **열린 후보**: OKF v0.2 이행 ADR(main-006 후속, `status` 어휘가 실질 위험) · wiki L1→L2 갭 85개(계약 존폐가 미결 — 근거였던 외부 vault 는 v0.7.17 에 사라졌다) · cross-host federation(MacBook, 시점 추후) · [TASK-2026-08-13-main-004] mypy flake 관찰.
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
- TASK-2026-08-14-main-009 task SSOT 4단계 — 본문 라벨 영어 전환 (release 경계)
## 3. 차단 작업

- 현재 `blocked` 작업:
-
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-08-18-main-004 wiki 3-step 파이프라인의 하위 두 단계가 죽어 있다 — 스키마·레이아웃 드리프트
- TASK-2026-08-14-main-019 환경 전제 pre-flight — venv/PEP 668/오프라인 전제를 도구가 선검사
- TASK-2026-08-18-main-006 OKF 상호운용 실측 — 다른 생산자의 번들과 대조
- TASK-2026-08-18-main-005 드리프트 감지 — 마커가 아니라 페이로드 해시로 비교
- TASK-2026-08-18-main-003 배포본에서 죽는 workflow-source 경로 참조 — wk 명령 6종 실측
- TASK-2026-08-18-main-002 rollover-baselines 가 실행마다 포인터 줄을 하나씩 쌓는다
- TASK-2026-08-14-main-017 채널별 재실행 계약 표 — 5개 플러그인 채널의 재설치/업데이트 시 행동을 §7.0 에 고정
- TASK-2026-08-18-main-001 AGENTS.md 를 공유 진입점으로 합친다 — oh-my-codex 계약과 워크플로우 규칙 공존
- TASK-2026-08-16-main-003 check_deprecation_3rd_cycle 의 제외 목록이 죽어 있다 — rel 기준과 제외 항목 기준이 어긋난다
- TASK-2026-08-16-main-001 backlog-update update 모드의 새 daily index 이월 결함 — 두 번째 task 부터 cannot_determine 조용한 스킵
그 이전 완료 항목은 [3차 세션 기록](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md)·[2차 세션 기록](./sessions/adr006_retrospective_and_calibration_2026-08-10.md)과 각 task 파일에 있다.

## 5. 다음 세션 시작 포인트

### ▶ 지금 할 일 — 소유자 판단 대기

배포 축은 48차에 닫혔고, 49차에 [main-004] wiki L2 파이프라인까지 닫혔다.
**다음 축은 소유자가 고른다.** 상세는
[49차 세션 기록](./sessions/wiki_l2_pipeline_revival_2026-08-19.md).

후보 셋 (준비 상태 순):

1. **wiki L1→L2 갭 85개 — 계약 존폐 결정** — 49차가 남긴 유일한 미결.
   `emit_wiki_l2_body` 는 이제 동작하지만 **살아 있는 입력이 없다**(후보 0).
   `.gitkeep` 계약은 L1 wiki page 마다 L2 파생 뷰를 두라고 하는데, 그 근거였던
   외부 vault retrieval 은 **v0.7.17 in-repo 전환 때 사라졌다** — in-repo 에서
   L1 은 이미 검색 가능하므로 85장은 절삭 사본 ~170KB 증가일 뿐이다.
   둘 중 하나: `--bootstrap-missing` 을 켜 계약대로 채우거나, 계약을
   'L2 = memory 파생 4종' 으로 좁힌다. **어느 쪽이든 한 줄이다.**
2. **OKF v0.2 이행 ADR** — ADR-006 이 v0.1 을 명시 고정했으므로 새 ADR 없이
   바꾸지 않는다. 지금 당장의 상호운용 손실은 **없다**(openwiki 도 v0.1).
   위험은 v0.2 소비자가 등장할 때. 최소안은 `status` 어휘 매핑
   (`active`/`accepted`→`stable`, `proposed`→`draft`), 우리 어휘는 확장 키로 보존.
3. **[main-009] 라벨 영어 전환** — release 경계 대기. `TASK_FIELD_LABELS` 한 줄만
   남았고 case 10 이 안전을 선실증했다.

관찰 축: cross-host federation(MacBook, 시점 추후) · mypy flake · memory_index 3-tuple.

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
