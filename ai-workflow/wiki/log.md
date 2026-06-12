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

## [2026-06-12] ingest | phase-2-concepts — 5 concept pages 신규

- wiki-source-rule-r9.md (98 lines, 11 cross-ref) — R9 (wiki-ingest source = archive/ only, v0.6.1.5)
- memory-3-state-lifecycle.md (105 lines, 4 cross-ref) — active ↔ archive ↔ release 3-state
- contract-v1-output-validation.md (180 lines, 6 cross-ref) — Pydantic v2 + output_validator + delegator + MUST NOT 7+2
- agent-topology.md (145 lines, 8 cross-ref) — 4-role orchestrator + 3 sub-agent (doc/code/validation)
- harness-distribution.md (103 lines, 7 cross-ref) — 6-harness overlay + bundle structure + export workflow
- 합계 631 lines, 36 cross-ref (5 page 평균 7.2)
- 모두 R2 1 commit (5-15 page 동시 갱신) 준수, R3 pull-before-push 대기

## [2026-06-12] ingest | phase-3-decisions — 4 ADR 신규 + 1 ADR extend

- decisions/adr-001-3-layer-separation (112 lines, 7 cross-ref, accepted v0.5.2) — Source/State/Knowledge 3-layer 분리
- decisions/adr-002-pydantic-v2-contract-v1 (111 lines, 6 cross-ref, accepted v0.5.4) — 외부 markdown spec + Pydantic v2 helper 결합
- decisions/adr-003-read-only-mcp-default (114+12 lines, 3 cross-ref, accepted v0.5.5) — MCP 6+1 server + 2 transport 의 read-only default
- decisions/adr-004-wiki-layer (37 → 114 lines, 7 cross-ref, accepted v0.6.0) — extend: frontmatter 정규화 + v0.6.1+ Evolution (R8/R9) + References 추가
- decisions/adr-005-r9-wiki-source-rule (119 lines, 22 cross-ref, proposed v0.6.1.5) — R9 rule 의 정식 ADR 승격
- 합계 5 page, 570 lines (extend 포함), 45 cross-ref (5 page 평균 9.0)
- ADR-001/002/003 mirror + ADR-004 extend + ADR-005 신규
- 모두 R2 1 commit (5-15 page 동시 갱신) 준수
- ADR-005 status=proposed (정식 accepted 시 status 갱신 필요)

## [2026-06-12] ingest | phase-4-patterns-entities — 3 pattern + 12 entity (R2 batch 3, 15 page = 한도 매칭)

- patterns/frozen-archive-immutability (119 lines, 3 cross-ref) — R8 freeze mechanism
- patterns/wiki-stub-emit (104 lines, 3 cross-ref) — bootstrap_lib/wiki.py emitter
- patterns/stale-90day-lint (74 lines, 4 cross-ref) — L05 stale 90일+ lint
- entities/standard-ai-workflow (159 lines, 21 cross-ref) — PRIMARY hub entity
- entities/workflow-kit (73 lines, 6 cross-ref) — Python package
- entities/workflow-source (73 lines, 11 cross-ref) — SSOT source dir
- entities/ai-workflow-runtime (71 lines, 5 cross-ref) — runtime layer
- entities/skill-catalog (107 lines, 7 cross-ref) — 11 skills
- entities/mcp-read-only-bundle (91 lines, 9 cross-ref) — 6+1 MCP servers
- entities/harness-overlay-codex (105 lines, 6 cross-ref) — Codex
- entities/harness-overlay-opencode (80 lines, 8 cross-ref) — OpenCode 5-agent
- entities/harness-overlay-gemini-cli (72 lines, 10 cross-ref) — Gemini CLI
- entities/harness-overlay-antigravity (92 lines, 10 cross-ref) — Antigravity
- entities/harness-overlay-minimax-code (87 lines, 13 cross-ref) — MiniMax Code
- entities/harness-overlay-pi-dev (71 lines, 5 cross-ref) — pi-dev
- 합계 15 page, 1378 lines, 121 cross-ref (15 page 평균 8.07)
- R2 1 commit = 1 ingest (5-15 page 동시 갱신) 한도 정확히 매칭 (15 page)
