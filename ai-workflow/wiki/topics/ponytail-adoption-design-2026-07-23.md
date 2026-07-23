---
type: topic
status: active
last_ingested_from: https://github.com/DietrichGebert/ponytail + https://blog.scottlogic.com/2026/06/16/ponytail-yagni-and-the-problem-with-prompt-benchmarks.html + workflow-source/releases/Beta-v1.0.0.md §2.19~§2.26
related_pages: [topics/workflow-audit-2026-07-09, topics/quality-dashboard-implementation-guide, topics/phase-13-definition-north-star, topics/harness-distribution-model]
created: 2026-07-23
updated: 2026-07-23
---

# Ponytail 개념 조사와 채택 설계 (2026-07-23)

## TL;DR

외부 스킬 [ponytail](https://github.com/DietrichGebert/ponytail) ("가장 게으른 시니어 개발자처럼
생각하게 만든다") 을 조사하고, 우리 워크플로우에 채택할 부분을 가렸다. **절반 이상은 이미 우리에게
있고 몇 개는 우리가 더 낫다.** 진짜로 없는 것은 두 가지 — **효율 사다리**와 **유보 마커 + 수확
원장** — 이며 이 둘만 채택한다. 헤드라인 지표(코드량 -54%)는 채택하지 않는다.

가장 큰 수확은 기능이 아니라 **비판**이었다. ponytail 의 54% 를 무너뜨린 것은 아이디어가 아니라
판정식이었고 — 비교군이 구조적으로 불리해 지표가 한 방향으로만 움직일 수 있었다 — 그것은 같은
날 우리가 `drift_ledger` 에서 찾은 결함(§2.26, 분자가 도달 불가)과 **같은 부류**다.

## 1. 조사 대상

| 항목 | 내용 |
|---|---|
| 대상 | ponytail (DietrichGebert/ponytail) |
| 핵심 주장 | 코드량 -54% (최대 -94%), 토큰 -22%, 비용 -20%, 시간 -27%, 안전성 100% |
| 실체 | 핵심 룰셋은 `AGENTS.md` 약 100줄 마크다운 + 하네스별 사본 + 6개 슬래시 커맨드 |
| 조사일 | 2026-07-23 |

### 1.1 효율 사다리 (핵심 개념)

코드를 쓰기 전에 **먼저 걸리는 단에서 멈춘다**:

1. 애초에 만들어야 하나? (YAGNI) → 안 만든다
2. 이 코드베이스에 이미 있나? → 재사용
3. stdlib 이 하나? → 표준 라이브러리
4. 네이티브 기능이 있나? → 그걸 쓴다
5. 설치된 의존성이 있나? → 그걸 쓴다
6. 한 줄로 되나? → 한 줄
7. 그제서야 최소 동작 코드

> **"해법에 게으르되, 읽는 데는 절대 게으르지 않다."** 사다리를 타기 전에 건드리는 코드의
> 실제 흐름을 먼저 읽는다.

**사다리 대상이 아닌 것** (양보 불가): 신뢰 경계 검증 / 데이터 손실 방지 / 보안 / 접근성 /
명시적으로 요청된 기능 / 비자명 로직의 테스트.

의도적으로 자른 구석은 `ponytail:` 주석으로 **한계와 승급 경로를 함께** 표시하고,
`/ponytail-debt` 가 그것을 수확한다.

## 2. 비판 — 채택 판단의 근거

### 2.1 Scott Logic: 헤드라인 지표가 성립하지 않는다

- **베이스라인이 불공정하다.** 비교군은 여러 대안과 설명을 함께 내놓게 두고 LOC 를 셌다.
  제대로 설정된 에이전트는 단일 해법만 낸다. 차이의 상당 부분이 여기서 나온다.
- **7단어로 재현된다.** 베이스라인 프롬프트에 `Follow YAGNI principles, and one-liner solutions`
  만 붙여 **6.9줄 vs ponytail 8.25줄** — 프레임워크를 자기 벤치마크에서 이겼다.
- **테스트 설계 결함.** debounce 과제는 DOM 존재를 가정해 전 케이스에서 실패했다.

### 2.2 dev.to: 남은 구멍 둘

- **성숙한 프로젝트에서 미검증.** 벤치마크가 컴포넌트 라이브러리가 **없는** FastAPI 템플릿에서
  돌았다. 가장 화려한 승리(date picker 404→23줄)는 네이티브 요소 선택에서 나왔는데, shadcn/MUI 가
  이미 깔린 저장소에서는 사다리 5단(설치된 의존성)이 4단(네이티브)보다 위라 결과가 뒤집힌다.
- **유보한 부채가 실제로 수확되는지 아무도 답하지 않았다.** 시간이 지나며 LOC 감소가 유지되는지,
  유지보수 국면에서 어떻게 되는지는 열린 문제다.

### 2.3 우리에게 주는 의미

ponytail 에는 §2.23 이 만든 **근거 계약**(`*_source` / `*_measured`)에 해당하는 장치가 없다.
그래서 숫자가 "누가 재현해볼 때까지" 살아남았다. 우리가 채택할 때는 **효과를 수치로 주장하지
않는다** — 공정한 베이스라인이 없기 때문이다.

## 3. 우리 자산과의 대조 — ponytail 자신의 사다리로 판정

| ponytail 요소 | 우리 자산 | 판정 |
|---|---|---|
| 15+ 하네스 룰 배포 | `HARNESS_SPECS` + `renderers.py`, 11 하네스 | **이미 있음** (bootstrap 자동 emit) |
| `check-rule-copies.js` (사본 정렬 검사) | `check_convention_single_source.py` (§2.24) | **이미 있음, 더 강함** — 텍스트 비교가 아니라 "정본 모듈이거나 정본 symbol 을 import 하거나" |
| `/ponytail-review` (diff 과잉 검사) | `/simplify`, `/code-review` (하네스 제공) | **이미 있음** |
| `/ponytail-gain` (지표 scoreboard) | quality dashboard 8 panel | **이미 있음** (릴리스 시점 emit) |
| `lite/full/ultra` 강도 dial | `MODE_GUIDELINES` (단계 mode) | **축이 다름** — 우리 건 단계, 저건 강도 |
| **효율 사다리** | 14개 skill 중 해당 없음 | **없음 → 채택 (A)** |
| **유보 마커 + 수확 원장** | `drift_ledger` 는 릴리스 drift 전용 | **없음 → 채택 (B)** |
| 54% 벤치마크 | — | **채택 불가** |

## 4. 설계 A — 효율 사다리를 `MODE_GUIDELINES` 한 줄로

### 4.1 자리와 근거

`workflow_kit/common/modes/registry.py` 에 `EFFICIENCY_LADDER` 상수를 신설하고
`Implementation` / `Refactoring` 두 mode 의 guideline 에 추가한다. 소비자는 이미 있다 —
`session_outputs.build_session_summary` → session-start.

**왜 새 skill 이 아닌가**: 사다리 2단("이미 있나?")을 채택 결정 자체에 적용한 결과다.
mode registry 가 있고 session-start 가 이미 표면화한다. ponytail 처럼 15개 하네스에 배포하는
방식은 우리 경우 **사본 위험만 늘린다** — 하네스 overlay 배포는 하지 않는다.

### 4.2 설계상 함정 — `summary[:8]`

`build_session_summary` 는 마지막에 `return summary[:8]` 로 자른다. mode guideline 이 늘면
8칸을 두고 baseline / axis / 진행중 건수 / 제약과 경쟁한다.
**레지스트리에 넣었다고 화면에 나온다는 보장이 없다.**

→ 검증은 "상수가 등록됐나" 가 아니라 **"실제 세션 요약 산출물에 살아남아 나오는가"** 로 잡는다.
§2.26 에서 얻은 도달 가능성 검사를 그대로 적용한 것이다.

### 4.3 측정하지 않는 것

**효과를 수치로 주장하지 않는다.** §2.1 의 재현 사례가 있으므로 %를 주장하려면 공정한 대조군이
필요한데 우리에겐 없다. 무엇을 왜 측정하지 않는지를 릴리스 노트에 명시한다 — 근거 없는 숫자를
만들지 않는 것이 §2.23 의 정신이다.

## 5. 설계 B — 유보 마커 + 수확 원장

### 5.1 마커 문법 — 필드를 강제한다

```
# DEFER: <요약> | ceiling=<어디까지 동작하나> | upgrade=<언제 무엇을 하나>
```

토큰은 grep 안정성을 위해 **ASCII `DEFER:`** 로 고정한다 (본문은 한국어).

ponytail 은 "한계와 승급 경로를 함께 적으라" 고 말만 하고 강제 장치가 없다 — §2.2 가 지적한
구멍이 정확히 거기다. **`ceiling` / `upgrade` 누락은 lint FAIL** 로 막는다. 강제하지 않으면
그냥 TODO 가 되고, TODO 는 아무도 갚지 않는다.

기존 `# TODO` 는 production 에 **2건**뿐이다 (`workflow_kit/common/scaffold.py`,
`skills/automated-repro-scaffold/scripts/run_automated_repro_scaffold.py`). 둘 다 "미구현" 이라
DEFER 대상이다 → 병행 시스템을 만들지 말고 흡수한다.

### 5.2 `upgrade` 를 기계가 볼 수 있게

```
upgrade=version:v1.1.0     ← 판정 가능
upgrade=cycles:3           ← 판정 가능 (3 릴리스 사이클 후 재검토)
upgrade=when:<자유 텍스트>  ← escape hatch, 판정 불가
```

`when:` 을 허용하되 **몇 건이 판정 불가인지 근거로 함께 낸다**. 조용히 빠져나가는 경로를
만들지 않는 것이 §2.24 방식이다.

### 5.3 지표가 한 방향으로만 못 움직이게 — 가장 중요한 논점

순진하게 `open_defer_count` 를 지표로 삼으면 **마커를 안 다는 것이 최적 전략**이 된다.
0 이 좋아 보이면 아무도 안 단다. 이것은 §2.26 에서 잡은 결함과 정확히 같은 부류다 —
판정식이 한 방향으로만 움직인다.

| | 설계 |
|---|---|
| **지표** | `overdue_defer_count` = 승급 조건이 **이미 지났는데** 안 갚은 마커 수 |
| 마커를 안 달면 | `0` 이 아니라 **`미측정`** (원장이 비었음 — `drift_ledger` 와 같은 규칙) |
| 제때 갚으면 | 0 |
| 안 갚으면 | 오른다 |
| `open_defer_count` | 지표 아님. **근거 field** 로만 emit |
| 판정 불가(`when:`) 건수 | 근거 field 로 함께 emit |

`JUDGMENT_METRICS` 에 `(panel, metric, source, measured)` 로 등록하면
`check_metric_source_contract.py` 가 자동으로 강제한다.

### 5.4 수확 경로가 실제로 도달 가능한가

§2.2 의 미해결 질문("유보한 부채가 실제로 수확되는가")과 §2.26 에서 찾은 결함이 같은 모양이다.
그래서 **처음부터** 세 층으로 단다:

| 층 | 언제 도는가 | 무엇을 막나 |
|---|---|---|
| `check_defer_marker_contract.py` | 매 push | 마커 문법 붕괴 |
| release cycle 당 원장 1 line | 릴리스마다 | 분모 (안 쟀다 ≠ 0건) |
| **orchestrator 도달 가능성 테스트** | 매 push | `overdue ≥ 1` 인 상태를 만들어 그 line 이 실제로 생기는지 |

세 번째가 §2.26 에서 배운 것이다. **writer ↔ reader 가 맞물리는 것만으로는 부족하다.**

원장 writer 는 `_self_recover_step` 옆, **판정이 확정되는 지점**에 둔다 (§2.26 에서 고친 자리와
같은 원칙 — `gh release create` 뒤에 두면 early return 하는 cycle 이 통째로 빠진다).

### 5.5 규약 단일 출처 등록을 첫날에

`DEFER_MARKER_RE` / `DEFER_LEDGER_RELPATH` 를 `CONVENTIONS` 에 5·6번째 규약으로 등록한다.
§2.24 는 "전수 조사 후 등록" 을 전제하는데, 신규라 **조사할 사본이 0 인 지금이 가장 싼 순간**이다.
나중에는 반드시 비싸다.

### 5.6 Panel

9번째 panel 신설이 필요하고 `check_phase15_dashboard_panels.py` 의 `expected_panels` 갱신
대상이다. 다만 그 테스트가 현재 HEAD 에서 이미 red 라 **선행 조사(단계 0.5)에 의존**한다 —
남의 red 위에 쌓지 않는다.

## 6. 단계 계획

| # | 단계 | 산출물 | 게이트 |
|---|---|---|---|
| 0 | `drift_ledger` 마무리 (§2.26) | 노트 누적 수치 정합, 커밋 | 정본 러너 전량 green |
| 0.5 ✅ | **선행 조사**: HEAD 기존 red 5건 | → §6.1 (해소 완료) | 노트 "209/209" 가 사실인지 판정 |
| A1 | 효율 사다리 | `EFFICIENCY_LADDER` + wiring smoke | `summary[:8]` 절단 뒤에도 나오는지 |
| B1 | 마커 문법 + lint | `defer_ledger.py` 정본, `check_defer_marker_contract.py`, 기존 TODO 2건 이관 | 되돌려 주입 FAIL 확인 |
| B2 | 규약 등록 | `CONVENTIONS` 5·6번째 | 사본 0 확인 |
| B3 | 원장 + 도달 가능성 | writer 배선 + orchestrator 테스트 | `overdue ≥ 1` line 이 실제로 생기는지 |
| B4 | Panel 9 + 지표 | `JUDGMENT_METRICS` 등록 | 단계 0.5 결과에 의존 |

**결정 (2026-07-23)**: B1~B3 을 한 사이클로 진행하고 B4 는 그 뒤. 단계 0.5 를 먼저 본다.
마커 토큰은 ASCII.

### 6.1 단계 0.5 결과 — 전량 smoke 라는 최상위 지표가 재현 불가능했다

조사 결과 5건 전부 **테스트가 실행 환경에 누적된 상태에 의존**하고 있었다. 깨끗한 워크트리에서
정본 러너로 돌려도 같은 5건이 실패했고, GitHub Actions smoke 는 **최근 40회 전량 failure**
(성공 기록 없음). "전량 209/209" 를 적은 커밋들의 CI 가 전부 red 였다.

이것이 §2 의 ponytail 비판과 **같은 형태**라는 점이 중요하다. Scott Logic 이 무너뜨린 것은
아이디어가 아니라 *재현 불가능한 조건에서 잰 수치* 였다. 우리 저장소는 §2.19~§2.24 동안
"지표가 무엇을 재고 있는가" 를 고쳐 왔는데, 정작 **최상위 지표(전량 smoke)가 작성자
워킹카피에서만 성립**하고 있었다.

조치는 릴리스 노트 §2.27 에 기록. 요점 셋:

- **skip 이 아니라 fixture 로 고쳤다.** 없는 파일에 skip 을 주면 CI 에서 항상 skip 되고,
  그건 red 보다 나쁘다 — 도는 척하며 초록으로 보인다.
- fixture 는 손으로 쓰지 않고 **프로덕션 writer 로** 만든다 (§2.22 와 같은 이유).
- 곁들여 정본 helper 결함을 찾았다 — `state_path_for_workspace(workspace_root)` 가 접두는
  인자에서, **branch 는 모듈이 속한 저장소에서** 가져와 *호출 위치가 답을 바꾸고* 있었다.
  `branch_for_workspace()` 신설로 해소.

**앞으로 전량 수치를 적을 때는 어디서 쟀는지를 함께 적는다.**

이 원칙은 채택안 A 의 "효과를 측정하지 않는다"(§4.3) 와 짝을 이룬다 — 잴 수 없으면 안 적고,
적을 거면 재현 조건을 함께 적는다.

## 7. 채택하지 않는 것

- **gain / 벤치마크 수치** — 베이스라인이 불공정하고 7단어로 재현된다 (§2.1).
- **플러그인 마켓플레이스 패키징** — 우리는 bootstrap emit 이 정본이다.
- **하네스 15종 룰 사본 배포** — 사본 위험을 늘린다. 필요해지면 정본 상수에서 렌더한다.
- **`lite/full/ultra` 강도 dial** — 우리 mode 는 단계 축이라 성격이 다르다. 강도가 필요해지면
  그때 별도 축으로 설계한다.

## 8. 참고

- [GitHub — DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)
- [Ponytail? YAGNI! — Scott Logic (2026-06-16)](https://blog.scottlogic.com/2026/06/16/ponytail-yagni-and-the-problem-with-prompt-benchmarks.html)
- [dev.to — the one question nobody's answered yet](https://dev.to/yashddesai/ponytail-the-ai-coding-skill-taking-github-by-storm-and-the-one-question-nobodys-answered-yet-46mc)
- 릴리스 노트 `workflow-source/releases/Beta-v1.0.0.md` §2.19 / §2.22 / §2.23 / §2.24 / §2.26
