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

## 3. 검증

누적 smoke **211/211 PASS** (2026-07-23, `run_all_checks.py --tmp-dir=<실디스크>` 격리 실행,
resource guard 완주 — abort 0 / 고아 프로세스 0 / 디스크 변동 0).
**전량 실행 후 워킹트리 변경 0** — smoke 가 추적 파일을 write 하던 경로를 차단한 결과다.

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
| 전량 smoke | **211/211 PASS** (미푸시 HEAD 에서는 CI 상태 의존 2건 + dist 경합 flake 1건이 붙는다 — 위 실측 기록 참조) |
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
