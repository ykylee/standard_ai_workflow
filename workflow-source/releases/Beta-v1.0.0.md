# Beta v1.0.0 (2026-07-22)

> **상태: 릴리스.** `tool_version = v1.0.0-beta`, tag `v1.0.0-beta`, GitHub Release 발행.
> PyPI 배포는 정책상 미실행 (릴리스 채널 = GitHub Releases).
>
> 버전 suffix 체계는 기존 관례를 **유지**한다 (노트 파일명 `Beta-v*.md`).

## 0. 릴리스 판정

`core/v1_0_0_entry_evaluation.md` 의 entry gate 6/6 PASS 에 더해, **전량 smoke
199/199 PASS** (test case 219 PASS / 0 FAIL) 를 실측으로 확인했다.

v1.0.0 진입이 여러 차례 보류됐던 이유는 기능 미비가 아니라 **릴리스 도구와 메모리
계층이 실데이터·실행환경을 침범하던 구조적 결함**이었고, 본 사이클에서 모두 해소했다.

| # | 보류 사유였던 항목 | 상태 |
|---|---|---|
| 1 | 브랜치별 메모리 재설계 — session-start 자동 아카이브 wiring | ✅ 완료 |
| 2 | `MEMORY_GOVERNANCE.md` / `active/README.md` branch-scoped layout 반영 | ✅ 완료 |
| 3 | branch-scoped + 아카이브 전용 smoke 신규 | ✅ 완료 (`check_branch_scoped_memory.py` 8/8) |
| 4 | 기존 red smoke 잔여분 분류·해소 | ✅ 완료 (**잔여 0**) |
| 5 | CHANGELOG 재생성 + dashboard snapshot + tag/release | ✅ 완료 |

### 0.1 본 사이클에서 해소한 red (누적)

| 성격 | 대상 | 해소 방식 |
|---|---|---|
| **구조적** | `deprecation_cycle_v0_14_5` 외 3종 | `workflow_memory_dir()` 의 docs/ 분기에 `active/` 가 빠져 **부트스트랩한 모든 프로젝트의 memory 경로가 한 단계 어긋나** 있었다. bootstrap 산출물을 근거로 정정 (§2.9) |
| **프로세스** | `wiki_source_rule` (R9) | `memory-freeze` 스킬이 **문법 오류로 실행 불가**였던 것이 근본 원인. 복구 후 정식 freeze → wiki provenance repoint (§2.11) |
| **품질 게이트** | `smoke_trend_cross` case_5, `quality_dashboard` Panel 4 | **자기참조 구조** 제거 — 제외 대상을 note 에 명시하고 실효 지표로 판정 (§2.12) |
| **문서 lint** | `docs`, `source_without_runtime_layer`, `wiki_drift`, `wiki_trend` | 스코프 정정(생성물·불변 영역 제외) + 실제 부채 76건 수정 + 체커 위양성 3종 (§2.10) |
| **빌드 의존** | `release_pipeline_lib/phase2/phase3`, `v0_7_4_followup` | 릴리스 도구 의존(`build`/`twine`) 미선언 + `verify --apply` 부재 (§2.13) |
| **CI 상태 의존** | `mypy_ci_cross_verify`, `release_summary` | push 후 CI 결과 생성으로 자동 해소 |
| **미조사 6종** | `export_harness_package` 외 | 원인 확정 후 전부 해소 (§2.9) |

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

### 2.9 "미조사 6종" 원인 확정 — 실은 5개 원인, 진짜 버그는 1건

traceback 이 잘려 미확정이던 6종의 원인을 전부 규명했다. 서로 독립인 원인은 5개였고,
그중 **프로덕션 버그는 `refresh_wiki_memory` 1건**뿐이었다. 나머지는 test 가 저장소의
*우연한 상태*(버전 / git 태그 / 산출물 경로 계약)에 결합돼 있던 경우다.

- `export_harness_package`: 커밋 `24b626b` 이 dist 에서 저장소 절대경로를 제거하며
  payload 4 key 를 뺐는데 test 만 미갱신. 경로를 `output_root` 에서 유도하도록 바꾸고,
  **역방향 assertion**(payload 에 절대경로 key 부재 / manifest 에 REPO_ROOT 부재)을
  추가해 그 커밋의 의도를 계약으로 고정했다.
- `existing_project_onboarding`: bootstrap 이 non-TTY 에서 `--harness` 를 필수로 요구하게
  바뀐 뒤 exit 1.
- `release_status_auto_bump`: `_read_pyproject_version` 만 mock 하고 실제 git 태그와
  비교하는 분기 가드를 mock 하지 않아 분기 진입 자체가 불가였다.
- `drift_prevention_helpers`: `__init__.py` 에서 `"v0."` 을 grep — 1.0.0 bump 로 매치 0.
- `refresh_wiki_memory` (**실 버그**) + `run_all_checks`(그 downstream): §2.10 참조.

### 2.10 memory layout 버그 — 부트스트랩한 모든 프로젝트가 어긋나 있었다

`workflow_memory_dir()` 의 `docs/` 분기가 `ai-workflow/memory` 를 반환해 **`active/` 가
한 단계 빠져** 있었다. bootstrap 은 `docs/PROJECT_PROFILE.md` 와
`ai-workflow/memory/active/` 를 함께 만들므로, **새로 부트스트랩한 모든 프로젝트에서**
backlog / sessions / state.json 경로가 전부 틀렸고 state cache 가 skip 됐다.
`state/cache.py` 주석의 *"v0.6.0.1 의 `/ "active"` 후속 fix 누락"* 이 가리키던 지점이다.
정답은 코드가 아니라 **bootstrap 이 실제로 만드는 레이아웃**으로 판정했다.

재발 방지로 branch-scoped fallback 규칙을 `paths.py` 의 `path_in_active()` 한 곳에
모았다 — 규칙을 복사해 둔 caller 가 layout 변경을 놓친 것이 `refresh_wiki_memory`
red 의 원인이었다.

### 2.11 smoke 가 저장소를 침범하던 4경로 차단

전량 smoke 실행만으로 워킹트리가 더러워지거나 **작업이 사라지던** 경로들이다.
`release_pipeline` 의 `git add` 와 겹치면 릴리스와 무관한 변경이 release commit 에
흡수되므로 §2.3 의 amend 위험과 같은 계열이다.

1. **`release --dry-run` 이 문서 63개를 write** — `cmd_release` 의 `_attr_ns()` 가
   `dry_run=False` / `apply=True` 를 하드코딩해 auto-step 이 실저장소를 고쳤다.
   dry-run 의 계약 자체를 깨고 있었다.
2. `check_merge_doc_reconcile` → 예제 fixture 의 `state.json` 재생성.
3. `check_refresh_maturity_*` 3종 → `core/maturity_matrix.json` 의 `last_updated`.
   도구에 이미 있던 `--maturity-path` override 를 쓰지 않았다.
4. **`check_bidir_link_v0_13_3` 이 미커밋 작업을 파괴** — 복원을
   `git checkout HEAD -- ai-workflow/wiki` 로 해서 그 경로의 미커밋 작업이 조용히
   사라졌다. 실제로 본 사이클에서 wiki 수정분 전량이 smoke 한 번에 소실됐다.
   **snapshot 기반 복원**으로 교체(실행 직전 내용을 떠서 되돌림).

> **재발 방지 test 는 버그 코드에서 실패하는지 반드시 확인할 것.** dry-run 검증을
> "실행 전후 워킹트리 diff" 로 짰더니 **버그 코드에서도 PASS** 했다 — 앞 case 가 이미
> 날짜를 바꿔놔 두 번째 실행이 멱등 noop 이 된 탓이다. `--json` 의 step `mode` 로
> 판정하도록 바꿔 양방향(버그=FAIL / 수정=PASS) 검증했다.

### 2.12 R9 해소 — `memory-freeze` 스킬이 실행 불가였다

`wiki_source_rule`(R9) 의 근본 원인은 **freeze 스킬의 문법 오류**였다. v0.6.6
(`6a9126c`) 이 5개 skill 에 stage_completion 블록을 template 삽입할 때 skill 이름을
그대로 변수명에 넣어 `memory-freeze_completion`(hyphen) 을 만들었다. 즉 **v0.6.6 이후
R8 freeze 는 한 번도 수행되지 않았다.**

두 번째 결함으로 freeze 가 최상위 파일만 복사해 `active/<branch>/` 하위가 통째로
빠졌다(6 → **132 file**). MEMORY_GOVERNANCE §4 와 freeze lint 는 recursive 를 전제한다.

복구 후 `archive/2026-07-22/` 를 정식 생성하고 wiki 7 page 의 `last_ingested_from` 을
불변 archive 경로로 repoint 했다. **freeze 날짜는 소급하지 않았다** — 소급하면 그날
freeze 가 일어났다는 기록의 위조가 된다. `r9_skip` marker 로 침묵시키지도 않았다.

### 2.13 자기참조 품질 게이트 제거

`quality_dashboard` Panel 4 와 `smoke_trend_cross` case_5 는 "전량 PASS(rate=1.0)" 를
요구하는데 **자기 자신도 전량에 포함**돼, 둘이 green 이어야 green 이 되는 **순환**이었다.
과거 note 가 통과했던 것은 전량이 아니라 *일부만* 세어 적었기 때문("24/24")이며, 전량
199 를 정직하게 기록한 순간 만족 불가능해졌다.

숫자를 줄이는 대신 **제외 대상을 note 에 명시**하고(§3) Panel 4 가
`self_referential_excluded` / `effective_*` 를 추가로 내도록 했다. **원 수치는 그대로
남는다.** 순환을 끊자 두 게이트가 green 이 되어 최종 실측은 199/199 가 됐고, 제외
장치는 no-op 안전망으로 남는다.

### 2.14 릴리스 도구 의존 선언 + `verify --apply` 복구

`release_pipeline.py dist` 가 `python -m build` / `python -m twine check` 를 실제
호출하는데 **pyproject 에 선언돼 있지 않아** 환경마다 red/green 이 갈렸다.
`release` extra(`build>=1.0`, `twine>=4.0`) 로 명시한다. `_twine_check` 도 "미설치"와
"검증 실패"를 구분하도록 정정(`build` 는 이미 가용성을 따로 보고하던 비대칭).

**`verify` 는 CLI 로 실제 검증에 도달할 수 없었다** — 전역 정책이 "둘 다 미지정 →
dry-run" 인데 `verify` 서브파서에 `--apply` 가 없어 `gh release view` 를 부르는 본문
전체가 죽은 코드였다. `rollback` / `dist` 와 동일하게 플래그를 추가했다.

### 2.15 auto-bump 이 dry-run 에서 version 을 write 하던 결함 (**릴리스 후 발견**)

> 본 절은 `v1.0.0-beta` **발행 이후** 확인된 내용이다. tag `v1.0.0-beta` 시점의
> 노트에는 없으며 `main` 에서 보강했다. 수정 커밋: `94e61e1`.

발행 직후 전량 smoke 를 한 번 더 돌렸더니 **저장소 version 이 1.0.0 → 1.0.1 로 bump**
되어 있었다. `check_release_pipeline_release_coordination` 이 실행하는
`release --auto-bump --skip-validate --dry-run` 이 dry-run 인데도 `pyproject.toml` 과
`workflow_kit/__init__.py` 를 in-place 로 고친 것이다.

**왜 릴리스 전에는 드러나지 않았나** — auto-bump 는 `next_available_version()` 이
`bumped=True` 를 낼 때만 write 한다. 즉 **현재 version 의 tag 가 이미 존재할 때**만
발현하는데, 그 조건은 `v1.0.0-beta` 를 발행한 순간 처음 성립했다. 릴리스 전에는 조건이
거짓이라 조용히 잠복해 있었다. §2.11 의 `_attr_ns()` dry-run 미상속과 같은 계열이지만
**다른 코드 경로**다.

수정: `cmd_release` 의 auto-bump 두 경로(`--auto-bump`, `--full-auto` 재flow)가 모두
`args.dry_run` 을 존중하고, dry-run 은 `auto_bump.applied=False` / `mode="dry-run"` 을
보고한다. 재발 방지 case 7 추가 — 판정은 파일 diff 가 아니라 **보고된 mode** 로 한다
(bump 대상이 없으면 아무것도 쓰지 않아 파일 변화 유무가 저장소 상태에 좌우된다).

부수로 `test_remote_tag_check_dry_run_no_remote` 의 격리가 **애초에 동작하지 않았음**이
드러났다 — temp git repo + dummy remote 를 만들지만 `_check_remote_tag` 는 cwd 가 아니라
module-level `REPO_ROOT` 기준으로 실제 origin 을 조회한다(주석은 "cwd 기준 호출" 이라
적혀 있었다). 실제 의도인 graceful 동작만 검증하도록 정정.

> **교훈**: tag 존재 여부로 갈리는 코드 경로가 있으므로 **릴리스 직후 전량 smoke 를
> 반드시 한 번 더 돌리고 `git status` 를 확인해야 한다.** 릴리스 전 green 이 릴리스 후
> green 을 보장하지 않는다.

## 3. 검증

누적 smoke **199/199 PASS** (2026-07-22, `run_all_checks.py --tmp-dir=<실디스크>` 격리 실행,
resource guard 완주 — abort 0 / 고아 프로세스 0 / 디스크 변동 0).
**전량 실행 후 워킹트리 변경 0** — smoke 가 추적 파일을 write 하던 경로를 차단한 결과다.

- smoke 자기참조 게이트 제외: 2 (`check_quality_dashboard_v0_13_0` Panel 4,
  `check_smoke_trend_cross_v0_15_5` case_5)

> **왜 제외하는가**: 두 게이트는 "전량 PASS(rate=1.0)" 를 요구하는데 **자기 자신도
> 전량에 포함**된다. 따라서 둘이 red 인 한 pass != total 이고, pass == total 이
> 되려면 둘이 green 이어야 하는 **순환**이 생긴다. 과거 note 들이 이 게이트를
> 통과했던 것은 전량이 아니라 *일부만* 세어 적었기 때문이며, 전량 199 를 정직하게
> 기록한 순간부터 만족 불가능해졌다.
> 원 수치는 그대로 두고 **무엇을 왜 뺐는지 명시**해 실효 지표를 따로 낸다 —
> 숫자를 줄여 적는 방식(과거의 "24/24")과는 반대 방향이다.
> 자기참조를 끊자 두 게이트가 green 이 되어 최종 실측은 **199/199** 가 됐고, 제외
> 장치는 이제 no-op 이다. 향후 게이트 하나가 red 가 되어도 나머지로 연쇄되지 않게
> 하는 **안전망**으로 남긴다.

| 항목 | 결과 |
|---|---|
| 전량 smoke | **199/199 PASS** (test case 219 PASS / 0 FAIL) |
| 실효 smoke | **197/197 PASS** (자기참조 게이트 2건 제외 — 순환 재발 방지용 안전망) |
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
