# html-plan 개념 흡수 — concept 검토

- 문서 목적: Anthropic 커뮤니티 플러그인 `html-plan` 의 개념(주장 트리 · 결정 배치 · 응답 왕복)을 실측하고, task 파일 Plan 계약 흡수(안 A)와 html-plan 검토 브리지(안 B)의 설계 초안과 소유자 선택지를 판단 가능한 형태로 정리한다 (TASK-2026-11-12-claude-remote-sync-check-234c32-002, M-022/WBS-22.1).
- 범위: html-plan 1.0.0 의 구성 · 규칙 · pack 린트 · Respond 응답 형식, 현 task `## 🧭 Plan` 계약과의 대조, A(필드 · 린트 · 게이트 · verifier) 와 B(`plan-export` · `plan-import`) 설계 초안, 정본 · 파생 영향
- 대상 독자: 소유자 (M-022 다음 단계 결정), maintainer
- 상태: **종결 (2026-11-12)** — 소유자 결정 = §7 기본값 D1~D5 전부 (§10). **안 B 는 하네스 중립 제약으로 정정 (§11, W5 로 확정)**. requirements 는 M-023
- 최종 수정일: 2026-11-12
- 관련 문서: [`M-022`](../../ai-workflow/memory/active/roadmap/M-022-claim-plan.md), [`ai-native-sdlc-playbook-review-2026-10.md`](./ai-native-sdlc-playbook-review-2026-10.md) (`## 🧭 Plan` 절과 verifier 를 낳은 선행 concept), [`compact-relay-review-2026-09.md`](./compact-relay-review-2026-09.md) (같은 형식의 선행 concept), [`project_docs.py`](../../workflow-source/workflow_kit/common/project_docs.py) (task 라벨 정본), [`backlog_update.py`](../../workflow-source/workflow_kit/tools/backlog_update.py) (Plan 쓰기 · 게이트)

## 0. 한 줄 결론

> html-plan 의 핵심은 HTML 이 아니라 **계획의 문법**이다 — 계획을 *참·거짓을 가를 수 있는 동작 주장*의
> 트리로 쓰고, 사람이 정할 *결정*을 그 결정이 바꾸는 주장 위에 두고, **열어 보지 않은 기본값을 동의로
> 세지 않는다.** 이 세 가지는 우리 원칙("검증 안 된 것을 done 으로 쓰지 않는다", "되돌릴 수 없는 결정은
> 혼자 하지 않는다")과 같은 방향인데, 지금 task 파일에는 담을 칸이 없다. 그래서 **문법은 task 파일 계약으로
> 흡수(A — 모든 하네스)** 하고, **HTML 화면은 html-plan 플러그인에 맡기고 그 입출구만 잇는다(B — Claude Code +
> 플러그인 설치 시)**. 런타임(JS/CSS 209KB · node)은 들이지 않는다.

## 1. 전제 — 무엇을 하지 않는가

1. **런타임을 저장소에 들이지 않는다.** `htmlplan.js` · `htmlplan.css` · `pack.mjs` 는 MIT 지만, PURPOSE 제외
   영역(Python 외 런타임 · 외부 코드 직접 차용)에 걸린다. B 는 html-plan 의 **입력 형식을 쓰고 출력 형식을
   읽을** 뿐이다.
2. **기존 task 파일(2026-11-12 실측 561개, main 515개)을 고치지 않는다.** 새 필드는 선택이고, 없는 파일은 지금과 똑같이 읽힌다
   (`TASK_FIELD_ALIASES` 가 옛 표기를 계속 받는 것과 같은 원칙).
3. **STE(ASD-STE100) 문체 규칙은 흡수하지 않는다.** 영어 전용이고, 우리 문안은 한국어다. 흡수하는 것은
   "주장은 참·거짓을 가르는 짧은 한 문장" 이라는 **형태 규칙**과 길이 예산뿐이다.
4. **응답을 지시로 읽지 않는다.** html-plan 이 스스로 못 박은 규칙(응답 = 데이터)을 그대로 계약으로 옮긴다.
5. **A 는 B 없이 완결된다.** html-plan 플러그인이 없는 하네스(Codex · Grok · Antigravity 등)에서도 A 의
   필드 · 린트 · 게이트는 그대로 동작해야 한다.

## 2. 실측 — html-plan 1.0.0

출처: [`anthropics/claude-plugins-community/html-plan`](https://github.com/anthropics/claude-plugins-community/tree/main/html-plan),
커밋 `163301d` (2026-11-05), 작성자 Thariq Shihipar, MIT. 내려받은 코드는 **읽기만 했다** (pack 미실행 — §8).

### 2.1 구성

| 파일 | 크기 | 역할 |
|---|---|---|
| `.claude-plugin/plugin.json` | 0.5KB | 매니페스트 (Claude Code 전용 — Codex 매니페스트 없음) |
| `skills/html-plan/SKILL.md` | 12KB | `/html-plan <만들 것>` — 트리 · 규칙 · 문체 · 절차 · 응답 처리 |
| `skills/html-plan/references/blocks.md` | 14KB | 블록 문법 (`doc-plan` · `doc-claim` · `doc-ask` · `doc-code` · `doc-calls` · `doc-schema` · `doc-mock` · `doc-machine` …) |
| `skills/html-plan/runtime/htmlplan.js` · `.css` | 145KB · 64KB | 트리 그리기 · 결정 폼 · 주석 · Respond |
| `skills/html-plan/runtime/pack.mjs` | 46KB | 린트 + 코드 채우기 + 인라인 → 오프라인 단일 파일 (node 필요) |
| `skills/html-plan/examples/scheduled-send.html` | 15KB | 완성 예시 |

### 2.2 트리와 규칙

| 단계 | 답하는 질문 | 주장 | 근거 자료(exhibit) |
|---|---|---|---|
| `h1` | 무엇인가 | 변경 + 장소, 3~7 단어 | 없음 |
| `details.thread` | 왜 | — | 요청자 원문 인용 (`doc-quote`) |
| 1 | 무엇을 하거나 볼 수 있게 되나 | 동작 | 화면 목업 · 상태 기계 |
| 2 | 어떻게 동작하나 | 진입점 · 규칙 · 레코드 하나 | 호출 스택 · 스키마 · 짧은 코드 |
| 3 | 어디인가 | `file:line · symbol` | 실제 코드 |

SKILL.md 규칙 11개 중 우리에게 의미 있는 것 (괄호 = pack 이 기계로 검사하는 규칙):

- 1단계는 **동작 단위로만** 나눈다 — 파일 · 계층 · 작업 순서로 나누지 않는다 (규칙 1).
- 1·2단계 주장은 **참·거짓을 가를 수 있는 한 문장**, 약 12 단어 이내. 3단계는 위치만 (규칙 2 — pack).
- 주장 하나에 근거 자료 하나 (규칙 3 — pack). 접힌 트리가 곧 요약이라 TL;DR · 단계 목록을 쓰지 않는다 (규칙 4).
- 자식 5개 이하 · 깊이 3단계 이하 (규칙 5 — pack).
- 결정은 **그 결정이 바꾸는 주장 위에**, 근거 자료 뒤 · 자식 앞에 둔다. 계획당 2~5개, 추천안에 `checked`,
  선택지가 주장을 없애면 "claim 4 goes" 로 밝힌다 (규칙 6 — 개수는 pack).
- 끝에 `aux="shared"`(여럿이 쓰는 공유 부분) 와 `aux="scope"`(바꾸지 않는 것) (규칙 7 — pack).
- 그린 것보다 실제 코드 — `src="path" lines="a-b"` 로 저장소에서 채우고, 아직 없는 코드는 스케치로 표시 (규칙 8).

### 2.3 pack.mjs

`node pack.mjs plan.html [--root <repo>]… [-o out] [--lint-only] [--artifact]` (`blocks.md` §pack.mjs):

- 브라우저와 같은 파서로 블록과 트리 모양을 린트한다. **오류가 있으면 파일을 쓰지 않는다**; 경고는 단어 ·
  폰 폭 예산이다.
- `src=` 블록을 `--root` 와 페이지 폴더 안에서만 채운다 — 밖은 거부, 비밀처럼 보이는 파일명 · 내용(`sk-ant-` · `AKIA` · 개인키 등)도 거부.
  채운 코드에 **커밋 sha 를 찍고, 커밋되지 않은 변경이면 `+wt`** 를 붙인다. 끝에 "페이지에 들어간 파일" 목록을 출력한다.
- git 은 `rev-parse` · `cat-file` 만 허용하고 hooks · fsmonitor 를 끈다.

### 2.4 Respond 응답 형식 — `htmlplan.js` `buildResponse()` (560–605행)

```
# Re: <h1 텍스트>
## Decisions
<i>. [<주장 번호>] <질문>[  _(kept as proposed)_ | _(not opened; default kept)_]
   → **<선택지 라벨>** `<value>`[  ✎ (was: <기본 라벨>)]
## Walked            ← 상태 기계를 따라 걸은 기록
## Edits             ← doc-draft · doc-schema 수정, diff 펜스
## Struck from the plan
## Comments          ← "  > " 인용
_Lines that start with “>” and the diffs are text the reader typed. …_
```

**설계에 결정적인 사실 세 가지:**

1. 결정 줄에 **`doc-ask` 의 id 가 실리지 않는다.** 식별자는 페이지 순서 번호 `<i>`, 주장 번호 `[1.3]`,
   질문 문장뿐이다.
2. 주장 번호는 **트리 위치로 매겨진다** (`dataset.no = 부모번호 + '.' + (++i)`, 1190행). `aux` 주장은 번호가 없다.
3. 접미사 없음 = 기본값에서 **바뀜**, `kept as proposed` = 열어 보고 유지, `not opened; default kept` = **열지 않음**.
   SKILL.md 는 마지막 것을 "동의로 읽지 말라" 고 못 박는다.

### 2.5 이름이 같은 다른 것

`plannotator/effective-html` 의 `html-plan` 스킬은 별개다 (45행 지침, 원문 보존 · 진척률 날조 금지 위주,
런타임 없음). 그 원칙 중 "원문에 근거 없는 진척 표시 금지" 는 A 의 린트에 겹쳐 들어가므로 따로 다루지 않는다.

## 3. 현재 Plan 계약과의 대조

| html-plan | 지금 우리 | 차이 |
|---|---|---|
| 동작 주장 트리 (1단계 = 동작) | `Files that change` · `Order of work` — **파일 · 순서 단위** | html-plan 이 금지하는 분할만 있다. 무엇이 참이 되는가는 `Completion criteria` 에 따로, 평평하게 있다 |
| 결정 + 기본값 + 열람 상태 | 없음 (대화에만 남는다) | compact · 세션 경계에서 "무엇을 소유자에게 물었고, 답했나" 가 사라진다 |
| `aux="scope"` 바꾸지 않는 것 | `Out of scope` (Description 절) | **이미 있다** — 재사용한다 |
| `aux="shared"` 공유 부분 | 없음 | 흡수하지 않는다 (§4.1 끝) |
| 3단계 `file:line` + sha 찍기 | `Files that change` 는 경로만, 줄 · 존재 검사 없음 | 인용한 위치가 그 커밋에 있는지 잴 수 있다 |
| pack 린트 (오류면 안 씀) | `backlog-update` 게이트 (WBS · 상태 · 형식) | 같은 자리에 린트를 단다 |
| 응답 = 데이터 | 외부 내용 = 데이터 (하네스 규칙) | 워크플로우 정본에는 문장이 없다 |
| 검증자 | `verifier` — 완료 기준별 PASS/FAIL/UNMEASURED | 주장이 생기면 판정 단위를 주장에 묶을 수 있다 |

## 4. 안 A — task Plan 계약 흡수

### 4.1 새 필드

| 의미 key | 정본 라벨 | 한국어 별칭 | 성격 |
|---|---|---|---|
| `plan_claims` | `Claims` | `주장` | 누적 (`CUMULATIVE_FIELDS`, `--replace-field` 로 교체) |
| `plan_decisions` | `Decisions` | `결정` | 누적, 단 **상태 칸은 현재값** (§4.4) |

`## 🧭 Plan` 절의 **맨 앞**에 둔다 (주장이 먼저, 파일 · 순서는 그 다음 — 실행 정보로 남는다).
`Out of scope` 는 그대로 쓰고 위치도 옮기지 않는다. `aux="shared"` 는 흡수하지 않는다 — 우리 계획 단위(task)는
html-plan 의 계획보다 작아 공유 레코드가 드물고, 있으면 2단계 주장 하나로 쓰면 된다.

### 4.2 문법

```markdown
## 🧭 Plan

- Claims: C1 미열람 결정이 남은 task 는 done 으로 닫히지 않는다.
- Claims: C1.1 backlog-update 는 done 전이에서 Decisions 상태를 읽는다.
- Claims: C1.1.1 @ workflow-source/workflow_kit/tools/backlog_update.py:542 · main()
- Claims: C1.1.2 @ new: workflow-source/workflow_kit/common/plan_claims.py · open_decisions()
- Claims: C2 옛 task 파일은 지금과 같게 읽힌다.
- Decisions: D1 [C1] 미열람 결정이 남으면 done 을 막는가? | 기본: block | 선택: block = 거부한다; warn = 경고만 낸다 | 상태: proposed
- Files that change: workflow-source/workflow_kit/tools/backlog_update.py
- Order of work: …
- Plan risks: …
- Proof: …
```

- **주장 ID** `C<n>[.<n>[.<n>]]` — 깊이 = 점 수 + 1. 3단계는 `@ <path>:<line>[-<line>] · <symbol>` 위치만.
  아직 없는 코드는 `@ new: <path> · <symbol>` (html-plan 규칙 8 의 "스케치 표시" 대응 — 줄 번호 없음).
- **결정** `D<n> [<주장 ID>] <질문> | 기본: <value> | 선택: <value> = <설명>; … | 상태: <state>`.
- **상태** `proposed`(아직 묻지 않음) · `unopened`(물었으나 열어 보지 않음 — 기본값 유지) · `kept`(열어 보고 유지) ·
  `changed:<value>`(바꿈) · `answered:<value>`(대화에서 소유자가 직접 답함 — B 없이 쓰는 경로).

### 4.3 린트 규칙

| # | 규칙 | html-plan 대응 | 강도 |
|---|---|---|---|
| L1 | 1단계 주장 ≤ 5, 각 노드 자식 ≤ 5, 깊이 ≤ 3 | 규칙 5 | 경고 |
| L2 | 주장 ID 는 유일하고 형제 사이에서 1 부터 연속 | (B 번호 정합 — §5.3) | **오류** (B 전제) |
| L3 | 1·2단계 주장은 문장(종결 + 마침표)이고 길이 예산 이내 (초안 80자 — requirements 에서 실측 확정) | 규칙 2 | 경고 |
| L4 | 1단계 주장이 경로 · 파일명으로 시작하면 "파일 단위 분할" 경고 | 규칙 1 | 경고 |
| L5 | 3단계 `@ path:line` 이 HEAD 에 있고 줄 범위가 파일 길이 안 | 규칙 8 · pack `src` 검사 | 경고 (아직 없는 파일은 `@ new:` 로 표시하면 면제) |
| L6 | 결정 ≤ 5, 각 결정은 있는 주장을 가리키고, 기본값이 선택지 안에 있고, 선택지 ≥ 2 | 규칙 6 · `checked` 의무 | **오류** (형식) |
| L7 | `Completion criteria` 에 `[C<n>]` 인용이 하나도 없는 1단계 주장 = "재지 않는 주장" | (verifier 연결 — §4.5) | 경고 |
| L8 | 진척률(%) · 상태 배지류 표현이 주장에 있으면 경고 | effective-html 원문 보존 원칙 | 경고 |

린트는 `backlog-update` 쓰기 경로(dry-run 포함)에서 돌고 `warnings` 로 나간다. 파서는 B 의 `plan-export` 와
**같은 함수**를 쓴다 — 두 벌이 되면 갈라진다(이 저장소의 반복 교훈, `TASK_ID_PATTERN` 주석).

### 4.4 게이트 — 상태 전이

| 전이 | `proposed` / `unopened` 결정이 남았을 때 |
|---|---|
| → `in_progress` | 경고: "소유자에게 묻지 않은(또는 열리지 않은) 결정 n건" |
| → `done` | **거부** (기본값 — §7 D2). 결정을 `answered` 로 기록하거나, 결정을 지우고(`--replace-field plan_decisions`) 사유를 Progress 에 남긴다 |

근거: html-plan 의 "열지 않은 기본값 ≠ 동의" 를 우리 원칙 "되돌릴 수 없는 결정은 혼자 하지 않는다" 와 묶는
**유일한 기계 지점**이 done 전이다. 결정이 없는 task 는 영향이 없다.

### 4.5 완료 기준 · verifier 연결

- `Completion criteria` 줄 앞에 `[C1]` 처럼 주장을 인용할 수 있다 (선택). 인용 형식은 줄 머리 대괄호 하나 —
  기존 기준 문장과 섞여도 파싱이 갈라지지 않는다.
- `verifier` 보고에 **주장별 묶음**을 더한다: 1단계 주장마다 인용한 기준들의 판정을 모아
  "C1: PASS 2 · UNMEASURED 1" 로. 인용 없는 1단계 주장은 "재지 않은 주장" 줄로 보고한다 (L7 과 같은 사실).
- 주장이 완료 기준을 **대체하지는 않는다** (기본값 — §7 D3). 대체는 기존 task 파일 561개와 생성기 계약을 깬다.

### 4.6 호환 · 순서

- **리더 먼저:** `TASK_FIELD_LABELS` · `TASK_FIELD_ALIASES` 에 두 라벨을 넣는 릴리스가 쓰는 쪽보다 먼저 나간다
  (2026-08-20 라벨 영어 전환 때와 같은 순서 문제). 같은 릴리스에서 리더 · 라이터를 함께 내도 되는지는
  "옛 리더가 새 라벨 줄을 만나면 무엇을 하나" 의 실측으로 정한다 — 모르는 `- Claims:` 줄을 조용히 버리는지,
  다른 필드에 붙이는지 (§8).
- **state.json 에는 싣지 않는다** (초안). 세션 시작 컨텍스트 예산(ADR-029) 안에 주장 전문이 들어갈 자리가 없다.
  싣는다면 task 별 `open_decisions: n` 숫자 하나 — requirements 에서 정한다.
- **의무 여부:** 기본은 선택 (§7 D1). `Files that change` 가 3개 이상인데 `Claims` 가 비면 경고 하나
  (html-plan 의 발동 조건 "파일 두어 개 넘는 변경" 대응).

### 4.7 정본 · 문서 영향

- `core/global_workflow_standard.md` §1 Working Principles — "작업 전 계획을 task 파일에 적는다" 문장에
  **주장 · 결정**을 더하고, "열지 않은 기본값은 동의가 아니다" 한 줄. → 모든 진입점의 생성 블록이 바뀐다
  (`check_standard_single_source` · bootstrap 진입점 · 플러그인 스킬 본문이 함께 움직인다 — 정본 개정 1회).
- `core/backlog_update_skill_spec.md` — 필드 · 린트 · 게이트 절.
- `.claude/agents/verifier.md` — 주장별 묶음 (§4.5).
- `backlog-update` CLI — `--plan-claim` · `--plan-decision` (반복), `--decision-state D1=answered:block` (현재값 교체).

## 5. 안 B — html-plan 검토 브리지

### 5.1 흐름

```
task 파일 (A 계약)
   │  wk plan-export --task=ID            ← Python, 결정론
   ▼
<ID>.plan.html  (html-plan 원본 형식, 근거 자료 자리는 비어 있음)
   │  /html-plan  "이 뼈대를 채워라"        ← html-plan 스킬이 목업 · 호출 스택 · 스키마를 채움
   │  node pack.mjs … --root <repo>        ← html-plan 쪽 (node)
   ▼
<ID>.plan.packed.html  → 소유자가 브라우저에서 열고 결정 · 주석 → Respond → 복사
   │  wk plan-import --task=ID --response=<파일|->   (기본 dry-run, --apply)
   ▼
task 파일 Decisions 상태 갱신 + 응답 원문 보존 + Progress 한 줄
```

`plan-export` 는 **뼈대**만 만든다 — 근거 자료(목업 · 상태 기계 · 호출 스택)는 판단이 필요해 LLM(html-plan 스킬) 몫이다.
우리 명령은 "task 파일에 이미 있는 사실" 만 옮기고, 그 사실이 화면에서 **번호까지 그대로** 보이게 보장한다.

### 5.2 `plan-export` 매핑

| task 파일 | html-plan 원본 | 비고 |
|---|---|---|
| 제목의 ` — ` 앞부분 | `h1` | 7 단어(한국어는 어절)를 넘으면 경고 (html-plan 규칙 11) |
| `Description` | `details.thread` > `doc-quote via="doc" from="<TASK-ID>"` | 원문 그대로, 줄이지 않는다 |
| `Files that change` | `doc-changes new= changed=` | HEAD 에 있으면 changed, 없으면 new. 글롭 · 설명 붙은 줄은 세지 않고 보고 |
| `Claims` 1·2단계 | `doc-claim` > `<p>` + **근거 자료 자리** (`doc-note tone="idea"` "근거 자료 필요") | ID 순서 그대로 (§5.3) |
| `Claims` 3단계 `@ path:line` | `doc-claim at="path:line"` > `doc-code src="path" lines="a-b"` | pack 이 sha 를 찍는다 |
| `Decisions` | 가리키는 주장 안 `doc-ask id="D<n>"` + radio, 기본값에 `checked` | 상태가 `answered` · `changed` 인 결정은 **답한 값**을 checked 로 (재검토 왕복) |
| `Plan risks` 중 `[C<n>]` 인용 줄 | 그 주장의 `doc-note tone="risk"` | 인용 없는 위험은 내보내지 않고 보고 |
| `Out of scope` | `doc-claim aux="scope"` > `<ul>` | |
| `Order of work` · `Proof` · `Completion criteria` | 내보내지 않음 | 실행 정보 — 보고에 "내보내지 않은 필드" 로 센다 |

머리에 `<meta name="generator" content="workflow_kit plan-export">` 와 `<meta name="html-plan-format" content="1.0.0">` 를
싣는다. 보고(JSON)는 **내보낸 것 · 내보내지 않은 것**을 빠짐없이 센다 — 원문 약속이 화면에서 사라졌는지 사람이 볼 수 있게.

### 5.3 번호 정합 불변식

html-plan 은 주장 번호를 트리 위치로 매기고(§2.4-2), 응답은 결정을 위치 번호로만 식별한다(§2.4-1). 그래서:

- **L2 (오류)** — 주장 ID 가 형제 사이에서 1 부터 연속이면, `plan-export` 가 ID 순서대로 내보낸 페이지의
  위치 번호 `1.3` 은 정확히 `C1.3` 이다.
- 결정의 페이지 순서는 주장 트리의 전위 순회 순서다 — export 가 같은 순회로 `D` 를 배치하므로, 응답의 `<i>` 번째
  결정이 어느 `D` 인지 계산할 수 있다.
- import 는 **세 값을 모두** 대조한다: 위치 순번 `<i>`, 주장 번호 `[1.3]`, 질문 문장. 하나라도 어긋나면 그 응답은
  지금 task 파일과 다른 계획에 대한 것이다 → 쓰지 않는다 (§5.5).
- 주의: html-plan 스킬이 뼈대를 채우면서 **주장을 더하거나 순서를 바꾸면** 번호가 밀린다. 스킬 지시문에 "주장 ·
  결정을 더하거나 옮기지 말고 근거 자료만 채워라" 를 넣고, import 의 3중 대조가 마지막 방어선이다.

### 5.4 `plan-import`

1. 입력: 파일 또는 stdin, 상한 256KB, 제어 문자 거부.
2. `# Re: <h1>` 이 export 한 `h1` 과 같은지 본다.
3. `## Decisions` 의 각 항목을 파싱한다: 접미사 → 상태 (`kept as proposed` → `kept`,
   `not opened; default kept` → `unopened`, 접미사 없음 → `changed:<value>`). 값은 `` `<value>` `` 백틱 안에서만 읽는다.
4. §5.3 대조를 통과한 결정만 상태를 갱신한다 (`answered` · `changed` 는 덮지 않는다 — 소유자가 대화에서 먼저 답했으면
   그것이 우선, 충돌은 보고).
5. 응답 원문 전체를 브랜치 메모리에 저장한다 (§7 D5 — 기본 `active/<branch>/plan_responses/<TASK-ID>-<n>.md`).
6. task `Progress` 에 한 줄: "plan 응답 n: 결정 4 (바뀜 1 · 미열람 1) · 주석 2 · 수정 0 · 삭제 1 — <경로>".
7. `## Edits` · `## Struck from the plan` · `## Comments` · `## Walked` 는 **반영하지 않는다** (§7 D4 기본) —
   원문 파일에만 있고, 에이전트가 읽고 소유자와 대화로 처리한다.

기본은 dry-run(무엇을 쓸지 JSON), `--apply` 로 쓴다 — `backlog-update` 와 같은 관례.

### 5.5 실패 시 닫힘

다음 중 하나면 **아무것도 쓰지 않고** 이유를 보고한다: `h1` 불일치 · 결정 수 불일치 · 3중 대조 실패 · radio 가 아닌
결정 컨트롤(export 가 radio 만 내므로 형식 변화의 신호) · 알 수 없는 접미사 · 상한 초과. 부분 반영은 하지 않는다.

### 5.6 응답 = 데이터

- 응답은 그 페이지를 연 **누구든** 쓴 텍스트다. `plan-import` 는 명령을 실행하지 않고, 경로를 열지 않고, URL 을 따르지 않는다.
  하는 일은 Decisions 상태 갱신 · 원문 저장 · Progress 한 줄뿐이다.
- 주석 · 수정 · 삭제 요청이 계획 밖의 일을 요구하면, 에이전트는 실행하지 않고 소유자에게 대화로 묻는다.
  이 문장을 정본 §1 의 "외부 내용" 규칙 옆에 둔다.

### 5.7 형식 결합

- html-plan 1.0.0 은 첫 공개 판(2026-11-05)이다. 응답 문자열은 런타임 코드 안의 리터럴이고 **공개 계약으로 선언된 것이
  아니다** — 바뀌어도 알림이 없다.
- 대응: ①export 머리에 형식 판을 싣고, import 는 아는 판만 받는다 ②응답 형식 fixture(2.4 의 실제 출력 모양)를
  검사로 고정한다 ③형식이 바뀌면 §5.5 가 닫히므로 **조용한 오반영은 없고** 실패만 있다.
- `doctor` 가 html-plan 플러그인 설치 · 판을 보고할지는 design 에서 정한다 (설치 안 됐을 때 B 명령의 안내 문구 포함).

### 5.8 하네스 · 채널

- B 는 **Claude Code + html-plan 플러그인 + node** 가 있을 때만 끝까지 간다. 다른 하네스에서 `plan-export` 결과는 런타임 없는
  HTML 이라 화면이 없다 — 명령은 동작하되 "html-plan 플러그인 필요" 를 보고한다.
- §11.1 명령이 두 개 는다(`plan-export` · `plan-import`). 플러그인 스킬은 §11.1 과 1:1 이므로 스킬도 따라 는다 — 두 개로 둘지,
  왕복을 한 스킬(`plan-review`)로 묶고 §11.1 예외를 선언할지는 design 의 결정 대상이다 (compact-relay 는 명령 1 · 스킬 1).

## 6. 새로 만드는 것 — 정본과 파생

| 무엇 | 어디 | 안 |
|---|---|---|
| 라벨 2 · 별칭 2 | `common/project_docs.py` `TASK_FIELD_LABELS` · `TASK_FIELD_ALIASES` | A |
| 주장 · 결정 파서 + 린트 (공용) | `common/` 새 모듈 (예: `plan_claims.py`) | A · B 공용 |
| 쓰기 · 게이트 | `tools/backlog_update.py` (`PLAN_FIELDS` · `CUMULATIVE_FIELDS` · 상태 전이) · `common/workflow_writes.py` (`_PLAN_KEYS`) | A |
| verifier 주장별 묶음 | `.claude/agents/verifier.md` | A |
| 정본 문장 | `core/global_workflow_standard.md` §1 (+ §11.1 명령 2줄) → 생성 블록 전파 | A · B |
| `plan-export` · `plan-import` | `tools/` 새 모듈 + CLI 등록 | B |
| 응답 fixture · 왕복 검사 | `workflow-source/tests/` | B |
| 플러그인 스킬 | `plugin_payload.py` 파생 | B |

## 7. 소유자 선택지

| # | 결정 | 기본 (권장) | 대안 |
|---|---|---|---|
| D1 | `Claims` 의무 여부 | **선택** — 있으면 린트, `Files that change` ≥ 3 인데 비면 경고 | 새 task 는 필수 (create 거부) |
| D2 | 미열람 결정 게이트 | **in_progress 경고 · done 거부** | 둘 다 경고만 |
| D3 | 완료 기준과 주장의 관계 | **인용 연결** — 기준에 `[C1]` 선택, 인용 없는 1단계 주장 경고, verifier 주장별 묶음 | 주장이 완료 기준을 대체 (계약 파괴 — 기존 task 파일 561개 · 생성기) |
| D4 | import 반영 범위 | **결정 상태만** — 수정 · 삭제 · 주석은 원문 보존, 사람이 처리 | `Struck` 를 Plan 에서 자동 제거까지 |
| D5 | 응답 원문 보존 위치 | **브랜치 메모리에 커밋** (`plan_responses/`) — 소유자 결정의 근거가 남는다 | 워크트리 로컬 · gitignore (compact-relay checkpoint 와 같은 취급) |

**권장 근거:** A 는 이 저장소가 반복해서 잃은 것(대화에만 있던 결정 · 재지 않은 약속)을 task 파일에 고정하는 일이라 비용
대비 가치가 크다. 의무화(D1 대안)와 대체(D3 대안)는 계약을 깨거나 모든 작은 task 에 부담을 지운다. B 는 A 의 문법 위에서만
가능하고(번호 정합), 반영 범위를 결정 상태로 좁혀야(D4) 외부 형식이 바뀌어도 피해가 "닫힘" 에서 멈춘다.

## 8. 미실측 · 리스크

- **pack.mjs 를 돌리지 않았다** (내려받은 코드 실행 회피). 뼈대의 `doc-note` 자리표시가 규칙 3(근거 자료 하나) 검사에서
  오류인지 경고인지 모른다 — requirements 전에 격리 디렉터리에서 example 과 뼈대로 실측한다 (node 26.13.0 은 이 호스트에 있다).
- pack 의 STE 경고가 **한국어 문안**에서 어떻게 나오는지 모른다 — 경고 폭주면 B 의 화면 검토 경험이 나빠진다.
- 옛 리더가 모르는 `- Claims:` 줄을 만나면 어떻게 되는지(§4.6) — 버리는지, 앞 필드 값에 붙는지.
- 주장 길이 예산 80자는 근거 없는 초안이다 — 이 저장소 task 의 완료 기준 길이 분포로 정한다.
- html-plan 의 응답 형식은 선언된 계약이 아니다 (§5.7). 1.0.0 이후 판의 변화를 지켜볼 장치가 없다.
- 이 문서 자체가 A 의 문법을 아직 쓰지 못한다 — 첫 적용 대상은 M-022 이후 단계의 task 다.

## 9. 다음 단계

소유자 결정(§7) → requirements([`M-022`](../../ai-workflow/memory/active/roadmap/M-022-claim-plan.md) 다음 마일스톤)에서
§8 미실측을 재고 숫자(길이 예산 · 응답 상한)를 확정 → design(ADR-031 + core 스펙)에서 모듈 배치 · §11.1 문구 · 스킬 수 ·
`doctor` 연동을 결정.

## 10. 소유자 결정 (2026-11-12, 123차)

권장안(§7 기본값)대로:

1. **D1** `Claims` 는 **선택** — 있으면 린트, `Files that change` ≥ 3 인데 비면 경고 하나.
2. **D2** 열리지 않은 결정 게이트 — `proposed` · `unopened` 결정이 남으면 **in_progress 전이 경고 · done 전이 거부**.
3. **D3** 완료 기준과 주장은 **인용 연결** — 기준 줄 머리 `[C<n>]` (선택), 인용 없는 1단계 주장 경고(L7), verifier 주장별 묶음.
   주장은 완료 기준을 대체하지 않는다.
4. **D4** `plan-import` 는 **결정 상태만** 반영 — 수정 · 삭제 · 주석 · 걸은 기록은 원문 파일에만 두고 사람이 처리한다.
5. **D5** 응답 원문은 **브랜치 메모리에 커밋** — `active/<branch>/plan_responses/<TASK-ID>-<n>.md`.

범위는 A + B 그대로. requirements 단계는 [`M-023`](../../ai-workflow/memory/active/roadmap/M-023-claim-plan-requirements.md) 로 이어진다 —
§8 미실측(pack.mjs 격리 실측 · 옛 리더의 새 라벨 처리 · 주장 길이 예산 · 응답 상한)을 먼저 잰다.

## 11. 정정 — 하네스 중립 제약 (2026-11-12, 123차)

소유자 지시: **이 kit 은 Claude 전용이 아니므로 Claude 전용 기능은 있으면 안 된다.**

안 B 는 html-plan 플러그인과 잇는 브리지였다. html-plan 은 Claude Code 플러그인(`.claude-plugin` 매니페스트만 있다)이라,
B 의 흐름(`plan-export` → `/html-plan` 채움 → pack → Respond → `plan-import`)은 Claude Code 에서만 끝까지 간다 (§5.8 이
이미 그렇게 적었다). 그래서 B 를 다음처럼 바꾼다 — 정정안은 [`plan-workbench-review-2026-11.md`](./plan-workbench-review-2026-11.md)
(M-024) §8 W5 로 소유자 확인을 받았다 (2026-11-12 확정, 같은 문서 §10):

- **삭제**: html-plan 형식 export(§5.2 매핑 · §5.3 번호 정합 · `html-plan-format` 메타), html-plan Respond 파싱(§5.4 의 접미사
  `kept as proposed` · `not opened; default kept` 해석), 형식 결합 위험(§5.7), 플러그인 의존(§5.8).
- **대체**: 결정 응답은 kit 워크벤치(웹, Python — 접속 위치 무가정은 M-024 §11)의 결정 폼이 **우리 응답 형식**으로 브랜치 받은편지함에 쓰고,
  `plan-import` 가 그 형식을 읽는다. 하네스와 무관하다.
- **유지**: 안 A 전부(필드 · 린트 · 게이트 · verifier 묶음), D1~D5, 응답 = 데이터(§5.6), 실패 시 닫힘(§5.5 — 대조
  대상만 우리 형식으로), 응답 원문 보존(D5).
- html-plan 에서 가져오는 것은 이제 **개념뿐**이다 — PURPOSE 의 "외부 reference 의 concept 흡수, 코드 차용 ❌" 와도 맞는다.

