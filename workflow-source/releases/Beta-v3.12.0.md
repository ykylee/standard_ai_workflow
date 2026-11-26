# Beta v3.12.0 — 진입 렌더 영역 예산 12KiB · 120줄 (2026-11-26)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- **진입 렌더 영역 예산 8KB → 12KiB · 120줄**: 허브가 각 저장소 진입 파일(CLAUDE.md · AGENTS.md …)에 쓰는 영역 하나의 상한이다. 바이트와 줄 수를 둘 다 보고, 넘으면 `entry_budget_exceeded` 422 — 사유에 바이트 · 줄 수가 나온다. 8KB 는 1.x 에서 생성 진입 파일 **전체** 에 걸던 값을 2.0 이 영역에 그대로 옮긴 것이라 하네스 제약과 무관했고, 표준 블록이 커지자 프로젝트 지침 자리가 사라졌다(지침 제안 4건 모두 예산 초과). 새 값은 Claude Code 의 진입 파일 200줄 권고와 Codex 의 AGENTS.md 합계 32KiB(넘으면 조용히 잘림)에 맞춘다. 프로젝트 지침 자리가 약 6.8KB 가 된다.
- 1.x 부트스트랩 생성 진입 파일 예산(`ENTRY_BUDGET_BYTES` 8KiB)은 그대로다.

## 검증

- 누적 smoke **362/362 PASS**
- `check_hub_bootstrap` case 10 · Go `TestGuideRegionBudgetEdges` — 12,288B · 120줄 정확히는 통과, 1B · 1줄 넘으면 422, 3.4KB 지침 렌더. 줄 판정을 빼는 되주입이 양쪽 red.

## 운영 범위

- **DB 판은 22 그대로다** — 3.11.0 으로 되돌릴 때 실행 파일만 바꾸면 된다(되돌리면 8KB 를 넘는 지침은 다시 렌더되지 않는다).
- AGENTS.md 는 손 문단과 허브 영역을 합쳐 32KiB 아래로 둔다 — 넘으면 Codex 가 뒷부분을 조용히 자른다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-11-26T14:49:34Z)_

- total wiki pages: **104**
- total memory entries: **30**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
