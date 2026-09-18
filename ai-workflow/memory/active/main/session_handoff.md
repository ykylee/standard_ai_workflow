# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-09-18 (79차 세션 **종료** — plex 호스트의 채널이 5주째 v1.1.8-beta 였다: content_drift 해시가 지목, 4채널을 v1.9.4 in-sync 로 정렬 + CLAUDE.md 포크 병합(렌더러 함수 대조, 채택 0) (task 2건) / 78차 세션 **종료** — WBS-7.1 무기한 연기 처리(main-017 → blocked) + backlog-update 의 --task-brief 를 update 에서 선택 인자로(additive) + 자기 오진 2건 철회 (task 1건) / 77차 세션 **종료** — session-start 가 매번 내던 health 0 / scope creep 10건이 오탐이 아니라 지표 결함 3건임을 실측하고 판정으로 종결 + **v1.9.4 발행·전 채널 재적용** + emit 판정 공백 보강 + §7.0.2 명령 형태 교정 (task 5건) / 76차 세션 **종료** — 예제 산출물 드리프트에서 생성기 결함 2건(handoff fallback 부재 · 거짓 cast)을 파내 정본과 판정으로 종결 + 75차 수리의 사본 1건 제거 + §7.0.2 grok 복구 열 오기 + task ID 호스트 간 충돌(거짓 보증) + **소비자 배포처 모순의 뿌리**(설치본에서 모듈 앵커 증발) 수리 + **v1.9.3 발행·전 채널 재적용** (task 8건 close) / 75차 세션 **종료** — 발행마다 손이 가던 두 자리를 파생과 판정으로 종결(README 헤더 줄 리터럴 4곳 · 누적 smoke 노트 왕복) + **v1.9.2 발행** + 이 호스트 전 채널 재적용 / 74차 — session-start 불일치 경고를 도구 결함으로 확정·수리 + **v1.9.1 발행** + 이 호스트 전 채널 적용 / 73차 세션 — **v1.9.0 발행** (필수 CI 게이트 + done 강등 보존) + 미발행 잔여 0 / 72차 세션 **종료** — 손 목록·리터럴·주장을 파생으로 전환 5건 + **v1.8.1 발행** + 발행 게이트가 필수 CI 전수를 보고 차단 / 71차 — v1.8.0 발행 완료 + 등급 전수 재평가(1.8.0 유지) + guarantee 은퇴 행 복원 / 70차 — 탐침 자기 측정(kit_provenance) / 69차 — 현재 주장 3부류 고착 수리 / 68차 — 탐침 침묵 3건 / 67차 세션 **종료** — gemini-cli 지원 종료 + antigravity 플러그인 채널 합류(실측) + 호스트 4채널 1.7.0 정렬 / 66차 — meta-watch 선언 보급 완주 / 65차 — '자기 위치 오인' 결함족 전수 마감 / 64차 — TDAD 축 완주 + v1.7.0 발행)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **79차 세션 (2026-09-18, plex 호스트/linux) — 이 저장소가 배포하는 물건을 *이 호스트가 5주째 못 받고 있었다*. 코드는 한 줄도 안 건드렸고, 드러난 것이 이 세션의 실질이다 (task 2건 close: 2026-09-18-main-002 · -003).** **① '이 호스트' 는 쓴 사람의 호스트다**: 77차가 `v1.9.4 발행 + 이 호스트 소비자 채널 재적용` 을 done 으로 남겼지만 그것은 macOS 호스트였고, plex 의 claude-code 설치본은 **v1.1.8-beta(2026-08-13)** 그대로였다 — 5주. 그리고 그 낡음은 **마커로는 안 보인다**: 실제로 지목한 것은 `content_drift` 의 페이로드 해시였다(다름 7 / 없음 4 — 스킬 4종 SKILL.md 전부 + hooks.json + rules.md, agents/openai.yaml 부재). **② 로컬 체크아웃도 159커밋 뒤처져 있었다** — 그 상태로 `session-start` 를 부르면 **44차(2026-08-14) 기준선을 복원하면서 `status: ok, warnings: []`** 를 낸다. 도구는 낡은 입력을 낡았다고 말하지 않는다. 세션 시작의 첫 동작은 `git fetch` + behind 확인이어야 한다. **③ 채널 4종을 v1.9.4 `[in-sync]` 로 맞췄다**: claude-code 갱신 + codex·grok-build·antigravity **신규** (이 호스트에 사본 0 이었다). codex 는 Release ZIP 을 `~/.local/share/standard-ai-workflow/` 에 풀어 등록했다 — 이 채널의 marketplace 는 **버전 경로에 고정**되므로 다음 버전에는 remove→add 가 필요하고, 그 경로를 지우면 채널이 깨진다. pi-dev 는 `pi` 부재로 제외(소유자 판단). **④ 포크 병합은 렌더된 문서가 아니라 렌더러 함수로 쟀다**: 포크는 한국어고 kit 템플릿은 영어라 문서끼리 diff 하면 65줄이 전부 다르게 보인다. `render_claude_code_agents` 를 `v1.3.0`/`HEAD` 에서 뽑아 대조하니 **델타는 진입 명령 목록의 파생화 하나뿐**이고 산출 내용은 동일 — **채택 0**, 기각 3 은 main-015 판단의 재확인(언어 전환 / 실행 기본값 TODO 되돌림 / 버전 마커). 쓴 것은 두 줄이다. **⑤ 게이트 1차 red 는 78차와 같은 모양이었다**: `--wbs` 를 붙여 task 를 만들면 로드맵 SSOT 가 바뀌는데 `roadmap_state.json` 이 안 따라온다(`check_roadmap_state_generated` + `check_state_json_generated` 동시 red). `wk refresh-state` 로 해소. 78차 ⑤ 도 같은 자리였다 — **이틀에 두 번이면 다음은 도구가 잡을 자리다.** **⑥ 검증**: 커밋 전 `--changed` rc=0 · push 게이트 전량 2축 **284/284 ×2 green** · push 후 CI 4종(smoke 5m55s · mcp-sdk-matrix · mypy-strict · os-matrix) **전부 success**. **⑦ 잔여**: 이 세션 프로세스(pid 6722)가 설치보다 먼저 떠서 `runtime_load` 가 낡은 호스트 1 로 센다 — `claude` CLI 재시작이 필요하다(`/clear` 로는 부족).
- 직전 기준선: **78차 세션 (2026-09-17~18, macOS 호스트) — 소유자 지시로 **WBS-7.1 무기한 연기**(main-017 → blocked)를 처리하고, 그 과정에서 `backlog-update` 의 함정 하나를 additive 로 닫았다 (task 1건 close: 2026-09-18-main-001). **① 연기의 대상은 leaf 가 아니라 task 다**: M-007 은 *상설* 마일스톤이라 done 을 목표로 하지 않고 WBS-7.1 은 반복 범주다 — 연기할 수 있는 실체는 그 leaf 에 걸린 열린 task 뿐이었다. main-017 의 완료 기준 1(수리+판정)은 77차에 끝났고 남은 것은 기준 2(Windows 실측)뿐인데 호스트 확보 시점이 없어 `blocked` 로 park 했다. **done 으로 닫지 않았다** — 검증 없는 done 은 기록을 거짓으로 만든다. leaf 에는 main-009(planned)가 아직 붙어 있어 비지 않는다. **② 오진 2건을 스스로 잡았다 — 이 세션의 실질**. 첫째, '`backlog-update --apply` 가 roadmap_state.json 을 자기 기록 이전 상태로 재생성한다(오늘 날짜 + 낡은 내용)' 고 보고했다가 **철회**했다: mtime 실측으로 `--apply` 는 그 파일을 쓰지 않는다. 소거법을 썼는데 **후보 목록 자체가 틀렸다** — 낡은 내용은 세션 이전부터 있던 더티 상태였다. 참인 것은 하나뿐이다: `generate_roadmap_state()` 가 이름과 달리 **디스크에 쓴다**(읽기인 줄 알고 부른 호출이 파일을 고쳤다). 둘째, `--progress-note` 미지정 시 Progress 가 `task_brief` 로 덮이는 것을 '보호되지 않은 스칼라'로 진단하고 수리까지 했는데, `check_backlog_update_layout.test_update_preserves_unspecified_fields` 가 **그 동작을 명시적으로 고정**하고 있었다('진행 한 줄' assertion). update 에서 `--task-brief` 는 `작업 내용` 이 아니라 `진행 현황` 으로 해석되는 것이 설계다 — 수리가 아니라 **계약 변경**임이 드러나 원복했다(9/9 복귀). **수리 전에 그 동작을 고정하는 검사가 있는지 먼저 본다.** **③ 소유자가 C안을 택했다 (계약 변경 B 대신 additive)**: update 에서 `--task-brief` 를 **선택 인자로**. 기존 호출은 전부 brief 를 넘기므로 동작 불변이고, 생략이 가능해지면서 '의미 없는 문장을 억지로 넘겨 이전 세션의 진행 기록을 현재 타임스탬프와 함께 덮는' 함정 자체가 사라진다(78차가 실제로 77차 Progress 를 그렇게 잃었다 — 새 스탬프 때문에 소실이 드러나지도 않았다). 구현 6곳: argparse required 해제 + help 에 **모드별 이중 의미** 명시 / 최상단 guard 를 **부재 vs 공백**으로 분리(공백은 여전히 거부) / 모드 확정 후 create 전용 필수 guard 신설(`auto`→create 포함) / progress 합성·병합·빈 `작업 내용` 채우기를 전부 brief 유무에 건다. **④ 판정**: case 10 `test_update_task_brief_is_optional` 신설(생략 update 의 진행·작업내용·상태 / create 거부 / 공백 거부). 거부 경로는 `assert rc==0` 을 통과할 수 없어 rc 비검사 헬퍼 `_run_raw` 를 더했다. 되주입 3종(무조건 덮기 / create guard 무력화 / 부재도 거부) 전부 의도한 case 에서만 red. **⑤ 검증**: `--changed` rc=0 · 좁은 선언 0 · `check_backlog_update_layout` 10/10 · `check_self_application` 8/8. 게이트 1차 red 3건은 전부 메모리 산출물이었다(state/roadmap 미재생성 · handoff §5 후보 소절이 blocked 된 main-017 만 인용) — 코드 결함 0. **덤으로 `check_handoff_next_steps` 의 취약점 하나를 봤다** — 후보 소절을 heading **리터럴의 첫 등장**으로 자르는데, 그 리터럴을 산문에서 백틱으로 인용만 해도 §1부터 파싱이 시작된다(이 문장을 쓰다가 실제로 밟았다). 우회는 쉽고(인용을 안 쓰면 된다) 실해는 게이트 red 뿐이라 task 로 열지 않았다 — 다시 밟으면 그때 연다. **⑥ 별건 — design 단계 검토 (착수 ❌, 후보만)**: Michael Lynch 의 *How to Write an Effective Software Design Document* 를 읽고 우리 `design` 단계를 실측했다. 스펙은 `설계 문서 / ADR` 을 병기하는데 **앞쪽 물건의 형식이 어디에도 없고**(템플릿은 ADR 형식뿐), 산출물 판정은 `state/roadmap.py:467` 의 **경로 존재 여부뿐**이라 `docs/architecture/README.md` 한 장으로 통과한다. 가져올 값이 있는 것 3: **Open Issues/Resolved Issues 자리**(ADR 은 결정을 *닫는* 형식이라 안 닫힌 것을 담을 자리가 없어 전부 handoff 산문으로 흘러간다 — 실제 통증) · '언제 쓰는가' 6문항 + 비용 휴리스틱(씨앗이 신규 프로젝트 전부에 design 마일스톤을 무조건 심는다) · 마일스톤 단위 non-goals. 섹션 20종 목록을 그대로 들여오는 것은 **기각** — `work_item_plan_template.md` §4 의 '맞지 않는 항목은 삭제' 패턴이 이미 더 낫게 푼다. 첫 후보(Open Issues)는 M-007 의 4범주 어디에도 안 들어가 **새 기능 축 M-013 이 필요**하다.**
- 그 이전 기준선: **77차 세션 (2026-09-07, macOS 호스트) — session-start 가 매번 내던 `health_score 0 / tier poor` + `scope creep 의심` 10건을 '오탐 조사' 후보로 열었더니 **오탐이 아니라 지표 자체의 결함 3건**이었다. task 2건 (2026-09-07-main-009 기록 / main-010 수리).** **① 점수가 일한 것을 벌하고 있었다**: `100 - uncovered*15 - scope_creep*10 + min(surprising*5, 25)` 는 벌점이 항목 수에 비례해 무한히 커지는데 보너스는 25 에서 막혀, goal 매칭 0 을 고정하고 완료 항목만 늘리면 0건 40(fair) → 3건 25 → 10건 **-35(0 으로 clamp, poor)** 였다. 표준이 recently-done 을 10건으로 상한하므로 **활발한 저장소는 영구히 바닥**이고, 보고되던 0 은 '나쁘다' 가 아니라 **clamp 자국**이었다. 두 성분 모두 비율로 바꿨다(coverage 70*covered/goals + classification 30*(1-미분류/전체)) — 규모 1~30배에서 점수 불변, 분류된 일을 추가해도 절대 안 내려감, clamp 에 닿는 입력 0. **② 매칭은 구조적으로 성립하지 않는다**: Goals 는 지향 문장이고 deliverable 은 결함 수리 제목이라 어휘가 겹칠 이유가 없다 — goal 4개 전부 공집합. **한국어 조사 가설을 세워 조사를 제거하고 재측정했지만 여전히 공집합**이었고, 부분문자열까지 완화해도 회수되는 것은 `ai` 와 `처럼` 둘뿐이다. **토크나이저를 고쳐도 안 열리는 자리다** — 임계값만 옮긴다. 그래서 지표를 정교화하는 대신 **주장을 좁혔다**: 이것이 재는 것은 어휘 겹침이지 건강도가 아니고, 낮은 값은 '어휘가 겹치지 않는다' 로 읽으며, 어떤 skill·harness 도 이것을 소비하지 않으므로(참조 0건, state.json 에도 미저장) 자동 판정의 근거로 쓰지 않는다 — module 과 두 schema docstring 에 정본으로 적었다. **③ 정반대 술어가 같은 경고 접두사를 썼다**: `purpose_context` 는 §3 제외 영역에 **걸리면** scope creep 이라 하고 `purpose_graph` 는 **안 걸리면** 그렇다 했는데, 둘 다 `"scope creep 의심:"` 으로 시작하면서 `scope_creep_warnings` 라는 **같은 이름의 두 필드**(top-level / `graph_insights.`)로 나갔다 — 읽는 쪽이 어느 규칙이 울렸는지 구분할 수 없었다. `미분류 산출물:` 정본 상수로 갈랐다. **필드 이름은 건드리지 않았다** — 공개 schema 라 G3 SemVer 보증상 개명은 deprecation 사이클이 필요하고, 그 사실을 schema docstring 에 남겼다(후속 후보). **④ 좋은 점수를 내는 유일한 fixture 가 항등식을 쟀다**: goal 문자열을 deliverable 에 **그대로 복사**해 두어 coverage 100% 가 나왔다. 게다가 낡은 `vX.Y.Z (hash):` 형식이라, 표준이 `TASK-` 로 바꾼 뒤인 지금 살아 있는 10건은 전부 `version='unknown'` 으로 떨어지고 모든 항목이 공유하는 `task`/`2026`/`09`/`main`/`008` 이 키워드에 섞여 있었다 — **결함이 어려웠던 게 아니라 재는 자리가 없었다**(76차 main-002 와 같은 모양). fixture 13자리를 현재 형식 + 복사 아닌 문장으로 교체하고, 파서는 정본 `TASK_ID_PATTERN` 에서 **파생**해 신설(복제하면 갈라진다, legacy 병행 유지). **⑤ 판정으로 닫았다**: `check_graph_insights_health_monotonic.py` 신설(4 case — 단조성 / 접두사 분리 / fixture 가 goal 복사 아님 / TASK- 인식과 ID 누출 0). 되주입 4종 전부 의도한 case 에서 red. **⑥ 별건 — 재생성 전에 원인부터 갔다 (자기 교정)**: 게이트가 `check_state_json_generated` 를 'state.json 이 갈라졌다 → `wk refresh-state` 로 재생성하라' 로 red 냈는데, 체크인본과 재생성본을 평탄화 대조하니 **차이 나는 키 0개**였다. payload 는 `drift=false`/`drifted_keys=[]`/**`roadmap_drift=true`** — 도구는 두 산출물 중 어느 쪽이 갈라져도 rc=1 인데 case_5 의 문구가 **무조건 state.json 을 지목**했다. 시키는 대로 했으면 멀쩡한 산출물을 다시 쓰며 진짜 원인을 지나쳤다. 문구가 payload 를 읽고 범인을 말하게 고쳤다. **⑦ runtime_load 잔여 칸은 기록만 남겼다 (main-009, 소유자 결정)**: 76차 handoff 가 '이 세션 자신이 낡은 호스트에 포함된다' 고 적었으나 **이 세션에는 해당하지 않았다** — pid 15598 / 13:02:22 시작으로 설치(12:55:44)보다 뒤라 doctor 가 세는 '최신 호스트 1개' 가 이 세션이다. 낡은 3개는 전부 **이 저장소 밖**(pid 10649 claude @~/repos/auto-trading · 9096 codex @~/repos/custom-harness · 18642 codex app-server 데몬)이라 죽이지 않았다. doctor 가 '실제 호출로만 재진다' 고 남긴 노출 미측정 칸은 이 세션의 `/session-start` 가 1.9.3 스킬 경로에서 정상 실행돼 claude-code 채널에 한해 닫혔다. **⑧ 검증**: `--changed` 257/257 PASS (FAIL 0) · meta-watch 좁은 선언 0 · mypy strict 204 files 0 · `check_self_application` 8/8 · 되주입 4종 red. smoke count 282→283 갱신은 `CODE_INDEX`·`INSTALLATION` 둘뿐 — **발행된 노트를 고치라는 요구 0건**(main-004 수리가 이번에도 물었다). **⑨ 남은 것**: 지표는 여전히 0 을 내지만 이제 **정직한 읽기**다(coverage 0 + 전량 미분류). 어휘 겹침이라는 근거 자체를 바꾸려면 ADR 이 필요해 범위 밖으로 남겼다. **⑩ 같은 세션에서 v1.9.4 를 발행하고 이 호스트 전 채널을 재적용했다 (소유자 지시, main-011).** 등급은 **도구 파생값(patch)을 소유자가 택했다** — §1.5 적용으로는 공개 API 추가 2종이 있어 73차 선례로 minor 로 읽을 여지가 있었으나, 두 추가는 수리를 가능하게 한 보조 장치이지 소비자용 기능이 아니라는 해석이고 '손으로 등급을 덮지 않는다' 는 규칙과도 맞는다. 태그 `v1.9.4` → `51ab7cb2`, draft 아님, asset 4종 실측. `required_ci` 필수 4종 success·`blocking=[]`. **발행 직전 수리가 안 먹은 것처럼 보였다** — `wk session-start` 가 옛 문구를 그대로 냈다. 원인은 전역 wk 가 발행본(수리 이전) 1.9.3 을 돌고 있어서였고 탐침이 스스로 말했다: '버전은 같은데 내용이 다르다 (.py 3개 어긋남)'. **버전 문자열이 같은 것은 내용이 같다는 뜻이 아니다** — 소스에서 고친 것을 설치본으로 확인하면 안 된다. 그래서 발행 검증은 **격리 venv**(PYTHONPATH 없음, 모듈 경로가 site-packages 임을 assert)로 했다: 1.9.4 · 새 접두사 · total_items · 단조성 [50,50,50,50]. 준비 게이트 12건은 전부 버전 bump 파생(v1.9.3 사이클과 같은 수·모양) — self-recover 가 README 4리터럴을 manual_required=0 으로, 생성기 3종은 **재생성 전에 대조**해 차이가 버전 문자열뿐(1·8·1건)임을 확인하고 돌렸다. `docs/RELEASE.md:175` 은 **역사 인용이라 일부러 남겼다** — 일괄 치환은 과거 기록을 거짓으로 만든다. `doc-headers-update` 는 껐다(안 건드린 77개를 오늘로 찍는데 전량 green 이라 요구 없음). **smoke 왕복은 이번에도 0회** — 검사가 282→284 로 늘었는데 발행 노트를 고치라는 요구가 없었다(main-004 수리 2사이클 연속). **⑪ main-017 은 '수리할 것이 없다' 가 결론이었다.** 62차가 이미 다 고쳤고 emit 지점 전수가 정본을 지난다 — 없던 것은 판정이라 `check_mcp_emit_launcher_sweep`(3 case) 를 세웠다. 기존 검사의 docstring 이 스스로 'smoke 는 이 호스트의 산출물만 밟는다' 고 적어 둔 자리다. **검사가 조용히 통과할 뻔했다** — opencode 만 command 가 리스트라 문자열 전용 추출이 0건을 냈고 그 0건이 위반 0건과 구분되지 않았다. 커버리지(렌더러마다 최소 1건 + 모듈 렌더러 전수가 사정권 안)를 검사에 넣었다. 완료 기준 2(Windows 실측)는 이 호스트 불가라 **in_progress 유지**. **⑫ 명령이 성공했는데 버전이 틀렸다 (main-012).** 채널 재적용에서 문서의 `marketplace remove → add → plugin add` 를 따랐더니 앞 둘이 usage 오류로 죽었고 `codex plugin add` 가 **옛 marketplace 를 보고 1.9.3 을 다시 깔았다** (`Installed plugin root: …/1.9.3`). 맨 `marketplace …` 최상위 명령은 **세 CLI 어디에도 없다** — 전부 `plugin` 아래이고 동사도 갈린다(claude=update / codex=**upgrade** / grok=update). 같은 문서 282행은 이미 올바른 형태였으니 사본이 갈린 것이다. **claude 는 rc 로 못 가른다**: 맨 형태가 rc **0** 인데 명령 실행이 아니라 프롬프트로 먹혀 모델이 산문으로 답한 것이다 — rc 표만 믿었으면 '맨 형태도 된다' 고 적을 뻔했다. **측정 장치 자체도 한 번 틀렸다** — 여러 단어 문자열을 `$c` 로 실행해 통째로 명령명이 됐고 rc 가 전부 무의미했다. 값이 예상보다 깔끔하면 도구가 아니라 측정 장치를 먼저 의심한다. §7.0.2 표·각주 4곳 교정 + 각주 7 신설. **이 자리는 정적 판정으로 못 닫는다**(CLI 인자 의미론). **⑬ 남은 것**: `runtime_load` 낡은 호스트에 **이 세션이 포함된다**(재시작 필요) · main-017 Windows 실측(호스트 불가) · `scope_creep_warnings` 개명(deprecation 사이클) · cross-host federation. 후반 상세는 [발행 세션 기록](./sessions/release_v1_9_4_and_command_form_drift_2026-09-07.md). 76차 상세는 아래 직전 기준선.**
- 그 이전 기준선: **76차 세션 (2026-09-07, macOS 호스트) — '체크인된 예제 state.json 이 생성기와 갈라졌는데 아무 검사도 안 본다'(74차가 별건으로 남긴 후보) 를 열었더니 **드리프트는 산출물의 낡음이 아니라 살아 있는 생성기 결함 두 개가 찍힌 자국**이었다. task 4건 close (2026-09-07-main-001·002·003·004).** **① 단순 재생성은 결함을 샘플에 굳혔을 것이다** — 수리 전에 재생성했다면 handoff 유래 필드가 통째로 빈 채로 커밋됐다. 그래서 원인부터 갔다. **② main-001 (handoff 경로에 legacy fallback 부재)**: 디렉터리(backlog/tasks/sessions)는 전부 `_branch_scoped_dir` 를 지나 'branch-scoped 없으면 legacy' 로 떨어지는데 `session_handoff.md` **만** helper 가 없어 소비자마다 인라인 조립했고 그 조립에는 fallback 이 없었다. 관례도 둘로 갈려 `ingest.py` 는 브랜치를 아예 빼고 봤다 — 같은 저장소에 대해 두 소비자가 **다른 파일**을 가리켰다. 실측: 예제에 `session_handoff.md` 가 **있는데도** 생성기가 못 찾아 `current_baseline`/`current_axis`/`recent_done_items` 가 전부 null·[] 로 떨어졌다. **경고가 없다** — 없으면 그냥 비고 state.json 은 정상으로 보인다. 수리: 정본 `workflow_handoff_path()` 신설(규칙을 복제하지 않고 기존 `_branch_scoped_dir` 를 그대로 탄다) + 파일명 리터럴을 `HANDOFF_FILENAME` 하나로 + 읽는 쪽 8곳 경유. workspace+branch 만 아는 세 caller 는 **이미 있던** 정본 `path_in_active()` 로 보냈다(새 함수를 만들지 않았다). 쓰는 쪽은 branch-scoped 유지 — '신규 생성은 항상 branch-scoped' 규약이 그대로다. **③ main-002 (거짓말하는 cast)**: `builder.py` 의 `cast(list[str], handoff.get('constraints'))` 는 실제 `str|None` 을 목록이라 **선언만** 했다. `cast` 는 아무것도 변환하지 않는다 — 문자열을 iterate 해 `environment_constraints` 가 **한 글자씩** 쪼개졌다(28개). 같은 값을 `session_start.py` 는 `[handoff, profile]` 로 감싸 **맞게** 냈다 — 같은 입력에 두 소비자가 다른 답을 냈고, `cast` 가 mypy strict 를 통과시켜 타입 축은 이것을 볼 수 없었다. **이 저장소에서 안 보인 이유가 핵심이다**: main 의 handoff 에는 `주요 제약` 줄이 없어 값이 늘 `[]` 였고, 그 줄을 가진 유일한 코퍼스가 `examples/` 였는데 그 산출물을 보는 검사가 없었다. **결함이 어려웠던 게 아니라 재는 자리가 없었다.** 수리: `normalize_constraint_values()` 정본 신설 + 두 소비자 통합 + `is_meaningful_text` 도 같은 파일로 이관(술어를 복제하면 갈라진다). **④ main-003 (판정 공백이 그 둘을 살려 뒀다)**: 기존 두 검사는 같은 입력으로 **tmpdir 에 새로 생성**해 느슨한 속성만 봤고 **체크인본을 읽지 않았다**. `check_example_state_artifact.py` 신설(5 cases) + 되주입 4종 전부 의도한 case 에서 red. **⑤ 2축 게이트가 내 결함을 잡았다 (자기 교정)**: 재생성한 산출물의 `sessions_dir` 이 `main/sessions` 가 됐는데, 예제에 `sessions/` 가 없어 branch-scoped 로 떨어졌고 **그 branch 는 예제의 것이 아니라 저장소를 체크아웃한 브랜치**였다 — `slash` 축에서 `feature/ci-slash-probe/sessions`. **어떤 값으로 커밋해도 다른 축에서 red** 인 구조이고 `native` 만 재면 차이가 0이다(2026-08-10 의 15연속 CI red 와 같은 모양). 예제에 `sessions/` 를 실재시켜 legacy 로 떨어뜨렸다 — `sessions_dir` 은 **원래 체크인 값 `sessions` 로 돌아왔다. 원래 값이 맞았고 내 재생성이 누출을 넣은 것**이다. 재발 방지로 case 5(산출물에 저장소 브랜치 이름 금지) 신설. **⑥ main-004 (75차 수리의 사본이 남아 왕복을 되살렸다)**: 검사 파일 +1(280→281)이 게이트를 red 로 만들었는데, green 으로 만드는 유일한 길이 **발행된 `Beta-v1.9.2.md` 를 고치는 것**이었다 — 75차가 없앤 바로 그 왕복이다. 원인: 75차는 `check_smoke_trend_cross` case 2 만 '자기 시점' 으로 고쳤고, **같은 규칙의 사본이 `verify_release_note_smoke_count` 에 남아** 태그를 안 보고 늘 현재 갯수와 쟀다(docstring 도 '살아있는 지표' 라는 75차 이전 서술 그대로). 그래서 case 2 는 PASS 인데 게이트만 red. 수리: 규칙을 kit 정본 `expected_smoke_count_for_note()` 하나로 모으고 게이트와 두 검사가 그것을 읽게 했다. 테스트 파일의 사본 helper 2개는 삭제 — 규칙이 테스트에 살면 게이트와 갈라진다. **`Beta-v1.9.2.md` 는 끝까지 한 바이트도 고치지 않았다.** **⑦ 문서 스탬프 도구가 과했다 (자기 교정)**: `doc-headers-update --apply` 가 내가 건드리지 않은 문서 101개까지 오늘 날짜로 바꿨다 — 사실이 아닌 기록이라 스탬프만 바뀐 파일을 전부 되돌리고 실제로 고친 3개(CODE_INDEX/INSTALLATION/RELEASE)만 남겼다. 발행 준비용 sweep 을 사이클 중에 부른 것이 잘못이다. **⑧ 검증**: 전량 2축 **281/281 ×2 PASS** (native / slash, FAIL 0, 좁은 선언 0) · mypy strict 0 (204 files) · `check_self_application` 8/8 · 되주입 6종 red 실증. mcp SDK 코드 무변경이라 SDK 매트릭스는 해당 없음. **⑨ `INSTALLATION_AND_USAGE §7.0.2` grok 복구 열 오기도 같은 세션에서 닫았다 (소유자 지시, `main-005`)**: 표 왼쪽 열이 설치 경로의 `<id>` 를 `plugin-<hash>` 로 못박아 둔 상태에서 복구 열은 `uninstall → install` 로만 적혀 있어 그 id 를 주는 것으로 읽혔다. 복구 열에 인자 형태를 명시하고 읽는 법 6번을 신설했다 — **함정은 `grok plugin list` 의 출력 형식 자체다**: `plugin-da9172c3: standard-ai-workflow` 처럼 **id 를 먼저** 찍어서, CLI 도움말의 '`plugin list` 에 보이는 이름' 이라는 안내가 오히려 id 를 가리키는 것처럼 읽힌다. **명령에 주는 값은 콜론 뒤다.** 파괴적 경로(실제 uninstall)는 돌리지 않고 같은 해석기의 읽기 전용 명령으로 쟀다 — `details plugin-da9172c3` → `not found` rc 1 / `details standard-ai-workflow` → rc 0. 저장소에 같은 지시의 사본은 없다. **이 자리는 판정으로 못 닫는다** — CLI 인자 의미론은 정적 검사가 고정할 수 없고, grok 이 해석을 바꾸면 표가 다시 낡는다. 실측 기록으로만 지켜지는 자리다. **⑩ task ID 호스트 간 충돌도 같은 세션에서 닫았다 (`main-006`)** — 75차가 남긴 마지막 실행 가능 후보다. **코드가 거짓 보증을 적고 있었다**: `next_task_id` docstring 이 브랜치 격리를 근거로 *동시 작업 호스트끼리도 안 겹친다* 고 보증했는데, 그것은 브랜치가 **다를 때** 성립하는 문장이다. 같은 브랜치(대개 main)의 두 호스트는 각자 로컬만 보고 같은 번호를 낸다 — 2026-09-04 에 실제로 둘 다 `main-002` 를 매겼고 **push 거절로만** 알았다. **보증을 적어 두면 아무도 다시 재지 않는다.** **수리**: ID 형식은 안 건드렸다(형식 변경은 `TASK_ID_PATTERN`·파서·과거 참조를 전부 흔든다). `common/git.py` 에 `remote_known_task_ids()` 정본 신설 — **원격 추적 ref 를 읽으므로 네트워크를 타지 않는다**(채번마다 fetch 하면 오프라인에서 멈추고 실패를 조용히 통과로 바꾸기 쉽다). 반환이 `RemoteTaskIds(ids, consulted, ref, reason)` 라 **못 봤을 때 빈 목록을 '원격에 없다' 로 읽을 수 없다**. 저장소 루트·pathspec 계산도 정본이 맡는다 — 호출자가 상대경로를 만들게 하면 절대경로를 넘기기 쉽고 그때 `ls-tree` 가 **조용히 빈 목록**을 낸다(=막으려던 실패 모드 그 자체). 채번기 둘이 이것을 받고, `backlog_update` 는 ref 를 못 읽었으면 '유일성을 로컬 안에서만 확인했다' 를 경고로 낸다. `MEMORY_GOVERNANCE.md` §212 의 같은 거짓 보증도 고쳤다(§124 는 '두 브랜치가' 로 한정돼 참이었다). **되주입 3종 전부 red**. 그 중 하나가 **내 docstring 의 역사 인용까지 물었다** — 75차 README changelog 와 같은 모양이라 인용을 풀어썼다. **남은 리스크(닫지 않았다)**: ref 는 마지막 fetch 시점에 멈춰 있어 **fetch 없이는 유일성이 로컬 안에서만 성립한다**. 도구는 그것을 경고로만 말한다 — 완전한 방지는 채번 시 fetch 나 ID 형식에 호스트 축을 넣는 것인데 둘 다 비용이 크다고 판단했다. **⑪ main-004 수리가 이 세션에서 첫 실전으로 물었다**: 검사 파일이 또 늘었는데(281→282) **발행된 노트를 고치라는 요구가 없었다**. 갱신 대상은 현재 갯수를 주장하는 `INSTALLATION`·`CODE_INDEX` 둘뿐이었다. **⑫ 소유자 보고('타 배포처에서 자꾸 모순')를 조사해 뿌리를 찾아 닫았다 (`main-007`)** — 오늘 닫은 것들(main-001 평평한 layout, main-006 호스트 간 ID)이 전부 이 뿌리의 파편이었다. **`Path(__file__).parents[3]` 이 배포 형태마다 다른 것을 가리킨다**: 소스 배치에서는 저장소 루트지만 설치본(uv tool·플러그인 캐시)에서는 `…/lib/python3.13` 이라 git 저장소가 아니다. 그래서 `get_current_branch()` 가 **조용히 `"main"`** 으로 떨어진다 — **오류가 아니라 그럴듯한 오답**이라 아무도 눈치채지 못한다. 실측(설치본 배치 + `feature/xyz` 소비자): `wk backlog-update` 가 ID 를 `TASK-…-main-001` 로 매기면서 파일은 `active/feature/xyz/` 에 썼다 — **ID slug 와 네임스페이스가 어긋난다**. 두 브랜치가 모두 `main-001` 을 매겨 병합 시 충돌했고, **slug 가 존재하는 이유가 소비자에서 통째로 무효**였다. **이 저장소에서는 구조적으로 안 보인다** — 이 저장소가 곧 모듈의 저장소라 틀린 해석기가 우연히 맞는 답을 내고, 282개 검사 전부 그 조건에서만 돈다. `check_branch_resolver_agreement` 가 이미 있었지만 해석기 **3개**만 봤고 채번은 대상 밖이었으며, `audit_root_anchors` 는 정적 스캔이라 *앵커가 설치본에서 증발한다*는 것을 볼 수 없다(`path_in_active` 는 심지어 **선언된 예외**였다). **수리**: `resolve_branch_for_workspace()` + `BranchResolution(slug, source, detail)` 신설 — 답과 함께 **출처**를 돌려준다(조용히 떨어지는 것이 뿌리이므로). 채번이 workspace 계열을 쓰고 출처가 workspace 가 아니면 경고한다. `refresh_wiki_memory` 도 branch 를 명시해 ledger 예외를 밟는 소비자 호출이 남지 않는다. **판정을 배포 형태까지 넓혔다**: 계약 4(채번 slug == 네임스페이스) · 계약 5(**설치본 배치**에서도 workspace 기준 유지 — 패키지를 저장소 아닌 곳으로 **실제 복사**한다; symlink 은 `resolve()` 가 되짚어 흉내가 안 된다). **⑬ 감사에 구멍을 낼 뻔했다 (자기 교정)**: R3 의 어휘가 `get_current_branch` **하나뿐**이라 내가 만든 새 fallback(`_resolve_module_branch`)을 못 봤다. 어휘를 넓히고 원장 잔재를 정리했다 — 규칙이 좁아지면 조용히 사라진다. **남은 리스크**: `get_current_branch()` 자체는 여전히 모듈 앵커를 본다(sandbox caller 를 위한 의도된 동작). 새 호출자가 workspace 를 알면서 그것을 쓰면 재발하며, audit R3 + resolver 검사만이 그것을 막는다. **⑭ 같은 세션에서 v1.9.3 을 발행하고 이 호스트 전 채널을 재적용했다 (소유자 지시, `main-008`)**: 등급 두 갈래가 같은 답(patch). 태그 `v1.9.3` → `6b3c070e`, draft 아님, asset 4종 실측. `required_ci` 필수 4종 success·`blocking=[]`. **`smoke_count_check` 가 이번 사이클에 280→282 로 두 번 늘었는데 발행된 노트를 고치라고 요구한 횟수는 0** — main-004 수리가 실전에서 물었다. **발행본 실측이 핵심이다**: wheel 을 fresh venv 에 깔아(`wk doctor` → 1.9.3) `feature/xyz` 소비자에서 돌리니 `TASK-…-feature-xyz-001` 이 `active/feature/xyz/` 에 착지했다 — 뿌리 수리가 **소비자에게 실제로 도달한다**. 준비 게이트 잔여 12건은 전부 버전 bump 파생이었다(plugin payload 5 · read_only fixture 3종 · 샘플 24 · 문서 리터럴 · README 4리터럴은 self-recover 가 `manual_required=0` 으로). `doc-headers-update` step 은 **껐다** — 안 건드린 문서 77개를 오늘로 찍는데 전량이 282/282 green 이라 어떤 검사도 요구하지 않는다. **채널**: 전역 `wk` 는 `uv tool upgrade` 가 의존성만 올리고 kit 은 1.9.2 그대로여서 **발행본 wheel 로 `--force` 재설치**해야 했다(버전 경로 고정 계열, 다음에도 같다) · claude-code(풀 id `plugin update`) · codex(`marketplace remove` → 1.9.3 ZIP 배치 → `add` → `plugin add <plugin>@<marketplace>`; 무인자 `add` 는 `--marketplace` 를 요구한다) · grok-build(`uninstall <플러그인 이름>` → `marketplace update` → `install --trust`). `content_drift` **3채널 전부 in-sync**(대조 12·10·19), 진입점 낡음 0 / 부재 0. antigravity 는 `agy` 부재로 여전히 막혀 있다. **오늘 고친 §7.0.2 가 실전에서 확인됐다** — `grok plugin uninstall` 에 플러그인 이름을 주어 성공했다(registry id 였으면 `not found`). **⑮ 남은 한 칸은 재시작**: `runtime_load` 가 claude-code 2개·codex 2개를 낡은 호스트로 잡고 **이 세션 자신이 거기 포함된다**. 전역 `wk` 는 프로세스마다 새로 떠서 이미 1.9.3 이다. **⑯ 남은 후보**: `TASK-2026-08-25-main-017`(Windows 실측 잔여, **이 호스트 불가**) · cross-host federation(plex 미기동·토큰 부재). 75차 상세는 아래 직전 기준선.**
- 그 이전 기준선은 [`baselines.md`](./baselines.md) 에 있다 (이관 92건, 최신이 위).

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
- TASK-2026-09-18-main-005 runtime_load 재측정 + '노출 한 칸' 첫 실측 — 그리고 캐시 사본은 읽히지 않는다
- TASK-2026-09-18-main-004 backlog-update --apply 가 roadmap_state.json 을 안 따라간다 — 파생물 갱신을 쓰는 층에 흡수
- TASK-2026-09-18-main-003 CLAUDE.md 포크 병합 — v1.3.0 이후 kit 델타 전수, 채택 0
- TASK-2026-09-18-main-002 이 호스트(plex) 채널 v1.9.4 재적용 — claude-code 가 v1.1.8-beta 로 5주 낡아 있었다
- TASK-2026-09-18-main-001 backlog-update 가 --progress-note 미지정 시 이전 Progress 를 task_brief 로 덮는다 — 새 타임스탬프가 붙어 갱신처럼 보인다
- TASK-2026-09-07-main-012 INSTALLATION 7.0.2 가 존재하지 않는 맨 marketplace 명령을 적고 있었다
- TASK-2026-09-07-main-011 v1.9.4 발행 + 이 호스트 소비자 채널 재적용
- TASK-2026-09-07-main-010 graph_insights health 가 완료한 일이 늘수록 내려간다 — 100% 발화하는 scope creep 경고와 항등식을 재는 fixture
- TASK-2026-09-07-main-008 v1.9.3 발행 + 이 호스트 소비자 채널 재적용
- TASK-2026-09-07-main-007 설치본에서 모듈 앵커가 증발해 브랜치 해석이 갈라진다 — 소비자 배포처의 모순 뿌리
그 이전 완료 항목은 [3차 세션 기록](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md)·[2차 세션 기록](./sessions/adr006_retrospective_and_calibration_2026-08-10.md)과 각 task 파일에 있다.

## 5. 다음 세션 시작 포인트

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
상주하며 좁은 선언을 red 로 잡는다 (분류 현황: **국소 198 / 전역 10 / 미분류 68**
— 66차 보급 완주 이후. 남은 68건은 표면이 source 트리 전체라 선언해도 선택 이득이
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

> **mypy 게이트 flake 는 66차에 닫혔다** (`TASK-2026-08-13-main-004`, 관찰 9차).
> 62차 소유자 결정의 close 기준 — '격리(`19e40ac9`) 후 완료 smoke run 33건에서
> mypy 게이트 실패 0' — 을 **33/33 · 실패 0** 으로 충족했다. 표본 중 failure 6건은
> `--log-failed` 전수 분류 결과 전부 deterministic 비-mypy(스탬프 드리프트 4 ·
> 생성물 정합 2). close 의 주 근거는 통계가 아니라 **기전**이다: 경합면(공유
> `.mypy_cache`)이 제거됐고 캐시 생성 0 이 실증돼 있다. **재발하면 새 task 로 연다** —
> 증거 그물(`--show-traceback` + 결론-우선 절단)은 이미 게이트 안에 있다.

- `TASK-2026-09-07-main-009` — `runtime_load` 낡은 호스트 3개 잔존. 셋 다
  **이 저장소 밖** 세션이라(auto-trading · custom-harness · codex app-server
  데몬) 재시작이 소유자 손에 있다. 이 저장소에서 할 수 있는 것은 재측정뿐이다
  — `wk doctor` 한 번으로 현재 값이 갱신된다.

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

### 64차가 남긴 규칙 (재발 방지)

- **게이트 확인과 push 를 한 명령에 묶지 않는다.** 결과 파일 cat 과 `git push`
  를 한 Bash 호출에 나열하면 exit code 분기가 사라진다 — 발행 완료 커밋이
  게이트 red(FAIL 8)인 채 push 됐다. 확인은 확인대로 끝내고, push 는 green
  을 **본 뒤** 별도로 실행한다.
- **러너가 도는 동안 저장소를 편집하지 않는다.** 두 번 밟았다: ① 진행 중
  게이트 위에 편집이 겹쳐 그 결과가 무효(중지 후 재실행), ② discovery 정숙
  구간 중 문서 편집이 `check_no_repo_write` 오탐 red. 락은 다른 러너만 막고
  에이전트의 편집은 못 막는다.
- **생성물은 생성기로 갱신한다.** 스키마 JSON 3종을 버전 문자열 치환으로
  고쳤더니 생성기 출력과 갈라져 즉시 red — 생성기 stdout 리다이렉트가 정답
  이었다. bump 파생물 목록에서 '치환 가능' 과 '재생성 필요' 를 구분할 것.
- **발행 post-step 은 검사 리터럴 스탬프와 같이 움직인다.** doc-headers-update
  가 인덱스 frontmatter 를 올리면 `EXPECTED_LAST_UPDATED` 리터럴 2곳(code/
  document index 검사)도 같은 커밋에서 올려야 한다 — 이번 red push 의 실체.
- **외부 SDK 의 부동 최신은 커밋과 무관하게 red 를 만든다.** mcp 2.1.1 이
  문서-only 커밋에서 mypy red 를 냈다. 정적 try/except import 는 mypy 가
  설치본 표면으로 **두 분기 모두** 검사한다 — ignore 주석은 strict 의
  warn_unused_ignores 로 반대쪽에서 역 red, importlib 동적 해석만 양쪽에 선다.
  새 버전은 매트릭스에 핀을 추가해 재현 자리를 만든다.
- **결함족은 사본을 하나씩 고치지 말고 전수 조사한다.** '자기 위치 오인' 이
  세션마다 하나씩 나온다 (suggest-memory-entries → archive-branch-memory →
  release-bump). 다음 수리 때 모듈 위치 파생 경로를 kit 전체에서 훑는다.

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
