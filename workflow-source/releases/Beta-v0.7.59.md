# Beta v0.7.59 — cmd_consumer_metrics in-process refactor (dispatcher 27 정합) (2026-06-17)

> v0.7.58 의 consumer-metrics tool 의 *dispatcher in-process* 정합 — v0.7.55+ 의
> release-doctor / v0.7.56+ 의 score-wiki-trend 와 동일 정공법으로 통일.
> **subprocess delegation → import_module** 1-step. dispatcher subcommand 27 단일 surface 유지.
> 5 module test 98 → **98 PASS** (변동 없음, in-process 자체는 test_count 변동 없음). 2 commit, 0 신규 file.

## 핵심 추가 (1 follow-up, 1 commit, 2 신규 test, 0 신규 tool)

### 1. cmd_consumer_metrics in-process refactor

v0.7.58 의 `cmd_consumer_metrics` 는 *subprocess delegation* (subprocess.run + sys.executable) 패턴
채택. 본 release 는 v0.7.55+ 의 release-doctor / v0.7.56+ 의 score-wiki-trend 와 동일
*in-process wrapper* 정공법으로 통일:

**정공법 4종 일치** (workflow_kit_cli.py:1053-1075):

1. `from pathlib import Path` 로 `workflow_source_dir` 산출
   (`kit_dir.parent` — `workflow_kit_cli.py` 가 있는 `workflow_kit/` 의 부모 = `workflow-source/`)
2. `sys.path.insert(0, str(workflow_source_dir))` (idempotent — `if ... not in sys.path`)
3. `importlib.import_module("tools.consumer_metrics")` — `tools/__init__.py` (v0.7.56+) 으로
   package import 가능
4. `sys.argv = ["consumer_metrics", *argv]` patch + `try/finally` 로 restore
   (argparse 가 `sys.argv[1:]` 를 읽으므로 dispatcher argv 를 그대로 forwarding)

**예외 처리 2종**:

- `except SystemExit` → `e.code if isinstance(e.code, int) else 2` (argparse 가 `--help` 등에서
  `sys.exit(0)` 호출 시 rc 로 변환)
- `except Exception` → `print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)` + rc=2

**제거** (subprocess delegation 정공법 잔재):

- `import subprocess as _sp` 라인
- `from pathlib import Path as _P` 중복 (이미 위에서 import)
- `metrics_path.exists()` 체크 (in-process 라 import 시점에 fail 이 더 명확)
- `_sp.run(...)` + `sys.stdout.write(proc.stdout)` 등 subprocess plumbing

**Days validation 단일 출처 정공법**:

v0.7.58 의 dispatcher 는 `--days` range (1-90) 을 dispatcher 측에서도 검증 후,
subprocess 도 검증. 본 release 는 **dispatcher 측 검증 제거**, `consumer_metrics.main()` 의
argparse 가 단일 출처. 결과: 1 line 의 validation logic 사라짐 (의도적 *defense in depth*
약화, *단일 출처* 가 더 안전).

## 운영 누적 (v0.7.52 → v0.7.59)

| | v0.7.52 | v0.7.53 | v0.7.54 | v0.7.55 | v0.7.56 | v0.7.57 | v0.7.58 | **v0.7.59** |
|---|---|---|---|---|---|---|---|---|
| **dispatcher** | 6 | 8 | 11 | 14 | 23 | 26 | 27 | **27** |
| **dispatcher test** | 6 | 9 | 13 | 20 | 33 | 38 | 41 | **43** |
| **5 module test** | 64 | 68 | 68 | 68 | 83 | 98 | 98 | **98** |
| **consumer_metrics test** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 6 | **6** |
| **in-process dispatcher** | ❌ | ❌ | ❌ | release-doctor | score-wiki-trend | score-wiki-trend | ❌ | **consumer-metrics** |

## In-flight 발견 + fix

- (없음) — 패턴 자체가 v0.7.55+ 에서 검증된 정공법, 신규 위험 없음

## Test 결과

- `check_workflow_kit_cli.py`: 41/41 → **43/43** PASS (+2 신규)
  - `test_consumer_metrics_in_process_v0_7_59` — dispatcher argv 가 tools.consumer_metrics 를
    in-process import 하고, sys.modules 에 모듈이 존재함을 증명 (subprocess fork 와 구분)
  - `test_consumer_metrics_argv_forwarded_v0_7_59` — dispatcher 의 --days=0/100 이
    consumer_metrics.main() 까지 도달하여 단일 출처에서 rc=2 반환 (defense in depth 제거 확인)
- `check_consumer_metrics.py`: 6/6 PASS (변동 없음)
- `check_cache_migration.py`: 5/5 PASS (변동 없음)
- `check_url_validity.py`: 14/14 PASS (변동 없음)
- `check_okf_import.py`: 25/25 PASS (변동 없음)
- `check_release_pipeline_lib.py`: 7/7 PASS (변동 없음)
- **cumulative dispatcher test**: 41 → **43 PASS** (+2, 5% 증가)
- **cumulative 5 module test**: 98 → **98 PASS** (변동 없음)
- **cumulative +1 tool test**: 6/6 PASS (변동 없음)

## 다음 (v0.7.60 / v0.8.0)

1. v0.7.60 E. 5 module audit 4차 (path_resolver / phishing_keywords 정합)
2. v0.7.60 C. dispatcher 28+ (cache-lru-decay / cache-lfu-decay-persist / cache-merge-csv)
3. v0.7.61 F. mkdocs `--strict` 진짜 활성화 (wiki mirror 또는 multirepo)
4. v0.7.62 B + D. consumer-metrics trend snapshot + weekly digest
5. v0.8.0 J. stable API freeze + mypy strict + PyPI + generated schema SSOT
   (workflow-source/core/v0_8_0_stable_api_spec.md)
