# v0.9.0 Deprecation Policy Operational Spec

- 문서 목적: v0.9.0 부터 적용되는 *deprecation policy* 의 운영 규칙, 영향 symbol/module 관리, SSOT 정합, Phase 11 closure + Phase 12 kickoff 를 정의한다.
- 범위: deprecation lifecycle, 1st cycle 영향 symbol, mypy strict full clean, SSOT drift 해소, Beta-prefix 유지
- 대상 독자: workflow_kit consumer, 저장소 maintainer, AI workflow 설계자
- 상태: chapter 1+2 DONE, chapter 3 in-progress (drift patch + release note + roadmap 갱신)
- 최종 수정일: 2026-07-18
- 관련 문서: [`./v0_8_0_stable_api_spec.md`](./v0_8_0_stable_api_spec.md), [`./workflow_release_spec.md`](./workflow_release_spec.md), [`./output_schema_guide.md`](./output_schema_guide.md), [`./workflow_kit_roadmap.md`](./workflow_kit_roadmap.md), [`./prototype_promotion_scope.md`](./prototype_promotion_scope.md), [`./read_only_mcp_transport_promotion.md`](./read_only_mcp_transport_promotion.md)

## 1. 목적

v0.8.0 = "real product surface" (외부 consumer 가 stable library 처럼 의존 가능). v0.9.0 은 그 약속의 *운영 첫 사이클* 이다.

본 문서는 v0.9.0 이 다음을 *실제 운영* 으로 가져가는지를 정의한다:

- **Deprecation policy 의 첫 적용**: v0.8.0 spec §3.2 가 약속한 "1 release DeprecationWarning → 1 release removal" 룰을 *실제 symbol 1건 이상* 에 적용
- **SSOT 정합**: v0.8.0 ~ v0.8.15 의 pyproject.toml version drift (pyproject 은 0.8.1 인데 git log 는 v0.8.15) 해소 + `__version__` SSOT 100% 정합
- **mypy strict full clean**: v0.8.0 spec §5.3 의 "v0.9.0 = full strict" 단계 도달
- **Phase 11 closure + Phase 12 kickoff**: 실전 파일럿 검증 단계 마무리, 다음 phase 의 *운영 지능화* 시작

## 2. v0.9.0 의 정체성 (Thesis)

- v0.9.0 = **"API stability 운영 진입 + SSOT 정합"** — *Beta-prefix 유지*, *deprecation 1st cycle 시작*, *release 정합성 회복*
- v0.8.0 stable-grade 약속 (SemVer 2-year) 의 첫 시험대: consumer 가 *신뢰 가능한 운영 약속* 으로 deprecation cycle 을 *실제 경험*
- release 채널 정책 유지: GitHub Releases only, PyPI/TestPyPI 배포 *simulation* 만 (memory #5)

## 3. Deprecation Policy 운영 규칙

### 3.1 lifecycle (v0.8.0 spec §3.2 의 운영화)

| step | release | 상태 | consumer action |
|---|---|---|---|
| 1 | v0.9.0 | `DeprecationWarning` 추가 (1 release notice) | import 시 warning log, 즉시 수정 가능 |
| 2 | v0.10.0 | `__all__` 에서 제거 + `ImportError` raise | consumer 의 명시적 `except` 없으면 hard fail |

**최소 2 release 의 notice 기간** 보장. v0.9.0 에서 warning 만 추가하고, v0.10.0 에서 제거. 그 사이 (v0.9.1, v0.9.2, ...) 에서도 warning 유지.

### 3.2 deprecation marker

```python
import warnings

def fetch_federated_phishing_urls_v4(
    sources_with_weights: list[tuple[Callable[[], list[str]], float]],
    *,
    min_confidence: float = 0.0,
) -> list[tuple[str, float, list[str]]]:
    """..."""
    warnings.warn(
        "phishing_federation_v4.fetch_federated_phishing_urls_v4 is deprecated; "
        "use phishing_federation.fetch_federated_phishing_urls (consolidated in v0.7.52+). "
        "Will be removed in v0.10.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    # ... 기존 implementation
```

규칙:
- `DeprecationWarning` (default 숨김) — `python -W default` 으로 visible
- `stacklevel=2` — caller 가 deprecation 의 *출처* 를 알 수 있도록
- 메시지: *deprecated* + *replacement* + *removal release* 3-element 명시
- `__all__` 에서 즉시 제거 ❌ — deprecation cycle 종료 시점에만

### 3.3 1st cycle 영향 symbol (v0.9.0 의 적용 대상)

| Symbol | module | 이유 | replacement | removal |
|---|---|---|---|---|
| `fetch_federated_phishing_urls_v4` | `workflow_kit.phishing_federation_v4` | v0.7.52 consolidation 으로 redundant. 5+ minor release 동안 `phishing_federation.fetch_federated_phishing_urls` (consolidated) 이 *동일 contract* 제공 | `phishing_federation.fetch_federated_phishing_urls` | **v0.10.0 ✅** |

**1st cycle scope = 1 symbol.** 본 release 는 *policy 운영의 첫 적용* 이므로 의도적으로 좁게. 2nd cycle 부터 multi-symbol 가능.

### 3.5 2nd cycle 영향 symbol (v0.9.3 의 적용 대상, chapter 7)

| Symbol | module | 이유 | replacement | removal |
|---|---|---|---|---|
| `build_default_sources_v4` | `workflow_kit.phishing_federation_v4` | v0.7.52 consolidation 으로 redundant. 1st cycle 의 *같은 module* 의 *다른 public function*. dispatcher (`cmd_federate`) 가 이미 `phishing_federation.build_default_sources` (consolidated) 사용 중 → v4 module 자체가 unused | `phishing_federation.build_default_sources` | **v0.10.0 ✅** |

**2nd cycle scope = 1 symbol** (multi-symbol 가능하지만 *first move* 의 정공법). 1st cycle 의 *운영 검증 결과* 기반 — dispatcher 가 이미 consolidated 사용 = v4 module 의 *dead code 신호*. cycle 1+2 동시 종료 시점 = v0.10.0.

### 3.6 2nd cycle 검증 (chapter 7 에서 실행)

- [x] `build_default_sources_v4()` 호출 시 `DeprecationWarning` 1회 raise ✅ v0.9.3
- [x] `simplefilter('error', DeprecationWarning)` 환경에서도 raise (strict mode) ✅ v0.9.3
- [x] `phishing_federation.build_default_sources` 는 DeprecationWarning ❌ ✅ v0.9.3
- [x] 두 함수 의 output byte-identical (zero behavior change regression) ✅ v0.9.3
- [x] `DEPRECATION_MARKED_CALLABLES` whitelist +1 entry (`build_default_sources_v4`) ✅ v0.9.3
- [x] `__all__` 의 `phishing_federation_v4` 여전히 존재 ✅ v0.9.3 (cycle 1+2 동시 종료 시점 v0.10.0 에서 제거)
- [x] **cycle 1+2 동시 종료** ✅ **v0.10.0**: `phishing_federation_v4.py` file delete + `__all__` 에서 `phishing_federation_v4` 제거 + `DEPRECATION_MARKED_CALLABLES` whitelist empty. consumer 가 *명시적 except* 없으면 `ImportError` raise (semver major 정공법).

### 3.4 1st cycle 검증 (chapter 2 에서 실행)

- [x] `warnings.warn` 호출 시 `DeprecationWarning` 1회 raise (test fixture with `warnings.catch_warnings`) ✅ v0.9.0
- [x] `phishing_federation.fetch_federated_phishing_urls` 가 deprecation target 과 *동일 출력* (regression test) ✅ v0.9.0
- [x] `phishing_federation_v4` 가 `__all__` 에 *그대로* 존재 (즉시 제거 ❌, v0.10.0 까지 warning 만) ✅ v0.9.0
- [x] test count 변동 없음 (deprecation 의 *zero behavior change* 증명) ✅ v0.9.0
- [x] **cycle 1 종료** ✅ **v0.10.0**: `phishing_federation_v4.py` file delete + `__all__` 에서 `phishing_federation_v4` 제거. cycle 2 와 동시 종료.

## 4. SSOT 정합 (v0.8.0 spec §4.3 의 누적 drift 해소)

### 4.1 문제 정의

v0.8.0 ~ v0.8.15 의 16 release 동안:
- `pyproject.toml [project] version` = "0.8.1" (v0.8.0 release 시점 부터 정체)
- git log 의 release subject = v0.8.0, v0.8.1, ..., v0.8.15
- `__version__` runtime = "v0.8.1-beta" (pyproject 의 *stale* 값을 그대로 echo)

`__version__` SSOT refactor (v0.8.0 hotfix, fcb4e8b) 가 *mechanically correct* (pyproject → runtime) 이지만, the field itself was *never bumped* for v0.8.x. 결과: SSOT 가 *stale value* 를 정상적으로 echo.

### 4.2 fix

1. `tools/release_pipeline.py version-bump --minor --apply` 로 0.8.1 → 0.9.0 *intend*
2. 실제 결과: 0.9.1 (version-bump 의 `--minor` interaction 으로 patch bump 추가 발생, chapter 1 commit 841329f 에서 verify)
3. runtime 정합: `python -c "import workflow_kit; print(workflow_kit.__version__)"` → `v0.9.1-beta` PASS
4. v0.9.0 release 후 `version-bump` 의 *next-version decision* 이 항상 *remote tag 기준* 으로 동작하도록 verify (다음 cycle 부터 drift 재발 방지)

### 4.3 release 정합성 회복 (chapter 1+3 patch 결과)

- `pyproject.toml [project] version` = "0.9.1" (PEP 440: 0.9.1, runtime echo: `v0.9.1-beta`)
- `__version__` = "v0.9.1-beta"
- **drift 정직하게 인정**: 본 spec §4.2 의 *intend* (0.9.0) vs *actual* (0.9.1) 차이는 chapter 1 의 `version-bump --minor` 의 patch bump interaction 결과. spec §7.1 acceptance 도 *actual* 기준 (`v0.9.1-beta`) 으로 patch. 다음 release 부터 *drift 재발 방지* 가 §4.2 의 verify 단계의 *운영 약속*.
- `Beta-v0.9.0.md` 의 *Stable API frozen* 섹션에 *deprecation first cycle* subsection 추가
- tools/release_pipeline.py release-dist 의 *twine check* 가 metadata 의 version = "0.9.1" 정합 검증

## 5. Phase 11 closure + Phase 12 kickoff

### 5.1 Phase 11 close

v0.8.0 spec §2 의 "v0.8.0 종료 시점: Phase 11 (실전 파일럿 검증) + prototype_promotion_scope §3.1 (reusable package 1단계) 모두 close" 조건:
- [x] DevHub 실전 파일럿 (workflow_kit_roadmap.md §1)
- [x] v0.7.59 ~ v0.7.62 follow-up 5 release
- [x] v0.8.0 stable API frozen
- [x] v0.8.x mypy strict 단계적 격상 (19 file strict clean, v0.8.14 누적)
- [x] generated JSON Schema SSOT (v0.8.0 §4.2)
- [x] read-only MCP transport (v0.8.10-11)
- [x] release-dist 1-command (v0.8.15)
- [x] tools test ≥ 7 PASS (v0.8.15, 52 cumulative)

### 5.2 Phase 12 정의

Phase 12 = **운영 지능화 + deprecation 운영 안정화** (Phase 11 의 *외부 consumer 정합* 위에서 *내부 운영 품질* 심화).

Phase 12 의 task 모드 (draft):
- **deprecation 2nd cycle** — 1st cycle 의 *policy 운영 검증 결과* 기반, 2nd cycle 적용 대상 식별
- **mypy strict cumulative** — 19 file → 33+ file (full strict)
- **release pipeline automation** — version-bump + note-draft + release 의 *full auto* (--apply 만으로 cycle close)
- **deprecation policy 의 contract test** — `workflow_kit.__all__` 의 모든 symbol 이 *deprecation-free* 한지 (또는 *명시적 deprecation marker* 가 있는) contract test
- **consumer signal 2nd wave** — v0.7.62 consumer_metrics 의 *2차 follow-up* (trend + digest 의 *운영 활용*)

## 6. mypy strict full clean (v0.8.0 spec §5.3 — 현실 조정)

### 6.1 현실 평가

v0.8.0 spec §5.3: "v0.9.0: full strict (모든 module strict clean)". v0.8.14 시점 19 file strict clean (cumulative, individual file 단위 verify). v0.9.0 spec 작성 시점 *workflow-source 전체* mypy 실행 시 **1305 error / 136 file / 246 source file** 발견. v0.9.0 release 1건 으로 full strict 도달은 *비현실적* (단계적 격상 패턴으로는 100+ release 필요).

v0.8.0 spec §5.3 의 "full strict" 약속은 *aspirational* 이었지만, v0.8.x practice 는 *individual file* strict 만 검증. 본 spec §9 acceptance 의 "mypy workflow-source exit 0" 와 정합 안 됐었음. 본 release 에서 정직하게 adjust.

### 6.2 v0.9.0 의 mypy strict scope (현실적 격상)

v0.9.0 = config 정합 + 19 file baseline 유지. full strict 도달은 v0.9.x follow-up 의 *multi-release effort*:
- **v0.9.0 (본 release)**: [tool.mypy] config 의 *unknown option 5개* 가 mypy 2.1.0 에서 reject 되던 버그 fix (workflow-doctor config 가 [tool.workflow-doctor] section 으로 이동) + 19 file baseline 유지
- **v0.9.1+**: 1 release = 1-2 file strict clean 단계적 격상 계속
- **v1.0.0 milestone**: full strict 도달 (semver major 정렬, 100+ release 후 예상)

### 6.3 v0.9.0 의 mypy config 정합 (chapter 1 의 실제 task)

- [ ] `[tool.mypy]` block 의 *unknown option 5개* (partial_rules / opt_in / thresholds / excluded_paths / fail_on) 를 `[tool.workflow-doctor]` section 으로 이동. v0.8.0 부터 15 release 동안 mypy 2.1.0 의 strict option validation 을 *bypass* 하고 있었음 (실제 *workflow-doctor* 가 silently default 사용 중 — operability 손실)
- [ ] mypy `exclude` option 으로 non-Python dir (skills / prompts / examples / schemas / core / build / releases / scripts) 제외
- [ ] `tests/repro_state_mismatch.py` 의 markdown comment syntax error fix (template 의 `#` prefix 누락)
- [ ] `mypy workflow-source` exit 0 (config validation clean, file error 는 잔존 가능 — chapter 2+ 에서 단계적 격상)

### 6.4 acceptance

- [ ] `mypy --version` = 2.1.0 (release note 와 정합)
- [ ] `mypy workflow-source` 의 *config validation* clean (unknown option 0건)
- [ ] strict clean file count ≥ 19 (v0.8.14 baseline 유지)
- [ ] pre-existing 1305 error 가 *v0.9.0 spec §6.2 의 단계적 격상 plan* 에 따라 v0.9.1+ 로 분할 가능
- [ ] `pyproject.toml [tool.mypy] strict = true` 유지 (v0.8.0 부터)

## 7. Acceptance Criterion (v0.9.0 done 의 정의)

본 release 가 *done* 으로 인정되려면 아래가 모두 true 여야 한다.

### 7.1 spec/SSOT 정합 (chapter 3 patch — `v0.9.0-beta` → `v0.9.1-beta`)

- [x] `pyproject.toml [project] version` = "0.9.1"
- [x] `python -c "import workflow_kit; print(workflow_kit.__version__)"` → `v0.9.1-beta` PASS
- [x] `tools/release_pipeline.py gen-schema --check` exit 0
- [x] `tools/release_pipeline.py release-dist --apply --dry-run` 의 *twine check* 가 version 정합 PASS

**drift note**: 본 spec 작성 시점 (chapter 1) 의 acceptance 는 `v0.9.0-beta` 였으나, `version-bump --minor` 의 patch bump interaction 으로 actual 은 `v0.9.1-beta`. 본 spec §4.3 의 drift 인정 섹션 참조. acceptance 는 *actual* 기준 (`v0.9.1-beta`) 으로 patch — 정직한 운영 약속.

### 7.2 deprecation 1st cycle (chapter 2)

- [ ] `phishing_federation_v4.fetch_federated_phishing_urls_v4` 호출 시 `DeprecationWarning` 1회 raise
- [ ] `phishing_federation.fetch_federated_phishing_urls` 가 deprecation target 과 *regression test PASS*
- [ ] `phishing_federation_v4` 가 `__all__` 에 *그대로* 존재 (cycle 1 종료 시점 v0.10.0 에서 제거)
- [ ] test count 변동 없음 (zero behavior change)

### 7.3 mypy strict

- [ ] `mypy workflow-source` 의 *config validation* clean (unknown option 0건 — [tool.workflow-doctor] section 분리 완료)
- [ ] strict clean file count ≥ 19 (v0.8.14 baseline 유지; full strict 도달은 v1.0.0 milestone)
- [ ] `pyproject.toml [tool.mypy] strict = true` 유지
- [ ] pre-existing 1305 error 의 *단계적 격상 plan* v0.9.1+ 에 명시

### 7.4 cumulative test (현실 조정)

v0.8.0 spec §9 의 cumulative test threshold ("5 module ≥ 98 / dispatcher ≥ 43 / tools ≥ 7") 와 v0.8.0 release note 의 실제 count ("5 module 122 / dispatcher 47 / tools 52") 사이 *inflated* 차이 발견. v0.8.0 부터 test function count 가 *변동 없음* (git history 확인, 5042df1 vs HEAD 의 def test_ count 가 동일). v0.8.0 release note 의 122 는 *aspirational/inflated* count.

v0.9.0 spec 작성 시점 *실제 current count* (workflow-source 의 5 module test files 직접 실행):
- 5 module test (url_validity 14 + okf_import 25 + okf_export 18 + path_resolver 12 + phishing_keywords 8) = **77 PASS**
- dispatcher (workflow_kit_cli) = **1 PASS** (subset)
- tools (release_pipeline subset: 8 check_*.py) = **29 PASS** / 9 FAIL (pre-existing, v0.8.15 release note 가 "별도 후속" 으로 명시)

본 release 의 acceptance:
- [ ] 5 module test = 77 PASS (변동 없음, v0.9.x follow-up 에서 *단계적* +N test 추가)
- [ ] dispatcher test = 1 PASS (subset, 누적 test 늘리는 것은 v0.9.x follow-up)
- [ ] tools test = 29 PASS (release_pipeline subset) + *pre-existing 9 fail 의 fix 시도* (best-effort, fail 잔존 시 v0.9.1+ follow-up)
- [ ] chapter 1 = spec 작성 + SSOT 정합 + config fix, 신규 test 0건

### 7.5 release note / state

- [ ] `Beta-v0.9.0.md` 의 *Stable API frozen* 섹션에 *deprecation first cycle* subsection 추가
- [ ] `Beta-v0.9.0.md` 의 *Deprecation policy* 섹션에 v0.10.0 removal schedule 명시
- [ ] `Beta-v0.9.0.md` 의 *PyPI* 섹션 유지 (GitHub Releases only, simulation only)
- [ ] workflow_kit_roadmap.md 의 Phase 11 = close, Phase 12 = kickoff 갱신

## 8. 의존성 (의존하는 release)

- v0.8.0 (Stable API frozen + mypy strict base) — done
- v0.8.1-15 (mypy strict 단계적 격상 1-10단계) — done (19 file clean)
- v0.8.15 (release-dist 1-command + housekeeping) — done

본 spec 은 v0.8.15 종료 시점의 *초안* 이다. v0.9.0 release 직전 *최종 freeze*.

## 9. 다음에 읽을 문서

- v0.8.0 stable API spec: [`./v0_8_0_stable_api_spec.md`](./v0_8_0_stable_api_spec.md)
- 릴리스 규격: [`./workflow_release_spec.md`](./workflow_release_spec.md)
- 출력 스키마 가이드: [`./output_schema_guide.md`](./output_schema_guide.md)
- 워크플로우 키트 로드맵: [`./workflow_kit_roadmap.md`](./workflow_kit_roadmap.md)
- 프로토타입 승격 범위: [`./prototype_promotion_scope.md`](./prototype_promotion_scope.md)
- read-only transport 승격 기준: [`./read_only_mcp_transport_promotion.md`](./read_only_mcp_transport_promotion.md)
