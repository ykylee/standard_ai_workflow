# Memory Operation Log

- 목적: `ai-workflow/memory/` 의 append-only 작업 로그. 각 session-start, freeze, ingest 기록.
- 형식: `## [YYYY-MM-DD] event_type | description`
- 속성: append-only. 선행 entry 수정 금지 (R8 immutability 정신)

## [2026-06-12] init | memory/log.md 생성 (v0.6.3 P4)
- 로그 체계 도입. wiki/log.md 와 동일 형식. session-start, memory-freeze 시 append.

## [2026-06-12] freeze | v0.6.1 test freeze
- archive/2026-06-12/ 생성. 6개 파일 frozen (PROJECT_PROFILE, state.json, work_backlog.md 등)

## [2026-06-12] session | v0.6.3 release + wiki organization
- wiki page types 정리: decisions/adr-004-wiki-layer, patterns/r4-anchor-index, entities/bootstrap-wiki-py 신규
- index.md 갱신: 7 entries (3 concepts + 1 decision + 1 pattern + 1 entity + 1 archived)
- memory archive freeze: 2회 (v6.3, self-dogfood)
- self-dogfood concept page: project-architecture.md 작성 (3-Layer + Wiki + Memory 3-State)
- 모든 lint test PASS

## [2026-06-16] release | v0.7.56 — 6 follow-up 통합
- score-wiki-trend in-process (memory rule 8 fix — tools/ package 화)
- dispatcher 14 → 23 (9 subcommand 신규: okf-cleanup / cache-prune / release-{bump,note,changelog,create,verify,rollback,dist})
- release_pipeline wrapper 1 → 8 (7 wrapper 신규)
- cache-lfu-decay CSV in-place (decay_csv_inplace + dispatcher --inplace)
- 5 module audit 3차 (okf strict mode lint 7 신규)
- GH Pages FEEDBACK.md (외부 consumer feedback loop)
- 누적: dispatcher 6→23, 5 module test ~147 PASS, GH Pages ✅
- memory rule 5 (destructive subcommand dry-run default) 정공법 4 subcommand 적용
- 다음: <in-memory> test artifact cleanup, dispatcher 25+, mkdocs --strict
