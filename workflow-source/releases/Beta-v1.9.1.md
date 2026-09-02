# Beta v1.9.1 (2026-09-03)

> **상태: 릴리스 준비.** package `1.9.1`, runtime `__version__ = 1.9.1`, tag `v1.9.1`.
> **patch release** — 세션을 열 때마다 뜨던 거짓 경고 하나를 없앤다.
>
> 등급 근거 (§1.5): 공개 API 시그니처 변경 0 · 진입점 제거 0 · 산출물 형식 변경 0
> (`warnings` 는 그대로 `list[str]`). 새로 생긴 심볼 3개는 새 기능이 아니라 결함
> 수리를 구현하려고 쪼갠 내부 헬퍼다. `wk release-status` 파생도 patch
> (breaking 0 / feat 0 / fix 1).

## 0. 릴리스 판정

이 사이클의 주제는 **"경고가 재는 분모가 정본과 같은가"** 다.

`session-start` 는 handoff 의 열린 작업이 backlog 와 맞는지 본다고 적혀 있었다.
그런데 비교 대상이 backlog SSOT 가 아니라 **오늘자 daily 파일 하나**였다.
append-only 레이아웃에서 `in_progress` task 는 *등록된 날짜의 파일*에 있으므로,
하루 안에 끝나지 않은 작업이 하나만 있어도 **날이 바뀌는 순간부터 매 세션
시작마다** 거짓 경고가 났다.

`state.json` 생성기는 같은 질문에 대해 `backlog/tasks/` 전수를 본다. 즉 같은
저장소 안에서 **정본과 경고가 서로 다른 분모를 쓰고 있었다.**

**이 릴리스에는 발행해야 할 이유가 있다.** 이 경고는 거의 항상 거짓이라
늑대 소년이 되고, `recommended_next_action` 까지 점거해 세션의 첫 행동을
"불일치 여부를 먼저 확인한다" 로 밀어낸다. 즉 비용이 세션마다 반복된다.
v1.9.0 소비자는 지금 그 상태다.

## 1. 릴리스 요약

- 범위: `v1.9.0..HEAD` (2 commit). 이 중 1건(`573fa786`)은 **v1.9.0 발행 마무리**가
  태그 뒤에 착지한 것이라 실질 내용은 1 commit 이다.
- 누적 smoke **280/280 PASS** (전량 2축 · case 합계 560, FAIL 0, 좁은 선언 0),
  mypy strict 0 errors
- 검사 신설 1종 (`check_state_reconcile` 7 cases)
- 지원 하네스 12 (변동 없음), MCP 표면 13 (변동 없음)
- 공개 API **+3** (`state.builder.collect_task_corpus_status` ·
  `reconcile.diff_state_lists` · `reconcile.STATE_CONFLICT_MARKER`) — 제거 0

## 2. 소비자 가시 변경

### 2.1 fix(session-start) — 상태 불일치 경고의 분모가 task corpus 전수가 된다 (`b3f3eff9`)

**증상이 바뀐다. 이전에는 정합인 저장소에서도 경고가 났다.**

결함은 세 겹이었고, 세 개가 겹쳐야 이만큼 조용히 나쁘다.

- **분모**: `compare_state_lists` 가 handoff 의 열린 작업 전체를 *오늘자 daily
  backlog 하나* 와 비교했다. 실측(2026-09-02, 이 저장소): task corpus 전수의
  `in_progress` 는 handoff 와 정확히 일치하는데, 오늘자 backlog 는 비어 있어
  불일치로 보고됐다.
- **키**: 문자열 집합 비교라 handoff 의 `TASK-… <제목>` 과 corpus 의 `TASK-…`
  가 서로 다른 원소였다. 같은 저장소의 `dedupe_work_items` 는 이미
  `WORK_ITEM_ID_RE` 로 ID 를 키로 쓴다 — 정본은 ID 로 볼 줄 알았고 **경고
  경로만** 몰랐다.
- **설명**: 문안이 "다를 수 있으므로 수동 재확인이 필요하다" 뿐이었다. 차집합은
  도구가 이미 두 목록으로 들고 있었는데, 사람이 매번 두 문서를 손으로 대조했다.

**수리**: `collect_task_corpus_status()` 신설 — `state.json` 생성기가 쓰는 것과
**같은 집계**를 노출한다. 비교는 task ID 를 키로 하고(선두 inline backtick 도
걷는다), 경고는 `handoff 에만: … / backlog 에만: …` 로 어느 항목이 어느 쪽에만
있는지 짚는다.

**corpus 부재는 "비었다" 가 아니다.** `collect_task_corpus_status` 는 corpus 가
없으면 `None` 을 돌려주고, 호출자는 그때만 종전대로 daily backlog 를 쓴다. 둘을
같게 보면 append-only 로 아직 이관되지 않은 legacy 프로젝트에서 handoff 전체가
'분모에 없는 항목' 으로 뒤집혀 나온다.

**분모의 뿌리는 profile 이 아니라 방금 고른 backlog 문서 자신(`.parent`)이다.**
첫 구현이 profile 파생 경로를 썼는데, `--session-handoff-path` /
`--work-backlog-index-path` 로 다른 워크스페이스를 가리키면서 profile 만 호스트
저장소를 쓰는 호출이 실재한다(seed / claim 스모크). 그 조합에서 남의 저장소
task 와 대조하게 된다 — 게이트가 잡았다.

`merge-doc-reconcile` 의 `state_conflicts` 도 같은 분모 오판을 갖고 있었고 같이
고쳤다. 두 소비자가 이제 `reconcile.py` 의 한 코어를 쓴다 —
`explain_state_conflicts` 는 호출자가 하나뿐인 사실상 사문이었다.

**경고 문안이 바뀐다.** 그 줄을 리터럴로 매칭하던 소비자가 있다면
`reconcile.STATE_CONFLICT_MARKER` 를 쓴다 — 사본을 들고 가면 문안이 바뀌는 순간
조용히 아무것도 안 고른다.

## 3. 업그레이드

전역 설치본은 재설치해야 이 수리가 반영된다. `wk doctor` 의 `kit 사본` 줄이
돌고 있는 사본과 저장소 소스의 정합을 말해 준다.

```bash
uv tool install --force \
  "standard-ai-workflow @ https://github.com/ykylee/standard_ai_workflow/releases/download/v1.9.1/standard_ai_workflow-1.9.1-py3-none-any.whl"
wk doctor | head -12
```

`session_handoff.md` / `backlog/tasks/` 형식 변경은 없다 — 마이그레이션 불필요.

## 4. 검증

- 전량 2축 **280/280 ×2 PASS** (`--branch-context=all`, RUNNER_EXIT=0,
  native 134.2s / slash 131.4s, 좁은 선언 0)
- mypy strict **0 errors** (203 source files)
- CI `b3f3eff9` 필수 4종 전부 success (`smoke` · `mypy-strict` · `os-matrix` ·
  `mcp-sdk-matrix`) + `mkdocs` success
- 신설 `check_state_reconcile` **7 cases** — 되주입 red 를 **양방향**으로 건다:
  corpus 에 없는 항목이 handoff 에 있을 때 / handoff 가 corpus 의 열린 작업을
  통째로 빠뜨렸을 때. 한 방향만 재면 "아무것도 안 잡는" 구현이 통과한다.
- 실증: 이 저장소 `session-start` 경고 **1건 → 0건**, `recommended_next_action`
  이 "불일치 여부를 먼저 확인한다" 에서 벗어남

## 5. Commit

| Hash | Subject |
|---|---|
| `b3f3eff9` | fix(session-start): 상태 불일치 경고의 분모를 task corpus 전수로 바꾼다 (main-002) |
| `573fa786` | release(v1.9.0): 발행 완료 — 태그 push + GitHub Release(asset 4종) + post-step 정합 |

## 6. Reference

- 이전 release note: `Beta-v1.9.0.md`
- task SSOT: `TASK-2026-09-02-main-002`
- 비교 정본: `workflow_kit/common/reconcile.py`
- 분모 정본: `workflow_kit/common/state/builder.py` (`collect_task_corpus_status`)
