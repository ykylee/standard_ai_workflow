# Beta v0.15.21 — Phase 13 follow-up 1차 (AC2 telemetry 다양성 + CHANGELOG lockdown) (2026-07-21)

> Phase 13 follow-up 진입 첫 release.
> roadmap §8 의 P0-2 (telemetry source 다양성 ≥ 4 AC2 수렴) + P1-1 (CHANGELOG auto-gen lockdown) close-out.
> P1-2 / P1-3 (repro-scaffold / git-conflict-resolver 승격) 은 이미 v0.11.24 에서 완료됨을 확인 (stale roadmap 정정).

## 1. 릴리스 요약

- **AC2 telemetry source 다양성 ≥ 4 수렴**: 3 skill (session-start / doc-sync / backlog-update) 의 memory_index retrieval 게이트를 opt-in → *workspace memory_index 존재 시 자동 활성* 으로 전환. dispatcher 1 source → 4 source (dispatcher + 3 skill), live hit_rate 1.0.
- **CHANGELOG.md auto-gen lockdown**: `cmd_release` 에 `changelog-gen` pre-step auto-wire + `RELEASE_RE` 를 맨몸 `vX.Y.Z —` commit 형식까지 확장 + semver 정렬로 backfill 정상화.
- **roadmap stale 정리**: automated-repro-scaffold / git-conflict-resolver 는 이미 v0.11.24 4th batch 에서 stable 승격 완료 (12 skill 전량 stable).
- **pre-existing drift 해소**: sample tool_version v0.15.18 → v0.15.21 (v0.15.19/20 이 미갱신하던 sample_version case_2 drift 동반 해소).
- breaking change: ❌.

## 2. deliverable (3개)

### 2.1 AC2 — telemetry source 다양성 ≥ 4 (P0-2 close-out)

**배경**: `events.jsonl` 은 gitignore 런타임 데이터라 "skill 실행 → 4 source 생성 → live-file smoke ≥ 4" 접근은 clean checkout/CI 에서 파일 부재로 깨진다. 그래서 (a) 게이트 자동 활성 + (b) 자립형 smoke 로 분리.

- **게이트 자동 활성** (`skills/{session-start,doc-sync,backlog-update}/scripts/run_*.py`): `--memory-index-dir` / `--memory-query-tokens` flag 부재 시에도 workspace 표준 `ai-workflow/memory/active/memory_index` dir 이 존재하면 retrieval 자동 활성 (flag 는 override 유지, dir 부재 시 zero-risk skip → 기존 caller 정합).
- **default query token**: session-start `session,handoff,workflow` / doc-sync `doc,sync,workflow` / backlog-update `backlog,task,workflow` — 공통 anchor `workflow` 로 seed cue 에 hit → hit_rate 유지.
- **신규 자립형 smoke** `tests/check_telemetry_source_diversity.py` (5 case, 5/5 PASS): temp workspace 4-source fixture → `by_source` ≥ `AC2_MIN_SOURCE_DIVERSITY(4)` + hit_rate ≥ `AC2_MIN_HIT_RATE(0.9)` sanity + under-diversity(3 source) 검출 + 4 canonical source schema round-trip. live-file 의존 없이 CI durable.
- **live events.jsonl**: dispatcher + session-start + doc-sync + backlog-update = 4 source, hit_rate 1.0 (dashboard Panel 8 반영).
- **SKILL.md 3종** memory_index 섹션 갱신 (opt-in → 자동 활성 override 설명).

### 2.2 CHANGELOG.md auto-gen lockdown (P1-1 close-out)

`tools/release_pipeline.py`:

- **`RELEASE_RE_BARE` 신규**: conventional-commit 접두사(`type(scope): `) 직후 선행 `vX.Y.Z` 인식. 기존 `RELEASE_RE` (괄호형 `(vX.Y.Z)`) 는 최근 관례인 맨몸 `... : vX.Y.Z — ...` 를 전부 놓쳐 v0.12~v0.15 대를 [Unreleased] 로 흡수하던 backfill bug 해소. prose 안 version (`v0.13.3 → v0.14.0`) 오분류는 접두사 앵커로 회피.
- **`_changelog_version_sort_key` 신규**: semver tuple 정렬 (unreleased sentinel 최상단). 기존 문자열 reverse 정렬의 두 자리 minor 오정렬 (`"0.11" < "0.7"`) 해소. (모듈 상단의 tag 전용 `_version_sort_key` 와 분리.)
- **`cmd_release` changelog pre-step**: drift-prevention 블록(doc-headers-update / maturity-matrix-sync 다음)에 `changelog-gen` auto-wire. whole-file 재생성이라 marker guard 불필요 (idempotent-by-regen). `--skip-changelog-gen` escape hatch + normalization loop / 릴리즈 subparser 등록.
- **backfill**: `CHANGELOG.md` v0.7.10 ~ v0.15.20 version section 정상 재생성.

### 2.3 roadmap stale 정리 (P1-2 / P1-3)

`core/workflow_kit_roadmap.md`:

- §8 항목 4 (automated-repro-scaffold stable 승격) / 5 (git-conflict-resolver alpha→beta) 는 이미 v0.11.24 4th batch 에서 stable 승격 완료 (`check_automated_repro_scaffold_v0_11_24.py` 5/5 PASS, maturity_matrix `stage: stable`). stale 텍스트를 완료 표기로 정정.
- 누적 skill 통계 라인(§1.1)에 v0.11.24 12 skill 전량 stable 후속 완료 주석 추가.

## 3. 검증

| smoke | 결과 |
|---|---|
| `check_telemetry_source_diversity.py` (신규) | 5/5 PASS |
| `check_telemetry_cross_v0_15_6.py` | 4/4 PASS |
| `check_memory_index_telemetry.py` | 6/6 PASS |
| `check_release_pipeline_changelog_gen.py` | 6/6 PASS |
| `check_session_start` / `check_doc_sync` / `check_backlog_update` | 3/3 PASS |
| `check_drift_prevention_v0_11_23.py` | 6/6 PASS |
| `check_sample_version_cross_v0_15_11.py` | 4/4 PASS (drift 해소) |
| `check_automated_repro_scaffold_v0_11_24.py` | 5/5 PASS |

- **mypy**: `release_pipeline.py` 신규 error 0 (baseline 유지, tool 은 strict-clean 대상 아님), `workflow_kit/` 무변경.
- breaking change: ❌.

## 4. 산출물

- 신규 (2): `tests/check_telemetry_source_diversity.py` + `releases/Beta-v0.15.21.md`.
- 수정 (핵심): `tools/release_pipeline.py` (RELEASE_RE_BARE + sort key + changelog pre-step + skip flag) + 3 skill `run_*.py` + 3 skill `SKILL.md` + `core/workflow_kit_roadmap.md` + `core/maturity_matrix.json`.
- housekeeping: pyproject 0.15.21 + `__init__.py` fallback v0.15.21-beta + sample 24 file tool_version v0.15.21-beta + README header + dashboard regen + CHANGELOG regen.
