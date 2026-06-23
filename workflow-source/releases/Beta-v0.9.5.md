# Beta v0.9.5 — R-A follow-up part 2 (skill context load integration) (2026-06-23)

> Phase 12 의 *R-A follow-up* 두 번째 release. v0.9.4 (part 1) 의 *state.json.purpose_digest 1-line 자동 생성* 후속 — session-start / backlog-update / doc-sync 3종 skill 의 *context load* 시 `state.json.purpose_digest` 1-line + PURPOSE.md 본문 (≤200 token) 자동 read + backlog-update 의 *in-scope check* 시 Research Scope 와 비교하여 *scope creep 경고*. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 신규 helper + 3 schema 확장 + 3 script 통합 + 5 acceptance test + 5 spec layer 확장)

### 1. Skill context load integration (R-A follow-up part 2)

**v0.9.4 chapter 8 part 1 의 후속** — `state.json.purpose_digest` 가 1-line 으로 만들어졌으므로, 이걸 *실제 LLM context* 에 자동 주입하는 정공법:

- **`workflow_kit.common.purpose_context.build_purpose_context(workspace_root, state_path)` helper 신규** (5개 함수):
  - `find_purpose_path(workspace_root)` — 3 candidate path resolution (v0.9.4 builder 와 동일)
  - `_read_state_digest_and_rev(state_path)` — `state.json.purpose_digest` + `purpose_digest_rev` 동시 read, 부재/파싱실패/빈 string 모두 graceful skip
  - `read_purpose_body_excerpt(purpose_path, max_chars=800)` — PURPOSE.md 본문 (frontmatter 제외) ≤800 char (=≈200 token, 한국어 2-3 chars/token + 영어 4 chars/token 의 mixed content safe upper bound)
  - `extract_research_scope(purpose_path)` — §3 Research Scope 의 *포함 영역* / *제외 영역* parse
  - `check_scope_creep(task_brief, affected_documents, scope)` — 제외 영역 substring + 첫 2 token (≥4 char) 매칭 → warning emit

- **3 output schema 확장** (nested Pydantic model):
  - `SessionStartOutput.purpose_context: SessionStartPurposeContext | None` (9 field)
  - `BacklogUpdateOutput.purpose_context: BacklogUpdatePurposeContext | None` + `scope_creep_warnings: list[str]`
  - `DocSyncOutput.purpose_context: DocSyncPurposeContext | None` (9 field)
  - 모든 `*PurposeContext` 는 동일 9 field: `purpose_digest` / `purpose_digest_rev` / `purpose_path` / `body_excerpt` / `body_excerpt_truncated` / `body_excerpt_char_count` / `scope_included` / `scope_excluded` / `scope_warnings`

- **3 skill script 통합** (`workflow-source/skills/{session-start,backlog-update,doc-sync}/scripts/run_*.py`):
  - session-start: `build_purpose_context` 호출 → `output_model.purpose_context` 채움
  - backlog-update: `build_purpose_context` + `check_scope_creep` 호출 → `purpose_context` + `scope_creep_warnings` 채움 (hard scope check)
  - doc-sync: `build_purpose_context` 호출 → `output["purpose_context"]` 채움 (advisory only, hard scope check ❌)

- **Graceful skip 정책**: 3종 skill 모두 PURPOSE.md / state.json 어느 쪽이 부재해도 skill 실행 실패 ❌. `purpose_context` field 가 partial fill 또는 null + `scope_warnings: ["PURPOSE.md 부재 — scope check skipped"]` 1줄 advisory.

- **Scope creep check 정공법** (backlog-update 한정):
  - `scope["excluded"]` 의 각 area 에 대해 (1) 전체 substring 매칭 → hard warning, (2) 첫 2 token (≥4 char) 매칭 → keyword warning
  - 포함 영역 매칭은 soft heuristic — 본 hard warning 은 *제외* 만 다룬다
  - `excluded` 비어있으면 early return (no-op)
  - markdown marker (`**`, `*`, `` ` ``) 제거 + lowercase + whitespace 압축 후 매칭

## Spec layer 확장 (5 file)

| Spec | Section | 변경 |
|---|---|---|
| `llm_wiki_concept_purpose_spec.md` | §4.3 part 2 | v0.9.5 의 helper module / schema field / scope check logic 명시 (7 detail) |
| `llm_wiki_concept_purpose_spec.md` | §5 follow-up checklist | session-start / backlog-update 의 2 acceptance ✅ v0.9.5 part 2 |
| `llm_wiki_concept_purpose_spec.md` | §6 cross-reference | `workflow_kit/common/purpose_context.py` + 3 schema + 3 skill script + test file 명시 |
| `llm_wiki_concept_purpose_spec.md` | §10 cycle table | v0.9.5 row 에 runtime layer detail 추가 (helper + 3 schema + scope_creep_warnings) |
| `llm_wiki_concept_purpose_spec.md` | 상태 / 최종 수정일 | v0.9.5 chapter 9 part 2 / 2026-06-23 갱신 |
| `session_start_skill_spec.md` | §13 (신규) | Purpose Context Load: 5 sub-section (입력/출력/절차/graceful skip/acceptance) |
| `backlog_update_skill_spec.md` | §12 (신규) | Purpose Context Load + Scope Creep Check: 6 sub-section |
| `doc_sync_skill_spec.md` | §12 (신규) | Purpose Context Load (advisory only): 6 sub-section |
| `workflow_skill_catalog.md` | §5.3 (신규) | 3종 skill purpose_context 통합 + helper + scope creep + graceful skip 정책 + acceptance 표 |
| 3 skill spec 의 *관련 문서* + *다음에 읽을 문서* | top/bottom | `llm_wiki_concept_purpose_spec.md` cross-ref 추가 |

## 운영 누적 (v0.9.4 → v0.9.5)

| | v0.9.4 | **v0.9.5** |
|---|---|---|
| **session-start purpose context** | ❌ | **✅** (`purpose_context: SessionStartPurposeContext \| None`) |
| **backlog-update purpose context** | ❌ | **✅** (`purpose_context` + `scope_creep_warnings: list[str]`) |
| **doc-sync purpose context** | ❌ | **✅** (`purpose_context: DocSyncPurposeContext \| None`, advisory only) |
| **helper module** | ❌ | **✅** (`workflow_kit.common.purpose_context.build_purpose_context`) |
| **PURPOSE.md body excerpt** | ❌ | **≤800 char (=≈200 token)**, frontmatter 제외 |
| **scope creep check** | ❌ | **`check_scope_creep`** — 제외 영역 substring / 첫-2-token 매칭, hard warning |
| **graceful skip** | n/a | **3종 skill 모두** — PURPOSE.md / state.json 부재 시 partial fill + `scope_warnings` advisory 1줄 |
| **R-A follow-up cycle** | part 1 ✅ | **part 2 ✅** (part 3 = v0.9.6 후속) |
| **cumulative acceptance** | 25/25 | **31/31** (v0.9.5 6 신규 + v0.9.4 3 + v0.9.2 8 + v0.9.3 4 + v0.9.1 4 + v0.9.0 6) |
| **deprecation cycle** | 14/14 | **14/14** (1st 6 + contract 4 + 2nd 4 — 변경 ❌) |
| **spec §9 acceptance** | 11/12 | **12/12** (R-A follow-up part 1 + part 2 ✅ — v0.9.5 = spec §9 의 2번째 follow-up 충족) |

## Test 결과

- 신규 (6 PASS, v0.9.5+):
  - `test_purpose_context_session_start_v0_9_5` — `SessionStartPurposeContext` schema + helper `build_purpose_context` 가 state.json 의 purpose_digest + PURPOSE.md body excerpt populate + scope lists
  - `test_purpose_context_backlog_update_v0_9_5` — `BacklogUpdateOutput` schema 에 `purpose_context` + `scope_creep_warnings` 2 field 존재
  - `test_purpose_context_doc_sync_v0_9_5` — `DocSyncOutput` schema 에 `purpose_context` field 존재
  - `test_scope_creep_detection_v0_9_5` — 3 case: in-scope (no warning) / task_brief 매칭 (warning 1줄) / affected_documents 매칭 (warning 1줄)
  - `test_purpose_context_graceful_skip_v0_9_5` — PURPOSE.md 부재 시 helper 가 (None, None, None, None, False, 0, [], [], ["PURPOSE.md 부재 — scope check skipped"]) 반환 + `check_scope_creep` empty excluded → no-op early return
  - `test_skill_scripts_integration_v0_9_5` (보너스) — 3종 skill script 의 subprocess 실행 stdout JSON 에 `purpose_context` field 존재 + scope_creep_warnings 가 stripe/결제 task 에서 fire
- v0.9.4 regression: **3/3 PASS** (`check_purpose_concept_state_json_v0_9_4.py`)
- v0.9.2 regression: **8/8 PASS** (`check_purpose_concept_v0_9_2.py`)
- deprecation cycle regression: **14/14 PASS** (1st cycle 6/6 + contract 4/4 + 2nd cycle 4/4)
- 누적 acceptance: **31/31 PASS** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6)
- 누적 smoke: **162/162 + 31 별도 subset** (pydantic/jsonschema 의존성 fail 은 v0.9.3 부터의 환경 의존성으로 v0.9.5 scope 밖)

## 변경 파일 (5 변경 + 2 신규 + 1 doc sync)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/core/llm_wiki_concept_purpose_spec.md` | §4.3 part 2 명세 + §5 follow-up ✅ + §6 cross-ref + §10 cycle table detail + 상태/날짜 |
| M | `workflow-source/core/session_start_skill_spec.md` | §13 신규 (Purpose Context Load 5 sub-section) + 관련문서 cross-ref + 날짜 |
| M | `workflow-source/core/backlog_update_skill_spec.md` | §12 신규 (Purpose Context Load + Scope Creep Check 6 sub-section) + 관련문서 cross-ref + 다음에 읽을 문서 |
| M | `workflow-source/core/doc_sync_skill_spec.md` | §12 신규 (Purpose Context Load advisory only 6 sub-section) + 관련문서 cross-ref + 다음에 읽을 문서 |
| M | `workflow-source/core/workflow_skill_catalog.md` | §5.3 신규 (3종 skill purpose_context 통합 + helper + scope creep + graceful skip) |
| M | `workflow-source/workflow_kit/common/schemas/session.py` | `SessionStartPurposeContext` nested model + `SessionStartOutput.purpose_context` field |
| M | `workflow-source/workflow_kit/common/schemas/backlog.py` | `BacklogUpdatePurposeContext` nested model + `BacklogUpdateOutput.purpose_context` + `scope_creep_warnings` 2 field |
| M | `workflow-source/workflow_kit/common/schemas/doc_sync.py` | `DocSyncPurposeContext` nested model + `DocSyncOutput.purpose_context` field |
| M | `workflow-source/workflow_kit/common/schemas/__init__.py` | 3 *Context class export 추가 |
| M | `workflow-source/skills/session-start/scripts/run_session_start.py` | `build_purpose_context` 호출 + `output_model.purpose_context` 채움 + `scope_warnings` extend |
| M | `workflow-source/skills/backlog-update/scripts/run_backlog_update.py` | `build_purpose_context` + `check_scope_creep` 호출 + `purpose_context_obj` + `scope_creep_warnings` 채움 |
| M | `workflow-source/skills/doc-sync/scripts/run_doc_sync.py` | `build_purpose_context` 호출 + `result["purpose_context"]` 채움 (advisory only) |
| A | `workflow-source/workflow_kit/common/purpose_context.py` | helper module 신규 (5 함수, ≈ 200 line) |
| A | `workflow-source/tests/check_purpose_concept_skill_context_v0_9_5.py` | part 2 acceptance test 신규 (6 test, ≈ 450 line) |
| A | `workflow-source/releases/Beta-v0.9.5.md` | release note (본 file) |
| M | `workflow-source/pyproject.toml` | version 0.9.4 → 0.9.5 |
| M | `README.md` | §8 + §10 + release URL list 동기화 |
| M | `ai-workflow/memory/active/work_backlog.md` | cumulative summary + index |
| A | `ai-workflow/memory/release/v0.9.5/backlog/2026-06-23.md` | v0.9.5 plan |

## 다음 (v0.9.6+ / v0.10.0 / v1.0.0 milestone)

1. **v0.9.6 (chapter 10, R-A follow-up part 3)** — wiki-event-sync R-A trigger: release event hook + 30일 ingest/query 분포 trigger + LLM suggest (advisory). spec §4.4 정합.
2. **v0.9.7 follow-up** — external reference 흡수 cycle 2: file deletion cascade cleanup (3-method matching).
3. **v0.9.8 follow-up** — external reference 흡수 cycle 3: two-step CoT ingest (session-start → backlog-update 2-step contract) 명문화.
4. **v0.9.9 follow-up** — external reference 흡수 cycle 4: graph insights (surprising + gaps) 정형화.
5. **v0.9.10 follow-up** — release pipeline 의 `--apply default=False` 전환 (memory #5 의 "destructive subcommand 정공법" 정착). breaking change 회피로 minor release 에서 점진적 전환.
6. **v0.9.11 follow-up** — mypy strict cumulative 격상 (19 → 20-21 file). 1 release = 1-2 file 단계적 격상.
7. **v0.10.0** — **deprecation 1st + 2nd cycle 동시 종료**: `phishing_federation_v4` 를 `__all__` 에서 제거 + `ImportError` raise. consumer 가 *명시적 except* 없으면 hard fail. 2nd cycle 의 `build_default_sources_v4` 도 동시 제거.
8. **v1.0.0 milestone** — full mypy strict 도달 (semver major 정렬, 100+ release 후 예상). spec §9 acceptance 12/12 도달 (v0.9.5 R-A follow-up part 2 충족 ✅ → part 3 = v0.9.6).
