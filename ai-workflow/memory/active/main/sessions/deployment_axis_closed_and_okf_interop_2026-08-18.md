# 세션 기록 — 48차: 배포 축 gap 4개 전부 닫힘 + OKF 상호운용 실측 (2026-08-18)

- 문서 목적: 48차 세션의 작업 축과 결정을 다음 세션이 이어받을 수 있게 남긴다.
- 범위: 결함 2건 수리(main-002/003), 배포 축 잔여 gap 해소(main-005/019), OKF 상호운용 실측(main-006)
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-18
- 관련 문서: [handoff](../session_handoff.md), [backlog](../backlog/2026-08-18.md), [컨셉 문서](../../../../../workflow-source/core/workflow_deployment_idempotency.md), [INSTALLATION §7.0.0~§7.0.2](../../../../../docs/INSTALLATION_AND_USAGE.md)

## 0. 한 줄 요약

**배포 일관성·멱등성 축의 gap 4개가 전부 닫혔다.** task 5건 close, push 5회,
전량 2축은 매번 green, 검사 262 → 263. 축을 끝낸 것보다 중요한 것은 **왜 지금까지
안 걸렸는가** 가 세 번 반복해서 같은 모양이었다는 사실이다 — 검사가 정작 재야 할
자리를 안 재고 있었다.

## 1. main-002 — 롤오프 포인터가 실행마다 쌓였다

`wk rollover-baselines` 가 이관처 포인터를 기존 것 갱신 없이 **매 실행 덧붙였다**.
47차에 6회 돌자 7줄 → 13줄. 건수도 누적이 아니라 이번 이관분이라, 파일엔 45건인데
handoff 는 '3건' 을 말하고 있었다.

수리는 **포인터를 먼저 전부 걷고 하나만 다시 넣는** 형태다. 그래서 치유가 이관과
독립이고, 상한 이하에서도 쌓인 상태를 접는다(`needs_pointer_fix`).

> **이 세션의 반복 주제 1회차.** `check_handoff_baseline_cap` 의 case 4 는 "포인터가
> **있는가**" 만 봤다. 그래서 쌓는 구현이 11 cases 를 전부 통과했다. 있는가는
> *사라지는* 회귀만 잡고, **쌓이는 회귀는 개수를 세야** 잡힌다.

## 2. main-003 — 패키지가 체크아웃 레이아웃에 기대고 있었다

소유자 지적에서 출발했다: *"실전에서 참조하는 스크립트 중에 workflow-source 경로를
참조하는 게 있는지 확인해. 실제로 배포되는 경로는 다를 수 있어."*

맞았다. 개발 호스트의 `wk` 는 **editable 설치**라 `parents[3]` 가 우연히 맞는다.
비-editable wheel 을 임시 venv 에 깔고 가짜 소비자 프로젝트에서 재보니 `REPO_ROOT` 가
`<venv>/lib/python3.x` 로 잡혔다. **SDK 매트릭스·브랜치 매트릭스와 같은 계열의
사각지대** — 전량 검사도 `wk` 도 전부 체크아웃에서 돈다.

실측 red 3건:

| 명령 | 증상 |
|---|---|
| `wk wiki-emit` | 없는 `workflow-source/tools/*.py` 실행 — **배포본이 아니라 이 저장소에서** 죽어 있었다 (v1.2.0 shim drop 잔재) |
| `wk rotate-workflow-logs` | 기본 handoff 가 `<venv>/lib/pythonX/ai-workflow/…`, 브랜치도 `main` 하드코딩 |
| `wk install-pre-push-hook` | git root 를 모듈 위치에서 묻고, hook 원본이 wheel 미포함 |

정공법 셋: ①**자기 모듈은 `-m` 으로** (`common/child_process.py` 한 곳에 규칙) ②**런타임
자산은 패키지 안으로** (`workflow_kit/assets/` + package-data) ③**workspace 는 cwd 에서**.

> **반복 주제 2회차.** `check_pre_push_hook` 의 cases 1~7 은 `_git_root` 를 통째로
> **monkeypatch** 해서 "어느 저장소를 고르는가" 를 한 번도 재지 않았다. mock 이
> 정작 깨진 것을 가리고 있었다. case 8 은 mock 없이 진짜 프로세스를 띄운다.

`check_deployed_layout` 4 cases 신설. 처음엔 "패키지 안의 모든 `workflow-source`
문자열" 로 짰더니 60건 넘게 걸렸다 — *타깃 workspace* 를 가리키는 정당한 경우까지
잡아서였다. **모듈 자신의 설치 위치에서 역산하는 경우**로 좁혔다. 안 그러면 검사가
계약이 아니라 **현상 유지를 박제**한다.

## 3. main-005 — 드리프트를 마커가 아니라 페이로드 해시로

47차가 관측만 해 둔 상태(버전은 같고 내용만 낡음)를 `wk doctor` 가 이제 본다.

**전제가 먼저 막혔다**: 정본 렌더러 `render_agent_plugin()` 이 설치본에서 통째로
죽어 있었다(`_project_table()` 이 체크아웃 경로만 봤다 — main-003 과 같은 결함
계열). 소비자 호스트에서 대조가 성립하려면 그것부터 살아야 해서 설치 metadata
fallback 을 넣었다.

`content_drift` 절이 지키는 것 넷:

1. **정본은 생성기와 같은 함수** — 기준을 따로 두면 기준 자체가 드리프트한다.
2. **기대치는 채널별 파생** (`include_prefixes`). codex 는 매니페스트·MCP·skills 만
   담아서, payload 20개를 그대로 기대하면 정상 설치가 *없음 10건* 으로 보고됐다.
3. **사본 거주지도 registry**. 사본 없는 채널(pi-dev = 경로 참조)·미실측(gemini-cli)은
   `not_applicable` 로 밝힌다.
4. **report-only 유지**.

## 4. main-006 — OKF 상호운용을 자기 선언이 아니라 실측으로

소유자가 조사를 지시한 [langchain-ai/openwiki](https://github.com/langchain-ai/openwiki)
가 **우리와 같은 OKF v0.1** 을 쓴다는 데서 출발했다. 저장소에 openwiki 언급은 0건 —
서로 모르는 채 같은 포맷에 도착했다.

- **SPEC 이 v0.2 로 움직였다.** ADR-006 은 2026-06-16 에 v0.1 을 고정했다.
  `timestamp`→`generated.at` · `# Citations`→`sources` · **`status` 가 정규 필드로 승격**.
- **`status` 만 실질 위험.** 우리 값은 `active` 42 · `accepted` 25 · `draft` 2 ·
  `proposed` 1 인데 v0.2 어휘는 `draft|stable|deprecated` 다. SPEC 의 관용 보장은
  *unknown key* 에만 걸리므로 정규 필드가 된 `status` 에는 안 걸린다.
- **다른 생산자와는 실제로 읽힌다** — 둘 다 `okf_version: "0.1"` 선언, `index.md` 예약,
  **둘 다 `log.md` 미발행**, `type/title/description/tags`, 상대 링크.
- **그런데 `type` 으로 라우팅은 원리적으로 불가능** — SPEC 이 registry 없는 자유
  문자열로 정의해서 우리 닫힌 enum 과 openwiki 의 자유 산문이 **둘 다 적합**하다.
  어느 쪽 결함도 아니라 포맷의 성질이다.

고친 것 2건: Citations 헤딩 h2→**h1**(v0.2 의 legacy fallback 도 h1 을 본다 — h2 면
양쪽에서 안 걸린다) · wiki score 대시보드가 **frontmatter 없이 생성**돼 export 가
71장 중 1장을 조용히 빠뜨리던 것(생성물이라 템플릿에서 emit).

> **반복 주제 3회차.** 18 cases 중 아무도 Citations 헤딩 레벨을 재지 않았고, wiki
> lint 는 위치·index 만 봐서 frontmatter 부재를 못 봤다. **export 가 곧 frontmatter
> 계약의 실사용 검증**이라 자기 적용 case 를 넣었다.

## 5. main-019 — 환경 pre-flight, 그리고 축의 종료

설계의 핵심은 `environment` 절과 **다른 물건**이라는 것이다. 그쪽은 *지금 이
인터프리터가 검사를 돌릴 만한가*, `preflight` 는 *어느 채널로 설치할 수 있는가*.

**축은 측정과 선언의 분리다.** 실행 파일은 `shutil.which` 로 재고, 네트워크
도달성·내려받은 아카이브는 `declared_unmeasured` 로 남긴다. `installable: true` 는
"실행 파일 전제 충족" 이지 "설치 성공" 이 아니다 — **모름을 통과로 세면 거짓
안심**이 된다.

모든 플러그인 채널의 공통 전제로 `wk`·`python3` 을 명시했다: 둘 중 하나가 없으면
**설치는 성공해도 기능이 없는 상태**가 된다.

이 호스트 실측: 6채널 중 **gemini-cli 만 막힘**(`gemini` 부재) — §7.0.2 가 손으로
적어 둔 '미실측' 과 같은 사실을 도구가 스스로 말한다.

## 6. 이 세션이 남긴 규칙

- **검사는 "있는가" 가 아니라 "몇 개인가 / 어느 것인가" 를 재야 할 때가 있다.**
  포인터는 개수, git root 는 어느 저장소, Citations 는 헤딩 레벨. 셋 다 존재만
  확인하는 단언이 결함을 통과시켰다.
- **mock 은 정작 깨진 자리를 가릴 수 있다.** `_git_root` 를 monkeypatch 한 7 cases 가
  그랬다. 한 case 라도 mock 없이 실제 해석을 재는 것을 둔다.
- **판정을 좁히지 않으면 검사가 현상 유지를 박제한다.** `check_deployed_layout`
  case 1 을 넓게 짰을 때 60건 넘게 걸렸고, 그대로 두면 예외 목록이 곧 검사가 된다.
- **진단 실행이 저장소를 바꿀 수 있다.** `wk wiki-emit` 을 진단으로 돌렸다가 L2 stub
  4개의 `last_touched` 가 2026-07-22 → 2026-06-14 로 **뒷걸음쳤다**. `rc=0` 이었다.
  HEAD 클린 워크트리와 대조해 원복했다.
- **editable 설치는 배포 결함을 영원히 숨긴다.** SDK 매트릭스·브랜치 매트릭스에
  이어 세 번째 사각지대다. 배포 표면을 건드리면 **비-editable wheel 로 한 번 재본다**.

## 7. 남은 것

- **[main-004]** wiki 3-step 하위 두 단계 — 1단계 `KeyError: 'memory'`(state.json 스키마
  드리프트), 2단계 `ValueError`(레이아웃 드리프트), **3단계는 rc=0 인 채 퇴행시킨다**.
- **OKF v0.2 이행 ADR** — 최소안은 `status` 어휘 매핑(`active`/`accepted`→`stable`,
  `proposed`→`draft`)하고 우리 어휘는 확장 키로 보존.
- **[main-009]** 라벨 영어 전환 — release 경계 대기, `TASK_FIELD_LABELS` 한 줄.
