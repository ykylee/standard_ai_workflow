# 9차 세션 — §11 단일출처 검사 강화 (2026-08-12)

- 문서 목적: TASK-2026-08-11-main-026 종결 기록.
- 상태: done
- 관련: [TASK-026](../backlog/tasks/TASK-2026-08-11-main-026.md), [6차 세션 기록](./state_generated_and_composition_review_2026-08-11.md) §4.1

## 요약

§11.1 명령 문자열의 **손 사본 7곳이 정본 파생으로** 바뀌고, 검출기·분류 단언·자기
적용 탐침이 그 상태를 고정한다.

| 변경 | 내용 |
|---|---|
| `find_memory_command` 신설 (`standard_rules.py`) | 정본 §11.1 표에서 목적 키워드로 명령 추출. 실패 시 `StandardParseError` (조용한 기본값 없음) |
| 렌더러 7곳 정본 파생 전환 | claude-code command 3종 (`wk X --help`) + goose entry_points 3곳 + goose hook |
| goose `on_session_end` 수정 | 존재하지 않는 `ai-workflow/skills/.../run_session_start.py --update-handoff` → `wk refresh-state` (§11.1 종료 명령 — TASK-022 가 entry_points 만 갈고 놓친 잔여) |
| `_rule_literals` 확장 | §11.1 명령 + §11.2 계약 bullet 을 검출 대상에 추가 — 사각지대였던 7곳 부활 시 case 2 가 잡는다 |
| case 8 신설 | `PRIMARY ∪ EXEMPT == SUPPORTED_HARNESSES` 단언 — 미분류(`mavis` 가 그랬다)·유령 분류·중복 분류 검출. `mavis` 는 EXEMPT (project-local 산출물 0) |
| `check_self_application` §11 탐침 | 루트 진입점(§1/§8 만 보던)에 §11 명령 + 계약 탐침 추가 — 낡은 루트 `AGENTS.md` (§11 이전 마커, §1 6/8) 를 실측으로 잡아 재생성 |

검증: `check_standard_single_source` 7→**8 case** 8/8 + `check_self_application` 8/8.
**되주입 3종 실증** — ① 렌더러를 구버전(손 사본)으로 되돌리면 case 2 FAIL,
② AGENTS.md 에서 §11 을 지우면 self_application FAIL, ③ detector 에 명령/계약/종료
순서 사본을 주입하면 3종 모두 탐지. 전량 2축 250/250 ×2 green.

## 교훈

- **검출기의 범위는 정본의 범위를 따라가야 한다** — §11 을 정본에 신설(TASK-022)할 때
  검출기(`_rule_literals`)를 같이 넓히지 않아, 새 규칙의 사본 7곳이 처음부터
  사각지대에서 태어났다.
- **순회 대상이 손 목록의 합집합이면, 합집합 == 레지스트리 단언이 따로 필요하다** —
  없으면 새 등록이 조용히 빠져나간다 (mavis).
