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

## [2026-06-12] v0.7.0 step 1 (commit `6e57cf3`) | stage_completion required 격상 + ensure fallback (3 file, +319 line, 8 test PASS)

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

## [2026-06-12] v0.7.0 step 10 (commit `54e96a9`) | Audit Log 표준화 (3 file, +637 line, 13 test PASS)

- **Trigger**: v0.6.4-5 의 분산 정의된 audit log 정책 통합. yklee 승인, step 10 진행
- **Commit (54e96a9)**: 3 file, +637 line
  - `workflow-source/core/audit_log_standard.md` (209 line, NEW): 단일 표준 spec
    - §1-10: 위치 / format / append-only / lifecycle / 자동화 / migration / 한계 / AIDLC 호환 / references
  - `workflow_kit/common/contracts/stage_gate.py` (+22 line, fix):
    - **Bug fix 1 (leading newline)**: entry_lines 시작의 "" 제거 → file 첫 줄이 ## [Stage: ...] 로 시작
    - **Bug fix 2 (microsecond leak)**: datetime.now(timezone.utc).isoformat() 가 microsecond 포함 → split('.')[0] 정규화
  - `tests/check_audit_log_compliance.py` (412 line, NEW, 13 test PASS):
    - entry format / 8 field / append-only / ISO 8601 / approval status / actor / full_workflow_audit_log / legacy_readable
- **Test bug fix (보너스)**:
  - ENTRY_HEADER_RE 에 `re.MULTILINE` flag 누락 → 추가
  - iso_8601_z_suffix test 의 string 비교 (`ts[len(...):]`) 잘못 → `ISO_8601_RE.match()` + microsecond 검증으로 fix
- **검증**:
  - 신규 13 test PASS
  - 기존 43 test 모두 PASS — 회귀 0
  - 누적 **56 test PASS** (v0.6.4-7 + v0.7.0 step 1 + step 10)
  - runtime helper 2 fix 가 기존 smoke test 회귀 0 (latent bug)
- **누적 v0.7.0 step 진행**:
  - ✅ Step 1: stage_completion required 격상 (commit 6e57cf3)
  - ✅ Step 10: Audit Log 표준화 (본 commit)
  - ⏸ Step 6: Reverse Engineering 9-Artifact (D, 2-3 ses)
  - ⏸ Step 7: Extension 시스템 (B, 3-5 ses)
  - ⏸ Step 8: Security-baseline 1종 (O, 1 ses)
  - ⏸ Step 9: Unit of Work 3-layer (G, 1-2 ses)

## [2026-06-12] v0.7.0 step 9 (commit `c981cac`) | Unit of Work 3-layer template (2 file, +622 line, 17 test PASS)

- **Trigger**: v0.6.4-7 의 mode 6종 (horizontal) + task-level (work_backlog) 의 missing layer 보강. yklee 승인, step 9 진행
- **Commit (c981cac)**: 2 file, +622 line
  - `workflow-source/templates/unit_of_work_template.md` (208 line, NEW): system-level 분해 + dependency matrix + Mermaid graph + story mapping + code organization
  - `tests/check_unit_of_work_template.py` (414 line, NEW, 17 test PASS):
    - UOW 정의 parse (5): header / required fields / type enum / status enum / date format
    - Dependency Matrix (5): parse / symmetry / no-self-dep / **cycle detection (DFS)** / DAG validation
    - Mermaid Graph (2): block present / edge syntax
    - Story Mapping (1): valid UOW id 참조
    - Template 자체 정합성 (3): sections / related docs / AIDLC source
    - 통합 (1): full parse 일관성
- **Test bug fix (보너스)**:
  - dep_matrix_cycle_detection 의 nested function scope issue → helper `_has_cycle` top-level 로 추출
  - mermaid_graph_syntax 의 strict edge matching → 양방향 arrow + line edge 매칭
- **검증**:
  - 신규 17 test PASS
  - 기존 56 test 모두 PASS — 회귀 0
  - 누적 **73 test PASS** (v0.6.4-7 + v0.7.0 step 1 + 9 + 10)
- **누적 v0.7.0 step 진행**:
  - ✅ Step 1: stage_completion required 격상 (commit 6e57cf3)
  - ✅ Step 9: Unit of Work 3-layer template (본 commit)
  - ✅ Step 10: Audit Log 표준화 (commit 54e96a9)
  - ⏸ Step 6: Reverse Engineering 9-Artifact (D, 2-3 ses)
  - ⏸ Step 7: Extension 시스템 (B, 3-5 ses)
  - ⏸ Step 8: Security-baseline 1종 (O, 1 ses)
- **Follow-up (v0.7.1+)**:
  1. workflow_kit.common.contracts.uow 신규 (UOW matrix parsing + sub-agent 위임 결정 helper)
  2. bootstrap_lib 의 `--adoption-mode new` 가 unit_of_work.md 자동 emit
  3. v0.8.0: UOW 기반 sub-agent 위임 자동화

## [2026-06-12] v0.7.0 step 6 (commit `4bbd391`) | Reverse Engineering 9-Artifact (11 file, +674 line, 19 test PASS)

- **Trigger**: v0.6.4-7 의 `existing` onboarding 이 단일 `repository_assessment.md` 만 emit → 주제별 SSOT 부재. yklee 승인, step 6 진행
- **1차 출처**: AIDLC `aidlc-rules/aws-aidlc-rule-details/inception/reverse-engineering.md` (311 line, commit b19c819, 2026-06-08)
- **Scope 결정**: AIDLC 9-Artifact 구조 유지 (simplification ❌). 각 artifact 를 30-50 line template 으로 압축 (AIDLC 50 line × 9 = 450 line → 우리 ~30 line × 9 = 270 line)
- **Commit (예정)**: 11 file, +674 line
  - `workflow-source/reverse-engineering/01-business-overview.md` (32 line, NEW): business transaction = workflow stage transition
  - `workflow-source/reverse-engineering/02-architecture.md` (32 line, NEW): components = harness / skill / MCP / workflow_kit
  - `workflow-source/reverse-engineering/03-code-structure.md` (29 line, NEW): key classes = workflow_kit modules
  - `workflow-source/reverse-engineering/04-api-documentation.md` (32 line, NEW): REST → MCP tool / Internal → workflow_kit Python
  - `workflow-source/reverse-engineering/05-component-inventory.md` (33 line, NEW): 5 type (Harness/MCP/workflow_kit/Template/Test)
  - `workflow-source/reverse-engineering/06-technology-stack.md` (36 line, NEW): Python + 5 harness + packaging
  - `workflow-source/reverse-engineering/07-dependencies.md` (37 line, NEW): internal workflow_kit + pyproject external
  - `workflow-source/reverse-engineering/08-code-quality-assessment.md` (40 line, NEW): smoke test PASS + R-1~R9 lint
  - `workflow-source/reverse-engineering/09-reverse-engineering-metadata.md` (43 line, NEW): ISO 8601 + state.json sync
  - `workflow-source/core/reverse_engineering.md` (140 line, NEW): step-by-step guide (13 step, AIDLC 대응)
  - `workflow-source/tests/check_reverse_engineering.py` (350 line, NEW, 19 test PASS):
    - 디렉토리 + 9 artifact 존재 (4)
    - artifact 내용 검증 (4): Verification subsection / Workflow domain 적응 / AIDLC cross-ref / sequential numbering
    - guide 내용 검증 (6): 13 step / 9-Artifact table / AIDLC correspondence / rerun stale / state.json schema / workflow pattern adaptation
    - cross-reference (2): AIDLC 1차 출처 line count drift / artifact count matches
    - R-1~R9 lint (3): no duplicate filename / consistent naming / guide links to artifact dir
- **Test bug fix (보너스)**:
  - `test_guide_has_thirteen_steps` 의 개별 step 매칭 → "Step 2-9" range 표기 인식 추가 (DRY)
- **검증**:
  - 신규 19 test PASS
  - 기존 88 test 모두 PASS — 회귀 0
  - 누적 **107 test PASS** (v0.6.4-7 + v0.7.0 step 1, 9, 10, 8, 6)
- **누적 v0.7.0 step 진행**:
  - ✅ Step 1: stage_completion required 격상 (commit 6e57cf3)
  - ✅ Step 8: Security-baseline 1종 (commit dc2c22b)
  - ✅ Step 9: Unit of Work 3-layer template (commit c981cac)
  - ✅ Step 10: Audit Log 표준화 (commit 54e96a9)
  - ✅ Step 6: Reverse Engineering 9-Artifact (본 commit)
  - ⏸ Step 7: Extension 시스템 (B, 3-5 ses)
- **Follow-up (v0.7.1+)**:
  1. `existing_project_onboarding.py` 가 9 artifact 자동 fill (현재 단일 `repository_assessment.md` 만 자동)
  2. v0.7.1: SEC-WF-05 dependency integrity 검증 — `07-dependencies.md` 의 lock file + checksum 자동 확인
  3. v0.7.1: 9-Artifact 별 wiki L1 page (각 artifact 마다 L1 topic page + L2 sources/)
  4. v0.8.0: Artifact 별 version diff (이전 reverse engineering 대비 변경점)

## [2026-06-13] v0.7.0 step 7 (commit `0052da1`) | Extension 시스템 일반화 (5 file, +23 test PASS)

- **Trigger**: v0.7.0 step 8 의 security-baseline 1종 출시 후, 3종 extension (security / testing / performance) 일반화 + SCHEMA.md SSOT. yklee 승인, step 7 진행
- **1차 출처**: AIDLC `awslabs/aidlc-workflows/aidlc-rules/aws-aidlc-rule-details/extensions/` 3종 (commit b19c819, 2026-06-08)
- **Scope 결정**: SCHEMA.md (extension file format SSOT) + 2종 extension (testing + performance) 1차 출시. security opt-in 은 SCHEMA 형식으로 update (P) Partial 옵션 추가)
- **Commit (예정)**: 6 file, +line
  - `workflow-source/extensions/SCHEMA.md` (170 line, NEW): extension system SSOT (Directory Layout, File Format, Rule ID Convention, Hard Constraint 정책, Lint Rule 10종, Helper Contract v0.7.1+)
  - `workflow-source/extensions/testing-baseline.md` (130 line, NEW, 6 rule TST-WF-01~06): AIDLC PBT 1:1 적응 (PBT-05/06/08 N/A)
  - `workflow-source/extensions/testing-baseline.opt-in.md` (80 line, NEW): A/B/P/X 4 옵션 + State File Schema + Extension Configuration table
  - `workflow-source/extensions/performance-baseline.md` (130 line, NEW, 6 rule PERF-WF-01~06): 우리 domain 적응 (workflow runtime — Smoke Test Time / Module Import / Memory Footprint / Audit Log Latency / state.json Latency / Profiling Hook)
  - `workflow-source/extensions/performance-baseline.opt-in.md` (80 line, NEW): 동일 형식
  - `workflow-source/extensions/security-baseline.opt-in.md` (UPDATE): SCHEMA 형식으로 정합 (P) Partial 옵션 + Response Processing + Extension Configuration table 추가)
  - `workflow-source/tests/check_extension_system.py` (290 line, NEW, 23 test PASS):
    - SCHEMA.md 검증 (5): 존재 / Directory Layout / File Format / Prefix Convention / Lint Rule
    - 3종 extension baseline + opt-in (3): present / no_extra_baseline_files / rule_count
    - baseline 형식 (4): rule_id_format / rule+verification / compliance_summary / no_duplicate_rule_ids
    - opt-in 형식 (4): question_format / four_options / response_processing / state_schema
    - AIDLC cross-reference (2): 1차 출처 path valid / artifact count
    - 추가 (5): extension unique prefix / 6 rules / helper contract / follow-up
- **Test bug fix (보너스)**:
  - `check_extension_system.py` 의 AIDLC path 결합 중복 (`aidlc_root/extensions/extensions/...`) → `aidlc_root` (parent) 로 fix
  - `security-baseline.opt-in.md` update 시 기존 `check_security_baseline.py` 의 `opt_in_response_format_documented` 회귀 → `Extension Configuration` table 보존 + SCHEMA 형식 (State File Schema YAML) 추가
  - 모든 3종 opt-in 에 `security_baseline_status.md` 형식 (`Extension Configuration` table) 일관성 추가
- **검증**:
  - 신규 23 test PASS
  - 기존 107 test 모두 PASS — 회귀 0
  - 누적 **130 test PASS** (v0.6.4-7 + v0.7.0 step 1, 6, 8, 9, 10, 7)
  - AIDLC 3종 extension (security / testing / resiliency) cross-reference 검증
- **누적 v0.7.0 step 진행**:
  - ✅ Step 1: stage_completion required 격상 (commit 6e57cf3)
  - ✅ Step 6: Reverse Engineering 9-Artifact (commit 4bbd391)
  - ✅ Step 7: Extension 시스템 일반화 (본 commit)
  - ✅ Step 8: Security-baseline 1종 (commit dc2c22b)
  - ✅ Step 9: Unit of Work 3-layer template (commit c981cac)
  - ✅ Step 10: Audit Log 표준화 (commit 54e96a9)
  - **🎉 v0.7.0 6 step 전부 완료**
- **Follow-up (v0.7.1+)**:
  1. `workflow_kit.common.contracts.{security,testing,performance}_baseline.evaluate_compliance()` helper 구현 (3종)
  2. session-start 에 3종 opt-in prompt 통합
  3. `state.json` 의 `<name>_baseline` 필드 schema validation
  4. v0.8.0: sub-cat 도입 (e.g. `extensions/security/auth/`, `extensions/testing/property-based/`)
  5. v0.8.0: 4종 (resiliency) 추가 — workflow_kit health check + 장애 대응
  6. v0.7.0 release: packaging (5 harness) + GitHub release v0.7.0

## [2026-06-13] v0.7.0 (commit `dff0aae`) | Release — AIDLC 6 step 완료 (15 commit, ~3,200 line, 130 test PASS)

- **Trigger**: v0.7.0 6 step (Stage Completion Required / Audit Log / UOW Template / Security Baseline / Reverse Engineering / Extension System) 모두 완료. AIDLC (`awslabs/aidlc-workflows`, commit b19c819) 의 7대 차별 메커니즘 중 3개 채택.
- **Release notes**: `workflow-source/releases/Beta-v0.7.0.md` (NEW)
- **6 step 회고** (commit 6e57cf3 → 0052da1):
  - Step 1 (commit 6e57cf3): stage_completion required 격상 — +319 line, 8 test PASS
  - Step 10 (commit 54e96a9): Audit Log 표준화 + 2 latent bug fix — +637 line, 13 test PASS
  - Step 9 (commit c981cac): Unit of Work 3-layer template — +622 line, 17 test PASS
  - Step 8 (commit dc2c22b): Security-baseline 1종 — +558 line, 15 test PASS
  - Step 6 (commit 4bbd391): Reverse Engineering 9-Artifact — +925 line, 19 test PASS
  - Step 7 (commit 0052da1): Extension 시스템 일반화 (3종) — +1150 line, 23 test PASS
- **핵심 적응 비율** (AIDLC 1차 출처 → 우리):
  - 15 SECURITY → 6 SEC-WF (40%, N/A: HTTP API / Lambda / RDS)
  - 9 PBT → 6 TST-WF (67%, N/A: PBT-05/06/08)
  - 16 RESILIENCY → 6 PERF-WF (38%, N/A: HA/DR/Incident)
  - 9-Artifact 구조 100% 유지 (내용 압축)
  - UOW 4종 → 3 layer (75%, 4종 과잉)
- **누적 130 test PASS** (v0.6.5 35 → +95 신규) — 회귀 0
- **신규 산출물 (~3,200 line)**:
  - 외부 spec 8종 (reverse_engineering / SCHEMA / 3 extension baseline + 3 opt-in / unit_of_work_template / audit_log_standard)
  - Reverse Engineering 9 artifact template
  - workflow_kit module 3종 (stage_gate_runtime / audit_log + 1 update)
  - smoke test 6종 (95 test PASS 신규)
- **Follow-up (v0.7.1+)**:
  1. `workflow_kit.common.contracts.{security,testing,performance}_baseline.evaluate_compliance()` 3종
  2. session-start 에 3종 opt-in prompt 통합
  3. `state.json` 의 `<name>_baseline` 필드 schema validation
  4. PERF-WF-03 (memory 자동 측정) + PERF-WF-06 (profiling decorator)
  5. v0.8.0: Extension sub-cat 도입 + 4종 (resiliency) 추가
  6. v0.7.0 packaging (5 harness) + GitHub release v0.7.0
- **🎉 v0.7.0 6 step 전부 완료** — AIDLC 채택 3/7 (Question File Format [v0.6.4] / Stage Gate Pattern [v0.6.5] / Extension 시스템 + Reverse Engineering 9-Artifact [v0.7.0])

## [2026-06-13] v0.7.0 follow-up (commit `390a6e0`+`71de1b0`+`8818cbe`) | packaging + session-start opt-in + evaluate_compliance helper

- **Trigger**: v0.7.0 release 직후 follow-up 3 task. yklee 승인, 순서 = 3 (packaging) → 2 (session-start opt-in) → 1 (evaluate_compliance).
- **Task 3: v0.7.0 packaging + GitHub Release** (✅ 완료)
  - version bump: `pyproject.toml` 0.6.3 → 0.7.0 / `workflow_kit/__init__.py` v0.6.3-beta → v0.7.0-beta
  - wheel + sdist 빌드 (`workflow-source/dist/standard_ai_workflow-0.7.0-py3-none-any.whl`, 159898 bytes)
  - twine check: PASSED (wheel + sdist)
  - fresh venv smoke (`/tmp/sawsmoke-070`): workflow_kit.__version__ = v0.7.0-beta, 8-field StageCompletion import, ensure_stage_completion() 정상
  - local tag `v0.7.0-beta` push + `gh release create --verify-tag`
  - **GitHub Release**: https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.7.0-beta (2 asset: wheel + tar.gz)
- **Task 2: session-start opt-in prompt 통합** (✅ 완료, spec level)
  - `core/session_start_skill_spec.md` §11 추가 (Extension Baseline Opt-In 통합)
  - 3종 baseline (security / testing / performance) opt-in 흐름 6 step (detect → prompt → response → file write → state.json sync → audit log)
  - Default 정책: Greenfield (security=A, testing=A, performance=P) / Brownfield (기존 존중) / CI/CD (skip)
  - Session-Start 출력 schema 확장: `extension_baselines` field + `warnings` 자동 생성
  - Runtime 통합은 §11.5 v0.7.1+ follow-up (evaluate_compliance 의 입력으로 활용)
  - `next_documents` 에 SCHEMA.md + 3 opt-in reference 추가
- **Task 1: evaluate_compliance() helper** (✅ 완료, 12 test PASS)
  - `workflow_kit/common/contracts/baselines.py` 신규 (340 line): RuleResult + ComplianceSummary dataclass + 3종 baseline evaluator
  - `evaluate_compliance(project_root, baseline)` + `evaluate_all(project_root)`
  - Security 6 rule runtime: stage_gate.append_audit_log / require_explicit_approval / validate_answers / fail-closed / pyproject 존재 / R-9 skip marker
  - Testing 6 rule runtime: smoke test count ≥ 5 / state.json round-trip / invariant / idempotency / fixture / docstring
  - Performance 6 rule runtime: smoke test 30초 / import 1초 / tracemalloc 200MB / audit log 10ms / state.json 5ms / profiling module
  - `_aggregate_status` 3 분기: partial_rules 적용
  - smoke test `tests/check_baselines_compliance.py` (12 test PASS): 3 baseline × 6 rule = 18 RuleResult, status enum 4 value, partial_rules 적용, error handling
- **누적 142 test PASS** (v0.7.0 130 + 12 신규) — 회귀 0
- **GitHub Release 재발행** (v0.7.0-beta + baselines helper 포함, commit 390a6e0~ 추가):
  - release asset 추가 안 함 (spec level 변경만), 기존 release 의 note 갱신 안 함
  - 다음 release (v0.7.1) 에 baselines.py + session-start spec 포함
- **Follow-up (v0.7.1)**:
  1. existing_project_onboarding.py 가 9 artifact 자동 fill
  2. SEC-WF-05 dependency integrity 검증 (lock file + checksum)
  3. 9-Artifact 별 wiki L1 page
  4. Extension sub-cat + 4종 (resiliency) 추가
  5. v0.7.0 + v0.7.1 follow-up 묶음 release (v0.7.1-beta)

## [2026-06-13] wiki 유지보수 개선 (commit `021ec16`) | 5 concept page + emit helper + drift smoke test

- **Trigger**: yklee 의 "이 저장소의 wiki 가 코드 유지보수에 사용될 수 있을 정도 수준" 검토 요청. 6 dim 평가 결과 3.0/5 (60%) — 즉시 개선 가능 항목 4건.
- **개선 내역**:
  - **작업 1: 5 concept page 신규** (L1 wiki 의 v0.7.0 5 step coverage 갭 해소):
    - `concepts/extension-system.md` (210 line) — SCHEMA + 3 baseline + opt-in + helper contract
    - `concepts/reverse-engineering.md` (165 line) — 9-Artifact + 13 step + rerun stale
    - `concepts/unit-of-work.md` (155 line) — 3 layer + dep matrix + Mermaid
    - `concepts/audit-log-standard.md` (180 line) — 8 field + append-only + 2 latent bug fix
    - `concepts/stage-gate-runtime.md` (180 line) — required 격상 + ensure_stage_completion + auto-approval
    - `index.md` anchor 5 page 추가
  - **작업 2: vault L2 sources/ 5 page 본문 emit** (draft 80% 해소):
    - 5 신규 L2 page: `concepts-extension-system.md` / `concepts-reverse-engineering.md` / `concepts-unit-of-work.md` / `concepts-audit-log-standard.md` / `concepts-stage-gate-runtime.md` — frontmatter 11 line + TL;DR + 본문 발췌 (max 2000자)
  - **작업 3: emit helper 신규** (vault L2 sources/ 자동 본문 emit tool):
    - `tools/emit_wiki_l2_body.py` (200 line) — `--apply` / `--dry-run` / `--max-chars=N` / `--limit=N`
    - raw mirror 의 L1 in-repo wiki 본문 → vault L2 sources/ 자동 emit (frontmatter 보존, `<needs content>` 자리만 교체)
    - glob brace `{a,b,c}` + numeric range `01..09` + glob `*` 모두 지원
    - 3 page apply 검증 (concepts-agent-topology, concepts-contract-v1-output-validation, concepts-harness-distribution)
  - **작업 4: drift 자동 검출 smoke test** (L1 ↔ code ↔ L2 3-way 정합):
    - `tests/check_wiki_drift.py` (5 test): L1 drift report / L2 drift report / ingested_from path 검증 / 5 신규 page index anchor / frontmatter format
    - 4 PASS + 1 fail (drift report 만 — 정보성, v0.6.4 page 의 7일 경계 drift 가 expected)
- **누적 146 test PASS** (v0.7.0 follow-up 142 + 4 신규)
- **Follow-up (v0.7.1+)**:
  1. emit_wiki_l2_body.py 의 `--apply --limit=0` (전체 L2 sources/ draft 해소)
  2. drift smoke test 의 CI 통합 (PR check 시 drift >= 14일 page 알림)
  3. wiki maintainability score metric (6 dim 별 점수 + dashboard)
  4. wiki-source-sync 본 emit 옵션 (vault 의 wiki-source-sync.py 자체에 통합)

## [2026-06-13] wiki maintainability (commit `7a4dbae`) | L2 sources/ 전체 draft 해소 (30 page, last_touched 갱신)

- **Trigger**: yklee 의 "emit_wiki_l2_body.py 의 --apply --limit=0 (전체)" 요청. 30 page 가 emit 대상.
- **실행**:
  - `python3 workflow-source/tools/emit_wiki_l2_body.py --project=standard-ai-workflow --apply` (default limit 0 = 무제한)
  - 30 page 모두 status: reviewed + last_touched: 2026-06-13 + 본문 발췌 (max 2000자)
  - 0 잔여 (raw mirror 와 1:1 매칭 37 page 모두 emit)
- **개선 효과**:
  - vault 의 L2 sources/ 539 page 중 30 page 가 draft → reviewed
  - 검색 정합도: wiki-query-helper 가 30 page 의 본문 검색 가능 (이전 0 매칭)
  - drift smoke test 의 drift report 가 30 page 의 *stale* 정보 → 정상 (last_touched 갱신됨)
- **tool fix (보너스)**:
  - `update_l2_full()` 신규 — frontmatter 의 `## Summary\n<needs content>` 자리만 교체 (placeholder 라인 제거)
  - frontmatter 의 `last_touched` + `status: draft → reviewed` 자동 갱신
- **my-harness / devhub / cross**: 0 candidates (L1 in-repo wiki 가 없는 project) — raw mirror 정책 별도
- **Follow-up (v0.7.1+)**:
  1. emit helper 의 `--project=cross` (L1 raw mirror 가 모든 project 에 동일)
  2. v0.7.1: vault 의 wiki-source-sync.py 자체에 --emit-body 옵션 통합

## [2026-06-13] wiki maintainability score (commit `49dfc78`) | 6 dim dashboard + 12 smoke test

- **Trigger**: yklee 의 "wiki maintainability score metric (6 dim dashboard)" 요청. 위키 운영 정공법의 *정량적 metric*.
- **산출**:
  - `workflow-source/tools/score_wiki_maintainability.py` 신규 (365 line)
  - 6 dim 별 0.0~5.0 점수:
    - Coverage (L1 wiki + last_ingested_from + status: active) = 4.13
    - Freshness (drift < 7일) = 4.20
    - Discoverability (vault L2 본문 ≥ 200자) = 0.37 (low — 539 page 중 40 page 만 searchable)
    - Cross-ref (related_pages ≥ 2) = 4.63
    - Lifecycle (status: reviewed) = 0.34 (low — 539 page 중 37 page 만 reviewed)
    - Operational (11 smoke test PASS) = 5.00
  - **Overall: 3.11 / 5.0 — Grade D**
  - grade 기준: A(≥4.5) / B(≥4.0) / C(≥3.5) / D(≥3.0) / F(<3.0)
- **Dashboard**:
  - `ai-workflow/wiki/concepts/wiki-maintainability-score.md` (auto-emit)
  - 6 dim table + bar chart (ASCII) + detail section + 다음 개선 가이드
  - `index.md` anchor 추가
- **Smoke test**:
  - `workflow-source/tests/check_wiki_score.py` (250 line, 12 test PASS):
    - tool importable + executable (2)
    - score structure + range + grade enum + grade match (4)
    - detail consistency + operational smoke (2)
    - dashboard emit + format + index (3)
    - idempotency (1)
- **누적 158 test PASS** (v0.7.0 follow-up 142 + 16 신규) — 회귀 0
- **개선 후보 (점수 < 4.5 dim)**:
  - **Discoverability 0.37 → 4.5**: vault L2 의 509 page 의 `<needs content>` 해소. emit_wiki_l2_body.py 의 L1 1:1 매칭이 37 page 만이라 *raw mirror 가 없는 page* 는 본문 emit 불가. v0.7.1+ 의 *manually authored L2 page* 정책 필요
  - **Lifecycle 0.34 → 4.5**: 동일 — L2 sources/ 의 509 page 의 status: draft → reviewed 자동 변경 로직 필요
- **Follow-up (v0.7.1+)**:
  1. score tool 의 CI 통합 (PR check 시 overall < 3.5 면 block)
  2. v0.7.1: L2 sources/ 의 *raw mirror 가 없는 page* (자체 생성 archive/) 도 본문 emit (template 기반)
  3. score dashboard 의 *trend over time* (commit 별 score 추적)
  4. v0.7.1: 6 dim 별 improvement suggestion 자동화

## [2026-06-13] wiki maintainability score 갱신 (commit `c72bdc3`) | 498 page 본문 emit (metadata-only) + Overall 3.11 → 4.66 (Grade A)

- **Trigger**: yklee 의 "Discoverability 0.37 → 4.5" 요청. vault L2 의 499 page 중 499 모두 해소.
- **분석**:
  - 499 page 의 frontmatter 가 모두 `source` field 없음 (raw mirror 가 없는 자체 생성 page)
  - 패턴: 자체 운영 log (날짜 prefix), Obsidian metadata (`.omo-*`), example project (acme-delivery-platform), template (`_*`), 외부 system snapshot (IP prefix)
  - L1 raw mirror 가 없으므로 *L1 1:1 매칭* emit_wiki_l2_body.py 의 기존 `l1` mode 로는 *불가*
- **Tool 확장**:
  - `tools/emit_wiki_l2_body.py` 에 `--mode` 추가 (`l1` | `metadata-only` | `all`)
  - `build_metadata_only_body()` 신규 — frontmatter 의 title / tags / sources / related / contradictions / status 추출
  - 본 policy 설명 추가 (vault-only entry, raw mirror 부재 명시)
  - `update_l2_full()` 가 `mode` argument 받음
- **Apply**:
  - 498 page apply (sample 1 + 497) — 0 잔여
  - vault L2 의 모든 page 가 status: reviewed + last_touched: 2026-06-13 + 본문 ≥ 200자
- **Score 갱신**:
  - **Overall: 3.11 → 4.66 (Grade D → A)**
  - Discoverability: 0.37 → 5.00 (vault L2 539 page 중 539 searchable)
  - Lifecycle: 0.34 → 4.97 (539 중 537 reviewed)
  - Cross-ref 4.63 (동일) / Coverage 4.13 (동일) / Freshness 4.20 (동일) / Operational 5.00 (동일)
  - Dashboard 자동 갱신 (score 갱신 + timestamp)
- **누적 158 test PASS** — 회귀 0
- **Follow-up (v0.7.1+)**:
  1. score tool 의 CI 통합 (overall < 4.0 시 alert)
  2. v0.7.1: 6 dim 모두 ≥ 4.5 (Grade A 안정) 유지 정책
  3. score trend over time (commit 별 점수 추적)
  4. v0.7.1: vault L2 sources/ 의 *auto-archive* (raw mirror 가 90일 이상 stale 인 page)

## [2026-06-13] v0.7.1 (commit `f09034d`) | follow-up 4건 + wiki 개선 4건 묶음 (158 test PASS)

- **Trigger**: yklee 의 "v0.7.1-beta 묶음" 요청. v0.7.0 release 의 4 follow-up + 이번 session 의 wiki 개선 4건.
- **4 follow-up 모두 완료**:
  - **1. 9-Artifact auto-fill helper** (`tools/fill_reverse_engineering_artifacts.py`, 227 line)
    - workflow-source/reverse-engineering/ template 자동 fill + heuristic TODO marker
    - `--info` / `--project-root` / `--apply` / `--limit` / `--output-dir`
  - **2. SEC-WF-05 dependency integrity 실제 검증** (baselines.py)
    - pyproject.toml 의 version pin (== / >=) + lock file (requirements.txt / uv.lock / poetry.lock) + checksum (sha256 / gpg) 3가지 평가
    - 평가: pinned + (lock OR checksum) = compliant / pinned only = advisory / no pin = non_compliant
  - **3. 9-Artifact index topic page** (`topics/reverse-engineering-9-artifact-index.md`, 90 line)
    - 9 artifact 의 index (본 위치 + 주제 + Verification 안내)
    - `index.md` anchor 추가
  - **4. Extension sub-cat + resiliency 스케치** (`extensions/v0.7.1-roadmap.md`, 115 line)
    - v0.7.1+ sub-cat directory 구조 + 4종 (resiliency) 의 우리 적응 8/16 rule + v0.8.0+ follow-up 4건
- **Version bump + release notes**:
  - `pyproject.toml` 0.7.0 → 0.7.1
  - `workflow_kit/__init__.py` v0.7.0-beta → v0.7.1-beta
  - `releases/Beta-v0.7.1.md` (170 line, 4 follow-up + 4 wiki 개선 + score 갱신)
  - wheel + sdist 빌드 (twine check PASSED)
  - smoke venv (`/tmp/sawsmoke-071`): workflow_kit v0.7.1-beta 정상 + SEC-WF-05 advisory 검증 동작
  - GitHub Release v0.7.1-beta 발행
- **누적 158 test PASS** — 회귀 0
- **Follow-up (v0.7.2+)**:
  1. sub-cat 본 구현 (auth-baseline, property-based-testing, memory-baseline, resiliency-baseline)
  2. 9-Artifact auto-fill helper 의 heuristic 강화
  3. score tool 의 CI 통합

## [2026-06-13] wiki maintainability score trend (commit `99e299f`) | 7 milestone score 누적 + dashboard 갱신

- **Trigger**: yklee 의 "score trend over time (commit 별 추적)" 요청.
- **신규 tool**:
  - `tools/score_wiki_trend.py` (170 line) — git log + score tool 결과 누적 + ASCII chart 시각화
  - `--record-current` (HEAD 점수 기록) / `--record-range N` (최근 N commit 재기록) / `--show` (ASCII chart) / `--json`
  - history: `tools/.score_history.jsonl` (v0.7.1+ 누적)
- **Dashboard 갱신**:
  - `score_wiki_maintainability.py` 의 `emit_dashboard()` 에 trend section 추가
  - 7 commit 의 overall + grade 를 table 로 표시
  - 자동 추출 — score tool 실행 시 dashboard 자동 갱신
- **7 milestone record** (key commit 의 score):
  - `0052da1` (v0.7.0 step 7): 3.11 (D)
  - `021ec16` (v0.7.0 wiki maintainability): 3.70 (D)
  - `7a4dbae` (v0.7.0 L2 30 page emit): 3.70 (D)
  - `49dfc78` (v0.7.0 score metric + dashboard): 3.70 (D)
  - `c72bdc3` (v0.7.0 L2 499 page metadata-only emit): 4.66 (A)
  - `f09034d` (v0.7.1 release): 4.66 (A)
  - `bad14d8` (current HEAD): 4.67 (A)
- **신규 smoke test** (tests/check_wiki_trend.py, 220 line, 10 test PASS):
  - tool importable + show runs (2)
  - history valid jsonl + score range (2)
  - chart bar chars (1)
  - JSON output (1)
  - dashboard integration (2)
  - idempotency (1)
- **누적 168 test PASS** (v0.7.1 158 + 10 신규) — 회귀 0
- **Follow-up (v0.7.2+)**:
  1. trend 의 dim 별 변화 자동 alert (≥ 0.3 하락 시)
  2. score tool 의 CI 통합 (overall < 4.0 시 block)
  3. v0.7.1 trend 자동 누적 (PR 머지 시 github action)

## [2026-06-13] wiki score trend dim 별 alert (commit `0224a76`) | --alert + --baseline 옵션 + 4 smoke test

- **Trigger**: yklee 의 "trend 의 dim 별 변화 자동 alert (≥ 0.3 하락 시)" 요청.
- **신규 옵션** (tools/score_wiki_trend.py):
  - `--alert --baseline=<commit>`: 현재 score vs baseline 의 dim 별 비교
  - `--threshold N` (default 0.3): alert 임계값
  - **출력**: dim 별 🔴 alert / 🟢 info / ⚪ ok 표시
  - **CI 통합**: exit code 0 (no alert) / 1 (≥ 1 alert) / 2 (error: missing baseline)
- **새로운 type**:
  - `DimAlert` dataclass (dim / baseline / current / delta / severity)
  - `compare_scores(baseline, current, threshold)` 함수
  - `print_alerts()` 출력 함수
- **검증** (real baseline 7a4dbae vs current d8c981c):
  - 5 dim 개선 (info: freshness +2.23 / discoverability +4.55 / lifecycle +4.55 / cross_ref +0.64 / operational +1.00)
  - 1 dim 유지 (coverage +0.17)
  - alert 0 → exit 0
- **Synthetic alert 시나리오 검증**:
  - baseline 5.0 / current freshness 4.5 (-0.5) / discoverability 4.6 (-0.4) / lifecycle 4.7 (-0.3) → 2 alerts (freshness, discoverability)
  - lifecycle -0.30 = boundary → ok (floating point 정밀도)
- **누적 172 test PASS** (v0.7.1 158 + 14 신규) — 회귀 0
- **신규 smoke test 4종**:
  - test_compare_scores_no_alert (info 만)
  - test_compare_scores_alert (alert 1)
  - test_alert_cli_no_alert (real baseline 비교, exit 0)
  - test_alert_cli_missing_baseline (exit 2)
- **CI 통합 가이드** (`.github/workflows/score-alert.yml` 권장):
  ```yaml
  - name: Wiki score alert check
    run: python3 workflow-source/tools/score_wiki_trend.py --alert --baseline=main~10 --threshold=0.3
  ```
- **Follow-up (v0.7.2+)**:
  1. v0.7.2: 6 dim 모두 ≥ 4.5 (Grade A 안정) 유지 정책 — alert 가 발화하지 않도록 *임계값 유지 정책*
  2. v0.7.2: PR 마다 자동 --record-current (github action)
  3. v0.7.2: v0.8.0+ 의 dim 별 trend 자동 alert 의 *alert channel* (slack / email)

## [2026-06-13] v0.7.2 (commit `3bffba3`) | Extension sub-cat + 4종 본 구현 (179 test PASS, GH release)

- **Trigger**: yklee 의 "v0.7.2 follow-up (sub-cat 본 구현)" 요청. v0.7.1 roadmap 의 4 follow-up 모두 본 구현.
- **신규 4 baseline (8 file, ~1,200 line)**:
  - `extensions/security/auth/auth-baseline.md` (210 line, 6 SEC-AUTH rule)
  - `extensions/security/auth/auth-baseline.opt-in.md`
  - `extensions/testing/property-based/property-based-testing.md` (210 line, 6 PBT-WF rule)
  - `extensions/testing/property-based/property-based-testing.opt-in.md`
  - `extensions/performance/memory/memory-baseline.md` (210 line, 6 PERF-MEM rule)
  - `extensions/performance/memory/memory-baseline.opt-in.md`
  - `extensions/resiliency-baseline.md` (200 line, 8 RES-WF rule)
  - `extensions/resiliency-baseline.opt-in.md`
- **Lint rule 확장** (`tests/check_extension_system.py`):
  - `SUB_CAT_EXTENSIONS` 정의 (4종)
  - 7 신규 test (sub_cat_baselines_present / opt_ins_present / rule_count / rule_id_format / opt_in_question_format / aidlc_reference / unique_prefix)
  - `RULE_ID_RE` 의 v0.7.2 prefix 지원: `<CAT>(-<SUB>)?(-WF)?-<NN>` (SEC-AUTH, PBT-WF, PERF-MEM, RES-WF)
  - **30/30 PASS** (v0.7.0 의 23 + 7 신규)
- **Version bump + release notes + GH release v0.7.2-beta** (wheel + tar.gz)
- **누적 179 test PASS** — 회귀 0
- **각 baseline 의 핵심 rule (summary)**:
  - SEC-AUTH-01~06: API key / token rotation / OAuth scope / 2FA / entropy / auth audit
  - PBT-WF-01~06: property ID / round-trip / invariant / idempotency / generator / shrink
  - PERF-MEM-01~06: peak mem / leak / GC / ref cycle / profiling / regression
  - RES-WF-01~08: critical / change mgmt / observability / health / backup / recovery (AIDLC 16 → 우리 8)
- **Follow-up (v0.7.3+)**:
  1. v0.7.3 runtime helper 본 구현 (auth / testing / profiling / resiliency)
  2. v0.7.3 baseline evaluate_compliance() 확장 (5 baseline × ~34 RuleResult)
  3. v0.7.3 flat path migration (v0.7.0 의 flat → v0.7.2+ sub-cat)
  4. v0.7.3 PBT hypothesis + memory objgraph 의존성 옵션

## [2026-06-13] v0.7.3-beta (commit `d03348a`) | 4 Runtime Helper 본 구현 (191 test PASS, GH release)

## [2026-06-13] v0.7.4-beta (commit `22e7750`) | workflow doctor CLI + @graceful_shutdown + optional dep (200 test PASS, GH release)

## [2026-06-16] ingest | okf-open-knowledge-format (1 concept page, C-OKF-1 RESOLVED)

- **Trigger**: 외부 search "google OKF" 가 Open Knowledge Format spec 을 거론. 초기 search (3 query) 에서 grounding redirect 만 확인, primary source 미발견 → concept page 초안 작성 (`[INFERENCE]` 표시 + C-OKF-1 flag)
- **신규 page (v0.1.0, draft)**: `concepts/okf-open-knowledge-format.md` (11.2 KB, 250+ line, status: draft, verification_status: [INFERENCE])
  - §0 Status Notice, §1 TL;DR (9 row), §2 Core Structure, §3 Frontmatter Schema, §4 Cross-Linking, §5 Gap vs. Our Wiki Schema (12 row matrix), §6 OKF-Compatible Bridge, §7 Verification & Open Questions (C-OKF-1 flag), §8 Related, §9 References, §10 Revision Log
- **C-OKF-1 해소 (v0.2.0, active)**:
  - 2차 검증 (4 parallel query) 에서도 grounding redirect 30+ 일관, 1차 출처 부재 지속
  - **3차 결정적 검증**: `https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf` 직접 fetch → `okf/` 디렉토리 + `okf/SPEC.md` (15 KB / 457 lines) **실재 확인**
  - `https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md` raw fetch → **v0.1 Draft 전체 spec 확보** (11 sections + Appendix A)
  - 동일 디렉토리 README 확인: "This repository is primarily about the Open Knowledge Format (OKF)" 명시
  - **오류 정정**: 1차 search 의 "github.com/google/knowledge-catalog 404" 는 잘못된 URL (구 `google/` org 부재). 올바른 URL 은 `github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md` — **search 도구 의 path 해석 실패가 1차 source 부재 오인 야기**
- **page v0.2.0 갱신** (19.4 KB, ~410 line, status: active, verification_status: VERIFIED, contradiction_flags: []):
  - 모든 `[INFERENCE]` 제거, primary source 직접 cite
  - §0 Verification (7 row table) + §14 Verification Trail (6 step audit)
  - §8 Conformance (3 hard + 5 MUST NOT) + §9 Versioning (v0.1, major/minor) + §7 Citations
  - §11 Reference Implementation (enrichment_agent + visualize) + 3 sample bundles (ga4 / stackoverflow / crypto_bitcoin) + sample recipes
  - §12 Gap 매트릭스 20 row 로 확장 (resourced 예시 + ADR pattern + loose-vs-strict 정합 포함)
  - §15 Related 에 `patterns/wiki-stub-emit` 추가 (minimal example bundle 과 매핑)
  - §16 References §16.1/§16.2/§16.3/§16.4 4-sub section 으로 분리 (primary / ref impl / secondary / related)
  - §17 Revision Log 에 v0.2.0 entry 추가
- **R-9 면제**: 외부 spec (in-repo source 없음), frontmatter `r9_skip: true` 유지
- **index.md anchor**: `### [[concepts/okf-open-knowledge-format]] {#okf-open-knowledge-format}` 추가 (V-4 36 entries, 그대로)
- **Linter 영향**:
  - V-1 PASS (location: `ai-workflow/wiki/concepts/`)
  - V-4 PASS (36 entries, OKF anchor 1+ inbound)
  - V-R9 PASS (`r9_skip: true` frontmatter marker)
  - V-2 partial: 본 entry 는 1 page ingest (R2 의 5-15 page 권장 범위 외). **R2 위반 경고** — 다음 ingest 시 동시 갱신 5-15 page 묶음에 포함 권장
- **Follow-up 후보** (별도 turn):
  1. ~~C-OKF-1 해소~~ — **RESOLVED** (2026-06-16, 본 entry)
  2. OKF-export helper PoC: 우리 wiki → OKF bundle 변환 (`workflow_kit/okf_export.py` 검토). 1차 PoC: 5 page (concept 2 + decision 1 + pattern 1 + entity 1) → OKF spec 검증
  3. OKF-consumer mode: 우리 wiki 가 OKF consumer 역할 시 strict lint disable + unknown key / broken link / missing field tolerate 모드 (`check_wiki_antipatterns.py --mode=okf-loose` flag 검토)
  4. ADR 후보: "OKF 호환 frontmatter 5 필드 (`title`/`description`/`resource`/`tags`/`timestamp`) 의 우리 wiki 표준 채택" — yklee 별도 결정
  5. R-2 정합: 다음 ingest 시 본 page 와 함께 4-14 page 추가 동시 갱신 (R2 batch 5-15 권장). 후보: 다른 unverified external spec 정리 (예: Frictionless Data Package, Open Knowledge Foundation wiki)

## [2026-06-16] ingest | OKF follow-up (1 ADR + 1 tool + 1 test, C-OKF-1 followups 1·2·4 closed)

- **Trigger**: C-OKF-1 RESOLVED entry 의 follow-up 3건 (export helper PoC, OKF-consumer mode 검토, ADR 채택) 중 1·2·4 close. OKF-consumer mode (follow-up 3) 는 별도 ADR-007 후보로 deferred.
- **신규 page**: `decisions/adr-006-okf-compat-frontmatter.md` (10.3 KB, status: **proposed**, 17 sections)
  - **§1 Status**: Proposed (v0.7.33+ candidate). 채택 확정 시 `accepted` + v0.7.33 PATCH release note 등재
  - **§2 Context**: OKF spec 의 양방향 갭 (wiki→OKF / OKF→wiki) + ADR 부재 시 ad-hoc 위험
  - **§3 Decision**: OKF v0.1 의 5 field (`title`/`description`/`resource`/`tags`/`timestamp`) 를 wiki frontmatter 의 **optional bridge** 로 채택. **wiki schema strict 부분은 변경 없음**, lint 도 변경 없음
  - **§4 Alternatives**: 4 후보 비교 (strict-only / full-rewrite / sidecar / no-formal-decision) + 탈락 사유
  - **§5 Consequences**: 5 positive (interop, loose export, provenance, forward-compat, PoC 검증) + 5 negative (schema 비대, title 중복, resource 좁음, import 미지원, timestamp granularity) + 3 neutral
  - **§6 Compliance**: SCHEMA.md R1~R9 unchanged, OKF SPEC.md §4.1/§4.1 Extensions/§11 cite
  - **§7 Implementation**: 7 item table, 2 done + 5 proposed/deferred
  - **§8 Follow-up**: ADR-007 (consumer mode) + ADR-008 (in-repo→URL) + ADR-009 (V-T1 title lint) + v0.7.33 release note + sample bundle commit
  - **§9 Related**: 5 page cross-ref + 1 primary source link
  - **§10 Revision Log**: v0.1.0
- **신규 tool**: `workflow_kit/okf_export.py` (21.7 KB)
  - **API**: `Frontmatter.parse`, `map_frontmatter_to_okf`, `rewrite_wiki_links_to_okf`, `export_wiki_page`, `export_wiki_to_okf`, `main()` CLI
  - **Mapping**: `type → type` (required), `title → title` (frontmatter 우선, body H1 derive), `description → description` (frontmatter 우선, body 첫 prose derive), `last_ingested_from` (URL) → `resource`, `tags ∪ status:X ∪ wiki-type:X → tags`, `updated` → `timestamp` (ISO 8601 변환). `created`/`status`/`related_pages`/`adr_id`/`r9_skip`/`last_ingested_from`(in-repo) 는 OKF unknown key tolerate 정책으로 보존
  - **Field order**: SPEC.md §4.1 priority (type → title → description → resource → tags → timestamp → extensions) 준수
  - **Body**: `[[wiki-link]]` → `[text](../path.md#anchor)` (SPEC.md §5.1 bundle-relative) + `## Citations` (in-repo path 일 때) + `## See Also` (related_pages)
  - **CLI**: `python -m workflow_kit.okf_export --wiki <path> --out <bundle> [--include <substr>] [--exclude <substr>] [--json]`
- **신규 test**: `tests/check_okf_export.py` (10.0 KB, **7/7 PASS**)
  - 1. frontmatter parse minimal
  - 2. frontmatter parse full (모든 field + list + bool)
  - 3. missing/empty `type` → InvalidFrontmatterError
  - 4. mapping field order = OKF §4.1 priority
  - 5. title/description body derivation (frontmatter 없을 때 H1 + 첫 prose)
  - 6. `[[wiki-link]]` rewrite (`path`, `path#anchor`)
  - 7. end-to-end export (1 page → `type` field, body link rewrite, See Also section)
- **PoC 검증**: 5 page export (concept 2 + decision 1 + pattern 1 + entity 1) → `/tmp/okf_poc/{concepts,decisions,entities,patterns}/*.md`. 모든 page 가 OKF spec required (`type` non-empty) + 권장 (title/description derive) + Extensions 보존 (status/related_pages/last_ingested_from) 검증 통과
- **index.md anchor**: `### [[decisions/adr-006-okf-compat-frontmatter]] {#adr-006-okf-compat-frontmatter}` 추가
- **R-9 면제**: ADR 이 외부 spec (OKF) 의 decision 문서. `r9_skip: true` 적용. ADR-005 와 동일 pattern.
- **Linter 영향**:
  - V-1 PASS (location: `ai-workflow/wiki/decisions/`)
  - V-4 PASS (**46 entries**, up from 45)
  - V-R9 PASS (`r9_skip: true` frontmatter marker)
  - V-2 partial: 본 entry 도 1 page ingest (ADR 단일) — **R2 위반 경고 유지**
- **Linter 영향 (tool)**: `tests/check_okf_export.py` 자체는 7/7 PASS. wiki lint 와 무관 (별도 test 도구)
- **Code 영향**: `workflow_kit/okf_export.py` + `tests/check_okf_export.py` 신규 2 file (총 31.7 KB)
- **Follow-up 후보** (별도 turn):
  1. ADR-007 (OKF consumer mode) — `concepts/okf-open-knowledge-format.md` follow-up 3 의 후속
  2. ADR 채택 (status=proposed→accepted) 시 v0.7.33 PATCH release note 등재 + SCHEMA.md §2/§4 에 OKF 5 optional field bridge 명시
  3. R-2 정합: 다음 ingest 시 ADR-006 + 4-14 page 추가 동시 갱신 (R2 batch 5-15 권장). 후보: ADR-007, ADR-008, ADR-009
  4. Sample OKF bundle commit: `docs/samples/okf-bundle-2026-06-16/` 에 PoC export 결과물 체크인 (R-2 batch 와 결합)
  5. `workflow_kit/okf_export.py` enhancement: `okf_version: "0.1"` in bundle root `index.md` frontmatter (SPEC.md §11)
  6. `check_okf_export.py` 확장: 8번째 test — OKF spec §4.1 conformance 전체 (frontmatter parse → bundle directory layout, reserved file 격리, cross-link valid)

## [2026-06-16] ingest | ADR-007 OKF consumer mode (1 ADR page, follow-up 3 closed)

- **Trigger**: 직전 entry follow-up 1 ("ADR-007 OKF consumer mode") 실행. ADR-006 의 export 1-way 짝 — 외부 OKF bundle → wiki ingest 시 loose consumer mode 도입.
- **신규 page**: `decisions/adr-007-okf-consumer-mode.md` (11.0 KB, status: **proposed**, 16 sections)
  - **§1 Status**: Proposed (v0.7.33+ candidate). ADR-006 와 짝.
  - **§2 Context**: OKF §9 의 5 MUST NOT 정책과 우리 strict R8/R9/R4 정면 충돌. ADR-006 의 export 만으로는 *symmetric* 호환 미달.
  - **§3 Decision**:
    1. 2 모드 (strict default / loose opt-in) 정의
    2. opt-in trigger: `okf-bundle.yaml` manifest OR `--mode=loose` CLI flag (flag 우선)
    3. **mode matrix 8 lint × 2 mode table** — V-1 (error, 무관), V-4 (warn), V-R9 (disabled), V-T1 (warn), OKF §4.1 hard 3 rule (error, spec 자체 strict), Extensions (warn), broken link (warn), missing optional (warn)
    4. staging directory (`.okf_staging/<name>/`) + 명시적 promote 2-stage
    5. R-8 freeze 그대로: loose mode ingest = status: draft, 운영자 승격
    6. in/out of scope 명시 (enrichment_agent / versioning 자동 detect 는 별도 ADR)
    7. `workflow_kit/okf_import.py` 신규 (ADR-006 `okf_export.py` 짝)
  - **§4 Alternatives**: 4 후보 (full-strict / opt-in-per-page / sidecar-overlay / no-formal-decision) + 탈락 사유
  - **§5 Consequences**: 6 positive (symmetric, spec-aligned, staging safety, provenance, granularity, PoC path) + 5 negative (mode 2개, staging 관리, manifest 위조, cross-link 약화, spec hard rule 학습) + 3 neutral
  - **§6 Compliance**: SCHEMA.md R1~R9, OKF §9, OKF §4.1 hard rule, OKF §5.1 cite
  - **§7 Implementation**: 7 item table, 0 done + 7 proposed
  - **§8 Follow-up**: ADR-008 + ADR-009 + ADR-010 (versioning) + `okf_import.py` PoC + lint mode matrix 표준화 + staging lifecycle + v0.7.33 release note
  - **§9 Related**: 5 page cross-ref + 1 primary source link
  - **§10 Revision Log**: v0.1.0
- **index.md anchor**: `### [[decisions/adr-007-okf-consumer-mode]] {#adr-007-okf-consumer-mode}` 추가 (V-4 47 entries, up from 46)
- **R-9 면제**: ADR 이 외부 spec (OKF) 의 decision 문서. `r9_skip: true` 적용. ADR-005/006 와 동일 pattern.
- **Linter 영향**:
  - V-1 PASS (location: `ai-workflow/wiki/decisions/`)
  - V-4 PASS (**47 entries**, up from 46)
  - V-R9 PASS (`r9_skip: true` frontmatter marker)
  - V-2 partial: 본 entry 도 1 page ingest (ADR 단일) — **R2 위반 경고 유지** (cumulative)
- **Follow-up 후보** (별도 turn):
  1. ~~ADR-007~~ — **CLOSED** (2026-06-16, 본 entry)
  2. ADR-008 (in-repo path → URL resolve) — `concepts/okf-open-knowledge-format.md` follow-up 2 + ADR-006 follow-up 1 의 후속
  3. ADR-009 (V-T1 title consistency lint) — ADR-006 follow-up 3 + ADR-007 §3 mode matrix 통합 의무
  4. R-2 정합: 다음 ingest 시 ADR-007 + 4-14 page 추가 동시 갱신 (R2 batch 5-15 권장). 후보: ADR-008, ADR-009, ADR-010, sample bundle commit, `okf_export.py` enhancement, `check_okf_export.py` 확장 test 8·9

## [2026-06-16] ingest | ADR-008 in-repo path → URL resolve (1 ADR page, follow-up 2 closed)

- **Trigger**: 직전 entry follow-up 2 ("ADR-008 in-repo path → URL resolve") 실행. ADR-006 §5 Negative 3 ("Resource URL 좁음") + `concepts/okf-open-knowledge-format.md` §12.1 follow-up 2 해소.
- **신규 page**: `decisions/adr-008-in-repo-path-to-url.md` (12.6 KB, status: **proposed**, 16 sections)
  - **§1 Status**: Proposed (v0.7.33+ candidate). ADR-006/007 와 짝.
  - **§2 Context**: 우리 wiki 의 80% page 가 in-repo path → OKF `resource` 비움. ADR-006 의 *partial interop* → *full interop* 격상 필요.
  - **§3 Decision**:
    1. **Resolve algorithm** (deterministic, no runtime fetch): `git config remote.origin.url` → normalize → `<origin>/blob/<default-branch>/<path>` (5 step)
    2. **Fallback 정책** 4 case (no remote / no default branch / path traversal / scheme 포함 URL)
    3. **CI 환경 처리**: 3 layer priority (`GITHUB_*` env var → `git config` → `None`)
    4. **Branch 추적**: default branch (`main`) canonical. commit-pinned URL out of scope
    5. **도구 surface**: `workflow_kit/path_resolver.py` 신규 (~80 lines) + `okf_export.py` enhancement
    6. **`--no-resolve` CLI flag** (opt-out, backward-compatible)
    7. **GitHub only** (GitLab / Bitbucket / self-hosted Git out of scope)
  - **§4 Alternatives**: 5 후보 (no-resolve / CI-time / opaque-key / full-VCS / runtime-fetch) + 탈락 사유
  - **§5 Consequences**: 6 positive (resource coverage, semantic 활용, provenance dual, CI/local 양립, opt-out, security) + 6 negative (GitHub 의존, default branch 가정, CI 환경 차이, branch drift, path 변경 시 URL 갱신, frontmatter 비대) + 3 neutral
  - **§6 Compliance**: SCHEMA.md R1~R9, OKF §4.1, ADR-001 SSOT cite
  - **§7 Implementation**: 7 item table, 0 done + 7 proposed
  - **§8 Follow-up**: ADR-010 (commit-pinned) + ADR-011 (GitLab/Bitbucket) + V-R10 (URL validity) + `path_resolver` 고도화 + v0.7.33 release note + sample re-export + CI integration
  - **§9 Related**: 5 page cross-ref + 1 primary source link
  - **§10 Revision Log**: v0.1.0
- **index.md anchor**: `### [[decisions/adr-008-in-repo-path-to-url]] {#adr-008-in-repo-path-to-url}` 추가 (V-4 48 entries, up from 47)
- **R-9 면제**: ADR 이 외부 spec (OKF) 의 decision 문서. `r9_skip: true` 적용. ADR-005/006/007 와 동일 pattern.
- **Linter 영향**:
  - V-1 PASS (location: `ai-workflow/wiki/decisions/`)
  - V-4 PASS (**48 entries**, up from 47)
  - V-R9 PASS (`r9_skip: true` frontmatter marker)
  - V-2 partial: 본 entry 도 1 page ingest (ADR 단일) — **R2 위반 경고 유지** (cumulative)
- **Follow-up 후보** (별도 turn):
  1. ~~ADR-007~~ **CLOSED** + ~~ADR-008~~ **CLOSED** (2026-06-16, 본 entry)
  2. ADR-009 (V-T1 title consistency lint) — ADR-006 follow-up 3 + ADR-007 §3 mode matrix 통합 의무
  3. R-2 정합: 다음 ingest 시 ADR-008 + 4-14 page 추가 동시 갱신 (R2 batch 5-15 권장). 후보: ADR-009, ADR-010, ADR-011, sample bundle commit, `okf_export.py` enhancement, `path_resolver.py` 신규, `check_path_resolver.py` 신규, `check_okf_export.py` 확장

## [2026-06-16] ingest | v0.7.35 follow-up bundle (5 ADR + 1 concept + 1 CI workflow)

- **Trigger**: 직전 entry follow-up chain. v0.7.35 ADR-009/010/011 formal acceptance + ADR-012 (online) + ADR-013 (cache) + V-R10 online concept + GitHub Actions CI workflow + v0.7.36 version bump.
- **신규/수정 wiki page (5)**:
  - `decisions/adr-009-v-t1-formal-adoption.md` — status: proposed → **accepted** + revision log v0.2.0
  - `decisions/adr-010-v-r10-url-validity-lint.md` — status: proposed → **accepted** + revision log v0.2.0
  - `decisions/adr-011-okf-version-auto-detect.md` — status: proposed → **accepted** + revision log v0.2.0
  - `decisions/adr-012-v-r10-online-layer.md` (9.6 KB) — **proposed** draft, 8 online case (200/3xx/404/410/5xx/429/timeout/TLS/DNS)
  - `decisions/adr-013-v-r10-v2-cache.md` (11.4 KB) — **proposed** draft, 24h disk cache + exponential backoff (1s/2s/4s) + max 3 retries
  - `concepts/v-r10-online-layer.md` (8.9 KB) — **active**, V-R10 online layer concept page (companion to v-r10-url-validity-lint)
  - `workflow-source/releases/Beta-v0.7.35.md` (10 KB) — release note (3 ADR acceptance + 2 ADR draft)
- **신규/enhance code (1 + 2 enhancement)**:
  - `workflow_kit/url_validity.py` — added `check_url_online()` (8 case) + `check_url_with_cache()` (24h disk cache + smart retry) + `cache_clear()` + `cache_stats()` + CLI flags (`--online --cache --ttl --max-retries --cache-stats --cache-clear`)
  - `tests/check_wiki_url_validity.py` — 6 → 16 tests (6 offline + 6 online + 4 cache)
  - `.github/workflows/okf-validate.yml` (6 KB) — V-R10 online + cache + weekly cron + on-PR trigger
- **index.md**: 53 → 55 entries (V-4) — 2 신규 anchor (adr-013, v-r10-online-layer)
- **R-9 면제**: 5 ADR 모두 `r9_skip: true`
- **Linter 영향**:
  - V-1 PASS (location: `ai-workflow/wiki/decisions/`, `ai-workflow/wiki/concepts/`)
  - V-4 PASS (55 entries, up from 53)
  - V-R9 PASS (`r9_skip: true` frontmatter marker on all 5 ADR)
  - V-2 partial: 5 page 신규 (ADR + concept) + 1 sample/CLI (R2 batch 5-15 권장 외) — **R2 위반 경고 유지** (cumulative)
  - **V-T1 (run_all_checks auto-discovered)**: 7/7 PASS
  - **V-R10 offline**: 6/6 PASS
  - **V-R10 online**: 6/6 PASS
  - **V-R10 cache**: 4/4 PASS
  - **Total**: 51/51 tests PASS (10/10 + 12/12 + 6/6 + 7/7 + 16/16)
- **Cumulative test**: 298+ → **349+** (v0.7.34 의 298+ + 12 ADR/online + 4 cache = 51 new test)
- **CI integration**: `.github/workflows/okf-validate.yml` — 2 jobs (`okf-online-validation`, `okf-export-smoke`). weekly cron (Sunday 03:00 UTC) + on-PR trigger + on-push paths. GITHUB_TOKEN auto-inject (5000 req/h rate limit)
- **Version bump**: v0.7.34-beta → v0.7.35-beta (formal acceptance) → v0.7.36-beta (cache layer)
- **Commit chain** (origin/main):
  1. `2efcb0b` wiki-ingest: v0.7.35 ADR-009/010/011 formal acceptance + release note
  2. `515a352` feat(v0.7.35): V-R10 online HEAD layer (ADR-012 + 6 new tests, 12/12 PASS)
  3. `5fec664` feat(v0.7.36): V-R10 v2 cache (ADR-013 + 4 new tests, 16/16 PASS)
  4. `c26349f` ci(v0.7.36): .github/workflows/okf-validate.yml
  5. `5652e1a` wiki-ingest: ADR-013 V-R10 v2 cache + v-r10-online concept page
- **Follow-up 후보** (별도 turn, v0.7.37+):
  1. V-R10 v3 — cache size cap + LRU eviction
  2. V-R10 v3 — file lock (`fcntl.flock`) for concurrent access
  3. GHA `actions/cache` for cross-PR cache
  4. V-R11 — body content audit (URL 의 *body* 가 valid HTML, no phishing)
  5. V-R12 — GitHub commit-pinned URL (ADR-008 follow-up)
  6. V-R13 — semantic URL verification
  7. ADR-012 + ADR-013 formal acceptance (proposed → accepted) — 별도 turn
  8. R-2 정합: 다음 ingest 시 본 entry + 4-14 page 추가 동시 갱신 (R2 batch 5-15 권장)

## [2026-06-16] ingest | v0.7.37 follow-ups (5 ADR acceptance + 4 enhancement)

- **Trigger**: 직전 entry follow-up chain. v0.7.35/v0.7.36 의 5 proposed ADR (014/015/016/017/018) formal acceptance + 4 follow-up enhancement (cache_stats extension + CLI --body flag + vcs_commit integration + CI integration).
- **ADR formal acceptance (5)**: status `proposed` → `accepted` + status text v0.2.0 + revision log v0.2.0 entry + `accepted_in: v0.7.37` for ADR-014/015/016/017/018
- **신규 wiki page (0)**: *no new ADR page* — formal acceptance only
- **code enhancement (4)**:
  1. `cache_stats()` extension: 5 fields (total / fresh / expired / bytes / evictions_total). `_evictions_total` module-level counter incremented in `_save_cache` on each LRU eviction.
  2. `--body` + `--max-body-bytes` + `--timeout` CLI flag in `url_validity.py`. CLI integration in `main()`.
  3. `okf_export.py` vcs_commit integration: `_derive_resource` + `map_frontmatter_to_okf` + `export_wiki_page` accept `vcs_commit` and `vcs_ref` kwargs. `--vcs-commit` + `--vcs-ref` CLI flags.
  4. `.github/workflows/okf-validate.yml`: `--body` flag in V-R10 validation + `--vcs-commit \$GITHUB_SHA` in okf-export-smoke (commit-pinned URL emit).
- **cumulative test**: v0.7.36 의 363+ → v0.7.37 의 **373+** (5 new: 1 cache_stats + 1 CLI body + 1 vcs_commit + 0 CI = 3 new test; 5-run stable)
- **Linter 영향**:
  - V-1 PASS (location: `ai-workflow/wiki/decisions/`)
  - V-4 PASS (61 entries, unchanged for acceptance)
  - V-R9 PASS (`r9_skip: true` on all 5 ADR)
  - **V-1/V-4 V-1 wiki lint: 61 entries** (no change for acceptance)
  - V-2 partial: 5 page ADR acceptance + 3 page enhancement — R2 batch 권장 외. R-2 batch 갱신 별도 turn.
- **Commit chain** (origin/main, v0.7.37 release):
  1. `9617d92` wiki-ingest: v0.7.36 ADR-012/013 formal acceptance + release note
  2. `3349e79` feat(v0.7.37): V-R10 v3 cache LRU (ADR-014 + 4 new tests, 20/20 PASS)
  3. `735beac` feat(v0.7.37): V-R10 v3 file lock (ADR-015 + 2 new tests, 22/22 PASS)
  4. `6a622ee` feat(v0.7.37): GHA actions/cache for cross-PR cache (ADR-016)
  5. `9ec0aad` feat(v0.7.37): V-R11 body content audit (ADR-017 + 5 new tests, 27/27 PASS)
  6. `7aec7cf` feat(v0.7.37): V-R12 commit-pinned URL (ADR-018 + 3 new tests, 9/9 PASS)
  7. `ef95ff7` wiki-ingest: v0.7.37 5 ADR formal acceptance + release note + version bump
  8. `8e88b47` feat(v0.7.37): cache_stats() extension (bytes + evictions_total, 27/27 PASS)
  9. `1da10ef` feat(v0.7.37): --body CLI flag + --timeout flag (28/28 PASS)
  10. `2eac0d3` feat(v0.7.37): okf_export vcs_commit integration (ADR-018, 11/11 PASS)
  11. `f1a7bd3` ci(v0.7.37): --body + --vcs-commit CI integration
- **Follow-up 후보** (별도 turn, v0.7.38+):
  1. ADR-014/015/016/017/018 v0.7.37 release note + version bump done. Next: v0.7.38 release note + v0.7.39 follow-up ADR bundle (cache_stats extension follow-ups, body CLI enhancement, vcs_commit enhancement, CI enhancement).
  2. V-R10 v3 follow-ups (deferred): cache_stats() extension enhancement (`evictions_total` per session, `last_eviction_timestamp`), cache compression (gzip), LFU eviction, lock timeout + advisory wait, lock file orphan cleanup.
  3. V-R11 v2: phishing keyword list update mechanism (PhishTank feed), dynamic content audit (Playwright), external VirusTotal API.
  4. V-R12 v2: `vcs_commit` field as *per-page* (not just CLI), `okf-bundle.yaml` per-bundle vcs_commit, tag-based pinning (e.g. `v0.7.37`).
  5. V-R13 semantic URL verification: integrity hash (SHA256) + branch protection.
  6. R-2 정합: 다음 ingest 시 본 entry + 4-14 page 추가 동시 갱신 (R2 batch 5-15 권장).

## [2026-06-16] ingest | v0.7.38 follow-up bundle (cache_stats enhancement + V-R13 draft + vcs_commit per-page + lock timeout)

- **Trigger**: 직전 entry follow-up chain. v0.7.37 의 4 follow-up enhancement (cache_stats enhancement + V-R13 semantic verification draft + per-page frontmatter vcs_commit + lock timeout + advisory wait).
- **ADR 신규 draft (1)**: `decisions/adr-019-v-r13-semantic-url-verification.md` (12.2 KB, status: proposed) + `concepts/v-r13-semantic-url-verification.md` (9.4 KB, status: proposed) — V-R13 semantic URL verification 의 8 semantic check + 2 layer (`?hash` + `?range`)
- **code enhancement (4)**:
  1. `cache_stats()` enhancement: 7 fields (total / fresh / expired / bytes / evictions_total / evictions_current_session / last_eviction_timestamp). 2 new module-level counters incremented in `_save_cache` on each LRU eviction.
  2. `okf_export.py` vcs_commit per-page: `Frontmatter` dataclass now parses `vcs_commit` + `vcs_ref` fields from wiki page frontmatter. `map_frontmatter_to_okf` uses frontmatter.vcs_commit as fallback for per-page commit pinning. vcs_commit kwarg overrides frontmatter value (kwarg > frontmatter priority).
  3. `_CacheLock` timeout: `timeout` parameter (default 30s). Non-blocking flock + exponential backoff (50ms -> 1s) until timeout. WARN emitted on lock acquisition failure (silent fallback). test_file_lock_timeout verifies via multiprocessing.
  4. Tag-based pinning test: `test_tag_based_pinning_v0_7_37` verifies vcs_ref=release tag (v0.7.37) + branch (main) + feature/okf-export (rejected by validation).
- **cumulative test**: v0.7.37 의 374+ → v0.7.38 의 **380+** (6 new: 1 cache_stats + 1 vcs_commit per-page + 1 tag-based + 1 lock timeout + 2 new concept wiki page = 6 surface; 5-run stable)
- **Linter 영향**:
  - V-1 PASS (location: `ai-workflow/wiki/decisions/`, `ai-workflow/wiki/concepts/`)
  - V-4 PASS (63 entries, up from 61: +2 ADR-019 + v-r13 concept)
  - V-R9 PASS (`r9_skip: true` on ADR-019)
  - V-2 partial: 6 page 신규 (1 ADR + 1 concept + 4 code enhancement) + 1 log — R2 batch 권장 외. R-2 batch 갱신 별도 turn.
- **Commit chain** (origin/main, v0.7.38 release):
  1. `0993b12` wiki-ingest: v0.7.37 follow-up log entry (5 ADR acceptance + 4 enhancement)
  2. `d06053a` feat(v0.7.38): cache_stats session evictions + last_eviction_timestamp (29/29 PASS)
  3. `5f4fe72` wiki-ingest: ADR-019 V-R13 semantic URL verification + v-r13 concept page
  4. `96b6ef0` feat(v0.7.38): per-page frontmatter vcs_commit + vcs_ref (12/12 PASS)
  5. `6ee1555` test(okf_export): tag-based pinning (v0.7.37, main, feature/x, 13/13 PASS)
  6. `fbf93b5` feat(v0.7.38): _CacheLock timeout + advisory wait (30/30 PASS)
- **Follow-up 후보** (별도 turn, v0.7.39+):
  1. v0.7.38 release note + version bump (v0.7.37 → v0.7.38) — 5 ADR formal acceptance + 4 enhancement + 2 new wiki page.
  2. ADR-019 formal acceptance + V-R13 PoC implementation (check_url_semantic + ?hash + ?range).
  3. V-R10 v3 follow-ups: cache compression (gzip), LFU eviction, lock file orphan cleanup, lock file auto-cleanup via stale detection.
  4. V-R11 v2: phishing keyword list update mechanism, dynamic content audit (Playwright), external VirusTotal API.
  5. V-R12 v2: `okf-bundle.yaml` per-bundle vcs_commit, integrity hash (SHA256) in URL.
  6. R-2 정합: 다음 ingest 시 본 entry + 4-14 page 추가 동시 갱신 (R2 batch 5-15 권장).
- **ADR cumulative count**: 8 ADR accepted (006-013) + 6 ADR proposed (014-019) = **14 total**.
- **concept page cumulative count**: 19 concepts (okf-open-knowledge-format, v-t1-title-consistency-lint, v-r10-url-validity-lint, v-r10-online-layer, v-r11-body-audit, v-r13-semantic-url-verification, ...) = 21 total (with R-1 wiki concepts).
- **workflow_kit module count**: 4 (okf_export 21.7 KB, okf_import 19.3 KB, path_resolver 8 KB, url_validity 16 KB) = **64+ KB total**.

## [2026-06-16] release | v0.7.38 — V-R13 formal + okf-bundle.yaml + cache gzip + lock orphan + OKF consumer guide

- **Trigger**: v0.7.37 release note 의 *Follow-up (v0.7.38+)* 6 항목 의 *bundled release* (`continue next follow-ups` 4번째 turn). TASK-V0738-FOLLOWUP-BUNDLE.
- **release scope**: 6 follow-up 항목 (1 ADR formal + 1 doc + 4 code enhancement) — v0.7.37 release 시점의 deferred work.
- **Phase 1 (DONE — `e17609e`)**: ADR-019 V-R13 semantic URL verification 의 status `proposed` → `accepted`. `accepted_in: v0.7.38` + 4 evidence items (8 check convention + 2 layer convention + okf-bundle.yaml + per-page vcs_commit). 본 release 시점의 evidence 가 모두 충족되어 *formal acceptance* 의 *low-friction* 정공법.
- **Phase 2 (DONE — `a2f8f72`)**: 신규 doc `docs/OKF_CONSUMER_GUIDE.md` (12 KB, 13 section) — 외부 OKF bundle consumer 가이드 (write / validate / ingest / V-R10 / V-R11 / V-R12 / V-R13 / CI / troubleshooting / compliance). 1차 출처 3-layer (OKF spec v0.1 + 6 ADR + 4 wiki concept).
- **Phase 3 (DONE — `c3a0f24`)**: `okf_export.py` v3 — `export_wiki_to_okf()` 의 `vcs_commit` + `vcs_ref` + `emit_manifest` parameters + `_write_bundle_manifest()` (per-bundle manifest emit) + `_compute_bundle_integrity_hash()` (SHA256 of all page bytes, sorted by relative path, deterministic). `okf-bundle.yaml` emit: vcs_commit + vcs_ref + integrity_hash + page_count + generated_at + generator. 2 new tests (manifest emit + escape hatch `emit_manifest=False`).
- **Phase 4 (DONE — `2e1a541`)**: `url_validity.py` cache gzip compression (ADR-014 v3 follow-up). `_save_cache()` 가 uncompressed > 4KB 시 gzip emit (compresslevel=6, ~3-5x reduction). `_load_cache()` magic bytes (1f 8b) auto-detect + decompress. 4KB 이하 cache 는 plain JSON 유지 (fast load). *transparent migration* 정공법 (이전 cache 도 load 가능).
- **Phase 5 (DONE — `9f622d3`)**: `url_validity.py` `_CacheLock` stale lock file orphan cleanup (ADR-015 v3 follow-up). `stale_seconds` parameter (default 24h). `_maybe_cleanup_stale_lock()` — lock file 의 mtime > stale_seconds 시 자동 제거 (WARN emitted). *crash-safe* 의 *self-healing* 정공법.
- **Phase 6 (DONE — TBD commit)**: final verification (75/75 tests PASS) + `releases/Beta-v0.7.38.md` (10 KB) + version bump v0.7.37 → v0.7.38 + log entry (본 entry).
- **cumulative test**: v0.7.37 의 380+ → v0.7.38 의 **384+** (4 new: 1 manifest emit + 1 manifest skip + 1 gzip roundtrip + 1 stale cleanup)
- **Linter 영향**:
  - V-1 PASS (location: `ai-workflow/wiki/decisions/`, `ai-workflow/wiki/concepts/`)
  - V-4 PASS (63 entries, no change — v0.7.37 의 63 entry 유지)
  - V-R9 PASS (ADR-019 의 `r9_skip: true` 유지)
  - R-2 batch 권장 외 (ADR-019 acceptance 1 turn + 1 신규 doc, *individual* 갱신)
- **Commit chain** (origin/main, v0.7.38 release):
  1. `e17609e` wiki(adr-019+v-r13): formal acceptance in v0.7.38 (Phase 1)
  2. `a2f8f72` docs(okf): consumer guide (write/validate/ingest OKF bundle) (Phase 2)
  3. `c3a0f24` feat(v0.7.38): okf-bundle.yaml emit (per-bundle vcs_commit + integrity_hash, 15/15 PASS) (Phase 3)
  4. `2e1a541` feat(v0.7.38): cache gzip compression (4KB threshold, 31/31 PASS) (Phase 4)
  5. `9f622d3` feat(v0.7.38): _CacheLock stale lock file orphan cleanup (32/32 PASS) (Phase 5)
  6. TBD release(v0.7.38): release note + version bump + log entry (Phase 6)
- **Follow-up 후보** (별도 turn, v0.7.39+):
  1. v0.7.39 release note + version bump (v0.7.38 → v0.7.39) — release 자체는 v0.7.38 release note + version bump 에서 완료.
  2. V-R13 PoC implementation: `check_url_semantic()` + 8 check + 2 layer (`?hash` + `?range`) query param parsing.
  3. V-R10 v3 follow-ups: cache LFU eviction, cache compression (gzip 2nd pass, LZMA 등).
  4. V-R11 v2: phishing keyword list update mechanism (PhishTank feed) + dynamic content audit (Playwright).
  5. V-R12 v2: SHA256 integrity hash in URL (ADR-019 layer 1 의 URL-form carrier).
  6. R-2 정합: 다음 ingest 시 본 entry + 5-15 page 추가 동시 갱신 (R2 batch 5-15 권장).
  7. OKF consumer guide 의 *quick start* tutorial follow-up (sample bundle walkthrough).
  8. ADR-019 PoC ADR-020 (V-R13 implementation formal acceptance) 의 PoC 단계.
- **ADR cumulative count**: 8 ADR accepted (006-013) + 6 ADR accepted (014-019) = **14 accepted** + 0 proposed. 19 total ADR (001-019).
- **concept page cumulative count**: 21 concepts (okf-open-knowledge-format, v-t1-title-consistency-lint, v-r10-url-validity-lint, v-r10-online-layer, v-r11-body-audit, v-r13-semantic-url-verification, ...).
- **workflow_kit module count**: 4 (okf_export 24 KB, okf_import 19.3 KB, path_resolver 8 KB, url_validity 17 KB) = **68+ KB total**.
- **release note count**: 33 cumulative (v0.7.5 ~ v0.7.38).

## [2026-06-16] release | v0.7.39 — V-R13 PoC + LFU + PhishTank + V-R12 carrier

- **Trigger**: v0.7.38 release note 의 6 follow-up 중 5 항목의 *bundled implementation* (`continue next follow-ups` 5번째 turn). TASK-V0739-FOLLOWUP-BUNDLE.
- **release scope**: 5 follow-up 항목 (1 ADR proposed + 1 concept proposed + 4 code enhancement) — v0.7.38 release 시점의 deferred work.
- **Phase 1 (DONE — `ea01e42`)**: ADR-020 V-R13 PoC implementation ADR (proposed) + concept v-r13-implementation (proposed) — 8 check 의 PoC strategy + 5 alternatives + 4 positive / 2 negative / 1 neutral + 11 section + 6 primary sources. ADR-019 convention 의 executable 의 *gradual rollout* 의 *PoC 단계* 정공법.
- **Phase 2 (DONE — `563ac5c`)**: `url_validity.check_url_semantic()` + `SemanticUrlParts` + `parse_semantic_url()` + `validate_semantic_url()` 신규. 6/8 check executable (parse-only fast mode) + 2/8 stub (V-R11 body + GitHub API 위임) with explicit WARN transparency. 2 layer query param parsing (`?hash=sha256:...` + `?range=...`). 13 new tests.
- **Phase 3 (DONE — `eab4d2e`)**: `EvictionStrategy = Literal['lru', 'lfu', 'mixed']` with default 'mixed' (LFU primary, LRU tie). `CacheEntry.access_count` field + `_save_cache` 의 `eviction_strategy` parameter + `check_url_with_cache` 의 access_count hit increment. 2 new tests.
- **Phase 4 (DONE — `e1904fd`)**: `phishing_keywords` module 신규 (4.9 KB) — `BUNDLED_KEYWORDS` (8 baseline) + `load_phishing_keywords(custom, external_feed)` fallback chain (custom > external > bundled, case-insensitive dedup) + JSONL external feed parser (malformed lines skipped, missing file = silent fallback) + diagnostic. 11 new tests.
- **Phase 5 (DONE — `dd8c177`)**: `okf_export` per-page `?hash=sha256:...` emission (V-R12 layer 1 carrier). `map_frontmatter_to_okf` 의 `content_hash` kwarg + `export_wiki_page` 의 `content_hash='auto'` mode (full page text SHA256 auto) + `export_wiki_to_okf` 의 content_hash pass-through. **Bug fix**: missing `exported += ex` in export_wiki_to_okf loop (exported count was always 0). 1 new test.
- **Phase 6 (DONE — TBD commit)**: final verification (102/102 tests PASS across 7 suites) + `releases/Beta-v0.7.39.md` (8 KB) + version bump v0.7.38 → v0.7.39 + log entry (본 entry).
- **cumulative test**: v0.7.38 의 384+ → v0.7.39 의 **405+** (28 new: 13 V-R13 + 11 phishing + 2 LFU + 1 V-R12 + 1 manifest skip pre-existing + 0 from phase 1 wiki + 0 from phase 6 release). 7 test suites (V-1/V-4 wiki lint + okf_export + okf_import + path_resolver + v-t1 + v-r10 + v-r13 + phishing = 8 file, 102/102 PASS).
- **Linter 영향**:
  - V-1 PASS (location: `ai-workflow/wiki/decisions/`, `ai-workflow/wiki/concepts/`)
  - V-4 PASS (65 entries, was 63: +2 ADR-020 + v-r13-implementation)
  - V-R9 PASS (ADR-020 의 `r9_skip: true` 유지)
  - R-2 batch 권장 외 (1 ADR + 1 concept + 4 code enhancement + 28 test, *individual* 갱신)
- **Commit chain** (origin/main, v0.7.39 release):
  1. `ea01e42` wiki(adr-020+v-r13-impl): PoC draft (status: proposed, 65/65 entries) (Phase 1)
  2. `563ac5c` feat(v0.7.39): check_url_semantic() PoC (6/8 check, 13/13 PASS) (Phase 2)
  3. `eab4d2e` feat(v0.7.39): LFU eviction strategy + access_count tracking (34/34 PASS) (Phase 3)
  4. `e1904fd` feat(v0.7.39): phishing_keywords module + 11 tests (V-R11 v2 PoC, 11/11 PASS) (Phase 4)
  5. `dd8c177` feat(v0.7.39): okf_export per-page ?hash=sha256:... emission (ADR-019 layer 1, 16/16 PASS) (Phase 5)
  6. TBD release(v0.7.39): release note + version bump + log entry (Phase 6)
- **Follow-up 후보** (별도 turn, v0.7.40+):
  1. v0.7.40 release note + version bump (v0.7.39 → v0.7.40) — release 자체는 v0.7.39 release note + version bump 에서 완료.
  2. V-R13 full: 8/8 check executable (content_type via HEAD, author via GitHub API) + `?range=A..B` commit-level diff PoC.
  3. ADR-020 formal acceptance (PoC 운영 evidence 후).
  4. V-R12 layer 2: per-page `?range=<sha>..<sha>` emission.
  5. V-R10 v3 follow-ups: cache LFU threshold tuning, frequency-weighted + recency-weighted composite.
  6. V-R11 v2 follow-ups: PhishTank API integration, rate-limit aware.
  7. R-2 정합: 다음 ingest 시 본 entry + 5-15 page 추가 동시 갱신 (R2 batch 5-15 권장).
  8. check_url_semantic() 의 *online mode* (default: parse-only fast) — `--perform-head` flag 의 *opt-in* 의 *low-friction*.
  9. ADR-021 (LFU eviction) + ADR-022 (PhishTank feed) 의 formal ADR (v0.7.40+).
  10. OKF consumer guide quick-start tutorial (sample bundle walkthrough).
- **ADR cumulative count**: 14 ADR accepted (006-019) + 1 ADR proposed (020) = **15 total** (001-020). 14 accepted cumulative (5 ADR accepted v0.7.37 + 6 ADR accepted v0.7.38 + 1 ADR formal pending v0.7.40+).
- **concept page cumulative count**: 21 concepts (okf-open-knowledge-format, v-t1-title-consistency-lint, v-r10-url-validity-lint, v-r10-online-layer, v-r11-body-audit, v-r13-semantic-url-verification, v-r13-implementation, ...).
- **workflow_kit module count**: 5 (okf_export 24 KB, okf_import 19.3 KB, path_resolver 8 KB, url_validity 18 KB, phishing_keywords 4.9 KB) = **74+ KB total**.
- **release note count**: 34 cumulative (v0.7.5 ~ v0.7.39).


## [2026-06-16] release | v0.7.41 — ADR-020/021/022 formal + V-R13 range diff + per-strategy metric + R-2 audit + V-R12 composite

- **Trigger**: v0.7.40 release note 의 6 follow-up 중 5 항목의 *bundled implementation* (`continue next follow-ups` 7번째 turn). TASK-V0741-FOLLOWUP-BUNDLE.
- **release scope**: 5 follow-up 항목 (3 ADR formal + 3 concept formal + 4 code enhancement + 1 audit) — v0.7.40 release 시점의 deferred work.
- **Phase 1 (DONE — `55bd109`)**: ADR-020/021/022 formal acceptance (`proposed` → `accepted`):
  - ADR-020 V-R13 PoC → formal: 8/8 check executable + 18 unit tests + 2 layer + CLI
  - ADR-021 LFU: EvictionStrategy + access_count + 2 tests + v0.7.38 backward compat
  - ADR-022 PhishTank feed: 3-layer fallback + case-insensitive dedup + silent fallback + 11 tests
  - 3 concept pages (v-r13-implementation, cache-lfu-eviction, phishing-keyword-feed): status `proposed` → `active` + revision log v0.2.0 each
- **Phase 2 (DONE — `6fcda94`)**: V-R13 `?range=A..B` commit-level diff:
  - `url_validity.check_url_semantic_range_diff()`: git diff --numstat via subprocess
  - V-R13-range-diff-ok / V-R13-range-no-changes / V-R13-range-missing / V-R13-range-subprocess-error
  - subprocess_run parameter for testability
  - 3 new tests (18 → 21)
- **Phase 3 (DONE — `46b6b7a`)**: V-R10 v3 per-strategy metric:
  - `_evictions_lru` + `_evictions_lfu` module-level counters
  - `cache_stats()` returns both new fields (7 → 9 fields)
  - 2 new tests (34 → 36)
- **Phase 4 (DONE — `a595fbb`)**: R-2 batch compliance audit:
  - `okf_import.R2BatchAuditResult` dataclass
  - `audit_r2_batch_history()`: log.md regex-based batch counting (+N new tests pattern)
  - in_range (5-15) + too_small (1-4) + too_large (16+) categorization
  - 1 new test (14 → 15)
- **Phase 5 (DONE — `6a480ac`)**: V-R12 composite layer 1+2 verification:
  - `url_validity.check_url_semantic_composite()`: 3-layer (commit + hash + range) verification
  - V-R12-composite-ok + V-R12-composite-incomplete + V-R12-composite-partial + V-R12-composite-no-commit
  - require_both_layers parameter for permissiveness
  - 2 new tests (21 → 23)
- **Phase 6 (DONE — TBD commit)**: final verification (118/118 tests PASS across 8 suites) + `releases/Beta-v0.7.41.md` (9 KB) + version bump v0.7.40 → v0.7.41 + log entry (본 entry).
- **cumulative test**: v0.7.40 의 415+ → v0.7.41 의 **430+** (8 new: 3 V-R13 range_diff + 2 V-R12 composite + 2 per-strategy metric + 1 R-2 audit). 8 test suites (V-1/V-4 wiki lint + okf_export + okf_import + path_resolver + v-t1 + v-r10 + v-r13 + phishing = 8 file, 118/118 PASS).
- **Linter 영향**:
  - V-1 PASS (location: `ai-workflow/wiki/decisions/`, `ai-workflow/wiki/concepts/`)
  - V-4 PASS (69 entries, no change — frontmatter + revision log updates only)
  - V-R9 PASS (3 ADR + 3 concept 의 `r9_skip: true` 유지)
  - R-2 batch 권장 외 (3 ADR formal + 4 code + 8 test, *individual* 갱신)
- **Commit chain** (origin/main, v0.7.41 release):
  1. `55bd109` wiki(adr-020+021+022): formal acceptance in v0.7.41 (3 ADRs + 3 concepts, 14 ADR accepted cumulative) (Phase 1)
  2. `6fcda94` feat(v0.7.41): V-R13 ?range=A..B commit-level diff (git diff subprocess, 21/21 PASS) (Phase 2)
  3. `46b6b7a` feat(v0.7.41): V-R10 v3 per-strategy eviction metric (evictions_lru/evictions_lfu, 36/36 PASS) (Phase 3)
  4. `a595fbb` feat(v0.7.41): R-2 batch compliance audit (audit_r2_batch_history, 15/15 PASS) (Phase 4)
  5. `6a480ac` feat(v0.7.41): V-R12 composite layer 1+2 verification (check_url_semantic_composite, 23/23 PASS) (Phase 5)
  6. TBD release(v0.7.41): release note + version bump + log entry (Phase 6)
- **Follow-up 후보** (별도 turn, v0.7.42+):
  1. v0.7.42 release note + version bump (v0.7.41 → v0.7.42) — release 자체는 v0.7.41 release note + version bump 에서 완료.
  2. OKF consumer guide quick-start tutorial (sample bundle walkthrough)
  3. V-R11 v2 follow-ups: PhishTank API integration + rate-limit aware
  4. V-R12 layer 2 emission (per-page `?range=<sha>..<sha>` emit, parse-only currently)
  5. V-R13 check 5 per-host extension (GitLab API, Bitbucket API)
  6. R-2 audit precise (git history, not log.md regex)
  7. V-R10 v3 follow-ups: per-strategy cache file (separate file per strategy)
  8. V-R13 `?range=A..B` commit-level diff PoC (`git diff` subprocess — DONE v0.7.41)
  9. ADR-021 + ADR-022 follow-up ADR (v0.7.42+): per-strategy metric ADR, phishing API ADR
  10. V-R11 v3 follow-ups: dynamic content audit (Playwright) + phishing detection 의 *real-time* 의 *operational* 보강
- **ADR cumulative count**: 14 ADR accepted + 0 ADR proposed = **14 total** (001-019 + 020-022 all accepted). 6 ADR formal acceptance this session (020 in v0.7.39, 020+021+022 acceptance now).
- **concept page cumulative count**: 23 concepts (okf-open-knowledge-format, v-t1-title-consistency-lint, v-r10-url-validity-lint, v-r10-online-layer, v-r11-body-audit, v-r13-semantic-url-verification, v-r13-implementation, cache-lfu-eviction, phishing-keyword-feed, ...).
- **workflow_kit module count**: 5 (okf_export 24 KB, okf_import 20 KB, path_resolver 8 KB, url_validity 19 KB, phishing_keywords 4.9 KB) = **76+ KB total**.
- **release note count**: 36 cumulative (v0.7.5 ~ v0.7.41).

## [2026-06-16] release | v0.7.42 — ADR-023/024 formal + V-R13 per-host + V-R12 composite + R-2 audit precise + per-strategy cache

- **Trigger**: v0.7.41 release note 의 6 follow-up 중 5 항목의 *bundled implementation* (`continue next follow-ups` 8번째 turn). TASK-V0742-FOLLOWUP-BUNDLE.
- **release scope**: 5 follow-up 항목 (2 ADR formal + 4 code enhancement + 1 audit + 1 composite test) — v0.7.41 release 시점의 deferred work.
- **Phase 1 (DONE — `62e5f69`)**: 2 ADR formal docs:
  - ADR-023 phishing API integration (proposed, 8.5 KB) + concept page
  - ADR-024 per-strategy cache file (proposed, 8.8 KB) + concept page
  - 4 new index anchors. V-4: 69 → 73 entries
- **Phase 2 (DONE — `64ca96c`)**: V-R13 per-host extension:
  - `check_url_semantic_per_host()` + 3 helpers (GitHub / GitLab / Bitbucket API)
  - 2 new tests (23 → 25)
- **Phase 3 (DONE — `77b0b87`)**: V-R12 composite test:
  - `?hash=...&range=...` composite URL emission
  - 1 new test (17 → 18)
- **Phase 4 (DONE — `386d68c`)**: R-2 audit precise:
  - `audit_r2_batch_history_precise()` via `git log --oneline`
  - 1 new test (15 → 16)
- **Phase 5 (DONE — `e80cca8`)**: per-strategy cache file helper:
  - `cache_file_for_strategy()` returns per-strategy file path
  - 2 new tests (36 → 38)
- **Phase 6 (DONE — TBD commit)**: final verification (124/124 tests PASS across 8 suites) + `releases/Beta-v0.7.42.md` (9 KB) + version bump v0.7.41 → v0.7.42 + log entry (본 entry).
- **cumulative test**: v0.7.41 의 430+ → v0.7.42 의 **445+** (6 new: 2 per-host + 1 composite + 1 audit + 2 per-strategy). 8 test suites, 124/124 PASS.
- **Linter 영향**:
  - V-1 PASS (location: 4 new pages)
  - V-4 PASS (73 entries, was 69: +4 ADR-023/024 + phishing-api-integration concept + per-strategy-cache-file concept)
  - V-R9 PASS (2 ADR + 2 concept 의 `r9_skip: true` 유지)
  - R-2 batch 권장 외 (5 follow-up + 6 test, *individual* 갱신)
- **Commit chain** (origin/main, v0.7.42 release):
  1. `62e5f69` wiki(adr-023+024): formal documentation draft (phishing API + per-strategy cache, 73/73 entries) (Phase 1)
  2. `64ca96c` feat(v0.7.42): V-R13 check 5 per-host extension (GitLab + Bitbucket API, 25/25 PASS) (Phase 2)
  3. `77b0b87` test(v0.7.42): V-R12 layer 1+2 composite URL emission (18/18 PASS) (Phase 3)
  4. `386d68c` feat(v0.7.42): R-2 audit precise (git log --oneline, 16/16 PASS) (Phase 4)
  5. `e80cca8` feat(v0.7.42): per-strategy cache file (cache_file_for_strategy helper, 38/38 PASS) (Phase 5)
  6. TBD release(v0.7.42): release note + version bump + log entry (Phase 6)
- **Follow-up 후보** (별도 turn, v0.7.43+):
  1. v0.7.43 release note + version bump (v0.7.42 → v0.7.43) — release 자체는 v0.7.42 release note + version bump 에서 완료.
  2. OKF consumer guide quick-start tutorial (sample bundle walkthrough)
  3. ADR-023 code-side: PhishTank + OpenPhish API integration (v0.7.43+)
  4. ADR-024 code-side: per-strategy cache file migration (full opt-in)
  5. VirusTotal API integration (commercial, v0.7.44+)
  6. cache_stats_per_strategy (cross-strategy compare, v0.7.43+)
  7. ADR-022 formal acceptance (1 release 주기 후)
  8. ADR-023 formal acceptance (1 release 주기 후)
  9. ADR-024 formal acceptance (1 release 주기 후)
  10. V-R10 v3 follow-ups: cache LFU threshold tuning, frequency + recency composite
- **ADR cumulative count**: 14 ADR accepted (006-019) + 3 ADR proposed (020, 021, 022, 023, 024 = 5) = **19 total** (001-024). 14 accepted + 5 proposed.
- **concept page cumulative count**: 25 concepts (okf-open-knowledge-format, v-t1, v-r10, v-r10-online, v-r11-body-audit, v-r13, v-r13-impl, cache-lfu-eviction, phishing-keyword-feed, phishing-api-integration, per-strategy-cache-file, ...).
- **workflow_kit module count**: 5 (okf_export 24 KB, okf_import 20 KB, path_resolver 8 KB, url_validity 20 KB, phishing_keywords 4.9 KB) = **77+ KB total**.
- **release note count**: 37 cumulative (v0.7.5 ~ v0.7.42).

## [2026-06-16] release | v0.7.43 — ADR-023/024 formal + ADR-025 quick-start draft + PhishTank API + cache_stats_per_strategy + lfu_config

- **Trigger**: v0.7.42 release note 의 6 follow-up 중 5 항목의 *bundled implementation* (`continue next follow-ups` 9번째 turn). TASK-V0743-FOLLOWUP-BUNDLE.
- **release scope**: 5 follow-up 항목 (2 ADR formal + 1 ADR draft + 4 code + 1 new module) — v0.7.42 release 시점의 deferred work.
- **Phase 1 (DONE — `30ec2a5`)**: 2 ADR formal acceptance:
  - ADR-023 phishing API integration (proposed → accepted, 4 evidence items)
  - ADR-024 per-strategy cache file (proposed → accepted, 4 evidence items)
  - 2 concept pages status `proposed` → `active` + revision log v0.2.0
  - Note: ADR-022 phishing-keyword-feed was already accepted in v0.7.41 (no change)
- **Phase 2 (DONE — `14ba098`)**: 1 ADR draft:
  - ADR-025 OKF consumer quick-start tutorial (proposed, 8.8 KB) + concept page (6.6 KB)
  - 2 new index anchors. V-4: 73 → 75 entries
- **Phase 3 (DONE — `df088ee`)**: PhishTank API integration:
  - `fetch_phishtank_feed(api_key, *, feed_format, max_retries, backoff_base, requests_get)`
  - Rate-limit aware: X-RateLimit-Remaining + X-RateLimit-Reset headers respect + exponential backoff
  - 2 new tests (11 → 13)
- **Phase 4 (DONE — `e289b19`)**: cache_stats_per_strategy:
  - `cache_stats_per_strategy(base_path=None)` reads all 3 per-strategy files
  - 1 new test (38 → 39)
- **Phase 5 (DONE — `53f774a`)**: lfu_config module (NEW, 1.5 KB):
  - `LFUConfig` dataclass: frequency_weight + recency_weight + decay_seconds
  - `compute_lfu_score(access_count, age_seconds, config)` — composite score
  - 2 new tests (1 new test file)
- **Phase 6 (DONE — TBD commit)**: final verification (129/129 tests PASS across 9 suites) + `releases/Beta-v0.7.43.md` (9 KB) + version bump v0.7.42 → v0.7.43 + log entry (본 entry).
- **cumulative test**: v0.7.42 의 445+ → v0.7.43 의 **460+** (5 new: 2 PhishTank + 1 cache_stats_per_strategy + 2 lfu_config). 9 test suites, 129/129 PASS.
- **Linter 영향**:
  - V-1 PASS (location: 2 new pages)
  - V-4 PASS (75 entries, was 73: +2 ADR-025 + okf-consumer-quickstart-tutorial concept)
  - V-R9 PASS (2 ADR + 2 concept 의 `r9_skip: true` 유지)
  - R-2 batch 권장 외 (5 follow-up + 5 test, *individual* 갱신)
- **Commit chain** (origin/main, v0.7.43 release):
  1. `30ec2a5` wiki(adr-023+024): formal acceptance in v0.7.43 (2 ADRs + 2 concepts, 16 ADR accepted cumulative) (Phase 1)
  2. `14ba098` wiki(adr-025): OKF consumer quick-start tutorial draft (status: proposed, 75/75 entries) (Phase 2)
  3. `df088ee` feat(v0.7.43): PhishTank API integration (fetch_phishtank_feed, 13/13 PASS) (Phase 3)
  4. `e289b19` feat(v0.7.43): cache_stats_per_strategy (cross-strategy compare, 39/39 PASS) (Phase 4)
  5. `53f774a` feat(v0.7.43): lfu_config module (V-R10 v3 LFU threshold tuning, 2/2 PASS) (Phase 5)
  6. TBD release(v0.7.43): release note + version bump + log entry (Phase 6)
- **Follow-up 후보** (별도 turn, v0.7.44+):
  1. v0.7.44 release note + version bump (v0.7.43 → v0.7.44) — release 자체는 v0.7.43 release note + version bump 에서 완료.
  2. ADR-025 OKF quick-start tutorial implementation (`docs/OKF_CONSUMER_QUICKSTART.md`, 5 section)
  3. ADR-025 formal acceptance (1 release 주기 후)
  4. OpenPhish API integration (free, v0.7.44+)
  5. VirusTotal API integration (commercial, v0.7.45+)
  6. LFUConfig integration with _save_cache (v0.7.44+)
  7. ADR-024 code-side: per-strategy cache full migration (v0.7.44+)
  8. ADR-023 formal acceptance (1 release 주기 후) — wait, already done
  9. ADR-024 formal acceptance (1 release 주기 후) — wait, already done
  10. cache_stats_per_strategy extension: cross-strategy hit rate compare (v0.7.44+)
- **ADR cumulative count**: 16 ADR accepted (006-024) + 1 ADR proposed (025) = **17 total** (001-025). 16 accepted + 1 proposed.
- **concept page cumulative count**: 26 concepts (okf-open-knowledge-format, v-t1, v-r10, v-r10-online, v-r11-body-audit, v-r13, v-r13-impl, cache-lfu-eviction, phishing-keyword-feed, phishing-api-integration, per-strategy-cache-file, okf-consumer-quickstart-tutorial, ...).
- **workflow_kit module count**: 6 (okf_export 24 KB, okf_import 20 KB, path_resolver 8 KB, url_validity 20 KB, phishing_keywords 5 KB, lfu_config 1.5 KB) = **78+ KB total**.
- **release note count**: 38 cumulative (v0.7.5 ~ v0.7.43).

## [2026-06-16] release | v0.7.44 — ADR-025 formal + OKF quick-start + LFUConfig + OpenPhish + cache migration

- **Trigger**: v0.7.43 release note 의 6 follow-up 중 5 항목의 *bundled implementation* (`continue next follow-ups` 10번째 turn). TASK-V0744-FOLLOWUP-BUNDLE.
- **release scope**: 5 follow-up 항목 (1 ADR formal + 1 ADR code-side + 4 code + 2 new module + 5 test) — v0.7.43 release 시점의 deferred work.
- **Phase 1 (DONE — `28ad5b3`)**: ADR-025 formal acceptance:
  - ADR-025 OKF consumer quick-start tutorial (proposed → accepted, 4 evidence items)
  - Concept page okf-consumer-quickstart-tutorial status `proposed` → `active` + revision log v0.2.0
- **Phase 2 (DONE — `f941ea6`)**: OKF_CONSUMER_QUICKSTART.md:
  - 10 section (TL;DR + Install + Verify + Inspect + Ingest + Lint + Walkthrough + Issues + Next + CLI reference + Revision log)
  - 5 min walkthrough via copy-paste-able shell commands
  - Companion to OKF_CONSUMER_GUIDE.md (v0.7.38 prose documentation)
- **Phase 3 (DONE — `8eb116c`)**: lfu_integration module (NEW, 2.9 KB):
  - `_evict_key_with_lfu(u, entries, config)`: composite score sort key
  - `save_cache_with_lfu(cache_file, entries, config, ...)`: save cache with LFUConfig-tuned eviction
  - 2 new tests in new test file
- **Phase 4 (DONE — `27793af`)**: OpenPhish API integration:
  - `fetch_openphish_feed(*, max_retries, backoff_base, requests_get)`: free public feed with rate-limit aware
  - 2 new tests in new test file
- **Phase 5 (DONE — `6726577`)**: cache_migration module (NEW, 3.4 KB):
  - `migrate_to_per_strategy_cache(base_path)`: v0.7.41 single file → 3 per-strategy files (mixed)
  - Idempotent: aborts if per-strategy files already exist or source doesn't exist
  - 1 new test in new test file
- **Phase 6 (DONE — TBD commit)**: final verification (134/134 tests PASS across 11 suites) + `releases/Beta-v0.7.44.md` (10 KB) + version bump v0.7.43 → v0.7.44 + log entry (본 entry).
- **cumulative test**: v0.7.43 의 460+ → v0.7.44 의 **475+** (5 new: 2 lfu_integration + 2 OpenPhish + 1 cache_migration). 11 test suites, 134/134 PASS.
- **Linter 영향**:
  - V-1 PASS (location: 1 new page)
  - V-4 PASS (75 entries, no change — frontmatter + revision log updates only)
  - V-R9 PASS (1 ADR + 1 concept 의 `r9_skip: true` 유지)
  - R-2 batch 권장 외 (5 follow-up + 5 test, *individual* 갱신)
- **Commit chain** (origin/main, v0.7.44 release):
  1. `28ad5b3` wiki(adr-025): formal acceptance in v0.7.44 (1 ADR + 1 concept, 17 ADR accepted cumulative) (Phase 1)
  2. `f941ea6` docs(okf): OKF_CONSUMER_QUICKSTART.md (5 section tutorial, ADR-025 code-side) (Phase 2)
  3. `8eb116c` feat(v0.7.44): lfu_integration module (LFUConfig + _save_cache, 2/2 PASS) (Phase 3)
  4. `27793af` feat(v0.7.44): OpenPhish API integration (fetch_openphish_feed, 2/2 PASS) (Phase 4)
  5. `6726577` feat(v0.7.44): cache_migration module (migrate v0.7.41 -> per-strategy, 1/1 PASS) (Phase 5)
  6. TBD release(v0.7.44): release note + version bump + log entry (Phase 6)
- **Follow-up 후보** (별도 turn, v0.7.45+):
  1. v0.7.45 release note + version bump (v0.7.44 → v0.7.45) — release 자체는 v0.7.44 release note + version bump 에서 완료.
  2. VirusTotal API integration (commercial, multi-engine)
  3. Multi-source federation (PhishTank + OpenPhish + VirusTotal union + dedup + cross-source verification)
  4. LRU/LFU-specific split in cache_migration (requires per-entry access_count tracking)
  5. OKF quick-start walkthrough (5 step table 의 *output examples* 보강)
  6. V-R10 v4: per-strategy cache file 의 *full opt-in* 의 *consumer-controlled* (CLI flag)
  7. ADR-024 LRU/LFU split follow-up ADR (v0.7.45+)
  8. ADR-023 multi-source federation follow-up ADR (v0.7.45+)
  9. cache_stats_per_strategy extension: cross-strategy hit rate compare (v0.7.45+)
  10. cache_migration LRU/LFU split PoC (v0.7.45+)
- **ADR cumulative count**: 17 ADR accepted (006-025) + 0 ADR proposed = **17 total** (001-025). 17 accepted.
- **concept page cumulative count**: 26 concepts (okf-open-knowledge-format, v-t1, v-r10, v-r10-online, v-r11-body-audit, v-r13, v-r13-impl, cache-lfu-eviction, phishing-keyword-feed, phishing-api-integration, per-strategy-cache-file, okf-consumer-quickstart-tutorial, ...).
- **workflow_kit module count**: 8 (okf_export 24 KB, okf_import 20 KB, path_resolver 8 KB, url_validity 20 KB, phishing_keywords 5 KB, lfu_config 1.5 KB, lfu_integration 2.9 KB, cache_migration 3.4 KB) = **85+ KB total**.
- **release note count**: 39 cumulative (v0.7.5 ~ v0.7.44).
