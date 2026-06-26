# Beta v0.11.1 — Graph insights (R-A follow-up cycle 4) (2026-06-26)

> **SemVer patch** (v0.11.0 → v0.11.1) — v0.11.0 release note 의 "다음" §1 follow-up. **R-A follow-up cycle 4**: PURPOSE.md 의 4-element ↔ 실제 deliverable 의 *graph insights* 정형화. *directional intent* vs *structural facts* 의 불일치 발견 → Evolving Thesis 갱신 trigger. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 신규 helper + 1 CLI subcommand + 1 spec layer extension + 8 acceptance test)

### 1. Graph insights (R-A follow-up cycle 4)

**v0.11.0 cycle 3 (two-step CoT ingest) 의 후속** — Karpathy `llm-wiki.md` + llm_wiki (nashsu) 의 *Purpose.md — The Wiki's Soul* concept 의 *LLM can suggest updates based on usage patterns* 패턴을 PURPOSE ↔ deliverable 매핑 분석으로 정형화.

**기존 LLM context read pattern**:
- **v0.9.4 part 1** — `state.json.purpose_digest` 1-line 자동 생성
- **v0.9.5 part 2** — skill context load (PURPOSE.md 본문 ≤800 char + scope check)
- **v0.9.6 part 3** — wiki-event-sync R-A trigger (30일 분포 + LLM suggest)
- **v0.11.0 cycle 3** — two-step CoT ingest (raw → structured 4-element + cross-ref validate)
- **v0.11.1 cycle 4 (본 release)** — graph insights (PURPOSE.md ↔ deliverable 매핑 분석 + health score)

**`workflow_kit.common.purpose_graph` helper module 신규** (≈ 380 line):
- `extract_goal_keywords(purpose_path) -> list[GoalKeyword]` — PURPOSE.md §1 Goals 의 G1+ identifier + 본문 keyword 추출 (한글/영문 mixed content + stop word 제거)
- `parse_recent_done_items(state_path) -> list[RecentDoneItem]` — state.json recent_done_items 30+ entries 파싱 (version + commit hash + summary + keywords)
- `compute_goal_coverage(goals, items) -> GoalCoverageResult` — Jaccard similarity 기반 3 분류 (covered ≥50% / partial <50% / uncovered 0) + coverage_pct
- `find_surprising_deliverables(goals, items, scope_excluded) -> SurprisingResult` — Goals 매핑 0 + scope_excluded 매칭 ❌ → scope_creep 감지 (advisory warning)
- `find_gaps(goals, items) -> GapResult` — Goals 중 deliverable 매핑 0 인 goal 식별 (priority 1-3)
- `compute_health_score(coverage, surprising, gaps) -> HealthScore` — 100 - uncovered×15 - scope_creep×10 + min(surprising×5, 25) (4 tier: excellent/good/fair/poor)
- `run_graph_insights(purpose_path, workspace_root, state_path, ...) -> GraphInsightsResult` — unified entry (auto-find + include_surprising + include_gaps 옵션)
- 6 dataclass: `GoalKeyword` / `RecentDoneItem` / `GoalCoverageResult` / `SurprisingResult` / `GapResult` / `HealthScore` / `GraphInsightsResult`

**Graph insights 의 핵심 가치**:
- **Goal coverage**: `4/4 (25%)` 와 같이 정량화 — Evolving Thesis 의 "지금까지의 working hypothesis" 갱신 근거
- **Surprising 발견**: 의도하지 않은 deliverable (scope creep 의심) 자동 감지 → 운영자가 회고 시 즉시 식별
- **Gaps 식별**: §1 Goals 중 deliverable 0 인 goal (priority 1-3) → 다음 backlog 우선순위 결정
- **Health score**: 4 tier 정량화 (excellent ≥80 / good ≥60 / fair ≥40 / poor <40) — 트래킹 가능

### 2. CLI dispatcher subcommand `graph-insights` (v0.11.1+ 신규)

`workflow_kit/workflow_kit_cli.py` 의 dispatcher registry 에 subcommand 34 신규:

- `--purpose-path=PATH` (optional, default: auto-detect)
- `--workspace-root=PATH` (optional, default: cwd)
- `--state-path=PATH` (optional, default: auto-detect)
- `--no-surprising` (boolean, default: false)
- `--no-gaps` (boolean, default: false)
- `--json` (optional) — JSON output

**Read-only analysis only** (destructive subcommand 정공법 memory #5):
- file I/O ❌ (state.json 미변경)
- 출력은 advisory emit 만 (coverage + surprising + gaps + health score)

**Dispatcher registry 누적**: 34 subcommand (v0.11.0 ingest-purpose 33 → v0.11.1 graph-insights 34)

### 3. Spec layer 갱신 (1 spec)

| Spec | Section | 변경 |
|---|---|---|
| `core/llm_wiki_concept_purpose_spec.md` | §4.3 cycle 4 | v0.11.1 cycle 4 entry 추가 (graph insights 정공법 + 5 함수 + 6 dataclass + read-only + graceful skip) |
| `core/llm_wiki_concept_purpose_spec.md` | §5 acceptance criterion | cycle 4 check item (`[ ]`) 추가 |
| `core/llm_wiki_concept_purpose_spec.md` | §6 cross-reference | 4 신규 file (purpose_graph.py + 3 schema extension + cmd_graph_insights + test file) cross-ref |
| `core/llm_wiki_concept_purpose_spec.md` | §10 R-A follow-up cycle table | 5 release 분할 정합 (v0.9.4~v0.9.6 ✅ + v0.11.0 cycle 3 ✅ + v0.11.1 cycle 4 follow-up) |
| `core/llm_wiki_concept_purpose_spec.md` | 헤더 | 최종 수정일 `2026-06-26` |

## 운영 누적 (v0.11.0 → v0.11.1)

| | v0.11.0 | **v0.11.1** |
|---|---|---|
| **SemVer bump** | minor | **patch** |
| **`workflow_kit.common.purpose_graph`** | ❌ | **✅ (6 함수 + 7 dataclass + unified entry, ≈ 380 line)** |
| **`cmd_graph_insights` subcommand** | ❌ | **✅ (subcommand 34, read-only)** |
| **cumulative acceptance** | 69/69 | **77/77** (v0.11.1 8 신규) |
| **spec §9 acceptance** | 12/12 | **12/12** (변동 ❌) |
| **breaking change** | none | **none** (read-only dispatch, v0.11.0 호환) |
| **Bundle 비율 (1차 출처)** | ~92% | **~95%** (graph insights 정형화) |

## Test 결과

- 신규 (8 PASS, v0.11.1):
  - `test_extract_goal_keywords_v0_11_1` — Goals G1+ 추출 (정상 4 / 한국어 keyword / empty / None path 4 case)
  - `test_parse_recent_done_items_v0_11_1` — state.json recent_done_items 파싱 (정상 3 / None / corrupted 3 case)
  - `test_compute_goal_coverage_v0_11_1` — Goals ↔ deliverables 매칭 (전부 covered / 1/2 covered / 전부 uncovered 3 case)
  - `test_find_surprising_deliverables_v0_11_1` — scope_creep 감지 (scope_creep 의심 / out-of-scope 의도 2 case)
  - `test_find_gaps_v0_11_1` — Goals 중 deliverable 0 (2 gaps [G1, G3], priorities [1, 2])
  - `test_compute_health_score_v0_11_1` — 4 tier verify (100 excellent / 50% good / 4 uncovered poor / None)
  - `test_run_graph_insights_unified_v0_11_1` — unified entry graceful skip (정상 / PURPOSE 부재 / state 부재 / 둘 다 부재 4 case)
  - `test_graph_insights_cli_registered_v0_11_1` — CLI subcommand 등록 (subcommand 34, total 34) + dry-run subprocess verify (state.json 보존) + output field completeness
- v0.11.0 회귀: **6/6 PASS** ✅
- v0.10.3 회귀: **7/7 PASS** ✅
- v0.10.2 회귀: **9/9 PASS** ✅
- v0.10.1 회귀: **6/6 PASS** ✅
- v0.10.0 회귀: **6/6 PASS** ✅
- v0.9.6 회귀: **6/6 PASS** ✅
- v0.9.5 회귀: **6/6 PASS** ✅
- v0.9.4 회귀: **3/3 PASS** ✅
- v0.9.2 회귀: **8/8 PASS** ✅
- v0.9.3 회귀: **4/4 PASS** ✅
- v0.9.1 회귀: **4/4 PASS** ✅
- v0.9.0 회귀: **6/6 PASS** ✅
- 누적 acceptance: **77/77 PASS**
- 누적 smoke: **162/162 + 77 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6 + v0.9.6 6 + v0.10.0 6 + v0.10.1 6 + v0.10.2 9 + v0.10.3 7 + v0.11.0 6 + v0.11.1 8)

## 변경 파일 (5 변경 + 5 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/workflow_kit/workflow_kit_cli.py` | `cmd_graph_insights` 등록 (subcommand 34) + docstring + 6 flag parse |
| M | `workflow-source/core/llm_wiki_concept_purpose_spec.md` | §4.3 cycle 4 + §5 + §6 + §10 cycle table + 최종 수정일 갱신 |
| M | `workflow-source/pyproject.toml` | version 0.11.0 → 0.11.1 |
| M | `workflow-source/workflow_kit/__init__.py` | `_read_pyproject_version` loud fallback literal `"v0.11.0-beta"` → `"v0.11.1-beta"` |
| M | `ai-workflow/memory/active/state.json` | v0.11.1 in_progress + latest_backlog_path 갱신 |
| A | `workflow-source/workflow_kit/common/purpose_graph.py` | helper module 신규 (6 함수 + 7 dataclass, ≈ 380 line) |
| A | `workflow-source/tests/check_graph_insights_v0_11_1.py` | 신규 (8 acceptance test, ≈ 460 line) |
| A | `workflow-source/releases/Beta-v0.11.1.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.11.1/backlog/2026-06-26.md` | v0.11.1 plan |

## 다음 (v0.11.2+ / v1.0.0)

1. **v0.11.2 follow-up** — release pipeline `--apply default=False` 전환 (memory #5 의 "destructive subcommand 정공법" 정착). breaking change 회피로 patch release 에서 점진적 전환.
2. **v0.11.3 follow-up** — mypy strict cumulative 격상 (19 → 20-21 file). 1 release = 1-2 file 단계적 격상.
3. **v1.0.0 milestone** — full mypy strict 도달 (semver major 정렬, 100+ release 후 예상). spec §9 acceptance 12/12 도달 유지.

## Bundle 비율 (1차 출처 Karpathy + llm_wiki)

| cycle | bundle 비율 |
|---|---|
| v0.9.2 chapter 6 | ~75% |
| v0.9.5 part 2 | ~75% |
| v0.9.6 part 3 | ~80% |
| v0.11.0 cycle 3 | ~92% |
| **v0.11.1 cycle 4** | **~95%** |

신규 concept 100% 흡수:
- Graph insights (Goals ↔ deliverable 매핑): **100%**
- Surprising 발견 (scope creep 감지): **80%** (LLM context 외 단순 heuristic)
- Gaps 식별 (uncovered goal priority): **90%** (priority 1-3 heuristic)
- Health score (tier 정량화): **100%**
