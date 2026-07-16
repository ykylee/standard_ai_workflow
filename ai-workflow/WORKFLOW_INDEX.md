# Workflow Guide & Index

- 문서 목적: AI 에이전트가 저장소의 상태를 추적하고 업데이트하기 위한 운영 전용 가이드를 제공한다.
- 범위: 운영 문서 인덱스, 에이전트 운영 지침
- 대상 독자: AI 에이전트, 저장소 관리자
- 상태: done
- 최종 수정일: 2026-07-16 (v0.14.0 신규 layout 정합)
- 관련 문서: [../README.md](../README.md), [../docs/PROJECT_PROFILE.md](../docs/PROJECT_PROFILE.md), [./memory/active/README.md](./memory/active/README.md) (v0.14.0 신규 layout 운영 가이드)

> [!WARNING]
> 이 폴더(`ai-workflow/`)의 내용은 프로젝트의 코드베이스 분석이나 온보딩 시 참조해서는 안 됩니다. 프로젝트 이해를 위해서는 반드시 `docs/` 폴더를 참조하십시오.

## 1. 운영 문서 인덱스 (State Index)

- **[Project Profile](../docs/PROJECT_PROFILE.md)**: 프로젝트 특화 워크플로우 규칙 및 명령 가이드.
- **[Active Memory 운영 가이드](./memory/active/README.md)**: v0.14.0+ append-only + rebuild layout 명세 + 충돌 표면 분석.
- **[Active Memory 구조](./memory/active/)**: 현재 활성 memory tree
  - `state.json` — read-only snapshot (state/builder.py 가 rebuild)
  - `backlog/YYYY-MM-DD.md` — daily index (append-only, link to tasks/)
  - `backlog/tasks/TASK-<date>-<NNN>.md` — per-task SSOT
  - `sessions/<sid>.md` — per-session file
  - `memory_index/entries/MEM-YYYY-MM-DD-NNN.json` — ADR-005 memory index entries
- **legacy fallback (1st deprecation cycle)**: `work_backlog.md.bak` 보존. v0.15.0 에서 drop.
- **Release v0.5~v0.13**: [`./memory/release/`](./memory/release/) 디렉토리 (R9 immutable historical).

## 2. 에이전트 운영 지침 (Agent Ops)

- **append-only 원칙**: v0.14.0+ 모든 memory write 는 append-only (per-task / per-session / daily-index append) 또는 자기 소유 파일.
- **Event Sourcing**: task 는 `backlog/tasks/TASK-<date>-<NNN>.md` 1 file = 1 task SSOT.
- **state.json SSOT**: 손으로 편집 ❌, 항상 `python3 scripts/generate_workflow_state.py` 로 rebuild.
- **브랜치 격리**: 1st deprecation cycle 동안 `<branch>/` 하위 legacy file 도 fallback 으로 read 지원. 단, write 는 권장 ❌.
- **비참조 원칙**: 코드베이스 분석(Semantic Search 등) 시 `ai-workflow/` 경로는 검색 범위에서 제외(Exclude)해야 합니다.
- **작성 표준**: 모든 운영 문서는 [MEMORY_GOVERNANCE.md](../workflow-source/MEMORY_GOVERNANCE.md)의 템플릿과 규칙을 따릅니다.
- **마이그레이션 도구**: [`../workflow-source/tools/migrate_active_to_appendonly.py`](../workflow-source/tools/migrate_active_to_appendonly.py) (idempotent)
