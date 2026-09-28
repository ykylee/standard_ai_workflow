# 세션 시작 컨텍스트 예산 스펙

- 문서 목적: 세션을 열 때 읽는 문서의 섹션별 바이트 예산, 초과 시의 출구, 옮긴 뒤 잃지 않았음을 재는 판정을 kit 계약으로 정의한다.
- 범위: 예산 레코드와 정본 위치, handoff §5 현재형/누적형 계약, 이관 도구 계약, `state.json.memory_entries` 포인터 스키마, `CLAUDE.md` 이관, 강도(소비자 warn / 이 저장소 red), 구현 단계
- 대상 독자: workflow 설계자, AI agent, kit 소비 프로젝트
- 상태: active (ADR-029 accepted, M-017 구현 완료 2026-09-28)
- 최종 수정일: 2026-09-28
- 관련 문서: `../../ai-workflow/wiki/decisions/adr-029-session-context-budget.md`, `../../docs/planning/session-context-budget-requirements-2026-09.md`, `./global_workflow_standard.md`

> **결정 근거는 ADR-029 에 있다.** 이 문서는 *계약* 만 적는다.

## 1. 예산 레코드

정본은 `workflow_kit/common/context_budget.py` 하나다. 문서·검사·도구는 값을 다시 적지 않고 import 한다.

| 키 | 대상 | 상한 (바이트) | 강도 | 출구 |
|---|---|---|---|---|
| `handoff_s5_accumulated` | handoff §5 누적형 절의 합 | 8,192 | red | `wk rollover-handoff-notes --apply` |
| `handoff_baseline_line` | handoff §1 기준선 줄 하나 | 3,072 | warn | 상세를 task 파일·세션 기록으로 옮기고 줄을 요약한다 (판단) |
| `state_json` | 브랜치 `state.json` 전체 | 30,720 | red | 생성기 입력을 줄인다 — §1 기준선 줄, memory_index entry 수 |
| `claude_md` | 저장소 루트 `CLAUDE.md` | 12,288 | red | 운영 산문을 `docs/LOCAL_GATE.md` 로 옮긴다 |

개수 상한은 `common/project_docs.py` 에 있다 — `RECENT_DONE_ITEMS_CAP` (§4, 10건) ·
`BASELINE_ITEMS_CAP` (§1, 4줄). 두 부류는 서로 대체하지 않는다: 개수 상한은 한 줄이 커지는 것을 못
막고, 바이트 상한은 항목 수를 말하지 않는다.

상한 값은 requirements sign-off(Q2) 값이며, 구현 후 실측으로 **한 번** 재조정한다.

## 2. handoff §5 — 현재형과 누적형

- 현재형 절: `HANDOFF_S5_CURRENT_SECTIONS` (`context_budget.py`) 에 **이름 접두**로 선언된 절 —
  `▶ 지금 할 일` · `작업 후보` · `소유자 결정 대기` · `환경 상태` · `관찰 축`. 옮기지 않는다.
- 누적형 절: §5 의 그 밖의 `###` 절. 새 절은 위에 쌓는다 (최신이 위).
- 목록 밖의 새 절은 누적형이다. 현재형으로 두려면 목록에 올린다.

## 3. 이관 도구 — `wk rollover-handoff-notes`

- 기본은 계획 출력(dry-run), `--apply` 로 쓴다. 멱등 — 누적형 합이 상한 이하이고 포인터가 정상이면 no-op.
- 누적형 절을 **아래부터** 옮기며, 합이 상한 이하가 되면 멈춘다.
- 대상: `### N차가 남긴 규칙` → 브랜치 디렉터리의 `lessons.md` / 그 밖 → `sessions/handoff-notes_<이관일>.md`.
  대상 파일에는 newest-first 로 **앞에** 붙인다. 블록은 바이트 그대로 옮긴다.
- §5 에는 두 대상을 가리키는 **포인터 줄이 정확히 하나** 남는다. 건수는 대상 파일의 실제 블록 수다.

## 4. `state.json.memory_entries` v2

```json
"schema_version_memory_entries": "2",
"memory_entries": [
  {"id": "MEM-2026-09-23-015", "primary_abstraction": "<120자까지>",
   "path": "ai-workflow/memory/active/memory_index/entries/MEM-2026-09-23-015.json"}
]
```

본문의 정본은 `memory_index/entries/` 다. v1(전문 복제)은 남기지 않는다.

## 5. `CLAUDE.md` 이관

`## 프로젝트 실행 기본값` 절의 근거·실측 산문은 `docs/LOCAL_GATE.md` 로 옮긴다. `CLAUDE.md` 에는
명령(install · run · quick/isolated test · smoke) · 게이트 단계표 · 규칙 한 줄씩 · 그 문서로 가는
링크가 남는다. `## Working Principles` · `## Session Close Order` · `## Memory Update Paths` (생성 블록)
는 이 절의 범위가 아니다.

## 6. 강도

- **kit 소비자**: `wk refresh-state` 가 §1 의 모든 예산을 재고 초과를 warning 으로 낸다 — 출구 명령을
  그대로 싣는다. 게이트를 강요하지 않는다.
- **이 저장소**: `check_session_context_budget` 이 red 강도 예산을 push 게이트에서 잰다. warn 강도
  (`handoff_baseline_line`)는 refresh-state 경고로만 난다.

## 7. '잃지 않음' 판정

| 요구 | 재는 곳 | 판정 |
|---|---|---|
| 무손실 이관 (R4.1) | 이관 도구 fixture test | 옮긴 블록 각각이 대상 파일에 바이트 그대로 있고, §5 에 포인터가 하나 있다 |
| 포인터 역참조 (R4.2) | `check_session_context_budget` | `state.json` 포인터의 `path` 가 존재하고 그 파일의 `id` 가 같다 |
| 링크 생존 (R4.3) | `check_session_context_budget` | `CLAUDE.md` 가 `docs/LOCAL_GATE.md` 를 링크하고, 이관 전 명령표의 명령이 `CLAUDE.md` 에 남아 있다 |

이 판정은 '옮긴 것이 사라지지 않았다' 를 잴 뿐, '다음 세션이 그것을 찾아가는가' 는 재지 않는다.

## 8. 구현 단계

출구 먼저, red 나중 (ADR-029 결정 8 — 지금 저장소는 네 예산 모두 초과다):

1. `context_budget.py` (예산 레코드 + 현재형 목록) + refresh-state warning.
2. D — 생성기 포인터화 (`schema_version_memory_entries` 2).
3. A·B — `wk rollover-handoff-notes` + fixture test (R4.1) + 표준 `Memory Update Paths` 한 줄.
4. E — `docs/LOCAL_GATE.md` 이관.
5. 이 저장소에 이관 실행 → 실측 → 상한 한 번 재조정 (Q2).
6. `check_session_context_budget` 활성 (red).

### 구현 결과 (2026-09-28, 이 저장소)

| 예산 | 구현 전 | 구현 후 | 상한 |
|---|---|---|---|
| handoff §5 누적형 | 39,615 (21절) | 7,851 (4절) — 17절 이관 (규칙 10 → `lessons.md`, 기록 7 → `sessions/`) | 8,192 |
| handoff §1 기준선 한 줄 (warn) | 5,226 | 5,226 | 3,072 |
| `state.json` | 68,822 | 21,409 | 30,720 |
| `CLAUDE.md` | 19,595 | 11,341 | 12,288 |

필독 합 195.1KB → **111.5KB** (추정 ~107KB 와의 차이는 §5 현재형 20.1KB — 예산 밖으로 둔 부분).
**상한 재조정(Q2): 값 유지.** red 셋은 여유 있게 또는 도구가 맞추는 구조로 통과하고, `CLAUDE.md`
의 좁은 여유는 새 산문을 `docs/LOCAL_GATE.md` 로 보내라는 의도된 압력이다. 다음 재조정 후보는
§5 현재형(20KB, 관찰 중)이다.
