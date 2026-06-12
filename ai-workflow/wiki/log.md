# Wiki Ingest/Query Log

- 문서 목적: 모든 ingest / query / lint 이벤트의 append-only 작업 로그. 시간 순 보존, 편집 금지 (append only).
- 갱신 규칙: ingest 종료 시 또는 query/lint 실행 시 한 줄 추가. 형식 `## [YYYY-MM-DD] <event> | <summary>`.
- 최종 갱신일: 2026-06-12

## [2026-06-12] bootstrap | wiki layer P1 prototype

- SCHEMA.md, index.md, log.md, 2 concept pages seeded
- target: ai-workflow/wiki/ Runtime layer (R1, D1, D2)

## [2026-06-12] ingest | phase-1-scaffold — codebase ingest pipeline

- INGEST_GUIDE.md 신규 — codebase self-ingest 절차 (Phase 1-7), R9 면제 명시
- index.md anchor 확장 — 5 page type × Phase 2-5 placeholder (8 concept, 5 decision, 4 pattern, 13 entity, 3 topic)
- L3 raw mirror 셋업: `~/wiki/wiki-sync-standard-ai-workflow.sh` + `raw/projects/standard-ai-workflow/` (588 files, 4.7 MB)
- L2 placeholder: `~/wiki/index.md` §18 standard-ai-workflow section 추가 (Phase 6 hook)
- L1 wiki ingest commit 1회 (R2, 5-15 page 동시 갱신 준수)
