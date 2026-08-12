# 7차 세션 — backlog-update 병합 의미론 (2026-08-12)

- 문서 목적: TASK-2026-08-11-main-023 종결 기록.
- 상태: done
- 관련: [TASK-023](../backlog/tasks/TASK-2026-08-11-main-023.md), [6차 세션 기록](./state_generated_and_composition_review_2026-08-11.md) §3

## 요약

`wk backlog-update --mode update` 가 **재생성에서 병합으로** 바뀌었다. 6차 세션에서
이 도구의 첫 실사용이 TASK-018 파일을 깎아 손 복원했던 결함의 처방.

| 변경 | 내용 |
|---|---|
| `merge_task_file` 신설 (`workflow_writes.py`) | 기존 task SSOT 를 원본으로 명시 인자만 반영. 미반영 라벨은 경고로 노출 (조용히 버리지 않음). `검증 결과` 는 done 근거라 줄이 없으면 `작업 결과` 뒤에 삽입 |
| `_upsert_index_block` preserve 모드 | update 시 index block 을 교체하지 않고 `- status:` 줄만 교체 — head 의 `[kind]`·제목과 `notes:` 등 손 sub-bullet 보존 |
| `sync_handoff_status` ID dedupe | 표기가 달라도 같은 task ID 면 하나로 — "TASK-X — 제목" vs "TASK-X 제목" 중복 제거. done 전이 시 in_progress 에서 ID 로 제거 |
| `--kind` / `--priority` default None | update 미지정 시 기존 값 보존 (create 는 generic/high). argparse default 로는 "명시 안 함" 을 구분할 수 없었다 |
| 제목 불일치 | 기존 제목 유지 + 경고 (제목이 미지정 호출로 덮이지 않는다) |

검증: `check_backlog_update_layout` 5→**8 case** — 신설 3 case (필드 보존 / index 보존 /
handoff dedupe) 는 **버그 코드로 되돌리면 전부 FAIL** (되주입 실증). 종결 자체를 고친
도구로 수행해 실전 검증 (TASK-023 파일이 update 3회에도 원문 보존).

남긴 것: update 모드 `--status` 미지정 시 `in_progress` 로 리셋되는 보수 규칙은 기존
문서화된 동작이라 유지 — 바꾸려면 별도 논의.
