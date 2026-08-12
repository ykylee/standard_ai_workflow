# 19차 세션 — status 보존 규칙 + 실행-중 감시 (2026-08-12)

- 문서 목적: TASK-2026-08-12-main-008 (--status 보존) + 009 (no_repo_write 실행-중 감시) 종결 기록.
- 상태: done
- 관련: [TASK-008](../backlog/tasks/TASK-2026-08-12-main-008.md), [TASK-009](../backlog/tasks/TASK-2026-08-12-main-009.md)

## 1. backlog-update `--status` 보존 (TASK-023 후속)

update 에서 `--status` 미지정이면 **기존 상태 보존** — 이전 규칙은 무조건
`in_progress` 라 planned task 에 메모만 다는 호출이 상태를 승격시키고 done 을
되돌렸다. 미지정은 "바꾸지 말라" 다. done 강등(검증 없는 done 금지)은 **명시
요청에만** — 기존 done 보존은 재강등하지 않는다 (이미 검증과 함께 기록된 상태).
layout 검사 8→9 case, 되주입 실증.

## 2. `check_no_repo_write` 실행-중 감시 (§6 리스크 해소)

전후 비교는 "건드렸다 되돌리면 통과" 했다 — bidir 가 감시 목록에 **있으면서도**
그렇게 빠져나간 전력 (transient pyproject writer 미스터리와 같은 뿌리). 이제 실행
중 porcelain 을 0.15s 폴링해 중간 접촉을 잡는다:

- 판정 3층: 전후 불일치(기존 hard) / **미지 transient = FAIL** / 알려진
  touch-and-restore 는 이유 명시 원장 (타이밍 의존이라 **단방향** — 폴링의 음성은
  증명이 아니다, 과장 금지).
- 되주입: fixture git 저장소에서 touch-1s-restore 검출 + 무접촉 위양성 0.
- **실측: 감시 13개 전부 실행-중 무접촉** — 우려했던 "다수 red" 는 TASK-019 의
  사본 이관들이 이미 해소해 둔 상태였음을 확인. 원장은 공집합에서 출발.

## 교훈

- "되돌리는 것은 안 건드리는 것이 아니다" 가 이제 검사 문장이 됐다 — transient
  writer 재발 시 no_repo_write 가 1차 검출층, watch_transient_writer 가 정밀
  포렌식층.
