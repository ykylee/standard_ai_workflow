# 세션 시작 컨텍스트 예산 — requirements

- 문서 목적: concept 검토의 소유자 결정 **③ 출구 + 예산** 을 요구사항으로 확정한다 — 무엇을 어디로 옮기고, 무엇을 얼마로 제한하며, 옮긴 뒤 잃지 않았음을 무엇으로 재는가 (TASK-2026-09-28-main-011, M-015/WBS-15.1).
- 범위: 이관 대상 A~E 의 출구와 불변 조건, 섹션별 바이트 예산 값과 강도, '잃지 않음' 판정, session-start 절차의 원문 읽기, design 진입 조건
- 대상 독자: 소유자 (sign-off), maintainer
- 상태: **종결 (2026-09-28)** — 소유자 sign-off: Q1~Q5 권고안대로. design 은 M-016
- 최종 수정일: 2026-09-28
- 관련 문서: [`session-context-budget-review-2026-09.md`](./session-context-budget-review-2026-09.md) (concept), [`M-015`](../../ai-workflow/memory/active/roadmap/M-015-session-context-budget-requirements.md), [ADR-006 회고](../architecture/ADR-006-memory-index-retrospective.md) §2

## 0. 요약

| 대상 | 지금 | 출구 | 예산 (제안) | 줄어드는 양 |
|---|---|---|---|---|
| A. handoff §5 "N차가 남긴 규칙" | 31.4KB · 15 블록 | 새 이관 도구 → `lessons.md` (포인터 남김) | §5 누적형 합 ≤ 8KB | A+B 합 ~38.5KB (누적형 46.5 → 8) |
| B. §5 "무엇이 끝났나" · 8월 계획 · 닫힌 안건 | ~15.1KB | 같은 도구 → `sessions/` | (A 와 합산) | (A 에 포함) |
| C. §1 기준선 한 줄 | 줄당 1.3~4.7KB (역대 최대 18KB) | 상세는 task 파일·세션 기록 (warn 만) | 줄당 ≤ 3KB | 흐름 억제 |
| D. `state.json.memory_entries` | 46.9KB · 30 entry 전문 | 생성기가 포인터만 싣는다 | `state.json` ≤ 30KB | ~40.7KB (포인터 형태 실측 6.2KB) |
| E. `CLAUDE.md` "프로젝트 실행 기본값" | 11.9KB | `docs/` 운영 문서로, 명령표·규칙만 남김 | `CLAUDE.md` ≤ 12KB | ~8.6KB (남길 부분 ~3KB 추정) |

필독 195KB → **약 107KB** (195.1 − 38.5 − 40.7 − 8.6. A+B·D 는 실측 기반, E 는 남길 분량 추정. 구현 후 실측으로 확정).

## 1. 불변 조건 (R0)

- **R0.1 이관은 삭제가 아니다.** 옮긴 텍스트는 대상 파일에 **바이트 그대로** 있고, 원래 자리에는
  대상으로 가는 포인터가 남는다 (`wk rollover-baselines` 와 같은 규율).
- **R0.2 `state.json` 은 생성기로만 바뀐다.** D 는 생성기 변경이다.
- **R0.3 생성 블록은 건드리지 않는다.** `CLAUDE.md` 의 `## Working Principles` ·
  `## Session Close Order` · `## Memory Update Paths` 는 `check_standard_single_source` 가 정본과의
  일치를 강제한다. E 는 그 밖의 절만 다룬다.
- **R0.4 push 게이트 전량 2축은 그대로다.** 예산 검사는 게이트에 **추가**될 뿐이다.

## 2. 출구 (R1)

모든 예산 대상에는 **정확히 하나의 출구**가 있고, 예산 초과 메시지는 그 출구를 **명령으로** 가리킨다.

- **R1.1 (A·B) handoff §5 누적형 블록 이관 도구.** §5 의 하위 절을 두 부류로 나눈다.
  - **현재형** — 고정된 이름 목록: `지금 할 일` · `작업 후보` · `소유자 결정 대기` · `환경 상태` ·
    `관찰 축`. 옮기지 않는다 (후보 블록은 `check_handoff_next_steps` 가 대조한다).
  - **누적형** — 그 밖의 `###` 절 (`N차가 남긴 규칙` · `무엇이 끝났나` · 지난 계획 · 닫힌 안건).
    예산을 넘으면 **오래된 것부터** 옮긴다. 규칙은 `lessons.md`, 나머지는
    `sessions/handoff-notes_<날짜>.md` 로.
  - 현재형/누적형 판정은 **이름 목록**으로 한다 — 휴리스틱으로 고르면 현재형을 옮기는
    오판이 난다. 목록 밖의 새 절은 누적형으로 친다 (새 절이 계속 현재형으로 남으려면
    목록에 올려야 한다 = 선언).
- **R1.2 (C) 기준선 줄 바이트 상한.** 넘으면 session-end(`wk refresh-state`)가 warn 한다.
  자동으로 자르지 않는다 — 요약은 판단이다. 상세의 자리는 task 파일(SSOT)과 세션 기록이다.
- **R1.3 (D) `memory_entries` 포인터화.** 생성기가 entry 마다 `id` · `primary_abstraction`
  (앞 120자) · 정본 경로만 싣는다. 본문은 `memory_index/entries/` 가 정본이다. `state.json` 에서
  이 필드를 읽는 코드는 **없다** (2026-09-28 전수 grep — pass-through 를 단언하는 test 1곳뿐,
  `check_memory_index.py`). ADR-006 회고가 이미 "entry 가 수십 건이 되면 state.json 비대의 첫
  후보" 라고 적었다. 스키마 버전(`schema_version_memory_entries`)을 올린다.
- **R1.4 (E) `CLAUDE.md` 운영 절 이관.** "프로젝트 실행 기본값" 절의 **근거·실측 이야기**를
  `docs/` 운영 문서로 옮기고, `CLAUDE.md` 에는 명령표 · 단계표 · 규칙 한 줄씩 · 포인터를 남긴다.
  `CLAUDE.md` 는 대화마다 자동으로 실리므로 바이트당 비용이 가장 크다.

## 3. 예산 (R2)

- **R2.1 단위는 섹션별 바이트다** (concept §4). 토큰은 재지 않는다.
- **R2.2 예산 값의 정본은 한 곳이다** — 코드 상수 하나(모듈은 design 에서)와 그것을 읽는 검사.
  문서에 값을 다시 적지 않는다 (사본은 갈라진다).
- **R2.3 제안 값** (현행 실측 → 상한):

  | 대상 | 현행 | 상한 | 근거 |
  |---|---|---|---|
  | handoff §5 누적형 합 | ~46KB | 8KB | 최근 3~4 세션 분량. 그 이상은 `lessons.md` |
  | handoff §5 현재형 합 | ~19.6KB | 상한 없음, 관찰 | 현재형은 옮길 곳이 없다 — 늘면 후보 정리로 푼다 |
  | handoff §1 기준선 한 줄 | 1.3~4.7KB | 3KB | 역대 중앙 1.8KB · p90 6KB |
  | `state.json` 전체 | 67KB | 30KB | D 적용 후 약 26.6KB (67.3 − 46.9 + 6.2) |
  | `CLAUDE.md` | 19.6KB | 12KB | E 적용 후 약 11KB 추정 |

## 4. 강도 (R3)

- **R3.1 출구가 있는 예산은 push 게이트 red** 다 — A·B(§5 누적형), D(`state.json`), E(`CLAUDE.md`).
  red 메시지는 출구 명령을 싣는다. 8/08 의 손 압축이 7주 만에 되돌아간 것은 **아무것도
  막지 않았기** 때문이다 (concept §2.5). 재는 것이 없던 §5 는 한 번도 줄지 않았고, 줄 수
  상한으로 재던 §1 만 줄었다.
- **R3.2 출구가 판단인 예산은 warn** 이다 — C(기준선 한 줄). 자동 이관 수단이 없는데 red 를
  걸면 요약을 억지로 줄이게 되고, 그것은 '고친 것 없이 숫자만 좋아진다' 이다.

## 5. '잃지 않음' 판정 (R4)

- **R4.1 A·B 이관은 무손실이다** — 검사가 옮긴 블록 각각이 대상 파일에 바이트 그대로 있고,
  원래 자리에 그 대상을 가리키는 포인터가 있는지 잰다. (`check_handoff_baseline_cap` 이
  rollover 에 대해 하는 것과 같은 모양.)
- **R4.2 D 는 역참조 가능하다** — `state.json` 의 포인터마다 `memory_index/entries/<id>.json` 이
  존재하고 `id` 가 같다. 없는 포인터는 red.
- **R4.3 E 는 링크가 살아 있다** — 옮긴 절의 제목이 대상 문서에 있고 `CLAUDE.md` 가 그 문서를
  링크한다. 명령표의 명령은 그대로 남는다 (`CLAUDE.md` 의 명령 목록을 이관 전후로 대조).
- **R4.4 한계를 적어 둔다.** 위 셋은 '옮긴 것이 사라지지 않았다' 를 잴 뿐, '다음 세션이 그것을
  필요로 할 때 찾아가는가' 는 재지 못한다 (concept §3·§7). 그 판정은 이 단계 범위 밖이다.

## 6. session-start 절차 (R5)

session-start 스킬은 `state.json` · handoff · backlog · PROFILE · PURPOSE 를 **원문으로** 읽으라고
지시하고, 도구 출력은 16KB 다 (concept §2.6). **이번 범위에서 절차는 바꾸지 않는다** — A~E 로
원문 자체가 줄고, 스킬 문서는 플러그인 페이로드라 바꾸면 발행 사이클을 탄다. 재검토 조건:
A~E 적용 뒤에도 필독 합이 예산 합을 넘을 때.

## 7. design 진입 조건 (R6)

- §8 미결 5곳의 소유자 결정.
- design 은 다음을 정한다: 예산 상수 모듈 위치 · 이관 도구 CLI(`wk` 명령 이름) · 현재형 절
  이름 목록의 정본 위치 · `state.json` 스키마 버전 이행 · `CLAUDE.md` 이관 대상 문서 경로.

## 8. 미결 — 소유자 결정 (권고 포함)

| # | 질문 | 권고 |
|---|---|---|
| Q1 | 이번 범위 | **A+B+D+E** (C 는 warn 만 같이). 필독 195KB → ~107KB |
| Q2 | §2.3 상한 값 | 제안 값 그대로 — design·구현 뒤 실측으로 한 번 재조정 |
| Q3 | 강도 | §4 대로 — 출구 있는 것 red, C 만 warn |
| Q4 | A 의 대상 파일 | 규칙은 `lessons.md`(브랜치 디렉터리, 누적) · 나머지는 `sessions/` |
| Q5 | session-start 절차 변경 | 이번 범위 밖 (§6) |

## 9. sign-off 기록

**2026-09-28, 소유자 — Q1~Q5 권고안대로 승인.**

- Q1 범위 = A+B+D+E, C 는 warn 만.
- Q2 상한 = §2.3 제안 값 (§5 누적형 8KB · 기준선 한 줄 3KB · `state.json` 30KB · `CLAUDE.md` 12KB),
  구현 뒤 실측으로 한 번 재조정.
- Q3 강도 = 출구 있는 A·B·D·E 는 push 게이트 red, C 는 warn.
- Q4 A 대상 = 규칙은 `lessons.md`, 나머지는 `sessions/`.
- Q5 session-start 절차 변경 = 이번 범위 밖.

design 은 [`M-016`](../../ai-workflow/memory/active/roadmap/M-016-session-context-budget-design.md) 으로
이어진다 — §7 의 다섯 항목(예산 상수 모듈 · 이관 도구 CLI · 현재형 절 이름 목록의 정본 ·
`state.json` 스키마 이행 · `CLAUDE.md` 이관 대상 경로)을 ADR 과 core 스펙 절로 정한다.
