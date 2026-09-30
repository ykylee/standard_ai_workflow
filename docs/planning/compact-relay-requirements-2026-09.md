# compact 중계 — requirements

- 문서 목적: concept 검토의 소유자 결정(안 B)을 받아, compact 중계의 불변 조건 · 명령 계약 · checkpoint 형식 · 재주입 예산 · '잃지 않음' 판정 · 스킬/hook 범위 · 수명 · 검증을 요구사항으로 고정한다 (M-019/WBS-19.1).
- 범위: `wk` 명령 1개 신설(정본 §11.1), 플러그인 스킬 1 · hook 3, checkpoint 파일 계약, 재주입 출력 계약, 검사
- 대상 독자: 소유자 (sign-off), design 단계 작성자
- 상태: **종결 (2026-09-30)** — 소유자 sign-off: Q1~Q3 권고안대로 (§11). design 은 M-020
- 최종 수정일: 2026-09-30
- 관련 문서: [`compact-relay-review-2026-09.md`](./compact-relay-review-2026-09.md) (concept, §9 결정), [`M-019`](../../ai-workflow/memory/active/roadmap/M-019-compact-relay-requirements.md), [`session_context_budget_spec.md`](../../workflow-source/core/session_context_budget_spec.md), [`plugin_payload.py`](../../workflow-source/workflow_kit/plugin_payload.py)

## 0. 요약

압축 **전**에 checkpoint 를 기록하고(스킬 = 판단 층, `PreCompact` = 기계 층), 압축 **뒤**
`PostCompact` 요약과 대조해 빠진 식별자를 세고, `SessionStart(compact)` 로 **4KB 이하**의 상태
기록을 재주입한다. checkpoint 는 워크트리 로컬 · gitignore · 커밋하지 않는다. 명령은
`wk compact-checkpoint` 하나에 모드를 둔다 (§2, Q1).

## 1. requirements 착수 실측 (2026-09-30, Claude Code 2.1.285, 이 호스트)

concept §8 이 남긴 미실측 셋 중 둘을 닫았다. 모두 `claude -p` + `--plugin-dir` 임시 플러그인.

| 항목 | 결과 |
|---|---|
| **플러그인 배포 hook** 의 `PreCompact` · `PostCompact` · `SessionStart(matcher=compact)` | 셋 다 발화 — `--settings` hook 과 같은 입력 (concept §2.1 ①~③) |
| matcher `startup` / `compact` 분리 | 서로 섞이지 않는다 — startup hook 은 첫 실행에만, compact hook 은 압축 뒤에만 |
| **hook 출력 인라인 상한** | **≈10,000 자** (ASCII 9,990 자 인라인 · 10,010 자 초과). **문자 수**다 — 한글 9,900 자(29.7KB) 도 인라인 |
| 상한 초과 시 | 조용히 잘리지 않고 `<persisted-output>` — 전체를 파일로 저장하고 **앞 2KB 미리보기만** 컨텍스트에. 끝 부분(다음 한 걸음 등)은 모델이 못 본다 |
| 자동 압축(`trigger: auto`) | **미실측** — headless 에서 한계까지 채우기 어렵다. design 단계에서 대화형으로 1회 잰다 (R9) |

→ 예산 4KB 초안은 상한과 2.4배 이상 떨어져 있다 (4,096 바이트 ≤ 4,096 자). **확정한다** (R3).
상한 초과의 실패 양상이 "앞만 보인다" 이므로, 재주입 본문은 **중요한 것부터** 쓴다.

## 2. 명령 계약 (R1)

정본 §11.1 에 한 줄: `Relay working state across a compaction: wk compact-checkpoint`.

| 모드 | 호출자 | 입력 | 동작 |
|---|---|---|---|
| `--note` | 스킬 (모델) | `--verified` · `--unverified` · `--rejected` · `--next` (반복 가능 인자) | 판단 층을 `current.md` 에 쓴다. 기존 판단 층은 **대체** (누적 아님 — 최신 판단이 정본) |
| `--hook pre` | `PreCompact` | stdin JSON | 기계 층을 수집해 합친다. `session_id` · `trigger` · `custom_instructions` 기록 |
| `--hook post` | `PostCompact` | stdin JSON | `compact_summary` 를 `summary.md` 로 보관, 누락 식별자 계수 (R4) |
| `--restore` | `SessionStart(compact)` | stdin JSON | 재주입 본문을 stdout 으로 (R3) |
| `--clear` | 세션 종료 스킬 | — | `.compact/` 를 비운다 |

- hook 모드는 **항상 exit 0** 이다 — 실패는 stdout/stderr 한 줄로 말하고 세션을 막지 않는다.
  `wk` 부재는 기존 hook 과 같은 안내문을 쓴다 (명령 문자열은 §11.1 파생).
- 모르는 인자는 거절한다 (기존 CLI 규약).
- **모델 호출 없음.** 모든 모드는 결정적이다.

## 3. checkpoint 형식과 위치 (R2)

- 경로: `ai-workflow/memory/active/<branch>/.compact/current.md` (+ `summary.md`). 브랜치 해석은
  기존 branch-scoped 규약을 그대로 쓴다.
- `.gitignore`: `ai-workflow/memory/active/*/.compact/` — 이 저장소와 bootstrap 이 심는 `.gitignore` 양쪽.
- frontmatter: `session_id` · `branch` · `head` · `created` · `updated` · `trigger` · `layers`(`mechanical` / `judgment`).
- 본문 절 (고정 순서 = 재주입 우선순위): ① 다음 한 걸음 ② 미검증 ③ 진행 중 · 차단 task ④ 검증됨 ⑤ 기각한 안
  ⑥ 미커밋 파일 · 현재 WBS · `/compact` 지시문.
- 기계 층 출처는 SSOT 만: task 상태는 `backlog/tasks/` frontmatter, WBS 는 `roadmap_state.json`,
  파일은 `git status --porcelain`. `session_handoff.md` · `state.json` 은 **읽기만** 하고 쓰지 않는다.
- transcript 는 읽지 않는다.

## 4. 재주입 (R3)

- 머리말 한 블록 (항상 포함, ≤ 400 바이트): 출처(`compact-checkpoint`), `trigger`, 판단 층 유무
  ("없음 — 자동 압축" 을 **명시**), checkpoint 나이, 요약 누락 N개, 전체 파일 경로.
- 머리말 문구는 **상태 기록**으로 쓴다 — "다음을 하라" 가 아니라 "압축 직전 기록된 작업 상태".
- 본문은 §3 순서대로 채우다가 **4,096 바이트**에서 멈추고 "생략 N절 — 전체는 <경로>" 로 닫는다.
- `session_id` 가 입력과 다르면 본문 없이 머리말 + "다른 세션의 checkpoint — 넣지 않음" 만.
- checkpoint 가 없으면 **출력 없음** (조용함이 정상인 유일한 경우 — 압축 전 기록이 없었다).
- 예산 레코드를 `session_context_budget_spec` §1 에 추가한다 (강도: 코드 상한 — 넘길 수 없게 자른다).

## 5. '잃지 않음' 판정 (R4)

- 식별자형 항목만 대조: `TASK-\d{4}-\d{2}-\d{2}-[a-z0-9-]+-\d{3}` · `M-\d{3}` · `WBS-[\d.]+` · 백틱 안 경로 ·
  7~40자 hex sha · 미검증 절의 백틱 토큰.
- 누락 = checkpoint 에 있고 `compact_summary` 원문에 부분 문자열로 없는 것. 자연어는 대조하지 않는다.
- 결과는 `summary.md` frontmatter 에 `missing_count` · `checked_count` · `missing[]`, 재주입 머리말에 숫자.
- `checked_count = 0` 이면 "대조 대상 없음" 으로 적는다 — 0 누락과 구분한다.

## 6. 스킬 `compact` (R5)

- 플러그인 스킬 5번째. description 은 KO/EN 이중 (기존 규약). 트리거: "compact 전에", "컨텍스트가 길다", `/compact` 예정.
- 절차: ① `--note` 로 판단 층 기록 (미검증을 검증됨과 섞지 않는다) ② 붙여 넣을 한 줄 제시:
  `/compact Preserve the items in ai-workflow/memory/active/<branch>/.compact/current.md verbatim, especially unverified ones.`
  ③ 압축 뒤 첫 응답에서 재주입 머리말을 확인하고, 누락 N>0 이면 그 항목을 사용자에게 한 줄로 알린다.
- 스킬은 `/compact` 를 실행하지 못한다 — 실행은 사용자다 (문서화).
- `session-end` 스킬 본문에 한 단계: checkpoint 중 handoff 에 남길 줄을 옮기고 `--clear`.

## 7. hook 과 하네스 (R6)

- `render_claude_code_hooks` 에 `PreCompact`(matcher 없음 — manual/auto 모두) · `PostCompact` · `SessionStart(matcher=compact)` 추가.
  같은 JSON 이 `hooks/hooks.json`(Grok 사본)으로도 나간다.
- 기존 matcher 없는 `SessionStart` hook 두 개(`wk` 부재 안내 · 규칙 블록 조건부 주입)는 압축 뒤에도 돈다 — 그대로 둔다
  (규칙 3.0KB + 재주입 ≤4KB = 7KB, 상한 아래).
- 하네스 선언 표 (문서 + `plugin_payload` 주석):

| 하네스 | 스킬 | 기록 hook | 재주입 | 근거 |
|---|---|---|---|---|
| Claude Code | ✅ | ✅ | ✅ | 실측 (§1) |
| Grok Build | ✅ | 수동적 (무해) | ❌ SessionStart stdout 무시 | 공식 문서 — 선언만 |
| Codex | ✅ | 미실측 — manifest 에 hooks 없음 | 미실측 | 이번 범위 밖, 별도 leaf |
| Antigravity | ✅ | ❌ | ❌ | 압축 이벤트 없음 |

## 8. 불변 조건 (R0)

1. `session_handoff.md` · `state.json` 은 이 기능이 **쓰지 않는다**.
2. `.compact/` 는 커밋되지 않는다 — gitignore 누락은 검사가 red.
3. 재주입은 4,096 바이트를 넘지 않는다.
4. hook 은 세션을 막지 않는다 (exit 0).
5. 생성 규칙 블록은 정본 §11.1 개정으로만 바뀐다 (`check_standard_single_source`).

## 9. 검증 (R7) · design 진입 조건 (R8) · 남은 실측 (R9)

**R7 검사** (`check_compact_relay.py`, 각 case 결함 되주입으로 red 확인):
재주입 4KB 절단과 우선순위 · `session_id` 불일치 무본문 · checkpoint 부재 무출력 · 누락 계수(0 누락 / 대조 대상 없음 구분) ·
`--note` 대체 의미 · handoff/state.json 무변경 · hook JSON 이 §11.1 파생 · gitignore 포함 · hook 모드 exit 0.

**R8 design 진입 조건**: 이 문서 sign-off + Q1~Q3 결정.

**R9**: 자동 압축 경로 1회 실측(대화형) · Codex 플러그인 hook 적재 실측은 별도 leaf.

## 10. 미결 — 소유자 결정 (권고 포함)

| # | 질문 | 권고 |
|---|---|---|
| Q1 | 명령 하나(모드) vs 여럿 | **하나** — §11.1 에 한 줄, 스킬 1:1 규약 유지 |
| Q2 | 자동 압축에서도 기록 hook 을 도는가 | **돈다** — 기계 층만이라도 남기고, 판단 층 부재를 머리말에 명시 |
| Q3 | 오래된 checkpoint (다른 날 / HEAD 다름) | **머리말에 나이·HEAD 차이 표시 후 본문은 넣는다** — 같은 `session_id` 면 같은 작업이다 |

## 11. sign-off 기록

2026-09-30 (107차) 소유자 sign-off — **Q1~Q3 권고안대로**: 명령 하나(모드) · 자동 압축에서도 기록 hook
(기계 층만, 판단 층 부재 명시) · 오래된 checkpoint 는 나이·HEAD 차이를 머리말에 표시하고 본문은 넣는다.
design 단계는 [`M-020`](../../ai-workflow/memory/active/roadmap/M-020-compact-relay-design.md) 으로 이어진다.
