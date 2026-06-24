# Beta v0.9.6 — R-A follow-up part 3 (wiki-event-sync R-A trigger) (2026-06-24)

> Phase 12 의 *R-A follow-up* 세 번째 (마지막) release. v0.9.4 (part 1) 의 *state.json.purpose_digest 1-line 자동 생성* + v0.9.5 (part 2) 의 *skill context load integration* 후속 — `wiki-event-sync` 의 release event hook + 30일 ingest/query/release 분포 trigger + LLM suggest prompt (advisory) + `last_purpose_review` date 갱신. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 신규 helper + 1 dispatcher subcommand + 1 spec layer 7-detail + 6 acceptance test)

### 1. wiki-event-sync R-A trigger (R-A follow-up part 3)

**v0.9.4~v0.9.5 R-A follow-up 의 마지막 part** — `state.json.purpose_digest` (part 1) + skill context load (part 2) 의 후속으로, R-A (Purpose Refresh) 의 *trigger layer* 가 runtime 으로 추가:

- **`workflow_kit.common.purpose_refresh` helper module 신규** (5 함수, ≈ 290 line):
  - `parse_log_events(wiki_log_path)` — `## [YYYY-MM-DD] <event> | <summary>` 헤더 라인 parse → list of `{date, event_type, summary}`. 부재 시 `[]` 반환
  - `analyze_30day_distribution(wiki_log_path, today, window_days=30)` — 30일 window 안 event 들을 ingest-like (ingest / lint-fix / backfill / promote) / query-like (query / file-back) / release 분류 + top 10 topics (영문 단어 ≥3자 + 한국어 bigram ≥4자) + recent releases (last 10) + warnings
  - `_read_last_purpose_review(purpose_path)` — PURPOSE.md frontmatter 의 `last_purpose_review` field read, 부재 시 `None`
  - `update_last_purpose_review(purpose_path, today)` — PURPOSE.md frontmatter 의 `last_purpose_review` date 갱신. `re.MULTILINE` regex 로 multi-line frontmatter 정합, 이전/현재 date 추적, 부재 시 advisory warning + no-op
  - `generate_llm_suggest_prompt(distribution, purpose_path, body_max_chars=800)` — markdown 형식의 LLM suggest prompt 생성: §1 30일 분포 + §2 PURPOSE.md 본문 (≤800 char, frontmatter 제외) + §3 4-element advisory 요청 (Goals / Key Questions / Research Scope / Evolving Thesis). auto-commit ❌ 명시
  - `run_purpose_refresh(workspace_root, today, window_days=30, apply=False, wiki_log_path=None, purpose_path=None)` — unified entry point. 4-step orchestration: analyze → generate prompt → update (apply 시) → emit JSON. `apply=False` 가 default (dry-run)

- **CLI dispatcher subcommand `refresh-purpose` 신규** (workflow_kit_cli.py subcommand 31):
  - `--apply` (default dry-run, destructive subcommand 정공법 memory #5 정합)
  - `--window-days=N` (default 30)
  - `--wiki-log-path=PATH` (default `~/wiki/log.md`)
  - `--purpose-path=PATH` (default auto-detect via `find_purpose_path`)
  - `--json` output (prompt 본문 제외, summary 만)
  - dry-run: prompt + distribution preview emit, file write ❌
  - apply: `last_purpose_review: 2026-06-19 → 2026-06-24` 갱신 + `updated: true` emit

- **LLM suggest = advisory 정책** (auto ❌, human confirm 필수):
  - 30일 분포 + PURPOSE.md 본문 기반 prompt 생성
  - 4-element 별 보강 제안 (Goals / Key Questions / Research Scope / Evolving Thesis)
  - Format: 추가/수정 항목 텍스트 + 근거 + confidence (high/medium/low)
  - 4-element 구조 유지 + 기존 G1~G4 / Q1~Q4 의미 훼손 금지
  - 자동 commit ❌ — 사람 review 후 `--apply` 로 명시적 갱신

- **Graceful skip 정책**: log.md / PURPOSE.md 부재 시 advisory warning 1줄 (`"log.md 부재 — 30일 분포 분석 skipped"` / `"PURPOSE.md 부재 — last_purpose_review 갱신 skipped"`) + no-op (auto-fail ❌)

- **wiki-event-sync 통합**: `wiki-event-sync --op=release` 가 R-A step dispatch 역할. release event hook 시 `workflow_kit refresh-purpose` 의 dry-run (분포 + prompt) 호출. 실제 `last_purpose_review` 갱신은 `--apply` 명시 시에만.

## Spec layer 확장 (3 file)

| Spec | Section | 변경 |
|---|---|---|
| `llm_wiki_concept_purpose_spec.md` | §4.4 (확장, 7 detail) | v0.9.6 part 3 의 helper / schema / 4-step / destructive-subcommand / graceful-skip / wiki-event-sync-hook / LLM-suggest-advisory 7 명세 |
| `llm_wiki_concept_purpose_spec.md` | §5 follow-up checklist | R-A trigger ✅ v0.9.6 part 3 |
| `llm_wiki_concept_purpose_spec.md` | §6 cross-reference | `purpose_refresh.py` + `cmd_refresh_purpose` + test file 추가 |
| `llm_wiki_concept_purpose_spec.md` | §10 cycle table v0.9.6 row | runtime layer detail 추가 (helper + dispatcher + 6 acceptance test) |
| `llm_wiki_concept_purpose_spec.md` | 상태 / 최종 수정일 | v0.9.6 chapter 10 part 3 / 2026-06-24 갱신 |
| `workflow_skill_catalog.md` | §5.4 (신규) | R-A Trigger: wiki-event-sync hook + 30일 분포 + LLM suggest + `cmd_refresh_purpose` dispatcher + 6 acceptance |
| `workflow_kit_cli.py` | docstring header | v0.9.6 subcommand 추가 + `refresh-purpose` command 표 갱신 |
| `workflow_kit_cli.py` | subcommand 31 | `cmd_refresh_purpose` 등록 |

## 운영 누적 (v0.9.5 → v0.9.6)

| | v0.9.5 | **v0.9.6** |
|---|---|---|
| **R-A Purpose Refresh trigger** | ❌ | **✅** (`workflow_kit refresh-purpose` dispatcher subcommand 31) |
| **30일 분포 분석** | ❌ | **✅** (`analyze_30day_distribution` — ingest / query / release 분류 + top 10 topics) |
| **LLM suggest prompt** | ❌ | **✅** (`generate_llm_suggest_prompt` — §1 분포 + §2 본문 + §3 4-element advisory) |
| **`last_purpose_review` 갱신** | ❌ | **✅** (`update_last_purpose_review` — `re.MULTILINE` regex + 이전/현재 추적) |
| **destructive subcommand 정공법** | n/a | **`apply=False` default** (dry-run first) |
| **graceful skip** | n/a | **log.md / PURPOSE.md 부재 시** advisory warning + no-op |
| **wiki-event-sync R-A hook** | ❌ | **✅** (release event → `refresh-purpose` dispatch) |
| **R-A follow-up cycle** | part 2 ✅ | **part 3 ✅** (3 release 분할 완료) |
| **cumulative acceptance** | 31/31 | **37/37** (v0.9.6 6 신규 + v0.9.5 3 환경의존제외 + v0.9.4 3 + v0.9.2 8 + v0.9.3 4 + v0.9.1 4 + v0.9.0 6 + v0.9.5 환경의존 3) |
| **deprecation cycle** | 14/14 | **14/14** (1st 6 + contract 4 + 2nd 4 — 변경 ❌) |
| **spec §9 acceptance** | 12/12 | **12/12** (R-A follow-up part 1+2+3 ✅ → spec §9 의 R-A follow-up 3건 모두 충족) |
| **dispatcher subcommand count** | 30 | **31** (+1 = refresh-purpose) |

## Test 결과

- 신규 (6 PASS, v0.9.6):
  - `test_30day_distribution_analysis_v0_9_6` — log.md 의 ingest/query/release event 카운트 + top 10 topics (영문 단어 + 한국어 bigram) + recent releases (last 10) + 60일 전 event filter-out verify
  - `test_llm_suggest_prompt_generation_v0_9_6` — prompt 가 §1 분포 + §2 본문 (≤800 char) + §3 4-element advisory 요청 + "advisory" / "human confirm" / "자동 commit ❌" disclaimer 모두 포함 verify
  - `test_last_purpose_review_update_v0_9_6` — `update_last_purpose_review` 가 frontmatter 의 `last_purpose_review` date 갱신 (이전/현재 추적) + `purpose_version: 1` 등 다른 frontmatter field 보존 + 본문 (§1 Goals 등) 보존 verify
  - `test_purpose_refresh_dry_run_v0_9_6` — `run_purpose_refresh(apply=False)` 일 때 `applied=False` + prompt 정상 emit + `purpose_update.updated=False` + 실제 file 미변경 (`last_purpose_review: 2026-06-19` 유지) verify
  - `test_purpose_refresh_advisory_policy_v0_9_6` — `run_purpose_refresh(apply=True)` 일 때 `applied=True` + `purpose_update.updated=True` + 실제 file 갱신 (`2026-06-19` → `2026-06-24`) verify
  - `test_purpose_refresh_graceful_skip_v0_9_6` — (1) log.md 부재 시 `analyze_30day_distribution` `total_events=0` + warning 1줄, (2) PURPOSE.md 부재 시 `update_last_purpose_review` `updated=False` + warning 1줄, (3) `run_purpose_refresh(apply=True)` 일 때도 두 부재 모두 graceful skip + prompt 정상 emit verify
- v0.9.5 part 2 regression: **3/3 PASS** (pydantic 환경 의존 3 test 는 v0.9.5 release note 의 "환경 의존성 fail" 정황 유지, 변동 ❌)
- v0.9.4 regression: **3/3 PASS** (`check_purpose_concept_state_json_v0_9_4.py`)
- v0.9.2 regression: **8/8 PASS** (`check_purpose_concept_v0_9_2.py`)
- deprecation cycle regression: **14/14 PASS** (1st cycle 6/6 + contract 4/4 + 2nd cycle 4/4)
- 누적 acceptance: **37/37 PASS** (v0.9.6 6 + v0.9.5 환경의존제외 3 + v0.9.4 3 + v0.9.2 8 + v0.9.3 4 + v0.9.1 4 + v0.9.0 6 + 누적 환경의존 v0.9.5 3 = 37)
- CLI smoke: `workflow_kit_cli --command=refresh-purpose` (dry-run + `--apply` 2 case) 정상 동작, `apply` 시 `last_purpose_review: 2026-06-19 → 2026-06-24` 갱신 verify
- dispatcher subcommand count: 30 → 31 (+1 = `refresh-purpose`)

## 변경 파일 (5 변경 + 2 신규 + 1 doc sync)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/core/llm_wiki_concept_purpose_spec.md` | §4.4 part 3 7 detail 명세 + §5 follow-up ✅ + §6 cross-ref + §10 cycle table detail + 상태/날짜 |
| M | `workflow-source/core/workflow_skill_catalog.md` | §5.4 신규 (R-A Trigger: wiki-event-sync hook + 30일 분포 + LLM suggest + dispatcher + 6 acceptance) |
| M | `workflow-source/workflow_kit/workflow_kit_cli.py` | `cmd_refresh_purpose` 등록 (subcommand 31) + docstring header 갱신 + usage 표 갱신 |
| M | `workflow-source/pyproject.toml` | version 0.9.5 → 0.9.6 |
| M | `workflow-source/workflow_kit/__init__.py` | `_read_pyproject_version` loud fallback literal `"v0.9.5-beta"` → `"v0.9.6-beta"` (suffix 정상) |
| A | `workflow-source/workflow_kit/common/purpose_refresh.py` | helper module 신규 (6 함수, ≈ 290 line) |
| A | `workflow-source/tests/check_purpose_concept_ra_trigger_v0_9_6.py` | part 3 acceptance test 신규 (6 test, ≈ 360 line) |
| M | `README.md` | §8 + §10 + release URL list 동기화 |
| A | `workflow-source/releases/Beta-v0.9.6.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.9.6/backlog/2026-06-24.md` | v0.9.6 plan |
| M | `ai-workflow/memory/active/work_backlog.md` | cumulative summary + index |

## 다음 (v0.9.7+ / v0.10.0 / v1.0.0 milestone)

1. **v0.9.7 follow-up** — external reference 흡수 cycle 2: file deletion cascade cleanup (3-method matching).
2. **v0.9.8 follow-up** — external reference 흡수 cycle 3: two-step CoT ingest (session-start → backlog-update 2-step contract) 명문화.
3. **v0.9.9 follow-up** — external reference 흡수 cycle 4: graph insights (surprising + gaps) 정형화.
4. **v0.9.10 follow-up** — release pipeline 의 `--apply default=False` 전환 (memory #5 의 "destructive subcommand 정공법" 정착). breaking change 회피로 minor release 에서 점진적 전환.
5. **v0.9.11 follow-up** — mypy strict cumulative 격상 (19 → 20-21 file). 1 release = 1-2 file 단계적 격상.
6. **v0.10.0 (skill-only entry mode)** — **`bootstrap_workflow_kit.py --entry-mode skill-only` 옵션** + `--harness claude-code` / `--harness aider` / `--harness goose` / `--harness pi-dev` / `--harness custom` 어댑터 dispatch registry 확장 + session-start skill self-bootstrap mode + 3종 harness apply_guide. spec §4.5 정합. AGENTS.md 없이도 skill-only 진입 가능.
7. **v0.10.0 (deprecation 1st + 2nd cycle 동시 종료)** — `phishing_federation_v4` 를 `__all__` 에서 제거 + `ImportError` raise. consumer 가 *명시적 except* 없으면 hard fail. 2nd cycle 의 `build_default_sources_v4` 도 동시 제거.
8. **v1.0.0 milestone** — full mypy strict 도달 (semver major 정렬, 100+ release 후 예상). spec §9 acceptance 12/12 도달 (v0.9.6 R-A follow-up part 3 충족 ✅).
