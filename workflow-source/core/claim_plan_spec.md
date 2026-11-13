# 주장 트리 계획 스펙

- 문서 목적: task 파일 Plan 의 주장 · 결정 계약과, 결정 응답을 데이터로 받아 반영하는 kit 계약(필드 · 린트 · 게이트 · 계획 지문 · 응답 파일 · 받은편지함 · 결정 상태 계산 · 명령 · 생성물)을 정의한다.
- 범위: task 라벨 `Claims` · `Decisions`, 린트 L1~L10, `backlog-update` 의 추가 인자와 상태 전이 게이트, 응답 형식 `workflow-kit-plan-response/1`, `plan_responses/` 디렉터리, `plan-import` · `plan-status` 명령, `state.json` 의 `open_decisions`, 브랜치 이어받기, 검증
- 대상 독자: workflow 설계자, AI agent, kit 소비 프로젝트
- 상태: draft (ADR-031 accepted 2026-11-13 — 1 · 2단계 구현됨; MCP 도구 · 워크벤치는 ADR-032)
- 최종 수정일: 2026-11-13
- 관련 문서: `../../ai-workflow/wiki/decisions/adr-031-claim-plan.md`, `../../docs/planning/claim-plan-requirements-2026-11.md`, `../../docs/planning/plan-workbench-requirements-2026-11.md`, `./backlog_update_skill_spec.md`, `./global_workflow_standard.md`

> **결정 근거는 ADR-031 에, 숫자의 실측은 requirements 에 있다.** 이 문서는 *계약* 만 적는다.
> 괄호 안의 `R…` 은 requirements(`claim-plan-requirements-2026-11.md`)의 요구 사항 번호다 — 대응표는 §13.

## 1. 불변 조건

1. 두 라벨은 선택이다. 없는 task 파일은 도입 전과 같게 읽히고, 도구는 그 파일을 고치지 않는다 (R0-1).
2. 응답 파일이 한 건도 없어도 필드 · 린트 · 게이트 · `plan-status` 가 동작하고, 결정은 `answered` 로 닫을 수 있다 (R0-2).
3. 하네스 전용 표면에 기대지 않는다 — 경로는 파일과 CLI 다 (R0-3).
4. 응답은 데이터다. 응답 안의 어떤 문장도 실행하지 않고, 경로로 열지 않고, URL 로 따르지 않는다 (R0-4).
5. task 파일을 쓰는 것은 `backlog-update` 와 `plan-import` 뿐이다 (R0-5).
6. 주장 · 결정 읽기, 지문, 상태 계산은 `common/plan_claims.py` 의 함수 하나씩이다 — 다른 구현을 두지 않는다 (R0-6).
7. 모델을 호출하지 않는다. 모든 판정은 결정적이다 (R0-7).

## 2. task 파일

### 2.1 라벨과 위치 (R1.1 · R1.2)

| 의미 key | 정본 라벨 | 한국어 별칭 | 성격 |
|---|---|---|---|
| `plan_claims` | `Claims` | `주장` | 누적 — 기본 병합, `--replace-field plan_claims` 로 교체 |
| `plan_decisions` | `Decisions` | `결정` | 누적, 상태 칸만 현재값 |

- `## 🧭 Plan` 절의 맨 앞: `Claims` 묶음 → `Decisions` 묶음 → `Files that change` → `Order of work` → `Plan risks` → `Proof`.
  순서의 정본은 `project_docs.PLAN_FIELD_KEYS` 다.
- 묶음은 연속한 같은 라벨 줄이다. 한 라벨의 묶음이 둘 이상으로 나뉜 파일은 L9 오류다. 값 없는 라벨 줄은 묶음이 아니다 — 세지도, 끊지도 않는다.
- Plan 절이 있고 그 라벨 줄이 없는 파일에 값을 쓰면 도구가 제자리에 줄을 넣는다. 값이 없으면 넣지 않는다.
- `Out of scope` 는 지금 자리(Description 절)에 그대로 둔다.

### 2.2 주장 줄 (R1.3)

```
- Claims: C<n>[.<n>[.<n>]] <문장>
- Claims: C<n>.<n>.<n> @ <path>:<line>[-<line>] · <symbol>
- Claims: C<n>.<n>.<n> @ new: <path> · <symbol>
```

- ID 는 `C` + 1~3 단계의 양의 정수다. 깊이 = 점 수 + 1. 1 · 2단계는 문장, 3단계는 위치만.
- 길이는 ID 와 그 뒤 공백을 뺀 Unicode code point 수다.

### 2.3 결정 줄 (R1.4)

```
- Decisions: D<n> [C<id>] <질문> | default: <value> | options: <value> = <설명>; <value> = <설명>[; …] | state: <state>
```

- `<value>` 는 `[a-z0-9_-]{1,32}` 다.
- 칸 구분자는 ` | `, 선택지 구분자는 `; `. 칸 이름은 `default` · `options` · `state` 로 쓰고, `기본` · `선택` · `상태` 도 읽는다.
- 질문 · 설명에 ` | ` 가 있으면 L6 오류다.

### 2.4 결정 상태 (R1.5)

| 상태 | 뜻 | 열린 결정 | CLI 로 지정 |
|---|---|---|---|
| `proposed` | 유효한 응답이 없다 | 예 | `--decision-state D<n>=proposed` (`answered` 를 걷는다) |
| `unopened` | 응답은 있으나 그 결정에 채택된 입장이 없다 | 예 | 불가 |
| `disputed` | 서로 다른 응답자가 다른 값을 밝혔다 | 예 | 불가 |
| `kept` | 채택된 입장이 기본값이다 | 아니오 | 불가 |
| `changed:<value>` | 채택된 입장이 기본값이 아니다 | 아니오 | 불가 |
| `answered:<value>` | 대화에서 소유자가 답했다 | 아니오 | `--decision-state D<n>=answered:<value>` |

상태 칸은 §8 의 계산 결과를 적어 둔 것이다. 계산의 입력은 그 칸이 `answered` 인지뿐이다.

### 2.5 `backlog-update` 의 추가 인자 (R1.6)

| 인자 | 뜻 |
|---|---|
| `--plan-claim <줄>` (반복) | 주장 한 줄 (`C1 …`) |
| `--plan-decision <줄>` (반복) | 결정 한 줄. 줄에 `proposed` 가 아닌 `state:` 가 있으면 경고하고 버린다 — 새 결정은 `proposed` 다 |
| `--decision-state D<n>=<state>` (반복) | `answered:<value>` 또는 `proposed` 만. 다른 상태 · 모르는 결정 ID · 선택지 밖의 값은 거부 (`decision_state_rejected`) |
| `--replace-field plan_claims\|plan_decisions` | 묶음을 교체한다. **열린 결정을 없애는** 쓰기(교체든, 같은 ID 로 task 를 다시 만드는 create 든)는 같은 호출에 `--progress-note` 가 있어야 한다 — 사유에는 글자나 숫자(유니코드의 글자 · 숫자 — Python `str.isalnum`)가 하나는 있어야 한다: 공백 · 기호 · 폭 없는 문자뿐이면 사유가 아니고, 글자로 분류되지만 빈칸으로 정의된 여섯(U+115F · U+1160 · U+3164 · U+FFA0 · U+13441 · U+13442)은 글자로 세지 않는다. 판정은 이 열거가 전부다 — 사유는 제거의 흔적을 남기게 하는 장치이지 내용을 심사하는 방벽이 아니다 (없으면 거부 — `decision_removal_needs_note`) |

## 3. 린트 (R2)

| # | 규칙 | 강도 |
|---|---|---|
| L1 | 1단계 주장 ≤ 5, 각 노드의 자식 ≤ 5 | 경고 |
| L2 | 주장 ID 가 유일하고, 형제 사이에서 1 부터 연속이고, 부모가 있다 | 오류 |
| L3 | 1 · 2단계 주장에 `;` 가 없고 80자 이내다 | 경고 |
| L4 | 1단계 주장이 경로 · 파일명으로 시작한다 | 경고 |
| L5 | `@ path:line` 위치의 파일이 HEAD 에 있고 줄이 파일 길이 안이다 (`@ new:` 면제, git 밖이면 건너뛰고 보고); 3단계 주장은 위치여야 한다 | 경고 |
| L6 | 결정 ≤ 5, 결정 ID 유일, 가리키는 주장이 있다, 선택지 ≥ 2, `default` 와 상태의 값이 선택지 안, 값 문법 · 칸 형식이 맞다 | 오류 |
| L7 | 자신 또는 후손을 인용한 완료 기준이 없는 1단계 주장 | 경고 |
| L8 | 주장에 진척률(`\d+\s*%`)이 있거나 `완료` · `done` · `✅` 로 끝난다 | 경고 |
| L9 | `Claims` 또는 `Decisions` 묶음이 둘 이상으로 나뉘어 있다 | 오류 |
| L10 | 완료 기준의 `[C<id>]` 인용이 없는 주장을 가리킨다 | 경고 |

- 완료 기준 줄의 머리에 `[C<id>]` 를 하나 둘 수 있다 (선택).
- **오류**: `backlog-update` 가 파일을 쓰지 않는다 — `status: error`, `error_code: plan_lint_error`, 규칙 번호와 줄, rc 1. dry-run 도 같은 오류를 낸다.
- **경고**: 쓰고, `warnings` 에 규칙 번호와 함께 싣는다. 종료 코드는 0 이다.
- 린트는 그 호출이 주장 · 결정을 건드릴 때와 상태 전이 때 돈다. 그 밖의 update 는 경고를 되풀이하지 않는다.
- 이미 오류 상태인 파일: 주장 · 결정을 건드리지 않는 update 는 통과시키고 경고 하나를 낸다. 상태 전이는 §4 를 따른다 —
  **오류 규칙을 어긴 파일의 → `done` 은 거부한다** (`plan_lint_error`, 열린 결정 수와 무관), 그 밖의 전이는 통과한다. 오류가 있는 동안에는
  상태 칸을 다시 적지 않는다 (§8.6).
- **권고 (R2.3)**: `Files that change` 에서 `ai-workflow/` 로 시작하는 줄을 뺀 수가 3 이상인데 `Claims` 가 비면, create 와 → `in_progress` 전이에서
  한 번씩 `Claims 가 없다 — 바뀌는 파일 n개 (R2.3)` 를 경고한다.

## 4. 게이트 (R3)

열린 결정 = §8 로 **다시 계산한** 상태가 `proposed` · `unopened` · `disputed` 인 결정. 줄을 읽을 수 없는 결정(L6)은 열린 것으로 센다.

| 전이 | 조건 | 동작 |
|---|---|---|
| → `in_progress` | 열린 결정 n ≥ 1 | 쓰고 경고: `열린 결정 n건 (D1 proposed, D3 disputed) — 묻지 않았거나, 열리지 않았거나, 답이 갈렸다. 기본값은 동의가 아니다.` |
| → `done` | 열린 결정 n ≥ 1 | **거부** (`open_decisions`): 파일 무변경, rc 1 — `done 거부: 열린 결정 n건 (D1, D3). --decision-state D1=answered:<value> 로 답을 기록하거나, --replace-field plan_decisions 로 결정을 걷고 사유를 Progress 에 남긴다.` |
| → `done` | 그 task 의 받은편지함 건수(§7-7)가 1 이상이다 | **거부** (`pending_plan_responses`): `done 거부: 계획 응답 n건 미반영 — plan-import 로 반영하거나 --discard 로 거둔다.` |
| → `done` | task 파일이 오류 규칙(L2 · L6 · L9)을 어긴다 | **거부** (`plan_lint_error`) |
| → `blocked` · `planned` | — | 영향 없음 |

- 결정이 없는 task 는 **열린 결정 행과 받은편지함 행**의 영향을 받지 않는다. 오류 규칙 행은 주장만 있는 task 에도 적용된다 — L2 · L9 를 어긴
  `Claims` 만 있어도 → `done` 은 거부된다. 주장도 결정도 없는 task 는 이 절 전체와 무관하다.
- 거부 사유가 겹치면 `error_code` 는 표의 아래에서 위 순서로 고른다 — `plan_lint_error` > `pending_plan_responses` > `open_decisions` — 그리고
  `warnings` 에 나머지 사유를 함께 싣는다.
- 거부는 검증 결과 없는 `done` 의 강등(`determine_conservative_task_status`)보다 먼저 판정하고, 거부가 이긴다. 두 사유를 함께 보고한다.
- 거부는 `build_error_result` 의 JSON 과 rc 1 로 나간다. 쓰기 블록에 닿지 않는다.
- **칸 고쳐 쓰기**: `--apply` 가 붙어 실제로 쓰는 호출은 (task 파일이 오류 규칙을 어기지 않은 한 — §8.6) 계산값과 다른 상태 칸을 고치고 경고한다 —
  `뒷받침 없는 상태를 되돌렸다: D<n> changed:x → proposed`. 거부된 전이와 읽기 전용 명령은 쓰지 않고 **같은 경고만** 낸다
  (거부된 `done` 은 파일 무변경이다).
- **우회 검출 (R3.4)**: `refresh-state` 와 `session-start` 는 `done` 인데 계산한 열린 결정이 있는 task 를 `warnings` 에 싣는다 —
  `done 인데 열린 결정이 있다: <TASK-ID> (D1)`. 재생성은 막지 않고 파일도 고치지 않는다.

## 5. 계획 지문 (R5.2)

`plan_digest = "sha256:" + hex(sha256(본문))`. 본문은 `Claims` 줄 전부와 `Decisions` 줄 전부를 다음처럼 고친 것을 파일 순서대로 LF 로 이은 UTF-8 이다:

1. 라벨을 정본 표기(`Claims` · `Decisions`)로.
2. 결정 줄은 `<머리> | default: <값> | options: <값>` 으로 다시 쓴다 — 칸 이름은 정본 표기, 칸은 이 순서, 칸 값의 앞뒤 공백은 걷고,
   `state` 칸은 **뺀다**. 읽을 수 없는 결정 줄(L6)은 원문 그대로 쓴다.
3. 줄 끝 공백을 걷는다.

주장 문장 · 질문 · 선택지 · 기본값 중 하나라도 바뀌면 지문이 바뀐다. 상태만 바뀌면 같다.

## 6. 응답 파일 (R5)

```markdown
---
format: workflow-kit-plan-response/1
task: <TASK-ID>
plan_digest: sha256:<64 hex>
responder: <이름>
role: approver
received_at: 2026-11-13T21:04:11.482913+09:00
---

## Decisions

- D1 [C1] value: block | default: block | opened: yes
- D2 [C1.2] value: warn | default: block | opened: no

## Comments

- [C1.1]
  > 줄마다 "  > " 로 시작한다.
```

- `## Decisions` 는 응답 시점 task 의 모든 결정을 ID 순으로 한 줄씩 싣는다. `opened` 는 `yes` · `no`.
- `## Comments` 는 선택. 대상은 주장 ID · 결정 ID · `[-]`.
- 머리말의 키는 위 여섯뿐이고 한 번씩이다 — 모르는 키 · 겹친 키는 `format` 을 읽을 수 없는 것으로 본다 (자격 2 단계).
  `responder` 가 비었거나 `received_at` 이 아래 꼴이 아니면 1 단계다 — 그래서 머리말이 아예 없는 파일 · 빈 파일도 1 단계다.
- `received_at` 은 ISO 8601 의 한 꼴이다: `YYYY-MM-DDTHH:MM:SS[.f…]±HH:MM` — 날짜와 시각 사이는 `T`, 초까지 적고, 소수 초는 1~6 자리,
  시간대는 숫자 오프셋(`Z` 아님), 숫자는 ASCII. 시 00~23 · 분 00~59 · 초 00~59(윤초 없음), 오프셋 시 00~23 · 분 00~59. 순서의 비교는 표기가 아니라 순간이다. 그 밖의 표기(기본형 · 주 날짜 · 초 생략 · 7 자리 이상의 소수)는 받지 않는다 —
  읽는 쪽이 라이브러리의 파서에 맡기면 받는 범위가 실행 환경마다 달라진다.
- 줄 끝 LF, UTF-8, BOM 없음. 읽는 쪽은 줄바꿈을 고치지 않는다 — CR 은 제어 문자로 자격 1 단계에서 떨어진다 (고치는 것은 쓰는 쪽이다).
- 읽기 · 쓰기는 `encoding="utf-8"` · `newline="\n"` 을 명시한다 (`check_text_io_encoding` 의 대상).
- **한도 (R5.3)** — 각각 적용한다: 파일 전체 65,536 바이트 이하 · 주석 20건 이하 · 주석 한 건 1,000 code point 이하(줄바꿈을 센다, 접두 `  > ` 는
  세지 않는다) · `responder` 32자 이하 · `\n` · `\t` 밖의 제어 문자(U+0000–U+001F, U+007F) 없음.

## 7. `plan_responses/` (R8)

| 경로 (`ai-workflow/memory/active/<branch>/` 아래) | 무엇 | git |
|---|---|---|
| `plan_responses/inbox/<TASK-ID>-<n>.md` | 미반영 응답 | 무시 |
| `plan_responses/inbox/.gitignore` (`*`) · `.lock` | 자기 무시 · import 잠금 | 무시 |
| `plan_responses/<TASK-ID>-<n>.md` | 보관 — 자격 있는 응답 (채택됐든 다툼에 들었든) | 커밋 |
| `plan_responses/<TASK-ID>-<n>.rejected.md` | 거둔 응답 | 커밋 |

1. **번호**: `<n>` = `received_at` 의 epoch 마이크로초 정수. 쓰는 쪽이 정하고 보관까지 그대로다. 그 task 에 같은 번호가 이미 있으면
   (접미사 `.md` · `.rejected.md` 를 통틀어, 받은편지함과 보관 양쪽에서) 1 씩 더한다. 번호는 식별자일 뿐 순서의 근거가 아니다 —
   순서는 `received_at` 이다. 파일은 `<TASK-ID>-<숫자>.md` · `<TASK-ID>-<숫자>.rejected.md` 로만 찾는다.
2. **쓰기** (쓰는 쪽 — 워크벤치 또는 손): 같은 디렉터리의 `*.md` 가 아닌 임시 이름에 다 쓴 뒤 최종 이름으로 한 번에 공개한다. 있는 이름에 쓰지 않는다.
3. **자기 무시**: 받은편지함을 만들거나 여는 코드는 `inbox/.gitignore` 의 내용이 `*\n` 인지 매번 확인하고 다르면 다시 쓴다.
4. **잠금**: `plan-import` 의 `--apply` 와 `--discard --apply` 는 `inbox/.lock` 에 `common/file_lock.try_lock_exclusive` 를 쥐고 돈다.
   못 쥐면 기다리지 않고 `import_busy` 를 보고한다 (rc 0, 아무것도 쓰지 않음). 쥔 뒤 받은편지함을 다시 읽는다.
5. **배타 이동**: 보관(과 `.rejected.md`)으로의 이동은 있는 파일을 덮지 않는다. 그 번호가 이미 있으면(1 의 뜻으로) 1 을 더해 옮긴다.
   "이미 있다" 는 그 이름의 항목이 있다는 뜻이다 — 파일이 아닌 항목(디렉터리 · 깨진 링크)도 번호를 쥔다. 옮기는 파일 **자신**은 세지 않는다
   (브랜치 안의 디렉터리가 심볼릭 링크여도 같은 항목이면 자신이다).
6. 쓰는 쪽은 잠금을 쥐지 않는다.
7. 받은편지함의 "건수" 는 `inbox/<TASK-ID>-<숫자>.md` 의 수다 (1 의 패턴 — 임시 파일 · 숨은 파일 · 그 밖의 이름은 세지 않는다).
   `<TASK-ID>` 는 작업 항목 ID 문법(`project_docs.WORK_ITEM_ID_PATTERN`)에 맞는 것이고 `<숫자>` 는 ASCII `0-9` 다. 게이트가 세는 이름과
   보고가 "알 수 없는 파일" 로 치는 이름은 서로 여집합이다. epoch 이전의 `received_at` 은 번호 0 에서 출발한다.
   패턴에 맞지 않는 `.md` 가 받은편지함에 있으면 `plan-import` 와 `plan-status` 가 "알 수 없는 파일" 로 보고한다 — 게이트는 그것으로 막지 않는다.

## 8. 결정 상태 계산 (R6.2 · R6.3)

입력은 셋이다: task 파일의 주장 · 결정 줄(상태 칸은 `answered` 인지만), 그 task 의 보관 응답(`.rejected.md` 제외), 지금의 계획 지문.
출력은 결정마다 상태 하나다. **같은 입력이면 같은 출력이다** — 응답이 도착한 순서, import 를 부른 횟수와 방식, `answered` 를 적은 시점이
결과를 바꾸지 않는다.

### 8.1 자격 (R6.2 의 1~6)

응답 파일은 다음을 **모두** 지킬 때 자격이 있다. 보관된 파일도 매 계산에서 다시 본다.

1. §6 의 한도 · 인코딩.
2. `format` 이 `workflow-kit-plan-response/1`.
3. `task` 가 그 task 이고, 그 task 파일이 현재 브랜치에 있다.
4. `plan_digest` 가 지금 계산한 지문과 같다.
5. `role` 이 `approver`.
6. `## Decisions` 의 결정 ID 집합이 task 의 것과 같다; 각 줄의 주장 ID · `default` 가 task 와 같다; `value` 가 선택지 안이다; `opened` 가 `yes` · `no`.

0 단계: task 파일의 주장 · 결정에 오류 규칙(L2 · L6 · L9) 위반이 있으면 어떤 응답도 자격이 없고, `plan-import` 는 — `--apply` 든 `--discard` 든 —
아무것도 옮기지 않고 상태도 바꾸지 않는다 (`status: error`, `error_code: plan_lint_error`, rc 1).

### 8.2 입장

| 응답의 결정 줄 | 입장 |
|---|---|
| `value` ≠ `default` | `<value>` (`opened` 와 무관) |
| `value` = `default`, `opened: yes` | 기본값 |
| `value` = `default`, `opened: no` | 없음 |

### 8.3 유효 응답

자격 있는 보관 응답 중 응답자마다 `received_at` 이 가장 늦은 하나. `received_at` 까지 같으면 파일 내용의 sha256 이 큰 것.
같은 응답자의 앞 응답은 세지 않는다. 거둔 응답(`.rejected.md`)은 처음부터 없던 것이다 — 뒤 응답을 거두면 앞 응답이 다시 유효해진다.
"대체됨" 은 파일명에 적지 않고 매번 계산해 보고한다.

### 8.4 다툼

유효 응답 P 가 어떤 결정에 입장 `s` 를 밝혔고 다음 중 하나면 P 는 다툼에 든다:

1. 그 결정이 `answered:<v>` 이고 `v` ≠ `s`.
2. 그 결정이 `answered` 가 아니고, 다른 응답자의 유효 응답(다툼 1 로 물린 것도 포함)이 그 결정에 입장 `s'` ≠ `s` 를 밝혔다 — 둘 다 다툼에 든다.

다툼에 든 응답은 **파일 전체**의 입장을 채택하지 않는다.

### 8.5 상태

다툼에 들지 않은 유효 응답의 입장을 결정별로 모은다. 위에서부터 처음 맞는 행:

| 그 결정 | 결과 |
|---|---|
| `answered:<v>` | 그대로 |
| 다툼 2 가 걸렸다 | `disputed` |
| 모인 입장이 기본값 | `kept` |
| 모인 입장이 `<value>` (기본값 아님) | `changed:<value>` |
| 모인 입장이 없고 유효 응답이 하나라도 있다 | `unopened` |
| 유효 응답이 없다 | `proposed` |

### 8.6 다시 계산하는 때

입력이 바뀌는 쓰기는 같은 쓰기 안에서 그 task 의 모든 결정을 다시 계산해 상태 칸에 적는다: `plan-import --apply`(보관 · 거둠),
`backlog-update --decision-state`, 지문을 바꾸는 `backlog-update`, 그리고 `--apply` 가 붙은 그 밖의 `backlog-update` 쓰기.
게이트(§4)와 `plan-status` 는 칸을 읽지 않고 계산한다.

- 지문을 바꾸는 쓰기 뒤에는 옛 지문의 응답이 자격을 잃는다 — 새 지문에 맞는 보관 응답이 없으면 `answered` 가 아닌 결정은 `proposed` 가 된다.
  `answered` 는 값이 새 선택지 안에 있으면 유지하고 `질문이 바뀌었다 — answered 를 유지했다` 를 경고한다.
- `--decision-state D<n>=proposed` 는 `answered` 를 걷는다. 걷는 그 쓰기가 다시 계산하므로 결과가 `proposed` 가 아닐 수 있다.
- 다툼을 끝내는 길은 셋이다: `--decision-state D<n>=answered:<value>` · 응답자의 새 응답 · `plan-import --discard`.
- task 파일이 오류 규칙(L2 · L6 · L9)을 어긴 동안에는 **상태 칸을 다시 적지 않는다**. 게이트와 `plan-status` 는 그동안에도 계산한다 —
  0 단계로 응답이 전부 자격을 잃은 채로. 그리고 → `done` 은 거부된다 (§4).

## 9. `plan-import` (R6 · R7)

```
python -m workflow_kit plan-import --task=<TASK-ID> [--response=<파일>] [--apply]
python -m workflow_kit plan-import --discard=<파일> --reason=<사유> [--apply]
```

- 기본은 dry-run 이다 — 무엇을 옮기고 어느 칸이 바뀔지를 JSON 으로 낸다. 모르는 인자는 거절한다 (argparse, 접두 축약 없음).
- `--response` 를 생략하면 그 task 의 받은편지함 전부를 `received_at` 순(같으면 번호 순)으로 본다. 지정하면 그 파일만 옮기고, 상태는 옮긴 뒤의
  보관 집합으로 계산한다 — 받은편지함의 자격 있는 응답을 전부 옮기고 나면 어느 순서로 불렀든 같은 상태다.
- `--apply` 가 하는 일은 셋이다: ① 자격 있는 받은편지함 응답을 보관으로 옮긴다 (§7-5) ② §8 로 다시 계산해 상태 칸을 적는다
  ③ task `Progress` 에 한 줄 — `plan 응답 n건 (<응답자들>): 결정 3 (바뀜 1 · 유지 1 · 미열람 1 · 다툼 0) · 주석 2 · 대체 0 — <보관 경로들>`.
  주석은 반영하지 않는다 (D4).
- **자격 없는 응답**은 옮기지 않고 파일별 결과로 단계 번호(§8.1)와 사유를 낸다. 받은편지함에 남는다. 다른 응답의 판정에 영향이 없다.
- **`--discard`** 는 받은편지함 또는 보관의 응답을 `.rejected.md` 로 옮기고(§7-5), 다시 계산하고, Progress 에 사유 한 줄을 남긴다.
  task 파일이 오류 규칙을 어긴 동안에는 `--discard` 도 하지 않는다 (§8.1 의 0 단계 — 아무것도 옮기지 않고 `status: error`, rc 1).
  먼저 task 파일을 고친다. 거부된 명령은 아무것도 바꾸지 않으므로, 고친 뒤 다시 부르면 처음 부른 것과 같다.
  응답을 지우는 명령은 없다.
- 응답 이동 없이 칸만 바뀌어도 Progress 에 한 줄을 남긴다 — `결정 상태 재계산: D2 changed:x → proposed`.
- task 의 상태(`status`)는 건드리지 않는다. `done` 인 task 도 받는다.
- dry-run 이 예고하는 보관 이름 · Progress 는 `--apply` 가 실제로 놓는 것과 같다 — 같은 번호를 여러 파일이 쥐어도(`-5.md` 와 `-5.rejected.md`, `-05.md` 와 `-5.md`).
- dry-run 은 잠금을 쥐지 않고 받은편지함 디렉터리도 만들지 않는다. 읽기만 하는 명령(`plan-status` · 게이트 · `session-start`)도 만들지 않는다.
- `--response` 는 그 task 의 받은편지함 파일이어야 하고, `--discard` 는 받은편지함 또는 보관의 `<TASK-ID>-<숫자>.md` 여야 한다 (이미 거둔
  `.rejected.md` 는 다시 거두지 않는다). `--discard` 에는 글자 · 숫자가 있는 `--reason` 이 필요하다. 어긋나면 rc 2 로 거절하고 아무것도 바꾸지 않는다.
- 출력의 `outcome` 은 `imported` · `discarded` · `nothing_to_do` · `import_busy` · `dry_run` 중 하나다.
- 출력 계약 family `plan_import` 를 등록한다.

## 10. `plan-status`

```
python -m workflow_kit plan-status --task=<TASK-ID> [--format=json|md]
```

읽기 전용이다. 내는 것: 1단계 주장마다 자신 · 후손을 인용한 완료 기준의 번호 목록(없으면 "재지 않는 주장" — L7 과 같은 판정), 결정마다
계산한 상태와 칸의 값(다르면 둘 다), 열린 결정 목록, 받은편지함 건수와 파일별 자격(처음 어긋난 단계), 알 수 없는 받은편지함 파일, 다툼에 든 · 대체된 응답. `md` 형식은 검증 보고에 붙일 표다:

```
### 주장별

| 주장 | 기준 | 판정 |
|---|---|---|
| C1 <문장> | #1, #3 | |
| C2 <문장> | — | 재지 않는 주장 |

- 열린 결정: D1 (proposed)
```

판정 칸은 비어 있다 — 채우는 것은 검증하는 쪽이다. 주장이 없는 task 는 이 절을 내지 않는다. 출력 계약 family `plan_status` 를 등록한다.

검증의 최종 판정 규칙은 바뀌지 않는다: "닫아도 된다" 는 모든 완료 기준이 PASS 일 때뿐이다. "재지 않는 주장" 과 열린 결정은 그 옆에
**따로** 센다 — 주장은 완료 기준을 대체하지 않는다 (D3). 2 · 3단계 주장을 인용한 기준은 1단계 조상에 묶는다.

## 11. 생성물 · 보고 · 이어받기 (R9 · R10)

- **`state.json`**: `open_decisions: {"<TASK-ID>": n}` — `in_progress` · `blocked` · `planned` task 중 **상태 칸 기준** 열린 결정이 있는 것만.
  비어 있으면 키를 내지 않는다. 주장 · 결정 전문은 싣지 않는다. 생성기의 입력은 늘지 않는다 (task 파일뿐).
- **받은편지함 건수**는 `state.json` 에 싣지 않는다. `session-start` 와 `backlog-update` 가 명령 시점에 세어 `warnings` 에 싣는다 —
  `계획 응답 n건 미반영 (<TASK-ID> …) — plan-import 로 확인`. 응답의 내용은 싣지 않는다.
- **지문을 바꾸는 쓰기**는 받은편지함에 그 task 의 응답이 있으면 `받은편지함 n건이 옛 계획에 대한 것이다 — plan-import --discard` 를 경고한다.
- **이어받기**: `seed` 가 `inherited_from` 으로 옮기는 task 마다 모 브랜치의 보관 응답(`plan_responses/<TASK-ID>-<숫자>.md`, `.rejected.md` 제외)을
  함께 복사한다. 받은편지함은 옮기지 않는다. 합류 반영이 task 를 이월할 때도, 이어받은 task 를 원본 쪽에 되돌려 적을 때도 같다
  (브랜치에서 보관한 응답이 task 와 함께 돌아간다). 같은 이름이 이미 있으면 덮지 않는다.
  되돌려 적기는 **거둠도 나른다**: 브랜치에서 거둔 응답과 내용이 같은 원본 쪽 보관 응답을 `.rejected.md` 로 옮긴다 (§7-5).
  단 브랜치가 같은 내용을 보관에도 들고 있으면(거뒀다가 다시 받아들였거나, 같은 응답 둘 중 하나만 거뒀다) 거두지 않는다 —
  거둔 응답은 처음부터 없던 것이므로(§8.3), task 만 돌아가면 브랜치에서 `proposed` 로 되돌린 결정이 원본 쪽에서 다시 닫힌다.
  반대 방향(모 브랜치가 seed 뒤에 거둔 응답)은 나르지 않는다 — 이어받은 사본은 seed 시점의 것이다. 브랜치 합류 아카이브는 `plan_responses/` 를
  브랜치 디렉터리의 다른 파일과 같게 다룬다 — 별도 규칙이 없다.
- **정본**: `global_workflow_standard.md` §11.1 에 `Apply plan responses | python -m workflow_kit plan-import`, §1 의 계획 문장에
  `claims, open decisions` 와 "A decision the owner has not opened is not agreed — never close a task with open decisions." 한 줄.
- **스킬**: `plan-import` 하나 (bootstrap 채널의 slash command `/workflow-plan-import` 도 같은 본문이다). **verifier**: `plan-status --format=md` 의 출력을 보고에 붙인다.
- **`backlog_update_skill_spec.md`**: 필드 · 린트 · 게이트의 정본은 이 문서다. 그 스펙에는 새 인자 넷(§2.5)과 이 문서로의 포인터만 더한다 — 규칙을 두 곳에 적지 않는다.

## 12. 검증 (R11)

**모든 case 는 되주입으로 red 를 확인한다** — 판정이 보는 코드를 한 군데씩 되돌려 그 case 가 실제로 떨어지는지 본다.

| 검사 | case |
|---|---|
| `check_plan_claims.py` | 파서(주장 3단계 · 결정 칸 · 별칭 표기) · L1~L10 각각의 최소 위반(오류 규칙은 `--apply` 가 쓰지 않고, 경고 규칙은 쓴다) · 지문(상태만 바꾸면 같고 그 밖은 다르다) · 기존 task 파일 전수에서 필드 값과 `state.json` 무변화 · `PLAN_FIELD_KEYS` 가 유일한 Plan 키 목록 · **파서 단일성** — 린트 · 게이트 · `plan-status` · `plan-import` · state 생성기가 `common/plan_claims.py` 의 같은 함수를 부르고 다른 구현이 없다 (import 대조) · **`plan-status`** — 주장 · 인용 · 열린 결정이 있는 fixture 의 출력이 기대 표와 같고, 주장이 없는 task 는 절을 내지 않고, "재지 않는 주장" 집합이 L7 의 것과 같다 |
| `check_plan_decision_state.py` | §8 을 상태 기계로 전수 탐색 — 도착 · import(일괄 / 하나씩) · discard · `answered` 적기 · 걷기 · 손 편집의 모든 끼워 넣기에서 끝 상태 1종 · 재실행 멱등 · `done` 판정의 순서 무관(지문이 고정된 동안) · 입장 세 행 · 다툼 두 조건 · 상태 여섯 행이 각각 한 번 이상 발화 · 다툼에 든 입장이 채택된 채 닫히는 경로 0. 집합: {a x, b y} · {a x, b x, b y(뒤)} · {a x, a y(뒤)} ± discard · {a x, a 입장 없음(뒤)} · {a x 반영 뒤 discard} 와 {discard 뒤 import} · {a x(D1) · p(D2)} + `answered D1=y` · 3인 · 자격 없는 파일 섞임 · 같은 `received_at` |
| `check_plan_gate.py` | 오류 규칙이면 `--apply` 무변경 · 주장만 있고 L2 를 어긴 task 의 → `done` 거부 · 오류 상태 파일의 진행 메모 update 는 통과하되 칸을 건드리지 않는다 · 거부된 `done` 의 칸 불일치 경고 · → `in_progress` 경고 · → `done` 거부 셋(열린 결정 세 상태 각각 · 받은편지함 · 오류 규칙 위반) · `answered` 뒤 통과 · 결정이 없는 task 는 열린 결정 · 받은편지함 행의 영향을 받지 않는다 · 손 편집 `kept` 뒤 `done` 거부와 → `in_progress` 의 칸 고쳐 쓰기 · `--decision-state D1=kept` 거부 · 사유 없는 열린 결정 제거 거부 · `done` + `proposed` 의 `refresh-state` warning |
| `check_plan_import.py` | §8.1 의 0~6 단계마다 어긋난 응답 → 무변경 · 0 단계에서는 `--discard` 도 무변경(rc 1)이고 task 를 고친 뒤 같은 호출이 통한다 · 정상 응답의 보관 · Progress 한 줄 · `--discard` · 잠금을 못 쥔 쪽의 `import_busy` · 쓰는 쪽 × 옮기는 쪽 둘에서 중복 0 · 유실 0 · `inbox/.gitignore` 자기 무시 · 이어받기가 보관 응답을 옮긴다 |

경합 · 계산의 되주입 예: 배타 생성 제거 · 평범한 rename · 잠금 무력화(확률적 — 정한 회수 안에 1 회 이상) · 상태 칸을 입력으로 읽기 · 다툼에 든 응답의 부분 채택 ·
게이트가 칸으로 판정 · 받은편지함을 보지 않는 게이트.

## 13. requirements 대응

| requirements | 이 문서 | 비고 |
|---|---|---|
| R0 | §1 | |
| R1.1 · R1.2 | §2.1 | Plan 키 목록을 하나로 (ADR-031 V7) |
| R1.3 | §2.2 | |
| R1.4 | §2.3 | 칸 이름의 쓰기 표기를 영어로 (ADR-031 V2) |
| R1.5 | §2.4 | |
| R1.6 | §2.5 | |
| R2.1 · R2.2 · R2.3 | §3 | 오류 상태 파일은 칸을 다시 적지 않고 `done` 을 거부 (ADR-031 V9) |
| R3.1 · R3.2 · R3.3 · R3.4 | §4 | |
| R4 | §10 | 묶음은 `plan-status` 의 출력 (ADR-031 결정 4), 최종 판정 규칙 불변 |
| R5.1 · R5.3 | §6 | |
| R5.2 | §5 | |
| R6.1 · R6.4 · R7 | §9 | Progress 는 호출당 한 줄 (ADR-031 V6) |
| R6.2 | §8.1 | |
| R6.3 | §8.2~§8.6 | 유효 응답은 자격을 다시 본 것만 (ADR-031 V8) |
| R8.1 · R8.2 · R8.3 | §7 · §9 | 번호를 시각 기반으로 (ADR-031 V1) |
| R9.1 · R9.2 | §11 | |
| R10 | §6 · §11 | MCP 도구는 ADR-032 로 (ADR-031 V3). `backlog_update_skill_spec` 에는 포인터만 (V10). 텍스트 I/O 인코딩은 §6 |
| R11 | §12 | |
| R12 · R13 | — | design 진입 조건과 남은 실측 — ADR-031 Context 의 실측 표 |
