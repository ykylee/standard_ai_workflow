# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-05
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- **현재 기준선(§2.59+§2.60, 2026-08-05)**: v1.0.0-beta + `origin/main` = `6ebbd8b` (커밋 4건). **커밋마다 트리거된 CI 3종 전부 green 실측** — smoke(2셀)·mypy-strict·mcp-sdk-matrix. push 트리거 red 0건이다.
- CI 자기 측정(요약 필드 말고 로그의 사실): smoke 네 셀(커밋 2 × 셀 2)이 각각 `해석된 workflow 브랜치: main` / `feature/ci-slash-probe` 로 갈렸고 전부 `All 233 check_*.py scripts passed (220 test cases)`. **실제 emit 된 `::error::` 0건** — `grep '::error::'` 은 2건을 냈지만 둘 다 워크플로우 자체의 **명령 에코**(브랜치 가드가 실패 시 출력할 문자열의 원문)이지 emit 이 아니다. 명령 에코(`\x1b[36;1m`)를 빼고 세야 진짜 건수가 나온다.
- **미트리거 3종은 결함이 아니다**: actionlint(`.github/workflows/**`) · mkdocs(`docs/**`, `mkdocs.yml`) · okf-validate(wiki / sample bundle / `url_validity`·`okf_export`·`frontmatter_urls`) — 이번 변경이 그 경로를 하나도 밟지 않았다. 그러니 **"트리거된 3종 green" 이지 "6종 green" 이 아니다**(§2.53 과 같은 구분).
- 직전 push 기준선: v1.0.0-beta + `origin/main` = `c58111d` (§2.58 적용본). **트리거된 CI 6종 전부 green 실측** — `okf-validate`(**6주 연속 red 종료**, 24초)·smoke(2셀)·mypy-strict·mcp-sdk-matrix·actionlint·mkdocs. **push 트리거 red 0건**이다. `okf-validate` 가 낸 URL 2건을 세 층에서 함께 고친 결과다 — 추출기(워크플로우 안의 grep → `workflow_kit.frontmatter_urls`) / 데이터(wiki 의 `external (…)` → bare URL, sample bundle 2 page) / 규약(`resource` 는 bare URI, `V-R10-resource-not-bare-uri`)
- CI 자기 측정(요약 필드 말고 로그의 사실): smoke 두 셀이 각각 `해석된 workflow 브랜치: main` / `feature/ci-slash-probe` 로 갈렸고 양쪽 다 `All 233 check_*.py scripts passed (220 test cases)`, `::error::` 0건. `okf-validate` 는 `Extracted 4 unique URLs` → `OK: 99 file(s) scanned, 4 unique URL(s), 0 convention issue(s)` → online 검증 exit 0. mkdocs 는 `docs/**` 를 밟아 **직전 두 사이클 만에 처음 트리거돼 통과**했다
- 현재 주 작업 축: "생성기를 검사하는 것과 산출물을 검사하는 것은 다른 일이다" — 렌더러 안의 리터럴은 4/4 PASS 였고 디스크에 쓰인 파일은 깨져 있었다
- 직전 축: "판정 이름이 원인과 다르다" — 검사가 내는 보고의 *이름* 은 검출기가 아는 만큼만 말한다
- 최근 핵심 기준 문서:
  - [global_workflow_standard.md](../../../core/global_workflow_standard.md)
  - [Beta-v1.0.0.md §2.38~§2.45](../../../../workflow-source/releases/Beta-v1.0.0.md)
  - [MEMORY_GOVERNANCE.md "두 축을 섞지 않는다"](../../../../workflow-source/MEMORY_GOVERNANCE.md)

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
-
## 3. 차단 작업

- 현재 `blocked` 작업:
-
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-07-31-main-007 모든 panel 의 기준이 자기 근거를 안 내고 있었다
- TASK-2026-07-31-main-008 네 번을 손으로 찾았다 — 기준 전수 조사를 저장소에 남긴다
- TASK-2026-08-01-main-001 조사가 어디까지 보는지를 선언하고 있었다 — 포함 목록을 없앤다
- TASK-2026-08-03-main-001 생성물인지를 이름으로 가르고 있었다 — 정본은 .gitignore 다
- TASK-2026-08-03-main-002 슬래시 브랜치에서 깨지던 것들 — 셋이었고 원인이 서로 달랐다
- TASK-2026-08-03-main-003 슬래시 브랜치를 밟는 실행이 우연이었다 — smoke 를 2셀로
- TASK-2026-08-03-main-004 오래 red 인 스케줄 workflow 2건 — 둘 다 원인이 딴 데 있었다
- TASK-2026-08-04-main-001 검사가 처음 돌자 나온 URL 2건 — 죽은 링크가 아니라 태어난 적 없는 링크
- TASK-2026-08-05-main-001 자기 harness 를 부분만 적용하고 있었다 + 버전 마커가 frontmatter 를 깨고 있었다
- TASK-2026-08-05-main-002 설치 문서가 존재하지 않는 배송을 선언하고 있었다 — Claude Code MCP

## 5. 다음 세션 시작 포인트

**CI 실측은 끝났다 — 커밋 2건 각각 트리거된 3종 green, red 0건**(§1 에 로그 근거).
이 저장소에 오래 red 인 workflow 도 없다.

**결정이 하나 남아 있다.** `stamp_marker` 결함은 *이미 배포된* 소비자
프로젝트의 opencode / grok-build skill 파일에도 있다. 마커 버전이 같으면
`decide_action` 이 `IGNORED` 를 내므로 **재부트스트랩해도 안 고쳐진다** — kit 버전이
올라가야 갱신된다. 이번 커밋에서 버전을 올리지 않았으니, 릴리스에서 이 건을 어떻게
다룰지(버전 상승 / 별도 마이그레이션 안내) 정해야 한다.

**MCP 는 붙였다(§2.60)** — `.mcp.json` 이 생겼고, 그 파일로 서버를 띄워 `tools/list`
13종 + `tools/call` 성공까지 실측했다. 다만 **이 세션은 그 파일을 로드하지 못한다**
(세션 시작 시점에 없었다). 다음 세션에서 MCP 도구 13종이 실제로 붙는지 확인할 것 —
skill 때와 같은 순서다.

--- 이전 세션(§2.58)의 시작 포인트 ---

**CI 실측은 끝났다 — 트리거 6종 전부 green, red 0건**(§1 에 로그 근거까지 적어 뒀다).
`okf-validate` 가 닫히면서 **이 저장소에 오래 red 인 workflow 가 남아 있지 않다**.
다음 세션은 새 축을 잡고 시작하면 된다.

후보(급하지 않은 순): (1) `okf_export` 의 Citations/`resource` 외에 **다른 파생 필드도
생산자가 규약을 아는지** — 이번엔 `resource` 하나만 봤다. (2) `check_wiki_drift` 는
`_parse_code_paths` 와 존재 검사가 **같은 파싱을 두 번** 구현하고 있다(이번에 URL 스킵도
양쪽에 넣었다) — 규약 단일 출처로 접을 자리. (3) `last_ingested_from` 자유 서술은 그대로
두기로 했지만, 그 값에서 뽑히는 URL 이 늘면 외부 의존도 같이 는다.

**남은 리스크(이번 건 고유).** 이제 검사에 들어가는 URL 4건이 전부 외부 호스트다
(`raw.githubusercontent.com` / `github.com` / `blog.scottlogic.com`). 그중 하나가 죽으면
`okf-validate` 는 **이번과 같은 이름으로 red** 가 되지만 그때는 *진짜* stale 이다 —
로그의 provenance 줄(`파일:줄 key url`)로 구분할 것. 그 줄을 남기려고 추출기가 출처를
같이 낸다.

---

**직전 세션 기록: 검사가 처음 돌자 나온 URL 2건 (TASK-2026-08-04-main-001, §2.58).**
판정 이름은 `V-R10-online-stale`("링크가 죽었다")였는데 **둘 다 존재한 적 없는 URL** 이었다.
결함이 세 층에 나뉘어 있었고 하나만 고치면 나머지가 되돌린다.

- **추출기** — 규약을 아는 자리가 워크플로우 안의 `grep -rEho "resource: …"` 한 줄이었다.
  frontmatter 가 아니라 **파일 전체**를 훑어 산문 예시를 URL 로 만들었고(백틱·괄호·마침표
  포함), 값을 **공백에서 끊어** ``a + b`` 의 두 번째 출처를 조용히 버렸다 — ponytail page 의
  blog URL 은 이번까지 **한 번도 검사된 적이 없다**. `workflow_kit.frontmatter_urls` 로
  옮겼다: frontmatter 블록만, 값 안의 URL 전부, **출처(파일:줄:key) 동반**, 스캔 0건이면 exit 2.
- **생산자** — `okf_export._derive_resource` 가 `last_ingested_from`(자유 서술)을 통째로
  in-repo 경로로 넘겨 `…/blob/main/external` 을 만들었다. `external` 은 경로가 아니라
  "외부 출처" 표식이었다. 가드 2종: **공백이 있으면 URI 가 아니다** / **저장소에 없는 경로는
  URL 이 되지 않는다**. 커밋된 5-page 번들에 그런 `resource` 가 **2건** 있었고, 그중 하나는
  추출기가 공백에서 끊어 준 덕에 우연히 통과 중이었다.
- **규약** — `resource` 는 bare URI 하나(OKF §4.1). `V-R10-resource-not-bare-uri` 로 고정하고
  워크플로우가 매 실행 `--check` 로 강제한다. `last_ingested_from` 은 자유 서술 그대로 둔다
  (56개가 그렇게 쓰이고 있고, 거기를 조이면 사실이 줄어든다).
- 검사 1종 신규(smoke 232 → **233**): `check_frontmatter_url_extraction`(12 case).
  마지막 case 가 **커밋된 번들의 `resource` = 지금 생산자의 출력**을 본다 — 데이터를 손으로
  고치고 생산자를 두면 다음 export 가 되돌리기 때문이다.
- 부수 발견 2건: `check_wiki_drift` 가 `.md` 로 끝나는 **URL** 을 in-repo 경로로 오판했고
  (이전 값은 괄호로 끝나 확장자 검사에 안 걸려 조용히 지나갔다), `check_okf_export` 의
  pinning fixture 가 `repo_root=Path("/fake")` 로 **제품이 만들지 않는 모양**을 검사하고 있었다.
- 되주입 5종 각각 다른 신호: 생산자 가드 제거 3건 red / 데이터 되돌림 2건 / frontmatter
  경계 제거 3건 / 정규식 되돌림 2건 / 소비자 grep 복귀 1건.

---

**오래 red 인 스케줄 workflow 2건 — 둘 다 원인이 딴 데 있었다 (TASK-2026-08-03-main-004, §2.57).**

- **`okf-validate`** 는 URL 문제가 아니라 **CLI 표면이 소비자를 두고 갈라진 것**이었다.
  `46b6b7a`(v0.7.41)가 무관한 커밋에서 `--cache` 등록 한 줄만 지웠고 `main()` 의
  `args.cache` 참조·docstring·워크플로우는 그대로였다. **`--online` CLI 경로가 7주간
  통째로 죽어 있었다** — 주면 `ambiguous option`, 안 주면 `AttributeError`.
- **같은 사고가 두 번**이다. `--max-bytes` 도 `1da10ef`(v0.7.37)가 등록만 지우고
  `args.max_bytes` 참조를 남겼다. 형제 `--max-entries` 는 살아 있어 비대칭이 안 보였다.
- **smoke 232건이 못 본 이유**를 검사 헤더가 이미 적고 있었다 — *"network 의존이라 skip"*.
  옳은 판단이지만 **네트워크 의존은 *호출* 을 건너뛸 이유이지 *인자 계약* 을 건너뛸
  이유가 아니다.** 파싱도 실행 분기도 오프라인이다.
- 검사 3종 추가(12 → **15 case**), 층이 다르다: 소비자 yml 에서 인자 추출 대조 /
  `--online` 파싱+`args.cache` 실재 / **CI 실제 호출을 `main()` 으로 끝까지**(네트워크만 스텁).
  **3번이 없었으면 `--max-bytes` 는 안 잡혔다** — 되주입 실측: 파싱 case 2건은 통과하고
  실행 case 만 red(16/17). **파싱이 통과한다고 실행이 되는 것이 아니다.**
- **`consumer-metrics-digest`** 는 게시 문제가 아니라 **저장소의 보이지 않는 상태**였다.
  `consumer-metrics-feed` 라벨이 없어 `gh issue create --label` 이 죽었다(5주 연속).
  라벨을 손으로 만들면 fork·새 클론에서 되돌아오므로, **의존은 쓰는 쪽이 보장**하도록
  사용 직전 `gh label create --force`(멱등)로 확보하고 실패 시 `issues:write` 를 지목하며 죽는다.
- 실측: `check_url_validity` **17/17**, 전량 smoke **232/232**, mypy strict 122 files 0 errors,
  실제 CI 호출이 네트워크 포함 **exit 0**.
- **CI 실측 완료**: `consumer-metrics-digest` 를 `workflow_dispatch` 로 돌려 **success** —
  5주 연속 red 가 닫혔다. `okf-validate` 는 **여전히 failure 지만 성격이 바뀌었다** —
  CLI 크래시가 아니라 도구가 실제로 돌아 검출 결과를 낸 exit 123 이다(위 §5 첫 항목).

---

이전 세션 기록: **슬래시 브랜치를 밟는 실행이 우연이었다 — smoke 를 2셀로 (TASK-2026-08-03-main-003, §2.56).**
§2.55 의 검증 근거는 **로컬에서 env 를 손으로 덮어 돌린 것**이었다. smoke 는
`branches: ["**"]` 로 돌지만 개발이 거의 main 에서 이뤄지므로, 슬래시 브랜치를 밟는
실행은 **아무도 보장하지 않는 우연**이다 — 같은 부류의 다음 결함은 또 오래 산다.

- smoke job 을 브랜치 컨텍스트 **2셀 matrix** 로. `native`(오버라이드 없음) /
  `slash`(`CODEX_WORKFLOW_BRANCH=feature/ci-slash-probe`).
- **"branch-sensitive 검사 목록" 을 선언하지 않은 것이 핵심 결정이다.** 그 목록은
  §2.53 에서 없앤 포함 목록과 **같은 모양**이고, 실제로 §2.55 에서 handoff 가 지목한
  2건 중 1건은 틀렸고 3번째는 목록에 없었다. 전량을 두 컨텍스트로 돌린다(병렬이라
  wall-clock 동일, 컴퓨트만 2배).
- 오버라이드 키는 `CODEX_WORKFLOW_BRANCH`(`BRANCH_ENV_KEYS` 최우선) — `GITHUB_REF_NAME`
  을 덮으면 러너의 실제 컨텍스트까지 바뀐다. **빈 값은 export 하지 않는다**(빈 문자열은
  다음 키로 흘러가 native 와 구분이 안 된다).
- **workflow 가 자기 오버라이드를 강제한다**: 해석된 브랜치를 step summary 에 먼저 찍고,
  선언과 다르면 `::error::` 로 죽는다. 안 먹으면 두 셀이 같은 것을 재면서 "2셀 green"
  이라고 보고한다 — §2.50 의 `GITHUB_REF_NAME` 무력화와 같은 자리다.
- 검사 9 → **10 case**: `case_10_ci_runs_a_slash_branch_context`. **`case_9` 는 코드가
  슬래시를 감당하는지, `case_10` 은 그 검증이 CI 에서 실제로 도는지** — 다른 층이다.
- artifact 이름을 셀별로 갈랐다(`upload-artifact@v4` 는 중복 이름 두 번째에서 실패해
  통과한 셀의 증거가 사라진다).
- 실측: 로컬 전량 **2컨텍스트 각각 232/232**, `check_branch_scoped_memory` 10/10 양쪽,
  되주입 2종 각각 다른 신호.
  **CI 4종 green 실측 완료**(`9efbd88`) — **두 셀이 실제로 갈렸다**: `native` 는
  `해석된 workflow 브랜치: main`, `slash` 는 `feature/ci-slash-probe`, 양쪽 다
  `All 232 …`. **CI 가 슬래시 브랜치 경로를 밟은 것은 이번이 처음이다.**
  `::error::` 0건 = 오버라이드 자기 검증 통과. 6분 34초/6분 29초 병렬(wall-clock 동일).

---

이전 세션 기록: **슬래시 브랜치에서 깨지던 것들 — 셋이었고 원인이 서로 달랐다 (TASK-2026-08-03-main-002, §2.55).**
handoff 는 "2건" 이라고 적고 있었는데 재현하니 **셋**이었고, 그중 하나는 **슬래시와 무관**했다.

| 검사 | 무슬래시 새 브랜치 | 슬래시 브랜치 | 원인 |
|---|---|---|---|
| `check_branch_scoped_memory` | PASS | FAIL | fixture 가 파일명에 raw 브랜치 |
| `check_workflow_linter` | PASS | FAIL | fixture 가 링크 깊이를 상수로 고정 |
| `check_self_application` | **FAIL** | FAIL | **슬래시 무관 — 오귀속** |

- **오귀속된 것이 더 큰 문제였다.** smoke 는 `branches: ["**"]` 로 돌기 때문에,
  브랜치를 하나 따는 순간 자기 변경과 무관하게 CI 가 red 였다.
- **세 번째(`check_workflow_linter`)는 전량 실행 전까지 아무도 몰랐다.** handoff 가
  이름으로 지목한 2건만 봤다면 놓쳤다 — 발견 계기는 **슬래시 브랜치 환경으로 전량
  smoke 를 한 번 돌린 것** 하나다.
- **제품은 이미 옳았다.** `branch_slug` 정규화도 아카이버의 `rglob` 중첩 처리도 있었다.
  깨진 건 전부 **검사 쪽**이었다 — fixture 가 제품이 만들지 않는 파일명을 만들고,
  판정이 경로 한 컴포넌트를 다중 컴포넌트 브랜치명과 비교하고, 링크 깊이를 상수로 박고,
  검사가 *저장소* 대신 *브랜치* 를 물었다.
- 슬래시 브랜치를 **끝까지 밟는** case 신규(`check_branch_scoped_memory` 8 → 9 case).
  이 경로를 밟는 case 가 없었던 것이 결함이 안 보인 이유다.
- `check_self_application` 은 브랜치 메모리가 없으면 기존 브랜치로 검증하되
  **바꿔치기한 사실을 출력**한다. 조용히 대체하면 거짓을 말하게 된다.
- 실측: main **232/232**, `feature/slash-probe` **232/232**(이 저장소 최초),
  개별 검사는 `release/v1.2/hotfix`(다중 슬래시)까지 통과. 되주입 4종 각각 다른 신호 —
  그중 하나가 **"main 통과 / 슬래시 FAIL"** 로 갈렸다는 것이 이 건의 요약이다.
  **트리거된 CI 3종 green 실측 완료**(`dda0825`) — 러너 자기 측정 `All 232 …`.
  다만 **CI 는 여전히 main 에서만 쟀다** — 슬래시 브랜치 커버리지는 로컬 재현이 근거다.

---

이전 세션 기록: **생성물인지를 이름으로 가르고 있었다 — 정본은 `.gitignore` 다 (TASK-2026-08-03-main-001, §2.54).**
§2.53 이 포함 목록을 없앴지만 *제외*는 여전히 이름이었다. **이름은 성질이 아니다** —
`build` 라는 이름의 *진짜 소스* 가 생기면 조용히 빠지고 그 안의 결함이 "미선언 0건" 이
된다. 게다가 그 목록은 애초에 **`.gitignore` 가 선언한 것의 약한 사본**이었다.

- **정본을 쓴다**: `git ls-files`(tracked) + `ls-files --others --exclude-standard`
  (untracked-but-not-ignored)의 합집합이 "생성물이 아닌 `.py`" 의 정의다.
  `--show-toplevel == scan_root` 일 때만 쓴다 — 하위 디렉터리나 저장소 안에 들어앉은
  temp 를 가리켰을 때 남의 목록을 자기 것으로 착각하지 않기 위해서다.
- **이관 시점 두 방식이 446건으로 완전 일치**(git 전용 0 / 이름 전용 0). 지금 바뀌는 것은
  없고 이름 충돌 위험만 사라진다 — 바꾸기 가장 좋은 순간이었다.
- **fallback 은 자기가 fallback 임을 밝힌다**: `source_selection` = `git` /
  `name-fallback`. `EXCLUDED_PARTS` 는 fallback 전용으로 격하.
- 검사 10 → **11 case**(신규 파일 없음, smoke 232 그대로):
  `case_11_generated_is_decided_by_git_not_by_name`.
- **되주입이 두 모드의 차이를 그대로 보여 줬다.** 추적되는 `build/real_source.py` 에
  `parents[6]` 를 심으면 — git 모드 미선언 **1건**(정확히 지목) / fallback 모드 미선언
  **0건**. 같은 코드, 같은 결함, 다른 판정. **틀린 쪽이 더 조용하다.**
- `case_10` 의 기대값도 이름 목록 → git 으로 옮겼다. 안 그러면 추적되는 `build/` 소스가
  생겼을 때 *검사 쪽이* 위양성을 낸다. 정본을 공유하되 git 호출은 검사에서 따로 한다.
- 실측: 전량 smoke **232/232**, `check_root_anchor_audit` 11/11, mypy strict 2파일 clean.
  **트리거된 CI 3종 green 실측 완료**(`99eb05a`) — 러너 자기 측정 `All 232 …`. `git` 을
  subprocess 로 새로 부르기 시작한 변경이라 로컬 통과만으로는 부족했는데, 러너에서도
  `source_selection=git` 으로 도는 것이 `case_11`(a)로 확인됐다(fallback 이었으면 red).

---

이전 세션 기록: **조사가 어디까지 보는지를 선언하고 있었다 — 포함 목록을 없앤다 (TASK-2026-08-01-main-001, §2.53).**
§2.52 가 남긴 한계를 닫았다. 조사 범위가 `SCAN_DIRS` 라는 *포함* 목록이었고, 그 구조에서는
**"있는데 선언 안 한 트리" 를 셀 방법이 자체적으로 없다** — 조사가 자기 사각지대를 볼 수
없는 형태였다.

- 실제로 **27 file 이 조용히 빠져 있었다**: `workflow-source/skills` 19(**이 세션에서
  상태 문서를 실제로 쓴 `run_backlog_update.py` 가 여기 있다**) / `ai-workflow/mcp_servers`
  6(적용본이 아니라 자기 anchor `parents[4]` 를 가진 별개 소스였다) / `examples` 2.
- **포함 목록을 없앴다.** 드리프트할 수 있는 선언을 검사로 감시하느니 선언을 지운다.
  이제 scan_root 아래 모든 `.py` 를 보고, *제외*만 `EXCLUDED_PARTS` 한 곳에 둔다.
  제외도 조용하면 안 되므로 `excluded_trees`(제외 이름별 잘라낸 트리 수)로 낸다.
  순회는 `os.walk` 가지치기 — `rglob` 은 `.venv` 8000+ file 을 훑고 나서 버렸다.
- 검사 9 → **10 case**(신규 파일 없음, smoke 는 232 그대로):
  `case_10_scan_covers_every_source_file`. 저장소의 모든 `.py` 를 **검사 쪽에서 독립적으로
  다시 세어** 도구의 `scanned_paths` 와 대조한다. 개수만 되읽으면 자기 자신과 비교하는
  것밖에 못 한다 — 그래서 도구가 *목록* 을 내보내도록 payload 에 `scanned_paths` 를 더했다.
- **바닥선은 이 결함을 절대 못 잡는다.** `skills`(19 file)를 빼는 되주입에서 446 → 427 인데
  `MIN_SCANNED_FILES = 200` 은 여유롭게 통과했다. 실제로 case_1 은 통과하고 case_10 만
  빠진 19건을 이름까지 지목하며 red. **바닥선은 "붕괴" 를, 전수 대조는 "누락" 을 본다.**
- 실측: 조사 419 → **446 file**, 모듈 유도 기준 298 → 322, R2 후보 21 / R3 후보 147.
  새로 들어온 27 file 에서 **미선언 결함 0건** — 결함을 찾은 게 아니라 *안 보던 곳을 안
  보고 있었다는 사실* 을 없앤 것이다. 전량 smoke **232/232**, mypy strict 신규 2파일 clean.
  **트리거된 CI 3종 green 실측 완료**(`710ccea`) — 러너 자기 측정 `All 232 …`.

---

이전 세션 기록: **네 번을 손으로 찾았다 — 전수 조사를 저장소에 남긴다 (TASK-2026-07-31-main-008, §2.52).**
§2.47(린터)·§2.49(doctor)·§2.50(branch)·§2.51(dashboard)은 **같은 결함 네 번**이었다.
§2.50 에서 한 번은 AST 로 전수 조사했지만 **그 스크립트를 저장소에 남기지 않아** §2.51 은
다시 손으로 찾았다.

- `tools/audit_root_anchors.py` — 네 규칙. `anchor_outside_workspace`(§2.49 모양) /
  `module_anchor_as_default`(§2.51 모양) / `branch_from_module_repo`(§2.50 모양) /
  `stale_ledger_entry`(원장 부패). **R1 만으로는 부족하다** — §2.51 은 editable install
  이라 *우연히* 저장소 안에 착지했다.
- **선언 원장(`ROOT_ANCHOR_LEDGER`)**. 걸린 것이 전부 결함은 아니라, 선언된 설계는 *이유와
  함께* 남기고 선언 안 된 것만 결함으로 본다. key 는 `(rule, path, symbol)` 이라 줄이
  밀려도 안 깨진다. 현재 2건 — `branch_for_workspace`(규칙 자체의 정본) /
  `path_in_active`(§2.50 이 handoff 에만 적어 두었던 결정이 이제 코드 옆에 있다).
- 검사 1종 신규(smoke 231 → **232**): `check_root_anchor_audit.py`(9).
- **되주입을 실제 소스에 했더니 검출기 구멍이 나왔다.** R2 가 "기본값이 `None` 인 인자" 만
  보고 있었는데 §2.51 의 `resolve_workspace_root(workspace_root: Path | str | None)` 은
  **기본값이 없고 型으로만 미지정을 받았다** — 안 잡혔다. nullable annotation 도 세도록
  고쳐 잡았다. fixture 는 내가 상상한 모양이고, 실제 소스는 실제로 있던 모양이다.
- **처음 쓴 버전은 조사 0건인데 "미선언 0건" 이라고 말했다.** 저장소 밖 cwd 에서 부르면
  대상이 하나도 없는데 exit 0 이었다 — `scan_ok` 로 닫았다.
- 규칙 무력화 방어: `r2_candidate_functions` / `r3_candidate_functions`(규칙이 *들여다본*
  함수 수)에 바닥선. 인자 이름 목록이 코드와 갈라지면 규칙은 깨지지 않고 조용히 아무것도
  안 보게 된다.
- 실측: 전량 smoke **232/232**, mypy strict 122 files 0 errors, `mkdocs build --strict`
  성공, 인벤토리 419 file / 모듈 유도 기준 298 / cwd 17 / 기타 상승 연쇄 3.
  **CI 4종 green 실측 완료**(`5c8a85f`) — 러너 자기 측정 `All 232 …`.

---

이전 세션 기록: **모든 panel 의 기준이 자기 근거를 안 내고 있었다 (TASK-2026-07-31-main-007, §2.51).**
§2.50 이 "선언된 fallback 이라 범위 밖" 으로 남긴 마지막 한 건을 닫았다.

- `dashboard_data._repo_root(None)` 이 `Path(__file__).resolve().parents[3]` 로
  떨어졌다. 이 저장소는 editable install 이라 그 값이 **우연히** 저장소 루트였다.
  설치본 배치로 복사해 재보니 **`<venv>/lib/python3.13`** — 실재하는 디렉터리인데
  workspace 가 아니다(`ai-workflow/` 없음). 그러면 8 panel 이 전부 빈 값을 내고,
  그 빈 값이 **그 경로의 측정 결과처럼** 보고된다.
- **이 모듈이 이미 답을 적어 두고 있었다.** `JUDGMENT_METRICS` 위 주석: *"판정 지표는
  값만 내지 않는다 — 무엇을 보고 그렇게 판정했는지 함께 낸다."* 그런데 **모든 panel 의
  기준인 workspace root 자신은** 근거를 안 냈다. 규칙을 세운 자리와 안 지켜진 자리가
  **같은 파일 안**에 있었다.
- `resolve_workspace_root(ws) -> (Path, source)` 로 (명시 인자 → **cwd**) 두 갈래만
  두고, snapshot 에 `workspace_root_source` 를 싣는다. `_repo_root` 는 그것을 부르는
  얇은 wrapper다.
- 검사 1종 신규(smoke 230 → **231**): `check_dashboard_workspace_provenance.py`(4).
- **되주입 3번이 처음엔 통과했다.** 검사를 저장소 루트에서 돌리면 cwd 와 `parents[3]`
  이 우연히 같아 둘을 갈라 놓아도 차이가 안 보인다 — §2.50 에서 배운 "자기 자신과
  비교하는 검사" 를 **바로 다음 검사에서 또 썼다.** 다른 cwd 에서 재도록 고쳐 잡았다.
- **전량 smoke 가 의존 하나를 곧바로 잡았다**: `check_quality_dashboard_v0_13_0` 이
  `collect_dashboard_snapshot()` 을 인자 없이 부르며 모듈 위치 추측에 기대고 있었다.
  단독 실행은 저장소 루트라 통과하고 smoke 는 다른 cwd 라 red(`guard_cases (0) !=
  expected_cases (6)`). 검사가 옳고 의존이 틀렸다 → `REPO_ROOT` 명시로 교정.
- 실측: 전량 smoke **231/231**, mypy strict **122 files 0 errors**, dashboard 관련
  기존 검사 11종 PASS, 되주입 3건 각각 다른 신호.
  **CI 4종 green 실측 완료**(`1b52b85`) — 러너 자기 측정 `All 231 …`.

---

이전 세션 기록: **세 번째를 찾으러 갔더니 다른 축에 있었다 (TASK-2026-07-31-main-006, §2.50).**
§2.47(린터)과 §2.49(doctor)가 같은 모양이라, "이 모양이 또 어디 있나" 를 손으로 세지
않고 **AST 로 전수 조사**했다(`workflow-source/**/*.py`, build 제외).

- **경로 축에서는 세 번째가 없었다.** `Path(__file__)` 유도 기준 **309건 중 저장소 밖
  착지 0건** — doctor 가 마지막이었다. 인자 `.parent` 연쇄 depth≥2 는 3건(전부 근거
  있음), `Path.cwd()` 9건(명시적 선택). 배포 패키지 안의 11건 중 `server/*` 4건 +
  `harness` 1건이 `<repo>/workflow-source/` 배치를 가정하지만, `pyproject.toml` 이
  "나머지는 저장소 디렉터리 레이아웃으로 소비한다" 고 적은 **선언된 설계**다.
- **대신 다른 축에서 나왔다 — 경로만 기준이 아니다. branch 도 경로를 고른다.**
  v1.0.1 이 "workspace 로 파라미터화된 함수는 그 workspace 의 git 을 본다" 를
  선언했는데, 적용된 곳은 `state_path_for_workspace` **하나뿐**이었다. 실측:

      repoB(feature/probe-branch) 의 profile 로
        state_path_for_workspace → …/active/feature/probe-branch/state.json
        workflow_branch_dir      → …/active/main        ← 모듈 저장소의 branch
        workflow_archived_...    → …/archived/main

  같은 workspace 에 대해 **state.json 과 handoff/backlog 가 다른 branch 디렉터리**를
  가리켰다. 이 저장소는 모듈 저장소 == workspace 라 안 드러나고, **kit 을 쓰는 소비자
  프로젝트에서만** 발현한다 — 정확히 이 kit 이 존재하는 이유인 그 상황이다.
- **기존 검사가 못 본 이유: 자기 자신과 비교했다.** fixture 를 `get_current_branch()` 로
  만들고 결과를 `get_current_branch()` 와 대조하니, 두 해석기가 갈라져도 통과한다.
  신규 검사는 **모듈 저장소와 다른 branch 의 workspace 를 실제로 만들어** 셋의 합의를 본다.
- 검사 1종 신규(smoke 229 → **230**): `check_branch_resolver_agreement.py`(4).
- 실측: 전량 smoke **230/230**, mypy strict **122 files 0 errors**, 경로 관련 기존 검사
  9종 PASS, 되주입 3건 각각 다른 신호.
- **CI 1차 red 를 냈고 그것이 이번 세션의 가장 큰 교훈이다.** 로컬 230/230 통과 후
  러너에서 `fixture 준비 실패: main`. GitHub Actions 는 `GITHUB_REF_NAME` 을 항상
  세팅하고 `BRANCH_ENV_KEYS` 는 **모든 workspace 에 우선**한다 — CI 에서는 어떤
  workspace 를 물어도 CI 의 branch 가 나와서 "두 해석기가 합의한다" 가 자동으로 참이
  된다. **검사가 깨진 게 아니라 무력화된 것이다**(assert 순서가 달랐으면 조용히
  통과했을 것). 합의 케이스는 env 를 비우고 측정하고, env 우선 규칙은
  `test_branch_env_override_wins` 로 따로 고정했다. 검증은 `GITHUB_REF_NAME=main` 으로
  **러너 환경을 재현**해서 했다.
- **검사를 추가하면 러너 환경에서도 그 검사가 유효한지 확인할 것.** 로컬 통과는 절반의
  증거다. **CI 3종 green 실측 완료**(`15ee104`) — 러너 자기 측정 `All 230 …`.

---

이전 세션 기록: **같은 결함이 형제 도구에 그대로 있었다 (TASK-2026-07-31-main-005, §2.49).**
§2.47 이 "doctor 는 아직 provenance 를 안 쓴다" 로 남긴 후속인데, 열어 보니
**provenance 만의 문제가 아니었다.**

- `DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent × 5` 는 이 저장소에서
  `/home/yklee/repos` — **저장소 루트의 두 단계 위**다(실측). 설치본에서는 아예 사용자
  프로젝트와 무관한 경로다. **모듈 위치로 workspace 를 추측한다는 전제 자체가 틀렸다.**
  그 값이 `load_config` 와 `_read_state_json` 양쪽으로 가서, 인자 없는 기본 호출은
  설정도 state.json 도 못 찾고 있었다. 이제 기본값은 **cwd** 다.
- **기존 doctor smoke 는 전부 `--project-root` 를 명시해서 돌고 있었다.** 그래서 기본값이
  깨져 있어도 아무 검사도 실패하지 않았다 — 사용자가 실제로 치는 것은 인자 없는 쪽인데.
  §2.47 에서 지운 "통과하면서 아무것도 보장하지 못하는 검사" 와 같은 자리다.
- `--config-path` 신설(린터와 같은 형태) + 출력 3종에 `config_provenance`.
  `--show-config` 는 기존 5 field 를 **top-level 그대로** 두고 옆에 붙였다(v0.7.7 계약).
  pretty footer 는 `Config source: default (section_missing) → 선언한 설정이 적용되지
  않았다` 를 **표의 숫자보다 먼저** 적는다.
- **고치자마자 동작이 바뀌었다.** `--config-path workflow-source` 로 돌리면 선언한
  `partial_rules = { resiliency = [RES-WF-01, RES-WF-02] }` 가 평가 결과에 **실제로
  반영된다**. v0.7.8 이 "display only → actual apply 격상" 이라고 적은 기능은 이
  저장소에서 한 번도 apply 된 적이 없었다.
- 검사 1종 신규(smoke 228 → **229**): `check_doctor_config_provenance.py`(6).
- 실측: 전량 smoke **229/229**, mypy strict **122 files 0 errors**, 되주입 4건 각각
  다른 신호. **CI 4종 green 실측 완료**(`607b84c`) — 러너 자기 측정 `All 229 …`.

---

이전 세션 기록: **검사를 켰더니 보고가 왔고, 두 건은 종류가 달랐다 (TASK-2026-07-31-main-004, §2.48).**
§2.47 이 남긴 후속 2건이다. 같은 "드리프트" 로 묶을 뻔했는데, 사실 확인을 해 보니
하나는 **문서를 고쳐야 했고** 하나는 **검사를 고쳐야 했다.**

- **`task-modes` 는 위양성이었다.** matrix 항목에는 실행 표면이 없는 명세
  (`kind: "spec"`, 근거는 `spec_path`)가 있는데, 그 규약을 아는 자리가
  `check_maturity_registry.py` **하나뿐**이었고 **kit 이 배포하는 린터는 몰랐다** —
  소비자 저장소에서 `--maturity` 를 돌리면 영영 이 위양성을 본다는 뜻이다. 어휘 정본
  `common/maturity.py` 를 만들고 둘이 같은 이름을 읽는다(리터럴 사본 3곳 제거).
  명세의 근거는 `test_path` 가 아니라 **`spec_path` 실재**로 확인한다 — 완화가 아니라
  근거의 교체다(`missing_spec_file`, high).
- **roadmap 은 진짜 드리프트였다.** `workflow_kit_roadmap.md` 와
  `phase_13_followup.md` 가 둘 다 **2026-07-21** 자로 "Phase 13 planned 진입 대기" 인데,
  v1.0.0 은 **2026-07-22** 발행이고(entry gate 6영역 전부 PASS, `-beta` suffix 는 릴리스
  노트 머리말이 *명명 관례*라고 명시) matrix 는 `in_progress` / `started: 2026-07-21` 다.
  **두 문서가 릴리스 하루 전에서 멈춰 있었다.** matrix 를 사실로 채택해 양쪽을 맞췄고,
  `-beta` 가 왜 성숙도 주장이 아닌지 근거를 roadmap 에 남겼다.
- **판정도 같이 고쳤다.** 예전 검사는 milestone `name` 문자열의 **포함 여부** 하나라,
  그 줄만 넣으면 roadmap 이 `planned` 라고 말해도 통과했다(§2.47 에서 지운 것과 같은
  종류). 이제 언급과 **모순 없음**을 나눠 본다 — `roadmap_milestone_still_planned`.
  **어느 쪽이 사실인지는 도구가 정하지 않는다.** key 매칭은 숫자 경계를 본다.
- 검사 1종 신규(smoke 227 → **228**): `check_maturity_drift_judgment.py`(10).
- 실측: 전량 smoke **228/228**, mypy strict **122 files 0 errors**, 실저장소
  `--maturity` issue 0 / warning 0, 되주입 5건 각각 다른 신호.
  **CI 4종 green 실측 완료**(`2e13931`) — 러너 자기 측정 `All 228 …`.
- **정본만 고치면 배포 사본이 남는다.** 중간 smoke 에서 `check_standard_single_source`
  가 red 였다 — `workflow_kit_roadmap.md` 는 `ai-workflow/core/` 에 배포 사본이 있고
  정본과 byte 일치를 요구한다. 검사가 옳았다. `core/*.md` 를 고치면 사본도 함께 옮길 것.

---

이전 세션 기록: **기준 경로가 한 칸 어긋나 있었고, 그 사실을 아무도 말해 주지 않았다
(TASK-2026-07-31-main-003, §2.47).** §2.46 이 "별건" 으로 남긴 항목이다.

- `run_workflow_linter.py` 의 `project_root = project_profile_path.parent.parent.parent`
  는 `<root>/docs/PROJECT_PROFILE.md` 에서 root 가 아니라 **root 의 한 단계 위**다.
  되주입하면 fixture 에서 `project_root=/tmp` 가 나온다. 그 값이 두 곳으로 갔다.
  - `load_config(project_root)` → 없는 pyproject 를 물어 **언제나 기본값**.
    `[tool.workflow-doctor]` 의 `excluded_paths` 는 v0.7.15 도입 이래 한 번도 적용된
    적이 없다.
  - `--maturity` 의 matrix/roadmap 경로 → 늘 `skipped`. 그런데 runner 가 `issues_found`
    만 반영해서 **실행되지 못한 검사가 `status: ok / total_issues: 0`** 으로 보고됐다
    (v0.11.17 backlog 에 "정합 검증 통과" 로 기록돼 있다 — 그 기록은 사실이 아니었다).
- **둘 다 조용했던 이유는 같다.** `load_config` 는 어떤 경우에도 실패하지 않는다(운영
  안정성). 그 대가로 "설정이 적용됨" 과 "조용히 기본값으로 떨어짐" 이 산출물에서
  구별되지 않았다. `load_config_with_provenance` 가 **물어본 경로 / 얻은 파일 / 출처 /
  기본값 이유**(`file_missing`·`section_missing`·`parse_error`)를 함께 돌려주고,
  린터 산출물의 `source_context` 에 남는다. `load_config` 는 그것을 부르는 얇은 wrapper다.
- **이 저장소는 `--config-path workflow-source` 가 필요하다.** `[tool.workflow-doctor]`
  정본이 `workflow-source/pyproject.toml` 인데 workspace root 는 저장소 루트다. 사본을
  하나 더 두지 않고 **호출을 명시**하는 쪽을 택했고 `docs/PROJECT_PROFILE.md` 의 린터
  명령줄을 그 형태로 갱신했다(그 줄은 v0.5.5 릴리스 아카이브를 가리키는 죽은 명령이었다).
- 검사 1종 신규 + 1종 교체(smoke 226 → **227**): `check_linter_config_resolution.py`(9).
  그리고 `check_v0_7_15_config_thresholds.py` 의 9번째 case 를 **문자열 검사에서 동작
  검사로** 바꿨다 — 그것은 runner 본문에서 `"load_config(project_root)"` 라는 *문자열*을
  찾고 있었다. 그 줄은 내내 있었고 다만 없는 경로를 묻고 있었다.
- **고치자마자 실제 드리프트가 나왔다** (당시엔 범위 밖으로 드러내기만 했고,
  **§2.48 에서 닫았다**): matrix 는 `Phase 13` 을 `in_progress` 로 적는데 roadmap 은
  그 단계를 현재로 말하지 않았다, `task-modes` 가 stable 인데 `test_path` 가 없다.
  후자는 위양성으로 판명됐다.
- 실측: 전량 smoke **227/227**(`dev,release,mcp-sdk` venv, `--tmp-dir=/var/tmp/saw-smoke`),
  mypy strict 121 files 0 errors(`Config File:` 줄로 정본 로드 확인), 되주입 3건 스팟
  체크 각각 다른 신호. **CI 4종 green 실측 완료**(`14cd792`) — §1 기준선 참조.
  `gh run view --log` 대신 `gh api repos/<o>/<r>/actions/jobs/<job_id>/logs` 로 받아
  러너의 자기 측정 줄(`All 227 …`, `Config File:`, `mcp SDK 실측`)을 직접 확인했다.
- **스모크 중에 저장소를 건드리지 말 것.** 전량 smoke 가 도는 동안 backlog index 를
  편집했더니 `check_no_repo_write` 가 red 로 나왔다. 단독 재실행하면 PASS —
  검사가 옳고 편집이 틀렸다.

---

이전 세션 기록: **close-out 마다 반복되던 수작업을 없앴다 (TASK-2026-07-31-main-002, §2.46).**
두 결함 다 같은 모양이었다 — **파생물을 만드는 쪽이 규약을 모른다.**

- **handoff §4 상한이 쓰는 쪽에 없었다.** 상한을 아는 자리가 셋(쓰는 쪽 /
  state.json 조립 / 린터)인데 값을 만드는 쪽만 몰랐다. 그래서 `--apply` 마다 11번째
  줄이 생겼고 사람이 손으로 지웠다(2026-07-28, 07-31 연속 2회). 정본을
  `common/project_docs.RECENT_DONE_ITEMS_CAP` 한 곳으로 모으고 셋이 그 이름을 읽는다.
  **이번 close-out 에서 실제로 10을 유지했다** — 가장 오래된 1건이 자동으로 빠졌다.
- **`latest_backlog_path` 가 항상 null, `task_count` 가 항상 0 이었다.** 경로 해석
  세 갈래가 `legacy_index_present` 하나에 매달려 있어서, append-only layout 에서는
  **명시한 `--latest-backlog-path` 인자까지 버려졌다**. 이제 (명시 인자 → legacy
  index → daily 디렉터리 최신) 순으로 보고, 실재할 때만 채택한다. `backlog` block 이
  통째로 죽어 있던 것이라 `task_count` 만의 문제가 아니었다.
- **죽은 필드는 소비자까지 얼려 둔다.** 살리자마자 두 건이 드러났다:
  `current_focus` 가 전부 done 인 날 **완료된 작업을 초점으로** 집었고(→ 미완료만
  고르도록), `run_workflow_linter` 가 state.json 의 상대 경로를 `branch_dir` 기준으로
  붙여 경로가 겹쳤다(→ workspace root 기준 + 실재 확인). 후자는
  `check_self_application` 이 잡았다.
- 검사 2종 신규(smoke 224 → **226**): `check_handoff_done_cap.py`(7) /
  `check_state_backlog_block.py`(8, 이 저장소 자신의 state.json 포함).
- 실측: 전량 smoke **226/226**(`dev,release,mcp-sdk` venv, 워킹트리 변경 0),
  mypy strict 121 files 0 errors, 되주입 9건 각각 다른 신호.
  **CI 4종 green 실측 완료**(`72bfbe0`) — §1 기준선 참조.

---

이전 세션 기록: **§2.43 이 남긴 "설치 순서에 기댄 우연" 을 선언으로 바꿨다 (TASK-2026-07-31-main-001,
§2.45).** 세 job 이 서로 다른 mcp 버전으로 돌고 있었는데 그렇게 정한 사람이 없었다.
smoke 의 설치 3줄을 매 줄 관측했다 — `requirements.txt` 뒤 **2.0.0**,
`requirements-dev.txt` 뒤 **1.27.0**, editable install 뒤 **1.27.0**. 즉 그 한 줄을
지우면 1.x 커버리지가 조용히 사라지는데 아무 검사도 실패하지 않았다.

- 정본 `workflow_kit/common/sdk_matrix.py` 가 (a) 밟을 버전 3종과 근거, (b) 각 job 의
  정책(`pinned`/`floating`/`matrix`)과 그 버전이 **어디서 오는지** 를 적는다.
- `mcp-sdk-matrix` workflow 는 registry 에서 목록을 뽑아 `fromJson` 으로 matrix 를
  만든다 — **yml 에 버전 문자열이 없다**. path 필터도 없다(§2.43 이 늦게 발견된 이유).
- 기존 3 job 은 `--record <job>` 으로 집힌 버전을 step summary 첫 화면에 남긴다.
  `pinned` 인 smoke 는 어긋나면 실패한다.
- `check_mcp_sdk_matrix.py` 13건이 registry ↔ `requirements-dev.txt` ↔ pyproject extra
  ↔ workflow yml 을 **양방향**으로 묶는다.

**matrix 가 만들자마자 실제 결함을 하나 잡았다** — `check_read_only_mcp_sdk_stdio.py` 가
mcp 2.x 에서 깨져 있었다(`serverInfo` → `server_info` 등). 서버는 §2.43 에서 이관했지만
**읽는 쪽은 범위 밖**이었고, 이 검사는 smoke 에서만 = 1.x 로만 돌아서 아무도 못 봤다.
이번엔 전수 sweep 을 먼저 해 클라이언트 표면이 이 파일 하나임을 확인하고 고쳤다.

**판정을 두 번 고쳐 썼다** (§2.45): skip 문자열 탐지 → 위양성(`check_mcp_server_sdk_compat`
가 fail-fast 를 확인하느라 그 문자열을 *의도적으로* 출력), `run_all_checks` 의 `last_line`
→ 증거를 못 나름(1.x 는 SDK 로그가 뒤에 붙는다). 최종은 **판정이 왕복 검사 2건을 직접
돌려** exit 0 + 성공 메시지를 요구한다.

- 실측: 격리 venv 3종(1.27.0/1.29.0/2.0.0) 각각 요청=설치 일치 + subset 12/12 +
  왕복 증거 2/2. mypy strict 121 files 0 errors. 전량 smoke **224/224**
  (`dev,release,mcp-sdk` venv, 누수 0, 워킹트리 변경 0). 되주입 7건 각각 다른 신호.
- **수치에는 extra 조합을 함께 적을 것.** `release` 없는 venv 에서는 같은 트리가
  219/224 다 (3건은 문서가 223 이라 적고 있어서, 2건은 `build` 부재).
- **CI 러너 실측 완료**: 6종 green + matrix 3 셀 전부 요청=설치 일치·12/12·증거 2/2.
  `gh run view --log` 가 일부 run 에서 **빈 출력**을 낸다 (rc=0, size=0) — 없는 것이
  아니라 못 받은 것이다. `gh api repos/<o>/<r>/actions/jobs/<job_id>/logs` 로 받으면
  나온다. 이 경로로 세 job 의 `mcp SDK 실측` 줄을 확인했다.

---

이전 세션 기록: **의존성 드리프트로 `mypy-strict` 가 red 로 넘어갔다 — 상한 핀으로
되돌리고 원인 2건을 task 로 등록했다.** 문서 2줄만 바꾼 `23874d1` 에서 mypy-strict 가 실패했는데, 커밋
내용과 무관했다. CI 설치 로그에 **`mcp-2.0.0`** 이 찍혀 있고 (extra 가 `mcp[cli]>=1.0` 로
상한이 없었다) 같은 소스에 버전만 갈아 끼워 재현했다 — `1.28.1` green / `2.0.0` 에서
`mcp_v1_server.py:27 no-any-return`.

**에러 메시지가 원인에서 한 칸 떨어진 곳을 가리키고 있었다.** 실제 사실은 mcp 2.0.0 이
`mcp.server.fastmcp` 모듈 자체를 없애고 `mcp.server.mcpserver.MCPServer` 로 옮긴 것이다
(2.0.0 의 `mcp.server` 하위 모듈 목록 실측). 즉 타입 문제가 아니라 `HAS_FASTMCP=False` →
`sys.exit(1)` 인 **런타임 파손**인데, `pyproject.toml` 의 `ignore_missing_imports = true` 가
사라진 모듈을 error 가 아니라 `Any` 로 바꿔 놓아 27번 줄에서야 표면화됐다.

1차 조치는 상한 핀이었고(red 를 켜 둔 채로는 다음 커밋의 신호를 읽을 수 없어서지, 그것이
해결이어서가 아니다), 이후 TASK-2026-07-29-main-001 로 **wrapper 이관**을 마쳤다 — 세부는
릴리스 노트 §2.41. wrapper 가 2.x → 1.x 순으로 두 이름을 시도하고 어느 쪽을 잡았는지
`MCP_SERVER_SOURCE` 로 남긴다. `1.27.0`/`1.28.1`/`1.29.0`/`2.0.0` 네 버전에서 mypy strict
119 files 0 errors + 런타임(실제 서버 2종 tool 등록까지)을 각각 실측했다.

**거기서 핀을 한 번 풀었는데 그것이 틀렸다.** "이관했다" 의 범위를 SDK 표면이 아니라
**파일 하나**로 잡았다. 같은 SDK 를 쓰는 표면이 하나 더 있었고(`read_only_mcp_sdk.py` 의
lowlevel 서버), 핀을 푼 커밋이 처음으로 `server/**` 를 건드려 `mcp-inspector` 를 깨우기
전까지는 어느 검사도 그것을 보지 않았다. `grep '^from mcp'` 는 wrapper 만 짚어 준다 —
두 번째 표면은 `importlib.import_module("mcp…")` 로 들어와서 안 걸렸다.

**그 표면도 TASK-2026-07-29-main-003 으로 닫았다(§2.43).** import 문법 4가지로 전수
조사해 표면이 정확히 둘임을 먼저 확인한 뒤 **상한 핀을 해제**했다. 지금 `mcp` 는 상한이
없고, 두 표면 모두 1.x/2.x 를 해석한다.

- 기준선을 `71feef3` 으로 옮겼다. smoke(7m40s)·mypy-strict 둘 다 success 실측이고,
  설치 로그에서 러너가 실제로 집은 버전이 `mcp-1.29.0` 임을 확인했다 — 핀이 상한을
  걸고 있다는 것을 선언이 아니라 로그로 확인한 것이다. `mkdocs` 는 이번 변경 경로가
  path 필터에 안 걸려 미실행.
- 확인 방법: `gh run list --commit $(git rev-parse HEAD)` (**full SHA 필수** — short SHA 는
  조용히 0건을 낸다). smoke 는 러너에서 약 8분 걸리므로 push 직후 조회는 `in_progress` 다.
- smoke 가 이 드리프트에 안 걸린 것은 설계가 아니라 **설치 순서 덕**이다 —
  `requirements-dev.txt` 의 `mcp[cli]==1.27.0` 이 뒤에 깔리며 되돌려 놓는다. mypy-strict
  job 은 그 파일을 안 깔아서 그대로 맞았다.

앞 세션(TASK-2026-07-28-main-003)은 §2.39 후속의 이관 파서 결함을 닫았다 — 세부는 릴리스
노트 §2.40. 구분 heading(`### Historical archives`)을 몰라서 그 줄이 직전 entry 의 body 로
흘러들고(실측 `TASK-2026-06-05-001`) 아래 entry 들의 소속이 소실되고 있었다.

- [x] ~~TASK-2026-07-29-main-001 — mcp 2.0.0 이관(wrapper)~~ → **완료(§2.41)**. `.tool()` 은
      두 SDK 모두 "함수를 그대로 돌려주는 decorator" 라 wrapper 계약(`Callable[..., Any]`)이
      유효함을 확인했고, `cast` 로 좁혀 반환한다. **1.x 지원은 끊지 않았다** — 두 이름을
      모두 시도한다.
- [x] ~~`mcp-inspector` red — Python 문제인 줄 알았다~~ → **§2.42 에서 조치**. 핀 복원 후에도
      red 였고, 이번엔 Python 이 아니었다. `npx -y @modelcontextprotocol/inspector` 가
      버전 고정이 없어 Node 쪽 인스펙터도 **2.0.0** 으로 넘어갔고, `[target...]` 인자를
      삼켰다 (argv wrapper 로 `ARGC=0` 실측 → 맨 python 이 REPL 로 떠서 JSON-RPC 의
      `true` 를 Python 으로 실행 → `NameError`). `--config`/`--server` 선언 방식 +
      `@2` major 고정 + 빈 응답 실패화. 로컬 전 구간 13/13 일치 확인.
- [x] ~~TASK-2026-07-29-main-003 — lowlevel 이관~~ → **완료(§2.43). 상한 핀 해제.**
      분기 기준을 버전 문자열이 아니라 **계약의 존재**로 잡았다
      (`uses_handler_registration` = `hasattr(server, "add_request_handler")`).
      프로토콜 왕복을 실제로 돌려 확인했다 — 1.28.1/2.0.0 에서 `tools/list` 13개,
      `tools/call` 성공·실패 경로, **두 버전의 wire 산출물이 JSON 동일**.
      - `isError` 를 나중에 대입하던 것이 2.x 에서 `is_error` 라 빗나가 **실패한 tool
        호출이 성공으로 보고될** 자리였다 → 생성 시점 `force_error` 로 이동.
      - `Tool`/`CallToolResult` field 는 2.x 가 snake_case 로 바꿨지만 camel alias 로
        양쪽을 받아 payload 조립은 갈라 쓰지 않았다.
      - 핀 해제 전에 import 문법 4가지로 전수 조사해 표면이 정확히 **2개**임을 확인했다
        (§2.41 에서 이 조사를 안 한 것이 그때의 실수였다).
      - `version` 은 계속 전달하지 않는다. 2.x `MCPServer` 는 받지만 1.x `FastMCP` 는
        받지 않고, 여기서 넘기기 시작하면 서버 2종이 광고하는 version 이 바뀐다 —
        이관 범위 밖이라 기존 동작을 유지했다. 바꾸려면 별도 결정이 필요하다.
- [x] ~~핀 해제로 CI 가 두 major 를 동시에 밟는다 — 설치 순서에 기댄 우연~~ →
      **완료(§2.45)**. matrix 는 `pinned` 3종만 본다. **새 major 조기 경보는 여전히
      floating job(`mypy-strict`/`mcp-inspector`)에 의존한다 — 이것은 의도다.** 그 층이
      2.0.0 을 물어 왔고, 없애면 경보를 잃는다. 대신 부동이라고 적고 집힌 값을 남긴다.
      다음 major 를 matrix 에 넣는 것은 registry 에 한 줄 추가하는 일이다.
- [x] ~~TASK-2026-07-29-main-002 — `ignore_missing_imports` 탐지 구멍~~ → **완료(§2.44)**.
      **판정 기준을 먼저 정했다: 설정을 좁히지 않는다.** optional dep 은 실제로 optional 이라
      `mcp.*` 만 빼면 SDK 미설치 로컬이 red 가 되고, 더 근본적으로 **mypy 는 "안 깔림" 과
      "깔렸는데 모듈이 사라짐" 을 구분할 수 없다** — 그 구분은 런타임 import 에서만 된다.
      설정은 그대로 두고 판정을 옮겼다.
      - `common/optional_deps.py` 가 import 대상 정본. `required`(전부) /
        `alternative`(하나만) 두 종류로 나눴다 — 이 구분이 없으면 2.x 에서 검사가
        **틀린 실패**를 낸다. `read_only_mcp_sdk.SDK_IMPORT_TARGETS` 의 사본은 제거.
      - **완료 기준 확인**: 이관 전 가정을 되주입하면 1.28.1 은 통과, 2.0.0 은
        `'mcp.server.fastmcp' 모듈이 없다 (ModuleNotFoundError)` 로 실패한다. 같은
        상황에서 mypy 가 냈던 `no-any-return` 과 대비된다.
      - skip 은 조용히 넘기지 않는다 — 몇 건을 왜 건너뛰었는지 출력한다
        (로컬 2건, mcp 없는 venv 6건 실측).
- [x] ~~`backlog-update` 가 handoff §4 에 상한을 적용하지 않는다~~ → **완료(§2.46)**.
      쓰는 쪽(`sync_handoff_status`)이 상한을 적용한다. 정본은
      `common/project_docs.RECENT_DONE_ITEMS_CAP` 한 곳이고 린터의 리터럴 사본도 없앴다.
- [x] ~~`state.json` 의 `backlog.task_count` 는 항상 0, `latest_backlog_path` 는 항상
      `null`~~ → **완료(§2.46)**. 경로 해석을 세 갈래로 분리했다. `backlog` block 이
      통째로 죽어 있던 것이라 `task_count` 만의 문제가 아니었다.
- [x] ~~**`run_workflow_linter.py` 의 `project_root` 가 저장소 루트보다 한 단계 위를
      가리킨다**~~ → **완료(§2.47)**. 기준을 `project_workspace_root` 로 통일하고,
      정본이 `workflow-source/pyproject.toml` 인 문제는 사본이 아니라 `--config-path`
      명시로 풀었다. **같은 값이 `--maturity` 경로에도 쓰이고 있어서, 그쪽은 늘
      `skipped` 인데 `status: ok` 로 보고되고 있었다** — 그것도 같이 닫았다.
- [x] ~~**`--maturity` 를 처음 실제로 돌리니 내용 드리프트 2건이 나왔다**~~ →
      **완료(§2.48)**. roadmap 은 진짜 드리프트라 문서를 고쳤고(matrix 를 사실로 채택),
      `task-modes` 는 `kind: "spec"` 을 린터가 몰라서 난 **위양성**이라 검사를 고쳤다.
- [x] ~~**`workflow_kit.cli.doctor` 는 아직 provenance 를 안 쓴다**~~ → **완료(§2.49)**.
      열어 보니 기준 경로가 **저장소 루트의 두 단계 위**였다 — provenance 만의 문제가
      아니었다. 기본값을 cwd 로 바꾸고 `--config-path` + `config_provenance` 를 더했다.
- [ ] **`--project-root` 는 state.json 기준과 설정 기준 두 역할을 겸한다.** 이 저장소처럼
      둘이 갈라진 배치에서는 `--config-path` 를 매번 줘야 한다. 분리는 별도 결정.
- [x] ~~**경로 기준을 잡는 다른 진입점이 더 있는지 전수 조사하지 않았다.**~~ →
      **완료(§2.50)**. AST 전수 조사 결과 경로 축에서는 세 번째가 없었고(저장소 밖 착지
      0건), 대신 **branch 축**에서 나왔다. `workflow_branch_dir` /
      `workflow_archived_branch_dir` 를 v1.0.1 규칙에 맞췄다.
- [x] ~~**`dashboard_data._repo_root` 의 `workspace_root=None` fallback**~~ →
      **완료(§2.51)**. 설치본 배치에서 `<venv>/lib/python3.13` 이 나오는 것을 실측하고
      (명시 → cwd) 두 갈래로 바꿨다. snapshot 에 `workspace_root_source` 를 싣는다.
- [ ] **`_branch_scoped_or_legacy(active_dir, ...)` 는 여전히 `get_current_branch()`**
      로 떨어진다. active dir 만 받아 workspace 를 역산하지 않는 것이 의도라 남겼다.
- [x] ~~**전수 조사 스크립트를 저장소에 남기지 않았다**~~ → **완료(§2.52)**.
      `tools/audit_root_anchors.py` + `check_root_anchor_audit.py`(10 case)로 정례화.
- [x] ~~**조사 범위가 `SCAN_DIRS` 선언에 묶여 있다**~~ → **완료(§2.53)**. 포함 목록을
      없애고 전수 순회 + 소비자 측 독립 대조(case_10)로 바꿨다. 빠져 있던 27 file 편입.
- [x] ~~**제외는 여전히 이름 기반**(`EXCLUDED_PARTS`)~~ → **완료(§2.54)**. git 저장소에서는
      `.gitignore` 를 정본으로 쓴다. **남은 것**: git 이 없는 환경(소비자 프로젝트 등)에서는
      여전히 이름 fallback 이다 — 다만 이제 `source_selection` 으로 드러난다.
- [ ] **R1/R2 는 `Path` 계열 표현만 본다** — `os.path.dirname` 연쇄는 미탐이다
      (현재 저장소에는 없다).
- [ ] **handoff §4 는 상한만 생겼고 정렬 기준은 여전히 없다.** `tasks_dir` 이 있는
      저장소는 builder 가 task SSOT 를 먼저 쓰므로 무해하지만, legacy 저장소(task 파일
      부재)에서는 handoff 가 tail fallback 이 되고 builder 가 **앞에서** 자르므로
      오래된 것이 남는다.
- [x] ~~판정 근거가 없어 비워 둔 2건~~ → **둘 다 `done` 으로 판정 완료**.
      `archived/{codex/phase6,gemini/phase10}/` 의 handoff·day file 을 대조해 근거를 찾았다
      (task 파일 Outcome 에 근거 기록). `unknown_status_items` 는 이제 빈 목록이다.
- [x] ~~이관 도구가 비-task section 도 task 로 만든다~~ → **§2.40 에서 조치**. 파서가 구분
      heading 을 인식해 직전 entry 를 닫고, 소속을 `source_group:` 으로 보존하며, 이관
      summary 에 "확인 필요" 로 노출한다. **"아카이브 포인터면 task 가 아니다" 는 판정은
      도구가 하지 않는다** — 프로젝트 결정이라 드러내기만 한다.
- [ ] **아카이브 포인터 2건을 task 로 둘지는 미결.** 현재는 `source_group: Historical archives`
      가 붙은 채 `done` 으로 남아 있다. 정리(삭제/이동)할지는 프로젝트 결정.
- [ ] **`recent_done_items` 는 여전히 파생물이고 10개 상한이다.** 손으로 쓴 긴 서술은 다음
      `backlog-update` 실행에서 task SSOT 의 제목으로 재생성된다 — 상세의 집은 task SSOT 와
      릴리스 노트다. (정렬은 §2.38 에서 최신순으로 고쳤다. 상한 자체는 유지.)
- [ ] **daily index 의 "`status` 줄이 없으면 done" fallback 은 남아 있다**(builder §2 구간).
      task 파일이 있으면 그것이 SSOT 라 이 저장소에서는 발현하지 않지만(104건 전부 task 파일
      보유), *구형 index 만 있는 legacy 저장소* 에서는 여전히 추측이다. task 쪽은 §2.39 에서
      닫았고 이쪽은 호환 때문에 남겼다.
- [ ] **dashboard Panel 5 (`collect_recent_releases`)는 브랜치 간 정렬 키가 없다.** 브랜치별
      `state.json` 을 이어 붙인 뒤 앞에서 자른다 — 브랜치 *안* 은 이제 최신순이지만 브랜치
      *간* 은 여전히 concat 순서다 (항목 문자열에 날짜가 없다).
- [x] ~~슬래시(`/`) 브랜치에서 `check_branch_scoped_memory` 와 `check_self_application`
      이 깨진다~~ → **완료(§2.55)**. 실제로는 **셋**이었고(`check_workflow_linter` 추가),
      `check_self_application` 은 **슬래시와 무관**했다(모든 새 브랜치에서 red).
- [ ] **`session_handoff_template.md` 의 `../../docs/` 링크가 깊이 의존이다.** 슬래시와
      무관하게 branch-scoped layout 전반의 문제다 — 템플릿이 legacy 평면 layout 기준으로
      쓰였다. 이 저장소 handoff 는 손으로 쓴 링크라 현재는 동작한다. 별도 판단 필요.
- [x] ~~**슬래시 브랜치 전량 smoke 를 CI 에 정례화할지 미결**~~ → **완료(§2.56)**.
      smoke 를 `branch_context` 2셀 matrix 로. 전량을 두 컨텍스트로 돌린다.
- [ ] **컴퓨트가 2배다**(wall-clock 은 병렬이라 동일). smoke 가 더 길어지면 재검토 대상.
- [x] ~~스케줄 workflow 2건 여전히 red~~ → **완료(§2.57)**. 둘 다 알려진 원인(URL 검증 /
      issue 게시)이 **아니었다** — CLI 옵션 등록 삭제 2건과 저장소 라벨 부재였다.
- [ ] **`consumer-metrics-digest` 의 traffic API 403**(`Resource not accessible by
      integration`)은 WARN 처리라 치명적이지 않지만 남아 있다. `GITHUB_TOKEN` 권한 문제.
- [x] ~~**두 스케줄 workflow 를 실제로 트리거해 보지 않았다**~~ → **완료**.
      `consumer-metrics-digest` success. `okf-validate` 는 실패하지만 **원인이 바뀌었다**.
- [ ] **`okf-validate` 의 URL 추출기가 산문까지 훑고 마크다운 구문을 URL 에 포함시킨다**
      (위양성 1건). frontmatter 만 훑고 URL 경계를 끊을 것.
- [ ] **샘플 번들의 `resource:` 필드에 괄호 주석이 들어 있다** — bare URL 규약 위반.
      데이터를 고치고, 그 규약을 검사로 고정할 것.
- [ ] `active/<branch>/` 로 바뀐 bootstrap layout 을 실제 소비자 프로젝트에 적용해 볼 것
      (기존 평면 프로젝트는 유지되지만, 옮기려면 `tools/migrate_memory_to_branch_scoped.py`)

## 6. 남은 리스크 / 확인하지 못한 것

- **이번 세션의 교훈(§2.60, 판단은 실측 뒤에 한다)**: Claude Code MCP 를 붙이며 "정식 MCP
  하네스니까 `stdio-sdk` 를 써야 한다" 고 먼저 판단했는데 **재 보니 정반대였다.** emit 되는
  `command` 는 `python3` 즉 **시스템 python3** 이고 거기엔 `mcp` SDK 가 없어서 `stdio-sdk` 는
  `Connection closed` 로 죽는다. 이름이 초라한 `jsonrpc-bridge`(default)가 공식 MCP
  클라이언트와 왕복이 정상이다 — **두 transport 모두 MCP 를 말하고, 갈리는 건 프로토콜이
  아니라 의존성이었다.** 이름과 문서의 `transport_ready: false` 둘 다 오해를 부르는
  자기 선언이었다. 처방을 정하기 전에 *무엇으로 실행되는가* 를 먼저 잴 것.
- **이번 세션의 교훈(§2.60, 커밋되는 파일에 기계 고유값)**: `.mcp.json` 의
  `STANDARD_AI_WORKFLOW_ROOT` 가 절대 경로였다. 커밋되는 파일이라 한 사람의 체크아웃
  위치가 공유 파일에 박힌다. 단서는 **같은 env 블록 안에 이미 있었다** — `PYTHONPATH` 가
  상대(`workflow-source`)였다. 한 블록 안에서 두 값의 기준이 다르면 둘 중 하나는 틀렸다.
- **이번 세션의 교훈(§2.59)**: **생성기를 검사하는 것과 산출물을 검사하는 것은 다른
  일이다.** `check_harness_skill_frontmatter` 는 렌더러 안의 문자열 리터럴을 4 case 로
  검사하며 계속 PASS 였는데, 그 리터럴이 파일이 되는 마지막 한 걸음(`write_text` →
  `stamp_marker`)에서 버전 마커가 1행에 붙어 `---` 를 2행으로 밀어냈다. frontmatter 는
  **위치 계약** 이라 그 순간 평범한 산문이 되고, 하네스는 skill 을 아예 못 본다.
  이미 배포된 opencode skill·agent 5종·grok skill 까지 8개 블록 전부가 같은 상태였다.
  검사를 쓸 때는 **어느 층까지 검사하는지**를 적고, 산출물 층은 따로 덮을 것.
- **이번 세션의 교훈(§2.59, 요구 목록은 파생시킨다)**: `.claude/` 가 통째로 없는데
  자기적용 검사가 green 이었던 이유는 하나다 — `REQUIRED_ENTRYPOINTS = ("CLAUDE.md",)`
  가 `HarnessSpec.entry_files` 의 **손복사본** 이라 `extra_files` 를 아예 보지 않았다.
  같은 부류가 하루에 셋 더 나왔다: `total = 5`(케이스 수 하드코딩, 늘리자 "3/5" 로
  갈라짐), `len(extra_files) == 3`(계약은 "3종이 있는가" 인데 개수로 대리 판정),
  `check_docs` 의 overlay 노출. **판정 목록은 정본에서 파생시키면 따라온다.**
- **이번 세션의 교훈(§2.59, 개수는 계약이 아니다)**: `len(...) == 3` 은 "3종이 유지되는가"
  의 약한 대리물이다. 실제로 계약을 지킨 채 skill 하나를 더했을 뿐인데 두 검사가 깨졌다 —
  **깨져야 할 때 안 깨지고, 안 깨져도 될 때 깨진다.** 이름으로 존재를 물을 것.
- **이번 세션의 교훈(§2.59, 있는 것만 검사하면 없는 것은 못 잡는다)**: push 직후 하네스가
  실제로 로드하면서 "확인 못 함" 이 즉시 답을 냈다 — skill 은 정상 표시됐는데 **slash
  command 3종의 설명이 `<!-- standard-ai-workflow-kit: v1.0.0-beta -->` 로 떴다.**
  command 에는 frontmatter 가 없어 Claude Code 가 첫 줄을 설명으로 집었고, 거기 마커가
  앉아 있었다. 무조건 prepend 의 **두 번째 피해자**다. 핵심은 이거다 —
  `check_harness_skill_frontmatter` 의 1-5번은 전부 *있는* frontmatter 를 검증하므로
  **없는 것을 구조적으로 못 잡는다.** "무엇이 있어야 하는가" 를 묻는 case 를 따로
  뒀다(`test_claude_code_surfaces_declare_description`, 대상 <4 면 실패).
- **확인 완료(§2.59, 위 항목이 갱신)**: 발행한 skill 과 command 3종을 **실제 에이전트
  세션이 로드하는 것까지 실측했다** — 첫 커밋의 "확인 못 함" 은 push 가 해소했다.
  다만 그 실측이 결함을 하나 더 냈고, 커밋 2개째가 그것이다.
- **이전 세션의 교훈(§2.58)**: **검사가 내는 이름은 검출기가 아는 만큼만 말한다.**
  `V-R10-online-stale`("링크가 죽었다")로 보고된 2건은 죽은 링크가 아니라 *태어난 적 없는*
  링크였다. 검출기는 "이 URL 에 접근이 안 된다" 까지만 알고, "그 URL 이 어떻게 만들어졌는지"
  는 모른다. **red 를 그 이름대로 믿고 고치면 엉뚱한 곳을 고친다** — 값의 출처까지 거슬러
  올라갈 것.
- **이번 세션의 교훈(§2.58, 입력단도 검사 대상이다)**: 검사기(`url_validity`)는 17 case 로
  덮여 있었는데 **무엇을 먹일지 정하는 층**은 워크플로우 안의 grep 한 줄이었고 검사가 0건
  이었다. 그 한 줄이 위양성과 누락을 동시에 만들었다. **검사기를 검사했다고 그 검사가 옳은
  것을 보는 것은 아니다.**
- **이번 세션의 교훈(§2.58, 누락은 조용하다)**: 위양성 1건은 red 로 보였지만, 같은 결함이
  만든 **누락**(``a + b`` 의 두 번째 URL)은 아무 신호도 안 냈다. blog URL 은 7주가 아니라
  **처음부터** 검사된 적이 없다. §2.53/§2.54 와 같은 자리 — 0건은 "결함 없음" 과 "안 봤음"
  을 같은 모양으로 낸다.
- **확인 못 함(§2.58)**: 이제 검사에 들어가는 URL 4건이 **전부 외부 호스트**다. 그중 하나가
  실제로 죽으면 같은 이름으로 red 가 되지만 그때는 진짜 stale 이다 — 로그의 provenance
  줄로 구분할 것.
- **이번 세션의 교훈(§2.58, 조회 실패가 완료로 보였다)**: CI 를 기다리려고 건 monitor 가
  `gh run list --commit <sha>` 로 물었는데 **빈 결과**가 왔고, 스크립트는 그걸 "대기 0건" 으로
  세어 *전부 끝났다* 고 알렸다. 실제로는 두 개가 돌고 있었다. 이번에 고친 결함과 **같은
  모양**이다 — 못 본 것과 없는 것이 같은 값으로 나오면 그 판정은 무력화된다. 다시 걸 때는
  run ID 를 직접 물어 각 run 의 상태를 확인하게 고쳤다.
- **이번 세션의 교훈(§2.57)**: **오래 red 인 것은 아무도 안 보고, 그래서 원인이 이름과
  달라진다.** 두 건 다 알려진 이름("URL 검증 실패" / "issue 게시 실패")과 실제 원인이
  달랐다. red 를 방치하면 그 red 는 *증상 이름* 만 남고 사실은 사라진다.
- **이번 세션의 교훈(§2.57, skip 의 범위)**: "network 의존이라 skip" 은 옳은 판단이었지만
  **너무 넓게 적용**됐다. 네트워크 의존은 *호출* 을 건너뛸 이유이지 *인자 계약* 이나
  *실행 분기* 를 건너뛸 이유가 아니다 — 그 둘은 오프라인이다. **skip 할 때 무엇까지
  skip 되는지 볼 것.**
- **이번 세션의 교훈(§2.57, 파싱 ≠ 실행)**: 인자 계약 검사 2종이 통과하는 동안
  `args.max_bytes` 는 여전히 없었다. 실행 경로를 밟는 case 만 그것을 잡았다(16/17 실측).
  **CLI 를 검사할 거면 `main()` 을 부를 것** — 외부 의존만 스텁하고 분기는 실제로 태운다.

- **이번 세션의 교훈(§2.56)**: 결함을 고치는 것과 **그 결함이 다시 나면 잡히는가** 는
  다른 일이다. §2.55 는 3건을 고쳤지만 검증이 *손으로 env 를 덮은 1회 실행* 이었다 —
  그 상태로 두면 다음 결함도 똑같이 오래 산다. **고친 뒤에는 "이걸 누가 매번 재는가" 를
  물을 것.**
- **이번 세션의 교훈(§2.56, 목록의 유혹)**: 싼 방법은 "슬래시에 민감한 검사 3개만" 돌리는
  것이었다. 그러나 §2.55 가 **그 목록이 틀린다는 증거 자체**였다 — 지목된 2건 중 1건이
  오귀속이었고 진짜 3번째는 목록에 없었다. 비용이 두 배여도 전량을 돌린다.
- **확인됨(§2.56)**: 오버라이드가 러너에서 실제로 먹는다 — `CODEX_WORKFLOW_BRANCH` 가
  `GITHUB_HEAD_REF`/`GITHUB_REF_NAME` 보다 우선함을 CI 자기 측정으로 확인했다. §2.50 이
  정확히 이 축(`GITHUB_REF_NAME` 이 모든 workspace 에 우선해 검사를 무력화)에서 데였으므로
  확인 없이 넘어갈 수 없는 자리였다. 자기 검증(`::error::`)도 함께 돌았고 0건이다.

- **이번 세션의 교훈(§2.55)**: **한 환경에서만 재면 그 환경의 결함만 보인다.** 세 번째
  결함은 handoff 어디에도 없었고, 슬래시 브랜치로 **전량** smoke 를 한 번 돌린 것이
  유일한 발견 계기였다. 이름으로 지목된 목록만 확인했으면 놓쳤다.
- **이번 세션의 교훈(§2.55, 기록된 원인을 의심할 것)**: handoff 가 "슬래시에서 2건이
  깨진다" 고 적었지만, 한 건은 **슬래시와 무관**했다(모든 새 브랜치에서 red). 증상이
  같이 관측됐다고 원인이 같지는 않다 — **가르는 실험**(무슬래시 새 브랜치)을 한 번
  돌리는 것으로 갈렸다.
- **이번 세션의 교훈(§2.55, 깨진 것은 검사였다)**: 제품은 이미 슬래시를 감당하고 있었다.
  fixture 가 **제품이 만들지 않는 모양**을 만들고 있었던 것이 결함의 정체다. 되주입과
  같은 축이다 — fixture 는 내가 상상한 모양이고 제품은 실제 모양이다.

- **이번 세션의 교훈(§2.52)**: **조사를 남기지 않으면 조사는 없었던 것과 같다.** §2.50 이
  AST 로 전수 조사를 하고도 스크립트를 안 남겨서, 바로 다음 건(§2.51)을 또 손으로 찾았다.
  일회용으로 돌린 조사는 그 순간의 답만 주고 *다음 번 답을 주지 않는다*.
- **이번 세션의 교훈(§2.52, 되주입의 범위)**: 되주입을 **fixture 에만** 했다면 검출기의
  구멍을 못 봤다. R2 가 "기본값 `None`" 만 보고 있었고, 정작 §2.51 의 결함 함수는 기본값
  없이 **型으로만** 미지정을 받았다. fixture 는 내가 상상한 모양이고 실제 소스는 실제로
  있던 모양이다 — **되주입은 실제 소스에 할 것.**
- **이번 세션의 교훈(§2.52, 감사자도 감사 대상이다)**: 처음 쓴 조사 도구가 저장소 밖에서
  불리면 조사 0건인데 "미선언 0건" 이라고 말하고 exit 0 이었다. **조사 0건은 결함 0건이
  아니다.** 감사하는 함정(§2.51)에 감사자가 그대로 빠졌다.
- **이번 세션의 교훈(§2.53)**: **포함 목록은 자기 사각지대를 볼 수 없다.** "선언했는데
  없는 것" 은 셀 수 있어도 "있는데 선언 안 한 것" 은 그 구조 안에서 셀 방법이 없다.
  이런 자리는 검사를 덧붙이는 것보다 **선언 자체를 없애는** 쪽이 낫다 — 감시할 것을
  줄이는 게 감시를 늘리는 것보다 강하다.
- **이번 세션의 교훈(§2.53, 바닥선의 한계)**: 개수 바닥선은 **붕괴**만 본다. 범위가 조금
  줄어드는 것(446 → 427)은 통과시킨다. *누락* 을 보려면 **목록 대 목록 대조**가 필요하고,
  그 대조는 반드시 **소비자 쪽에서 독립적으로 다시 세야** 한다. 도구가 낸 개수를 되읽으면
  자기 자신과 비교하는 것이다. 그래서 도구는 개수가 아니라 **목록**(`scanned_paths`)을
  내야 한다.
- **이번 세션의 교훈(§2.54)**: **판정 근거가 이미 저장소에 있는데 약한 사본을 쓰고 있었다.**
  "무엇이 생성물인가" 는 `.gitignore` 가 이미 선언한 사실이고, 이름 목록은 그 사본이었다.
  사본은 반드시 갈라진다 — 사본을 고치지 말고 **정본에 물을 것**. [규약은 단일 출처로]
- **이번 세션의 교훈(§2.54, 조용한 쪽이 틀린 쪽이다)**: 같은 결함 fixture 에서 git 모드는
  미선언 1건, 이름 모드는 미선언 **0건**을 냈다. 놓치는 판정이 **더 깨끗해 보인다** —
  0건은 "결함 없음" 과 "안 봤음" 을 같은 모양으로 낸다. 그래서 `source_selection` 처럼
  *어떻게 골랐는지* 가 늘 산출물에 있어야 한다.
- **확인 못 함(§2.53)**: R1/R2 는 `Path` 계열 표현만 본다(`os.path.dirname` 연쇄 미탐 —
  현재 저장소에는 없다). 그리고 이번 커밋에서는 **mkdocs 가 트리거되지 않았다** — path
  필터대로지만, "4종 green" 이 아니라 "트리거된 3종 green" 이 사실이다.
- **별건(변동 없음)**: 스케줄 workflow `okf-validate`(V-R10 online URL 검증)는 2026-07-22
  이후 **6회 연속 red** 다. 정기 실행이라 main 최신 SHA 에 붙어 커밋 옆에 실패로 보이지만
  push 가 트리거한 것이 아니다(`exit code 123` 까지만 확인, 원인 미조사).
- **이번 세션의 교훈(§2.48)**: 검사를 켜면 보고가 온다. 그때 **다 믿어서도 안 되고 다
  지워서도 안 된다** — 한 건은 문서를 고쳐야 했고 한 건은 검사를 고쳐야 했다. 둘을 가른
  것은 `kind: "spec"` 이라는 사실 하나였고, 그 사실은 **이미 저장소 안에 있었는데 읽는
  층이 하나뿐**이었다. 규약을 아는 자리가 하나뿐이면 나머지 층은 위양성을 낸다.
- **이번 세션의 교훈(§2.48, 위양성 비용)**: 위양성을 내는 검사는 무시당하고, 그러면 같은
  검사가 잡아 줄 **진짜 결함도 함께 무시된다**. 실제로 이번 두 건은 같은 실행에서 같이
  나왔다 — 하나를 노이즈로 치웠다면 다른 하나도 함께 사라졌을 것이다.
- **이번 세션의 교훈(§2.47)**: §2.44 는 "관대한 *설정* 이 판정을 지운다" 였고 이건 그
  사촌이다 — **관대한 *fallback* 이 자기가 무엇을 못 했는지 말하지 않는다.** 실패하지
  않는 loader 를 만들 거면, 무엇을 물었고 무엇을 얻었는지는 반드시 함께 내놓아야 한다.
  그러지 않으면 "적용됨" 과 "떨어짐" 이 같은 모양이고, 같은 모양인 동안에는 아무도
  결함을 볼 수 없다.
- **이번 세션의 교훈(§2.47, 검사 쪽)**: `check_v0_7_15_config_thresholds` 의 9번째 case 는
  runner 본문에서 `"load_config(project_root)"` 라는 **문자열**을 찾고 있었다. 그 줄은
  내내 있었고 다만 없는 경로를 묻고 있었다 — **통과하면서 아무것도 보장하지 못하는
  검사**였다. 문자열이 아니라 **산출물의 사실**로 판정할 것.
- **이번 세션의 교훈(§2.40)**: §2.39 는 "판정 근거가 없으면 채우지 말라" 였는데, 이건 그 앞
  단계다 — **판정 근거를 애초에 버리지 말 것.** 아카이브 포인터인지 작업 항목인지 구분할
  단서는 구분 heading 하나뿐이었고, 이관이 그걸 버려서 판정 자체가 불가능해졌다.
  **이관은 형식을 바꾸는 일이지 사실을 줄이는 일이 아니다.**
- **이번 세션의 교훈(§2.39)**: 어휘가 모자라 보일 때 **먼저 의심할 것은 축이 섞였는지**다.
  `recorded` 는 다섯 번째 진행 상태가 아니라 *출처* 였다. 어휘를 늘렸다면 정본과 소비자
  validator 를 다 깨면서도 축 혼재는 그대로 남았을 것이다.
- **이번 세션에서 발견(§2.39)**: §2.38 이 만든 `unknown_status_items` 는 **payload 까지 오지
  않고 aggregate 안에만 있었다**. 테스트에서만 보이고 `state.json` 을 읽는 사람에게는 안
  보였다 — 노출을 만들었으면 **소비자가 실제로 보는 자리까지 왔는지** 확인할 것.
- **이전 세션의 교훈(§2.38)**: 증상은 "정렬이 시간순이 아니다" 한 줄이었는데, 열어 보니
  **정렬 키라는 것이 애초에 없었다**. 상한 `10` 이 두 곳에 있었고 자르는 방향이 반대라
  서로를 무효화했고, 완료 판정이 task 파일과 daily index 두 곳에 있어 파생물이 SSOT 를
  덮어썼다. **셋 다 각자의 자리에서는 말이 됐다** — §2.24/§2.37 과 같은 모양이다.
- **확인 못 함(§2.38)**: `_task_recency_key` 는 완료일이 아니라 **등록일 근사**다. 완료 시각
  필드가 표준이 아니라서, `completed_at`/`updated_at` 을 먼저 보게 해 두고 `created_at` 으로
  떨어진다. 같은 날 여러 건이 서로 다른 날 완료된 경우는 구분하지 못한다.
- **이전 세션의 교훈**: §2.35 (6) 에서 **관측하지 않은 값을 관측한 것처럼 적었다**. CI 의
  실패 사유가 어디에도 안 남아 있는 상태에서 로컬 출력을 CI 의 것으로 서술했고, 그래서
  원인을 mypy 로 잘못 지목했다. 실제 원인은 `gh` 인증 부재였다(§2.36). 처방이 맞았던 건
  운이다. **로컬 재현의 출력과 CI 의 출력은 다른 증거다.**
- **`gh` 인증 유무는 verdict 를 바꾸는 1급 환경 변수다** — CI 에서는 `skipped`, 로컬에서는
  `ci_sanity`/`ci_stale`. verdict 를 보는 검사는 전부 집합 검사 + 주입 검증이어야 한다.
- **도구 산출물은 diff 로 검토한다**(§2.37). stable 로 선언된 skill 이 상태 문서를 파괴하고
  있었고, `status: ok` 를 냈다. 발견 계기는 결과를 믿지 않고 `git diff` 를 읽은 것 하나다.
  close-out 에서 `backlog-update --apply` 를 쓴 뒤에는 반드시 diff 를 확인할 것.
- **확인 못 함**: 새로 생성한 진입점을 실제 에이전트 세션에서 로드해 보지는 않았다.
  파일 내용과 bootstrap 산출물, `check_self_application.py` 까지만 검증했다.
- **확인 못 함**: branch-scoped bootstrap 을 *기존 소비자 프로젝트* 에 재실행해 본 적은
  없다. 평면 layout 보존 분기는 temp fixture 로만 확인했다.
- **주요 제약**: 발표자료(`docs/presentations/`)의 11·12·15·22번 주장이 이제 사실이다.
  덱의 원리는 `core/workflow_design_principles.md` 가 정본이다.
