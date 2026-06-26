# Beta v0.11.0 — Two-step CoT ingest (R-A follow-up cycle 3) (2026-06-26)

> **SemVer minor** (v0.10.3 → v0.11.0) — v0.9.2 spec §4.3 / §10 R-A follow-up table 의 *cycle 3* 정공법 + v0.10.3 release note 의 "다음" §1 follow-up. **`PURPOSE.md` 의 2-step Chain-of-Thought ingest** (raw 추출 → structured 4-element emit + cross-reference validate). *directional intent* 와 *structural rules* 의 일관성 강화를 위한 정공법. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 신규 helper + 1 CLI subcommand + 3 output schema extension + 1 spec layer extension + 6 acceptance test)

### 1. Two-step CoT ingest (R-A follow-up cycle 3)

**v0.9.2 spec §4.3 / §10 R-A follow-up table 의 cycle 3** — Karpathy `llm-wiki.md` + llm_wiki (nashsu) 의 *Purpose.md — The Wiki's Soul* concept 의 *LLM context read pattern* 을 2-step Chain-of-Thought 로 정형화.

**기존 LLM context read pattern**:
- **v0.9.4 part 1** — `state.json.purpose_digest` 1-line 자동 생성
- **v0.9.5 part 2** — skill context load (3 skill 통합, PURPOSE.md 본문 ≤800 char + scope check)
- **v0.9.6 part 3** — wiki-event-sync R-A trigger (30일 분포 + LLM suggest, advisory)
- **v0.11.0 cycle 3 (본 release)** — two-step CoT ingest (raw → structured 4-element + cross-reference validate)

**`workflow_kit.common.purpose_ingest` helper module 신규** (≈ 350 line):
- `find_purpose_path(workspace_root: Path) -> Path | None` — `purpose_context.find_purpose_path` 와 동일 candidate locations (3 종) 재사용
- `extract_raw_purpose(purpose_path: Path | None) -> RawPurposeExtract` — step 1 raw 추출. PURPOSE.md 부재 / corrupted frontmatter 모두 graceful skip
- `build_structured_purpose(raw: RawPurposeExtract) -> StructuredPurpose` — step 2 structured 4-element emit. `StructuredPurposeValidationError` raise (Goals empty 시 acceptance criterion #3 정합)
- `emit_cot_trace(raw, structured) -> CoTTrace` — CoT 2-step trace: step1 ≤800 char excerpt + step2 4-element summary
- `cross_reference_validate(structured, workspace_root) -> CrossRefValidationResult` — PURPOSE.md 본문 의 `[[mention]]` ↔ `ai-workflow/wiki/concepts/*.md` stem 매칭 (matched / missing_refs / warnings)
- `run_two_step_cot_ingest(purpose_path, workspace_root, auto_find_purpose) -> TwoStepCoTIngestResult` — unified entry. 4 stage 모두 호출 + 모든 stage 의 graceful skip 보장
- 5 dataclass: `RawPurposeExtract` / `StructuredPurpose` / `StructuredPurposeValidationError` / `CoTTrace` / `CrossRefValidationResult` / `TwoStepCoTIngestResult`

**CoT 2-step trace (LLM 의 *directional intent* vs *structural rules* 일관성)**:
- **step 1 (raw)**: PURPOSE.md 본문 ≤800 char excerpt. 1차 정형화 없이 raw text 그대로 (LLM ingest 가능 형태)
- **step 2 (structured)**: Goals G1 first + Questions count + Scope included count 의 4-element summary

**Cross-reference validate** (wiki 운영 R-1~R9 cycle 의 1차 출처 concept 검증):
- PURPOSE.md 본문 의 `[[mention]]` wikilink 추출
- `ai-workflow/wiki/concepts/` 디렉토리 의 `*.md` 파일 stem 집합과 매칭
- mismatch 발견 시 `missing_refs` list + advisory warning (blocking ❌)
- wiki concepts 디렉토리 부재 시 `warnings` advisory + no-op

### 2. CLI dispatcher subcommand `ingest-purpose` (v0.11.0+ 신규)

`workflow_kit/workflow_kit_cli.py` 의 dispatcher registry 에 subcommand 33 신규:

- `--purpose-path=PATH` (optional, default: auto-detect)
- `--workspace-root=PATH` (optional, default: cwd)
- `--cross-ref-check` (boolean, default: true)
- `--apply` (default dry-run) — destructive subcommand 정공법 memory #5 정합
- `--json` (optional) — JSON output (CoT trace + cross_ref + digest_update)

**destructive subcommand 정공법 (memory #5)**:
- `apply=False` (default) — CoT ingest 결과 + cross-reference advisory 만 emit, file I/O ❌
- `--apply` 명시 시 — `state.json.purpose_digest` 의 stale 항목 (PURPOSE.md 변경 후 미반영) 만 advisory 갱신 (실제 atomic_write 는 workflow_kit 라이브러리 caller 책임)
- **3-step crash safety**: 1) raw read + hash verify → 2) structured build → 3) advisory emit (apply=True 시 digest update 만, atomic_write skip)

**Dispatcher registry 누적**: 33 subcommand (v0.10.3 cascade-delete 32 → v0.11.0 ingest-purpose 33)

### 3. 3 output schema extension (v0.11.0+ 신규)

| Schema | Field | Type |
|---|---|---|
| `SessionStartOutput` | `purpose_cot_trace` | `SessionStartPurposeCoTTrace \| None` |
| `BacklogUpdateOutput` | `purpose_cot_trace` | `BacklogUpdatePurposeCoTTrace \| None` |
| `DocSyncOutput` | `purpose_cot_trace` | dict (`step1_raw_excerpt` / `step1_truncated` / `step1_char_count` / `step2_structured_summary` / `cross_ref_matched` / `cross_ref_missing` / `cross_ref_warnings` / `overall_warnings`) |

**3 skill context load 통합**:
- `workflow_kit/skills/session-start/scripts/run_session_start.py` — `build_purpose_context` 호출 직후 `run_two_step_cot_ingest` 추가 호출
- `workflow_kit/skills/backlog-update/scripts/run_backlog_update.py` — 동일 패턴
- `workflow_kit/skills/doc-sync/scripts/run_doc_sync.py` — 동일 패턴
- `warnings` 누적: `cot_result.overall_warnings` extend → output `warnings` field

### 4. Spec layer 갱신 (1 spec)

| Spec | Section | 변경 |
|---|---|---|
| `core/llm_wiki_concept_purpose_spec.md` | §4.3 cycle 3 | v0.11.0 cycle 3 entry 추가 (2-step CoT ingest 정공법 + 5 함수 + 5 dataclass + 3 output schema + destructive 정공법 + graceful skip) |
| `core/llm_wiki_concept_purpose_spec.md` | §5 acceptance criterion | cycle 3 check item (`[ ]`) 추가 |
| `core/llm_wiki_concept_purpose_spec.md` | §6 cross-reference | 4 신규 file (purpose_ingest.py + 3 schema extension + cmd_ingest_purpose + test file) cross-ref |
| `core/llm_wiki_concept_purpose_spec.md` | §10 R-A follow-up cycle table | 4 release 분할 정합 (v0.9.4 part 1 ✅ / v0.9.5 part 2 ✅ / v0.9.6 part 3 ✅ / v0.11.0 cycle 3 follow-up) |
| `core/llm_wiki_concept_purpose_spec.md` | 헤더 | 최종 수정일 `2026-06-26` |

## 운영 누적 (v0.10.3 → v0.11.0)

| | v0.10.3 | **v0.11.0** |
|---|---|---|
| **SemVer bump** | minor | **minor** |
| **`workflow_kit.common.purpose_ingest`** | ❌ | **✅ (5 함수 + 5 dataclass + unified entry, ≈ 350 line)** |
| **`cmd_ingest_purpose` subcommand** | ❌ | **✅ (subcommand 33, destructive 정공법 정합)** |
| **`SessionStartOutput.purpose_cot_trace`** | ❌ | **✅ (CoT 2-step trace)** |
| **`BacklogUpdateOutput.purpose_cot_trace`** | ❌ | **✅ (CoT 2-step trace)** |
| **`DocSyncOutput.purpose_cot_trace`** | ❌ | **✅ (CoT 2-step trace, dict)** |
| **3 skill context load 통합** | ❌ | **✅ (session-start + backlog-update + doc-sync)** |
| **cumulative acceptance** | 63/63 | **69/69** (v0.11.0 6 신규) |
| **spec §9 acceptance** | 12/12 | **12/12** (변동 ❌) |
| **breaking change** | none | **none** (default dry-run, v0.10.3 호환) |

## Test 결과

- 신규 (6 PASS, v0.11.0):
  - `test_extract_raw_purpose_v0_11_0` — extract_raw_purpose SSOT (frontmatter + §1~§4 + 부재 + §1 empty + unicode 한국어 5 case)
  - `test_build_structured_purpose_v0_11_0` — build_structured_purpose 4-element parse (Goals 3+ / Questions 3 / Scope 포함·제외 / Thesis) + StructuredPurposeValidationError raise (empty goals + raw missing 2 case)
  - `test_emit_cot_trace_v0_11_0` — CoT trace 의 2-step 본문 ≤800 char (step1) + step2 summary 4-element + structured unavailable 3 case
  - `test_cross_reference_validate_v0_11_0` — `[[mention]]` ↔ wiki concepts filename 매칭 (matched 2/2 + matched 1/2 missing + 부재 3 case)
  - `test_run_two_step_cot_ingest_graceful_v0_11_0` — unified entry 의 graceful skip (no PURPOSE.md + §1 empty + 정상 + corrupted 4 case)
  - `test_ingest_purpose_cli_registered_v0_11_0` — CLI subcommand 등록 (subcommand 33, total 33) + dry-run subprocess verify (state.json 보존) + output field completeness
- v0.10.3 회귀: **7/7 PASS** ✅
- v0.10.2 회귀: **9/9 PASS** ✅
- v0.10.1 회귀: **6/6 PASS** ✅
- v0.10.0 회귀: **6/6 PASS** ✅
- v0.9.6 회귀: **6/6 PASS** ✅ (R-A trigger)
- v0.9.5 회귀: **6/6 PASS** ✅ (skill context load)
- v0.9.4 회귀: **3/3 PASS** ✅ (purpose_digest)
- v0.9.2 회귀: **8/8 PASS** ✅ (purpose concept)
- v0.9.3 회귀: **4/4 PASS** ✅ (deprecation 2nd)
- v0.9.1 회귀: **4/4 PASS** ✅ (deprecation contract)
- v0.9.0 회귀: **6/6 PASS** ✅
- 누적 acceptance: **69/69 PASS**
- 누적 smoke: **162/162 + 69 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6 + v0.9.6 6 + v0.10.0 6 + v0.10.1 6 + v0.10.2 9 + v0.10.3 7 + v0.11.0 6)

## 변경 파일 (8 변경 + 4 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/workflow_kit/workflow_kit_cli.py` | `cmd_ingest_purpose` 등록 (subcommand 33) + docstring + 5 flag parse |
| M | `workflow-source/workflow_kit/common/schemas/session.py` | `SessionStartPurposeCoTTrace` nested model + `SessionStartOutput.purpose_cot_trace` field 추가 |
| M | `workflow-source/workflow_kit/common/schemas/backlog.py` | `BacklogUpdatePurposeCoTTrace` nested model + `BacklogUpdateOutput.purpose_cot_trace` field 추가 |
| M | `workflow-source/skills/session-start/scripts/run_session_start.py` | `run_two_step_cot_ingest` 호출 + `purpose_cot_trace` output binding |
| M | `workflow-source/skills/backlog-update/scripts/run_backlog_update.py` | 동일 패턴 |
| M | `workflow-source/skills/doc-sync/scripts/run_doc_sync.py` | 동일 패턴 (dict 기반) |
| M | `workflow-source/core/llm_wiki_concept_purpose_spec.md` | §4.3 cycle 3 + §5 + §6 + §10 cycle table + 최종 수정일 갱신 |
| M | `workflow-source/pyproject.toml` | version 0.10.3 → 0.11.0 |
| M | `workflow-source/workflow_kit/__init__.py` | `_read_pyproject_version` loud fallback literal `"v0.10.3-beta"` → `"v0.11.0-beta"` |
| A | `workflow-source/workflow_kit/common/purpose_ingest.py` | helper module 신규 (5 함수 + 5 dataclass, ≈ 350 line) |
| A | `workflow-source/tests/check_two_step_cot_ingest_v0_11_0.py` | 신규 (6 acceptance test, ≈ 450 line) |
| A | `workflow-source/releases/Beta-v0.11.0.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.11.0/backlog/2026-06-26.md` | v0.11.0 plan |

## 다음 (v0.11.1+ / v1.0.0)

1. **v0.11.1 follow-up** — graph insights (R-A cycle 4, surprising + gaps) 정형화. PURPOSE.md 의 *Goals ↔ 실제 deliverable* 매핑 분석 + 의외의 발견 + 갭 식별.
2. **v0.11.2 follow-up** — release pipeline `--apply default=False` 전환 (destructive 정공법 정착). breaking change 회피로 minor release 에서 점진적 전환.
3. **v0.11.3 follow-up** — mypy strict cumulative 격상 (19 → 20-21 file). 1 release = 1-2 file 단계적 격상.
4. **v1.0.0 milestone** — full mypy strict 도달 (semver major 정렬, 100+ release 후 예상). spec §9 acceptance 12/12 도달 유지.

## Bundle 비율 (1차 출처 Karpathy + llm_wiki)

| concept | v0.9.2 | v0.9.5 part 2 | v0.9.6 part 3 | **v0.11.0 cycle 3** |
|---|---|---|---|---|
| 4-element 구조 | 100% | 100% | 100% | **100%** |
| LLM context read pattern | 80% | 80% | 80% | **90%** (CoT 2-step 추가) |
| Suggest-update trigger (R-A) | 0% | 0% | 60% | **60%** |
| Two-step CoT ingest (raw → structured) | 0% | 0% | 0% | **100%** (신규) |
| Cross-reference validate (wiki ↔ `[[mention]]`) | 0% | 0% | 0% | **100%** (신규) |
| **전체** | ~75% | ~75% | ~80% | **~92%** |
