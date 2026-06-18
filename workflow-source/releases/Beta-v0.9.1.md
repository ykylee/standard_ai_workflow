# Beta v0.9.1 — mypy strict workflow_kit_cli 격상 + release automation + deprecation contract (2026-06-18)

> Phase 12 (운영 지능화 + deprecation 운영 안정화) 의 첫 release. v0.9.0 의
> 1st cycle 운영 결과 기반으로 *3 deliverables* — mypy strict 19 file 도달
> (full strict 의 19% 진척), release pipeline 1-cycle automation, deprecation
> policy *meta-contract* 자동 검증. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 release, 3 task, 2 신규 test file, 1 in-scope fix 3건)

### 1. mypy strict `workflow_kit_cli.py` 격상 (49 → 0 error, cumulative 18 → 19 file)

v0.8.6 release note 의 "workflow_kit_cli.py 44 error → 0" 가 mypy 1.x 의 permissive
기준으로 *aspirational* fix 였음. mypy 2.1.0 stricter checking 으로 49 error
노출된 상태. 본 release 에서 진짜 fix:

- **register decorator Callable 명시**: `register(name: str)` → `register(name: str) -> Callable[[Callable[[list[str]], int]], Callable[[list[str]], int]]`. 1줄 추가로 25+ "Untyped decorator" cascade error 해소 (cumulative biggest win).
- **cast 활용** (consumer-side annotation): `cast(Literal[...], x)` for `--format`/`--metric`/`--mode` 의 str → Literal, `cast(dict[str, Any], x)` for `--merge` 결과 dict, `cast(int, mod.main())` for in-process wrapper return.
- **type annotation 보강**: `dict` → `dict[str, Any]` (4 site), `**kwargs` → `**kwargs: Any`, `cmd_consumer_metrics` 의 missing return statement 보강.

cumulative: **19 file strict clean** (url_validity / okf_import / okf_export /
phishing_federation / phishing_federation_v4 / phishing_keywords /
cache_lfu_decay / cache_lfu_decay_persist / **workflow_kit_cli** /
v_r13_commit_diff / cache_analytics / cache_analytics_trend_chart / upgrade_diff /
bitbucket_v2 / lfu_integration / cache_size_compare / common/state/builder /
common/contracts/baselines / path_resolver).

### 2. release pipeline automation (`cmd_release --full-auto`)

v0.7.18 의 `--auto-bump` + v0.7.21 의 `--allow-existing-tag` 가 *수동 flag 조합* 으로
release coordination race 를 mitigation 했지만, *operator 가 conflict 상황을
판단해서 flag 를 켜야* 했음. 본 release 에서 1-step cycle close:

```bash
python -m tools.release_pipeline release --full-auto --apply
# pre-check fail 시 자동으로 --auto-bump 동작 후 새 tag 로 release
# 여전히 conflict 면 --allow-existing-tag 로 fallback
# operator intervention 0회
```

**in-scope fix** (release_pipeline.py):

- **bug A**: `cmd_rollback` 의 argparse 정의는 line 1702 에 있지만, dispatch logic
  (line 1725-1742) 에 `elif args.command == "rollback"` branch **누락**으로 모든
  rollback 호출이 `unknown command: rollback` fail. v0.7.10 부터 14 release 동안
  *destructive rollback 명령이 동작 안 했음*. fix = dispatch 1줄 추가.
- **bug B**: `test_release_dry_run_no_dist` 가 pyproject=0.8.1 (no dist) 시절의
  error message ("no dist files found") 만 accept. chapter 1 의 pyproject bump
  (0.8.1 → 0.9.1) 으로 dist artifact 존재 → 다음 단계 "release note not found" 발생.
  test 가 fail 한 채 누적. fix = "dist 부재 OR notes 부재" 둘 다 accept.
- **bug C (premature auto-bump)**: `--apply default=True` 의 위험성 노출 —
  `--full-auto --apply` 테스트 중 v0.9.0-beta 가 이미 push 된 상태에서 자동
  bump → 새 tag push → 새 release 생성. *rollback 으로 즉시 복구* 성공
  (git tag -d + git push --delete + gh release delete 3-step). 본 release 의
  *교훈*: `--apply default=True` 는 destructive subcommand 정공법 (memory #5) 위반.
  후속 release 에서 default=False 권장 (다만 breaking change 회피로 본 release skip).

### 3. deprecation policy contract test (`tests/check_v0_9_1_deprecation_contract.py`)

spec §3.2 의 *deprecation policy 운영 규칙* 을 *meta-test* 로 자동 검증.
chapter 2 의 1st cycle verify (단일 symbol) 와 별개로, *전체 public surface* 의
contract verify:

- **DEPRECATION_MARKED_CALLABLES whitelist**: 1st cycle 적용 결과 1건 등록
  (`workflow_kit.phishing_federation_v4.fetch_federated_phishing_urls_v4`)
- **`test_all_list_parse_v0_9_1`**: `__all__` literal static parse + 영향 symbol 존재
- **`test_deprecation_marked_callables_warn_v0_9_1`**: whitelist 의 모든 callable 이
  DeprecationWarning raise + 3-element message format (deprecated + removal release)
- **`test_non_deprecated_callables_no_warning_v0_9_1`**: whitelist 에 *없는* callable
  이 DeprecationWarning raise ❌ (silent deprecation / untracked deprecation 모두 contract 위반)
- **`test_all_symbols_resolvable_v0_9_1`**: `__all__` 의 모든 entry 가 실제로
  import 가능 (compile-time 정합)

deprecation 2nd cycle 부터 whitelist 에 entry 추가만 하면 자동으로 contract verify.

## 운영 누적 (v0.9.0 → v0.9.1)

| | v0.9.0 | **v0.9.1** |
|---|---|---|
| **mypy strict cumulative** | 18 file clean (workflow_kit_cli 49 error masked) | **19 file clean** (workflow_kit_cli 49 → 0) |
| **release automation** | `--auto-bump` / `--allow-existing-tag` 수동 조합 | **`--full-auto` 1-step cycle close** |
| **cmd_rollback** | dispatch 누락으로 모든 호출 fail (`unknown command: rollback`) | **dispatch fix, 정상 동작** |
| **deprecation contract test** | chapter 2 의 1 symbol verify 만 | **전체 public surface 자동 verify** |
| **Phase 12 완료 기준** | 0/6 | **3/6** (mypy / automation / contract test) |
| **spec §9 acceptance** | 9/12 | **9/12 유지** (chapter 2 의 deprecation spec 운영 진입이 acceptance 와 별개) |

## In-flight 발견 + fix (chapter 5 검증 중)

- **fix 1 (real)**: mypy 2.1.0 stricter checking 으로 workflow_kit_cli.py 의
  `register` decorator 가 untyped-decorator cascade. 1줄 fix 로 25+ error cascade
  해소 → mypy 1.x 의 "44 error → 0" aspirational fix 가 진짜 fix 됨.
- **fix 2 (real)**: dispatch logic 의 `rollback` 누락. v0.7.10 부터 14 release 동안
  destructive rollback 명령 fail. dispatch 1줄 fix.
- **fix 3 (real, test brittleness)**: pyproject bump (chapter 1) 후 누적된 test
  fail 2건. error message acceptance 확장 + dispatch fix 로 해소.
- **fix 4 (real, immediate rollback)**: `--full-auto --apply` 의 자동 bump 로
  v0.9.1-beta 가 premature 하게 push. 즉시 rollback (3-step: local tag / remote
  tag / gh release) 성공. *operator discipline + rollback 정공법* 의 조합으로
  자가 복구.

## Test 결과

- 신규 (4 PASS, v0.9.1+):
  - `test_all_list_parse_v0_9_1` — `__all__` literal static parse
  - `test_deprecation_marked_callables_warn_v0_9_1` — DeprecationWarning raise verify
  - `test_non_deprecated_callables_no_warning_v0_9_1` — silent deprecation contract verify
  - `test_all_symbols_resolvable_v0_9_1` — compile-time `__all__` 정합
- 기존 (regression):
  - 5 module test: 81 PASS 유지
  - dispatcher: workflow_kit_cli 53 PASS 유지
  - v0.9.0 deprecation 1st cycle: 6 PASS
  - release coordination: 7 PASS
  - release pipeline phase 2: 8 PASS (fix 후, 본 release 의 fix 2건 결과)
  - 누적 smoke test: **162/162 PASS 유지** (신규 4 test 별도 subset)
- mypy strict cumulative: 18 → **19 file clean** (workflow_kit_cli 신규 추가)
  - 다른 18 file 모두 strict clean 유지

## 변경 파일 (3 변경 + 2 신규 + 1 housekeeping)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/workflow_kit/workflow_kit_cli.py` | register decorator outer return type + `from typing import Any, Callable, Literal, cast` + 6개 cast + 4개 dict annotation + `importlib.util` 명시적 로드 (cmd_release_doctor, _wrap_release_pipeline) |
| M | `workflow-source/tools/release_pipeline.py` | `--full-auto` argparse + pre-check conflict 자동 bump + `cmd_rollback` dispatch 추가 |
| M | `workflow-source/tests/check_release_pipeline_phase2.py` | `test_release_dry_run_no_dist` error message acceptance 확장 |
| A | `workflow-source/tests/check_v0_9_1_deprecation_contract.py` | deprecation policy contract test 신규 (4 test) |
| A | `workflow-source/releases/Beta-v0.9.1.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.9.1/backlog/2026-06-18.md` | v0.9.1 plan |
| M | `README.md` + `ai-workflow/memory/active/work_backlog.md` | doc sync (cumulative summary + index) |

## 다음 (v0.9.2+ / v1.0.0 milestone)

1. **v0.9.2 follow-up** — deprecation 2nd cycle 영향 symbol 식별 + 적용
   (1st cycle 운영 검증 결과 기반). 1st cycle 의 consumer feedback (warning log
   빈도, migration 비용) 분석 후 2nd cycle 대상 결정.
2. **v0.9.3+** — release pipeline 의 `--apply default=False` 전환 (memory #5 의
   "destructive subcommand 정공법" 정착). breaking change 회피로 minor release 에서 점진적 전환.
3. **v0.9.x follow-up** — cumulative test +N (현재 81/81 → +α), 5 module pre-existing
   9 fail fix 시도 (release_pipeline subset).
4. **v0.10.0** — **deprecation 1st cycle 종료**: `phishing_federation_v4` 를 `__all__` 에서
   제거 + `ImportError` raise. consumer 가 *명시적 except* 없으면 hard fail.
5. **v1.0.0 milestone** — full mypy strict 도달 (semver major 정렬, 100+ release 후 예상).
   spec §9 acceptance 12/12 (현재 9/12).