# Beta v0.9.3 — deprecation 2nd cycle (build_default_sources_v4) (2026-06-19)

> Phase 12 의 *deprecation 운영 안정화* 두 번째 release. 1st cycle (v0.9.0) 의 *운영 검증 결과* 기반, 같은 module (`phishing_federation_v4`) 의 *다른 public function* (`build_default_sources_v4`) 에 2nd cycle 적용. dispatcher (`cmd_federate`) 가 이미 consolidated 사용 = v4 module 자체가 *dead code 신호*. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 task, 1 in-scope update, 1 신규 test + 1 contract test update)

### 1. deprecation 2nd cycle (`build_default_sources_v4`)

**1st cycle (v0.9.0) 운영 검증 결과**:

- dispatcher (`workflow_kit_cli.cmd_federate`) 가 이미 `phishing_federation.build_default_sources` (consolidated) 사용 중 (line 255-257) → v4 module 자체가 unused
- 1st cycle 의 `fetch_federated_phishing_urls_v4` warning 로그 빈도 = 0 (v0.9.0 + v0.9.1 + v0.9.2 = 같은 날 release, consumer feedback data 0)
- 동일 module 의 *다른 public function* 1개 식별 = `build_default_sources_v4`

**2nd cycle 적용**:

- **`phishing_federation_v4.build_default_sources_v4` 본문** DeprecationWarning 1-block 추가 (1st cycle 정공법 그대로: `stacklevel=2`, 3-element message `deprecated + replacement + v0.10.0 removal`)
- **`phishing_federation_v4` 의 `__all__` 변경 ❌** — 1st cycle 정책 유지 (v0.10.0 까지 그대로)
- **`DEPRECATION_MARKED_CALLABLES` whitelist +1** (contract test 의 `dict[str, tuple[str, tuple, dict]]` format 확장: 1st/2nd cycle signature 차이 흡수)

**운영 검증 트리거**:

- 1st cycle 의 *code-level verification* (dispatcher 가 이미 consolidated 사용) = 충분
- 별도 *runtime 운영 데이터* (consumer warning log 빈도, migration 비용) 는 1st/2nd cycle 의 0일 release 사이클상 *불충분*. 후속 cycle 에서 *월 단위 운영 metric* 으로 보강 가능 (consumer signal 2nd wave 의 follow-up)

## 운영 누적 (v0.9.2 → v0.9.3)

| | v0.9.2 | **v0.9.3** |
|---|---|---|
| **deprecation policy 적용 symbol** | 1 (1st cycle) | **2** (1st + 2nd cycle) |
| **DEPRECATION_MARKED_CALLABLES whitelist** | 1 entry | **2 entries** (1st cycle `fetch_federated_phishing_urls_v4` + 2nd cycle `build_default_sources_v4`) |
| **contract test format** | `dict[str, str]` | **`dict[str, tuple[str, tuple, dict]]`** (signature 차이 흡수) |
| **2nd cycle scope** | 미정 | **1 symbol** (multi-symbol 가능, first move 정공법) |
| **cumulative smoke test** | 162/162 + 18 별도 subset | **162/162 + 22 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4) |
| **spec §9 acceptance** | 9/12 | **9/12 유지** (deprecation 2nd cycle ✅ — spec §9 의 "deprecation 2nd cycle" 항목 충족, 후속 2/12 = `--apply default=False` / consumer signal 2nd wave) |

## In-scope 발견 (chapter 7 검증 중)

- **fix 1 (real, test assumption)**: 2nd cycle test 의 `len(result) == 2` 가정 오류. v4 의 `build_default_sources_v4` default 호출 시 `phishtank_api_key=None` → PhishTank skip, OpenPhish 1 source 만. test 수정 `len(result) == 1` 로 정합 (zero behavior change verify 동등성 활용).
- **fix 2 (real, contract test format 확장)**: 1st cycle 의 `fetch_federated_phishing_urls_v4` signature `(sources_with_weights, *, min_confidence=0.0)` 와 2nd cycle 의 `build_default_sources_v4` signature `(phishtank_api_key=None, *, include_phishtank=True, include_openphish=True)` 가 다름. `_safe_call_with_warning_capture(func, ([],), {})` hard-coded 호출 → whitelist format 을 `(replacement, args, kwargs)` tuple 로 확장. contract test 의 *meta-test* 성격 강화.
- **fix 3 (real, dispatcher 의 dead code)**: `cmd_federate` 가 `phishing_federation.build_default_sources` (consolidated) 만 import. `phishing_federation_v4` module 자체가 dispatcher 에서 *unused*. 2nd cycle 의 *strong 근거* = 운영 metric 보강 없이도 *code-level dead code* 신호로 충분.

## Test 결과

- 신규 (4 PASS, v0.9.3+):
  - `test_deprecation_warning_raised_v0_9_3` — `build_default_sources_v4()` 호출 시 DeprecationWarning 1회 raise
  - `test_deprecation_warning_strict_mode_v0_9_3` — `simplefilter('error', DeprecationWarning)` 환경에서도 raise
  - `test_consolidated_does_not_warn_v0_9_3` — `phishing_federation.build_default_sources` DeprecationWarning ❌
  - `test_output_equivalent_to_consolidated_v0_9_3` — 두 함수 output 동등 (length + weight, callable identity 제외)
- 누적 smoke test: **162/162 PASS 유지** (신규 4 test 별도 subset)
- contract test: **4/4 PASS** (whitelist +1 + tuple format 확장)
- 1st cycle regression: **6/6 PASS** (deprecation marker 그대로, `phishing_federation_v4.fetch_federated_phishing_urls_v4` 1회 raise 유지)

## 변경 파일 (3 변경 + 1 신규 + 1 doc sync)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/core/v0_9_0_deprecation_policy_spec.md` | §3.5 (2nd cycle 영향 symbol) + §3.6 (2nd cycle 검증) 추가 |
| M | `workflow-source/workflow_kit/phishing_federation_v4.py` | `build_default_sources_v4` 본문 DeprecationWarning 1-block 추가 |
| M | `workflow-source/tests/check_v0_9_1_deprecation_contract.py` | `DEPRECATION_MARKED_CALLABLES` whitelist +1 + tuple format 확장 + for loop unpack update |
| A | `workflow-source/tests/check_v0_9_3_deprecation_2nd_cycle.py` | 2nd cycle acceptance test 신규 (4 test) |
| A | `workflow-source/releases/Beta-v0.9.3.md` | release note (본 file) |
| M | `workflow-source/pyproject.toml` | version 0.9.2 → 0.9.3 |
| M | `README.md` + `ai-workflow/memory/active/work_backlog.md` | doc sync (cumulative summary + index) |
| A | `ai-workflow/memory/release/v0.9.3/backlog/2026-06-19.md` | v0.9.3 plan |

## 다음 (v0.9.4+ / v1.0.0 milestone)

1. **v0.9.4 follow-up** — release pipeline 의 `--apply default=False` 전환 (memory #5 의 "destructive subcommand 정공법" 정착). breaking change 회피로 minor release 에서 점진적 전환.
2. **v0.9.5 follow-up** — mypy strict cumulative 격상 (19 → 20-21 file). 1 release = 1-2 file 단계적 격상.
3. **v0.9.6 follow-up** — R-A Purpose Refresh follow-up (cycle 7 follow-up): `state.json.purpose_digest` + session-start context load + R-A trigger.
4. **v0.9.7 follow-up** — external reference 흡수 cycle 2: file deletion cascade cleanup (3-method matching).
5. **v0.9.8 follow-up** — external reference 흡수 cycle 3: two-step CoT ingest (session-start → backlog-update 2-step contract) 명문화.
6. **v0.9.9 follow-up** — external reference 흡수 cycle 4: graph insights (surprising + gaps) 정형화.
7. **v0.10.0** — **deprecation 1st + 2nd cycle 동시 종료**: `phishing_federation_v4` 를 `__all__` 에서 제거 + `ImportError` raise. consumer 가 *명시적 except* 없으면 hard fail. 2nd cycle 의 `build_default_sources_v4` 도 동시 제거.
8. **v1.0.0 milestone** — full mypy strict 도달 (semver major 정렬, 100+ release 후 예상). spec §9 acceptance 12/12 (현재 9/12 → 10/12 v0.9.3 후속 deprecation 2nd cycle 충족, 남은 2/12 = `--apply default=False` / consumer signal 2nd wave).
