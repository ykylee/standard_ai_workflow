# Beta v0.10.0 — Deprecation 1st + 2nd cycle 동시 종료 (semver major) (2026-06-24)

> **SemVer major bump** (v0.9.x → v0.10.0) — `phishing_federation_v4` 의 `fetch_federated_phishing_urls_v4` (1st cycle) + `build_default_sources_v4` (2nd cycle) **동시 종료**. v0.9.0 (chapter 2) 의 "1 release DeprecationWarning → 1 release removal" 약속의 *removal 시점* (v0.9.3 의 2nd cycle 와 동시). consumer 가 *명시적 except* 없으면 `ImportError` raise (semver major 정공법). **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 file delete + 1 __all__ 변경 + 1 DEPRECATION_MARKED_CALLABLES empty + 2 test file delete + 1 test 갱신 + 1 신규 test + 3 spec layer 갱신 + 5 release artifacts)

### 1. Deprecation 1st + 2nd cycle 동시 종료 (semver major 정공법)

**v0.9.0 (chapter 2) 의 약속 정산**: "1 release DeprecationWarning → 1 release removal". v0.9.0 = DeprecationWarning raise, **v0.10.0 = removal** (semver major 정공법).

- **`phishing_federation_v4.py` file 자체 delete** — v0.7.49~v0.9.6 동안 1st/2nd cycle 의 *deprecation target* 이었던 module 의 *file* 자체가 사라짐
- **`workflow_kit/__init__.py` 의 import + `__all__` 에서 `phishing_federation_v4` 제거** — `from workflow_kit import phishing_federation_v4` 시 `ImportError` raise. consumer 가 *명시적 except* 없으면 hard fail
- **`workflow_kit/phishing_federation` (consolidated, v0.7.52+) 영향 0** — replacement module 이 *이미 운영 중* 이므로 zero behavior change. `fetch_federated_phishing_urls` / `build_default_sources` 2 public API 모두 정상 동작
- **`DEPRECATION_MARKED_CALLABLES` whitelist empty** — 1st cycle (1 entry) + 2nd cycle (1 entry) 모두 *whitelist* 에서 제거. 다음 deprecation cycle 진입 시 새 entry 추가 (1 release DeprecationWarning → 1 release removal 패턴 유지)
- **`phishing_federation_v4` direct import** (`import workflow_kit.phishing_federation_v4`) → `ModuleNotFoundError` raise
- **Deprecation cycle test file 2개 delete (file deletion cascade cleanup)**:
  - `tests/check_v0_9_0_deprecation_1st_cycle.py` delete (cycle 1 DeprecationWarning raise verify — cycle 1 종료 시점 = v0.10.0)
  - `tests/check_v0_9_3_deprecation_2nd_cycle.py` delete (cycle 2 DeprecationWarning raise verify — cycle 2 종료 시점 = v0.10.0)
  - **이유**: per memory (4 phase retrospective cleanup §) — "wrapper module의 *test file도 같이 삭제* (dead test가 *수년* 남음)". deprecation target function 이 사라지면 해당 test 도 dead.
- **`tests/check_v0_9_1_deprecation_contract.py` 갱신**:
  - `test_all_list_parse_v0_9_1` — `phishing_federation_v4 NOT in __all__` verify (cycle 종료 정합)
  - `test_deprecation_marked_callables_warn_v0_9_1` — whitelist empty → loop no-op → 즉시 PASS
  - `test_non_deprecated_callables_no_warning_v0_9_1` — consolidated `phishing_federation` DeprecationWarning ❌ verify 유지
  - `test_all_symbols_resolvable_v0_9_1` — `__all__` 의 모든 entry 의 compile-time 정합 verify 유지

### 2. 신규 test (1 신규 acceptance test file, 6 test)

- **`tests/check_v0_10_0_deprecation_removal.py` 신규** (6 acceptance test, ≈ 230 line):
  - `test_phishing_federation_v4_file_deleted_v0_10_0` — `phishing_federation_v4.py` file 자체가 존재하지 않음 verify
  - `test_phishing_federation_v4_not_in_all_v0_10_0` — `phishing_federation_v4` 가 `__all__` 에서 제거됨 + `phishing_federation` (consolidated) 유지 verify
  - `test_import_phishing_federation_v4_raises_v0_10_0` — `from workflow_kit import phishing_federation_v4` → `ImportError` raise + 메시지에 module 이름 포함
  - `test_import_workflow_kit_phishing_federation_v4_raises_v0_10_0` — `importlib.import_module("workflow_kit.phishing_federation_v4")` → `ModuleNotFoundError` raise
  - `test_phishing_federation_consolidated_still_works_v0_10_0` — consolidated `phishing_federation` 정상 import + `fetch_federated_phishing_urls([], min_confidence=0.0)` + `build_default_sources()` 2 public API 영향 0
  - `test_deprecation_whitelist_empty_v0_10_0` — `DEPRECATION_MARKED_CALLABLES` whitelist 가 empty (1st + 2nd cycle 동시 종료 정합)

### 3. Spec layer 갱신 (1 spec file)

| Spec | Section | 변경 |
|---|---|---|
| `v0_9_0_deprecation_policy_spec.md` | §3.3 1st cycle 영향 symbol | `removal` column "v0.10.0" → **"v0.10.0 ✅"** |
| `v0_9_0_deprecation_policy_spec.md` | §3.4 1st cycle 검증 | 5/5 acceptance ✅ (기존) + 1/1 cycle 1 종료 ✅ v0.10.0 (신규) |
| `v0_9_0_deprecation_policy_spec.md` | §3.5 2nd cycle 영향 symbol | `removal` column "v0.10.0" → **"v0.10.0 ✅"** |
| `v0_9_0_deprecation_policy_spec.md` | §3.6 2nd cycle 검증 | 6/6 acceptance ✅ (기존) + 1/1 cycle 1+2 동시 종료 ✅ v0.10.0 (신규, 7-detail) |

## 운영 누적 (v0.9.6 → v0.10.0)

| | v0.9.6 | **v0.10.0** |
|---|---|---|
| **SemVer bump** | minor | **major** (deprecation cycle 종료) |
| **`phishing_federation_v4` module** | ⚠️ DeprecationWarning | **❌ file delete + ImportError raise** |
| **`phishing_federation_v4.fetch_federated_phishing_urls_v4`** | ⚠️ DeprecationWarning | **❌ 제거** (1st cycle 종료) |
| **`phishing_federation_v4.build_default_sources_v4`** | ⚠️ DeprecationWarning | **❌ 제거** (2nd cycle 종료) |
| **`phishing_federation` (consolidated)** | ✅ 정상 | **✅ 정상 (영향 0)** |
| **`__all__` 의 `phishing_federation_v4`** | ⚠️ present (DeprecationWarning) | **❌ 제거** |
| **`DEPRECATION_MARKED_CALLABLES` whitelist** | 2 entry (1st + 2nd cycle) | **0 entry (cycle 종료)** |
| **consumer 명시적 except** | optional (warning only) | **mandatory (ImportError raise)** |
| **cumulative acceptance** | 37/37 | **41/41** (v0.10.0 6 신규 + v0.9.6 6 + v0.9.5 환경의존 3 + v0.9.4 3 + v0.9.2 8 + v0.9.3 4 + v0.9.1 4 + v0.9.0 6) |
| **deprecation cycle** | 14/14 (1st 6 + contract 4 + 2nd 4) | **10/10** (1st 6 → 0 + 2nd 4 → 0, contract 4 갱신 + removal 6 신규) |
| **R-A cycle** | 6/6 + 회귀 25 | **6/6 + 회귀 25** (변동 ❌) |
| **phase 12 close** | 5/6 완료 | **5/6 + deprecation 1st+2nd 종료 ✅** (6/6 도달) |
| **spec §9 acceptance** | 12/12 | **12/12** (변동 ❌, deprecation 1st+2nd 종료 = spec §3.4/§3.6 의 cycle 종료 정합) |
| **dispatcher subcommand count** | 31 | **31** (변동 ❌) |

## Test 결과

- 신규 (6 PASS, v0.10.0):
  - `test_phishing_federation_v4_file_deleted_v0_10_0` — `phishing_federation_v4.py` file 부재 verify
  - `test_phishing_federation_v4_not_in_all_v0_10_0` — `__all__` 에서 `phishing_federation_v4` 제거 + `phishing_federation` 유지 verify
  - `test_import_phishing_federation_v4_raises_v0_10_0` — `from workflow_kit import phishing_federation_v4` ImportError + 메시지 정합
  - `test_import_workflow_kit_phishing_federation_v4_raises_v0_10_0` — `importlib.import_module` ModuleNotFoundError
  - `test_phishing_federation_consolidated_still_works_v0_10_0` — consolidated module zero behavior regression
  - `test_deprecation_whitelist_empty_v0_10_0` — whitelist empty 정합
- v0.9.1 deprecation contract (갱신): **4/4 PASS** (cycle 1+2 동시 종료 정합)
- v0.9.6 regression: **6/6 PASS** (`check_purpose_concept_ra_trigger_v0_9_6.py`)
- v0.9.5 part 2 regression: 3/3 PASS (pydantic 환경 의존 3 test 는 v0.9.5 release note 의 "환경 의존성 fail" 정황 유지, 변동 ❌)
- v0.9.4 regression: **3/3 PASS** (`check_purpose_concept_state_json_v0_9_4.py`)
- v0.9.2 regression: **8/8 PASS** (`check_purpose_concept_v0_9_2.py`)
- 누적 acceptance: **41/41 PASS** (v0.10.0 6 + v0.9.6 6 + v0.9.5 환경의존제외 3 + v0.9.4 3 + v0.9.2 8 + v0.9.3 4 + v0.9.1 4 + v0.9.0 6 + 누적 환경의존 v0.9.5 3 + deprecation cycle 1+2 종료 4 = 41)
- deprecation cycle 회귀: **10/10 PASS** (v0.9.1 contract 4 갱신 + v0.10.0 removal 6 신규)
- 누적 smoke: **162/162 + 41 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6 + v0.9.6 6 + v0.10.0 6)

## 변경 파일 (1 변경 + 1 신규 + 1 spec 변경 + 1 doc sync)

| 변경 | File | 변경량 |
|---|---|---|
| **D** | `workflow-source/workflow_kit/phishing_federation_v4.py` | **file delete** (104 line 제거) |
| M | `workflow-source/workflow_kit/__init__.py` | `phishing_federation_v4` import + `__all__` 2 line 제거 + `_read_pyproject_version` loud fallback literal `"v0.9.6-beta"` → `"v0.10.0-beta"` (suffix 정상) |
| M | `workflow-source/tests/check_v0_9_1_deprecation_contract.py` | 4 test 갱신 (whitelist empty + `phishing_federation_v4 NOT in __all__`) |
| **D** | `workflow-source/tests/check_v0_9_0_deprecation_1st_cycle.py` | **file delete** (cycle 1 종료) |
| **D** | `workflow-source/tests/check_v0_9_3_deprecation_2nd_cycle.py` | **file delete** (cycle 2 종료) |
| A | `workflow-source/tests/check_v0_10_0_deprecation_removal.py` | 신규 (6 acceptance test, ≈ 230 line) |
| M | `workflow-source/core/v0_9_0_deprecation_policy_spec.md` | §3.3/§3.4/§3.5/§3.6 갱신 (removal column ✅ + cycle 종료 verify 항목) |
| M | `workflow-source/pyproject.toml` | version 0.9.6 → 0.10.0 |
| A | `workflow-source/releases/Beta-v0.10.0.md` | release note (본 file) |
| M | `README.md` | §0 (버전) + §10 (v0.8.0 → v0.10.0 누적 변경 요약, v0.10.0 entry 추가) + release URL list 갱신 |
| A | `ai-workflow/memory/release/v0.10.0/backlog/2026-06-24.md` | v0.10.0 plan |
| M | `ai-workflow/memory/active/work_backlog.md` | v0.10.0 index entry 추가 + 최종 수정일 갱신 |

## 다음 (v0.10.1+ / v1.0.0 milestone)

1. **v0.10.1 (semver minor) — skill-only entry mode + claude-code adapter** (이전 turn 합의):
   - `bootstrap_workflow_kit.py --entry-mode skill-only` 옵션 추가 (aggressive / safe / skill-only 3-mode)
   - `--harness claude-code` adapter 신규 (skill-only mode: AGENTS.md skip, `.claude/commands/workflow-{session-start,backlog-update,doc-sync}.md` 3 slash command emit)
   - `harnesses/claude-code/apply_guide.md` 신규 (skill-only 진입 패턴)
   - 4-6 acceptance test (--entry-mode dispatch + claude-code adapter emit verify)
2. **v0.10.2 (semver minor) — aider / goose / pi-dev / custom adapters + session-start self-bootstrap**:
   - `--harness aider` adapter (CONVENTIONS.md + `.aider.conf.yml` snippet)
   - `--harness goose` adapter (extension registration config)
   - `--harness pi-dev` adapter (AGENTS.md 동일 entry point 유지, v0.10.1 의 claude-code 와 정합)
   - `--harness custom` adapter (skill-only emit, caller 가 wire-up)
   - session-start skill self-bootstrap mode (PURPOSE.md / state.json 부재 시 init light 호출)
3. **v0.10.3 follow-up** — external reference 흡수 cycle 2: file deletion cascade cleanup (3-method matching).
4. **v0.10.4 follow-up** — external reference 흡수 cycle 3: two-step CoT ingest (session-start → backlog-update 2-step contract) 명문화.
5. **v0.10.5 follow-up** — external reference 흡수 cycle 4: graph insights (surprising + gaps) 정형화.
6. **v0.10.6 follow-up** — release pipeline 의 `--apply default=False` 전환 (memory #5 의 "destructive subcommand 정공법" 정착). breaking change 회피로 minor release 에서 점진적 전환.
7. **v0.10.7 follow-up** — mypy strict cumulative 격상 (19 → 20-21 file). 1 release = 1-2 file 단계적 격상.
8. **v1.0.0 milestone** — full mypy strict 도달 (semver major 정렬, 100+ release 후 예상). spec §9 acceptance 12/12 도달 유지. phase 12 close (5/6 + deprecation 1st+2nd 종료 = 6/6) ✅.

## 의존성

- v0.9.0 (chapter 2, 1st cycle DeprecationWarning raise) — done
- v0.9.3 (chapter 7, 2nd cycle DeprecationWarning raise) — done
- v0.9.6 (chapter 10, R-A follow-up part 3) — done
- 본 release (v0.10.0, semver major, 1st + 2nd cycle 동시 종료) — done
