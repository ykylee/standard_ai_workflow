# Beta v1.9.4 (2026-09-07)

> **상태: 릴리스 준비.** package `1.9.4`, runtime `__version__ = 1.9.4`, tag `v1.9.4`.
> **patch release** — **매 세션 보고되던 지표가 사실은 고장 나 있었다.**
>
> 등급 근거 (§1.5): 공개 API 시그니처 변경 0 (기존 dataclass 에 **기본값 있는**
> 필드 하나 추가 — `SurprisingResult.total_items=0`) · 진입점 제거 0 · 산출물
> 형식 변경 0 (`graph_insights` 필드 구성·타입 불변, 값과 경고 **문구**만 바뀐다) ·
> 외부 spec 무관. 새 심볼 2종은 전부 순증이다.
> `wk release-status` 파생도 patch (breaking 0 / feat 0). 소유자 결정으로 이 값을 택했다.

## 0. 릴리스 판정

이 사이클의 주제는 **"경고가 100% 울리면 그것은 신호가 아니다"** 다.

`session-start` 와 `backlog-update` 는 매번 `health_score 0 / tier poor` 와
`scope creep 의심` 경고를 **완료 항목 전건**에 대해 냈다. 오탐이라고 보고 열었는데,
오탐이 아니었다 — **점수가 일한 것을 벌하고 있었다.**

    100 - uncovered*15 - scope_creep*10 + min(surprising*5, 25)

벌점은 항목 수에 비례해 무한히 커지는데 보너스는 25 에서 막힌다. goal 매칭 0 을
고정하고 완료 항목 수만 늘리면:

| 완료 항목 | raw score | tier |
|---|---|---|
| 0건 | 40 | fair |
| 3건 | 25 | poor |
| 10건 | **−35 → 0 으로 clamp** | poor |

표준이 recently-done 을 10건으로 상한하므로 **활발한 저장소는 영구히 바닥**이고,
보고되던 `0` 은 "나쁘다" 가 아니라 **clamp 자국**이었다.

**이 릴리스에 발행할 이유가 있다.** 고친 자리가 소비자의 매 세션 출력에 그대로
나가는 값과 문구다.

## 1. 릴리스 요약

- 범위: `v1.9.3..HEAD` (5 commit). 이 중 2건은 memory·세션 기록이고 1건
  (`9733d55e`)은 **v1.9.3 발행 마무리**가 태그 뒤에 착지한 것이라 실질 내용은
  2 commit 이다.
- 누적 smoke **284/284 PASS** (전량 2축 · FAIL 0, 좁은 선언 0), mypy strict
  0 errors (204 files)
- 검사 신설 2종 (`check_graph_insights_health_monotonic` 4 cases ·
  `check_mcp_emit_launcher_sweep` 3 cases)
- 지원 하네스 12 (변동 없음), MCP 표면 13 (변동 없음)
- 공개 API **+2 심볼**, 제거 0 —
  `common.purpose_graph.UNCLASSIFIED_WARNING_PREFIX` ·
  `common.purpose_graph.SurprisingResult.total_items`

## 2. 소비자 가시 변경

### 2.1 fix(graph-insights) — 점수가 완료한 일을 벌했다 (`878f0ae7`, main-010)

**이 릴리스의 중심이다.** 산식의 두 성분을 **비율**로 바꿨다:

    coverage 70 * covered/total_goals  +  classification 30 * (1 - 미분류/전체)

`SurprisingResult` 가 분모(`total_items`)를 **함께** 돌려준다 — 호출자가
`len(surprising)` 로 비율을 내면 분모가 분자와 같아져 늘 1.0 이 된다.

실측으로 고정한 성질: 비율이 같으면 규모 1~30배에서 점수 불변 · 분류된
deliverable 을 추가하는 것은 점수를 **절대** 내리지 못함 · 최악 입력 0 / 최선
입력 100 이고 clamp 에 닿는 입력 없음.

> **소비자 영향**: `graph_insights.health_score` / `health_tier` 의 **값이 바뀐다.**
> 필드 구성과 타입은 그대로다. 옛 값을 기준선으로 삼아 둔 대시보드가 있다면
> 한 번 다시 재야 한다.

### 2.2 fix(graph-insights) — 정반대 술어가 같은 경고 접두사를 썼다 (`878f0ae7`)

`purpose_context.check_scope_creep` 은 §3 제외 영역에 **걸리면** scope creep 이라
하고, `purpose_graph.find_surprising_deliverables` 는 **안 걸리면** 그렇다 했다.
술어가 정반대인데 두 경고 모두 `"scope creep 의심:"` 으로 시작했고, 출력에서는
`scope_creep_warnings` 라는 **같은 이름의 두 필드**(top-level /
`graph_insights.`)로 나갔다 — 읽는 쪽이 어느 규칙이 울렸는지 구분할 수 없었다.

정본 상수 `UNCLASSIFIED_WARNING_PREFIX = "미분류 산출물:"` 로 갈랐다.

> **소비자 영향**: `graph_insights.scope_creep_warnings` 의 **문구가 바뀐다.**
> 그 문자열의 접두사를 파싱하던 소비자는 갱신이 필요하다. 필드 이름은 그대로
> 두었다 — 개명은 공개 schema 라 deprecation 사이클을 탄다(§4 참조).

### 2.3 fix(graph-insights) — 현재 표준 형식(`TASK-`)을 못 읽었다 (`878f0ae7`)

파서가 v0.9.4 시절 `vX.Y.Z (hash): 설명` 만 알았다. 표준이 recently-done 항목을
`TASK-` 로 시작하게 바꾼 뒤라, 살아 있는 항목이 **전부** `version="unknown"` 으로
떨어지고 모든 항목이 공유하는 `task` / `2026` / `09` / `main` 이 키워드 집합에
섞였다 — 어휘 겹침을 재는 자리에 순수한 잡음이다.

문법은 정본 `project_docs.TASK_ID_PATTERN` 에서 **파생**한다(복제하면 갈라진다).
legacy 형식은 계속 받는다.

### 2.4 docs — 이 지표가 무엇을 재는지 주장을 좁혔다 (`878f0ae7`)

매칭이 **구조적으로** 성립하지 않는다는 것을 실측했다. Goals 는 지향 문장이고
deliverable 은 결함 수리 제목이라 어휘가 겹칠 이유가 없다 — goal 4개 전부 공집합.
한국어 조사 가설을 세워 조사를 제거하고 재측정했지만 **여전히 공집합**이었고,
부분문자열 포함까지 완화해도 회수되는 것은 `ai` 와 `처럼` 둘뿐이다.
**토크나이저를 개선해도 열리지 않는 자리다** — 임계값만 옮긴다.

그래서 정교화하는 대신 module 과 두 schema docstring 에 적었다: 이것이 재는 것은
**어휘 겹침**이지 건강도가 아니고, 낮은 값은 "어휘가 겹치지 않는다" 로 읽으며,
어떤 skill·harness 지시문도 이것을 소비하지 않으므로 **자동 판정의 근거로 쓰지
않는다**.

### 2.5 fix(tests) — 오류 메시지가 엉뚱한 산출물을 지목했다 (`878f0ae7`)

`check_state_json_generated` case 5 가 실패할 때 늘 "state.json 이 갈라졌다 —
`wk refresh-state` 로 재생성하라" 고 적었다. 그런데 `refresh-state --check` 는
`state.json` **또는** `roadmap_state.json` 중 하나만 갈라져도 rc=1 이다.

실제로 이번 사이클에 그 상황이 왔다: `drift=false` · `drifted_keys=[]` ·
`roadmap_drift=true`. 메시지대로 따랐다면 **멀쩡한 state.json 을 다시 쓰면서 진짜
원인을 지나쳤을 것이다.** 이제 payload 를 읽고 범인을 말한다.

## 3. 판정 (회귀 방지)

- **`check_graph_insights_health_monotonic` 신설 (4 cases)** — 단조성(비율 고정 시
  규모 불변 · 분류된 일 추가가 점수를 안 내림 · clamp 자국 없음) · 두 경고 접두사
  분리 · fixture 가 goal 문자열의 복사가 아님 · `TASK-` 인식과 ID 토큰 누출 0.
- **`check_mcp_emit_launcher_sweep` 신설 (3 cases)** — emit 되는 MCP command 가
  **전 렌더러에서** 플랫폼 관례를 따르는지 산출물 수준에서 훑는다.
  (`TASK-2026-08-25-main-017` 의 판정 공백. 기존 검사는 정본 함수를 *직접* 부를
  뿐이라, 새 렌더러가 command 를 손으로 적어도 red 가 되지 않았다.)

> **좋은 점수를 내던 유일한 fixture 가 항등식을 재고 있었다.** goal 문자열을
> deliverable 문자열에 **그대로 복사**해 두어 coverage 100% 가 나왔다. 실제 작업
> 제목은 goal 의 재진술이 아니므로 그 case 는 아무것도 재지 않았다. 13자리를 현재
> 형식 + 복사 아닌 문장으로 교체했다. **결함이 어려웠던 게 아니라 재는 자리가
> 없었다** — v1.9.3 사이클의 `examples/` 와 같은 모양이다.

되주입 실증은 **7종**이고 전부 의도한 case 에서 red 였다. 그중 하나는 검사가
조용히 통과할 뻔한 자리를 드러냈다: `opencode` 는 MCP command 가 문자열이 아니라
**리스트**라 문자열 전용 추출이 0건을 반환했고, 그 0건은 **위반 0건과 구분되지
않았다.** 추출을 두 형태 모두 받게 고치고, 렌더러마다 최소 1건을 찾았는지를
검사 자체에 넣었다 — 모름을 통과로 세지 않는다.

## 4. 남은 리스크

- **이 저장소에서 지표는 여전히 0 을 낸다.** 그것은 이제 clamp 자국이 아니라
  **정직한 읽기**다 (coverage 0 + 전량 미분류). 어휘 겹침이라는 근거 자체를
  바꾸려면 — 예컨대 task 의 WBS·로드맵 링크를 쓰거나 goal 을 task 에 명시
  선언하게 하려면 — ADR 이 필요하고, 이번 범위 밖으로 남겼다.
- `graph_insights.scope_creep_warnings` 는 **이름과 내용이 어긋난 채로 남는다** —
  이름은 scope creep 인데 담기는 것은 미분류다. 개명은 공개 schema 라
  deprecation 사이클(§ G3/G4 보증) 후보로 남겼다.
- `check_mcp_emit_launcher_sweep` 은 emit 된 command 의 **이름**만 잰다. 그 이름이
  Windows PATH 에 실재해 spawn 되는지는 이 축으로 못 본다 —
  `TASK-2026-08-25-main-017` 의 완료 기준 2 가 아직 열려 있는 이유다.

## 5. 업그레이드

소비자 채널은 재적용이 필요하다 (`INSTALLATION_AND_USAGE §7.0.2` 의 복구 열).
`graph_insights` 를 읽던 소비자는 **값과 경고 문구가 바뀐다** — 필드 구성과 타입은
그대로이므로 읽기 자체는 깨지지 않는다.

## Reference

- 이전 release note: `Beta-v1.9.3.md`
- task: `TASK-2026-09-07-main-009` · `main-010` · `TASK-2026-08-25-main-017`(진행 중)
- 정본 문서: `docs/RELEASE.md` §1.5 (등급 판단) ·
  `workflow_kit/common/purpose_graph.py` (지표 해석)

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-09-07T06:05:39Z)_

- total wiki pages: **95**
- total memory entries: **15**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
