# Beta v1.9.0 (2026-09-02)

> **상태: 릴리스 준비.** package `1.9.0`, runtime `__version__ = 1.9.0`, tag `v1.9.0`.
> **minor release** — 발행 절차 자신과 상태 기록 도구가 *스스로를 검증하도록* 바뀐다.
>
> 등급 근거 (§1.5): 공개 API 시그니처 변경 0 · 진입점 제거 0 · 산출물 형식 변경 0.
> 다만 공개 API 에 `verify_required_ci()` + `REQUIRED_CI_WORKFLOWS` 가 **추가**됐고
> `release --apply` 의 기본 동작이 넓어졌다 — 추가는 minor 다.

## 0. 릴리스 판정

이 사이클의 주제는 **"게이트가 자기가 재는 것을 실제로 보고 있는가"** 다. 두 도구가
같은 모양으로 틀려 있었다 — **선언은 옳은데 구현이 그 선언보다 좁았다.**

- 발행 게이트는 "CI 가 green 인가" 를 묻는다고 적혀 있었지만 **워크플로 하나만**
  보았고 그마저 advisory 였다 (§2.1).
- `backlog-update` 는 docstring 에 "이미 기록된 done 은 강등하지 않는다" 고 적혀
  있었지만, 코드는 그 원칙을 `--status` 를 **생략했을 때만** 지켰다 (§2.2).

둘 다 저장소 안에서는 영원히 green 이다. 선언을 읽으면 옳고, 실행을 보면 좁다.

**이 릴리스에는 발행해야 할 이유가 있다.** §2.1 의 게이트가 없던 동안 **v1.8.0 이
`smoke` 10 커밋 연속 red 위에서 발행됐다.** 그 게이트는 v1.8.1 에 실리지 못하고
태그 뒤에 착지했으므로, 지금 v1.8.1 을 쓰는 소비자의 `release --apply` 는 여전히
CI 를 사실상 안 본다.

## 1. 릴리스 요약

- 범위: `v1.8.1..HEAD` (4 commit). 이 중 1건(`54ff793e`)은 **v1.8.1 발행 마무리**가
  태그 뒤에 착지한 것이라 실질 내용은 3 commit 이다.
- 누적 smoke **280/280 PASS** (전량 2축 · case 합계 560, FAIL 0, 좁은 선언 0),
  mypy strict 0 errors
- 검사 신설 2종 (`check_release_ci_gate` 8 cases · `check_done_demotion_rule` 8 cases)
- 지원 하네스 12 (변동 없음), MCP 표면 13 (변동 없음)
- 공개 API **+2** (`release_pipeline.verify_required_ci` · `REQUIRED_CI_WORKFLOWS`) — 제거 0

## 2. 소비자 가시 변경

### 2.1 feat(release) — `release --apply` 가 필수 CI 워크플로 전수를 보고 기본 차단한다 (`c49e2c74`)

**동작이 바뀐다. 이전에는 CI 가 red 여도 발행이 진행됐다.**

구멍은 셋이었고 세 개가 겹쳐야 조용해진다:

- **범위**: `_cross_verify_ci_mypy` 가 `mypy-strict.yml` **하나만** 조회했다.
  저장소 전체에서 `--workflow` 인자를 쓰는 자리는 거기 하나뿐인데 push 트리거
  워크플로는 7개다.
- **강제력**: 그 1개마저 `--strict-cross-verify` 를 **명시할 때만** hard fail 이었다.
  기본은 advisory 라 `ci_fail` 을 보고도 발행이 계속됐다.
- **대상 지정**: `--branch` 없이 `--limit 1` 이라, HEAD 의 run 이 아직 없으면
  **이전 커밋의 run** 을 읽었다.

그래서 `smoke` 가 2026-08-30 부터 10 커밋 연속 red 인 동안 게이트는 내내 green 을
보았고 **v1.8.0 이 그 위에서 발행됐다** (`6c495e61`: smoke=failure, 나머지 3종 success).

뿌리는 설계 분업이다. 릴리스 노트의 `누적 smoke N/N PASS` 는 **사람의 주장**이고
(`verify_release_note_smoke_count` 가 그렇게 적는다 — 도구가 대신 쓰면 거짓 주장이
된다), 그 주장을 **CI 실측과 대조하는 자리**가 절차 어디에도 없었다. v1.8.0 노트는
`276/276 PASS` 라 적었고 같은 커밋의 CI smoke 는 failure 였다.

**수리**:

- `REQUIRED_CI_WORKFLOWS` 선언 — `smoke` · `mypy-strict` · `os-matrix` ·
  `mcp-sdk-matrix` 4종.
- `verify_required_ci()` 가 `gh run list --commit <HEAD sha>` 로 **대상을 직접
  지정**해 전수 조회한다 (`--workflow` 1개 + `--limit 1` + `--branch` 없음 을 전부 걷음).
- `cmd_release` step 1.5 에서 **기본 차단** — apply 경로에서 **태그 생성 전에** 멈춘다.
- **모름은 통과가 아니다**: run 이 없거나(missing) 도는 중(pending)이거나 `gh` 를
  못 부른 경우(fetch_error)도 전부 차단이다.
- escape hatch 는 `--skip-ci-verify` **명시**이고 결과에 남는다. dry-run 은 보고만
  한다 (`smoke_count_check` 와 같은 관례).

목록을 4종으로 **좁게** 잡은 기준은 *소비자에게 나가는 산출물의 정확성을 재는 축*
이다. `mkdocs` · `actionlint` 까지 넣으면 막을 이유가 없는 것이 막히고, 그러면 사람이
escape hatch 를 습관적으로 쓰게 되며, 그 순간 게이트는 다시 없는 것이 된다.

**소비자 영향**: `wk release-pipeline release --apply` 를 쓰는 downstream 은 이제
**push 하고 CI 가 끝나기를 기다린 뒤** 발행해야 한다. `gh` CLI 가 없거나 로그인되지
않은 환경에서는 차단되므로, 그런 환경은 `--skip-ci-verify` 를 명시한다.

### 2.2 fix(backlog-update) — `done` 강등이 이미 기록된 완료를 취소하지 않는다 (`e6f033db`)

**상태 기록 도구의 데이터 손실 결함이다.**

이미 `done` 인 task 에 진행 메모만 덧붙이려고 `--status done --progress-note` 로
재호출하면, `--validation-result` 를 함께 싣지 않았다는 이유로 도구가 상태를
**`done` → `in_progress` 로 강등**하고 `session_handoff.md` 의 그 항목을
**§4(최근 완료) → §2(진행 중)로 되돌렸다**. 최상위 `status` 는 `ok` 였고 근거는
warnings 한 줄뿐이라, 그 상태 그대로 커밋되어 push 됐다.

뿌리는 **선언과 구현의 갈라짐**이다. `determine_conservative_task_status` 의
docstring 은 이미 "기존 done 의 보존은 강등하지 않는다 — 그 done 은 이미 검증과
함께 기록된 상태다" 라고 적는데, 코드는 그 원칙을 `--status` 를 **생략했을 때만**
지켰다. 명시하면 파일에 기록된 검증을 **읽지 않고** 무조건 낮췄다.

강등 자체는 설계된 동작이다 (검증 없는 `done` 금지). 그것이 **이미 기록된 완료를
취소하는 쓰기**까지 하는 것이 별개의 문제였다. 두 갈래로 나눴다:

- 기록된 검증이 **있으면 보존**한다 (경고는 남긴다).
- 어디에도 **없으면 강등을 유지**하되, 그것이 이미 `done` 이던 task 를 되돌리는
  경우에만 `DEMOTION_REVERTS_DONE` 표식을 붙여 최상위 `status` 를 `warning` 으로
  올린다. `done` 이 아니던 task 의 강등에는 표식을 **안 붙인다** — 취소한 것이
  없는데 붙이면 늑대 소년이 된다.

부수로 SSOT 읽기를 `read_task_ssot_state()` 로 추출했다 (`main()` 인라인이라 검사가
붙을 자리가 없던 곳이고, 검증 라벨은 별칭까지 받는다).

**소비자 영향**: `wk backlog-update` 로 완료된 task 에 메모를 덧붙이는 흐름이
안전해진다. 이전 판을 쓰고 있다면 **재호출이 완료 기록을 조용히 되돌릴 수 있다.**

## 3. 업그레이드

`v1.8.1` 에서 올라오는 데 필요한 조치는 **없다**. 공개 API 제거·시그니처 변경·산출물
형식 변경이 없다.

바뀌는 것은 **`release --apply` 의 기본 엄격도** 하나다 (§2.1). CI 를 기다리지 않고
발행하던 절차가 있으면 순서를 바꾼다 — push → CI green 확인 → 발행.

```bash
pip install --force-reinstall standard_ai_workflow-1.9.0-py3-none-any.whl
# 또는 uv tool
uv tool install --force <wheel 경로>
```

설치본이 저장소 소스와 갈라졌는지는 `wk doctor` 의 `kit 사본` 줄이 말해 준다.

## 4. 검증

- 전량 2축 **279/279 ×2 PASS** (`--branch-context=all`, RUNNER_EXIT=0, 좁은 선언 0)
- mypy strict **0 errors**
- `check_release_ci_gate` 8/8 · `check_done_demotion_rule` 8/8 · `check_self_application` 8/8
- 반사실 실측 (§2.1): v1.8.0 발행 커밋 `6c495e61` 의 **실제 CI 결과**
  (smoke=failure, 나머지 3종 success)를 그대로 먹이면 `ok=False`,
  `blocking=['smoke']` — 새 게이트는 그 발행을 막았을 것이다
- 배선 실증 (§2.1): `verify_required_ci` 를 not-ok 로 주입하고
  `cmd_release(apply=True)` 호출 시 error 반환 + `_tag_create` 호출 **0회**
  (태그 생성 전에 멈춘다). missing / pending / fetch_error 도 4 case 로 차단 고정
- 재현 실측 (§2.2): 이미 `done` 인 task 에 `--status done --progress-note` 만으로
  재호출 → 최상위 `status=ok`, task 파일 `done` 유지, handoff §4 배치 유지
  (이전에는 §2 로 되돌아갔다)
- 되주입 red 실증 (§2.2): 기록된 검증을 무시하도록 되돌리면 `case_1`·`case_2` FAIL,
  `DEMOTION_REVERTS_DONE` 표식을 제거하면 `case_3` FAIL
- **이 발행 자신이 §2.1 게이트의 첫 실전 통과다** — 태그는 4종 필수 워크플로가
  전부 green 인 커밋에 붙었다

## 5. Commit

| Hash | Subject |
|---|---|
| `0453dabf` | chore(memory): 72차 세션 종료 — 손 목록·리터럴·주장을 파생으로 전환 5건 + v1.8.1 발행 |
| `e6f033db` | fix(backlog-update): done 강등이 이미 기록된 완료를 취소하지 않는다 (main-003) |
| `c49e2c74` | feat(release): 발행 게이트가 필수 CI 워크플로 전수를 보고 기본 차단한다 (main-005) |
| `54ff793e` | release(v1.8.1): 발행 완료 — 태그 push + GitHub Release(asset 4종) + post-step 정합 |

## 6. Reference

- 이전 release note: `Beta-v1.8.1.md`
- task SSOT: `TASK-2026-09-01-main-005` · `TASK-2026-09-01-main-003`
- 발행 task: `TASK-2026-09-02-main-001`
- 절차 정본: `docs/RELEASE.md` §2.3 (필수 CI 게이트)

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-09-01T15:25:19Z)_

- total wiki pages: **95**
- total memory entries: **15**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
