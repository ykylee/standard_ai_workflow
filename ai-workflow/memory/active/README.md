# Active Memory — 운영 가이드 (v0.14.0 신규 layout)

- **문서 목적**: 본 디렉토리(`ai-workflow/memory/active/`)의 **append-only + rebuild** 모델 운영 규칙 + 신규 layout 명세
- **범위**: 디렉토리 구조, 파일별 책임, write/read 권한, 마이그레이션 노트
- **대상 독자**: AI agent (session-start / backlog-update / doc-sync), maintainer, 다음 세션의 본인
- **상태**: stable (v0.14.0 부터 신규 layout 적용, **1st deprecation cycle** 진행 중 — `work_backlog.md` fallback 유지)
- **최종 수정일**: 2026-07-16
- **관련 문서**:
  - [../../../workflow-source/MEMORY_GOVERNANCE.md](../../../workflow-source/MEMORY_GOVERNANCE.md) §2 (Standard Templates) — 본 layout 의 spec 출처
  - [../../../workflow-source/core/workflow_state_vs_project_docs.md](../../../workflow-source/core/workflow_state_vs_project_docs.md)
  - 영구 참조: [../../wiki/decisions/adr-003-deprecation-cycle.md](../../wiki/decisions/adr-003-deprecation-cycle.md)

## 1. 신규 layout (v0.14.0 append-only → **v1.0.0 branch-scoped**)

작업 상태는 **브랜치마다 물리적으로 분리**된다 (`active/<branch>/`). 여러 브랜치가 동시에
일해도 daily index / task 번호 / `state.json` 이 서로를 덮어쓰지 않는다.

```
ai-workflow/memory/
├── active/
│   ├── <branch>/                  ← 🆕 v1.0.0 브랜치별 작업 상태 (main 도 동일)
│   │   ├── state.json             ← read-only snapshot (state/builder.py 가 rebuild)
│   │   ├── backlog/               ← per-day + per-task append-only
│   │   │   ├── YYYY-MM-DD.md      ← daily index (link to tasks/)
│   │   │   └── tasks/
│   │   │       └── TASK-2026-07-21-main-001.md   ← 1 file = 1 task (per-task SSOT)
│   │   ├── sessions/              ← per-session (was session_handoff.md)
│   │   │   └── 2026-07-09-audit.md
│   │   └── session_analysis_<date>.md
│   │
│   ├── PROJECT_PROFILE.md         ← 공유 (브랜치 무관, manually maintained)
│   ├── PURPOSE.md                 ← 공유
│   ├── project_status_assessment.md / repository_assessment.md  ← 공유
│   ├── state.json.template        ← 공유 (template)
│   └── memory_index/              ← 공유 (통합 검색, 이미 append-only 정공법)
│       ├── entries/MEM-YYYY-MM-DD-NNN.json
│       └── telemetry/events.jsonl
│
├── archived/<branch>/             ← 🆕 종료된 브랜치 (.archived.json 메타 동반)
├── archive/YYYY-MM-DD/            ← R8 freeze (별개 개념 — 이름 혼동 주의)
├── release/<version>/             ← release cycle 아카이브
└── log.md                         ← unchanged (append-only)
```

**브랜치 종료 시**: `active/<branch>/` 가 있는데 git 에 그 브랜치가 없으면 종료로 보고
`archived/<branch>/` 로 옮긴다 (역방향 점검 — hook 은 브랜치 삭제를 못 잡는다).
고아 디렉터리가 구조적으로 생길 수 없다. 도구는 commit/push 를 하지 않으므로
**protected main 과 호환**되며, 작업 브랜치에서 실행해 그 PR 에 실어 보낸다(piggyback).

```bash
python3 workflow-source/tools/archive_branch_memory.py --dry-run   # 계획 확인
python3 workflow-source/tools/archive_branch_memory.py --apply     # 이동 (commit 은 직접)
```

## 2. 충돌 표면 (multi-agent 동시 작업 시)

| 파일 | 동시 작업 시 충돌? | 비고 |
|---|---|---|
| `<branch>/state.json` | ❌ **브랜치별 물리 격리** (v1.0.0) | 브랜치마다 자기 state |
| `<branch>/backlog/YYYY-MM-DD.md` | ❌ **브랜치별 물리 격리** (v1.0.0) | 같은 브랜치 내 동시 작업은 🟡 3-way concat |
| `<branch>/backlog/tasks/TASK-XXX.md` | ❌ **물리 격리** | task ID 에 브랜치 slug 포함 → 번호 충돌 0 |
| `<branch>/sessions/<date>-<topic>.md` | ❌ **물리 격리** | 다른 agent 가 다른 session file |
| `memory_index/entries/*.json` | ❌ **물리 격리** (기존) | v0.13.1 부터 |
| `memory_index/telemetry/events.jsonl` | ❌ **append-only** (기존) | v0.13.1 부터 |
| `log.md` | ❌ **append-only** (기존) | 2026-06-12 부터 |

→ **신규 layout 에서는 mutable 공유 파일이 `state.json` 단 1개**. 나머지는 모두 append-only 또는 자기 소유.

## 3. write 권한

| 디렉토리/파일 | 누가 쓰나 | 도구 |
|---|---|---|
| `state.json` | **state/builder.py** (rebuild only) | `python3 scripts/generate_workflow_state.py --apply` |
| `state.json.template` | maintainer | manual |
| `backlog/<date>.md` | agent (append section) | `backlog-update` skill `--apply` |
| `backlog/tasks/TASK-XXX.md` | agent (자기 task 만) | `backlog-update` skill `--mode create` |
| `sessions/<sid>.md` | agent (자기 session 만) | `session-start` skill |
| `PROJECT_PROFILE.md` / `PURPOSE.md` / `*.md` (정적) | maintainer | manual |
| `memory_index/entries/*.json` | agent (자기 entry 만) | `memory-index-query` / Python helper |
| `memory_index/telemetry/events.jsonl` | 자동 (3 skill + dispatcher wiring) | append-only |
| `log.md` | 자동 (session-start / freeze / ingest event) | append-only |

## 4. 운영 규칙

- **state.json**: 손으로 편집하지 않는다. 항상 `python3 scripts/generate_workflow_state.py` 로 rebuild.
- **backlog/YYYY-MM-DD.md**: 새 task 추가 시 새 section 1개 추가 (append). 절대 기존 section 수정 ❌.
- **backlog/tasks/TASK-XXX.md**: 1 task = 1 file, frontmatter 는 `MEMORY_GOVERNANCE.md` §2 의 `Task Detail (TASK-XXX.md)` 템플릿 정합.
- **sessions/<sid>.md**: 1 session = 1 file. 같은 session 내 append 가능, 다른 session 은 다른 file.
- **memory_index/** + **log.md**: 코드 자동 emit, 사용자 손 수정 ❌.

## 5. 마이그레이션 (v0.14.0)

기존 `work_backlog.md` 단일 파일은 다음 release 까지 fallback 으로 보존됩니다:

- **v0.14.0** (현재, 1st cycle): 신규 layout **활성**, `work_backlog.md` 가 있으면 warning log emit 후 fallback 으로 read. 동시 write 는 신규 layout 만 권장.
- **v0.14.5** (2nd cycle 시작 예정): `work_backlog.md` 는 `--legacy-memory` opt-out flag 가 있을 때만 read.
- **v0.15.0** (2nd cycle 종결): `work_backlog.md` / `work_backlog.md.bak` 모두 drop. 신규 layout 만 사용.

마이그레이션 도구: [`../../../workflow-source/tools/migrate_active_to_appendonly.py`](../../../workflow-source/tools/migrate_active_to_appendonly.py)

## 6. ADR

본 layout 결정은 다음 ADR 의 합류점:
- ADR-001 (deprecation contract) — v0.14.0~v0.15.0 의 1st/2nd cycle 패턴
- ADR-003 (memory 3-state lifecycle) — active / archive / release 의 역할 재확인
- ADR-005 (Memora-inspired Memory Index) — memory_index/ 의 append-only 패턴을 본 layout 의 정공법으로 채택

## 7. 다음에 읽을 문서

- 본 layout spec: [`../../../workflow-source/MEMORY_GOVERNANCE.md`](../../../workflow-source/MEMORY_GOVERNANCE.md) §2
- 작업 단위 task 템플릿: [`../../../workflow-source/MEMORY_GOVERNANCE.md#standard-templates`](../../../workflow-source/MEMORY_GOVERNANCE.md) (Task Detail)
- deprecation contract: [`../../wiki/decisions/adr-003-deprecation-cycle.md`](../../wiki/decisions/adr-003-deprecation-cycle.md)
- 신규 layout smoke: [`../../../workflow-source/tests/check_appendonly_memory_layout.py`](../../../workflow-source/tests/check_appendonly_memory_layout.py) (v0.14.0 신규)
