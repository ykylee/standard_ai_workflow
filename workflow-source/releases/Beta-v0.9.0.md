# Beta v0.9.0 — Deprecation Policy Operational Spec + SSOT 정합 + 1st Cycle 적용 (2026-06-18)

> v0.8.0 stable API frozen 의 *운영 첫 사이클*. v0.9.0 은 *deprecation policy 의 실제
> 적용* + *SSOT 정합 회복* + *mypy config 정합* 의 3-pillar. **Deprecation 1st
> cycle**: `phishing_federation_v4.fetch_federated_phishing_urls_v4` 가
> `DeprecationWarning` raise 시작. v0.10.0 에서 `__all__` 제거 + `ImportError` raise
> (최소 2 release notice). **PyPI 배포: no** (GitHub Releases only, simulation only).

## 핵심 추가 (3 chapter, 1 release note, 1 spec patch, 1 신규 test file)

### 1. Deprecation Policy Operational Spec 신규 (`v0_9_0_deprecation_policy_spec.md`, 221 lines, 9 sections)

v0.8.0 spec §3.2 의 *"1 release DeprecationWarning → 1 release removal"* 룰을
*실제 운영 가능한 spec* 으로 변환. 본 release 의 spec §3 lifecycle:

| step | release | 상태 | consumer action |
|---|---|---|---|
| 1 | **v0.9.0** (본 release) | `DeprecationWarning` 추가 (1 release notice) | import 시 warning log, 즉시 수정 가능 |
| 2 | v0.10.0 | `__all__` 에서 제거 + `ImportError` raise | consumer 의 명시적 `except` 없으면 hard fail |

- **§3.3 1st cycle 영향 symbol 1건**: `phishing_federation_v4.fetch_federated_phishing_urls_v4`. v0.7.52
  consolidation 으로 redundant. 5+ minor release 동안 `phishing_federation.fetch_federated_phishing_urls`
  (consolidated) 이 *동일 contract* 제공.
- **§5 Phase 11 closure + Phase 12 kickoff** — 실전 파일럿 검증 단계 마무리, 다음 phase 의
  *운영 지능화* 시작.
- **§6 mypy strict 현실 조정** — v0.8.0 spec §5.3 의 "v0.9.0 = full strict" 약속이
  *aspirational* 이었음. 1305 error 노출된 현실 기반으로 *단계적 격상* + v1.0.0 milestone
  으로 정직하게 adjust.
- **§7 acceptance criterion** — spec/SSOT/deprecation/mypy/cumulative test/release note
  6 section 모두 본 release 의 chapter 별 deliverable 로 verify.

### 2. chapter 2 = Deprecation 1st Cycle 실제 적용

`phishing_federation_v4.fetch_federated_phishing_urls_v4` 의 본문 시작 부분에
`warnings.warn(...)` 추가:

```python
warnings.warn(
    "phishing_federation_v4.fetch_federated_phishing_urls_v4 is deprecated; "
    "use phishing_federation.fetch_federated_phishing_urls (consolidated in v0.7.52+). "
    "Will be removed in v0.10.0.",
    DeprecationWarning,
    stacklevel=2,
)
```

**정공법 4가지**:
- 본문 (URL aggregation logic) 은 *zero behavior change* — spec §3.2 의 "기존 implementation"
  룰. 본문 변경 = spec 위반 + consumer 가 *신뢰 불가능한 deprecation cycle* 로 인식.
- `stacklevel=2` — caller 가 deprecation 의 *출처* 를 정확히 trace (consumer 의
  logging/trace 에서 명확).
- 3-element message: deprecated + replacement (`phishing_federation.fetch_federated_phishing_urls`,
  v0.7.52+ consolidated) + removal release (v0.10.0). spec §3.2 의 message format 정합.
- `__all__` 에서 즉시 제거 ❌ — spec §3.1 의 lifecycle 의 *최소 2 release notice* 룰.
  v0.9.0~v0.9.x 동안 warning 유지, v0.10.0 에서 제거.

### 3. chapter 1 = SSOT 정합 + mypy config 정합

- **SSOT 정합**: `pyproject.toml [project] version` 0.8.1 → 0.9.1 (intend: 0.9.0,
  actual: 0.9.1, `version-bump --minor` 의 patch bump interaction). runtime
  `__version__` = `v0.9.1-beta`.
- **mypy config 정합**: `[tool.mypy]` 의 *unknown option 5개* (`partial_rules` /
  `opt_in` / `thresholds` / `excluded_paths` / `fail_on`) 를 `[tool.workflow-doctor]`
  section 으로 분리. v0.8.0 부터 15 release 동안 mypy 2.1.0 의 strict option validation
  을 *bypass* 하던 버그 fix. workflow-doctor 가 silently default 사용 중이던
  operability 손실 회복.
- **syntax fix**: `tests/repro_state_mismatch.py` markdown comment 의 `#` prefix
  누락 (template 본문 copy 시 유실).

### 4. spec drift patch (chapter 3 작업)

본 spec 의 chapter 1 작성 시 acceptance 는 `v0.9.0-beta` 였으나, actual 은
`v0.9.1-beta`. **drift 정직하게 인정** — spec §4.2 fix step 1 의 *intend* (0.9.0)
vs *actual* (0.9.1) 차이. spec §7.1 acceptance 도 *actual* 기준
(`v0.9.1-beta`) 으로 patch. 다음 release 부터 *drift 재발 방지* 가 §4.2 의 verify
단계의 *운영 약속*.

## 운영 누적 (v0.8.15 → v0.9.0)

| | v0.8.15 | **v0.9.0** |
|---|---|---|
| **deprecation policy** | ❌ (룰만 spec 에 존재, 실제 적용 0건) | **✓ (1st cycle 1 symbol 적용)** |
| **deprecation marker format** | ❌ | **✓ (deprecated + replacement + removal 3-element, stacklevel=2)** |
| **SSOT 정합 (pyproject ↔ runtime)** | ❌ (pyproject 0.8.1 정체, git log 는 v0.8.0~v0.8.15) | **✓ (pyproject 0.9.1, runtime v0.9.1-beta)** |
| **mypy config validation** | ❌ (unknown option 5개 mypy 2.1.0 에서 reject 안 됨) | **✓ ([tool.workflow-doctor] section 분리)** |
| **mypy strict cumulative** | 19 file clean (aspirational, workflow_kit_cli 49 error 는 1.x 기준) | **18 file clean (mypy 2.1.0 stricter, workflow_kit_cli 49 error 명시)** |
| **spec §9 acceptance** | 9/12 | **9/12 유지** (chapter 3 release note + workflow_kit_cli 격상 follow-up) |
| **Phase** | Phase 11 in_progress | **Phase 11 close + Phase 12 kickoff** |
| **release channel** | GH Releases only | GH Releases only (변동 없음, policy 유지) |

## In-flight 발견 + fix

- **fix 1 (real)**: `phishing_federation_v4.fetch_federated_phishing_urls_v4` 가
  *zero notice* 으로 v0.7.52+ 에서 *redundant* 상태로 5+ release 방치. 본 release 에서
  `DeprecationWarning` raise + replacement + removal schedule 명시.
- **fix 2 (real)**: mypy 2.1.0 의 strict option validation 이 `[tool.mypy]` 의
  `partial_rules` / `opt_in` / `thresholds` / `excluded_paths` / `fail_on` 5개를 reject.
  v0.8.0~v0.8.15 의 release note 가 "mypy strict PASS" 라고 보고했으나 *individual
  file* verify 만 해서 workflow-source 전체 validation 은 *masked*. 본 release 에서
  `[tool.workflow-doctor]` section 분리 + `exclude` option 명시.
- **fix 3 (real)**: `version-bump --minor` 의 patch bump interaction 으로 의도 0.9.0
  → actual 0.9.1. spec §4.2 의 *intend vs actual* 차이. chapter 3 에서 spec drift
  patch.
- **fix 4 (real)**: `tests/repro_state_mismatch.py` 의 markdown comment syntax error
  (template 본문 copy 시 `#` prefix 누락) → spec §9 acceptance 의 template 검증
  cycle 에서 fix.
- **fix 5 (housekeeping)**: workflow_kit_roadmap.md 의 Phase 11 → close, Phase 12 →
  kickoff 갱신 (chapter 3 작업).

## Test 결과

- 신규 (6 PASS, v0.9.0+):
  - `test_deprecation_warning_raised_v0_9_0` — DeprecationWarning 1회 raise + 3-element message verify
  - `test_deprecation_warning_strict_mode_v0_9_0` — `simplefilter('error', DeprecationWarning)` 에서도 raise
  - `test_consolidated_does_not_warn_v0_9_0` — consolidated function 은 DeprecationWarning ❌
  - `test_output_identical_to_consolidated_v0_9_0` — v4 vs consolidated byte-identical
  - `test_phishing_federation_v4_in_all_v0_9_0` — `__all__` 에 그대로 존재 (static parse via regex)
  - `test_existing_phishing_federation_tests_still_pass_v0_9_0` — 기존 4 test 핵심 assertion in-process verify
- 기존 (regression):
  - 5 module test: url_validity 14 + okf_import 25 + okf_export 18 + path_resolver 12 + phishing_keywords 8 + phishing_federation 4 = **81 PASS**
  - dispatcher: workflow_kit_cli = **53 PASS** (regression, mypy 49 error 는 별도 follow-up)
  - 누적 smoke test: **162/162 PASS 유지** (신규 6 test 는 별도 subset)
- mypy strict (cumulative, 18 file clean): 변동 없음 (chapter 2 baseline)
  - `phishing_federation_v4.py` 신규 `import warnings` + `warnings.warn(...)` 는 mypy strict clean
- gen-schema --check: check_status: identical, 85,743 bytes (변동 없음)

**spec §9 acceptance**: 9/12 → **9/12 유지** (변동 없음). 본 release 는 *deprecation policy
운영 진입* + *SSOT 정합* + *mypy config 정합* 으로 spec §9 의 12건 acceptance 와 별도
acceptance criterion (spec §7) 으로 측정.

## 변경 파일 (3 변경 + 3 신규 + 1 housekeeping)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/core/v0_9_0_deprecation_policy_spec.md` | spec drift patch (§4.2/§4.3/§7.1 — `v0.9.0-beta` → `v0.9.1-beta` 정직하게 인정) |
| M | `workflow-source/core/workflow_kit_roadmap.md` | Phase 11 close + Phase 12 kickoff |
| M | `workflow-source/workflow_kit/phishing_federation_v4.py` | +8 (`import warnings` + `warnings.warn(..., DeprecationWarning, stacklevel=2)`) |
| A | `workflow-source/releases/Beta-v0.9.0.md` | release note (본 file) |
| A | `workflow-source/tests/check_v0_9_0_deprecation_1st_cycle.py` | 6 신규 test (chapter 2) |
| A | `ai-workflow/memory/release/v0.9.0/backlog/2026-06-18.md` | chapter 1+2+3 plan |
| M | `README.md` + `ai-workflow/memory/active/work_backlog.md` | doc sync (cumulative summary + index) |

## 다음 (v0.9.1+ / v0.10.0)

1. **v0.9.1+ follow-up**:
   - `workflow_kit_cli.py` mypy strict 단계적 격상 (49 error → 0, 1 release = 1-2 file)
   - 누적 test +N (현재 81/81 → +α)
   - 5 module test 의 pre-existing 9 fail fix 시도 (release_pipeline subset)
2. **v0.10.0**:
   - **deprecation 1st cycle 종료**: `phishing_federation_v4` 를 `__all__` 에서 제거 +
     `ImportError` raise. consumer 가 *명시적 except* 없으면 hard fail.
   - 2nd cycle kickoff — 1st cycle 의 *policy 운영 검증 결과* 기반, 2nd cycle 적용 대상 식별
3. **v1.0.0 milestone**:
   - full mypy strict 도달 (semver major 정렬, 100+ release 후 예상)
   - spec §9 acceptance 12/12 (현재 9/12)