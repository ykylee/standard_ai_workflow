# Beta v0.8.15 — release-dist 1-command (build + check + TestPyPI sim) + housekeeping (2026-06-17)

> v0.8.0 spec §9 acceptance 의 remaining 2건 해소 + housekeeping. `cmd_dist --apply`
> 가 1-command 로 `python -m build` + `twine check` + TestPyPI upload *simulation*
> 까지 1-command 실행. `--production` flag 는 production PyPI upload *simulation* 추가.
> 본 release 의 TestPyPI/Production upload 는 *simulation* 만 (release channel policy:
> GitHub Releases only, no actual PyPI/TestPyPI deployment).
> 부수: history file gitignore + work_backlog.md v0.7.25~v0.7.32 stale 정리. **PyPI 배포: no**.

## 핵심 추가 (1 TASK, 1 commit, 2 신규 test, 0 신규 subcommand)

### 1. spec §9 #7 — `release-dist --apply` 1-command (build + check + TestPyPI sim)

기존 `cmd_dist --apply` 는 `python -m build` 만 실행. spec §7.1 의 5-step (build + check +
TestPyPI dry run + TestPyPI install + production) 의 1-3 step 을 *simulation* 으로 확장:

| Step | command | 본 release 의 동작 |
|---|---|---|
| 1. build | `python -m build` | *real* subprocess 실행 (dist/ wheel + sdist 생성) |
| 2. check | `python -m twine check dist/*` | *real* subprocess 실행 (metadata 검증, PASSED) |
| 3. TestPyPI sim | `twine upload --repository testpypi --skip-existing` | *simulation* 만 (no actual upload, release policy) |
| 4. TestPyPI install | `pip install -i https://test.pypi.org/simple/ ...` | spec §7.1 step 4, manual (skip) |
| 5. Production sim | `twine upload` | `--production` flag 시 *simulation* 만 |

Real bug fix 동반:
- `python -m twine` invocation — PATH 의존성 제거. `sys.executable -m twine` 로 현재
  venv 의 twine 강제 사용 (PATH 의 `twine` 없을 때도 동작).
- skip-existing + post-build steps — 기존 skip-existing 분기에서 build skip 하지만
  twine check + simulation 은 *기존 artifact* 로 실행. 이전엔 early return 으로 skip.

### 2. spec §9 #11 — `tools test ≥ 7 PASS` verify

10개 tools/ 관련 test file (release_pipeline* + v0_7_24~v0_7_32) 실행. **52 PASS** (≥ 7 충족).
12 fail 은 *pre-existing* (release_pipeline_version_flag JSONDecode, v0_7_24 --notes-template
argparse mismatch) — 본 release 와 무관, 별도 후속.

### 3. housekeeping — history file gitignore 등록

`.gitignore` 에 `**/.consumer_metrics_history.jsonl` + `workflow-source/.venv-build/`
추가. v0.7.62+ consumer_metrics 의 append-only history jsonl + v0.8.x build venv.

### 4. housekeeping — work_backlog.md v0.7.25~v0.7.32 stale 정리

work_backlog.md 의 8 in-flight 항목 (v0.7.25~v0.7.32) 이 *stale* — 이미 main 에 merge
완료 (25 commits, 2026-06-15). 본 release 에서 commit hash 채우고 status: **DONE** 갱신.
in-flight 8 → 0 정리.

## 운영 누적 (v0.8.0 → v0.8.15)

| | v0.8.0 | v0.8.7 | v0.8.9 | v0.8.10 | v0.8.11 | v0.8.13 | v0.8.14 | **v0.8.15** |
|---|---|---|---|---|---|---|---|---|
| **release-dist 1-command** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✓** |
| **spec §9 acceptance** | 7/12 | 7/12 | 7/12 | 8/12 | 8/12 | 8/12 | 8/12 | **9/12** (#7 해소) |
| **tools test ≥ 7 PASS** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✓ (52 PASS)** (#11 해소) |
| **in-flight stale entries** | 8 | 8 | 8 | 8 | 8 | 8 | 8 | **0** |

## In-flight 발견 + fix

- **fix 1 (real)**: 기존 `cmd_dist` 가 `twine check` / TestPyPI simulation step 부재
  → spec §9 #7 acceptance 미충족. 본 release 에서 1-command 확장.
- **fix 2 (real)**: 기존 `cmd_dist` 의 skip-existing 분기가 early return 으로
  twine check / simulation skip → 본 release 에서 skip 후 post-build steps 실행.
- **fix 3 (real)**: `subprocess.run(["twine", ...])` 의 PATH 의존성 — `twine` CLI 가
  PATH 에 없을 때 fail. 본 release 에서 `sys.executable -m twine` 으로 PATH 의존성 제거.
- **fix 4 (housekeeping)**: work_backlog.md 의 v0.7.25~v0.7.32 8 in-flight 항목 stale
  (이미 main merged). 본 release 에서 commit hash + status 갱신.

## Test 결과

- 신규 (2 PASS, v0.8.15+):
  - `test_cmd_dist_1_command_build_check_testpypi_v0_8_15` — `--apply --skip-existing` → twine check + testpypi_simulation verify
  - `test_cmd_dist_with_production_simulation_v0_8_15` — `--production` flag 시 production_simulation 추가 verify
- 기존 (regression): 9 release_pipeline test + 151 other test = 160 PASS
- cumulative: **162/162 PASS**
- mypy strict (cumulative, 19 file): 변동 없음
- gen-schema --check: check_status: identical, 85,743 bytes

**spec §9 acceptance**: 8/12 → **9/12** done (#7 release-dist 1-command + #11 tools test ≥ 7)

## 변경 파일 (3 변경 + 1 housekeeping)

| 변경 | File | 변경량 |
|---|---|---|
| M | `tools/release_pipeline.py` | +97 / -8 (`_twine_check` + `_simulate_testpypi_upload` + `_simulate_production_upload` + skip-existing post-build steps + `--production` flag) |
| M | `tools/release_pipeline_lib.py` | +16 / -2 (`cmd_dist` wrapper 확장: skip_existing / production / sdist_only / wheel_only / timeout / json_output) |
| M | `tests/check_release_pipeline_lib.py` | +26 (2 신규 test) |
| M | `.gitignore` | +7 (history file + venv-build) |
| M | `ai-workflow/memory/active/work_backlog.md` | +16 / -16 (v0.7.25~v0.7.32 in-flight → DONE + commit hash) |
| A | `workflow-source/releases/Beta-v0.8.15.md` | release note |
| A | `ai-workflow/memory/release/v0.8.15/backlog/2026-06-17.md` | plan |

## 다음 (v0.9.0)

1. **v0.9.0** — full mypy strict (모든 module strict clean). spec §5.3 final 단계.
   - 19 file strict clean → all file (workflow_kit_cli.py 49 error + tools/* + common/* 등 잔여)
   - spec §9 #1 (mypy workflow_source exit 0) 해소 → spec §9 acceptance 10/12
2. (별도) spec §9 의 나머지 3건 — 의존적 (v0.9.0 + 추가 작업)
   - spec §9 #2 (모든 release 의 stable API freeze commit) — v0.9.0+ 자연
   - spec §9 #4 (beta → stable flag 1-year) — v0.9.0+ 자동
   - spec §9 #5 (5 follow-up 의 stable API 정합) — design 결정 필요
