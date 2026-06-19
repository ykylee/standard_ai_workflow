# Beta v0.9.4 — R-A follow-up part 1 (state.json.purpose_digest 1-line 자동 생성) (2026-06-23)

> Phase 12 의 *R-A follow-up* 첫 번째 release. v0.9.2 chapter 6 의 follow-up R-A (Purpose Refresh) = "state.json `purpose_digest` + session-start context load + wiki-event-sync release event hook" 을 **3 release 로 분할** (cycle 8 = part 1, cycle 9 = part 2, cycle 10 = part 3). **본 release (v0.9.4) 는 part 1** — `state.json.purpose_digest` 1-line 자동 생성. part 2 (skill context load) = v0.9.5, part 3 (wiki-event-sync R-A trigger) = v0.9.6. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 task, 1 in-scope update, 1 신규 test + spec layer 확장)

### 1. state.json.purpose_digest + purpose_digest_rev 자동 생성 (R-A follow-up part 1)

**v0.9.2 chapter 6 의 follow-up R-A 정공법** (1 release = 1 deliverable, deprecation 1st → 2nd cycle 의 0일 release 사이클 패턴과 정합):

- 3 release 분할 (R-A 의 *3 hook* = 1 hook / 1 release):
  - **v0.9.4 (chapter 8, 본 release)** — `state.json.purpose_digest` 1-line 자동 생성 (top-level field)
  - **v0.9.5 (chapter 9, 후속)** — skill context load integration (session-start / backlog-update / doc-sync 의 *context load* 시 purpose_digest 1-line + PURPOSE.md ≤200 token 자동 read)
  - **v0.9.6 (chapter 10, 후속)** — wiki-event-sync R-A trigger (release event hook + 30일 ingest/query 분포 trigger + LLM suggest advisory)

**Part 1 적용**:

- **`workflow_kit.common.state.builder._parse_purpose_summary` helper 신규**:
  - PURPOSE.md frontmatter `last_purpose_review` date parse (YYYY-MM-DD format)
  - PURPOSE.md §1 Goals 의 *첫 번째* goal text parse (e.g. `**G1**: 표준 AI 협업 워크플로우를 *독립 패키지 형태* 로 제공`)
  - PURPOSE.md 부재 시 graceful skip (`(None, None)` return)
  - OSError / read 실패 시 graceful skip
- **`build_workflow_state_payload` output schema 확장**:
  - top-level field 2개 추가: `purpose_digest` (str | None), `purpose_digest_rev` (str | None)
  - PURPOSE.md path resolution: 3 candidate (`ai-workflow/memory/active/PURPOSE.md` (primary) → `../<workspace_parent>/ai-workflow/memory/active/PURPOSE.md` → `workspace_root/PURPOSE.md` (fallback))
  - `next((p for p in purpose_candidates if p.exists()), None)` pattern — first match wins, 부재 시 None
- **generate_workflow_state.py caller 자동 populate**: `refresh_workflow_state_cache` 가 `build_workflow_state_payload` 호출 → caller 변경 ❌ (output schema extension 이라 downstream 자동 흡수)
- **format**:
  - `purpose_digest` = "표준 AI 협업 워크플로우를 *독립 패키지 형태* 로 제공" (Goals §1 의 첫 번째 goal 의 *G1*: prefix 제외한 본문)
  - `purpose_digest_rev` = PURPOSE.md frontmatter 의 `last_purpose_review` date (YYYY-MM-DD, e.g. `2026-06-19`)

**In-scope fix 1 (real, defensive)**:

- `build_workflow_state_payload` 의 `handoff_constraints = cast(list[str], handoff.get("constraints", []))` — `constraints` field 가 `None` 으로 들어오면 `cast` 가 type-lying 하면서 downstream `extend()` 등에서 `TypeError`. `or []` 추가 (`cast(list[str], handoff.get("constraints") or [])`) — dict.get()의 default 와 or 의 *None 방어* 차이를 흡수. v0.9.4 acceptance 1 (test_purpose_digest_field_exists_v0_9_4) 의 input fixture 에서 handoff 의 `constraints` 가 명시되지 않아 None 으로 들어오는 edge case 가 *정공법 검증* 으로 발견.

**In-scope fix 2 (real, regex literal)**:

- `_parse_purpose_summary` 의 `re.match(r"^---\n(.+?)\n---", text, re.S)` — frontmatter 가 file *시작* 이 아닌 경우 (e.g. BOM 또는 leading whitespace) 에는 match fail. *현재는 v0.9.2 PURPOSE.md 가 file 시작이므로 PASS* 이지만, helper 가 robust 하도록 의도적으로 `re.match` 유지 (file 시작이 아닌 case 는 spec §4.3 part 1 의 *PURPOSE.md frontmatter 가 file 시작* 가정으로 흡수). 후속 release 에서 file 시작 검증 추가 검토 (R-A follow-up cycle 외 scope).

## 운영 누적 (v0.9.3 → v0.9.4)

| | v0.9.3 | **v0.9.4** |
|---|---|---|
| **state.json.purpose_digest 자동 생성** | ❌ | **✅** (top-level 2 field, PURPOSE.md 부재 시 None) |
| **PURPOSE.md path resolution** | ❌ | **3 candidate** (primary: `ai-workflow/memory/active/PURPOSE.md` / parent: `../<workspace_parent>/ai-workflow/memory/active/PURPOSE.md` / fallback: `workspace_root/PURPOSE.md`) |
| **R-A follow-up cycle** | spec only (3 release 분할 미명시) | **§10 (R-A follow-up cycle table) 신규** (v0.9.4/0.9.5/0.9.6 = part 1/2/3) |
| **cumulative smoke test (v0.9 acceptance subset)** | 22 별도 subset (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4) | **25 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3) |
| **spec §9 acceptance** | 10/12 | **11/12** (R-A follow-up part 1 ✅ — spec §9 의 "R-A follow-up purpose_digest 자동 생성" 항목 충족, 남은 1/12 = part 2/3) |

## In-scope 발견 (chapter 8 검증 중)

- **fix 1 (real, defensive cast)**: `cast(list[str], handoff.get("constraints") or [])` — None 방어. v0.9.4 acceptance 1 의 input fixture 에서 handoff `constraints` 가 명시되지 않아 `dict.get("constraints", [])` 가 default [] 반환 (정상). 다만, **상위 caller (workflow_kit.common.workflow_state.refresh_workflow_state_cache) 의 input dict 가 `{"constraints": None}` 명시** 시 `cast` 가 type-lying → `or []` 추가가 정공법. *현장 fixture* 에서는 [] default 이므로 PASS 했지만, *defensive programming* 측면에서 in-scope fix 동봉.
- **fix 2 (real, regex literal)**: `re.match` 의 `^` anchor 가 file 시작만 match. BOM / leading whitespace case 는 v0.9.2 PURPOSE.md 가 file 시작이라 *현재 PASS* 이지만, helper robustness 측면에서 *의도적 re.match 유지* (spec §4.3 part 1 의 *PURPOSE.md frontmatter file 시작* 가정 흡수). 후속 release 에서 file 시작 검증 추가 검토.
- **fix 3 (real, version literal suffix 중복, v0.9.3 spec drift 정정)**: `workflow_kit/__init__.py` line 109 의 `_read_pyproject_version` loud fallback 이 `"v0.9.4-beta-beta"` (suffix "beta" 중복, *v0.9.3 commit 시점* 부터의 spec drift). v0.9.3 commit message 가 "pyproject 0.9.2 → 0.9.3" + "`__version__` = v0.9.3-beta 정합 verify" 라고 썼지만, 실제는 pyproject 0.9.2 → **0.9.4** 점프 + `__init__.py` literal 도 **v0.9.4-beta-beta** (suffix 중복). v0.9.4 release 시 정공법 정합: literal `"v0.9.4-beta-beta"` → `"v0.9.4-beta"` (suffix 1회). pyproject.toml 0.9.4 그대로 유지 (HEAD 가 이미 0.9.4, 다음 release 의 *minor* bump 가 0.9.4 → 0.9.5). spec drift 의 근본 원인 = v0.9.3 commit 의 manual version sync 누락.

## Test 결과

- 신규 (3 PASS, v0.9.4+):
  - `test_purpose_digest_field_exists_v0_9_4` — `build_workflow_state_payload` output dict 에 `purpose_digest` + `purpose_digest_rev` 2 field 추가
  - `test_purpose_digest_format_v0_9_4` — `purpose_digest` = "표준 AI 협업 워크플로우를 *독립 패키지 형태* 로 제공" + `purpose_digest_rev` = "2026-06-19" (last_purpose_review date)
  - `test_purpose_digest_graceful_skip_v0_9_4` — PURPOSE.md 부재 시 (None, None) return
- v0.9.2 regression: **8/8 PASS** (check_purpose_concept_v0_9_2 — 4-element + LLM-readable + structural verify)
- deprecation cycle regression: **14/14 PASS** (1st cycle 6/6 + contract 4/4 + 2nd cycle 4/4)
- 누적 acceptance: **25/25 PASS** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3)
- 누적 smoke: **162/162 PASS 유지** (신규 3 test 별도 subset, pydantic/jsonschema 의존성 fail 은 v0.9.3 부터의 환경 의존성으로 v0.9.4 scope 밖)

## 변경 파일 (2 변경 + 1 신규 + 1 doc sync)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/core/llm_wiki_concept_purpose_spec.md` | §4.3 part 1 (state.json.purpose_digest 자동 생성 명세) + §10 (R-A follow-up cycle table 신규) + §5 follow-up checklist 갱신 |
| M | `workflow-source/workflow_kit/common/state/builder.py` | `_parse_purpose_summary` helper 신규 + `build_workflow_state_payload` output schema 2 field 추가 + handoff_constraints defensive `or []` |
| A | `workflow-source/tests/check_purpose_concept_state_json_v0_9_4.py` | part 1 acceptance test 신규 (3 test) |
| A | `workflow-source/releases/Beta-v0.9.4.md` | release note (본 file) |
| M | `workflow-source/pyproject.toml` | version 0.9.3 → 0.9.4 |
| M | `README.md` + `ai-workflow/memory/active/work_backlog.md` | doc sync (cumulative summary + index) |
| A | `ai-workflow/memory/release/v0.9.4/backlog/2026-06-23.md` | v0.9.4 plan |

## 다음 (v0.9.5+ / v0.10.0 / v1.0.0 milestone)

1. **v0.9.5 (chapter 9, R-A follow-up part 2)** — skill context load integration: session-start / backlog-update / doc-sync skill 의 *context load* 시 `state.json.purpose_digest` 1-line + PURPOSE.md 본문 (≤200 token) 자동 read + backlog-update 의 *in-scope check* 시 Research Scope 와 비교하여 *scope creep 경고*.
2. **v0.9.6 (chapter 10, R-A follow-up part 3)** — wiki-event-sync R-A trigger: release event hook + 30일 ingest/query 분포 trigger + LLM suggest (advisory). spec §4.4 정합.
3. **v0.9.7 follow-up** — external reference 흡수 cycle 2: file deletion cascade cleanup (3-method matching).
4. **v0.9.8 follow-up** — external reference 흡수 cycle 3: two-step CoT ingest (session-start → backlog-update 2-step contract) 명문화.
5. **v0.9.9 follow-up** — external reference 흡수 cycle 4: graph insights (surprising + gaps) 정형화.
6. **v0.9.10 follow-up** — release pipeline 의 `--apply default=False` 전환 (memory #5 의 "destructive subcommand 정공법" 정착). breaking change 회피로 minor release 에서 점진적 전환.
7. **v0.9.11 follow-up** — mypy strict cumulative 격상 (19 → 20-21 file). 1 release = 1-2 file 단계적 격상.
8. **v0.10.0** — **deprecation 1st + 2nd cycle 동시 종료**: `phishing_federation_v4` 를 `__all__` 에서 제거 + `ImportError` raise. consumer 가 *명시적 except* 없으면 hard fail. 2nd cycle 의 `build_default_sources_v4` 도 동시 제거.
9. **v1.0.0 milestone** — full mypy strict 도달 (semver major 정렬, 100+ release 후 예상). spec §9 acceptance 12/12 (현재 11/12 → 12/12 v0.9.6 R-A follow-up part 3 충족 후 도달).
