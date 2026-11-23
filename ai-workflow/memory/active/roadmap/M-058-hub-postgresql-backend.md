---
id: M-058
title: 허브 PostgreSQL 백엔드와 SQLite 데이터 이관
sdlc_phase: implementation
status: in_progress
order: 58
parallel_allowed:
  - M-007
  - M-028
  - M-039
  - M-057
deliverables:
  - workflow-source/core/hub_postgresql_spec.md
  - hub-go/internal/db/
  - docs/HUB_OPERATIONS.md
goals: [G1, G3, G5]
---

# M-058 — 허브 PostgreSQL 백엔드와 SQLite 데이터 이관

허브 테스트는 계속 SQLite를 사용한다. 배포 런타임은 PostgreSQL 서버에 연결할 수 있고,
기존 SQLite 허브 DB의 스키마와 데이터를 PostgreSQL로 복사한 뒤 정합성을 확인할 수
있어야 한다. PostgreSQL runtime 대상은 Go와 Python 모두이며, TASK-2026-11-23-main-010의
소유자 결정으로 확정했다.

## WBS

- **WBS-58.1** PostgreSQL 연결·schema migration·SQLite 데이터 이전의 운영 계약 및 설계 정리 — 산출물: `hub_postgresql_spec.md`
- **WBS-58.2** PostgreSQL 연결과 versioned schema migration 구현 — 산출물: DSN 기반 기동, 원자적 판 올림, 실패 복구
- **WBS-58.3** 기존 SQLite DB를 PostgreSQL로 복사하고 무결성·행 수를 대조 — 산출물: 읽기 전용 원본 보존, 검증 보고서, 재실행 안전성
- **WBS-58.4** SQLite 테스트 유지, 설치·운영 안내와 실제 PostgreSQL 격리 pilot — 산출물: SQLite 기본 회귀 통과 및 PG 운영 절차
