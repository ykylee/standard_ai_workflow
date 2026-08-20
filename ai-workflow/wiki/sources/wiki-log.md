---
type: meta
status: draft
r9_skip: true
title: wiki-log
created: 2026-07-22
last_touched: 2026-08-20
---

# Wiki Log (Derived View, 2026-08-20)

> L1 SSOT: `ai-workflow/wiki/log.md` (2059 lines)
> 본 L2 파생 뷰는 in-repo retrieval 용 압축 요약이다. 정본은 L1 SSOT 를 본다.
> 생성: `2026-08-20` by `workflow_kit.tools.refresh_wiki_memory --emit-l2`

## 최근 entry 5건 (최신 우선)

## [2026-06-30] governance | workflow 종료 단계 commit/memory 순서 정합 (commit `32185c7` + memory cycle `df3d802`)

### Cross-ref 보강

- `concepts/memory-3-state-lifecycle.md` — Active 갱신 = commit 직전 정책 row 추가, §6 References 에 `global_workflow_standard.md §8` cross-ref
- `concepts/project-architecture.md` — Runtime layer 갱신 정합 row 추가 (3-Layer 표 + §6 References)

### SSOT

- [`workflow-source/core/global_workflow_standard.md` §8](../../../workflow-source/core/global_workflow_standard.md) — 8.1 memory → commit → push / 8.2 commit 이후 예외 / 8.3 안티패턴
- [`workflow-source/MEMORY_GOVERNANCE.md` §3](../../../workflow-source/MEMORY_GOVERNANCE.md) — §8 cross-ref
- [`workflow-source/core/phase5_governance_guide.md` §4](../../../workflow-source/core/phase5_governance_guide.md) — §8 정합
- [`workflow-source/extensions/resiliency-baseline.md` RES-WF-08](../../../workflow-source/extensions/resiliency-baseline.md)
- harness overlay (pi-dev/AGENTS + codex/gemini-cli/opencode apply_guide) 4 file
- examples/{acme_delivery_platform,research_eval_hub}/work_backlog.md 2 file
- templates/work_backlog_template.md 1 file

### Audit 결과

- 잔재 0 (다른 governance 문서 audit 결과 추가 정정 불필요)
- §7.2 "TASK 완료 시 세션 종료 전 roadmap 반영" 은 commit/memory 무관 (TASK 완료 시점 roadmap 동기화)
- Beta-v0.6.0.md "memory/archive/ ← 세션 종료 시 freeze" 는 R8 의도된 동작 (active → archive)

### Note

- 본 entry 는 wiki log.md 의 append-only 정책 준수 (기존 entry 편집 ❌, 마지막에만 append)
- R9 skip (wiki log 자체가 R9 예외)

## [2026-06-16] release | v0.7.57 — <in-memory> cleanup + dispatcher 26 + mkdocs link audit

### Cut

- **Commits** (4): ec1223c / cbcaaad / 654e21e (chore) — version bump 포함
- **Tag**: v0.7.57-beta (pending push)
- **Release note**: workflow-source/releases/Beta-v0.7.57.md

### 3 follow-up 결과

1. ✅ **<in-memory> artifact cleanup** — save_cache_with_decay 의 cache_path: str | None. None = compute only.
2. ✅ **dispatcher 23 → 26** — cache-merge-multi (24) / cache-import-csv (25) / cache-export-json (26)

... (이후 본문은 L1 SSOT 참조)
