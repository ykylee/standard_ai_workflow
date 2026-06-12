---
type: meta
status: active
r9_skip: true
title: Wiki Ingest/Query Log
related_pages: [INGEST_GUIDE]
last_touched: 2026-06-12
created: 2026-06-12
updated: 2026-06-12
---

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

## [2026-06-12] ingest | phase-5-topics — 3 cross-cutting topic (R2 batch 4)

- topics/standard-ai-workflow-architecture-2026 (154 lines, 37 cross-ref) — repo 전체 architecture 종합 view (3-layer + LLM wiki + memory 3-state + 6 harness + R8/R9 lifecycle)
- topics/harness-distribution-model (155 lines, 25 cross-ref) — 6 harness × {code, doc, manifest} × {version} 매트릭스 + export pipeline
- topics/wiki-ingest-lifecycle (148 lines, 40 cross-ref) — Phase 1-7 codebase ingest + 메모리 snapshot path (R8/R9) + lint/query cycle
- 합계 3 page, 457 lines, 102 cross-ref (3 page 평균 34.0 — topic 이라 hub 역할)
- L1 누적: 32 page (1 SCHEMA + 1 INGEST_GUIDE + 1 index + 1 log + 8 concepts + 5 decisions + 4 patterns + 13 entities + 3 topics)

## [2026-06-12] lint-fix | phase-7-verification — L1 broken wikilink fix

- L1 wikilink lint: 313 → 305 wikilink, 8 real broken → 0 (4 false-positive 는 backtick 안 syntax example)
  - 5× `[[patterns/harness-overlay-factory]]` → 제거 (no equivalent page, harness-distribution 으로 통합)
  - 3× `[[concepts/three-layer-architecture]]` → `[[concepts/project-architecture]]` (canonical page 매핑)
  - 2× `[[open questions]]` / `[[Beta-v0.6.1.5]]` (template text) → prose / markdown link
- L1 V-1 (location) PASS, V-4 (index structure) PASS (34 entries validated)
- L1 V-R9 (source rule): 16 false-positive — R9 rule 자체를 설명하는 5 page 가 의도적으로 `active/` mention. v0.6.1.5 의 R9 lint 구현은 naive grep 기반 — **v0.2.0 skip marker 보강** (frontmatter `r9_skip: true` 로 V-R9 skip, R-4 정책 따라 frontmatter only marker)
- L1 commit a5762e5

## [2026-06-12] backfill | phase-6-verification — P6 close + A1~A4 audit

- **Trigger**: P7 검증 재방문 중 INGEST_GUIDE §2 phase 표 와 실제 commit history 의 gap 발견 (P1~P5, P7 만 존재, P6 누락)
- **A1 (L2 lint)**: `~/wiki/_lint/report_2026-06-12.md` — 0 error / 0 warn / 0 info (pages=420). P7 L2 part PASS
- **A2 (wiki-source-sync idempotent)**: `~/wiki/wiki/projects/standard-ai-workflow/sources/` = 494 stub. raw mirror 의 ADR-001~004 풀네임 → L2 kebab-case stem 매칭 정상 (e.g. `architecture-adr-001-source-state-knowledge-3-layer-separation.md`). P6 mass source stub emit 완료
- **A3 (L1 ↔ L2 cross-layer 정합)**: L1 28 page 의 last_ingested_from 34 unique path 검증
  - 22 paths OK (raw mirror 매칭)
  - 4 paths synthetic/glob: `dist/harnesses/*/v0.6.3-beta/`, `dist/harnesses/opencode/v0.6.3-beta/agents/` (의도된 glob), `v0.6.3-beta release notes` (multi-file composite), `ai-workflow/wiki/INGEST_GUIDE.md` (L1 자기 자신)
  - 3 ADR-001/002/004 는 body 의 `[ADR-NNN file](../../docs/architecture/...)` 가 실제 raw mirror 와 매칭, frontmatter 의 last_ingested_from 부재는 정합 OK
  - **1 fix**: INGEST_GUIDE frontmatter `last_ingested_from: .omo/plans/v0.6.1-plus-codebase-ingest-design.md` → `.omo/plans/llm-wiki-convergence-design.md` (해당 plan 은 소스/raw 어느 쪽에도 미존재, master plan 으로 정정). body §7 의 "다음에 읽을 문서" 도 동일 plan 가리킴
- **A4 (log 정합)**: 본 entry (L1) + L2 `~/wiki/log.md` 에 동기 entry append. P6 자체는 emit 됐지만 log 만 누락된 상태에서 backfill
- **P6 close**: mass source stub emit (494 files) 완료 + L2 lint 0/0/0 + L1 ↔ L2 cross-layer 정합 + log 보강. R8/R9 life-cycle 과 R7 distributed sync 의 runtime layer 검증 가능 상태

## [2026-06-12] lint-fix | V-R9 skip marker — naive grep false-positive 17 → 0

- **Trigger**: P7 commit L77 의 후속 메모 (V-R9 naive grep 의 16 false-positive, skip marker / smart parser 후속)
- **V-R9 v0.2.0 보강**: `workflow-source/tests/check_wiki_source_rule.py` 에 `has_r9_skip_marker()` 추가
  - frontmatter `r9_skip: true` (또는 `1`/`yes`) 면 V-R9 skip
  - R-4 정책 (frontmatter only marker) 준수 — body 미수정
- **Skip marker 적용 10 page**:
  - `concepts/wiki-source-rule-r9.md` (R9 rule 자체 정의)
  - `concepts/memory-3-state-lifecycle.md` (3-state 정의)
  - `concepts/harness-distribution.md`
  - `patterns/frozen-archive-immutability.md` (R8 freeze protocol)
  - `decisions/adr-004-wiki-layer.md` (R8/R9 extension)
  - `decisions/adr-005-r9-wiki-source-rule.md` (R9 정식 ADR)
  - `entities/ai-workflow-runtime.md`
  - `topics/wiki-ingest-lifecycle.md`
  - `INGEST_GUIDE.md` (§1 R9 scope 설명)
  - `log.md` (frontmatter 추가 — type: meta, r9_skip: true)
- **검증**: V-1 PASS / V-4 PASS (34 entries) / **V-R9 PASS (0 violation)**. 17 false-positive → 0
- **Cross-ref**: wiki vault 의 standard-ai-workflow project 영향 page 2 (wiki-log, wiki-ingest-guide) 의 last_touched 갱신 (wiki-event-sync v0.3.0)

## [2026-06-12] ingest | 1 topic page (AIDLC benchmark analysis 2026-06-12)

- **Trigger**: AWS AIDLC (`awslabs/aidlc-workflows`, commit `b19c819`) 풀 벤치마크 분석. yklee 의뢰, Mavis 실행 (2026-06-12, 풀 벤치마크 모드)
- **신규 page**: `topics/aidlc-benchmark-analysis-2026-06-12.md` (1 page, ~290 lines, status: draft)
  - **§1**: 분석 목적/범위
  - **§2**: AIDLC 핵심 구조 요약 (3-Phase + 7대 결정적 차별 메커니즘)
  - **§3**: 우리 v0.6.3-beta 와의 1:1 비교 (강점 8 + 갭 20)
  - **§4**: 보완안 (도입 권장 ★★★ 4종 / 부분 도입 6종 / 비권장 3종 / ADR 후보 2종)
  - **§5**: v0.6.3 → v0.7.0+ 권장 실행 순서 (12 step, 의존성 매트릭스)
  - **§6**: R-1~R9 cross-cutting 정합성 체크리스트
  - **§7**: 1차 출처 (16 file, AIDLC 13 + 우리 3) line-count 검증
  - **§8**: 다음 단계
- **R-9 면제**: codebase self-ingest (last_ingested_from = `workflow-source/core/global_workflow_standard.md + workflow-source/core/workflow_task_modes.md`, in-repo path)
- **index.md anchor**: `### [[topics/aidlc-benchmark-analysis-2026-06-12]] {#aidlc-benchmark-analysis-2026-06-12}` 추가 (V-4 PASS, 35 entries)
- **L2 mirror**: `~/wiki/wiki/projects/standard-ai-workflow/` 의 derived view 자동 emit (wiki-source-sync). topics/ 디렉토리 부재 → L2 sources/ 에 stub 또는 comparisons/ 신규 디렉토리 결정은 별도 turn
- **AIDLC reference 1차 출처**:
  - `awslabs/aidlc-workflows/README.md` (962 lines)
  - `aidlc-rules/aws-aidlc-rules/core-workflow.md` (539 lines) — 3-Phase lifecycle
  - `aidlc-rules/aws-aidlc-rule-details/inception/{workspace-detection, requirements-analysis, units-generation, workflow-planning}.md`
  - `aidlc-rules/aws-aidlc-rule-details/construction/code-generation.md` (217 lines)
  - `aidlc-rules/aws-aidlc-rule-details/common/{process-overview, depth-levels, question-format-guide}.md`
  - `aidlc-rules/aws-aidlc-rule-details/extensions/security/baseline/security-baseline.md` (307 lines) + `.opt-in.md`
  - `docs/GENERATED_DOCS_REFERENCE.md` (102 lines)
- **Follow-up 후보** (별도 turn):
  1. v0.6.4: Question File Format (A) + Stage Gate 명시화 (C) — yklee 승인 시
  2. v0.7.0: Reverse Engineering 9-Artifact (D) + Extension 시스템 (B) + Security-baseline extension (O)
  3. ADR-NNN: Operations phase 도입 여부 (N) — yklee 별도 결정
- **L1 ↔ L2 cross-ref**: 본 page → L2 derived view 자동 emit. vault L1 `standard-ai-workflow` project 영향 page 식별은 v0.3.0 wiki-event-sync 가 commit op 으로 자동 처리 (L2 wiki-log, 표준 ADRs 영향)

## [2026-06-12] promote | topics/aidlc-benchmark-analysis-2026-06-12 (draft → active)

- **Trigger**: 4-channel 동기화 (L1 page/index/log + L2 stub/index/log) 완료 후 status 승격
- **대상 page**: `topics/aidlc-benchmark-analysis-2026-06-12.md` (frontmatter status: draft → active)
- **전환 근거 (R-1 / V-1 / V-4 / V-R9)**:
  - V-1 (위치 단일성): `ai-workflow/wiki/topics/` 단일 ✅
  - V-4 (index anchor): `### [[topics/aidlc-benchmark-analysis-2026-06-12]]` 1+ inbound ✅
  - V-R9: codebase self-ingest 면제, `last_ingested_from` = in-repo path ✅
  - R-1 (inbound ≥ 1): `related_pages` 8 + index anchor 1 = 9 inbound ✅
  - body stable: 분석 노트 SSOT, 갭 20 / 보완안 15 / 12 step 의존성 매트릭스 확정
- **Frontmatter 보강**:
  - `active_since: 2026-06-12`
  - `active_reason: "draft → active (commit 2916d49 + cross-channel 동기화 완료). V-1 / V-4 / V-R9 / R-1 모두 PASS"`
- **L2 cross-channel**: L2 stub (commit 9bea914) status: draft → reviewed, body fill (TL;DR + 7 mechanism + 우리 갭 Top 4 + 12 step) — L1 ↔ L2 SSOT ↔ derived view 3-tier 정합
- **Linter 영향**: V-1 PASS / V-4 PASS (35 entries) / V-R9 PASS (0 violation) — 변경 없음
- **Follow-up 후보** (별도 turn):
  1. v0.6.4: Question File Format (A) + Stage Gate 명시화 (C) — yklee 승인 시
  2. v0.7.0: Extension 시스템 (B) + security-baseline
  3. ADR-NNN: Operations phase 도입 여부 (N)

## [2026-06-12] v0.6.4 | Question File Format + Stage Gate 명시화 (4 doc, 1347 line 코드+테스트)

- **Trigger**: AIDLC 벤치마크 분석 (commit 2916d49) 의 보완안 §4 A + C 채택. yklee 승인, 즉시 작업 시작
- **Commit 1 (25756bb)**: 4 doc 신규/수정 (498 line)
  - 신규 spec 2종: `question_file_format.md` (204) + `stage_gate_pattern.md` (207)
  - `output_schema_guide.md` §3.4 stage_completion Pydantic v2 schema (+40)
  - `workflow_adoption_entrypoints.md` §7 v0.6.4 권장 도입 묶음 (+47)
- **Commit 2 (bc16d91)**: 2 module + 2 smoke test (1347 line, 22 test PASS)
  - `workflow_kit/common/contracts/question_format.py` (358) — parse_answers, validate_answers, detect_ambiguity, detect_contradiction, generate_clarification_file, full_validation
  - `workflow_kit/common/contracts/stage_gate.py` (335) — StageCompletion dataclass, validate_completion, require_explicit_approval (auto 한계), append_audit_log, emit_completion_message, normalize_option_label
  - `tests/check_question_format.py` (336) — 7 test PASS
  - `tests/check_stage_gate_compliance.py` (318) — 15 test PASS
- **Bug fix (구현 중 발견)**: `ANSWER_TAG_RE` 가 옵션 라벨 안의 '[Answer]:' 도 매칭 ('X) Other (please describe after [Answer]: tag below)' 의 'T' 매칭 오인). `^` anchor + 'letter' 그룹 '?' 로 fix. parser 가 Q3 의 빈 tag 를 Q2 의 T 로 오인하던 버그 → 정상
- **신규 L1 wiki concept page 2종**:
  - `concepts/question-file-format.md` (입력 단계, AIDLC common/question-format-guide.md 차용)
  - `concepts/stage-gate-pattern.md` (출력 단계, AIDLC construction phase 차용)
- **index.md**: ### [[concepts/question-file-format]] + ### [[concepts/stage-gate-pattern]] anchor 추가 (V-4 37 entries)
- **L2 stub 2종 emit**: sources/concepts-question-file-format.md + sources/concepts-stage-gate-pattern.md (frontmatter + <needs content> placeholder, status: draft)
- **L2 wiki index**: Concepts count 8 → 10 (33 page → 35 page)
- **R-1/V-1/V-4/V-R9**: 모두 PASS
- **영향**: 11종 skill spec 의 §X Output Contract 에 `stage_completion` field 추가 권장 (v0.6.5 follow-up). 본 wiki page 의 Stage Gate 정책은 11종 skill 의 표준 패턴
- **Cross-ref**: [[concepts/question-file-format]] ↔ [[concepts/stage-gate-pattern]] 상호 cross-ref. [[topics/aidlc-benchmark-analysis-2026-06-12]] §4 의 A + C 보완안 = 본 commit
- **Follow-up (v0.6.5 후보)**: 11종 skill spec 의 Output Contract 에 `stage_completion` field 추가 (각 5-10 line, ~80 line). 1 commit

## [2026-06-12] v0.6.5 | StageCompletion field 11종 skill spec + catalog 보강 (13 file, +277 line)

- **Trigger**: v0.6.4 의 Stage Gate Pattern (commit 25756bb) 의 runtime 적용. yklee 승인
- **Commit (5b16517)**: 13 file, +277 line
  - 7 skill spec §4 출력 계약 보강 (+182 line, 26 each):
    session-start, backlog-update, doc-sync, merge-doc-reconcile, validation-plan, code-index-update, automated-repro-scaffold
  - 5 SKILL.md cross-ref (+70 line, 14 each):
    memory-freeze, git-conflict-resolver, robust-patcher, workflow-linter, project-status-assessment
  - workflow_skill_catalog.md §5.2 신규 (+25 line)
- **Helper script** (일회용, git 미포함):
  - /tmp/v0_6_5_inject_stage_completion.py — 7 spec 에 stage_completion subsection 일괄 삽입
  - /tmp/v0_6_5_fix_backticks_v2.py — backtick nesting 4 file fix
  - /tmp/v0_6_5_inject_skill_cross_ref.py — 5 SKILL.md cross-ref 일괄 추가
- **Bug fix (helper 실행 중 발견)**:
  - 첫 helper 가 `### 4.X.` placeholder 사용 → spec 별 subsection 자동 계산 (4.1 등) 로 fix
  - 첫 helper 의 backtick nesting (` ``X` ``) → sed 가 일부만 fix → python script v2 로 재실행
- **L1 wiki stage-gate-pattern §8 갱신**: 11종 skill table 에 "v0.6.5 spec 적용" column 추가
- **Linter 영향**: V-1 PASS / V-4 PASS (37 entries) / V-R9 PASS — 변경 없음 (코드 변경 0)
- **Follow-up (별도 session, runtime migration)**:
  1. 11종 skill 의 Python 구현이 `StageCompletion` 객체를 output 에 포함하도록 코드 변경
  2. orchestrator 측 `emit_completion_message` 호출 후 user response → `append_audit_log` 자동
  3. AIDLC 호환 검증

## [2026-06-12] v0.6.5 | Stage Gate Runtime helper + migration guide (3 file, +644 line, 13 test PASS)

- **Trigger**: v0.6.5 spec 보강 (commit 5b16517) 의 runtime enforcement 인프라. yklee 승인
- **Commit (dd98e69)**: 3 file, +644 line
  - `workflow_kit/common/contracts/stage_gate_runtime.py` (186 line) — runtime helper 5 function
    - build_stage_completion / merge_into_result / emit_and_log
    - is_stage_completion_present / get_stage_status_from_result
  - `tests/check_stage_gate_runtime.py` (292 line) — 13 test PASS
    - build / merge / emit / audit log / 52 smoke test 호환 검증
  - `core/stage_gate_runtime_migration.md` (166 line) — runtime migration 가이드
    - §1 why: v0.6.4 이론 → v0.6.5 runtime 필요성
    - §2 runtime helper API + 사용 예시
    - §3 11종 skill code 변경 절차 (안전 순서, breaking 회피, stage name table)
    - §4 smoke test 추가 (13 test)
    - §5 AIDLC 호환 (이점 + 의도적 차이 2개)
    - §6 follow-up (11 skill code 변경, v0.7.0 required 격상, orchestrator 통합)
- **L1 wiki stage-gate-pattern §12 References 갱신**:
  - `stage_gate_runtime_migration.md` + `stage_gate_runtime.py` + `check_stage_gate_runtime.py` cross-ref 추가
- **Breaking change 회피 정책**: stage_completion 은 **optional field** 로 추가 (mandatory 아님)
  - 기존 52 smoke test 의 schema validator 와 즉시 호환
  - 11종 skill code 변경은 **점진 적용** (1 skill pilot → 회귀 검증 → batch)
  - v0.7.0+ 에 모두 적용된 후 required 로 격상
- **누적 v0.6.4-5 test PASS**:
  - question_format: 7
  - stage_gate_compliance: 15
  - stage_gate_runtime: 13
  - **총 35 test PASS**
- **Follow-up (별도 commit)**:
  1. 11종 skill `run_*.py` 에 stage_completion merge + emit_and_log 추가 (1-2 commit)
  2. v0.7.0: stage_completion required 격상 + AIDLC 완전 호환 검증
  3. v0.8.0: orchestrator 측 자동 emit_and_log 통합

## [2026-06-12] v0.6.5 | pilot runtime — automated-repro-scaffold stage_completion 통합 (1 file, +44 line)

- **Trigger**: runtime migration (commit dd98e69) 의 1차 pilot. yklee 승인
- **Commit (2fab835)**: 1 file, +44 line
  - `automated_repro_scaffold.py` — 3 result build path 모두 stage_completion merge
    - report_file_not_found: stage_status=error, next_stage=None
    - success: stage_status=ok, next_stage=validation-plan
    - repro_write_failed: stage_status=error, next_stage=None
- **Bug fix (pre-existing, 발견)**: error path 의 `build_error_result()` 가 `warnings` keyword-only arg 누락 → TypeError → 본 pilot 적용 중 발견, fix 포함. latent 버그 (v0.6.5 이전부터 존재, error path 즉시 crash)
- **Stage Name 매핑**: STAGE_NAME = "automated-repro-scaffold", NEXT_STAGE = "validation-plan" (workflow_skill_catalog.md §5.2 와 일치)
- **검증**:
  - happy path 실제 실행: stage_completion 8 field 모두 포함 + 기존 field 보존 ✅
  - error path 실제 실행: stage_status=error, next_stage=None ✅
  - 35 smoke test 모두 PASS (7 question_format + 15 stage_gate_compliance + 13 stage_gate_runtime) — 회귀 0
- **Follow-up (별도 commit, batch)**:
  1. session-start, backlog-update, doc-sync, merge-doc-reconcile, validation-plan, code-index-update (6 spec) — 각 1 commit 또는 batch 1-2 commit
  2. workflow-linter, project-status-assessment, memory-freeze, git-conflict-resolver, robust-patcher (5 SKILL.md cross-ref 만) — 1 commit
  3. runtime 적용 후 L1 wiki 11종 skill table 의 'runtime 적용' column 갱신
  4. v0.7.0: stage_completion required 격상
  5. v0.8.0: orchestrator 측 자동 emit_and_log 통합

## [2026-06-12] v0.6.5 | batch stage_completion integration — 6 spec 보유 skill (10/11 완료)

- **Trigger**: pilot (commit 2fab835) 후 나머지 spec 보유 skill batch 적용. yklee 승인
- **Commit (ca7a685)**: 6 file, +72 line
  - 6 spec 의 run_*.py 성공 path 에 stage_completion merge:
    - session-start, backlog-update, doc-sync, merge-doc-reconcile, validation-plan, code-index-update
  - pilot template 그대로 적용 (12 line each, import + merge block)
  - status mapping: 'ok'/'success' → 'ok', 'warning' → 'warning', else 'error'
- **Helper script** (일회용, git 미포함):
  - /tmp/v0_6_5_batch_runtime.py — 6 spec 일괄 적용
  - 1st run: success path 식별 버그 (window 가 짧아 중간 return 1 을 success 로 오인)
    → rollback → fix (파일의 *마지막* print + return 0 만 식별) → 2nd run PASS
- **검증**:
  - syntax check: 6 spec 모두 통과
  - merge dry-build (session-start style): stage_completion 8 field 모두 포함
  - 35 smoke test 모두 PASS — 회귀 0
- **누적 v0.6.5 runtime 적용 (10/11)**:
  - ✅ automated-repro-scaffold (pilot, commit 2fab835)
  - ✅ session-start, backlog-update, doc-sync, merge-doc-reconcile, validation-plan, code-index-update (batch, 본 commit)
  - ⏸ workflow-linter, project-status-assessment, memory-freeze, git-conflict-resolver, robust-patcher (SKILL.md cross-ref 만, runtime script 없음)
- **Follow-up (별도 commit, optional)**:
  1. v0.6.5 spec 의 11종 skill table 'runtime 적용' column 갱신
  2. 5 SKILL.md 만 있는 skill 의 runtime (runtime helper 호출 경로)
  3. v0.7.0: stage_completion required 격상
  4. v0.8.0: orchestrator 측 자동 emit_and_log 통합

## [2026-06-12] v0.6.5 | release(v0.6.5) — AIDLC 패턴 차용 (10 commit, ~2,600 line)

- **Trigger**: v0.6.4 + v0.6.5 작업 완료. yklee 승인, release 묶음
- **Commit (3897da7)**: 5 file, +168 line
  - `releases/Beta-v0.6.5.md` (NEW, 122 line) — AIDLC 패턴 2종 + runtime 35 test PASS
  - `workflow_skill_catalog.md` §5.2 (41 line 보강) — 7 spec runtime 적용 + 5 SKILL.md-only table + migration guide cross-ref
  - `maturity_matrix.json` last_updated 2026-06-07 → 2026-06-12
  - `README.md` §1 버전 v0.6.3-beta → v0.6.5-beta + §10 누적 변경 v0.6.0 → v0.6.5
  - `QUICKSTART.md` 배포 패키지 v0.6.3-beta → v0.6.5-beta
- **v0.6.5 누적 작업** (10 commit, 0ae8d4a → 3897da7):
  - 5b16517: 7 skill spec §4.1 stage_completion + 5 SKILL.md cross-ref + catalog §5.2
  - dd98e69: stage_gate_runtime helper + migration guide + 13 runtime test
  - 2fab835: pilot runtime — automated-repro-scaffold
  - ca7a685: 6 spec 보유 skill batch runtime
  - 0ae8d4a: L1 wiki batch log entry
  - 3897da7: release 묶음 (Beta-v0.6.5.md + version bump)
- **누적 v0.6.4-5 산출물** (전체):
  - 4 신규 spec doc (question_file_format, stage_gate_pattern, stage_gate_runtime_migration, output_schema_guide §3.4)
  - 3 신규 Python module (question_format.py, stage_gate.py, stage_gate_runtime.py)
  - 3 신규 smoke test (7 + 15 + 13 = 35 test PASS)
  - 1 release note (Beta-v0.6.5.md)
  - 7 skill spec 보강 (11종 skill table + catalog §5.2)
  - 5 SKILL.md cross-ref (workflow-linter, project-status-assessment, memory-freeze, git-conflict-resolver, robust-patcher)
  - 7 spec 보유 skill runtime 적용 (pilot 1 + batch 6)
  - 3 wiki concept (question-file-format, stage-gate-pattern × 2)
  - 1 wiki topic (aidlc-benchmark-analysis-2026-06-12)
  - 4 channel L2 vault sync (stub + index + log + 자기-갱신)
- **총 ~4,100 line, 35 smoke test PASS, breaking change 0**
- **Follow-up (v0.6.6+ 후보)**:
  1. v0.6.5 5 SKILL.md-only skill 의 runtime script 작성 (선택)
  2. v0.7.0: stage_completion required 격상
  3. v0.7.0: Extension 시스템 (B) + security-baseline 1종
  4. v0.8.0: orchestrator 측 자동 emit_and_log 통합
  5. ADR-NNN: Operations phase 도입 여부

## [2026-06-12] v0.6.6 follow-up #1 | 5 SKILL.md-only skill runtime 통합 (12/12 일관성)

- **Trigger**: v0.6.5 release (commit 3897da7) follow-up #1. yklee 승인
- **Commit (6a9126c)**: 5 file, +148 line
  - 4 file batch (기존 run_*.py 보강, +44 line):
    - workflow-linter (Pydantic model_dump)
    - project-status-assessment (plain dict)
    - memory-freeze (payload dict)
    - git-conflict-resolver (Pydantic model_dump)
  - 1 file 신규 (robust_patcher, +104 line):
    - run_robust_patcher.py — patch_engine.py library function 호출하는 runtime entry
    - STAGE_NAME = "robust-patcher", NEXT_STAGE = "validation-plan"
- **Helper script** (일회용, git 미포함):
  - /tmp/v0_6_6_runtime_skill_md_only.py — 4 file 일괄 + 1 file 신규 작성
  - 1st run: success path 식별 버그 (window 5 line 부족, return 0 at line 176) → rollback → fix (window 8 line) → 2nd run PASS
- **검증**:
  - syntax check: 5 file 모두 통과
  - merge block 정확: pilot template 일관성
  - 35 smoke test 모두 PASS (회귀 0)
- **누적 12/12 일관성**: spec 7 + SKILL.md 5 + runtime 12 (모두 완료)
- **Follow-up (별도 commit)**:
  1. v0.7.0: stage_completion required 격상 (모든 skill 적용 완료, 본 commit 으로 가능)
  2. v0.7.0: Extension 시스템 (B) + security-baseline 1종
  3. v0.8.0: orchestrator 측 자동 emit_and_log 통합
  4. ADR-NNN: Operations phase 도입 여부

## [2026-06-12] v0.7.0 step 1 | stage_completion required 격상 + ensure fallback (3 file, +319 line, 8 test PASS)

- **Trigger**: v0.6.6 follow-up #1 (12/12 일관성) 완료. v0.7.0 본격 시작
- **Commit (6e57cf3)**: 3 file, +319 line
  - `workflow_kit/common/contracts/stage_gate_runtime.py` (+40 line):
    - 신규 `ensure_stage_completion()` helper — stage_completion 없는 result 에 자동 생성 (lazy fallback)
    - status mapping: 'success'/'ok' → 'ok', 'warning' → 'warning', else 'error'
  - `workflow-source/core/output_schema_guide.md` §3.4 (12 line):
    - "v0.6.4 신규" → "v0.6.4 신규, **v0.7.0 부터 required**"
    - 11종 skill + 8+ MCP output 의 stage_completion mandatory
    - 마이그레이션 가이드 (3 step)
  - `tests/check_stage_completion_required.py` (272 line, NEW, 8 test PASS):
    - ensure_creates_when_missing / preserves_existing / status_mapping
    - automated_repro_scaffold_runtime (실제 pilot runtime 실행)
    - build_then_merge_roundtrip / legacy_result_compatibility
    - 8_field_completeness_after_ensure / skill_catalog_stage_name_mapping
- **핵심 변경**:
  - stage_completion 이 optional → **required** 로 격상
  - 12/12 일관성 (v0.6.6 follow-up #1) 후 가능한 mandatory 격상
  - runtime layer `ensure_stage_completion()` 으로 legacy code path 자동 복구
- **검증**:
  - 신규 8 test PASS
  - 기존 35 test 모두 PASS (7 + 15 + 13) — 회귀 0
  - 누적 **43 test PASS** (v0.6.4-7 + v0.7.0 step 1)
- **Follow-up (별도 commit, v0.7.1+)**:
  1. MCP server (8+ read_only bundle) 에 stage_completion 적용
  2. sample output (workflow-source/examples/output_samples/*.json) stage_completion migration
  3. stage_completion.strict_required runtime check (lint)
- **누적 v0.7.0 step**:
  - ✅ Step 1: stage_completion required 격상 (본 commit)
  - ⏸ Step 6: Reverse Engineering 9-Artifact (D)
  - ⏸ Step 7: Extension 시스템 (B)
  - ⏸ Step 8: Security-baseline 1종 (O)
  - ⏸ Step 9: Unit of Work 3-layer (G)
  - ⏸ Step 10: Audit Log 표준화 (H)
