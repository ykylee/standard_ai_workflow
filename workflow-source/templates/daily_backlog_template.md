# Backlog Index — YYYY-MM-DD

- 문서 목적: 해당 날짜의 작업 항목(task) SSOT link 모음.
- 범위: 해당 일자(task 단위)의 모든 task.
- 대상 독자: AI agent (session-start / backlog-update), maintainer.
- 상태: stable (v0.14.0 append-only layout).
- 최종 수정일: 2026-08-24
- 관련 문서: [./tasks/](./tasks/) (per-task SSOT)

## Tasks

- **TASK-YYYY-MM-DD-<slug>-001** [generic] <작업명>
  - path: [`./tasks/TASK-YYYY-MM-DD-<slug>-001.md`](./tasks/TASK-YYYY-MM-DD-<slug>-001.md)
  - status: planned | in_progress | blocked | done

> **이 파일은 index 다** (v0.14.0+ append-only layout). 작업 본문은
> `./tasks/<TASK-ID>.md` 가 갖는다 — 여기에 계획/실행/검증 절을 적지 않는다.
> 항목은 `wk backlog-update` 가 추가·갱신한다. 손으로 고치면 파싱 계약이
> 조용히 깨진다 (`MEMORY_GOVERNANCE.md` §2).

> 머리말과 항목 형식의 정본은 `workflow_kit.common.workflow_writes` 의
> `render_daily_backlog_header` / `daily_index_entry_lines` 다. 이 파일은
> 그 산출물의 **사본**이고, `check_daily_backlog_template` 이 일치를 강제한다
> — 사본을 검사 없이 두면 갈라진다 (TASK-2026-08-24-main-003).
