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

### 2.16 실행 표면 / 저장소 오염 메타 체크 신규 (**릴리스 후 보강**)

> 본 절도 `v1.0.0-beta` 발행 이후 추가분이다 (§2.15 와 동일).

§2.11 의 오염 5경로와 §2.12 의 freeze 스킬 실행 불가는 **모두 사후에 사람이 발견**했다.
경로를 하나씩 막는 대신 그 부류가 생기는 것 자체를 CI 가 잡도록 메타 체크 2종을 세운다.

**`check_executable_surface.py`** — 실행 표면(skill / tool / script 62 file)이 실제로
실행 가능한가. (1) 전량 compile, (2) `run_*.py` entrypoint 16종의 `--help` 응답으로
import chain 검증, (3) hyphen 이 섞인 식별자 금지(v0.6.6 template 회귀 패턴 차단).

> 도입 즉시 **두 번째 실행 불가 스킬을 잡아냈다** — `git-conflict-resolver` 가
> 존재한 적 없는 `UnresolvedConflict` 를 import 해 entrypoint 가 ImportError 로
> 죽어 있었다. maturity_matrix 에는 **stable 로 등재**된 상태였다. 출력 계약이
> `list[dict[str, str]]` 이므로 dict emit 으로 정정했다(계약 변경 없음).

**`check_no_repo_write.py`** — 감시 대상 check 실행 전후로 `git status --porcelain` +
`git diff HEAD --stat` 해시를 비교해 추적 파일이 바뀌면 실패시킨다. 감시 목록은 과거에
실제 오염을 일으켰던 check 8종(경로 1~5 전부 포함).

- **전후 delta 로 판정**하므로 워킹트리가 이미 dirty 해도 동작한다.
- `git status` 만으로는 §2.11 경로 4(HEAD 로 복원해 작업을 지우는 유형)를 놓치므로
  내용 해시를 함께 본다.
- **오염을 일으키는 임시 check 를 넣어 FAIL 하는 것까지 확인**했다 (통과만 하는
  체크가 되지 않도록 — §2.11 의 교훈).

부수: `release_status.py` 의 `.rstrip("-beta")` 를 정식 suffix 제거로 교체.
문자집합 strip 이라 `"1.0.0-alpha"` → `"1.0.0-alph"`, `"1.0.0-rc"` → 그대로가 되어
alpha / rc 릴리스에서 version 비교가 조용히 어긋났다(둘 다 `suffix_order` 에 정식
지원되는 suffix). beta 만 쓰는 동안 우연히 맞았을 뿐이다.

### 2.17 memory-freeze stable 승격 + wiki L2 계층 복구 (**릴리스 후 보강**)

**memory-freeze 를 조건 충족 후 stable 승격.** §2.12 에서 복구했지만 status 는
`prototype (P2, v0.6.1)` 이었고, `skill_beta_criteria.md` §3.1 의 6개 조건 중 **3개가
미충족**이었다(error_code 2종 <3 / 전용 smoke 부재 / maturity_matrix 미등재).
라벨만 바꾸면 §2.16 이 잡아낸 `git-conflict-resolver`("stable 등재 + 실행 불가")와
같은 실수가 되므로 조건을 실제로 채웠다:

- `ARCHIVE_WRITE_FAILED` 추가 — copy 실패 시 **부분 freeze 를 남기지 않도록** 방금 만든
  archive_dir 을 제거한다. archive 는 R9 immutable 이라 반쪽 스냅샷이 굳으면 이후
  ingest 의 출처가 오염된다.
- `check_memory_freeze_skill.py` 신규 6 case — 기존 `check_memory_freeze_lint.py` 는
  archive 무결성(R10) lint 이지 skill 을 실행하지 않아, 이 skill 이 실행 불가였던
  1년 가까이를 아무도 탐지하지 못했다. 정상 freeze / **recursive 포함** / 중복 skip
  (immutability) / `--freeze-date` override / error 2종을 모두 temp 위에서 검증한다.
- maturity_matrix 등재 (skills 12 → 13).

> 부수 발견: maturity_matrix 와 디스크가 **3방향으로 드리프트**해 있다 —
> `robust_patcher`(디스크) vs `robust-patcher`(등재), `task-modes` 등재-디스크 부재,
> `memory-index-query` / `workers` 미등재. 별도 정리 필요.

**wiki L2 계층 복구.** `wiki/sources/` 가 `.gitkeep` 뿐이라 dashboard 의
discoverability / lifecycle 이 분모 0(측정 불가)이었다. `--emit-l2 --apply` 가 부재 시
**bootstrap 생성**하도록 바꿔 4 stub 을 복원했다(이전엔 loud 실패라 영원히 생성 불가).

그 결과 **lifecycle 지표가 잘못 정의돼 있었음이 드러났다.** 정의가
`status: reviewed` 비율인데 (1) `reviewed` 는 wiki SCHEMA 에 정의된 적 없는 값이고,
(2) L2 stub 은 매 사이클 재생성되는 **생성물**이라 "사람이 검토함" 상태가 구조적으로
붙지 않는다. stub 을 복원하자 0.00 이 됐는데 이는 품질 저하가 아니라 지표 오정의
신호였다. `last_touched` 신선도(기본 30일)로 재정의하고 **SCHEMA 에 L2 sources 절을
신설**해 명문화했다(`reviewed` 미사용 명시).

측정 결과: discoverability n/a → **5.00**, lifecycle n/a → **5.00**,
overall **4.68 (Grade A)**, trend alert 0건.

### 2.18 maturity registry 정합 — "선언이 사실인가" 를 CI 가 검사 (**릴리스 후 보강**)

§2.16 의 `check_executable_surface` 가 "실행 가능한가" 를 본다면, 본 절은 **"선언이
사실인가"** 를 본다. 한 사이클에 선언-실제 괴리가 두 번 나왔기 때문이다:
`git-conflict-resolver`(stable 등재 + 실행 불가), `memory-freeze`(governance 필수
규칙 구현인데 registry 미등재 + prototype 표기).

**드리프트 3건 해소** — registry ↔ 디스크가 세 방향으로 어긋나 있었다:

| 유형 | 대상 | 처리 |
|---|---|---|
| 디렉터리명 규약 이탈 | `robust_patcher`(underscore) vs 등재 `robust-patcher` | 다른 13개와 같은 hyphen 규약으로 디렉터리 rename (Python import 없음 확인, live 참조 3건 갱신). `family="robust_patcher"` 는 payload family 이름이라 별개로 유지 |
| 등재됐으나 디스크 부재 | `task-modes` | 실행 skill 이 아니라 **명세**(`core/workflow_task_modes.md`) → `kind: "spec"` 명시. `test_path: null` + stable 이 조건과 충돌하던 것도 해소 |
| 디스크에 있으나 미등재 | `memory-index-query` | 등재. SKILL.md 가 스스로 `beta` 라 선언하고 실행 예시 절도 없으므로 **beta 로 정직하게** 등재 |
| skill 아님 | `workers/`(SKILL.md 없음) | `skill_registry_exempt_dirs` 로 명시적 제외 |

**`check_maturity_registry.py` 신규** (3 case): registry ↔ 디스크 양방향 정합 /
`stage: stable` 의 승격 조건 충족 / `test_path` 실재.

도입 과정에서 `git-conflict-resolver` 의 **SKILL.md 에 실행 예시 절이 없다**는 실제
누락을 잡아 CLI 실측 기준으로 추가했다.

> **의도적으로 검증하지 않는 조건**: §3.1 의 "error_code 최소 3종" 은 선언 위치가
> 통일돼 있지 않다 — run script inline literal / `.get("error_code", ...)` default /
> 일부는 schema 의 `*_ERROR_CODES` tuple (게다가 schema module 명이 skill 명과 1:1 이
> 아니다: workflow-linter → `linter.py`, git-conflict-resolver → `git.py`).
> 어설픈 정규식 계수는 위양성을 냈고(초안이 정상 skill 4종을 오탐), **위양성을 내는
> check 는 무시당해 결국 아무것도 막지 못한다.** 규약이 생기면 기계 검증으로 승격한다.

세 메타 체크 모두 **드리프트를 주입해 FAIL 하는 것까지 확인**했다.

### 2.19 Panel 1 의 두 지표가 구조적으로 무의미했다 (**릴리스 후 보강**)

§2.18 이 "선언이 사실인가" 를 물었다면, 본 절은 한 단계 더 올라가 **"지표 자체가
무엇을 재고 있는가"** 를 묻는다. 답은 둘 다 *재고 있지 않았다* 였다.

| 지표 | 기존 정의 | 문제 |
|---|---|---|
| `maturity_stale` | `last_updated != 오늘` | `maturity_matrix.json` 을 **매일** 스탬프하지 않는 한 항상 True. 초록으로 만드는 유일한 방법이 "날짜만 찍기" 였고, 그건 §2.18 이 하지 말라고 경고한 그 행위다 |
| `silent_failing_cycles_count` | `1 if maturity_stale else 0` | Phase 13 AC1 north-star 의 정의(*drift 를 manual fix 해야 했던 release cycle 의 누적 갯수*)와 아무 관계 없는 freshness proxy 가 north-star 자리에 앉아 있었다 |

**stale 재정의 — 달력이 아니라 drift.** maturity surface(`skills/` ·
`mcp_servers/` · `harnesses/` · matrix 자신)를 마지막으로 바꾼 commit 날짜가 선언
(`last_updated`)보다 **나중**이면 선언이 뒤처진 것 = stale. surface 가 그대로면
몇 달이 지나도 stale 이 아니다. 스탬프로는 못 속이고 선언을 실제로 갱신해야만
초록이 된다. 판정 근거가 없으면(git 불가 / 선언 부재) `source: unknown` 으로
**stale 로 단정하지 않는다** — 근거 없이 red 를 내는 체크는 위양성으로 무시당한다.

이 재정의를 켜자 곧바로 진짜 drift 가 하나 잡혔다: `43079c0` 이 skill 디렉터리와
matrix 를 바꾸면서 `last_updated` 는 안 올렸다. 선언을 `2026-07-22` 로 갱신해 해소.

**north-star 분리 — 원장에서만 나온다.** freshness proxy 를 떼어내고
`ai-workflow/memory/release/drift_ledger.jsonl`(append-only, release cycle 당 1 line)
에서 읽는다. release pipeline 이 self-recover 결과를 cycle 마다 기록하고 —
**drift 가 없던 cycle 도 기록한다**. 분모가 없으면 "0건" 과 "안 재봄" 이 같은 0 으로
보이기 때문이다. 원장이 비면 `0` 이 아니라 **`미측정`** 으로 렌더한다.

`check_north_star_metric.py` 신규 (6 case). **구 판정 코드를 되돌려 주입해 case 2
(달력 회귀)와 case 4(proxy 회귀)가 실제로 FAIL 하는 것을 확인**했다 — §0 의
"재발 방지 test 는 버그 코드에서 실패하는지 확인" 규칙 정합. 곁들여 refresh hint 가
`python3 -c "python3 -c "…""` 로 깨져 나가던 렌더 버그도 고쳤다.

### 2.20 state.json 이 2026-07-21 이후 갱신되지 않고 있었다 (**릴리스 후 보강**)

"v1.0.0 사이클이 워크플로우 메모리에 미기록" 이라는 증상을 파고들자 손이 게을렀던
게 아니라 **코드가 조용히 실패하고 있었다**.

v1.0.0 의 branch-scoped 전환에서 `state.json` 경로가 절반만 옮겨졌다:

| | 경로 | |
|---|---|---|
| hint (`build_state_cache_refresh_hint`) | `active/<branch>/state.json` | ✅ 옮겨짐 |
| writer (`refresh_workflow_state_cache`) | `active/state.json` | ❌ 남겨짐 |

reader 는 전부 `workflow_state_path()` 를 통해 branch-scoped 를 보므로, refresh 는
**아무도 읽지 않는 파일**을 새로 만들고 정작 읽히는 `active/main/state.json` 은 영원히
갱신되지 않았다. 게다가 반환값은 `"refreshed"` 였다 — 성공했다고 보고하면서 실패한다.
이것이 Phase 13 north-star 가 세려는 *silent failing* 의 교과서적 사례다.

같은 호출 경로에서 두 번째 결함도 드러났다: **`backlog-update` 가 `--apply` 없이도
state cache 를 재생성**했다. 초안만 달라는 호출이 저장소에 파일을 만드는 것으로,
skill 권한 경계(§5 "초안 생성 중심") 위반이자 §2.15 auto-bump 와 같은 부류의 dry-run
오염이다. 실제로 이 사실은 **스킬을 직접 돌려보다가** 발견했다 — 정적으로 읽을 때는
안 보였다.

`check_state_cache_branch_scoped_write.py` 신규 (4 case: writer 가 branch-scoped 로
쓰는가 / hint 와 writer 의 경로가 같은가 / 미마이그레이션 저장소는 legacy 유지 /
draft 모드가 아무것도 쓰지 않는가). **구 코드에서 3 case 가 FAIL** 하는 것을 확인했다.

> **기존 테스트가 버그를 규약으로 굳혀 놓고 있었다.** `check_backlog_update.py` case 1 은
> `--apply` 없이 호출한 뒤 `state_cache_status == "refreshed"` 를 *단언*하고 있었다.
> 테스트가 dry-run 오염을 요구하고 있었으므로, 판정 자체를 뒤집어 고쳤다.

### 2.21 stable skill 이 governance 가 규정한 layout 을 만들지 못했다 (**릴리스 후 보강**)

§2.20 의 close-out 을 하려고 `backlog-update` 를 실제로 돌려보니, stable 로 선언된
skill 의 `--apply` 산출물이 **v0.14.0 append-only layout 이 아니었다**. v0.14.0 전환이
절반만 적용돼 있었던 것:

| | 산출물 | 현행 규약 |
|---|---|---|
| task file 이름 | `YYYY-MM-DD_TASK-….md` | `TASK-….md` |
| daily index | task 본문을 **통째로 인라인** | link 모음 |
| 덮어쓰기 | `.md.bak` 생성 | `.bak` 는 v0.15.0 에서 폐기 |

그래서 이번 사이클의 메모리 파일은 손으로 썼고(§2.20), 그 사실을 후속 작업으로
**선언해** 두었다. 본 절이 그 후속을 닫는다.

**정본 ID 패턴을 단일 출처로.** 더 근본적인 문제는 task ID 정규식이 네 군데에 흩어져
있었다는 것이다 — `TASK_HEADER_RE`(대문자만 허용), builder 의 daily-index 정규식,
layout 체커, skill. v1.0.0 branch-scoped 가 도입한 `TASK-<date>-<slug>-<NNN>` 은
소문자 slug 를 포함하므로 **앞의 셋 모두에서 인식되지 않았다**. 정본을
`project_docs.TASK_ID_PATTERN` 하나로 모으고 나머지가 그것을 import 하게 했다.

**`--kind` flag 신규** (`release` | `session` | `generic`) — frontmatter 의 `kind`
이자 index 의 `[kind]` marker. index 갱신은 **block 단위 교체**라 같은 task 를 다시
apply 해도 중복되지 않고, 사람이 손으로 넣은 `source:` 주석도 살아남는다.

`check_backlog_update_layout.py` 신규 (5 case). 기존 smoke 는 "파일이 쓰였는가" 와
본문 문자열만 보고 **layout 자체를 규약으로 검사하지 않아** 이 드리프트를 1년 가까이
놓쳤다. 구 writer 동작을 되돌려 주입해 **5 case 전부 FAIL** 하는 것을 확인했다.

### 2.22 세 결함이 같은 모양이었다 — writer ↔ reader 왕복 계약 (**릴리스 후 보강**)

§2.19 / §2.20 / §2.21 을 나란히 놓으면 하나의 결함이다: **같은 사실이 두 곳에 있는데
둘을 이어주는 기계적 장치가 없다.**

| 사례 | 두 곳 | 왜 기존 테스트가 못 잡았나 |
|---|---|---|
| §2.19 north-star | 지표 **정의**(wiki) ↔ **구현** | proxy 를 north-star 자리에 앉혀도 타입은 맞다 |
| §2.20 `state.json` | **writer** 경로 ↔ **reader** 경로 | 각자 자기 경로에서 정상 동작, 서로 만나지 않는다 |
| §2.21 task ID | 정규식 **4곳** 복제 | 각 정규식이 자기 테스트를 통과한다 |

공통점은 **부품별 테스트가 전부 green 인데 조립하면 안 맞는다**는 것. 그래서 단언을
하나로 통일한 smoke 를 둔다 — *프로덕션 writer 로 쓰고 **프로덕션 reader 로 되읽어
같은 것이 나오는가***. `check_writer_reader_roundtrip.py` 신규, 8 pair:

`state.json` · daily index/task · append-only 집계 · maturity 선언 · drift 원장 ·
telemetry · memory_index entry · session handoff.

**§2.20 과 §2.21 의 결함을 되돌려 주입해 해당 pair 가 실제로 FAIL 하는 것을 확인**했다
(§2.19 는 duplication 이 아니라 *대체* 라 본 계열로는 안 잡힌다 — 지표가 판정 근거를
함께 emit 하게 한 §2.19 의 장치가 그 몫이다).

> **fixture 를 손으로 쓰면 이 결함을 못 잡는다.** 처음 작성한 `state.json` pair 는
> 빈 workspace 에서 시작해 통과해버렸다 — writer 가 legacy 경로에 써도 reader 의
> fallback 이 그 파일을 집어 우연히 일치했기 때문이다. **이미 갱신돼 온 파일이 있는**
> 실제 저장소 상태를 재현하자 비로소 FAIL 했다. 계약 테스트는 *실제 상태를 닮은
> 출발점* 에서 시작해야 한다.

곁들여 `_append_drift_ledger_entry` 가 저장소 경로에 고정돼 있던 것을
`workspace_root` 주입 가능하게 고쳤다 — 고정돼 있으면 계약 테스트가 실저장소를
오염시킨다. **테스트 가능성이 곧 설계 압력**으로 작동한 사례.

### 2.23 판정 지표는 근거를 함께 낸다 (**릴리스 후 보강**)

§2.22 의 왕복 계약이 잡는 것은 *복제로 인한 갈라짐* 이다. §2.19 는 복제가 아니라
**대체**(진짜 측정 자리에 대충 계산한 값을 앉힘)라서 그 계열로는 안 잡힌다. 못 알아챈
이유는 단순하다 — **값의 타입은 맞았고, 근거를 말하지 않으니 대조할 것이 없었다.**

그래서 규칙을 하나 세운다: **판정 지표는 값과 함께 판정 근거(`*_source`)를 emit 한다.
north-star 는 측정 여부(`*_measured`)도 emit 하고, 못 쟀으면 0 이 아니라 `미측정` 으로
렌더한다.** `JUDGMENT_METRICS` registry 가 정본이고
`check_metric_source_contract.py` (5 case) 가 강제한다.

도입하면서 **Panel 6 의 north-star 도 같은 결함이었음**이 드러났다.
`multi_agent_concurrent_write_conflict_count` 는 working tree marker + `git log` 두
측정원을 쓰는데, git 호출이 실패하면 예외를 삼키고 0 을 그대로 뒀다 — **"충돌 없음" 과
"못 셌음" 이 같은 0 이었고, 그 상태로 `status: pass` 를 냈다.** `conflict_count_source`
(`working_tree+git_log`) + `conflict_count_measured` 를 추가하고, 측정원이 하나도 안
돌면 `status: unknown` 을 내도록 고쳤다.

검증: §2.19 형태(근거를 `freshness_proxy` 로 둔 proxy)와 Panel 6 의 근거 부재 상태를
각각 주입해 해당 case 가 FAIL 하는 것을 확인했다.

> **한계를 과장하지 않는다.** 근거 이름을 그럴듯하게 지어 붙이면 이 check 는 통과한다.
> 구조적으로 보장하는 것은 (a) 근거 field 의 존재, (b) 'pending/tbd' 류 표현 배제,
> (c) **새 north-star 가 registry 를 우회할 수 없음** — 이 셋이다. 근거가 *사실인지* 는
> §2.22 의 실측 계약이 본다.

### 2.24 규약은 정본 한 곳에서만 — 그리고 남아 있던 사본 7건 (**릴리스 후 보강**)

§2.22 는 *조립이 맞는가*, §2.23 은 *근거를 말하는가* 를 본다. 남은 한 겹은 애초에
**사본이 생기지 못하게** 하는 것이다.

`check_convention_single_source.py` 신규 (4 case). 판정 규칙은 단순하다 — 등록된 규약의
리터럴을 쓰는 production 파일은 **정본 모듈이거나, 정본 symbol 을 import 하거나** 둘 중
하나여야 한다. 아니면 사본이다. 예외는 **이유와 함께** registry 에 적는다(조용한 우회
경로를 만들지 않는다). 등록 규약 3종: `state.json` 경로 조립 / task ID 정규식 /
drift 원장 경로.

> **범위를 좁게 잡는 것이 전부다.** 일반적인 "중복 코드 탐지"로 만들면 위양성이
> 쏟아지고, 위양성을 내는 check 는 무시당해 결국 아무것도 막지 못한다(§2.18 에서 이미
> 겪은 실패 모드). 그래서 *등록된 규약만* 본다. `tests/` 는 제외 — fixture 경로 조립은
> 정당한 사용이다.

**도입하자마자 사본 7건이 나왔다.** §2.20 에서 고친 것은 writer 한 곳이었는데, 같은
legacy 조립(`workflow_memory_dir(...) / "state.json"`)이 **6곳에 더** 남아 있었다:

| 대상 | 실제 영향 |
|---|---|
| `doc-sync` / `session-start` / `backlog-update` / `workflow-linter` | `build_purpose_context` 가 `purpose_digest=None` 을 받는다 — **4개 skill 이 목적 컨텍스트 없이 동작**했다 (실측 확인: legacy 경로 → None, 정본 → 정상) |
| `release_pipeline.py` validate | state.json freshness 게이트가 `exists()` False 로 **조용히 통과** |
| `sync_release_hash.py` | 아무도 읽지 않는 파일에 release hash 를 기록 |

일곱 번째는 task ID 정규식 사본(`backlog-update` 의 `TASK_ID_RE`)이다. 채번용 분해
정규식을 `project_docs.TASK_ID_CAPTURE_RE` 로 올리고 skill 이 import 하게 했다.

수정 전 코드로 돌려 **7건을 모두 이름까지 지목해 FAIL** 하는 것을 확인했다.

### 2.25 같은 부류 전수 조사 — memory 경로 조립 14곳 (**릴리스 후 보강**)

§2.24 에서 얻은 교훈이 "하나 고쳤다고 그 부류가 끝난 게 아니다" 였으므로, **같은 모양의
리터럴을 전수 조사**했다. production 179 파일의 문자열 상수를 AST 로 뽑아 파일 수 기준
빈도를 냈고, 1~3위가 `"ai-workflow"`(28) / `"memory"`(21) / `"active"`(19) 였다 —
`state.json` 은 12위였다. 즉 §2.20 에서 만난 것은 **더 넓은 문제의 한 조각**이었다.

`ai-workflow/memory/…` 를 손으로 이어 붙이는 곳이 **14개 모듈**에 있었다.
workspace root 만 아는 caller 를 위한 정본 진입점이 없어서 각자 조립하고 있었던 것이다
(`workflow_memory_dir` 은 `PROJECT_PROFILE.md` 경로를 받는다).

- `paths.py` 에 `memory_dir_for_workspace(workspace_root)` /
  `memory_active_dir(workspace_root)` 신규 — `state_path_for_workspace` 와 같은 계열.
- 14개 모듈(dashboard / builder / memory_index / purpose_* / auth / 4 tool /
  2 migration tool / export) 의 조립을 helper 호출로 교체. **경로 값은 동일**하므로
  동작 변화 없음 (전량 209/209 로 확인).
- `check_convention_single_source.py` 에 네 번째 규약으로 등록 — 다시 자라지 못한다.

마이그레이션 전 코드로 돌려 **14곳을 모두 지목해 FAIL** 하는 것을 확인했다.

> 자동 치환 과정에서 import 를 `# noqa` **주석 뒤에** 붙여 두 tool 이 NameError 로
> 죽는 실수를 냈다. 전량 smoke 가 `check_branch_scoped_memory` 6/8 과
> `check_v0_7_26_sync_release_hash` 1/5 로 즉시 잡았다 — **기계적 일괄 치환일수록
> 전량 실행이 필수**라는 증거로 남긴다.

### 2.26 north-star 의 분자가 도달 불가였다 — 원장에 첫 entry 가 생길 수 없었다 (**릴리스 후 보강**)

§2.19 에서 north-star `silent_failing_cycles_count` 를 원장 기반으로 재정의하고
"다음 릴리스에서 첫 entry 를 확인한다" 를 다음 작업으로 남겼다. 그 확인을 하려고
경로를 따라가 보니, **첫 entry 가 생길 수 있는 호출 경로 자체가 없었다.**

`cmd_release` 안에서 두 지점의 순서가 이랬다:

```
step 2.7  : self-recover → manual_required 1+ 이면 **early return**
step 6.5b : (gh release create 성공 뒤) 원장 append      ← 도달 불가
```

원장의 분자는 `manual_required_count > 0` 인 line 인데, 그런 line 을 만들 수 있는
cycle 은 **정확히 step 2.7 에서 멈추는 cycle** 이다. 즉 지표가 한 방향으로만 움직일
수 있었다 — 영구히 0.

단순 누락보다 나쁜 점이 있다. 릴리스가 한 번이라도 성공하면 clean line 이 쌓여
`measured` 가 True 로 뒤집힌다. 그러면 정직한 `미측정` 이 **"N cycle 재봤더니 0건"**
이라는 거짓 초록불로 바뀐다. §2.19 가 세운 "원장이 비면 미측정" 원칙이 바로 그
구간에서 무력해진다.

- `_self_recover_step` 추출 — self-recover 실행 / **원장 기록** / manual_required 판정을
  한 단위로 묶고, 기록을 early return **앞**, 즉 drift 판정이 확정되는 지점에 둔다.
  step 6.5b 는 제거하고 자리에 이유를 남겼다.
- 부수 효과 1: step 6 dashboard emit 보다 앞이 되어, release 가 emit 하는 snapshot 이
  **자기 cycle 을 포함**한다 (이전에는 항상 한 cycle 뒤처졌다).
- 부수 효과 2: `--skip-self-recover` 면 drift 를 재지 않았으므로 원장에도 남기지
  않는다. "안 쟀다" 를 "0건" 으로 적지 않는다.
- reader `collect_silent_failing_cycles` 를 line 단위 → **version 단위 cycle 집계**로.
  manual fix 후 재실행은 한 cycle 의 두 시도인데, line 을 그대로 세면 **정상 운영
  흐름이 분모를 계속 부풀린다** (1 cycle 이 "1/2" 로 보인다). 한 cycle 안에서 한 번이라도
  manual 개입이 있었으면 그 cycle 을 분자로 센다.

**왜 §2.22 왕복 계약이 못 잡았나.** 왕복 테스트는 writer 를 *직접* 불러 dirty payload 를
넣는다. 그래서 pair 는 green 이었다 — 프로덕션 orchestrator 는 writer 에게 그 payload 를
건넬 수 없는데도. writer 와 reader 가 맞물리는지 보는 것만으로는 부족하고,
**orchestrator 가 writer 를 그 값으로 부를 수 있는 경로가 있는가** 를 따로 봐야 한다.

- 신규 `check_drift_ledger_cycle_recording.py` (5 case) — orchestrator 를 실제로 돌려
  manual cycle / clean cycle / dry-run 무기록 / 같은 version 재시도 / 원장→north-star 를
  검사한다. **원장 append 를 제거해 되돌려 주입하니 5/5 FAIL** 하는 것을 확인했다.
- 기존 `check_writer_reader_roundtrip.py` 의 drift 원장 pair 가 "같은 version 2줄 =
  2 cycle" 을 전제하고 있어 함께 갱신했다 (재시도 case 추가).

> 이 결함은 §2.23 이 만든 근거 계약(`*_source` / `*_measured`)을 **통과한 채로**
> 존재했다. 근거 이름은 정확했고 원장도 실재했다 — 다만 그 원장에 분자가 들어갈 수
> 없었을 뿐이다. §2.23 이 스스로 명시한 한계("근거 이름을 그럴듯하게 지으면 통과")의
> 실제 사례로 남긴다.

### 2.27 "209/209" 는 작성자 워킹카피에서만 성립했다 — CI 는 계속 red 였다 (**릴리스 후 보강**)

§2.26 을 고치고 전량을 다시 돌리다 5건이 실패했다. 처음엔 이 워크트리에 `.venv` 가 없어서인
줄 알았는데, **깨끗한 HEAD 워크트리에서 정본 러너로 돌려도 같은 5건이 실패**했다. 확인해 보니
GitHub Actions smoke workflow 는 **최근 40회 전량 failure** 였고 성공 기록이 없었다 —
"전량 209/209", "208/208", "207/207" 을 적은 바로 그 커밋들 포함이다.

CI 는 fresh clone 에 `pip install -r requirements*.txt` 만 한다. 즉 그 수치들은 `.venv` 와
gitignore 된 런타임 데이터가 **누적된 원본 작업 사본에서만** 재현됐다. 이 저장소가 §2.19~§2.24
동안 고쳐 온 것이 "지표가 무엇을 재고 있는가" 였는데, 정작 **전량 smoke 라는 최상위 지표
자체가 재현 불가능한 환경에서 측정되고 있었다.**

5건의 뿌리는 하나다 — *테스트가 실행 환경에 누적된 상태에 의존한다*:

| check | 원인 | 조치 |
|---|---|---|
| `check_memory_index` | `<workspace>/.venv/bin/python3` 하드코딩 | `sys.executable` (저장소 관용구) |
| `check_telemetry_cross_v0_15_6` | gitignore 된 live `events.jsonl` 의존 | 프로덕션 writer 로 fixture workspace 생성 |
| `check_phase15_dashboard_panels` case_3 | 동일 | 동일 |
| `check_deprecation_cycle_v0_14_5` case_1 | 실저장소 `active/<branch>/backlog` 의존 | branch-scoped temp workspace + env pin |
| `check_graph_insights_..._v0_11_2` | 실저장소 `active/<branch>/state.json` 의존 | temp workspace |

**skip 이 아니라 fixture 로 고쳤다.** 없는 파일을 만나면 skip 하게 두면 CI 에서 항상 skip 되고,
그건 red 보다 나쁘다 — 도는 척하며 초록으로 보인다. fixture 는 손으로 쓰지 않고
`append_telemetry_event` / `save_memory_entry` 같은 **프로덕션 writer 로** 만든다 (§2.22 와 같은 이유).

고치는 과정에서 두 가지가 더 드러났다:

- **`check_graph_insights` 의 read-only 단언은 무의미했다.** 파일이 없으면 mtime 비교가
  `None == None` 이 되어 *아무것도 증명하지 않고 통과*한다. 이제 실제로 존재하는 파일을 잰다.
- **`check_telemetry_cross` 에 `assert True` dummy case 가 있었다** (주석: "case 가 4개뿐이라
  dummy 추가"). 자리를 채우던 것을 실제 검사(telemetry 부재 분기)로 교체했다 — 그 분기는
  그때까지 한 번도 테스트된 적이 없었다.

곁들여 **정본 helper 의 결함**을 하나 찾았다. `state_path_for_workspace(workspace_root)` 가
접두는 인자에서 가져오면서 **branch 는 이 모듈이 속한 저장소**에서 가져오고 있었다:

```
cwd=repoA(main)    : state_path_for_workspace(repoB) → repoB/…/active/main/
cwd=repoB(feature) : state_path_for_workspace(repoA) → repoA/…/active/feature/
```

같은 인자에 대해 **호출 위치가 답을 바꾼다.** `branch_for_workspace()` 를 신설해 workspace 를
받는 쪽은 그 workspace 의 git 을 보게 했다 (`get_current_branch()` 는 sandbox caller 를 위한
기존 동작 유지). §2.25 가 경로 조립을 정본으로 모았는데, **정본 자신이 두 출처를 섞고 있었다.**

### 2.28 문서 사이트는 한 번도 배포된 적이 없었다 — mkdocs plugin 이 로드 불가였다 (**릴리스 후 보강**)

`mkdocs.yml` 에 이렇게 적혀 있었다:

```yaml
plugins:
  - search
  - tools.mkdocs_git_dates:GitDatesPlugin
```

그리고 workflow 는 `PYTHONPATH=workflow-source` 를 주며 주석에 "plugin import 가능하게"
라고 적어 두었다. **그러나 mkdocs 는 `plugins:` 항목을 `mkdocs.plugins` entry point
*이름* 으로만 해석한다** (`plugins.get_plugins()` → `entry_points(group=...)`). import
경로가 아니다. 그래서 매 build 가 이렇게 중단됐다:

```
ERROR - Config value 'plugins': The "tools.mkdocs_git_dates:GitDatesPlugin"
        plugin is not installed
```

`PYTHONPATH` 로는 해결되지 않는 구조다. 최근 100회 실행 중 **성공 0회** — 즉
**문서 사이트가 한 번도 배포되지 않았다** (build 실패 → Pages deploy job skip).
덧붙여 `GitDatesPlugin` 은 `BasePlugin` 을 상속하지도 않아, entry point 를 등록했더라도
mkdocs 가 거부했을 것이다. 두 겹으로 불가능했다.

**수정: `plugins:` → `hooks:`.** mkdocs 의 `hooks:` 는 **파일 경로**로 모듈을 읽어
module-level 함수를 event handler 로 쓴다 — 저장소 로컬 훅을 패키징 없이 붙이라고 있는
수단이고 이 경우에 정확히 맞는다. `tools` 를 wheel 에 넣는 대안은 소비자에게 저장소 내부
도구를 배포하게 되므로 택하지 않았다. 기존 `GitDatesPlugin` 클래스는 로직의 정본으로
남기고 module-level `on_page_markdown` 이 위임한다 (`MKDOCS_GIT_DATES=off` 로 비활성).

실측: `mkdocs build --strict` **성공**, 그리고 훅이 실제로 동작한다 —
`docs/CODE_INDEX.md` 의 선언 `2026-07-21` 이 산출물에서 git 실제 날짜 `2026-07-23` 으로
교체됐다.

**신규 `check_mkdocs_config.py` (4 case)** — mkdocs 설치 없이 로드 가능성의 *필요조건*
만 본다: `plugins:` 항목이 entry point 이름 모양인가(`module:Class` 면 즉시 fail) /
`hooks:` 경로 실재 / hook 모듈이 **module level** event 함수를 노출하는가(클래스
메서드만 있으면 호출되지 않는다) / 탐지기 자체 동작. 원래 결함을 되돌려 주입하니
`test_plugins_are_entry_point_names` 가 **FAIL** 하는 것을 확인했다.

> 이 결함이 오래 산 이유는 §2.27 과 같다. 설정은 그럴듯해 보였고, 로컬에서 `mkdocs build`
> 를 돌리지 않으면 드러나지 않으며, CI 는 red 였지만 **무엇이 깨졌는지 볼 수 없었다**.

**고치자마자 다음 층이 드러났다.** main 에 병합해 처음으로 build 가 성공하니
(`Build site: success`), 이번엔 그때까지 **한 번도 실행된 적 없던 deploy job** 이 실패했다:

```
Error: Unable to get ACTIONS_ID_TOKEN_REQUEST_URL env variable
##[error]Ensure GITHUB_TOKEN has permission "id-token: write".
```

`actions/deploy-pages@v4` 는 OIDC 토큰을 요구하는데 workflow 는 `contents: write` 만
선언하고 있었다. build 가 항상 먼저 죽었으므로 이 구멍은 관측될 기회가 없었다.
`permissions` 를 `contents: read` / `pages: write` / `id-token: write` 로 정정했다
(gh-pages 브랜치를 쓰지 않는 artifact 방식이므로 contents 쓰기는 애초에 불필요했다.
헤더 주석의 "deploy to gh-pages branch" 도 실제와 달라 함께 정정).

> **남은 전제**: 저장소에 **GitHub Pages 가 활성화돼 있지 않다** (`gh api .../pages` → 404).
> 권한을 고쳐도 Pages source 를 "GitHub Actions" 로 설정하기 전까지 deploy 는 실패한다.
> 이는 문서를 공개 웹에 게시하는 결정이므로 코드 변경으로 처리하지 않고 남겨 둔다.
>
> 층이 셋이었다는 점을 기록해 둔다 — **plugin 로드 → deploy 권한 → Pages 활성화**.
> 맨 아래 한 층이 막혀 있는 동안 위의 두 층은 존재조차 관측되지 않았다.

> **후속 (2026-07-25)**: 맨 아래 층을 열었다. Pages 활성화
> (`gh api -X POST .../pages -f build_type=workflow`) → run `30159275873` 에서
> **deploy 성공 (9s)**, 사이트 게시. `exclude_docs` 4종은 404, 주요 페이지는 200 확인.
> 덤으로 `hooks:` 전환이 *의도한 변환까지* 수행함이 처음 산출물로 확인됐다 — 원본 헤더가
> stale 한 3건(`index` 06-17, `CODE_INDEX` 07-21, `FEEDBACK` 06-17)이 게시본에서 각각
> git log 날짜(07-22 / 07-23 / 07-22)로 덮여 있다. **로드되는가**와 **일하는가**는
> 다른 층인데, 배포된 적이 없어 후자를 볼 수단이 그때까지 없었다.

### §2.29 — mypy strict 는 v0.11.11 이래 한 번도 적용된 적이 없다 (2026-07-25)

`pyproject.toml` 3중 불일치를 정리하려다 발견했다. `mypy-strict.yml` 은 이렇게 돌고 있었다:

```
mypy --no-incremental workflow-source/workflow_kit/     # cwd = REPO_ROOT
```

헤더 주석은 "workflow-source/ 의 pyproject `[tool.mypy] strict=true` read" 라고 적고
있었다. 사실이 아니었다. mypy 의 config 탐색은 **cwd 기준**이고, REPO_ROOT 의
`pyproject.toml` 은 v0.15.0+ 의 **의도된 root-level placeholder scaffold**(`eb62f37`)라
`[tool.mypy]` 가 없다. 그래서 탐색이 전부
실패하고 `Config File: Default` 로 떨어졌다 (`mypy -v` 의 `Config File:` 줄로 확인).

| 실행 | Config | 결과 |
|---|---|---|
| CI 가 하던 것 | **Default** | 0 errors / 117 files → green |
| 선언된 strict 를 물렸을 때 | `workflow-source/pyproject.toml` | **4 errors** |

**AST 로 전수 조사하니 mypy 호출 지점이 23곳이었고, 그 중 21곳이 config 없이 돌고
있었다** — CI, release-time gate(`release_pipeline.py`), Layer 2
gate(`release_status.py`), 그리고 `check_mypy_strict_v0_11_3~10` 등 "strict clean" 을
이름에 달고 있는 smoke 9종 전부. 처음엔 3곳인 줄 알고 목록을 손으로 적었다가 AST 로
훑고 나서야 규모를 알았다. **손으로 유지하는 목록은 반드시 빠진다.**

곁들여 `exclude` 결함: `"schemas/.*"` 는 anchor 가 없어 경로 어디서든 매치했다.
의도한 대상은 `workflow-source/schemas/`(실은 `.py` 가 **0개**)였는데, 실제로 잘라낸
것은 `workflow_kit/common/schemas/` 의 **실소스 20 file** 이었다 (117 → 97). exclude 는
crawl 대상에서 조용히 빼므로 줄어들었다는 사실이 어디에도 남지 않는다.

**v0.11.11 릴리스 노트의 인과 설명도 틀렸다** — mypy 는 config 를 merge 하지 않고,
정확히 하나만 고른다. "sub-package config 와의 merge 회피" 라던 조치는 실제로는 *설정을
통째로 잃는* 조치였고, 46 → 0 은 코드가 좋아져서가 아니라 검사를 안 하게 돼서였다.
해당 노트에 정정 블록을 넣었다 (`600f6e1` 의 tmpfs 귀인 정정과 같은 처리).

가장 나쁜 층은 재발 방지 test 였다. `check_mypy_strict_ci_v0_11_11.py` case 8 은 CI
invocation 을 **충실히 재현**하고 exit 0 을 확인했다. 깨진 실행을 정확히 복제했으니
green 이었다. **재현은 검증이 아니다** — 무엇을 재현하는지도 함께 봐야 한다.

조치:

| # | 내용 |
|---|---|
| 1 | `exclude` 를 디렉터리 경계에 anchor (cwd 두 곳 모두 대응) → 검사 대상 97 → **117 file** |
| 2 | mypy 호출 **23곳 전부** `--config-file` 명시 |
| 3 | 드러난 `unused-ignore` 4건 제거 (`testing` / `profiling` / `metadata` / `release_status`) |
| 4 | 신규 `check_mypy_config_actually_loaded.py` (6 case) — AST 전수 조사 + `mypy -v` 의 `Config File:` 줄 실측 + **음성 대조**(config 를 빼면 정말 Default 로 떨어지는가) |
| 5 | CI run 블록에 `Config File:` 가드 — 기대 경로가 아니면 `::error::` + exit 1 |

3번은 2번과 **짝**이다. 그 ignore 들이 unused 였던 이유가 config 의
`ignore_missing_imports = true` 이므로, config 없이 돌리면 되레 진짜 에러 3건이 뜬다.
4·5번 가드가 그 전제를 강제한다.

주입 검증 (전부 확인): exclude anchor 되돌림 → 2 case FAIL / CI 에서 `--config-file`
제거 → 1 case FAIL (주석에 남은 `config-file` 문자열에 속지 않는다) / CI run 블록에서
제거 → `::error::` + exit 1.

### §2.30 — YAML·스킬·MCP 를 파서와 도구로 검사한다 (2026-07-25)

§2.29 를 끝내고 보니, 이 저장소에서 **YAML 을 읽는 유일한 코드가 자체 정규식
파서**였다. 그리고 그 안에 결함이 있었다:

```python
fallback_pattern = re.compile(r"mypy[^\\n]*--no-incremental[^\\n]*workflow_kit/")
```

raw string 이라 문자 클래스가 `[^\n]`(줄바꿈 제외)이 아니라 **`[^\\n]`(역슬래시와
문자 `n` 제외)** 로 해석된다. 여러 줄 invocation 을 허용하려던 의도가 전혀 동작하지
않았다. 더 나쁜 것은 이 fallback 이 도는 조건이 **PyYAML 부재**였고, `pyyaml` 은
dev extra 에 선언돼 있지 않았다는 점이다 — 즉 *CI 에서는 항상 결함 있는 경로*로 돌았다.

조치 (도구 선택: PyYAML + actionlint, Node 의존성 0 / 서버 기동이 필요한 층만 Node):

| 층 | 산출물 | 무엇을 보는가 |
|---|---|---|
| 구문·스키마 | `check_yaml_surfaces.py` (4 case) | 전 YAML 파싱, 워크플로우 스키마, **자체 파서 금지**, errexit 안전 |
| 스킬 | `check_harness_skill_frontmatter.py` (4 case) | harness frontmatter 7종 — `name` 형식/`description` 길이/`mode`·`permission` enum |
| MCP 정적 | `check_mcp_tool_descriptors.py` (4 case) | tool 13개가 MCP 스펙 모양인가 + `tool_count` 선언↔사실 |
| 워크플로우 셸 | `.github/workflows/actionlint.yml` | actionlint + shellcheck |
| MCP 동작 | `.github/workflows/mcp-inspector.yml` | **서버를 실제로 띄워** `tools/list` ↔ 커밋된 descriptor 대조 |

자체 정규식 YAML 파서 3곳(`_read_yaml_simple`, `_read_yaml_text_based`,
`_read_yaml_block`)을 전부 `yaml.safe_load` 로 교체하고, 재등장을 금지하는 규칙을
두었다. 그 판정은 **이름이 아니라 동작**으로 한다 — 처음에 `def _read_yaml*` 같은
이름으로 잡았더니 내부를 이미 고친 함수까지 걸려 위양성이 났다.

**실측**: 살아 있는 MCP 서버가 노출하는 tool 13개가 커밋된 descriptor 13개와
이름·`inputSchema` 까지 완전히 일치. harness frontmatter 7종 모두 유효한 YAML 이고
보간 0건.

#### 내가 틀렸던 것 2건 (지우지 않고 남긴다)

1. **actionlint 이 §2.27 사고를 잡을 것이라고 적었는데, 잡지 못한다.** `set -e` 아래
   `rc=$?` 모양을 그대로 재현해 돌려 보니 exit 0 이었다 — shellcheck 에는 "errexit
   때문에 이 줄에 닿지 못한다"는 규칙이 없다. 그 부류의 유일한 방어선은
   `check_yaml_surfaces.py` 4번 case 다. actionlint 은 다른 층에서 값을 한다 —
   도입 시점에 실제 결함 6건(SC2086 ×2, SC2129, SC2002, SC1072/1073)을 찾았다.
2. **shellcheck 없이 actionlint 은 `run:` 블록을 아예 건너뛰고 조용히 exit 0** 이
   된다. 이번 사이클이 내내 다룬 "조용히 초록" 그 모양이라, 워크플로우가 shellcheck
   존재를 명시적으로 확인하게 했다. (덧붙여 그 확인을 설명하는 주석을
   `# shellcheck` 로 시작했다가 shellcheck 가 directive 로 파싱해 SC1072/1073 을
   냈다 — 도구를 도입하는 커밋이 그 도구에 걸린 셈이다.)

### §2.31 — 진입점에 규칙을 주입한다면서, 렌더러가 규칙을 손으로 들고 있었다 (2026-07-27)

발표자료를 만들다가 "규칙은 한 벌만 쓰고 도구별로 내보낸다" 고 적어 놓고, 정말
그런지 확인해 봤다. 아니었다.

하네스 진입점(`CLAUDE.md` / `AGENTS.md` / `GEMINI.md` …)은
`bootstrap_lib/harnesses/renderers.py` 의 하네스별 f-string 이 만든다. 그런데 그
파일은 정본 `core/global_workflow_standard.md` 를 **한 번도 읽지 않는다**. 규칙
문장이 렌더러 안에 6벌 복제돼 있었고, 예상대로 갈라져 있었다:

| 규칙 | 도입 전 | 도입 후 |
|---|---|---|
| §1 검증하지 않은 결과는 완료로 확정하지 않는다 | 12개 진입점 중 6개 | 주요 진입점 7종 전부 |
| §3 상태값 4종 | 12개 중 6개 | 주요 진입점 7종 전부 |
| **§8 memory 갱신 → commit → push** | **12개 중 2개** | **주요 진입점 7종 + AGENTS.md / 보조 SKILL 2종** |

§8 은 표준이 안티패턴까지 적어 둔 규칙인데, 정작 그걸 지켜야 할 에이전트 대부분이
규칙을 받지 못하고 있었다. claude-code · codex · gemini-cli · antigravity ·
minimax-code · pi-dev · aider · opencode 중 어느 진입점에도 종료 순서가 없었다.

**같은 결함이 한 층 더 있었다.** 이 저장소의 배포본 사본 `ai-workflow/core/` 21개
문서가 전부 정본과 갈라져 있었다. `global_workflow_standard.md` 는 최종 수정일이
2026-05-01 에 멈춰 있었고 (정본 2026-07-21), **빠진 것이 하필 §8 전체**였다.
진입점이 "표준 문서" 라고 가리키는 것이 이 사본이니, 에이전트는 2개월 낡은 규칙을
읽고 있었던 셈이다. 사본 21개는 순수 stale 이었다 — 사본 쪽에만 있는 내용은 없었다.

조치:

| 층 | 산출물 | 무엇을 보장하는가 |
|---|---|---|
| 추출 | `workflow_kit/common/standard_rules.py` | 정본 §1 · §3 · §8 을 파싱해 진입점 블록을 **생성**. 추출 실패 시 `StandardParseError` — 조용한 기본값 없음 |
| 배포 | `workflow_kit/common/_standard_rules_snapshot.py` | wheel 설치(=`SOURCE_ROOT is None`)에서도 규칙을 잃지 않는 **생성된** 스냅샷 |
| 검사 | `tests/check_standard_single_source.py` (5 case) | 스냅샷↔정본 / 렌더러 리터럴 부재 / **실제 bootstrap 산출물** / 배포본↔정본 / 탐지기 자활 |
| 규약 | `check_convention_single_source.py` 에 5번째 규약 등록 | 렌더러 밖의 어떤 production 코드가 §8 문장을 복제해도 걸린다 |

검사 3번은 렌더러를 직접 호출하지 않고 **temp 에 실제 bootstrap 을 돌려** 산출물을
본다. 렌더러가 옳아도 배선이 빠지면 파일에는 안 실리는데, 이 사이클에서 반복해서
샌 곳이 정확히 그 조립 단계였기 때문이다.

**되주입 확인 3건** — 재발 방지 검사는 결함 코드에서 실패해야 의미가 있다:
렌더러에 규칙을 하드코딩하면 2·3번이, 배포본에서 §8 을 지우면 4번이, 스냅샷을
손으로 고치면 1번이 각각 FAIL 한다. 확인 후 원복했다.

**한계 (과장하지 않는다)**: 2번 case 는 *문장 리터럴* 만 본다. 렌더러가 규칙을
의역해 새로 쓰면 못 잡는다. 의미 비교는 위양성을 낳고, 위양성 내는 검사는
무시당한다. 대신 3번이 "정본 문장이 산출물에 그대로 있는가" 를 보므로 의역본만
남기면 3번에서 걸린다. 또 `goose`(config-only) · `custom`(빈 템플릿) ·
`codex`(pi-dev 와 `AGENTS.md` 파일 소유가 겹친다) 는 이유를 적어 면제했다 —
특히 codex/pi-dev 의 파일 충돌은 이번에 드러난 별도 결함이다.

### §2.32 — 린터가 "읽지 못한 문서" 를 통과로 셈하고 있었다 (2026-07-27)

§2.31 을 하다가 이 저장소로 린터를 돌려 봤더니 이랬다:

```json
{ "status": "ok", "summary": { "total_issues": 0 },
  "warnings": ["Failed to parse handoff: No such file or directory ..."] }
```

**`session_handoff.md` 가 없는데 `ok` 다.** 부재를 warning 한 줄로 흘리고 `{}` 로 계속
진행했기 때문이다. 그러면 그 뒤의 정합 검사(state ↔ handoff ↔ backlog 의 `in_progress`
대조)가 **빈 집합끼리 비교**하게 되어 언제나 통과한다. 덜 본 것이 통과로 셈해진 것이다.

같은 시각 `session-start` 는 같은 파일 때문에 `missing_required_document` 로 **아예 실행조차
되지 않고 있었다.** 한쪽은 없어서 못 돌고 한쪽은 없는 줄도 모르고 green 이었다.

조치 (`workflow_kit/common/linter.py`):

| 상황 | 이전 | 지금 |
|---|---|---|
| 문서 부재 | `warnings` + `status: ok` | `issues[].code = missing_required_document`, severity high |
| 문서 파손 | `warnings` + `status: ok` | `issues[].code = document_parse_failure` (원인이 다르니 code 를 나눈다) |
| 요약 | — | `summary.missing_documents` 신규 — 0 이 아니면 나머지 수치는 *그만큼 덜 본 결과* |

issue description 에 **"이 문서를 읽는 검사(state ↔ handoff in_progress 대조)가 무력화된 채
통과한다"** 를 적었다. 무엇을 못 봤는지가 결과에 남아야 한다.

**곁가지로 하나 더 나왔다.** 링크 검사가 `path.exists()` 로만 걸러 디렉터리에도 True 가 되어
`read_text()` 가 `IsADirectoryError` 로 터졌고, 러너의 최상위 catch 가 그걸 `runtime_error`
로 바꾸는 바람에 **문서 부재 issue 자체가 보고되지 못했다.** `is_file()` 로 정정했다.
재발 방지 test 2건(`check_workflow_linter.py`)을 넣고, 되돌려 주입해 FAIL 하는 것을 확인했다.

### §2.33 — 진입점을 배포하면서 정작 이 저장소에는 없었다 (2026-07-27)

`CLAUDE.md` 도 `AGENTS.md` 도 없었다. 11개 하네스용 진입점을 만들어 배포하는 저장소가
자기 진입점은 한 번도 만든 적이 없다. `docs/archive/AGENTS.md` 의 deprecation 배너는
"현재는 **루트의 AGENTS.md** 가 canonical" 이라고 적고 있는데, 그 루트 파일이 없다.

§2.31 의 렌더러로 생성해 넣었다. 규칙 블록(`## 작업 원칙` / `## 세션 종료 순서`)은 정본에서
나오므로 손대지 않는다. 다만 **상태 문서 경로 5~8곳만** `active/<branch>/` 로 조정했고,
그 이유를 파일 상단에 적었다 — bootstrap 의 기본 산출물은 평평한 `active/` 인데 이 저장소는
브랜치별이기 때문이다. 이 불일치 자체가 남은 결함이다 (아래).

`session_handoff.md` 도 만들었다. §2.32 가 잡아낸 그 파일이다. 결과:

| | 이전 | 지금 |
|---|---|---|
| `workflow-linter` | `ok` (문서가 없는데) | `ok` (문서가 있어서) — 그 사이 한 번 `warning` 을 거쳤다 |
| `session-start` | `error: missing_required_document` | `ok` — 이 저장소에서 처음 돈다 |

**남은 결함 3건 (이번에 고치지 않고 기록한다)**:

1. `AGENTS.md` 를 codex 와 pi-dev 가 함께 쓴다 — 둘 다 고르면 나중 렌더러가 이긴다.
2. bootstrap 은 평평한 `active/` 를 만드는데 이 저장소는 `active/<branch>/` 다. 브랜치별
   레이아웃이 배포 경로에는 반영되지 않았다.
3. `WORK_STATUS_RE` 는 대문자 task ID 만 받고 `TASK_ID_PATTERN` 은 소문자 브랜치 세그먼트를
   허용한다 (`TASK-2026-07-27-main-001`). 같은 규약의 두 정규식이 갈라져 있다 — §2.24 가
   등록한 부류와 같은 모양이라 규약 registry 후보다.

### §2.34 — 발표자료의 주장을 저장소의 규범으로 옮긴다 (2026-07-27)

§2.31~§2.33 은 전부 같은 자리에서 나왔다. **발표자료에 "우리는 이렇게 한다" 고 적어
놓고 저장소를 열어 보니 아니었던 것들**이다. 그렇다면 문제는 개별 결함이 아니라, 그
주장들이 **어디에도 규범으로 적혀 있지 않아 아무것도 그것을 지키지 않았다**는 점이다.
발표자료는 검사 대상이 아니니까.

그래서 덱의 내용을 설계 문서로 승격했다.

**신규 `core/workflow_design_principles.md`** — `global_workflow_standard.md` 가
*무엇을 하는가* 를 정한다면, 이 문서는 *왜 그렇게 하는가* 를 정한다:

| 절 | 내용 |
|---|---|
| §1 | 무엇이 새는가 — 시간 · 도구 · 사람 · 품질 4축과 대응 원리 |
| §2 | 설계 원리 3층 — 상태를 세션 밖에 / 규칙은 한 벌만 / 검사가 규칙을 지킨다 |
| §3 | 규칙을 쓰는 법 — "검사로 옮길 수 있는 문장인가". 옮길 수 없으면 소망이다 |
| §4 | 운영 규율 — 세션 열기 · 하루 한 사이클 · 맡기기 전 3가지 · 인계 · 협업 · 얇게 시작 |
| §5 | **자기 적용** + 원리 ↔ 검사 매핑 표 |

§2.3 에는 이번 사이클에서 반복해 배운 검사 설계 규칙을 명문화했다 — 커밋을 막지 않아도
된다(막는 검사부터 만들면 우회한다) · 위양성 내는 검사는 무시당한다 · 재발 방지 검사는
결함 코드에서 실패해야 한다 · **덜 본 것을 통과로 셈하지 않는다**(§2.32 가 그 사례다).

**표준에 §8.4 자기 적용 신설** — "배포하는 것을 우리가 쓰지 않으면 그것이 동작하는지 알
방법이 없다". 새 규칙을 표준에 넣을 때는 **그 규칙을 검사할 방법을 함께 제안**하고,
방법이 없으면 규칙이 아니라 가이드로 분류한다.

**신규 `tests/check_self_application.py` (5 case)** — 다짐을 검사로 바꾼다:

1. 원리 ↔ 검사 매핑 표가 가리키는 검사 파일이 전부 실재한다 (없는 검사를 가리키는 표는
   지켜지는 것처럼 보이는 장식이다)
2. 루트 진입점이 존재하고 정본에서 생성된 §1 · §8 을 담는다
3. 브랜치 메모리에 state / handoff / backlog 가 모두 있다
4. 자기 린터가 자기 저장소에서 issue 0 으로 통과한다
5. 자기 session-start 가 자기 저장소에서 `ok` 로 돈다

**되주입 확인 4건**: 루트 진입점 삭제 → 2번 FAIL. handoff 삭제 → 3·4·5번 동시 FAIL.
매핑 표를 없는 검사로 조작 → 1번 FAIL. 진입점에서 §8 문장 제거 → 2번 FAIL.

설계 원칙 문서는 `DEFAULT_CORE_DOCS` 에 넣어 소비자 프로젝트에도 함께 배포한다. 규칙만
받고 원리를 못 받으면, 도입한 팀이 규칙을 조정할 때 근거 없이 조정하게 된다.

**커밋 직전에 하나 걸렸다.** 2번 case 가 처음에 `AGENTS.md` 도 요구했는데, `.gitignore` 의
"Workflow layer (selective tracking)" 이 `/AGENTS.md` · `/GEMINI.md` · `/ANTIGRAVITY.md` 를
의도적으로 제외하고 있었다. 그대로 푸시했으면 **깨끗한 clone 과 CI 에서 반드시 실패**한다
— 내 워킹트리에만 있는 파일을 요구하는 검사였다. §2.27 이 "재현 불가능한 환경에서 잰
수치는 지표가 아니다" 라고 적어 둔 것과 같은 함정이다. 추적되는 진입점만 요구하고,
나머지는 *있으면 내용까지 검증* 으로 낮췄다. AGENTS.md 를 지우고 돌려 통과를 확인했다.

### §2.35 — 남겨 뒀던 결함 3건 + CI 를 상시 red 로 만들던 자기참조 (2026-07-27)

§2.33 에서 "이번에 고치지 않고 기록한다" 고 적어 둔 3건과, main 을 계속 red 로
만들던 검사 1건을 함께 정리했다.

**(1) `AGENTS.md` 파일 소유 충돌 — 덮어쓰기에서 합치기로.** codex/opencode 와 pi-dev 는
둘 다 root `AGENTS.md` 를 읽는다. 코드에는 이미 자백이 적혀 있었다:

```python
# If both are selected, Pi's version will overwrite or vice versa.
# Usually only one harness is selected for a project.
```

"보통 하나만 고른다" 는 가정이지 보장이 아니다. 둘 다 고르면 나중에 도는 pi-dev 가
codex 판을 조용히 덮어썼고, manifest 는 `codex_agents` / `pi_dev_agents` 두 key 로
**두 파일이 생긴 것처럼** 보고했다. 파일이 하나뿐이면 답은 덮어쓰기가 아니라 합치기다
— codex 판 뒤에 pi-dev 전용 장을 이어 붙이고(`pi_dev_agents_supplement`), 이미 base 에
있는 생성 블록(§8)은 빼서 **한 파일 안의 사본**도 만들지 않는다. 재실행에 멱등이다.
충돌 사실은 manifest `warnings` 로 알린다.

**(2) bootstrap 이 평평한 layout 을 만들고 있었다.** 런타임(`state_path_for_workspace`)은
branch-scoped 를 먼저 보고 legacy 로 fallback 하는데, 정작 부트스트랩이 legacy 만
만들었다. 즉 **브랜치별 분리는 이 저장소에만 있고, 우리가 배포한 프로젝트에는 없었다**
— 발표자료가 "갈라 두면 서로 덮어쓰지 않는다" 고 말하는 바로 그 지점이다.

| | 이전 | 지금 |
|---|---|---|
| 브랜치 상태 | `active/state.json` (공유) | `active/<branch>/{state.json, session_handoff.md, work_backlog.md, backlog/, sessions/}` |
| 프로젝트 정체성 | 〃 같은 곳 | `active/{PROJECT_PROFILE, PURPOSE, *_assessment}` (브랜치 무관 공유) |
| 기존 평면 프로젝트 | — | **그대로 둔다** — 재실행이 병렬 상태를 만들면 "진짜 상태는 어느 쪽인가" 가 모호해진다 |

대상이 git 저장소가 아니면 `main` 으로 고정한다. `branch_for_workspace` 를 그대로 쓰면
*내가 feature 브랜치에서 실행했다는 이유로* 남의 새 프로젝트에 `active/feature-x/` 가
생긴다 — 호출 위치가 답을 바꾸는 그 함정이다.

진입점 문서의 경로 93곳도 `<branch>` 로 맞추고, placeholder 의 뜻을 문서에 한 줄로
적었다. 설명 없는 placeholder 는 에이전트가 그대로 열려고 한다.

**(3) task ID 정규식이 갈라져 있었다.** `WORK_STATUS_RE` 는 `[A-Z0-9-]+` 로 **대문자만**
받는데 `TASK_ID_PATTERN` 은 branch slug 에 소문자를 허용한다. 그래서
`TASK-2026-07-27-main-001` 같은 *정본 문법에 맞는 ID* 를 handoff 의 Work Status 줄에서
통째로 놓쳤다. `WORK_ITEM_ID_PATTERN` 으로 문법을 명시하고 셋의 포함 관계를 주석에
적었다. 같은 파일 안의 분기라 리터럴 검사(파일 단위)로는 안 잡히므로 **동작으로**
고정했다 (`check_convention_single_source` 5번째 case).

**(4) CI 를 상시 red 로 만들던 자기참조.** `check_release_summary_v0_11_15` 의 case 7 이
`ci_mypy=sanity` 를 요구했다. `sanity` 는 "최신 mypy-strict run 이 success 이고 그
headSha 가 HEAD 와 같다" 는 뜻인데, 이 검사는 smoke 의 일부로 **바로 그 commit 의 CI
안에서** 돈다. 그 시점엔 같은 SHA 의 run 이 아직 없다. 즉 **구조적으로 통과할 수 없는
단언**이었고, 로컬에서도 push 하고 CI 가 끝나야만 green 이었다.

검사의 본래 목적은 "cmd_release 가 verdict 를 summary 에 제대로 싣는가" 라는 *계약*이다.
환경 관찰과 계약 검증을 분리했다 — case 7 은 verdict 가 *알려진 값 집합에 드는가* 만
보고, 매핑 자체는 verdict 를 **주입해서** 검증한다 (case 7b, 기존 case 8 과 같은 방식).
`gh` 유무와 무관하게 통과하는 것을 확인했다.

**신규 검사 2 case** (`check_standard_single_source` → 7 case):
같은 파일을 쓰는 두 하네스를 함께 골라도 지침이 사라지지 않는가 / **진입점이 가리키는
경로에 실제로 파일이 있는가**. 후자는 도입하자마자 `sessions/` 를 잡아냈다 — 문서는
"항상 먼저 읽을 문서" 로 안내하는데 bootstrap 이 그 디렉터리를 만들지 않고 있었다.

되주입 확인: 평평한 layout 복귀 → case 7 FAIL, pi-dev 덮어쓰기 복귀 → case 3·6 FAIL,
대문자 전용 정규식 복귀 → 규약 5번 FAIL.

**(5) 정리하는 중에 같은 부류를 하나 더 만났다.** 위 4건을 끝내고 세션 종료 절차대로
`backlog-update` 로 작업을 등록하려는데, 스킬이 `status: ok` 를 내면서 **아무것도 쓰지
않았다**. `--mode auto` 가 `--task-id` 만 보고 무조건 update 로 잡은 탓이다:

```python
requested_mode = "update" if args.task_id else "create"   # 존재 여부를 안 본다
```

없는 ID 였으니 `cannot_determine` 이 되어 write 가 0건인데, 반환은 `ok` 였다. auto 의
뜻은 "있으면 갱신, 없으면 생성" 이므로 **존재 여부를 실제로 보고** 정하도록 고쳤다.
재발 방지 test 는 없는 ID → create, 있는 ID → update 양방향을 함께 본다 (한쪽만 보면
반대로 넓어진 것을 놓친다).

이 건이 이번 사이클의 요약이기도 하다 — **덜 한 것을 통과로 셈하는 코드**는 문서 계층
(§2.32 린터)에도, 배포 계층(§2.31 렌더러)에도, 스킬 계층(여기)에도 똑같이 있었다.

**(6) 그리고 (4)를 한 번 더 틀렸다 — 같은 자리에 환경 의존이 둘이었다.** `ci_mypy=sanity`
만 고치고 push 했는데 CI 는 여전히 red 였다. 바로 옆줄의 `local_mypy=ok` 도 같은 부류다
— 이 값은 **test 를 실행한 환경에서 mypy 를 돌린 결과** 이지, `cmd_release` 가 verdict 를
summary 에 싣는가 하는 이 검사의 계약이 아니다. 로컬 시스템 `python3` (mypy 없음) 에서는
`FAIL` 이고 `.venv` 에서는 `ok` 다 — 어느 쪽이든 *검사의 계약과 무관한 값*이다. (4)와 같은
방식으로 분리했다: 값은 알려진 집합에 드는지만 보고, 매핑 자체는 case 7b 에서 주입으로
검증한다. mypy 가 있는 인터프리터와 없는 인터프리터 **양쪽에서** 통과하는 것을 확인했다.

> **정정.** 이 항목을 처음 쓸 때 "CI 의 smoke job 에서 `local_mypy=FAIL` 이었다" 고 적었는데
> **사실이 아니다.** 그 `FAIL` 은 내가 *로컬 시스템 python3* 로 돌려 본 결과였고, CI 의
> 실제 실패 사유는 (7) 의 excerpt 결함 때문에 어디에도 남아 있지 않았다. 관측하지 못한
> 값을 관측한 것처럼 적은 것이다 — 이 사이클이 내내 다루던 결함(덜 한 것을 통과로 셈하기)
> 을 서술에서 그대로 반복했다. 실제 원인은 §2.36 에서 계측해 확정했다.

**(7) 그 왕복을 한 번 더 쓰게 만든 관측성 결함.** CI 아티팩트에는
`=== Result: 0/1 PASS ===` 만 남아 무엇이 왜 실패했는지 알 수 없었다. `run_all_checks.py`
의 excerpt 가 *마지막 3줄* 을 자르는데, check 들이 끝에 요약 줄 + 빈 줄을 붙이고 개행으로
끝나는 문자열은 split 시 빈 원소가 하나 더 생기므로 **사유가 적힌 줄은 늘 뒤에서 4번째**
였다. 고정 위치 대신 실패 표지가 있는 줄을 고르도록 바꿨다 (표지가 없으면 마지막 비어
있지 않은 줄들로 fallback). 2026-07-25 세션이 "별도 과제" 로 남겨 둔 항목이고, 바꾸자마자
값을 했다 — 시스템 python3 전량 실행에서 7건의 실패 사유가 한 줄씩 그대로 보였다.

**(8) 그리고 (7)이 곧바로 둘을 더 찾아냈다 — 같은 자기참조가 넷이었다.** (6)을 커밋한 뒤
전량 smoke 를 돌리니 2건이 새로 red 였고, 고쳐 둔 excerpt 덕에 사유가 그대로 보였다:
`check_mypy_ci_cross_verify_v0_11_13` case 7 (`ci_sanity` 가 아니면 실패)과
`check_release_summary_v0_11_15` case 4 (`ci_mypy=no_local_verify` 고정). 둘 다
`_resolve_cross_verify_verdict` 매트릭스의 **`ci_sanity` 행 하나만 정답으로 박아 둔** 것이다.

이게 왜 문제인지가 이 사이클의 핵심이다. `ci_sanity` 는 "최신 mypy-strict run 이 success
이고 그 headSha 가 HEAD 와 같다" 는 뜻이므로, **커밋한 직후부터 그 커밋이 CI 를 통과할
때까지는 반드시 `ci_stale`** 이다. 즉 이 두 검사는 *push 직전 — 게이트가 정작 필요한
순간 — 에 구조적으로 통과할 수 없었다*. 실측: HEAD=`44b1b78`(미push) 일 때 최신 run 은
`1943026` 이라 verdict=`ci_stale`.

그래서 앞선 사이클의 "217/217 PASS" 는 **조건부**였다 — 커밋 *전에*, HEAD 가 마지막 green
run 과 같을 때 측정한 값이다. 반대로 CI 에서는 이 2건이 안 터진다. smoke job 에는
`GH_TOKEN` 이 없어 verdict 가 `absent`/`skipped` 로 떨어지고 그 값은 통과하기 때문이다.
**로컬에서만 red, CI 에서만 green 인 거울상**이었고, 그래서 지금까지 아무도 못 봤다.

처방은 (4)/(6)과 같다: 관측한 값은 *알려진 verdict 집합에 드는가* 만 보고, 매트릭스 자체는
주입으로 검증한다 (`check_release_summary` case 4b 신규 — 7행 전부). 느슨하게 푸는
변경이므로 **반대 방향으로 확인했다** — `ci_sanity + local skipped → sanity` 로 결함을
주입하니 case 4b 가 FAIL 한다.

### §2.36 — 그 red 의 원인을 CI 안에서 계측했다: mypy 가 아니라 `gh` 였다 (2026-07-27)

§2.35 (6) 은 원인을 `local_mypy` 로 지목했지만, 그건 **관측이 아니라 추측**이었다. CI 의
실제 실패 사유는 (7) 의 excerpt 결함 때문에 아무 데도 남지 않았고, 내가 근거로 삼은
`local_mypy=FAIL` 문자열은 *내 로컬 시스템 python3* 의 출력이었다. 그래서 계측했다.

**계측 방법.** `smoke.yml` 이 `branches: ["**"]` 에서 도는 성질을 이용해, 진단 probe 2개를
임시 브랜치에 얹어 CI 안에서 값을 찍고 아티팩트로 회수했다 (관측 후 브랜치 삭제). probe 는
실패 표지 줄로 출력해 (7) 에서 고친 `_error_excerpt` 가 400자까지 싣게 했다 — **(7)이 없었으면
이 계측 자체가 불가능했다**.

**결과 — mypy 는 처음부터 정상이었다.**

```
A4 raw rc=0 6.8s o='Success: no issues found in 119 source files' e=''
B1 clm 6.8s/ok=True/rc=0/n=0  6.8s/ok=True/rc=0/n=0  6.8s/ok=True/rc=0/n=0
B3 c7 sum=ci_mypy=skipped, local_mypy=ok, ready=false, ...
```

진짜 변수는 `ci_mypy=skipped` 였다. smoke job 의 `gh` 는 인증이 없어 `gh run list` 가 실패하고,
`_cross_verify_ci_mypy` 는 이를 `skipped` 로 돌려준다. 그런데 당시 case 4 는 `--skip-validate`
경로의 verdict 를 `no_local_verify` 로 **박아 놨다**. 그 행은 매트릭스상 CI verdict 가
`ci_sanity` 일 때만 나온다. 따라서 이 검사는 *`gh` 가 인증된 환경에서만* 통과할 수 있었다.

소요 시간이 이를 뒷받침한다. 실패 run 은 **7.04초**였는데, 이 검사가 정상 완주하면 mypy 를
4회 불러 CI 기준 **36.1초**다. 7.04초 = case 2 의 mypy 1회(6.8초) + case 4 즉시 실패. 
로컬에서 `gh` 를 실패하도록 바꿔 4.58초에 같은 자리·같은 사유로 재현했다.

즉 §2.35 (8) 에서 case 4 를 알려진 집합(= `skipped` 포함)으로 푼 것이 **바로 이 red 를 고친
조치**였다. 원인을 잘못 적어 두고도 처방은 맞았던 셈인데, 그건 운이지 방법이 아니다.

**교훈 2개.**

1. **관측하지 못한 값을 관측한 것처럼 적지 말 것.** 로컬 재현의 출력과 CI 의 출력은 다른
   증거다. (6)의 서술은 이 사이클이 내내 잡아 온 결함 — *덜 한 것을 통과로 셈하기* — 을
   문장에서 그대로 반복한 것이다.
2. **`gh` 인증 유무는 verdict 를 바꾸는 1급 환경 변수다.** CI 에서는 `skipped`, 로컬에서는
   `ci_sanity`/`ci_stale`. 이 축이 검사 통과 여부를 가르지 않도록, verdict 를 보는 검사는
   전부 집합 검사 + 주입 검증 형태여야 한다.

**부수 관측 (미조치).** probe 브랜치 이름 `probe/local-mypy-diag` 처럼 **`/` 가 들어간 브랜치**
에서 `check_branch_scoped_memory` 와 `check_self_application` 이 깨진다 — branch-scoped 경로가
`active/probe/local-mypy-diag/` 로 한 단계 더 중첩되고, task ID 에 `/` 가 섞인다. main 에서는
드러나지 않는 결함이다. 별도 과제로 남긴다.

### §2.37 — 세션을 닫으려다 상태 문서를 파괴하는 도구를 발견했다 (2026-07-27)

close-out 은 저장소 자체 skill 로 하는 게 dogfood 상 맞다고 보고 `backlog-update --apply` 를
썼다. 결과를 검토하니 **`state.json` 의 `recent_done_items` 가 10건 → 8건으로 줄고, 정작 새
항목은 추가되지 않았다.** 되돌려 손으로 갱신한 뒤 원인을 추적했다.

**(1) 데이터 소실 — 규약 사본, 세 번째.** `normalize.WORK_ITEM_ID_RE` 가 정본
`project_docs.WORK_ITEM_ID_PATTERN` 의 사본이었고, 문자 클래스가 **대문자 전용**이라
branch-scoped ID 의 소문자 브랜치 segment 에서 매치가 끊겼다.

```
TASK-2026-07-27-main-001  →  key 'TASK-2026-07-27-'
TASK-2026-07-27-main-002  →  key 'TASK-2026-07-27-'   ← 충돌
```

`dedupe_work_items` 가 이 key 로 중복을 지우므로 **같은 날짜의 task 가 전부 하나로 뭉개져
첫 개만 살아남는다.** 게다가 `state.json` 은 자기 내용이 다시 입력으로 돌아오는 구조라
**한 번 지워지면 영구 소실**이다. §2.35 (3) 에서 `WORK_STATUS_RE` 의 *같은* 결함을 고치며
정본을 세웠는데, 이 사본이 남아 있었다.

**(2) 그리고 검사가 왜 못 잡았는지.** §2.24 의 규약 단일 출처 검사에는 "task ID 정규식"
규약이 등록돼 있다. 그런데 탐지 리터럴이 문자열 `TASK-` 를 찾는 반면 사본은
`(?:TASK|WF)-` 라 **그 문자열이 등장하지 않았다** — 교대(alternation)로 쓰면 탐지를 통과한다.
리터럴을 `TASK[-|]` 로 넓히고 `rf"` 접두도 받게 했다. 더불어 면제 판정을 **코드에서만**
하도록 바꿨다 — 이전에는 정본 이름을 *주석에 언급만 해도* 사본이 통과했다(되주입으로 실측).

**(3)(4)(5) 같은 실행에서 함께 관측된 것.**

| 결함 | 원인 | 조치 |
|---|---|---|
| `written_paths` 가 4개 쓰고 2개만 보고 | task SSOT 와 `state.json` 경로 미기록 | 쓴 것을 전부 보고 (`git status` 와 4/4 일치 확인) |
| `--validation-result` 유실 | `result_note` 가 빈 경우에만 그 자리를 대신 | `- 검증 결과:` 로 별도 렌더 |
| handoff 빈 bullet 누적 | `- ` 는 strip 하면 `-` 라 `startswith("- ")` 실패 → **교체가 아니라 삽입** | 빈 bullet 을 목록 줄로 인정 + `- <라벨>:` 종결 조건 추가 |

마지막 건은 고치는 도중에 기존 검사 1건이 깨지며 드러난 게 있다 — **빈 bullet 이 우연한
방벽 역할**을 하고 있어서, 그것을 목록 줄로 인정하자 스캔이 다음 구간까지 흘러 라벨 자체를
항목으로 삼켰다. 종결 조건을 명시해 잡았다.

**회귀 테스트.** `check_writer_reader_roundtrip` 에 pair 를 추가했다 — 같은 날짜 task 3건이
`state.json` 재생성에서 살아남는가. **되주입 시 정확히 실패한다**(001 만 남고 002·003 소실).
넓힌 정본 검사도 실제 사본을 잡는 것을 되주입으로 확인했다.

**미조치.** `recent_done_items` 는 설계상 10개 상한이고 `state.json` 이 자기 입력으로
순환하므로, 상한을 넘긴 항목은 영구히 사라진다. 정렬이 시간순이 아니라 **오래된 항목이 남고
최근 항목이 밀릴 수** 있다 (E2E 에서 `TASK-2026-07-22-003` 이 밀려났다 — 상세는 이 노트와
task SSOT 에 남아 있다). 범위 밖이라 손대지 않았다.

> **이 사이클의 마무리로 적어 둘 것**: §2.35~§2.36 이 "환경에 기댄 판정" 을 다뤘다면, 여기는
> **"stable 로 선언된 도구가 상태 문서를 파괴한다"** 는 더 나쁜 형태였다. 그리고 그것을
> 찾은 계기는 *도구의 산출물을 그냥 믿지 않고 diff 를 읽은 것* 하나다.

### §2.38 — "최근 완료" 목록이 최신을 고른 적이 없었다 (2026-07-28)

§2.37 이 미조치로 남긴 건을 집었다. 증상은 "정렬이 시간순이 아니다" 한 줄이었는데, 열어 보니
**정렬 키라는 것이 애초에 없었다**. `recent_done_items` 는 이렇게 조립되고 있었다:

```
tasks_dir(파일명 사전순)  ++  daily index 잔여분(파일 날짜순)
```

그리고 두 번 잘렸다 — `_aggregate_from_appendonly_layout` 이 `[-10:]` (뒤 10개),
`build_workflow_state_payload` 가 `[:10]` (앞 10개). **자르는 방향이 반대**라 서로를 무효화했고,
어느 쪽도 *최신* 을 고르는 기준이 아니었다. 하필 뒤에 붙는 daily 잔여분이 저장소에서 가장
오래된 task 들이라, `[-10:]` 가 그것들을 통째로 "최근 완료" 자리에 앉혔다.

실측 (조치 전 `main`):

```
0 TASK-2026-07-25-main-001 …          5 Phase 10 MCP/JSON-RPC draft          ← 2026-04-24
1 TASK-2026-07-27-main-001 …          6 Phase 6 multi-agent delegation pilot ← 2026-05-01
2 TASK-2026-07-27-main-002 …          7 workflow 종료 단계 commit/memory …   ← 2026-06-30
3 TASK-2026-07-27-main-003 …          8 워크플로우 구성 점검 …               ← 2026-07-09
4 TASK-2026-07-27-main-004 …          9 2026-07-09 audit-session …           ← 2026-07-09
```

목록의 **뒤쪽 절반이 가장 오래된 5건**이고, 그 자리를 차지하느라 `TASK-2026-07-22-001~003`,
`TASK-2026-07-23-main-001` 이 밀려났다.

**세 번째 원인 — 파생물이 SSOT 를 밀어냈다.** 병합 순서가 `handoff §4` → `appendonly` 였다.
handoff §4 는 `sync_handoff_status` 가 append-only 로 쌓는 파생물이고 **상한이 없다**. 그게
앞에 있으면 가장 오래된 handoff 항목이 상한을 먼저 채운다. 되주입으로 실측하면 task 파일이
3개 있어도 목록 10칸이 전부 handoff 의 옛 항목으로 찬다.

**네 번째 원인 — 완료를 날조하고 있었다.** 같은 함수의 daily index fallback 은
`done/in_progress/blocked` 어느 목록에도 없는 ID 를 **무조건 `done` 으로** 되살렸다. 그런데
`migrate_active_to_appendonly.py` 는 legacy 이관 task 에 어휘 밖의 `status: recorded` 를 쓴다.
builder 는 그 값을 몰라서 세 목록 어디에도 넣지 않았고 → fallback 이 done 으로 되살렸다.
**실측 3건**(`TASK-2026-04-24-001` / `TASK-2026-05-01-001` / `TASK-2026-06-30-002`)이
완료로 보고되고 있었다. task 파일이 SSOT 인데 파생물인 daily index 가 그 판정을 덮어썼다.

**조치.**

| 항목 | 조치 |
|---|---|
| 상한 | `RECENT_DONE_ITEMS_CAP` 단일 출처. aggregate 는 자르지 않고, builder 가 한 번만 자른다 |
| 정렬 | `_task_recency_key` 도입 — `completed_at` → `updated_at` → `created_at` → ID 날짜 순 fallback. **최신순** 정렬 (소비자가 전부 앞에서 자른다) |
| 병합 순서 | task SSOT 를 앞, handoff 를 tail fallback 으로. `tasks_dir` 이 없는 legacy 저장소에서는 handoff 가 그대로 살아난다 |
| status 어휘 | `project_docs.TASK_STATUSES` 단일 출처 — `STATUS_RE` / `WORK_STATUS_RE` 가 여기서 조립된다 (같은 목록이 두 정규식에 리터럴로 복제돼 있었다) |
| 어휘 밖 status | 조용히 버리지 않고 `unknown_status_items` 로 드러낸다. task 파일이 있으면 daily index 가 판정을 덮어쓰지 못한다 |

`_task_recency_key` 는 **완료일이 아니라 근사값**이다 — 완료 시각을 담는 필드가 아직 표준이
아니라서 등록일로 대신한다. 앞의 두 필드를 먼저 보게 해 뒀으니, writer 가 나중에 채우면 별도
수정 없이 정확해진다. 근사라는 사실은 코드 주석에 남겼다.

**회귀 테스트.** `check_recent_done_items_order.py` 5건 (최신순+상한 1회 / 어휘 밖 status
되살리기 금지 / `planned` 완료 보고 금지 / 구형 index 항목의 날짜 자리 / handoff 가 SSOT 를
밀어내지 않음). **되주입 시 5/5 가 각각 다른 증상으로 실패**하는 것을 확인했다 — 상한 slice 를
되돌리면 최신 항목이 밀리고, fallback 을 되돌리면 `recorded`/`planned` 가 done 으로 나오고,
병합 순서를 되돌리면 10칸이 전부 handoff 항목이 된다. 픽스처는 손으로 쓰지 않고 프로덕션
writer(`upsert_backlog_entry`)로 만든다.

조치 후 실측 (`main`, 최신순):

```
0 TASK-2026-07-27-main-004    5 TASK-2026-07-23-main-001    (…)
1 TASK-2026-07-27-main-003    6 TASK-2026-07-22-003   ← 돌아왔다
2 TASK-2026-07-27-main-002    7 TASK-2026-07-22-002
3 TASK-2026-07-27-main-001    8 TASK-2026-07-22-001
4 TASK-2026-07-25-main-001    9 TASK-2026-07-21-001
```

`done_items` 는 104 → 101 로 줄었다. 줄어든 3건이 위의 `recorded` 다 — **없어진 게 아니라
완료가 아니었던 것**이고, 이제 `unknown_status_items` 에 보인다.

**미조치 2건.**

- `migrate_active_to_appendonly.py` 는 여전히 어휘 밖 `recorded` 를 쓴다. 이 값이 뜻하는
  "이관은 됐고 완료 여부는 확인 못 함" 은 실재하는 상태인데 표준 어휘에 없다. 어휘를 늘릴지
  (`global_workflow_standard.md` 개정) 기존 네 값에 맞출지는 governance 결정이라 남긴다.
  이미 만들어진 3건의 status 도 **완료 여부를 확인하지 않았으므로 손대지 않았다**.
  → **§2.39 에서 결정·조치했다** (어휘 확장이 아니라 축 분리).
- dashboard Panel 5(`collect_recent_releases`)는 브랜치별 `state.json` 을 이어 붙인 뒤 앞에서
  자른다. 브랜치 *안* 은 이제 최신순이지만 브랜치 *간* 정렬 키는 여전히 없다 (문자열에 날짜가
  없다). 별도 과제.

> 이번 건의 모양은 §2.24/§2.37 과 같다 — **같은 규약이 두 곳에 있으면 갈라지는 게 아니라 같이
> 틀린다**. 상한 `10` 이 두 곳에 있었고, status 어휘가 두 정규식에 복제돼 있었으며, 완료 판정이
> task 파일과 daily index 두 곳에 있었다. 셋 다 각자의 자리에서는 말이 됐다.

### 2.39. `status` 칸에 출처를 적고 있었다 — 진행 상태 축과 출처 축의 분리

§2.38 이 governance 결정으로 남긴 건이다. `migrate_active_to_appendonly.py` 가 표준 어휘 밖의
`status: recorded` 를 쓴다는 것까지는 §2.38 에서 확인했고, **어휘를 다섯으로 늘릴지 넷에
맞출지**가 미결이었다.

**결정: 어휘는 넷으로 유지하고, 축을 분리한다.**

`recorded` 가 실제로 뜻한 것은 진행 상태가 아니었다. "legacy `work_backlog.md` 에서 이관됐고
진행 상태는 모른다" — 이건 **출처(provenance)** 사실이다. 어휘를 다섯으로 늘리면 다섯 번째
값만 진행 상태가 아닌 채로 남고, `global_workflow_standard.md` 정본과 그걸 소비하는
프로젝트의 validator·bootstrap `choices` 를 전부 깨야 한다. 축이 둘이면 칸도 둘이어야 한다.

| 축 | 필드 | 규칙 |
|---|---|---|
| 진행 상태 | `status` | `planned`/`in_progress`/`blocked`/`done` **고정**. 판정 근거가 있을 때만 쓴다 |
| 출처 | `provenance` | `migrated-legacy` 등. 이 task 가 어디서 왔는가 |

**"근거가 없으면 비운다" 가 이 결정의 핵심이다.** 도구가 모르는 것을 채우면 그게 곧 날조다.
`migrate_active_to_appendonly.py` 는 이제 **release entry 에만** `status: done` 을 쓴다 —
발행된 릴리스 노트가 근거다. generic/session entry 에는 `status` 줄을 아예 쓰지 않고
`provenance` 만 남긴다.

**같은 결함이 builder 에도 있었다.** `_aggregate_from_appendonly_layout` 은 `status:` 줄이
없으면 `planned` 로 떨어뜨렸다. 그것도 판정이며, 이미 끝난 이관 task 를 "아직 시작 안 함"
으로 기록한다. 이제 `unknown_status_items` 에 `<ID>: <미기재>` 로 드러낸다 — "판정하지
않았다" 와 "어휘 밖 값을 적었다" 는 다른 사실이라 표식을 구분한다.

**그리고 그 노출은 아무 데도 안 보이고 있었다.** §2.38 이 만든 `unknown_status_items` 는
aggregate 의 반환값 안에만 있었고 **state payload 까지 오지 않았다**. `state.json` 을 읽는
사람에게도, skill 에게도 안 보였으니 조용히 사라지는 것과 다르지 않다 — 이번에 발견해
`session.unknown_status_items` 로 emit 한다 (빈 목록이어도 key 유지).

**기존 3건의 처리.** 완료 여부를 *판정 가능한 것만* 확정했다.

| task | 처리 | 근거 |
|---|---|---|
| `TASK-2026-06-30-002` | `status: done` | 본문에 commit 9건(`32185c7`…`4253eed`)이 결과와 함께 있고 **FULL mypy strict 도달(107 file clean)** 로 종료 |
| `TASK-2026-04-24-001` | `status` 미기재 | legacy 본문이 한 줄 요약뿐 — 판정 근거 없음 |
| `TASK-2026-05-01-001` | `status` 미기재 | 〃 |

뒤의 두 건은 **모르는 채로 남겨 두는 것이 조치**다. `unknown_status_items` 에 드러나고,
근거가 생기면 넷 중 하나로 채운다.

**후속 — 그 두 건을 곧바로 판정했다.** 노출된 김에 근거를 찾아봤더니 둘 다 남아 있었다.
그리고 찾는 과정에서 **이 두 항목이 애초에 task 가 아니었다**는 게 드러났다. legacy
`work_backlog.md` 에서 둘은 `### Historical archives` 아래의 **아카이브 포인터 한 줄**이었고,
이관 도구가 `### [[path]] {#anchor}` block 을 일괄로 task 화하면서 포인터까지 task 가 됐다.
그래서 본문이 한 줄이었던 것이다 — 내용은 가리키는 대상에 있었다.

| task | 판정 | 근거 |
|---|---|---|
| `TASK-2026-05-01-001` | `done` | `archived/codex/phase6/backlog/2026-05-01.md` frontmatter `상태: done` + `session_handoff.md` `Status: done`(TASK-038~045 및 WF-042-01~06 전부 done, Next Actions 전 항목 `[x]`, "No active blocker") + 산출물 실재(`check_source_without_runtime_layer.py`, `workflow-source/`↔`ai-workflow/` 분리 = 현재 저장소 구조) |
| `TASK-2026-04-24-001` | `done` | `archived/gemini/phase10/session_handoff.md`(Updated **2026-05-04**, 그 브랜치 메모리의 최신 기록) Work Status 에 `TASK-001 표준 AI 워크플로우 초기 도입: done` 명시 |

두 번째 건은 **기록 셋이 서로 어긋나 있었다**: handoff(05-04)는 `done`, work_backlog §3
체크박스(05-02)는 미체크, day file(04-24, 문서 상태 `draft`)은 `planned` 인 채 방치. 같은
브랜치의 `2026-04-26.md` 는 `done` 으로 갱신돼 있어 그 날짜 파일만 안 고쳐진 것으로 보인다.
**가장 나중이면서 유일하게 명시적인 상태 선언인 handoff 를 따랐고**, 어긋난다는 사실 자체는
task 파일에 남겼다. 셋이 왜 어긋났는지는 알 수 없다 — 이것도 §2.38/§2.39 와 같은 부류다.

> **관측**: 이관 도구는 `### Historical archives` 같은 **비-task section 도 task 로 만든다**.
> 이 저장소에서는 2건이고 둘 다 판정으로 닫혔지만, 다른 저장소에서 같은 도구를 돌리면
> 아카이브 인덱스가 그대로 task 로 늘어난다. → **§2.40 에서 조치했다.**

### 2.40. 구분 heading 을 몰라서 두 가지를 동시에 잃고 있었다

§2.39 후속에서 관측한 건이다. legacy `work_backlog.md` 의 `## 최근 작업 백로그` 안에는
`###` 가 **두 종류** 섞여 있다.

```
### [[release/v0.5.1/backlog/2026-06-05.md]] {#release-v0-5-1}   ← entry
- 2026-06-05: v0.5.1 self-dogfooding bootstrap …

### Historical archives {#historical-archives}                    ← 구분 heading
### [[codex/phase6/backlog/2026-05-01.md]] {#codex-phase6}        ← entry (아카이브 포인터)
- 2026-05-01: Phase 6 multi-agent delegation pilot
```

`migrate_active_to_appendonly.py` 의 파서는 `### [[path]] {#anchor}` 만 알았다. 두 번째
종류를 만나면 `ENTRY_RE` 가 매치되지 않고, 그대로 **직전 entry 의 body 로 흘러갔다**.

**손실 1 — 본문 오염.** 실측: `TASK-2026-06-05-001.md` 의 Implementation 절 안에
`### Historical archives {#historical-archives}` 가 그대로 박혀 있었다. 그 entry 의 내용이
아니라 *다음 묶음의 시작*을 알리는 줄이다.

**손실 2 — 소속 소실. 이쪽이 실제로 비쌌다.** 아카이브 포인터와 실제 작업 항목은 형태가
같다 — 둘 다 `### [[path]] {#anchor}` + 한 줄 요약. 구분할 단서는 위의 구분 heading
**하나뿐**인데 파서가 그걸 버렸다. 그래서 이관 후에는 알 방법이 없었고, §2.39 에서 그
2건이 "본문 한 줄짜리 정체불명 task" 로 남아 완료 판정에 세션 하나를 소모했다. **판정이
어려웠던 게 아니라, 판정에 필요한 사실이 이관에서 버려진 것이다.**

**조치.**

| 항목 | 조치 |
|---|---|
| 파서 | `GROUP_HEADING_RE` — entry 형태가 아닌 `###` 는 **직전 entry 를 닫고** 현재 소속을 갱신 |
| 소속 보존 | `Entry.group` → task frontmatter 의 `source_group:` (없으면 key 자체를 안 씀) |
| 노출 | 이관 summary 에 `[확인 필요] 구분 heading 아래의 entry` 로 묶음별 목록 출력 |
| 판정 | **하지 않는다.** "아카이브 포인터면 task 가 아니다" 는 프로젝트 결정이라 도구가 정하지 않고 드러내기만 한다 (§2.39 와 같은 원칙) |

기존 산출물도 정리했다 — `TASK-2026-06-05-001.md` 의 유출 heading 제거, 포인터 2건에
`source_group: Historical archives` 기록.

**검증.** 실제 legacy 파일(`work_backlog.md.bak`, git 이력에서 복원)로 확인: entry
**93건 그대로**(삼킴 0), body 오염 **1건 → 0건**, 포인터 2건에 소속 부여.
신규 `check_migration_group_heading.py` 6건 + **되주입 3건이 각각 다른 증상으로 실패**
(파서 인식 제거 → 오염·소속 3건 동시 실패 / frontmatter emit 제거 → 소속만 실패 /
실파일 heading 복원 → 전수 검사만 실패).

> §2.39 는 "판정 근거가 없으면 채우지 말라" 였고, 이건 그 앞 단계다 — **판정 근거를
> 애초에 버리지 말 것.** 이관은 형식을 바꾸는 일이지 사실을 줄이는 일이 아니다.

**검사층.** `check_task_status_axis_separation.py` 6건 신규 (이관 도구가 근거 없이 status 를
쓰지 않는가 / release 에만 done 인가 / 어떤 kind 든 어휘 안인가 / 미기재를 기본값으로 채우지
않는가 / state.json 까지 완료로 새지 않는가 / 실저장소 task 103건 전수 어휘 검사).
`check_appendonly_memory_layout.py` 의 frontmatter 규칙도 함께 고쳤다 — `status` 를 필수에서
빼는 대신 **`status` 와 `provenance` 중 하나는 필수**, 그리고 `status` 가 있으면 어휘 안.

**되주입 4건, 각각 다른 증상으로 실패 확인**: 이관 도구를 `recorded` 로 되돌리면 어휘 검사가
잡고, builder 를 `planned` fallback 으로 되돌리면 미기재 검사가 잡고, 실파일에 `recorded` 를
넣으면 layout 검사와 전수 검사가 각각 잡고, `provenance` 를 지우면 "둘 다 없다" 가 잡는다.

> §2.23 이 판정 지표에 대해 한 것(`*_source` / `*_measured` 를 함께 낸다)을 task 상태에 대해
> 한 셈이다. **판정과 그 근거는 다른 칸에 있어야 하고, 근거가 없으면 판정하지 않는다.**

### 2.41. 상한 없는 의존성이 측정을 갈아 끼웠다 — mcp 2.0.0 이관

문서 2줄만 바꾼 커밋(`23874d1`)에서 `mypy-strict` 가 red 로 넘어갔다. **커밋 내용과
무관했다.** `mcp-sdk` extra 가 `mcp[cli]>=1.0` 로 상한이 없어, 그 사이 릴리스된 mcp
2.0.0 을 러너가 집은 것이다 (CI 설치 로그에 `mcp-2.0.0`). 같은 소스에 버전만 갈아 끼워
재현했다 — `1.28.1` green / `2.0.0` 에서 fail.

**보고된 에러는 원인에서 한 칸 떨어져 있었다.**

```
mcp_v1_server.py:27: error: Returning Any from function declared to return "Callable[..., Any]"
```

읽으면 타입 문제 같지만 사실은 아니다. mcp 2.0.0 은 `mcp.server.fastmcp` **모듈 자체를**
없애고 `mcp.server.mcpserver.MCPServer` 로 옮겼다. `try: from mcp.server.fastmcp import
FastMCP` 가 항상 `ImportError` 로 떨어져 `HAS_FASTMCP=False` → `sys.exit(1)` 이 되는
**런타임 파손**이다. `[tool.mypy]` 의 `ignore_missing_imports = true` 가 사라진 모듈을
error 가 아니라 `Any` 로 바꿔 놓아, 그 `Any` 가 반환되는 27번 줄에서야 표면화됐다.

**1차 조치는 상한 핀이었다** (`>=1.0,<2`). red 를 켜 둔 채로는 다음 커밋의 신호를 읽을 수
없기 때문이지, 그것이 해결이어서가 아니다. 파손은 그대로 남았다.

**이관.** wrapper 가 두 이름을 모두 시도하고, 어느 쪽이 잡혔는지 `MCP_SERVER_SOURCE` 로
남긴다 (진단에 필요하다). 두 클래스의 계약은 이 wrapper 가 쓰는 범위에서 동일함을
실측으로 확인했다.

| 항목 | 1.x `FastMCP` | 2.x `MCPServer` |
|---|---|---|
| `__init__` | 첫 위치 인자 `name` | 같음 (+`version` 키워드 추가) |
| `.tool()` | `Callable[[AnyFunction], AnyFunction]` | `Callable[[_CallableT], _CallableT]` |
| `.run()` | 인자 없이 stdio | 같음 |

`version` 은 **일부러 전달하지 않는다** — 1.x 는 받지 않고, wrapper 의 `version` 은
예전부터 서버에 전달되지 않고 있었다. 여기서 넘기기 시작하면 서버 2종이 광고하는 version
이 바뀐다. 이관 범위 밖이라 기존 동작을 유지하고 사실만 적어 둔다.

**검증 — 네 버전 × 두 층.** `1.27.0`(smoke 가 실제로 쓰는 버전) / `1.28.1` / `1.29.0` /
`2.0.0` 각각에서 mypy strict **119 files 0 errors**, 그리고 런타임으로
`create_v1_server` → `.tool()` decorator 가 원함수 반환 → `.run` 호출 가능까지 확인했다.
실제 서버 2종(`latest-backlog`, `check-doc-metadata`)이 1.x/2.x 양쪽에서 tool 등록까지
되는 것도 확인했다.

**여기서 상한 핀을 풀었고, 그것이 틀렸다.** 핀을 푼 커밋이 처음으로 `server/**` 를
건드렸고 — `mcp-inspector` workflow 는 그 경로가 바뀔 때만 돈다 — 그제야 **두 번째 SDK
표면**이 드러났다. `read_only_mcp_sdk.py` 는 `FastMCP` 가 아니라 `mcp.server.lowlevel`
을 쓰는데, 2.0.0 의 `Server` 는 `list_tools` / `call_tool` decorator 를 없애고
`add_request_handler(method, params_type, handler)` 로 바꿨다.

```
AttributeError: 'Server' object has no attribute 'list_tools'
```

로컬에서 1.28.1(정상 initialize 응답) / 2.0.0(위 AttributeError) 로 재현했다.
**상한 핀을 복원**했고, lowlevel 이관은 TASK-2026-07-29-main-003 으로 분리했다.

> **"이관했다" 의 범위를 SDK 표면이 아니라 파일 하나로 잡았다.** `mcp_v1_server.py` 를
> 고치고 나서 "mcp 2.0.0 이관 완료" 라고 적었는데, 같은 SDK 를 쓰는 표면이 하나 더
> 있었다. §2.25 가 AST 로 문자열 상수 빈도를 낸 것과 같은 조사를 여기서 하지 않은 것이다
> — 고친 곳이 *그 부류의 전부인지* 는 따로 세어 봐야 한다. import 지점을 세는 것으로는
> 부족했다: `grep '^from mcp'` 는 wrapper 만 짚어 주고, `importlib.import_module("mcp…")`
> 로 들어오는 두 번째 표면은 걸리지 않았다.

**검사층.** `check_mcp_server_sdk_compat.py` 7건 신규. `sys.modules` 에 stub 을 심어
2.x 만 / 1.x 만 / 둘 다 / 둘 다 없음 네 환경을 각각 재해석시킨다 — 설치된 한 버전에서만
도는 검사는 다음 major 에서 또 같은 방식으로 놓치기 때문이다.

만들면서 두 번 걸렸고, 둘 다 이 저장소가 이미 아는 부류였다.

- **"없는 환경" 을 재현하지 못하고 있었다.** `sys.modules` 에서 지우기만 하면 디스크에
  설치된 진짜 mcp 를 다시 찾아온다. `None` 을 심어야 미설치와 같은 신호가 된다.
- **미설치면 skip** 이 다음 major 를 통째로 삼킨다. 두 이름이 다 사라져도 조용히
  통과한다 — §2.39 의 "미분류는 통과" 와 같은 결함이다. 그래서 **mcp 자체가 없을 때만**
  skip 하고, mcp 는 있는데 서버 구현을 못 잡으면 실패로 드러낸다. 되주입(두 import 를
  존재하지 않는 이름으로 교체)으로 이 경로가 실제로 실패하는 것을 확인했다.

**되주입 검증.** import 사슬만 fastmcp 단일로 되돌리면 `test_v2_only_resolves_mcpserver`
가 *"2.x 만 있는데 SDK 없음으로 판정했다"* 로, `test_both_present_prefers_v2` 가
*"둘 다 있으면 새 SDK 를 잡아야 한다"* 로 각각 다른 증상으로 실패한다. 이름만 바꿔도
실패하는 약한 검사가 아니라는 확인이다. 이 과정에서 runner 결함도 하나 나왔다 —
wrapper 의 fail-fast `sys.exit(1)` 이 `except Exception` 을 빠져나가 **첫 실패가 나머지
검사와 요약 줄을 통째로 없앴다**. `SystemExit` 을 따로 잡아 실패로 세고 계속 돌린다.

> 상한 없는 의존성은 커밋을 바꾸지 않아도 측정을 갈아 끼운다. 어제 green 이던 커밋이
> 오늘 red 인데 diff 가 무관하다면, 의심할 곳은 코드가 아니라 **러너가 집은 버전**이다.
> 그리고 관대한 설정(`ignore_missing_imports`)은 "없는 것" 을 "아무 타입" 으로 바꿔
> 진단을 원인에서 멀리 떨어뜨린다 — §2.29 의 config 함정과 같은 부류다.

**남은 관측** (고치지 않고 드러냄): smoke 가 이 드리프트에 걸리지 않은 것은 설계가 아니라
**설치 순서 덕**이다. `requirements-dev.txt` 의 `mcp[cli]==1.27.0` 이 뒤에 깔리며 되돌려
놓는다. mypy-strict job 은 그 파일을 깔지 않아 그대로 맞았다. 상한을 푼 지금은 두 job 이
서로 다른 major 를 밟게 되어 커버리지가 넓어졌지만, 그것도 여전히 우연이다.

### 2.42. 같은 날 세 번째 드리프트 — 도구도 의존성이다

§2.41 의 핀을 복원하고 `mcp-inspector` 를 수동 실행했더니 **여전히 red** 였다. 이번에는
`AttributeError` 가 없고 `Connection timed out after 15000 ms` 만 남았다. 설치 로그를
보니 러너가 집은 것은 `mcp-1.29.0` — 핀은 제대로 걸려 있었다. **Python 쪽이 아니었다.**

로컬에서 `mcp 1.27.0` / `1.28.1` / `1.29.0` 각각에 `initialize` 를 넣어 보니 셋 다 정상
응답한다. 서버는 멀쩡했다. 그런데 인스펙터를 통하면 재현된다:

```
File "<stdin>", line 1, in <module>
NameError: name 'true' is not defined. Did you mean: 'True'?
```

`<stdin>` 이라는 건 **python 이 인자 없이 떴다**는 뜻이다. argv 를 기록하는 wrapper 를
끼워 측정했더니 `ARGC=0 ARGV=[]` — 인스펙터가 `-m workflow_kit.server.read_only_mcp_sdk
--stdio-sdk` 를 전부 자기 파서에 먹고 명령만 띄웠다. 맨 python 이 REPL 로 떠서 JSON-RPC
의 `true` 를 Python 소스로 실행한 것이다. 15초 timeout 은 그 뒤의 표면 증상이었다.

원인은 `npx -y @modelcontextprotocol/inspector` 가 **버전을 고정하지 않은 것**이다. Node
쪽 인스펙터도 같은 시기에 **2.0.0** 이 됐고, `[target...]` 인자 처리가 바뀌었다.

| | 조치 |
|---|---|
| 호출 | 명령을 위치 인자로 넘기지 않고 `--config` + `--server` 로 **선언**한다 (2.0.0 에서 tools/list 왕복 실측) |
| 버전 | `@modelcontextprotocol/inspector@2` 로 major 고정 |
| 빈 응답 | rc=0 인데 `tools` 가 비면 실패로 만든다 — "죽지 않았다" 는 "받았다" 가 아니다 |

로컬 전 구간 재현: 인스펙터 → `live-tools.json` → 커밋된 descriptor 대조까지
**서버 13개 / descriptor 13개, 불일치 0**.

> 하루에 같은 부류가 세 번 나왔다 — Python `mcp` 상한 없음(§2.41), 그 안의 두 번째 SDK
> 표면(lowlevel), 그리고 `npx -y` 의 인스펙터. **셋 다 "우리 코드는 안 바뀌었는데 결과가
> 바뀌었다" 였다.** 검사 도구 자체도 고정하지 않으면 측정이 조용히 달라진다.

### 2.43. lowlevel 이관 — 계약이 사라졌으면 계약의 존재로 가른다

§2.41 이 남긴 두 번째 표면을 닫는다. mcp 2.0.0 의 `mcp.server.lowlevel.Server` 는
`@list_tools()` / `@call_tool()` decorator 를 없애고
`add_request_handler(method, params_type, handler)` 로 바꿨다.

**분기 기준은 버전 문자열이 아니라 계약의 존재다** (`uses_handler_registration` =
`hasattr(server, "add_request_handler")`). 버전 비교는 fork/backport 에서 틀리고, 여기서
알고 싶은 것은 "그 method 가 있는가" 하나다.

handler 계약은 SDK 소스에서 읽어 확정했다 (추측하지 않았다):

| | 1.x | 2.x |
|---|---|---|
| 등록 | `@server.list_tools()` / `@server.call_tool(validate_input=False)` | `add_request_handler("tools/list", PaginatedRequestParams, …)` / `("tools/call", CallToolRequestParams, …)` |
| list 반환 | `list[Tool]` | `ListToolsResult(tools=[...])` |
| call 인자 | `(name, arguments)` | `(ctx, params)` — `params.name` / `params.arguments` |
| Tool field | `inputSchema` | `input_schema` (**camel alias 로 양쪽 수용**) |

field 이름이 snake_case 로 바뀌었지만 alias 로 camelCase 를 그대로 받는다(실측:
`populate_by_name` + camel alias generator). 그래서 payload 조립은 **갈라 쓰지 않았다** —
버전 분기가 하나 더 생길 이유가 없다.

**한 군데는 갈라야 했다.** 예전 코드는 `result.isError = True` 로 **나중에** 덮었는데,
2.x 에서 그 이름의 attribute 는 `is_error` 다. 대입이 조용히 빗나가 **실패한 tool 호출이
성공으로 보고될** 자리였다. 생성 시점에 `force_error` 로 넣도록 바꿨다.

**검증 — 프로토콜 왕복.** 파일 모양 검사는 이 층을 대신하지 못한다는 것이 §2.41 에서
확인된 사실이라, 실제로 서버를 띄워 인스펙터로 왕복시켰다. 1.28.1 과 2.0.0 에서
`tools/list` **13개**, `tools/call` 성공 경로(`isError=false`)와 실패 경로
(`isError=true`) 모두, **두 버전의 wire 산출물이 JSON 으로 동일**하다. mypy strict 는
1.27.0 / 1.28.1 / 1.29.0 / 2.0.0 네 버전에서 119 files 0 errors.

**전수 조사를 이번엔 먼저 했다.** §2.41 의 실수(범위를 파일 하나로 잡음)를 되풀이하지
않으려고 import 문법 네 가지(`from mcp` / `import mcp` / `importlib.import_module("mcp…")`
/ `__import__`)로 쓸었다. 표면은 정확히 둘이고 둘 다 이관됐다. 확인 후 상한 핀을 해제했다.

**검사층.** `check_mcp_lowlevel_sdk_compat.py` 8건 신규. 두 형태의 `Server` 를 흉내내
조립기가 각각에 맞게 등록하는지 본다 (SDK 없이도 돈다).

만들면서 또 걸렸고, 이번 것은 **검사가 조용히 통과하는** 쪽이었다. 결함을 되주입했는데
8/8 PASS 였다. 되주입이 안 먹은 줄 알고 확인해 보니 적용은 됐고, 원인은 가짜를 심는
**범위가 검사하려는 코드보다 좁았던 것**이다 — `finally` 가 handler 를 부르기 *전에*
patch 를 되돌려, handler 안에서는 진짜 `invoke_tool` 이 불리고 있었다. context manager
로 범위를 넓히자 그 되주입이 *"returncode != 0 인데 isError 가 생성 시점에 안 들어갔다
(False)"* 로 정확히 실패한다.

> §2.42 가 "도구도 의존성이다" 였다면 이건 그 짝이다 — **가짜도 범위가 있다.** 심은
> 것이 실제로 불리는지까지 확인하지 않으면, 되주입이 통과하는 것을 "안전하다" 로 읽게
> 된다. 이번엔 되주입이 있어서 알았다.

**되주입 2건, 각각 다른 증상으로 실패 확인**: 2.x 분기를 없애면
`AttributeError: '_HandlerServer' object has no attribute 'list_tools'` 로 — **프로덕션에서
났던 바로 그 메시지** — 5건이 실패하고, `isError` 를 나중 대입으로 되돌리면 해당 1건만
실패한다.

### 2.44. 관대한 설정은 판정을 지운다 — optional dep 탐지층

§2.41 이 남긴 마지막 조각이다. mcp 2.0.0 이 `mcp.server.fastmcp` 를 통째로 없앴을 때
mypy 가 보고한 것은 "모듈이 없다" 가 아니라 엉뚱한 줄의 `no-any-return` 이었다.
`[tool.mypy]` 의 `ignore_missing_imports = true` 가 **없는 모듈을 error 가 아니라 `Any`
로** 바꿨기 때문이다. 판정이 지워진 자리에 그럴듯한 다른 판정이 들어앉았다.

**먼저 정한 것은 "그 설정을 좁힐 것인가" 였고, 답은 아니오다.** optional dep 은 실제로
optional 이라, `mcp.*` 만 override 에서 빼면 SDK 를 안 깐 로컬에서 mypy 가 red 가 된다.
더 근본적으로 **mypy 는 "안 깔림" 과 "깔렸는데 모듈이 사라짐" 을 구분할 수 없다** —
둘 다 그냥 "못 찾겠다" 다. 그 구분은 런타임 import 에서만 된다. 그래서 설정은 그대로
두고 판정을 옮겼다.

| 층 | 무엇을 아는가 |
|---|---|
| mypy (`ignore_missing_imports`) | 없는 모듈을 `Any` 로 — **구분하지 않는다** |
| `check_optional_dep_imports.py` | 배포판 설치 여부 × 모듈 import 가능 여부 = **네 칸 중 어디인가** |

`common/optional_deps.py` 에 import 대상 정본을 두었다. 두 종류로 나뉜다:

- `required_modules` — 그 extra 를 깔았으면 **전부** 돼야 한다.
- `alternative_modules` — 묶음에서 **하나만** 되면 된다 (`mcp.server.mcpserver` ↔
  `mcp.server.fastmcp`). 이 구분이 없으면 검사가 2.x 환경에서 **틀린 실패**를 낸다 —
  코드는 멀쩡히 도는데 검사만 우는 상황이다.

`read_only_mcp_sdk.SDK_IMPORT_TARGETS` 는 사본이었고, 이제 정본에서 가져온다. 그 사본은
mcp 2.0.0 이 이름을 옮겼을 때 **아무것도 몰랐다**.

**skip 을 조용히 넘기지 않는다.** 안 깔린 extra 는 건너뛰되 몇 개를 왜 건너뛰었는지
출력한다 — "어느 목록에도 없으면 통과" 는 §2.39 에서 이미 당한 결함이다. 실측: 로컬
`.venv` 는 2건 skip(pbt/profiling), mcp 없는 venv 는 6건 skip 이 그대로 찍힌다.

**완료 기준 확인 — 같은 상황, 다른 신호.** 이관 전 가정(`mcp.server.fastmcp` 를
`required` 로)을 되주입하고 두 버전에서 돌렸다:

| | mypy 가 낸 신호 | 이 층이 내는 신호 |
|---|---|---|
| mcp 1.28.1 | (green) | 6/6 PASS |
| mcp 2.0.0 | `mcp_v1_server.py:27 no-any-return` | **`'mcp.server.fastmcp' 모듈이 없다 (ModuleNotFoundError)`** |

**되주입 4건, 각각 다른 증상**: 이관 전 가정 → "모듈이 없다"; extra 를 registry 에서
빼면 → "pyproject 에 있는데 정본 registry 에 없는 extra: ['pbt']"; 빈 extra 의 note 를
지우면 → "빠뜨린 것인지 원래 없는 것인지 구분되지 않는다"; 소비자가 사본을 들면 →
"정본과 다르다 — 사본이 갈라졌다".

> §2.41 은 "상한 없는 의존성이 측정을 갈아 끼운다" 였고 이건 그 뒷면이다 — **관대한
> 설정은 측정을 지운다.** 지워진 판정은 없어지지 않고 다른 이름으로 나타나서, 읽는
> 사람을 원인에서 멀어지게 한다. 설정을 좁힐 수 없을 때는 **판정을 옮길 것.**

### 2.45. 커버리지가 넓은 것과 넓다고 말할 수 있는 것 — SDK 버전 matrix

§2.43 에서 상한 핀을 풀 때 남긴 문장이 있다: "핀 해제로 CI 가 두 major 를 동시에 밟는다
— 커버리지는 넓어졌지만 **여전히 설치 순서에 기댄 우연이다**." 그 우연을 선언으로 바꾼
것이 이번 작업이다.

**우연의 정체.** 세 job 이 서로 다른 버전으로 돌고 있었는데, 그렇게 정한 사람이 없다:

| job | 실제 mcp | 그 버전인 이유 |
|---|---|---|
| `smoke` | 1.x | `requirements-dev.txt` 의 고정 핀이 editable install **뒤에** 깔려 되돌린다 |
| `mypy-strict` | 2.x | 그 파일을 안 깔아서, 상한 없는 extra 가 최신을 집는다 |
| `mcp-inspector` | 2.x | 위와 같음 |

smoke 의 설치 3줄을 그대로 밟아 버전을 매 줄 관측했다(빈 venv, 2026-07-31):
`requirements.txt` 뒤 **2.0.0** → `requirements-dev.txt` 뒤 **1.27.0** → editable install
뒤 **1.27.0**. 두 번째 줄이 첫 줄을 되돌리고, 세 번째 줄의 `mcp[cli]>=1.0` 은 이미
만족돼서 손대지 않는다. 즉 `requirements-dev.txt` 한 줄을 지우면 **1.x 커버리지가 조용히
사라지는데 아무 검사도 실패하지 않는다.** 커버리지가 넓은 것과, 넓다고 말할 수 있는
것은 다른 일이다.

**조치는 네 층이다.**

1. `workflow_kit/common/sdk_matrix.py` — 밟을 버전(role + 근거)과 **각 job 의 버전
   정책**(`pinned` / `floating` / `matrix`, 그 버전이 어디서 오는지)을 한 곳에 적는다.
2. `mcp-sdk-matrix` workflow — `prepare` job 이 registry 에서 목록을 뽑아 `fromJson` 으로
   matrix 를 만든다. **yml 에 버전 문자열이 없다.** 셀마다 고정 설치 → 실측 검증 →
   `--filter mcp,optional_dep` 실행.
3. 기존 3 job 에 `--record <job>` 스텝 — 집힌 버전을 step summary 첫 화면에 남기고,
   `pinned` 로 선언한 job 은 어긋나면 실패한다.
4. `check_mcp_sdk_matrix.py` — 정본과 `requirements-dev.txt` / `pyproject` extra /
   workflow yml 이 갈라지지 않는지. **양방향**이다: mcp 를 깔면서 정책을 선언 안 한
   workflow 가 있어도 실패한다.

**floating 을 없애지 않았다.** 상한 없는 설치가 mcp 2.0.0 을 CI 로 끌고 들어왔고, 그래서
§2.41~§2.44 를 할 수 있었다. 나쁜 것은 부동인 것이 아니라 **부동인 줄 몰랐던 것**이다.
그래서 부동은 부동이라고 적고, 집힌 값을 로그에 남긴다.

**그리고 matrix 가 만들자마자 실제 결함을 하나 잡았다.**
`check_read_only_mcp_sdk_stdio.py` 는 mcp 2.x 에서 깨져 있었다 —
`InitializeResult.serverInfo` 가 2.x 에서 `server_info` 로 바뀌었는데(`isError` →
`is_error`, `structuredContent` → `structured_content` 도 같이), 이 파일은 camel 이름을
그대로 읽고 있었다. **서버 쪽은 §2.43 에서 이관했지만 읽는 쪽은 그 범위에 없었다** —
§2.41 에서 "이관 범위를 파일 하나로 잡았다" 와 같은 모양이다. 아무도 못 본 이유는
이 검사가 smoke 에서만 돌고 smoke 는 1.x 로만 돌기 때문이다. 이번엔 먼저 전수 조사부터
했다(`serverInfo` / `isError` / `structuredContent` / `readOnlyHint` 를 저장소 전체에서
sweep) — 클라이언트 표면은 이 파일 **하나**였다.

**판정을 두 번 고쳐 썼다. 둘 다 "무엇을 증거로 삼을 것인가" 의 문제였다.**

- 1차: 출력에서 "skip 처럼 보이는 말"(`Skipping`, `not installed`)을 찾는 **부정 판정**.
  → 위양성. `check_mcp_server_sdk_compat.py` 는 "둘 다 없을 때 fail-fast 하는가" 를
  *의도적으로* 확인하느라, SDK 가 깔린 환경에서도 그 문자열을 출력한다.
- 2차: `run_all_checks --json` 의 `last_line` 에서 성공 메시지를 찾는 **긍정 판정**.
  → 여전히 틀렸다. mcp 1.x 는 서버 로그(`Processing request of type
  ListToolsRequest`)를 stderr 로 뒤에 붙여서, 성공한 검사의 마지막 줄이 성공 메시지가
  아니다.
- 3차(채택): 판정이 **자기 측정을 직접 한다.** 왕복 검사 2건을 직접 돌려 exit 0 과
  성공 메시지를 요구한다. 남이 요약한 필드를 믿지 않는다.

`--assert-installed`("깔렸는가")와 `--assert-exercised`("그것으로 실제로 쟀는가")는 서로를
대신하지 못한다 — 설치가 조용히 실패하면 두 왕복 검사가 `Skipping…` 을 찍고 **exit 0**
으로 끝나서, 셀 전체가 아무것도 재지 않은 채 green 이 된다.

**실측(로컬 venv 3개, 각각 격리 설치).**

| mcp | 요청=실측 | 검사 subset | SDK 왕복 증거 | mypy strict |
|---|---|---|---|---|
| 1.27.0 (floor) | ✅ | 12/12 | 2/2 | 121 files 0 errors |
| 1.29.0 (latest 1.x) | ✅ | 12/12 | 2/2 | — |
| 2.0.0 (latest 2.x) | ✅ | 12/12 | 2/2 | 121 files 0 errors |

**되주입 7건, 각각 다른 신호**: 핀 제거 → "고정 핀을 못 찾았다"; 핀 드리프트 → "핀(1.28.1)
과 registry floor(1.27.0) 가 갈렸다"; extra 에 상한 부활 → "floating 이라고 선언돼 있는데
더 이상 부동이 아니다"; `--record` 제거 → "실측이 어디에도 안 남는다"; 정책 없는 job 추가
→ "정책이 선언 안 된 workflow: ['zz-probe']"; yml 에 버전 직접 기입 → "버전 문자열이 직접
적혀 있다"; 판정 층 제거 → "`--assert-exercised` 를 부르지 않는다". SDK 미설치 환경에서
`--assert-exercised` 는 두 검사 모두 "증거가 없다" 로 실패한다(실측).

> §2.41 은 "상한 없는 의존성이 측정을 갈아 끼운다", §2.44 는 "관대한 설정이 측정을
> 지운다" 였다. 이건 셋째 면이다 — **아무도 정하지 않은 측정.** 우연히 옳은 값은 다음
> 커밋에서 우연히 틀린 값이 되고, 그 사이에 아무 신호도 없다. 넓은 커버리지를 **선언**
> 으로 바꾸는 값은, 그것이 사라질 때 무언가 실패한다는 것이다.

### 2.46. 도구가 만든 초과를 사람이 치우고 있었다 — 파생물의 상한과 포인터

두 결함을 닫는다. 둘 다 같은 모양이다: **파생물을 만드는 쪽이 규약을 모른다.**

**(1) handoff §4 의 상한이 쓰는 쪽에 없었다.**

`recent_done_items` 를 아는 자리가 셋인데 상한을 아는 자리는 하나였다.

| 자리 | 하는 일 | 상한 |
|---|---|---|
| `sync_handoff_status` | handoff §4 에 append | **없음 — 무한히 쌓았다** |
| `build_workflow_state_payload` | state.json 조립 | `RECENT_DONE_ITEMS_CAP` |
| `linter.handoff_bloat` | 넘쳤는지 본다 | 리터럴 `10` (사본) |

그래서 `backlog-update --apply` 를 돌릴 때마다 §4 가 11번째 줄을 얻었고, `handoff_bloat`
가 그것을 잡으면 **사람이 손으로 가장 오래된 한 줄을 지웠다.** 2026-07-28 과 2026-07-31
두 close-out 에서 연속으로 재발했다 — 즉 이건 사고가 아니라 **고정 비용**이었다.
§2.38 이 "상한이 두 곳에 있고 자르는 방향이 반대" 를 고쳤는데, 그때 본 두 곳은 둘 다
*읽는* 쪽이었다. 쓰는 쪽은 그 시야에 없었다.

- 상한 정본을 `common/project_docs.RECENT_DONE_ITEMS_CAP` 으로 옮기고, 쓰는 쪽 /
  조립하는 쪽 / 보는 쪽이 전부 그 이름을 읽는다. 이 상한의 리터럴 사본은 사라졌다.
- `sync_handoff_status` 가 §4 에만 상한을 적용한다. **버리는 것은 가장 오래된 것**이다
  (§4 는 뒤가 최신인 append 목록 — 사람이 손으로 하던 조작과 같다).
  `in_progress` / `blocked` 는 상한이 없다. 전부 보여야 하는 사실이라서다.

**(2) `latest_backlog_path` 는 항상 `null`, `task_count` 는 항상 `0` 이었다.**

task 파일이 107건 있는 저장소에서 `state.json` 은 이렇게 적고 있었다.

```
source_of_truth.latest_backlog_path : null
backlog.latest_backlog_path         : null
backlog.task_count                  : 0        ← "모른다" 가 아니라 틀린 사실
```

경로 해석 세 갈래가 전부 `legacy_index_present`(구형 `work_backlog.md` 가 있는가) **하나**
에 매달려 있었다. append-only layout 에는 그 파일이 없으니 전부 `None` 으로 떨어졌고,
호출자가 `--latest-backlog-path` 로 **명시한 인자까지 버려졌다**(2026-07-31 실측: 넘겨도
그대로 `null`). 그 결과 `backlog` block 을 채우는 `parse_backlog` 가 아예 호출되지 않아
block 전체가 죽어 있었다 — `task_count` 만의 문제가 아니었다.

- 해석을 세 경로로 분리했다: (a) 명시한 인자, (b) legacy index 가 가리키는 최신 파일,
  (c) append-only layout 의 daily 디렉터리에서 가장 최신 `YYYY-MM-DD.md`. 실재하지 않는
  경로는 `null` 로 떨어진다 — 없는 파일을 가리키지 않는다.
- 파서는 손대지 않았다. `parse_backlog` 는 이미 신규 daily index(=link 모음)를 따라가
  task 파일을 읽는다. **읽는 쪽이 아니라 부르는 쪽이 막혀 있었다.**
- 이 필드는 `session-start` / `doc-sync` / `validation-plan` / `merge-doc-reconcile` 네
  skill 의 입력이다. 즉 최신 backlog 를 가리키는 포인터를 넷이 통째로 잃고 있었다.

**필드를 살리자 소비자 쪽 결함 둘이 곧바로 드러났다.** 값이 `null` 인 동안에는 그 값을
쓰는 코드가 한 번도 실행되지 않았다 — 죽은 필드는 자기 소비자까지 같이 얼려 둔다.

- `current_focus` 의 fallback 이 "최신 backlog 의 **첫** task" 였다. 그래서 전부 `done` 인
  날에 **완료된 작업이 "현재 초점"** 으로 올라왔다(실측). 아직 안 끝난 것만 고르고,
  없으면 비운다 — 없는 초점을 지어내지 않는다.
- `run_workflow_linter.py` 가 state.json 의 상대 경로를 **`branch_dir` 기준**으로 붙이고
  있었다. builder 는 workspace root 기준으로 적으므로 경로가 두 번 겹쳤고
  (`…/active/main/ai-workflow/memory/active/main/…`), 린터는 자기 저장소에서
  `missing_required_document` 를 냈다. 기준을 맞추고, **실재할 때만 채택**하도록 했다
  (그 전에는 없는 경로를 채택해 아래 fallback 이 건너뛰어졌다). `check_self_application`
  의 `test_own_linter_passes_on_own_repo` 가 이걸 잡았다.

**검사 2건(smoke 224 → 226).** `check_handoff_done_cap.py`(7 case) 는 쓰는 쪽의 상한과
버리는 방향, 그리고 **상한이 한 객체인지**를 본다 — 정본 값을 갈아 끼우고 쓰는 쪽과
린터의 동작이 따라오는지로 잰다(리터럴을 들고 있으면 안 따라온다). 린터 판정을 여기서
다시 쓰지 않고 프로덕션 `check_workflow_consistency` 를 그대로 부른다 — 판정을 복제하면
재현일 뿐 검증이 아니다(§2.29). `check_state_backlog_block.py`(8 case) 는 fixture 7건
(명시 인자 존중 / daily fallback / 빈 디렉터리 / 실재하지 않는 경로 / `task_count` 일치 /
완료 task 는 초점이 아님 / legacy layout 회귀)에 더해 **이 저장소 자신의 `state.json`** 을 본다. 필드가 다시
`null` 로 굳으면 거기서 실패한다.

**되주입 9건, 각각 다른 신호**: 쓰는 쪽 상한 제거 → "§4 가 상한(10)을 넘었다: 13개";
쓰는 쪽 리터럴화 → "상한을 3으로 바꿨는데 7개다"; 자르는 방향 반전 → "최신 10건이
아니다"; 린터 리터럴화 → "정본을 8로 낮췄는데 `handoff_bloat` 가 안 켜졌다"; 경로 해석을
legacy 에 재결합 → "명시한 인자를 버렸다"; daily fallback 제거 → "append-only layout 에서
`latest_backlog_path` 가 null 이다"; fallback 이 최오래 파일 선택 → "최신이 아니다";
`current_focus` fallback 되돌림 → "완료된 작업이 현재 초점이 됐다"; 린터 경로 해석
되돌림 → "status=warning issues=['missing_required_document']".

> **한 가지는 잡히지 않았다는 것도 적어 둔다.** 린터의 기준 경로만 `branch_dir` 로
> 되돌리면 아무 검사도 실패하지 않는다 — 겹친 경로가 실재하지 않아 **실재 확인
> 가드**가 걸러 내고 fallback 이 옳은 파일을 집기 때문이다. 즉 이 자리에서 실제로
> 일하는 것은 가드 쪽이고, 기준 경로 교정은 그 위의 정합이다. 둘을 함께 되돌려야
> 원래 증상이 재현된다.

> §2.38 은 "상한이 두 곳에 있었다" 였고 이건 그 다음 칸이다 — **상한을 아는 곳과 값을
> 만드는 곳이 다르면, 넘친 것을 사람이 치운다.** 수작업이 두 번 반복됐다는 사실 자체가
> 신호였다. 검사가 잡아 주는데도 매번 손이 가면, 잡는 층이 아니라 **만드는 층**이
> 규약을 모르는 것이다.

### 2.47. 기준 경로가 한 칸 어긋나 있었다 — 린터의 설정과 maturity

§2.46 이 남긴 "별건" 을 닫는다. `run_workflow_linter.py` 는 기준을 이렇게 잡았다.

```python
project_root = project_profile_path.parent.parent.parent
```

`<root>/docs/PROJECT_PROFILE.md` 에서 이 값은 root 가 아니라 **root 의 한 단계 위**다
(docs → root → 그 위). 되주입해 보면 fixture 에서 `project_root=/tmp` 가 나온다.
그 값이 두 곳으로 갔다.

1. **`load_config(project_root)`** — 없는 pyproject 를 물어 **언제나 기본값**.
   `[tool.workflow-doctor]` 의 `excluded_paths` 는 v0.7.15 도입 이래 한 번도 적용된
   적이 없다.
2. **`--maturity` 의 matrix/roadmap 경로** — 늘 빗나가 `status: skipped`. 그런데 runner
   는 `issues_found` 만 반영해서, **실행되지 못한 검사가 `status: ok / total_issues: 0`**
   으로 보고됐다. v0.11.17 backlog 에 `workflow_linter --maturity: status=ok,
   total_issues=0` 이 **정합 검증 통과**로 기록돼 있다 — 그 기록은 사실이 아니었다.

**둘 다 조용했던 이유는 같다.** `load_config` 는 어떤 경우에도 실패하지 않도록 설계돼
있다(운영 안정성). 좋은 성질이지만, 그 대가로 **"설정이 적용됨" 과 "조용히 기본값으로
떨어짐" 이 산출물에서 구별되지 않았다.** 안전한 fallback 은 결함을 감추는 데도 똑같이
안전하다.

**조치.**

- 기준을 정본 helper 하나로 잡는다 — `project_workspace_root(project_profile_path)`.
- `load_config_with_provenance` 신설. **물어본 경로 / 얻은 파일 / 출처 / 기본값으로
  떨어진 이유**(`file_missing` / `section_missing` / `parse_error`)를 함께 돌려준다.
  `load_config` 는 이걸 부르는 얇은 wrapper다 — 보고하는 경로와 쓰는 경로가 갈라지면
  보고가 사실이 아니게 된다. 결과는 린터 산출물의 `source_context` 에 남는다.
- `--config-path` 신설(파일이든 디렉터리든). **이 저장소에는 이게 필요하다** —
  `[tool.workflow-doctor]` 정본이 `workflow-source/pyproject.toml` 인데 workspace root
  는 저장소 루트라, 생략하면 정직하게 `config_source: default (section_missing)` 이
  나온다. 사본을 하나 더 두지 않고 **호출을 명시**하는 쪽을 택했고,
  `docs/PROJECT_PROFILE.md` 의 린터 명령줄을 그 형태로 갱신했다(그 줄은 v0.5.5 릴리스
  아카이브를 가리키는 죽은 명령이었다).
- `--maturity` 는 **못 돌았으면 통과라고 하지 않는다** — `maturity_check_not_run`
  (severity high) + `maturity_status` / `maturity_matrix_path` 기록. matrix 는
  `--maturity-path` 명시가 우선이고, 없으면 consumer layout(`ai-workflow/core/`) →
  kit layout(`workflow-source/core/`) 순으로 **실재하는 것**을 고른다.
- `test_path` 의 기준은 **matrix 를 담은 kit root**(= `core/` 의 부모)다. 저장소 루트를
  기준으로 삼으면 consumer 의 앱 테스트를 가리킨다. 검사 fixture 에 그 decoy 를 두어
  기준이 어긋나면 실패하게 했다.

**고치자마자 실제 드리프트가 나왔다.** 이 저장소에서 `--maturity` 를 처음으로 *실제로*
돌리니 `roadmap_milestone_mismatch` 1건(matrix 는 `Phase 13` 을 `in_progress` 로 적는데
roadmap 은 그 단계를 현재로 말하지 않는다) + `task-modes` 에 `test_path` 없음 경고 1건.
**내용 정정은 이 커밋의 범위가 아니라 그대로 드러내고 후속으로 남긴다.**

**검사 1종 신규 + 1종 교체(smoke 226 → 227).** `check_linter_config_resolution.py`(9
case)는 기준 경로 / 설정 도달 / 출처 기록 / 명시 우선 / maturity 4종을 프로덕션 runner
를 subprocess 로 돌려 본다. 그리고 `check_v0_7_15_config_thresholds.py` 의 9번째 case
를 **문자열 검사에서 동작 검사로 바꿨다** — 그것은 runner 본문에서
`"load_config(project_root)"` 라는 *문자열*을 찾고 있었다. 그 줄은 내내 있었고, 다만
없는 경로를 묻고 있었다. **통과하면서 아무것도 보장하지 못하는 검사였다.**

**되주입 7건, 각각 다른 신호**: 기준 경로 되돌림 → "project_root=/tmp 가 workspace
root 가 아니다"; `--config-path` 무시 → "명시가 우선하지 않는다"; maturity 기준을
project_root 로 → decoy 때문에 "없는 test_path 를 못 잡았다"; `issues_found` 만 반영 →
"matrix 부재인데 통과로 보고됐다: status=ok"; 후보 실재 확인 제거 → "kit layout 을
못 고른다"; section 부재를 `pyproject` 로 보고 → "출처 날조"; 파일 부재와 section 부재를
같은 이유로 뭉갬 → "두 사실이 구별되지 않는다".

> §2.44 는 "관대한 설정이 판정을 지운다" 였고, 이건 그 사촌이다 — **관대한 fallback 이
> 자기가 무엇을 못 했는지 말하지 않는다.** 실패하지 않는 loader 를 만들 거면, 무엇을
> 물었고 무엇을 얻었는지는 반드시 함께 내놓아야 한다. 그러지 않으면 "적용됨" 과
> "떨어짐" 이 같은 모양이고, 그 둘이 같은 모양인 동안에는 아무도 결함을 볼 수 없다.

### 2.48. 검사가 처음 돌자 나온 2건 — 하나는 진짜였고 하나는 위양성이었다

§2.47 이 `--maturity` 를 **처음으로 실제로** 돌게 만들자 두 건이 나왔다. 둘을 같은
"드리프트" 로 묶을 뻔했는데, 사실 확인을 해 보니 종류가 달랐다.

**(1) `task-modes` 는 위양성이었다.** "stable 인데 `test_path` 가 없다" 는 warning 이
붙었지만, 그 항목은 `kind: "spec"` 이다 — 실행 표면이 없는 명세이고 근거는
`spec_path: core/workflow_task_modes.md` 다. 그 규약을 아는 자리는
`tests/check_maturity_registry.py` **하나뿐**이었고(`kind != "spec"` 리터럴 3곳),
**kit 이 배포하는 린터는 몰랐다.** 소비자 저장소에서 `--maturity` 를 돌리면 영영 이
위양성을 본다는 뜻이다. 위양성을 내는 검사는 무시당한다 — 그러면 같은 검사가 잡아 줄
진짜 결함도 함께 무시된다.

- 어휘 정본 `workflow_kit/common/maturity.py` 신설: `SKILL_KIND_SPEC` /
  `TEST_REQUIRED_STAGES` / `is_spec_entry` / `requires_test_path` / `spec_path_of`.
  린터와 registry 검사가 **같은 이름을 읽는다** (리터럴 사본 제거).
- 명세 항목은 `test_path` 대신 **`spec_path` 실재**를 요구한다. 선언한 파일이 없으면
  `missing_spec_file`(high), 선언 자체가 없으면 warning. **완화가 아니라 근거의 교체다.**

**(2) roadmap 은 진짜 드리프트였다 — 그리고 판정이 그것을 잡을 수 없는 모양이었다.**
`workflow_kit_roadmap.md` 와 `phase_13_followup.md` 는 둘 다 **2026-07-21** 자로
"Phase 13 planned 진입 대기" 라고 적고 있었다. v1.0.0 은 **2026-07-22** 에 발행됐고
(entry gate 6영역 전부 PASS, `-beta` suffix 는 릴리스 노트 머리말이 *명명 관례*라고
명시한다), matrix 는 `Phase 13.status = in_progress` / `started = 2026-07-21` 다. 즉
**두 문서가 릴리스 하루 전에서 멈춰 있었다.**

문제는 판정이었다. 예전 검사는 milestone `name` 문자열이 roadmap 본문에 **있는지**만
봤다. 그 한 줄만 넣으면 roadmap 이 같은 단계를 `planned` 라고 말해도 통과한다 — §2.47
에서 지운 것과 같은 종류의 검사다. 그래서 판정을 둘로 나눴다.

- **언급**: `name` 이 본문에 있는가 (기존 `roadmap_milestone_mismatch` 유지).
- **모순 없음**: matrix 가 `in_progress` 라는 단계를 roadmap 이 `planned` / `진입 대기` /
  `진입 예정` 으로 적고 있지 않은가 → 신규 `roadmap_milestone_still_planned`.
  **어느 쪽이 사실인지는 도구가 정하지 않는다** — 모순을 드러내고 사람에게 넘긴다.
  key 매칭은 숫자 경계를 본다(`Phase 1` 이 `Phase 13` 줄에 걸리면 없는 모순을 만든다).

내용 정정은 **matrix 를 사실로** 채택했다: roadmap §1/§1.3/§7/§8 과
`phase_13_followup.md` 의 상태 줄을 `in_progress` (2026-07-21 start) 로 맞추고, `-beta`
suffix 가 왜 성숙도 주장이 아닌지 roadmap 에 근거로 남겼다.

**검사 1종 신규(smoke 227 → 228)**: `check_maturity_drift_judgment.py`(10) — spec 어휘
4종 + roadmap 정합 4종 + "소비자에 리터럴 사본이 없다" + 이 저장소 실제 상태.

**되주입 5건, 각각 다른 신호**: spec 분기 제거 → 원래 위양성 문구가 그대로 재현
(`Skill 'task-modes' is in stage 'stable' but has no test_path defined.`); 모순 판정 제거
→ "이름만 적어도 통과한다"(`status: ok`); roadmap 내용 되돌림 → 실저장소 판정이
`roadmap_milestone_still_planned` 로 실패; 숫자 경계 제거 → `Phase 1` 이 `Phase 13` 줄에
걸림; registry 에 리터럴 복원 → "어휘 사본이 남아 있다".

> §2.47 이 "관대한 fallback 이 자기가 못 한 일을 말하지 않는다" 였다면, 이건 그
> **다음 날의 이야기**다. 검사를 켜면 보고가 온다. 그때 **보고를 다 믿어서도 안 되고
> 다 지워서도 안 된다** — 한 건은 문서를 고쳐야 했고 한 건은 검사를 고쳐야 했다.
> 둘을 가른 것은 `kind: "spec"` 이라는 사실 하나였고, 그 사실은 이미 저장소 안에
> 있었는데 **읽는 층이 하나뿐**이었다.

### 2.49. 같은 결함이 CLI 에도 있었다 — doctor 의 기준 경로와 출처

§2.47 을 린터에서 닫으면서 "`workflow_kit.cli.doctor` 는 아직 provenance 를 안 쓴다" 를
후속으로 남겼다. 열어 보니 **provenance 만의 문제가 아니었다.**

```python
DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
```

이 저장소에서 그 값은 `/home/yklee/repos` — **저장소 루트의 두 단계 위**다(실측). 그리고
kit 이 site-packages 에 설치되면 그 경로는 사용자의 프로젝트와 아무 관계도 없다.
**모듈 위치로 사용자의 workspace 를 추측할 수 있다는 전제 자체가 틀렸다.** 그 값이
`load_config` 와 `_read_state_json` 양쪽으로 갔으니, 기본 호출
(`python -m workflow_kit.cli.doctor`)은 설정도 state.json 도 못 찾고 있었다.

**기존 doctor smoke 는 전부 `--project-root` 를 명시해서 돌고 있었다.** 그래서 기본값이
깨져 있어도 아무 검사도 실패하지 않았다 — §2.47 에서 지운 "통과하면서 아무것도 보장하지
못하는 검사" 와 같은 자리다. 사용자가 실제로 치는 것은 인자 없는 쪽인데.

**조치.**

- `--project-root` 기본값을 **cwd** 로. 추측이 아니라 호출자가 서 있는 자리다.
- `--config-path` 신설(린터와 같은 형태). 이 저장소는 `[tool.workflow-doctor]` 정본이
  `workflow-source/pyproject.toml` 이라 이게 필요하다.
- 출력 3종에 **`config_provenance`** 를 싣는다 — `--show-config`(기존 5 field 는
  **top-level 그대로** 두고 옆에 붙인다), `--json`, 그리고 pretty footer 는
  `Config source: default (section_missing) → 선언한 설정이 적용되지 않았다` 를
  **표의 숫자보다 먼저** 적는다.

**고치자마자 동작이 바뀌었다.** `--config-path workflow-source` 로 돌리면 선언한
`partial_rules = { resiliency = ["RES-WF-01", "RES-WF-02"] }` 가 **평가 결과에 실제로
반영된다**(`results.resiliency.partial_rules`). v0.7.8 이 "display only 를 actual apply 로
격상" 이라고 적은 그 기능은, 이 저장소에서 한 번도 apply 된 적이 없었다.

**검사 1종 신규(smoke 228 → 229)**: `check_doctor_config_provenance.py`(6) — 기준 경로 /
기존 5 field 계약 유지 / 출처 2종 / 명시 우선 + **평가 도달** / pretty footer.
`check_v0_7_4_followup` 의 JSON envelope 계약도 `config_provenance` 를 포함하도록 갱신했다.

**되주입 4건, 각각 다른 신호**: default 를 모듈 위치로 되돌림 → `project_root:
/home/yklee/repos`; `--config-path` 무시 → 선언한 설정이 평가에 도달하지 않음;
pretty 출처 줄 제거 → footer 에 출처 없음; `--show-config` 를 nested 로 → 기존 5 field
top-level 계약 파기.

> §2.47 은 한 도구의 경로 하나를 고쳤다. 이건 **같은 결함이 형제 도구에 그대로 있었다**는
> 이야기다. 결함을 고칠 때 "이 모양이 또 어디 있나" 를 묻지 않으면, 같은 것을 두 번
> 발견하게 된다. 이번엔 후속 항목으로 적어 둬서 두 번째 발견이 하루 안에 왔다.


### 2.50. 세 번째를 찾으러 갔다 — 경로 기준 전수 조사

§2.47(린터)과 §2.49(doctor)가 **같은 모양**이었다. 그래서 "이 모양이 또 어디 있나" 를
손으로 세지 않고 **AST 로 전수 조사**했다 (`workflow-source/**/*.py`, build 제외).

| 부류 | 건수 | 판정 |
|---|---|---|
| A. `Path(__file__)` 에서 유도한 기준 | 309 | 저장소 밖 착지 **0건** (doctor 가 마지막이었다) |
| B. 인자/변수의 `.parent` 연쇄 (depth ≥ 2) | 3 | 전부 근거 있음 |
| C. `Path.cwd()` 기반 | 9 | 명시적 선택 |

A 의 309건은 대부분 저장소 자산을 찾는 in-repo 스크립트라 정상이다. 배포 패키지
(`workflow_kit/**`) 안의 11건을 따로 봤고, `server/*` 4건과 `harness` 1건이
`<repo>/workflow-source/` 배치를 가정하지만 이는 **선언된 설계**다 —
`pyproject.toml` 이 "나머지는 저장소 디렉터리 레이아웃으로 소비한다" 고 적고 있다.

**그런데 B 를 보다가 다른 축에서 세 번째가 나왔다.** 기준이 되는 것은 경로만이 아니다 —
**branch** 도 경로를 고른다.

v1.0.1 이 `branch_for_workspace` 를 만들며 규칙을 선언했다: *workspace 로 파라미터화된
함수는 그 workspace 의 git 을 본다. 호출 위치가 답을 바꾸면 안 된다.* 그런데 그 규칙을
적용한 곳은 `state_path_for_workspace` **하나뿐**이었다. profile 을 받는
`workflow_branch_dir` / `workflow_archived_branch_dir` 는 `get_current_branch()`
(= 이 모듈이 속한 저장소)를 계속 쓰고 있었다. **실측**:

```
repoB(feature/probe-branch) 의 profile 로
  state_path_for_workspace → …/active/feature/probe-branch/state.json
  workflow_branch_dir      → …/active/main            ← 모듈 저장소의 branch
  workflow_archived_...    → …/archived/main
```

같은 workspace 에 대해 **state.json 과 handoff/backlog 가 서로 다른 branch 디렉터리**를
가리킨다. 한쪽만 갱신되고 다른 쪽은 조용히 옛 값을 읽는, §2.20 의 "branch-scoped 전환에서
경로가 절반만 옮겨졌던" 것과 같은 자리다. 이 저장소에서는 모듈 저장소 == workspace 라 안 드러나고, **kit 을 쓰는
소비자 프로젝트에서만** 발현한다 — 정확히 이 kit 이 존재하는 이유인 그 상황이다.

**기존 검사들이 못 본 이유는 자기 자신과 비교했기 때문이다.** fixture 를
`get_current_branch()` 로 만들고 결과를 `get_current_branch()` 와 대조하니, 두 해석기가
갈라져도 통과한다. 신규 검사는 **모듈 저장소와 다른 branch 의 workspace 를 실제로 만들어**
셋이 같은 slug 를 쓰는지 본다.

**검사 1종 신규(smoke 229 → 230)**: `check_branch_resolver_agreement.py`(4) — 해석기 합의 /
state 와 문서가 같은 디렉터리 / 비-git workspace fallback / 명시 인자 우선.

**되주입 2건, 각각 다른 신호**: `workflow_branch_dir` 되돌림 → `branch_dir=main
archived=feature/… state=feature/…`; archived 되돌림 → `archived=main` 만 어긋남.

> §2.47 → §2.49 → §2.50. 세 번 다 "**기준을 어디서 얻는가**" 였고, 세 번째는 경로가 아니라
> branch 였다. 규칙을 선언한 것만으로는 부족하다 — **선언한 규칙을 따르지 않는 자리를
> 찾아 두는 검사**가 있어야 한다. v1.0.1 은 규칙을 적고 한 곳에 적용했고, 나머지 두 곳은
> 5개월 뒤 전수 조사에서 나왔다.


## 3. 검증

누적 smoke **230/230 PASS** (2026-07-31, `dev,release,mcp-sdk` extra 를 깐 격리 venv 에서
`run_all_checks.py --tmp-dir=<실디스크>`, resource guard 완주 — abort 0 / 고아 프로세스 0 /
디스크 변동 0). 누적 추이는 217 → 218(§2.38 `check_recent_done_items_order`) → 219(§2.39
`check_task_status_axis_separation`) → 220(§2.40 `check_migration_group_heading`)
→ 221(§2.41 `check_mcp_server_sdk_compat`) → 222(§2.43
`check_mcp_lowlevel_sdk_compat`) → 223(§2.44 `check_optional_dep_imports`)
→ 224(§2.45 `check_mcp_sdk_matrix`) → 226(§2.46 `check_handoff_done_cap` +
`check_state_backlog_block`) → 227(§2.47 `check_linter_config_resolution`)
→ 228(§2.48 `check_maturity_drift_judgment`)
→ 229(§2.49 `check_doctor_config_provenance`)
→ **230**(§2.50 `check_branch_resolver_agreement`).

> **§2.45 작업 중 `release` extra 없는 venv 에서 먼저 돌렸더니 219/224 였다.** 5건 중
> 3건은 문서가 아직 223 이라고 적고 있어서였고(`CODE_INDEX` / `INSTALLATION_AND_USAGE` /
> 이 노트 — 셋 다 이번에 224 로 갱신), 나머지 2건(`check_release_pipeline_lib`,
> `check_release_pipeline_phase3`)은 `build` 모듈 부재였다. 같은 트리를
> `dev,release,mcp-sdk` venv 에서 돌리면 각각 9/9, 8/8 로 통과한다 — **코드 결함이 아니라
> 어떤 환경으로 쟀는가**의 차이다. 위 §2 의 "인터프리터를 바꾸면 같은 트리가 208/216 이
> 된다" 와 같은 부류라, 수치에는 extra 조합도 함께 적는다.
>
> **mcp SDK 버전별 실측(§2.45)**: `1.27.0` / `1.29.0` / `2.0.0` 세 격리 venv 에서 mcp 관련
> subset 12/12 PASS + SDK 왕복 증거 2/2 + 요청 버전 = 설치 버전 일치. mypy strict 는
> 1.27.0 과 2.0.0 에서 각각 **121 files 0 errors** (mypy 2.1.0, `--config-file` 명시).

> **인터프리터를 바꾸면 같은 트리가 208/216 이 된다 (2026-07-27 실측).** 시스템
> `python3` 로 돌리면 8건이 실패하는데, `.venv/bin/python` 으로 돌리면 0건이다. 실패하던
> 8건은 mypy 부재(`mypy_strict_*` 2건) 와 dev/release extra 부재(`release_*` 5건,
> `workflow_kit_cli` 1건) 였다 — 코드 결함이 아니라 **어떤 인터프리터로 쟀는가**의 차이다.
> §2.29 의 "config 를 명시하지 않으면 조용히 Default 로 떨어진다" 와 같은 부류이므로,
> 전량 수치에는 인터프리터도 함께 적는다.
>
> **회귀 여부는 같은 환경끼리 비교했다.** 시스템 `python3` 기준으로 §2.31 적용 트리는
> 208/216, `git worktree` 로 새로 뽑은 깨끗한 HEAD 는 207/215 — **실패 목록이 완전히
> 동일한 8건**이다. 즉 §2.31 은 smoke 를 하나 늘리고 하나 통과시켰을 뿐 회귀는 0건이다.
**전량 실행 후 워킹트리 변경 0** — smoke 가 추적 파일을 write 하던 경로를 차단한 결과다.

> **위 수치는 푸시 후 기준이다. 미푸시 HEAD 실측은 213/215.** 나머지 2건
> (`check_mypy_ci_cross_verify_v0_11_13`, `check_release_summary_v0_11_15`)은 같은 SHA 의
> CI run 이 아직 없어 `ci_stale` 로 떨어진다 — 코드 결함이 아니고, 푸시 후 CI 가 돌면
> green 으로 전환된다 (v1.0.0 사이클에서 관측). 예측을 실측처럼 적지 않기 위해 두 수치를
> 함께 남긴다.
>
> **덧붙여 기록해 둘 약점 하나**: `smoke_trend_cross` / `quality_dashboard` Panel 4 는
> 실행 결과가 아니라 **이 릴리스 노트에 손으로 적은 숫자**를 읽어 판정한다. 즉 노트의
> 수치가 틀리면 게이트도 함께 틀린다. 이번에도 노트에 215/215 라고 적힌 상태에서
> 실제 실행은 213/215 였는데 게이트는 green 이었다. 산출물을 직접 세는 쪽으로
> 옮기는 것이 맞다 — 별도 과제로 남긴다.

> **측정 환경 명시 (§2.27)**: 위 수치는 **`git worktree` 로 새로 체크아웃한 깨끗한 트리**에서
> 잰 것이다. 이전 사이클의 "209/209" 는 작성자의 원본 작업 사본에서만 성립했고 CI 는 red 였다.
> 앞으로 전량 수치를 적을 때는 **어디서 쟀는지** 를 함께 적는다 — 재현 불가능한 환경에서 잰
> 수치는 지표가 아니다.

> **측정 조건에 따라 갈리는 잔여 3건 (실측 기록)**: 커밋 `2e3c00b` 를 새 워크트리로 뽑아
> 실디스크 `--tmp-dir` 로 돌리면 **210 중 207 PASS** 다. 3건의 성격이 다르다.
>
> | 잔여 | 갯수 | 성격 |
> |---|---|---|
> | `mypy_ci_cross_verify_v0_11_13`, `release_summary_v0_11_15` | 2 | **CI 상태 의존** — §0.1 이 이미 분류한 "push 후 자동 해소" 범주. HEAD 가 **미푸시**라 GitHub 에 해당 SHA 의 run 이 없어 `ci_stale` 이 된다. push 후 CI 가 돌면 해소된다. |
> | `release_pipeline_lib` | 1 | **공유 저장소 경로 경합** (아래). standalone 9/9, 전량에서 간헐 |
>
> 즉 위 두 건은 *코드가 아니라 측정 시점* 의 문제다 — 릴리스 노트가 기술하는 것은 **push 된
> 상태**이므로, 미푸시 HEAD 에서 잰 수치를 그대로 적으면 조건이 어긋난다. §2.27 이 말한
> "어디서 쟀는지가 수치의 일부다" 가 여기에도 그대로 적용된다.

> **잘못 짚었던 것을 그대로 남긴다 — `tmpfs` 가 원인이 아니었다.** `check_release_pipeline_lib`
> 가 8/9 로 넘어지는 것을 처음엔 tmpfs(RAM) TMPDIR 탓으로 봤다. 같은 트리를 tmpfs 로 한 번,
> 실디스크로 한 번 돌렸더니 실디스크에서 통과했기 때문이다 — **2회 관측으로 인과를 단정했다.**
> 세 번째 실행(실디스크)에서 다시 8/9 로 넘어져 그 귀인이 틀렸음이 드러났다.
>
> 실제 원인은 `cmd_dist` 가 per-check TMPDIR 이 아니라 **공유 경로 `workflow-source/dist/` 에
> 쓴다**는 것이다 (`_dist_dir = REPO_ROOT / "dist"`). runner 의 격리는 TMPDIR 만 덮으므로 이
> 경로는 보호되지 않고, 같은 dist 를 만지는 check 와 동시에 돌면 경합한다. `dist/` 는
> gitignore 라 "저장소 오염 0" 에도 잡히지 않는다. 단독 실행과 `--filter` 격리에서는 9/9 라
> 결함으로 오인하기 쉽다.
>
> 교훈은 §2.27 과 같다: **재현 조건을 고정하지 않은 2회 관측은 인과가 아니다.** 이 사이클이
> 고친 것이 바로 그 부류인데 고치는 사람이 같은 실수를 했으므로 지운 자리 대신 기록으로 남긴다.
> 이 flake 는 v1.0.0 이전부터 있던 것으로, 본 사이클의 변경과 무관하다 (다음 사이클 과제).

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
| 전량 smoke | **217/217 PASS** (2026-07-27 §2.31 반영, `.venv/bin/python` 실측 372초. 시스템 `python3` 로는 같은 트리가 208/216 — 인터프리터 차이다, 위 실측 기록 참조) |
| 실효 smoke | **204/204 PASS** (자기참조 게이트 2건 제외 — 순환 재발 방지용 안전망) |
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
