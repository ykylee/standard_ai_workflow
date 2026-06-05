# Work Backlog Index

- 문서 목적: 일별 작업 백로그에 대한 인덱스로, 최근 작업 흐름을 빠르게 복원한다.
- 범위: 인덱스 항목, 백로그 경로 규약, 갱신 규칙
- 대상 독자: AI agent, 저장소 maintainer
- 상태: stable
- 최종 수정일: 2026-06-05
- 관련 문서: [./PROJECT_PROFILE.md](./PROJECT_PROFILE.md), 브랜치별 daily backlog (각 브랜치 디렉터리 아래 `backlog/YYYY-MM-DD.md`)

## 인덱스 규칙

- 한 줄 = `YYYY-MM-DD 작업 백로그` 링크, 형식 예: `- [2026-06-05 작업 백로그](./release/v0.5.1/backlog/2026-06-05.md) — 요약` (실제 인덱스 항목은 각 브랜치 디렉터리(`<BRANCH>`) 의 실제 경로로 작성)
- 각 일자 백로그는 TASK-NNN 식별자를 가진 작업 항목 1개 이상 포함
- 같은 일자에 여러 브랜치 작업이 있으면 브랜치별로 별도 백로그 파일

## 최근 작업 백로그

### release/v0.5.1 (2026-06-05)
- [2026-06-05 작업 백로그](./release/v0.5.1/backlog/2026-06-05.md) — v0.5.0 self-dogfooding 점검 + 메모리 layer 부트스트랩 (TASK-V051-001, TASK-V051-002)

### Historical (참고용, 보존)
- [2026-05-01 작업 백로그](./codex/phase6/backlog/2026-05-01.md) — Phase 6 multi-agent delegation pilot (코드x/phase6 스냅샷)
- [2026-04-30 작업 백로그](./gemini/phase10/backlog/2026-04-24.md) — Phase 10 (MCP/JSON-RPC draft) (gemini/phase10 스냅샷)

## 다음에 읽을 문서

- [release/v0.5.1/session_handoff.md](./release/v0.5.1/session_handoff.md)
- [release/v0.5.1/backlog/2026-06-05.md](./release/v0.5.1/backlog/2026-06-05.md)
- [Maturity Matrix](../../workflow-source/core/maturity_matrix.json)
