# 세션 기록 — 브랜치 메모리 네임스페이스 가드 (2026-08-13)

- 문서 목적: PR #23 세션 기록 §7 "남은 구멍" 을 닫은 작업과 판단 근거를 남긴다.
- 범위: `check_branch_memory_namespace` 신설, 정본 창구 정정, 전량 실패 3건 분류
- 대상 독자: AI agent, 저장소 관리자
- 상태: stable
- 최종 수정일: 2026-08-13
- 관련 문서: [task](../backlog/tasks/TASK-2026-08-13-fix-branch-memory-namespace-guard-001.md),
  [PR #23 세션 기록](../../../../archived/feat/plugin-harness-distribution/sessions/plugin_harness_distribution_pr23_2026-08-13.md)

## 1. 구멍은 하나가 아니라 둘이었다

§7 은 "작업 브랜치에 `active/<branch>/` 가 없다는 사실을 직접 지목하는 검사가 없다"
고 적었다. 실제로는 원인과 결과가 나뉜다:

- **(A) 원인** — 작업 브랜치가 *다른 브랜치 네임스페이스*(`active/main/`)에 task·
  handoff 를 추가/수정한다. 이걸 지목하는 자리가 아무 데도 없었다.
- **(B) 결과** — 자기 디렉터리가 안 생긴다. 3개 검사(`check_branch_context_matrix` /
  `check_claim_workspace` / `check_seed_workspace_memory`)의 **간접 증상**으로만 드러났다.

`check_appendonly_memory_layout` case 7 은 A 의 *사후* 흔적(ID 중복)만 잡는다 —
병합된 뒤다. 브랜치에서 일하는 동안에는 여전히 아무도 지적하지 않았다.

`check_branch_memory_namespace` (8 cases) 가 둘을 직접 지목한다. **커밋 전 워킹
트리까지** 본다 — 커밋된 뒤에 알려주는 가드는 이미 늦다.

## 2. 판정이 호스트 환경에 달리지 않게 한 것들

PR #23 이 같은 모양으로 세 번 데인 자리다 (그 기록 §5·§6). 설계에 그대로 반영했다:

- 네임스페이스 매핑은 **경로 내용만으로** 한다 (marker segment 앞까지가 slug).
  `feat/plugin-harness-distribution` 처럼 슬래시 든 브랜치명이 한 segment 로 잘리지
  않는다 — 4번째 비대칭이 정확히 그 자리에서 났다.
- CI 환경변수를 보지 않는다. 기본 브랜치는 `_detect_default_branch` (origin 이 있으면
  현재 브랜치로 내려가지 않게 고쳐진 그 함수) 를 쓴다.
- detached HEAD 는 **사유를 찍고 SKIP**. 조용한 PASS 는 금지 — 브랜치가 없으면
  "브랜치 네임스페이스" 라는 질문 자체가 성립하지 않는다.

**fixture 도 origin 을 갖게 만들었다.** 처음엔 origin 없는 temp 저장소로 쟀는데,
그러면 `_detect_default_branch` 가 *현재 브랜치*를 기본 브랜치로 돌려주어 검사가
통째로 skip 되면서 green 이 나왔다. 실제 저장소에서는 일어나지 않는 형상으로 얻은
green 이다. `refs/remotes/origin/HEAD` 는 일부러 안 만든다 — `actions/checkout` 이
그것을 만들지 않으므로 CI 와 같은 축으로 재기 위해서다.

## 3. 되주입

- fixture: PR #23 의 모양(작업 브랜치가 `active/main/` 에 task 추가)을 실제 git
  저장소로 재현 → FAIL + 오염 경로 지목 (case 4).
- **살아있는 저장소**: 이 브랜치에서 `active/main/backlog/tasks/` 에 파일 하나를
  심자 case 8 이 커밋 전에 FAIL 했다. 지우면 통과. 공허하지 않다.
- 반대 방향도 잰다 — 삭제(archive piggyback)와 정상 브랜치를 red 로 만들지 않는지
  (case 3·6). `archive_branch_memory.py` 를 작업 브랜치에서 돌려 PR 에 싣는 것은
  **정본 절차**라, 삭제까지 잡으면 정본 절차가 red 가 된다.

## 4. §4 의 진단이 절반 틀렸다 (이번 세션의 실질 발견)

PR #23 §4 는 "만드는 자리는 `wk backlog-update` 하나다" 라고 적었다. **그대로
따랐더니 전량에서 3검사가 red 였다**:

    check_appendonly_memory_layout   sessions/ 디렉토리 부재
    check_memory_freeze_lint         [V-R10] Missing in active/<branch>/: sessions/
    check_self_application           missing_required_document

`backlog-update` 는 `tasks_dir.mkdir()` 의 **부수효과로** `backlog/` 만 만든다.
`sessions/` 와 `session_handoff.md` 가 없는 **절반짜리 네임스페이스**가 된다.
한 벌로 만드는 정본 창구는 **`wk seed-workspace-memory`** 다 — 그 도구의 docstring
이 바로 이 실패(`missing_required_document`)를 계보로 적고 있다.

이게 중요한 이유: **도구를 옳게 썼는데도 red** 면 다음 사람은 다시 손 편집으로
도망간다. 검사만 세우고 안내를 안 고쳤으면 구멍을 반만 메운 것이다. 그래서
새 검사의 (B) 안내 문구는 `seed-workspace-memory` + `refresh-state` 를 가리키고,
`backlog-update` 만 쓰면 무엇이 빠지는지까지 적는다.

올바른 순서(이번에 실측):

```
git checkout -b <branch>
wk seed-workspace-memory --branch <branch> --axis … --task-title … --apply
wk backlog-update … --mode update      # 이후 갱신
wk refresh-state                        # state.json 은 파생물
```

`MEMORY_GOVERNANCE.md` 의 branch-scoped layout 절에 이 순서를 정본으로 적었고,
PR #23 §4 에는 정정 블록을 달았다 (원문은 남긴다 — 발행된 서술을 고쳐 쓰지 않는다).

## 5. 전량 실패 3건의 분류 — 2건은 main 의 기존 red

전량을 돌리자 내 변경과 무관한 실패 2건이 나왔다. **stash 후 깨끗한 트리에서
재현**해 기존 것임을 확인했다:

- **`check_release_pipeline_phase2`** — 확실한 회귀. v1.2.0 이 native plugin ZIP
  게이트를 앞단에 더해 `plugin archives missing` 이 dist 판정보다 **먼저** 걸리는데,
  test 의 acceptable 목록이 안 넓혀졌다. test 가 재는 것은 *어느* 단계에서 멈추느냐가
  아니라 **graceful 하게 멈추느냐** 이므로 목록에 그 메시지를 더해 수리했다.
  구조적으로는 단계를 늘릴 때마다 깨지는 모양이라 별도 설계 여지를 주석에 남겼다.
- **`check_mavis_attach_e2e`** — read-only 번들이 13종을 노출한다고 기대하는데 11종이다
  (빠진 둘은 `apply_robust_patch` / `rotate_workflow_logs` — **write 도구**).
  v1.2.0 의 `--bundle` 기본값 `all`→`read-only` 전환과 정면으로 어긋난다.
  **고치지 않았다** — 기대치를 11 로 낮출 일인지(번들 분리 의도대로), 검사를
  `--bundle all` 로 붙일 일인지는 의도 판정이라 추측으로 정할 수 없다.
  handoff §6 의 "darwin mavis e2e 재확인 필요" 가 바로 이 축이고, 답은 **red** 다.
  별건 task 로 등록했다.

두 건 모두 handoff 의 "전량 2축 253/253 green" 과 어긋난다. 릴리스 노트의 살아있는
수치가 *최신 전량 결과*를 반영해야 한다는 규약(`verify_release_note_smoke_count`)이
있는데, 그 수치는 **총 파일 수**만 강제하고 PASS 수는 강제하지 않는다.

## 6. 자기 리뷰에서 나온 결함 3건 (PR #24 리뷰 라운드)

전부 **추측이 아니라 실측으로 재현**한 뒤 고쳤다. 셋 다 검사를 조용히 무력화한다.

1. **porcelain rename 파싱** — git 은 rename 을 한 줄에 `R  old -> new` 로 준다.
   `line[3:]` 을 경로로 쓰면 `"old -> new"` 라는 없는 경로가 되어 매칭이 통째로
   샌다. **남의 네임스페이스로 파일을 옮기는 것이 정확히 그 형태**라, 가장 잡아야 할
   조작을 못 잡고 있었다. → case 9.
2. **비ASCII 경로** — git 이 `"d/\355\225\234\352\270\200.md"` 로 따옴표
   이스케이프한다. 선두 `"` 때문에 접두사 매칭이 빗나간다. 이 저장소는 문서가
   한국어라 실제로 밟을 수 있는 자리다. → case 10.
   1·2 는 `git diff`/`git status` 를 **`-z`** 로 읽어 함께 닫았다 (이스케이프 없음 +
   rename 두 경로가 별도 토큰).
3. **브랜치 이름에 marker segment** — `feat/backlog` 에서 marker 탐색이 첫 번째
   `backlog` 에 멈춰 네임스페이스를 `feat` 로 읽고 **자기 파일을 남의 것으로 지목**
   했다 (오탐). 자기 것인지는 `namespace_of` 가 아니라 **접두사**로 재야 한다.
   `active/feat/backlog/…` 의 애매함은 git 이 `feat` 와 `feat/backlog` 를 동시에
   가질 수 없다는 사실이 없앤다. → case 11.

**CI 유효 범위도 과장하지 않게 적었다**: `smoke.yml` 은 `fetch-depth: 0` 이라
push 셀에서는 `origin/main` 이 있고 브랜치가 체크아웃돼 판정이 돈다. pull_request
셀은 detached 라 SKIP 이다 — CI 에서 이 검사를 밟는 축은 **push 셀 하나**다.

## 7. CI mypy flake 재발 (TASK-2026-08-13-main-004)

PR #24 의 첫 커밋 native 셀이 `check_mypy_strict_ci_v0_11_11` 로 red 였다:
`CI mypy invocation exit 2 (0 errors in workflow_kit/)`. 같은 내용의 두 번째 push
는 통과했다 — 알려진 flake 의 재발이고, handoff 가 세던 **연속 green 카운터(5)가
깨졌다**. exit 2 는 mypy 의 usage/internal error 계열이라 "0 errors 인데 실패" 가
성립한다 (병렬 부하에서의 cache race 가설과 맞는 모양).

이 관측은 `active/main/` 의 task 소속이라 **이 브랜치에서 고치지 않았다** — 그게
이 PR 이 세우는 규칙 자체다. main 에서 별도로 반영한다.

## 8. 남은 것

- `check_mavis_attach_e2e` 기대치 판정 (의도 확인 필요).
- 전량 실행 시간 — 벽시계의 36% 가 정숙 구간(직렬)이고 그 65% 가
  `check_no_repo_write` 하나다. 별건 task 로 등록.
