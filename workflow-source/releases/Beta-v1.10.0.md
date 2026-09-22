# Beta v1.10.0 (2026-09-22)

> **상태: 릴리스 준비.** package `1.10.0`, runtime `__version__ = 1.10.0`, tag `v1.10.0`.
> **minor release** — **게이트가 무엇을 재고 있었는지 다섯 번 뒤집은 사이클.**
>
> 등급 근거 (§1.5): 공개 Python API 시그니처 변경 **0** (새 심볼 전부 순증 —
> `python_floor.iter_sources` · `resolve_scope` · `packaged_declaration`,
> `check_warnings.sweep_compile` · `gated_only` · `SweepResult`) · 진입점 제거 **0** ·
> 산출물 형식 **후방 호환** (`graph_insights` 출력 키 제거 0 / 추가 3 —
> `coverage_mode_undeclared` · `covered_goals` · `total_goals`. v1.9.4 소비자가
> 읽던 키는 전부 남아 있다) · 외부 spec 무관.
> `wk release-status` 파생도 minor (breaking 0 / feat 6 / fix 5 / other 17, total 28).

## 0. 릴리스 판정

이 사이클의 주제는 **"green 은 판정이 살아 있다는 증거가 아니다"** 다.

다섯 개의 축이 전부 같은 모양으로 고장나 있었고, 전부 **아무 검사도 실패하지 않은 채로**
그랬다.

| 축 | 무엇을 재고 있었나 | 무엇을 재야 했나 |
|---|---|---|
| goal coverage | 어휘 겹침 (실측 4/4 goal 전부 **정확히 0**) | 선언 사슬 `task.wbs → milestone → PURPOSE §1` |
| smoke 수 주장 | 손으로 고른 문서 2곳 | git 추적 md **전수** |
| Python 문법 하한 | 아무것도 (`ast.parse` 가 PEP 701 을 통과시킨다) | 실물 3.10 해석기 |
| 검사를 도는 해석기 | 개발자 `.venv` 에 우연히 깔린 3.13 | 선언 registry → CI 4셀 |
| 컴파일 시점 경고 | `__pycache__` 상태 | 소스 전수 메모리 `compile()` |

마지막 줄이 가장 고약했다. **소스를 그대로 둔 채 게이트를 두 번 돌리면 1차 `exit 1` /
2차 `exit 0`** 이었다 — 고친 것 없이 재실행만으로 green 이 되는 게이트다.

**이 릴리스에 발행할 이유가 있다.** 고친 자리 중 둘(`graph_insights` 판정, `wk
backlog-update` 의 필수 인자)이 소비자의 매 세션 출력과 호출에 그대로 나간다.

## 1. 릴리스 요약

- 범위: `v1.9.4..HEAD` (28 commit). 이 중 14건은 memory·backlog·환경 기록이고 1건
  (`0facde38`)은 **v1.9.4 발행 마무리**가 태그 뒤에 착지한 것이라 실질 내용은
  **13 commit** 이다.
- 누적 smoke **290/290 PASS** (브랜치 2 × 해석기 2 = **4셀** 전량 · FAIL 0,
  좁은 선언 0), mypy strict 0 errors
- 검사 **284 → 290** (신설 6 · 제거 0 · 보강 다수), 되주입 실증 **누적 53종**
  (세션 기록 합산: 80차 3 · 81차 23 · 82차 17 · 83차 10)
- CI smoke 가 1셀 → **4셀** (native/slash × py3.11/py3.13)

## 2. 소비자 가시 변경

### 2.1 fix(metrics) — goal coverage 가 어휘를 재고 있었다 (`c08dfebd`, main-001)

4개 goal 전부 완료 항목과의 겹침이 **정확히 0** (0/13 · 0/14 · 0/12 · 0/15)이었다.
조사 제거·CJK bigram 두 대안 토크나이저로 다시 재도 최대 0.07 이고, 그 유일한 겹침은
기능어 `처럼` 이었다. **원인은 토크나이저도 임계도 아니라 입력 쌍이다** — Goals 는
전략 산문이고 완료 항목은 결함수리 제목이라, 애초에 비교 가능한 종류가 아니었다.

판정을 선언 사슬(`task.wbs → milestone.wbs_goals/goals → PURPOSE §1`)로 갈았다.
저장소 실측 **0.0/poor → 75.0/excellent**, 미분류 10 → 0.

**소비자 영향**: `graph_insights` 의 값이 크게 바뀐다. 키는 제거 없이 3개 순증이므로
읽기는 깨지지 않는다. 못 잰 것은 `undeclared`/`unmeasured` 로 나오고 `provenance` 가
무엇을 채우면 닿는지 적는다.

### 2.2 fix(backlog-update) — 뜻이 갈리는 필수 인자가 진행 기록을 덮었다 (`371afdbf`)

`--task-brief` 는 create 에서는 `작업 내용`, update 에서는 `진행 현황` 이라 의미가
모드마다 다른데 **양쪽에서 필수**였다. 그래서 상태만 바꾸려는 호출이 기존 진행 기록을
덮어썼다. update 에서 선택 인자로 내렸다 — 생략하면 기존 값을 보존한다.

### 2.3 fix(backlog-update) — `--apply` 가 형제 생성물을 두고 갔다 (`cc172d6c`, main-004)

`state.json` 은 재생성하면서 `roadmap_state.json` 은 두고 갔다. 그 SSOT 가 *방금
자기가 쓴* task frontmatter 인데도 그랬고, 뒤처짐은 경고 없이 push 게이트에서야
드러났다. 같은 호출에서 같이 재생성한다.

### 2.4 fix(doctor) — `content_drift` 가 아무도 안 읽는 사본을 재고 있었다 (`3d5c7830`)

마켓플레이스 소스가 `directory` 면 서빙 경로는 저장소 워킹 트리인데, 탐침은 캐시
사본을 대조하고 있었다. 두 사본이 byte 동일이라 **파일 비교로는 원리적으로 못 가르는**
자리였고 캐시에 마커를 심어 확정했다. 이제 소스 유형을 읽어 서빙 경로를 대조하고,
읽히지 않는 사본은 `served=false` 로 `unserved` 에 남긴다.

### 2.5 fix(docs) — smoke 수 주장이 8곳 중 2곳만 게이트됐다 (`d882b42a`, main-004)

목록 밖은 조용히 갈라져 있었다 — README 162 · roadmap 52 · `.omo` 52, 실제 285.
수가 짐을 지지 않는 자리에서는 수를 뺐고, 남긴 자리는 git 추적 md **1321건 전수**를
훑는 검사가 덮는다.

## 3. 판정 (회귀 방지)

신설 6종:

- **`check_requirement_declarations`** — `ENFORCES` 선언 축. 검사의 `§` 산문 인용
  **671건 / 127파일** 중 기계가 문서를 특정할 수 있는 것이 **10건** 뿐이라, 끊긴
  링크가 아니라 *링크가 아닌 것* 이 본체였다 (OpenSpec 도구 채택은 기각, concept 만 흡수).
- **`check_smoke_count_claims`** — git 추적 md 전수. 동결 문서는 이름이 아니라
  **문맥 두 신호**로 파생한다.
- **`check_python_floor_syntax`** — 선언 하한을 **실물 해석기**로 잰다.
  `ast.parse(feature_version=)` 은 PEP 701(중첩 f-string)을 통과시킨다 — 이 축을
  만들게 한 바로 그 결함이다.
- **`check_interpreter_matrix`** — 검사를 도는 해석기를 선언으로. CI smoke 가 4셀.
- **`check_warning_gate`** — 저장소 코드가 낸 Python 경고는 `exit 0` 이어도 red.
- **`check_source_compile_warnings`** — 컴파일 시점 경고를 **캐시와 무관하게**.

> **세 번 연속 같은 모양이었다: 범위가 손 목록이면 그 밖이 갈라진다.** smoke 수 ·
> 해석기 · 컴파일 범위 모두 포함 목록으로 시작했다가 **파생**으로 갈았다. 특히
> 해석기 축에서는 '민감한 검사 목록' 을 선언하자는 설계를 **실측으로 기각**했다 —
> 민감한 쪽이 *저장소 소스를 파싱하는 검사* 라 미리 목록화할 수 없다.

> **우연한 커버리지는 선언이 아니다.** CI 는 검사를 3.11 하나로만 돌았고 3.13 은
> 개발자 `.venv` 에 깔린 것이었다. `.venv` 를 3.11 로 다시 만들면 그 커버리지는
> **조용히 사라지고 아무 검사도 실패하지 않는다.** 그리고 그 축은 가정이 아니라 이미
> 열려 있었다 — 3.12+ 에서만 나는 `SyntaxWarning: invalid escape sequence` 를 5개
> 검사가 3.13 에서만 보고 **3.11(CI)은 완전히 침묵**했다.

되주입 실증은 이 사이클 누적 **53종**이고 전부 의도한 case 에서 red 였다. 그 되주입이
잡은 것 중 넷은 **검사 자신의 결함**이다:

- 표본에 판별 토큰이 없어 **요구를 지워도 통과**하던 case
- 저장소에 해당 상태가 0 이라 **발화 불가능** 하던 case (수집을 지워도 green)
- 경고 범주를 하드코딩해 **3.11 셀에서만 red** 이던 case (invalid escape 는 3.12+ 에서
  `SyntaxWarning`, 3.11 이하에서 `DeprecationWarning` — 판정이 해석기에 달렸다)
- 되주입 harness 자신이 `.pyc` 재사용으로 **다른 case 의 증상**을 낸 것

## 4. 남은 리스크

- **CI 의 Python 하한은 부분 측정이다.** CI 에 `uv` 도 `python3.10` 도 없어
  `feature_version` 으로 내려가고 **PEP 701 부류를 못 본다**. 검사가 그 사실을
  `[unmeasured]` 두 줄로 출력한다. 전수로 올리려면 `smoke.yml` 에 한 단계가 필요한데
  2026-09-21 소유자 지시로 **올리지 않았다**.
- **`ENFORCES` 미선언 282/290 은 의도된 관찰 지표다.** 전수 강제하면 선언의 품질이
  아니라 개수만 는다 — 정본 스펙 §7.1 에 근거가 있다.
- **G4 가 uncovered 인 것은 실측 결과이지 결함이 아니다.** `WBS-7.4` 에 G4 를 얹으면
  coverage 가 100% 상수가 되므로 일부러 얹지 않았다.
- **`consumer-metrics-digest` 가 8월부터 만성 red 다** (`TASK-2026-09-22-main-001`).
  `REQUIRED_CI_WORKFLOWS` 가 아니라 이 발행을 막지 않지만, 주간 cron 실패가 어디에도
  신호로 안 뜬 채 8회 중 7회 실패했다.
- **`scope_creep_warnings` 는 이름과 내용이 어긋난 채로 남는다** (v1.9.4 에서 이월).

## 5. 업그레이드

소비자 채널은 재적용이 필요하다 (`INSTALLATION_AND_USAGE §7.0.2` 의 복구 열).
`graph_insights` 를 읽던 소비자는 **값이 크게 바뀐다** — 키 제거가 없고 3개가 순증이므로
읽기 자체는 깨지지 않는다. `wk backlog-update --task-brief` 를 update 에서 넘기던
호출은 그대로 동작한다 (필수 → 선택은 후방 호환).

## Reference

- 이전 release note: `Beta-v1.9.4.md`
- task: `TASK-2026-09-21-main-001` ~ `main-009` · `TASK-2026-09-18-main-004` ~ `main-006` ·
  `TASK-2026-09-22-main-001`(열림)
- 정본 문서: `docs/RELEASE.md` §1.5 (등급 판단) ·
  `workflow-source/core/test_impact_tiering_spec.md` §7 (`ENFORCES` · 요구 선언) ·
  `workflow_kit/common/interpreter_matrix.py` (해석기 registry) ·
  `workflow_kit/common/check_warnings.py` (경고 게이트)

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-09-22T02:30:34Z)_

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
