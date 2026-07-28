# 세션 기록 — "최근 완료" 목록이 최신을 고른 적이 없었다 (2026-07-28)

- 문서 목적: 이 세션이 무엇을 재고, 무엇을 틀렸고, 무엇을 남겼는지 다음 세션이 이어받게 한다.
- 범위: TASK-2026-07-28-main-001 (§2.38)
- 대상 독자: AI agent, 저장소 관리자
- 상태: closed
- 최종 수정일: 2026-07-28
- 관련 문서: [state.json](../state.json), [session_handoff.md](../session_handoff.md),
  [TASK-2026-07-28-main-001](../backlog/tasks/TASK-2026-07-28-main-001.md),
  `workflow-source/releases/Beta-v1.0.0.md` §2.38

## 1. 시작 지점

직전 세션이 §2.37 에 **미조치**로 적어 둔 한 줄이다 — *"정렬이 시간순이 아니라 오래된 항목이
남고 최근 항목이 밀린다"*. 사용자가 이것부터 잡자고 했다.

## 2. 무엇이었나

한 줄짜리 증상인 줄 알았는데 **정렬 키라는 것이 애초에 없었다**. 결함 4개가 전부 같은 함수
(`_aggregate_from_appendonly_layout` + `build_workflow_state_payload`)에 있었다.

| # | 결함 | 실측 |
|---|---|---|
| 1 | 상한 `10` 이 두 곳, **자르는 방향이 반대** (`[-10:]` vs `[:10]`) | 서로 무효화, 어느 쪽도 "최신" 기준 아님 |
| 2 | 정렬 키 부재 — `tasks_dir(사전순) ++ daily 잔여분(날짜순)` 조립 순서가 곧 순서 | 가장 오래된 5건이 목록 뒤 절반을 차지 |
| 3 | 병합 순서가 `handoff §4` → `appendonly` | 상한 없는 파생물이 task SSOT 를 밀어냄 |
| 4 | daily index fallback 이 미분류 ID 를 무조건 `done` 으로 | `status: recorded` 3건이 **완료로 날조**됨 |

4번은 찾으러 간 게 아니라 2번을 재현하다 나왔다. `TASK-2026-04-24-001` 이 왜 done 목록에
있는지 물어보니 task 파일에는 `status: recorded` 가 적혀 있었다 —
`migrate_active_to_appendonly.py` 가 표준 어휘 밖의 값을 쓰고 있고, builder 는 그 값을 몰라
세 목록 어디에도 넣지 않았으며, fallback 이 그걸 done 으로 되살렸다.

## 3. 조치

- `RECENT_DONE_ITEMS_CAP` 단일 출처 — aggregate 는 자르지 않고 builder 가 한 번만 자른다
- `_task_recency_key` — `completed_at` → `updated_at` → `created_at` → ID 날짜 fallback,
  **최신순** 정렬 (소비자가 전부 앞에서 자른다)
- 병합 순서를 task SSOT → handoff 로. `tasks_dir` 없는 legacy 저장소에서는 handoff 가 그대로
- `project_docs.TASK_STATUSES` 단일 출처 — `STATUS_RE` / `WORK_STATUS_RE` 를 여기서 조립
  (같은 목록이 두 정규식에 리터럴로 복제돼 있었다. 조립 후 패턴 문자열이 이전과 byte-identical
  인 것을 확인했다)
- 어휘 밖 status 는 `unknown_status_items` 로 노출. task 파일이 있으면 daily index 가 판정을
  덮어쓰지 못한다

## 4. 검증

- 신규 `check_recent_done_items_order.py` 5건. **되주입 시 5/5 가 각각 다른 증상으로 실패**
  하는 것을 확인했다 (상한 slice 되돌림 → 최신 밀림 / fallback 되돌림 → `recorded`·`planned`
  가 done / 병합 순서 되돌림 → 10칸 전부 handoff 항목). 픽스처는 손으로 쓰지 않고 프로덕션
  writer(`upsert_backlog_entry`)로 만든다.
- 전량 smoke **218/218 PASS** (`.venv/bin/python`, 격리 tmp-dir, 저장소 변경 0)
- mypy strict **119 files, 0 errors** (`--config-file workflow-source/pyproject.toml` 명시)
- E2E: `backlog-update --apply` 산출물을 `git diff` 로 검토 — 최신순 정렬 + `TASK-2026-07-22-003`
  복귀 + `recorded` 3건 이탈 확인

첫 smoke 실행에서 3건이 red 였는데 전부 같은 원인이었다 — 스모크 파일 수 선언 217 vs 실제
218. 저장소의 "선언과 사실" 검사가 제 일을 한 것이라, 선언 쪽(`CODE_INDEX.md`,
`INSTALLATION_AND_USAGE.md`, 릴리스 노트 §3)을 218 로 맞췄다.

## 5. 남긴 것

- **`recorded` 어휘 문제는 governance 결정** 이라 손대지 않았다. 뜻하는 상태는 실재하는데
  표준 어휘 넷에 없다. 기존 3건도 **완료 여부를 확인하지 않았으므로** 상태를 바꾸지 않았다.
- dashboard Panel 5 는 브랜치 간 정렬 키가 여전히 없다 (항목 문자열에 날짜가 없다).
- `_task_recency_key` 는 **등록일 근사**다. 같은 날 여러 건이 서로 다른 날 완료된 경우는
  구분하지 못한다. writer 가 `completed_at` 을 채우면 별도 수정 없이 정확해지도록 해 뒀다.

## 6. 다음 세션에

`git status` 로 커밋 여부부터 확인할 것. 이 세션은 memory 갱신까지 마쳤고 commit/push 는
사용자 확인 대기였다.
