# Beta v1.0.0 — 준비 현황 (⚠️ **릴리스 보류 / 초안**) (2026-07-21)

> **상태: 릴리스하지 않았다.** 본 문서는 v1.0.0 진입을 위해 진행한 작업과 **잔여 과제**를
> 기록하는 초안이다. tag / GitHub Release / PyPI 배포 **모두 미실행**.
>
> `core/v1_0_0_entry_evaluation.md` 의 6/6 entry gate 는 PASS 이지만, 이후 실제 전량
> smoke 회귀 과정에서 **릴리스 도구와 메모리 계층의 구조적 결함**이 드러나 진입을 보류했다.
> 특히 (1) smoke 전량 실행이 저장소 히스토리를 재작성할 수 있었고, (2) 성능 측정 규칙이
> 사용자 작업 기억(`state.json`)을 반복 파괴하고 있었다. 둘 다 본 사이클에서 수정했다.
>
> 버전 suffix 체계는 기존 관례를 **유지**한다 (`tool_version = v1.0.0-beta`, 노트 파일명 `Beta-v*.md`).

## 0. 잔여 과제 (릴리스 보류 사유)

| # | 항목 | 상태 |
|---|---|---|
| 1 | 브랜치별 메모리 재설계 — session-start 자동 아카이브 wiring | ✅ 완료 (탐지+안내 기본, `--archive-stale-branches` 로 실이동) |
| 2 | `MEMORY_GOVERNANCE.md` / `active/README.md` 의 branch-scoped layout 반영 | ✅ 완료 |
| 3 | branch-scoped + 아카이브 전용 smoke 신규 | ✅ 완료 (`check_branch_scoped_memory.py` 8/8) |
| 4 | 기존 red smoke 잔여분 (문서 lint / 빌드 의존 / `ci_stale`) 분류·해소 | ⏳ 진행 중 (13건 회복, 잔여 ~19) |
| 5 | CHANGELOG 재생성 + dashboard snapshot + tag/release | ⏳ 미착수 |

### 잔여 red 성격별 (다음 세션 착수 지점)

| 성격 | 대상 | 메모 |
|---|---|---|
| **구조적** | `deprecation_cycle_v0_14_5` | `docs/PROJECT_PROFILE.md` 사용 시 `workflow_memory_dir()` 이 `memory/` 를 반환하나 실제 layout 은 `memory/active/`. `cache.py` 주석의 "v0.6.0.1 `/ "active"` fix 누락" 과 같은 뿌리. **44개 참조 영향** → 별도 판단 |
| **프로세스** | `wiki_source_rule` | wiki 가 `active/` 를 ingest source 로 참조(R9 위반). archive 에 해당 스냅샷이 없어 **freeze 선행** 필요 |
| **품질 게이트** | `smoke_trend_cross` case_5 | "전량 PASS(rate=1.0)" 요구. 잔여 red 를 모두 해소해야 통과하는 **올바른 목표 지표** — 억지로 맞추지 않는다 |
| **문서 lint** | `docs`, `source_without_runtime_layer`, `wiki_drift`, `wiki_trend` | `reverse-engineering/*.md` 메타데이터 누락 등 누적 부채 |
| **빌드 의존** | `release_pipeline_lib/phase2/phase3`, `v0_7_4_followup` | `python -m build` / doctor 실행 환경 필요 |
| **CI 상태 의존** | `mypy_ci_cross_verify`, `release_summary` | `ci_stale` — push 후 CI 결과가 있어야 판정 |
| **미조사** | `export_harness_package`, `existing_project_onboarding`, `drift_prevention_helpers`, `refresh_wiki_memory`, `release_status_auto_bump`, `run_all_checks` | traceback 이 잘려 원인 미확정 |

## 1. 릴리스 요약

- **v1.0.0 stable 진입**: entry gate 6영역 (dashboard 정합 / smoke / mypy strict / backward compat / public API / deprecation roadmap) **전부 PASS**. Break Point #1 (Panel 5 `items_total=11`) + #3 (venv mypy strict 117 file 0 error) close-out 완료. 잔여 Break Point #2 (TST-WF-01 historical smoke coverage) 는 **non-blocking 품질 항목**.
- **temp dir 누수 근절**: `/var/tmp` 211GB 회수 + CI per-check timeout + 누수 가드 7 case (`check_tempdir_leak_guard.py` 신규).
- **release_pipeline amend 가드** (신규): 무가드 `git add -A` + `--amend` 가 **미커밋 작업을 push 된 커밋에 흡수**하던 위험을 3중으로 차단.
- **기존 red smoke 2종 회복**: `check_v0_7_29_poststep_amend.py` (호출순서 취약성으로 StopIteration) + `check_v0_10_2_delivery_layer_extension.py` (harness 집합 고정) — 둘 다 **본 변경 이전부터 CI red** 였던 항목.
- breaking change: ❌.

## 2. deliverable

### 2.1 v1.0.0 entry gate 6/6 PASS

`core/v1_0_0_entry_evaluation.md` §0 / §1 / §8.1 정합화 완료.

| # | Gate | 결과 |
|---|---|---|
| 1 | Panel 1~8 dashboard 정합 | ✅ Panel 5 `items_total=11` 재정합 (Break Point #1 close-out) |
| 2 | 누적 smoke PASS | ✅ 24/24, 회귀 0 |
| 3 | mypy strict clean | ✅ venv mypy 2.1.0 직접 verify — **117 source files, 0 errors** (Break Point #3 close-out) |
| 4 | Backward compat | ✅ 100+ release 중 breaking 1건 (v0.15.0 `.bak` drop, 2-cycle deprecation 종결) |
| 5 | Public API stability | ✅ 25 `__all__` + 12 skill stable + 11 MCP stable, `BaseOutput` 100% |
| 6 | Deprecation roadmap | ✅ Panel 7 `stage=v0.15.0 complete`, ADR-007 accepted |

버전 스탬프 정합: `pyproject.toml` 1.0.0 + `workflow_kit/__init__.py` fallback + sample 24 file `tool_version` + README/docs 헤더.

### 2.2 temp dir 누수 근절 + 재발 방지 가드

`/var/tmp` 211GB 점유로 디스크 100% → tmpfs 경유 OOM 이 발생한 사고의 근본 대응.

- `.github/workflows/smoke.yml`: **per-check timeout** 도입 (`timeout --signal=TERM --kill-after=10s 120s`). timeout 부재 시 hang 한 check 하나가 job 전체를 무한 대기시키고, 강제 kill 시 `tempfile.TemporaryDirectory` 정리 코드가 돌지 않아 temp dir 이 누수된다. SIGTERM 을 먼저 보내 **정리 가능한 종료**를 보장.
- `scripts/export_harness_package.py`: temp dir 생성/정리 경로 정비.
- `tests/check_tempdir_leak_guard.py` **신규** (7 case): 누수 패턴 회귀 차단.
- `check_cache_lfu_decay_full.py` / `check_cache_size_compare_evict.py` / `check_scaffold_harness.py`: 누수 유발 패턴 제거.

### 2.3 release_pipeline `--amend` 안전 가드 (신규)

**배경**: `_run_post_step_sync_hash()` 의 Phase 2 가 무조건 `git add -A` → `git commit --amend --no-edit` 를 수행했다. 이 조합은 (a) **릴리스와 무관한 미커밋 작업까지 release commit 에 흡수**하고, (b) HEAD 가 이미 push 됐다면 **원격 history 를 재작성**한다. 실제로 본 릴리스 준비 중 사고가 발생해 백업 ref 로 복구한 이력이 있다.

`tools/release_pipeline.py`:

- **`_git_dirty_paths()` 신규**: `git status --porcelain` 의 변경 path 목록 (untracked 포함, rename 은 new path).
- **`_head_is_pushed()` 신규**: upstream (`@{u}`) 해석 후 `git merge-base --is-ancestor HEAD <upstream>` 으로 push 여부 판정. upstream 부재 시 `checked=False` (판정 불가 → 차단하지 않음).
- **Guard 1 — pre-flight clean tree** (`cmd_version_bump`): amend 가 실제로 도는 경우(`--skip-sync-hash` 미지정)에만 clean tree 를 강제하고, dirty 면 **write 이전에** `mode="aborted"` 로 중단 + `dirty_paths` 보고. 근본 원인을 정확히 차단하는 지점.
- **Guard 2 — pushed HEAD 거부**: amend 직전 판정. push 된 HEAD 면 `ok=False` + 사유 반환, amend 미실행.
- **Guard 3 — scoped add**: `git add -A` → `git add -- <dirty paths>` 로 전환하고 무엇이 흡수됐는지 `staged_paths` 로 결과에 기록. 변경 0 이면 amend 자체를 skip (빈 amend 방지).
- **escape hatch**: `--allow-dirty` / `--allow-pushed-amend` (둘 다 기본 off). `release_status.py` 등 `argparse.Namespace` 직접 구성 caller 는 `getattr` 기본값으로 **안전 측 (가드 활성)** 에 놓인다.

### 2.4 기존 red smoke 2종 회복

둘 다 **본 릴리스 변경 이전부터 CI red** 였던 항목이다.

- **`tests/check_v0_7_29_poststep_amend.py` 전면 재작성** (5 → 9 test): mock 을 *호출 순서* 기반 `side_effect` list 에서 ***명령 내용* 기반 dispatch** 로 전환. 기존 구조는 4-call 시퀀스를 가정했으나 v0.7.26 의 2-step `rev-parse` 도입으로 5번째 호출에서 `StopIteration` 이 나 red 였다. 신규 가드 3종 (dirty abort / pushed 거부 / scoped add) 테스트 추가.
- **`tests/check_v0_10_2_delivery_layer_extension.py`**: `SUPPORTED_HARNESSES` 를 정확히 10종으로 고정하던 assertion 이 이후 추가된 `grok-build` / `codewhale` 로 깨졌다. **"v0.10.2 당시 10종이 여전히 지원되는지"** 라는 회귀 의도만 남기고 (subset 검사 + 중복 검사) 추가에 관대하도록 정정.

### 2.5 `state.json` 반복 소실 버그 (PERF-WF-05) — 데이터 파괴

`workflow_kit/common/contracts/baselines.py` 의 성능 규칙이 **실제 `state.json` 을 50회
read/write** 하고 있었다:

```python
for _ in range(50):
    data = state_path.read_text(...)
    state_path.write_text(data, ...)   # truncate 후 쓰기
```

`write_text` 는 truncate 가 선행되므로 루프 중 프로세스가 kill 되면 **0바이트로 남는다**.
smoke 전량 실행(per-check timeout)·OOM 재부팅 때마다 사용자의 작업 기억이 사라졌고,
실제로 본 세션에서 3회 재현·복구했다. 벤치마크를 temp 사본으로 옮겨 원본은 읽기만 한다.

### 2.6 **fork bomb 근절 (PERF-WF-01)** — 반복 OOM 의 진짜 원인

세션 중 두 차례 발생한 "python3 수백 개 → OOM → 세션 kill" 의 원인을 규명했다.
performance baseline 의 `PERF-WF-01` 이 **실제 smoke 를 실행** 하고 있었다:

```python
for tf in list(tests_dir.glob("check_*.py"))[:3]:   # glob 은 정렬을 보장하지 않음
    subprocess.run(["python3", str(tf)], ...)
```

재귀 고리: `check_v0_7_4_followup.py` → `workflow doctor` → performance baseline →
`PERF-WF-01` → `check_*.py` 3개 실행 → **표본에 자기 자신 포함** → doctor → … 무한.
`glob()` 의 순서가 비결정적이라 자기 자신이 표본에 들어갈 수 있는 것이 방아쇠였다.
실측에서 프로세스들의 PPID 가 서로 같은 스크립트였던 것과 정확히 일치한다.

수정: 환경변수 `WORKFLOW_KIT_PERF_PROBE` 로 **재귀 depth 를 1 로 제한**, 표본을 `sorted()`
로 재현 가능하게, 자식은 `start_new_session=True` 로 격리. 수정 후 같은 파일 실행 시
프로세스 최대 3개로 즉시 종료(이전: 수백 개 누적).

### 2.7 smoke 실행 안전성 — resource guard 정식 채용

전량 실행 중 두 종류의 사고가 실제로 발생했다: `/tmp`(tmpfs)에 temp 가 쌓여 **RAM 고갈 →
OOM → 세션 kill**, 그리고 이전 사이클의 `/var/tmp` **211GB 점유**. 원인은 개별 check 의
버그가 아니라 *실행 방식* 이었으므로 `tests/run_all_checks.py` 가 직접 방어한다:

- check 마다 **전용 TMPDIR** 부여 후 종료 시 무조건 삭제 (누수 축적 원천 차단)
- `start_new_session` + 종료 시 **프로세스 그룹째 정리** (고아 자식 누적 차단 — `timeout` 은 부모만 죽인다)
- 디스크 여유(절대 1GB **또는** 비율 5%) / temp 총량(2GB) 초과 시 중단, **exit 3** 으로 구분
- TMPDIR 이 tmpfs 면 preflight 경고
- `.github/workflows/smoke.yml` 을 for-루프에서 본 러너 호출로 교체

### 2.8 브랜치별 메모리 (branch-scoped) + 자동 아카이브

다중 동시 작업에서 backlog index / task 번호 / `state.json` 이 서로를 덮어쓰지 않도록
메모리를 **물리적으로 분리**한다.

```
ai-workflow/memory/
├── active/<branch>/     ← state.json, backlog/, sessions/  (main 포함)
├── archived/<branch>/   ← 종료된 브랜치 (자동 이동 + .archived.json 메타)
├── archive/YYYY-MM-DD/  ← 기존 freeze
└── release/<version>/   ← 기존
```

- `paths.py`: `_branch_scoped_dir` / `workflow_state_path` / `state_path_for_workspace` /
  `workflow_archived_branch_dir` 추가. **legacy fallback** 을 두어 미마이그레이션 저장소도 안 깨진다.
- `active/state.json` 을 직접 조립하던 6곳(`cli` / `dashboard_data` / `ingest` /
  `baselines`×3 / `cache`)을 전부 브랜치 인식으로 통일.
- **task ID 채번 버그**: 기존 정규식 `TASK-(\d+)` 이 `TASK-2026-07-20-001` 의 연도를 순번으로
  오인해 다음 ID 가 `TASK-2027` 이 됐다. `TASK-<date>-<slug>-<NNN>` 으로 바꾸고 **같은 날짜 +
  같은 브랜치** 만 순번 비교 대상으로 삼는다 → 동시 작업 시 번호 충돌 0.
- **자동 아카이브**: hook 은 브랜치 삭제를 못 잡으므로 **역방향 점검** — `active/<slug>/` 가
  있는데 git 에 그 브랜치가 없으면 종료로 보고 `archived/` 로 이동한다. 고아가 구조적으로
  생길 수 없다. commit/push 는 하지 않으므로 **protected main 과 호환**되며, 작업 브랜치에서
  실행해 그 PR 에 실어 보낸다(piggyback).
- **집계 뷰**: dashboard 가 `active/*/state.json` 을 모두 스캔해 집계하므로 main 전용 집계
  파일이 불필요하다 → merge 마다 갱신할 대상이 없다.
- 도구 2종 신규: `tools/migrate_memory_to_branch_scoped.py`, `tools/archive_branch_memory.py`.
- 고아 정리: `memory/{gemini,codex}` (1.5개월 stale) → `archived/`,
  `memory/main/backlog/2026-06-30.md` (구 layout 상세 사료) → `archived/main-legacy/`.

## 3. 검증

누적 smoke **188/199 PASS** (2026-07-22, `run_all_checks.py --tmp-dir=<실디스크>` 격리 실행,
resource guard 완주 — abort 0 / 고아 프로세스 0 / 디스크 변동 0).
**전량 실행 후 워킹트리 변경 0** — smoke 가 추적 파일을 write 하던 3경로를 차단한 결과다.

| 항목 | 결과 |
|---|---|
| 전량 smoke | **188/199 PASS** (test case 211 PASS / 3 FAIL, 334초) |
| 저장소 오염 | **0 file** (이전에는 전량 실행 시 문서 63개 + fixture 2종이 수정됐다) |
| resource guard | abort 0, 프로세스 최대 4개, temp 최대 1MB |
| 신규 `check_branch_scoped_memory.py` | **8/8 PASS** |
| `check_appendonly_memory_layout.py` | 6/6 PASS (branch-scoped 갱신) |
| `check_v0_7_29_poststep_amend.py` | 9/9 PASS (재작성, 기존 red 회복) |
| `check_tempdir_leak_guard.py` | 7/7 PASS |

**본 사이클에서 회복시킨 red 8건**: `v0_7_29_poststep_amend` / `v0_10_2_delivery_layer` /
`mypy_strict_ci_v0_11_11` / `release_md_v0_15_18` / `memory_freeze_lint` /
`graph_insights_skill_integration` / `v0_7_28_archive_stale_memory`(TZ flaky) /
`ingest_atomicity`(날짜 flaky) + `v0_7_24_release_notes_template`(CLI 옵션 누락).

**잔여 red 11건** — 전부 v1.0.0 이전부터의 부채다. 성격별로 문서 lint(4:
`docs` / `source_without_runtime_layer` / `wiki_drift` / `wiki_trend`) / 빌드·도구
의존(4: `release_pipeline_lib` / `phase2` / `phase3` / `v0_7_4_followup`) /
프로세스(1: `wiki_source_rule` — memory-freeze 선행 필요) / 품질 게이트(2:
`smoke_trend_cross` case_5 + `quality_dashboard` Panel 4 — 둘 다 "전량 PASS(rate=1.0)"
를 요구하는 **목표 지표**이며, 잔여 red 를 모두 해소해야 통과한다. 수치를 맞추려고
릴리스 노트에 일부만 세지 않는다). 상세는 §0 잔여 과제 4번.

> CI 상태 의존 2건(`mypy_ci_cross_verify` / `release_summary`)은 push 후 CI 결과가
> 생기며 green 으로 전환됐다.

- **mypy**: venv mypy 2.1.0 `--strict` **117 source files, 0 errors** (Gate 3).
  smoke 는 반드시 `.venv/bin/python3` 로 실행해야 한다 — 시스템 python3 에는 mypy 가 없어
  mypy 의존 check 5종이 "exit 1 (0 errors)" 로 **위양성** 실패한다.
- breaking change: ❌ (메모리 layout 은 legacy fallback 으로 additive).

## 4. 산출물

- 신규: `tests/check_tempdir_leak_guard.py` + `releases/Beta-v1.0.0.md`.
- 수정 (핵심): `tools/release_pipeline.py` (amend 가드 3종 + helper 2 + flag 2) + `tests/check_v0_7_29_poststep_amend.py` (재작성) + `tests/check_v0_10_2_delivery_layer_extension.py` + `.github/workflows/smoke.yml` + `scripts/export_harness_package.py`.
- 문서: `core/v1_0_0_entry_evaluation.md` (6/6 gate 정합) + `core/workflow_kit_roadmap.md` (§8 P0-2/P1-1 완료 표기) + `core/maturity_matrix.json`.
- housekeeping: pyproject 1.0.0 + `__init__.py` fallback + sample 24 file `tool_version` + README/docs 헤더 + dashboard snapshot.
