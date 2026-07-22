---
type: meta
status: draft
r9_skip: true
title: active-state
created: 2026-07-22
last_touched: 2026-07-22
---

# Active State (v0.6.4~v0.7.4 보강, 2026-06-14)

> **Status**: dense — raw mirror `state.json` 동기화 완료. v0.6.3 freeze 후 누적 5 release 의 recent_done 갱신.

## SSOT 요약

| 필드 | 값 | 갱신 |
|---|---|---|
| `session.in_progress_items` | [] | - |
| `wiki.last_ingest` | 2026-06-14 | 2026-06-12 → 14 |
| `memory.last_freeze` | 2026-06-14-v0.7.4 | 2026-06-12-v6.3 → 14-v0.7.4 |

## Recent Done (v0.6.4~v0.7.4)

- v0.7.10 (fdf8159): release_pipeline Phase 2 (release / verify / rollback) + 8 smoke test
- v0.7.9 (cb0a892): release_pipeline tool 정식화 (validate / version-bump / note-draft) + 8 smoke test
- v0.7.8 (d3235ad): state-aware evaluate_compliance + config actual apply
- v0.7.7 (022672f): workflow_kit.cli.doctor 에 load_config + should_fail integration
- v0.7.6 (53d5dc8): run_all_checks 통합 runner + 10 smoke test
- v0.7.5 (0741775): refresh_wiki_memory tool 정식화 + 10 smoke test (Wiki 운영 자동화)
- v0.7.4 (22e7750): CLI wrapper (workflow doctor) + @graceful_shutdown + optional dep (hypothesis/objgraph)
- v0.7.3 (d03348a): 4 runtime helper (auth/testing/profiling/resiliency) + 7 baseline dispatcher
- v0.7.2 (3bffba3): Extension sub-cat + 4종 (resiliency) 본 구현 (179 test PASS)
- v0.7.1 (f09034d): follow-up 4건 + wiki 개선 4건 묶음 (158 test PASS, GH release)
- v0.7.0 (6e57cf3): stage_completion required 격상 + ensure fallback
- v0.6.6 (6a9126c): 5 SKILL.md-only skill runtime 통합 (12/12 spec+runtime 일관성)
- v0.6.5 (5b16517): StageCompletion field 11종 skill spec + catalog 보강 (13 file)
- v0.6.4 (25756bb): Question File Format + Stage Gate 명시화 (4 doc)

## 다음에 읽을 문서

- [in-repo/ai-workflow/memory/active/state.json](../../../memory/active/state.json) (1차 출처)
- [in-repo/ai-workflow/memory/active/backlog](../../../memory/active/work_backlog.md)
- [in-repo/ai-workflow/wiki/log.md](../../../wiki/log.md)
