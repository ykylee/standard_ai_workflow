# 세션 기록 — 아카이브 이력 무결성 (2026-08-13)

- 문서 목적: 브랜치 아카이브가 이력을 끊던 자리와 그 수리를 남긴다.
- 범위: `archive_branch_memory` 이관 도입, `check_archive_history_integrity` 신설, 기존 이력 복구
- 대상 독자: AI agent, 저장소 관리자
- 상태: stable
- 최종 수정일: 2026-08-13
- 관련 문서: [task](../backlog/tasks/TASK-2026-08-13-fix-archive-history-integrity-001.md)

## 1. 아카이브는 "이동" 만 하고 있었다

`archive_branch_memory` 는 `active/<branch>/` 를 `archived/<branch>/` 로 옮기기만 했다.
**이관이라는 개념이 없었다.** 두 갈래로 이력이 끊겼다:

**(A) 미완료 task 소실.** 도구는 task 파일을 세어 `.archived.json` 에 id 를 적으면서
**status 를 보지 않았다**. `archived/` 는 어떤 집계도 읽지 않는다 — state 생성기에
`archived` 참조 0건, dashboard 는 `active/*/state.json` 만 훑는다. 그래서 미완료 task 는
옮겨지는 순간 **어디에서도 안 보이게** 된다. 직전 세션에서 `…-guard-003`(planned)이
정확히 그렇게 사라졌고, 도구도 검사도 아닌 **사람 눈**이 알아채 이월했다.

**(B) 참조 미재작성.** 옮긴 뒤 그 경로를 가리키던 링크를 아무도 안 고쳤다. 실측:

- 아카이브된 문서 **22개 중 12개**가 깨진 링크 보유
- `archived/feat/plugin-harness-distribution/state.json` 의 `source_of_truth`
  **5개 경로 전부**가 사라진 `active/…` 를 가리킴
- `codex/phase6` 의 11개 파일은 **1.5개월간** 죽은 참조를 들고 있었다

**그런데 전량 254/254 는 green 이었다.** `check_doc_links` 는 `doc_dir_path` 를 받는
on-demand MCP 도구지 저장소를 훑는 smoke 가 아니다. `archived/` 아래는 아무도 안 봤고,
회귀 방지 장치가 없으니 깨짐이 쌓이기만 했다.

## 2. 수리 — 이동에 두 걸음을 붙였다

**차단이 기본이다.** 미완료 task 가 있으면 아카이브를 막고 어느 task 때문인지 지목한다.
exit code 도 0이 아니다 (CI 가 봐야 한다). *보이게 하는 것으로는 부족하다* — 이월 여부는
사람이 판단할 일이고, 그 판단 전에 옮기면 판단할 기회 자체가 사라진다. 의도적으로 넘기려면
`--allow-open-tasks` 이고 그 사실이 `.archived.json` 의 `open_task_ids` 에 남는다.

**`carried_over_to` 는 별도 축이다.** 브랜치는 끝났는데 일이 안 끝난 경우가 있다. 그때
`done` 으로 적으면 **거짓**이다. 진행 상태와 이관 사실을 한 칸에 섞지 않는다는 §2.39 의
원칙 그대로, 이관은 별도 key 로 적고 차단 판정만 면제한다 — 어디로 갔는지가 파일에 남아
추적이 끊기지 않는다. `guard-003` 에 `carried_over_to: TASK-2026-08-13-main-009` 를 적었고
`status: planned` 는 그대로 뒀다.

**참조는 해석해서 옮긴다.** `../../../active/<branch>/…` 같은 상대 경로는 문자열 치환이
안 통한다. 링크를 resolve 해서 *대상이 없고* archived 쪽에 있을 때만 그 파일 기준 상대
경로로 다시 쓴다. **살아 있는 링크는 안 건드린다** — 고치는 쪽이 손상이 되면 안 된다
(case 6 이 이 방향을 잰다).

## 3. 만들면서 같은 결함을 두 번 밟았다

참조 재작성이 fixture 에서 no-op 이었다. 두 자리 다 **memory root 가 저장소 밖일 때**
망가지는 형태였다:

- `.md` 스캔이 `repo_root.rglob` 만 돌았다 → 저장소 밖 memory root 는 안 훑는다
- `state.json` 치환이 *저장소 상대* 접두사를 썼다 → 밖이면 절대 경로라 안 맞는다

이 kit 은 외부 프로젝트에 배포되고 `_move` 는 이미 "memory root 가 repo 밖일 수 있다" 를
전제하고 있었다. 같은 전제를 새 코드가 안 지킨 것이다. 스캔은 두 root 를 돌게 했고,
치환은 `active/<branch>/` **경로 조각**을 옮기되 앞에 경계를 요구해 `inactive/…` 에
잘못 걸리지 않게 했다.

## 4. 기존 이력 복구

- **`state.json` 2건** — 도구 자신(`rewrite_moved_references`)으로 고쳤다. 직전 세션에
  아카이브한 브랜치의 것도 깨져 있었는데 그때는 몰랐다.
- **링크 1건** — `archived/feat/…/sessions/…:166`. 조사해 보니 *이동 때문이 아니라
  **처음 쓸 때부터 잘못*** 이었다 (`../../../active/…` 는 `archived/active/…` 로 풀린다).
  archived 를 아무도 안 봐서 드러나지 않았을 뿐이다. 신설 검사가 잡는 부류가 이것이다.
- **죽은 참조 11건** — `codex/phase6` → `gemini/phase10/work_backlog.md`. 대상은
  2026-08-11 아카이브 정리(TASK-2026-08-11-main-003, 185파일 제거)로 **영구 삭제**됐다.
  링크를 걷고 `` `경로` (삭제됨 — …) `` 로 사실만 남겼다. 이력이므로 문장은 보존한다.

## 5. 부수 — 차단 규칙이 기존 검사를 깼다

`check_branch_scoped_memory` 의 fixture 가 task 를 `# t` 한 줄로 만들었다. status 미기재는
새 규칙에서 미완료이므로 아카이브가 막혀 3 케이스가 red 가 됐다. fixture 를
`status: done` 으로 고쳤다 — 그 검사가 재는 것은 아카이브 *기전*이지 미완료 정책이 아니고,
"종료된 브랜치" 를 흉내 내려면 끝난 것으로 적는 게 맞다.

## 6. seed 가 끝을 안 맺고 있었다 (같은 뿌리의 반대편)

아카이브가 이력의 *끝*을 안 맺었다면, seed 는 *시작*을 안 맺고 있었다.

`seed_workspace_memory` 는 `state.json` 을 **일부러 안 만들었다** — "파생물이므로
generate_workflow_state.py 가 만든다". 판단 자체는 맞다. 그런데 그 결과가 **seed 직후의
브랜치는 항상 절반짜리**였고, `wk refresh-state` 를 따로 돌리기 전까지
`check_appendonly_memory_layout` / `check_memory_freeze_lint` /
`check_branch_context_matrix` 가 red 였다. 이 세션에서만 **두 번** 밟았다.

"파생물이니 손으로 쓰지 않는다" 와 "파생물이니 나중에" 는 다른 말이다. 앞은 규율이고
뒤는 미완성이다. 이제 seed 가 **생성기를 호출해** 마무리한다 — 여전히 생성물이고,
달라진 것은 그 호출을 누가 책임지느냐다. 한 번 돌리면 시작할 수 있는 상태가 된다.

`check_seed_workspace_memory` 의 case 4 가 정확히 반대 계약(`test_no_state_json`)을
고정하고 있었으므로 함께 뒤집었다.

**가드도 같이 강화했다.** `check_branch_memory_namespace` 의 (B) 는 `is_dir()` 만 봐서
**절반짜리를 통과시키고 있었다** — 가드가 있는데 못 잡는 상태였다. `backlog` /
`sessions` / `session_handoff.md` / `state.json` 네 가지를 요구하고, 없는 것을 지목한다
(case 12 신설).

## 7. 이 브랜치에서 내 가드에 두 번 걸렸다

둘 다 **정당한 검출**이라 우회하지 않고 따랐다.

- `active/main/session_handoff.md` 를 이 브랜치에서 고치려다 case 8 이 잡았다. 되돌리고
  main 에서 반영한다 — 그게 이 규칙의 존재 이유다.
- `check_convention_single_source` 가 `_generate_state` 의 경로 조립을 정본 사본으로
  지목했다. `state_path_in_active` 로 바꿨다. 그러고도 한 번 더 걸렸는데, 이번엔
  **그 사실을 설명하는 주석 문구 자체**가 탐지 패턴(`/` + 리터럴)에 걸린 것이었다.

## 8. 자기 리뷰에서 나온 결함 5건 (PR #25 리뷰 라운드)

전부 실측으로 재현한 뒤 고쳤다. **가장 위험한 것이 첫 번째**다.

1. **본문의 `status:` 를 frontmatter 로 오인** — 파일 앞 20줄을 그냥 훑고 있었다.
   본문에 `status: done` 이 한 줄만 있으면 **미완료 task 가 완료로 판정되어 그대로
   아카이브로 사라진다** — 이 함수가 막으려던 바로 그 사고를 이 함수가 일으킨다.
   앞머리 `---` 블록만 읽도록 고쳤다.
2. **긴 frontmatter 의 status 누락** — 20줄 상한 때문. 상한을 없앴다 (블록 끝까지 읽는다).
3. **root 를 resolve 안 하면 재작성이 통째로 침묵** — macOS 의 `/var` ↔ `/private/var`
   심링크 하나로 `relative_to` 가 전부 ValueError 가 되어 **아무것도 안 고치고 오류도
   안 났다**. 조용한 no-op 이 최악이다. 함수 안에서 양쪽 root 와 `doc_dir` 을 맞춘다
   (한쪽만 맞추면 상대 경로가 `../../../private/var/…` 로 터무니없어진다 — 이것도 밟았다).
4. **앵커 소실** — `s.md#sec` → `s.md`. 링크는 살아나지만 문서의 엉뚱한 곳으로 간다.
   **고친 척하고 정보를 잃는 쪽이 더 나쁘다.** 앵커를 보존한다.
5. **제목·꺾쇠 링크 미처리** — `](path "제목")` / `](<path>)` 는 CommonMark 정식 형태인데
   경로 매칭이 빗나가 깨진 채 남았다.

case 11~13 으로 고정 (10 → 13 cases).

## 9. 남은 것

- 신설 검사는 `archived/` 만 본다. `active/` 의 깨진 링크는 여전히 `check_self_application`
  이 handoff 를 린트할 때만 걸린다 — 저장소 전역 링크 검사는 없다.
- `.archived.json` 의 `merge_commit` 은 `--grep=Merge.*<branch>` 로 찾는다. squash merge
  에서는 그 문구가 없을 수 있다 (이 저장소는 merge 커밋을 쓰므로 지금은 성립).
