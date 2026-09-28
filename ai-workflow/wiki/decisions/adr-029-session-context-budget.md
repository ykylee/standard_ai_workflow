---
type: decision
status: accepted
adr_id: ADR-029
decided_at: 2026-09-28
alternatives_considered: [extend-rollover-baselines, budget-in-project-docs, embed-memory-entries-truncated, keep-claude-md-and-raise-budget, red-for-all-budgets]
related_pages: [decisions/adr-027-roadmap-wbs-sdlc, decisions/adr-028-test-impact-meta-validation]
created: 2026-09-28
updated: 2026-09-28
r9_skip: true
---

# ADR-029: 세션 시작 컨텍스트 예산 — 섹션별 바이트 예산과 출구

## Status

**Accepted** (2026-09-28 소유자 승인, requirements sign-off 를 받은 design 단계 — TASK-2026-09-28-main-012,
M-016/WBS-16.1). requirements 정본은 `docs/planning/session-context-budget-requirements-2026-09.md`,
kit 계약 정본은 `workflow-source/core/session_context_budget_spec.md`. 이 페이지는 결정과 근거만 적는다.

## Context

세션 시작 필독 문서가 195KB 다 (concept 실측, 2026-09-28). 절반 이상이 handoff §5 (59KB) 와
`state.json.memory_entries` (47KB) 이고, 둘 다 **줄어드는 경로가 없다**. 8/08 에 손으로 99KB → 6KB
로 줄인 handoff 는 7주 만에 82KB 로 돌아왔다. 줄 수 상한과 이관 도구가 함께 있던 §1 만 줄었다.

requirements sign-off (Q1~Q5) 가 고정한 것: 범위 A(§5 규칙 블록) · B(§5 완료 기록) · D(`memory_entries`)
· E(`CLAUDE.md` 운영 절), C(기준선 한 줄)는 warn 만 / 단위는 섹션별 바이트 / 출구 있는 예산은
push 게이트 red / 이관은 삭제가 아니다.

design 이 정할 것 (requirements §7): 예산 정본 위치 · 이관 도구 CLI · §5 현재형 절 목록의 정본 ·
`memory_entries` 포인터 스키마 · `CLAUDE.md` 이관 대상.

## Decision

1. **예산 정본은 새 모듈 `workflow_kit/common/context_budget.py` 하나다.** 예산마다
   `(대상, 바이트 상한, 강도, 출구)` 를 한 레코드로 둔다. 출구는 **실행할 명령 문자열**이다 —
   초과 메시지가 그것을 그대로 싣는다. 개수 상한(`RECENT_DONE_ITEMS_CAP` · `BASELINE_ITEMS_CAP`)은
   `project_docs` 에 그대로 두고, 스펙이 두 부류를 한 표에서 가리킨다.
2. **§5 현재형 절 이름 목록도 같은 모듈에 둔다** (`HANDOFF_S5_CURRENT_SECTIONS`). 이관 도구와
   예산 검사와 `check_handoff_next_steps` 가 이 목록을 import 한다. 목록 밖의 절은 누적형이다 —
   새 절이 현재형으로 남으려면 목록에 올려야 한다(선언).
3. **이관은 새 도구 `wk rollover-handoff-notes` 가 한다.** `wk rollover-baselines` 와 같은 계약
   (dry-run 기본 · `--apply` · 멱등 · 포인터 정확히 하나 · 대상은 newest-first 앞 붙임 · 이관 건수는
   대상 파일의 실제 항목 수) 을 따르되 별도 도구다 — 단위(줄 vs `###` 블록)와 대상(한 파일 vs
   규칙/기록 두 파일)이 달라, 한 도구에 합치면 두 계약이 한 인자 공간에 섞인다.
   - §5 누적형 블록은 **아래(오래된 것)부터** 옮긴다. §5 는 새 블록을 위에 쌓는다.
   - `### N차가 남긴 규칙` 은 브랜치 디렉터리의 `lessons.md`, 나머지 누적형은
     `sessions/handoff-notes_<이관일>.md` 로.
   - 누적형 합이 예산 이하가 될 때까지 옮긴다. 예산을 한 블록이 넘으면 그 블록만 옮긴다.
4. **`memory_entries` 는 포인터로 싣는다** — entry 마다 `{id, primary_abstraction(120자까지),
   path}`. `path` 는 워크스페이스 기준 `ai-workflow/memory/active/memory_index/entries/<id>.json`.
   `schema_version_memory_entries` 를 `"1"` → `"2"` 로 올린다. 코드 소비자가 없으므로(전수
   grep) 이행 기간 없이 바꾸고, pass-through 를 단언하던 test 를 포인터 + 역참조 단언으로 바꾼다.
5. **`CLAUDE.md` 의 `## 프로젝트 실행 기본값` 절 본문은 `docs/LOCAL_GATE.md` 로 옮긴다.**
   `CLAUDE.md` 에는 명령(install · run · quick/isolated test · smoke) · 게이트 단계표 · 규칙 한 줄씩
   · 포인터를 남긴다. 생성 블록 세 절은 건드리지 않는다.
6. **강도는 두 층이다.**
   - **kit 소비자**: `wk refresh-state` (세션 종료) 가 모든 예산을 재고 초과를 **warning** 으로 낸다
     (출구 명령 포함). 소비 프로젝트에 이 저장소의 게이트를 강요하지 않는다.
   - **이 저장소**: 신규 `check_session_context_budget` 이 red 강도 예산을 게이트에서 잰다.
     C(기준선 한 줄)는 warn 강도라 refresh-state 경고로만 난다.
7. **'잃지 않음' (requirements R4) 은 도구 test 와 저장소 검사로 나눈다.** 무손실 이관(R4.1)은
   이관 도구의 fixture test 가 바이트 대조로, 포인터 역참조(R4.2)와 `CLAUDE.md` 링크 생존(R4.3)은
   `check_session_context_budget` 이 살아 있는 저장소에서 잰다.
8. **구현 순서는 출구 먼저, red 나중이다.** 현재 저장소는 네 예산 모두 초과다 — 검사를 먼저 켜면
   만성 red 가 되고, 만성 red 는 fixture 가 된다. D → A·B 도구 → E → 이관 실행 → 검사 활성.

## Alternatives Considered

| 대안 | 기각 이유 |
|---|---|
| `rollover-baselines` 에 `--section` 확장 | 단위·대상·포인터 위치가 달라 한 도구에 두 계약이 섞인다. 기존 도구의 멱등·포인터 계약 test 가 새 분기에 오염된다 |
| 예산을 `project_docs` 에 추가 | `project_docs` 는 파서다. 개수 상한은 파싱과 붙어 있지만 바이트 예산은 출구·강도를 가진 정책이라 별도 모듈이 읽기 쉽다 |
| `memory_entries` 를 잘라서(각 entry 1KB) 계속 전문 복제 | 소비자가 없는 사본을 줄여 유지하는 것 — 사본은 갈라진다. 포인터가 역참조로 무손실을 보장한다 |
| `CLAUDE.md` 예산을 20KB 로 올려 유지 | `CLAUDE.md` 는 대화마다 실린다 — 필독 중 바이트당 비용이 가장 크다. 근거 산문은 명령을 쓸 때만 필요하다 |
| 모든 예산 red (C 포함) | C 의 출구는 요약(판단)이다. red 는 억지 축약을 만든다 — '고친 것 없이 숫자만 좋아진다' |

## Consequences

- 필독 195KB → 약 107KB (requirements §0 추정, 구현 후 실측으로 확정하고 상한을 한 번 재조정 — Q2).
- `lessons.md` 가 새로 생긴다 — 누적 교훈의 자리가 handoff 에서 브랜치 디렉터리 파일로 옮겨 간다.
  읽는 시점은 필요할 때다 (필독이 아니다).
- 표준 문서의 `Memory Update Paths` 에 `wk rollover-handoff-notes` 한 줄이 는다 — 생성 블록이라
  `core/global_workflow_standard.md` 를 고치고 재생성한다.
- 현재형 절 목록 밖에 새 `###` 절을 만들면 누적형으로 취급돼 다음 초과 때 옮겨진다 — 의도된 성질이다.
- `state.json` 스키마가 바뀐다 (memory_entries v2). 외부 소비자가 전문을 읽고 있었다면 깨진다 —
  저장소 안에는 없다.

## References

- `docs/planning/session-context-budget-review-2026-09.md` (concept)
- `docs/planning/session-context-budget-requirements-2026-09.md` (requirements, §9 sign-off)
- `docs/architecture/ADR-006-memory-index-retrospective.md` §2 — `memory_entries` 비대 예고
- `workflow-source/workflow_kit/tools/rollover_handoff_baselines.py` — 이관 계약의 선례
